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

### Healthcare Financial Calculation Safety (Based on PR #31 Lessons)

```python
# ✅ CRITICAL: Financial calculation safety patterns
class HealthcareFinancialSafety:
    """Financial calculation safety patterns from real production issues."""
    
    @staticmethod
    def safe_division_with_zero_check(numerator: Decimal, denominator: Decimal) -> Decimal:
        """Division with zero protection for insurance calculations."""
        if denominator <= 0:
            return Decimal('0')  # or appropriate default
        return numerator / denominator
    
    @staticmethod
    def ensure_decimal_precision(value: Any) -> Decimal:
        """Convert financial values to Decimal safely."""
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float)):
            return Decimal(str(value))  # String conversion preserves precision
        raise ValueError(f"Cannot convert {type(value)} to Decimal")
    
    @staticmethod
    def validate_method_signature_compatibility(method_call: str, expected_params: List[str]) -> bool:
        """Validate method calls match expected signatures."""
        # Pattern to catch signature mismatches before runtime
        pass

# ✅ CRITICAL: Database resource management patterns
class HealthcareDatabaseSafety:
    """Database connection safety patterns from production issues."""
    
    @asynccontextmanager
    async def get_connection_with_auto_release(self):
        """Proper database connection management."""
        conn = await self.pool.acquire()
        try:
            yield conn
        finally:
            await self.pool.release(conn)
    
    async def safe_database_operation(self, operation_func, *args, **kwargs):
        """Template for safe database operations."""
        async with self.get_connection_with_auto_release() as conn:
            return await operation_func(conn, *args, **kwargs)

# ✅ CRITICAL: Avoid code duplication patterns
class HealthcareCodeOrganization:
    """Code organization patterns to prevent duplication."""
    
    # Common utilities should be in shared modules:
    # - domains/healthcare_utils.py for financial utilities
    # - core/utils/type_conversion.py for type safety utilities  
    # - core/utils/database_helpers.py for connection management
    
    @staticmethod
    def identify_duplicate_methods() -> List[str]:
        """Methods commonly duplicated across healthcare modules."""
        return [
            "_ensure_decimal",
            "_get_negotiated_rate", 
            "_get_patient_coverage_data",
            "_validate_database_connection"
        ]
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
        # Route through: intake → document_processor → clinical_research_agent
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

## Updated PHI Handling (2025-08-14)

- Literature authorship and publication metadata are not PHI and should be preserved.
- Error logs must not include patient identifiers; use DIAGNOSTIC markers and previews capped to 200 chars.
- Minimum Necessary still applies to EHR data; not applicable to public literature metadata.

## Medical Data Processing Patterns (2025-08-14)

- Normalize literature sources with DOI/PMID/URL keys; deduplicate on that precedence.
- Provide DOI link first, then PubMed link; include year, journal, and abstract snippet when present.
- Always return a disclaimer and a readable summary even on timeouts or upstream errors.

---
