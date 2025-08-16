"""
Minimal LangChain Orchestrator façade.

Initial version wires a single HealthcareLangChainAgent. Routing and
parallel helpers can be added in subsequent iterations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from core.mcp.universal_parser import extract_citations_from_mcp_steps
from pathlib import Path
import yaml

from langchain_core.language_models import BaseChatModel

from core.infrastructure.healthcare_logger import get_healthcare_logger
from core.langchain.agents import HealthcareLangChainAgent
from core.langchain.agent_adapters import synthesize_answer_from_sources, create_conclusive_agent_adapter

logger = get_healthcare_logger("core.langchain.orchestrator")


class LangChainOrchestrator:
    """Thin orchestrator around a single healthcare agent."""

    def __init__(
        self,
        mcp_client,
        chat_model: Optional[BaseChatModel] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        verbose: bool = False,
        max_orchestrator_iterations: int = 3,  # Not used - custom parameter for potential future use
        max_agent_iterations: int = 5,  # LangChain max_iterations: drastically reduced to prevent loops
        memory_max_token_limit: int = 2000,
        always_run_medical_search: bool = True,
        presearch_max_results: int = 5,
        citations_max_display: int = 10,
        tool_max_retries: int = 2,
        tool_retry_base_delay: float = 0.5,
        show_sources_default: bool = True,
        timeouts: Optional[Dict[str, float]] = None,
        show_agent_header: Optional[bool] = None,
        agent_manager: Optional[Any] = None,
    ):
        """Initialize the LangChain orchestrator for healthcare queries.

        Args:
            mcp_client: MCP client for tool execution
            model: Ollama model name
            temperature: LLM temperature for response generation
            verbose: Enable verbose logging
            max_orchestrator_iterations: Maximum orchestrator-level agent calls
            max_agent_iterations: Maximum agent-internal tool iterations
            memory_max_token_limit: Maximum tokens for conversation memory
            always_run_medical_search: Always run medical search presearch
            presearch_max_results: Maximum results for presearch
            citations_max_display: Maximum citations to display
            tool_max_retries: Maximum retries for tool calls
            tool_retry_base_delay: Base delay between tool retries
            show_sources_default: Default value for showing sources
        """
        # Load YAML configuration and prefer it over provided defaults/env when present
        cfg = self._load_orchestrator_config()

        # Resolve runtime settings with precedence: YAML config > provided args (defaults) > env handled by agent
        resolved_verbose = True  # Temporarily enable for debugging thought process
        resolved_always_run_medical_search = (
            bool(cfg.get("routing", {}).get("always_run_medical_search", always_run_medical_search))
            if isinstance(cfg, dict)
            else always_run_medical_search
        )
        resolved_presearch_max_results = (
            int(cfg.get("routing", {}).get("presearch_max_results", presearch_max_results))
            if isinstance(cfg, dict)
            else presearch_max_results
        )
        resolved_show_agent_header = (
            cfg.get("provenance", {}).get("show_agent_header")
            if isinstance(cfg, dict)
            else show_agent_header
        )

        # Timeouts and tool retry settings
        cfg_timeouts: Dict[str, float] | None = None
        if isinstance(cfg, dict) and isinstance(cfg.get("timeouts"), dict):
            tmo = cfg.get("timeouts", {})
            cfg_timeouts = {}
            for k in ("router_selection", "per_agent_default", "per_agent_hard_cap"):
                if k in tmo and tmo[k] is not None:
                    try:
                        cfg_timeouts[k] = float(tmo[k])
                    except Exception:
                        pass
            # Override tool retry knobs if present
            try:
                tool_max_retries = int(tmo.get("tool_max_retries", tool_max_retries))
            except Exception:
                pass
            try:
                tool_retry_base_delay = float(
                    tmo.get("tool_retry_base_delay", tool_retry_base_delay)
                )
            except Exception:
                pass

        self.mcp_client = mcp_client
        self.always_run_medical_search = resolved_always_run_medical_search
        self.presearch_max_results = resolved_presearch_max_results
        self.max_orchestrator_iterations = max_orchestrator_iterations
        self.citations_max_display = citations_max_display
        self.show_sources_default = show_sources_default

        # Environment overrides for iteration/timeouts
        import os as _os

        try:
            env_agent_iters = int(
                _os.getenv("HEALTHCARE_AGENT_MAX_ITERATIONS", str(max_agent_iterations))
            )
        except ValueError:
            env_agent_iters = max_agent_iterations
        # Initialize the LangChain agent with correct parameters
        self.agent = HealthcareLangChainAgent(
            mcp_client=mcp_client,
            chat_model=chat_model,
            model=model,
            temperature=temperature,
            verbose=resolved_verbose,
            max_iterations=env_agent_iters,  # Agent can use more internal iterations (env-aware)
            memory_max_token_limit=memory_max_token_limit,
            tool_max_retries=tool_max_retries,
            tool_retry_base_delay=tool_retry_base_delay,
            agent_manager=agent_manager,
        )

        # Apply optional runtime settings
        # Prefer YAML provenance.show_agent_header when present, else use explicit param if provided
        effective_show_header = (
            resolved_show_agent_header
            if resolved_show_agent_header is not None
            else show_agent_header
        )
        if effective_show_header is not None:
            try:
                setattr(self.agent, "show_agent_header", bool(effective_show_header))
            except Exception:
                pass

        # Apply timeouts: YAML first, then explicit param dict
        applied_timeouts = (
            cfg_timeouts
            if cfg_timeouts is not None
            else (timeouts if isinstance(timeouts, dict) else None)
        )
        if isinstance(applied_timeouts, dict):
            try:
                if "per_agent_default" in applied_timeouts:
                    setattr(
                        self.agent,
                        "per_agent_default_timeout",
                        float(applied_timeouts["per_agent_default"]),
                    )
                if "per_agent_hard_cap" in applied_timeouts:
                    setattr(
                        self.agent,
                        "per_agent_hard_cap",
                        float(applied_timeouts["per_agent_hard_cap"]),
                    )
            except Exception:
                # Best-effort; keep defaults if casting fails
                pass

        # Apply environment timeouts if provided (as a fallback when 'timeouts' not passed)
        try:
            import os as _os

            env_default = _os.getenv("HEALTHCARE_AGENT_TIMEOUT_DEFAULT")
            env_hardcap = _os.getenv("HEALTHCARE_AGENT_TIMEOUT_HARDCAP")
            if env_default:
                setattr(self.agent, "per_agent_default_timeout", float(env_default))
            if env_hardcap:
                setattr(self.agent, "per_agent_hard_cap", float(env_hardcap))
        except Exception:
            pass

    def _load_orchestrator_config(self) -> Dict[str, Any]:
        """Load orchestrator YAML config if available.

        Returns an empty dict when not found or on error.
        """
        try:
            cfg_dir = Path(__file__).parent.parent.parent / "config"
            path = cfg_dir / "orchestrator.yml"
            if path.exists():
                with open(path, "r") as f:
                    data = yaml.safe_load(f) or {}
                    if isinstance(data, dict):
                        return data
        except Exception:
            pass
        return {}

    async def process(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        show_sources: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Process a healthcare query using the LangChain agent.

        Args:
            query: The user's healthcare-related query
            context: Optional context for the query
            show_sources: Whether to show sources in formatted_summary (default: from config)

        Returns:
            Dictionary with formatted_summary, agent_name, agents_used, and optionally citations
        """
        try:
            # Optional presearch to guarantee medical_search coverage
            pre_citations: List[Dict[str, Any]] = []
            if self.always_run_medical_search:
                try:
                    # Prefer hyphenated tool name to match MCP normalization
                    presearch_obs = await self.mcp_client.call_tool(
                        "search-pubmed", {"query": query, "max_results": self.presearch_max_results}
                    )

                    class _Action:
                        def __init__(self, tool: str) -> None:
                            self.tool = tool

                    # Reuse citation extractor by forming a single synthetic step
                    pre_citations = self._extract_citations(
                        [(_Action("search_medical_literature"), presearch_obs)]
                    )
                except Exception:
                    pre_citations = []

            # Process with agent
            result = await self.agent.process(query, context=context)

            # Always include which agents were used (default to medical_search)
            result.setdefault("agents_used", [result.get("agent_name", "medical_search")])

            # Extract citations/sources from intermediate tool calls and attach
            citations = self._extract_citations(result.get("intermediate_steps", []))
            if pre_citations:
                citations = self._merge_citations(pre_citations, citations)
            if citations:
                result["citations"] = citations
                # Append a human-readable sources section when enabled
                display_sources = True if show_sources is None else bool(show_sources)
                if display_sources:
                    formatted = result.get("formatted_summary", "") or ""
                    lines = [formatted, "\n\nSources:"]
                    for c in citations[: self.citations_max_display]:
                        title = c.get("title") or c.get("name") or c.get("id") or "Source"
                        url = c.get("url") or c.get("link") or ""
                        src = c.get("source") or ""
                        bullet = f"- {title}"
                        if src:
                            bullet += f" ({src})"
                        if url:
                            bullet += f": {url}"
                        lines.append(bullet)
                    result["formatted_summary"] = "\n".join(lines).strip()

            return result
        except ConnectionError as e:
            # Specific handling for connection errors
            return {
                "success": False,
                "formatted_summary": "Unable to connect to the AI service. Please ensure the Ollama service is running and accessible.",
                "error": f"Connection failed: {str(e)}",
                "agent_name": "orchestrator",
                "agents_used": [],
            }
        except Exception as e:
            # Log the full error for debugging
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Orchestrator error: {e}", exc_info=True)

            # Return user-friendly error
            error_msg = str(e)
            if "connection" in error_msg.lower():
                return {
                    "success": False,
                    "formatted_summary": "The AI service is temporarily unavailable. Please try again in a moment.",
                    "error": "Service connection issue",
                    "agent_name": "orchestrator",
                    "agents_used": [],
                }
            else:
                # If the agent provided structured error_details, surface them
                error_details = None
                try:
                    if isinstance(e, Exception) and hasattr(e, "__dict__"):
                        error_details = getattr(e, "error_details", None)
                except Exception:
                    pass
                return {
                    "success": False,
                    "formatted_summary": f"I encountered an issue processing your request: {error_msg}",
                    "error": error_msg,
                    "error_details": error_details,
                    "agent_name": "orchestrator",
                    "agents_used": [],
                }

    async def process_with_conclusive_adapters(
        self,
        query: str,
        discovered_agents: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        show_sources: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Process a healthcare query using conclusive agent adapters to prevent iteration loops.
        
        This implements the pattern from the handoff document to ensure agents return
        conclusive answers instead of just source lists, preventing LangChain from
        hitting max_iterations (25).
        
        Args:
            query: The user's healthcare-related query
            discovered_agents: Dictionary of available healthcare agents
            context: Optional context for the query
            show_sources: Whether to show sources in formatted_summary
            
        Returns:
            Dictionary with conclusive answer, avoiding iteration loops
        """
        try:
            logger.info(f"🔄 Processing query with conclusive adapters: {query[:100]}...")
            
            # Determine the most appropriate agent for the query
            agent_name = "medical_search"  # Default to medical search
            if "appointment" in query.lower() or "schedule" in query.lower():
                agent_name = "scheduling"
            elif "billing" in query.lower() or "insurance" in query.lower():
                agent_name = "billing_helper"
            elif "intake" in query.lower() or "registration" in query.lower():
                agent_name = "intake"
            elif "clinical" in query.lower() or "research" in query.lower() or "trial" in query.lower():
                agent_name = "clinical_research"
            
            # Get the appropriate agent
            selected_agent = discovered_agents.get(agent_name)
            if not selected_agent:
                # Fallback to any available agent
                if discovered_agents:
                    agent_name, selected_agent = next(iter(discovered_agents.items()))
                else:
                    # No agents available, use fallback
                    return {
                        "success": False,
                        "formatted_summary": "No healthcare agents are currently available. Please try again later.",
                        "agent_name": "orchestrator",
                        "agents_used": [],
                    }
            
            logger.info(f"🎯 Selected agent: {agent_name}")
            
            # Create conclusive adapter for the selected agent
            conclusive_adapter = create_conclusive_agent_adapter(selected_agent, agent_name)
            
            # Call the agent through the conclusive adapter
            conclusive_result = await conclusive_adapter(query)
            
            logger.info(f"✅ Conclusive adapter completed for {agent_name}")
            
            # Extract agent result from "CONCLUSIVE ANSWER:" prefix if present
            if conclusive_result.startswith("CONCLUSIVE ANSWER: "):
                answer_content = conclusive_result[len("CONCLUSIVE ANSWER: "):]
            else:
                answer_content = conclusive_result
            
            # Try to get sources from the original agent call if available
            sources = []
            try:
                if hasattr(selected_agent, '_process_implementation'):
                    raw_result = await selected_agent._process_implementation({"query": query})
                    if isinstance(raw_result, dict) and "sources" in raw_result:
                        sources = raw_result["sources"]
            except Exception:
                pass
            
            # Build structured result
            result = {
                "success": True,
                "formatted_summary": answer_content,
                "agent_name": agent_name,
                "agents_used": [agent_name],
                "total_sources": len(sources),
                "search_query": query,
            }
            
            # Add citations if sources are available
            if sources:
                result["citations"] = sources
                # Append sources to formatted summary if requested
                display_sources = True if show_sources is None else bool(show_sources)
                if display_sources:
                    formatted = result.get("formatted_summary", "") or ""
                    lines = [formatted, "\n\nSources:"]
                    for c in sources[: self.citations_max_display]:
                        title = c.get("title") or c.get("name") or c.get("id") or "Source"
                        url = c.get("url") or c.get("link") or ""
                        src = c.get("source") or ""
                        bullet = f"- {title}"
                        if src:
                            bullet += f" ({src})"
                        if url:
                            bullet += f": {url}"
                        lines.append(bullet)
                    result["formatted_summary"] = "\n".join(lines).strip()
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in conclusive adapter processing: {e}")
            return {
                "success": False,
                "formatted_summary": f"I encountered an issue processing your request: {str(e)}",
                "error": str(e),
                "agent_name": "orchestrator",
                "agents_used": [],
            }

    def get_fallback_response(self) -> Dict[str, Any]:
        return {
            "success": False,
            "formatted_summary": "We couldn't complete the request right now. Please try again.",
            "agent_name": "Fallback",
            "agents_used": ["Fallback"],
        }

    def _extract_citations(self, intermediate_steps: Any) -> List[Dict[str, Any]]:
        """Extract citations from intermediate steps using the universal MCP parser."""
        try:
            return extract_citations_from_mcp_steps(intermediate_steps)
        except Exception:
            return []

    def _merge_citations(
        self, a: List[Dict[str, Any]], b: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        seen: set[Tuple[str, str]] = set()
        merged: List[Dict[str, Any]] = []
        for lst in (a, b):
            for c in lst:
                if not isinstance(c, dict):
                    continue
                title = str(c.get("title") or "").strip()
                url = str(c.get("url") or c.get("link") or "").strip()
                key = (title.lower(), url.lower())
                if key in seen:
                    continue
                seen.add(key)
                merged.append(c)
        return merged
