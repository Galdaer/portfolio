"""
Medical Literature Search Assistant
Provides information about medical concepts, not diagnoses
"""

import asyncio
import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Dict, List, Optional, cast, Awaitable, Mapping, Any

import yaml

from agents import BaseHealthcareAgent
from core.config.models import get_primary_model, get_instruct_model
from config.medical_search_config_loader import MedicalSearchConfigLoader
from core.infrastructure.agent_context import AgentContext, new_agent_context
from core.infrastructure.agent_metrics import AgentMetricsStore
from core.infrastructure.healthcare_logger import get_healthcare_logger
from core.medical import search_utils as medical_search_utils
from core.medical.url_utils import generate_source_url, format_source_for_display, generate_conversational_summary
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
    information_sources: list[dict[str, object]]
    related_conditions: list[dict[str, object]]  # From literature, not diagnosed
    drug_information: list[dict[str, object]]
    clinical_references: list[dict[str, object]]
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

        # Load intent configuration (YAML) once
        self._intent_config: dict[str, object] = {}
        try:
            self._intent_config = self._load_intent_config()
            logger.info("Loaded medical_query_patterns.yaml for intent classification")
        except Exception as e:
            logger.warning(f"Failed to load intent config: {e}")

    async def _process_implementation(self, request: Mapping[str, object]) -> dict[str, object]:
        """
        Required implementation for BaseHealthcareAgent
        Processes search requests through the standard agent interface
        """
        logger.info(f"Medical search agent processing request: {request}")
        user_id_val = request.get("user_id")
        ctx: AgentContext = new_agent_context(
            "medical_search",
            user_id=str(user_id_val) if isinstance(user_id_val, (str, int)) else None,
        )
        
        # Record metrics (non-blocking)
        try:
            await self._metrics.incr("requests_total")
        except Exception as metrics_error:
            logger.warning(f"Failed to record metrics: {metrics_error}")

        sq1 = request.get("search_query")
        sq2 = request.get("query")
        search_query = str(sq1) if isinstance(sq1, (str, int)) else (str(sq2) if isinstance(sq2, (str, int)) else "")
        sc_val = request.get("search_context")
        search_context: dict[str, object] = sc_val if isinstance(sc_val, dict) else {}

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

            merged_ctx: dict[str, object] = {}
            merged_ctx.update(search_context)
            merged_ctx["intent"] = intent_key
            merged_ctx["intent_cfg"] = intent_cfg
            search_result = await self.search_medical_literature(
                search_query=search_query,
                search_context=merged_ctx,
            )
            logger.info(
                f"Medical search completed successfully, found {len(search_result.information_sources)} sources"
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
                logger.info("DIAGNOSTIC: Response formatting completed successfully")
            except Exception as format_error:
                logger.error(f"DIAGNOSTIC: Response formatting failed: {format_error}", exc_info=True)
                # Fallback to basic summary
                formatted_summary = f"Found {len(search_result.information_sources)} medical literature sources for '{search_query}'"

            logger.info(f"DIAGNOSTIC: formatted_summary length: {len(formatted_summary) if formatted_summary else 0}")
            logger.info(f"DIAGNOSTIC: formatted_summary preview: {formatted_summary[:200] if formatted_summary else 'EMPTY'}")
            logger.info(f"DIAGNOSTIC: intent_key: {intent_key}, template: {intent_cfg.get('template', 'NOT_SET') if intent_cfg else 'NO_CFG'}")

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
            logger.info(f"DIAGNOSTIC: Response success: {response_dict['success']}, total_sources: {response_dict['total_sources']}")

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

    async def search_medical_literature(
        self,
        search_query: str,
        search_context: dict[str, object] | None = None,
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
        self, search_query: str, search_context: dict[str, object] | None = None,
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

        # Extract simple medical terms from the original query
        logger.info("Extracting medical terms from original query...")
        try:
            medical_concepts = await self._extract_simple_medical_terms(search_query)
            if not medical_concepts:
                medical_concepts = [search_query]
        except Exception:
            medical_concepts = [search_query]
        logger.info(f"Using medical terms: {medical_concepts}")

        # Validate the concepts
        validated_concepts = await self._validate_medical_terms(medical_concepts)
        logger.info(f"Validated medical terms: {validated_concepts}")

        # Intent-aware source selection
        include_sources: list[str] = []
        if search_context and isinstance(search_context, dict):
            icfg = search_context.get("intent_cfg") or {}
            if isinstance(icfg, dict):
                is_val = icfg.get("include_sources", [])
                if isinstance(is_val, list):
                    include_sources = [str(s) for s in is_val if isinstance(s, str)]

        # Default: articles request goes to PubMed only unless user hints trials/drugs
        if not include_sources:
            include_sources = ["pubmed"]

        # Build search tasks based on selected sources (cap parallelism and avoid duplicates)
        search_tasks: list[Awaitable[list[dict[str, object]]]] = []
        if "pubmed" in include_sources:
            search_tasks.append(self._search_condition_information(validated_concepts))
            search_tasks.append(self._search_symptom_literature(validated_concepts))
        else:
            # Placeholders for merging later
            async def _empty() -> list[dict[str, object]]:
                return []
            search_tasks.append(_empty())
            search_tasks.append(_empty())

        if "fda_drugs" in include_sources:
            search_tasks.append(self._search_drug_information(validated_concepts))
        else:
            async def _empty2() -> list[dict[str, object]]:
                return []
            search_tasks.append(_empty2())

        if "clinical_trials" in include_sources:
            search_tasks.append(self._search_clinical_references(validated_concepts))
        else:
            async def _empty3() -> list[dict[str, object]]:
                return []
            search_tasks.append(_empty3())

        # Execute selected tasks; avoid calling unnecessary tools
        search_results = await asyncio.gather(
            *cast(List[Awaitable[list[dict[str, object]]]], search_tasks),
            return_exceptions=True,
        )

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

        # Combine all information sources and dedupe by DOI/PMID/URL
        all_sources: list[dict[str, object]] = []
        all_sources.extend(condition_info)
        all_sources.extend(symptom_literature)
        all_sources.extend(drug_info)
        all_sources.extend(clinical_refs)

        # Deduplicate
        seen_keys: set[str] = set()
        deduped_sources: list[dict[str, object]] = []
        for s in all_sources:
            val = s.get("doi") or s.get("pmid") or s.get("url") or s.get("title") or ""
            key = str(val).strip().lower()
            if not key or key in seen_keys:
                continue
            seen_keys.add(key)
            deduped_sources.append(s)

        # Rank by medical evidence quality and relevance (centralized util)
        ranked_sources = medical_search_utils.rank_sources_by_evidence_and_relevance(deduped_sources, search_query)

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

    # ------------------------
    # Intent configuration & formatting
    # ------------------------
    def _load_intent_config(self) -> dict[str, object]:
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
            logger.info(f"DIAGNOSTIC: Loaded intent config with keys: {list(config_data.keys()) if isinstance(config_data, dict) else 'NOT_DICT'}")
            return config_data

    def _classify_query_intent(self, query: str) -> tuple[str, dict[str, object]]:
        """Simple keyword-based classifier per YAML patterns with default fallback."""
        patterns = (self._intent_config.get("query_patterns") or {}) if isinstance(self._intent_config, dict) else {}
        if not isinstance(patterns, dict):
            patterns = {}
        ql = (query or "").lower()
        best_key = "information_request"
        best_score = 0
        best_cfg: dict[str, object] = {}
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
            best_cfg = patterns.get(best_key, {}) if isinstance(patterns.get(best_key), dict) else {}
        return best_key, best_cfg

    def _format_response_by_intent(
        self,
        intent_key: str,
        intent_cfg: dict[str, object],
        search_result: "MedicalSearchResult",
        original_query: str,
    ) -> str:
        """Format human-readable response using template from YAML config."""
        template = (intent_cfg or {}).get("template", "conversational_overview")

        try:
            if template == "academic_article_list":
                # PubMed-focused structured list
                pubmed = [s for s in search_result.information_sources if s.get("source_type") in ["condition_information", "symptom_literature"]]
                max_items = int((cast(dict[str, object], self._intent_config.get("response_templates", {})).get("academic_article_list", {}) or {}).get("max_items", 10))
                include_abstracts = bool((cast(dict[str, object], self._intent_config.get("response_templates", {})).get("academic_article_list", {}) or {}).get("include_abstracts", True))
                lines: List[str] = [f"Academic articles for: {original_query}", ""]
                for i, src in enumerate(pubmed[:max_items], 1):
                    fmt = format_source_for_display(src)
                    title = cast(str, src.get("title", "Untitled"))
                    lines.append(f"{i}. {title}")
                    cit = cast(str, fmt.get("citation", ""))
                    if cit:
                        lines.append(f"   {cit}")
                    lines.append(f"   {cast(str, fmt['url'])}")
                    if include_abstracts:
                        abstract = cast(str, src.get("abstract", src.get("content", "")))
                        if abstract:
                            lines.append(f"   {abstract[:400]}...")
                    lines.append("")
                lines.append("\n" + "\n".join(search_result.disclaimers))
                return "\n".join(lines)

            if template == "mixed_studies_list":
                pubmed = [s for s in search_result.information_sources if s.get("source_type") in ["condition_information", "symptom_literature"]]
                trials = [s for s in search_result.information_sources if "trial" in s.get("source_type", "") or s.get("source_type") == "clinical_guideline"]
                rt_cfg = cast(dict[str, object], self._intent_config.get("response_templates", {})).get("mixed_studies_list", {}) or {}
                max_pubmed = int(cast(dict[str, object], rt_cfg).get("max_pubmed", 6))
                max_trials = int(cast(dict[str, object], rt_cfg).get("max_trials", 4))
                lines = [f"Studies relevant to: {original_query}", "", "Research Articles:"]
                for i, src in enumerate(pubmed[:max_pubmed], 1):
                    fmt = format_source_for_display(src)
                    lines.append(f"- {cast(str, src.get('title', 'Untitled'))} — {cast(str, fmt.get('citation', ''))}")
                    lines.append(f"  {cast(str, fmt['url'])}")
                lines.append("\nClinical Trials / Guidelines:")
                for i, src in enumerate(trials[:max_trials], 1):
                    fmt = format_source_for_display(src)
                    title = cast(str, src.get("title", "Unnamed study"))
                    status = cast(str, fmt.get("status_display", ""))
                    phase = cast(str, fmt.get("phase_display", ""))
                    meta_line = " ".join([p for p in [status, phase] if p])
                    lines.append(f"- {title}{(' — ' + meta_line) if meta_line else ''}")
                    lines.append(f"  {cast(str, fmt['url'])}")
                lines.append("\n" + "\n".join(search_result.disclaimers))
                return "\n".join(lines)

            if template == "treatment_options_list":
                pubmed = [s for s in search_result.information_sources if s.get("source_type") in ["condition_information", "symptom_literature"]]
                trials = [s for s in search_result.information_sources if "trial" in s.get("source_type", "") or s.get("source_type") == "clinical_guideline"]
                drugs = [s for s in search_result.information_sources if s.get("source_type") == "drug_info"]
                rt_cfg = cast(dict[str, object], self._intent_config.get("response_templates", {})).get("treatment_options_list", {}) or {}
                max_pubmed = int(cast(dict[str, object], rt_cfg).get("max_pubmed", 4))
                max_trials = int(cast(dict[str, object], rt_cfg).get("max_trials", 3))
                max_drugs = int(cast(dict[str, object], rt_cfg).get("max_drugs", 3))
                lines = [f"Treatment-related information for: {original_query}", "", "Evidence from Literature:"]
                for i, src in enumerate(pubmed[:max_pubmed], 1):
                    fmt = format_source_for_display(src)
                    lines.append(f"- {cast(str, src.get('title', 'Untitled'))} — {cast(str, fmt.get('citation', ''))}")
                    lines.append(f"  {cast(str, fmt['url'])}")
                lines.append("\nRelevant Clinical Trials:")
                for i, src in enumerate(trials[:max_trials], 1):
                    fmt = format_source_for_display(src)
                    lines.append(f"- {cast(str, src.get('title', 'Unnamed study'))} — {cast(str, fmt.get('status_display', ''))} {cast(str, fmt.get('phase_display', ''))}")
                    lines.append(f"  {cast(str, fmt['url'])}")
                lines.append("\nDrug Information:")
                for i, src in enumerate(drugs[:max_drugs], 1):
                    fmt = format_source_for_display(src)
                    dn = cast(str, src.get('drug_name', src.get('generic_name', 'Unknown drug')))
                    lines.append(f"- {dn}")
                    man = cast(str, fmt.get('manufacturer_display', ''))
                    if man:
                        lines.append(f"  {man}")
                    appr = cast(str, fmt.get('approval_display', ''))
                    if appr:
                        lines.append(f"  {appr}")
                    lines.append(f"  {cast(str, fmt['url'])}")
                lines.append("\n" + "\n".join(search_result.disclaimers))
                return "\n".join(lines)

            if template == "clinical_trials_list":
                trials = [s for s in search_result.information_sources if "trial" in s.get("source_type", "") or s.get("source_type") == "clinical_guideline"]
                max_trials = int((cast(dict[str, object], self._intent_config.get("response_templates", {})).get("clinical_trials_list", {}) or {}).get("max_trials", 10))
                lines = [f"Clinical trials for: {original_query}", ""]
                for i, src in enumerate(trials[:max_trials], 1):
                    fmt = format_source_for_display(src)
                    title = cast(str, src.get("title", "Unnamed study"))
                    status = cast(str, fmt.get("status_display", ""))
                    phase = cast(str, fmt.get("phase_display", ""))
                    meta_line = " ".join([p for p in [status, phase] if p])
                    lines.append(f"{i}. {title}{(' — ' + meta_line) if meta_line else ''}")
                    lines.append(f"   {cast(str, fmt['url'])}")
                    lines.append("")
                lines.append("\n" + "\n".join(search_result.disclaimers))
                return "\n".join(lines)

            if template == "drug_information_list":
                drugs = [s for s in search_result.information_sources if s.get("source_type") == "drug_info"]
                max_drugs = int((cast(dict[str, object], self._intent_config.get("response_templates", {})).get("drug_information_list", {}) or {}).get("max_drugs", 10))
                lines = [f"Drug information related to: {original_query}", ""]
                for i, src in enumerate(drugs[:max_drugs], 1):
                    fmt = format_source_for_display(src)
                    dn = cast(str, src.get('drug_name', src.get('generic_name', 'Unknown drug')))
                    lines.append(f"{i}. {dn}")
                    man = cast(str, fmt.get('manufacturer_display', ''))
                    if man:
                        lines.append(f"   {man}")
                    appr = cast(str, fmt.get('approval_display', ''))
                    if appr:
                        lines.append(f"   {appr}")
                    lines.append(f"   {cast(str, fmt['url'])}")
                    lines.append("")
                lines.append("\n" + "\n".join(search_result.disclaimers))
                return "\n".join(lines)

            # Default conversational overview using utility (LLM primary handled elsewhere)
            return cast(str, generate_conversational_summary(search_result.information_sources, original_query))

        except Exception as e:
            logger.warning(f"Intent formatting failed ({template}): {e}")
            # Fallback to minimal, clean summary without preface
            try:
                return generate_conversational_summary(search_result.information_sources, original_query)
            except Exception:
                # Last resort: extremely simple list
                items = []
                for i, s in enumerate(search_result.information_sources[:8], 1):
                    title = str(s.get("title", "Untitled")).strip()
                    url = str(s.get("url", "")).strip()
                    items.append(f"{i}. {title}{(' — ' + url) if url else ''}")
                return "\n".join(items) if items else "No literature found."

    async def _search_condition_information(
        self, medical_concepts: list[str],
    ) -> list[dict[str, object]]:
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
                    logger.info(f"Raw MCP result for concept '{concept}': type={type(literature_results).__name__} keys={list(literature_results.keys()) if isinstance(literature_results, dict) else 'n/a'}")
                    
                    # CRITICAL DEBUG: Log the exact raw response
                    import json
                    logger.error(f"CRITICAL DEBUG - Full MCP response: {json.dumps(literature_results, indent=2)}")
                    
                    if isinstance(literature_results, dict) and "content" in literature_results:
                        logger.info(f"MCP content field type: {type(literature_results['content']).__name__}")
                        if literature_results['content'] and isinstance(literature_results['content'][0], dict):
                            first_content = literature_results['content'][0]
                            logger.info(f"First content keys: {list(first_content.keys())}")
                            if 'text' in first_content:
                                text_preview = first_content['text'][:200] if len(first_content['text']) > 200 else first_content['text']
                                logger.info(f"Text content preview: {text_preview}")
                                
                                # CRITICAL DEBUG: Log the exact text content
                                logger.error(f"CRITICAL DEBUG - Full text content: {first_content['text']}")

                    parsed_articles = medical_search_utils.parse_mcp_search_results(literature_results)
                    logger.info(f"MCP call completed successfully, parsed {len(parsed_articles)} articles for '{concept}'")

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
                                "evidence_level": article.get("evidence_level") or medical_search_utils.determine_evidence_level(article),
                                "relevance_score": self._calculate_concept_relevance(concept, article),
                                "concept": concept,
                                "pmid": pmid,  # For PubMed URLs
                                "doi": doi,   # For DOI URLs (preferred)
                                "url": generate_source_url({
                                    "source_type": "condition_information",
                                    "pmid": pmid,
                                    "doi": doi,
                                    "source": f"PubMed:{pmid}" if pmid else "PubMed"
                                }),
                                "publication_date": article.get("date", ""),
                                "journal": article.get("journal", ""),
                                "authors": article.get("authors", []),
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

    async def _search_symptom_literature(self, medical_concepts: list[str]) -> list[dict[str, object]]:
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
                    # Debug raw response and parse
                    logger.info(f"Raw MCP result for symptom '{symptom}': type={type(literature_results).__name__} keys={list(literature_results.keys()) if isinstance(literature_results, dict) else 'n/a'}")
                    parsed_articles = medical_search_utils.parse_mcp_search_results(literature_results)

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
                                "url": generate_source_url({
                                    "source_type": "symptom_literature",
                                    "pmid": pmid,
                                    "doi": doi,
                                    "source": f"PubMed:{pmid}" if pmid else "PubMed"
                                }),
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

    async def _search_drug_information(self, medical_concepts: list[str]) -> list[dict[str, object]]:
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
                            self.mcp_client.call_tool(
                                "get-drug-info",  # Updated: Use actual MCP tool name
                                {
                                    "genericName": drug_concept,  # Updated: Use correct parameter name
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

                        # Get NDC and other identifiers for URL generation
                        ndc = drug_results.get("ndc", "") if isinstance(drug_results, dict) else ""
                        generic_name = drug_results.get("generic_name", drug_concept) if isinstance(drug_results, dict) else drug_concept
                        
                        sources.append(
                            {
                                "source_type": "drug_info",
                                "drug_name": drug_concept,
                                "generic_name": generic_name,
                                "ndc": ndc,
                                "fda_approval": drug_results.get("approval_date", "") if isinstance(drug_results, dict) else "",
                                "approval_date": drug_results.get("approval_date", "") if isinstance(drug_results, dict) else "",
                                "manufacturer": drug_results.get("manufacturer", "") if isinstance(drug_results, dict) else "",
                                "indications": drug_results.get("indications", []) if isinstance(drug_results, dict) else [],
                                "contraindications": drug_results.get("contraindications", []) if isinstance(drug_results, dict) else [],
                                "interactions": drug_results.get("interactions", []) if isinstance(drug_results, dict) else [],
                                "url": generate_source_url({
                                    "source_type": "drug_info",
                                    "ndc": ndc,
                                    "drug_name": drug_concept,
                                    "generic_name": generic_name
                                }),
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
    ) -> list[dict[str, object]]:
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
                    logger.info(f"Raw MCP trials/guidelines result for '{concept}': type={type(guideline_results).__name__} keys={list(guideline_results.keys()) if isinstance(guideline_results, dict) else 'n/a'}")

                    guidelines = []
                    if isinstance(guideline_results, dict):
                        if isinstance(guideline_results.get("guidelines"), list):
                            guidelines = guideline_results.get("guidelines", [])
                        else:
                            # Fallback: try generic parser for records
                            guidelines = medical_search_utils.parse_mcp_search_results(guideline_results)

                    for guideline in guidelines:
                        nct_id = guideline.get("nct_id", guideline.get("nctId", ""))
                        sources.append(
                            {
                                "source_type": "clinical_guideline",
                                "concept": concept,
                                "title": guideline.get("title", ""),
                                "organization": guideline.get("organization", ""),
                                "publication_year": guideline.get("year", guideline.get("date", "")),
                                "nct_id": nct_id,
                                "url": generate_source_url({
                                    "source_type": "clinical_guideline",
                                    "nct_id": nct_id
                                }) if nct_id else guideline.get("url", guideline.get("_raw", {}).get("url", "")),
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

    async def _extract_literature_conditions(self, sources: list[dict[str, object]]) -> list[dict[str, object]]:
        """
        Extract conditions mentioned in literature using SciSpacy (not diagnose them)
        Returns: List of conditions found in literature with context
        """
        conditions: list[dict[str, object]] = []

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
        unique_conditions: dict[str, dict[str, object]] = {}
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

    def _calculate_search_confidence(self, sources: list[dict[str, object]], query: str) -> float:
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
            "can", "you", "help", "me", "find", "search", "for", "about", "on",
            "recent", "latest", "new", "current", "show", "get", "give", "provide",
            "articles", "studies", "research", "papers", "information", "data",
            "trials", "medications", "medicines", "drugs", "treatments"
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
            "what can you tell me about"
        ]
        
        for prefix in prefixes_to_remove:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
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

                        # Use LLM to understand query intent and craft search terms (as backup)
                        llm_search_terms = await self._llm_craft_search_terms(search_query, medical_entities)

                        # PRIORITY 1: Extract professional medical terms from original query
                        professional_terms = self._extract_professional_medical_terms(search_query)
                        
                        # PRIORITY 2: Always include the original user query as a search term (cleaned)
                        original_cleaned = search_query.replace("Find me recent research on", "").replace("Can you help me find recent articles on", "").replace("?", "").strip()
                        if len(original_cleaned) > 5:  # Only if meaningful
                            original_search_terms = [original_cleaned]
                        else:
                            original_search_terms = []

                        # PRIORITY 3: SciSpacy entities as supplementary terms
                        # PRIORITY 4: LLM terms as fallback (often converts professional to lay terms)

                        # Combine in priority order: professional terms + original query + entities + LLM terms
                        all_concepts = professional_terms + original_search_terms + medical_entities + llm_search_terms
                        unique_concepts = list(dict.fromkeys(all_concepts))  # Preserve order, remove duplicates

                        logger.info(f"Professional medical terms: {professional_terms}")
                        logger.info(f"Combined medical concepts: {unique_concepts}")
                        return unique_concepts
                    logger.warning(f"SciSpacy service returned status {response.status}")
                    raise Exception(f"SciSpacy service error: {response.status}")

        except Exception as e:
            logger.error(f"SciSpacy entity extraction failed: {e}")
            raise Exception(f"Medical entity extraction failed: {e}")

    async def _llm_craft_search_terms(self, original_query: str, medical_entities: list[str]) -> list[str]:
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

    def _extract_professional_medical_terms(self, query: str) -> list[str]:
        """Extract professional medical terminology from the query text"""
        # Professional medical terms that should be preserved exactly as written
        professional_medical_terms = [
            "cardiovascular", "cardiology", "cardiothoracic", "cardiac", "myocardial",
            "hypertension", "hypotension", "atherosclerosis", "thrombosis", "embolism",
            "diabetes", "diabetic", "endocrine", "metabolic", "obesity", "hyperlipidemia",
            "oncology", "neoplasm", "carcinoma", "malignancy", "chemotherapy", "radiotherapy",
            "neurology", "neurological", "alzheimer", "parkinson", "dementia", "stroke",
            "pulmonary", "respiratory", "pneumonia", "asthma", "copd", "bronchitis",
            "gastroenterology", "hepatology", "nephrology", "renal", "dialysis",
            "orthopedic", "musculoskeletal", "rheumatoid", "arthritis", "osteoporosis",
            "dermatology", "immunology", "infectious", "antimicrobial", "antibiotic",
            "pharmaceutical", "pharmacology", "clinical trial", "randomized", "systematic review",
            "meta-analysis", "epidemiology", "biomarker", "pathology", "diagnosis", "prognosis",
            "prevention", "treatment", "therapy", "intervention", "rehabilitation"
        ]
        
        # Extract terms that appear in the query
        query_lower = query.lower()
        found_terms = []
        
        # Look for professional terms
        for term in professional_medical_terms:
            if term in query_lower:
                # Extract the term with its original context (preserve case and surrounding words)
                import re
                pattern = rf'\b\w*{re.escape(term)}\w*\b'
                matches = re.findall(pattern, query, re.IGNORECASE)
                found_terms.extend(matches)
        
        # Also look for compound medical phrases
        medical_phrases = [
            "cardiovascular health", "heart disease", "disease prevention", "risk factors",
            "blood pressure", "clinical trial", "systematic review", "meta analysis",
            "randomized controlled", "evidence based", "peer reviewed"
        ]
        
        for phrase in medical_phrases:
            if phrase in query_lower:
                # Find the exact phrase with original capitalization
                import re
                pattern = rf'\b{re.escape(phrase)}\b'
                match = re.search(pattern, query, re.IGNORECASE)
                if match:
                    found_terms.append(match.group())
        
        # Remove duplicates while preserving order
        unique_terms = list(dict.fromkeys(found_terms))
        logger.info(f"Professional medical terms extracted: {unique_terms}")
        return unique_terms

    def _calculate_concept_relevance(self, concept: str, article: dict[str, object]) -> float:
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

    def _determine_evidence_level(self, article: dict[str, object]) -> str:
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
        original_query: str
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
                source_type = source.get('source_type', 'unknown')
                
                if source_type in ['condition_information', 'symptom_literature'] and source.get('pmid'):
                    # PubMed articles with proper links (prefer DOI when available)
                    pmid = source.get('pmid', '')
                    fmt = format_source_for_display(source)
                    url = fmt.get('url', source.get('url', ''))
                    
                    pubmed_articles.append({
                        'title': source.get('title', 'Unknown'),
                        'authors': source.get('authors', []) if isinstance(source.get('authors'), list) else [source.get('authors', 'Unknown')],
                        'journal': source.get('journal', 'Unknown'),
                        'date': source.get('publication_date', 'Unknown'),
                        'abstract': source.get('content', source.get('abstract', 'No summary available'))[:300],
                        'pmid': pmid,
                        'url': url
                    })
                
                elif source_type == 'clinical_guideline':
                    # Clinical trials/guidelines
                    clinical_trials.append({
                        'title': source.get('title', 'Unknown'),
                        'organization': source.get('organization', 'Unknown'),
                        'year': source.get('publication_year', 'Unknown'),
                        'summary': source.get('summary', 'No summary available')[:300],
                        'url': source.get('url', ''),
                        'evidence_grade': source.get('evidence_grade', 'Unknown')
                    })
                
                elif source_type == 'drug_info':
                    # Drug information
                    drug_info.append({
                        'drug_name': source.get('drug_name', 'Unknown'),
                        'manufacturer': source.get('manufacturer', 'Unknown'),
                        'approval_date': source.get('fda_approval', 'Unknown'),
                        'indications': source.get('indications', []),
                        'url': source.get('url', ''),
                        'interactions': source.get('interactions', [])
                    })
                
                else:
                    # Other sources (database, etc.)
                    other_sources.append({
                        'title': source.get('title', 'Unknown'),
                        'content': source.get('content', 'No content available')[:200],
                        'source': source.get('source', 'Unknown'),
                        'url': source.get('url', '')
                    })

            # Prepare related conditions string for the prompt
            rc_names: list[str] = []
            for rc in search_result.related_conditions[:5]:
                if isinstance(rc, dict):
                    name = rc.get('condition_name') or rc.get('name') or rc.get('condition') or ''
                    if name:
                        rc_names.append(str(name))
                elif isinstance(rc, str):
                    rc_names.append(rc)
            related_conditions_display = ", ".join(rc_names) if rc_names else "None identified"

            # Create comprehensive LLM prompt for all source types
            conversation_prompt = f"""
You are a medical research assistant helping someone understand research on: "{original_query}"

I found information from multiple medical sources. Please create a conversational, informative response that:

1. Provides a clear overview of what the research shows
2. Highlights key findings from the most relevant studies
3. Uses natural language that's accessible but scientifically accurate
4. Includes inline citations with clickable links: "According to [Smith et al. (2024)](https://pubmed.ncbi.nlm.nih.gov/12345678/)"
5. Organizes information by source type (research articles, clinical guidelines, drug information)
6. Ends with the medical disclaimer

RESEARCH ARTICLES ({len(pubmed_articles)} found):
""" + "\n".join([
                f"- **{article['title']}** by {', '.join(article['authors'][:3])} et al. in {article['journal']} ({article['date']})\n  Summary: {article['abstract']}...\n  [PubMed: {article['pmid']}]({article['url']})\n"
                for article in pubmed_articles[:8]
            ]) + f"""

CLINICAL GUIDELINES ({len(clinical_trials)} found):
""" + ("\n".join([
                f"- **{trial['title']}** by {trial['organization']} ({trial['year']})\n  Summary: {trial['summary']}...\n  Evidence Grade: {trial['evidence_grade']}\n  [View Guidelines]({trial['url']})\n"
                for trial in clinical_trials[:5]
            ]) if clinical_trials else "None found") + f"""

DRUG INFORMATION ({len(drug_info)} found):
""" + ("\n".join([
                f"- **{drug['drug_name']}** by {drug['manufacturer']} (Approved: {drug['approval_date']})\n  Indications: {', '.join(drug['indications'][:3])}\n  [FDA Information]({drug['url']})\n"
                for drug in drug_info[:3]
            ]) if drug_info else "None found") + f"""

ADDITIONAL SOURCES ({len(other_sources)} found):
""" + ("\n".join([
                f"- **{source['title']}** from {source['source']}\n  {source['content']}...\n"
                for source in other_sources[:3]
            ]) if other_sources else "None found") + f"""

Related conditions mentioned: {related_conditions_display}

Create a helpful, conversational response that synthesizes this research:
"""            # Generate response using local LLM
            if self.llm_client:
                response = await self.llm_client.chat(
                    model=get_instruct_model(),
                    messages=[{
                        "role": "user",
                        "content": conversation_prompt
                    }],
                    options={"temperature": 0.3}  # Lower temperature for more factual responses
                )
                
                conversational_text = response.get('message', {}).get('content', '')
                
                # Add medical disclaimer if not already included
                if "medical disclaimer" not in conversational_text.lower():
                    conversational_text += "\n\n**Medical Disclaimer**: This information is for educational purposes only and is not medical advice. Always consult your healthcare provider for questions about a medical condition."
                
                logger.info(f"Generated conversational response of {len(conversational_text)} characters")
                return conversational_text
            
            else:
                # Fallback if LLM is not available
                return self._create_fallback_response(search_result, original_query)
                
        except Exception as e:
            logger.error(f"Failed to generate conversational response: {e}")
            return self._create_fallback_response(search_result, original_query)

    def _create_fallback_response(self, search_result: MedicalSearchResult, original_query: str) -> str:
        """Create a concise, preface-free response when LLM is unavailable."""
        lines: list[str] = []
        for i, source in enumerate(search_result.information_sources[:8], 1):
            try:
                fmt = format_source_for_display(source)
            except Exception:
                fmt = {"url": source.get("url", "")}
            title = str(source.get('title', 'Untitled')).strip()
            citation = str(fmt.get('citation', ''))
            url = str(fmt.get('url', source.get('url', '')))
            header = f"{i}. {title}"
            if citation:
                header += f" — {citation}"
            lines.append(header)
            if url:
                lines.append(f"   {url}")
            abstract = str(source.get('abstract', source.get('content', ''))).strip()
            if abstract:
                snippet = abstract if len(abstract) <= 400 else abstract[:400].rstrip() + "..."
                lines.append(f"   {snippet}")
            lines.append("")
        lines.append("**Medical Disclaimer**: This information is for educational purposes only and is not medical advice. Always consult your healthcare provider for questions about a medical condition.")
        return "\n".join(lines).rstrip()
