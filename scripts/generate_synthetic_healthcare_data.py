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

# Optional database dependencies with graceful fallback
try:
    import psycopg2
    from psycopg2.extensions import connection as PgConnection

    PSYCOPG2_AVAILABLE = True
except ImportError:
    psycopg2 = None
    PgConnection = None
    PSYCOPG2_AVAILABLE = False
    print("⚠️  psycopg2 not available - database population will be skipped")

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False
    print("⚠️  redis not available - Redis caching will be skipped")

from faker import Faker
from faker.providers import BaseProvider

# Initialize Faker with healthcare-specific providers
fake = Faker()


def random_date(start, end):
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

    def medical_specialty(self):
        return self.random_element(self.medical_specialties)

    def insurance_provider(self):
        return self.random_element(self.insurance_providers)

    def medical_condition(self):
        return self.random_element(self.medical_conditions)

    def lab_test(self):
        return self.random_element(self.lab_tests)

    def visit_reason(self):
        return self.random_element(self.visit_reasons)

    def member_id(self):
        """Generate realistic member ID"""
        return f"{fake.random_element(['A', 'B', 'C', 'H', 'U'])}{fake.random_number(digits=9)}"

    def npi_number(self):
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

        # Database connections (optional)
        self.db_conn = None
        self.redis_client = None

        if self.use_database:
            self._connect_to_databases()

    def _connect_to_databases(self):
        """Connect to PostgreSQL and Redis if using database mode"""
        if not PSYCOPG2_AVAILABLE or psycopg2 is None:
            print("⚠️  psycopg2 not available - skipping PostgreSQL connection")
            self.db_conn = None
        else:
            try:
                self.db_conn = psycopg2.connect(
                    "postgresql://intelluxe:secure_password@localhost:5432/intelluxe"
                )
                print("✅ Connected to PostgreSQL")
            except Exception as e:
                print(f"⚠️  PostgreSQL connection failed: {e}")
                self.db_conn = None

        if not REDIS_AVAILABLE or redis is None:
            print("⚠️  redis not available - skipping Redis connection")
            self.redis_client = None
        else:
            try:
                self.redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)
                self.redis_client.ping()
                print("✅ Connected to Redis")
            except Exception as e:
                print(f"⚠️  Redis connection failed: {e}")
                self.redis_client = None

    def generate_patient(self):
        """Generate synthetic patient data"""
        return {
            "id": str(uuid.uuid4()),
            "patient_id": f"pt_{uuid.uuid4().hex[:8]}",
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "dob": random_date(datetime(1940, 1, 1), datetime(2020, 1, 1)).strftime("%Y-%m-%d"),
            "age": random.randint(18, 95),
            "gender": random.choice(["M", "F", "Other"]),
            "phone": fake.phone_number(),
            "email": fake.email(),
            "address": fake.address().replace("\n", ", "),
            "insurance_provider": fake.insurance_provider(),
            "member_id": fake.member_id(),
            "primary_condition": fake.medical_condition(),
            "allergies": random.choice(["None", "Penicillin", "Shellfish", "Peanuts", "Latex"]),
            "emergency_contact": fake.name(),
            "emergency_phone": fake.phone_number(),
            "created_at": fake.date_time_between(start_date="-2y", end_date="now").isoformat(),
        }

    def generate_doctor(self):
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
                ]
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

    def generate_encounter(self, patient_id: str, doctor_id: str):
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
                ]
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
                ]
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

    def generate_lab_result(self, patient_id: str):
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
                "%Y-%m-%d"
            ),
            "date_completed": random_date(datetime(2023, 1, 1), datetime(2025, 7, 1)).strftime(
                "%Y-%m-%d"
            ),
            "result_status": random.choice(["Normal", "Abnormal", "Critical", "Pending"]),
            "value": round(random.uniform(min_val, max_val), 2),
            "unit": unit,
            "reference_range": f"{min_val}-{max_val}",
            "ordering_physician": f"dr_{uuid.uuid4().hex[:8]}",
            "lab_facility": random.choice(
                ["Central Lab", "Hospital Lab", "Regional Testing Center", "Quick Lab"]
            ),
            "created_at": fake.date_time_between(start_date="-1y", end_date="now").isoformat(),
        }

    def generate_insurance_verification(self, patient_id: str):
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
                "%Y-%m-%d"
            ),
            "termination_date": fake.date_between(start_date="today", end_date="+2y").strftime(
                "%Y-%m-%d"
            ),
            "verification_method": random.choice(["API", "Phone", "Web Portal", "Fax"]),
            "verified_by": fake.name(),
            "notes": random.choice(
                [
                    "Coverage verified successfully",
                    "Prior authorization required for specialists",
                    "High deductible plan",
                    "Coverage active, no issues",
                ]
            ),
        }

    def generate_agent_session(self, doctor_id: str):
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
                ]
            ),
            "start_time": fake.date_time_between(start_date="-30d", end_date="now").isoformat(),
            "end_time": fake.date_time_between(start_date="-30d", end_date="now").isoformat(),
            "duration_seconds": random.randint(30, 1800),
            "messages_exchanged": random.randint(5, 50),
            "tokens_used": random.randint(500, 5000),
            "model_used": random.choice(["llama3.2:3b", "llama3.2:8b", "qwen2.5:7b"]),
            "session_outcome": random.choice(["completed", "interrupted", "error", "timeout"]),
            "user_satisfaction": random.randint(1, 5),
            "cost_usd": round(random.uniform(0.01, 0.50), 3),
            "created_at": fake.date_time_between(start_date="-30d", end_date="now").isoformat(),
        }

    def generate_billing_claim(self, patient_id: str, doctor_id: str, encounter_id: str):
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
                ["Z00.00", "I10", "E11.9", "M79.3", "R50.9"], k=random.randint(1, 2)
            ),
            "claim_status": random.choice(
                ["submitted", "approved", "denied", "pending", "resubmitted"]
            ),
            "denial_reason": (
                random.choice(
                    [
                        None,
                        "Prior authorization required",
                        "Service not covered",
                        "Duplicate claim",
                    ]
                )
                if random.random() < 0.2
                else None
            ),
            "created_at": fake.date_time_between(start_date="-90d", end_date="now").isoformat(),
        }

    def generate_doctor_preferences(self, doctor_id: str):
        """Generate doctor workflow preferences for LoRA personalization (Phase 2)"""
        return {
            "doctor_id": doctor_id,
            "documentation_style": random.choice(
                ["concise", "detailed", "bullet_points", "narrative"]
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
                ["formal", "conversational", "brief", "empathetic"]
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
                ]
            ),
            "created_at": fake.date_time_between(start_date="-365d", end_date="now").isoformat(),
            "updated_at": fake.date_time_between(start_date="-30d", end_date="now").isoformat(),
        }

    def generate_audit_log(self, user_id: str, user_type: str = "doctor"):
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
                ]
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

    def generate_all_data(self):
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
        print(f"📁 Files saved to: {self.output_dir}/")

    def _save_json_files(self):
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
        }

        for name, data in datasets.items():
            filepath = os.path.join(self.output_dir, f"{name}.json")
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2, default=str)
            print(f"💾 Saved {filepath} ({len(data)} records)")

    def _populate_databases(self):
        """Populate PostgreSQL and Redis with generated data"""
        if not self.db_conn:
            print("⚠️  Database connection not available, skipping database population")
            return

        print("\n🗄️  Populating databases...")

        # Example: Populate Redis with session data
        if self.redis_client:
            for session in self.agent_sessions:
                key = f"session:{session['session_id']}"
                self.redis_client.hset(key, mapping=session)
                # Set expiration for session data (30 days)
                self.redis_client.expire(key, 30 * 24 * 60 * 60)
            print(f"✅ Populated Redis with {len(self.agent_sessions)} sessions")

        # Example: Create simple tables and populate PostgreSQL
        # (This would require actual table schemas in a real implementation)
        print("ℹ️  PostgreSQL population requires schema setup - skipping for now")


def main():
    """Main execution function"""
    import argparse

    parser = argparse.ArgumentParser(description="Generate synthetic healthcare data")
    parser.add_argument("--doctors", type=int, default=25, help="Number of doctors to generate")
    parser.add_argument("--patients", type=int, default=100, help="Number of patients to generate")
    parser.add_argument(
        "--encounters", type=int, default=300, help="Number of encounters to generate"
    )
    parser.add_argument(
        "--output-dir", default="data/synthetic", help="Output directory for JSON files"
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
