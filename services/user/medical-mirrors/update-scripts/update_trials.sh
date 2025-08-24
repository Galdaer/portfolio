#!/bin/bash
# Update script for ClinicalTrials.gov data
# Should be run weekly via cron job

set -e

LOG_FILE="/app/logs/trials_update.log"
PYTHON_PATH="/app/src"

echo "$(date): Starting ClinicalTrials update" >> $LOG_FILE

cd /app

# Set Python path
export PYTHONPATH=$PYTHON_PATH

# Run ClinicalTrials update
python3 -c "
import asyncio
import sys
import os
import logging
import json
from pathlib import Path
sys.path.append('$PYTHON_PATH')
from src.clinicaltrials.smart_downloader import SmartClinicalTrialsDownloader
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

async def update_trials():
    config = Config()
    
    try:
        # Use smart downloader with automatic state management and retries
        output_dir = Path('/app/data/clinicaltrials')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        async with SmartClinicalTrialsDownloader(output_dir=output_dir, config=config) as downloader:
            logger.info('Starting smart ClinicalTrials download with automatic retry handling')
            
            # Download complete dataset for ClinicalTrials
            summary = await downloader.download_all_clinical_trials(force_fresh=False, complete_dataset=True)
            
            logger.info(f'Smart download completed: {summary[\\\"total_studies\\\"]} studies from {summary[\\\"total_files\\\"]} files')
            logger.info(f'Success rate: {summary[\\\"success_rate\\\"]:.1f}%')
            
            if summary[\\\"failed_sources\\\"] > 0:
                logger.warning(f'Failed sources: {summary[\\\"failed_sources\\\"]} (will retry automatically)')
            
            if summary[\\\"rate_limited_sources\\\"] > 0:
                logger.info(f'Rate limited sources: {summary[\\\"rate_limited_sources\\\"]} (will retry in background)')
            
        # Load the downloaded and validated studies
        all_studies_file = output_dir / 'all_clinical_trials_complete.json'
        if not all_studies_file.exists():
            logger.error('No clinical trials were downloaded')
            return False
            
        with open(all_studies_file, 'r') as f:
            validated_studies = json.load(f)
        
        logger.info(f'Processing {len(validated_studies)} validated studies for database insertion')
        
        # Insert/Update into database using UPSERT
        with get_db_session() as db:
            logger.info('Upserting clinical trials (preserving existing data)')
            
            # Use UPSERT to preserve existing data and only update with better information
            for study_data in validated_studies:
                db.execute(text('''
                    INSERT INTO clinical_trials (
                        nct_id, brief_title, overall_status, phase, study_type, conditions,
                        interventions, locations, sponsors, start_date, completion_date,
                        enrollment, eligibility_criteria, primary_outcome, secondary_outcome,
                        source, search_text, created_at, updated_at
                    ) VALUES (
                        :nct_id, :brief_title, :overall_status, :phase, :study_type, :conditions,
                        :interventions, :locations, :sponsors, :start_date, :completion_date,
                        :enrollment, :eligibility_criteria, :primary_outcome, :secondary_outcome,
                        :source, :search_text, NOW(), NOW()
                    )
                    ON CONFLICT (nct_id) DO UPDATE SET
                        -- Only update if we have better/more complete information
                        brief_title = COALESCE(NULLIF(EXCLUDED.brief_title, ''), clinical_trials.brief_title),
                        overall_status = COALESCE(NULLIF(EXCLUDED.overall_status, ''), clinical_trials.overall_status),
                        phase = COALESCE(NULLIF(EXCLUDED.phase, ''), clinical_trials.phase),
                        study_type = COALESCE(NULLIF(EXCLUDED.study_type, ''), clinical_trials.study_type),
                        conditions = COALESCE(NULLIF(EXCLUDED.conditions, '[]'::jsonb), clinical_trials.conditions),
                        interventions = COALESCE(NULLIF(EXCLUDED.interventions, '[]'::jsonb), clinical_trials.interventions),
                        locations = COALESCE(NULLIF(EXCLUDED.locations, '[]'::jsonb), clinical_trials.locations),
                        sponsors = COALESCE(NULLIF(EXCLUDED.sponsors, '[]'::jsonb), clinical_trials.sponsors),
                        start_date = COALESCE(NULLIF(EXCLUDED.start_date, ''), clinical_trials.start_date),
                        completion_date = COALESCE(NULLIF(EXCLUDED.completion_date, ''), clinical_trials.completion_date),
                        enrollment = COALESCE(EXCLUDED.enrollment, clinical_trials.enrollment),
                        eligibility_criteria = COALESCE(NULLIF(EXCLUDED.eligibility_criteria, ''), clinical_trials.eligibility_criteria),
                        primary_outcome = COALESCE(NULLIF(EXCLUDED.primary_outcome, ''), clinical_trials.primary_outcome),
                        secondary_outcome = COALESCE(NULLIF(EXCLUDED.secondary_outcome, ''), clinical_trials.secondary_outcome),
                        source = COALESCE(NULLIF(EXCLUDED.source, ''), clinical_trials.source),
                        search_text = COALESCE(NULLIF(EXCLUDED.search_text, ''), clinical_trials.search_text),
                        updated_at = NOW()
                '''), {
                    'nct_id': study_data.get('nct_id', ''),
                    'brief_title': study_data.get('brief_title', ''),
                    'overall_status': study_data.get('overall_status', ''),
                    'phase': study_data.get('phase', ''),
                    'study_type': study_data.get('study_type', ''),
                    'conditions': json.dumps(study_data.get('conditions', [])),
                    'interventions': json.dumps(study_data.get('interventions', [])),
                    'locations': json.dumps(study_data.get('locations', [])),
                    'sponsors': json.dumps(study_data.get('sponsors', [])),
                    'start_date': study_data.get('start_date', ''),
                    'completion_date': study_data.get('completion_date', ''),
                    'enrollment': study_data.get('enrollment', 0),
                    'eligibility_criteria': study_data.get('eligibility_criteria', ''),
                    'primary_outcome': study_data.get('primary_outcome', ''),
                    'secondary_outcome': study_data.get('secondary_outcome', ''),
                    'source': study_data.get('source', 'smart_clinical_trials_downloader'),
                    'search_text': study_data.get('search_text', study_data.get('brief_title', ''))
                })
            
            db.commit()
            
            # Update statistics
            result = db.execute(text('SELECT COUNT(*) as total FROM clinical_trials'))
            total_count = result.fetchone().total
            
            logger.info(f'Successfully inserted {total_count} clinical trials')
        
        logger.info('ClinicalTrials update completed successfully')
        return True
        
    except Exception as e:
        logger.error(f'Error updating ClinicalTrials: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return False

# Run the update
success = asyncio.run(update_trials())
print(f'ClinicalTrials update completed: {\\\"success\\\" if success else \\\"failed\\\"}')
if not success:
    sys.exit(1)
" >> $LOG_FILE 2>&1

if [ $? -eq 0 ]; then
    echo "$(date): ClinicalTrials update completed successfully" >> $LOG_FILE
else
    echo "$(date): ClinicalTrials update failed" >> $LOG_FILE
    exit 1
fi
