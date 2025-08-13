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

from typing import Any, Dict, Iterable, List

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


def determine_evidence_level(article: Dict[str, Any]) -> str:
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


def extract_source_links(sources: Iterable[Dict[str, Any]]) -> list[str]:  # re-export for backwards compatibility
    return generic_extract_source_links(sources)


def rank_sources_by_evidence_and_relevance(
    sources: list[Dict[str, Any]], query: str
) -> list[Dict[str, Any]]:
    """Rank merged source list by evidence, relevance term overlap, recency.

    Implements weighted score similar to agent logic but centralized.
    """
    query_terms = normalize_query_terms(query)
    ranked: list[Dict[str, Any]] = []
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
    sources: list[Dict[str, Any]], query: str, min_sources: int = 15, min_high_quality: int = 5
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
