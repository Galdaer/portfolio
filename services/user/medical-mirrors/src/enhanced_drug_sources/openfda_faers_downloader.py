"""
OpenFDA FAERS Smart Downloader
Downloads FDA Adverse Event Reporting System data focusing on drug safety in special populations
Follows no-parsing architecture - saves raw JSON responses only
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


class FAERSDownloadState:
    """State management for OpenFDA FAERS downloads"""

    def __init__(self):
        self.successful_downloads = 0
        self.failed_downloads = 0
        self.rate_limited_count = 0
        self.total_files_downloaded = 0
        self.last_download = None
        self.retry_after = {}  # query -> retry timestamp
        self.completed_queries = set()  # Track which queries completed successfully
        self.downloaded_reports = set()  # Track individual report IDs
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


class SmartOpenFDAFAERSDownloader:
    """Smart downloader for OpenFDA FAERS adverse event data"""

    def __init__(self, output_dir: Path | None = None, config: Config | None = None):
        self.config = config or Config()
        self.output_dir = output_dir or Path(self.config.get_openfda_faers_data_dir())
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize state
        self.state = FAERSDownloadState()

        # Rate limiting configuration - OpenFDA allows 240 requests per minute (4 per second)
        self.request_delay = self.config.OPENFDA_REQUEST_DELAY  # Use configured delay directly
        self.retry_attempts = self.config.DRUG_API_RETRY_ATTEMPTS
        self.timeout = self.config.DRUG_API_TIMEOUT

        # Downloaded files tracking - NO PARSING
        self.downloaded_files: dict[str, str] = {}  # query -> file_path
        self.session: httpx.AsyncClient | None = None

        # Special population search terms
        self.special_population_terms = {
            "pediatric": ["infant", "child", "adolescent", "paediatric", "pediatric", "newborn"],
            "geriatric": ["elderly", "geriatric", "aged", "senior"],
            "pregnancy": ["pregnant", "pregnancy", "gravid", "maternal", "prenatal"],
            "nursing": ["lactating", "breastfeeding", "nursing", "breast feeding"],
        }

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
        await self._load_existing_results()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.aclose()

    def _load_state(self) -> dict[str, Any]:
        """Load download state from file"""
        state_file = self.output_dir / "faers_download_state.json"
        if state_file.exists():
            try:
                with open(state_file) as f:
                    state_data = json.load(f)
                    # Restore state
                    self.state.completed_queries = set(state_data.get("completed_queries", []))
                    self.state.downloaded_reports = set(state_data.get("downloaded_reports", []))
                    self.state.retry_after = state_data.get("retry_after", {})
                    self.state.successful_downloads = state_data.get("successful_downloads", 0)
                    self.state.failed_downloads = state_data.get("failed_downloads", 0)
                    logger.info(f"Loaded FAERS state: {len(self.state.completed_queries)} completed queries")
                    return state_data
            except Exception as e:
                logger.warning(f"Failed to load FAERS state: {e}")
        return {}

    def _save_state(self):
        """Save download state to file"""
        state_file = self.output_dir / "faers_download_state.json"
        state_data = {
            "timestamp": datetime.now().isoformat(),
            "completed_queries": list(self.state.completed_queries),
            "downloaded_reports": list(self.state.downloaded_reports),
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
            logger.exception(f"Failed to save FAERS state: {e}")

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
                logger.debug(f"Found existing FAERS file: {json_file.name}")
            except Exception as e:
                logger.warning(f"Error processing existing file {json_file}: {e}")

        logger.info(f"Loaded {len(self.downloaded_files)} existing FAERS files")

    async def search_adverse_events(
        self,
        drug_name: str,
        population_type: str = None,
        date_range: tuple = None,
        limit: int = 1000,
    ) -> str | None:
        """Search for adverse events by drug and population - saves raw JSON only"""

        # Create unique query key
        query_parts = [f"drug_{drug_name.lower().replace(' ', '_')}"]
        if population_type:
            query_parts.append(f"pop_{population_type}")
        if date_range:
            query_parts.append(f"date_{date_range[0]}_{date_range[1]}")

        query_key = "_".join(query_parts)

        if query_key in self.state.completed_queries:
            logger.debug(f"FAERS query {query_key} already completed")
            return self.downloaded_files.get(query_key)

        if self.state.is_rate_limited(query_key):
            logger.debug(f"FAERS query {query_key} is rate limited")
            return None

        try:
            # Build search query for OpenFDA FAERS API
            search_terms = []

            # Add drug name search
            search_terms.append(f'patient.drug.medicinalproduct:"{drug_name}"')

            # Add generic name search as alternative
            search_terms.append(f'patient.drug.activesubstance.activesubstancename:"{drug_name}"')

            # Add population-specific terms
            if population_type and population_type in self.special_population_terms:
                pop_terms = self.special_population_terms[population_type]
                for term in pop_terms:
                    search_terms.append(f'patient.patientagegroup:"{term}"')
                    search_terms.append(f'narrative.narrativeincludeclinical:"{term}"')

            # Combine search terms with OR
            search_query = " OR ".join([f"({term})" for term in search_terms])

            # Build API parameters
            params = {
                "search": search_query,
                "limit": min(limit, 1000),  # OpenFDA max is 1000 per request
            }

            # Add date range if specified
            if date_range:
                params["search"] += f" AND receivedate:[{date_range[0]} TO {date_range[1]}]"

            all_results = []
            skip = 0

            while len(all_results) < limit:
                # Rate limiting
                await asyncio.sleep(self.request_delay)

                # Set skip parameter for pagination
                if skip > 0:
                    params["skip"] = skip

                response = await self.session.get(
                    self.config.OPENFDA_FAERS_API_BASE_URL,
                    params=params,
                )

                if response.status_code == 429:
                    # Rate limited
                    retry_after = int(response.headers.get("Retry-After", 60))
                    self.state.set_rate_limit(query_key, retry_after)
                    logger.warning(f"Rate limited for query {query_key}, retry after {retry_after}s")
                    return None

                if response.status_code == 404:
                    # No results found
                    logger.debug(f"No FAERS results found for {drug_name} in {population_type}")
                    break

                response.raise_for_status()

                # Parse JSON response with error handling
                try:
                    data = response.json()
                except json.JSONDecodeError as e:
                    logger.exception(f"Failed to parse JSON response for {drug_name}: {e}")
                    logger.exception(f"Response content: {response.text[:500]}...")
                    break

                if not isinstance(data, dict):
                    logger.error(f"Expected dict response, got {type(data)}: {data}")
                    break

                results = data.get("results", [])
                if not results:
                    break  # No more results

                all_results.extend(results)

                # Track report IDs
                for result in results:
                    if isinstance(result, dict):
                        # Try multiple possible fields for unique report ID
                        report_id = None
                        for field_name in ["safetyreportid", "receiptdate", "receiptdateformat"]:
                            if field_name in result:
                                report_id = result.get(field_name)
                                break

                        if report_id:
                            self.state.downloaded_reports.add(str(report_id))
                    else:
                        logger.warning(f"Unexpected result type: {type(result)}, value: {result}")

                logger.debug(f"Downloaded batch for {drug_name}: {len(results)} reports")

                # Check if we have more results
                meta = data.get("meta", {})
                total_results = meta.get("results", {}).get("total", 0)
                skip += len(results)

                if skip >= total_results or len(results) < params["limit"]:
                    break  # No more pages

            # Save raw JSON response - NO PARSING
            output_file = self.output_dir / f"{query_key}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump({
                    "drug_name": drug_name,
                    "population_type": population_type,
                    "search_query": search_query,
                    "date_range": date_range,
                    "total_reports": len(all_results),
                    "download_timestamp": datetime.now().isoformat(),
                    "results": all_results,
                }, f, indent=2, ensure_ascii=False)

            self.downloaded_files[query_key] = str(output_file)
            self.state.completed_queries.add(query_key)
            self.state.successful_downloads += 1
            self.state.total_files_downloaded += 1

            logger.info(f"Downloaded {len(all_results)} FAERS adverse event reports for {drug_name}")
            return str(output_file)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.debug(f"No FAERS adverse events found for {drug_name} (404)")
                self.state.completed_queries.add(query_key)  # Don't retry 404s
            else:
                logger.exception(f"HTTP error searching FAERS for {drug_name}: {e}")
                self.state.failed_downloads += 1
            return None

        except Exception as e:
            logger.exception(f"Error searching FAERS for {drug_name}: {e}")
            self.state.failed_downloads += 1
            return None

    async def download_special_population_adverse_events(
        self,
        drug_names: list[str] | None = None,
        force_fresh: bool = False,
        max_concurrent: int = 2,  # Conservative due to rate limits
        date_range: tuple = None,
    ) -> dict[str, Any]:
        """Download adverse events focusing on special populations"""

        if force_fresh:
            self.state = FAERSDownloadState()
            self.downloaded_files.clear()

        self.state.download_start_time = datetime.now()

        # If no drug names provided, use high-priority drugs
        if not drug_names:
            drug_names = [
                # Drugs with known special population concerns
                "warfarin", "digoxin", "lithium", "phenytoin", "carbamazepine",
                "valproic acid", "aspirin", "ibuprofen", "acetaminophen", "codeine",
                "morphine", "fentanyl", "methadone", "tramadol", "oxycodone",
                "fluoxetine", "sertraline", "paroxetine", "citalopram", "escitalopram",
                "risperidone", "olanzapine", "quetiapine", "aripiprazole", "haloperidol",
                "methylphenidate", "atomoxetine", "amphetamine", "dextroamphetamine",
                "insulin", "metformin", "glipizide", "glyburide", "pioglitazone",
            ]

        # Default date range - last 5 years
        if not date_range:
            current_year = datetime.now().year
            date_range = (f"{current_year-5}0101", f"{current_year}1231")

        logger.info(f"Starting FAERS download for {len(drug_names)} drugs")

        # Create download tasks for each drug and population combination
        semaphore = asyncio.Semaphore(max_concurrent)
        download_tasks = []

        async def download_with_semaphore(drug_name: str, pop_type: str):
            async with semaphore:
                return await self.search_adverse_events(
                    drug_name=drug_name,
                    population_type=pop_type,
                    date_range=date_range,
                    limit=500,  # Limit per query to manage data volume
                )

        # Create tasks for each drug and population combination
        population_types = ["pediatric", "geriatric", "pregnancy", "nursing", None]  # None for general population

        for drug_name in drug_names:
            for pop_type in population_types:
                task = download_with_semaphore(drug_name, pop_type)
                download_tasks.append(task)

        if download_tasks:
            results = await asyncio.gather(*download_tasks, return_exceptions=True)

            # Count successful downloads
            successful_files = [r for r in results if isinstance(r, str) and r is not None]
            logger.info(f"Successfully downloaded {len(successful_files)} FAERS files")

        # Save final state
        self._save_state()

        return await self.get_download_summary()

    async def get_download_status(self) -> dict[str, Any]:
        """Get current download status"""
        return {
            "timestamp": datetime.now().isoformat(),
            "data_type": "openfda_faers_adverse_events",
            "progress": {
                "total_files": self.state.total_files_downloaded,
                "successful_downloads": self.state.successful_downloads,
                "failed_downloads": self.state.failed_downloads,
                "rate_limited_count": self.state.rate_limited_count,
                "completed_queries": len(self.state.completed_queries),
                "unique_reports": len(self.state.downloaded_reports),
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
                "openfda_faers": total_files,
            },
            "download_stats": {
                "files_processed": total_files,
                "download_errors": self.state.failed_downloads,
                "files_verified": total_files,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "success_rate": (self.state.successful_downloads / max(1, self.state.successful_downloads + self.state.failed_downloads)),
            },
            "completed_queries": len(self.state.completed_queries),
            "unique_reports_downloaded": len(self.state.downloaded_reports),
            "data_source": "openfda_faers",
        }

    def reset_download_state(self):
        """Reset all download states"""
        self.state = FAERSDownloadState()
        self.downloaded_files.clear()

        # Remove state file
        state_file = self.output_dir / "faers_download_state.json"
        if state_file.exists():
            state_file.unlink()

        logger.info("Reset OpenFDA FAERS download state")
