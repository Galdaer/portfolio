"""
Database Connection Factory
Provides testable database connection management with dependency injection
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Protocol, cast

import psycopg2

from src.security.environment_detector import EnvironmentDetector

logger = logging.getLogger(__name__)


class DatabaseConnection(Protocol):
    """Database connection protocol for type safety"""

    @abstractmethod
    def cursor(self, cursor_factory: Any | None = None) -> psycopg2.extensions.cursor:
        """Return a database cursor"""
        ...

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        pass

    @property
    def closed(self) -> int:
        """Return 0 if connection is open, nonzero if closed (abstract)"""
        raise NotImplementedError("Subclasses must implement 'closed' property")


class ConnectionFactory(ABC):
    """Abstract connection factory for dependency injection"""

    @abstractmethod
    def create_connection(self) -> DatabaseConnection:
        """Create database connection"""

    @abstractmethod
    def get_connection_info(self) -> dict:
        """Get connection information for logging/debugging"""


class PostgresConnectionFactory(ConnectionFactory):
    """PostgreSQL connection factory with environment-aware configuration"""

    def __init__(self, connection_string: str | None = None, **kwargs: Any) -> None:
        """
        Initialize PostgreSQL connection factory

        Args:
            connection_string: Full PostgreSQL connection string
            **kwargs: Individual connection parameters (host, port, database, etc.)
        """
        self.connection_string = connection_string
        self.connection_params = kwargs
        self.logger = logging.getLogger(f"{__name__}.PostgresConnectionFactory")

        # Validate configuration based on environment
        self._validate_configuration()

    def _validate_configuration(self) -> None:
        """Validate connection configuration based on environment"""
        if EnvironmentDetector.is_production():
            # Production requires secure connection parameters
            if not self.connection_string and not self.connection_params:
                raise RuntimeError("Database connection parameters required in production")

            # Check for secure connection requirements
            if self.connection_string:
                if "sslmode=require" not in self.connection_string.lower():
                    self.logger.warning(
                        "SSL not explicitly required in production connection string",
                    )
            elif self.connection_params:
                if self.connection_params.get("sslmode") != "require":
                    self.logger.warning(
                        "SSL not explicitly required in production connection params",
                    )

    def create_connection(self) -> DatabaseConnection:
        """Create PostgreSQL database connection"""
        try:
            if self.connection_string:
                connection = psycopg2.connect(self.connection_string)
            else:
                params = self._get_secure_connection_params()
                connection = psycopg2.connect(**params)

            # Set connection properties based on environment
            connection.autocommit = False

            self.logger.info("Database connection established successfully")
            return cast("DatabaseConnection", connection)

        except psycopg2.Error as e:
            self.logger.exception(f"Failed to create database connection: {e}")
            msg = f"Database connection failed: {e}"
            raise RuntimeError(msg)

    def _get_secure_connection_params(self) -> dict:
        """Get secure connection parameters with environment-specific defaults"""
        # Base parameters with secure defaults
        params = {
            "host": self.connection_params.get("host", "localhost"),
            "port": self.connection_params.get("port", 5432),
            "database": self.connection_params.get("database", "intelluxe"),
            "user": self.connection_params.get("user"),
            "password": self.connection_params.get("password"),
            "connect_timeout": self.connection_params.get("connect_timeout", 10),
            "application_name": "intelluxe-healthcare",
        }

        # Environment-specific security settings
        if EnvironmentDetector.is_production():
            params.update(
                {
                    "sslmode": self.connection_params.get("sslmode", "require"),
                    "sslcert": self.connection_params.get("sslcert"),
                    "sslkey": self.connection_params.get("sslkey"),
                    "sslrootcert": self.connection_params.get("sslrootcert"),
                },
            )
        elif EnvironmentDetector.is_development():
            params.update({"sslmode": self.connection_params.get("sslmode", "prefer")})

        # Remove None values
        return {k: v for k, v in params.items() if v is not None}

    def get_connection_info(self) -> dict:
        """Get connection information for logging/debugging"""
        if self.connection_string:
            # Parse connection string for safe logging (remove password)
            safe_string = self.connection_string
            if "password=" in safe_string.lower():
                import re

                safe_string = re.sub(
                    r'(?i)(password\s*=\s*)(["\']?)(.*?)(\2)(?=;|&|\s|$)',
                    r"\1\2***\2",
                    safe_string,
                )
            return {"connection_string": safe_string}
        safe_params = self.connection_params.copy()
        if "password" in safe_params:
            safe_params["password"] = "***"
        return {"connection_params": safe_params}


class MockConnectionFactory(ConnectionFactory):
    """Mock connection factory for testing"""

    def __init__(self, mock_connection: Any | None = None) -> None:
        self.mock_connection = mock_connection
        self.logger = logging.getLogger(f"{__name__}.MockConnectionFactory")

    def create_connection(self) -> DatabaseConnection:
        """Return mock connection for testing"""
        if self.mock_connection:
            return cast("DatabaseConnection", self.mock_connection)

        # Create a simple mock connection
        from unittest.mock import Mock

        mock_conn = Mock()
        mock_conn.cursor.return_value.__enter__.return_value = Mock()
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_conn.closed = 0
        return cast("DatabaseConnection", mock_conn)

    def get_connection_info(self) -> dict:
        """Get mock connection info"""
        return {"type": "mock", "connection": "test"}


class ConnectionManager:
    """Manages database connections with proper lifecycle"""

    def __init__(self, connection_factory: ConnectionFactory):
        self.connection_factory = connection_factory
        self._connection: DatabaseConnection | None = None
        self.logger = logging.getLogger(f"{__name__}.ConnectionManager")

    @property
    def connection(self) -> DatabaseConnection:
        """Get database connection (lazy loading with health check)"""
        if self._connection is None or self._is_connection_closed():
            self._connection = self.connection_factory.create_connection()
        return self._connection

    def _is_connection_closed(self) -> bool:
        """Check if connection is closed"""
        if self._connection is None:
            return True
        try:
            return self._connection.closed != 0
        except Exception:
            return True

    def close(self) -> None:
        """Close database connection"""
        if self._connection and not self._is_connection_closed():
            try:
                self._connection.close()
                self.logger.info("Database connection closed")
            except Exception as e:
                self.logger.warning(f"Error closing database connection: {e}")
            finally:
                self._connection = None

    def __enter__(self) -> "ConnectionManager":
        """Context manager entry"""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit"""
        self.close()
