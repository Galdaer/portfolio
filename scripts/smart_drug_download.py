#!/usr/bin/env python3
"""
Smart Enhanced Drug Sources Download Script
Orchestrates all 7 enhanced drug source downloaders for comprehensive pharmaceutical data collection

This script coordinates:
1. DailyMed API (FDA Drug Labeling)
2. ClinicalTrials.gov API (Special Populations)
3. OpenFDA FAERS API (Adverse Events)
4. RxClass API (Drug Classifications)
5. DrugCentral PostgreSQL (MOA/Targets)
6. DDInter 2.0 (Drug-Drug Interactions)
7. LactMed NCBI E-utilities (Breastfeeding Safety)

Uses the same configuration and patterns as the medical-mirrors service
for consistency with the existing database schema and architecture.
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add medical-mirrors src to path
medical_mirrors_src = str(Path(__file__).parent.parent / "services/user/medical-mirrors/src")
if medical_mirrors_src not in sys.path:
    sys.path.insert(0, medical_mirrors_src)

try:
    from enhanced_drug_sources.clinical_trials_downloader import SmartClinicalTrialsDownloader
    from enhanced_drug_sources.dailymed_downloader import SmartDailyMedDownloader
    from enhanced_drug_sources.ddinter_downloader import SmartDDInterDownloader
    from enhanced_drug_sources.drugcentral_downloader import SmartDrugCentralDownloader
    from enhanced_drug_sources.lactmed_downloader import SmartLactMedDownloader
    from enhanced_drug_sources.openfda_faers_downloader import SmartOpenFDAFAERSDownloader
    from enhanced_drug_sources.rxclass_downloader import SmartRxClassDownloader

    from config import Config
except ImportError as e:
    print(f"Failed to import enhanced drug sources modules: {e}")
    print("Make sure medical-mirrors service is properly installed")
    print(f"Looking for modules in: {medical_mirrors_src}")
    sys.exit(1)


# Override Config paths for local execution
class LocalConfig(Config):
    def __init__(self):
        super().__init__()
        self.DATA_DIR = "/home/intelluxe/database/medical_complete"
        self.LOGS_DIR = "/home/intelluxe/logs"


class EnhancedDrugDownloadState:
    """State management for enhanced drug downloads"""

    def __init__(self):
        self.successful_sources = 0
        self.failed_sources = 0
        self.rate_limited_sources = 0
        self.total_files_downloaded = 0
        self.start_time = None
        self.end_time = None
        self.completed_sources = set()
        self.source_results = {}
        self.errors = []


class SmartEnhancedDrugDownloader:
    """
    Orchestrates all enhanced drug source downloads with intelligent coordination.

    Manages parallel downloads, rate limiting coordination, progress tracking,
    and error handling across all 7 enhanced pharmaceutical data sources.
    """

    def __init__(self, custom_data_dir: str = None):
        # Use medical-mirrors Config for consistency with local paths
        self.config = LocalConfig()

        # Allow custom data directory override
        if custom_data_dir:
            self.base_data_dir = Path(custom_data_dir)
            self.base_data_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.base_data_dir = Path(self.config.DATA_DIR)

        self.logger = self._setup_logging()
        self.state = EnhancedDrugDownloadState()

        # Define enhanced drug sources with their characteristics
        self.enhanced_sources = {
            "dailymed": {
                "downloader_class": SmartDailyMedDownloader,
                "description": "FDA Drug Labeling (special populations)",
                "priority": 1,
                "max_concurrent": 3,
                "estimated_mb": 15,
                "estimated_minutes": 5,
            },
            "clinical_trials": {
                "downloader_class": SmartClinicalTrialsDownloader,
                "description": "ClinicalTrials.gov Special Populations",
                "priority": 2,
                "max_concurrent": 2,
                "estimated_mb": 25,
                "estimated_minutes": 4,
            },
            "openfda_faers": {
                "downloader_class": SmartOpenFDAFAERSDownloader,
                "description": "OpenFDA FAERS Adverse Events",
                "priority": 3,
                "max_concurrent": 2,
                "estimated_mb": 1,
                "estimated_minutes": 3,
            },
            "rxclass": {
                "downloader_class": SmartRxClassDownloader,
                "description": "RxClass Drug Classifications",
                "priority": 4,
                "max_concurrent": 3,
                "estimated_mb": 1,
                "estimated_minutes": 2,
            },
            "drugcentral": {
                "downloader_class": SmartDrugCentralDownloader,
                "description": "DrugCentral PostgreSQL (MOA/Targets)",
                "priority": 5,
                "max_concurrent": 1,  # Database connection
                "estimated_mb": 11,
                "estimated_minutes": 3,
            },
            "ddinter": {
                "downloader_class": SmartDDInterDownloader,
                "description": "DDInter 2.0 Drug-Drug Interactions",
                "priority": 6,
                "max_concurrent": 1,  # Web scraping
                "estimated_mb": 1,
                "estimated_minutes": 2,
            },
            "lactmed": {
                "downloader_class": SmartLactMedDownloader,
                "description": "LactMed Breastfeeding Safety",
                "priority": 7,
                "max_concurrent": 1,  # NCBI rate limits
                "estimated_mb": 1,
                "estimated_minutes": 2,
            },
        }

    def _setup_logging(self) -> logging.Logger:
        """Setup comprehensive orchestration logging"""
        logger = logging.getLogger("enhanced_drug_downloader")
        logger.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s",
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # File handler for detailed logs
        log_dir = self.base_data_dir / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "enhanced_drug_download.log"

        file_handler = logging.FileHandler(log_file)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        logger.info(f"Enhanced drug download logging to: {log_file}")
        return logger

    def estimate_total_requirements(self) -> dict:
        """Estimate total download requirements for all enhanced sources"""
        total_mb = sum(source["estimated_mb"] for source in self.enhanced_sources.values())
        total_minutes_sequential = sum(source["estimated_minutes"] for source in self.enhanced_sources.values())
        total_minutes_parallel = max(source["estimated_minutes"] for source in self.enhanced_sources.values()) + 5

        return {
            "total_size_mb": total_mb,
            "estimated_minutes_sequential": total_minutes_sequential,
            "estimated_minutes_parallel": total_minutes_parallel,
            "sources_count": len(self.enhanced_sources),
            "database_sources": ["drugcentral"],
            "api_sources": ["dailymed", "clinical_trials", "openfda_faers", "rxclass", "lactmed"],
            "web_scraping_sources": ["ddinter"],
        }

    async def download_source(self, source_name: str, source_info: dict, test_drugs: list = None) -> dict:
        """Download data from a single enhanced drug source"""

        self.logger.info(f"Starting {source_name}: {source_info['description']}")

        try:
            downloader_class = source_info["downloader_class"]
            max_concurrent = source_info["max_concurrent"]

            # Use enhanced_drug_data subdirectory for enhanced sources
            output_dir = self.base_data_dir / "enhanced_drug_data" / source_name

            async with downloader_class(output_dir=output_dir, config=self.config) as downloader:

                if source_name == "drugcentral":
                    # DrugCentral has different interface - downloads all data
                    await downloader.download_mechanism_of_action_data()
                    await downloader.download_drug_target_data()
                    await downloader.download_pharmacology_data()
                    result = await downloader.get_download_summary()

                elif source_name == "dailymed":
                    result = await downloader.download_enhanced_drug_labeling(
                        drug_names=test_drugs,
                        max_concurrent=max_concurrent,
                    )
                elif source_name == "clinical_trials":
                    result = await downloader.download_special_population_studies(
                        drug_names=test_drugs,
                        max_concurrent=max_concurrent,
                    )
                elif source_name == "openfda_faers":
                    result = await downloader.download_special_population_adverse_events(
                        drug_names=test_drugs,
                        max_concurrent=max_concurrent,
                    )
                elif source_name == "rxclass":
                    result = await downloader.download_comprehensive_classifications(
                        drug_names=test_drugs,
                        max_concurrent=max_concurrent,
                    )
                elif source_name == "ddinter":
                    result = await downloader.download_drug_interactions_batch(
                        drug_names=test_drugs,
                        max_concurrent=max_concurrent,
                    )
                elif source_name == "lactmed":
                    result = await downloader.download_lactation_safety_batch(
                        drug_names=test_drugs,
                        max_concurrent=max_concurrent,
                    )
                else:
                    msg = f"Unknown source: {source_name}"
                    raise ValueError(msg)

                files_downloaded = result.get("total_files", 0)
                success_rate = result.get("success_rate", 0)

                self.logger.info(f"✅ {source_name}: {files_downloaded} files, {success_rate:.1f}% success")

                self.state.source_results[source_name] = result
                self.state.completed_sources.add(source_name)
                self.state.successful_sources += 1
                self.state.total_files_downloaded += files_downloaded

                return result

        except Exception as e:
            error_msg = f"Failed to download {source_name}: {e}"
            self.logger.exception(error_msg)
            self.state.errors.append(error_msg)
            self.state.failed_sources += 1
            return {"error": str(e), "total_files": 0, "success_rate": 0}

    async def download_all_enhanced_sources(self,
                                          selected_sources: list = None,
                                          parallel: bool = True,
                                          test_drugs: list = None,
                                          max_parallel: int = 3) -> dict:
        """Download all or selected enhanced drug sources"""

        self.state.start_time = datetime.now()

        # Use default test drug set if none provided
        if not test_drugs:
            test_drugs = [
                "acetaminophen", "ibuprofen", "aspirin", "metformin", "lisinopril",
                "omeprazole", "simvastatin", "levothyroxine", "amlodipine", "metoprolol",
            ]

        # Determine which sources to download
        if selected_sources:
            sources_to_download = {k: v for k, v in self.enhanced_sources.items()
                                 if k in selected_sources}
        else:
            sources_to_download = self.enhanced_sources

        self.logger.info("Starting enhanced drug sources download")
        self.logger.info(f"Sources: {', '.join(sources_to_download.keys())}")
        self.logger.info(f"Test drugs: {test_drugs}")
        self.logger.info(f"Parallel execution: {parallel} (max: {max_parallel})")

        if parallel:
            # Parallel execution with semaphore
            semaphore = asyncio.Semaphore(max_parallel)

            async def download_with_semaphore(source_name, source_info):
                async with semaphore:
                    return await self.download_source(source_name, source_info, test_drugs)

            # Create tasks
            tasks = [
                download_with_semaphore(name, info)
                for name, info in sources_to_download.items()
            ]

            # Execute all downloads
            await asyncio.gather(*tasks, return_exceptions=True)

        else:
            # Sequential execution (safer for debugging)
            for source_name, source_info in sources_to_download.items():
                await self.download_source(source_name, source_info, test_drugs)

        self.state.end_time = datetime.now()

        return await self.get_final_summary()

    async def get_final_summary(self) -> dict:
        """Generate comprehensive final summary"""

        duration = None
        if self.state.start_time and self.state.end_time:
            duration = (self.state.end_time - self.state.start_time).total_seconds()

        # Calculate total file sizes
        total_size_mb = 0
        for source_result in self.state.source_results.values():
            if "download_stats" in source_result:
                total_size_mb += source_result["download_stats"].get("total_size_mb", 0)

        return {
            "summary": {
                "total_sources": len(self.enhanced_sources),
                "successful_sources": self.state.successful_sources,
                "failed_sources": self.state.failed_sources,
                "success_rate": (self.state.successful_sources / len(self.enhanced_sources)) * 100,
                "total_files_downloaded": self.state.total_files_downloaded,
                "total_size_mb": round(total_size_mb, 2),
                "duration_seconds": round(duration, 1) if duration else None,
            },
            "by_source": self.state.source_results,
            "completed_sources": list(self.state.completed_sources),
            "errors": self.state.errors,
            "requirements_met": {
                "all_sources_attempted": True,
                "majority_successful": self.state.successful_sources >= (len(self.enhanced_sources) * 0.7),
                "critical_sources_working": all(s in self.state.completed_sources
                                              for s in ["dailymed", "drugcentral"]),
            },
        }

    async def get_status(self) -> dict:
        """Get current download status"""
        return {
            "timestamp": datetime.now().isoformat(),
            "sources_completed": len(self.state.completed_sources),
            "sources_total": len(self.enhanced_sources),
            "files_downloaded": self.state.total_files_downloaded,
            "successful_sources": self.state.successful_sources,
            "failed_sources": self.state.failed_sources,
            "errors_count": len(self.state.errors),
            "currently_running": self.state.start_time is not None and self.state.end_time is None,
        }


async def main():
    """Main entry point for enhanced drug sources download orchestration"""

    parser = argparse.ArgumentParser(
        description="Enhanced Drug Sources Download Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s download                    # Download all enhanced drug sources
  %(prog)s download --sources dailymed,rxclass  # Download specific sources
  %(prog)s status                      # Show current status
  %(prog)s test                        # Quick test of all sources

Enhanced Drug Sources:
  dailymed         - FDA Drug Labeling (special populations)
  clinical_trials  - ClinicalTrials.gov Special Populations
  openfda_faers    - OpenFDA FAERS Adverse Events
  rxclass          - RxClass Drug Classifications
  drugcentral      - DrugCentral PostgreSQL (MOA/Targets)
  ddinter          - DDInter 2.0 Drug-Drug Interactions
  lactmed          - LactMed Breastfeeding Safety
        """,
    )

    parser.add_argument("command", nargs="?", default="download",
                       choices=["download", "status", "test", "estimate"],
                       help="Command to execute")
    parser.add_argument("--data-dir", type=Path,
                       default=Path("/home/intelluxe/database/medical_complete"),
                       help="Output directory for downloaded data")
    parser.add_argument("--sources", type=str,
                       help="Comma-separated list of sources to download")
    parser.add_argument("--sequential", action="store_true",
                       help="Download sources sequentially (safer, slower)")
    parser.add_argument("--max-parallel", type=int, default=3,
                       help="Maximum parallel downloads")
    parser.add_argument("--test-drugs", type=str,
                       help="Comma-separated list of test drugs")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Parse arguments
    selected_sources = None
    if args.sources:
        selected_sources = [s.strip() for s in args.sources.split(",")]

    test_drugs = None
    if args.test_drugs:
        test_drugs = [d.strip() for d in args.test_drugs.split(",")]

    # Initialize orchestrator
    orchestrator = SmartEnhancedDrugDownloader(str(args.data_dir))

    try:
        if args.command == "estimate":
            # Show requirements estimate
            requirements = orchestrator.estimate_total_requirements()
            print("\n📊 Enhanced Drug Sources Requirements Estimate:")
            print(f"   • Total sources: {requirements['sources_count']}")
            print(f"   • Estimated size: {requirements['total_size_mb']} MB")
            print(f"   • Sequential time: {requirements['estimated_minutes_sequential']} minutes")
            print(f"   • Parallel time: {requirements['estimated_minutes_parallel']} minutes")
            print(f"   • API sources: {len(requirements['api_sources'])}")
            print(f"   • Database sources: {len(requirements['database_sources'])}")
            print(f"   • Web scraping sources: {len(requirements['web_scraping_sources'])}")

        elif args.command == "status":
            # Show current status
            status = await orchestrator.get_status()
            print("\n📈 Enhanced Drug Sources Status:")
            print(f"   • Sources completed: {status['sources_completed']}/{status['sources_total']}")
            print(f"   • Files downloaded: {status['files_downloaded']}")
            print(f"   • Successful sources: {status['successful_sources']}")
            print(f"   • Failed sources: {status['failed_sources']}")
            print(f"   • Currently running: {status['currently_running']}")

        elif args.command == "test":
            # Quick test with minimal data
            test_drugs = ["aspirin", "ibuprofen", "acetaminophen"]
            print(f"\n🧪 Testing all enhanced drug sources with drugs: {test_drugs}")

            result = await orchestrator.download_all_enhanced_sources(
                selected_sources=selected_sources,
                parallel=not args.sequential,
                test_drugs=test_drugs,
                max_parallel=args.max_parallel,
            )

            summary = result["summary"]
            print("\n📊 Test Results Summary:")
            print(f"   • Sources tested: {summary['total_sources']}")
            print(f"   • Successful: {summary['successful_sources']}")
            print(f"   • Failed: {summary['failed_sources']}")
            print(f"   • Success rate: {summary['success_rate']:.1f}%")
            print(f"   • Files downloaded: {summary['total_files_downloaded']}")
            print(f"   • Total size: {summary['total_size_mb']} MB")
            if summary["duration_seconds"]:
                print(f"   • Duration: {summary['duration_seconds']:.1f} seconds")

        else:
            # Full download
            print("\n🚀 Starting Enhanced Drug Sources Download...")

            result = await orchestrator.download_all_enhanced_sources(
                selected_sources=selected_sources,
                parallel=not args.sequential,
                test_drugs=test_drugs,
                max_parallel=args.max_parallel,
            )

            summary = result["summary"]
            print("\n🎉 Download Complete!")
            print(f"   • Total sources: {summary['total_sources']}")
            print(f"   • Successful: {summary['successful_sources']}")
            print(f"   • Failed: {summary['failed_sources']}")
            print(f"   • Success rate: {summary['success_rate']:.1f}%")
            print(f"   • Total files: {summary['total_files_downloaded']}")
            print(f"   • Total size: {summary['total_size_mb']} MB")
            if summary["duration_seconds"]:
                print(f"   • Duration: {summary['duration_seconds']:.1f} seconds")

            # Show any errors
            if result["errors"]:
                print("\n❌ Errors encountered:")
                for error in result["errors"]:
                    print(f"   • {error}")

            # Determine exit code
            requirements_met = result["requirements_met"]
            if requirements_met["majority_successful"] and requirements_met["critical_sources_working"]:
                print("\n✅ Enhanced drug sources download completed successfully!")
                return 0
            print("\n⚠️  Enhanced drug sources download completed with issues.")
            return 1

    except KeyboardInterrupt:
        print("\n⏹️  Download interrupted by user")
        return 130

    except Exception as e:
        print(f"\n❌ Download failed with error: {e}")
        orchestrator.logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
