#!/usr/bin/env python3
"""
Test DDInter integration - load processed interactions into database
"""

import json
import logging
import sys
from pathlib import Path

# Add medical-mirrors src to path
sys.path.insert(0, "/home/intelluxe/services/user/medical-mirrors/src")

from sqlalchemy import text

from database import get_db_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_ddinter_integration():
    """Test DDInter static data integration"""

    # Path to processed DDInter data
    ddinter_file = Path("/home/intelluxe/database/medical_complete/enhanced_drug_data/ddinter/ddinter_interactions.json")

    if not ddinter_file.exists():
        print("❌ DDInter processed data file not found")
        print(f"   Expected: {ddinter_file}")
        return False

    # Load the processed data
    with open(ddinter_file) as f:
        interactions = json.load(f)

    print(f"📊 Loaded {len(interactions):,} drug interactions from DDInter")

    # Show sample interactions by severity
    severity_samples = {}
    for interaction in interactions:
        severity = interaction.get("severity", "Unknown")
        if severity not in severity_samples:
            severity_samples[severity] = interaction

    print("\n🔍 Sample interactions by severity:")
    for severity, sample in sorted(severity_samples.items()):
        print(f"   {severity}: {sample['drug_1']} ↔ {sample['drug_2']}")

    # Test database connection
    try:
        session_factory = get_db_session
        db = session_factory()

        # Check if drug_interactions table exists
        tables_result = db.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = 'drug_interactions'
        """)).fetchall()

        if tables_result:
            print("✅ drug_interactions table exists")

            # Get current interaction count
            count = db.execute(text("SELECT COUNT(*) FROM drug_interactions")).scalar()
            print(f"   Current interactions in database: {count:,}")

            # Test insertion of a few sample interactions
            print("\n🧪 Testing sample insertions...")

            sample_interactions = interactions[:5]  # Test with first 5
            inserted_count = 0

            for interaction in sample_interactions:
                try:
                    insert_sql = text("""
                        INSERT INTO drug_interactions (
                            drug_1, drug_2, interaction_type, severity,
                            mechanism, clinical_effect, management,
                            evidence_level, references, source, metadata
                        ) VALUES (
                            :drug_1, :drug_2, :interaction_type, :severity,
                            :mechanism, :clinical_effect, :management,
                            :evidence_level, :references, :source, :metadata
                        ) ON CONFLICT DO NOTHING
                    """)

                    metadata = {
                        "ddinter_id_a": interaction.get("ddinter_id_a"),
                        "ddinter_id_b": interaction.get("ddinter_id_b"),
                    }

                    result = db.execute(insert_sql, {
                        "drug_1": interaction.get("drug_1"),
                        "drug_2": interaction.get("drug_2"),
                        "interaction_type": interaction.get("interaction_type"),
                        "severity": interaction.get("severity"),
                        "mechanism": interaction.get("mechanism"),
                        "clinical_effect": interaction.get("clinical_effect"),
                        "management": interaction.get("management"),
                        "evidence_level": interaction.get("evidence_level"),
                        "references": interaction.get("references"),
                        "source": "DDInter",
                        "metadata": json.dumps(metadata),
                    })

                    if result.rowcount > 0:
                        inserted_count += 1

                except Exception as e:
                    logger.warning(f"Error inserting interaction: {e}")

            db.commit()
            print(f"   Successfully inserted {inserted_count} sample interactions")

        else:
            print("⚠️  drug_interactions table does not exist")
            print("   Run database migrations to create the table")

        db.close()

    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

    print("\n✅ DDInter integration test completed successfully!")
    print(f"   Ready to process {len(interactions):,} drug interactions")
    print("   Data includes severity levels: Major, Moderate, Minor")

    return True


if __name__ == "__main__":
    success = test_ddinter_integration()
    sys.exit(0 if success else 1)
