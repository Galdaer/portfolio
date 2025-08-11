"""Healthcare Pipeline Forwarder
===============================

SIMPLIFIED ARCHITECTURE: The pipeline is a simple HTTP relay that forwards all requests
to the main healthcare-api service. It does NOT interact with MCP servers directly.

Correct flow: Open WebUI → Pipeline → Main API → Agents → MCP Client → MCP Server

STRICT RESPONSIBILITIES ONLY:
 - Accept chat requests from Open WebUI pipeline server
 - Forward them to the healthcare-api HTTP endpoint (/stream/ai_reasoning)
 - Return the response transparently
 - Provide basic timeout + connection error handling
 - Log request lifecycle for observability (no PHI persistence)

All agent selection, MCP tool orchestration, and clinical workflow logic lives
inside the healthcare-api service. This file MUST remain < 200 LOC and contain
NO business logic, MCP imports, or tool invocation.

MEDICAL DISCLAIMER: Administrative/documentation support only; not medical
advice, diagnosis, or treatment. All clinical decisions belong to licensed
professionals.
"""

from __future__ import annotations

import json
import logging
import os
import time
import aiohttp
from typing import Any, List
from fastapi import HTTPException

import httpx
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
# Pydantic request / response models (intentionally minimal)
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    """Incoming chat request payload from Open WebUI pipeline.

    Fields are intentionally generic; the healthcare-api owns semantic meaning.
    Additional metadata passes through transparently via the `meta` dict.
    """

    message: str = Field(..., description="User message or prompt text")
    session_id: str | None = Field(
        None, description="Session identifier for continuity if provided",
    )
    user_id: str | None = Field(
        None, description="End-user identifier (non-PHI opaque ID)",
    )
    meta: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary metadata forwarded without interpretation",
    )


class ForwardResult(BaseModel):
    """Standardized forwarder result wrapper.

    The `data` field contains the raw JSON payload returned by healthcare-api.
    """

    status: str
    data: Any
    error: str | None = None
    latency_ms: int | None = None


# ---------------------------------------------------------------------------
# Pipeline Forwarder
# ---------------------------------------------------------------------------
class Pipeline:
    """Thin forwarding pipeline.

    Environment Variables:
      - HEALTHCARE_API_URL: Base URL of healthcare-api (default: http://healthcare-api:8000)
      - PIPELINE_TIMEOUT_SECONDS: Request timeout (default: 30)
    """

    def __init__(self) -> None:
        self.base_url = os.environ.get(
            "HEALTHCARE_API_URL", "http://healthcare-api:8000",
        ).rstrip("/")
        timeout_raw = os.environ.get("PIPELINE_TIMEOUT_SECONDS", "30")
        try:
            self.timeout = float(timeout_raw)
        except ValueError:
            logger.warning(
                "Invalid PIPELINE_TIMEOUT_SECONDS=%s; falling back to 30", timeout_raw,
            )
            self.timeout = 30.0

    def pipelines(self):
        """Return list of available pipelines for Open WebUI."""
        return [
            {"id": "healthcare-assistant", "name": "Healthcare Assistant", "description": "Healthcare AI assistant via main API"},
        ]

    async def pipe(self, user_message: str, model_id: str, messages: list, **kwargs):
        """Main pipe method for Open WebUI integration."""
        try:
            # Handle different message formats defensively
            if isinstance(user_message, dict):
                content = user_message.get("content", str(user_message))
            elif isinstance(user_message, list):
                content = " ".join(str(msg) for msg in user_message)
            else:
                content = str(user_message)
            
            # Create standardized message format
            if not messages:
                messages = [{"role": "user", "content": content}]
            
            # Use the new generic /process endpoint that routes to appropriate agents
            url = f"{self.base_url}/process"
            payload = {
                "message": content,
                "messages": messages,
                "user_id": kwargs.get("user_id", "pipeline_user"),
                "session_id": kwargs.get("session_id", "pipeline_session"),
                "model_id": model_id,
                "meta": kwargs
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=self.timeout) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("status") == "success":
                            return str(result.get("data", "Processing completed."))
                        else:
                            return f"Error: {result.get('message', 'Unknown error')}"
                    else:
                        error_text = await response.text()
                        raise HTTPException(status_code=response.status, detail=f"Healthcare API error: {error_text}")
                        
        except Exception as e:
            # Graceful fallback for errors
            logger.error(f"Pipeline error: {str(e)}")
            return f"I'm having trouble processing your request right now. Error: {str(e)}"

    async def on_startup(self):
        """Initialize pipeline on startup."""
        logger.info("Healthcare pipeline starting - simple HTTP forwarder to main API")
        pass


# Singleton instance (stateless aside from config)
pipeline = Pipeline()

__all__ = ["ChatRequest", "ForwardResult", "Pipeline", "pipeline"]


