"""
Memory Management for Intelluxe AI

Provides unified interface for Redis (session cache) and PostgreSQL (persistence)
with healthcare-specific memory patterns.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid

import redis.asyncio as redis
import asyncpg
from config.app import config

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Unified memory management for healthcare AI agents

    Uses Redis for fast session storage and PostgreSQL for persistent context.
    Implements healthcare-specific memory patterns with audit logging.
    """

    def __init__(self) -> None:
        self.redis_client: Optional[redis.Redis] = None
        self.postgres_pool: Optional[asyncpg.Pool] = None
        self._initialized: bool = False

    async def initialize(self) -> None:
        """Initialize Redis and PostgreSQL connections"""
        try:
            # Initialize Redis connection
            self.redis_client = redis.from_url(
                config.redis_url,
                encoding="utf-8",
                decode_responses=True
            )

            # Test Redis connection
            await self.redis_client.ping()
            logger.info("Redis connection established")

            # Initialize PostgreSQL connection pool
            self.postgres_pool = await asyncpg.create_pool(
                config.postgres_url,
                min_size=2,
                max_size=10
            )

            logger.info("PostgreSQL connection pool established")
            self._initialized = True

        except Exception as e:
            logger.error(f"Failed to initialize memory manager: {e}")
            raise

    async def close(self) -> None:
        """Close all connections"""
        if self.redis_client:
            await self.redis_client.close()

        if self.postgres_pool:
            await self.postgres_pool.close()

        self._initialized = False
        logger.info("Memory manager connections closed")

    async def health_check(self) -> Dict[str, Any]:
        """Check health of memory systems"""
        if not self._initialized:
            return {"status": "not_initialized"}

        try:
            # Test Redis
            redis_latency = await self._test_redis_latency()

            # Test PostgreSQL
            postgres_latency = await self._test_postgres_latency()

            return {
                "status": "healthy",
                "redis": {
                    "connected": True,
                    "latency_ms": redis_latency
                },
                "postgres": {
                    "connected": True,
                    "latency_ms": postgres_latency
                }
            }

        except Exception as e:
            logger.error(f"Memory health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    async def _test_redis_latency(self) -> float:
        """Test Redis latency"""
        if self.redis_client is None:
            raise RuntimeError("Redis client not initialized")
        start_time = asyncio.get_event_loop().time()
        await self.redis_client.ping()
        return (asyncio.get_event_loop().time() - start_time) * 1000

    async def _test_postgres_latency(self) -> float:
        """Test PostgreSQL latency"""
        start_time = asyncio.get_event_loop().time()
        if self.postgres_pool is None:
            raise RuntimeError("Persistent storage is not available")
        async with self.postgres_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return (asyncio.get_event_loop().time() - start_time) * 1000

    # Session management methods (Redis-based)
    async def store_session(self, session_id: str, data: Dict[str, Any], ttl: int = 3600) -> None:
        """Store session data in Redis with TTL"""
        if not self._initialized:
            raise RuntimeError("Memory manager not initialized")
        if self.redis_client is None:
            raise RuntimeError("Redis client not initialized")

        await self.redis_client.setex(
            f"session:{session_id}",
            ttl,
            json.dumps(data, default=str)
        )

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session data from Redis"""
        if not self._initialized:
            raise RuntimeError("Memory manager not initialized")
        if self.redis_client is None:
            raise RuntimeError("Redis client not initialized")

        data = await self.redis_client.get(f"session:{session_id}")
        return json.loads(data) if data else None

    # Persistent context management (PostgreSQL-based)
    async def store_context(self, user_id: str, context_type: str, data: Dict[str, Any]) -> str:
        """Store persistent context in PostgreSQL"""
        if not self._initialized:
            raise RuntimeError("Memory manager not initialized")

        context_id = str(uuid.uuid4())

        if self.postgres_pool is None:
            raise RuntimeError("Persistent storage is not available")
        async with self.postgres_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO conversation_context
                (context_id, user_id, context_type, data, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """,
                context_id,
                user_id,
                context_type,
                json.dumps(data),
                datetime.utcnow(),
                datetime.utcnow()
            )

        return context_id

    async def get_context(self, context_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve persistent context from PostgreSQL"""
        if not self._initialized:
            raise RuntimeError("Memory manager not initialized")
        if self.postgres_pool is None:
            raise RuntimeError("Persistent storage is not available")
        async with self.postgres_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT data FROM conversation_context
                WHERE context_id = $1
            """, context_id)

        return json.loads(row['data']) if row else None


# Global memory manager instance (initialized in main.py)
memory_manager = MemoryManager()
