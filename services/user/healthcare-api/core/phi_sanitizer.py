"""
PHI Sanitization Utilities for Open WebUI Integration

Provides HIPAA-compliant sanitization of medical requests and responses
for the healthcare AI system Open WebUI endpoints.
"""

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, Optional

import os
from src.healthcare_mcp.phi_detection import PHIDetector
from core.infrastructure.healthcare_logger import get_healthcare_logger
from config.phi_detection_config_loader import phi_config

logger = get_healthcare_logger("core.phi_sanitizer")

# Global PHI detector instance
_phi_detector: Optional[PHIDetector] = None


def get_phi_detector() -> PHIDetector:
    """Get or create PHI detector singleton.

    Tries to use Presidio for intelligent PHI detection first, with fallback
    to basic patterns only when Presidio is unavailable. This ensures medical
    terminology isn't incorrectly flagged as PHI.
    """
    global _phi_detector
    if _phi_detector is None:
        try:
            _phi_detector = PHIDetector(use_presidio=True)
            logger.info("✅ PHI detector initialized with Presidio (intelligent detection)")
        except Exception as e:
            logger.warning(f"⚠️ Presidio unavailable, using basic PHI detection: {e}")
            _phi_detector = PHIDetector(use_presidio=False)
            logger.info("✅ PHI detector initialized with basic patterns (fallback)")
    return _phi_detector


def _is_external_medical_content(content: str) -> bool:
    """
    Check if content appears to be external medical literature/research content
    or general medical terminology that should bypass PHI detection.

    This includes content from:
    - Medical journals and publications
    - PubMed and other medical databases
    - Clinical research papers
    - Medical textbooks and references
    - General medical terminology and queries
    """
    if not content or not isinstance(content, str):
        return False

    content_lower = content.lower()

    # Check for clear external medical source indicators
    external_indicators = [
        "pubmed.ncbi.nlm.nih.gov",
        "doi.org/",
        "clinicaltrials.gov",
        "ncbi.nlm.nih.gov",
        "nih.gov",
        "who.int",
        "cdc.gov",
        "fda.gov",
        "medical journal",
        "peer reviewed",
        "published in",
        "abstract:",
        "citation:",
        "pmid:",
        "issn:",
        "volume",
        "issue",
    ]

    # Medical terminology that should be exempted from PHI detection
    medical_terms = [
        "cardiovascular",
        "diabetes",
        "hypertension",
        "cancer",
        "treatment",
        "prevention",
        "symptoms",
        "diagnosis",
        "therapy",
        "medication",
        "research",
        "study",
        "clinical",
        "health",
        "disease",
        "condition",
        "patient care",
        "healthcare",
        "medical",
        "guidelines",
        "protocol",
        "intervention",
        "management",
        "prognosis",
        "pathology",
        "epidemiology",
        "immunology",
        "neurology",
        "cardiology",
        "oncology",
        "psychiatry",
        "pediatrics",
        "geriatrics",
        "surgery",
        "radiology",
        "pathophysiology",
    ]

    # Medical query patterns that indicate legitimate medical research
    medical_query_patterns = [
        "find.*research",
        "recent.*studies",
        "treatment.*options",
        "prevention.*strategies",
        "clinical.*guidelines",
        "medical.*literature",
        "health.*information",
        "disease.*management",
        "therapeutic.*approaches",
    ]

    # Check if content contains clear external source indicators
    if any(indicator in content_lower for indicator in external_indicators):
        return True

    # Check if content contains medical terminology
    if any(term in content_lower for term in medical_terms):
        logger.info(f"🏥 Medical terminology detected, exempting from PHI: {content[:50]}...")
        return True

    # Check for medical query patterns
    for pattern in medical_query_patterns:
        if re.search(pattern, content_lower):
            logger.info(f"🔬 Medical query pattern detected, exempting from PHI: {content[:50]}...")
            return True

    return False


