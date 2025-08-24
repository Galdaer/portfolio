"""
Enhanced Query Engine for Medical Literature
Agentic RAG system for medical literature with dynamic knowledge retrieval

MEDICAL DISCLAIMER: This system provides medical research assistance and literature analysis
only. It searches medical databases, clinical trials, and evidence-based resources to support
healthcare decision-making. It does not provide medical diagnosis, treatment recommendations,
or replace clinical judgment. All medical decisions must be made by qualified healthcare
professionals based on individual patient assessment.
"""

import asyncio
import hashlib
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from cachetools import TTLCache

from config.app import config
from core.infrastructure.healthcare_logger import get_healthcare_logger
from core.mcp.universal_parser import (
    parse_clinical_trials_response,
    parse_pubmed_response,
)

from .medical_response_validator import MedicalTrustScore

logger = get_healthcare_logger("core.medical.enhanced_query_engine")


class QueryType(Enum):
    SYMPTOM_ANALYSIS = "symptom_analysis"
    DRUG_INTERACTION = "drug_interaction"
    DIFFERENTIAL_DIAGNOSIS = "differential_diagnosis"
    CLINICAL_GUIDELINES = "clinical_guidelines"
    LITERATURE_RESEARCH = "literature_research"


@dataclass
class MedicalQueryResult:
    query_id: str
    query_type: QueryType
    original_query: str
    refined_queries: list[str]
    sources: list[dict[str, Any]]
    confidence_score: float
    reasoning_chain: list[dict[str, Any]]
    medical_entities: list[dict[str, Any]]
    disclaimers: list[str]
    source_links: list[str]
    generated_at: datetime


