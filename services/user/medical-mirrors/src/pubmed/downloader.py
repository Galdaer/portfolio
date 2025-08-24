"""
PubMed data downloader
Downloads XML dumps from NCBI FTP and processes them
"""

import asyncio
import ftplib
import gzip
import logging
import os
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager, suppress
from typing import Any

from config import Config

logger = logging.getLogger(__name__)


class PubMedDownloader:
    """Downloads PubMed XML data from NCBI FTP"""

    def __init__(self, config=None) -> None:
        self.config = config or Config()
        self.ftp_host = "ftp.ncbi.nlm.nih.gov"
        self.ftp_path = "/pubmed/baseline/"
        self.update_path = "/pubmed/updatefiles/"
        self.data_dir = self.config.get_pubmed_data_dir()

        # FTP timeout and retry configuration (optimized for gigabit)
        self.connection_timeout = 60  # seconds - more time for initial connection
        self.operation_timeout = 120  # seconds - more time for operations
        self.download_timeout = 1800  # seconds (30 min) for very large files
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        self.ftp_buffer_size = 64 * 1024  # 64KB buffer for better throughput

    @contextmanager
    def ftp_connection(self, timeout: int | None = None) -> Iterator[ftplib.FTP]:
        """Context manager for FTP connections with timeout and cleanup"""
        ftp = None
        try:
            timeout = timeout or self.connection_timeout
            logger.info(f"Connecting to {self.ftp_host} with {timeout}s timeout")

            ftp = ftplib.FTP(timeout=timeout)
            ftp.connect(self.ftp_host)
            ftp.login()
            
            # Enable passive mode for better NAT/firewall compatibility
            ftp.set_pasv(True)
            
            # Set binary mode for better performance
            ftp.voidcmd('TYPE I')

            logger.info("FTP connection established successfully (passive mode, binary)")
            yield ftp

        except ftplib.all_errors as e:
            logger.exception(f"FTP connection error: {e}")
            raise
        finally:
            if ftp:
                try:
                    ftp.quit()
                    logger.debug("FTP connection closed")
                except Exception:
                    # Force close if quit fails
                    with suppress(Exception):
                        ftp.close()

    def retry_operation(
        self,
        operation_name: str,
        operation_func: Callable[..., list[str]],
        *args: Any,
        **kwargs: Any,
    ) -> list[str]:
        """Retry an operation with exponential backoff"""
        for attempt in range(self.max_retries):
            try:
                logger.debug(
                    f"Attempting {operation_name} (attempt {attempt + 1}/{self.max_retries})",
                )
                return operation_func(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.exception(
                        f"{operation_name} failed after {self.max_retries} attempts: {e}",
                    )
                    raise

                wait_time = self.retry_delay * (2**attempt)
                logger.warning(
                    f"{operation_name} failed (attempt {attempt + 1}): {e}, retrying in {wait_time}s",
                )
                time.sleep(wait_time)

        # This should never be reached due to the raise in the loop, but ensures type safety
        return []

    async def download_baseline(self) -> list[str]:
        """Download PubMed baseline files with robust error handling"""
        logger.info("Starting PubMed baseline download")

        def download_operation() -> list[str]:
            with self.ftp_connection(self.connection_timeout) as ftp:
                # Change to baseline directory
                ftp.cwd(self.ftp_path)
                logger.info(f"Changed to directory: {self.ftp_path}")

                # Get list of baseline files
                files: list[str] = []
                ftp.retrlines("NLST", files.append)
                xml_files = [f for f in files if f.endswith(".xml.gz")]

                logger.info(f"Found {len(xml_files)} baseline files")

                # Download first few files for testing (adjust as needed)
                recent_files = xml_files[:5]  # Download first 5 for testing
                downloaded_files: list[str] = []
                downloaded_files = []

                for i, file in enumerate(recent_files, 1):
                    local_path = os.path.join(self.data_dir, file)
                    if not os.path.exists(local_path):
                        logger.info(f"📥 Downloading PubMed baseline file {i}/{len(recent_files)}: {file}")

                        # Set longer timeout for large file downloads
                        if hasattr(ftp, "sock") and ftp.sock:
                            ftp.sock.settimeout(self.download_timeout)

                        # Download with progress tracking
                        file_size = 0
                        try:
                            # Get file size if possible (binary mode already set in connection)
                            file_size = ftp.size(file)
                        except Exception:
                            pass  # Size not available, continue without it
                        
                        downloaded_bytes = 0
                        def progress_callback(data):
                            nonlocal downloaded_bytes
                            downloaded_bytes += len(data)
                            # Show progress every 10MB
                            if downloaded_bytes % (10 * 1024 * 1024) < len(data):
                                if file_size > 0:
                                    percent = (downloaded_bytes / file_size) * 100
                                    logger.info(f"   📊 Progress: {downloaded_bytes//1024//1024}MB/{file_size//1024//1024}MB ({percent:.1f}%)")
                                else:
                                    logger.info(f"   📊 Downloaded: {downloaded_bytes//1024//1024}MB")
                            return data

                        with open(local_path, "wb") as local_file:
                            def write_with_progress(data):
                                progress_callback(data)
                                local_file.write(data)
                            
                            ftp.retrbinary(f"RETR {file}", write_with_progress, blocksize=self.ftp_buffer_size)

                        logger.info(f"✅ Downloaded: {file} ({downloaded_bytes//1024//1024}MB)")
                        downloaded_files.append(local_path)
                        
                        # Rate limiting between downloads
                        if i < len(recent_files):  # Don't sleep after the last file
                            time.sleep(self.config.PUBMED_REQUEST_DELAY)
                    else:
                        logger.info(f"⏭️  File already exists: {file}")
                        downloaded_files.append(local_path)

                return downloaded_files

        try:
            downloaded_files = self.retry_operation("baseline_download", download_operation)
            logger.info(f"Downloaded {len(downloaded_files)} baseline files")
            return downloaded_files

        except Exception as e:
            logger.exception(f"PubMed baseline download failed: {e}")
            raise

    async def download_updates(self) -> list[str]:
        """Download PubMed update files with robust error handling"""
        logger.info("Starting PubMed updates download")

        def download_operation() -> list[str]:
            with self.ftp_connection(self.connection_timeout) as ftp:
                # Change to updates directory
                ftp.cwd(self.update_path)
                logger.info(f"Changed to directory: {self.update_path}")

                # Get list of update files
                files: list[str] = []
                ftp.retrlines("NLST", files.append)
                xml_files = [f for f in files if f.endswith(".xml.gz")]

                # Get recent updates (last 50 files - approximate recent files)
                recent_files = xml_files[-50:] if len(xml_files) > 50 else xml_files
                logger.info(f"Found {len(recent_files)} recent update files")

                downloaded_files: list[str] = []
                downloaded_files = []
                for i, file in enumerate(recent_files, 1):
                    local_path = os.path.join(self.data_dir, f"updates_{file}")
                    if not os.path.exists(local_path):
                        logger.info(f"Downloading update file {i}/{len(recent_files)}: {file}")

                        # Set longer timeout for large file downloads
                        if hasattr(ftp, "sock") and ftp.sock:
                            ftp.sock.settimeout(self.download_timeout)

                        with open(local_path, "wb") as local_file:
                            ftp.retrbinary(f"RETR {file}", local_file.write)

                        logger.info(f"Successfully downloaded: {file}")
                        downloaded_files.append(local_path)
                        
                        # Rate limiting between downloads
                        if i < len(recent_files):  # Don't sleep after the last file
                            time.sleep(self.config.PUBMED_REQUEST_DELAY)
                    else:
                        logger.info(f"Update file already exists: {file}")
                        downloaded_files.append(local_path)

                return downloaded_files

        try:
            downloaded_files = self.retry_operation("updates_download", download_operation)
            logger.info(f"Downloaded {len(downloaded_files)} update files")
            return downloaded_files

        except Exception as e:
            logger.exception(f"PubMed updates download failed: {e}")
            raise

    def extract_xml_file(self, gz_file_path: str) -> str:
        """Extract gzipped XML file"""
        extracted_path = gz_file_path.replace(".gz", "")

        if os.path.exists(extracted_path):
            return extracted_path

        try:
            with gzip.open(gz_file_path, "rb") as gz_file:
                with open(extracted_path, "wb") as xml_file:
                    xml_file.write(gz_file.read())

            logger.info(f"Extracted {gz_file_path} to {extracted_path}")
            return extracted_path

        except Exception as e:
            logger.exception(f"Failed to extract {gz_file_path}: {e}")
            raise

    async def get_available_files(self) -> list[str]:
        """Get list of downloaded XML files ready for parsing"""
        xml_files = []

        for file in os.listdir(self.data_dir):
            if file.endswith(".xml.gz"):
                # Extract if needed
                gz_path = os.path.join(self.data_dir, file)
                xml_path = self.extract_xml_file(gz_path)
                xml_files.append(xml_path)
            elif file.endswith(".xml"):
                xml_files.append(os.path.join(self.data_dir, file))

        return xml_files

    async def download_complete_baseline(self) -> list[str]:
        """
        Download ALL PubMed baseline files for complete dataset.

        This method downloads the complete PubMed corpus instead of just
        the first 5 files like the regular download_baseline method.
        Use for initial full setup or complete data refresh.
        """
        logger.info("Starting COMPLETE PubMed baseline download (~120GB)")

        def download_complete_operation() -> list[str]:
            with self.ftp_connection(self.connection_timeout) as ftp:
                # Change to baseline directory
                ftp.cwd(self.ftp_path)
                logger.info(f"Changed to directory: {self.ftp_path}")

                # Get complete list of baseline files
                files: list[str] = []
                ftp.retrlines("NLST", files.append)
                xml_files = [f for f in files if f.endswith(".xml.gz")]

                logger.info(f"Found {len(xml_files)} baseline files for COMPLETE download")
                logger.warning("⚠️  This will download ALL baseline files (~120GB)")

                # Download ALL baseline files (not limited to 5)
                downloaded_files: list[str] = []

                for i, file in enumerate(xml_files, 1):
                    local_path = os.path.join(self.data_dir, file)
                    if not os.path.exists(local_path):
                        logger.info(f"📥 Downloading PubMed baseline file {i}/{len(xml_files)}: {file}")
                        
                        # Set longer timeout for large file downloads
                        if hasattr(ftp, "sock") and ftp.sock:
                            ftp.sock.settimeout(self.download_timeout)

                        # Download with progress tracking
                        file_size = 0
                        try:
                            # Get file size if possible (binary mode already set in connection)
                            file_size = ftp.size(file)
                        except Exception:
                            pass  # Size not available, continue without it
                        
                        downloaded_bytes = 0
                        def progress_callback(data):
                            nonlocal downloaded_bytes
                            downloaded_bytes += len(data)
                            # Show progress every 10MB
                            if downloaded_bytes % (10 * 1024 * 1024) < len(data):
                                if file_size > 0:
                                    percent = (downloaded_bytes / file_size) * 100
                                    logger.info(f"   📊 Progress: {downloaded_bytes//1024//1024}MB/{file_size//1024//1024}MB ({percent:.1f}%)")
                                else:
                                    logger.info(f"   📊 Downloaded: {downloaded_bytes//1024//1024}MB")
                            return data

                        with open(local_path, "wb") as local_file:
                            def write_with_progress(data):
                                progress_callback(data)
                                local_file.write(data)
                            
                            ftp.retrbinary(f"RETR {file}", write_with_progress, blocksize=self.ftp_buffer_size)

                        logger.info(f"✅ Downloaded: {file} ({downloaded_bytes//1024//1024}MB)")
                        downloaded_files.append(local_path)
                        
                        # Rate limiting between downloads
                        if i < len(xml_files):  # Don't sleep after the last file
                            time.sleep(self.config.PUBMED_REQUEST_DELAY)
                        
                        # Progress summary every 10 files
                        if i % 10 == 0:
                            logger.info(f"📈 Progress Summary: {i}/{len(xml_files)} files downloaded ({i/len(xml_files)*100:.1f}%)")
                            
                    else:
                        logger.info(f"⏭️  File already exists: {file}")
                        downloaded_files.append(local_path)

                return downloaded_files

        try:
            downloaded_files = self.retry_operation("complete_baseline_download", download_complete_operation)
            logger.info(f"Downloaded {len(downloaded_files)} complete baseline files")
            return downloaded_files

        except Exception as e:
            logger.exception(f"Complete PubMed baseline download failed: {e}")
            raise

    async def download_complete_updates(self) -> list[str]:
        """
        Download ALL PubMed update files for complete dataset.

        This method downloads all available update files instead of just
        the recent 50 files like the regular download_updates method.
        Use for complete data coverage.
        """
        logger.info("Starting COMPLETE PubMed updates download (~100GB)")

        def download_complete_operation() -> list[str]:
            with self.ftp_connection(self.connection_timeout) as ftp:
                # Change to updates directory
                ftp.cwd(self.update_path)
                logger.info(f"Changed to directory: {self.update_path}")

                # Get complete list of update files
                files: list[str] = []
                ftp.retrlines("NLST", files.append)
                xml_files = [f for f in files if f.endswith(".xml.gz")]

                logger.info(f"Found {len(xml_files)} update files for COMPLETE download")
                logger.warning("⚠️  This will download ALL update files (~100GB)")

                # Download ALL update files (not limited to recent 50)
                downloaded_files: list[str] = []

                for i, file in enumerate(xml_files, 1):
                    local_path = os.path.join(self.data_dir, f"updates_{file}")
                    if not os.path.exists(local_path):
                        logger.info(f"Downloading update file {i}/{len(xml_files)}: {file}")

                        # Set longer timeout for large file downloads
                        if hasattr(ftp, "sock") and ftp.sock:
                            ftp.sock.settimeout(self.download_timeout)

                        with open(local_path, "wb") as local_file:
                            ftp.retrbinary(f"RETR {file}", local_file.write)

                        logger.info(f"Successfully downloaded: {file}")
                        downloaded_files.append(local_path)
                        
                        # Rate limiting between downloads
                        if i < len(xml_files):  # Don't sleep after the last file
                            time.sleep(self.config.PUBMED_REQUEST_DELAY)
                    else:
                        logger.info(f"Update file already exists: {file}")
                        downloaded_files.append(local_path)

                return downloaded_files

        try:
            downloaded_files = self.retry_operation("complete_updates_download", download_complete_operation)
            logger.info(f"Downloaded {len(downloaded_files)} complete update files")
            return downloaded_files

        except Exception as e:
            logger.exception(f"Complete PubMed updates download failed: {e}")
            raise

    async def download_complete_dataset(self) -> dict[str, Any]:
        """
        Download complete PubMed dataset (baseline + all updates).

        This is the master method for downloading the entire PubMed corpus
        for offline database operation. Downloads ~220GB total.

        Returns:
            Dictionary with download statistics and file lists
        """
        logger.info("Starting COMPLETE PubMed dataset download (~220GB)")
        start_time = time.time()

        try:
            # Download complete baseline files
            baseline_files = await self.download_complete_baseline()

            # Download all update files
            update_files = await self.download_complete_updates()

            end_time = time.time()
            duration = end_time - start_time

            total_files = len(baseline_files) + len(update_files)

            logger.info("✅ Complete PubMed dataset download finished!")
            logger.info(f"   Baseline files: {len(baseline_files)}")
            logger.info(f"   Update files: {len(update_files)}")
            logger.info(f"   Total files: {total_files}")
            logger.info(f"   Duration: {duration/3600:.1f} hours")

            return {
                "status": "success",
                "baseline_files": baseline_files,
                "update_files": update_files,
                "total_files": total_files,
                "baseline_count": len(baseline_files),
                "update_count": len(update_files),
                "duration_seconds": duration,
                "duration_hours": duration / 3600,
                "estimated_size_gb": total_files * 0.1,  # Rough estimate: ~100MB per file
            }

        except Exception as e:
            logger.exception(f"Complete PubMed dataset download failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "duration_seconds": time.time() - start_time,
            }
