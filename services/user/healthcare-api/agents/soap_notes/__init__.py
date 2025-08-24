"""
SOAP Notes Agent Module

Provides structured clinical documentation generation from transcribed medical encounters.
Transforms raw transcription data into properly formatted clinical notes including
SOAP notes, progress notes, and other medical documentation formats.
"""

from .soap_notes_agent import SoapNotesAgent

__all__ = ["SoapNotesAgent"]
