#!/usr/bin/env python3
"""
Test fuzzy matching capabilities
"""
import sys
sys.path.append('/home/intelluxe/services/user/medical-mirrors/src')

from enhanced_drug_sources.drug_name_matcher import DrugNameMatcher

def test_fuzzy_matching():
    matcher = DrugNameMatcher()
    
    print("🧪 Testing Drug Name Fuzzy Matching")
    
    # Test cases based on our actual data
    test_cases = [
        ("(s)-nicardipine", "NICARDIPINE"),
        ("acetaminophen", "ACETAMINOPHEN"), 
        ("levothyroxine sodium", "LEVOTHYROXINE"),
        ("ibuprofen", "IBUPROFEN"),
        ("aspirin", "ASPIRIN"),
        ("(r)-warfarin", "WARFARIN"),
        ("nicardipine hydrochloride", "NICARDIPINE"),
        ("metformin hcl", "METFORMIN"),
    ]
    
    print("\n📊 Testing individual matches:")
    for source_name, db_name in test_cases:
        score = matcher.get_matching_score(source_name, db_name)
        normalized_source = matcher.normalize_drug_name(source_name)
        normalized_db = matcher.normalize_drug_name(db_name)
        
        print(f"  '{source_name}' → '{db_name}' = {score:.2f}")
        print(f"    Normalized: '{normalized_source}' → '{normalized_db}'")
        print()
    
    # Test with actual DrugCentral data
    print("\n🎯 Testing with sample DrugCentral names:")
    drugcentral_names = ["(s)-nicardipine", "acetaminophen", "amlodipine", "levothyroxine"]
    db_names = ["NICARDIPINE", "ACETAMINOPHEN", "AMLODIPINE", "LEVOTHYROXINE", "METFORMIN", "ASPIRIN"]
    
    lookup_map = matcher.create_lookup_map(drugcentral_names, db_names, threshold=0.7)
    
    for source_name, matched_name in lookup_map.items():
        print(f"  '{source_name}' → '{matched_name}'")

if __name__ == "__main__":
    test_fuzzy_matching()