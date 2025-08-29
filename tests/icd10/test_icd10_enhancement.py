#!/usr/bin/env python3
"""
Test script to validate ICD10 enhancement fixes for category and search vector coverage
"""

import json
from src.icd10.parser import ICD10Parser
from src.icd10.database_loader import ICD10DatabaseLoader
from src.database import get_db_session
from sqlalchemy import text

def test_parser_enhancements():
    """Test the enhanced parser for category population"""
    print("=== TESTING ENHANCED ICD10 PARSER ===")
    
    # Test data simulating current database issues
    test_codes = [
        {
            "code": "E11.9",
            "description": "Type 2 diabetes mellitus without complications",
            "chapter": "E00-E89",
            "synonyms": ["Adult-onset diabetes", "NIDDM"],
            "source": "test"
            # Note: No category provided - should be populated by parser
        },
        {
            "code": "I10",
            "description": "Essential (primary) hypertension", 
            "chapter": "I00-I99",
            "synonyms": ["High blood pressure"],
            "source": "test"
            # Note: No category provided - should be populated by parser
        },
        {
            "code": "J44.0",
            "description": "Chronic obstructive pulmonary disease with acute lower respiratory infection",
            "synonyms": ["COPD with infection"],
            "source": "test"
            # Note: No chapter or category - should be populated
        },
        {
            "code": "S72.001A", 
            "description": "Fracture of unspecified part of neck of right femur, initial encounter",
            "category": "Injury and poisoning",  # Has existing category
            "source": "test"
        }
    ]
    
    parser = ICD10Parser()
    parsed_codes = parser.parse_and_validate(test_codes)
    
    print(f"Parsed {len(parsed_codes)} codes:")
    
    category_count = 0
    for code in parsed_codes:
        category = code.get("category", "")
        has_category = bool(category and category.strip())
        if has_category:
            category_count += 1
            
        print(f"  {code['code']}: {code['description'][:50]}...")
        print(f"    Category: '{category}' {'✅' if has_category else '❌'}")
        print(f"    Search Text: {code['search_text'][:80]}...")
        print()
    
    coverage_pct = category_count / len(parsed_codes) * 100 if parsed_codes else 0
    print(f"Category coverage: {category_count}/{len(parsed_codes)} ({coverage_pct:.1f}%)")
    
    if coverage_pct >= 95:
        print("🎉 SUCCESS: Parser fixes work - high category coverage!")
    else:
        print("⚠️  ISSUE: Parser still has category coverage problems")
    
    return parsed_codes


def test_database_loader(test_codes):
    """Test the enhanced database loader"""
    print("\n=== TESTING ENHANCED DATABASE LOADER ===")
    
    loader = ICD10DatabaseLoader()
    
    # Test the enhancement process
    enhanced_codes = loader._enhance_codes_data(test_codes)
    
    print(f"Enhanced {len(enhanced_codes)} codes:")
    
    category_count = 0
    for code in enhanced_codes:
        category = code.get("category", "")
        has_category = bool(category and category.strip())
        if has_category:
            category_count += 1
            
        print(f"  {code['code']}: Category: '{category}' {'✅' if has_category else '❌'}")
    
    coverage_pct = category_count / len(enhanced_codes) * 100 if enhanced_codes else 0
    print(f"Enhanced category coverage: {category_count}/{len(enhanced_codes)} ({coverage_pct:.1f}%)")
    
    # Test database loading (small subset)
    print("\nTesting database loading...")
    try:
        stats = loader.load_codes(enhanced_codes[:2])  # Small test
        print(f"Database loading test results: {stats}")
        return True
    except Exception as e:
        print(f"Database loading test failed: {e}")
        return False


def analyze_current_issues():
    """Analyze current database state"""
    print("\n=== CURRENT DATABASE STATE ANALYSIS ===")
    
    with get_db_session() as db:
        result = db.execute(text("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN category IS NOT NULL AND category != '' THEN 1 END) as with_category,
                COUNT(CASE WHEN search_vector IS NOT NULL THEN 1 END) as with_search_vector,
                COUNT(CASE WHEN search_text IS NOT NULL AND search_text != '' THEN 1 END) as with_search_text
            FROM icd10_codes
        """)).fetchone()
        
        print(f"Current database state:")
        print(f"  Total codes: {result.total:,}")
        print(f"  With category: {result.with_category:,} ({result.with_category/result.total*100:.2f}%)")
        print(f"  With search_vector: {result.with_search_vector:,} ({result.with_search_vector/result.total*100:.2f}%)")
        print(f"  With search_text: {result.with_search_text:,} ({result.with_search_text/result.total*100:.2f}%)")
        
        return result


def main():
    """Run comprehensive test of ICD10 enhancements"""
    print("🚀 TESTING ICD10 DATA QUALITY FIXES")
    print("=" * 50)
    
    # Analyze current state
    current_state = analyze_current_issues()
    
    # Test parser enhancements  
    parsed_codes = test_parser_enhancements()
    
    # Test database loader
    db_success = test_database_loader(parsed_codes)
    
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    
    category_issue = current_state.with_category / current_state.total * 100 < 5
    search_vector_issue = current_state.with_search_vector / current_state.total * 100 < 95
    
    if category_issue:
        print("❌ Category coverage issue confirmed (< 5%)")
        print("✅ Parser enhancements should fix this")
    
    if search_vector_issue:
        print("❌ Search vector coverage issue confirmed (< 95%)")
        print("✅ Database loader should fix this")
    
    if db_success:
        print("✅ Database loader test passed")
        
    print("\n🎯 NEXT STEPS:")
    print("1. Run: QUICK_TEST=true ./update-scripts/update_icd10.sh")
    print("2. Verify field coverage improvements")
    print("3. Run full update if test successful")


if __name__ == "__main__":
    main()