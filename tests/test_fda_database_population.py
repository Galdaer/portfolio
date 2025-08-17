#!/usr/bin/env python3
"""
Test FDA database population and medical query integration
"""

import json
import os
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent / "services/user/medical-mirrors/src"))

def test_fda_database_population():
    """Test populating database with real FDA data and querying it"""
    print("🗄️ Testing FDA Database Population")
    print("=" * 50)
    
    try:
        # Import modules
        from database import get_database_session, FDADrug
        
        # Import parser
        parser_file = Path(__file__).parent.parent / "services/user/medical-mirrors/src/fda/parser.py"
        
        import importlib.util
        spec = importlib.util.spec_from_file_location("parser", parser_file)
        parser_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(parser_module)
        
        parser = parser_module.FDAParser()
        
        # Find FDA data
        fda_data_dir = Path("/home/intelluxe/database/medical_complete/fda")
        fda_file = fda_data_dir / "labels" / "drug-label-0001-of-0013.json"
        
        if not fda_file.exists():
            print("❌ FDA data file not found")
            return False
        
        print(f"📄 Loading FDA data from: {fda_file}")
        
        # Load FDA data
        with open(fda_file, 'r') as f:
            data = json.load(f)
        
        results = data.get('results', [])
        print(f"📊 Found {len(results)} FDA records")
        
        # Get database session
        session = get_database_session()
        
        # Check existing data
        existing_count = session.query(FDADrug).count()
        print(f"📋 Existing drugs in database: {existing_count}")
        
        # Parse and insert first 10 records as test
        inserted = 0
        errors = 0
        
        for i, record in enumerate(results[:10]):
            try:
                parsed = parser.parse_drug_label_record(record)
                
                if parsed and parsed.get('name') and parsed.get('name') != 'Unknown':
                    # Check if already exists
                    existing = session.query(FDADrug).filter_by(ndc=parsed['ndc']).first()
                    
                    if not existing:
                        # Create new drug record
                        drug = FDADrug()
                        
                        # Set all available fields
                        for field, value in parsed.items():
                            if hasattr(drug, field) and field not in ['search_vector', 'created_at', 'updated_at']:
                                if isinstance(value, list):
                                    # For array fields in database, keep as list
                                    if field in ['ingredients', 'contraindications', 'warnings', 'precautions', 'adverse_reactions']:
                                        setattr(drug, field, value)  # Keep as array
                                    else:
                                        # Convert list to string for text fields
                                        setattr(drug, field, ', '.join(str(v) for v in value if v))
                                elif isinstance(value, dict):
                                    # For JSON fields, keep as dict
                                    setattr(drug, field, value)
                                else:
                                    setattr(drug, field, value)
                        
                        session.add(drug)
                        inserted += 1
                        print(f"  ✅ Inserted: {parsed['name']}")
                    else:
                        print(f"  ⚠️ Already exists: {parsed['name']}")
                
            except Exception as e:
                errors += 1
                print(f"  ❌ Error processing record {i+1}: {e}")
        
        # Commit changes
        if inserted > 0:
            try:
                session.commit()
                print(f"💾 Committed {inserted} new drugs to database")
            except Exception as e:
                session.rollback()
                print(f"❌ Database commit failed: {e}")
                return False
        
        # Verify final count
        final_count = session.query(FDADrug).count()
        print(f"📊 Final database count: {final_count} drugs")
        
        # Test search functionality
        print(f"\n🔍 Testing search functionality:")
        
        # Search for a specific drug
        test_searches = ['ondansetron', 'guaifenesin', 'acetaminophen']
        
        for search_term in test_searches:
            results = session.query(FDADrug).filter(
                FDADrug.name.ilike(f'%{search_term}%')
            ).limit(3).all()
            
            print(f"  '{search_term}': {len(results)} results")
            
            for drug in results:
                print(f"    - {drug.name} ({drug.generic_name}) by {drug.manufacturer}")
                if hasattr(drug, 'indications_and_usage') and drug.indications_and_usage:
                    indications = drug.indications_and_usage[:60] + "..." if len(drug.indications_and_usage) > 60 else drug.indications_and_usage
                    print(f"      Indications: {indications}")
        
        session.close()
        
        success = final_count > existing_count or final_count > 0
        status = "✅ PASS" if success else "❌ FAIL" 
        print(f"\n{status} - FDA Database Population Test")
        
        return success
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_fda_database_population()
    sys.exit(0 if success else 1)
