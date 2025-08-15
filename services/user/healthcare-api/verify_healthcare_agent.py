#!/usr/bin/env python3
"""
Quick verification script for healthcare agent functionality.

This script tests the core components without complex test frameworks.
"""

import asyncio
import sys
import os

# Add healthcare-api to path for local testing
sys.path.insert(0, '/app')  # Container path
sys.path.insert(0, '/home/intelluxe/services/user/healthcare-api')  # Local path


async def verify_setup():
    """Verify that all components are working"""
    print("🔍 Healthcare Agent Verification")
    print("-" * 35)
    
    # Step 1: Test MCP Client
    print("\n1️⃣ Testing MCP Client...")
    try:
        from core.mcp.direct_mcp_client import DirectMCPClient
        
        mcp_client = DirectMCPClient()
        tools = await mcp_client.get_available_tools()
        
        print(f"   ✅ MCP Client: {len(tools)} tools available")
        
        # Show a few tool names
        for i, tool in enumerate(tools[:3]):
            name = tool.get('name', 'Unknown')
            print(f"      - {name}")
        
    except Exception as e:
        print(f"   ❌ MCP Client failed: {e}")
        return False
    
    # Step 2: Test Agent Initialization
    print("\n2️⃣ Testing Agent Initialization...")
    try:
        from core.langchain.agents import HealthcareLangChainAgent
        
        agent = HealthcareLangChainAgent(mcp_client)
        print("   ✅ Agent initialized successfully")
        
    except Exception as e:
        print(f"   ❌ Agent initialization failed: {e}")
        return False
    
    # Step 3: Test Simple Query
    print("\n3️⃣ Testing Simple Query...")
    try:
        response = await agent.process("Hello, test query")
        
        # Handle both string and dict responses
        if isinstance(response, dict):
            if response.get("success") and "formatted_summary" in response:
                text_response = response["formatted_summary"]
                print(f"   ✅ Query successful: {len(text_response)} character response")
                print(f"   📝 Preview: {text_response[:80]}...")
                print(f"   🔧 Agent name: {response.get('agent_name', 'unknown')}")
            else:
                print(f"   ⚠️  Response dict missing expected fields: {list(response.keys())}")
                return False
        elif isinstance(response, str) and len(response) > 0:
            print(f"   ✅ Query successful: {len(response)} character response")
            print(f"   📝 Preview: {response[:80]}...")
        else:
            print(f"   ⚠️  Unexpected response type: {type(response)}")
            return False
            
    except Exception as e:
        print(f"   ❌ Query failed: {e}")
        print(f"      Error type: {type(e).__name__}")
        
        # Provide specific guidance for common errors
        if 'connection' in str(e).lower():
            print("      💡 Check Ollama connectivity")
        elif 'parsing' in str(e).lower():
            print("      💡 Check LangChain agent configuration")
        
        return False
    
    print("\n🎉 All verification steps passed!")
    print("🏥 Healthcare agent is ready for use.")
    return True


def main():
    """Run verification"""
    try:
        success = asyncio.run(verify_setup())
        exit_code = 0 if success else 1
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Verification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Verification crashed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
