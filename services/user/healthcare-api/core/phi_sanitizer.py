"""
PHI Sanitization Utilities for Open WebUI Integration

Provides HIPAA-compliant sanitization of medical requests and responses
for the healthcare AI system Open WebUI endpoints.
"""

import json
import logging
from typing import Any, Dict, Optional

from src.healthcare_mcp.phi_detection import PHIDetector
from core.infrastructure.healthcare_logger import get_healthcare_logger

logger = get_healthcare_logger("core.phi_sanitizer")

# Global PHI detector instance
_phi_detector: Optional[PHIDetector] = None

def get_phi_detector() -> PHIDetector:
    """Get or create PHI detector singleton"""
    global _phi_detector
    if _phi_detector is None:
        try:
            _phi_detector = PHIDetector(use_presidio=True)
            logger.info("✅ PHI detector initialized with Presidio")
        except Exception as e:
            logger.warning(f"⚠️ Presidio unavailable, using basic PHI detection: {e}")
            _phi_detector = PHIDetector(use_presidio=False)
            logger.info("✅ PHI detector initialized with basic patterns")
    return _phi_detector


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
                        result = detector.detect_phi_sync(content)
                        if result.phi_detected:
                            sanitized_data["messages"][i]["content"] = result.masked_text
                            logger.warning(f"🛡️ PHI detected in request message {i}, types: {result.phi_types}")
        
        # Sanitize top-level message field (if present)
        if "message" in sanitized_data and isinstance(sanitized_data["message"], str):
            result = detector.detect_phi_sync(sanitized_data["message"])
            if result.phi_detected:
                sanitized_data["message"] = result.masked_text
                logger.warning(f"🛡️ PHI detected in request message, types: {result.phi_types}")
                
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
                            result = detector.detect_phi_sync(content)
                            if result.phi_detected:
                                sanitized_data["choices"][i]["message"]["content"] = result.masked_text
                                logger.warning(f"🛡️ PHI detected in response choice {i}, types: {result.phi_types}")
        
        # Sanitize top-level response content (if present)
        if "response" in sanitized_data and isinstance(sanitized_data["response"], str):
            result = detector.detect_phi_sync(sanitized_data["response"])
            if result.phi_detected:
                sanitized_data["response"] = result.masked_text
                logger.warning(f"🛡️ PHI detected in response, types: {result.phi_types}")
                
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
            "timestamp": logger.extra.get("timestamp", "unknown"),
            "details": details,
            "action": "masked_and_logged"
        }
        
        # Use healthcare logger for HIPAA audit trail
        logger.info("🛡️ HIPAA Audit: PHI detected and masked", extra={"audit": audit_entry})
        
    except Exception as e:
        logger.error(f"❌ Failed to log PHI incident: {e}")
