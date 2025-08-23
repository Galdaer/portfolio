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
from datetime import datetime
from functools import lru_cache
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config.app import config
from core.config.models import get_primary_model
from core.infrastructure.healthcare_logger import (
    get_healthcare_logger,
    setup_healthcare_logging,
)
from core.phi_sanitizer import sanitize_request_data, sanitize_response_data
from config.transcription_config_loader import TRANSCRIPTION_CONFIG

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


# Open WebUI compatible models
class ChatCompletionsRequest(BaseModel):
    model: str
    messages: list[dict[str, str]]
    temperature: float = 0.7
    max_tokens: int | None = None
    stream: bool = False


class InvokeRequest(BaseModel):
    arguments: dict[str, Any] | None = None


# Simple chat request for direct orchestrator routing
class ChatRequest(BaseModel):
    message: str


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
            "prefer": [
                "formatted_summary",
                "formatted_response",
                "response",
                "research_summary",
                "message",
            ],
            "agent_priority": [
                "medical_search",
                "clinical_research",
                "document_processor",
                "intake",
            ],
            "header_prefix": "🤖 ",
        },
        "fallback": {
            "agent_name": "base",
            "message_template": 'I couldn\'t find a specialized agent to handle this request yet.\n\nRequest: "{user_message}"',
        },
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

        # Dynamic agent discovery first
        from agents import BaseHealthcareAgent

        agents_dir = Path(__file__).parent / "agents"
        discovered_agents = {}

        for agent_dir in agents_dir.iterdir():
            if not agent_dir.is_dir() or agent_dir.name.startswith("__"):
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
                        if (
                            issubclass(obj, BaseHealthcareAgent)
                            and obj != BaseHealthcareAgent
                            and hasattr(obj, "__module__")
                            and obj.__module__ == module_name
                        ):
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

        # Initialize LangChain orchestrator as the default router (after agent discovery)
        try:
            from core.langchain.orchestrator import LangChainOrchestrator
            from src.local_llm.ollama_client import OllamaConfig, build_chat_model

            orch_cfg = load_orchestrator_config()
            timeouts = orch_cfg.get("timeouts", {}) if isinstance(orch_cfg, dict) else {}
            base_url = os.getenv("OLLAMA_BASE_URL", "http://172.20.0.10:11434")
            model_name = getattr(ORCHESTRATOR_MODEL, "model", None) or ORCHESTRATOR_MODEL

            chat_model = build_chat_model(
                OllamaConfig(model=str(model_name), base_url=base_url, temperature=0.0)
            )

            # Create a simple agent manager for discovered_agents
            class SimpleAgentManager:
                def __init__(self, agents_dict):
                    self.agents = agents_dict

                def get_agent(self, name):
                    return self.agents.get(name)

                def list_agents(self):
                    return list(self.agents.keys())

            agent_manager = SimpleAgentManager(discovered_agents)

            langchain_orchestrator = LangChainOrchestrator(
                mcp_client=healthcare_services.mcp_client,
                chat_model=chat_model,
                timeouts={
                    "per_agent_default": float(timeouts.get("per_agent_default", 30)),
                    "per_agent_hard_cap": float(timeouts.get("per_agent_hard_cap", 90)),
                },
                always_run_medical_search=bool(
                    orch_cfg.get("routing", {}).get("always_run_medical_search", True)
                ),
                presearch_max_results=int(
                    orch_cfg.get("routing", {}).get("presearch_max_results", 5)
                ),
                citations_max_display=int(
                    orch_cfg.get("langchain", {}).get("citations_max_display", 10)
                ),
                agent_manager=agent_manager,
            )
            logger.info("LangChain orchestrator initialized (default)")
        except Exception as e:
            logger.error(f"Failed to initialize LangChain orchestrator: {e}")

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

# Enable CORS for Open WebUI integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for UI components
app.mount("/static", StaticFiles(directory="static"), name="static")


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
        "policy_version": getattr(
            __import__(
                "core.infrastructure.rate_limiting", fromlist=["RATE_LIMITS_POLICY_VERSION"]
            ),
            "RATE_LIMITS_POLICY_VERSION",
            "unknown",
        ),
    }


