#!/usr/bin/env python3
"""
Test script for DrugCentral PostgreSQL database connection
Tests basic connectivity and sample queries
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent))

from enhanced_drug_sources.drugcentral_downloader import SmartDrugCentralDownloader
from config import Config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_drugcentral_connection():
    """Test DrugCentral PostgreSQL connection and sample queries"""
    config = Config()
    
    logger.info("Testing DrugCentral PostgreSQL connection...")
    logger.info(f"Host: {config.DRUGCENTRAL_DB_HOST}:{config.DRUGCENTRAL_DB_PORT}")
    logger.info(f"Database: {config.DRUGCENTRAL_DB_NAME}")
    logger.info(f"User: {config.DRUGCENTRAL_DB_USER}")
    
    async with SmartDrugCentralDownloader(config=config) as downloader:
        try:
            # Test basic connection
            logger.info("Testing database connection...")
            
            # Test mechanism of action query
            logger.info("\n=== Testing Mechanism of Action Query ===")
            moa_file = await downloader.download_mechanism_of_action_data()
            if moa_file:
                logger.info(f"✅ MOA data saved to: {moa_file}")
            else:
                logger.warning("❌ Failed to download MOA data")
            
            # Test drug target query
            logger.info("\n=== Testing Drug Target Query ===")
            target_file = await downloader.download_drug_target_data()
            if target_file:
                logger.info(f"✅ Drug target data saved to: {target_file}")
            else:
                logger.warning("❌ Failed to download drug target data")
            
            # Test pharmacology query
            logger.info("\n=== Testing Pharmacology Query ===")
            pharm_file = await downloader.download_pharmacology_data()
            if pharm_file:
                logger.info(f"✅ Pharmacology data saved to: {pharm_file}")
            else:
                logger.warning("❌ Failed to download pharmacology data")
            
            # Get final status
            status = await downloader.get_download_status()
            logger.info(f"\n=== Final Status ===")
            logger.info(f"Files downloaded: {status['files_downloaded']}")
            logger.info(f"Successful downloads: {status['progress']['successful_downloads']}")
            logger.info(f"Failed downloads: {status['progress']['failed_downloads']}")
            
            if status['progress']['successful_downloads'] > 0:
                logger.info("🎉 DrugCentral connection test PASSED!")
                return True
            else:
                logger.error("❌ DrugCentral connection test FAILED - no successful downloads")
                return False
                
        except Exception as e:
            logger.error(f"❌ DrugCentral connection test FAILED with error: {e}")
            return False


if __name__ == "__main__":
    success = asyncio.run(test_drugcentral_connection())
    sys.exit(0 if success else 1)