"""
Smart PubMed Downloader with automatic rate limit handling and recovery
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from config import Config

from .downloader import PubMedDownloader

logger = logging.getLogger(__name__)


class PubMedDownloadState:
    """State management for PubMed downloads"""

    def __init__(self):
        self.successful_sources = 0
        self.failed_sources = 0
        self.rate_limited_sources = 0
        self.total_articles = 0
        self.last_download = None
        self.retry_after = {}  # source -> retry timestamp
        self.daily_retry_counts = {}  # source -> date -> count

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


class SmartPubMedDownloader:
    """Smart downloader that coordinates PubMed downloads with state management"""

    def __init__(self, output_dir: Path | None = None, config: Config | None = None):
        self.config = config or Config()
        self.output_dir = output_dir or Path("/home/intelluxe/database/medical_complete/pubmed")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.state = PubMedDownloadState()
        self.downloader = PubMedDownloader(config=self.config)
        # Override downloader's data directory to use our output directory
        self.downloader.data_dir = str(self.output_dir)

        # Smart retry configuration
        self.retry_interval = 900  # 15 minutes between retry checks for FTP
        self.max_daily_retries = 8  # Max retries per day (FTP is more stable)

        # File management - track downloaded files only
        self.baseline_files: list[str] = []
        self.update_files: list[str] = []

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""

    def _load_state(self) -> dict[str, Any]:
        """Load download state from file"""
        state_file = self.output_dir / "download_state.json"
        if state_file.exists():
            try:
                with open(state_file) as f:
                    return json.load(f)
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
                "total_articles": self.state.total_articles,
                "last_download": datetime.now().isoformat(),
                "retry_after": self.state.retry_after,
                "daily_retry_counts": self.state.daily_retry_counts,
                "baseline_count": len(self.baseline_files),
                "update_count": len(self.update_files),
            }
            with open(state_file, "w") as f:
                json.dump(state_data, f)
        except Exception as e:
            logger.warning(f"Failed to save state file: {e}")

    async def download_all_pubmed_data(self, force_fresh: bool = False, complete_dataset: bool = False) -> dict[str, Any]:
        """
        Download all PubMed data with automatic retry handling

        Args:
            force_fresh: If True, ignore cached state and start fresh
            complete_dataset: If True, download complete dataset (~220GB)
        """
        logger.info(f"Starting smart PubMed download (complete_dataset={complete_dataset})")

        if not force_fresh:
            # Load previous state
            saved_state = self._load_state()
            if saved_state:
                logger.info(f"Loaded previous state: {saved_state.get('total_articles', 0)} articles")

        try:
            # Download baseline files
            await self._download_baseline_files(complete_dataset)

            # Download update files
            await self._download_update_files(complete_dataset)

            # Update state - track by files downloaded, not parsed articles
            self.state.successful_sources = 2  # baseline + updates
            self.state.total_articles = len(self.baseline_files) + len(self.update_files)  # Track files, not articles
            self._save_state()

            return self._get_summary()

        except Exception as e:
            logger.exception(f"Smart PubMed download failed: {e}")
            self.state.failed_sources += 1
            self._save_state()
            raise

    async def _download_baseline_files(self, complete_dataset: bool):
        """Download PubMed baseline files"""
        source = "pubmed_baseline"

        if self.state.is_rate_limited(source):
            logger.info(f"Skipping {source} - rate limited")
            return

        if self.state.get_daily_retry_count(source) >= self.max_daily_retries:
            logger.info(f"Skipping {source} - daily retry limit reached")
            return

        try:
            logger.info(f"Downloading PubMed baseline files (complete={complete_dataset})")

            if complete_dataset:
                self.baseline_files = await self.downloader.download_complete_baseline()
            else:
                self.baseline_files = await self.downloader.download_baseline()

            logger.info(f"Downloaded {len(self.baseline_files)} baseline files")

        except Exception as e:
            logger.exception(f"Failed to download baseline files: {e}")
            self.state.increment_retry_count(source)

            # Set retry delay based on error type
            if "timeout" in str(e).lower() or "network" in str(e).lower():
                self.state.set_rate_limit(source, 1800)  # 30 minutes for network issues
            else:
                self.state.set_rate_limit(source, 900)   # 15 minutes for other issues
            raise

    async def _download_update_files(self, complete_dataset: bool):
        """Download PubMed update files"""
        source = "pubmed_updates"

        if self.state.is_rate_limited(source):
            logger.info(f"Skipping {source} - rate limited")
            return

        if self.state.get_daily_retry_count(source) >= self.max_daily_retries:
            logger.info(f"Skipping {source} - daily retry limit reached")
            return

        try:
            logger.info(f"Downloading PubMed update files (complete={complete_dataset})")

            if complete_dataset:
                self.update_files = await self.downloader.download_complete_updates()
            else:
                self.update_files = await self.downloader.download_updates()

            logger.info(f"Downloaded {len(self.update_files)} update files")

        except Exception as e:
            logger.exception(f"Failed to download update files: {e}")
            self.state.increment_retry_count(source)

            # Set retry delay based on error type
            if "timeout" in str(e).lower() or "network" in str(e).lower():
                self.state.set_rate_limit(source, 1800)  # 30 minutes for network issues
            else:
                self.state.set_rate_limit(source, 900)   # 15 minutes for other issues
            raise

    # Parsing methods removed - parsing is now handled by medical-mirrors service
    # Raw downloaded files are left for medical-mirrors to parse

    async def get_download_status(self) -> dict[str, Any]:
        """Get current download status and progress"""
        # Load saved state if available
        self._load_state()

        total_sources = 2  # baseline + updates
        completed = self.state.successful_sources

        status = {
            "timestamp": datetime.now().isoformat(),
            "progress": {
                "completed": completed,
                "total_sources": total_sources,
                "completion_rate": (completed / total_sources) * 100 if total_sources > 0 else 0,
            },
            "ready_for_retry": [],
            "total_files_downloaded": len(self.baseline_files) + len(self.update_files),
            "next_retry_times": {},
            "baseline_files": len(self.baseline_files),
            "update_files": len(self.update_files),
        }

        # Check which sources are ready for retry
        sources = ["pubmed_baseline", "pubmed_updates"]
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
        total_sources = 2  # baseline + updates
        success_rate = (self.state.successful_sources / total_sources) * 100 if total_sources > 0 else 0

        return {
            "total_files_downloaded": len(self.baseline_files) + len(self.update_files),
            "baseline_files": len(self.baseline_files),
            "update_files": len(self.update_files),
            "total_files": len(self.baseline_files) + len(self.update_files),
            "successful_sources": self.state.successful_sources,
            "failed_sources": self.state.failed_sources,
            "rate_limited_sources": self.state.rate_limited_sources,
            "success_rate": success_rate,
            "download_timestamp": datetime.now().isoformat(),
        }
