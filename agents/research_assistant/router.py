"""
Research Assistant API Router
Provides medical literature search and clinical research capabilities
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from agents.research_assistant.clinical_research_agent import ClinicalResearchAgent
from agents.research_assistant.search_assistant import MedicalLiteratureSearchAssistant

logger = logging.getLogger(__name__)

router = APIRouter()


class ResearchRequest(BaseModel):
    """Research request model with healthcare compliance"""

    query: str = Field(..., description="Medical research query")
    query_type: str = Field(
        default="general_inquiry",
        description="Type of research: general_inquiry, differential_diagnosis, drug_interaction, literature_research",
    )
    clinical_context: dict[str, Any] = Field(
        default_factory=dict, description="Clinical context for the research"
    )
    session_id: str = Field(default="default", description="Session identifier")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "What does current literature say about hypertension management?",
                "query_type": "literature_research",
                "clinical_context": {"specialty": "cardiology"},
                "session_id": "research_session_001",
            }
        }


class LiteratureSearchRequest(BaseModel):
    """Literature search request model"""

    search_query: str = Field(..., description="Medical literature search query")
    search_context: dict[str, Any] = Field(
        default_factory=dict, description="Additional search context"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "search_query": "diabetes management guidelines 2024",
                "search_context": {"focus": "type_2_diabetes", "patient_age": "adult"},
            }
        }


async def get_mcp_client() -> Any:
    """Get MCP client (placeholder for dependency injection)"""
    # TODO: Replace with actual MCP client dependency
    return None


async def get_llm_client() -> Any:
    """Get LLM client (placeholder for dependency injection)"""
    # TODO: Replace with actual LLM client dependency
    return None


@router.post("/clinical-research")
async def clinical_research(
    request: ResearchRequest,
    mcp_client: Any = Depends(get_mcp_client),
    llm_client: Any = Depends(get_llm_client),
) -> dict[str, Any]:
    """
    Perform clinical research with enhanced agentic RAG capabilities

    MEDICAL DISCLAIMER: This provides educational information only,
    not medical advice, diagnosis, or treatment recommendations.
    """
    try:
        # Initialize clinical research agent
        agent = ClinicalResearchAgent(
            mcp_client=mcp_client,
            llm_client=llm_client,
            max_steps=50,
        )

        # Process research request
        result = await agent._process_implementation(request.model_dump())

        # Add standard healthcare disclaimers
        result["disclaimers"] = result.get("disclaimers", []) + [
            "This information is for educational purposes only and is not medical advice.",
            "Always consult with qualified healthcare professionals for medical decisions.",
            "In case of emergency, contact emergency services immediately.",
        ]

        return result

    except Exception as e:
        logger.error(f"Clinical research error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Research processing failed: {str(e)}",
        )


@router.post("/literature-search")
async def literature_search(
    request: LiteratureSearchRequest,
    mcp_client: Any = Depends(get_mcp_client),
    llm_client: Any = Depends(get_llm_client),
) -> dict[str, Any]:
    """
    Search medical literature like a medical librarian

    Returns information about medical concepts, not diagnoses.
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
        logger.error(f"Literature search error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Literature search failed: {str(e)}",
        )


@router.get("/health")
async def research_health_check() -> dict[str, Any]:
    """Health check for research assistant services"""
    return {
        "status": "healthy",
        "service": "research_assistant",
        "capabilities": [
            "clinical_research",
            "literature_search",
            "differential_diagnosis",
            "drug_interaction_analysis",
        ],
        "disclaimer": "Educational information only - not medical advice",
    }
