"""
Healthcare MCP Client for stdio communication with healthcare-mcp server
Uses direct subprocess communication to bypass problematic anyio task group issues
in the standard MCP Python client library.

Logs are routed through the healthcare-compliant logger so they appear in logs/.
"""

import asyncio
import json
import os
from typing import Any

from core.infrastructure.healthcare_logger import get_healthcare_logger

logger = get_healthcare_logger("infrastructure.mcp")


class HealthcareMCPClient:
    """Direct subprocess MCP client that bypasses anyio issues."""

    def __init__(self, server_command: str | None = None):
        # Use direct subprocess communication for single-container architecture
        self.mcp_server_path = os.getenv("MCP_SERVER_PATH", "/app/mcp-server/build/stdio_entry.js")

        # Check if we're in combined container mode
        if os.path.exists(self.mcp_server_path):
            # Single container: spawn MCP server as subprocess
            logger.info(f"Using single-container MCP server at {self.mcp_server_path}")

            # Use the same environment variables as the original healthcare-mcp.conf
            self.env = {
                "MCP_TRANSPORT": "stdio-only",
                "NO_COLOR": "1",
                "FHIR_BASE_URL": os.getenv("FHIR_BASE_URL", "http://172.20.0.13:5432"),
                "PUBMED_API_KEY": os.getenv("PUBMED_API_KEY", "test"),
                "CLINICALTRIALS_API_KEY": os.getenv("CLINICALTRIALS_API_KEY", "test"),
                # Inherit additional environment variables from container
                "POSTGRES_HOST": os.getenv("POSTGRES_HOST", "postgresql"),
                "REDIS_HOST": os.getenv("REDIS_HOST", "redis"),
                "ENVIRONMENT": os.getenv("ENVIRONMENT", "development"),
                "LOG_LEVEL": os.getenv("LOG_LEVEL", "info"),
            }
            logger.info(
                f"MCP environment configured with API keys and service URLs: {list(self.env.keys())}",
            )
            self.use_local_server = True
        else:
            # Fallback mode: Not in single container, would need docker exec
            logger.warning("MCP server not found locally, direct subprocess mode unavailable")
            self.use_local_server = False
            raise RuntimeError("MCP server not available in this container configuration")

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call an MCP tool using direct subprocess communication."""
        if not self.use_local_server:
            return {"status": "error", "error": "MCP server not available"}

        try:
            logger.info(f"Starting MCP subprocess call for tool: {tool_name}")

            # CRITICAL DEBUG: Log the exact command and environment
            logger.error(f"CRITICAL DEBUG - MCP server path: {self.mcp_server_path}")
            logger.error(f"CRITICAL DEBUG - Environment vars: {json.dumps(self.env, indent=2)}")

            # Start MCP server as subprocess
            proc = await asyncio.create_subprocess_exec(
                "node",
                self.mcp_server_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self.env,
            )

            # Send initialize message
            init_msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
                    "clientInfo": {"name": "healthcare-api", "version": "1.0"},
                },
            }

            proc.stdin.write((json.dumps(init_msg) + "\n").encode())
            await proc.stdin.drain()

            # Read initialize response
            init_response_data = await proc.stdout.readline()
            init_response = json.loads(init_response_data.decode())

            if "error" in init_response:
                msg = f"MCP initialization failed: {init_response['error']}"
                raise RuntimeError(msg)

            logger.debug(
                f"MCP initialized successfully: {init_response.get('result', {}).get('serverInfo', {})}",
            )

            # Send tool call
            tool_msg = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            }

            # CRITICAL DEBUG: Log the exact tool message being sent
            logger.error(
                f"CRITICAL DEBUG - Tool message being sent: {json.dumps(tool_msg, indent=2)}",
            )

            proc.stdin.write((json.dumps(tool_msg) + "\n").encode())
            await proc.stdin.drain()

            # Read tool response
            tool_response_data = await proc.stdout.readline()
            tool_response = json.loads(tool_response_data.decode())

            # DEBUG: Log the exact response structure
            logger.info(
                f"DEBUG: Raw tool response for {tool_name}: {json.dumps(tool_response, indent=2)[:500]}...",
            )

            # Clean shutdown
            proc.stdin.close()
            await proc.wait()

            if "error" in tool_response:
                logger.error(f"MCP tool call failed: {tool_response['error']}")
                return {"status": "error", "error": tool_response["error"]}

            result = tool_response.get("result", {})
            logger.info(
                f"DEBUG: Extracted result for {tool_name}: {json.dumps(result, indent=2)[:500]}...",
            )
            logger.info(f"MCP tool call completed successfully: {tool_name}")
            return result

        except Exception as e:
            logger.exception(f"MCP subprocess call failed: {e}")
            return {"status": "error", "error": str(e)}

    async def _ensure_connected(self) -> None:
        """Compatibility no-op: connections are established per-call."""

    async def connect(self) -> None:
        """No-op connect for compatibility (connections are created per call)."""
        logger.info(
            "MCP direct subprocess client ready (per-call connections)",
            extra={
                "healthcare_context": {
                    "operation_type": "mcp_connect",
                    "server_path": self.mcp_server_path,
                    "env_keys": sorted(self.env.keys()),
                },
            },
        )

    async def get_available_tools(self) -> list[dict[str, Any]]:
        """List available tools using a short-lived session with timeouts."""
        import asyncio

        logger.info("Listing MCP tools via short-lived session")
        tools: list[dict[str, Any]] = []
        # Open, list, close in the same task to avoid cancel-scope issues
        from mcp import ClientSession  # type: ignore
        from mcp.client.stdio import stdio_client  # type: ignore

        try:
            async with stdio_client("node", self.mcp_server_path) as (read_stream, write_stream):
                session = ClientSession(read_stream, write_stream)
                # Guard initialization and list with timeouts to avoid hangs
                await asyncio.wait_for(session.initialize(), timeout=45)
                tools_response = await asyncio.wait_for(session.list_tools(), timeout=45)
                if hasattr(tools_response, "tools"):
                    tools = tools_response.tools  # type: ignore[assignment]
                elif isinstance(tools_response, dict):
                    tools = tools_response.get("tools", [])  # type: ignore[assignment]
            logger.info(f"Discovered {len(tools)} MCP tools")
        except TimeoutError:
            logger.exception(
                "Timeout while listing MCP tools (possible stdout banner contamination). Ensure the MCP stdio server does not print human-readable logs to stdout; use stderr for banners.",
                extra={
                    "healthcare_context": {
                        "operation_type": "mcp_list_tools_timeout",
                        "hint": "Move any 'STDIO server ready...' or startup banners to stderr when MCP_TRANSPORT=stdio",
                    },
                },
            )

    async def list_tools(self) -> list[str]:
        """List available MCP tools using direct subprocess call."""
        try:
            logger.info("Listing MCP tools via direct subprocess")

            # Start MCP server as subprocess
            proc = await asyncio.create_subprocess_exec(
                "node",
                self.mcp_server_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self.env,
            )

            # Send initialize message
            init_msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
                    "clientInfo": {"name": "healthcare-api", "version": "1.0"},
                },
            }

            proc.stdin.write((json.dumps(init_msg) + "\n").encode())
            await proc.stdin.drain()

            # Read initialize response
            init_response_data = await proc.stdout.readline()
            json.loads(init_response_data.decode())

            # Send tools/list message
            list_msg = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}

            proc.stdin.write((json.dumps(list_msg) + "\n").encode())
            await proc.stdin.drain()

            # Read tools list response
            list_response_data = await proc.stdout.readline()
            list_response = json.loads(list_response_data.decode())

            # Clean shutdown
            proc.stdin.close()
            await proc.wait()

            tools = []
            if "result" in list_response and "tools" in list_response["result"]:
                tools = [tool["name"] for tool in list_response["result"]["tools"]]

            logger.info(f"Found {len(tools)} MCP tools: {tools}")
            return tools

        except Exception as e:
            logger.exception(f"Error listing MCP tools: {e}")
            return []

    async def call_healthcare_tool(
        self, tool_name: str, arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Healthcare convenience wrapper returning raw result or error payload."""
        result = await self.call_tool(tool_name, arguments)
        if result.get("status") == "success":
            return result.get("content", {})
        return {"error": result.get("error", "Unknown error"), "status": "error"}

    async def disconnect(self) -> None:
        """No-op disconnect for compatibility (nothing persistent to close)."""
        logger.info("MCP direct subprocess client disconnect (no persistent session)")
