#!/usr/bin/env python3
"""
Test Open WebUI Medical Query Routing

This test specifically addresses the Primary Issue from the handoff:
Open WebUI healthcare queries not reaching the medical search agent

Expected behavior:
- Medical queries through Open WebUI should trigger agent_medical_search.log entries
- Healthcare agent should be selected for medical queries
- MCP tools should be invoked for medical literature search
"""

import asyncio
import logging
import sys
from pathlib import Path

import aiohttp

# Add healthcare-api to path
sys.path.insert(0, str(Path("/home/intelluxe/services/user/healthcare-api")))

try:
    from core.infrastructure.healthcare_logger import get_healthcare_logger
except ImportError:
    # Fallback if healthcare logger not available
    def get_healthcare_logger(name):
        return logging.getLogger(name)


logger = get_healthcare_logger("test.open_webui_routing")


class OpenWebUIMedicalRoutingTest:
    """Test suite for Open WebUI medical query routing diagnosis."""

    def __init__(self):
        self.healthcare_api_url = "http://localhost:8000"
        self.log_files = {
            "healthcare_system": Path("/home/intelluxe/logs/healthcare_system.log"),
            "agent_medical_search": Path("/home/intelluxe/logs/agent_medical_search.log"),
        }

    async def test_healthcare_api_health(self) -> bool:
        """Test healthcare API is accessible and agents are registered."""
        logger.info("Testing healthcare API health and agent registration")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.healthcare_api_url}/health") as response:
                    if response.status == 200:
                        health_data = await response.json()
                        agents = health_data.get("agents", [])

                        logger.info(f"✅ Healthcare API healthy with {len(agents)} agents")
                        logger.info(f"Registered agents: {agents}")

                        if "medical_search" in agents:
                            logger.info("✅ Medical search agent is registered")
                            return True
                        logger.error("❌ Medical search agent NOT registered")
                        return False
                    logger.error(f"❌ Healthcare API unhealthy: {response.status}")
                    return False
        except Exception as e:
            logger.exception(f"❌ Healthcare API connection error: {e}")
            return False

    def get_log_baseline(self) -> dict[str, int]:
        """Get current line count of relevant log files."""
        baseline = {}
        for name, log_path in self.log_files.items():
            if log_path.exists():
                with open(log_path) as f:
                    baseline[name] = len(f.readlines())
            else:
                baseline[name] = 0
                logger.warning(f"Log file {log_path} does not exist")

        logger.info(f"Log baseline: {baseline}")
        return baseline

    def check_log_activity(
        self, baseline: dict[str, int], expected_logs: list[str],
    ) -> dict[str, bool]:
        """Check if new entries appeared in logs after baseline."""
        results = {}

        for name, log_path in self.log_files.items():
            if not log_path.exists():
                results[name] = False
                continue

            with open(log_path) as f:
                current_lines = f.readlines()

            new_lines = current_lines[baseline[name] :]
            new_content = "".join(new_lines)

            # Check for expected activity
            has_activity = any(keyword in new_content.lower() for keyword in expected_logs)
            results[name] = has_activity

            if new_lines:
                logger.info(f"📋 New entries in {name}: {len(new_lines)} lines")
                logger.info(f"Sample: {new_content[:200]}...")
            else:
                logger.info(f"📋 No new entries in {name}")

        return results

    async def test_direct_medical_query_api(self) -> bool:
        """Test direct medical query to healthcare API (bypass Open WebUI)."""
        logger.info("Testing direct medical query to healthcare API")

        # Get baseline
        baseline = self.get_log_baseline()

        # Medical query payload
        medical_query = {
            "model": "healthcare",
            "messages": [
                {"role": "user", "content": "What are the symptoms of diabetes mellitus type 2?"},
            ],
            "stream": False,
        }

        try:
            async with aiohttp.ClientSession() as session, session.post(
                f"{self.healthcare_api_url}/v1/chat/completions",
                json=medical_query,
                headers={"Content-Type": "application/json"},
            ) as response:
                if response.status == 200:
                    response_data = await response.json()
                    logger.info("✅ Direct medical query successful")
                    logger.info(f"Response preview: {str(response_data)[:200]}...")

                    # Wait for logs to flush
                    await asyncio.sleep(2)

                    # Check log activity
                    log_activity = self.check_log_activity(
                        baseline, ["medical", "search", "agent", "diabetes", "pubmed"],
                    )

                    if log_activity.get("agent_medical_search", False):
                        logger.info("✅ Medical search agent was activated")
                        return True
                    logger.error("❌ Medical search agent was NOT activated")
                    logger.error(f"Log activity: {log_activity}")
                    return False
                logger.error(f"❌ Direct query failed: {response.status}")
                error_text = await response.text()
                logger.error(f"Error details: {error_text}")
                return False

        except Exception as e:
            logger.exception(f"❌ Direct medical query error: {e}")
            return False

    async def test_medical_agent_import(self) -> bool:
        """Test that medical search agent can be imported and initialized."""
        logger.info("Testing medical search agent import and initialization")

        try:
            from agents.medical_search_agent import MedicalLiteratureSearchAssistant
            from core.config.models import get_primary_model
            from core.mcp.direct_mcp_client import DirectMCPClient

            # Initialize components
            mcp_client = DirectMCPClient()
            llm_client = get_primary_model()  # Should return Ollama client

            # Initialize agent
            agent = MedicalLiteratureSearchAssistant(mcp_client, llm_client)

            logger.info("✅ Medical search agent imported and initialized successfully")
            logger.info(f"Agent type: {type(agent)}")
            logger.info(f"MCP client: {type(mcp_client)}")
            logger.info(f"LLM client: {type(llm_client)}")

            return True

        except Exception as e:
            logger.exception(f"❌ Medical search agent import/init error: {e}")
            return False

    def diagnose_request_routing(self) -> dict[str, str]:
        """Analyze healthcare system logs for request routing patterns."""
        logger.info("Diagnosing request routing patterns")

        analysis = {
            "agent_selection": "unknown",
            "intent_classification": "unknown",
            "mcp_calls": "unknown",
            "error_patterns": "unknown",
        }

        try:
            healthcare_log = self.log_files["healthcare_system"]
            if not healthcare_log.exists():
                logger.warning("Healthcare system log not found")
                return analysis

            with open(healthcare_log) as f:
                recent_lines = f.readlines()[-100:]  # Last 100 lines

            recent_content = "".join(recent_lines).lower()

            # Analyze patterns
            if "agent" in recent_content:
                analysis["agent_selection"] = "found_agent_references"

            if any(word in recent_content for word in ["medical", "clinical", "health"]):
                analysis["intent_classification"] = "medical_keywords_present"

            if "mcp" in recent_content:
                analysis["mcp_calls"] = "mcp_activity_detected"

            if any(word in recent_content for word in ["error", "exception", "failed"]):
                analysis["error_patterns"] = "errors_detected"

            logger.info(f"Request routing analysis: {analysis}")

        except Exception as e:
            logger.exception(f"❌ Request routing analysis error: {e}")

        return analysis


