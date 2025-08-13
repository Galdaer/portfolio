import sys
from pathlib import Path

# Add healthcare-api service module to path
SERVICE_DIR = Path(__file__).resolve().parents[2] / "services" / "user" / "healthcare-api"
sys.path.insert(0, str(SERVICE_DIR))

from core.medical import search_utils  # type: ignore


def test_rank_sources_by_evidence_and_relevance_ordering():
    query = "hypertension treatment guideline"
    sources = [
        {
            "title": "Old review on hypertension",
            "publication_type": "Review",
            "publication_date": "2014",
            "abstract": "hypertension overview",
        },
        {
            "title": "Recent RCT about blood pressure",
            "publication_type": "randomized controlled trial",
            "publication_date": "2024",
            "abstract": "hypertension study results",
        },
        {
            "title": "Clinical guideline for hypertension management",
            "publication_type": "clinical guideline",
            "publication_date": "2020",
            "abstract": "hypertension treatment recommendations",
        },
    ]

    ranked = search_utils.rank_sources_by_evidence_and_relevance(sources, query)

    # Expect guideline to be first due to highest evidence weight, then RCT, then review
    titles_in_order = [s["title"] for s in ranked]
    assert titles_in_order[0].lower().startswith("clinical guideline")
    assert titles_in_order[1].lower().startswith("recent rct")
    assert titles_in_order[2].lower().startswith("old review")


def test_calculate_search_confidence_high_quality_and_relevance():
    sources = [
        {"evidence_level": "systematic_review", "relevance_score": 0.9},
        {"evidence_level": "meta_analysis", "relevance_score": 0.7},
        {"evidence_level": "clinical_guideline", "relevance_score": 0.8},
        {"evidence_level": "randomized_controlled_trial", "relevance_score": 0.6},
        {"evidence_level": "review", "relevance_score": 0.5},
        {"evidence_level": "unknown", "relevance_score": 0.2},
        {"evidence_level": "systematic_review", "relevance_score": 0.85},
        {"evidence_level": "meta_analysis", "relevance_score": 0.75},
        {"evidence_level": "clinical_guideline", "relevance_score": 0.65},
        {"evidence_level": "randomized_controlled_trial", "relevance_score": 0.55},
        {"evidence_level": "review", "relevance_score": 0.4},
        {"evidence_level": "unknown", "relevance_score": 0.1},
        {"evidence_level": "systematic_review", "relevance_score": 0.9},
        {"evidence_level": "meta_analysis", "relevance_score": 0.8},
        {"evidence_level": "clinical_guideline", "relevance_score": 0.7},
    ]
    # With 15 sources and multiple high-quality entries, confidence should be reasonably high (< 1.0 cap)
    conf = search_utils.calculate_search_confidence(sources, query="hypertension")
    assert 0.6 <= conf <= 1.0
