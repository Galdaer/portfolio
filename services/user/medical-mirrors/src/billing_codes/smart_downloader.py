"""
Smart Billing Codes Downloader with automatic rate limit handling and recovery
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
import time

from .download_state_manager import DownloadStateManager, DownloadStatus
from .cms_downloader import CMSHCPCSDownloader
from .downloader import BillingCodesDownloader
from .parser import BillingCodesParser
from config import Config

logger = logging.getLogger(__name__)


class SmartBillingCodesDownloader:
    """Smart downloader that coordinates multiple sources with rate limit handling"""
    
    def __init__(self, output_dir: Optional[Path] = None, config: Optional[Config] = None):
        self.config = config or Config()
        self.output_dir = output_dir or Path("/home/intelluxe/database/medical_complete/billing")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.state_manager = DownloadStateManager()
        self.parser = BillingCodesParser()
        
        # Download sources
        self.cms_downloader: Optional[CMSHCPCSDownloader] = None
        self.nlm_downloader: Optional[BillingCodesDownloader] = None
        
        # Smart retry configuration
        self.max_concurrent_sources = 3
        self.retry_interval = 300  # 5 minutes between retry checks
        self.max_daily_retries = 24  # Max retries per source per day
        
        # Results tracking
        self.all_codes: Dict[str, List[Dict[str, Any]]] = {}
        self.total_downloaded = 0
        
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
    
    async def download_all_billing_codes(self, force_fresh: bool = False) -> Dict[str, Any]:
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
    
    async def _create_download_plan(self) -> Dict[str, List[str]]:
        """Create intelligent download plan based on current states"""
        plan = {
            "immediate": [],      # Sources ready to download immediately
            "retry_ready": [],    # Sources ready for retry
            "rate_limited": [],   # Sources currently rate limited  
            "completed": [],      # Sources already completed
            "failed": []          # Sources that have failed too many times
        }
        
        # Define all possible sources
        all_sources = [
            "cms_hcpcs_current",
            "cms_hcpcs_alpha", 
            "cms_hcpcs_anweb",
            "nlm_hcpcs_api",
            "nlm_cpt_api",
            "fallback_codes"
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
    
    async def _execute_smart_downloads(self, plan: Dict[str, List[str]]) -> Dict[str, Any]:
        """Execute downloads according to the plan"""
        results = {
            "successful": [],
            "failed": [],
            "rate_limited": [],
            "completed": 0,
            "total_codes": 0,
            "sources_attempted": 0
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
                logger.error(f"Unexpected error downloading {source}: {e}")
                results["failed"].append(source)
        
        # Calculate total codes
        results["total_codes"] = sum(len(codes) for codes in self.all_codes.values())
        
        return results
    
    async def _download_single_source(self, source: str, semaphore: asyncio.Semaphore) -> bool:
        """Download from a single source with rate limit handling"""
        async with semaphore:
            try:
                logger.info(f"Starting download for source: {source}")
                
                if source.startswith("cms_"):
                    return await self._download_cms_source(source)
                elif source.startswith("nlm_"):
                    return await self._download_nlm_source(source) 
                elif source == "fallback_codes":
                    return await self._download_fallback_source()
                else:
                    logger.error(f"Unknown source type: {source}")
                    return False
                    
            except Exception as e:
                logger.error(f"Error downloading {source}: {e}")
                self.state_manager.mark_failed(source, str(e))
                return False
    
    async def _download_cms_source(self, source: str) -> bool:
        """Download from CMS source"""
        try:
            # Map source names to CMS URLs
            cms_mapping = {
                "cms_hcpcs_current": "hcpcs_current",
                "cms_hcpcs_alpha": "hcpcs_alpha", 
                "cms_hcpcs_anweb": "hcpcs_anweb"
            }
            
            cms_source = cms_mapping.get(source)
            if not cms_source:
                logger.error(f"Unknown CMS source: {source}")
                return False
            
            # Download just this specific CMS source
            url = self.cms_downloader.CMS_URLS.get(cms_source)
            if not url:
                logger.error(f"No URL found for CMS source: {cms_source}")
                return False
            
            # Download content
            content = await self.cms_downloader._download_with_retry(url, source)
            if not content:
                return False
            
            # Parse content
            codes = self.cms_downloader._parse_hcpcs_zip(content, source)
            if codes:
                self.all_codes[source] = codes
                self.state_manager.mark_completed(source, len(codes))
                logger.info(f"Downloaded {len(codes)} codes from {source}")
                return True
            else:
                self.state_manager.mark_failed(source, "No codes extracted")
                return False
                
        except Exception as e:
            logger.error(f"Error downloading CMS source {source}: {e}")
            self.state_manager.mark_failed(source, str(e))
            return False
    
    async def _download_nlm_source(self, source: str) -> bool:
        """Download from NLM API source"""
        try:
            if source == "nlm_hcpcs_api":
                # Download HCPCS codes via NLM API
                codes = await self.nlm_downloader._download_hcpcs_codes()
                if codes:
                    self.all_codes[source] = codes
                    self.state_manager.mark_completed(source, len(codes))
                    logger.info(f"Downloaded {len(codes)} HCPCS codes from NLM API")
                    return True
                else:
                    self.state_manager.mark_failed(source, "No HCPCS codes retrieved")
                    return False
                    
            elif source == "nlm_cpt_api":
                # Download available CPT codes via NLM API
                codes = await self.nlm_downloader._download_available_cpt_codes()
                if codes:
                    self.all_codes[source] = codes
                    self.state_manager.mark_completed(source, len(codes))
                    logger.info(f"Downloaded {len(codes)} CPT codes from NLM API")
                    return True
                else:
                    # CPT codes often not available due to copyright - not a failure
                    self.state_manager.mark_completed(source, 0)
                    logger.info("No CPT codes available from NLM API (expected due to copyright)")
                    return True
                    
        except Exception as e:
            logger.error(f"Error downloading NLM source {source}: {e}")
            
            # Check if this is a rate limit error
            if "429" in str(e) or "rate limit" in str(e).lower():
                self.state_manager.mark_rate_limited(source)
            else:
                self.state_manager.mark_failed(source, str(e))
            return False
    
    async def _download_fallback_source(self) -> bool:
        """Load fallback billing codes"""
        try:
            fallback_codes = self.nlm_downloader._get_fallback_billing_codes()
            if fallback_codes:
                self.all_codes["fallback_codes"] = fallback_codes
                self.state_manager.mark_completed("fallback_codes", len(fallback_codes))
                logger.info(f"Loaded {len(fallback_codes)} fallback codes")
                return True
            else:
                self.state_manager.mark_failed("fallback_codes", "No fallback codes available")
                return False
                
        except Exception as e:
            logger.error(f"Error loading fallback codes: {e}")
            self.state_manager.mark_failed("fallback_codes", str(e))
            return False
    
    async def _save_consolidated_results(self):
        """Save consolidated results from all sources"""
        if not self.all_codes:
            logger.warning("No codes to save")
            return
        
        # Combine all codes and deduplicate
        all_codes_list = []
        seen_codes: Set[str] = set()
        
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
            with open(consolidated_file, 'w') as f:
                json.dump(validated_codes, f, indent=2, default=str)
            logger.info(f"Saved {len(validated_codes)} validated codes to {consolidated_file}")
        except Exception as e:
            logger.error(f"Error saving consolidated results: {e}")
        
        # Save individual source files
        for source, codes in self.all_codes.items():
            source_file = self.output_dir / f"{source}_codes.json"
            try:
                with open(source_file, 'w') as f:
                    json.dump(codes, f, indent=2, default=str)
            except Exception as e:
                logger.error(f"Error saving {source} results: {e}")
        
        self.total_downloaded = len(validated_codes)
    
    async def _load_existing_results(self):
        """Load existing results from completed downloads"""
        for source in ["cms_hcpcs_current", "cms_hcpcs_alpha", "cms_hcpcs_anweb", 
                       "nlm_hcpcs_api", "nlm_cpt_api", "fallback_codes"]:
            source_file = self.output_dir / f"{source}_codes.json"
            if source_file.exists():
                try:
                    with open(source_file, 'r') as f:
                        codes = json.load(f)
                        self.all_codes[source] = codes
                        logger.debug(f"Loaded {len(codes)} existing codes from {source}")
                except Exception as e:
                    logger.error(f"Error loading existing results from {source}: {e}")
    
    def _generate_final_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
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
                "rate_limited": results["rate_limited"]
            },
            "by_source_breakdown": {}
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
                logger.error(f"Error in continuous download process: {e}")
                await asyncio.sleep(check_interval)
    
    async def get_download_status(self) -> Dict[str, Any]:
        """Get current download status and progress"""
        progress = self.state_manager.get_progress_summary()
        ready_sources = self.state_manager.get_ready_for_retry()
        
        status = {
            "timestamp": datetime.now().isoformat(),
            "progress": progress,
            "ready_for_retry": ready_sources,
            "total_codes_downloaded": self.total_downloaded,
            "next_retry_times": {}
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
        
        print(f"\n=== Smart Download Summary ===")
        print(f"Total codes downloaded: {summary['total_codes']}")
        print(f"Successful sources: {summary['successful_sources']}")
        print(f"Failed sources: {summary['failed_sources']}")
        print(f"Rate limited sources: {summary['rate_limited_sources']}")
        print(f"Success rate: {summary['success_rate']:.1f}%")
        
        print(f"\n=== By Source ===")
        for source, count in summary["by_source_breakdown"].items():
            print(f"{source}: {count} codes")
        
        # Show current status
        status = await downloader.get_download_status()
        print(f"\n=== Current Status ===")
        print(json.dumps(status, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())