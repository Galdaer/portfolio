#!/usr/bin/env python3
"""
Complete PubMed Archive Downloader
Downloads the full PubMed corpus (~220GB) for offline database operation

Uses the same configuration and patterns as the medical-mirrors service
for consistency with the existing database schema and architecture.
"""

import argparse
import asyncio
import ftplib
import gzip
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import Any, Callable, Iterator

# Type checking imports
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from medical_mirrors_types import Config
else:
    # Runtime imports - add medical-mirrors to Python path
    medical_mirrors_src = str(Path(__file__).parent.parent / "services/user/medical-mirrors/src")
    if medical_mirrors_src not in sys.path:
        sys.path.insert(0, medical_mirrors_src)

    try:
        from config import Config
    except ImportError as e:
        print(f"Failed to import medical-mirrors modules: {e}")
        print(f"Make sure medical-mirrors service is properly installed")
        print(f"Looking for modules in: {medical_mirrors_src}")
        sys.exit(1)


class CompletePubMedDownloader:
    """
    Downloads complete PubMed archive for local database caching.
    
    Based on the existing medical-mirrors PubMedDownloader but enhanced
    for complete archive downloads instead of incremental updates.
    """

    def __init__(self, custom_data_dir: str | None = None):
        # Use medical-mirrors Config for consistency
        self.config = Config()
        self.ftp_host = "ftp.ncbi.nlm.nih.gov"
        self.baseline_path = "/pubmed/baseline/"
        self.updates_path = "/pubmed/updatefiles/"
        
        # Allow custom data directory override
        if custom_data_dir:
            self.data_dir = custom_data_dir
            os.makedirs(self.data_dir, exist_ok=True)
        else:
            self.data_dir = self.config.get_pubmed_data_dir()
        
        self.logger = self._setup_logging()
        
        # Use same timeout/retry patterns as existing downloader
        self.connection_timeout = 30  # seconds
        self.operation_timeout = 60  # seconds
        self.download_timeout = 300  # seconds for large files
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        
        # Download statistics
        self.stats = {
            "baseline_files_downloaded": 0,
            "update_files_downloaded": 0,
            "total_size_downloaded": 0,
            "start_time": None,
            "end_time": None,
            "errors": []
        }

    def _setup_logging(self) -> logging.Logger:
        """Setup comprehensive download logging"""
        logger = logging.getLogger("complete_pubmed_downloader")
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    @contextmanager
    def ftp_connection(self, timeout: int | None = None) -> Iterator[ftplib.FTP]:
        """Context manager for FTP connections with timeout and cleanup (same as medical-mirrors)"""
        ftp = None
        try:
            timeout = timeout or self.connection_timeout
            self.logger.info(f"Connecting to {self.ftp_host} with {timeout}s timeout")

            ftp = ftplib.FTP(timeout=timeout)
            ftp.connect(self.ftp_host)
            ftp.login()

            self.logger.info("FTP connection established successfully")
            yield ftp

        except ftplib.all_errors as e:
            self.logger.exception(f"FTP connection error: {e}")
            raise
        finally:
            if ftp:
                try:
                    ftp.quit()
                    self.logger.debug("FTP connection closed")
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
        for attempt in range(self.config.max_retries):
            try:
                self.logger.debug(
                    f"Attempting {operation_name} (attempt {attempt + 1}/{self.config.max_retries})"
                )
                return operation_func(*args, **kwargs)
            except Exception as e:
                if attempt == self.config.max_retries - 1:
                    self.logger.exception(
                        f"{operation_name} failed after {self.config.max_retries} attempts: {e}"
                    )
                    raise

                wait_time = self.config.retry_delay * (2**attempt)
                self.logger.warning(
                    f"{operation_name} failed (attempt {attempt + 1}): {e}, retrying in {wait_time}s"
                )
                time.sleep(wait_time)

        return []

    async def download_complete_archive(self) -> dict[str, Any]:
        """Download complete PubMed baseline + update files"""
        self.logger.info("Starting complete PubMed archive download (~220GB)")
        self.stats["start_time"] = time.time()

        # Create directories
        baseline_dir = self.config.data_dir / "baseline"
        updates_dir = self.config.data_dir / "updates"
        baseline_dir.mkdir(parents=True, exist_ok=True)
        updates_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Download complete baseline files (~1,219 files, ~120GB)
            self.logger.info("Phase 1: Downloading complete PubMed baseline (~120GB)")
            baseline_files = await self.download_complete_baseline()
            self.stats["baseline_files_downloaded"] = len(baseline_files)

            # Download all update files (~2,000 files, ~100GB)
            self.logger.info("Phase 2: Downloading all PubMed updates (~100GB)")
            update_files = await self.download_complete_updates()
            self.stats["update_files_downloaded"] = len(update_files)

            self.stats["end_time"] = time.time()
            duration = self.stats["end_time"] - self.stats["start_time"]
            
            total_files = len(baseline_files) + len(update_files)
            
            self.logger.info(f"✅ Complete PubMed download finished!")
            self.logger.info(f"   Baseline files: {len(baseline_files)}")
            self.logger.info(f"   Update files: {len(update_files)}")
            self.logger.info(f"   Total files: {total_files}")
            self.logger.info(f"   Duration: {duration/3600:.1f} hours")
            
            return {
                "status": "success",
                "baseline_files": len(baseline_files),
                "update_files": len(update_files),
                "total_files": total_files,
                "duration_hours": duration / 3600,
                "errors": self.stats["errors"]
            }

        except Exception as e:
            self.logger.exception(f"Complete PubMed download failed: {e}")
            self.stats["errors"].append(str(e))
            return {
                "status": "failed",
                "error": str(e),
                "partial_stats": self.stats
            }

    async def download_complete_baseline(self) -> list[str]:
        """Download ALL PubMed baseline files (~1,219 files, ~120GB)"""
        self.logger.info("Downloading complete PubMed baseline corpus")

        def download_operation() -> list[str]:
            with self.ftp_connection(self.config.connection_timeout) as ftp:
                # Change to baseline directory
                ftp.cwd(self.baseline_path)
                self.logger.info(f"Changed to directory: {self.baseline_path}")

                # Get complete list of baseline files
                files: list[str] = []
                ftp.retrlines("NLST", files.append)
                xml_files = [f for f in files if f.endswith(".xml.gz")]

                self.logger.info(f"Found {len(xml_files)} baseline files to download")
                self.logger.warning("⚠️  This will download ~120GB of data")

                # Download ALL baseline files (not just first 5)
                downloaded_files: list[str] = []
                baseline_dir = self.config.data_dir / "baseline"

                with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                    futures = []
                    
                    for i, file in enumerate(xml_files, 1):
                        local_path = baseline_dir / file
                        future = executor.submit(
                            self._download_single_file, 
                            ftp, 
                            file, 
                            local_path, 
                            f"baseline {i}/{len(xml_files)}"
                        )
                        futures.append((future, local_path))

                    # Wait for all downloads
                    for future, local_path in futures:
                        try:
                            if future.result():
                                downloaded_files.append(str(local_path))
                        except Exception as e:
                            self.logger.error(f"Failed to download {local_path.name}: {e}")
                            self.stats["errors"].append(f"Baseline {local_path.name}: {e}")

                return downloaded_files

        try:
            downloaded_files = self.retry_operation("complete_baseline_download", download_operation)
            self.logger.info(f"Downloaded {len(downloaded_files)} baseline files")
            return downloaded_files

        except Exception as e:
            self.logger.exception(f"Complete PubMed baseline download failed: {e}")
            raise

    async def download_complete_updates(self) -> list[str]:
        """Download ALL PubMed update files (~2,000 files, ~100GB)"""
        self.logger.info("Downloading all PubMed update files")

        def download_operation() -> list[str]:
            with self.ftp_connection(self.config.connection_timeout) as ftp:
                # Change to updates directory
                ftp.cwd(self.updates_path)
                self.logger.info(f"Changed to directory: {self.updates_path}")

                # Get complete list of update files
                files: list[str] = []
                ftp.retrlines("NLST", files.append)
                xml_files = [f for f in files if f.endswith(".xml.gz")]

                self.logger.info(f"Found {len(xml_files)} update files to download")
                self.logger.warning("⚠️  This will download ~100GB of data")

                # Download ALL update files (not just recent 50)
                downloaded_files: list[str] = []
                updates_dir = self.config.data_dir / "updates"

                with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                    futures = []
                    
                    for i, file in enumerate(xml_files, 1):
                        local_path = updates_dir / file
                        future = executor.submit(
                            self._download_single_file, 
                            ftp, 
                            file, 
                            local_path, 
                            f"update {i}/{len(xml_files)}"
                        )
                        futures.append((future, local_path))

                    # Wait for all downloads
                    for future, local_path in futures:
                        try:
                            if future.result():
                                downloaded_files.append(str(local_path))
                        except Exception as e:
                            self.logger.error(f"Failed to download {local_path.name}: {e}")
                            self.stats["errors"].append(f"Update {local_path.name}: {e}")

                return downloaded_files

        try:
            downloaded_files = self.retry_operation("complete_updates_download", download_operation)
            self.logger.info(f"Downloaded {len(downloaded_files)} update files")
            return downloaded_files

        except Exception as e:
            self.logger.exception(f"Complete PubMed updates download failed: {e}")
            raise

    def _download_single_file(self, ftp: ftplib.FTP, filename: str, local_path: Path, progress_label: str) -> bool:
        """Download a single file with resume support and progress tracking"""
        try:
            # Check if file already exists and get size
            resume_pos = 0
            if local_path.exists() and self.config.resume_downloads:
                resume_pos = local_path.stat().st_size
                if resume_pos > 0:
                    self.logger.info(f"Resuming {filename} from position {resume_pos}")

            # Set longer timeout for large file downloads
            if hasattr(ftp, "sock") and ftp.sock:
                ftp.sock.settimeout(self.config.download_timeout)

            # Open file in append mode if resuming
            mode = "ab" if resume_pos > 0 else "wb"
            
            with open(local_path, mode) as local_file:
                # Use REST command for resume
                if resume_pos > 0:
                    ftp.voidcmd(f"REST {resume_pos}")
                
                def write_callback(data):
                    local_file.write(data)
                    self.stats["total_size_downloaded"] += len(data)

                ftp.retrbinary(f"RETR {filename}", write_callback)

            file_size = local_path.stat().st_size
            self.logger.info(f"✅ Downloaded {progress_label}: {filename} ({file_size/1024/1024:.1f} MB)")
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to download {filename}: {e}")
            # Clean up partial file on error
            if local_path.exists() and not self.config.resume_downloads:
                local_path.unlink()
            return False

    def get_download_stats(self) -> dict[str, Any]:
        """Get comprehensive download statistics"""
        stats = self.stats.copy()
        
        if stats["start_time"] and stats["end_time"]:
            duration = stats["end_time"] - stats["start_time"]
            stats["duration_seconds"] = duration
            stats["duration_hours"] = duration / 3600
            
            total_files = stats["baseline_files_downloaded"] + stats["update_files_downloaded"]
            stats["total_files"] = total_files
            
            if duration > 0:
                stats["files_per_second"] = total_files / duration
                stats["mb_per_second"] = (stats["total_size_downloaded"] / 1024 / 1024) / duration
        
        return stats


