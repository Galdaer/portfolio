"""Healthcare Pipeline with MCP stdio communication
================================================

CORRECT ARCHITECTURE: The pipeline uses MCP stdio protocol to communicate with healthcare-api
which then communicates with healthcare-mcp via stdio.

Correct flow: Open WebUI → Pipeline (HTTP) → healthcare-api (stdio) → healthcare-mcp (stdio)

RESPONSIBILITIES:
 - Accept chat requests from Open WebUI pipeline server via HTTP
 - Forward them to healthcare-api via MCP stdio protocol
 - Return the response transparently
 - Provide basic timeout + connection error handling
 - Log request lifecycle for observability (no PHI persistence)

MEDICAL DISCLAIMER: Administrative/documentation support only; not medical
advice, diagnosis, or treatment. All clinical decisions belong to licensed
professionals.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from pydantic import BaseModel, Field

# MCP imports for stdio communication
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

logger = logging.getLogger("mcp_pipeline")
if not logger.handlers:  # Basic config only if root not configured
    raw_level = os.environ.get("LOG_LEVEL", "INFO")
    level = raw_level.upper()
    try:
        logging.basicConfig(
            level=level,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )
    except ValueError:
        # Fallback to INFO if invalid
        logging.basicConfig(
            level="INFO",
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )
        logger.warning("Invalid LOG_LEVEL '%s'; defaulted to INFO", raw_level)


# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    """Incoming chat request payload from Open WebUI pipeline."""

    message: str = Field(..., description="User message or prompt text")
    session_id: str | None = Field(
        None, description="Session identifier for continuity if provided"
    )
    user_id: str | None = Field(None, description="End-user identifier (non-PHI opaque ID)")
    meta: dict[str, Any] = Field(
        default_factory=dict, description="Arbitrary metadata forwarded without interpretation"
    )


class ForwardResult(BaseModel):
    """Standardized forwarder result wrapper."""

    status: str
    data: Any
    error: str | None = None
    latency_ms: int | None = None


# ---------------------------------------------------------------------------
# MCP Healthcare Client for stdio communication
# ---------------------------------------------------------------------------
class HealthcareMCPClient:
    """MCP client for stdio communication with healthcare-api container"""

    def __init__(self):
        if not MCP_AVAILABLE:
            raise RuntimeError("MCP library not available")

        # Connect to healthcare-api container via stdio
        command = "docker"
        args = ["exec", "-i", "healthcare-api", "python", "-m", "main", "--stdio"]
        env = {"MCP_TRANSPORT": "stdio"}

        self.params = StdioServerParameters(command=command, args=args, env=env)
        self.client_cm = None
        self.session = None

    async def connect(self):
        """Connect to the healthcare-api via stdio"""
        try:
            logger.info("Connecting to healthcare-api via stdio")

            # Create stdio client context manager
            self.client_cm = stdio_client(self.params)

            # Enter the context manager to get streams
            read_stream, write_stream = await self.client_cm.__aenter__()

            # Create ClientSession with the streams
            self.session = ClientSession(read_stream, write_stream)

            # Initialize the session
            await self.session.initialize()
            logger.info("Connected to healthcare-api via stdio")

        except Exception as e:
            logger.error(f"Failed to connect to healthcare-api: {e}")
            raise

    async def call_tool(self, tool_name: str, arguments: dict[str, Any] = None) -> dict[str, Any]:
        """Call a tool via MCP stdio"""
        if not self.session:
            await self.connect()

        args = arguments or {}

        try:
            result = await self.session.call_tool(tool_name, args)
            return {"status": "success", "result": result}
        except Exception as e:
            logger.error(f"Failed to call tool {tool_name}: {e}")
            return {"status": "error", "error": str(e)}

    async def process_chat(
        self, message: str, user_id: str = None, session_id: str = None
    ) -> dict[str, Any]:
        """Process chat message via healthcare-api"""
        try:
            # Use the clinical research agent's process_research_query method
            result = await self.call_tool(
                "process_research_query",
                {
                    "query": message,
                    "user_id": user_id or "anonymous",
                    "session_id": session_id or "default",
                },
            )
            return result
        except Exception as e:
            logger.error(f"Failed to process chat: {e}")
            return {"status": "error", "error": str(e)}

    async def disconnect(self):
        """Disconnect from healthcare-api"""
        try:
            if self.session:
                await self.session.close()
            if self.client_cm:
                await self.client_cm.__aexit__(None, None, None)
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")
        finally:
            self.client_cm = None
            self.session = None


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
class Pipeline:
    """MCP stdio pipeline for healthcare-api communication"""

    def __init__(self) -> None:
        if not MCP_AVAILABLE:
            logger.error("MCP library not available - cannot initialize pipeline")
            raise RuntimeError("MCP library required for stdio communication")

        self.mcp_client = HealthcareMCPClient()
        timeout_raw = os.environ.get("PIPELINE_TIMEOUT_SECONDS", "30")
        try:
            self.timeout = float(timeout_raw)
        except ValueError:
            logger.warning("Invalid PIPELINE_TIMEOUT_SECONDS=%s; falling back to 30", timeout_raw)
            self.timeout = 30.0

    def pipelines(self):
        """Return list of available pipelines for Open WebUI."""
        return [
            {
                "id": "healthcare-assistant",
                "name": "Healthcare Assistant",
                "description": "Healthcare AI assistant via stdio MCP",
            },
        ]

    async def pipe(self, user_message: str, model_id: str, messages: list, **kwargs):
        """Main pipe method for Open WebUI integration with MCP stdio."""
        try:
            # Handle different message formats defensively
            if isinstance(user_message, dict):
                message_text = user_message.get("content", "") or user_message.get("message", "")
            elif isinstance(user_message, list):
                message_text = " ".join(str(msg) for msg in user_message)
            else:
                message_text = str(user_message)

            # Create standardized message format
            if not messages:
                final_message = message_text
            else:
                # Get the last user message
                last_msg = messages[-1] if messages else {}
                if isinstance(last_msg, dict):
                    final_message = last_msg.get("content", message_text)
                else:
                    final_message = message_text

            if not final_message:
                return "I need a message to process."

            # Extract session info from kwargs
            user_id = kwargs.get("user_id") or kwargs.get("__user", {}).get("id")
            session_id = kwargs.get("session_id")

            # Process via MCP stdio
            result = await asyncio.wait_for(
                self.mcp_client.process_chat(final_message, user_id, session_id),
                timeout=self.timeout,
            )

            if result.get("status") == "error":
                error_msg = result.get("error", "Unknown error")
                logger.error(f"Pipeline error: {error_msg}")
                return f"I'm having trouble processing your request. Error: {error_msg}"

            # Extract the actual response from the result
            response_data = result.get("result", {})
            if isinstance(response_data, dict):
                # Look for common response fields
                response_text = (
                    response_data.get("response")
                    or response_data.get("research_summary")
                    or response_data.get("message")
                    or str(response_data)
                )
            else:
                response_text = str(response_data)

            return response_text

        except TimeoutError:
            logger.error("Pipeline timeout")
            return "I'm having trouble processing your request right now. The request timed out."
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            return f"I'm having trouble processing your request right now. Error: {str(e)}"

    async def on_startup(self):
        """Initialize pipeline on startup."""
        logger.info("Healthcare pipeline starting - MCP stdio communication with healthcare-api")
        try:
            await self.mcp_client.connect()
            logger.info("Successfully connected to healthcare-api via stdio")
        except Exception as e:
            logger.error(f"Failed to connect to healthcare-api on startup: {e}")


# Singleton instance
pipeline = Pipeline()

__all__ = ["ChatRequest", "ForwardResult", "Pipeline", "pipeline"]
