"""
Healthcare Dependency Injection
Provides MCP clients, LLM clients, and other healthcare services
"""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from core.config.models import MODEL_CONFIG

import asyncpg
from fastapi import Depends

logger = logging.getLogger(__name__)


class DatabaseConnectionError(Exception):
    """Raised when database connection is unavailable for healthcare operations"""



class HealthcareServices:
    """Singleton service container for healthcare AI services"""

    _instance: "HealthcareServices | None" = None
    _mcp_client: Any = None
    _llm_client: Any = None
    _db_pool: Any = None
    _redis_client: Any = None
    _initialized: bool = False

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
            self._initialized = True

        except Exception as e:
            logger.exception(f"Failed to initialize healthcare services: {e}")
            raise

    async def _initialize_mcp_client(self) -> None:
        """Initialize MCP client for healthcare tools (lazy connection)"""
        try:
            from core.mcp.healthcare_mcp_client import HealthcareMCPClient

            # Initialize stdio-based MCP client but don't connect yet (lazy connection)
            # Connection will happen on first use to avoid blocking startup
            self._mcp_client = HealthcareMCPClient()
            logger.info("MCP client initialized (lazy connection - will connect on first use)")

        except ImportError:
            # Fallback mock for development
            logger.warning("MCP client not available, using mock")
            self._mcp_client = self._create_mock_mcp_client()
        except Exception as e:
            logger.error(f"Failed to initialize MCP client: {e}")
            # Use mock client as fallback
            logger.warning("Using mock MCP client as fallback")
            self._mcp_client = self._create_mock_mcp_client()

    async def _initialize_llm_client(self) -> None:
        """LLM communication handled via MCP stdio protocol - no direct HTTP client needed"""
        # For stdio MCP mode, we don't initialize HTTP ollama client
        # All LLM requests go through MCP stdio protocol
        self._llm_client = None
        logger.info("LLM communication will use MCP stdio protocol")

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
            logger.exception(f"CRITICAL: Database pool initialization failed: {e}")
            raise DatabaseConnectionError(
                "Healthcare database unavailable. Please check connection. "
                "Run 'make setup' to initialize database or verify DATABASE_URL environment variable.",
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
        """Create simplified mock MCP client for development"""

        class SimplifiedMockMCPClient:
            """Simplified mock that implements expected interface without breaking"""
            
            async def call_healthcare_tool(
                self, tool_name: str, params: dict[str, Any],
            ) -> dict[str, Any]:
                """Mock healthcare tool call"""
                if tool_name == "search-pubmed":
                    return {
                        "tool": tool_name,
                        "params": params,
                        "articles": [
                            {
                                "title": f"Mock PubMed article for: {params.get('query', 'N/A')}",
                                "abstract": "This is a mock response for development purposes.",
                                "authors": ["Mock Author"],
                                "journal": "Mock Journal",
                                "year": "2024"
                            }
                        ],
                        "mock": True,
                    }
                elif tool_name == "search-trials":
                    return {
                        "tool": tool_name,
                        "params": params,
                        "trials": [
                            {
                                "title": f"Mock clinical trial for: {params.get('condition', 'N/A')}",
                                "status": "Recruiting",
                                "phase": "Phase II",
                                "location": "Mock Medical Center"
                            }
                        ],
                        "mock": True,
                    }
                else:
                    return {
                        "tool": tool_name,
                        "params": params,
                        "result": f"Mock response for {tool_name}",
                        "mock": True,
                    }

            # Add any other methods the real client might have
            async def list_tools(self) -> list[str]:
                return ["search-pubmed", "search-trials", "get-drug-info", "echo_test"]

        return SimplifiedMockMCPClient()

    def _create_mock_llm_client(self) -> Any:
        """Mock LLM client removed - stdio MCP only"""
        return None

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
            "Run 'make setup' to initialize database or verify DATABASE_URL environment variable.",
        )
    return healthcare_services.db_pool


async def get_database_connection() -> Any:
    """Get database connection - required for healthcare operations"""
    if healthcare_services.db_pool is None:
        raise DatabaseConnectionError(
            "Healthcare database unavailable. Please check connection. "
            "Run 'make setup' to initialize database or verify DATABASE_URL environment variable.",
        )

    # Return a connection from the pool
    return await healthcare_services.db_pool.acquire()


@asynccontextmanager
async def get_database_connection_context() -> AsyncGenerator[asyncpg.Connection, None]:
    """Get database connection with automatic release"""
    if healthcare_services.db_pool is None:
        raise DatabaseConnectionError(
            "Healthcare database unavailable. Please check connection. "
            "Run 'make setup' to initialize database or verify DATABASE_URL environment variable.",
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
