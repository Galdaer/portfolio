"""
Healthcare MCP Client for stdio communication with healthcare-mcp server
Stateless wrapper that opens a short-lived stdio session per call to avoid AnyIO
cancel-scope issues on __aexit__ and to ensure clean shutdown without Ctrl+C.

Logs are routed through the healthcare-compliant logger so they appear in logs/.
"""
from typing import Any, Dict, List, Optional

from core.infrastructure.healthcare_logger import get_healthcare_logger

logger = get_healthcare_logger("infrastructure.mcp")


class HealthcareMCPClient:
    """Lightweight MCP client using short-lived stdio sessions per request."""

    def __init__(self, server_command: Optional[str] = None):
        # Import here to keep symbols bound even if library isn't installed at import-time
        try:
            from mcp import StdioServerParameters  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError(f"MCP library not available: {e}")

        # EXPERIMENTAL: Run stdio_entry.js directly instead of via docker exec  
        # This avoids potential docker exec stdio stream corruption issues
        command = server_command or "bash"
        if command == "bash":
            # Copy stdio_entry.js to a temp location and run it directly
            sh_cmd = """
            set -e
            # Copy the stdio entry from container to temp
            docker cp healthcare-mcp:/app/build/stdio_entry.js /tmp/stdio_entry_temp.js 2>/dev/null
            # Run it directly with proper env
            export MCP_TRANSPORT=stdio-only
            export NO_COLOR=1
            node /tmp/stdio_entry_temp.js 2>/tmp/mcp_direct.err
            """
            args = ["-c", sh_cmd]
        else:
            # Fallback to original docker exec approach
            sh_cmd = "node /app/build/stdio_entry.js 2> /app/logs/mcp_stdio_entry.err"
            args = [
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
                sh_cmd,
            ]
        # Environment variables here affect the docker CLI only; the actual server env is passed via -e above.
        env = {"NO_COLOR": "1"}

        self.params = StdioServerParameters(command=command, args=args, env=env)
        # Compatibility attribute so existing code won't try to lazy-connect
        self.session = True  # truthy sentinel

    async def _ensure_connected(self) -> None:
        """Compatibility no-op: sessions are established per-call."""
        await self.connect()

    async def connect(self) -> None:
        """No-op connect for compatibility (sessions are created per call)."""
        logger.info(
            "MCP stateless client ready (per-call sessions)",
            extra={
                "healthcare_context": {
                    "operation_type": "mcp_connect",
                    "command": self.params.command,
                    "args": self.params.args,
                    "env_keys": sorted(list(getattr(self.params, "env", {}).keys())),
                }
            },
        )

    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """List available tools using a short-lived session with timeouts."""
        import asyncio
        logger.info("Listing MCP tools via short-lived session")
        tools: List[Dict[str, Any]] = []
        # Open, list, close in the same task to avoid cancel-scope issues
        from mcp import ClientSession  # type: ignore
        from mcp.client.stdio import stdio_client  # type: ignore
        try:
            async with stdio_client(self.params) as (read_stream, write_stream):
                session = ClientSession(read_stream, write_stream)
                # Guard initialization and list with timeouts to avoid hangs
                await asyncio.wait_for(session.initialize(), timeout=45)
                tools_response = await asyncio.wait_for(session.list_tools(), timeout=45)
                if hasattr(tools_response, "tools"):
                    tools = tools_response.tools  # type: ignore[assignment]
                elif isinstance(tools_response, dict):
                    tools = tools_response.get("tools", [])  # type: ignore[assignment]
            logger.info(f"Discovered {len(tools)} MCP tools")
        except asyncio.TimeoutError:
            logger.error(
                "Timeout while listing MCP tools (possible stdout banner contamination). Ensure the MCP stdio server does not print human-readable logs to stdout; use stderr for banners.",
                extra={
                    "healthcare_context": {
                        "operation_type": "mcp_list_tools_timeout",
                        "hint": "Move any 'STDIO server ready...' or startup banners to stderr when MCP_TRANSPORT=stdio",
                    }
                },
            )
        except Exception as e:  # pragma: no cover
            logger.exception(
                f"Error listing MCP tools: {e}",
                extra={"healthcare_context": {"operation_type": "mcp_list_tools_error", "error": str(e)}},
            )
        return tools

    async def call_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Call a tool using a short-lived session and return a wrapped result."""
        import asyncio
        args = arguments or {}
        logger.info(f"MCP call start: tool={tool_name} args_keys={list(args.keys())}")
        try:
            from mcp import ClientSession  # type: ignore
            from mcp.client.stdio import stdio_client  # type: ignore
            async with stdio_client(self.params) as (read_stream, write_stream):
                session = ClientSession(read_stream, write_stream)
                await asyncio.wait_for(session.initialize(), timeout=45)
                result = await asyncio.wait_for(session.call_tool(tool_name, args), timeout=60)
            # After context closes cleanly, log a compact preview
            preview = None
            try:
                if isinstance(result, dict):
                    preview = {k: (len(v) if isinstance(v, list) else type(v).__name__) for k, v in result.items() if k in ("articles", "count", "status")}
                else:
                    preview = str(type(result))
            except Exception:
                preview = "unavailable"
            logger.info(f"MCP call done: tool={tool_name} preview={preview}")
            return {"status": "success", "result": result}
        except asyncio.TimeoutError:
            logger.error(
                f"Timeout calling tool {tool_name} (possible stdout banner contamination). Ensure the MCP stdio server uses clean JSON on stdout and logs to stderr.",
                extra={
                    "healthcare_context": {
                        "operation_type": "mcp_call_timeout",
                        "tool": tool_name,
                        "hint": "No human-readable logs on stdout in stdio mode",
                    }
                },
            )
            return {"status": "error", "error": "timeout"}
        except Exception as e:  # pragma: no cover
            logger.exception(
                f"Failed to call tool {tool_name}: {e}",
                extra={"healthcare_context": {"operation_type": "mcp_call_error", "tool": tool_name, "error": str(e)}},
            )
            return {"status": "error", "error": str(e)}

    async def call_healthcare_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Healthcare convenience wrapper returning raw result or error payload."""
        result = await self.call_tool(tool_name, arguments)
        if result.get("status") == "success":
            return result.get("result", {})
        return {"error": result.get("error", "Unknown error"), "status": "error"}

    async def disconnect(self) -> None:
        """No-op disconnect for compatibility (nothing persistent to close)."""
        logger.info("MCP stateless client disconnect (no persistent session)")
