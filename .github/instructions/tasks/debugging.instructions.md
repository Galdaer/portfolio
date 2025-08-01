# Healthcare AI Debugging Instructions

## Purpose

Specialized debugging guidance for healthcare AI systems with PHI protection and medical compliance requirements.

## Healthcare-Specific Debugging Patterns

### PHI-Safe Debugging

```python
# ✅ CORRECT: Debug without exposing PHI
def debug_patient_processing(patient_id: str, error: Exception):
    """Debug patient processing errors without PHI exposure."""

    # Log error with anonymized patient reference
    logger.error(
        f"Patient processing failed",
        extra={
            "patient_hash": hashlib.sha256(patient_id.encode()).hexdigest()[:8],
            "error_type": type(error).__name__,
            "error_message": str(error),
            "stack_trace": traceback.format_exc()
        }
    )

    # ❌ NEVER: logger.error(f"Patient {patient_name} failed: {error}")

# ✅ CORRECT: Safe data sampling for debugging
def get_debug_sample(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Get anonymized sample data for debugging."""
    return [
        {k: "[REDACTED]" if is_phi_field(k) else v for k, v in record.items()}
        for record in data[:3]  # Small sample only
    ]
```

### Medical Logic Debugging

```python
# ✅ CORRECT: Validate medical data without interpretation
def debug_soap_note_processing(soap_data: Dict[str, Any]):
    """Debug SOAP note processing with medical data validation."""

    required_sections = ["subjective", "objective", "assessment", "plan"]

    for section in required_sections:
        if section not in soap_data:
            logger.warning(f"Missing SOAP section: {section}")
        elif not soap_data[section].strip():
            logger.warning(f"Empty SOAP section: {section}")

    # Validate structure without interpreting medical content
    if "assessment" in soap_data:
        assessment = soap_data["assessment"]
        if not any(keyword in assessment.lower() for keyword in ["diagnosis", "impression", "findings"]):
            logger.info("Assessment may need clinical review for completeness")
```

### Healthcare Integration Debugging

```python
# ✅ CORRECT: Debug EHR integration safely
def debug_ehr_integration(ehr_response: Dict[str, Any], transaction_id: str):
    """Debug EHR integration without exposing patient data."""

    safe_response = {
        "status_code": ehr_response.get("status_code"),
        "transaction_id": transaction_id,
        "response_size": len(str(ehr_response)),
        "has_patient_data": "patient" in ehr_response,
        "timestamp": datetime.utcnow().isoformat()
    }

    logger.debug("EHR Integration Debug", extra=safe_response)

    # Validate response structure
    if "error" in ehr_response:
        logger.error(f"EHR Error: {ehr_response['error']}")

    # Check for required fields without exposing content
    required_fields = ["patient_id", "encounter_id", "timestamp"]
    missing_fields = [f for f in required_fields if f not in ehr_response]
    if missing_fields:
        logger.warning(f"Missing EHR fields: {missing_fields}")
```

## Debugging Workflow

### Step 1: Reproduce Safely

1. Use synthetic test data only
2. Never use production PHI for debugging
3. Sanitize logs before sharing
4. Use anonymized patient references

### Step 2: Isolate Healthcare Components

1. Test medical logic separately from PHI handling
2. Validate SOAP note structure without content interpretation
3. Check compliance patterns independently
4. Test EHR integration with mock data

### Step 3: Validate Medical Compliance

```python
def validate_debugging_compliance():
    """Ensure debugging practices meet healthcare standards."""

    checks = {
        "phi_protection": check_no_phi_in_logs(),
        "audit_logging": check_debug_audit_trail(),
        "data_minimization": check_minimal_data_exposure(),
        "access_controls": check_debug_access_restrictions()
    }

    failed_checks = [check for check, passed in checks.items() if not passed]
    if failed_checks:
        raise ComplianceError(f"Debugging compliance failed: {failed_checks}")
```

### Step 4: Modern Development Tools

- Use **Ruff** for fast error detection: `ruff check --select E,W,F`
- Use **MyPy** for type safety: `mypy --strict`
- Use healthcare-specific linting rules
- Integrate with VS Code debugging with PHI-safe breakpoints

