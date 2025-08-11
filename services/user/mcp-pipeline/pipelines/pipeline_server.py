"""Healthcare MCP Pipeline Server
=============================

Hosts the MCP pipeline for Open WebUI integration.
Uses the pipeline.pipe() interface that Open WebUI expects.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Import our MCP pipeline with path fallback
try:
    from MCP_pipeline import Pipeline
except ImportError:
    # Add current directory to Python path and try again
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from MCP_pipeline import Pipeline

# Initialize pipeline instance
pipeline = Pipeline()

app = FastAPI(
    title="Healthcare MCP Pipeline",
    description="MCP pipeline for healthcare tools integration with Open WebUI",
    version="1.0.0",
)

# Enable permissive CORS for Open WebUI internal calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class InvokeRequest(BaseModel):
    arguments: Optional[Dict[str, Any]] = None


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "healthcare-mcp-pipeline"}


@app.get("/pipelines")
async def list_pipelines():
    """List available pipelines"""
    try:
        # Fallback for current simplified pipeline
        if hasattr(pipeline, 'pipelines'):
            return pipeline.pipelines()
        else:
            return [
                {"id": "mcp-healthcare", "name": "MCP Healthcare", "description": "Healthcare tools via MCP"},
                {"id": "mcp-general", "name": "MCP General", "description": "General purpose MCP tool access"},
            ]
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to list pipelines: {str(e)}"}
        )


@app.get("/models")
async def list_models():
    """Return a minimal OpenAI-style models list so Open WebUI detects this server"""
    try:
        models = [
            {"id": "mcp-healthcare", "name": "MCP Healthcare", "owned_by": "mcp"},
            {"id": "mcp-general", "name": "MCP General", "owned_by": "mcp"},
        ]
        # Fallback pipelines list
        pipelines_data = []
        if hasattr(pipeline, 'pipelines'):
            pipelines_data = pipeline.pipelines()
        else:
            pipelines_data = [
                {"id": "mcp-healthcare", "name": "MCP Healthcare", "description": "Healthcare tools via MCP"},
                {"id": "mcp-general", "name": "MCP General", "description": "General purpose MCP tool access"},
            ]
        return {"object": "list", "data": models, "pipelines": pipelines_data}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/tools")
async def list_tools():
    """List discovered MCP tools (dynamic)."""
    try:
        if hasattr(pipeline, 'list_tools'):
            return {"object": "list", "data": pipeline.list_tools()}
        else:
            return {"object": "list", "data": []}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/tools/{tool_id}")
async def get_tool(tool_id: str):
    """Return details for a single tool."""
    try:
        if hasattr(pipeline, 'list_tools'):
            tools = pipeline.list_tools()
            for t in tools:
                if t["id"] == tool_id:
                    return t
        return JSONResponse(status_code=404, content={"error": "Tool not found"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/tools/{tool_id}/invoke")
async def invoke_tool(tool_id: str, req: InvokeRequest):
    """Invoke a tool via MCP and return its result."""
    try:
        if hasattr(pipeline, 'invoke_tool'):
            arguments = req.arguments if req.arguments is not None else {}
            result = await pipeline.invoke_tool(tool_id, arguments)
            return {"object": "tool.invocation", "data": result}
        else:
            return JSONResponse(status_code=501, content={"error": "Tool invocation not available"})
    except ValueError as ve:
        return JSONResponse(status_code=404, content={"error": str(ve)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Invocation failed: {e}"})


@app.post("/v1/chat/completions")
async def chat_completions(request: dict):
    """Handle chat completions through MCP pipeline"""
    try:
        # Extract parameters from request
        messages = request.get("messages", [])
        model = request.get("model", "mcp-healthcare")

        if not messages:
            return JSONResponse(
                status_code=400,
                content={"error": "No messages provided"}
            )

        # Get the last user message with defensive parsing
        user_message = None
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, list):
                    user_message = " ".join(str(p) for p in content if p is not None)
                else:
                    user_message = str(content)
                if user_message.strip():
                    break
            elif isinstance(msg, str) and not user_message:
                user_message = msg.strip()

        if not user_message:
            return JSONResponse(
                status_code=400,
                content={"error": "No user message found"}
            )

        # Process through pipeline.pipe() - the Open WebUI interface
        response = await pipeline.pipe(
            user_message=user_message,
            model_id=model,
            messages=messages,
            body=request
        )

        # Format response for Open WebUI
        return {
            "id": "healthcare-mcp-response",
            "object": "chat.completion",
            "model": model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": str(response)
                },
                "finish_reason": "stop"
            }]
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Pipeline processing failed: {str(e)}"}
        )


# Add the same route without /v1 prefix for Open WebUI compatibility
app.add_api_route("/chat/completions", chat_completions, methods=["POST"])


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize pipeline on startup"""
    try:
        await pipeline.on_startup()
        print("✅ Healthcare MCP Pipeline initialized successfully")
    except Exception as e:
        print(f"❌ Pipeline initialization failed: {e}")
        raise


if __name__ == "__main__":  # pragma: no cover
    # Binding to 0.0.0.0 is intentional within container network (internal only)
    host = os.getenv("PIPELINES_HOST", "0.0.0.0")  # noqa: S104
    port = int(os.getenv("PIPELINES_PORT", "9099"))  # default as str for lint
    # Simple route listing for diagnostics at startup
    for r in app.router.routes:  # pragma: no cover debug logging only
        try:
            methods = getattr(r, 'methods', []) or []
            print(f"[ROUTE] {','.join(methods)} {getattr(r, 'path', '?')}")
        except Exception:  # noqa: BLE001
            pass

    uvicorn.run(app, host=host, port=port, log_level="info", access_log=False)
