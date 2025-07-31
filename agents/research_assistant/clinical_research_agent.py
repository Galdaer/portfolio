"""
Clinical Research Agent with agentic RAG capabilities
Integrates dynamic knowledge retrieval with medical reasoning
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import yaml

from agents import BaseHealthcareAgent
from core.medical.enhanced_query_engine import EnhancedMedicalQueryEngine, QueryType
from core.reasoning.medical_reasoning_enhanced import EnhancedMedicalReasoning


class ClinicalResearchAgent(BaseHealthcareAgent):
    """
    Enhanced Clinical Research Agent with agentic RAG capabilities
    Integrates dynamic knowledge retrieval with medical reasoning
    """

    def __init__(
        self,
        mcp_client,
        llm_client,
        max_steps: Optional[int] = None,
        config_override: Optional[Dict] = None,
    ) -> None:
        super().__init__("clinical_research", "research_assistant")

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

    def _load_agent_config(self, config_override: Optional[Dict] = None) -> Dict[str, Any]:
        """Load agent-specific configuration from file"""
        if config_override:
            return config_override

        try:
            config_path = "config/agent_settings.yml"
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    full_config = yaml.safe_load(f)
                return full_config.get("agent_limits", {}).get("clinical_research", {})
        except Exception:
            pass

        # Return defaults if config fails to load
        return {
            "max_steps": 50,
            "max_iterations": 3,
            "timeout_seconds": 300,
            "llm_settings": {"temperature": 0.3, "max_tokens": 1000},
        }

    async def _process_implementation(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process clinical research request with enhanced agentic RAG
        """
        self.current_step = 0

        try:
            # Reset step counter for new queries
            session_id = request.get("session_id", "default")

            # Initialize result with default response
            result = self._create_error_response("Processing incomplete", session_id)

            # Process with step limiting (like their agent.run() with max_steps)
            while self.current_step < self.max_steps:
                result = await self._process_with_step_limit(request, session_id)

                # Break if we have a complete result
                if result.get("complete", False):
                    break

                self.current_step += 1

            return result

        except Exception as e:
            session_id = request.get("session_id", "default")
            return self._create_error_response(f"Processing error: {str(e)}", session_id)

    async def _process_with_step_limit(
        self, input_data: Dict[str, Any], session_id: str
    ) -> Dict[str, Any]:
        """Process single step with completion checking"""
        # Extract query information
        query = input_data.get("query", "")
        query_type = input_data.get("query_type", "general_inquiry")
        clinical_context = input_data.get("clinical_context", {})

        # Route to appropriate processing method based on query type
        try:
            if query_type == "differential_diagnosis":
                result = await self._process_differential_diagnosis(
                    query, clinical_context, session_id
                )
            elif query_type == "drug_interaction":
                result = await self._process_drug_interaction(query, clinical_context, session_id)
            elif query_type == "literature_research":
                result = await self._process_literature_research(
                    query, clinical_context, session_id
                )
            else:
                # Default general processing
                result = await self._process_general_inquiry(query, clinical_context, session_id)

            # Mark as complete
            result["complete"] = True
            return result

        except Exception as e:
            return self._create_error_response(f"Step processing error: {str(e)}", session_id)

    async def _process_differential_diagnosis(
        self, query: str, clinical_context: Dict[str, Any], session_id: str
    ) -> Dict[str, Any]:
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
        self, query: str, clinical_context: Dict[str, Any], session_id: str
    ) -> Dict[str, Any]:
        """
        Process drug interaction analysis with FDA and literature integration
        """
        # Extract medications from query and context
        medications = clinical_context.get("medications", [])
        if not medications:
            # Try to extract from query using NLP
            entity_result = await self.mcp_client.call_healthcare_tool(
                "extract_medical_entities", {"text": query}
            )
            drug_entities = [
                e.get("text")
                for e in entity_result.get("entities", [])
                if e.get("label") in ["CHEMICAL", "DRUG"]
            ]
            medications.extend(drug_entities)

        if not medications:
            return self._create_error_response(
                "No medications identified for interaction analysis", session_id
            )

        # Enhanced drug interaction reasoning
        clinical_context["medications"] = medications
        reasoning_result = await self.medical_reasoning.reason_with_dynamic_knowledge(
            clinical_scenario=clinical_context, reasoning_type="drug_interaction", max_iterations=2
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
                    }
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
        self, query: str, clinical_context: Dict[str, Any], session_id: str
    ) -> Dict[str, Any]:
        """
        Comprehensive literature research with source prioritization
        """
        # Multi-stage literature search
        research_stages = [
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
                query=stage["query"],
                query_type=stage["query_type"],
                context=clinical_context,
                max_iterations=2,
            )
            for stage in research_stages
        ]

        research_results = await asyncio.gather(*research_tasks, return_exceptions=True)

        # Process and categorize results
        categorized_results: Dict[str, List[Dict[str, Any]]] = {
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
            stage_sources: List[Dict[str, Any]] = []
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
            categorized_results["all_sources"]
        )

        # Generate research summary
        summary = await self._generate_research_summary(
            query, prioritized_sources, clinical_context
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
                categorized_results["all_sources"]
            ),
            "source_links": list(
                set([source.get("url", "") for source in prioritized_sources if source.get("url")])
            ),
            "disclaimers": [
                "This research summary is for informational purposes only.",
                "Always verify information with original sources.",
                "Clinical decisions should be based on professional medical judgment.",
            ],
            "generated_at": datetime.utcnow().isoformat(),
        }

    def _prioritize_sources_by_evidence(
        self, sources: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
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

    def _analyze_evidence_quality(self, sources: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Analyze distribution of evidence quality levels
        """
        quality_counts: Dict[str, int] = {}
        for source in sources:
            evidence_level = source.get("evidence_level", "unknown")
            quality_counts[evidence_level] = quality_counts.get(evidence_level, 0) + 1

        return quality_counts

    async def _generate_research_summary(
        self, query: str, sources: List[Dict[str, Any]], clinical_context: Dict[str, Any]
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
                    f"{source.get('abstract', 'No abstract')[:200]}..."
                )
            elif source.get("source_type") == "fda":
                source_summaries.append(
                    f"- FDA: {source.get('drug_name', 'Unknown drug')} - "
                    f"Indications: {', '.join(source.get('indications', [])[:3])}"
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
            model="llama3.1",
            prompt=summary_prompt,
            options={"temperature": 0.3, "max_tokens": 1000},
        )

        return response.get("response", "Unable to generate research summary.")

    def _create_error_response(self, error_message: str, session_id: str) -> Dict[str, Any]:
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
            prompt=prompt, model="llama3.1", options=llm_settings
        )

        return response.get("response", "")

    def _get_validation_config(self) -> Dict[str, Any]:
        """Get response validation configuration"""
        try:
            config_path = "config/agent_settings.yml"
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    full_config = yaml.safe_load(f)
                return full_config.get("response_validation", {}).get("medical_trust_scoring", {})
        except Exception:
            pass

        return {"llm_settings": {"temperature": 0.1, "max_tokens": 10}}

    async def _process_general_inquiry(
        self, query: str, clinical_context: Dict[str, Any], session_id: str
    ) -> Dict[str, Any]:
        """
        Process general medical inquiry

        MEDICAL DISCLAIMER: This provides educational information only,
        not medical advice, diagnosis, or treatment recommendations.
        """
        try:
            # TODO: Implement general inquiry processing
            # For now, return a basic response structure
            return {
                "success": True,
                "query": query,
                "response": "General inquiry processing not yet implemented",
                "session_id": session_id,
                "clinical_context": clinical_context,
                "agent_name": self.agent_name,
                "disclaimer": "This is educational information only. Consult healthcare professionals for medical advice.",
            }
        except Exception as e:
            return self._create_error_response(f"General inquiry error: {str(e)}", session_id)
