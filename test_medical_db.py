#!/usr/bin/env python3
"""Test script for updated medical_db.py functionality"""

import asyncio
import sys
import os
sys.path.insert(0, '/home/intelluxe/services/user/healthcare-api')

# Set required environment variables
os.environ['POSTGRES_URL'] = 'postgresql://intelluxe:secure_password@localhost:5432/intelluxe'
os.environ['ENVIRONMENT'] = 'development'
os.environ['LOG_LEVEL'] = 'INFO'

from core.database.medical_db import MedicalDatabaseAccess

def print_results(title: str, results: list):
    """Helper to print search results"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    
    if not results:
        print("No results found")
    else:
        print(f"Found {len(results)} results:")
        for i, result in enumerate(results[:3], 1):  # Show first 3 results
            print(f"\n{i}. ", end="")
            if 'name' in result:
                print(f"{result.get('name', 'N/A')}")
            elif 'title' in result:
                print(f"{result.get('title', 'N/A')}")
            elif 'description' in result:
                print(f"{result.get('description', 'N/A')[:100]}...")
            elif 'code' in result:
                print(f"{result.get('code', 'N/A')}: {result.get('description', 'N/A')[:80]}...")
            else:
                print(str(result)[:100] + "...")
                
            # Show source
            source = result.get('source') or result.get('source_type', 'unknown')
            print(f"   Source: {source}")

def test_medical_db():
    """Test all medical database access methods"""
    
    # Initialize database access
    db = MedicalDatabaseAccess()
    
    print("\n" + "="*60)
    print("Testing Medical Database Access Layer")
    print("="*60)
    
    # Test database status
    print("\n1. Testing database status...")
    status = db.get_database_status()
    if status.get('database_available'):
        print("✅ Database is available")
        print("\nTable counts:")
        for table, info in status.get('tables', {}).items():
            if info.get('available'):
                print(f"  - {table}: {info.get('count', 0)} records")
            else:
                print(f"  - {table}: ❌ Not available")
        
        print("\nLast updates:")
        for source, time in status.get('last_updates', {}).items():
            print(f"  - {source}: {time or 'Never'}")
    else:
        print(f"❌ Database error: {status.get('error')}")
        return
    
    # Test PubMed search
    print("\n2. Testing PubMed search...")
    pubmed_results = db.search_pubmed_local("diabetes treatment", max_results=5)
    print_results("PubMed Search Results", pubmed_results)
    
    # Test Clinical Trials search
    print("\n3. Testing Clinical Trials search...")
    trials_results = db.search_clinical_trials_local("COVID-19 vaccine", max_results=5)
    print_results("Clinical Trials Search Results", trials_results)
    
    # Test FDA Drugs search (updated schema)
    print("\n4. Testing FDA Drugs search (new schema)...")
    fda_results = db.search_fda_drugs_local("aspirin", max_results=5)
    print_results("FDA Drugs Search Results", fda_results)
    if fda_results:
        # Show first drug details
        drug = fda_results[0]
        print(f"\nFirst drug details:")
        print(f"  - NDC: {drug.get('ndc', 'N/A')}")
        print(f"  - Generic Name: {drug.get('generic_name', 'N/A')}")
        print(f"  - Brand Name: {drug.get('brand_name', 'N/A')}")
        print(f"  - Manufacturer: {drug.get('manufacturer', 'N/A')}")
        print(f"  - Data Sources: {', '.join(drug.get('data_sources', []))}")
    
    # Test Health Topics search (new)
    print("\n5. Testing Health Topics search (NEW)...")
    topics_results = db.search_health_topics_local("hypertension", max_results=5)
    print_results("Health Topics Search Results", topics_results)
    
    # Test Food Items search (new)
    print("\n6. Testing Food Items search (NEW)...")
    food_results = db.search_food_items_local("apple", max_results=5)
    print_results("Food Items Search Results", food_results)
    if food_results:
        # Show nutrition info for first food
        food = food_results[0]
        print(f"\nNutrition for '{food.get('description', 'N/A')}':")
        print(f"  - Calories: {food.get('calories', 0)}")
        print(f"  - Protein: {food.get('protein', 0)}g")
        print(f"  - Carbs: {food.get('carbohydrates', 0)}g")
        print(f"  - Fat: {food.get('fat', 0)}g")
    
    # Test Exercises search (new)
    print("\n7. Testing Exercises search (NEW)...")
    exercise_results = db.search_exercises_local("push", max_results=5)
    print_results("Exercises Search Results", exercise_results)
    
    # Test with body part filter
    print("\n   Testing with body part filter...")
    chest_exercises = db.search_exercises_local("", body_part="chest", max_results=3)
    if chest_exercises:
        print(f"   Found {len(chest_exercises)} chest exercises")
    
    # Test ICD-10 Codes search (new)
    print("\n8. Testing ICD-10 Codes search (NEW)...")
    icd10_results = db.search_icd10_codes_local("diabetes", max_results=5)
    print_results("ICD-10 Codes Search Results", icd10_results)
    
    # Test exact code match
    print("\n   Testing exact code match...")
    exact_icd10 = db.search_icd10_codes_local("E11.9", exact_match=True)
    if exact_icd10:
        code = exact_icd10[0]
        print(f"   Found: {code.get('code')} - {code.get('description')}")
    
    # Test Billing Codes search (new)
    print("\n9. Testing Billing Codes search (NEW)...")
    billing_results = db.search_billing_codes_local("injection", max_results=5)
    print_results("Billing Codes Search Results", billing_results)
    
    # Test with code type filter
    print("\n   Testing with CPT code type filter...")
    cpt_codes = db.search_billing_codes_local("evaluation", code_type="CPT", max_results=3)
    if cpt_codes:
        print(f"   Found {len(cpt_codes)} CPT codes")
    
    print("\n" + "="*60)
    print("✅ All tests completed successfully!")
    print("="*60)

if __name__ == "__main__":
    try:
        test_medical_db()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()