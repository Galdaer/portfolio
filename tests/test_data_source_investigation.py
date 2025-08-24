#!/usr/bin/env python3
"""
Test the data source investigation pattern from handoff document.

This tests Critical Discovery 3: Database vs External API Investigation
"""

import asyncio
import sys

# Add the healthcare API to the path
sys.path.append("/home/intelluxe/services/user/healthcare-api")

from core.mcp.direct_mcp_client import DirectMCPClient


async def main():
    """Test data source investigation with different medical queries."""
    print("🔍 Testing Data Source Investigation Pattern...")
    print("=" * 60)

    client = DirectMCPClient()

    # Test queries with different characteristics
    test_queries = [
        "diabetes symptoms",  # Common query - likely fast/database
        "rare metabolic disorder phenylketonuria",  # Specific - likely database
        "latest COVID-19 treatment protocols 2025",  # Recent - likely external API
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n🧪 Test {i}: '{query}'")
        print("-" * 40)

        try:
            result = await client.investigate_data_source(query)

            print(f"✅ Source Type: {result['source_type']}")
            print(f"⏱️  Response Time: {result['response_time']:.3f}s")
            print(f"📊 Article Count: {result['article_count']}")
            print(f"🕒 Investigation Time: {result['investigation_time']}")

            # Analysis
            if result["response_time"] < 0.5:
                print("   → Analysis: Fast response indicates local database")
            elif result["response_time"] > 5.0:
                print("   → Analysis: Slow response indicates external API")
            else:
                print("   → Analysis: Medium response indicates hybrid sources")

            if result["article_count"] > 50:
                print("   → Analysis: Large result set indicates comprehensive database")

        except Exception as e:
            print(f"❌ Error investigating '{query}': {e}")
            # This is expected when running from host environment
            if "MCP server not found" in str(e):
                print("   → Note: MCP server is container-only, expected error from host")

    print("\n" + "=" * 60)
    print("🏁 Data Source Investigation Test Complete")
    print("\nNote: Full functionality requires running inside healthcare-api container")
    print("where MCP server is available at /app/mcp-server/build/stdio_entry.js")


if __name__ == "__main__":
    asyncio.run(main())
