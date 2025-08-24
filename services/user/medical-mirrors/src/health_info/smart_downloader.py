"""
Smart Health Information Downloader with automatic rate limit handling and recovery
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import time

from .downloader import HealthInfoDownloader
# No parser import - this is a DOWNLOADER, not a parser
from config import Config

logger = logging.getLogger(__name__)


class HealthInfoDownloadState:
    """State management for health info downloads"""
    
    def __init__(self):
        self.successful_sources = 0
        self.failed_sources = 0
        self.rate_limited_sources = 0
        self.total_health_topics = 0
        self.total_exercises = 0
        self.total_food_items = 0
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


class SmartHealthInfoDownloader:
    """Smart downloader that coordinates health info sources with state management"""
    
    def __init__(self, output_dir: Optional[Path] = None, config: Optional[Config] = None):
        self.config = config or Config()
        self.output_dir = output_dir or Path("/home/intelluxe/database/medical_complete/health_info")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.state = HealthInfoDownloadState()
        self.downloader = HealthInfoDownloader(self.config)
        # No parser - this is a DOWNLOADER, saves raw API responses
        
        # Smart retry configuration
        self.retry_interval = 600  # 10 minutes between retry checks for APIs
        self.max_daily_retries = 12  # Max retries per day per source
        
        # Results tracking
        self.all_health_data: Dict[str, List[Dict[str, Any]]] = {
            "health_topics": [],
            "exercises": [],
            "food_items": []
        }
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.downloader.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.downloader.__aexit__(exc_type, exc_val, exc_tb)
    
    async def download_and_parse_all(self, 
                                   max_concurrent: int = 3,
                                   force_fresh: bool = False) -> Dict[str, Any]:
        """
        Download all health information with smart retry handling
        
        Args:
            max_concurrent: Maximum concurrent API requests
            force_fresh: If True, reset all download states and start fresh
            
        Returns:
            Summary of download results including totals and source breakdown
        """
        logger.info("Starting smart health information download process")
        
        if force_fresh:
            logger.info("Force fresh download - resetting all states")
            await self.reset_download_state()
        
        start_time = time.time()
        
        try:
            # Download all health data in one call
            try:
                logger.info("Downloading all health information sources...")
                
                # Use the single download_all_health_data method
                health_data = await self.downloader.download_all_health_data()
                
                # Extract individual data types
                self.all_health_data = {
                    "health_topics": health_data.get("health_topics", []),
                    "exercises": health_data.get("exercises", []),
                    "food_items": health_data.get("food_items", [])
                }
                
                # Update state
                self.state.total_health_topics = len(self.all_health_data["health_topics"])
                self.state.total_exercises = len(self.all_health_data["exercises"])
                self.state.total_food_items = len(self.all_health_data["food_items"])
                self.state.successful_sources = 3  # All sources completed
                
                successful_sources = ["health_topics", "exercises", "food_items"]
                failed_sources = []
                
                logger.info(f"✅ All health sources completed:")
                logger.info(f"   Health topics: {self.state.total_health_topics}")
                logger.info(f"   Exercises: {self.state.total_exercises}")
                logger.info(f"   Food items: {self.state.total_food_items}")
                
            except Exception as e:
                logger.error(f"❌ Health data download failed: {e}")
                failed_sources = ["health_topics", "exercises", "food_items"]
                successful_sources = []
                self.state.failed_sources = 3
                
                # Check for rate limit errors and set retry time
                if "rate limit" in str(e).lower() or "429" in str(e):
                    for source in failed_sources:
                        self.state.set_rate_limit(source, self.retry_interval)
                        self.state.increment_retry_count(source)
            
            # Parse and save all downloaded data
            if self.all_health_data['health_topics']:
                await self._save_data('health_topics', self.all_health_data['health_topics'])
            if self.all_health_data['exercises']:
                await self._save_data('exercises', self.all_health_data['exercises'])
            if self.all_health_data['food_items']:
                await self._save_data('food_items', self.all_health_data['food_items'])
            
            duration = time.time() - start_time
            
            result = {
                'total_health_topics': self.state.total_health_topics,
                'total_exercises': self.state.total_exercises,
                'total_food_items': self.state.total_food_items,
                'successful_sources': successful_sources,
                'failed_sources': failed_sources,
                'duration_seconds': duration,
                'rate_limited_sources': len(self.state.retry_after)
            }
            
            logger.info(f"Health info download completed in {duration:.1f}s")
            logger.info(f"Health topics: {self.state.total_health_topics}, "
                       f"Exercises: {self.state.total_exercises}, "
                       f"Food items: {self.state.total_food_items}")
            
            return result
            
        except Exception as e:
            logger.error(f"Smart health info download failed: {e}")
            raise
    
    async def _save_data(self, data_type: str, data: List[Dict[str, Any]]):
        """Save downloaded data to JSON files"""
        output_file = self.output_dir / f"{data_type}_complete.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(data)} {data_type} to {output_file}")
    
    async def get_download_status(self) -> Dict[str, Any]:
        """Get current download status"""
        return {
            'progress': {
                'completed': self.state.successful_sources,
                'total_sources': 3,  # health_topics, exercises, food_items
            },
            'state': 'ready' if self.state.successful_sources == 0 else 'in_progress',
            'ready_for_retry': self.state.failed_sources > 0,
            'rate_limited_sources': list(self.state.retry_after.keys()),
            'next_retry_time': min(self.state.retry_after.values()) if self.state.retry_after else None,
            'totals': {
                'health_topics': self.state.total_health_topics,
                'exercises': self.state.total_exercises,
                'food_items': self.state.total_food_items
            }
        }
    
    async def reset_download_state(self):
        """Reset all download state"""
        logger.info("Resetting health info download state")
        
        self.state = HealthInfoDownloadState()
        self.all_health_data = {
            "health_topics": [],
            "exercises": [],
            "food_items": []
        }
        
        # Remove any state files
        state_files = list(self.output_dir.glob("*_complete.json"))
        for state_file in state_files:
            if state_file.exists():
                state_file.unlink()
                logger.info(f"Removed: {state_file}")