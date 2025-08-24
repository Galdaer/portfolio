"""
Fix column width issues across all tables

This migration addresses potential data truncation issues by:
- Increasing column widths for fields that might be too small
- Improving data type consistency
- Adding safety margins for string fields
"""

import logging

from sqlalchemy import text
from src.database import engine

logger = logging.getLogger(__name__)


def get_existing_tables(conn):
    """Get list of existing tables"""
    result = conn.execute(text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
    """))
    return [row[0] for row in result.fetchall()]


def upgrade():
    """Apply the migration"""
    logger.info("Starting migration 004: Fix column widths")

    with engine.connect() as conn:
        # Check which tables exist first
        existing_tables = get_existing_tables(conn)
        logger.info(f"Found existing tables: {existing_tables}")

        # Fix UpdateLog table (always exists)
        if "update_logs" in existing_tables:
            fix_update_logs_columns(conn)

        # Fix FDADrug table (always exists)
        if "fda_drugs" in existing_tables:
            fix_fda_drugs_columns(conn)

        # Fix ICD-10 codes table (only if exists)
        if "icd10_codes" in existing_tables:
            fix_icd10_codes_columns(conn)

        # Fix Billing codes table (only if exists)
        if "billing_codes" in existing_tables:
            fix_billing_codes_columns(conn)

        # Fix Health info tables (only if exist)
        if any(table in existing_tables for table in ["health_topics", "exercises", "food_items"]):
            fix_health_info_columns(conn, existing_tables)

    logger.info("Migration 004 completed successfully")


def fix_update_logs_columns(conn):
    """Fix UpdateLog table column widths"""
    logger.info("Fixing UpdateLog table columns")

    # Increase status column from 20 to 50 characters
    conn.execute(text("""
        ALTER TABLE update_logs
        ALTER COLUMN status TYPE VARCHAR(50)
    """))

    # Increase source column to handle longer source names
    conn.execute(text("""
        ALTER TABLE update_logs
        ALTER COLUMN source TYPE VARCHAR(100)
    """))

    # Increase update_type for more descriptive types
    conn.execute(text("""
        ALTER TABLE update_logs
        ALTER COLUMN update_type TYPE VARCHAR(100)
    """))

    conn.commit()
    logger.info("Updated UpdateLog table columns")


def fix_fda_drugs_columns(conn):
    """Fix FDADrug table column widths"""
    logger.info("Fixing FDADrug table columns")

    # Increase reference_listed_drug from 5 to 10
    conn.execute(text("""
        ALTER TABLE fda_drugs
        ALTER COLUMN reference_listed_drug TYPE VARCHAR(10)
    """))

    # Increase orange_book_code to handle longer equivalence codes
    conn.execute(text("""
        ALTER TABLE fda_drugs
        ALTER COLUMN orange_book_code TYPE VARCHAR(50)
    """))

    # Increase application_number to handle edge cases
    conn.execute(text("""
        ALTER TABLE fda_drugs
        ALTER COLUMN application_number TYPE VARCHAR(50)
    """))

    # Increase product_number for safety
    conn.execute(text("""
        ALTER TABLE fda_drugs
        ALTER COLUMN product_number TYPE VARCHAR(20)
    """))

    conn.commit()
    logger.info("Updated FDADrug table columns")


def fix_icd10_codes_columns(conn):
    """Fix ICD-10 codes table column widths"""
    logger.info("Fixing ICD-10 codes table columns")

    # Increase chapter from 10 to 50 characters
    conn.execute(text("""
        ALTER TABLE icd10_codes
        ALTER COLUMN chapter TYPE VARCHAR(50)
    """))

    # Increase code from 20 to 30 for complex codes with extensions
    conn.execute(text("""
        ALTER TABLE icd10_codes
        ALTER COLUMN code TYPE VARCHAR(30)
    """))

    # Increase parent_code accordingly
    conn.execute(text("""
        ALTER TABLE icd10_codes
        ALTER COLUMN parent_code TYPE VARCHAR(30)
    """))

    # Increase category for longer category names
    conn.execute(text("""
        ALTER TABLE icd10_codes
        ALTER COLUMN category TYPE VARCHAR(300)
    """))

    # Increase source field
    conn.execute(text("""
        ALTER TABLE icd10_codes
        ALTER COLUMN source TYPE VARCHAR(100)
    """))

    conn.commit()
    logger.info("Updated ICD-10 codes table columns")


def fix_billing_codes_columns(conn):
    """Fix billing codes table column widths"""
    logger.info("Fixing billing codes table columns")

    # Increase code from 20 to 30 for complex billing codes
    conn.execute(text("""
        ALTER TABLE billing_codes
        ALTER COLUMN code TYPE VARCHAR(30)
    """))

    # Increase code_type for longer code type descriptions
    conn.execute(text("""
        ALTER TABLE billing_codes
        ALTER COLUMN code_type TYPE VARCHAR(50)
    """))

    # Increase category for longer category names
    conn.execute(text("""
        ALTER TABLE billing_codes
        ALTER COLUMN category TYPE VARCHAR(300)
    """))

    # Increase gender_specific from 20 to 100
    conn.execute(text("""
        ALTER TABLE billing_codes
        ALTER COLUMN gender_specific TYPE VARCHAR(100)
    """))

    # Increase age_specific from 20 to 100
    conn.execute(text("""
        ALTER TABLE billing_codes
        ALTER COLUMN age_specific TYPE VARCHAR(100)
    """))

    # Increase source field
    conn.execute(text("""
        ALTER TABLE billing_codes
        ALTER COLUMN source TYPE VARCHAR(100)
    """))

    conn.commit()
    logger.info("Updated billing codes table columns")


def fix_health_info_columns(conn, existing_tables):
    """Fix health info tables column widths"""
    logger.info("Fixing health info table columns")

    # Fix health_topics table (only if exists)
    if "health_topics" in existing_tables:
        conn.execute(text("""
            ALTER TABLE health_topics
            ALTER COLUMN topic_id TYPE VARCHAR(100),
            ALTER COLUMN category TYPE VARCHAR(300),
            ALTER COLUMN last_reviewed TYPE VARCHAR(100),
            ALTER COLUMN source TYPE VARCHAR(100)
        """))
        logger.info("Updated health_topics table columns")

    # Fix exercises table (only if exists)
    if "exercises" in existing_tables:
        conn.execute(text("""
            ALTER TABLE exercises
            ALTER COLUMN exercise_id TYPE VARCHAR(100),
            ALTER COLUMN body_part TYPE VARCHAR(200),
            ALTER COLUMN equipment TYPE VARCHAR(200),
            ALTER COLUMN target TYPE VARCHAR(200),
            ALTER COLUMN difficulty_level TYPE VARCHAR(100),
            ALTER COLUMN exercise_type TYPE VARCHAR(100),
            ALTER COLUMN duration_estimate TYPE VARCHAR(200),
            ALTER COLUMN calories_estimate TYPE VARCHAR(200),
            ALTER COLUMN source TYPE VARCHAR(100)
        """))
        logger.info("Updated exercises table columns")

    # Fix food_items table (only if exists)
    if "food_items" in existing_tables:
        conn.execute(text("""
            ALTER TABLE food_items
            ALTER COLUMN food_category TYPE VARCHAR(300),
            ALTER COLUMN brand_owner TYPE VARCHAR(300),
            ALTER COLUMN serving_size_unit TYPE VARCHAR(100),
            ALTER COLUMN source TYPE VARCHAR(100)
        """))
        logger.info("Updated food_items table columns")

    conn.commit()
    logger.info("Updated health info table columns")


def downgrade():
    """Reverse the migration"""
    logger.info("Starting migration 004 downgrade")

    with engine.connect() as conn:
        # Revert UpdateLog changes
        conn.execute(text("""
            ALTER TABLE update_logs
            ALTER COLUMN status TYPE VARCHAR(20),
            ALTER COLUMN source TYPE VARCHAR(50),
            ALTER COLUMN update_type TYPE VARCHAR(50)
        """))

        # Revert FDADrug changes
        conn.execute(text("""
            ALTER TABLE fda_drugs
            ALTER COLUMN reference_listed_drug TYPE VARCHAR(5),
            ALTER COLUMN orange_book_code TYPE VARCHAR(20),
            ALTER COLUMN application_number TYPE VARCHAR(20),
            ALTER COLUMN product_number TYPE VARCHAR(10)
        """))

        # Revert ICD-10 changes
        conn.execute(text("""
            ALTER TABLE icd10_codes
            ALTER COLUMN chapter TYPE VARCHAR(10),
            ALTER COLUMN code TYPE VARCHAR(20),
            ALTER COLUMN parent_code TYPE VARCHAR(20),
            ALTER COLUMN category TYPE VARCHAR(200),
            ALTER COLUMN source TYPE VARCHAR(50)
        """))

        # Revert billing codes changes
        conn.execute(text("""
            ALTER TABLE billing_codes
            ALTER COLUMN code TYPE VARCHAR(20),
            ALTER COLUMN code_type TYPE VARCHAR(20),
            ALTER COLUMN category TYPE VARCHAR(200),
            ALTER COLUMN gender_specific TYPE VARCHAR(20),
            ALTER COLUMN age_specific TYPE VARCHAR(20),
            ALTER COLUMN source TYPE VARCHAR(50)
        """))

        # Revert health info changes
        conn.execute(text("""
            ALTER TABLE health_topics
            ALTER COLUMN topic_id TYPE VARCHAR(50),
            ALTER COLUMN category TYPE VARCHAR(200),
            ALTER COLUMN last_reviewed TYPE VARCHAR(50),
            ALTER COLUMN source TYPE VARCHAR(50)
        """))

        conn.execute(text("""
            ALTER TABLE exercises
            ALTER COLUMN exercise_id TYPE VARCHAR(50),
            ALTER COLUMN body_part TYPE VARCHAR(100),
            ALTER COLUMN equipment TYPE VARCHAR(100),
            ALTER COLUMN target TYPE VARCHAR(100),
            ALTER COLUMN difficulty_level TYPE VARCHAR(50),
            ALTER COLUMN exercise_type TYPE VARCHAR(50),
            ALTER COLUMN duration_estimate TYPE VARCHAR(100),
            ALTER COLUMN calories_estimate TYPE VARCHAR(100),
            ALTER COLUMN source TYPE VARCHAR(50)
        """))

        conn.execute(text("""
            ALTER TABLE food_items
            ALTER COLUMN food_category TYPE VARCHAR(200),
            ALTER COLUMN brand_owner TYPE VARCHAR(200),
            ALTER COLUMN serving_size_unit TYPE VARCHAR(50),
            ALTER COLUMN source TYPE VARCHAR(50)
        """))

        conn.commit()

    logger.info("Migration 004 downgrade completed")


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()
