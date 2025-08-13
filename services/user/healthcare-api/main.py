#!/usr/bin/env python3
"""
Intelluxe AI - Healthcare AI System FastAPI Server

Privacy-First Healthcare AI System built for on-premise clinical deployment.
Focus: Administrative/documentation support, NOT medical advice.

MEDICAL DISCLAIMER: This system provides administrative and documentation support only.
It does not provide medical advice, diagnosis, or treatment recommendations.
All medical decisions should be made by qualified healthcare professionals.
"""

import asyncio
import importlib
import inspect
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from config.app import config
from core.infrastructure.healthcare_logger import (
    get_healthcare_logger,
    setup_healthcare_logging,
)

# Setup healthcare-compliant logging infrastructure
setup_healthcare_logging(log_level=config.log_level.upper())

# Get healthcare logger for main application
logger = get_healthcare_logger(__name__)

# Healthcare AI orchestration configuration
ORCHESTRATOR_MODEL = "llama3.1:8b"

# HTTP Request/Response models
class ProcessRequest(BaseModel):
    message: str
    user_id: str = "anonymous"
    session_id: str = "default"
    format: str = "human"  # "human" for readable text, "json" for raw JSON

class ProcessResponse(BaseModel):
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None
    formatted_response: str | None = None  # Human-readable response

# Global variables for agent management
discovered_agents = {}
healthcare_services = None
llm_client = None


