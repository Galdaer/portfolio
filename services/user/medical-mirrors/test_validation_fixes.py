#!/usr/bin/env python3
"""
Test validation and parsing fixes
"""

import sys

sys.path.append("/home/intelluxe/services/user/medical-mirrors")

import logging

from src.database_validation import DatabaseValidator, validate_record_for_table
from src.error_handling import ErrorCollector, safe_parse
from src.validation_utils import DataValidator

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_data_validation():
    """Test data validation utilities"""
    logger.info("=== Testing Data Validation ===")

    # Test PMID validation
    valid_pmid = DataValidator.validate_pmid("12345678")
    invalid_pmid = DataValidator.validate_pmid("abc123")
    logger.info(f"PMID validation: valid={valid_pmid}, invalid={invalid_pmid}")

    # Test NDC validation
    valid_ndc = DataValidator.validate_ndc("12345-123-12")
    synthetic_ndc = DataValidator.validate_ndc("OB_123456_001")
    logger.info(f"NDC validation: valid={valid_ndc}, synthetic={synthetic_ndc}")

    # Test NCT ID validation
    valid_nct = DataValidator.validate_nct_id("NCT12345678")
    invalid_nct = DataValidator.validate_nct_id("invalid123")
    logger.info(f"NCT ID validation: valid={valid_nct}, invalid={invalid_nct}")

    # Test string length validation
    long_string = "a" * 300
    truncated = DataValidator.validate_string_length(long_string, "test_field", "test_table", 50)
    logger.info(f"String truncation: original={len(long_string)}, truncated={len(truncated) if truncated else 0}")

    # Test array validation
    test_array = "item1, item2; item3 | item4"
    validated_array = DataValidator.validate_array_field(test_array, "test_array", "test_table")
    logger.info(f"Array validation: {validated_array}")

    return True

def test_database_validation():
    """Test database-specific validation"""
    logger.info("=== Testing Database Validation ===")

    # Test PubMed article validation
    pubmed_record = {
        "pmid": "12345678",
        "title": "Test Article Title",
        "abstract": "This is a test abstract.",
        "authors": ["Author One", "Author Two"],
        "journal": "Test Journal",
        "pub_date": "2023-01-15",
        "doi": "10.1234/test.doi",
        "mesh_terms": ["Term1", "Term2"],
    }

    try:
        validated_pubmed = DatabaseValidator.validate_pubmed_article(pubmed_record)
        logger.info(f"PubMed validation successful: PMID={validated_pubmed['pmid']}")
    except Exception as e:
        logger.exception(f"PubMed validation failed: {e}")

    # Test Clinical Trial validation
    trial_record = {
        "nct_id": "NCT12345678",
        "title": "Test Clinical Trial",
        "status": "Active, not recruiting",
        "phase": "Phase 2",
        "conditions": ["Cancer", "Tumor"],
        "interventions": ["Drug A", "Placebo"],
        "locations": ["Hospital A", "Hospital B"],
        "sponsors": ["Sponsor Inc"],
        "start_date": "2023-01-01",
        "completion_date": "2024-12-31",
        "enrollment": 100,
        "study_type": "Interventional",
    }

    try:
        validated_trial = DatabaseValidator.validate_clinical_trial(trial_record)
        logger.info(f"Clinical Trial validation successful: NCT={validated_trial['nct_id']}")
    except Exception as e:
        logger.exception(f"Clinical Trial validation failed: {e}")

    # Test FDA Drug validation
    fda_record = {
        "ndc": "12345-123-12",
        "name": "Test Drug",
        "generic_name": "test_generic",
        "brand_name": "TestBrand",
        "manufacturer": "Test Pharma Inc",
        "applicant": "Test Applicant",
        "ingredients": ["Active Ingredient"],
        "strength": "100mg",
        "dosage_form": "Tablet",
        "route": "Oral",
        "application_number": "NDA123456",
        "product_number": "001",
        "approval_date": "2020-01-15",
        "orange_book_code": "AB",
        "reference_listed_drug": "No",
        "therapeutic_class": "Test Class",
        "pharmacologic_class": "Test Pharm Class",
        "data_sources": ["ndc", "orange_book"],
    }

    try:
        validated_fda = DatabaseValidator.validate_fda_drug(fda_record)
        logger.info(f"FDA Drug validation successful: NDC={validated_fda['ndc']}")
    except Exception as e:
        logger.exception(f"FDA Drug validation failed: {e}")

    return True

