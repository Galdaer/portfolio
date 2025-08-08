"""
Enhanced Healthcare Configuration Management

Centralized configuration with environment-specific settings,
healthcare compliance parameters, and model configurations.
"""

import os
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class EnvironmentType(str, Enum):
    """Deployment environment types"""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class ModelConfig(BaseModel):
    """AI model configuration settings"""

    temperature: float = Field(default=0.1, description="Model temperature for medical responses")
    max_tokens: int = Field(default=2048, description="Maximum tokens for responses")
    top_p: float = Field(default=0.9, description="Top-p sampling parameter")
    frequency_penalty: float = Field(default=0.0, description="Frequency penalty")
    presence_penalty: float = Field(default=0.0, description="Presence penalty")
    timeout_seconds: int = Field(default=30, description="Model response timeout")


class HealthcareComplianceConfig(BaseModel):
    """HIPAA and healthcare compliance settings"""

    phi_detection_enabled: bool = Field(default=True, description="Enable PHI detection")
    audit_logging_enabled: bool = Field(default=True, description="Enable audit logging")
    session_timeout_minutes: int = Field(default=480, description="8-hour healthcare shift timeout")
    max_failed_auth_attempts: int = Field(
        default=3, description="Max failed authentication attempts",
    )
    require_mfa: bool = Field(default=False, description="Require multi-factor authentication")
    data_retention_days: int = Field(default=2555, description="7-year HIPAA retention")


class CacheConfig(BaseModel):
    """Caching configuration for healthcare data"""

    redis_url: str = Field(default="redis://localhost:6379", description="Redis connection URL")
    medical_literature_ttl_hours: int = Field(
        default=24, description="Medical literature cache TTL",
    )
    drug_interaction_ttl_hours: int = Field(default=12, description="Drug interaction cache TTL")
    patient_context_ttl_minutes: int = Field(default=60, description="Patient context cache TTL")
    max_cache_size_mb: int = Field(default=256, description="Maximum cache size in MB")


class DatabaseConfig(BaseModel):
    """Database configuration for healthcare data"""

    postgres_url: str = Field(
        default="postgresql://localhost:5432/intelluxe", description="PostgreSQL URL",
    )
    max_connections: int = Field(default=20, description="Maximum database connections")
    connection_timeout_seconds: int = Field(default=30, description="Connection timeout")
    query_timeout_seconds: int = Field(default=60, description="Query timeout")
    enable_ssl: bool = Field(default=True, description="Enable SSL for database connections")


class MonitoringConfig(BaseModel):
    """Health monitoring and alerting configuration"""

    health_check_interval_seconds: int = Field(default=30, description="Health check interval")
    alert_threshold_error_rate: float = Field(
        default=0.05, description="Error rate alert threshold (5%)",
    )
    alert_threshold_response_time_ms: int = Field(
        default=5000, description="Response time alert threshold",
    )
    log_level: str = Field(default="INFO", description="Logging level")
    enable_performance_metrics: bool = Field(default=True, description="Enable performance metrics")


class HealthcareConfig(BaseModel):
    """Comprehensive healthcare system configuration"""

    environment: EnvironmentType = Field(default=EnvironmentType.DEVELOPMENT)

    # Core configurations
    model: ModelConfig = Field(default_factory=ModelConfig)
    compliance: HealthcareComplianceConfig = Field(default_factory=HealthcareComplianceConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)

    # Environment-specific settings
    debug_mode: bool = Field(default=False, description="Enable debug mode")
    api_rate_limit_per_minute: int = Field(default=60, description="API rate limit per minute")
    jwt_secret_key: str = Field(default="change-in-production", description="JWT secret key")


