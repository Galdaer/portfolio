"""
Intelluxe AI Configuration Management

Centralized configuration for the healthcare AI system.
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class IntelluxeConfig(BaseSettings):
    """Main configuration class for Intelluxe AI"""

    # Core application settings
    project_name: str = Field(default="intelluxe-ai", json_schema_extra={"env": "PROJECT_NAME"})
    version: str = "1.0.0"
    environment: str = Field(default="development", json_schema_extra={"env": "ENVIRONMENT"})
    development_mode: bool = Field(default=True, json_schema_extra={"env": "DEVELOPMENT_MODE"})
    debug_enabled: bool = Field(default=False, json_schema_extra={"env": "DEBUG_ENABLED"})

    # Server configuration
    host: str = Field(default="0.0.0.0", json_schema_extra={"env": "HOST"})
    port: int = Field(default=8000, json_schema_extra={"env": "PORT"})
    log_level: str = Field(default="info", json_schema_extra={"env": "LOG_LEVEL"})

    # Database configuration
    database_name: str = Field(default="intelluxe", json_schema_extra={"env": "DATABASE_NAME"})
    database_url: str | None = Field(default=None, json_schema_extra={"env": "DATABASE_URL"})
    postgres_password: str = Field(
        default="secure_password",
        json_schema_extra={"env": "POSTGRES_PASSWORD"},
    )
    redis_password: str | None = Field(default=None, json_schema_extra={"env": "REDIS_PASSWORD"})

    # Database host configuration (fallback if DATABASE_URL not provided)
    postgres_host: str = Field(default="172.20.0.13", json_schema_extra={"env": "POSTGRES_HOST"})
    redis_host: str = Field(default="172.20.0.14", json_schema_extra={"env": "REDIS_HOST"})

    # Database URLs
    @property
    def postgres_url(self) -> str:
        # Use DATABASE_URL from .env if provided, otherwise build from components
        if self.database_url:
            return self.database_url
        return f"postgresql://intelluxe:{self.postgres_password}@{self.postgres_host}:5432/{self.database_name}"

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:6379"
        return f"redis://{self.redis_host}:6379"

    def get_model_for_task(self, task_type: str = "default") -> str:
        """Get appropriate model for a specific task type - delegates to MODEL_CONFIG"""
        from core.config.models import MODEL_CONFIG

        return MODEL_CONFIG.get_model_for_task(task_type)

    # AI Model configuration
    ollama_url: str = Field(default="intelluxe-ai", json_schema_extra={"env": "OLLAMA_URL"})
    ollama_max_loaded_models: int = Field(
        default=3,
        json_schema_extra={"env": "OLLAMA_MAX_LOADED_MODELS"},
    )
    ollama_keep_alive: str = Field(default="24h", json_schema_extra={"env": "OLLAMA_KEEP_ALIVE"})

    # MCP configuration
    mcp_server_url: str = Field(
        default="http://healthcare-mcp:3000",
        json_schema_extra={"env": "MCP_SERVER_URL"},
    )

    # Training configuration (Phase 2+)
    unsloth_training_enabled: bool = Field(
        default=False,
        json_schema_extra={"env": "UNSLOTH_TRAINING_ENABLED"},
    )
    training_data_path: str = Field(
        default="/app/data/training",
        json_schema_extra={"env": "TRAINING_DATA_PATH"},
    )
    adapter_registry_path: str = Field(
        default="/app/models/adapters",
        json_schema_extra={"env": "ADAPTER_REGISTRY_PATH"},
    )
    wandb_project: str = Field(
        default="intelluxe-training",
        json_schema_extra={"env": "WANDB_PROJECT"},
    )

    # Performance configuration
    gpu_memory_fraction: float = Field(
        default=0.8,
        json_schema_extra={"env": "GPU_MEMORY_FRACTION"},
    )

    # Compliance and security
    data_retention_days: int = Field(
        default=2555,
        json_schema_extra={"env": "DATA_RETENTION_DAYS"},
    )  # 7 years
    audit_log_level: str = Field(default="detailed", json_schema_extra={"env": "AUDIT_LOG_LEVEL"})
    pii_redaction_enabled: bool = Field(
        default=True,
        json_schema_extra={"env": "PII_REDACTION_ENABLED"},
    )
    rbac_enabled: bool = Field(default=True, json_schema_extra={"env": "RBAC_ENABLED"})

    # Health monitoring
    health_check_interval: str = Field(
        default="60s",
        json_schema_extra={"env": "HEALTH_CHECK_INTERVAL"},
    )
    health_alert_webhook: str | None = Field(
        default=None,
        json_schema_extra={"env": "HEALTH_ALERT_WEBHOOK"},
    )
    health_page_public: bool = Field(default=False, json_schema_extra={"env": "HEALTH_PAGE_PUBLIC"})

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
        "env_prefix": "",
        "env_ignore_empty": False,
        "env_nested_delimiter": "__",
        "env_nested_max_split": 1,
        "nested_model_default_partial_update": False,
    }


# Global configuration instance
config = IntelluxeConfig()
