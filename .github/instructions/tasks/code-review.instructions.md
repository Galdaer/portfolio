# Healthcare AI Code Review Instructions

## Purpose

Specialized code review guidance for healthcare AI systems emphasizing medical compliance, PHI protection, and healthcare-specific patterns.

## Healthcare Code Review Checklist

### Medical Safety & Compliance

```python
# ✅ REVIEW: Medical advice prevention
def review_medical_advice_prevention(code: str) -> List[str]:
    """Check code for inappropriate medical advice patterns."""

    warnings = []

    # Flag medical advice patterns
    advice_patterns = [
        r"diagnosis.*=.*recommend",
        r"treatment.*should.*take",
        r"medication.*dosage",
        r"patient.*should.*do"
    ]

    for pattern in advice_patterns:
        if re.search(pattern, code, re.IGNORECASE):
            warnings.append(f"Potential medical advice detected: {pattern}")

    # Check for proper disclaimers
    if "medical advice" not in code.lower() and any(term in code.lower() for term in ["diagnosis", "treatment", "medication"]):
        warnings.append("Missing medical advice disclaimer in medical context")

    return warnings

# ✅ REVIEW: PHI handling validation
def review_phi_handling(code: str) -> List[str]:
    """Validate PHI handling patterns in code."""

    issues = []

    # Check for direct PHI logging
    if re.search(r'log.*patient.*name|print.*ssn|console.*phone', code, re.IGNORECASE):
        issues.append("Direct PHI logging detected - use anonymized logging")

    # Check for PHI in comments
    if re.search(r'#.*\d{3}-\d{2}-\d{4}|#.*\(\d{3}\)\s*\d{3}-\d{4}', code):
        issues.append("PHI patterns in comments - remove or anonymize")

    # Validate encryption for PHI fields
    phi_fields = ["ssn", "phone", "email", "address", "patient_name"]
    for field in phi_fields:
        if field in code and "encrypt" not in code:
            issues.append(f"PHI field '{field}' may need encryption consideration")

    return issues
```

### Healthcare-Specific Code Patterns

```python
# ✅ REVIEW: SOAP note processing
def review_soap_note_handling(code: str) -> List[str]:
    """Review SOAP note processing for proper medical formatting."""

    recommendations = []

    # Check for proper SOAP structure
    required_sections = ["subjective", "objective", "assessment", "plan"]
    soap_sections_found = sum(1 for section in required_sections if section in code.lower())

    if soap_sections_found > 0 and soap_sections_found < 4:
        recommendations.append("SOAP note processing should handle all four sections: S.O.A.P")

    # Check for medical terminology standardization
    if "medical_term" in code or "abbreviation" in code:
        if "standardize" not in code:
            recommendations.append("Consider medical terminology standardization")

    # Validate assessment vs diagnosis distinction
    if "diagnosis" in code and "assessment" not in code:
        recommendations.append("Use 'assessment' for AI systems, 'diagnosis' is clinical judgment")

    return recommendations

# ✅ REVIEW: EHR integration patterns
def review_ehr_integration(code: str) -> List[str]:
    """Review EHR integration code for compliance patterns."""

    issues = []

    # Check for audit logging
    if "ehr" in code.lower() and "audit" not in code.lower():
        issues.append("EHR integration should include audit logging")

    # Check for proper error handling
    if "ehr_request" in code and "except" not in code:
        issues.append("EHR requests need comprehensive error handling")

    # Validate FHIR compliance if applicable
    if "fhir" in code.lower():
        if "validate" not in code:
            issues.append("FHIR resources should be validated")

    return issues
```

### Modern Development Standards

```python
# ✅ REVIEW: Type safety compliance
def review_type_annotations(code: str) -> List[str]:
    """Check for comprehensive type annotations."""

    issues = []

    # Check function return types
    function_matches = re.findall(r'def\s+(\w+)\([^)]*\):', code)
    for func in function_matches:
        if f"def {func}" in code and "->" not in code:
            issues.append(f"Function '{func}' missing return type annotation")

    # Check class attribute types
    if "class " in code and ":" in code:
        if not re.search(r'self\.\w+:\s*\w+', code):
            issues.append("Class attributes should have type annotations")

    # Check for Dict[str, Any] patterns
    if "dict" in code.lower() and "Dict[str, Any]" not in code:
        issues.append("Use explicit Dict[str, Any] typing instead of dict")

    return issues

# ✅ REVIEW: Ruff compliance patterns
def review_ruff_compliance(code: str) -> List[str]:
    """Check code against Ruff formatting standards."""

    suggestions = []

    # Check for import sorting
    imports = re.findall(r'^import\s+\w+|^from\s+\w+', code, re.MULTILINE)
    if len(imports) > 1:
        suggestions.append("Run 'ruff check --select I --fix' for import sorting")

    # Check line length
    long_lines = [line for line in code.split('\n') if len(line) > 100]
    if long_lines:
        suggestions.append(f"Consider breaking {len(long_lines)} lines over 100 characters")

    # Check for unused imports
    if re.search(r'^import\s+\w+', code, re.MULTILINE):
        suggestions.append("Run 'ruff check --select F401 --fix' to remove unused imports")

    return suggestions
```

## Healthcare-Specific Review Areas

### 1. Medical Data Validation

```python
# ✅ REVIEW CHECKLIST: Medical data processing
review_checklist = {
    "medical_terminology": [
        "Are medical terms used consistently?",
        "Is medical abbreviation expansion handled?",
        "Are ICD-10/CPT codes formatted correctly?"
    ],
    "soap_notes": [
        "Does SOAP processing maintain proper structure?",
        "Is there clear separation between sections?",
        "Are assessment vs diagnosis terms used correctly?"
    ],
    "clinical_workflows": [
        "Does the workflow follow clinical best practices?",
        "Are care transitions handled properly?",
        "Is provider handoff information preserved?"
    ]
}
```

