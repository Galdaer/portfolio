"""
Healthcare Audit Logger
HIPAA-compliant audit logging with structured output
"""

import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


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

    VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

    def __init__(self, config, log_level: str = "INFO"):
        self.config = config
        self.logger = logging.getLogger("healthcare_audit")

        # Validate log level before setting
        log_level_upper = log_level.upper()
        if log_level_upper not in self.VALID_LOG_LEVELS:
            raise ValueError(
                f"Invalid log level: {log_level}. "
                f"Must be one of: {', '.join(sorted(self.VALID_LOG_LEVELS))}"
            )

        self.logger.setLevel(getattr(logging, log_level_upper))

    async def log_request(self, request, response, processing_time: float):
        """Log HTTP request for audit trail"""
        self.logger.info(
            f"REQUEST: method={getattr(request, 'method', 'unknown')}, "
            f"path={getattr(request, 'url', 'unknown')}, "
            f"processing_time={processing_time:.3f}s, "
            f"status={getattr(response, 'status_code', 'unknown')}"
        )

    def log_security_event(self, event_type: str, details: Dict[str, Any]):
        """Log security events for monitoring (synchronous)"""
        self.logger.warning(f"SECURITY_EVENT: {event_type}, details={details}")

    async def log_phi_detection(self, request_data, phi_details: Dict[str, Any]):
        """Log PHI detection events"""
        request_id = getattr(request_data, "id", "unknown")
        phi_types = phi_details.get("entities", [])

        self.logger.warning(
            f"PHI_DETECTION: request_id={request_id}, "
            f"types={phi_types}, "
            f"confidence={phi_details.get('confidence', 0.0)}, "
            f"details={phi_details.get('detection_details', [])}"
        )

    def log_audit_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        result: str = "success",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log healthcare audit event with structured data"""

        audit_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type.value,
            "user_id": user_id or "system",
            "resource": resource,
            "action": action,
            "result": result,
            "details": details or {},
        }

        self.logger.info(json.dumps(audit_record))


# Example usage
if __name__ == "__main__":
    # This would be used in testing
    pass
