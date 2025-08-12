"""
Medical Literature Search API Router
Provides medical information search and literature review capabilities
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from agents.search_agent.search_agent import MedicalLiteratureSearchAssistant
from core.dependencies import get_llm_client, get_mcp_client

logger = logging.getLogger(__name__)

router = APIRouter()


class SearchRequest(BaseModel):
    """Medical literature search request model"""

    search_query: str = Field(..., description="Medical literature search query")
    search_context: dict[str, Any] = Field(
        default_factory=dict, description="Additional search context",
    )
    session_id: str = Field(default="default", description="Session identifier")

    class Config:
        json_schema_extra = {
            "example": {
                "search_query": "diabetes management guidelines 2024",
                "search_context": {"focus": "type_2_diabetes", "patient_age": "adult"},
                "session_id": "search_session_001",
            },
        }


@router.post("/search-literature")
async def search_medical_literature(
    request: SearchRequest,
    mcp_client: Any = Depends(get_mcp_client),
    llm_client: Any = Depends(get_llm_client),
) -> dict[str, Any]:
    """
    Search medical literature like a medical librarian

    Returns information about medical concepts, not diagnoses.
    
    MEDICAL DISCLAIMER: This provides educational information only,
    not medical advice, diagnosis, or treatment recommendations.
    """
    try:
        # Initialize search assistant
        search_assistant = MedicalLiteratureSearchAssistant(
            mcp_client=mcp_client,
            llm_client=llm_client,
        )

        # Perform literature search
        search_result = await search_assistant.search_medical_literature(
            search_query=request.search_query,
            search_context=request.search_context,
        )

        # Convert dataclass to dict for JSON response
        return {
            "search_id": search_result.search_id,
            "search_query": search_result.search_query,
            "information_sources": search_result.information_sources,
            "related_conditions": search_result.related_conditions,
            "drug_information": search_result.drug_information,
            "clinical_references": search_result.clinical_references,
            "search_confidence": search_result.search_confidence,
            "disclaimers": search_result.disclaimers,
            "source_links": search_result.source_links,
            "generated_at": search_result.generated_at.isoformat(),
            "total_sources": len(search_result.information_sources),
        }

    except Exception as e:
        logger.exception(f"Literature search error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Literature search failed: {str(e)}",
        )


@router.get("/health")
async def search_health_check() -> dict[str, Any]:
    """Health check for medical literature search services"""
    return {
        "status": "healthy",
        "service": "medical_literature_search",
        "capabilities": [
            "literature_search",
            "medical_information_lookup",
            "condition_information",
            "drug_information",
        ],
        "disclaimer": "Educational information only - not medical advice",
    }
