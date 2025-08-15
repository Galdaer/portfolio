# Healthcare Testing Patterns

**WORKFLOW CONTROL**: All workflows are controlled by `copilot-instructions.md`. This file provides implementation patterns only.

## Synthetic Data Testing

```python
import pytest
from decimal import Decimal

# Generate synthetic patient data
def create_synthetic_patient():
    return {
        "id": "SYNTHETIC-PT-001",
        "name": "Test Patient (SYNTHETIC)",
        "dob": "1980-01-01",
        "mrn": "TEST-MRN-123456",
        "note": "SYNTHETIC_DATA_NOT_REAL_PHI"
    }

# Test with clearly marked synthetic data
def test_patient_processing():
    synthetic_patient = create_synthetic_patient()
    result = process_patient_data(synthetic_patient)
    
    assert result["processed"] == True
    assert "medical_disclaimer" in result
```

## PHI Protection Testing

```python
# Test PHI detection
def test_phi_detection():
    test_cases = [
        "Patient SSN: 123-45-6789",  # Should be detected
        "Synthetic SSN: 555-55-5555",  # Should be flagged as test data
        "Patient ID: SYNTHETIC-001"  # Should be safe
    ]
    
    for test_case in test_cases:
        result = scan_for_phi(test_case)
        if "SYNTHETIC" in test_case:
            assert result["synthetic_data"] == True
        else:
            assert result["phi_detected"] == True

# Test audit logging
def test_audit_logging():
    with capture_logs() as logs:
        access_patient_data("SYNTHETIC-PT-001")
    
    assert any("phi_access" in log for log in logs)
    assert any("SYNTHETIC" in log for log in logs)
```

## Medical Calculation Testing

```python
# Test financial calculations with Decimal
def test_copay_calculation():
    amount = Decimal('100.00')
    percentage = Decimal('20.0')
    
    result = calculate_copay(amount, percentage)
    
    assert result == Decimal('20.00')
    assert isinstance(result, Decimal)

# Test division by zero protection
def test_zero_division_protection():
    amount = Decimal('100.00')
    percentage = Decimal('0')
    
    result = calculate_copay(amount, percentage)
    
    assert result == Decimal('0')  # Should not raise exception
```

## Database Testing

```python
# Test database operations with cleanup
@pytest.mark.asyncio
async def test_patient_database_operations():
    async with get_test_db() as db:
        # Insert synthetic patient
        patient_id = await db.insert_patient(create_synthetic_patient())
        
        # Test retrieval
        patient = await db.get_patient(patient_id)
        assert patient["id"] == patient_id
        assert "SYNTHETIC" in patient["note"]
        
        # Cleanup happens automatically via context manager

# Test connection cleanup
def test_connection_cleanup():
    connection_count_before = get_active_connections()
    
    # This should not leak connections
    for i in range(10):
        with get_db_connection() as conn:
            conn.execute("SELECT 1")
    
    connection_count_after = get_active_connections()
    assert connection_count_before == connection_count_after
```

## API Testing

```python
# Test healthcare API endpoints
def test_clinical_analysis_endpoint(test_client):
    synthetic_data = {
        "patient_id": "SYNTHETIC-PT-001",
        "encounter_data": "SYNTHETIC encounter data"
    }
    
    response = test_client.post("/analyze", json=synthetic_data)
    
    assert response.status_code == 200
    assert "medical_disclaimer" in response.json()
    assert response.json()["provider_review_required"] == True

# Test authentication
def test_provider_authentication(test_client):
    # Test without auth
    response = test_client.post("/clinical/analyze", json={})
    assert response.status_code == 401
    
    # Test with valid auth
    headers = {"Authorization": "Bearer synthetic_test_token"}
    response = test_client.post("/clinical/analyze", json={}, headers=headers)
    assert response.status_code != 401
```

## Agent Testing

```python
# Test agent provenance
def test_agent_provenance(test_client):
    response = test_client.post('/process', json={
        'message': 'find articles on hypertension', 
        'format': 'human'
    })
    
    formatted_response = response.json().get('formatted_response', '')
    assert formatted_response.startswith('🤖 ')

# Test agent fallback
def test_agent_fallback():
    # When agent selection fails, should fall back gracefully
    result = process_with_fallback("unknown request type")
    
    assert result["fallback_used"] == True
    assert "medical_disclaimer" in result
```

## Error Testing

```python
# Test error handling without PHI exposure
def test_error_handling():
    with pytest.raises(PatientDataError) as exc_info:
        process_invalid_patient_data("invalid_data")
    
    # Error message should not contain PHI
    error_msg = str(exc_info.value)
    assert not contains_phi(error_msg)
    assert "synthetic" in error_msg.lower() or "test" in error_msg.lower()

# Test medical safety errors
def test_medical_safety_validation():
    # Should reject medical advice patterns
    with pytest.raises(MedicalSafetyError):
        validate_medical_content("I diagnose you with...")
    
    # Should accept informational content
    result = validate_medical_content("Educational information for providers")
    assert result["safe"] == True
```