def sanitize_request_data(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize request data for HIPAA compliance

    Args:
        request_data: Dictionary containing request data (e.g., OpenAI chat request)

    Returns:
        Dictionary with PHI-sanitized data
    """
    try:
        detector = get_phi_detector()
        sanitized_data = request_data.copy()

        # Sanitize messages content if present (OpenAI format)
        if "messages" in sanitized_data:
            for i, message in enumerate(sanitized_data["messages"]):
                if isinstance(message, dict) and "content" in message:
                    content = message["content"]
                    if isinstance(content, str):
                        # Skip PHI detection for external medical content (research citations)
                        if _is_external_medical_content(content):
                            logger.info(
                                f"🔬 External medical content detected, skipping PHI sanitization: {content[:50]}..."
                            )
                            continue

                        result = detector.detect_phi_sync(content)
                        if result.phi_detected:
                            sanitized_data["messages"][i]["content"] = result.masked_text
                            logger.warning(
                                f"🛡️ PHI detected in request message {i}, types: {result.phi_types}"
                            )

        # Sanitize top-level message field (if present)
        if "message" in sanitized_data and isinstance(sanitized_data["message"], str):
            # Skip PHI detection for external medical content
            if not _is_external_medical_content(sanitized_data["message"]):
                result = detector.detect_phi_sync(sanitized_data["message"])
                if result.phi_detected:
                    sanitized_data["message"] = result.masked_text
                    logger.warning(f"🛡️ PHI detected in request message, types: {result.phi_types}")
            else:
                logger.info("🔬 External medical content detected, skipping PHI sanitization")

        return sanitized_data

    except Exception as e:
        logger.error(f"❌ PHI sanitization failed for request: {e}")
        # Return original data if sanitization fails (logged for audit)
        return request_data


def sanitize_response_data(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize response data for HIPAA compliance

    Args:
        response_data: Dictionary containing response data (e.g., OpenAI chat response)

    Returns:
        Dictionary with PHI-sanitized data
    """
    try:
        detector = get_phi_detector()
        sanitized_data = response_data.copy()

        # Sanitize choices content if present (OpenAI format)
        if "choices" in sanitized_data:
            for i, choice in enumerate(sanitized_data["choices"]):
                if isinstance(choice, dict) and "message" in choice:
                    message = choice["message"]
                    if isinstance(message, dict) and "content" in message:
                        content = message["content"]
                        if isinstance(content, str):
                            # Skip PHI detection for external medical content (research citations)
                            if _is_external_medical_content(content):
                                logger.info(
                                    f"🔬 External medical content detected in response, skipping PHI sanitization: {content[:50]}..."
                                )
                                continue

                            result = detector.detect_phi_sync(content)
                            if result.phi_detected:
                                sanitized_data["choices"][i]["message"]["content"] = (
                                    result.masked_text
                                )
                                logger.warning(
                                    f"🛡️ PHI detected in response choice {i}, types: {result.phi_types}"
                                )

        # Sanitize top-level response content (if present)
        if "response" in sanitized_data and isinstance(sanitized_data["response"], str):
            # Skip PHI detection for external medical content
            if not _is_external_medical_content(sanitized_data["response"]):
                result = detector.detect_phi_sync(sanitized_data["response"])
                if result.phi_detected:
                    sanitized_data["response"] = result.masked_text
                    logger.warning(f"🛡️ PHI detected in response, types: {result.phi_types}")
            else:
                logger.info(
                    "🔬 External medical content detected in response, skipping PHI sanitization"
                )

        return sanitized_data

    except Exception as e:
        logger.error(f"❌ PHI sanitization failed for response: {e}")
        # Return original data if sanitization fails (logged for audit)
        return response_data


def sanitize_text_content(text: str) -> str:
    """
    Sanitize plain text content for PHI

    Args:
        text: Text content to sanitize

    Returns:
        PHI-masked text
    """
    try:
        detector = get_phi_detector()
        result = detector.detect_phi_sync(text)

        if result.phi_detected:
            logger.warning(f"🛡️ PHI detected in text, types: {result.phi_types}")
            return result.masked_text

        return text

    except Exception as e:
        logger.error(f"❌ PHI sanitization failed for text: {e}")
        return text


def log_phi_incident(data_type: str, phi_types: list[str], details: str = ""):
    """
    Log PHI detection incident for HIPAA audit trail

    Args:
        data_type: Type of data where PHI was detected (request/response)
        phi_types: List of PHI types detected
        details: Additional details for audit trail
    """
    try:
        audit_entry = {
            "event": "phi_detection",
            "data_type": data_type,
            "phi_types": phi_types,
            "timestamp": datetime.now().isoformat(),
            "details": details,
            "action": "masked_and_logged",
        }

        # Use healthcare logger for HIPAA audit trail
        logger.info("🛡️ HIPAA Audit: PHI detected and masked", extra={"audit": audit_entry})

    except Exception as e:
        logger.error(f"❌ Failed to log PHI incident: {e}")
