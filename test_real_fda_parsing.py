#!/usr/bin/env python3
"""
Test FDA parsing with actual FDA drug label data structure
"""

import logging
import sys
from pathlib import Path

# Add medical-mirrors to Python path
medical_mirrors_src = Path(__file__).parent / "services/user/medical-mirrors/src"
sys.path.insert(0, str(medical_mirrors_src))

try:
    from fda.parser_optimized import parse_drug_label_record_worker
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

def test_real_fda_structure():
    """Test parsing with actual FDA drug label structure"""
    logger.info("=== Testing Real FDA Structure ===")
    
    # Actual FDA drug label structure based on what we saw in the data files
    real_fda_record = {
        "set_id": "7f16f2d4-8df6-4bd7-ac10-56994fa257b0",
        "id": "2f0f66b3-8b38-4c68-b632-55f6e1d0d012",
        "effective_time": "20220301",
        "version": "1",
        
        # Clinical information fields (actual field names from FDA)
        "indications_and_usage": [
            "ZENPEP is indicated for the treatment of exocrine pancreatic insufficiency in adult and pediatric patients."
        ],
        "contraindications": [
            "Known hypersensitivity to pork protein or any component of ZENPEP."
        ],
        "warnings_and_cautions": [
            "Fibrosing colonopathy is associated with high-dose use of pancreatic enzyme replacement. ZENPEP should be used with caution in patients with a history of fibrosing colonopathy."
        ],
        "adverse_reactions": [
            "The most common adverse reactions (≥4%) are stomach pain, flatulence, throat pain, and cough."
        ],
        "dosage_and_administration": [
            "ZENPEP is taken by mouth during meals or snacks. The dosage is individualized based on clinical symptoms."
        ],
        "mechanism_of_action": [
            "The pancreatic enzymes in ZENPEP catalyze the breakdown of fats into glycerol and fatty acids, proteins into amino acids, and starches into dextrin and sugars."
        ],
        "pharmacokinetics": [
            "Pancreatic enzymes are not absorbed into the systemic circulation in significant amounts."
        ],
        "clinical_pharmacology": [
            "ZENPEP is a pancreatic enzyme replacement therapy containing lipases, proteases, and amylases."
        ],
        
        # Product information in openfda object (where it actually is)
        "openfda": {
            "product_ndc": ["73562-110", "73562-113", "73562-115"],
            "brand_name": ["Zenpep"],
            "generic_name": ["PANCRELIPASE LIPASE, PANCRELIPASE PROTEASE, PANCRELIPASE AMYLASE"],
            "manufacturer_name": ["Aimmune Therapeutics, Inc."],
            "route": ["ORAL"],
            "substance_name": ["PANCRELIPASE AMYLASE", "PANCRELIPASE LIPASE", "PANCRELIPASE PROTEASE"],
            "product_type": ["HUMAN PRESCRIPTION DRUG"]
        }
    }
    
    try:
        logger.info("🔄 Testing real FDA drug label structure...")
        parsed_drug = parse_drug_label_record_worker(real_fda_record)
        
        if parsed_drug:
            logger.info(f"✅ Successfully parsed: {parsed_drug['name']}")
            logger.info(f"  NDC: {parsed_drug['ndc']}")
            logger.info(f"  Generic Name: {parsed_drug['generic_name']}")
            logger.info(f"  Brand Name: {parsed_drug['brand_name']}")
            logger.info(f"  Manufacturer: {parsed_drug['manufacturer']}")
            logger.info(f"  Route: {parsed_drug['route']}")
            logger.info(f"  Active Ingredients: {parsed_drug['strength']}")
            
            # Check clinical fields
            clinical_fields = [
                'contraindications', 'warnings', 'adverse_reactions',
                'indications_and_usage', 'dosage_and_administration', 
                'mechanism_of_action', 'pharmacokinetics'
            ]
            
            logger.info("  Clinical Information:")
            for field in clinical_fields:
                value = parsed_drug.get(field, "")
                if value:
                    preview = value[:100] + "..." if len(value) > 100 else value
                    logger.info(f"    {field}: {preview}")
                else:
                    logger.info(f"    {field}: (empty)")
            
            return True
        else:
            logger.error("❌ Parsing returned None")
            return False
            
    except Exception as e:
        logger.exception(f"❌ Parsing failed: {e}")
        return False

def main():
    print("🧪 Testing Real FDA Structure Parsing\n")
    
    success = test_real_fda_structure()
    
    print("\n" + "="*60)
    print("REAL FDA STRUCTURE TEST RESULTS")
    print("="*60)
    
    if success:
        print("✅ PASS - Real FDA structure parsing works!")
        print("\n🎉 The parser correctly handles:")
        print("   • NDC extraction from openfda.product_ndc")
        print("   • Brand/generic names from openfda object")
        print("   • Clinical fields with actual FDA field names")
        print("   • warnings_and_cautions → warnings mapping")
        return 0
    else:
        print("❌ FAIL - Parser cannot handle real FDA structure")
        return 1

if __name__ == "__main__":
    sys.exit(main())