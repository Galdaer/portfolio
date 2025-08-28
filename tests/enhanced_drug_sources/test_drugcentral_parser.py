#!/usr/bin/env python3
"""
Test DrugCentral parser directly
"""
import sys
sys.path.append('/home/intelluxe/services/user/medical-mirrors/src')

from enhanced_drug_sources.drugcentral_parser import DrugCentralParser

def test_drugcentral():
    parser = DrugCentralParser()
    
    print("Testing DrugCentral parser...")
    print("Parsing mechanism_of_action.json...")
    
    mechanism_data = parser.parse_mechanism_of_action_file(
        "/home/intelluxe/database/medical_complete/enhanced_drug_data/drugcentral/mechanism_of_action.json"
    )
    
    print(f"Found mechanism data for {len(mechanism_data)} drugs")
    if mechanism_data:
        # Show first few entries
        for i, (drug_key, moa_text) in enumerate(list(mechanism_data.items())[:3]):
            print(f"  {drug_key}: {moa_text[:100]}...")
            if i >= 2:
                break

if __name__ == "__main__":
    test_drugcentral()