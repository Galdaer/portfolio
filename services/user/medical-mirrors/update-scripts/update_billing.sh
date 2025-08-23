#!/bin/bash

# Update medical billing codes (HCPCS) from NLM Clinical Tables API
# This script downloads billing codes and updates the local mirror

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Configuration
LOG_FILE="/app/logs/billing_update.log"
LOCK_FILE="/tmp/billing_update.lock"
PYTHON_ENV="/app/venv/bin/python"

# Create logs directory if it doesn't exist
mkdir -p /app/logs

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Function to cleanup
cleanup() {
    rm -f "$LOCK_FILE"
    log_message "Billing codes update cleanup completed"
}

# Set up trap to cleanup on exit
trap cleanup EXIT

# Check if already running
if [ -f "$LOCK_FILE" ]; then
    log_message "Billing codes update already running (lock file exists)"
    exit 1
fi

# Create lock file
echo $$ > "$LOCK_FILE"

log_message "Starting billing codes update"

# Change to project directory
cd "$PROJECT_DIR"

# Update billing codes
log_message "Downloading billing codes from NLM Clinical Tables API"

$PYTHON_ENV -c "
import asyncio
import sys
import logging
from src.billing_codes.downloader import BillingCodesDownloader
from src.billing_codes.parser import BillingCodesParser
from src.config import Config
from src.database import get_db_session
from sqlalchemy import text

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

async def update_billing_codes():
    config = Config()
    
    try:
        # Download codes
        async with BillingCodesDownloader(config) as downloader:
            logger.info('Starting billing codes download')
            raw_codes = await downloader.download_all_codes()
            download_stats = downloader.get_download_stats()
            
            logger.info(f'Downloaded {len(raw_codes)} raw codes')
            logger.info(f'Download stats: {download_stats}')
        
        # Parse and validate
        parser = BillingCodesParser()
        validated_codes = parser.parse_and_validate(raw_codes)
        parsing_stats = parser.get_parsing_stats()
        
        logger.info(f'Parsed {len(validated_codes)} validated codes')
        logger.info(f'Parsing stats: {parsing_stats}')
        
        # Organize by category
        categorized_codes = parser.organize_by_category(validated_codes)
        logger.info(f'Organized into {len(categorized_codes)} categories')
        
        # Insert into database
        with get_db_session() as db:
            # Clear existing data
            logger.info('Clearing existing billing codes')
            db.execute(text('DELETE FROM billing_codes'))
            
            # Insert new data
            logger.info('Inserting new billing codes')
            for code_data in validated_codes:
                db.execute(text('''
                    INSERT INTO billing_codes (
                        code, short_description, long_description, description,
                        code_type, category, coverage_notes, effective_date,
                        termination_date, is_active, modifier_required,
                        gender_specific, age_specific, bilateral_indicator,
                        source, search_text, last_updated
                    ) VALUES (
                        :code, :short_description, :long_description, :description,
                        :code_type, :category, :coverage_notes, :effective_date,
                        :termination_date, :is_active, :modifier_required,
                        :gender_specific, :age_specific, :bilateral_indicator,
                        :source, :search_text, NOW()
                    )
                '''), {
                    'code': code_data['code'],
                    'short_description': code_data['short_description'],
                    'long_description': code_data['long_description'],
                    'description': code_data['description'],
                    'code_type': code_data['code_type'],
                    'category': code_data['category'],
                    'coverage_notes': code_data['coverage_notes'],
                    'effective_date': code_data['effective_date'],
                    'termination_date': code_data['termination_date'],
                    'is_active': code_data['is_active'],
                    'modifier_required': code_data['modifier_required'],
                    'gender_specific': code_data['gender_specific'],
                    'age_specific': code_data['age_specific'],
                    'bilateral_indicator': code_data['bilateral_indicator'],
                    'source': code_data['source'],
                    'search_text': code_data['search_text']
                })
            
            db.commit()
            
            # Update statistics
            result = db.execute(text('''
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN is_active = true THEN 1 END) as active,
                    COUNT(CASE WHEN code_type = 'HCPCS' THEN 1 END) as hcpcs,
                    COUNT(CASE WHEN code_type = 'CPT' THEN 1 END) as cpt
                FROM billing_codes
            '''))
            
            stats = result.fetchone()
            logger.info(f'Successfully inserted {stats.total} billing codes')
            logger.info(f'  Active: {stats.active}, HCPCS: {stats.hcpcs}, CPT: {stats.cpt}')
        
        logger.info('Billing codes update completed successfully')
        return True
        
    except Exception as e:
        logger.error(f'Error updating billing codes: {e}')
        return False

# Run the update
if __name__ == '__main__':
    success = asyncio.run(update_billing_codes())
    sys.exit(0 if success else 1)
"

UPDATE_EXIT_CODE=$?

if [ $UPDATE_EXIT_CODE -eq 0 ]; then
    log_message "Billing codes update completed successfully"
else
    log_message "Billing codes update failed with exit code $UPDATE_EXIT_CODE"
fi

# Update last run timestamp
echo "$(date '+%Y-%m-%d %H:%M:%S')" > /app/data/.billing_last_update

log_message "Billing codes update script finished"

exit $UPDATE_EXIT_CODE