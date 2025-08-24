#!/usr/bin/env python3
"""
Container Healthcare Integration Test

Tests the actual production architecture:
- Healthcare-API container with MCP server inside
- Container connects to host Ollama
- Full end-to-end workflow testing

This is the ONLY architecture that matters for production.
"""

import subprocess
import sys


class ContainerHealthcareTest:
    """Test healthcare system in production container architecture."""

    def __init__(self):
        self.container_name = "healthcare-api-test"
        self.image_name = "intelluxe/healthcare-api:latest"

    def ensure_container_built(self) -> bool:
        """Ensure the healthcare-api container is built."""
        print("🏗️ Ensuring healthcare-api container is built...")

        try:
            result = subprocess.run(
                ["make", "healthcare-api-build"],
                check=False, cwd="/home/intelluxe",
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                print("✅ Container built successfully")
                return True
            print(f"❌ Container build failed: {result.stderr}")
            return False

        except Exception as e:
            print(f"❌ Container build error: {e}")
            return False

    def test_ollama_connectivity_from_container(self) -> bool:
        """Test if container can reach host Ollama."""
        print("🔗 Testing Ollama connectivity from container...")

        try:
            # Use host networking to access localhost Ollama
            result = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--network",
                    "host",
                    self.image_name,
                    "curl",
                    "-s",
                    "http://172.20.0.10:11434/api/version",
                ],
                check=False, capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                print("✅ Container can reach Ollama")
                return True
            print(f"❌ Container cannot reach Ollama: {result.stderr}")
            return False

        except Exception as e:
            print(f"❌ Ollama connectivity test error: {e}")
            return False

    def test_mcp_server_in_container(self) -> bool:
        """Test that MCP server exists and works in container."""
        print("🔧 Testing MCP server in container...")

        try:
            cmd = [
                "docker",
                "run",
                "--rm",
                "-i",
                self.image_name,
                "node",
                "/app/mcp-server/build/stdio_entry.js",
            ]
            input_data = '{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}\n'
            result = subprocess.run(
                cmd, check=False, input=input_data, capture_output=True, text=True, timeout=30,
            )

            # Combine stdout and stderr since MCP server logs to stderr
            output = result.stdout + result.stderr
            if result.returncode == 0 and '"result"' in output and "tools" in output:
                print("✅ MCP server responds correctly")
                return True
            print(f"❌ MCP server error (exit code {result.returncode})")
            print(f"❌ Combined output: {output[:500]}...")
            return False

        except Exception as e:
            print(f"❌ MCP server test error: {e}")
            return False

    def test_langchain_agent_in_container(self) -> bool:
        """Test LangChain agent with full workflow in container."""
        print("🤖 Testing LangChain agent in container...")

        test_script = """
import asyncio
import sys
import os
import signal

# Set timeout
def timeout_handler(signum, frame):
    print("TIMEOUT: Agent test took too long")
    sys.exit(1)

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(45)  # 45 second timeout

async def test_agent():
    try:
        from core.langchain.agents import HealthcareLangChainAgent
        from core.mcp.direct_mcp_client import DirectMCPClient

        print("📋 Initializing MCP client...")
        mcp_client = DirectMCPClient()

        print("🤖 Initializing LangChain agent...")
        agent = HealthcareLangChainAgent(
            mcp_client=mcp_client,
            verbose=True,
            model="llama3.1:8b"
        )

        print("💬 Testing simple medical query...")
        result = await agent.process("What are common symptoms of type 2 diabetes?")

        if result.get("success"):
            print("✅ Agent processing successful!")
            print(f"📄 Response preview: {result.get('formatted_summary', '')[:200]}...")
            return True
        else:
            print(f"❌ Agent processing failed: {result.get('error', 'Unknown error')}")
            print(f"🔧 Error type: {result.get('error_type', 'Unknown')}")
            return False

    except Exception as e:
        print(f"❌ Agent test error: {e}")
        import traceback
        traceback.print_exc()
        return False

# Run the test
success = asyncio.run(test_agent())
sys.exit(0 if success else 1)
"""

        try:
            result = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--network",
                    "host",
                    self.image_name,
                    "python3",
                    "-c",
                    test_script,
                ],
                check=False, capture_output=True,
                text=True,
                timeout=60,
            )

            print(f"📋 Agent test output:\n{result.stdout}")
            if result.stderr:
                print(f"🚨 Agent test errors:\n{result.stderr}")

            if result.returncode == 0:
                print("✅ LangChain agent test successful!")
                return True
            print(f"❌ LangChain agent test failed (exit code: {result.returncode})")
            return False

        except subprocess.TimeoutExpired:
            print("❌ LangChain agent test timed out")
            return False
        except Exception as e:
            print(f"❌ LangChain agent test error: {e}")
            return False

    def run_full_test_suite(self) -> bool:
        """Run the complete container test suite."""
        print("🏥 Container Healthcare Integration Test Suite")
        print("=" * 50)

        tests = [
            ("Container Build", self.ensure_container_built),
            ("Ollama Connectivity", self.test_ollama_connectivity_from_container),
            ("MCP Server", self.test_mcp_server_in_container),
            ("LangChain Agent", self.test_langchain_agent_in_container),
        ]

        passed = 0
        for test_name, test_func in tests:
            print(f"\n🧪 Running: {test_name}")
            if test_func():
                passed += 1
            else:
                print(f"💥 FAILED: {test_name}")
                break  # Stop on first failure for faster feedback

        print(f"\n📊 Results: {passed}/{len(tests)} tests passed")

        if passed == len(tests):
            print("🎉 ALL TESTS PASSED! Healthcare system is ready for production!")
            return True
        print("❌ Some tests failed. System needs fixes before production.")
        return False


def main():
    """Run container healthcare integration tests."""
    if "--quick" in sys.argv:
        # Quick test: just check container build and MCP server
        test = ContainerHealthcareTest()
        print("🚀 Quick Container Test")
        success = test.ensure_container_built() and test.test_mcp_server_in_container()
    else:
        # Full test suite
        test = ContainerHealthcareTest()
        success = test.run_full_test_suite()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
