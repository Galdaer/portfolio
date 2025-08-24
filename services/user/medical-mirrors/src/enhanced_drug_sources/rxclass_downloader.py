"""
Enhanced RxClass API Smart Downloader
Downloads therapeutic classifications and drug relationships from NIH/NLM RxClass API
Focuses on ATC 2025 classifications and therapeutic roles
Follows no-parsing architecture - saves raw JSON responses only
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
import httpx

from config import Config

logger = logging.getLogger(__name__)


class RxClassDownloadState:
    """State management for RxClass downloads"""
    
    def __init__(self):
        self.successful_downloads = 0
        self.failed_downloads = 0
        self.rate_limited_count = 0
        self.total_files_downloaded = 0
        self.last_download = None
        self.retry_after = {}  # query -> retry timestamp
        self.completed_queries = set()  # Track which queries completed successfully
        self.downloaded_class_ids = set()  # Track individual class IDs
        self.download_start_time = None
        
    def is_rate_limited(self, query: str) -> bool:
        """Check if query is currently rate limited"""
        retry_time = self.retry_after.get(query)
        if retry_time:
            return datetime.now() < datetime.fromisoformat(retry_time)
        return False
        
    def set_rate_limit(self, query: str, retry_after_seconds: int):
        """Set rate limit for a query"""
        retry_time = datetime.now() + timedelta(seconds=retry_after_seconds)
        self.retry_after[query] = retry_time.isoformat()
        self.rate_limited_count += 1


class SmartRxClassDownloader:
    """Enhanced smart downloader for RxClass therapeutic classification data"""
    
    def __init__(self, output_dir: Optional[Path] = None, config: Optional[Config] = None):
        self.config = config or Config()
        self.output_dir = output_dir or Path(self.config.get_rxclass_data_dir())
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize state
        self.state = RxClassDownloadState()
        
        # Rate limiting configuration - RxNav allows up to 20 requests per second
        self.rate_limit = min(self.config.RXCLASS_RATE_LIMIT, 20)
        self.request_delay = 1.0 / self.rate_limit if self.rate_limit > 0 else 0.05
        self.retry_attempts = self.config.DRUG_API_RETRY_ATTEMPTS
        self.timeout = self.config.DRUG_API_TIMEOUT
        
        # Downloaded files tracking - NO PARSING
        self.downloaded_files: Dict[str, str] = {}  # query -> file_path
        self.session: Optional[httpx.AsyncClient] = None
        
        # RxClass classification types to download (only validated working sources)
        self.class_types = [
            'ATC',         # ATC Level 1-4 classifications (VERIFIED WORKING)
            'ATCPROD',     # ATC classification of RxNorm drug products (VERIFIED WORKING)
            # Temporarily disabled invalid relaSource values that cause 400 errors:
            # 'CHEM', 'EPC', 'MOA', 'PE', 'PK', 'THERAP', 'VA'
            # TODO: Research correct relaSource parameter names for these classifications
        ]
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        await self._load_existing_results()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.aclose()
    
    def _load_state(self) -> Dict[str, Any]:
        """Load download state from file"""
        state_file = self.output_dir / "rxclass_download_state.json"
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state_data = json.load(f)
                    # Restore state
                    self.state.completed_queries = set(state_data.get('completed_queries', []))
                    self.state.downloaded_class_ids = set(state_data.get('downloaded_class_ids', []))
                    self.state.retry_after = state_data.get('retry_after', {})
                    self.state.successful_downloads = state_data.get('successful_downloads', 0)
                    self.state.failed_downloads = state_data.get('failed_downloads', 0)
                    logger.info(f"Loaded RxClass state: {len(self.state.completed_queries)} completed queries")
                    return state_data
            except Exception as e:
                logger.warning(f"Failed to load RxClass state: {e}")
        return {}
    
    def _save_state(self):
        """Save download state to file"""
        state_file = self.output_dir / "rxclass_download_state.json"
        state_data = {
            'timestamp': datetime.now().isoformat(),
            'completed_queries': list(self.state.completed_queries),
            'downloaded_class_ids': list(self.state.downloaded_class_ids),
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
            logger.error(f"Failed to save RxClass state: {e}")
    
    async def _load_existing_results(self):
        """Load existing downloaded files - NO PARSING"""
        self._load_state()
        
        # Scan for existing JSON files
        for json_file in self.output_dir.glob("*.json"):
            if json_file.name.endswith("_state.json"):
                continue  # Skip state files
                
            try:
                # Extract query identifier from filename
                identifier = json_file.stem  # Remove .json extension
                self.downloaded_files[identifier] = str(json_file)
                logger.debug(f"Found existing RxClass file: {json_file.name}")
            except Exception as e:
                logger.warning(f"Error processing existing file {json_file}: {e}")
        
        logger.info(f"Loaded {len(self.downloaded_files)} existing RxClass files")
    
    async def get_drug_classes(
        self, 
        drug_name: str,
        class_types: List[str] = None
    ) -> Optional[str]:
        """Get drug classifications by drug name - saves raw JSON only"""
        
        query_key = f"drug_classes_{drug_name.lower().replace(' ', '_')}"
        
        if query_key in self.state.completed_queries:
            logger.debug(f"RxClass query {query_key} already completed")
            return self.downloaded_files.get(query_key)
        
        if self.state.is_rate_limited(query_key):
            logger.debug(f"RxClass query {query_key} is rate limited")
            return None
            
        try:
            class_types_to_use = class_types or self.class_types
            all_classifications = {}
            
            for class_type in class_types_to_use:
                # Rate limiting
                await asyncio.sleep(self.request_delay)
                
                # RxClass API endpoint for getting classes by drug name
                # Updated to match official API documentation format
                url = f"{self.config.RXCLASS_API_BASE_URL}/class/byDrugName.json"
                params = {
                    'drugName': drug_name,
                    'relaSource': class_type
                }
                
                response = await self.session.get(url, params=params)
                
                if response.status_code == 429:
                    # Rate limited
                    retry_after = int(response.headers.get('Retry-After', 60))
                    self.state.set_rate_limit(query_key, retry_after)
                    logger.warning(f"Rate limited for query {query_key}, retry after {retry_after}s")
                    return None
                    
                if response.status_code == 404:
                    logger.debug(f"No RxClass data found for {drug_name} in {class_type}")
                    continue
                    
                response.raise_for_status()
                data = response.json()
                
                # Store classification data
                all_classifications[class_type] = data
                
                # Track class IDs
                for class_concept in data.get('drugClassList', []):
                    class_id = class_concept.get('classId')
                    if class_id:
                        self.state.downloaded_class_ids.add(class_id)
                
                logger.debug(f"Downloaded {class_type} classifications for {drug_name}")
            
            if not all_classifications:
                logger.debug(f"No RxClass classifications found for {drug_name}")
                self.state.completed_queries.add(query_key)  # Don't retry if no data
                return None
            
            # Save raw JSON response - NO PARSING
            output_file = self.output_dir / f"{query_key}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'drug_name': drug_name,
                    'class_types_requested': class_types_to_use,
                    'total_class_types': len(all_classifications),
                    'download_timestamp': datetime.now().isoformat(),
                    'classifications': all_classifications
                }, f, indent=2, ensure_ascii=False)
            
            self.downloaded_files[query_key] = str(output_file)
            self.state.completed_queries.add(query_key)
            self.state.successful_downloads += 1
            self.state.total_files_downloaded += 1
            
            logger.info(f"Downloaded RxClass classifications for drug: {drug_name} ({len(all_classifications)} types)")
            return str(output_file)
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting RxClass data for {drug_name}: {e}")
            self.state.failed_downloads += 1
            return None
            
        except Exception as e:
            logger.error(f"Error getting RxClass data for {drug_name}: {e}")
            self.state.failed_downloads += 1
            return None
    
    async def get_class_members(
        self,
        class_id: str,
        class_type: str
    ) -> Optional[str]:
        """Get members of a specific drug class - saves raw JSON only"""
        
        query_key = f"class_members_{class_type}_{class_id}"
        
        if query_key in self.state.completed_queries:
            logger.debug(f"RxClass query {query_key} already completed")
            return self.downloaded_files.get(query_key)
        
        if self.state.is_rate_limited(query_key):
            logger.debug(f"RxClass query {query_key} is rate limited")
            return None
            
        try:
            # Rate limiting
            await asyncio.sleep(self.request_delay)
            
            # RxClass API endpoint for getting class members
            url = f"{self.config.RXCLASS_API_BASE_URL}/classMembers.json"
            params = {
                'classId': class_id,
                'relaSource': class_type
            }
            
            response = await self.session.get(url, params=params)
            
            if response.status_code == 429:
                # Rate limited
                retry_after = int(response.headers.get('Retry-After', 60))
                self.state.set_rate_limit(query_key, retry_after)
                logger.warning(f"Rate limited for query {query_key}, retry after {retry_after}s")
                return None
                
            if response.status_code == 404:
                logger.debug(f"No RxClass members found for class {class_id}")
                self.state.completed_queries.add(query_key)  # Don't retry 404s
                return None
                
            response.raise_for_status()
            data = response.json()
            
            # Save raw JSON response - NO PARSING
            output_file = self.output_dir / f"{query_key}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'class_id': class_id,
                    'class_type': class_type,
                    'total_members': len(data.get('drugMemberGroup', {}).get('drugMember', [])),
                    'download_timestamp': datetime.now().isoformat(),
                    'class_data': data
                }, f, indent=2, ensure_ascii=False)
            
            self.downloaded_files[query_key] = str(output_file)
            self.state.completed_queries.add(query_key)
            self.state.successful_downloads += 1
            self.state.total_files_downloaded += 1
            
            logger.info(f"Downloaded RxClass members for {class_type} class: {class_id}")
            return str(output_file)
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting RxClass members for {class_id}: {e}")
            self.state.failed_downloads += 1
            return None
            
        except Exception as e:
            logger.error(f"Error getting RxClass members for {class_id}: {e}")
            self.state.failed_downloads += 1
            return None
    
    async def download_comprehensive_classifications(
        self,
        drug_names: Optional[List[str]] = None,
        force_fresh: bool = False,
        max_concurrent: int = 5,
        include_class_members: bool = True
    ) -> Dict[str, Any]:
        """Download comprehensive drug classifications from RxClass"""
        
        if force_fresh:
            self.state = RxClassDownloadState()
            self.downloaded_files.clear()
        
        self.state.download_start_time = datetime.now()
        
        # If no drug names provided, use a curated list from existing drug database
        if not drug_names:
            drug_names = [
                # High-priority drugs for classification
                "acetaminophen", "ibuprofen", "aspirin", "metformin", "insulin",
                "lisinopril", "atorvastatin", "levothyroxine", "metoprolol", "amlodipine",
                "omeprazole", "sertraline", "fluoxetine", "warfarin", "prednisone",
                "hydrochlorothiazide", "furosemide", "gabapentin", "tramadol", "morphine",
                "amoxicillin", "azithromycin", "ciprofloxacin", "doxycycline", "cephalexin",
                "simvastatin", "losartan", "carvedilol", "propranolol", "digoxin"
            ]
        
        logger.info(f"Starting RxClass download for {len(drug_names)} drugs")
        
        # Phase 1: Download drug classifications
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def download_with_semaphore(drug_name: str):
            async with semaphore:
                return await self.get_drug_classes(drug_name)
        
        classification_tasks = [download_with_semaphore(drug_name) for drug_name in drug_names]
        
        if classification_tasks:
            results = await asyncio.gather(*classification_tasks, return_exceptions=True)
            successful_files = [r for r in results if isinstance(r, str) and r is not None]
            logger.info(f"Successfully downloaded {len(successful_files)} drug classification files")
        
        # Phase 2: Download class members for discovered classes (optional)
        if include_class_members and len(self.state.downloaded_class_ids) > 0:
            logger.info(f"Downloading members for {len(self.state.downloaded_class_ids)} discovered classes")
            
            member_tasks = []
            for class_id in list(self.state.downloaded_class_ids)[:100]:  # Limit to avoid overload
                for class_type in self.class_types:
                    task = asyncio.create_task(self.get_class_members(class_id, class_type))
                    member_tasks.append(task)
            
            if member_tasks:
                member_results = await asyncio.gather(*member_tasks, return_exceptions=True)
                successful_member_files = [r for r in member_results if isinstance(r, str) and r is not None]
                logger.info(f"Successfully downloaded {len(successful_member_files)} class member files")
        
        # Save final state
        self._save_state()
        
        return await self.get_download_summary()
    
    async def get_download_status(self) -> Dict[str, Any]:
        """Get current download status"""
        return {
            'timestamp': datetime.now().isoformat(),
            'data_type': 'rxclass_therapeutic_classifications',
            'progress': {
                'total_files': self.state.total_files_downloaded,
                'successful_downloads': self.state.successful_downloads,
                'failed_downloads': self.state.failed_downloads,
                'rate_limited_count': self.state.rate_limited_count,
                'completed_queries': len(self.state.completed_queries),
                'unique_classes': len(self.state.downloaded_class_ids)
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
                'rxclass': total_files
            },
            'download_stats': {
                'files_processed': total_files,
                'download_errors': self.state.failed_downloads,
                'files_verified': total_files,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'success_rate': (self.state.successful_downloads / max(1, self.state.successful_downloads + self.state.failed_downloads))
            },
            'completed_queries': len(self.state.completed_queries),
            'unique_classes_discovered': len(self.state.downloaded_class_ids),
            'classification_types': self.class_types,
            'data_source': 'rxclass'
        }
    
    def reset_download_state(self):
        """Reset all download states"""
        self.state = RxClassDownloadState()
        self.downloaded_files.clear()
        
        # Remove state file
        state_file = self.output_dir / "rxclass_download_state.json"
        if state_file.exists():
            state_file.unlink()
        
        logger.info("Reset RxClass download state")