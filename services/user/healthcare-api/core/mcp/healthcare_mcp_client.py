"""
Healthcare MCP Client for stdio communication with healthcare-mcp server
Uses official MCP Python client library for reliable stdio communication
"""
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logging.warning("MCP library not available")

logger = logging.getLogger(__name__)

class HealthcareMCPClient:
    """MCP client for communicating with healthcare-mcp server via stdio using official MCP library"""
    
    def __init__(self, server_command: Optional[str] = None):
        """
        Initialize MCP client using official MCP Python library

        Connect to the existing healthcare-mcp container via stdio, NOT spawning a new server.
        """
        if not MCP_AVAILABLE:
            raise RuntimeError("MCP library not available")
            
        # Connect to existing healthcare-mcp container via stdio
        # Use docker exec to connect to the existing stdio server, not spawn a new one
        command = "docker"
        args = ["exec", "-i", "healthcare-mcp", "node", "/app/build/stdio_entry.js"]
        env = {"MCP_TRANSPORT": "stdio"}
        
        self.params = StdioServerParameters(command=command, args=args, env=env)
        self.client_cm: Optional[Any] = None
        self.session: Optional[ClientSession] = None
        self.tools: List[Dict[str, Any]] = []
        
    async def connect(self) -> None:
        """Connect to the MCP server using official MCP client"""
        try:
            logger.info("Connecting to MCP server with official MCP client")
            logger.info(f"Command: {self.params.command} {self.params.args}")
            
            # Create stdio client context manager - this returns read/write streams
            logger.info("Creating stdio client context manager...")
            self.client_cm = stdio_client(self.params)
            
            # Enter the context manager to get streams
            logger.info("Entering context manager to get streams...")
            read_stream, write_stream = await self.client_cm.__aenter__()
            logger.info("Successfully got read/write streams")
            
            # Create ClientSession with the streams
            logger.info("Creating ClientSession...")
            self.session = ClientSession(read_stream, write_stream)
            logger.info("ClientSession created successfully")
            
            # Initialize the session
            await self.session.initialize()
                
            await self._discover_tools()
            logger.info("MCP client connected successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            raise
    
    async def _discover_tools(self) -> None:
        """Discover tools using official MCP client session.list_tools()"""
        try:
            if not self.session:
                raise RuntimeError("Session not initialized")
                
            # Use ClientSession.list_tools() method
            tools_response = await self.session.list_tools()
            
            # Handle tools response - should have "tools" field with list
            if hasattr(tools_response, 'tools'):
                self.tools = tools_response.tools
            elif isinstance(tools_response, dict) and 'tools' in tools_response:
                self.tools = tools_response['tools']
            else:
                logger.warning(f"Unexpected tools response format: {type(tools_response)}")
                self.tools = []
                
            logger.info(f"Discovered {len(self.tools)} tools via MCP session.list_tools()")
            if self.tools:
                tool_names = [getattr(tool, 'name', str(tool)) for tool in self.tools]
                logger.info(f"Available tools: {tool_names}")
                
        except Exception as e:
            logger.error(f"Failed to discover tools: {e}")
            self.tools = []

    async def _ensure_connected(self) -> None:
        """Ensure MCP client is connected, connect if not already connected"""
        if not self.session:
            await self.connect()

    async def call_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Call a tool using official MCP client session.call_tool()"""
        await self._ensure_connected()
        
        if not self.session:
            raise RuntimeError("Session not initialized")
            
        args = arguments or {}
        
        try:
            # Use ClientSession.call_tool() method
            result = await self.session.call_tool(tool_name, args)
            return {"status": "success", "result": result}
                
        except Exception as e:
            logger.error(f"Failed to call tool {tool_name}: {e}")
            return {"status": "error", "error": str(e)}
    
    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools"""
        await self._ensure_connected()
        return self.tools
    
    async def disconnect(self) -> None:
        """Disconnect from MCP server using context manager cleanup"""
        try:
            if self.session:
                await self.session.close()
                logger.info("MCP session closed")
            if self.client_cm:
                await self.client_cm.__aexit__(None, None, None)
                logger.info("MCP client disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting from MCP server: {e}")
        finally:
            self.client_cm = None
            self.session = None
