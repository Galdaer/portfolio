#!/usr/bin/env python3
"""
Test suite for HealthcareLangChainAgent

This test file provides comprehensive testing for the LangChain-powered
healthcare agent with MCP tool integration.

Tests include:
- Agent initialization and configuration
- MCP client connectivity
- Ollama LLM connectivity
- End-to-end query processing
- Error handling and edge cases
"""

import asyncio
import pytest
from unittest.mock import Mock, patch
import os
import sys

# Add the healthcare-api directory to Python path for imports
sys.path.insert(0, "/app")  # For container testing
sys.path.insert(0, "/home/intelluxe/services/user/healthcare-api")  # For local testing

from core.langchain.agents import HealthcareLangChainAgent
from core.mcp.direct_mcp_client import DirectMCPClient


class TestHealthcareLangChainAgent:
    """Test suite for HealthcareLangChainAgent"""

    def setup_method(self):
        """Setup for each test method"""
        self.mcp_client = None
        self.agent = None

    def teardown_method(self):
        """Cleanup after each test method"""
        if self.mcp_client:
            # Clean up any connections
            pass

    async def test_mcp_client_connectivity(self):
        """Test that MCP client can connect and get available tools"""
        print("\n=== Testing MCP Client Connectivity ===")

        try:
            self.mcp_client = DirectMCPClient()
            tools = await self.mcp_client.get_available_tools()

            print(f"✅ MCP client connected successfully")
            print(f"✅ Found {len(tools)} available tools")

            # Print first few tools for verification
            for i, tool in enumerate(tools[:3]):
                print(f"   {i + 1}. {tool.get('name', 'Unknown')}")

            assert len(tools) > 0, "Should have at least some MCP tools available"
            assert any("patient" in str(tool).lower() for tool in tools), (
                "Should have patient-related tools"
            )

            return True

        except Exception as e:
            print(f"❌ MCP client connectivity failed: {e}")
            return False

    async def test_agent_initialization(self):
        """Test agent initialization with MCP client"""
        print("\n=== Testing Agent Initialization ===")

        try:
            # First ensure MCP client works
            mcp_success = await self.test_mcp_client_connectivity()
            if not mcp_success:
                pytest.skip("MCP client not available - skipping agent tests")

            # Initialize agent
            self.agent = HealthcareLangChainAgent(self.mcp_client)

            print("✅ Agent initialized successfully")

            # Test agent has required attributes
            assert hasattr(self.agent, "mcp_client"), "Agent should have mcp_client attribute"
            assert hasattr(self.agent, "process"), "Agent should have process method"

            return True

        except Exception as e:
            print(f"❌ Agent initialization failed: {e}")
            return False

    async def test_ollama_connectivity(self):
        """Test Ollama LLM connectivity"""
        print("\n=== Testing Ollama Connectivity ===")

        try:
            # Check if Ollama environment variables are set
            ollama_url = os.getenv("OLLAMA_URL") or os.getenv(
                "OLLAMA_BASE_URL", "http://172.20.0.10:11434"
            )
            print(f"Using Ollama URL: {ollama_url}")

            # Initialize agent if not already done
            if not self.agent:
                agent_success = await self.test_agent_initialization()
                if not agent_success:
                    pytest.skip("Agent initialization failed - skipping Ollama test")

            # Try a simple query to test Ollama connectivity
            # This will also test the full stack: Agent -> Ollama -> MCP tools
            response = await self.agent.process(
                "Hello, can you tell me about medical search capabilities?"
            )

            print("✅ Ollama connectivity successful")
            print(
                f"✅ Received response: {response[:100]}..."
                if len(response) > 100
                else f"✅ Received response: {response}"
            )

            assert isinstance(response, str), "Response should be a string"
            assert len(response) > 0, "Response should not be empty"

            return True

        except Exception as e:
            print(f"❌ Ollama connectivity failed: {e}")
            print(f"   Error type: {type(e).__name__}")

            # Provide helpful debugging info
            if "connection" in str(e).lower():
                print("   💡 This appears to be a connection issue")
                print(f"   💡 Check that Ollama is running at: {ollama_url}")

            return False

    async def test_medical_query_processing(self):
        """Test processing of a medical query end-to-end"""
        print("\n=== Testing Medical Query Processing ===")

        try:
            # Ensure agent is initialized
            if not self.agent:
                agent_success = await self.test_agent_initialization()
                if not agent_success:
                    pytest.skip("Agent initialization failed - skipping medical query test")

            # Test a medical query that should use MCP tools
            medical_query = "Can you help me find information about diabetes management?"

            print(f"Processing query: {medical_query}")
            response = await self.agent.process(medical_query)

            print("✅ Medical query processed successfully")
            print(f"✅ Response length: {len(response)} characters")

            # Basic response validation
            assert isinstance(response, str), "Response should be a string"
            assert len(response) > 50, "Medical response should be substantial"

            # Check for medical-related content (basic validation)
            medical_keywords = ["diabetes", "medical", "health", "patient", "treatment"]
            response_lower = response.lower()
            found_keywords = [kw for kw in medical_keywords if kw in response_lower]

            print(f"✅ Found medical keywords: {found_keywords}")
            assert len(found_keywords) > 0, "Response should contain medical-related keywords"

            return True

        except Exception as e:
            print(f"❌ Medical query processing failed: {e}")
            return False

    async def test_error_handling(self):
        """Test agent error handling with invalid inputs"""
        print("\n=== Testing Error Handling ===")

        try:
            # Ensure agent is initialized
            if not self.agent:
                agent_success = await self.test_agent_initialization()
                if not agent_success:
                    pytest.skip("Agent initialization failed - skipping error handling test")

            # Test empty query
            try:
                response = await self.agent.process("")
                print("✅ Empty query handled gracefully")
            except Exception as e:
                print(f"⚠️  Empty query handling: {e}")

            # Test None query
            try:
                response = await self.agent.process(None)
                print("✅ None query handled gracefully")
            except Exception as e:
                print(f"⚠️  None query handling: {e}")

            # Test very long query
            try:
                long_query = "What is diabetes? " * 1000  # Very long query
                response = await self.agent.process(long_query)
                print("✅ Long query handled gracefully")
            except Exception as e:
                print(f"⚠️  Long query handling: {e}")

            return True

        except Exception as e:
            print(f"❌ Error handling test failed: {e}")
            return False


