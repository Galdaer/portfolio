"""
Smart ICD-10 Codes Downloader with automatic rate limit handling and recovery
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

# No parser import - this is a DOWNLOADER, not a parser
from config import Config

from .cms_icd10_downloader import CMSICD10Downloader
from .download_state_manager import DownloadStatus, ICD10DownloadStateManager
from .downloader import ICD10Downloader

logger = logging.getLogger(__name__)


class SmartICD10Downloader:
    """Smart downloader that coordinates multiple ICD-10 sources with rate limit handling"""

    def __init__(self, output_dir: Path | None = None, config: Config | None = None):
        self.config = config or Config()
        self.output_dir = output_dir or Path("/home/intelluxe/database/medical_complete/icd10")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.state_manager = ICD10DownloadStateManager()

        # Download sources
        self.cms_downloader: CMSICD10Downloader | None = None
        self.nlm_downloader: ICD10Downloader | None = None

        # Smart retry configuration
        self.max_concurrent_sources = 2  # More conservative for ICD-10
        self.retry_interval = 600  # 10 minutes between retry checks
        self.max_daily_retries = 12  # Max retries per source per day

        # Results tracking - track downloaded files, NOT parsed codes
        self.downloaded_files: dict[str, str] = {}  # source -> file_path
        self.all_codes: dict[str, list[Any]] = {}  # source -> codes list
        self.total_files_downloaded = 0

    async def __aenter__(self):
        """Async context manager entry"""
        self.cms_downloader = CMSICD10Downloader(self.state_manager, self.output_dir)
        await self.cms_downloader.__aenter__()

        self.nlm_downloader = ICD10Downloader(self.config)
        await self.nlm_downloader.__aenter__()

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.cms_downloader:
            await self.cms_downloader.__aexit__(exc_type, exc_val, exc_tb)
        if self.nlm_downloader:
            await self.nlm_downloader.__aexit__(exc_type, exc_val, exc_tb)

    async def _process_existing_zip_files(self):
        """Process any existing ZIP files that haven't been parsed yet"""
        logger.info("Checking for existing ICD-10 ZIP files to process")
        
        cms_sources = ["cms_icd10_cm_2025", "cms_icd10_cm_2024", "cdc_icd10_cm_2025", "cdc_icd10_cm_2025_april", "cdc_icd10_cm_tabular_2025", "cdc_icd10_cm_tabular_2025_april"]
        processed_count = 0
        
        for source in cms_sources:
            zip_file = self.output_dir / f"{source}.zip"
            if zip_file.exists() and source not in self.all_codes:
                try:
                    logger.info(f"Processing existing ICD-10 ZIP file: {zip_file}")
                    with open(zip_file, 'rb') as f:
                        content = f.read()
                    
                    # Parse ZIP file to extract codes
                    parsed_codes = self.cms_downloader._parse_icd10_zip(content, source)
                    
                    if parsed_codes:
                        self.all_codes[source] = parsed_codes
                        processed_count += 1
                        logger.info(f"Processed existing ICD-10 ZIP file {source}: {len(parsed_codes)} codes extracted")
                    else:
                        logger.warning(f"No ICD-10 codes extracted from existing ZIP file: {source}")
                        
                except Exception as e:
                    logger.error(f"Failed to process existing ICD-10 ZIP file {source}: {e}")
        
        if processed_count > 0:
            logger.info(f"Successfully processed {processed_count} existing ICD-10 ZIP files")
        else:
            logger.info("No existing ICD-10 ZIP files found to process")

    async def download_all_icd10_codes(self, force_fresh: bool = False) -> dict[str, Any]:
        """
        Download all ICD-10 codes from all sources with smart retry handling

        Args:
            force_fresh: If True, reset all download states and start fresh

        Returns:
            Summary of download results including totals and source breakdown
        """
        logger.info("Starting smart ICD-10 codes download process")

        if force_fresh:
            logger.info("Force fresh download - resetting all ICD-10 states")
            self._reset_all_states()

        # Process existing ZIP files that might not have been parsed yet
        await self._process_existing_zip_files()

        # Get initial progress
        initial_progress = self.state_manager.get_progress_summary()
        logger.info(f"Initial ICD-10 state: {initial_progress['completed']}/{initial_progress['total_sources']} sources completed")

        # Plan download strategy
        download_plan = await self._create_download_plan()
        logger.info(f"ICD-10 download plan: {len(download_plan['immediate'])} immediate, "
                   f"{len(download_plan['retry_ready'])} ready for retry, "
                   f"{len(download_plan['rate_limited'])} rate limited")

        # Execute downloads
        results = await self._execute_smart_downloads(download_plan)

        # Save download summary
        await self._save_download_summary()

        # Generate final summary
        final_summary = self._generate_final_summary(results)

        logger.info(f"Smart ICD-10 download completed: {final_summary['total_files']} files from "
                   f"{final_summary['successful_sources']} sources")

        return final_summary

    async def _create_download_plan(self) -> dict[str, list[str]]:
        """Create intelligent download plan based on current states"""
        plan = {
            "immediate": [],      # Sources ready to download immediately
            "retry_ready": [],    # Sources ready for retry
            "rate_limited": [],   # Sources currently rate limited
            "completed": [],      # Sources already completed
            "failed": [],          # Sources that have failed too many times
        }

        # Define all possible ICD-10 sources (prioritize CDC official sources)
        all_sources = [
            # CDC Official Sources (Primary - Complete detailed codes)
            "cdc_icd10_cm_2025_april",  # Most recent update
            "cdc_icd10_cm_2025",
            "cdc_icd10_cm_tabular_2025_april",
            "cdc_icd10_cm_tabular_2025",
            "cdc_icd10_cm_2024",
            "cdc_icd10_cm_tabular_2024",

            # CMS Secondary Sources (Category codes only)
            "cms_icd10_cm_2026",
            "cms_icd10_cm_2025",
            "cms_icd10_cm_2024",

            # API Fallbacks
            "nlm_icd10_api",
            "fallback_codes",
        ]

        now = datetime.now()

        for source in all_sources:
            state = self.state_manager.get_state(source)

            if not state:
                # New source - add to immediate
                plan["immediate"].append(source)
                continue

            if state.status == DownloadStatus.COMPLETED:
                plan["completed"].append(source)
                continue

            if state.status == DownloadStatus.FAILED:
                if state.retry_count >= self.max_daily_retries:
                    plan["failed"].append(source)
                    continue

            if state.status in [DownloadStatus.RATE_LIMITED, DownloadStatus.FAILED]:
                if state.next_retry:
                    try:
                        retry_time = datetime.fromisoformat(state.next_retry)
                        if now >= retry_time:
                            plan["retry_ready"].append(source)
                        else:
                            plan["rate_limited"].append(source)
                    except Exception:
                        # Can't parse retry time, assume ready
                        plan["retry_ready"].append(source)
                else:
                    plan["retry_ready"].append(source)
                continue

            # Default to immediate for other statuses
            plan["immediate"].append(source)

        return plan

    async def _execute_smart_downloads(self, plan: dict[str, list[str]]) -> dict[str, Any]:
        """Execute downloads according to the plan"""
        results = {
            "successful": [],
            "failed": [],
            "rate_limited": [],
            "completed": 0,
            "total_codes": 0,
            "sources_attempted": 0,
        }

        # Process immediate and retry-ready sources
        active_sources = plan["immediate"] + plan["retry_ready"]

        if not active_sources:
            logger.info("No ICD-10 sources need downloading")
            # Load existing completed results
            await self._load_existing_files()
            results["total_codes"] = sum(len(codes) for codes in self.all_codes.values())
            return results

        # Limit concurrent downloads (ICD-10 sources can be large)
        semaphore = asyncio.Semaphore(self.max_concurrent_sources)

        # Create download tasks
        download_tasks = []
        for source in active_sources[:self.max_concurrent_sources]:  # Limit initial batch
            task = asyncio.create_task(self._download_single_source(source, semaphore))
            download_tasks.append((source, task))

        # Wait for initial batch
        for source, task in download_tasks:
            try:
                success = await task
                results["sources_attempted"] += 1

                if success:
                    results["successful"].append(source)
                    results["completed"] += 1
                    logger.info(f"Successfully completed ICD-10 download for {source}")
                else:
                    state = self.state_manager.get_state(source)
                    if state and state.status == DownloadStatus.RATE_LIMITED:
                        results["rate_limited"].append(source)
                        logger.warning(f"Rate limited: ICD-10 {source}")
                    else:
                        results["failed"].append(source)
                        logger.error(f"Failed to download ICD-10: {source}")

            except Exception as e:
                logger.exception(f"Unexpected error downloading ICD-10 {source}: {e}")
                results["failed"].append(source)

        # Calculate total files downloaded
        results["total_files"] = len(self.downloaded_files)
        self.total_files_downloaded = results["total_files"]

        return results

    async def _download_single_source(self, source: str, semaphore: asyncio.Semaphore) -> bool:
        """Download from a single ICD-10 source with rate limit handling"""
        async with semaphore:
            try:
                logger.info(f"Starting ICD-10 download for source: {source}")

                if source.startswith(("cms_", "cdc_", "who_")):
                    return await self._download_cms_who_source(source)
                if source.startswith("nlm_"):
                    return await self._download_nlm_source(source)
                if source == "fallback_codes":
                    return await self._download_fallback_source()
                logger.error(f"Unknown ICD-10 source type: {source}")
                return False

            except Exception as e:
                logger.exception(f"Error downloading ICD-10 {source}: {e}")
                self.state_manager.mark_failed(source, str(e))
                return False

    async def _download_cms_who_source(self, source: str) -> bool:
        """Download raw file from CDC, CMS, or WHO source - NO PARSING"""
        try:
            # Map source names to CDC/CMS URLs
            source_mapping = {
                # CDC Official Sources
                "cdc_icd10_cm_2025_april": "cdc_icd10_cm_2025_april",
                "cdc_icd10_cm_2025": "cdc_icd10_cm_2025",
                "cdc_icd10_cm_tabular_2025_april": "cdc_icd10_cm_tabular_2025_april",
                "cdc_icd10_cm_tabular_2025": "cdc_icd10_cm_tabular_2025",
                "cdc_icd10_cm_2024": "cdc_icd10_cm_2024",
                "cdc_icd10_cm_tabular_2024": "cdc_icd10_cm_tabular_2024",

                # CMS Secondary Sources
                "cms_icd10_cm_2026": "cms_icd10_cm_2026",
                "cms_icd10_cm_2025": "cms_icd10_cm_2025",
                "cms_icd10_cm_2024": "cms_icd10_cm_2024",
            }

            cms_source = source_mapping.get(source)
            if not cms_source:
                logger.error(f"Unknown CMS/WHO source: {source}")
                return False

            # Download just this specific source
            if not self.cms_downloader or not hasattr(self.cms_downloader, "CMS_URLS"):
                logger.error("CMS ICD-10 downloader not properly initialized")
                return False

            url = self.cms_downloader.CMS_URLS.get(cms_source)
            if not url:
                logger.error(f"No URL found for ICD-10 source: {cms_source}")
                return False

            # Download raw content and save to file
            if not hasattr(self.cms_downloader, "_download_with_retry"):
                logger.error("CMS ICD-10 downloader missing _download_with_retry method")
                return False

            content = await self.cms_downloader._download_with_retry(url, source)
            if not content:
                return False

            # Save raw file and parse it
            output_file = self.output_dir / f"{source}.zip"
            try:
                with open(output_file, "wb") as f:
                    f.write(content)

                # Parse ZIP file to extract codes
                logger.info(f"Parsing ICD-10 ZIP file for {source}")
                parsed_codes = self.cms_downloader._parse_icd10_zip(content, source)
                
                if parsed_codes:
                    self.all_codes[source] = parsed_codes
                    logger.info(f"Extracted {len(parsed_codes)} ICD-10 codes from {source}")
                else:
                    logger.warning(f"No ICD-10 codes extracted from {source} ZIP file")

                self.downloaded_files[source] = str(output_file)
                self.state_manager.mark_completed(source, output_file.stat().st_size)
                logger.info(f"Downloaded and processed ICD-10 file {output_file} ({len(content)} bytes) from {source}")
                return True

            except Exception as e:
                logger.exception(f"Failed to save ICD-10 file {output_file}: {e}")
                self.state_manager.mark_failed(source, f"Failed to save file: {e}")
                return False

        except Exception as e:
            logger.exception(f"Error downloading CMS/WHO source {source}: {e}")
            self.state_manager.mark_failed(source, str(e))
            return False

    async def _download_nlm_source(self, source: str) -> bool:
        """Download raw JSON from NLM API source - NO PARSING"""
        try:
            if source == "nlm_icd10_api":
                # Download raw JSON response from NLM API
                if not self.nlm_downloader or not hasattr(self.nlm_downloader, "download_raw_json"):
                    logger.error("NLM ICD-10 downloader not properly initialized or missing download_raw_json method")
                    return False

                json_data = await self.nlm_downloader.download_raw_json()
                if json_data:
                    # Save raw JSON file - NO PARSING
                    output_file = self.output_dir / f"{source}.json"
                    try:
                        with open(output_file, "w") as f:
                            import json
                            json.dump(json_data, f)

                        self.downloaded_files[source] = str(output_file)
                        self.state_manager.mark_completed(source, output_file.stat().st_size)
                        logger.info(f"Downloaded ICD-10 file {output_file} ({output_file.stat().st_size} bytes) from NLM API")
                        return True

                    except Exception as e:
                        logger.exception(f"Failed to save NLM JSON file {output_file}: {e}")
                        self.state_manager.mark_failed(source, f"Failed to save file: {e}")
                        return False
                else:
                    self.state_manager.mark_failed(source, "No JSON data retrieved from NLM")
                    return False
            else:
                logger.error(f"Unknown NLM source: {source}")
                return False

        except Exception as e:
            logger.exception(f"Error downloading NLM source {source}: {e}")

            # Check if this is a rate limit error
            if "429" in str(e) or "rate limit" in str(e).lower():
                self.state_manager.mark_rate_limited(source)
            else:
                self.state_manager.mark_failed(source, str(e))
            return False

    async def _download_fallback_source(self) -> bool:
        """Save fallback ICD-10 data as JSON file - NO PARSING"""
        try:
            if not self.nlm_downloader or not hasattr(self.nlm_downloader, "_get_fallback_icd10_data"):
                logger.error("NLM ICD-10 downloader not properly initialized or missing _get_fallback_icd10_data method")
                return False

            fallback_data = self.nlm_downloader._get_fallback_icd10_data()
            if fallback_data:
                # Save fallback data as JSON file - NO PARSING
                output_file = self.output_dir / "fallback_codes.json"
                try:
                    with open(output_file, "w") as f:
                        import json
                        json.dump(fallback_data, f)

                    self.downloaded_files["fallback_codes"] = str(output_file)
                    self.state_manager.mark_completed("fallback_codes", output_file.stat().st_size)
                    logger.info(f"Saved fallback ICD-10 file {output_file} ({output_file.stat().st_size} bytes)")
                    return True

                except Exception as e:
                    logger.exception(f"Failed to save fallback file {output_file}: {e}")
                    self.state_manager.mark_failed("fallback_codes", f"Failed to save file: {e}")
                    return False
            else:
                self.state_manager.mark_failed("fallback_codes", "No fallback ICD-10 data available")
                return False

        except Exception as e:
            logger.exception(f"Error creating fallback ICD-10 file: {e}")
            self.state_manager.mark_failed("fallback_codes", str(e))
            return False

    async def _save_download_summary(self):
        """Save summary of downloaded files - NO PARSING"""
        if not self.downloaded_files:
            logger.warning("No ICD-10 files downloaded")
            return

        # Save summary of downloaded files
        download_summary = {
            "download_timestamp": datetime.now().isoformat(),
            "total_files": len(self.downloaded_files),
            "downloaded_files": dict(self.downloaded_files),  # source -> file_path mapping
            "file_details": {},
        }

        # Add file size information
        for source, file_path in self.downloaded_files.items():
            try:
                from pathlib import Path
                file_obj = Path(file_path)
                if file_obj.exists():
                    download_summary["file_details"][source] = {
                        "file_path": file_path,
                        "file_size_bytes": file_obj.stat().st_size,
                        "file_name": file_obj.name,
                    }
            except Exception as e:
                logger.warning(f"Could not get file info for {source}: {e}")

        # Save summary file
        summary_file = self.output_dir / "download_summary.json"
        try:
            with open(summary_file, "w") as f:
                import json
                json.dump(download_summary, f)
            logger.info(f"Saved download summary to {summary_file}")
        except Exception as e:
            logger.exception(f"Error saving ICD-10 download summary: {e}")

    async def _load_existing_files(self):
        """Load existing downloaded files from previous runs"""
        for source in ["cdc_icd10_cm_2025_april", "cdc_icd10_cm_2025", "cdc_icd10_cm_tabular_2025_april",
                       "cdc_icd10_cm_tabular_2025", "cdc_icd10_cm_2024", "cdc_icd10_cm_tabular_2024",
                       "cms_icd10_cm_2026", "cms_icd10_cm_2025", "cms_icd10_cm_2024",
                       "nlm_icd10_api", "fallback_codes"]:

            # Check for ZIP files
            zip_file = self.output_dir / f"{source}.zip"
            json_file = self.output_dir / f"{source}.json"

            if zip_file.exists():
                self.downloaded_files[source] = str(zip_file)
                logger.debug(f"Found existing ICD-10 file: {zip_file}")
            elif json_file.exists():
                self.downloaded_files[source] = str(json_file)
                logger.debug(f"Found existing ICD-10 file: {json_file}")

    def _generate_final_summary(self, results: dict[str, Any]) -> dict[str, Any]:
        """Generate final summary of ICD-10 file download results"""
        progress = self.state_manager.get_progress_summary()
        
        # Calculate total codes from all downloaded data
        total_codes = sum(len(codes) for codes in self.all_codes.values())

        return {
            "timestamp": datetime.now().isoformat(),
            "data_type": "icd10_files",
            "total_files": self.total_files_downloaded,
            "total_codes": total_codes,  # Add missing field for update script compatibility
            "sources_attempted": results["sources_attempted"],
            "successful_sources": len(results["successful"]),
            "failed_sources": len(results["failed"]),
            "rate_limited_sources": len(results["rate_limited"]),
            "completed_sources": progress["completed"],
            "total_sources": progress["total_sources"],
            "success_rate": (len(results["successful"]) / max(results["sources_attempted"], 1)) * 100,
            "sources": {
                "successful": results["successful"],
                "failed": results["failed"],
                "rate_limited": results["rate_limited"],
            },
            "downloaded_files": dict(self.downloaded_files),
            "expected_vs_actual": {
                "expected_files": "Raw ICD-10 ZIP/JSON files for parsing by medical-mirrors",
                "actual_files": self.total_files_downloaded,
                "note": "Files contain 70,000+ ICD-10-CM codes to be parsed by medical-mirrors service",
            },
        }


    def _reset_all_states(self):
        """Reset all download states for fresh start"""
        sources = ["cdc_icd10_cm_2025_april", "cdc_icd10_cm_2025", "cdc_icd10_cm_tabular_2025_april",
                   "cdc_icd10_cm_tabular_2025", "cdc_icd10_cm_2024", "cdc_icd10_cm_tabular_2024",
                   "cms_icd10_cm_2026", "cms_icd10_cm_2025", "cms_icd10_cm_2024",
                   "nlm_icd10_api", "fallback_codes"]

        for source in sources:
            self.state_manager.reset_source(source)

        # Clear downloaded files tracking
        self.downloaded_files.clear()
        self.total_files_downloaded = 0

        logger.info("Reset all ICD-10 download states")

    async def run_continuous_downloads(self, check_interval: int = 600) -> None:
        """
        Run continuous ICD-10 download process that automatically retries rate-limited sources

        Args:
            check_interval: Time in seconds between retry checks (default 10 minutes)
        """
        logger.info(f"Starting continuous ICD-10 download process (checking every {check_interval} seconds)")

        while True:
            try:
                # Check for sources ready for retry
                ready_sources = self.state_manager.get_ready_for_retry()

                if ready_sources:
                    logger.info(f"Found {len(ready_sources)} ICD-10 sources ready for retry: {ready_sources}")

                    # Attempt to download ready sources
                    plan = {"immediate": [], "retry_ready": ready_sources, "rate_limited": [],
                           "completed": [], "failed": []}

                    results = await self._execute_smart_downloads(plan)

                    if results["successful"]:
                        logger.info(f"Successfully retried {len(results['successful'])} ICD-10 sources")
                        logger.info("ICD-10 retry downloads completed successfully")

                else:
                    logger.debug("No ICD-10 sources ready for retry")

                # Wait before next check
                await asyncio.sleep(check_interval)

            except Exception as e:
                logger.exception(f"Error in continuous ICD-10 download process: {e}")
                await asyncio.sleep(check_interval)

    async def get_download_status(self) -> dict[str, Any]:
        """Get current ICD-10 download status and progress"""
        progress = self.state_manager.get_progress_summary()
        ready_sources = self.state_manager.get_ready_for_retry()
        completion_estimate = self.state_manager.estimate_completion_time()

        # Load existing codes to get accurate count
        if not self.all_codes:
            await self._load_existing_files()
        
        status = {
            "timestamp": datetime.now().isoformat(),
            "data_type": "icd10_codes",
            "progress": progress,
            "ready_for_retry": ready_sources,
            "total_files_downloaded": self.total_files_downloaded,
            "total_codes_downloaded": sum(len(codes) for codes in self.all_codes.values()),
            "completion_estimate": completion_estimate,
            "next_retry_times": {},
            "source_details": {},
        }

        # Add next retry times for rate-limited sources
        for source, source_info in progress["sources"].items():
            if source_info["status"] == "rate_limited" and source_info["next_retry"]:
                status["next_retry_times"][source] = source_info["next_retry"]

        # Add detailed source information
        for source in ["cdc_icd10_cm_2025_april", "cdc_icd10_cm_2025", "cdc_icd10_cm_tabular_2025_april",
                       "cdc_icd10_cm_tabular_2025", "cdc_icd10_cm_2024", "cdc_icd10_cm_tabular_2024",
                       "cms_icd10_cm_2026", "cms_icd10_cm_2025", "cms_icd10_cm_2024",
                       "nlm_icd10_api", "fallback_codes"]:
            status["source_details"][source] = self.state_manager.get_source_details(source)

        return status

    async def get_codes_statistics(self) -> dict[str, Any]:
        """Get detailed statistics about downloaded ICD-10 codes"""
        if not self.all_codes:
            await self._load_existing_files()

        stats = {
            "total_codes": sum(len(codes) for codes in self.all_codes.values()),
            "by_source": {},
            "by_chapter": {},
            "billable_vs_non_billable": {"billable": 0, "non_billable": 0},
            "code_length_distribution": {},
            "most_common_categories": {},
        }

        chapter_counts = {}
        category_counts = {}
        length_counts = {}

        for source, codes in self.all_codes.items():
            stats["by_source"][source] = len(codes)

            for code in codes:
                # Chapter analysis
                chapter = code.get("chapter", "Unknown")
                chapter_counts[chapter] = chapter_counts.get(chapter, 0) + 1

                # Category analysis
                category = code.get("category", "Unknown")
                category_counts[category] = category_counts.get(category, 0) + 1

                # Billable status
                if code.get("is_billable", False):
                    stats["billable_vs_non_billable"]["billable"] += 1
                else:
                    stats["billable_vs_non_billable"]["non_billable"] += 1

                # Code length
                code_length = code.get("code_length", 0)
                length_counts[str(code_length)] = length_counts.get(str(code_length), 0) + 1

        stats["by_chapter"] = dict(sorted(chapter_counts.items(), key=lambda x: x[1], reverse=True)[:20])
        stats["most_common_categories"] = dict(sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:10])
        stats["code_length_distribution"] = dict(sorted(length_counts.items()))

        return stats


