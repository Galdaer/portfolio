#!/usr/bin/env python3
"""
Comprehensive Synthetic Healthcare Data Generator for Intelluxe AI
Combines simple JSON generation with comprehensive database population
Generates HIPAA-compliant synthetic data for all phases of development
"""

import json
import os
import random
import uuid
from datetime import datetime, timedelta
from typing import Any

from faker import Faker
from faker.providers import BaseProvider

# Healthcare scripts require database connectivity - no fallbacks
try:
    import psycopg2

    PSYCOPG2_AVAILABLE = True
except ImportError as e:
    print("❌ Database connection required for healthcare data generation")
    print("   To fix: Run 'make setup' to initialize database dependencies")
    print("   Database-first architecture: Healthcare scripts require database connectivity")
    raise ImportError(
        "Healthcare data generation requires psycopg2 database connectivity. "
        "Run 'make setup' to initialize database or install with: pip install psycopg2-binary",
    ) from e

try:
    import redis

    redis_module = redis
    REDIS_AVAILABLE = True
except ImportError as e:
    print("❌ Redis connection required for healthcare caching")
    print("   To fix: Run 'make setup' to initialize Redis dependencies")
    raise ImportError(
        "Healthcare data generation requires Redis for caching. "
        "Run 'make setup' to initialize Redis or install with: pip install redis",
    ) from e

# Initialize Faker with healthcare-specific providers
fake = Faker()


# Synthetic data generation constants for maintainability
class SyntheticDataConstants:
    """Constants for synthetic healthcare data generation"""

    # SSN Constants
    SYNTHETIC_SSN_PREFIX = "555"
    SSN_GROUP_MIN = 10
    SSN_GROUP_MAX = 99
    SSN_SERIAL_MIN = 1000
    SSN_SERIAL_MAX = 9999

    # Phone Number Constants
    SYNTHETIC_PHONE_AREA_CODES = ["555", "123", "456"]
    PHONE_PREFIX_MIN = 100
    PHONE_PREFIX_MAX = 999
    PHONE_LINE_MIN = 1000
    PHONE_LINE_MAX = 9999

    # Medical Record Number Constants
    MRN_PREFIXES = ["MRN", "HSP", "MED", "PAT"]
    MRN_NUMBER_MIN = 100000
    MRN_NUMBER_MAX = 999999

    # Email Constants
    SYNTHETIC_EMAIL_DOMAIN = "synthetic-health.test"
    EMAIL_NUMBER_MIN = 1
    EMAIL_NUMBER_MAX = 999


def random_date(start: datetime, end: datetime) -> datetime:
    """Generate random date between two dates"""
    return start + timedelta(days=random.randint(0, int((end - start).days)))


class HealthcareProvider(BaseProvider):
    """Custom Faker provider for healthcare-specific data"""

    medical_specialties = [
        "Family Medicine",
        "Internal Medicine",
        "Pediatrics",
        "Cardiology",
        "Dermatology",
        "Emergency Medicine",
        "Neurology",
        "Oncology",
        "Psychiatry",
        "Surgery",
        "Orthopedics",
        "Radiology",
    ]

    insurance_providers = [
        "Anthem",
        "UnitedHealth",
        "Aetna",
        "Cigna",
        "Blue Cross Blue Shield",
        "Humana",
        "Kaiser Permanente",
        "Molina Healthcare",
    ]

    medical_conditions = [
        "Hypertension",
        "Type 2 Diabetes",
        "Hyperlipidemia",
        "Asthma",
        "Depression",
        "Anxiety",
        "Arthritis",
        "COPD",
        "Migraine",
        "Sleep Apnea",
        "Chronic Pain",
        "Allergies",
    ]

    lab_tests = [
        "CBC",
        "A1C",
        "Lipid Panel",
        "COVID PCR",
        "Basic Metabolic Panel",
        "Liver Function Tests",
        "Thyroid Panel",
        "Urinalysis",
        "Vitamin D",
        "PSA",
        "HbA1c",
        "CRP",
        "ESR",
        "Troponin",
    ]

    visit_reasons = [
        "Annual Physical",
        "Follow-up",
        "Sick Visit",
        "Vaccination",
        "Lab Review",
        "Chronic Disease Management",
        "Preventive Care",
        "Acute Illness",
        "Routine Checkup",
        "Urgent Care",
    ]

    def medical_specialty(self) -> str:
        return str(self.random_element(self.medical_specialties))

    def insurance_provider(self) -> str:
        return str(self.random_element(self.insurance_providers))

    def medical_condition(self) -> str:
        return str(self.random_element(self.medical_conditions))

    def lab_test(self) -> str:
        return str(self.random_element(self.lab_tests))

    def visit_reason(self) -> str:
        return str(self.random_element(self.visit_reasons))

    def member_id(self) -> str:
        """Generate realistic member ID"""
        return f"{fake.random_element(['A', 'B', 'C', 'H', 'U'])}{fake.random_number(digits=9)}"

    def npi_number(self) -> str:
        """Generate National Provider Identifier"""
        return f"{fake.random_number(digits=10)}"


# Add healthcare provider to Faker
fake.add_provider(HealthcareProvider)


