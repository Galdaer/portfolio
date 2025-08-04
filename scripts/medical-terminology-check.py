#!/usr/bin/env python3
"""
Medical Terminology Validation for Pre-commit
Ensures proper capitalization of medical terms.
"""

import os
import re
import sys


def check_medical_terminology(filename: str) -> list[str]:
    """Check for proper medical terminology"""
    # Common medical terminology that should be spelled correctly
    medical_terms = {
        "hipaa": "HIPAA",
        "phi": "PHI",
        "fhir": "FHIR",
        "hl7": "HL7",
        "icd": "ICD",
        "cpt": "CPT",
        "snomed": "SNOMED",
        "loinc": "LOINC",
    }

    try:
        with open(filename, encoding="utf-8") as f:
            content = f.read()

        issues = []

        for incorrect, correct in medical_terms.items():
            # Look for incorrect lowercase versions in comments and strings
            pattern = r"(?i)\b" + re.escape(incorrect) + r"\b"
            if re.search(pattern, content):
                # Check if it's already correctly capitalized
                correct_pattern = r"\b" + re.escape(correct) + r"\b"
                if not re.search(correct_pattern, content):
                    issues.append(f"{filename}: Use {correct} instead of {incorrect}")

        return issues
    except Exception:
        return []


def main() -> None:
    """Main terminology validation function"""
    # Check relevant files
    issues = []
    for root, _dirs, files in os.walk("."):
        if any(skip in root for skip in [".git", "node_modules", "__pycache__"]):
            continue

        for file in files:
            if file.endswith((".py", ".md", ".rst", ".txt")):
                filepath = os.path.join(root, file)
                issues.extend(check_medical_terminology(filepath))

    if issues:
        print("Medical Terminology Issues Found:")
        for issue in issues:
            print(f"  - {issue}")
        print("Please use proper medical terminology capitalization.")
        sys.exit(1)
    else:
        print("Medical terminology validation passed")


if __name__ == "__main__":
    main()
