#!/usr/bin/env python3
"""
Test script for the LangChain agent scratchpad fix
"""

import asyncio
import sys
import os

# Add the healthcare-api to the path
sys.path.insert(0, "/home/intelluxe/services/user/healthcare-api")


async def test_langchain_agent():
    """Test the fixed LangChain agent"""
    try:
        from core.langchain.agents import HealthcareLangChainAgent
        from core.mcp.direct_mcp_client import DirectMCPClient

        print("🧪 Testing LangChain Agent Fix...")

        # Initialize MCP client
        mcp_client = DirectMCPClient()

        # Initialize agent with verbose mode
        agent = HealthcareLangChainAgent(mcp_client=mcp_client, verbose=True, model="llama3.1:8b")

        print("✅ Agent initialized successfully")

        # Test simple query
        test_query = "What are the symptoms of diabetes?"
        print(f"🔍 Testing query: {test_query}")

        result = await agent.process(test_query)

        if result["success"]:
            print("✅ Agent processing successful!")
            print(f"📄 Response: {result['formatted_summary'][:200]}...")
            print(f"🔧 Intermediate steps: {len(result.get('intermediate_steps', []))}")
        else:
            print("❌ Agent processing failed!")
            print(f"🚫 Error: {result.get('error', 'Unknown error')}")
            print(f"🔧 Error type: {result.get('error_type', 'Unknown')}")

            # Check if it's the specific scratchpad error
            error_msg = result.get("error", "").lower()
            if "agent_scratchpad" in error_msg and "list of base messages" in error_msg:
                print("🔴 CRITICAL: The agent_scratchpad error is still occurring!")
                return False
            else:
                print("🟡 Different error - not the scratchpad issue")

        return result["success"]

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("🔧 Make sure you're in the correct directory and dependencies are installed")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_langchain_agent())
    if success:
        print("\n🎉 SUCCESS: LangChain agent scratchpad fix is working!")
        sys.exit(0)
    else:
        print("\n💥 FAILURE: LangChain agent still has issues")
        sys.exit(1)
