import sys
from pathlib import Path
from datetime import datetime, UTC

# Add the healthcare-api service directory to import path
SERVICE_DIR = Path(__file__).resolve().parents[2] / "services" / "user" / "healthcare-api"
sys.path.insert(0, str(SERVICE_DIR))

from agents.medical_search_agent.medical_search_agent import (  # type: ignore  # noqa: E402
    MedicalLiteratureSearchAssistant,
    MedicalSearchResult,
)


def build_agent_for_formatting_tests():
    # Create instance without running __init__ to avoid external deps
    agent = MedicalLiteratureSearchAssistant.__new__(MedicalLiteratureSearchAssistant)
    # Minimal intent config needed by formatter
    agent._intent_config = {
        "response_templates": {
            "academic_article_list": {"max_items": 10, "include_abstracts": True}
        }
    }
    return agent


def test_academic_article_list_formats_items_and_disclaimer():
    agent = build_agent_for_formatting_tests()

    info_sources = [
        {
            "source_type": "condition_information",
            "title": "Impact of Exercise on Cardiovascular Health",
            "authors": ["Smith J", "Doe A"],
            "journal": "Journal of Cardiology",
            "publication_date": "2024",
            "pmid": "12345678",
            "doi": "10.1000/j.jc.2024.01.001",
            "url": "https://pubmed.ncbi.nlm.nih.gov/12345678/",
            "abstract": "Regular exercise reduces cardiovascular risk...",
        },
        {
            "source_type": "symptom_literature",
            "title": "Hypertension Management in Adults",
            "authors": "Williams K; Lee P",
            "journal": "Lancet",
            "publication_date": "2023",
            "pmid": "87654321",
            "url": "https://pubmed.ncbi.nlm.nih.gov/87654321/",
            "abstract": "Guideline-based hypertension management...",
        },
    ]

    result = MedicalSearchResult(
        search_id="test123",
        search_query="cardiovascular health",
        information_sources=info_sources,
        related_conditions=[],
        drug_information=[],
        clinical_references=[],
        search_confidence=0.8,
        disclaimers=[
            "This information is for educational purposes only and is not medical advice."
        ],
        source_links=[],
        generated_at=datetime.now(UTC),
    )

    intent_cfg = {"template": "academic_article_list"}
    formatted = agent._format_response_by_intent(
        "information_request", intent_cfg, result, "cardiovascular health"
    )

    # Header
    assert "Academic articles for: cardiovascular health" in formatted
    # First article details
    assert "**1. Impact of Exercise on Cardiovascular Health**" in formatted
    assert "Authors: Smith J, Doe A" in formatted
    assert "Journal: Journal of Cardiology (2024)" in formatted
    assert "PMID: 12345678" in formatted
    # Second article details (authors string passthrough)
    assert "**2. Hypertension Management in Adults**" in formatted
    assert "Authors: Williams K; Lee P" in formatted
    assert "Journal: Lancet (2023)" in formatted
    assert "PMID: 87654321" in formatted
    # Disclaimer appended
    assert (
        "This information is for educational purposes only and is not medical advice." in formatted
    )


def test_academic_article_list_handles_non_dict_formatter(monkeypatch):
    agent = build_agent_for_formatting_tests()

    # Monkeypatch format_source_for_display to return a non-dict object
    SERVICE_DIR = Path(__file__).resolve().parents[2] / "services" / "user" / "healthcare-api"
    sys.path.insert(0, str(SERVICE_DIR))
    import agents.medical_search_agent.medical_search_agent as msa  # type: ignore  # noqa: E402

    class NonDict:
        def __init__(self, url: str = ""):
            self.url = url

    def fake_formatter(src):  # pylint: disable=unused-argument
        return NonDict(url=src.get("url", ""))

    monkeypatch.setattr(msa, "format_source_for_display", fake_formatter)

    result = MedicalSearchResult(
        search_id="x",
        search_query="cv",
        information_sources=[
            {
                "title": "A",
                "authors": ["Z"],
                "journal": "J",
                "publication_date": "2024",
                "pmid": "1",
                "url": "http://x",
            }
        ],
        related_conditions=[],
        drug_information=[],
        clinical_references=[],
        search_confidence=0.5,
        disclaimers=["d"],
        source_links=[],
        generated_at=datetime.now(UTC),
    )

    formatted = agent._format_response_by_intent(
        "information_request", {"template": "academic_article_list"}, result, "cv"
    )

    # Should include the title and PMID even if formatter isn't a dict
    assert "**1. A**" in formatted
    assert "PMID: 1" in formatted
