"""
Shared test fixtures for business services testing.

Provides database connections, synthetic data access, and common test utilities
for all business service tests.
"""

import os
from unittest.mock import AsyncMock, MagicMock

import pytest
import redis

# Import project modules
from tests.database_test_utils import SyntheticHealthcareData


@pytest.fixture(scope="session")
def db_url():
    """Database connection URL for testing."""
    return os.getenv(
        "HEALTHCARE_DB_URL",
        "postgresql://intelluxe:secure_password@172.20.0.13:5432/intelluxe",
    )


@pytest.fixture(scope="session")
def redis_url():
    """Redis connection URL for testing."""
    return os.getenv("REDIS_URL", "redis://172.20.0.12:6379")


@pytest.fixture(scope="session")
def healthcare_data(db_url):
    """Provide access to synthetic healthcare data."""
    data_provider = SyntheticHealthcareData(db_url)
    data_provider.connect()
    yield data_provider
    if data_provider.connection:
        data_provider.connection.close()


@pytest.fixture(scope="function")
def db_connection(healthcare_data):
    """Database connection for individual tests with function scope to prevent transaction issues."""
    return healthcare_data.connection


@pytest.fixture
def redis_connection(redis_url):
    """Redis connection for testing cache and session data."""
    try:
        r = redis.from_url(redis_url, decode_responses=True)
        r.ping()  # Test connection
        yield r
    except Exception:
        # Mock Redis if not available
        yield MagicMock()


@pytest.fixture
def sample_patients(db_connection):
    """Get sample patient data from database."""
    cursor = db_connection.cursor()
    try:
        cursor.execute("""
            SELECT patient_id, first_name, last_name, date_of_birth,
                   phone, email, address_line1, city, state, zip_code,
                   emergency_contact_name, emergency_contact_phone
            FROM patients
            LIMIT 5
        """)
        return cursor.fetchall()
    except Exception:
        db_connection.rollback()
        return []  # Return empty list for tests to handle gracefully
    finally:
        cursor.close()


@pytest.fixture
def sample_doctors(db_connection):
    """Get sample doctor data from database."""
    cursor = db_connection.cursor()
    try:
        cursor.execute("""
            SELECT doctor_id, first_name, last_name, specialty,
                   npi_number, license_number, phone, email
            FROM doctors
            LIMIT 3
        """)
        return cursor.fetchall()
    except Exception:
        db_connection.rollback()
        return []
    finally:
        cursor.close()


@pytest.fixture
def sample_insurance_verifications(db_connection):
    """Get sample insurance verification data."""
    cursor = db_connection.cursor()
    try:
        cursor.execute("""
            SELECT verification_id, patient_id, insurance_provider, member_id,
                   group_number, eligibility_status, coverage_type,
                   copay_amount, deductible_amount, deductible_met, prior_auth_required
            FROM insurance_verifications
            LIMIT 5
        """)
        return cursor.fetchall()
    except Exception:
        db_connection.rollback()
        return []
    finally:
        cursor.close()


@pytest.fixture
def sample_billing_claims(db_connection):
    """Get sample billing claims data."""
    cursor = db_connection.cursor()
    try:
        cursor.execute("""
            SELECT claim_id, patient_id, doctor_id, encounter_id,
                   claim_amount, insurance_amount, patient_amount,
                   service_date, cpt_codes, diagnosis_codes, claim_status
            FROM billing_claims
            LIMIT 5
        """)
        return cursor.fetchall()
    except Exception:
        db_connection.rollback()
        return []
    finally:
        cursor.close()


@pytest.fixture
def sample_audit_logs(db_connection):
    """Get sample audit log data for compliance testing."""
    cursor = db_connection.cursor()
    try:
        cursor.execute("""
            SELECT log_id, user_id, user_type, action, resource_type,
                   resource_id, timestamp, ip_address, user_agent, success
            FROM audit_logs
            LIMIT 10
        """)
        return cursor.fetchall()
    except Exception:
        db_connection.rollback()
        return []
    finally:
        cursor.close()


@pytest.fixture
def sample_doctor_preferences(db_connection):
    """Get sample doctor preferences for personalization testing."""
    cursor = db_connection.cursor()
    try:
        cursor.execute("""
            SELECT doctor_id, documentation_style, preferred_templates,
                   ai_assistance_level, auto_coding_preference,
                   communication_style, specialization_focus
            FROM doctor_preferences
        """)
        return cursor.fetchall()
    except Exception:
        db_connection.rollback()
        return []
    finally:
        cursor.close()


