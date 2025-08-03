# Healthcare PHI Security Migration: Runtime-First Implementation

## Task Overview

Implement the new runtime-first PHI security model across the Intelluxe AI healthcare system. This represents a fundamental shift from static code analysis to runtime data leakage monitoring, based on the realistic principle that **PHI lives in databases, not code**.

## Background Context

The previous approach of scanning source code for hardcoded PHI patterns was unrealistic for production healthcare systems. The new approach focuses on:

1. **PHI in databases only** - never in source code
2. **Runtime monitoring** - logs, outputs, data pipelines  
3. **Database-backed testing** - synthetic data from PostgreSQL
4. **Practical compliance** - focus on what auditors actually check

## Reference Implementation

The new patterns are established in:
- `scripts/check-runtime-phi-leakage.sh` - Runtime PHI detection
- `tests/database_test_utils.py` - Database-backed test utilities  
- `tests/migration_guide.py` - Migration documentation
- `tests/example_test_migration.py` - Test migration examples
- `docs/RUNTIME_PHI_SECURITY.md` - Complete documentation

## Implementation Tasks

### 1. Update CI/CD Pipeline

**File**: `.github/workflows/healthcare-ai-validation.yml`

**Changes needed**:
- Replace `scripts/check-phi-exposure.sh` with `scripts/check-runtime-phi-leakage.sh`
- Update PHI detection job to focus on runtime outputs
- Ensure workflow uses synthetic data artifacts properly

**Pattern to follow**:
```yaml
# ❌ OLD: Static code analysis
- name: PHI Exposure Check
  run: bash scripts/check-phi-exposure.sh

# ✅ NEW: Runtime monitoring  
- name: Runtime PHI Leakage Detection
  run: bash scripts/check-runtime-phi-leakage.sh
```

### 2. Migrate Existing Tests

**Target directories**: `tests/healthcare_evaluation/`, `tests/security/`

**Migration pattern** (from `tests/example_test_migration.py`):
```python
# ❌ OLD WAY: Hardcoded test data
# test_patient = {
#     'ssn': '123-45-6789',  # ❌ Fake PHI in code
#     'name': 'John Doe'
# }

# ✅ NEW WAY: Database-backed synthetic data
from tests.database_test_utils import HealthcareTestCase

class MyTest(HealthcareTestCase):
    def test_something(self):
        patient = self.get_sample_patient()  # From database
        # Test logic here - no PHI in code!
```

**Specific files to migrate**:
- `tests/healthcare_evaluation/test_phase1_infrastructure.py`
- `tests/healthcare_evaluation/test_critical_fixes_validation.py`
- `tests/security/test_encryption_validation.py`
- Any tests with hardcoded medical/patient data

### 3. Update Healthcare Modules

**Target modules**: Any healthcare processing code that might log or output data

**Pattern to implement**:
```python
# ✅ Add runtime PHI protection to existing functions
def process_patient_data(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process patient data with runtime PHI monitoring."""
    
    # Ensure no PHI in logs
    logger.info(f"Processing patient: {patient_data.get('patient_id', 'UNKNOWN')}")
    # ❌ NEVER: logger.info(f"Processing patient: {patient_data['name']}")
    
    # Process data
    result = existing_processing_logic(patient_data)
    
    # Verify no PHI in output
    if contains_phi_patterns(result):
        logger.error("PHI detected in processing output - sanitizing")
        result = sanitize_phi(result)
    
    return result
```

### 4. Deprecate Old PHI Detection

**Files to update**:
- `scripts/check-phi-exposure.sh` - Add deprecation notice, redirect to new script
- Any code references to old PHI detection patterns
- Update documentation to reference new approach

### 5. Database Connection Validation

**Ensure tests can connect to synthetic data**:
- Verify `scripts/generate_synthetic_healthcare_data.py --use-database` works
- Test database connection in `tests/database_test_utils.py`
- Add database health checks to CI pipeline

## Implementation Priority

1. **HIGH**: Update CI/CD pipeline to use runtime PHI detection
2. **HIGH**: Migrate critical test files to database-backed approach
3. **MEDIUM**: Add runtime PHI protection to healthcare modules  
4. **LOW**: Deprecate old PHI detection scripts (with backward compatibility)

## Success Criteria

- [ ] CI/CD pipeline uses `check-runtime-phi-leakage.sh` instead of `check-phi-exposure.sh`
- [ ] At least 5 test files migrated to use `tests/database_test_utils.py` 
- [ ] No hardcoded PHI patterns in migrated tests
- [ ] Runtime PHI detection passes on all logs/outputs
- [ ] Database-backed tests can run successfully
- [ ] Documentation updated to reflect new approach

## Quality Standards

- Follow existing code patterns and style
- Maintain backward compatibility where possible
- Add medical disclaimers to healthcare functions
- Use type annotations consistently
- Test all changes with synthetic data

## Healthcare Compliance Notes

This migration improves compliance by:
- Eliminating fake PHI from source code
- Focusing security on actual data handling
- Implementing realistic production security patterns
- Enabling proper audit trails for data access

**CRITICAL**: Never use real PHI during implementation. All testing must use synthetic data from the database or the existing synthetic data files.

## Autonomous Work Guidelines

- Work continuously for 2-4 hours on this migration
- Start with CI/CD pipeline updates (highest impact)
- Migrate tests systematically using established patterns
- Document any issues or blockers encountered
- Validate changes with runtime PHI detection script

This represents a fundamental improvement in healthcare AI security modeling and should be implemented systematically across the codebase.
