"""
Healthcare Rate Limiting Infrastructure

Provides intelligent rate limiting for healthcare APIs with role-based limits,
medical emergency bypass, and healthcare-appropriate thresholds.
"""

import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict

try:
    import yaml  # type: ignore
    _YAML_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    _YAML_AVAILABLE = False

import redis.asyncio as redis
from fastapi import HTTPException, Request, Response

from core.infrastructure.authentication import AuthenticatedUser, HealthcareRole

logger = logging.getLogger(__name__)


class RateLimitType(str, Enum):
    """Types of rate limiting for healthcare operations"""

    API_GENERAL = "api_general"  # General API calls
    MEDICAL_QUERY = "medical_query"  # Medical literature/research queries
    PATIENT_ACCESS = "patient_access"  # Patient data access
    DOCUMENT_UPLOAD = "document_upload"  # Document processing
    EMERGENCY = "emergency"  # Emergency/urgent requests
    BULK_OPERATION = "bulk_operation"  # Bulk data operations


@dataclass
class RateLimitConfig:
    """Rate limit configuration for healthcare operations"""

    requests_per_minute: int
    requests_per_hour: int
    burst_allowance: int
    emergency_bypass: bool = False
    description: str = ""


def _default_limits() -> dict[HealthcareRole, dict[RateLimitType, RateLimitConfig]]:
    """Hard-coded fallback limits used if YAML not present or parsing fails.

    NOTE: Keep in sync with config/rate_limits.yml. Externalization allows
    operations teams to tune limits without code changes. Scaling and disabling
    can be controlled via environment variables (RL_GLOBAL_SCALE, RL_DISABLE).
    """
    return {
        HealthcareRole.DOCTOR: {
            RateLimitType.API_GENERAL: RateLimitConfig(
                requests_per_minute=120,
                requests_per_hour=3600,
                burst_allowance=20,
                description="High limits for doctors during patient care",
            ),
            RateLimitType.MEDICAL_QUERY: RateLimitConfig(
                requests_per_minute=60,
                requests_per_hour=1800,
                burst_allowance=15,
                description="Medical literature and research queries",
            ),
            RateLimitType.PATIENT_ACCESS: RateLimitConfig(
                requests_per_minute=180,
                requests_per_hour=5400,
                burst_allowance=30,
                description="Patient data access during clinical care",
            ),
            RateLimitType.EMERGENCY: RateLimitConfig(
                requests_per_minute=300,
                requests_per_hour=7200,
                burst_allowance=50,
                emergency_bypass=True,
                description="Emergency medical situations",
            ),
        },
        HealthcareRole.NURSE: {
            RateLimitType.API_GENERAL: RateLimitConfig(
                requests_per_minute=90,
                requests_per_hour=2700,
                burst_allowance=15,
                description="Nurse workflow support",
            ),
            RateLimitType.MEDICAL_QUERY: RateLimitConfig(
                requests_per_minute=30,
                requests_per_hour=900,
                burst_allowance=10,
                description="Medical reference lookups",
            ),
            RateLimitType.PATIENT_ACCESS: RateLimitConfig(
                requests_per_minute=120,
                requests_per_hour=3600,
                burst_allowance=20,
                description="Patient care data access",
            ),
        },
        HealthcareRole.RECEPTIONIST: {
            RateLimitType.API_GENERAL: RateLimitConfig(
                requests_per_minute=60,
                requests_per_hour=1800,
                burst_allowance=10,
                description="Administrative operations",
            ),
            RateLimitType.PATIENT_ACCESS: RateLimitConfig(
                requests_per_minute=90,
                requests_per_hour=2700,
                burst_allowance=15,
                description="Patient scheduling and demographics",
            ),
        },
        HealthcareRole.BILLING: {
            RateLimitType.API_GENERAL: RateLimitConfig(
                requests_per_minute=45,
                requests_per_hour=1350,
                burst_allowance=8,
                description="Billing operations",
            ),
            RateLimitType.BULK_OPERATION: RateLimitConfig(
                requests_per_minute=20,
                requests_per_hour=600,
                burst_allowance=5,
                description="Bulk billing data processing",
            ),
        },
        HealthcareRole.RESEARCH: {
            RateLimitType.API_GENERAL: RateLimitConfig(
                requests_per_minute=30,
                requests_per_hour=900,
                burst_allowance=5,
                description="Research data access",
            ),
            RateLimitType.MEDICAL_QUERY: RateLimitConfig(
                requests_per_minute=45,
                requests_per_hour=1350,
                burst_allowance=10,
                description="Research literature queries",
            ),
        },
        HealthcareRole.ADMIN: {
            RateLimitType.API_GENERAL: RateLimitConfig(
                requests_per_minute=200,
                requests_per_hour=6000,
                burst_allowance=40,
                description="Administrative system access",
            ),
            RateLimitType.BULK_OPERATION: RateLimitConfig(
                requests_per_minute=100,
                requests_per_hour=3000,
                burst_allowance=20,
                description="System administration operations",
            ),
        },
    }