async def initialize_agents():
    """Initialize AI agents for HTTP processing"""
    global discovered_agents, healthcare_services, llm_client

    try:
        # Initialize healthcare services
        from core.dependencies import HealthcareServices
        healthcare_services = HealthcareServices()
        await healthcare_services.initialize()

        # Get LLM client
        llm_client = healthcare_services.llm_client

        # Dynamic agent discovery
        from agents import BaseHealthcareAgent

        agents_dir = Path(__file__).parent / "agents"
        discovered_agents = {}

        for agent_dir in agents_dir.iterdir():
            if not agent_dir.is_dir() or agent_dir.name.startswith("."):
                continue

            # Look for agent files with flexible pattern matching
            agent_files = list(agent_dir.glob("*_agent.py"))
            if not agent_files:
                # Fallback to standard patterns
                agent_file_patterns = [
                    agent_dir / f"{agent_dir.name}_agent.py",
                    agent_dir / "agent.py",
                    agent_dir / f"{agent_dir.name}.py",
                ]
                agent_files = [f for f in agent_file_patterns if f.exists()]

            for agent_file in agent_files:
                try:
                    module_name = f"agents.{agent_dir.name}.{agent_file.stem}"
                    module = importlib.import_module(module_name)

                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if (issubclass(obj, BaseHealthcareAgent)
                                and obj != BaseHealthcareAgent
                                and hasattr(obj, "__module__")
                                and obj.__module__ == module_name):

                            # Instantiate agent with dependencies
                            agent_instance = obj(healthcare_services.mcp_client, llm_client)
                            agent_name = getattr(agent_instance, "agent_name", agent_dir.name)
                            discovered_agents[agent_name] = agent_instance
                            logger.info(f"Discovered and loaded agent: {agent_name}")
                            break
                    break
                except Exception as e:
                    logger.warning(f"Failed to import {agent_file}: {e}")
                    continue

        if not discovered_agents:
            logger.error("No agents discovered! Check agent directory structure and imports.")
        else:
            logger.info(f"AI agents initialized: {list(discovered_agents.keys())}")

    except Exception as e:
        logger.error(f"Failed to initialize agents: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for FastAPI application"""
    # Startup
    await initialize_agents()
    yield
    # Shutdown
    if healthcare_services:
        try:
            await healthcare_services.cleanup()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

# FastAPI app for HTTP server
app = FastAPI(
    title="Healthcare AI API",
    description="Healthcare AI system for administrative support",
    version="1.0.0",
    lifespan=lifespan,
)


@app.head("/warm")
@app.get("/warm")
async def warm() -> dict[str, Any]:
    """Warm endpoint to preload critical resources.

    Idempotent: safe to call multiple times. HEAD returns headers only.
    Preloads: agent initialization (handled in lifespan), optionally triggers
    lightweight LLM no-op prompt (skipped if unavailable) so first real
    request is lower latency.
    """
    # Optionally perform a tiny no-op generation to warm local model
    warmed_llm = False
    try:
        if llm_client and hasattr(llm_client, "generate"):
            # Minimal, fast prompt; ignore output
            await asyncio.wait_for(
                llm_client.generate(
                    model=ORCHESTRATOR_MODEL,
                    prompt="warmup",  # tiny context
                    stream=False,
                ),
                timeout=3.0,
            )
            warmed_llm = True
    except Exception:
        warmed_llm = False
    return {
        "status": "warm",
        "agents": list(discovered_agents.keys()) if discovered_agents else [],
        "llm_warmed": warmed_llm,
        "policy_version": getattr(__import__("core.infrastructure.rate_limiting", fromlist=["RATE_LIMITS_POLICY_VERSION"]), "RATE_LIMITS_POLICY_VERSION", "unknown"),
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "healthcare-api",
        "agents": list(discovered_agents.keys()) if discovered_agents else [],
    }


@app.get("/admin/rate-limit/stats")
async def rate_limit_stats():
    """Return current in-memory rate limiting metrics snapshot.

    NOTE: In-memory only; for multi-instance deployments aggregate via external metrics.
    """
    try:
        from core.infrastructure.rate_limiting import get_healthcare_rate_limiter
        limiter = get_healthcare_rate_limiter()
        return limiter.snapshot_metrics()
    except Exception as e:  # pragma: no cover
        logger.error(f"Failed to render rate limit stats: {e}")
        raise HTTPException(status_code=500, detail="metrics_unavailable")


@app.get("/admin/rate-limit/metrics/raw")
async def rate_limit_metrics_raw():
    """Return raw counter map (internal diagnostic)."""
    try:
        from core.infrastructure.rate_limiting import RATE_LIMIT_METRICS
        return {"metrics": RATE_LIMIT_METRICS}
    except Exception as e:  # pragma: no cover
        logger.error(f"Failed to fetch raw metrics: {e}")
        raise HTTPException(status_code=500, detail="raw_metrics_unavailable")


@app.get("/admin/health/full")
async def full_health():
    try:
        from core.infrastructure.health_monitoring import healthcare_monitor
        return await healthcare_monitor.comprehensive_health_check()
    except Exception as e:  # pragma: no cover
        logger.error(f"Full health check failed: {e}")
        raise HTTPException(status_code=500, detail="health_check_failed")


@app.get("/admin/health/quick")
async def quick_health():
    try:
        from core.infrastructure.health_monitoring import healthcare_monitor
        return await healthcare_monitor.quick_health_check()
    except Exception as e:  # pragma: no cover
        logger.error(f"Quick health check failed: {e}")
        raise HTTPException(status_code=500, detail="quick_health_failed")


@app.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics() -> str:
    """Prometheus-style metrics exposition.

    Text format (no dependencies). Safe to scrape. Lightweight aggregation only.
    """
    lines: list[str] = []
    # Rate limiting metrics via helper
    try:
        from core.infrastructure.rate_limiting import get_healthcare_rate_limiter
        limiter = get_healthcare_rate_limiter()
        lines.extend(limiter.prometheus_lines())
    except Exception as e:  # pragma: no cover
        logger.debug(f"Rate limit metrics build failed: {e}")
    # Health quick status
    try:
        from core.infrastructure.health_monitoring import healthcare_monitor
        # Refresh cached snapshot opportunistically
        await healthcare_monitor.quick_health_check()
        lines.extend(healthcare_monitor.prometheus_lines())
    except Exception as e:  # pragma: no cover
        logger.debug(f"Health quick metrics failed: {e}")
    # Optional instance label rewrite
    inst = os.getenv("METRICS_INSTANCE") or os.getenv("HOSTNAME")
    if inst:
        rewritten: list[str] = []
        for ln in lines:
            if ln.startswith("healthcare_") and "{" in ln:
                name, rest = ln.split("{", 1)
                if rest.startswith("}"):
                    # no existing labels
                    rewritten.append(f'{name}{{instance="{inst}"}}{rest[1:]}')
                else:
                    rewritten.append(f'{name}{{instance="{inst}",{rest}')
            else:
                rewritten.append(ln)
        lines = rewritten
    return "\n".join(lines) + "\n"


async def select_agent_with_llm(message: str, available_agents: dict, llm_client: Any) -> Any:
    """
    Use local LLM to intelligently select the most appropriate agent for the message
    
    SECURITY: Cloud AI disabled for PHI protection - using local LLM only
    """
    if not available_agents:
        raise ValueError("No agents available")

    # If only one agent, use it
    if len(available_agents) == 1:
        return next(iter(available_agents.values()))

    try:
        # Create agent descriptions for LLM using actual agent metadata
        agent_descriptions = {}
        for name, agent in available_agents.items():
            agent_type = getattr(agent, "agent_type", "general")

            # Get agent capabilities from docstring
            capabilities = []
            if hasattr(agent, "__doc__") and agent.__doc__:
                doc_lines = agent.__doc__.strip().split("\n")
                if doc_lines:
                    capabilities.append(doc_lines[0])

            # Try to get explicit capabilities
            if hasattr(agent, "get_capabilities"):
                try:
                    agent_caps = await agent.get_capabilities()
                    if isinstance(agent_caps, list):
                        capabilities.extend(agent_caps)
                except Exception as e:
                    logger.debug(f"Agent {name}.get_capabilities() failed: {e}")

            # Build description from available metadata
            description_parts = [f"Agent: {name}", f"Type: {agent_type}"]
            if capabilities:
                description_parts.append(f"Capabilities: {', '.join(capabilities)}")
            else:
                description_parts.append("Capabilities: Available via process_request interface")

            agent_descriptions[name] = " | ".join(description_parts)

        # Create prompt for LLM agent selection using actual agent metadata
        agent_list = "\n".join([f"- {name}: {desc}" for name, desc in agent_descriptions.items()])

        prompt = f"""
You are an intelligent agent router for an AI system. Based on the user message and the available agents with their actual capabilities, select the most appropriate agent.

Available agents with their capabilities:
{agent_list}

User message: "{message}"

Analyze the user's request and match it to the agent whose capabilities best align with what the user needs. Consider the agent type and specific capabilities listed.

You must respond with a JSON object containing only the agent name. Do not include explanations or reasoning.
"""

        # JSON schema for structured output - forces LLM to return just agent name
        format_schema = {
            "type": "object",
            "properties": {
                "agent": {
                    "type": "string",
                    "description": "The exact name of the selected agent",
                },
            },
            "required": ["agent"],
        }

        # Call LOCAL LLM to select agent (PHI-safe) with structured output
        if hasattr(llm_client, "generate"):
            # Ollama AsyncClient uses generate method with structured output
            response = await llm_client.generate(
                model=ORCHESTRATOR_MODEL,
                prompt=prompt,
                format=format_schema,
                stream=False,
            )
            # Parse structured JSON response
            import json
            try:
                response_data = json.loads(response["response"])
                selected_agent_name = response_data["agent"].strip().lower()
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Failed to parse LLM structured response: {response.get('response', 'No response')}")
                raise ValueError(f"LLM returned malformed response: {e}")
        elif hasattr(llm_client, "chat"):
            # Alternative Ollama chat interface with structured output
            response = await llm_client.chat(
                model=ORCHESTRATOR_MODEL,
                messages=[{"role": "user", "content": prompt}],
                format=format_schema,
                stream=False,
            )
            # Parse structured JSON response
            import json
            try:
                response_data = json.loads(response["message"]["content"])
                selected_agent_name = response_data["agent"].strip().lower()
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Failed to parse LLM structured response: {response['message'].get('content', 'No response')}")
                raise ValueError(f"LLM returned malformed response: {e}")
        else:
            raise ValueError(f"LLM client missing expected methods. Available methods: {[method for method in dir(llm_client) if not method.startswith('_')]}")

        # Try to find matching agent
        for name, agent in available_agents.items():
            if name.lower() == selected_agent_name or name.lower().replace("_", "") == selected_agent_name.replace("_", ""):
                logger.info(f"Local LLM selected agent: {name}")
                return agent

        # If no exact match, raise error to identify LLM selection issues
        raise ValueError(f"Local LLM selected unknown agent '{selected_agent_name}', available: {list(available_agents.keys())}")

    except Exception as e:
        logger.error(f"Error in LLM agent selection: {e}")
        raise  # Don't mask LLM issues with fallbacks


def format_response_for_user(result: dict[str, Any], agent_name: str = None) -> str:
    """
    Convert agent JSON response to human-readable text for web UI users
    
    Args:
        result: The JSON response from the agent
        agent_name: Name of the agent that generated the response
        
    Returns:
        Human-readable formatted text
    """
    if not result:
        return "No response received from the agent."

    # Handle success/failure status
    if isinstance(result, dict):
        if result.get("status") == "error":
            error_msg = result.get("error", "Unknown error")
            return f"❌ Error: {error_msg}"

        if result.get("success") is False:
            error_msg = result.get("error", result.get("message", "Operation failed"))
            return f"❌ {error_msg}"

        # Format successful responses based on common patterns
        response_parts = []

        # Add agent identification if provided
        if agent_name:
            response_parts.append(f"🤖 **{agent_name.replace('_', ' ').title()} Agent Response:**\n")

        # Handle search results
        if "search_id" in result:
            search_id = result["search_id"]
            response_parts.append(f"🔍 **Search completed** (ID: {search_id})")

            if "results" in result:
                results = result["results"]
                if isinstance(results, list) and results:
                    response_parts.append(f"Found {len(results)} result(s):")
                    for i, item in enumerate(results[:5], 1):  # Show first 5 results
                        if isinstance(item, dict):
                            title = item.get("title", item.get("name", f"Result {i}"))
                            response_parts.append(f"  {i}. {title}")
                        else:
                            response_parts.append(f"  {i}. {str(item)}")
                    if len(results) > 5:
                        response_parts.append(f"  ... and {len(results) - 5} more results")

        # Handle document processing
        if "processed_document" in result or "document_analysis" in result:
            response_parts.append("📄 **Document processed successfully**")

            analysis = result.get("document_analysis") or result.get("analysis")
            if analysis:
                response_parts.append(f"Analysis: {analysis}")

        # Handle general success messages
        if "message" in result and result.get("success", True):
            message = result["message"]
            if isinstance(message, str):
                response_parts.append(f"✅ {message}")

        # Handle data or content fields
        if "data" in result:
            data = result["data"]
            if isinstance(data, str):
                response_parts.append(f"📋 **Data:** {data}")
            elif isinstance(data, list):
                response_parts.append(f"📋 **Data:** {len(data)} items returned")

        # Handle general result field
        if "result" in result and len(response_parts) <= 1:  # Only if we haven't found other content
            result_data = result["result"]
            if isinstance(result_data, str):
                response_parts.append(result_data)
            elif isinstance(result_data, dict):
                # Try to extract meaningful information from result object
                for key in ["message", "summary", "description", "content"]:
                    if key in result_data:
                        response_parts.append(str(result_data[key]))
                        break

        # If we still have minimal content, show success
        if len(response_parts) <= 1:
            response_parts.append("✅ **Operation completed successfully**")

        return "\n".join(response_parts)

    # Handle non-dict responses
    if isinstance(result, str):
        return result
    if isinstance(result, list):
        return f"📋 Returned {len(result)} items: " + ", ".join(str(item)[:50] for item in result[:3])
    return f"✅ Operation completed. Result: {str(result)[:200]}"


@app.post("/process", response_model=ProcessResponse)
async def process_message(request: ProcessRequest) -> ProcessResponse:
    """Process message via AI agents"""
    try:
        # Ensure agents are initialized
        if not discovered_agents:
            return ProcessResponse(status="error", error="No agents available")

        if not llm_client:
            return ProcessResponse(status="error", error="LLM client not available")

        # Let LLM choose the appropriate agent based on message content
        selected_agent = await select_agent_with_llm(request.message, discovered_agents, llm_client)

        # All agents inherit from BaseHealthcareAgent and must implement process_request
        if not hasattr(selected_agent, "process_request"):
            logger.error(f"Agent {getattr(selected_agent, 'agent_name', 'unknown')} missing process_request method")
            return ProcessResponse(status="error", error="Agent missing required interface")

        # Call the standard process_request method with a dict parameter
        request_data = {
            "message": request.message,
            "query": request.message,  # Some agents may expect 'query' instead of 'message'
            "user_id": request.user_id,
            "session_id": request.session_id,
        }

        try:
            result = await selected_agent.process_request(request_data)

            # Format response based on user preference
            if request.format == "human":
                # Convert JSON to human-readable format
                formatted_text = format_response_for_user(result, getattr(selected_agent, "agent_name", "unknown"))
                return ProcessResponse(
                    status="success",
                    result=result,
                    formatted_response=formatted_text,
                )
            # Return raw JSON for API consumers
            return ProcessResponse(status="success", result=result)

        except Exception as e:
            logger.error(f"Error calling agent process_request: {e}")
            error_msg = f"Agent processing error: {str(e)}"

            if request.format == "human":
                return ProcessResponse(
                    status="error",
                    error=error_msg,
                    formatted_response=f"❌ **Error:** {error_msg}",
                )
            return ProcessResponse(status="error", error=error_msg)

    except Exception as e:
        logger.error(f"Error processing HTTP request: {e}")
        error_msg = str(e)

        # Try to get format from request, default to human for errors
        format_type = getattr(request, "format", "human")

        if format_type == "human":
            return ProcessResponse(
                status="error",
                error=error_msg,
                formatted_response=f"❌ **System Error:** {error_msg}",
            )
        return ProcessResponse(status="error", error=error_msg)


if __name__ == "__main__":
    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)

    # Run as HTTP server
    logger.info("Starting healthcare-api HTTP server")
    uvicorn.run(app, host="0.0.0.0", port=8000)
