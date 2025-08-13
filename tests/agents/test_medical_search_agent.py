import sys
from pathlib import Path
import asyncio
import pytest

# Add the healthcare-api service directory to import path
SERVICE_DIR = Path(__file__).resolve().parents[2] / "services" / "user" / "healthcare-api"
sys.path.insert(0, str(SERVICE_DIR))

from agents.medical_search_agent.medical_search_agent import (  # type: ignore
    MedicalLiteratureSearchAssistant,
)


def test_validate_medical_terms_filters_and_dedup():
    # Create instance without running __init__ to avoid external deps
    agent = MedicalLiteratureSearchAssistant.__new__(MedicalLiteratureSearchAssistant)

    terms = [
        "  ",  # empty
        "ab",  # too short
        "123",  # numeric only
        "COVID-19",
        "covid-19",  # duplicate (case-insensitive)
        "Pain",
        "PAIN",  # duplicate
        "x",  # too short
    ]

    result = asyncio.run(agent._validate_medical_terms(terms))
    assert result == ["COVID-19", "Pain"]


def test_extract_literature_conditions_dedup_and_limit():
    # Create instance without running __init__
    agent = MedicalLiteratureSearchAssistant.__new__(MedicalLiteratureSearchAssistant)

    async def stub_extract(text: str):
        # Return duplicates to test dedup behavior
        return ["Hypertension", "hypertension", "Diabetes"]

    # Monkeypatch the internal extractor to avoid network calls
    agent._extract_conditions_from_text = stub_extract  # type: ignore[attr-defined]

    # Build more than 10 sources to also exercise the limiting
    sources = [
        {"title": f"Article {i}", "abstract": "Lorem ipsum", "source_type": "pubmed"}
        for i in range(15)
    ]

    conditions = asyncio.run(agent._extract_literature_conditions(sources))

    # Should deduplicate case-insensitively -> 2 unique conditions
    names = sorted({c["condition_name"].lower() for c in conditions})
    assert names == ["diabetes", "hypertension"]

    # Should not exceed 10 results
    assert len(conditions) <= 10