def _apply_scale(value: int, scale: float) -> int:
    return max(1, int(round(value * scale)))


RATE_LIMITS_SOURCE: str = "defaults"
RATE_LIMITS_POLICY_VERSION: str = "1"


def _load_external_rate_limits() -> dict[HealthcareRole, dict[RateLimitType, RateLimitConfig]]:
    """Load external YAML config for rate limits with scaling & fallbacks.

    Environment variables:
        RL_YAML_PATH: path to YAML file (default config/rate_limits.yml)
        RL_GLOBAL_SCALE: float multiplier applied to rpm/rph/burst (default 1.0)
        RL_DISABLE: if 'true', returns permissive limits (very high values)

    Returns parsed structure or defaults on error. Errors are logged but never
    raise to avoid blocking healthcare operations.
    """
    # Discovery precedence:
    # 1. Explicit RL_YAML_PATH
    # 2. First matching 'rate_limits.yml' under CONFIG_DISCOVERY_ROOT (default 'config')
    # 3. Fallback default hard-coded limits
    global RATE_LIMITS_SOURCE, RATE_LIMITS_POLICY_VERSION
    yaml_path_env = os.getenv("RL_YAML_PATH")
    discovery_root = os.getenv("CONFIG_DISCOVERY_ROOT", "config")
    yaml_path: str
    if yaml_path_env:
        yaml_path = yaml_path_env
    else:
        # Prefer indexed config if present
        index_path = Path(discovery_root) / "config_index.yml"
        indexed_path: str | None = None
        try:
            if index_path.exists() and _YAML_AVAILABLE:
                with index_path.open("r", encoding="utf-8") as f:
                    idx_data = yaml.safe_load(f) or {}
                RATE_LIMITS_POLICY_VERSION = str(idx_data.get("version", RATE_LIMITS_POLICY_VERSION))
                files = idx_data.get("files", [])
                for entry in files:
                    # support either string entries or dict with name/path keys
                    if isinstance(entry, str) and entry.endswith("rate_limits.yml"):
                        indexed_path = str(Path(discovery_root) / entry)
                        break
                    if isinstance(entry, dict):
                        path_val = entry.get("path") or entry.get("name")
                        if path_val and str(path_val).endswith("rate_limits.yml"):
                            indexed_path = str(Path(discovery_root) / str(path_val))
                            break
        except Exception:  # pragma: no cover
            logger.debug("Failed loading config_index.yml for rate limits", exc_info=True)
        if indexed_path:
            yaml_path = indexed_path
        else:
            # Walk discovery root (non-fatal if large; assume controlled). Stop at first match.
            found: str | None = None
            root_path = Path(discovery_root)
            if root_path.exists():
                for p in root_path.rglob("rate_limits.yml"):
                    found = str(p)
                    break
            yaml_path = found if found else str(root_path / "rate_limits.yml")
    disable = os.getenv("RL_DISABLE", "false").lower() == "true"
    scale_raw = os.getenv("RL_GLOBAL_SCALE", "1.0")
    try:
        scale = float(scale_raw)
        if scale <= 0:
            raise ValueError("Scale must be > 0")
    except Exception:
        logger.warning("Invalid RL_GLOBAL_SCALE=%s; defaulting to 1.0", scale_raw)
        scale = 1.0

    if disable:
        logger.warning("Rate limiting disabled via RL_DISABLE environment variable")
        # Return extremely high limits but keep structure
        base = _default_limits()
        for role_cfg in base.values():
            for cfg in role_cfg.values():
                cfg.requests_per_minute = 1_000_000
                cfg.requests_per_hour = 10_000_000
                cfg.burst_allowance = 100_000
        return base

    if not _YAML_AVAILABLE:
        logger.info("yaml library not available; using default embedded rate limits")
        base = _default_limits()
        if scale != 1.0:
            for role_cfg in base.values():
                for cfg in role_cfg.values():
                    cfg.requests_per_minute = _apply_scale(cfg.requests_per_minute, scale)
                    cfg.requests_per_hour = _apply_scale(cfg.requests_per_hour, scale)
                    cfg.burst_allowance = _apply_scale(cfg.burst_allowance, scale)
        return base

    path = Path(yaml_path)
    if not path.exists():
        logger.warning("Rate limits YAML not found at %s; using defaults", path)
        base = _default_limits()
        if scale != 1.0:
            for role_cfg in base.values():
                for cfg in role_cfg.values():
                    cfg.requests_per_minute = _apply_scale(cfg.requests_per_minute, scale)
                    cfg.requests_per_hour = _apply_scale(cfg.requests_per_hour, scale)
                    cfg.burst_allowance = _apply_scale(cfg.burst_allowance, scale)
        return base

    try:
        with path.open("r", encoding="utf-8") as f:
            data: Dict[str, Any] = yaml.safe_load(f) or {}
        roles: Dict[str, Any] = data.get("roles", {})
        result: dict[HealthcareRole, dict[RateLimitType, RateLimitConfig]] = {}
        for role_name, limits in roles.items():
            try:
                role_enum = HealthcareRole[role_name]
            except KeyError:
                logger.warning("Unknown role in rate_limits.yml: %s", role_name)
                continue
            role_map: dict[RateLimitType, RateLimitConfig] = {}
            for limit_key, cfg in limits.items():
                try:
                    limit_enum = RateLimitType(limit_key)
                except ValueError:
                    logger.warning("Unknown limit type for role %s: %s", role_name, limit_key)
                    continue
                rpm = int(cfg.get("rpm", 30))
                rph = int(cfg.get("rph", 900))
                burst = int(cfg.get("burst", 5))
                emergency = bool(cfg.get("emergency_bypass", False))
                if scale != 1.0:
                    rpm = _apply_scale(rpm, scale)
                    rph = _apply_scale(rph, scale)
                    burst = _apply_scale(burst, scale)
                role_map[limit_enum] = RateLimitConfig(
                    requests_per_minute=rpm,
                    requests_per_hour=rph,
                    burst_allowance=burst,
                    emergency_bypass=emergency,
                    description=f"Configured via YAML (role={role_name}, type={limit_key})",
                )
            if role_map:
                result[role_enum] = role_map
        # Merge with defaults to ensure missing combinations get fallback
        defaults = _default_limits()
        for role, d_limits in defaults.items():
            if role not in result:
                result[role] = d_limits
                continue
            for lt, cfg in d_limits.items():
                result[role].setdefault(lt, cfg)
        RATE_LIMITS_SOURCE = str(path)
        logger.info(
            "Loaded external rate limits from %s (scale=%s, policy_version=%s)",
            path,
            scale,
            RATE_LIMITS_POLICY_VERSION,
        )
        return result
    except Exception as exc:  # pragma: no cover - robustness path
        logger.exception("Failed parsing rate limits YAML (%s); using defaults", exc)
        return _default_limits()


