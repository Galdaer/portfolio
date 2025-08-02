#!/usr/bin/env python3
"""
Simple Synthetic Healthcare Data Generator
Creates basic synthetic data without external dependencies for CI testing
"""

import json
import os
import random
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List

def generate_simple_synthetic_data(output_dir: str = "data/synthetic"):
    """Generate simple synthetic healthcare data for testing"""
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate synthetic patients
    patients = []
    for i in range(20):
        patient_id = f"PAT{i+1:03d}"
        patients.append({
            "patient_id": patient_id,
            "first_name": f"TestPatient{i+1}",
            "last_name": f"Synthetic{i+1}",
            "date_of_birth": "1990-01-01",
            "phone": f"555-{random.randint(100,999):03d}-{random.randint(1000,9999):04d}",
            "insurance_provider": "SyntheticInsurance",
            "member_id": f"SYN{random.randint(100000,999999)}",
            "primary_condition": "Test Condition",
            "_synthetic": True
        })
    
    # Generate synthetic doctors
    doctors = []
    for i in range(5):
        doctor_id = f"PROV{i+1:03d}"
        doctors.append({
            "doctor_id": doctor_id,
            "name": f"Dr. TestProvider{i+1}",
            "specialty": "General Medicine",
            "npi": f"123456789{i}",
            "_synthetic": True
        })
    
    # Generate synthetic encounters
    encounters = []
    for i in range(30):
        encounter_id = f"ENC{i+1:03d}"
        patient_id = f"PAT{(i % 20) + 1:03d}"
        encounters.append({
            "encounter_id": encounter_id,
            "patient_id": patient_id,
            "provider_id": f"PROV{(i % 5) + 1:03d}",
            "date": "2024-01-15",
            "chief_complaint": "routine visit",
            "reason": "routine care",
            "vital_signs": {"bp": "120/80", "temp": "98.6"},
            "diagnosis_codes": ["Z00.00"],
            "notes": "Standard synthetic encounter",
            "_synthetic": True
        })
    
    # Generate synthetic lab results
    lab_results = []
    for i in range(40):
        lab_results.append({
            "lab_id": f"LAB{i+1:03d}",
            "patient_id": f"PAT{(i % 20) + 1:03d}",
            "test_type": "Complete Blood Count",
            "result_date": "2024-01-15",
            "status": "Normal",
            "_synthetic": True
        })
    
    # Generate synthetic insurance verifications
    insurance_verifications = []
    for i in range(20):
        insurance_verifications.append({
            "verification_id": f"INS{i+1:03d}",
            "patient_id": f"PAT{i+1:03d}",
            "insurance_provider": "SyntheticInsurance",
            "eligibility_status": "Active",
            "coverage_type": "Standard",
            "copay_amount": 25,
            "verification_date": "2024-01-15",
            "_synthetic": True
        })
    
    # Generate synthetic billing claims
    billing_claims = []
    for i in range(25):
        billing_claims.append({
            "claim_id": f"CLM{i+1:03d}",
            "patient_id": f"PAT{(i % 20) + 1:03d}",
            "provider_id": f"PROV{(i % 5) + 1:03d}",
            "cpt_codes": ["99213"],
            "diagnosis_codes": ["Z00.00"],
            "claim_amount": 150,
            "service_date": "2024-01-15",
            "claim_status": "Pending",
            "insurance_provider": "SyntheticInsurance",
            "_synthetic": True
        })
    
    # Generate synthetic agent sessions
    agent_sessions = []
    for i in range(15):
        agent_sessions.append({
            "session_id": f"SESS{i+1:03d}",
            "agent_type": "test_agent",
            "patient_id": f"PAT{(i % 20) + 1:03d}",
            "session_start": "2024-01-15T10:00:00Z",
            "session_end": "2024-01-15T10:30:00Z",
            "summary": "Synthetic test session",
            "_synthetic": True
        })
    
    # Generate synthetic doctor preferences
    doctor_preferences = []
    for i in range(5):
        doctor_preferences.append({
            "doctor_id": f"PROV{i+1:03d}",
            "documentation_style": "standard",
            "preferred_templates": ["soap_note"],
            "workflow_settings": {"auto_save": True},
            "_synthetic": True
        })
    
    # Generate synthetic audit logs
    audit_logs = []
    for i in range(30):
        audit_logs.append({
            "log_id": f"AUDIT{i+1:03d}",
            "user_id": f"USER{(i % 5) + 1:03d}",
            "action": "view_patient_record",
            "resource": f"PAT{(i % 20) + 1:03d}",
            "timestamp": "2024-01-15T10:00:00Z",
            "compliance_level": "HIPAA",
            "_synthetic": True
        })
    
    # Save all data to JSON files
    datasets = {
        "patients.json": patients,
        "doctors.json": doctors,
        "encounters.json": encounters,
        "lab_results.json": lab_results,
        "insurance_verifications.json": insurance_verifications,
        "billing_claims.json": billing_claims,
        "agent_sessions.json": agent_sessions,
        "doctor_preferences.json": doctor_preferences,
        "audit_logs.json": audit_logs
    }
    
    for filename, data in datasets.items():
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"✅ Generated {filepath} with {len(data)} records")
    
    print(f"\n✅ Synthetic healthcare data generation complete!")
    print(f"📁 Data saved to: {output_dir}")
    print(f"📊 Total records: {sum(len(data) for data in datasets.values())}")

if __name__ == "__main__":
    generate_simple_synthetic_data()