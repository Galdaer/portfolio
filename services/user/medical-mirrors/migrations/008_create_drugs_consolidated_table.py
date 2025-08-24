#!/usr/bin/env python3
"""
Migration 008: Create drugs_consolidated table

This migration creates a new consolidated drugs table that groups all formulations
of the same generic drug into a single record with structured data. This solves
the duplication problem where we have 141K records for only 20K unique drugs.

Key improvements:
- Single record per generic drug (20K instead of 141K records)
- All formulations stored as structured JSONB array
- Consolidated clinical information with conflict resolution
- Data quality scoring for clinical reliability
- Preserved detailed information in structured format
"""

import sys
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from database import get_database_url, engine
from sqlalchemy import text


def upgrade():
    """Create consolidated drugs table"""
    print("Creating drugs_consolidated table...")
    
    with engine.connect() as conn:
        # Create the consolidated drugs table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS drugs_consolidated (
            id SERIAL PRIMARY KEY,
            generic_name TEXT NOT NULL UNIQUE,
            
            -- Aggregated product variations
            brand_names TEXT[] DEFAULT '{}', -- All brand names for this generic
            manufacturers TEXT[] DEFAULT '{}', -- All manufacturers  
            formulations JSONB DEFAULT '[]', -- [{strength, dosage_form, route, ndc, brand_name, manufacturer}]
            
            -- Consolidated clinical information (single authoritative values)
            therapeutic_class TEXT, -- Most common/authoritative value
            indications_and_usage TEXT, -- Longest/most complete version
            mechanism_of_action TEXT, -- Longest/most complete version
            contraindications TEXT[] DEFAULT '{}', -- Merged unique values
            warnings TEXT[] DEFAULT '{}', -- Merged unique values
            precautions TEXT[] DEFAULT '{}', -- Merged unique values
            adverse_reactions TEXT[] DEFAULT '{}', -- Merged unique values
            drug_interactions JSONB DEFAULT '{}', -- Merged interaction data
            
            -- Additional clinical fields (consolidated)
            dosage_and_administration TEXT,
            pharmacokinetics TEXT,
            pharmacodynamics TEXT,
            boxed_warning TEXT,
            clinical_studies TEXT,
            pediatric_use TEXT,
            geriatric_use TEXT,
            pregnancy TEXT,
            nursing_mothers TEXT,
            overdosage TEXT,
            nonclinical_toxicology TEXT,
            
            -- Regulatory information (aggregated)
            approval_dates TEXT[], -- All approval dates found
            orange_book_codes TEXT[], -- All therapeutic equivalence codes
            application_numbers TEXT[], -- All FDA application numbers
            
            -- Metadata and quality metrics
            total_formulations INTEGER DEFAULT 0,
            data_sources TEXT[] DEFAULT '{}', -- All contributing sources (ndc, orange_book, drugs_fda, labels)
            confidence_score FLOAT DEFAULT 0.0, -- Quality metric (0-1) based on data completeness
            has_clinical_data BOOLEAN DEFAULT FALSE, -- Quick flag for clinical information availability
            
            -- Timestamps
            created_at TIMESTAMP DEFAULT NOW(),
            last_updated TIMESTAMP DEFAULT NOW(),
            
            -- Search optimization
            search_vector TSVECTOR
        );
        """
        
        conn.execute(text(create_table_sql))
        print("  ✅ Created drugs_consolidated table")
        
        # Create indexes for performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_drugs_consolidated_generic_name ON drugs_consolidated (generic_name);",
            "CREATE INDEX IF NOT EXISTS idx_drugs_consolidated_therapeutic_class ON drugs_consolidated (therapeutic_class);", 
            "CREATE INDEX IF NOT EXISTS idx_drugs_consolidated_search_vector ON drugs_consolidated USING GIN (search_vector);",
            "CREATE INDEX IF NOT EXISTS idx_drugs_consolidated_confidence ON drugs_consolidated (confidence_score DESC);",
            "CREATE INDEX IF NOT EXISTS idx_drugs_consolidated_clinical ON drugs_consolidated (has_clinical_data) WHERE has_clinical_data = TRUE;",
            "CREATE INDEX IF NOT EXISTS idx_drugs_consolidated_brands ON drugs_consolidated USING GIN (brand_names);",
            "CREATE INDEX IF NOT EXISTS idx_drugs_consolidated_manufacturers ON drugs_consolidated USING GIN (manufacturers);"
        ]
        
        for index_sql in indexes:
            try:
                conn.execute(text(index_sql))
                index_name = index_sql.split()[5]  # Extract index name
                print(f"  ✅ Created index: {index_name}")
            except Exception as e:
                print(f"  ⚠️  Index creation failed: {e}")
        
        # Create function to update search vector automatically
        search_trigger_sql = """
        CREATE OR REPLACE FUNCTION update_drugs_consolidated_search_vector() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := to_tsvector('english', 
                COALESCE(NEW.generic_name, '') || ' ' ||
                COALESCE(array_to_string(NEW.brand_names, ' '), '') || ' ' ||
                COALESCE(array_to_string(NEW.manufacturers, ' '), '') || ' ' ||
                COALESCE(NEW.therapeutic_class, '') || ' ' ||
                COALESCE(NEW.indications_and_usage, '')
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS drugs_consolidated_search_vector_update ON drugs_consolidated;
        CREATE TRIGGER drugs_consolidated_search_vector_update 
            BEFORE INSERT OR UPDATE ON drugs_consolidated
            FOR EACH ROW EXECUTE FUNCTION update_drugs_consolidated_search_vector();
        """
        
        conn.execute(text(search_trigger_sql))
        print("  ✅ Created search vector trigger")
        
        conn.commit()
        print("✅ drugs_consolidated table created successfully!")


def downgrade():
    """Remove drugs_consolidated table"""
    print("Dropping drugs_consolidated table...")
    
    with engine.connect() as conn:
        # Drop trigger and function
        conn.execute(text("DROP TRIGGER IF EXISTS drugs_consolidated_search_vector_update ON drugs_consolidated;"))
        conn.execute(text("DROP FUNCTION IF EXISTS update_drugs_consolidated_search_vector();"))
        
        # Drop table (cascades to indexes)
        conn.execute(text("DROP TABLE IF EXISTS drugs_consolidated CASCADE;"))
        
        conn.commit()
        print("✅ drugs_consolidated table dropped!")


if __name__ == "__main__":
    print("Drug Information Consolidation Migration 008")
    print("===========================================")
    upgrade()