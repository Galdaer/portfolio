"""
Healthcare Scheduling Optimizer Agent Module

This module provides administrative scheduling support for healthcare organizations,
including appointment scheduling, calendar optimization, and resource management.

MEDICAL DISCLAIMER: This module provides administrative scheduling support and resource
optimization assistance only. It helps healthcare professionals optimize appointment
scheduling, manage provider calendars, and improve operational efficiency. It does not
provide medical advice, diagnosis, or treatment recommendations. All medical decisions
must be made by qualified healthcare professionals.
"""

from .scheduling_agent import (
    SchedulingOptimizerAgent,
    scheduling_optimizer_agent,
    SchedulingResult,
    AppointmentSlot,
    OptimizationRecommendation
)
from .router import router

__all__ = [
    'SchedulingOptimizerAgent',
    'scheduling_optimizer_agent',
    'SchedulingResult',
    'AppointmentSlot',
    'OptimizationRecommendation',
    'router'
]
