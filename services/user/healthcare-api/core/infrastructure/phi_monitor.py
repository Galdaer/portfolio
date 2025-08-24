"""
PHI Monitoring and Detection System

Real-time PHI detection and monitoring for healthcare AI compliance.
Provides runtime data pipeline safety monitoring and HIPAA compliance validation.

MEDICAL DISCLAIMER: This system provides administrative PHI protection support.
It does not provide medical advice, diagnosis, or treatment recommendations.
All medical decisions must be made by qualified healthcare professionals.
"""

import hashlib
import re
from collections.abc import Callable
from datetime import datetime
from enum import Enum
from typing import Any

from config.phi_detection_config_loader import phi_config

from .healthcare_logger import get_healthcare_logger, log_phi_alert


class PHIRiskLevel(Enum):
    """PHI risk levels for different types of data processing."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PHIType(Enum):
    """Types of PHI that can be detected."""

    SSN = "ssn"
    PHONE = "phone"
    EMAIL = "email"
    MEDICAL_RECORD_NUMBER = "medical_record_number"
    PATIENT_ID = "patient_id"
    INSURANCE_ID = "insurance_id"
    DATE_OF_BIRTH = "date_of_birth"
    ADDRESS = "address"
    NAME = "name"
    BIOMETRIC = "biometric"


class PHIDetectionResult:
    """Result from PHI detection scanning."""

    def __init__(
        self,
        phi_detected: bool,
        phi_types: list[PHIType],
        risk_level: PHIRiskLevel,
        detection_details: dict[str, Any],
        recommendations: list[str],
    ):
        self.phi_detected = phi_detected
        self.phi_types = phi_types
        self.risk_level = risk_level
        self.detection_details = detection_details
        self.recommendations = recommendations
        self.timestamp = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary for logging."""
        return {
            "phi_detected": self.phi_detected,
            "phi_types": [phi_type.value for phi_type in self.phi_types],
            "risk_level": self.risk_level.value,
            "detection_details": self.detection_details,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp.isoformat(),
        }


