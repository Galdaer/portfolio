"""
Agent Compliance Monitoring Integration

Provides compliance monitoring integration for all healthcare agents
to ensure HIPAA compliance and PHI protection across the system.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from core.clients.business_services import get_business_client
from core.infrastructure.healthcare_logger import get_healthcare_logger

if TYPE_CHECKING:
    from core.clients.business_services import ServiceResponse

logger = get_healthcare_logger("agent.compliance_monitor")


class AgentComplianceMonitor:
    """Centralized compliance monitoring for healthcare agents"""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name

    async def log_agent_event(
        self,
        operation_type: str,
        event_data: dict[str, Any],
        user_id: str | None = None,
        patient_id: str | None = None,
        phi_risk_level: str = "medium",
        compliance_notes: str | None = None,
    ) -> bool:
        """
        Log compliance event for agent operation

        Args:
            operation_type: Type of operation (e.g., 'transcription', 'billing', 'insurance_verification')
            event_data: Event data (PHI will be sanitized)
            user_id: User performing the operation
            patient_id: Patient ID (will be masked in logs)
            phi_risk_level: Risk level (low, medium, high)
            compliance_notes: Additional compliance notes

        Returns:
            bool: True if logged successfully, False otherwise
        """
        try:
            async with get_business_client() as client:
                # Prepare compliance event
                audit_event = {
                    "event_type": "agent_operation",
                    "agent_name": self.agent_name,
                    "operation_type": operation_type,
                    "user_id": user_id,
                    "patient_id": patient_id,
                    "phi_risk_level": phi_risk_level,
                    "timestamp": datetime.now().isoformat(),
                    "event_data": event_data,
                    "compliance_notes": compliance_notes,
                }

                service_response: ServiceResponse = await client.log_audit_event(audit_event)

                if service_response.success:
                    logger.debug(f"Compliance event logged for {operation_type}")
                    return True
                logger.warning(f"Failed to log compliance event: {service_response.error}")
                return False

        except Exception as e:
            logger.exception(f"Compliance monitoring error: {e}")
            return False

    async def check_phi_compliance(self, text_content: str) -> dict[str, Any]:
        """
        Check text content for PHI compliance

        Args:
            text_content: Text to scan for PHI

        Returns:
            dict: Compliance check results
        """
        try:
            async with get_business_client() as client:
                phi_scan_request = {
                    "text": text_content,
                    "agent_name": self.agent_name,
                    "scan_type": "agent_content",
                }

                service_response: ServiceResponse = await client.scan_phi(phi_scan_request)

                if service_response.success:
                    return service_response.data
                logger.warning(f"PHI scan failed: {service_response.error}")
                return {"compliant": False, "error": service_response.error}

        except Exception as e:
            logger.exception(f"PHI compliance check error: {e}")
            return {"compliant": False, "error": str(e)}

    async def validate_operation_compliance(
        self,
        operation_type: str,
        operation_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Validate that an operation meets compliance requirements

        Args:
            operation_type: Type of operation
            operation_data: Operation data to validate

        Returns:
            dict: Validation results
        """
        try:
            async with get_business_client() as client:
                compliance_check = {
                    "check_type": "agent_operation",
                    "agent_name": self.agent_name,
                    "operation_type": operation_type,
                    "operation_data": operation_data,
                }

                service_response: ServiceResponse = await client.check_compliance(compliance_check)

                if service_response.success:
                    return service_response.data
                logger.warning(f"Compliance validation failed: {service_response.error}")
                return {"compliant": False, "error": service_response.error}

        except Exception as e:
            logger.exception(f"Operation compliance validation error: {e}")
            return {"compliant": False, "error": str(e)}


def compliance_monitor_decorator(
    operation_type: str,
    phi_risk_level: str = "medium",
    log_success: bool = True,
    log_failure: bool = True,
    validate_input: bool = False,
    validate_output: bool = False,
):
    """
    Decorator to add compliance monitoring to agent methods

    Args:
        operation_type: Type of operation for compliance logging
        phi_risk_level: Risk level (low, medium, high)
        log_success: Whether to log successful operations
        log_failure: Whether to log failed operations
        validate_input: Whether to validate input for PHI
        validate_output: Whether to validate output for PHI
    """
    def decorator(func):
        async def wrapper(self, *args, **kwargs):
            agent_name = getattr(self, "agent_name", "unknown_agent")
            compliance_monitor = AgentComplianceMonitor(agent_name)

            # Pre-operation validation
            if validate_input and args:
                input_text = str(args[0]) if args else ""
                phi_check = await compliance_monitor.check_phi_compliance(input_text)
                if not phi_check.get("compliant", True):
                    logger.warning(f"PHI detected in input for {operation_type}")
                    # Still continue but log the compliance issue
                    await compliance_monitor.log_agent_event(
                        operation_type=f"{operation_type}_phi_warning",
                        event_data={"phi_detected": True, "input_validated": True},
                        phi_risk_level="high",
                        compliance_notes="PHI detected in agent input",
                    )

            try:
                # Execute the original function
                result = await func(self, *args, **kwargs)

                # Post-operation validation
                if validate_output and result:
                    output_text = str(result)
                    phi_check = await compliance_monitor.check_phi_compliance(output_text)
                    if not phi_check.get("compliant", True):
                        logger.warning(f"PHI detected in output for {operation_type}")
                        await compliance_monitor.log_agent_event(
                            operation_type=f"{operation_type}_phi_warning",
                            event_data={"phi_detected": True, "output_validated": True},
                            phi_risk_level="high",
                            compliance_notes="PHI detected in agent output",
                        )

                # Log successful operation
                if log_success:
                    await compliance_monitor.log_agent_event(
                        operation_type=operation_type,
                        event_data={
                            "status": "success",
                            "args_count": len(args),
                            "kwargs_keys": list(kwargs.keys()),
                        },
                        phi_risk_level=phi_risk_level,
                        compliance_notes=f"Successful {operation_type} operation",
                    )

                return result

            except Exception as e:
                # Log failed operation
                if log_failure:
                    await compliance_monitor.log_agent_event(
                        operation_type=f"{operation_type}_error",
                        event_data={
                            "status": "error",
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                        },
                        phi_risk_level=phi_risk_level,
                        compliance_notes=f"Failed {operation_type} operation",
                    )

                raise  # Re-raise the original exception

        return wrapper
    return decorator


# Convenience function for easy integration
def get_compliance_monitor(agent_name: str) -> AgentComplianceMonitor:
    """Get compliance monitor instance for an agent"""
    return AgentComplianceMonitor(agent_name)
