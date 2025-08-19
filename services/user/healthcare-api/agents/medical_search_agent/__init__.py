"""
Medical Literature Search Agent
Provides medical information search and literature review capabilities
"""

from .medical_search_agent import MedicalLiteratureSearchAssistant
from .router import router

__all__ = ["MedicalLiteratureSearchAssistant", "router"]
