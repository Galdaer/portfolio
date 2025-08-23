import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
def test_rate_limit_disabled_metrics(monkeypatch, test_client: TestClient):
    """When RL_DISABLE=true, metrics should expose disabled flag and suppress normal counters."""
    monkeypatch.setenv("RL_DISABLE", "true")
    # Seed health so /metrics gets some health lines (not required for limiter lines)
    test_client.get("/admin/health/full")
    resp = test_client.get("/metrics")
    assert resp.status_code == 200
    body = resp.text.splitlines()
    # Disabled flag present
    disabled_line = next(
        (line for line in body if line.startswith("healthcare_rate_limit_disabled")), None
    )
    assert disabled_line == "healthcare_rate_limit_disabled 1"
    # Ensure standard rate limit counters absent when disabled
    assert not any(line.startswith("healthcare_rate_limit_total") for line in body), (
        "rate_limit_total should be suppressed when disabled"
    )
    assert not any(line.startswith("healthcare_rate_limit_breakdown_total") for line in body), (
        "breakdown metrics should be suppressed when disabled"
    )
    # Policy info still present
    assert any(line.startswith("healthcare_rate_limit_policy_info") for line in body)