class PHIMonitor:
    """
    Real-time PHI detection and monitoring system.

    Provides comprehensive PHI detection for healthcare AI systems with
    runtime data pipeline monitoring and compliance validation.
    """

    def __init__(self, enable_synthetic_detection: bool = True):
        """
        Initialize PHI monitor.

        Args:
            enable_synthetic_detection: Whether to detect and ignore synthetic data patterns
        """
        self.logger = get_healthcare_logger("phi_monitor")
        self.enable_synthetic_detection = enable_synthetic_detection

        # Load configuration from YAML files
        self._load_configuration()

        self._detection_stats = {
            "total_scans": 0,
            "phi_detections": 0,
            "synthetic_data_filtered": 0,
            "false_positives": 0,
        }

    def _load_configuration(self) -> None:
        """Load PHI detection configuration from config files."""
        try:
            # Get compiled patterns from config
            self._compiled_patterns = phi_config.get_compiled_patterns()

            # Get other config settings
            self._risk_settings = phi_config.get_risk_settings()
            self._synthetic_patterns = phi_config.get_synthetic_patterns()
            self._phi_field_names = phi_config.get_phi_field_names()
            self._risk_mappings = phi_config.get_risk_mappings()
            self._recommendations_config = phi_config.get_recommendations()

            # Update instance settings from config
            if not hasattr(self, "enable_synthetic_detection"):
                self.enable_synthetic_detection = self._risk_settings.get(
                    "enable_synthetic_detection", True,
                )

            self.logger.info("PHI detection configuration loaded successfully")

        except Exception as e:
            self.logger.exception(f"Failed to load PHI configuration: {e}")
            # Use basic fallback patterns
            self._compiled_patterns = {}
            self._synthetic_patterns = []
            self._phi_field_names = set()
            self._risk_mappings = {
                "high_risk_types": [],
                "medium_risk_types": [],
                "low_risk_types": [],
            }
            self._recommendations_config = {}

    def reload_configuration(self) -> None:
        """Reload PHI detection configuration (useful for runtime updates)."""
        phi_config.reload_config()
        self._load_configuration()
        self.logger.info("PHI detection configuration reloaded")

    def scan_for_phi(
        self,
        data: str | dict[str, Any] | list[Any],
        context: str | None = None,
    ) -> PHIDetectionResult:
        """
        Comprehensive PHI detection scan.

        Args:
            data: Data to scan (string, dict, or list)
            context: Context information for the scan

        Returns:
            PHIDetectionResult with detection details
        """
        # MEDICAL LITERATURE EXEMPTION: Check config-based exemptions
        if context and phi_config.is_exempted_context(context):
            return PHIDetectionResult(
                phi_detected=False,
                phi_types=[],
                risk_level=PHIRiskLevel.NONE,
                detection_details={"exemption": "configured_exemption", "context": context},
                recommendations=["Context exempted from PHI detection by configuration"],
            )
        self._detection_stats["total_scans"] += 1

        # Convert data to scannable text
        scan_text = self._prepare_scan_text(data)

        # Check for synthetic data patterns first
        is_synthetic = self._is_synthetic_data(scan_text)
        if is_synthetic and self.enable_synthetic_detection:
            self._detection_stats["synthetic_data_filtered"] += 1
            return PHIDetectionResult(
                phi_detected=False,
                phi_types=[],
                risk_level=PHIRiskLevel.NONE,
                detection_details={"synthetic_data": True, "context": context},
                recommendations=["Data identified as synthetic/test data"],
            )

        # Perform PHI detection
        detected_phi_types: list[PHIType] = []
        detection_details: dict[str, Any] = {"matches": {}, "context": context}

        for phi_type_str, patterns in self._compiled_patterns.items():
            matches = []
            for pattern in patterns:
                found_matches = pattern.findall(scan_text)
                if found_matches:
                    matches.extend(found_matches)

            if matches:
                # Convert string to PHIType enum if possible
                try:
                    phi_type = PHIType(phi_type_str)
                    detected_phi_types.append(phi_type)
                    detection_details["matches"][str(phi_type)] = len(matches)
                except ValueError:
                    # If conversion fails, log and skip
                    self.logger.warning(f"Unknown PHI type: {phi_type_str}")
                    continue

        # Check field names for PHI indicators
        phi_field_matches = self._scan_field_names(data)
        if phi_field_matches:
            detection_details["phi_fields"] = phi_field_matches

        # Determine overall result
        phi_detected = bool(detected_phi_types or phi_field_matches)

        if phi_detected:
            self._detection_stats["phi_detections"] += 1

        # Calculate risk level
        risk_level = self._calculate_risk_level(detected_phi_types, phi_field_matches)

        # Generate recommendations
        recommendations = self._generate_recommendations(detected_phi_types, risk_level)

        result = PHIDetectionResult(
            phi_detected=phi_detected,
            phi_types=detected_phi_types,
            risk_level=risk_level,
            detection_details=detection_details,
            recommendations=recommendations,
        )

        # Log detection if PHI found
        if phi_detected:
            self._log_phi_detection(result, context)

        return result

    def _prepare_scan_text(self, data: str | dict[str, Any] | list[Any]) -> str:
        """Convert various data types to scannable text."""
        if isinstance(data, str):
            return data
        if isinstance(data, dict):
            # Create searchable text from dict keys and values
            text_parts = []
            for key, value in data.items():
                text_parts.append(f"{key}: {value}")
            return " ".join(text_parts)
        if isinstance(data, list):
            return " ".join(str(item) for item in data)

        # Handle other primitive types (bool, int, float, None)
        if isinstance(data, bool | int | float | type(None)):
            return str(data)

        # This should never be reached for supported types
        msg = f"Unexpected data type: {type(data)}"
        raise AssertionError(msg)

    def _is_synthetic_data(self, text: str) -> bool:
        """Check if data appears to be synthetic/test data."""
        if not self.enable_synthetic_detection:
            return False

        return any(pattern.search(text) for pattern in self._synthetic_patterns)

    def _scan_field_names(self, data: str | dict[str, Any] | list[Any]) -> list[str]:
        """Scan for PHI field names in data structure."""
        phi_fields = []

        if isinstance(data, dict):
            for key in data:
                if isinstance(key, str) and key.lower() in self._phi_field_names:
                    phi_fields.append(key)
        elif isinstance(data, str):
            # Check if the string contains field-like patterns
            for field_name in self._phi_field_names:
                pattern = rf"\b{re.escape(field_name)}\s*[:=]"
                if re.search(pattern, data, re.IGNORECASE):
                    phi_fields.append(field_name)

        return phi_fields

    def _calculate_risk_level(
        self,
        detected_types: list[PHIType],
        phi_fields: list[str],
    ) -> PHIRiskLevel:
        """Calculate risk level based on detected PHI types and config mappings."""
        if not detected_types and not phi_fields:
            return PHIRiskLevel.NONE

        # Convert PHIType enums to strings for comparison with config
        detected_type_names = [phi_type.value for phi_type in detected_types]

        # Get risk mappings from config
        high_risk_types = set(self._risk_mappings.get("high_risk_types", []))
        medium_risk_types = set(self._risk_mappings.get("medium_risk_types", []))

        # Check for high-risk PHI types
        if any(phi_type in high_risk_types for phi_type in detected_type_names):
            return PHIRiskLevel.CRITICAL

        # Check for multiple PHI types (critical threshold from config)
        critical_threshold = self._risk_settings.get("critical_threshold", 3)
        if len(detected_types) >= critical_threshold:
            return PHIRiskLevel.HIGH

        # Check for medium-risk PHI types
        if any(phi_type in medium_risk_types for phi_type in detected_type_names):
            return PHIRiskLevel.MEDIUM

        return PHIRiskLevel.LOW

    def _generate_recommendations(
        self,
        detected_types: list[PHIType],
        risk_level: PHIRiskLevel,
    ) -> list[str]:
        """Generate recommendations based on detection results and config."""
        # Get recommendations from config
        risk_level_key = risk_level.value.lower()
        if risk_level_key in self._recommendations_config:
            return self._recommendations_config[risk_level_key].copy()

        # Fallback recommendations if config is missing
        fallback_recommendations = {
            "critical": ["IMMEDIATE ACTION REQUIRED: Critical PHI detected"],
            "high": ["HIGH PRIORITY: Multiple PHI types detected"],
            "medium": ["MEDIUM PRIORITY: PHI detected"],
            "low": ["LOW PRIORITY: Minimal PHI detected"],
            "none": [],
        }

        return fallback_recommendations.get(risk_level_key, [])

    def _log_phi_detection(self, result: PHIDetectionResult, context: str | None) -> None:
        """Log PHI detection with appropriate severity."""
        severity_map = {
            PHIRiskLevel.CRITICAL: "critical",
            PHIRiskLevel.HIGH: "high",
            PHIRiskLevel.MEDIUM: "medium",
            PHIRiskLevel.LOW: "low",
        }

        log_phi_alert(
            message=f"PHI detected in {context or 'unknown context'}",
            context=result.to_dict(),
            severity=severity_map.get(result.risk_level, "medium"),
        )

    def monitor_data_pipeline(
        self,
        pipeline_name: str,
        data: Any,
        stage: str = "processing",
    ) -> bool:
        """
        Monitor data pipeline for PHI exposure.

        Args:
            pipeline_name: Name of the data pipeline
            data: Data being processed
            stage: Pipeline stage (input, processing, output)

        Returns:
            True if data is safe to process, False if PHI concerns exist
        """
        result = self.scan_for_phi(data, context=f"{pipeline_name}:{stage}")

        # Log pipeline monitoring
        self.logger.info(
            f"Pipeline monitoring: {pipeline_name} - {stage}",
            extra={
                "healthcare_context": {
                    "pipeline_name": pipeline_name,
                    "stage": stage,
                    "phi_detected": result.phi_detected,
                    "risk_level": result.risk_level.value,
                    "phi_types": [t.value for t in result.phi_types],
                },
            },
        )

        # Return safety status
        return result.risk_level in [PHIRiskLevel.NONE, PHIRiskLevel.LOW]

    def get_detection_stats(self) -> dict[str, Any]:
        """Get PHI detection statistics for monitoring."""
        return {
            **self._detection_stats,
            "detection_rate": (
                self._detection_stats["phi_detections"]
                / max(self._detection_stats["total_scans"], 1)
            )
            * 100,
        }

    def create_patient_hash(self, patient_id: str) -> str:
        """
        Create a secure hash for patient identification in logs.

        Args:
            patient_id: Original patient identifier

        Returns:
            Secure hash suitable for logging
        """
        return hashlib.sha256(patient_id.encode()).hexdigest()[:8]

    def sanitize_for_logging(
        self, data: dict[str, Any], context: str | None = None,
    ) -> dict[str, Any]:
        """
        Sanitize data for secure logging by removing or hashing PHI.

        Args:
            data: Data to sanitize
            context: Context for PHI detection (e.g., 'medical_literature')

        Returns:
            Sanitized data safe for logging
        """
        sanitized = {}

        for key, value in data.items():
            if isinstance(key, str) and key.lower() in self._phi_field_names:
                # Hash PHI fields
                if isinstance(value, str):
                    sanitized[f"{key}_hash"] = self.create_patient_hash(value)
                else:
                    sanitized[f"{key}_hash"] = "[HASHED]"
            else:
                # Check value for PHI content, passing context
                result = self.scan_for_phi(value, context)
                if result.phi_detected and result.risk_level != PHIRiskLevel.LOW:
                    sanitized[key] = "[PHI_SANITIZED]"
                else:
                    sanitized[key] = value

        return sanitized

    def validate_healthcare_context(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Validate healthcare context for compliance and safety.

        Args:
            context: Healthcare context to validate

        Returns:
            Validation results and recommendations
        """
        validation_result: dict[str, Any] = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "sanitized_context": {},
        }

        # Scan context for PHI
        phi_result = self.scan_for_phi(context, "healthcare_context")

        if phi_result.phi_detected:
            if phi_result.risk_level == PHIRiskLevel.CRITICAL:
                validation_result["valid"] = False
                validation_result["errors"].append("Critical PHI detected in healthcare context")
            elif phi_result.risk_level == PHIRiskLevel.HIGH:
                validation_result["warnings"].append("High-risk PHI detected in healthcare context")

        # Create sanitized version
        validation_result["sanitized_context"] = self.sanitize_for_logging(context)

        # Add recommendations
        validation_result["recommendations"] = phi_result.recommendations

        return validation_result


# Global PHI monitor instance
phi_monitor = PHIMonitor(enable_synthetic_detection=True)


# Convenience functions for common operations
def scan_for_phi(data: Any, context: str | None = None) -> bool:
    """
    Quick PHI scan - returns True if PHI is detected.

    Args:
        data: Data to scan
        context: Context for the scan

    Returns:
        True if PHI detected, False otherwise
    """
    result = phi_monitor.scan_for_phi(data, context)
    return result.phi_detected


def sanitize_healthcare_data(data: dict[str, Any], context: str | None = None) -> dict[str, Any]:
    """
    Sanitize healthcare data for safe logging.

    Args:
        data: Healthcare data to sanitize
        context: Context for PHI detection (e.g., 'medical_literature')

    Returns:
        Sanitized data safe for logging
    """
    return phi_monitor.sanitize_for_logging(data, context)


def create_patient_hash(patient_id: str) -> str:
    """
    Create patient hash for secure logging.

    Args:
        patient_id: Original patient identifier

    Returns:
        Secure hash for logging
    """
    return phi_monitor.create_patient_hash(patient_id)


def monitor_pipeline_safety(pipeline_name: str, data: Any, stage: str = "processing") -> bool:
    """
    Monitor data pipeline for PHI safety.

    Args:
        pipeline_name: Name of the pipeline
        data: Data being processed
        stage: Processing stage

    Returns:
        True if safe to proceed, False if PHI concerns exist
    """
    return phi_monitor.monitor_data_pipeline(pipeline_name, data, stage)


def phi_monitor_decorator(
    risk_level: str = "medium",
    operation_type: str = "healthcare_operation",
) -> Callable:
    """
    Decorator for PHI monitoring of healthcare methods.

    Args:
        risk_level: Expected PHI risk level (low, medium, high, critical)
        operation_type: Type of healthcare operation being performed

    Returns:
        Decorated function with PHI monitoring
    """

    def decorator(func: Callable) -> Callable:
        import functools

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract method context
            method_name = f"{func.__qualname__}"

            # Monitor inputs for PHI
            input_data = {"args": args[1:], "kwargs": kwargs}  # Skip 'self'
            input_result = phi_monitor.scan_for_phi(input_data, f"input_{method_name}")

            if input_result.phi_detected and input_result.risk_level.value in ["high", "critical"]:
                log_phi_alert(
                    f"PHI detected in method inputs: {method_name}",
                    input_result.to_dict(),
                    severity=input_result.risk_level.value,
                )

            try:
                # Execute the function
                result = await func(*args, **kwargs)

                # Monitor outputs for PHI
                if result is not None:
                    output_result = phi_monitor.scan_for_phi(result, f"output_{method_name}")

                    if output_result.phi_detected and output_result.risk_level.value in [
                        "high",
                        "critical",
                    ]:
                        log_phi_alert(
                            f"PHI detected in method outputs: {method_name}",
                            output_result.to_dict(),
                            severity=output_result.risk_level.value,
                        )

                return result

            except Exception as e:
                # Log error without exposing PHI
                logger = get_healthcare_logger("phi_monitor")
                logger.exception(
                    f"PHI monitored method failed: {method_name}",
                    extra={
                        "healthcare_context": {
                            "method": method_name,
                            "operation_type": operation_type,
                            "risk_level": risk_level,
                            "error_type": type(e).__name__,
                        },
                    },
                )
                raise

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Handle synchronous functions similarly
            method_name = f"{func.__qualname__}"

            input_data = {"args": args[1:], "kwargs": kwargs}
            input_result = phi_monitor.scan_for_phi(input_data, f"input_{method_name}")

            if input_result.phi_detected and input_result.risk_level.value in ["high", "critical"]:
                log_phi_alert(
                    f"PHI detected in method inputs: {method_name}",
                    input_result.to_dict(),
                    severity=input_result.risk_level.value,
                )

            try:
                result = func(*args, **kwargs)

                if result is not None:
                    output_result = phi_monitor.scan_for_phi(result, f"output_{method_name}")

                    if output_result.phi_detected and output_result.risk_level.value in [
                        "high",
                        "critical",
                    ]:
                        log_phi_alert(
                            f"PHI detected in method outputs: {method_name}",
                            output_result.to_dict(),
                            severity=output_result.risk_level.value,
                        )

                return result

            except Exception as e:
                logger = get_healthcare_logger("phi_monitor")
                logger.exception(
                    f"PHI monitored method failed: {method_name}",
                    extra={
                        "healthcare_context": {
                            "method": method_name,
                            "operation_type": operation_type,
                            "risk_level": risk_level,
                            "error_type": type(e).__name__,
                        },
                    },
                )
                raise

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# Make phi_monitor decorator available using the expected decorator syntax
