"""
Healthcare Testing Configuration

Pytest configuration and test utilities for healthcare AI system testing.
"""

import asyncio
import logging
from collections.abc import Generator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.infrastructure.authentication import AuthenticatedUser, HealthcareRole
from tests.healthcare_integration_tests import (
    HealthcareIntegrationTestBase,
    HealthcareWorkflowTester,
    MockHealthcareLLM,
    MockHealthcareMCP,
)

# Configure test logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def healthcare_app() -> FastAPI:
    """Create healthcare FastAPI app for testing"""
    from main import app

    # Override with test configuration
    app.state.testing = True

    return app

@pytest.fixture(scope="session")
async def test_client(healthcare_app: FastAPI) -> TestClient:
    """Create test client for healthcare app"""
    return TestClient(healthcare_app)

@pytest.fixture(scope="function")
async def integration_test_base(healthcare_app: FastAPI) -> HealthcareIntegrationTestBase:
    """Create integration test base with mock services"""
    base = HealthcareIntegrationTestBase()
    await base.setup_test_environment(healthcare_app)

    yield base

    await base.teardown_test_environment()

@pytest.fixture(scope="function")
async def workflow_tester(integration_test_base: HealthcareIntegrationTestBase) -> HealthcareWorkflowTester:
    """Create healthcare workflow tester"""
    return HealthcareWorkflowTester(integration_test_base)

@pytest.fixture(scope="function")
def mock_healthcare_mcp() -> MockHealthcareMCP:
    """Create mock healthcare MCP server"""
    return MockHealthcareMCP()

@pytest.fixture(scope="function")
def mock_healthcare_llm() -> MockHealthcareLLM:
    """Create mock healthcare LLM"""
    return MockHealthcareLLM()

@pytest.fixture(scope="function")
def test_doctor() -> AuthenticatedUser:
    """Create test doctor user"""
    return AuthenticatedUser(
        user_id="test_doctor_001",
        role=HealthcareRole.DOCTOR,
        facility_id="test_facility_001",
        department="internal_medicine",
        permissions=["read:patient_data", "write:patient_data", "read:medical_records"]
    )

@pytest.fixture(scope="function")
def test_nurse() -> AuthenticatedUser:
    """Create test nurse user"""
    return AuthenticatedUser(
        user_id="test_nurse_001",
        role=HealthcareRole.NURSE,
        facility_id="test_facility_001",
        department="general_care",
        permissions=["read:patient_data", "write:patient_vitals"]
    )

@pytest.fixture(scope="function")
def test_receptionist() -> AuthenticatedUser:
    """Create test receptionist user"""
    return AuthenticatedUser(
        user_id="test_receptionist_001",
        role=HealthcareRole.RECEPTIONIST,
        facility_id="test_facility_001",
        department="front_desk",
        permissions=["read:patient_demographics", "write:appointments"]
    )

@pytest.fixture(scope="function")
def synthetic_patient_data() -> dict[str, Any]:
    """Create synthetic patient data for testing"""
    return {
        "patient_id": "TEST_PATIENT_001",
        "first_name": "Alice",
        "last_name": "Smith",
        "date_of_birth": "1985-03-22",
        "gender": "F",
        "phone": "555-0100",
        "email": "alice.smith@example.com",
        "address": {
            "street": "456 Healthcare Ave",
            "city": "Medical City",
            "state": "MC",
            "zip_code": "54321"
        },
        "insurance": {
            "provider": "HealthFirst Insurance",
            "policy_number": "HF987654321",
            "group_number": "GRP100"
        },
        "medical_history": [
            {
                "condition": "Hypertension",
                "diagnosed_date": "2020-01-15",
                "status": "active"
            },
            {
                "condition": "Type 2 Diabetes",
                "diagnosed_date": "2018-06-10",
                "status": "managed"
            }
        ]
    }