class EnhancedMedicalQueryEngine:
    """
    Agentic RAG system for medical literature with dynamic knowledge retrieval
    Implements NVIDIA's agentic RAG concepts for healthcare
    """

    def __init__(self, mcp_client: Any, llm_client: Any) -> None:
        self.mcp_client = mcp_client
        self.llm_client = llm_client

        # Dynamic knowledge cache with TTL
        self.knowledge_cache: TTLCache[str, Any] = TTLCache(maxsize=1000, ttl=1800)  # 30 min cache

        # Session-level cache to prevent duplicate MCP calls within same session
        self.session_cache: TTLCache[str, Any] = TTLCache(
            maxsize=100, ttl=300,
        )  # 5 min session cache

        # Query refinement tracking
        self.query_history: dict[str, Any] = {}

        # Medical disclaimers
        self.disclaimers = {
            "information_only": "This information is for educational purposes only and is not medical advice.",
            "professional_judgment": "Clinical decisions require professional medical judgment.",
            "source_verification": "Please verify information with original sources.",
            "emergency": "For medical emergencies, contact emergency services immediately.",
        }

    async def process_medical_query(
        self,
        query: str,
        query_type: QueryType,
        context: dict[str, Any] | None = None,
        max_iterations: int = 3,
    ) -> MedicalQueryResult:
        """
        Process medical query using agentic RAG with iterative refinement

        RUNTIME PHI PROTECTION: Monitors query content for PHI exposure
        """
        # Runtime PHI monitoring - check query for PHI patterns
        phi_detected = self._monitor_runtime_phi(query, "medical_query_input")
        if phi_detected:
            # Log anonymized version for audit trail
            query_hash = hashlib.sha256(query.encode()).hexdigest()[:8]
            print(f"⚠️  PHI patterns detected in medical query {query_hash} - content sanitized")

            # Sanitize query content for processing (remove potential PHI)
            query = self._sanitize_query_phi(query)

        query_id = self._generate_query_id(query)

        # Initialize query session
        query_session: dict[str, Any] = {
            "query_id": query_id,
            "original_query": query,
            "query_type": query_type,
            "context": context or {},
            "iterations": [],
            "refined_queries": [],
            "sources": [],
            "reasoning_chain": [],
            "start_time": datetime.utcnow(),
        }

        # Extract medical entities first
        medical_entities = await self._extract_medical_entities(query)

        # Initial query processing
        current_query = query

        for iteration in range(max_iterations):
            # Generate refined query based on previous results
            if iteration > 0:
                current_query = await self._refine_query_with_reasoning(
                    original_query=query,
                    previous_results=query_session["sources"],
                    query_type=query_type,
                    context=context,
                )
                query_session["refined_queries"].append(current_query)

            # Perform dynamic knowledge retrieval
            iteration_results = await self._dynamic_knowledge_retrieval(
                query=current_query,
                query_type=query_type,
                medical_entities=medical_entities,
                context=context,
            )

            # Evaluate result quality and relevance
            quality_score = await self._evaluate_result_quality(
                query=query,
                results=iteration_results,
                query_type=query_type,
            )

            # Add reasoning step
            reasoning_step = {
                "iteration": iteration + 1,
                "refined_query": current_query,
                "sources_found": len(iteration_results.get("sources", [])),
                "quality_score": quality_score,
                "reasoning": iteration_results.get("reasoning", ""),
                "timestamp": datetime.utcnow().isoformat(),
            }

            query_session["reasoning_chain"].append(reasoning_step)
            query_session["sources"].extend(iteration_results.get("sources", []))

            # Stop if quality threshold reached OR if we have any sources (prevent infinite retries)
            if quality_score > 0.5 or len(iteration_results.get("sources", [])) > 0:
                break

        # Generate final result
        result = MedicalQueryResult(
            query_id=query_id,
            query_type=query_type,
            original_query=query,
            refined_queries=query_session["refined_queries"],
            sources=query_session["sources"],
            confidence_score=await self._calculate_final_confidence(query_session),
            reasoning_chain=query_session["reasoning_chain"],
            medical_entities=medical_entities,
            disclaimers=self._get_relevant_disclaimers(query_type),
            source_links=self._extract_source_links(query_session["sources"]),
            generated_at=datetime.utcnow(),
        )

        # Runtime PHI monitoring - check result content before returning
        result_content = str(result.sources) + str(result.reasoning_chain)
        phi_in_result = self._monitor_runtime_phi(result_content, "medical_query_result")
        if phi_in_result:
            print(
                f"⚠️  PHI detected in medical query result {query_id} - review output sanitization",
            )

        # Cache result
        self.knowledge_cache[query_id] = result

        return result

    async def _dynamic_knowledge_retrieval(
        self,
        query: str,
        query_type: QueryType,
        medical_entities: list[dict[str, Any]],
        context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """
        Dynamic knowledge retrieval from multiple medical sources
        """
        sources: list[dict[str, Any]] = []
        reasoning = ""

        try:
            # Parallel search across multiple sources - OPTIMIZED to reduce calls
            search_tasks = []

            # PubMed literature search (always - primary source)
            search_tasks.append(self._search_pubmed_with_context(query, medical_entities, context))

            # FDA drug database (ONLY for drug-specific queries, not general symptoms)
            if query_type == QueryType.DRUG_INTERACTION:
                search_tasks.append(self._search_fda_drugs(query, medical_entities))

            # Clinical trials (ONLY for specific clinical research, not basic information)
            if query_type == QueryType.CLINICAL_GUIDELINES:
                search_tasks.append(self._search_clinical_trials(query, medical_entities))

            # Clinical guidelines
            if query_type == QueryType.CLINICAL_GUIDELINES:
                search_tasks.append(self._search_clinical_guidelines(query, medical_entities))

            # Execute searches in parallel
            search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

            # Process and combine results
            for result in search_results:
                if isinstance(result, Exception):
                    continue
                if result and isinstance(result, dict) and "sources" in result:
                    sources.extend(result["sources"])

            # Generate reasoning for source selection
            reasoning = await self._generate_source_reasoning(query, sources, query_type)

        except Exception as e:
            reasoning = f"Error in knowledge retrieval: {str(e)}"

        return {
            "sources": sources,
            "reasoning": reasoning,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def _search_pubmed_with_context(
        self,
        query: str,
        medical_entities: list[dict[str, Any]],
        context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """
        Enhanced PubMed search with medical context
        """
        try:
            # Enhance query with medical entities
            enhanced_query = await self._enhance_query_with_entities(query, medical_entities)

            # Search PubMed via MCP
            pubmed_results = await self.mcp_client.call_tool(
                "search-pubmed",
                {
                    "query": enhanced_query,
                    "max_results": 10,  # Reduced from 20 to prevent rate limiting
                },
            )  # CRITICAL DEBUG: Log the actual MCP result structure
            logger.info(
                f"CRITICAL DEBUG - MCP search-pubmed result keys: {list(pubmed_results.keys()) if isinstance(pubmed_results, dict) else 'NOT_DICT'}",
            )
            logger.info(f"CRITICAL DEBUG - MCP search-pubmed result type: {type(pubmed_results)}")
            if isinstance(pubmed_results, dict):
                for key, value in pubmed_results.items():
                    if isinstance(value, list):
                        logger.info(f"CRITICAL DEBUG - Key '{key}' has {len(value)} items")
                    else:
                        logger.info(f"CRITICAL DEBUG - Key '{key}' = {str(value)[:100]}")

            # Process and rank results
            processed_sources = []

            # Parse the MCP response structure: content[0].text contains JSON string with articles
            articles = parse_pubmed_response(pubmed_results)
            logger.info(
                f"CRITICAL DEBUG - Universal parser extracted {len(articles)} articles from MCP response",
            )

            for i, article in enumerate(articles):
                # CRITICAL DEBUG: Log actual article structure
                logger.info(
                    f"CRITICAL DEBUG - Article {i} keys: {list(article.keys()) if isinstance(article, dict) else 'NOT_DICT'}",
                )
                logger.info(f"CRITICAL DEBUG - Article {i} type: {type(article)}")
                if isinstance(article, dict):
                    logger.info(
                        f"CRITICAL DEBUG - Article {i} title: '{article.get('title', 'NO_TITLE')}'",
                    )
                    logger.info(
                        f"CRITICAL DEBUG - Article {i} pmid: '{article.get('pmid', 'NO_PMID')}'",
                    )

                    processed_sources.append(
                        {
                            "source_type": "pubmed",
                            "title": article.get("title", ""),
                            "authors": article.get("authors", []),
                            "journal": article.get("journal", ""),
                            "publication_date": article.get("date")
                            or article.get("publication_date")
                            or article.get("pubDate", ""),
                            "pmid": article.get("pmid", ""),
                            "doi": article.get("doi", ""),
                            "abstract": article.get("abstract", ""),
                            "relevance_score": article.get("relevance_score", 0.0),
                            "study_type": article.get("study_type")
                            or article.get("publication_type", ""),
                            "evidence_level": self._determine_evidence_level(article),
                        },
                    )

            return {"sources": processed_sources}

        except Exception:
            return {"sources": []}

    async def _search_fda_drugs(
        self,
        query: str,
        medical_entities: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Search FDA drug database for medication information
        """
        try:
            # Extract drug names from entities
            drug_entities = [
                entity
                for entity in medical_entities
                if entity.get("label") in ["CHEMICAL", "DRUG", "MEDICATION"]
            ]

            if not drug_entities:
                return {"sources": []}

            fda_sources = []
            for drug in drug_entities:
                drug_name = drug.get("text", "")

                # Search FDA Orange Book
                fda_result = await self.mcp_client.call_tool(
                    "search_fda_drugs",
                    {
                        "drug_name": drug_name,
                        "include_interactions": True,
                        "include_adverse_events": True,
                    },
                )

                if fda_result.get("found"):
                    fda_sources.append(
                        {
                            "source_type": "fda",
                            "drug_name": drug_name,
                            "ndc_number": fda_result.get("ndc", ""),
                            "approval_date": fda_result.get("approval_date", ""),
                            "manufacturer": fda_result.get("manufacturer", ""),
                            "indications": fda_result.get("indications", []),
                            "contraindications": fda_result.get("contraindications", []),
                            "interactions": fda_result.get("interactions", []),
                            "adverse_events": fda_result.get("adverse_events", []),
                            "url": fda_result.get("fda_url", ""),
                            "evidence_level": "regulatory_approval",
                        },
                    )

            return {"sources": fda_sources}

        except Exception:
            return {"sources": []}

    async def _refine_query_with_reasoning(
        self,
        original_query: str,
        previous_results: list[dict[str, Any]],
        query_type: QueryType,
        context: dict[str, Any] | None,
    ) -> str:
        """
        Use reasoning to refine query based on previous results
        """
        try:
            # Analyze previous results to identify gaps
            result_analysis = await self._analyze_result_gaps(previous_results, query_type)

            # Generate refined query using LLM
            refinement_prompt = f"""
            Original query: {original_query}
            Query type: {query_type.value}

            Previous search found {len(previous_results)} sources.
            Analysis of gaps: {result_analysis}

            Generate a refined search query that addresses these gaps and improves relevance.
            Focus on medical terminology and specific concepts.

            Refined query:"""

            response = await self.llm_client.generate(
                model=config.get_model_for_task("reasoning"),
                prompt=refinement_prompt,
                options={"temperature": 0.3, "max_tokens": 100},
            )

            refined_query = response.get("response", "").strip()
            result: str = refined_query if refined_query else original_query
            return result

        except Exception:
            return original_query

    async def _extract_medical_entities(self, query: str) -> list[dict[str, Any]]:
        """
        Extract medical entities from query using NLP
        """
        try:
            # Use medical NER via MCP tools
            entities_result = await self.mcp_client.call_tool(
                "extract_medical_entities",
                {"text": query},
            )

            entities_data = entities_result.get("entities", [])
            return entities_data if isinstance(entities_data, list) else []

        except Exception:
            return []

    async def _evaluate_result_quality(
        self,
        query: str,
        results: dict[str, Any],
        query_type: QueryType,
    ) -> float:
        """
        Evaluate quality and relevance of search results
        """
        sources = results.get("sources", [])

        if not sources:
            return 0.0

        # Quality factors
        quality_factors = {
            "source_count": min(len(sources) / 10.0, 1.0),  # Up to 10 sources = 1.0
            "evidence_level": self._calculate_evidence_level_score(sources),
            "recency": self._calculate_recency_score(sources),
            "relevance": await self._calculate_relevance_score(query, sources),
        }

        # Weighted average
        weights = {
            "source_count": 0.2,
            "evidence_level": 0.3,
            "recency": 0.2,
            "relevance": 0.3,
        }

        quality_score = sum(quality_factors[factor] * weights[factor] for factor in quality_factors)

        return min(quality_score, 1.0)

    def _generate_query_id(self, query: str) -> str:
        """Generate unique query ID"""
        return hashlib.md5(f"{query}{datetime.utcnow()}".encode()).hexdigest()[:12]

    def _get_relevant_disclaimers(self, query_type: QueryType) -> list[str]:
        """Get relevant disclaimers based on query type"""
        base_disclaimers = [
            self.disclaimers["information_only"],
            self.disclaimers["professional_judgment"],
            self.disclaimers["source_verification"],
        ]

        if query_type in [QueryType.SYMPTOM_ANALYSIS, QueryType.DIFFERENTIAL_DIAGNOSIS]:
            base_disclaimers.append(self.disclaimers["emergency"])

        return base_disclaimers

    def _extract_source_links(self, sources: list[dict[str, Any]]) -> list[str]:
        """Extract all source URLs for easy access"""
        links = []
        for source in sources:
            if "url" in source and source["url"]:
                links.append(source["url"])
        return links

    async def _refine_query_with_trust_feedback(
        self,
        original_query: str,
        previous_response: str,
        trust_score: MedicalTrustScore,
        iteration: int,
    ) -> str:
        """Refine query based on trust score feedback"""

        if trust_score.overall_trust > 0.8:
            return original_query  # Good enough, don't change

        # Identify specific issues
        refinement_needed = []

        if trust_score.accuracy_score < 0.6:
            refinement_needed.append("more specific medical terminology")

        if trust_score.evidence_strength < 0.6:
            refinement_needed.append("request for peer-reviewed sources")

        if trust_score.safety_score < 0.8:
            refinement_needed.append("emphasize information-only nature")

        if not refinement_needed:
            return original_query

        refinement_prompt = f"""
        Original Query: {original_query}
        Previous Response Trust Score: {trust_score.overall_trust:.2f}
        Issues Found: {", ".join(refinement_needed)}

        Refine the query to address these issues while maintaining the original intent.
        Make the query more specific and likely to return high-quality medical information.
        """

        try:
            result = await self.llm_client.generate(
                prompt=refinement_prompt,
                model=config.get_model_for_task("reasoning"),
                options={"temperature": 0.3, "max_tokens": 100},
            )

            refined_query = result.get("response", original_query).strip()
            final_result: str = refined_query if refined_query else original_query
            return final_result

        except Exception:
            return original_query

    async def _calculate_final_confidence(self, query_session: dict[str, Any]) -> float:
        """Calculate final confidence score based on query session results"""
        sources = query_session.get("sources", [])
        reasoning_chain = query_session.get("reasoning_chain", [])

        if not sources:
            return 0.0

        # Factors for confidence calculation
        source_quality = self._calculate_evidence_level_score(sources)
        source_quantity = min(len(sources) / 15.0, 1.0)  # Up to 15 sources = max score
        reasoning_quality = sum(step.get("quality_score", 0.5) for step in reasoning_chain) / max(
            len(reasoning_chain),
            1,
        )

        # Weighted average
        confidence: float = source_quality * 0.4 + source_quantity * 0.3 + reasoning_quality * 0.3
        return min(confidence, 1.0)

    async def _search_clinical_trials(
        self,
        query: str,
        medical_entities: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Search clinical trials database"""
        try:
            # Use ClinicalTrials.gov API via MCP (tool name uses hyphen per MCP schema)
            trials_mcp = await self.mcp_client.call_tool(
                "search-trials",
                {
                    "condition": query,
                    "maxResults": 10,
                },
            )

            # Parse via universal parser to support both array and keyed JSON
            trials_list = parse_clinical_trials_response(trials_mcp)

            processed_trials = []
            for trial in trials_list:
                nct_id = trial.get("nct_id") or trial.get("nctId") or trial.get("nct") or ""
                processed_trials.append(
                    {
                        "source_type": "clinical_trial",
                        "title": trial.get("title", ""),
                        "nct_id": nct_id,
                        "status": trial.get("status", ""),
                        "phase": trial.get("phase", ""),
                        "condition": trial.get("condition", ""),
                        "intervention": trial.get("intervention", ""),
                        "sponsor": trial.get("sponsor", ""),
                        "url": f"https://clinicaltrials.gov/study/{nct_id}" if nct_id else "",
                        "evidence_level": "clinical_trial",
                        "enrollment": trial.get("enrollment", 0),
                    },
                )

            return {"sources": processed_trials}

        except Exception:
            return {"sources": []}

    async def _search_clinical_guidelines(
        self,
        query: str,
        medical_entities: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Search clinical practice guidelines"""
        try:
            # Search medical society guidelines
            guidelines_result = await self.mcp_client.call_tool(
                "search_clinical_guidelines",
                {
                    "query": query,
                    "organizations": ["AMA", "AHA", "ACC", "NIH", "CDC", "WHO"],
                    "max_results": 8,
                },
            )

            processed_guidelines = []
            for guideline in guidelines_result.get("guidelines", []):
                processed_guidelines.append(
                    {
                        "source_type": "clinical_guideline",
                        "title": guideline.get("title", ""),
                        "organization": guideline.get("organization", ""),
                        "publication_date": guideline.get("date", ""),
                        "recommendation_grade": guideline.get("grade", ""),
                        "topic": guideline.get("topic", ""),
                        "url": guideline.get("url", ""),
                        "evidence_level": "clinical_guideline",
                        "summary": guideline.get("summary", ""),
                    },
                )

            return {"sources": processed_guidelines}

        except Exception:
            return {"sources": []}

    async def _generate_source_reasoning(
        self,
        query: str,
        sources: list[dict[str, Any]],
        query_type: QueryType,
    ) -> str:
        """Generate reasoning for source selection and quality"""
        if not sources:
            return "No relevant sources found for the query."

        source_summary: dict[str, Any] = {
            "total": len(sources),
            "by_type": {},
            "high_evidence": 0,
        }

        # Analyze source composition
        for source in sources:
            source_type = source.get("source_type", "unknown")
            if source_type not in source_summary["by_type"]:
                source_summary["by_type"][source_type] = 0
            source_summary["by_type"][source_type] += 1

            evidence_level = source.get("evidence_level", "")
            if evidence_level in [
                "systematic_review",
                "meta_analysis",
                "randomized_controlled_trial",
                "clinical_guideline",
            ]:
                source_summary["high_evidence"] += 1

        reasoning_prompt = f"""
        Query: {query}
        Query Type: {query_type.value}

        Sources Found:
        - Total: {source_summary["total"]}
        - High Evidence Sources: {source_summary["high_evidence"]}
        - By Type: {source_summary["by_type"]}

        Provide a brief reasoning for source selection quality and relevance (2-3 sentences):
        """

        try:
            result = await self.llm_client.generate(
                prompt=reasoning_prompt,
                model=config.get_model_for_task("reasoning"),
                options={"temperature": 0.3, "max_tokens": 150},
            )

            result_text: str = result.get(
                "response",
                "Sources selected based on relevance and evidence quality.",
            )
            return result_text

        except Exception:
            return f"Found {len(sources)} sources including {source_summary['high_evidence']} high-evidence sources."

    async def _enhance_query_with_entities(
        self,
        query: str,
        medical_entities: list[dict[str, Any]],
    ) -> str:
        """Transform conversational query into optimized search terms using LLM"""

        # First, use LLM to convert question to search terms
        search_query = await self._convert_question_to_search(query)

        # Then enhance with extracted entities if available
        if not medical_entities:
            return search_query

        # Extract relevant entity terms
        entity_terms = []
        for entity in medical_entities:
            entity_type = entity.get("label", "")
            entity_text = entity.get("text", "")

            # Add medical terminology
            if entity_type in ["DISEASE", "CONDITION", "SYMPTOM"]:
                entity_terms.append(f"({entity_text} OR {entity_text.lower()})")
            elif entity_type in ["DRUG", "MEDICATION", "CHEMICAL"]:
                entity_terms.append(f"({entity_text} AND (drug OR medication))")

        if entity_terms:
            return f"{search_query} AND ({' OR '.join(entity_terms[:3])})"  # Limit to top 3

        return search_query

    async def _convert_question_to_search(self, question: str) -> str:
        """Convert conversational question to optimized search terms using LLM"""

        # Create prompt for LLM to extract search terms
        prompt = f"""Convert this medical question into concise search terms suitable for a medical literature database.

Question: "{question}"

Extract the key medical concepts and convert to effective search terms. Return only the search terms, no explanation.

Examples:
"What are the symptoms of diabetes?" → "diabetes symptoms"
"How is hypertension treated?" → "hypertension treatment"
"What causes heart disease?" → "heart disease etiology causes"
"Side effects of metformin" → "metformin adverse effects side effects"

Search terms for the question above:"""

        try:
            # Use LLM to convert question to search terms
            response = await self.llm_client.chat(
                model="llama3.1:8b",  # Use the healthcare model
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.1, "max_tokens": 50},
            )

            search_terms = response["message"]["content"].strip()

            # Clean up the response - remove quotes, extra whitespace
            search_terms = search_terms.strip("\"'").strip()

            # Fallback to simple extraction if LLM fails
            if not search_terms or len(search_terms) < 3:
                return self._fallback_search_extraction(question)

            return search_terms

        except Exception as e:
            print(f"LLM query conversion failed: {e}")
            # Fallback to simple extraction
            return self._fallback_search_extraction(question)

    def _fallback_search_extraction(self, question: str) -> str:
        """Simple fallback for extracting search terms when LLM fails"""
        import re

        # Remove question words
        question_words = ["what", "how", "why", "when", "where", "is", "are", "can", "does", "do"]
        words = question.lower().split()
        words = [w for w in words if w not in question_words and len(w) > 2]

        # Remove common words
        stop_words = ["the", "and", "or", "but", "for", "with", "this", "that", "these", "those"]
        words = [w for w in words if w not in stop_words]

        # Clean punctuation
        words = [re.sub(r"[^\w\s]", "", w) for w in words]
        words = [w for w in words if w]  # Remove empty strings

        return " ".join(words[:4])  # Limit to 4 key terms

    def _determine_evidence_level(self, article: dict[str, Any]) -> str:
        """Determine evidence level from article metadata"""
        pub_type = article.get("publication_type", "").lower()
        title = article.get("title", "").lower()

        if any(term in pub_type for term in ["systematic review", "meta-analysis"]):
            return "systematic_review"
        if any(term in pub_type for term in ["randomized controlled trial", "rct"]):
            return "randomized_controlled_trial"
        if any(term in title for term in ["systematic review", "meta-analysis"]):
            return "systematic_review"
        if any(term in title for term in ["randomized", "controlled trial"]):
            return "randomized_controlled_trial"
        if "cohort" in pub_type or "cohort" in title:
            return "cohort_study"
        if "case control" in pub_type or "case-control" in title:
            return "case_control_study"
        if "case series" in pub_type or "case series" in title:
            return "case_series"
        return "unknown"

    async def _analyze_result_gaps(
        self,
        previous_results: list[dict[str, Any]],
        query_type: QueryType,
    ) -> str:
        """Analyze gaps in previous search results"""
        if not previous_results:
            return "No previous results to analyze"

        analysis: dict[str, Any] = {
            "total_sources": len(previous_results),
            "source_types": {},
            "evidence_levels": {},
            "recency": {"recent": 0, "older": 0},
        }

        current_year = datetime.now().year

        for source in previous_results:
            # Count by source type
            source_type = source.get("source_type", "unknown")
            if source_type not in analysis["source_types"]:
                analysis["source_types"][source_type] = 0
            analysis["source_types"][source_type] += 1

            # Count by evidence level
            evidence_level = source.get("evidence_level", "unknown")
            if evidence_level not in analysis["evidence_levels"]:
                analysis["evidence_levels"][evidence_level] = 0
            analysis["evidence_levels"][evidence_level] += 1

            # Check recency
            pub_date = source.get("publication_date", "")
            if pub_date and str(current_year - 3) <= pub_date:  # Last 3 years
                analysis["recency"]["recent"] += 1
            else:
                analysis["recency"]["older"] += 1

        # Identify gaps
        gaps = []
        if analysis["evidence_levels"].get("systematic_review", 0) == 0:
            gaps.append("systematic reviews")
        if (
            analysis["source_types"].get("clinical_guideline", 0) == 0
            and query_type == QueryType.CLINICAL_GUIDELINES
        ):
            gaps.append("clinical guidelines")
        if analysis["recency"]["recent"] < analysis["total_sources"] * 0.5:
            gaps.append("recent publications")

        if gaps:
            return f"Missing: {', '.join(gaps)}. Need more specific search terms."
        return "Good coverage of source types and evidence levels."

    def _calculate_evidence_level_score(self, sources: list[dict[str, Any]]) -> float:
        """Calculate score based on evidence level quality"""
        if not sources:
            return 0.0

        evidence_weights = {
            "systematic_review": 1.0,
            "meta_analysis": 1.0,
            "randomized_controlled_trial": 0.9,
            "clinical_guideline": 0.8,
            "cohort_study": 0.7,
            "case_control_study": 0.6,
            "case_series": 0.4,
            "regulatory_approval": 0.8,
            "clinical_trial": 0.7,
            "unknown": 0.3,
        }

        total_weight = 0.0
        for source in sources:
            evidence_level = source.get("evidence_level", "unknown")
            total_weight += evidence_weights.get(evidence_level, 0.3)

        return min(total_weight / len(sources), 1.0)

    def _calculate_recency_score(self, sources: list[dict[str, Any]]) -> float:
        """Calculate score based on publication recency"""
        if not sources:
            return 0.0

        current_year = datetime.now().year
        recency_scores = []

        for source in sources:
            pub_date = source.get("publication_date", "")

            if not pub_date:
                recency_scores.append(0.3)  # Default for unknown date
                continue

            try:
                # Extract year from various date formats
                if len(pub_date) >= 4 and pub_date[:4].isdigit():
                    pub_year = int(pub_date[:4])
                    years_old = current_year - pub_year

                    if years_old <= 1:
                        recency_scores.append(1.0)
                    elif years_old <= 3:
                        recency_scores.append(0.8)
                    elif years_old <= 5:
                        recency_scores.append(0.6)
                    elif years_old <= 10:
                        recency_scores.append(0.4)
                    else:
                        recency_scores.append(0.2)
                else:
                    recency_scores.append(0.3)

            except (ValueError, TypeError):
                recency_scores.append(0.3)

        return sum(recency_scores) / len(recency_scores) if recency_scores else 0.0

    async def _calculate_relevance_score(self, query: str, sources: list[dict[str, Any]]) -> float:
        """Calculate relevance score of sources to query"""
        if not sources:
            return 0.0

        # For now, use a simplified relevance calculation
        # In a full implementation, this could use semantic similarity
        relevance_scores = []

        query_words = set(query.lower().split())

        for source in sources:
            title = source.get("title", "").lower()
            abstract = source.get("abstract", "").lower()

            # Count word overlaps
            title_words = set(title.split())
            abstract_words = set(abstract.split())

            title_overlap = len(query_words.intersection(title_words)) / max(len(query_words), 1)
            abstract_overlap = len(query_words.intersection(abstract_words)) / max(
                len(query_words),
                1,
            )

            # Weight title more heavily than abstract
            source_relevance = (title_overlap * 0.7) + (abstract_overlap * 0.3)
            relevance_scores.append(min(source_relevance, 1.0))

        return sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0

    def _monitor_runtime_phi(self, content: str, context_type: str) -> bool:
        """
        Runtime PHI monitoring for medical query processing.

        This monitors actual runtime content for PHI patterns, not static code.
        Returns True if potential PHI is detected.
        """
        import re

        # Critical PHI patterns that should never appear in medical queries
        phi_patterns = [
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN patterns
            r"\b\d{9}\b.*SSN",  # Raw SSN numbers
            r"\(\d{3}\)\s*\d{3}-\d{4}",  # Phone patterns (excluding 555)
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email patterns
            r"MRN.*\d{6,}",  # Medical record numbers
        ]

        # Safe synthetic patterns (don't flag these)
        safe_patterns = [
            r"PAT\d{3}",  # PAT001 patient IDs
            r"555-\d{3}-\d{4}",  # 555 test phone numbers
            r"XXX-XX-XXXX",  # Masked SSN patterns
            r".*@example\.(com|test)",  # Test domain emails
            r"01/01/1990",  # Standard test DOB
        ]

        # Check if content contains safe synthetic patterns first
        for safe_pattern in safe_patterns:
            if re.search(safe_pattern, content, re.IGNORECASE):
                return False  # It's safe synthetic data

        # Check for PHI patterns
        for phi_pattern in phi_patterns:
            if re.search(phi_pattern, content, re.IGNORECASE):
                # Log the detection (without exposing actual content)
                content_hash = hashlib.sha256(content.encode()).hexdigest()[:8]
                print(
                    f"🚨 Runtime PHI detection: {context_type} contains potential PHI (hash: {content_hash})",
                )
                return True

        return False

    def _sanitize_query_phi(self, query: str) -> str:
        """
        Sanitize query content by removing potential PHI patterns.

        This replaces potential PHI with generic placeholders for safe processing.
        """
        import re

        # Replace potential PHI patterns with safe placeholders
        sanitized = query

        # Replace SSN patterns
        sanitized = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[PATIENT_ID]", sanitized)

        # Replace phone patterns (but preserve 555 test numbers)
        sanitized = re.sub(r"(?!555)\(\d{3}\)\s*\d{3}-\d{4}", "[PHONE]", sanitized)

        # Replace email patterns (but preserve test domains)
        sanitized = re.sub(
            r"\b[A-Za-z0-9._%+-]+@(?!example\.)[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "[EMAIL]",
            sanitized,
        )

        # Replace MRN patterns
        sanitized = re.sub(r"MRN.*\d{6,}", "[MEDICAL_RECORD]", sanitized)

        if sanitized != query:
            print("✅ Query sanitized for PHI protection - processing with placeholders")

        return sanitized
