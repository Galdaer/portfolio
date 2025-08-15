"""
Agent-First LangChain Tools for Healthcare

Provides healthcare agent tools as the primary interface, with MCP tools
as fallback only. All medical queries should go through specialized agents.

Architecture:
- Primary: Route to specialized healthcare agents via adapters
- Fallback: Direct MCP tool calls if agent unavailable
- Focus: Agent adapter pattern for proper routing and logging

UPDATED: Now uses agent_adapters.py for proper agent routing!
"""
from __future__ import annotations

from typing import Any, List, Callable
import asyncio
import json

from pydantic import BaseModel, Field
from langchain.tools import StructuredTool

from core.infrastructure.healthcare_logger import get_healthcare_logger
from core.tools import tool_registry
from core.langchain.agent_adapters import create_healthcare_agent_adapters, create_general_healthcare_router

logger = get_healthcare_logger("core.langchain.healthcare_tools")

# Optional database import - gracefully handle missing dependencies
try:
    from core.database.medical_db import get_medical_db
    # Test database connection on import
    db_instance = get_medical_db()
    status = db_instance.get_database_status()
    DATABASE_AVAILABLE = status.get("database_available", False)
    logger.info(f"🔗 Database availability: {DATABASE_AVAILABLE}")
except Exception as e:
    logger.warning(f"🔄 Database not available, will use external APIs only: {e}")
    DATABASE_AVAILABLE = False
    get_medical_db = None


def safe_async_call(coro):
    """
    Safely execute an async coroutine from sync context.
    
    Handles the case where we're already in an event loop by using
    different execution strategies.
    """
    try:
        # Try to get the current event loop
        asyncio.get_running_loop()
        # If we're in a running loop, we can't use asyncio.run()
        # Instead, we need to use a different approach
        import concurrent.futures
        import threading
        
        def run_in_thread():
            # Create a new event loop in a separate thread
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(coro)
            finally:
                new_loop.close()
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            return future.result(timeout=30)  # 30 second timeout
            
    except RuntimeError:
        # No event loop running, safe to use asyncio.run()
        return asyncio.run(coro)
    except Exception as e:
        logger.error(f"Failed to execute async call: {e}")
        raise


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
    """Create healthcare tools with agent-first architecture using adapters.
    
    This is the NEW implementation that uses the adapter pattern to route
    LangChain calls through existing healthcare agents, ensuring proper
    agent logging and compliance.
    
    Args:
        mcp_client: MCP client (used by agents internally and for fallback)
        agent_manager: Healthcare agent manager with discovered agents
        max_retries: Maximum retries for tool calls
        
    Returns:
        List of StructuredTool instances that route to healthcare agents
    """
    
    # Initialize ToolRegistry with MCP client for robust tool management
    try:
        if not tool_registry._initialized:
            logger.info("🔄 Initializing ToolRegistry with MCP client...")
            safe_async_call(tool_registry.initialize(mcp_client))
            logger.info("✅ ToolRegistry initialized successfully")
        else:
            logger.info("✅ ToolRegistry already initialized")
    except Exception as e:
        logger.warning(f"⚠️ ToolRegistry initialization failed, using direct MCP fallback: {e}")
    
    tools: List[StructuredTool] = []
    
    # AGENT-FIRST ARCHITECTURE: Use agent adapters for primary routing
    if agent_manager and hasattr(agent_manager, 'agents'):
        discovered_agents = agent_manager.agents
        logger.info(f"🔧 Creating agent adapters for {len(discovered_agents)} agents: {list(discovered_agents.keys())}")
        
        # Create individual agent adapters (medical_search_agent, intake_agent, etc.)
        agent_tools = create_healthcare_agent_adapters(discovered_agents)
        tools.extend(agent_tools)
        
        # Create general healthcare router for intelligent routing
        router_tool = create_general_healthcare_router(discovered_agents)
        tools.append(router_tool)
        
        logger.info(f"✅ Created {len(tools)} agent-based healthcare tools")
        
    else:
        logger.warning("⚠️ No agent_manager or agents found, falling back to MCP-only tools")
        # Fallback to original MCP-based tools if agents not available
        tools.extend(_create_mcp_fallback_tools(mcp_client, max_retries))
    
    return tools