async def run_all_tests():
    """Run all tests in sequence"""
    print("🏥 Healthcare LangChain Agent Test Suite")
    print("=" * 50)

    test_instance = TestHealthcareLangChainAgent()
    test_instance.setup_method()

    try:
        # Run tests in logical order
        tests = [
            ("MCP Client Connectivity", test_instance.test_mcp_client_connectivity),
            ("Agent Initialization", test_instance.test_agent_initialization),
            ("Ollama Connectivity", test_instance.test_ollama_connectivity),
            ("Medical Query Processing", test_instance.test_medical_query_processing),
            ("Error Handling", test_instance.test_error_handling),
        ]

        results = {}

        for test_name, test_func in tests:
            print(f"\n🔬 Running: {test_name}")
            try:
                result = await test_func()
                results[test_name] = "PASS" if result else "FAIL"
            except Exception as e:
                print(f"❌ Test '{test_name}' crashed: {e}")
                results[test_name] = "CRASH"

        # Print summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)

        for test_name, result in results.items():
            status_emoji = "✅" if result == "PASS" else "❌" if result == "FAIL" else "💥"
            print(f"{status_emoji} {test_name}: {result}")

        # Overall result
        passed = sum(1 for r in results.values() if r == "PASS")
        total = len(results)

        print(f"\n🏆 Overall: {passed}/{total} tests passed")

        if passed == total:
            print("🎉 All tests passed! Agent is working correctly.")
        else:
            print("⚠️  Some tests failed. Check the output above for details.")

    finally:
        test_instance.teardown_method()


def run_quick_test():
    """Quick test function for rapid debugging"""
    print("🚀 Quick LangChain Agent Test")
    print("-" * 30)

    async def quick_test():
        try:
            # Quick MCP connectivity check
            mcp_client = DirectMCPClient()
            tools = await mcp_client.get_available_tools()
            print(f"✅ MCP: {len(tools)} tools available")

            # Quick agent initialization
            agent = HealthcareLangChainAgent(mcp_client)
            print("✅ Agent: Initialized successfully")

            # Quick query test
            response = await agent.process("Hello")
            print(f"✅ Query: Got response ({len(response)} chars)")

            print("🎉 Quick test passed!")

        except Exception as e:
            print(f"❌ Quick test failed: {e}")

    asyncio.run(quick_test())


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Healthcare LangChain Agent Tests")
    parser.add_argument("--quick", action="store_true", help="Run quick test only")
    parser.add_argument("--test", help="Run specific test method")

    args = parser.parse_args()

    if args.quick:
        run_quick_test()
    elif args.test:
        # Run specific test
        test_instance = TestHealthcareLangChainAgent()
        test_instance.setup_method()

        if hasattr(test_instance, args.test):
            asyncio.run(getattr(test_instance, args.test)())
        else:
            print(f"❌ Test method '{args.test}' not found")
    else:
        # Run all tests
        asyncio.run(run_all_tests())
