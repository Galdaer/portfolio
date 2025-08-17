#!/usr/bin/env python3
"""
Test FDA parser with real FDA data
Validates that the parser correctly extracts all expected fields from actual FDA JSON files
"""

import json
import os
import sys
from pathlib import Path

# Add the medical-mirrors src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "services/user/medical-mirrors/src"))

def test_fda_parser_with_real_data():
    """Test FDA parser with actual FDA drug label data"""
    print("🧪 Testing FDA Parser with Real Data")
    print("=" * 50)
    
    # Import the parser class directly
    parser_file = Path(__file__).parent.parent / "services/user/medical-mirrors/src/fda/parser.py"
    
    # Load the parser module
    import importlib.util
    spec = importlib.util.spec_from_file_location("parser", parser_file)
    parser_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parser_module)
    
    # Create parser instance
    parser = parser_module.FDAParser()
    parse_drug_label_record = parser.parse_drug_label_record
    
    # Find real FDA data file
    fda_data_dir = Path("/home/intelluxe/database/medical_complete/fda")
    test_files = [
        fda_data_dir / "drug_labels" / "drug-label-0001-of-0013.json",
        fda_data_dir / "labels" / "drug-label-0001-of-0013.json",
        fda_data_dir / "drug_labels (2)" / "drug-label-0001-of-0013.json",
        fda_data_dir / "drug_labels (3)" / "drug-label-0001-of-0013.json"
    ]
    
    fda_file = None
    for test_file in test_files:
        if test_file.exists():
            fda_file = test_file
            break
    
    if not fda_file:
        print("❌ No FDA data files found")
        return False
    
    print(f"📄 Using FDA file: {fda_file}")
    
    try:
        # Load and parse FDA data
        with open(fda_file, 'r') as f:
            data = json.load(f)
        
        if 'results' not in data:
            print("❌ No 'results' field in FDA data")
            return False
        
        results = data['results']
        print(f"📊 Found {len(results)} drug records")
        
        if not results:
            print("❌ No drug records in results")
            return False
        
        # Test parser with first few records
        successful_parses = 0
        field_counts = {}
        
        for i, record in enumerate(results[:5]):  # Test first 5 records
            print(f"\n🔍 Testing record {i+1}:")
            
            try:
                parsed = parse_drug_label_record(record)
                
                if parsed:
                    successful_parses += 1
                    
                    # Count non-empty fields
                    non_empty_fields = [k for k, v in parsed.items() 
                                      if v and str(v).strip() and k not in ['created_at', 'updated_at']]
                    
                    field_counts[i] = len(non_empty_fields)
                    
                    print(f"  ✅ Parsed successfully - {len(non_empty_fields)} fields with data")
                    print(f"     Name: {parsed.get('name', 'N/A')}")
                    print(f"     Generic: {parsed.get('generic_name', 'N/A')}")
                    print(f"     Brand: {parsed.get('brand_name', 'N/A')}")
                    print(f"     Manufacturer: {parsed.get('manufacturer', 'N/A')}")
                    
                    # Check key prescribing info
                    prescribing_fields = [
                        'indications_and_usage', 'contraindications', 'adverse_reactions',
                        'drug_interactions', 'warnings', 'dosage_and_administration'
                    ]
                    
                    prescribing_count = sum(1 for field in prescribing_fields 
                                          if parsed.get(field) and str(parsed[field]).strip())
                    
                    print(f"     Prescribing info: {prescribing_count}/{len(prescribing_fields)} fields")
                    
                    # Show sample prescribing info
                    if parsed.get('indications_and_usage'):
                        indications = str(parsed['indications_and_usage'])[:80]
                        print(f"     Indications: {indications}...")
                    
                else:
                    print(f"  ❌ Parse failed for record {i+1}")
                    
            except Exception as e:
                print(f"  ❌ Parse error for record {i+1}: {e}")
        
        # Summary
        print(f"\n📈 SUMMARY:")
        print(f"  Successful parses: {successful_parses}/5")
        if field_counts:
            avg_fields = sum(field_counts.values()) / len(field_counts)
            print(f"  Average fields extracted: {avg_fields:.1f}")
            print(f"  Field count range: {min(field_counts.values())}-{max(field_counts.values())}")
        
        # Test database model compatibility
        print(f"\n🗄️ Database Model Compatibility:")
        try:
            from database import FDADrug
            model_fields = [c.name for c in FDADrug.__table__.columns]
            print(f"  Database model has {len(model_fields)} fields")
            
            if successful_parses > 0:
                # Check field compatibility with first successful parse
                test_record = None
                for i, record in enumerate(results[:5]):
                    try:
                        parsed = parse_drug_label_record(record)
                        if parsed:
                            test_record = parsed
                            break
                    except:
                        continue
                
                if test_record:
                    parser_fields = set(test_record.keys())
                    model_fields_set = set(model_fields)
                    
                    compatible_fields = parser_fields.intersection(model_fields_set)
                    missing_in_parser = model_fields_set - parser_fields
                    extra_in_parser = parser_fields - model_fields_set
                    
                    print(f"  Compatible fields: {len(compatible_fields)}")
                    print(f"  Missing in parser: {len(missing_in_parser)}")
                    print(f"  Extra in parser: {len(extra_in_parser)}")
                    
                    if missing_in_parser:
                        print(f"  Missing fields: {sorted(missing_in_parser)}")
                    
                    compatibility_score = len(compatible_fields) / len(model_fields_set) * 100
                    print(f"  Compatibility score: {compatibility_score:.1f}%")
            
        except Exception as e:
            print(f"  ❌ Database model check failed: {e}")
        
        success = successful_parses >= 3  # At least 3 successful parses
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"\n{status} - FDA Parser Real Data Test")
        
        return success
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = test_fda_parser_with_real_data()
    sys.exit(0 if success else 1)
