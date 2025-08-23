"""
Health information APIs downloader (MyHealthfinder, ExerciseDB, USDA FoodData Central)
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

import aiohttp
from aiohttp import ClientError

from config import Config

logger = logging.getLogger(__name__)


class HealthInfoDownloader:
    """Downloads health information from free public APIs"""
    
    def __init__(self, config: Config):
        self.config = config
        
        # API endpoints
        self.myhealthfinder_url = "https://healthfinder.gov/developer/api"
        self.exercisedb_url = "https://exercisedb.p.rapidapi.com"
        self.usda_url = "https://api.nal.usda.gov/fdc/v1"
        
        # API keys from environment
        self.rapidapi_key = os.getenv("RAPIDAPI_KEY")
        self.usda_api_key = os.getenv("USDA_API_KEY")
        
        self.session = None
        self.download_stats = {
            "health_topics_downloaded": 0,
            "exercises_downloaded": 0,
            "food_items_downloaded": 0,
            "requests_made": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"User-Agent": "Medical-Mirrors/1.0 (Healthcare Research)"}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def download_all_health_data(self) -> Dict[str, List[Dict]]:
        """Download all available health information data"""
        logger.info("Starting comprehensive health information download")
        self.download_stats["start_time"] = datetime.now()
        
        all_data = {
            "health_topics": [],
            "exercises": [],
            "food_items": []
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
            logger.error(f"Error in health information download: {e}")
            self.download_stats["errors"] += 1
            raise
    
    async def _download_myhealthfinder_data(self) -> List[Dict]:
        """Download health topics from MyHealthfinder API"""
        logger.info("Downloading MyHealthfinder health topics")
        
        all_topics = []
        
        try:
            # Get health topics overview
            topics_url = f"{self.myhealthfinder_url}/topicslist.json"
            
            self.download_stats["requests_made"] += 1
            async with self.session.get(topics_url) as response:
                response.raise_for_status()
                data = await response.json()
                
                topics_data = data.get("Result", {}).get("Topics", [])
                
                # Process each topic
                for topic in topics_data:
                    try:
                        # Get detailed information for each topic
                        topic_detail = await self._get_myhealthfinder_topic_detail(topic)
                        if topic_detail:
                            all_topics.append(topic_detail)
                            
                        # Rate limiting
                        await asyncio.sleep(self.config.REQUEST_DELAY)
                        
                    except Exception as e:
                        logger.error(f"Error processing topic {topic.get('Id')}: {e}")
                        continue
            
            self.download_stats["health_topics_downloaded"] = len(all_topics)
            logger.info(f"Downloaded {len(all_topics)} health topics")
            
        except Exception as e:
            logger.error(f"Error downloading MyHealthfinder data: {e}")
            self.download_stats["errors"] += 1
        
        # If no health topics were downloaded, use fallback data
        if not all_topics:
            logger.warning("No health topics downloaded from MyHealthfinder API - using fallback health topics")
            all_topics = self._get_fallback_health_topics()
        
        return all_topics
    
    async def _get_myhealthfinder_topic_detail(self, topic: Dict) -> Optional[Dict]:
        """Get detailed information for a specific health topic"""
        try:
            topic_id = topic.get("Id")
            if not topic_id:
                return None
            
            # Get topic details
            detail_url = f"{self.myhealthfinder_url}/topic.json"
            params = {"TopicId": topic_id}
            
            self.download_stats["requests_made"] += 1
            async with self.session.get(detail_url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                
                result = data.get("Result", {})
                if not result:
                    return None
                
                # Parse topic details
                topic_data = {
                    "topic_id": topic_id,
                    "title": topic.get("Title", ""),
                    "category": topic.get("ParentTopic", "General Health"),
                    "url": topic.get("AccessibleVersion", ""),
                    "last_reviewed": result.get("LastUpdate", ""),
                    "audience": self._extract_audience(result),
                    "sections": self._extract_sections(result),
                    "related_topics": self._extract_related_topics(result),
                    "source": "myhealthfinder",
                    "last_updated": datetime.now().isoformat(),
                    "search_text": self._create_health_search_text(topic, result)
                }
                
                return topic_data
                
        except Exception as e:
            logger.error(f"Error getting topic detail for {topic.get('Id')}: {e}")
            return None
    
    def _extract_audience(self, result: Dict) -> List[str]:
        """Extract target audience from topic result"""
        audiences = []
        
        # Check for age groups
        if "Adults" in str(result):
            audiences.append("adults")
        if "Children" in str(result) or "Kids" in str(result):
            audiences.append("children")
        if "Teens" in str(result) or "Adolescent" in str(result):
            audiences.append("teens")
        if "Seniors" in str(result) or "Older" in str(result):
            audiences.append("seniors")
        
        # Check for specific groups
        if "Women" in str(result):
            audiences.append("women")
        if "Men" in str(result):
            audiences.append("men")
        if "Pregnant" in str(result):
            audiences.append("pregnant_women")
        
        return audiences if audiences else ["general"]
    
    def _extract_sections(self, result: Dict) -> List[Dict]:
        """Extract content sections from topic result"""
        sections = []
        
        # Try to extract sections from the result
        # MyHealthfinder API structure may vary, so this is adaptable
        if "Sections" in result:
            for section in result.get("Sections", []):
                if isinstance(section, dict):
                    sections.append({
                        "title": section.get("Title", ""),
                        "content": section.get("Content", ""),
                        "type": section.get("Type", "content")
                    })
        
        return sections
    
    def _extract_related_topics(self, result: Dict) -> List[str]:
        """Extract related topics from result"""
        related = []
        
        if "RelatedTopics" in result:
            for topic in result.get("RelatedTopics", []):
                if isinstance(topic, dict):
                    title = topic.get("Title")
                    if title:
                        related.append(title)
        
        return related
    
    def _create_health_search_text(self, topic: Dict, result: Dict) -> str:
        """Create searchable text for health topics"""
        search_parts = [
            topic.get("Title", ""),
            topic.get("ParentTopic", ""),
            str(result)  # Include all content for search
        ]
        
        return " ".join(search_parts).lower()
    
    async def _download_exercise_data(self) -> List[Dict]:
        """Download exercise data from ExerciseDB API by body parts"""
        logger.info("Downloading complete exercise data from ExerciseDB")
        
        if not self.rapidapi_key:
            logger.warning("RAPIDAPI_KEY not available - using fallback exercise data")
            return self._get_fallback_exercises()
        
        exercises = []
        
        try:
            headers = {
                "X-RapidAPI-Key": self.rapidapi_key,
                "X-RapidAPI-Host": "exercisedb.p.rapidapi.com"
            }
            
            # First get all body parts available
            logger.info("Getting available body parts from ExerciseDB")
            self.download_stats["requests_made"] += 1
            
            body_parts_url = f"{self.exercisedb_url}/exercises/bodyPartList"
            async with self.session.get(body_parts_url, headers=headers, timeout=15) as response:
                if response.status == 200:
                    body_parts = await response.json()
                    logger.info(f"Found {len(body_parts)} body parts: {body_parts}")
                else:
                    logger.warning(f"Failed to get body parts list: {response.status}")
                    body_parts = ["back", "cardio", "chest", "lower arms", "lower legs", "neck", "shoulders", "upper arms", "upper legs", "waist"]
            
            # Download exercises for each body part
            exercise_ids_seen = set()
            
            for body_part in body_parts:
                logger.info(f"Downloading exercises for body part: {body_part}")
                exercises_url = f"{self.exercisedb_url}/exercises/bodyPart/{body_part.replace(' ', '%20')}"
                
                self.download_stats["requests_made"] += 1
                
                try:
                    async with self.session.get(exercises_url, headers=headers, timeout=15) as response:
                        if response.status == 200:
                            data = await response.json()
                            logger.info(f"Body part '{body_part}' returned {len(data)} exercises")
                            
                            for exercise in data:
                                exercise_id = exercise.get("id", "")
                                
                                # Skip duplicates
                                if exercise_id in exercise_ids_seen:
                                    continue
                                exercise_ids_seen.add(exercise_id)
                                
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
                                    "search_text": f"{exercise.get('name', '')} {exercise.get('bodyPart', '')} {exercise.get('target', '')}".lower()
                                }
                                exercises.append(exercise_data)
                        elif response.status == 429:
                            logger.warning("Rate limited - waiting before next request")
                            await asyncio.sleep(5)
                        else:
                            logger.warning(f"Failed to get exercises for {body_part}: {response.status}")
                    
                    # Rate limiting between requests
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error downloading exercises for {body_part}: {e}")
                    continue
            
            self.download_stats["exercises_downloaded"] = len(exercises)
            logger.info(f"Successfully downloaded {len(exercises)} total exercises from {len(body_parts)} body parts")
            
        except Exception as e:
            logger.error(f"Error downloading exercise data: {e}")
            self.download_stats["errors"] += 1
        
        # If no exercises were downloaded, use fallback data
        if not exercises:
            logger.warning("No exercises downloaded from API - using fallback exercise data")
            exercises = self._get_fallback_exercises()
        
        return exercises
    
    async def _download_exercises_with_pagination(self, headers: dict, limit_per_page: int = 50) -> List[Dict]:
        """Download exercises using pagination if the API supports it"""
        logger.info("Downloading exercises with pagination")
        exercises = []
        offset = 0
        max_retries = 20  # Maximum 20 pages * 50 = 1000 exercises
        
        while len(exercises) < 1500 and offset < max_retries:  # ExerciseDB has ~1300 exercises
            try:
                exercises_url = f"{self.exercisedb_url}/exercises"
                params = {"limit": str(limit_per_page), "offset": str(offset * limit_per_page)}
                
                logger.info(f"Downloading page {offset + 1}, offset {offset * limit_per_page}")
                self.download_stats["requests_made"] += 1
                
                async with self.session.get(exercises_url, headers=headers, params=params, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if not data or len(data) == 0:
                            logger.info("No more exercises found - pagination complete")
                            break
                        
                        page_exercises = []
                        for exercise in data:
                            exercise_data = {
                                "exercise_id": exercise.get("id", ""),
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
                                "search_text": f"{exercise.get('name', '')} {exercise.get('bodyPart', '')} {exercise.get('target', '')}".lower()
                            }
                            page_exercises.append(exercise_data)
                        
                        exercises.extend(page_exercises)
                        logger.info(f"Downloaded {len(page_exercises)} exercises from page {offset + 1} (total: {len(exercises)})")
                        
                        # If we got fewer than the limit, we've reached the end
                        if len(data) < limit_per_page:
                            logger.info("Reached end of exercise data")
                            break
                            
                    elif response.status == 429:
                        logger.warning("Rate limited - waiting 10 seconds")
                        await asyncio.sleep(10)
                        continue  # Retry same page
                    else:
                        logger.warning(f"API returned status {response.status} for page {offset + 1}")
                        break
                
                # Rate limiting between requests
                await asyncio.sleep(1)
                offset += 1
                
            except Exception as e:
                logger.error(f"Error downloading page {offset + 1}: {e}")
                break
        
        logger.info(f"Pagination download complete: {len(exercises)} total exercises")
        return exercises
    
    async def _download_usda_food_data(self) -> List[Dict]:
        """Download food data from USDA FoodData Central API"""
        logger.info("Downloading USDA food data")
        
        if not self.usda_api_key:
            logger.warning("USDA_API_KEY not available - using fallback food data")
            return self._get_fallback_food_items()
        
        logger.info(f"USDA API key loaded: {self.usda_api_key[:10]}... (length: {len(self.usda_api_key)})")
        
        food_items = []
        
        try:
            # Search for common foods
            common_foods = [
                "apple", "banana", "chicken", "beef", "salmon", "rice", "bread",
                "milk", "cheese", "eggs", "broccoli", "spinach", "tomato",
                "potato", "carrot", "orange", "beans", "pasta", "oats"
            ]
            
            logger.info(f"Starting USDA food download for {len(common_foods)} food types")
            
            for food in common_foods:
                try:
                    logger.info(f"Searching USDA for: {food}")
                    food_data = await self._search_usda_foods(food)
                    food_items.extend(food_data)
                    logger.info(f"Found {len(food_data)} items for '{food}'")
                    
                    # Rate limiting
                    await asyncio.sleep(self.config.REQUEST_DELAY * 2)  # USDA has stricter limits
                    
                except Exception as e:
                    logger.error(f"Error searching USDA for '{food}': {e}")
                    continue
            
            self.download_stats["food_items_downloaded"] = len(food_items)
            logger.info(f"Downloaded {len(food_items)} total food items from USDA")
            
        except Exception as e:
            logger.error(f"Error downloading USDA food data: {e}")
            self.download_stats["errors"] += 1
        
        # If no food items or very few were downloaded, use fallback data
        expected_minimum = len(common_foods) * 2  # At least 2 items per food type on average
        if not food_items or len(food_items) < expected_minimum:
            if not food_items:
                logger.warning("No food items downloaded from USDA API - using fallback food data")
            else:
                logger.warning(f"Only {len(food_items)} food items downloaded (expected minimum {expected_minimum}) - using fallback food data")
            food_items = self._get_fallback_food_items()
        
        return food_items
    
    async def _search_usda_foods(self, query: str, max_results: int = 20) -> List[Dict]:
        """Search USDA FoodData Central for specific foods"""
        search_url = f"{self.usda_url}/foods/search"
        
        params = {
            "api_key": self.usda_api_key,
            "query": query,
            "dataType": ["Foundation", "SR Legacy"],
            "pageSize": max_results
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
                        "search_text": f"{food.get('description', '')} {food.get('commonNames', '')}".lower()
                    }
                    food_items.append(food_data)
        
        except Exception as e:
            logger.error(f"Error searching USDA for '{query}': {type(e).__name__}: {e}")
            # Return what we have so far instead of raising
            return food_items
        
        return food_items
    
    def _extract_nutrients(self, food_nutrients: List[Dict]) -> List[Dict]:
        """Extract key nutrients from USDA food nutrients data"""
        key_nutrients = [
            "Energy", "Protein", "Total lipid (fat)", "Carbohydrate, by difference",
            "Fiber, total dietary", "Sugars, total including NLEA", "Sodium, Na",
            "Vitamin C, total ascorbic acid", "Calcium, Ca", "Iron, Fe"
        ]
        
        extracted = []
        
        for nutrient in food_nutrients:
            nutrient_name = nutrient.get("nutrientName", "")
            if any(key in nutrient_name for key in key_nutrients):
                extracted.append({
                    "name": nutrient_name,
                    "amount": nutrient.get("value"),
                    "unit": nutrient.get("unitName", ""),
                    "nutrient_number": nutrient.get("nutrientNumber")
                })
        
        return extracted[:10]  # Limit to top 10 nutrients
    
    def get_download_stats(self) -> Dict:
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
    
    def _get_fallback_health_topics(self) -> List[Dict]:
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
                    {"title": "Tips", "content": "Read nutrition labels, limit processed foods, cook at home more often, and stay hydrated with water.", "type": "tips"}
                ],
                "related_topics": ["Physical Activity", "Weight Management", "Diabetes Prevention"],
                "summary": "Learn about healthy eating patterns and making nutritious food choices following MyPlate guidelines.",
                "keywords": ["nutrition", "healthy eating", "diet", "food choices", "myplate", "balanced meals"],
                "content_length": 350,
                "source": "curated",
                "search_text": "healthy eating nutrition diet food choices myplate balanced meals",
                "last_updated": datetime.now().isoformat()
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
                    {"title": "Benefits", "content": "Reduces risk of heart disease, diabetes, stroke, and some cancers. Improves mental health and helps maintain healthy weight.", "type": "benefits"}
                ],
                "related_topics": ["Healthy Eating", "Heart Health", "Weight Management", "Mental Health"],
                "summary": "Discover the benefits of regular physical activity and how to get started with exercise recommendations.",
                "keywords": ["exercise", "physical activity", "fitness", "health", "cardio", "strength training"],
                "content_length": 400,
                "source": "curated",
                "search_text": "physical activity exercise fitness health cardio strength training",
                "last_updated": datetime.now().isoformat()
            },
            {
                "topic_id": "ht_003",
                "title": "Heart Health",
                "category": "Cardiovascular",
                "url": "https://www.cdc.gov/heartdisease/prevention.htm",
                "last_reviewed": "2024-01-01",
                "audience": ["adults", "seniors"],
                "sections": [
                    {"title": "Overview", "content": "Heart disease is the leading cause of death, but it's largely preventable through lifestyle changes.", "type": "content"},
                    {"title": "Risk Factors", "content": "High blood pressure, high cholesterol, smoking, diabetes, obesity, poor diet, and physical inactivity increase heart disease risk.", "type": "risk_factors"},
                    {"title": "Prevention", "content": "Eat healthy foods, maintain healthy weight, exercise regularly, don't smoke, limit alcohol, and manage stress.", "type": "prevention"}
                ],
                "related_topics": ["Physical Activity", "Healthy Eating", "Blood Pressure", "Cholesterol"],
                "summary": "Learn about heart disease prevention and maintaining cardiovascular health through lifestyle changes.",
                "keywords": ["heart health", "cardiovascular", "prevention", "heart disease", "blood pressure", "cholesterol"],
                "content_length": 450,
                "source": "curated",
                "search_text": "heart health cardiovascular prevention heart disease blood pressure cholesterol",
                "last_updated": datetime.now().isoformat()
            },
            {
                "topic_id": "ht_004",
                "title": "Mental Health",
                "category": "Mental Health",
                "url": "https://www.mentalhealth.gov",
                "last_reviewed": "2024-01-01",
                "audience": ["adults", "teens"],
                "sections": [
                    {"title": "Overview", "content": "Mental health includes emotional, psychological, and social well-being. It affects how we think, feel, and act.", "type": "content"},
                    {"title": "Signs", "content": "Eating or sleeping too much or too little, pulling away from people, having little or no energy, feeling hopeless.", "type": "warning_signs"},
                    {"title": "Support", "content": "Talk to someone you trust, get professional help if needed, practice self-care, connect with others.", "type": "support"}
                ],
                "related_topics": ["Physical Activity", "Stress Management", "Sleep Health"],
                "summary": "Understanding mental health and knowing when and how to get help for mental health concerns.",
                "keywords": ["mental health", "depression", "anxiety", "stress", "wellness", "therapy"],
                "content_length": 380,
                "source": "curated",
                "search_text": "mental health depression anxiety stress wellness therapy",
                "last_updated": datetime.now().isoformat()
            },
            {
                "topic_id": "ht_005",
                "title": "Sleep Health",
                "category": "Sleep",
                "url": "https://www.cdc.gov/sleep/about_sleep/why_it_matters.html",
                "last_reviewed": "2024-01-01",
                "audience": ["adults", "teens"],
                "sections": [
                    {"title": "Overview", "content": "Getting enough quality sleep is essential for good health and well-being.", "type": "content"},
                    {"title": "Guidelines", "content": "Adults need 7-9 hours of sleep per night. Teens need 8-10 hours. Keep a consistent sleep schedule.", "type": "recommendations"},
                    {"title": "Tips", "content": "Create a relaxing bedtime routine, keep bedroom dark and cool, avoid screens before bed, limit caffeine.", "type": "tips"}
                ],
                "related_topics": ["Mental Health", "Physical Activity", "Stress Management"],
                "summary": "Learn about the importance of sleep and tips for getting better quality rest.",
                "keywords": ["sleep", "rest", "insomnia", "sleep hygiene", "bedtime routine"],
                "content_length": 320,
                "source": "curated",
                "search_text": "sleep rest insomnia sleep hygiene bedtime routine",
                "last_updated": datetime.now().isoformat()
            },
            {
                "topic_id": "ht_006",
                "title": "Preventive Care",
                "category": "Prevention",
                "url": "https://www.healthfinder.gov/health-tools/my-health-finder",
                "last_reviewed": "2024-01-01",
                "audience": ["adults", "seniors"],
                "sections": [
                    {"title": "Overview", "content": "Preventive care includes checkups, screenings, and vaccines to help prevent illness and detect problems early.", "type": "content"},
                    {"title": "Screenings", "content": "Regular screenings for blood pressure, cholesterol, diabetes, cancer, and other conditions based on age and risk factors.", "type": "screenings"},
                    {"title": "Vaccines", "content": "Stay up to date with recommended vaccines including flu shot, COVID-19, and others based on age and health conditions.", "type": "vaccines"}
                ],
                "related_topics": ["Heart Health", "Cancer Prevention", "Immunizations"],
                "summary": "Understanding the importance of preventive care including regular checkups, screenings, and vaccinations.",
                "keywords": ["preventive care", "checkups", "screenings", "vaccines", "immunizations", "early detection"],
                "content_length": 380,
                "source": "curated",
                "search_text": "preventive care checkups screenings vaccines immunizations early detection",
                "last_updated": datetime.now().isoformat()
            },
            {
                "topic_id": "ht_007",
                "title": "Weight Management",
                "category": "Weight",
                "url": "https://www.cdc.gov/healthyweight/losing_weight/index.html",
                "last_reviewed": "2024-01-01",
                "audience": ["adults", "teens"],
                "sections": [
                    {"title": "Overview", "content": "Maintaining a healthy weight is important for overall health and can help prevent many health problems.", "type": "content"},
                    {"title": "Healthy Weight", "content": "BMI between 18.5 and 24.9 is considered normal weight. Talk to your doctor about what's right for you.", "type": "guidelines"},
                    {"title": "Tips", "content": "Focus on healthy eating and regular physical activity rather than quick fixes. Make gradual, sustainable changes.", "type": "tips"}
                ],
                "related_topics": ["Healthy Eating", "Physical Activity", "Diabetes Prevention"],
                "summary": "Learn about maintaining a healthy weight through balanced eating and regular physical activity.",
                "keywords": ["weight management", "healthy weight", "BMI", "obesity", "weight loss", "diet"],
                "content_length": 350,
                "source": "curated",
                "search_text": "weight management healthy weight BMI obesity weight loss diet",
                "last_updated": datetime.now().isoformat()
            },
            {
                "topic_id": "ht_008",
                "title": "Diabetes Prevention",
                "category": "Diabetes",
                "url": "https://www.cdc.gov/diabetes/prevention/index.html",
                "last_reviewed": "2024-01-01",
                "audience": ["adults", "seniors"],
                "sections": [
                    {"title": "Overview", "content": "Type 2 diabetes can often be prevented through healthy lifestyle choices.", "type": "content"},
                    {"title": "Risk Factors", "content": "Being overweight, physically inactive, having prediabetes, family history, or being over 45 increases risk.", "type": "risk_factors"},
                    {"title": "Prevention", "content": "Lose weight if overweight, be physically active, eat healthy foods, and get regular checkups.", "type": "prevention"}
                ],
                "related_topics": ["Weight Management", "Physical Activity", "Healthy Eating", "Blood Sugar"],
                "summary": "Understanding diabetes risk factors and how to prevent type 2 diabetes through lifestyle changes.",
                "keywords": ["diabetes prevention", "prediabetes", "blood sugar", "insulin resistance", "type 2 diabetes"],
                "content_length": 370,
                "source": "curated",
                "search_text": "diabetes prevention prediabetes blood sugar insulin resistance type 2 diabetes",
                "last_updated": datetime.now().isoformat()
            },
            {
                "topic_id": "ht_009",
                "title": "Cancer Prevention",
                "category": "Cancer",
                "url": "https://www.cancer.gov/about-cancer/causes-prevention",
                "last_reviewed": "2024-01-01",
                "audience": ["adults", "seniors"],
                "sections": [
                    {"title": "Overview", "content": "Many cancers can be prevented through healthy lifestyle choices and regular screening.", "type": "content"},
                    {"title": "Prevention", "content": "Don't smoke, limit alcohol, maintain healthy weight, protect skin from sun, get vaccinated, get regular screenings.", "type": "prevention"},
                    {"title": "Screenings", "content": "Regular screenings for breast, cervical, colorectal, and lung cancer can detect cancer early when treatment is most effective.", "type": "screenings"}
                ],
                "related_topics": ["Preventive Care", "Healthy Eating", "Physical Activity", "Tobacco Cessation"],
                "summary": "Learn about cancer prevention strategies and the importance of regular cancer screenings.",
                "keywords": ["cancer prevention", "cancer screening", "mammography", "colonoscopy", "skin cancer"],
                "content_length": 400,
                "source": "curated",
                "search_text": "cancer prevention cancer screening mammography colonoscopy skin cancer",
                "last_updated": datetime.now().isoformat()
            },
            {
                "topic_id": "ht_010",
                "title": "Tobacco Cessation",
                "category": "Smoking",
                "url": "https://www.cdc.gov/tobacco/quit_smoking/index.htm",
                "last_reviewed": "2024-01-01",
                "audience": ["adults", "teens"],
                "sections": [
                    {"title": "Overview", "content": "Quitting tobacco is one of the most important things you can do for your health.", "type": "content"},
                    {"title": "Benefits", "content": "Quitting improves health immediately and reduces risk of heart disease, stroke, lung disease, and cancer.", "type": "benefits"},
                    {"title": "Resources", "content": "Call 1-800-QUIT-NOW, use quitlines, try nicotine replacement therapy, talk to your doctor, get support from family and friends.", "type": "resources"}
                ],
                "related_topics": ["Heart Health", "Cancer Prevention", "Lung Health"],
                "summary": "Information and resources for quitting smoking and tobacco use for better health.",
                "keywords": ["quit smoking", "tobacco cessation", "nicotine replacement", "quitline", "smoking cessation"],
                "content_length": 360,
                "source": "curated",
                "search_text": "quit smoking tobacco cessation nicotine replacement quitline smoking cessation",
                "last_updated": datetime.now().isoformat()
            }
        ]
    
    def _get_fallback_exercises(self) -> List[Dict]:
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
                "last_updated": datetime.now().isoformat()
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
                "last_updated": datetime.now().isoformat()
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
                "last_updated": datetime.now().isoformat()
            }
        ]
    
    def _get_fallback_food_items(self) -> List[Dict]:
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
                "last_updated": datetime.now().isoformat()
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
                "last_updated": datetime.now().isoformat()
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
                "last_updated": datetime.now().isoformat()
            }
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