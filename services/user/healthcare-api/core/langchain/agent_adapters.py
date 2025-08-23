"""
Healthcare Agent Adapters for LangChain Integration

Provides thin adapter layer that translates between def create_agent_adapter(
    agent_instance: "BaseHealthcareAgent", agent_name: str, input_schema: Any
) -> StructuredTool:gChain tool interface
and existing healthcare agent interfaces. This preserves all existing agent
logic while enabling LangChain coordination.

Architecture: "Restaurant Kitchen" Pattern
- LangChain: Head chef (coordinates)
- Adapters: Translation layer (this file)
- Agents: Specialized chefs (existing agent logic preserved)
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
from typing import Any, Dict, List, Optional, TYPE_CHECKING, TypedDict, cast

from langchain.tools import StructuredTool
from pydantic import BaseModel, Field

from core.infrastructure.healthcare_logger import get_healthcare_logger
from agents import BaseHealthcareAgent

logger = get_healthcare_logger("core.langchain.agent_adapters")


def synthesize_answer_from_sources(query: str, sources: List[Dict[str, Any]]) -> str:
    """
    Synthesize a conclusive answer from medical sources.

    Critical function to prevent LangChain iteration loops by ensuring
    agents return conclusive answers instead of just source lists.

    Args:
        query: The original medical query
        sources: List of source dictionaries with medical information

    Returns:
        Synthesized conclusive answer that prevents iteration loops
    """
    if not sources:
        return f"No medical information found for '{query}'."

    # Extract key information from sources
    source_summaries = []
    pubmed_count = 0
    trial_count = 0
    fda_count = 0

    for source in sources[:5]:  # Limit to top 5 sources for synthesis
        source_type = source.get("source_type", "unknown")
        title = source.get("title", "Untitled")

        if source_type == "pubmed":
            pubmed_count += 1
            abstract = (
                source.get("abstract", "")[:200] + "..."
                if len(source.get("abstract", "")) > 200
                else source.get("abstract", "")
            )
            if abstract:
                source_summaries.append(f"Research: {title} - {abstract}")
        elif source_type == "clinical_trial":
            trial_count += 1
            brief_title = source.get("brief_title", title)
            status = source.get("overall_status", "Unknown status")
            source_summaries.append(f"Clinical Trial: {brief_title} (Status: {status})")
        elif source_type == "fda":
            fda_count += 1
            drug_name = source.get("drug_name", title)
            indications = source.get("indications", [])
            indication_text = ", ".join(indications[:3]) if indications else "Various indications"
            source_summaries.append(f"FDA Drug: {drug_name} - {indication_text}")
        else:
            # Generic source handling
            summary = source.get("summary", source.get("abstract", ""))[:150]
            if summary:
                source_summaries.append(f"{title} - {summary}...")

    # Build conclusive answer
    answer_parts = []

    # Add source overview
    source_overview = []
    if pubmed_count > 0:
        source_overview.append(f"{pubmed_count} research article{'s' if pubmed_count != 1 else ''}")
    if trial_count > 0:
        source_overview.append(f"{trial_count} clinical trial{'s' if trial_count != 1 else ''}")
    if fda_count > 0:
        source_overview.append(f"{fda_count} FDA drug record{'s' if fda_count != 1 else ''}")

    if source_overview:
        answer_parts.append(f"Based on {' and '.join(source_overview)}:")

    # Add synthesized information
    if source_summaries:
        answer_parts.extend(source_summaries)

    # Add medical disclaimer
    answer_parts.append(
        "\n**Medical Disclaimer**: This information is for educational purposes only. "
        "Always consult with healthcare professionals for medical advice."
    )

    return "\n\n".join(answer_parts)


def create_conclusive_agent_adapter(agent: Any, name: str):
    """
    Create agent adapter that prevents iteration loops.

    This implements the pattern from the handoff document to ensure
    agents return conclusive answers instead of just source lists,
    preventing LangChain from hitting max_iterations (25).

    Args:
        agent: Healthcare agent instance
        name: Agent name for tool registration

    Returns:
        Function that provides conclusive answers
    """

    async def conclusive_agent(request: str) -> str:
        """Agent wrapper that always provides conclusive answers."""

        logger.info(f"🔄 Processing conclusive request for {name}: {request[:100]}...")

        try:
            # Parse request if it's JSON, otherwise use as string
            if request.strip().startswith("{"):
                try:
                    parsed_request = json.loads(request)
                    if isinstance(parsed_request, dict) and "query" in parsed_request:
                        query = parsed_request["query"]
                    else:
                        query = request
                except json.JSONDecodeError:
                    query = request
            else:
                query = request

            # Call agent with proper format
            if hasattr(agent, "process_request"):
                result = await agent.process_request({"query": query})
            elif hasattr(agent, "_process_implementation"):
                result = await agent._process_implementation({"query": query})
            elif hasattr(agent, "search"):
                result = await agent.search(query)
            elif hasattr(agent, "process"):
                result = await agent.process(query)
            else:
                logger.error(f"Agent {name} has no recognizable processing method")
                return f"CONCLUSIVE ANSWER: Agent {name} is not properly configured."

            # CRITICAL: Use formatted_summary if available (medical search agent provides this)
            if isinstance(result, dict):
                # First priority: Use the agent's formatted_summary if available
                if "formatted_summary" in result and result["formatted_summary"]:
                    formatted_summary = result["formatted_summary"]
                    logger.info("✅ Using agent's formatted_summary for conclusive answer")
                    return f"CONCLUSIVE ANSWER: {formatted_summary}"

                # Second priority: Synthesize from sources
                if "sources" in result and len(result["sources"]) > 0:
                    answer = synthesize_answer_from_sources(query, result["sources"])
                    logger.info(
                        f"✅ Synthesized conclusive answer from {len(result['sources'])} sources"
                    )
                    return f"CONCLUSIVE ANSWER: {answer}"
                elif "sources" in result:
                    logger.info(f"⚠️ No sources found for query: {query[:50]}...")
                    return f"CONCLUSIVE ANSWER: No information found for '{query}'"

            # Handle string responses
            if isinstance(result, str):
                return f"CONCLUSIVE ANSWER: {result}"

            # Handle other response types
            logger.info(f"✅ Processed {name} request, result type: {type(result)}")
            return f"CONCLUSIVE ANSWER: {str(result)}"

        except Exception as e:
            logger.error(f"❌ Error in {name} conclusive adapter: {e}")
            return f"CONCLUSIVE ANSWER: Error processing request - {str(e)}"

    return conclusive_agent


# Input schemas for agent adapters
class MedicalSearchInput(BaseModel):
    """Input for medical search agent adapter."""

    query: str = Field(description="Medical research, literature, or clinical question")


class IntakeInput(BaseModel):
    """Input for intake agent adapter."""

    query: str = Field(description="Patient intake, registration, or admission question")


class BillingInput(BaseModel):
    """Input for billing agent adapter."""

    query: str = Field(description="Medical billing, insurance, or financial question")


class SchedulingInput(BaseModel):
    """Input for scheduling agent adapter."""

    query: str = Field(description="Appointment scheduling or calendar management question")


class DocumentInput(BaseModel):
    """Input for document processing agent adapter."""

    query: str = Field(description="Medical document processing or analysis question")


class ClinicalResearchInput(BaseModel):
    """Input for clinical research agent adapter."""

    query: str = Field(description="Clinical research, trials, or study analysis question")


class TranscriptionInput(BaseModel):
    """Input for transcription agent adapter."""

    query: str = Field(description="Medical transcription or voice-to-text question")


class InsuranceInput(BaseModel):
    """Input for insurance verification agent adapter."""

    query: str = Field(description="Insurance verification, authorization, or coverage question")


def safe_async_call(coro):
    """
    Safely execute an async coroutine from sync context.
    Handles event loop management for agent calls.
    """
    try:
        # Try to get the current event loop
        asyncio.get_running_loop()
        # If we're in a running loop, use thread-based execution
        import threading

        def run_in_thread():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(coro)
            finally:
                new_loop.close()

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            return future.result(timeout=60)  # Increased timeout for medical queries

    except RuntimeError:
        # No event loop running, safe to use asyncio.run()
        return asyncio.run(coro)
    except Exception as e:
        logger.exception(f"Failed to execute async agent call: {e}")
        raise


def create_agent_adapter(
    agent_instance: BaseHealthcareAgent,
    agent_name: str,
    input_schema: type[BaseModel],
) -> StructuredTool:
    """
    Create a LangChain tool adapter for an existing healthcare agent.

    This is the core adapter pattern - it translates between LangChain's
    tool interface and the existing agent's _process_implementation interface.

    Args:
        agent_instance: Existing healthcare agent instance
        agent_name: Name for the LangChain tool
        input_schema: Pydantic schema for input validation

    Returns:
        StructuredTool that LangChain can use
    """

    def agent_wrapper(query: str) -> str:
        """
        Thin adapter wrapper - translates LangChain call to agent call.

        NO LOGIC CHANGES - just interface translation!
        """
        try:
            # Step 1: Log the routing (this creates the agent logging we need!)
            logger.info(f"🔄 LangChain adapter routing to {agent_name} agent: {query[:100]}")

            # Step 2: Translate LangChain string input to agent's expected format
            agent_request = {
                "query": query,
                "search_query": query,  # Some agents expect search_query
                "message": query,  # Some agents expect message
                "user_id": "langchain",  # Default user for agent logging
                "session_id": "adapter_session",
            }

            # Step 3: Call existing agent's EXISTING method (no changes to agent code!)
            result = safe_async_call(agent_instance._process_implementation(agent_request))

            # Step 4: Log successful routing for verification
            logger.info(f"✅ {agent_name} agent completed successfully via adapter")

            # Step 5: Return in format LangChain expects - CONCLUSIVE format to prevent loops
            if isinstance(result, dict):
                # For successful responses, extract key information into conclusive summary
                if result.get("success") and result.get("formatted_summary"):
                    total_sources = result.get("total_sources", 0)

                    # CRITICAL FIX: Handle empty results with DEFINITIVE completion
                    if total_sources == 0:
                        conclusive_response = f"""FINAL ANSWER: No medical literature sources found.

