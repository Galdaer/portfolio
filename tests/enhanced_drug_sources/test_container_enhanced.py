#!/usr/bin/env python3
"""
Test script to run inside the container environment
"""
import sys
sys.path.append('/app/src')
import os
import asyncio
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

# Environment setup
os.environ['DATABASE_URL'] = 'postgresql://intelluxe:secure_password@localhost:5432/intelluxe_public'

from drugs.api import DrugAPI
from database import get_db_session

async def test_drugcentral_in_container():
    print("🧪 Testing DrugCentral integration in container environment")
    
    # Create API instance
    drug_api = DrugAPI(get_db_session)
    db = get_db_session()
    
    try:
        # Test just DrugCentral processing
        print("🎯 Testing DrugCentral processing...")
        stats = await drug_api._process_drugcentral_data("/app/data/enhanced_drug_data/drugcentral", db)
        print(f"DrugCentral stats: {stats}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_drugcentral_in_container())