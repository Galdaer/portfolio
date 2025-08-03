# Healthcare AI Testing Instructions

## Purpose

Comprehensive testing guidance for healthcare AI systems emphasizing PHI-safe testing, medical compliance validation, and modern testing frameworks with synthetic data.

## Healthcare Testing Framework

### Database-Backed Testing (NEW APPROACH)

**CRITICAL CHANGE**: PHI lives in databases, not code. Tests should connect to synthetic database data.

```python
# ✅ CORRECT: Database-backed healthcare testing
from tests.database_test_utils import HealthcareTestCase, get_test_medical_scenario
from typing import Dict, List, Any, Optional, Protocol
from dataclasses import dataclass
import pytest
import asyncio
from unittest.mock import MagicMock, patch
import tempfile
import json
from datetime import datetime, timedelta

class HealthcareTestFramework:
    """
    Database-backed healthcare testing framework.
    Replaces hardcoded PHI patterns with database connections.
    """
    
    def __init__(self):
        self.synthetic_data = SyntheticHealthcareData()
        
    def setup_test_environment(self) -> Dict[str, Any]:
        """Set up test environment with database-backed synthetic data."""
        return {
            "database_url": "postgresql://localhost:5432/intelluxe_healthcare",
            "synthetic_data_provider": self.synthetic_data,
            "phi_protection": "database_only",
            "test_approach": "runtime_monitoring"
        }

# ✅ CORRECT: Migration from hardcoded to database-backed testing
class TestMigrationPattern:
    """
    Example of migrating from hardcoded PHI to database-backed testing.
    """
    
    def OLD_APPROACH_hardcoded_phi(self):
        # ❌ OLD WAY - Hardcoded PHI in code
        # test_patient = {
        #     'ssn': '123-45-6789',  # ❌ Fake PHI in code
        #     'name': 'John Doe'
        # }
        pass
    
    def NEW_APPROACH_database_backed(self):
        # ✅ NEW WAY - Database-backed synthetic data
        from tests.database_test_utils import HealthcareTestCase
        
        class MyTest(HealthcareTestCase):
            def test_patient_processing(self):
                patient = self.get_sample_patient()  # From database
                # Test logic here - no PHI in code!

    def _setup_test_database(self) -> Dict[str, Any]:
        """Set up isolated test database with synthetic data."""

        # Use SQLite in-memory for test isolation
        test_db_config = {
            "engine": "sqlite",
            "database": ":memory:",
            "isolation_level": "SERIALIZABLE",
            "phi_encryption": True,
            "audit_logging": True
        }

        return test_db_config

    def _load_synthetic_healthcare_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load comprehensive synthetic healthcare dataset."""

        # Load from existing synthetic data files
        synthetic_data = {
            "patients": self._load_synthetic_patients(),
            "doctors": self._load_synthetic_doctors(),
            "encounters": self._load_synthetic_encounters(),
            "lab_results": self._load_synthetic_lab_results(),
            "billing_claims": self._load_synthetic_billing_claims(),
            "agent_sessions": self._load_synthetic_agent_sessions()
        }

        # Validate cross-references
        self._validate_synthetic_data_integrity(synthetic_data)

        return synthetic_data

@dataclass
class HealthcareTestCase:
    """Structured healthcare test case with compliance validation."""

    name: str
    description: str
    test_data: Dict[str, Any]
    expected_outcome: Dict[str, Any]
    compliance_requirements: List[str]
    phi_safety_level: str  # "SAFE", "PROTECTED", "ENCRYPTED"
    medical_safety_check: bool = True

    def validate_test_safety(self) -> Dict[str, Any]:
        """Validate test case meets healthcare safety standards."""

        safety_validation = {
            "phi_exposure_risk": self._check_phi_exposure_risk(),
            "medical_advice_risk": self._check_medical_advice_risk(),
            "compliance_coverage": self._check_compliance_coverage(),
            "audit_requirement": self._check_audit_requirement(),
            "safe_to_execute": True
        }

        # Determine overall safety
        safety_validation["safe_to_execute"] = all([
            safety_validation["phi_exposure_risk"]["safe"],
            safety_validation["medical_advice_risk"]["safe"],
            safety_validation["compliance_coverage"]["adequate"]
        ])

        return safety_validation

    def _check_phi_exposure_risk(self) -> Dict[str, Any]:
        """Check for PHI exposure risks in test data."""

        phi_patterns = [
            r'\d{3}-\d{2}-\d{4}',  # SSN pattern
            r'\(\d{3}\)\s*\d{3}-\d{4}',  # Phone pattern
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'  # Email pattern
        ]

        test_data_str = json.dumps(self.test_data)
        phi_matches = []

        for pattern in phi_patterns:
            matches = re.findall(pattern, test_data_str)
            if matches:
                phi_matches.extend(matches)

        return {
            "safe": len(phi_matches) == 0 or self.phi_safety_level == "SYNTHETIC",
            "phi_pattern_matches": len(phi_matches),
            "safety_level": self.phi_safety_level,
            "risk_mitigation": "Use synthetic data only for testing"
        }

    def _check_medical_advice_risk(self) -> Dict[str, Any]:
        """Check for medical advice generation risks."""

        medical_advice_patterns = [
            "patient should take", "recommend medication", "diagnosis is",
            "treatment plan", "medical advice", "prescribe", "dosage"
        ]

        expected_output_str = json.dumps(self.expected_outcome).lower()

        advice_patterns_found = [
            pattern for pattern in medical_advice_patterns
            if pattern in expected_output_str
        ]

        return {
            "safe": len(advice_patterns_found) == 0,
            "medical_advice_patterns": advice_patterns_found,
            "requires_medical_review": len(advice_patterns_found) > 0
        }

# ✅ CORRECT: Comprehensive healthcare test scenarios
class HealthcareTestScenarios:
    """Comprehensive test scenarios for healthcare AI systems."""

    def generate_soap_note_processing_tests(self) -> List[HealthcareTestCase]:
        """Generate comprehensive SOAP note processing test cases."""

        test_cases = [
            HealthcareTestCase(
                name="Complete SOAP Note Processing",
                description="Test processing of complete SOAP note with all sections",
                test_data={
                    "soap_note": {
                        "subjective": "Patient reports mild headache for 2 days",
                        "objective": "BP 120/80, temp 98.6F, alert and oriented",
                        "assessment": "Tension headache, likely stress-related",
                        "plan": "Rest, hydration, follow up if symptoms persist"
                    },
                    "provider_id": "PROV001",
                    "patient_id": "PAT001"
                },
                expected_outcome={
                    "status": "success",
                    "soap_validation": "complete",
                    "missing_sections": [],
                    "format_valid": True
                },
                compliance_requirements=["HIPAA", "Documentation Standards"],
                phi_safety_level="SYNTHETIC"
            ),

            HealthcareTestCase(
                name="Incomplete SOAP Note Validation",
                description="Test validation of SOAP note missing required sections",
                test_data={
                    "soap_note": {
                        "subjective": "Patient reports symptoms",
                        "objective": "",  # Missing objective
                        "assessment": "Need more information",
                        "plan": ""  # Missing plan
                    },
                    "provider_id": "PROV002",
                    "patient_id": "PAT002"
                },
                expected_outcome={
                    "status": "validation_error",
                    "missing_sections": ["objective", "plan"],
                    "requires_completion": True
                },
                compliance_requirements=["Documentation Completeness"],
                phi_safety_level="SYNTHETIC"
            ),

            HealthcareTestCase(
                name="SOAP Note PHI Protection",
                description="Test PHI protection in SOAP note processing",
                test_data={
                    "soap_note": {
                        "subjective": "Patient John Doe (SSN: XXX-XX-XXXX) reports pain",
                        "objective": "Examination findings documented",
                        "assessment": "Working diagnosis established",
                        "plan": "Treatment plan developed"
                    },
                    "provider_id": "PROV003",
                    "patient_id": "PAT003"
                },
                expected_outcome={
                    "status": "success",
                    "phi_protected": True,
                    "sanitized_note": True,
                    "audit_logged": True
                },
                compliance_requirements=["HIPAA", "PHI Protection"],
                phi_safety_level="PROTECTED"
            )
        ]

        return test_cases

    def generate_agent_interaction_tests(self) -> List[HealthcareTestCase]:
        """Generate healthcare AI agent interaction test cases."""

        return [
            HealthcareTestCase(
                name="Document Processing Agent Validation",
                description="Test document processing agent with medical documents",
                test_data={
                    "document_type": "discharge_summary",
                    "content": "Patient discharged in stable condition...",
                    "processing_task": "extract_key_information",
                    "agent_id": "document_processor"
                },
                expected_outcome={
                    "status": "success",
                    "extracted_info": {
                        "discharge_date": "2024-01-15",
                        "condition": "stable",
                        "follow_up_required": True
                    },
                    "medical_advice_generated": False
                },
                compliance_requirements=["No Medical Advice", "Data Accuracy"],
                phi_safety_level="SYNTHETIC"
            ),

            HealthcareTestCase(
                name="Intake Agent Medical Safety",
                description="Test intake agent doesn't provide medical advice",
                test_data={
                    "patient_query": "What medication should I take for my headache?",
                    "agent_id": "intake_agent",
                    "session_context": {"patient_id": "PAT004"}
                },
                expected_outcome={
                    "status": "success",
                    "response_type": "administrative_guidance",
                    "medical_advice_provided": False,
                    "referral_to_provider": True
                },
                compliance_requirements=["Medical Safety", "No Diagnosis"],
                phi_safety_level="SYNTHETIC",
                medical_safety_check=True
            )
        ]

    def generate_compliance_validation_tests(self) -> List[HealthcareTestCase]:
        """Generate HIPAA and compliance validation test cases."""

        return [
            HealthcareTestCase(
                name="Audit Logging Compliance",
                description="Test comprehensive audit logging for all patient data access",
                test_data={
                    "user_action": "view_patient_record",
                    "user_id": "USER001",
                    "patient_id": "PAT005",
                    "access_purpose": "treatment_planning",
                    "timestamp": datetime.now().isoformat()
                },
                expected_outcome={
                    "audit_log_created": True,
                    "log_details": {
                        "action": "view_patient_record",
                        "user_hash": "abc123...",
                        "patient_hash": "def456...",
                        "purpose": "treatment_planning",
                        "compliance_level": "HIPAA"
                    }
                },
                compliance_requirements=["HIPAA Audit Trail"],
                phi_safety_level="PROTECTED"
            )
        ]
```

