#!/usr/bin/env python3
"""
Complete FDA Archive Downloader
Downloads complete FDA drug databases (~22GB) for offline database operation

Uses the same configuration and patterns as the medical-mirrors service
for consistency with the existing database schema and architecture.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
import zipfile
from pathlib import Path
from typing import Any, Dict

import httpx

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


class CompleteFDADownloader:
    """
    Downloads complete FDA drug databases for local database caching.
    
    Based on the existing medical-mirrors FDADownloader but enhanced
    for complete archive downloads with working URLs.
    """

    def __init__(self, custom_data_dir: str | None = None):
        # Use medical-mirrors Config for consistency
        self.config = Config()
        
        # Allow custom data directory override
        if custom_data_dir:
            self.data_dir = custom_data_dir
            os.makedirs(self.data_dir, exist_ok=True)
        else:
            self.data_dir = self.config.get_fda_data_dir()
            
        self.logger = self._setup_logging()
        
        # HTTP session with longer timeout for large files
        self.session = httpx.AsyncClient(timeout=120.0)
        
        # Download statistics
        self.stats = {
            "datasets_downloaded": 0,
            "total_size_downloaded": 0,
            "files_extracted": 0,
            "start_time": None,
            "end_time": None,
            "errors": []
        }

    def _setup_logging(self) -> logging.Logger:
        """Setup comprehensive download logging"""
        logger = logging.getLogger("complete_fda_downloader")
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    async def download_complete_archive(self) -> dict[str, Any]:
        """Download complete FDA drug databases"""
        self.logger.info("Starting complete FDA drug databases download (~22GB)")
        self.stats["start_time"] = time.time()

        try:
            # Download all FDA datasets
            results = {}
            
            # 1. Orange Book (FDA Approved Drug Products)
            results["orange_book"] = await self.download_orange_book()
            
            # 2. NDC Directory (National Drug Code Directory)
            results["ndc_directory"] = await self.download_ndc_directory()
            
            # 3. Drugs@FDA (Drug Approvals and Reviews)
            results["drugs_fda"] = await self.download_drugs_fda()
            
            # 4. Drug Labels (openFDA Labels)
            results["drug_labels"] = await self.download_drug_labels()
            
            self.stats["end_time"] = time.time()
            duration = self.stats["end_time"] - self.stats["start_time"]
            
            success_count = sum(1 for result in results.values() if result.get("success", False))
            
            self.logger.info(f"✅ Complete FDA download finished!")
            self.logger.info(f"   Successful datasets: {success_count}/4")
            self.logger.info(f"   Total size: {self.stats['total_size_downloaded'] / 1024 / 1024 / 1024:.1f} GB")
            self.logger.info(f"   Duration: {duration/3600:.1f} hours")
            
            return {
                "status": "success",
                "datasets_downloaded": success_count,
                "total_datasets": 4,
                "duration_hours": duration / 3600,
                "total_size_gb": self.stats["total_size_downloaded"] / 1024 / 1024 / 1024,
                "results": results,
                "errors": self.stats["errors"]
            }

        except Exception as e:
            self.logger.exception(f"Complete FDA download failed: {e}")
            self.stats["errors"].append(str(e))
            return {
                "status": "failed",
                "error": str(e),
                "partial_stats": self.stats
            }

    async def download_orange_book(self) -> dict[str, Any]:
        """Download FDA Orange Book data"""
        self.logger.info("Downloading FDA Orange Book...")
        
        try:
            # Updated working URL for Orange Book
            # https://www.fda.gov/drugs/drug-approvals-and-databases/approved-drug-products-therapeutic-equivalence-evaluations-orange-book
            orange_book_url = "https://www.fda.gov/media/76860/download"
            
            orange_dir = os.path.join(self.data_dir, "orange_book")
            os.makedirs(orange_dir, exist_ok=True)
            
            zip_file = os.path.join(orange_dir, "orange_book.zip")
            
            # Download ZIP file
            self.logger.info("Downloading Orange Book ZIP file...")
            response = await self.session.get(orange_book_url)
            response.raise_for_status()
            
            with open(zip_file, "wb") as f:
                f.write(response.content)
            
            file_size = len(response.content)
            self.stats["total_size_downloaded"] += file_size
            self.logger.info(f"Downloaded Orange Book ZIP: {file_size / 1024 / 1024:.1f} MB")
            
            # Extract ZIP file
            with zipfile.ZipFile(zip_file, "r") as zip_ref:
                zip_ref.extractall(orange_dir)
                extracted_files = zip_ref.namelist()
                self.stats["files_extracted"] += len(extracted_files)
            
            self.logger.info(f"✅ Orange Book extracted: {len(extracted_files)} files")
            
            return {
                "success": True,
                "directory": orange_dir,
                "files_extracted": len(extracted_files),
                "size_mb": file_size / 1024 / 1024
            }
            
        except Exception as e:
            self.logger.error(f"❌ Orange Book download failed: {e}")
            self.stats["errors"].append(f"Orange Book: {e}")
            return {"success": False, "error": str(e)}

    async def download_ndc_directory(self) -> dict[str, Any]:
        """Download FDA NDC Directory"""
        self.logger.info("Downloading FDA NDC Directory...")
        
        try:
            # openFDA NDC directory
            ndc_url = "https://download.open.fda.gov/drug/ndc/drug-ndc-0001-of-0001.json.zip"
            
            ndc_dir = os.path.join(self.data_dir, "ndc_directory")
            os.makedirs(ndc_dir, exist_ok=True)
            
            zip_file = os.path.join(ndc_dir, "ndc_directory.zip")
            
            # Download ZIP file
            self.logger.info("Downloading NDC Directory ZIP file...")
            response = await self.session.get(ndc_url)
            response.raise_for_status()
            
            with open(zip_file, "wb") as f:
                f.write(response.content)
            
            file_size = len(response.content)
            self.stats["total_size_downloaded"] += file_size
            self.logger.info(f"Downloaded NDC Directory ZIP: {file_size / 1024 / 1024:.1f} MB")
            
            # Extract ZIP file
            with zipfile.ZipFile(zip_file, "r") as zip_ref:
                zip_ref.extractall(ndc_dir)
                extracted_files = zip_ref.namelist()
                self.stats["files_extracted"] += len(extracted_files)
            
            self.logger.info(f"✅ NDC Directory extracted: {len(extracted_files)} files")
            
            return {
                "success": True,
                "directory": ndc_dir,
                "files_extracted": len(extracted_files),
                "size_mb": file_size / 1024 / 1024
            }
            
        except Exception as e:
            self.logger.error(f"❌ NDC Directory download failed: {e}")
            self.stats["errors"].append(f"NDC Directory: {e}")
            return {"success": False, "error": str(e)}

    async def download_drugs_fda(self) -> dict[str, Any]:
        """Download Drugs@FDA database"""
        self.logger.info("Downloading Drugs@FDA database...")
        
        try:
            # openFDA Drugs@FDA database
            drugs_fda_url = "https://download.open.fda.gov/drug/drugsfda/drug-drugsfda-0001-of-0001.json.zip"
            
            drugs_dir = os.path.join(self.data_dir, "drugs_fda")
            os.makedirs(drugs_dir, exist_ok=True)
            
            zip_file = os.path.join(drugs_dir, "drugs_fda.zip")
            
            # Download ZIP file
            self.logger.info("Downloading Drugs@FDA ZIP file...")
            response = await self.session.get(drugs_fda_url)
            response.raise_for_status()
            
            with open(zip_file, "wb") as f:
                f.write(response.content)
            
            file_size = len(response.content)
            self.stats["total_size_downloaded"] += file_size
            self.logger.info(f"Downloaded Drugs@FDA ZIP: {file_size / 1024 / 1024:.1f} MB")
            
            # Extract ZIP file
            with zipfile.ZipFile(zip_file, "r") as zip_ref:
                zip_ref.extractall(drugs_dir)
                extracted_files = zip_ref.namelist()
                self.stats["files_extracted"] += len(extracted_files)
            
            self.logger.info(f"✅ Drugs@FDA extracted: {len(extracted_files)} files")
            
            return {
                "success": True,
                "directory": drugs_dir,
                "files_extracted": len(extracted_files),
                "size_mb": file_size / 1024 / 1024
            }
            
        except Exception as e:
            self.logger.error(f"❌ Drugs@FDA download failed: {e}")
            self.stats["errors"].append(f"Drugs@FDA: {e}")
            return {"success": False, "error": str(e)}

    async def download_drug_labels(self) -> dict[str, Any]:
        """Download FDA drug labeling data"""
        self.logger.info("Downloading FDA drug labels (largest dataset)...")
        
        try:
            # Get current download URLs from FDA API
            download_info_response = await self.session.get("https://api.fda.gov/download.json")
            download_info_response.raise_for_status()
            download_info = download_info_response.json()
            
            # Get drug label partitions
            label_partitions = download_info["results"]["drug"]["label"]["partitions"]
            if not label_partitions:
                raise Exception("No drug label partitions available")
            
            labels_dir = os.path.join(self.data_dir, "drug_labels")
            os.makedirs(labels_dir, exist_ok=True)
            
            total_downloaded = 0
            total_files = 0
            
            # Download all partitions (this is where the ~20GB comes from)
            self.logger.info(f"Found {len(label_partitions)} drug label partitions to download")
            
            for i, partition in enumerate(label_partitions, 1):
                try:
                    url = partition["file"]
                    size_mb = partition.get("size_mb", 0)
                    
                    self.logger.info(f"Downloading drug labels partition {i}/{len(label_partitions)} ({size_mb}MB)")
                    
                    response = await self.session.get(url)
                    response.raise_for_status()
                    
                    # Save partition file
                    partition_file = os.path.join(labels_dir, f"drug_labels_part_{i:03d}.zip")
                    with open(partition_file, "wb") as f:
                        f.write(response.content)
                    
                    file_size = len(response.content)
                    total_downloaded += file_size
                    self.stats["total_size_downloaded"] += file_size
                    
                    # Extract partition
                    with zipfile.ZipFile(partition_file, "r") as zip_ref:
                        zip_ref.extractall(os.path.join(labels_dir, f"part_{i:03d}"))
                        extracted_files = zip_ref.namelist()
                        total_files += len(extracted_files)
                        self.stats["files_extracted"] += len(extracted_files)
                    
                    self.logger.info(f"✅ Partition {i} downloaded and extracted: {file_size / 1024 / 1024:.1f} MB")
                    
                    # Small delay between partitions to be respectful
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    self.logger.error(f"❌ Failed to download partition {i}: {e}")
                    self.stats["errors"].append(f"Drug labels partition {i}: {e}")
                    continue
            
            self.logger.info(f"✅ Drug labels complete: {total_downloaded / 1024 / 1024 / 1024:.1f} GB, {total_files} files")
            
            return {
                "success": True,
                "directory": labels_dir,
                "partitions_downloaded": len(label_partitions),
                "files_extracted": total_files,
                "size_gb": total_downloaded / 1024 / 1024 / 1024
            }
            
        except Exception as e:
            self.logger.error(f"❌ Drug labels download failed: {e}")
            self.stats["errors"].append(f"Drug labels: {e}")
            return {"success": False, "error": str(e)}

    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.aclose()

    def get_download_stats(self) -> dict[str, Any]:
        """Get comprehensive download statistics"""
        stats = self.stats.copy()
        
        if stats["start_time"] and stats["end_time"]:
            duration = stats["end_time"] - stats["start_time"]
            stats["duration_seconds"] = duration
            stats["duration_hours"] = duration / 3600
            
            if duration > 0:
                stats["mb_per_second"] = (stats["total_size_downloaded"] / 1024 / 1024) / duration
        
        return stats


def main():
    """Main function for complete FDA download"""
    parser = argparse.ArgumentParser(
        description="Download complete FDA drug databases for offline operation",
        epilog="Uses medical-mirrors configuration for database compatibility"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        help="Directory to store complete FDA data (default: medical-mirrors config)"
    )
    parser.add_argument(
        "--orange-book-only",
        action="store_true",
        help="Download only Orange Book data"
    )
    parser.add_argument(
        "--ndc-only",
        action="store_true",
        help="Download only NDC Directory"
    )
    parser.add_argument(
        "--drugs-fda-only",
        action="store_true",
        help="Download only Drugs@FDA database"
    )
    parser.add_argument(
        "--labels-only",
        action="store_true",
        help="Download only drug labels (largest dataset)"
    )

    args = parser.parse_args()

    # Create downloader with optional custom data directory
    downloader = CompleteFDADownloader(custom_data_dir=args.data_dir)

    print(f"\n💊 Starting complete FDA drug databases download to: {downloader.data_dir}")
    print("⚠️  Target: 4 datasets totaling ~22GB")
    print("🔧 Using medical-mirrors config for database compatibility\n")

    # Run specific or complete download
    async def run_download():
        if args.orange_book_only:
            print("📥 Downloading Orange Book only")
            result = await downloader.download_orange_book()
            return {"status": "success" if result.get("success") else "failed", "results": {"orange_book": result}}
        elif args.ndc_only:
            print("📥 Downloading NDC Directory only")
            result = await downloader.download_ndc_directory()
            return {"status": "success" if result.get("success") else "failed", "results": {"ndc_directory": result}}
        elif args.drugs_fda_only:
            print("📥 Downloading Drugs@FDA only")
            result = await downloader.download_drugs_fda()
            return {"status": "success" if result.get("success") else "failed", "results": {"drugs_fda": result}}
        elif args.labels_only:
            print("📥 Downloading drug labels only (~20GB)")
            result = await downloader.download_drug_labels()
            return {"status": "success" if result.get("success") else "failed", "results": {"drug_labels": result}}
        else:
            print("📥 Downloading complete FDA archive (~22GB)")
            return await downloader.download_complete_archive()

    result = asyncio.run(run_download())

    # Show results
    if isinstance(result, dict) and result.get("status") == "success":
        print("\n✅ FDA download completed successfully!")
        if "datasets_downloaded" in result:
            print(f"   Datasets: {result.get('datasets_downloaded', 'N/A')}/{result.get('total_datasets', 'N/A')}")
        print(f"   Duration: {result.get('duration_hours', 0):.1f} hours")
        if "total_size_gb" in result:
            print(f"   Size: {result.get('total_size_gb', 0):.1f} GB")
    else:
        print("\n❌ FDA download failed or incomplete")
        if isinstance(result, dict) and "error" in result:
            print(f"   Error: {result['error']}")

    # Show download statistics
    stats = downloader.get_download_stats()
    print(f"\n📊 Download Statistics:")
    print(f"   Total downloaded: {stats.get('total_size_downloaded', 0) / 1024 / 1024 / 1024:.1f} GB")
    print(f"   Files extracted: {stats.get('files_extracted', 0)}")
    print(f"   Speed: {stats.get('mb_per_second', 0):.1f} MB/s")
    print(f"   Errors: {len(stats.get('errors', []))}")
    
    # Show next steps
    print(f"\n📋 Next Steps:")
    print(f"   1. Parse downloaded files: python scripts/parse_downloaded_archives.py fda")
    print(f"   2. Or use medical-mirrors API: POST /update/fda")
    print(f"   3. Files stored in: {downloader.data_dir}")

    # Clean up
    asyncio.run(downloader.close())


if __name__ == "__main__":
    main()