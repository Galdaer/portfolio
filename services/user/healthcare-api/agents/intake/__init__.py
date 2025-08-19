"""
Intake Agent Module
Handles patient registration, scheduling, and administrative workflows
"""

from .intake_agent import HealthcareIntakeAgent
from .router import router

__all__ = ["HealthcareIntakeAgent", "router"]
