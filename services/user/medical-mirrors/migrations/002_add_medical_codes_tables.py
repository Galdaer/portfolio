"""
Add medical codes tables (ICD-10, billing codes, health information)

This migration adds:
- icd10_codes table for ICD-10 diagnostic codes
- billing_codes table for CPT/HCPCS billing codes
- health_topics table for MyHealthfinder content
- exercises table for ExerciseDB data
- food_items table for USDA food data
- Full-text search indices for all tables
"""

import logging

from sqlalchemy import text
from src.database import engine

logger = logging.getLogger(__name__)


def upgrade():
    """Apply the migration"""
    logger.info("Starting migration 002: Add medical codes tables")

    with engine.connect() as conn:
        # Enable required extensions
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        conn.commit()

        # Create ICD-10 codes table
        create_icd10_table(conn)

        # Create billing codes table
        create_billing_codes_table(conn)

        # Create health topics table
        create_health_topics_table(conn)

        # Create exercises table
        create_exercises_table(conn)

        # Create food items table
        create_food_items_table(conn)

        # Create indices
        create_indices(conn)

    logger.info("Migration 002 completed successfully")


def create_icd10_table(conn):
    """Create ICD-10 codes table"""
    logger.info("Creating icd10_codes table")

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS icd10_codes (
            code VARCHAR(20) PRIMARY KEY,
            description TEXT NOT NULL,
            category VARCHAR(200),
            chapter VARCHAR(10),
            synonyms JSONB,
            inclusion_notes JSONB,
            exclusion_notes JSONB,
            is_billable BOOLEAN DEFAULT false,
            code_length INTEGER,
            parent_code VARCHAR(20),
            children_codes JSONB,
            source VARCHAR(50) DEFAULT 'nlm_clinical_tables',
            search_text TEXT,
            search_vector tsvector,
            last_updated TIMESTAMP DEFAULT NOW(),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))

    # Create trigger for automatic search vector update
    conn.execute(text("""
        CREATE OR REPLACE FUNCTION update_icd10_search_vector()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', COALESCE(NEW.code, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(NEW.category, '')), 'C') ||
                setweight(to_tsvector('english', COALESCE(NEW.search_text, '')), 'D');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """))

    conn.execute(text("""
        DROP TRIGGER IF EXISTS icd10_search_vector_update ON icd10_codes
    """))

    conn.execute(text("""
        CREATE TRIGGER icd10_search_vector_update
        BEFORE INSERT OR UPDATE ON icd10_codes
        FOR EACH ROW EXECUTE FUNCTION update_icd10_search_vector()
    """))

    conn.commit()


def create_billing_codes_table(conn):
    """Create billing codes table"""
    logger.info("Creating billing_codes table")

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS billing_codes (
            code VARCHAR(20) PRIMARY KEY,
            short_description TEXT,
            long_description TEXT,
            description TEXT,
            code_type VARCHAR(20) NOT NULL,
            category VARCHAR(200),
            coverage_notes TEXT,
            effective_date DATE,
            termination_date DATE,
            is_active BOOLEAN DEFAULT true,
            modifier_required BOOLEAN DEFAULT false,
            gender_specific VARCHAR(20),
            age_specific VARCHAR(20),
            bilateral_indicator BOOLEAN DEFAULT false,
            source VARCHAR(50) DEFAULT 'nlm_clinical_tables',
            search_text TEXT,
            search_vector tsvector,
            last_updated TIMESTAMP DEFAULT NOW(),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))

    # Create trigger for automatic search vector update
    conn.execute(text("""
        CREATE OR REPLACE FUNCTION update_billing_codes_search_vector()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', COALESCE(NEW.code, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(NEW.short_description, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(NEW.long_description, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(NEW.category, '')), 'C') ||
                setweight(to_tsvector('english', COALESCE(NEW.search_text, '')), 'D');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """))

    conn.execute(text("""
        DROP TRIGGER IF EXISTS billing_codes_search_vector_update ON billing_codes
    """))

    conn.execute(text("""
        CREATE TRIGGER billing_codes_search_vector_update
        BEFORE INSERT OR UPDATE ON billing_codes
        FOR EACH ROW EXECUTE FUNCTION update_billing_codes_search_vector()
    """))

    conn.commit()


def create_health_topics_table(conn):
    """Create health topics table"""
    logger.info("Creating health_topics table")

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS health_topics (
            topic_id VARCHAR(50) PRIMARY KEY,
            title TEXT NOT NULL,
            category VARCHAR(200),
            url TEXT,
            last_reviewed VARCHAR(50),
            audience JSONB,
            sections JSONB,
            related_topics JSONB,
            summary TEXT,
            keywords JSONB,
            content_length INTEGER DEFAULT 0,
            source VARCHAR(50) DEFAULT 'medlineplus',
            search_text TEXT,
            search_vector tsvector,
            last_updated TIMESTAMP DEFAULT NOW(),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))

    # Create trigger for automatic search vector update
    conn.execute(text("""
        CREATE OR REPLACE FUNCTION update_health_topics_search_vector()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.category, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(NEW.summary, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(NEW.search_text, '')), 'D');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """))

    conn.execute(text("""
        DROP TRIGGER IF EXISTS health_topics_search_vector_update ON health_topics
    """))

    conn.execute(text("""
        CREATE TRIGGER health_topics_search_vector_update
        BEFORE INSERT OR UPDATE ON health_topics
        FOR EACH ROW EXECUTE FUNCTION update_health_topics_search_vector()
    """))

    conn.commit()