@pytest.fixture(scope="function")
def synthetic_encounter_data() -> dict[str, Any]:
    """Create synthetic encounter data for testing"""
    from datetime import datetime

    return {
        "encounter_id": "ENC_TEST_001",
        "patient_id": "TEST_PATIENT_001",
        "provider_id": "DR_TEST_001",
        "encounter_date": datetime.now().isoformat(),
        "encounter_type": "routine_checkup",
        "chief_complaint": "Follow-up for diabetes management",
        "vital_signs": {
            "blood_pressure": "135/85",
            "heart_rate": 78,
            "temperature": 98.2,
            "weight": 165,
            "height": 66,
            "bmi": 26.6
        },
        "review_of_systems": {
            "constitutional": "No fever, chills, or night sweats",
            "cardiovascular": "No chest pain or palpitations",
            "endocrine": "Reports compliance with diabetes medications"
        },
        "physical_exam": {
            "general": "Well-appearing adult in no acute distress",
            "cardiovascular": "Regular rate and rhythm, no murmurs",
            "extremities": "No edema noted"
        },
        "assessment_and_plan": {
            "diabetes_type_2": {
                "assessment": "Well-controlled on current regimen",
                "plan": "Continue metformin, recheck HbA1c in 3 months"
            },
            "hypertension": {
                "assessment": "Slightly elevated, may need adjustment",
                "plan": "Increase lisinopril to 15mg daily"
            }
        },
        "prescriptions": [
            {
                "medication": "Metformin",
                "dosage": "1000mg",
                "frequency": "twice daily",
                "duration": "90 days",
                "refills": 2
            },
            {
                "medication": "Lisinopril",
                "dosage": "15mg",
                "frequency": "daily",
                "duration": "90 days",
                "refills": 2
            }
        ]
    }

@pytest.fixture(scope="function")
def test_medical_document() -> str:
    """Create test medical document content"""
    return """
    EMERGENCY DEPARTMENT NOTE

    Date: 2024-08-03 14:30:00
    Patient: Robert Johnson (DOB: 1972-09-15, MRN: MR123456)
    Provider: Dr. Sarah Lee, MD

    CHIEF COMPLAINT:
    "Chest pain for the past 2 hours"

    HISTORY OF PRESENT ILLNESS:
    58-year-old male presents to the ED with acute onset chest pain that started
    approximately 2 hours ago while at rest. Pain is described as crushing,
    substernal, radiating to left arm and jaw. Associated with diaphoresis
    and nausea. No shortness of breath. Patient has history of hypertension
    and hyperlipidemia.

    PAST MEDICAL HISTORY:
    - Hypertension (diagnosed 2015)
    - Hyperlipidemia (diagnosed 2018)
    - No prior cardiac events

    MEDICATIONS:
    - Lisinopril 20mg daily
    - Atorvastatin 40mg daily

    PHYSICAL EXAMINATION:
    Vital Signs: BP 165/95, HR 92, RR 18, Temp 98.4°F, O2 Sat 98% on RA

    General: Anxious-appearing male in moderate distress
    Cardiovascular: Tachycardic, regular rhythm, no murmurs, rubs, or gallops
    Pulmonary: Clear to auscultation bilaterally

    DIAGNOSTIC TESTS:
    EKG: Sinus tachycardia, ST elevations in leads II, III, aVF
    Troponin I: 2.5 ng/mL (elevated)

    ASSESSMENT AND PLAN:
    58-year-old male with acute inferior STEMI. Cardiology consulted.
    Patient transferred to cardiac catheterization lab for emergent PCI.

    DISPOSITION:
    Admitted to CCU

    Dr. Sarah Lee, MD
    Emergency Medicine
    """

# Test markers for different test categories
pytest.mark.integration = pytest.mark.integration
pytest.mark.unit = pytest.mark.unit
pytest.mark.performance = pytest.mark.performance
pytest.mark.security = pytest.mark.security
pytest.mark.compliance = pytest.mark.compliance

# Healthcare-specific test utilities
class HealthcareTestUtilities:
    """Utility functions for healthcare testing"""

    @staticmethod
    def assert_phi_not_present(data: Any) -> None:
        """Assert that PHI is not present in data"""
        data_str = str(data).lower()

        # Check for common PHI patterns
        phi_patterns = [
            "ssn", "social security",
            "date of birth", "dob",
            "phone", "email",
            "address", "street",
            "mrn", "medical record number"
        ]

        for pattern in phi_patterns:
            assert pattern not in data_str, f"Potential PHI detected: {pattern}"

    @staticmethod
    def assert_medical_disclaimer_present(response: dict[str, Any]) -> None:
        """Assert that medical disclaimer is present in response"""
        response_str = str(response).lower()

        disclaimer_phrases = [
            "not medical advice",
            "administrative support only",
            "consult healthcare professional"
        ]

        has_disclaimer = any(phrase in response_str for phrase in disclaimer_phrases)
        assert has_disclaimer, "Medical disclaimer not found in response"

    @staticmethod
    def assert_hipaa_compliance(response: dict[str, Any]) -> None:
        """Assert response meets HIPAA compliance requirements"""
        # Check for audit logging information
        assert "timestamp" in response, "Missing timestamp for audit trail"

        # Check for appropriate access controls
        if "user_id" in response:
            assert "role" in response, "Missing role information for access control"

        # Ensure no direct PHI exposure
        HealthcareTestUtilities.assert_phi_not_present(response)
