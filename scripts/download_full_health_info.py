#!/usr/bin/env python3
"""
Complete Health Information Archive Downloader
Downloads complete health information datasets for offline database operation

Uses the same configuration and patterns as the medical-mirrors service
for consistency with the existing database schema and architecture.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import aiohttp
from aiohttp import ClientError

# Type checking imports
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from medical_mirrors_types import Config, HealthInfoDownloader
else:
    # Runtime imports - add medical-mirrors to Python path
    medical_mirrors_src = str(Path(__file__).parent.parent / "services/user/medical-mirrors/src")
    if medical_mirrors_src not in sys.path:
        sys.path.insert(0, medical_mirrors_src)

    try:
        from config import Config
        from health_info.downloader import HealthInfoDownloader
    except ImportError as e:
        print(f"Failed to import medical-mirrors modules: {e}")
        print(f"Make sure medical-mirrors service is properly installed")
        print(f"Looking for modules in: {medical_mirrors_src}")
        sys.exit(1)

class CompleteHealthInfoDownloader:
    """
    Downloads complete health information datasets for local database caching.
    
    Based on the existing medical-mirrors HealthInfoDownloader but enhanced
    for systematic complete downloads with database schema compatibility.
    """

    def __init__(self, custom_data_dir: str | None = None):
        # Use medical-mirrors Config for consistency
        self.config = Config()
        
        # Allow custom data directory override
        if custom_data_dir:
            self.data_dir = custom_data_dir
            os.makedirs(self.data_dir, exist_ok=True)
        else:
            self.data_dir = self.config.get_health_info_data_dir()
            
        self.logger = self._setup_logging()
        
        # Use the existing HealthInfoDownloader as base
        self.base_downloader = HealthInfoDownloader(self.config)
        
        # Download statistics
        self.stats: Dict[str, Any] = {
            "health_topics_downloaded": 0,
            "exercises_downloaded": 0,
            "food_items_downloaded": 0,
            "total_items_downloaded": 0,
            "api_calls_made": 0,
            "start_time": None,
            "end_time": None,
            "errors": []
        }

    def _setup_logging(self) -> logging.Logger:
        """Setup comprehensive download logging"""
        logger = logging.getLogger("complete_health_info_downloader")
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    async def download_complete_archive(self) -> dict[str, Any]:
        """Download complete health information datasets"""
        self.logger.info("Starting complete health information datasets download")
        self.logger.info("Target: MyHealthfinder topics + ExerciseDB + USDA FoodData")
        self.stats["start_time"] = time.time()

        try:
            async with self.base_downloader:
                # Download all health data using the existing comprehensive method
                all_data = await self.base_downloader.download_all_health_data()
                
                # Validate and normalize data for medical-mirrors schema compatibility
                validated_data = await self._validate_and_normalize_data(all_data)
                
                # Save complete datasets
                complete_files = await self.save_complete_datasets(validated_data)
                
                # Get download stats from base downloader
                base_stats = self.base_downloader.get_download_stats()
                self.stats.update({
                    "health_topics_downloaded": base_stats.get("health_topics_downloaded", 0),
                    "exercises_downloaded": base_stats.get("exercises_downloaded", 0),
                    "food_items_downloaded": base_stats.get("food_items_downloaded", 0),
                    "total_items_downloaded": base_stats.get("total_items_downloaded", 0),
                    "api_calls_made": base_stats.get("requests_made", 0),
                })
                
                # Handle errors list separately
                existing_errors = self.stats.get("errors", [])
                new_errors = [str(e) for e in base_stats.get("errors", [])]
                if isinstance(existing_errors, list) and isinstance(new_errors, list):
                    self.stats["errors"] = existing_errors + new_errors
                
                self.stats["end_time"] = time.time()
                start_time = self.stats.get("start_time", 0)
                end_time = self.stats.get("end_time", 0)
                duration = float(end_time) - float(start_time or 0)
                
                total_items = sum([
                    len(validated_data["health_topics"]),
                    len(validated_data["exercises"]),
                    len(validated_data["food_items"])
                ])
                
                self.logger.info(f"✅ Complete health information download finished!")
                self.logger.info(f"   Health topics: {len(validated_data['health_topics'])}")
                self.logger.info(f"   Exercises: {len(validated_data['exercises'])}")
                self.logger.info(f"   Food items: {len(validated_data['food_items'])}")
                self.logger.info(f"   Total items: {total_items}")
                self.logger.info(f"   API calls made: {self.stats['api_calls_made']}")
                self.logger.info(f"   Duration: {duration/60:.1f} minutes")
                self.logger.info(f"   Complete files: {len(complete_files)} datasets")
                
                return {
                    "status": "success",
                    "health_topics": len(validated_data["health_topics"]),
                    "exercises": len(validated_data["exercises"]),
                    "food_items": len(validated_data["food_items"]),
                    "total_items": total_items,
                    "api_calls": self.stats["api_calls_made"],
                    "duration_minutes": duration / 60,
                    "complete_files": complete_files,
                    "errors": self.stats["errors"]
                }

        except Exception as e:
            self.logger.exception(f"Complete health information download failed: {e}")
            if isinstance(self.stats["errors"], list):
                self.stats["errors"].append(str(e))
            return {
                "status": "failed",
                "error": str(e),
                "partial_stats": self.stats
            }

    async def _validate_and_normalize_data(self, all_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Validate and normalize health data for medical-mirrors schema compatibility.
        
        Maps API responses to database column constraints from migration 002 + 004:
        
        Health Topics (health_topics table):
        - topic_id: VARCHAR(100) PRIMARY KEY (extended from 50 in migration 004)
        - title: TEXT NOT NULL
        - category: VARCHAR(300) (extended from 200 in migration 004)
        - url: TEXT
        - last_reviewed: VARCHAR(100) (extended from 50 in migration 004)
        - audience: JSONB
        - sections: JSONB
        - related_topics: JSONB
        - summary: TEXT
        - keywords: JSONB
        - content_length: INTEGER DEFAULT 0
        - source: VARCHAR(100) (extended from 50 in migration 004)
        - search_text: TEXT
        
        Exercises (exercises table):
        - exercise_id: VARCHAR(100) PRIMARY KEY (extended from 50 in migration 004)
        - name: TEXT NOT NULL
        - body_part: VARCHAR(200) (extended from 100 in migration 004)
        - equipment: VARCHAR(200) (extended from 100 in migration 004)
        - target: VARCHAR(200) (extended from 100 in migration 004)
        - secondary_muscles: JSONB
        - instructions: JSONB
        - gif_url: TEXT
        - difficulty_level: VARCHAR(100) (extended from 50 in migration 004)
        - exercise_type: VARCHAR(100) (extended from 50 in migration 004)
        - duration_estimate: VARCHAR(200) (extended from 100 in migration 004)
        - calories_estimate: VARCHAR(200) (extended from 100 in migration 004)
        - source: VARCHAR(100) (extended from 50 in migration 004)
        - search_text: TEXT
        
        Food Items (food_items table):
        - fdc_id: INTEGER PRIMARY KEY
        - description: TEXT NOT NULL
        - scientific_name: TEXT
        - common_names: TEXT
        - food_category: VARCHAR(300) (extended from 200 in migration 004)
        - nutrients: JSONB
        - nutrition_summary: JSONB
        - brand_owner: VARCHAR(300) (extended from 200 in migration 004)
        - ingredients: TEXT
        - serving_size: NUMERIC
        - serving_size_unit: VARCHAR(100) (extended from 50 in migration 004)
        - allergens: JSONB
        - dietary_flags: JSONB
        - nutritional_density: NUMERIC DEFAULT 0
        - source: VARCHAR(100) (extended from 50 in migration 004)
        - search_text: TEXT
        """
        
        validated_data: Dict[str, List[Dict[str, Any]]] = {
            "health_topics": [],
            "exercises": [],
            "food_items": []
        }
        
        # Validate health topics
        self.logger.info(f"Validating {len(all_data.get('health_topics', []))} health topics")
        for topic_data in all_data.get("health_topics", []):
            try:
                topic_id = str(topic_data.get("topic_id", ""))[:100]  # VARCHAR(100) constraint
                if not topic_id:
                    self.logger.warning("Skipping health topic with empty topic_id")
                    continue
                
                title = str(topic_data.get("title", "")).strip()
                if not title:
                    self.logger.warning(f"Skipping health topic {topic_id} with empty title")
                    continue
                
                # Apply column constraints
                category = str(topic_data.get("category", ""))[:300]  # VARCHAR(300)
                last_reviewed = str(topic_data.get("last_reviewed", ""))[:100]  # VARCHAR(100)
                source = str(topic_data.get("source", "myhealthfinder"))[:100]  # VARCHAR(100)
                
                # Handle JSONB fields
                audience = topic_data.get("audience", [])
                if not isinstance(audience, list):
                    audience = [str(audience)] if audience else []
                
                sections = topic_data.get("sections", [])
                if not isinstance(sections, list):
                    sections = []
                
                related_topics = topic_data.get("related_topics", [])
                if not isinstance(related_topics, list):
                    related_topics = []
                
                # Calculate content length
                search_text = self._create_health_topic_search_text(topic_data)
                content_length = len(search_text)
                
                normalized_topic = {
                    "topic_id": topic_id,
                    "title": title,
                    "category": category,
                    "url": str(topic_data.get("url", "")),
                    "last_reviewed": last_reviewed,
                    "audience": audience,
                    "sections": sections,
                    "related_topics": related_topics,
                    "summary": str(topic_data.get("summary", "")),
                    "keywords": [],  # Could be enhanced with keyword extraction
                    "content_length": content_length,
                    "source": source,
                    "search_text": search_text,
                    "last_updated": topic_data.get("last_updated"),
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                
                validated_data["health_topics"].append(normalized_topic)
                
            except Exception as e:
                self.logger.warning(f"Failed to validate health topic {topic_data.get('topic_id', 'unknown')}: {e}")
                continue
        
        # Validate exercises
        self.logger.info(f"Validating {len(all_data.get('exercises', []))} exercises")
        for exercise_data in all_data.get("exercises", []):
            try:
                exercise_id = str(exercise_data.get("exercise_id", ""))[:100]  # VARCHAR(100) constraint
                if not exercise_id:
                    self.logger.warning("Skipping exercise with empty exercise_id")
                    continue
                
                name = str(exercise_data.get("name", "")).strip()
                if not name:
                    self.logger.warning(f"Skipping exercise {exercise_id} with empty name")
                    continue
                
                # Apply column constraints
                body_part = str(exercise_data.get("body_part", ""))[:200]  # VARCHAR(200)
                equipment = str(exercise_data.get("equipment", ""))[:200]  # VARCHAR(200)
                target = str(exercise_data.get("target", ""))[:200]  # VARCHAR(200)
                difficulty_level = str(exercise_data.get("difficulty_level", ""))[:100]  # VARCHAR(100)
                exercise_type = str(exercise_data.get("exercise_type", ""))[:100]  # VARCHAR(100)
                duration_estimate = str(exercise_data.get("duration_estimate", ""))[:200]  # VARCHAR(200)
                calories_estimate = str(exercise_data.get("calories_estimate", ""))[:200]  # VARCHAR(200)
                source = str(exercise_data.get("source", "exercisedb"))[:100]  # VARCHAR(100)
                
                # Handle JSONB fields
                secondary_muscles = exercise_data.get("secondary_muscles", [])
                if not isinstance(secondary_muscles, list):
                    secondary_muscles = []
                
                instructions = exercise_data.get("instructions", [])
                if not isinstance(instructions, list):
                    instructions = [str(instructions)] if instructions else []
                
                search_text = self._create_exercise_search_text(exercise_data)
                
                normalized_exercise = {
                    "exercise_id": exercise_id,
                    "name": name,
                    "body_part": body_part,
                    "equipment": equipment,
                    "target": target,
                    "secondary_muscles": secondary_muscles,
                    "instructions": instructions,
                    "gif_url": str(exercise_data.get("gif_url", "")),
                    "difficulty_level": difficulty_level,
                    "exercise_type": exercise_type,
                    "duration_estimate": duration_estimate,
                    "calories_estimate": calories_estimate,
                    "source": source,
                    "search_text": search_text,
                    "last_updated": exercise_data.get("last_updated"),
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                
                validated_data["exercises"].append(normalized_exercise)
                
            except Exception as e:
                self.logger.warning(f"Failed to validate exercise {exercise_data.get('exercise_id', 'unknown')}: {e}")
                continue
        
        # Validate food items
        self.logger.info(f"Validating {len(all_data.get('food_items', []))} food items")
        for food_data in all_data.get("food_items", []):
            try:
                fdc_id = food_data.get("fdc_id")
                if not fdc_id:
                    self.logger.warning("Skipping food item with empty fdc_id")
                    continue
                
                try:
                    fdc_id = int(fdc_id)
                except (ValueError, TypeError):
                    self.logger.warning(f"Skipping food item with invalid fdc_id: {fdc_id}")
                    continue
                
                description = str(food_data.get("description", "")).strip()
                if not description:
                    self.logger.warning(f"Skipping food item {fdc_id} with empty description")
                    continue
                
                # Apply column constraints
                food_category = str(food_data.get("food_category", ""))[:300]  # VARCHAR(300)
                brand_owner = str(food_data.get("brand_owner", ""))[:300]  # VARCHAR(300)
                serving_size_unit = str(food_data.get("serving_size_unit", ""))[:100]  # VARCHAR(100)
                source = str(food_data.get("source", "usda_fooddata"))[:100]  # VARCHAR(100)
                
                # Handle numeric fields
                serving_size = food_data.get("serving_size")
                if serving_size is not None:
                    try:
                        serving_size = float(serving_size)
                    except (ValueError, TypeError):
                        serving_size = None
                
                # Handle JSONB fields
                nutrients = food_data.get("nutrients", [])
                if not isinstance(nutrients, list):
                    nutrients = []
                
                allergens = food_data.get("allergens", [])
                if not isinstance(allergens, list):
                    allergens = []
                
                dietary_flags = food_data.get("dietary_flags", [])
                if not isinstance(dietary_flags, list):
                    dietary_flags = []
                
                search_text = self._create_food_search_text(food_data)
                
                normalized_food = {
                    "fdc_id": fdc_id,
                    "description": description,
                    "scientific_name": str(food_data.get("scientific_name", "")),
                    "common_names": str(food_data.get("common_names", "")),
                    "food_category": food_category,
                    "nutrients": nutrients,
                    "nutrition_summary": {},  # Could be computed from nutrients
                    "brand_owner": brand_owner,
                    "ingredients": str(food_data.get("ingredients", "")),
                    "serving_size": serving_size,
                    "serving_size_unit": serving_size_unit,
                    "allergens": allergens,
                    "dietary_flags": dietary_flags,
                    "nutritional_density": 0,  # Could be computed from nutrients
                    "source": source,
                    "search_text": search_text,
                    "last_updated": food_data.get("last_updated"),
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                
                validated_data["food_items"].append(normalized_food)
                
            except Exception as e:
                self.logger.warning(f"Failed to validate food item {food_data.get('fdc_id', 'unknown')}: {e}")
                continue
        
        total_validated = sum([
            len(validated_data["health_topics"]),
            len(validated_data["exercises"]),
            len(validated_data["food_items"])
        ])
        self.logger.info(f"Validated {total_validated} total health information items for database insertion")
        
        return validated_data

    def _create_health_topic_search_text(self, topic_data: dict) -> str:
        """Create comprehensive search text for health topics"""
        search_parts = [
            str(topic_data.get("title", "")),
            str(topic_data.get("category", "")),
            str(topic_data.get("summary", "")),
        ]
        
        # Add sections content if available
        sections = topic_data.get("sections", [])
        if isinstance(sections, list):
            for section in sections:
                if isinstance(section, dict):
                    search_parts.extend([
                        str(section.get("title", "")),
                        str(section.get("content", ""))
                    ])
        
        return " ".join(search_parts).lower()

    def _create_exercise_search_text(self, exercise_data: dict) -> str:
        """Create comprehensive search text for exercises"""
        search_parts = [
            str(exercise_data.get("name", "")),
            str(exercise_data.get("body_part", "")),
            str(exercise_data.get("equipment", "")),
            str(exercise_data.get("target", "")),
            str(exercise_data.get("difficulty_level", "")),
            str(exercise_data.get("exercise_type", ""))
        ]
        
        # Add instructions if available
        instructions = exercise_data.get("instructions", [])
        if isinstance(instructions, list):
            search_parts.extend([str(inst) for inst in instructions])
        
        return " ".join(search_parts).lower()

    def _create_food_search_text(self, food_data: dict) -> str:
        """Create comprehensive search text for food items"""
        search_parts = [
            str(food_data.get("description", "")),
            str(food_data.get("common_names", "")),
            str(food_data.get("food_category", "")),
            str(food_data.get("brand_owner", "")),
            str(food_data.get("scientific_name", ""))
        ]
        
        return " ".join(search_parts).lower()

    async def save_complete_datasets(self, validated_data: Dict[str, List[Dict]]) -> List[str]:
        """Save complete health information datasets to JSON files for processing"""
        complete_files = []
        
        # Save each dataset separately for easier processing
        for dataset_name, data in validated_data.items():
            if not data:
                continue
                
            output_file = os.path.join(self.data_dir, f"all_{dataset_name}_complete.json")
            
            # Prepare metadata specific to each dataset
            dataset_info: Dict[str, Any] = {
                "metadata": {
                    "dataset_type": dataset_name,
                    "total_items": len(data),
                    "download_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "api_calls_made": self.stats["api_calls_made"],
                    "schema_version": "medical_mirrors_compatible"
                },
                dataset_name: data
            }
            
            # Add dataset-specific metadata
            if dataset_name == "health_topics":
                categories = list(set(item.get("category", "") for item in data if item.get("category")))
                dataset_info["metadata"]["categories"] = categories
                dataset_info["metadata"]["sources"] = list(set(item.get("source", "") for item in data))
            elif dataset_name == "exercises":
                body_parts = list(set(item.get("body_part", "") for item in data if item.get("body_part")))
                equipment_types = list(set(item.get("equipment", "") for item in data if item.get("equipment")))
                dataset_info["metadata"]["body_parts"] = body_parts
                dataset_info["metadata"]["equipment_types"] = equipment_types
            elif dataset_name == "food_items":
                food_categories = list(set(item.get("food_category", "") for item in data if item.get("food_category")))
                dataset_info["metadata"]["food_categories"] = food_categories
                dataset_info["metadata"]["with_nutrition"] = len([item for item in data if item.get("nutrients")])
            
            # Save with proper formatting
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(dataset_info, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"Saved {dataset_name} dataset: {output_file} ({len(data)} items)")
            complete_files.append(output_file)
        
        return complete_files

    def get_download_stats(self) -> dict[str, Any]:
        """Get comprehensive download statistics"""
        stats = self.stats.copy()
        
        start_time = stats.get("start_time")
        end_time = stats.get("end_time")
        if start_time and end_time:
            duration = float(end_time) - float(start_time)
            stats["duration_seconds"] = duration
            stats["duration_minutes"] = duration / 60
            
            if duration > 0:
                total_items = stats.get("total_items_downloaded", 0)
                api_calls = stats.get("api_calls_made", 0)
                if isinstance(total_items, (int, float)) and isinstance(api_calls, (int, float)):
                    stats["items_per_second"] = float(total_items) / duration
                    stats["api_calls_per_minute"] = float(api_calls) / (duration / 60)
        
        return stats


def main():
    """Main function for complete health information download"""
    parser = argparse.ArgumentParser(
        description="Download complete health information datasets for offline operation",
        epilog="Uses medical-mirrors configuration for database compatibility"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        help="Directory to store complete health info data (default: medical-mirrors config)"
    )
    parser.add_argument(
        "--topics-only",
        action="store_true",
        help="Download only health topics (MyHealthfinder)"
    )
    parser.add_argument(
        "--exercises-only",
        action="store_true",
        help="Download only exercises (ExerciseDB - requires RAPIDAPI_KEY)"
    )
    parser.add_argument(
        "--nutrition-only",
        action="store_true",
        help="Download only nutrition data (USDA - requires USDA_API_KEY)"
    )

    args = parser.parse_args()

    # Create downloader with optional custom data directory
    downloader = CompleteHealthInfoDownloader(custom_data_dir=args.data_dir)

    print(f"\n📋 Starting complete health information download to: {downloader.data_dir}")
    print("⚠️  Target: MyHealthfinder topics + ExerciseDB + USDA FoodData")
    print("🔧 Using medical-mirrors config for database compatibility")
    
    # Show API key requirements
    rapidapi_key = os.getenv("RAPIDAPI_KEY")
    usda_api_key = os.getenv("USDA_API_KEY")
    
    if args.exercises_only and not rapidapi_key:
        print("❌ RAPIDAPI_KEY required for ExerciseDB")
        return
    elif args.nutrition_only and not usda_api_key:
        print("❌ USDA_API_KEY required for USDA FoodData")
        return
    else:
        print(f"🔑 ExerciseDB: {'✅' if rapidapi_key else '❌ (skip)'}")
        print(f"🔑 USDA FoodData: {'✅' if usda_api_key else '❌ (skip)'}")
        print()

    # Run download
    result = asyncio.run(downloader.download_complete_archive())

    # Show results
    if isinstance(result, dict) and result.get("status") == "success":
        print("\n✅ Health information download completed successfully!")
        print(f"   Health topics: {result.get('health_topics', 0)}")
        print(f"   Exercises: {result.get('exercises', 0)}")
        print(f"   Food items: {result.get('food_items', 0)}")
        print(f"   Total items: {result.get('total_items', 0)}")
        print(f"   Duration: {result.get('duration_minutes', 0):.1f} minutes")
        print(f"   Complete files: {len(result.get('complete_files', []))}")
    else:
        print("\n❌ Health information download failed or incomplete")
        if isinstance(result, dict) and "error" in result:
            print(f"   Error: {result['error']}")

    # Show download statistics
    stats = downloader.get_download_stats()
    print(f"\n📊 Download Statistics:")
    print(f"   API calls made: {stats.get('api_calls_made', 0)}")
    print(f"   Average speed: {stats.get('items_per_second', 0):.1f} items/sec")
    print(f"   Errors: {len(stats.get('errors', []))}")
    
    # Show next steps
    print(f"\n📋 Next Steps:")
    print(f"   1. Parse downloaded files: python scripts/parse_downloaded_archives.py health-info")
    print(f"   2. Or use medical-mirrors API: POST /update/health-info")
    print(f"   3. Files stored in: {downloader.data_dir}")
    
    # Show API key reminders
    if not rapidapi_key:
        print(f"\n💡 Note: Set RAPIDAPI_KEY to download ExerciseDB data")
    if not usda_api_key:
        print(f"💡 Note: Set USDA_API_KEY to download USDA nutrition data")


if __name__ == "__main__":
    main()