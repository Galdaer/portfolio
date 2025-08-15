"""
Healthcare Agent Tools for LangChain Integration

Provides LangChain tools that route to specialized healthcare agents.
This is the agent-first architecture where queries go through domain experts.
"""

from __future__ import annotations

from typing import Any, List, Callable
import asyncio
import json

from pydantic import BaseModel, Field
from langchain.tools import StructuredTool

from core.infrastructure.healthcare_logger import get_healthcare_logger

logger = get_healthcare_logger("core.langchain.agent_tools")


# Agent tool input schemas
class MedicalSearchInput(BaseModel):
    """Input for medical literature search queries."""

    query: str = Field(description="Medical research or literature search question")


class BillingQueryInput(BaseModel):
    """Input for billing-related queries."""

    query: str = Field(description="Billing, insurance, or payment-related question")


class InsuranceVerificationInput(BaseModel):
    """Input for insurance verification queries."""

    query: str = Field(description="Insurance verification, coverage, or authorization question")


class SchedulingQueryInput(BaseModel):
    """Input for scheduling optimization queries."""

    query: str = Field(description="Appointment scheduling or optimization question")


class DocumentProcessingInput(BaseModel):
    """Input for document processing queries."""

    query: str = Field(description="Document processing, analysis, or extraction question")
    document_content: str = Field(default="", description="Document content to process")


class TranscriptionQueryInput(BaseModel):
    """Input for transcription-related queries."""

    query: str = Field(description="Medical transcription or note-taking question")


class IntakeQueryInput(BaseModel):
    """Input for patient intake queries."""

    query: str = Field(description="Patient intake, registration, or onboarding question")


class ClinicalResearchInput(BaseModel):
    """Input for clinical research queries."""

    query: str = Field(description="Clinical research, trials, or evidence-based question")


