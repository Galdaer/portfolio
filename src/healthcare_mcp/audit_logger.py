"""
Healthcare Audit Logger
HIPAA-compliant audit logging with structured output
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum


class AuditEventType(Enum):
    """Healthcare audit event types for HIPAA compliance"""
    PHI_ACCESS = "phi_access"
    PHI_MODIFICATION = "phi_modification"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    SYSTEM_ACCESS = "system_access"
    DATA_EXPORT = "data_export"
    SECURITY_EVENT = "security_event"


class HealthcareAuditLogger:
    """
    HIPAA-compliant audit logger for healthcare AI operations
    """

    def __init__(self, log_level: str = "INFO"):
        self.logger = logging.getLogger("healthcare_audit")
        self.logger.setLevel(getattr(logging, log_level.upper()))

        # Create structured handler
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log_audit_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        result: str = "success",
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log healthcare audit event with structured data"""

        audit_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type.value,
            "user_id": user_id or "system",
            "resource": resource,
            "action": action,
            "result": result,
            "details": details or {}
        }

        self.logger.info(json.dumps(audit_record))

# Example usage
if __name__ == "__main__":
    # This would be used in testing
    pass
