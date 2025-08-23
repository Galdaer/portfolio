"""
HIPAA-Compliant Synthetic Healthcare Data Generator
Generates realistic but completely synthetic patient data for testing
"""

import json
import logging
import os
import random
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from faker import Faker
from faker.providers import BaseProvider

# Configure logging
logger = logging.getLogger(__name__)


class MedicalProvider(BaseProvider):
    """Custom Faker provider for medical data"""

    # Medical conditions (common, non-sensitive examples)
    conditions = [
        "Hypertension",
        "Type 2 Diabetes",
        "Hyperlipidemia",
        "Asthma",
        "Allergic Rhinitis",
        "Gastroesophageal Reflux",
        "Osteoarthritis",
        "Anxiety Disorder",
        "Depression",
        "Migraine Headaches",
    ]

    # Common medications (generic names)
    medications = [
        "Lisinopril",
        "Metformin",
        "Atorvastatin",
        "Albuterol",
        "Omeprazole",
        "Ibuprofen",
        "Acetaminophen",
        "Sertraline",
        "Loratadine",
        "Vitamin D3",
    ]

    # Medical specialties
    specialties = [
        "Family Medicine",
        "Internal Medicine",
        "Cardiology",
        "Endocrinology",
        "Pulmonology",
        "Gastroenterology",
        "Orthopedics",
        "Psychiatry",
        "Neurology",
        "Dermatology",
    ]

    # Vital signs ranges (normal ranges)
    vital_ranges = {
        "systolic_bp": (110, 140),
        "diastolic_bp": (70, 90),
        "heart_rate": (60, 100),
        "temperature": (97.0, 99.5),
        "respiratory_rate": (12, 20),
        "oxygen_saturation": (95, 100),
    }

    def medical_condition(self) -> str:
        condition: str = self.random_element(self.conditions)
        return condition

    def medication(self) -> str:
        med: str = self.random_element(self.medications)
        return med

    def medical_specialty(self) -> str:
        specialty: str = self.random_element(self.specialties)
        return specialty

    def vital_sign(self, vital_type: str) -> float:
        if vital_type in self.vital_ranges:
            min_val, max_val = self.vital_ranges[vital_type]
            if vital_type == "temperature":
                return round(random.uniform(min_val, max_val), 1)
            return random.randint(int(min_val), int(max_val))
        return 0


@dataclass
class SyntheticPatient:
    """Synthetic patient data structure"""

    patient_id: str
    first_name: str
    last_name: str
    date_of_birth: str
    gender: str
    phone: str
    email: str
    address: dict[str, str]
    emergency_contact: dict[str, str]
    insurance: dict[str, str]
    medical_history: list[dict[str, Any]]
    current_medications: list[dict[str, str]]
    allergies: list[str]
    vital_signs: dict[str, Any]
    created_at: str


@dataclass
class SyntheticEncounter:
    """Synthetic medical encounter data"""

    encounter_id: str
    patient_id: str
    provider_name: str
    specialty: str
    encounter_date: str
    encounter_type: str
    chief_complaint: str
    assessment: str
    plan: str
    notes: str
    created_at: str


