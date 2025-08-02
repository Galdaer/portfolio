#!/usr/bin/env python3
"""
HIPAA Configuration Validation for Pre-commit
Validates HIPAA compliance configuration files.
"""

import os
import sys

import yaml


def validate_hipaa_config():
    """Validate HIPAA configuration files"""
    issues = []

    # Check for HIPAA compliance configuration
    hipaa_config_file = "config/security/hipaa_compliance.yml"
    if os.path.exists(hipaa_config_file):
        try:
            with open(hipaa_config_file) as f:
                config = yaml.safe_load(f)

            # Check required sections
            required_sections = [
                "administrative_safeguards",
                "physical_safeguards",
                "technical_safeguards",
                "encryption",
                "audit_monitoring",
            ]

            for section in required_sections:
                if section not in config:
                    issues.append(f"Missing required HIPAA section: {section}")

            # Check encryption requirements
            if "encryption" in config:
                encryption = config["encryption"]
                if "data_at_rest" not in encryption or not encryption["data_at_rest"].get(
                    "database_encryption"
                ):
                    issues.append("Database encryption not enabled in HIPAA config")

                if (
                    "data_in_transit" not in encryption
                    or encryption["data_in_transit"].get("tls_version") != "1.3"
                ):
                    issues.append("TLS 1.3 not configured for data in transit")

        except Exception as e:
            issues.append(f"Error validating HIPAA config: {str(e)}")
    else:
        issues.append("HIPAA compliance configuration file not found")

    return issues


def main() -> None:
    """Main HIPAA validation function"""
    issues = validate_hipaa_config()

    if issues:
        print("HIPAA Configuration Issues Found:")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("HIPAA configuration validation passed")


if __name__ == "__main__":
    main()
