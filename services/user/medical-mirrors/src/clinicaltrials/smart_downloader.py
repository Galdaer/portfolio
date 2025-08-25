"""
Smart ClinicalTrials Downloader with automatic rate limit handling and recovery
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from config import Config

from .downloader import ClinicalTrialsDownloader

logger = logging.getLogger(__name__)


class ClinicalTrialsDownloadState:
    """State management for ClinicalTrials downloads"""

    def __init__(self):
        self.successful_sources = 0
        self.failed_sources = 0
        self.rate_limited_sources = 0
        self.total_studies = 0
        self.last_download = None
        self.retry_after = {}  # source -> retry timestamp
        self.daily_retry_counts = {}  # source -> date -> count
        self.last_batch_processed = 0  # Track progress for resume capability

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


class SmartClinicalTrialsDownloader:
    """Smart downloader that coordinates ClinicalTrials downloads with state management"""

    def __init__(self, output_dir: Path | None = None, config: Config | None = None):
        self.config = config or Config()
        self.output_dir = output_dir or Path("/home/intelluxe/database/medical_complete/clinicaltrials")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.state = ClinicalTrialsDownloadState()
        self.downloader = ClinicalTrialsDownloader(config=self.config)
        # Override downloader's data directory to use our output directory
        self.downloader.data_dir = str(self.output_dir)

        # Smart retry configuration
        self.retry_interval = 600  # 10 minutes between retry checks
        self.max_daily_retries = 20  # Higher limit for API-based source
        self.batch_size = 10000  # Studies per batch - increased for efficiency

        # File management - track downloaded files only
        self.batch_files: list[str] = []
        self.update_files: list[str] = []

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.downloader.close()

    def _load_state(self) -> dict[str, Any]:
        """Load download state from file"""
        state_file = self.output_dir / "download_state.json"
        if state_file.exists():
            try:
                with open(state_file) as f:
                    state_data = json.load(f)
                    # Restore state
                    self.state.last_batch_processed = state_data.get("last_batch_processed", 0)
                    self.state.retry_after = state_data.get("retry_after", {})
                    self.state.daily_retry_counts = state_data.get("daily_retry_counts", {})
                    return state_data
            except Exception as e:
                logger.warning(f"Failed to load state file: {e}")
        return {}

    def _save_state(self):
        """Save download state to file"""
        state_file = self.output_dir / "download_state.json"
        try:
            state_data = {
                "successful_sources": self.state.successful_sources,
                "failed_sources": self.state.failed_sources,
                "rate_limited_sources": self.state.rate_limited_sources,
                "total_studies": self.state.total_studies,
                "last_download": datetime.now().isoformat(),
                "retry_after": self.state.retry_after,
                "daily_retry_counts": self.state.daily_retry_counts,
                "last_batch_processed": self.state.last_batch_processed,
                "batch_count": len(self.batch_files),
                "update_count": len(self.update_files),
            }
            with open(state_file, "w") as f:
                json.dump(state_data, f)
        except Exception as e:
            logger.warning(f"Failed to save state file: {e}")

    async def download_all_clinical_trials(self, force_fresh: bool = False, complete_dataset: bool = True) -> dict[str, Any]:
        """
        Download all ClinicalTrials data with automatic retry handling

        Args:
            force_fresh: If True, ignore cached state and start fresh
            complete_dataset: If True, download complete dataset (default for ClinicalTrials)
        """
        logger.info(f"Starting smart ClinicalTrials download (complete_dataset={complete_dataset})")

        if not force_fresh:
            # Load previous state
            saved_state = self._load_state()
            if saved_state:
                logger.info(f"Loaded previous state: {saved_state.get('total_studies', 0)} studies")

        try:
            # Download all studies in batches
            await self._download_all_studies()

            # Download recent updates
            await self._download_recent_updates()

            # Update state - track by files downloaded, not parsed studies
            self.state.successful_sources = 2  # all_studies + updates
            self.state.total_studies = len(self.batch_files) + len(self.update_files)  # Track files, not studies
            self._save_state()

            return self._get_summary()

        except Exception as e:
            logger.exception(f"Smart ClinicalTrials download failed: {e}")
            self.state.failed_sources += 1
            self._save_state()
            raise

    async def _download_all_studies(self):
        """Download all ClinicalTrials studies with resume capability"""
        source = "clinical_trials_all"

        if self.state.is_rate_limited(source):
            logger.info(f"Skipping {source} - rate limited")
            return

        if self.state.get_daily_retry_count(source) >= self.max_daily_retries:
            logger.info(f"Skipping {source} - daily retry limit reached")
            return

        try:
            logger.info("Downloading all ClinicalTrials studies")

            # Resume from last batch if available
            start = max(1, self.state.last_batch_processed + 1)

            while True:
                try:
                    batch_file = await self.downloader.download_studies_batch(start, self.batch_size)
                    if not batch_file:
                        break

                    self.batch_files.append(batch_file)
                    self.state.last_batch_processed = start
                    start += self.batch_size

                    # Save state periodically for resume capability
                    if len(self.batch_files) % 10 == 0:
                        self._save_state()
                        logger.info(f"Progress: {len(self.batch_files)} batches downloaded")

                    # Use ClinicalTrials-specific rate limit (0.83 req/sec max)
                    await asyncio.sleep(self.config.CLINICALTRIALS_REQUEST_DELAY)

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:  # Rate limited
                        retry_after = int(e.response.headers.get("retry-after", 300))
                        logger.warning(f"Rate limited, waiting {retry_after} seconds")
                        self.state.set_rate_limit(source, retry_after)
                        await asyncio.sleep(retry_after)
                        continue
                    if 500 <= e.response.status_code < 600:  # Server error
                        logger.warning(f"Server error {e.response.status_code}, retrying in 60s")
                        await asyncio.sleep(60)
                        continue
                    raise
                except httpx.RequestError as e:
                    logger.warning(f"Network error: {e}, retrying in 30s")
                    await asyncio.sleep(30)
                    continue

            logger.info(f"Downloaded {len(self.batch_files)} study batches")

        except Exception as e:
            logger.exception(f"Failed to download all studies: {e}")
            self.state.increment_retry_count(source)

            # Set retry delay based on error type
            if "429" in str(e) or "rate" in str(e).lower():
                self.state.set_rate_limit(source, 3600)  # 1 hour for rate limits
            elif "timeout" in str(e).lower() or "network" in str(e).lower():
                self.state.set_rate_limit(source, 900)   # 15 minutes for network issues
            else:
                self.state.set_rate_limit(source, 600)   # 10 minutes for other issues
            raise

    async def _download_recent_updates(self):
        """Download recent ClinicalTrials updates"""
        source = "clinical_trials_updates"

        if self.state.is_rate_limited(source):
            logger.info(f"Skipping {source} - rate limited")
            return

        if self.state.get_daily_retry_count(source) >= self.max_daily_retries:
            logger.info(f"Skipping {source} - daily retry limit reached")
            return

        try:
            logger.info("Downloading recent ClinicalTrials updates")

            self.update_files = await self.downloader.download_recent_updates(days=30)
            logger.info(f"Downloaded {len(self.update_files)} update files")

        except Exception as e:
            logger.exception(f"Failed to download updates: {e}")
            self.state.increment_retry_count(source)

            # Set retry delay based on error type
            if "429" in str(e) or "rate" in str(e).lower():
                self.state.set_rate_limit(source, 3600)  # 1 hour for rate limits
            elif "timeout" in str(e).lower() or "network" in str(e).lower():
                self.state.set_rate_limit(source, 900)   # 15 minutes for network issues
            else:
                self.state.set_rate_limit(source, 600)   # 10 minutes for other issues
            raise

    # Parsing methods removed - parsing is now handled by medical-mirrors service


    async def get_download_status(self) -> dict[str, Any]:
        """Get current download status and progress"""
        # Load saved state if available
        self._load_state()

        total_sources = 2  # all_studies + updates
        completed = self.state.successful_sources

        status = {
            "timestamp": datetime.now().isoformat(),
            "progress": {
                "completed": completed,
                "total_sources": total_sources,
                "completion_rate": (completed / total_sources) * 100 if total_sources > 0 else 0,
            },
            "ready_for_retry": [],
            "total_files_downloaded": len(self.batch_files) + len(self.update_files),
            "next_retry_times": {},
            "batch_files": len(self.batch_files),
            "update_files": len(self.update_files),
            "last_batch_processed": self.state.last_batch_processed,
        }

        # Check which sources are ready for retry
        sources = ["clinical_trials_all", "clinical_trials_updates"]
        for source in sources:
            if not self.state.is_rate_limited(source):
                if self.state.get_daily_retry_count(source) < self.max_daily_retries:
                    status["ready_for_retry"].append(source)
            else:
                # Add retry time for rate-limited sources
                retry_time = self.state.retry_after.get(source)
                if retry_time:
                    status["next_retry_times"][source] = retry_time

        return status

    def _get_summary(self) -> dict[str, Any]:
        """Get download summary statistics"""
        total_sources = 2  # all_studies + updates
        success_rate = (self.state.successful_sources / total_sources) * 100 if total_sources > 0 else 0

        return {
            "total_files_downloaded": len(self.batch_files) + len(self.update_files),
            "batch_files": len(self.batch_files),
            "update_files": len(self.update_files),
            "total_files": len(self.batch_files) + len(self.update_files),
            "successful_sources": self.state.successful_sources,
            "failed_sources": self.state.failed_sources,
            "rate_limited_sources": self.state.rate_limited_sources,
            "success_rate": success_rate,
            "download_timestamp": datetime.now().isoformat(),
        }
