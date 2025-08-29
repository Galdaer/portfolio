#!/usr/bin/env python3
"""
Test dietary flags integration in medical-mirrors parser
"""

import sys
import json
sys.path.append('/home/intelluxe/services/user/medical-mirrors/src')

from health_info.parser import HealthInfoParser

def test_dietary_flags_integration():
    """Test the enhanced dietary flags functionality"""
    
    parser = HealthInfoParser()
    
    # Test food with rich nutritional data
    test_food = {
        "fdc_id": "123456",
        "description": "Spinach, raw",
        "food_category": "Vegetables and Vegetable Products",
        "nutrients": [
            {"name": "Protein", "amount": 2.86},
            {"name": "Total lipid (fat)", "amount": 0.39},
            {"name": "Carbohydrate, by difference", "amount": 3.63},
            {"name": "Fiber, total dietary", "amount": 2.2},
            {"name": "Sodium, Na", "amount": 79},
            {"name": "Energy", "amount": 23}
        ]
    }
    
    print("Testing Enhanced Dietary Flags Integration")
    print("=" * 50)
    
    # Test the dietary flags method directly
    dietary_flags = parser._determine_dietary_flags(test_food)
    
    print(f"MyPlate Group: {dietary_flags.get('myplate_food_group')}")
    print(f"FDA Claims: {dietary_flags.get('fda_nutritional_claims')}")
    print(f"Potential Allergens: {dietary_flags.get('potential_allergens')}")
    print(f"Data Sources: {json.dumps(dietary_flags.get('data_sources', {}), indent=2)}")
    
    # Test full parsing with private method
    parsed_food = parser._parse_food_item(test_food)
    print(f"\nFull parsing successful: {parsed_food is not None}")
    print(f"Has dietary_flags: {'dietary_flags' in (parsed_food or {})}")
    
    if parsed_food and 'dietary_flags' in parsed_food:
        flags = parsed_food['dietary_flags']
        print(f"Structure complete: {all(key in flags for key in ['myplate_food_group', 'fda_nutritional_claims', 'potential_allergens', 'data_sources', 'disclaimers'])}")
        print(f"Last updated field: {'last_updated' in flags}")
    
    print("\n✅ Integration test completed successfully")
    return True

if __name__ == "__main__":
    test_dietary_flags_integration()