#!/usr/bin/env python3
"""
Test FDA search API functionality
"""

import asyncio
import sys
import os
sys.path.append('/home/intelluxe/services/user/medical-mirrors')

from sqlalchemy.orm import sessionmaker
from src.database import engine
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_fda_search():
    """Test FDA search API functionality"""
    logger.info("=== Testing FDA Search API ===")
    
    try:
        # Import here to avoid the downloader initialization issue
        from src.fda.api import FDAAPI
        
        # Create session factory
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Create API instance but bypass downloader initialization for testing
        # We'll directly set the session factory and skip the downloader
        api = FDAAPI.__new__(FDAAPI)  # Create without calling __init__
        api.session_factory = SessionLocal
        
        # Test search functionality
        logger.info("Testing search for 'aspirin'...")
        aspirin_results = await api.search_drugs(generic_name="aspirin", max_results=3)
        logger.info(f"Found {len(aspirin_results)} aspirin results")
        
        if aspirin_results:
            drug = aspirin_results[0]
            logger.info("Sample aspirin drug data:")
            for key, value in drug.items():
                if value:  # Only show non-empty fields
                    logger.info(f"  {key}: {value}")
        
        # Test search for acetaminophen
        logger.info("\nTesting search for 'acetaminophen'...")
        acetaminophen_results = await api.search_drugs(generic_name="acetaminophen", max_results=2)
        logger.info(f"Found {len(acetaminophen_results)} acetaminophen results")
        
        if acetaminophen_results:
            drug = acetaminophen_results[0] 
            logger.info("Sample acetaminophen drug data:")
            for key, value in drug.items():
                if value:  # Only show non-empty fields  
                    logger.info(f"  {key}: {value}")
                    
        # Test NDC lookup
        if aspirin_results:
            ndc = aspirin_results[0]['ndc']
            logger.info(f"\nTesting NDC lookup for '{ndc}'...")
            drug_detail = await api.get_drug(ndc)
            if drug_detail:
                logger.info("Drug detail lookup successful:")
                for key, value in drug_detail.items():
                    if value:
                        logger.info(f"  {key}: {value}")
            else:
                logger.warning("Drug detail lookup returned None")
                
        # Test status 
        logger.info("\nTesting API status...")
        status = await api.get_status()
        logger.info("API Status:")
        for key, value in status.items():
            logger.info(f"  {key}: {value}")
        
        logger.info("=== FDA Search Test Completed Successfully ===")
        return True
        
    except Exception as e:
        logger.exception(f"FDA search test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_fda_search())
    sys.exit(0 if success else 1)