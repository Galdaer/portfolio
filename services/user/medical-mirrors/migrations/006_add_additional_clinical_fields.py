#!/usr/bin/env python3
"""
Migration 006: Add additional clinical fields to fda_drugs table

Adds new fields discovered from comprehensive drug label analysis:
- boxed_warning: FDA black box warnings
- clinical_studies: Clinical trial data and efficacy results  
- pediatric_use: Pediatric usage information
- geriatric_use: Geriatric usage information
- pregnancy: Pregnancy category and safety information
- nursing_mothers: Lactation safety information
- overdosage: Overdose symptoms and treatment
- nonclinical_toxicology: Animal study data
"""

import sys
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from database import get_database_url, engine
from sqlalchemy import text


def upgrade():
    """Add new clinical fields to fda_drugs table"""
    print("Adding additional clinical fields to fda_drugs table...")
    
    with engine.connect() as conn:
        # Add the new clinical fields
        new_fields = [
            "boxed_warning TEXT",
            "clinical_studies TEXT",
            "pediatric_use TEXT",
            "geriatric_use TEXT",
            "pregnancy TEXT",
            "nursing_mothers TEXT",
            "overdosage TEXT",
            "nonclinical_toxicology TEXT"
        ]
        
        for field in new_fields:
            try:
                conn.execute(text(f"ALTER TABLE fda_drugs ADD COLUMN {field}"))
                print(f"  ✅ Added column: {field.split()[0]}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"  ⚠️  Column {field.split()[0]} already exists, skipping")
                else:
                    print(f"  ❌ Failed to add {field.split()[0]}: {e}")
                    raise
        
        conn.commit()
        print("✅ Migration completed successfully!")


def downgrade():
    """Remove the added clinical fields (rollback)"""
    print("Rolling back additional clinical fields...")
    
    with engine.connect() as conn:
        field_names = [
            "boxed_warning",
            "clinical_studies",
            "pediatric_use", 
            "geriatric_use",
            "pregnancy",
            "nursing_mothers",
            "overdosage",
            "nonclinical_toxicology"
        ]
        
        for field_name in field_names:
            try:
                conn.execute(text(f"ALTER TABLE fda_drugs DROP COLUMN IF EXISTS {field_name}"))
                print(f"  ✅ Dropped column: {field_name}")
            except Exception as e:
                print(f"  ❌ Failed to drop {field_name}: {e}")
        
        conn.commit()
        print("✅ Rollback completed!")


if __name__ == "__main__":
    print("FDA Drug Database Migration 006")
    print("================================")
    upgrade()