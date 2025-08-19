#!/usr/bin/env python3
"""Standalone probe to list tools from healthcare MCP stdio server.
Usage: python3 scripts/mcp_stdio_probe.py
Relies on interfaces/open_webui/mcp_config.json for command/args under key 'healthcare_server'.
"""
import asyncio
import json
from pathlib import Path
from typing import Any

CONFIG_PATH = Path("/home/intelluxe/interfaces/open_webui/mcp_config.json")

async def main():
    try:
        from mcp import ClientSession, StdioServerParameters  # type: ignore
        from mcp.client.stdio import stdio_client  # type: ignore
    except Exception as e:
        print(f"MCP SDK not available: {e}")
        return 1

    if not CONFIG_PATH.exists():
        print(f"Config not found: {CONFIG_PATH}")
        return 1
    cfg = json.loads(CONFIG_PATH.read_text())
    servers = cfg.get("mcpServers", {})
    hc = servers.get("healthcare_server")
    if not hc:
        print("healthcare_server entry missing in config")
        return 1
    params = StdioServerParameters(command=hc["command"], args=hc.get("args", []), env=hc.get("env", {}))
    async with stdio_client(params) as (read_stream, write_stream):  # type: ignore
        session = ClientSession(read_stream, write_stream)
        await session.initialize()
        tools_resp = await session.list_tools()
        tools: Any = getattr(tools_resp, "tools", [])
        print(f"Tool count: {len(tools)}")
        for t in tools:
            name = getattr(t, "name", None)
            if name is None and isinstance(t, dict):  # fallback defensive
                name = t.get("name")
            print(" -", name)
    return 0

if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
