#!/usr/bin/env python3
"""
Migration 007: Rename fda_drugs table to drug_information

This migration renames the fda_drugs table to drug_information to better reflect
the expanded scope beyond pure FDA data. The table now includes:
- FDA data (NDC, Orange Book, drug labels)
- RxClass therapeutic classifications (NLM)
- Potential future sources (DailyMed, interaction databases)

This is part of the architectural refactoring from FDA-specific to
comprehensive drug information system.
"""

import sys
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from sqlalchemy import text

from database import engine


def upgrade():
    """Rename fda_drugs table to drug_information"""
    print("Renaming fda_drugs table to drug_information...")

    with engine.connect() as conn:
        # Check if old table exists and new table doesn't
        check_old_table = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'fda_drugs'
            )
        """)).fetchone()[0]

        check_new_table = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'drug_information'
            )
        """)).fetchone()[0]

        if not check_old_table:
            print("  ⚠️  fda_drugs table does not exist, skipping migration")
            return

        if check_new_table:
            print("  ⚠️  drug_information table already exists, skipping migration")
            return

        print("  🔄 Renaming table fda_drugs -> drug_information...")
        conn.execute(text("ALTER TABLE fda_drugs RENAME TO drug_information"))

        print("  🔄 Renaming primary key constraint...")
        conn.execute(text("""
            ALTER TABLE drug_information
            RENAME CONSTRAINT fda_drugs_pkey TO drug_information_pkey
        """))

        print("  🔄 Renaming indexes...")
        # Rename indexes to match new table name
        indexes_to_rename = [
            ("idx_fda_drugs_ndc", "idx_drug_information_ndc"),
            ("idx_fda_drugs_generic_name", "idx_drug_information_generic_name"),
            ("idx_fda_drugs_brand_name", "idx_drug_information_brand_name"),
            ("idx_fda_drugs_search_vector", "idx_drug_information_search_vector"),
            ("idx_fda_drugs_therapeutic_class", "idx_drug_information_therapeutic_class"),
        ]

        for old_idx, new_idx in indexes_to_rename:
            try:
                conn.execute(text(f"ALTER INDEX {old_idx} RENAME TO {new_idx}"))
                print(f"    ✅ Renamed index: {old_idx} -> {new_idx}")
            except Exception as e:
                if "does not exist" in str(e).lower():
                    print(f"    ⚠️  Index {old_idx} does not exist, skipping")
                else:
                    print(f"    ❌ Failed to rename index {old_idx}: {e}")

        conn.commit()
        print("✅ Table successfully renamed to drug_information!")


def downgrade():
    """Revert drug_information table back to fda_drugs"""
    print("Reverting drug_information table back to fda_drugs...")

    with engine.connect() as conn:
        # Check if new table exists and old table doesn't
        check_new_table = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'drug_information'
            )
        """)).fetchone()[0]

        check_old_table = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'fda_drugs'
            )
        """)).fetchone()[0]

        if not check_new_table:
            print("  ⚠️  drug_information table does not exist, skipping rollback")
            return

        if check_old_table:
            print("  ⚠️  fda_drugs table already exists, skipping rollback")
            return

        print("  🔄 Renaming table drug_information -> fda_drugs...")
        conn.execute(text("ALTER TABLE drug_information RENAME TO fda_drugs"))

        print("  🔄 Renaming primary key constraint...")
        conn.execute(text("""
            ALTER TABLE fda_drugs
            RENAME CONSTRAINT drug_information_pkey TO fda_drugs_pkey
        """))

        print("  🔄 Renaming indexes...")
        # Revert index names
        indexes_to_revert = [
            ("idx_drug_information_ndc", "idx_fda_drugs_ndc"),
            ("idx_drug_information_generic_name", "idx_fda_drugs_generic_name"),
            ("idx_drug_information_brand_name", "idx_fda_drugs_brand_name"),
            ("idx_drug_information_search_vector", "idx_fda_drugs_search_vector"),
            ("idx_drug_information_therapeutic_class", "idx_fda_drugs_therapeutic_class"),
        ]

        for old_idx, new_idx in indexes_to_revert:
            try:
                conn.execute(text(f"ALTER INDEX {old_idx} RENAME TO {new_idx}"))
                print(f"    ✅ Reverted index: {old_idx} -> {new_idx}")
            except Exception as e:
                if "does not exist" in str(e).lower():
                    print(f"    ⚠️  Index {old_idx} does not exist, skipping")
                else:
                    print(f"    ❌ Failed to revert index {old_idx}: {e}")

        conn.commit()
        print("✅ Table successfully reverted to fda_drugs!")


if __name__ == "__main__":
    print("Drug Information Database Migration 007")
    print("======================================")
    upgrade()
