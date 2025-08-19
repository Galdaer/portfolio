import httpx
import uvicorn
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Healthcare MCP Bridge", description="OpenAPI bridge for Healthcare MCP")

MCP_SERVER_URL = "http://172.20.0.12:3000"


@app.get("/health")
async def health():
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{MCP_SERVER_URL}/health")
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/openapi.json")
async def openapi():
    return {
        "openapi": "3.0.0",
        "info": {"title": "Healthcare MCP Bridge", "version": "1.0.0"},
        "paths": {
            "/health": {"get": {"summary": "Health check"}},
            "/tools": {"get": {"summary": "List available tools"}},
        },
    }


@app.get("/tools")
async def list_tools():
    # Return available MCP tools for Open WebUI
    return {
        "tools": [
            {"name": "healthcare_search", "description": "Search healthcare information"},
            {"name": "patient_lookup", "description": "Look up patient information"},
        ],
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
