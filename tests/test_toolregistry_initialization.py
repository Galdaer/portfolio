"""
Diagnostic tests for ToolRegistry initialization and MCP tool discovery.

These tests validate why the system might fall back to direct MCP tools
by checking initialization sequence and available tools.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
import pytest

# Ensure healthcare-api package is importable
PROJECT_ROOT = Path(__file__).resolve().parents[1]
HEALTHCARE_API_PATH = PROJECT_ROOT / "services" / "user" / "healthcare-api"
if str(HEALTHCARE_API_PATH) not in sys.path:
    sys.path.append(str(HEALTHCARE_API_PATH))


@pytest.mark.asyncio
async def test_toolregistry_initialize_and_list_tools():
    # Import without side effects
    from core.tools import tool_registry
    from core.mcp.direct_mcp_client import DirectMCPClient

    client = DirectMCPClient()

    # In host environments the MCP server only exists inside the container.
    # This is expected and should xfail with clear guidance.
    if not os.path.exists(client.mcp_server_path):
        pytest.xfail(
            f"MCP server not available at {client.mcp_server_path}. "
            "This is expected on host - MCP server only exists inside healthcare-api container. "
            "Run inside container with: docker exec healthcare-api python -m pytest"
        )

    # Initialize and discover tools (only runs inside container)
    await tool_registry.initialize(client)
    health = await tool_registry.health_check()

    assert health.get("status") in {"healthy", "unhealthy"}
    assert "available_tools" in health or health.get("status") == "unhealthy"

    # If healthy, ensure at least one known tool exists
    if health.get("status") == "healthy":
        tools = await tool_registry.get_available_tools()
        tool_names = {t.get("name") for t in tools if isinstance(t, dict)}
        assert any(
            name in tool_names for name in {"search-pubmed", "search-clinical-trials", "search-fda"}
        ), f"Expected core tools missing. Found: {sorted(tool_names)}"


@pytest.mark.asyncio
async def test_toolregistry_execute_minimal_tool_if_available():
    from core.tools import tool_registry

    if not tool_registry._initialized:
        pytest.xfail("ToolRegistry not initialized in this environment (MCP server only exists inside healthcare-api container).")

    tools = await tool_registry.get_available_tools()
    names = [t.get("name") for t in tools if isinstance(t, dict)]

    # Pick any available tool that accepts a simple 'query' arg
    candidate = None
    for t in tools:
        if isinstance(t, dict):
            if t.get("name") in {"search-pubmed", "search-clinical-trials", "search-fda"}:
                candidate = t.get("name")
                break
    if not candidate:
        pytest.xfail(f"No suitable tool found. Available: {names}")

    # Execute a smoke request
    result = await tool_registry.execute_tool(candidate, {"query": "test", "max_results": 1})
    assert isinstance(result, dict)
