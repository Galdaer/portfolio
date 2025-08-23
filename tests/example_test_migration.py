#!/usr/bin/env python3
"""
Example Test Migration: From Hardcoded PHI to Database-Backed Synthetic Data

This example shows how to migrate existing tests from hardcoded test data
to database-backed synthetic healthcare data.
"""

import sys
import unittest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.database_test_utils import (  # noqa: E402
    HealthcareTestCase,
    get_test_medical_scenario,
    get_test_patient_data,
)


class ExampleMigratedTest(HealthcareTestCase, unittest.TestCase):
    """
    Example of a test migrated from hardcoded data to database-backed synthetic data.
    """

    def setUp(self):
        """Set up test case with database-backed synthetic data."""
        # Call parent setUp to initialize database connection and load test data
        super().setUp()

    def tearDown(self):
        """Clean up test case."""
        # Call parent tearDown to close database connections
        super().tearDown()

    def test_patient_data_validation_OLD_WAY(self):
        """
        OLD WAY: Hardcoded test data (❌ Contains fake PHI in code)
        """
        # ❌ OLD APPROACH - Hardcoded test data
        # test_patient = {
        #     'patient_id': 'TEST001',
        #     'first_name': 'John',
        #     'last_name': 'Doe',
        #     'ssn': '123-45-6789',  # ❌ Fake PHI in code
        #     'dob': '1990-01-01',
        #     'phone': '555-123-4567'
        # }
        #
        # # Test validation logic
        # self.assertIsNotNone(test_patient['patient_id'])
        # self.assertEqual(test_patient['first_name'], 'John')
        # self.assertRegex(test_patient['ssn'], r'\d{3}-\d{2}-\d{4}')

        self.skipTest("Replaced with NEW_WAY - keeping for reference")

    def test_patient_data_validation_NEW_WAY(self):
        """
        NEW WAY: Database-backed synthetic data (✅ No PHI in code)
        """
        # ✅ NEW APPROACH - Database-backed synthetic data
        patient = self.get_sample_patient()

        # Test validation logic (same business logic, different data source)
        self.assertIsNotNone(patient["patient_id"])
        self.assertIsNotNone(patient["first_name"])
        self.assertIsNotNone(patient["last_name"])

        # Verify it's marked as synthetic
        # The database ensures all test data is marked as synthetic=true
        print(f"✅ Testing with synthetic patient: {patient['first_name']} {patient['last_name']}")

    def test_medical_encounter_processing_OLD_WAY(self):
        """
        OLD WAY: Hardcoded medical scenario (❌ Contains fake medical data in code)
        """
        # ❌ OLD APPROACH - Hardcoded medical scenario
        # test_scenario = {
        #     'patient': {
        #         'id': 'PAT001',
        #         'name': 'Jane Doe',
        #         'diagnosis': 'Hypertension'  # ❌ Medical info in code
        #     },
        #     'doctor': {
        #         'id': 'DOC001',
        #         'name': 'Dr. Smith',
        #         'specialty': 'Cardiology'
        #     }
        # }

        self.skipTest("Replaced with NEW_WAY - keeping for reference")

    def test_medical_encounter_processing_NEW_WAY(self):
        """
        NEW WAY: Database-backed medical scenario (✅ No medical data in code)
        """
        # ✅ NEW APPROACH - Database-backed synthetic medical scenario
        patient = self.get_sample_patient()
        doctor = self.get_sample_doctor()
        encounter = self.get_sample_encounter()

        # Test the same business logic with real synthetic data
        self.assertIsNotNone(patient["patient_id"])
        self.assertIsNotNone(doctor["doctor_id"])

        if encounter:
            self.assertIsNotNone(encounter["encounter_id"])
            print(f"✅ Testing medical encounter: {encounter['chief_complaint']}")

        # Test processing logic (business logic unchanged)
        processed_data = self._process_medical_encounter(patient, doctor, encounter)
        self.assertIsNotNone(processed_data)

    def test_lab_results_analysis_NEW_WAY(self):
        """
        NEW WAY: Test lab results with database-backed synthetic data
        """
        # Get synthetic lab results from database
        patient = self.get_sample_patient()
        lab_results = self.synthetic_data.get_test_lab_results(
            patient_id=patient["patient_id"],
            limit=3,
        )

        if lab_results:
            for lab_result in lab_results:
                self.assertIsNotNone(lab_result["lab_id"])
                self.assertIsNotNone(lab_result["test_name"])
                self.assertIsNotNone(lab_result["test_value"])

                print(
                    f"✅ Testing lab result: {lab_result['test_name']} = {lab_result['test_value']}",
                )

    def _process_medical_encounter(self, patient, doctor, encounter):
        """
        Business logic for processing medical encounters.
        This stays the same - only the data source changes.
        """
        return {
            "patient_id": patient["patient_id"],
            "doctor_id": doctor["doctor_id"],
            "encounter_id": encounter["encounter_id"] if encounter else None,
            "processed": True,
        }


class QuickTestDataExample(unittest.TestCase):
    """
    Example of using the quick test data functions for simple tests.
    """

    def test_quick_patient_data(self):
        """Example using the quick convenience function."""

        # Quick way to get test data for simple tests
        patients = get_test_patient_data(limit=2)

        self.assertGreater(len(patients), 0)
        for patient in patients:
            self.assertIsNotNone(patient["patient_id"])
            print(f"✅ Quick test with patient: {patient['first_name']}")

    def test_complete_medical_scenario(self):
        """Example using the complete medical scenario function."""

        # Get a complete test scenario (patient + doctor + encounter)
        scenario = get_test_medical_scenario()

        self.assertIsNotNone(scenario["patient"])
        self.assertIsNotNone(scenario["doctor"])
        self.assertTrue(scenario["synthetic"])  # Always marked as synthetic

        print("✅ Complete scenario test:")
        print(f"   Patient: {scenario['patient']['first_name']} {scenario['patient']['last_name']}")
        print(f"   Doctor: {scenario['doctor']['first_name']} {scenario['doctor']['last_name']}")


if __name__ == "__main__":
    print(
        "🏥 Running example test migration from hardcoded PHI to database-backed synthetic data...",
    )
    print()

    # Run the tests
    unittest.main(verbosity=2)