def main():
    """Main function for complete PubMed download"""
    parser = argparse.ArgumentParser(
        description="Download complete PubMed archive for offline operation",
        epilog="Uses medical-mirrors configuration for database compatibility"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        help="Directory to store complete PubMed data (default: medical-mirrors config)"
    )
    parser.add_argument(
        "--baseline-only",
        action="store_true",
        help="Download only baseline files (~120GB)"
    )
    parser.add_argument(
        "--updates-only",
        action="store_true",
        help="Download only update files (~100GB)"
    )

    args = parser.parse_args()

    # Create downloader with optional custom data directory
    downloader = CompletePubMedDownloader(custom_data_dir=args.data_dir)

    print(f"\n📚 Starting complete PubMed download to: {downloader.data_dir}")
    print("⚠️  WARNING: This will download ~220GB of medical literature")
    print("💾 Ensure you have sufficient disk space before proceeding")
    print("🔧 Using medical-mirrors config for database compatibility\n")

    # Run download
    if args.baseline_only:
        print("📥 Downloading baseline files only (~120GB)")
        result = asyncio.run(downloader.download_complete_baseline())
    elif args.updates_only:
        print("📥 Downloading update files only (~100GB)")
        result = asyncio.run(downloader.download_complete_updates())
    else:
        print("📥 Downloading complete archive (~220GB)")
        result = asyncio.run(downloader.download_complete_archive())

    # Show results
    if isinstance(result, dict) and result.get("status") == "success":
        print("\n✅ PubMed download completed successfully!")
        print(f"   Files downloaded: {result.get('total_files', 'N/A')}")
        print(f"   Duration: {result.get('duration_hours', 0):.1f} hours")
    else:
        print("\n❌ PubMed download failed or incomplete")
        if isinstance(result, dict) and "error" in result:
            print(f"   Error: {result['error']}")

    # Show download statistics
    stats = downloader.get_download_stats()
    print(f"\n📊 Download Statistics:")
    print(f"   Total size: {stats.get('total_size_downloaded', 0) / 1024 / 1024 / 1024:.1f} GB")
    print(f"   Speed: {stats.get('mb_per_second', 0):.1f} MB/s")
    print(f"   Errors: {len(stats.get('errors', []))}")
    
    # Show next steps
    print(f"\n📋 Next Steps:")
    print(f"   1. Parse downloaded files: python scripts/parse_downloaded_archives.py pubmed")
    print(f"   2. Or use medical-mirrors API: POST /update/pubmed")
    print(f"   3. Files stored in: {downloader.data_dir}")


if __name__ == "__main__":
    main()