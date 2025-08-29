#!/usr/bin/env python3
"""
Test script to manually trigger enhanced drug sources processing
"""
import asyncio
import logging
import os
import sys

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Add the medical-mirrors src directory to Python path
sys.path.append("/home/intelluxe/services/user/medical-mirrors/src")

# Set environment variables
os.environ["DATABASE_URL"] = "postgresql://intelluxe:secure_password@localhost:5432/intelluxe_public"

try:
    from drugs.api import DrugAPI
    from sqlalchemy import text

    from database import get_db_session

    async def test_enhanced_sources():
        """Test enhanced drug sources processing"""
        print("🧪 Testing Enhanced Drug Sources Processing")

        # Create drug API instance
        drug_api = DrugAPI(get_db_session)

        # Create database session
        db = get_db_session()

        try:
            print("📊 Checking current database stats...")
            # Get current stats
            current_stats = db.execute(text("""
                SELECT
                    COUNT(*) FILTER (WHERE therapeutic_class IS NOT NULL AND therapeutic_class != '') as has_therapeutic_class,
                    COUNT(*) FILTER (WHERE indications_and_usage IS NOT NULL AND indications_and_usage != '') as has_indications,
                    COUNT(*) FILTER (WHERE mechanism_of_action IS NOT NULL AND mechanism_of_action != '') as has_mechanism,
                    COUNT(*) FILTER (WHERE pharmacokinetics IS NOT NULL AND pharmacokinetics != '') as has_pharmacokinetics,
                    COUNT(*) as total_drugs
                FROM drug_information
            """)).fetchone()

            print("Current stats:")
            print(f"  - Total drugs: {current_stats.total_drugs}")
            print(f"  - Therapeutic class: {current_stats.has_therapeutic_class}")
            print(f"  - Indications: {current_stats.has_indications}")
            print(f"  - Mechanism of action: {current_stats.has_mechanism}")
            print(f"  - Pharmacokinetics: {current_stats.has_pharmacokinetics}")

            print("\n🚀 Starting enhanced sources processing...")

            # Process enhanced sources
            stats = await drug_api.process_enhanced_drug_sources(db)

            print("\n✅ Enhanced sources processing completed!")
            print(f"Stats: {stats}")

            # Get updated stats
            updated_stats = db.execute(text("""
                SELECT
                    COUNT(*) FILTER (WHERE therapeutic_class IS NOT NULL AND therapeutic_class != '') as has_therapeutic_class,
                    COUNT(*) FILTER (WHERE indications_and_usage IS NOT NULL AND indications_and_usage != '') as has_indications,
                    COUNT(*) FILTER (WHERE mechanism_of_action IS NOT NULL AND mechanism_of_action != '') as has_mechanism,
                    COUNT(*) FILTER (WHERE pharmacokinetics IS NOT NULL AND pharmacokinetics != '') as has_pharmacokinetics,
                    COUNT(*) as total_drugs
                FROM drug_information
            """)).fetchone()

            print("\nUpdated stats:")
            print(f"  - Total drugs: {updated_stats.total_drugs}")
            print(f"  - Therapeutic class: {updated_stats.has_therapeutic_class} (+{updated_stats.has_therapeutic_class - current_stats.has_therapeutic_class})")
            print(f"  - Indications: {updated_stats.has_indications} (+{updated_stats.has_indications - current_stats.has_indications})")
            print(f"  - Mechanism of action: {updated_stats.has_mechanism} (+{updated_stats.has_mechanism - current_stats.has_mechanism})")
            print(f"  - Pharmacokinetics: {updated_stats.has_pharmacokinetics} (+{updated_stats.has_pharmacokinetics - current_stats.has_pharmacokinetics})")

        finally:
            db.close()

    if __name__ == "__main__":
        asyncio.run(test_enhanced_sources())

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
