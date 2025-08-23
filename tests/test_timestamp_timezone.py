import re

import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
def test_full_health_timestamp_timezone(test_client: TestClient):
    resp = test_client.get("/admin/health/full")
    assert resp.status_code == 200
    data = resp.json()
    ts = data.get("timestamp")
    assert ts is not None
    # ISO 8601 with timezone ends with +00:00 or Z (we expect +00:00 after change)
    assert re.search(r"[T0-9:\.-]+\+00:00$", ts), f"Timestamp not timezone-aware: {ts}"


@pytest.mark.unit
def test_quick_health_timestamp_timezone(test_client: TestClient):
    # Seed cache
    test_client.get("/admin/health/full")
    resp = test_client.get("/admin/health/quick")
    assert resp.status_code == 200
    ts = resp.json().get("timestamp")
    assert ts is not None
    assert ts.endswith("+00:00"), f"Quick health timestamp not timezone-aware: {ts}"
