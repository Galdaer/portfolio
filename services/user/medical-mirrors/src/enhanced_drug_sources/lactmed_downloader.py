"""
LactMed Smart Downloader
Downloads lactation/breastfeeding safety data via NCBI E-utilities
Accesses the LactMed database for drug safety during breastfeeding
Follows no-parsing architecture - saves raw XML responses only
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from config import Config

logger = logging.getLogger(__name__)


class LactMedDownloadState:
    """State management for LactMed downloads"""

    def __init__(self):
        self.successful_downloads = 0
        self.failed_downloads = 0
        self.rate_limited_count = 0
        self.total_files_downloaded = 0
        self.last_download = None
        self.retry_after = {}  # drug -> retry timestamp
        self.completed_queries = set()  # Track which queries completed successfully
        self.downloaded_pmids = set()  # Track individual PubMed IDs
        self.download_start_time = None

    def is_rate_limited(self, drug: str) -> bool:
        """Check if drug query is currently rate limited"""
        retry_time = self.retry_after.get(drug)
        if retry_time:
            return datetime.now() < datetime.fromisoformat(retry_time)
        return False

    def set_rate_limit(self, drug: str, retry_after_seconds: int):
        """Set rate limit for a drug query"""
        retry_time = datetime.now() + timedelta(seconds=retry_after_seconds)
        self.retry_after[drug] = retry_time.isoformat()
        self.rate_limited_count += 1


class SmartLactMedDownloader:
    """Smart downloader for LactMed breastfeeding safety data via NCBI E-utilities"""

    def __init__(self, output_dir: Path | None = None, config: Config | None = None):
        self.config = config or Config()
        self.output_dir = output_dir or Path(self.config.get_lactmed_data_dir())
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize state
        self.state = LactMedDownloadState()

        # Rate limiting configuration (NCBI E-utilities requirements)
        self.request_delay = self.config.PUBMED_REQUEST_DELAY  # Use same limit as PubMed (NCBI E-utilities)
        self.retry_attempts = self.config.DRUG_API_RETRY_ATTEMPTS
        self.timeout = self.config.DRUG_API_TIMEOUT

        # Use PubMed API key if available for higher rate limits
        self.api_key = getattr(self.config, "PUBMED_API_KEY", None)

        # Downloaded files tracking - NO PARSING
        self.downloaded_files: dict[str, str] = {}  # drug_name -> file_path
        self.session: httpx.AsyncClient | None = None

        # NCBI E-utilities base URL from configuration
        self.base_url = self.config.LACTMED_API_BASE_URL

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            headers={
                "User-Agent": "medical-mirrors-lactmed/1.0 (healthcare research; research@intelluxe.ai)",
                "Accept": "application/xml, text/xml, */*",
            },
        )
        await self._load_existing_results()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.aclose()

    def _load_state(self) -> dict[str, Any]:
        """Load download state from file"""
        state_file = self.output_dir / "lactmed_download_state.json"
        if state_file.exists():
            try:
                with open(state_file) as f:
                    state_data = json.load(f)
                    # Restore state
                    self.state.completed_queries = set(state_data.get("completed_queries", []))
                    self.state.downloaded_pmids = set(state_data.get("downloaded_pmids", []))
                    self.state.retry_after = state_data.get("retry_after", {})
                    self.state.successful_downloads = state_data.get("successful_downloads", 0)
                    self.state.failed_downloads = state_data.get("failed_downloads", 0)
                    logger.info(f"Loaded LactMed state: {len(self.state.completed_queries)} completed queries")
                    return state_data
            except Exception as e:
                logger.warning(f"Failed to load LactMed state: {e}")
        return {}

    def _save_state(self):
        """Save download state to file"""
        state_file = self.output_dir / "lactmed_download_state.json"
        state_data = {
            "timestamp": datetime.now().isoformat(),
            "completed_queries": list(self.state.completed_queries),
            "downloaded_pmids": list(self.state.downloaded_pmids),
            "retry_after": self.state.retry_after,
            "successful_downloads": self.state.successful_downloads,
            "failed_downloads": self.state.failed_downloads,
            "rate_limited_count": self.state.rate_limited_count,
            "total_files_downloaded": self.state.total_files_downloaded,
        }

        try:
            with open(state_file, "w") as f:
                json.dump(state_data, f)
        except Exception as e:
            logger.exception(f"Failed to save LactMed state: {e}")

    async def _load_existing_results(self):
        """Load existing downloaded files - NO PARSING"""
        self._load_state()

        # Scan for existing XML files
        for xml_file in self.output_dir.glob("*.xml"):
            if xml_file.name.endswith("_state.xml"):
                continue  # Skip state files

            try:
                # Extract drug identifier from filename
                identifier = xml_file.stem  # Remove .xml extension
                self.downloaded_files[identifier] = str(xml_file)
                logger.debug(f"Found existing LactMed file: {xml_file.name}")
            except Exception as e:
                logger.warning(f"Error processing existing file {xml_file}: {e}")

        logger.info(f"Loaded {len(self.downloaded_files)} existing LactMed files")

    async def search_lactation_data(
        self,
        drug_name: str,
        max_results: int = 20,
    ) -> str | None:
        """Search for lactation safety data via NCBI E-utilities - saves raw XML only"""

        query_key = f"lactmed_{drug_name.lower().replace(' ', '_').replace('-', '_')}"

        if query_key in self.state.completed_queries:
            logger.debug(f"LactMed query {query_key} already completed")
            return self.downloaded_files.get(query_key)

        if self.state.is_rate_limited(drug_name):
            logger.debug(f"LactMed query {query_key} is rate limited")
            return None

        try:
            # Rate limiting (NCBI requires careful rate limiting)
            await asyncio.sleep(self.request_delay)

            # Step 1: Search LactMed database using esearch
            search_url = f"{self.base_url}/esearch.fcgi"
            search_params = {
                "db": "books",  # LactMed is in the books database
                "term": f'"{drug_name}"[Title] AND "LactMed"[Book]',
                "retmax": max_results,
                "retmode": "xml",
                "tool": "medical_mirrors",
                "email": "research@intelluxe.ai",
            }

            if self.api_key:
                search_params["api_key"] = self.api_key

            response = await self.session.get(search_url, params=search_params)

            if response.status_code == 429:
                # Rate limited
                retry_after = int(response.headers.get("Retry-After", 120))
                self.state.set_rate_limit(drug_name, retry_after)
                logger.warning(f"Rate limited for drug {drug_name}, retry after {retry_after}s")
                return None

            response.raise_for_status()
            search_xml = response.text

            # Step 2: If we have results, fetch detailed records using efetch
            # For now, just save the search results as they contain the basic information

            # Save raw XML response - NO PARSING
            output_file = self.output_dir / f"{query_key}.xml"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                f.write(f"<!-- LactMed search for drug: {drug_name} -->\n")
                f.write(f"<!-- Download timestamp: {datetime.now().isoformat()} -->\n")
                f.write(f"<!-- Search parameters: {search_params} -->\n")
                f.write(search_xml)

            self.downloaded_files[query_key] = str(output_file)
            self.state.completed_queries.add(query_key)
            self.state.successful_downloads += 1
            self.state.total_files_downloaded += 1

            logger.info(f"Downloaded LactMed data for drug: {drug_name}")
            return str(output_file)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.debug(f"No LactMed data found for {drug_name} (404)")
                self.state.completed_queries.add(query_key)  # Don't retry 404s
            else:
                logger.exception(f"HTTP error searching LactMed for {drug_name}: {e}")
                self.state.failed_downloads += 1
            return None

        except Exception as e:
            logger.exception(f"Error searching LactMed for {drug_name}: {e}")
            self.state.failed_downloads += 1
            return None

    async def download_lactation_safety_batch(
        self,
        drug_names: list[str] | None = None,
        force_fresh: bool = False,
        max_concurrent: int = 2,  # Low concurrency for NCBI
    ) -> dict[str, Any]:
        """Download lactation safety data for multiple drugs"""

        if force_fresh:
            self.state = LactMedDownloadState()
            self.downloaded_files.clear()

        self.state.download_start_time = datetime.now()

        # If no drug names provided, use drugs commonly prescribed to nursing mothers
        if not drug_names:
            drug_names = [
                # Common drugs prescribed during breastfeeding
                "acetaminophen", "ibuprofen", "aspirin", "naproxen", "diclofenac",
                "amoxicillin", "azithromycin", "cephalexin", "clindamycin", "erythromycin",
                "fluoxetine", "sertraline", "paroxetine", "citalopram", "escitalopram",
                "loratadine", "cetirizine", "fexofenadine", "diphenhydramine",
                "omeprazole", "lansoprazole", "ranitidine", "famotidine",
                "metformin", "insulin", "levothyroxine", "prednisone",
                "albuterol", "montelukast", "budesonide", "fluticasone",
            ]

        logger.info(f"Starting LactMed download for {len(drug_names)} drugs")

        # Create download tasks with low concurrency for NCBI compliance
        semaphore = asyncio.Semaphore(max_concurrent)
        download_tasks = []

        async def download_with_semaphore(drug_name: str):
            async with semaphore:
                return await self.search_lactation_data(drug_name)

        # Create tasks for each drug
        for drug_name in drug_names:
            task = download_with_semaphore(drug_name)
            download_tasks.append(task)

        if download_tasks:
            results = await asyncio.gather(*download_tasks, return_exceptions=True)

            # Count successful downloads
            successful_files = [r for r in results if isinstance(r, str) and r is not None]
            logger.info(f"Successfully downloaded {len(successful_files)} LactMed files")

        # Save final state
        self._save_state()

        return await self.get_download_summary()

    async def get_download_status(self) -> dict[str, Any]:
        """Get current download status"""
        return {
            "timestamp": datetime.now().isoformat(),
            "data_type": "lactmed_breastfeeding_safety",
            "progress": {
                "total_files": self.state.total_files_downloaded,
                "successful_downloads": self.state.successful_downloads,
                "failed_downloads": self.state.failed_downloads,
                "rate_limited_count": self.state.rate_limited_count,
                "completed_queries": len(self.state.completed_queries),
                "unique_pmids": len(self.state.downloaded_pmids),
            },
            "files_downloaded": len(self.downloaded_files),
            "output_directory": str(self.output_dir),
            "state": "completed" if len(self.state.retry_after) == 0 else "in_progress",
        }

    async def get_download_summary(self) -> dict[str, Any]:
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
            "total_files": total_files,
            "successful_sources": 1 if total_files > 0 else 0,
            "failed_sources": 1 if self.state.failed_downloads > 0 else 0,
            "rate_limited_sources": 1 if self.state.rate_limited_count > 0 else 0,
            "success_rate": (self.state.successful_downloads / max(1, self.state.successful_downloads + self.state.failed_downloads)) * 100,
            "by_source_breakdown": {
                "lactmed": total_files,
            },
            "download_stats": {
                "files_processed": total_files,
                "download_errors": self.state.failed_downloads,
                "files_verified": total_files,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "success_rate": (self.state.successful_downloads / max(1, self.state.successful_downloads + self.state.failed_downloads)),
            },
            "completed_queries": len(self.state.completed_queries),
            "unique_records_downloaded": len(self.state.downloaded_pmids),
            "data_source": "lactmed",
        }

    def reset_download_state(self):
        """Reset all download states"""
        self.state = LactMedDownloadState()
        self.downloaded_files.clear()

        # Remove state file
        state_file = self.output_dir / "lactmed_download_state.json"
        if state_file.exists():
            state_file.unlink()

        logger.info("Reset LactMed download state")
