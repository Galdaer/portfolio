"""
Smart ICD-10 Codes Downloader with automatic rate limit handling and recovery
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
import time

from .download_state_manager import ICD10DownloadStateManager, DownloadStatus
from .cms_icd10_downloader import CMSICD10Downloader
from .downloader import ICD10Downloader
from .parser import ICD10Parser
from config import Config

logger = logging.getLogger(__name__)


class SmartICD10Downloader:
    """Smart downloader that coordinates multiple ICD-10 sources with rate limit handling"""
    
    def __init__(self, output_dir: Optional[Path] = None, config: Optional[Config] = None):
        self.config = config or Config()
        self.output_dir = output_dir or Path("/home/intelluxe/database/medical_complete/icd10")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.state_manager = ICD10DownloadStateManager()
        self.parser = ICD10Parser()
        
        # Download sources
        self.cms_downloader: Optional[CMSICD10Downloader] = None
        self.nlm_downloader: Optional[ICD10Downloader] = None
        
        # Smart retry configuration
        self.max_concurrent_sources = 2  # More conservative for ICD-10
        self.retry_interval = 600  # 10 minutes between retry checks
        self.max_daily_retries = 12  # Max retries per source per day
        
        # Results tracking
        self.all_codes: Dict[str, List[Dict[str, Any]]] = {}
        self.total_downloaded = 0
        
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
    
    async def download_all_icd10_codes(self, force_fresh: bool = False) -> Dict[str, Any]:
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
        
        # Save consolidated results
        await self._save_consolidated_results()
        
        # Generate final summary
        final_summary = self._generate_final_summary(results)
        
        logger.info(f"Smart ICD-10 download completed: {final_summary['total_codes']} codes from "
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
            logger.info("No ICD-10 sources need downloading")
            # Load existing completed results
            await self._load_existing_results()
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
                logger.error(f"Unexpected error downloading ICD-10 {source}: {e}")
                results["failed"].append(source)
        
        # Calculate total codes
        results["total_codes"] = sum(len(codes) for codes in self.all_codes.values())
        
        return results
    
    async def _download_single_source(self, source: str, semaphore: asyncio.Semaphore) -> bool:
        """Download from a single ICD-10 source with rate limit handling"""
        async with semaphore:
            try:
                logger.info(f"Starting ICD-10 download for source: {source}")
                
                if source.startswith("cms_") or source.startswith("cdc_") or source.startswith("who_"):
                    return await self._download_cms_who_source(source)
                elif source.startswith("nlm_"):
                    return await self._download_nlm_source(source) 
                elif source == "fallback_codes":
                    return await self._download_fallback_source()
                else:
                    logger.error(f"Unknown ICD-10 source type: {source}")
                    return False
                    
            except Exception as e:
                logger.error(f"Error downloading ICD-10 {source}: {e}")
                self.state_manager.mark_failed(source, str(e))
                return False
    
    async def _download_cms_who_source(self, source: str) -> bool:
        """Download from CDC, CMS, or WHO source"""
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
                "cms_icd10_cm_2024": "cms_icd10_cm_2024"
            }
            
            cms_source = source_mapping.get(source)
            if not cms_source:
                logger.error(f"Unknown CMS/WHO source: {source}")
                return False
            
            # Download just this specific source
            url = self.cms_downloader.CMS_URLS.get(cms_source)
            if not url:
                logger.error(f"No URL found for ICD-10 source: {cms_source}")
                return False
            
            # Download content
            content = await self.cms_downloader._download_with_retry(url, source)
            if not content:
                return False
            
            # Parse content
            codes = self.cms_downloader._parse_icd10_zip(content, source)
            if codes:
                self.all_codes[source] = codes
                self.state_manager.mark_completed(source, len(codes))
                logger.info(f"Downloaded {len(codes)} ICD-10 codes from {source}")
                return True
            else:
                self.state_manager.mark_failed(source, "No ICD-10 codes extracted")
                return False
                
        except Exception as e:
            logger.error(f"Error downloading CMS/WHO source {source}: {e}")
            self.state_manager.mark_failed(source, str(e))
            return False
    
    async def _download_nlm_source(self, source: str) -> bool:
        """Download from NLM API source"""
        try:
            if source == "nlm_icd10_api":
                # Download ICD-10 codes via NLM API
                codes = await self.nlm_downloader.download_all_codes()
                if codes:
                    self.all_codes[source] = codes
                    self.state_manager.mark_completed(source, len(codes))
                    logger.info(f"Downloaded {len(codes)} ICD-10 codes from NLM API")
                    return True
                else:
                    self.state_manager.mark_failed(source, "No ICD-10 codes retrieved from NLM")
                    return False
                    
        except Exception as e:
            logger.error(f"Error downloading NLM source {source}: {e}")
            
            # Check if this is a rate limit error
            if "429" in str(e) or "rate limit" in str(e).lower():
                self.state_manager.mark_rate_limited(source)
            else:
                self.state_manager.mark_failed(source, str(e))
            return False
    
    async def _download_fallback_source(self) -> bool:
        """Load fallback ICD-10 codes"""
        try:
            fallback_codes = self.nlm_downloader._get_fallback_icd10_codes()
            if fallback_codes:
                self.all_codes["fallback_codes"] = fallback_codes
                self.state_manager.mark_completed("fallback_codes", len(fallback_codes))
                logger.info(f"Loaded {len(fallback_codes)} fallback ICD-10 codes")
                return True
            else:
                self.state_manager.mark_failed("fallback_codes", "No fallback ICD-10 codes available")
                return False
                
        except Exception as e:
            logger.error(f"Error loading fallback ICD-10 codes: {e}")
            self.state_manager.mark_failed("fallback_codes", str(e))
            return False
    
    async def _save_consolidated_results(self):
        """Save consolidated results from all ICD-10 sources"""
        if not self.all_codes:
            logger.warning("No ICD-10 codes to save")
            return
        
        # Combine all codes and deduplicate
        all_codes_list = []
        seen_codes: Set[str] = set()
        
        for source, codes in self.all_codes.items():
            logger.info(f"Processing {len(codes)} ICD-10 codes from {source}")
            
            for code in codes:
                code_key = code.get("code", "")
                if code_key and code_key not in seen_codes:
                    # Ensure consistent source attribution
                    code["source"] = source
                    all_codes_list.append(code)
                    seen_codes.add(code_key)
        
        logger.info(f"Consolidated {len(all_codes_list)} unique ICD-10 codes from {len(self.all_codes)} sources")
        
        # Parse and validate all codes
        validated_codes = self.parser.parse_and_validate(all_codes_list)
        
        # Save main consolidated file
        consolidated_file = self.output_dir / "all_icd10_codes_complete.json"
        try:
            with open(consolidated_file, 'w') as f:
                json.dump(validated_codes, f, indent=2, default=str)
            logger.info(f"Saved {len(validated_codes)} validated ICD-10 codes to {consolidated_file}")
        except Exception as e:
            logger.error(f"Error saving consolidated ICD-10 results: {e}")
        
        # Save individual source files
        for source, codes in self.all_codes.items():
            source_file = self.output_dir / f"{source}_codes.json"
            try:
                with open(source_file, 'w') as f:
                    json.dump(codes, f, indent=2, default=str)
            except Exception as e:
                logger.error(f"Error saving ICD-10 {source} results: {e}")
        
        self.total_downloaded = len(validated_codes)
    
    async def _load_existing_results(self):
        """Load existing results from completed downloads"""
        for source in ["cdc_icd10_cm_2025_april", "cdc_icd10_cm_2025", "cdc_icd10_cm_tabular_2025_april",
                       "cdc_icd10_cm_tabular_2025", "cdc_icd10_cm_2024", "cdc_icd10_cm_tabular_2024",
                       "cms_icd10_cm_2026", "cms_icd10_cm_2025", "cms_icd10_cm_2024", 
                       "nlm_icd10_api", "fallback_codes"]:
            source_file = self.output_dir / f"{source}_codes.json"
            if source_file.exists():
                try:
                    with open(source_file, 'r') as f:
                        codes = json.load(f)
                        self.all_codes[source] = codes
                        logger.debug(f"Loaded {len(codes)} existing ICD-10 codes from {source}")
                except Exception as e:
                    logger.error(f"Error loading existing ICD-10 results from {source}: {e}")
    
    def _generate_final_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate final summary of ICD-10 download results"""
        progress = self.state_manager.get_progress_summary()
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "data_type": "icd10_codes",
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
            "by_source_breakdown": {},
            "expected_vs_actual": {
                "expected_total": "70,000+ ICD-10-CM codes",
                "actual_total": self.total_downloaded,
                "improvement_over_fallback": max(0, self.total_downloaded - 10)  # Current fallback is 10
            }
        }
        
        # Add breakdown by source
        for source, codes in self.all_codes.items():
            summary["by_source_breakdown"][source] = len(codes)
        
        return summary
    
    def _reset_all_states(self):
        """Reset all download states for fresh start"""
        sources = ["cdc_icd10_cm_2025_april", "cdc_icd10_cm_2025", "cdc_icd10_cm_tabular_2025_april",
                   "cdc_icd10_cm_tabular_2025", "cdc_icd10_cm_2024", "cdc_icd10_cm_tabular_2024",
                   "cms_icd10_cm_2026", "cms_icd10_cm_2025", "cms_icd10_cm_2024", 
                   "nlm_icd10_api", "fallback_codes"]
        
        for source in sources:
            self.state_manager.reset_source(source)
        
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
                        await self._save_consolidated_results()
                
                else:
                    logger.debug("No ICD-10 sources ready for retry")
                
                # Wait before next check
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"Error in continuous ICD-10 download process: {e}")
                await asyncio.sleep(check_interval)
    
    async def get_download_status(self) -> Dict[str, Any]:
        """Get current ICD-10 download status and progress"""
        progress = self.state_manager.get_progress_summary()
        ready_sources = self.state_manager.get_ready_for_retry()
        completion_estimate = self.state_manager.estimate_completion_time()
        
        status = {
            "timestamp": datetime.now().isoformat(),
            "data_type": "icd10_codes",
            "progress": progress,
            "ready_for_retry": ready_sources,
            "total_codes_downloaded": self.total_downloaded,
            "completion_estimate": completion_estimate,
            "next_retry_times": {},
            "source_details": {}
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
    
    async def get_codes_statistics(self) -> Dict[str, Any]:
        """Get detailed statistics about downloaded ICD-10 codes"""
        if not self.all_codes:
            await self._load_existing_results()
        
        stats = {
            "total_codes": sum(len(codes) for codes in self.all_codes.values()),
            "by_source": {},
            "by_chapter": {},
            "billable_vs_non_billable": {"billable": 0, "non_billable": 0},
            "code_length_distribution": {},
            "most_common_categories": {}
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
        
        print(f"\n=== Smart ICD-10 Download Summary ===")
        print(f"Total codes downloaded: {summary['total_codes']:,}")
        print(f"Successful sources: {summary['successful_sources']}")
        print(f"Failed sources: {summary['failed_sources']}")
        print(f"Rate limited sources: {summary['rate_limited_sources']}")
        print(f"Success rate: {summary['success_rate']:.1f}%")
        
        print(f"\n=== Expected vs Actual ===")
        print(f"Expected: {summary['expected_vs_actual']['expected_total']}")
        print(f"Actual: {summary['expected_vs_actual']['actual_total']:,}")
        print(f"Improvement: +{summary['expected_vs_actual']['improvement_over_fallback']:,} codes")
        
        print(f"\n=== By Source ===")
        for source, count in summary["by_source_breakdown"].items():
            print(f"{source}: {count:,} codes")
        
        # Show current status
        status = await downloader.get_download_status()
        print(f"\n=== Current Status ===")
        print(json.dumps(status, indent=2, default=str))
        
        # Show code statistics
        stats = await downloader.get_codes_statistics()
        print(f"\n=== Code Statistics ===")
        print(json.dumps(stats, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())