## Integration Testing

```python
# Test full workflow with synthetic data
@pytest.mark.integration
def test_patient_workflow_integration():
    # Create synthetic patient
    patient = create_synthetic_patient()
    
    # Test full workflow
    intake_result = patient_intake(patient)
    analysis_result = clinical_analysis(intake_result)
    documentation_result = generate_documentation(analysis_result)
    
    # Verify each step
    assert intake_result["processed"] == True
    assert analysis_result["provider_review_required"] == True
    assert "medical_disclaimer" in documentation_result
    
    # Verify synthetic data maintained throughout
    assert "SYNTHETIC" in str(documentation_result)
```

## Performance Testing

```python
# Test under medical emergency load
def test_emergency_response_time():
    start_time = time.time()
    
    # Simulate emergency patient processing
    result = process_emergency_patient(create_synthetic_emergency_patient())
    
    end_time = time.time()
    response_time = end_time - start_time
    
    # Should respond quickly for emergency scenarios
    assert response_time < 2.0  # 2 second max for emergency
    assert result["emergency_processed"] == True
```

    def test_base_fallback_when_agent_fails(self, mock_router_failure, test_client):
        # Simulate agent failure; API should return base fallback message
        resp = test_client.post('/process', json={'message': 'trigger failure', 'format': 'human'})
        data = resp.json()
        assert data['status'] == 'success'
        assert 'base' in (data.get('result', {}).get('agent_name') or '')
        assert 'not medical advice' in (data.get('formatted_response') or data.get('response') or '').lower()

    def test_timeout_respected(self, slow_agent_selected, test_client, orchestrator_config):
        # Ensure per_agent_default timeout is enforced
        resp = test_client.post('/process', json={'message': 'slow op', 'format': 'json'})
        assert resp.status_code == 200

# ✅ PATTERN: Emergency scenario testing
class EmergencyScenarioTesting:
    def test_emergency_response_times(self):
        # Pattern: Validate <500ms response for critical care scenarios
        emergency_request = self.create_emergency_scenario()
        
        start_time = time.time()
        response = healthcare_system.handle_emergency(emergency_request)
        response_time = time.time() - start_time
        
        # Beyond HIPAA: Strict emergency performance requirements
        assert response_time < 0.5, f"Emergency response too slow: {response_time}s"
        assert response.priority == "CRITICAL"
        assert response.escalated_to_human == True
    
    def test_system_failure_patient_safety(self):
        # Pattern: Ensure failures never compromise patient safety
        # Requirement: System fails safely, escalates to human oversight
        pass
```

### Database-Backed Testing (Beyond HIPAA)

**Healthcare Database Integration Patterns** - Use real PostgreSQL/Redis with synthetic data for comprehensive testing:

```python
# ✅ PATTERN: Full healthcare database integration testing
from core.models.healthcare import (
    get_healthcare_session, Doctor, Patient, Encounter, 
    LabResult, BillingClaim, AuditLog
)

class HealthcareDatabaseTesting:
    def __init__(self):
        # Use real database with synthetic data for authentic testing
        self.db_session = get_healthcare_session()
        self.use_real_database = True
        self.synthetic_data_only = True  # PHI-safe
        
    def test_complete_healthcare_workflow(self):
        """Test full patient care workflow with database persistence"""
        # Generate synthetic healthcare scenario
        doctor = self.create_synthetic_doctor()
        patient = self.create_synthetic_patient() 
        encounter = self.create_synthetic_encounter(patient.patient_id, doctor.doctor_id)
        
        # Test database persistence
        self.db_session.add(doctor)
        self.db_session.add(patient)
        self.db_session.add(encounter)
        self.db_session.commit()
        
        # Verify relationships and data integrity
        retrieved_encounter = self.db_session.query(Encounter).filter_by(
            encounter_id=encounter.encounter_id
        ).first()
        
        assert retrieved_encounter.patient.first_name == patient.first_name
        assert retrieved_encounter.doctor.specialty == doctor.specialty
        assert retrieved_encounter.diagnosis_codes is not None
    
    def test_synthetic_data_generation_integration(self):
        """Test synthetic data generator database population"""
        # Run synthetic data generator with database integration
        from scripts.generate_synthetic_healthcare_data import SyntheticHealthcareDataGenerator
        
        generator = SyntheticHealthcareDataGenerator(
            num_doctors=5,
            num_patients=20, 
            num_encounters=30,
            use_database=True
        )
        
        generator.generate_all_data()
        
        # Verify data was populated in database
        doctor_count = self.db_session.query(Doctor).count()
        patient_count = self.db_session.query(Patient).count()
        encounter_count = self.db_session.query(Encounter).count()
        
        assert doctor_count == 5
        assert patient_count == 20
        assert encounter_count == 30
    
    def test_cross_table_healthcare_relationships(self):
        """Test complex healthcare data relationships"""
        # Test patient-doctor-encounter relationships
        patients_with_multiple_visits = self.db_session.query(Patient).join(
            Encounter
        ).group_by(Patient.patient_id).having(
            func.count(Encounter.encounter_id) > 1
        ).all()
        
        for patient in patients_with_multiple_visits:
            # Verify each patient has valid encounters
            assert len(patient.encounters) > 1
            # Verify all encounters have valid doctors
            for encounter in patient.encounters:
                assert encounter.doctor is not None
                assert encounter.doctor.specialty is not None

