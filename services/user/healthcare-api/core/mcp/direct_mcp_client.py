"""
Direct MCP Client using JSON-RPC communication.

This implementation follows the handoff document's recommendation to spawn fresh
MCP subprocess for each call, avoiding the problematic mcp.client.stdio library.
"""
import asyncio
import json
import logging
import os
import subprocess
from typing import Any, Dict, List, Optional

from core.infrastructure.healthcare_logger import get_healthcare_logger

logger = get_healthcare_logger("infrastructure.mcp.direct")


class DirectMCPClient:
    """
    Direct MCP Client using JSON-RPC communication.
    
    Spawns the Node.js MCP server as a subprocess for each tool call,
    following MCP best practices from the handoff document.
    """

    def __init__(self) -> None:
        """Initialize direct MCP client with single-container parameters."""
        self.mcp_server_path = "/app/mcp-server/build/index.js"
        
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
            "Direct MCP client initialized",
            extra={
                "healthcare_context": {
                    "operation_type": "mcp_init",
                    "server_path": self.mcp_server_path,
                    "communication_method": "direct_jsonrpc",
                },
            },
        )

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call an MCP tool using fresh subprocess with direct JSON-RPC.
        
        This follows the handoff document pattern of spawning a fresh MCP
        subprocess for each call to avoid stdio communication issues.
        """
        logger.info(f"Calling MCP tool: {tool_name}", extra={
            "healthcare_context": {
                "operation_type": "mcp_tool_call",
                "tool_name": tool_name,
                "arguments": arguments,
            }
        })

        try:
            # Spawn fresh MCP server subprocess
            process = subprocess.Popen(
                ['node', self.mcp_server_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=self.mcp_env
            )

            # Wait for server to start
            await asyncio.sleep(1)

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

            logger.info(f"Sending tool request: {tool_name}")
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
            
            # Clean up process
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

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
                }
            })
            # Clean up on error
            if 'process' in locals():
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except Exception:
                    pass
            raise

    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available MCP tools using fresh subprocess."""
        logger.info("Listing available MCP tools")

        try:
            # Spawn fresh MCP server subprocess
            process = subprocess.Popen(
                ['node', self.mcp_server_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=self.mcp_env
            )

            # Wait for server to start
            await asyncio.sleep(1)

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
            await asyncio.wait_for(
                asyncio.to_thread(process.stdout.readline),
                timeout=10
            )

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
            
            # Clean up process
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

            if 'error' in result:
                logger.error(f"Failed to list tools: {result['error']}")
                return []

            tools = result.get('result', {}).get('tools', [])
            logger.info(f"Found {len(tools)} available MCP tools")
            return tools

        except Exception as e:
            logger.error(f"Failed to list MCP tools: {e}")
            # Clean up on error
            if 'process' in locals():
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except Exception:
                    pass
            return []

    async def connect(self) -> None:
        """No-op connect for compatibility."""
        logger.info("Direct MCP client ready (per-call sessions)")
