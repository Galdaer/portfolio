#!/usr/bin/env python3
"""
Full Medical Archives Download Strategy
Downloads complete historical datasets for comprehensive medical AI training
"""

import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import requests


@dataclass
class DownloadConfig:
    """Configuration for full medical data downloads"""
    base_dir: Path
    max_workers: int = 8
    verify_checksums: bool = True
    resume_downloads: bool = True

class FullMedicalDownloader:
    """Downloads complete medical archives for comprehensive AI training"""

    def __init__(self, config: DownloadConfig):
        self.config = config
        self.logger = self._setup_logging()

    def _setup_logging(self) -> logging.Logger:
        """Setup comprehensive download logging"""
        logger = logging.getLogger("full_medical_downloader")
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def estimate_full_download_sizes(self) -> dict[str, dict[str, str]]:
        """Estimate sizes for complete medical archives"""
        return {
            "pubmed_complete": {
                "baseline_files": "~1,219 files x ~100MB = ~120GB",
                "update_files": "~2,000 files x ~50MB = ~100GB",
                "total": "~220GB (complete PubMed corpus)",
                "articles": "~36 million articles (1946-present)",
                "value": "Complete medical literature - ESSENTIAL for medical AI",
            },
            "clinicaltrials_complete": {
                "all_studies": "~450,000 studies x ~1MB = ~450MB",
                "total": "~500MB (all ClinicalTrials.gov data)",
                "studies": "All trials since 1999 with results",
                "value": "Treatment outcomes & efficacy data - CRITICAL for evidence-based medicine",
            },
            "fda_complete": {
                "drug_labels": "13 files x ~1.5GB = ~20GB",
                "orange_book": "~100MB",
                "ndc_directory": "~500MB",
                "drugs_fda": "~1GB",
                "total": "~22GB (complete FDA drug database)",
                "value": "Complete drug safety & prescribing information",
            },
            "grand_total": {
                "estimated_size": "~242GB",
                "vs_current": "Current ~15GB vs Full ~242GB",
                "medical_coverage": "Complete vs Partial medical knowledge",
            },
        }

    def download_complete_pubmed(self) -> bool:
        """Download complete PubMed baseline + updates"""
        self.logger.info("Starting complete PubMed download...")

        pubmed_dir = self.config.base_dir / "pubmed_complete"
        pubmed_dir.mkdir(parents=True, exist_ok=True)

        # Download baseline files (complete corpus)
        baseline_success = self._download_pubmed_baseline(pubmed_dir)

        # Download all update files
        updates_success = self._download_pubmed_updates(pubmed_dir)

        return baseline_success and updates_success

    def _download_pubmed_baseline(self, pubmed_dir: Path) -> bool:
        """Download all PubMed baseline files (~1,219 files, ~120GB)"""
        self.logger.info("Downloading PubMed baseline corpus...")

        # Get list of all baseline files
        baseline_url = "https://ftp.ncbi.nlm.nih.gov/pubmed/baseline/"

        try:
            response = requests.get(baseline_url)
            response.raise_for_status()

            # Parse FTP directory listing to get all .xml.gz files
            baseline_files = self._parse_ftp_directory(response.text, ".xml.gz")

            self.logger.info(f"Found {len(baseline_files)} baseline files to download")

            # Download files in parallel
            with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                futures = []
                for filename in baseline_files:
                    file_url = f"{baseline_url}{filename}"
                    local_path = pubmed_dir / "baseline" / filename
                    local_path.parent.mkdir(parents=True, exist_ok=True)

                    future = executor.submit(self._download_file, file_url, local_path)
                    futures.append(future)

                # Wait for all downloads
                success_count = sum(1 for future in futures if future.result())

            self.logger.info(f"Downloaded {success_count}/{len(baseline_files)} baseline files")
            return success_count == len(baseline_files)

        except Exception as e:
            self.logger.exception(f"Failed to download PubMed baseline: {e}")
            return False

    def download_complete_clinicaltrials(self) -> bool:
        """Download ALL ClinicalTrials.gov studies with results"""
        self.logger.info("Starting complete ClinicalTrials download...")

        trials_dir = self.config.base_dir / "clinicaltrials_complete"
        trials_dir.mkdir(parents=True, exist_ok=True)

        # Use bulk download API for all studies
        api_url = "https://clinicaltrials.gov/api/v2/studies"

        try:
            # Download all studies with results (completed trials)
            params = {
                "format": "json",
                "markupFormat": "markdown",
                "countTotal": "true",
                "pageSize": 1000,  # Maximum page size
                "filter.overallStatus": ["COMPLETED", "TERMINATED", "WITHDRAWN"],
                "filter.hasResults": "true",  # Only studies with results
            }

            all_studies = []
            page = 1

            while True:
                params["pageToken"] = page
                response = requests.get(api_url, params=params)
                response.raise_for_status()

                data = response.json()
                studies = data.get("studies", [])

                if not studies:
                    break

                all_studies.extend(studies)
                self.logger.info(f"Downloaded page {page}, total studies: {len(all_studies)}")

                # Check if we have more pages
                if len(studies) < params["pageSize"]:
                    break

                page += 1

            # Save complete dataset
            import json
            output_file = trials_dir / "all_completed_trials_with_results.json"
            with open(output_file, "w") as f:
                json.dump(all_studies, f, indent=2)

            self.logger.info(f"Downloaded {len(all_studies)} completed trials with results")
            return True

        except Exception as e:
            self.logger.exception(f"Failed to download complete ClinicalTrials: {e}")
            return False

    def download_complete_fda(self) -> bool:
        """Download ALL FDA drug data files"""
        self.logger.info("Starting complete FDA download...")

        fda_dir = self.config.base_dir / "fda_complete"
        fda_dir.mkdir(parents=True, exist_ok=True)

        # Download all drug label files (13 files)
        labels_success = self._download_all_drug_labels(fda_dir)

        # Download complete Orange Book
        orange_success = self._download_complete_orange_book(fda_dir)

        # Download complete NDC Directory
        ndc_success = self._download_complete_ndc(fda_dir)

        # Download complete Drugs@FDA
        drugs_success = self._download_complete_drugs_fda(fda_dir)

        return all([labels_success, orange_success, ndc_success, drugs_success])

    def _download_all_drug_labels(self, fda_dir: Path) -> bool:
        """Download all 13 drug label files (~20GB total)"""
        self.logger.info("Downloading all FDA drug labels...")

        labels_dir = fda_dir / "drug_labels"
        labels_dir.mkdir(parents=True, exist_ok=True)

        # All 13 drug label files
        label_files = [
            "prescription_2009.zip",
            "prescription_2010.zip",
            "prescription_2011.zip",
            "prescription_2012.zip",
            "prescription_2013.zip",
            "prescription_2014.zip",
            "prescription_2015.zip",
            "prescription_2016.zip",
            "prescription_2017.zip",
            "prescription_2018.zip",
            "prescription_2019.zip",
            "prescription_2020.zip",
            "prescription_current.zip",
        ]

        base_url = "https://download.fda.gov/Drugs/DrugsfDALabel/"

        with ThreadPoolExecutor(max_workers=4) as executor:  # Fewer workers for large files
            futures = []
            for filename in label_files:
                file_url = f"{base_url}{filename}"
                local_path = labels_dir / filename

                future = executor.submit(self._download_file, file_url, local_path)
                futures.append(future)

            success_count = sum(1 for future in futures if future.result())

        self.logger.info(f"Downloaded {success_count}/{len(label_files)} drug label files")
        return success_count == len(label_files)

    def _download_file(self, url: str, local_path: Path) -> bool:
        """Download a single file with resume support"""
        try:
            # Check if file already exists and get size
            resume_pos = 0
            if local_path.exists() and self.config.resume_downloads:
                resume_pos = local_path.stat().st_size

            headers = {}
            if resume_pos > 0:
                headers["Range"] = f"bytes={resume_pos}-"

            try:
                response = requests.get(url, headers=headers, stream=True)
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 416:
                    # Range not satisfiable - file may have changed, restart download
                    self.logger.warning(f"Resume failed for {local_path.name}, restarting download")
                    if local_path.exists():
                        local_path.unlink()  # Delete partial file
                    resume_pos = 0
                    headers = {}
                    response = requests.get(url, headers=headers, stream=True)
                    response.raise_for_status()
                else:
                    raise

            # Open file in append mode if resuming
            mode = "ab" if resume_pos > 0 else "wb"

            with open(local_path, mode) as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            self.logger.info(f"Downloaded: {local_path.name}")
            return True

        except Exception as e:
            self.logger.exception(f"Failed to download {url}: {e}")
            return False

    def _download_pubmed_updates(self, pubmed_dir: Path) -> bool:
        """Download all PubMed update files (~2,000 files, ~100GB)"""
        self.logger.info("Downloading PubMed update files...")
        
        updates_dir = pubmed_dir / "updates"
        updates_dir.mkdir(parents=True, exist_ok=True)
        
        # Get list of all update files
        updates_url = "https://ftp.ncbi.nlm.nih.gov/pubmed/updatefiles/"
        
        try:
            response = requests.get(updates_url)
            response.raise_for_status()
            
            # Parse FTP directory listing to get all .xml.gz files
            update_files = self._parse_ftp_directory(response.text, ".xml.gz")
            
            self.logger.info(f"Found {len(update_files)} update files to download")
            
            # Download files in parallel
            with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                futures = []
                for filename in update_files:
                    file_url = f"{updates_url}{filename}"
                    local_path = updates_dir / filename
                    
                    future = executor.submit(self._download_file, file_url, local_path)
                    futures.append(future)
                
                # Wait for all downloads
                success_count = sum(1 for future in futures if future.result())
            
            self.logger.info(f"Downloaded {success_count}/{len(update_files)} update files")
            return success_count == len(update_files)
            
        except Exception as e:
            self.logger.exception(f"Failed to download PubMed updates: {e}")
            return False

    def _download_complete_orange_book(self, fda_dir: Path) -> bool:
        """Download complete FDA Orange Book data"""
        self.logger.info("Downloading complete FDA Orange Book...")
        
        orange_dir = fda_dir / "orange_book"
        orange_dir.mkdir(parents=True, exist_ok=True)
        
        # FDA Orange Book download URL
        orange_book_url = "https://www.fda.gov/media/76860/download"
        local_path = orange_dir / "orange_book.zip"
        
        try:
            success = self._download_file(orange_book_url, local_path)
            
            if success:
                # Extract the ZIP file
                import zipfile
                with zipfile.ZipFile(local_path, 'r') as zip_ref:
                    zip_ref.extractall(orange_dir)
                self.logger.info("Orange Book extracted successfully")
                
            return success
            
        except Exception as e:
            self.logger.exception(f"Failed to download Orange Book: {e}")
            return False

    def _download_complete_ndc(self, fda_dir: Path) -> bool:
        """Download complete FDA NDC Directory"""
        self.logger.info("Downloading complete FDA NDC Directory...")
        
        ndc_dir = fda_dir / "ndc_directory"
        ndc_dir.mkdir(parents=True, exist_ok=True)
        
        # FDA NDC Directory from openFDA
        ndc_url = "https://download.open.fda.gov/drug/ndc/drug-ndc-0001-of-0001.json.zip"
        local_path = ndc_dir / "ndc_directory.zip"
        
        try:
            success = self._download_file(ndc_url, local_path)
            
            if success:
                # Extract the ZIP file
                import zipfile
                with zipfile.ZipFile(local_path, 'r') as zip_ref:
                    zip_ref.extractall(ndc_dir)
                self.logger.info("NDC Directory extracted successfully")
                
            return success
            
        except Exception as e:
            self.logger.exception(f"Failed to download NDC Directory: {e}")
            return False

    def _download_complete_drugs_fda(self, fda_dir: Path) -> bool:
        """Download complete Drugs@FDA database"""
        self.logger.info("Downloading complete Drugs@FDA database...")
        
        drugs_dir = fda_dir / "drugs_fda"
        drugs_dir.mkdir(parents=True, exist_ok=True)
        
        # Drugs@FDA from openFDA
        drugs_url = "https://download.open.fda.gov/drug/drugsfda/drug-drugsfda-0001-of-0001.json.zip"
        local_path = drugs_dir / "drugs_fda.zip"
        
        try:
            success = self._download_file(drugs_url, local_path)
            
            if success:
                # Extract the ZIP file
                import zipfile
                with zipfile.ZipFile(local_path, 'r') as zip_ref:
                    zip_ref.extractall(drugs_dir)
                self.logger.info("Drugs@FDA database extracted successfully")
                
            return success
            
        except Exception as e:
            self.logger.exception(f"Failed to download Drugs@FDA: {e}")
            return False

    def _parse_ftp_directory(self, html_content: str, extension: str) -> list[str]:
        """Parse FTP directory listing to get files with specific extension"""
        import re

        # Find all links ending with the specified extension
        pattern = rf'href="([^"]*{re.escape(extension)})"'
        return re.findall(pattern, html_content)


