#!/usr/bin/env python3
"""
End-to-end test that replicates Open WebUI usage pattern.

This test calls the actual HTTP API endpoints to catch integration issues
that direct agent testing might miss.
"""

import asyncio
import sys

import httpx

sys.path.insert(0, "/app")  # Container path
sys.path.insert(0, "/home/intelluxe/services/user/healthcare-api")  # Local path


async def test_http_api_endpoints():
    """Test the HTTP API endpoints that Open WebUI would use"""
    print("🌐 Testing HTTP API Endpoints (Open WebUI Pattern)")
    print("=" * 55)

    # Use the container's internal URL
    base_url = "http://healthcare-api:8000"

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test 1: Health check endpoint
        print("\n1️⃣ Testing Health Check...")
        try:
            response = await client.get(f"{base_url}/health")
            print(f"   ✅ Health check: {response.status_code}")
            if response.status_code == 200:
                health_data = response.json()
                print(f"   📊 Status: {health_data.get('status', 'unknown')}")
            else:
                print(f"   ❌ Health check failed: {response.text}")
                return False
        except Exception as e:
            print(f"   ❌ Health check error: {e}")
            return False

        # Test 2: Agent query endpoint (what Open WebUI calls)
        print("\n2️⃣ Testing Agent Query Endpoint...")
        try:
            query_data = {
                "message": "Hello, test medical query",
                "user_id": "test_user",
                "session_id": "test_session",
            }

            response = await client.post(
                f"{base_url}/process", json=query_data, headers={"Content-Type": "application/json"},
            )

            print(f"   📡 Response status: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print("   ✅ Query successful")
                print(f"   📝 Response keys: {list(result.keys())}")

                if "formatted_summary" in result:
                    summary = result["formatted_summary"]
                    print(f"   📄 Summary length: {len(summary)} characters")
                    print(f"   🔍 Preview: {summary[:100]}...")
                else:
                    print("   ⚠️  Missing formatted_summary in response")
                    return False

            else:
                print(f"   ❌ Query failed: {response.status_code}")
                print(f"   📄 Error response: {response.text}")
                return False

        except Exception as e:
            print(f"   ❌ Query endpoint error: {e}")
            return False

        # Test 3: Direct LangChain endpoint (if available)
        print("\n3️⃣ Testing LangChain Endpoint...")
        try:
            langchain_data = {"query": "What are the latest treatments for diabetes?"}

            response = await client.post(
                f"{base_url}/api/v1/langchain/query",
                json=langchain_data,
                headers={"Content-Type": "application/json"},
            )

            print(f"   📡 LangChain response status: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print("   ✅ LangChain query successful")
                print(f"   📝 Response keys: {list(result.keys())}")
            else:
                print(f"   ⚠️  LangChain endpoint: {response.status_code} - {response.text[:200]}")

        except Exception as e:
            print(f"   ⚠️  LangChain endpoint error: {e}")
            # Don't fail the test for this - might not be available

        print("\n🎉 HTTP API testing completed!")
        return True


async def test_in_container():
    """Test from inside the container like our verification script"""
    print("\n🐳 Testing from Inside Container...")
    print("-" * 35)

    try:
        from core.langchain.agents import HealthcareLangChainAgent
        from core.mcp.direct_mcp_client import DirectMCPClient

        # Test the exact same pattern that fails
        mcp_client = DirectMCPClient()
        agent = HealthcareLangChainAgent(mcp_client)

        # Use the same query that might be causing issues
        result = await agent.process("Hello, test medical query")

        print("   ✅ Direct agent call successful")
        print(f"   📊 Result type: {type(result)}")
        print(f"   📝 Result keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")

        if isinstance(result, dict) and result.get("success"):
            print(f"   🎯 Agent success: {result['success']}")
        else:
            print(f"   ❌ Agent failed: {result}")
            return False

        return True

    except Exception as e:
        print(f"   ❌ Container test failed: {e}")
        import traceback

        print(f"   🔍 Stack trace:\n{traceback.format_exc()}")
        return False


def main():
    """Run comprehensive HTTP API tests"""
    print("🔬 Comprehensive Healthcare API Testing")
    print("🎯 Goal: Replicate Open WebUI usage patterns")
    print("=" * 60)

    async def run_tests():
        results = {}

        # Test from container (direct agent)
        print("\n🧪 Phase 1: Direct Agent Testing")
        results["container"] = await test_in_container()

        # Test HTTP API (Open WebUI pattern)
        print("\n🧪 Phase 2: HTTP API Testing")
        results["http_api"] = await test_http_api_endpoints()

        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)

        for test_name, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} {test_name.replace('_', ' ').title()}")

        total_passed = sum(results.values())
        total_tests = len(results)

        print(f"\n🏆 Overall: {total_passed}/{total_tests} test phases passed")

        if total_passed == total_tests:
            print("🎉 All tests passed! API is working correctly.")
        else:
            print("⚠️  Some tests failed. Check output above for details.")
            print("💡 This should help identify why Open WebUI is failing.")

    try:
        asyncio.run(run_tests())
    except KeyboardInterrupt:
        print("\n⚠️  Testing interrupted by user")
    except Exception as e:
        print(f"\n💥 Testing crashed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
