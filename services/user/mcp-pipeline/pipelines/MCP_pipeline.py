"""Healthcare Pipeline for Open WebUI ↔ Healthcare API communication
================================================================

CORRECT ARCHITECTURE: Simple format converter between Open WebUI and healthcare-api

Flow: Open WebUI (HTTP) → Pipeline → Healthcare-API (JSON-RPC stdin/stdout) → Healthcare-MCP (MCP protocol)

RESPONSIBILITIES:
 - Convert Open WebUI requests to JSON-RPC format for healthcare-api
 - Handle stdio communication with healthcare-api container
 - Convert healthcare-api responses back to Open WebUI format
 - Basic timeout and error handling

MEDICAL DISCLAIMER: Administrative/documentation support only; not medical
advice, diagnosis, or treatment. All clinical decisions belong to licensed
professionals.
"""

from __future__ import annotations

import asyncio
import logging
import os

# Direct subprocess communication for healthcare-api stdio bridge
from typing import Any

import aiohttp
from pydantic import BaseModel, Field

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
    session_id: str | None = Field(None, description="Session identifier for continuity if provided")
    user_id: str | None = Field(None, description="End-user identifier (non-PHI opaque ID)")
    meta: dict[str, Any] = Field(default_factory=dict, description="Arbitrary metadata forwarded without interpretation")


class ForwardResult(BaseModel):
    """Standardized forwarder result wrapper."""
    status: str
    data: Any
    error: str | None = None
    latency_ms: int | None = None


# ---------------------------------------------------------------------------
# Healthcare API Client for direct stdio communication
# ---------------------------------------------------------------------------
class HealthcareAPIClient:
    """HTTP client for healthcare-api container communication"""

    def __init__(self):
        # Simple HTTP client for container-to-container communication
        self.base_url = "http://healthcare-api:8000"
        self.session = None

    async def connect(self):
        """Connect to the healthcare-api via HTTP"""
        try:
            logger.info("Connecting to healthcare-api via HTTP")

            # Simple HTTP session for container-to-container communication
            self.session = aiohttp.ClientSession()

            logger.info("Connected to healthcare-api via HTTP")

        except Exception as e:
            logger.error(f"Failed to connect to healthcare-api: {e}")
            raise

    async def ensure_connection(self):
        """Ensure we have a valid HTTP session"""
        if self.session is None or self.session.closed:
            logger.info("Session not available, reconnecting...")
            await self.connect()

    async def send_request(self, endpoint: str, data: dict[str, Any] = None) -> dict[str, Any]:
        """Send HTTP request to healthcare-api"""
        await self.ensure_connection()

        try:
            # Send HTTP POST request to healthcare-api
            async with self.session.post(f"{self.base_url}/{endpoint}", json=data or {}) as response:
                if response.status == 200:
                    result = await response.json()
                    return {"status": "success", "result": result}
                error_text = await response.text()
                return {"status": "error", "error": f"HTTP {response.status}: {error_text}"}

        except Exception as e:
            logger.error(f"Failed to send HTTP request to healthcare-api: {e}")
            return {"status": "error", "error": str(e)}

    async def process_chat(self, message: str, user_id: str = None, session_id: str = None) -> dict[str, Any]:
        """Process chat message via healthcare-api HTTP endpoint"""
        return await self.send_request("process", {
            "message": message,
            "user_id": user_id or "anonymous",
            "session_id": session_id or "default",
        })

    async def disconnect(self):
        """Disconnect from healthcare-api"""
        try:
            if self.session and not self.session.closed:
                await self.session.close()
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")
        finally:
            self.session = None


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
class Pipeline:
    """Direct stdio pipeline for healthcare-api communication"""

    def __init__(self) -> None:
        self.api_client = HealthcareAPIClient()
        timeout_raw = os.environ.get("PIPELINE_TIMEOUT_SECONDS", "30")
        try:
            self.timeout = float(timeout_raw)
        except ValueError:
            logger.warning("Invalid PIPELINE_TIMEOUT_SECONDS=%s; falling back to 30", timeout_raw)
            self.timeout = 30.0

    def pipelines(self):
        """Return list of available pipelines for Open WebUI."""
        return [
            {"id": "healthcare-assistant", "name": "Healthcare Assistant", "description": "Healthcare AI assistant via stdio MCP"},
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

            # Process via direct stdio
            result = await asyncio.wait_for(
                self.api_client.process_chat(final_message, user_id, session_id),
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
        logger.info("Healthcare pipeline starting - direct stdio communication with healthcare-api")
        # Don't connect during startup - use lazy connection when needed
        logger.info("Healthcare API Pipeline ready for stdio connections")


# Singleton instance
pipeline = Pipeline()

__all__ = ["ChatRequest", "ForwardResult", "Pipeline", "pipeline"]
