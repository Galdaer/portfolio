# core/orchestration/medical_workflow_state.py

from dataclasses import dataclass
from enum import Enum
from typing import Any

from config.app import config


class MedicalWorkflowStep(Enum):
    QUERY_ANALYSIS = "query_analysis"
    INITIAL_SEARCH = "initial_search"
    VALIDATION = "validation"
    REFINEMENT = "refinement"
    FINAL_SYNTHESIS = "final_synthesis"
    TRUST_SCORING = "trust_scoring"


@dataclass
class MedicalWorkflowState:
    """State management for complex medical information workflows"""

    step: MedicalWorkflowStep
    query_id: str
    original_query: str
    current_query: str
    iteration: int
    max_iterations: int
    results: list[dict[str, Any]]
    trust_scores: list[dict[str, Any]]
    errors: list[str]
    context: dict[str, Any]


class MedicalWorkflowOrchestrator:
    """Orchestrate complex medical information workflows with state management"""

    def __init__(self, query_engine: Any, validator: Any, llm_client: Any) -> None:
        self.query_engine = query_engine
        self.validator = validator
        self.llm_client = llm_client

    def _generate_query_id(self) -> str:
        """Generate unique query ID for tracking"""
        import uuid

        return f"medical_query_{uuid.uuid4().hex[:12]}"

    async def _analyze_query(self, state: MedicalWorkflowState) -> MedicalWorkflowState:
        """Analyze the initial query to determine search strategy"""
        try:
            # Extract medical entities and query type from the query
            analysis_prompt = f"""
            Analyze this medical query and provide structured information:
            Query: {state.original_query}

            Provide:
            1. Query type (diagnosis, treatment, drug_info, general)
            2. Medical entities mentioned
            3. Urgency level (low, medium, high)
            4. Recommended search strategy
            """

            result = await self.llm_client.generate(
                prompt=analysis_prompt,
                model=config.get_model_for_task("clinical"),
                options={"temperature": 0.1, "max_tokens": 300},
            )

            analysis = result.get("response", "")

            # Store analysis in context
            state.context.update(
                {
                    "query_analysis": analysis,
                    "analyzed_at": "2025-01-23T00:00:00Z",
                    "entities_extracted": True,
                },
            )

        except Exception as e:
            state.errors.append(f"Query analysis error: {str(e)}")

        return state

    async def _execute_search(self, state: MedicalWorkflowState) -> MedicalWorkflowState:
        """Execute medical information search"""
        try:
            # Use the query engine to search for medical information
            result = await self.query_engine.process_medical_query(
                query=state.current_query, context=state.context,
            )
            state.results.append(result)
        except Exception as e:
            state.errors.append(f"Search error: {str(e)}")
        return state

    async def _refine_query(self, state: MedicalWorkflowState) -> MedicalWorkflowState:
        """Refine query based on previous results and trust scores"""
        try:
            if not state.trust_scores:
                return state

            latest_trust = state.trust_scores[-1]

            # If trust score is very low, try to refine the query
            if latest_trust["overall_trust"] < 0.5:
                refinement_prompt = f"""
                The previous search for "{state.current_query}" had low trust scores:
                - Overall trust: {latest_trust["overall_trust"]:.2f}
                - Accuracy: {latest_trust["accuracy_score"]:.2f}
                - Safety: {latest_trust["safety_score"]:.2f}

                Suggest a more specific medical query that might yield better results.
                Focus on:
                1. More specific medical terminology
                2. Clearer clinical context
                3. Specific evidence types needed

                Original query: {state.original_query}
                Current query: {state.current_query}
                """

                result = await self.llm_client.generate(
                    prompt=refinement_prompt,
                    model=config.get_model_for_task("reasoning"),
                    options={"temperature": 0.2, "max_tokens": 200},
                )

                refined_query = result.get("response", state.current_query).strip()
                if refined_query and refined_query != state.current_query:
                    state.current_query = refined_query
                    state.context["query_refined"] = True
                    state.context["refinement_reason"] = "low_trust_score"

        except Exception as e:
            state.errors.append(f"Query refinement error: {str(e)}")

        return state

    async def _synthesize_final_response(self, state: MedicalWorkflowState) -> MedicalWorkflowState:
        """Synthesize final response from all iterations"""
        try:
            if not state.results:
                state.errors.append("No results to synthesize")
                return state

            # Collect all responses and sources
            all_sources = []
            all_responses = []

            for result in state.results:
                if "response" in result:
                    all_responses.append(result["response"])
                if "sources" in result:
                    all_sources.extend(result["sources"])

            # Remove duplicate sources based on title/URL
            unique_sources = []
            seen_titles = set()
            for source in all_sources:
                title = source.get("title", "")
                if title and title not in seen_titles:
                    unique_sources.append(source)
                    seen_titles.add(title)

            # Create synthesis prompt
            synthesis_prompt = f"""
            Based on multiple medical search iterations for: "{state.original_query}"

            Synthesize a comprehensive response using these findings:
            {chr(10).join(all_responses)}

            Requirements:
            1. Provide a clear, evidence-based summary
            2. Note any conflicting information
            3. Include appropriate medical disclaimers
            4. Cite the strength of evidence
            5. Recommend next steps if appropriate

            Total sources reviewed: {len(unique_sources)}
            Search iterations: {state.iteration + 1}
            """

            result = await self.llm_client.generate(
                prompt=synthesis_prompt,
                model=config.get_model_for_task("reasoning"),
                options={"temperature": 0.1, "max_tokens": 800},
            )

            final_response = {
                "synthesized_response": result.get("response", ""),
                "total_sources": len(unique_sources),
                "unique_sources": unique_sources,
                "iterations_completed": state.iteration + 1,
                "final_trust_score": state.trust_scores[-1] if state.trust_scores else None,
                "query_id": state.query_id,
                "medical_disclaimer": "This information is for educational purposes only and not medical advice.",
            }

            state.results.append(final_response)
            state.context["synthesis_completed"] = True

        except Exception as e:
            state.errors.append(f"Response synthesis error: {str(e)}")

        return state

    async def execute_medical_workflow(
        self,
        query: str,
        context: dict[str, Any] | None = None,
        max_iterations: int = 3,
    ) -> dict[str, Any]:
        """Execute complete medical information workflow with state tracking"""

        state = MedicalWorkflowState(
            step=MedicalWorkflowStep.QUERY_ANALYSIS,
            query_id=self._generate_query_id(),
            original_query=query,
            current_query=query,
            iteration=0,
            max_iterations=max_iterations,
            results=[],
            trust_scores=[],
            errors=[],
            context=context or {},
        )

        try:
            # Step 1: Query Analysis
            state = await self._analyze_query(state)

            # Step 2-4: Iterative Search and Refinement
            while state.iteration < state.max_iterations:
                state.step = MedicalWorkflowStep.INITIAL_SEARCH
                state = await self._execute_search(state)

                state.step = MedicalWorkflowStep.VALIDATION
                state = await self._validate_results(state)

                # Check if trust score is good enough
                if state.trust_scores and state.trust_scores[-1]["overall_trust"] > 0.8:
                    break

                state.step = MedicalWorkflowStep.REFINEMENT
                state = await self._refine_query(state)
                state.iteration += 1

            # Step 5: Final Synthesis
            state.step = MedicalWorkflowStep.FINAL_SYNTHESIS
            state = await self._synthesize_final_response(state)

            return self._format_workflow_result(state)

        except Exception as e:
            state.errors.append(f"Workflow error: {str(e)}")
            return self._format_error_result(state)

    async def _validate_results(self, state: MedicalWorkflowState) -> MedicalWorkflowState:
        """Validate current results and add trust scores"""

        if not state.results:
            state.errors.append("No results to validate")
            return state

        latest_result = state.results[-1]

        trust_score = await self.validator.validate_medical_response(
            response=latest_result.get("response", ""),
            original_query=state.original_query,
            sources=latest_result.get("sources", []),
            query_type=latest_result.get("query_type", "general"),
        )

        state.trust_scores.append(
            {
                "iteration": state.iteration,
                "overall_trust": trust_score.overall_trust,
                "accuracy_score": trust_score.accuracy_score,
                "safety_score": trust_score.safety_score,
                "evidence_strength": trust_score.evidence_strength,
            },
        )

        return state

    def _format_workflow_result(self, state: MedicalWorkflowState) -> dict[str, Any]:
        """Format the final workflow result"""
        return {
            "query_id": state.query_id,
            "original_query": state.original_query,
            "results": state.results,
            "trust_scores": state.trust_scores,
            "iterations": state.iteration,
            "final_step": state.step.value,
            "errors": state.errors,
        }

    def _format_error_result(self, state: MedicalWorkflowState) -> dict[str, Any]:
        """Format error result when workflow fails"""
        return {
            "query_id": state.query_id,
            "original_query": state.original_query,
            "errors": state.errors,
            "partial_results": state.results,
            "status": "error",
        }


