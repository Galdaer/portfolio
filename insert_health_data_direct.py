#!/usr/bin/env python3
"""
Direct insertion of health info data into database
"""

import json
import logging
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def insert_exercises(cur, exercises_data):
    """Insert exercises data directly"""
    logger.info(f"Processing {len(exercises_data)} exercises...")

    # Clear existing data
    cur.execute("DELETE FROM exercises")

    inserted = 0
    for exercise in exercises_data:
        try:
            cur.execute("""
                INSERT INTO exercises (
                    exercise_id, name, body_part, target, equipment,
                    gif_url, instructions, secondary_muscles, source
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (exercise_id) DO NOTHING
            """, (
                exercise.get("exercise_id"),
                exercise.get("name"),
                exercise.get("body_part"),
                exercise.get("target"),
                exercise.get("equipment"),
                exercise.get("gif_url", ""),
                json.dumps(exercise.get("instructions", [])),
                json.dumps(exercise.get("secondary_muscles", [])),
                exercise.get("source", "exercisedb"),
            ))
            inserted += 1
        except Exception as e:
            logger.exception(f"Error inserting exercise {exercise.get('exercise_id', 'unknown')}: {e}")

    logger.info(f"✅ Inserted {inserted} exercises")
    return inserted


def insert_food_items(cur, food_data):
    """Insert food items data directly"""
    logger.info(f"Processing {len(food_data)} food items...")

    # Clear existing data
    cur.execute("DELETE FROM food_items")

    inserted = 0
    for food in food_data:
        try:
            # Handle common_names as list or string
            common_names = food.get("common_names", [])
            if isinstance(common_names, list):
                common_names_str = ", ".join(common_names)
            else:
                common_names_str = str(common_names) if common_names else ""

            # Handle fdc_id - it might be a string like "fallback_food_1" but database expects integer
            fdc_id = food.get("fdc_id")
            if isinstance(fdc_id, str):
                if fdc_id.startswith("fallback_food_"):
                    # Convert fallback_food_X to integer
                    fdc_id = int(fdc_id.replace("fallback_food_", "")) + 1000000  # Use high numbers to avoid conflicts
                else:
                    try:
                        fdc_id = int(fdc_id)
                    except ValueError:
                        fdc_id = hash(fdc_id) % 2147483647  # Convert string to positive int within PostgreSQL int range

            cur.execute("""
                INSERT INTO food_items (
                    fdc_id, description, scientific_name, common_names, food_category,
                    nutrients, nutrition_summary, brand_owner, ingredients,
                    serving_size, serving_size_unit, allergens, dietary_flags,
                    nutritional_density, source
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (fdc_id) DO NOTHING
            """, (
                fdc_id,
                food.get("description"),
                food.get("scientific_name", ""),
                common_names_str,
                food.get("food_category"),
                json.dumps(food.get("nutrients", [])),
                json.dumps({"summary": food.get("nutrition_summary", "")}),
                food.get("brand_owner", ""),
                food.get("ingredients", ""),
                food.get("serving_size"),
                food.get("serving_size_unit", ""),
                json.dumps(food.get("allergens", "")),
                json.dumps(food.get("dietary_flags", [])),
                food.get("nutritional_density", 0),
                food.get("source", "downloaded"),
            ))
            inserted += 1
        except Exception as e:
            logger.exception(f"Error inserting food item {food.get('fdc_id', 'unknown')}: {e}")

    logger.info(f"✅ Inserted {inserted} food items")
    return inserted


def insert_health_topics(cur, topics_data):
    """Insert health topics data directly"""
    if not topics_data:
        logger.info("No health topics data to insert")
        return 0

    logger.info(f"Processing {len(topics_data)} health topics...")

    # Clear existing data
    cur.execute("DELETE FROM health_topics")

    inserted = 0
    for topic in topics_data:
        try:
            cur.execute("""
                INSERT INTO health_topics (
                    topic_id, title, category, content,
                    age_group, sex, description, keywords
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (topic_id) DO NOTHING
            """, (
                topic.get("topic_id"),
                topic.get("title"),
                topic.get("category"),
                topic.get("content", ""),
                topic.get("age_group", "all"),
                topic.get("sex", "all"),
                topic.get("description", ""),
                topic.get("keywords", []),
            ))
            inserted += 1
        except Exception as e:
            logger.exception(f"Error inserting health topic {topic.get('topic_id', 'unknown')}: {e}")

    logger.info(f"✅ Inserted {inserted} health topics")
    return inserted


def main():
    """Main processing function"""
    data_dir = Path("/home/intelluxe/database/medical_complete/health_info")

    # Database connection
    try:
        db_url = f"postgresql://intelluxe:{os.getenv('POSTGRES_PASSWORD', 'secure_password')}@localhost:5432/intelluxe_public"
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        total_inserted = 0

        # Load and insert exercises - try multiple files to get the best data
        exercises_files = [
            data_dir / "exercises_complete_all.json",  # Try this first
            data_dir / "exercises_complete.json",      # Fallback
            data_dir / "exercises_extracted.json",      # Last resort
        ]

        exercises_data = []
        for exercises_file in exercises_files:
            if exercises_file.exists():
                logger.info(f"Loading exercises data from {exercises_file}...")
                with open(exercises_file) as f:
                    exercises_data = json.load(f)
                logger.info(f"Found {len(exercises_data)} exercises in {exercises_file.name}")
                break

        if exercises_data:
            total_inserted += insert_exercises(cur, exercises_data)

        # Load and insert food items
        food_file = data_dir / "food_items_complete.json"
        if food_file.exists():
            logger.info("Loading food items data...")
            with open(food_file) as f:
                food_data = json.load(f)
            total_inserted += insert_food_items(cur, food_data)

        # Load and insert health topics (if exists)
        topics_file = data_dir / "health_topics_complete.json"
        if topics_file.exists():
            logger.info("Loading health topics data...")
            with open(topics_file) as f:
                topics_data = json.load(f)
            total_inserted += insert_health_topics(cur, topics_data)

        # Commit all changes
        conn.commit()
        logger.info(f"🎉 Successfully inserted {total_inserted} total health items into database!")

    except Exception as e:
        logger.exception(f"Database error: {e}")
        if "conn" in locals():
            conn.rollback()
        sys.exit(1)
    finally:
        if "cur" in locals():
            cur.close()
        if "conn" in locals():
            conn.close()


if __name__ == "__main__":
    main()
