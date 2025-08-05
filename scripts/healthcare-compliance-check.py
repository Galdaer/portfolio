#!/usr/bin/env python3
"""
Enhanced Healthcare Compliance Check
Comprehensive validation for HIPAA compliance, PHI protection, and medical data handling
across multiple languages and file types.

Integrates patterns from removed shell scripts for comprehensive compliance checking.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


class ComplianceIssue:
    """Represents a healthcare compliance issue"""

    def __init__(
        self,
        filename: str,
        line_number: int | None,
        issue_type: str,
        message: str,
        severity: str = "warning",
        compliance_requirement: str | None = None,
    ):
        self.filename = filename
        self.line_number = line_number
        self.issue_type = issue_type
        self.message = message
        self.severity = severity
        self.compliance_requirement = compliance_requirement

    def __str__(self) -> str:
        location = f"{self.filename}"
        if self.line_number:
            location += f":{self.line_number}"

        compliance_info = ""
        if self.compliance_requirement:
            compliance_info = f" [{self.compliance_requirement}]"

        return f"{location}: {self.severity.upper()}: {self.message}{compliance_info}"


class HealthcareComplianceChecker:
    """Enhanced healthcare compliance checker with multi-language support"""

    def __init__(self, config_file: str | None = None):
        self.config = self._load_config(config_file)
        self.synthetic_markers = self._get_synthetic_markers()
        self.phi_patterns = self._get_phi_patterns()
        self.medical_disclaimer_requirements = self._get_medical_disclaimer_requirements()
        self.skip_directories = self._get_skip_directories()
        self.issues: list[ComplianceIssue] = []

    def _load_config(self, config_file: str | None) -> dict[str, Any]:
        """Load compliance configuration"""
        default_config = {
            "strict_mode": False,
            "check_javascript": True,
            "check_typescript": True,
            "check_yaml": True,
            "check_json": True,
            "require_medical_disclaimers": True,
            "phi_detection_enabled": True,
            "audit_logging": True,
        }

        if config_file and os.path.exists(config_file):
            try:
                with open(config_file) as f:
                    if config_file.endswith(".yml") or config_file.endswith(".yaml"):
                        user_config = yaml.safe_load(f)
                    else:
                        user_config = json.load(f)
                default_config.update(user_config)
            except Exception as e:
                print(f"Warning: Could not load config file {config_file}: {e}")

        return default_config

    def _get_synthetic_markers(self) -> list[str]:
        """Get comprehensive synthetic data markers"""
        return [
            # Standard synthetic markers
            "synthetic",
            "_synthetic",
            "SYN-",
            "TEST-",
            "DEMO-",
            # Healthcare synthetic IDs
            "PAT001",
            "PAT002",
            "PAT003",
            "PAT999",
            "PROV001",
            "PROV002",
            "ENC001",
            # Fake contact information
            "000-000-0000",
            "555-0000",
            "XXX-XX-XXXX",
            "123-45-6789",
            "example.com",
            "test.com",
            "synthetic.test",
            "fake.email",
            # Test/demo names and organizations
            "John Doe",
            "Jane Smith",
            "Meghan Anderson",
            "Test Hospital",
            "UnitedHealth Test",
            "Demo Clinic",
            "Sample Healthcare",
            # Development markers
            "fake",
            "test",
            "demo",
            "mock",
            "stub",
            "placeholder",
            # Synthetic healthcare data indicators
            "generated_patient",
            "synthetic_encounter",
            "test_diagnosis",
        ]

    def _get_phi_patterns(self) -> dict[str, dict[str, Any]]:
        """Get comprehensive PHI detection patterns"""
        return {
            "ssn": {
                "pattern": r"\b\d{3}-\d{2}-\d{4}\b",
                "description": "Social Security Number",
                "severity": "error",
                "compliance": "HIPAA_164.514(b)(2)(i)",
            },
            "phone": {
                "pattern": r"\b\d{3}-\d{3}-\d{4}\b|\(\d{3}\)\s*\d{3}-\d{4}\b",
                "description": "Phone Number",
                "severity": "warning",
                "compliance": "HIPAA_164.514(b)(2)(i)",
            },
            "email": {
                "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                "description": "Email Address",
                "severity": "warning",
                "compliance": "HIPAA_164.514(b)(2)(i)",
            },
            "credit_card": {
                "pattern": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
                "description": "Credit Card Number",
                "severity": "error",
                "compliance": "PCI_DSS",
            },
            "medical_record_number": {
                "pattern": r"\bMRN\d{6,10}\b",
                "description": "Medical Record Number",
                "severity": "warning",
                "compliance": "HIPAA_164.514(b)(2)(i)",
            },
            "npi_number": {
                "pattern": r"\bNPI\d{10}\b|\b\d{10}\b(?=.*(?:provider|physician|doctor))",
                "description": "National Provider Identifier",
                "severity": "info",
                "compliance": "HIPAA_164.514(b)(2)(i)",
            },
        }

    def _get_medical_disclaimer_requirements(self) -> dict[str, list[str]]:
        """Get medical disclaimer requirements by file type"""
        return {
            "python": [
                r"medical.*disclaimer",
                r"not.*provide.*medical.*advice",
                r"consult.*healthcare.*professional",
                r"administrative.*support.*only",
            ],
            "javascript": [
                r"medical.*disclaimer",
                r"not.*provide.*medical.*advice",
                r"healthcare.*professional",
            ],
            "typescript": [
                r"medical.*disclaimer",
                r"not.*provide.*medical.*advice",
                r"healthcare.*professional",
            ],
        }

    def _get_skip_directories(self) -> set[str]:
        """Get directories to skip during compliance checking"""
        return {
            ".git",
            "node_modules",
            "__pycache__",
            ".pytest_cache",
            "data/synthetic",
            "test",
            "tests",
            "mock",
            "coverage",
            ".venv",
            "venv",
            "env",
            "reference/ai-patterns",
        }

    def is_synthetic_data(self, content: str, filename: str) -> bool:
        """Enhanced synthetic data detection"""
        # Check file path
        if any(
            skip_dir in filename
            for skip_dir in ["data/synthetic", "test", "mock", "_test", ".test."]
        ):
            return True

        # Check for synthetic markers in content
        content_lower = content.lower()
        for marker in self.synthetic_markers:
            if marker.lower() in content_lower:
                return True

        return False

    def check_phi_patterns(self, content: str, filename: str) -> list[ComplianceIssue]:
        """Check for PHI patterns in content"""
        issues: list[ComplianceIssue] = []

        if self.is_synthetic_data(content, filename):
            return issues  # Skip synthetic data files

        lines = content.split("\n")

        for _pattern_name, pattern_info in self.phi_patterns.items():
            pattern = pattern_info["pattern"]
            description = pattern_info["description"]
            severity = pattern_info["severity"]
            compliance = pattern_info["compliance"]

            for line_num, line in enumerate(lines, 1):
                matches = re.finditer(pattern, line)
                for match in matches:
                    if not self._is_pattern_in_synthetic_context(line, match.group()):
                        issues.append(
                            ComplianceIssue(
                                filename=filename,
                                line_number=line_num,
                                issue_type="phi_pattern",
                                message=f"Potential {description} detected: '{match.group()}'",
                                severity=severity,
                                compliance_requirement=compliance,
                            )
                        )

        return issues

    def check_medical_disclaimers(self, content: str, filename: str) -> list[ComplianceIssue]:
        """Check for required medical disclaimers"""
        issues: list[ComplianceIssue] = []

        if not self.config["require_medical_disclaimers"]:
            return issues

        # Determine file type
        file_ext = Path(filename).suffix.lower()
        file_type = None

        if file_ext in [".py"]:
            file_type = "python"
        elif file_ext in [".js"]:
            file_type = "javascript"
        elif file_ext in [".ts"]:
            file_type = "typescript"

        if not file_type:
            return issues

        # Check if file contains medical AI content
        medical_ai_patterns = [
            r"medical.*ai|ai.*medical",
            r"diagnosis|treatment|clinical",
            r"patient.*data|medical.*record",
            r"healthcare.*ai|medical.*assistant",
        ]

        has_medical_content = False
        for pattern in medical_ai_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                has_medical_content = True
                break

        if not has_medical_content:
            return issues

        # Check for required disclaimer patterns
        disclaimer_patterns = self.medical_disclaimer_requirements.get(file_type, [])
        missing_disclaimers = []

        for disclaimer_pattern in disclaimer_patterns:
            if not re.search(disclaimer_pattern, content, re.IGNORECASE):
                missing_disclaimers.append(disclaimer_pattern)

        if missing_disclaimers:
            issues.append(
                ComplianceIssue(
                    filename=filename,
                    line_number=None,
                    issue_type="missing_medical_disclaimer",
                    message=f"Medical AI code missing required disclaimers: {missing_disclaimers}",
                    severity="warning",
                    compliance_requirement="MEDICAL_DISCLAIMER_REQUIREMENT",
                )
            )

        return issues

    def check_security_measures(self, content: str, filename: str) -> list[ComplianceIssue]:
        """Check for proper security measures around medical data handling"""
        issues: list[ComplianceIssue] = []

        # Check for medical data handling patterns
        medical_data_patterns = [
            r"patient.*data|medical.*record|phi",
            r"healthcare.*database|medical.*database",
            r"clinical.*data|diagnosis.*data",
        ]

        has_medical_data = False
        for pattern in medical_data_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                has_medical_data = True
                break

        if not has_medical_data:
            return issues

        # Check for required security measures
        security_patterns = [
            r"encrypt|encryption",
            r"audit|logging|log",
            r"security|secure",
            r"authentication|authorization",
            r"hipaa|compliance",
        ]

        has_security_measures = False
        for pattern in security_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                has_security_measures = True
                break

        if not has_security_measures:
            issues.append(
                ComplianceIssue(
                    filename=filename,
                    line_number=None,
                    issue_type="missing_security_measures",
                    message="Medical data handling without apparent security measures",
                    severity="warning",
                    compliance_requirement="HIPAA_164.312",
                )
            )

        return issues

    def check_configuration_files(self, content: str, filename: str) -> list[ComplianceIssue]:
        """Check configuration files for compliance issues"""
        issues: list[ComplianceIssue] = []

        file_ext = Path(filename).suffix.lower()

        if file_ext in [".yml", ".yaml"]:
            try:
                config_data = yaml.safe_load(content)
                issues.extend(self._check_yaml_config(config_data, filename))
            except yaml.YAMLError:
                issues.append(
                    ComplianceIssue(
                        filename=filename,
                        line_number=None,
                        issue_type="invalid_yaml",
                        message="Invalid YAML configuration file",
                        severity="error",
                    )
                )

        elif file_ext == ".json":
            try:
                config_data = json.loads(content)
                issues.extend(self._check_json_config(config_data, filename))
            except json.JSONDecodeError:
                issues.append(
                    ComplianceIssue(
                        filename=filename,
                        line_number=None,
                        issue_type="invalid_json",
                        message="Invalid JSON configuration file",
                        severity="error",
                    )
                )

        return issues

    def check_file_compliance(self, filename: str) -> list[ComplianceIssue]:
        """Check single file for healthcare compliance"""
        issues: list[ComplianceIssue] = []

        # Skip certain directories
        if any(skip_dir in filename for skip_dir in self.skip_directories):
            return issues

        try:
            with open(filename, encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            issues.append(
                ComplianceIssue(
                    filename=filename,
                    line_number=None,
                    issue_type="file_read_error",
                    message=f"Error reading file: {str(e)}",
                    severity="error",
                )
            )
            return issues

        # PHI pattern checking
        if self.config["phi_detection_enabled"]:
            issues.extend(self.check_phi_patterns(content, filename))

        # Medical disclaimer checking
        issues.extend(self.check_medical_disclaimers(content, filename))

        # Security measures checking
        issues.extend(self.check_security_measures(content, filename))

        # Configuration file checking
        if Path(filename).suffix.lower() in [".yml", ".yaml", ".json"]:
            issues.extend(self.check_configuration_files(content, filename))

        return issues

    def run_compliance_check(self, target_paths: list[str] | None = None) -> tuple[int, int, int]:
        """Run comprehensive compliance check"""
        if not target_paths:
            target_paths = ["."]

        supported_extensions = {".py", ".js", ".ts", ".yml", ".yaml", ".json"}

        files_to_check = []
        for target_path in target_paths:
            if os.path.isfile(target_path):
                files_to_check.append(target_path)
            else:
                for root, dirs, files in os.walk(target_path):
                    # Skip certain directories
                    dirs[:] = [
                        d for d in dirs if not any(skip in d for skip in self.skip_directories)
                    ]

                    for file in files:
                        file_path = os.path.join(root, file)
                        if Path(file).suffix.lower() in supported_extensions:
                            files_to_check.append(file_path)

        # Check each file
        total_issues = 0
        errors = 0
        warnings = 0

        for filename in files_to_check:
            file_issues = self.check_file_compliance(filename)
            self.issues.extend(file_issues)

            for issue in file_issues:
                total_issues += 1
                if issue.severity == "error":
                    errors += 1
                elif issue.severity == "warning":
                    warnings += 1

        return total_issues, errors, warnings

    def generate_report(self, output_format: str = "text") -> str:
        """Generate compliance report"""
        if output_format == "json":
            return self._generate_json_report()
        elif output_format == "yaml":
            return self._generate_yaml_report()
        else:
            return self._generate_text_report()

    def _is_pattern_in_synthetic_context(self, line: str, pattern_match: str) -> bool:
        """Check if a pattern match is in synthetic context"""
        line_lower = line.lower()

        # Check for synthetic markers in the same line
        for marker in self.synthetic_markers:
            if marker.lower() in line_lower:
                return True

        # Check for test/mock contexts
        test_contexts = ["test", "mock", "example", "sample", "demo", "fake"]
        for context in test_contexts:
            if context in line_lower:
                return True

        return False

    def _check_yaml_config(self, config_data: Any, filename: str) -> list[ComplianceIssue]:
        """Check YAML configuration for healthcare compliance"""
        issues: list[ComplianceIssue] = []

        if not isinstance(config_data, dict):
            return issues

        # Check for healthcare-specific configuration requirements
        if "healthcare" in filename.lower() or "medical" in filename.lower():
            # Check for required healthcare sections
            required_sections = ["medical_compliance", "security", "audit_logging"]
            for section in required_sections:
                if not self._find_nested_key(config_data, section):
                    issues.append(
                        ComplianceIssue(
                            filename=filename,
                            line_number=None,
                            issue_type="missing_healthcare_config",
                            message=f"Missing required healthcare configuration section: {section}",
                            severity="warning",
                            compliance_requirement="HEALTHCARE_CONFIG_REQUIREMENT",
                        )
                    )

        return issues

    def _check_json_config(self, config_data: Any, filename: str) -> list[ComplianceIssue]:
        """Check JSON configuration for healthcare compliance"""
        issues: list[ComplianceIssue] = []

        if not isinstance(config_data, dict):
            return issues

        # Similar checks as YAML but for JSON
        if "healthcare" in filename.lower() or "medical" in filename.lower():
            required_sections = ["medical_compliance", "security", "audit_logging"]
            for section in required_sections:
                if not self._find_nested_key(config_data, section):
                    issues.append(
                        ComplianceIssue(
                            filename=filename,
                            line_number=None,
                            issue_type="missing_healthcare_config",
                            message=f"Missing required healthcare configuration section: {section}",
                            severity="warning",
                            compliance_requirement="HEALTHCARE_CONFIG_REQUIREMENT",
                        )
                    )

        return issues

    def _find_nested_key(self, data: dict, key: str) -> bool:
        """Find a key in nested dictionary structure"""
        if key in data:
            return True

        for value in data.values():
            if isinstance(value, dict):
                if self._find_nested_key(value, key):
                    return True

        return False

    def _generate_text_report(self) -> str:
        """Generate text format compliance report"""
        if not self.issues:
            return "✅ Healthcare compliance check passed - no issues found"

        report_lines = ["🏥 Healthcare Compliance Report", "=" * 40, ""]

        # Group issues by severity
        errors = [issue for issue in self.issues if issue.severity == "error"]
        warnings = [issue for issue in self.issues if issue.severity == "warning"]
        infos = [issue for issue in self.issues if issue.severity == "info"]

        if errors:
            report_lines.extend([f"❌ ERRORS ({len(errors)}):", ""])
            for issue in errors:
                report_lines.append(f"  {issue}")
            report_lines.append("")

        if warnings:
            report_lines.extend([f"⚠️  WARNINGS ({len(warnings)}):", ""])
            for issue in warnings:
                report_lines.append(f"  {issue}")
            report_lines.append("")

        if infos:
            report_lines.extend([f"ℹ️  INFO ({len(infos)}):", ""])
            for issue in infos:
                report_lines.append(f"  {issue}")
            report_lines.append("")

        report_lines.extend(
            [
                "Summary:",
                f"  Total Issues: {len(self.issues)}",
                f"  Errors: {len(errors)}",
                f"  Warnings: {len(warnings)}",
                f"  Info: {len(infos)}",
            ]
        )

        return "\n".join(report_lines)

    def _generate_json_report(self) -> str:
        """Generate JSON format compliance report"""
        report_data: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_issues": len(self.issues),
            "summary": {
                "errors": len([i for i in self.issues if i.severity == "error"]),
                "warnings": len([i for i in self.issues if i.severity == "warning"]),
                "info": len([i for i in self.issues if i.severity == "info"]),
            },
            "issues": [],
        }

        for issue in self.issues:
            report_data["issues"].append(
                {
                    "filename": issue.filename,
                    "line_number": issue.line_number,
                    "issue_type": issue.issue_type,
                    "message": issue.message,
                    "severity": issue.severity,
                    "compliance_requirement": issue.compliance_requirement,
                }
            )

        return json.dumps(report_data, indent=2)

    def _generate_yaml_report(self) -> str:
        """Generate YAML format compliance report"""
        report_data: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_issues": len(self.issues),
            "summary": {
                "errors": len([i for i in self.issues if i.severity == "error"]),
                "warnings": len([i for i in self.issues if i.severity == "warning"]),
                "info": len([i for i in self.issues if i.severity == "info"]),
            },
            "issues": [],
        }

        for issue in self.issues:
            report_data["issues"].append(
                {
                    "filename": issue.filename,
                    "line_number": issue.line_number,
                    "issue_type": issue.issue_type,
                    "message": issue.message,
                    "severity": issue.severity,
                    "compliance_requirement": issue.compliance_requirement,
                }
            )

        return yaml.dump(report_data, default_flow_style=False)


def check_healthcare_compliance(filename: str) -> list[str]:
    """Legacy function for backward compatibility"""
    checker = HealthcareComplianceChecker()
    issues = checker.check_file_compliance(filename)
    return [str(issue) for issue in issues]


def main() -> None:
    """Main compliance check function"""
    parser = argparse.ArgumentParser(
        description="Enhanced Healthcare Compliance Check",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Check current directory
  %(prog)s --strict                 # Strict mode (errors fail)
  %(prog)s --format json            # JSON output
  %(prog)s --config compliance.yml  # Use custom config
  %(prog)s src/ agents/             # Check specific directories
        """,
    )

    parser.add_argument(
        "paths", nargs="*", default=["."], help="Paths to check (default: current directory)"
    )

    parser.add_argument("--config", help="Configuration file path")

    parser.add_argument(
        "--format",
        choices=["text", "json", "yaml"],
        default="text",
        help="Output format (default: text)",
    )

    parser.add_argument(
        "--strict", action="store_true", help="Strict mode: warnings are treated as errors"
    )

    parser.add_argument("--no-phi-check", action="store_true", help="Disable PHI pattern checking")

    parser.add_argument(
        "--no-disclaimer-check", action="store_true", help="Disable medical disclaimer checking"
    )

    args = parser.parse_args()

    # Create compliance checker
    checker = HealthcareComplianceChecker(config_file=args.config)

    # Override config with command line arguments
    if args.no_phi_check:
        checker.config["phi_detection_enabled"] = False
    if args.no_disclaimer_check:
        checker.config["require_medical_disclaimers"] = False
    if args.strict:
        checker.config["strict_mode"] = True

    # Run compliance check
    total_issues, errors, warnings = checker.run_compliance_check(args.paths)

    # Generate and print report
    report = checker.generate_report(args.format)
    print(report)

    # Determine exit code
    if errors > 0:
        sys.exit(1)
    elif warnings > 0 and args.strict:
        sys.exit(1)
    elif total_issues > 0:
        sys.exit(0)  # Issues found but not failing
    else:
        sys.exit(0)  # No issues found


if __name__ == "__main__":
    main()
