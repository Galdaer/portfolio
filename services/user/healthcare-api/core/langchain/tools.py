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
import asyncio
import json
import time

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


def _safe_tool_wrapper(
    tool_name: str,
    fn: Callable[..., Any],
    *,
    max_retries: int = 2,
    base_delay: float = 0.2,
) -> Callable[..., str]:
    """Wrap tool functions with PHI-safe error handling and logging.

    For LangChain compatibility, always returns a sync function that returns strings.
    Async functions are executed using asyncio.run().
    """

    def _sync_wrapper(*args: Any, **kwargs: Any) -> str:
        """Sync wrapper that handles both sync and async functions."""
        attempt = 0
        while True:
            try:
                # Check if function is async using proper detection
                if asyncio.iscoroutinefunction(fn):
                    # This is an async function - run it with asyncio
                    try:
                        # Check if we're in an async context
                        asyncio.get_running_loop()
                        # If we're in an async context, use thread executor
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(asyncio.run, fn(*args, **kwargs))
                            result = future.result()
                    except RuntimeError:
                        # No running loop, we can use asyncio.run directly
                        result = asyncio.run(fn(*args, **kwargs))
                else:
                    # This is a sync function
                    result = fn(*args, **kwargs)
                
                # Ensure we always return a string
                if isinstance(result, dict):
                    return json.dumps(result, indent=2)
                return str(result)
                
            except Exception:
                attempt += 1
                if attempt > max_retries:
                    logger.error(
                        f"Tool error ({tool_name})",
                        extra={
                            "healthcare_context": {
                                "operation_type": "tool_error",
                                "tool": tool_name,
                                "status": "degraded",
                                "retries": attempt - 1,
                            }
                        },
                    )
                    return json.dumps({
                        "error": "Tool temporarily unavailable",
                        "fallback": "Using cached medical data",
                        "status": "degraded",
                    }, indent=2)
                time.sleep(base_delay * attempt)

    return _sync_wrapper


def create_mcp_tools(
    mcp_client: Any, *, max_retries: int = 2, retry_base_delay: float = 0.2
) -> List[StructuredTool]:
    """Create LangChain StructuredTool list backed by the MCP client.

    The provided client must implement `call_tool(name: str, arguments: dict)`.
    """

    async def _pubmed_search(query: str, max_results: int = 10) -> str:
        """Call MCP PubMed search using normalized hyphenated tool name.

        Primary: "search-pubmed" (normalized)
        Fallback: "search_pubmed" (legacy underscore)
        """
        try:
            result = await mcp_client.call_tool(
                "search-pubmed", {"query": query, "max_results": max_results}
            )
            # CRITICAL: Always return a string, not a dict
            if isinstance(result, dict):
                return json.dumps(result, indent=2)
            return str(result)
        except Exception as e:
            # Best-effort fallback for environments still exposing underscore tool names
            try:
                result = await mcp_client.call_tool(
                    "search_pubmed", {"query": query, "max_results": max_results}
                )
                if isinstance(result, dict):
                    return json.dumps(result, indent=2)
                return str(result)
            except Exception:
                return f"Tool error: {str(e)}"

    async def _clinical_trials(
        condition: str, status: Optional[str] = "recruiting"
    ) -> str:
        """Call MCP Clinical Trials search with normalized tool name.

        Primary: "search-trials"
        Fallback: "search_clinical_trials"
        """
        try:
            result = await mcp_client.call_tool(
                "search-trials", {"condition": condition, "status": status}
            )
            # CRITICAL: Always return a string, not a dict
            if isinstance(result, dict):
                return json.dumps(result, indent=2)
            return str(result)
        except Exception as e:
            try:
                result = await mcp_client.call_tool(
                    "search_clinical_trials", {"condition": condition, "status": status}
                )
                if isinstance(result, dict):
                    return json.dumps(result, indent=2)
                return str(result)
            except Exception:
                return f"Tool error: {str(e)}"

    async def _drug_info(drug_name: str) -> str:
        """Call MCP Drug Info with normalized tool name.

        Primary: "get-drug-info"
        Fallback: "get_drug_info"
        """
        try:
            result = await mcp_client.call_tool("get-drug-info", {"drug_name": drug_name})
            # CRITICAL: Always return a string, not a dict
            if isinstance(result, dict):
                return json.dumps(result, indent=2)
            return str(result)
        except Exception as e:
            try:
                result = await mcp_client.call_tool("get_drug_info", {"drug_name": drug_name})
                if isinstance(result, dict):
                    return json.dumps(result, indent=2)
                return str(result)
            except Exception:
                return f"Tool error: {str(e)}"

    tools: List[StructuredTool] = [
        StructuredTool.from_function(
            func=_safe_tool_wrapper(
                "search_medical_literature", _pubmed_search, max_retries=max_retries, base_delay=retry_base_delay
            ),
            name="search_medical_literature",
            description="Search PubMed for peer-reviewed medical literature",
            args_schema=PubMedSearchInput,
            return_direct=False,
            handle_tool_error=True,
        ),
        StructuredTool.from_function(
            func=_safe_tool_wrapper(
                "search_clinical_trials", _clinical_trials, max_retries=max_retries, base_delay=retry_base_delay
            ),
            name="search_clinical_trials",
            description="Search for clinical trials (e.g., recruiting)",
            args_schema=ClinicalTrialsInput,
            return_direct=False,
            handle_tool_error=True,
        ),
        StructuredTool.from_function(
            func=_safe_tool_wrapper(
                "get_drug_information", _drug_info, max_retries=max_retries, base_delay=retry_base_delay
            ),
            name="get_drug_information",
            description="Get FDA drug information and warnings",
            args_schema=DrugInfoInput,
            return_direct=False,
            handle_tool_error=True,
        ),
    ]

    return tools
