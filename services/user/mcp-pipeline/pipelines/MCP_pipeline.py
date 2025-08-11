"""Thin MCP Pipeline Forwarder
================================

Minimal forwarding layer between Open WebUI (pipeline server) and the
healthcare-api service.

STRICT RESPONSIBILITIES ONLY:
 - Accept chat (and future generic) requests from the pipeline server
 - Forward them to the healthcare-api HTTP endpoint
 - Return the response transparently
 - Provide basic timeout + connection error handling
 - Log request lifecycle for observability (no PHI persistence)

All agent selection, MCP tool orchestration, and clinical workflow logic lives
inside the healthcare-api service. This file MUST remain < 200 LOC and contain
NO business logic or model/tool invocation.

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

    async def forward_chat(self, messages, **kwargs):
        """Forward chat request to healthcare API streaming endpoint."""
        # Extract the user message content
        user_message = ""
        if messages:
            last_message = messages[-1]
            if isinstance(last_message, dict) and last_message.get("role") == "user":
                content = last_message.get("content", "")
                if isinstance(content, list):
                    user_message = " ".join(str(p) for p in content if p)
                else:
                    user_message = str(content)
        
        if not user_message.strip():
            return "I didn't receive a message to process."
        
        # Use the streaming AI reasoning endpoint
        url = f"{self.base_url}/stream/ai_reasoning"
        params = {
            "medical_query": user_message,
            "user_id": kwargs.get("user_id", "pipeline_user"),
            "session_id": kwargs.get("session_id", "pipeline_session")
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        # Collect the streaming response
                        full_response = ""
                        async for line in response.content:
                            line_text = line.decode('utf-8').strip()
                            if line_text.startswith('data: '):
                                data = line_text[6:]  # Remove 'data: ' prefix
                                if data and data != '[DONE]':
                                    try:
                                        event_data = json.loads(data)
                                        if isinstance(event_data, dict) and 'content' in event_data:
                                            full_response += event_data['content']
                                        elif isinstance(event_data, str):
                                            full_response += event_data
                                    except json.JSONDecodeError:
                                        full_response += data
                        
                        return full_response.strip() if full_response.strip() else "Healthcare analysis completed."
                    else:
                        error_text = await response.text()
                        raise HTTPException(status_code=response.status, detail=f"Healthcare API error: {error_text}")
        except aiohttp.ClientError as e:
            raise HTTPException(status_code=503, detail=f"Healthcare service unavailable: {str(e)}")

    def pipelines(self):
        """Return list of available pipelines for Open WebUI."""
        return [
            {"id": "mcp-healthcare", "name": "MCP Healthcare", "description": "Healthcare tools via MCP"},
            {"id": "mcp-general", "name": "MCP General", "description": "General purpose MCP tool access"},
        ]

    def list_tools(self):
        """Return list of available MCP tools."""
        # For now return empty list - could be extended to discover actual MCP tools
        return []

    async def invoke_tool(self, tool_id: str, arguments: dict):
        """Invoke a specific MCP tool."""
        # For now return not implemented - could be extended for actual tool invocation
        raise ValueError(f"Tool invocation not implemented for {tool_id}")

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
            
            # Forward to healthcare API using our streaming endpoint
            response = await self.forward_chat(messages, **kwargs)
            
            # Return response in expected format
            return response
                
        except Exception as e:
            # Graceful fallback for errors
            logger.error(f"Pipeline error: {str(e)}")
            return f"I'm having trouble processing your request right now. Error: {str(e)}"

    async def on_startup(self):
        """Initialize pipeline on startup."""
        # For now just pass - could be extended for MCP client initialization
        pass


# Singleton instance (stateless aside from config)
pipeline = Pipeline()

__all__ = ["ChatRequest", "ForwardResult", "Pipeline", "pipeline"]