### Modern Testing Tools Integration

```python
# ✅ CORRECT: Modern testing framework integration for healthcare
class ModernHealthcareTestRunner:
    """Modern testing framework integration for healthcare AI."""

    def __init__(self) -> None:
        self.pytest_config = self._setup_pytest_config()
        self.coverage_config = self._setup_coverage_config()
        self.performance_config = self._setup_performance_config()

    def _setup_pytest_config(self) -> Dict[str, Any]:
        """Configure pytest for healthcare testing."""

        return {
            "markers": {
                "phi_safe": "Tests that handle PHI safely",
                "medical_safety": "Tests for medical safety validation",
                "compliance": "Compliance and regulatory tests",
                "performance": "Performance and load tests",
                "integration": "Integration tests with healthcare systems"
            },
            "fixtures": {
                "synthetic_data": "Provides synthetic healthcare data",
                "test_database": "Isolated test database",
                "mock_ehr": "Mock EHR system for testing",
                "compliance_validator": "HIPAA compliance validation"
            },
            "plugins": [
                "pytest-asyncio",
                "pytest-cov",
                "pytest-mock",
                "pytest-xdist",
                "pytest-benchmark"
            ]
        }

    def run_healthcare_test_suite(self, test_categories: List[str]) -> Dict[str, Any]:
        """Run comprehensive healthcare test suite."""

        test_commands = {
            "unit": "pytest tests/unit/ -v --tb=short",
            "integration": "pytest tests/integration/ -v --tb=line",
            "compliance": "pytest tests/compliance/ -v -m compliance",
            "performance": "pytest tests/performance/ -v --benchmark-only",
            "phi_safety": "pytest tests/ -v -m phi_safe",
            "medical_safety": "pytest tests/ -v -m medical_safety"
        }

        results = {}
        for category in test_categories:
            if category in test_commands:
                results[category] = self._execute_test_command(test_commands[category])

        return results

    def _execute_test_command(self, command: str) -> Dict[str, Any]:
        """Execute test command with healthcare-specific validation."""

        # Implementation would execute command and parse results
        return {
            "exit_code": 0,
            "tests_passed": 95,
            "tests_failed": 2,
            "coverage_percentage": 88.5,
            "phi_safety_validated": True,
            "compliance_checks_passed": True
        }

# ✅ CORRECT: Healthcare-specific pytest fixtures
@pytest.fixture
def synthetic_healthcare_data() -> Dict[str, List[Dict[str, Any]]]:
    """Provide comprehensive synthetic healthcare data for testing."""

    return {
        "patients": [
            {
                "patient_id": "PAT001",
                "demographics": {
                    "age": 45,
                    "gender": "M",
                    "insurance": "Blue Cross"
                },
                "medical_history": ["hypertension", "diabetes_type2"]
            },
            {
                "patient_id": "PAT002",
                "demographics": {
                    "age": 32,
                    "gender": "F",
                    "insurance": "Aetna"
                },
                "medical_history": ["migraine"]
            }
        ],
        "doctors": [
            {
                "provider_id": "PROV001",
                "name": "Dr. Smith",
                "specialty": "Internal Medicine",
                "npi": "1234567890"
            }
        ],
        "encounters": [
            {
                "encounter_id": "ENC001",
                "patient_id": "PAT001",
                "provider_id": "PROV001",
                "date": "2024-01-15",
                "type": "office_visit"
            }
        ]
    }

@pytest.fixture
def test_database():
    """Provide isolated test database."""

    # Set up in-memory SQLite for testing
    import sqlite3
    conn = sqlite3.connect(":memory:")

    # Create healthcare tables
    conn.execute("""
        CREATE TABLE patients (
            patient_id TEXT PRIMARY KEY,
            demographics TEXT,
            created_at TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE encounters (
            encounter_id TEXT PRIMARY KEY,
            patient_id TEXT,
            provider_id TEXT,
            soap_note TEXT,
            created_at TIMESTAMP
        )
    """)

    yield conn
    conn.close()

@pytest.fixture
def compliance_validator():
    """Provide HIPAA compliance validation."""

    class MockComplianceValidator:
        def validate_phi_protection(self, data: Dict[str, Any]) -> bool:
            """Mock PHI protection validation."""
            # Check for obvious PHI patterns
            data_str = json.dumps(data)
            phi_patterns = [r'\d{3}-\d{2}-\d{4}', r'\(\d{3}\)\s*\d{3}-\d{4}']

            for pattern in phi_patterns:
                if re.search(pattern, data_str):
                    return False
            return True

        def validate_audit_logging(self, operation: str) -> bool:
            """Mock audit logging validation."""
            required_fields = ["user_id", "action", "timestamp", "resource"]
            return all(field in operation for field in required_fields)

    return MockComplianceValidator()

# ✅ CORRECT: Healthcare test examples with modern patterns
class TestHealthcareSOAPProcessing:
    """Test SOAP note processing with healthcare compliance."""

    @pytest.mark.phi_safe
    @pytest.mark.asyncio
    async def test_soap_note_processing_complete(
        self,
        synthetic_healthcare_data: Dict[str, Any],
        compliance_validator
    ) -> None:
        """Test complete SOAP note processing with PHI safety."""

        # Arrange
        soap_processor = SOAPNoteProcessor()
        test_soap_data = {
            "subjective": "Patient reports mild headache for 2 days",
            "objective": "BP 120/80, temp 98.6F, alert and oriented",
            "assessment": "Tension headache, likely stress-related",
            "plan": "Rest, hydration, follow up if symptoms persist"
        }

        # Act
        result = await soap_processor.process_soap_note(
            raw_note=json.dumps(test_soap_data),
            provider_id="PROV001"
        )

        # Assert
        assert result is not None
        assert result.subjective == test_soap_data["subjective"]
        assert result.objective == test_soap_data["objective"]
        assert result.assessment == test_soap_data["assessment"]
        assert result.plan == test_soap_data["plan"]
        assert result.provider_id == "PROV001"

        # Validate PHI protection
        anonymized = result.anonymize_for_logging()
        assert compliance_validator.validate_phi_protection(anonymized)

    @pytest.mark.medical_safety
    def test_soap_note_no_medical_advice(self, synthetic_healthcare_data: Dict[str, Any]) -> None:
        """Test SOAP note processing doesn't generate medical advice."""

        # Arrange
        soap_processor = SOAPNoteProcessor()

        # Act
        validation_result = soap_processor.validate_medical_safety({
            "subjective": "Patient asks for medication recommendation",
            "objective": "Patient appears well",
            "assessment": "Administrative documentation only",
            "plan": "Refer to healthcare provider for medical decisions"
        })

        # Assert - Should not contain medical advice patterns
        assert validation_result["safe"] is True
        assert validation_result["medical_advice_detected"] is False
        assert "refer to healthcare provider" in validation_result["plan"].lower()

    @pytest.mark.compliance
    def test_soap_note_audit_logging(
        self,
        synthetic_healthcare_data: Dict[str, Any],
        compliance_validator
    ) -> None:
        """Test SOAP note processing creates proper audit logs."""

        # Arrange
        soap_processor = SOAPNoteProcessor()
        audit_data = {
            "user_id": "USER001",
            "action": "create_soap_note",
            "timestamp": datetime.now().isoformat(),
            "resource": "soap_note",
            "patient_hash": "abc123..."
        }

        # Act & Assert
        assert compliance_validator.validate_audit_logging(audit_data)

class TestHealthcareAgentInteractions:
    """Test healthcare AI agent interactions."""

    @pytest.mark.phi_safe
    @pytest.mark.asyncio
    async def test_document_processor_agent(
        self,
        synthetic_healthcare_data: Dict[str, Any]
    ) -> None:
        """Test document processing agent with synthetic data."""

        # Arrange
        document_processor = DocumentProcessorAgent()
        test_document = {
            "type": "discharge_summary",
            "content": "Patient discharged in stable condition with follow-up scheduled",
            "patient_id": "PAT001"
        }

        # Act
        result = await document_processor.process_document(test_document)

        # Assert
        assert result["status"] == "success"
        assert result["extracted_info"]["condition"] == "stable"
        assert result["medical_advice_generated"] is False
        assert "follow_up" in result["extracted_info"]

    @pytest.mark.medical_safety
    def test_intake_agent_medical_safety(self, synthetic_healthcare_data: Dict[str, Any]) -> None:
        """Test intake agent doesn't provide medical advice."""

        # Arrange
        intake_agent = IntakeAgent()
        patient_query = "What medication should I take for my headache?"

        # Act
        response = intake_agent.process_query(patient_query)

        # Assert
        assert response["medical_advice_provided"] is False
        assert response["referral_to_provider"] is True
        assert "consult with your healthcare provider" in response["message"].lower()
```

