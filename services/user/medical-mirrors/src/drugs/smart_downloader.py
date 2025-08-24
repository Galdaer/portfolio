"""
Unified Smart Drug Downloader orchestrating multiple drug data sources
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import time

from .downloader import DrugDownloader
from .rxclass_downloader import SmartRxClassDownloader
from config import Config

logger = logging.getLogger(__name__)


class DrugDownloadState:
    """State management for unified drug downloads"""
    
    def __init__(self):
        self.successful_sources = 0
        self.failed_sources = 0
        self.rate_limited_sources = 0
        self.total_drugs = 0
        self.last_download = None
        self.retry_after = {}  # source -> retry timestamp
        self.daily_retry_counts = {}  # source -> date -> count
        self.completed_sources = set()  # Track which sources completed successfully
        
    def is_rate_limited(self, source: str) -> bool:
        """Check if source is currently rate limited"""
        retry_time = self.retry_after.get(source)
        if retry_time:
            return datetime.now() < datetime.fromisoformat(retry_time)
        return False
        
    def set_rate_limit(self, source: str, retry_after_seconds: int):
        """Set rate limit for a source"""
        retry_time = datetime.now() + timedelta(seconds=retry_after_seconds)
        self.retry_after[source] = retry_time.isoformat()
        self.rate_limited_sources += 1
        
    def get_daily_retry_count(self, source: str) -> int:
        """Get retry count for today"""
        today = datetime.now().date().isoformat()
        return self.daily_retry_counts.get(source, {}).get(today, 0)
        
    def increment_retry_count(self, source: str):
        """Increment daily retry count"""
        today = datetime.now().date().isoformat()
        if source not in self.daily_retry_counts:
            self.daily_retry_counts[source] = {}
        self.daily_retry_counts[source][today] = self.get_daily_retry_count(source) + 1


class SmartDrugDownloader:
    """Unified smart downloader orchestrating multiple drug data sources"""
    
    def __init__(self, output_dir: Optional[Path] = None, config: Optional[Config] = None):
        self.config = config or Config()
        self.output_dir = output_dir or Path("/home/intelluxe/database/medical_complete")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize state
        self.state = DrugDownloadState()
        
        # Initialize source-specific downloaders
        self.fda_downloader = None
        self.rxclass_downloader = None
        
        # Smart retry configuration
        self.retry_interval = 1200  # 20 minutes between retry checks
        self.max_daily_retries = 5   # Lower limit for large downloads
        
        # Source management - track which sources are enabled
        self.sources = {
            'fda': True,        # FDA drug databases
            'rxclass': True,    # RxClass therapeutic classifications
        }
        
    async def __aenter__(self):
        """Async context manager entry"""
        # Initialize source-specific downloaders
        if self.sources['fda']:
            self.fda_downloader = DrugDownloader(config=self.config)
            # Set the output directory manually since DrugDownloader uses data_dir from config
            self.fda_downloader.data_dir = str(self.output_dir / "fda")
            await self.fda_downloader.__aenter__()
            
        if self.sources['rxclass']:
            self.rxclass_downloader = SmartRxClassDownloader(
                output_dir=self.output_dir / "rxclass",
                config=self.config
            )
            await self.rxclass_downloader.__aenter__()
            
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.fda_downloader:
            await self.fda_downloader.__aexit__(exc_type, exc_val, exc_tb)
        if self.rxclass_downloader:
            await self.rxclass_downloader.__aexit__(exc_type, exc_val, exc_tb)
        
    def _load_state(self) -> Dict[str, Any]:
        """Load download state from file"""
        state_file = self.output_dir / "drug_download_state.json"
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state_data = json.load(f)
                    # Restore state
                    self.state.retry_after = state_data.get('retry_after', {})
                    self.state.daily_retry_counts = state_data.get('daily_retry_counts', {})
                    self.state.completed_sources = set(state_data.get('completed_sources', []))
                    return state_data
            except Exception as e:
                logger.warning(f"Failed to load unified drug state file: {e}")
        return {}
        
    def _save_state(self):
        """Save download state to file"""
        state_file = self.output_dir / "drug_download_state.json"
        try:
            state_data = {
                'successful_sources': self.state.successful_sources,
                'failed_sources': self.state.failed_sources,
                'rate_limited_sources': self.state.rate_limited_sources,
                'total_drugs': self.state.total_drugs,
                'last_download': datetime.now().isoformat(),
                'retry_after': self.state.retry_after,
                'daily_retry_counts': self.state.daily_retry_counts,
                'completed_sources': list(self.state.completed_sources)
            }
            with open(state_file, 'w') as f:
                json.dump(state_data, f)
        except Exception as e:
            logger.warning(f"Failed to save unified drug state file: {e}")
    
    async def download_all_drug_data(self, force_fresh: bool = False, complete_dataset: bool = True, sources: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Download all drug data from multiple sources with coordination
        
        Args:
            force_fresh: If True, ignore cached state and start fresh
            complete_dataset: If True, download complete datasets
            sources: List of sources to download (default: all enabled sources)
        """
        logger.info(f"Starting unified drug download (complete_dataset={complete_dataset})")
        
        # Determine which sources to process
        active_sources = sources or [s for s, enabled in self.sources.items() if enabled]
        
        if not force_fresh:
            # Load previous state
            saved_state = self._load_state()
            if saved_state:
                logger.info(f"Loaded previous state: {len(saved_state.get('completed_sources', []))} sources completed")
        
        results = {}
        
        try:
            # Phase 1: Download FDA data (foundational drug information)
            if 'fda' in active_sources and self.fda_downloader:
                logger.info("Phase 1: Downloading FDA drug databases")
                if 'fda' not in self.state.completed_sources or force_fresh:
                    fda_result = await self.fda_downloader.download_all()
                    results['fda'] = fda_result
                    self.state.completed_sources.add('fda')
                    self.state.successful_sources += 1
                    logger.info(f"FDA download completed: {fda_result.get('total_datasets_downloaded', 0)} datasets")
                else:
                    logger.info("FDA download already completed - skipping")
                    
            # Phase 2: Download RxClass classifications (enhances FDA data with therapeutic classes)
            if 'rxclass' in active_sources and self.rxclass_downloader:
                logger.info("Phase 2: Downloading RxClass therapeutic classifications")
                if 'rxclass' not in self.state.completed_sources or force_fresh:
                    # Get drug names from FDA data for classification
                    drug_names = await self._get_drug_names_for_classification()
                    if drug_names:
                        rxclass_result = await self.rxclass_downloader.download_all(drug_names=drug_names, force_fresh=force_fresh)
                        results['rxclass'] = rxclass_result
                        self.state.completed_sources.add('rxclass')
                        self.state.successful_sources += 1
                        logger.info(f"RxClass download completed: {rxclass_result.get('total_drugs_classified', 0)} drugs classified")
                    else:
                        logger.warning("No drug names found for RxClass classification")
                else:
                    logger.info("RxClass download already completed - skipping")
            
            # Update final state
            self.state.total_drugs = sum(r.get('total_drugs_classified', r.get('total_datasets_downloaded', 0)) for r in results.values())
            self._save_state()
            
            return self._get_unified_summary(results)
            
        except Exception as e:
            logger.error(f"Unified drug download failed: {e}")
            self.state.failed_sources += 1
            self._save_state()
            raise
    
    async def _get_drug_names_for_classification(self) -> List[str]:
        """Get unique generic drug names for therapeutic classification"""
        fda_data_dir = self.output_dir / "fda"
        
        # Look for FDA data files
        drug_names = set()
        
        # Check for various FDA data files
        potential_files = [
            fda_data_dir / "all_drug_information_complete.json",
            fda_data_dir / "orange_book.json",
            fda_data_dir / "ndc_directory.json",
            fda_data_dir / "drugs_fda.json"
        ]
        
        for data_file in potential_files:
            if data_file.exists():
                try:
                    with open(data_file, 'r') as f:
                        data = json.load(f)
                    
                    # Extract generic names based on file structure
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                generic_name = item.get('generic_name') or item.get('nonproprietary_name')
                                if generic_name and generic_name.strip():
                                    drug_names.add(generic_name.strip().lower())
                    
                    logger.info(f"Extracted {len(drug_names)} unique drug names from {data_file}")
                    if len(drug_names) > 100:  # Reasonable threshold
                        break  # Use first available file with good data
                    
                except Exception as e:
                    logger.warning(f"Failed to read {data_file}: {e}")
                    continue
        
        if not drug_names:
            logger.warning("No FDA drug data found - using sample drug list for classification")
            # Fallback to common drugs for testing
            drug_names = {"aspirin", "atorvastatin", "metformin", "lisinopril", "amlodipine"}
        
        return list(drug_names)
    
    # Legacy method for backward compatibility
    async def download_all_fda_data(self, force_fresh: bool = False, complete_dataset: bool = True) -> Dict[str, Any]:
        """Download all FDA data - legacy method for backward compatibility"""
        return await self.download_all_drug_data(force_fresh=force_fresh, complete_dataset=complete_dataset, sources=['fda'])
    
    # Main entry points
    async def download_and_parse_all(self, force_fresh: bool = False, complete_dataset: bool = True) -> Dict[str, Any]:
        """Download all drug data from all sources - main entry point"""
        return await self.download_all_drug_data(force_fresh=force_fresh, complete_dataset=complete_dataset)

    async def get_download_status(self) -> Dict[str, Any]:
        """Get current download status and progress across all sources"""
        # Load saved state if available
        self._load_state()
        
        active_sources = [s for s, enabled in self.sources.items() if enabled]
        total_sources = len(active_sources)
        completed = len(self.state.completed_sources)
        
        status = {
            "timestamp": datetime.now().isoformat(),
            "progress": {
                "completed": completed,
                "total_sources": total_sources,
                "completion_rate": (completed / total_sources) * 100 if total_sources > 0 else 0
            },
            "ready_for_retry": [],
            "total_drugs_processed": self.state.total_drugs,
            "next_retry_times": {},
            "completed_sources": list(self.state.completed_sources),
            "source_details": {}
        }
        
        # Get detailed status from each source
        if self.fda_downloader and 'fda' in active_sources:
            try:
                fda_status = await self.fda_downloader.get_download_status()
                status["source_details"]["fda"] = fda_status
            except Exception as e:
                logger.warning(f"Failed to get FDA status: {e}")
        
        if self.rxclass_downloader and 'rxclass' in active_sources:
            try:
                rxclass_status = await self.rxclass_downloader.get_download_status()
                status["source_details"]["rxclass"] = rxclass_status
            except Exception as e:
                logger.warning(f"Failed to get RxClass status: {e}")
        
        # Check which sources are ready for retry
        for source in active_sources:
            if source not in self.state.completed_sources:
                if not self.state.is_rate_limited(source):
                    if self.state.get_daily_retry_count(source) < self.max_daily_retries:
                        status["ready_for_retry"].append(source)
                else:
                    # Add retry time for rate-limited sources
                    retry_time = self.state.retry_after.get(source)
                    if retry_time:
                        status["next_retry_times"][source] = retry_time
        
        return status

    async def reset_download_state(self):
        """Reset all download state across all sources"""
        logger.info("Resetting unified drug download state")
        self.state = DrugDownloadState()
        
        # Reset individual source states
        if self.fda_downloader:
            await self.fda_downloader.reset_download_state()
        if self.rxclass_downloader:
            await self.rxclass_downloader.reset_download_state()
        
        # Remove unified state file
        state_file = self.output_dir / "drug_download_state.json"
        if state_file.exists():
            state_file.unlink()
    
    def _get_unified_summary(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Get unified download summary statistics"""
        active_sources = [s for s, enabled in self.sources.items() if enabled]
        total_sources = len(active_sources)
        success_rate = (len(self.state.completed_sources) / total_sources) * 100 if total_sources > 0 else 0
        
        summary = {
            'total_sources_processed': len(self.state.completed_sources),
            'completed_sources': list(self.state.completed_sources),
            'total_sources': total_sources,
            'successful_sources': len(self.state.completed_sources),
            'failed_sources': self.state.failed_sources,
            'rate_limited_sources': self.state.rate_limited_sources,
            'success_rate': success_rate,
            'total_drugs_processed': self.state.total_drugs,
            'download_timestamp': datetime.now().isoformat(),
            'source_results': results
        }
        
        return summary