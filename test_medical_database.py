#!/usr/bin/env python3
"""
Test script for updated medical database access
"""

import asyncio
import sys

sys.path.insert(0, "/home/intelluxe/services/user/healthcare-api")

from core.database.medical_db import get_medical_db


async def test_medical_db():
    """Test medical database operations"""
    print("Testing medical database access...")

    try:
        # Get medical database instance
        medical_db = await get_medical_db()

        print("✅ Medical database instance created")

        # Test PubMed search
        articles = await medical_db.search_pubmed_local("diabetes", max_results=3)
        print(f"✅ PubMed search: found {len(articles)} articles")
        if articles:
            print(f"   Example: {articles[0]['title'][:60]}...")

        # Test clinical trials search
        trials = await medical_db.search_clinical_trials_local("cancer", max_results=2)
        print(f"✅ Clinical trials search: found {len(trials)} trials")
        if trials:
            print(f"   Example: {trials[0]['title'][:60]}...")

        # Test health topics search
        topics = await medical_db.search_health_topics_local("nutrition", max_results=2)
        print(f"✅ Health topics search: found {len(topics)} topics")
        if topics:
            print(f"   Example: {topics[0]['title'][:60]}...")

        # Test database status
        status = await medical_db.get_database_status()
        print(f"✅ Database status: {status['database_available']}")
        print(f"   Available tables: {len(status['tables'])}")

        print("\n🎉 All medical database tests passed!")

    except Exception as e:
        print(f"❌ Medical database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = asyncio.run(test_medical_db())
    sys.exit(0 if success else 1)
