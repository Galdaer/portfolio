#!/usr/bin/env python3
"""
Test script for FDA drug database operations
Tests database insertion and connection using parsed FDA data
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Add medical-mirrors to Python path
medical_mirrors_src = Path(__file__).parent / "services/user/medical-mirrors/src"
sys.path.insert(0, str(medical_mirrors_src))

try:
    from database import get_db_session, FDADrug, engine
    from fda.parser_optimized import parse_drug_label_record_worker
    from sqlalchemy import text
    from sqlalchemy.dialects.postgresql import insert
except ImportError as e:
    print(f"Failed to import modules: {e}")
    print(f"Looking for modules in: {medical_mirrors_src}")
    sys.exit(1)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_database_connection():
    """Test basic database connection"""
    logger.info("=== Testing Database Connection ===")
    
    try:
        # Test connection
        db = get_db_session()
        
        # Test basic query
        result = db.execute(text("SELECT 1 as test")).fetchone()
        logger.info(f"✅ Database connection successful: {result}")
        
        # Check if fda_drugs table exists
        table_check = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'fda_drugs'
            )
        """)).fetchone()
        
        if table_check[0]:
            logger.info("✅ fda_drugs table exists")
            
            # Get current count
            count = db.execute(text("SELECT COUNT(*) FROM fda_drugs")).fetchone()
            logger.info(f"📊 Current fda_drugs count: {count[0]}")
        else:
            logger.warning("⚠️ fda_drugs table does not exist")
        
        db.close()
        return True
        
    except Exception as e:
        logger.exception(f"❌ Database connection failed: {e}")
        return False

def create_test_drug_data() -> List[Dict[str, Any]]:
    """Create test FDA drug data for database insertion"""
    sample_labels = [
        {
            "product_ndc": ["TEST-001"],
            "brand_name": ["Test Drug A"],
            "generic_name": ["testcompound-a"],
            "manufacturer_name": ["Test Pharma Inc"],
            "dosage_form": ["tablet"],
            "route": ["oral"],
            "active_ingredient": ["testcompound-a 10mg"],
            "contraindications": ["Known hypersensitivity to testcompound-a"],
            "warnings": ["May cause drowsiness"],
            "precautions": ["Use with caution in elderly patients"],
            "adverse_reactions": ["Nausea", "Dizziness", "Headache"],
            "drug_interactions": [{"drug": "Alcohol", "severity": "Moderate"}],
            "indications_and_usage": "For the treatment of test conditions in adult patients.",
            "dosage_and_administration": "Take 1 tablet daily with food.",
            "mechanism_of_action": "Acts by binding to test receptors.",
            "pharmacokinetics": "Rapidly absorbed with peak levels at 2 hours.",
            "pharmacodynamics": "Provides sustained effect for 24 hours."
        },
        {
            "product_ndc": ["TEST-002"],
            "brand_name": ["Test Drug B"],
            "generic_name": ["testcompound-b"],
            "manufacturer_name": ["Another Pharma LLC"],
            "dosage_form": ["injection"],
            "route": ["intravenous"],
            "active_ingredient": ["testcompound-b 50mg/mL"],
            "contraindications": ["Severe renal impairment"],
            "warnings": ["Black box warning: Increased infection risk"],
            "indications_and_usage": "For severe test conditions requiring IV therapy."
        }
    ]
    
    parsed_drugs = []
    for label_data in sample_labels:
        try:
            parsed_drug = parse_drug_label_record_worker(label_data)
            if parsed_drug:
                parsed_drugs.append(parsed_drug)
        except Exception as e:
            logger.error(f"Failed to parse test drug: {e}")
    
    return parsed_drugs

