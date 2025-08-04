#!/usr/bin/env python3
"""
Intelluxe AI - Healthcare AI System Entry Point

Privacy-First Healthcare AI System built for on-premise clinical deployment.
Focus: Administrative/documentation support, NOT medical advice.

MEDICAL DISCLAIMER: This system provides administrative and documentation support only.
It does not provide medical advice, diagnosis, or treatment recommendations.
All medical decisions should be made by qualified healthcare professionals.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse, StreamingResponse

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
    description="""
    ## Privacy-First Healthcare AI System

    **Administrative and documentation support for healthcare professionals**

    ### 🏥 MEDICAL DISCLAIMER
    **This system provides administrative and documentation support only.**
    - ❌ Does NOT provide medical advice, diagnosis, or treatment recommendations
    - ❌ Does NOT replace qualified healthcare professional judgment
    - ✅ Assists with documentation, scheduling, and administrative tasks
    - ✅ All PHI/PII remains on-premise with no cloud dependencies

    ### 🔒 HIPAA Compliance
    - **Privacy-First Architecture**: All patient data remains on-premise
    - **Audit Logging**: Complete audit trail for all healthcare access
    - **Role-Based Access**: Secure authentication with healthcare role permissions
    - **PHI Protection**: Runtime PHI detection and data leakage monitoring

    ### 🤖 Available Healthcare Agents
    - **Intake Agent**: Patient registration, appointment scheduling, insurance verification
    - **Document Processor**: Medical document analysis and clinical note generation
    - **Research Assistant**: Medical literature search and clinical research support

    ### 📋 Authentication Required
    Most endpoints require JWT authentication with appropriate healthcare role permissions.
    Contact your system administrator for access credentials.

    ### ⚕️ Healthcare Compliance
    Built for on-premise deployment in clinical environments with comprehensive
    HIPAA compliance, audit logging, and patient data protection.
    """,
    version="1.0.0",
    lifespan=lifespan,
    terms_of_service="For healthcare administrative use only. No medical advice provided.",
    contact={
        "name": "Intelluxe AI Healthcare Support",
        "email": "support@intelluxe.ai",
    },
    license_info={
        "name": "Healthcare Administrative License",
        "identifier": "Healthcare-Admin-Only",
    },
)

# Configure CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
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


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, Any]:
    """
    Comprehensive Healthcare System Health Check

    Returns detailed health status for all healthcare system components:
    - Database connectivity (PostgreSQL)
    - Cache system (Redis)
    - MCP server connectivity
    - LLM availability
    - Background task processing
    - Memory usage and performance metrics

    **Use Case**: System monitoring, deployment validation, troubleshooting
    """
    try:
        from core.infrastructure.health_monitoring import healthcare_monitor

        return await healthcare_monitor.comprehensive_health_check()

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


@app.get("/health/quick", tags=["health"])
async def quick_health_check() -> dict[str, Any]:
    """
    Quick Healthcare System Status Check

    Returns cached health status for rapid monitoring:
    - Overall system status
    - Critical component availability
    - Cached performance metrics

    **Use Case**: Load balancer health checks, rapid status monitoring
    **Response Time**: < 100ms (cached results)
    """
    try:
        from core.infrastructure.health_monitoring import healthcare_monitor

        return await healthcare_monitor.quick_health_check()

    except Exception as e:
        logger.error(f"Quick health check failed: {e}")
        raise HTTPException(status_code=500, detail="Quick health check failed")


# Custom OpenAPI schema with healthcare compliance information
def custom_openapi() -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add healthcare-specific security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Healthcare JWT token with role-based permissions",
        }
    }

    # Add healthcare compliance tags
    openapi_schema["tags"] = [
        {"name": "health", "description": "System health monitoring and status endpoints"},
        {
            "name": "intake",
            "description": "Patient intake, registration, and appointment scheduling",
        },
        {
            "name": "document",
            "description": "Medical document processing and clinical note generation",
        },
        {
            "name": "research",
            "description": "Medical literature search and clinical research support",
        },
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi  # type: ignore[method-assign]


# Streaming endpoints for enhanced user experience
@app.get("/stream/literature_search", tags=["streaming"])
async def stream_literature_search(
    query: str, max_results: int = 10, user_id: str = "demo_user", session_id: str = "demo_session"
) -> StreamingResponse:
    """
    Stream Medical Literature Search Results

    **Real-time streaming** of medical literature search progress and results.

    **Stream Events:**
    - Progress updates during database search
    - Individual paper results as they arrive
    - Citation formatting and relevance scoring
    - Final completion with summary statistics

    **Use Case:** Improve user experience during long literature searches
    **Response Format:** Server-Sent Events (SSE)
    """
    from core.infrastructure.streaming import stream_medical_literature_search

    return await stream_medical_literature_search(query, user_id, session_id, max_results)


@app.get("/stream/ai_reasoning", tags=["streaming"])
async def stream_ai_reasoning(
    medical_query: str, user_id: str = "demo_user", session_id: str = "demo_session"
) -> StreamingResponse:
    """
    Stream AI Reasoning Process

    **Transparent AI decision-making** for healthcare queries with real-time reasoning steps.

    **Stream Events:**
    - Query analysis and medical context identification
    - PHI detection and safety verification
    - Step-by-step reasoning with confidence scores
    - Final analysis with safety disclaimers

    **Use Case:** Provide transparency in AI medical analysis
    **Compliance:** Includes medical disclaimers and safety warnings
    """
    from core.infrastructure.streaming import stream_ai_reasoning

    return await stream_ai_reasoning(medical_query, user_id, session_id)


@app.get("/stream/document_processing", tags=["streaming"])
async def stream_document_processing(
    document_type: str = "clinical_note",
    user_id: str = "demo_user",
    session_id: str = "demo_session",
) -> StreamingResponse:
    """
    Stream Medical Document Processing

    **Real-time updates** during medical document analysis and processing.

    **Stream Events:**
    - Document structure analysis
    - Medical entity extraction progress
    - PHI detection and compliance checking
    - Structured output generation

    **Use Case:** Show progress during complex document processing
    **Compliance:** PHI detection and HIPAA compliance verification
    """
    from core.infrastructure.streaming import stream_document_processing

    return await stream_document_processing(document_type, user_id, session_id)


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
