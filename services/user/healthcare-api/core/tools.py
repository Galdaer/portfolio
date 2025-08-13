"""
Healthcare Tool Registry
Placeholder implementation for healthcare tool management
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Placeholder tool registry for healthcare AI tools"""

    def __init__(self):
        self._initialized = False
        self._tools = {}

    async def initialize(self) -> None:
        """Initialize tool registry"""
        self._initialized = True
        logger.info("Tool registry initialized (placeholder)")

    async def get_available_tools(self) -> list[dict[str, Any]]:
        """Get available tools - queries MCP client for real tools"""
        if not self._initialized:
            await self.initialize()

        # Get real tools from MCP client - no fallbacks to expose real errors
        from core.dependencies import get_mcp_client
        mcp_client = await get_mcp_client()

        if not mcp_client:
            raise RuntimeError("MCP client not available - tool registry requires MCP connection")

        mcp_tools = await mcp_client.get_available_tools()

        # Convert MCP tools to our format
        available_tools = []
        for tool in mcp_tools:
            tool_info = {
                "id": getattr(tool, "name", str(tool)),
                "name": getattr(tool, "name", str(tool)),
                "type": "healthcare_tool",
                "status": "available",
                "description": getattr(tool, "description", ""),
            }
            available_tools.append(tool_info)

        logger.info(f"Retrieved {len(available_tools)} tools from MCP client")
        return available_tools


# Global registry instance
tool_registry = ToolRegistry()
