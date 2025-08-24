#!/usr/bin/env python3
"""
Test FDA data integration to verify all 4 sources are properly merged
"""

import asyncio
import sys

sys.path.append("/home/intelluxe/services/user/medical-mirrors")

import logging

from sqlalchemy.orm import sessionmaker
from src.database import engine, get_database_session
from src.fda.api import FDAAPI

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_fda_integration():
    """Test FDA data integration with all 4 sources"""
    logger.info("=== Testing FDA Data Integration ===")

    # Create session factory for FDA API
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    fda_api = FDAAPI(session_factory=SessionLocal)

    try:
        # Test a quick update with limit to see merging in action
        logger.info("Triggering quick FDA test update...")
        result = await fda_api.trigger_update(quick_test=True, limit=100)
        logger.info(f"Update result: {result}")

        # Test search functionality
        logger.info("Testing search for common drugs...")

        # Search for aspirin (should be in multiple sources)
        aspirin_results = await fda_api.search_drugs(generic_name="aspirin", max_results=5)
        logger.info(f"Found {len(aspirin_results)} aspirin results")

        if aspirin_results:
            drug = aspirin_results[0]
            logger.info("Sample aspirin drug data:")
            for key, value in drug.items():
                if value:  # Only show non-empty fields
                    logger.info(f"  {key}: {value}")

        # Search for acetaminophen (another common drug)
        acetaminophen_results = await fda_api.search_drugs(generic_name="acetaminophen", max_results=3)
        logger.info(f"Found {len(acetaminophen_results)} acetaminophen results")

        if acetaminophen_results:
            drug = acetaminophen_results[0]
            logger.info("Sample acetaminophen drug data:")
            for key, value in drug.items():
                if value:  # Only show non-empty fields
                    logger.info(f"  {key}: {value}")

        # Check database statistics
        db = get_database_session()
        try:
            from sqlalchemy import func, text
            from src.database import FDADrug

            # Total drug count
            total_count = db.query(func.count(FDADrug.ndc)).scalar()
            logger.info(f"Total drugs in database: {total_count}")

            # Count drugs with data from multiple sources
            multi_source_query = text("""
                SELECT COUNT(*)
                FROM fda_drugs
                WHERE array_length(data_sources, 1) > 1
            """)
            multi_source_count = db.execute(multi_source_query).scalar()
            logger.info(f"Drugs with data from multiple sources: {multi_source_count}")

            # Show sample of data sources
            sources_query = text("""
                SELECT data_sources, COUNT(*) as count
                FROM fda_drugs
                WHERE data_sources IS NOT NULL
                GROUP BY data_sources
                ORDER BY count DESC
                LIMIT 10
            """)
            sources_result = db.execute(sources_query)
            logger.info("Data source combinations:")
            for row in sources_result:
                logger.info(f"  {row[0]}: {row[1]} drugs")

        finally:
            db.close()

        logger.info("=== FDA Integration Test Completed ===")
        return True

    except Exception as e:
        logger.exception(f"FDA integration test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_fda_integration())
    sys.exit(0 if success else 1)
