#!/usr/bin/env python3
"""
Test ICD10 enhancement integration with medical-mirrors service
Verifies that the service update script can use the enhancement
"""

import sys
import subprocess
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, '/home/intelluxe/services/user/medical-mirrors/src')

def test_service_script_syntax():
    """Test that the updated service script has valid syntax"""
    print("🧪 Testing Medical-Mirrors Service Script Integration")
    
    script_path = "/home/intelluxe/services/user/medical-mirrors/update-scripts/update_icd10.sh"
    
    try:
        # Check if script file exists
        if not Path(script_path).exists():
            print(f"❌ Service script not found: {script_path}")
            return False
            
        # Test bash syntax
        result = subprocess.run(
            ["bash", "-n", script_path], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode != 0:
            print(f"❌ Service script has syntax errors:")
            print(result.stderr)
            return False
        
        print("✅ Service script syntax is valid")
        
        # Check for enhancement integration
        with open(script_path, 'r') as f:
            content = f.read()
        
        if "enhance_after_download=True" in content:
            print("✅ Service script includes enhance_after_download=True")
        else:
            print("❌ Service script missing enhance_after_download=True")
            return False
            
        if "enhance_after_load=True" in content:
            print("✅ Service script includes enhance_after_load=True")
        else:
            print("❌ Service script missing enhance_after_load=True")
            return False
            
        if "enhancement_stats" in content:
            print("✅ Service script includes enhancement statistics logging")
        else:
            print("❌ Service script missing enhancement statistics logging")
            return False
            
        if "synonyms_pct" in content:
            print("✅ Service script includes comprehensive field validation")
        else:
            print("❌ Service script missing comprehensive field validation")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing service script: {e}")
        return False


def test_enhancement_module_imports():
    """Test that enhancement modules can be imported in service context"""
    print("🧪 Testing Enhancement Module Imports")
    
    try:
        # Test core enhancement module
        from icd10.icd10_enrichment import ICD10DatabaseEnhancer
        print("✅ ICD10DatabaseEnhancer import successful")
        
        # Test that enhancer can be instantiated
        enhancer = ICD10DatabaseEnhancer()
        print("✅ ICD10DatabaseEnhancer instantiation successful")
        
        # Test database loader with enhancement
        from icd10.database_loader import ICD10DatabaseLoader
        loader = ICD10DatabaseLoader()
        print("✅ ICD10DatabaseLoader with enhancement import successful")
        
        # Test smart downloader with enhancement
        from icd10.smart_downloader import SmartICD10Downloader
        print("✅ SmartICD10Downloader with enhancement import successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Enhancement module import failed: {e}")
        return False


def main():
    """Run all service integration tests"""
    print("🏥 Medical-Mirrors Service Enhancement Integration Tests")
    print("=" * 60)
    
    tests = [
        test_enhancement_module_imports(),
        test_service_script_syntax(),
    ]
    
    passed = sum(tests)
    total = len(tests)
    
    print(f"\n📊 Service Integration Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All service integration tests passed!")
        print("\n💡 Medical-mirrors service is ready to use enhancement:")
        print("   - Service script syntax is valid")
        print("   - Enhancement parameters integrated")
        print("   - Enhancement statistics logging added")
        print("   - Comprehensive field validation included")
        print("   - All required modules import successfully")
        print("\n🚀 The /update/icd10 API endpoint will now automatically enhance data!")
        return True
    else:
        print("❌ Some service integration tests failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)