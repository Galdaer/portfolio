"""
PHI-safe testing utilities for healthcare AI
Ensures no PHI in test data and provides synthetic data generation
"""

import random
import re
import uuid
from datetime import datetime
from typing import Any


class PHISafeTestingFramework:
    """Ensures no PHI in test data and provides synthetic data generation"""

    PHI_PATTERNS = {
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "phone": r"\b\d{3}-\d{3}-\d{4}\b",
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "date": r"\b\d{1,2}/\d{1,2}/\d{4}\b",
        "mrn": r"\b(MRN|MR|MedRec)\s*:?\s*\d+\b",
    }

    SAFE_TEST_PREFIXES = {
        "patient_id": "TEST_PAT_",
        "encounter_id": "TEST_ENC_",
        "provider_id": "TEST_PROV_",
        "session_id": "TEST_SESS_",
    }

    @classmethod
    def validate_test_data(cls, data: dict[str, Any]) -> bool:
        """Ensure test data contains no real PHI"""
        data_str = str(data)

        # Check for PHI patterns, but allow safe synthetic data
        phi_violations = []
        for phi_type, pattern in cls.PHI_PATTERNS.items():
            matches = re.findall(pattern, data_str)
            if matches:
                # Check if matches are synthetic/safe
                if phi_type == "email":
                    # Allow test emails with test domains
                    unsafe_emails = [
                        m
                        for m in matches
                        if not (
                            "@test.example.com" in m
                            or "@synthetic.test" in m
                            or "@example.com" in m
                        )
                    ]
                    if unsafe_emails:
                        phi_violations.append(f"{phi_type}: {unsafe_emails}")
                elif phi_type == "phone":
                    # Allow 555 test numbers
                    unsafe_phones = [m for m in matches if not m.startswith("555")]
                    if unsafe_phones:
                        phi_violations.append(f"{phi_type}: {unsafe_phones}")
                elif phi_type == "ssn":
                    # Allow 555 test SSNs
                    unsafe_ssns = [m for m in matches if not m.startswith("555")]
                    if unsafe_ssns:
                        phi_violations.append(f"{phi_type}: {unsafe_ssns}")
                else:
                    phi_violations.append(f"{phi_type}: {matches}")

        if phi_violations:
            raise ValueError(f"Potential PHI detected in test data: {phi_violations}")

        # Ensure test identifiers have proper prefixes
        for field, prefix in cls.SAFE_TEST_PREFIXES.items():
            if field in data and isinstance(data[field], str):
                if not data[field].startswith(prefix):
                    raise ValueError(f"{field} must start with {prefix} for test data")

        return True

    @classmethod
    def generate_synthetic_patient(cls) -> dict[str, Any]:
        """Generate HIPAA-safe synthetic patient data"""
        patient_num = random.randint(1000, 9999)
        return {
            "patient_id": f"TEST_PAT_{patient_num}",
            "first_name": random.choice(["John", "Jane", "Alex", "Sam", "Chris", "Taylor"]),
            "last_name": random.choice(["Doe", "Smith", "Johnson", "Brown", "Davis", "Miller"]),
            "date_of_birth": "1980-01-01",  # Fixed safe date
            "contact_phone": "555-0123",  # Safe test number
            "email": f"patient{patient_num}@test.example.com",
            "insurance_primary": "Test Insurance Co",
            "medical_record_number": f"TEST_MRN_{patient_num}",
            "chief_complaint": "Routine checkup",
            "medical_history": ["Hypertension", "Type 2 Diabetes"],
            "synthetic_marker": True,  # Clear indication this is synthetic data
        }

    @classmethod
    def generate_synthetic_encounter(cls, patient_id: str) -> dict[str, Any]:
        """Generate synthetic encounter data"""
        encounter_num = random.randint(1000, 9999)
        return {
            "encounter_id": f"TEST_ENC_{encounter_num}",
            "patient_id": patient_id,
            "provider_id": f"TEST_PROV_{random.randint(100, 999)}",
            "encounter_date": "2024-01-15",
            "encounter_type": random.choice(["office_visit", "consultation", "follow_up"]),
            "chief_complaint": random.choice(
                ["Routine checkup", "Follow-up visit", "Annual physical", "Medication review"]
            ),
            "session_id": f"TEST_SESS_{encounter_num}",
            "synthetic_marker": True,
        }

    @classmethod
    def generate_synthetic_audio_data(cls) -> dict[str, Any]:
        """Generate synthetic audio data for transcription testing"""
        return {
            "audio_format": "wav",
            "duration_seconds": 120,
            "sample_rate": 16000,
            "channels": 1,
            "mock_content": "This is a test audio transcription for healthcare AI testing.",
            "synthetic_marker": True,
            "test_only": True,
        }

    @classmethod
    def scrub_phi_from_logs(cls, log_data: str) -> str:
        """Remove potential PHI from log data"""
        scrubbed = log_data

        for phi_type, pattern in cls.PHI_PATTERNS.items():
            scrubbed = re.sub(
                pattern, f"[{phi_type.upper()}_REDACTED]", scrubbed, flags=re.IGNORECASE
            )

        return scrubbed

    @classmethod
    def create_test_session_context(cls) -> dict[str, Any]:
        """Create test session context with PHI-safe identifiers"""
        session_id = str(uuid.uuid4())
        return {
            "session_id": f"TEST_SESS_{session_id[:8]}",
            "timestamp": datetime.now().isoformat(),
            "test_mode": True,
            "phi_protected": True,
            "synthetic_data_only": True,
        }