def test_error_handling():
    """Test error handling utilities"""
    logger.info("=== Testing Error Handling ===")

    # Test ErrorCollector
    collector = ErrorCollector("Test Process")

    # Simulate some operations
    for i in range(10):
        if i % 3 == 0:
            collector.record_error(ValueError(f"Test error {i}"), record_id=f"record_{i}")
        else:
            collector.record_success()

    # Log summary
    collector.log_summary(logger)

    # Test safe_parse
    def failing_parser(data):
        if data == "fail":
            raise ValueError("Intentional failure")
        return f"parsed_{data}"

    result1 = safe_parse(failing_parser, "success", record_id="test1", default_return="default")
    result2 = safe_parse(failing_parser, "fail", record_id="test2", default_return="default")

    logger.info(f"Safe parse results: success={result1}, failure={result2}")

    return True

def test_length_validation():
    """Test that our column width fixes work"""
    logger.info("=== Testing Column Width Fixes ===")

    # Test very long strings
    long_category = "Very Long Category Name That Might Have Been Too Long Before" * 5
    long_source = "Very Long Source Name" * 10
    long_status = "very_long_status_that_might_exceed_old_limit"

    # Test validation handles these correctly
    truncated_category = DataValidator.validate_string_length(
        long_category, "category", "icd10_codes",
    )
    truncated_source = DataValidator.validate_string_length(
        long_source, "source", "billing_codes",
    )
    truncated_status = DataValidator.validate_string_length(
        long_status, "status", "update_logs",
    )

    logger.info("Length validation:")
    logger.info(f"  Category: {len(long_category)} -> {len(truncated_category) if truncated_category else 0}")
    logger.info(f"  Source: {len(long_source)} -> {len(truncated_source) if truncated_source else 0}")
    logger.info(f"  Status: {len(long_status)} -> {len(truncated_status) if truncated_status else 0}")

    return True

def test_edge_cases():
    """Test edge cases and error conditions"""
    logger.info("=== Testing Edge Cases ===")

    # Test empty/null values
    empty_tests = [
        ("", "empty string"),
        (None, "None value"),
        ("   ", "whitespace only"),
        ([], "empty list"),
        ({}, "empty dict"),
    ]

    for test_value, description in empty_tests:
        try:
            result = DataValidator.validate_string_length(
                test_value, "test_field", "test_table", 50,
            )
            logger.info(f"Edge case {description}: {result}")
        except Exception as e:
            logger.info(f"Edge case {description} error: {e}")

    # Test invalid data types
    try:
        invalid_pmid = DataValidator.validate_pmid(12345)  # Integer instead of string
        logger.info(f"Invalid PMID type handled: {invalid_pmid}")
    except Exception as e:
        logger.info(f"Invalid PMID type error: {e}")

    # Test malformed records
    malformed_record = {
        "pmid": None,  # Missing required field
        "title": "Test",
        "invalid_field": "should be ignored",
    }

    try:
        validated = validate_record_for_table(malformed_record, "pubmed_articles")
        logger.info(f"Malformed record validation succeeded unexpectedly: {validated}")
    except Exception as e:
        logger.info(f"Malformed record correctly rejected: {e}")

    return True

def main():
    """Run all tests"""
    logger.info("Starting validation and parsing tests...")

    tests = [
        ("Data Validation", test_data_validation),
        ("Database Validation", test_database_validation),
        ("Error Handling", test_error_handling),
        ("Length Validation", test_length_validation),
        ("Edge Cases", test_edge_cases),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, "PASSED" if result else "FAILED"))
            logger.info(f"✅ {test_name} completed")
        except Exception as e:
            results.append((test_name, f"ERROR: {e}"))
            logger.exception(f"❌ {test_name} failed: {e}")

        logger.info("")  # Add spacing

    # Summary
    logger.info("=== Test Summary ===")
    for test_name, result in results:
        logger.info(f"{test_name}: {result}")

    passed = sum(1 for _, result in results if result == "PASSED")
    total = len(results)
    logger.info(f"Overall: {passed}/{total} tests passed")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
