"""
Healthcare-Specific Performance Caching
Optimized caching for medical literature, drug interactions, and clinical data
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import redis.asyncio as redis

from core.infrastructure.healthcare_logger import get_healthcare_logger

logger = get_healthcare_logger("healthcare_cache")


class CacheSecurityLevel(Enum):
    """Cache security levels for healthcare data"""

    PUBLIC = "public"  # Non-sensitive data
    HEALTHCARE_SENSITIVE = "healthcare"  # Healthcare data, no PHI
    PHI_PROTECTED = "phi_protected"  # May contain PHI - encrypted
    NO_CACHE = "no_cache"  # Never cache


@dataclass
class CacheEntry:
    """Healthcare cache entry with metadata"""

    key: str
    data: Any
    security_level: CacheSecurityLevel
    ttl_seconds: int
    created_at: datetime
    last_accessed: datetime
    access_count: int
    healthcare_context: dict[str, Any]
    phi_detected: bool = False
    encrypted: bool = False


class HealthcareCacheManager:
    """Healthcare-specific caching with PHI protection and compliance"""

    def __init__(self, redis_url: str = "redis://localhost:6379/1"):
        self.redis_url = redis_url
        self.redis_client: redis.Redis | None = None

        # Cache TTL configurations (in seconds)
        self.cache_ttls = {
            CacheSecurityLevel.PUBLIC: 3600 * 24,  # 24 hours
            CacheSecurityLevel.HEALTHCARE_SENSITIVE: 3600 * 4,  # 4 hours
            CacheSecurityLevel.PHI_PROTECTED: 3600,  # 1 hour
            CacheSecurityLevel.NO_CACHE: 0,  # Never cache
        }

        # Cache prefixes for organization
        self.cache_prefixes = {
            "medical_literature": "med_lit:",
            "drug_interactions": "drug_int:",
            "clinical_guidelines": "clin_guide:",
            "icd_codes": "icd:",
            "cpt_codes": "cpt:",
            "patient_data": "patient:",  # PHI protected
            "session_data": "session:",  # Temporary data
            "search_results": "search:",  # Research results
        }

        logger.info("Healthcare cache manager initialized")

    async def initialize(self) -> None:
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("Redis connection established for healthcare cache")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def _ensure_redis_client(self) -> redis.Redis:
        """Ensure Redis client is available and initialized"""
        if not self.redis_client:
            await self.initialize()
        assert self.redis_client is not None, "Redis client should be initialized"
        return self.redis_client

    async def get(
        self, cache_key: str, security_level: CacheSecurityLevel = CacheSecurityLevel.PUBLIC
    ) -> Any | None:
        """Get item from cache with security validation"""

        if security_level == CacheSecurityLevel.NO_CACHE:
            return None

        if not self.redis_client:
            await self.initialize()

        redis_client = await self._ensure_redis_client()

        try:
            # Get cache entry
            cached_data = await redis_client.get(cache_key)
            if not cached_data:
                return None

            # Deserialize
            cache_entry_data = json.loads(cached_data)
            cache_entry = CacheEntry(**cache_entry_data)

            # Validate security level
            if cache_entry.security_level != security_level:
                logger.warning(
                    f"Cache security level mismatch for key: {cache_key}",
                    extra={
                        "operation_type": "cache_security_mismatch",
                        "expected_level": security_level.value,
                        "actual_level": cache_entry.security_level.value,
                    },
                )
                return None

            # Update access metadata
            cache_entry.last_accessed = datetime.utcnow()
            cache_entry.access_count += 1

            # Update in cache
            redis_client = await self._ensure_redis_client()
            await redis_client.setex(
                cache_key,
                self.cache_ttls[security_level],
                json.dumps(asdict(cache_entry), default=str),
            )

            logger.debug(
                f"Cache hit for key: {cache_key}",
                extra={
                    "operation_type": "cache_hit",
                    "cache_key": cache_key,
                    "security_level": security_level.value,
                    "access_count": cache_entry.access_count,
                },
            )

            return cache_entry.data

        except Exception as e:
            logger.error(
                f"Cache get error for key {cache_key}: {e}",
                extra={
                    "operation_type": "cache_get_error",
                    "cache_key": cache_key,
                    "error": str(e),
                },
            )
            return None

    async def set(
        self,
        cache_key: str,
        data: Any,
        security_level: CacheSecurityLevel = CacheSecurityLevel.PUBLIC,
        ttl_override: int | None = None,
        healthcare_context: dict[str, Any] | None = None,
    ) -> bool:
        """Set item in cache with healthcare compliance"""

        if security_level == CacheSecurityLevel.NO_CACHE:
            return False

        if not self.redis_client:
            await self.initialize()

        try:
            # Validate data for PHI
            phi_detected = await self._detect_phi_in_data(data)

            if phi_detected and security_level not in [
                CacheSecurityLevel.PHI_PROTECTED,
                CacheSecurityLevel.NO_CACHE,
            ]:
                logger.error(
                    "PHI detected in data for non-PHI cache level",
                    extra={
                        "operation_type": "cache_phi_violation",
                        "cache_key": cache_key,
                        "security_level": security_level.value,
                    },
                )
                return False

            # Create cache entry
            cache_entry = CacheEntry(
                key=cache_key,
                data=data,
                security_level=security_level,
                ttl_seconds=ttl_override or self.cache_ttls[security_level],
                created_at=datetime.utcnow(),
                last_accessed=datetime.utcnow(),
                access_count=0,
                healthcare_context=healthcare_context or {},
                phi_detected=phi_detected,
                encrypted=False,  # Encryption would be implemented here if needed
            )

            # Set in Redis
            redis_client = await self._ensure_redis_client()
            await redis_client.setex(
                cache_key, cache_entry.ttl_seconds, json.dumps(asdict(cache_entry), default=str)
            )

            logger.debug(
                f"Cache set for key: {cache_key}",
                extra={
                    "operation_type": "cache_set",
                    "cache_key": cache_key,
                    "security_level": security_level.value,
                    "ttl_seconds": cache_entry.ttl_seconds,
                    "phi_detected": phi_detected,
                },
            )

            return True

        except Exception as e:
            logger.error(
                f"Cache set error for key {cache_key}: {e}",
                extra={
                    "operation_type": "cache_set_error",
                    "cache_key": cache_key,
                    "error": str(e),
                },
            )
            return False

    async def delete(self, cache_key: str) -> bool:
        """Delete item from cache"""

        if not self.redis_client:
            await self.initialize()

        if self.redis_client is None:
            raise RuntimeError("Redis client not available")

        try:
            result = await self.redis_client.delete(cache_key)

            logger.debug(
                f"Cache delete for key: {cache_key}",
                extra={
                    "operation_type": "cache_delete",
                    "cache_key": cache_key,
                    "deleted": bool(result),
                },
            )

            return bool(result)

        except Exception as e:
            logger.error(f"Cache delete error for key {cache_key}: {e}")
            return False

    async def get_medical_literature(
        self, query: str, max_results: int = 10
    ) -> list[dict[str, Any]] | None:
        """Get cached medical literature search results"""

        cache_key = self._generate_cache_key("medical_literature", query, max_results=max_results)

        return await self.get(cache_key, CacheSecurityLevel.PUBLIC)

    async def cache_medical_literature(
        self, query: str, results: list[dict[str, Any]], max_results: int = 10
    ) -> bool:
        """Cache medical literature search results"""

        cache_key = self._generate_cache_key("medical_literature", query, max_results=max_results)

        return await self.set(
            cache_key,
            results,
            CacheSecurityLevel.PUBLIC,
            healthcare_context={
                "query": query,
                "result_count": len(results),
                "cached_at": datetime.utcnow().isoformat(),
            },
        )

    async def get_drug_interactions(self, medications: list[str]) -> dict[str, Any] | None:
        """Get cached drug interaction data"""

        # Sort medications for consistent cache key
        sorted_meds = sorted(medications)
        cache_key = self._generate_cache_key("drug_interactions", json.dumps(sorted_meds))

        return await self.get(cache_key, CacheSecurityLevel.HEALTHCARE_SENSITIVE)

    async def cache_drug_interactions(
        self, medications: list[str], interactions: dict[str, Any]
    ) -> bool:
        """Cache drug interaction data"""

        sorted_meds = sorted(medications)
        cache_key = self._generate_cache_key("drug_interactions", json.dumps(sorted_meds))

        return await self.set(
            cache_key,
            interactions,
            CacheSecurityLevel.HEALTHCARE_SENSITIVE,
            ttl_override=3600 * 24 * 7,  # Cache for 1 week
            healthcare_context={
                "medications": sorted_meds,
                "interaction_count": len(interactions.get("interactions", [])),
            },
        )

    async def get_clinical_guidelines(
        self, condition: str, specialty: str | None = None
    ) -> dict[str, Any] | None:
        """Get cached clinical guidelines"""

        cache_key = self._generate_cache_key("clinical_guidelines", condition, specialty=specialty)

        return await self.get(cache_key, CacheSecurityLevel.HEALTHCARE_SENSITIVE)

    async def cache_clinical_guidelines(
        self, condition: str, guidelines: dict[str, Any], specialty: str | None = None
    ) -> bool:
        """Cache clinical guidelines"""

        cache_key = self._generate_cache_key("clinical_guidelines", condition, specialty=specialty)

        return await self.set(
            cache_key,
            guidelines,
            CacheSecurityLevel.HEALTHCARE_SENSITIVE,
            ttl_override=3600 * 24 * 30,  # Cache for 30 days
            healthcare_context={
                "condition": condition,
                "specialty": specialty,
                "guideline_count": len(guidelines.get("guidelines", [])),
            },
        )

    async def get_medical_codes(
        self, code_type: str, search_term: str
    ) -> list[dict[str, Any]] | None:
        """Get cached medical codes (ICD, CPT)"""

        cache_key = self._generate_cache_key(f"{code_type}_codes", search_term)

        return await self.get(cache_key, CacheSecurityLevel.PUBLIC)

    async def cache_medical_codes(
        self, code_type: str, search_term: str, codes: list[dict[str, Any]]
    ) -> bool:
        """Cache medical codes"""

        cache_key = self._generate_cache_key(f"{code_type}_codes", search_term)

        return await self.set(
            cache_key,
            codes,
            CacheSecurityLevel.PUBLIC,
            ttl_override=3600 * 24 * 90,  # Cache for 90 days (codes change infrequently)
            healthcare_context={
                "code_type": code_type,
                "search_term": search_term,
                "code_count": len(codes),
            },
        )

    async def get_session_data(self, session_id: str, data_key: str) -> Any | None:
        """Get cached session data"""

        cache_key = self._generate_cache_key("session_data", session_id, data_key=data_key)

        return await self.get(cache_key, CacheSecurityLevel.HEALTHCARE_SENSITIVE)

    async def cache_session_data(
        self, session_id: str, data_key: str, data: Any, ttl_minutes: int = 30
    ) -> bool:
        """Cache session data with short TTL"""

        cache_key = self._generate_cache_key("session_data", session_id, data_key=data_key)

        return await self.set(
            cache_key,
            data,
            CacheSecurityLevel.HEALTHCARE_SENSITIVE,
            ttl_override=ttl_minutes * 60,
            healthcare_context={"session_id": session_id, "data_key": data_key},
        )

    async def clear_session_cache(self, session_id: str) -> int:
        """Clear all cached data for a session"""

        if not self.redis_client:
            await self.initialize()

        if self.redis_client is None:
            raise RuntimeError("Redis client not available")

        pattern = f"{self.cache_prefixes['session_data']}*{session_id}*"

        try:
            keys = []
            async for key in self.redis_client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                deleted_count = await self.redis_client.delete(*keys)

                logger.info(
                    f"Cleared session cache for {session_id}",
                    extra={
                        "operation_type": "session_cache_clear",
                        "session_id": session_id,
                        "keys_deleted": deleted_count,
                    },
                )

                return int(deleted_count)

            return 0

        except Exception as e:
            logger.error(f"Failed to clear session cache for {session_id}: {e}")
            return 0

    async def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics for monitoring"""

        if not self.redis_client:
            await self.initialize()

        if self.redis_client is None:
            raise RuntimeError("Redis client not available")

        try:
            info = await self.redis_client.info()

            # Get key counts by prefix
            key_counts = {}
            for prefix_name, prefix in self.cache_prefixes.items():
                count = 0
                async for _ in self.redis_client.scan_iter(match=f"{prefix}*"):
                    count += 1
                key_counts[prefix_name] = count

            stats = {
                "redis_info": {
                    "used_memory": info.get("used_memory_human"),
                    "connected_clients": info.get("connected_clients"),
                    "total_keys": info.get("db1", {}).get("keys", 0),
                },
                "key_counts_by_type": key_counts,
                "cache_levels": {level.value: ttl for level, ttl in self.cache_ttls.items()},
                "timestamp": datetime.utcnow().isoformat(),
            }

            return stats

        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"error": str(e)}

    def _generate_cache_key(self, cache_type: str, primary_key: str, **kwargs: Any) -> str:
        """Generate consistent cache key"""

        prefix = self.cache_prefixes.get(cache_type, f"{cache_type}:")

        # Create hash of primary key and additional parameters
        key_data = {"primary": primary_key, **kwargs}

        key_hash = hashlib.sha256(json.dumps(key_data, sort_keys=True).encode()).hexdigest()[:16]

        return f"{prefix}{key_hash}"

    async def _detect_phi_in_data(self, data: Any) -> bool:
        """Detect PHI in data before caching"""

        # Simple PHI detection - in production would use comprehensive PHI detector
        data_str = json.dumps(data, default=str).lower()

        phi_patterns = [
            "ssn",
            "social security",
            "patient_id",
            "medical_record",
            "phone",
            "email",
            "address",
            "date_of_birth",
        ]

        return any(pattern in data_str for pattern in phi_patterns)

    async def cleanup(self) -> None:
        """Cleanup Redis connection"""
        if self.redis_client:
            await self.redis_client.close()


