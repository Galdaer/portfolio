#!/usr/bin/env python3
"""
Healthcare MCP Authentication Proxy - Direct MCP Integration

This FastAPI server provides direct communication with the Healthcare MCP server
without relying on mcpo, ensuring all 15 tools are available.

Architecture:
- Open WebUI → FastAPI Auth Proxy (port 3001) → Healthcare MCP Server (direct MCP protocol)

Medical Disclaimer:
This tool is for administrative and documentation support only. It does not provide
medical advice, diagnosis, or treatment recommendations. All medical decisions should
be made by qualified healthcare professionals.
"""

import asyncio
import fcntl
import json
import logging
import os
import select
import subprocess
from typing import Any

import uvicorn
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Authentication setup
security = HTTPBearer()

# Expected API key (matches what's in start_services.sh)
EXPECTED_API_KEY = "healthcare-mcp-2025"

# Direct MCP communication setup
mcp_process: subprocess.Popen | None = None
healthcare_tools: list[dict[str, Any]] = []
request_id_counter = 1


class ToolRequest(BaseModel):
    """Request model for tool execution"""

    arguments: dict[str, Any] = {}


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    message: str
    tools_available: int


async def authenticate(credentials: HTTPAuthorizationCredentials = Depends(security)) -> bool:
    """Authenticate API requests"""
    if credentials.credentials != EXPECTED_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return True


