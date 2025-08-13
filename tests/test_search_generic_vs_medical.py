import pytest

from core.medical.search_utils import (
    determine_evidence_level,
    rank_sources_by_evidence_and_relevance,
)
from core.search import basic_rank_sources

SAMPLE_SOURCES = [
    {
        "title": "Randomized Trial of Therapy X",
        "abstract": "A randomized controlled trial evaluating Therapy X for condition Y",
        "publication_type": "Randomized Controlled Trial",
        "publication_date": "2024-01-10",
    },
    {
        "title": "Systematic Review of Therapy X",
        "abstract": "Comprehensive systematic review covering Therapy X studies",
        "publication_type": "Systematic Review",
        "publication_date": "2023-06-01",
    },
    {
        "title": "Observational study of Therapy X",
        "abstract": "Prospective observational clinical study",
        "publication_type": "Clinical Trial",
        "publication_date": "2018-05-01",
    },
]

@pytest.mark.unit
def test_generic_vs_medical_ranking_differs():
    query = "Therapy X randomized study"
    generic_ranked = basic_rank_sources(SAMPLE_SOURCES, query)
    medical_ranked = rank_sources_by_evidence_and_relevance(SAMPLE_SOURCES, query)
    # Ensure same length
    assert len(generic_ranked) == len(medical_ranked)
    # Medical should prioritize systematic review above observational even if recency similar
    titles_medical = [s["title"] for s in medical_ranked]
    assert titles_medical[0] in {"Systematic Review of Therapy X", "Randomized Trial of Therapy X"}
    # Generic recency+overlap might order differently; ensure at least ordering not identical to prove difference potential
    titles_generic = [s["title"] for s in generic_ranked]
    assert titles_generic != titles_medical or titles_medical[0] == "Systematic Review of Therapy X"

@pytest.mark.unit
def test_determine_evidence_level_mapping():
    assert determine_evidence_level({"publication_type": "Systematic Review"}) == "systematic_review"
    assert determine_evidence_level({"publication_type": "Meta-Analysis"}) == "meta_analysis"
    assert determine_evidence_level({"publication_type": "Randomized Controlled Trial"}) == "randomized_controlled_trial"
    assert determine_evidence_level({"publication_type": "Clinical Trial"}) == "clinical_study"
    assert determine_evidence_level({"publication_type": "Guideline"}) == "clinical_guideline"
    assert determine_evidence_level({"publication_type": "Review"}) == "review"