@app.get("/api/config/ui")
async def get_ui_config():
    """Get UI configuration for frontend applications"""
    try:
        from config.ui_config_loader import UI_CONFIG
        
        return {
            "websocket_url": UI_CONFIG.api_integration.websocket_url,
            "rest_api_url": UI_CONFIG.api_integration.rest_api_url,
            "transcription_endpoint": UI_CONFIG.api_integration.transcription_endpoint,
            "session_timeout_seconds": UI_CONFIG.session.timeout_seconds,
            "chunk_interval_seconds": UI_CONFIG.session.chunk_interval_seconds,
            "show_real_time_transcription": UI_CONFIG.user_experience.show_real_time_transcription,
            "show_status_updates": UI_CONFIG.user_experience.show_status_updates,
            "medical_disclaimer": UI_CONFIG.compliance.disclaimer_text if UI_CONFIG.compliance.show_medical_disclaimer else None
        }
    except Exception as e:
        logger.error(f"Error loading UI config: {e}")
        return {
            "websocket_url": "ws://localhost:8000",
            "rest_api_url": "http://localhost:8000", 
            "transcription_endpoint": "/ws/transcription",
            "session_timeout_seconds": 300,
            "chunk_interval_seconds": 2,
            "show_real_time_transcription": True,
            "show_status_updates": True,
            "medical_disclaimer": "⚠️ This system provides administrative transcription support only."
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
            try:
                response_data = json.loads(response["response"])
                selected_agent_name = response_data["agent"].strip().lower()
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(
                    f"Failed to parse LLM structured response: {response.get('response', 'No response')}"
                )
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
            try:
                response_data = json.loads(response["message"]["content"])
                selected_agent_name = response_data["agent"].strip().lower()
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(
                    f"Failed to parse LLM structured response: {response['message'].get('content', 'No response')}"
                )
                raise ValueError(f"LLM returned malformed response: {e}")
        else:
            raise ValueError(
                f"LLM client missing expected methods. Available methods: {[method for method in dir(llm_client) if not method.startswith('_')]}"
            )

        # Try to find matching agent
        for name, agent in available_agents.items():
            if name.lower() == selected_agent_name or name.lower().replace(
                "_", ""
            ) == selected_agent_name.replace("_", ""):
                logger.info(f"Local LLM selected agent: {name}")
                return agent

        # If no exact match, raise error to identify LLM selection issues
        raise ValueError(
            f"Local LLM selected unknown agent '{selected_agent_name}', available: {list(available_agents.keys())}"
        )

    except Exception as e:
        logger.error(f"Error in LLM agent selection: {e}")
        raise  # Don't mask LLM issues with fallbacks


async def process_query(self, query: str, **kwargs) -> Dict[str, Any]:
    """Process a healthcare query using the appropriate agent."""
    try:
        # ...existing code...

        # Process with selected agent
        result = await agent_func({"query": query, **kwargs})

        # Format the response for human consumption
        if isinstance(result, dict) and result.get("success"):
            formatted_response = self._format_agent_response(result)
            return {
                "success": True,
                "message": formatted_response,
                "raw_data": result,  # Keep raw data for debugging
                "agent_used": selected_agent,
            }

        return result

    except Exception as e:
        logger.error(f"❌ Error processing query: {str(e)}")
        return {"success": False, "error": str(e)}


def _format_agent_response(self, response: Dict[str, Any]) -> str:
    """Format agent response for human-readable output."""

    # Check if we already have a formatted summary
    if "formatted_summary" in response:
        return response["formatted_summary"]

    # Handle medical search responses
    if response.get("agent_type") == "search" and "information_sources" in response:
        sources = response.get("information_sources", [])
        total = response.get("total_sources", len(sources))

        formatted = f"I found {total} relevant articles on cardiovascular health. Here are the most recent:\n\n"

        for i, source in enumerate(sources[:10], 1):
            title = source.get("title", "No title")
            authors = source.get("authors", [])
            journal = source.get("journal", "Unknown journal")
            url = source.get("url", "")
            abstract = source.get("abstract", "No abstract available")

            formatted += f"**{i}. {title}**\n"
            if authors:
                formatted += f"   Authors: {', '.join(authors[:3])}"
                if len(authors) > 3:
                    formatted += f" et al."
                formatted += "\n"
            formatted += f"   Journal: {journal}\n"
            if url:
                formatted += f"   [View on PubMed]({url})\n"
            if abstract and abstract != "No abstract available":
                formatted += (
                    f"   Abstract: {abstract[:200]}...\n"
                    if len(abstract) > 200
                    else f"   Abstract: {abstract}\n"
                )
            formatted += "\n"

        # Add disclaimers
        disclaimers = response.get("disclaimers", [])
        if disclaimers:
            formatted += "\n---\n*" + "\n*".join(disclaimers) + "*"

        return formatted

    # Default formatting for other responses
    return json.dumps(response, indent=2)


async def _call_agent_safely(
    agent: Any, request_data: dict[str, Any], timeout_s: float
) -> tuple[dict[str, Any] | None, str | None]:
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
            response_parts.append(
                f"🤖 **{agent_name.replace('_', ' ').title()} Agent Response:**\n"
            )

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
        if (
            "result" in result and len(response_parts) <= 1
        ):  # Only if we haven't found other content
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
        return f"📋 Returned {len(result)} items: " + ", ".join(
            str(item)[:50] for item in result[:3]
        )
    return f"✅ Operation completed. Result: {str(result)[:200]}"


# Open WebUI compatible endpoints
@app.get("/pipelines")
async def list_pipelines():
    """List available pipelines for Open WebUI"""
    try:
        return [
            {
                "id": "healthcare",
                "name": "Healthcare AI",
                "description": "Healthcare AI with medical literature search",
            },
            {
                "id": "medical-search",
                "name": "Medical Search",
                "description": "Medical literature search and clinical information",
            },
        ]
    except Exception as e:
        logger.error(f"Failed to list pipelines: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to list pipelines: {str(e)}"},
        )


