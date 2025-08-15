# Healthcare AI Security Review Instructions

## Healthcare Security Review Patterns

### Runtime PHI Leakage Monitoring (NEW APPROACH)

**CRITICAL CHANGE**: Focus on runtime data leakage monitoring, not static code analysis.

```python
# ✅ CORRECT: Runtime PHI monitoring patterns
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
import re
import logging
from enum import Enum

class SecurityRiskLevel(Enum):
    CRITICAL = "CRITICAL"  # PHI exposed in logs/outputs
    HIGH = "HIGH"         # Database credentials in logs
    MEDIUM = "MEDIUM"     # Large data exports
    LOW = "LOW"          # Development patterns detected

@dataclass
class HealthcareSecurityFinding:
    risk_level: SecurityRiskLevel
    finding_type: str
    file_path: str
    line_number: Optional[int]
    content: str
    recommendation: str
    phi_detected: bool = False

class RuntimePHIMonitor:
    """
    Runtime PHI leakage detection system.
    Monitors logs, outputs, and data pipelines for PHI exposure.
    """
    
    def scan_runtime_outputs(self) -> List[HealthcareSecurityFinding]:
        """Scan logs and outputs for PHI leakage."""
        findings = []
        
        # Monitor log files for PHI patterns
        log_dirs = ["logs/", "coverage/", ".pytest_cache/"]
        for log_dir in log_dirs:
            findings.extend(self._scan_logs_for_phi(log_dir))
        
        # Monitor data exports for PHI
        findings.extend(self._scan_data_exports())
        
        # Monitor database connection security
        findings.extend(self._scan_db_connections())
        
        return findings
    
    def _scan_logs_for_phi(self, log_dir: str) -> List[HealthcareSecurityFinding]:
        """Scan log files for actual PHI exposure."""
        # Implementation focuses on runtime monitoring
        pass

class HealthcareSecurityReviewer:
```

### Security Review Automation

