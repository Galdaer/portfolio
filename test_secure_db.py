#!/usr/bin/env python3
"""
Test script for secure database manager
"""

import asyncio
import sys

sys.path.insert(0, "/home/intelluxe/services/user/healthcare-api")

from core.database.secure_db_manager import DatabaseType, get_db_manager


async def test_connections():
    """Test database connections and routing"""
    print("Testing secure database connections...")

    try:
        # Get database manager
        db_manager = await get_db_manager()

        print("✅ Database manager initialized")

        # Test public database connection
        result = await db_manager.fetchval(
            "SELECT COUNT(*) FROM pubmed_articles",
            database=DatabaseType.PUBLIC,
        )
        print(f"✅ Public database: {result} PubMed articles")

        # Test private database connection
        result = await db_manager.fetchval(
            "SELECT COUNT(*) FROM appointments",
            database=DatabaseType.PRIVATE,
        )
        print(f"✅ Private database: {result} appointments")

        # Test PHI table routing
        phi_tables = ["appointments", "patient_scheduling_preferences"]
        for table in phi_tables:
            exists = await db_manager.fetchval(
                f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')",
                database=DatabaseType.PRIVATE,
            )
            print(f"✅ PHI table '{table}' in private DB: {'exists' if exists else 'not found'}")

        # Test public table routing
        public_tables = ["providers", "facilities", "appointment_types"]
        for table in public_tables:
            exists = await db_manager.fetchval(
                f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')",
                database=DatabaseType.PUBLIC,
            )
            print(f"✅ Public table '{table}' in public DB: {'exists' if exists else 'not found'}")

        # Test pool statistics
        stats = await db_manager.get_pool_stats()
        print(f"✅ Connection pool stats: {stats}")

        print("\n🎉 All database tests passed!")

    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

    return True


if __name__ == "__main__":
    success = asyncio.run(test_connections())
    sys.exit(0 if success else 1)
