#!/usr/bin/env python3
"""
Test AI-driven ICD10 enhancement using SciSpacy and Ollama
"""

import sys
import os
sys.path.insert(0, '/home/intelluxe/services/user/medical-mirrors/src')

from icd10.scispacy_client import SciSpacyClientSync
from icd10.llm_client import OllamaClientSync, LLMConfig
from icd10.icd10_enrichment import ICD10DatabaseEnhancer


def test_scispacy_connection():
    """Test SciSpacy service connection"""
    print("🧪 Testing SciSpacy service connection...")
    
    client = SciSpacyClientSync()
    if client.client.check_health():
        print("✅ SciSpacy service is healthy")
        
        # Test entity extraction
        test_text = "Type 2 diabetes mellitus with diabetic nephropathy"
        entities = client.extract_medical_entities(test_text)
        
        if entities:
            print(f"✅ Extracted {len(entities)} medical entities")
            for entity in entities[:3]:  # Show first 3
                print(f"   - {entity.text} ({entity.label})")
        else:
            print("⚠️  No entities extracted (service may need configuration)")
            
        return True
    else:
        print("❌ SciSpacy service not available")
        return False


def test_ollama_connection():
    """Test Ollama service connection"""
    print("\n🧪 Testing Ollama service connection...")
    
    client = OllamaClientSync()
    if client.client.check_health():
        print("✅ Ollama service is healthy")
        
        # Test generation
        test_prompt = "List 3 medical synonyms for: hypertension"
        response = client.generate(test_prompt)
        
        if response:
            print(f"✅ Generated response: {response[:100]}...")
        else:
            print("⚠️  No response generated")
            
        return True
    else:
        print("❌ Ollama service not available")
        return False


def test_ai_enhancement():
    """Test AI-driven ICD10 enhancement"""
    print("\n🧪 Testing AI-driven ICD10 enhancement...")
    
    # Create test data
    test_descriptions = [
        "Type 2 diabetes mellitus without complications",
        "Essential (primary) hypertension",
        "Acute bronchitis, unspecified"
    ]
    
    # Test with a small limit
    try:
        print("Creating AI-driven enhancer...")
        enhancer = ICD10DatabaseEnhancer(batch_size=10, use_ai=True)
        
        # Check if AI enhancer was initialized
        if hasattr(enhancer, 'ai_enhancer'):
            print("✅ AI enhancer initialized")
            
            # Test medical concept extraction
            if hasattr(enhancer.ai_enhancer, 'scispacy_client'):
                for desc in test_descriptions[:1]:
                    print(f"\nTesting enhancement for: '{desc}'")
                    
                    # Extract medical concepts
                    concepts = enhancer.ai_enhancer.scispacy_client.extract_medical_concepts(desc)
                    if concepts:
                        print(f"✅ Extracted medical concepts:")
                        for key, values in concepts.items():
                            if values and key != 'all_entities':
                                print(f"   - {key}: {values[:2]}")  # Show first 2
                    
                    # Generate synonyms
                    synonyms = enhancer.ai_enhancer.ollama_client.generate_medical_synonyms(desc)
                    if synonyms:
                        print(f"✅ Generated {len(synonyms)} synonyms:")
                        for syn in synonyms[:3]:  # Show first 3
                            print(f"   - {syn}")
                    
                    # Generate inclusion notes
                    inclusion = enhancer.ai_enhancer.ollama_client.generate_inclusion_notes(desc, concepts)
                    if inclusion:
                        print(f"✅ Generated {len(inclusion)} inclusion notes:")
                        for note in inclusion[:2]:  # Show first 2
                            print(f"   - {note}")
                    
                    # Generate exclusion notes
                    exclusion = enhancer.ai_enhancer.ollama_client.generate_exclusion_notes(desc, concepts)
                    if exclusion:
                        print(f"✅ Generated {len(exclusion)} exclusion notes:")
                        for note in exclusion[:2]:  # Show first 2
                            print(f"   - {note}")
            
            return True
        else:
            print("❌ AI enhancer not initialized (check service availability)")
            return False
            
    except Exception as e:
        print(f"❌ AI enhancement test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mode_switching():
    """Test switching between pattern-based and AI-driven modes"""
    print("\n🧪 Testing mode switching...")
    
    # Test pattern-based mode
    enhancer_pattern = ICD10DatabaseEnhancer(use_ai=False)
    if hasattr(enhancer_pattern, 'notes_extractor'):
        print("✅ Pattern-based mode initialized correctly")
    else:
        print("❌ Pattern-based mode failed to initialize")
        return False
    
    # Test AI-driven mode
    enhancer_ai = ICD10DatabaseEnhancer(use_ai=True)
    if hasattr(enhancer_ai, 'ai_enhancer'):
        print("✅ AI-driven mode initialized correctly")
    else:
        print("❌ AI-driven mode failed to initialize")
        return False
    
    return True


def main():
    """Run all AI enhancement tests"""
    print("🏥 ICD10 AI Enhancement Test Suite")
    print("=" * 50)
    
    tests = []
    
    # Test connections
    scispacy_ok = test_scispacy_connection()
    ollama_ok = test_ollama_connection()
    
    tests.append(scispacy_ok)
    tests.append(ollama_ok)
    
    # Only test enhancement if services are available
    if scispacy_ok and ollama_ok:
        tests.append(test_ai_enhancement())
        tests.append(test_mode_switching())
    else:
        print("\n⚠️  Skipping enhancement tests - AI services not available")
        print("   Make sure SciSpacy (port 8080) and Ollama (port 11434) are running")
    
    # Summary
    passed = sum(tests)
    total = len(tests)
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        print("\n💡 AI-driven enhancement is ready to use:")
        print("   - Run with: USE_AI=true python3 icd10_enrichment.py")
        print("   - Or use: python3 icd10_enrichment.py --ai")
        print("   - Integrates with existing pipeline automatically")
    else:
        print("❌ Some tests failed")
        print("\n💡 To use AI enhancement, ensure:")
        print("   - SciSpacy service is running at port 8080")
        print("   - Ollama service is running at port 11434")
        print("   - Services are accessible from medical-mirrors container")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)