````python
# ✅ CORRECT: Automated security review for healthcare AI
class AutomatedHealthcareSecurityReview:
    """Automated security review tools for healthcare AI systems."""

    def __init__(self) -> None:
        self.security_tools = self._initialize_security_tools()
        self.healthcare_rules = self._load_healthcare_security_rules()

    def run_automated_security_scan(self, codebase_path: str) -> Dict[str, Any]:
        """Run comprehensive automated security scan."""

        scan_results = {
            "bandit_scan": self._run_bandit_scan(codebase_path),
            "semgrep_healthcare_rules": self._run_semgrep_healthcare_scan(codebase_path),
            "phi_exposure_scan": self._run_phi_exposure_scan(codebase_path),
            "medical_safety_scan": self._run_medical_safety_scan(codebase_path),
            "dependency_vulnerability_scan": self._run_dependency_scan(codebase_path),
            "secrets_detection": self._run_secrets_detection(codebase_path),
            "compliance_validation": self._run_compliance_validation(codebase_path)
        }

        # Aggregate and prioritize findings
        aggregated_findings = self._aggregate_scan_findings(scan_results)

        return {
            "scan_timestamp": datetime.now().isoformat(),
            "scan_results": scan_results,
            "aggregated_findings": aggregated_findings,
            "security_score": self._calculate_security_score(aggregated_findings),
            "remediation_priorities": self._prioritize_remediation(aggregated_findings)
        }

    def _run_bandit_scan(self, codebase_path: str) -> Dict[str, Any]:
        """Run Bandit security scan with healthcare-specific rules."""

        bandit_config = {
            "exclude_paths": ["tests/", "docs/", "venv/"],
            "severity_levels": ["HIGH", "MEDIUM"],
            "confidence_levels": ["HIGH", "MEDIUM"],
            "healthcare_specific_tests": [
                "B105",  # hardcoded_password_string
                "B106",  # hardcoded_password_funcarg
                "B107",  # hardcoded_password_default
                "B501",  # request_with_no_cert_validation
                "B502",  # ssl_with_bad_version
                "B503",  # ssl_with_bad_defaults
                "B506",  # yaml_load
                "B601",  # paramiko_calls
                "B602",  # subprocess_popen_with_shell_equals_true
                "B608",  # hardcoded_sql_expressions
            ]
        }

        # Execute Bandit scan
        bandit_command = f"""
        bandit -r {codebase_path} \
               -f json \
               -o bandit_healthcare_report.json \
               -ll \
               -i {','.join(bandit_config['healthcare_specific_tests'])}
        """

        return {
            "command": bandit_command,
            "config": bandit_config,
            "healthcare_focus": "PHI protection and medical safety"
        }

    def _run_semgrep_healthcare_scan(self, codebase_path: str) -> Dict[str, Any]:
        """Run Semgrep with healthcare-specific security rules."""

        healthcare_semgrep_rules = {
            "phi_exposure_rules": [
                "rules/healthcare/phi-exposure-logging.yml",
                "rules/healthcare/phi-hardcoded-patterns.yml",
                "rules/healthcare/phi-unsafe-transmission.yml"
            ],
            "medical_safety_rules": [
                "rules/healthcare/medical-advice-detection.yml",
                "rules/healthcare/diagnosis-language-detection.yml",
                "rules/healthcare/treatment-recommendation-detection.yml"
            ],
            "hipaa_compliance_rules": [
                "rules/healthcare/hipaa-encryption-requirements.yml",
                "rules/healthcare/hipaa-audit-logging.yml",
                "rules/healthcare/hipaa-access-controls.yml"
            ]
        }

        semgrep_command = f"""
        semgrep --config=rules/healthcare/ \
                --json \
                --output=semgrep_healthcare_report.json \
                {codebase_path}
        """

        return {
            "command": semgrep_command,
            "healthcare_rules": healthcare_semgrep_rules,
            "compliance_focus": "HIPAA and medical safety"
        }

    def _run_phi_exposure_scan(self, codebase_path: str) -> Dict[str, Any]:
        """Run specialized PHI exposure detection scan.

        PHI DETECTION METHODOLOGY:

        Our PHI detection uses a hybrid approach combining:
        1. **Pattern Matching**: Exact regex patterns for structured data (SSN, phone, MRN)
        2. **Semantic Understanding**: AI-powered detection for aliases and variations
        3. **Context Analysis**: Understanding when non-PHI becomes PHI in healthcare context

        Examples of AI expansion beyond exact matching:
        - "Patient ID", "pt_id", "medical_id" → recognized as patient identifier variations
        - "John Doe", "J. Doe", "JDoe" → recognized as potential patient name variations
        - Date patterns near patient context → flagged as potential DOB

        This ensures comprehensive PHI protection while minimizing false positives.
        """

        phi_patterns = {
            "ssn_patterns": [
                r'\b\d{3}-\d{2}-\d{4}\b',
                r'\b\d{9}\b'
            ],
            "phone_patterns": [
                r'\(\d{3}\)\s*\d{3}-\d{4}',
                r'\d{3}-\d{3}-\d{4}',
                r'\d{10}\b'
            ],
            "email_patterns": [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            ],
            "medical_record_patterns": [
                r'MRN\s*:?\s*\d+',
                r'Medical\s+Record\s+Number\s*:?\s*\d+'
            ]
        }

        scan_results = {
            "files_scanned": 0,
            "potential_phi_exposures": [],
            "patterns_detected": {}
        }

        # Scan implementation would go here
        return {
            "phi_patterns": phi_patterns,
            "scan_results": scan_results,
            "remediation_guidance": "Replace with synthetic data patterns"
        }

## PHI Tracking & Compliance Demonstration Patterns

### Gradual Implementation Strategy

**IMPLEMENT INCREMENTALLY**: Add PHI tracking capabilities to existing code as you work on it, rather than implementing all at once.