I have completed a thorough search of the medical literature database for "{result.get("search_query", query)}" but found no matching articles or sources.

Possible reasons:
- Query terms may be too specific
- No recent articles on this exact topic in our database
- Alternative search terms might be needed

SEARCH STATUS: COMPLETED - NO RESULTS FOUND
This healthcare search task is now finished."""
                    else:
                        # Use the agent's own formatted summary as the conclusive response
                        conclusive_response = f"""MEDICAL SEARCH COMPLETE: {result["formatted_summary"]}

Key Findings:
- Sources Found: {total_sources}
- Search Query: {result.get("search_query", query)}
- Search Confidence: {result.get("search_confidence", "N/A")}

This medical literature search has been completed successfully by the specialized medical search agent."""

                    return conclusive_response
                elif result.get("success"):
                    # Generic success format for other agents
                    return f"AGENT TASK COMPLETE: {agent_name.replace('_', ' ').title()} agent successfully processed: {query[:100]}"
                else:
                    # Error format
                    return f"AGENT ERROR: {result.get('error', 'Unknown error occurred')}"
            return str(result)

        except Exception as e:
            error_msg = f"❌ {agent_name} agent adapter error: {e}"
            logger.error(error_msg)
            return error_msg

    # Create the LangChain StructuredTool with proper metadata
    return StructuredTool.from_function(
        func=agent_wrapper,
        name=f"{agent_name}_agent",
        description=f"Healthcare {agent_name.replace('_', ' ')} agent. Routes queries to specialized {agent_name} agent for expert processing.",
        args_schema=input_schema,
    )


class AgentConfig(TypedDict):
    input_schema: type[BaseModel]
    description_suffix: str


def create_healthcare_agent_adapters(discovered_agents: dict[str, Any]) -> list[StructuredTool]:
    """
    Create LangChain tool adapters for all discovered healthcare agents.

    This is where the "restaurant kitchen" pattern is implemented:
    - Each agent remains a specialized chef (unchanged)
    - Adapters provide communication interface for the head chef (LangChain)

    Args:
        discovered_agents: Dictionary of agent_name -> agent_instance

    Returns:
        List of StructuredTool adapters for LangChain to use
    """
    tools: list[StructuredTool] = []

    # Define agent-specific configurations
    agent_configs: dict[str, AgentConfig] = {
        "medical_search": {
            "input_schema": MedicalSearchInput,
            "description_suffix": "Use for medical literature, research, drug information, clinical studies, or disease information queries.",
        },
        "intake": {
            "input_schema": IntakeInput,
            "description_suffix": "Use for patient intake, registration, admission, or onboarding processes.",
        },
        "billing_helper": {
            "input_schema": BillingInput,
            "description_suffix": "Use for medical billing, insurance claims, payment processing, or financial healthcare questions.",
        },
        "schedulingoptimizer": {
            "input_schema": SchedulingInput,
            "description_suffix": "Use for appointment scheduling, calendar management, or time optimization questions.",
        },
        "document_processor": {
            "input_schema": DocumentInput,
            "description_suffix": "Use for medical document analysis, processing, or extraction questions.",
        },
        "clinical_research": {
            "input_schema": ClinicalResearchInput,
            "description_suffix": "Use for clinical research, trial analysis, or research methodology questions.",
        },
        "transcription": {
            "input_schema": TranscriptionInput,
            "description_suffix": "Use for medical transcription, voice-to-text, or audio processing questions.",
        },
        "insurance_verification": {
            "input_schema": InsuranceInput,
            "description_suffix": "Use for insurance verification, authorization, or coverage validation questions.",
        },
    }

    # Create adapters for each discovered agent
    for agent_name, agent_instance in discovered_agents.items():
        if not isinstance(agent_instance, BaseHealthcareAgent):
            logger.warning(f"⚠️ Skipping {agent_name} - not a BaseHealthcareAgent instance")
            continue

        # Get configuration for this agent type
        config = cast(
            AgentConfig,
            agent_configs.get(
                agent_name,
            )
            or {
                "input_schema": MedicalSearchInput,  # Default to medical search schema
                "description_suffix": f"Use for {agent_name.replace('_', ' ')} related healthcare questions.",
            },
        )

        try:
            # Create adapter using the core adapter pattern
            adapter_tool = create_agent_adapter(
                agent_instance=agent_instance,
                agent_name=agent_name,
                input_schema=cast(type[BaseModel], config["input_schema"]),
            )

            tools.append(adapter_tool)
            logger.info(f"✅ Created adapter for {agent_name} agent")

        except Exception as e:
            logger.error(f"❌ Failed to create adapter for {agent_name}: {e}")
            continue

    if not tools:
        logger.error("❌ No agent adapters created! Check discovered_agents dictionary")
    else:
        logger.info(
            f"🔧 Created {len(tools)} healthcare agent adapters: {[tool.name for tool in tools]}",
        )

    return tools


def create_general_healthcare_router(discovered_agents: dict[str, Any]) -> StructuredTool:
    """
    Create a general healthcare query router that intelligently selects agents.

    This provides the "head chef" coordination logic that routes queries
    to the most appropriate specialized agent.
    """

    def healthcare_router(query: str) -> str:
        """
        Intelligent routing logic for healthcare queries.
        Analyzes query content and routes to the best available agent.
        """
        try:
            query_lower = query.lower()

            # Define routing keywords for each agent type
            routing_map = {
                "medical_search": [
                    "research",
                    "study",
                    "literature",
                    "drug",
                    "medication",
                    "treatment",
                    "disease",
                    "condition",
                    "clinical",
                    "medical",
                    "pubmed",
                    "journal",
                ],
                "intake": [
                    "intake",
                    "registration",
                    "admit",
                    "new patient",
                    "enrollment",
                    "demographics",
                    "patient information",
                ],
                "billing_helper": [
                    "billing",
                    "insurance",
                    "payment",
                    "claim",
                    "cost",
                    "charge",
                    "financial",
                    "coverage",
                    "copay",
                ],
                "schedulingoptimizer": [
                    "schedule",
                    "appointment",
                    "calendar",
                    "booking",
                    "availability",
                    "time slot",
                    "reschedule",
                ],
                "document_processor": [
                    "document",
                    "form",
                    "report",
                    "extract",
                    "process",
                    "analyze",
                    "pdf",
                    "text",
                ],
                "clinical_research": [
                    "clinical trial",
                    "research methodology", 
                    "clinical study",
                    "research protocol",
                    "study design",
                    "clinical investigation",
                    "trial enrollment",
                    "research analysis",
                    "evidence synthesis",
                    "systematic review",
                    "meta-analysis",
                    "research findings",
                    "clinical evidence",
                    "literature synthesis",
                    "comprehensive research"
                ],
                "transcription": ["transcribe", "voice", "audio", "speech", "dictation", "record"],
                "insurance_verification": [
                    "verify",
                    "authorization",
                    "coverage",
                    "benefits",
                    "eligibility",
                    "approval",
                ],
            }

            # Score each agent based on keyword matches
            agent_scores = {}
            for agent_name, keywords in routing_map.items():
                if agent_name in discovered_agents:
                    score = sum(1 for keyword in keywords if keyword in query_lower)
                    if score > 0:
                        agent_scores[agent_name] = score

            # Route to highest scoring agent
            if agent_scores:
                best_agent = max(agent_scores.items(), key=lambda x: x[1])[0]
                logger.info(
                    f"🎯 Healthcare router selecting {best_agent} agent for query: {query[:50]}",
                )

                # Call the selected agent through its adapter
                agent_instance = discovered_agents[best_agent]
                adapter_result = safe_async_call(
                    agent_instance._process_implementation(
                        {
                            "query": query,
                            "search_query": query,
                            "user_id": "router",
                            "session_id": "router_session",
                        },
                    ),
                )

                return (
                    json.dumps(adapter_result, indent=2)
                    if isinstance(adapter_result, dict)
                    else str(adapter_result)
                )

            # Default to medical search if no specific match (it's the most robust agent)
            if "medical_search" in discovered_agents:
                logger.info(f"🔄 No specific agent match, using medical_search for: {query[:50]}")
                agent_instance = discovered_agents["medical_search"]
                adapter_result = safe_async_call(
                    agent_instance._process_implementation(
                        {
                            "query": query,
                            "search_query": query,
                            "user_id": "router_default",
                            "session_id": "router_session",
                        },
                    ),
                )

                # CRITICAL FIX: Apply same conclusive formatting as individual agents
                if isinstance(adapter_result, dict):
                    if adapter_result.get("success") and adapter_result.get("formatted_summary"):
                        total_sources = adapter_result.get("total_sources", 0)

                        if total_sources == 0:
                            return f"""FINAL ANSWER: No medical literature sources found.