## Common Healthcare AI Debug Scenarios

### SOAP Note Processing Issues

```python
def debug_soap_processing(soap_note: str, expected_sections: List[str]):
    """Debug SOAP note processing issues."""

    # Parse sections safely
    sections = extract_soap_sections(soap_note)

    # Validate without medical interpretation
    debug_info = {
        "total_length": len(soap_note),
        "sections_found": list(sections.keys()),
        "sections_expected": expected_sections,
        "missing_sections": [s for s in expected_sections if s not in sections],
        "empty_sections": [s for s, content in sections.items() if not content.strip()]
    }

    logger.debug("SOAP Processing Debug", extra=debug_info)
    return debug_info
```

### Agent Communication Debugging

```python
def debug_agent_communication(agent_name: str, message: Dict[str, Any]):
    """Debug inter-agent communication safely."""

    safe_message = {
        "agent": agent_name,
        "message_type": message.get("type"),
        "message_size": len(str(message)),
        "has_patient_context": "patient_id" in message,
        "timestamp": message.get("timestamp")
    }

    # Log communication patterns without exposing content
    logger.debug("Agent Communication", extra=safe_message)

    # Validate message structure
    if "type" not in message:
        logger.error(f"Agent {agent_name} sent message without type")

    if "patient_id" in message and not is_valid_patient_id(message["patient_id"]):
        logger.error(f"Agent {agent_name} sent invalid patient_id format")
```

## Error Handling Patterns

### Healthcare-Safe Exception Handling

```python
class HealthcareSafeException(Exception):
    """Exception that safely logs healthcare errors without PHI exposure."""

    def __init__(self, message: str, patient_hash: str = None, context: Dict[str, Any] = None):
        super().__init__(message)
        self.patient_hash = patient_hash
        self.context = context or {}

        # Log safely
        logger.error(
            message,
            extra={
                "patient_hash": patient_hash,
                "context": {k: v for k, v in self.context.items() if not is_phi_field(k)}
            }
        )

# Usage
try:
    process_patient_data(patient_data)
except ValidationError as e:
    raise HealthcareSafeException(
        "Patient data validation failed",
        patient_hash=hash_patient_id(patient_data["id"]),
        context={"validation_errors": e.errors}
    )
```

### Compliance-Aware Debugging Tools

```python
def safe_debug_print(data: Any, context: str = ""):
    """Print debug information with PHI protection."""

    if isinstance(data, dict):
        safe_data = {
            k: "[PHI_REDACTED]" if is_phi_field(k) else v
            for k, v in data.items()
        }
    elif isinstance(data, str) and contains_phi_patterns(data):
        safe_data = "[PHI_CONTENT_REDACTED]"
    else:
        safe_data = data

    print(f"DEBUG {context}: {safe_data}")

def debug_trace_healthcare_function(func):
    """Decorator for tracing healthcare functions safely."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Log function entry without PHI
        safe_args = [str(type(arg)) for arg in args]
        safe_kwargs = {k: type(v) for k, v in kwargs.items()}

        logger.debug(f"Entering {func.__name__}", extra={
            "args_types": safe_args,
            "kwargs_types": safe_kwargs
        })

        try:
            result = func(*args, **kwargs)
            logger.debug(f"Exiting {func.__name__} successfully")
            return result
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {type(e).__name__}")
            raise

    return wrapper
```

## Debugging Checklist

### Before Starting Debug Session

- [ ] Verify using synthetic data only
- [ ] Enable audit logging for debug session
- [ ] Set up PHI-safe logging configuration
- [ ] Prepare anonymized test cases

### During Debugging

- [ ] Check for PHI exposure in logs/console
- [ ] Validate medical logic without interpretation
- [ ] Test compliance patterns independently
- [ ] Use modern development tools (Ruff, MyPy)

### After Debugging

- [ ] Clear any temporary debug data
- [ ] Review logs for accidental PHI exposure
- [ ] Document debugging insights safely
- [ ] Update test cases based on findings

Remember: Healthcare debugging requires balancing technical insight with strict PHI protection and medical compliance standards.
