#!/usr/bin/env python3
"""
Compliance Violation Detector

Detects HIPAA and healthcare compliance violations from audit events and system monitoring.
Implements rule-based detection with configurable thresholds and alert mechanisms.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
import aioredis
import psycopg2
from psycopg2.extras import RealDictCursor

from models.compliance_models import (
    ViolationType, ViolationSeverity, ViolationStatus,
    ComplianceViolation, AuditEvent
)

logger = logging.getLogger(__name__)

class RuleType(Enum):
    PHI_ACCESS = "phi_access"
    FAILED_LOGIN = "failed_login"
    DATA_EXPORT = "data_export"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    BULK_OPERATION = "bulk_operation"
    SUSPICIOUS_QUERY = "suspicious_query"
    AFTER_HOURS_ACCESS = "after_hours_access"
    RAPID_ACCESS = "rapid_access"
    POLICY_VIOLATION = "policy_violation"

@dataclass
class DetectionRule:
    """Configuration for a specific violation detection rule"""
    rule_id: str
    rule_type: RuleType
    name: str
    description: str
    severity: ViolationSeverity
    threshold_count: int = 1
    time_window_minutes: int = 60
    enabled: bool = True
    conditions: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.conditions is None:
            self.conditions = {}

class ViolationDetector:
    """Detects compliance violations from audit events and system metrics"""
    
    def __init__(self, 
                 db_host: str = "localhost",
                 db_port: int = 5432,
                 db_name: str = "intelluxe_public",
                 db_user: str = "intelluxe",
                 db_password: str = "secure_password",
                 redis_url: str = "redis://localhost:6379/2"):
        self.db_host = db_host
        self.db_port = db_port
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password
        self.redis_url = redis_url
        self.redis_client: Optional[aioredis.Redis] = None
        self.detection_rules = self._initialize_rules()
        self.active_violations: Dict[str, ComplianceViolation] = {}
        
    async def initialize(self):
        """Initialize Redis connection and database tables"""
        try:
            self.redis_client = await aioredis.from_url(self.redis_url)
            await self._create_violation_tables()
            logger.info("Violation detector initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize violation detector: {e}")
            raise
    
    def _initialize_rules(self) -> Dict[str, DetectionRule]:
        """Initialize default detection rules"""
        rules = {
            "phi_excessive_access": DetectionRule(
                rule_id="phi_excessive_access",
                rule_type=RuleType.PHI_ACCESS,
                name="Excessive PHI Access",
                description="User accessed PHI records excessively within time window",
                severity=ViolationSeverity.HIGH,
                threshold_count=50,
                time_window_minutes=60,
                conditions={"event_type": "phi_access"}
            ),
            "failed_login_attempts": DetectionRule(
                rule_id="failed_login_attempts",
                rule_type=RuleType.FAILED_LOGIN,
                name="Multiple Failed Login Attempts",
                description="Multiple failed login attempts from same user/IP",
                severity=ViolationSeverity.MEDIUM,
                threshold_count=5,
                time_window_minutes=15,
                conditions={"event_type": "authentication", "success": False}
            ),
            "bulk_data_export": DetectionRule(
                rule_id="bulk_data_export",
                rule_type=RuleType.DATA_EXPORT,
                name="Bulk Data Export",
                description="Large volume of data exported by user",
                severity=ViolationSeverity.CRITICAL,
                threshold_count=1000,
                time_window_minutes=30,
                conditions={"event_type": "data_export"}
            ),
            "unauthorized_table_access": DetectionRule(
                rule_id="unauthorized_table_access",
                rule_type=RuleType.UNAUTHORIZED_ACCESS,
                name="Unauthorized Database Table Access",
                description="Access to restricted database tables",
                severity=ViolationSeverity.HIGH,
                threshold_count=1,
                time_window_minutes=1,
                conditions={"event_type": "database_access", "restricted": True}
            ),
            "after_hours_access": DetectionRule(
                rule_id="after_hours_access",
                rule_type=RuleType.AFTER_HOURS_ACCESS,
                name="After Hours System Access",
                description="System access outside normal business hours",
                severity=ViolationSeverity.MEDIUM,
                threshold_count=10,
                time_window_minutes=60,
                conditions={"event_type": "system_access"}
            ),
            "rapid_patient_access": DetectionRule(
                rule_id="rapid_patient_access",
                rule_type=RuleType.RAPID_ACCESS,
                name="Rapid Patient Record Access",
                description="Unusually rapid access to multiple patient records",
                severity=ViolationSeverity.HIGH,
                threshold_count=20,
                time_window_minutes=5,
                conditions={"event_type": "patient_access"}
            ),
            "suspicious_query_pattern": DetectionRule(
                rule_id="suspicious_query_pattern",
                rule_type=RuleType.SUSPICIOUS_QUERY,
                name="Suspicious Database Query Pattern",
                description="Database queries matching suspicious patterns",
                severity=ViolationSeverity.HIGH,
                threshold_count=1,
                time_window_minutes=1,
                conditions={"event_type": "database_query", "suspicious": True}
            )
        }
        return rules
    
    async def _create_violation_tables(self):
        """Create database tables for storing violations"""
        try:
            conn = psycopg2.connect(
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
                user=self.db_user,
                password=self.db_password
            )
            
            with conn.cursor() as cur:
                # Create violations table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS compliance_violations (
                        violation_id VARCHAR(255) PRIMARY KEY,
                        rule_id VARCHAR(255) NOT NULL,
                        violation_type VARCHAR(50) NOT NULL,
                        severity VARCHAR(20) NOT NULL,
                        status VARCHAR(20) NOT NULL DEFAULT 'open',
                        user_id VARCHAR(255),
                        service_name VARCHAR(100),
                        description TEXT,
                        details JSONB,
                        first_detected_at TIMESTAMP WITH TIME ZONE NOT NULL,
                        last_detected_at TIMESTAMP WITH TIME ZONE NOT NULL,
                        resolved_at TIMESTAMP WITH TIME ZONE,
                        resolution_notes TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
                
                # Create violation events table (for tracking related audit events)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS violation_events (
                        id SERIAL PRIMARY KEY,
                        violation_id VARCHAR(255) REFERENCES compliance_violations(violation_id),
                        audit_event_id VARCHAR(255),
                        event_timestamp TIMESTAMP WITH TIME ZONE,
                        event_data JSONB,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
                
                # Create indexes
                cur.execute("CREATE INDEX IF NOT EXISTS idx_violations_rule_id ON compliance_violations(rule_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_violations_user_id ON compliance_violations(user_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_violations_status ON compliance_violations(status)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_violations_severity ON compliance_violations(severity)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_violations_detected_at ON compliance_violations(first_detected_at)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_violation_events_violation_id ON violation_events(violation_id)")
                
                conn.commit()
                logger.info("Violation detection tables created successfully")
                
        except Exception as e:
            logger.error(f"Failed to create violation tables: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    async def process_audit_event(self, audit_event: AuditEvent) -> List[ComplianceViolation]:
        """Process a single audit event and detect violations"""
        violations = []
        
        for rule in self.detection_rules.values():
            if not rule.enabled:
                continue
                
            if await self._event_matches_rule(audit_event, rule):
                violation = await self._check_violation_threshold(audit_event, rule)
                if violation:
                    violations.append(violation)
                    await self._store_violation(violation, audit_event)
        
        return violations
    
    async def _event_matches_rule(self, event: AuditEvent, rule: DetectionRule) -> bool:
        """Check if audit event matches detection rule conditions"""
        try:
            # Check basic conditions
            for condition_key, condition_value in rule.conditions.items():
                event_value = getattr(event, condition_key, None)
                if event_value != condition_value:
                    return False
            
            # Special rule-specific logic
            if rule.rule_type == RuleType.AFTER_HOURS_ACCESS:
                return self._is_after_hours(event.timestamp)
            elif rule.rule_type == RuleType.SUSPICIOUS_QUERY:
                return self._is_suspicious_query(event.details)
            elif rule.rule_type == RuleType.BULK_OPERATION:
                return self._is_bulk_operation(event.details)
                
            return True
            
        except Exception as e:
            logger.error(f"Error matching event to rule {rule.rule_id}: {e}")
            return False
    
    def _is_after_hours(self, timestamp: datetime) -> bool:
        """Check if timestamp is outside business hours (9 AM - 6 PM)"""
        hour = timestamp.hour
        weekday = timestamp.weekday()  # 0=Monday, 6=Sunday
        
        # Weekend or outside 9 AM - 6 PM
        return weekday >= 5 or hour < 9 or hour >= 18
    
    def _is_suspicious_query(self, details: Dict[str, Any]) -> bool:
        """Detect suspicious database query patterns"""
        query = details.get("query", "").lower()
        suspicious_patterns = [
            "select * from",
            "union all select",
            "information_schema",
            "pg_catalog",
            "drop table",
            "delete from",
            "update.*set.*password",
            "where.*1=1"
        ]
        
        return any(pattern in query for pattern in suspicious_patterns)
    
    def _is_bulk_operation(self, details: Dict[str, Any]) -> bool:
        """Check if operation involves bulk data access"""
        record_count = details.get("record_count", 0)
        return record_count > 100
    
    async def _check_violation_threshold(self, event: AuditEvent, rule: DetectionRule) -> Optional[ComplianceViolation]:
        """Check if event triggers violation based on rule threshold"""
        try:
            # Create cache key for counting events
            cache_key = f"violation_count:{rule.rule_id}:{event.user_id}:{event.service_name}"
            
            # Get current count from Redis
            current_count = await self.redis_client.get(cache_key)
            current_count = int(current_count) if current_count else 0
            
            # Increment count
            current_count += 1
            
            # Set with expiration based on rule time window
            await self.redis_client.setex(
                cache_key, 
                rule.time_window_minutes * 60, 
                current_count
            )
            
            # Check if threshold exceeded
            if current_count >= rule.threshold_count:
                violation_id = f"{rule.rule_id}_{event.user_id}_{int(event.timestamp.timestamp())}"
                
                # Check if we already have an active violation for this pattern
                if violation_id in self.active_violations:
                    # Update existing violation
                    existing = self.active_violations[violation_id]
                    existing.last_detected_at = event.timestamp
                    existing.event_count += 1
                    return existing
                
                # Create new violation
                violation = ComplianceViolation(
                    violation_id=violation_id,
                    rule_id=rule.rule_id,
                    violation_type=ViolationType.HIPAA_VIOLATION,  # Default, could be more specific
                    severity=rule.severity,
                    status=ViolationStatus.OPEN,
                    user_id=event.user_id,
                    service_name=event.service_name,
                    description=f"{rule.name}: {rule.description}",
                    details={
                        "rule_name": rule.name,
                        "threshold_count": rule.threshold_count,
                        "actual_count": current_count,
                        "time_window_minutes": rule.time_window_minutes,
                        "triggering_event": asdict(event)
                    },
                    first_detected_at=event.timestamp,
                    last_detected_at=event.timestamp,
                    event_count=current_count
                )
                
                self.active_violations[violation_id] = violation
                return violation
                
            return None
            
        except Exception as e:
            logger.error(f"Error checking violation threshold for rule {rule.rule_id}: {e}")
            return None
    
    async def _store_violation(self, violation: ComplianceViolation, triggering_event: AuditEvent):
        """Store violation in database"""
        try:
            conn = psycopg2.connect(
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
                user=self.db_user,
                password=self.db_password
            )
            
            with conn.cursor() as cur:
                # Insert or update violation
                cur.execute("""
                    INSERT INTO compliance_violations (
                        violation_id, rule_id, violation_type, severity, status,
                        user_id, service_name, description, details,
                        first_detected_at, last_detected_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (violation_id) DO UPDATE SET
                        last_detected_at = EXCLUDED.last_detected_at,
                        details = EXCLUDED.details,
                        updated_at = NOW()
                """, (
                    violation.violation_id,
                    violation.rule_id,
                    violation.violation_type.value,
                    violation.severity.value,
                    violation.status.value,
                    violation.user_id,
                    violation.service_name,
                    violation.description,
                    json.dumps(violation.details),
                    violation.first_detected_at,
                    violation.last_detected_at
                ))
                
                # Insert related event
                cur.execute("""
                    INSERT INTO violation_events (
                        violation_id, audit_event_id, event_timestamp, event_data
                    ) VALUES (%s, %s, %s, %s)
                """, (
                    violation.violation_id,
                    triggering_event.event_id,
                    triggering_event.timestamp,
                    json.dumps(asdict(triggering_event))
                ))
                
                conn.commit()
                logger.info(f"Stored violation {violation.violation_id}")
                
        except Exception as e:
            logger.error(f"Failed to store violation {violation.violation_id}: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    async def get_active_violations(self, 
                                   severity: Optional[ViolationSeverity] = None,
                                   user_id: Optional[str] = None,
                                   service_name: Optional[str] = None,
                                   limit: int = 100) -> List[ComplianceViolation]:
        """Get active violations with optional filtering"""
        try:
            conn = psycopg2.connect(
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
                user=self.db_user,
                password=self.db_password
            )
            
            conditions = ["status = 'open'"]
            params = []
            
            if severity:
                conditions.append("severity = %s")
                params.append(severity.value)
            
            if user_id:
                conditions.append("user_id = %s")
                params.append(user_id)
            
            if service_name:
                conditions.append("service_name = %s")
                params.append(service_name)
            
            query = f"""
                SELECT violation_id, rule_id, violation_type, severity, status,
                       user_id, service_name, description, details,
                       first_detected_at, last_detected_at, created_at
                FROM compliance_violations
                WHERE {' AND '.join(conditions)}
                ORDER BY first_detected_at DESC
                LIMIT %s
            """
            params.append(limit)
            
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
                
                violations = []
                for row in rows:
                    violation = ComplianceViolation(
                        violation_id=row['violation_id'],
                        rule_id=row['rule_id'],
                        violation_type=ViolationType(row['violation_type']),
                        severity=ViolationSeverity(row['severity']),
                        status=ViolationStatus(row['status']),
                        user_id=row['user_id'],
                        service_name=row['service_name'],
                        description=row['description'],
                        details=row['details'] or {},
                        first_detected_at=row['first_detected_at'],
                        last_detected_at=row['last_detected_at']
                    )
                    violations.append(violation)
                
                return violations
                
        except Exception as e:
            logger.error(f"Failed to get active violations: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    async def resolve_violation(self, 
                               violation_id: str, 
                               resolution_notes: str,
                               resolved_by: str) -> bool:
        """Mark violation as resolved"""
        try:
            conn = psycopg2.connect(
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
                user=self.db_user,
                password=self.db_password
            )
            
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE compliance_violations
                    SET status = 'resolved',
                        resolved_at = NOW(),
                        resolution_notes = %s,
                        updated_at = NOW()
                    WHERE violation_id = %s AND status = 'open'
                """, (resolution_notes, violation_id))
                
                if cur.rowcount > 0:
                    conn.commit()
                    
                    # Remove from active violations cache
                    if violation_id in self.active_violations:
                        del self.active_violations[violation_id]
                    
                    logger.info(f"Resolved violation {violation_id} by {resolved_by}")
                    return True
                else:
                    logger.warning(f"Violation {violation_id} not found or already resolved")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to resolve violation {violation_id}: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    async def get_violation_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get violation statistics for the past N days"""
        try:
            conn = psycopg2.connect(
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
                user=self.db_user,
                password=self.db_password
            )
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Total violations by severity
                cur.execute("""
                    SELECT severity, COUNT(*) as count
                    FROM compliance_violations
                    WHERE first_detected_at >= %s
                    GROUP BY severity
                """, (cutoff_date,))
                severity_stats = {row['severity']: row['count'] for row in cur.fetchall()}
                
                # Total violations by rule
                cur.execute("""
                    SELECT rule_id, COUNT(*) as count
                    FROM compliance_violations
                    WHERE first_detected_at >= %s
                    GROUP BY rule_id
                    ORDER BY count DESC
                    LIMIT 10
                """, (cutoff_date,))
                rule_stats = {row['rule_id']: row['count'] for row in cur.fetchall()}
                
                # Total violations by user
                cur.execute("""
                    SELECT user_id, COUNT(*) as count
                    FROM compliance_violations
                    WHERE first_detected_at >= %s AND user_id IS NOT NULL
                    GROUP BY user_id
                    ORDER BY count DESC
                    LIMIT 10
                """, (cutoff_date,))
                user_stats = {row['user_id']: row['count'] for row in cur.fetchall()}
                
                # Resolution statistics
                cur.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN status = 'resolved' THEN 1 END) as resolved,
                        COUNT(CASE WHEN status = 'open' THEN 1 END) as open
                    FROM compliance_violations
                    WHERE first_detected_at >= %s
                """, (cutoff_date,))
                resolution_stats = dict(cur.fetchone())
                
                return {
                    "period_days": days,
                    "severity_breakdown": severity_stats,
                    "top_violated_rules": rule_stats,
                    "top_violating_users": user_stats,
                    "resolution_status": resolution_stats,
                    "generated_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to get violation statistics: {e}")
            return {}
        finally:
            if conn:
                conn.close()
    
    def add_custom_rule(self, rule: DetectionRule):
        """Add or update a custom detection rule"""
        self.detection_rules[rule.rule_id] = rule
        logger.info(f"Added custom detection rule: {rule.rule_id}")
    
    def disable_rule(self, rule_id: str):
        """Disable a detection rule"""
        if rule_id in self.detection_rules:
            self.detection_rules[rule_id].enabled = False
            logger.info(f"Disabled detection rule: {rule_id}")
    
    def enable_rule(self, rule_id: str):
        """Enable a detection rule"""
        if rule_id in self.detection_rules:
            self.detection_rules[rule_id].enabled = True
            logger.info(f"Enabled detection rule: {rule_id}")
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.redis_client:
            await self.redis_client.close()

if __name__ == "__main__":
    # Test the violation detector
    async def test_detector():
        detector = ViolationDetector()
        await detector.initialize()
        
        # Create test audit event
        test_event = AuditEvent(
            event_id="test_001",
            timestamp=datetime.now(),
            event_type="phi_access",
            user_id="test_user",
            service_name="healthcare-api",
            details={"patient_id": "12345", "record_count": 1},
            ip_address="192.168.1.100"
        )
        
        # Process event
        violations = await detector.process_audit_event(test_event)
        print(f"Detected {len(violations)} violations")
        
        # Get statistics
        stats = await detector.get_violation_statistics(7)
        print(f"Statistics: {json.dumps(stats, indent=2)}")
        
        await detector.cleanup()
    
    asyncio.run(test_detector())