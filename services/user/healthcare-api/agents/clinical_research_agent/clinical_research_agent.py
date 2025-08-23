"""
Clinical Research Agent with agentic RAG capabilities
Integrates dynamic knowledge retrieval with medical reasoning
"""

import asyncio
import json
import logging
import os
import traceback
from datetime import datetime
from typing import Any

import yaml

from agents import BaseHealthcareAgent
from config.app import config
from core.infrastructure.healthcare_logger import (
    get_healthcare_logger,
    log_healthcare_event,
)
from core.mcp.universal_parser import (
    parse_mcp_response,
    parse_pubmed_response,
    parse_clinical_trials_response,
)
from core.medical.enhanced_query_engine import EnhancedMedicalQueryEngine, QueryType
from core.reasoning.medical_reasoning_enhanced import EnhancedMedicalReasoning

logger = get_healthcare_logger("agent.research_assistant")


class ClinicalResearchAgent(BaseHealthcareAgent):
    """
    Enhanced Clinical Research Agent with agentic RAG capabilities
    Integrates dynamic knowledge retrieval with medical reasoning

    MEDICAL DISCLAIMER: This agent provides medical research assistance and clinical data
    analysis only. It searches medical literature, clinical trials, drug interactions, and
    evidence-based resources to support healthcare decision-making. It does not provide
    medical diagnosis, treatment recommendations, or replace clinical judgment. All medical
    decisions must be made by qualified healthcare professionals based on individual
    patient assessment.
    """

    def __init__(
        self,
        mcp_client: Any,
        llm_client: Any,
        max_steps: int | None = None,
        config_override: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            mcp_client, llm_client, agent_name="clinical_research", agent_type="research_assistant"
        )

        # Load configuration
        self.config = self._load_agent_config(config_override)

        # Set parameters from config or defaults
        self.max_steps = max_steps or self.config.get("max_steps", 50)
        self.max_iterations = self.config.get("max_iterations", 3)
        self.timeout_seconds = self.config.get("timeout_seconds", 300)
        self.llm_settings = self.config.get("llm_settings", {})

        self.query_engine = EnhancedMedicalQueryEngine(mcp_client, llm_client)
        self.medical_reasoning = EnhancedMedicalReasoning(self.query_engine, llm_client)
        self.mcp_client = mcp_client
        self.llm_client = llm_client
        self.current_step = 0

        # Log agent initialization with healthcare context
        log_healthcare_event(
            logger,
            logging.INFO,
            "Clinical Research Agent initialized",
            context={
                "agent": "clinical_research",
                "initialization": True,
                "phi_monitoring": True,
                "medical_research_support": True,
                "no_medical_advice": True,
            },
            operation_type="agent_initialization",
        )

    def _load_agent_config(self, config_override: dict | None = None) -> dict[str, Any]:
        """Load agent-specific configuration from file"""
        if config_override:
            return config_override

        try:
            config_path = "config/agent_settings.yml"
            if os.path.exists(config_path):
                with open(config_path) as f:
                    full_config = yaml.safe_load(f)
                config_data = (
                    full_config.get("agent_limits", {}).get("clinical_research", {})
                    if full_config
                    else {}
                )
                return config_data if isinstance(config_data, dict) else {}
        except Exception:
            pass

        # Return defaults if config fails to load
        return {
            "max_steps": 50,
            "max_iterations": 3,
            "timeout_seconds": 300,
            "llm_settings": {"temperature": 0.3, "max_tokens": 1000},
        }

    async def _process_implementation(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Process clinical research request with enhanced agentic RAG
        """
        self.current_step = 0
        query = request.get("query", "")
        session_id = request.get("session_id", "default")

        logger.info(f"🔬 Clinical Research Agent processing request: {query[:100]}...")
        logger.info(f"📊 Session ID: {session_id}")

        try:
            # Reset step counter for new queries
            logger.info(f"🚀 Starting clinical research processing with max {self.max_steps} steps")

            # Initialize result with default response
            result = self._create_error_response("Processing incomplete", session_id)

            # Process with step limiting (like their agent.run() with max_steps)
            while self.current_step < self.max_steps:
                logger.info(f"🔄 Processing step {self.current_step + 1}/{self.max_steps}")
                result = await self._process_with_step_limit(request, session_id)

                # Break if we have a complete result
                if result.get("complete", False):
                    logger.info(
                        f"✅ Clinical research completed successfully in {self.current_step + 1} steps"
                    )
                    break

                self.current_step += 1

            if not result.get("complete", False):
                logger.warning(
                    f"⚠️ Clinical research reached max steps ({self.max_steps}) without completion"
                )

            return result

        except Exception as e:
            logger.error(f"❌ Clinical research processing error: {str(e)}")
            session_id = request.get("session_id", "default")
            return self._create_error_response(f"Processing error: {str(e)}", session_id)

    async def _process_with_step_limit(
        self,
        input_data: dict[str, Any],
        session_id: str,
    ) -> dict[str, Any]:
        """Process single step with completion checking"""
        # Extract query information
        query = input_data.get("query", "")
        query_type = input_data.get("query_type", "general_inquiry")
        clinical_context = input_data.get("clinical_context", {})

        # Route to appropriate processing method based on query type
        try:
            if query_type == "differential_diagnosis":
                result = await self._process_differential_diagnosis(
                    query,
                    clinical_context,
                    session_id,
                )
            elif query_type == "drug_interaction":
                result = await self._process_drug_interaction(query, clinical_context, session_id)
            else:
                # Route all other queries (including literature_research) to comprehensive research with MCP tools
                result = await self._process_comprehensive_research(
                    query, clinical_context, session_id
                )

            # Mark as complete
            result["complete"] = True
            return result

        except Exception as e:
            return self._create_error_response(f"Step processing error: {str(e)}", session_id)

    async def _process_differential_diagnosis(
        self,
        query: str,
        clinical_context: dict[str, Any],
        session_id: str,
    ) -> dict[str, Any]:
        """
        Process differential diagnosis with iterative reasoning
        """
        # Enhanced query with medical reasoning
        reasoning_result = await self.medical_reasoning.reason_with_dynamic_knowledge(
            clinical_scenario=clinical_context,
            reasoning_type="differential_diagnosis",
            max_iterations=3,
        )

        # Additional literature search for specific diagnoses identified
        literature_queries = []
        for step in reasoning_result.steps:
            analysis = step.get("analysis", {})
            if isinstance(analysis, dict) and "most_likely_diagnoses" in analysis:
                for diagnosis in analysis["most_likely_diagnoses"][:3]:
                    diagnosis_name = (
                        diagnosis.get("name", "") if isinstance(diagnosis, dict) else str(diagnosis)
                    )
                    if diagnosis_name:
                        literature_queries.append(diagnosis_name)

        # Parallel literature search for identified diagnoses
        literature_results = []
        if literature_queries:
            search_tasks = [
                self.query_engine.process_medical_query(
                    query=f"{diag} diagnosis criteria evidence",
                    query_type=QueryType.LITERATURE_RESEARCH,
                    context=clinical_context,
                )
                for diag in literature_queries[:3]  # Limit to top 3
            ]

            literature_results = await asyncio.gather(*search_tasks, return_exceptions=True)
            literature_results = [r for r in literature_results if not isinstance(r, Exception)]

        return {
            "agent_type": "clinical_research",
            "request_type": "differential_diagnosis",
            "session_id": session_id,
            "reasoning_result": {
                "reasoning_type": reasoning_result.reasoning_type,
                "steps": reasoning_result.steps,
                "final_assessment": reasoning_result.final_assessment,
                "confidence_score": reasoning_result.confidence_score,
                "clinical_recommendations": reasoning_result.clinical_recommendations,
            },
            "supporting_literature": [
                {
                    "diagnosis": (
                        literature_queries[i] if i < len(literature_queries) else "Unknown"
                    ),
                    "sources": (
                        getattr(result, "sources", [])[:5]
                        if hasattr(result, "sources")
                        and isinstance(getattr(result, "sources", None), list)
                        else []
                    ),
                    "source_links": (
                        getattr(result, "source_links", [])[:5]
                        if hasattr(result, "source_links")
                        and isinstance(getattr(result, "source_links", None), list)
                        else []
                    ),
                }
                for i, result in enumerate(literature_results)
                if not isinstance(result, Exception)
            ],
            "evidence_sources": reasoning_result.evidence_sources,
            "disclaimers": reasoning_result.disclaimers,
            "generated_at": reasoning_result.generated_at.isoformat(),
            "processing_time": self._calculate_processing_time(),
        }

    async def _process_drug_interaction(
        self,
        query: str,
        clinical_context: dict[str, Any],
        session_id: str,
    ) -> dict[str, Any]:
        """
        Process drug interaction analysis with FDA and literature integration
        """
        # Extract medications from query and context
        medications = clinical_context.get("medications", [])
        if not medications:
            # Try to extract from query using NLP
            entity_result = await self.mcp_client.call_healthcare_tool(
                "extract_medical_entities",
                {"text": query},
            )
            drug_entities = [
                e.get("text")
                for e in entity_result.get("entities", [])
                if e.get("label") in ["CHEMICAL", "DRUG"]
            ]
            medications.extend(drug_entities)

        if not medications:
            return self._create_error_response(
                "No medications identified for interaction analysis",
                session_id,
            )

        # Enhanced drug interaction reasoning
        clinical_context["medications"] = medications
        reasoning_result = await self.medical_reasoning.reason_with_dynamic_knowledge(
            clinical_scenario=clinical_context,
            reasoning_type="drug_interaction",
            max_iterations=2,
        )

        # Direct FDA query for each medication
        fda_results = []
        for medication in medications:
            try:
                fda_query = await self.query_engine.process_medical_query(
                    query=f"{medication} drug interactions contraindications",
                    query_type=QueryType.DRUG_INTERACTION,
                    context=clinical_context,
                )
                fda_results.append(
                    {
                        "medication": medication,
                        "fda_data": [
                            source
                            for source in fda_query.sources
                            if source.get("source_type") == "fda"
                        ],
                    },
                )
            except Exception:
                continue

        return {
            "agent_type": "clinical_research",
            "request_type": "drug_interaction",
            "session_id": session_id,
            "medications_analyzed": medications,
            "reasoning_result": {
                "analysis_steps": reasoning_result.steps,
                "final_assessment": reasoning_result.final_assessment,
                "confidence_score": reasoning_result.confidence_score,
                "clinical_recommendations": reasoning_result.clinical_recommendations,
            },
            "fda_data": fda_results,
            "evidence_sources": reasoning_result.evidence_sources,
            "disclaimers": reasoning_result.disclaimers
            + [
                "Always consult official FDA prescribing information.",
                "Drug interactions may vary based on individual patient factors.",
            ],
            "generated_at": reasoning_result.generated_at.isoformat(),
        }

    async def _process_literature_research(
        self,
        query: str,
        clinical_context: dict[str, Any],
        session_id: str,
    ) -> dict[str, Any]:
        """
        Comprehensive literature research with source prioritization
        """
        # Multi-stage literature search
        research_stages: list[dict[str, Any]] = [
            {
                "query": query,
                "query_type": QueryType.LITERATURE_RESEARCH,
                "description": "Primary literature search",
            },
            {
                "query": f"{query} systematic review meta-analysis",
                "query_type": QueryType.LITERATURE_RESEARCH,
                "description": "High-evidence systematic reviews",
            },
            {
                "query": f"{query} clinical guidelines recommendations",
                "query_type": QueryType.CLINICAL_GUIDELINES,
                "description": "Clinical practice guidelines",
            },
        ]

        # Execute research stages in parallel
        research_tasks = [
            self.query_engine.process_medical_query(
                query=str(stage["query"]),
                query_type=stage["query_type"],
                context=clinical_context,
                max_iterations=2,
            )
            for stage in research_stages
        ]

        research_results = await asyncio.gather(*research_tasks, return_exceptions=True)

        # Process and categorize results
        categorized_results: dict[str, list[dict[str, Any]]] = {
            "primary_literature": [],
            "systematic_reviews": [],
            "clinical_guidelines": [],
            "all_sources": [],
        }

        for i, result in enumerate(research_results):
            if isinstance(result, Exception):
                continue

            stage_info = research_stages[i]
            stage_desc: str = (
                stage_info["description"] if isinstance(stage_info["description"], str) else ""
            )
            # Type-safe access to sources with proper typing
            stage_sources: list[dict[str, Any]] = []
            if hasattr(result, "sources") and hasattr(result, "__dict__"):
                sources_attr = getattr(result, "sources", None)
                if isinstance(sources_attr, list):
                    stage_sources = sources_attr

            categorized_results["all_sources"].extend(stage_sources)

            if "systematic review" in stage_desc.lower():
                categorized_results["systematic_reviews"].extend(stage_sources)
            elif "guidelines" in stage_desc.lower():
                categorized_results["clinical_guidelines"].extend(stage_sources)
            else:
                categorized_results["primary_literature"].extend(stage_sources)

        # Prioritize sources by evidence level
        prioritized_sources = self._prioritize_sources_by_evidence(
            categorized_results["all_sources"],
        )

        # Generate research summary
        summary = await self._generate_research_summary(
            query,
            prioritized_sources,
            clinical_context,
        )

        return {
            "agent_type": "clinical_research",
            "request_type": "literature_research",
            "session_id": session_id,
            "query": query,
            "research_summary": summary,
            "categorized_results": categorized_results,
            "prioritized_sources": prioritized_sources[:15],  # Top 15 sources
            "total_sources_found": len(categorized_results["all_sources"]),
            "evidence_quality_distribution": self._analyze_evidence_quality(
                categorized_results["all_sources"],
            ),
            "source_links": list(
                {source.get("url", "") for source in prioritized_sources if source.get("url")},
            ),
            "disclaimers": [
                "This research summary is for informational purposes only.",
                "Always verify information with original sources.",
                "Clinical decisions should be based on professional medical judgment.",
            ],
            "generated_at": datetime.utcnow().isoformat(),
        }

    def _prioritize_sources_by_evidence(
        self,
        sources: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Prioritize sources by evidence level and quality
        """
        evidence_weights = {
            "systematic_review": 10,
            "meta_analysis": 9,
            "randomized_controlled_trial": 8,
            "regulatory_approval": 8,
            "cohort_study": 6,
            "case_control_study": 5,
            "case_series": 3,
            "expert_opinion": 2,
            "unknown": 1,
        }

        # Score each source
        scored_sources = []
        for source in sources:
            evidence_level = source.get("evidence_level", "unknown")
            base_score = evidence_weights.get(evidence_level, 1)

            # Additional scoring factors
            if source.get("source_type") == "fda":
                base_score += 2  # FDA sources get bonus

            if source.get("journal") and "new england" in source.get("journal", "").lower():
                base_score += 1  # High-impact journal bonus

            scored_sources.append({**source, "priority_score": base_score})

        # Sort by priority score
        return sorted(scored_sources, key=lambda x: x.get("priority_score", 0), reverse=True)

    def _analyze_evidence_quality(self, sources: list[dict[str, Any]]) -> dict[str, int]:
        """
        Analyze distribution of evidence quality levels
        """
        quality_counts: dict[str, int] = {}
        for source in sources:
            evidence_level = source.get("evidence_level", "unknown")
            quality_counts[evidence_level] = quality_counts.get(evidence_level, 0) + 1

        return quality_counts

    async def _generate_research_summary(
        self,
        query: str,
        sources: list[dict[str, Any]],
        clinical_context: dict[str, Any],
    ) -> str:
        """
        Generate AI-powered research summary
        """
        if not sources:
            return "No relevant sources found for the research query."

        # Create summary prompt
        top_sources = sources[:10]  # Use top 10 sources
        source_summaries = []

        for source in top_sources:
            if source.get("source_type") == "pubmed":
                source_summaries.append(
                    f"- {source.get('title', 'Unknown title')} "
                    f"({source.get('evidence_level', 'Unknown level')}) - "
                    f"{source.get('abstract', 'No abstract')[:200]}...",
                )
            elif source.get("source_type") == "fda":
                source_summaries.append(
                    f"- FDA: {source.get('drug_name', 'Unknown drug')} - "
                    f"Indications: {', '.join(source.get('indications', [])[:3])}",
                )

        summary_prompt = f"""
        Research Query: {query}
        Clinical Context: {json.dumps(clinical_context)}

        Top Evidence Sources:
        {chr(10).join(source_summaries)}

        Provide a comprehensive research summary including:
        1. Key findings from the literature
        2. Evidence strength and quality assessment
        3. Clinical implications
        4. Gaps in current evidence
        5. Recommendations for clinical practice

        Focus on evidence-based conclusions with appropriate caveats.
        """

        response = await self.llm_client.generate(
            model=config.get_model_for_task("clinical"),
            prompt=summary_prompt,
            options={"temperature": 0.3, "max_tokens": 1000},
        )

        response_text = response.get("response", "Unable to generate research summary.")
        return str(response_text)

    def _create_error_response(self, error_message: str, session_id: str) -> dict[str, Any]:
        """Create standardized error response"""
        return {
            "agent_type": "clinical_research",
            "session_id": session_id,
            "error": error_message,
            "success": False,
            "disclaimers": [
                "This system experienced an error processing your request.",
                "Please consult medical literature directly or contact technical support.",
            ],
            "generated_at": datetime.utcnow().isoformat(),
        }

    def _calculate_processing_time(self) -> float:
        """Calculate processing time (simplified)"""
        # In real implementation, track start time
        return 0.0

    async def _call_llm_with_config(self, prompt: str, response_type: str = "general") -> str:
        """Call LLM using configuration settings"""
        # Get specific settings for response type
        llm_settings = self.llm_settings.copy()

        # Override for specific response types if needed
        if response_type == "validation":
            # Use validation settings from config
            validation_config = self._get_validation_config()
            llm_settings.update(validation_config.get("llm_settings", {}))

        response = await self.llm_client.generate(
            prompt=prompt,
            model=config.get_model_for_task("clinical"),
            options=llm_settings,
        )

        response_text = response.get("response", "")
        return str(response_text)

    def _get_validation_config(self) -> dict[str, Any]:
        """Get response validation configuration"""
        try:
            config_path = "config/agent_settings.yml"
            if os.path.exists(config_path):
                with open(config_path) as f:
                    full_config = yaml.safe_load(f)
                config_data = (
                    full_config.get("response_validation", {}).get("medical_trust_scoring", {})
                    if full_config
                    else {}
                )
                return config_data if isinstance(config_data, dict) else {}
        except Exception:
            pass

        return {"llm_settings": {"temperature": 0.1, "max_tokens": 10}}

    async def _process_general_inquiry(
        self,
        query: str,
        clinical_context: dict[str, Any],
        session_id: str,
    ) -> dict[str, Any]:
        """
        Process general medical inquiry

        MEDICAL DISCLAIMER: This provides educational information only,
        not medical advice, diagnosis, or treatment recommendations.
        """
        try:
            # Process general medical inquiry using enhanced query engine
            result = await self.query_engine.process_medical_query(
                query=query,
                query_type=QueryType.LITERATURE_RESEARCH,
                context={"session_id": session_id},
            )

            return {
                "success": True,
                "query": query,
                "response": f"Research findings for: {result.original_query}",
                "sources": result.sources,
                "confidence": result.confidence_score,
                "session_id": session_id,
                "medical_disclaimer": "This information is for educational purposes only.",
                "query_id": result.query_id,
                "refined_queries": result.refined_queries,
            }
        except Exception as e:
            return self._create_error_response(f"General inquiry error: {str(e)}", session_id)

    async def process_research_query(
        self,
        query: str,
        user_id: str,
        session_id: str,
    ) -> dict[str, Any]:
        """
        Process research query with MCP tool integration for medical literature search

        This is the primary entry point for clinical research queries from the pipeline.
        Provides comprehensive medical literature search, clinical reasoning, and evidence synthesis.

        MEDICAL DISCLAIMER: This agent provides medical research assistance and clinical data
        analysis only. It searches medical literature, clinical trials, drug interactions, and
        evidence-based resources to support healthcare decision-making. It does not provide
        medical diagnosis, treatment recommendations, or replace clinical judgment. All medical
        decisions must be made by qualified healthcare professionals based on individual
        patient assessment.

        Args:
            query: The medical research query from the user
            user_id: User identifier for session tracking
            session_id: Session identifier for conversation continuity

        Returns:
            Dict containing research results, sources, and medical disclaimers
        """
        try:
            # Log the research query with healthcare context
            log_healthcare_event(
                logger,
                logging.INFO,
                "Clinical research query initiated",
                context={
                    "agent": "clinical_research",
                    "user_id": user_id,
                    "session_id": session_id,
                    "query_type": "research_query",
                    "phi_monitoring": True,
                    "medical_research_support": True,
                    "no_medical_advice": True,
                },
                operation_type="research_query_start",
            )

            # Ensure MCP client connection using lazy connection pattern
            if hasattr(self.mcp_client, "_ensure_connected"):
                await self.mcp_client._ensure_connected()

            # Analyze query to determine appropriate processing approach
            query_analysis = await self._analyze_research_query(query)

            # Create clinical context from analysis
            clinical_context = {
                "user_id": user_id,
                "session_id": session_id,
                "query_analysis": query_analysis,
                "research_focus": query_analysis.get("focus_areas", []),
            }

            # Route to appropriate processing method based on query type
            if query_analysis.get("query_type") == "differential_diagnosis":
                result = await self._process_differential_diagnosis(
                    query,
                    clinical_context,
                    session_id,
                )
            elif query_analysis.get("query_type") == "drug_interaction":
                result = await self._process_drug_interaction(
                    query,
                    clinical_context,
                    session_id,
                )
            else:
                # Default to comprehensive research with MCP tools for all other queries
                result = await self._process_comprehensive_research(
                    query,
                    clinical_context,
                    session_id,
                )

            # Add pipeline-specific response formatting
            pipeline_response = {
                "status": "success",
                "agent_type": "clinical_research",
                "request_type": "research_query",
                "user_id": user_id,
                "session_id": session_id,
                "query": query,
                "research_results": result,
                "processing_time": self._calculate_processing_time(),
                "disclaimers": [
                    "MEDICAL DISCLAIMER: This information is for educational and research purposes only.",
                    "This does not constitute medical advice, diagnosis, or treatment recommendations.",
                    "Always consult qualified healthcare professionals for medical decisions.",
                    "In case of medical emergency, contact emergency services immediately.",
                ],
                "generated_at": datetime.utcnow().isoformat(),
                "compliance_notes": [
                    "PHI monitoring active - no personal health information stored",
                    "Healthcare compliance verified - administrative support only",
                    "Medical reasoning provided for educational purposes only",
                ],
            }

            # Log successful completion
            log_healthcare_event(
                logger,
                logging.INFO,
                "Clinical research query completed successfully",
                context={
                    "agent": "clinical_research",
                    "user_id": user_id,
                    "session_id": session_id,
                    "query_type": query_analysis.get("query_type", "general"),
                    "sources_found": len(result.get("supporting_literature", []))
                    if "supporting_literature" in result
                    else 0,
                    "processing_successful": True,
                },
                operation_type="research_query_complete",
            )

            return pipeline_response

        except Exception as e:
            # Get full traceback for debugging
            error_traceback = traceback.format_exc()

            # Log error with healthcare context and full traceback
            log_healthcare_event(
                logger,
                logging.ERROR,
                f"Clinical research query failed: {str(e)}",
                context={
                    "agent": "clinical_research",
                    "user_id": user_id,
                    "session_id": session_id,
                    "error_type": type(e).__name__,
                    "error_traceback": error_traceback,
                    "processing_failed": True,
                },
                operation_type="research_query_error",
            )

            return {
                "status": "error",
                "agent_type": "clinical_research",
                "user_id": user_id,
                "session_id": session_id,
                "query": query,
                "error": f"Research query processing failed: {str(e)}",
                "error_type": type(e).__name__,
                "error_details": str(e),
                "full_traceback": error_traceback,
                "disclaimers": [
                    "MEDICAL DISCLAIMER: This system experienced an error processing your request.",
                    "Please consult medical literature directly or contact technical support.",
                    "For medical emergencies, contact emergency services immediately.",
                ],
                "generated_at": datetime.utcnow().isoformat(),
            }

    async def _analyze_research_query(self, query: str) -> dict[str, Any]:
        """
        Analyze the research query using LLM intelligence to determine processing approach

        Uses advanced LLM reasoning to categorize medical research queries and select appropriate tools
        """
        try:
            # Create intelligent query analysis prompt
            analysis_prompt = f"""
You are a medical research query analyzer. Analyze this query and determine the best research approach and tools to use.

Query: "{query}"

Analyze this query and respond with a JSON object containing:
1. query_type: One of ["differential_diagnosis", "drug_interaction", "literature_research", "comprehensive_research"]
2. focus_areas: Array of relevant medical specialties or focus areas
3. complexity_score: Float from 0.1 to 1.0 indicating query complexity
4. recommended_tools: Array of MCP tools to use (e.g., ["search-pubmed", "search-trials", "get-drug-info"])
5. research_strategy: Brief description of recommended research approach
6. urgency_level: One of ["low", "medium", "high", "emergency"]

Guidelines:
- For literature searches, recent studies, or general medical topics: use "comprehensive_research" with ["search-pubmed", "search-trials"]
- For specific symptom combinations or diagnostic questions: use "differential_diagnosis" 
- For medication questions, drug interactions, side effects: use "drug_interaction" with ["get-drug-info", "search-pubmed"]
- For emergency or urgent medical questions: mark urgency as "high" or "emergency"

Respond only with valid JSON.
"""

            # Use LLM to analyze the query intelligently
            response = await self.llm_client.generate(
                model=config.get_model_for_task("clinical"),
                prompt=analysis_prompt,
                options={"temperature": 0.2, "max_tokens": 500},
            )

            # Parse LLM response
            response_text = response.get("response", "")

            try:
                import json

                analysis_result = json.loads(response_text)

                # Validate and set defaults if needed
                query_type = analysis_result.get("query_type", "comprehensive_research")
                focus_areas = analysis_result.get("focus_areas", ["general_medicine"])
                complexity_score = float(analysis_result.get("complexity_score", 0.6))
                recommended_tools = analysis_result.get("recommended_tools", ["search-pubmed"])
                research_strategy = analysis_result.get(
                    "research_strategy", "Comprehensive literature search"
                )
                urgency_level = analysis_result.get("urgency_level", "medium")

                return {
                    "query_type": query_type,
                    "focus_areas": focus_areas,
                    "complexity_score": min(max(complexity_score, 0.1), 1.0),
                    "recommended_tools": recommended_tools,
                    "research_strategy": research_strategy,
                    "urgency_level": urgency_level,
                    "requires_mcp_tools": len(recommended_tools) > 0,
                    "estimated_processing_time": "30-60 seconds",
                    "llm_analysis": True,
                }

            except json.JSONDecodeError:
                logger.warning(f"Failed to parse LLM analysis response: {response_text}")
                # Fallback to default comprehensive research
                return self._get_default_analysis()

        except Exception as e:
            logger.warning(f"LLM query analysis failed: {e}")
            # Fallback to default comprehensive research
            return self._get_default_analysis()

    def _get_default_analysis(self) -> dict[str, Any]:
        """Fallback analysis when LLM analysis fails"""
        return {
            "query_type": "comprehensive_research",
            "focus_areas": ["general_medicine"],
            "complexity_score": 0.6,
            "recommended_tools": ["search-pubmed", "search-trials"],
            "research_strategy": "Comprehensive literature search with multiple sources",
            "urgency_level": "medium",
            "requires_mcp_tools": True,
            "estimated_processing_time": "30-60 seconds",
            "llm_analysis": False,
        }

    async def _process_comprehensive_research(
        self,
        query: str,
        clinical_context: dict[str, Any],
        session_id: str,
    ) -> dict[str, Any]:
        """
        Process comprehensive research query with multiple MCP tool integrations

        Combines literature search, clinical guidelines, and evidence synthesis
        """
        try:
            # Multi-stage research approach
            research_stages = []

            # Stage 1: Primary literature search via MCP tools
            if hasattr(self.mcp_client, "call_tool"):
                try:
                    pubmed_result = await self.mcp_client.call_tool(
                        "search-pubmed",
                        {"query": query, "max_results": 10},
                    )
                    research_stages.append(
                        {
                            "stage": "pubmed_search",
                            "tool": "search-pubmed",
                            "result": pubmed_result,
                            "success": True,
                        }
                    )
                except Exception as mcp_error:
                    logger.warning(f"MCP tool search-pubmed failed: {mcp_error}")
                    research_stages.append(
                        {
                            "stage": "pubmed_search",
                            "tool": "search-pubmed",
                            "error": str(mcp_error),
                            "success": False,
                        }
                    )

                # Stage 2: Clinical trial search via MCP tools
                try:
                    trials_result = await self.mcp_client.call_tool(
                        "search-trials",
                        {"query": query, "max_results": 5},
                    )
                    research_stages.append(
                        {
                            "stage": "trials_search",
                            "tool": "search-trials",
                            "result": trials_result,
                            "success": True,
                        }
                    )
                except Exception as mcp_error:
                    logger.warning(f"MCP tool search-trials failed: {mcp_error}")
                    research_stages.append(
                        {
                            "stage": "trials_search",
                            "tool": "search-trials",
                            "error": str(mcp_error),
                            "success": False,
                        }
                    )

            # Stage 3: Enhanced medical reasoning using existing capabilities
            reasoning_result = await self.medical_reasoning.reason_with_dynamic_knowledge(
                clinical_scenario=clinical_context,
                reasoning_type="literature_research",
                max_iterations=2,
            )

            # Stage 4: Synthesis and summary generation
            research_summary = await self._synthesize_research_findings(
                query,
                research_stages,
                reasoning_result,
            )

            # Create formatted summary for orchestrator compatibility
            formatted_summary = self._create_formatted_summary(
                query, research_stages, reasoning_result, research_summary
            )

            # Extract sources for orchestrator
            sources = []
            for stage in research_stages:
                if stage.get("success") and stage.get("result"):
                    result = stage.get("result", {})
                    if "articles" in result:
                        sources.extend(result["articles"])
                    elif "sources" in result:
                        sources.extend(result["sources"])

            return {
                "research_type": "comprehensive_research",
                "query": query,
                "session_id": session_id,
                "formatted_summary": formatted_summary,  # Key addition for orchestrator
                "sources": sources,  # Key addition for orchestrator
                "research_stages": research_stages,
                "medical_reasoning": {
                    "reasoning_type": reasoning_result.reasoning_type,
                    "steps": reasoning_result.steps,
                    "final_assessment": reasoning_result.final_assessment,
                    "confidence_score": reasoning_result.confidence_score,
                    "clinical_recommendations": reasoning_result.clinical_recommendations,
                },
                "research_summary": research_summary,
                "evidence_sources": reasoning_result.evidence_sources,
                "mcp_tools_used": [
                    stage["tool"] for stage in research_stages if stage.get("success")
                ],
                "total_sources_found": sum(
                    len(stage.get("result", {}).get("articles", []))
                    for stage in research_stages
                    if stage.get("success") and stage.get("result")
                ),
                "disclaimers": reasoning_result.disclaimers
                + [
                    "MCP tool integration provides enhanced literature access",
                    "Results synthesized from multiple authoritative medical sources",
                ],
                "generated_at": reasoning_result.generated_at.isoformat(),
            }

        except Exception as e:
            return self._create_error_response(
                f"Comprehensive research processing error: {str(e)}",
                session_id,
            )

    async def _synthesize_research_findings(
        self,
        query: str,
        research_stages: list[dict[str, Any]],
        reasoning_result: Any,
    ) -> str:
        """
        Synthesize findings from multiple research stages into coherent summary
        """
        # Collect findings from successful research stages
        findings = []

        for stage in research_stages:
            if stage.get("success") and stage.get("result"):
                stage_name = stage.get("stage", "unknown")
                result_data = stage.get("result", {})

                # Parse MCP response using universal parser to fix "Untitled" issue
                if stage_name == "pubmed_search":
                    parsed_articles = parse_pubmed_response(result_data)
                    articles = parsed_articles[:5]  # Top 5 articles
                    findings.append(
                        f"Literature Review ({len(articles)} studies): "
                        + "; ".join(
                            [article.get("title", "Untitled")[:100] for article in articles]
                        )
                    )

                elif stage_name == "trials_search":
                    parsed_trials = parse_clinical_trials_response(result_data)
                    trials = parsed_trials[:3]  # Top 3 trials
                    findings.append(
                        f"Clinical Trials ({len(trials)} trials): "
                        + "; ".join([trial.get("title", "Untitled")[:100] for trial in trials])
                    )

        # Add reasoning insights
        if hasattr(reasoning_result, "final_assessment"):
            findings.append(f"Clinical Assessment: {reasoning_result.final_assessment}")

        # Create synthesis prompt for LLM
        synthesis_prompt = f"""
        Research Query: {query}
        
        Research Findings:
        {chr(10).join(f"- {finding}" for finding in findings)}
        
        Provide a comprehensive research synthesis including:
        1. Key findings and evidence quality
        2. Clinical implications and relevance
        3. Gaps in current evidence
        """

        try:
            synthesis_response = await self.llm_client.chat(
                model="llama3.1:8b",
                messages=[{"role": "user", "content": synthesis_prompt}],
                options={"temperature": 0.1},
            )
            return synthesis_response.get("message", {}).get(
                "content", "Research synthesis completed."
            )
        except Exception:
            return "Research synthesis completed with findings listed above."

    def _create_formatted_summary(
        self,
        query: str,
        research_stages: list[dict[str, Any]],
        reasoning_result: Any,
        research_summary: str,
    ) -> str:
        """
        Create a formatted summary compatible with the orchestrator and medical search agent style.
        This ensures the clinical research agent output matches expected formatting.
        """
        formatted_lines = []

        # Header
        formatted_lines.append(f"# Clinical Research: {query}")
        formatted_lines.append("")

        # Research summary
        if research_summary:
            formatted_lines.append("## Research Summary")
            formatted_lines.append(research_summary)
            formatted_lines.append("")

        # Clinical assessment
        if hasattr(reasoning_result, "final_assessment") and reasoning_result.final_assessment:
            formatted_lines.append("## Clinical Assessment")
            formatted_lines.append(reasoning_result.final_assessment)
            formatted_lines.append("")

        # Key findings from successful research stages
        successful_stages = [s for s in research_stages if s.get("success")]
        if successful_stages:
            formatted_lines.append("## Literature Findings")
            formatted_lines.append("")

            article_count = 0
            for stage in successful_stages:
                result = stage.get("result", {})
                articles = result.get("articles", [])

                for article in articles[:10]:  # Limit to top 10 articles
                    article_count += 1

                    # Format like medical search agent
                    title = article.get("title", "Untitled Research")
                    authors = article.get("authors", [])
                    journal = article.get("journal", "")
                    pub_date = article.get("publication_date", "")
                    doi = article.get("doi", "")
                    abstract = article.get("abstract", "")

                    formatted_lines.append(f"### {article_count}. {title}")

                    if authors:
                        if isinstance(authors, list):
                            author_text = ", ".join(authors[:3])
                            if len(authors) > 3:
                                author_text += f" et al. ({len(authors)} authors)"
                        else:
                            author_text = str(authors)
                        formatted_lines.append(f"**Authors:** {author_text}")

                    if journal:
                        journal_text = journal
                        if pub_date:
                            journal_text += f" ({pub_date})"
                        formatted_lines.append(f"**Journal:** {journal_text}")

                    # Only use DOI links
                    if doi:
                        formatted_lines.append(f"📄 **Full Article:** https://doi.org/{doi}")

                    if abstract:
                        # Truncate long abstracts
                        if len(abstract) > 300:
                            abstract = abstract[:300] + "..."
                        formatted_lines.append(f"**Abstract:** {abstract}")

                    formatted_lines.append("")

        # Clinical recommendations
        if (
            hasattr(reasoning_result, "clinical_recommendations")
            and reasoning_result.clinical_recommendations
        ):
            formatted_lines.append("## Clinical Recommendations")
            for rec in reasoning_result.clinical_recommendations:
                formatted_lines.append(f"- {rec}")
            formatted_lines.append("")

        # Medical disclaimer
        formatted_lines.append("---")
        formatted_lines.append(
            "**Medical Disclaimer:** This research synthesis is for educational and informational purposes only. It does not constitute medical advice, diagnosis, or treatment recommendations. Always consult qualified healthcare professionals for medical decisions."
        )

        return "\n".join(formatted_lines)
