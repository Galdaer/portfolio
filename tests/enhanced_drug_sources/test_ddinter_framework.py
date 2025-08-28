#!/usr/bin/env python3
"""
Test DDInter integration through medical-mirrors framework
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add medical-mirrors src to path
sys.path.insert(0, "/home/intelluxe/services/user/medical-mirrors/src")

from drugs.api import DrugAPI
from config import Config
from database import get_db_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_ddinter_framework():
    """Test DDInter integration using medical-mirrors framework"""
    
    try:
        # Initialize DrugAPI
        config = Config()
        session_factory = get_db_session
        drug_api = DrugAPI(session_factory, config)
        
        # DDInter data directory
        ddinter_data_dir = "/home/intelluxe/database/medical_complete/enhanced_drug_data/ddinter"
        
        print(f"🧪 Testing DDInter integration via medical-mirrors framework")
        print(f"   Data directory: {ddinter_data_dir}")
        
        # Check if directory exists
        data_path = Path(ddinter_data_dir)
        if not data_path.exists():
            print(f"❌ DDInter data directory not found: {data_path}")
            return False
        
        # List available files
        csv_files = list(data_path.glob("ddinter_downloads_code_*.csv"))
        print(f"   Found {len(csv_files)} DDInter CSV files")
        
        if not csv_files:
            print("❌ No DDInter CSV files found")
            return False
        
        # Process DDInter interactions through framework
        db = session_factory()
        try:
            print("📊 Processing DDInter interactions...")
            result = await drug_api.process_ddinter_interactions(ddinter_data_dir, db)
            
            print("✅ DDInter processing completed!")
            print(f"   Status: {result.get('status')}")
            print(f"   Interactions processed: {result.get('interactions_processed', 0):,}")
            print(f"   Drugs updated: {result.get('drugs_updated', 0):,}")
            
            # Show parser stats
            parser_stats = result.get('parser_stats', {})
            if parser_stats:
                print(f"   Parser statistics:")
                print(f"     - Processed: {parser_stats.get('processed_interactions', 0):,}")
                print(f"     - Duplicates removed: {parser_stats.get('duplicates_removed', 0):,}")
                print(f"     - Validation errors: {parser_stats.get('validation_errors', 0):,}")
            
            # Test a sample query to see if interactions were added
            from sqlalchemy import text
            sample_query = text("""
                SELECT generic_name, drug_interactions->'ddinter' as ddinter_data
                FROM drug_information 
                WHERE drug_interactions ? 'ddinter'
                LIMIT 3
            """)
            
            sample_results = db.execute(sample_query).fetchall()
            
            if sample_results:
                print(f"\n🔍 Sample drugs with DDInter interactions:")
                for row in sample_results:
                    drug_name = row[0]
                    ddinter_data = row[1] if row[1] else []
                    interaction_count = len(ddinter_data) if isinstance(ddinter_data, list) else 0
                    print(f"   - {drug_name}: {interaction_count} interactions")
            else:
                print("⚠️  No drugs found with DDInter interactions in database")
            
        finally:
            db.close()
        
        return True
        
    except Exception as e:
        logger.exception(f"Error testing DDInter framework integration: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_ddinter_framework())
    print(f"\n{'✅ Success' if success else '❌ Failed'}")
    sys.exit(0 if success else 1)