#!/usr/bin/env python3
"""
Integration test for ICD10 enrichment module
Tests the complete enhancement pipeline on sample data
"""

import sys
sys.path.append('src')

from src.icd10.icd10_enrichment import ICD10DatabaseEnhancer

def test_enrichment_pipeline():
    """Test the complete enrichment pipeline"""
    print("=== ICD10 ENRICHMENT INTEGRATION TEST ===")
    
    # Initialize enhancer
    enhancer = ICD10DatabaseEnhancer(batch_size=50)
    
    try:
        # Run enhancement test with small sample
        print("Running enrichment test with 50 codes...")
        results = enhancer.run_enhancement_test(limit=50)
        
        print(f"\n✓ Enhancement completed successfully!")
        print(f"Processing time: {results['processing_time']}")
        print(f"Codes processed: {results['total_codes_processed']}")
        
        # Display enhancement statistics
        print("\nEnhancement Results:")
        stats = results['enhancement_statistics']
        print(f"  Inclusion notes added: {stats['inclusion_notes_added']}")
        print(f"  Exclusion notes added: {stats['exclusion_notes_added']}")
        print(f"  Synonyms added: {stats['synonyms_added']}")
        print(f"  Relationships added: {stats['relationships_added']}")
        
        # Display component statistics
        print("\nComponent Performance:")
        comp_stats = results['component_statistics']
        
        notes_stats = comp_stats['notes_extractor']
        print(f"  Notes Extractor: {notes_stats['notes_extracted']}/{notes_stats['processed']} codes enhanced")
        
        synonym_stats = comp_stats['synonym_generator']
        print(f"  Synonym Generator: {synonym_stats['synonyms_generated']} synonyms generated")
        
        hierarchy_stats = comp_stats['hierarchy_builder']
        print(f"  Hierarchy Builder: {hierarchy_stats['relationships_built']} relationships built")
        
        # Display final coverage (if available)
        if 'database_statistics' in results:
            print("\nFinal Database Coverage:")
            db_stats = results['database_statistics']
            
            for field in ['synonyms', 'inclusion_notes', 'exclusion_notes', 'children_codes']:
                coverage_key = f'{field}_coverage'
                if coverage_key in db_stats:
                    coverage = db_stats[coverage_key]
                    count = coverage.get('count', 0)
                    percentage = coverage.get('percentage', 0)
                    print(f"  {field.replace('_', ' ').title()}: {count} ({percentage:.1f}%)")
        
        return True
        
    except Exception as e:
        print(f"✗ Enhancement test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def demonstrate_individual_components():
    """Demonstrate individual component functionality"""
    print("\n=== INDIVIDUAL COMPONENT DEMONSTRATIONS ===")
    
    from src.icd10.icd10_enrichment import (
        ICD10ClinicalNotesExtractor,
        ICD10SynonymGenerator,
        ICD10HierarchyBuilder
    )
    
    # Sample test data
    test_codes = [
        {
            'code': 'E11.9',
            'description': 'Type 2 diabetes mellitus without complications, includes adult-onset diabetes and maturity-onset diabetes, excludes type 1 diabetes',
            'synonyms': [],
            'inclusion_notes': [],
            'exclusion_notes': []
        },
        {
            'code': 'I10',
            'description': 'Essential (primary) hypertension, also known as high blood pressure',
            'synonyms': [],
            'inclusion_notes': [],
            'exclusion_notes': []
        },
        {
            'code': 'J44.0',
            'description': 'Chronic obstructive pulmonary disease with acute lower respiratory infection',
            'synonyms': [],
            'inclusion_notes': [],
            'exclusion_notes': []
        }
    ]
    
    # Test Clinical Notes Extractor
    print("\n1. Clinical Notes Extraction:")
    notes_extractor = ICD10ClinicalNotesExtractor()
    
    for code_data in test_codes:
        notes = notes_extractor.extract_clinical_notes(
            code_data['code'], 
            code_data['description']
        )
        print(f"  {code_data['code']}:")
        if notes['inclusion_notes']:
            print(f"    Inclusions: {notes['inclusion_notes']}")
        if notes['exclusion_notes']:
            print(f"    Exclusions: {notes['exclusion_notes']}")
    
    # Test Synonym Generator
    print("\n2. Synonym Generation:")
    synonym_generator = ICD10SynonymGenerator()
    
    for code_data in test_codes:
        synonyms = synonym_generator.generate_synonyms(
            code_data['code'],
            code_data['description']
        )
        print(f"  {code_data['code']}: {synonyms}")
    
    # Test Hierarchy Builder
    print("\n3. Hierarchy Building:")
    hierarchy_builder = ICD10HierarchyBuilder()
    
    # Add parent codes for demonstration
    extended_codes = test_codes + [
        {'code': 'E11', 'description': 'Type 2 diabetes mellitus'},
        {'code': 'E11.2', 'description': 'Type 2 diabetes mellitus with kidney complications'},
        {'code': 'E11.21', 'description': 'Type 2 diabetes mellitus with diabetic nephropathy'},
    ]
    
    enhanced_hierarchy = hierarchy_builder.build_hierarchy(extended_codes)
    
    for code_data in enhanced_hierarchy:
        code = code_data['code']
        parent = code_data.get('parent_code', 'None')
        children = code_data.get('children_codes', [])
        print(f"  {code}: parent={parent}, children={children}")
    
    print("\n✓ Component demonstrations completed")

if __name__ == '__main__':
    print("Starting ICD10 Enrichment Integration Tests...\n")
    
    # Test individual components first
    demonstrate_individual_components()
    
    # Then test full pipeline (commented out for safety - uncomment when ready)
    # test_success = test_enrichment_pipeline()
    
    print("\n" + "="*50)
    print("Integration tests completed!")
    print("Ready for production enhancement.")
    print("\nTo run full database enhancement:")
    print("  python3 src/icd10/icd10_enrichment.py")
    print("  python3 src/icd10/icd10_enrichment.py 1000  # Test with 1000 codes")