"""Medical-specialized search utilities layered atop generic search primitives.

This module now focuses strictly on *medical domain specificity* (evidence level
inference, medical-enhanced ranking, search confidence) and delegates generic
capabilities (recency scoring, URL extraction, base term normalization) to
``core.search`` to avoid over-generalizing medical concepts into cross-agent code.

Why this split?
----------------
Other agents should consume a *medical search agent* rather than import medical
utilities directly. For non-medical domains (financial, administrative), the
generic utilities are sufficient and domain-specific weighting can replicate this
pattern in their own modules without inheriting medical evidence semantics.

MEDICAL DISCLAIMER: These utilities assist with structuring and ranking medical
literature information only; they do not perform diagnosis or clinical
decision-making. Always defer to qualified healthcare professionals.
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from core.search import (
    calculate_recency_score as generic_recency_score,
    extract_source_links as generic_extract_source_links,
    normalize_query_terms,
)

# Evidence level canonical ordering (higher index = stronger evidence for weighting logic)
_EVIDENCE_PRIORITY = [
    "unknown",
    "review",
    "clinical_study",
    "randomized_controlled_trial",
    "meta_analysis",
    "systematic_review",
    "clinical_guideline",
    "regulatory_approval",
]


def determine_evidence_level(article: dict[str, Any]) -> str:
    """Infer evidence level from publication metadata.

    Combines logic previously duplicated in agents.
    """
    pub_type = (article.get("publication_type") or article.get("study_type") or "").lower()
    title = (article.get("title") or "").lower()
    if "systematic review" in pub_type or "systematic review" in title:
        return "systematic_review"
    if "meta-analysis" in pub_type or "meta-analysis" in title:
        return "meta_analysis"
    if "randomized" in pub_type and "trial" in pub_type:
        return "randomized_controlled_trial"
    if "clinical trial" in pub_type:
        return "clinical_study"
    if "guideline" in pub_type:
        return "clinical_guideline"
    if "review" in pub_type:
        return "review"
    return "unknown"


def extract_source_links(sources: Iterable[dict[str, Any]]) -> list[str]:  # re-export for backwards compatibility
    return generic_extract_source_links(sources)


def rank_sources_by_evidence_and_relevance(
    sources: list[dict[str, Any]], query: str,
) -> list[dict[str, Any]]:
    """Rank merged source list by evidence, relevance term overlap, recency.

    Implements weighted score similar to agent logic but centralized.
    """
    query_terms = normalize_query_terms(query)
    ranked: list[dict[str, Any]] = []
    for src in sources:
        ev = src.get("evidence_level") or determine_evidence_level(src)
        recency = generic_recency_score(src.get("publication_date") or src.get("date"))
        text_blob = " ".join([
            str(src.get("title", "")),
            str(src.get("abstract", "")),
            str(src.get("summary", "")),
        ]).lower()
        rel_hits = sum(1 for t in query_terms if t in text_blob)
        rel_score = (rel_hits / len(query_terms)) if query_terms else 0.0
        try:
            evidence_weight = _EVIDENCE_PRIORITY.index(ev)
        except ValueError:
            evidence_weight = 0
        final_score = evidence_weight + (rel_score * 3.0) + recency
        ranked.append({**src, "evidence_level": ev, "search_score": final_score, "relevance_score": rel_score})
    return sorted(ranked, key=lambda x: x.get("search_score", 0), reverse=True)


def calculate_search_confidence(
    sources: list[dict[str, Any]], query: str, min_sources: int = 15, min_high_quality: int = 5,
) -> float:
    """Compute literature search confidence (not diagnostic).

    High-quality evidence levels counted: systematic/meta/guideline/regulatory.
    """
    if not sources:
        return 0.0
    high_quality = sum(
        1
        for s in sources
        if s.get("evidence_level")
        in {"systematic_review", "meta_analysis", "clinical_guideline", "regulatory_approval"}
    )
    source_count_factor = min(len(sources) / float(min_sources), 1.0)
    quality_factor = min(high_quality / float(min_high_quality), 1.0)
    relevance_scores = [float(s.get("relevance_score", 0)) for s in sources]
    avg_relevance = sum(relevance_scores) / len(relevance_scores) if sources else 0.0
    return min((source_count_factor * 0.3) + (quality_factor * 0.4) + (avg_relevance * 0.3), 1.0)


# ------------------------
# Parsing and formatting
# ------------------------
def parse_mcp_search_results(raw_mcp_result: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse raw MCP tool results into normalized medical literature entries.

    Accepts multiple shapes (articles/items/results/content) and returns a list of
    dicts with common fields: pmid, title, abstract, journal, date, doi, study_type.
    """
    if not isinstance(raw_mcp_result, dict):
        return []

    # Common containers across tools
    containers: list = []
    for key in ("articles", "items", "results", "records", "content"):
        val = raw_mcp_result.get(key)
        if isinstance(val, list):
            containers = val
            break

    normalized: list[dict[str, Any]] = []
    for item in containers:
        if not isinstance(item, dict):
            continue
        pmid = item.get("pmid") or item.get("id") or item.get("pmid_id") or ""
        normalized.append(
            {
                "pmid": str(pmid) if pmid is not None else "",
                "title": item.get("title", ""),
                "abstract": item.get("abstract") or item.get("summary", ""),
                "journal": item.get("journal", ""),
                "date": item.get("publication_date") or item.get("date") or item.get("year", ""),
                "doi": item.get("doi", ""),
                "study_type": item.get("study_type") or item.get("publication_type", ""),
                "publication_type": item.get("publication_type", ""),
                "evidence_level": determine_evidence_level(item),
                # Preserve original in case downstream needs it
                "_raw": item,
            },
        )
    return normalized


