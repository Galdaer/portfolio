"""
ClinicalTrials.gov Smart Downloader
Downloads clinical trial data focusing on drug studies with pediatric, geriatric, and pregnancy populations
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


class ClinicalTrialsDownloadState:
    """State management for ClinicalTrials.gov downloads"""
    
    def __init__(self):
        self.successful_downloads = 0
        self.failed_downloads = 0
        self.rate_limited_count = 0
        self.total_files_downloaded = 0
        self.last_download = None
        self.retry_after = {}  # query -> retry timestamp
        self.completed_queries = set()  # Track which queries completed successfully
        self.downloaded_study_ids = set()  # Track individual study IDs
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


class SmartClinicalTrialsDownloader:
    """Smart downloader for ClinicalTrials.gov data with focus on drug studies"""
    
    def __init__(self, output_dir: Optional[Path] = None, config: Optional[Config] = None):
        self.config = config or Config()
        self.output_dir = output_dir or Path(self.config.get_clinical_trials_data_dir())
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize state
        self.state = ClinicalTrialsDownloadState()
        
        # Rate limiting configuration
        self.rate_limit = self.config.CLINICAL_TRIALS_RATE_LIMIT  # requests per second
        self.request_delay = 1.0 / self.rate_limit if self.rate_limit > 0 else 0.1
        self.retry_attempts = self.config.DRUG_API_RETRY_ATTEMPTS
        self.timeout = self.config.DRUG_API_TIMEOUT
        
        # Downloaded files tracking - NO PARSING
        self.downloaded_files: Dict[str, str] = {}  # query/study_id -> file_path
        self.session: Optional[httpx.AsyncClient] = None
        
        # Drug-related study search parameters
        self.drug_study_fields = [
            'NCTId', 'BriefTitle', 'OfficialTitle', 'OverallStatus',
            'Phase', 'StudyType', 'InterventionType', 'InterventionName',
            'Condition', 'Gender', 'MinimumAge', 'MaximumAge',
            'HealthyVolunteers', 'EligibilityCriteria', 'PrimaryOutcome',
            'SecondaryOutcome', 'StartDate', 'CompletionDate'
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
        state_file = self.output_dir / "clinical_trials_download_state.json"
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state_data = json.load(f)
                    # Restore state
                    self.state.completed_queries = set(state_data.get('completed_queries', []))
                    self.state.downloaded_study_ids = set(state_data.get('downloaded_study_ids', []))
                    self.state.retry_after = state_data.get('retry_after', {})
                    self.state.successful_downloads = state_data.get('successful_downloads', 0)
                    self.state.failed_downloads = state_data.get('failed_downloads', 0)
                    logger.info(f"Loaded ClinicalTrials state: {len(self.state.completed_queries)} completed queries")
                    return state_data
            except Exception as e:
                logger.warning(f"Failed to load ClinicalTrials state: {e}")
        return {}
    
    def _save_state(self):
        """Save download state to file"""
        state_file = self.output_dir / "clinical_trials_download_state.json"
        state_data = {
            'timestamp': datetime.now().isoformat(),
            'completed_queries': list(self.state.completed_queries),
            'downloaded_study_ids': list(self.state.downloaded_study_ids),
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
            logger.error(f"Failed to save ClinicalTrials state: {e}")
    
    async def _load_existing_results(self):
        """Load existing downloaded files - NO PARSING"""
        self._load_state()
        
        # Scan for existing JSON files
        for json_file in self.output_dir.glob("*.json"):
            if json_file.name.endswith("_state.json"):
                continue  # Skip state files
                
            try:
                # Extract query/study identifier from filename
                identifier = json_file.stem  # Remove .json extension
                self.downloaded_files[identifier] = str(json_file)
                logger.debug(f"Found existing ClinicalTrials file: {json_file.name}")
            except Exception as e:
                logger.warning(f"Error processing existing file {json_file}: {e}")
        
        logger.info(f"Loaded {len(self.downloaded_files)} existing ClinicalTrials files")
    
    async def search_drug_studies(
        self, 
        drug_name: str,
        special_populations: List[str] = None,
        page_size: int = 100,
        max_pages: int = 10
    ) -> Optional[str]:
        """Search for drug studies with focus on special populations - saves raw JSON only"""
        
        query_key = f"drug_{drug_name.lower().replace(' ', '_')}"
        
        if query_key in self.state.completed_queries:
            logger.debug(f"ClinicalTrials query {query_key} already completed")
            return self.downloaded_files.get(query_key)
        
        if self.state.is_rate_limited(query_key):
            logger.debug(f"ClinicalTrials query {query_key} is rate limited")
            return None
            
        try:
            # Build search parameters for ClinicalTrials.gov API v2
            search_params = {
                'format': 'json',
                'fields': '|'.join(self.drug_study_fields),
                'query.intr': drug_name,  # Intervention/drug name
                'filter.overallStatus': 'COMPLETED|RECRUITING|ACTIVE_NOT_RECRUITING',
                'pageSize': page_size,
                'countTotal': 'true'  # Get total count for pagination
            }
            
            # Note: Age filters temporarily disabled due to API 400 errors
            # TODO: Research correct age filter values for ClinicalTrials.gov API v2
            # if special_populations:
            #     age_filters = []
            #     if 'pediatric' in special_populations:
            #         age_filters.extend(['Child', 'Infant'])
            #     if 'geriatric' in special_populations:
            #         age_filters.extend(['Older Adult'])
            #     if age_filters:
            #         search_params['filter.ages'] = '|'.join(age_filters)
            
            all_studies = []
            page_count = 0
            next_page_token = None
            
            while page_count < max_pages:
                # Rate limiting
                await asyncio.sleep(self.request_delay)
                
                # Set pagination token if we have one from previous response
                if next_page_token:
                    search_params['pageToken'] = next_page_token
                elif 'pageToken' in search_params:
                    # Remove pageToken for first request
                    del search_params['pageToken']
                
                response = await self.session.get(
                    self.config.CLINICAL_TRIALS_API_BASE_URL + '/v2/studies',
                    params=search_params
                )
                
                if response.status_code == 429:
                    # Rate limited
                    retry_after = int(response.headers.get('Retry-After', 60))
                    self.state.set_rate_limit(query_key, retry_after)
                    logger.warning(f"Rate limited for query {query_key}, retry after {retry_after}s")
                    return None
                    
                response.raise_for_status()
                page_data = response.json()
                
                studies = page_data.get('studies', [])
                if not studies:
                    break  # No more results
                    
                all_studies.extend(studies)
                
                # Track individual study IDs
                for study in studies:
                    nct_id = study.get('protocolSection', {}).get('identificationModule', {}).get('nctId')
                    if nct_id:
                        self.state.downloaded_study_ids.add(nct_id)
                
                page_count += 1
                logger.debug(f"Downloaded page {page_count} for {drug_name}: {len(studies)} studies")
                
                # Check if we have more pages - API v2 returns nextPageToken
                next_page_token = page_data.get('nextPageToken')
                if not next_page_token:
                    break  # No more pages available
            
            # Save raw JSON response - NO PARSING
            output_file = self.output_dir / f"{query_key}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'drug_name': drug_name,
                    'search_params': search_params,
                    'total_studies': len(all_studies),
                    'download_timestamp': datetime.now().isoformat(),
                    'studies': all_studies
                }, f, indent=2, ensure_ascii=False)
            
            self.downloaded_files[query_key] = str(output_file)
            self.state.completed_queries.add(query_key)
            self.state.successful_downloads += 1
            self.state.total_files_downloaded += 1
            
            logger.info(f"Downloaded {len(all_studies)} ClinicalTrials studies for drug: {drug_name}")
            return str(output_file)
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.debug(f"No ClinicalTrials studies found for {drug_name} (404)")
                self.state.completed_queries.add(query_key)  # Don't retry 404s
            else:
                logger.error(f"HTTP error searching for {drug_name}: {e}")
                self.state.failed_downloads += 1
            return None
            
        except Exception as e:
            logger.error(f"Error searching ClinicalTrials for {drug_name}: {e}")
            self.state.failed_downloads += 1
            return None
    
    async def download_special_population_studies(
        self,
        drug_names: Optional[List[str]] = None,
        force_fresh: bool = False,
        max_concurrent: int = 3
    ) -> Dict[str, Any]:
        """Download clinical trials focusing on special populations (pediatric, geriatric, pregnancy)"""
        
        if force_fresh:
            self.state = ClinicalTrialsDownloadState()
            self.downloaded_files.clear()
        
        self.state.download_start_time = datetime.now()
        
        # If no drug names provided, use a curated list focusing on special population usage
        if not drug_names:
            drug_names = [
                # Drugs commonly used in special populations
                "acetaminophen", "ibuprofen", "amoxicillin", "insulin", "methylphenidate",
                "fluoxetine", "sertraline", "risperidone", "aripiprazole", "atomoxetine",
                "metformin", "levothyroxine", "prednisone", "albuterol", "montelukast",
                "azithromycin", "cephalexin", "dextroamphetamine", "clonidine", "guanfacine",
                "warfarin", "digoxin", "furosemide", "lisinopril", "metoprolol",
                "atorvastatin", "simvastatin", "omeprazole", "lansoprazole", "gabapentin"
            ]
        
        logger.info(f"Starting ClinicalTrials download for {len(drug_names)} drugs")
        
        # Define special population categories to search for
        special_population_queries = [
            ('pediatric', ['pediatric']),
            ('geriatric', ['geriatric']),
            ('pregnancy', []),  # Pregnancy studies don't have specific age filters
        ]
        
        # Create download tasks
        semaphore = asyncio.Semaphore(max_concurrent)
        download_tasks = []
        
        async def download_with_semaphore(drug_name: str, pop_type: str, pop_filters: List[str]):
            async with semaphore:
                return await self.search_drug_studies(
                    drug_name=drug_name,
                    special_populations=pop_filters
                )
        
        # Create tasks for each drug and population combination
        for drug_name in drug_names:
            for pop_type, pop_filters in special_population_queries:
                task = download_with_semaphore(drug_name, pop_type, pop_filters)
                download_tasks.append(task)
        
        if download_tasks:
            results = await asyncio.gather(*download_tasks, return_exceptions=True)
            
            # Count successful downloads
            successful_files = [r for r in results if isinstance(r, str) and r is not None]
            logger.info(f"Successfully downloaded {len(successful_files)} ClinicalTrials files")
        
        # Save final state
        self._save_state()
        
        return await self.get_download_summary()
    
    async def get_download_status(self) -> Dict[str, Any]:
        """Get current download status"""
        return {
            'timestamp': datetime.now().isoformat(),
            'data_type': 'clinical_trials_drug_studies',
            'progress': {
                'total_files': self.state.total_files_downloaded,
                'successful_downloads': self.state.successful_downloads,
                'failed_downloads': self.state.failed_downloads,
                'rate_limited_count': self.state.rate_limited_count,
                'completed_queries': len(self.state.completed_queries),
                'unique_studies': len(self.state.downloaded_study_ids)
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
                'clinical_trials': total_files
            },
            'download_stats': {
                'files_processed': total_files,
                'download_errors': self.state.failed_downloads,
                'files_verified': total_files,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'success_rate': (self.state.successful_downloads / max(1, self.state.successful_downloads + self.state.failed_downloads))
            },
            'completed_queries': len(self.state.completed_queries),
            'unique_studies_downloaded': len(self.state.downloaded_study_ids),
            'data_source': 'clinical_trials'
        }
    
    def reset_download_state(self):
        """Reset all download states"""
        self.state = ClinicalTrialsDownloadState()
        self.downloaded_files.clear()
        
        # Remove state file
        state_file = self.output_dir / "clinical_trials_download_state.json"
        if state_file.exists():
            state_file.unlink()
        
        logger.info("Reset ClinicalTrials download state")