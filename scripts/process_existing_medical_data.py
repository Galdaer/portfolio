#!/usr/bin/env python3
"""
Process existing medical data files into database tables.
This script will load data from downloaded JSON files into the appropriate database tables.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg2

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Database connection
DATABASE_URL = "postgresql://intelluxe:secure_password@172.20.0.13:5432/intelluxe_public"
DATA_DIR = Path("/home/intelluxe/database/medical_complete")


def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(DATABASE_URL)


def process_icd10_codes(data_file: Path) -> dict[str, Any]:
    """Process ICD-10 codes from JSON file into database"""
    logger.info(f"Processing ICD-10 codes from {data_file}")

    if not data_file.exists():
        logger.error(f"Data file not found: {data_file}")
        return {"success": False, "error": "File not found"}

    try:
        # Load JSON data
        with open(data_file) as f:
            codes_data = json.load(f)

        logger.info(f"Loaded {len(codes_data)} ICD-10 codes from file")

        # Connect to database
        conn = get_db_connection()
        cur = conn.cursor()

        # Clear existing data (optional - comment out if you want to append)
        cur.execute("DELETE FROM icd10_codes")
        logger.info("Cleared existing ICD-10 codes")

        # Insert new data
        inserted = 0
        skipped = 0

        for code_data in codes_data:
            try:
                # Prepare data for insertion
                insert_data = {
                    "code": code_data.get("code"),
                    "description": code_data.get("description"),
                    "category": code_data.get("category", ""),
                    "chapter": code_data.get("chapter", ""),
                    "synonyms": json.dumps(code_data.get("synonyms", [])),
                    "inclusion_notes": json.dumps(code_data.get("inclusion_notes", [])),
                    "exclusion_notes": json.dumps(code_data.get("exclusion_notes", [])),
                    "is_billable": code_data.get("is_billable", False),
                    "code_length": code_data.get("code_length", len(code_data.get("code", "").replace(".", ""))),
                    "parent_code": code_data.get("parent_code"),
                    "children_codes": json.dumps(code_data.get("children_codes", [])),
                    "source": code_data.get("source", "processed_file"),
                    "search_text": code_data.get("search_text", f"{code_data.get('code', '')} {code_data.get('description', '')}".lower()),
                    "last_updated": code_data.get("last_updated", datetime.now().isoformat()),
                }

                # Insert record
                cur.execute("""
                    INSERT INTO icd10_codes (
                        code, description, category, chapter, synonyms, inclusion_notes,
                        exclusion_notes, is_billable, code_length, parent_code, children_codes,
                        source, search_text, last_updated, created_at
                    ) VALUES (
                        %(code)s, %(description)s, %(category)s, %(chapter)s, %(synonyms)s,
                        %(inclusion_notes)s, %(exclusion_notes)s, %(is_billable)s, %(code_length)s,
                        %(parent_code)s, %(children_codes)s, %(source)s, %(search_text)s,
                        %(last_updated)s, NOW()
                    ) ON CONFLICT (code) DO UPDATE SET
                        description = EXCLUDED.description,
                        category = EXCLUDED.category,
                        chapter = EXCLUDED.chapter,
                        synonyms = EXCLUDED.synonyms,
                        inclusion_notes = EXCLUDED.inclusion_notes,
                        exclusion_notes = EXCLUDED.exclusion_notes,
                        is_billable = EXCLUDED.is_billable,
                        code_length = EXCLUDED.code_length,
                        parent_code = EXCLUDED.parent_code,
                        children_codes = EXCLUDED.children_codes,
                        source = EXCLUDED.source,
                        search_text = EXCLUDED.search_text,
                        last_updated = EXCLUDED.last_updated
                """, insert_data)

                inserted += 1

            except Exception as e:
                logger.warning(f"Failed to insert code {code_data.get('code', 'unknown')}: {e}")
                skipped += 1
                continue

        # Update search vectors
        logger.info("Updating search vectors...")
        cur.execute("""
            UPDATE icd10_codes
            SET search_vector = to_tsvector('english',
                COALESCE(code, '') || ' ' ||
                COALESCE(description, '') || ' ' ||
                COALESCE(category, '')
            )
            WHERE search_vector IS NULL
        """)

        # Commit changes
        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"ICD-10 processing complete: {inserted} inserted, {skipped} skipped")

        return {
            "success": True,
            "inserted": inserted,
            "skipped": skipped,
            "total_processed": len(codes_data),
        }

    except Exception as e:
        logger.exception(f"Error processing ICD-10 codes: {e}")
        return {"success": False, "error": str(e)}


def process_billing_codes(data_file: Path) -> dict[str, Any]:
    """Process billing codes from JSON file into database"""
    logger.info(f"Processing billing codes from {data_file}")

    if not data_file.exists():
        logger.error(f"Data file not found: {data_file}")
        return {"success": False, "error": "File not found"}

    try:
        # Load JSON data
        with open(data_file) as f:
            codes_data = json.load(f)

        logger.info(f"Loaded {len(codes_data)} billing codes from file")

        # Connect to database
        conn = get_db_connection()
        cur = conn.cursor()

        # Clear existing data (optional)
        cur.execute("DELETE FROM billing_codes")
        logger.info("Cleared existing billing codes")

        # Insert new data
        inserted = 0
        skipped = 0

        for code_data in codes_data:
            try:
                # Prepare data for insertion - use actual table schema
                insert_data = {
                    "code": code_data.get("code"),
                    "short_description": code_data.get("short_description", ""),
                    "long_description": code_data.get("long_description", ""),
                    "description": code_data.get("description", ""),
                    "code_type": code_data.get("code_type", "unknown"),
                    "category": code_data.get("category", ""),
                    "coverage_notes": code_data.get("coverage_notes", ""),
                    "effective_date": code_data.get("effective_date"),
                    "termination_date": code_data.get("termination_date"),
                    "is_active": code_data.get("is_active", True),
                    "modifier_required": code_data.get("modifier_required", False),
                    "gender_specific": code_data.get("gender_specific"),
                    "age_specific": code_data.get("age_specific"),
                    "bilateral_indicator": code_data.get("bilateral_indicator", False),
                    "source": code_data.get("source", "processed_file"),
                    "search_text": f"{code_data.get('code', '')} {code_data.get('description', '')}".lower(),
                    "last_updated": code_data.get("last_updated", datetime.now().isoformat()),
                }

                # Insert record
                cur.execute("""
                    INSERT INTO billing_codes (
                        code, short_description, long_description, description, code_type, category,
                        coverage_notes, effective_date, termination_date, is_active, modifier_required,
                        gender_specific, age_specific, bilateral_indicator, source, search_text,
                        last_updated, created_at
                    ) VALUES (
                        %(code)s, %(short_description)s, %(long_description)s, %(description)s, %(code_type)s,
                        %(category)s, %(coverage_notes)s, %(effective_date)s, %(termination_date)s, %(is_active)s,
                        %(modifier_required)s, %(gender_specific)s, %(age_specific)s, %(bilateral_indicator)s,
                        %(source)s, %(search_text)s, %(last_updated)s, NOW()
                    ) ON CONFLICT (code) DO UPDATE SET
                        short_description = EXCLUDED.short_description,
                        long_description = EXCLUDED.long_description,
                        description = EXCLUDED.description,
                        code_type = EXCLUDED.code_type,
                        category = EXCLUDED.category,
                        coverage_notes = EXCLUDED.coverage_notes,
                        effective_date = EXCLUDED.effective_date,
                        termination_date = EXCLUDED.termination_date,
                        is_active = EXCLUDED.is_active,
                        modifier_required = EXCLUDED.modifier_required,
                        gender_specific = EXCLUDED.gender_specific,
                        age_specific = EXCLUDED.age_specific,
                        bilateral_indicator = EXCLUDED.bilateral_indicator,
                        source = EXCLUDED.source,
                        search_text = EXCLUDED.search_text,
                        last_updated = EXCLUDED.last_updated
                """, insert_data)

                inserted += 1

            except Exception as e:
                logger.warning(f"Failed to insert code {code_data.get('code', 'unknown')}: {e}")
                skipped += 1
                continue

        # Update search vectors
        logger.info("Updating search vectors...")
        cur.execute("""
            UPDATE billing_codes
            SET search_vector = to_tsvector('english',
                COALESCE(code, '') || ' ' ||
                COALESCE(description, '') || ' ' ||
                COALESCE(category, '')
            )
            WHERE search_vector IS NULL
        """)

        # Commit changes
        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"Billing codes processing complete: {inserted} inserted, {skipped} skipped")

        return {
            "success": True,
            "inserted": inserted,
            "skipped": skipped,
            "total_processed": len(codes_data),
        }

    except Exception as e:
        logger.exception(f"Error processing billing codes: {e}")
        return {"success": False, "error": str(e)}


def process_health_topics(data_file: Path) -> dict[str, Any]:
    """Process health topics from JSON file into database"""
    logger.info(f"Processing health topics from {data_file}")

    if not data_file.exists():
        logger.error(f"Data file not found: {data_file}")
        return {"success": False, "error": "File not found"}

    try:
        # Load JSON data
        with open(data_file) as f:
            full_data = json.load(f)

        # Handle structured JSON with metadata
        if isinstance(full_data, dict) and "health_topics" in full_data:
            topics_data = full_data["health_topics"]
        elif isinstance(full_data, list):
            topics_data = full_data
        else:
            topics_data = [full_data]  # Single record

        logger.info(f"Loaded {len(topics_data)} health topics from file")

        # Connect to database
        conn = get_db_connection()
        cur = conn.cursor()

        # Clear existing data (optional)
        cur.execute("DELETE FROM health_topics")
        logger.info("Cleared existing health topics")

        # Insert new data
        inserted = 0
        skipped = 0

        for topic_data in topics_data:
            try:
                # Prepare data for insertion - match actual table schema
                insert_data = {
                    "topic_id": topic_data.get("topic_id") or str(topic_data.get("id", "")),
                    "title": topic_data.get("title", ""),
                    "category": topic_data.get("category", ""),
                    "url": topic_data.get("url", ""),
                    "last_reviewed": topic_data.get("last_reviewed", ""),
                    "audience": json.dumps(topic_data.get("audience", [])),
                    "sections": json.dumps(topic_data.get("sections", [])),
                    "related_topics": json.dumps(topic_data.get("related_topics", [])),
                    "summary": topic_data.get("summary", "") or topic_data.get("description", ""),
                    "keywords": json.dumps(topic_data.get("keywords", [])),
                    "content_length": len(str(topic_data.get("summary", "") or topic_data.get("description", ""))),
                    "source": topic_data.get("source", "processed_file"),
                    "search_text": f"{topic_data.get('title', '')} {topic_data.get('summary', '') or topic_data.get('description', '')}".lower(),
                    "last_updated": topic_data.get("last_updated", datetime.now().isoformat()),
                }

                # Insert record
                cur.execute("""
                    INSERT INTO health_topics (
                        topic_id, title, category, url, last_reviewed, audience, sections,
                        related_topics, summary, keywords, content_length, source,
                        search_text, last_updated, created_at
                    ) VALUES (
                        %(topic_id)s, %(title)s, %(category)s, %(url)s, %(last_reviewed)s,
                        %(audience)s, %(sections)s, %(related_topics)s, %(summary)s,
                        %(keywords)s, %(content_length)s, %(source)s, %(search_text)s,
                        %(last_updated)s, NOW()
                    ) ON CONFLICT (topic_id) DO UPDATE SET
                        title = EXCLUDED.title,
                        category = EXCLUDED.category,
                        url = EXCLUDED.url,
                        last_reviewed = EXCLUDED.last_reviewed,
                        audience = EXCLUDED.audience,
                        sections = EXCLUDED.sections,
                        related_topics = EXCLUDED.related_topics,
                        summary = EXCLUDED.summary,
                        keywords = EXCLUDED.keywords,
                        content_length = EXCLUDED.content_length,
                        source = EXCLUDED.source,
                        search_text = EXCLUDED.search_text,
                        last_updated = EXCLUDED.last_updated
                """, insert_data)

                inserted += 1

            except Exception as e:
                logger.warning(f"Failed to insert topic {topic_data.get('topic_id', 'unknown')}: {e}")
                skipped += 1
                continue

        # Update search vectors
        logger.info("Updating search vectors...")
        cur.execute("""
            UPDATE health_topics
            SET search_vector = to_tsvector('english',
                COALESCE(title, '') || ' ' ||
                COALESCE(summary, '') || ' ' ||
                COALESCE(category, '')
            )
            WHERE search_vector IS NULL
        """)

        # Commit changes
        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"Health topics processing complete: {inserted} inserted, {skipped} skipped")

        return {
            "success": True,
            "inserted": inserted,
            "skipped": skipped,
            "total_processed": len(topics_data),
        }

    except Exception as e:
        logger.exception(f"Error processing health topics: {e}")
        return {"success": False, "error": str(e)}


def process_exercises(data_file: Path) -> dict[str, Any]:
    """Process exercises from JSON file into database"""
    logger.info(f"Processing exercises from {data_file}")

    if not data_file.exists():
        logger.error(f"Data file not found: {data_file}")
        return {"success": False, "error": "File not found"}

    try:
        # Load JSON data
        with open(data_file) as f:
            full_data = json.load(f)

        # Handle structured JSON with metadata
        if isinstance(full_data, dict) and "exercises" in full_data:
            exercises_data = full_data["exercises"]
        elif isinstance(full_data, list):
            exercises_data = full_data
        else:
            exercises_data = [full_data]  # Single record

        logger.info(f"Loaded {len(exercises_data)} exercises from file")

        # Connect to database
        conn = get_db_connection()
        cur = conn.cursor()

        # Clear existing data (optional)
        cur.execute("DELETE FROM exercises")
        logger.info("Cleared existing exercises")

        # Insert new data
        inserted = 0
        skipped = 0

        for exercise_data in exercises_data:
            try:
                # Prepare data for insertion - match actual table schema
                insert_data = {
                    "exercise_id": exercise_data.get("exercise_id") or str(exercise_data.get("id", "")),
                    "name": exercise_data.get("name", ""),
                    "body_part": exercise_data.get("body_part", "") or exercise_data.get("bodyPart", ""),
                    "equipment": exercise_data.get("equipment", ""),
                    "target": exercise_data.get("target", "") or exercise_data.get("target_muscles", ""),
                    "secondary_muscles": json.dumps(exercise_data.get("secondary_muscles", []) or exercise_data.get("secondaryMuscles", [])),
                    "instructions": json.dumps(exercise_data.get("instructions", [])),
                    "gif_url": exercise_data.get("gif_url", "") or exercise_data.get("gifUrl", ""),
                    "difficulty_level": exercise_data.get("difficulty_level", "intermediate"),
                    "exercise_type": exercise_data.get("exercise_type", "") or exercise_data.get("category", ""),
                    "duration_estimate": exercise_data.get("duration_estimate", ""),
                    "calories_estimate": exercise_data.get("calories_estimate", ""),
                    "source": exercise_data.get("source", "processed_file"),
                    "search_text": f"{exercise_data.get('name', '')} {exercise_data.get('body_part', '') or exercise_data.get('bodyPart', '')} {exercise_data.get('equipment', '')}".lower(),
                    "last_updated": exercise_data.get("last_updated", datetime.now().isoformat()),
                }

                # Insert record
                cur.execute("""
                    INSERT INTO exercises (
                        exercise_id, name, body_part, equipment, target, secondary_muscles,
                        instructions, gif_url, difficulty_level, exercise_type,
                        duration_estimate, calories_estimate, source, search_text,
                        last_updated, created_at
                    ) VALUES (
                        %(exercise_id)s, %(name)s, %(body_part)s, %(equipment)s, %(target)s,
                        %(secondary_muscles)s, %(instructions)s, %(gif_url)s, %(difficulty_level)s,
                        %(exercise_type)s, %(duration_estimate)s, %(calories_estimate)s, %(source)s,
                        %(search_text)s, %(last_updated)s, NOW()
                    ) ON CONFLICT (exercise_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        body_part = EXCLUDED.body_part,
                        equipment = EXCLUDED.equipment,
                        target = EXCLUDED.target,
                        secondary_muscles = EXCLUDED.secondary_muscles,
                        instructions = EXCLUDED.instructions,
                        gif_url = EXCLUDED.gif_url,
                        difficulty_level = EXCLUDED.difficulty_level,
                        exercise_type = EXCLUDED.exercise_type,
                        duration_estimate = EXCLUDED.duration_estimate,
                        calories_estimate = EXCLUDED.calories_estimate,
                        source = EXCLUDED.source,
                        search_text = EXCLUDED.search_text,
                        last_updated = EXCLUDED.last_updated
                """, insert_data)

                inserted += 1

            except Exception as e:
                logger.warning(f"Failed to insert exercise {exercise_data.get('exercise_id', 'unknown')}: {e}")
                skipped += 1
                continue

        # Update search vectors
        logger.info("Updating search vectors...")
        cur.execute("""
            UPDATE exercises
            SET search_vector = to_tsvector('english',
                COALESCE(name, '') || ' ' ||
                COALESCE(body_part, '') || ' ' ||
                COALESCE(equipment, '') || ' ' ||
                COALESCE(target, '')
            )
            WHERE search_vector IS NULL
        """)

        # Commit changes
        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"Exercises processing complete: {inserted} inserted, {skipped} skipped")

        return {
            "success": True,
            "inserted": inserted,
            "skipped": skipped,
            "total_processed": len(exercises_data),
        }

    except Exception as e:
        logger.exception(f"Error processing exercises: {e}")
        return {"success": False, "error": str(e)}


def main():
    """Main function to process all data types"""
    logger.info("Starting medical data processing from existing files")

    results = {}

    # ICD-10 codes
    icd10_file = DATA_DIR / "icd10" / "all_icd10_codes_complete.json"
    if icd10_file.exists():
        logger.info("Processing ICD-10 codes...")
        results["icd10"] = process_icd10_codes(icd10_file)
    else:
        logger.warning(f"ICD-10 file not found: {icd10_file}")
        results["icd10"] = {"success": False, "error": "File not found"}

    # Billing codes
    billing_files = [
        DATA_DIR / "billing" / "all_billing_codes_complete.json",
        DATA_DIR / "all_billing_codes_complete.json",
    ]

    billing_processed = False
    for billing_file in billing_files:
        if billing_file.exists():
            logger.info("Processing billing codes...")
            results["billing"] = process_billing_codes(billing_file)
            billing_processed = True
            break

    if not billing_processed:
        logger.warning("No billing codes file found")
        results["billing"] = {"success": False, "error": "File not found"}

    # Health topics
    health_files = [
        DATA_DIR / "health_info" / "all_health_topics_complete.json",
        DATA_DIR / "all_health_topics_complete.json",
    ]

    health_processed = False
    for health_file in health_files:
        if health_file.exists():
            logger.info("Processing health topics...")
            results["health_topics"] = process_health_topics(health_file)
            health_processed = True
            break

    if not health_processed:
        logger.warning("No health topics file found")
        results["health_topics"] = {"success": False, "error": "File not found"}

    # Exercises
    exercise_files = [
        DATA_DIR / "health_info" / "all_exercises_complete.json",
        DATA_DIR / "all_exercises_complete.json",
    ]

    exercise_processed = False
    for exercise_file in exercise_files:
        if exercise_file.exists():
            logger.info("Processing exercises...")
            results["exercises"] = process_exercises(exercise_file)
            exercise_processed = True
            break

    if not exercise_processed:
        logger.warning("No exercises file found")
        results["exercises"] = {"success": False, "error": "File not found"}

    # Print summary
    logger.info("\n" + "="*50)
    logger.info("MEDICAL DATA PROCESSING SUMMARY")
    logger.info("="*50)

    for data_type, result in results.items():
        if result["success"]:
            logger.info(f"{data_type.upper()}: SUCCESS - {result.get('inserted', 0)} records inserted")
        else:
            logger.error(f"{data_type.upper()}: FAILED - {result.get('error', 'Unknown error')}")

    logger.info("="*50)

    return results


if __name__ == "__main__":
    try:
        results = main()

        # Exit with appropriate code
        all_success = all(r["success"] for r in results.values())
        sys.exit(0 if all_success else 1)

    except Exception as e:
        logger.exception(f"Critical error in medical data processing: {e}")
        sys.exit(1)
