# AI Instructions for Healthcare Scripts Development

## Purpose

**DATABASE-FIRST SCRIPTS**: All healthcare scripts must use databases as primary data source unless explicitly designed for database setup.

AI guidance for developing and maintaining healthcare automation scripts, deployment scripts, testing utilities, and system administration tools with enhanced synthetic data generation and offline capabilities.

## CRITICAL: Database-First Script Requirements

**All healthcare scripts** must:
- Require database connectivity for healthcare operations
- Fail gracefully with clear error messages when database unavailable
- Provide database setup guidance in error messages
- Generate PHI-like synthetic data for proper PHI detection testing

### Script Database Validation Pattern

**✅ REQUIRED: Database Connectivity Check**
```bash
#!/bin/bash
# Standard healthcare script initialization

check_database_connectivity() {
    python3 -c "
import sys
sys.path.append('/home/intelluxe')
try:
    from core.dependencies import get_database_connection
    import asyncio
    async def test():
        conn = await get_database_connection()
        await conn.execute('SELECT version()')
        return True
    asyncio.run(test())
except Exception as e:
    print(f'ERROR: Database required for healthcare operations: {e}', file=sys.stderr)
    print('Please run: make deps && ensure PostgreSQL is running', file=sys.stderr)
    sys.exit(1)
"
}

# Call at script start
check_database_connectivity
```

## Healthcare Script Development Patterns

### Script Safety Requirements
- All scripts must use synthetic data for development and testing
- Never hardcode PHI or production credentials
- Include comprehensive error handling and rollback procedures
- Log all script operations for audit compliance

### Synthetic Data Generation Scripts
```bash
# When working on generate_synthetic_healthcare_data.py
# ✅ CORRECT: Synthetic data generation patterns

#!/usr/bin/env python3
"""Generate synthetic healthcare data for development and testing."""

import json
import random
from faker import Faker
from typing import Dict, List

# Initialize faker with healthcare providers
fake = Faker(['en_US'])
fake.add_provider('faker.providers.medical')

def generate_synthetic_patient() -> Dict[str, str]:
    """Generate a synthetic patient record."""
    return {
        'patient_id': f"PT{random.randint(100000, 999999)}",
        'name': fake.name(),
        'dob': fake.date_of_birth(minimum_age=18, maximum_age=90).isoformat(),
        'phone': fake.phone_number(),
        'email': fake.email(),
        'address': fake.address(),
        'insurance_id': f"INS{random.randint(100000, 999999)}",
        'mrn': f"MRN{random.randint(100000, 999999)}"
    }
```

### Compliance Check Scripts
```bash
# When working on healthcare-compliance-check.py
# ✅ CORRECT: Compliance validation patterns

def check_phi_exposure():
    """Check for potential PHI exposure in logs and configs."""
    
    phi_patterns = [
        r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
        r'\b\d{3}-\d{3}-\d{4}\b',  # Phone
        r'MRN[:\s]*\d+',           # Medical Record Number
    ]
    
    violations = []
    
    # Check log files
    for log_file in find_log_files():
        violations.extend(scan_file_for_patterns(log_file, phi_patterns))
    
    # Check configuration files
    for config_file in find_config_files():
        violations.extend(scan_file_for_patterns(config_file, phi_patterns))
    
    return violations
```

### Deployment Scripts
```bash
# When working on deployment scripts (auto-upgrade.sh, bootstrap.sh, etc.)
# ✅ CORRECT: Healthcare deployment patterns

#!/bin/bash
set -euo pipefail

# Healthcare deployment safety checks
validate_healthcare_environment() {
    echo "🏥 Validating healthcare environment..."
    
    # Check required environment variables
    required_vars=(
        "HEALTHCARE_AUDIT_ENABLED"
        "PHI_MONITORING_ENABLED"
        "HIPAA_COMPLIANCE_MODE"
    )
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            echo "❌ Required healthcare environment variable not set: $var"
            exit 1
        fi
    done
    
    echo "✅ Healthcare environment validation passed"
}

# Pre-deployment PHI safety check
check_phi_safety() {
    echo "🔒 Running PHI safety checks..."
    
    if python3 scripts/healthcare-compliance-check.py --check-phi; then
        echo "✅ PHI safety check passed"
    else
        echo "❌ PHI safety violations detected - aborting deployment"
        exit 1
    fi
}
```

### Testing Scripts
```bash
# When working on test scripts (test.sh, run_integration_tests.py, etc.)
# ✅ CORRECT: Healthcare testing patterns

def run_healthcare_tests():
    """Run healthcare-specific test suites with synthetic data."""
    
    # Setup synthetic data environment
    setup_synthetic_data()
    
    test_suites = [
        'tests/test_phi_monitoring.py',
        'tests/test_healthcare_logging.py', 
        'tests/test_agent_compliance.py',
        'tests/test_fhir_integration.py'
    ]
    
    results = []
    for suite in test_suites:
        print(f"🧪 Running {suite}...")
        result = run_test_suite(suite)
        results.append(result)
        
        # Verify no PHI was exposed during testing
        verify_no_phi_in_test_logs(suite)
    
    return results
```

### System Administration Scripts
```bash
# When working on system admin scripts
# ✅ CORRECT: Healthcare system administration

check_healthcare_system_health() {
    echo "🏥 Checking healthcare system health..."
    
    # Check critical healthcare services
    services=(
        "healthcare-logger"
        "phi-monitor" 
        "audit-trail"
        "fhir-api"
    )
    
    for service in "${services[@]}"; do
        if systemctl is-active --quiet "$service"; then
            echo "✅ $service is running"
        else
            echo "❌ $service is not running"
            # Attempt to restart with proper logging
            systemctl restart "$service"
            log_healthcare_event "service.restart" "{\"service\": \"$service\"}"
        fi
    done
}
```

### Configuration Scripts
```python
# When working on configuration management scripts
def update_healthcare_config(config_updates: Dict[str, Any]):
    """Update healthcare configuration with validation."""
    
    # Load current config
    current_config = load_healthcare_config()
    
    # Validate proposed changes
    for key, value in config_updates.items():
        if not validate_config_change(key, value):
            raise ConfigValidationError(f"Invalid config change: {key}={value}")
    
    # Apply changes with backup
    backup_config(current_config)
    
    try:
        apply_config_changes(config_updates)
        validate_system_after_config_change()
        log_healthcare_event('config.updated', {'changes': list(config_updates.keys())})
    except Exception as e:
        restore_config_from_backup()
        raise ConfigUpdateError(f"Config update failed: {e}")
```

## Script Documentation Requirements
- Include clear usage examples with synthetic data
- Document all command-line arguments and options
- Provide rollback procedures for deployment scripts
- Include logging and audit trail information
- Add compliance notes for healthcare-specific operations

## Error Handling Patterns
- Always include rollback procedures
- Log all errors for audit compliance
- Provide clear error messages with next steps
- Never expose sensitive information in error messages
- Include contact information for script failures
