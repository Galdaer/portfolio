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
import json
from functools import lru_cache
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from config.app import config
from core.config.models import get_primary_model
from core.infrastructure.healthcare_logger import (
    get_healthcare_logger,
    setup_healthcare_logging,
)

# Setup healthcare-compliant logging infrastructure
setup_healthcare_logging(log_level=config.log_level.upper())

# Get healthcare logger for main application
logger = get_healthcare_logger(__name__)

# Healthcare AI orchestration configuration (centralized)
ORCHESTRATOR_MODEL = get_primary_model()

# HTTP Request/Response models
class ProcessRequest(BaseModel):
    message: str
    user_id: str = "anonymous"
    session_id: str = "default"
    format: str = "human"  # "human" for readable text, "json" for raw JSON
    # Optional per-request toggle to include a human-readable "Sources" section
    # Citations remain in result["citations"] regardless of this flag
    show_sources: bool | None = None

class ProcessResponse(BaseModel):
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None
    # Back-compat for older pipelines expecting a 'response' string
    response: str | None = None
    formatted_response: str | None = None  # Human-readable response

# Global variables for agent management
discovered_agents = {}
healthcare_services = None
llm_client = None
langchain_orchestrator = None  # primary orchestrator (LangChain)


# -------------------------
# Orchestrator configuration
# -------------------------
@lru_cache(maxsize=1)
def load_orchestrator_config() -> dict[str, Any]:
    """Load orchestrator.yml with safe defaults."""
    cfg_path = Path(__file__).parent / "config" / "orchestrator.yml"
    defaults: dict[str, Any] = {
        "selection": {"enabled": True, "enable_fallback": True, "allow_parallel_helpers": False},
        "timeouts": {
            "router_selection": 5,
            "per_agent_default": 30,
            "per_agent_hard_cap": 90,
            "tool_max_retries": 2,
            "tool_retry_base_delay": 0.2,
        },
        "provenance": {"show_agent_header": True, "include_metadata": True},
        "routing": {
            "always_run_medical_search": True,
            "presearch_max_results": 5,
        },
        "synthesis": {
            "prefer": ["formatted_summary", "formatted_response", "response", "research_summary", "message"],
            "agent_priority": ["medical_search", "clinical_research", "document_processor", "intake"],
            "header_prefix": "🤖 ",
        },
        "fallback": {"agent_name": "base", "message_template": "I couldn't find a specialized agent to handle this request yet.\n\nRequest: \"{user_message}\""},
    }
    try:
        import yaml  # type: ignore
        if cfg_path.exists():
            with cfg_path.open("r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f) or {}
            # shallow-merge with defaults
            for k, v in defaults.items():
                if k not in loaded or not isinstance(loaded[k], dict):
                    loaded[k] = v
                else:
                    merged = v.copy()
                    merged.update(loaded[k])
                    loaded[k] = merged
            return loaded
    except Exception as e:  # pragma: no cover
        logger.warning(f"Failed to load orchestrator config: {e}")
    return defaults


def _build_agent_header(agent_name: str) -> str:
    pretty = agent_name.replace("_", " ").title()
    return f"🤖 **{pretty} Agent Response:**\n\n"


async def initialize_agents():
    """Initialize AI agents for HTTP processing"""
    global discovered_agents, healthcare_services, llm_client, langchain_orchestrator

    try:
        # Initialize healthcare services
        from core.dependencies import HealthcareServices
        healthcare_services = HealthcareServices()
        await healthcare_services.initialize()

        # Get LLM client
        llm_client = healthcare_services.llm_client

        # Initialize LangChain orchestrator as the default router
        try:
            from core.langchain.orchestrator import LangChainOrchestrator
            from src.local_llm.ollama_client import OllamaConfig, build_chat_model

            orch_cfg = load_orchestrator_config()
            timeouts = orch_cfg.get("timeouts", {}) if isinstance(orch_cfg, dict) else {}
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            model_name = getattr(ORCHESTRATOR_MODEL, "model", None) or ORCHESTRATOR_MODEL

            chat_model = build_chat_model(
                OllamaConfig(model=str(model_name), base_url=base_url, temperature=0.0)
            )
            langchain_orchestrator = LangChainOrchestrator(
                mcp_client=healthcare_services.mcp_client,
                chat_model=chat_model,
                timeouts={
                    "per_agent_default": float(timeouts.get("per_agent_default", 30)),
                    "per_agent_hard_cap": float(timeouts.get("per_agent_hard_cap", 90)),
                },
                always_run_medical_search=bool(orch_cfg.get("routing", {}).get("always_run_medical_search", True)),
                presearch_max_results=int(orch_cfg.get("routing", {}).get("presearch_max_results", 5)),
                citations_max_display=int(orch_cfg.get("langchain", {}).get("citations_max_display", 10)),
            )
            logger.info("LangChain orchestrator initialized (default)")
        except Exception as e:
            logger.error(f"Failed to initialize LangChain orchestrator: {e}")

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


async def _call_agent_safely(agent: Any, request_data: dict[str, Any], timeout_s: float) -> tuple[dict[str, Any] | None, str | None]:
    """Call an agent with timeout and exception safety. Returns (result, error)."""
    try:
        result = await asyncio.wait_for(agent.process_request(request_data), timeout=timeout_s)
        return result, None
    except Exception as e:
        return None, str(e)


async def _run_base_fallback(user_message: str) -> dict[str, Any]:
    """Generate a minimal, safe fallback response using the base model without medical advice."""
    orch = load_orchestrator_config()
    tmpl = orch.get("fallback", {}).get("message_template", "")
    msg = tmpl.format(user_message=user_message)
    # Build a conservative summary with disclaimers
    summary_lines = [
        msg,
        "",
        "Disclaimers:",
        "- This system provides administrative/documentation support only and is not medical advice.",
        "- For medical concerns, consult a licensed healthcare professional.",
    ]
    formatted = "\n".join(summary_lines)
    return {
        "success": True,
        "agent_name": orch.get("fallback", {}).get("agent_name", "base"),
        "agent_type": "base",
        "message": msg,
        "formatted_summary": formatted,
    }


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
    """Process message via AI agents.

    Parameters
    - show_sources: When false, hides the human-readable "Sources" section in the
        formatted response (citations still returned in result["citations"]).
    """
    try:
        # Default path: LangChain orchestrator
        if not langchain_orchestrator:
            return ProcessResponse(status="error", error="LangChain orchestrator unavailable")
        try:
            result = await langchain_orchestrator.process(
                request.message,
                show_sources=request.show_sources,
            )
            if request.format == "human":
                formatted = result.get("formatted_summary", "") or "Operation completed."
                return ProcessResponse(status="success", result=result, response=formatted, formatted_response=formatted)
            return ProcessResponse(status="success", result=result)
        except Exception as e:
            logger.error(f"LangChain orchestrator error: {e}")
            fb = langchain_orchestrator.get_fallback_response() if langchain_orchestrator else {"formatted_summary": "Unavailable"}
            if request.format == "human":
                formatted = fb.get("formatted_summary", "")
                return ProcessResponse(status="error", error="orchestrator_error", response=formatted, formatted_response=formatted)
            return ProcessResponse(status="error", error="orchestrator_error", result=fb)

        # Ensure agents are initialized
        if not discovered_agents:
            return ProcessResponse(status="error", error="No agents available")

        if not llm_client:
            return ProcessResponse(status="error", error="LLM client not available")

        orch = load_orchestrator_config()

        # Let LLM choose the appropriate agent based on message content
        selected_agent = await select_agent_with_llm(request.message, discovered_agents, llm_client)

        # All agents inherit from BaseHealthcareAgent and must implement process_request
        if not hasattr(selected_agent, "process_request"):
            logger.error(f"Agent {getattr(selected_agent, 'agent_name', 'unknown')} missing process_request method")
            return ProcessResponse(status="error", error="Agent missing required interface")

        # Standard request payload for agents
        request_data = {
            "message": request.message,
            "query": request.message,  # Some agents may expect 'query' instead of 'message'
            "user_id": request.user_id,
            "session_id": request.session_id,
        }

        # Primary call with safe timeout and base fallback
        try:
            timeout_s = float(orch.get("timeouts", {}).get("per_agent_default", 30))
            hard_cap = float(orch.get("timeouts", {}).get("per_agent_hard_cap", 90))
            timeout_s = min(max(1.0, timeout_s), hard_cap)

            result, err = await _call_agent_safely(selected_agent, request_data, timeout_s)

            enable_fallback = bool(orch.get("selection", {}).get("enable_fallback", True))
            if err or not isinstance(result, dict) or (result.get("success") is False and enable_fallback):
                logger.warning(f"Primary agent failed or returned unsuccessful result, falling back. Error: {err}")
                result = await _run_base_fallback(request.message)
                agent_name_for_header = result.get("agent_name", "base")
            else:
                agent_name_for_header = getattr(selected_agent, "agent_name", "unknown")

            if request.format == "human":
                preferred_keys = orch.get("synthesis", {}).get("prefer", [
                    "formatted_summary", "formatted_response", "response", "research_summary", "message",
                ])
                payload = result or {}
                text = next((payload.get(k) for k in preferred_keys if isinstance(payload.get(k), str) and payload.get(k)), None)
                if not text:
                    text = json.dumps(payload) if payload else "Operation completed."
                header = _build_agent_header(agent_name_for_header) if orch.get("provenance", {}).get("show_agent_header", True) else ""
                formatted_text = f"{header}{text}"
                return ProcessResponse(status="success", result=result, response=formatted_text, formatted_response=formatted_text)

            return ProcessResponse(status="success", result=result)

        except Exception as e:
            logger.error(f"Error calling agent process_request: {e}")
            error_msg = f"Agent processing error: {str(e)}"
            if request.format == "human":
                return ProcessResponse(
                    status="error",
                    error=error_msg,
                    response=f"❌ **Error:** {error_msg}",
                    formatted_response=f"❌ **Error:** {error_msg}",
                )
            return ProcessResponse(status="error", error=error_msg)

    except Exception as e:
        logger.error(f"Error processing HTTP request: {e}")
        error_msg = str(e)

        format_type = getattr(request, "format", "human")
        if format_type == "human":
            return ProcessResponse(
                status="error",
                error=error_msg,
                response=f"❌ **System Error:** {error_msg}",
                formatted_response=f"❌ **System Error:** {error_msg}",
            )
        return ProcessResponse(status="error", error=error_msg)


if __name__ == "__main__":
    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)

    # Run as HTTP server
    logger.info("Starting healthcare-api HTTP server")
    uvicorn.run(app, host="0.0.0.0", port=8000)
