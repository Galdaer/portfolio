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
sys.path.append('$PYTHON_PATH')
from fda.api import FDAAPI
from database import get_database_url
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

async def update_fda():
    engine = create_engine(get_database_url())
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    api = FDAAPI(SessionLocal)
    result = await api.trigger_update()
    print(f'FDA update completed: {result}')

asyncio.run(update_fda())
" >> $LOG_FILE 2>&1

if [ $? -eq 0 ]; then
    echo "$(date): FDA update completed successfully" >> $LOG_FILE
else
    echo "$(date): FDA update failed" >> $LOG_FILE
    exit 1
fi
