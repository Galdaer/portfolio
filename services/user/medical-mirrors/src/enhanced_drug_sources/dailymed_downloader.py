"""
DailyMed Smart Downloader
Downloads FDA drug labeling data from DailyMed API with focus on pregnancy, pediatric, geriatric, and nursing mothers data
Follows no-parsing architecture - saves raw JSON responses only
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import httpx

from config import Config

logger = logging.getLogger(__name__)


class DailyMedDownloadState:
    """State management for DailyMed downloads"""
    
    def __init__(self):
        self.successful_downloads = 0
        self.failed_downloads = 0
        self.rate_limited_count = 0
        self.total_files_downloaded = 0
        self.last_download = None
        self.retry_after = {}  # drug_name -> retry timestamp
        self.completed_drugs = set()  # Track which drugs completed successfully
        self.download_start_time = None
        
    def is_rate_limited(self, drug_name: str) -> bool:
        """Check if drug is currently rate limited"""
        retry_time = self.retry_after.get(drug_name)
        if retry_time:
            return datetime.now() < datetime.fromisoformat(retry_time)
        return False
        
    def set_rate_limit(self, drug_name: str, retry_after_seconds: int):
        """Set rate limit for a drug"""
        retry_time = datetime.now() + timedelta(seconds=retry_after_seconds)
        self.retry_after[drug_name] = retry_time.isoformat()
        self.rate_limited_count += 1


class SmartDailyMedDownloader:
    """Smart downloader for DailyMed FDA drug labeling data with state management"""
    
    def __init__(self, output_dir: Optional[Path] = None, config: Optional[Config] = None):
        self.config = config or Config()
        self.output_dir = output_dir or Path(self.config.get_dailymed_data_dir())
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize state
        self.state = DailyMedDownloadState()
        
        # Rate limiting configuration
        self.rate_limit = self.config.DAILYMED_RATE_LIMIT  # requests per second
        self.request_delay = 1.0 / self.rate_limit if self.rate_limit > 0 else 0.1
        self.retry_attempts = self.config.DRUG_API_RETRY_ATTEMPTS
        self.timeout = self.config.DRUG_API_TIMEOUT
        
        # Downloaded files tracking - NO PARSING
        self.downloaded_files: Dict[str, str] = {}  # drug_setid -> file_path
        self.session: Optional[httpx.AsyncClient] = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        # Headers for DailyMed API - accepts JSON response
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'Intelluxe-AI-Medical-Mirrors/1.0'
        }
        
        self.session = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            headers=headers
        )
        await self._load_existing_results()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.aclose()
    
    def _load_state(self) -> Dict[str, Any]:
        """Load download state from file"""
        state_file = self.output_dir / "dailymed_download_state.json"
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state_data = json.load(f)
                    # Restore state
                    self.state.completed_drugs = set(state_data.get('completed_drugs', []))
                    self.state.retry_after = state_data.get('retry_after', {})
                    self.state.successful_downloads = state_data.get('successful_downloads', 0)
                    self.state.failed_downloads = state_data.get('failed_downloads', 0)
                    logger.info(f"Loaded DailyMed state: {len(self.state.completed_drugs)} completed drugs")
                    return state_data
            except Exception as e:
                logger.warning(f"Failed to load DailyMed state: {e}")
        return {}
    
    def _save_state(self):
        """Save download state to file"""
        state_file = self.output_dir / "dailymed_download_state.json"
        state_data = {
            'timestamp': datetime.now().isoformat(),
            'completed_drugs': list(self.state.completed_drugs),
            'retry_after': self.state.retry_after,
            'successful_downloads': self.state.successful_downloads,
            'failed_downloads': self.state.failed_downloads,
            'rate_limited_count': self.state.rate_limited_count,
            'total_files_downloaded': self.state.total_files_downloaded
        }
        
        try:
            with open(state_file, 'w') as f:
                json.dump(state_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save DailyMed state: {e}")
    
    async def _load_existing_results(self):
        """Load existing downloaded files - NO PARSING"""
        self._load_state()
        
        # Scan for existing XML and JSON files (XML for SPL data, JSON for search results)
        for data_file in self.output_dir.glob("*"):
            if data_file.name.endswith("_state.json") or not data_file.is_file():
                continue  # Skip state files and directories
                
            try:
                # Extract setid from filename (could be .xml or .json)
                setid = data_file.stem  # Remove extension
                self.downloaded_files[setid] = str(data_file)
                logger.debug(f"Found existing DailyMed file: {data_file.name}")
            except Exception as e:
                logger.warning(f"Error processing existing file {data_file}: {e}")
        
        logger.info(f"Loaded {len(self.downloaded_files)} existing DailyMed files")
    
    async def download_drug_labeling_by_setid(self, setid: str) -> Optional[str]:
        """Download drug labeling by setId - saves raw JSON only"""
        if setid in self.state.completed_drugs:
            logger.debug(f"DailyMed setId {setid} already completed")
            return self.downloaded_files.get(setid)
        
        if self.state.is_rate_limited(setid):
            logger.debug(f"DailyMed setId {setid} is rate limited")
            return None
            
        try:
            # Rate limiting
            await asyncio.sleep(self.request_delay)
            
            # DailyMed API endpoint for SPL data - individual SPLs only support XML format
            url = f"{self.config.DAILYMED_API_BASE_URL}/v2/spls/{setid}.xml"
            
            response = await self.session.get(url)
            
            if response.status_code == 429:
                # Rate limited
                retry_after = int(response.headers.get('Retry-After', 60))
                self.state.set_rate_limit(setid, retry_after)
                logger.warning(f"Rate limited for setId {setid}, retry after {retry_after}s")
                return None
                
            response.raise_for_status()
            
            # Save raw XML response - NO PARSING
            # Individual SPL documents are only available in XML format
            output_file = self.output_dir / f"{setid}.xml"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            self.downloaded_files[setid] = str(output_file)
            self.state.completed_drugs.add(setid)
            self.state.successful_downloads += 1
            self.state.total_files_downloaded += 1
            
            logger.info(f"Downloaded DailyMed labeling for setId {setid}")
            return str(output_file)
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.debug(f"DailyMed setId {setid} not found (404)")
                self.state.completed_drugs.add(setid)  # Don't retry 404s
            else:
                logger.error(f"HTTP error downloading setId {setid}: {e}")
                self.state.failed_downloads += 1
            return None
            
        except Exception as e:
            logger.error(f"Error downloading DailyMed setId {setid}: {e}")
            self.state.failed_downloads += 1
            return None
    
    async def search_drugs_for_download(self, drug_names: List[str], max_per_drug: int = 10) -> List[str]:
        """Search for setIds to download based on drug names"""
        setids_to_download = []
        
        for drug_name in drug_names:
            try:
                # Rate limiting
                await asyncio.sleep(self.request_delay)
                
                # DailyMed search API - .json extension IS required
                search_url = f"{self.config.DAILYMED_API_BASE_URL}/v2/spls.json"
                params = {
                    'drug_name': drug_name,
                    'page_size': max_per_drug
                }
                
                response = await self.session.get(search_url, params=params)
                response.raise_for_status()
                
                search_results = response.json()
                
                # Extract setIds from search results - NO PARSING
                for result in search_results.get('data', []):
                    setid = result.get('setid')
                    if setid and setid not in self.state.completed_drugs:
                        setids_to_download.append(setid)
                
                logger.info(f"Found {len(search_results.get('data', []))} results for drug: {drug_name}")
                
            except Exception as e:
                logger.error(f"Error searching for drug {drug_name}: {e}")
                continue
        
        return setids_to_download
    
    async def download_enhanced_drug_labeling(
        self, 
        drug_names: Optional[List[str]] = None,
        force_fresh: bool = False,
        max_concurrent: int = 5
    ) -> Dict[str, Any]:
        """Download enhanced drug labeling data focusing on special populations"""
        
        if force_fresh:
            self.state = DailyMedDownloadState()
            self.downloaded_files.clear()
        
        self.state.download_start_time = datetime.now()
        
        # If no drug names provided, use a curated list of high-priority drugs
        if not drug_names:
            drug_names = [
                # High-priority drugs with frequent special population usage
                "acetaminophen", "ibuprofen", "aspirin", "metformin", "lisinopril",
                "atorvastatin", "levothyroxine", "metoprolol", "amlodipine", "omeprazole",
                "sertraline", "fluoxetine", "warfarin", "prednisone", "insulin",
                "hydrochlorothiazide", "furosemide", "gabapentin", "tramadol", "oxycodone",
                "morphine", "fentanyl", "amoxicillin", "azithromycin", "ciprofloxacin",
                "cephalexin", "doxycycline", "clindamycin", "vancomycin", "penicillin"
            ]
        
        logger.info(f"Starting DailyMed download for {len(drug_names)} drug names")
        
        # Search for setIds to download
        setids_to_download = await self.search_drugs_for_download(drug_names)
        logger.info(f"Found {len(setids_to_download)} setIds to download")
        
        # Download files concurrently
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def download_with_semaphore(setid: str):
            async with semaphore:
                return await self.download_drug_labeling_by_setid(setid)
        
        download_tasks = [download_with_semaphore(setid) for setid in setids_to_download]
        
        if download_tasks:
            results = await asyncio.gather(*download_tasks, return_exceptions=True)
            
            # Count successful downloads
            successful_files = [r for r in results if isinstance(r, str) and r is not None]
            logger.info(f"Successfully downloaded {len(successful_files)} DailyMed files")
        
        # Save final state
        self._save_state()
        
        return await self.get_download_summary()
    
    async def get_download_status(self) -> Dict[str, Any]:
        """Get current download status"""
        return {
            'timestamp': datetime.now().isoformat(),
            'data_type': 'dailymed_drug_labeling',
            'progress': {
                'total_files': self.state.total_files_downloaded,
                'successful_downloads': self.state.successful_downloads,
                'failed_downloads': self.state.failed_downloads,
                'rate_limited_count': self.state.rate_limited_count,
                'completed_drugs': len(self.state.completed_drugs)
            },
            'files_downloaded': len(self.downloaded_files),
            'output_directory': str(self.output_dir),
            'state': 'completed' if len(self.state.retry_after) == 0 else 'in_progress'
        }
    
    async def get_download_summary(self) -> Dict[str, Any]:
        """Get download summary with file statistics"""
        total_files = len(self.downloaded_files)
        
        # Calculate file size statistics
        total_size = 0
        for file_path in self.downloaded_files.values():
            try:
                total_size += Path(file_path).stat().st_size
            except:
                continue
        
        return {
            'total_files': total_files,
            'successful_sources': 1 if total_files > 0 else 0,
            'failed_sources': 1 if self.state.failed_downloads > 0 else 0,
            'rate_limited_sources': 1 if self.state.rate_limited_count > 0 else 0,
            'success_rate': (self.state.successful_downloads / max(1, self.state.successful_downloads + self.state.failed_downloads)) * 100,
            'by_source_breakdown': {
                'dailymed': total_files
            },
            'download_stats': {
                'files_processed': total_files,
                'download_errors': self.state.failed_downloads,
                'files_verified': total_files,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'success_rate': (self.state.successful_downloads / max(1, self.state.successful_downloads + self.state.failed_downloads))
            },
            'completed_drugs': len(self.state.completed_drugs),
            'data_source': 'dailymed'
        }
    
    def reset_download_state(self):
        """Reset all download states"""
        self.state = DailyMedDownloadState()
        self.downloaded_files.clear()
        
        # Remove state file
        state_file = self.output_dir / "dailymed_download_state.json"
        if state_file.exists():
            state_file.unlink()
        
        logger.info("Reset DailyMed download state")