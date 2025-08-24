"""
Medical Literature Search Assistant
Provides information about medical concepts, not diagnoses
"""

import asyncio
import contextlib
import hashlib
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import yaml

from agents import BaseHealthcareAgent
from config.medical_search_config_loader import MedicalSearchConfigLoader
from core.config.models import get_instruct_model, get_primary_model

if TYPE_CHECKING:
    from core.infrastructure.agent_context import AgentContext

from core.database.medical_db import MedicalDatabaseAccess
from core.enhanced_sessions import EnhancedSessionManager
from core.infrastructure.agent_context import new_agent_context
from core.infrastructure.agent_logging_utils import (
    AgentWorkflowLogger,
    enhanced_agent_method,
    log_agent_cache_event,
    log_agent_query,
)
from core.infrastructure.agent_metrics import AgentMetricsStore
from core.infrastructure.healthcare_cache import CacheSecurityLevel, HealthcareCacheManager
from core.infrastructure.healthcare_logger import get_healthcare_logger
from core.mcp.universal_parser import parse_pubmed_response
from core.medical import search_utils as medical_search_utils
from core.medical.enhanced_query_engine import (
    EnhancedMedicalQueryEngine,
    MedicalQueryResult,
    QueryType,
)
from core.medical.url_utils import (
    format_source_for_display,
    generate_conversational_summary,
    generate_source_url,
)
from core.security.chat_log_manager import ChatLogManager

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

    def __init__(self, mcp_client: object, llm_client: object) -> None:
        super().__init__(
            mcp_client,
            llm_client,
            agent_name="medical_search",
            agent_type="literature_search",
        )
        self.mcp_client = mcp_client
        self.llm_client = llm_client
        self._metrics = AgentMetricsStore(agent_name="medical_search")

        # Initialize cache manager for performance
        self._cache_manager = HealthcareCacheManager()

        # Initialize local medical database access for database-first pattern
        self._medical_db = MedicalDatabaseAccess()

        # Initialize session manager for conversation continuity
        self._session_manager = EnhancedSessionManager()

        # Initialize chat log manager for HIPAA-compliant audit trails
        self._chat_log_manager = ChatLogManager()

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
        with contextlib.suppress(Exception):
            self.disclaimers = medical_search_utils.generate_medical_disclaimers()

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
        self._mcp_sem = asyncio.Semaphore(max(1, int(max_concurrent)))

        # Load intent configuration (YAML) once
        self._intent_config: dict[str, Any] = {}
        try:
            self._intent_config = self._load_intent_config()
            logger.info("Loaded medical_query_patterns.yaml for intent classification")
        except Exception as e:
            logger.warning(f"Failed to load intent config: {e}")

        # Initialize Enhanced Medical Query Engine for Phase 2 capabilities
        self._enhanced_query_engine = EnhancedMedicalQueryEngine(mcp_client, llm_client)
        logger.info("Enhanced Medical Query Engine initialized for sophisticated medical search")

    async def _check_safety_boundaries(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Override safety boundaries for medical search agent.

        Medical search agents are designed to search for treatment information,
        drug information, and medical literature - this is their purpose.
        We only block truly unsafe requests (personal medical advice).
        """
        logger.info(
            f"🔒 MEDICAL SEARCH AGENT OVERRIDE: safety check called with: {str(request)[:100]}",
        )

        request_text = str(request).lower()

        # Only block direct personal medical advice requests
        unsafe_patterns = [
            "diagnose me",
            "am i sick",
            "is this cancer",
            "what should i do about my",
            "should i take",
            "can i stop taking",
            "is my medication",
        ]

        for pattern in unsafe_patterns:
            if pattern in request_text:
                logger.info(f"🚫 MEDICAL SEARCH AGENT OVERRIDE: blocking unsafe pattern: {pattern}")
                return {
                    "safe": False,
                    "message": "I cannot provide personal medical advice. Please consult a healthcare professional for personal health concerns. I can search for general medical information and research.",
                }

        # Allow all literature searches, including treatment and medication information
        logger.info("✅ MEDICAL SEARCH AGENT OVERRIDE: allowing medical literature search")
        return {"safe": True}

    async def _process_implementation(self, request: Mapping[str, Any]) -> dict[str, Any]:
        """
        Required implementation for BaseHealthcareAgent
        Processes search requests through the standard agent interface
        """
        logger.info(f"Medical search agent processing request: {request}")
        user_id_val = request.get("user_id")
        ctx: AgentContext = new_agent_context(
            "medical_search",
            user_id=str(user_id_val) if isinstance(user_id_val, str | int) else None,
        )

        # Record metrics (non-blocking)
        try:
            await self._metrics.incr("requests_total")
        except Exception as metrics_error:
            logger.warning(f"Failed to record metrics: {metrics_error}")

        sq1 = request.get("search_query")
        sq2 = request.get("query")
        search_query = (
            str(sq1)
            if isinstance(sq1, str | int)
            else (str(sq2) if isinstance(sq2, str | int) else "")
        )
        sc_val = request.get("search_context")
        search_context: dict[str, Any] = sc_val if isinstance(sc_val, dict) else {}

        logger.info(f"Extracted search query: '{search_query}', context: {search_context}")

        if not search_query:
            logger.warning("No search query provided in request")

            # Record metrics (non-blocking)
            try:
                await self._metrics.incr("requests_error_missing_query")
            except Exception as metrics_error:
                logger.warning(f"Failed to record error metrics: {metrics_error}")

            return {
                "success": False,
                "error": "Missing search query",
                "agent_type": "medical_search",
            }

        try:
            # Perform the literature search (intent-aware)
            logger.info(f"Starting medical literature search for: '{search_query}'")

            # Classify query intent using YAML patterns
            intent_key, intent_cfg = self._classify_query_intent(search_query)
            logger.info(f"Classified query intent as '{intent_key}'")

            merged_ctx: dict[str, Any] = {}
            merged_ctx.update(search_context)
            merged_ctx["intent"] = intent_key
            merged_ctx["intent_cfg"] = intent_cfg
            search_result = await self.search_medical_literature(
                search_query=search_query,
                search_context=merged_ctx,
            )
            logger.info(
                f"Medical search completed successfully, found {len(search_result.information_sources)} sources",
            )

            # Record metrics (non-blocking)
            try:
                await self._metrics.incr("requests_success")
                await self._metrics.record_timing("request_ms", ctx.elapsed_ms)
            except Exception as metrics_error:
                logger.warning(f"Failed to record metrics: {metrics_error}")

            # Intent-specific response formatting with fallback
            logger.info("DIAGNOSTIC: Starting response formatting...")
            try:
                formatted_summary = self._format_response_by_intent(
                    intent_key=intent_key,
                    intent_cfg=intent_cfg,
                    search_result=search_result,
                    original_query=search_query,
                )
                logger.info(
                    f"📄 Formatted summary length: {len(formatted_summary)}, contains DOI: {'doi.org' in formatted_summary.lower()}",
                )
                logger.info(f"📄 Formatted summary preview: {formatted_summary[:200]}...")
                logger.info("DIAGNOSTIC: Response formatting completed successfully")
            except Exception as format_error:
                logger.error(
                    f"DIAGNOSTIC: Response formatting failed: {format_error}",
                    exc_info=True,
                )
                # Fallback to basic summary
                formatted_summary = f"Found {len(search_result.information_sources)} medical literature sources for '{search_query}'"

            logger.info(
                f"DIAGNOSTIC: formatted_summary length: {len(formatted_summary) if formatted_summary else 0}",
            )
            logger.info(
                f"DIAGNOSTIC: formatted_summary preview: {formatted_summary[:200] if formatted_summary else 'EMPTY'}",
            )
            logger.info(
                f"DIAGNOSTIC: intent_key: {intent_key}, template: {intent_cfg.get('template', 'NOT_SET') if intent_cfg else 'NO_CFG'}",
            )

            response_dict = {
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
                "intent": intent_key,
                "formatted_summary": formatted_summary,
            }

            logger.info(f"DIAGNOSTIC: Final response keys: {list(response_dict.keys())}")
            logger.info(
                f"DIAGNOSTIC: Response success: {response_dict['success']}, total_sources: {response_dict['total_sources']}",
            )

            return response_dict

        except Exception as e:
            logger.exception(f"Search processing error: {e}")

            # Record metrics (non-blocking)
            try:
                await self._metrics.incr("requests_exception")
            except Exception as metrics_error:
                logger.warning(f"Failed to record exception metrics: {metrics_error}")

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

    @enhanced_agent_method(operation_type="medical_literature_search", phi_risk_level="medium", track_performance=True)
    async def search_medical_literature(
        self,
        search_query: str,
        search_context: dict[str, Any] | None = None,
    ) -> MedicalSearchResult:
        """
        Search medical literature like a medical librarian would
        Returns information about conditions, not diagnoses
        """
        # Generate query hash for tracking
        query_hash = log_agent_query(self.agent_name, search_query, "literature_search")

        # Initialize workflow logger for medical search
        workflow_logger = self.get_workflow_logger()
        workflow_logger.start_workflow("medical_literature_search", {
            "query_hash": query_hash,
            "query_length": len(search_query),
            "has_context": search_context is not None,
            "context_keys": list(search_context.keys()) if search_context else [],
        })

        logger.info(f"search_medical_literature called with query: '{search_query}' (hash: {query_hash})")

        try:
            workflow_logger.log_step("configure_search_timeout")
            # Get configurable timeout for entire search operation; prefer 'total_search' if present
            sp = getattr(search_config, "search_parameters", None)
            timeouts_cfg = getattr(sp, "timeouts", {}) if sp else {}
            if not isinstance(timeouts_cfg, dict):
                timeouts_cfg = {}
            total_timeout = (
                timeouts_cfg.get("total_search") or timeouts_cfg.get("search_request") or 60
            )

            workflow_logger.log_performance_metric("search_timeout", total_timeout, "seconds")
            workflow_logger.log_step("execute_literature_search", {
                "timeout_seconds": total_timeout,
            })

            # Use asyncio.wait_for for overall timeout protection (module-level import)
            result = await asyncio.wait_for(
                self._perform_literature_search(search_query, search_context, workflow_logger),
                timeout=total_timeout,
            )

            workflow_logger.log_step("search_completed", {
                "result_id": result.search_id if result else None,
                "sources_count": len(result.information_sources) if result else 0,
                "confidence": result.search_confidence if result else 0.0,
            })

            workflow_logger.finish_workflow("completed", {
                "search_id": result.search_id if result else None,
                "sources_count": len(result.information_sources) if result else 0,
                "confidence": result.search_confidence if result else 0.0,
                "query_hash": query_hash,
            })

            return result

        except TimeoutError:
            workflow_logger.finish_workflow("failed", {"error": "timeout", "timeout_seconds": total_timeout})

            logger.exception(
                f"Medical literature search timed out after {total_timeout}s for query: '{search_query[:100]}...'",
            )
            # Return empty result with timeout message
            return MedicalSearchResult(
                search_id=self._generate_search_id(search_query),
                search_query=search_query,
                information_sources=[],
                related_conditions=[],
                drug_information=[],
                clinical_references=[],
                search_confidence=0.0,
                disclaimers=[
                    f"Search request timed out after {total_timeout} seconds. Please try a more specific query.",
                ],
                source_links=[],
                generated_at=datetime.now(UTC),
            )
        except Exception as e:
            workflow_logger.finish_workflow("failed", error=e)

            logger.exception(f"Medical literature search failed: {e}")
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
        self,
        search_query: str,
        search_context: dict[str, Any] | None = None,
        workflow_logger: AgentWorkflowLogger | None = None,
    ) -> MedicalSearchResult:
        """Core literature search logic using Enhanced Medical Query Engine (Phase 2) with caching and database-first pattern"""

        # Check cache first for performance
        if workflow_logger:
            workflow_logger.log_step("check_cache")

        cache_key = f"medical_search:{hashlib.sha256(search_query.encode()).hexdigest()[:16]}"
        try:
            cached_result = await self._cache_manager.get(
                cache_key,
                security_level=CacheSecurityLevel.HEALTHCARE_SENSITIVE,
            )
            if cached_result:
                await self._metrics.incr("cache_hits")
                log_agent_cache_event(self.agent_name, cache_key, hit=True, operation="lookup")
                if workflow_logger:
                    workflow_logger.log_step("cache_hit_found", {"cache_key_hash": cache_key[-8:]})
                logger.info(f"Cache hit for medical search query: '{search_query[:50]}...'")
                return cached_result
        except Exception as e:
            logger.warning(f"Cache lookup failed: {e}")

        await self._metrics.incr("cache_misses")
        log_agent_cache_event(self.agent_name, cache_key, hit=False, operation="lookup")
        if workflow_logger:
            workflow_logger.log_step("cache_miss", {"proceeding_to": "database_search"})

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
                    disclaimers=[
                        "This appears to be a system prompt. Please provide a medical research question instead.",
                    ],
                    source_links=[],
                    generated_at=datetime.now(UTC),
                )

        logger.info(
            f"Processing legitimate medical search query with Enhanced Query Engine: '{search_query}'",
        )

        # PHASE 1: Database-first pattern - check local medical database
        try:
            # Search local PubMed database first for better performance
            local_articles = self._medical_db.search_pubmed_local(search_query, max_results=20)
            if local_articles:
                await self._metrics.incr("local_database_hits")
                logger.info(f"Found {len(local_articles)} articles in local PubMed database")

                # Convert local results to search result format
                search_result = self._convert_local_db_to_search_result(search_query, local_articles)

                # Cache the result for future use
                try:
                    await self._cache_manager.set(
                        cache_key,
                        search_result,
                        security_level=CacheSecurityLevel.HEALTHCARE_SENSITIVE,
                        ttl_seconds=3600,  # 1 hour cache
                        healthcare_context={"search_type": "medical_literature", "data_source": "local_db"},
                    )
                except Exception as e:
                    logger.warning(f"Failed to cache result: {e}")

                return search_result
            await self._metrics.incr("local_database_misses")
            logger.info("No results in local database, proceeding with Enhanced Query Engine")

        except Exception as e:
            logger.warning(f"Local database search failed: {e}, proceeding with Enhanced Query Engine")
            await self._metrics.incr("local_database_errors")

        # PHASE 2: Use Enhanced Medical Query Engine for 25x more sophisticated search
        try:
            # Classify intent and map to QueryType
            intent_key, intent_cfg = self._classify_query_intent(search_query)
            query_type = self._map_intent_to_query_type(intent_key)

            logger.info(f"Using Enhanced Query Engine with QueryType: {query_type}")

            # Use Enhanced Medical Query Engine for sophisticated medical search
            enhanced_result = await self._enhanced_query_engine.process_medical_query(
                query=search_query,
                query_type=query_type,
                context=search_context,
                max_iterations=1,  # Reduce iterations to prevent timeouts
            )

            # Get max_items limit from intent config to optimize processing
            max_items = 10  # Default
            if intent_cfg:
                response_templates = self._intent_config.get("response_templates", {})
                if isinstance(response_templates, dict):
                    template_name = intent_cfg.get("template", "academic_article_list")
                    template_config = response_templates.get(template_name, {})
                    if isinstance(template_config, dict):
                        max_items = int(template_config.get("max_items", 10))

            # Convert enhanced result to legacy interface format with performance limit
            search_result = self._convert_enhanced_result_to_search_result(
                enhanced_result, max_items,
            )

            logger.info(
                f"Enhanced search completed - confidence: {enhanced_result.confidence_score:.2f}, "
                f"sources: {len(enhanced_result.sources)}, limited to: {max_items}, entities: {len(enhanced_result.medical_entities)}",
            )

            # Cache the enhanced search result
            try:
                await self._cache_manager.set(
                    cache_key,
                    search_result,
                    security_level=CacheSecurityLevel.HEALTHCARE_SENSITIVE,
                    ttl_seconds=1800,  # 30 minutes cache for MCP results
                    healthcare_context={"search_type": "medical_literature", "data_source": "enhanced_engine"},
                )
            except Exception as e:
                logger.warning(f"Failed to cache enhanced result: {e}")

            return search_result

        except Exception as e:
            logger.exception(f"Enhanced Query Engine failed, falling back to basic search: {e}")
            # Fallback to basic search if enhanced engine fails
            return await self._fallback_basic_search(search_query, search_context)

    async def _fallback_basic_search(
        self,
        search_query: str,
        search_context: dict[str, Any] | None = None,
    ) -> MedicalSearchResult:
        """Fallback to basic search if Enhanced Query Engine fails"""
        search_id = self._generate_search_id(search_query)
        logger.info(f"Using fallback basic search for query: '{search_query}'")

        try:
            # Extract simple medical terms from the original query
            medical_concepts = await self._extract_simple_medical_terms(search_query)
            if not medical_concepts:
                medical_concepts = [search_query]

            # Validate the concepts
            validated_concepts = await self._validate_medical_terms(medical_concepts)

            # Use basic PubMed search only
            condition_info = await self._search_condition_information(validated_concepts)
            symptom_literature = await self._search_symptom_literature(validated_concepts)

            # Combine results
            all_sources = []
            all_sources.extend(condition_info if isinstance(condition_info, list) else [])
            all_sources.extend(symptom_literature if isinstance(symptom_literature, list) else [])

            # Basic deduplication
            seen_keys: set[str] = set()
            deduped_sources: list[dict[str, Any]] = []
            for s in all_sources:
                val = s.get("doi") or s.get("pmid") or s.get("url") or s.get("title") or ""
                key = str(val).strip().lower()
                if not key or key in seen_keys:
                    continue
                seen_keys.add(key)
                deduped_sources.append(s)

            # Calculate basic confidence
            confidence = min(1.0, len(deduped_sources) / 10.0) if deduped_sources else 0.0

            return MedicalSearchResult(
                search_id=search_id,
                search_query=search_query,
                information_sources=deduped_sources,
                related_conditions=[],
                drug_information=[],
                clinical_references=[],
                search_confidence=confidence,
                disclaimers=self.disclaimers,
                source_links=[],
                generated_at=datetime.now(UTC),
            )

        except Exception as e:
            logger.exception(f"Fallback search also failed: {e}")
            return MedicalSearchResult(
                search_id=search_id,
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

    # ------------------------
    # Intent configuration & formatting
    # ------------------------
    def _load_intent_config(self) -> dict[str, Any]:
        """Load YAML-based intent patterns from config directory."""
        # agents/medical_search_agent/ -> up two levels to healthcare-api/, then config/
        base_dir = Path(__file__).resolve().parents[2]  # Up 2 levels to healthcare-api root
        cfg_path = base_dir / "config" / "medical_query_patterns.yaml"
        logger.info(f"DIAGNOSTIC: Looking for intent config at: {cfg_path}")
        if not cfg_path.exists():
            logger.warning(f"DIAGNOSTIC: Intent config file not found at {cfg_path}")
            return {}

        with cfg_path.open("r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f) or {}
            logger.info(
                f"DIAGNOSTIC: Loaded intent config with keys: {list(config_data.keys()) if isinstance(config_data, dict) else 'NOT_DICT'}",
            )
            return config_data

    def _classify_query_intent(self, query: str) -> tuple[str, dict[str, Any]]:
        """Simple keyword-based classifier per YAML patterns with default fallback."""
        patterns = (
            (self._intent_config.get("query_patterns") or {})
            if isinstance(self._intent_config, dict)
            else {}
        )
        if not isinstance(patterns, dict):
            patterns = {}
        ql = (query or "").lower()
        best_key = "information_request"
        best_score = 0
        best_cfg: dict[str, Any] = {}
        for key, cfg in patterns.items():
            kws = cfg.get("keywords", []) if isinstance(cfg, dict) else []
            if not isinstance(kws, list):
                continue
            score = sum(1 for kw in kws if isinstance(kw, str) and kw.lower() in ql)
            if score > best_score:
                best_key = key
                best_score = score
                best_cfg = cfg if isinstance(cfg, dict) else {}
        if not best_cfg:
            best_cfg = (
                patterns.get(best_key, {}) if isinstance(patterns.get(best_key), dict) else {}
            )
        return best_key, best_cfg

    def _map_intent_to_query_type(self, intent_key: str) -> QueryType:
        """Map agent intent classification to Enhanced Query Engine QueryType"""
        intent_to_query_type = {
            "symptom_analysis": QueryType.SYMPTOM_ANALYSIS,
            "drug_information": QueryType.DRUG_INTERACTION,
            "differential_diagnosis": QueryType.DIFFERENTIAL_DIAGNOSIS,
            "clinical_guidelines": QueryType.CLINICAL_GUIDELINES,
            "information_request": QueryType.LITERATURE_RESEARCH,
            "treatment_research": QueryType.CLINICAL_GUIDELINES,
            "drug_interaction": QueryType.DRUG_INTERACTION,
        }
        return intent_to_query_type.get(intent_key, QueryType.LITERATURE_RESEARCH)

    def _convert_enhanced_result_to_search_result(
        self,
        enhanced_result: MedicalQueryResult,
        max_items: int = 10,
    ) -> MedicalSearchResult:
        """Convert Enhanced Query Engine result to Medical Search Agent result format"""
        # Extract different source types from enhanced result
        information_sources = []
        related_conditions: list[dict[str, Any]] = []
        drug_information = []
        clinical_references = []

        # PERFORMANCE OPTIMIZATION: Limit sources early to prevent processing 75+ articles
        # Sort by publication date (most recent first) and limit before processing
        sources_to_process = enhanced_result.sources
        if len(sources_to_process) > max_items * 2:  # Allow some extra for categorization
            # Sort by publication_date if available (most recent first)
            def get_pub_date(source):
                date_str = source.get("publication_date", source.get("date", ""))
                if date_str:
                    # Simple date comparison - assumes YYYY-MM-DD or YYYY format
                    return date_str
                return "0000"  # Put undated articles last

            sources_to_process = sorted(enhanced_result.sources, key=get_pub_date, reverse=True)[
                : max_items * 2
            ]  # Take double the limit to account for categorization

            logger.info(
                f"🚀 PERFORMANCE: Limited processing from {len(enhanced_result.sources)} to {len(sources_to_process)} sources",
            )

        for source in sources_to_process:
            source_type = source.get("source_type", "")
            if source_type in ["condition_information", "symptom_literature"]:
                if len(information_sources) < max_items:  # Stop when we have enough
                    information_sources.append(source)
            elif source_type == "drug_information":
                drug_information.append(source)
            elif source_type == "clinical_references":
                clinical_references.append(source)
            # Default to information sources
            elif len(information_sources) < max_items:  # Stop when we have enough
                information_sources.append(source)

        # Convert enhanced result to legacy format
        return MedicalSearchResult(
            search_id=enhanced_result.query_id,
            search_query=enhanced_result.original_query,
            information_sources=information_sources,
            related_conditions=related_conditions,
            drug_information=drug_information,
            clinical_references=clinical_references,
            search_confidence=enhanced_result.confidence_score,
            disclaimers=enhanced_result.disclaimers,
            source_links=enhanced_result.source_links,
            generated_at=enhanced_result.generated_at,
        )

    def _convert_local_db_to_search_result(
        self,
        search_query: str,
        local_articles: list[dict[str, Any]],
    ) -> MedicalSearchResult:
        """Convert local database articles to MedicalSearchResult format"""

        # Convert local database articles to information_sources format
        information_sources = []
        for article in local_articles[:10]:  # Limit to 10 results
            source = {
                "title": article.get("title", "Untitled"),
                "abstract": article.get("abstract", ""),
                "authors": article.get("authors", []),
                "journal": article.get("journal", ""),
                "publication_date": article.get("pub_date", ""),
                "pmid": article.get("pmid", ""),
                "doi": article.get("doi", ""),
                "mesh_terms": article.get("mesh_terms", []),
                "source_type": "local_database",
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{article.get('pmid', '')}" if article.get("pmid") else "",
            }
            information_sources.append(source)

        # Generate source links
        source_links = [src["url"] for src in information_sources if src.get("url")]

        # Calculate confidence based on number of results and recency
        confidence = min(0.9, len(local_articles) / 20.0 + 0.1)

        return MedicalSearchResult(
            search_id=self._generate_search_id(search_query),
            search_query=search_query,
            information_sources=information_sources,
            related_conditions=[],  # Local DB doesn't provide condition info
            drug_information=[],    # Local DB doesn't provide drug info
            clinical_references=[],  # Local DB doesn't provide clinical refs
            search_confidence=confidence,
            disclaimers=self.disclaimers + [
                "Results from local PubMed database mirror for improved performance.",
                "Local database may not include the most recent publications.",
            ],
            source_links=source_links,
            generated_at=datetime.now(UTC),
        )

    def _format_response_by_intent(
        self,
        intent_key: str,
        intent_cfg: dict[str, Any],
        search_result: "MedicalSearchResult",
        original_query: str,
    ) -> str:
        """Format human-readable response using template from YAML config."""
        template = (intent_cfg or {}).get("template", "conversational_overview")
        logger.info(f"🎨 Using template: {template} for intent: {intent_key}")

        try:
            if template == "academic_article_list":
                # Accept ALL articles from information_sources for academic_article_list
                # Don't filter them out - we already collected them properly
                articles = search_result.information_sources

                # Safe config access with proper defaults
                response_templates = self._intent_config.get("response_templates", {})
                if isinstance(response_templates, dict):
                    article_config = response_templates.get("academic_article_list", {})
                    if isinstance(article_config, dict):
                        max_items = int(article_config.get("max_items", 10))
                        include_abstracts = bool(article_config.get("include_abstracts", True))
                    else:
                        max_items = 10
                        include_abstracts = True
                else:
                    max_items = 10
                    include_abstracts = True

                lines: list[str] = [f"Academic articles for: {original_query}", ""]

                # Helper to safely get fields from formatter output (dict or object)
                def _fmt_get(fmt_obj: Any, key: str, default: str = "") -> str:
                    try:
                        if isinstance(fmt_obj, dict):
                            val = fmt_obj.get(key, default)
                        else:
                            val = getattr(fmt_obj, key, default)
                        return cast("str", val) if val is not None else default
                    except Exception:
                        return default

                for i, src in enumerate(articles[:max_items], 1):
                    title = str(src.get("title", "Untitled")).strip() or "Untitled"

                    # Authors formatting
                    raw_authors = src.get("authors", [])
                    if isinstance(raw_authors, list):
                        authors = ", ".join([str(a) for a in raw_authors[:3]])
                        if len(raw_authors) > 3:
                            authors += " et al."
                    else:
                        authors = str(raw_authors) if raw_authors else ""

                    # Journal and date
                    journal = src.get("journal", "")
                    date = src.get("publication_date", src.get("date", ""))

                    # DOI is PRIMARY - it links to full article
                    doi = src.get("doi", "")

                    # DEBUG: Log what we're getting for DOI and date
                    logger.info(
                        f"FORMATTING DEBUG - Article {i}: title='{title[:50]}...', doi='{doi}', date='{date}', journal='{journal}'",
                    )

                    # Build article entry with clickable title
                    if doi:
                        doi_url = f"https://doi.org/{doi}" if not doi.startswith("http") else doi
                        title_with_link = f"[{title}]({doi_url})"
                    else:
                        title_with_link = title

                    lines.append(f"**{i}. {title_with_link}**")

                    if authors:
                        lines.append(f"   Authors: {authors}")

                    if journal:
                        journal_line = f"   Journal: {journal}"
                        if date:
                            journal_line += f" ({date})"
                        lines.append(journal_line)

                    # Abstract if requested
                    if include_abstracts:
                        abstract = src.get("abstract", src.get("content", ""))
                        if abstract and abstract != "No abstract available":
                            # Show FULL abstract as requested by user - no truncation
                            lines.append(f"   Abstract: {abstract.strip()}")

                    lines.append("")  # Empty line between articles
                lines.append("\n" + "\n".join(search_result.disclaimers))
                return "\n".join(lines)

            if template == "mixed_studies_list":
                pubmed = [
                    s
                    for s in search_result.information_sources
                    if cast("str", s.get("source_type", ""))
                    in ["condition_information", "symptom_literature"]
                ]
                trials = [
                    s
                    for s in search_result.information_sources
                    if "trial" in cast("str", s.get("source_type", ""))
                    or cast("str", s.get("source_type", "")) == "clinical_guideline"
                ]
                rt_cfg = (
                    cast("dict[str, Any]", self._intent_config.get("response_templates", {})).get(
                        "mixed_studies_list",
                        {},
                    )
                    or {}
                )
                max_pubmed_obj = cast("dict[str, Any]", rt_cfg).get("max_pubmed", 6)
                max_trials_obj = cast("dict[str, Any]", rt_cfg).get("max_trials", 4)
                max_pubmed = int(max_pubmed_obj) if isinstance(max_pubmed_obj, int | str) else 6
                max_trials = int(max_trials_obj) if isinstance(max_trials_obj, int | str) else 4
                lines = [f"Studies relevant to: {original_query}", "", "Research Articles:"]
                for i, src in enumerate(pubmed[:max_pubmed], 1):
                    title = src.get("title", "Untitled")
                    doi = src.get("doi", "")
                    pub_date = src.get("publication_date", "")

                    # Make title clickable if DOI exists
                    if doi:
                        doi_url = f"https://doi.org/{doi}" if not doi.startswith("http") else doi
                        title_with_link = f"[{title}]({doi_url})"
                    else:
                        title_with_link = title

                    # Include publication date
                    date_suffix = f" ({pub_date})" if pub_date else ""
                    lines.append(f"{i}. {title_with_link}{date_suffix}")
                lines.append("\nClinical Trials / Guidelines:")
                for i, src in enumerate(trials[:max_trials], 1):
                    fmt = format_source_for_display(src)
                    title = cast("str", src.get("title", "Unnamed study"))
                    status = cast("str", fmt.get("status_display", ""))
                    phase = cast("str", fmt.get("phase_display", ""))
                    meta_line = " ".join([p for p in [status, phase] if p])
                    lines.append(f"- {title}{(' — ' + meta_line) if meta_line else ''}")
                    lines.append(f"  {cast('str', fmt['url'])}")
                lines.append("\n" + "\n".join(search_result.disclaimers))
                return "\n".join(lines)

            if template == "treatment_options_list":
                pubmed = search_result.information_sources
                trials = [
                    s
                    for s in search_result.information_sources
                    if "trial" in cast("str", s.get("source_type", ""))
                    or cast("str", s.get("source_type", "")) == "clinical_guideline"
                ]
                drugs = [
                    s
                    for s in search_result.information_sources
                    if cast("str", s.get("source_type", "")) == "drug_info"
                ]
                rt_cfg = (
                    cast("dict[str, Any]", self._intent_config.get("response_templates", {})).get(
                        "treatment_options_list",
                        {},
                    )
                    or {}
                )
                max_pubmed_obj = cast("dict[str, Any]", rt_cfg).get("max_pubmed", 4)
                max_trials_obj = cast("dict[str, Any]", rt_cfg).get("max_trials", 3)
                max_drugs_obj = cast("dict[str, Any]", rt_cfg).get("max_drugs", 3)
                max_pubmed = int(max_pubmed_obj) if isinstance(max_pubmed_obj, int | str) else 4
                max_trials = int(max_trials_obj) if isinstance(max_trials_obj, int | str) else 3
                max_drugs = int(max_drugs_obj) if isinstance(max_drugs_obj, int | str) else 3
                lines = [
                    f"Treatment-related information for: {original_query}",
                    "",
                    "Evidence from Literature:",
                ]
                for i, src in enumerate(pubmed[:max_pubmed], 1):
                    fmt = format_source_for_display(src)
                    lines.append(
                        f"- {cast('str', src.get('title', 'Untitled'))} — {cast('str', fmt.get('citation', ''))}",
                    )
                    lines.append(f"  {cast('str', fmt['url'])}")
                lines.append("\nRelevant Clinical Trials:")
                for i, src in enumerate(trials[:max_trials], 1):
                    fmt = format_source_for_display(src)
                    lines.append(
                        f"- {cast('str', src.get('title', 'Unnamed study'))} — {cast('str', fmt.get('status_display', ''))} {cast('str', fmt.get('phase_display', ''))}",
                    )
                    lines.append(f"  {cast('str', fmt['url'])}")
                lines.append("\nDrug Information:")
                for i, src in enumerate(drugs[:max_drugs], 1):
                    fmt = format_source_for_display(src)
                    dn = cast("str", src.get("drug_name", src.get("generic_name", "Unknown drug")))
                    lines.append(f"- {dn}")
                    man = cast("str", fmt.get("manufacturer_display", ""))
                    if man:
                        lines.append(f"  {man}")
                    appr = cast("str", fmt.get("approval_display", ""))
                    if appr:
                        lines.append(f"  {appr}")
                    lines.append(f"  {cast('str', fmt['url'])}")
                lines.append("\n" + "\n".join(search_result.disclaimers))
                return "\n".join(lines)

            if template == "clinical_trials_list":
                trials = [
                    s
                    for s in search_result.information_sources
                    if "trial" in cast("str", s.get("source_type", ""))
                    or cast("str", s.get("source_type", "")) == "clinical_guideline"
                ]
                rt_cfg = (
                    cast("dict[str, Any]", self._intent_config.get("response_templates", {})).get(
                        "clinical_trials_list",
                        {},
                    )
                    or {}
                )
                max_trials_obj = cast("dict[str, Any]", rt_cfg).get("max_trials", 10)
                max_trials = int(max_trials_obj) if isinstance(max_trials_obj, int | str) else 10
                lines = [f"Clinical trials for: {original_query}", ""]
                for i, src in enumerate(trials[:max_trials], 1):
                    fmt = format_source_for_display(src)
                    title = cast("str", src.get("title", "Unnamed study"))
                    status = cast("str", fmt.get("status_display", ""))
                    phase = cast("str", fmt.get("phase_display", ""))
                    meta_line = " ".join([p for p in [status, phase] if p])
                    lines.append(f"{i}. {title}{(' — ' + meta_line) if meta_line else ''}")
                    lines.append(f"   {cast('str', fmt['url'])}")
                    lines.append("")
                lines.append("\n" + "\n".join(search_result.disclaimers))
                return "\n".join(lines)

            if template == "drug_information_list":
                drugs = [
                    s
                    for s in search_result.information_sources
                    if cast("str", s.get("source_type", "")) == "drug_info"
                ]
                rt_cfg = (
                    cast("dict[str, Any]", self._intent_config.get("response_templates", {})).get(
                        "drug_information_list",
                        {},
                    )
                    or {}
                )
                max_drugs_obj = cast("dict[str, Any]", rt_cfg).get("max_drugs", 10)
                max_drugs = int(max_drugs_obj) if isinstance(max_drugs_obj, int | str) else 10
                lines = [f"Drug information related to: {original_query}", ""]
                for i, src in enumerate(drugs[:max_drugs], 1):
                    fmt = format_source_for_display(src)
                    dn = cast("str", src.get("drug_name", src.get("generic_name", "Unknown drug")))
                    lines.append(f"{i}. {dn}")
                    man = cast("str", fmt.get("manufacturer_display", ""))
                    if man:
                        lines.append(f"   {man}")
                    appr = cast("str", fmt.get("approval_display", ""))
                    if appr:
                        lines.append(f"   {appr}")
                    lines.append(f"   {cast('str', fmt['url'])}")
                    lines.append("")
                lines.append("\n" + "\n".join(search_result.disclaimers))
                return "\n".join(lines)

            # Default conversational overview using utility (LLM primary handled elsewhere)
            return cast(
                "str",
                generate_conversational_summary(search_result.information_sources, original_query),
            )

        except Exception as e:
            logger.warning(f"Intent formatting failed ({template}): {e}")
            # Fallback to minimal, clean summary without preface
            try:
                return generate_conversational_summary(
                    search_result.information_sources,
                    original_query,
                )
            except Exception:
                # Last resort: extremely simple list
                items = []
                for i, s in enumerate(search_result.information_sources[:8], 1):
                    title = str(s.get("title", "Untitled")).strip()
                    url = str(s.get("url", "")).strip()
                    items.append(f"{i}. {title}{(' — ' + url) if url else ''}")
                return "\n".join(items) if items else "No literature found."

    async def _search_condition_information(
        self,
        medical_concepts: list[str],
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
        query_template = query_templates_map.get(
            "condition_info",
            "{concept} overview pathophysiology symptoms",
        )

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
                            sources.append(
                                {
                                    "source_type": "condition_information",
                                    "title": f"Clinical Case: {concept}",
                                    "content": row.soap_notes[:500] + "..."
                                    if len(row.soap_notes) > 500
                                    else row.soap_notes,
                                    "source": "Healthcare Database",
                                    "evidence_level": "clinical_case",
                                    "relevance_score": 0.8,
                                    "concept": concept,
                                    "url": "#database_case",
                                    "publication_date": "2024",
                                    "study_type": "case_series",
                                },
                            )

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
                    logger.info(
                        f"Starting MCP call to 'search-pubmed' with timeout {mcp_timeout}s for concept '{concept}'...",
                    )
                    # Health check if available
                    if hasattr(self.mcp_client, "_ensure_connected"):
                        try:
                            await asyncio.wait_for(self.mcp_client._ensure_connected(), timeout=5)
                            logger.info("MCP connection established successfully")
                        except Exception as conn_error:
                            logger.exception(f"MCP connection failed pre-call: {conn_error}")
                            # Continue; client has internal retry

                    # Limit concurrency across all MCP calls
                    async with self._mcp_sem:
                        literature_results = await asyncio.wait_for(
                            self.mcp_client.call_tool(
                                "search-pubmed",  # Updated: Use the actual MCP tool name
                                {
                                    "query": search_query,
                                    "maxResults": max_results,  # Updated: Use correct parameter name
                                },
                            ),
                            timeout=mcp_timeout,
                        )
                    # Raw result debugging
                    logger.info(
                        f"Raw MCP result for concept '{concept}': type={type(literature_results).__name__} keys={list(literature_results.keys()) if isinstance(literature_results, dict) else 'n/a'}",
                    )

                    # CRITICAL DEBUG: Log the exact raw response
                    import json

                    logger.error(
                        f"CRITICAL DEBUG - Full MCP response: {json.dumps(literature_results, indent=2)}",
                    )

                    if isinstance(literature_results, dict) and "content" in literature_results:
                        logger.info(
                            f"MCP content field type: {type(literature_results['content']).__name__}",
                        )
                        if literature_results["content"] and isinstance(
                            literature_results["content"][0],
                            dict,
                        ):
                            first_content = literature_results["content"][0]
                            logger.info(f"First content keys: {list(first_content.keys())}")
                            if "text" in first_content:
                                text_preview = (
                                    first_content["text"][:200]
                                    if len(first_content["text"]) > 200
                                    else first_content["text"]
                                )
                                logger.info(f"Text content preview: {text_preview}")

                                # CRITICAL DEBUG: Log the exact text content
                                logger.error(
                                    f"CRITICAL DEBUG - Full text content: {first_content['text']}",
                                )

                    # Parse MCP response using universal parser to fix "Untitled article" issue
                    parsed_articles = parse_pubmed_response(literature_results)
                    logger.info(
                        f"MCP call completed successfully, parsed {len(parsed_articles)} articles for '{concept}'",
                    )

                    for article in parsed_articles:
                        pmid = article.get("pmid", "")
                        doi = article.get("doi", "")
                        sources.append(
                            {
                                "source_type": "condition_information",
                                "title": article.get("title", ""),
                                "content": article.get("abstract", ""),
                                "abstract": article.get("abstract", ""),
                                "source": f"PubMed:{pmid}" if pmid else "PubMed",
                                "evidence_level": article.get("evidence_level")
                                or medical_search_utils.determine_evidence_level(article),
                                "relevance_score": self._calculate_concept_relevance(
                                    concept,
                                    article,
                                ),
                                "concept": concept,
                                "pmid": pmid,  # For PubMed URLs
                                "doi": doi,  # For DOI URLs (preferred)
                                "url": generate_source_url(
                                    {
                                        "source_type": "condition_information",
                                        "pmid": pmid,
                                        "doi": doi,
                                        "source": f"PubMed:{pmid}" if pmid else "PubMed",
                                    },
                                ),
                                "publication_date": article.get("date", ""),
                                "journal": article.get("journal", ""),
                                "authors": article.get("authors", []),
                                "study_type": article.get(
                                    "study_type",
                                    article.get("publication_type", "research_article"),
                                ),
                            },
                        )

                    logger.info(f"MCP search found {len(parsed_articles)} articles for '{concept}'")

                except TimeoutError:
                    logger.warning(
                        f"MCP search timed out after {mcp_timeout}s for concept '{concept}'",
                    )
                    # Continue with other concepts
                except Exception as mcp_error:
                    logger.warning(f"MCP literature search failed for '{concept}': {mcp_error}")
                    # Continue with other concepts

            except Exception as e:
                logger.warning(f"Failed to search condition information for '{concept}': {e}")
                # Continue with other concepts

        logger.info(f"Total condition information sources found: {len(sources)}")
        return sources

    async def _search_symptom_literature(
        self,
        medical_concepts: list[str],
    ) -> list[dict[str, Any]]:
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
        query_template = query_templates_map.get(
            "symptom_literature",
            "{symptom} presentation differential clinical features",
        )

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
                            self.mcp_client.call_tool(
                                "search-pubmed",  # Updated: Use actual MCP tool name
                                {
                                    "query": search_query,
                                    "maxResults": max_results,  # Updated: Use correct parameter name
                                },
                            ),
                            timeout=mcp_timeout,
                        )
                    # Debug raw response and parse using universal parser
                    logger.info(
                        f"Raw MCP result for symptom '{symptom}': type={type(literature_results).__name__} keys={list(literature_results.keys()) if isinstance(literature_results, dict) else 'n/a'}",
                    )
                    parsed_articles = parse_pubmed_response(literature_results)

                    for article in parsed_articles:
                        pmid = article.get("pmid", "")
                        doi = article.get("doi", "")
                        sources.append(
                            {
                                "source_type": "symptom_literature",
                                "symptom": symptom,
                                "title": article.get("title", ""),
                                "journal": article.get("journal", ""),
                                "publication_date": article.get("date", ""),
                                "pmid": pmid,
                                "doi": doi,
                                "url": generate_source_url(
                                    {
                                        "source_type": "symptom_literature",
                                        "pmid": pmid,
                                        "doi": doi,
                                        "source": f"PubMed:{pmid}" if pmid else "PubMed",
                                    },
                                ),
                                "abstract": article.get("abstract", ""),
                                "evidence_level": medical_search_utils.determine_evidence_level(
                                    article,
                                ),
                                "information_type": "symptom_research",
                            },
                        )

                    logger.info(
                        f"MCP search found {len(parsed_articles)} articles for symptom '{symptom}'",
                    )

                except TimeoutError:
                    logger.warning(
                        f"MCP search timed out after {mcp_timeout}s for symptom '{symptom}'",
                    )
                except Exception as mcp_error:
                    logger.warning(
                        f"MCP literature search failed for symptom '{symptom}': {mcp_error}",
                    )

            except Exception as e:
                logger.warning(f"Failed to search symptom literature for '{symptom}': {e}")

        logger.info(f"Total symptom literature sources found: {len(sources)}")
        return sources

    async def _search_drug_information(
        self,
        medical_concepts: list[str],
    ) -> list[dict[str, Any]]:
        """
        Search for drug information and interactions
        Returns: Official drug information, not prescribing advice
        """
        sources = []

        # Get configuration parameters
        url_patterns_map = getattr(search_config, "url_patterns", {}) or {}
        if not isinstance(url_patterns_map, dict):
            url_patterns_map = {}
        fda_url_pattern = url_patterns_map.get(
            "fda_drug",
            "https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm",
        )

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
                            self.mcp_client.call_tool(
                                "get-drug-info",  # Updated: Use actual MCP tool name
                                {
                                    "genericName": drug_concept,  # Updated: Use correct parameter name
                                },
                            ),
                            timeout=mcp_timeout,
                        )

                    logger.info(
                        f"Raw MCP drug result for '{drug_concept}': type={type(drug_results).__name__} keys={list(drug_results.keys()) if isinstance(drug_results, dict) else 'n/a'}",
                    )

                    found_flag = False
                    if isinstance(drug_results, dict):
                        found_flag = bool(drug_results.get("found"))
                    if found_flag:
                        # Use configurable URL pattern if application number available
                        drug_url = (
                            drug_results.get("fda_url", "")
                            if isinstance(drug_results, dict)
                            else ""
                        )
                        if (
                            not drug_url
                            and isinstance(drug_results, dict)
                            and drug_results.get("application_number")
                        ):
                            drug_url = fda_url_pattern.format(
                                application_number=drug_results.get("application_number"),
                            )

                        # Get NDC and other identifiers for URL generation
                        ndc = drug_results.get("ndc", "") if isinstance(drug_results, dict) else ""
                        generic_name = (
                            drug_results.get("generic_name", drug_concept)
                            if isinstance(drug_results, dict)
                            else drug_concept
                        )

                        sources.append(
                            {
                                "source_type": "drug_info",
                                "drug_name": drug_concept,
                                "generic_name": generic_name,
                                "ndc": ndc,
                                "fda_approval": drug_results.get("approval_date", "")
                                if isinstance(drug_results, dict)
                                else "",
                                "approval_date": drug_results.get("approval_date", "")
                                if isinstance(drug_results, dict)
                                else "",
                                "manufacturer": drug_results.get("manufacturer", "")
                                if isinstance(drug_results, dict)
                                else "",
                                "indications": drug_results.get("indications", [])
                                if isinstance(drug_results, dict)
                                else [],
                                "contraindications": drug_results.get("contraindications", [])
                                if isinstance(drug_results, dict)
                                else [],
                                "interactions": drug_results.get("interactions", [])
                                if isinstance(drug_results, dict)
                                else [],
                                "url": generate_source_url(
                                    {
                                        "source_type": "drug_info",
                                        "ndc": ndc,
                                        "drug_name": drug_concept,
                                        "generic_name": generic_name,
                                    },
                                ),
                                "information_type": "regulatory_information",
                                "evidence_level": "regulatory_approval",
                            },
                        )

                    status_txt = (
                        "found"
                        if (isinstance(drug_results, dict) and drug_results.get("found"))
                        else "not found"
                    )
                    logger.info(f"MCP drug search completed for '{drug_concept}': {status_txt}")

                except TimeoutError:
                    logger.warning(
                        f"MCP drug search timed out after {mcp_timeout}s for drug '{drug_concept}'",
                    )
                except Exception as mcp_error:
                    logger.warning(f"MCP drug search failed for '{drug_concept}': {mcp_error}")

            except Exception as e:
                logger.warning(f"Failed to search drug information for '{drug_concept}': {e}")

        logger.info(f"Total drug information sources found: {len(sources)}")
        return sources

    async def _search_clinical_references(
        self,
        medical_concepts: list[str],
    ) -> list[dict[str, Any]]:
        """
        Search clinical practice guidelines and reference materials
        Returns: Reference information for clinical context
        """
        sources = []

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
                            self.mcp_client.call_tool(
                                "search-trials",  # Updated: Use actual MCP tool name
                                {
                                    "condition": concept,
                                },
                            ),
                            timeout=mcp_timeout,
                        )
                    logger.info(
                        f"Raw MCP trials/guidelines result for '{concept}': type={type(guideline_results).__name__} keys={list(guideline_results.keys()) if isinstance(guideline_results, dict) else 'n/a'}",
                    )

                    guidelines = []
                    if isinstance(guideline_results, dict):
                        if isinstance(guideline_results.get("guidelines"), list):
                            guidelines = guideline_results.get("guidelines", [])
                        else:
                            # Fallback: try universal parser then generic parser for records
                            guidelines = parse_pubmed_response(guideline_results)

                    for guideline in guidelines:
                        nct_id = guideline.get("nct_id", guideline.get("nctId", ""))
                        sources.append(
                            {
                                "source_type": "clinical_guideline",
                                "concept": concept,
                                "title": guideline.get("title", ""),
                                "organization": guideline.get("organization", ""),
                                "publication_year": guideline.get(
                                    "year",
                                    guideline.get("date", ""),
                                ),
                                "nct_id": nct_id,
                                "url": generate_source_url(
                                    {"source_type": "clinical_guideline", "nct_id": nct_id},
                                )
                                if nct_id
                                else guideline.get("url", guideline.get("_raw", {}).get("url", "")),
                                "summary": guideline.get("summary", guideline.get("abstract", "")),
                                "evidence_grade": guideline.get(
                                    "evidence_grade",
                                    guideline.get("evidence_level", ""),
                                ),
                                "information_type": "clinical_reference",
                                "evidence_level": "clinical_guideline",
                            },
                        )

                    logger.info(
                        f"MCP trials search found {len(guidelines)} guidelines for '{concept}'",
                    )

                except TimeoutError:
                    logger.warning(
                        f"MCP trials search timed out after {mcp_timeout}s for concept '{concept}'",
                    )
                except Exception as mcp_error:
                    logger.warning(f"MCP trials search failed for '{concept}': {mcp_error}")

            except Exception as e:
                logger.warning(f"Failed to search clinical guidelines for '{concept}': {e}")

        logger.info(f"Total clinical reference sources found: {len(sources)}")
        return sources

    async def _extract_literature_conditions(
        self,
        sources: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
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

            async with aiohttp.ClientSession() as session, session.post(
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
                            if (
                                condition_text and len(condition_text) > 2
                            ):  # Filter very short terms
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

    async def _extract_simple_medical_terms(self, search_query: str) -> list[str]:
        """Extract medical terms by simply cleaning the original query"""
        # Remove common question words and phrases
        question_words = {
            "can",
            "you",
            "help",
            "me",
            "find",
            "search",
            "for",
            "about",
            "on",
            "recent",
            "latest",
            "new",
            "current",
            "show",
            "get",
            "give",
            "provide",
            "articles",
            "studies",
            "research",
            "papers",
            "information",
            "data",
            "trials",
            "medications",
            "medicines",
            "drugs",
            "treatments",
        }

        # Clean the query
        cleaned = search_query.lower()

        # Remove common prefixes
        prefixes_to_remove = [
            "can you help me find recent articles on",
            "can you help me find articles on",
            "help me find recent articles on",
            "find me recent articles on",
            "search for recent articles on",
            "find recent research on",
            "show me recent research on",
            "i need information about",
            "tell me about",
            "what can you tell me about",
        ]

        for prefix in prefixes_to_remove:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix) :].strip()
                break

        # Remove question marks and extra punctuation
        cleaned = cleaned.replace("?", "").replace(".", "").strip()

        # Split into words and filter out question words
        words = [word.strip() for word in cleaned.split() if word.strip()]
        medical_words = [word for word in words if word.lower() not in question_words]

        # Join back into phrases and also include individual important terms
        search_terms = []

        # Always include the cleaned original query if it's meaningful
        if len(" ".join(medical_words)) > 3:
            search_terms.append(" ".join(medical_words))

        # Include individual medical terms that are meaningful
        for word in medical_words:
            if len(word) > 3 and word not in search_terms:
                search_terms.append(word)

        logger.info(f"Simple extraction from '{search_query}' -> {search_terms}")
        return search_terms
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
                            "AMINO_ACID",
                            "ANATOMICAL_SYSTEM",
                            "CANCER",
                            "CELL",
                            "CELLULAR_COMPONENT",
                            "DEVELOPING_ANATOMICAL_STRUCTURE",
                            "GENE_OR_GENE_PRODUCT",
                            "IMMATERIAL_ANATOMICAL_ENTITY",
                            "MULTI-TISSUE_STRUCTURE",
                            "ORGAN",
                            "ORGANISM",
                            "ORGANISM_SUBDIVISION",
                            "ORGANISM_SUBSTANCE",
                            "PATHOLOGICAL_FORMATION",
                            "SIMPLE_CHEMICAL",
                            "TISSUE",
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

                        # Use LLM to understand query intent and craft search terms (as backup)
                        llm_search_terms = await self._llm_craft_search_terms(
                            search_query,
                            medical_entities,
                        )

                        # PRIORITY 1: Extract professional medical terms from original query
                        professional_terms = self._extract_professional_medical_terms(search_query)

                        # PRIORITY 2: Always include the original user query as a search term (cleaned)
                        original_cleaned = (
                            search_query.replace("Find me recent research on", "")
                            .replace("Can you help me find recent articles on", "")
                            .replace("?", "")
                            .strip()
                        )
                        if len(original_cleaned) > 5:  # Only if meaningful
                            original_search_terms = [original_cleaned]
                        else:
                            original_search_terms = []

                        # PRIORITY 3: SciSpacy entities as supplementary terms
                        # PRIORITY 4: LLM terms as fallback (often converts professional to lay terms)

                        # Combine in priority order: professional terms + original query + entities + LLM terms
                        all_concepts = (
                            professional_terms
                            + original_search_terms
                            + medical_entities
                            + llm_search_terms
                        )
                        unique_concepts = list(
                            dict.fromkeys(all_concepts),
                        )  # Preserve order, remove duplicates

                        logger.info(f"Professional medical terms: {professional_terms}")
                        logger.info(f"Combined medical concepts: {unique_concepts}")
                        return unique_concepts
                    logger.warning(f"SciSpacy service returned status {response.status}")
                    msg = f"SciSpacy service error: {response.status}"
                    raise Exception(msg)

        except Exception as e:
            logger.exception(f"SciSpacy entity extraction failed: {e}")
            msg = f"Medical entity extraction failed: {e}"
            raise Exception(msg)

    async def _llm_craft_search_terms(
        self,
        original_query: str,
        medical_entities: list[str],
    ) -> list[str]:
        """Use LLM to understand query intent and craft simple search terms"""
        try:
            # Create a prompt for the LLM to understand the query and suggest SIMPLE search terms
            prompt = f"""Given this medical query: "{original_query}"

Medical entities found: {medical_entities}

Generate 3-5 SIMPLE search terms that would find relevant medical articles.
Use only plain English terms - NO brackets, NO MeSH terms, NO complex syntax.
Use simple terms like "heart disease prevention" not "(Heart Disease[mesh]) AND Prevention".
For multiple concepts, use simple OR combinations like "cardiovascular health OR heart health".

Return only the simple search terms, one per line, no explanations:"""

            # Call local LLM for search term generation
            response = await self.llm_client.chat(
                model=get_primary_model(),
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract search terms from LLM response
            llm_terms: list[str] = []
            if response and "message" in response and "content" in response["message"]:
                content = response["message"]["content"].strip()
                # Split by lines and apply stricter heuristics
                lines = [ln.strip() for ln in content.split("\n") if ln.strip()]
                bullet_re = re.compile(r"^\s*(?:\d+\.|[-*])\s*")
                daterange_re = re.compile(
                    r"\b(?:19|20)\d{2}\s*[-–]\s*(?:19|20)\d{2}\b|last\s+\d+\s+years",
                    re.I,
                )
                bracket_filter_re = re.compile(r"\[(?:title|ti|abstract|ab|mesh|mh):[^\]]+\]", re.I)
                noise_prefixes = ("The ", "Here ", "Consider ", "- ")
                candidates: list[str] = []
                for raw in lines:
                    term = bullet_re.sub("", raw)
                    term = bracket_filter_re.sub("", term)
                    term = term.strip("\"' ”“").strip()
                    if not term or len(term) > 80:
                        continue
                    if term.startswith(noise_prefixes):
                        continue
                    if daterange_re.search(term):
                        continue
                    if not re.search(r"[A-Za-z]", term):
                        continue
                    if ":" in term and not re.search(
                        r"\b(therapy|treatment|syndrome|disease|trial|review|guideline)\b",
                        term,
                        re.I,
                    ):
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
            keywords = [
                word
                for word in original_query.split()
                if len(word) > 3 and word.lower() not in ["help", "find", "articles", "recent"]
            ]
            return keywords[:3]

    def _extract_professional_medical_terms(self, query: str) -> list[str]:
        """Extract professional medical terminology from the query text"""
        # Professional medical terms that should be preserved exactly as written
        professional_medical_terms = [
            "cardiovascular",
            "cardiology",
            "cardiothoracic",
            "cardiac",
            "myocardial",
            "hypertension",
            "hypotension",
            "atherosclerosis",
            "thrombosis",
            "embolism",
            "diabetes",
            "diabetic",
            "endocrine",
            "metabolic",
            "obesity",
            "hyperlipidemia",
            "oncology",
            "neoplasm",
            "carcinoma",
            "malignancy",
            "chemotherapy",
            "radiotherapy",
            "neurology",
            "neurological",
            "alzheimer",
            "parkinson",
            "dementia",
            "stroke",
            "pulmonary",
            "respiratory",
            "pneumonia",
            "asthma",
            "copd",
            "bronchitis",
            "gastroenterology",
            "hepatology",
            "nephrology",
            "renal",
            "dialysis",
            "orthopedic",
            "musculoskeletal",
            "rheumatoid",
            "arthritis",
            "osteoporosis",
            "dermatology",
            "immunology",
            "infectious",
            "antimicrobial",
            "antibiotic",
            "pharmaceutical",
            "pharmacology",
            "clinical trial",
            "randomized",
            "systematic review",
            "meta-analysis",
            "epidemiology",
            "biomarker",
            "pathology",
            "diagnosis",
            "prognosis",
            "prevention",
            "treatment",
            "therapy",
            "intervention",
            "rehabilitation",
        ]

        # Extract terms that appear in the query
        query_lower = query.lower()
        found_terms = []

        # Look for professional terms
        for term in professional_medical_terms:
            if term in query_lower:
                # Extract the term with its original context (preserve case and surrounding words)
                import re

                pattern = rf"\b\w*{re.escape(term)}\w*\b"
                matches = re.findall(pattern, query, re.IGNORECASE)
                found_terms.extend(matches)

        # Also look for compound medical phrases
        medical_phrases = [
            "cardiovascular health",
            "heart disease",
            "disease prevention",
            "risk factors",
            "blood pressure",
            "clinical trial",
            "systematic review",
            "meta analysis",
            "randomized controlled",
            "evidence based",
            "peer reviewed",
        ]

        for phrase in medical_phrases:
            if phrase in query_lower:
                # Find the exact phrase with original capitalization
                import re

                pattern = rf"\b{re.escape(phrase)}\b"
                match = re.search(pattern, query, re.IGNORECASE)
                if match:
                    found_terms.append(match.group())

        # Remove duplicates while preserving order
        unique_terms = list(dict.fromkeys(found_terms))
        logger.info(f"Professional medical terms extracted: {unique_terms}")
        return unique_terms

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

    async def generate_conversational_response(
        self,
        search_result: MedicalSearchResult,
        original_query: str,
    ) -> str:
        """
        Generate a conversational response from search results using LLM.

        Transforms technical search results into human-readable format with
        inline citations and natural language explanations.
        """
        try:
            # Prepare content from all source types with proper links
            pubmed_articles = []
            clinical_trials = []
            drug_info = []
            other_sources = []

            for source in search_result.information_sources[:15]:  # Limit to 15 most relevant
                source_type = source.get("source_type", "unknown")

                if source_type in ["condition_information", "symptom_literature"] and source.get(
                    "pmid",
                ):
                    # PubMed articles with proper links (prefer DOI when available)
                    pmid = source.get("pmid", "")
                    fmt = format_source_for_display(source)
                    url = fmt.get("url", source.get("url", ""))

                    pubmed_articles.append(
                        {
                            "title": source.get("title", "Unknown"),
                            "authors": source.get("authors", [])
                            if isinstance(source.get("authors"), list)
                            else [source.get("authors", "Unknown")],
                            "journal": source.get("journal", "Unknown"),
                            "date": source.get("publication_date", "Unknown"),
                            "abstract": source.get(
                                "content",
                                source.get("abstract", "No summary available"),
                            )[:300],
                            "pmid": pmid,
                            "url": url,
                        },
                    )

                elif source_type == "clinical_guideline":
                    # Clinical trials/guidelines
                    clinical_trials.append(
                        {
                            "title": source.get("title", "Unknown"),
                            "organization": source.get("organization", "Unknown"),
                            "year": source.get("publication_year", "Unknown"),
                            "summary": source.get("summary", "No summary available")[:300],
                            "url": source.get("url", ""),
                            "evidence_grade": source.get("evidence_grade", "Unknown"),
                        },
                    )

                elif source_type == "drug_info":
                    # Drug information
                    drug_info.append(
                        {
                            "drug_name": source.get("drug_name", "Unknown"),
                            "manufacturer": source.get("manufacturer", "Unknown"),
                            "approval_date": source.get("fda_approval", "Unknown"),
                            "indications": source.get("indications", []),
                            "url": source.get("url", ""),
                            "interactions": source.get("interactions", []),
                        },
                    )

                else:
                    # Other sources (database, etc.)
                    other_sources.append(
                        {
                            "title": source.get("title", "Unknown"),
                            "content": source.get("content", "No content available")[:200],
                            "source": source.get("source", "Unknown"),
                            "url": source.get("url", ""),
                        },
                    )

            # Prepare related conditions string for the prompt
            rc_names: list[str] = []
            for rc in search_result.related_conditions[:5]:
                if isinstance(rc, dict):
                    name = rc.get("condition_name") or rc.get("name") or rc.get("condition") or ""
                    if name:
                        rc_names.append(str(name))
                elif isinstance(rc, str):
                    rc_names.append(rc)
            related_conditions_display = ", ".join(rc_names) if rc_names else "None identified"

            # Create comprehensive LLM prompt for all source types
            conversation_prompt = (
                f"""
You are a medical research assistant helping someone understand research on: "{original_query}"

I found information from multiple medical sources. Please create a conversational, informative response that:

1. Provides a clear overview of what the research shows
2. Highlights key findings from the most relevant studies
3. Uses natural language that's accessible but scientifically accurate
4. Includes inline citations with clickable links: "According to [Smith et al. (2024)](https://pubmed.ncbi.nlm.nih.gov/12345678/)"
5. Organizes information by source type (research articles, clinical guidelines, drug information)
6. Ends with the medical disclaimer

RESEARCH ARTICLES ({len(pubmed_articles)} found):
"""
                + "\n".join(
                    [
                        f"- **{article['title']}** by {', '.join(article['authors'][:3])} et al. in {article['journal']} ({article['date']})\n  Summary: {article['abstract']}...\n  [PubMed: {article['pmid']}]({article['url']})\n"
                        for article in pubmed_articles[:8]
                    ],
                )
                + f"""

CLINICAL GUIDELINES ({len(clinical_trials)} found):
"""
                + (
                    "\n".join(
                        [
                            f"- **{trial['title']}** by {trial['organization']} ({trial['year']})\n  Summary: {trial['summary']}...\n  Evidence Grade: {trial['evidence_grade']}\n  [View Guidelines]({trial['url']})\n"
                            for trial in clinical_trials[:5]
                        ],
                    )
                    if clinical_trials
                    else "None found"
                )
                + f"""

DRUG INFORMATION ({len(drug_info)} found):
"""
                + (
                    "\n".join(
                        [
                            f"- **{drug['drug_name']}** by {drug['manufacturer']} (Approved: {drug['approval_date']})\n  Indications: {', '.join(drug['indications'][:3])}\n  [FDA Information]({drug['url']})\n"
                            for drug in drug_info[:3]
                        ],
                    )
                    if drug_info
                    else "None found"
                )
                + f"""

ADDITIONAL SOURCES ({len(other_sources)} found):
"""
                + (
                    "\n".join(
                        [
                            f"- **{source['title']}** from {source['source']}\n  {source['content']}...\n"
                            for source in other_sources[:3]
                        ],
                    )
                    if other_sources
                    else "None found"
                )
                + f"""

Related conditions mentioned: {related_conditions_display}

Create a helpful, conversational response that synthesizes this research:
"""
            )  # Generate response using local LLM
            if self.llm_client:
                response = await self.llm_client.chat(
                    model=get_instruct_model(),
                    messages=[{"role": "user", "content": conversation_prompt}],
                    options={"temperature": 0.3},  # Lower temperature for more factual responses
                )

                conversational_text = response.get("message", {}).get("content", "")

                # Add medical disclaimer if not already included
                if "medical disclaimer" not in conversational_text.lower():
                    conversational_text += "\n\n**Medical Disclaimer**: This information is for educational purposes only and is not medical advice. Always consult your healthcare provider for questions about a medical condition."

                logger.info(
                    f"Generated conversational response of {len(conversational_text)} characters",
                )
                return conversational_text

            # Fallback if LLM is not available
            return self._create_fallback_response(search_result, original_query)

        except Exception as e:
            logger.exception(f"Failed to generate conversational response: {e}")
            return self._create_fallback_response(search_result, original_query)

    def _create_fallback_response(
        self,
        search_result: MedicalSearchResult,
        original_query: str,
    ) -> str:
        """Create a concise, preface-free response when LLM is unavailable."""
        lines: list[str] = []
        for i, source in enumerate(search_result.information_sources[:8], 1):
            try:
                fmt = format_source_for_display(source)
            except Exception:
                fmt = {"url": source.get("url", "")}
            title = str(source.get("title", "Untitled")).strip()
            citation = str(fmt.get("citation", ""))
            url = str(fmt.get("url", source.get("url", "")))
            header = f"{i}. {title}"
            if citation:
                header += f" — {citation}"
            lines.append(header)
            if url:
                lines.append(f"   {url}")
            abstract = str(source.get("abstract", source.get("content", ""))).strip()
            if abstract:
                snippet = abstract if len(abstract) <= 400 else abstract[:400].rstrip() + "..."
                lines.append(f"   {snippet}")
            lines.append("")
        lines.append(
            "**Medical Disclaimer**: This information is for educational purposes only and is not medical advice. Always consult your healthcare provider for questions about a medical condition.",
        )
        return "\n".join(lines).rstrip()