### 2. Compliance & Security Review

```python
# ✅ REVIEW CHECKLIST: Healthcare compliance
compliance_checklist = {
    "hipaa_compliance": [
        "Is PHI properly encrypted at rest and in transit?",
        "Are access controls implemented for all PHI access?",
        "Is audit logging comprehensive and tamper-proof?"
    ],
    "medical_safety": [
        "Does code avoid making medical recommendations?",
        "Are medical disclaimers present where needed?",
        "Is there clear escalation to healthcare professionals?"
    ],
    "data_handling": [
        "Is data minimization principle followed?",
        "Are retention policies implemented correctly?",
        "Is cross-border data transfer compliant?"
    ]
}
```

### 3. Integration & Interoperability

```python
# ✅ REVIEW CHECKLIST: Healthcare integration
integration_checklist = {
    "ehr_integration": [
        "Are HL7 FHIR standards followed correctly?",
        "Is error handling comprehensive for EHR failures?",
        "Are transaction logs audit-compliant?"
    ],
    "agent_communication": [
        "Is inter-agent communication secure?",
        "Are message formats consistent across agents?",
        "Is there proper timeout and retry logic?"
    ],
    "external_apis": [
        "Are healthcare API calls properly authenticated?",
        "Is rate limiting implemented for external services?",
        "Are API responses validated for medical correctness?"
    ]
}
```

## Review Process Workflow

### Pre-Review Setup

1. **Environment Check**: Ensure review environment has no access to production PHI
2. **Context Loading**: Review related healthcare compliance documentation
3. **Tool Preparation**: Set up Ruff, MyPy, and healthcare-specific linters

### Code Review Steps

```python
def healthcare_code_review_process(pull_request: PullRequest) -> ReviewResult:
    """Comprehensive healthcare code review process."""

    review_results = {
        "medical_safety": [],
        "phi_compliance": [],
        "technical_quality": [],
        "integration_patterns": []
    }

    for file_change in pull_request.changed_files:
        # Medical safety review
        review_results["medical_safety"].extend(
            review_medical_advice_prevention(file_change.content)
        )

        # PHI handling review
        review_results["phi_compliance"].extend(
            review_phi_handling(file_change.content)
        )

        # Technical quality review
        review_results["technical_quality"].extend(
            review_type_annotations(file_change.content)
        )

        # Healthcare integration review
        if "ehr" in file_change.path or "agent" in file_change.path:
            review_results["integration_patterns"].extend(
                review_ehr_integration(file_change.content)
            )

    return ReviewResult(review_results)
```

### Review Comments Templates

#### Medical Safety Issues

```markdown
**⚠️ Medical Safety Concern**

This code appears to provide medical advice/recommendations. In healthcare AI systems, we must:

- Focus on administrative and documentation support only
- Include medical disclaimers: "This system does not provide medical advice"
- Escalate medical decisions to qualified healthcare professionals

**Suggested Action**: Refactor to provide administrative support without medical interpretation.
```

#### PHI Protection Issues

```markdown
**🔒 PHI Protection Required**

This code handles Protected Health Information (PHI) and needs additional safeguards:

- Encrypt PHI fields at rest and in transit
- Implement audit logging for all PHI access
- Use anonymized logging (patient hash instead of identifiers)
- Apply data minimization principles

**Suggested Action**: Implement PHI protection patterns from healthcare security guidelines.
```

#### Healthcare Integration Issues

```markdown
**🏥 Healthcare Integration Pattern**

This integration with healthcare systems should follow established patterns:

- Use HL7 FHIR standards for data exchange
- Implement comprehensive error handling and retry logic
- Include audit logging for compliance requirements
- Validate all healthcare data formats

**Suggested Action**: Review healthcare integration documentation and apply standard patterns.
```

## Review Automation Integration

### GitHub Actions Integration

```yaml
# Add to healthcare-ai-validation.yml
- name: Healthcare Code Review Automation
  run: |
    echo "🏥 Running automated healthcare code review..."

    # Check for medical advice patterns
    python3 scripts/healthcare-compliance-check.py --mode=review

    # Validate PHI handling
    python3 scripts/check-phi-exposure.py --review-mode

    # Run healthcare-specific linting
    ruff check --config=pyproject.toml --select=HC  # Healthcare-specific rules
```

### Modern Development Tools Integration

- **Ruff Integration**: `ruff check --select=E,W,F,HC` (with healthcare-specific rules)
- **MyPy Healthcare**: Custom mypy configuration for healthcare type checking
- **Pre-commit Hooks**: Healthcare compliance validation in pre-commit pipeline
- **VS Code Integration**: Healthcare-specific snippets and linting rules

## Review Success Criteria

### Checklist for Approval

- [ ] **Medical Safety**: No medical advice or clinical recommendations
- [ ] **PHI Protection**: All PHI handling follows encryption and audit requirements
- [ ] **Type Safety**: Comprehensive type annotations and MyPy compliance
- [ ] **Modern Tools**: Ruff formatting and linting standards met
- [ ] **Healthcare Integration**: HL7 FHIR standards and error handling patterns
- [ ] **Documentation**: Medical disclaimers and usage guidance included
- [ ] **Testing**: Healthcare-specific test coverage with synthetic data

### Escalation Criteria

Escalate to healthcare compliance team if:

- Medical advice patterns detected
- PHI exposure risks identified
- Compliance requirements unclear
- Integration with critical healthcare systems

Remember: Healthcare code review balances technical excellence with strict medical compliance and patient safety requirements.
