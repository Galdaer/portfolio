"""
Healthcare Security Middleware for Intelluxe AI Healthcare System

Provides HIPAA-compliant security middleware for handling PHI/PII
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class HealthcareSecurityMiddleware:
    """
    HIPAA-compliant security middleware for healthcare applications

    Provides:
    - PHI/PII detection and redaction
    - Security header management
    - Request/response sanitization
    - Audit logging
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """
        Initialize healthcare security middleware

        Args:
            config: Optional configuration for security settings
        """
        self.config = config or {}
        self.pii_patterns = [
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
            r"\b\d{3}-\d{3}-\d{4}\b",  # Phone
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
            r"\b\d{1,2}/\d{1,2}/\d{4}\b",  # DOB
            r"\bMRN\s*:?\s*\d+\b",  # Medical Record Number
            r"\b\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b",  # Credit Card
        ]

    def sanitize_data(self, data: Any) -> Any:
        """
        Sanitize data by removing or redacting PHI/PII

        Args:
            data: Data to sanitize (string, dict, list, etc.)

        Returns:
            Sanitized data with PHI/PII redacted
        """
        if isinstance(data, str):
            return self._redact_pii_from_string(data)
        if isinstance(data, dict):
            return {k: self.sanitize_data(v) for k, v in data.items()}
        if isinstance(data, list):
            return [self.sanitize_data(item) for item in data]
        return data

    def _redact_pii_from_string(self, text: str) -> str:
        """
        Redact PII patterns from text

        Args:
            text: Input text that may contain PII

        Returns:
            Text with PII patterns replaced with [REDACTED]
        """
        redacted = text
        for pattern in self.pii_patterns:
            redacted = re.sub(pattern, "[REDACTED]", redacted, flags=re.IGNORECASE)
        return redacted

    def get_security_headers(self) -> dict[str, str]:
        """
        Get HIPAA-appropriate security headers

        Returns:
            Dictionary of security headers
        """
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Cache-Control": "no-store, no-cache, must-revalidate, private",
        }

    def validate_request(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """
        Validate request for security compliance

        Args:
            request_data: Request data to validate

        Returns:
            Validation result with 'valid' boolean and optional 'issues' list
        """
        issues = []

        # Check for potential injection attempts
        if self._contains_injection_patterns(str(request_data)):
            issues.append("Potential injection attack detected")

        # Check for oversized payloads
        if len(str(request_data)) > self.config.get("max_request_size", 1024 * 1024):
            issues.append("Request payload too large")

        return {"valid": len(issues) == 0, "issues": issues}

    def _contains_injection_patterns(self, text: str) -> bool:
        """
        Check for common injection patterns

        Args:
            text: Text to check

        Returns:
            True if injection patterns detected
        """
        injection_patterns = [
            r"<script[^>]*>",
            r"javascript:",
            r"onload\s*=",
            r"onerror\s*=",
            r"union\s+select",
            r"drop\s+table",
            r"exec\s*\(",
        ]

        text_lower = text.lower()
        return any(re.search(pattern, text_lower, re.IGNORECASE) for pattern in injection_patterns)
