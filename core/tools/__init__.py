"""
Tool Registry for Intelluxe AI

Manages integration with Healthcare-MCP and custom healthcare tools.
Provides unified interface for tool discovery and execution.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
import httpx
from config.app import config

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Registry for managing healthcare tools through MCP integration
    
    Provides tool discovery, capability mapping, and execution
    through the Healthcare-MCP server.
    """
    
    def __init__(self):
        self.mcp_client: Optional[httpx.AsyncClient] = None
        self._available_tools: List[Dict[str, Any]] = []
        self._tool_versions: Dict[str, str] = {}
        self._tool_capabilities: Dict[str, Any] = {}
        self._tool_performance: Dict[str, Dict[str, Any]] = {}
        self._summary_plugins: Dict[str, Any] = {}
        self._initialized = False
    def register_transcription_plugin(self, plugin_name: str, plugin_obj: Any) -> None:
        """Register a transcription plugin (e.g., SOAP note generator, doctor summary style)"""
        self._summary_plugins[plugin_name] = plugin_obj

    def get_transcription_plugin(self, plugin_name: str) -> Any:
        """Get a registered transcription plugin"""
        return self._summary_plugins.get(plugin_name)
    
    async def initialize(self) -> None:
        """Initialize MCP client and discover available tools"""
        try:
            self.mcp_client = httpx.AsyncClient(
                base_url=config.mcp_server_url,
                timeout=30.0
            )
            
            # Test connection and discover tools
            await self._discover_tools()
            self._initialized = True
            
            logger.info(f"Tool registry initialized with {len(self._available_tools)} tools")
            
        except Exception as e:
            logger.error(f"Failed to initialize tool registry: {e}")
            raise
    
    async def close(self) -> None:
        """Close MCP client"""
        if self.mcp_client:
            await self.mcp_client.aclose()
        
        self._initialized = False
        logger.info("Tool registry closed")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of tool services"""
        if not self._initialized:
            return {"status": "not_initialized"}
        
        try:
            # Test MCP server connection
            response = await self.mcp_client.get("/health")
            
            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "mcp_connected": True,
                    "available_tools": len(self._available_tools),
                    "tools": [tool.get("name") for tool in self._available_tools]
                }
            else:
                return {
                    "status": "unhealthy",
                    "mcp_connected": False,
                    "error": f"HTTP {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Tool health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    async def _discover_tools(self) -> None:
        """Discover available tools from MCP server and track version/capabilities"""
        try:
            response = await self.mcp_client.get("/tools")
            response.raise_for_status()
            data = response.json()
            self._available_tools = data.get("tools", [])
            # Track version and capabilities if available
            for tool in self._available_tools:
                name = tool.get("name")
                version = tool.get("version", "unknown")
                capabilities = tool.get("capabilities", {})
                self._tool_versions[name] = version
                self._tool_capabilities[name] = capabilities
            logger.info(f"Discovered {len(self._available_tools)} tools")
        except Exception as e:
            logger.warning(f"Failed to discover tools: {e}")
            self._available_tools = []
    def log_tool_performance(self, tool_name: str, metrics: Dict[str, Any]) -> None:
        """Log performance metrics for a tool"""
        self._tool_performance[tool_name] = metrics

    def register_summary_plugin(self, plugin_name: str, plugin_obj: Any) -> None:
        """Register a summary/transcription plugin"""
        self._summary_plugins[plugin_name] = plugin_obj

    def get_summary_plugin(self, plugin_name: str) -> Any:
        """Get a registered summary/transcription plugin"""
        return self._summary_plugins.get(plugin_name)
    
    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools"""
        if not self._initialized:
            raise RuntimeError("Tool registry not initialized")
        
        return self._available_tools.copy()
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool with given parameters"""
        if not self._initialized:
            raise RuntimeError("Tool registry not initialized")
        
        try:
            payload = {
                "tool": tool_name,
                "parameters": parameters
            }
            
            response = await self.mcp_client.post("/execute", json=payload)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to execute tool {tool_name}: {e}")
            raise
    
    async def get_tool_capabilities(self, tool_name: str) -> Dict[str, Any]:
        """Get capabilities and schema for a specific tool"""
        if not self._initialized:
            raise RuntimeError("Tool registry not initialized")
        
        try:
            response = await self.mcp_client.get(f"/tools/{tool_name}")
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to get capabilities for tool {tool_name}: {e}")
            raise


# Global tool registry instance
tool_registry = ToolRegistry()
