# Healthcare AI Testing Instructions

## Purpose

Testing patterns for healthcare AI systems emphasizing PHI-safe testing, medical compliance validation, and beyond-HIPAA security standards with patient-first design principles.

## Beyond-HIPAA Testing Security Principles

### Patient-First Testing Standards
- **Zero real patient data**: Never use real PHI, even in secure test environments
- **Proactive synthetic data**: Generate realistic test data that exceeds real-world complexity
- **Emergency scenario testing**: Validate system behavior during critical medical situations
- **Compassionate failure modes**: Ensure system failures never compromise patient care

## Healthcare Testing Framework

### PHI-Safe Testing (Beyond HIPAA Requirements)

```python
# ✅ PATTERN: Healthcare testing with zero PHI risk
import pytest
from unittest.mock import MagicMock
from tests.synthetic_healthcare_data import generate_realistic_patient_scenario

class HealthcareTestFramework:
    def __init__(self):
        # Beyond HIPAA: Proactive PHI exclusion in all test environments
        self.zero_phi_policy = True
        self.synthetic_data_only = True
        self.emergency_scenario_testing = True
    
    def test_with_synthetic_patient(self, test_scenario: str):
        # Pattern: Use complex synthetic data that tests real-world edge cases
        synthetic_patient = generate_realistic_patient_scenario(test_scenario)
        
        # Validate synthetic data complexity exceeds typical test data
        assert synthetic_patient.has_realistic_medical_history()
        assert synthetic_patient.contains_edge_case_scenarios()
        
        return synthetic_patient

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
        
        # Test coordination: intake → document_processor → research_assistant
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
