"""
Enhanced Session Management for Open WebUI
PHI-aware conversation continuity with semantic understanding

Provides intelligent cross-session context while maintaining healthcare privacy compliance.
"""

from .enhanced_session_manager import EnhancedSessionManager
from .medical_topic_extractor import MedicalTopicExtractor
from .phi_aware_storage import PHIAwareConversationStorage
from .privacy_manager import PrivacyManager
from .semantic_search import SemanticSearchEngine

__all__ = [
    "EnhancedSessionManager",
    "PHIAwareConversationStorage",
    "MedicalTopicExtractor",
    "PrivacyManager",
    "SemanticSearchEngine",
]

__version__ = "1.0.0"