class HealthcareTestValidator:
    """Validates healthcare test scenarios and compliance"""

    @staticmethod
    def validate_medical_safety(response: dict[str, Any]) -> bool:
        """Ensure response doesn't provide medical advice"""
        response_text = str(response).lower()

        # Check for medical advice patterns
        medical_advice_patterns = [
            "you should take",
            "i recommend",
            "my diagnosis is",
            "treatment plan:",
            "prescribe",
            "dosage",
        ]

        for pattern in medical_advice_patterns:
            if pattern in response_text:
                raise ValueError(f"Medical advice detected in response: {pattern}")

        return True

    @staticmethod
    def validate_phi_protection(response: dict[str, Any]) -> bool:
        """Ensure response doesn't expose PHI"""
        framework = PHISafeTestingFramework()

        try:
            framework.validate_test_data(response)
            return True
        except ValueError as e:
            raise ValueError(f"PHI protection violation in response: {e}")

    @staticmethod
    def validate_audit_logging(response: dict[str, Any]) -> bool:
        """Ensure response includes audit metadata"""
        required_audit_fields = ["session_id", "timestamp", "operation_type"]

        audit_metadata = response.get("_audit_metadata", {})

        missing_fields = [field for field in required_audit_fields if field not in audit_metadata]

        if missing_fields:
            raise ValueError(f"Missing audit fields: {missing_fields}")

        return True


class SyntheticDataGenerator:
    """Generate comprehensive synthetic healthcare data"""

    @staticmethod
    def generate_test_dataset(num_patients: int = 10) -> dict[str, Any]:
        """Generate a complete synthetic healthcare dataset"""
        framework = PHISafeTestingFramework()

        patients: list[dict[str, Any]] = []
        encounters: list[dict[str, Any]] = []

        for _i in range(num_patients):
            patient = framework.generate_synthetic_patient()
            patients.append(patient)

            # Generate 1-3 encounters per patient
            num_encounters = random.randint(1, 3)
            for _j in range(num_encounters):
                encounter = framework.generate_synthetic_encounter(patient["patient_id"])
                encounters.append(encounter)

        return {
            "patients": patients,
            "encounters": encounters,
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "synthetic_data_only": True,
                "phi_safe": True,
                "test_purpose_only": True,
            },
        }
