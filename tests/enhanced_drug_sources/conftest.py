"""
Enhanced Drug Sources Test Configuration

Pytest configuration for enhanced drug sources integration tests.
Provides fixtures and setup for testing the drug integration pipeline.
"""
import sys
from unittest.mock import MagicMock

import pytest

# Add the source directory to Python path for imports
sys.path.insert(0, "/home/intelluxe/services/user/medical-mirrors/src")

@pytest.fixture(scope="session")
def test_database_url():
    """Database URL for testing enhanced drug sources integration."""
    return "postgresql://intelluxe:secure_password@localhost:5432/intelluxe_public"

@pytest.fixture(scope="session")
def test_data_dir():
    """Test data directory path for enhanced drug sources."""
    return "/app/data/enhanced_drug_data"

@pytest.fixture
def mock_database_session():
    """Mock database session for unit tests."""
    mock_session = MagicMock()
    mock_session.query.return_value = mock_session
    mock_session.filter.return_value = mock_session
    mock_session.first.return_value = None
    mock_session.commit.return_value = None
    return mock_session

@pytest.fixture
def sample_drug_data():
    """Sample drug data for testing fuzzy matching and parsing."""
    return {
        "source_drugs": [
            "aspirin", "acetaminophen", "ibuprofen",
            "lisinopril hydrochloride", "(S)-warfarin sodium",
        ],
        "database_drugs": [
            "ASPIRIN", "ACETAMINOPHEN", "IBUPROFEN",
            "LISINOPRIL", "WARFARIN",
        ],
        "expected_matches": {
            "aspirin": "ASPIRIN",
            "acetaminophen": "ACETAMINOPHEN",
            "ibuprofen": "IBUPROFEN",
            "lisinopril hydrochloride": "LISINOPRIL",
            "(S)-warfarin sodium": "WARFARIN",
        },
    }

@pytest.fixture
def sample_dailymed_xml():
    """Sample DailyMed XML structure for parser testing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
    <document xmlns="urn:hl7-org:v3">
        <title>ASPIRIN TABLET</title>
        <author>
            <representedOrganization>
                <name>Test Pharma Inc.</name>
            </representedOrganization>
        </author>
        <component>
            <structuredBody>
                <component>
                    <section>
                        <code code="34067-9" displayName="INDICATIONS AND USAGE"/>
                        <text>Used for pain relief and inflammation.</text>
                    </section>
                </component>
            </structuredBody>
        </component>
    </document>"""

@pytest.fixture
def sample_drugcentral_json():
    """Sample DrugCentral JSON data for parser testing."""
    return {
        "mechanism_of_action": [
            {
                "drug_name": "aspirin",
                "mechanism_of_action": "Irreversibly inhibits cyclooxygenase-1 and cyclooxygenase-2",
            },
        ],
    }

@pytest.fixture
def sample_rxclass_json():
    """Sample RxClass JSON data for parser testing."""
    return {
        "classifications": {
            "ATC": {
                "rxclassDrugInfoList": {
                    "rxclassDrugInfo": [
                        {
                            "rxclassMinConceptItem": {
                                "className": "Anti-inflammatory Agents, Non-Steroidal",
                                "classType": "Therapeutic Category",
                            },
                        },
                    ],
                },
            },
        },
    }

# Pytest markers for different test categories
pytest.mark.integration = pytest.mark.integration
pytest.mark.fuzzy_matching = pytest.mark.fuzzy_matching
pytest.mark.parser = pytest.mark.parser
pytest.mark.container = pytest.mark.container
