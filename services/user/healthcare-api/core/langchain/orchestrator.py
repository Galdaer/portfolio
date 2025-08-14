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
        *,
        mcp_client: Any,
        chat_model: BaseChatModel,
        show_agent_header: bool = True,
        timeouts: Optional[Dict[str, float]] = None,
        always_run_medical_search: bool = True,
        presearch_max_results: int = 5,
        citations_max_display: int = 10,
    ) -> None:
        timeouts = timeouts or {}
        self.mcp_client = mcp_client
        self.always_run_medical_search = bool(always_run_medical_search)
        self.presearch_max_results = int(presearch_max_results)
        self.citations_max_display = int(citations_max_display)
        self.agent = HealthcareLangChainAgent(
            mcp_client,
            chat_model,
            show_agent_header=show_agent_header,
            per_agent_default_timeout=float(timeouts.get("per_agent_default", 30)),
            per_agent_hard_cap=float(timeouts.get("per_agent_hard_cap", 90)),
            tool_max_retries=int((timeouts.get("tool_max_retries", 2))),
            tool_retry_base_delay=float((timeouts.get("tool_retry_base_delay", 0.2))),
        )

    async def process(self, query: str, *, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            # Optional presearch to guarantee medical_search coverage
            pre_citations: List[Dict[str, Any]] = []
            if self.always_run_medical_search:
                try:
                    presearch_obs = await self.mcp_client.call_tool(
                        "search_pubmed", {"query": query, "max_results": self.presearch_max_results}
                    )

                    class _Action:
                        def __init__(self, tool: str) -> None:
                            self.tool = tool

                    # Reuse citation extractor by forming a single synthetic step
                    pre_citations = self._extract_citations([(_Action("search_medical_literature"), presearch_obs)])
                except Exception:
                    pre_citations = []

            result = await self.agent.process(query, context=context)

            # Always include which agents were used (default to medical_search)
            result.setdefault("agents_used", [result.get("agent_name", "medical_search")])

            # Extract citations/sources from intermediate tool calls and attach
            citations = self._extract_citations(result.get("intermediate_steps", []))
            if pre_citations:
                citations = self._merge_citations(pre_citations, citations)
            if citations:
                result["citations"] = citations
                # Append a human-readable sources section
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
        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"Orchestrator error: {e}")
            return self.get_fallback_response()

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
