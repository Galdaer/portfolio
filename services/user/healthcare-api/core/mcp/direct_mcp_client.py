"""
Direct MCP Client using JSON-RPC communication.

This implementation follows the handoff document's recommendation to spawn fresh
MCP subprocess for each call, avoiding the problematic mcp.client.stdio library.
Fixed: Implements connection pooling and proper subprocess lifecycle management
to resolve broken pipe errors when called from LangChain agents.
"""
import asyncio
import json
import logging
import os
import subprocess
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

from core.infrastructure.healthcare_logger import get_healthcare_logger

logger = get_healthcare_logger("infrastructure.mcp.direct")


class DirectMCPClient:
    """
    Direct MCP Client using JSON-RPC communication.
    
    Uses connection pooling and proper subprocess lifecycle management
    to prevent broken pipe errors during LangChain agent execution.
    """

    def __init__(self) -> None:
        """Initialize direct MCP client with pooled connection management."""
        # Use container MCP server path - this is the production architecture
        self.mcp_server_path = "/app/mcp-server/build/stdio_entry.js"
        
        self._active_connections: Dict[str, subprocess.Popen] = {}
        self._connection_lock = asyncio.Lock()
        
        # Environment configuration for MCP server
        self.mcp_env = {
            "MCP_TRANSPORT": "stdio-only",
            "NO_COLOR": "1",
            "FHIR_BASE_URL": os.getenv("FHIR_BASE_URL", "https://hapi.fhir.org/baseR4"),
            "PUBMED_API_KEY": os.getenv("PUBMED_API_KEY", "optional_for_higher_rate_limits"),
            "CLINICALTRIALS_API_KEY": os.getenv("CLINICALTRIALS_API_KEY", "test"),
            "POSTGRES_HOST": os.getenv("POSTGRES_HOST", "postgresql"),
            "REDIS_HOST": os.getenv("REDIS_HOST", "redis"),
            "ENVIRONMENT": os.getenv("ENVIRONMENT", "development"),
            "LOG_LEVEL": os.getenv("LOG_LEVEL", "info"),
        }
        
        logger.info(
            "Direct MCP client initialized with connection pooling",
            extra={
                "healthcare_context": {
                    "operation_type": "mcp_init",
                    "server_path": self.mcp_server_path,
                    "communication_method": "pooled_jsonrpc",
                    "fix_applied": "broken_pipe_resolution",
                },
            },
        )

    @asynccontextmanager
    async def _get_mcp_connection(self, connection_id: str = "default"):
        """
        Async context manager for MCP connections with proper lifecycle management.
        
        Implements connection pooling to prevent rapid create/destroy cycles
        that cause broken pipe errors in LangChain agent execution.
        """
        async with self._connection_lock:
            # Reuse existing connection if available and healthy
            if connection_id in self._active_connections:
                process = self._active_connections[connection_id]
                if process.poll() is None:  # Process still running
                    logger.debug(f"Reusing existing MCP connection: {connection_id}")
                    yield process
                    return
                else:
                    # Clean up dead connection
                    del self._active_connections[connection_id]
                    logger.debug(f"Cleaned up dead MCP connection: {connection_id}")
            
            # Create new connection
            logger.debug(f"Creating new MCP connection: {connection_id}")
            
            # Build command based on server type
            if hasattr(self, 'mcp_server_args'):
                # Python-based server
                cmd = [self.mcp_server_path] + self.mcp_server_args
            else:
                # Node.js-based server
                cmd = ['node', self.mcp_server_path]
            
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=self.mcp_env
            )
            
            try:
                # Wait for server to start with shorter timeout for pooled connections
                await asyncio.sleep(0.5)
                
                # Initialize MCP session
                init_request = {
                    'jsonrpc': '2.0',
                    'id': 1,
                    'method': 'initialize',
                    'params': {
                        'protocolVersion': '2024-11-05',
                        'capabilities': {},
                        'clientInfo': {'name': 'healthcare-api', 'version': '1.0.0'}
                    }
                }

                process.stdin.write(json.dumps(init_request) + '\n')
                process.stdin.flush()
                
                # Read initialization response
                response_line = await asyncio.wait_for(
                    asyncio.to_thread(process.stdout.readline),
                    timeout=10
                )
                
                if not response_line:
                    raise RuntimeError("No response from MCP server during initialization")
                
                # Store active connection for reuse
                self._active_connections[connection_id] = process
                logger.debug(f"MCP connection established: {connection_id}")
                
                yield process
                
            except Exception as e:
                # Clean up on error
                logger.error(f"Failed to establish MCP connection {connection_id}: {e}")
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except Exception:
                    process.kill()
                    process.wait()
                raise

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call an MCP tool using pooled connection with proper lifecycle management.
        
        This implementation uses connection pooling to prevent broken pipe errors
        that occur during LangChain agent execution due to rapid subprocess cycling.
        """
        logger.info(f"Calling MCP tool: {tool_name}", extra={
            "healthcare_context": {
                "operation_type": "mcp_tool_call",
                "tool_name": tool_name,
                "arguments": arguments,
                "connection_strategy": "pooled",
            }
        })

        try:
            # Use connection pool with tool-specific connection ID
            connection_id = f"tool_{tool_name}"
            
            async with self._get_mcp_connection(connection_id) as process:
                # Call the tool
                tool_request = {
                    'jsonrpc': '2.0',
                    'id': 2,
                    'method': 'tools/call',
                    'params': {
                        'name': tool_name,
                        'arguments': arguments
                    }
                }

                logger.debug(f"Sending tool request: {tool_name}")
                process.stdin.write(json.dumps(tool_request) + '\n')
                process.stdin.flush()

                # Read tool response with longer timeout for medical searches
                response_line = await asyncio.wait_for(
                    asyncio.to_thread(process.stdout.readline),
                    timeout=30
                )

                if not response_line:
                    raise RuntimeError(f"No response from MCP server for tool: {tool_name}")

                # Parse response
                result = json.loads(response_line.strip())

                if 'error' in result:
                    logger.error(f"MCP tool error: {result['error']}")
                    raise RuntimeError(f"MCP tool error: {result['error']}")

                logger.info(f"MCP tool {tool_name} completed successfully")
                return result.get('result', {})

        except Exception as e:
            logger.error(f"Failed to call MCP tool {tool_name}: {e}", extra={
                "healthcare_context": {
                    "operation_type": "mcp_tool_error",
                    "tool_name": tool_name,
                    "error": str(e),
                    "fix_note": "pooled_connection_failed",
                }
            })
            raise

    async def cleanup_connections(self) -> None:
        """Clean up all active MCP connections."""
        async with self._connection_lock:
            for connection_id, process in list(self._active_connections.items()):
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                except Exception as e:
                    logger.warning(f"Error cleaning up connection {connection_id}: {e}")
                
            self._active_connections.clear()
            logger.info("All MCP connections cleaned up")

    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available MCP tools using pooled connection."""
        logger.info("Listing available MCP tools")

        try:
            async with self._get_mcp_connection("tools_list") as process:
                # List tools
                tools_request = {
                    'jsonrpc': '2.0',
                    'id': 2,
                    'method': 'tools/list',
                    'params': {}
                }

                process.stdin.write(json.dumps(tools_request) + '\n')
                process.stdin.flush()

                # Read tools response
                response_line = await asyncio.wait_for(
                    asyncio.to_thread(process.stdout.readline),
                    timeout=10
                )

                # Parse response
                result = json.loads(response_line.strip())

                if 'error' in result:
                    logger.error(f"Failed to list tools: {result['error']}")
                    return []

                tools = result.get('result', {}).get('tools', [])
                logger.info(f"Found {len(tools)} available MCP tools")
                return tools

        except Exception as e:
            logger.error(f"Failed to list MCP tools: {e}")
            return []

    async def connect(self) -> None:
        """Initialize connection pool - compatibility method."""
        logger.info("Direct MCP client ready with connection pooling")

    async def debug_connection(self) -> None:
        """Debug method to test MCP connection and fix validation."""
        logger.info("Testing MCP connection with new pooled implementation")
        try:
            # Test connection pool
            async with self._get_mcp_connection("debug") as process:
                if process.poll() is None:
                    logger.info("✅ MCP connection pool working correctly")
                    
            # Test actual tool call
            result = await self.call_tool('search-pubmed', {'query': 'test connection'})
            logger.info(f"✅ MCP tool test successful: {len(str(result))} chars response")
            
        except Exception as e:
            logger.error(f"❌ MCP connection test failed: {e}")
            raise
