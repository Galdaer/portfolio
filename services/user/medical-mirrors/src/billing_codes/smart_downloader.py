"""
Smart Billing Codes Downloader with automatic rate limit handling and recovery
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from config import Config

from .cms_downloader import CMSHCPCSDownloader
from .download_state_manager import DownloadStateManager, DownloadStatus
from .downloader import BillingCodesDownloader
from .parser import BillingCodesParser

logger = logging.getLogger(__name__)


class SmartBillingCodesDownloader:
    """Smart downloader that coordinates multiple sources with rate limit handling"""

    def __init__(self, output_dir: Path | None = None, config: Config | None = None):
        self.config = config or Config()
        self.output_dir = output_dir or Path("/home/intelluxe/database/medical_complete/billing")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.state_manager = DownloadStateManager()
        self.parser = BillingCodesParser()

        # Download sources
        self.cms_downloader: CMSHCPCSDownloader | None = None
        self.nlm_downloader: BillingCodesDownloader | None = None

        # Smart retry configuration
        self.max_concurrent_sources = 3
        self.retry_interval = 300  # 5 minutes between retry checks
        self.total_downloaded = 0  # Total codes downloaded
        self.max_daily_retries = 24  # Max retries per source per day

        # Results tracking - track downloaded files, NOT parsed codes
        self.downloaded_files: dict[str, str] = {}  # source -> file_path
        self.all_codes: dict[str, list[Any]] = {}  # source -> codes list
        self.total_files_downloaded = 0

    async def __aenter__(self):
        """Async context manager entry"""
        self.cms_downloader = CMSHCPCSDownloader(self.state_manager, self.output_dir)
        await self.cms_downloader.__aenter__()

        self.nlm_downloader = BillingCodesDownloader(self.config)
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
        logger.info("Checking for existing ZIP files to process")

        cms_sources = ["cms_hcpcs_current", "cms_hcpcs_alpha", "cms_hcpcs_anweb"]
        processed_count = 0

        for source in cms_sources:
            zip_file = self.output_dir / f"{source}.zip"
            if zip_file.exists() and source not in self.all_codes:
                try:
                    logger.info(f"Processing existing ZIP file: {zip_file}")
                    with open(zip_file, "rb") as f:
                        content = f.read()

                    # Parse ZIP file to extract codes
                    parsed_codes = self.cms_downloader._parse_hcpcs_zip(content, source)

                    if parsed_codes:
                        self.all_codes[source] = parsed_codes
                        processed_count += 1
                        logger.info(f"Processed existing ZIP file {source}: {len(parsed_codes)} codes extracted")
                    else:
                        logger.warning(f"No codes extracted from existing ZIP file: {source}")

                except Exception as e:
                    logger.exception(f"Failed to process existing ZIP file {source}: {e}")

        if processed_count > 0:
            logger.info(f"Successfully processed {processed_count} existing ZIP files")
        else:
            logger.info("No existing ZIP files found to process")

    async def download_all_billing_codes(self, force_fresh: bool = False) -> dict[str, Any]:
        """
        Download all billing codes from all sources with smart retry handling

        Args:
            force_fresh: If True, reset all download states and start fresh

        Returns:
            Summary of download results including totals and source breakdown
        """
        logger.info("Starting smart billing codes download process")

        if force_fresh:
            logger.info("Force fresh download - resetting all states")
            self._reset_all_states()

        # Process existing ZIP files that might not have been parsed yet
        await self._process_existing_zip_files()

        # Get initial progress
        initial_progress = self.state_manager.get_progress_summary()
        logger.info(f"Initial state: {initial_progress['completed']}/{initial_progress['total_sources']} sources completed")

        # Plan download strategy
        download_plan = await self._create_download_plan()
        logger.info(f"Download plan: {len(download_plan['immediate'])} immediate, "
                   f"{len(download_plan['retry_ready'])} ready for retry, "
                   f"{len(download_plan['rate_limited'])} rate limited")

        # Execute downloads
        results = await self._execute_smart_downloads(download_plan)

        # Save consolidated results
        await self._save_consolidated_results()

        # Generate final summary
        final_summary = self._generate_final_summary(results)

        logger.info(f"Smart download completed: {final_summary['total_codes']} codes from "
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

        # Define all possible sources
        all_sources = [
            "cms_hcpcs_current",
            "cms_hcpcs_alpha",
            "cms_hcpcs_anweb",
            "nlm_hcpcs_api",
            "nlm_cpt_api",
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
            logger.info("No sources need downloading")
            # Load existing completed results
            await self._load_existing_results()
            results["total_codes"] = sum(len(codes) for codes in self.all_codes.values())
            return results

        # Limit concurrent downloads to prevent overwhelming servers
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
                    logger.info(f"Successfully completed download for {source}")
                else:
                    state = self.state_manager.get_state(source)
                    if state and state.status == DownloadStatus.RATE_LIMITED:
                        results["rate_limited"].append(source)
                        logger.warning(f"Rate limited: {source}")
                    else:
                        results["failed"].append(source)
                        logger.error(f"Failed to download: {source}")

            except Exception as e:
                logger.exception(f"Unexpected error downloading {source}: {e}")
                results["failed"].append(source)

        # Calculate total files downloaded
        results["total_files"] = len(self.downloaded_files)
        self.total_files_downloaded = results["total_files"]

        return results

    async def _download_single_source(self, source: str, semaphore: asyncio.Semaphore) -> bool:
        """Download from a single source with rate limit handling"""
        async with semaphore:
            try:
                logger.info(f"Starting download for source: {source}")

                if source.startswith("cms_"):
                    return await self._download_cms_source(source)
                if source.startswith("nlm_"):
                    return await self._download_nlm_source(source)
                if source == "fallback_codes":
                    return await self._download_fallback_source()
                logger.error(f"Unknown source type: {source}")
                return False

            except Exception as e:
                logger.exception(f"Error downloading {source}: {e}")
                self.state_manager.mark_failed(source, str(e))
                return False

    async def _download_cms_source(self, source: str) -> bool:
        """Download from CMS source"""
        try:
            # Map source names to CMS URLs
            cms_mapping = {
                "cms_hcpcs_current": "hcpcs_current",
                "cms_hcpcs_alpha": "hcpcs_alpha",
                "cms_hcpcs_anweb": "hcpcs_anweb",
            }

            cms_source = cms_mapping.get(source)
            if not cms_source:
                logger.error(f"Unknown CMS source: {source}")
                return False

            # Download just this specific CMS source
            if not self.cms_downloader or not hasattr(self.cms_downloader, "CMS_URLS"):
                logger.error("CMS downloader not properly initialized")
                return False

            url = self.cms_downloader.CMS_URLS.get(cms_source)
            if not url:
                logger.error(f"No URL found for CMS source: {cms_source}")
                return False

            # Download content
            if not hasattr(self.cms_downloader, "_download_with_retry"):
                logger.error("CMS downloader missing _download_with_retry method")
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
                logger.info(f"Parsing ZIP file for {source}")
                parsed_codes = self.cms_downloader._parse_hcpcs_zip(content, source)

                if parsed_codes:
                    self.all_codes[source] = parsed_codes
                    logger.info(f"Extracted {len(parsed_codes)} codes from {source}")
                else:
                    logger.warning(f"No codes extracted from {source} ZIP file")

                self.downloaded_files[source] = str(output_file)
                self.state_manager.mark_completed(source, output_file.stat().st_size)
                logger.info(f"Downloaded and processed file {output_file} ({len(content)} bytes) from {source}")
                return True

            except Exception as e:
                logger.exception(f"Failed to save file {output_file}: {e}")
                self.state_manager.mark_failed(source, f"Failed to save file: {e}")
                return False

        except Exception as e:
            logger.exception(f"Error downloading CMS source {source}: {e}")
            self.state_manager.mark_failed(source, str(e))
            return False

    async def _download_nlm_source(self, source: str) -> bool:
        """Download raw JSON from NLM API source - NO PARSING"""
        try:
            if source == "nlm_hcpcs_api":
                # Download raw JSON from NLM HCPCS API
                if not self.nlm_downloader or not hasattr(self.nlm_downloader, "_download_hcpcs_raw_json"):
                    logger.error("NLM downloader not properly initialized or missing _download_hcpcs_raw_json method")
                    return False

                json_data = await self.nlm_downloader._download_hcpcs_raw_json()
                if json_data:
                    # Save raw JSON file - NO PARSING
                    output_file = self.output_dir / f"{source}.json"
                    try:
                        with open(output_file, "w") as f:
                            import json
                            json.dump(json_data, f)

                        self.downloaded_files[source] = str(output_file)
                        self.state_manager.mark_completed(source, output_file.stat().st_size)
                        logger.info(f"Downloaded file {output_file} ({output_file.stat().st_size} bytes) from NLM HCPCS API")
                        return True

                    except Exception as e:
                        logger.exception(f"Failed to save JSON file {output_file}: {e}")
                        self.state_manager.mark_failed(source, f"Failed to save file: {e}")
                        return False
                else:
                    self.state_manager.mark_failed(source, "No JSON data retrieved from NLM HCPCS")
                    return False

            elif source == "nlm_cpt_api":
                # Download raw JSON from NLM CPT API
                if not self.nlm_downloader or not hasattr(self.nlm_downloader, "_download_cpt_raw_json"):
                    logger.error("NLM downloader not properly initialized or missing _download_cpt_raw_json method")
                    return False

                json_data = await self.nlm_downloader._download_cpt_raw_json()
                if json_data:
                    # Save raw JSON file - NO PARSING
                    output_file = self.output_dir / f"{source}.json"
                    try:
                        with open(output_file, "w") as f:
                            import json
                            json.dump(json_data, f)

                        self.downloaded_files[source] = str(output_file)
                        self.state_manager.mark_completed(source, output_file.stat().st_size)
                        logger.info(f"Downloaded file {output_file} ({output_file.stat().st_size} bytes) from NLM CPT API")
                        return True

                    except Exception as e:
                        logger.exception(f"Failed to save JSON file {output_file}: {e}")
                        self.state_manager.mark_failed(source, f"Failed to save file: {e}")
                        return False
                else:
                    # CPT codes often not available due to copyright - create empty file
                    output_file = self.output_dir / f"{source}.json"
                    try:
                        with open(output_file, "w") as f:
                            import json
                            json.dump({"note": "CPT codes not available due to copyright restrictions"}, f)

                        self.downloaded_files[source] = str(output_file)
                        self.state_manager.mark_completed(source, output_file.stat().st_size)
                        logger.info("Created placeholder file for CPT codes (expected due to copyright)")
                        return True

                    except Exception as e:
                        logger.exception(f"Failed to save placeholder file {output_file}: {e}")
                        self.state_manager.mark_failed(source, f"Failed to save file: {e}")
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
        """Save fallback billing codes data as JSON file - NO PARSING"""
        try:
            if not self.nlm_downloader or not hasattr(self.nlm_downloader, "_get_fallback_billing_data"):
                logger.error("NLM downloader not properly initialized or missing _get_fallback_billing_data method")
                return False

            fallback_data = self.nlm_downloader._get_fallback_billing_data()
            if fallback_data:
                # Save fallback data as JSON file - NO PARSING
                output_file = self.output_dir / "fallback_codes.json"
                try:
                    with open(output_file, "w") as f:
                        import json
                        json.dump(fallback_data, f)

                    self.downloaded_files["fallback_codes"] = str(output_file)
                    self.state_manager.mark_completed("fallback_codes", output_file.stat().st_size)
                    logger.info(f"Saved fallback billing codes file {output_file} ({output_file.stat().st_size} bytes)")
                    return True

                except Exception as e:
                    logger.exception(f"Failed to save fallback file {output_file}: {e}")
                    self.state_manager.mark_failed("fallback_codes", f"Failed to save file: {e}")
                    return False
            else:
                self.state_manager.mark_failed("fallback_codes", "No fallback billing codes data available")
                return False

        except Exception as e:
            logger.exception(f"Error creating fallback billing codes file: {e}")
            self.state_manager.mark_failed("fallback_codes", str(e))
            return False

    async def _save_consolidated_results(self):
        """Save consolidated results from all sources"""
        if not self.all_codes:
            logger.warning("No codes to save")
            return

        # Combine all codes and deduplicate
        all_codes_list = []
        seen_codes: set[str] = set()

        for source, codes in self.all_codes.items():
            logger.info(f"Processing {len(codes)} codes from {source}")

            for code in codes:
                code_key = code.get("code", "")
                if code_key and code_key not in seen_codes:
                    all_codes_list.append(code)
                    seen_codes.add(code_key)

        logger.info(f"Consolidated {len(all_codes_list)} unique codes from {len(self.all_codes)} sources")

        # Parse and validate all codes
        validated_codes = self.parser.parse_and_validate(all_codes_list)

        # Save main consolidated file
        consolidated_file = self.output_dir / "all_billing_codes_complete.json"
        try:
            with open(consolidated_file, "w") as f:
                json.dump(validated_codes, f, default=str)
            logger.info(f"Saved {len(validated_codes)} validated codes to {consolidated_file}")
            
            # Load into database using medical-mirrors database loader
            try:
                from .database_loader import BillingCodesDatabaseLoader
                loader = BillingCodesDatabaseLoader()
                load_stats = loader.load_codes(validated_codes)
                logger.info(f"✅ Database loading completed: {load_stats}")
            except Exception as db_error:
                logger.error(f"Failed to load codes into database: {db_error}")
                # Continue processing - database loading failure shouldn't stop file generation
                
        except Exception as e:
            logger.exception(f"Error saving consolidated results: {e}")

        # Save individual source files
        for source, codes in self.all_codes.items():
            source_file = self.output_dir / f"{source}_codes.json"
            try:
                with open(source_file, "w") as f:
                    json.dump(codes, f, default=str)
            except Exception as e:
                logger.exception(f"Error saving {source} results: {e}")

        self.total_downloaded = len(validated_codes)

    async def _load_existing_results(self):
        """Load existing results from completed downloads"""
        for source in ["cms_hcpcs_current", "cms_hcpcs_alpha", "cms_hcpcs_anweb",
                       "nlm_hcpcs_api", "nlm_cpt_api", "fallback_codes"]:
            source_file = self.output_dir / f"{source}_codes.json"
            if source_file.exists():
                try:
                    with open(source_file) as f:
                        codes = json.load(f)
                        self.all_codes[source] = codes
                        logger.debug(f"Loaded {len(codes)} existing codes from {source}")
                except Exception as e:
                    logger.exception(f"Error loading existing results from {source}: {e}")

    def _generate_final_summary(self, results: dict[str, Any]) -> dict[str, Any]:
        """Generate final summary of download results"""
        progress = self.state_manager.get_progress_summary()

        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_codes": self.total_downloaded,
            "sources_attempted": results["sources_attempted"],
            "successful_sources": len(results["successful"]),
            "failed_sources": len(results["failed"]),
            "rate_limited_sources": len(results["rate_limited"]),
            "completed_sources": progress["completed"],
            "total_sources": progress["total_sources"],
            "success_rate": (len(results["successful"]) / max(results["sources_attempted"], 1)) * 100,
            "parser_stats": self.parser.get_parsing_stats(),
            "sources": {
                "successful": results["successful"],
                "failed": results["failed"],
                "rate_limited": results["rate_limited"],
            },
            "by_source_breakdown": {},
        }

        # Add breakdown by source
        for source, codes in self.all_codes.items():
            summary["by_source_breakdown"][source] = len(codes)

        return summary

    def _reset_all_states(self):
        """Reset all download states for fresh start"""
        sources = ["cms_hcpcs_current", "cms_hcpcs_alpha", "cms_hcpcs_anweb",
                   "nlm_hcpcs_api", "nlm_cpt_api", "fallback_codes"]

        for source in sources:
            self.state_manager.reset_source(source)

        logger.info("Reset all download states")

    async def run_continuous_downloads(self, check_interval: int = 300) -> None:
        """
        Run continuous download process that automatically retries rate-limited sources

        Args:
            check_interval: Time in seconds between retry checks (default 5 minutes)
        """
        logger.info(f"Starting continuous download process (checking every {check_interval} seconds)")

        while True:
            try:
                # Check for sources ready for retry
                ready_sources = self.state_manager.get_ready_for_retry()

                if ready_sources:
                    logger.info(f"Found {len(ready_sources)} sources ready for retry: {ready_sources}")

                    # Attempt to download ready sources
                    plan = {"immediate": [], "retry_ready": ready_sources, "rate_limited": [],
                           "completed": [], "failed": []}

                    results = await self._execute_smart_downloads(plan)

                    if results["successful"]:
                        logger.info(f"Successfully retried {len(results['successful'])} sources")
                        await self._save_consolidated_results()

                else:
                    logger.debug("No sources ready for retry")

                # Wait before next check
                await asyncio.sleep(check_interval)

            except Exception as e:
                logger.exception(f"Error in continuous download process: {e}")
                await asyncio.sleep(check_interval)

    async def get_download_status(self) -> dict[str, Any]:
        """Get current download status and progress"""
        progress = self.state_manager.get_progress_summary()
        ready_sources = self.state_manager.get_ready_for_retry()

        status = {
            "timestamp": datetime.now().isoformat(),
            "progress": progress,
            "ready_for_retry": ready_sources,
            "total_codes_downloaded": getattr(self, "total_downloaded", 0),
            "next_retry_times": {},
        }

        # Add next retry times for rate-limited sources
        for source, source_info in progress["sources"].items():
            if source_info["status"] == "rate_limited" and source_info["next_retry"]:
                status["next_retry_times"][source] = source_info["next_retry"]

        return status


async def main():
    """Test the smart billing codes downloader"""
    logging.basicConfig(level=logging.INFO)

    async with SmartBillingCodesDownloader() as downloader:
        # Test smart download
        summary = await downloader.download_all_billing_codes()

        print("\n=== Smart Download Summary ===")
        print(f"Total codes downloaded: {summary['total_codes']}")
        print(f"Successful sources: {summary['successful_sources']}")
        print(f"Failed sources: {summary['failed_sources']}")
        print(f"Rate limited sources: {summary['rate_limited_sources']}")
        print(f"Success rate: {summary['success_rate']:.1f}%")

        print("\n=== By Source ===")
        for source, count in summary["by_source_breakdown"].items():
            print(f"{source}: {count} codes")

        # Show current status
        status = await downloader.get_download_status()
        print("\n=== Current Status ===")
        print(json.dumps(status, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
