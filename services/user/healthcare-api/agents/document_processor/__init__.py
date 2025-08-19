"""
Document Processor Agent Module
Handles medical document formatting, organization, and administrative processing
"""

from .document_processor import HealthcareDocumentProcessor
from .router import router

__all__ = ["HealthcareDocumentProcessor", "router"]