def create_agent_tools(agent_manager) -> List[StructuredTool]:
    """Create LangChain tools for specialized healthcare agents.

    Args:
        agent_manager: The healthcare agent manager that provides access to agents

    Returns:
        List of StructuredTool instances for each healthcare agent
    """

    async def _medical_search_query(query: str) -> str:
        """Route medical literature queries to the medical search agent."""
        try:
            if hasattr(agent_manager, "get_agent"):
                agent = agent_manager.get_agent("medical_search")
                if agent and hasattr(agent, "process_query"):
                    result = await agent.process_query(query)
                    return json.dumps(result) if isinstance(result, dict) else str(result)
            return "Medical search agent not available. Please search medical literature manually."
        except Exception as e:
            logger.error(f"Medical search agent error: {e}")
            return f"Medical search error: {str(e)}"

    async def _billing_agent_query(query: str) -> str:
        """Route billing queries to the billing helper agent."""
        try:
            if hasattr(agent_manager, "get_agent"):
                agent = agent_manager.get_agent("billing_helper")
                if agent and hasattr(agent, "process_query"):
                    result = await agent.process_query(query)
                    return json.dumps(result) if isinstance(result, dict) else str(result)
            return "Billing agent not available. Please contact billing department directly."
        except Exception as e:
            logger.error(f"Billing agent error: {e}")
            return f"Billing query error: {str(e)}"

    async def _insurance_verification_query(query: str) -> str:
        """Route insurance verification queries to the insurance verification agent."""
        try:
            if hasattr(agent_manager, "get_agent"):
                agent = agent_manager.get_agent("insurance_verification")
                if agent and hasattr(agent, "process_query"):
                    result = await agent.process_query(query)
                    return json.dumps(result) if isinstance(result, dict) else str(result)
            return "Insurance verification agent not available. Please verify insurance manually."
        except Exception as e:
            logger.error(f"Insurance verification agent error: {e}")
            return f"Insurance verification error: {str(e)}"

    async def _scheduling_agent_query(query: str) -> str:
        """Route scheduling queries to the scheduling optimizer agent."""
        try:
            if hasattr(agent_manager, "get_agent"):
                agent = agent_manager.get_agent("schedulingoptimizer")
                if agent and hasattr(agent, "process_query"):
                    result = await agent.process_query(query)
                    return json.dumps(result) if isinstance(result, dict) else str(result)
            return "Scheduling agent not available. Please use manual scheduling procedures."
        except Exception as e:
            logger.error(f"Scheduling agent error: {e}")
            return f"Scheduling query error: {str(e)}"

    async def _document_processing_query(query: str, document_content: str = "") -> str:
        """Route document processing queries to the document processor agent."""
        try:
            if hasattr(agent_manager, "get_agent"):
                agent = agent_manager.get_agent("documentprocessor")
                if agent and hasattr(agent, "process_query"):
                    # Combine query and document content
                    full_query = (
                        f"{query}\\n\\nDocument content: {document_content}"
                        if document_content
                        else query
                    )
                    result = await agent.process_query(full_query)
                    return json.dumps(result) if isinstance(result, dict) else str(result)
            return "Document processing agent not available. Please process documents manually."
        except Exception as e:
            logger.error(f"Document processing agent error: {e}")
            return f"Document processing error: {str(e)}"

    async def _transcription_agent_query(query: str) -> str:
        """Route transcription queries to the transcription agent."""
        try:
            if hasattr(agent_manager, "get_agent"):
                agent = agent_manager.get_agent("transcription")
                if agent and hasattr(agent, "process_query"):
                    result = await agent.process_query(query)
                    return json.dumps(result) if isinstance(result, dict) else str(result)
            return "Transcription agent not available. Please use manual transcription methods."
        except Exception as e:
            logger.error(f"Transcription agent error: {e}")
            return f"Transcription query error: {str(e)}"

    async def _intake_agent_query(query: str) -> str:
        """Route intake queries to the intake agent."""
        try:
            if hasattr(agent_manager, "get_agent"):
                agent = agent_manager.get_agent("intake")
                if agent and hasattr(agent, "process_query"):
                    result = await agent.process_query(query)
                    return json.dumps(result) if isinstance(result, dict) else str(result)
            return "Intake agent not available. Please use standard intake procedures."
        except Exception as e:
            logger.error(f"Intake agent error: {e}")
            return f"Intake query error: {str(e)}"

    async def _clinical_research_query(query: str) -> str:
        """Route clinical research queries to the clinical research agent."""
        try:
            if hasattr(agent_manager, "get_agent"):
                agent = agent_manager.get_agent("clinical_research")
                if agent and hasattr(agent, "process_query"):
                    result = await agent.process_query(query)
                    return json.dumps(result) if isinstance(result, dict) else str(result)
            return "Clinical research agent not available. Please consult research department."
        except Exception as e:
            logger.error(f"Clinical research agent error: {e}")
            return f"Clinical research query error: {str(e)}"

    def _safe_agent_wrapper(
        func_name: str, func: Callable, max_retries: int = 1, base_delay: float = 0.5
    ):
        """Wrapper for agent function calls with error handling and retries."""

        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        await asyncio.sleep(base_delay * (2**attempt))
                        logger.warning(f"Agent tool {func_name} attempt {attempt + 1} failed: {e}")
                    else:
                        logger.error(
                            f"Agent tool {func_name} failed after {max_retries + 1} attempts: {e}"
                        )

            return f"Agent tool error after {max_retries + 1} attempts: {str(last_exception)}"

        return wrapper

    tools: List[StructuredTool] = [
        StructuredTool.from_function(
            func=_safe_agent_wrapper("medical_search", _medical_search_query),
            name="search_medical_literature",
            description="Search medical literature and research using the medical search agent",
            args_schema=MedicalSearchInput,
            return_direct=False,
            handle_tool_error=True,
        ),
        StructuredTool.from_function(
            func=_safe_agent_wrapper("billing_query", _billing_agent_query),
            name="billing_assistance",
            description="Handle billing, insurance verification, and payment-related queries",
            args_schema=BillingQueryInput,
            return_direct=False,
            handle_tool_error=True,
        ),
        StructuredTool.from_function(
            func=_safe_agent_wrapper("insurance_verification", _insurance_verification_query),
            name="insurance_verification",
            description="Verify insurance coverage, authorizations, and benefits",
            args_schema=InsuranceVerificationInput,
            return_direct=False,
            handle_tool_error=True,
        ),
        StructuredTool.from_function(
            func=_safe_agent_wrapper("scheduling_query", _scheduling_agent_query),
            name="scheduling_optimization",
            description="Optimize appointment scheduling and resource allocation",
            args_schema=SchedulingQueryInput,
            return_direct=False,
            handle_tool_error=True,
        ),
        StructuredTool.from_function(
            func=_safe_agent_wrapper("document_processing", _document_processing_query),
            name="document_processing",
            description="Process, analyze, and extract information from healthcare documents",
            args_schema=DocumentProcessingInput,
            return_direct=False,
            handle_tool_error=True,
        ),
        StructuredTool.from_function(
            func=_safe_agent_wrapper("transcription_query", _transcription_agent_query),
            name="medical_transcription",
            description="Handle medical transcription and note-taking tasks",
            args_schema=TranscriptionQueryInput,
            return_direct=False,
            handle_tool_error=True,
        ),
        StructuredTool.from_function(
            func=_safe_agent_wrapper("intake_query", _intake_agent_query),
            name="patient_intake",
            description="Assist with patient intake, registration, and onboarding processes",
            args_schema=IntakeQueryInput,
            return_direct=False,
            handle_tool_error=True,
        ),
        StructuredTool.from_function(
            func=_safe_agent_wrapper("clinical_research_query", _clinical_research_query),
            name="clinical_research",
            description="Provide clinical research support and evidence-based information",
            args_schema=ClinicalResearchInput,
            return_direct=False,
            handle_tool_error=True,
        ),
    ]

    logger.info(f"Created {len(tools)} agent tools for LangChain integration")
    return tools
