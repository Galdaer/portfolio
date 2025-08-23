#!/usr/bin/env python3
"""
Simple FDA data integration test to verify database schema and search functionality
"""

import sys
import os
sys.path.append('/home/intelluxe/services/user/medical-mirrors')

from sqlalchemy import text, func
from src.database import get_database_session, FDADrug
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_fda_schema():
    """Test FDA database schema and verify new columns are present"""
    logger.info("=== Testing FDA Database Schema ===")
    
    db = get_database_session()
    try:
        # Test that the enhanced columns exist by querying for them
        test_query = text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'fda_drugs' 
            AND column_name IN (
                'applicant', 'strength', 'application_number', 
                'product_number', 'reference_listed_drug', 
                'pharmacologic_class', 'data_sources'
            )
            ORDER BY column_name
        """)
        
        result = db.execute(test_query)
        columns = result.fetchall()
        
        logger.info("Enhanced FDA columns found:")
        for column in columns:
            logger.info(f"  {column.column_name}: {column.data_type} (nullable: {column.is_nullable})")
        
        if len(columns) == 7:  # All 7 new columns should be present
            logger.info("✅ All enhanced FDA columns are present")
        else:
            logger.warning(f"❌ Expected 7 columns, found {len(columns)}")
            return False
            
        # Test search vector trigger exists
        trigger_query = text("""
            SELECT trigger_name, event_manipulation 
            FROM information_schema.triggers 
            WHERE trigger_name = 'fda_drugs_search_vector_update'
        """)
        
        trigger_result = db.execute(trigger_query)
        triggers = trigger_result.fetchall()
        
        if triggers:
            logger.info("✅ FDA search vector trigger is present")
            for trigger in triggers:
                logger.info(f"  {trigger.trigger_name}: {trigger.event_manipulation}")
        else:
            logger.warning("❌ FDA search vector trigger not found")
            return False
        
        # Test basic database connectivity and table structure
        count_query = db.query(func.count(FDADrug.ndc))
        total_drugs = count_query.scalar()
        logger.info(f"Total FDA drugs in database: {total_drugs}")
        
        # Test that we can query the enhanced fields
        if total_drugs > 0:
            sample_query = text("""
                SELECT ndc, name, generic_name, applicant, strength, 
                       application_number, data_sources
                FROM fda_drugs 
                WHERE applicant IS NOT NULL OR strength IS NOT NULL 
                   OR application_number IS NOT NULL
                LIMIT 5
            """)
            sample_result = db.execute(sample_query)
            samples = sample_result.fetchall()
            
            logger.info(f"Sample drugs with enhanced data ({len(samples)} found):")
            for drug in samples:
                logger.info(f"  NDC: {drug.ndc}")
                logger.info(f"    Name: {drug.name}")
                logger.info(f"    Generic: {drug.generic_name}")
                logger.info(f"    Applicant: {drug.applicant}")
                logger.info(f"    Strength: {drug.strength}")
                logger.info(f"    App Number: {drug.application_number}")
                logger.info(f"    Sources: {drug.data_sources}")
                logger.info("")
        
        logger.info("=== FDA Schema Test Completed Successfully ===")
        return True
        
    except Exception as e:
        logger.exception(f"FDA schema test failed: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = test_fda_schema()
    sys.exit(0 if success else 1)