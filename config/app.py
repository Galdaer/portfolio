"""
Intelluxe AI Configuration Management

Centralized configuration for the healthcare AI system.
"""

import os
from typing import Optional
from pydantic import BaseSettings, Field


class IntelluxeConfig(BaseSettings):
    """Main configuration class for Intelluxe AI"""
    
    # Core application settings
    project_name: str = Field(default="intelluxe-ai", env="PROJECT_NAME")
    version: str = "1.0.0"
    environment: str = Field(default="development", env="ENVIRONMENT")
    development_mode: bool = Field(default=True, env="DEVELOPMENT_MODE")
    debug_enabled: bool = Field(default=False, env="DEBUG_ENABLED")
    
    # Server configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    log_level: str = Field(default="info", env="LOG_LEVEL")
    
    # Database configuration
    database_name: str = Field(default="intelluxe", env="DATABASE_NAME")
    postgres_password: str = Field(default="secure_password_here", env="POSTGRES_PASSWORD")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    
    # Database URLs
    @property
    def postgres_url(self) -> str:
        return f"postgresql://intelluxe:{self.postgres_password}@postgres:5432/{self.database_name}"
    
    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@redis:6379"
        return "redis://redis:6379"
    
    # AI Model configuration
    ollama_url: str = Field(default="http://ollama:11434", env="OLLAMA_URL")
    ollama_max_loaded_models: int = Field(default=3, env="OLLAMA_MAX_LOADED_MODELS")
    ollama_keep_alive: str = Field(default="24h", env="OLLAMA_KEEP_ALIVE")
    
    # MCP configuration
    mcp_server_url: str = Field(default="http://healthcare-mcp:3000", env="MCP_SERVER_URL")
    
    # Training configuration (Phase 2+)
    unsloth_training_enabled: bool = Field(default=False, env="UNSLOTH_TRAINING_ENABLED")
    training_data_path: str = Field(default="/app/data/training", env="TRAINING_DATA_PATH")
    adapter_registry_path: str = Field(default="/app/models/adapters", env="ADAPTER_REGISTRY_PATH")
    wandb_project: str = Field(default="intelluxe-training", env="WANDB_PROJECT")
    
    # Performance configuration
    gpu_memory_fraction: float = Field(default=0.8, env="GPU_MEMORY_FRACTION")
    
    # Compliance and security
    data_retention_days: int = Field(default=2555, env="DATA_RETENTION_DAYS")  # 7 years
    audit_log_level: str = Field(default="detailed", env="AUDIT_LOG_LEVEL")
    pii_redaction_enabled: bool = Field(default=True, env="PII_REDACTION_ENABLED")
    rbac_enabled: bool = Field(default=True, env="RBAC_ENABLED")
    
    # Health monitoring
    health_check_interval: str = Field(default="60s", env="HEALTH_CHECK_INTERVAL")
    health_alert_webhook: Optional[str] = Field(default=None, env="HEALTH_ALERT_WEBHOOK")
    health_page_public: bool = Field(default=False, env="HEALTH_PAGE_PUBLIC")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global configuration instance
config = IntelluxeConfig()
