````instructions
# Healthcare Code Review Patterns

**WORKFLOW CONTROL**: All workflows are controlled by `copilot-instructions.md`. This file provides implementation patterns only.

## Medical Safety Review

```python
# Check for medical advice prevention
def check_medical_advice(code: str) -> bool:
    forbidden_patterns = [
        "diagnose", "treat", "prescribe", "medical advice",
        "cure", "therapy recommendation"
    ]
    return any(pattern in code.lower() for pattern in forbidden_patterns)

# Verify medical disclaimers
def verify_medical_disclaimer(module: str) -> bool:
    required_disclaimer = "healthcare professional use only"
    return required_disclaimer.lower() in module.lower()
```

## PHI Protection Review

```python
# Check for PHI exposure
phi_patterns = [
    r"\b\d{3}-\d{2}-\d{4}\b",  # SSN pattern
    r"\b[A-Z]{2}\d{7}\b",      # Medical record pattern
    r"\(\d{3}\)\s*\d{3}-\d{4}" # Phone pattern
]

def scan_for_phi_in_code(code: str) -> List[str]:
    found_patterns = []
    for pattern in phi_patterns:
        if re.search(pattern, code):
            found_patterns.append(pattern)
    return found_patterns
```

## Financial Calculation Review

```python
# Check for proper decimal usage
def check_financial_calculations(code: str) -> List[str]:
    issues = []
    
    # Flag float usage for money
    if "float" in code and any(word in code for word in ["price", "cost", "amount", "billing"]):
        issues.append("Use Decimal for financial calculations, not float")
    
    # Check for division without zero protection
    if "/" in code and "if" not in code:
        issues.append("Add zero-division protection")
    
    return issues

# Example proper financial code
from decimal import Decimal

def calculate_copay(amount: Decimal, percentage: Decimal) -> Decimal:
    if percentage == 0:
        return Decimal('0')
    return amount * (percentage / Decimal('100'))
```

## Database Resource Review

```python
# Check for proper resource cleanup
def check_db_resources(code: str) -> List[str]:
    issues = []
    
    if "connection =" in code and "connection.close()" not in code:
        issues.append("Missing connection.close()")
    
    if "async with" not in code and "await" in code:
        issues.append("Use async context managers for DB operations")
    
    return issues

# Example proper database pattern
async def proper_db_usage():
    async with get_db_connection() as connection:
        result = await connection.execute(query)
        return result
    # Connection automatically closed
```

## Code Duplication Review

```python
# Common duplication patterns to flag
duplication_checks = [
    "Similar import blocks across files",
    "Repeated validation logic", 
    "Duplicate error handling patterns",
    "Magic numbers that should be constants",
    "Repeated SQL query patterns"
]

# Example consolidation
# Instead of repeating everywhere:
PATIENT_ID_PATTERN = r"^PT-\d{6}$"
ENCOUNTER_ID_PATTERN = r"^ENC-\d{8}$"
```

## Synthetic Data Review

```python
# Verify test data is synthetic
def check_synthetic_data(code: str) -> bool:
    synthetic_markers = [
        "SYNTHETIC", "TEST", "DEMO", "SAMPLE", 
        "FAKE", "MOCK", "PLACEHOLDER"
    ]
    
    # Check if test data includes markers
    if any(marker in code for marker in ["patient_data", "test_data", "example"]):
        return any(marker in code.upper() for marker in synthetic_markers)
    
    return True

# Example proper synthetic data
SYNTHETIC_PATIENT = {
    "id": "SYNTHETIC-PT-001",
    "name": "Demo Patient (NOT REAL)",
    "note": "SYNTHETIC_DATA_FOR_TESTING_ONLY"
}
```

## Healthcare Compliance Review

```python
# Audit logging check
def check_audit_logging(code: str) -> bool:
    if "patient" in code.lower() or "phi" in code.lower():
        return "audit_log" in code or "log_access" in code
    return True

# Access control review
def check_access_control(code: str) -> List[str]:
    issues = []
    
    if "@app.route" in code or "@router." in code:
        if "auth" not in code and "login" not in code:
            issues.append("Missing authentication check")
    
    return issues
```
 
## Orchestrator Alignment Checklist (2025-08-14)

- Routing
	- [ ] Exactly one agent selected per request (no implicit helpers)
	- [ ] No always-on medical_search; invoked only when selected
- Provenance
	- [ ] Human responses include agent provenance header when enabled
	- [ ] Agent payloads include `agent_name` when available
- Fallback
	- [ ] Base fallback path returns safe, non-medical response with disclaimers
	- [ ] No business logic in pipeline; fallback handled by healthcare-api
- Timeouts & Resilience
	- [ ] `timeouts.per_agent_default` respected; `per_agent_hard_cap` enforced
	- [ ] Metrics/logging are non-blocking
- Formatting & Contracts
	- [ ] Agents prefer `formatted_summary` for human UI
	- [ ] JSON contracts unchanged; human formatting added at API layer
- Configuration
	- [ ] `services/user/healthcare-api/config/orchestrator.yml` is the source of truth
	- [ ] PRs document any changes to routing/timeouts/provenance/fallback keys
````
