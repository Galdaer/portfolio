"""
Simple Compliance Monitor

Provides basic HIPAA compliance monitoring and audit logging
for healthcare operations.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from core.infrastructure.healthcare_logger import get_healthcare_logger, log_healthcare_event
from config.config_loader import get_healthcare_config

logger = get_healthcare_logger(__name__)

class ComplianceRiskLevel(Enum):
    """Compliance risk severity levels"""
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ComplianceEvent:
    """Individual compliance event record"""
    event_id: str
    event_type: str
    risk_level: ComplianceRiskLevel
    description: str
    agent_name: str
    session_id: Optional[str] = None
    patient_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    resolution_notes: Optional[str] = None
    
@dataclass
class ComplianceStatus:
    """Overall compliance status summary"""
    total_events: int
    high_risk_events: int
    unresolved_events: int
    last_audit_date: Optional[datetime]
    compliance_score: float  # 0-100
    active_violations: List[ComplianceEvent]

class SimpleComplianceMonitor:
    """
    Simple compliance monitoring for HIPAA and healthcare regulations using configuration
    """
    
    def __init__(self):
        # Load configuration
        self.config = get_healthcare_config().compliance
        
        # Initialize from configuration
        retention_config = self.config.event_retention
        self.max_events_retention = retention_config.get("max_events_retention", 10000)
        
        # Get scoring configuration
        self.scoring_config = self.config.scoring
        self.high_risk_penalty = self.scoring_config.get("high_risk_penalty", 10)
        self.unresolved_penalty = self.scoring_config.get("unresolved_penalty", 5)
        self.base_score = self.scoring_config.get("base_score", 100.0)
        
        # Initialize data structures
        self.compliance_events: List[ComplianceEvent] = []
        self.audit_trail: List[Dict[str, Any]] = []
        
        # Initialize logging
        log_healthcare_event(
            logger,
            logging.INFO,
            "Configuration-based compliance monitor initialized",
            context={
                "max_retention": self.max_events_retention,
                "high_risk_penalty": self.high_risk_penalty,
                "unresolved_penalty": self.unresolved_penalty
            },
            operation_type="compliance_monitor_init"
        )
    
    def log_compliance_event(
        self,
        event_type: str,
        description: str,
        agent_name: str,
        risk_level: ComplianceRiskLevel = ComplianceRiskLevel.LOW,
        session_id: Optional[str] = None,
        patient_id: Optional[str] = None
    ) -> str:
        """
        Log a compliance event for audit trail
        
        Args:
            event_type: Type of compliance event
            description: Human-readable description
            agent_name: Name of the agent generating event
            risk_level: Severity level
            session_id: Optional session identifier
            patient_id: Optional patient identifier
            
        Returns:
            str: Event ID for tracking
        """
        event_id = f"COMP_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(self)}"
        
        compliance_event = ComplianceEvent(
            event_id=event_id,
            event_type=event_type,
            risk_level=risk_level,
            description=description,
            agent_name=agent_name,
            session_id=session_id,
            patient_id=patient_id
        )
        
        # Add to events list
        self.compliance_events.append(compliance_event)
        
        # Maintain retention limit
        if len(self.compliance_events) > self.max_events_retention:
            self.compliance_events = self.compliance_events[-self.max_events_retention:]
        
        # Log to healthcare logger
        log_healthcare_event(
            logger,
            logging.WARNING if risk_level in [ComplianceRiskLevel.HIGH, ComplianceRiskLevel.CRITICAL] else logging.INFO,
            f"Compliance event logged: {event_type}",
            context={
                "event_id": event_id,
                "event_type": event_type,
                "risk_level": risk_level.value,
                "agent_name": agent_name,
                "session_id": session_id,
                "description": description
            },
            operation_type="compliance_event_logged"
        )
        
        return event_id
    
    def log_phi_access(
        self,
        agent_name: str,
        operation: str,
        patient_id: Optional[str] = None,
        session_id: Optional[str] = None,
        justification: Optional[str] = None
    ) -> str:
        """
        Log PHI access for HIPAA audit trail
        
        Args:
            agent_name: Name of agent accessing PHI
            operation: Type of PHI operation (read, write, process, etc.)
            patient_id: Patient whose PHI was accessed
            session_id: Session context
            justification: Business justification for access
            
        Returns:
            str: Event ID
        """
        description = f"PHI {operation}"
        if justification:
            description += f" - {justification}"
            
        return self.log_compliance_event(
            event_type="phi_access",
            description=description,
            agent_name=agent_name,
            risk_level=ComplianceRiskLevel.MEDIUM,
            session_id=session_id,
            patient_id=patient_id
        )
    
    def log_data_breach_risk(
        self,
        agent_name: str,
        breach_type: str,
        details: str,
        session_id: Optional[str] = None
    ) -> str:
        """
        Log potential data breach or security risk
        
        Args:
            agent_name: Agent that detected the risk
            breach_type: Type of breach risk
            details: Detailed description
            session_id: Session context
            
        Returns:
            str: Event ID
        """
        return self.log_compliance_event(
            event_type="data_breach_risk",
            description=f"Breach risk: {breach_type} - {details}",
            agent_name=agent_name,
            risk_level=ComplianceRiskLevel.CRITICAL,
            session_id=session_id
        )
    
    def log_audit_access(
        self,
        user_id: str,
        resource_accessed: str,
        access_type: str = "read",
        justification: Optional[str] = None
    ) -> str:
        """
        Log audit trail access for compliance review
        
        Args:
            user_id: User accessing audit trail
            resource_accessed: What was accessed
            access_type: Type of access
            justification: Business justification
            
        Returns:
            str: Event ID
        """
        description = f"Audit access: {access_type} {resource_accessed}"
        if justification:
            description += f" - {justification}"
            
        return self.log_compliance_event(
            event_type="audit_access",
            description=description,
            agent_name="compliance_monitor",
            risk_level=ComplianceRiskLevel.MEDIUM,
            session_id=user_id
        )
    
    def get_compliance_status(self) -> ComplianceStatus:
        """
        Get overall compliance status summary
        
        Returns:
            ComplianceStatus: Current compliance metrics
        """
        total_events = len(self.compliance_events)
        high_risk_events = len([
            event for event in self.compliance_events 
            if event.risk_level in [ComplianceRiskLevel.HIGH, ComplianceRiskLevel.CRITICAL]
        ])
        unresolved_events = len([
            event for event in self.compliance_events 
            if not event.resolved
        ])
        
        # Configuration-based compliance score calculation
        if total_events == 0:
            compliance_score = self.base_score
        else:
            # Reduce score based on configured penalties
            penalty = (high_risk_events * self.high_risk_penalty) + (unresolved_events * self.unresolved_penalty)
            compliance_score = max(0.0, self.base_score - penalty)
        
        # Get active violations (critical unresolved events)
        active_violations = [
            event for event in self.compliance_events
            if event.risk_level == ComplianceRiskLevel.CRITICAL and not event.resolved
        ]
        
        # Find last audit date
        last_audit_date = None
        audit_events = [
            event for event in self.compliance_events
            if event.event_type == "audit_access"
        ]
        if audit_events:
            last_audit_date = max(event.timestamp for event in audit_events)
        
        return ComplianceStatus(
            total_events=total_events,
            high_risk_events=high_risk_events,
            unresolved_events=unresolved_events,
            last_audit_date=last_audit_date,
            compliance_score=compliance_score,
            active_violations=active_violations
        )
    
    def resolve_compliance_event(
        self,
        event_id: str,
        resolution_notes: str,
        resolver_name: str
    ) -> bool:
        """
        Mark a compliance event as resolved
        
        Args:
            event_id: ID of event to resolve
            resolution_notes: Description of resolution
            resolver_name: Name of person/system resolving
            
        Returns:
            bool: True if event was found and resolved
        """
        for event in self.compliance_events:
            if event.event_id == event_id:
                event.resolved = True
                event.resolution_notes = f"{resolution_notes} (Resolved by: {resolver_name} at {datetime.now()})"
                
                log_healthcare_event(
                    logger,
                    logging.INFO,
                    f"Compliance event resolved: {event_id}",
                    context={
                        "event_id": event_id,
                        "resolver": resolver_name,
                        "resolution_notes": resolution_notes
                    },
                    operation_type="compliance_event_resolved"
                )
                
                return True
        
        logger.warning(f"Compliance event not found for resolution: {event_id}")
        return False
    
    def get_events_by_type(
        self,
        event_type: str,
        limit: int = 100,
        include_resolved: bool = True
    ) -> List[ComplianceEvent]:
        """
        Get compliance events filtered by type
        
        Args:
            event_type: Type of events to retrieve
            limit: Maximum number of events to return
            include_resolved: Whether to include resolved events
            
        Returns:
            List[ComplianceEvent]: Matching events
        """
        filtered_events = [
            event for event in self.compliance_events
            if event.event_type == event_type and (include_resolved or not event.resolved)
        ]
        
        # Sort by timestamp (newest first) and limit
        filtered_events.sort(key=lambda x: x.timestamp, reverse=True)
        return filtered_events[:limit]
    
    def get_events_by_agent(
        self,
        agent_name: str,
        limit: int = 100
    ) -> List[ComplianceEvent]:
        """
        Get compliance events for specific agent
        
        Args:
            agent_name: Name of agent
            limit: Maximum events to return
            
        Returns:
            List[ComplianceEvent]: Agent's compliance events
        """
        agent_events = [
            event for event in self.compliance_events
            if event.agent_name == agent_name
        ]
        
        agent_events.sort(key=lambda x: x.timestamp, reverse=True)
        return agent_events[:limit]
    
    def generate_audit_report(
        self,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """
        Generate compliance audit report
        
        Args:
            days_back: Number of days to include in report
            
        Returns:
            dict: Audit report data
        """
        cutoff_date = datetime.now() - timedelta(days=days_back)
        recent_events = [
            event for event in self.compliance_events
            if event.timestamp >= cutoff_date
        ]
        
        # Group events by type
        events_by_type = {}
        for event in recent_events:
            if event.event_type not in events_by_type:
                events_by_type[event.event_type] = []
            events_by_type[event.event_type].append(event)
        
        # Get compliance status
        status = self.get_compliance_status()
        
        report = {
            "report_generated": datetime.now().isoformat(),
            "period_days": days_back,
            "period_start": cutoff_date.isoformat(),
            "total_events_in_period": len(recent_events),
            "events_by_type": {
                event_type: len(events) 
                for event_type, events in events_by_type.items()
            },
            "compliance_status": {
                "compliance_score": status.compliance_score,
                "total_events": status.total_events,
                "high_risk_events": status.high_risk_events,
                "unresolved_events": status.unresolved_events,
                "active_violations_count": len(status.active_violations)
            },
            "recommendations": self._generate_recommendations(status, recent_events)
        }
        
        log_healthcare_event(
            logger,
            logging.INFO,
            f"Compliance audit report generated for {days_back} days",
            context={
                "period_days": days_back,
                "events_in_period": len(recent_events),
                "compliance_score": status.compliance_score
            },
            operation_type="audit_report_generated"
        )
        
        return report
    
    def _generate_recommendations(
        self,
        status: ComplianceStatus,
        recent_events: List[ComplianceEvent]
    ) -> List[str]:
        """Generate compliance recommendations based on current status"""
        recommendations = []
        
        if status.compliance_score < 80:
            recommendations.append("Compliance score is below 80%. Review high-risk events and implement corrective actions.")
        
        if status.active_violations:
            recommendations.append(f"There are {len(status.active_violations)} active critical violations requiring immediate attention.")
        
        if status.unresolved_events > 10:
            recommendations.append("High number of unresolved compliance events. Prioritize resolution of pending items.")
        
        # Check for PHI access patterns
        phi_events = [e for e in recent_events if e.event_type == "phi_access"]
        if len(phi_events) > 100:
            recommendations.append("High volume of PHI access events. Consider implementing additional access controls.")
        
        # Check audit frequency using configuration
        audit_config = self.config.audit
        audit_frequency_days = audit_config.get("frequency_days", 90)
        if not status.last_audit_date or (datetime.now() - status.last_audit_date).days > audit_frequency_days:
            recommendations.append(f"No recent audit access logged in {audit_frequency_days} days. Ensure regular compliance reviews are being conducted.")
        
        return recommendations if recommendations else ["No immediate compliance concerns identified."]

# Global compliance monitor instance
compliance_monitor = SimpleComplianceMonitor()