class SyntheticHealthcareDataGenerator:
    """Generate comprehensive synthetic healthcare data for all phases"""

    def __init__(
        self,
        num_doctors: int = 25,
        num_patients: int = 500,
        num_encounters: int = 1000,
        output_dir: str = "data/synthetic",
        use_database: bool = False,
    ):
        self.num_doctors = num_doctors
        self.num_patients = num_patients
        self.num_encounters = num_encounters
        self.output_dir = output_dir
        self.use_database = use_database

        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

        # Storage for cross-referential data
        self.doctors: list[dict[str, Any]] = []
        self.patients: list[dict[str, Any]] = []
        self.encounters: list[dict[str, Any]] = []
        self.lab_results: list[dict[str, Any]] = []
        self.insurance_verifications: list[dict[str, Any]] = []
        self.agent_sessions: list[dict[str, Any]] = []

        # Phase 2 business data for local deployment
        self.billing_claims: list[dict[str, Any]] = []
        self.doctor_preferences: list[dict[str, Any]] = []
        self.audit_logs: list[dict[str, Any]] = []

        # Business services data
        self.compliance_violations: list[dict[str, Any]] = []
        self.analytics_metrics: list[dict[str, Any]] = []
        self.personalization_training_data: list[dict[str, Any]] = []
        self.service_communication_logs: list[dict[str, Any]] = []

        # Database connections (optional)
        self.db_conn: Any | None = None
        self.redis_client: Any | None = None

        if self.use_database:
            self._connect_to_databases()

    def _connect_to_databases(self) -> None:
        """Connect to PostgreSQL and Redis - REQUIRED for healthcare operations"""
        # PostgreSQL connection - REQUIRED
        try:
            self.db_conn = psycopg2.connect(
                "postgresql://intelluxe:secure_password@172.20.0.13:5432/intelluxe",
            )
            print("✅ Connected to PostgreSQL")
        except Exception as e:
            print(f"❌ PostgreSQL connection failed: {e}")
            print("   To fix: Run 'make setup' to initialize database or verify DATABASE_URL")
            print(
                "   Database-first architecture: Healthcare scripts require database connectivity",
            )
            msg = (
                f"Healthcare data generation requires PostgreSQL database connectivity. Error: {e}. "
                "Run 'make setup' to initialize database."
            )
            raise ConnectionError(
                msg,
            ) from e

        # Redis connection - REQUIRED
        try:
            self.redis_client = redis_module.Redis(
                host="localhost",
                port=6379,
                decode_responses=True,
            )
            if self.redis_client:
                self.redis_client.ping()
                print("✅ Connected to Redis")
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            print("   To fix: Run 'make setup' to initialize Redis dependencies")
            msg = (
                f"Healthcare data generation requires Redis for caching. Error: {e}. "
                "Run 'make setup' to initialize Redis."
            )
            raise ConnectionError(
                msg,
            ) from e

    def generate_patient(self) -> dict[str, Any]:
        """
        Generate synthetic patient data with PHI-like realistic patterns

        Creates realistic synthetic data that properly tests PHI detection systems:
        - Realistic SSN patterns (555-xx-xxxx for synthetic safety)
        - Phone numbers with realistic area codes
        - Email patterns that look real but are clearly synthetic
        - Medical record numbers with hospital-like prefixes
        - Realistic names and addresses
        """
        first_name = fake.first_name()
        last_name = fake.last_name()

        # Enhanced PHI-like patterns for proper detection testing
        # Break down SSN generation for readability
        ssn_group = random.randint(
            SyntheticDataConstants.SSN_GROUP_MIN,
            SyntheticDataConstants.SSN_GROUP_MAX,
        )
        ssn_serial = random.randint(
            SyntheticDataConstants.SSN_SERIAL_MIN,
            SyntheticDataConstants.SSN_SERIAL_MAX,
        )
        synthetic_ssn = f"{SyntheticDataConstants.SYNTHETIC_SSN_PREFIX}-{ssn_group}-{ssn_serial}"  # 555 prefix = synthetic SSN (reserved for test data)

        # Break down phone generation for readability
        phone_area = random.choice(SyntheticDataConstants.SYNTHETIC_PHONE_AREA_CODES)
        phone_prefix = random.randint(
            SyntheticDataConstants.PHONE_PREFIX_MIN,
            SyntheticDataConstants.PHONE_PREFIX_MAX,
        )
        phone_line = random.randint(
            SyntheticDataConstants.PHONE_LINE_MIN,
            SyntheticDataConstants.PHONE_LINE_MAX,
        )
        realistic_phone = f"({phone_area}) {phone_prefix}-{phone_line}"

        # Break down email generation for readability
        email_number = random.randint(
            SyntheticDataConstants.EMAIL_NUMBER_MIN,
            SyntheticDataConstants.EMAIL_NUMBER_MAX,
        )
        synthetic_email = f"{first_name.lower()}.{last_name.lower()}{email_number}@{SyntheticDataConstants.SYNTHETIC_EMAIL_DOMAIN}"

        # Realistic medical record number pattern
        mrn_prefix = random.choice(SyntheticDataConstants.MRN_PREFIXES)
        medical_record_number = f"{mrn_prefix}{random.randint(SyntheticDataConstants.MRN_NUMBER_MIN, SyntheticDataConstants.MRN_NUMBER_MAX)}"

        return {
            "id": str(uuid.uuid4()),
            "patient_id": f"pt_{uuid.uuid4().hex[:8]}",
            "first_name": first_name,
            "last_name": last_name,
            # PHI-like patterns that should trigger detection systems
            "ssn": synthetic_ssn,
            "phone_number": realistic_phone,
            "email_address": synthetic_email,
            "medical_record_number": medical_record_number,
            "dob": random_date(datetime(1940, 1, 1), datetime(2020, 1, 1)).strftime("%Y-%m-%d"),
            "age": random.randint(18, 95),
            "gender": random.choice(["M", "F", "Other"]),
            "phone": fake.phone_number(),  # Keep original faker phone too
            "email": fake.email(),  # Keep original faker email too
            "address": fake.address().replace("\n", ", "),
            "insurance_provider": fake.insurance_provider(),
            "member_id": fake.member_id(),
            "primary_condition": fake.medical_condition(),
            "allergies": random.choice(["None", "Penicillin", "Shellfish", "Peanuts", "Latex"]),
            "emergency_contact": fake.name(),
            "emergency_phone": fake.phone_number(),
            "created_at": fake.date_time_between(start_date="-2y", end_date="now").isoformat(),
            # MANDATORY: Clear synthetic markers for compliance
            "synthetic_data": True,
            "data_source": "synthetic_healthcare_generator",
            "phi_testing_patterns": [
                "ssn",
                "phone_number",
                "email_address",
                "medical_record_number",
            ],
            "compliance_note": "Synthetic data for PHI detection testing - not real patient information",
        }

    def generate_doctor(self) -> dict[str, Any]:
        """Generate synthetic doctor data"""
        return {
            "id": str(uuid.uuid4()),
            "doctor_id": f"dr_{uuid.uuid4().hex[:8]}",
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "specialty": fake.medical_specialty(),
            "npi_number": fake.npi_number(),
            "email": fake.email(),
            "phone": fake.phone_number(),
            "years_experience": random.randint(1, 35),
            "preferred_communication_style": random.choice(["formal", "casual", "mixed"]),
            "license_number": f"MD{fake.random_number(digits=6)}",
            "hospital_affiliations": random.choice(
                [
                    "General Hospital",
                    "Regional Medical Center",
                    "University Hospital",
                    "Community Health Center",
                    "Specialty Clinic",
                ],
            ),
            "created_at": fake.date_time_between(start_date="-2y", end_date="now").isoformat(),
            "preferences": {
                "summary_style": random.choice(["detailed", "concise", "bullet_points"]),
                "preferred_note_format": random.choice(["soap", "dap", "narrative"]),
                "include_differential": random.choice([True, False]),
                "auto_generate_plan": random.choice([True, False]),
                "formality_level": random.choice(["formal", "casual", "mixed"]),
            },
        }

    def generate_encounter(self, patient_id: str, doctor_id: str) -> dict[str, Any]:
        """Generate synthetic encounter/visit data"""
        return {
            "encounter_id": str(uuid.uuid4()),
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "date": random_date(datetime(2023, 1, 1), datetime(2025, 7, 1)).strftime("%Y-%m-%d"),
            "time": fake.time(),
            "reason": fake.visit_reason(),
            "chief_complaint": random.choice(
                [
                    "Routine checkup",
                    "Feeling unwell",
                    "Follow-up appointment",
                    "Medication review",
                    "Preventive care",
                    "Acute symptoms",
                ],
            ),
            "duration_minutes": random.randint(15, 60),
            "visit_type": random.choice(["in-person", "telehealth", "phone"]),
            "notes": random.choice(
                [
                    "Patient doing well overall",
                    "Prescribed new medication",
                    "Needs follow-up in 3 months",
                    "Lab work ordered",
                    "Referral to specialist recommended",
                ],
            ),
            "diagnosis_codes": [f"Z{fake.random_number(digits=2)}.{fake.random_number(digits=1)}"],
            "vital_signs": {
                "blood_pressure_systolic": random.randint(90, 180),
                "blood_pressure_diastolic": random.randint(60, 120),
                "heart_rate": random.randint(60, 100),
                "temperature": round(random.uniform(97.0, 101.0), 1),
                "weight": random.randint(100, 300),
                "height": random.randint(60, 80),
            },
            "status": random.choice(["completed", "no-show", "cancelled", "rescheduled"]),
            "created_at": fake.date_time_between(start_date="-1y", end_date="now").isoformat(),
        }

    def generate_lab_result(self, patient_id: str) -> dict[str, Any]:
        """Generate synthetic lab result data"""
        lab_test = fake.lab_test()

        # Generate realistic values based on test type
        value_ranges = {
            "CBC": (4.0, 11.0, "K/uL"),
            "A1C": (4.0, 14.0, "%"),
            "HbA1c": (4.0, 14.0, "%"),
            "Lipid Panel": (120, 300, "mg/dL"),
            "Basic Metabolic Panel": (70, 200, "mg/dL"),
            "Vitamin D": (10, 80, "ng/mL"),
            "Thyroid Panel": (0.5, 5.0, "mIU/L"),
        }

        min_val, max_val, unit = value_ranges.get(lab_test, (1.0, 15.0, "mg/dL"))

        return {
            "result_id": str(uuid.uuid4()),
            "patient_id": patient_id,
            "test_name": lab_test,
            "date_ordered": random_date(datetime(2023, 1, 1), datetime(2025, 7, 1)).strftime(
                "%Y-%m-%d",
            ),
            "date_completed": random_date(datetime(2023, 1, 1), datetime(2025, 7, 1)).strftime(
                "%Y-%m-%d",
            ),
            "result_status": random.choice(["Normal", "Abnormal", "Critical", "Pending"]),
            "value": round(random.uniform(min_val, max_val), 2),
            "unit": unit,
            "reference_range": f"{min_val}-{max_val}",
            "ordering_physician": f"dr_{uuid.uuid4().hex[:8]}",
            "lab_facility": random.choice(
                ["Central Lab", "Hospital Lab", "Regional Testing Center", "Quick Lab"],
            ),
            "created_at": fake.date_time_between(start_date="-1y", end_date="now").isoformat(),
        }

    def generate_insurance_verification(self, patient_id: str) -> dict[str, Any]:
        """Generate synthetic insurance verification data"""
        return {
            "verification_id": str(uuid.uuid4()),
            "patient_id": patient_id,
            "insurance_provider": fake.insurance_provider(),
            "member_id": fake.member_id(),
            "group_number": f"GRP{fake.random_number(digits=6)}",
            "verification_date": fake.date_between(start_date="-30d", end_date="today").isoformat(),
            "eligibility_status": random.choice(["Active", "Inactive", "Pending", "Suspended"]),
            "coverage_type": random.choice(["HMO", "PPO", "EPO", "POS", "Medicare", "Medicaid"]),
            "copay_amount": random.choice([10, 15, 20, 25, 30, 35, 40]),
            "deductible_amount": random.choice([0, 500, 1000, 1500, 2000, 3000, 5000]),
            "deductible_met": random.choice([True, False]),
            "prior_auth_required": random.choice([True, False]),
            "effective_date": fake.date_between(start_date="-2y", end_date="today").strftime(
                "%Y-%m-%d",
            ),
            "termination_date": fake.date_between(start_date="today", end_date="+2y").strftime(
                "%Y-%m-%d",
            ),
            "verification_method": random.choice(["API", "Phone", "Web Portal", "Fax"]),
            "verified_by": fake.name(),
            "notes": random.choice(
                [
                    "Coverage verified successfully",
                    "Prior authorization required for specialists",
                    "High deductible plan",
                    "Coverage active, no issues",
                ],
            ),
        }

    def generate_agent_session(self, doctor_id: str) -> dict[str, Any]:
        """Generate synthetic AI agent session data for Phase 1"""
        return {
            "session_id": str(uuid.uuid4()),
            "doctor_id": doctor_id,
            "agent_type": random.choice(
                [
                    "intake_assistant",
                    "document_processor",
                    "research_assistant",
                    "scheduling_optimizer",
                    "billing_helper",
                ],
            ),
            "start_time": fake.date_time_between(start_date="-30d", end_date="now").isoformat(),
            "end_time": fake.date_time_between(start_date="-30d", end_date="now").isoformat(),
            "duration_seconds": random.randint(30, 1800),
            "messages_exchanged": random.randint(5, 50),
            "tokens_used": random.randint(500, 5000),
            "model_used": random.choice(["llama3.1:3b", "llama3.1:8b", "qwen2.5:7b"]),
            "session_outcome": random.choice(["completed", "interrupted", "error", "timeout"]),
            "user_satisfaction": random.randint(1, 5),
            "cost_usd": round(random.uniform(0.01, 0.50), 3),
            "created_at": fake.date_time_between(start_date="-30d", end_date="now").isoformat(),
        }

    def generate_billing_claim(
        self,
        patient_id: str,
        doctor_id: str,
        encounter_id: str,
    ) -> dict[str, Any]:
        """Generate synthetic billing claim for Phase 2 business automation"""
        return {
            "claim_id": f"CLM-{fake.random_number(digits=8)}",
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "encounter_id": encounter_id,
            "claim_amount": round(random.uniform(50.0, 2500.0), 2),
            "insurance_amount": round(random.uniform(30.0, 2000.0), 2),
            "patient_amount": round(random.uniform(10.0, 500.0), 2),
            "service_date": fake.date_between(start_date="-90d", end_date="today").isoformat(),
            "submitted_date": fake.date_between(start_date="-60d", end_date="today").isoformat(),
            "cpt_codes": random.sample(
                ["99213", "99214", "99215", "85025", "80053", "93000"],
                k=random.randint(1, 3),
            ),
            "diagnosis_codes": random.sample(
                ["Z00.00", "I10", "E11.9", "M79.3", "R50.9"],
                k=random.randint(1, 2),
            ),
            "claim_status": random.choice(
                ["submitted", "approved", "denied", "pending", "resubmitted"],
            ),
            "denial_reason": (
                random.choice(
                    [
                        None,
                        "Prior authorization required",
                        "Service not covered",
                        "Duplicate claim",
                    ],
                )
                if random.random() < 0.2
                else None
            ),
            "created_at": fake.date_time_between(start_date="-90d", end_date="now").isoformat(),
        }

    def generate_doctor_preferences(self, doctor_id: str) -> dict[str, Any]:
        """Generate doctor workflow preferences for LoRA personalization (Phase 2)"""
        return {
            "doctor_id": doctor_id,
            "documentation_style": random.choice(
                ["concise", "detailed", "bullet_points", "narrative"],
            ),
            "preferred_templates": random.sample(
                [
                    "chief_complaint_first",
                    "assessment_plan_focus",
                    "soap_format",
                    "problem_oriented",
                    "chronological",
                ],
                k=random.randint(2, 4),
            ),
            "ai_assistance_level": random.choice(["minimal", "moderate", "extensive"]),
            "auto_coding_preference": random.choice(["suggest_only", "auto_apply", "disabled"]),
            "alert_sensitivity": random.choice(["low", "medium", "high"]),
            "communication_style": random.choice(
                ["formal", "conversational", "brief", "empathetic"],
            ),
            "typical_appointment_duration": random.randint(10, 45),
            "specialization_focus": random.choice(
                [
                    "preventive_care",
                    "chronic_disease",
                    "acute_care",
                    "pediatrics",
                    "geriatrics",
                    "mental_health",
                ],
            ),
            "created_at": fake.date_time_between(start_date="-365d", end_date="now").isoformat(),
            "updated_at": fake.date_time_between(start_date="-30d", end_date="now").isoformat(),
        }

    def generate_audit_log(self, user_id: str, user_type: str = "doctor") -> dict[str, Any]:
        """Generate audit log entries for HIPAA compliance (Phase 2)"""
        actions = {
            "doctor": [
                "view_patient",
                "update_notes",
                "order_lab",
                "prescribe_medication",
                "schedule_appointment",
            ],
            "staff": [
                "schedule_appointment",
                "update_insurance",
                "process_payment",
                "view_patient_summary",
            ],
            "system": [
                "backup_completed",
                "login_attempt",
                "password_change",
                "export_data",
            ],
        }

        return {
            "log_id": str(uuid.uuid4()),
            "user_id": user_id,
            "user_type": user_type,
            "action": random.choice(actions.get(user_type, actions["system"])),
            "resource_type": random.choice(
                [
                    "patient_record",
                    "appointment",
                    "billing",
                    "lab_result",
                    "system_config",
                ],
            ),
            "resource_id": f"RES-{fake.random_number(digits=6)}",
            "ip_address": fake.ipv4_private(),
            "user_agent": fake.user_agent(),
            "timestamp": fake.date_time_between(start_date="-30d", end_date="now").isoformat(),
            "success": random.choice([True, True, True, False]),  # 75% success rate
            "error_message": (
                random.choice([None, "Access denied", "Resource not found", "Timeout"])
                if random.random() < 0.25
                else None
            ),
            "session_id": str(uuid.uuid4()),
        }

    def generate_compliance_violation(self, user_id: str, violation_type: str = None) -> dict[str, Any]:
        """Generate compliance violation events for testing compliance monitoring"""
        violation_types = [
            "unauthorized_phi_access",
            "phi_disclosure_without_consent",
            "access_outside_work_hours",
            "bulk_patient_access",
            "suspicious_login_pattern",
            "failed_authentication_attempts",
            "data_export_without_approval",
            "patient_record_modification_after_hours",
        ]

        return {
            "violation_id": f"VIO_{fake.random_number(digits=6)}",
            "user_id": user_id,
            "violation_type": violation_type or random.choice(violation_types),
            "severity": random.choice(["low", "medium", "high", "critical"]),
            "detected_at": fake.date_time_between(start_date="-30d", end_date="now").isoformat(),
            "resource_accessed": f"patient_{fake.random_number(digits=6)}",
            "violation_details": {
                "action_attempted": random.choice(["VIEW", "EDIT", "DELETE", "EXPORT", "PRINT"]),
                "location": fake.ipv4(),
                "device_info": fake.user_agent(),
                "time_of_access": fake.time(),
            },
            "auto_detected": random.choice([True, False]),
            "resolved": random.choice([True, False]),
            "resolution_notes": fake.sentence() if random.random() > 0.5 else None,
        }

    def generate_analytics_metrics(self, date: str = None) -> dict[str, Any]:
        """Generate analytics metrics for business intelligence testing"""
        target_date = date or fake.date_between(start_date="-90d", end_date="today").isoformat()

        return {
            "metric_id": str(uuid.uuid4()),
            "date": target_date,
            "revenue_metrics": {
                "total_revenue": round(random.uniform(5000.0, 25000.0), 2),
                "claims_processed": random.randint(50, 200),
                "average_claim_value": round(random.uniform(100.0, 500.0), 2),
                "collection_rate": round(random.uniform(0.75, 0.95), 3),
            },
            "operational_metrics": {
                "patient_visits": random.randint(75, 300),
                "average_wait_time": random.randint(5, 45),
                "provider_utilization": round(random.uniform(0.60, 0.95), 3),
                "no_show_rate": round(random.uniform(0.05, 0.20), 3),
            },
            "compliance_metrics": {
                "compliance_score": round(random.uniform(85.0, 99.5), 1),
                "violations_detected": random.randint(0, 5),
                "audit_events": random.randint(100, 500),
                "phi_access_events": random.randint(200, 800),
            },
            "quality_metrics": {
                "patient_satisfaction": round(random.uniform(3.5, 5.0), 1),
                "readmission_rate": round(random.uniform(0.02, 0.15), 3),
                "medication_adherence": round(random.uniform(0.70, 0.95), 3),
            },
        }

    def generate_personalization_training_data(self, doctor_id: str) -> dict[str, Any]:
        """Generate personalization training data for LoRA adaptation"""
        return {
            "training_id": str(uuid.uuid4()),
            "doctor_id": doctor_id,
            "interaction_type": random.choice([
                "patient_note_generation",
                "diagnosis_assistance",
                "treatment_recommendation",
                "medication_review",
                "clinical_decision_support",
            ]),
            "input_text": fake.text(max_nb_chars=500),
            "preferred_output": fake.text(max_nb_chars=300),
            "feedback_score": random.choice([1, 2, 3, 4, 5]),
            "interaction_date": fake.date_time_between(start_date="-60d", end_date="now").isoformat(),
            "session_context": {
                "patient_specialty": random.choice(["cardiology", "dermatology", "family_medicine", "pediatrics"]),
                "documentation_style": random.choice(["concise", "detailed", "bullet_points"]),
                "clinical_complexity": random.choice(["simple", "moderate", "complex"]),
            },
            "model_version": f"v{random.randint(1, 5)}.{random.randint(0, 9)}",
            "adaptation_score": round(random.uniform(6.0, 10.0), 1),
        }

    def generate_service_communication_log(self, from_service: str, to_service: str) -> dict[str, Any]:
        """Generate service-to-service communication logs for integration testing"""

        return {
            "log_id": str(uuid.uuid4()),
            "from_service": from_service,
            "to_service": to_service,
            "request_method": random.choice(["GET", "POST", "PUT", "DELETE"]),
            "endpoint": f"/{random.choice(['health', 'verify', 'process', 'analyze', 'generate'])}",
            "request_time": fake.date_time_between(start_date="-7d", end_date="now").isoformat(),
            "response_time": fake.date_time_between(start_date="-7d", end_date="now").isoformat(),
            "duration_ms": random.randint(10, 5000),
            "status_code": random.choice([200, 201, 400, 401, 404, 500, 502, 503]),
            "request_size_bytes": random.randint(100, 10000),
            "response_size_bytes": random.randint(50, 50000),
            "user_id": f"user_{fake.random_number(digits=6)}",
            "correlation_id": str(uuid.uuid4()),
            "circuit_breaker_state": random.choice(["CLOSED", "OPEN", "HALF_OPEN"]),
            "retry_count": random.randint(0, 3),
        }

    def generate_all_data(self) -> None:
        """Generate all synthetic data types"""
        print("🏥 Generating comprehensive synthetic healthcare data...")

        # Generate core entities
        print("\n👨‍⚕️ Generating doctors...")
        self.doctors = [self.generate_doctor() for _ in range(self.num_doctors)]

        print("👥 Generating patients...")
        self.patients = [self.generate_patient() for _ in range(self.num_patients)]

        print("📋 Generating encounters...")
        for _ in range(self.num_encounters):
            patient = random.choice(self.patients)
            doctor = random.choice(self.doctors)
            encounter = self.generate_encounter(patient["patient_id"], doctor["doctor_id"])
            self.encounters.append(encounter)

        print("🧪 Generating lab results...")
        for patient in self.patients:
            # Each patient gets 1-3 lab results
            for _ in range(random.randint(1, 3)):
                lab_result = self.generate_lab_result(patient["patient_id"])
                self.lab_results.append(lab_result)

        print("🏥 Generating insurance verifications...")
        for patient in self.patients:
            verification = self.generate_insurance_verification(patient["patient_id"])
            self.insurance_verifications.append(verification)

        print("🤖 Generating AI agent sessions...")
        for doctor in self.doctors:
            # Each doctor gets 5-15 agent sessions
            for _ in range(random.randint(5, 15)):
                session = self.generate_agent_session(doctor["doctor_id"])
                self.agent_sessions.append(session)

        # Phase 2 Business Data Generation
        print("\n💼 Generating Phase 2 business data...")

        print("💰 Generating billing claims...")
        for encounter in self.encounters:
            # 80% of encounters generate billing claims
            if random.random() < 0.8:
                claim = self.generate_billing_claim(
                    encounter["patient_id"],
                    encounter["doctor_id"],
                    encounter["encounter_id"],
                )
                self.billing_claims.append(claim)

        print("⚙️ Generating doctor preferences...")
        for doctor in self.doctors:
            preferences = self.generate_doctor_preferences(doctor["doctor_id"])
            self.doctor_preferences.append(preferences)

        print("📋 Generating audit logs...")
        # Generate audit logs for all doctors and some system events
        for doctor in self.doctors:
            # Each doctor gets 10-30 audit log entries
            for _ in range(random.randint(10, 30)):
                audit_log = self.generate_audit_log(doctor["doctor_id"], "doctor")
                self.audit_logs.append(audit_log)

        # Add some system audit logs
        for _ in range(random.randint(20, 50)):
            audit_log = self.generate_audit_log("system", "system")
            self.audit_logs.append(audit_log)

        print("\n🔧 Generating business services data...")

        print("⚠️ Generating compliance violations...")
        # Generate some compliance violations for testing
        all_users = [doc["doctor_id"] for doc in self.doctors] + ["system"]
        for _ in range(random.randint(5, 20)):
            user_id = random.choice(all_users)
            violation = self.generate_compliance_violation(user_id)
            self.compliance_violations.append(violation)

        print("📊 Generating analytics metrics...")
        # Generate daily analytics for the past 30 days
        for i in range(30):
            date_str = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            metrics = self.generate_analytics_metrics(date_str)
            self.analytics_metrics.append(metrics)

        print("🤖 Generating personalization training data...")
        # Generate training data for each doctor
        for doctor in self.doctors:
            for _ in range(random.randint(10, 30)):
                training_data = self.generate_personalization_training_data(doctor["doctor_id"])
                self.personalization_training_data.append(training_data)

        print("🔗 Generating service communication logs...")
        # Generate service-to-service communication logs
        services = [
            "healthcare-api", "insurance-verification", "billing-engine",
            "compliance-monitor", "business-intelligence", "doctor-personalization",
        ]
        for _ in range(random.randint(100, 300)):
            from_service = random.choice(services)
            to_service = random.choice([s for s in services if s != from_service])
            comm_log = self.generate_service_communication_log(from_service, to_service)
            self.service_communication_logs.append(comm_log)

        # Save to JSON files
        self._save_json_files()

        # Optionally populate databases
        if self.use_database:
            self._populate_databases()

        print("\n✅ Synthetic data generation complete!")
        print("📊 Generated:")
        print("   📋 Phase 1 Core Data:")
        print(f"     - {len(self.doctors)} doctors")
        print(f"     - {len(self.patients)} patients")
        print(f"     - {len(self.encounters)} encounters")
        print(f"     - {len(self.lab_results)} lab results")
        print(f"     - {len(self.insurance_verifications)} insurance verifications")
        print(f"     - {len(self.agent_sessions)} AI agent sessions")
        print("   💼 Phase 2 Business Data:")
        print(f"     - {len(self.billing_claims)} billing claims")
        print(f"     - {len(self.doctor_preferences)} doctor preferences")
        print(f"     - {len(self.audit_logs)} audit log entries")
        print("   🔧 Business Services Data:")
        print(f"     - {len(self.compliance_violations)} compliance violations")
        print(f"     - {len(self.analytics_metrics)} analytics metrics")
        print(f"     - {len(self.personalization_training_data)} personalization training records")
        print(f"     - {len(self.service_communication_logs)} service communication logs")
        print(f"📁 Files saved to: {self.output_dir}/")

    def _save_json_files(self) -> None:
        """Save all generated data to JSON files"""
        datasets = {
            # Phase 1 Core Data
            "doctors": self.doctors,
            "patients": self.patients,
            "encounters": self.encounters,
            "lab_results": self.lab_results,
            "insurance_verifications": self.insurance_verifications,
            "agent_sessions": self.agent_sessions,
            # Phase 2 Business Data
            "billing_claims": self.billing_claims,
            "doctor_preferences": self.doctor_preferences,
            "audit_logs": self.audit_logs,
            # Business Services Data
            "compliance_violations": self.compliance_violations,
            "analytics_metrics": self.analytics_metrics,
            "personalization_training_data": self.personalization_training_data,
            "service_communication_logs": self.service_communication_logs,
        }

        for name, data in datasets.items():
            filepath = os.path.join(self.output_dir, f"{name}.json")
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2, default=str)
            print(f"💾 Saved {filepath} ({len(data)} records)")

    def _populate_databases(self) -> None:
        """Populate PostgreSQL and Redis with generated data"""
        print("\n🗄️  Populating databases...")

        # Populate Redis with session data
        if self.redis_client:
            for session in self.agent_sessions:
                key = f"session:{session['session_id']}"
                self.redis_client.hset(key, mapping=session)
                # Set expiration for session data (30 days)
                self.redis_client.expire(key, 30 * 24 * 60 * 60)
            print(f"✅ Populated Redis with {len(self.agent_sessions)} sessions")

        # Populate PostgreSQL with healthcare data using SQLAlchemy models
        if self.db_conn:
            self._populate_postgresql()
        else:
            print("⚠️  PostgreSQL connection not available, skipping PostgreSQL population")

    def _populate_postgresql(self) -> None:
        """Populate PostgreSQL with all healthcare data using SQLAlchemy models"""
        try:
            # Import healthcare models
            import os
            import sys

            sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
            from core.models.healthcare import (
                AgentSession,
                AuditLog,
                BillingClaim,
                Doctor,
                DoctorPreferences,
                Encounter,
                InsuranceVerification,
                LabResult,
                Patient,
                get_healthcare_session,
                init_healthcare_database,
            )

            # Initialize database tables
            if not init_healthcare_database():
                print("❌ Failed to initialize healthcare database")
                return

            # Get database session
            session = get_healthcare_session()

            try:
                print("📋 Populating PostgreSQL tables...")

                # Populate doctors
                for doctor_data in self.doctors:
                    # Remove fields that don't belong in the Doctor model
                    doctor_dict = {
                        k: v for k, v in doctor_data.items() if k not in ["id", "preferences"]
                    }
                    doctor = Doctor(**doctor_dict)
                    session.add(doctor)
                session.commit()
                print(f"✅ Populated {len(self.doctors)} doctors")

                # Populate patients
                for patient_data in self.patients:
                    # Map fields and remove conflicts for Patient model
                    patient_dict = {}
                    for k, v in patient_data.items():
                        if k == "phone_number":
                            patient_dict["phone"] = v  # Map phone_number to phone
                        elif k == "email_address":
                            patient_dict["email"] = v  # Map email_address to email
                        elif k == "dob":
                            patient_dict["date_of_birth"] = v  # Map dob to date_of_birth
                        elif k == "address":
                            patient_dict["address_line1"] = v  # Map address to address_line1
                        elif k == "emergency_contact":
                            patient_dict["emergency_contact_name"] = v
                        elif k == "emergency_phone":
                            patient_dict["emergency_contact_phone"] = v
                        elif k == "member_id":
                            patient_dict["insurance_member_id"] = v
                        elif k not in [
                            "id",
                            "age",
                            "gender",
                            "primary_condition",
                            "allergies",
                            "synthetic_data",
                            "data_source",
                            "phi_testing_patterns",
                        ]:
                            # Only include fields that exist in the Patient model
                            if k in [
                                "patient_id",
                                "first_name",
                                "last_name",
                                "ssn",
                                "phone",
                                "email",
                                "address_line1",
                                "address_line2",
                                "city",
                                "state",
                                "zip_code",
                                "emergency_contact_name",
                                "emergency_contact_phone",
                                "insurance_provider",
                                "insurance_member_id",
                                "insurance_group_number",
                                "medical_record_number",
                                "date_of_birth",
                                "created_at",
                            ]:
                                patient_dict[k] = v

                    patient = Patient(**patient_dict)
                    session.add(patient)
                session.commit()
                print(f"✅ Populated {len(self.patients)} patients")

                # Populate encounters
                for encounter_data in self.encounters:
                    # Convert nested vital_signs to JSON string and remove id field
                    encounter_dict = {k: v for k, v in encounter_data.items() if k not in ["id"]}

                    # Handle vital_signs nested object
                    if "vital_signs" in encounter_dict:
                        import json

                        encounter_dict["vital_signs_json"] = json.dumps(
                            encounter_dict["vital_signs"],
                        )
                        del encounter_dict["vital_signs"]

                    encounter = Encounter(**encounter_dict)
                    session.add(encounter)
                session.commit()
                print(f"✅ Populated {len(self.encounters)} encounters")

                # Populate lab results
                for lab_data in self.lab_results:
                    # Remove fields that don't belong in the LabResult model
                    lab_dict = {k: v for k, v in lab_data.items() if k not in ["id"]}
                    lab_result = LabResult(**lab_dict)
                    session.add(lab_result)
                session.commit()
                print(f"✅ Populated {len(self.lab_results)} lab results")

                # Populate insurance verifications
                for insurance_data in self.insurance_verifications:
                    # Remove fields that don't belong in the InsuranceVerification model
                    insurance_dict = {k: v for k, v in insurance_data.items() if k not in ["id"]}
                    insurance = InsuranceVerification(**insurance_dict)
                    session.add(insurance)
                session.commit()
                print(f"✅ Populated {len(self.insurance_verifications)} insurance verifications")

                # Populate billing claims
                for claim_data in self.billing_claims:
                    # Remove fields that don't belong in the BillingClaim model
                    claim_dict = {k: v for k, v in claim_data.items() if k not in ["id"]}
                    claim = BillingClaim(**claim_dict)
                    session.add(claim)
                session.commit()
                print(f"✅ Populated {len(self.billing_claims)} billing claims")

                # Populate doctor preferences (from doctor preferences list, not nested data)
                for pref_data in self.doctor_preferences:
                    # Remove fields that don't belong in the DoctorPreferences model
                    pref_dict = {k: v for k, v in pref_data.items() if k not in ["id"]}
                    prefs = DoctorPreferences(**pref_dict)
                    session.add(prefs)
                session.commit()
                print(f"✅ Populated {len(self.doctor_preferences)} doctor preferences")

                # Populate audit logs
                for audit_data in self.audit_logs:
                    # Remove fields that don't belong in the AuditLog model
                    audit_dict = {k: v for k, v in audit_data.items() if k not in ["id"]}
                    audit = AuditLog(**audit_dict)
                    session.add(audit)
                session.commit()
                print(f"✅ Populated {len(self.audit_logs)} audit logs")

                # Populate agent sessions
                for session_data in self.agent_sessions:
                    # Remove fields that don't belong in the AgentSession model
                    session_dict = {k: v for k, v in session_data.items() if k not in ["id"]}
                    agent_session = AgentSession(**session_dict)
                    session.add(agent_session)
                session.commit()
                print(f"✅ Populated {len(self.agent_sessions)} agent sessions")

                print("🎉 PostgreSQL population completed successfully!")

            except Exception as e:
                session.rollback()
                print(f"❌ Error populating PostgreSQL: {e}")
                raise
            finally:
                session.close()

        except ImportError as e:
            print(f"❌ Failed to import healthcare models: {e}")
            print("   Make sure core.models.healthcare is in Python path")
        except Exception as e:
            print(f"❌ PostgreSQL population failed: {e}")


def main() -> None:
    """Main execution function"""
    import argparse

    parser = argparse.ArgumentParser(description="Generate synthetic healthcare data")
    parser.add_argument("--doctors", type=int, default=25, help="Number of doctors to generate")
    parser.add_argument("--patients", type=int, default=100, help="Number of patients to generate")
    parser.add_argument(
        "--encounters",
        type=int,
        default=300,
        help="Number of encounters to generate",
    )
    parser.add_argument(
        "--output-dir",
        default="data/synthetic",
        help="Output directory for JSON files",
    )
    parser.add_argument("--use-database", action="store_true", help="Also populate databases")

    args = parser.parse_args()

    generator = SyntheticHealthcareDataGenerator(
        num_doctors=args.doctors,
        num_patients=args.patients,
        num_encounters=args.encounters,
        output_dir=args.output_dir,
        use_database=args.use_database,
    )

    generator.generate_all_data()


if __name__ == "__main__":
    main()
