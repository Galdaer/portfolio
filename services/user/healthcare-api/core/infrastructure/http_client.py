"""Lightweight async HTTP client utilities with retry & PHI-safe logging.

Placed in infrastructure (not agents/shared) so multiple agents can reuse
without creating a new shared hierarchy.

Design:
- Uses httpx.AsyncClient (defer import to allow environment without httpx)
- Exponential backoff with jitter
- Optional PHI masking: naive pattern-based redaction for logging only
- Pure functions; caller may pass a shared client for connection pooling

DISCLAIMER: This client logs only redacted summaries when PHI masking enabled.
"""
from __future__ import annotations

import asyncio
import json
import math
import random
from dataclasses import dataclass
from typing import Any, Dict, Optional

from core.infrastructure.healthcare_logger import get_healthcare_logger

logger = get_healthcare_logger("infrastructure.http_client")

try:  # optional dependency pattern
    import httpx  # type: ignore
except Exception:  # pragma: no cover
    httpx = None  # type: ignore


@dataclass
class HTTPRequestSpec:
    method: str
    url: str
    headers: Dict[str, str] | None = None
    json_body: Any | None = None
    timeout: float = 10.0


MASK_PATTERNS = [
    "patient", "name", "dob", "ssn", "mrn", "address", "phone", "email",
]


def _mask_value(val: str) -> str:
    lowered = val.lower()
    for pat in MASK_PATTERNS:
        if pat in lowered:
            return "[REDACTED]"
    if len(val) > 120:
        return val[:117] + "..."
    return val


def _redact_body(body: Any) -> Any:
    try:
        if isinstance(body, dict):
            return {k: _mask_value(str(v)) for k, v in body.items()}
        if isinstance(body, list):
            return [_mask_value(str(v)) for v in body]
        if isinstance(body, (str, bytes)):
            return _mask_value(body if isinstance(body, str) else body.decode("utf-8", "ignore"))
    except Exception:  # pragma: no cover
        return "[UNREDACTABLE]"
    return body


async def _sleep_backoff(attempt: int, base: float, cap: float) -> None:
    delay = min(cap, base * math.pow(2, attempt))
    # jitter
    delay = delay * (0.6 + random.random() * 0.4)
    await asyncio.sleep(delay)


async def http_request(
    spec: HTTPRequestSpec,
    *,
    retries: int = 2,
    backoff_base: float = 0.25,
    backoff_cap: float = 3.0,
    client: Any | None = None,
    mask_phi: bool = True,
) -> tuple[int, Dict[str, Any] | str | None]:
    """Execute HTTP request with basic retries.

    Returns tuple(status_code, json_or_text_body)
    """
    if httpx is None:  # pragma: no cover
        raise RuntimeError("httpx not available in environment")

    owned_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=spec.timeout)
        owned_client = True

    try:
        for attempt in range(retries + 1):
            try:
                response = await client.request(
                    spec.method.upper(),
                    spec.url,
                    headers=spec.headers,
                    json=spec.json_body,
                    timeout=spec.timeout,
                )
                content_type = response.headers.get("content-type", "")
                parsed: Dict[str, Any] | str | None = None
                if "application/json" in content_type:
                    try:
                        parsed = response.json()
                    except Exception:
                        parsed = response.text
                else:
                    parsed = response.text

                # Logging
                if mask_phi:
                    body_preview = _redact_body(spec.json_body)
                else:
                    body_preview = spec.json_body
                logger.info(
                    "http_request",
                    extra={
                        "method": spec.method,
                        "url": spec.url,
                        "status": response.status_code,
                        "attempt": attempt,
                        "request_body_preview": body_preview,
                    },
                )

                # Retry on 5xx
                if response.status_code >= 500 and attempt < retries:
                    await _sleep_backoff(attempt, backoff_base, backoff_cap)
                    continue
                return response.status_code, parsed
            except Exception as e:  # network error
                if attempt < retries:
                    logger.warning(f"HTTP attempt {attempt} failed: {e}; retrying")
                    await _sleep_backoff(attempt, backoff_base, backoff_cap)
                    continue
                logger.error(f"HTTP request ultimately failed: {e}")
                raise
    finally:
        if owned_client:
            try:
                await client.aclose()
            except Exception:  # pragma: no cover
                pass


__all__ = ["HTTPRequestSpec", "http_request"]
