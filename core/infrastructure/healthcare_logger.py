"""
Healthcare-Compliant Logging Infrastructure

Provides comprehensive logging for healthcare AI systems with PHI protection,
HIPAA compliance, and runtime data pipeline monitoring.

MEDICAL DISCLAIMER: This logging system supports healthcare administrative functions.
It does not provide medical advice, diagnosis, or treatment recommendations.
All medical decisions must be made by qualified healthcare professionals.
"""

import hashlib
import logging
import logging.handlers
import re
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class HealthcareLogRecord(logging.LogRecord):
    """Extended LogRecord with healthcare context"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.healthcare_context: Optional[Dict[str, Any]] = None
        self.phi_detected: bool = False
        self.audit_required: bool = False


class HealthcareFormatter(logging.Formatter):
    """Healthcare-compliant log formatter with PHI protection"""

    # PHI patterns that should be automatically scrubbed from logs
    PHI_PATTERNS = [
        (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN_REDACTED]"),  # SSN
        (r"\b\d{3}-\d{3}-\d{4}\b", "[PHONE_REDACTED]"),  # Phone numbers
        (r"\b[A-Z]{2}\d{6,10}\b", "[MRN_REDACTED]"),  # Medical Record Numbers
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL_REDACTED]"),  # Email
        (
            r'patient_id["\']?\s*:\s*["\']?[^,}\]]+',
            "patient_id: [PATIENT_ID_REDACTED]",
        ),  # Patient IDs
        (
            r'insurance_id["\']?\s*:\s*["\']?[^,}\]]+',
            "insurance_id: [INSURANCE_ID_REDACTED]",
        ),  # Insurance IDs
        (r"\b\d{1,2}/\d{1,2}/\d{4}\b", "[DOB_REDACTED]"),  # Date of birth patterns
        (r"DOB[:\s]+\d{1,2}/\d{1,2}/\d{4}", "DOB: [DOB_REDACTED]"),  # DOB with label
    ]

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with automatic PHI scrubbing."""
        # Format the message first
        formatted = super().format(record)

        # Scrub any potential PHI from the formatted message
        for pattern, replacement in self.PHI_PATTERNS:
            formatted = re.sub(pattern, replacement, formatted, flags=re.IGNORECASE)

        return formatted


class PHISafeHandler(logging.Handler):
    """Custom handler that ensures PHI safety before writing logs."""

    def __init__(self, base_handler: logging.Handler):
        super().__init__()
        self.base_handler = base_handler

    def emit(self, record: logging.LogRecord) -> None:
        """Emit log record after PHI safety validation."""
        try:
            # Additional PHI safety check before emitting
            if hasattr(record, "healthcare_context"):
                # Verify healthcare context doesn't contain raw PHI
                context = record.healthcare_context
                if self._contains_phi_indicators(str(context)):
                    # Create a sanitized version
                    record.healthcare_context = self._sanitize_healthcare_context(context)

            self.base_handler.emit(record)
        except Exception:
            self.handleError(record)

    def _contains_phi_indicators(self, text: str) -> bool:
        """Check if text contains potential PHI indicators."""
        phi_indicators = [
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
            r"\b\d{3}-\d{3}-\d{4}\b",  # Phone
            r"patient_id.*[A-Z0-9]{5,}",  # Patient ID patterns
            r"insurance.*\d{6,}",  # Insurance number patterns
        ]

        for pattern in phi_indicators:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _sanitize_healthcare_context(self, context: dict[str, Any]) -> dict[str, Any]:
        """Sanitize healthcare context for safe logging."""
        sanitized = {}
        for key, value in context.items():
            if key in ["patient_id", "insurance_id", "medical_record_number"]:
                # Hash sensitive identifiers
                if isinstance(value, str):
                    sanitized[key + "_hash"] = hashlib.sha256(value.encode()).hexdigest()[:8]
                else:
                    sanitized[key + "_hash"] = "[HASHED]"
            elif isinstance(value, str) and self._contains_phi_indicators(value):
                sanitized[key] = "[PHI_SANITIZED]"
            else:
                sanitized[key] = value
        return sanitized


