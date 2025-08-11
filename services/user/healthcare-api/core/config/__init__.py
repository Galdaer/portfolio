"""
Configuration module for Healthcare AI System
"""

from .models import (
    ModelConfig,
    MODEL_CONFIG,
    get_primary_model,
    get_instruct_model,
    get_medical_model,
    get_research_model,
    get_validation_model,
    get_workflow_model,
    get_fallback_model,
    get_alternative_models,
    get_model_settings,
    MODEL_SETTINGS,
)

__all__ = [
    "ModelConfig",
    "MODEL_CONFIG",
    "get_primary_model",
    "get_instruct_model",
    "get_medical_model",
    "get_research_model",
    "get_validation_model",
    "get_workflow_model",
    "get_fallback_model",
    "get_alternative_models",
    "get_model_settings",
    "MODEL_SETTINGS",
]
