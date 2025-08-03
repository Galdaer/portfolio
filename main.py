#!/usr/bin/env python3
"""
Intelluxe AI - Healthcare AI System Entry Point

Privacy-First Healthcare AI System built for on-premise clinical deployment.
Focus: Administrative/documentation support, NOT medical advice.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from config.app import config

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("logs/intelluxe-ai.log")],
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle management"""
    logger.info(f"Starting {config.project_name}")

    # Initialize core services
    try:
        # Initialize healthcare services (MCP, LLM, Database, Redis)
        from core.dependencies import healthcare_services
        await healthcare_services.initialize()

        # Initialize memory manager
        from core.memory import MemoryManager

        app.state.memory_manager = MemoryManager()
        await app.state.memory_manager.initialize()

        # Initialize model registry
        from core.models import ModelRegistry

        app.state.model_registry = ModelRegistry()
        await app.state.model_registry.initialize()

        # Initialize tool registry
        from core.tools import ToolRegistry

        app.state.tool_registry = ToolRegistry()
        await app.state.tool_registry.initialize()

        logger.info("Core services initialized successfully")
        yield

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise
    finally:
        logger.info(f"Shutting down {config.project_name}")

        # Cleanup resources
        if hasattr(app.state, "memory_manager"):
            await app.state.memory_manager.close()

        # Cleanup healthcare services
        from core.dependencies import healthcare_services
        await healthcare_services.close()


app = FastAPI(
    title="Intelluxe AI - Healthcare Administrative Assistant",
    description="Privacy-First Healthcare AI System for administrative support",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)  # type: ignore[misc]
async def root() -> str:
    """Health check and system status"""
    return """
    <html>
        <head><title>Intelluxe AI - Healthcare Assistant</title></head>
        <body>
            <h1>Intelluxe AI Healthcare Administrative Assistant</h1>
            <p>Privacy-First Healthcare AI System</p>
            <p>Status: <strong>Running</strong></p>
            <p><a href="/docs">API Documentation</a></p>
            <p><a href="/health">Health Check</a></p>
        </body>
    </html>
    """


@app.get("/health")  # type: ignore[misc]
async def health_check() -> dict[str, Any]:
    """Detailed health check endpoint"""
    try:
        from core.infrastructure.health_monitoring import healthcare_monitor
        return await healthcare_monitor.comprehensive_health_check()

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


@app.get("/health/quick")  # type: ignore[misc]
async def quick_health_check() -> dict[str, Any]:
    """Quick health check endpoint (cached results)"""
    try:
        from core.infrastructure.health_monitoring import healthcare_monitor
        return await healthcare_monitor.quick_health_check()

    except Exception as e:
        logger.error(f"Quick health check failed: {e}")
        raise HTTPException(status_code=500, detail="Quick health check failed")


# Import and include agent routers
try:
    from agents.document_processor import router as document_router
    from agents.intake import router as intake_router
    from agents.research_assistant import router as research_router

    app.include_router(intake_router, prefix="/agents/intake", tags=["intake"])
    app.include_router(document_router, prefix="/agents/document", tags=["document"])
    app.include_router(research_router, prefix="/agents/research", tags=["research"])

    logger.info("Agent routers loaded successfully")
except ImportError as e:
    logger.warning(f"Agent routers not available: {e}")


if __name__ == "__main__":
    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)

    # Run the application
    uvicorn.run(
        "main:app",
        host=config.host,
        port=config.port,
        reload=config.development_mode,
        log_level=config.log_level.lower(),
    )