class HealthcareMCPOrchestrator:
    """MCP orchestrator for healthcare tools and services"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8000,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.max_retries = max_retries

    @classmethod
    def from_config_dict(cls, config_dict: dict[str, Any]) -> "HealthcareMCPOrchestrator":
        """Create orchestrator from configuration dictionary like mcp-use library"""

        # Extract healthcare MCP config
        healthcare_config = config_dict.get("mcpServers", {}).get("healthcare", {})

        # Initialize with dictionary-based config
        return cls(
            host=healthcare_config.get("host", "localhost"),
            port=healthcare_config.get("port", 8000),
            timeout=healthcare_config.get("timeout", 30),
            max_retries=healthcare_config.get("max_retries", 3),
        )

    async def get_available_tools(self) -> list[str]:
        """Get list of available healthcare tools from MCP server"""
        try:
            # In Phase 1, we'll actually call the MCP server
            # For now, return the expected healthcare tools based on the MCP pattern
            available_tools = [
                "search_medical_literature",
                "validate_medical_response",
                "extract_medical_entities",
                "search_clinical_trials",
                "search_clinical_guidelines",
                "get_drug_interactions",
                "search_medical_databases",
                "validate_medical_terminology",
                "get_clinical_decision_support",
                "search_diagnostic_criteria",
            ]

            # Make actual MCP server call to list available tools
            try:
                import aiohttp

                # Prepare MCP JSON-RPC request for tools/list
                mcp_request = {
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "params": {},
                    "id": 1,
                }

                # Call the MCP server endpoint
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as session, session.post(
                    f"http://{self.host}:{self.port}/mcp",
                    json=mcp_request,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if response.status == 200:
                        mcp_response = await response.json()
                        if "result" in mcp_response and "tools" in mcp_response["result"]:
                            # Extract tool names from MCP response
                            mcp_tools = [
                                tool["name"] for tool in mcp_response["result"]["tools"]
                            ]
                            # Combine with our expected healthcare tools
                            return list(set(available_tools + mcp_tools))

                    # If MCP call fails, fall back to default tools
                    return available_tools

            except Exception as mcp_error:
                # Log the MCP connection error but continue with fallback
                print(f"MCP server connection failed: {mcp_error}")
                return available_tools

        except Exception as e:
            # Fallback to basic tools if MCP unavailable
            print(f"Healthcare MCP orchestrator error: {e}")
            return [
                "search_medical_literature",
                "validate_medical_response",
                "extract_medical_entities",
            ]

    async def create_agent_with_mcp(self, llm_client: Any, max_steps: int = 50) -> Any:
        """Create healthcare agent with MCP integration like MCPAgent pattern"""

        # Import here to avoid circular imports
        from agents.clinical_research_assistant.clinical_research_agent import (
            ClinicalResearchAgent,
        )

        # Similar to their MCPAgent(llm=llm, client=client, max_steps=100)
        return ClinicalResearchAgent(llm_client=llm_client, mcp_client=self)
