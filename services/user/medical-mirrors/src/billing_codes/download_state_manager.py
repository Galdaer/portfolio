"""
Download State Manager for persistent progress tracking of billing codes downloads
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class DownloadStatus(Enum):
    """Status of download operations"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    PAUSED = "paused"


@dataclass
class DownloadState:
    """State information for a download operation"""
    source: str
    status: DownloadStatus
    total_items: int | None = None
    completed_items: int = 0
    failed_items: int = 0
    last_page: int | None = None
    last_offset: int | None = None
    last_attempt: str | None = None
    next_retry: str | None = None
    retry_count: int = 0
    error_message: str | None = None
    rate_limit_reset: str | None = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class DownloadStateManager:
    """Manages persistent download state for billing codes"""

    def __init__(self, state_file: Path | None = None):
        if state_file is None:
            state_file = Path("/home/intelluxe/database/medical_complete/billing/download_state.json")

        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._states: dict[str, DownloadState] = {}
        self._load_state()

    def _load_state(self):
        """Load download state from persistent storage"""
        try:
            if self.state_file.exists():
                with open(self.state_file) as f:
                    data = json.load(f)

                self._states = {}
                for source, state_dict in data.items():
                    # Convert status string back to enum
                    state_dict["status"] = DownloadStatus(state_dict["status"])
                    self._states[source] = DownloadState(**state_dict)

                logger.info(f"Loaded download state for {len(self._states)} sources")
            else:
                logger.info("No existing download state found, starting fresh")

        except Exception as e:
            logger.exception(f"Failed to load download state: {e}")
            self._states = {}

    def _save_state(self):
        """Save download state to persistent storage"""
        try:
            # Convert to serializable format
            data = {}
            for source, state in self._states.items():
                state_dict = asdict(state)
                # Convert enum to string
                state_dict["status"] = state.status.value
                data[source] = state_dict

            # Write atomically
            temp_file = self.state_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(data, f, indent=2, default=str)

            temp_file.replace(self.state_file)
            logger.debug(f"Saved download state to {self.state_file}")

        except Exception as e:
            logger.exception(f"Failed to save download state: {e}")

    def get_state(self, source: str) -> DownloadState | None:
        """Get download state for a specific source"""
        return self._states.get(source)

    def create_state(self, source: str, total_items: int | None = None) -> DownloadState:
        """Create new download state for a source"""
        state = DownloadState(
            source=source,
            status=DownloadStatus.PENDING,
            total_items=total_items,
            last_attempt=datetime.now().isoformat(),
        )

        self._states[source] = state
        self._save_state()

        logger.info(f"Created download state for source: {source}")
        return state

    def update_state(self, source: str, **kwargs) -> DownloadState:
        """Update download state for a source"""
        if source not in self._states:
            msg = f"No state found for source: {source}"
            raise ValueError(msg)

        state = self._states[source]

        # Update provided fields
        for field, value in kwargs.items():
            if hasattr(state, field):
                setattr(state, field, value)
            else:
                # Store in metadata
                state.metadata[field] = value

        # Update last attempt timestamp
        state.last_attempt = datetime.now().isoformat()

        self._save_state()
        return state

    def mark_progress(self, source: str, completed_items: int,
                     failed_items: int = 0, **metadata):
        """Mark progress for a download"""
        state = self._states.get(source)
        if not state:
            state = self.create_state(source)

        state.status = DownloadStatus.IN_PROGRESS
        state.completed_items = completed_items
        state.failed_items = failed_items

        # Update metadata
        for key, value in metadata.items():
            state.metadata[key] = value

        self._save_state()
        logger.debug(f"Progress for {source}: {completed_items} completed, {failed_items} failed")

    def mark_completed(self, source: str, total_items: int):
        """Mark download as completed"""
        state = self._states.get(source)
        if not state:
            state = self.create_state(source, total_items)

        state.status = DownloadStatus.COMPLETED
        state.total_items = total_items
        state.completed_items = total_items
        state.retry_count = 0
        state.error_message = None
        state.rate_limit_reset = None
        state.next_retry = None

        self._save_state()
        logger.info(f"Marked {source} as completed with {total_items} items")

    def mark_rate_limited(self, source: str, reset_time: datetime | None = None,
                         retry_after: int = 3600):
        """Mark download as rate limited"""
        state = self._states.get(source)
        if not state:
            state = self.create_state(source)

        state.status = DownloadStatus.RATE_LIMITED
        state.retry_count += 1

        if reset_time:
            state.rate_limit_reset = reset_time.isoformat()
            state.next_retry = reset_time.isoformat()
        else:
            # Use exponential backoff
            delay = min(retry_after * (2 ** (state.retry_count - 1)), 86400)  # Max 24 hours
            next_retry = datetime.now() + timedelta(seconds=delay)
            state.next_retry = next_retry.isoformat()

        self._save_state()
        logger.warning(f"Marked {source} as rate limited, retry at {state.next_retry}")

    def mark_failed(self, source: str, error_message: str):
        """Mark download as failed"""
        state = self._states.get(source)
        if not state:
            state = self.create_state(source)

        state.status = DownloadStatus.FAILED
        state.retry_count += 1
        state.error_message = error_message

        # Schedule retry with exponential backoff
        delay = min(300 * (2 ** (state.retry_count - 1)), 3600)  # Max 1 hour
        next_retry = datetime.now() + timedelta(seconds=delay)
        state.next_retry = next_retry.isoformat()

        self._save_state()
        logger.error(f"Marked {source} as failed: {error_message}")

    def get_ready_for_retry(self) -> list[str]:
        """Get list of sources ready for retry"""
        ready_sources = []
        now = datetime.now()

        for source, state in self._states.items():
            if state.status in [DownloadStatus.FAILED, DownloadStatus.RATE_LIMITED]:
                if state.next_retry:
                    try:
                        retry_time = datetime.fromisoformat(state.next_retry)
                        if now >= retry_time:
                            ready_sources.append(source)
                    except Exception:
                        # If we can't parse the retry time, assume ready
                        ready_sources.append(source)
                else:
                    # No retry time set, assume ready
                    ready_sources.append(source)

        return ready_sources

    def get_incomplete_sources(self) -> list[str]:
        """Get list of incomplete download sources"""
        incomplete = []

        for source, state in self._states.items():
            if state.status not in [DownloadStatus.COMPLETED]:
                incomplete.append(source)

        return incomplete

    def get_progress_summary(self) -> dict[str, Any]:
        """Get summary of download progress"""
        summary = {
            "total_sources": len(self._states),
            "completed": 0,
            "in_progress": 0,
            "failed": 0,
            "rate_limited": 0,
            "pending": 0,
            "total_items": 0,
            "completed_items": 0,
            "failed_items": 0,
            "sources": {},
        }

        for source, state in self._states.items():
            status_key = state.status.value
            summary[status_key] += 1

            if state.total_items:
                summary["total_items"] += state.total_items

            summary["completed_items"] += state.completed_items
            summary["failed_items"] += state.failed_items

            summary["sources"][source] = {
                "status": state.status.value,
                "completed": state.completed_items,
                "failed": state.failed_items,
                "total": state.total_items,
                "retry_count": state.retry_count,
                "last_attempt": state.last_attempt,
                "next_retry": state.next_retry,
            }

        return summary

    def reset_source(self, source: str):
        """Reset download state for a source"""
        if source in self._states:
            del self._states[source]
            self._save_state()
            logger.info(f"Reset download state for source: {source}")

    def cleanup_old_states(self, days: int = 30):
        """Clean up old completed states"""
        cutoff = datetime.now() - timedelta(days=days)
        removed = []

        for source, state in list(self._states.items()):
            if (state.status == DownloadStatus.COMPLETED and
                state.last_attempt and
                datetime.fromisoformat(state.last_attempt) < cutoff):

                del self._states[source]
                removed.append(source)

        if removed:
            self._save_state()
            logger.info(f"Cleaned up {len(removed)} old completed states")

        return removed


def main():
    """Test the download state manager"""
    logging.basicConfig(level=logging.INFO)

    # Test state manager
    manager = DownloadStateManager()

    # Create test states
    test_sources = ["cms_hcpcs", "nlm_api", "fallback"]

    for source in test_sources:
        state = manager.create_state(source, total_items=1000)
        print(f"Created state for {source}: {state.status.value}")

    # Simulate progress
    manager.mark_progress("cms_hcpcs", completed_items=250, page=5)
    manager.mark_rate_limited("nlm_api", retry_after=1800)
    manager.mark_completed("fallback", total_items=28)

    # Check ready for retry
    ready = manager.get_ready_for_retry()
    print(f"Ready for retry: {ready}")

    # Get progress summary
    summary = manager.get_progress_summary()
    print(f"Progress summary: {json.dumps(summary, indent=2)}")


if __name__ == "__main__":
    main()