@app.get("/models")
async def list_models():
    """Return OpenAI-style models list for Open WebUI compatibility"""
    try:
        models = [
            {"id": "healthcare", "name": "Healthcare AI", "owned_by": "intelluxe"},
            {"id": "medical-search", "name": "Medical Search", "owned_by": "intelluxe"},
        ]
        pipelines_data = [
            {
                "id": "healthcare",
                "name": "Healthcare AI",
                "description": "Healthcare AI with medical literature search",
            },
            {
                "id": "medical-search",
                "name": "Medical Search",
                "description": "Medical literature search and clinical information",
            },
        ]
        return {"object": "list", "data": models, "pipelines": pipelines_data}
    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/tools")
async def list_tools():
    """List available MCP tools"""
    try:
        # Return discovered agents as tools
        tools = []
        for name, agent in discovered_agents.items():
            tools.append(
                {
                    "id": name,
                    "name": name.replace("_", " ").title(),
                    "description": f"Healthcare agent: {name}",
                    "type": "agent",
                }
            )
        return {"object": "list", "data": tools}
    except Exception as e:
        logger.error(f"Failed to list tools: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/tools/{tool_id}")
async def get_tool(tool_id: str):
    """Return details for a single tool"""
    try:
        if tool_id in discovered_agents:
            agent = discovered_agents[tool_id]
            return {
                "id": tool_id,
                "name": tool_id.replace("_", " ").title(),
                "description": f"Healthcare agent: {tool_id}",
                "type": "agent",
                "agent_name": getattr(agent, "agent_name", tool_id),
                "agent_type": getattr(agent, "agent_type", "healthcare"),
            }
        return JSONResponse(status_code=404, content={"error": "Tool not found"})
    except Exception as e:
        logger.error(f"Failed to get tool {tool_id}: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/tools/{tool_id}/invoke")
