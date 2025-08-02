"""
Configuration package for Intelluxe AI Healthcare System

Provides centralized configuration management with environment variable support,
healthcare-specific settings, and compliance configurations.
"""

from .app import IntelluxeConfig, config
from .environment_detector import EnvironmentDetector
from .healthcare_security import HealthcareSecurityMiddleware
from .rbac_foundation import Permission, RBACFoundation, ResourceType

# Export main configuration objects
__all__ = [
    "config",
    "IntelluxeConfig",
    "EnvironmentDetector",
    "HealthcareSecurityMiddleware",
    "RBACFoundation",
    "Permission",
    "ResourceType",
]

# Version information
__version__ = "1.0.0"


# Configuration validation
def validate_config() -> bool:
    """Validate that all required configuration is present"""
    required_fields = ["project_name", "database_name", "ollama_url", "mcp_server_url"]

    for field in required_fields:
        if not hasattr(config, field):
            raise ValueError(f"Required configuration field '{field}' is missing")

    return True


# Healthcare compliance check
def check_compliance_config() -> bool:
    """Check that healthcare compliance settings are properly configured"""
    compliance_fields = [
        "data_retention_days",
        "audit_log_level",
        "pii_redaction_enabled",
        "rbac_enabled",
    ]

    missing_fields = []
    for field in compliance_fields:
        if not hasattr(config, field):
            missing_fields.append(field)

    if missing_fields:
        raise ValueError(f"Healthcare compliance fields missing: {missing_fields}")

    # Validate healthcare-specific values
    if config.data_retention_days < 2555:  # 7 years minimum for healthcare
        raise ValueError(
            "Data retention must be at least 7 years (2555 days) for healthcare compliance"
        )

    return True


# Development vs Production configuration helpers
def is_development() -> bool:
    """Check if running in development mode"""
    return getattr(config, "development_mode", True)


def is_production() -> bool:
    """Check if running in production mode"""
    return not is_development()


# Healthcare AI specific configuration helpers
def get_ai_config() -> Dict[str, Any]:
    """Get AI-specific configuration settings"""
    return {
        "ollama_url": config.ollama_url,
        "ollama_max_loaded_models": config.ollama_max_loaded_models,
        "ollama_keep_alive": config.ollama_keep_alive,
        "mcp_server_url": config.mcp_server_url,
        "gpu_memory_fraction": config.gpu_memory_fraction,
    }


def get_database_config() -> Dict[str, Any]:
    """Get database configuration for healthcare data storage"""
    return {
        "database_name": config.database_name,
        "postgres_password": config.postgres_password,
        "redis_password": config.redis_password,
    }


def get_compliance_config():
    """Get healthcare compliance configuration"""
    return {
        "data_retention_days": config.data_retention_days,
        "audit_log_level": config.audit_log_level,
        "pii_redaction_enabled": config.pii_redaction_enabled,
        "rbac_enabled": config.rbac_enabled,
    }
