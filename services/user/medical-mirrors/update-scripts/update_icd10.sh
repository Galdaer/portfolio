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
        
        logger.info(f'Processing {len(validated_codes)} validated codes for database insertion')
        
        # Insert/Update into database using UPSERT
        with get_db_session() as db:
            logger.info('Upserting ICD-10 codes (preserving existing data)')
            
            # Use UPSERT to preserve existing data and only update with better information
            for code_data in validated_codes:
                db.execute(text('''
                    INSERT INTO icd10_codes (
                        code, description, category, chapter, synonyms,
                        inclusion_notes, exclusion_notes, is_billable,
                        code_length, parent_code, children_codes,
                        source, search_text, last_updated
                    ) VALUES (
                        :code, :description, :category, :chapter, :synonyms,
                        :inclusion_notes, :exclusion_notes, :is_billable,
                        :code_length, :parent_code, :children_codes,
                        :source, :search_text, NOW()
                    )
                    ON CONFLICT (code) DO UPDATE SET
                        -- Only update if we have better/more complete information
                        description = COALESCE(NULLIF(EXCLUDED.description, ''), icd10_codes.description),
                        category = COALESCE(NULLIF(EXCLUDED.category, ''), icd10_codes.category),
                        chapter = COALESCE(NULLIF(EXCLUDED.chapter, ''), icd10_codes.chapter),
                        synonyms = COALESCE(NULLIF(EXCLUDED.synonyms, '[]'::jsonb), icd10_codes.synonyms),
                        inclusion_notes = COALESCE(NULLIF(EXCLUDED.inclusion_notes, '[]'::jsonb), icd10_codes.inclusion_notes),
                        exclusion_notes = COALESCE(NULLIF(EXCLUDED.exclusion_notes, '[]'::jsonb), icd10_codes.exclusion_notes),
                        is_billable = COALESCE(EXCLUDED.is_billable, icd10_codes.is_billable),
                        code_length = COALESCE(EXCLUDED.code_length, icd10_codes.code_length),
                        parent_code = COALESCE(NULLIF(EXCLUDED.parent_code, ''), icd10_codes.parent_code),
                        children_codes = COALESCE(NULLIF(EXCLUDED.children_codes, '[]'::jsonb), icd10_codes.children_codes),
                        source = COALESCE(NULLIF(EXCLUDED.source, ''), icd10_codes.source),
                        search_text = COALESCE(NULLIF(EXCLUDED.search_text, ''), icd10_codes.search_text),
                        last_updated = NOW()
                '''), {
                    'code': code_data.get('code', ''),
                    'description': code_data.get('description', ''),
                    'category': code_data.get('category', ''),
                    'chapter': code_data.get('chapter', ''),
                    'synonyms': json.dumps(code_data.get('synonyms', [])),
                    'inclusion_notes': json.dumps(code_data.get('inclusion_notes', [])),
                    'exclusion_notes': json.dumps(code_data.get('exclusion_notes', [])),
                    'is_billable': code_data.get('is_billable', False),
                    'code_length': code_data.get('code_length', 0),
                    'parent_code': code_data.get('parent_code', ''),
                    'children_codes': json.dumps(code_data.get('children_codes', [])),
                    'source': code_data.get('source', 'smart_icd10_downloader'),
                    'search_text': code_data.get('search_text', code_data.get('description', ''))
                })
            
            db.commit()
            
            # Update statistics
            result = db.execute(text('SELECT COUNT(*) as total FROM icd10_codes'))
            total_count = result.fetchone().total
            
            logger.info(f'Successfully inserted {total_count} ICD-10 codes')
        
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