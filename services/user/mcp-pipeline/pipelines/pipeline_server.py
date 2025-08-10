"""
Healthcare MCP Pipeline Server
Hosts the MCP pipeline for Open WebUI integration
"""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import sys

# Import our MCP pipeline
sys.path.append('/app/pipelines')
from MCP_pipeline import Pipeline

app = FastAPI(
    title="Healthcare MCP Pipeline",
    description="MCP pipeline for healthcare tools integration with Open WebUI",
    version="1.0.0"
)

# Enable permissive CORS for Open WebUI internal calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize pipeline
pipeline = Pipeline()

from pydantic import BaseModel
from typing import Any, Dict, List, Optional

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
        return pipeline.pipelines()
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
        return {"object": "list", "data": models, "pipelines": pipeline.pipelines()}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/tools")
async def list_tools():
    """List discovered MCP tools (dynamic)."""
    try:
        return {"object": "list", "data": pipeline.list_tools()}
    except Exception as e:  # pragma: no cover
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/tools/{tool_id}")
async def get_tool(tool_id: str):
    """Return details for a single tool."""
    tools = pipeline.list_tools()
    for t in tools:
        if t["id"] == tool_id:
            return t
    return JSONResponse(status_code=404, content={"error": "Tool not found"})

@app.post("/tools/{tool_id}/invoke")
async def invoke_tool(tool_id: str, req: InvokeRequest):
    """Invoke a tool via MCP and return its result."""
    try:
        result = await pipeline.invoke_tool(tool_id, req.arguments)
        return {"object": "tool.invocation", "data": result}
    except ValueError as ve:
        return JSONResponse(status_code=404, content={"error": str(ve)})
    except Exception as e:  # pragma: no cover
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
        
        # Get the last user message
        user_message = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
        
        if not user_message:
            return JSONResponse(
                status_code=400,
                content={"error": "No user message found"}
            )
        
        # Process through pipeline
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

if __name__ == "__main__":
    port = int(os.getenv("PIPELINES_PORT", 9099))
    host = os.getenv("PIPELINES_HOST", "0.0.0.0")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=False
    )
