#!/bin/bash
# Update script for PubMed data
# Should be run daily via cron job

set -e

LOG_FILE="/app/logs/pubmed_update.log"
PYTHON_PATH="/app/src"

echo "$(date): Starting PubMed update" >> $LOG_FILE

cd /app

# Set Python path
export PYTHONPATH=$PYTHON_PATH

# Run PubMed update
python3 -c "
import asyncio
import sys
import os
import logging
import json
from pathlib import Path
sys.path.append('$PYTHON_PATH')
from src.pubmed.smart_downloader import SmartPubMedDownloader
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

async def update_pubmed():
    config = Config()
    
    try:
        # Use smart downloader with automatic state management and retries
        output_dir = Path('/app/data/pubmed')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        async with SmartPubMedDownloader(output_dir=output_dir, config=config) as downloader:
            logger.info('Starting smart PubMed download with automatic retry handling')
            
            # Download complete dataset for PubMed (baseline + updates)
            summary = await downloader.download_all_pubmed_data(force_fresh=False, complete_dataset=False)
            
            logger.info(f'Smart download completed: {summary[\\\"total_articles\\\"]} articles from {summary[\\\"total_files\\\"]} files')
            logger.info(f'Success rate: {summary[\\\"success_rate\\\"]:.1f}%')
            
            if summary[\\\"failed_sources\\\"] > 0:
                logger.warning(f'Failed sources: {summary[\\\"failed_sources\\\"]} (will retry automatically)')
            
            if summary[\\\"rate_limited_sources\\\"] > 0:
                logger.info(f'Rate limited sources: {summary[\\\"rate_limited_sources\\\"]} (will retry in background)')
            
        # Load the downloaded and validated articles
        all_articles_file = output_dir / 'all_pubmed_articles_complete.json'
        if not all_articles_file.exists():
            logger.error('No PubMed articles were downloaded')
            return False
            
        with open(all_articles_file, 'r') as f:
            validated_articles = json.load(f)
        
        logger.info(f'Processing {len(validated_articles)} validated articles for database insertion')
        
        # Insert/Update into database using UPSERT
        with get_db_session() as db:
            logger.info('Upserting PubMed articles (preserving existing data)')
            
            # Use UPSERT to preserve existing data and only update with better information
            for article_data in validated_articles:
                db.execute(text('''
                    INSERT INTO pubmed_articles (
                        pmid, title, abstract, authors, journal, pub_date, doi,
                        mesh_terms, source, search_text, created_at, updated_at
                    ) VALUES (
                        :pmid, :title, :abstract, :authors, :journal, :pub_date, :doi,
                        :mesh_terms, :source, :search_text, NOW(), NOW()
                    )
                    ON CONFLICT (pmid) DO UPDATE SET
                        -- Only update if we have better/more complete information
                        title = COALESCE(NULLIF(EXCLUDED.title, ''), pubmed_articles.title),
                        abstract = COALESCE(NULLIF(EXCLUDED.abstract, ''), pubmed_articles.abstract),
                        authors = COALESCE(NULLIF(EXCLUDED.authors, '{}'), pubmed_articles.authors),
                        journal = COALESCE(NULLIF(EXCLUDED.journal, ''), pubmed_articles.journal),
                        pub_date = COALESCE(NULLIF(EXCLUDED.pub_date, ''), pubmed_articles.pub_date),
                        doi = COALESCE(NULLIF(EXCLUDED.doi, ''), pubmed_articles.doi),
                        mesh_terms = COALESCE(NULLIF(EXCLUDED.mesh_terms, '{}'), pubmed_articles.mesh_terms),
                        source = COALESCE(NULLIF(EXCLUDED.source, ''), pubmed_articles.source),
                        search_text = COALESCE(NULLIF(EXCLUDED.search_text, ''), pubmed_articles.search_text),
                        updated_at = NOW()
                '''), {
                    'pmid': article_data.get('pmid', ''),
                    'title': article_data.get('title', ''),
                    'abstract': article_data.get('abstract', ''),
                    'authors': json.dumps(article_data.get('authors', [])),
                    'journal': article_data.get('journal', ''),
                    'pub_date': article_data.get('pub_date', ''),
                    'doi': article_data.get('doi', ''),
                    'mesh_terms': json.dumps(article_data.get('mesh_terms', [])),
                    'source': article_data.get('source', 'smart_pubmed_downloader'),
                    'search_text': article_data.get('search_text', article_data.get('title', ''))
                })
            
            db.commit()
            
            # Update statistics
            result = db.execute(text('SELECT COUNT(*) as total FROM pubmed_articles'))
            total_count = result.fetchone().total
            
            logger.info(f'Successfully inserted {total_count} PubMed articles')
        
        logger.info('PubMed update completed successfully')
        return True
        
    except Exception as e:
        logger.error(f'Error updating PubMed: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return False

# Run the update
success = asyncio.run(update_pubmed())
print(f'PubMed update completed: {\\\"success\\\" if success else \\\"failed\\\"}')
if not success:
    sys.exit(1)
" >> $LOG_FILE 2>&1

if [ $? -eq 0 ]; then
    echo "$(date): PubMed update completed successfully" >> $LOG_FILE
else
    echo "$(date): PubMed update failed" >> $LOG_FILE
    exit 1
fi
