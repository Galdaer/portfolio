"""
Agent-First LangChain Tools for Healthcare

Provides healthcare agent tools as the primary interface, with MCP tools
as fallback only. All medical queries should go through specialized agents.

Architecture:
- Primary: Route to specialized healthcare agents
- Fallback: Direct MCP tool calls if agent unavailable
- Focus: Medical search agent (only fully implemented agent)
"""
from __future__ import annotations

from typing import Any, List
import asyncio
import json

from pydantic import BaseModel, Field
from langchain.tools import StructuredTool
from core.infrastructure.healthcare_logger import get_healthcare_logger

logger = get_healthcare_logger("core.langchain.healthcare_tools")


# Input schemas for agent tools
class MedicalSearchInput(BaseModel):
    """Input for medical literature search queries."""
    query: str = Field(description="Medical research or literature search question")


class HealthcareQueryInput(BaseModel):
    """Input for general healthcare queries."""
    query: str = Field(description="Healthcare-related question or request")


# Input schemas for MCP fallback tools
class PubMedSearchInput(BaseModel):
    """Input for PubMed search (MCP fallback)."""
    query: str = Field(description="Medical literature search query")
    max_results: int = Field(default=10, description="Maximum number of results")


class ClinicalTrialsInput(BaseModel):
    """Input for clinical trials search (MCP fallback)."""
    query: str = Field(description="Clinical trials search query")
    max_results: int = Field(default=5, description="Maximum number of results")


class DrugInfoInput(BaseModel):
    """Input for drug information (MCP fallback)."""
    drug_name: str = Field(description="Name of drug or medication")


def create_healthcare_tools(mcp_client: Any, agent_manager: Any, *, max_retries: int = 2) -> List[StructuredTool]:
    """Create healthcare tools with agent-first architecture.
    
    Args:
        mcp_client: MCP client (used by agents internally and for fallback)
        agent_manager: Healthcare agent manager (primary interface)
        max_retries: Maximum retries for tool calls
        
    Returns:
        List of StructuredTool instances prioritizing healthcare agents
    """
    
    tools: List[StructuredTool] = []
    
    # Agent-first tools (primary interface)
    if agent_manager:
        
        def search_medical_literature_agent(query: str) -> str:
            """Search medical literature using the medical search agent.
            
            This is the primary tool for medical literature searches.
            Routes to the specialized medical search agent.
            """
            try:
                # Get medical search agent (only fully implemented agent)
                agent = agent_manager.get_agent("medical_search")
                if agent and hasattr(agent, 'process_query'):
                    logger.info(f"🔍 Routing medical search to agent: {query[:100]}")
                    # Use asyncio.run since agent.process_query is async
                    result = asyncio.run(agent.process_query(query))
                    if isinstance(result, dict):
                        return json.dumps(result, indent=2)
                    return str(result)
                else:
                    # Fallback to MCP if agent not available
                    logger.warning("Medical search agent not available, falling back to MCP")
                    return _fallback_pubmed_search(mcp_client, query)
            except Exception as e:
                logger.error(f"Medical search agent error: {e}")
                return _fallback_pubmed_search(mcp_client, query)

        def healthcare_query_router(query: str) -> str:
            """Route general healthcare queries to appropriate agents.
            
            Analyzes the query and routes to the best available agent.
            Currently focuses on medical search since it's the only fully implemented agent.
            """
            try:
                # Simple query analysis for routing
                medical_keywords = ['medication', 'drug', 'treatment', 'research', 'study', 'clinical', 'disease', 'condition']
                query_lower = query.lower()
                
                # Check if it's a medical literature query
                if any(keyword in query_lower for keyword in medical_keywords):
                    logger.info(f"🔍 Routing to medical search agent: {query[:50]}...")
                    return search_medical_literature_agent(query)
                
                # For other queries, try medical search as fallback (since it's the only working agent)
                logger.info(f"🔄 Using medical search as general healthcare agent: {query[:50]}...")
                return search_medical_literature_agent(query)
                
            except Exception as e:
                logger.error(f"Healthcare query router error: {e}")
                return f"Error processing healthcare query: {str(e)}"

        # Add agent-first tools
        tools.extend([
            StructuredTool.from_function(
                func=search_medical_literature_agent,
                name="search_medical_literature",
                description="Search medical literature and research using the medical search agent. Use for questions about drugs, treatments, diseases, clinical studies, or medical research.",
                args_schema=MedicalSearchInput,
            ),
            StructuredTool.from_function(
                func=healthcare_query_router,
                name="healthcare_query",
                description="General healthcare query router. Analyzes the query and routes to the appropriate healthcare agent.",
                args_schema=HealthcareQueryInput,
            ),
        ])
    
    # MCP fallback tools (direct MCP access)
    def _fallback_pubmed_search(client: Any, query: str, max_results: int = 10) -> str:
        """Fallback PubMed search using direct MCP call."""
        try:
            logger.info(f"🔄 MCP fallback - PubMed search: {query[:50]}...")
            result = asyncio.run(client.call_tool("search-pubmed", {
                "query": query,
                "max_results": max_results
            }))
            return json.dumps(result, indent=2) if result else "No results found"
        except Exception as e:
            logger.error(f"MCP PubMed search error: {e}")
            return f"Search error: {str(e)}"

    def pubmed_search_fallback(query: str, max_results: int = 10) -> str:
        """Direct PubMed search (fallback when agent unavailable)."""
        return _fallback_pubmed_search(mcp_client, query, max_results)

    def clinical_trials_search(query: str, max_results: int = 5) -> str:
        """Search clinical trials database."""
        try:
            logger.info(f"🔍 Clinical trials search: {query[:50]}...")
            result = asyncio.run(mcp_client.call_tool("search-clinical-trials", {
                "query": query,
                "max_results": max_results
            }))
            return json.dumps(result, indent=2) if result else "No clinical trials found"
        except Exception as e:
            logger.error(f"Clinical trials search error: {e}")
            return f"Clinical trials search error: {str(e)}"

    def drug_information_lookup(drug_name: str) -> str:
        """Look up drug information and interactions."""
        try:
            logger.info(f"🔍 Drug info lookup: {drug_name}")
            result = asyncio.run(mcp_client.call_tool("get-drug-info", {
                "drug_name": drug_name
            }))
            return json.dumps(result, indent=2) if result else f"No information found for {drug_name}"
        except Exception as e:
            logger.error(f"Drug info lookup error: {e}")
            return f"Drug information error: {str(e)}"

    # Add MCP fallback tools
    tools.extend([
        StructuredTool.from_function(
            func=pubmed_search_fallback,
            name="pubmed_search_direct",
            description="Direct PubMed search (fallback). Use only if medical search agent is unavailable.",
            args_schema=PubMedSearchInput,
        ),
        StructuredTool.from_function(
            func=clinical_trials_search,
            name="search_clinical_trials",
            description="Search clinical trials database for ongoing and completed studies.",
            args_schema=ClinicalTrialsInput,
        ),
        StructuredTool.from_function(
            func=drug_information_lookup,
            name="get_drug_information",
            description="Get detailed drug information including interactions and side effects.",
            args_schema=DrugInfoInput,
        ),
    ])
    
    logger.info(f"✅ Created {len(tools)} healthcare tools (agent-first architecture)")
    return tools
