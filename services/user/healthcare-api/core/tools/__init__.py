"""
Tool Registry for Intelluxe AI

Manages integration with Healthcare-MCP and custom healthcare tools.
Provides unified interface for tool discovery and execution.
"""

import asyncio
import logging
from typing import Any

from config.app import config

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Registry for managing healthcare tools through MCP integration

    Provides tool discovery, capability mapping, and execution
    through the Healthcare-MCP server.
    """

    def __init__(self) -> None:
        self.mcp_client: Any = None  # Will be set to HealthcareMCPClient
        self._available_tools: list[dict[str, Any]] = []
        self._tool_versions: dict[str, str] = {}
        self._tool_capabilities: dict[str, Any] = {}
        self._tool_performance: dict[str, dict[str, Any]] = {}
        self._summary_plugins: dict[str, Any] = {}
        self._initialized: bool = False

    def register_transcription_plugin(self, plugin_name: str, plugin_obj: Any) -> None:
        """Register a transcription plugin (e.g., SOAP note generator, doctor summary style)"""
        self._summary_plugins[plugin_name] = plugin_obj

    def get_transcription_plugin(self, plugin_name: str) -> Any:
        """Get a registered transcription plugin"""
        return self._summary_plugins.get(plugin_name)

    async def initialize(self, mcp_client: Any = None) -> None:
        """Initialize with MCP client and discover available tools"""
        try:
            # Use provided MCP client (from HealthcareServices)
            if mcp_client is not None:
                self.mcp_client = mcp_client

            # Test connection and discover tools
            await self._discover_tools()
            self._initialized = True

            logger.info(f"Tool registry initialized with {len(self._available_tools)} tools")

        except Exception as e:
            logger.exception(f"Failed to initialize tool registry: {e}")
            raise

    async def close(self) -> None:
        """Close MCP client"""
        if self.mcp_client:
            await self.mcp_client.aclose()

        self._initialized = False
        logger.info("Tool registry closed")

    async def health_check(self) -> dict[str, Any]:
        """Check health of tool services"""
        if not self._initialized or self.mcp_client is None:
            return {"status": "not_initialized"}

        try:
            # Test MCP server connection - adapt to different client interfaces
            if hasattr(self.mcp_client, "get"):
                # HTTP client interface
                response = await self.mcp_client.get("/health")
                mcp_connected = response.status_code == 200
            elif hasattr(self.mcp_client, "call_tool"):
                # DirectMCPClient stdio interface - test with a simple tool call
                try:
                    await self.mcp_client.call_tool(
                        "search-pubmed", {"query": "test", "max_results": 1},
                    )
                    mcp_connected = True
                except Exception:
                    mcp_connected = False
            else:
                # Unknown client type
                mcp_connected = False

            if mcp_connected:
                return {
                    "status": "healthy",
                    "mcp_connected": True,
                    "available_tools": len(self._available_tools),
                    "tools": [tool.get("name") for tool in self._available_tools],
                }
            return {
                "status": "unhealthy",
                "mcp_connected": False,
                "error": "MCP connection failed",
            }

        except Exception as e:
            logger.exception(f"Tool health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    async def _discover_tools(self) -> None:
        """Discover available tools from MCP server via stdio protocol"""
        if self.mcp_client is None:
            logger.error("MCP client is not initialized")
            self._available_tools = []
            return
        try:
            # Use MCP protocol method for tool discovery (not HTTP)
            if hasattr(self.mcp_client, "get_available_tools"):
                tools = await self.mcp_client.get_available_tools()
                self._available_tools = tools
            elif hasattr(self.mcp_client, "list_tools"):
                tools = await self.mcp_client.list_tools()
                self._available_tools = tools
            elif hasattr(self.mcp_client, "get_tools"):
                tools = await self.mcp_client.get_tools()
                self._available_tools = tools
            else:
                # Fallback - assume client has tools method or attribute
                logger.warning("MCP client doesn't have expected tool discovery methods")
                self._available_tools = []

            # Track version and capabilities if available
            for tool in self._available_tools:
                name = tool.get("name") if isinstance(tool, dict) else getattr(tool, "name", None)
                version = (
                    tool.get("version", "unknown")
                    if isinstance(tool, dict)
                    else getattr(tool, "version", "unknown")
                )
                capabilities = (
                    tool.get("capabilities", {})
                    if isinstance(tool, dict)
                    else getattr(tool, "capabilities", {})
                )
                if name is not None:
                    self._tool_versions[name] = version
                    self._tool_capabilities[name] = capabilities
            logger.info(f"Discovered {len(self._available_tools)} tools via MCP stdio")
        except Exception as e:
            logger.warning(f"Failed to discover tools: {e}")
            self._available_tools = []

    def log_tool_performance(self, tool_name: str, metrics: dict[str, Any]) -> None:
        """Log performance metrics for a tool"""
        self._tool_performance[tool_name] = metrics

    def register_summary_plugin(self, plugin_name: str, plugin_obj: Any) -> None:
        """Register a summary/transcription plugin"""
        self._summary_plugins[plugin_name] = plugin_obj

    def get_summary_plugin(self, plugin_name: str) -> Any:
        """Get a registered summary/transcription plugin"""
        return self._summary_plugins.get(plugin_name)

    async def get_available_tools(self) -> list[dict[str, Any]]:
        """Get list of available tools"""
        if not self._initialized:
            raise RuntimeError("Tool registry not initialized")

        return self._available_tools.copy()

    async def execute_tool(self, tool_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool with given parameters"""
        if not self._initialized:
            raise RuntimeError("Tool registry not initialized")

        try:
            if self.mcp_client is None:
                raise RuntimeError("MCP client is not initialized")

            # Adapt to different client interfaces
            if hasattr(self.mcp_client, "post"):
                # HTTP client interface
                payload = {"tool": tool_name, "parameters": parameters}
                response = await self.mcp_client.post("/execute", json=payload)
                response.raise_for_status()
                result: dict[str, Any] = response.json()
            elif hasattr(self.mcp_client, "call_tool"):
                # DirectMCPClient stdio interface
                result = await self.mcp_client.call_tool(tool_name, parameters)
                # Ensure result is a dict
                if not isinstance(result, dict):
                    result = {"result": result}
            else:
                msg = f"Unsupported MCP client type: {type(self.mcp_client)}"
                raise RuntimeError(msg)

            return result

        except Exception as e:
            logger.exception(f"Failed to execute tool {tool_name}: {e}")
            raise

    async def execute_tools_concurrently(
        self,
        tool_requests: list[dict[str, Any]],
        timeout: float = 30.0,
    ) -> list[dict[str, Any]]:
        """Execute multiple tools concurrently using asyncio for healthcare workflows"""
        if not self._initialized:
            raise RuntimeError("Tool registry not initialized")

        # Create tasks for concurrent execution
        tasks = []
        for req in tool_requests:
            tool_name = req.get("tool_name")
            parameters = req.get("parameters", {})
            if tool_name:
                task = asyncio.create_task(
                    self.execute_tool(tool_name, parameters),
                    name=f"tool_{tool_name}",
                )
                tasks.append((req.get("request_id", "unknown"), task))

        # Execute with timeout for healthcare responsiveness
        results = []
        try:
            completed_tasks = await asyncio.wait_for(
                asyncio.gather(*[task for _, task in tasks], return_exceptions=True),
                timeout=timeout,
            )

            for i, result in enumerate(completed_tasks):
                request_id = tasks[i][0]
                if isinstance(result, Exception):
                    results.append(
                        {"request_id": request_id, "success": False, "error": str(result)},
                    )
                else:
                    results.append({"request_id": request_id, "success": True, "result": result})

        except TimeoutError:
            logger.exception(f"Tool execution batch timed out after {timeout}s")
            # Cancel remaining tasks
            for _, task in tasks:
                if not task.done():
                    task.cancel()
            raise

        return results

    async def get_tool_capabilities(self, tool_name: str) -> dict[str, Any]:
        """Get capabilities and schema for a specific tool"""
        if not self._initialized:
            raise RuntimeError("Tool registry not initialized")

        if self.mcp_client is None:
            raise RuntimeError("MCP client is not initialized")

        try:
            # Use MCP protocol method for tool capabilities (not HTTP)
            if hasattr(self.mcp_client, "get_tool_schema"):
                capabilities = await self.mcp_client.get_tool_schema(tool_name)
            elif hasattr(self.mcp_client, "describe_tool"):
                capabilities = await self.mcp_client.describe_tool(tool_name)
            else:
                # Fallback to cached capabilities from discovery
                capabilities = self._tool_capabilities.get(tool_name, {})

            return capabilities

        except Exception as e:
            logger.exception(f"Failed to get capabilities for tool {tool_name}: {e}")
            raise


# Global tool registry instance
tool_registry = ToolRegistry()
