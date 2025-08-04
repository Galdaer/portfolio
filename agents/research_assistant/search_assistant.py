"""
Medical Literature Search Assistant
Provides information about medical concepts, not diagnoses
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class MedicalSearchResult:
    """Search result that provides information, not diagnosis"""

    search_id: str
    search_query: str
    information_sources: list[dict[str, Any]]
    related_conditions: list[dict[str, Any]]  # From literature, not diagnosed
    drug_information: list[dict[str, Any]]
    clinical_references: list[dict[str, Any]]
    search_confidence: float
    disclaimers: list[str]
    source_links: list[str]
    generated_at: datetime


class MedicalLiteratureSearchAssistant:
    """
    Medical literature search assistant - provides information, not diagnoses
    Acts like a sophisticated medical Google, not a diagnostic tool
    """

    def __init__(self, mcp_client: Any, llm_client: Any) -> None:
        self.mcp_client = mcp_client
        self.llm_client = llm_client

        # Standard medical disclaimers
        self.disclaimers = [
            "This information is for educational purposes only and is not medical advice.",
            "Only a qualified healthcare professional can provide medical diagnosis.",
            "Always consult with a healthcare provider for medical concerns.",
            "In case of emergency, contact emergency services immediately.",
            "This search provides literature information, not clinical recommendations.",
        ]

    async def search_medical_literature(
        self, search_query: str, search_context: dict[str, Any] | None = None
    ) -> MedicalSearchResult:
        """
        Search medical literature like a medical librarian would
        Returns information about conditions, not diagnoses
        """
        search_id = self._generate_search_id(search_query)

        # Parse search query for medical concepts
        medical_concepts = await self._extract_medical_concepts(search_query)

        # Parallel search across medical databases
        search_tasks = [
            self._search_condition_information(medical_concepts),
            self._search_symptom_literature(medical_concepts),
            self._search_drug_information(medical_concepts),
            self._search_clinical_references(medical_concepts),
        ]

        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

        # Process results - ensure we only get lists, not exceptions
        condition_info = search_results[0] if not isinstance(search_results[0], Exception) else []
        symptom_literature = (
            search_results[1] if not isinstance(search_results[1], Exception) else []
        )
        drug_info = search_results[2] if not isinstance(search_results[2], Exception) else []
        clinical_refs = search_results[3] if not isinstance(search_results[3], Exception) else []

        # Type assertion to help mypy understand these are definitely lists
        condition_info = condition_info if isinstance(condition_info, list) else []
        symptom_literature = symptom_literature if isinstance(symptom_literature, list) else []
        drug_info = drug_info if isinstance(drug_info, list) else []
        clinical_refs = clinical_refs if isinstance(clinical_refs, list) else []

        # Combine all information sources
        all_sources: list[dict[str, Any]] = []
        all_sources.extend(condition_info)
        all_sources.extend(symptom_literature)
        all_sources.extend(drug_info)
        all_sources.extend(clinical_refs)

        # Rank by medical evidence quality and relevance
        ranked_sources = self._rank_sources_by_evidence(all_sources, search_query)

        # Extract related conditions from literature (not diagnose them)
        related_conditions = self._extract_literature_conditions(ranked_sources)

        # Calculate search confidence (how well we found relevant info)
        search_confidence = self._calculate_search_confidence(ranked_sources, search_query)

        return MedicalSearchResult(
            search_id=search_id,
            search_query=search_query,
            information_sources=ranked_sources[:20],  # Top 20 sources
            related_conditions=related_conditions,
            drug_information=[s for s in ranked_sources if s.get("source_type") == "drug_info"],
            clinical_references=[
                s
                for s in ranked_sources
                if s.get("source_type") in ["clinical_guideline", "medical_reference"]
            ],
            search_confidence=search_confidence,
            disclaimers=self.disclaimers,
            source_links=self._extract_source_links(ranked_sources),
            generated_at=datetime.utcnow(),
        )

    async def _search_condition_information(
        self, medical_concepts: list[str]
    ) -> list[dict[str, Any]]:
        """
        Search for condition information in medical literature
        Returns: Information about conditions, not diagnostic recommendations
        """
        sources = []

        for concept in medical_concepts:
            try:
                # Search PubMed for condition information
                pubmed_results = await self.mcp_client.call_healthcare_tool(
                    "search_pubmed",
                    {
                        "query": f"{concept} overview pathophysiology symptoms",
                        "max_results": 10,
                        "publication_types": [
                            "review",
                            "meta_analysis",
                            "systematic_review",
                        ],
                    },
                )

                for article in pubmed_results.get("articles", []):
                    sources.append(
                        {
                            "source_type": "condition_information",
                            "concept": concept,
                            "title": article.get("title", ""),
                            "authors": article.get("authors", []),
                            "journal": article.get("journal", ""),
                            "publication_date": article.get("date", ""),
                            "pmid": article.get("pmid", ""),
                            "url": f"https://pubmed.ncbi.nlm.nih.gov/{article.get('pmid', '')}/",
                            "abstract": article.get("abstract", ""),
                            "evidence_level": self._determine_evidence_level(article),
                            "relevance_score": self._calculate_concept_relevance(concept, article),
                            "information_type": "medical_literature",
                        }
                    )

            except Exception:
                continue

        return sources

    async def _search_symptom_literature(self, medical_concepts: list[str]) -> list[dict[str, Any]]:
        """
        Search literature about symptoms and their associations
        Returns: Literature about what symptoms are associated with, not diagnoses
        """
        sources = []

        # Look for symptom-related concepts
        symptom_concepts = [
            c
            for c in medical_concepts
            if any(
                symptom_word in c.lower()
                for symptom_word in [
                    "pain",
                    "fever",
                    "cough",
                    "headache",
                    "nausea",
                    "fatigue",
                ]
            )
        ]

        for symptom in symptom_concepts:
            try:
                # Search for literature about symptom presentations
                literature_results = await self.mcp_client.call_healthcare_tool(
                    "search_pubmed",
                    {
                        "query": f"{symptom} presentation differential clinical features",
                        "max_results": 15,
                        "publication_types": ["clinical_study", "review"],
                    },
                )

                for article in literature_results.get("articles", []):
                    sources.append(
                        {
                            "source_type": "symptom_literature",
                            "symptom": symptom,
                            "title": article.get("title", ""),
                            "journal": article.get("journal", ""),
                            "publication_date": article.get("date", ""),
                            "pmid": article.get("pmid", ""),
                            "url": f"https://pubmed.ncbi.nlm.nih.gov/{article.get('pmid', '')}/",
                            "abstract": article.get("abstract", ""),
                            "evidence_level": self._determine_evidence_level(article),
                            "information_type": "symptom_research",
                        }
                    )

            except Exception:
                continue

        return sources

    async def _search_drug_information(self, medical_concepts: list[str]) -> list[dict[str, Any]]:
        """
        Search for drug information and interactions
        Returns: Official drug information, not prescribing advice
        """
        sources = []

        # Look for drug-related concepts
        drug_concepts = [
            c
            for c in medical_concepts
            if any(
                drug_indicator in c.lower()
                for drug_indicator in [
                    "mg",
                    "tablet",
                    "capsule",
                    "injection",
                    "medication",
                ]
            )
        ]

        for drug_concept in drug_concepts:
            try:
                # Search FDA drug database
                fda_results = await self.mcp_client.call_healthcare_tool(
                    "search_fda_drugs",
                    {
                        "drug_name": drug_concept,
                        "include_interactions": True,
                        "include_prescribing_info": True,
                    },
                )

                if fda_results.get("found"):
                    sources.append(
                        {
                            "source_type": "drug_info",
                            "drug_name": drug_concept,
                            "fda_approval": fda_results.get("approval_date", ""),
                            "manufacturer": fda_results.get("manufacturer", ""),
                            "indications": fda_results.get("indications", []),
                            "contraindications": fda_results.get("contraindications", []),
                            "interactions": fda_results.get("interactions", []),
                            "url": fda_results.get("fda_url", ""),
                            "information_type": "regulatory_information",
                            "evidence_level": "regulatory_approval",
                        }
                    )

            except Exception:
                continue

        return sources

    async def _search_clinical_references(
        self, medical_concepts: list[str]
    ) -> list[dict[str, Any]]:
        """
        Search clinical practice guidelines and reference materials
        Returns: Reference information for clinical context
        """
        sources = []

        for concept in medical_concepts:
            try:
                # Search for clinical guidelines
                guideline_results = await self.mcp_client.call_healthcare_tool(
                    "search_clinical_guidelines",
                    {
                        "condition": concept,
                        "organizations": ["AHA", "ACC", "ACP", "USPSTF"],
                        "max_results": 5,
                    },
                )

                for guideline in guideline_results.get("guidelines", []):
                    sources.append(
                        {
                            "source_type": "clinical_guideline",
                            "concept": concept,
                            "title": guideline.get("title", ""),
                            "organization": guideline.get("organization", ""),
                            "publication_year": guideline.get("year", ""),
                            "url": guideline.get("url", ""),
                            "summary": guideline.get("summary", ""),
                            "evidence_grade": guideline.get("evidence_grade", ""),
                            "information_type": "clinical_reference",
                            "evidence_level": "clinical_guideline",
                        }
                    )

            except Exception:
                continue

        return sources

    def _extract_literature_conditions(self, sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Extract conditions mentioned in literature (not diagnose them)
        Returns: List of conditions found in literature with context
        """
        conditions: list[dict[str, Any]] = []

        for source in sources:
            # Extract conditions mentioned in abstracts/summaries
            text_content = " ".join(
                [
                    source.get("title", ""),
                    source.get("abstract", ""),
                    source.get("summary", ""),
                ]
            ).lower()

            # Common medical conditions to look for in literature
            condition_terms = [
                "hypertension",
                "diabetes",
                "pneumonia",
                "bronchitis",
                "migraine",
                "gastritis",
                "arthritis",
                "depression",
                "anxiety",
                "asthma",
            ]

            for condition in condition_terms:
                if condition in text_content:
                    conditions.append(
                        {
                            "condition_name": condition.title(),
                            "mentioned_in_source": source.get("title", "Unknown source"),
                            "source_type": source.get("source_type", ""),
                            "evidence_level": source.get("evidence_level", ""),
                            "source_url": source.get("url", ""),
                            "context": "mentioned_in_literature",
                            "note": "Condition mentioned in medical literature, not a diagnosis",
                        }
                    )

        # Remove duplicates and limit results
        unique_conditions: dict[str, dict[str, Any]] = {}
        for condition_dict in conditions:
            key = condition_dict["condition_name"]
            if key not in unique_conditions:
                unique_conditions[key] = condition_dict

        return list(unique_conditions.values())[:10]  # Top 10 mentioned conditions

    def _rank_sources_by_evidence(
        self, sources: list[dict[str, Any]], query: str
    ) -> list[dict[str, Any]]:
        """
        Rank sources by evidence quality and relevance, like a medical librarian would
        """
        evidence_weights = {
            "systematic_review": 10,
            "meta_analysis": 9,
            "randomized_controlled_trial": 8,
            "clinical_guideline": 8,
            "regulatory_approval": 7,
            "cohort_study": 6,
            "case_control_study": 5,
            "clinical_study": 4,
            "review": 3,
            "case_report": 2,
            "unknown": 1,
        }

        scored_sources = []
        query_terms = set(query.lower().split())

        for source in sources:
            # Base evidence score
            evidence_level = source.get("evidence_level", "unknown")
            base_score = evidence_weights.get(evidence_level, 1)

            # Relevance score
            source_text = " ".join(
                [
                    source.get("title", ""),
                    source.get("abstract", ""),
                    source.get("summary", ""),
                ]
            ).lower()

            relevance_count = sum(1 for term in query_terms if term in source_text)
            relevance_score = float(relevance_count) / len(query_terms) if query_terms else 0.0

            # Recency bonus (recent = more relevant)
            recency_score = self._calculate_recency_score(source.get("publication_date", ""))

            # Final score
            final_score = base_score + (relevance_score * 3) + recency_score

            scored_sources.append(
                {
                    **source,
                    "search_score": final_score,
                    "relevance_score": relevance_score,
                    "evidence_weight": base_score,
                }
            )

        return sorted(scored_sources, key=lambda x: x.get("search_score", 0), reverse=True)

    def _calculate_search_confidence(self, sources: list[dict[str, Any]], query: str) -> float:
        """
        Calculate how confident we are that we found good information (not diagnostic confidence)
        """
        if not sources:
            return 0.0

        # Factors for search quality
        source_count_factor = min(len(sources) / 15.0, 1.0)  # Up to 15 sources = full score

        # Evidence quality factor
        high_quality_sources = sum(
            1
            for s in sources
            if s.get("evidence_level")
            in [
                "systematic_review",
                "meta_analysis",
                "clinical_guideline",
                "regulatory_approval",
            ]
        )
        quality_factor = min(high_quality_sources / 5.0, 1.0)  # Up to 5 high-quality = full score

        # Relevance factor
        relevance_scores = [float(s.get("relevance_score", 0)) for s in sources]
        avg_relevance = sum(relevance_scores) / len(sources) if sources else 0.0

        # Search confidence (not diagnostic confidence)
        search_confidence = (
            (source_count_factor * 0.3) + (quality_factor * 0.4) + (avg_relevance * 0.3)
        )

        return min(search_confidence, 1.0)

    async def _extract_medical_concepts(self, search_query: str) -> list[str]:
        """Extract medical concepts from search query using NLP"""
        try:
            entities_result = await self.mcp_client.call_healthcare_tool(
                "extract_medical_entities", {"text": search_query}
            )

            concepts = []
            for entity in entities_result.get("entities", []):
                if entity.get("label") in ["DISEASE", "CHEMICAL", "SYMPTOM", "ANATOMY"]:
                    concepts.append(entity.get("text", ""))

            # Also include the original query terms
            concepts.extend(search_query.split())

            return list(set(concepts))  # Remove duplicates

        except Exception:
            # Fallback to simple word extraction
            return search_query.split()

    def _calculate_concept_relevance(self, concept: str, article: dict[str, Any]) -> float:
        """Calculate how relevant an article is to a medical concept"""
        article_text = " ".join([article.get("title", ""), article.get("abstract", "")]).lower()

        concept_lower = concept.lower()

        # Direct mention
        if concept_lower in article_text:
            return 1.0

        # Partial matches
        concept_words = concept_lower.split()
        matches = sum(1 for word in concept_words if word in article_text)

        return matches / len(concept_words) if concept_words else 0.0

    def _determine_evidence_level(self, article: dict[str, Any]) -> str:
        """Determine evidence level from article metadata"""
        pub_type = article.get("publication_type", "").lower()
        title = article.get("title", "").lower()

        if "systematic review" in pub_type or "systematic review" in title:
            return "systematic_review"
        elif "meta-analysis" in pub_type or "meta-analysis" in title:
            return "meta_analysis"
        elif "randomized controlled trial" in pub_type:
            return "randomized_controlled_trial"
        elif "clinical trial" in pub_type:
            return "clinical_study"
        elif "review" in pub_type:
            return "review"
        else:
            return "unknown"

    def _calculate_recency_score(self, publication_date: str) -> float:
        """Calculate recency bonus for more recent publications"""
        if not publication_date:
            return 0.0

        try:
            # Extract year
            year = int(publication_date[:4])
            current_year = datetime.utcnow().year
            years_old = current_year - year

            # Recent publications get higher scores
            if years_old <= 2:
                return 1.0
            elif years_old <= 5:
                return 0.5
            elif years_old <= 10:
                return 0.2
            else:
                return 0.0

        except (ValueError, TypeError):
            return 0.0

    def _extract_source_links(self, sources: list[dict[str, Any]]) -> list[str]:
        """Extract all source URLs for easy verification"""
        links = []
        for source in sources:
            if "url" in source and source["url"]:
                links.append(source["url"])
        return list(set(links))  # Remove duplicates

    def _generate_search_id(self, query: str) -> str:
        """Generate unique search ID"""
        import hashlib

        return hashlib.md5(f"{query}{datetime.utcnow()}".encode()).hexdigest()[:12]
