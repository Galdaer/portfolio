"""
Healthcare System Health Monitoring
Provides comprehensive health checks for all healthcare AI components
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class HealthcareSystemMonitor:
    """
    Comprehensive health monitoring for healthcare AI system

    Monitors:
    - Database connectivity (PostgreSQL)
    - Cache system (Redis)
    - MCP server connectivity
    - LLM availability (Ollama)
    - Background task system
    - Memory usage and performance
    - Healthcare-specific service status

    Features:
    - Async health checks with timeouts
    - Detailed status reporting
    - Performance metrics
    - Healthcare compliance monitoring
    """

    def __init__(self) -> None:
        self.health_check_timeout = 5.0  # seconds
        self.last_check_time: float = 0.0
        self.cached_status: dict[str, Any] = {}

    async def comprehensive_health_check(self) -> dict[str, Any]:
        """
        Perform comprehensive health check of all healthcare AI components

        Returns:
            Detailed health status report
        """
        start_time = time.time()

        # Run all health checks concurrently
        health_tasks = [
            self._check_database_health(),
            self._check_redis_health(),
            self._check_mcp_health(),
            self._check_llm_health(),
            self._check_background_tasks_health(),
            self._check_memory_usage(),
            self._check_cache_performance(),
        ]

        try:
            results = await asyncio.gather(*health_tasks, return_exceptions=True)

            # Process results
            health_status: dict[str, Any] = {
                "overall_status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "check_duration_ms": round((time.time() - start_time) * 1000, 2),
                "components": {
                    "database": results[0]
                    if not isinstance(results[0], Exception)
                    else {"status": "error", "error": str(results[0])},
                    "cache": results[1]
                    if not isinstance(results[1], Exception)
                    else {"status": "error", "error": str(results[1])},
                    "mcp_server": results[2]
                    if not isinstance(results[2], Exception)
                    else {"status": "error", "error": str(results[2])},
                    "llm": results[3]
                    if not isinstance(results[3], Exception)
                    else {"status": "error", "error": str(results[3])},
                    "background_tasks": results[4]
                    if not isinstance(results[4], Exception)
                    else {"status": "error", "error": str(results[4])},
                    "memory": results[5]
                    if not isinstance(results[5], Exception)
                    else {"status": "error", "error": str(results[5])},
                    "cache_performance": results[6]
                    if not isinstance(results[6], Exception)
                    else {"status": "error", "error": str(results[6])},
                },
            }

            # Determine overall status
            component_statuses = []
            components_dict = health_status.get("components", {})
            if isinstance(components_dict, dict):
                for comp in components_dict.values():
                    if isinstance(comp, dict):
                        component_statuses.append(comp.get("status", "unknown"))
                    else:
                        component_statuses.append("unknown")
            if "critical" in component_statuses:
                health_status["overall_status"] = "critical"
            elif "degraded" in component_statuses:
                health_status["overall_status"] = "degraded"
            elif "error" in component_statuses:
                health_status["overall_status"] = "error"

            # Cache successful results
            self.last_check_time = time.time()
            self.cached_status = health_status

            return health_status

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "overall_status": "critical",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "check_duration_ms": round((time.time() - start_time) * 1000, 2),
            }

    async def _check_database_health(self) -> dict[str, Any]:
        """Check PostgreSQL database health"""
        try:
            from core.dependencies import healthcare_services

            db_pool = healthcare_services.db_pool

            if not db_pool:
                return {
                    "status": "degraded",
                    "message": "Database pool not initialized",
                    "available_connections": 0,
                }

            start_time = time.time()

            # Test connection with simple query
            async with db_pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                if result != 1:
                    raise Exception("Database query returned unexpected result")

            query_time = round((time.time() - start_time) * 1000, 2)

            # Get pool stats
            pool_stats = {
                "size": db_pool.get_size(),
                "min_size": db_pool.get_min_size(),
                "max_size": db_pool.get_max_size(),
                "idle_connections": db_pool.get_idle_size(),
            }

            return {
                "status": "healthy",
                "query_time_ms": query_time,
                "pool_stats": pool_stats,
                "message": "Database connection successful",
            }

        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            return {"status": "critical", "error": str(e), "message": "Database connection failed"}

    async def _check_redis_health(self) -> dict[str, Any]:
        """Check Redis cache health"""
        try:
            from core.dependencies import healthcare_services

            redis_client = healthcare_services.redis_client

            if not redis_client:
                return {"status": "degraded", "message": "Redis client not initialized"}

            start_time = time.time()

            # Test Redis with ping
            pong = await redis_client.ping()
            if not pong:
                raise Exception("Redis ping failed")

            ping_time = round((time.time() - start_time) * 1000, 2)

            # Get Redis info
            info = await redis_client.info()

            return {
                "status": "healthy",
                "ping_time_ms": ping_time,
                "memory_used": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "message": "Redis connection successful",
            }

        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            return {"status": "critical", "error": str(e), "message": "Redis connection failed"}

    async def _check_mcp_health(self) -> dict[str, Any]:
        """Check MCP server health"""
        try:
            from core.dependencies import healthcare_services

            mcp_client = healthcare_services.mcp_client

            if not mcp_client:
                return {"status": "degraded", "message": "MCP client not initialized"}

            # Check if it's our mock client
            if hasattr(mcp_client, "call_healthcare_tool"):
                start_time = time.time()

                # Test with simple healthcare tool call
                result = await mcp_client.call_healthcare_tool("health_check", {})

                response_time = round((time.time() - start_time) * 1000, 2)

                if result.get("mock"):
                    return {
                        "status": "degraded",
                        "message": "Using mock MCP client - real MCP server not connected",
                        "response_time_ms": response_time,
                        "mock_client": True,
                    }
                else:
                    return {
                        "status": "healthy",
                        "message": "MCP server connection successful",
                        "response_time_ms": response_time,
                        "mock_client": False,
                    }
            else:
                return {"status": "error", "message": "MCP client missing expected interface"}

        except Exception as e:
            logger.warning(f"MCP health check failed: {e}")
            return {
                "status": "critical",
                "error": str(e),
                "message": "MCP server connection failed",
            }

    async def _check_llm_health(self) -> dict[str, Any]:
        """Check LLM (Ollama) health"""
        try:
            from core.dependencies import healthcare_services

            llm_client = healthcare_services.llm_client

            if not llm_client:
                return {"status": "degraded", "message": "LLM client not initialized"}

            start_time = time.time()

            # Test with simple generation
            if hasattr(llm_client, "generate"):
                result = await llm_client.generate(
                    model="llama3.1",
                    prompt="Health check test",
                )

                response_time = round((time.time() - start_time) * 1000, 2)

                if result.get("mock"):
                    return {
                        "status": "degraded",
                        "message": "Using mock LLM client - Ollama not connected",
                        "response_time_ms": response_time,
                        "mock_client": True,
                    }
                else:
                    return {
                        "status": "healthy",
                        "message": "LLM connection successful",
                        "response_time_ms": response_time,
                        "mock_client": False,
                    }
            else:
                return {"status": "error", "message": "LLM client missing expected interface"}

        except Exception as e:
            logger.warning(f"LLM health check failed: {e}")
            return {"status": "critical", "error": str(e), "message": "LLM connection failed"}

    async def _check_background_tasks_health(self) -> dict[str, Any]:
        """Check background task system health"""
        try:
            from core.infrastructure.background_tasks import HealthcareTaskManager

            task_manager = HealthcareTaskManager()
            active_tasks = len(task_manager.active_tasks)

            return {
                "status": "healthy",
                "active_tasks": active_tasks,
                "message": f"Background task system operational with {active_tasks} active tasks",
            }

        except Exception as e:
            logger.warning(f"Background tasks health check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": "Background task system check failed",
            }

    async def _check_memory_usage(self) -> dict[str, Any]:
        """Check system memory usage"""
        try:
            import psutil

            memory = psutil.virtual_memory()

            status = "healthy"
            if memory.percent > 90:
                status = "critical"
            elif memory.percent > 80:
                status = "degraded"

            return {
                "status": status,
                "memory_percent": memory.percent,
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "memory_used_gb": round(memory.used / (1024**3), 2),
                "message": f"Memory usage: {memory.percent:.1f}%",
            }

        except ImportError:
            return {"status": "degraded", "message": "psutil not available for memory monitoring"}
        except Exception as e:
            logger.warning(f"Memory health check failed: {e}")
            return {"status": "error", "error": str(e), "message": "Memory check failed"}

    async def _check_cache_performance(self) -> dict[str, Any]:
        """Check cache system performance"""
        try:
            from core.infrastructure.caching import healthcare_cache

            cache_stats = await healthcare_cache.get_cache_stats()

            if cache_stats.get("status") == "redis_unavailable":
                return {"status": "degraded", "message": "Cache system unavailable"}
            elif cache_stats.get("status") == "error":
                return {
                    "status": "error",
                    "error": cache_stats.get("error"),
                    "message": "Cache performance check failed",
                }
            else:
                total_keys = cache_stats.get("total_keys", 0)
                return {
                    "status": "healthy",
                    "total_cache_keys": total_keys,
                    "cache_entry_counts": cache_stats.get("cache_entry_counts", {}),
                    "redis_memory": cache_stats.get("redis_memory_used", "unknown"),
                    "message": f"Cache system healthy with {total_keys} entries",
                }

        except Exception as e:
            logger.warning(f"Cache performance check failed: {e}")
            return {"status": "error", "error": str(e), "message": "Cache performance check failed"}

    async def quick_health_check(self) -> dict[str, Any]:
        """
        Quick health check (cached results if recent)

        Returns:
            Basic health status
        """
        # Return cached results if recent (within 30 seconds)
        if (time.time() - self.last_check_time) < 30 and self.cached_status:
            return {
                **self.cached_status,
                "cached": True,
                "cache_age_seconds": round(time.time() - self.last_check_time, 1),
            }

        # Perform quick checks only
        try:
            quick_tasks = [
                self._check_database_health(),
                self._check_redis_health(),
            ]

            results = await asyncio.wait_for(
                asyncio.gather(*quick_tasks, return_exceptions=True),
                timeout=self.health_check_timeout,
            )

            db_status = results[0] if not isinstance(results[0], Exception) else {"status": "error"}
            redis_status = (
                results[1] if not isinstance(results[1], Exception) else {"status": "error"}
            )

            overall = "healthy"
            if (isinstance(db_status, dict) and db_status.get("status") == "critical") or (
                isinstance(redis_status, dict) and redis_status.get("status") == "critical"
            ):
                overall = "critical"
            elif (
                isinstance(db_status, dict) and db_status.get("status") in ["degraded", "error"]
            ) or (
                isinstance(redis_status, dict)
                and redis_status.get("status") in ["degraded", "error"]
            ):
                overall = "degraded"

            return {
                "overall_status": overall,
                "timestamp": datetime.utcnow().isoformat(),
                "quick_check": True,
                "database": db_status.get("status") if isinstance(db_status, dict) else "error",
                "cache": redis_status.get("status") if isinstance(redis_status, dict) else "error",
            }

        except TimeoutError:
            return {
                "overall_status": "critical",
                "timestamp": datetime.utcnow().isoformat(),
                "error": "Health check timeout",
                "quick_check": True,
            }
        except Exception as e:
            return {
                "overall_status": "critical",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "quick_check": True,
            }


# Global health monitor instance
healthcare_monitor = HealthcareSystemMonitor()
