#!/usr/bin/env python3
"""
Healthcare Compliance Check for Pre-commit
Validates code for HIPAA compliance and medical data handling.
"""

import os
import re
import sys


def check_healthcare_compliance(filename):
    """Check file for healthcare compliance issues"""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()

        issues = []

        # Check for medical data handling without proper protection
        if re.search(r"patient.*data|medical.*record|phi", content, re.IGNORECASE):
            if not re.search(r"encrypt|audit|log|security", content, re.IGNORECASE):
                issues.append(f"{filename}: Medical data handling without security measures")

        # Check for hardcoded medical information
        medical_patterns = [
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN pattern
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
            r"\b\d{3}-\d{3}-\d{4}\b",  # Phone
        ]

        for pattern in medical_patterns:
            if re.search(pattern, content):
                issues.append(f"{filename}: Potential PHI pattern detected")
                break

        # Check for proper medical disclaimers in AI code
        if re.search(r"medical.*ai|ai.*medical|diagnosis|treatment", content, re.IGNORECASE):
            if not re.search(
                r"disclaimer|educational.*purpose|consult.*healthcare", content, re.IGNORECASE
            ):
                issues.append(f"{filename}: Medical AI code missing disclaimers")

        return issues
    except Exception as e:
        return [f"{filename}: Error checking compliance - {str(e)}"]


def main():
    """Main compliance check function"""
    # Check all Python files
    issues = []
    for root, dirs, files in os.walk("."):
        # Skip certain directories
        if any(skip in root for skip in [".git", "node_modules", "__pycache__", ".pytest_cache"]):
            continue

        for file in files:
            if file.endswith((".py", ".js", ".ts")):
                filepath = os.path.join(root, file)
                issues.extend(check_healthcare_compliance(filepath))

    if issues:
        print("Healthcare Compliance Issues Found:")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("Healthcare compliance check passed")


if __name__ == "__main__":
    main()
