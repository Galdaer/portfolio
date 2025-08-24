"""
PHI-Aware Conversation Storage
Secure storage with automatic PHI detection and sanitization
"""

from typing import Any

from core.infrastructure.healthcare_logger import get_healthcare_logger
from core.infrastructure.phi_monitor import sanitize_healthcare_data, scan_for_phi


class PHIAwareConversationStorage:
    """
    PHI-aware storage system for conversation data

    Automatically detects and sanitizes PHI while preserving
    conversational context for healthcare applications.
    """

    def __init__(self):
        self.logger = get_healthcare_logger("phi_aware_storage")

    def sanitize_message(self, message: dict[str, Any]) -> dict[str, Any]:
        """
        Sanitize a message for PHI content

        Args:
            message: Message data to sanitize

        Returns:
            Dict: Sanitized message data
        """
        return sanitize_healthcare_data(message)

    def detect_phi_in_content(self, content: str) -> dict[str, Any]:
        """
        Detect PHI in message content

        Args:
            content: Message content to analyze

        Returns:
            Dict: PHI detection results
        """
        return scan_for_phi(content)
