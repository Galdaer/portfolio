"""
Healthcare Transcription Agent Module

This module provides administrative transcription support for healthcare organizations,
including medical dictation processing, clinical note generation, and documentation formatting.

MEDICAL DISCLAIMER: This module provides administrative transcription support only.
It does not provide medical advice, diagnosis, or treatment recommendations.
All medical decisions must be made by qualified healthcare professionals.
"""

from .router import router
from .transcription_agent import (
    ClinicalNoteResult,
    DocumentationTemplate,
    TranscriptionAgent,
    TranscriptionResult,
    transcription_agent,
)

__all__ = [
    "TranscriptionAgent",
    "transcription_agent",
    "TranscriptionResult",
    "ClinicalNoteResult",
    "DocumentationTemplate",
    "router",
]
