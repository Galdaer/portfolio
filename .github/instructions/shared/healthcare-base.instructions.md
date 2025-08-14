# Shared Healthcare AI Base Instructions

## Universal Healthcare Compliance Requirements

### HIPAA Compliance Framework
- All healthcare operations must maintain PHI protection
- Log all data access and modifications with full audit trails  
- Ensure proper access controls and authentication for all operations
- Follow data minimization principles - process only necessary information

### Medical Safety Guidelines
**CRITICAL**: AI systems provide administrative and analytical support only, never medical guidance
- If asked about medical symptoms, treatment, or diagnosis, respond: "I cannot provide medical advice. Please consult with a healthcare professional."
- Focus on data processing, documentation, and administrative workflows
- Escalate any medical interpretation questions to qualified healthcare staff

### Standard Medical Disclaimer
**IMPORTANT: This system provides administrative and analytical support only. It helps healthcare professionals with data processing, documentation, and workflow optimization. It does not provide medical advice, diagnosis, or treatment recommendations. All medical decisions must be made by qualified healthcare professionals based on individual patient assessment.**

## Shared Technical Patterns

### Healthcare Logging
```python
# Standard healthcare logging pattern
from core.infrastructure.healthcare_logger import get_healthcare_logger, healthcare_log_method, log_healthcare_event

# Use in all healthcare components
logger = get_healthcare_logger('component.name')

@healthcare_log_method
def process_healthcare_data(data):
    log_healthcare_event('operation.started', {'component': 'name'})
    # ... processing logic
    log_healthcare_event('operation.completed', {'component': 'name'})
```

### PHI Protection
```python
# Standard PHI monitoring pattern
from core.infrastructure.phi_monitor import phi_monitor, scan_for_phi, sanitize_healthcare_data

@phi_monitor
def handle_sensitive_data(data):
    # Scan for potential PHI exposure
    phi_risks = scan_for_phi(data)
    if phi_risks:
        raise PHIViolationError(f"Potential PHI detected: {phi_risks}")
    
    # Sanitize data before processing
    clean_data = sanitize_healthcare_data(data)
    return process_data(clean_data)
```

### Standard Validation Patterns
```python
# Healthcare data validation patterns
def validate_healthcare_input(data, required_fields):
    """Standard validation for healthcare data inputs."""
    for field in required_fields:
        if not data.get(field):
            return f"Missing required field: {field}"
    
    # Check for PHI exposure
    phi_risks = scan_for_phi(data)
    if phi_risks:
        return f"Potential PHI detected in fields: {phi_risks}"
    
    return "Valid"
```

## Integration Requirements
- All healthcare components must inherit these base patterns
- Use shared logging and PHI monitoring infrastructure  
- Follow consistent error handling and validation approaches
- Maintain audit trails for all healthcare operations

## Orchestrator Alignment (2025-08-14)

- Single-agent routing per request using local LLM; no implicit helpers
- Human responses include agent provenance header (API responsibility)
- Base fallback handled in healthcare-api with safe, non-medical messaging
- Honor timeouts from `services/user/healthcare-api/config/orchestrator.yml`
- Agents should emit `formatted_summary` for human UI; JSON contracts unchanged