async def start_mcp_server():
    """Start the Healthcare MCP server process"""
    global mcp_process, healthcare_tools, request_id_counter

    try:
        # Start Healthcare MCP server as subprocess
        mcp_process = subprocess.Popen(
            ["node", "/app/build/index.js"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0,
        )

        logger.info("Healthcare MCP server process started")

        # Give the server time to start up
        await asyncio.sleep(2)

        # Check if the process is still running
        if mcp_process.poll() is not None:
            stderr_output = mcp_process.stderr.read() if mcp_process.stderr else "No stderr"
            logger.error(f"MCP server process exited early. Stderr: {stderr_output}")
            return False

        # Check what the server outputs on startup
        try:
            # Try to read any initial output without sending requests first

            # Set non-blocking mode for both stdout and stderr
            for stream in [mcp_process.stdout, mcp_process.stderr]:
                if stream:
                    fd = stream.fileno()
                    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
                    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

            # Check for any startup output
            ready_out, _, _ = select.select([mcp_process.stdout], [], [], 1.0)
            ready_err, _, _ = select.select([mcp_process.stderr], [], [], 1.0)

            if ready_out:
                try:
                    initial_output = mcp_process.stdout.read()
                    if initial_output:
                        logger.info(f"MCP server initial stdout: {initial_output}")
                except (OSError, ValueError) as e:
                    logger.debug(f"Error reading stdout: {e}")

            if ready_err:
                try:
                    stderr_output = mcp_process.stderr.read()
                    if stderr_output:
                        logger.info(f"MCP server initial stderr: {stderr_output}")
                except (OSError, ValueError) as e:
                    logger.debug(f"Error reading stderr: {e}")

        except Exception as e:
            logger.warning(f"Error reading initial MCP output: {e}")

        # Initialize MCP protocol
        init_request = {
            "jsonrpc": "2.0",
            "id": request_id_counter,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "healthcare-auth-proxy", "version": "1.0.0"},
            },
        }
        request_id_counter += 1

        # Send initialization request
        if mcp_process.stdin is None:
            logger.error("MCP process stdin is None")
            return False

        mcp_process.stdin.write(json.dumps(init_request) + "\n")
        mcp_process.stdin.flush()

        # Give the server a moment to initialize
        await asyncio.sleep(1)

        # Check if server started successfully by looking at stderr for startup messages
        # MCP servers often output startup info to stderr
        stderr_available = mcp_process.stderr.readable()
        if stderr_available:
            # Try to read any startup messages
            try:
                # Set non-blocking mode for stderr
                import fcntl
                import os

                fd = mcp_process.stderr.fileno()
                fl = fcntl.fcntl(fd, fcntl.F_GETFL)
                fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

                stderr_output = mcp_process.stderr.read()
                if stderr_output:
                    logger.info(f"MCP server startup output: {stderr_output.strip()}")
            except (OSError, BlockingIOError, ValueError) as e:
                logger.debug(f"Non-blocking read failed: {e}")  # Non-blocking read failed, continue

        # Try to read initialization response with timeout
        try:
            # Use select to wait for output with timeout
            import select

            ready, _, _ = select.select([mcp_process.stdout], [], [], 2.0)  # 2 second timeout

            if ready:
                if mcp_process.stdout is None:
                    logger.warning("MCP process stdout is None")
                    return False

                raw_response = mcp_process.stdout.readline()
                response_line = raw_response.strip() if raw_response else ""
                if response_line:
                    json.loads(response_line)
                    logger.info("MCP initialization successful")
                else:
                    logger.warning("MCP server returned empty response to initialization")
            else:
                logger.warning("MCP server did not respond to initialization within timeout")
        except json.JSONDecodeError as e:
            logger.warning(f"MCP server returned invalid JSON: {e}")
        except Exception as e:
            logger.warning(f"Error reading MCP initialization response: {e}")

        # Send tools/list request to get available tools
        tools_request = {
            "jsonrpc": "2.0",
            "id": request_id_counter,
            "method": "tools/list",
            "params": {},
        }
        request_id_counter += 1

        if mcp_process.stdin is None:
            logger.error("MCP process stdin is None for tools request")
            return False

        mcp_process.stdin.write(json.dumps(tools_request) + "\n")
        mcp_process.stdin.flush()

        # Try to read tools response with timeout
        try:
            if mcp_process.stdout is None:
                logger.error("MCP process stdout is None for tools response")
                return False

            ready, _, _ = select.select([mcp_process.stdout], [], [], 2.0)  # 2 second timeout

            if ready:
                if mcp_process.stdout is None:
                    logger.warning("MCP process stdout became None")
                    return False

                raw_tools_response = mcp_process.stdout.readline()
                tools_response_line = raw_tools_response.strip() if raw_tools_response else ""
                if tools_response_line:
                    tools_response = json.loads(tools_response_line)
                    if "result" in tools_response and "tools" in tools_response["result"]:
                        healthcare_tools = tools_response["result"]["tools"]
                        logger.info(
                            f"Successfully retrieved {len(healthcare_tools)} healthcare tools"
                        )
                        for tool in healthcare_tools:
                            logger.info(f"Available tool: {tool.get('name', 'Unknown')}")
                        return True
                    else:
                        logger.warning(f"Unexpected tools response format: {tools_response}")
                else:
                    logger.warning("MCP server returned empty response to tools/list")
            else:
                logger.warning("MCP server did not respond to tools/list within timeout")
        except json.JSONDecodeError as e:
            logger.warning(f"MCP server returned invalid JSON for tools/list: {e}")
        except Exception as e:
            logger.warning(f"Error reading MCP tools response: {e}")

        # No fallback - if MCP communication failed, we should not expose any tools
        logger.error("MCP tool discovery failed - no tools will be available")
        healthcare_tools = []
        return False

        return False

    except Exception as e:
        logger.error(f"Failed to start MCP server: {e}")
        return False


