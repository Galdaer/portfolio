import re
import pytest
from fastapi.testclient import TestClient

HISTO_PREFIX = "healthcare_health_check_duration_seconds"

@pytest.mark.unit
def test_health_check_latency_histogram_present(test_client: TestClient):
    # Run comprehensive health twice to ensure counts increment
    r1 = test_client.get("/admin/health/full")
    assert r1.status_code == 200
    r2 = test_client.get("/admin/health/full")
    assert r2.status_code == 200
    metrics = test_client.get("/metrics")
    assert metrics.status_code == 200
    body = metrics.text
    # Ensure histogram type lines
    assert f"# TYPE {HISTO_PREFIX} histogram" in body
    # Collect bucket lines
    bucket_lines = [line for line in body.splitlines() if line.startswith(f"{HISTO_PREFIX}_bucket")]
    assert bucket_lines, "Expected histogram bucket lines"
    # Buckets should be cumulative; parse values
    values = []
    last = -1
    for line in bucket_lines:
        # Example: healthcare_health_check_duration_seconds_bucket{le="0.1"} 2
        m = re.search(r"}\s+(\d+)$", line)
        assert m, f"Could not parse bucket count from {line}"
        val = int(m.group(1))
        assert val >= last, "Histogram buckets must be cumulative non-decreasing"
        last = val
        values.append(val)
    # Expect final +Inf bucket equals _count
    count_line = next((line for line in body.splitlines() if line.startswith(f"{HISTO_PREFIX}_count")), None)
    assert count_line is not None
    total_count = int(count_line.split()[-1])
    assert values[-1] == total_count
    # Sum line present
    assert f"{HISTO_PREFIX}_sum" in body
