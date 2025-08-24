#!/bin/bash
# Update script for FDA data
# Should be run monthly via cron job

set -e

LOG_FILE="/app/logs/fda_update.log"
PYTHON_PATH="/app/src"

echo "$(date): Starting FDA update" >> $LOG_FILE

cd /app

# Set Python path
export PYTHONPATH=$PYTHON_PATH

# Run FDA update
python3 -c "
import asyncio
import sys
import os
import logging
import json
from pathlib import Path
sys.path.append('$PYTHON_PATH')
from fda.smart_downloader import SmartFDADownloader
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

async def update_fda():
    config = Config()
    
    try:
        # Use smart downloader with automatic state management and retries
        output_dir = Path('/app/data/fda')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        async with SmartFDADownloader(output_dir=output_dir, config=config) as downloader:
            logger.info('Starting smart FDA download with automatic retry handling')
            
            # Download complete FDA dataset
            summary = await downloader.download_all(force_fresh=False, complete_dataset=True)
            
            logger.info(f'Smart download completed: {summary[\\\"total_drugs\\\"]} drugs from {summary[\\\"total_datasets\\\"]} datasets')
            logger.info(f'Success rate: {summary[\\\"success_rate\\\"]:.1f}%')
            
            if summary[\\\"failed_sources\\\"] > 0:
                logger.warning(f'Failed sources: {summary[\\\"failed_sources\\\"]} (will retry automatically)')
            
            if summary[\\\"rate_limited_sources\\\"] > 0:
                logger.info(f'Rate limited sources: {summary[\\\"rate_limited_sources\\\"]} (will retry in background)')
            
        # Load the downloaded and validated drugs
        all_drugs_file = output_dir / 'all_fda_drugs_complete.json'
        if not all_drugs_file.exists():
            logger.error('No FDA drugs were downloaded')
            return False
            
        with open(all_drugs_file, 'r') as f:
            validated_drugs = json.load(f)
        
        logger.info(f'Processing {len(validated_drugs)} validated drugs for database insertion')
        
        # Insert/Update into database using UPSERT
        with get_db_session() as db:
            logger.info('Upserting FDA drugs (preserving existing data)')
            
            # Use UPSERT to preserve existing data and only update with better information
            for drug_data in validated_drugs:
                db.execute(text('''
                    INSERT INTO fda_drugs (
                        drug_id, ndc, application_number, name, generic_name, brand_name,
                        manufacturer, dosage_form, route, strength, approval_date,
                        marketing_status, active_ingredients, indications, warnings,
                        dataset, source, search_text, created_at, updated_at
                    ) VALUES (
                        :drug_id, :ndc, :application_number, :name, :generic_name, :brand_name,
                        :manufacturer, :dosage_form, :route, :strength, :approval_date,
                        :marketing_status, :active_ingredients, :indications, :warnings,
                        :dataset, :source, :search_text, NOW(), NOW()
                    )
                    ON CONFLICT (drug_id) DO UPDATE SET
                        -- Only update if we have better/more complete information
                        ndc = COALESCE(NULLIF(EXCLUDED.ndc, ''), fda_drugs.ndc),
                        application_number = COALESCE(NULLIF(EXCLUDED.application_number, ''), fda_drugs.application_number),
                        name = COALESCE(NULLIF(EXCLUDED.name, ''), fda_drugs.name),
                        generic_name = COALESCE(NULLIF(EXCLUDED.generic_name, ''), fda_drugs.generic_name),
                        brand_name = COALESCE(NULLIF(EXCLUDED.brand_name, ''), fda_drugs.brand_name),
                        manufacturer = COALESCE(NULLIF(EXCLUDED.manufacturer, ''), fda_drugs.manufacturer),
                        dosage_form = COALESCE(NULLIF(EXCLUDED.dosage_form, ''), fda_drugs.dosage_form),
                        route = COALESCE(NULLIF(EXCLUDED.route, ''), fda_drugs.route),
                        strength = COALESCE(NULLIF(EXCLUDED.strength, ''), fda_drugs.strength),
                        approval_date = COALESCE(NULLIF(EXCLUDED.approval_date, ''), fda_drugs.approval_date),
                        marketing_status = COALESCE(NULLIF(EXCLUDED.marketing_status, ''), fda_drugs.marketing_status),
                        active_ingredients = COALESCE(NULLIF(EXCLUDED.active_ingredients, '[]'::jsonb), fda_drugs.active_ingredients),
                        indications = COALESCE(NULLIF(EXCLUDED.indications, ''), fda_drugs.indications),
                        warnings = COALESCE(NULLIF(EXCLUDED.warnings, ''), fda_drugs.warnings),
                        dataset = COALESCE(NULLIF(EXCLUDED.dataset, ''), fda_drugs.dataset),
                        source = COALESCE(NULLIF(EXCLUDED.source, ''), fda_drugs.source),
                        search_text = COALESCE(NULLIF(EXCLUDED.search_text, ''), fda_drugs.search_text),
                        updated_at = NOW()
                '''), {
                    'drug_id': drug_data.get('drug_id', ''),
                    'ndc': drug_data.get('ndc', ''),
                    'application_number': drug_data.get('application_number', ''),
                    'name': drug_data.get('name', ''),
                    'generic_name': drug_data.get('generic_name', ''),
                    'brand_name': drug_data.get('brand_name', ''),
                    'manufacturer': drug_data.get('manufacturer', ''),
                    'dosage_form': drug_data.get('dosage_form', ''),
                    'route': drug_data.get('route', ''),
                    'strength': drug_data.get('strength', ''),
                    'approval_date': drug_data.get('approval_date', ''),
                    'marketing_status': drug_data.get('marketing_status', ''),
                    'active_ingredients': json.dumps(drug_data.get('active_ingredients', [])) if isinstance(drug_data.get('active_ingredients'), list) else str(drug_data.get('active_ingredients', '')),
                    'indications': drug_data.get('indications', ''),
                    'warnings': drug_data.get('warnings', ''),
                    'dataset': drug_data.get('dataset', ''),
                    'source': drug_data.get('source', 'smart_fda_downloader'),
                    'search_text': drug_data.get('search_text', drug_data.get('name', ''))
                })
            
            db.commit()
            
            # Update statistics
            result = db.execute(text('SELECT COUNT(*) as total FROM fda_drugs'))
            total_count = result.fetchone().total
            
            logger.info(f'Successfully inserted {total_count} FDA drugs')
        
        logger.info('FDA update completed successfully')
        return True
        
    except Exception as e:
        logger.error(f'Error updating FDA: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return False

# Run the update
success = asyncio.run(update_fda())
print(f'FDA update completed: {\\\"success\\\" if success else \\\"failed\\\"}')
if not success:
    sys.exit(1)
" >> $LOG_FILE 2>&1

if [ $? -eq 0 ]; then
    echo "$(date): FDA update completed successfully" >> $LOG_FILE
else
    echo "$(date): FDA update failed" >> $LOG_FILE
    exit 1
fi