async def call_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Call a tool via direct MCP communication"""
    global mcp_process, request_id_counter

    if not mcp_process or mcp_process.poll() is not None:
        raise HTTPException(status_code=503, detail="Healthcare MCP server unavailable")

    try:
        # Prepare MCP tool call request
        tool_request = {
            "jsonrpc": "2.0",
            "id": request_id_counter,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        request_id_counter += 1

        # Send request to MCP server
        if mcp_process.stdin is None:
            raise HTTPException(status_code=503, detail="MCP server stdin unavailable")

        mcp_process.stdin.write(json.dumps(tool_request) + "\n")
        mcp_process.stdin.flush()

        # Read response with timeout
        if mcp_process.stdout is None:
            raise HTTPException(status_code=503, detail="MCP server stdout unavailable")

        ready, _, _ = select.select([mcp_process.stdout], [], [], 10.0)  # 10 second timeout

        if ready:
            raw_response = mcp_process.stdout.readline()
            response_line = raw_response.strip() if raw_response else ""
            if response_line:
                response = json.loads(response_line)
                if "result" in response:
                    return response["result"]
                elif "error" in response:
                    raise HTTPException(
                        status_code=400, detail=f"MCP tool error: {response['error']}"
                    )
                else:
                    raise HTTPException(status_code=500, detail="Unexpected MCP response format")
            else:
                raise HTTPException(status_code=500, detail="No response from MCP server")
        else:
            raise HTTPException(status_code=504, detail="MCP server timeout")

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in MCP communication: {e}")
        raise HTTPException(status_code=500, detail="Invalid MCP response format")
    except Exception as e:
        logger.error(f"Error calling MCP tool {tool_name}: {e}")
        raise HTTPException(status_code=500, detail=f"MCP tool execution failed: {str(e)}")


# Create FastAPI app
app = FastAPI(
    title="Healthcare MCP Tools",
    description="Authentication proxy for Healthcare MCP server tools. Medical Disclaimer: This service provides administrative support only, not medical advice.",
    version="1.0.0",
)

# CORS configuration for Open WebUI integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Open WebUI integration
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize the authentication proxy"""
    logger.info("Starting Healthcare MCP Authentication Proxy (Direct MCP)")
    logger.info(
        "Medical Disclaimer: This service provides administrative support only, not medical advice"
    )

    # Start MCP server
    success = await start_mcp_server()
    if success:
        logger.info(f"Successfully registered {len(healthcare_tools)} healthcare tools")

        # Dynamically create endpoints for each tool
        for tool in healthcare_tools:
            tool_name = tool.get("name")
            if not tool_name:
                continue

            def create_tool_handler(name: str):
                async def tool_handler(
                    request: ToolRequest, authenticated: bool = Depends(authenticate)
                ):
                    """Handle tool execution"""
                    try:
                        logger.info(f"Executing healthcare tool: {name}")
                        result = await call_mcp_tool(name, request.arguments)
                        return {
                            "success": True,
                            "result": result,
                            "tool": name,
                            "disclaimer": "Medical Disclaimer: This service provides administrative support only, not medical advice",
                        }
                    except HTTPException:
                        raise
                    except Exception as e:
                        logger.error(f"Unexpected error in tool {name}: {e}")
                        raise HTTPException(status_code=500, detail="Internal server error")

                return tool_handler

            # Add the endpoint to the app
            handler = create_tool_handler(tool_name)
            app.post(f"/tools/{tool_name}")(handler)

            logger.info(f"Registered healthcare tool endpoint: /tools/{tool_name}")
    else:
        logger.error("Failed to start Healthcare MCP server")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global mcp_process
    if mcp_process:
        mcp_process.terminate()
        mcp_process.wait()
        logger.info("Healthcare MCP server terminated")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    global mcp_process

    is_healthy = mcp_process and mcp_process.poll() is None

    return HealthResponse(
        status="healthy" if is_healthy else "unhealthy",
        message="Healthcare MCP Authentication Proxy operational"
        if is_healthy
        else "MCP server unavailable",
        tools_available=len(healthcare_tools),
    )


@app.get("/tools")
async def list_tools(authenticated: bool = Depends(authenticate)):
    """List all available healthcare tools"""
    return {
        "tools": healthcare_tools,
        "count": len(healthcare_tools),
        "disclaimer": "Medical Disclaimer: This service provides administrative support only, not medical advice",
    }


if __name__ == "__main__":
    logger.info("Starting Healthcare MCP Authentication Proxy on port 3001")
    logger.info(
        "Medical Disclaimer: This service provides administrative support only, not medical advice"
    )

    uvicorn.run(app, host="0.0.0.0", port=3001, log_level="info")
