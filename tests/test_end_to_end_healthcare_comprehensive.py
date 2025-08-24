#!/usr/bin/env python3
"""
End-to-End Healthcare System Test

This test validates the complete workflow:
HTTP request → LangChain agent → Ollama LLM → MCP tools → Response

Usage:
    python3 test_end_to_end_healthcare.py                    # Run locally
    python3 test_end_to_end_healthcare.py --container        # Run in container
    python3 test_end_to_end_healthcare.py --quick            # Quick test only
"""

import argparse
import asyncio
import subprocess
import sys

# Add healthcare-api to path for local testing
sys.path.insert(0, "/app")  # Container path
sys.path.insert(0, "/home/intelluxe/services/user/healthcare-api")  # Local path


async def test_ollama_connectivity():
    """Test 1: Ollama connectivity"""
    print("1️⃣ Testing Ollama connectivity...")

    try:
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get("http://172.20.0.10:11434/api/version", timeout=10.0)
            if response.status_code == 200:
                version_data = response.json()
                print(f"   ✅ Ollama running: {version_data.get('version', 'unknown')}")
                return True
            print(f"   ❌ Ollama responded with status {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Ollama connection failed: {e}")
        return False


async def test_mcp_tools():
    """Test 2: MCP tools functionality"""
    print("2️⃣ Testing MCP tools...")

    try:
        from core.mcp.direct_mcp_client import DirectMCPClient

        mcp_client = DirectMCPClient()

        # Test getting available tools
        tools = await mcp_client.get_available_tools()
        print(f"   ✅ MCP tools available: {len(tools)}")

        # Test a simple tool call
        result = await mcp_client.call_tool("search-pubmed", {"query": "diabetes"})
        if result and "content" in result:
            print("   ✅ PubMed search tool working")
            return True
        print(f"   ❌ PubMed tool returned unexpected result: {result}")
        return False

    except Exception as e:
        print(f"   ❌ MCP tools failed: {e}")
        return False


async def test_langchain_initialization():
    """Test 3: LangChain agent initialization"""
    print("3️⃣ Testing LangChain agent initialization...")

    try:
        from core.langchain.agents import HealthcareLangChainAgent
        from core.mcp.direct_mcp_client import DirectMCPClient

        mcp_client = DirectMCPClient()
        agent = HealthcareLangChainAgent(mcp_client=mcp_client, verbose=True, model="llama3.1:8b")

        print("   ✅ LangChain agent initialized successfully")
        return agent

    except Exception as e:
        print(f"   ❌ LangChain agent initialization failed: {e}")
        import traceback

        traceback.print_exc()
        return None


async def test_simple_llm_query(agent):
    """Test 4: Simple LLM query (no tools)"""
    print("4️⃣ Testing simple LLM query...")

    try:
        # Test just the LLM without tool usage
        from langchain_ollama import ChatOllama

        llm = ChatOllama(model="llama3.1:8b", base_url="http://172.20.0.10:11434", temperature=0.1)

        response = await llm.ainvoke("What is diabetes? Give a brief answer.")

        if response and hasattr(response, "content") and response.content:
            print(f"   ✅ LLM query successful: {len(response.content)} chars")
            return True
        print(f"   ❌ LLM returned unexpected response: {type(response)}")
        return False

    except Exception as e:
        print(f"   ❌ LLM query failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_full_agent_workflow(agent):
    """Test 5: Full agent workflow with tools"""
    print("5️⃣ Testing full agent workflow...")

    try:
        # Simple query that should trigger tool usage
        query = "What are the symptoms of diabetes?"
        print(f"   🔍 Query: {query}")

        result = await agent.process(query)

        if isinstance(result, dict):
            success = result.get("success", False)
            if success:
                response = result.get("formatted_summary", result.get("response", ""))
                steps = result.get("intermediate_steps", [])
                print("   ✅ Agent workflow successful!")
                print(f"   📄 Response length: {len(response)} chars")
                print(f"   🔧 Tool calls: {len(steps)}")
                return True
            error = result.get("error", "Unknown error")
            error_type = result.get("error_type", "Unknown")
            print(f"   ❌ Agent workflow failed: {error}")
            print(f"   🔧 Error type: {error_type}")
            return False
        print(f"   ❌ Agent returned unexpected result type: {type(result)}")
        return False

    except Exception as e:
        print(f"   ❌ Agent workflow crashed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def run_local_tests(quick_mode=False):
    """Run all tests locally"""
    print("🏥 Healthcare End-to-End Test Suite (Local)")
    print("=" * 50)

    results = []

    # Test 1: Ollama
    results.append(await test_ollama_connectivity())

    # Test 2: MCP Tools
    results.append(await test_mcp_tools())

    if quick_mode:
        print("\n🚀 Quick mode: Skipping full agent tests")
        return all(results)

    # Test 3: Agent Init
    agent = await test_langchain_initialization()
    results.append(agent is not None)

    if agent is None:
        print("\n❌ Cannot continue without agent")
        return False

    # Test 4: Simple LLM
    results.append(await test_simple_llm_query(agent))

    # Test 5: Full Workflow
    results.append(await test_full_agent_workflow(agent))

    # Summary
    passed = sum(results)
    total = len(results)

    print(f"\n📊 Test Results: {passed}/{total} passed")

    if all(results):
        print("🎉 ALL TESTS PASSED! Healthcare system is fully operational.")
        return True
    print("❌ Some tests failed. Healthcare system needs attention.")
    return False


def run_container_tests():
    """Run tests inside the healthcare container"""
    print("🐳 Healthcare End-to-End Test Suite (Container)")
    print("=" * 50)

    try:
        # Build the container test command
        test_script = """
cd /app
python3 -c "
import asyncio
import sys
sys.path.insert(0, '/app')

async def main():
    # Import test functions from this file
    exec(open('/home/intelluxe/test_end_to_end_healthcare.py').read())
    success = await run_local_tests()
    sys.exit(0 if success else 1)

asyncio.run(main())
"
"""

        cmd = [
            "docker",
            "run",
            "--rm",
            "--network",
            "host",
            "-v",
            "/home/intelluxe/test_end_to_end_healthcare.py:/home/intelluxe/test_end_to_end_healthcare.py:ro",
            "intelluxe/healthcare-api:latest",
            "bash",
            "-c",
            test_script,
        ]

        print("🔄 Running tests in container...")
        result = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=120)

        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        if result.returncode == 0:
            print("✅ Container tests passed!")
            return True
        print(f"❌ Container tests failed (exit code: {result.returncode})")
        return False

    except subprocess.TimeoutExpired:
        print("❌ Container tests timed out")
        return False
    except Exception as e:
        print(f"❌ Container test execution failed: {e}")
        return False


def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description="Healthcare End-to-End Test Suite")
    parser.add_argument("--container", action="store_true", help="Run tests in container")
    parser.add_argument("--quick", action="store_true", help="Run quick tests only")

    args = parser.parse_args()

    if args.container:
        success = run_container_tests()
    else:
        success = asyncio.run(run_local_tests(quick_mode=args.quick))

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