async def invoke_tool(tool_id: str, req: InvokeRequest):
    """Invoke a tool (agent) directly"""
    try:
        if tool_id not in discovered_agents:
            return JSONResponse(status_code=404, content={"error": "Tool not found"})

        agent = discovered_agents[tool_id]
        args = req.arguments or {}

        # Convert arguments to process_request format
        request_data = {
            "message": args.get("message", args.get("query", "")),
            "query": args.get("query", args.get("message", "")),
            "user_id": args.get("user_id", "anonymous"),
            "session_id": args.get("session_id", "default"),
        }

        result = await agent.process_request(request_data)
        return {"status": "success", "result": result}

    except ValueError as ve:
        logger.error(f"Tool invocation validation error: {ve}")
        return JSONResponse(status_code=400, content={"error": str(ve)})
    except Exception as e:
        logger.error(f"Tool invocation error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionsRequest):
    """Handle OpenAI-style chat completions for Open WebUI with HIPAA compliance"""
    try:
        # PHASE 1.2 PHI DETECTION: Sanitize incoming request for HIPAA compliance
        request_dict = request.dict()
        sanitized_request = sanitize_request_data(request_dict)
        logger.info("🛡️ Request sanitized for HIPAA compliance")

        # Extract the last user message (from sanitized request)
        user_message = ""
        for message in reversed(sanitized_request.get("messages", [])):
            if message.get("role") == "user":
                user_message = message.get("content", "")
                break

        if not user_message:
            return JSONResponse(status_code=400, content={"error": "No user message found"})

        # Process through our healthcare system
        process_request = ProcessRequest(
            message=user_message,
            user_id="openwebui",
            session_id="openwebui_session",
            format="human",
        )

        # Use the existing process logic
        result = await process_message(process_request)

        if result.status == "error":
            return JSONResponse(status_code=500, content={"error": result.error})

        # Convert to OpenAI format
        response_content = result.formatted_response or result.response or "Operation completed"

        openai_response = {
            "id": "chatcmpl-healthcare",
            "object": "chat.completion",
            "created": int(asyncio.get_event_loop().time()),
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": response_content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": len(user_message.split()),
                "completion_tokens": len(response_content.split()),
                "total_tokens": len(user_message.split()) + len(response_content.split()),
            },
        }

        # PHASE 1.2 PHI DETECTION: Sanitize outgoing response for HIPAA compliance
        sanitized_response = sanitize_response_data(openai_response)
        logger.info("🛡️ Response sanitized for HIPAA compliance")

        logger.info(f"OpenAI chat completion processed with PHI protection: {user_message[:100]}")
        return sanitized_response

    except Exception as e:
        logger.error(f"Chat completion error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# Add the same route without /v1 prefix for Open WebUI compatibility
app.add_api_route("/chat/completions", chat_completions, methods=["POST"])


@app.post("/chat")
async def chat(request: ChatRequest):
    """Process chat messages through the healthcare AI system."""
    try:
        # PHASE 1.2 PHI DETECTION: Sanitize incoming request for HIPAA compliance
        request_dict = request.dict()
        sanitized_request = sanitize_request_data(request_dict)
        logger.info("🛡️ Request sanitized for HIPAA compliance")

        # Extract the last user message (from sanitized request)
        user_message = ""
        for message in reversed(sanitized_request.get("messages", [])):
            if message.get("role") == "user":
                user_message = message.get("content", "")
                break

        if not user_message:
            return JSONResponse(status_code=400, content={"error": "No user message found"})

        # Process through our healthcare system
        process_request = ProcessRequest(
            message=user_message,
            user_id="openwebui",
            session_id="openwebui_session",
            format="human",
        )

        # Use the existing process logic
        result = await process_message(process_request)

        if result.status == "error":
            return JSONResponse(status_code=500, content={"error": result.error})

        # Convert to OpenAI format
        response_content = result.formatted_response or result.response or "Operation completed"

        openai_response = {
            "id": "chatcmpl-healthcare",
            "object": "chat.completion",
            "created": int(asyncio.get_event_loop().time()),
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": response_content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": len(user_message.split()),
                "completion_tokens": len(response_content.split()),
                "total_tokens": len(user_message.split()) + len(response_content.split()),
            },
        }

        # PHASE 1.2 PHI DETECTION: Sanitize outgoing response for HIPAA compliance
        sanitized_response = sanitize_response_data(openai_response)
        logger.info("🛡️ Response sanitized for HIPAA compliance")

        logger.info(f"OpenAI chat completion processed with PHI protection: {user_message[:100]}")
        return sanitized_response

    except Exception as e:
        logger.error(f"❌ Error in chat endpoint: {str(e)}")
        return {
            "response": "I apologize, but I encountered an error processing your request.",
            "metadata": {"error": str(e)},
        }


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
            # Use conclusive adapters when agents are available to prevent iteration loops
            if discovered_agents:
                result = await langchain_orchestrator.process_with_conclusive_adapters(
                    request.message,
                    discovered_agents,
                    show_sources=request.show_sources,
                )
            else:
                # Fallback to regular processing when no agents discovered
                result = await langchain_orchestrator.process(
                    request.message,
                    show_sources=request.show_sources,
                )
            if request.format == "human":
                formatted = result.get("formatted_summary", "") or "Operation completed."
                return ProcessResponse(
                    status="success",
                    result=result,
                    response=formatted,
                    formatted_response=formatted,
                )
            return ProcessResponse(status="success", result=result)
        except Exception as e:
            logger.error(f"LangChain orchestrator error: {e}")
            fb = (
                langchain_orchestrator.get_fallback_response()
                if langchain_orchestrator
                else {"formatted_summary": "Unavailable"}
            )
            if request.format == "human":
                formatted = fb.get("formatted_summary", "")
                return ProcessResponse(
                    status="error",
                    error="orchestrator_error",
                    response=formatted,
                    formatted_response=formatted,
                )
            return ProcessResponse(status="error", error="orchestrator_error", result=fb)

    # Legacy direct-agent routing removed; API now routes exclusively through orchestrator

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