def create_exercises_table(conn):
    """Create exercises table"""
    logger.info("Creating exercises table")

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS exercises (
            exercise_id VARCHAR(50) PRIMARY KEY,
            name TEXT NOT NULL,
            body_part VARCHAR(100),
            equipment VARCHAR(100),
            target VARCHAR(100),
            secondary_muscles JSONB,
            instructions JSONB,
            gif_url TEXT,
            difficulty_level VARCHAR(50),
            exercise_type VARCHAR(50),
            duration_estimate VARCHAR(100),
            calories_estimate VARCHAR(100),
            source VARCHAR(50) DEFAULT 'exercisedb',
            search_text TEXT,
            search_vector tsvector,
            last_updated TIMESTAMP DEFAULT NOW(),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))

    # Create trigger for automatic search vector update
    conn.execute(text("""
        CREATE OR REPLACE FUNCTION update_exercises_search_vector()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', COALESCE(NEW.name, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.body_part, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(NEW.target, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(NEW.equipment, '')), 'C') ||
                setweight(to_tsvector('english', COALESCE(NEW.search_text, '')), 'D');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """))

    conn.execute(text("""
        DROP TRIGGER IF EXISTS exercises_search_vector_update ON exercises
    """))

    conn.execute(text("""
        CREATE TRIGGER exercises_search_vector_update
        BEFORE INSERT OR UPDATE ON exercises
        FOR EACH ROW EXECUTE FUNCTION update_exercises_search_vector()
    """))

    conn.commit()


def create_food_items_table(conn):
    """Create food items table"""
    logger.info("Creating food_items table")

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS food_items (
            fdc_id INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            scientific_name TEXT,
            common_names TEXT,
            food_category VARCHAR(200),
            nutrients JSONB,
            nutrition_summary JSONB,
            brand_owner VARCHAR(200),
            ingredients TEXT,
            serving_size NUMERIC,
            serving_size_unit VARCHAR(50),
            allergens JSONB,
            dietary_flags JSONB,
            nutritional_density NUMERIC DEFAULT 0,
            source VARCHAR(50) DEFAULT 'usda_fooddata',
            search_text TEXT,
            search_vector tsvector,
            last_updated TIMESTAMP DEFAULT NOW(),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))

    # Create trigger for automatic search vector update
    conn.execute(text("""
        CREATE OR REPLACE FUNCTION update_food_items_search_vector()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.common_names, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(NEW.food_category, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(NEW.brand_owner, '')), 'C') ||
                setweight(to_tsvector('english', COALESCE(NEW.search_text, '')), 'D');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """))

    conn.execute(text("""
        DROP TRIGGER IF EXISTS food_items_search_vector_update ON food_items
    """))

    conn.execute(text("""
        CREATE TRIGGER food_items_search_vector_update
        BEFORE INSERT OR UPDATE ON food_items
        FOR EACH ROW EXECUTE FUNCTION update_food_items_search_vector()
    """))

    conn.commit()


def create_indices(conn):
    """Create database indices for performance"""
    logger.info("Creating database indices")

    # ICD-10 indices
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_icd10_search_vector ON icd10_codes USING gin(search_vector)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_icd10_code ON icd10_codes(UPPER(code))"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_icd10_category ON icd10_codes(category)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_icd10_chapter ON icd10_codes(chapter)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_icd10_billable ON icd10_codes(is_billable)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_icd10_parent ON icd10_codes(parent_code)"))

    # Billing codes indices
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_billing_search_vector ON billing_codes USING gin(search_vector)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_billing_code ON billing_codes(UPPER(code))"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_billing_type ON billing_codes(code_type)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_billing_category ON billing_codes(category)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_billing_active ON billing_codes(is_active)"))

    # Health topics indices
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_health_topics_search_vector ON health_topics USING gin(search_vector)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_health_topics_category ON health_topics(category)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_health_topics_audience ON health_topics USING gin(audience)"))

    # Exercises indices
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_exercises_search_vector ON exercises USING gin(search_vector)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_exercises_body_part ON exercises(body_part)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_exercises_equipment ON exercises(equipment)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_exercises_difficulty ON exercises(difficulty_level)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_exercises_type ON exercises(exercise_type)"))

    # Food items indices
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_food_items_search_vector ON food_items USING gin(search_vector)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_food_items_category ON food_items(food_category)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_food_items_brand ON food_items(brand_owner)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_food_items_dietary ON food_items USING gin(dietary_flags)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_food_items_allergens ON food_items USING gin(allergens)"))

    # General performance indices
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_icd10_updated ON icd10_codes(last_updated)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_billing_updated ON billing_codes(last_updated)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_health_topics_updated ON health_topics(last_updated)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_exercises_updated ON exercises(last_updated)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_food_items_updated ON food_items(last_updated)"))

    conn.commit()


def downgrade():
    """Reverse the migration"""
    logger.info("Downgrading migration 002")

    with engine.connect() as conn:
        # Drop tables in reverse order
        tables = [
            "food_items",
            "exercises",
            "health_topics",
            "billing_codes",
            "icd10_codes",
        ]

        for table in tables:
            conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))

        # Drop functions
        functions = [
            "update_icd10_search_vector()",
            "update_billing_codes_search_vector()",
            "update_health_topics_search_vector()",
            "update_exercises_search_vector()",
            "update_food_items_search_vector()",
        ]

        for function in functions:
            conn.execute(text(f"DROP FUNCTION IF EXISTS {function} CASCADE"))

        conn.commit()

    logger.info("Migration 002 downgrade completed")


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()
