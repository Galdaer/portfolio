#!/usr/bin/env python3
"""
Parse and insert health info data files into database
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

# Add medical-mirrors src to path
sys.path.append("/home/intelluxe/services/user/medical-mirrors/src")

from health_info.parser import HealthInfoParser


def load_health_data_files(data_dir: Path) -> dict:
    """Load health info data files"""
    health_data = {}

    # Load exercises
    exercises_file = data_dir / "exercises_complete.json"
    if exercises_file.exists():
        with open(exercises_file) as f:
            health_data["exercises"] = json.load(f)
            logger.info(f"Loaded {len(health_data['exercises'])} exercises")

    # Load food items
    food_items_file = data_dir / "food_items_complete.json"
    if food_items_file.exists():
        with open(food_items_file) as f:
            health_data["food_items"] = json.load(f)
            logger.info(f"Loaded {len(health_data['food_items'])} food items")

    # Load health topics (if exists)
    health_topics_file = data_dir / "health_topics_complete.json"
    if health_topics_file.exists():
        with open(health_topics_file) as f:
            health_data["health_topics"] = json.load(f)
            logger.info(f"Loaded {len(health_data['health_topics'])} health topics")
    else:
        logger.info("No health topics file found - using existing database data")
        health_data["health_topics"] = []

    return health_data


def insert_health_data(validated_data: dict):
    """Insert health data into database"""
    try:
        # Database connection
        db_url = f"postgresql://intelluxe:{os.getenv('POSTGRES_PASSWORD', 'secure_password')}@localhost:5432/intelluxe_public"
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        # Insert exercises
        if validated_data["exercises"]:
            logger.info(f"Inserting {len(validated_data['exercises'])} exercises...")

            # Clear existing data
            cur.execute("DELETE FROM exercises")

            # Insert new data
            for exercise in validated_data["exercises"]:
                cur.execute("""
                    INSERT INTO exercises (
                        exercise_id, name, body_part, target, equipment,
                        gif_url, instructions, secondary_muscles, synergists
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (exercise_id) DO NOTHING
                """, (
                    exercise.get("id"),
                    exercise.get("name"),
                    exercise.get("bodyPart"),
                    exercise.get("target"),
                    exercise.get("equipment"),
                    exercise.get("gifUrl"),
                    exercise.get("instructions", []),
                    exercise.get("secondaryMuscles", []),
                    exercise.get("synergists", []),
                ))

            logger.info("✅ Inserted exercises")

        # Insert food items
        if validated_data["food_items"]:
            logger.info(f"Inserting {len(validated_data['food_items'])} food items...")

            # Clear existing data
            cur.execute("DELETE FROM food_items")

            # Insert new data
            for food in validated_data["food_items"]:
                cur.execute("""
                    INSERT INTO food_items (
                        fdc_id, description, food_category, nutrients,
                        search_terms, data_type, brand_owner
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (fdc_id) DO NOTHING
                """, (
                    food.get("fdcId"),
                    food.get("description"),
                    food.get("foodCategory"),
                    json.dumps(food.get("nutrients", [])),
                    food.get("searchTerms", []),
                    food.get("dataType"),
                    food.get("brandOwner"),
                ))

            logger.info("✅ Inserted food items")

        # Commit changes
        conn.commit()
        logger.info("✅ All health data successfully inserted into database")

    except Exception as e:
        logger.exception(f"Database error: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def main():
    """Main processing function"""
    data_dir = Path("/home/intelluxe/database/medical_complete/health_info")

    logger.info("Loading health info data files...")
    raw_data = load_health_data_files(data_dir)

    if not raw_data:
        logger.error("No data files found to process")
        return

    logger.info("Parsing and validating data...")
    parser = HealthInfoParser()
    validated_data = parser.parse_and_validate(raw_data)

    logger.info("Inserting into database...")
    insert_health_data(validated_data)

    logger.info("Health info processing complete!")


if __name__ == "__main__":
    main()