async def main():
    """Test the smart ICD-10 codes downloader"""
    logging.basicConfig(level=logging.INFO)

    async with SmartICD10Downloader() as downloader:
        # Test smart download
        summary = await downloader.download_all_icd10_codes()

        print("\n=== Smart ICD-10 Download Summary ===")
        print(f"Total codes downloaded: {summary['total_codes']:,}")
        print(f"Successful sources: {summary['successful_sources']}")
        print(f"Failed sources: {summary['failed_sources']}")
        print(f"Rate limited sources: {summary['rate_limited_sources']}")
        print(f"Success rate: {summary['success_rate']:.1f}%")

        print("\n=== Expected vs Actual ===")
        print(f"Expected: {summary['expected_vs_actual']['expected_total']}")
        print(f"Actual: {summary['expected_vs_actual']['actual_total']:,}")
        print(f"Improvement: +{summary['expected_vs_actual']['improvement_over_fallback']:,} codes")

        print("\n=== By Source ===")
        for source, count in summary["by_source_breakdown"].items():
            print(f"{source}: {count:,} codes")

        # Show current status
        status = await downloader.get_download_status()
        print("\n=== Current Status ===")
        print(json.dumps(status, indent=2, default=str))

        # Show code statistics
        stats = await downloader.get_codes_statistics()
        print("\n=== Code Statistics ===")
        print(json.dumps(stats, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
