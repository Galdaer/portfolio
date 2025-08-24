"""
Smart RxClass Downloader for therapeutic drug classifications
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import aiohttp

from config import Config
from rxclass_api import RxClassAPI

logger = logging.getLogger(__name__)


class RxClassDownloadState:
    """State management for RxClass downloads"""
    
    def __init__(self):
        self.successful_sources = 0
        self.failed_sources = 0
        self.total_drugs_classified = 0
        self.last_download = None
        self.retry_after = {}  # source -> retry timestamp
        self.daily_retry_counts = {}  # source -> date -> count
        self.completed_batches = set()  # Track which batches completed successfully
        
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


class SmartRxClassDownloader:
    """Smart downloader for RxClass therapeutic classification data"""
    
    def __init__(self, output_dir: Optional[Path] = None, config: Optional[Config] = None):
        self.config = config or Config()
        self.output_dir = output_dir or Path("/home/intelluxe/database/medical_complete/rxclass")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.state = RxClassDownloadState()
        
        # Smart retry configuration for API calls
        self.retry_interval = 300   # 5 minutes between retry checks for API calls
        self.max_daily_retries = 10 # Higher limit for API calls
        self.rate_limit_delay = 0.1 # 100ms between API calls
        
        # Classification tracking
        self.batch_size = 100
        
    async def __aenter__(self):
        """Async context manager entry"""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        pass
        
    def _load_state(self) -> Dict[str, Any]:
        """Load download state from file"""
        state_file = self.output_dir / "rxclass_download_state.json"
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state_data = json.load(f)
                    # Restore state
                    self.state.retry_after = state_data.get('retry_after', {})
                    self.state.daily_retry_counts = state_data.get('daily_retry_counts', {})
                    self.state.completed_batches = set(state_data.get('completed_batches', []))
                    return state_data
            except Exception as e:
                logger.warning(f"Failed to load RxClass state file: {e}")
        return {}
        
    def _save_state(self):
        """Save download state to file"""
        state_file = self.output_dir / "rxclass_download_state.json"
        try:
            state_data = {
                'successful_sources': self.state.successful_sources,
                'failed_sources': self.state.failed_sources,
                'total_drugs_classified': self.state.total_drugs_classified,
                'last_download': datetime.now().isoformat(),
                'retry_after': self.state.retry_after,
                'daily_retry_counts': self.state.daily_retry_counts,
                'completed_batches': list(self.state.completed_batches)
            }
            with open(state_file, 'w') as f:
                json.dump(state_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save RxClass state file: {e}")
    
    async def download_drug_classifications(self, drug_names: List[str], force_fresh: bool = False) -> Dict[str, Any]:
        """
        Download therapeutic classifications for a list of drug names
        
        Args:
            drug_names: List of generic drug names to classify
            force_fresh: If True, ignore cached state and start fresh
        """
        logger.info(f"Starting RxClass classification download for {len(drug_names)} drugs")
        
        if not force_fresh:
            # Load previous state
            saved_state = self._load_state()
            if saved_state:
                logger.info(f"Loaded previous state: {len(saved_state.get('completed_batches', []))} batches completed")
        
        classifications_file = self.output_dir / "drug_classifications.json"
        all_classifications = {}
        
        # Load existing classifications if they exist
        if classifications_file.exists() and not force_fresh:
            try:
                with open(classifications_file, 'r') as f:
                    all_classifications = json.load(f)
                logger.info(f"Loaded {len(all_classifications)} existing classifications")
            except Exception as e:
                logger.warning(f"Failed to load existing classifications: {e}")
        
        try:
            # Process drugs in batches
            async with RxClassAPI(rate_limit_delay=self.rate_limit_delay) as rxclass:
                total_batches = (len(drug_names) + self.batch_size - 1) // self.batch_size
                
                for batch_idx in range(total_batches):
                    batch_key = f"batch_{batch_idx}"
                    
                    if batch_key in self.state.completed_batches and not force_fresh:
                        logger.info(f"Skipping {batch_key} - already completed")
                        continue
                    
                    start_idx = batch_idx * self.batch_size
                    end_idx = min(start_idx + self.batch_size, len(drug_names))
                    batch_drugs = drug_names[start_idx:end_idx]
                    
                    logger.info(f"Processing batch {batch_idx + 1}/{total_batches}: {len(batch_drugs)} drugs")
                    
                    try:
                        # Get classifications for this batch
                        batch_classifications = await rxclass.batch_classify_drugs(
                            batch_drugs, 
                            max_concurrent=3  # Conservative concurrency for API
                        )
                        
                        # Merge with existing classifications
                        all_classifications.update(batch_classifications)
                        
                        # Save progress after each batch
                        with open(classifications_file, 'w') as f:
                            json.dump(all_classifications, f, indent=2)
                        
                        self.state.completed_batches.add(batch_key)
                        self.state.total_drugs_classified += len(batch_classifications)
                        self._save_state()
                        
                        logger.info(f"Completed batch {batch_idx + 1}: {len(batch_classifications)} drugs classified")
                        
                        # Small delay between batches
                        if batch_idx < total_batches - 1:
                            await asyncio.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Failed to process batch {batch_idx + 1}: {e}")
                        self.state.failed_sources += 1
                        self.state.increment_retry_count(batch_key)
                        
                        # Set retry delay for this batch
                        if "429" in str(e) or "rate" in str(e).lower():
                            self.state.set_rate_limit(batch_key, 3600)  # 1 hour for rate limits
                        elif "timeout" in str(e).lower() or "network" in str(e).lower():
                            self.state.set_rate_limit(batch_key, 900)   # 15 minutes for network issues
                        else:
                            self.state.set_rate_limit(batch_key, 300)   # 5 minutes for other issues
                        
                        self._save_state()
                        continue  # Continue with next batch
            
            # Update final state
            self.state.successful_sources = len(self.state.completed_batches)
            self._save_state()
            
            logger.info(f"RxClass classification download completed: {len(all_classifications)} drugs classified")
            
            return self._get_summary(all_classifications)
            
        except Exception as e:
            logger.error(f"RxClass classification download failed: {e}")
            self._save_state()
            raise
    
    async def download_all(self, drug_names: Optional[List[str]] = None, force_fresh: bool = False) -> Dict[str, Any]:
        """
        Main entry point - download classifications for all provided drugs
        """
        if not drug_names:
            # If no drug names provided, try to load from FDA data
            drug_names = await self._get_drug_names_from_fda_data()
        
        return await self.download_drug_classifications(drug_names, force_fresh)
    
    async def _get_drug_names_from_fda_data(self) -> List[str]:
        """Get unique generic drug names from FDA download data"""
        fda_data_dir = Path("/home/intelluxe/database/medical_complete/fda")
        
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
                    break  # Use first available file
                    
                except Exception as e:
                    logger.warning(f"Failed to read {data_file}: {e}")
                    continue
        
        if not drug_names:
            logger.warning("No FDA drug data found - using sample drug list")
            # Fallback to common drugs for testing
            drug_names = {"aspirin", "atorvastatin", "metformin", "lisinopril", "amlodipine"}
        
        return list(drug_names)
    
    async def get_download_status(self) -> Dict[str, Any]:
        """Get current download status and progress"""
        # Load saved state if available
        self._load_state()
        
        status = {
            "timestamp": datetime.now().isoformat(),
            "progress": {
                "completed_batches": len(self.state.completed_batches),
                "total_drugs_classified": self.state.total_drugs_classified,
            },
            "ready_for_retry": [],
            "next_retry_times": {},
            "completed_batches": list(self.state.completed_batches)
        }
        
        return status

    async def reset_download_state(self):
        """Reset all download state"""
        logger.info("Resetting RxClass download state")
        self.state = RxClassDownloadState()
        
        # Remove state file
        state_file = self.output_dir / "rxclass_download_state.json"
        if state_file.exists():
            state_file.unlink()
    
    def _get_summary(self, classifications: Dict[str, Dict[str, List[str]]]) -> Dict[str, Any]:
        """Get download summary statistics"""
        
        # Count classification types
        type_counts = {}
        for drug_classifications in classifications.values():
            for class_type in drug_classifications.keys():
                type_counts[class_type] = type_counts.get(class_type, 0) + 1
        
        return {
            'total_drugs_classified': len(classifications),
            'classification_type_counts': type_counts,
            'completed_batches': len(self.state.completed_batches),
            'successful_sources': self.state.successful_sources,
            'failed_sources': self.state.failed_sources,
            'download_timestamp': datetime.now().isoformat(),
            'output_file': str(self.output_dir / "drug_classifications.json")
        }