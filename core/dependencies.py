"""
Healthcare Dependency Injection
Provides MCP clients, LLM clients, and other healthcare services
"""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import asyncpg
from fastapi import Depends

logger = logging.getLogger(__name__)


class DatabaseConnectionError(Exception):
    """Raised when database connection is unavailable for healthcare operations"""

    pass


class HealthcareServices:
    """Singleton service container for healthcare AI services"""

    _instance: "HealthcareServices | None" = None
    _mcp_client: Any = None
    _llm_client: Any = None
    _db_pool: Any = None
    _redis_client: Any = None

    def __new__(cls) -> "HealthcareServices":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def initialize(self) -> None:
        """Initialize all healthcare services"""
        logger.info("Initializing healthcare services...")

        try:
            # Initialize MCP client
            await self._initialize_mcp_client()

            # Initialize LLM client
            await self._initialize_llm_client()

            # Initialize database pool
            await self._initialize_database_pool()

            # Initialize Redis client
            await self._initialize_redis_client()

            logger.info("Healthcare services initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize healthcare services: {e}")
            raise

    async def _initialize_mcp_client(self) -> None:
        """Initialize MCP client for healthcare tools"""
        try:
            # TODO: Replace with actual MCP client implementation
            # For now, create a mock client that works with our agent code
            from core.mcp.healthcare_mcp_client import HealthcareMCPClient

            self._mcp_client = HealthcareMCPClient(
                server_url=os.getenv("HEALTHCARE_MCP_URL", "http://localhost:3001"),
                api_key=os.getenv("HEALTHCARE_MCP_KEY", "dev-key"),
            )
            await self._mcp_client.connect()
            logger.info("MCP client initialized")

        except ImportError:
            # Fallback mock for development
            logger.warning("MCP client not available, using mock")
            self._mcp_client = self._create_mock_mcp_client()

    async def _initialize_llm_client(self) -> None:
        """Initialize Ollama LLM client"""
        try:
            import ollama

            self._llm_client = ollama.AsyncClient(
                host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
                timeout=30.0,
            )

            # Test connection
            models = await self._llm_client.list()
            logger.info(f"Ollama client initialized with {len(models.get('models', []))} models")

        except ImportError:
            logger.warning("Ollama not available, using mock LLM client")
            self._llm_client = self._create_mock_llm_client()

    async def _initialize_database_pool(self) -> None:
        """Initialize PostgreSQL connection pool - REQUIRED for healthcare operations"""
        try:
            database_url = os.getenv(
                "DATABASE_URL",
                "postgresql://intelluxe:dev_password@localhost:5432/intelluxe",
            )

            self._db_pool = await asyncpg.create_pool(
                database_url,
                min_size=2,
                max_size=10,
                command_timeout=30,
            )

            # Test connection to ensure database is available
            async with self._db_pool.acquire() as connection:
                await connection.execute("SELECT 1")

            logger.info("Database pool initialized and validated")

        except Exception as e:
            logger.error(f"CRITICAL: Database pool initialization failed: {e}")
            raise DatabaseConnectionError(
                "Healthcare database unavailable. Please check connection. "
                "Run 'make setup' to initialize database or verify DATABASE_URL environment variable."
            ) from e

    async def _initialize_redis_client(self) -> None:
        """Initialize Redis client for caching"""
        try:
            import redis.asyncio as redis_async

            self._redis_client = redis_async.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                db=int(os.getenv("REDIS_DB", "0")),
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )

            await self._redis_client.ping()
            logger.info("Redis client initialized")

        except Exception as e:
            logger.warning(f"Redis initialization failed: {e}")
            self._redis_client = None

    def _create_mock_mcp_client(self) -> Any:
        """Create mock MCP client for development"""

        class MockMCPClient:
            async def call_healthcare_tool(
                self, tool_name: str, params: dict[str, Any]
            ) -> dict[str, Any]:
                return {
                    "tool": tool_name,
                    "params": params,
                    "result": "Mock healthcare tool response",
                    "mock": True,
                }

        return MockMCPClient()

    def _create_mock_llm_client(self) -> Any:
        """Create mock LLM client for development"""

        class MockLLMClient:
            async def generate(
                self, model: str = "llama3.1", prompt: str = "", **kwargs: Any
            ) -> dict[str, Any]:
                return {
                    "response": f"Mock LLM response for: {prompt[:50]}...",
                    "model": model,
                    "mock": True,
                }

        return MockLLMClient()

    @property
    def mcp_client(self) -> Any:
        return self._mcp_client

    @property
    def llm_client(self) -> Any:
        return self._llm_client

    @property
    def db_pool(self) -> Any:
        return self._db_pool

    @property
    def redis_client(self) -> Any:
        return self._redis_client

    async def close(self) -> None:
        """Clean up all services"""
        logger.info("Closing healthcare services...")

        if self._db_pool:
            await self._db_pool.close()

        if self._redis_client:
            await self._redis_client.close()

        logger.info("Healthcare services closed")


# Global service instance
healthcare_services = HealthcareServices()


# Dependency injection functions
async def get_mcp_client() -> Any:
    """Get MCP client for healthcare tools"""
    return healthcare_services.mcp_client


async def get_llm_client() -> Any:
    """Get LLM client for AI processing"""
    return healthcare_services.llm_client


async def get_db_pool() -> Any:
    """Get database connection pool"""
    if healthcare_services.db_pool is None:
        raise DatabaseConnectionError(
            "Healthcare database unavailable. Please check connection. "
            "Run 'make setup' to initialize database or verify DATABASE_URL environment variable."
        )
    return healthcare_services.db_pool


async def get_database_connection() -> Any:
    """Get database connection - required for healthcare operations"""
    if healthcare_services.db_pool is None:
        raise DatabaseConnectionError(
            "Healthcare database unavailable. Please check connection. "
            "Run 'make setup' to initialize database or verify DATABASE_URL environment variable."
        )

    # Return a connection from the pool
    return await healthcare_services.db_pool.acquire()


@asynccontextmanager
async def get_database_connection_context() -> AsyncGenerator[asyncpg.Connection, None]:
    """Get database connection with automatic release"""
    if healthcare_services.db_pool is None:
        raise DatabaseConnectionError(
            "Healthcare database unavailable. Please check connection. "
            "Run 'make setup' to initialize database or verify DATABASE_URL environment variable."
        )

    conn = await healthcare_services.db_pool.acquire()
    try:
        yield conn
    finally:
        await healthcare_services.db_pool.release(conn)


async def get_redis_client() -> Any:
    """Get Redis client for caching"""
    return healthcare_services.redis_client


# FastAPI dependency shortcuts
MCPClient = Depends(get_mcp_client)
LLMClient = Depends(get_llm_client)
DatabasePool = Depends(get_db_pool)
DatabaseConnection = Depends(get_database_connection)
RedisClient = Depends(get_redis_client)