# Live Transcription WebSocket Management
class SessionManager:
    """Manage live transcription sessions for doctor-patient encounters"""
    
    def __init__(self):
        self.active_sessions = {}
        self.config = TRANSCRIPTION_CONFIG.session
        
    async def create_session(self, doctor_id: str, patient_context: dict = None) -> str:
        """Create a new live transcription session"""
        import uuid
        from datetime import datetime
        
        session_id = f"{self.config.session_id_prefix}{str(uuid.uuid4())}"
        self.active_sessions[session_id] = {
            "doctor_id": doctor_id,
            "patient_context": patient_context or {},
            "start_time": datetime.utcnow(),
            "transcription_buffer": [],
            "status": "active",
            "timeout_seconds": self.config.default_timeout_seconds
        }
        
        logger.info(f"Created live transcription session {session_id} for doctor {doctor_id}")
        return session_id
        
    async def end_session(self, session_id: str) -> dict:
        """End a session and return full transcription"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session["status"] = "completed"
            session["end_time"] = datetime.utcnow()
            
            full_transcription = " ".join([
                chunk["text"] for chunk in session["transcription_buffer"]
            ])
            
            logger.info(f"Ended transcription session {session_id}")
            return {
                "session_id": session_id,
                "full_transcription": full_transcription,
                "duration_minutes": (session["end_time"] - session["start_time"]).total_seconds() / 60,
                "chunk_count": len(session["transcription_buffer"])
            }
        return {"error": "Session not found"}
        
    def get_session(self, session_id: str) -> dict:
        """Get session information"""
        return self.active_sessions.get(session_id, {})

# Global session manager
session_manager = SessionManager()


@app.websocket("/ws/transcription/{doctor_id}")
async def websocket_transcription(websocket: WebSocket, doctor_id: str):
    """
    WebSocket endpoint for live medical transcription during doctor-patient sessions
    
    Features:
    - Real-time audio processing with WhisperLive integration
    - PHI detection and sanitization
    - Medical terminology processing
    - Session management for encounter context
    """
    await websocket.accept()
    
    # Get transcription configuration
    config = TRANSCRIPTION_CONFIG
    
    # Create transcription session
    patient_context = {}  # Could be enhanced to receive patient context
    session_id = await session_manager.create_session(doctor_id, patient_context)
    
    try:
        # Send session initialization with configuration
        await websocket.send_json({
            "type": "session_start",
            "session_id": session_id,
            "doctor_id": doctor_id,
            "message": "Live transcription session started",
            "timeout_seconds": config.session.default_timeout_seconds,
            "chunk_interval_seconds": config.session.audio_chunk_interval_seconds
        })
        
        while True:
            # Receive audio data from WebSocket
            message = await websocket.receive_json()
            
            if message.get("type") == "audio_chunk":
                # Process audio chunk for transcription
                audio_data = message.get("audio_data", {})
                result = await process_live_audio_chunk(session_id, doctor_id, audio_data)
                
                # Send transcription result back
                await websocket.send_json({
                    "type": "transcription_chunk",
                    "session_id": session_id,
                    "result": result
                })
                
            elif message.get("type") == "end_session":
                # End the session and generate final summary
                session_summary = await session_manager.end_session(session_id)
                
                # Generate SOAP note if enabled and transcription is available
                soap_note_result = None
                if config.integration.soap_generation_enabled and session_summary.get("full_transcription"):
                    soap_note_result = await generate_soap_note_from_session(
                        session_id, doctor_id, session_summary
                    )
                
                await websocket.send_json({
                    "type": "session_end",
                    "session_id": session_id,
                    "summary": session_summary,
                    "soap_note": soap_note_result,
                    "soap_generation_enabled": config.integration.soap_generation_enabled
                })
                break
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for doctor {doctor_id}, session {session_id}")
        # Clean up session
        await session_manager.end_session(session_id)
    except Exception as e:
        logger.error(f"WebSocket error for doctor {doctor_id}: {e}")
        await websocket.close(code=1011, reason="Internal server error")


async def process_live_audio_chunk(session_id: str, doctor_id: str, audio_data: dict) -> dict:
    """Process a live audio chunk for transcription"""
    try:
        # Get the transcription agent
        transcription_agent = discovered_agents.get("transcription")
        if not transcription_agent:
            logger.error("Transcription agent not found")
            return {"error": "Transcription service unavailable"}
            
        # Prepare the request for the transcription agent
        request_data = {
            "audio_data": audio_data,
            "session_id": session_id,
            "doctor_id": doctor_id,
            "real_time": True
        }
        
        # Process with transcription agent
        result = await transcription_agent.process_request(request_data)
        
        # Store in session buffer
        session = session_manager.get_session(session_id)
        if session and result.get("success"):
            session["transcription_buffer"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "text": result.get("transcription", ""),
                "confidence": result.get("confidence", 0.0)
            })
            
        return result
        
    except Exception as e:
        logger.error(f"Error processing live audio chunk: {e}")
        return {"error": str(e), "success": False}


async def generate_soap_note_from_session(session_id: str, doctor_id: str, session_summary: dict) -> dict:
    """Generate SOAP note from completed transcription session"""
    try:
        # Get the SOAP notes agent
        soap_notes_agent = discovered_agents.get("soap_notes")
        if not soap_notes_agent:
            logger.warning("SOAP notes agent not found, skipping SOAP generation")
            return {"error": "SOAP notes service unavailable"}
        
        # Prepare request for SOAP notes agent
        soap_request = {
            "session_to_soap": {
                "session_id": session_id,
                "full_transcription": session_summary["full_transcription"],
                "doctor_id": doctor_id,
                "patient_id": "unknown",  # Could be enhanced to get from session context
                "encounter_date": datetime.now().isoformat()
            }
        }
        
        # Generate SOAP note
        soap_result = await soap_notes_agent.process_request(soap_request)
        
        if soap_result.get("success"):
            logger.info(f"SOAP note generated for session {session_id}")
            return {
                "success": True,
                "note_id": soap_result["note_id"],
                "soap_note": soap_result["soap_note"],
                "completeness_score": soap_result["completeness_score"],
                "quality_recommendations": soap_result["quality_recommendations"]
            }
        else:
            logger.error(f"SOAP note generation failed: {soap_result.get('error')}")
            return {"error": soap_result.get("error", "SOAP generation failed")}
        
    except Exception as e:
        logger.error(f"Error generating SOAP note from session {session_id}: {e}")
        return {"error": str(e)}


# Additional API endpoints for live transcription integration

class GenerateSOAPRequest(BaseModel):
    session_id: str
    doctor_id: str
    patient_id: str = "unknown"


@app.post("/generate-soap-from-session")
async def generate_soap_from_session_endpoint(request: GenerateSOAPRequest):
    """
    Generate SOAP note from a completed transcription session
    
    This endpoint allows manual generation of SOAP notes from transcription sessions
    that may not have automatically generated them during the WebSocket session.
    """
    try:
        # Get session data
        session = session_manager.get_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Check if session has transcription data
        if not session.get("transcription_buffer"):
            raise HTTPException(status_code=400, detail="No transcription data in session")
        
        # Create session summary
        full_transcription = " ".join([
            chunk["text"] for chunk in session["transcription_buffer"]
        ])
        
        session_summary = {
            "session_id": request.session_id,
            "full_transcription": full_transcription,
            "chunk_count": len(session["transcription_buffer"])
        }
        
        # Generate SOAP note
        soap_result = await generate_soap_note_from_session(
            request.session_id, request.doctor_id, session_summary
        )
        
        if soap_result.get("success"):
            return {
                "status": "success",
                "session_id": request.session_id,
                "soap_note": soap_result,
                "transcription_length": len(full_transcription)
            }
        else:
            raise HTTPException(
                status_code=500, 
                detail=f"SOAP generation failed: {soap_result.get('error', 'Unknown error')}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in SOAP generation endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/{session_id}")
async def get_session_info(session_id: str):
    """
    Get information about a transcription session
    
    Returns session status, transcription buffer, and metadata.
    """
    try:
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Calculate session statistics
        transcription_buffer = session.get("transcription_buffer", [])
        total_text_length = sum(len(chunk.get("text", "")) for chunk in transcription_buffer)
        
        return {
            "session_id": session_id,
            "status": session.get("status", "unknown"),
            "doctor_id": session.get("doctor_id"),
            "start_time": session.get("start_time"),
            "chunk_count": len(transcription_buffer),
            "total_text_length": total_text_length,
            "has_transcription": len(transcription_buffer) > 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)

    # Run as HTTP server
    logger.info("Starting healthcare-api HTTP server")
    uvicorn.run(app, host="0.0.0.0", port=8000)
