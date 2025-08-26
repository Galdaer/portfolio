"""
Audit Tracking System for Compliance Monitoring
Tracks all audit events across healthcare services
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

import aiofiles
from models.compliance_models import (
    AuditEvent,
    AuditEventType,
    AuditLogRequest,
    ComplianceDashboard,
    ComplianceQuery,
)

logger = logging.getLogger(__name__)


class AuditTracker:
    """Comprehensive audit tracking system for healthcare compliance"""
    
    def __init__(self, storage_backend=None, redis_client=None):
        self.storage_backend = storage_backend  # Database connection
        self.redis_client = redis_client  # Real-time caching
        
        # Audit configuration
        self.retention_days = 2555  # 7 years for HIPAA compliance
        self.batch_size = 100
        self.flush_interval_seconds = 30
        
        # In-memory buffer for high-frequency events
        self.event_buffer = []
        self.buffer_lock = asyncio.Lock()
        
        # Event categorization for compliance
        self.phi_related_events = {
            AuditEventType.PHI_ACCESS,
            AuditEventType.PHI_MODIFICATION,
            AuditEventType.PHI_EXPORT,
            AuditEventType.INSURANCE_VERIFICATION,
            AuditEventType.CLAIM_SUBMISSION
        }
        
        # Critical events that require immediate attention
        self.critical_events = {
            AuditEventType.FAILED_LOGIN,
            AuditEventType.ERROR_OCCURRED,
            AuditEventType.SYSTEM_CONFIG_CHANGE
        }
    
    async def log_audit_event(
        self,
        request: AuditLogRequest,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> str:
        """Log an audit event"""
        
        event_id = f"audit_{uuid4().hex[:8]}"
        
        # Create audit event
        audit_event = AuditEvent(
            event_id=event_id,
            event_type=request.event_type,
            user_id=request.user_id,
            session_id=request.session_id,
            service_name=request.service_name,
            resource_accessed=request.resource_accessed,
            action_performed=request.action_performed,
            ip_address=client_ip or request.ip_address,
            user_agent=user_agent or request.user_agent,
            request_details=request.request_details,
            response_status=request.response_status,
            processing_time_ms=request.processing_time_ms,
            phi_detected=request.phi_detected,
            compliance_tags=self._generate_compliance_tags(request)
        )
        
        # Add to buffer for batch processing
        async with self.buffer_lock:
            self.event_buffer.append(audit_event)
            
            # Flush if buffer is full
            if len(self.event_buffer) >= self.batch_size:
                await self._flush_events()
        
        # Handle critical events immediately
        if request.event_type in self.critical_events:
            await self._handle_critical_event(audit_event)
        
        # Cache recent event for real-time dashboard
        if self.redis_client:
            await self._cache_recent_event(audit_event)
        
        logger.info(f"Logged audit event {event_id}: {request.event_type} from {request.service_name}")
        return event_id
    
    async def query_audit_events(
        self,
        query: ComplianceQuery
    ) -> Dict[str, Any]:
        """Query audit events based on criteria"""
        
        # Build query conditions
        conditions = []
        params = []
        
        conditions.append("timestamp BETWEEN %s AND %s")
        params.extend([query.start_date, query.end_date])
        
        if query.event_types:
            event_type_placeholders = ','.join(['%s'] * len(query.event_types))
            conditions.append(f"event_type IN ({event_type_placeholders})")
            params.extend([et.value for et in query.event_types])
        
        if query.service_names:
            service_placeholders = ','.join(['%s'] * len(query.service_names))
            conditions.append(f"service_name IN ({service_placeholders})")
            params.extend(query.service_names)
        
        if query.user_ids:
            user_placeholders = ','.join(['%s'] * len(query.user_ids))
            conditions.append(f"user_id IN ({user_placeholders})")
            params.extend(query.user_ids)
        
        if query.phi_events_only:
            phi_types = [et.value for et in self.phi_related_events]
            phi_placeholders = ','.join(['%s'] * len(phi_types))
            conditions.append(f"event_type IN ({phi_placeholders})")
            params.extend(phi_types)
        
        # Execute query (mock implementation)
        events = await self._execute_audit_query(conditions, params, query.limit, query.offset)
        
        # Calculate summary statistics
        total_events = await self._count_audit_events(conditions, params)
        
        return {
            "query_id": f"query_{uuid4().hex[:8]}",
            "total_events": total_events,
            "returned_events": len(events),
            "events": [event.dict() for event in events],
            "query_executed_at": datetime.utcnow().isoformat(),
            "query_parameters": query.dict()
        }
    
    async def generate_compliance_dashboard(self) -> ComplianceDashboard:
        """Generate real-time compliance dashboard"""
        
        dashboard_id = f"dashboard_{uuid4().hex[:8]}"
        now = datetime.utcnow()
        last_24_hours_start = now - timedelta(hours=24)
        
        # Get last 24 hours statistics
        last_24h_stats = await self._get_24h_statistics(last_24_hours_start, now)
        
        # Get current open violations
        current_violations = await self._get_current_violations()
        
        # Get system health indicators
        system_health = await self._get_system_health_indicators()
        
        # Get compliance trends
        compliance_trends = await self._get_compliance_trends()
        
        # Get top alerts
        top_alerts = await self._get_top_alerts()
        
        # Get service status
        service_status = await self._get_service_status()
        
        # Get recent events
        recent_events = await self._get_recent_events(limit=20)
        
        # Calculate risk indicators
        risk_indicators = await self._calculate_risk_indicators(last_24h_stats)
        
        return ComplianceDashboard(
            dashboard_id=dashboard_id,
            last_24_hours=last_24h_stats,
            current_violations=current_violations,
            system_health=system_health,
            compliance_trends=compliance_trends,
            top_alerts=top_alerts,
            service_status=service_status,
            recent_events=recent_events,
            risk_indicators=risk_indicators
        )
    
    async def export_audit_trail(
        self,
        start_date: datetime,
        end_date: datetime,
        format_type: str = "json"
    ) -> str:
        """Export audit trail for compliance reporting"""
        
        export_id = f"export_{uuid4().hex[:8]}"
        
        # Query all events in date range
        query = ComplianceQuery(
            start_date=start_date,
            end_date=end_date,
            limit=10000  # Large limit for export
        )
        
        result = await self.query_audit_events(query)
        
        # Generate export file
        export_filename = f"audit_trail_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.{format_type}"
        
        if format_type == "json":
            await self._export_json(result, export_filename)
        elif format_type == "csv":
            await self._export_csv(result, export_filename)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")
        
        logger.info(f"Exported audit trail {export_id} to {export_filename}")
        
        return {
            "export_id": export_id,
            "filename": export_filename,
            "total_events": result["total_events"],
            "exported_at": datetime.utcnow().isoformat(),
            "format": format_type
        }
    
    # Internal methods
    async def _flush_events(self):
        """Flush events from buffer to storage"""
        if not self.event_buffer:
            return
        
        events_to_flush = self.event_buffer.copy()
        self.event_buffer.clear()
        
        try:
            # Store events in database (mock implementation)
            await self._store_events_batch(events_to_flush)
            logger.debug(f"Flushed {len(events_to_flush)} audit events to storage")
            
        except Exception as e:
            logger.error(f"Failed to flush audit events: {e}")
            # Re-add events to buffer for retry
            self.event_buffer.extend(events_to_flush)
    
    async def _handle_critical_event(self, event: AuditEvent):
        """Handle critical audit events immediately"""
        
        # Log critical event
        logger.warning(f"Critical audit event: {event.event_type} from {event.service_name}")
        
        # Send real-time alert (mock implementation)
        await self._send_critical_alert(event)
        
        # Store immediately (bypass buffer)
        await self._store_events_batch([event])
    
    async def _cache_recent_event(self, event: AuditEvent):
        """Cache recent event in Redis for real-time dashboard"""
        try:
            event_key = f"recent_events:{event.service_name}"
            event_data = event.dict()
            event_data['timestamp'] = event_data['timestamp'].isoformat()
            
            # Add to Redis list (keep last 100 events per service)
            await self.redis_client.lpush(event_key, event_data)
            await self.redis_client.ltrim(event_key, 0, 99)
            await self.redis_client.expire(event_key, 86400)  # 24 hour expiry
            
        except Exception as e:
            logger.error(f"Failed to cache recent event: {e}")
    
    def _generate_compliance_tags(self, request: AuditLogRequest) -> List[str]:
        """Generate compliance tags for audit event"""
        
        tags = []
        
        # PHI-related tags
        if request.phi_detected:
            tags.append("phi_involved")
        
        if request.event_type in self.phi_related_events:
            tags.append("phi_access")
        
        # HIPAA-related tags
        if request.event_type in [
            AuditEventType.PHI_ACCESS,
            AuditEventType.PHI_MODIFICATION,
            AuditEventType.PHI_EXPORT
        ]:
            tags.append("hipaa_regulated")
        
        # Administrative tags
        if request.event_type in [
            AuditEventType.USER_LOGIN,
            AuditEventType.USER_LOGOUT,
            AuditEventType.FAILED_LOGIN
        ]:
            tags.append("authentication")
        
        # Financial tags
        if request.event_type in [
            AuditEventType.INSURANCE_VERIFICATION,
            AuditEventType.CLAIM_SUBMISSION,
            AuditEventType.PAYMENT_PROCESSING
        ]:
            tags.append("financial_transaction")
        
        return tags
    
    # Mock database operations - replace with actual database integration
    async def _execute_audit_query(
        self,
        conditions: List[str],
        params: List[Any],
        limit: int,
        offset: int
    ) -> List[AuditEvent]:
        """Execute audit query against database"""
        
        # Mock query execution
        mock_events = []
        for i in range(min(limit, 10)):
            mock_events.append(AuditEvent(
                event_id=f"mock_{uuid4().hex[:8]}",
                event_type=AuditEventType.PHI_ACCESS,
                service_name="healthcare-api",
                action_performed="patient_lookup",
                timestamp=datetime.utcnow() - timedelta(hours=i)
            ))
        
        return mock_events
    
    async def _count_audit_events(
        self,
        conditions: List[str],
        params: List[Any]
    ) -> int:
        """Count audit events matching conditions"""
        return 150  # Mock count
    
    async def _store_events_batch(self, events: List[AuditEvent]):
        """Store batch of events in database"""
        # Mock storage operation
        logger.debug(f"Storing {len(events)} events in database")
    
    async def _get_24h_statistics(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Get last 24 hours statistics"""
        
        return {
            "total_events": 1547,
            "phi_events": 89,
            "failed_logins": 3,
            "unique_users": 23,
            "unique_services": 5,
            "api_requests": 2341,
            "errors": 12,
            "average_response_time_ms": 245.5
        }
    
    async def _get_current_violations(self) -> List[Any]:
        """Get current open violations"""
        return []  # Mock - no current violations
    
    async def _get_system_health_indicators(self) -> Dict[str, Any]:
        """Get system health indicators"""
        
        return {
            "overall_health": "good",
            "services_online": 5,
            "services_total": 5,
            "database_connections": "healthy",
            "redis_connections": "healthy",
            "disk_usage_percent": 45.2,
            "memory_usage_percent": 67.8,
            "cpu_usage_percent": 23.1
        }
    
    async def _get_compliance_trends(self) -> Dict[str, Any]:
        """Get compliance trend data"""
        
        return {
            "daily_events_trend": [1245, 1387, 1456, 1547],
            "violation_trend": [0, 1, 0, 0],
            "phi_access_trend": [67, 78, 82, 89],
            "login_failure_trend": [2, 1, 4, 3]
        }
    
    async def _get_top_alerts(self) -> List[Dict[str, Any]]:
        """Get top priority alerts"""
        
        return [
            {
                "alert_id": "alert_001",
                "type": "warning",
                "message": "Elevated PHI access volume in last hour",
                "timestamp": (datetime.utcnow() - timedelta(minutes=15)).isoformat(),
                "service": "healthcare-api"
            }
        ]
    
    async def _get_service_status(self) -> Dict[str, str]:
        """Get service status overview"""
        
        return {
            "healthcare-api": "online",
            "insurance-verification": "online",
            "billing-engine": "online",
            "medical-mirrors": "online",
            "compliance-monitor": "online"
        }
    
    async def _get_recent_events(self, limit: int = 20) -> List[AuditEvent]:
        """Get recent audit events"""
        
        events = []
        for i in range(limit):
            events.append(AuditEvent(
                event_id=f"recent_{i}",
                event_type=AuditEventType.API_REQUEST,
                service_name="healthcare-api",
                action_performed="patient_search",
                timestamp=datetime.utcnow() - timedelta(minutes=i*2)
            ))
        
        return events
    
    async def _calculate_risk_indicators(
        self,
        stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate risk indicators based on statistics"""
        
        risk_score = 0.0
        
        # Failed login risk
        if stats["failed_logins"] > 10:
            risk_score += 0.3
        elif stats["failed_logins"] > 5:
            risk_score += 0.1
        
        # Error rate risk
        error_rate = stats["errors"] / stats["total_events"] * 100
        if error_rate > 2.0:
            risk_score += 0.2
        elif error_rate > 1.0:
            risk_score += 0.1
        
        # PHI access volume risk
        phi_rate = stats["phi_events"] / stats["total_events"] * 100
        if phi_rate > 15.0:
            risk_score += 0.2
        elif phi_rate > 10.0:
            risk_score += 0.1
        
        risk_level = "low"
        if risk_score > 0.5:
            risk_level = "high"
        elif risk_score > 0.3:
            risk_level = "medium"
        
        return {
            "overall_risk_score": min(risk_score, 1.0),
            "risk_level": risk_level,
            "failed_login_risk": stats["failed_logins"] > 5,
            "error_rate_risk": error_rate > 1.0,
            "phi_access_risk": phi_rate > 10.0,
            "recommendations": self._generate_risk_recommendations(risk_score, stats)
        }
    
    def _generate_risk_recommendations(
        self,
        risk_score: float,
        stats: Dict[str, Any]
    ) -> List[str]:
        """Generate risk mitigation recommendations"""
        
        recommendations = []
        
        if stats["failed_logins"] > 5:
            recommendations.append("Review failed login attempts for potential security threats")
        
        if stats["errors"] / stats["total_events"] > 0.01:
            recommendations.append("Investigate elevated error rates across services")
        
        if stats["phi_events"] / stats["total_events"] > 0.1:
            recommendations.append("Review PHI access patterns for compliance")
        
        if risk_score > 0.5:
            recommendations.append("Consider implementing additional security measures")
        
        return recommendations
    
    async def _send_critical_alert(self, event: AuditEvent):
        """Send critical event alert"""
        # Mock alert sending
        logger.warning(f"CRITICAL ALERT: {event.event_type} - {event.action_performed}")
    
    async def _export_json(self, data: Dict[str, Any], filename: str):
        """Export data as JSON"""
        import json
        
        async with aiofiles.open(f"/app/logs/{filename}", 'w') as f:
            await f.write(json.dumps(data, indent=2, default=str))
    
    async def _export_csv(self, data: Dict[str, Any], filename: str):
        """Export data as CSV"""
        import csv
        
        # Mock CSV export
        logger.info(f"Exporting {len(data['events'])} events to CSV: {filename}")