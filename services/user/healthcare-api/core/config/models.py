"""
Centralized Model Configuration for Healthcare AI System
Healthcare compliance disclaimer: Model configurations are for administrative and documentation support only.
No medical advice, diagnosis, or treatment recommendations are provided.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class ModelConfig:
    """Configuration for AI models used in healthcare system"""
    
    # Primary models for different use cases
    PRIMARY_CHAT_MODEL: str = "llama3.1:8b"
    PRIMARY_INSTRUCT_MODEL: str = "llama3.1:8b-instruct-q4_K_M"
    FALLBACK_MODEL: str = "llama3.1:8b"
    
    # Specialized models for specific tasks
    MEDICAL_ANALYSIS_MODEL: str = "llama3.1:8b-instruct-q4_K_M"
    RESEARCH_MODEL: str = "llama3.1:8b-instruct-q4_K_M"
    VALIDATION_MODEL: str = "llama3.1:8b-instruct-q4_K_M"
    WORKFLOW_MODEL: str = "llama3.1:8b"
    
    # Alternative models (when primary unavailable)
    ALTERNATIVE_MODELS: list = None
    
    def __post_init__(self):
        if self.ALTERNATIVE_MODELS is None:
            self.ALTERNATIVE_MODELS = [
                "mistral:7b-instruct-q4_K_M",
                "llama3.1:8b",
                "llama3:8b"
            ]
    
    @classmethod
    def from_env(cls) -> 'ModelConfig':
        """Create model config from environment variables"""
        return cls(
            PRIMARY_CHAT_MODEL=os.getenv("PRIMARY_CHAT_MODEL", "llama3.1:8b"),
            PRIMARY_INSTRUCT_MODEL=os.getenv("PRIMARY_INSTRUCT_MODEL", "llama3.1:8b-instruct-q4_K_M"),
            FALLBACK_MODEL=os.getenv("FALLBACK_MODEL", "llama3.1:8b"),
            MEDICAL_ANALYSIS_MODEL=os.getenv("MEDICAL_ANALYSIS_MODEL", "llama3.1:8b-instruct-q4_K_M"),
            RESEARCH_MODEL=os.getenv("RESEARCH_MODEL", "llama3.1:8b-instruct-q4_K_M"),
            VALIDATION_MODEL=os.getenv("VALIDATION_MODEL", "llama3.1:8b-instruct-q4_K_M"),
            WORKFLOW_MODEL=os.getenv("WORKFLOW_MODEL", "llama3.1:8b"),
        )
    
    def get_model_for_task(self, task_type: str) -> str:
        """Get appropriate model for specific task type"""
        task_model_map = {
            "chat": self.PRIMARY_CHAT_MODEL,
            "instruct": self.PRIMARY_INSTRUCT_MODEL,
            "medical_analysis": self.MEDICAL_ANALYSIS_MODEL,
            "research": self.RESEARCH_MODEL,
            "validation": self.VALIDATION_MODEL,
            "workflow": self.WORKFLOW_MODEL,
            "fallback": self.FALLBACK_MODEL,
            # Add the task types we were using in the other config
            "clinical": self.MEDICAL_ANALYSIS_MODEL,
            "reasoning": self.RESEARCH_MODEL,
            "fast": self.PRIMARY_CHAT_MODEL,
            "default": self.PRIMARY_CHAT_MODEL,
        }
        return task_model_map.get(task_type, self.PRIMARY_CHAT_MODEL)

# Global model configuration instance
MODEL_CONFIG = ModelConfig.from_env()

# Convenience functions for backward compatibility
def get_primary_model() -> str:
    """Get the primary chat model"""
    return MODEL_CONFIG.PRIMARY_CHAT_MODEL

def get_instruct_model() -> str:
    """Get the primary instruction-following model"""
    return MODEL_CONFIG.PRIMARY_INSTRUCT_MODEL

def get_medical_model() -> str:
    """Get the model for medical analysis tasks"""
    return MODEL_CONFIG.MEDICAL_ANALYSIS_MODEL

def get_research_model() -> str:
    """Get the model for research tasks"""
    return MODEL_CONFIG.RESEARCH_MODEL

def get_validation_model() -> str:
    """Get the model for validation tasks"""
    return MODEL_CONFIG.VALIDATION_MODEL

def get_workflow_model() -> str:
    """Get the model for workflow orchestration"""
    return MODEL_CONFIG.WORKFLOW_MODEL

def get_fallback_model() -> str:
    """Get the fallback model when primary is unavailable"""
    return MODEL_CONFIG.FALLBACK_MODEL

def get_alternative_models() -> list:
    """Get list of alternative models to try"""
    return MODEL_CONFIG.ALTERNATIVE_MODELS.copy()

# Model capabilities and settings
MODEL_SETTINGS: Dict[str, Dict[str, Any]] = {
    "llama3.1:8b": {
        "max_tokens": 8192,
        "temperature": 0.7,
        "top_p": 0.9,
        "context_window": 8192,
        "use_case": ["chat", "general"],
    },
    "llama3.1:8b-instruct-q4_K_M": {
        "max_tokens": 4096,
        "temperature": 0.3,
        "top_p": 0.85,
        "context_window": 8192,
        "use_case": ["medical_analysis", "research", "validation", "instruct"],
    },
    "mistral:7b-instruct-q4_K_M": {
        "max_tokens": 4096,
        "temperature": 0.3,
        "top_p": 0.9,
        "context_window": 8192,
        "use_case": ["fallback", "instruct"],
    },
}

def get_model_settings(model_name: str) -> Dict[str, Any]:
    """Get settings for a specific model"""
    return MODEL_SETTINGS.get(model_name, {
        "max_tokens": 4096,
        "temperature": 0.7,
        "top_p": 0.9,
        "context_window": 4096,
        "use_case": ["general"],
    })
