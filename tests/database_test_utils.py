#!/usr/bin/env python3
"""
Database-Backed Test Utility for Intelluxe AI Healthcare Testing

This utility connects tests to the synthetic healthcare database instead of
using hardcoded test data. All PHI is safely contained in the database.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import database and healthcare modules
try:
    import asyncpg
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError as e:
    print(f"⚠️  Database dependencies not installed: {e}")
    print("Run: pip install asyncpg psycopg2-binary")
    sys.exit(1)

class SyntheticHealthcareData:
    """
    Database-backed synthetic healthcare data provider.
    Connects to PostgreSQL with synthetic data instead of using hardcoded test data.
    """

    def __init__(self, db_url: str | None = None):
        """Initialize database connection to synthetic healthcare data."""
        self.db_url = db_url or os.getenv(
            'HEALTHCARE_DB_URL',
            'postgresql://intelluxe:secure_password@localhost:5432/intelluxe_healthcare'
        )
        self.connection = None
        self.async_pool = None

    def connect(self) -> None:
        """Establish synchronous database connection."""
        try:
            self.connection = psycopg2.connect(
                self.db_url,
                cursor_factory=RealDictCursor
            )
            logging.info("✅ Connected to synthetic healthcare database")
        except psycopg2.Error as e:
            logging.error(f"❌ Failed to connect to healthcare database: {e}")
            raise

    async def async_connect(self) -> None:
        """Establish asynchronous database connection pool."""
        try:
            self.async_pool = await asyncpg.create_pool(self.db_url)
            logging.info("✅ Connected to synthetic healthcare database (async)")
        except Exception as e:
            logging.error(f"❌ Failed to connect to healthcare database (async): {e}")
            raise

    def get_test_patients(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get synthetic patient data for testing."""
        if not self.connection:
            self.connect()

        with self.connection.cursor() as cursor:
            cursor.execute("""
                SELECT patient_id, first_name, last_name, date_of_birth,
                       gender, phone_number, email, insurance_provider
                FROM patients
                WHERE synthetic = true
                LIMIT %s
            """, (limit,))

            return [dict(row) for row in cursor.fetchall()]

    async def async_get_test_patients(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get synthetic patient data for testing (async)."""
        if not self.async_pool:
            await self.async_connect()

        async with self.async_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT patient_id, first_name, last_name, date_of_birth,
                       gender, phone_number, email, insurance_provider
                FROM patients
                WHERE synthetic = true
                LIMIT $1
            """, limit)

            return [dict(row) for row in rows]

    def get_test_doctors(self, limit: int = 5) -> list[dict[str, Any]]:
        """Get synthetic doctor data for testing."""
        if not self.connection:
            self.connect()

        with self.connection.cursor() as cursor:
            cursor.execute("""
                SELECT doctor_id, first_name, last_name, specialty,
                       npi_number, license_number, email
                FROM doctors
                WHERE synthetic = true
                LIMIT %s
            """, (limit,))

            return [dict(row) for row in cursor.fetchall()]

    def get_test_encounters(self, patient_id: str = None, limit: int = 10) -> list[dict[str, Any]]:
        """Get synthetic encounter data for testing."""
        if not self.connection:
            self.connect()

        with self.connection.cursor() as cursor:
            if patient_id:
                cursor.execute("""
                    SELECT encounter_id, patient_id, doctor_id, visit_date,
                           chief_complaint, diagnosis, treatment_plan
                    FROM encounters
                    WHERE synthetic = true AND patient_id = %s
                    LIMIT %s
                """, (patient_id, limit))
            else:
                cursor.execute("""
                    SELECT encounter_id, patient_id, doctor_id, visit_date,
                           chief_complaint, diagnosis, treatment_plan
                    FROM encounters
                    WHERE synthetic = true
                    LIMIT %s
                """, (limit,))

            return [dict(row) for row in cursor.fetchall()]

    def get_test_lab_results(self, patient_id: str = None, limit: int = 10) -> list[dict[str, Any]]:
        """Get synthetic lab result data for testing."""
        if not self.connection:
            self.connect()

        with self.connection.cursor() as cursor:
            if patient_id:
                cursor.execute("""
                    SELECT lab_id, patient_id, test_name, test_value,
                           reference_range, test_date, status
                    FROM lab_results
                    WHERE synthetic = true AND patient_id = %s
                    LIMIT %s
                """, (patient_id, limit))
            else:
                cursor.execute("""
                    SELECT lab_id, patient_id, test_name, test_value,
                           reference_range, test_date, status
                    FROM lab_results
                    WHERE synthetic = true
                    LIMIT %s
                """, (limit,))

            return [dict(row) for row in cursor.fetchall()]

    def cleanup(self) -> None:
        """Clean up database connections."""
        if self.connection:
            self.connection.close()

    async def async_cleanup(self) -> None:
        """Clean up async database connections."""
        if self.async_pool:
            await self.async_pool.close()