def test_single_drug_insertion():
    """Test inserting a single drug record"""
    logger.info("=== Testing Single Drug Insertion ===")
    
    test_drugs = create_test_drug_data()
    if not test_drugs:
        logger.error("❌ No test drugs created")
        return False
    
    db = get_db_session()
    try:
        drug_data = test_drugs[0]
        logger.info(f"Testing insertion for: {drug_data['name']}")
        
        # Prepare data for insertion
        insert_data = {
            "ndc": drug_data.get("ndc", "").strip(),
            "name": drug_data.get("name", ""),
            "generic_name": drug_data.get("generic_name", ""),
            "brand_name": drug_data.get("brand_name", ""),
            "manufacturer": drug_data.get("manufacturer", ""),
            "applicant": drug_data.get("applicant", ""),
            "ingredients": drug_data.get("ingredients", []),
            "strength": drug_data.get("strength", ""),
            "dosage_form": drug_data.get("dosage_form", ""),
            "route": drug_data.get("route", ""),
            "application_number": drug_data.get("application_number", ""),
            "product_number": drug_data.get("product_number", ""),
            "approval_date": drug_data.get("approval_date", ""),
            "orange_book_code": drug_data.get("orange_book_code", ""),
            "reference_listed_drug": drug_data.get("reference_listed_drug", ""),
            "therapeutic_class": drug_data.get("therapeutic_class", ""),
            "pharmacologic_class": drug_data.get("pharmacologic_class", ""),
            
            # Clinical information fields
            "contraindications": drug_data.get("contraindications", []),
            "warnings": drug_data.get("warnings", []),
            "precautions": drug_data.get("precautions", []),
            "adverse_reactions": drug_data.get("adverse_reactions", []),
            "drug_interactions": drug_data.get("drug_interactions", {}),
            "indications_and_usage": drug_data.get("indications_and_usage", ""),
            "dosage_and_administration": drug_data.get("dosage_and_administration", ""),
            "mechanism_of_action": drug_data.get("mechanism_of_action", ""),
            "pharmacokinetics": drug_data.get("pharmacokinetics", ""),
            "pharmacodynamics": drug_data.get("pharmacodynamics", ""),
            
            "data_sources": drug_data.get("data_sources", []),
            "updated_at": datetime.utcnow(),
        }
        
        logger.info("📝 Prepared data for insertion:")
        for key, value in insert_data.items():
            if isinstance(value, str) and len(value) > 100:
                display_value = value[:100] + "..."
            else:
                display_value = value
            logger.info(f"  {key}: {display_value}")
        
        # Use PostgreSQL UPSERT
        stmt = insert(FDADrug).values(insert_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=["ndc"],
            set_={
                "name": stmt.excluded.name,
                "updated_at": stmt.excluded.updated_at,
                "contraindications": stmt.excluded.contraindications,
                "warnings": stmt.excluded.warnings,
                "precautions": stmt.excluded.precautions,
                "adverse_reactions": stmt.excluded.adverse_reactions,
                "drug_interactions": stmt.excluded.drug_interactions,
                "indications_and_usage": stmt.excluded.indications_and_usage,
                "dosage_and_administration": stmt.excluded.dosage_and_administration,
                "mechanism_of_action": stmt.excluded.mechanism_of_action,
                "pharmacokinetics": stmt.excluded.pharmacokinetics,
                "pharmacodynamics": stmt.excluded.pharmacodynamics,
            },
        )
        
        # Execute insertion
        db.execute(stmt)
        db.commit()
        
        logger.info("✅ Drug insertion successful!")
        
        # Verify insertion
        result = db.execute(
            text("SELECT ndc, name, contraindications, drug_interactions FROM fda_drugs WHERE ndc = :ndc"),
            {"ndc": insert_data["ndc"]}
        ).fetchone()
        
        if result:
            logger.info(f"✅ Verification successful:")
            logger.info(f"  NDC: {result[0]}")
            logger.info(f"  Name: {result[1]}")
            logger.info(f"  Contraindications: {result[2]}")
            logger.info(f"  Drug Interactions: {result[3]}")
            return True
        else:
            logger.error("❌ Verification failed - record not found")
            return False
            
    except Exception as e:
        logger.exception(f"❌ Single drug insertion failed: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def test_batch_insertion():
    """Test batch insertion of multiple drugs"""
    logger.info("=== Testing Batch Drug Insertion ===")
    
    test_drugs = create_test_drug_data()
    if len(test_drugs) < 2:
        logger.error("❌ Need at least 2 test drugs for batch insertion")
        return False
    
    db = get_db_session()
    try:
        insert_data_list = []
        
        for drug_data in test_drugs:
            insert_data = {
                "ndc": drug_data.get("ndc", "").strip(),
                "name": drug_data.get("name", ""),
                "generic_name": drug_data.get("generic_name", ""),
                "brand_name": drug_data.get("brand_name", ""),
                "manufacturer": drug_data.get("manufacturer", ""),
                "applicant": drug_data.get("applicant", ""),
                "ingredients": drug_data.get("ingredients", []),
                "strength": drug_data.get("strength", ""),
                "dosage_form": drug_data.get("dosage_form", ""),
                "route": drug_data.get("route", ""),
                "application_number": drug_data.get("application_number", ""),
                "product_number": drug_data.get("product_number", ""),
                "approval_date": drug_data.get("approval_date", ""),
                "orange_book_code": drug_data.get("orange_book_code", ""),
                "reference_listed_drug": drug_data.get("reference_listed_drug", ""),
                "therapeutic_class": drug_data.get("therapeutic_class", ""),
                "pharmacologic_class": drug_data.get("pharmacologic_class", ""),
                
                # Clinical information fields
                "contraindications": drug_data.get("contraindications", []),
                "warnings": drug_data.get("warnings", []),
                "precautions": drug_data.get("precautions", []),
                "adverse_reactions": drug_data.get("adverse_reactions", []),
                "drug_interactions": drug_data.get("drug_interactions", {}),
                "indications_and_usage": drug_data.get("indications_and_usage", ""),
                "dosage_and_administration": drug_data.get("dosage_and_administration", ""),
                "mechanism_of_action": drug_data.get("mechanism_of_action", ""),
                "pharmacokinetics": drug_data.get("pharmacokinetics", ""),
                "pharmacodynamics": drug_data.get("pharmacodynamics", ""),
                
                "data_sources": drug_data.get("data_sources", []),
                "updated_at": datetime.utcnow(),
            }
            insert_data_list.append(insert_data)
        
        logger.info(f"📝 Preparing batch insertion of {len(insert_data_list)} drugs")
        
        # Batch UPSERT
        stmt = insert(FDADrug)
        stmt = stmt.on_conflict_do_update(
            index_elements=["ndc"],
            set_={
                "name": stmt.excluded.name,
                "updated_at": stmt.excluded.updated_at,
                "contraindications": stmt.excluded.contraindications,
                "warnings": stmt.excluded.warnings,
                "precautions": stmt.excluded.precautions,
                "adverse_reactions": stmt.excluded.adverse_reactions,
                "drug_interactions": stmt.excluded.drug_interactions,
                "indications_and_usage": stmt.excluded.indications_and_usage,
                "dosage_and_administration": stmt.excluded.dosage_and_administration,
                "mechanism_of_action": stmt.excluded.mechanism_of_action,
                "pharmacokinetics": stmt.excluded.pharmacokinetics,
                "pharmacodynamics": stmt.excluded.pharmacodynamics,
            },
        )
        
        # Execute batch insertion
        db.execute(stmt, insert_data_list)
        db.commit()
        
        logger.info("✅ Batch insertion successful!")
        
        # Verify batch insertion
        ndcs = [data["ndc"] for data in insert_data_list]
        ndc_list = "', '".join(ndcs)
        
        result = db.execute(
            text(f"SELECT COUNT(*) FROM fda_drugs WHERE ndc IN ('{ndc_list}')")
        ).fetchone()
        
        logger.info(f"✅ Verification: {result[0]} out of {len(ndcs)} drugs found in database")
        return result[0] == len(ndcs)
        
    except Exception as e:
        logger.exception(f"❌ Batch insertion failed: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def test_search_functionality():
    """Test search functionality with inserted test data"""
    logger.info("=== Testing Search Functionality ===")
    
    db = get_db_session()
    try:
        # Test basic search
        search_query = text("""
            SELECT ndc, name, generic_name, brand_name, contraindications
            FROM fda_drugs
            WHERE ndc LIKE 'TEST-%'
            ORDER BY ndc
            LIMIT 10
        """)
        
        results = db.execute(search_query).fetchall()
        
        logger.info(f"📊 Found {len(results)} test drugs:")
        for result in results:
            logger.info(f"  NDC: {result[0]}, Name: {result[1]}")
            if result[4]:  # contraindications
                logger.info(f"    Contraindications: {result[4]}")
        
        # Test full-text search (if search vectors are set up)
        try:
            fts_query = text("""
                SELECT ndc, name, ts_rank(search_vector, plainto_tsquery('test')) as rank
                FROM fda_drugs
                WHERE search_vector @@ plainto_tsquery('test')
                ORDER BY rank DESC
                LIMIT 5
            """)
            
            fts_results = db.execute(fts_query).fetchall()
            logger.info(f"📊 Full-text search results: {len(fts_results)} matches")
            for result in fts_results:
                logger.info(f"  {result[0]}: {result[1]} (rank: {result[2]:.3f})")
                
        except Exception as e:
            logger.info(f"ℹ️ Full-text search not available (search vectors may need update): {e}")
        
        return len(results) > 0
        
    except Exception as e:
        logger.exception(f"❌ Search functionality test failed: {e}")
        return False
    finally:
        db.close()

def cleanup_test_data():
    """Clean up test data from database"""
    logger.info("=== Cleaning Up Test Data ===")
    
    db = get_db_session()
    try:
        result = db.execute(
            text("DELETE FROM fda_drugs WHERE ndc LIKE 'TEST-%'")
        )
        db.commit()
        
        logger.info(f"🧹 Deleted {result.rowcount} test records")
        return True
        
    except Exception as e:
        logger.exception(f"❌ Cleanup failed: {e}")
        return False
    finally:
        db.close()

def main():
    """Run all FDA database tests"""
    print("🧪 Starting FDA Database Operations Tests\n")
    
    test_results = []
    
    try:
        # Test 1: Database connection
        test_results.append(("Database Connection", test_database_connection()))
        
        # Test 2: Single drug insertion
        test_results.append(("Single Drug Insertion", test_single_drug_insertion()))
        
        # Test 3: Batch insertion
        test_results.append(("Batch Drug Insertion", test_batch_insertion()))
        
        # Test 4: Search functionality
        test_results.append(("Search Functionality", test_search_functionality()))
        
        # Cleanup
        cleanup_test_data()
        
        # Results summary
        print("\n" + "="*50)
        print("TEST RESULTS SUMMARY")
        print("="*50)
        
        passed = 0
        for test_name, success in test_results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} {test_name}")
            if success:
                passed += 1
        
        print(f"\n📊 {passed}/{len(test_results)} tests passed")
        
        if passed == len(test_results):
            print("\n🎉 All FDA database tests passed!")
            return 0
        else:
            print(f"\n⚠️ {len(test_results) - passed} tests failed")
            return 1
            
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        logger.exception("Test execution failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())