"""
Medical Literature Search Assistant
Provides information about medical concepts, not diagnoses
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from agents import BaseHealthcareAgent
from core.infrastructure.healthcare_logger import get_healthcare_logger, log_healthcare_event
from config.medical_search_config_loader import MedicalSearchConfigLoader

logger = get_healthcare_logger("agent.medical_search")

# Load medical search configuration
config_loader = MedicalSearchConfigLoader()
search_config = config_loader.load_config()


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


class MedicalLiteratureSearchAssistant(BaseHealthcareAgent):
    """
    Medical literature search assistant - provides information, not diagnoses
    Acts like a sophisticated medical Google, not a diagnostic tool
    """

    def __init__(self, mcp_client: Any, llm_client: Any) -> None:
        super().__init__(mcp_client, llm_client, agent_name="medical_search", agent_type="literature_search")
        self.mcp_client = mcp_client
        self.llm_client = llm_client

        # Debug logging for initialization
        logger.info("MedicalLiteratureSearchAssistant initialized")
        logger.info(f"MCP client: {type(mcp_client)} - {mcp_client}")
        logger.info(f"LLM client: {type(llm_client)} - {llm_client}")

        # Discover available MCP search sources dynamically
        self._available_search_sources = None

        # Standard medical disclaimers
        self.disclaimers = [
            "This information is for educational purposes only and is not medical advice.",
            "Only a qualified healthcare professional can provide medical diagnosis.",
            "Always consult with a healthcare provider for medical concerns.",
            "In case of emergency, contact emergency services immediately.",
            "This search provides literature information, not clinical recommendations.",
        ]

    async def _process_implementation(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Required implementation for BaseHealthcareAgent
        Processes search requests through the standard agent interface
        """
        logger.info(f"Medical search agent processing request: {request}")
        
        search_query = request.get("search_query", request.get("query", ""))
        search_context = request.get("search_context", {})
        
        logger.info(f"Extracted search query: '{search_query}', context: {search_context}")
        
        if not search_query:
            logger.warning("No search query provided in request")
            return {
                "success": False,
                "error": "Missing search query",
                "agent_type": "medical_search",
            }
        
        try:
            # Perform the literature search
            logger.info(f"Starting medical literature search for: '{search_query}'")
            search_result = await self.search_medical_literature(
                search_query=search_query,
                search_context=search_context,
            )
            logger.info(f"Medical search completed successfully, found {len(search_result.information_sources)} sources")
            
            # Convert dataclass to dict for response
            return {
                "success": True,
                "search_id": search_result.search_id,
                "search_query": search_result.search_query,
                "information_sources": search_result.information_sources,
                "related_conditions": search_result.related_conditions,
                "drug_information": search_result.drug_information,
                "clinical_references": search_result.clinical_references,
                "search_confidence": search_result.search_confidence,
                "disclaimers": search_result.disclaimers,
                "source_links": search_result.source_links,
                "generated_at": search_result.generated_at.isoformat(),
                "total_sources": len(search_result.information_sources),
                "agent_type": "search",
            }
            
        except Exception as e:
            logger.exception(f"Search processing error: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent_type": "search",
            }
        finally:
            # Critical: Clean up MCP connection to prevent runaway tasks
            try:
                if hasattr(self.mcp_client, 'disconnect'):
                    await self.mcp_client.disconnect()
                    logger.debug("MCP client disconnected after search")
            except Exception as cleanup_error:
                logger.warning(f"Error during MCP cleanup: {cleanup_error}")

    async def _validate_medical_terms(self, concepts: list[str]) -> list[str]:
        """Validate and expand medical terms using MCP reference sources"""
        validated_concepts = []
        
        for concept in concepts:
            try:
                # For now, accept all SciSpacy-extracted terms as valid
                # Future: Use MCP to validate against medical knowledge bases
                # This is where your PubMed/FDA/ClinicalTrials MCPs would shine
                
                # Placeholder for MCP validation (implement when needed)
                # validation_result = await self.mcp_client.call_healthcare_tool(
                #     "validate_medical_term", {"term": concept}
                # )
                
                # For now, include all concepts
                validated_concepts.append(concept)
                    
            except Exception as e:
                logger.debug(f"Term validation failed for '{concept}': {e}")
                # Include concept anyway
                validated_concepts.append(concept)
        
        # Remove empty strings and duplicates
        return list(set(filter(None, validated_concepts)))

    async def search_medical_literature(
        self, search_query: str, search_context: dict[str, Any] | None = None,
    ) -> MedicalSearchResult:
        """
        Search medical literature like a medical librarian would
        Returns information about conditions, not diagnoses
        """
        logger.info(f"search_medical_literature called with query: '{search_query}'")
        
        try:
            # Get configurable timeout for entire search operation
            total_timeout = search_config.search_parameters.timeouts.get('total_search', 30)
            
            # Use asyncio.wait_for for overall timeout protection
            import asyncio
            result = await asyncio.wait_for(
                self._perform_literature_search(search_query, search_context),
                timeout=total_timeout
            )
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"Medical literature search timed out after {total_timeout}s for query: '{search_query[:100]}...'")
            # Return empty result with timeout message
            return MedicalSearchResult(
                search_id=self._generate_search_id(search_query),
                search_query=search_query,
                information_sources=[],
                related_conditions=[],
                drug_information=[],
                clinical_references=[],
                search_confidence=0.0,
                disclaimers=[f"Search request timed out after {total_timeout} seconds. Please try a more specific query."],
                source_links=[],
                generated_at=datetime.now()
            )
        except Exception as e:
            logger.error(f"Medical literature search failed: {e}")
            # Return empty result with error message
            return MedicalSearchResult(
                search_id=self._generate_search_id(search_query),
                search_query=search_query,
                information_sources=[],
                related_conditions=[],
                drug_information=[],
                clinical_references=[],
                search_confidence=0.0,
                disclaimers=[f"Search failed: {str(e)}"],
                source_links=[],
                generated_at=datetime.now()
            )
    
    async def _perform_literature_search(
        self, search_query: str, search_context: dict[str, Any] | None = None,
    ) -> MedicalSearchResult:
        """Core literature search logic with prompt injection detection"""
        
        # CRITICAL: Detect OpenWebUI prompt injections and reject them
        openwebui_prompts = [
            "Suggest 3-5 relevant follow-up questions",
            "Generate a concise, 3-5 word title with an emoji",
            "Query Generation Prompt",
            "Leave empty to use the default prompt",
            "Web Search Query Generation",
            "### Task:",
            "### Guidelines:",
            "### Output:",
            "JSON format:",
            "follow_ups",
            "title generation",
            "autocomplete generation"
        ]
        
        # Check if this is an OpenWebUI system prompt
        query_lower = search_query.lower()
        for prompt_indicator in openwebui_prompts:
            if prompt_indicator.lower() in query_lower:
                logger.warning(f"Rejecting OpenWebUI system prompt: '{search_query[:100]}...'")
                return MedicalSearchResult(
                    search_id=self._generate_search_id(search_query),
                    search_query=search_query,
                    information_sources=[],
                    related_conditions=[],
                    drug_information=[],
                    clinical_references=[],
                    search_confidence=0.0,
                    disclaimers=["This appears to be a system prompt. Please provide a medical research question instead."],
                    source_links=[],
                    generated_at=datetime.now()
                )
        
        logger.info(f"Processing legitimate medical search query: '{search_query}'")
        
        search_id = self._generate_search_id(search_query)
        logger.info(f"Generated search ID: {search_id}")

        # Parse search query for medical concepts using SciSpacy
        logger.info("Extracting medical concepts from query...")
        medical_concepts = await self._extract_medical_concepts(search_query)
        logger.info(f"SciSpacy extracted concepts: {medical_concepts}")
        
        # Validate and expand concepts using MCP knowledge bases
        logger.info("Validating medical concepts with MCP knowledge bases...")
        validated_concepts = await self._validate_medical_terms(medical_concepts)
        logger.info(f"MCP validated concepts: {validated_concepts}")

        # Parallel search across medical databases using validated concepts
        search_tasks = [
            self._search_condition_information(validated_concepts),
            self._search_symptom_literature(validated_concepts),
            self._search_drug_information(validated_concepts),
            self._search_clinical_references(validated_concepts),
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
        self, medical_concepts: list[str],
    ) -> list[dict[str, Any]]:
        """
        Search for condition information using database-first approach
        Returns: Information about conditions, not diagnostic recommendations
        """
        sources = []
        
        # Get configuration parameters
        max_results = search_config.search_parameters.max_results.get('condition_info', 10)
        query_template = search_config.search_parameters.query_templates.get(
            'condition_info', '{concept} overview pathophysiology symptoms'
        )
        publication_types = search_config.publication_types.condition_info
        url_pattern = search_config.url_patterns.get(
            'pubmed_article', 'https://pubmed.ncbi.nlm.nih.gov/{pmid}/'
        )

        for concept in medical_concepts:
            try:
                # DATABASE-FIRST: Try database lookup first
                logger.info(f"Searching database for condition information on '{concept}'...")
                
                try:
                    # Try database first (synthetic healthcare data)
                    from core.models.healthcare import Encounter
                    from core.database.healthcare_database import get_database_session
                    
                    async with get_database_session() as session:
                        db_results = await session.execute(
                            f"SELECT diagnosis_codes, soap_notes FROM encounters WHERE diagnosis_codes ILIKE '%{concept}%' LIMIT 5"
                        )
                        
                        for row in db_results:
                            sources.append({
                                "source_type": "condition_information",
                                "title": f"Clinical Case: {concept}",
                                "content": row.soap_notes[:500] + "..." if len(row.soap_notes) > 500 else row.soap_notes,
                                "source": "Healthcare Database",
                                "evidence_level": "clinical_case",
                                "relevance_score": 0.8,
                                "concept": concept,
                                "url": "#database_case",
                                "publication_date": "2024",
                                "study_type": "case_series"
                            })
                        
                        logger.info(f"Found {len(sources)} database entries for '{concept}'")
                        
                except Exception as db_error:
                    logger.warning(f"Database lookup failed for '{concept}': {db_error}")
                    # Continue to MCP search even if database fails
                
                # MCP SEARCH: Use MCP tools for literature search (even if database failed)
                logger.info(f"Searching MCP literature sources for '{concept}'...")
                
                search_query = query_template.format(concept=concept)
                
                # Add timeout protection for MCP calls
                mcp_timeout = search_config.search_parameters.timeouts.get('mcp_request', 15)
                
                import asyncio
                try:
                    logger.info(f"Starting MCP call to 'search-pubmed' with timeout {mcp_timeout}s for concept '{concept}'...")
                    
                    # Test MCP connection first
                    try:
                        await asyncio.wait_for(self.mcp_client._ensure_connected(), timeout=5)
                        logger.info("MCP connection established successfully")
                    except Exception as conn_error:
                        logger.error(f"MCP connection failed: {conn_error}")
                        raise conn_error
                    
                    literature_results = await asyncio.wait_for(
                        self.mcp_client.call_healthcare_tool(
                            "search-pubmed",  # Fixed: Use hyphen (MCP tool name)
                            {
                                "query": search_query,
                                "max_results": max_results,
                                "publication_types": publication_types,
                            },
                        ),
                        timeout=mcp_timeout
                    )
                    logger.info(f"MCP call completed successfully, got {len(literature_results.get('articles', []))} articles for '{concept}'")

                    for article in literature_results.get("articles", []):
                        pmid = article.get("pmid", "")
                        sources.append(
                            {
                                "source_type": "condition_information",
                                "title": article.get("title", ""),
                                "content": article.get("abstract", ""),
                                "source": f"PubMed:{pmid}",
                                "evidence_level": article.get("evidence_level", "peer_reviewed"),
                                "relevance_score": self._calculate_concept_relevance(concept, article),
                                "concept": concept,
                                "url": url_pattern.format(pmid=pmid),
                                "publication_date": article.get("publication_date", ""),
                                "study_type": article.get("study_type", "research_article"),
                            }
                        )
                        
                    logger.info(f"MCP search found {len(literature_results.get('articles', []))} articles for '{concept}'")
                        
                except asyncio.TimeoutError:
                    logger.warning(f"MCP search timed out after {mcp_timeout}s for concept '{concept}'")
                    # Continue with other concepts
                except Exception as mcp_error:
                    logger.warning(f"MCP literature search failed for '{concept}': {mcp_error}")
                    # Continue with other concepts
                    
            except Exception as e:
                logger.warning(f"Failed to search condition information for '{concept}': {e}")
                # Continue with other concepts

        logger.info(f"Total condition information sources found: {len(sources)}")
        return sources

    async def _search_symptom_literature(self, medical_concepts: list[str]) -> list[dict[str, Any]]:
        """
        Search literature about symptoms and their associations
        Returns: Literature about what symptoms are associated with, not diagnoses
        """
        sources = []
        
        # Get configuration parameters
        max_results = search_config.search_parameters.max_results.get('symptom_literature', 15)
        query_template = search_config.search_parameters.query_templates.get(
            'symptom_literature', '{symptom} presentation differential clinical features'
        )
        publication_types = search_config.publication_types.symptom_literature
        url_pattern = search_config.url_patterns.get(
            'pubmed_article', 'https://pubmed.ncbi.nlm.nih.gov/{pmid}/'
        )

        # Use all medical concepts from SciSpacy (no hardcoded filtering)
        # SciSpacy already identifies medical entities accurately
        for symptom in medical_concepts:
            try:
                # Use configurable query template
                search_query = query_template.format(symptom=symptom)
                
                # Add timeout protection for MCP calls
                mcp_timeout = search_config.search_parameters.timeouts.get('mcp_request', 15)
                
                # Search for literature about symptom presentations using PubMed
                # Medical search agent focuses on medical literature sources
                import asyncio
                try:
                    literature_results = await asyncio.wait_for(
                        self.mcp_client.call_healthcare_tool(
                            "search-pubmed",  # Fixed: Use hyphen (MCP tool name)
                            {
                                "query": search_query,
                                "max_results": max_results,
                                "publication_types": publication_types,
                            },
                        ),
                        timeout=mcp_timeout
                    )

                    for article in literature_results.get("articles", []):
                        pmid = article.get("pmid", "")
                        sources.append(
                            {
                                "source_type": "symptom_literature",
                                "symptom": symptom,
                                "title": article.get("title", ""),
                                "journal": article.get("journal", ""),
                                "publication_date": article.get("date", ""),
                                "pmid": pmid,
                                "url": url_pattern.format(pmid=pmid),
                                "abstract": article.get("abstract", ""),
                                "evidence_level": self._determine_evidence_level(article),
                                "information_type": "symptom_research",
                            },
                        )
                        
                    logger.info(f"MCP search found {len(literature_results.get('articles', []))} articles for symptom '{symptom}'")
                        
                except asyncio.TimeoutError:
                    logger.warning(f"MCP search timed out after {mcp_timeout}s for symptom '{symptom}'")
                except Exception as mcp_error:
                    logger.warning(f"MCP literature search failed for symptom '{symptom}': {mcp_error}")

            except Exception as e:
                logger.warning(f"Failed to search symptom literature for '{symptom}': {e}")

        logger.info(f"Total symptom literature sources found: {len(sources)}")
        return sources

    async def _search_drug_information(self, medical_concepts: list[str]) -> list[dict[str, Any]]:
        """
        Search for drug information and interactions
        Returns: Official drug information, not prescribing advice
        """
        sources = []
        
        # Get configuration parameters
        fda_url_pattern = search_config.url_patterns.get(
            'fda_drug', 'https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm'
        )

        # Use all medical concepts from SciSpacy (SciSpacy detects CHEMICAL entities for drugs)
        # Medical search agent focuses on FDA drug database
        for drug_concept in medical_concepts:
            try:
                # Add timeout protection for MCP calls
                mcp_timeout = search_config.search_parameters.timeouts.get('mcp_request', 15)
                
                # Search FDA drug database - focused medical source
                import asyncio
                try:
                    drug_results = await asyncio.wait_for(
                        self.mcp_client.call_healthcare_tool(
                            "get-drug-info",  # Fixed: Use correct MCP tool name
                            {
                                "drug_name": drug_concept,
                                "include_interactions": True,
                                "include_prescribing_info": True,
                            },
                        ),
                        timeout=mcp_timeout
                    )

                    if drug_results.get("found"):
                        # Use configurable URL pattern if application number available
                        drug_url = drug_results.get("fda_url", "")
                        if not drug_url and drug_results.get("application_number"):
                            drug_url = fda_url_pattern.format(
                                application_number=drug_results.get("application_number")
                            )
                        
                        sources.append(
                            {
                                "source_type": "drug_info",
                                "drug_name": drug_concept,
                                "fda_approval": drug_results.get("approval_date", ""),
                                "manufacturer": drug_results.get("manufacturer", ""),
                                "indications": drug_results.get("indications", []),
                                "contraindications": drug_results.get("contraindications", []),
                                "interactions": drug_results.get("interactions", []),
                                "url": drug_url,
                                "information_type": "regulatory_information",
                                "evidence_level": "regulatory_approval",
                            },
                        )
                        
                    logger.info(f"MCP drug search completed for '{drug_concept}': {'found' if drug_results.get('found') else 'not found'}")
                        
                except asyncio.TimeoutError:
                    logger.warning(f"MCP drug search timed out after {mcp_timeout}s for drug '{drug_concept}'")
                except Exception as mcp_error:
                    logger.warning(f"MCP drug search failed for '{drug_concept}': {mcp_error}")

            except Exception as e:
                logger.warning(f"Failed to search drug information for '{drug_concept}': {e}")

        logger.info(f"Total drug information sources found: {len(sources)}")
        return sources

    async def _search_clinical_references(
        self, medical_concepts: list[str],
    ) -> list[dict[str, Any]]:
        """
        Search clinical practice guidelines and reference materials
        Returns: Reference information for clinical context
        """
        sources = []
        
        # Get configuration parameters
        trusted_orgs = search_config.trusted_organizations
        max_results = search_config.search_parameters.max_results.get('clinical_references', 5)

        for concept in medical_concepts:
            try:
                # Add timeout protection for MCP calls
                mcp_timeout = search_config.search_parameters.timeouts.get('mcp_request', 15)
                
                # Search for clinical guidelines - focused medical source
                import asyncio
                try:
                    guideline_results = await asyncio.wait_for(
                        self.mcp_client.call_healthcare_tool(
                            "search-trials",  # Fixed: Use correct MCP tool name
                            {
                                "condition": concept,
                                "organizations": trusted_orgs,
                                "max_results": max_results,
                            },
                        ),
                        timeout=mcp_timeout
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
                            },
                        )
                        
                    logger.info(f"MCP trials search found {len(guideline_results.get('guidelines', []))} guidelines for '{concept}'")
                        
                except asyncio.TimeoutError:
                    logger.warning(f"MCP trials search timed out after {mcp_timeout}s for concept '{concept}'")
                except Exception as mcp_error:
                    logger.warning(f"MCP trials search failed for '{concept}': {mcp_error}")

            except Exception as e:
                logger.warning(f"Failed to search clinical guidelines for '{concept}': {e}")

        logger.info(f"Total clinical reference sources found: {len(sources)}")
        return sources

    def _extract_literature_conditions(self, sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Extract conditions mentioned in literature using SciSpacy (not diagnose them)
        Returns: List of conditions found in literature with context
        """
        conditions: list[dict[str, Any]] = []
        
        for source in sources:
            # Extract conditions mentioned in abstracts/summaries using SciSpacy
            text_content = " ".join(
                [
                    source.get("title", ""),
                    source.get("abstract", ""),
                    source.get("summary", ""),
                ],
            )
            
            if not text_content.strip():
                continue
                
            try:
                # Use SciSpacy to extract medical entities from literature text
                import asyncio
                extracted_conditions = asyncio.run(self._extract_conditions_from_text(text_content))
                
                for condition in extracted_conditions:
                    conditions.append(
                        {
                            "condition_name": condition,
                            "mentioned_in_source": source.get("title", "Unknown source"),
                            "source_type": source.get("source_type", ""),
                            "evidence_level": source.get("evidence_level", ""),
                            "source_url": source.get("url", ""),
                            "context": "mentioned_in_literature",
                            "note": "Condition mentioned in medical literature, not a diagnosis",
                            "extraction_method": "scispacy_nlp",
                        },
                    )
                    
            except Exception as e:
                logger.warning(f"SciSpacy extraction failed for source: {e}")
                continue

        # Remove duplicates and limit results
        unique_conditions: dict[str, dict[str, Any]] = {}
        for condition_dict in conditions:
            key = condition_dict["condition_name"].lower()
            if key not in unique_conditions:
                unique_conditions[key] = condition_dict

        return list(unique_conditions.values())[:10]  # Top 10 mentioned conditions

    async def _extract_conditions_from_text(self, text: str) -> list[str]:
        """Extract medical conditions from text using SciSpacy"""
        try:
            # Call SciSpacy service for biomedical entity extraction
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://172.20.0.6:8001/analyze",  # SciSpacy service
                    json={"text": text},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # Extract only DISEASE entities as conditions
                        conditions = []
                        for entity in result.get("entities", []):
                            if entity.get("label") == "DISEASE":
                                condition_text = entity.get("text", "").strip()
                                if condition_text and len(condition_text) > 2:  # Filter very short terms
                                    conditions.append(condition_text)
                        
                        return list(set(conditions))  # Remove duplicates
                    else:
                        logger.warning(f"SciSpacy service returned status {response.status}")
                        return []
                        
        except Exception as e:
            logger.warning(f"SciSpacy condition extraction failed: {e}")
            return []

    def _rank_sources_by_evidence(
        self, sources: list[dict[str, Any]], query: str,
    ) -> list[dict[str, Any]]:
        """
        Rank sources by evidence quality and relevance, like a medical librarian would
        """
        # Use configurable evidence weights
        evidence_weights = search_config.evidence_weights

        scored_sources = []
        query_terms = set(query.lower().split())

        for source in sources:
            # Base evidence score using configuration
            evidence_level = source.get("evidence_level", "unknown")
            base_score = evidence_weights.get(evidence_level, 1)

            # Relevance score
            source_text = " ".join(
                [
                    source.get("title", ""),
                    source.get("abstract", ""),
                    source.get("summary", ""),
                ],
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
                },
            )

        return sorted(scored_sources, key=lambda x: x.get("search_score", 0), reverse=True)

    def _calculate_search_confidence(self, sources: list[dict[str, Any]], query: str) -> float:
        """
        Calculate how confident we are that we found good information (not diagnostic confidence)
        """
        if not sources:
            return 0.0

        # Get configurable confidence parameters
        min_sources = search_config.confidence_parameters.get('min_sources_for_high_confidence', 15)
        min_high_quality = search_config.confidence_parameters.get('min_high_quality_sources', 5)

        # Factors for search quality
        source_count_factor = min(len(sources) / float(min_sources), 1.0)

        # Evidence quality factor - count high-quality sources
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
        quality_factor = min(high_quality_sources / float(min_high_quality), 1.0)

        # Relevance factor
        relevance_scores = [float(s.get("relevance_score", 0)) for s in sources]
        avg_relevance = sum(relevance_scores) / len(sources) if sources else 0.0

        # Search confidence (not diagnostic confidence)
        search_confidence = (
            (source_count_factor * 0.3) + (quality_factor * 0.4) + (avg_relevance * 0.3)
        )

        return min(search_confidence, 1.0)

    async def _extract_medical_concepts(self, search_query: str) -> list[str]:
        """Extract medical concepts using SciSpacy entities + LLM query understanding"""
        try:
            logger.info("Extracting medical entities via SciSpacy...")
            
            # Get configurable timeout
            scispacy_timeout = search_config.search_parameters.timeouts.get('scispacy_request', 10)
            
            # Call SciSpacy service for biomedical entity extraction
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://172.20.0.6:8001/analyze",  # SciSpacy service
                    json={"text": search_query},
                    timeout=aiohttp.ClientTimeout(total=scispacy_timeout)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # Extract comprehensive medical entities from bionlp13cg model
                        # Entity types: AMINO_ACID, ANATOMICAL_SYSTEM, CANCER, CELL, CELLULAR_COMPONENT,
                        # DEVELOPING_ANATOMICAL_STRUCTURE, GENE_OR_GENE_PRODUCT, IMMATERIAL_ANATOMICAL_ENTITY,
                        # MULTI-TISSUE_STRUCTURE, ORGAN, ORGANISM, ORGANISM_SUBDIVISION,
                        # ORGANISM_SUBSTANCE, PATHOLOGICAL_FORMATION, SIMPLE_CHEMICAL, TISSUE
                        medical_entity_types = {
                            "AMINO_ACID", "ANATOMICAL_SYSTEM", "CANCER", "CELL", "CELLULAR_COMPONENT",
                            "DEVELOPING_ANATOMICAL_STRUCTURE", "GENE_OR_GENE_PRODUCT", "IMMATERIAL_ANATOMICAL_ENTITY",
                            "MULTI-TISSUE_STRUCTURE", "ORGAN", "ORGANISM", "ORGANISM_SUBDIVISION",
                            "ORGANISM_SUBSTANCE", "PATHOLOGICAL_FORMATION", "SIMPLE_CHEMICAL", "TISSUE"
                        }
                        medical_entities = []
                        for entity in result.get("entities", []):
                            if entity.get("label") in medical_entity_types:
                                medical_entities.append(entity.get("text", ""))
                        
                        logger.info(f"SciSpacy extracted {len(medical_entities)} medical entities: {medical_entities}")
                        
                        # Use LLM to understand query intent and craft search terms
                        llm_search_terms = await self._llm_craft_search_terms(search_query, medical_entities)
                        
                        # Combine both approaches
                        all_concepts = medical_entities + llm_search_terms
                        unique_concepts = list(dict.fromkeys(all_concepts))  # Preserve order, remove duplicates
                        
                        logger.info(f"Combined medical concepts: {unique_concepts}")
                        return unique_concepts
                    else:
                        logger.warning(f"SciSpacy service returned status {response.status}")
                        raise Exception(f"SciSpacy service error: {response.status}")
                        
        except Exception as e:
            logger.error(f"SciSpacy entity extraction failed: {e}")
            raise Exception(f"Medical entity extraction failed: {e}")

    async def _llm_craft_search_terms(self, original_query: str, medical_entities: list[str]) -> list[str]:
        """Use LLM to understand query intent and craft appropriate PubMed search terms"""
        try:
            # Create a prompt for the LLM to understand the query and suggest search terms
            prompt = f"""Given this medical query: "{original_query}"
            
Medical entities found: {medical_entities}

Craft 3-5 precise PubMed search terms that would find relevant medical literature.
Consider:
- The user's intent (recent articles, specific conditions, treatments, etc.)
- Broader medical concepts that might not be detected as entities
- Synonyms and related terms that researchers would use

Return only the search terms, one per line, no explanations:"""

            # Call local LLM for search term generation
            response = await self.llm_client.chat(
                model="llama3.1:8b",
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Extract search terms from LLM response
            llm_terms = []
            if response and "message" in response and "content" in response["message"]:
                content = response["message"]["content"].strip()
                # Split by lines and clean up
                terms = [term.strip() for term in content.split('\n') if term.strip()]
                # Filter out explanatory text, keep only actual search terms
                for term in terms:
                    if len(term) < 50 and not term.startswith(('The ', 'Here ', 'Consider ', '- ')):
                        llm_terms.append(term)
            
            logger.info(f"LLM crafted search terms: {llm_terms}")
            return llm_terms[:5]  # Limit to 5 terms
            
        except Exception as e:
            logger.warning(f"LLM search term crafting failed: {e}")
            # Fallback to simple keyword extraction
            keywords = [word for word in original_query.split()
                        if len(word) > 3 and word.lower() not in ['help', 'find', 'articles', 'recent']]
            return keywords[:3]

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
        if "meta-analysis" in pub_type or "meta-analysis" in title:
            return "meta_analysis"
        if "randomized controlled trial" in pub_type:
            return "randomized_controlled_trial"
        if "clinical trial" in pub_type:
            return "clinical_study"
        if "review" in pub_type:
            return "review"
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
            if years_old <= 5:
                return 0.5
            if years_old <= 10:
                return 0.2
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
        return hashlib.md5(f"{query}{datetime.utcnow()}".encode()).hexdigest()[:12]
