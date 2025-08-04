"""
Healthcare Transcription Agent Module

This module provides administrative transcription support for healthcare organizations,
including medical dictation processing, clinical note generation, and documentation formatting.

MEDICAL DISCLAIMER: This module provides administrative transcription support only.
It does not provide medical advice, diagnosis, or treatment recommendations.
All medical decisions must be made by qualified healthcare professionals.
"""

from .transcription_agent import (
    TranscriptionAgent,
    transcription_agent,
    TranscriptionResult,
    ClinicalNoteResult,
    DocumentationTemplate
)
from .router import router

__all__ = [
    'TranscriptionAgent',
    'transcription_agent',
    'TranscriptionResult',
    'ClinicalNoteResult',
    'DocumentationTemplate',
    'router'
]
