import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
def test_metrics_basic_lines(test_client: TestClient):
    # Seed comprehensive health to populate cached component snapshot
    seed = test_client.get("/admin/health/full")
    assert seed.status_code == 200
    resp = test_client.get("/metrics")
    assert resp.status_code == 200
    body = resp.text
    # Core health metrics
    assert "healthcare_overall_status" in body
    assert "# TYPE healthcare_overall_status gauge" in body
    # Component status lines should exist (database or cache or rate_limiting etc.)
    assert (
        'healthcare_component_status{component="database"' in body
        or 'healthcare_component_status{component="cache"' in body
        or 'healthcare_component_status{component="rate_limiting"' in body
    ), "Expected at least one component status metric line"
    # Rate limiting metrics (aggregate with outcome labels)
    assert 'healthcare_rate_limit_total{outcome="allowed"}' in body
    assert 'healthcare_rate_limit_total{outcome="denied"}' in body


@pytest.mark.unit
def test_metrics_instance_label_injection(test_client: TestClient, monkeypatch):
    monkeypatch.setenv("METRICS_INSTANCE", "test-instance-1")
    # Seed health snapshot
    test_client.get("/admin/health/full")
    resp = test_client.get("/metrics")
    assert resp.status_code == 200
    body = resp.text
    # Ensure instance label appears on health metric line with label set
    line = next(
        (
            line_
            for line_ in body.splitlines()
            if line_.startswith("healthcare_overall_status") and "{" in line_
        ),
        None,
    )
    assert line is not None, "Expected labeled healthcare_overall_status line"
    assert 'instance="test-instance-1"' in line
