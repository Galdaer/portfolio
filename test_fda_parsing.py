#!/usr/bin/env python3
"""
Test script for FDA drug label parsing
Tests the parsing logic in isolation to identify issues
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add medical-mirrors to Python path
medical_mirrors_src = Path(__file__).parent / "services/user/medical-mirrors/src"
sys.path.insert(0, str(medical_mirrors_src))

try:
    from fda.parser_optimized import _extract_text_field, parse_drug_label_record_worker
except ImportError as e:
    print(f"Failed to import FDA parser modules: {e}")
    print(f"Looking for modules in: {medical_mirrors_src}")
    sys.exit(1)

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_sample_fda_label_data() -> List[Dict[str, Any]]:
    """Create sample FDA drug label data for testing"""
    return [
        {
            "product_ndc": ["0777-3105"],
            "brand_name": ["Tylenol"],
            "generic_name": ["acetaminophen"],
            "manufacturer_name": ["Johnson & Johnson"],
            "dosage_form": ["tablet"],
            "route": ["oral"],
            "active_ingredient": ["acetaminophen 325 mg"],
            
            # Clinical information fields (complex structures)
            "contraindications": [
                "Known hypersensitivity to acetaminophen or any component of the product."
            ],
            "warnings": [
                "Liver warning: This product contains acetaminophen. "
                "Severe liver damage may occur if you take more than 4,000 mg of acetaminophen in 24 hours."
            ],
            "precautions": [
                "Do not exceed recommended dose.",
                "Consult a healthcare provider before use if you have liver disease."
            ],
            "adverse_reactions": [
                "Nausea", "Vomiting", "Constipation", "Dizziness", "Drowsiness"
            ],
            "drug_interactions": [
                {
                    "drug_name": "Warfarin",
                    "interaction": "May increase anticoagulant effect"
                }
            ],
            "indications_and_usage": "For the temporary relief of minor aches and pains due to headache, muscular aches, backache, minor pain of arthritis, the common cold, toothache, premenstrual and menstrual cramps, and for reduction of fever.",
            "dosage_and_administration": "Adults and children 12 years and over: Take 2 tablets every 4 to 6 hours while symptoms persist. Do not take more than 8 tablets in 24 hours.",
            "mechanism_of_action": "Acetaminophen is a centrally acting analgesic and antipyretic agent. The mechanism of action is not completely understood but is thought to involve inhibition of cyclooxygenase (COX) enzymes in the central nervous system.",
            "pharmacokinetics": "Acetaminophen is rapidly absorbed from the gastrointestinal tract with peak plasma concentrations occurring about 30 minutes to 2 hours after ingestion.",
            "pharmacodynamics": "The analgesic and antipyretic effects of acetaminophen are mediated through inhibition of prostaglandin synthesis in the central nervous system."
        },
        {
            # More complex example with nested structures
            "product_ndc": ["12345-678"],
            "brand_name": ["TestDrug"],
            "generic_name": ["testcompound"],
            "manufacturer_name": ["Test Pharma"],
            "dosage_form": ["injection"],
            "route": ["intravenous"],
            "active_ingredient": ["testcompound 50mg/mL"],
            
            # Complex nested clinical data
            "contraindications": {
                "text": "Contraindicated in patients with severe renal impairment (creatinine clearance <30 mL/min)."
            },
            "warnings": {
                "content": [
                    "Black Box Warning: Increased risk of serious cardiovascular thrombotic events.",
                    "May cause serious gastrointestinal adverse events."
                ]
            },
            "drug_interactions": {
                "major_interactions": [
                    {"drug": "Aspirin", "severity": "Major", "description": "Increased bleeding risk"},
                    {"drug": "Lithium", "severity": "Moderate", "description": "Increased lithium levels"}
                ]
            },
            "indications_and_usage": {
                "text": "Indicated for the treatment of moderate to severe pain in adult patients."
            }
        }
    ]

def test_extract_text_field():
    """Test the _extract_text_field function with various input types"""
    logger.info("=== Testing _extract_text_field function ===")
    
    test_cases = [
        # Simple string
        ("Simple string", "Expected: Simple string"),
        
        # List with single string
        (["Single item"], "Expected: Single item"),
        
        # List with multiple strings
        (["Item 1", "Item 2", "Item 3"], "Expected: Item 1; Item 2; Item 3"),
        
        # Dict with 'text' key
        ({"text": "Text from dict"}, "Expected: Text from dict"),
        
        # Dict with 'content' key
        ({"content": "Content from dict"}, "Expected: Content from dict"),
        
        # Complex nested dict
        ({"content": ["Warning 1", "Warning 2"]}, "Expected: ['Warning 1', 'Warning 2']"),
        
        # None/empty cases
        (None, "Expected: (empty)"),
        ("", "Expected: (empty)"),
        ([], "Expected: (empty)"),
    ]
    
    for i, (input_data, expected_desc) in enumerate(test_cases, 1):
        result = _extract_text_field(input_data)
        logger.info(f"Test {i}: {expected_desc}")
        logger.info(f"  Input: {input_data}")
        logger.info(f"  Result: '{result}'")
        logger.info("")

def test_drug_label_parsing():
    """Test parsing of sample FDA drug label data"""
    logger.info("=== Testing FDA Drug Label Parsing ===")
    
    sample_data = create_sample_fda_label_data()
    
    for i, label_data in enumerate(sample_data, 1):
        logger.info(f"Testing drug label {i}: {label_data.get('brand_name', 'Unknown')}")
        
        try:
            parsed_drug = parse_drug_label_record_worker(label_data)
            
            if parsed_drug:
                logger.info("✅ Parsing successful!")
                logger.info(f"  NDC: {parsed_drug.get('ndc')}")
                logger.info(f"  Name: {parsed_drug.get('name')}")
                logger.info(f"  Generic: {parsed_drug.get('generic_name')}")
                logger.info(f"  Brand: {parsed_drug.get('brand_name')}")
                
                # Check clinical information fields
                clinical_fields = [
                    'contraindications', 'warnings', 'precautions', 
                    'adverse_reactions', 'drug_interactions',
                    'indications_and_usage', 'dosage_and_administration',
                    'mechanism_of_action', 'pharmacokinetics', 'pharmacodynamics'
                ]
                
                logger.info("  Clinical Information:")
                for field in clinical_fields:
                    value = parsed_drug.get(field)
                    if value:
                        # Truncate long values for readability
                        if isinstance(value, str) and len(value) > 100:
                            display_value = value[:100] + "..."
                        elif isinstance(value, list) and len(str(value)) > 100:
                            display_value = str(value)[:100] + "..."
                        elif isinstance(value, dict):
                            display_value = f"Dict with {len(value)} keys"
                        else:
                            display_value = value
                        logger.info(f"    {field}: {display_value}")
                
            else:
                logger.warning("❌ Parsing returned None")
                
        except Exception as e:
            logger.exception(f"❌ Parsing failed for drug {i}: {e}")
        
        logger.info("-" * 50)

def test_data_type_compatibility():
    """Test that parsed data types match database schema expectations"""
    logger.info("=== Testing Data Type Compatibility ===")
    
    sample_data = create_sample_fda_label_data()
    parsed_drugs = []
    
    for label_data in sample_data:
        try:
            parsed_drug = parse_drug_label_record_worker(label_data)
            if parsed_drug:
                parsed_drugs.append(parsed_drug)
        except Exception as e:
            logger.error(f"Failed to parse drug: {e}")
    
    # Expected types based on database schema
    expected_types = {
        'ndc': str,
        'name': str,
        'generic_name': str,
        'brand_name': str,
        'manufacturer': str,
        'ingredients': list,  # ARRAY(String) in DB
        'strength': str,
        'dosage_form': str,
        'route': str,
        'contraindications': list,  # ARRAY(String) in DB
        'warnings': list,  # ARRAY(String) in DB
        'precautions': list,  # ARRAY(String) in DB
        'adverse_reactions': list,  # ARRAY(String) in DB
        'drug_interactions': dict,  # JSON in DB
        'indications_and_usage': str,  # Text in DB
        'dosage_and_administration': str,  # Text in DB
        'mechanism_of_action': str,  # Text in DB
        'pharmacokinetics': str,  # Text in DB
        'pharmacodynamics': str,  # Text in DB
        'data_sources': list,  # ARRAY(String) in DB
    }
    
    type_issues = []
    
    for drug in parsed_drugs:
        drug_name = drug.get('name', 'Unknown')
        logger.info(f"Checking types for: {drug_name}")
        
        for field, expected_type in expected_types.items():
            if field in drug:
                actual_value = drug[field]
                actual_type = type(actual_value)
                
                if actual_type != expected_type:
                    issue = f"  ❌ {field}: expected {expected_type.__name__}, got {actual_type.__name__} ({actual_value})"
                    logger.warning(issue)
                    type_issues.append((drug_name, field, expected_type, actual_type, actual_value))
                else:
                    logger.debug(f"  ✅ {field}: {expected_type.__name__}")
    
    if type_issues:
        logger.error(f"\n🚨 Found {len(type_issues)} type compatibility issues:")
        for drug_name, field, expected, actual, value in type_issues:
            logger.error(f"  {drug_name}.{field}: expected {expected.__name__}, got {actual.__name__}")
    else:
        logger.info("✅ All data types compatible with database schema")

def main():
    """Run all FDA parsing tests"""
    print("🧪 Starting FDA Drug Label Parsing Tests\n")
    
    try:
        # Test individual functions
        test_extract_text_field()
        
        # Test full parsing workflow
        test_drug_label_parsing()
        
        # Test database compatibility
        test_data_type_compatibility()
        
        print("\n✅ FDA parsing tests completed!")
        
    except Exception as e:
        print(f"\n❌ Tests failed: {e}")
        logger.exception("Test execution failed")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())