class HealthcareConfigManager:
    """Configuration manager with environment-specific overrides"""

    def __init__(self, config_path: str | None = None):
        self.config_path = config_path or "config/healthcare_settings.yml"
        self.config: HealthcareConfig | None = None
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from YAML file with environment overrides"""

        # Start with default configuration
        config_data: dict[str, Any] = {}

        # Load from YAML file if it exists
        config_file = Path(self.config_path)
        if config_file.exists():
            with open(config_file) as f:
                file_config = yaml.safe_load(f) or {}
                config_data.update(file_config)

        # Apply environment-specific overrides
        env = os.getenv("HEALTHCARE_ENV", "development")
        config_data["environment"] = env

        # Environment-specific database URLs
        if env == "production":
            database_config = config_data.setdefault("database", {})
            if isinstance(database_config, dict):
                database_config["postgres_url"] = os.getenv(
                    "DATABASE_URL",
                    config_data.get("database", {}).get(
                        "postgres_url", "postgresql://localhost:5432/intelluxe",
                    )
                    if isinstance(config_data.get("database"), dict)
                    else "postgresql://localhost:5432/intelluxe",
                )
            cache_config = config_data.setdefault("cache", {})
            if isinstance(cache_config, dict):
                cache_config["redis_url"] = os.getenv(
                    "REDIS_URL",
                    config_data.get("cache", {}).get("redis_url", "redis://localhost:6379")
                    if isinstance(config_data.get("cache"), dict)
                    else "redis://localhost:6379",
                )

        # Security overrides from environment
        config_data["jwt_secret_key"] = os.getenv(
            "JWT_SECRET_KEY", config_data.get("jwt_secret_key", "change-in-production"),
        )

        # Development-specific settings
        if env == "development":
            config_data["debug_mode"] = True
            compliance_config = config_data.setdefault("compliance", {})
            if isinstance(compliance_config, dict):
                compliance_config["require_mfa"] = False
            monitoring_config = config_data.setdefault("monitoring", {})
            if isinstance(monitoring_config, dict):
                monitoring_config["log_level"] = "DEBUG"

        # Production security hardening
        elif env == "production":
            config_data["debug_mode"] = False
            compliance_config = config_data.setdefault("compliance", {})
            if isinstance(compliance_config, dict):
                compliance_config["require_mfa"] = True
            database_config = config_data.setdefault("database", {})
            if isinstance(database_config, dict):
                database_config["enable_ssl"] = True
            monitoring_config = config_data.setdefault("monitoring", {})
            if isinstance(monitoring_config, dict):
                monitoring_config["log_level"] = "WARNING"

        # Create configuration object
        self.config = HealthcareConfig(**config_data)

    def get_config(self) -> HealthcareConfig:
        """Get current healthcare configuration"""
        if self.config is None:
            self._load_config()
        if self.config is None:
            raise RuntimeError("Failed to load healthcare configuration")
        return self.config

    def reload_config(self) -> None:
        """Reload configuration from file"""
        self._load_config()

    def get_model_config(self) -> ModelConfig:
        """Get AI model configuration"""
        return self.get_config().model

    def get_compliance_config(self) -> HealthcareComplianceConfig:
        """Get healthcare compliance configuration"""
        return self.get_config().compliance

    def get_cache_config(self) -> CacheConfig:
        """Get caching configuration"""
        return self.get_config().cache

    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration"""
        return self.get_config().database

    def get_monitoring_config(self) -> MonitoringConfig:
        """Get monitoring configuration"""
        return self.get_config().monitoring


# Global configuration manager instance
_config_manager: HealthcareConfigManager | None = None


def get_healthcare_config() -> HealthcareConfig:
    """Get global healthcare configuration"""
    global _config_manager
    if _config_manager is None:
        _config_manager = HealthcareConfigManager()
    return _config_manager.get_config()


def get_model_config() -> ModelConfig:
    """Get AI model configuration"""
    return get_healthcare_config().model


def get_compliance_config() -> HealthcareComplianceConfig:
    """Get healthcare compliance configuration"""
    return get_healthcare_config().compliance


def get_cache_config() -> CacheConfig:
    """Get caching configuration"""
    return get_healthcare_config().cache


def get_database_config() -> DatabaseConfig:
    """Get database configuration"""
    return get_healthcare_config().database


def get_monitoring_config() -> MonitoringConfig:
    """Get monitoring configuration"""
    return get_healthcare_config().monitoring
