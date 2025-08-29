#!/usr/bin/env python3
"""
Monitor ExerciseDB API rate limits and automatically collect exercises when available
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path

import aiohttp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def check_api_status():
    """Check if ExerciseDB API is accessible"""
    rapidapi_key = os.getenv("RAPIDAPI_KEY")
    if not rapidapi_key:
        logger.error("RAPIDAPI_KEY not found")
        return False

    headers = {
        "X-RapidAPI-Key": rapidapi_key,
        "X-RapidAPI-Host": "exercisedb.p.rapidapi.com",
    }

    async with aiohttp.ClientSession() as session:
        try:
            # Try a simple endpoint
            url = "https://exercisedb.p.rapidapi.com/exercises/bodyPartList"
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    logger.info("✅ API is available")
                    return True
                if response.status == 429:
                    logger.info("⏳ API still rate limited (429)")
                    return False
                logger.warning(f"❓ API returned status {response.status}")
                return False
        except Exception as e:
            logger.warning(f"❓ API check failed: {e}")
            return False


async def collect_single_category(session, headers, category_type, category_name):
    """Collect exercises from a single category"""
    try:
        url = f"https://exercisedb.p.rapidapi.com/exercises/{category_type}/{category_name.replace(' ', '%20')}"

        async with session.get(url, headers=headers, timeout=15) as response:
            if response.status == 200:
                exercises = await response.json()
                logger.info(f"✅ {category_type}/{category_name}: {len(exercises)} exercises")
                return exercises
            if response.status == 429:
                logger.warning(f"⏳ Rate limited on {category_type}/{category_name}")
                return None
            logger.warning(f"❓ {category_type}/{category_name}: HTTP {response.status}")
            return None

    except Exception as e:
        logger.warning(f"❓ Error with {category_type}/{category_name}: {e}")
        return None


async def systematic_collection():
    """Systematically collect exercises from all categories"""
    rapidapi_key = os.getenv("RAPIDAPI_KEY")
    if not rapidapi_key:
        logger.error("RAPIDAPI_KEY not found")
        return []

    headers = {
        "X-RapidAPI-Key": rapidapi_key,
        "X-RapidAPI-Host": "exercisedb.p.rapidapi.com",
    }

    # Categories to try (start with most likely to work)
    categories = [
        # Body parts
        ("bodyPart", "back"),
        ("bodyPart", "chest"),
        ("bodyPart", "shoulders"),
        ("bodyPart", "upper arms"),
        ("bodyPart", "lower arms"),
        ("bodyPart", "upper legs"),
        ("bodyPart", "lower legs"),
        ("bodyPart", "waist"),
        ("bodyPart", "cardio"),
        ("bodyPart", "neck"),

        # Equipment types
        ("equipment", "barbell"),
        ("equipment", "dumbbell"),
        ("equipment", "body weight"),
        ("equipment", "cable"),
        ("equipment", "kettlebell"),
        ("equipment", "resistance band"),
        ("equipment", "machine"),
        ("equipment", "stability ball"),
        ("equipment", "medicine ball"),
        ("equipment", "rope"),

        # Target muscles
        ("target", "pectorals"),
        ("target", "lats"),
        ("target", "delts"),
        ("target", "biceps"),
        ("target", "triceps"),
        ("target", "quads"),
        ("target", "hamstrings"),
        ("target", "glutes"),
        ("target", "calves"),
        ("target", "abs"),
        ("target", "abductors"),
    ]

    all_exercises = []
    seen_ids = set()
    successful_categories = 0
    failed_categories = 0

    async with aiohttp.ClientSession() as session:
        for i, (category_type, category_name) in enumerate(categories):
            logger.info(f"📥 Collecting {category_type}/{category_name} ({i+1}/{len(categories)})")

            exercises = await collect_single_category(session, headers, category_type, category_name)

            if exercises:
                successful_categories += 1
                new_count = 0
                for exercise in exercises:
                    exercise_id = exercise.get("id", "")
                    if exercise_id and exercise_id not in seen_ids:
                        seen_ids.add(exercise_id)
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
                        new_count += 1

                logger.info(f"   Added {new_count} new exercises (total unique: {len(all_exercises)})")
            else:
                failed_categories += 1
                # If we hit rate limits, wait a bit before continuing
                if failed_categories >= 3:
                    logger.info("⏳ Multiple failures detected, waiting 30s...")
                    await asyncio.sleep(30)
                    failed_categories = 0

            # Rate limiting between requests
            await asyncio.sleep(2)

    logger.info("🎉 Collection complete!")
    logger.info(f"   Successful categories: {successful_categories}")
    logger.info(f"   Failed categories: {len(categories) - successful_categories}")
    logger.info(f"   Total unique exercises: {len(all_exercises)}")

    return all_exercises


async def main():
    """Main monitoring and collection loop"""
    logger.info("🚀 Starting ExerciseDB monitoring and collection...")

    while True:
        logger.info(f"⏰ Checking API status at {datetime.now().strftime('%H:%M:%S')}")

        if await check_api_status():
            logger.info("🎯 API is available! Starting systematic collection...")
            exercises = await systematic_collection()

            if exercises and len(exercises) > 10:  # Only save if we got meaningful data
                output_dir = Path("/home/intelluxe/database/medical_complete/health_info")
                output_dir.mkdir(parents=True, exist_ok=True)

                output_file = output_dir / "exercises_comprehensive.json"
                with open(output_file, "w") as f:
                    json.dump(exercises, f, default=str)

                logger.info(f"💾 Saved {len(exercises)} exercises to {output_file}")

                # Show variety stats
                body_parts = set()
                equipment_types = set()
                targets = set()
                for ex in exercises:
                    body_parts.add(ex.get("body_part"))
                    equipment_types.add(ex.get("equipment"))
                    targets.add(ex.get("target"))

                logger.info("📊 Exercise variety:")
                logger.info(f"   Body parts: {len(body_parts)}")
                logger.info(f"   Equipment types: {len(equipment_types)}")
                logger.info(f"   Target muscles: {len(targets)}")

                # Success! Break out of monitoring loop
                break
            logger.warning("⚠️ Collected data insufficient, continuing monitoring...")

        logger.info("😴 Waiting 5 minutes before next check...")
        await asyncio.sleep(300)  # Wait 5 minutes


if __name__ == "__main__":
    asyncio.run(main())