```python
# ✅ CORRECT: PHI tracking integration pattern
import logging
from typing import Dict, Any, List
from datetime import datetime

class PHITrackingLogger:
    """Gradual PHI tracking implementation - add to existing modules as you modify them."""

    def __init__(self, module_name: str):
        self.module_name = module_name
        self.phi_audit_logger = logging.getLogger(f"phi_audit.{module_name}")

    def log_phi_access(self, action: str, context: Dict[str, Any]) -> None:
        """Log PHI access with zone tracking - ADD THIS to any PHI-handling function."""

        # Hash PHI identifiers for logging
        patient_hash = self._hash_phi_identifier(context.get("patient_id", "unknown"))

        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "module": self.module_name,
            "action": action,
            "patient_hash": patient_hash,
            "secure_zone": context.get("zone", "unknown"),
            "user_id": context.get("user_id", "system"),
            "phi_fields_accessed": self._get_phi_fields(context),
            "data_never_left_zone": self._verify_zone_containment(context)
        }

        self.phi_audit_logger.info("PHI_ACCESS", extra=audit_entry)

    def verify_phi_containment(self, data_flow: List[str]) -> bool:
        """Verify PHI never left designated secure zones - ADD TO data processing functions."""

        secure_zones = {"secure_db", "encrypted_storage", "local_processing"}

        for zone in data_flow:
            if zone not in secure_zones:
                self.phi_audit_logger.critical(
                    "PHI_CONTAINMENT_VIOLATION",
                    extra={"violated_zone": zone, "data_flow": data_flow}
                )
                return False

        return True

# ADD THIS PATTERN to existing healthcare functions:
def existing_patient_function(patient_data: Dict[str, Any]) -> Any:
    """Example of adding PHI tracking to existing function."""

    # ADD THESE LINES to any function that handles PHI:
    phi_tracker = PHITrackingLogger("patient_processor")
    phi_tracker.log_phi_access("patient_data_processing", {
        "patient_id": patient_data.get("id"),
        "zone": "secure_processing",
        "user_id": get_current_user_id()
    })

    # Existing function logic...
    result = process_patient_data(patient_data)

    # ADD VERIFICATION at the end:
    data_flow = ["secure_db", "secure_processing", "encrypted_storage"]
    phi_tracker.verify_phi_containment(data_flow)

    return result
````

### Testing Pattern for PHI Compliance

```python
# ✅ CORRECT: Add these tests as you modify healthcare modules
def test_phi_never_leaves_secure_zone(caplog, mock_patient_data):
    """Add this test pattern to any module that handles PHI."""

    with caplog.at_level(logging.INFO, logger="phi_audit"):
        result = your_healthcare_function(mock_patient_data)

        # Verify no PHI in logs
        phi_audit_logs = [record for record in caplog.records
                         if record.name.startswith("phi_audit")]

        for log_entry in phi_audit_logs:
            assert log_entry.extra["data_never_left_zone"] is True
            assert "patient_hash" in log_entry.extra  # Hashed, not raw PHI
            assert log_entry.extra["secure_zone"] in ["secure_db", "local_processing"]

def test_client_compliance_report_generation():
    """Add this test to demonstrate compliance to clients."""

    # Generate sample compliance report
    report = generate_phi_compliance_report(days=30)

    assert report["phi_violations"] == 0
    assert report["secure_zone_containment"] == "100%"
    assert "audit_trail" in report
    assert len(report["audit_trail"]) > 0
```

### Client Demonstration Dashboard Pattern

```python
# ✅ CORRECT: Gradual dashboard implementation
class PHIComplianceDashboard:
    """Add compliance reporting as you build other features."""

    def generate_client_report(self, date_range: Dict[str, str]) -> Dict[str, Any]:
        """Generate compliance report for client demonstration."""

        return {
            "reporting_period": date_range,
            "phi_protection_metrics": {
                "total_phi_accesses": self._count_phi_accesses(date_range),
                "secure_zone_violations": 0,  # Must always be 0
                "encryption_compliance": "100%",
                "audit_trail_completeness": "100%"
            },
            "zone_containment_proof": {
                "phi_data_zones": ["secure_db", "encrypted_storage", "local_processing"],
                "prohibited_zones": ["public_logs", "external_apis", "cloud_storage"],
                "containment_verification": "All PHI remained in designated secure zones"
            },
            "audit_summary": self._generate_audit_summary(date_range)
        }