async def run_open_webui_medical_routing_tests():
    """Run comprehensive Open WebUI medical routing diagnostic tests."""
    print("🏥 Open WebUI Medical Query Routing Diagnostic Tests")
    print("=" * 60)

    test_suite = OpenWebUIMedicalRoutingTest()
    results = {}

    # Test 1: Healthcare API Health
    print("\n1. Testing Healthcare API Health...")
    results["api_health"] = await test_suite.test_healthcare_api_health()

    # Test 2: Medical Agent Import
    print("\n2. Testing Medical Agent Import...")
    results["agent_import"] = await test_suite.test_medical_agent_import()

    # Test 3: Direct Medical Query (Key Test)
    print("\n3. Testing Direct Medical Query (Key Diagnostic)...")
    results["direct_medical_query"] = await test_suite.test_direct_medical_query_api()

    # Test 4: Request Routing Analysis
    print("\n4. Analyzing Request Routing Patterns...")
    routing_analysis = test_suite.diagnose_request_routing()
    results["routing_analysis"] = routing_analysis

    # Summary
    print("\n🔍 DIAGNOSTIC SUMMARY")
    print("=" * 40)

    for test_name, result in results.items():
        if test_name == "routing_analysis":
            print(f"📊 {test_name}: {result}")
        else:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name}")

    # Critical findings
    if not results.get("direct_medical_query", False):
        print("\n⚠️  CRITICAL FINDING:")
        print("   Direct medical queries are NOT triggering medical search agent")
        print("   This confirms the Open WebUI integration issue")
        print("   Next steps: Investigate agent selection/routing logic")

    return results


if __name__ == "__main__":
    asyncio.run(run_open_webui_medical_routing_tests())
