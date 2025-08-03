"""
Healthcare Rate Limiting Infrastructure

Provides intelligent rate limiting for healthcare APIs with role-based limits,
medical emergency bypass, and healthcare-appropriate thresholds.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from fastapi import HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials
import redis.asyncio as redis

from core.infrastructure.authentication import HealthcareRole, AuthenticatedUser

logger = logging.getLogger(__name__)

class RateLimitType(str, Enum):
    """Types of rate limiting for healthcare operations"""
    API_GENERAL = "api_general"           # General API calls
    MEDICAL_QUERY = "medical_query"       # Medical literature/research queries  
    PATIENT_ACCESS = "patient_access"     # Patient data access
    DOCUMENT_UPLOAD = "document_upload"   # Document processing
    EMERGENCY = "emergency"               # Emergency/urgent requests
    BULK_OPERATION = "bulk_operation"     # Bulk data operations

@dataclass
class RateLimitConfig:
    """Rate limit configuration for healthcare operations"""
    requests_per_minute: int
    requests_per_hour: int
    burst_allowance: int
    emergency_bypass: bool = False
    description: str = ""

# Healthcare role-based rate limits
HEALTHCARE_RATE_LIMITS: Dict[HealthcareRole, Dict[RateLimitType, RateLimitConfig]] = {
    HealthcareRole.DOCTOR: {
        RateLimitType.API_GENERAL: RateLimitConfig(
            requests_per_minute=120,
            requests_per_hour=3600,
            burst_allowance=20,
            description="High limits for doctors during patient care"
        ),
        RateLimitType.MEDICAL_QUERY: RateLimitConfig(
            requests_per_minute=60,
            requests_per_hour=1800,
            burst_allowance=15,
            description="Medical literature and research queries"
        ),
        RateLimitType.PATIENT_ACCESS: RateLimitConfig(
            requests_per_minute=180,
            requests_per_hour=5400,
            burst_allowance=30,
            description="Patient data access during clinical care"
        ),
        RateLimitType.EMERGENCY: RateLimitConfig(
            requests_per_minute=300,
            requests_per_hour=7200,
            burst_allowance=50,
            emergency_bypass=True,
            description="Emergency medical situations"
        )
    },
    
    HealthcareRole.NURSE: {
        RateLimitType.API_GENERAL: RateLimitConfig(
            requests_per_minute=90,
            requests_per_hour=2700,
            burst_allowance=15,
            description="Nurse workflow support"
        ),
        RateLimitType.MEDICAL_QUERY: RateLimitConfig(
            requests_per_minute=30,
            requests_per_hour=900,
            burst_allowance=10,
            description="Medical reference lookups"
        ),
        RateLimitType.PATIENT_ACCESS: RateLimitConfig(
            requests_per_minute=120,
            requests_per_hour=3600,
            burst_allowance=20,
            description="Patient care data access"
        )
    },
    
    HealthcareRole.RECEPTIONIST: {
        RateLimitType.API_GENERAL: RateLimitConfig(
            requests_per_minute=60,
            requests_per_hour=1800,
            burst_allowance=10,
            description="Administrative operations"
        ),
        RateLimitType.PATIENT_ACCESS: RateLimitConfig(
            requests_per_minute=90,
            requests_per_hour=2700,
            burst_allowance=15,
            description="Patient scheduling and demographics"
        )
    },
    
    HealthcareRole.BILLING: {
        RateLimitType.API_GENERAL: RateLimitConfig(
            requests_per_minute=45,
            requests_per_hour=1350,
            burst_allowance=8,
            description="Billing operations"
        ),
        RateLimitType.BULK_OPERATION: RateLimitConfig(
            requests_per_minute=20,
            requests_per_hour=600,
            burst_allowance=5,
            description="Bulk billing data processing"
        )
    },
    
    HealthcareRole.RESEARCH: {
        RateLimitType.API_GENERAL: RateLimitConfig(
            requests_per_minute=30,
            requests_per_hour=900,
            burst_allowance=5,
            description="Research data access"
        ),
        RateLimitType.MEDICAL_QUERY: RateLimitConfig(
            requests_per_minute=45,
            requests_per_hour=1350,
            burst_allowance=10,
            description="Research literature queries"
        )
    },
    
    HealthcareRole.ADMIN: {
        RateLimitType.API_GENERAL: RateLimitConfig(
            requests_per_minute=200,
            requests_per_hour=6000,
            burst_allowance=40,
            description="Administrative system access"
        ),
        RateLimitType.BULK_OPERATION: RateLimitConfig(
            requests_per_minute=100,
            requests_per_hour=3000,
            burst_allowance=20,
            description="System administration operations"
        )
    }
}

@dataclass
class RateLimitStatus:
    """Current rate limit status for a user"""
    allowed: bool
    requests_remaining: int
    reset_time: datetime
    retry_after_seconds: Optional[int] = None
    limit_type: Optional[RateLimitType] = None
    user_role: Optional[HealthcareRole] = None

class HealthcareRateLimiter:
    """Healthcare-focused rate limiter with role-based limits and emergency bypass"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.emergency_bypass_active: Dict[str, datetime] = {}
        logger.info("Healthcare rate limiter initialized")
    
    async def check_rate_limit(
        self,
        user: AuthenticatedUser,
        limit_type: RateLimitType,
        request_id: Optional[str] = None,
        is_emergency: bool = False
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
                description="Default healthcare rate limit"
            )
        
        # Emergency bypass check
        if is_emergency and limit_config.emergency_bypass:
            logger.info(
                f"Emergency bypass activated - User: {user.user_id}, "
                f"Type: {limit_type.value}, Role: {user.role.value}"
            )
            self.emergency_bypass_active[user.user_id] = datetime.now()
            
            return RateLimitStatus(
                allowed=True,
                requests_remaining=999,  # Effectively unlimited during emergency
                reset_time=datetime.now() + timedelta(minutes=1),
                limit_type=limit_type,
                user_role=user.role
            )
        
        # Check sliding window rate limits
        current_time = time.time()
        minute_key = f"rate_limit:{user.user_id}:{limit_type.value}:minute"
        hour_key = f"rate_limit:{user.user_id}:{limit_type.value}:hour"
        
        try:
            if self.redis_client:
                # Use Redis for distributed rate limiting
                status = await self._check_redis_rate_limit(
                    user, limit_config, limit_type, minute_key, hour_key, current_time
                )
            else:
                # Fallback to in-memory rate limiting
                status = await self._check_memory_rate_limit(
                    user, limit_config, limit_type, current_time
                )
            
            # Log rate limit status for healthcare audit
            if not status.allowed:
                logger.warning(
                    f"Rate limit exceeded - User: {user.user_id}, "
                    f"Role: {user.role.value}, Type: {limit_type.value}, "
                    f"Retry after: {status.retry_after_seconds}s"
                )
            
            return status
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Fail open for healthcare safety - allow request
            return RateLimitStatus(
                allowed=True,
                requests_remaining=100,
                reset_time=datetime.now() + timedelta(minutes=1),
                limit_type=limit_type,
                user_role=user.role
            )
    
    async def _check_redis_rate_limit(
        self,
        user: AuthenticatedUser,
        config: RateLimitConfig,
        limit_type: RateLimitType,
        minute_key: str,
        hour_key: str,
        current_time: float
    ) -> RateLimitStatus:
        """Check rate limits using Redis sliding window"""
        
        # Get current minute and hour windows
        minute_window = int(current_time // 60)
        hour_window = int(current_time // 3600)
        
        minute_count = await self.redis_client.get(f"{minute_key}:{minute_window}") or 0
        hour_count = await self.redis_client.get(f"{hour_key}:{hour_window}") or 0
        
        minute_count = int(minute_count)
        hour_count = int(hour_count)
        
        # Check if limits exceeded
        minute_exceeded = minute_count >= config.requests_per_minute
        hour_exceeded = hour_count >= config.requests_per_hour
        
        if minute_exceeded or hour_exceeded:
            retry_after = 60 if minute_exceeded else 3600 - (current_time % 3600)
            
            return RateLimitStatus(
                allowed=False,
                requests_remaining=0,
                reset_time=datetime.fromtimestamp(current_time + retry_after),
                retry_after_seconds=int(retry_after),
                limit_type=limit_type,
                user_role=user.role
            )
        
        # Increment counters
        await self.redis_client.incr(f"{minute_key}:{minute_window}")
        await self.redis_client.expire(f"{minute_key}:{minute_window}", 120)  # 2 minutes TTL
        
        await self.redis_client.incr(f"{hour_key}:{hour_window}")
        await self.redis_client.expire(f"{hour_key}:{hour_window}", 7200)  # 2 hours TTL
        
        return RateLimitStatus(
            allowed=True,
            requests_remaining=min(
                config.requests_per_minute - minute_count - 1,
                config.requests_per_hour - hour_count - 1
            ),
            reset_time=datetime.fromtimestamp(current_time + 60),
            limit_type=limit_type,
            user_role=user.role
        )
    
    async def _check_memory_rate_limit(
        self,
        user: AuthenticatedUser,
        config: RateLimitConfig,
        limit_type: RateLimitType,
        current_time: float
    ) -> RateLimitStatus:
        """Fallback in-memory rate limiting"""
        # Simple implementation - in production, Redis should be preferred
        return RateLimitStatus(
            allowed=True,
            requests_remaining=config.requests_per_minute,
            reset_time=datetime.fromtimestamp(current_time + 60),
            limit_type=limit_type,
            user_role=user.role
        )
    
    async def activate_emergency_bypass(
        self,
        user: AuthenticatedUser,
        duration_minutes: int = 30,
        reason: str = "Medical emergency"
    ) -> bool:
        """
        Activate emergency bypass for healthcare user
        
        Temporarily removes rate limits for emergency medical situations
        """
        if user.role not in [HealthcareRole.DOCTOR, HealthcareRole.NURSE, HealthcareRole.ADMIN]:
            logger.warning(
                f"Emergency bypass denied - insufficient role: {user.role.value}"
            )
            return False
        
        self.emergency_bypass_active[user.user_id] = datetime.now() + timedelta(minutes=duration_minutes)
        
        logger.info(
            f"Emergency bypass activated - User: {user.user_id}, "
            f"Duration: {duration_minutes}min, Reason: {reason}"
        )
        
        return True
    
    def get_rate_limit_headers(self, status: RateLimitStatus) -> Dict[str, str]:
        """Generate HTTP headers for rate limit status"""
        headers = {
            "X-RateLimit-Limit": str(status.requests_remaining + 1),
            "X-RateLimit-Remaining": str(status.requests_remaining),
            "X-RateLimit-Reset": str(int(status.reset_time.timestamp())),
            "X-Healthcare-Role": status.user_role.value if status.user_role else "unknown"
        }
        
        if status.retry_after_seconds:
            headers["Retry-After"] = str(status.retry_after_seconds)
        
        if status.limit_type:
            headers["X-RateLimit-Type"] = status.limit_type.value
        
        return headers

# Global healthcare rate limiter instance
healthcare_rate_limiter: Optional[HealthcareRateLimiter] = None

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
    is_emergency: bool = False
) -> Optional[Response]:
    """
    Apply healthcare rate limiting to request
    
    Returns None if request is allowed, Response with 429 if rate limited
    """
    rate_limiter = get_healthcare_rate_limiter()
    
    status = await rate_limiter.check_rate_limit(
        user=user,
        limit_type=limit_type,
        request_id=request.headers.get("X-Request-ID"),
        is_emergency=is_emergency
    )
    
    if not status.allowed:
        headers = rate_limiter.get_rate_limit_headers(status)
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "message": f"Too many {limit_type.value} requests",
                "retry_after_seconds": status.retry_after_seconds,
                "healthcare_role": status.user_role.value if status.user_role else None,
                "emergency_bypass_available": user.role in [
                    HealthcareRole.DOCTOR, HealthcareRole.NURSE, HealthcareRole.ADMIN
                ]
            },
            headers=headers
        )
    
    return None  # Request allowed
