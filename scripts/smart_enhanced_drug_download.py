#!/usr/bin/env python3
"""
Smart Enhanced Drug Sources download script - integrates with medical-mirrors system
Orchestrates multiple enhanced drug data sources: DailyMed, ClinicalTrials, FAERS, RxClass, DrugCentral, DDInter, LactMed
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add medical-mirrors src to path
sys.path.append("/home/intelluxe/services/user/medical-mirrors/src")

from enhanced_drug_sources.clinical_trials_downloader import SmartClinicalTrialsDownloader
from enhanced_drug_sources.dailymed_downloader import SmartDailyMedDownloader
from enhanced_drug_sources.ddinter_downloader import SmartDDInterDownloader
from enhanced_drug_sources.drugcentral_downloader import SmartDrugCentralDownloader
from enhanced_drug_sources.lactmed_downloader import SmartLactMedDownloader
from enhanced_drug_sources.openfda_faers_downloader import SmartOpenFDAFAERSDownloader
from enhanced_drug_sources.rxclass_downloader import SmartRxClassDownloader

from config import Config


# Override Config paths for local execution
class LocalConfig(Config):
    def __init__(self):
        super().__init__()
        self.DATA_DIR = "/home/intelluxe/database/medical_complete"
        self.LOGS_DIR = "/home/intelluxe/logs"


class EnhancedDrugSourcesOrchestrator:
    """Orchestrates all enhanced drug data sources"""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.config = LocalConfig()
        self.logger = self._setup_logging()

        # Track results from each source
        self.results = {}
        self.stats = {
            "total_sources": 7,
            "completed_sources": 0,
            "failed_sources": 0,
            "start_time": None,
            "end_time": None,
        }

    def _setup_logging(self) -> logging.Logger:
        """Setup comprehensive logging"""
        logger = logging.getLogger("enhanced_drug_orchestrator")
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    async def download_all_sources(self) -> dict:
        """Download from all enhanced drug sources"""
        self.logger.info("Starting enhanced drug sources download")
        self.stats["start_time"] = datetime.now()

        # Define all sources to download
        sources = [
            ("dailymed", self._download_dailymed),
            ("clinical_trials", self._download_clinical_trials),
            ("openfda_faers", self._download_openfda_faers),
            ("rxclass", self._download_rxclass),
            ("drugcentral", self._download_drugcentral),
            ("ddinter", self._download_ddinter),
            ("lactmed", self._download_lactmed),
        ]

        # Download from all sources
        for source_name, download_func in sources:
            try:
                self.logger.info(f"📥 Starting {source_name} download...")
                result = await download_func()
                self.results[source_name] = result

                if result.get("success", False):
                    self.stats["completed_sources"] += 1
                    self.logger.info(f"✅ {source_name} completed successfully")
                else:
                    self.stats["failed_sources"] += 1
                    self.logger.error(f"❌ {source_name} failed: {result.get('error', 'Unknown error')}")

            except Exception as e:
                self.stats["failed_sources"] += 1
                self.results[source_name] = {"success": False, "error": str(e)}
                self.logger.exception(f"❌ {source_name} failed with exception: {e}")

        self.stats["end_time"] = datetime.now()
        duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()

        # Generate final report
        report = {
            "status": "completed",
            "stats": self.stats,
            "duration_minutes": duration / 60,
            "results": self.results,
            "completion_timestamp": self.stats["end_time"].isoformat(),
        }

        # Save report
        report_file = self.data_dir / f"enhanced_drug_sources_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, default=str)

        self.logger.info("Enhanced drug sources download completed!")
        self.logger.info(f"   Successful: {self.stats['completed_sources']}/{self.stats['total_sources']}")
        self.logger.info(f"   Duration: {duration/60:.1f} minutes")
        self.logger.info(f"   Report saved: {report_file}")

        return report

    async def _download_dailymed(self) -> dict:
        """Download DailyMed drug labeling data"""
        try:
            async with SmartDailyMedDownloader(config=self.config) as downloader:
                result = await downloader.download_enhanced_drug_labeling()
                return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _download_clinical_trials(self) -> dict:
        """Download clinical trials drug data"""
        try:
            async with SmartClinicalTrialsDownloader(config=self.config) as downloader:
                result = await downloader.download_drug_studies()
                return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _download_openfda_faers(self) -> dict:
        """Download OpenFDA FAERS adverse events data"""
        try:
            async with SmartOpenFDAFAERSDownloader(config=self.config) as downloader:
                result = await downloader.download_faers_data()
                return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _download_rxclass(self) -> dict:
        """Download RxClass therapeutic classification data"""
        try:
            async with SmartRxClassDownloader(config=self.config) as downloader:
                result = await downloader.download_classifications()
                return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _download_drugcentral(self) -> dict:
        """Download DrugCentral pharmaceutical data"""
        try:
            async with SmartDrugCentralDownloader(config=self.config) as downloader:
                result = await downloader.download_drug_data()
                return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _download_ddinter(self) -> dict:
        """Download DDInter drug-drug interaction data"""
        try:
            async with SmartDDInterDownloader(config=self.config) as downloader:
                result = await downloader.download_interactions()
                return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _download_lactmed(self) -> dict:
        """Download LactMed breastfeeding safety data"""
        try:
            async with SmartLactMedDownloader(config=self.config) as downloader:
                result = await downloader.download_lactation_data()
                return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}


async def main():
    """Main entry point for enhanced drug sources download"""
    import argparse

    parser = argparse.ArgumentParser(description="Smart Enhanced Drug Sources Downloader")
    parser.add_argument("command", nargs="?", default="download",
                       choices=["download", "status", "reset"],
                       help="Command to execute")
    parser.add_argument("--data-dir", type=Path,
                       default=Path("/home/intelluxe/database/medical_complete/enhanced_drug_sources"),
                       help="Output directory for downloaded data")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    orchestrator = EnhancedDrugSourcesOrchestrator(args.data_dir)

    if args.command == "download":
        print("🧬 Starting Enhanced Drug Sources Download")
        print(f"📁 Output directory: {args.data_dir}")
        print("🔬 Sources: DailyMed, ClinicalTrials, FAERS, RxClass, DrugCentral, DDInter, LactMed")
        print()

        result = await orchestrator.download_all_sources()

        if result["stats"]["completed_sources"] > 0:
            print("\n✅ Enhanced drug sources download completed!")
            print(f"   Successful: {result['stats']['completed_sources']}/{result['stats']['total_sources']}")
            print(f"   Duration: {result['duration_minutes']:.1f} minutes")
        else:
            print("\n❌ Enhanced drug sources download failed")
            print("   No sources completed successfully")
            sys.exit(1)

    elif args.command == "status":
        print("📊 Enhanced drug sources status not yet implemented")

    elif args.command == "reset":
        print("🔄 Enhanced drug sources reset not yet implemented")


if __name__ == "__main__":
    asyncio.run(main())
