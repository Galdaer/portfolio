#!/usr/bin/env python3
"""
Enhanced HIPAA Configuration Validation
Comprehensive validation for HIPAA compliance configuration files across multiple formats.

Integrates patterns from removed shell scripts and provides detailed compliance reporting.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, cast

import yaml


class HIPAAValidationIssue:
    """Represents a HIPAA configuration validation issue"""

    def __init__(
        self,
        config_file: str,
        section: str | None,
        issue_type: str,
        message: str,
        severity: str = "warning",
        hipaa_requirement: str | None = None,
        remediation: str | None = None,
    ):
        self.config_file = config_file
        self.section = section
        self.issue_type = issue_type
        self.message = message
        self.severity = severity
        self.hipaa_requirement = hipaa_requirement
        self.remediation = remediation

    def __str__(self) -> str:
        location = self.config_file
        if self.section:
            location += f":{self.section}"

        hipaa_info = ""
        if self.hipaa_requirement:
            hipaa_info = f" [{self.hipaa_requirement}]"

        return f"{location}: {self.severity.upper()}: {self.message}{hipaa_info}"


class HIPAAConfigValidator:
    """Enhanced HIPAA configuration validator"""

    def __init__(self) -> None:
        self.issues: list[HIPAAValidationIssue] = []
        self.validation_rules = self._get_validation_rules()
        self.config_files_found: dict[str, bool] = {}

    def _get_validation_rules(self) -> dict[str, dict[str, Any]]:
        """Get comprehensive HIPAA validation rules"""
        return {
            "administrative_safeguards": {
                "required": True,
                "hipaa_ref": "HIPAA_164.308",
                "required_fields": [
                    "security_officer_assigned",
                    "workforce_training_program",
                    "information_access_management",
                    "security_awareness_training",
                    "contingency_plan",
                ],
                "validation_checks": {
                    "security_officer_assigned": lambda x: x is True,
                    "workforce_training_program": lambda x: isinstance(x, dict)
                    and "frequency_months" in x,
                    "contingency_plan": lambda x: isinstance(x, dict) and "backup_procedures" in x,
                },
            },
            "physical_safeguards": {
                "required": True,
                "hipaa_ref": "HIPAA_164.310",
                "required_fields": [
                    "facility_access_controls",
                    "workstation_use_restrictions",
                    "device_media_controls",
                ],
                "validation_checks": {
                    "facility_access_controls": lambda x: isinstance(x, dict)
                    and "access_logging" in x,
                    "workstation_use_restrictions": lambda x: isinstance(x, dict)
                    and "automatic_logoff" in x,
                },
            },
            "technical_safeguards": {
                "required": True,
                "hipaa_ref": "HIPAA_164.312",
                "required_fields": [
                    "access_control",
                    "audit_controls",
                    "integrity",
                    "person_authentication",
                    "transmission_security",
                ],
                "validation_checks": {
                    "access_control": lambda x: isinstance(x, dict)
                    and "unique_user_identification" in x,
                    "audit_controls": lambda x: isinstance(x, dict)
                    and "log_retention_days" in x
                    and x["log_retention_days"] >= 2555,
                    "transmission_security": lambda x: isinstance(x, dict)
                    and x.get("tls_version") == "1.3",
                },
            },
            "encryption": {
                "required": True,
                "hipaa_ref": "HIPAA_164.312(a)(2)(iv)",
                "required_fields": ["data_at_rest", "data_in_transit", "key_management"],
                "validation_checks": {
                    "data_at_rest": lambda x: isinstance(x, dict)
                    and x.get("algorithm") == "AES-256-GCM",
                    "data_in_transit": lambda x: isinstance(x, dict)
                    and x.get("tls_version") == "1.3",
                    "key_management": lambda x: isinstance(x, dict)
                    and "rotation_days" in x
                    and x["rotation_days"] <= 365,
                },
            },
            "audit_monitoring": {
                "required": True,
                "hipaa_ref": "HIPAA_164.312(b)",
                "required_fields": [
                    "audit_logging_enabled",
                    "log_retention_policy",
                    "real_time_monitoring",
                    "breach_detection",
                ],
                "validation_checks": {
                    "audit_logging_enabled": lambda x: x is True,
                    "log_retention_policy": lambda x: isinstance(x, dict)
                    and x.get("retention_days", 0) >= 2555,
                    "real_time_monitoring": lambda x: isinstance(x, dict)
                    and x.get("enabled") is True,
                    "breach_detection": lambda x: isinstance(x, dict) and "automated_alerts" in x,
                },
            },
            "breach_notification": {
                "required": True,
                "hipaa_ref": "HIPAA_164.400",
                "required_fields": [
                    "notification_procedures",
                    "risk_assessment_process",
                    "documentation_requirements",
                ],
                "validation_checks": {
                    "notification_procedures": lambda x: isinstance(x, dict)
                    and "timeline_hours" in x
                    and x["timeline_hours"] <= 72,
                    "risk_assessment_process": lambda x: isinstance(x, dict)
                    and "automated_assessment" in x,
                },
            },
            "business_associate_agreements": {
                "required": True,
                "hipaa_ref": "HIPAA_164.502(e)",
                "required_fields": [
                    "baa_management",
                    "subcontractor_oversight",
                    "termination_procedures",
                ],
                "validation_checks": {
                    "baa_management": lambda x: isinstance(x, dict) and "tracking_enabled" in x
                },
            },
        }

    def find_hipaa_config_files(self, search_paths: list[str]) -> list[str]:
        """Find HIPAA configuration files"""
        config_files = []

        for search_path in search_paths:
            if os.path.isfile(search_path):
                config_files.append(search_path)
            else:
                for root, dirs, files in os.walk(search_path):
                    # Skip certain directories
                    dirs[:] = [d for d in dirs if d not in [".git", "node_modules", "__pycache__"]]

                    for file in files:
                        file_path = os.path.join(root, file)

                        # Check for HIPAA-related configuration files
                        if any(
                            keyword in file.lower()
                            for keyword in [
                                "hipaa",
                                "compliance",
                                "security",
                                "healthcare_settings",
                            ]
                        ):
                            if file.endswith((".yml", ".yaml", ".json")):
                                config_files.append(file_path)

        return config_files

    def validate_config_file(self, config_file: str) -> list[HIPAAValidationIssue]:
        """Validate a single configuration file"""
        issues = []

        try:
            with open(config_file) as f:
                if config_file.endswith((".yml", ".yaml")):
                    config_data = yaml.safe_load(f)
                elif config_file.endswith(".json"):
                    config_data = json.load(f)
                else:
                    issues.append(
                        HIPAAValidationIssue(
                            config_file=config_file,
                            section=None,
                            issue_type="unsupported_format",
                            message="Unsupported configuration file format",
                            severity="error",
                        )
                    )
                    return issues

            if not isinstance(config_data, dict):
                issues.append(
                    HIPAAValidationIssue(
                        config_file=config_file,
                        section=None,
                        issue_type="invalid_structure",
                        message="Configuration file must contain a dictionary",
                        severity="error",
                    )
                )
                return issues

            # Validate HIPAA sections
            issues.extend(self._validate_hipaa_sections(config_data, config_file))

            # Validate healthcare system configuration
            issues.extend(self._validate_healthcare_system_config(config_data, config_file))

            # Validate environment-specific requirements
            issues.extend(self._validate_environment_requirements(config_data, config_file))

        except Exception as e:
            issues.append(
                HIPAAValidationIssue(
                    config_file=config_file,
                    section=None,
                    issue_type="file_error",
                    message=f"Error reading configuration file: {str(e)}",
                    severity="error",
                )
            )

        return issues

    def _validate_hipaa_sections(
        self, config_data: dict[str, Any], config_file: str
    ) -> list[HIPAAValidationIssue]:
        """Validate HIPAA-specific configuration sections"""
        issues = []

        for section_name, section_rules in self.validation_rules.items():
            if section_rules["required"]:
                section_data = self._find_nested_section(config_data, section_name)

                if not section_data:
                    issues.append(
                        HIPAAValidationIssue(
                            config_file=config_file,
                            section=section_name,
                            issue_type="missing_required_section",
                            message=f"Missing required HIPAA section: {section_name}",
                            severity="error",
                            hipaa_requirement=section_rules["hipaa_ref"],
                            remediation=f"Add {section_name} section with required fields: {section_rules['required_fields']}",
                        )
                    )
                    continue

                # Validate required fields
                for required_field in section_rules["required_fields"]:
                    if required_field not in section_data:
                        issues.append(
                            HIPAAValidationIssue(
                                config_file=config_file,
                                section=f"{section_name}.{required_field}",
                                issue_type="missing_required_field",
                                message=f"Missing required field: {required_field}",
                                severity="error",
                                hipaa_requirement=section_rules["hipaa_ref"],
                                remediation=f"Add {required_field} field to {section_name} section",
                            )
                        )

                # Validate field values
                validation_checks = section_rules.get("validation_checks", {})
                for field_name, validation_func in validation_checks.items():
                    if field_name in section_data:
                        try:
                            if not validation_func(section_data[field_name]):
                                issues.append(
                                    HIPAAValidationIssue(
                                        config_file=config_file,
                                        section=f"{section_name}.{field_name}",
                                        issue_type="invalid_field_value",
                                        message=f"Invalid value for {field_name}",
                                        severity="warning",
                                        hipaa_requirement=section_rules["hipaa_ref"],
                                    )
                                )
                        except Exception as e:
                            issues.append(
                                HIPAAValidationIssue(
                                    config_file=config_file,
                                    section=f"{section_name}.{field_name}",
                                    issue_type="validation_error",
                                    message=f"Error validating {field_name}: {str(e)}",
                                    severity="warning",
                                )
                            )

        return issues

    def _validate_healthcare_system_config(
        self, config_data: dict[str, Any], config_file: str
    ) -> list[HIPAAValidationIssue]:
        """Validate healthcare system specific configuration"""
        issues: list[HIPAAValidationIssue] = []

        # Check for healthcare_system section
        healthcare_config = config_data.get("healthcare_system")
        if not healthcare_config:
            return issues  # Not a healthcare system configuration file

        # Validate medical compliance section
        medical_compliance = healthcare_config.get("medical_compliance", {})

        if not medical_compliance.get("medical_disclaimer"):
            issues.append(
                HIPAAValidationIssue(
                    config_file=config_file,
                    section="healthcare_system.medical_compliance.medical_disclaimer",
                    issue_type="missing_medical_disclaimer",
                    message="Medical disclaimer is required for healthcare systems",
                    severity="error",
                    remediation="Add medical_disclaimer field with appropriate medical disclaimer text",
                )
            )

        hipaa_compliance = medical_compliance.get("hipaa_compliance", {})
        if not hipaa_compliance.get("enabled"):
            issues.append(
                HIPAAValidationIssue(
                    config_file=config_file,
                    section="healthcare_system.medical_compliance.hipaa_compliance.enabled",
                    issue_type="hipaa_disabled",
                    message="HIPAA compliance is disabled",
                    severity="error",
                    hipaa_requirement="HIPAA_164.530",
                    remediation="Enable HIPAA compliance by setting enabled: true",
                )
            )

        # Validate audit retention
        audit_retention = hipaa_compliance.get("audit_retention_days", 0)
        if audit_retention < 2555:  # 7 years
            issues.append(
                HIPAAValidationIssue(
                    config_file=config_file,
                    section="healthcare_system.medical_compliance.hipaa_compliance.audit_retention_days",
                    issue_type="insufficient_audit_retention",
                    message=f"Audit retention period ({audit_retention} days) is less than required 7 years (2555 days)",
                    severity="error",
                    hipaa_requirement="HIPAA_164.312(b)",
                    remediation="Set audit_retention_days to at least 2555 (7 years)",
                )
            )

        # Validate security configuration
        security_config = healthcare_config.get("security", {})

        # Check JWT expiration
        jwt_expiration = security_config.get("authentication", {}).get("jwt_expiration_minutes", 60)
        if jwt_expiration > 30:
            issues.append(
                HIPAAValidationIssue(
                    config_file=config_file,
                    section="healthcare_system.security.authentication.jwt_expiration_minutes",
                    issue_type="excessive_jwt_expiration",
                    message=f"JWT expiration ({jwt_expiration} minutes) exceeds recommended maximum for healthcare (30 minutes)",
                    severity="warning",
                    hipaa_requirement="HIPAA_164.312(a)(2)(iii)",
                    remediation="Set jwt_expiration_minutes to 30 or less for healthcare environments",
                )
            )

        # Check encryption algorithm
        encryption_algorithm = security_config.get("encryption", {}).get("phi_encryption_algorithm")
        if encryption_algorithm != "AES-256-GCM":
            issues.append(
                HIPAAValidationIssue(
                    config_file=config_file,
                    section="healthcare_system.security.encryption.phi_encryption_algorithm",
                    issue_type="weak_encryption",
                    message=f"PHI encryption algorithm ({encryption_algorithm}) is not AES-256-GCM",
                    severity="error",
                    hipaa_requirement="HIPAA_164.312(a)(2)(iv)",
                    remediation="Set phi_encryption_algorithm to AES-256-GCM",
                )
            )

        return issues

    def _validate_environment_requirements(
        self, config_data: dict[str, Any], config_file: str
    ) -> list[HIPAAValidationIssue]:
        """Validate environment-specific requirements"""
        issues = []

        # Check for environment detection
        environment = None
        if "healthcare_system" in config_data:
            environment = (
                config_data["healthcare_system"].get("metadata", {}).get("deployment_environment")
            )

        if not environment:
            # Try to detect from filename
            if "production" in config_file:
                environment = "production"
            elif "staging" in config_file:
                environment = "staging"
            elif "development" in config_file:
                environment = "development"

        # Production-specific validations
        if environment == "production":
            issues.extend(self._validate_production_requirements(config_data, config_file))

        return issues

    def _validate_production_requirements(
        self, config_data: dict[str, Any], config_file: str
    ) -> list[HIPAAValidationIssue]:
        """Validate production environment requirements"""
        issues = []

        healthcare_config = config_data.get("healthcare_system", {})

        # Check MFA requirements
        security_config = healthcare_config.get("security", {})
        mfa_required_roles = security_config.get("authentication", {}).get("mfa_required_roles", [])

        required_mfa_roles = ["healthcare_provider", "nurse", "security_officer", "privacy_officer"]
        missing_mfa_roles = [role for role in required_mfa_roles if role not in mfa_required_roles]

        if missing_mfa_roles:
            issues.append(
                HIPAAValidationIssue(
                    config_file=config_file,
                    section="healthcare_system.security.authentication.mfa_required_roles",
                    issue_type="insufficient_mfa_coverage",
                    message=f"MFA not required for critical roles in production: {missing_mfa_roles}",
                    severity="error",
                    hipaa_requirement="HIPAA_164.312(a)(2)(i)",
                    remediation=f"Add {missing_mfa_roles} to mfa_required_roles for production environment",
                )
            )

        # Check rate limiting
        rate_limiting = healthcare_config.get("performance", {}).get("rate_limiting", {})
        emergency_bypass = rate_limiting.get("emergency_bypass_enabled", True)

        if emergency_bypass:
            issues.append(
                HIPAAValidationIssue(
                    config_file=config_file,
                    section="healthcare_system.performance.rate_limiting.emergency_bypass_enabled",
                    issue_type="production_security_bypass",
                    message="Emergency bypass is enabled in production environment",
                    severity="warning",
                    remediation="Consider disabling emergency_bypass_enabled in production for enhanced security",
                )
            )

        return issues

    def _find_nested_section(
        self, config_data: dict[str, Any], section_name: str
    ) -> dict[str, Any] | None:
        """Find nested configuration section"""
        # Direct lookup
        if section_name in config_data:
            return cast(dict[str, Any], config_data[section_name])

        # Look in healthcare_system section
        healthcare_system = config_data.get("healthcare_system", {})
        if section_name in healthcare_system:
            return cast(dict[str, Any], healthcare_system[section_name])

        # Look in medical_compliance section
        medical_compliance = healthcare_system.get("medical_compliance", {})
        if section_name in medical_compliance:
            return cast(dict[str, Any], medical_compliance[section_name])

        # Look in security section
        security = healthcare_system.get("security", {})
        if section_name in security:
            return cast(dict[str, Any], security[section_name])

        return None

    def run_validation(self, search_paths: list[str] | None = None) -> tuple[int, int, int]:
        """Run comprehensive HIPAA configuration validation"""
        if not search_paths:
            search_paths = ["."]

        # Find configuration files
        config_files = self.find_hipaa_config_files(search_paths)

        if not config_files:
            self.issues.append(
                HIPAAValidationIssue(
                    config_file="<search_paths>",
                    section=None,
                    issue_type="no_config_files",
                    message="No HIPAA configuration files found",
                    severity="warning",
                    remediation="Create HIPAA compliance configuration files",
                )
            )

        total_issues = 0
        errors = 0
        warnings = 0

        # Validate each configuration file
        for config_file in config_files:
            file_issues = self.validate_config_file(config_file)
            self.issues.extend(file_issues)

            for issue in file_issues:
                total_issues += 1
                if issue.severity == "error":
                    errors += 1
                elif issue.severity == "warning":
                    warnings += 1

        return total_issues, errors, warnings

    def generate_report(self, output_format: str = "text") -> str:
        """Generate HIPAA validation report"""
        if output_format == "json":
            return self._generate_json_report()
        elif output_format == "yaml":
            return self._generate_yaml_report()
        else:
            return self._generate_text_report()

    def _generate_text_report(self) -> str:
        """Generate text format validation report"""
        if not self.issues:
            return "✅ HIPAA configuration validation passed - no issues found"

        report_lines = ["🏥 HIPAA Configuration Validation Report", "=" * 45, ""]

        # Group issues by severity
        errors = [issue for issue in self.issues if issue.severity == "error"]
        warnings = [issue for issue in self.issues if issue.severity == "warning"]
        infos = [issue for issue in self.issues if issue.severity == "info"]

        if errors:
            report_lines.extend([f"❌ ERRORS ({len(errors)}):", ""])
            for issue in errors:
                report_lines.append(f"  {issue}")
                if issue.remediation:
                    report_lines.append(f"     💡 Remediation: {issue.remediation}")
            report_lines.append("")

        if warnings:
            report_lines.extend([f"⚠️  WARNINGS ({len(warnings)}):", ""])
            for issue in warnings:
                report_lines.append(f"  {issue}")
                if issue.remediation:
                    report_lines.append(f"     💡 Remediation: {issue.remediation}")
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
        """Generate JSON format validation report"""
        report_data: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "validation_type": "HIPAA_Configuration",
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
                    "config_file": issue.config_file,
                    "section": issue.section,
                    "issue_type": issue.issue_type,
                    "message": issue.message,
                    "severity": issue.severity,
                    "hipaa_requirement": issue.hipaa_requirement,
                    "remediation": issue.remediation,
                }
            )

        return json.dumps(report_data, indent=2)

    def _generate_yaml_report(self) -> str:
        """Generate YAML format validation report"""
        report_data: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "validation_type": "HIPAA_Configuration",
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
                    "config_file": issue.config_file,
                    "section": issue.section,
                    "issue_type": issue.issue_type,
                    "message": issue.message,
                    "severity": issue.severity,
                    "hipaa_requirement": issue.hipaa_requirement,
                    "remediation": issue.remediation,
                }
            )

        return str(yaml.dump(report_data, default_flow_style=False))


def validate_hipaa_config() -> list[str]:
    """Legacy function for backward compatibility"""
    validator = HIPAAConfigValidator()
    total_issues, _, _ = validator.run_validation(["."])
    return [str(issue) for issue in validator.issues]


def main() -> None:
    """Main HIPAA validation function"""
    parser = argparse.ArgumentParser(
        description="Enhanced HIPAA Configuration Validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Check current directory
  %(prog)s --strict                 # Strict mode (warnings fail)
  %(prog)s --format json            # JSON output
  %(prog)s config/ services/        # Check specific directories
        """,
    )

    parser.add_argument(
        "paths",
        nargs="*",
        default=["."],
        help="Paths to check for HIPAA configuration files (default: current directory)",
    )

    parser.add_argument(
        "--format",
        choices=["text", "json", "yaml"],
        default="text",
        help="Output format (default: text)",
    )

    parser.add_argument(
        "--strict", action="store_true", help="Strict mode: warnings are treated as errors"
    )

    args = parser.parse_args()

    # Create HIPAA validator
    validator = HIPAAConfigValidator()

    # Run validation
    total_issues, errors, warnings = validator.run_validation(args.paths)

    # Generate and print report
    report = validator.generate_report(args.format)
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
