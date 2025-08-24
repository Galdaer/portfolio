"""
Download State Manager for persistent progress tracking of ICD-10 code downloads
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

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
    total_items: Optional[int] = None
    completed_items: int = 0
    failed_items: int = 0
    last_page: Optional[int] = None
    last_offset: Optional[int] = None
    last_attempt: Optional[str] = None
    next_retry: Optional[str] = None
    retry_count: int = 0
    error_message: Optional[str] = None
    rate_limit_reset: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ICD10DownloadStateManager:
    """Manages persistent download state for ICD-10 codes"""
    
    def __init__(self, state_file: Optional[Path] = None):
        if state_file is None:
            state_file = Path("/home/intelluxe/database/medical_complete/icd10/download_state.json")
        
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._states: Dict[str, DownloadState] = {}
        self._load_state()
    
    def _load_state(self):
        """Load download state from persistent storage"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                
                self._states = {}
                for source, state_dict in data.items():
                    # Convert status string back to enum
                    state_dict['status'] = DownloadStatus(state_dict['status'])
                    self._states[source] = DownloadState(**state_dict)
                
                logger.info(f"Loaded ICD-10 download state for {len(self._states)} sources")
            else:
                logger.info("No existing ICD-10 download state found, starting fresh")
                
        except Exception as e:
            logger.error(f"Failed to load ICD-10 download state: {e}")
            self._states = {}
    
    def _save_state(self):
        """Save download state to persistent storage"""
        try:
            # Convert to serializable format
            data = {}
            for source, state in self._states.items():
                state_dict = asdict(state)
                # Convert enum to string
                state_dict['status'] = state.status.value
                data[source] = state_dict
            
            # Write atomically
            temp_file = self.state_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            temp_file.replace(self.state_file)
            logger.debug(f"Saved ICD-10 download state to {self.state_file}")
            
        except Exception as e:
            logger.error(f"Failed to save ICD-10 download state: {e}")
    
    def get_state(self, source: str) -> Optional[DownloadState]:
        """Get download state for a specific source"""
        return self._states.get(source)
    
    def create_state(self, source: str, total_items: Optional[int] = None) -> DownloadState:
        """Create new download state for a source"""
        state = DownloadState(
            source=source,
            status=DownloadStatus.PENDING,
            total_items=total_items,
            last_attempt=datetime.now().isoformat()
        )
        
        self._states[source] = state
        self._save_state()
        
        logger.info(f"Created ICD-10 download state for source: {source}")
        return state
    
    def update_state(self, source: str, **kwargs) -> DownloadState:
        """Update download state for a source"""
        if source not in self._states:
            raise ValueError(f"No state found for ICD-10 source: {source}")
        
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
        """Mark progress for an ICD-10 download"""
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
        logger.debug(f"ICD-10 progress for {source}: {completed_items} completed, {failed_items} failed")
    
    def mark_completed(self, source: str, total_items: int):
        """Mark ICD-10 download as completed"""
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
        logger.info(f"Marked ICD-10 {source} as completed with {total_items} items")
    
    def mark_rate_limited(self, source: str, reset_time: Optional[datetime] = None, 
                         retry_after: int = 3600):
        """Mark ICD-10 download as rate limited"""
        state = self._states.get(source)
        if not state:
            state = self.create_state(source)
        
        state.status = DownloadStatus.RATE_LIMITED
        state.retry_count += 1
        
        if reset_time:
            state.rate_limit_reset = reset_time.isoformat()
            state.next_retry = reset_time.isoformat()
        else:
            # Use exponential backoff for ICD-10 (often more restrictive)
            delay = min(retry_after * (2 ** (state.retry_count - 1)), 86400)  # Max 24 hours
            next_retry = datetime.now() + timedelta(seconds=delay)
            state.next_retry = next_retry.isoformat()
        
        self._save_state()
        logger.warning(f"Marked ICD-10 {source} as rate limited, retry at {state.next_retry}")
    
    def mark_failed(self, source: str, error_message: str):
        """Mark ICD-10 download as failed"""
        state = self._states.get(source)
        if not state:
            state = self.create_state(source)
        
        state.status = DownloadStatus.FAILED
        state.retry_count += 1
        state.error_message = error_message
        
        # Schedule retry with exponential backoff (more aggressive for ICD-10)
        delay = min(600 * (2 ** (state.retry_count - 1)), 7200)  # Max 2 hours
        next_retry = datetime.now() + timedelta(seconds=delay)
        state.next_retry = next_retry.isoformat()
        
        self._save_state()
        logger.error(f"Marked ICD-10 {source} as failed: {error_message}")
    
    def get_ready_for_retry(self) -> List[str]:
        """Get list of ICD-10 sources ready for retry"""
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
    
    def get_incomplete_sources(self) -> List[str]:
        """Get list of incomplete ICD-10 download sources"""
        incomplete = []
        
        for source, state in self._states.items():
            if state.status not in [DownloadStatus.COMPLETED]:
                incomplete.append(source)
        
        return incomplete
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """Get summary of ICD-10 download progress"""
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
            "sources": {}
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
                "error_message": state.error_message
            }
        
        return summary
    
    def reset_source(self, source: str):
        """Reset download state for an ICD-10 source"""
        if source in self._states:
            del self._states[source]
            self._save_state()
            logger.info(f"Reset ICD-10 download state for source: {source}")
    
    def cleanup_old_states(self, days: int = 30):
        """Clean up old completed ICD-10 states"""
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
            logger.info(f"Cleaned up {len(removed)} old completed ICD-10 states")
        
        return removed
    
    def get_source_details(self, source: str) -> Dict[str, Any]:
        """Get detailed information about a specific source"""
        state = self._states.get(source)
        if not state:
            return {"error": f"Source {source} not found"}
        
        details = asdict(state)
        details['status'] = state.status.value
        
        # Add calculated fields
        if state.total_items and state.total_items > 0:
            details['completion_percentage'] = (state.completed_items / state.total_items) * 100
        else:
            details['completion_percentage'] = 0
        
        if state.last_attempt:
            try:
                last_attempt = datetime.fromisoformat(state.last_attempt)
                details['time_since_last_attempt'] = str(datetime.now() - last_attempt)
            except Exception:
                pass
        
        return details
    
    def estimate_completion_time(self) -> Dict[str, Any]:
        """Estimate when all ICD-10 downloads will be complete"""
        incomplete_sources = self.get_incomplete_sources()
        if not incomplete_sources:
            return {"status": "all_completed", "estimated_completion": None}
        
        # Find the source with the latest retry time
        latest_retry = None
        for source in incomplete_sources:
            state = self._states.get(source)
            if state and state.next_retry:
                try:
                    retry_time = datetime.fromisoformat(state.next_retry)
                    if latest_retry is None or retry_time > latest_retry:
                        latest_retry = retry_time
                except Exception:
                    continue
        
        return {
            "status": "incomplete",
            "incomplete_sources": len(incomplete_sources),
            "estimated_completion": latest_retry.isoformat() if latest_retry else None,
            "sources_ready_now": len(self.get_ready_for_retry())
        }


