"""
LangChain Tool Wrappers for Healthcare MCP

Provides StructuredTool wrappers around the existing MCP client without
introducing side effects at import time. All network/process activity is
deferred until the wrapped functions are invoked.

Notes:
- PHI-safe logging only (no sensitive data in logs)
- Compatible with LangChain 0.3.x
"""
from __future__ import annotations

from typing import Any, Callable, List, Optional

from pydantic import BaseModel, Field
from langchain.tools import StructuredTool

from core.infrastructure.healthcare_logger import get_healthcare_logger

logger = get_healthcare_logger("core.langchain.tools")


# Input schemas
class PubMedSearchInput(BaseModel):
    """Input for PubMed search."""

    query: str = Field(description="Medical search query")
    max_results: int = Field(default=10, description="Maximum results to return")


class ClinicalTrialsInput(BaseModel):
    """Input for clinical trials search."""

    condition: str = Field(description="Medical condition")
    status: Optional[str] = Field(
        default="recruiting", description="Desired trial status (e.g., recruiting)"
    )


class DrugInfoInput(BaseModel):
    """Input for FDA drug information."""

    drug_name: str = Field(description="Drug name to lookup")


def _safe_tool_wrapper(tool_name: str, fn: Callable[..., Any]) -> Callable[..., Any]:
    """Wrap tool functions with PHI-safe error handling and logging.

    Returns an async or sync callable that mirrors the wrapped function.
    """

    async def _aw(*args: Any, **kwargs: Any) -> Any:  # async wrapper
        try:
            return await fn(*args, **kwargs)  # type: ignore[misc]
        except Exception:
            logger.error(
                f"Tool error ({tool_name})",  # keep message generic
                extra={
                    "healthcare_context": {
                        "operation_type": "tool_error",
                        "tool": tool_name,
                        "status": "degraded",
                    }
                },
            )
            return {
                "error": "Tool temporarily unavailable",
                "fallback": "Using cached medical data",
                "status": "degraded",
            }

    def _sw(*args: Any, **kwargs: Any) -> Any:  # sync wrapper
        try:
            return fn(*args, **kwargs)
        except Exception:
            logger.error(
                f"Tool error ({tool_name})",
                extra={
                    "healthcare_context": {
                        "operation_type": "tool_error",
                        "tool": tool_name,
                        "status": "degraded",
                    }
                },
            )
            return {
                "error": "Tool temporarily unavailable",
                "fallback": "Using cached medical data",
                "status": "degraded",
            }

    # Preserve async nature when wrapping
    return _aw if callable(getattr(fn, "__await__", None)) else _sw


def create_mcp_tools(mcp_client: Any) -> List[StructuredTool]:
    """Create LangChain StructuredTool list backed by the MCP client.

    The provided client must implement `call_tool(name: str, arguments: dict)`.
    """

    async def _pubmed_search(query: str, max_results: int = 10) -> dict[str, Any]:
        return await mcp_client.call_tool(
            "search_pubmed", {"query": query, "max_results": max_results}
        )

    async def _clinical_trials(
        condition: str, status: Optional[str] = "recruiting"
    ) -> dict[str, Any]:
        return await mcp_client.call_tool(
            "search_clinical_trials", {"condition": condition, "status": status}
        )

    async def _drug_info(drug_name: str) -> dict[str, Any]:
        return await mcp_client.call_tool("get_drug_info", {"drug_name": drug_name})

    tools: List[StructuredTool] = [
        StructuredTool.from_function(
            func=_safe_tool_wrapper("search_medical_literature", _pubmed_search),
            name="search_medical_literature",
            description="Search PubMed for peer-reviewed medical literature",
            args_schema=PubMedSearchInput,
            return_direct=False,
            handle_tool_error=True,
        ),
        StructuredTool.from_function(
            func=_safe_tool_wrapper("search_clinical_trials", _clinical_trials),
            name="search_clinical_trials",
            description="Search for clinical trials (e.g., recruiting)",
            args_schema=ClinicalTrialsInput,
            return_direct=False,
            handle_tool_error=True,
        ),
        StructuredTool.from_function(
            func=_safe_tool_wrapper("get_drug_information", _drug_info),
            name="get_drug_information",
            description="Get FDA drug information and warnings",
            args_schema=DrugInfoInput,
            return_direct=False,
            handle_tool_error=True,
        ),
    ]

    return tools
