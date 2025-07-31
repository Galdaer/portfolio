"""
Environment Detection Module for Intelluxe AI Healthcare System

Detects deployment environment and provides appropriate configuration
"""

import os
from enum import Enum
from typing import Any, Dict, Optional, Union


class EnvironmentType(Enum):
    """Supported deployment environments"""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class EnvironmentDetector:
    """
    Detects current deployment environment and provides environment-specific configuration

    Uses environment variables and system detection to determine deployment context
    """

    def __init__(self) -> None:
        self._environment: Optional[EnvironmentType] = None
        self._detected_settings: Dict[str, Any] = {}

    def detect_environment(self) -> EnvironmentType:
        """
        Detect current environment based on environment variables and system state

        Returns:
            EnvironmentType: Detected environment
        """
        if self._environment is not None:
            return self._environment

        # Check explicit environment variable
        env_var = os.getenv("ENVIRONMENT", "").lower()
        if env_var in [e.value for e in EnvironmentType]:
            self._environment = EnvironmentType(env_var)
            return self._environment

        # Check for CI environment
        if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
            self._environment = EnvironmentType.TESTING
            return self._environment

        # Check for production indicators
        if os.getenv("PRODUCTION") or os.path.exists("/etc/intelluxe/production.flag"):
            self._environment = EnvironmentType.PRODUCTION
            return self._environment

        # Default to development
        self._environment = EnvironmentType.DEVELOPMENT
        return self._environment

    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.detect_environment() == EnvironmentType.DEVELOPMENT

    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.detect_environment() == EnvironmentType.PRODUCTION

    def is_testing(self) -> bool:
        """Check if running in testing environment"""
        return self.detect_environment() == EnvironmentType.TESTING

    def get_environment_settings(self) -> Dict[str, Union[str, bool, int]]:
        """
        Get environment-specific settings

        Returns:
            Dict containing environment-appropriate configuration
        """
        env = self.detect_environment()

        base_settings: Dict[str, Union[str, bool, int]] = {
            "environment": env.value,
            "debug": env != EnvironmentType.PRODUCTION,
            "log_level": "DEBUG" if env == EnvironmentType.DEVELOPMENT else "INFO",
        }

        if env == EnvironmentType.DEVELOPMENT:
            base_settings.update(
                {
                    "database_pool_size": 5,
                    "enable_hot_reload": True,
                    "strict_ssl": False,
                    "enable_debug_endpoints": True,
                }
            )
        elif env == EnvironmentType.PRODUCTION:
            base_settings.update(
                {
                    "database_pool_size": 20,
                    "enable_hot_reload": False,
                    "strict_ssl": True,
                    "enable_debug_endpoints": False,
                    "security_headers": True,
                }
            )
        elif env == EnvironmentType.TESTING:
            base_settings.update(
                {
                    "database_pool_size": 2,
                    "enable_hot_reload": False,
                    "strict_ssl": False,
                    "enable_debug_endpoints": True,
                    "mock_external_services": True,
                }
            )

        return base_settings
