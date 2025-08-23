"""
Universal MCP Response Parser for Healthcare Applications

This module provides standardized parsing for all MCP tool responses which follow
the universal structure: {"content": [{"type": "text", "text": "JSON_STRING"}]}

MEDICAL DISCLAIMER: This system provides administrative support for healthcare
data processing only. It does not provide medical advice, diagnosis, or treatment
recommendations. All medical decisions must be made by qualified healthcare professionals.
"""

import json
from typing import Any

from core.infrastructure.healthcare_logger import get_healthcare_logger

logger = get_healthcare_logger(__name__)


def parse_mcp_response(
    mcp_result: dict[str, Any],
    data_key: str = "articles",
    default_value: Any | None = None,
) -> list[dict[str, Any]] | dict[str, Any] | Any:
    """
    Universal MCP response parser for all healthcare tools.

    ALL MCP tools return: {"content": [{"type": "text", "text": "JSON_STRING"}]}
    Where JSON_STRING contains the actual data:
    - PubMed: '{"articles": [...]}'
    - Clinical Trials: '{"results": [...]}'
    - FDA: '{"results": [...]}'

    Args:
        mcp_result: Raw MCP response dictionary
        data_key: Key to extract from parsed JSON (e.g., "articles", "results")
        default_value: Value to return if parsing fails (defaults to empty list)

    Returns:
        Parsed data from the specified key, or default_value if parsing fails

    Examples:
        >>> pubmed_result = {"content": [{"type": "text", "text": '{"articles": [...]}'}]}
        >>> articles = parse_mcp_response(pubmed_result, "articles")

        >>> trials_result = {"content": [{"type": "text", "text": '{"results": [...]}'}]}
        >>> trials = parse_mcp_response(trials_result, "results")
    """
    if default_value is None:
        default_value = []

    try:
        # Check for valid MCP response structure
        if not isinstance(mcp_result, dict):
            logger.warning(f"MCP result is not a dictionary: {type(mcp_result)}")
            return default_value

        if not mcp_result.get("content"):
            logger.warning("MCP result missing 'content' field")
            return default_value

        if not isinstance(mcp_result["content"], list) or not len(mcp_result["content"]):
            logger.warning("MCP result 'content' is not a non-empty list")
            return default_value

        content_item = mcp_result["content"][0]
        if not isinstance(content_item, dict):
            logger.warning(f"Content item is not a dictionary: {type(content_item)}")
            return default_value

        if "text" not in content_item:
            logger.warning("Content item missing 'text' field")
            return default_value

        # Parse the JSON string to get actual data
        text_content = content_item["text"]
        if not isinstance(text_content, str):
            logger.warning(f"Text content is not a string: {type(text_content)}")
            return default_value

        try:
            data = json.loads(text_content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from text content: {e}")
            logger.debug(f"Raw text content: {text_content[:200]}...")
            return default_value

        # Extract the requested data key
        if not isinstance(data, dict):
            logger.warning(f"Parsed data is not a dictionary: {type(data)}")
            return data  # Return the parsed data as-is

        result = data.get(data_key, default_value)

        # Log successful parsing for debugging
        if isinstance(result, list):
            logger.info(
                f"Successfully parsed {len(result)} items from MCP response (key: {data_key})",
            )
        else:
            logger.info(f"Successfully parsed MCP response (key: {data_key}, type: {type(result)})")

        return result

    except Exception as e:
        logger.error(f"Unexpected error parsing MCP response: {e}")
        logger.debug(
            f"Raw MCP result keys: {list(mcp_result.keys()) if isinstance(mcp_result, dict) else 'not a dict'}",
        )
        return default_value


def parse_pubmed_response(mcp_result: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse PubMed MCP response to extract articles."""
    result = parse_mcp_response(mcp_result, "articles", [])
    return result if isinstance(result, list) else []


def parse_clinical_trials_response(mcp_result: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse Clinical Trials MCP response to extract trial results."""
    result = parse_mcp_response(mcp_result, "results", [])
    return result if isinstance(result, list) else []


def parse_fda_response(mcp_result: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse FDA MCP response to extract drug information."""
    result = parse_mcp_response(mcp_result, "results", [])
    return result if isinstance(result, list) else []


def debug_mcp_response_structure(mcp_result: dict[str, Any]) -> dict[str, Any]:
    """
    Debug helper to examine MCP response structure.

    Returns:
        Dictionary with structural analysis of the MCP response
    """
    analysis = {
        "is_dict": isinstance(mcp_result, dict),
        "top_level_keys": list(mcp_result.keys()) if isinstance(mcp_result, dict) else None,
        "has_content": "content" in mcp_result if isinstance(mcp_result, dict) else False,
        "content_type": None,
        "content_length": None,
        "first_item_keys": None,
        "text_preview": None,
        "json_parseable": False,
        "parsed_keys": None,
    }

    try:
        if isinstance(mcp_result, dict) and "content" in mcp_result:
            content = mcp_result["content"]
            analysis["content_type"] = type(content).__name__

            if isinstance(content, list):
                analysis["content_length"] = len(content)

                if len(content) > 0 and isinstance(content[0], dict):
                    analysis["first_item_keys"] = list(content[0].keys())

                    if "text" in content[0]:
                        text = content[0]["text"]
                        analysis["text_preview"] = text[:100] + "..." if len(text) > 100 else text

                        try:
                            parsed = json.loads(text)
                            analysis["json_parseable"] = True
                            if isinstance(parsed, dict):
                                analysis["parsed_keys"] = list(parsed.keys())
                        except:
                            pass

    except Exception as e:
        analysis["error"] = str(e)

    return analysis


# Enhanced citation extraction with MCP parsing
def extract_citations_from_mcp_steps(intermediate_steps: list[Any]) -> list[dict[str, Any]]:
    """
    Extract citations from LangChain intermediate steps with proper MCP parsing.

    Args:
        intermediate_steps: List of (action, observation) tuples from LangChain agent

    Returns:
        List of citation dictionaries with standardized fields
    """
    citations = []

    for step in intermediate_steps:
        try:
            if not isinstance(step, tuple) or len(step) != 2:
                continue

            action, observation = step

            # Get tool name
            tool_name = getattr(action, "tool", "") or str(action)

            # Parse observation based on tool type
            if "pubmed" in tool_name.lower() or "medical" in tool_name.lower():
                articles = parse_pubmed_response(observation)
                for article in articles:
                    citations.append(
                        {
                            "title": article.get("title", "Unknown Title"),
                            "source": "PubMed",
                            "url": article.get("url") or article.get("link", ""),
                            "id": article.get("pmid") or article.get("id", ""),
                            "authors": article.get("authors", []),
                            "journal": article.get("journal", ""),
                            "year": article.get("year", ""),
                            "tool": tool_name,
                        },
                    )

            elif "trial" in tool_name.lower():
                trials = parse_clinical_trials_response(observation)
                for trial in trials:
                    citations.append(
                        {
                            "title": trial.get("title", "Unknown Trial"),
                            "source": "ClinicalTrials.gov",
                            "url": trial.get("url") or trial.get("link", ""),
                            "id": trial.get("nct_id") or trial.get("id", ""),
                            "status": trial.get("status", ""),
                            "phase": trial.get("phase", ""),
                            "tool": tool_name,
                        },
                    )

            elif "fda" in tool_name.lower() or "drug" in tool_name.lower():
                drugs = parse_fda_response(observation)
                for drug in drugs:
                    citations.append(
                        {
                            "title": drug.get("name", "Unknown Drug"),
                            "source": "FDA",
                            "url": drug.get("url") or drug.get("link", ""),
                            "id": drug.get("application_number") or drug.get("id", ""),
                            "approval_date": drug.get("approval_date", ""),
                            "indication": drug.get("indication", ""),
                            "tool": tool_name,
                        },
                    )

        except Exception as e:
            logger.error(f"Error extracting citations from step: {e}")
            continue

    logger.info(f"Extracted {len(citations)} citations from {len(intermediate_steps)} steps")
    return citations
