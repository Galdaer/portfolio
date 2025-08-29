#!/usr/bin/env python3
"""
Test script to test DailyMed integration with fuzzy matching
"""
import sys

sys.path.append("/app/src")
import asyncio
import logging
import os

# Set up logging
logging.basicConfig(level=logging.INFO)

# Environment setup
os.environ["DATABASE_URL"] = "postgresql://intelluxe:secure_password@localhost:5432/intelluxe_public"

from drugs.api import DrugAPI

from database import get_db_session


async def test_dailymed_in_container():
    print("🧪 Testing DailyMed integration in container environment")

    # Create API instance
    drug_api = DrugAPI(get_db_session)
    db = get_db_session()

    try:
        # Test just DailyMed processing
        print("🎯 Testing DailyMed processing...")
        stats = await drug_api._process_dailymed_data("/app/data/enhanced_drug_data/dailymed", db)
        print(f"DailyMed stats: {stats}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_dailymed_in_container())