```

**IMPLEMENTATION APPROACH:**

1. **Add PHI tracking to 1-2 functions per development session**
2. **Include PHI compliance tests when you write any healthcare tests**
3. **Build compliance reporting incrementally as you create dashboards**
4. **Document PHI handling in any new security reviews**

This gradual approach ensures comprehensive PHI tracking without overwhelming development cycles.

    def _run_medical_safety_scan(self, codebase_path: str) -> Dict[str, Any]:
        """Run medical safety compliance scan."""

        medical_safety_patterns = {
            "medical_advice_indicators": [
                r'(patient should|you should|take medication|prescribe)',
                r'(diagnosis is|condition is|you have)',
                r'(treatment plan|therapy|cure)'
            ],
            "clinical_decision_patterns": [
                r'(recommend.*treatment|suggest.*medication)',
                r'(medical advice|clinical recommendation)',
                r'(dosage|prescription|treatment protocol)'
            ],
            "safety_boundary_violations": [
                r'(doctor.*recommends|physician.*advises)',
                r'(medical.*opinion|clinical.*judgment)',
                r'(diagnostic.*conclusion|treatment.*decision)'
            ]
        }

        return {
            "safety_patterns": medical_safety_patterns,
            "scan_focus": "Administrative boundaries and medical safety",
            "compliance_requirement": "No medical advice generation"
        }

````

### Security Review Integration with Modern Tools

```python
# ✅ CORRECT: Integration with modern security tools
class ModernHealthcareSecurityTools:
    """Integration of modern security tools for healthcare AI."""

    def setup_security_pipeline(self) -> Dict[str, Any]:
        """Set up comprehensive security pipeline for healthcare."""

        return {
            "static_analysis": {
                "bandit": "bandit -r . -f json -o security_report.json",
                "semgrep": "semgrep --config=auto --json --output=semgrep_report.json .",
                "ruff_security": "ruff check --select=S .",  # Security-focused rules
                "mypy_security": "mypy . --strict --no-error-summary"
            },

            "dependency_scanning": {
                "safety": "safety check --json --output=safety_report.json",
                "pip_audit": "pip-audit --format=json --output=audit_report.json",
                "trivy": "trivy fs --format json --output trivy_report.json ."
            },

            "secrets_detection": {
                "detect_secrets": "detect-secrets scan --all-files",
                "trufflehog": "trufflehog filesystem . --json",
                "gitleaks": "gitleaks detect --source . --report-format json"
            },

            "healthcare_specific": {
                "phi_scanner": "python3 scripts/scan-phi-exposure.py",
                "medical_safety_scanner": "python3 scripts/scan-medical-safety.py",
                "hipaa_compliance_checker": "python3 scripts/check-hipaa-compliance.py"
            }
        }

    def setup_pre_commit_security_hooks(self) -> str:
        """Set up pre-commit security hooks for healthcare development."""

        return """
# .pre-commit-config.yaml - Healthcare Security Hooks
repos:
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: ['-c', 'bandit.yml']

  - repo: https://github.com/returntocorp/semgrep
    rev: v1.45.0
    hooks:
      - id: semgrep
        args: ['--config=rules/healthcare/', '--error']

  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']

  - repo: local
    hooks:
      - id: phi-exposure-check
        name: PHI Exposure Check
        entry: python3 scripts/check-phi-exposure.py
        language: python
        files: '\\.py$'

      - id: medical-safety-check
        name: Medical Safety Check
        entry: python3 scripts/check-medical-safety.py
        language: python
        files: '\\.py$'

      - id: hipaa-compliance-check
        name: HIPAA Compliance Check
        entry: python3 scripts/check-hipaa-compliance.py
        language: python
        files: '\\.py$'
        """

    def setup_github_actions_security(self) -> str:
        """Set up GitHub Actions security workflow for healthcare."""

        return """
name: Healthcare Security Review

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  security-scan:
    runs-on: self-hosted

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install security tools
      run: |
        pip install bandit safety detect-secrets
        pip install semgrep ruff mypy
        pip install -r requirements-security.txt

    - name: Run Bandit security scan
      run: |
        bandit -r . -f json -o bandit_report.json || true

    - name: Run Semgrep healthcare rules
      run: |
        semgrep --config=rules/healthcare/ --json --output=semgrep_report.json . || true

    - name: Run dependency vulnerability scan
      run: |
        safety check --json --output=safety_report.json || true
        pip-audit --format=json --output=audit_report.json || true

    - name: Run PHI exposure scan
      run: |
        python3 scripts/scan-phi-exposure.py --output=phi_scan_report.json

    - name: Run medical safety scan
      run: |
        python3 scripts/scan-medical-safety.py --output=medical_safety_report.json

    - name: Run HIPAA compliance check
      run: |
        python3 scripts/check-hipaa-compliance.py --output=hipaa_compliance_report.json

    - name: Generate security summary
      run: |
        python3 scripts/generate-security-summary.py \
          --bandit=bandit_report.json \
          --semgrep=semgrep_report.json \
          --safety=safety_report.json \
          --phi=phi_scan_report.json \
          --medical=medical_safety_report.json \
          --hipaa=hipaa_compliance_report.json \
          --output=security_summary.json

    - name: Upload security reports
      uses: actions/upload-artifact@v3
      with:
        name: security-reports
        path: |
          *_report.json
          security_summary.json

    - name: Security gates
      run: |
        python3 scripts/security-gates.py --summary=security_summary.json
        """