# ✅ PATTERN: Performance testing with realistic database loads
class HealthcarePerformanceTesting:
    def test_database_performance_with_healthcare_data(self):
        """Test database performance with realistic healthcare data volumes"""
        # Generate large synthetic dataset for performance testing
        generator = SyntheticHealthcareDataGenerator(
            num_doctors=100,
            num_patients=10000,
            num_encounters=50000,
            use_database=True
        )
        
        start_time = time.time()
        generator.generate_all_data()
        generation_time = time.time() - start_time
        
        # Performance requirements for healthcare data generation
        assert generation_time < 300, f"Data generation too slow: {generation_time}s"
        
        # Test query performance with large dataset
        start_time = time.time()
        recent_encounters = self.db_session.query(Encounter).filter(
            Encounter.date >= "2024-01-01"
        ).limit(1000).all()
        query_time = time.time() - start_time
        
        assert query_time < 5.0, f"Query performance too slow: {query_time}s"
        assert len(recent_encounters) > 0

# ✅ PATTERN: HIPAA compliance testing with database audit trails
class HIPAAComplianceDatabaseTesting:
    def test_audit_log_database_integration(self):
        """Test HIPAA audit logging with database persistence"""
        # Create test audit events
        test_actions = [
            ("view_patient", "doctor", "pt_12345"),
            ("update_notes", "doctor", "enc_67890"), 
            ("access_lab_results", "nurse", "lab_54321")
        ]
        
        for action, user_type, resource_id in test_actions:
            audit_log = AuditLog(
                log_id=str(uuid.uuid4()),
                user_id=f"test_user_{uuid.uuid4().hex[:8]}",
                user_type=user_type,
                action=action,
                resource_id=resource_id,
                timestamp=datetime.utcnow(),
                success=True
            )
            self.db_session.add(audit_log)
        
        self.db_session.commit()
        
        # Verify audit trail completeness
        audit_count = self.db_session.query(AuditLog).count()
        assert audit_count >= len(test_actions)
        
        # Test audit query capabilities
        doctor_actions = self.db_session.query(AuditLog).filter_by(
            user_type="doctor"
        ).all()
        assert len(doctor_actions) > 0
```

### Redis Healthcare Session Testing

```python
# ✅ PATTERN: Redis integration testing for healthcare sessions
class RedisHealthcareSessionTesting:
    def __init__(self):
        self.redis_client = redis.Redis(
            host="172.20.0.14", port=6379, decode_responses=True
        )
    
    def test_agent_session_redis_integration(self):
        """Test AI agent session storage in Redis"""
        # Create synthetic agent session
        session_data = {
            "session_id": str(uuid.uuid4()),
            "doctor_id": "dr_test_123",
            "agent_type": "intake",
            "start_time": datetime.utcnow().isoformat(),
            "duration_seconds": 180,
            "messages_exchanged": 25,
            "tokens_used": 2500,
            "model_used": "llama3.1:8b",
            "session_outcome": "completed"
        }
        
        # Store in Redis
        session_key = f"session:{session_data['session_id']}"
        self.redis_client.hset(session_key, mapping=session_data)
        self.redis_client.expire(session_key, 30 * 24 * 60 * 60)  # 30 days
        
        # Verify storage and retrieval
        retrieved_data = self.redis_client.hgetall(session_key)
        assert retrieved_data["doctor_id"] == session_data["doctor_id"]
        assert retrieved_data["agent_type"] == session_data["agent_type"]
        
        # Test session expiration
        ttl = self.redis_client.ttl(session_key)
        assert ttl > 0 and ttl <= 30 * 24 * 60 * 60
