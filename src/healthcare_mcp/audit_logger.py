"""
Healthcare Audit Logger
Comprehensive audit logging for HIPAA compliance and healthcare AI systems
"""

import json
import time
from typing import Dict, Optional, Any
from datetime import datetime, timezone
from dataclasses import dataclass
import hashlib
import uuid
from enum import Enum
from collections import OrderedDict

import psycopg2
from psycopg2.extras import RealDictCursor
import structlog
from fastapi import Request, Response

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


class LRUCacheWithTTL:
    """LRU Cache with TTL support"""
    def __init__(self, max_size: int = 100, ttl: int = 300):
        self.max_size = max_size
        self.ttl = ttl
        self.cache = OrderedDict()

    def get(self, key: str):
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                return value
            else:
                # Expired
                del self.cache[key]
        return None

    def set(self, key: str, value):
        # Remove oldest items if at capacity
        while len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)

        self.cache[key] = (value, time.time())


class AuditEventType(Enum):
    """Types of audit events"""
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    PHI_ACCESS = "phi_access"
    PHI_DETECTION = "phi_detection"
    API_REQUEST = "api_request"
    SYSTEM_ERROR = "system_error"
    SECURITY_VIOLATION = "security_violation"
    COMPLIANCE_CHECK = "compliance_check"

class AuditLevel(Enum):
    """Audit logging levels"""
    BASIC = "basic"
    DETAILED = "detailed"
    COMPREHENSIVE = "comprehensive"

@dataclass
class AuditEvent:
    """Audit event data structure"""
    event_id: str
    timestamp: str
    event_type: AuditEventType
    user_id: Optional[str]
    session_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    resource_accessed: Optional[str]
    action_performed: str
    outcome: str  # success, failure, error
    details: Dict[str, Any]
    phi_involved: bool
    compliance_status: str
    risk_level: str  # low, medium, high, critical

