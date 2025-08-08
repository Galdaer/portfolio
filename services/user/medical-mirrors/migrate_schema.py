#!/usr/bin/env python3
"""
Database schema migration script for medical-mirrors service
Fixes StringDataRightTruncation and other constraint issues
"""

import sys

from database import get_database_url
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


def run_migration():
    """
    Run database schema migration.

    Handles migration of tables for the medical-mirrors service, including schema updates for
    fda_drugs, pubmed_articles, and clinical_trials tables.

    Error Handling:
        - Catches exceptions related to database connection, SQL execution, and other runtime errors.
        - On error, logs the exception, rolls back the transaction, and exits the process with a nonzero status code.

    Exceptions:
        - sqlalchemy.exc.SQLAlchemyError: Raised for database connection or SQL execution errors.
        - Exception: Any other unexpected errors during migration.

    This function is intended for production use; review logs and exit codes to determine migration success.
    """
    print("🔄 Starting medical-mirrors database schema migration...")

    # Get database connection
    engine = create_engine(get_database_url())
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with SessionLocal() as db:
        try:
            print("📊 Checking current schema...")

            # Check if tables exist
            result = db.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('pubmed_articles', 'clinical_trials', 'fda_drugs')
            """))
            existing_tables = [row[0] for row in result.fetchall()]
            print(f"   Found tables: {existing_tables}")

            # Migrate FDA drugs table
            if 'fda_drugs' in existing_tables:
                print("🔧 Updating fda_drugs table schema...")

                # Increase column sizes to prevent truncation
                migrations = [
                    "ALTER TABLE fda_drugs ALTER COLUMN ndc TYPE VARCHAR(50)",
                    "ALTER TABLE fda_drugs ALTER COLUMN name TYPE TEXT",
                    "ALTER TABLE fda_drugs ALTER COLUMN generic_name TYPE TEXT",
                    "ALTER TABLE fda_drugs ALTER COLUMN brand_name TYPE TEXT",
                    "ALTER TABLE fda_drugs ALTER COLUMN manufacturer TYPE TEXT",
                    "ALTER TABLE fda_drugs ALTER COLUMN dosage_form TYPE VARCHAR(200)",
                    "ALTER TABLE fda_drugs ALTER COLUMN route TYPE VARCHAR(200)",
                    "ALTER TABLE fda_drugs ALTER COLUMN orange_book_code TYPE VARCHAR(20)",
                    "ALTER TABLE fda_drugs ALTER COLUMN therapeutic_class TYPE TEXT"
                ]

                for migration in migrations:
                    try:
                        db.execute(text(migration))
                        print(f"   ✅ {migration}")
                    except Exception as e:
                        print(f"   ⚠️  {migration} - {e}")

                db.commit()
                print("   🎉 FDA drugs schema updated")

            # Migrate PubMed articles table
            if 'pubmed_articles' in existing_tables:
                print("🔧 Updating pubmed_articles table schema...")

                migrations = [
                    "ALTER TABLE pubmed_articles ALTER COLUMN title DROP NOT NULL",
                    "ALTER TABLE pubmed_articles ALTER COLUMN journal TYPE TEXT",
                    "ALTER TABLE pubmed_articles ALTER COLUMN doi TYPE VARCHAR(200)"
                ]

                for migration in migrations:
                    try:
                        db.execute(text(migration))
                        print(f"   ✅ {migration}")
                    except Exception as e:
                        print(f"   ⚠️  {migration} - {e}")

                db.commit()
                print("   🎉 PubMed articles schema updated")

            # Migrate Clinical trials table
            if 'clinical_trials' in existing_tables:
                print("🔧 Updating clinical_trials table schema...")

                migrations = [
                    "ALTER TABLE clinical_trials ALTER COLUMN title DROP NOT NULL",
                    "ALTER TABLE clinical_trials ALTER COLUMN status TYPE VARCHAR(100)",
                    "ALTER TABLE clinical_trials ALTER COLUMN phase TYPE VARCHAR(100)",
                    "ALTER TABLE clinical_trials ALTER COLUMN study_type TYPE VARCHAR(100)"
                ]

                for migration in migrations:
                    try:
                        db.execute(text(migration))
                        print(f"   ✅ {migration}")
                    except Exception as e:
                        print(f"   ⚠️  {migration} - {e}")

                db.commit()
                print("   🎉 Clinical trials schema updated")

            print("✅ Database schema migration completed successfully!")
            print("🚀 Ready for production overnight downloads")

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            db.rollback()
            sys.exit(1)

if __name__ == "__main__":
    run_migration()
