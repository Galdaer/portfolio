# Healthcare AI Domain Instructions

## Purpose

AI development patterns for healthcare domains emphasizing medical compliance, patient safety, and healthcare-specific technical patterns.

## Core Healthcare AI Principles

### Medical Safety Framework

```python
# ✅ CRITICAL: Healthcare AI safety principles
class HealthcareAISafetyFramework:
    def validate_medical_request(self, request: str) -> bool:
        # Detect medical advice requests and redirect appropriately
        medical_keywords = ["diagnose", "treatment", "medication", "symptoms"]
        if any(keyword in request.lower() for keyword in medical_keywords):
            return False, "I cannot provide medical advice. Please consult with a healthcare professional."
        return True, None
```

### Healthcare Compliance Framework

```python
# ✅ CORRECT: Comprehensive healthcare logging and PHI monitoring
class HealthcareLoggingFramework:
    def __init__(self):
        # Setup HIPAA-compliant logging with PHI detection
        pass

class PHIMonitor:
    def detect_phi(self, data: str) -> bool:
        # Detect SSN, DOB, medical record numbers, phone numbers
        pass
    
    def anonymize_for_logging(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Remove/hash PHI for safe logging
        pass

@healthcare_log_method
def process_patient_intake(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
    # Process healthcare data with automatic audit logging
    return processed_data
```

### Medical Workflow Integration

```python
# ✅ CORRECT: Healthcare workflow patterns
class HealthcareWorkflowManager:
    def process_soap_note(self, soap_data: Dict[str, Any]) -> Dict[str, Any]:
        # Process SOAP notes with medical compliance validation
        pass
    
    def schedule_appointment(self, request: Dict[str, Any]) -> Dict[str, Any]:
        # Administrative scheduling without medical decision-making
        pass
```

### Healthcare AI Agent Coordination

```python
# ✅ CORRECT: Multi-agent healthcare coordination
class HealthcareAgentOrchestrator:
    def coordinate_intake_workflow(self, patient_request: Dict[str, Any]):
        # Route through: intake → document_processor → research_assistant
        pass
    
    def handle_emergency_scenario(self, emergency_data: Dict[str, Any]):
        # Escalate to human healthcare providers immediately
        pass
```

## Healthcare Domain Integration Patterns

### EHR Integration with AI Safety

```python
# ✅ CORRECT: Safe EHR integration patterns
class SafeEHRIntegration:
    def fetch_patient_data(self, patient_id: str, required_fields: List[str]):
        # Minimum necessary principle, audit logging, PHI protection
        pass
    
    def update_patient_record(self, patient_id: str, updates: Dict[str, Any]):
        # Validate updates don't contain medical advice or diagnosis
        pass
```

### Clinical Decision Support Integration

```python
# ✅ CORRECT: AI-assisted clinical decision support (administrative only)
class ClinicalDecisionSupportAssistant:
    def suggest_documentation_improvements(self, note: str):
        # Suggest documentation completeness, not medical decisions
        pass
    
    def validate_coding_accuracy(self, diagnosis_codes: List[str]):
        # Administrative coding validation, not medical interpretation
        pass
```

## PHI-Safe Development Patterns

- **Never expose real patient data** in logs, tests, or API calls
- **Use synthetic data generators** for all healthcare scenarios
- **Document all endpoints** with compliance disclaimers
- **Validate all external API calls** for PHI safety before deployment
- **Medical Safety**: Always redirect medical advice requests to healthcare professionals

---
