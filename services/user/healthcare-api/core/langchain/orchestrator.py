"""
Minimal LangChain Orchestrator façade.

Initial version wires a single HealthcareLangChainAgent. Routing and
parallel helpers can be added in subsequent iterations.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from langchain_core.language_models import BaseChatModel

from core.infrastructure.healthcare_logger import get_healthcare_logger
from core.langchain.agents import HealthcareLangChainAgent

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
        max_iterations: int = 3,
        memory_max_token_limit: int = 2000,
        always_run_medical_search: bool = True,
        presearch_max_results: int = 5,
        citations_max_display: int = 10,
        tool_max_retries: int = 2,
        tool_retry_base_delay: float = 0.5,
        show_sources_default: bool = True,
        timeouts: Optional[Dict[str, float]] = None,
        show_agent_header: Optional[bool] = None,
    ):
        """Initialize the LangChain orchestrator for healthcare queries.

        Args:
            mcp_client: MCP client for tool execution
            model: Ollama model name
            temperature: LLM temperature for response generation
            verbose: Enable verbose logging
            max_iterations: Maximum agent iterations
            memory_max_token_limit: Maximum tokens for conversation memory
            always_run_medical_search: Always run medical search presearch
            presearch_max_results: Maximum results for presearch
            citations_max_display: Maximum citations to display
            tool_max_retries: Maximum retries for tool calls
            tool_retry_base_delay: Base delay between tool retries
            show_sources_default: Default value for showing sources
        """
        self.mcp_client = mcp_client
        self.always_run_medical_search = always_run_medical_search
        self.presearch_max_results = presearch_max_results
        self.citations_max_display = citations_max_display
        self.show_sources_default = show_sources_default

        # Initialize the LangChain agent with correct parameters
        self.agent = HealthcareLangChainAgent(
            mcp_client=mcp_client,
            chat_model=chat_model,
            model=model,
            temperature=temperature,
            verbose=verbose,
            max_iterations=max_iterations,
            memory_max_token_limit=memory_max_token_limit,
            tool_max_retries=tool_max_retries,
            tool_retry_base_delay=tool_retry_base_delay,
        )

        # Apply optional runtime settings
        if show_agent_header is not None:
            try:
                setattr(self.agent, "show_agent_header", bool(show_agent_header))
            except Exception:
                pass
        if isinstance(timeouts, dict):
            try:
                if "per_agent_default" in timeouts:
                    setattr(self.agent, "per_agent_default_timeout", float(timeouts["per_agent_default"]))
                if "per_agent_hard_cap" in timeouts:
                    setattr(self.agent, "per_agent_hard_cap", float(timeouts["per_agent_hard_cap"]))
            except Exception:
                # Best-effort; keep defaults if casting fails
                pass

    async def process(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        show_sources: Optional[bool] = None
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
                    pre_citations = self._extract_citations([(_Action("search_medical_literature"), presearch_obs)])
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
                "agents_used": []
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
                    "agents_used": []
                }
            else:
                return {
                    "success": False,
                    "formatted_summary": f"I encountered an issue processing your request: {error_msg}",
                    "error": error_msg,
                    "agent_name": "orchestrator",
                    "agents_used": []
                }

    def get_fallback_response(self) -> Dict[str, Any]:
        return {
            "success": False,
            "formatted_summary": "We couldn't complete the request right now. Please try again.",
            "agent_name": "Fallback",
            "agents_used": ["Fallback"],
        }

    def _extract_citations(self, intermediate_steps: Any) -> List[Dict[str, Any]]:
        """Best-effort extraction of citations from tool observations.

        Handles common shapes like:
        - observation = {"citations": [...]}  # preferred
        - observation = {"results": [{"title": ..., "url"|"link": ...}, ...]}
        - observation = [{"title": ..., "url": ...}, ...]
        """
        citations: List[Dict[str, Any]] = []
        try:
            steps = intermediate_steps or []
            for step in steps:
                # step may be (action, observation)
                if not isinstance(step, (list, tuple)) or len(step) < 2:
                    continue
                action, observation = step[0], step[1]
                tool_name = getattr(action, "tool", None) or "medical_search"

                # Normalize observation into iterable of items
                items: List[Any] = []
                if isinstance(observation, dict):
                    if isinstance(observation.get("citations"), list):
                        items = observation.get("citations")  # type: ignore[assignment]
                    elif isinstance(observation.get("results"), list):
                        items = observation.get("results")  # type: ignore[assignment]
                    elif isinstance(observation.get("content"), list):
                        items = observation.get("content")  # type: ignore[assignment]
                    else:
                        items = [observation]
                elif isinstance(observation, list):
                    items = observation
                else:
                    # unsupported shape, skip
                    continue

                for it in items:
                    if not isinstance(it, dict):
                        continue
                    title = it.get("title") or it.get("name") or it.get("id")
                    url = it.get("url") or it.get("link")
                    if not (title or url):
                        # Look inside nested structures
                        meta = it.get("metadata") if isinstance(it.get("metadata"), dict) else {}
                        title = title or (meta.get("title") if isinstance(meta, dict) else None)
                        url = url or (meta.get("url") if isinstance(meta, dict) else None)
                    if title or url:
                        citations.append({"title": title or "Source", "url": url or "", "source": tool_name})
        except Exception:  # pragma: no cover - defensive
            return citations
        return citations

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
