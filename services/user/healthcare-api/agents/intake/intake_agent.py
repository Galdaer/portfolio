"""
Healthcare Intake Agent - Administrative Support Only
Handles patient registration, scheduling, and administrative workflows
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from agents import BaseHealthcareAgent
from core.infrastructure.healthcare_logger import (
    get_healthcare_logger,
    healthcare_agent_log,
    healthcare_log_method,
    log_healthcare_event,
)
from core.infrastructure.phi_monitor import phi_monitor, sanitize_healthcare_data, scan_for_phi

logger = get_healthcare_logger("agent.intake")


@dataclass
class IntakeResult:
    """Result from intake processing with healthcare compliance"""

    intake_id: str
    status: str
    patient_id: str | None
    appointment_id: str | None
    insurance_verified: bool
    required_documents: list[str]
    next_steps: list[str]
    validation_errors: list[str]
    administrative_notes: list[str]
    disclaimers: list[str]
    generated_at: datetime


class HealthcareIntakeAgent(BaseHealthcareAgent):
    """
    Healthcare Intake Agent for administrative support

    CRITICAL: Provides administrative support only, never medical advice.
    Focus: Registration, scheduling, documentation, insurance verification.
    """

    def __init__(
        self,
        mcp_client: Any,
        llm_client: Any,
        config_override: dict[str, Any] | None = None,
    ) -> None:
        super().__init__("intake", "intake")

        self.mcp_client = mcp_client
        self.llm_client = llm_client
        self.config = config_override or {}

        # Log agent initialization with healthcare context
        log_healthcare_event(
            logger,
            logging.INFO,
            "Healthcare Intake Agent initialized",
            context={
                "agent": "intake",
                "initialization": True,
                "phi_monitoring": True,
                "medical_advice_disabled": True,
                "database_required": True,
            },
            operation_type="agent_initialization",
        )

        # Standard healthcare disclaimers
        self.disclaimers = [
            "This system provides administrative support only, not medical advice.",
            "For medical questions, please consult with qualified healthcare professionals.",
            "In case of emergency, contact emergency services immediately.",
            "All patient data is handled in compliance with HIPAA regulations.",
            "Database connectivity required for healthcare operations.",
        ]

    async def initialize(self) -> None:
        """Initialize intake agent with database connectivity validation"""
        try:
            # Call parent initialization which validates database connectivity
            await self.initialize_agent()

            log_healthcare_event(
                logger,
                logging.INFO,
                "Intake Agent fully initialized with database connectivity",
                context={
                    "agent": "intake",
                    "database_validated": True,
                    "ready_for_operations": True,
                },
                operation_type="agent_ready",
            )
        except Exception as e:
            log_healthcare_event(
                logger,
                logging.CRITICAL,
                f"Intake Agent initialization failed: {e}",
                context={
                    "agent": "intake",
                    "initialization_failed": True,
                    "error": str(e),
                },
                operation_type="agent_initialization_error",
            )
            raise

    @healthcare_log_method(operation_type="patient_intake", phi_risk_level="high")
    @healthcare_agent_log("intake")
    async def _process_implementation(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Process intake request with administrative focus

        MEDICAL DISCLAIMER: Administrative support only - not medical advice.
        """
        session_id = request.get("session_id", "default")

        # PHI detection before processing
        if scan_for_phi(request):
            log_healthcare_event(
                logger,
                25,  # PHI_ALERT level
                "PHI detected in intake request - applying protection measures",
                context={"session_id": session_id, "request_type": "intake"},
                operation_type="phi_detection",
            )

        try:
            intake_type = request.get("intake_type", "new_patient_registration")
            patient_data = request.get("patient_data", {})

            # Sanitize patient data for logging
            sanitized_data = sanitize_healthcare_data(patient_data)
            log_healthcare_event(
                logger,
                logging.INFO,
                f"Processing intake request: {intake_type}",
                context={
                    "intake_type": intake_type,
                    "session_id": session_id,
                    "data_fields": list(sanitized_data.keys()),
                },
                operation_type="intake_processing",
            )

            if intake_type == "new_patient_registration":
                result = await self._process_new_patient_registration(patient_data, session_id)
            elif intake_type == "appointment_scheduling":
                result = await self._process_appointment_scheduling(patient_data, session_id)
            elif intake_type == "insurance_verification":
                result = await self._process_insurance_verification(patient_data, session_id)
            elif intake_type == "document_checklist":
                result = await self._process_document_checklist(patient_data, session_id)
            else:
                result = await self._process_general_intake(patient_data, session_id)

            return self._format_intake_response(result, session_id)

        except Exception as e:
            log_healthcare_event(
                logger,
                35,  # MEDICAL_ERROR level
                f"Intake processing error: {e}",
                context={"session_id": session_id, "error": str(e)},
                operation_type="intake_error",
            )
            return self._create_error_response(f"Intake processing failed: {str(e)}", session_id)

    @healthcare_log_method(operation_type="patient_registration", phi_risk_level="high")
    async def _process_new_patient_registration(
        self, patient_data: dict[str, Any], session_id: str,
    ) -> IntakeResult:
        """
        Process new patient registration with administrative validation
        """
        intake_id = self._generate_intake_id("registration")
        validation_errors = []
        administrative_notes = []

        # PHI monitoring for patient registration
        phi_result = phi_monitor.scan_for_phi(patient_data, "patient_registration")
        if phi_result.phi_detected:
            log_healthcare_event(
                logger,
                25,  # PHI_ALERT level
                "PHI detected in patient registration data",
                context={
                    "intake_id": intake_id,
                    "phi_risk_level": phi_result.risk_level.value,
                    "phi_types": [t.value for t in phi_result.phi_types],
                },
                operation_type="phi_detection",
            )

        # Validate required administrative fields
        required_fields = [
            "first_name",
            "last_name",
            "date_of_birth",
            "contact_phone",
            "contact_email",
            "emergency_contact",
            "insurance_primary",
        ]

        for field in required_fields:
            if not patient_data.get(field):
                validation_errors.append(f"Missing required field: {field}")

        # Validate data formatting
        if patient_data.get("date_of_birth"):
            if not self._validate_date_format(patient_data["date_of_birth"]):
                validation_errors.append("Date of birth must be in YYYY-MM-DD format")

        if patient_data.get("contact_phone"):
            if not self._validate_phone_format(patient_data["contact_phone"]):
                validation_errors.append("Phone number format invalid")

        # Administrative workflow steps
        next_steps = []
        if not validation_errors:
            patient_id = await self._create_patient_record(patient_data)
            next_steps = [
                "Complete insurance verification",
                "Upload required documents",
                "Schedule initial appointment",
                "Complete health history questionnaire",
            ]
            administrative_notes.append("Patient record created successfully")
        else:
            patient_id = None
            next_steps = ["Complete missing required information", "Resubmit registration form"]

        # Required documents checklist
        required_documents = [
            "Government-issued photo ID",
            "Insurance card (front and back)",
            "List of current medications",
            "Emergency contact information",
        ]

        return IntakeResult(
            intake_id=intake_id,
            status="completed" if not validation_errors else "pending_information",
            patient_id=patient_id,
            appointment_id=None,
            insurance_verified=False,
            required_documents=required_documents,
            next_steps=next_steps,
            validation_errors=validation_errors,
            administrative_notes=administrative_notes,
            disclaimers=self.disclaimers,
            generated_at=datetime.utcnow(),
        )

    async def _process_appointment_scheduling(
        self, patient_data: dict[str, Any], session_id: str,
    ) -> IntakeResult:
        """
        Process appointment scheduling with administrative workflow
        """
        intake_id = self._generate_intake_id("scheduling")
        validation_errors = []
        administrative_notes = []

        # Validate scheduling data
        patient_id = patient_data.get("patient_id")
        provider_preference = patient_data.get("provider_preference")
        preferred_times = patient_data.get("preferred_times", [])
        appointment_type = patient_data.get("appointment_type")

        if not patient_id:
            validation_errors.append("Patient ID required for scheduling")

        if not appointment_type:
            validation_errors.append("Appointment type must be specified")

        if not preferred_times:
            validation_errors.append("At least one preferred time slot required")

        # Administrative scheduling workflow
        appointment_id = None
        next_steps = []

        if not validation_errors:
            # Simulate appointment creation
            appointment_id = await self._create_appointment_request(
                patient_id or "unknown",
                provider_preference,
                preferred_times,
                appointment_type or "general",
            )
            next_steps = [
                "Appointment request submitted to scheduling team",
                "Confirmation will be sent within 24 hours",
                "Complete pre-appointment paperwork",
                "Arrive 15 minutes early for appointment",
            ]
            administrative_notes.append("Appointment request created successfully")
        else:
            next_steps = ["Complete missing scheduling information", "Resubmit scheduling request"]

        return IntakeResult(
            intake_id=intake_id,
            status="appointment_requested" if not validation_errors else "pending_information",
            patient_id=patient_id,
            appointment_id=appointment_id,
            insurance_verified=False,
            required_documents=["Insurance card", "Photo ID", "Completed intake forms"],
            next_steps=next_steps,
            validation_errors=validation_errors,
            administrative_notes=administrative_notes,
            disclaimers=self.disclaimers,
            generated_at=datetime.utcnow(),
        )

    async def _process_insurance_verification(
        self, patient_data: dict[str, Any], session_id: str,
    ) -> IntakeResult:
        """
        Process insurance verification with administrative validation
        """
        intake_id = self._generate_intake_id("insurance")
        validation_errors = []
        administrative_notes = []

        # Extract insurance information
        insurance_info = patient_data.get("insurance_info", {})
        patient_id = patient_data.get("patient_id")

        # Validate insurance data
        required_insurance_fields = [
            "insurance_provider",
            "policy_number",
            "group_number",
            "subscriber_name",
        ]

        for field in required_insurance_fields:
            if not insurance_info.get(field):
                validation_errors.append(f"Missing insurance field: {field}")

        # Simulate insurance verification
        insurance_verified = False
        next_steps = []

        if not validation_errors:
            # Administrative insurance verification workflow
            verification_result = await self._verify_insurance_coverage(insurance_info)
            insurance_verified = verification_result.get("verified", False)

            if insurance_verified:
                next_steps = [
                    "Insurance verified successfully",
                    "Copay information updated in system",
                    "Pre-authorization status checked",
                    "Ready to schedule appointments",
                ]
                administrative_notes.append("Insurance verification completed")
            else:
                next_steps = [
                    "Contact insurance provider to verify coverage",
                    "Check policy status and active dates",
                    "Provide updated insurance information",
                ]
                administrative_notes.append(
                    "Insurance verification failed - please update information",
                )
        else:
            next_steps = ["Complete missing insurance information", "Resubmit verification request"]

        return IntakeResult(
            intake_id=intake_id,
            status="verified" if insurance_verified else "verification_failed",
            patient_id=patient_id,
            appointment_id=None,
            insurance_verified=insurance_verified,
            required_documents=["Insurance card (front and back)", "Photo ID"],
            next_steps=next_steps,
            validation_errors=validation_errors,
            administrative_notes=administrative_notes,
            disclaimers=self.disclaimers,
            generated_at=datetime.utcnow(),
        )

    async def _process_document_checklist(
        self, patient_data: dict[str, Any], session_id: str,
    ) -> IntakeResult:
        """
        Generate document checklist for patient intake
        """
        intake_id = self._generate_intake_id("documents")
        appointment_type = patient_data.get("appointment_type", "general")
        patient_type = patient_data.get("patient_type", "new")

        # Generate comprehensive document checklist
        required_documents = ["Government-issued photo ID", "Insurance card (front and back)"]

        if patient_type == "new":
            required_documents.extend(
                [
                    "Completed new patient registration form",
                    "Medical history questionnaire",
                    "Emergency contact information",
                    "List of current medications and dosages",
                    "Pharmacy contact information",
                ],
            )

        if appointment_type == "specialist":
            required_documents.extend(
                [
                    "Referral from primary care physician",
                    "Previous test results or imaging",
                    "Specialist-specific intake forms",
                ],
            )

        # Administrative next steps
        next_steps = [
            "Review document checklist",
            "Gather all required documents",
            "Upload or bring documents to appointment",
            "Complete all forms before appointment date",
        ]

        return IntakeResult(
            intake_id=intake_id,
            status="checklist_generated",
            patient_id=patient_data.get("patient_id"),
            appointment_id=None,
            insurance_verified=False,
            required_documents=required_documents,
            next_steps=next_steps,
            validation_errors=[],
            administrative_notes=["Document checklist generated based on appointment type"],
            disclaimers=self.disclaimers,
            generated_at=datetime.utcnow(),
        )

    async def _process_general_intake(
        self, patient_data: dict[str, Any], session_id: str,
    ) -> IntakeResult:
        """
        Process general intake request with basic administrative support
        """
        intake_id = self._generate_intake_id("general")

        return IntakeResult(
            intake_id=intake_id,
            status="general_support",
            patient_id=patient_data.get("patient_id"),
            appointment_id=None,
            insurance_verified=False,
            required_documents=[
                "Photo ID",
                "Insurance card",
                "Completed intake forms",
            ],
            next_steps=[
                "Contact our administrative team for specific assistance",
                "Complete online patient portal registration",
                "Review our patient resources and FAQ",
            ],
            validation_errors=[],
            administrative_notes=["General intake support provided"],
            disclaimers=self.disclaimers,
            generated_at=datetime.utcnow(),
        )

    async def _create_patient_record(self, patient_data: dict[str, Any]) -> str:
        """Create patient record in system (administrative function)"""
        # Simulate patient record creation
        patient_id = f"PAT_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        logger.info(f"Patient record created: {patient_id}")
        return patient_id

    async def _create_appointment_request(
        self,
        patient_id: str,
        provider_preference: str | None,
        preferred_times: list[str],
        appointment_type: str,
    ) -> str:
        """Create appointment request (administrative function)"""
        # Simulate appointment request creation
        appointment_id = f"APT_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        logger.info(f"Appointment request created: {appointment_id}")
        return appointment_id

    async def _verify_insurance_coverage(self, insurance_info: dict[str, Any]) -> dict[str, Any]:
        """Verify insurance coverage (administrative function)"""
        # Simulate insurance verification
        # In real implementation, this would call insurance verification services
        policy_number = insurance_info.get("policy_number", "")

        # Basic validation check
        verified = len(policy_number) >= 6  # Simple validation rule

        return {
            "verified": verified,
            "copay": 25.00 if verified else None,
            "deductible_met": False if verified else None,
            "verification_date": datetime.utcnow().isoformat(),
        }

    def _validate_date_format(self, date_string: str) -> bool:
        """Validate date format (YYYY-MM-DD)"""
        try:
            datetime.strptime(date_string, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def _validate_phone_format(self, phone: str) -> bool:
        """Validate phone number format"""
        # Remove non-digit characters
        digits_only = "".join(filter(str.isdigit, phone))
        # US phone numbers should have 10 digits
        return len(digits_only) == 10

    def _generate_intake_id(self, intake_type: str) -> str:
        """Generate unique intake ID"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"INT_{intake_type.upper()}_{timestamp}"

    def _format_intake_response(self, result: IntakeResult, session_id: str) -> dict[str, Any]:
        """Format intake result for API response"""
        return {
            "agent_type": "intake",
            "session_id": session_id,
            "intake_id": result.intake_id,
            "status": result.status,
            "patient_id": result.patient_id,
            "appointment_id": result.appointment_id,
            "insurance_verified": result.insurance_verified,
            "required_documents": result.required_documents,
            "next_steps": result.next_steps,
            "validation_errors": result.validation_errors,
            "administrative_notes": result.administrative_notes,
            "disclaimers": result.disclaimers,
            "generated_at": result.generated_at.isoformat(),
            "success": len(result.validation_errors) == 0,
        }

    def _create_error_response(self, error_message: str, session_id: str) -> dict[str, Any]:
        """Create standardized error response"""
        return {
            "agent_type": "intake",
            "session_id": session_id,
            "error": error_message,
            "success": False,
            "disclaimers": self.disclaimers,
            "generated_at": datetime.utcnow().isoformat(),
        }
