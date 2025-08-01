# Healthcare AI Security Review Instructions

## Purpose

Comprehensive security review guidance for healthcare AI systems emphasizing PHI protection, medical safety validation, and healthcare-specific security frameworks with HIPAA compliance.

## Healthcare Security Review Framework

### PHI Protection Security Review

```python
# ✅ CORRECT: Healthcare security review patterns
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
import re
import logging
from enum import Enum

class SecurityRiskLevel(Enum):
    """Healthcare security risk classification."""
    CRITICAL = "CRITICAL"  # PHI exposure, medical safety violation
    HIGH = "HIGH"  # Security vulnerability affecting patient data
    MEDIUM = "MEDIUM"  # General security improvement needed
    LOW = "LOW"  # Best practice recommendation
    INFORMATIONAL = "INFORMATIONAL"  # Security awareness item

@dataclass
class HealthcareSecurityFinding:
    """Structured healthcare security finding with compliance context."""

    finding_id: str
    title: str
    description: str
    risk_level: SecurityRiskLevel
    affected_component: str
    phi_impact: bool
    medical_safety_impact: bool
    compliance_frameworks: List[str]
    remediation_steps: List[str]
    validation_criteria: List[str]

    def generate_remediation_priority(self) -> int:
        """Generate remediation priority based on healthcare impact."""

        priority_score = 0

        # PHI impact gets highest priority
        if self.phi_impact:
            priority_score += 100

        # Medical safety impact gets second highest
        if self.medical_safety_impact:
            priority_score += 50

        # Risk level scoring
        risk_scores = {
            SecurityRiskLevel.CRITICAL: 25,
            SecurityRiskLevel.HIGH: 20,
            SecurityRiskLevel.MEDIUM: 15,
            SecurityRiskLevel.LOW: 10,
            SecurityRiskLevel.INFORMATIONAL: 5
        }

        priority_score += risk_scores.get(self.risk_level, 0)

        # Compliance framework impact
        if "HIPAA" in self.compliance_frameworks:
            priority_score += 15
        if "HITECH" in self.compliance_frameworks:
            priority_score += 10

        return priority_score

class HealthcareSecurityReviewer:
    """Comprehensive security reviewer for healthcare AI systems."""

    def __init__(self) -> None:
        self.phi_patterns = self._load_phi_detection_patterns()
        self.medical_safety_patterns = self._load_medical_safety_patterns()
        self.compliance_requirements = self._load_compliance_requirements()
        self.security_findings: List[HealthcareSecurityFinding] = []

    def conduct_comprehensive_security_review(
        self,
        codebase_path: str,
        review_scope: List[str] = None
    ) -> Dict[str, Any]:
        """Conduct comprehensive security review for healthcare AI system."""

        review_scope = review_scope or [
            "phi_protection",
            "medical_safety",
            "authentication_authorization",
            "data_encryption",
            "audit_logging",
            "input_validation",
            "error_handling",
            "dependency_security"
        ]

        review_results = {}

        for scope_area in review_scope:
            review_method = getattr(self, f"_review_{scope_area}", None)
            if review_method:
                review_results[scope_area] = review_method(codebase_path)

        # Generate overall security assessment
        overall_assessment = self._generate_overall_assessment(review_results)

        return {
            "review_timestamp": datetime.now().isoformat(),
            "scope_areas": review_scope,
            "detailed_findings": review_results,
            "overall_assessment": overall_assessment,
            "prioritized_findings": self._prioritize_findings(),
            "compliance_status": self._assess_compliance_status(),
            "remediation_roadmap": self._generate_remediation_roadmap()
        }

    def _review_phi_protection(self, codebase_path: str) -> Dict[str, Any]:
        """Review PHI protection implementation and identify vulnerabilities."""

        phi_findings = []

        # Scan for potential PHI exposure in code
        phi_exposure_findings = self._scan_phi_exposure_patterns(codebase_path)
        phi_findings.extend(phi_exposure_findings)

        # Review encryption implementation
        encryption_findings = self._review_phi_encryption(codebase_path)
        phi_findings.extend(encryption_findings)

        # Review data storage patterns
        storage_findings = self._review_phi_storage_patterns(codebase_path)
        phi_findings.extend(storage_findings)

        # Review data transmission security
        transmission_findings = self._review_phi_transmission(codebase_path)
        phi_findings.extend(transmission_findings)

        return {
            "phi_protection_status": self._assess_phi_protection_status(phi_findings),
            "findings": phi_findings,
            "encryption_compliance": self._assess_encryption_compliance(codebase_path),
            "data_minimization_compliance": self._assess_data_minimization(codebase_path),
            "access_control_assessment": self._assess_phi_access_controls(codebase_path)
        }

    def _scan_phi_exposure_patterns(self, codebase_path: str) -> List[HealthcareSecurityFinding]:
        """Scan codebase for potential PHI exposure patterns."""

        findings = []

        # Define PHI exposure patterns
        phi_exposure_patterns = {
            "hardcoded_ssn": {
                "pattern": r'\b\d{3}-\d{2}-\d{4}\b',
                "description": "Potential hardcoded SSN detected",
                "risk_level": SecurityRiskLevel.CRITICAL
            },
            "hardcoded_phone": {
                "pattern": r'\(\d{3}\)\s*\d{3}-\d{4}',
                "description": "Potential hardcoded phone number detected",
                "risk_level": SecurityRiskLevel.HIGH
            },
            "hardcoded_email": {
                "pattern": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                "description": "Potential hardcoded email address detected",
                "risk_level": SecurityRiskLevel.MEDIUM
            },
            "patient_data_logging": {
                "pattern": r'log.*patient.*data|print.*patient.*info',
                "description": "Potential patient data in logging statements",
                "risk_level": SecurityRiskLevel.HIGH
            }
        }

        # Scan files for PHI exposure patterns
        for root, dirs, files in os.walk(codebase_path):
            for file in files:
                if file.endswith(('.py', '.js', '.ts', '.sql')):
                    file_path = os.path.join(root, file)
                    findings.extend(self._scan_file_for_phi_patterns(file_path, phi_exposure_patterns))

        return findings

    def _review_medical_safety(self, codebase_path: str) -> Dict[str, Any]:
        """Review medical safety implementation and identify risks."""

        medical_safety_findings = []

        # Scan for medical advice generation patterns
        medical_advice_findings = self._scan_medical_advice_patterns(codebase_path)
        medical_safety_findings.extend(medical_advice_findings)

        # Review diagnosis/treatment patterns
        diagnosis_findings = self._scan_diagnosis_patterns(codebase_path)
        medical_safety_findings.extend(diagnosis_findings)

        # Review medication recommendation patterns
        medication_findings = self._scan_medication_patterns(codebase_path)
        medical_safety_findings.extend(medication_findings)

        # Review clinical decision support boundaries
        decision_support_findings = self._review_clinical_boundaries(codebase_path)
        medical_safety_findings.extend(decision_support_findings)

        return {
            "medical_safety_status": self._assess_medical_safety_status(medical_safety_findings),
            "findings": medical_safety_findings,
            "administrative_boundaries": self._assess_administrative_boundaries(codebase_path),
            "provider_referral_patterns": self._assess_provider_referrals(codebase_path),
            "medical_disclaimer_compliance": self._assess_medical_disclaimers(codebase_path)
        }

    def _scan_medical_advice_patterns(self, codebase_path: str) -> List[HealthcareSecurityFinding]:
        """Scan for potential medical advice generation patterns."""

        findings = []

        medical_advice_patterns = {
            "diagnosis_language": {
                "pattern": r'(patient has|diagnosis is|condition is|you have)',
                "description": "Potential diagnosis language detected",
                "risk_level": SecurityRiskLevel.CRITICAL
            },
            "treatment_recommendations": {
                "pattern": r'(should take|recommend.*medication|prescribe|dosage)',
                "description": "Potential treatment recommendation detected",
                "risk_level": SecurityRiskLevel.CRITICAL
            },
            "medical_advice_verbs": {
                "pattern": r'(treat with|cure|heal|therapy for)',
                "description": "Potential medical advice language detected",
                "risk_level": SecurityRiskLevel.HIGH
            },
            "symptom_interpretation": {
                "pattern": r'(symptoms indicate|likely cause|probable diagnosis)',
                "description": "Potential symptom interpretation detected",
                "risk_level": SecurityRiskLevel.HIGH
            }
        }

        # Scan for medical advice patterns
        for root, dirs, files in os.walk(codebase_path):
            for file in files:
                if file.endswith(('.py', '.js', '.ts')):
                    file_path = os.path.join(root, file)
                    file_findings = self._scan_file_for_medical_patterns(file_path, medical_advice_patterns)
                    findings.extend(file_findings)

        return findings

    def _review_authentication_authorization(self, codebase_path: str) -> Dict[str, Any]:
        """Review authentication and authorization security."""

        auth_findings = []

        # Review authentication mechanisms
        auth_mechanism_findings = self._review_auth_mechanisms(codebase_path)
        auth_findings.extend(auth_mechanism_findings)

        # Review session management
        session_findings = self._review_session_management(codebase_path)
        auth_findings.extend(session_findings)

        # Review role-based access control
        rbac_findings = self._review_rbac_implementation(codebase_path)
        auth_findings.extend(rbac_findings)

        # Review healthcare-specific access controls
        healthcare_access_findings = self._review_healthcare_access_controls(codebase_path)
        auth_findings.extend(healthcare_access_findings)

        return {
            "authentication_status": self._assess_authentication_status(auth_findings),
            "findings": auth_findings,
            "session_security": self._assess_session_security(codebase_path),
            "access_control_matrix": self._generate_access_control_matrix(codebase_path),
            "healthcare_rbac_compliance": self._assess_healthcare_rbac(codebase_path)
        }

    def _review_data_encryption(self, codebase_path: str) -> Dict[str, Any]:
        """Review data encryption implementation for healthcare compliance."""

        encryption_findings = []

        # Review encryption at rest
        encryption_at_rest_findings = self._review_encryption_at_rest(codebase_path)
        encryption_findings.extend(encryption_at_rest_findings)

        # Review encryption in transit
        encryption_in_transit_findings = self._review_encryption_in_transit(codebase_path)
        encryption_findings.extend(encryption_in_transit_findings)

        # Review key management
        key_management_findings = self._review_key_management(codebase_path)
        encryption_findings.extend(key_management_findings)

        # Review PHI-specific encryption
        phi_encryption_findings = self._review_phi_encryption_specific(codebase_path)
        encryption_findings.extend(phi_encryption_findings)

        return {
            "encryption_status": self._assess_encryption_status(encryption_findings),
            "findings": encryption_findings,
            "encryption_algorithms": self._assess_encryption_algorithms(codebase_path),
            "key_management_assessment": self._assess_key_management(codebase_path),
            "hipaa_encryption_compliance": self._assess_hipaa_encryption(codebase_path)
        }

    def _review_audit_logging(self, codebase_path: str) -> Dict[str, Any]:
        """Review audit logging implementation for healthcare compliance."""

        audit_findings = []

        # Review audit log completeness
        audit_completeness_findings = self._review_audit_completeness(codebase_path)
        audit_findings.extend(audit_completeness_findings)

        # Review audit log security
        audit_security_findings = self._review_audit_security(codebase_path)
        audit_findings.extend(audit_security_findings)

        # Review PHI access logging
        phi_access_findings = self._review_phi_access_logging(codebase_path)
        audit_findings.extend(phi_access_findings)

        # Review audit log retention
        retention_findings = self._review_audit_retention(codebase_path)
        audit_findings.extend(retention_findings)

        return {
            "audit_logging_status": self._assess_audit_logging_status(audit_findings),
            "findings": audit_findings,
            "audit_coverage": self._assess_audit_coverage(codebase_path),
            "log_integrity": self._assess_log_integrity(codebase_path),
            "hipaa_audit_compliance": self._assess_hipaa_audit_compliance(codebase_path)
        }
```

### Security Review Automation

```python
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
        """Run specialized PHI exposure detection scan."""

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
```

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
```

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
