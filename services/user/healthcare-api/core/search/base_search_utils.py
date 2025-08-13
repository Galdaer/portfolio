"""Generic search utilities (domain-agnostic).

These functions provide foundational scoring and ranking used by specialized
search domains (e.g., medical, financial). Medical-specific evidence weighting
lives in core.medical.search_utils which composes these primitives.

Design goals:
- Pure/stateless for easy reuse & testing
- Minimal assumptions about document schema beyond optional fields

DISCLAIMER: Generic relevance scoring only – does not interpret or validate
content domain correctness.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List

__all__ = [
    "normalize_query_terms",
    "calculate_recency_score",
    "extract_source_links",
    "basic_rank_sources",
]

def normalize_query_terms(query: str) -> set[str]:
    return {t for t in query.lower().split() if t}


def calculate_recency_score(publication_date: str | None) -> float:
    """Recency scoring (generic).
    Recent (<=2y) strongest; moderate decay over 10y horizon.
    Accepts YYYY or full date string starting with YYYY.
    """
    if not publication_date:
        return 0.0
    try:
        year = int(publication_date[:4])
        current_year = datetime.now(timezone.utc).year
        age = current_year - year
        if age <= 2:
            return 1.0
        if age <= 5:
            return 0.5
        if age <= 10:
            return 0.2
        return 0.0
    except Exception:
        return 0.0


def extract_source_links(sources: Iterable[Dict[str, Any]]) -> list[str]:
    urls: list[str] = []
    for s in sources:
        url = s.get("url")
        if url:
            urls.append(str(url))
    seen: set[str] = set()
    ordered: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            ordered.append(u)
    return ordered


def basic_rank_sources(sources: list[Dict[str, Any]], query: str) -> list[Dict[str, Any]]:
    """Generic ranking: recency + simple term overlap.

    Score = recency + (term_overlap_ratio * 2.0)
    """
    terms = normalize_query_terms(query)
    ranked: list[Dict[str, Any]] = []
    for src in sources:
        recency = calculate_recency_score(src.get("publication_date") or src.get("date"))
        blob = " ".join([
            str(src.get("title", "")),
            str(src.get("abstract", "")),
            str(src.get("summary", "")),
        ]).lower()
        hits = sum(1 for t in terms if t in blob)
        overlap = (hits / len(terms)) if terms else 0.0
        score = recency + (overlap * 2.0)
        ranked.append({**src, "generic_score": score, "overlap_score": overlap})
    return sorted(ranked, key=lambda x: x.get("generic_score", 0), reverse=True)
