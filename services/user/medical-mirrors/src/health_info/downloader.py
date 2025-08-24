"""
Health information APIs downloader (MyHealthfinder, ExerciseDB, USDA FoodData Central)
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import aiohttp
from aiohttp import ClientResponseError

from config import Config

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Raised when API rate limit is exceeded"""
    def __init__(self, message: str, retry_after: int):
        super().__init__(message)
        self.retry_after = retry_after


class HealthInfoDownloader:
    """Downloads health information from free public APIs"""

    def __init__(self, config: Config):
        self.config = config

        # API endpoints
        self.myhealthfinder_url = "https://odphp.health.gov/myhealthfinder/api/v4"
        self.exercisedb_url = "https://exercisedb.p.rapidapi.com"
        self.usda_url = "https://api.nal.usda.gov/fdc/v1"

        # API keys from environment
        self.rapidapi_key = os.getenv("RAPIDAPI_KEY")
        self.usda_api_key = os.getenv("USDA_API_KEY")

        # Progress tracking
        self.progress_file = Path(config.get_health_info_data_dir()) / "download_progress.json"
        
        self.session = None
        self.download_stats = {
            "health_topics_downloaded": 0,
            "exercises_downloaded": 0,
            "food_items_downloaded": 0,
            "requests_made": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None,
        }

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"User-Agent": "Medical-Mirrors/1.0 (Healthcare Research)"},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def download_all_health_data(self) -> dict[str, list[dict]]:
        """Download all available health information data"""
        logger.info("Starting comprehensive health information download")
        self.download_stats["start_time"] = datetime.now()

        all_data = {
            "health_topics": [],
            "exercises": [],
            "food_items": [],
        }

        try:
            # Download MyHealthfinder topics
            health_topics = await self._download_myhealthfinder_data()
            all_data["health_topics"] = health_topics

            # Download exercise data (if API key available)
            exercises = await self._download_exercise_data()
            all_data["exercises"] = exercises

            # Download USDA food data (if API key available)
            food_items = await self._download_usda_food_data()
            all_data["food_items"] = food_items

            self.download_stats["end_time"] = datetime.now()

            total_items = (len(health_topics) + len(exercises) + len(food_items))
            logger.info(f"Downloaded {total_items} total health information items")

            return all_data

        except Exception as e:
            logger.exception(f"Error in health information download: {e}")
            self.download_stats["errors"] += 1
            raise

    def _load_progress(self) -> Dict:
        """Load download progress from checkpoint file"""
        default_progress = {
            "last_update": datetime.now().isoformat(),
            "health_topics": {
                "total": 0,
                "downloaded": [],
                "failed": [],
                "rate_limited_at": None,
                "retry_after": None
            },
            "exercises": {
                "body_parts_completed": [],
                "equipment_completed": [],
                "target_completed": [],
                "exercises_downloaded": [],
                "rate_limited_at": None,
                "retry_after": None
            },
            "food_items": {
                "queries_completed": [],
                "items_downloaded": [],
                "rate_limited_at": None,
                "retry_after": None
            }
        }
        
        if not self.progress_file.exists():
            return default_progress
        
        try:
            with open(self.progress_file, 'r') as f:
                progress = json.load(f)
                # Ensure all required keys exist
                for key in default_progress:
                    if key not in progress:
                        progress[key] = default_progress[key]
                for source in ['health_topics', 'exercises', 'food_items']:
                    for subkey in default_progress[source]:
                        if subkey not in progress[source]:
                            progress[source][subkey] = default_progress[source][subkey]
                return progress
        except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
            logger.warning(f"Failed to load progress file: {e}, using defaults")
            return default_progress

    def _save_progress(self, progress: Dict):
        """Save download progress to checkpoint file"""
        try:
            progress["last_update"] = datetime.now().isoformat()
            with open(self.progress_file, 'w') as f:
                json.dump(progress, f, default=str)
            logger.debug(f"Progress saved to {self.progress_file}")
        except Exception as e:
            logger.error(f"Failed to save progress: {e}")

    def _calculate_wait_time(self, source_progress: Dict) -> float:
        """Calculate how long to wait before retrying after rate limit"""
        if not source_progress.get('rate_limited_at'):
            return 0.0
        
        rate_limited_time = datetime.fromisoformat(source_progress['rate_limited_at'])
        retry_after = source_progress.get('retry_after', 60)  # Default 1 minute
        
        # Calculate elapsed time since rate limit
        elapsed = (datetime.now() - rate_limited_time).total_seconds()
        remaining = max(0, retry_after - elapsed)
        
        return remaining

    async def _retry_with_backoff(self, func, *args, max_retries: int = 5, base_delay: float = 5.0, **kwargs):
        """Retry function with exponential backoff"""
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except ClientResponseError as e:
                if e.status == 429:  # Rate limited
                    if attempt == max_retries - 1:
                        # Last attempt, raise custom exception with retry info
                        retry_after = int(e.headers.get('Retry-After', '60'))
                        raise RateLimitError(f"Rate limited after {max_retries} attempts", retry_after)
                    
                    # Calculate exponential backoff delay (5, 10, 20, 40, 80 seconds, capped at 5 minutes)
                    delay = min(base_delay * (2 ** attempt), 300)
                    logger.info(f"Rate limited (attempt {attempt + 1}/{max_retries}), waiting {delay}s")
                    await asyncio.sleep(delay)
                else:
                    # Non-rate-limit error, re-raise immediately
                    raise
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                # For other exceptions, use shorter delay
                delay = min(base_delay * (2 ** attempt), 60)
                logger.warning(f"Error on attempt {attempt + 1}/{max_retries}: {e}, retrying in {delay}s")
                await asyncio.sleep(delay)
        
        # Should not reach here
        raise Exception("Max retries exceeded")

    async def _download_exercise_data(self) -> list[dict]:
        """Download ALL available exercise data from ExerciseDB using comprehensive strategy"""
        logger.info("Starting comprehensive exercise download from ExerciseDB API")

        if not self.rapidapi_key:
            logger.warning("RAPIDAPI_KEY not available - using fallback exercise data")
            return self._get_fallback_exercises()

        # Load progress
        progress = self._load_progress()
        exercises_progress = progress["exercises"]
        
        # Check if we need to wait for rate limit
        wait_time = self._calculate_wait_time(exercises_progress)
        if wait_time > 0:
            logger.info(f"Rate limit active, waiting {wait_time:.1f}s before continuing")
            await asyncio.sleep(wait_time)
            
        headers = {
            "X-RapidAPI-Key": self.rapidapi_key,
            "X-RapidAPI-Host": "exercisedb.p.rapidapi.com",
        }

        all_exercises = []
        exercise_ids_seen = set(exercises_progress.get("exercises_downloaded", []))
        total_unique_exercises = len(exercise_ids_seen)
        
        logger.info(f"Resuming download - already have {total_unique_exercises} unique exercise IDs")

        try:
            # Strategy 1: Download by body parts
            body_parts = await self._get_exercisedb_body_parts(headers)
            await self._download_exercises_by_category(
                headers, "bodyPart", body_parts, all_exercises, 
                exercise_ids_seen, exercises_progress, progress
            )

            # Strategy 2: Download by equipment types
            equipment_types = await self._get_exercisedb_equipment_types(headers)
            await self._download_exercises_by_category(
                headers, "equipment", equipment_types, all_exercises, 
                exercise_ids_seen, exercises_progress, progress
            )

            # Strategy 3: Download by target muscles
            target_muscles = await self._get_exercisedb_target_muscles(headers)
            await self._download_exercises_by_category(
                headers, "target", target_muscles, all_exercises, 
                exercise_ids_seen, exercises_progress, progress
            )

            # Clear rate limit markers if we completed successfully
            exercises_progress["rate_limited_at"] = None
            exercises_progress["retry_after"] = None
            self._save_progress(progress)

            total_unique = len(exercise_ids_seen)
            logger.info(f"✅ Download complete! Collected {total_unique} unique exercises using comprehensive strategy")
            self.download_stats["exercises_downloaded"] = total_unique

        except RateLimitError as e:
            logger.warning(f"Rate limited: {e}. Progress saved, will resume automatically")
            exercises_progress["rate_limited_at"] = datetime.now().isoformat()
            exercises_progress["retry_after"] = e.retry_after
            self._save_progress(progress)
        except Exception as e:
            logger.exception(f"Error in comprehensive exercise download: {e}")
            self.download_stats["errors"] += 1

        # Convert exercise IDs back to full exercise data
        if exercise_ids_seen:
            logger.info("Converting exercise IDs to full exercise data")
            all_exercises = await self._get_full_exercise_data(headers, list(exercise_ids_seen))

        # Fallback if no exercises were downloaded
        if not all_exercises:
            logger.warning("No exercises downloaded - using fallback exercise data")
            all_exercises = self._get_fallback_exercises()

        return all_exercises

    async def _get_exercisedb_body_parts(self, headers: dict) -> List[str]:
        """Get list of all available body parts from ExerciseDB"""
        try:
            url = f"{self.exercisedb_url}/exercises/bodyPartList"
            self.download_stats["requests_made"] += 1
            
            response = await self._retry_with_backoff(
                self.session.get, url, headers=headers, timeout=15
            )
            
            async with response as resp:
                resp.raise_for_status()
                body_parts = await resp.json()
                logger.info(f"Found {len(body_parts)} body parts: {body_parts}")
                return body_parts
                
        except Exception as e:
            logger.warning(f"Failed to get body parts list: {e}, using fallback")
            return ["back", "cardio", "chest", "lower arms", "lower legs", "neck", "shoulders", "upper arms", "upper legs", "waist"]

    async def _get_exercisedb_equipment_types(self, headers: dict) -> List[str]:
        """Get list of all available equipment types from ExerciseDB"""
        try:
            url = f"{self.exercisedb_url}/exercises/equipmentList"
            self.download_stats["requests_made"] += 1
            
            response = await self._retry_with_backoff(
                self.session.get, url, headers=headers, timeout=15
            )
            
            async with response as resp:
                resp.raise_for_status()
                equipment_types = await resp.json()
                logger.info(f"Found {len(equipment_types)} equipment types: {equipment_types}")
                return equipment_types
                
        except Exception as e:
            logger.warning(f"Failed to get equipment list: {e}, using fallback")
            # Fallback equipment types we discovered
            return ["barbell", "dumbbell", "body weight", "cable", "machine", "kettlebell", "resistance band", "stability ball", "medicine ball", "rope"]

    async def _get_exercisedb_target_muscles(self, headers: dict) -> List[str]:
        """Get list of all available target muscles from ExerciseDB"""
        try:
            url = f"{self.exercisedb_url}/exercises/targetList"
            self.download_stats["requests_made"] += 1
            
            response = await self._retry_with_backoff(
                self.session.get, url, headers=headers, timeout=15
            )
            
            async with response as resp:
                resp.raise_for_status()
                target_muscles = await resp.json()
                logger.info(f"Found {len(target_muscles)} target muscles: {target_muscles}")
                return target_muscles
                
        except Exception as e:
            logger.warning(f"Failed to get target muscles list: {e}, using fallback")
            # Fallback target muscles we discovered
            return ["abductors", "abs", "biceps", "calves", "glutes", "hamstrings", "lats", "pectorals", "quads", "triceps", "delts"]

    async def _download_exercises_by_category(self, headers: dict, category_type: str, categories: List[str], 
                                            all_exercises: List[dict], exercise_ids_seen: set, 
                                            exercises_progress: dict, progress: dict):
        """Download exercises for a specific category type (bodyPart, equipment, target)"""
        progress_key = f"{category_type.lower()}_completed"
        if progress_key not in exercises_progress:
            exercises_progress[progress_key] = []
            
        completed_categories = set(exercises_progress[progress_key])
        pending_categories = [cat for cat in categories if cat not in completed_categories]
        
        logger.info(f"📥 {category_type} strategy: {len(completed_categories)} completed, {len(pending_categories)} pending")
        
        for i, category in enumerate(pending_categories):
            try:
                logger.info(f"Downloading exercises for {category_type}: '{category}' ({i+1}/{len(pending_categories)})")
                
                # Build URL based on category type
                safe_category = category.replace(' ', '%20').replace('/', '%2F')
                url = f"{self.exercisedb_url}/exercises/{category_type}/{safe_category}"
                
                self.download_stats["requests_made"] += 1
                
                response = await self._retry_with_backoff(
                    self.session.get, url, headers=headers, timeout=15
                )
                
                async with response as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    
                    new_exercises = 0
                    for exercise in data:
                        exercise_id = exercise.get("id", "")
                        if exercise_id and exercise_id not in exercise_ids_seen:
                            exercise_ids_seen.add(exercise_id)
                            new_exercises += 1
                    
                    logger.info(f"✅ {category_type} '{category}': {len(data)} total, {new_exercises} new unique exercises")
                    
                # Mark this category as completed
                exercises_progress[progress_key].append(category)
                exercises_progress["exercises_downloaded"] = list(exercise_ids_seen)
                self._save_progress(progress)
                
                # Rate limiting between requests
                await asyncio.sleep(1)
                
            except RateLimitError:
                # Let the parent method handle rate limits
                raise
            except Exception as e:
                logger.warning(f"Failed to download exercises for {category_type} '{category}': {e}")
                continue

    async def _get_full_exercise_data(self, headers: dict, exercise_ids: List[str]) -> List[dict]:
        """Convert exercise IDs to full exercise data by fetching individual exercises"""
        logger.info(f"Converting {len(exercise_ids)} exercise IDs to full exercise data")
        all_exercises = []
        
        # We'll get full data by querying one of the category endpoints and filtering
        # Since we know we have comprehensive coverage from all endpoints
        
        try:
            # Get all exercises from body parts (most comprehensive single endpoint)
            body_parts = ["back", "cardio", "chest", "lower arms", "lower legs", "neck", "shoulders", "upper arms", "upper legs", "waist"]
            
            for body_part in body_parts:
                try:
                    url = f"{self.exercisedb_url}/exercises/bodyPart/{body_part.replace(' ', '%20')}"
                    self.download_stats["requests_made"] += 1
                    
                    response = await self._retry_with_backoff(
                        self.session.get, url, headers=headers, timeout=15
                    )
                    
                    async with response as resp:
                        resp.raise_for_status()
                        data = await resp.json()
                        
                        for exercise in data:
                            exercise_id = exercise.get("id", "")
                            if exercise_id in exercise_ids:
                                exercise_data = {
                                    "exercise_id": exercise_id,
                                    "name": exercise.get("name", ""),
                                    "body_part": exercise.get("bodyPart", ""),
                                    "equipment": exercise.get("equipment", ""),
                                    "target": exercise.get("target", ""),
                                    "secondary_muscles": exercise.get("secondaryMuscles", []),
                                    "instructions": exercise.get("instructions", []),
                                    "gif_url": exercise.get("gifUrl", ""),
                                    "category": "exercise",
                                    "source": "exercisedb",
                                    "last_updated": datetime.now().isoformat(),
                                    "search_text": f"{exercise.get('name', '')} {exercise.get('bodyPart', '')} {exercise.get('target', '')}".lower(),
                                }
                                all_exercises.append(exercise_data)
                                
                    await asyncio.sleep(1)  # Rate limiting
                    
                except Exception as e:
                    logger.warning(f"Error fetching full data for body part {body_part}: {e}")
                    continue
                    
        except Exception as e:
            logger.exception(f"Error converting exercise IDs to full data: {e}")
            
        logger.info(f"Converted {len(all_exercises)} exercise IDs to full exercise data")
        return all_exercises

    async def _download_myhealthfinder_data(self) -> list[dict]:
        """Download health topics from MyHealthfinder API with progress tracking"""
        logger.info("Downloading MyHealthfinder health topics")

        # Load progress
        progress = self._load_progress()
        
        # Check if we're still rate limited
        wait_time = self._calculate_wait_time(progress['health_topics'])
        if wait_time > 0:
            logger.info(f"Still rate limited, waiting {wait_time:.1f}s before retrying")
            await asyncio.sleep(wait_time)
            # Clear rate limit status after waiting
            progress['health_topics']['rate_limited_at'] = None
            progress['health_topics']['retry_after'] = None

        all_topics = []

        try:
            # Get health topics list
            topics_url = f"{self.myhealthfinder_url}/itemlist.json"
            params = {"Type": "topic"}

            logger.info(f"Fetching topics list from {topics_url}")
            
            self.download_stats["requests_made"] += 1
            topics_response = await self._retry_with_backoff(
                self.session.get, topics_url, params=params
            )
            
            async with topics_response as response:
                response.raise_for_status()
                data = await response.json()
                
                # Parse new API response structure
                result = data.get("Result", {})
                if result.get("Error") != "False":
                    raise Exception(f"API returned error: {result}")
                
                topics_data = result.get("Items", {}).get("Item", [])
                progress['health_topics']['total'] = len(topics_data)
                logger.info(f"Found {len(topics_data)} total health topics")

                # Filter out already downloaded topics
                downloaded_ids = set(progress['health_topics']['downloaded'])
                pending_topics = [t for t in topics_data if t.get('Id') not in downloaded_ids]
                
                logger.info(f"Already downloaded: {len(downloaded_ids)}, Pending: {len(pending_topics)}")

                # Process each pending topic
                for i, topic in enumerate(pending_topics):
                    try:
                        topic_id = topic.get('Id')
                        if not topic_id:
                            continue
                            
                        logger.info(f"Downloading topic {i+1}/{len(pending_topics)}: {topic.get('Title', topic_id)}")
                        
                        # Get detailed information for each topic
                        topic_detail = await self._get_myhealthfinder_topic_detail_v4(topic)
                        if topic_detail:
                            all_topics.append(topic_detail)
                            # Save progress immediately after each successful download
                            progress['health_topics']['downloaded'].append(topic_id)
                            self._save_progress(progress)

                        # Rate limiting between requests
                        await asyncio.sleep(self.config.REQUEST_DELAY)

                    except RateLimitError as e:
                        logger.warning(f"Rate limited while downloading topics. Saving progress and stopping.")
                        progress['health_topics']['rate_limited_at'] = datetime.now().isoformat()
                        progress['health_topics']['retry_after'] = e.retry_after
                        self._save_progress(progress)
                        break  # Stop processing but return partial results
                    except Exception as e:
                        logger.exception(f"Error processing topic {topic.get('Id')}: {e}")
                        # Add to failed list but continue with other topics
                        topic_id = topic.get('Id')
                        if topic_id and topic_id not in progress['health_topics']['failed']:
                            progress['health_topics']['failed'].append(topic_id)
                        continue

            self.download_stats["health_topics_downloaded"] = len(all_topics)
            logger.info(f"Downloaded {len(all_topics)} new health topics (total in progress: {len(progress['health_topics']['downloaded'])})")

        except RateLimitError as e:
            logger.warning(f"Rate limited during topics list fetch: {e}")
            progress['health_topics']['rate_limited_at'] = datetime.now().isoformat()
            progress['health_topics']['retry_after'] = e.retry_after
            self._save_progress(progress)
        except Exception as e:
            logger.exception(f"Error downloading MyHealthfinder data: {e}")
            self.download_stats["errors"] += 1

        # If no health topics were downloaded and none were previously downloaded, use fallback data
        if not all_topics and not progress['health_topics']['downloaded']:
            logger.warning("No health topics downloaded from MyHealthfinder API - using fallback health topics")
            all_topics = self._get_fallback_health_topics()
        elif progress['health_topics']['downloaded']:
            # We have partial data from previous runs, that's OK
            logger.info(f"Returning partial data: {len(all_topics)} new + {len(progress['health_topics']['downloaded'])} previously downloaded")

        return all_topics

    async def _get_myhealthfinder_topic_detail_v4(self, topic: dict) -> dict | None:
        """Get detailed information for a specific health topic using API v4"""
        try:
            topic_id = topic.get("Id")
            if not topic_id:
                return None

            # Get topic details using new API v4 endpoint
            detail_url = f"{self.myhealthfinder_url}/topicsearch.json"
            params = {"TopicId": topic_id}

            self.download_stats["requests_made"] += 1
            
            detail_response = await self._retry_with_backoff(
                self.session.get, detail_url, params=params
            )
            
            async with detail_response as response:
                response.raise_for_status()
                data = await response.json()

                result = data.get("Result", {})
                if result.get("Error") != "False":
                    logger.warning(f"API returned error for topic {topic_id}: {result}")
                    return None

                # Parse new v4 API response structure
                resources = result.get("Resources", {}).get("Resource", [])
                if not resources:
                    logger.warning(f"No resource data found for topic {topic_id}")
                    return None
                
                resource = resources[0]  # Take first resource
                
                # Extract sections from the new structure
                sections = []
                if "Sections" in resource:
                    sections_data = resource["Sections"].get("section", [])
                    for section in sections_data:
                        if isinstance(section, dict):
                            # Clean HTML content
                            content = section.get("Content", "")
                            # Remove HTML tags for cleaner storage
                            content = re.sub(r'<[^>]+>', '', content)
                            content = content.replace('&nbsp;', ' ').replace('&amp;', '&')
                            
                            sections.append({
                                "title": section.get("Title", ""),
                                "content": content,
                                "type": "content"
                            })

                # Extract related topics
                related_topics = []
                if "RelatedItems" in resource:
                    related_items = resource["RelatedItems"].get("RelatedItem", [])
                    for item in related_items:
                        if isinstance(item, dict):
                            title = item.get("Title")
                            if title:
                                related_topics.append(title)

                # Create comprehensive topic data
                topic_data = {
                    "topic_id": topic_id,
                    "title": resource.get("Title", topic.get("Title", "")),
                    "category": resource.get("Categories", topic.get("ParentTopic", "General Health")),
                    "url": resource.get("AccessibleVersion", ""),
                    "last_reviewed": resource.get("LastUpdate", ""),
                    "audience": self._extract_audience_v4(resource),
                    "sections": sections,
                    "related_topics": related_topics,
                    "summary": self._create_summary_from_sections(sections),
                    "keywords": self._extract_keywords_from_content(sections),
                    "content_length": sum(len(s.get("content", "")) for s in sections),
                    "source": "myhealthfinder",
                    "search_text": self._create_health_search_text_v4(topic, resource, sections),
                    "last_updated": datetime.now().isoformat()
                }

                return topic_data

        except Exception as e:
            logger.exception(f"Error getting topic detail for {topic.get('Id')}: {e}")
            return None

    def _extract_audience_v4(self, resource: dict) -> List[str]:
        """Extract target audience from v4 API resource"""
        audiences = []
        
        # Check content for audience indicators
        content_str = str(resource).lower()
        
        # Check for age groups
        if any(word in content_str for word in ["adult", "grown-up"]):
            audiences.append("adults")
        if any(word in content_str for word in ["child", "kid", "pediatric"]):
            audiences.append("children")
        if any(word in content_str for word in ["teen", "adolescent", "youth"]):
            audiences.append("teens")
        if any(word in content_str for word in ["senior", "older", "elderly"]):
            audiences.append("seniors")
        
        # Check for specific groups
        if "women" in content_str or "female" in content_str:
            audiences.append("women")
        if "men" in content_str or "male" in content_str:
            audiences.append("men")
        if "pregnant" in content_str or "pregnancy" in content_str:
            audiences.append("pregnant_women")
        
        return audiences if audiences else ["general"]

    def _create_summary_from_sections(self, sections: List[dict]) -> str:
        """Create a summary from the first section or overview"""
        for section in sections:
            title = section.get("title") or ""
            if title.lower() in ["overview", "basics", "the basics"]:
                content = section.get("content", "")
                # Take first 200 characters as summary
                summary = content[:200].strip()
                if len(content) > 200:
                    summary += "..."
                return summary
        
        # If no overview section, use first section
        if sections:
            content = sections[0].get("content", "")
            summary = content[:200].strip()
            if len(content) > 200:
                summary += "..."
            return summary
        
        return ""

    def _extract_keywords_from_content(self, sections: List[dict]) -> List[str]:
        """Extract keywords from section content"""
        all_content = " ".join(s.get("content", "") for s in sections).lower()
        
        # Common health-related keywords to look for
        health_keywords = [
            "health", "prevention", "treatment", "symptoms", "diagnosis", "disease",
            "exercise", "diet", "nutrition", "wellness", "medical", "screening",
            "medication", "therapy", "care", "doctor", "hospital", "clinic"
        ]
        
        found_keywords = []
        for keyword in health_keywords:
            if keyword in all_content:
                found_keywords.append(keyword)
        
        # Add title words as keywords
        title_words = []
        for section in sections:
            title = section.get("title") or ""
            if title:
                words = re.findall(r'\b\w+\b', title.lower())
                title_words.extend([w for w in words if len(w) > 3])
        
        return list(set(found_keywords + title_words))

    def _create_health_search_text_v4(self, topic: dict, resource: dict, sections: List[dict]) -> str:
        """Create searchable text for health topics using v4 data"""
        search_parts = [
            topic.get("Title", ""),
            resource.get("Title", ""),
            resource.get("Categories", ""),
            " ".join(s.get("content", "") for s in sections)
        ]
        
        return " ".join(search_parts).lower()

    async def _download_usda_food_data(self) -> list[dict]:
        """Download comprehensive food data from USDA FoodData Central API"""
        logger.info("Starting comprehensive food download from USDA FoodData Central API")

        if not self.usda_api_key:
            logger.warning("USDA_API_KEY not available - using fallback food data")
            return self._get_fallback_food_items()

        logger.info(f"USDA API key loaded: {self.usda_api_key[:10]}... (length: {len(self.usda_api_key)})")

        # Load progress
        progress = self._load_progress()
        food_progress = progress["food_items"]
        
        # Check if we need to wait for rate limit
        wait_time = self._calculate_wait_time(food_progress)
        if wait_time > 0:
            logger.info(f"Rate limit active, waiting {wait_time:.1f}s before continuing")
            await asyncio.sleep(wait_time)

        all_food_items = food_progress.get("downloaded_items", [])
        food_ids_seen = set(item["fdc_id"] for item in all_food_items if item.get("fdc_id"))
        total_unique_foods = len(food_ids_seen)
        
        logger.info(f"Resuming download - already have {total_unique_foods} unique food items")

        try:
            # Get comprehensive list of food queries
            food_queries = self._get_comprehensive_food_queries()
            completed_queries = set(food_progress.get("queries_completed", []))
            pending_queries = [query for query in food_queries if query not in completed_queries]
            
            logger.info(f"📥 Food queries: {len(completed_queries)} completed, {len(pending_queries)} pending")

            # Download foods for each query with pagination
            await self._download_foods_with_pagination(
                pending_queries, all_food_items, food_ids_seen, 
                food_progress, progress
            )

            # Clear rate limit markers if we completed successfully
            food_progress["rate_limited_at"] = None
            food_progress["retry_after"] = None
            self._save_progress(progress)

            total_unique = len(food_ids_seen)
            logger.info(f"✅ Download complete! Collected {total_unique} unique food items using comprehensive strategy")
            self.download_stats["food_items_downloaded"] = total_unique

        except RateLimitError as e:
            logger.warning(f"Rate limited: {e}. Progress saved, will resume automatically")
            food_progress["rate_limited_at"] = datetime.now().isoformat()
            food_progress["retry_after"] = e.retry_after
            self._save_progress(progress)
        except Exception as e:
            logger.exception(f"Error in comprehensive food download: {e}")
            self.download_stats["errors"] += 1

        # Food data is already complete from search results
        # No need to convert food IDs - they're already full food objects

        # Fallback if no food items were downloaded
        if not all_food_items:
            logger.warning("No food items downloaded - using fallback food data")
            all_food_items = self._get_fallback_food_items()

        return all_food_items

    async def _search_usda_foods(self, query: str, max_results: int = 20) -> list[dict]:
        """Search USDA FoodData Central for specific foods"""
        search_url = f"{self.usda_url}/foods/search"

        params = {
            "api_key": self.usda_api_key,
            "query": query,
            "dataType": ["Foundation", "SR Legacy"],
            "pageSize": max_results,
        }

        logger.info(f"Making USDA API request to: {search_url} with query: {query}")

        food_items = []

        try:
            self.download_stats["requests_made"] += 1
            async with self.session.get(search_url, params=params, timeout=10) as response:
                response.raise_for_status()
                data = await response.json()

                foods = data.get("foods", [])

                for food in foods:
                    food_data = {
                        "fdc_id": food.get("fdcId"),
                        "description": food.get("description", ""),
                        "scientific_name": food.get("scientificName", ""),
                        "common_names": food.get("commonNames", ""),
                        "food_category": food.get("foodCategory", ""),
                        "nutrients": self._extract_nutrients(food.get("foodNutrients", [])),
                        "brand_owner": food.get("brandOwner", ""),
                        "ingredients": food.get("ingredients", ""),
                        "serving_size": food.get("servingSize"),
                        "serving_size_unit": food.get("servingSizeUnit"),
                        "category": "food",
                        "source": "usda_fooddata",
                        "last_updated": datetime.now().isoformat(),
                        "search_text": f"{food.get('description', '')} {food.get('commonNames', '')}".lower(),
                    }
                    food_items.append(food_data)

        except Exception as e:
            logger.exception(f"Error searching USDA for '{query}': {type(e).__name__}: {e}")
            # Return what we have so far instead of raising
            return food_items

        return food_items

    def _extract_nutrients(self, food_nutrients: list[dict]) -> list[dict]:
        """Extract key nutrients from USDA food nutrients data"""
        key_nutrients = [
            "Energy", "Protein", "Total lipid (fat)", "Carbohydrate, by difference",
            "Fiber, total dietary", "Sugars, total including NLEA", "Sodium, Na",
            "Vitamin C, total ascorbic acid", "Calcium, Ca", "Iron, Fe",
        ]

        extracted = []

        for nutrient in food_nutrients:
            nutrient_name = nutrient.get("nutrientName", "")
            if any(key in nutrient_name for key in key_nutrients):
                extracted.append({
                    "name": nutrient_name,
                    "amount": nutrient.get("value"),
                    "unit": nutrient.get("unitName", ""),
                    "nutrient_number": nutrient.get("nutrientNumber"),
                })

        return extracted[:10]  # Limit to top 10 nutrients

    def _get_comprehensive_food_queries(self) -> List[str]:
        """Get comprehensive list of food search queries"""
        return [
            # Core proteins
            "chicken", "beef", "salmon", "tuna", "eggs", "turkey", "pork", "shrimp", "cod", "tilapia",
            "tofu", "tempeh", "beans", "lentils", "chickpeas", "black beans", "kidney beans", "quinoa",
            
            # Dairy and alternatives
            "milk", "cheese", "yogurt", "butter", "cream", "cottage cheese", "mozzarella", "cheddar",
            "almond milk", "soy milk", "coconut milk", "oat milk", "ricotta", "feta",
            
            # Grains and starches
            "rice", "bread", "pasta", "oats", "quinoa", "barley", "wheat", "corn", "millet", "buckwheat",
            "brown rice", "wild rice", "basmati rice", "jasmine rice", "couscous", "bulgur", "farro",
            
            # Vegetables
            "broccoli", "spinach", "kale", "carrots", "sweet potato", "potato", "tomato", "onion",
            "bell pepper", "zucchini", "cauliflower", "brussels sprouts", "asparagus", "cabbage",
            "cucumber", "celery", "lettuce", "mushrooms", "eggplant", "squash", "pumpkin",
            
            # Fruits
            "apple", "banana", "orange", "strawberry", "blueberry", "grapes", "pineapple", "mango",
            "avocado", "lemon", "lime", "grapefruit", "peach", "pear", "cherry", "watermelon",
            "cantaloupe", "kiwi", "papaya", "pomegranate", "blackberry", "raspberry",
            
            # Nuts and seeds
            "almonds", "walnuts", "cashews", "pecans", "peanuts", "pistachios", "sunflower seeds",
            "chia seeds", "flax seeds", "pumpkin seeds", "sesame seeds", "hemp seeds",
            
            # Oils and fats
            "olive oil", "coconut oil", "avocado oil", "canola oil", "butter", "ghee", "sesame oil",
            
            # Pantry staples
            "flour", "sugar", "salt", "pepper", "garlic", "ginger", "cinnamon", "vanilla", "honey",
            "maple syrup", "vinegar", "soy sauce", "baking powder", "yeast",
            
            # Ethnic and specialty foods
            "kimchi", "miso", "seaweed", "tahini", "hummus", "salsa", "pesto", "curry powder",
            "turmeric", "cumin", "paprika", "oregano", "basil", "thyme", "rosemary",
            
            # Processed/convenience foods
            "cereal", "crackers", "granola", "soup", "frozen vegetables", "canned tomatoes",
            "peanut butter", "almond butter", "jam", "pickles", "olives"
        ]

    async def _download_foods_with_pagination(self, queries: List[str], all_food_items: List[dict], 
                                            food_ids_seen: set, food_progress: dict, progress: dict):
        """Download foods for each query with pagination support"""
        for i, query in enumerate(queries):
            try:
                logger.info(f"Downloading foods for query: '{query}' ({i+1}/{len(queries)})")
                
                # Download with pagination (up to 4 pages = 200 items per query)
                query_food_items = await self._search_usda_foods_paginated(query, max_pages=4)
                
                new_foods = 0
                for food_item in query_food_items:
                    fdc_id = food_item.get("fdc_id")
                    if fdc_id and fdc_id not in food_ids_seen:
                        food_ids_seen.add(fdc_id)
                        all_food_items.append(food_item)
                        new_foods += 1
                
                logger.info(f"✅ Query '{query}': {len(query_food_items)} total, {new_foods} new unique foods")
                
                # Mark this query as completed and save progress
                food_progress["queries_completed"].append(query)
                food_progress["downloaded_items"] = all_food_items
                self._save_progress(progress)
                
                # Rate limiting - USDA has 1000 requests/hour limit (0.36s minimum between requests)
                # Use 3.6s delay to stay well under limit (1000 requests/hour = ~3.6s per request)
                await asyncio.sleep(3.6)
                
            except RateLimitError:
                # Let the parent method handle rate limits
                raise
            except Exception as e:
                logger.warning(f"Failed to download foods for query '{query}': {e}")
                continue

    async def _search_usda_foods_paginated(self, query: str, max_pages: int = 4) -> List[dict]:
        """Search USDA foods with pagination support"""
        all_foods = []
        page_size = 50  # USDA allows up to 200, but 50 is more reliable
        
        for page_num in range(1, max_pages + 1):
            try:
                search_url = f"{self.usda_url}/foods/search"
                params = {
                    "api_key": self.usda_api_key,
                    "query": query,
                    "dataType": ["Foundation", "SR Legacy", "Survey (FNDDS)"],
                    "pageSize": page_size,
                    "pageNumber": page_num,
                }
                
                logger.debug(f"USDA API request: {query} (page {page_num})")
                self.download_stats["requests_made"] += 1
                
                response = await self._retry_with_backoff(
                    self.session.get, search_url, params=params, timeout=15
                )
                
                async with response as resp:
                    if resp.status == 429:  # Rate limit exceeded
                        retry_after = int(resp.headers.get('Retry-After', 3600))  # Default 1 hour
                        raise RateLimitError(f"USDA API rate limit exceeded", retry_after)
                    resp.raise_for_status()
                    data = await resp.json()
                    
                    foods = data.get("foods", [])
                    if not foods:
                        logger.debug(f"No more foods found for '{query}' at page {page_num}")
                        break
                    
                    # Process foods into our standard format
                    page_foods = []
                    for food in foods:
                        food_data = {
                            "fdc_id": food.get("fdcId"),
                            "description": food.get("description", ""),
                            "scientific_name": food.get("scientificName", ""),
                            "common_names": food.get("commonNames", ""),
                            "food_category": food.get("foodCategory", ""),
                            "nutrients": self._extract_nutrients(food.get("foodNutrients", [])),
                            "brand_owner": food.get("brandOwner", ""),
                            "ingredients": food.get("ingredients", ""),
                            "serving_size": food.get("servingSize"),
                            "serving_size_unit": food.get("servingSizeUnit"),
                            "category": "food",
                            "source": "usda_fooddata",
                            "last_updated": datetime.now().isoformat(),
                            "search_text": f"{food.get('description', '')} {food.get('commonNames', '')}".lower(),
                        }
                        page_foods.append(food_data)
                    
                    all_foods.extend(page_foods)
                    logger.debug(f"Page {page_num}: {len(page_foods)} foods (total: {len(all_foods)})")
                    
                    # If we got fewer than page_size, we've reached the end
                    if len(foods) < page_size:
                        logger.debug(f"Reached end of results for '{query}' at page {page_num}")
                        break
                
                # USDA-specific rate limit (1000 requests/hour = 0.28 req/sec)
                await asyncio.sleep(self.config.USDA_FOOD_REQUEST_DELAY)
                
            except Exception as e:
                logger.warning(f"Error fetching page {page_num} for '{query}': {e}")
                break
        
        return all_foods

    async def _get_full_food_data(self, food_ids: List[str]) -> List[dict]:
        """Get full food data from food IDs (placeholder - food data is already complete)"""
        # For foods, we already have full data from the search results
        # This method exists for API consistency with exercises
        logger.info(f"Food data already complete for {len(food_ids)} items")
        return []

    def get_download_stats(self) -> dict:
        """Get download statistics"""
        stats = self.download_stats.copy()

        if stats["start_time"] and stats["end_time"]:
            duration = stats["end_time"] - stats["start_time"]
            stats["duration_seconds"] = duration.total_seconds()

            total_items = (stats["health_topics_downloaded"] +
                          stats["exercises_downloaded"] +
                          stats["food_items_downloaded"])
            stats["total_items_downloaded"] = total_items
            stats["items_per_second"] = (
                total_items / duration.total_seconds()
                if duration.total_seconds() > 0 else 0
            )

        return stats

    def _get_fallback_health_topics(self) -> list[dict]:
        """Comprehensive fallback health topics for when MyHealthfinder API is unavailable"""
        return [
            {
                "topic_id": "ht_001",
                "title": "Healthy Eating",
                "category": "Nutrition",
                "url": "https://www.myplate.gov",
                "last_reviewed": "2024-01-01",
                "audience": ["adults", "teens"],
                "sections": [
                    {"title": "Overview", "content": "Eating a variety of foods helps ensure you get all the nutrients your body needs.", "type": "content"},
                    {"title": "Guidelines", "content": "Follow MyPlate recommendations: fill half your plate with fruits and vegetables, choose whole grains, lean proteins, and low-fat dairy.", "type": "recommendations"},
                    {"title": "Tips", "content": "Read nutrition labels, limit processed foods, cook at home more often, and stay hydrated with water.", "type": "tips"},
                ],
                "related_topics": ["Physical Activity", "Weight Management", "Diabetes Prevention"],
                "summary": "Learn about healthy eating patterns and making nutritious food choices following MyPlate guidelines.",
                "keywords": ["nutrition", "healthy eating", "diet", "food choices", "myplate", "balanced meals"],
                "content_length": 350,
                "source": "curated",
                "search_text": "healthy eating nutrition diet food choices myplate balanced meals",
                "last_updated": datetime.now().isoformat(),
            },
            {
                "topic_id": "ht_002",
                "title": "Physical Activity",
                "category": "Exercise",
                "url": "https://www.cdc.gov/physicalactivity/basics/adults/index.htm",
                "last_reviewed": "2024-01-01",
                "audience": ["adults", "teens", "seniors"],
                "sections": [
                    {"title": "Overview", "content": "Regular physical activity is one of the most important things you can do for your health.", "type": "content"},
                    {"title": "Guidelines", "content": "Adults need at least 150 minutes of moderate-intensity aerobic activity and 2 days of muscle-strengthening activities per week.", "type": "recommendations"},
                    {"title": "Benefits", "content": "Reduces risk of heart disease, diabetes, stroke, and some cancers. Improves mental health and helps maintain healthy weight.", "type": "benefits"},
                ],
                "related_topics": ["Healthy Eating", "Heart Health", "Weight Management", "Mental Health"],
                "summary": "Discover the benefits of regular physical activity and how to get started with exercise recommendations.",
                "keywords": ["exercise", "physical activity", "fitness", "health", "cardio", "strength training"],
                "content_length": 400,
                "source": "curated",
                "search_text": "physical activity exercise fitness health cardio strength training",
                "last_updated": datetime.now().isoformat(),
            }
        ]

    def _get_fallback_exercises(self) -> list[dict]:
        """Fallback exercises for when ExerciseDB API is unavailable"""
        return [
            {
                "exercise_id": "fallback_ex_1",
                "name": "Push-ups",
                "body_part": "chest",
                "equipment": "body weight",
                "target": "pectorals",
                "secondary_muscles": ["triceps", "shoulders"],
                "instructions": ["Start in a plank position", "Lower your body until chest nearly touches floor", "Push back up to starting position"],
                "gif_url": "",
                "difficulty_level": "beginner",
                "exercise_type": "strength",
                "duration_estimate": 15,
                "calories_estimate": 50,
                "source": "fallback",
                "search_text": "push-ups chest body weight pectorals",
                "last_updated": datetime.now().isoformat(),
            },
            {
                "exercise_id": "fallback_ex_2",
                "name": "Squats",
                "body_part": "legs",
                "equipment": "body weight",
                "target": "quadriceps",
                "secondary_muscles": ["glutes", "hamstrings"],
                "instructions": ["Stand with feet shoulder-width apart", "Lower your body as if sitting back into a chair", "Return to standing position"],
                "gif_url": "",
                "difficulty_level": "beginner",
                "exercise_type": "strength",
                "duration_estimate": 15,
                "calories_estimate": 40,
                "source": "fallback",
                "search_text": "squats legs body weight quadriceps",
                "last_updated": datetime.now().isoformat(),
            },
            {
                "exercise_id": "fallback_ex_3",
                "name": "Walking",
                "body_part": "cardio",
                "equipment": "none",
                "target": "cardiovascular system",
                "secondary_muscles": ["legs", "core"],
                "instructions": ["Start with a comfortable pace", "Maintain good posture", "Gradually increase duration and intensity"],
                "gif_url": "",
                "difficulty_level": "beginner",
                "exercise_type": "cardio",
                "duration_estimate": 30,
                "calories_estimate": 150,
                "source": "fallback",
                "search_text": "walking cardio cardiovascular legs",
                "last_updated": datetime.now().isoformat(),
            },
        ]

    def _get_fallback_food_items(self) -> list[dict]:
        """Fallback food items for when USDA API is unavailable"""
        return [
            {
                "fdc_id": "fallback_food_1",
                "description": "Apple, raw",
                "scientific_name": "Malus domestica",
                "common_names": ["apple", "red apple", "green apple"],
                "food_category": "Fruits",
                "nutrients": [{"name": "Energy", "amount": 52, "unit": "kcal"}, {"name": "Carbohydrate", "amount": 14, "unit": "g"}],
                "nutrition_summary": "Low calorie fruit high in fiber and vitamin C",
                "brand_owner": "",
                "ingredients": "",
                "serving_size": 182,
                "serving_size_unit": "g",
                "allergens": "",
                "dietary_flags": ["vegan", "gluten-free"],
                "nutritional_density": 8.5,
                "source": "fallback",
                "search_text": "apple raw fruit malus domestica",
                "last_updated": datetime.now().isoformat(),
            },
            {
                "fdc_id": "fallback_food_2",
                "description": "Chicken breast, skinless, boneless, raw",
                "scientific_name": "Gallus gallus domesticus",
                "common_names": ["chicken breast", "chicken", "poultry"],
                "food_category": "Proteins",
                "nutrients": [{"name": "Energy", "amount": 165, "unit": "kcal"}, {"name": "Protein", "amount": 31, "unit": "g"}],
                "nutrition_summary": "High protein, low fat meat source",
                "brand_owner": "",
                "ingredients": "",
                "serving_size": 100,
                "serving_size_unit": "g",
                "allergens": "",
                "dietary_flags": ["high-protein", "low-carb"],
                "nutritional_density": 9.2,
                "source": "fallback",
                "search_text": "chicken breast protein poultry gallus",
                "last_updated": datetime.now().isoformat(),
            },
            {
                "fdc_id": "fallback_food_3",
                "description": "Broccoli, raw",
                "scientific_name": "Brassica oleracea",
                "common_names": ["broccoli", "green vegetable"],
                "food_category": "Vegetables",
                "nutrients": [{"name": "Energy", "amount": 34, "unit": "kcal"}, {"name": "Vitamin C", "amount": 89, "unit": "mg"}],
                "nutrition_summary": "Nutrient-dense vegetable high in vitamins and minerals",
                "brand_owner": "",
                "ingredients": "",
                "serving_size": 100,
                "serving_size_unit": "g",
                "allergens": "",
                "dietary_flags": ["vegan", "gluten-free", "low-calorie"],
                "nutritional_density": 9.8,
                "source": "fallback",
                "search_text": "broccoli raw vegetable brassica oleracea",
                "last_updated": datetime.now().isoformat(),
            },
        ]


async def main():
    """Test the health info downloader"""
    logging.basicConfig(level=logging.INFO)
    config = Config()

    async with HealthInfoDownloader(config) as downloader:
        # Test MyHealthfinder
        topics = await downloader._download_myhealthfinder_data()
        print(f"Found {len(topics)} health topics")

        if topics:
            print(f"Sample topic: {topics[0]['title']}")

        # Get stats
        stats = downloader.get_download_stats()
        print(f"\nDownload stats: {stats}")


if __name__ == "__main__":
    asyncio.run(main())