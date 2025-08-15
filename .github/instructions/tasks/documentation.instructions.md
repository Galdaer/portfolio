# Healthcare Documentation Patterns

**WORKFLOW CONTROL**: All workflows are controlled by `copilot-instructions.md`. This file provides implementation patterns only.

## Medical Disclaimer Templates

```python
# Standard medical disclaimer for healthcare AI
MEDICAL_DISCLAIMER = """
This system provides information for healthcare professionals only.
Not intended for direct patient diagnosis or treatment decisions.
All medical decisions require licensed healthcare provider oversight.
"""

# API documentation disclaimer
API_DISCLAIMER = """
Healthcare AI API - For authorized healthcare providers only.
Requires valid credentials and HIPAA compliance training.
All interactions logged for audit compliance.
"""
```

## PHI-Safe Documentation

```python
# Document functions without exposing PHI
def document_patient_function():
    """
    Process patient data for clinical workflow.
    
    Args:
        patient_data: Structured patient information (PHI-protected)
        encounter_type: Type of clinical encounter
        
    Returns:
        ProcessingResult: Analysis results for provider review
        
    Example:
        # Use with synthetic data only in documentation
        result = process_patient(synthetic_patient_data, "annual_checkup")
    """
    pass

# Document database schemas safely
class PatientDocumentation:
    """
    Patient data model documentation.
    
    Fields:
        patient_id: Unique identifier (UUID)
        demographics: Basic demographic data
        medical_history: Clinical history summary
        
    Note: All examples use synthetic data. Never include real PHI.
    """
```

## README Templates

```markdown
# Healthcare AI Module

## Medical Disclaimer
This system provides clinical decision support for healthcare professionals only.
Not intended for direct patient care without provider oversight.

## Usage
```python
from healthcare_module import process_clinical_data

# Process with proper medical oversight
result = process_clinical_data(patient_data, provider_context)
```

## Compliance
- HIPAA audit logging enabled
- PHI detection and protection active
- All interactions require provider authentication
```

## API Documentation

```python
# FastAPI route documentation
@app.post("/clinical/analyze")
async def analyze_clinical_data(
    data: ClinicalDataRequest,
    provider: ProviderAuth = Depends(verify_provider)
) -> ClinicalAnalysis:
    """
    Analyze clinical data for healthcare provider review.
    
    **Medical Disclaimer**: For healthcare professional use only.
    Results require clinical validation by licensed provider.
    
    **Security**: All requests logged, PHI protection active.
    """
```

## Code Comments

```python
# Medical data processing - provider oversight required
def process_medical_data(patient_data: Dict) -> Dict:
    # HIPAA: Log access for audit trail
    audit_logger.log_phi_access(provider_id, patient_id)
    
    # Medical safety: Validate input structure
    if not validate_medical_data_structure(patient_data):
        raise MedicalDataError("Invalid medical data structure")
    
    # Clinical processing - requires provider validation
    results = clinical_analyzer.process(patient_data)
    
    # Medical disclaimer: Mark results as requiring provider review
    results["provider_review_required"] = True
    results["medical_disclaimer"] = MEDICAL_DISCLAIMER
    
    return results
```

## Synthetic Data Examples

```python
# Safe examples for documentation
SYNTHETIC_EXAMPLES = {
    "patient_id": "PT-DEMO-12345",
    "encounter_id": "ENC-TEST-67890", 
    "provider_id": "DR-SAMPLE-001",
    "note": "SYNTHETIC: Routine checkup, patient reports feeling well"
}

# Mark all test data clearly
SYNTHETIC_MARKER = "SYNTHETIC_DATA_NOT_REAL_PHI"
```

## Error Documentation

```python
# Document errors without exposing PHI
try:
    result = process_patient_encounter(encounter_data)
except PatientDataError as e:
    # Log error without PHI
    logger.error(f"Patient processing failed: {type(e).__name__}")
    # Include synthetic example for debugging docs
    logger.debug(f"Example error pattern: {SYNTHETIC_ERROR_EXAMPLE}")
```

## Test Documentation

```python
# Document tests with synthetic data only
def test_patient_processing():
    """Test patient data processing with synthetic data."""
    # Use clearly marked synthetic data
    synthetic_patient = {
        "id": "SYNTHETIC-PT-001",
        "data": "CLEARLY_MARKED_TEST_DATA",
        "note": "This is synthetic data for testing only"
    }
    
    result = process_patient(synthetic_patient)
    assert result["processed"] == True
    assert "medical_disclaimer" in result
```
