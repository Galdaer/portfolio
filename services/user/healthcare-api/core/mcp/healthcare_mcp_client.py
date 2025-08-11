"""
Healthcare MCP Client for stdio communication with healthcare-mcp server
"""
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
import subprocess
import os

logger = logging.getLogger(__name__)

class HealthcareMCPClient:
    """MCP client for communicating with healthcare-mcp server via stdio"""
    
    def __init__(self, server_command: Optional[str] = None):
        """
        Initialize MCP client
        
        Args:
            server_command: Command to start MCP server (default: docker exec healthcare-mcp node /app/build/index.js)
        """
        self.server_command = server_command or ["docker", "exec", "-i", "healthcare-mcp", "node", "/app/build/index.js"]
        self.process: Optional[subprocess.Popen] = None
        self.tools: List[Dict[str, Any]] = []
        self._request_id = 0
        
    async def connect(self) -> None:
        """Connect to the MCP server"""
        try:
            logger.info(f"Starting MCP server process: {' '.join(self.server_command)}")
            self.process = subprocess.Popen(
                self.server_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0
            )
            
            # Initialize MCP connection
            await self._initialize_connection()
            logger.info("MCP client connected successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            raise
    
    async def _initialize_connection(self) -> None:
        """Initialize MCP protocol connection and discover tools"""
        try:
            # Send initialize request
            init_request = {
                "jsonrpc": "2.0",
                "id": self._get_request_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "clientInfo": {
                        "name": "healthcare-api",
                        "version": "1.0.0"
                    }
                }
            }
            
            await self._send_request(init_request)
            
            # List available tools
            await self._discover_tools()
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP connection: {e}")
            raise
    
    async def _discover_tools(self) -> None:
        """Discover available tools from MCP server"""
        try:
            tools_request = {
                "jsonrpc": "2.0",
                "id": self._get_request_id(),
                "method": "tools/list"
            }
            
            response = await self._send_request(tools_request)
            if response and "result" in response and "tools" in response["result"]:
                self.tools = response["result"]["tools"]
                logger.info(f"Discovered {len(self.tools)} MCP tools: {[tool.get('name', 'unknown') for tool in self.tools]}")
            else:
                logger.warning("No tools discovered from MCP server")
                
        except Exception as e:
            logger.error(f"Failed to discover tools: {e}")
            self.tools = []
    
    async def _send_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send request to MCP server and get response"""
        if not self.process or not self.process.stdin:
            raise RuntimeError("MCP server process not available")
        
        try:
            # Send request
            request_line = json.dumps(request) + "\n"
            self.process.stdin.write(request_line)
            self.process.stdin.flush()
            
            # Read response
            response_line = self.process.stdout.readline()
            if response_line:
                return json.loads(response_line.strip())
            
        except Exception as e:
            logger.error(f"Failed to send MCP request: {e}")
            return None
    
    def _get_request_id(self) -> int:
        """Get next request ID"""
        self._request_id += 1
        return self._request_id
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        try:
            request = {
                "jsonrpc": "2.0",
                "id": self._get_request_id(),
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            response = await self._send_request(request)
            if response and "result" in response:
                return response["result"]
            else:
                logger.error(f"Failed to call tool {tool_name}: {response}")
                return {"error": f"Tool call failed: {response}"}
                
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return {"error": f"Tool call error: {str(e)}"}
    
    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools"""
        return self.tools
    
    async def disconnect(self) -> None:
        """Disconnect from MCP server"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            except Exception as e:
                logger.error(f"Error disconnecting from MCP server: {e}")
            finally:
                self.process = None
                
    def __del__(self):
        """Cleanup on destruction"""
        if hasattr(self, 'process') and self.process:
            try:
                self.process.terminate()
            except Exception as e:
                logger.error(f"Error terminating MCP process in __del__: {e}")
                pass
