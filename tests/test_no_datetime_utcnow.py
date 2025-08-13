import os
import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent / "services" / "user" / "healthcare-api"
FORBIDDEN_PATTERN = re.compile(r"datetime\.utcnow\(")

@pytest.mark.unit
def test_no_datetime_utcnow_usage():
    """Ensure codebase does not use naive datetime.utcnow(), enforcing timezone aware now(timezone.utc)."""
    assert PROJECT_ROOT.exists(), f"Project root not found: {PROJECT_ROOT}"
    offending = []
    for path in PROJECT_ROOT.rglob("*.py"):
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:  # pragma: no cover
            continue
        if "datetime.utcnow(" in text:  # quick check
            offending.append(str(path))
    assert not offending, f"Found forbidden datetime.utcnow() usage in: {offending}"
