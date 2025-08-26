#!/usr/bin/env python3
"""
Process existing FDA data without re-downloading
Uses the medical-mirrors optimized parser to extract clinical fields from existing data
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add medical-mirrors src to path
sys.path.insert(0, "/home/intelluxe/services/user/medical-mirrors/src")

from drugs.api import DrugAPI
from database import get_db_session
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def process_existing_fda_data():
    """Process existing FDA data files"""
    logger.info("Processing existing FDA data with optimized clinical field extraction")
    
    config = Config()
    session_factory = get_db_session
    
    # Initialize drug API with optimized parser enabled
    drug_api = DrugAPI(session_factory, config, enable_downloader=False)
    
    # Process existing datasets
    data_dir = "/home/intelluxe/database/medical_complete/fda"
    datasets = {
        "labels": f"{data_dir}/labels",
        "ndc": f"{data_dir}/ndc", 
        "drugs_fda": f"{data_dir}/drugs_fda",
        "orange_book": f"{data_dir}/orange_book"
    }
    
    db = session_factory()
    total_processed = 0
    
    try:
        for dataset_name, data_path in datasets.items():
            if os.path.exists(data_path):
                logger.info(f"Processing {dataset_name} from {data_path}")
                processed = await drug_api.process_fda_dataset(dataset_name, data_path, db)
                total_processed += processed
                logger.info(f"Processed {processed} records from {dataset_name}")
            else:
                logger.warning(f"Dataset {dataset_name} not found at {data_path}")
    
        logger.info(f"✅ Total processed: {total_processed} drug records")
        return total_processed
        
    except Exception as e:
        logger.exception(f"Error processing FDA data: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    result = asyncio.run(process_existing_fda_data())
    print(f"Processed {result} drug records")