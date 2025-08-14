"""
Medical Literature Search API Router
Provides medical information search and literature review capabilities
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from agents.medical_search_agent.medical_search_agent import MedicalLiteratureSearchAssistant
from core.dependencies import get_llm_client, get_mcp_client
from core.medical.url_utils import generate_conversational_summary

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

        # Generate conversational response using LLM
        try:
            conversational_response = await search_assistant.generate_conversational_response(
                search_result=search_result,
                original_query=request.search_query
            )
        except Exception as llm_error:
            logger.warning(f"LLM conversational response failed, using utility fallback: {llm_error}")
            # Fallback to utility-based conversational summary
            conversational_response = generate_conversational_summary(
                search_result.information_sources,
                request.search_query
            )

        # Return conversational response for better user experience
        return {
            "response": conversational_response,
            "search_id": search_result.search_id,
            "total_sources": len(search_result.information_sources),
            "search_confidence": search_result.search_confidence,
            "generated_at": search_result.generated_at.isoformat(),
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
