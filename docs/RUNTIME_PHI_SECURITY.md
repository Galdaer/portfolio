# Healthcare PHI Security: Runtime-First Approach

## Overview

Based on your insight that **PHI will never be in code** (it lives in databases), we've completely refactored the PHI security strategy from static code analysis to **runtime data leakage monitoring**.

## Key Changes

### 1. New Security Model

**OLD Approach (❌):**
- Scan source code for hardcoded PHI patterns
- Maintain test/tests directories with mock PHI data
- Focus on preventing PHI in code

**NEW Approach (✅):**
- PHI lives safely in databases only
- Monitor runtime outputs (logs, data pipelines) for PHI leakage
- Tests connect to database with synthetic data
- Focus on data pipeline security

### 2. Runtime PHI Leakage Detection

**New Script:** `scripts/check-runtime-phi-leakage.sh`

**What it monitors:**
- Log files (`logs/`, `*.log`, `*.out`, `*.err`)
- Data export files (`*.csv`, `*.json`, `*.xlsx`)
- Database connection strings in logs
- SQL queries with patient data in outputs
- Debug/error messages with PHI
- Large data files that might contain PHI exports

**Safe patterns (excluded):**
- Synthetic data markers (`PAT001`, `555-XXX-XXXX`)
- Test domains (`example.com`, `synthetic.test`)
- Development configs (`localhost`, `127.0.0.1`)

### 3. Database-Backed Testing

**New Utility:** `tests/database_test_utils.py`

**Features:**
- `HealthcareTestCase` base class for tests
- Database connection to synthetic healthcare data
- Quick helper functions for test scenarios
- No hardcoded PHI in test code

**Example migration:**
```python
# ❌ OLD WAY
test_patient = {
    'ssn': '123-45-6789',  # PHI in code
    'name': 'John Doe'
}

# ✅ NEW WAY
class MyTest(HealthcareTestCase):
    def test_something(self):
        patient = self.get_sample_patient()  # From database
        # No PHI in code!
```

### 4. Updated CI/CD Pipeline

**GitHub Actions Changes:**
- Replace `check-phi-exposure.sh` with `check-runtime-phi-leakage.sh`
- Focus on runtime monitoring, not static code analysis
- Tests use database-backed synthetic data

## Implementation Files

### Core Security
- `scripts/check-runtime-phi-leakage.sh` - Runtime PHI leakage detection
- `tests/database_test_utils.py` - Database-backed test utilities

### Documentation & Examples
- `tests/migration_guide.py` - Migration documentation
- `tests/example_test_migration.py` - Test migration examples

### CI/CD
- `.github/workflows/healthcare-ai-validation.yml` - Updated with runtime monitoring

## Next Steps

### Immediate (Ready to Deploy)
1. ✅ Runtime PHI detection implemented
2. ✅ Database test utilities created
3. ✅ CI/CD pipeline updated
4. ✅ Migration examples provided

### Test Migration Strategy
The test/ and tests/ directories can be evaluated for migration:

**Current Status:**
- `test/` - Contains system/infrastructure tests (mostly BATS)
- `tests/healthcare_evaluation/` - Python tests, some already use synthetic data
- `tests/security/` - Security validation tests

**Recommendation:**
- Keep system tests in `test/` (they don't deal with PHI)
- Migrate Python tests in `tests/` to use database utilities
- Focus on tests that currently have hardcoded medical data

### Database Setup
Ensure PostgreSQL is running with synthetic healthcare data:
```bash
python3 scripts/generate_synthetic_healthcare_data.py --use-database
```

## Security Benefits

1. **Realistic Security Model**: PHI in databases, not code
2. **Runtime Monitoring**: Catch actual data leakage risks
3. **Compliance Focus**: Monitor what auditors care about (data handling)
4. **Development Friendly**: No false positives on legitimate dev patterns
5. **Scalable**: Database-backed tests scale better than hardcoded data

## Testing the New Approach

```bash
# Test runtime PHI detection
bash scripts/check-runtime-phi-leakage.sh

# Test database utilities
python3 tests/migration_guide.py

# Run example migration
python3 tests/example_test_migration.py
```

This approach aligns with real-world healthcare compliance where the focus is on **data handling and pipeline security**, not static code patterns.
