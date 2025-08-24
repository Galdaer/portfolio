#!/usr/bin/env python3
"""
Simple MCP test script to isolate the communication issue
"""

import asyncio
import json
import logging
import subprocess
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_mcp_direct():
    """Test MCP communication with a minimal setup"""

    # MCP server path
    mcp_server = "/home/intelluxe/services/user/healthcare-mcp/build/index.js"

    # Check if server exists
    if not Path(mcp_server).exists():
        logger.error(f"MCP server not found at {mcp_server}")
        return

    # Environment for MCP server
    env = {
        "MCP_TRANSPORT": "stdio-only",
        "NO_COLOR": "1",
        "FHIR_BASE_URL": "https://hapi.fhir.org/baseR4",
        "PUBMED_API_KEY": "optional_for_higher_rate_limits",
        "CLINICALTRIALS_API_KEY": "test",
        "POSTGRES_HOST": "postgresql",
        "REDIS_HOST": "redis",
        "ENVIRONMENT": "development",
        "LOG_LEVEL": "info",
    }

    try:
        # Start subprocess
        logger.info("Starting MCP server subprocess...")
        process = subprocess.Popen(
            ["node", mcp_server],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )

        # Wait a moment for startup
        await asyncio.sleep(2)

        if process.poll() is not None:
            stderr = process.stderr.read() if process.stderr else "No stderr"
            logger.error(f"MCP server exited early with code {process.poll()}: {stderr}")
            return

        logger.info("MCP server started, attempting simple JSON-RPC call...")

        # Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        }

        # Send request
        request_str = json.dumps(init_request) + "\n"
        logger.info(f"Sending: {request_str.strip()}")

        process.stdin.write(request_str)
        process.stdin.flush()

        # Try to read response
        logger.info("Waiting for response...")
        try:
            response = await asyncio.wait_for(
                asyncio.create_task(asyncio.to_thread(process.stdout.readline)), timeout=10,
            )
            logger.info(f"Response: {response.strip()}")
        except TimeoutError:
            logger.exception("Timeout waiting for response")

        # Clean up
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()

    except Exception as e:
        logger.exception(f"Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_mcp_direct())
