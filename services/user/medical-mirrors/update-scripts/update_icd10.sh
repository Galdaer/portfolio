#!/bin/bash

# Update ICD-10 diagnostic codes from NLM Clinical Tables API
# This script downloads ICD-10 codes and updates the local mirror

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Configuration
LOG_FILE="/app/logs/icd10_update.log"
LOCK_FILE="/tmp/icd10_update.lock"
PYTHON_ENV="/usr/local/bin/python"

# Create logs directory if it doesn't exist
mkdir -p /app/logs

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Function to cleanup
cleanup() {
    rm -f "$LOCK_FILE"
    log_message "ICD-10 update cleanup completed"
}

# Set up trap to cleanup on exit
trap cleanup EXIT

# Check if already running
if [ -f "$LOCK_FILE" ]; then
    log_message "ICD-10 update already running (lock file exists)"
    exit 1
fi

# Create lock file
echo $$ > "$LOCK_FILE"

log_message "Starting ICD-10 codes update"

# Change to project directory
cd "$PROJECT_DIR"

# Handle quick test mode
if [ "$QUICK_TEST" = "true" ]; then
    log_message "Running ICD-10 update in QUICK TEST mode (limited to 100 codes)"
    LIMIT_CODES=100
else
    log_message "Running ICD-10 update in FULL mode"
    LIMIT_CODES=0
fi

# Update ICD-10 codes
log_message "Downloading ICD-10 codes from NLM Clinical Tables API"

$PYTHON_ENV -c "
import asyncio
import sys
import os
import logging
import json
from pathlib import Path
from src.icd10.smart_downloader import SmartICD10Downloader
from src.icd10.parser import ICD10Parser
from src.icd10.database_loader import ICD10DatabaseLoader
from src.config import Config
from src.database import get_db_session
from sqlalchemy import text

# Get limit from environment variable
limit_codes = int(os.getenv('LIMIT_CODES', 0)) or $LIMIT_CODES

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('$LOG_FILE'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def update_icd10_codes():
    config = Config()
    
    try:
        # Use smart downloader with automatic state management and retries
        output_dir = Path('/app/data/icd10')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        async with SmartICD10Downloader(output_dir=output_dir, config=config) as downloader:
            logger.info('Starting smart ICD-10 download with automatic retry handling')
            
            # Force fresh download if QUICK_TEST to avoid using cached state
            force_fresh = bool(limit_codes > 0)
            
            summary = await downloader.download_all_icd10_codes(force_fresh=force_fresh)
            
            logger.info(f'Smart download completed: {summary[\"total_codes\"]} codes from {summary[\"successful_sources\"]} sources')
            logger.info(f'Success rate: {summary[\"success_rate\"]:.1f}%')
            
            if summary[\"failed_sources\"] > 0:
                logger.warning(f'Failed sources: {summary[\"failed_sources\"]} (will retry automatically)')
            
            if summary[\"rate_limited_sources\"] > 0:
                logger.info(f'Rate limited sources: {summary[\"rate_limited_sources\"]} (will retry in background)')
            
        # Load the downloaded and validated codes
        all_codes_file = output_dir / 'all_icd10_codes_complete.json'
        if not all_codes_file.exists():
            logger.error('No ICD-10 codes were downloaded')
            return False
            
        with open(all_codes_file, 'r') as f:
            validated_codes = json.load(f)
        
        # Limit for quick test
        if limit_codes > 0:
            logger.info(f'Limiting to first {limit_codes} codes for quick test')
            validated_codes = validated_codes[:limit_codes]
        
        # Parse codes with enhanced category population
        logger.info('Parsing and validating ICD-10 codes with enhanced category extraction')
        parser = ICD10Parser()
        parsed_codes = parser.parse_and_validate(validated_codes)
        
        logger.info(f'Processing {len(parsed_codes)} parsed codes with enhanced data')
        
        # Use enhanced database loader for proper field coverage
        loader = ICD10DatabaseLoader()
        stats = loader.load_codes(parsed_codes)
        
        logger.info(f'Database loading completed:')
        logger.info(f'  - Processed: {stats["processed"]} codes')
        logger.info(f'  - Total in DB: {stats["total_in_db"]} codes')
        logger.info(f'  - Category coverage: {stats["category_coverage"]} codes')
        logger.info(f'  - Search vector coverage: {stats["search_vector_coverage"]} codes')
        
        # Final validation - check field coverage
        with get_db_session() as db:
            result = db.execute(text('''
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN category IS NOT NULL AND category != '' THEN 1 END) as with_category,
                    COUNT(CASE WHEN search_vector IS NOT NULL THEN 1 END) as with_search_vector
                FROM icd10_codes
            ''')).fetchone()
            
            category_pct = result.with_category / result.total * 100 if result.total > 0 else 0
            search_pct = result.with_search_vector / result.total * 100 if result.total > 0 else 0
            
            logger.info(f'✅ FINAL DATA QUALITY:')
            logger.info(f'   Category coverage: {result.with_category}/{result.total} ({category_pct:.1f}%)')
            logger.info(f'   Search vector coverage: {result.with_search_vector}/{result.total} ({search_pct:.1f}%)')
            
            if category_pct >= 95.0:
                logger.info('🎉 SUCCESS: Achieved >95% category coverage!')
            else:
                logger.warning(f'⚠️  Category coverage still low: {category_pct:.1f}%')
        
        logger.info('ICD-10 update completed successfully')
        return True
        
    except Exception as e:
        logger.error(f'Error updating ICD-10 codes: {e}')
        return False

# Run the update
if __name__ == '__main__':
    success = asyncio.run(update_icd10_codes())
    sys.exit(0 if success else 1)
"

UPDATE_EXIT_CODE=$?

if [ $UPDATE_EXIT_CODE -eq 0 ]; then
    log_message "ICD-10 update completed successfully"
else
    log_message "ICD-10 update failed with exit code $UPDATE_EXIT_CODE"
fi

# Update last run timestamp
echo "$(date '+%Y-%m-%d %H:%M:%S')" > /app/data/.icd10_last_update

log_message "ICD-10 update script finished"

exit $UPDATE_EXIT_CODE