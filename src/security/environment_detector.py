"""
Secure Environment Detection
Provides robust environment detection with security-first approach
"""

import logging
import os
from enum import Enum

logger = logging.getLogger(__name__)


class Environment(Enum):
    """Supported environment types"""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class EnvironmentDetector:
    """Secure environment detection with validation"""

    @staticmethod
    def get_environment() -> Environment:
        """
        Get current environment with security-first validation

        Returns:
            Environment: The detected environment

        Raises:
            RuntimeError: If environment cannot be safely determined
        """
        env_var = os.getenv("ENVIRONMENT", "").strip().lower()

        # Security-first approach: require explicit environment setting
        if not env_var:
            logger.error("ENVIRONMENT variable is not set - this is required for security")
            raise RuntimeError(
                "ENVIRONMENT variable must be explicitly set. "
                "Valid values: development, testing, staging, production"
            )

        # Validate against known environments
        try:
            environment = Environment(env_var)
            logger.info(f"Environment detected: {environment.value}")
            return environment
        except ValueError:
            logger.error(f"Invalid ENVIRONMENT value: '{env_var}'")
            raise RuntimeError(
                f"Invalid ENVIRONMENT value: '{env_var}'. "
                f"Valid values: {', '.join([e.value for e in Environment])}"
            )

    @staticmethod
    def is_production() -> bool:
        """Check if running in production environment"""
        try:
            return EnvironmentDetector.get_environment() == Environment.PRODUCTION
        except RuntimeError as e:
            # If environment cannot be determined, assume production for security
            logger.error(
                "CRITICAL: Environment could not be determined. "
                f"Falling back to production mode as a secure default. Error: {e}"
            )
            # Also log to stderr for immediate visibility
            import sys

            print(
                "CRITICAL: Environment detection failed - assuming production mode for security",
                file=sys.stderr,
            )
            return True

    @staticmethod
    def is_development() -> bool:
        """Check if running in development environment"""
        try:
            return EnvironmentDetector.get_environment() == Environment.DEVELOPMENT
        except RuntimeError as e:
            # If environment cannot be determined, do not assume development
            logger.error(
                "Environment could not be determined. "
                f"NOT assuming development mode for security. Error: {e}"
            )
            return False

    @staticmethod
    def is_testing() -> bool:
        """Check if running in testing environment"""
        try:
            return EnvironmentDetector.get_environment() == Environment.TESTING
        except RuntimeError:
            return False

    @staticmethod
    def is_staging() -> bool:
        """Check if running in staging environment"""
        try:
            return EnvironmentDetector.get_environment() == Environment.STAGING
        except RuntimeError:
            return False

    @staticmethod
    def require_environment(required_env: Environment) -> None:
        """
        Require specific environment or raise error

        Args:
            required_env: The required environment

        Raises:
            RuntimeError: If not running in required environment
        """
        current_env = EnvironmentDetector.get_environment()
        if current_env != required_env:
            raise RuntimeError(
                f"This operation requires {required_env.value} environment, "
                f"but running in {current_env.value}"
            )

    @staticmethod
    def require_non_production() -> None:
        """
        Require non-production environment for dangerous operations

        Raises:
            RuntimeError: If running in production
        """
        if EnvironmentDetector.is_production():
            raise RuntimeError("This operation is not allowed in production environment")

    @staticmethod
    def get_environment_config() -> dict:
        """
        Get environment-specific configuration

        Returns:
            dict: Environment-specific settings
        """
        env = EnvironmentDetector.get_environment()

        config = {
            Environment.DEVELOPMENT: {
                "debug": True,
                "log_level": "DEBUG",
                "allow_key_generation": True,
                "strict_validation": False,
                "enable_test_endpoints": True,
            },
            Environment.TESTING: {
                "debug": True,
                "log_level": "INFO",
                "allow_key_generation": False,
                "strict_validation": True,
                "enable_test_endpoints": True,
            },
            Environment.STAGING: {
                "debug": False,
                "log_level": "INFO",
                "allow_key_generation": False,
                "strict_validation": True,
                "enable_test_endpoints": False,
            },
            Environment.PRODUCTION: {
                "debug": False,
                "log_level": "WARNING",
                "allow_key_generation": False,
                "strict_validation": True,
                "enable_test_endpoints": False,
            },
        }

        return config[env]