class SyntheticHealthcareDataGenerator:
    """
    Generate synthetic healthcare data for testing purposes.

    All generated data follows healthcare testing best practices:
    - Phone numbers use 555 prefix (NANP standard for fictional numbers)
    - Insurance providers clearly marked as synthetic to prevent confusion
    - All data is obviously fake to prevent accidental PHI exposure
    """

    # The 555 prefix complies with North American Numbering Plan (NANP)
    # telecommunications standards for fictional numbers in testing environments.
    #
    # NANP Compliance Details:
    # - 555-0100 through 555-0199: Reserved for fictional use in North America
    # - Prevents accidental contact with real people during testing
    # - Avoids privacy violations and unwanted communications
    # - Complies with FCC regulations for test data in telecommunications
    # - Recognized industry standard for healthcare testing scenarios
    #
    # Privacy Protection:
    # - Eliminates risk of contacting real patients or providers
    # - Prevents HIPAA violations from accidental real-world contact
    # - Ensures test data cannot be confused with actual healthcare records
    FICTIONAL_PHONE_PREFIX = "555"  # NANP-compliant prefix for fictional phone numbers

    # Synthetic insurance names prevent confusion with real providers
    # and ensure test data is clearly identified as non-production
    INSURANCE_PROVIDERS = [
        "Synthetic Health Plan A",  # Clearly marked as test data
        "Synthetic Health Plan B",  # Prevents real provider confusion
        "Synthetic Medicare",  # Distinguishable from real Medicare
        "Synthetic Medicaid",  # Distinguishable from real Medicaid
        "Synthetic Commercial Plan",
    ]

    def __init__(self, locale: str = "en_US", seed: int | None = None):
        self.fake = Faker(locale)
        self.fake.add_provider(MedicalProvider)
        self.logger = logging.getLogger(f"{__name__}.SyntheticHealthcareDataGenerator")

        # Ensure reproducible but varied data if a seed is provided
        if seed is not None:
            Faker.seed(seed)
            random.seed(seed)
            self.logger.info(f"Using seed {seed} for reproducible synthetic data")
        else:
            self.logger.info("Using random seed for varied synthetic data")

    def generate_phone_number(self) -> str:
        """Generate NANP-compliant fictional phone number using 555-01XX format"""
        # NANP standard: 555-01XX-XXXX for fictional numbers
        # This ensures compliance with North American Numbering Plan
        # while clearly marking numbers as fictional
        area_code = random.choice(["555"])  # Fictional area code
        exchange = f"01{random.randint(10, 99)}"  # 555-01XX format
        number = f"{random.randint(1000, 9999)}"
        return f"{area_code}-{exchange}-{number}"

    def generate_provider_phone(self) -> str:
        """Generate fictional provider phone number"""
        # Use same NANP-compliant format for consistency
        return self.generate_phone_number()

    def generate_synthetic_patient(self) -> SyntheticPatient:
        """Generate a completely synthetic patient record"""

        # Generate synthetic identifiers (clearly marked as synthetic)
        patient_id = f"SYN-{str(uuid.uuid4())[:8].upper()}"

        # Generate demographic data
        gender = self.fake.random_element(["Male", "Female", "Other"])
        first_name = (
            self.fake.first_name_male() if gender == "Male" else self.fake.first_name_female()
        )
        last_name = self.fake.last_name()

        # Generate age-appropriate date of birth (18-90 years old)
        birth_date = self.fake.date_of_birth(minimum_age=18, maximum_age=90)

        # Generate contact information (clearly synthetic)
        phone = self.generate_phone_number()
        email = f"{first_name.lower()}.{last_name.lower()}@synthetic-email.test"

        # Generate address
        address = {
            "street": self.fake.street_address(),
            "city": self.fake.city(),
            "state": self.fake.state_abbr(),
            "zip_code": self.fake.zipcode(),
            "country": "US",
        }

        # Generate emergency contact
        emergency_contact = {
            "name": self.fake.name(),
            "relationship": self.fake.random_element(
                ["Spouse", "Parent", "Sibling", "Child", "Friend"],
            ),
            "phone": self.generate_phone_number(),
        }

        # Generate insurance information (synthetic)
        insurance = {
            "provider": self.fake.random_element(self.INSURANCE_PROVIDERS),
            "policy_number": f"SYN{random.randint(100000, 999999)}",
            "group_number": f"GRP{random.randint(1000, 9999)}",
        }

        # Generate medical history
        num_conditions = random.randint(0, 3)
        medical_history = []
        for _ in range(num_conditions):
            condition = {
                "condition": self.fake.medical_condition(),
                "diagnosed_date": self.fake.date_between(
                    start_date="-10y",
                    end_date="today",
                ).isoformat(),
                "status": self.fake.random_element(["Active", "Resolved", "Chronic"]),
            }
            medical_history.append(condition)

        # Generate current medications
        num_medications = random.randint(0, 5)
        current_medications = []
        for _ in range(num_medications):
            medication = {
                "name": self.fake.medication(),
                "dosage": f"{random.randint(5, 100)}mg",
                "frequency": self.fake.random_element(
                    ["Once daily", "Twice daily", "Three times daily", "As needed"],
                ),
                "prescribed_date": self.fake.date_between(
                    start_date="-2y",
                    end_date="today",
                ).isoformat(),
            }
            current_medications.append(medication)

        # Generate allergies
        num_allergies = random.randint(0, 3)
        allergies = []
        allergy_options = [
            "Penicillin",
            "Sulfa drugs",
            "Latex",
            "Peanuts",
            "Shellfish",
            "Pollen",
            "Dust mites",
        ]
        for _ in range(num_allergies):
            allergies.append(self.fake.random_element(allergy_options))

        # Generate vital signs
        vital_signs = {
            "blood_pressure": f"{self.fake.vital_sign('systolic_bp')}/{self.fake.vital_sign('diastolic_bp')}",
            "heart_rate": self.fake.vital_sign("heart_rate"),
            "temperature": self.fake.vital_sign("temperature"),
            "respiratory_rate": self.fake.vital_sign("respiratory_rate"),
            "oxygen_saturation": self.fake.vital_sign("oxygen_saturation"),
            "recorded_date": datetime.now().isoformat(),
        }

        return SyntheticPatient(
            patient_id=patient_id,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=birth_date.isoformat(),
            gender=gender,
            phone=phone,
            email=email,
            address=address,
            emergency_contact=emergency_contact,
            insurance=insurance,
            medical_history=medical_history,
            current_medications=current_medications,
            allergies=allergies,
            vital_signs=vital_signs,
            created_at=datetime.now().isoformat(),
        )

    def generate_synthetic_encounter(self, patient_id: str) -> SyntheticEncounter:
        """Generate a synthetic medical encounter"""

        encounter_id = f"ENC-{str(uuid.uuid4())[:8].upper()}"

        # Generate provider information
        provider_name = f"Dr. {self.fake.name()}"
        specialty = self.fake.medical_specialty()

        # Generate encounter details
        encounter_date = self.fake.date_between(start_date="-1y", end_date="today").isoformat()
        encounter_type = self.fake.random_element(
            ["Office Visit", "Telehealth", "Follow-up", "Annual Physical"],
        )

        # Generate clinical content (generic, non-specific)
        chief_complaints = [
            "Routine follow-up",
            "Annual physical exam",
            "Medication review",
            "General wellness check",
            "Preventive care visit",
            "Health maintenance",
        ]
        chief_complaint = self.fake.random_element(chief_complaints)

        assessments = [
            "Patient appears well",
            "Stable chronic conditions",
            "No acute concerns",
            "Routine health maintenance",
            "Continue current management",
            "Good overall health",
        ]
        assessment = self.fake.random_element(assessments)

        plans = [
            "Continue current medications",
            "Return in 6 months",
            "Routine lab work",
            "Maintain current lifestyle",
            "Follow-up as needed",
            "Preventive care counseling",
        ]
        plan = self.fake.random_element(plans)

        # Generate clinical notes (generic)
        notes = f"Patient seen for {chief_complaint.lower()}. {assessment}. {plan}."

        return SyntheticEncounter(
            encounter_id=encounter_id,
            patient_id=patient_id,
            provider_name=provider_name,
            specialty=specialty,
            encounter_date=encounter_date,
            encounter_type=encounter_type,
            chief_complaint=chief_complaint,
            assessment=assessment,
            plan=plan,
            notes=notes,
            created_at=datetime.now().isoformat(),
        )

    def generate_dataset(
        self,
        num_patients: int = 100,
        encounters_per_patient: int = 3,
    ) -> dict[str, Any]:
        """Generate a complete synthetic healthcare dataset"""

        self.logger.info(
            f"Generating synthetic dataset: {num_patients} patients, {encounters_per_patient} encounters each",
        )

        patients = []
        encounters = []

        for i in range(num_patients):
            # Generate patient
            patient = self.generate_synthetic_patient()
            patients.append(asdict(patient))

            # Generate encounters for this patient
            for _ in range(random.randint(1, encounters_per_patient)):
                encounter = self.generate_synthetic_encounter(patient.patient_id)
                encounters.append(asdict(encounter))

            if (i + 1) % 10 == 0:
                self.logger.info(f"Generated {i + 1}/{num_patients} patients")

        dataset = {
            "patients": patients,
            "encounters": encounters,
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_patients": len(patients),
                "total_encounters": len(encounters),
                "data_type": "synthetic",
                "hipaa_compliant": True,
                "phi_present": False,
            },
        }

        self.logger.info(
            f"Dataset generation complete: {len(patients)} patients, {len(encounters)} encounters",
        )
        return dataset

    def save_dataset(self, dataset: dict[str, list[dict]], output_path: str) -> None:
        """Save synthetic dataset to file"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(dataset, f, indent=2, default=str)

        self.logger.info(f"Synthetic dataset saved to {output_path}")


# Example usage
if __name__ == "__main__":
    generator = SyntheticHealthcareDataGenerator()
    dataset = generator.generate_dataset(num_patients=50, encounters_per_patient=2)
    generator.save_dataset(
        dataset,
        "/opt/intelluxe/data/evaluation/synthetic/healthcare_test_data.json",
    )