# Initialize global rate limits (may be reloaded later if hot-reload added)
HEALTHCARE_RATE_LIMITS: dict[HealthcareRole, dict[RateLimitType, RateLimitConfig]] = _load_external_rate_limits()


@dataclass
class RateLimitStatus:
    """Current rate limit status for a user

    tokens_remaining: remaining burst tokens (after request) if token bucket used
    """

    allowed: bool
    requests_remaining: int
    reset_time: datetime
    retry_after_seconds: int | None = None
    limit_type: RateLimitType | None = None
    user_role: HealthcareRole | None = None
    tokens_remaining: float | None = None
    user_id: str | None = None


RATE_LIMIT_METRICS: dict[str, int] = {
    "allowed": 0,
    "denied": 0,
    "emergency_bypass": 0,
}


def _metric_key(role: HealthcareRole, limit_type: RateLimitType, outcome: str) -> str:
    return f"{role.value}:{limit_type.value}:{outcome}"


class HealthcareRateLimiter:
    """Healthcare-focused rate limiter with role-based limits and emergency bypass.

    Implements hybrid token-bucket (burst & smoothing) + fixed window (minute/hour) limits.
    """

    def __init__(self, redis_client: redis.Redis | None = None):
        self.redis_client = redis_client
        self.emergency_bypass_active: dict[str, datetime] = {}
        logger.info("Healthcare rate limiter initialized (policy_version=%s, source=%s)", RATE_LIMITS_POLICY_VERSION, RATE_LIMITS_SOURCE)

    async def check_rate_limit(
        self,
        user: AuthenticatedUser,
        limit_type: RateLimitType,
        request_id: str | None = None,
        is_emergency: bool = False,
    ) -> RateLimitStatus:
        """
        Check if request is within rate limits

        Args:
            user: Authenticated healthcare user
            limit_type: Type of operation being rate limited
            request_id: Optional request identifier for tracking
            is_emergency: Whether this is an emergency medical request
        """

        # Get rate limit configuration for user role and operation type
        role_limits = HEALTHCARE_RATE_LIMITS.get(user.role, {})
        limit_config = role_limits.get(limit_type)

        if not limit_config:
            # Default limits for unknown combinations
            limit_config = RateLimitConfig(
                requests_per_minute=30,
                requests_per_hour=900,
                burst_allowance=5,
                description="Default healthcare rate limit",
            )

        # Prune expired emergency bypass entries lazily
        if self.emergency_bypass_active:
            now = datetime.now()
            expired = [uid for uid, exp in self.emergency_bypass_active.items() if exp < now]
            for uid in expired:
                self.emergency_bypass_active.pop(uid, None)

        # Activate emergency bypass if requested and allowed
        if is_emergency and limit_config.emergency_bypass:
            duration_minutes = int(os.getenv("RL_EMERGENCY_DEFAULT_MINUTES", "30"))
            expiry = datetime.now() + timedelta(minutes=duration_minutes)
            logger.info(
                "Emergency bypass activated - user=%s role=%s type=%s duration=%sm",  # noqa: E501
                user.user_id,
                user.role.value,
                limit_type.value,
                duration_minutes,
            )
            self.emergency_bypass_active[user.user_id] = expiry
            RATE_LIMIT_METRICS["emergency_bypass"] = RATE_LIMIT_METRICS.get("emergency_bypass", 0) + 1
            return RateLimitStatus(
                allowed=True,
                requests_remaining=999,
                reset_time=expiry,
                limit_type=limit_type,
                user_role=user.role,
                user_id=user.user_id,
            )

        # If already under active bypass for any type, allow generously
        active_expiry = self.emergency_bypass_active.get(user.user_id)
        if active_expiry and active_expiry > datetime.now():
            return RateLimitStatus(
                allowed=True,
                requests_remaining=999,
                reset_time=active_expiry,
                limit_type=limit_type,
                user_role=user.role,
                user_id=user.user_id,
            )

        # Check sliding window rate limits
        current_time = time.time()
        minute_key = f"rate_limit:{user.user_id}:{limit_type.value}:minute"
        hour_key = f"rate_limit:{user.user_id}:{limit_type.value}:hour"

        try:
            if self.redis_client:
                # Use Redis for distributed rate limiting (token bucket + counters)
                status = await self._check_redis_rate_limit(
                    user, limit_config, limit_type, minute_key, hour_key, current_time,
                )
            else:
                # Fallback to in-memory rate limiting
                status = await self._check_memory_rate_limit(
                    user, limit_config, limit_type, current_time,
                )

            # Log rate limit status for healthcare audit
            if not status.allowed:
                logger.warning(
                    f"Rate limit exceeded - User: {user.user_id}, "
                    f"Role: {user.role.value}, Type: {limit_type.value}, "
                    f"Retry after: {status.retry_after_seconds}s",
                )
                RATE_LIMIT_METRICS["denied"] = RATE_LIMIT_METRICS.get("denied", 0) + 1
                RATE_LIMIT_METRICS[_metric_key(user.role, limit_type, "denied")] = RATE_LIMIT_METRICS.get(_metric_key(user.role, limit_type, "denied"), 0) + 1
            else:
                RATE_LIMIT_METRICS["allowed"] = RATE_LIMIT_METRICS.get("allowed", 0) + 1
                RATE_LIMIT_METRICS[_metric_key(user.role, limit_type, "allowed")] = RATE_LIMIT_METRICS.get(_metric_key(user.role, limit_type, "allowed"), 0) + 1

            return status

        except Exception as e:
            logger.exception(f"Rate limit check failed: {e}")
            # Fail open for healthcare safety - allow request
            return RateLimitStatus(
                allowed=True,
                requests_remaining=100,
                reset_time=datetime.now() + timedelta(minutes=1),
                limit_type=limit_type,
                user_role=user.role,
            )

    async def _check_redis_rate_limit(
        self,
        user: AuthenticatedUser,
        config: RateLimitConfig,
        limit_type: RateLimitType,
        minute_key: str,
        hour_key: str,
        current_time: float,
    ) -> RateLimitStatus:
        """Check rate limits using atomic Redis Lua script for token bucket + guardrails.

        Lua script returns array:
            [ allowed(int 1/0), tokens_remaining(float), minute_count(int), hour_count(int), retry_after(int) ]
        """
        tb_key = f"rl:tb:{user.user_id}:{limit_type.value}"
        minute_window = int(current_time // 60)
        hour_window = int(current_time // 3600)
        minute_counter_key = f"{minute_key}:{minute_window}"
        hour_counter_key = f"{hour_key}:{hour_window}"
        capacity = max(1, config.burst_allowance)
        fill_rate_per_sec = config.requests_per_minute / 60.0 if config.requests_per_minute > 0 else 0.0
        lua = """
local tb_key = KEYS[1]
local minute_key = KEYS[2]
local hour_key = KEYS[3]
local now = tonumber(ARGV[1])
local capacity = tonumber(ARGV[2])
local fill_rate = tonumber(ARGV[3])
local rpm = tonumber(ARGV[4])
local rph = tonumber(ARGV[5])

local data = redis.call('HMGET', tb_key, 'tokens', 'ts')
local tokens = tonumber(data[1]) or capacity
local ts = tonumber(data[2]) or now
if now > ts then
    local elapsed = now - ts
    if fill_rate > 0 then
        tokens = math.min(capacity, tokens + elapsed * fill_rate)
    end
end
local allowed = 0
local retry_after = 0
if tokens >= 1 then
    tokens = tokens - 1
    allowed = 1
    redis.call('HMSET', tb_key, 'tokens', tokens, 'ts', now)
    redis.call('EXPIRE', tb_key, 3600)
end

local minute_count = tonumber(redis.call('GET', minute_key) or '0')
local hour_count = tonumber(redis.call('GET', hour_key) or '0')

if allowed == 1 then
    if minute_count >= rpm or hour_count >= rph then
        -- rollback token
        tokens = math.min(capacity, tokens + 1)
        redis.call('HMSET', tb_key, 'tokens', tokens, 'ts', now)
        allowed = 0
    else
        minute_count = minute_count + 1
        hour_count = hour_count + 1
        redis.call('INCR', minute_key)
        redis.call('EXPIRE', minute_key, 120)
        redis.call('INCR', hour_key)
        redis.call('EXPIRE', hour_key, 7200)
    end
end

if allowed == 0 then
    if tokens < 1 and fill_rate > 0 then
        local need = 1 - tokens
        retry_after = math.max(1, math.floor(need / fill_rate))
    else
        -- window exceed
        retry_after = 60 -- conservative default; client can retry after minute boundary
    end
end
return {allowed, tokens, minute_count, hour_count, retry_after}
        """
        try:
            result = await self.redis_client.eval(
                lua,
                3,
                tb_key,
                minute_counter_key,
                hour_counter_key,
                current_time,
                capacity,
                fill_rate_per_sec,
                config.requests_per_minute,
                config.requests_per_hour,
            )  # type: ignore
        except Exception as e:  # pragma: no cover
            logger.debug("Lua rate limit script failed, falling back to Python logic: %s", e)
            return await self._legacy_python_bucket(
                user, config, limit_type, minute_key, hour_key, current_time,
            )

        allowed_flag = int(result[0]) == 1
        tokens_remaining = float(result[1])
        minute_count = int(result[2])
        hour_count = int(result[3])
        retry_after = int(result[4])

        if not allowed_flag:
            return RateLimitStatus(
                allowed=False,
                requests_remaining=0,
                reset_time=datetime.fromtimestamp(current_time + retry_after),
                retry_after_seconds=retry_after,
                limit_type=limit_type,
                user_role=user.role,
                tokens_remaining=tokens_remaining,
                user_id=user.user_id,
            )

        remaining_by_time = min(
            config.requests_per_minute - minute_count,
            config.requests_per_hour - hour_count,
        )
        remaining = min(int(tokens_remaining), remaining_by_time)
        return RateLimitStatus(
            allowed=True,
            requests_remaining=max(0, remaining),
            reset_time=datetime.fromtimestamp(current_time + 60),
            limit_type=limit_type,
            user_role=user.role,
            tokens_remaining=tokens_remaining,
            user_id=user.user_id,
        )

    async def _legacy_python_bucket(
        self,
        user: AuthenticatedUser,
        config: RateLimitConfig,
        limit_type: RateLimitType,
        minute_key: str,
        hour_key: str,
        current_time: float,
    ) -> RateLimitStatus:
        # Minimal fallback: allow to avoid hard failure
        return RateLimitStatus(
            allowed=True,
            requests_remaining=config.requests_per_minute,
            reset_time=datetime.fromtimestamp(current_time + 60),
            limit_type=limit_type,
            user_role=user.role,
            tokens_remaining=float(config.burst_allowance),
            user_id=user.user_id,
        )

    async def _check_memory_rate_limit(
        self,
        user: AuthenticatedUser,
        config: RateLimitConfig,
        limit_type: RateLimitType,
        current_time: float,
    ) -> RateLimitStatus:
        """Fallback in-memory rate limiting"""
        # Simple implementation - in production, Redis should be preferred
        return RateLimitStatus(
            allowed=True,
            requests_remaining=config.requests_per_minute,
            reset_time=datetime.fromtimestamp(current_time + 60),
            limit_type=limit_type,
            user_role=user.role,
        )

    async def activate_emergency_bypass(
        self, user: AuthenticatedUser, duration_minutes: int = 30, reason: str = "Medical emergency",
    ) -> bool:
        """
        Activate emergency bypass for healthcare user

        Temporarily removes rate limits for emergency medical situations
        """
        if user.role not in [HealthcareRole.DOCTOR, HealthcareRole.NURSE, HealthcareRole.ADMIN]:
            logger.warning(f"Emergency bypass denied - insufficient role: {user.role.value}")
            return False

        self.emergency_bypass_active[user.user_id] = datetime.now() + timedelta(
            minutes=duration_minutes,
        )

        logger.info(
            f"Emergency bypass activated - User: {user.user_id}, "
            f"Duration: {duration_minutes}min, Reason: {reason}",
        )

        return True

    def get_rate_limit_headers(self, status: RateLimitStatus) -> dict[str, str]:
        """Generate HTTP headers for rate limit status with policy metadata"""
        headers = {
            "X-RateLimit-Limit": str(status.requests_remaining + 1),
            "X-RateLimit-Remaining": str(status.requests_remaining),
            "X-RateLimit-Reset": str(int(status.reset_time.timestamp())),
            "X-Healthcare-Role": status.user_role.value if status.user_role else "unknown",
            "X-RateLimit-Policy-Version": RATE_LIMITS_POLICY_VERSION,
            "X-RateLimit-Source": RATE_LIMITS_SOURCE,
        }

        if status.retry_after_seconds:
            headers["Retry-After"] = str(status.retry_after_seconds)

        if status.limit_type:
            headers["X-RateLimit-Type"] = status.limit_type.value

        if status.tokens_remaining is not None:
            headers["X-RateLimit-Tokens-Remaining"] = f"{status.tokens_remaining:.2f}"

        # Provide burst capacity once (static from config) if available
        role_limits = HEALTHCARE_RATE_LIMITS.get(status.user_role) if status.user_role else None
        if role_limits and status.limit_type in role_limits:
            headers["X-RateLimit-Burst-Capacity"] = str(role_limits[status.limit_type].burst_allowance)

        # Emergency bypass active header
        if status.user_id and self.emergency_bypass_active.get(status.user_id):
            if self.emergency_bypass_active[status.user_id] > datetime.now():
                headers["X-RateLimit-Emergency-Bypass"] = "active"

        return headers

    def snapshot_metrics(self) -> dict[str, Any]:
        """Return a structured snapshot of current metrics with breakdowns.

        Designed for lightweight JSON exposure; no heavy aggregation to keep O(1).
        """
        total_allowed = RATE_LIMIT_METRICS.get("allowed", 0)
        total_denied = RATE_LIMIT_METRICS.get("denied", 0)
        emergency = RATE_LIMIT_METRICS.get("emergency_bypass", 0)
        breakdown: dict[str, dict[str, int]] = {}
        for key, val in RATE_LIMIT_METRICS.items():
            if ":" in key:  # role:type:outcome pattern
                role, rtype, outcome = key.split(":", 2)
                breakdown.setdefault(role, {}).setdefault(rtype, 0)
                if outcome == "denied":
                    breakdown[role][rtype] -= val  # track negative for denied
                else:
                    breakdown[role][rtype] += val
        return {
            "summary": {
                "allowed": total_allowed,
                "denied": total_denied,
                "emergency_bypass": emergency,
                "allow_rate": (total_allowed / (total_allowed + total_denied)) if (total_allowed + total_denied) else 1.0,
            },
            "breakdown": breakdown,
            "policy_version": RATE_LIMITS_POLICY_VERSION,
            "source": RATE_LIMITS_SOURCE,
        }

    def prometheus_lines(self) -> list[str]:  # lightweight; no external deps
        """Build Prometheus exposition metric lines for rate limiter.

        Exposed separately so HTTP layer can reuse without duplicating logic.
        """
        lines: list[str] = []
        # If limiter disabled via env, emit a single flagged metric and suppress counters
        if os.getenv("RL_DISABLE", "false").lower() == "true":
            lines.append("# HELP healthcare_rate_limit_disabled Rate limiter disabled flag (1=disabled)")
            lines.append("# TYPE healthcare_rate_limit_disabled gauge")
            lines.append("healthcare_rate_limit_disabled 1")
            lines.append(
                f"healthcare_rate_limit_policy_info{{policy_version=\"{RATE_LIMITS_POLICY_VERSION}\",source=\"{RATE_LIMITS_SOURCE}\"}} 1"
            )
            return lines
        total_allowed = RATE_LIMIT_METRICS.get("allowed", 0)
        total_denied = RATE_LIMIT_METRICS.get("denied", 0)
        emergency = RATE_LIMIT_METRICS.get("emergency_bypass", 0)
        lines.append("# HELP healthcare_rate_limit_total Requests allowed/denied counters")
        lines.append("# TYPE healthcare_rate_limit_total counter")
        lines.append(f"healthcare_rate_limit_total{{outcome=\"allowed\"}} {total_allowed}")
        lines.append(f"healthcare_rate_limit_total{{outcome=\"denied\"}} {total_denied}")
        lines.append(f"healthcare_rate_limit_total{{outcome=\"emergency_bypass\"}} {emergency}")
        for key, val in RATE_LIMIT_METRICS.items():
            if ":" in key and key.count(":") == 2:
                role, rtype, outcome = key.split(":", 2)
                lines.append(
                    f"healthcare_rate_limit_breakdown_total{{role=\"{role}\",type=\"{rtype}\",outcome=\"{outcome}\"}} {val}"
                )
        lines.append(
            f"healthcare_rate_limit_policy_info{{policy_version=\"{RATE_LIMITS_POLICY_VERSION}\",source=\"{RATE_LIMITS_SOURCE}\"}} 1"
        )
        # Active emergency bypass gauge
        active_bypass = sum(1 for _, exp in self.emergency_bypass_active.items() if exp > datetime.now())
        lines.append("# HELP healthcare_active_emergency_bypass Active emergency bypass sessions")
        lines.append("# TYPE healthcare_active_emergency_bypass gauge")
        lines.append(f"healthcare_active_emergency_bypass {active_bypass}")
        return lines


# Global healthcare rate limiter instance
healthcare_rate_limiter: HealthcareRateLimiter | None = None


def get_healthcare_rate_limiter() -> HealthcareRateLimiter:
    """Get global healthcare rate limiter instance"""
    global healthcare_rate_limiter
    if healthcare_rate_limiter is None:
        healthcare_rate_limiter = HealthcareRateLimiter()
    return healthcare_rate_limiter


# Rate limiting middleware
async def apply_healthcare_rate_limit(
    request: Request,
    user: AuthenticatedUser,
    limit_type: RateLimitType = RateLimitType.API_GENERAL,
    is_emergency: bool = False,
) -> Response | None:
    """
    Apply healthcare rate limiting to request

    Returns None if request is allowed, Response with 429 if rate limited
    """
    rate_limiter = get_healthcare_rate_limiter()

    status = await rate_limiter.check_rate_limit(
        user=user,
        limit_type=limit_type,
        request_id=request.headers.get("X-Request-ID"),
        is_emergency=is_emergency,
    )

    if not status.allowed:
        headers = rate_limiter.get_rate_limit_headers(status)

        raise HTTPException(
            status_code=429,  # HTTP 429 Too Many Requests
            detail={
                "error": "Rate limit exceeded",
                "message": f"Too many {limit_type.value} requests",
                "retry_after_seconds": status.retry_after_seconds,
                "healthcare_role": status.user_role.value if status.user_role else None,
                "emergency_bypass_available": user.role
                in [HealthcareRole.DOCTOR, HealthcareRole.NURSE, HealthcareRole.ADMIN],
            },
            headers=headers,
        )

    return None  # Request allowed
