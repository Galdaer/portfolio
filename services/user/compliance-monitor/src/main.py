#!/usr/bin/env python3
"""
HIPAA Compliance Monitor Service

Tracks audit events, detects violations, and generates compliance reports
for the Intelluxe AI healthcare system.
"""

import os
import uuid
from datetime import datetime, timedelta

import asyncpg
import redis.asyncio as redis
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from models.compliance_models import (
    AuditEvent,
    AuditLogRequest,
    ComplianceDashboard,
    ComplianceQuery,
    ComplianceReport,
    ComplianceViolation,
    MonitoringRule,
    ViolationReportRequest,
    ViolationSeverity,
)


class ComplianceMonitor:
    def __init__(self):
        self.app = FastAPI(
            title="HIPAA Compliance Monitor",
            description="Audit tracking and compliance monitoring for healthcare AI system",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc",
        )
        self.db_pool: asyncpg.Pool | None = None
        self.redis_client: redis.Redis | None = None
        self.monitoring_rules: dict[str, MonitoringRule] = {}
        self.setup_routes()
        self.setup_middleware()

    def setup_middleware(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def setup_routes(self):

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            try:
                if self.db_pool:
                    async with self.db_pool.acquire() as conn:
                        await conn.fetchval("SELECT 1")

                if self.redis_client:
                    await self.redis_client.ping()

                return {
                    "status": "healthy",
                    "timestamp": datetime.utcnow(),
                    "service": "compliance-monitor",
                    "version": "1.0.0",
                }
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                return {"status": "unhealthy", "error": str(e)}

        @self.app.post("/audit/log")
        async def log_audit_event(request: AuditLogRequest):
            """Log a new audit event"""
            try:
                event = AuditEvent(
                    event_id=str(uuid.uuid4()),
                    event_type=request.event_type,
                    user_id=request.user_id,
                    session_id=request.session_id,
                    service_name=request.service_name,
                    action_performed=request.action_performed,
                    resource_accessed=request.resource_accessed,
                    request_details=request.request_details,
                    response_status=request.response_status,
                    processing_time_ms=request.processing_time_ms,
                    phi_detected=request.phi_detected,
                    ip_address=request.ip_address,
                    user_agent=request.user_agent,
                )

                event_id = await self.store_audit_event(event)
                await self.check_compliance_rules(event)

                return {
                    "event_id": event_id,
                    "status": "logged",
                    "timestamp": event.timestamp,
                }
            except Exception as e:
                logger.error(f"Failed to log audit event: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/violations/report")
        async def report_violation(request: ViolationReportRequest):
            """Report a compliance violation"""
            try:
                violation = ComplianceViolation(
                    violation_id=str(uuid.uuid4()),
                    violation_type=request.violation_type,
                    severity=request.severity,
                    service_name=request.service_name,
                    description=request.description,
                    affected_resources=request.affected_resources,
                    user_id=request.user_id,
                    session_id=request.session_id,
                    remediation_steps=request.remediation_steps,
                )

                violation_id = await self.store_violation(violation)
                await self.alert_on_violation(violation)

                return {
                    "violation_id": violation_id,
                    "status": "reported",
                    "severity": violation.severity,
                    "timestamp": violation.detected_at,
                }
            except Exception as e:
                logger.error(f"Failed to report violation: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/violations", response_model=list[ComplianceViolation])
        async def get_violations(
            status: str | None = Query("open"),
            severity: ViolationSeverity | None = Query(None),
            service: str | None = Query(None),
            limit: int = Query(100, le=1000),
        ):
            """Get compliance violations with filters"""
            try:
                return await self.get_filtered_violations(status, severity, service, limit)
            except Exception as e:
                logger.error(f"Failed to get violations: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/audit/events", response_model=list[AuditEvent])
        async def get_audit_events(query: ComplianceQuery = Depends()):
            """Get audit events based on query parameters"""
            try:
                return await self.query_audit_events(query)
            except Exception as e:
                logger.error(f"Failed to get audit events: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/reports/generate")
        async def generate_report(
            report_type: str = Query(...),
            period_days: int = Query(30, ge=1, le=365),
        ):
            """Generate compliance report"""
            try:
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=period_days)

                return await self.generate_compliance_report(
                    report_type, start_date, end_date,
                )

            except Exception as e:
                logger.error(f"Failed to generate report: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/dashboard", response_model=ComplianceDashboard)
        async def get_dashboard():
            """Get real-time compliance dashboard"""
            try:
                return await self.get_compliance_dashboard()
            except Exception as e:
                logger.error(f"Failed to get dashboard: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/rules/add")
        async def add_monitoring_rule(rule: MonitoringRule):
            """Add a new monitoring rule"""
            try:
                await self.add_monitoring_rule(rule)
                return {
                    "rule_id": rule.rule_id,
                    "status": "added",
                    "enabled": rule.enabled,
                }
            except Exception as e:
                logger.error(f"Failed to add monitoring rule: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.put("/violations/{violation_id}/resolve")
        async def resolve_violation(violation_id: str, resolution_notes: str):
            """Resolve a compliance violation"""
            try:
                await self.resolve_violation(violation_id, resolution_notes)
                return {
                    "violation_id": violation_id,
                    "status": "resolved",
                    "resolved_at": datetime.utcnow(),
                }
            except Exception as e:
                logger.error(f"Failed to resolve violation: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    async def startup(self):
        """Initialize database connections and monitoring rules"""
        try:
            # Initialize database connection
            postgres_url = os.getenv("POSTGRES_URL")
            if not postgres_url:
                raise ValueError("POSTGRES_URL environment variable not set")

            self.db_pool = await asyncpg.create_pool(postgres_url, min_size=5, max_size=20)
            await self.create_tables()

            # Initialize Redis connection
            redis_url = os.getenv("REDIS_URL", "redis://172.20.0.12:6379")
            self.redis_client = redis.from_url(redis_url)

            # Load monitoring rules
            await self.load_monitoring_rules()

            logger.info("Compliance Monitor service started successfully")

        except Exception as e:
            logger.error(f"Failed to start Compliance Monitor: {e}")
            raise

    async def shutdown(self):
        """Clean up resources"""
        if self.db_pool:
            await self.db_pool.close()
        if self.redis_client:
            await self.redis_client.close()

    async def create_tables(self):
        """Create database tables if they don't exist"""
        async with self.db_pool.acquire() as conn:
            # Audit events table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id VARCHAR PRIMARY KEY,
                    event_type VARCHAR NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    user_id VARCHAR,
                    session_id VARCHAR,
                    service_name VARCHAR NOT NULL,
                    resource_accessed VARCHAR,
                    action_performed VARCHAR NOT NULL,
                    ip_address VARCHAR,
                    user_agent TEXT,
                    request_details JSONB DEFAULT '{}',
                    response_status INTEGER,
                    processing_time_ms INTEGER,
                    phi_detected BOOLEAN DEFAULT FALSE,
                    compliance_tags TEXT[],
                    metadata JSONB DEFAULT '{}'
                )
            """)

            # Compliance violations table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS compliance_violations (
                    violation_id VARCHAR PRIMARY KEY,
                    violation_type VARCHAR NOT NULL,
                    severity VARCHAR NOT NULL,
                    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    service_name VARCHAR NOT NULL,
                    description TEXT NOT NULL,
                    affected_resources TEXT[],
                    user_id VARCHAR,
                    session_id VARCHAR,
                    remediation_required BOOLEAN DEFAULT TRUE,
                    remediation_steps TEXT[],
                    status VARCHAR DEFAULT 'open',
                    resolution_notes TEXT,
                    resolved_at TIMESTAMP WITH TIME ZONE,
                    related_events TEXT[],
                    compliance_impact JSONB DEFAULT '{}'
                )
            """)

            # Monitoring rules table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS monitoring_rules (
                    rule_id VARCHAR PRIMARY KEY,
                    rule_name VARCHAR NOT NULL,
                    description TEXT,
                    rule_type VARCHAR NOT NULL,
                    enabled BOOLEAN DEFAULT TRUE,
                    conditions JSONB NOT NULL,
                    violation_type VARCHAR NOT NULL,
                    severity VARCHAR NOT NULL,
                    threshold_values JSONB DEFAULT '{}',
                    time_window_minutes INTEGER DEFAULT 60,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    last_modified TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    last_triggered TIMESTAMP WITH TIME ZONE,
                    trigger_count INTEGER DEFAULT 0
                )
            """)

    async def store_audit_event(self, event: AuditEvent) -> str:
        """Store audit event in database"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO audit_events (
                    event_id, event_type, timestamp, user_id, session_id,
                    service_name, resource_accessed, action_performed,
                    ip_address, user_agent, request_details, response_status,
                    processing_time_ms, phi_detected, compliance_tags, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
            """,
                event.event_id, event.event_type.value, event.timestamp,
                event.user_id, event.session_id, event.service_name,
                event.resource_accessed, event.action_performed,
                event.ip_address, event.user_agent, event.request_details,
                event.response_status, event.processing_time_ms,
                event.phi_detected, event.compliance_tags, event.metadata,
            )

            # Cache recent events in Redis
            await self.redis_client.lpush(
                f"recent_events:{event.service_name}",
                event.model_dump_json(),
            )
            await self.redis_client.ltrim(f"recent_events:{event.service_name}", 0, 100)

            return event.event_id

    async def store_violation(self, violation: ComplianceViolation) -> str:
        """Store compliance violation in database"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO compliance_violations (
                    violation_id, violation_type, severity, detected_at,
                    service_name, description, affected_resources,
                    user_id, session_id, remediation_required,
                    remediation_steps, status, compliance_impact
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            """,
                violation.violation_id, violation.violation_type.value,
                violation.severity.value, violation.detected_at,
                violation.service_name, violation.description,
                violation.affected_resources, violation.user_id,
                violation.session_id, violation.remediation_required,
                violation.remediation_steps, violation.status,
                violation.compliance_impact,
            )

            return violation.violation_id

    async def check_compliance_rules(self, event: AuditEvent):
        """Check event against monitoring rules"""
        for rule in self.monitoring_rules.values():
            if not rule.enabled:
                continue

            try:
                if await self.evaluate_rule(rule, event):
                    await self.trigger_rule_violation(rule, event)
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.rule_id}: {e}")

    async def evaluate_rule(self, rule: MonitoringRule, event: AuditEvent) -> bool:
        """Evaluate if an event triggers a monitoring rule"""
        conditions = rule.conditions

        # Simple pattern matching - can be extended
        if "event_type" in conditions:
            if event.event_type.value not in conditions["event_type"]:
                return False

        if "phi_detected" in conditions:
            if event.phi_detected != conditions["phi_detected"]:
                return False

        if "failed_response" in conditions and conditions["failed_response"] and (
            not event.response_status or event.response_status < 400
        ):
            return False

        # Time-based threshold checks
        if rule.rule_type == "threshold":
            return await self.check_threshold_rule(rule, event)

        return True

    async def check_threshold_rule(self, rule: MonitoringRule, event: AuditEvent) -> bool:
        """Check threshold-based rules"""
        threshold_values = rule.threshold_values
        time_window = timedelta(minutes=rule.time_window_minutes)
        since = datetime.utcnow() - time_window

        async with self.db_pool.acquire() as conn:
            if "max_events_per_user" in threshold_values and event.user_id:
                count = await conn.fetchval("""
                    SELECT COUNT(*) FROM audit_events
                    WHERE user_id = $1 AND timestamp > $2
                """, event.user_id, since)

                if count >= threshold_values["max_events_per_user"]:
                    return True

        return False

    async def trigger_rule_violation(self, rule: MonitoringRule, event: AuditEvent):
        """Trigger a violation when a rule is matched"""
        violation = ComplianceViolation(
            violation_id=str(uuid.uuid4()),
            violation_type=rule.violation_type,
            severity=rule.severity,
            service_name=event.service_name,
            description=f"Rule '{rule.rule_name}' triggered by event {event.event_id}",
            related_events=[event.event_id],
            user_id=event.user_id,
            session_id=event.session_id,
            compliance_impact={
                "rule_id": rule.rule_id,
                "trigger_event": event.event_id,
                "automatic_detection": True,
            },
        )

        await self.store_violation(violation)
        await self.update_rule_trigger_count(rule.rule_id)

    async def update_rule_trigger_count(self, rule_id: str):
        """Update rule trigger count"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE monitoring_rules
                SET trigger_count = trigger_count + 1,
                    last_triggered = NOW()
                WHERE rule_id = $1
            """, rule_id)

    async def alert_on_violation(self, violation: ComplianceViolation):
        """Send alerts for high-severity violations"""
        if violation.severity in [ViolationSeverity.HIGH, ViolationSeverity.CRITICAL]:
            # Store alert in Redis for real-time notifications
            alert_data = {
                "violation_id": violation.violation_id,
                "type": violation.violation_type.value,
                "severity": violation.severity.value,
                "service": violation.service_name,
                "timestamp": violation.detected_at.isoformat(),
            }

            await self.redis_client.lpush("compliance_alerts", str(alert_data))
            await self.redis_client.ltrim("compliance_alerts", 0, 50)

    async def get_filtered_violations(
        self,
        status: str | None,
        severity: ViolationSeverity | None,
        service: str | None,
        limit: int,
    ) -> list[ComplianceViolation]:
        """Get violations with filters"""
        query = "SELECT * FROM compliance_violations WHERE 1=1"
        params = []
        param_count = 0

        if status:
            param_count += 1
            query += f" AND status = ${param_count}"
            params.append(status)

        if severity:
            param_count += 1
            query += f" AND severity = ${param_count}"
            params.append(severity.value)

        if service:
            param_count += 1
            query += f" AND service_name = ${param_count}"
            params.append(service)

        query += f" ORDER BY detected_at DESC LIMIT ${param_count + 1}"
        params.append(limit)

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [ComplianceViolation(**dict(row)) for row in rows]

    async def query_audit_events(self, query: ComplianceQuery) -> list[AuditEvent]:
        """Query audit events based on criteria"""
        sql = "SELECT * FROM audit_events WHERE timestamp BETWEEN $1 AND $2"
        params = [query.start_date, query.end_date]
        param_count = 2

        if query.event_types:
            param_count += 1
            event_types = [et.value for et in query.event_types]
            sql += f" AND event_type = ANY(${param_count})"
            params.append(event_types)

        if query.service_names:
            param_count += 1
            sql += f" AND service_name = ANY(${param_count})"
            params.append(query.service_names)

        if query.phi_events_only:
            sql += " AND phi_detected = true"

        sql += f" ORDER BY timestamp DESC LIMIT ${param_count + 1} OFFSET ${param_count + 2}"
        params.extend([query.limit, query.offset])

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [AuditEvent(**dict(row)) for row in rows]

    async def generate_compliance_report(
        self,
        report_type: str,
        start_date: datetime,
        end_date: datetime,
    ) -> ComplianceReport:
        """Generate comprehensive compliance report"""
        async with self.db_pool.acquire() as conn:
            # Get basic statistics
            total_events = await conn.fetchval("""
                SELECT COUNT(*) FROM audit_events
                WHERE timestamp BETWEEN $1 AND $2
            """, start_date, end_date)

            total_violations = await conn.fetchval("""
                SELECT COUNT(*) FROM compliance_violations
                WHERE detected_at BETWEEN $1 AND $2
            """, start_date, end_date)

            # Get violations by severity
            severity_stats = await conn.fetch("""
                SELECT severity, COUNT(*) as count
                FROM compliance_violations
                WHERE detected_at BETWEEN $1 AND $2
                GROUP BY severity
            """, start_date, end_date)

            violations_by_severity = {row["severity"]: row["count"] for row in severity_stats}

            # PHI access summary
            phi_events = await conn.fetchval("""
                SELECT COUNT(*) FROM audit_events
                WHERE timestamp BETWEEN $1 AND $2 AND phi_detected = true
            """, start_date, end_date)

            # Calculate compliance score (simplified)
            compliance_score = max(0, 100 - (total_violations * 5))

            return ComplianceReport(
                report_id=str(uuid.uuid4()),
                report_type=report_type,
                period_start=start_date,
                period_end=end_date,
                total_events=total_events,
                total_violations=total_violations,
                violations_by_severity=violations_by_severity,
                phi_access_summary={"phi_events": phi_events},
                compliance_score=compliance_score,
                recommendations=await self.generate_recommendations(violations_by_severity),
            )

    async def generate_recommendations(self, violations_by_severity: dict[str, int]) -> list[str]:
        """Generate compliance recommendations based on violations"""
        recommendations = []

        if violations_by_severity.get("critical", 0) > 0:
            recommendations.append("Immediate attention required for critical violations")

        if violations_by_severity.get("high", 0) > 5:
            recommendations.append("Review access controls and monitoring rules")

        if not recommendations:
            recommendations.append("Compliance posture is acceptable, continue monitoring")

        return recommendations

    async def get_compliance_dashboard(self) -> ComplianceDashboard:
        """Get real-time compliance dashboard data"""
        last_24h = datetime.utcnow() - timedelta(hours=24)

        async with self.db_pool.acquire() as conn:
            # Last 24 hours stats
            events_24h = await conn.fetchval("""
                SELECT COUNT(*) FROM audit_events WHERE timestamp > $1
            """, last_24h)

            violations_24h = await conn.fetchval("""
                SELECT COUNT(*) FROM compliance_violations WHERE detected_at > $1
            """, last_24h)

            # Current open violations
            open_violations_rows = await conn.fetch("""
                SELECT * FROM compliance_violations
                WHERE status = 'open'
                ORDER BY detected_at DESC
                LIMIT 10
            """)

            open_violations = [ComplianceViolation(**dict(row)) for row in open_violations_rows]

            return ComplianceDashboard(
                dashboard_id=str(uuid.uuid4()),
                last_24_hours={
                    "events": events_24h,
                    "violations": violations_24h,
                },
                current_violations=open_violations,
                system_health={"status": "operational"},
                service_status={"compliance-monitor": "healthy"},
            )

    async def load_monitoring_rules(self):
        """Load monitoring rules from database"""
        try:
            async with self.db_pool.acquire() as conn:
                rules_rows = await conn.fetch("""
                    SELECT * FROM monitoring_rules WHERE enabled = true
                """)

                for row in rules_rows:
                    rule = MonitoringRule(**dict(row))
                    self.monitoring_rules[rule.rule_id] = rule

            logger.info(f"Loaded {len(self.monitoring_rules)} monitoring rules")
        except Exception as e:
            logger.error(f"Failed to load monitoring rules: {e}")

    async def add_monitoring_rule(self, rule: MonitoringRule):
        """Add a new monitoring rule"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO monitoring_rules (
                    rule_id, rule_name, description, rule_type, enabled,
                    conditions, violation_type, severity, threshold_values,
                    time_window_minutes
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
                rule.rule_id, rule.rule_name, rule.description,
                rule.rule_type, rule.enabled, rule.conditions,
                rule.violation_type.value, rule.severity.value,
                rule.threshold_values, rule.time_window_minutes,
            )

        self.monitoring_rules[rule.rule_id] = rule

    async def resolve_violation(self, violation_id: str, resolution_notes: str):
        """Resolve a compliance violation"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE compliance_violations
                SET status = 'resolved',
                    resolution_notes = $2,
                    resolved_at = NOW()
                WHERE violation_id = $1
            """, violation_id, resolution_notes)


# Application instance
compliance_monitor = ComplianceMonitor()
app = compliance_monitor.app


@app.on_event("startup")
async def startup_event():
    await compliance_monitor.startup()


@app.on_event("shutdown")
async def shutdown_event():
    await compliance_monitor.shutdown()


def main():
    """Main entry point"""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    logger.remove()
    logger.add(
        "/app/logs/compliance-monitor.log",
        rotation="1 day",
        retention="30 days",
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )
    logger.add(
        lambda msg: print(msg, end=""),
        level=log_level,
        format="{time:HH:mm:ss} | {level: <8} | {message}",
    )

    logger.info("Starting HIPAA Compliance Monitor Service...")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8005,
        log_level=log_level.lower(),
        access_log=True,
    )


if __name__ == "__main__":
    main()
