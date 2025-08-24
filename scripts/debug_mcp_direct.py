#!/usr/bin/env python3
"""Test script to debug MCP client stdio communication"""

import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_direct_mcp():
    params = StdioServerParameters(
        command="docker",
        args=[
            "exec",
            "-i",
            "-u",
            "node",
            "-e",
            "MCP_TRANSPORT=stdio-only",
            "-e",
            "NO_COLOR=1",
            "healthcare-mcp",
            "sh",
            "-c",
            "node /app/build/stdio_entry.js 2> /app/logs/debug_mcp_test.err",
        ],
        env={"NO_COLOR": "1"},
    )

    print("Testing MCP stdio client...")
    try:
        async with stdio_client(params) as (read_stream, write_stream):
            print("Streams opened successfully")
            session = ClientSession(read_stream, write_stream)
            print("Initializing session...")
            await asyncio.wait_for(session.initialize(), timeout=10)
            print("Session initialized!")

            print("Listing tools...")
            tools_response = await asyncio.wait_for(session.list_tools(), timeout=10)
            print(
                f"Tools found: {len(tools_response.tools) if hasattr(tools_response, 'tools') else 'unknown'}",
            )

            if hasattr(tools_response, "tools"):
                for tool in tools_response.tools[:3]:  # Show first 3
                    print(f"  - {tool.name}: {tool.description[:50]}...")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_direct_mcp())
