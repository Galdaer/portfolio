import asyncio
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

from core.infrastructure.health_monitoring import healthcare_monitor


@pytest.mark.unit
def test_quick_health_uses_comprehensive_cache(test_client: TestClient):
    """quick_health_check only returns cached results if a comprehensive check ran recently.

    This test seeds cache with /admin/health/full then verifies /admin/health/quick
    returns cached=True within 30s window.
    """
    healthcare_monitor.cached_status = {}
    healthcare_monitor.last_check_time = 0.0

    # Seed cache via comprehensive health endpoint
    full_resp = test_client.get("/admin/health/full")
    assert full_resp.status_code == 200
    seeded_timestamp = healthcare_monitor.last_check_time
    assert healthcare_monitor.cached_status

    # First quick call should be served from cache
    q1 = test_client.get("/admin/health/quick")
    assert q1.status_code == 200
    q1_data = q1.json()
    assert q1_data.get("cached") is True
    assert q1_data.get("cache_age_seconds") >= 0
    assert healthcare_monitor.last_check_time == seeded_timestamp

    # Advance simulated time but still <30s to remain cached
    original_time = time.time
    try:
        time.time = lambda: seeded_timestamp + 15  # type: ignore
        q2 = test_client.get("/admin/health/quick")
        assert q2.status_code == 200
        q2_data = q2.json()
        assert q2_data.get("cached") is True
        assert healthcare_monitor.last_check_time == seeded_timestamp
    finally:
        time.time = original_time  # type: ignore


@pytest.mark.unit
def test_quick_health_cache_expiry_after_30_seconds(test_client: TestClient):
    healthcare_monitor.cached_status = {}
    healthcare_monitor.last_check_time = 0.0

    # Seed cache via comprehensive health
    full_resp = test_client.get("/admin/health/full")
    assert full_resp.status_code == 200
    seed_time = healthcare_monitor.last_check_time

    # Expire cache (>30s)
    original_time = time.time
    try:
        time.time = lambda: seed_time + 31  # type: ignore
        q = test_client.get("/admin/health/quick")
        assert q.status_code == 200
        data = q.json()
        # Fresh quick result (not cached) because seeded comprehensive cache is stale; quick path itself doesn't update cache
        assert data.get("cached") is None
    finally:
        time.time = original_time  # type: ignore
