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
sys.path.append('$PYTHON_PATH')
from pubmed.api import PubMedAPI
from database import get_database_url
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

async def update_pubmed():
    engine = create_engine(get_database_url())
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    api = PubMedAPI(SessionLocal)
    result = await api.trigger_update()
    print(f'PubMed update completed: {result}')

asyncio.run(update_pubmed())
" >> $LOG_FILE 2>&1

if [ $? -eq 0 ]; then
    echo "$(date): PubMed update completed successfully" >> $LOG_FILE
else
    echo "$(date): PubMed update failed" >> $LOG_FILE
    exit 1
fi