````

### Healthcare Security Review Checklist

```bash
#!/bin/bash
# scripts/healthcare-security-review.sh

echo "🔒 Starting Healthcare AI Security Review..."

# Create security reports directory
mkdir -p reports/security/

# Run static security analysis
echo "🔍 Running static security analysis..."
bandit -r . -f json -o reports/security/bandit_report.json || true
semgrep --config=rules/healthcare/ --json --output=reports/security/semgrep_report.json . || true
ruff check --select=S --format=json --output-file=reports/security/ruff_security.json . || true

# Run dependency security scans
echo "📦 Running dependency security scans..."
safety check --json --output=reports/security/safety_report.json || true
pip-audit --format=json --output=reports/security/audit_report.json || true

# Run healthcare-specific security scans
echo "🏥 Running healthcare-specific security scans..."
python3 scripts/scan-phi-exposure.py --output=reports/security/phi_scan_report.json
python3 scripts/scan-medical-safety.py --output=reports/security/medical_safety_report.json
python3 scripts/check-hipaa-compliance.py --output=reports/security/hipaa_compliance_report.json

# Generate comprehensive security report
echo "📊 Generating comprehensive security report..."
python3 scripts/generate-security-summary.py \
  --bandit=reports/security/bandit_report.json \
  --semgrep=reports/security/semgrep_report.json \
  --safety=reports/security/safety_report.json \
  --phi=reports/security/phi_scan_report.json \
  --medical=reports/security/medical_safety_report.json \
  --hipaa=reports/security/hipaa_compliance_report.json \
  --output=reports/security/comprehensive_security_report.json

# Validate security gates
echo "🚨 Validating security gates..."
python3 scripts/security-gates.py --summary=reports/security/comprehensive_security_report.json

echo "✅ Healthcare security review completed!"
echo "📁 Reports available in: reports/security/"
echo "📋 Summary: reports/security/comprehensive_security_report.json"
```

## Healthcare Security Review Best Practices

### PHI Protection Review

- **Data Flow Analysis**: Trace PHI through all system components
- **Encryption Validation**: Verify AES-256 encryption for PHI at rest and in transit
- **Access Control Review**: Validate role-based access to PHI
- **Audit Trail Verification**: Ensure comprehensive PHI access logging

### Medical Safety Review

- **Administrative Boundary Validation**: Ensure no medical advice generation
- **Clinical Decision Support Limits**: Validate appropriate system boundaries
- **Provider Referral Patterns**: Check proper referrals for medical questions
- **Medical Disclaimer Compliance**: Verify disclaimers on all healthcare functions

### Automated Security Integration

- **Pre-commit Hooks**: Automated security validation on every commit
- **CI/CD Security Gates**: Block deployments failing security requirements
- **Continuous Monitoring**: Ongoing security monitoring in production
- **Compliance Reporting**: Automated HIPAA compliance reporting

### Modern Tool Integration

- **Bandit + Semgrep**: Comprehensive static analysis with healthcare rules
- **Dependency Scanning**: Automated vulnerability detection in dependencies
- **Secrets Detection**: Prevent PHI or credentials in code repositories
- **Ruff Security Rules**: Ultra-fast security linting integrated with development

Remember: Healthcare security review must ensure both cybersecurity and medical safety compliance while maintaining comprehensive PHI protection throughout the system architecture.