def main():
    """Main function to run complete medical data downloads"""
    import argparse

    parser = argparse.ArgumentParser(description="Download complete medical archives")
    parser.add_argument("--data-dir", default="/home/intelluxe/data/medical_complete",
                        help="Directory to store complete medical data")
    parser.add_argument("--estimate-only", action="store_true",
                        help="Only show size estimates, don't download")
    parser.add_argument("--pubmed-only", action="store_true",
                        help="Download only complete PubMed data")
    parser.add_argument("--clinicaltrials-only", action="store_true",
                        help="Download only complete ClinicalTrials data")
    parser.add_argument("--fda-only", action="store_true",
                        help="Download only complete FDA data")

    args = parser.parse_args()

    config = DownloadConfig(
        base_dir=Path(args.data_dir),
        max_workers=8,
        verify_checksums=True,
        resume_downloads=True,
    )

    downloader = FullMedicalDownloader(config)

    if args.estimate_only:
        estimates = downloader.estimate_full_download_sizes()
        print("\n=== COMPLETE MEDICAL ARCHIVES SIZE ESTIMATES ===\n")

        for dataset, info in estimates.items():
            print(f"📊 {dataset.upper()}:")
            for key, value in info.items():
                print(f"   {key}: {value}")
            print()

        return

    # Create data directory
    config.base_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n🏥 Starting complete medical data downloads to: {config.base_dir}")
    print("⚠️  WARNING: This will download ~242GB of medical data")
    print("💾 Ensure you have sufficient disk space before proceeding\n")

    # Download based on arguments
    if args.pubmed_only:
        success = downloader.download_complete_pubmed()
    elif args.clinicaltrials_only:
        success = downloader.download_complete_clinicaltrials()
    elif args.fda_only:
        success = downloader.download_complete_fda()
    else:
        # Download everything
        pubmed_success = downloader.download_complete_pubmed()
        trials_success = downloader.download_complete_clinicaltrials()
        fda_success = downloader.download_complete_fda()

        success = all([pubmed_success, trials_success, fda_success])

    if success:
        print("\n✅ Complete medical data download finished successfully!")
    else:
        print("\n❌ Some downloads failed. Check logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
