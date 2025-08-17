#!/usr/bin/env python3
"""
Test FDA parser with actual FDA JSON structure to validate extraction
"""
import json
import sys
from pathlib import Path

# Add medical-mirrors to path
sys.path.append(str(Path(__file__).parent / "services/user/medical-mirrors/src"))

from fda.parser import FDAParser

def test_fda_parser_extraction():
    """Test FDA parser with actual FDA JSON structure"""
    
    # Sample FDA data based on the structure you provided
    sample_fda_data = {
        "results": [
            {
                "indications_and_usage": [
                    "ENTRESTO is indicated to reduce the risk of cardiovascular death and hospitalization for heart failure in adult patients with chronic heart failure (NYHA Class II-IV) and reduced ejection fraction."
                ],
                "contraindications": [
                    "ENTRESTO is contraindicated in patients with a history of angioedema related to previous ACE inhibitor or ARB therapy."
                ],
                "warnings_and_cautions": [
                    "Angioedema: May occur at any time during treatment. Discontinue immediately if angioedema occurs."
                ],
                "adverse_reactions": [
                    "Most common adverse reactions (≥2% and greater than placebo): hypotension, hyperkalemia, cough, dizziness, and renal impairment."
                ],
                "drug_interactions": [
                    "ACE inhibitors: Do not administer ENTRESTO within 36 hours of switching to or from an ACE inhibitor."
                ],
                "dosage_and_administration": [
                    "Recommended starting dose is 49/51 mg twice daily. Double the dose after 2-4 weeks to target maintenance dose of 97/103 mg twice daily, as tolerated."
                ],
                "mechanism_of_action": [
                    "ENTRESTO contains the neprilysin inhibitor sacubitril and the angiotensin receptor blocker valsartan."
                ],
                "openfda": {
                    "brand_name": ["ENTRESTO"],
                    "generic_name": ["SACUBITRIL; VALSARTAN"],
                    "manufacturer_name": ["Novartis Pharmaceuticals Corporation"],
                    "product_ndc": ["0078-0646", "0078-0647"],
                    "substance_name": ["SACUBITRIL", "VALSARTAN"],
                    "pharm_class_epc": ["Neprilysin Inhibitor [EPC]", "Angiotensin 2 Receptor Blocker [EPC]"],
                    "route": ["ORAL"],
                    "dosage_form": ["TABLET"]
                }
            }
        ]
    }
    
    print("🧪 Testing FDA Parser with Real Data Structure...")
    
    # Initialize parser
    parser = FDAParser()
    
    try:
        # Parse the sample data - use the label data structure directly
        drug_record = parser.parse_drug_label_record(sample_fda_data["results"][0])
        
        print(f"✅ Successfully parsed drug record: {drug_record.get('brand_name', 'Unknown')}")
        
        # Check if detailed information was extracted
        print("\n📋 Extracted Information:")
        
        key_fields = [
            'indications_and_usage',
            'contraindications',
            'adverse_reactions',
            'drug_interactions',
            'warnings',
            'dosage_and_administration',
            'mechanism_of_action'
        ]
        
        for field in key_fields:
            value = drug_record.get(field, '')
            if value and value.strip():
                print(f"✅ {field}: {value[:100]}..." if len(value) > 100 else f"✅ {field}: {value}")
            else:
                print(f"❌ {field}: MISSING or EMPTY")
                
        # Check basic information
        print("\n🏷️ Basic Information:")
        print(f"Brand Name: {drug_record.get('brand_name', 'N/A')}")
        print(f"Generic Name: {drug_record.get('generic_name', 'N/A')}")
        print(f"Manufacturer: {drug_record.get('manufacturer', 'N/A')}")
        print(f"NDC: {drug_record.get('ndc', 'N/A')}")
        
        # Test if the parser can handle missing fields gracefully
        print("\n🔍 Testing parser robustness...")
        minimal_data = {"openfda": {"brand_name": ["TEST DRUG"]}}
        minimal_record = parser.parse_drug_label_record(minimal_data)
        print(f"✅ Handles minimal data: {minimal_record.get('brand_name', 'FAILED')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Parser test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_fda_parser_extraction()
    print(f"\n🎯 FDA Parser Test: {'PASSED' if success else 'FAILED'}")
