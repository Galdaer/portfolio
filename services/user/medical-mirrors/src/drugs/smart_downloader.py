"""
Smart FDA Downloader with automatic rate limit handling and recovery
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import time
import httpx

from .downloader import DrugDownloader
from .parser import DrugParser
from config import Config

logger = logging.getLogger(__name__)


class FDADownloadState:
    """State management for FDA downloads"""
    
    def __init__(self):
        self.successful_sources = 0
        self.failed_sources = 0
        self.rate_limited_sources = 0
        self.total_drugs = 0
        self.last_download = None
        self.retry_after = {}  # source -> retry timestamp
        self.daily_retry_counts = {}  # source -> date -> count
        self.completed_datasets = set()  # Track which datasets completed successfully
        
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
    """Smart downloader that coordinates FDA downloads with state management"""
    
    def __init__(self, output_dir: Optional[Path] = None, config: Optional[Config] = None):
        self.config = config or Config()
        self.output_dir = output_dir or Path("/home/intelluxe/database/medical_complete/fda")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.state = FDADownloadState()
        self.downloader = DrugDownloader(config)
        # Override downloader's data directory to use our output directory
        self.downloader.data_dir = str(self.output_dir)
        self.parser = DrugParser()
        
        # Smart retry configuration
        self.retry_interval = 1200  # 20 minutes between retry checks for large downloads
        self.max_daily_retries = 5   # Lower limit for large file downloads
        
        # Dataset management
        self.datasets = {
            'orange_book': None,
            'ndc': None,
            'drugs_fda': None,
            'labels': None
        }
        self.all_drugs: List[Dict[str, Any]] = []
        
    async def __aenter__(self):
        """Async context manager entry"""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.downloader.close()
        
    def _load_state(self) -> Dict[str, Any]:
        """Load download state from file"""
        state_file = self.output_dir / "download_state.json"
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state_data = json.load(f)
                    # Restore state
                    self.state.retry_after = state_data.get('retry_after', {})
                    self.state.daily_retry_counts = state_data.get('daily_retry_counts', {})
                    self.state.completed_datasets = set(state_data.get('completed_datasets', []))
                    return state_data
            except Exception as e:
                logger.warning(f"Failed to load state file: {e}")
        return {}
        
    def _save_state(self):
        """Save download state to file"""
        state_file = self.output_dir / "download_state.json"
        try:
            state_data = {
                'successful_sources': self.state.successful_sources,
                'failed_sources': self.state.failed_sources,
                'rate_limited_sources': self.state.rate_limited_sources,
                'total_drugs': self.state.total_drugs,
                'last_download': datetime.now().isoformat(),
                'retry_after': self.state.retry_after,
                'daily_retry_counts': self.state.daily_retry_counts,
                'completed_datasets': list(self.state.completed_datasets)
            }
            with open(state_file, 'w') as f:
                json.dump(state_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save state file: {e}")
    
    async def download_all_fda_data(self, force_fresh: bool = False, complete_dataset: bool = True) -> Dict[str, Any]:
        """
        Download all FDA data with automatic retry handling
        
        Args:
            force_fresh: If True, ignore cached state and start fresh
            complete_dataset: If True, download complete dataset (default for FDA)
        """
        logger.info(f"Starting smart FDA download (complete_dataset={complete_dataset})")
        
        if not force_fresh:
            # Load previous state
            saved_state = self._load_state()
            if saved_state:
                logger.info(f"Loaded previous state: {saved_state.get('total_drugs', 0)} drugs")
        
        try:
            # Download each FDA dataset
            await self._download_orange_book()
            await self._download_ndc_directory()
            await self._download_drugs_fda()
            await self._download_drug_labels()
            
            # Parse and validate all downloaded files
            await self._parse_all_files()
            
            # Save final results
            await self._save_results()
            
            # Update state
            self.state.successful_sources = len(self.state.completed_datasets)
            self.state.total_drugs = len(self.all_drugs)
            self._save_state()
            
            return self._get_summary()
            
        except Exception as e:
            logger.error(f"Smart FDA download failed: {e}")
            self.state.failed_sources += 1
            self._save_state()
            raise
    
    async def _download_orange_book(self):
        """Download FDA Orange Book"""
        source = "orange_book"
        
        if source in self.state.completed_datasets:
            logger.info(f"Skipping {source} - already completed")
            return
            
        if self.state.is_rate_limited(source):
            logger.info(f"Skipping {source} - rate limited")
            return
            
        if self.state.get_daily_retry_count(source) >= self.max_daily_retries:
            logger.info(f"Skipping {source} - daily retry limit reached")
            return
        
        try:
            logger.info("Downloading FDA Orange Book")
            self.datasets[source] = await self.downloader.download_orange_book()
            self.state.completed_datasets.add(source)
            logger.info(f"Successfully downloaded {source}")
            
        except Exception as e:
            logger.error(f"Failed to download {source}: {e}")
            self.state.increment_retry_count(source)
            
            # Set retry delay based on error type
            if "429" in str(e) or "rate" in str(e).lower():
                self.state.set_rate_limit(source, 3600)  # 1 hour for rate limits
            elif "timeout" in str(e).lower() or "network" in str(e).lower():
                self.state.set_rate_limit(source, 1800)  # 30 minutes for network issues
            else:
                self.state.set_rate_limit(source, 1200)  # 20 minutes for other issues
            raise
    
    async def _download_ndc_directory(self):
        """Download FDA NDC Directory"""
        source = "ndc"
        
        if source in self.state.completed_datasets:
            logger.info(f"Skipping {source} - already completed")
            return
            
        if self.state.is_rate_limited(source):
            logger.info(f"Skipping {source} - rate limited")
            return
            
        if self.state.get_daily_retry_count(source) >= self.max_daily_retries:
            logger.info(f"Skipping {source} - daily retry limit reached")
            return
        
        try:
            logger.info("Downloading FDA NDC Directory")
            self.datasets[source] = await self.downloader.download_ndc_directory()
            self.state.completed_datasets.add(source)
            logger.info(f"Successfully downloaded {source}")
            
        except Exception as e:
            logger.error(f"Failed to download {source}: {e}")
            self.state.increment_retry_count(source)
            
            # Set retry delay based on error type
            if "429" in str(e) or "rate" in str(e).lower():
                self.state.set_rate_limit(source, 3600)  # 1 hour for rate limits
            elif "timeout" in str(e).lower() or "network" in str(e).lower():
                self.state.set_rate_limit(source, 1800)  # 30 minutes for network issues
            else:
                self.state.set_rate_limit(source, 1200)  # 20 minutes for other issues
            raise
    
    async def _download_drugs_fda(self):
        """Download Drugs@FDA database"""
        source = "drugs_fda"
        
        if source in self.state.completed_datasets:
            logger.info(f"Skipping {source} - already completed")
            return
            
        if self.state.is_rate_limited(source):
            logger.info(f"Skipping {source} - rate limited")
            return
            
        if self.state.get_daily_retry_count(source) >= self.max_daily_retries:
            logger.info(f"Skipping {source} - daily retry limit reached")
            return
        
        try:
            logger.info("Downloading Drugs@FDA database")
            self.datasets[source] = await self.downloader.download_drugs_at_fda()
            self.state.completed_datasets.add(source)
            logger.info(f"Successfully downloaded {source}")
            
        except Exception as e:
            logger.error(f"Failed to download {source}: {e}")
            self.state.increment_retry_count(source)
            
            # Set retry delay based on error type
            if "429" in str(e) or "rate" in str(e).lower():
                self.state.set_rate_limit(source, 3600)  # 1 hour for rate limits
            elif "timeout" in str(e).lower() or "network" in str(e).lower():
                self.state.set_rate_limit(source, 1800)  # 30 minutes for network issues
            else:
                self.state.set_rate_limit(source, 1200)  # 20 minutes for other issues
            raise
    
    async def _download_drug_labels(self):
        """Download FDA drug labeling data"""
        source = "labels"
        
        if source in self.state.completed_datasets:
            logger.info(f"Skipping {source} - already completed")
            return
            
        if self.state.is_rate_limited(source):
            logger.info(f"Skipping {source} - rate limited")
            return
            
        if self.state.get_daily_retry_count(source) >= self.max_daily_retries:
            logger.info(f"Skipping {source} - daily retry limit reached")
            return
        
        try:
            logger.info("Downloading FDA drug labels")
            self.datasets[source] = await self.downloader.download_drug_labels()
            self.state.completed_datasets.add(source)
            logger.info(f"Successfully downloaded {source}")
            
        except Exception as e:
            logger.error(f"Failed to download {source}: {e}")
            self.state.increment_retry_count(source)
            
            # Set retry delay based on error type
            if "429" in str(e) or "rate" in str(e).lower():
                self.state.set_rate_limit(source, 3600)  # 1 hour for rate limits
            elif "timeout" in str(e).lower() or "network" in str(e).lower():
                self.state.set_rate_limit(source, 1800)  # 30 minutes for network issues
            else:
                self.state.set_rate_limit(source, 1200)  # 20 minutes for other issues
            raise
    
    async def _parse_all_files(self):
        """Parse all downloaded FDA files"""
        logger.info("Parsing downloaded FDA files")
        
        # Get all available files from downloader
        available_files = await self.downloader.get_available_files()
        
        for dataset_name, file_list in available_files.items():
            if not file_list:
                continue
                
            logger.info(f"Parsing {len(file_list)} files from {dataset_name}")
            
            for file_path in file_list:
                try:
                    # Parse drugs from file
                    drugs = self.parser.parse_file(file_path, dataset_name)
                    
                    # Validate and add drugs
                    for drug in drugs:
                        validated_drug = self._validate_drug(drug, dataset_name)
                        if validated_drug:
                            self.all_drugs.append(validated_drug)
                            
                    logger.info(f"Parsed {len(drugs)} drugs from {file_path}")
                    
                except Exception as e:
                    logger.error(f"Failed to parse {file_path}: {e}")
                    continue
        
        logger.info(f"Total parsed drugs: {len(self.all_drugs)}")
    
    def _validate_drug(self, drug: Dict[str, Any], dataset: str) -> Optional[Dict[str, Any]]:
        """Validate and clean drug data"""
        try:
            # Ensure required fields (varies by dataset)
            drug_id = drug.get('ndc') or drug.get('application_number') or drug.get('id')
            if not drug_id:
                return None
                
            # Clean and validate data
            validated = {
                'drug_id': str(drug_id),
                'ndc': drug.get('ndc', ''),
                'application_number': drug.get('application_number', ''),
                'name': drug.get('name', '').strip(),
                'generic_name': drug.get('generic_name', '').strip(),
                'brand_name': drug.get('brand_name', '').strip(),
                'manufacturer': drug.get('manufacturer', '').strip(),
                'dosage_form': drug.get('dosage_form', '').strip(),
                'route': drug.get('route', '').strip(),
                'strength': drug.get('strength', '').strip(),
                'approval_date': drug.get('approval_date', ''),
                'marketing_status': drug.get('marketing_status', '').strip(),
                'active_ingredients': drug.get('active_ingredients', []),
                'indications': drug.get('indications', '').strip(),
                'warnings': drug.get('warnings', '').strip(),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'source': f'smart_fda_downloader_{dataset}',
                'dataset': dataset
            }
            
            # Add search text for full-text search
            search_components = [
                validated['name'],
                validated['generic_name'],
                validated['brand_name'],
                validated['manufacturer'],
                validated['dosage_form'],
                validated['route'],
                validated['strength'],
                validated['marketing_status'],
                ' '.join(validated['active_ingredients']) if isinstance(validated['active_ingredients'], list) else str(validated['active_ingredients']),
                validated['indications'],
                validated['warnings']
            ]
            validated['search_text'] = ' '.join(filter(None, search_components))
            
            return validated
            
        except Exception as e:
            logger.warning(f"Failed to validate drug {drug.get('name', 'unknown')}: {e}")
            return None
    
    async def _save_results(self):
        """Save all validated drugs to JSON file"""
        output_file = self.output_dir / 'all_drug_information_complete.json'
        
        try:
            with open(output_file, 'w') as f:
                json.dump(self.all_drugs, f, indent=2)
            
            logger.info(f"Saved {len(self.all_drugs)} drugs to {output_file}")
            
            # Also save summary statistics
            stats_file = self.output_dir / 'download_stats.json'
            stats = {
                'total_drugs': len(self.all_drugs),
                'completed_datasets': list(self.state.completed_datasets),
                'total_datasets': len(self.datasets),
                'download_date': datetime.now().isoformat(),
                'sources': list(self.datasets.keys())
            }
            
            with open(stats_file, 'w') as f:
                json.dump(stats, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
            raise
    
    async def get_download_status(self) -> Dict[str, Any]:
        """Get current download status and progress"""
        # Load saved state if available
        self._load_state()
        
        total_sources = len(self.datasets)
        completed = len(self.state.completed_datasets)
        
        status = {
            "timestamp": datetime.now().isoformat(),
            "progress": {
                "completed": completed,
                "total_sources": total_sources,
                "completion_rate": (completed / total_sources) * 100 if total_sources > 0 else 0
            },
            "ready_for_retry": [],
            "total_drugs_downloaded": len(self.all_drugs),
            "next_retry_times": {},
            "completed_datasets": list(self.state.completed_datasets)
        }
        
        # Check which sources are ready for retry
        for source in self.datasets.keys():
            if source not in self.state.completed_datasets:
                if not self.state.is_rate_limited(source):
                    if self.state.get_daily_retry_count(source) < self.max_daily_retries:
                        status["ready_for_retry"].append(source)
                else:
                    # Add retry time for rate-limited sources
                    retry_time = self.state.retry_after.get(source)
                    if retry_time:
                        status["next_retry_times"][source] = retry_time
        
        return status
    
    def _get_summary(self) -> Dict[str, Any]:
        """Get download summary statistics"""
        total_sources = len(self.datasets)
        success_rate = (len(self.state.completed_datasets) / total_sources) * 100 if total_sources > 0 else 0
        
        return {
            'total_drugs': len(self.all_drugs),
            'completed_datasets': list(self.state.completed_datasets),
            'total_datasets': total_sources,
            'successful_sources': len(self.state.completed_datasets),
            'failed_sources': self.state.failed_sources,
            'rate_limited_sources': self.state.rate_limited_sources,
            'success_rate': success_rate,
            'download_timestamp': datetime.now().isoformat()
        }