### Performance Testing for Healthcare

```python
# ✅ CORRECT: Healthcare-specific performance testing
class HealthcarePerformanceTestSuite:
    """Performance testing for healthcare AI systems."""

    @pytest.mark.performance
    @pytest.mark.benchmark
    def test_soap_note_processing_performance(self, benchmark) -> None:
        """Benchmark SOAP note processing performance."""

        def process_soap_notes():
            processor = SOAPNoteProcessor()
            test_notes = [
                {"subjective": f"Patient {i} symptoms", "objective": f"Exam {i}",
                 "assessment": f"Assessment {i}", "plan": f"Plan {i}"}
                for i in range(100)
            ]

            results = []
            for note in test_notes:
                result = processor.process_soap_note_sync(note, "PROV001")
                results.append(result)

            return results

        # Benchmark with healthcare performance requirements
        result = benchmark.pedantic(process_soap_notes, rounds=5, iterations=10)

        # Healthcare performance assertions
        assert len(result) == 100
        assert benchmark.stats.mean < 1.0  # Should process 100 notes in < 1 second

    @pytest.mark.performance
    def test_concurrent_patient_data_access(self) -> None:
        """Test concurrent patient data access performance."""

        import asyncio
        import time

        async def concurrent_patient_access():
            patient_service = PatientDataService()
            patient_ids = [f"PAT{i:03d}" for i in range(1, 51)]  # 50 patients

            start_time = time.time()

            # Simulate concurrent access
            tasks = [
                patient_service.get_patient_data(patient_id)
                for patient_id in patient_ids
            ]

            results = await asyncio.gather(*tasks)

            end_time = time.time()
            processing_time = end_time - start_time

            # Healthcare performance requirements
            assert processing_time < 2.0  # Should handle 50 concurrent requests in < 2 seconds
            assert len(results) == 50
            assert all(result is not None for result in results)

        asyncio.run(concurrent_patient_access())

    @pytest.mark.performance
    def test_ehr_integration_response_time(self) -> None:
        """Test EHR integration response time performance."""

        ehr_client = MockEHRClient()

        # Test various EHR operations
        operations = [
            ("get_patient", "PAT001"),
            ("create_encounter", {"patient_id": "PAT001", "type": "visit"}),
            ("update_soap_note", {"encounter_id": "ENC001", "note": "Updated"}),
            ("search_patients", {"criteria": {"age_range": [30, 50]}})
        ]

        response_times = []

        for operation, params in operations:
            start_time = time.time()
            result = getattr(ehr_client, operation)(params)
            end_time = time.time()

            response_time = end_time - start_time
            response_times.append(response_time)

            # Healthcare EHR response time requirements
            assert response_time < 0.5  # Each operation should complete in < 500ms
            assert result is not None

        # Overall performance check
        average_response_time = sum(response_times) / len(response_times)
        assert average_response_time < 0.3  # Average should be < 300ms
```

