"""
PubMed data downloader
Downloads XML dumps from NCBI FTP and processes them
"""

import ftplib
import gzip
import logging
import os
import time
from contextlib import contextmanager
from typing import Optional

from config import Config

logger = logging.getLogger(__name__)


class PubMedDownloader:
    """Downloads PubMed XML data from NCBI FTP"""

    def __init__(self):
        self.config = Config()
        self.ftp_host = "ftp.ncbi.nlm.nih.gov"
        self.ftp_path = "/pubmed/baseline/"
        self.update_path = "/pubmed/updatefiles/"
        self.data_dir = self.config.get_pubmed_data_dir()
        
        # FTP timeout and retry configuration
        self.connection_timeout = 30  # seconds
        self.operation_timeout = 60   # seconds
        self.download_timeout = 300   # seconds for large files
        self.max_retries = 3
        self.retry_delay = 5          # seconds

    @contextmanager
    def ftp_connection(self, timeout: Optional[int] = None):
        """Context manager for FTP connections with timeout and cleanup"""
        ftp = None
        try:
            timeout = timeout or self.connection_timeout
            logger.info(f"Connecting to {self.ftp_host} with {timeout}s timeout")
            
            ftp = ftplib.FTP(timeout=timeout)
            ftp.connect(self.ftp_host)
            ftp.login()
            
            logger.info("FTP connection established successfully")
            yield ftp
            
        except ftplib.all_errors as e:
            logger.error(f"FTP connection error: {e}")
            raise
        finally:
            if ftp:
                try:
                    ftp.quit()
                    logger.debug("FTP connection closed")
                except Exception:
                    # Force close if quit fails
                    try:
                        ftp.close()
                    except Exception:
                        pass

    def retry_operation(self, operation_name: str, operation_func, *args, **kwargs):
        """Retry an operation with exponential backoff"""
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Attempting {operation_name} (attempt {attempt + 1}/{self.max_retries})")
                return operation_func(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"{operation_name} failed after {self.max_retries} attempts: {e}")
                    raise
                
                wait_time = self.retry_delay * (2 ** attempt)
                logger.warning(f"{operation_name} failed (attempt {attempt + 1}): {e}, retrying in {wait_time}s")
                time.sleep(wait_time)

    async def download_baseline(self) -> list[str]:
        """Download PubMed baseline files with robust error handling"""
        logger.info("Starting PubMed baseline download")

        def download_operation():
            with self.ftp_connection(self.connection_timeout) as ftp:
                # Change to baseline directory
                ftp.cwd(self.ftp_path)
                logger.info(f"Changed to directory: {self.ftp_path}")

                # Get list of baseline files
                files = []
                ftp.retrlines("NLST", files.append)
                xml_files = [f for f in files if f.endswith(".xml.gz")]
                
                logger.info(f"Found {len(xml_files)} baseline files")

                # Download first few files for testing (adjust as needed)
                recent_files = xml_files[:5]  # Download first 5 for testing
                downloaded_files = []

                for i, file in enumerate(recent_files, 1):
                    local_path = os.path.join(self.data_dir, file)
                    if not os.path.exists(local_path):
                        logger.info(f"Downloading baseline file {i}/{len(recent_files)}: {file}")
                        
                        # Set longer timeout for large file downloads
                        ftp.sock.settimeout(self.download_timeout)
                        
                        with open(local_path, "wb") as local_file:
                            ftp.retrbinary(f"RETR {file}", local_file.write)
                        
                        logger.info(f"Successfully downloaded: {file}")
                        downloaded_files.append(local_path)
                    else:
                        logger.info(f"File already exists: {file}")
                        downloaded_files.append(local_path)

                return downloaded_files

        try:
            downloaded_files = self.retry_operation("baseline_download", download_operation)
            logger.info(f"Downloaded {len(downloaded_files)} baseline files")
            return downloaded_files

        except Exception as e:
            logger.error(f"PubMed baseline download failed: {e}")
            raise

    async def download_updates(self) -> list[str]:
        """Download PubMed update files with robust error handling"""
        logger.info("Starting PubMed updates download")

        def download_operation():
            with self.ftp_connection(self.connection_timeout) as ftp:
                # Change to updates directory
                ftp.cwd(self.update_path)
                logger.info(f"Changed to directory: {self.update_path}")

                # Get list of update files
                files = []
                ftp.retrlines("NLST", files.append)
                xml_files = [f for f in files if f.endswith(".xml.gz")]

                # Get recent updates (last 50 files - approximate recent files)
                recent_files = xml_files[-50:] if len(xml_files) > 50 else xml_files
                logger.info(f"Found {len(recent_files)} recent update files")

                downloaded_files = []
                for i, file in enumerate(recent_files, 1):
                    local_path = os.path.join(self.data_dir, f"updates_{file}")
                    if not os.path.exists(local_path):
                        logger.info(f"Downloading update file {i}/{len(recent_files)}: {file}")
                        
                        # Set longer timeout for large file downloads
                        ftp.sock.settimeout(self.download_timeout)
                        
                        with open(local_path, "wb") as local_file:
                            ftp.retrbinary(f"RETR {file}", local_file.write)
                        
                        logger.info(f"Successfully downloaded: {file}")
                        downloaded_files.append(local_path)
                    else:
                        logger.info(f"Update file already exists: {file}")
                        downloaded_files.append(local_path)

                return downloaded_files

        try:
            downloaded_files = self.retry_operation("updates_download", download_operation)
            logger.info(f"Downloaded {len(downloaded_files)} update files")
            return downloaded_files

        except Exception as e:
            logger.error(f"PubMed updates download failed: {e}")
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
            logger.error(f"Failed to extract {gz_file_path}: {e}")
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
