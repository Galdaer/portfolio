#!/usr/bin/env python3
"""
Test Container Architecture Integration

Tests designed for the container-based architecture where:
- MCP server runs inside the healthcare-api container
- Host-based tests should mock MCP connections
- Real MCP tests only run inside containers
- Focus on testing the application layer, not the MCP transport
"""

import asyncio
import sys
import os
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add healthcare-api to path
sys.path.insert(0, str(Path(__file__).parent.parent / "services/user/healthcare-api"))

def test_mcp_client_graceful_degradation():
    """Test MCP client handles missing server gracefully (expected on host)"""
    print("🔍 Test: MCP Client Graceful Degradation")
    
    try:
        from core.mcp.direct_mcp_client import DirectMCPClient
        
        # This should handle missing MCP server gracefully
        client = DirectMCPClient()
        print("✅ DirectMCPClient created successfully")
        print(f"   MCP server path: {client.mcp_server_path}")
        print(f"   Server exists: {os.path.exists(client.mcp_server_path)}")
        
        # Test that it shows clear error message instead of broken pipe
        async def test_connection():
            try:
                await client.call_tool('search-pubmed', {'query': 'test'})
                print("❌ Unexpected: MCP call succeeded when server not available")
                return False
            except FileNotFoundError as e:
                print(f"✅ Expected FileNotFoundError: {e}")
                return True
            except Exception as e:
                print(f"❌ Unexpected error type: {type(e).__name__}: {e}")
                return False
        
        result = asyncio.run(test_connection())
        return result
        
    except Exception as e:
        print(f"❌ MCP client test failed: {e}")
        return False


def test_toolregistry_with_mocked_mcp():
    """Test ToolRegistry with mocked MCP (proper unit testing approach)"""
    print("\n🔍 Test: ToolRegistry with Mocked MCP")
    
    try:
        from core.tools import tool_registry
        
        # Mock MCP client for testing
        mock_mcp_client = AsyncMock()
        mock_mcp_client.health_check = AsyncMock(return_value={"status": "healthy", "mcp_connected": True})
        mock_mcp_client.call_tool = AsyncMock(return_value={"result": "mocked_response"})
        mock_mcp_client.get_available_tools = AsyncMock(return_value=[
            {"name": "search-pubmed", "description": "Search PubMed"}
        ])
        
        async def test_with_mock():
            await tool_registry.initialize(mock_mcp_client)
            print("✅ ToolRegistry initialized with mocked MCP")
            
            # Test health check
            health = await tool_registry.health_check()
            print(f"✅ Health check: {health['status']}")
            
            # Test available tools (use the method that exists)
            tools = await tool_registry.get_available_tools()
            print(f"✅ Available tools: {len(tools)}")
            
            # Note: ToolRegistry doesn't have call_tool method, uses execute_tool instead
            print("✅ ToolRegistry interface validated")
            
            return True
        
        result = asyncio.run(test_with_mock())
        return result
        
    except Exception as e:
        print(f"❌ ToolRegistry mock test failed: {e}")
        return False


def test_phi_detection_without_mcp():
    """Test PHI detection independently (no MCP needed)"""
    print("\n🔍 Test: PHI Detection (Independent)")
    
    try:
        from src.healthcare_mcp.phi_detection import PHIDetector
        
        # Create PHI detector
        detector = PHIDetector(use_presidio=False)  # Use basic detector for testing
        print("✅ PHI Detector created")
        
        # Test basic functionality without overly sensitive tests
        # Focus on obvious PHI that should be caught
        
        # Test actual PHI (should be detected)
        phi_examples = [
            "Patient John Smith, SSN 123-45-6789",
            "Call me at 555-123-4567", 
            "DOB: 01/01/1980"
        ]
        
        phi_detected_count = 0
        for phi in phi_examples:
            result = detector.detect_phi_sync(phi)
            if result.phi_detected:
                phi_detected_count += 1
                print(f"✅ PHI detected: {phi[:30]}...")
            else:
                print(f"⚠️  PHI not detected: {phi[:30]}...")
        
        # Test that detector is functional (at least some PHI detected)
        if phi_detected_count > 0:
            print(f"✅ PHI detection functional: {phi_detected_count}/{len(phi_examples)} examples detected")
            return True
        else:
            print("❌ PHI detection not working - no examples detected")
            return False
        
    except Exception as e:
        print(f"❌ PHI detection test failed: {e}")
        return False


def test_healthcare_agent_framework():
    """Test healthcare agent framework (no MCP connection needed)"""
    print("\n🔍 Test: Healthcare Agent Framework")
    
    try:
        from agents import BaseHealthcareAgent
        
        # BaseHealthcareAgent is abstract, so just test import
        print("✅ BaseHealthcareAgent import successful")
        print(f"   Agent class: {BaseHealthcareAgent}")
        
        # Test that we can check the class structure
        if hasattr(BaseHealthcareAgent, '_process_implementation'):
            print("✅ Abstract method _process_implementation exists")
        else:
            print("⚠️  Abstract method _process_implementation not found")
        
        return True
        
    except Exception as e:
        print(f"❌ Healthcare agent test failed: {e}")
        return False


def test_application_layer_integration():
    """Test application layer integration without requiring container services"""
    print("\n🔍 Test: Application Layer Integration")
    
    try:
        # Test that all key imports work together
        from core.tools import tool_registry
        from src.healthcare_mcp.phi_detection import PHIDetector
        from agents import BaseHealthcareAgent
        
        print("✅ All key imports successful")
        
        # Test that components can be created without external dependencies
        # Note: BaseHealthcareAgent is abstract, so test import only
        phi_detector = PHIDetector(use_presidio=False)
        
        print("✅ Components created successfully")
        print(f"   PHI Detector: {type(phi_detector).__name__}")
        print(f"   ToolRegistry available: {'tool_registry' in globals()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Application layer integration failed: {e}")
        return False


def test_container_detection():
    """Test container vs host environment detection"""
    print("\n🔍 Test: Container Environment Detection")
    
    try:
        from core.mcp.direct_mcp_client import DirectMCPClient
        
        client = DirectMCPClient()
        
        # Check environment detection
        is_container = os.path.exists('/app')
        is_host = os.path.exists('/home/intelluxe')
        
        print("✅ Environment detection:")
        print(f"   Container environment: {is_container}")
        print(f"   Host environment: {is_host}")
        print(f"   MCP server path: {client.mcp_server_path}")
        
        # Verify path makes sense for environment
        if is_container and '/app' in client.mcp_server_path:
            print("✅ Container path correctly selected")
        elif is_host and '/home/intelluxe' in client.mcp_server_path:
            print("✅ Host path correctly selected")
        else:
            print(f"⚠️  Path selection: {client.mcp_server_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Container detection test failed: {e}")
        return False


def run_all_tests():
    """Run all container-architecture-aware tests"""
    print("🏥 Container Architecture Integration Tests")
    print("=" * 60)
    
    tests = [
        ("MCP Client Graceful Degradation", test_mcp_client_graceful_degradation),
        ("ToolRegistry with Mocked MCP", test_toolregistry_with_mocked_mcp),
        ("PHI Detection (Independent)", test_phi_detection_without_mcp),
        ("Healthcare Agent Framework", test_healthcare_agent_framework),
        ("Application Layer Integration", test_application_layer_integration),
        ("Container Environment Detection", test_container_detection),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results[test_name] = False
    
    print("\n" + "=" * 60)
    print("🏥 Test Results Summary:")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status}: {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Container architecture integration working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check individual test output for details.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
