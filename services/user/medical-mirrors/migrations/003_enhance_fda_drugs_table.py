"""
Enhance FDA drugs table to handle all 4 data sources

This migration adds columns to support:
- Orange Book data (therapeutic equivalence, application numbers, RLD flags)
- Drugs@FDA data (applicant, pharmacologic class)
- Drug Labels data (enhanced classification)
- Data source tracking
"""

import logging

from sqlalchemy import text
from src.database import engine

logger = logging.getLogger(__name__)


def upgrade():
    """Apply the migration"""
    logger.info("Starting migration 003: Enhance FDA drugs table")

    with engine.connect() as conn:
        # Add new columns to fda_drugs table
        enhance_fda_drugs_table(conn)

        # Update search vector trigger to include new fields
        update_search_vector_trigger(conn)

    logger.info("Migration 003 completed successfully")


def enhance_fda_drugs_table(conn):
    """Add new columns to fda_drugs table"""
    logger.info("Enhancing fda_drugs table with new columns")

    # Check if columns already exist before adding them
    columns_to_add = [
        ("applicant", "TEXT"),
        ("strength", "TEXT"),
        ("application_number", "VARCHAR(20)"),
        ("product_number", "VARCHAR(10)"),
        ("reference_listed_drug", "VARCHAR(5)"),
        ("pharmacologic_class", "TEXT"),
        ("data_sources", "TEXT[]"),
    ]

    for column_name, column_type in columns_to_add:
        try:
            conn.execute(text(f"""
                ALTER TABLE fda_drugs
                ADD COLUMN IF NOT EXISTS {column_name} {column_type}
            """))
            logger.info(f"Added column {column_name} to fda_drugs table")
        except Exception as e:
            logger.warning(f"Column {column_name} might already exist: {e}")

    conn.commit()


def update_search_vector_trigger(conn):
    """Update search vector trigger to include new fields"""
    logger.info("Updating search vector trigger for fda_drugs")

    # Drop existing trigger
    conn.execute(text("""
        DROP TRIGGER IF EXISTS fda_drugs_search_vector_update ON fda_drugs
    """))

    # Drop existing function
    conn.execute(text("""
        DROP FUNCTION IF EXISTS update_fda_drugs_search_vector()
    """))

    # Create updated function
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

    # Create updated trigger
    conn.execute(text("""
        CREATE TRIGGER fda_drugs_search_vector_update
            BEFORE INSERT OR UPDATE ON fda_drugs
            FOR EACH ROW EXECUTE FUNCTION update_fda_drugs_search_vector();
    """))

    conn.commit()
    logger.info("Updated search vector trigger for fda_drugs")


def downgrade():
    """Reverse the migration"""
    logger.info("Starting migration 003 downgrade")

    with engine.connect() as conn:
        # Remove added columns
        columns_to_remove = [
            "applicant",
            "strength",
            "application_number",
            "product_number",
            "reference_listed_drug",
            "pharmacologic_class",
            "data_sources",
        ]

        for column_name in columns_to_remove:
            try:
                conn.execute(text(f"""
                    ALTER TABLE fda_drugs
                    DROP COLUMN IF EXISTS {column_name}
                """))
                logger.info(f"Removed column {column_name} from fda_drugs table")
            except Exception as e:
                logger.warning(f"Error removing column {column_name}: {e}")

        # Restore original search vector trigger
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
                    COALESCE(array_to_string(NEW.ingredients, ' '), '') || ' ' ||
                    COALESCE(NEW.therapeutic_class, '')
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

    logger.info("Migration 003 downgrade completed")


if __name__ == "__main__":
    upgrade()
