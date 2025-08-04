"""
Healthcare Caching Layer
Provides intelligent caching for medical literature, drug interactions, and patient context
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class HealthcareCacheManager:
    """
    Intelligent caching system for healthcare AI operations

    Use Cases:
    - Medical literature search results (expensive PubMed/FDA queries)
    - Drug interaction databases (complex pharmaceutical data)
    - Clinical guideline lookups (stable reference data)
    - Patient session context (temporary, secure)

    Features:
    - TTL-based expiration (different for different data types)
    - Healthcare-appropriate cache keys (no PHI)
    - HIPAA-compliant patient context caching
    - Intelligent invalidation for updated medical data
    """

    def __init__(self) -> None:
        self.cache_ttl_config = {
            "medical_literature": 86400,  # 24 hours - literature is relatively stable
            "drug_interactions": 43200,   # 12 hours - drug data changes less frequently
            "clinical_guidelines": 604800,  # 7 days - guidelines are stable
            "patient_session": 3600,      # 1 hour - patient context should expire quickly
            "fda_data": 21600,            # 6 hours - regulatory data is fairly stable
            "medical_entities": 7200,     # 2 hours - entity extraction can be cached short-term
        }

    async def get_medical_literature(
        self,
        query: str,
        query_params: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        Get cached medical literature search results

        Args:
            query: The medical literature search query
            query_params: Additional search parameters (filters, limits, etc.)

        Returns:
            Cached literature results or None if not found/expired
        """
        cache_key = self._generate_literature_cache_key(query, query_params)

        try:
            from core.dependencies import healthcare_services
            redis_client = healthcare_services.redis_client

            if not redis_client:
                return None

            cached_data = await redis_client.get(cache_key)
            if cached_data:
                from typing import cast
                result: dict[str, Any] = cast(dict[str, Any], json.loads(cached_data))
                logger.info(f"Cache HIT for medical literature: {query[:50]}...")
                return result

        except Exception as e:
            logger.warning(f"Failed to get cached literature: {e}")

        return None

    async def cache_medical_literature(
        self,
        query: str,
        query_params: dict[str, Any],
        results: dict[str, Any]
    ) -> None:
        """
        Cache medical literature search results

        Args:
            query: The medical literature search query
            query_params: Additional search parameters
            results: Literature search results to cache
        """
        cache_key = self._generate_literature_cache_key(query, query_params)
        ttl = self.cache_ttl_config["medical_literature"]

        try:
            from core.dependencies import healthcare_services
            redis_client = healthcare_services.redis_client

            if not redis_client:
                return

            # Add cache metadata
            cache_data = {
                "query": query,
                "results": results,
                "cached_at": datetime.utcnow().isoformat(),
                "source": "medical_literature_cache"
            }

            await redis_client.setex(
                cache_key,
                ttl,
                json.dumps(cache_data)
            )
            logger.info(f"Cached medical literature: {query[:50]}... (TTL: {ttl}s)")

        except Exception as e:
            logger.warning(f"Failed to cache literature: {e}")

    async def get_drug_interactions(
        self,
        drug_list: list[str]
    ) -> dict[str, Any] | None:
        """
        Get cached drug interaction data

        Args:
            drug_list: List of drug names to check interactions for

        Returns:
            Cached drug interaction results or None if not found
        """
        cache_key = self._generate_drug_cache_key(drug_list)

        try:
            from core.dependencies import healthcare_services
            redis_client = healthcare_services.redis_client

            if not redis_client:
                return None

            cached_data = await redis_client.get(cache_key)
            if cached_data:
                from typing import cast
                result: dict[str, Any] = cast(dict[str, Any], json.loads(cached_data))
                logger.info(f"Cache HIT for drug interactions: {', '.join(drug_list[:3])}...")
                return result

        except Exception as e:
            logger.warning(f"Failed to get cached drug interactions: {e}")

        return None

    async def cache_drug_interactions(
        self,
        drug_list: list[str],
        interaction_data: dict[str, Any]
    ) -> None:
        """
        Cache drug interaction data

        Args:
            drug_list: List of drug names
            interaction_data: Drug interaction results to cache
        """
        cache_key = self._generate_drug_cache_key(drug_list)
        ttl = self.cache_ttl_config["drug_interactions"]

        try:
            from core.dependencies import healthcare_services
            redis_client = healthcare_services.redis_client

            if not redis_client:
                return

            cache_data = {
                "drugs": sorted(drug_list),  # Normalize order
                "interactions": interaction_data,
                "cached_at": datetime.utcnow().isoformat(),
                "source": "drug_interaction_cache"
            }

            await redis_client.setex(
                cache_key,
                ttl,
                json.dumps(cache_data)
            )
            logger.info(f"Cached drug interactions: {', '.join(drug_list)} (TTL: {ttl}s)")

        except Exception as e:
            logger.warning(f"Failed to cache drug interactions: {e}")

    async def get_patient_session_context(
        self,
        session_id: str
    ) -> dict[str, Any] | None:
        """
        Get cached patient session context (HIPAA-compliant)

        Args:
            session_id: Secure session identifier (no PHI)

        Returns:
            Cached session context or None if not found/expired

        Security:
            - Session IDs must not contain PHI
            - Context automatically expires after 1 hour
            - All patient data is synthetic for development
        """
        if self._contains_potential_phi(session_id):
            logger.warning(f"Session ID appears to contain PHI: {session_id[:10]}...")
            return None

        cache_key = f"patient_session:{session_id}"

        try:
            from core.dependencies import healthcare_services
            redis_client = healthcare_services.redis_client

            if not redis_client:
                return None

            cached_data = await redis_client.get(cache_key)
            if cached_data:
                from typing import cast
                result: dict[str, Any] = cast(dict[str, Any], json.loads(cached_data))
                logger.info(f"Cache HIT for patient session: {session_id}")
                return result

        except Exception as e:
            logger.warning(f"Failed to get cached session context: {e}")

        return None

    async def cache_patient_session_context(
        self,
        session_id: str,
        context_data: dict[str, Any]
    ) -> None:
        """
        Cache patient session context securely

        Args:
            session_id: Secure session identifier
            context_data: Session context to cache (must be synthetic data)

        Security:
            - Validates no PHI in session ID or context
            - Short TTL for security
            - Synthetic data only
        """
        if self._contains_potential_phi(session_id) or self._contains_potential_phi(str(context_data)):
            logger.error("PHI detected in session cache - operation blocked")
            return

        cache_key = f"patient_session:{session_id}"
        ttl = self.cache_ttl_config["patient_session"]

        try:
            from core.dependencies import healthcare_services
            redis_client = healthcare_services.redis_client

            if not redis_client:
                return

            cache_data = {
                "session_id": session_id,
                "context": context_data,
                "cached_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(seconds=ttl)).isoformat(),
                "source": "patient_session_cache"
            }

            await redis_client.setex(
                cache_key,
                ttl,
                json.dumps(cache_data)
            )
            logger.info(f"Cached patient session: {session_id} (TTL: {ttl}s)")

        except Exception as e:
            logger.warning(f"Failed to cache session context: {e}")

    async def invalidate_medical_cache(self, cache_type: str = "all") -> None:
        """
        Invalidate medical cache (for updated medical data)

        Args:
            cache_type: Type of cache to invalidate ("all", "literature", "drugs", etc.)
        """
        try:
            from core.dependencies import healthcare_services
            redis_client = healthcare_services.redis_client

            if not redis_client:
                return

            if cache_type == "all":
                patterns = ["medical_lit:*", "drug_int:*", "clinical_guide:*"]
            elif cache_type == "literature":
                patterns = ["medical_lit:*"]
            elif cache_type == "drugs":
                patterns = ["drug_int:*"]
            else:
                patterns = [f"{cache_type}:*"]

            for pattern in patterns:
                keys = await redis_client.keys(pattern)
                if keys:
                    await redis_client.delete(*keys)
                    logger.info(f"Invalidated {len(keys)} cache entries for pattern: {pattern}")

        except Exception as e:
            logger.warning(f"Failed to invalidate cache: {e}")

    def _generate_literature_cache_key(self, query: str, params: dict[str, Any]) -> str:
        """Generate cache key for literature search"""
        # Create deterministic key from query and params
        combined = f"{query}:{json.dumps(params, sort_keys=True)}"
        hash_key = hashlib.md5(combined.encode()).hexdigest()
        return f"medical_lit:{hash_key}"

    def _generate_drug_cache_key(self, drug_list: list[str]) -> str:
        """Generate cache key for drug interactions"""
        # Sort drugs for consistent cache keys
        sorted_drugs = sorted([drug.lower().strip() for drug in drug_list])
        combined = ":".join(sorted_drugs)
        hash_key = hashlib.md5(combined.encode()).hexdigest()
        return f"drug_int:{hash_key}"

    def _contains_potential_phi(self, text: str) -> bool:
        """
        Basic PHI detection for cache security

        Returns:
            True if potential PHI patterns detected
        """
        import re
        phi_patterns = [
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
            r'\b\d{3}-\d{3}-\d{4}\b',  # Phone (non-555 test numbers)
            r'\b[A-Za-z0-9._%+-]+@(?!example\.com)[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'  # Real email
        ]

        for pattern in phi_patterns:
            if re.search(pattern, text):
                return True
        return False

    async def get_cache_stats(self) -> dict[str, Any]:
        """
        Get cache performance statistics

        Returns:
            Cache statistics for monitoring
        """
        try:
            from core.dependencies import healthcare_services
            redis_client = healthcare_services.redis_client

            if not redis_client:
                return {"status": "redis_unavailable"}

            # Get Redis info
            info = await redis_client.info()

            # Count cache entries by type
            cache_counts = {}
            for cache_type in ["medical_lit", "drug_int", "clinical_guide", "patient_session"]:
                keys = await redis_client.keys(f"{cache_type}:*")
                cache_counts[cache_type] = len(keys)

            return {
                "status": "healthy",
                "redis_memory_used": info.get("used_memory_human", "unknown"),
                "cache_entry_counts": cache_counts,
                "total_keys": sum(cache_counts.values()),
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.warning(f"Failed to get cache stats: {e}")
            return {"status": "error", "error": str(e)}

# Global cache manager instance
healthcare_cache = HealthcareCacheManager()