def setup_healthcare_logging(
    log_dir: Path = Path("logs"),
    log_level: str = "INFO",
    max_bytes: int = 50 * 1024 * 1024,  # 50MB
    backup_count: int = 10,
) -> None:
    """
    Setup healthcare-compliant logging infrastructure.

    Args:
        log_dir: Directory for log files
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        max_bytes: Maximum size per log file before rotation
        backup_count: Number of backup files to keep for audit compliance
    """
    # Ensure log directory exists
    log_dir.mkdir(exist_ok=True)

    # Add custom log levels for healthcare
    logging.addLevelName(25, "PHI_ALERT")
    logging.addLevelName(35, "MEDICAL_ERROR")
    logging.addLevelName(33, "COMPLIANCE_WARNING")

    # Configure root healthcare logger
    healthcare_logger = logging.getLogger("healthcare")
    healthcare_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers to avoid duplicates
    healthcare_logger.handlers.clear()

    # Healthcare-specific formatter
    formatter = HealthcareLogFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # File handler with rotation for HIPAA retention compliance
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "healthcare_system.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    # PHI-safe file handler wrapper
    phi_safe_file_handler = PHISafeHandler(file_handler)

    # Console handler for development (WARNING and above)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.WARNING)

    # PHI-safe console handler wrapper
    phi_safe_console_handler = PHISafeHandler(console_handler)

    # Add handlers to healthcare logger
    healthcare_logger.addHandler(phi_safe_file_handler)
    healthcare_logger.addHandler(phi_safe_console_handler)

    # Prevent propagation to root logger to avoid duplicate messages
    healthcare_logger.propagate = False

    # Create specialized loggers for different healthcare components
    _setup_specialized_loggers(log_dir, formatter)

    # Log initialization
    healthcare_logger.info(
        "Healthcare logging system initialized",
        extra={
            "healthcare_context": {
                "initialization": True,
                "phi_protection": True,
                "audit_compliance": True,
                "log_directory": str(log_dir),
                "retention_policy": f"{backup_count} files, {max_bytes} bytes each",
            }
        },
    )


def _setup_specialized_loggers(log_dir: Path, formatter: HealthcareLogFormatter) -> None:
    """Setup specialized loggers for different healthcare components."""

    # Agent-specific loggers
    agent_loggers = ["intake", "document_processor", "research_assistant"]
    for agent in agent_loggers:
        logger = logging.getLogger(f"healthcare.agent.{agent}")

        # Dedicated file for each agent
        agent_handler = logging.handlers.RotatingFileHandler(
            log_dir / f"agent_{agent}.log",
            maxBytes=10 * 1024 * 1024,  # 10MB per agent
            backupCount=5,
        )
        agent_handler.setFormatter(formatter)

        # PHI-safe wrapper
        phi_safe_agent_handler = PHISafeHandler(agent_handler)
        logger.addHandler(phi_safe_agent_handler)
        logger.propagate = False

    # PHI monitoring logger
    phi_logger = logging.getLogger("healthcare.phi_monitor")
    phi_handler = logging.handlers.RotatingFileHandler(
        log_dir / "phi_monitoring.log",
        maxBytes=25 * 1024 * 1024,  # 25MB for PHI monitoring
        backupCount=10,
    )
    phi_handler.setFormatter(formatter)
    phi_safe_phi_handler = PHISafeHandler(phi_handler)
    phi_logger.addHandler(phi_safe_phi_handler)
    phi_logger.propagate = False

    # Audit logger for compliance
    audit_logger = logging.getLogger("healthcare.audit")
    audit_handler = logging.handlers.RotatingFileHandler(
        log_dir / "audit_trail.log",
        maxBytes=100 * 1024 * 1024,  # 100MB for audit trail
        backupCount=20,  # Keep more audit files for compliance
    )
    audit_handler.setFormatter(formatter)
    phi_safe_audit_handler = PHISafeHandler(audit_handler)
    audit_logger.addHandler(phi_safe_audit_handler)
    audit_logger.propagate = False


def get_healthcare_logger(module_name: str) -> logging.Logger:
    """
    Get a healthcare-compliant logger for a specific module.

    Args:
        module_name: Name of the module (e.g., 'agent.intake', 'phi_monitor')

    Returns:
        Logger configured for healthcare compliance
    """
    return logging.getLogger(f"healthcare.{module_name}")


