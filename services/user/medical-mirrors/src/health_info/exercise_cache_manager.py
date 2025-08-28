"""
ExerciseDB On-Demand Cache Manager
Fetches and permanently caches exercises from ExerciseDB API as needed
Avoids rate limit issues by only downloading when requested
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
from aiohttp import ClientResponseError
from sqlalchemy import text

from config import Config
from database import get_db_session

logger = logging.getLogger(__name__)


class ExerciseRateLimitManager:
    """Manages rate limiting for ExerciseDB API"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.rate_limit_file = data_dir / "exercisedb_rate_limit.json"
        self.daily_limit = 500  # Conservative estimate for free tier
        self.monthly_limit = 1000  # Conservative estimate
        self.load_rate_limit_status()
    
    def load_rate_limit_status(self):
        """Load current rate limit status"""
        try:
            if self.rate_limit_file.exists():
                with open(self.rate_limit_file, 'r') as f:
                    data = json.load(f)
                    self.daily_requests = data.get('daily_requests', 0)
                    self.monthly_requests = data.get('monthly_requests', 0)
                    self.last_reset = datetime.fromisoformat(data.get('last_reset', datetime.now().isoformat()))
                    self.rate_limited_until = data.get('rate_limited_until')
                    if self.rate_limited_until:
                        self.rate_limited_until = datetime.fromisoformat(self.rate_limited_until)
            else:
                self.reset_counters()
        except Exception as e:
            logger.warning(f"Error loading rate limit status: {e}")
            self.reset_counters()
    
    def reset_counters(self):
        """Reset rate limit counters"""
        self.daily_requests = 0
        self.monthly_requests = 0
        self.last_reset = datetime.now()
        self.rate_limited_until = None
    
    def save_rate_limit_status(self):
        """Save current rate limit status"""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            data = {
                'daily_requests': self.daily_requests,
                'monthly_requests': self.monthly_requests,
                'last_reset': self.last_reset.isoformat(),
                'rate_limited_until': self.rate_limited_until.isoformat() if self.rate_limited_until else None
            }
            with open(self.rate_limit_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving rate limit status: {e}")
    
    def check_daily_reset(self):
        """Check if daily counters should be reset"""
        now = datetime.now()
        if now.date() > self.last_reset.date():
            self.daily_requests = 0
            self.last_reset = now
            logger.info("Reset daily ExerciseDB request counter")
    
    def can_make_request(self) -> bool:
        """Check if we can make a request within rate limits"""
        self.check_daily_reset()
        
        # Check if we're currently rate limited
        if self.rate_limited_until and datetime.now() < self.rate_limited_until:
            return False
        
        # Check daily limit
        if self.daily_requests >= self.daily_limit:
            logger.warning(f"Daily ExerciseDB limit reached: {self.daily_requests}/{self.daily_limit}")
            return False
        
        # Check monthly limit
        if self.monthly_requests >= self.monthly_limit:
            logger.warning(f"Monthly ExerciseDB limit reached: {self.monthly_requests}/{self.monthly_limit}")
            return False
        
        return True
    
    def record_request(self):
        """Record a successful API request"""
        self.daily_requests += 1
        self.monthly_requests += 1
        self.save_rate_limit_status()
    
    def record_rate_limit(self, retry_after_minutes: int = 60):
        """Record that we've been rate limited"""
        self.rate_limited_until = datetime.now() + timedelta(minutes=retry_after_minutes)
        self.save_rate_limit_status()
        logger.warning(f"ExerciseDB rate limited until {self.rate_limited_until}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current rate limit status"""
        self.check_daily_reset()
        return {
            'daily_requests': self.daily_requests,
            'monthly_requests': self.monthly_requests,
            'daily_limit': self.daily_limit,
            'monthly_limit': self.monthly_limit,
            'can_make_request': self.can_make_request(),
            'rate_limited_until': self.rate_limited_until.isoformat() if self.rate_limited_until else None
        }


class ExerciseCacheManager:
    """Manages on-demand caching of ExerciseDB exercises"""
    
    def __init__(self, config: Config):
        self.config = config
        self.data_dir = Path(config.get_health_info_data_dir())
        self.session_factory = get_db_session
        self.rate_limiter = ExerciseRateLimitManager(self.data_dir)
        
        # API configuration
        self.exercisedb_url = "https://exercisedb.p.rapidapi.com"
        self.rapidapi_key = os.getenv("RAPIDAPI_KEY")
        
        # Session management
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        headers = {}
        if self.rapidapi_key:
            headers.update({
                "X-RapidAPI-Key": self.rapidapi_key,
                "X-RapidAPI-Host": "exercisedb.p.rapidapi.com"
            })
        
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                "User-Agent": "Medical-Mirrors/1.0 (Healthcare Research)",
                **headers
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def get_cached_exercise(self, exercise_id: str) -> Optional[Dict[str, Any]]:
        """Get exercise from local cache/database"""
        db = self.session_factory()
        try:
            result = db.execute(
                text("SELECT * FROM exercises WHERE exercise_id = :exercise_id"),
                {"exercise_id": exercise_id}
            ).fetchone()
            
            if result:
                # Convert to dict
                columns = result._fields
                exercise_data = dict(zip(columns, result))
                logger.debug(f"Found cached exercise: {exercise_id}")
                return exercise_data
            
            return None
        except Exception as e:
            logger.error(f"Error querying cached exercise {exercise_id}: {e}")
            return None
        finally:
            db.close()
    
    async def cache_exercise(self, exercise_data: Dict[str, Any]) -> bool:
        """Cache exercise data in database"""
        db = self.session_factory()
        try:
            # Upsert exercise data
            upsert_sql = text("""
                INSERT INTO exercises (
                    exercise_id, name, body_part, equipment, target,
                    secondary_muscles, instructions, gif_url, category,
                    source, last_updated, search_text
                ) VALUES (
                    :exercise_id, :name, :body_part, :equipment, :target,
                    :secondary_muscles, :instructions, :gif_url, :category,
                    :source, :last_updated, :search_text
                )
                ON CONFLICT (exercise_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    body_part = EXCLUDED.body_part,
                    equipment = EXCLUDED.equipment,
                    target = EXCLUDED.target,
                    secondary_muscles = EXCLUDED.secondary_muscles,
                    instructions = EXCLUDED.instructions,
                    gif_url = EXCLUDED.gif_url,
                    last_updated = EXCLUDED.last_updated,
                    search_text = EXCLUDED.search_text
            """)
            
            db.execute(upsert_sql, exercise_data)
            db.commit()
            
            logger.info(f"Cached exercise: {exercise_data.get('name', exercise_data.get('exercise_id'))}")
            return True
            
        except Exception as e:
            logger.error(f"Error caching exercise: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    async def fetch_exercise_from_api(self, exercise_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single exercise from ExerciseDB API"""
        if not self.session:
            raise RuntimeError("ExerciseCacheManager not initialized - use async context manager")
        
        if not self.rapidapi_key:
            logger.error("No RapidAPI key configured for ExerciseDB")
            return None
        
        try:
            url = f"{self.exercisedb_url}/exercises/exercise/{exercise_id}"
            
            async with self.session.get(url) as response:
                if response.status == 429:
                    logger.warning(f"Rate limited when fetching exercise {exercise_id}")
                    self.rate_limiter.record_rate_limit()
                    return None
                
                if response.status == 404:
                    logger.debug(f"Exercise {exercise_id} not found")
                    return None
                
                response.raise_for_status()
                data = await response.json()
                
                # Record successful request
                self.rate_limiter.record_request()
                
                # Convert to our standard format
                exercise_data = {
                    "exercise_id": exercise_id,
                    "name": data.get("name", ""),
                    "body_part": data.get("bodyPart", ""),
                    "equipment": data.get("equipment", ""),
                    "target": data.get("target", ""),
                    "secondary_muscles": json.dumps(data.get("secondaryMuscles", [])),
                    "instructions": json.dumps(data.get("instructions", [])),
                    "gif_url": data.get("gifUrl", ""),
                    "category": "exercise",
                    "source": "exercisedb",
                    "last_updated": datetime.now().isoformat(),
                    "search_text": f"{data.get('name', '')} {data.get('bodyPart', '')} {data.get('target', '')}".lower(),
                }
                
                logger.info(f"Fetched exercise from API: {exercise_data['name']}")
                return exercise_data
        
        except ClientResponseError as e:
            if e.status == 429:
                self.rate_limiter.record_rate_limit()
            logger.error(f"HTTP error fetching exercise {exercise_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching exercise {exercise_id}: {e}")
            return None
    
    async def get_exercise(self, exercise_id: str) -> Dict[str, Any]:
        """Get exercise by ID - cache first, then API if needed"""
        # First try cache
        cached_exercise = await self.get_cached_exercise(exercise_id)
        if cached_exercise:
            return {
                "success": True,
                "exercise": cached_exercise,
                "source": "cache"
            }
        
        # Check if we can make API request
        if not self.rate_limiter.can_make_request():
            status = self.rate_limiter.get_status()
            return {
                "success": False,
                "error": "Rate limited",
                "rate_limit_status": status,
                "message": f"ExerciseDB API rate limit exceeded. Try again after {status.get('rate_limited_until', 'some time')}"
            }
        
        # Fetch from API
        exercise_data = await self.fetch_exercise_from_api(exercise_id)
        if not exercise_data:
            return {
                "success": False,
                "error": "Not found",
                "message": f"Exercise {exercise_id} not found or API error"
            }
        
        # Cache the exercise
        cached_success = await self.cache_exercise(exercise_data)
        
        return {
            "success": True,
            "exercise": exercise_data,
            "source": "api",
            "cached": cached_success
        }
    
    async def search_cached_exercises(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search only cached exercises - no API calls"""
        db = self.session_factory()
        try:
            search_sql = text("""
                SELECT * FROM exercises 
                WHERE search_text ILIKE :query 
                   OR name ILIKE :query
                   OR body_part ILIKE :query
                   OR target ILIKE :query
                ORDER BY 
                    CASE WHEN name ILIKE :query THEN 1 ELSE 2 END,
                    name
                LIMIT :limit
            """)
            
            results = db.execute(search_sql, {
                "query": f"%{query.lower()}%",
                "limit": limit
            }).fetchall()
            
            exercises = []
            for result in results:
                columns = result._fields
                exercise_data = dict(zip(columns, result))
                exercises.append(exercise_data)
            
            logger.info(f"Found {len(exercises)} cached exercises for query: {query}")
            return exercises
            
        except Exception as e:
            logger.error(f"Error searching cached exercises: {e}")
            return []
        finally:
            db.close()
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        db = self.session_factory()
        try:
            # Count cached exercises
            count_result = db.execute(text("SELECT COUNT(*) FROM exercises WHERE source = 'exercisedb'")).scalar()
            
            # Get recent additions (PostgreSQL syntax)
            recent_result = db.execute(text("""
                SELECT COUNT(*) FROM exercises 
                WHERE source = 'exercisedb' 
                  AND last_updated >= NOW() - INTERVAL '7 days'
            """)).scalar()
            
            # Get rate limit status
            rate_status = self.rate_limiter.get_status()
            
            return {
                "total_cached_exercises": count_result or 0,
                "recent_additions": recent_result or 0,
                "rate_limit_status": rate_status
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {
                "total_cached_exercises": 0,
                "recent_additions": 0,
                "rate_limit_status": self.rate_limiter.get_status(),
                "error": str(e)
            }
        finally:
            db.close()
    
    async def warmup_cache(self, exercise_ids: List[str], delay_seconds: float = 2.0) -> Dict[str, Any]:
        """Warm up cache with specific exercise IDs (respects rate limits)"""
        logger.info(f"Starting cache warmup for {len(exercise_ids)} exercises")
        
        successful = 0
        failed = 0
        skipped = 0
        
        for i, exercise_id in enumerate(exercise_ids):
            # Check if already cached
            cached = await self.get_cached_exercise(exercise_id)
            if cached:
                skipped += 1
                continue
            
            # Check rate limits
            if not self.rate_limiter.can_make_request():
                logger.warning(f"Rate limit hit during warmup after {i} requests")
                break
            
            # Fetch and cache
            result = await self.get_exercise(exercise_id)
            if result.get("success"):
                successful += 1
            else:
                failed += 1
            
            # Delay between requests
            if i < len(exercise_ids) - 1:
                await asyncio.sleep(delay_seconds)
        
        return {
            "requested": len(exercise_ids),
            "successful": successful,
            "failed": failed,
            "skipped": skipped,
            "rate_limit_status": self.rate_limiter.get_status()
        }


async def main():
    """Test the exercise cache manager"""
    from config import Config
    
    config = Config()
    
    async with ExerciseCacheManager(config) as cache_manager:
        # Get cache stats
        stats = await cache_manager.get_cache_stats()
        print(f"Cache stats: {json.dumps(stats, indent=2)}")
        
        # Try to get a specific exercise
        result = await cache_manager.get_exercise("0001")
        print(f"Exercise 0001 result: {json.dumps(result, indent=2)}")
        
        # Search cached exercises
        search_results = await cache_manager.search_cached_exercises("push")
        print(f"Found {len(search_results)} exercises matching 'push'")


if __name__ == "__main__":
    asyncio.run(main())