I have completed a thorough search of the medical literature database for "{adapter_result.get("search_query", query)}" but found no matching articles or sources.

Possible reasons:
- Query terms may be too specific
- No recent articles on this exact topic in our database
- Alternative search terms might be needed

SEARCH STATUS: COMPLETED - NO RESULTS FOUND
This healthcare search task is now finished."""
                        else:
                            return f"""MEDICAL SEARCH COMPLETE: {adapter_result["formatted_summary"]}

Key Findings:
- Sources Found: {total_sources}
- Search Query: {adapter_result.get("search_query", query)}
- Search Confidence: {adapter_result.get("search_confidence", "N/A")}

This medical literature search has been completed successfully."""
                    elif adapter_result.get("success"):
                        return f"AGENT TASK COMPLETE: Medical search agent successfully processed: {query[:100]}"
                    else:
                        return (
                            f"AGENT ERROR: {adapter_result.get('error', 'Unknown error occurred')}"
                        )

                return str(adapter_result)

            return "No suitable healthcare agent available for this query."

        except Exception as e:
            error_msg = f"Healthcare router error: {e}"
            logger.error(error_msg)
            return error_msg

    return StructuredTool.from_function(
        func=healthcare_router,
        name="healthcare_query_router",
        description="Intelligent healthcare query router. Analyzes the query and routes to the most appropriate specialized healthcare agent.",
        args_schema=MedicalSearchInput,  # Use general schema for router
    )