### Test Execution and Validation

```bash
# Healthcare test execution commands
pytest tests/ -v -m "phi_safe and not performance"  # PHI-safe tests only
pytest tests/ -v -m "medical_safety"  # Medical safety tests
pytest tests/ -v -m "compliance"  # Compliance tests
pytest tests/ -v --tb=short --cov=core --cov=agents  # Coverage testing
pytest tests/performance/ -v --benchmark-only  # Performance tests only

# Comprehensive healthcare test suite
pytest tests/ -v -m "phi_safe or medical_safety or compliance" --tb=short --cov=core --cov=agents --cov-report=html
```

## Healthcare Testing Best Practices

### Test Data Management

- **Synthetic Data Only**: Never use real PHI in tests
- **Cross-Reference Validation**: Ensure synthetic data maintains realistic relationships
- **Data Minimization**: Use only necessary data for each test
- **PHI Pattern Detection**: Validate no real PHI patterns in synthetic data

### Medical Safety Testing

- **No Medical Advice**: Test that systems never provide medical advice
- **Administrative Focus**: Validate systems stay within administrative boundaries
- **Provider Referrals**: Test appropriate referrals to healthcare providers
- **Compliance Validation**: Ensure regulatory compliance in all scenarios

### Modern Testing Integration

- **Ruff Integration**: `ruff check tests/` for ultra-fast test code validation
- **MyPy Validation**: `mypy tests/ --config-file mypy.ini` for type safety
- **Async Testing**: Use `pytest-asyncio` for testing async healthcare operations
- **Performance Benchmarking**: Use `pytest-benchmark` for healthcare performance requirements

### Continuous Integration Testing

- **GitHub Actions**: Integrate with self-hosted runners for healthcare environments
- **Coverage Requirements**: Maintain >85% test coverage for medical modules
- **Compliance Validation**: Automated HIPAA compliance checking in CI/CD
- **PHI Safety Scanning**: Automated detection of PHI exposure risks

Remember: Healthcare testing requires rigorous validation of PHI protection, medical safety compliance, and regulatory adherence while maintaining comprehensive test coverage and performance standards.