class HealthcareTestCase:
    """
    Base test case class that provides database-backed synthetic healthcare data.

    Replaces hardcoded test data with database connections to synthetic data.
    """

    def __init__(self):
        """Initialize healthcare test case with synthetic data provider."""
        self.synthetic_data = SyntheticHealthcareData()
        self.test_patients = []
        self.test_doctors = []
        self.test_encounters = []

    def setUp(self) -> None:
        """Set up test case with synthetic data."""
        self.synthetic_data.connect()

        # Load test data sets
        self.test_patients = self.synthetic_data.get_test_patients(limit=5)
        self.test_doctors = self.synthetic_data.get_test_doctors(limit=3)

        if self.test_patients:
            # Get encounters for first test patient
            self.test_encounters = self.synthetic_data.get_test_encounters(
                patient_id=self.test_patients[0]['patient_id'],
                limit=3
            )

    def tearDown(self) -> None:
        """Clean up test case."""
        self.synthetic_data.cleanup()

    def get_sample_patient(self) -> dict[str, Any]:
        """Get a sample patient for testing."""
        if not self.test_patients:
            raise ValueError("No test patients available. Check database connection.")
        return self.test_patients[0]

    def get_sample_doctor(self) -> dict[str, Any]:
        """Get a sample doctor for testing."""
        if not self.test_doctors:
            raise ValueError("No test doctors available. Check database connection.")
        return self.test_doctors[0]

    def get_sample_encounter(self) -> dict[str, Any]:
        """Get a sample encounter for testing."""
        if not self.test_encounters:
            raise ValueError("No test encounters available. Check database connection.")
        return self.test_encounters[0]


# Convenience functions for quick testing
def get_test_patient_data(limit: int = 1) -> list[dict[str, Any]]:
    """Quick function to get synthetic patient data for testing."""
    data_provider = SyntheticHealthcareData()
    try:
        return data_provider.get_test_patients(limit=limit)
    finally:
        data_provider.cleanup()


def get_test_medical_scenario() -> dict[str, Any]:
    """Get a complete test medical scenario (patient + doctor + encounter)."""
    data_provider = SyntheticHealthcareData()
    try:
        patients = data_provider.get_test_patients(limit=1)
        doctors = data_provider.get_test_doctors(limit=1)

        if not patients or not doctors:
            raise ValueError("Insufficient synthetic data for test scenario")

        patient = patients[0]
        encounters = data_provider.get_test_encounters(
            patient_id=patient['patient_id'],
            limit=1
        )

        return {
            'patient': patient,
            'doctor': doctors[0],
            'encounter': encounters[0] if encounters else None,
            'synthetic': True  # Mark as synthetic data
        }
    finally:
        data_provider.cleanup()


# Example test migration
if __name__ == "__main__":
    """
    Example of migrating from hardcoded test data to database-backed synthetic data.
    """

    print("🏥 Testing database-backed synthetic healthcare data...")

    # OLD WAY (hardcoded test data):
    # test_patient = {
    #     'patient_id': 'TEST001',
    #     'first_name': 'John',
    #     'last_name': 'Doe',
    #     'ssn': '123-45-6789'  # ❌ Fake PHI in code
    # }

    # NEW WAY (database-backed synthetic data):
    try:
        scenario = get_test_medical_scenario()
        print("✅ Got synthetic test scenario:")
        print(f"   Patient: {scenario['patient']['first_name']} {scenario['patient']['last_name']}")
        print(f"   Doctor: {scenario['doctor']['first_name']} {scenario['doctor']['last_name']}")
        if scenario['encounter']:
            print(f"   Encounter: {scenario['encounter']['chief_complaint']}")
        print(f"   Synthetic: {scenario['synthetic']}")

    except Exception as e:
        print(f"❌ Error accessing synthetic data: {e}")
        print("   Make sure PostgreSQL is running with synthetic healthcare data")
        print("   Run: python3 scripts/generate_synthetic_healthcare_data.py --use-database")
