"""
Database migrations for medical mirrors
"""

from sqlalchemy import create_engine, text
import logging
from database import Base, get_database_url

logger = logging.getLogger(__name__)


def create_database_indexes():
    """Create optimized indexes for medical mirrors"""
    engine = create_engine(get_database_url())

    with engine.connect() as conn:
        # Create GIN indexes for full-text search
        logger.info("Creating full-text search indexes...")

        # PubMed indexes
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_pubmed_search_vector 
            ON pubmed_articles USING GIN(search_vector)
        """)
        )

        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_pubmed_pmid 
            ON pubmed_articles(pmid)
        """)
        )

        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_pubmed_pub_date 
            ON pubmed_articles(pub_date)
        """)
        )

        # Clinical trials indexes
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_trials_search_vector 
            ON clinical_trials USING GIN(search_vector)
        """)
        )

        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_trials_nct_id 
            ON clinical_trials(nct_id)
        """)
        )

        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_trials_status 
            ON clinical_trials(status)
        """)
        )

        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_trials_conditions 
            ON clinical_trials USING GIN(conditions)
        """)
        )

        # FDA drugs indexes
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_fda_search_vector 
            ON fda_drugs USING GIN(search_vector)
        """)
        )

        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_fda_ndc 
            ON fda_drugs(ndc)
        """)
        )

        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_fda_generic_name 
            ON fda_drugs(generic_name)
        """)
        )

        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_fda_brand_name 
            ON fda_drugs(brand_name)
        """)
        )

        # Update logs indexes
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_update_logs_source_date 
            ON update_logs(source, started_at DESC)
        """)
        )

        conn.commit()
        logger.info("Database indexes created successfully")


def create_database_functions():
    """Create helpful database functions"""
    engine = create_engine(get_database_url())

    with engine.connect() as conn:
        # Function to update search vectors
        logger.info("Creating database functions...")

        # PubMed search vector update function
        conn.execute(
            text("""
            CREATE OR REPLACE FUNCTION update_pubmed_search_vector()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.search_vector := to_tsvector('english', 
                    COALESCE(NEW.title, '') || ' ' || 
                    COALESCE(NEW.abstract, '') || ' ' ||
                    COALESCE(array_to_string(NEW.authors, ' '), '') || ' ' ||
                    COALESCE(array_to_string(NEW.mesh_terms, ' '), '')
                );
                RETURN NEW;
            END
            $$ LANGUAGE plpgsql;
        """)
        )

        # Clinical trials search vector update function
        conn.execute(
            text("""
            CREATE OR REPLACE FUNCTION update_trials_search_vector()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.search_vector := to_tsvector('english', 
                    COALESCE(NEW.title, '') || ' ' || 
                    COALESCE(array_to_string(NEW.conditions, ' '), '') || ' ' ||
                    COALESCE(array_to_string(NEW.interventions, ' '), '') || ' ' ||
                    COALESCE(array_to_string(NEW.locations, ' '), '') || ' ' ||
                    COALESCE(array_to_string(NEW.sponsors, ' '), '')
                );
                RETURN NEW;
            END
            $$ LANGUAGE plpgsql;
        """)
        )

        # FDA drugs search vector update function
        conn.execute(
            text("""
            CREATE OR REPLACE FUNCTION update_fda_search_vector()
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
            END
            $$ LANGUAGE plpgsql;
        """)
        )

        conn.commit()
        logger.info("Database functions created successfully")


def create_database_triggers():
    """Create triggers to automatically update search vectors"""
    engine = create_engine(get_database_url())

    with engine.connect() as conn:
        logger.info("Creating database triggers...")

        # PubMed triggers
        conn.execute(
            text("""
            DROP TRIGGER IF EXISTS pubmed_search_vector_trigger ON pubmed_articles;
            CREATE TRIGGER pubmed_search_vector_trigger
            BEFORE INSERT OR UPDATE ON pubmed_articles
            FOR EACH ROW EXECUTE FUNCTION update_pubmed_search_vector();
        """)
        )

        # Clinical trials triggers
        conn.execute(
            text("""
            DROP TRIGGER IF EXISTS trials_search_vector_trigger ON clinical_trials;
            CREATE TRIGGER trials_search_vector_trigger
            BEFORE INSERT OR UPDATE ON clinical_trials
            FOR EACH ROW EXECUTE FUNCTION update_trials_search_vector();
        """)
        )

        # FDA drugs triggers
        conn.execute(
            text("""
            DROP TRIGGER IF EXISTS fda_search_vector_trigger ON fda_drugs;
            CREATE TRIGGER fda_search_vector_trigger
            BEFORE INSERT OR UPDATE ON fda_drugs
            FOR EACH ROW EXECUTE FUNCTION update_fda_search_vector();
        """)
        )

        conn.commit()
        logger.info("Database triggers created successfully")


def migrate_database():
    """Run complete database migration"""
    logger.info("Starting database migration for medical mirrors")

    try:
        # Create tables
        engine = create_engine(get_database_url())
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created")

        # Create indexes
        create_database_indexes()

        # Create functions
        create_database_functions()

        # Create triggers
        create_database_triggers()

        logger.info("Database migration completed successfully")

    except Exception as e:
        logger.error(f"Database migration failed: {e}")
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    migrate_database()