class HealthcareCacheDecorator:
    """Decorator for caching healthcare function results"""

    def __init__(
        self,
        cache_manager: HealthcareCacheManager,
        cache_type: str,
        security_level: CacheSecurityLevel = CacheSecurityLevel.PUBLIC,
        ttl_seconds: int | None = None,
    ):
        self.cache_manager = cache_manager
        self.cache_type = cache_type
        self.security_level = security_level
        self.ttl_seconds = ttl_seconds

    def __call__(self, func: Any) -> Any:
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Generate cache key from function arguments
            cache_key = self._generate_function_cache_key(func.__name__, args, kwargs)

            # Try to get from cache
            cached_result = await self.cache_manager.get(cache_key, self.security_level)
            if cached_result is not None:
                return cached_result

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result
            await self.cache_manager.set(
                cache_key,
                result,
                self.security_level,
                self.ttl_seconds,
                healthcare_context={
                    "function": func.__name__,
                    "args_count": len(args),
                    "kwargs_count": len(kwargs),
                },
            )

            return result

        return wrapper

    def _generate_function_cache_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Generate cache key for function call"""

        key_data = {"function": func_name, "args": args, "kwargs": kwargs}

        key_hash = hashlib.sha256(
            json.dumps(key_data, sort_keys=True, default=str).encode()
        ).hexdigest()[:16]

        prefix = self.cache_manager.cache_prefixes.get(self.cache_type, f"{self.cache_type}:")
        return f"{prefix}func_{key_hash}"


# Singleton cache manager instance
_cache_manager: HealthcareCacheManager | None = None


async def get_healthcare_cache() -> HealthcareCacheManager:
    """Get singleton healthcare cache manager"""
    global _cache_manager

    if _cache_manager is None:
        _cache_manager = HealthcareCacheManager()
        await _cache_manager.initialize()

    return _cache_manager


# Convenience decorators for common cache types
def cache_medical_literature(ttl_seconds: int = 3600 * 24) -> Any:
    """Decorator for caching medical literature results"""

    async def decorator(func: Any) -> Any:
        cache_manager = await get_healthcare_cache()
        return HealthcareCacheDecorator(
            cache_manager, "medical_literature", CacheSecurityLevel.PUBLIC, ttl_seconds
        )(func)

    return decorator


def cache_drug_interactions(ttl_seconds: int = 3600 * 24 * 7) -> Any:
    """Decorator for caching drug interaction results"""

    async def decorator(func: Any) -> Any:
        cache_manager = await get_healthcare_cache()
        return HealthcareCacheDecorator(
            cache_manager, "drug_interactions", CacheSecurityLevel.HEALTHCARE_SENSITIVE, ttl_seconds
        )(func)

    return decorator