class HealthcareAuditLogger:
    """Healthcare-specific audit logger with HIPAA compliance"""

    def __init__(self, config):
        self.config = config
        self.logger = structlog.get_logger("healthcare_audit")
        self.audit_level = AuditLevel(config.audit_logging_level)

        # Initialize PHI detection cache with proper management
        self._phi_cache = LRUCacheWithTTL(max_size=100, ttl=300)
        self._phi_cache_version = "v1.0"  # Add versioning for cache invalidation

        # Initialize database connection for audit storage
        self._init_audit_database()

        # Create audit tables if they don't exist
        self._create_audit_tables()

    def _init_audit_database(self):
        """Initialize audit database connection"""
        try:
            self.audit_conn = psycopg2.connect(
                host=self.config.postgres_host,
                port=self.config.postgres_port,
                database=self.config.postgres_db,
                user=self.config.postgres_user,
                password=self.config.postgres_password
            )
            self.audit_conn.autocommit = True

            self.logger.info("Audit database connection initialized")

        except Exception as e:
            self.logger.error("Failed to initialize audit database", error=str(e))
            raise

    def _create_audit_tables(self):
        """Create audit tables if they don't exist"""
        try:
            with self.audit_conn.cursor() as cursor:
                # Main audit log table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS healthcare_audit_log (
                        id SERIAL PRIMARY KEY,
                        event_id VARCHAR(255) UNIQUE NOT NULL,
                        timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                        event_type VARCHAR(100) NOT NULL,
                        user_id VARCHAR(255),
                        session_id VARCHAR(255),
                        ip_address INET,
                        user_agent TEXT,
                        resource_accessed TEXT,
                        action_performed TEXT NOT NULL,
                        outcome VARCHAR(50) NOT NULL,
                        details JSONB,
                        phi_involved BOOLEAN DEFAULT FALSE,
                        compliance_status VARCHAR(50),
                        risk_level VARCHAR(20),
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)

                # PHI access log table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS phi_access_log (
                        id SERIAL PRIMARY KEY,
                        event_id VARCHAR(255) NOT NULL,
                        timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                        user_id VARCHAR(255),
                        phi_type VARCHAR(100),
                        access_reason TEXT,
                        data_hash VARCHAR(255),
                        detection_confidence FLOAT,
                        masked_data TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)

                # API request log table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS api_request_log (
                        id SERIAL PRIMARY KEY,
                        event_id VARCHAR(255) NOT NULL,
                        timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                        method VARCHAR(10),
                        endpoint TEXT,
                        status_code INTEGER,
                        processing_time FLOAT,
                        request_size INTEGER,
                        response_size INTEGER,
                        user_id VARCHAR(255),
                        ip_address INET,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)

                # Create indexes for performance
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_audit_timestamp
                    ON healthcare_audit_log(timestamp)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_audit_event_type
                    ON healthcare_audit_log(event_type)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_audit_user_id
                    ON healthcare_audit_log(user_id)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_phi_access_timestamp
                    ON phi_access_log(timestamp)
                """)

            self.logger.info("Audit tables created successfully")

        except Exception as e:
            self.logger.error("Failed to create audit tables", error=str(e))
            raise

    def _generate_event_id(self) -> str:
        """Generate unique event ID"""
        return str(uuid.uuid4())

    def _hash_sensitive_data(self, data: str) -> str:
        """Hash sensitive data for audit trail"""
        return hashlib.sha256(data.encode()).hexdigest()

    def _extract_user_info(self, request: Request) -> Dict[str, Optional[str]]:
        """Extract user information from request"""
        return {
            "ip_address": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "session_id": request.headers.get("x-session-id"),
            "user_id": request.headers.get("x-user-id", "anonymous")
        }

    async def log_audit_event(self, event: AuditEvent):
        """Log audit event to database and structured logs"""
        try:
            # Log to structured logger
            self.logger.info(
                "audit_event",
                event_id=event.event_id,
                event_type=event.event_type.value,
                user_id=event.user_id,
                action=event.action_performed,
                outcome=event.outcome,
                phi_involved=event.phi_involved,
                risk_level=event.risk_level,
                details=event.details
            )

            # Store in database
            with self.audit_conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO healthcare_audit_log
                    (event_id, timestamp, event_type, user_id, session_id, ip_address,
                     user_agent, resource_accessed, action_performed, outcome, details,
                     phi_involved, compliance_status, risk_level)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    event.event_id,
                    event.timestamp,
                    event.event_type.value,
                    event.user_id,
                    event.session_id,
                    event.ip_address,
                    event.user_agent,
                    event.resource_accessed,
                    event.action_performed,
                    event.outcome,
                    json.dumps(event.details),
                    event.phi_involved,
                    event.compliance_status,
                    event.risk_level
                ))

        except Exception as e:
            self.logger.error("Failed to log audit event", error=str(e), event_id=event.event_id)

    async def log_request(self, request: Request, response: Response, processing_time: float):
        """Log API request for audit trail"""
        user_info = self._extract_user_info(request)
        event_id = self._generate_event_id()

        # Determine risk level based on endpoint and method
        risk_level = "low"
        if "patient" in str(request.url).lower():
            risk_level = "medium"
        if request.method in ["POST", "PUT", "DELETE"]:
            risk_level = "medium"

        # Create audit event
        audit_event = AuditEvent(
            event_id=event_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=AuditEventType.API_REQUEST,
            user_id=user_info["user_id"],
            session_id=user_info["session_id"],
            ip_address=user_info["ip_address"],
            user_agent=user_info["user_agent"],
            resource_accessed=str(request.url),
            action_performed=f"{request.method} {request.url.path}",
            outcome="success" if response.status_code < 400 else "failure",
            details={
                "method": request.method,
                "endpoint": str(request.url.path),
                "status_code": response.status_code,
                "processing_time": processing_time,
                "query_params": dict(request.query_params) if self.audit_level == AuditLevel.COMPREHENSIVE else {}
            },
            phi_involved=False,  # Will be updated if PHI is detected
            compliance_status="compliant",
            risk_level=risk_level
        )

        await self.log_audit_event(audit_event)

        # Also log to API request table
        try:
            with self.audit_conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO api_request_log
                    (event_id, timestamp, method, endpoint, status_code, processing_time,
                     user_id, ip_address)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    event_id,
                    datetime.now(timezone.utc),
                    request.method,
                    str(request.url.path),
                    response.status_code,
                    processing_time,
                    user_info["user_id"],
                    user_info["ip_address"]
                ))
        except Exception as e:
            self.logger.error("Failed to log API request", error=str(e))

    async def log_phi_detection(self, request_data: Any, phi_details: Dict[str, Any]):
        """Log PHI detection event"""
        event_id = self._generate_event_id()

        # Hash the data for audit trail
        data_hash = self._hash_sensitive_data(json.dumps(request_data, default=str))

        audit_event = AuditEvent(
            event_id=event_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=AuditEventType.PHI_DETECTION,
            user_id="system",
            session_id=None,
            ip_address=None,
            user_agent=None,
            resource_accessed="phi_detector",
            action_performed="phi_detection",
            outcome="phi_detected",
            details={
                "phi_types": phi_details.get("phi_types", []),
                "confidence_scores": phi_details.get("confidence_scores", []),
                "detection_count": len(phi_details.get("detection_details", [])),
                "data_hash": data_hash
            },
            phi_involved=True,
            compliance_status="requires_review",
            risk_level="high"
        )

        await self.log_audit_event(audit_event)

        # Log to PHI access table
        try:
            with self.audit_conn.cursor() as cursor:
                for detail in phi_details.get("detection_details", []):
                    cursor.execute("""
                        INSERT INTO phi_access_log
                        (event_id, timestamp, phi_type, access_reason, data_hash,
                         detection_confidence, masked_data)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        event_id,
                        datetime.now(timezone.utc),
                        detail.get("type"),
                        "automatic_detection",
                        data_hash,
                        detail.get("confidence"),
                        detail.get("text", "")[:100] + "..." if len(detail.get("text", "")) > 100 else detail.get("text", "")
                    ))
        except Exception as e:
            self.logger.error("Failed to log PHI detection", error=str(e))

    async def _get_cached_phi_result(self, phi_detector, details_str: str):
        """Cache PHI detection results for similar content with version checking"""
        # Create hash of content for caching with version
        content_hash = hashlib.sha256(details_str.encode()).hexdigest()
        cache_key = f"{self._phi_cache_version}_{content_hash}"

        # Check cache
        cached_result = self._phi_cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        # Perform detection and cache result with version
        result = await phi_detector.detect_phi(details_str)
        self._phi_cache.set(cache_key, result)

        return result

    def invalidate_phi_cache(self, new_version: str = None):
        """Invalidate PHI cache when detection rules change"""
        if new_version:
            self._phi_cache_version = new_version
        self._phi_cache.clear()
        self.logger.info(f"PHI cache invalidated, new version: {self._phi_cache_version}")

    async def log_security_violation(self, violation_type: str, details: Dict[str, Any],
                                     user_id: Optional[str] = None):
        """Log security violation with PHI protection"""
        event_id = self._generate_event_id()

        # Use dedicated PHI detection instead of basic string matching
        try:
            from .phi_detection import PHIDetector
            phi_detector = PHIDetector()

            # Check and mask PHI in violation details with caching
            details_str = json.dumps(details, default=str)
            phi_result = await self._get_cached_phi_result(phi_detector, details_str)

            phi_involved = phi_result.phi_detected
            processed_details = details.copy()

            if phi_result.phi_detected:
                # Mask PHI before logging
                self.logger.warning(f"PHI detected in security violation details: {phi_result.phi_types}")
                processed_details["original_masked"] = True
                processed_details["phi_types_detected"] = phi_result.phi_types
                processed_details["masked_content"] = phi_result.masked_text[:500]  # Limit size

                # Remove potentially sensitive original details
                sensitive_keys = ["error_message", "request_data", "response_data", "user_input"]
                for key in sensitive_keys:
                    if key in processed_details:
                        processed_details[key] = "[MASKED - PHI DETECTED]"

        except ImportError:
            # Fallback if PHI detector not available
            self.logger.warning("PHI detector not available for security violation logging")
            phi_involved = details.get("phi_involved", False)
            processed_details = details
        except Exception as e:
            # Error in PHI detection - err on side of caution
            self.logger.error(f"Error in PHI detection for security violation: {e}")
            phi_involved = True  # Assume PHI present to be safe
            processed_details = {"error": "PHI detection failed", "original_details_masked": True}

        audit_event = AuditEvent(
            event_id=event_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=AuditEventType.SECURITY_VIOLATION,
            user_id=user_id or "unknown",
            session_id=details.get("session_id"),
            ip_address=details.get("ip_address"),
            user_agent=details.get("user_agent"),
            resource_accessed=details.get("resource"),
            action_performed=violation_type,
            outcome="security_violation",
            details=processed_details,
            phi_involved=phi_involved,
            compliance_status="violation",
            risk_level="critical"
        )

        await self.log_audit_event(audit_event)

    def get_audit_summary(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get audit summary for a date range"""
        try:
            with self.audit_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Get event counts by type
                cursor.execute("""
                    SELECT event_type, COUNT(*) as count
                    FROM healthcare_audit_log
                    WHERE timestamp BETWEEN %s AND %s
                    GROUP BY event_type
                """, (start_date, end_date))
                event_counts = dict(cursor.fetchall())

                # Get PHI access counts
                cursor.execute("""
                    SELECT COUNT(*) as phi_access_count
                    FROM healthcare_audit_log
                    WHERE timestamp BETWEEN %s AND %s AND phi_involved = true
                """, (start_date, end_date))
                phi_access_count = cursor.fetchone()["phi_access_count"]

                # Get security violations
                cursor.execute("""
                    SELECT COUNT(*) as violation_count
                    FROM healthcare_audit_log
                    WHERE timestamp BETWEEN %s AND %s AND event_type = %s
                """, (start_date, end_date, AuditEventType.SECURITY_VIOLATION.value))
                violation_count = cursor.fetchone()["violation_count"]

                return {
                    "period": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat()
                    },
                    "event_counts": event_counts,
                    "phi_access_count": phi_access_count,
                    "security_violations": violation_count,
                    "compliance_status": "compliant" if violation_count == 0 else "violations_detected"
                }

        except Exception as e:
            self.logger.error("Failed to generate audit summary", error=str(e))
            return {"error": "Failed to generate audit summary"}

    def close(self):
        """Close audit database connection"""
        if hasattr(self, 'audit_conn'):
            self.audit_conn.close()

# Example usage
if __name__ == "__main__":
    # This would be used in testing
    pass
