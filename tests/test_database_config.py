#!/usr/bin/env python3
"""
Test database connection with updated configuration
"""

import sys

# Add healthcare-api to Python path
sys.path.append("/home/intelluxe/services/user/healthcare-api")

from config.app import IntelluxeConfig


def test_database_config():
    """Test that database configuration uses static IP"""
    config = IntelluxeConfig()

    print("🔍 Testing database configuration...")
    print(f"Database URL: {config.postgres_url}")
    print(f"Database Name: {config.database_name}")
    print(f"Postgres Host: {config.postgres_host}")

    # Check if it's using the static IP
    if "172.20.0.13" in config.postgres_url:
        print("✅ Database configuration using static IP correctly")
    else:
        print("❌ Database configuration NOT using static IP")

    # Test the database_url property
    if config.database_url:
        print(f"✅ DATABASE_URL from .env: {config.database_url}")
    else:
        print("❌ DATABASE_URL not found in .env")


if __name__ == "__main__":
    test_database_config()
