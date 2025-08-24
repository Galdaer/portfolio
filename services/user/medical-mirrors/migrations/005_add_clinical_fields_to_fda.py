"""
Add clinical information fields to FDA drugs table

This migration adds comprehensive clinical fields to support:
- Drug interactions (JSON format for structured data)
- Safety information (contraindications, warnings, precautions)
- Clinical usage (indications, dosage, administration)
- Pharmacology (mechanism of action, pharmacokinetics, pharmacodynamics)
- Enhanced search capabilities
"""

import logging
import sys
from pathlib import Path

# Add src directory to Python path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from sqlalchemy import text

from database import engine

logger = logging.getLogger(__name__)


def upgrade():
    """Apply the migration"""
    logger.info("Starting migration 005: Add clinical fields to FDA drugs table")

    with engine.connect() as conn:
        # Add clinical information columns
        add_clinical_fields(conn)

        # Update search vector to include clinical fields
        update_search_vector_for_clinical_data(conn)

    logger.info("Migration 005 completed successfully")


def add_clinical_fields(conn):
    """Add clinical information columns to fda_drugs table"""
    logger.info("Adding clinical fields to fda_drugs table")

    # Clinical fields to add
    clinical_columns = [
        # Safety and warnings (arrays for multiple entries)
        ("contraindications", "TEXT[]"),
        ("warnings", "TEXT[]"),
        ("precautions", "TEXT[]"),
        ("adverse_reactions", "TEXT[]"),

        # Drug interactions (JSON for structured data)
        ("drug_interactions", "JSON"),

        # Clinical usage information
        ("indications_and_usage", "TEXT"),
        ("dosage_and_administration", "TEXT"),

        # Pharmacology information
        ("mechanism_of_action", "TEXT"),
        ("pharmacokinetics", "TEXT"),
        ("pharmacodynamics", "TEXT"),
    ]

    for column_name, column_type in clinical_columns:
        try:
            conn.execute(text(f"""
                ALTER TABLE fda_drugs
                ADD COLUMN IF NOT EXISTS {column_name} {column_type}
            """))
            logger.info(f"Added clinical column {column_name} to fda_drugs table")
        except Exception as e:
            logger.warning(f"Clinical column {column_name} might already exist: {e}")

    conn.commit()


def update_search_vector_for_clinical_data(conn):
    """Update search vector to include clinical information fields"""
    logger.info("Updating search vector to include clinical data")

    # Drop existing trigger and function
    conn.execute(text("""
        DROP TRIGGER IF EXISTS fda_drugs_search_vector_update ON fda_drugs
    """))

    conn.execute(text("""
        DROP FUNCTION IF EXISTS update_fda_drugs_search_vector()
    """))

    # Create enhanced search vector function with clinical data
    conn.execute(text("""
        CREATE OR REPLACE FUNCTION update_fda_drugs_search_vector()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector := to_tsvector('english',
                -- Basic drug information
                COALESCE(NEW.name, '') || ' ' ||
                COALESCE(NEW.generic_name, '') || ' ' ||
                COALESCE(NEW.brand_name, '') || ' ' ||
                COALESCE(NEW.manufacturer, '') || ' ' ||
                COALESCE(NEW.applicant, '') || ' ' ||
                COALESCE(array_to_string(NEW.ingredients, ' '), '') || ' ' ||
                COALESCE(NEW.therapeutic_class, '') || ' ' ||
                COALESCE(NEW.pharmacologic_class, '') || ' ' ||

                -- Clinical information (key for medical searches)
                COALESCE(NEW.indications_and_usage, '') || ' ' ||
                COALESCE(NEW.mechanism_of_action, '') || ' ' ||
                COALESCE(array_to_string(NEW.contraindications, ' '), '') || ' ' ||
                COALESCE(array_to_string(NEW.warnings, ' '), '') || ' ' ||
                COALESCE(array_to_string(NEW.adverse_reactions, ' '), '')
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """))

    # Create updated trigger
    conn.execute(text("""
        CREATE TRIGGER fda_drugs_search_vector_update
            BEFORE INSERT OR UPDATE ON fda_drugs
            FOR EACH ROW EXECUTE FUNCTION update_fda_drugs_search_vector();
    """))

    conn.commit()
    logger.info("Updated search vector to include clinical data")


def downgrade():
    """Reverse the migration"""
    logger.info("Starting migration 005 downgrade")

    with engine.connect() as conn:
        # Remove clinical columns
        clinical_columns = [
            "contraindications",
            "warnings",
            "precautions",
            "adverse_reactions",
            "drug_interactions",
            "indications_and_usage",
            "dosage_and_administration",
            "mechanism_of_action",
            "pharmacokinetics",
            "pharmacodynamics",
        ]

        for column_name in clinical_columns:
            try:
                conn.execute(text(f"""
                    ALTER TABLE fda_drugs
                    DROP COLUMN IF EXISTS {column_name}
                """))
                logger.info(f"Removed clinical column {column_name} from fda_drugs table")
            except Exception as e:
                logger.warning(f"Error removing clinical column {column_name}: {e}")

        # Restore previous search vector function
        conn.execute(text("""
            DROP TRIGGER IF EXISTS fda_drugs_search_vector_update ON fda_drugs
        """))

        conn.execute(text("""
            DROP FUNCTION IF EXISTS update_fda_drugs_search_vector()
        """))

        conn.execute(text("""
            CREATE OR REPLACE FUNCTION update_fda_drugs_search_vector()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.search_vector := to_tsvector('english',
                    COALESCE(NEW.name, '') || ' ' ||
                    COALESCE(NEW.generic_name, '') || ' ' ||
                    COALESCE(NEW.brand_name, '') || ' ' ||
                    COALESCE(NEW.manufacturer, '') || ' ' ||
                    COALESCE(NEW.applicant, '') || ' ' ||
                    COALESCE(array_to_string(NEW.ingredients, ' '), '') || ' ' ||
                    COALESCE(NEW.therapeutic_class, '') || ' ' ||
                    COALESCE(NEW.pharmacologic_class, '')
                );
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """))

        conn.execute(text("""
            CREATE TRIGGER fda_drugs_search_vector_update
                BEFORE INSERT OR UPDATE ON fda_drugs
                FOR EACH ROW EXECUTE FUNCTION update_fda_drugs_search_vector();
        """))

        conn.commit()

    logger.info("Migration 005 downgrade completed")


if __name__ == "__main__":
    upgrade()