def main():
    """Test the ICD-10 download state manager"""
    logging.basicConfig(level=logging.INFO)
    
    # Test state manager
    manager = ICD10DownloadStateManager()
    
    # Create test states for ICD-10 sources
    test_sources = ["cms_icd10_cm", "who_icd10", "nlm_api", "fallback"]
    
    for source in test_sources:
        state = manager.create_state(source, total_items=70000 if source == "cms_icd10_cm" else 1000)
        print(f"Created state for {source}: {state.status.value}")
    
    # Simulate progress for different scenarios
    manager.mark_progress("cms_icd10_cm", completed_items=25000, chapter="A00-A09")
    manager.mark_rate_limited("who_icd10", retry_after=3600)
    manager.mark_completed("fallback", total_items=10)
    manager.mark_failed("nlm_api", "API timeout after multiple retries")
    
    # Check ready for retry
    ready = manager.get_ready_for_retry()
    print(f"Ready for retry: {ready}")
    
    # Get progress summary
    summary = manager.get_progress_summary()
    print(f"Progress summary: {json.dumps(summary, indent=2)}")
    
    # Get completion estimate
    completion = manager.estimate_completion_time()
    print(f"Completion estimate: {json.dumps(completion, indent=2)}")


if __name__ == "__main__":
    main()