def log_healthcare_event(
    logger: logging.Logger,
    level: int,
    message: str,
    context: dict[str, Any] | None = None,
    patient_hash: str | None = None,
    operation_type: str | None = None,
) -> None:
    """
    Log a healthcare event with standardized context.

    Args:
        logger: Healthcare logger instance
        level: Logging level (e.g., logging.INFO)
        message: Log message
        context: Additional context for the event
        patient_hash: Hashed patient identifier (if applicable)
        operation_type: Type of healthcare operation
    """
    healthcare_context = {
        "timestamp": datetime.now().isoformat(),
        "operation_type": operation_type,
        "patient_hash": patient_hash,
        "context": context or {},
    }

    logger.log(level, message, extra={"healthcare_context": healthcare_context})


def log_phi_alert(message: str, context: dict[str, Any], severity: str = "high") -> None:
    """
    Log a PHI exposure alert with high priority.

    Args:
        message: Alert message
        context: Context information (will be sanitized)
        severity: Alert severity (low, medium, high, critical)
    """
    phi_logger = logging.getLogger("healthcare.phi_monitor")

    # Create sanitized context
    sanitized_context = {
        "severity": severity,
        "alert_type": "phi_exposure",
        "detection_time": datetime.now().isoformat(),
        "requires_review": True,
    }

    # Add non-sensitive context information
    for key, value in context.items():
        if key not in ["patient_data", "raw_input", "sensitive_content"]:
            sanitized_context[key] = value

    phi_logger.log(
        25,
        f"PHI_ALERT: {message}",
        extra={  # PHI_ALERT level = 25
            "healthcare_context": sanitized_context
        },
    )


def log_compliance_event(
    event_type: str, details: dict[str, Any], compliance_status: str = "compliant"
) -> None:
    """
    Log a compliance-related event for audit purposes.

    Args:
        event_type: Type of compliance event
        details: Event details (will be sanitized for PHI)
        compliance_status: Status (compliant, non_compliant, review_required)
    """
    audit_logger = logging.getLogger("healthcare.audit")

    compliance_context = {
        "event_type": event_type,
        "compliance_status": compliance_status,
        "audit_timestamp": datetime.now().isoformat(),
        "details": details,
    }

    audit_logger.info(
        f"COMPLIANCE_EVENT: {event_type}", extra={"healthcare_context": compliance_context}
    )


# Healthcare-specific logging decorators
def healthcare_log_method(
    operation_type: str = "healthcare_operation", phi_risk_level: str = "medium"
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator for comprehensive healthcare method logging.

    Args:
        operation_type: Type of healthcare operation being logged
        phi_risk_level: Risk level for PHI exposure (low, medium, high)
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = get_healthcare_logger(f"{func.__module__}")
            method_name = f"{func.__qualname__}"

            # Entry logging
            start_time = datetime.now()
            log_healthcare_event(
                logger,
                logging.INFO,
                f"Healthcare method entry: {method_name}",
                context={
                    "method": method_name,
                    "operation_type": operation_type,
                    "phi_risk_level": phi_risk_level,
                    "entry_time": start_time.isoformat(),
                },
            )

            try:
                # Execute method
                result = func(*args, **kwargs)

                # Success logging
                execution_time = (datetime.now() - start_time).total_seconds()
                log_healthcare_event(
                    logger,
                    logging.INFO,
                    f"Healthcare method success: {method_name}",
                    context={
                        "method": method_name,
                        "execution_time_ms": round(execution_time * 1000, 2),
                        "success": True,
                    },
                )

                return result

            except Exception as e:
                # Error logging
                execution_time = (datetime.now() - start_time).total_seconds()
                log_healthcare_event(
                    logger,
                    35,  # MEDICAL_ERROR level
                    f"Healthcare method error: {method_name}: {str(e)}",
                    context={
                        "method": method_name,
                        "error_type": type(e).__name__,
                        "error_message": str(e)[:200],  # Truncated for safety
                        "execution_time_ms": round(execution_time * 1000, 2),
                        "success": False,
                    },
                )
                raise

        return wrapper

    return decorator


def healthcare_agent_log(agent_name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Specialized logging decorator for healthcare agents.

    Args:
        agent_name: Name of the healthcare agent
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = get_healthcare_logger(f"agent.{agent_name}")

            log_healthcare_event(
                logger,
                logging.INFO,
                f"Agent {agent_name} processing: {func.__name__}",
                context={
                    "agent": agent_name,
                    "operation": func.__name__,
                    "agent_version": "1.0",
                    "processing_start": datetime.now().isoformat(),
                },
            )

            return func(*args, **kwargs)

        return wrapper

    return decorator
