"""
Configuration module for Healthcare AI System
"""

from .models import (
    MODEL_CONFIG,
    MODEL_SETTINGS,
    ModelConfig,
    get_alternative_models,
    get_fallback_model,
    get_instruct_model,
    get_medical_model,
    get_model_settings,
    get_primary_model,
    get_research_model,
    get_validation_model,
    get_workflow_model,
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
