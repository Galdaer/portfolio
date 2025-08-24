#!/usr/bin/env python3
"""
Test FDA search with actual drug names in the database
"""

import asyncio
import sys

sys.path.append("/home/intelluxe/services/user/medical-mirrors")

import logging

from sqlalchemy.orm import sessionmaker
from src.database import engine

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_real_fda_search():
    """Test FDA search with real drug names"""
    logger.info("=== Testing FDA Search with Real Data ===")

    try:
        from src.fda.api import FDAAPI

        # Create session factory
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        # Create API instance bypassing downloader
        api = FDAAPI.__new__(FDAAPI)
        api.session_factory = SessionLocal

        # Test with budesonide (we know this exists)
        logger.info("Testing search for 'budesonide'...")
        budesonide_results = await api.search_drugs(generic_name="budesonide", max_results=3)
        logger.info(f"Found {len(budesonide_results)} budesonide results")

        if budesonide_results:
            for i, drug in enumerate(budesonide_results):
                logger.info(f"Budesonide result {i+1}:")
                for key, value in drug.items():
                    if value:
                        if isinstance(value, list):
                            logger.info(f"  {key}: {value}")
                        else:
                            logger.info(f"  {key}: {value}")
                logger.info("")

        # Test with fexofenadine
        logger.info("Testing search for 'fexofenadine'...")
        fexo_results = await api.search_drugs(generic_name="fexofenadine", max_results=2)
        logger.info(f"Found {len(fexo_results)} fexofenadine results")

        if fexo_results:
            drug = fexo_results[0]
            logger.info("Sample fexofenadine drug:")
            for key, value in drug.items():
                if value:
                    logger.info(f"  {key}: {value}")
            logger.info("")

        # Test with betamethasone
        logger.info("Testing search for 'betamethasone'...")
        beta_results = await api.search_drugs(generic_name="betamethasone", max_results=2)
        logger.info(f"Found {len(beta_results)} betamethasone results")

        if beta_results:
            drug = beta_results[0]
            logger.info("Sample betamethasone drug:")
            for key, value in drug.items():
                if value:
                    logger.info(f"  {key}: {value}")
            logger.info("")

        # Test NDC lookup if we have results
        if budesonide_results:
            ndc = budesonide_results[0]["ndc"]
            logger.info(f"Testing direct NDC lookup for '{ndc}'...")
            drug_detail = await api.get_drug(ndc)
            if drug_detail:
                logger.info("Direct NDC lookup result:")
                for key, value in drug_detail.items():
                    if value:
                        logger.info(f"  {key}: {value}")
            else:
                logger.warning("Direct NDC lookup returned None")

        logger.info("=== Real FDA Search Test Completed Successfully ===")
        return True

    except Exception as e:
        logger.exception(f"Real FDA search test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_real_fda_search())
    sys.exit(0 if success else 1)
