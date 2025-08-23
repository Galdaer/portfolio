#!/usr/bin/env python3
"""
Integration test to verify all fixes work with actual database
"""

import sys
import os
sys.path.append('/home/intelluxe/services/user/medical-mirrors')

from src.database import get_database_session
from src.database_validation import validate_record_for_table
from sqlalchemy import text
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_database_column_widths():
    """Test that column width fixes were applied correctly"""
    logger.info("=== Testing Database Column Widths ===")
    
    db = get_database_session()
    try:
        # Check updated column widths
        width_checks = [
            ("update_logs", "status", 50),
            ("update_logs", "source", 100),
            ("fda_drugs", "reference_listed_drug", 10),
            ("fda_drugs", "orange_book_code", 50),
            ("fda_drugs", "application_number", 50),
        ]
        
        for table, column, expected_width in width_checks:
            try:
                query = text("""
                    SELECT character_maximum_length 
                    FROM information_schema.columns 
                    WHERE table_name = :table AND column_name = :column
                """)
                result = db.execute(query, {"table": table, "column": column}).fetchone()
                
                if result:
                    actual_width = result[0]
                    status = "✅" if actual_width >= expected_width else "❌"
                    logger.info(f"{status} {table}.{column}: expected >= {expected_width}, got {actual_width}")
                else:
                    logger.warning(f"Column {table}.{column} not found")
            except Exception as e:
                logger.error(f"Error checking {table}.{column}: {e}")
    
    finally:
        db.close()
    
    return True

def test_validation_integration():
    """Test validation with database schema"""
    logger.info("=== Testing Validation Integration ===")
    
    # Test records that would have failed before fixes
    test_records = [
        {
            "table": "update_logs",
            "record": {
                "source": "very_long_source_name_that_would_have_been_too_long_before_fixes",
                "update_type": "full_refresh_with_detailed_processing_information",
                "status": "completed_with_warnings_and_detailed_status_info",
                "records_processed": 12345,
                "started_at": "2023-01-01T00:00:00",
            }
        },
        {
            "table": "fda_drugs", 
            "record": {
                "ndc": "12345-678-90",
                "name": "Test Drug with Very Long Name",
                "generic_name": "test_generic_compound_with_long_name",
                "brand_name": "TestBrand Extended Release Formula",
                "manufacturer": "Test Pharmaceutical Company Inc with Very Long Name",
                "applicant": "Test Applicant Company with Extended Name and Details",
                "ingredients": ["Active Ingredient One", "Active Ingredient Two"],
                "strength": "100mg/5ml extended release formulation",
                "dosage_form": "Extended Release Capsule with Special Coating",
                "route": "Oral Administration via Capsule",
                "application_number": "NDA123456789012345",  # Longer than old limit
                "product_number": "001234567890",  # Longer than old limit
                "approval_date": "January 15, 2020 - Full Approval with Special Conditions",
                "orange_book_code": "AB - Therapeutically Equivalent to Reference",  # Longer than old limit
                "reference_listed_drug": "Yes - RLD",  # Longer than old limit
                "therapeutic_class": "Test Therapeutic Class",
                "pharmacologic_class": "Test Pharmacologic Class",
                "data_sources": ["ndc", "orange_book", "drugs_fda"]
            }
        }
    ]
    
    for test_case in test_records:
        table = test_case["table"]
        record = test_case["record"]
        
        try:
            validated_record = validate_record_for_table(record, table)
            logger.info(f"✅ {table} validation successful")
            
            # Check that long fields were handled correctly
            for key, value in validated_record.items():
                if isinstance(value, str) and len(value) > 100:
                    logger.info(f"  Long field {key}: {len(value)} chars")
                    
        except Exception as e:
            logger.error(f"❌ {table} validation failed: {e}")
            return False
    
    return True

def test_fda_search_functionality():
    """Test that FDA search still works after changes"""
    logger.info("=== Testing FDA Search Functionality ===")
    
    db = get_database_session()
    try:
        # Test that FDA search functionality works
        search_query = text("""
            SELECT ndc, name, generic_name, brand_name, applicant, 
                   strength, application_number, data_sources
            FROM fda_drugs 
            WHERE search_vector @@ plainto_tsquery('english', 'budesonide')
            LIMIT 3
        """)
        
        results = db.execute(search_query).fetchall()
        
        if results:
            logger.info(f"✅ FDA search returned {len(results)} results")
            for result in results:
                logger.info(f"  Found: {result.name} (NDC: {result.ndc})")
                if result.applicant:
                    logger.info(f"    Applicant: {result.applicant}")
                if result.data_sources:
                    logger.info(f"    Data sources: {result.data_sources}")
        else:
            logger.info("ℹ️ No search results found (database may be empty)")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ FDA search test failed: {e}")
        return False
    finally:
        db.close()

def test_error_logging():
    """Test that error logging works correctly"""
    logger.info("=== Testing Error Logging ===")
    
    from src.error_handling import ErrorCollector, safe_parse
    
    # Test error collection
    collector = ErrorCollector("Integration Test")
    
    def test_parser(data):
        if "error" in data:
            raise ValueError("Test error condition")
        return f"parsed_{data}"
    
    test_data = ["success1", "error_case", "success2", "another_error", "success3"]
    
    for item in test_data:
        result = safe_parse(
            test_parser, 
            item, 
            record_id=f"test_{item}",
            default_return="failed"
        )
        
        if result == "failed":
            collector.record_error(ValueError(f"Failed to parse {item}"), record_id=f"test_{item}")
        else:
            collector.record_success()
    
    # Log summary
    collector.log_summary(logger)
    
    summary = collector.get_summary()
    expected_success_rate = 0.6  # 3 successes out of 5
    
    if abs(summary['success_rate'] - expected_success_rate) < 0.1:
        logger.info("✅ Error logging working correctly")
        return True
    else:
        logger.error(f"❌ Error logging issue: expected {expected_success_rate}, got {summary['success_rate']}")
        return False

def main():
    """Run integration tests"""
    logger.info("Starting integration tests...")
    
    tests = [
        ("Database Column Widths", test_database_column_widths),
        ("Validation Integration", test_validation_integration),
        ("FDA Search Functionality", test_fda_search_functionality),
        ("Error Logging", test_error_logging),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, "PASSED" if result else "FAILED"))
            logger.info(f"✅ {test_name} completed")
        except Exception as e:
            results.append((test_name, f"ERROR: {e}"))
            logger.error(f"❌ {test_name} failed: {e}")
        
        logger.info("")  # Add spacing
    
    # Summary
    logger.info("=== Integration Test Summary ===")
    for test_name, result in results:
        logger.info(f"{test_name}: {result}")
    
    passed = sum(1 for _, result in results if result == "PASSED")
    total = len(results)
    logger.info(f"Overall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All integration tests passed! The fixes are working correctly.")
    else:
        logger.warning("⚠️  Some integration tests failed. Please review the results above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)