def _create_mcp_fallback_tools(mcp_client: Any, max_retries: int) -> List[StructuredTool]:
    """Create fallback MCP tools when agents are not available."""
    logger.warning("🔄 Creating MCP fallback tools (agents not available)")
    
    def pubmed_search_fallback(query: str, max_results: int = 10) -> str:
        """Direct PubMed search (fallback when agent unavailable)."""
        return _fallback_pubmed_search(mcp_client, query, max_results)

    def clinical_trials_search(query: str, max_results: int = 5) -> str:
        """Clinical trials search via MCP."""
        try:
            if tool_registry._initialized:
                result = safe_async_call(tool_registry.execute_tool("search-clinical-trials", {
                    "query": query,
                    "max_results": max_results
                }))
            else:
                result = safe_async_call(mcp_client.call_tool("search-clinical-trials", {
                    "query": query,
                    "max_results": max_results
                }))
            return json.dumps(result, indent=2) if result else "No clinical trials found"
        except Exception as e:
            logger.exception(f"Clinical trials search error: {e}")
            return f"Search error: {str(e)}"

    return [
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
    ]


# MCP fallback tools (direct MCP access)
def _fallback_pubmed_search(client: Any, query: str, max_results: int = 10) -> str:
        """Database-first PubMed search with external API fallback."""
        try:
            # STEP 1: Try local database first (if available)
            logger.info(f"🗃️ Searching local PubMed database first: {query[:50]}...")
            
            if DATABASE_AVAILABLE and get_medical_db:
                medical_db = get_medical_db()
                local_results = medical_db.search_pubmed_local(query, max_results)
                
                if local_results:
                    logger.info(f"✅ Found {len(local_results)} articles in local database")
                    return json.dumps({"results": local_results, "source": "local_database"})
            else:
                logger.info("🔄 Database not available, using external API only")
            
            # STEP 2: If no local results, fallback to external API
            logger.warning(f"📡 No local results found, using external PubMed API: {query[:50]}...")
            
            # Try ToolRegistry first (robust tool management)
            if tool_registry._initialized:
                result = safe_async_call(tool_registry.execute_tool("search-pubmed", {
                    "query": query,
                    "max_results": max_results
                }))
                logger.info("✅ Used ToolRegistry for external PubMed search")
            else:
                # Fallback to direct MCP call if ToolRegistry unavailable
                logger.warning("⚠️ ToolRegistry not available, using direct MCP")
                result = safe_async_call(client.call_tool("search-pubmed", {
                    "query": query,
                    "max_results": max_results
                }))
                
            return json.dumps(result, indent=2) if result else "No results found"
        except Exception as e:
            logger.error(f"PubMed search error: {e}")
            return f"Search error: {str(e)}"

    def pubmed_search_fallback(query: str, max_results: int = 10) -> str:
        """Direct PubMed search (fallback when agent unavailable)."""
        return _fallback_pubmed_search(mcp_client, query, max_results)

    def clinical_trials_search(query: str, max_results: int = 5) -> str:
        """Database-first clinical trials search with external API fallback."""
        try:
            # STEP 1: Try local database first (if available)
            if DATABASE_AVAILABLE:
                logger.info(f"🗃️ Searching local clinical trials database first: {query[:50]}...")
                medical_db = get_medical_db()
                local_results = medical_db.search_clinical_trials_local(query, max_results)
            else:
                logger.info(f"📡 Database not available, using external Clinical Trials API directly: {query[:50]}...")
                local_results = None
            
            if local_results:
                logger.info(f"✅ Found {len(local_results)} trials in local database")
                # For external APIs, just do a health check
                try:
                    if tool_registry._initialized:
                        # Quick health check on external API (1 result only)
                        safe_async_call(tool_registry.execute_tool("search-clinical-trials", {
                            "query": "health",
                            "max_results": 1
                        }))
                        logger.info("✅ External Clinical Trials API health check passed")
                    else:
                        logger.info("ℹ️ ToolRegistry not available, skipping health check")
                except Exception as e:
                    logger.warning(f"⚠️ External Clinical Trials API health check failed: {e}")
                
                return json.dumps({
                    "results": local_results,
                    "source": "local_database",
                    "total_found": len(local_results),
                    "external_api_status": "health_check_completed"
                }, indent=2)
            
            # STEP 2: If no local results, fallback to external API
            logger.warning(f"📡 No local results found, using external Clinical Trials API: {query[:50]}...")
            
            # Try ToolRegistry first (robust tool management)
            if tool_registry._initialized:
                result = safe_async_call(tool_registry.execute_tool("search-clinical-trials", {
                    "query": query,
                    "max_results": max_results
                }))
                logger.info("✅ Used ToolRegistry for clinical trials search")
            else:
                # Fallback to direct MCP call if ToolRegistry unavailable
                logger.warning("⚠️ ToolRegistry not available, using direct MCP")
                result = safe_async_call(mcp_client.call_tool("search-clinical-trials", {
                    "query": query,
                    "max_results": max_results
                }))
                
            return json.dumps(result, indent=2) if result else "No clinical trials found"
        except Exception as e:
            logger.error(f"Clinical trials search error: {e}")
            return f"Clinical trials search error: {str(e)}"

    def drug_information_lookup(drug_name: str) -> str:
        """Database-first drug information lookup with external API fallback."""
        try:
            # STEP 1: Try local database first (if available)
            if DATABASE_AVAILABLE:
                logger.info(f"🗃️ Searching local FDA drugs database first: {drug_name}")
                medical_db = get_medical_db()
                local_results = medical_db.search_fda_drugs_local(drug_name, max_results=5)
            else:
                logger.info(f"📡 Database not available, using external Drug Info API directly: {drug_name}")
                local_results = None
            
            if local_results:
                logger.info(f"✅ Found {len(local_results)} drugs in local database")
                # For external APIs, just do a health check
                try:
                    if tool_registry._initialized:
                        # Quick health check on external API
                        safe_async_call(tool_registry.execute_tool("get-drug-info", {
                            "drug_name": "aspirin"  # Common drug for health check
                        }))
                        logger.info("✅ External Drug Info API health check passed")
                    else:
                        logger.info("ℹ️ ToolRegistry not available, skipping health check")
                except Exception as e:
                    logger.warning(f"⚠️ External Drug Info API health check failed: {e}")
                
                return json.dumps({
                    "results": local_results,
                    "source": "local_database",
                    "total_found": len(local_results),
                    "external_api_status": "health_check_completed"
                }, indent=2)
            
            # STEP 2: If no local results, fallback to external API
            logger.warning(f"📡 No local results found, using external Drug Info API: {drug_name}")
            
            # Try ToolRegistry first (robust tool management)
            if tool_registry._initialized:
                result = safe_async_call(tool_registry.execute_tool("get-drug-info", {
                    "drug_name": drug_name
                }))
                logger.info("✅ Used ToolRegistry for drug information lookup")
            else:
                # Fallback to direct MCP call if ToolRegistry unavailable
                logger.warning("⚠️ ToolRegistry not available, using direct MCP")
                result = safe_async_call(mcp_client.call_tool("get-drug-info", {
                    "drug_name": drug_name
                }))
                
            return json.dumps(result, indent=2) if result else f"No information found for {drug_name}"
        except Exception as e:
            logger.error(f"Drug information lookup error: {e}")
            return f"Drug information lookup error: {str(e)}"

    def check_database_status() -> str:
        """Check status of local medical database tables."""
        try:
            logger.info("🔍 Checking medical database status...")
            medical_db = get_medical_db()
            status = medical_db.get_database_status()
            
            logger.info(f"✅ Database status checked: {status.get('database_available', False)}")
            return json.dumps(status, indent=2)
            
        except Exception as e:
            logger.error(f"Database status check error: {e}")
            return f"Database status check error: {str(e)}"

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
        StructuredTool.from_function(
            func=check_database_status,
            name="check_medical_database_status",
            description="Check status and availability of local medical database tables (PubMed, clinical trials, FDA drugs).",
        ),
    ])
    
    logger.info(f"✅ Created {len(tools)} healthcare tools (agent-first architecture)")
    return tools