@pytest.fixture
def mock_service_responses():
    """Mock responses for service-to-service communication."""
    return {
        "insurance_verification": {
            "success": {
                "verification_id": "ver_123456",
                "eligibility_status": "Active",
                "coverage_verified": True,
                "copay_amount": 25,
                "prior_auth_required": False,
            },
            "failure": {
                "error": "Insurance provider not responding",
                "retry_recommended": True,
            },
        },
        "billing_engine": {
            "success": {
                "claim_id": "CLM-789012",
                "claim_status": "submitted",
                "estimated_reimbursement": 250.00,
            },
            "denial": {
                "claim_id": "CLM-789013",
                "claim_status": "denied",
                "denial_reason": "Prior authorization required",
            },
        },
        "compliance_monitor": {
            "violation_detected": {
                "violation_id": "VIO_001",
                "severity": "high",
                "violation_type": "unauthorized_phi_access",
            },
            "compliance_score": {
                "overall_score": 95.2,
                "last_updated": "2024-01-15T10:30:00Z",
            },
        },
        "business_intelligence": {
            "analytics": {
                "revenue_metrics": {
                    "total_revenue": 125000.50,
                    "claims_processed": 450,
                    "average_claim_value": 277.78,
                },
            },
        },
        "doctor_personalization": {
            "model_ready": {
                "doctor_id": "dr_001",
                "model_version": "v1.2",
                "adaptation_score": 8.7,
            },
        },
    }


@pytest.fixture
def mock_ai_responses():
    """Mock AI model responses for testing reasoning patterns."""
    return {
        "chain_of_thought": {
            "steps": [
                "1. Gathering patient insurance information",
                "2. Validating insurance provider connectivity",
                "3. Checking eligibility and coverage",
                "4. Verifying benefits and limitations",
                "5. Providing final verification result",
            ],
            "reasoning": "Based on the step-by-step analysis...",
            "conclusion": "Insurance verification completed successfully",
        },
        "tree_of_thoughts": {
            "paths": [
                {
                    "path_id": 1,
                    "strategy": "standard_billing",
                    "estimated_reimbursement": 200.00,
                    "confidence": 0.85,
                },
                {
                    "path_id": 2,
                    "strategy": "alternative_coding",
                    "estimated_reimbursement": 275.00,
                    "confidence": 0.72,
                },
            ],
            "selected_path": 2,
            "reasoning": "Alternative coding provides better reimbursement",
        },
    }


@pytest.fixture
def service_urls():
    """Service endpoint URLs for testing."""
    return {
        "healthcare_api": "http://172.20.0.11:8000",
        "insurance_verification": "http://172.20.0.23:8003",
        "billing_engine": "http://172.20.0.24:8004",
        "compliance_monitor": "http://172.20.0.25:8005",
        "business_intelligence": "http://172.20.0.26:8006",
        "doctor_personalization": "http://172.20.0.27:8007",
    }


@pytest.fixture
def test_environment_variables():
    """Environment variables for testing."""
    return {
        "POSTGRES_URL": "postgresql://intelluxe:secure_password@172.20.0.13:5432/intelluxe",
        "REDIS_URL": "redis://172.20.0.12:6379",
        "PHI_DETECTION_ENABLED": "true",
        "COT_REASONING_ENABLED": "true",
        "TOT_REASONING_ENABLED": "true",
        "PERSONALIZATION_ENABLED": "true",
        "AUDIT_RETENTION_DAYS": "2555",
        "LOG_LEVEL": "INFO",
    }


# Pytest markers for organizing tests
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "insurance: tests for insurance verification service")
    config.addinivalue_line("markers", "billing: tests for billing engine service")
    config.addinivalue_line("markers", "compliance: tests for compliance monitor service")
    config.addinivalue_line("markers", "analytics: tests for business intelligence service")
    config.addinivalue_line("markers", "personalization: tests for doctor personalization service")
    config.addinivalue_line("markers", "integration: tests for service integration")
    config.addinivalue_line("markers", "chain_of_thought: tests for CoT reasoning")
    config.addinivalue_line("markers", "tree_of_thoughts: tests for ToT reasoning")
    config.addinivalue_line("markers", "phi_safe: tests that handle PHI safely")
    config.addinivalue_line("markers", "slow: tests that take longer to run")


# Mock external dependencies for testing
@pytest.fixture
def mock_ollama_client():
    """Mock Ollama client for AI inference testing."""
    mock = AsyncMock()
    mock.chat.return_value = {
        "message": {
            "content": "Mock AI response for testing",
        },
    }
    return mock


@pytest.fixture
def mock_external_apis():
    """Mock external API responses."""
    return {
        "insurance_api": {
            "eligibility_check": {"eligible": True, "benefits": "Full coverage"},
            "prior_auth": {"required": False, "status": "approved"},
        },
        "medical_codes_api": {
            "validate_cpt": {"valid": True, "description": "Office visit"},
            "validate_icd10": {"valid": True, "description": "Essential hypertension"},
        },
    }
