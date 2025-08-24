#!/usr/bin/env python3
"""
Test LangChain Agent Iteration Limits

Tests that the LangChain agent can handle medical queries requiring multiple MCP tool calls
without hitting iteration limits.
"""

import time

import requests


def test_langchain_iteration_limits():
    """Test that LangChain agent can handle multiple MCP tool calls"""

    print("🔍 Testing LangChain agent iteration limits...")

    # Test endpoint
    url = "http://localhost:8000/v1/chat/completions"

    # Medical query that should trigger multiple MCP searches
    medical_query = (
        "Can you help me find recent articles on cardiovascular health and diabetes prevention?"
    )

    payload = {"model": "healthcare", "messages": [{"role": "user", "content": medical_query}]}

    headers = {"Content-Type": "application/json"}

    print(f"📤 Sending medical query: {medical_query}")

    try:
        start_time = time.time()
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        end_time = time.time()

        print(f"⏱️  Response time: {end_time - start_time:.2f} seconds")
        print(f"📊 Status code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

            print(f"✅ Response received (length: {len(content)} chars)")

            # Check for iteration limit error
            if "iteration limit" in content.lower() or "time limit" in content.lower():
                print("❌ FAIL: Agent hit iteration or time limit")
                print(f"Response: {content}")
                return False
            if "connection attempts failed" in content.lower():
                print("❌ FAIL: Connection error (Ollama issue)")
                print(f"Response: {content}")
                return False
            if len(content) < 50:
                print("⚠️  WARNING: Response seems too short")
                print(f"Response: {content}")
                return False
            print("✅ SUCCESS: Agent completed medical query without limits")
            print(f"Response preview: {content[:200]}...")
            return True
        print(f"❌ FAIL: HTTP {response.status_code}")
        print(f"Response: {response.text}")
        return False

    except Exception as e:
        print(f"❌ FAIL: Exception occurred: {e}")
        return False


def test_health_endpoint():
    """Test healthcare API health endpoint"""

    print("🔍 Testing healthcare API health...")

    try:
        response = requests.get("http://localhost:8000/health", timeout=10)

        if response.status_code == 200:
            data = response.json()
            agents = data.get("agents", [])
            print(f"✅ Healthcare API healthy with {len(agents)} agents")
            print(f"   Agents: {', '.join(agents)}")
            return True
        print(f"❌ Health check failed: {response.status_code}")
        return False

    except Exception as e:
        print(f"❌ Health check exception: {e}")
        return False


def main():
    """Run iteration limits test"""

    print("🏥 LangChain Agent Iteration Limits Test")
    print("=" * 50)

    # Test health first
    if not test_health_endpoint():
        print("❌ Health check failed - cannot proceed with tests")
        return False

    print()

    # Test iteration limits
    success = test_langchain_iteration_limits()

    print()
    print("=" * 50)
    if success:
        print("✅ ALL TESTS PASSED: LangChain agent iteration limits working correctly")
    else:
        print("❌ TESTS FAILED: LangChain agent hitting iteration limits")

    return success


if __name__ == "__main__":
    main()