def generate_medical_disclaimers(extra_context: str | None = None) -> list[str]:
    """Standard, PHI-safe medical disclaimers with optional context."""
    disclaimers = [
        "This information is for educational purposes only and is not medical advice.",
        "Only a qualified healthcare professional can provide medical diagnosis or treatment.",
        "Always consult your healthcare provider for questions about a medical condition.",
        "If this is an emergency, call your local emergency number immediately.",
    ]
    if extra_context:
        disclaimers.append(extra_context)
    return disclaimers


def format_medical_search_response(
    search_results: list[dict[str, Any]],
    query: str,
    related_conditions: list[dict[str, Any]] | None = None,
    max_items: int = 8,
    disclaimers: list[str] | None = None,
) -> str:
    """Build a concise, human-readable summary of medical literature findings."""
    related_conditions = related_conditions or []
    disclaimers = disclaimers or generate_medical_disclaimers()

    lines: list[str] = []
    lines.append("🏥 Medical Search Summary")
    lines.append("")
    lines.append(f"Query: {query}")
    lines.append("")

    if not search_results:
        lines.append("No literature was retrieved. This may be due to dynamic timeouts or issues with the upstream sources.")
    else:
        lines.append("Key findings:")
        limit = min(len(search_results), max_items)
        for i in range(limit):
            art = search_results[i]
            title = (art.get("title") or "Untitled").strip()
            journal = art.get("journal") or ""
            year = ""
            date_val = art.get("date") or art.get("publication_date")
            if isinstance(date_val, str):
                year = date_val[:4]
            doi = art.get("doi") or ""
            ev = art.get("evidence_level") or determine_evidence_level(art)
            url = art.get("url") or art.get("_raw", {}).get("url") or ""
            bullet = f"• {title}"
            meta_parts = []
            if journal:
                meta_parts.append(journal)
            if year:
                meta_parts.append(year)
            if ev and ev != "unknown":
                meta_parts.append(ev.replace("_", " "))
            if doi:
                meta_parts.append(f"doi:{doi}")
            if meta_parts:
                bullet += f" — {'; '.join(meta_parts)}"
            if url:
                bullet += f" ({url})"
            lines.append(bullet)

    if related_conditions:
        lines.append("")
        lines.append("Related conditions mentioned in literature:")
        # Deduplicate by name
        seen: set[str] = set()
        for rc in related_conditions:
            name = (rc.get("condition_name") or rc.get("name") or "").strip()
            if not name:
                continue
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"• {name}")

    if disclaimers:
        lines.append("")
        lines.append("Important medical disclaimer:")
        for d in disclaimers:
            lines.append(f"• {d}")

    return "\n".join(lines)
