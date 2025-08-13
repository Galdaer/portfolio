"""
Medical Literature Search Assistant
Provides information about medical concepts, not diagnoses
"""

import asyncio
import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from agents import BaseHealthcareAgent
from config.medical_search_config_loader import MedicalSearchConfigLoader
from core.infrastructure.agent_context import AgentContext, new_agent_context
from core.infrastructure.agent_metrics import AgentMetricsStore
from core.infrastructure.healthcare_logger import get_healthcare_logger
from core.medical import search_utils as medical_search_utils
from core.search import extract_source_links

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
        self._metrics = AgentMetricsStore(agent_name="medical_search")

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
        # Derived disclaimer set from centralized utilities (ensures consistency)
        try:
            self.disclaimers = medical_search_utils.generate_medical_disclaimers()
        except Exception:
            pass

        # Limit MCP concurrency to reduce transport contention/TaskGroup errors
        try:
            timeouts_cfg = getattr(search_config, "search_parameters", None)
            timeouts_map = getattr(timeouts_cfg, "timeouts", {}) if timeouts_cfg else {}
            if not isinstance(timeouts_map, dict):
                timeouts_map = {}
            max_concurrent = int(timeouts_map.get("max_concurrent_mcp", 2))
        except Exception:
            max_concurrent = 2
        # Semaphore used around MCP tool invocations
        import asyncio as _asyncio  # local alias to avoid name shadowing
        self._mcp_sem = _asyncio.Semaphore(max(1, int(max_concurrent)))

    async def _process_implementation(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Required implementation for BaseHealthcareAgent
        Processes search requests through the standard agent interface
        """
        logger.info(f"Medical search agent processing request: {request}")
        ctx: AgentContext = new_agent_context("medical_search", user_id=request.get("user_id"))
        await self._metrics.incr("requests_total")

        search_query = request.get("search_query", request.get("query", ""))
        search_context = request.get("search_context", {})

        logger.info(f"Extracted search query: '{search_query}', context: {search_context}")

        if not search_query:
            logger.warning("No search query provided in request")
            await self._metrics.incr("requests_error_missing_query")
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
            await self._metrics.incr("requests_success")
            await self._metrics.record_timing("request_ms", ctx.elapsed_ms)

            # Convert dataclass to dict for response and include a formatted summary
            formatted_summary = medical_search_utils.format_medical_search_response(
                search_results=search_result.information_sources,
                query=search_query,
                related_conditions=search_result.related_conditions,
                max_items=8,
                disclaimers=search_result.disclaimers,
            )

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
                "formatted_summary": formatted_summary,
            }

        except Exception as e:
            logger.exception(f"Search processing error: {e}")
            await self._metrics.incr("requests_exception")
            return {
                "success": False,
                "error": str(e),
                "agent_type": "search",
            }
        finally:
            # MCP lifecycle is handled by application shutdown via HealthcareServices.cleanup()
            pass

    async def _validate_medical_terms(self, concepts: list[str]) -> list[str]:
        """Validate and normalize medical terms using basic heuristics.

        Current filters:
          - Strip whitespace, drop empty
          - Min length 3
          - Exclude pure numeric tokens
          - Deduplicate case-insensitively (keep first occurrence for ordering)
        Future: integrate MCP ontology validation (e.g., UMLS, MeSH).
        """
        seen: set[str] = set()
        cleaned: list[str] = []
        for raw in concepts:
            term = (raw or "").strip()
            if not term:
                continue
            if len(term) < 3:
                continue
            if all(ch.isdigit() for ch in term):
                continue
            key = term.lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(term)
        return cleaned

    async def search_medical_literature(
        self, search_query: str, search_context: dict[str, Any] | None = None,
    ) -> MedicalSearchResult:
        """
        Search medical literature like a medical librarian would
        Returns information about conditions, not diagnoses
        """
        logger.info(f"search_medical_literature called with query: '{search_query}'")

        try:
            # Get configurable timeout for entire search operation; prefer 'total_search' if present
            sp = getattr(search_config, "search_parameters", None)
            timeouts_cfg = getattr(sp, "timeouts", {}) if sp else {}
            if not isinstance(timeouts_cfg, dict):
                timeouts_cfg = {}
            total_timeout = (
                timeouts_cfg.get("total_search")
                or timeouts_cfg.get("search_request")
                or 60
            )

            # Use asyncio.wait_for for overall timeout protection (module-level import)
            result = await asyncio.wait_for(
                self._perform_literature_search(search_query, search_context),
                timeout=total_timeout,
            )
            return result

        except TimeoutError:
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
                generated_at=datetime.now(UTC),
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
                generated_at=datetime.now(UTC),
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
            "autocomplete generation",
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
                    generated_at=datetime.now(UTC),
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

        # Rank by medical evidence quality and relevance (centralized util)
        ranked_sources = medical_search_utils.rank_sources_by_evidence_and_relevance(all_sources, search_query)

        # Extract related conditions from literature (not diagnose them)
        related_conditions = await self._extract_literature_conditions(ranked_sources)

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
            source_links=extract_source_links(ranked_sources),
            generated_at=datetime.now(UTC),
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
        sp = getattr(search_config, "search_parameters", None)
        max_results_map = getattr(sp, "max_results", {}) if sp else {}
        if not isinstance(max_results_map, dict):
            max_results_map = {}
        query_templates_map = getattr(sp, "query_templates", {}) if sp else {}
        if not isinstance(query_templates_map, dict):
            query_templates_map = {}
        max_results = int(max_results_map.get("condition_info", 10))
        query_template = query_templates_map.get("condition_info", "{concept} overview pathophysiology symptoms")
        publication_types = getattr(getattr(search_config, "publication_types", None), "condition_info", [])
        url_patterns_map = getattr(search_config, "url_patterns", {}) or {}
        if not isinstance(url_patterns_map, dict):
            url_patterns_map = {}
        url_pattern = url_patterns_map.get("pubmed_article", "https://pubmed.ncbi.nlm.nih.gov/{pmid}/")

        for concept in medical_concepts:
            try:
                # DATABASE-FIRST: Try database lookup first
                logger.info(f"Searching database for condition information on '{concept}'...")

                try:
                    # Try database first (synthetic healthcare data)
                    from core.database.healthcare_database import get_database_session

                    async with get_database_session() as session:
                        db_results = await session.execute(
                            f"SELECT diagnosis_codes, soap_notes FROM encounters WHERE diagnosis_codes ILIKE '%{concept}%' LIMIT 5",
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
                                "study_type": "case_series",
                            })

                        logger.info(f"Found {len(sources)} database entries for '{concept}'")

                except Exception as db_error:
                    logger.warning(f"Database lookup failed for '{concept}': {db_error}")
                    # Continue to MCP search even if database fails

                # MCP SEARCH: Use MCP tools for literature search (even if database failed)
                logger.info(f"Searching MCP literature sources for '{concept}'...")

                search_query = query_template.format(concept=concept)

                # Add timeout protection for MCP calls
                sp = getattr(search_config, "search_parameters", None)
                timeouts_map = getattr(sp, "timeouts", {}) if sp else {}
                if not isinstance(timeouts_map, dict):
                    timeouts_map = {}
                mcp_timeout = int(timeouts_map.get("mcp_request", 45))

                try:
                    logger.info(f"Starting MCP call to 'search-pubmed' with timeout {mcp_timeout}s for concept '{concept}'...")
                    # Health check if available
                    if hasattr(self.mcp_client, "_ensure_connected"):
                        try:
                            await asyncio.wait_for(self.mcp_client._ensure_connected(), timeout=5)
                            logger.info("MCP connection established successfully")
                        except Exception as conn_error:
                            logger.error(f"MCP connection failed pre-call: {conn_error}")
                            # Continue; client has internal retry

                    # Limit concurrency across all MCP calls
                    async with self._mcp_sem:
                        literature_results = await asyncio.wait_for(
                            self.mcp_client.call_healthcare_tool(
                                "search-pubmed",  # Fixed: Use hyphen (MCP tool name)
                                {
                                    "query": search_query,
                                    "max_results": max_results,
                                    "publication_types": publication_types,
                                },
                            ),
                            timeout=mcp_timeout,
                        )
                    # Raw result debugging
                    logger.info(f"Raw MCP result for concept '{concept}': type={type(literature_results).__name__} keys={list(literature_results.keys()) if isinstance(literature_results, dict) else 'n/a'}")
                    if isinstance(literature_results, dict) and "content" in literature_results:
                        logger.info(f"MCP content field type: {type(literature_results['content']).__name__}")

                    parsed_articles = medical_search_utils.parse_mcp_search_results(literature_results)
                    logger.info(f"MCP call completed successfully, parsed {len(parsed_articles)} articles for '{concept}'")

                    for article in parsed_articles:
                        pmid = article.get("pmid", "")
                        sources.append(
                            {
                                "source_type": "condition_information",
                                "title": article.get("title", ""),
                                "content": article.get("abstract", ""),
                                "source": f"PubMed:{pmid}" if pmid else "PubMed",
                                "evidence_level": article.get("evidence_level") or medical_search_utils.determine_evidence_level(article),
                                "relevance_score": self._calculate_concept_relevance(concept, article),
                                "concept": concept,
                                "url": url_pattern.format(pmid=pmid) if pmid else article.get("url", ""),
                                "publication_date": article.get("date", ""),
                                "study_type": article.get("study_type", article.get("publication_type", "research_article")),
                            },
                        )

                    logger.info(f"MCP search found {len(parsed_articles)} articles for '{concept}'")

                except TimeoutError:
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
        sp = getattr(search_config, "search_parameters", None)
        max_results_map = getattr(sp, "max_results", {}) if sp else {}
        if not isinstance(max_results_map, dict):
            max_results_map = {}
        query_templates_map = getattr(sp, "query_templates", {}) if sp else {}
        if not isinstance(query_templates_map, dict):
            query_templates_map = {}
        max_results = int(max_results_map.get("symptom_literature", 15))
        query_template = query_templates_map.get("symptom_literature", "{symptom} presentation differential clinical features")
        publication_types = getattr(getattr(search_config, "publication_types", None), "symptom_literature", [])
        url_patterns_map = getattr(search_config, "url_patterns", {}) or {}
        if not isinstance(url_patterns_map, dict):
            url_patterns_map = {}
        url_pattern = url_patterns_map.get("pubmed_article", "https://pubmed.ncbi.nlm.nih.gov/{pmid}/")

        # Use all medical concepts from SciSpacy (no hardcoded filtering)
        # SciSpacy already identifies medical entities accurately
        for symptom in medical_concepts:
            try:
                # Use configurable query template
                search_query = query_template.format(symptom=symptom)

                # Add timeout protection for MCP calls
                sp = getattr(search_config, "search_parameters", None)
                timeouts_map = getattr(sp, "timeouts", {}) if sp else {}
                if not isinstance(timeouts_map, dict):
                    timeouts_map = {}
                mcp_timeout = int(timeouts_map.get("mcp_request", 45))

                # Search for literature about symptom presentations using PubMed
                # Medical search agent focuses on medical literature sources
                try:
                    async with self._mcp_sem:
                        literature_results = await asyncio.wait_for(
                            self.mcp_client.call_healthcare_tool(
                                "search-pubmed",  # Fixed: Use hyphen (MCP tool name)
                                {
                                    "query": search_query,
                                    "max_results": max_results,
                                    "publication_types": publication_types,
                                },
                            ),
                            timeout=mcp_timeout,
                        )
                    # Debug raw response and parse
                    logger.info(f"Raw MCP result for symptom '{symptom}': type={type(literature_results).__name__} keys={list(literature_results.keys()) if isinstance(literature_results, dict) else 'n/a'}")
                    parsed_articles = medical_search_utils.parse_mcp_search_results(literature_results)

                    for article in parsed_articles:
                        pmid = article.get("pmid", "")
                        sources.append(
                            {
                                "source_type": "symptom_literature",
                                "symptom": symptom,
                                "title": article.get("title", ""),
                                "journal": article.get("journal", ""),
                                "publication_date": article.get("date", ""),
                                "pmid": pmid,
                                "url": url_pattern.format(pmid=pmid) if pmid else article.get("url", ""),
                                "abstract": article.get("abstract", ""),
                                "evidence_level": medical_search_utils.determine_evidence_level(article),
                                "information_type": "symptom_research",
                            },
                        )

                    logger.info(f"MCP search found {len(parsed_articles)} articles for symptom '{symptom}'")

                except TimeoutError:
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
        url_patterns_map = getattr(search_config, "url_patterns", {}) or {}
        if not isinstance(url_patterns_map, dict):
            url_patterns_map = {}
        fda_url_pattern = url_patterns_map.get("fda_drug", "https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm")

        # Use all medical concepts from SciSpacy (SciSpacy detects CHEMICAL entities for drugs)
        # Medical search agent focuses on FDA drug database
        for drug_concept in medical_concepts:
            try:
                # Add timeout protection for MCP calls
                sp = getattr(search_config, "search_parameters", None)
                timeouts_map = getattr(sp, "timeouts", {}) if sp else {}
                if not isinstance(timeouts_map, dict):
                    timeouts_map = {}
                mcp_timeout = int(timeouts_map.get("mcp_request", 45))

                # Search FDA drug database - focused medical source
                try:
                    async with self._mcp_sem:
                        drug_results = await asyncio.wait_for(
                            self.mcp_client.call_healthcare_tool(
                                "get-drug-info",  # Fixed: Use correct MCP tool name
                                {
                                    "drug_name": drug_concept,
                                    "include_interactions": True,
                                    "include_prescribing_info": True,
                                },
                            ),
                            timeout=mcp_timeout,
                        )

                    logger.info(f"Raw MCP drug result for '{drug_concept}': type={type(drug_results).__name__} keys={list(drug_results.keys()) if isinstance(drug_results, dict) else 'n/a'}")

                    found_flag = False
                    if isinstance(drug_results, dict):
                        found_flag = bool(drug_results.get("found"))
                    if found_flag:
                        # Use configurable URL pattern if application number available
                        drug_url = drug_results.get("fda_url", "") if isinstance(drug_results, dict) else ""
                        if not drug_url and isinstance(drug_results, dict) and drug_results.get("application_number"):
                            drug_url = fda_url_pattern.format(
                                application_number=drug_results.get("application_number"),
                            )

                        sources.append(
                            {
                                "source_type": "drug_info",
                                "drug_name": drug_concept,
                                "fda_approval": drug_results.get("approval_date", "") if isinstance(drug_results, dict) else "",
                                "manufacturer": drug_results.get("manufacturer", "") if isinstance(drug_results, dict) else "",
                                "indications": drug_results.get("indications", []) if isinstance(drug_results, dict) else [],
                                "contraindications": drug_results.get("contraindications", []) if isinstance(drug_results, dict) else [],
                                "interactions": drug_results.get("interactions", []) if isinstance(drug_results, dict) else [],
                                "url": drug_url,
                                "information_type": "regulatory_information",
                                "evidence_level": "regulatory_approval",
                            },
                        )

                    status_txt = "found" if (isinstance(drug_results, dict) and drug_results.get("found")) else "not found"
                    logger.info(f"MCP drug search completed for '{drug_concept}': {status_txt}")

                except TimeoutError:
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
        trusted_orgs = getattr(search_config, "trusted_organizations", [])
        sp = getattr(search_config, "search_parameters", None)
        max_results_map = getattr(sp, "max_results", {}) if sp else {}
        if not isinstance(max_results_map, dict):
            max_results_map = {}
        max_results = int(max_results_map.get("clinical_references", 5))

        for concept in medical_concepts:
            try:
                # Add timeout protection for MCP calls
                sp = getattr(search_config, "search_parameters", None)
                timeouts_map = getattr(sp, "timeouts", {}) if sp else {}
                if not isinstance(timeouts_map, dict):
                    timeouts_map = {}
                mcp_timeout = int(timeouts_map.get("mcp_request", 45))

                # Search for clinical guidelines - focused medical source
                try:
                    async with self._mcp_sem:
                        guideline_results = await asyncio.wait_for(
                            self.mcp_client.call_healthcare_tool(
                                "search-trials",  # Fixed: Use correct MCP tool name
                                {
                                    "condition": concept,
                                    "organizations": trusted_orgs,
                                    "max_results": max_results,
                                },
                            ),
                            timeout=mcp_timeout,
                        )
                    logger.info(f"Raw MCP trials/guidelines result for '{concept}': type={type(guideline_results).__name__} keys={list(guideline_results.keys()) if isinstance(guideline_results, dict) else 'n/a'}")

                    guidelines = []
                    if isinstance(guideline_results, dict):
                        if isinstance(guideline_results.get("guidelines"), list):
                            guidelines = guideline_results.get("guidelines", [])
                        else:
                            # Fallback: try generic parser for records
                            guidelines = medical_search_utils.parse_mcp_search_results(guideline_results)

                    for guideline in guidelines:
                        sources.append(
                            {
                                "source_type": "clinical_guideline",
                                "concept": concept,
                                "title": guideline.get("title", ""),
                                "organization": guideline.get("organization", ""),
                                "publication_year": guideline.get("year", guideline.get("date", "")),
                                "url": guideline.get("url", guideline.get("_raw", {}).get("url", "")),
                                "summary": guideline.get("summary", guideline.get("abstract", "")),
                                "evidence_grade": guideline.get("evidence_grade", guideline.get("evidence_level", "")),
                                "information_type": "clinical_reference",
                                "evidence_level": "clinical_guideline",
                            },
                        )

                    logger.info(f"MCP trials search found {len(guidelines)} guidelines for '{concept}'")

                except TimeoutError:
                    logger.warning(f"MCP trials search timed out after {mcp_timeout}s for concept '{concept}'")
                except Exception as mcp_error:
                    logger.warning(f"MCP trials search failed for '{concept}': {mcp_error}")

            except Exception as e:
                logger.warning(f"Failed to search clinical guidelines for '{concept}': {e}")

        logger.info(f"Total clinical reference sources found: {len(sources)}")
        return sources

    async def _extract_literature_conditions(self, sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
                extracted_conditions = await self._extract_conditions_from_text(text_content)

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
            # Use configurable timeout for SciSpacy requests
            sp = getattr(search_config, "search_parameters", None)
            timeouts_map = getattr(sp, "timeouts", {}) if sp else {}
            if not isinstance(timeouts_map, dict):
                timeouts_map = {}
            scispacy_timeout = int(timeouts_map.get("scispacy_request", 15))
            # Call SciSpacy service for biomedical entity extraction
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://172.20.0.6:8001/analyze",  # SciSpacy service
                    json={"text": text},
                    timeout=aiohttp.ClientTimeout(total=scispacy_timeout),
                ) as response:
                    if response.status == 200:
                        result = await response.json()

                        # Extract only DISEASE entities as conditions
                        conditions: list[str] = []
                        for entity in result.get("entities", []):
                            if entity.get("label") == "DISEASE":
                                condition_text = entity.get("text", "").strip()
                                if condition_text and len(condition_text) > 2:  # Filter very short terms
                                    conditions.append(condition_text)

                        return list(set(conditions))  # Remove duplicates
                    logger.warning(f"SciSpacy service returned status {response.status}")
                    return []

        except Exception as e:
            logger.warning(f"SciSpacy condition extraction failed: {e}")
            return []

    # _rank_sources_by_evidence removed in favor of centralized utilities in core.medical.search_utils

    def _calculate_search_confidence(self, sources: list[dict[str, Any]], query: str) -> float:
        """
        Calculate how confident we are that we found good information (not diagnostic confidence)
        """
        if not sources:
            return 0.0

        # Get configurable confidence parameters
        min_sources = search_config.confidence_parameters.get("min_sources_for_high_confidence", 15)
        min_high_quality = search_config.confidence_parameters.get("min_high_quality_sources", 5)

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
            sp = getattr(search_config, "search_parameters", None)
            timeouts_map = getattr(sp, "timeouts", {}) if sp else {}
            if not isinstance(timeouts_map, dict):
                timeouts_map = {}
            scispacy_timeout = int(timeouts_map.get("scispacy_request", 15))

            # Call SciSpacy service for biomedical entity extraction
            import aiohttp
            async with aiohttp.ClientSession() as session:
                # Request enrichment so we can prioritize certain biomedical categories if metadata available
                async with session.post(
                    "http://172.20.0.6:8001/analyze?enrich=true",  # SciSpacy service
                    json={"text": search_query},
                    timeout=aiohttp.ClientTimeout(total=scispacy_timeout),
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
                            "ORGANISM_SUBSTANCE", "PATHOLOGICAL_FORMATION", "SIMPLE_CHEMICAL", "TISSUE",
                        }
                        medical_entities: list[str] = []
                        enriched_mode = result.get("enriched")
                        for entity in result.get("entities", []):
                            label = entity.get("label") or entity.get("type")
                            text_val = entity.get("text", "")
                            if not text_val:
                                continue
                            if label in medical_entity_types:
                                # If enriched, optionally weight high-priority categories first
                                if enriched_mode and entity.get("priority") == "high":
                                    # Insert at front to ensure ordering preference
                                    medical_entities.insert(0, text_val)
                                else:
                                    medical_entities.append(text_val)

                        logger.info(
                            f"SciSpacy extracted {len(medical_entities)} medical entities (enriched={enriched_mode}): {medical_entities}",
                        )

                        # Use LLM to understand query intent and craft search terms
                        llm_search_terms = await self._llm_craft_search_terms(search_query, medical_entities)

                        # Combine both approaches
                        all_concepts = medical_entities + llm_search_terms
                        unique_concepts = list(dict.fromkeys(all_concepts))  # Preserve order, remove duplicates

                        logger.info(f"Combined medical concepts: {unique_concepts}")
                        return unique_concepts
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
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract search terms from LLM response
            llm_terms: list[str] = []
            if response and "message" in response and "content" in response["message"]:
                content = response["message"]["content"].strip()
                # Split by lines and apply stricter heuristics
                lines = [ln.strip() for ln in content.split("\n") if ln.strip()]
                bullet_re = re.compile(r"^\s*(?:\d+\.|[-*])\s*")
                daterange_re = re.compile(r"\b(?:19|20)\d{2}\s*[-–]\s*(?:19|20)\d{2}\b|last\s+\d+\s+years", re.I)
                bracket_filter_re = re.compile(r"\[(?:title|ti|abstract|ab|mesh|mh):[^\]]+\]", re.I)
                noise_prefixes = ("The ", "Here ", "Consider ", "- ")
                candidates: list[str] = []
                for raw in lines:
                    term = bullet_re.sub("", raw)
                    term = bracket_filter_re.sub("", term)
                    term = term.strip('"\' ”“').strip()
                    if not term or len(term) > 80:
                        continue
                    if term.startswith(noise_prefixes):
                        continue
                    if daterange_re.search(term):
                        continue
                    if not re.search(r"[A-Za-z]", term):
                        continue
                    if ":" in term and not re.search(r"\b(therapy|treatment|syndrome|disease|trial|review|guideline)\b", term, re.I):
                        continue
                    candidates.append(term)
                # Deduplicate while preserving order
                seen: set[str] = set()
                for t in candidates:
                    tl = t.lower()
                    if tl in seen:
                        continue
                    seen.add(tl)
                    llm_terms.append(t)

            logger.info(f"LLM crafted search terms: {llm_terms}")
            return llm_terms[:5]  # Limit to 5 terms

        except Exception as e:
            logger.warning(f"LLM search term crafting failed: {e}")
            # Fallback to simple keyword extraction
            keywords = [word for word in original_query.split()
                        if len(word) > 3 and word.lower() not in ["help", "find", "articles", "recent"]]
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

    def _generate_search_id(self, query: str) -> str:
        """Generate unique search ID"""
        return hashlib.md5(f"{query}{datetime.now(UTC)}".encode()).hexdigest()[:12]
