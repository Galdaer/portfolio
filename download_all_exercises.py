#!/usr/bin/env python3
"""
Download ALL exercises from ExerciseDB using the /exercises endpoint
This bypasses the category-based approach and gets the complete database
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
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def download_all_exercises():
    """Download ALL exercises from ExerciseDB using the /exercises endpoint"""
    
    rapidapi_key = os.getenv("RAPIDAPI_KEY")
    if not rapidapi_key:
        logger.error("RAPIDAPI_KEY not found in environment variables")
        return
    
    headers = {
        "X-RapidAPI-Key": rapidapi_key,
        "X-RapidAPI-Host": "exercisedb.p.rapidapi.com",
    }
    
    output_dir = Path("/home/intelluxe/database/medical_complete/health_info")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    async with aiohttp.ClientSession() as session:
        try:
            # Try the main /exercises endpoint first
            url = "https://exercisedb.p.rapidapi.com/exercises"
            logger.info(f"Fetching ALL exercises from {url}")
            
            async with session.get(url, headers=headers, timeout=60) as response:
                if response.status == 200:
                    exercises = await response.json()
                    logger.info(f"✅ Downloaded {len(exercises)} exercises from /exercises endpoint")
                    
                    # The /exercises endpoint might be limited to 10 results by default
                    # If we get exactly 10, we should try the offset method instead
                    if len(exercises) == 10:
                        logger.info("Got exactly 10 exercises - API likely has default limit, trying offset method...")
                        # Don't save yet, try offset method below
                    else:
                        # Convert to our format and save
                        processed_exercises = []
                        for exercise in exercises:
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
                                "search_text": f"{exercise.get('name', '')} {exercise.get('bodyPart', '')} {exercise.get('target', '')}".lower(),
                            }
                            processed_exercises.append(exercise_data)
                        
                        # Save to file
                        output_file = output_dir / "exercises_complete_all.json"
                        with open(output_file, "w") as f:
                            json.dump(processed_exercises, f, default=str)
                        
                        logger.info(f"✅ Saved {len(processed_exercises)} exercises to {output_file}")
                        return processed_exercises
                    
                else:
                    logger.error(f"Failed to fetch exercises: HTTP {response.status}")
                    
        except Exception as e:
            logger.error(f"Error downloading exercises: {e}")
            
        # Fallback: try with offset/limit parameters but with much smaller batch size and delays
        try:
            logger.info("Trying /exercises with offset parameter and careful rate limiting...")
            offset = 0
            limit = 20  # Much smaller batches to avoid rate limits
            all_exercises = []
            
            while offset < 1500:  # Try up to 1500 exercises
                url = f"https://exercisedb.p.rapidapi.com/exercises?offset={offset}&limit={limit}"
                logger.info(f"Fetching exercises {offset}-{offset+limit-1}")
                
                try:
                    async with session.get(url, headers=headers, timeout=30) as response:
                        if response.status == 200:
                            exercises = await response.json()
                            if not exercises:
                                logger.info("No more exercises returned, stopping")
                                break
                                
                            all_exercises.extend(exercises)
                            logger.info(f"Got {len(exercises)} exercises (total: {len(all_exercises)})")
                            
                            if len(exercises) < limit:
                                logger.info("Last batch received, stopping")
                                break  # Last batch
                                
                        elif response.status == 429:
                            logger.warning(f"Rate limited at offset {offset}, waiting 30 seconds...")
                            await asyncio.sleep(30)
                            continue  # Retry same offset
                        else:
                            logger.error(f"Failed at offset {offset}: HTTP {response.status}")
                            break
                    
                    offset += limit
                    await asyncio.sleep(3)  # Longer delay between requests
                    
                except Exception as e:
                    logger.error(f"Error at offset {offset}: {e}")
                    await asyncio.sleep(10)
                    offset += limit  # Skip this batch
            
            if all_exercises:
                # Convert to our format
                processed_exercises = []
                for exercise in all_exercises:
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
                        "search_text": f"{exercise.get('name', '')} {exercise.get('bodyPart', '')} {exercise.get('target', '')}".lower(),
                    }
                    processed_exercises.append(exercise_data)
                
                # Save to file
                output_file = output_dir / "exercises_complete_all.json"
                with open(output_file, "w") as f:
                    json.dump(processed_exercises, f, default=str)
                
                logger.info(f"✅ Saved {len(processed_exercises)} exercises to {output_file} (using offset method)")
                return processed_exercises
        
        except Exception as e:
            logger.error(f"Error with offset method: {e}")
    
    return []


async def main():
    """Main function"""
    logger.info("Starting comprehensive ExerciseDB download...")
    exercises = await download_all_exercises()
    
    if exercises:
        logger.info(f"🎉 Successfully downloaded {len(exercises)} exercises!")
        logger.info("Next step: Run insertion script to update database")
    else:
        logger.error("❌ Failed to download exercises")


if __name__ == "__main__":
    asyncio.run(main())