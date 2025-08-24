"""
PHI (Protected Health Information) Detector
Detects and helps protect sensitive health information
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class PHIDetector:
    """
    Detects potential PHI in text and data structures
    Based on HIPAA Safe Harbor guidelines
    """

    def __init__(self):
        """Initialize PHI detector with patterns"""
        # Common PHI patterns
        self.patterns = {
            "ssn": re.compile(r"\b\d{3}-?\d{2}-?\d{4}\b"),
            "phone": re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"),
            "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
            "mrn": re.compile(r"\b(MRN|Medical Record Number)[:\s]*\d+\b", re.IGNORECASE),
            "dob": re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"),
            "credit_card": re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
            "medicare": re.compile(r"\b\d{3}-?\d{2}-?\d{4}[A-Z]?\b"),
            "insurance_id": re.compile(r"\b[A-Z]{3}\d{9}\b"),
        }

        # PHI keywords to look for
        self.phi_keywords = [
            "patient", "diagnosis", "treatment", "medication",
            "medical", "health", "clinical", "prescription",
            "insurance", "claim", "provider", "physician",
            "hospital", "clinic", "appointment", "surgery",
            "condition", "symptom", "disease", "disorder",
        ]

        # Fields that commonly contain PHI
        self.phi_fields = [
            "patient_name", "patient_id", "patient_dob",
            "patient_phone", "patient_email", "patient_address",
            "patient_ssn", "insurance_id", "medical_record_number",
            "diagnosis", "treatment_plan", "medications",
            "clinical_notes", "lab_results", "imaging_results",
        ]

    def contains_phi(self, text: str) -> bool:
        """
        Check if text potentially contains PHI

        Args:
            text: Text to check

        Returns:
            True if potential PHI detected
        """
        if not text:
            return False

        text_lower = text.lower()

        # Check for pattern matches
        for pattern_name, pattern in self.patterns.items():
            if pattern.search(text):
                logger.debug(f"PHI pattern detected: {pattern_name}")
                return True

        # Check for PHI keywords (but be less aggressive)
        # Only flag if multiple keywords present
        keyword_count = sum(1 for keyword in self.phi_keywords if keyword in text_lower)
        if keyword_count >= 3:
            logger.debug(f"Multiple PHI keywords detected: {keyword_count}")
            return True

        return False

    def scan_dict(self, data: dict[str, Any]) -> list[str]:
        """
        Scan dictionary for PHI fields

        Args:
            data: Dictionary to scan

        Returns:
            List of fields that may contain PHI
        """
        phi_detected = []

        for key, value in data.items():
            # Check if field name suggests PHI
            key_lower = key.lower()
            if any(phi_field in key_lower for phi_field in self.phi_fields):
                phi_detected.append(key)
                continue

            # Check if value contains PHI
            if isinstance(value, str) and self.contains_phi(value):
                phi_detected.append(key)
            elif isinstance(value, dict):
                nested_phi = self.scan_dict(value)
                if nested_phi:
                    phi_detected.append(f"{key}.{','.join(nested_phi)}")
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, str) and self.contains_phi(item):
                        phi_detected.append(f"{key}[{i}]")
                    elif isinstance(item, dict):
                        nested_phi = self.scan_dict(item)
                        if nested_phi:
                            phi_detected.append(f"{key}[{i}].{','.join(nested_phi)}")

        return phi_detected

    def sanitize_text(self, text: str, replacement: str = "[REDACTED]") -> str:
        """
        Sanitize text by removing potential PHI

        Args:
            text: Text to sanitize
            replacement: Replacement string for PHI

        Returns:
            Sanitized text
        """
        if not text:
            return text

        sanitized = text

        # Replace pattern matches
        for _pattern_name, pattern in self.patterns.items():
            sanitized = pattern.sub(replacement, sanitized)

        return sanitized

    def sanitize_dict(self, data: dict[str, Any], deep_copy: bool = True) -> dict[str, Any]:
        """
        Sanitize dictionary by redacting PHI fields

        Args:
            data: Dictionary to sanitize
            deep_copy: Whether to create a deep copy

        Returns:
            Sanitized dictionary
        """
        import copy

        if deep_copy:
            data = copy.deepcopy(data)

        phi_fields = self.scan_dict(data)

        for field_path in phi_fields:
            # Parse field path and redact
            self._redact_field(data, field_path)

        return data

    def _redact_field(self, data: dict[str, Any], field_path: str):
        """Redact a field in a dictionary based on path"""
        parts = field_path.split(".")
        current = data

        for _i, part in enumerate(parts[:-1]):
            if "[" in part:
                # Handle array notation
                field_name, index = part.split("[")
                index = int(index.rstrip("]"))
                current = current[field_name][index]
            else:
                current = current[part]

        # Redact the final field
        final_part = parts[-1]
        if "[" in final_part:
            field_name, index = final_part.split("[")
            index = int(index.rstrip("]"))
            current[field_name][index] = "[REDACTED-PHI]"
        else:
            current[final_part] = "[REDACTED-PHI]"

    def get_risk_level(self, text: str) -> str:
        """
        Assess PHI risk level

        Args:
            text: Text to assess

        Returns:
            Risk level: 'none', 'low', 'medium', 'high'
        """
        if not text:
            return "none"

        # Count pattern matches
        pattern_matches = sum(
            1 for pattern in self.patterns.values()
            if pattern.search(text)
        )

        # Count keyword matches
        text_lower = text.lower()
        keyword_matches = sum(
            1 for keyword in self.phi_keywords
            if keyword in text_lower
        )

        # Determine risk level
        if pattern_matches >= 2 or (pattern_matches >= 1 and keyword_matches >= 2):
            return "high"
        if pattern_matches >= 1 or keyword_matches >= 3:
            return "medium"
        if keyword_matches >= 1:
            return "low"
        return "none"
