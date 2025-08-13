"""Lightweight agent metrics utilities.

Purpose: Provide per-agent counters & simple duration recording without
pulling in a heavy metrics stack. These feed higher-level /metrics exporter
that already exists for rate limiting & health. Agents can increment local
counters which are later scraped/merged.

Design goals:
 - Zero external dependency by default (pure in-memory)
 - Optional Redis backend if a redis client is passed (database-first pattern)
 - Non-blocking best-effort writes; failures fall back to in-memory
 - Timezone-aware timestamps (UTC) for last_update
 - Thread/async safe enough for typical agent workloads via asyncio.Lock

DISCLAIMER: Not a replacement for Prometheus instrumentation; acts as a
light aggregation layer so agents avoid duplicating counting logic.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from core.infrastructure.healthcare_logger import get_healthcare_logger

logger = get_healthcare_logger("infrastructure.agent_metrics")


class AgentMetricsStore:
    """In-memory metrics store with optional Redis duplication.

    Supported metric types (minimal set for current agents):
      - counters: simple incrementing integers
      - timings: store cumulative milliseconds & count for avg calculation
    """

    def __init__(self, agent_name: str, redis_client: Any | None = None) -> None:
        self.agent_name = agent_name
        self.redis = redis_client
        self._counters: dict[str, int] = {}
        self._timings: dict[str, dict[str, float]] = {}
        self._lock = asyncio.Lock()
        self._last_update: datetime | None = None

    @property
    def last_update(self) -> datetime | None:
        return self._last_update

    async def incr(self, name: str, amount: int = 1) -> None:
        async with self._lock:
            self._counters[name] = self._counters.get(name, 0) + amount
            self._last_update = datetime.now(UTC)
            if self.redis is not None:
                try:
                    await self._redis_incr(name, amount)
                except Exception as e:  # pragma: no cover - best effort
                    logger.warning(f"Redis incr failed for {name}: {e}")

    async def record_timing(self, name: str, duration_ms: float) -> None:
        async with self._lock:
            stat = self._timings.setdefault(name, {"total_ms": 0.0, "count": 0.0})
            stat["total_ms"] += float(duration_ms)
            stat["count"] += 1.0
            self._last_update = datetime.now(UTC)
            if self.redis is not None:
                try:
                    await self._redis_record_timing(name, duration_ms)
                except Exception as e:  # pragma: no cover
                    logger.warning(f"Redis timing failed for {name}: {e}")

    async def snapshot(self) -> dict[str, Any]:
        async with self._lock:
            timings_export = {}
            for key, stat in self._timings.items():
                avg = stat["total_ms"] / stat["count"] if stat["count"] else 0.0
                timings_export[key] = {
                    "total_ms": stat["total_ms"],
                    "count": int(stat["count"]),
                    "avg_ms": avg,
                }
            return {
                "agent": self.agent_name,
                "counters": dict(self._counters),
                "timings": timings_export,
                "last_update": self._last_update.isoformat() if self._last_update else None,
            }

    # Redis helpers -----------------------------------------------------
    async def _redis_incr(self, name: str, amount: int) -> None:
        key = f"agent:{self.agent_name}:counter:{name}"
        res = self.redis.incrby(key, amount)  # support sync/async
        if asyncio.iscoroutine(res):
            await res

    async def _redis_record_timing(self, name: str, duration_ms: float) -> None:
        key_total = f"agent:{self.agent_name}:timing:{name}:total_ms"
        key_count = f"agent:{self.agent_name}:timing:{name}:count"
        try:
            pipe = None
            if hasattr(self.redis, "pipeline"):
                pipe = self.redis.pipeline()
                pipe.incrbyfloat(key_total, float(duration_ms))
                pipe.incrby(key_count, 1)
                res = pipe.execute()
                if asyncio.iscoroutine(res):
                    await res
            else:
                r1 = self.redis.incrbyfloat(key_total, float(duration_ms))
                r2 = self.redis.incrby(key_count, 1)
                if asyncio.iscoroutine(r1):
                    await r1
                if asyncio.iscoroutine(r2):
                    await r2
        except Exception as e:  # pragma: no cover
            logger.debug(f"Redis timing pipe failed: {e}")


__all__ = ["AgentMetricsStore"]
