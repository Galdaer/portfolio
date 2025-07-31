"""
Enhanced Query Engine for Medical Literature
Agentic RAG system for medical literature with dynamic knowledge retrieval
"""

import asyncio
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from cachetools import TTLCache

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
refined_queries: List[str]
sources: List[Dict[str, Any]]
confidence_score: float
reasoning_chain: List[Dict[str, Any]]
medical_entities: List[Dict[str, Any]]
disclaimers: List[str]
source_links: List[str]
generated_at: datetime

class EnhancedMedicalQueryEngine:
"""
Agentic RAG system for medical literature with dynamic knowledge retrieval
Implements NVIDIA's agentic RAG concepts for healthcare
"""

    def __init__(self, mcp_client, llm_client):
        self.mcp_client = mcp_client
        self.llm_client = llm_client

        # Dynamic knowledge cache with TTL
        self.knowledge_cache = TTLCache(maxsize=1000, ttl=1800)  # 30 min cache

        # Query refinement tracking
        self.query_history = {}

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
        context: Optional[Dict[str, Any]] = None,
        max_iterations: int = 3,
    ) -> MedicalQueryResult:
        """
        Process medical query using agentic RAG with iterative refinement
        """
        query_id = self._generate_query_id(query)

        # Initialize query session
        query_session: Dict[str, Any] = {
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
                query=query, results=iteration_results, query_type=query_type
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

            # Stop if quality threshold reached
            if quality_score > 0.8:
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

        # Cache result
        self.knowledge_cache[query_id] = result

        return result

    async def _dynamic_knowledge_retrieval(
        self,
        query: str,
        query_type: QueryType,
        medical_entities: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Dynamic knowledge retrieval from multiple medical sources
        """
        sources = []
        reasoning = ""

        try:
            # Parallel search across multiple sources
            search_tasks = []

            # PubMed literature search
            search_tasks.append(self._search_pubmed_with_context(query, medical_entities, context))

            # FDA drug database (if drug-related)
            if query_type in [QueryType.DRUG_INTERACTION, QueryType.SYMPTOM_ANALYSIS]:
                search_tasks.append(self._search_fda_drugs(query, medical_entities))

            # Clinical trials (if relevant)
            if query_type in [QueryType.CLINICAL_GUIDELINES, QueryType.LITERATURE_RESEARCH]:
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
        self, query: str, medical_entities: List[Dict[str, Any]], context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Enhanced PubMed search with medical context
        """
        try:
            # Enhance query with medical entities
            enhanced_query = await self._enhance_query_with_entities(query, medical_entities)

            # Search PubMed via MCP
            pubmed_results = await self.mcp_client.call_healthcare_tool(
                "search_pubmed",
                {
                    "query": enhanced_query,
                    "max_results": 20,
                    "sort": "relevance",
                    "publication_types": ["clinical_trial", "systematic_review", "meta_analysis"],
                },
            )

            # Process and rank results
            processed_sources = []
            for article in pubmed_results.get("articles", []):
                processed_sources.append(
                    {
                        "source_type": "pubmed",
                        "title": article.get("title", ""),
                        "authors": article.get("authors", []),
                        "journal": article.get("journal", ""),
                        "publication_date": article.get("date", ""),
                        "pmid": article.get("pmid", ""),
                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{article.get('pmid', '')}/",
                        "abstract": article.get("abstract", ""),
                        "relevance_score": article.get("relevance_score", 0.0),
                        "study_type": article.get("publication_type", ""),
                        "evidence_level": self._determine_evidence_level(article),
                    }
                )

            return {"sources": processed_sources}

        except Exception:
            return {"sources": []}

    async def _search_fda_drugs(
        self, query: str, medical_entities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
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
                fda_result = await self.mcp_client.call_healthcare_tool(
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
                        }
                    )

            return {"sources": fda_sources}

        except Exception:
            return {"sources": []}

    async def _refine_query_with_reasoning(
        self,
        original_query: str,
        previous_results: List[Dict[str, Any]],
        query_type: QueryType,
        context: Optional[Dict[str, Any]],
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
                model="llama3.1",
                prompt=refinement_prompt,
                options={"temperature": 0.3, "max_tokens": 100},
            )

            refined_query = response.get("response", "").strip()
            return refined_query if refined_query else original_query

        except Exception:
            return original_query

    async def _extract_medical_entities(self, query: str) -> List[Dict[str, Any]]:
        """
        Extract medical entities from query using NLP
        """
        try:
            # Use medical NER via MCP tools
            entities_result = await self.mcp_client.call_healthcare_tool(
                "extract_medical_entities", {"text": query}
            )

            return entities_result.get("entities", [])

        except Exception:
            return []

    async def _evaluate_result_quality(
        self, query: str, results: Dict[str, Any], query_type: QueryType
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
        weights = {"source_count": 0.2, "evidence_level": 0.3, "recency": 0.2, "relevance": 0.3}

        quality_score = sum(quality_factors[factor] * weights[factor] for factor in quality_factors)

        return min(quality_score, 1.0)

    def _generate_query_id(self, query: str) -> str:
        """Generate unique query ID"""
        return hashlib.md5(f"{query}{datetime.utcnow()}".encode()).hexdigest()[:12]

    def _get_relevant_disclaimers(self, query_type: QueryType) -> List[str]:
        """Get relevant disclaimers based on query type"""
        base_disclaimers = [
            self.disclaimers["information_only"],
            self.disclaimers["professional_judgment"],
            self.disclaimers["source_verification"],
        ]

        if query_type in [QueryType.SYMPTOM_ANALYSIS, QueryType.DIFFERENTIAL_DIAGNOSIS]:
            base_disclaimers.append(self.disclaimers["emergency"])

        return base_disclaimers

    def _extract_source_links(self, sources: List[Dict[str, Any]]) -> List[str]:
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
        iteration: int
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
        Issues Found: {', '.join(refinement_needed)}

        Refine the query to address these issues while maintaining the original intent.
        Make the query more specific and likely to return high-quality medical information.
        """

        try:
            result = await self.llm_client.generate(
                prompt=refinement_prompt,
                model="llama3.1",
                options={"temperature": 0.3, "max_tokens": 100}
            )

            refined_query = result.get("response", original_query).strip()
            return refined_query if refined_query else original_query

        except Exception:
            return original_query
