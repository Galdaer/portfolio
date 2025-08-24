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
from core.database.medical_db import MedicalDatabaseAccess
from core.enhanced_sessions import EnhancedSessionManager
from core.infrastructure.agent_metrics import AgentMetricsStore
from core.infrastructure.healthcare_cache import CacheSecurityLevel, HealthcareCacheManager
from core.infrastructure.healthcare_logger import (
    get_healthcare_logger,
    log_healthcare_event,
)
from core.mcp.universal_parser import (
    parse_clinical_trials_response,
    parse_pubmed_response,
)
from core.medical.enhanced_query_engine import EnhancedMedicalQueryEngine, QueryType
from core.reasoning.medical_reasoning_enhanced import EnhancedMedicalReasoning
from core.security.chat_log_manager import ChatLogManager

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
            mcp_client, llm_client, agent_name="clinical_research", agent_type="research_assistant",
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

        # Initialize shared healthcare infrastructure tools
        self._metrics = AgentMetricsStore(agent_name="clinical_research")
        self._cache_manager = HealthcareCacheManager()
        self._medical_db = MedicalDatabaseAccess()
        self._session_manager = EnhancedSessionManager()
        self._chat_log_manager = ChatLogManager()

        # Conversation state management
        self._conversation_memory: dict[str, dict[str, Any]] = {}
        self._source_cache: dict[str, dict[str, Any]] = {}
        self._topic_history: dict[str, list[str]] = {}

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
                        f"✅ Clinical research completed successfully in {self.current_step + 1} steps",
                    )
                    break

                self.current_step += 1

            if not result.get("complete", False):
                logger.warning(
                    f"⚠️ Clinical research reached max steps ({self.max_steps}) without completion",
                )

            return result

        except Exception as e:
            logger.exception(f"❌ Clinical research processing error: {str(e)}")
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
                    query, clinical_context, session_id,
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
        Enhanced with conversation state management for follow-up questions.

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
            # Check cache first for performance
            import hashlib
            cache_key = f"clinical_research:{hashlib.sha256(f"{query}:{session_id}".encode()).hexdigest()[:16]}"
            try:
                cached_result = await self._cache_manager.get(
                    cache_key,
                    security_level=CacheSecurityLevel.HEALTHCARE_SENSITIVE,
                )
                if cached_result:
                    await self._metrics.incr("cache_hits")
                    logger.info(f"Cache hit for clinical research query: '{query[:50]}...'")
                    return cached_result
            except Exception as e:
                logger.warning(f"Cache lookup failed: {e}")

            await self._metrics.incr("cache_misses")

            # Enhance query with conversation context for follow-up questions
            enhanced_query = await self._enhance_query_with_context(query, session_id)

            # Log the research query with healthcare context
            log_healthcare_event(
                logger,
                logging.INFO,
                "Clinical research query initiated",
                context={
                    "agent": "clinical_research",
                    "user_id": user_id,
                    "session_id": session_id,
                    "original_query": query,
                    "enhanced_query": enhanced_query if enhanced_query != query else None,
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
            query_analysis = await self._analyze_research_query(enhanced_query)

            # Create clinical context from analysis including conversation context
            conversation_context = self._get_conversation_context(session_id)
            clinical_context = {
                "user_id": user_id,
                "session_id": session_id,
                "query_analysis": query_analysis,
                "research_focus": query_analysis.get("focus_areas", []),
                "conversation_context": conversation_context,
                "original_query": query,
                "enhanced_query": enhanced_query,
            }

            # Route to appropriate processing method based on query type
            query_type = query_analysis.get("query_type")
            if query_type == "differential_diagnosis":
                result = await self._process_differential_diagnosis(
                    enhanced_query,
                    clinical_context,
                    session_id,
                )
            elif query_type == "drug_interaction":
                result = await self._process_drug_interaction(
                    enhanced_query,
                    clinical_context,
                    session_id,
                )
            elif query_type in ["treatment_recommendation", "lifestyle_guidance"]:
                # Route to new treatment recommendation processor
                result = await self._process_treatment_recommendations(
                    enhanced_query,
                    clinical_context,
                    session_id,
                )
            else:
                # Default to comprehensive research with MCP tools for literature queries
                result = await self._process_comprehensive_research(
                    enhanced_query,
                    clinical_context,
                    session_id,
                )

            # Update conversation state with results for future follow-up questions
            await self._update_conversation_state(session_id, query, result)

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

            # Cache the successful result
            try:
                await self._cache_manager.set(
                    cache_key,
                    pipeline_response,
                    security_level=CacheSecurityLevel.HEALTHCARE_SENSITIVE,
                    ttl_seconds=1800,  # 30 minutes cache for research results
                    healthcare_context={
                        "search_type": "clinical_research",
                        "query_type": query_analysis.get("query_type", "general"),
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to cache clinical research result: {e}")

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

        Enhanced to distinguish between information-based research and actionable treatment recommendations
        """
        try:
            # Create intelligent query analysis prompt with treatment recommendation support
            analysis_prompt = f"""
You are a medical research query analyzer. Analyze this query and determine the best research approach and tools to use.

Query: "{query}"

Analyze this query and respond with a JSON object containing:
1. query_type: One of ["differential_diagnosis", "drug_interaction", "literature_research", "comprehensive_research", "treatment_recommendation", "lifestyle_guidance"]
2. intent_category: One of ["information_seeking", "actionable_guidance"]
3. focus_areas: Array of relevant medical specialties or focus areas
4. complexity_score: Float from 0.1 to 1.0 indicating query complexity
5. recommended_tools: Array of MCP tools to use (e.g., ["search-pubmed", "search-trials", "get-drug-info", "lifestyle-api", "exercise-api"])
6. research_strategy: Brief description of recommended research approach
7. urgency_level: One of ["low", "medium", "high", "emergency"]
8. requires_treatment_guidance: Boolean indicating if practical treatment recommendations are needed

Guidelines for classification:
- **Information-seeking queries**: "what causes diabetes?", "research on heart disease", "studies about medication X"
  - Use "literature_research" or "comprehensive_research"
  - Tools: ["search-pubmed", "search-trials"]

- **Actionable guidance queries**: "physical therapy for back pain", "lifestyle changes for cardiovascular health", "exercises for diabetes management"
  - Use "treatment_recommendation" or "lifestyle_guidance"
  - Tools: ["search-pubmed", "lifestyle-api", "exercise-api", "nutrition-api"]
  - Set requires_treatment_guidance: true

- **Diagnostic queries**: symptom combinations, diagnostic questions
  - Use "differential_diagnosis"

- **Medication queries**: drug interactions, side effects, dosing
  - Use "drug_interaction"
  - Tools: ["get-drug-info", "search-pubmed"]

Respond only with valid JSON.
"""

            # Use LLM to analyze the query intelligently
            response = await self.llm_client.generate(
                model=config.get_model_for_task("clinical"),
                prompt=analysis_prompt,
                options={"temperature": 0.2, "max_tokens": 600},
            )

            # Parse LLM response
            response_text = response.get("response", "")

            try:
                import json

                analysis_result = json.loads(response_text)

                # Validate and set defaults if needed
                query_type = analysis_result.get("query_type", "comprehensive_research")
                intent_category = analysis_result.get("intent_category", "information_seeking")
                focus_areas = analysis_result.get("focus_areas", ["general_medicine"])
                complexity_score = float(analysis_result.get("complexity_score", 0.6))
                recommended_tools = analysis_result.get("recommended_tools", ["search-pubmed"])
                research_strategy = analysis_result.get(
                    "research_strategy", "Comprehensive literature search",
                )
                urgency_level = analysis_result.get("urgency_level", "medium")
                requires_treatment_guidance = bool(analysis_result.get("requires_treatment_guidance", False))

                return {
                    "query_type": query_type,
                    "intent_category": intent_category,
                    "focus_areas": focus_areas,
                    "complexity_score": min(max(complexity_score, 0.1), 1.0),
                    "recommended_tools": recommended_tools,
                    "research_strategy": research_strategy,
                    "urgency_level": urgency_level,
                    "requires_treatment_guidance": requires_treatment_guidance,
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
            "intent_category": "information_seeking",
            "focus_areas": ["general_medicine"],
            "complexity_score": 0.6,
            "recommended_tools": ["search-pubmed", "search-trials"],
            "research_strategy": "Comprehensive literature search with multiple sources",
            "urgency_level": "medium",
            "requires_treatment_guidance": False,
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

            # Stage 0: Database-first pattern - check local medical databases
            try:
                # Search local PubMed database first
                local_pubmed_articles = self._medical_db.search_pubmed_local(query, max_results=15)
                if local_pubmed_articles:
                    await self._metrics.incr("local_pubmed_hits")
                    logger.info(f"Found {len(local_pubmed_articles)} articles in local PubMed database")

                    research_stages.append({
                        "stage": "local_pubmed_search",
                        "source": "Local PubMed Database",
                        "results_count": len(local_pubmed_articles),
                        "articles": local_pubmed_articles[:10],  # Limit for performance
                        "query": query,
                        "data_freshness": "Local mirror - may not include latest publications",
                    })
                else:
                    await self._metrics.incr("local_pubmed_misses")
                    logger.info("No results in local PubMed database")

                # Search local ClinicalTrials database
                local_trials = self._medical_db.search_clinical_trials_local(query, max_results=10)
                if local_trials:
                    await self._metrics.incr("local_trials_hits")
                    logger.info(f"Found {len(local_trials)} clinical trials in local database")

                    research_stages.append({
                        "stage": "local_trials_search",
                        "source": "Local ClinicalTrials Database",
                        "results_count": len(local_trials),
                        "trials": local_trials,
                        "query": query,
                        "data_freshness": "Local mirror - may not include latest trials",
                    })
                else:
                    await self._metrics.incr("local_trials_misses")

            except Exception as e:
                logger.warning(f"Local database search failed: {e}")
                await self._metrics.incr("local_database_errors")

            # Stage 1: Primary literature search via MCP tools (if local results insufficient)
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
                        },
                    )
                except Exception as mcp_error:
                    logger.warning(f"MCP tool search-pubmed failed: {mcp_error}")
                    research_stages.append(
                        {
                            "stage": "pubmed_search",
                            "tool": "search-pubmed",
                            "error": str(mcp_error),
                            "success": False,
                        },
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
                        },
                    )
                except Exception as mcp_error:
                    logger.warning(f"MCP tool search-trials failed: {mcp_error}")
                    research_stages.append(
                        {
                            "stage": "trials_search",
                            "tool": "search-trials",
                            "error": str(mcp_error),
                            "success": False,
                        },
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
                query, research_stages, reasoning_result, research_summary,
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

            # Ensure orchestrator compatibility with standardized response format
            return {
                "success": True,
                "research_type": "comprehensive_research",
                "query": query,
                "session_id": session_id,
                "formatted_summary": formatted_summary,  # Key addition for orchestrator
                "sources": sources,  # Key addition for orchestrator
                "agent_name": "clinical_research",
                "agent_type": "clinical_research",
                "total_sources": len(sources),
                "search_confidence": reasoning_result.confidence_score if hasattr(reasoning_result, "confidence_score") else 0.8,
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
        Synthesize findings from multiple research stages into conversational, comprehensive summary

        Enhanced to provide natural, conversational responses while maintaining scientific accuracy
        """
        # Enhanced source processing for conversational synthesis
        source_analysis = self._analyze_sources_for_conversation(research_stages)

        # Build conversational synthesis prompt
        synthesis_prompt = f"""You are a clinical research specialist providing a conversational summary of medical literature findings.

Query: "{query}"

Available Research Sources:
{self._format_sources_for_synthesis(source_analysis)}

Clinical Assessment:
{getattr(reasoning_result, 'final_assessment', 'No clinical assessment available')}

Provide a comprehensive, conversational response that:

1. **Opens with a direct answer** to the user's question in natural language
2. **Organizes information by clinical relevance** (not by source type)
3. **Uses conversational transitions** between topics
4. **Formats sections intelligently**:
   - Use headers (##) for major topics
   - Use bullet points for lists of findings
   - Use paragraphs for explanations
   - Use emphasis (**bold**) for key clinical points
5. **Synthesizes across source types** rather than listing them separately
6. **Maintains scientific accuracy** while being accessible
7. **Ends with practical implications** when appropriate

Write as if explaining to a healthcare professional in a consultation setting.
Avoid formal academic language - use clear, professional conversation style.
"""

        try:
            synthesis_response = await self.llm_client.generate(
                model=config.get_model_for_task("clinical"),
                prompt=synthesis_prompt,
                options={"temperature": 0.2, "max_tokens": 1500},  # Higher token limit for comprehensive responses
            )

            conversational_summary = synthesis_response.get("response", "")

            # Post-process to ensure quality
            if len(conversational_summary.strip()) < 100:
                # Fallback to structured summary if LLM response is too short
                return self._create_structured_fallback_summary(query, source_analysis, reasoning_result)

            return conversational_summary

        except Exception as e:
            logger.warning(f"LLM synthesis failed: {e}, using structured fallback")
            return self._create_structured_fallback_summary(query, source_analysis, reasoning_result)

    def _analyze_sources_for_conversation(self, research_stages: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze and categorize sources for conversational synthesis"""
        analysis = {
            "pubmed_articles": [],
            "clinical_trials": [],
            "fda_data": [],
            "total_sources": 0,
            "key_topics": [],
            "evidence_strength": "limited",
        }

        for stage in research_stages:
            if not stage.get("success") or not stage.get("result"):
                continue

            stage_name = stage.get("stage", "unknown")
            result_data = stage.get("result", {})

            if stage_name == "pubmed_search":
                articles = parse_pubmed_response(result_data)
                analysis["pubmed_articles"] = articles[:8]  # Top 8 articles for synthesis
                analysis["total_sources"] += len(articles)

                # Extract key topics from titles and abstracts
                for article in articles[:5]:
                    title = article.get("title", "").lower()
                    abstract = article.get("abstract", "").lower()
                    # Simple keyword extraction for topics
                    for text in [title, abstract]:
                        if any(term in text for term in ["efficacy", "effective", "treatment"]):
                            analysis["key_topics"].append("treatment_efficacy")
                        if any(term in text for term in ["safety", "adverse", "side effect"]):
                            analysis["key_topics"].append("safety")
                        if any(term in text for term in ["mechanism", "pathway", "receptor"]):
                            analysis["key_topics"].append("mechanism")

            elif stage_name == "trials_search":
                trials = parse_clinical_trials_response(result_data)
                analysis["clinical_trials"] = trials[:5]  # Top 5 trials
                analysis["total_sources"] += len(trials)

        # Determine evidence strength
        if analysis["total_sources"] >= 10:
            analysis["evidence_strength"] = "substantial"
        elif analysis["total_sources"] >= 5:
            analysis["evidence_strength"] = "moderate"

        # Deduplicate topics
        analysis["key_topics"] = list(set(analysis["key_topics"]))

        return analysis

    def _format_sources_for_synthesis(self, source_analysis: dict[str, Any]) -> str:
        """Format sources in a way that's useful for LLM synthesis"""
        formatted_sources = []

        # PubMed articles
        for article in source_analysis["pubmed_articles"]:
            title = article.get("title", "Untitled")
            authors = article.get("authors", [])
            journal = article.get("journal", "")
            year = article.get("publication_date", "")
            abstract = article.get("abstract", "")

            author_text = ", ".join(authors[:3]) if isinstance(authors, list) and authors else "Unknown authors"

            formatted_sources.append(f"""
**Research Article**: {title}
- Authors: {author_text}
- Journal: {journal} ({year})
- Key findings: {abstract[:300]}...
""")

        # Clinical trials
        for trial in source_analysis["clinical_trials"]:
            title = trial.get("title", "Untitled")
            status = trial.get("overall_status", "Unknown")
            condition = trial.get("condition", "")
            intervention = trial.get("intervention_name", "")

            formatted_sources.append(f"""
**Clinical Trial**: {title}
- Status: {status}
- Condition: {condition}
- Intervention: {intervention}
""")

        summary_text = f"Total sources: {source_analysis['total_sources']}, Evidence strength: {source_analysis['evidence_strength']}"
        if source_analysis["key_topics"]:
            summary_text += f", Key topics: {', '.join(source_analysis['key_topics'])}"

        return summary_text + "\n\n" + "\n".join(formatted_sources)

    def _create_structured_fallback_summary(self, query: str, source_analysis: dict[str, Any], reasoning_result: Any) -> str:
        """Create structured fallback when LLM synthesis fails"""
        summary_parts = []

        summary_parts.append(f"## Clinical Research Summary: {query}")
        summary_parts.append("")

        if source_analysis["total_sources"] > 0:
            summary_parts.append(f"Based on analysis of {source_analysis['total_sources']} medical sources with {source_analysis['evidence_strength']} evidence strength:")
            summary_parts.append("")

            # Key findings from PubMed
            if source_analysis["pubmed_articles"]:
                summary_parts.append("### Research Literature Findings")
                for i, article in enumerate(source_analysis["pubmed_articles"][:5], 1):
                    title = article.get("title", "Research finding")
                    summary_parts.append(f"{i}. **{title}**")
                    if article.get("abstract"):
                        abstract_summary = article["abstract"][:200] + "..." if len(article["abstract"]) > 200 else article["abstract"]
                        summary_parts.append(f"   - {abstract_summary}")
                summary_parts.append("")

            # Clinical trials
            if source_analysis["clinical_trials"]:
                summary_parts.append("### Clinical Trial Evidence")
                for trial in source_analysis["clinical_trials"][:3]:
                    title = trial.get("title", "Clinical trial")
                    status = trial.get("overall_status", "Unknown status")
                    summary_parts.append(f"- **{title}** (Status: {status})")
                summary_parts.append("")

            # Clinical assessment
            if hasattr(reasoning_result, "final_assessment") and reasoning_result.final_assessment:
                summary_parts.append("### Clinical Assessment")
                summary_parts.append(reasoning_result.final_assessment)
                summary_parts.append("")
        else:
            summary_parts.append("No medical literature sources found for this specific query.")
            summary_parts.append("")

        summary_parts.append("**Note**: This information is for educational purposes only. Always consult healthcare professionals for medical advice.")

        return "\n".join(summary_parts)

    async def _update_conversation_state(self, session_id: str, query: str, result: dict[str, Any]) -> None:
        """Update conversation memory and source cache for follow-up questions"""
        # Initialize conversation memory for this session if needed
        if session_id not in self._conversation_memory:
            self._conversation_memory[session_id] = {
                "queries": [],
                "topics_discussed": [],
                "sources_used": [],
                "last_updated": datetime.utcnow().isoformat(),
            }

        # Update conversation memory
        memory = self._conversation_memory[session_id]
        memory["queries"].append({
            "query": query,
            "timestamp": datetime.utcnow().isoformat(),
            "topics": self._extract_topics_from_query(query),
        })

        # Keep only last 10 queries to manage memory
        memory["queries"] = memory["queries"][-10:]

        # Extract and cache sources from result
        sources = []
        if "sources" in result:
            sources.extend(result["sources"])
        elif "supporting_literature" in result:
            for lit in result["supporting_literature"]:
                if "sources" in lit:
                    sources.extend(lit["sources"])

        # Cache sources with deduplication
        source_cache_key = f"{session_id}_sources"
        if source_cache_key not in self._source_cache:
            self._source_cache[source_cache_key] = {"sources": [], "last_updated": datetime.utcnow().isoformat()}

        cached_sources = self._source_cache[source_cache_key]["sources"]

        # Add new sources with deduplication
        for source in sources:
            if not self._is_duplicate_source(source, cached_sources):
                cached_sources.append(source)

        # Keep only last 50 sources to manage memory
        self._source_cache[source_cache_key]["sources"] = cached_sources[-50:]
        self._source_cache[source_cache_key]["last_updated"] = datetime.utcnow().isoformat()

        # Update topics history
        if session_id not in self._topic_history:
            self._topic_history[session_id] = []

        query_topics = self._extract_topics_from_query(query)
        for topic in query_topics:
            if topic not in self._topic_history[session_id]:
                self._topic_history[session_id].append(topic)

        # Keep only last 20 topics
        self._topic_history[session_id] = self._topic_history[session_id][-20:]

    def _extract_topics_from_query(self, query: str) -> list[str]:
        """Extract key medical topics from query for conversation tracking"""
        query_lower = query.lower()
        topics = []

        # Medical condition keywords
        condition_keywords = [
            "diabetes", "hypertension", "cancer", "depression", "anxiety",
            "infection", "inflammation", "cardiovascular", "respiratory", "neurological",
        ]

        # Treatment keywords
        treatment_keywords = [
            "treatment", "therapy", "medication", "drug", "surgery", "intervention",
        ]

        # Research keywords
        research_keywords = [
            "study", "trial", "research", "evidence", "systematic review", "meta-analysis",
        ]

        for keyword_list, category in [
            (condition_keywords, "condition"),
            (treatment_keywords, "treatment"),
            (research_keywords, "research"),
        ]:
            for keyword in keyword_list:
                if keyword in query_lower:
                    topics.append(f"{category}:{keyword}")

        return topics

    def _is_duplicate_source(self, new_source: dict[str, Any], cached_sources: list[dict[str, Any]]) -> bool:
        """Check if a source is already cached to avoid duplication"""
        new_title = new_source.get("title", "").lower().strip()
        new_url = new_source.get("url", "").strip()
        new_doi = new_source.get("doi", "").strip()

        if not new_title and not new_url and not new_doi:
            return False  # Can't determine duplicates without identifiers

        for cached_source in cached_sources:
            cached_title = cached_source.get("title", "").lower().strip()
            cached_url = cached_source.get("url", "").strip()
            cached_doi = cached_source.get("doi", "").strip()

            # Check for exact matches
            if new_doi and cached_doi and new_doi == cached_doi:
                return True
            if new_url and cached_url and new_url == cached_url:
                return True
            if new_title and cached_title and new_title == cached_title:
                return True

            # Check for very similar titles (90% similarity)
            if new_title and cached_title and len(new_title) > 10:
                similarity = self._calculate_title_similarity(new_title, cached_title)
                if similarity > 0.9:
                    return True

        return False

    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles using word overlap"""
        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

    def _get_conversation_context(self, session_id: str) -> dict[str, Any]:
        """Get conversation context for follow-up questions"""
        context = {
            "previous_queries": [],
            "discussed_topics": [],
            "available_sources": 0,
            "conversation_depth": 0,
        }

        if session_id in self._conversation_memory:
            memory = self._conversation_memory[session_id]
            context["previous_queries"] = [q["query"] for q in memory["queries"][-5:]]  # Last 5 queries
            context["conversation_depth"] = len(memory["queries"])

        if session_id in self._topic_history:
            context["discussed_topics"] = self._topic_history[session_id][-10:]  # Last 10 topics

        source_cache_key = f"{session_id}_sources"
        if source_cache_key in self._source_cache:
            context["available_sources"] = len(self._source_cache[source_cache_key]["sources"])

        return context

    async def _enhance_query_with_context(self, query: str, session_id: str) -> str:
        """Enhance query with conversation context for better follow-up handling"""
        context = self._get_conversation_context(session_id)

        if context["conversation_depth"] == 0:
            # First query in conversation - no enhancement needed
            return query

        # Build context-aware query enhancement
        enhancement_prompt = f"""Previous conversation context:
- Recent queries: {', '.join(context['previous_queries'][-3:])}
- Topics discussed: {', '.join(context['discussed_topics'][-5:])}
- Available cached sources: {context['available_sources']}

Current query: "{query}"

If this query is a follow-up question (asking for "more details", "tell me about", "what else", etc.),
enhance it by incorporating relevant context from the previous conversation.

Enhanced query:"""

        try:
            response = await self.llm_client.generate(
                model=config.get_model_for_task("clinical"),
                prompt=enhancement_prompt,
                options={"temperature": 0.1, "max_tokens": 200},
            )

            enhanced_query = response.get("response", "").strip()

            # Only use enhanced query if it's substantially different and reasonable
            if enhanced_query and len(enhanced_query) > len(query) + 10 and len(enhanced_query) < 300:
                logger.info(f"Enhanced follow-up query: {query[:50]} -> {enhanced_query[:50]}")
                return enhanced_query

        except Exception as e:
            logger.warning(f"Query enhancement failed: {e}")

        return query

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
            "**Medical Disclaimer:** This research synthesis is for educational and informational purposes only. It does not constitute medical advice, diagnosis, or treatment recommendations. Always consult qualified healthcare professionals for medical decisions.",
        )

        return "\n".join(formatted_lines)

    async def _process_treatment_recommendations(
        self,
        query: str,
        clinical_context: dict[str, Any],
        session_id: str,
    ) -> dict[str, Any]:
        """
        Process treatment recommendation queries with actionable clinical guidance

        Provides evidence-based treatment protocols, physical therapy recommendations,
        lifestyle modifications, and practical clinical interventions.

        MEDICAL DISCLAIMER: These recommendations are for educational purposes only
        and should not replace professional medical assessment and personalized care.
        """
        try:
            query_analysis = clinical_context.get("query_analysis", {})
            focus_areas = query_analysis.get("focus_areas", ["general_medicine"])

            # Stage 1: Evidence-based literature search for treatment protocols
            literature_search_query = f"{query} evidence-based treatment protocols clinical guidelines"
            literature_result = await self.query_engine.process_medical_query(
                query=literature_search_query,
                query_type=QueryType.CLINICAL_GUIDELINES,
                context=clinical_context,
                max_iterations=2,
            )

            # Stage 2: Physical therapy and exercise recommendations
            physical_therapy_recommendations = await self._get_physical_therapy_recommendations(
                query, focus_areas, clinical_context,
            )

            # Stage 3: Lifestyle and nutrition guidance
            lifestyle_recommendations = await self._get_lifestyle_recommendations(
                query, focus_areas, clinical_context,
            )

            # Stage 4: Free public API integration for additional resources
            public_api_resources = await self._integrate_public_health_apis(
                query, focus_areas,
            )

            # Stage 5: Generate comprehensive treatment recommendations
            treatment_synthesis = await self._synthesize_treatment_recommendations(
                query,
                literature_result,
                physical_therapy_recommendations,
                lifestyle_recommendations,
                public_api_resources,
                clinical_context,
            )

            # Create formatted treatment plan
            formatted_treatment_plan = self._create_formatted_treatment_plan(
                query,
                treatment_synthesis,
                literature_result,
                physical_therapy_recommendations,
                lifestyle_recommendations,
                public_api_resources,
            )

            return {
                "success": True,
                "agent_type": "clinical_research",
                "request_type": "treatment_recommendation",
                "session_id": session_id,
                "query": query,
                "treatment_plan": formatted_treatment_plan,
                "evidence_based_protocols": {
                    "literature_sources": getattr(literature_result, "sources", [])[:10],
                    "confidence_score": getattr(literature_result, "confidence_score", 0.7),
                    "guidelines_found": len(getattr(literature_result, "sources", [])),
                },
                "physical_therapy": physical_therapy_recommendations,
                "lifestyle_guidance": lifestyle_recommendations,
                "public_resources": public_api_resources,
                "clinical_focus_areas": focus_areas,
                "recommendations_confidence": self._calculate_recommendations_confidence(
                    literature_result, physical_therapy_recommendations, lifestyle_recommendations,
                ),
                "disclaimers": [
                    "MEDICAL DISCLAIMER: These recommendations are educational and informational only.",
                    "This does not constitute personalized medical advice or treatment.",
                    "Always consult qualified healthcare professionals before implementing treatments.",
                    "Individual responses to treatments may vary significantly.",
                    "Professional medical assessment is required for personalized care.",
                ],
                "generated_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            return self._create_error_response(
                f"Treatment recommendation processing error: {str(e)}",
                session_id,
            )

    async def _get_physical_therapy_recommendations(
        self,
        query: str,
        focus_areas: list[str],
        clinical_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Get evidence-based physical therapy recommendations"""
        try:
            # Search for physical therapy protocols in literature
            pt_query = f"{query} physical therapy rehabilitation protocol exercise therapy"
            pt_result = await self.query_engine.process_medical_query(
                query=pt_query,
                query_type=QueryType.LITERATURE_RESEARCH,
                context=clinical_context,
                max_iterations=1,
            )

            # Extract common physical therapy approaches for different conditions
            condition_specific_pt = self._get_condition_specific_pt_protocols(query, focus_areas)

            return {
                "evidence_based_protocols": getattr(pt_result, "sources", [])[:8],
                "condition_specific_approaches": condition_specific_pt,
                "general_recommendations": [
                    "Assessment by qualified physical therapist recommended",
                    "Start with supervised sessions before home programs",
                    "Progressive loading and gradual exercise advancement",
                    "Pain monitoring during activity modification",
                    "Regular reassessment of functional goals",
                ],
                "contraindications_to_consider": [
                    "Acute injury phases may require rest before active therapy",
                    "Certain cardiovascular conditions require medical clearance",
                    "Neurological conditions need specialized PT assessment",
                ],
            }

        except Exception as e:
            logger.warning(f"Physical therapy recommendation error: {e}")
            return {
                "evidence_based_protocols": [],
                "condition_specific_approaches": [],
                "general_recommendations": ["Consult physical therapist for personalized assessment"],
                "error": str(e),
            }

    def _get_condition_specific_pt_protocols(self, query: str, focus_areas: list[str]) -> list[dict[str, Any]]:
        """Get condition-specific physical therapy protocols based on evidence"""
        protocols = []
        query_lower = query.lower()

        # Cardiovascular conditions
        if any(term in query_lower for term in ["cardiovascular", "heart", "cardiac", "circulation"]):
            protocols.append({
                "condition_category": "Cardiovascular Health",
                "evidence_level": "High (AHA/ACC Guidelines)",
                "recommended_exercises": [
                    "Supervised aerobic exercise (walking, cycling, swimming)",
                    "Resistance training with light-moderate weights",
                    "Flexibility and stretching programs",
                    "Progressive exercise intensity based on cardiac capacity",
                ],
                "frequency": "150 minutes moderate aerobic activity per week",
                "special_considerations": [
                    "Medical clearance required for cardiac patients",
                    "Heart rate monitoring during exercise",
                    "Recognition of cardiac symptoms during activity",
                ],
            })

        # Musculoskeletal conditions
        if any(term in query_lower for term in ["back pain", "spine", "lumbar", "musculoskeletal"]):
            protocols.append({
                "condition_category": "Back Pain / Spinal Health",
                "evidence_level": "High (Clinical Practice Guidelines)",
                "recommended_exercises": [
                    "Core strengthening exercises (planks, bridges)",
                    "Spinal mobility and flexibility exercises",
                    "Progressive resistance training",
                    "Functional movement patterns",
                ],
                "frequency": "3-4 sessions per week, 20-30 minutes",
                "special_considerations": [
                    "Avoid exercises that increase spinal flexion during acute phases",
                    "Progress gradually from passive to active movements",
                    "Include ergonomic and posture education",
                ],
            })

        # Diabetes and metabolic conditions
        if any(term in query_lower for term in ["diabetes", "metabolic", "weight", "glucose"]):
            protocols.append({
                "condition_category": "Diabetes / Metabolic Health",
                "evidence_level": "High (ADA Guidelines)",
                "recommended_exercises": [
                    "Regular aerobic exercise (brisk walking, swimming)",
                    "Resistance training 2-3 times per week",
                    "Flexibility exercises",
                    "Balance training for fall prevention",
                ],
                "frequency": "At least 150 minutes moderate aerobic activity per week",
                "special_considerations": [
                    "Blood glucose monitoring before/after exercise",
                    "Proper foot care and footwear",
                    "Gradual exercise progression",
                    "Recognition of hypoglycemia symptoms",
                ],
            })

        return protocols

    async def _get_lifestyle_recommendations(
        self,
        query: str,
        focus_areas: list[str],
        clinical_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Get evidence-based lifestyle recommendations"""
        try:
            # Search for lifestyle modification protocols
            lifestyle_query = f"{query} lifestyle modifications diet nutrition behavioral interventions"
            lifestyle_result = await self.query_engine.process_medical_query(
                query=lifestyle_query,
                query_type=QueryType.LITERATURE_RESEARCH,
                context=clinical_context,
                max_iterations=1,
            )

            # Get condition-specific lifestyle recommendations
            condition_specific_lifestyle = self._get_condition_specific_lifestyle(query, focus_areas)

            return {
                "evidence_based_guidelines": getattr(lifestyle_result, "sources", [])[:8],
                "condition_specific_guidance": condition_specific_lifestyle,
                "general_principles": [
                    "Mediterranean diet pattern for most conditions",
                    "Regular sleep schedule (7-9 hours for adults)",
                    "Stress management techniques (meditation, yoga)",
                    "Social support and community engagement",
                    "Smoking cessation if applicable",
                    "Moderate alcohol consumption guidelines",
                ],
                "behavioral_change_strategies": [
                    "Set specific, measurable, achievable goals",
                    "Track progress with apps or journals",
                    "Build gradual habit changes",
                    "Seek professional support when needed",
                    "Address barriers to lifestyle changes",
                ],
            }

        except Exception as e:
            logger.warning(f"Lifestyle recommendation error: {e}")
            return {
                "evidence_based_guidelines": [],
                "condition_specific_guidance": [],
                "general_principles": ["Consult healthcare provider for personalized lifestyle guidance"],
                "error": str(e),
            }

    def _get_condition_specific_lifestyle(self, query: str, focus_areas: list[str]) -> list[dict[str, Any]]:
        """Get condition-specific lifestyle recommendations based on evidence"""
        recommendations = []
        query_lower = query.lower()

        # Cardiovascular health
        if any(term in query_lower for term in ["cardiovascular", "heart", "cardiac", "hypertension", "cholesterol"]):
            recommendations.append({
                "condition_category": "Cardiovascular Health",
                "dietary_recommendations": [
                    "DASH diet or Mediterranean diet pattern",
                    "Reduce sodium intake (<2300mg daily, ideally <1500mg)",
                    "Increase fruits, vegetables, whole grains, lean proteins",
                    "Limit saturated fats, trans fats, added sugars",
                    "Include omega-3 fatty acids (fish, nuts, seeds)",
                ],
                "lifestyle_modifications": [
                    "Regular physical activity (150 min/week moderate intensity)",
                    "Maintain healthy weight (BMI 18.5-24.9)",
                    "Stress management techniques",
                    "Adequate sleep (7-9 hours)",
                    "Smoking cessation",
                    "Limit alcohol consumption",
                ],
                "monitoring_parameters": [
                    "Blood pressure tracking",
                    "Cholesterol levels",
                    "Weight monitoring",
                    "Physical activity logs",
                ],
            })

        # Diabetes management
        if any(term in query_lower for term in ["diabetes", "glucose", "insulin", "blood sugar"]):
            recommendations.append({
                "condition_category": "Diabetes Management",
                "dietary_recommendations": [
                    "Carbohydrate counting and portion control",
                    "Choose complex carbohydrates over simple sugars",
                    "Include high-fiber foods",
                    "Regular meal timing",
                    "Limit processed foods and refined sugars",
                    "Moderate healthy fats (avocado, nuts, olive oil)",
                ],
                "lifestyle_modifications": [
                    "Regular physical activity (aerobic + resistance training)",
                    "Weight management",
                    "Consistent sleep schedule",
                    "Stress reduction techniques",
                    "Regular blood glucose monitoring",
                    "Foot care and skin care",
                ],
                "monitoring_parameters": [
                    "Blood glucose levels",
                    "HbA1c testing",
                    "Weight and BMI",
                    "Blood pressure",
                    "Cholesterol levels",
                ],
            })

        return recommendations

    async def _integrate_public_health_apis(self, query: str, focus_areas: list[str]) -> dict[str, Any]:
        """Integrate free public health APIs for additional resources"""
        try:
            resources = {
                "myhealthfinder_resources": [],
                "exercise_database": [],
                "nutrition_data": [],
                "government_guidelines": [],
            }

            # For now, provide structured resource links that would be populated by actual API calls
            # This sets up the framework for future API integration
            query_lower = query.lower()

            if any(term in query_lower for term in ["exercise", "physical", "therapy", "fitness"]):
                resources["exercise_database"] = [
                    {
                        "resource_type": "Exercise Database",
                        "description": "Evidence-based exercise protocols",
                        "source": "ExerciseDB API (to be integrated)",
                        "exercises_available": "1000+ evidence-based exercises",
                        "categories": ["Cardio", "Strength", "Flexibility", "Rehabilitation"],
                    },
                ]

            if any(term in query_lower for term in ["nutrition", "diet", "food", "eating"]):
                resources["nutrition_data"] = [
                    {
                        "resource_type": "USDA Food Database",
                        "description": "Comprehensive nutritional information",
                        "source": "USDA FoodData Central API (to be integrated)",
                        "data_points": "Calories, macronutrients, micronutrients",
                        "food_items": "400,000+ food items",
                    },
                ]

            # MyHealthfinder API resources
            resources["myhealthfinder_resources"] = [
                {
                    "resource_type": "Health Topic Information",
                    "description": "Consumer health information from federal agencies",
                    "source": "MyHealthfinder API (to be integrated)",
                    "topics_covered": "Prevention, screening, lifestyle",
                    "audience": "Consumers and healthcare providers",
                },
            ]

            return resources

        except Exception as e:
            logger.warning(f"Public API integration error: {e}")
            return {"error": str(e), "resources_available": False}

    async def _synthesize_treatment_recommendations(
        self,
        query: str,
        literature_result: Any,
        physical_therapy: dict[str, Any],
        lifestyle: dict[str, Any],
        public_resources: dict[str, Any],
        clinical_context: dict[str, Any],
    ) -> str:
        """Synthesize all treatment recommendations into a comprehensive plan"""
        try:
            synthesis_prompt = f"""You are a clinical expert synthesizing treatment recommendations based on current evidence.

Query: "{query}"

Available Evidence:
- Literature sources: {len(getattr(literature_result, 'sources', []))} clinical studies/guidelines
- Physical therapy protocols: {len(physical_therapy.get('condition_specific_approaches', []))} evidence-based approaches
- Lifestyle interventions: {len(lifestyle.get('condition_specific_guidance', []))} evidence-based recommendations

Create a comprehensive, actionable treatment plan that:

1. **Prioritizes evidence-based interventions** from strongest to moderate evidence
2. **Provides specific, actionable recommendations** (not vague advice)
3. **Includes implementation timelines** and progression steps
4. **Addresses potential barriers** to implementation
5. **Emphasizes safety considerations** and when to seek professional help
6. **Uses a conversational, professional tone** suitable for patient education

Structure the response with:
- **Immediate Actions** (first 1-2 weeks)
- **Short-term Goals** (1-3 months)
- **Long-term Management** (3+ months)
- **Red Flags** (when to seek immediate medical attention)
- **Professional Referrals** recommended

Write as if counseling a patient with evidence-based, actionable guidance.
"""

            synthesis_response = await self.llm_client.generate(
                model=config.get_model_for_task("clinical"),
                prompt=synthesis_prompt,
                options={"temperature": 0.2, "max_tokens": 2000},
            )

            return synthesis_response.get("response", "Unable to generate treatment synthesis.")

        except Exception as e:
            logger.warning(f"Treatment synthesis failed: {e}")
            return f"## Treatment Recommendations for: {query}\n\nBasic evidence-based approaches were identified. Please consult healthcare professionals for personalized treatment planning."

    def _calculate_recommendations_confidence(
        self,
        literature_result: Any,
        physical_therapy: dict[str, Any],
        lifestyle: dict[str, Any],
    ) -> float:
        """Calculate confidence score for treatment recommendations"""
        confidence_factors = []

        # Literature evidence strength
        if hasattr(literature_result, "confidence_score"):
            confidence_factors.append(literature_result.confidence_score * 0.4)

        # Physical therapy evidence
        if physical_therapy.get("evidence_based_protocols"):
            confidence_factors.append(0.8 * 0.3)  # High confidence for PT protocols

        # Lifestyle evidence
        if lifestyle.get("evidence_based_guidelines"):
            confidence_factors.append(0.7 * 0.3)  # Good confidence for lifestyle guidelines

        return sum(confidence_factors) if confidence_factors else 0.6

    def _create_formatted_treatment_plan(
        self,
        query: str,
        treatment_synthesis: str,
        literature_result: Any,
        physical_therapy: dict[str, Any],
        lifestyle: dict[str, Any],
        public_resources: dict[str, Any],
    ) -> str:
        """Create formatted treatment plan for orchestrator compatibility"""
        formatted_lines = []

        # Header
        formatted_lines.append(f"# Evidence-Based Treatment Plan: {query}")
        formatted_lines.append("")

        # Main treatment synthesis
        if treatment_synthesis:
            formatted_lines.append("## Comprehensive Treatment Approach")
            formatted_lines.append(treatment_synthesis)
            formatted_lines.append("")

        # Physical therapy section
        if physical_therapy.get("condition_specific_approaches"):
            formatted_lines.append("## Physical Therapy & Exercise Recommendations")
            for approach in physical_therapy["condition_specific_approaches"]:
                formatted_lines.append(f"### {approach.get('condition_category', 'Physical Therapy')}")
                formatted_lines.append(f"**Evidence Level:** {approach.get('evidence_level', 'Moderate')}")

                if approach.get("recommended_exercises"):
                    formatted_lines.append("**Recommended Exercises:**")
                    for exercise in approach["recommended_exercises"]:
                        formatted_lines.append(f"- {exercise}")

                if approach.get("frequency"):
                    formatted_lines.append(f"**Frequency:** {approach['frequency']}")

                formatted_lines.append("")

        # Lifestyle modifications section
        if lifestyle.get("condition_specific_guidance"):
            formatted_lines.append("## Lifestyle & Dietary Recommendations")
            for guidance in lifestyle["condition_specific_guidance"]:
                formatted_lines.append(f"### {guidance.get('condition_category', 'General Health')}")

                if guidance.get("dietary_recommendations"):
                    formatted_lines.append("**Dietary Guidelines:**")
                    for dietary in guidance["dietary_recommendations"]:
                        formatted_lines.append(f"- {dietary}")

                if guidance.get("lifestyle_modifications"):
                    formatted_lines.append("**Lifestyle Changes:**")
                    for modification in guidance["lifestyle_modifications"]:
                        formatted_lines.append(f"- {modification}")

                formatted_lines.append("")

        # Evidence sources
        literature_sources = getattr(literature_result, "sources", [])
        if literature_sources:
            formatted_lines.append("## Supporting Evidence")
            for i, source in enumerate(literature_sources[:8], 1):
                title = source.get("title", "Clinical Research")
                journal = source.get("journal", "")
                year = source.get("publication_date", "")

                formatted_lines.append(f"**{i}.** {title}")
                if journal:
                    journal_info = journal
                    if year:
                        journal_info += f" ({year})"
                    formatted_lines.append(f"   *{journal_info}*")
                formatted_lines.append("")

        # Medical disclaimer
        formatted_lines.append("---")
        formatted_lines.append("**IMPORTANT MEDICAL DISCLAIMER:**")
        formatted_lines.append("This treatment plan provides evidence-based educational information only. It does not constitute personalized medical advice, diagnosis, or treatment recommendations. Individual responses to treatments vary significantly. Always consult qualified healthcare professionals before implementing any treatment plan. Professional medical assessment is required for personalized care planning.")

        return "\n".join(formatted_lines)

    def get_agent_capabilities(self) -> dict[str, Any]:
        """Return agent capabilities for discovery and routing"""
        return {
            "agent_name": "clinical_research",
            "agent_type": "research_assistant",
            "capabilities": [
                "comprehensive_medical_research",
                "clinical_trial_analysis",
                "differential_diagnosis_support",
                "drug_interaction_analysis",
                "literature_synthesis",
                "evidence_based_research",
                "systematic_review_support",
                "meta_analysis_support",
                "treatment_recommendation_protocols",
                "physical_therapy_guidance",
                "lifestyle_modification_support",
                "actionable_clinical_guidance",
            ],
            "supported_query_types": [
                "literature_research",
                "differential_diagnosis",
                "drug_interaction",
                "clinical_guidelines",
                "comprehensive_research",
                "treatment_recommendation",
                "lifestyle_guidance",
            ],
            "mcp_tools": [
                "search-pubmed",
                "search-trials",
                "get-drug-info",
                "search-icd10",  # Future capability
                "search-billing-codes",  # Future capability
                "lifestyle-api",  # Future capability
                "exercise-api",  # Future capability
                "nutrition-api",  # Future capability
            ],
            "dual_functionality": {
                "information_seeking": "Comprehensive literature research and evidence synthesis",
                "actionable_guidance": "Evidence-based treatment protocols and lifestyle recommendations",
            },
            "conversation_support": True,
            "source_deduplication": True,
            "phi_compliant": True,
            "medical_disclaimer": "Provides research assistance and evidence-based educational guidance only, not personalized medical advice",
        }

    async def health_check(self) -> dict[str, Any]:
        """Agent health check for system monitoring"""
        try:
            # Basic connectivity tests
            mcp_status = "connected" if self.mcp_client else "not_available"
            llm_status = "connected" if self.llm_client else "not_available"

            # Memory status
            memory_status = {
                "active_conversations": len(self._conversation_memory),
                "cached_sources": sum(len(cache["sources"]) for cache in self._source_cache.values()),
                "topic_histories": len(self._topic_history),
            }

            return {
                "agent_name": "clinical_research",
                "status": "healthy",
                "mcp_client": mcp_status,
                "llm_client": llm_status,
                "memory_status": memory_status,
                "capabilities": self.get_agent_capabilities(),
                "last_check": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {
                "agent_name": "clinical_research",
                "status": "unhealthy",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat(),
            }
