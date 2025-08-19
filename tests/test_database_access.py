#!/usr/bin/env python3
"""
Test Medical Database Access

Tests the database-first approach for medical literature queries.
"""

import sys
import os

# Add healthcare-api to path
sys.path.append('/home/intelluxe/services/user/healthcare-api')

from core.database.medical_db import get_medical_db


def test_database_access():
    """Test database access and status"""
    print("🔍 Testing Medical Database Access...")
    
    try:
        # Get database instance
        medical_db = get_medical_db()
        print("✅ Database instance created")
        
        # Check database status
        print("\n🗃️ Checking database status...")
        status = medical_db.get_database_status()
        print(f"Database available: {status.get('database_available', False)}")
        
        if status.get('database_available', False):
            tables = status.get('tables', {})
            for table_name, table_info in tables.items():
                count = table_info.get('count', 0)
                available = table_info.get('available', False)
                print(f"  {table_name}: {count:,} records ({'✅' if available else '❌'})")
        
        # Test PubMed search if database is available
        if status.get('database_available', False):
            print("\n🔍 Testing PubMed search...")
            results = medical_db.search_pubmed_local("cardiovascular health", max_results=3)
            print(f"Found {len(results)} PubMed articles")
            for i, article in enumerate(results[:2]):
                title = article.get('title', 'No title')[:60]
                print(f"  {i+1}. {title}...")
        
        print("\n✅ Database test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_database_access()
    sys.exit(0 if success else 1)