```

### Database-Backed Testing (Beyond HIPAA)

```python
# ✅ PATTERN: Database testing with enhanced synthetic data
class EnhancedSyntheticDataTesting:
    def __init__(self):
        # Beyond HIPAA: More realistic synthetic data than required
        self.synthetic_complexity_multiplier = 2.0
        self.edge_case_coverage = 0.95  # 95% edge case coverage
        
    def test_database_with_complex_synthetics(self):
        # Pattern: Test with synthetic data more complex than real scenarios
        complex_patient_data = self.generate_complex_synthetic_dataset()
        
        # Validate database handles complexity beyond typical real-world data
        assert len(complex_patient_data.medical_history) > 10
        assert complex_patient_data.has_multiple_insurance_types()
        assert complex_patient_data.includes_emergency_contacts()
        
        # Test database operations with this enhanced synthetic data
        result = database.process_patient_data(complex_patient_data)
        assert result.success == True

# ✅ PATTERN: Compliance testing beyond HIPAA minimums
class BeyondHIPAAComplianceTesting:
    def test_phi_detection_enhanced(self):
        # Pattern: Test PHI detection beyond HIPAA-required fields
        enhanced_phi_patterns = [
            "Social Security Numbers", "Phone Numbers", "Email Addresses",
            "Medical Record Numbers", "Account Numbers", "Insurance IDs",
            # Beyond HIPAA: Additional privacy protections
            "Partial SSNs", "Voice Recordings", "Biometric Identifiers",
            "Genetic Information", "Mental Health Notes", "Substance Abuse Records"
        ]
        
        for pattern in enhanced_phi_patterns:
            test_data = self.create_test_data_with_pattern(pattern)
            detection_result = phi_detector.scan(test_data)
            
            assert detection_result.detected == True
            assert pattern in detection_result.detected_types
    
    def test_audit_logging_comprehensive(self):
        # Pattern: Audit beyond HIPAA minimum requirements
        # Include: User intent, system state, patient impact assessment
        pass
```

### Healthcare Integration Testing

```python
# ✅ PATTERN: Integration testing with patient-first priorities
class PatientFirstIntegrationTesting:
    def test_multi_agent_coordination(self):
        # Pattern: Test agent coordination with patient safety priority
        patient_request = self.create_complex_patient_scenario()
        
        # Test coordination: intake → document_processor → clinical_research_agent
        coordination_result = agent_orchestrator.process_patient_request(patient_request)
        
        # Validate patient-first outcomes
        assert coordination_result.patient_safety_validated == True
        assert coordination_result.human_oversight_triggered == True
        assert coordination_result.medical_advice_avoided == True
    
    def test_emergency_escalation_pathways(self):
        # Pattern: Validate emergency scenarios escalate to humans immediately
        emergency_indicators = ["chest pain", "difficulty breathing", "severe injury"]
        
        for indicator in emergency_indicators:
            request = self.create_request_with_indicator(indicator)
            response = system.process_request(request)
            
            # Beyond HIPAA: Proactive emergency detection and escalation
            assert response.escalated_immediately == True
            assert response.human_provider_notified == True
            assert response.emergency_protocols_activated == True
```

### Healthcare MCP & Ollama Integration Testing

```python
# ✅ PATTERN: MCP testing with synthetic data and offline capability
class HealthcareMCPTesting:
    def test_mcp_with_synthetic_prompts(self):
        # Pattern: Test MCP servers with complex synthetic medical scenarios
        synthetic_medical_query = self.generate_synthetic_medical_literature_query()
        
        # Test JSON-RPC payload with synthetic data
        mcp_response = self.send_mcp_request({
            "jsonrpc": "2.0",
            "method": "search_medical_literature", 
            "params": {"query": synthetic_medical_query.query},
            "id": 1
        })
        
        assert mcp_response["result"]["medical_disclaimer"] is not None
        assert "no medical advice" in mcp_response["result"]["medical_disclaimer"]
    
    def test_offline_capability_healthcare(self):
        # Pattern: Ensure MCP servers work offline for remote healthcare settings
        # Critical for rural healthcare and intermittent connectivity
        offline_test_result = mcp_server.test_offline_mode()
        assert offline_test_result.can_function_offline == True
        assert offline_test_result.cached_medical_resources_available == True
```

## Implementation Guidelines

### Testing Best Practices (Beyond HIPAA)

**Patient-First Testing Design:**
- **Zero Real PHI Policy**: Never use real patient data, even in secure environments
- **Enhanced Synthetic Data**: Test with synthetic data more complex than real scenarios  
- **Emergency Scenario Coverage**: Validate <500ms response for critical care situations
- **Compassionate Failure Testing**: Ensure system failures escalate to human providers
- **Proactive Privacy Testing**: Test privacy protection beyond HIPAA minimums

**Security-Enhanced Testing Patterns:**
- **Comprehensive PHI Detection**: Test detection of all potential patient identifiers
- **Audit Trail Validation**: Verify complete audit logging of all healthcare operations
- **Multi-Agent Safety Testing**: Validate patient safety across all AI agent interactions
- **Offline Capability Testing**: Ensure system functions in remote healthcare settings
- **Performance Under Load**: Validate emergency response times under stress conditions

---
