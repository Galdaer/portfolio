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
from src.icd10.downloader import ICD10Downloader
from src.icd10.parser import ICD10Parser
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
        # Download codes
        async with ICD10Downloader(config) as downloader:
            logger.info('Starting ICD-10 download')
            raw_codes = await downloader.download_all_codes()
            download_stats = downloader.get_download_stats()
            
            logger.info(f'Downloaded {len(raw_codes)} raw codes')
            logger.info(f'Download stats: {download_stats}')
        
        # Parse and validate
        parser = ICD10Parser()
        validated_codes = parser.parse_and_validate(raw_codes)
        parsing_stats = parser.get_parsing_stats()
        
        logger.info(f'Parsed {len(validated_codes)} validated codes')
        logger.info(f'Parsing stats: {parsing_stats}')
        
        # Limit for quick test
        if limit_codes > 0:
            logger.info(f'Limiting to first {limit_codes} codes for quick test')
            validated_codes = validated_codes[:limit_codes]
        
        # Build hierarchy
        codes_with_hierarchy = parser.build_hierarchy(validated_codes)
        
        # Insert/Update into database using UPSERT
        with get_db_session() as db:
            logger.info('Upserting ICD-10 codes (preserving existing data)')
            
            # Use UPSERT to preserve existing data and only update with better information
            for code_data in codes_with_hierarchy:
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
                    'code': code_data['code'],
                    'description': code_data['description'],
                    'category': code_data['category'],
                    'chapter': code_data['chapter'],
                    'synonyms': json.dumps(code_data['synonyms']) if code_data['synonyms'] else '[]',
                    'inclusion_notes': json.dumps(code_data['inclusion_notes']) if code_data['inclusion_notes'] else '[]',
                    'exclusion_notes': json.dumps(code_data['exclusion_notes']) if code_data['exclusion_notes'] else '[]',
                    'is_billable': code_data['is_billable'],
                    'code_length': code_data['code_length'],
                    'parent_code': code_data['parent_code'],
                    'children_codes': json.dumps(code_data['children_codes']) if code_data['children_codes'] else '[]',
                    'source': code_data['source'],
                    'search_text': code_data['search_text']
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