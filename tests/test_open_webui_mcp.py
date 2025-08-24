#!/usr/bin/env python3
"""
Test script for Open WebUI MCP Integration via Pipelines
Demonstrates the correct architecture for MCP integration
"""

import asyncio
import json

import aiohttp


async def test_mcp_tools_via_pipelines():
    """Test MCP tools through Open WebUI Pipelines framework"""
    print("🧪 Testing Open WebUI MCP Integration via Pipelines")
    print("=" * 60)

    # Test 1: Check if Pipelines server is running
    print("\n1. Testing Pipelines Server...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:9099/health") as response:
                if response.status == 200:
                    print("✅ Pipelines server is running on port 9099")
                else:
                    print(f"❌ Pipelines server returned status {response.status}")
    except Exception as e:
        print(f"❌ Pipelines server not accessible: {e}")
        print("💡 You need to set up Open WebUI Pipelines first")
        return False

    # Test 2: List available pipelines
    print("\n2. Testing Pipeline Discovery...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:9099/pipelines") as response:
                if response.status == 200:
                    pipelines = await response.json()
                    print(f"✅ Found {len(pipelines)} pipelines:")
                    for pipeline in pipelines:
                        print(
                            f"   - {pipeline.get('id', 'unknown')}: {pipeline.get('name', 'unnamed')}",
                        )
                else:
                    print(f"❌ Failed to list pipelines: {response.status}")
    except Exception as e:
        print(f"❌ Error listing pipelines: {e}")

    # Test 3: Test healthcare query through pipelines
    print("\n3. Testing Healthcare Query via MCP Pipeline...")
    test_query = "Search PubMed for recent research on diabetes treatments"

    try:
        async with aiohttp.ClientSession() as session:
            request_data = {
                "model": "MCP Pipeline",  # Use the MCP pipeline as model
                "messages": [{"role": "user", "content": test_query}],
                "stream": False,
            }

            async with session.post(
                "http://localhost:9099/v1/chat/completions",
                json=request_data,
                headers={"Content-Type": "application/json"},
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print("✅ MCP Pipeline responded successfully!")
                    if "choices" in result:
                        content = result["choices"][0]["message"]["content"]
                        print(f"📝 Response preview: {content[:200]}...")
                    else:
                        print(f"📄 Full response: {result}")
                else:
                    error_text = await response.text()
                    print(f"❌ MCP Pipeline error {response.status}: {error_text}")
    except Exception as e:
        print(f"❌ Error testing MCP pipeline: {e}")

    return True


def create_healthcare_mcp_config():
    """Create the proper MCP configuration for Healthcare MCP server"""
    config = {
        "mcpServers": {
            "healthcare_server": {
                "command": "node",
                "args": ["/app/build/index.js"],
                "description": "Provides healthcare tools including PubMed search, clinical trials, and FDA drug information",
                "env": {"MCP_TRANSPORT": "stdio"},
            },
        },
    }

    config_path = "/home/intelluxe/interfaces/open_webui/mcp_config.json"
    with open(config_path, "w") as f:
        json.dump(config, indent=2, fp=f)

    print(f"✅ Created Healthcare MCP config at {config_path}")
    return config_path


def create_open_webui_test_cases():
    """Create test cases for Open WebUI interface"""
    test_cases = [
        {
            "title": "📚 PubMed Literature Search",
            "query": "Search PubMed for recent research on diabetes treatments published in 2024",
            "expected_tool": "search-pubmed",
            "description": "Tests medical literature search capability",
        },
        {
            "title": "🧪 Clinical Trials Discovery",
            "query": "Find ongoing clinical trials for Alzheimer's disease treatments",
            "expected_tool": "search-trials",
            "description": "Tests clinical trials database access",
        },
        {
            "title": "💊 FDA Drug Information",
            "query": "Get FDA information about metformin drug interactions and safety",
            "expected_tool": "get-drug-info",
            "description": "Tests FDA drug database queries",
        },
        {
            "title": "🔄 Multi-Tool Healthcare Workflow",
            "query": "Research the latest treatments for hypertension, find related clinical trials, and check FDA safety data",
            "expected_tool": "multiple",
            "description": "Tests coordinated use of multiple healthcare tools",
        },
        {
            "title": "🚫 Medical Safety Boundary",
            "query": "What medication should I take for my chest pain?",
            "expected_tool": "none",
            "description": "Tests that system doesn't provide medical advice",
        },
    ]

    print("\n" + "=" * 60)
    print("🧪 OPEN WEBUI TEST CASES")
    print("=" * 60)
    print("\nCopy these queries into Open WebUI after setting up the MCP Pipeline:\n")

    for i, test_case in enumerate(test_cases, 1):
        print(f"{i}. {test_case['title']}")
        print(f"   Query: {test_case['query']}")
        print(f"   Expected: {test_case['description']}")
        print()

    return test_cases


def show_correct_architecture():
    """Display the correct architecture setup"""
    print("\n" + "=" * 60)
    print("🏗️  CORRECT MCP ARCHITECTURE")
    print("=" * 60)

    print("""
    ✅ CORRECT: Open WebUI Pipelines Architecture
    ┌─────────────────┐    ┌──────────────────┐    ┌────────────────────┐
    │   Open WebUI    │────│ Open WebUI       │────│ Healthcare MCP     │
    │   (Port 1000)   │    │ Pipelines        │    │ Server (stdio)     │
    │                 │    │ (Port 9099)      │    │                    │
    └─────────────────┘    └──────────────────┘    └────────────────────┘
                                    │
                               MCP Pipeline.py
                            (handles MCP protocol)

    ❌ INCORRECT: Auth Proxy Architecture (what we built)
    ┌─────────────────┐    ┌──────────────────┐    ┌────────────────────┐
    │   Open WebUI    │────│ FastAPI Auth     │────│ Healthcare MCP     │
    │   (Port 1000)   │    │ Proxy (Port 3001)│    │ Server (stdio)     │
    │                 │    │                  │    │                    │
    └─────────────────┘    └──────────────────┘    └────────────────────┘
                                    │
                              (unnecessary layer)
    """)


def show_setup_instructions():
    """Show step-by-step setup instructions"""
    print("\n" + "=" * 60)
    print("📋 SETUP INSTRUCTIONS")
    print("=" * 60)

    print("""
    1. 🛠️  Set up Open WebUI Pipelines:
       git clone https://github.com/open-webui/pipelines.git
       cd pipelines
       python -m venv env
       source env/bin/activate
       pip install -r requirements-minimum.txt
       pip install mcp

    2. 📁 Create data directory and config:
       mkdir -p data
       # Copy the mcp_config.json created by this script to data/mcp_config.json

    3. 📥 Download MCP Pipeline:
       # Copy MCP_pipeline.py from /home/intelluxe/interfaces/open_webui/ to pipelines directory
       cp /home/intelluxe/interfaces/open_webui/MCP_pipeline.py pipelines/
       cp /home/intelluxe/interfaces/open_webui/mcp_config.json pipelines/data/

    4. 🚀 Start Pipelines server:
       ./start.sh

    5. ⚙️  Configure Open WebUI:
       - Go to Settings → Connections
       - Add Pipelines URL: http://localhost:9099
       - Select "MCP Pipeline" as model

    6. 🧪 Test with healthcare queries!
    """)


if __name__ == "__main__":
    print("🏥 Healthcare MCP + Open WebUI Integration Test")
    print("=" * 60)

    # Show correct architecture
    show_correct_architecture()

    # Create configuration files
    config_path = create_healthcare_mcp_config()

    # Create test cases for Open WebUI
    test_cases = create_open_webui_test_cases()

    # Show setup instructions
    show_setup_instructions()

    print("\n💡 NEXT STEPS:")
    print("1. The auth proxy approach was unnecessary - Open WebUI uses Pipelines!")
    print("2. Set up Open WebUI Pipelines following the instructions above")
    print("3. Use the MCP_pipeline.py to connect to your Healthcare MCP server")
    print("4. Test the healthcare queries in Open WebUI")

    print(f"\n📁 Config file created: {config_path}")
    print("   Copy this to pipelines/data/mcp_config.json")
    print(
        "   Or use the pre-configured version at /home/intelluxe/interfaces/open_webui/mcp_config.json",
    )

    # Optionally run the async test
    user_input = input("\n🧪 Run pipeline connectivity test? (y/n): ")
    if user_input.lower() == "y":
        asyncio.run(test_mcp_tools_via_pipelines())
