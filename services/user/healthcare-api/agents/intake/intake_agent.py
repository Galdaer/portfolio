"""
Healthcare Intake Agent - Administrative Support Only
Handles patient registration, scheduling, and administrative workflows
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from agents import BaseHealthcareAgent
from agents.transcription.transcription_agent import TranscriptionAgent
from config.config_loader import get_healthcare_config
from core.compliance.agent_compliance_monitor import compliance_monitor_decorator
from core.enhanced_sessions import EnhancedSessionManager
from core.infrastructure.agent_logging_utils import (
    enhanced_agent_method,
)
from core.infrastructure.healthcare_logger import (
    get_healthcare_logger,
    healthcare_agent_log,
    healthcare_log_method,
    log_healthcare_event,
)
from core.infrastructure.phi_monitor import phi_monitor, sanitize_healthcare_data, scan_for_phi
from core.orchestration import WorkflowType, workflow_orchestrator

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
    voice_session_id: str | None = None
    transcription_confidence: float | None = None
    medical_terms_extracted: list[str] | None = None


@dataclass
class VoiceIntakeResult:
    """Result from voice intake processing"""

    voice_session_id: str
    transcription_text: str
    confidence_score: float
    medical_terms: list[str]
    intake_form_data: dict[str, Any]
    form_completion_percentage: float
    phi_detected: bool
    phi_sanitized: bool
    processing_timestamp: datetime
    status: str  # "processing", "completed", "failed"


class VoiceIntakeProcessor:
    """
    Voice processing component for real-time intake form completion

    Integrates with TranscriptionAgent to process spoken patient responses
    and automatically populate intake forms with PHI protection.
    """

    def __init__(self, transcription_agent: TranscriptionAgent, session_manager: EnhancedSessionManager):
        self.transcription_agent = transcription_agent
        self.session_manager = session_manager
        self.logger = get_healthcare_logger("voice_intake_processor")

        # Voice-to-form field mappings for common intake questions
        self.field_mappings = {
            "first_name": ["first name", "given name", "what is your first name", "your first name"],
            "last_name": ["last name", "family name", "surname", "what is your last name"],
            "date_of_birth": ["date of birth", "birthday", "birth date", "when were you born"],
            "contact_phone": ["phone number", "telephone", "contact number", "phone"],
            "contact_email": ["email", "email address", "electronic mail"],
            "emergency_contact": ["emergency contact", "emergency person", "emergency number"],
            "insurance_primary": ["insurance", "insurance company", "health insurance", "insurance provider"],
            "chief_complaint": ["chief complaint", "main concern", "reason for visit", "why are you here"],
            "current_medications": ["medications", "drugs", "pills", "medicine", "current medications"],
            "allergies": ["allergies", "allergic to", "drug allergies", "food allergies"],
        }

        # Form completion tracking
        self.active_voice_sessions: dict[str, dict[str, Any]] = {}

    @healthcare_log_method(operation_type="voice_intake_start", phi_risk_level="high")
    async def start_voice_intake_session(self, patient_id: str, intake_type: str = "new_patient_registration") -> str:
        """
        Start a new voice intake session for a patient

        Args:
            patient_id: Patient identifier
            intake_type: Type of intake being performed

        Returns:
            str: Voice session ID
        """
        try:
            voice_session_id = f"voice_intake_{patient_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Initialize session tracking
            self.active_voice_sessions[voice_session_id] = {
                "patient_id": patient_id,
                "intake_type": intake_type,
                "start_time": datetime.now(),
                "form_data": {},
                "transcription_buffer": [],
                "current_question": None,
                "completion_percentage": 0.0,
                "medical_terms_collected": [],
                "phi_incidents": [],
            }

            # Store session in enhanced session manager
            await self.session_manager.create_session(
                user_id=patient_id,
                session_type="voice_intake",
                metadata={
                    "voice_session_id": voice_session_id,
                    "intake_type": intake_type,
                    "phi_protection_enabled": True,
                },
            )

            log_healthcare_event(
                self.logger,
                logging.INFO,
                f"Voice intake session started: {voice_session_id}",
                context={
                    "voice_session_id": voice_session_id,
                    "patient_id": patient_id,
                    "intake_type": intake_type,
                },
                operation_type="voice_intake_session_start",
            )

            return voice_session_id

        except Exception as e:
            log_healthcare_event(
                self.logger,
                logging.ERROR,
                f"Failed to start voice intake session: {str(e)}",
                context={"patient_id": patient_id, "error": str(e)},
                operation_type="voice_intake_session_error",
            )
            raise

    @healthcare_log_method(operation_type="voice_chunk_processing", phi_risk_level="high")
    @compliance_monitor_decorator(
        operation_type="patient_intake_voice",
        phi_risk_level="high",
        validate_input=True
    )
    async def process_voice_chunk(self, voice_session_id: str, audio_data: dict[str, Any]) -> VoiceIntakeResult:
        """
        Process real-time voice audio chunk and update intake form

        Args:
            voice_session_id: Active voice intake session ID
            audio_data: Audio chunk data for transcription

        Returns:
            VoiceIntakeResult: Processing result with form updates
        """
        try:
            if voice_session_id not in self.active_voice_sessions:
                msg = f"Voice session not found: {voice_session_id}"
                raise ValueError(msg)

            session_data = self.active_voice_sessions[voice_session_id]

            # Process audio chunk through transcription agent
            transcription_result = await self.transcription_agent.process_real_time_audio(
                audio_data=audio_data,
                session_id=voice_session_id,
                doctor_id="intake_agent",
            )

            transcribed_text = transcription_result.get("transcription", "")
            confidence_score = transcription_result.get("confidence", 0.0)
            medical_terms = transcription_result.get("medical_terms", [])
            phi_detected = transcription_result.get("phi_sanitized", False)

            # Update session buffer
            session_data["transcription_buffer"].append({
                "text": transcribed_text,
                "confidence": confidence_score,
                "timestamp": datetime.now(),
                "medical_terms": medical_terms,
            })

            # Extract form field data from transcription
            form_updates = await self._extract_form_data_from_speech(transcribed_text, session_data)

            # Update form data
            session_data["form_data"].update(form_updates)
            session_data["medical_terms_collected"].extend(medical_terms)

            if phi_detected:
                session_data["phi_incidents"].append({
                    "timestamp": datetime.now(),
                    "text_sample": transcribed_text[:50] + "..." if len(transcribed_text) > 50 else transcribed_text,
                })

            # Calculate completion percentage
            completion_percentage = self._calculate_form_completion(session_data["form_data"], session_data["intake_type"])
            session_data["completion_percentage"] = completion_percentage

            # Store updated session data
            await self.session_manager.store_message(
                session_id=voice_session_id,
                role="assistant",
                content=f"Voice input processed: {len(transcribed_text)} chars, {len(form_updates)} field updates",
                metadata={
                    "voice_processing": True,
                    "form_updates": form_updates,
                    "medical_terms": medical_terms,
                    "completion_percentage": completion_percentage,
                },
            )

            log_healthcare_event(
                self.logger,
                logging.INFO,
                f"Voice chunk processed for session {voice_session_id}",
                context={
                    "voice_session_id": voice_session_id,
                    "transcription_length": len(transcribed_text),
                    "confidence_score": confidence_score,
                    "form_updates_count": len(form_updates),
                    "completion_percentage": completion_percentage,
                    "phi_detected": phi_detected,
                },
                operation_type="voice_chunk_processed",
            )

            return VoiceIntakeResult(
                voice_session_id=voice_session_id,
                transcription_text=transcribed_text,
                confidence_score=confidence_score,
                medical_terms=list(set(session_data["medical_terms_collected"])),
                intake_form_data=session_data["form_data"].copy(),
                form_completion_percentage=completion_percentage,
                phi_detected=phi_detected,
                phi_sanitized=phi_detected,
                processing_timestamp=datetime.now(),
                status="processing" if completion_percentage < 80.0 else "completed",
            )

        except Exception as e:
            log_healthcare_event(
                self.logger,
                logging.ERROR,
                f"Voice chunk processing failed: {str(e)}",
                context={
                    "voice_session_id": voice_session_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                operation_type="voice_processing_error",
            )

            return VoiceIntakeResult(
                voice_session_id=voice_session_id,
                transcription_text="",
                confidence_score=0.0,
                medical_terms=[],
                intake_form_data={},
                form_completion_percentage=0.0,
                phi_detected=False,
                phi_sanitized=False,
                processing_timestamp=datetime.now(),
                status="failed",
            )

    async def _extract_form_data_from_speech(self, transcribed_text: str, session_data: dict[str, Any]) -> dict[str, Any]:
        """
        Extract structured form field data from transcribed speech

        Args:
            transcribed_text: Text from speech transcription
            session_data: Current session state

        Returns:
            dict: Extracted form field updates
        """
        form_updates = {}
        text_lower = transcribed_text.lower()

        # Simple pattern matching for common intake responses
        # In production, this would use more sophisticated NLP

        # Extract names
        if any(pattern in text_lower for pattern in self.field_mappings["first_name"]):
            # Look for name patterns after the question words
            import re
            name_pattern = r"(?:name is|i am|i'm|call me)\s+([a-zA-Z]+)"
            match = re.search(name_pattern, text_lower)
            if match:
                form_updates["first_name"] = match.group(1).title()

        # Extract phone numbers
        if any(pattern in text_lower for pattern in self.field_mappings["contact_phone"]):
            phone_pattern = r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"
            match = re.search(phone_pattern, transcribed_text)
            if match:
                form_updates["contact_phone"] = match.group(0)

        # Extract common medical complaints
        if any(pattern in text_lower for pattern in self.field_mappings["chief_complaint"]):
            # Look for symptoms or complaints
            complaint_keywords = ["pain", "hurt", "ache", "sick", "feel", "problem", "issue", "concern"]
            for keyword in complaint_keywords:
                if keyword in text_lower:
                    # Extract the surrounding context
                    start = max(0, text_lower.find(keyword) - 20)
                    end = min(len(transcribed_text), text_lower.find(keyword) + 50)
                    form_updates["chief_complaint"] = transcribed_text[start:end].strip()
                    break

        # Extract medication mentions
        if any(pattern in text_lower for pattern in self.field_mappings["current_medications"]):
            # Look for drug name patterns
            med_keywords = ["taking", "prescribed", "medication", "pill", "drug"]
            for keyword in med_keywords:
                if keyword in text_lower:
                    # Extract medication context
                    start = text_lower.find(keyword)
                    end = min(len(transcribed_text), start + 100)
                    current_meds = form_updates.get("current_medications", "")
                    new_med_text = transcribed_text[start:end].strip()
                    form_updates["current_medications"] = f"{current_meds}; {new_med_text}" if current_meds else new_med_text

        # Extract allergy information
        if any(pattern in text_lower for pattern in self.field_mappings["allergies"]):
            allergy_keywords = ["allergic", "allergy", "react to", "can't take"]
            for keyword in allergy_keywords:
                if keyword in text_lower:
                    start = text_lower.find(keyword)
                    end = min(len(transcribed_text), start + 80)
                    form_updates["allergies"] = transcribed_text[start:end].strip()
                    break

        return form_updates

    def _calculate_form_completion(self, form_data: dict[str, Any], intake_type: str) -> float:
        """
        Calculate percentage completion of intake form based on filled fields

        Args:
            form_data: Current form field data
            intake_type: Type of intake form

        Returns:
            float: Completion percentage (0.0 to 100.0)
        """
        if intake_type == "new_patient_registration":
            required_fields = [
                "first_name", "last_name", "date_of_birth",
                "contact_phone", "contact_email", "emergency_contact",
                "insurance_primary",
            ]
        elif intake_type == "appointment_scheduling":
            required_fields = ["patient_id", "appointment_type", "preferred_times"]
        else:
            required_fields = ["patient_id"]

        filled_fields = sum(1 for field in required_fields if form_data.get(field))
        return (filled_fields / len(required_fields)) * 100.0 if required_fields else 100.0

    async def finalize_voice_intake_session(self, voice_session_id: str) -> dict[str, Any]:
        """
        Complete and finalize a voice intake session

        Args:
            voice_session_id: Voice session to finalize

        Returns:
            dict: Final session summary and extracted data
        """
        try:
            if voice_session_id not in self.active_voice_sessions:
                msg = f"Voice session not found: {voice_session_id}"
                raise ValueError(msg)

            session_data = self.active_voice_sessions[voice_session_id]

            # Create final session summary
            session_summary = {
                "voice_session_id": voice_session_id,
                "patient_id": session_data["patient_id"],
                "intake_type": session_data["intake_type"],
                "duration_seconds": (datetime.now() - session_data["start_time"]).total_seconds(),
                "form_data": session_data["form_data"],
                "completion_percentage": session_data["completion_percentage"],
                "total_transcriptions": len(session_data["transcription_buffer"]),
                "medical_terms_extracted": list(set(session_data["medical_terms_collected"])),
                "phi_incidents_count": len(session_data["phi_incidents"]),
                "finalized_at": datetime.now(),
            }

            # Store final session data in enhanced session manager
            await self.session_manager.store_message(
                session_id=voice_session_id,
                role="system",
                content="Voice intake session finalized",
                metadata={
                    "session_finalized": True,
                    "final_summary": session_summary,
                },
            )

            # Clean up active session
            del self.active_voice_sessions[voice_session_id]

            log_healthcare_event(
                self.logger,
                logging.INFO,
                f"Voice intake session finalized: {voice_session_id}",
                context=session_summary,
                operation_type="voice_intake_session_finalized",
            )

            return session_summary

        except Exception as e:
            log_healthcare_event(
                self.logger,
                logging.ERROR,
                f"Failed to finalize voice intake session: {str(e)}",
                context={"voice_session_id": voice_session_id, "error": str(e)},
                operation_type="voice_session_finalization_error",
            )
            raise


class HealthcareIntakeAgent(BaseHealthcareAgent):
    """
    Healthcare Intake Agent for administrative support with voice processing capabilities

    CRITICAL: Provides administrative support only, never medical advice.
    Focus: Registration, scheduling, documentation, insurance verification.
    Enhanced with voice processing for real-time form completion.
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

        # Load healthcare configuration
        try:
            self.intake_config = get_healthcare_config().intake_agent
        except Exception as e:
            logger.warning(f"Could not load intake configuration: {e}, using defaults")
            self.intake_config = self._get_default_config()

        # Initialize transcription agent for voice processing
        self.transcription_agent = TranscriptionAgent(mcp_client=mcp_client, llm_client=llm_client)

        # Initialize enhanced session manager for cross-agent data sharing
        self.session_manager = EnhancedSessionManager()

        # Initialize voice intake processor
        self.voice_processor = VoiceIntakeProcessor(
            transcription_agent=self.transcription_agent,
            session_manager=self.session_manager,
        )

        # Log agent initialization with healthcare context
        log_healthcare_event(
            logger,
            logging.INFO,
            "Healthcare Intake Agent initialized with voice processing",
            context={
                "agent": "intake",
                "initialization": True,
                "phi_monitoring": True,
                "medical_advice_disabled": True,
                "database_required": True,
                "voice_processing_enabled": True,
                "transcription_integration": True,
                "enhanced_sessions_enabled": True,
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
        """Initialize intake agent with database connectivity validation and voice processing"""
        try:
            # Call parent initialization which validates database connectivity
            await self.initialize_agent()

            # Initialize transcription agent
            await self.transcription_agent.initialize()

            # Initialize session manager
            await self.session_manager.initialize()

            log_healthcare_event(
                logger,
                logging.INFO,
                "Intake Agent fully initialized with database connectivity and voice processing",
                context={
                    "agent": "intake",
                    "database_validated": True,
                    "voice_processing_ready": True,
                    "transcription_agent_ready": True,
                    "session_manager_ready": True,
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

    # Voice Processing Methods

    @healthcare_log_method(operation_type="voice_intake_start", phi_risk_level="high")
    async def start_voice_intake(self, patient_id: str, intake_type: str = "new_patient_registration") -> dict[str, Any]:
        """
        Start a new voice intake session for real-time form completion

        Args:
            patient_id: Patient identifier
            intake_type: Type of intake (new_patient_registration, appointment_scheduling, etc.)

        Returns:
            dict: Voice session information and instructions
        """
        try:
            voice_session_id = await self.voice_processor.start_voice_intake_session(patient_id, intake_type)

            return {
                "success": True,
                "voice_session_id": voice_session_id,
                "intake_type": intake_type,
                "status": "voice_session_started",
                "instructions": [
                    "Voice intake session is now active",
                    "Please speak clearly when providing information",
                    "The system will automatically populate your intake form",
                    "All voice data is processed with PHI protection",
                ],
                "disclaimers": self.disclaimers,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to start voice intake: {str(e)}",
                "disclaimers": self.disclaimers,
            }

    @healthcare_log_method(operation_type="voice_intake_process", phi_risk_level="high")
    async def process_voice_input(self, voice_session_id: str, audio_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process voice audio input and update intake form in real-time

        Args:
            voice_session_id: Active voice intake session
            audio_data: Audio chunk data for processing

        Returns:
            dict: Processing result with form updates
        """
        try:
            voice_result = await self.voice_processor.process_voice_chunk(voice_session_id, audio_data)

            return {
                "success": True,
                "voice_session_id": voice_session_id,
                "transcription": voice_result.transcription_text,
                "confidence": voice_result.confidence_score,
                "form_data": voice_result.intake_form_data,
                "completion_percentage": voice_result.form_completion_percentage,
                "medical_terms_extracted": voice_result.medical_terms,
                "phi_protected": voice_result.phi_sanitized,
                "status": voice_result.status,
                "timestamp": voice_result.processing_timestamp.isoformat(),
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Voice processing failed: {str(e)}",
                "voice_session_id": voice_session_id,
            }

    @healthcare_log_method(operation_type="voice_intake_complete", phi_risk_level="high")
    async def complete_voice_intake(self, voice_session_id: str) -> dict[str, Any]:
        """
        Complete voice intake session and generate final intake result

        Args:
            voice_session_id: Voice session to complete

        Returns:
            dict: Completed intake result with all collected data
        """
        try:
            # Finalize voice session
            session_summary = await self.voice_processor.finalize_voice_intake_session(voice_session_id)

            # Create intake result from voice data
            form_data = session_summary["form_data"]
            intake_type = session_summary["intake_type"]

            # Process the collected form data as a standard intake request

            # Use existing intake processing logic
            if intake_type == "new_patient_registration":
                result = await self._process_new_patient_registration(form_data, voice_session_id)
            elif intake_type == "appointment_scheduling":
                result = await self._process_appointment_scheduling(form_data, voice_session_id)
            elif intake_type == "insurance_verification":
                result = await self._process_insurance_verification(form_data, voice_session_id)
            else:
                result = await self._process_general_intake(form_data, voice_session_id)

            # Enhance result with voice processing data
            result.voice_session_id = voice_session_id
            result.transcription_confidence = session_summary.get("completion_percentage", 0.0) / 100.0
            result.medical_terms_extracted = session_summary.get("medical_terms_extracted", [])

            return self._format_voice_intake_response(result, session_summary)

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to complete voice intake: {str(e)}",
                "voice_session_id": voice_session_id,
                "disclaimers": self.disclaimers,
            }

    def _format_voice_intake_response(self, result: IntakeResult, session_summary: dict[str, Any]) -> dict[str, Any]:
        """
        Format voice intake result for API response with enhanced data

        Args:
            result: Standard intake result
            session_summary: Voice session summary data

        Returns:
            dict: Enhanced response with voice processing information
        """
        response = self._format_intake_response(result, session_summary["voice_session_id"])

        # Add voice-specific data
        response.update({
            "voice_processing": {
                "voice_session_id": session_summary["voice_session_id"],
                "session_duration_seconds": session_summary["duration_seconds"],
                "total_transcriptions": session_summary["total_transcriptions"],
                "form_completion_percentage": session_summary["completion_percentage"],
                "medical_terms_extracted": session_summary["medical_terms_extracted"],
                "phi_incidents_count": session_summary["phi_incidents_count"],
                "voice_to_form_processing": True,
            },
            "enhanced_features": {
                "real_time_transcription": True,
                "automatic_form_population": True,
                "phi_protection_active": True,
                "medical_terminology_extraction": True,
                "cross_agent_integration": True,
            },
        })

        return response

    @enhanced_agent_method(operation_type="patient_intake", phi_risk_level="high", track_performance=True)
    @healthcare_agent_log("intake")
    async def _process_implementation(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Process intake request with administrative focus and voice processing support

        MEDICAL DISCLAIMER: Administrative support only - not medical advice.
        """
        session_id = request.get("session_id", "default")

        # Initialize workflow logger for intake processing
        workflow_logger = self.get_workflow_logger()
        workflow_logger.start_workflow("intake_processing", {
            "session_id": session_id,
            "has_voice_session": "voice_session_id" in request,
            "has_audio_data": "audio_data" in request,
            "request_keys": list(request.keys()),
        })

        # Check if this is a voice processing request
        if "voice_session_id" in request and "audio_data" in request:
            workflow_logger.log_step("routing_to_voice_processing")
            workflow_logger.finish_workflow("completed", {"routed_to": "voice_processing"})
            return await self.process_voice_input(request["voice_session_id"], request["audio_data"])

        if "start_voice_intake" in request:
            workflow_logger.log_step("starting_voice_intake")
            patient_id = request.get("patient_id", "unknown")
            intake_type = request.get("intake_type", "new_patient_registration")
            workflow_logger.finish_workflow("completed", {"routed_to": "start_voice_intake"})
            return await self.start_voice_intake(patient_id, intake_type)

        if "complete_voice_intake" in request:
            workflow_logger.log_step("completing_voice_intake")
            voice_session_id = request.get("voice_session_id")
            if not voice_session_id:
                workflow_logger.finish_workflow("failed", {"error": "missing_voice_session_id"})
                return {
                    "success": False,
                    "error": "voice_session_id required for completing voice intake",
                    "disclaimers": self.disclaimers,
                }
            workflow_logger.finish_workflow("completed", {"routed_to": "complete_voice_intake"})
            return await self.complete_voice_intake(voice_session_id)

        # PHI detection before processing
        workflow_logger.log_step("phi_scanning")
        if scan_for_phi(request):
            workflow_logger.log_step("phi_detected", level=logging.WARNING)
            log_healthcare_event(
                logger,
                25,  # PHI_ALERT level
                "PHI detected in intake request - applying protection measures",
                context={"session_id": session_id, "request_type": "intake"},
                operation_type="phi_detection",
            )

        try:
            workflow_logger.log_step("extract_intake_parameters")
            intake_type = request.get("intake_type", "new_patient_registration")
            patient_data = request.get("patient_data", {})

            # Sanitize patient data for logging
            sanitized_data = sanitize_healthcare_data(patient_data)
            workflow_logger.log_step("sanitize_patient_data", {
                "intake_type": intake_type,
                "data_fields_count": len(sanitized_data),
            })

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

            workflow_logger.log_step("route_intake_processing", {"intake_type": intake_type})

            if intake_type == "new_patient_registration":
                workflow_logger.log_step("processing_new_patient_registration")
                result = await self._process_new_patient_registration(patient_data, session_id)
            elif intake_type == "appointment_scheduling":
                workflow_logger.log_step("processing_appointment_scheduling")
                result = await self._process_appointment_scheduling(patient_data, session_id)
            elif intake_type == "insurance_verification":
                workflow_logger.log_step("processing_insurance_verification")
                result = await self._process_insurance_verification(patient_data, session_id)
            elif intake_type == "document_checklist":
                workflow_logger.log_step("processing_document_checklist")
                result = await self._process_document_checklist(patient_data, session_id)
            else:
                workflow_logger.log_step("processing_general_intake")
                result = await self._process_general_intake(patient_data, session_id)

            workflow_logger.log_step("format_intake_response", {
                "result_status": result.status if result else "no_result",
                "intake_id": result.intake_id if result else None,
            })

            response = self._format_intake_response(result, session_id)

            workflow_logger.finish_workflow("completed", {
                "final_status": result.status if result else "unknown",
                "intake_id": result.intake_id if result else None,
                "validation_errors_count": len(result.validation_errors) if result else 0,
            })

            return response

        except Exception as e:
            workflow_logger.finish_workflow("failed", error=e)

            log_healthcare_event(
                logger,
                35,  # MEDICAL_ERROR level
                f"Intake processing error: {e}",
                context={"session_id": session_id, "error": str(e)},
                operation_type="intake_error",
            )
            return self._create_error_response(f"Intake processing failed: {str(e)}", session_id)
        finally:
            # Critical: Clean up MCP connection to prevent runaway tasks
            try:
                if hasattr(self.mcp_client, "disconnect"):
                    await self.mcp_client.disconnect()
                    logger.debug("MCP client disconnected after intake processing")
            except Exception as cleanup_error:
                logger.warning(f"Error during MCP cleanup: {cleanup_error}")

    @healthcare_log_method(operation_type="patient_registration", phi_risk_level="high")
    async def _process_new_patient_registration(
        self,
        patient_data: dict[str, Any],
        session_id: str,
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

        # Get configuration-based requirements
        required_fields = self._get_required_fields("new_patient_registration")
        required_documents = self._get_required_documents("new_patient_registration", "new")
        next_steps_template = self._get_next_steps("new_patient_registration")

        # Validate required fields
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
            next_steps = next_steps_template
            administrative_notes.append("Patient record created successfully")
        else:
            patient_id = None
            next_steps = ["Complete missing required information", "Resubmit registration form"]

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
        self,
        patient_data: dict[str, Any],
        session_id: str,
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
        self,
        patient_data: dict[str, Any],
        session_id: str,
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
        self,
        patient_data: dict[str, Any],
        session_id: str,
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
        self,
        patient_data: dict[str, Any],
        session_id: str,
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
        """Generate intake ID with type prefix"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"INTAKE_{intake_type.upper()}_{timestamp}"

    def _get_required_documents(self, intake_type: str, patient_type: str = "existing") -> list[str]:
        """Get required documents from configuration based on intake and patient type"""
        if hasattr(self.intake_config, "document_requirements"):
            doc_req = self.intake_config.document_requirements

            # Handle specific intake types
            if intake_type == "insurance_verification":
                return getattr(doc_req, "insurance_verification", [])
            if intake_type == "appointment_scheduling":
                return getattr(doc_req, "appointment_scheduling", [])
            if intake_type == "general_intake":
                return getattr(doc_req, "general_intake", [])

            # Build comprehensive document list
            documents = getattr(doc_req, "base_documents", []).copy()

            if patient_type == "new":
                documents.extend(getattr(doc_req, "new_patient_additional", []))

            if intake_type == "specialist":
                documents.extend(getattr(doc_req, "specialist_additional", []))

            return documents
        # Default document requirements
        return self._get_default_documents(intake_type, patient_type)

    def _get_next_steps(self, intake_type: str) -> list[str]:
        """Get next steps from configuration based on intake type"""
        if hasattr(self.intake_config, "next_steps_templates"):
            templates = self.intake_config.next_steps_templates
            return templates.get(intake_type, templates.get("general_intake", []))
        return self._get_default_next_steps(intake_type)

    def _get_required_fields(self, intake_type: str) -> list[str]:
        """Get required fields from configuration based on intake type"""
        if hasattr(self.intake_config, "required_fields"):
            return self.intake_config.required_fields.get(intake_type, [])
        return self._get_default_required_fields(intake_type)


    def _get_default_config(self) -> Any:
        """Get default configuration when config loader fails"""
        from types import SimpleNamespace

        default_config = SimpleNamespace()
        default_config.document_requirements = SimpleNamespace()
        default_config.document_requirements.base_documents = [
            "Photo ID", "Insurance Card", "Emergency Contact Information",
        ]
        default_config.document_requirements.new_patient_additional = [
            "Medical History Form", "Medication List", "Allergy Information",
        ]
        default_config.document_requirements.insurance_verification = [
            "Current Insurance Card", "Photo ID",
        ]
        default_config.document_requirements.appointment_scheduling = [
            "Insurance Verification",
        ]
        default_config.document_requirements.general_intake = [
            "Completed Intake Form",
        ]

        default_config.next_steps_templates = {
            "new_patient_registration": [
                "Complete registration forms",
                "Schedule initial appointment",
                "Upload required documents",
            ],
            "appointment_scheduling": [
                "Verify insurance coverage",
                "Confirm appointment time",
                "Prepare for visit",
            ],
            "insurance_verification": [
                "Review benefits",
                "Confirm coverage details",
                "Check copay requirements",
            ],
            "general_intake": [
                "Review provided information",
                "Complete any missing fields",
                "Continue with process",
            ],
        }

        default_config.required_fields = {
            "new_patient_registration": [
                "first_name", "last_name", "date_of_birth",
                "contact_phone", "contact_email", "insurance_primary",
            ],
            "appointment_scheduling": [
                "patient_id", "appointment_type", "preferred_date", "preferred_time",
            ],
            "insurance_verification": [
                "patient_id", "insurance_provider", "member_id", "group_number",
            ],
            "document_checklist": [
                "patient_id", "checklist_type",
            ],
            "general_intake": [
                "patient_id",
            ],
        }

        return default_config

    def _get_default_documents(self, intake_type: str, patient_type: str = "existing") -> list[str]:
        """Get default document requirements when configuration is unavailable"""
        config = self._get_default_config()
        doc_req = config.document_requirements

        if intake_type == "insurance_verification":
            return doc_req.insurance_verification
        if intake_type == "appointment_scheduling":
            return doc_req.appointment_scheduling
        if intake_type == "general_intake":
            return doc_req.general_intake

        documents = doc_req.base_documents.copy()
        if patient_type == "new":
            documents.extend(doc_req.new_patient_additional)

        return documents

    def _get_default_next_steps(self, intake_type: str) -> list[str]:
        """Get default next steps when configuration is unavailable"""
        config = self._get_default_config()
        templates = config.next_steps_templates
        return templates.get(intake_type, templates.get("general_intake", []))

    def _get_default_required_fields(self, intake_type: str) -> list[str]:
        """Get default required fields when configuration is unavailable"""
        config = self._get_default_config()
        return config.required_fields.get(intake_type, [])

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
            "voice_processing_available": True,
        }

    async def cleanup(self) -> None:
        """
        Enhanced cleanup method including voice processing resources
        """
        try:
            # Clean up voice processor sessions
            if hasattr(self, "voice_processor") and self.voice_processor:
                for voice_session_id in list(self.voice_processor.active_voice_sessions.keys()):
                    try:
                        await self.voice_processor.finalize_voice_intake_session(voice_session_id)
                    except Exception as e:
                        logger.warning(f"Error finalizing voice session {voice_session_id}: {e}")

            # Clean up transcription agent
            if hasattr(self, "transcription_agent") and self.transcription_agent:
                await self.transcription_agent.cleanup()

            # Clean up session manager
            if hasattr(self, "session_manager") and self.session_manager:
                await self.session_manager.cleanup()

            # Call parent cleanup
            await super().cleanup()

            log_healthcare_event(
                logger,
                logging.INFO,
                "Enhanced intake agent cleanup completed",
                context={
                    "agent": "intake",
                    "voice_processing_cleaned": True,
                    "transcription_agent_cleaned": True,
                    "session_manager_cleaned": True,
                },
                operation_type="agent_cleanup",
            )

        except Exception as e:
            log_healthcare_event(
                logger,
                logging.ERROR,
                f"Error during enhanced intake agent cleanup: {str(e)}",
                context={"error": str(e)},
                operation_type="cleanup_error",
            )

    # ==== WORKFLOW ORCHESTRATION METHODS ====

    async def start_intake_to_billing_workflow(
        self,
        session_id: str,
        user_id: str,
        patient_data: dict[str, Any],
        doctor_id: str | None = None,
    ) -> str:
        """
        Start the complete INTAKE_TO_BILLING workflow using orchestration

        This workflow coordinates intake → transcription → clinical_analysis → billing
        following the PHASE_3 orchestration patterns.

        Args:
            session_id: Enhanced session ID for cross-agent data sharing
            user_id: User initiating the workflow
            patient_data: Initial patient intake data
            doctor_id: Optional doctor ID for workflow context

        Returns:
            str: Workflow ID for tracking progress
        """

        workflow_input = {
            "intake_type": patient_data.get("intake_type", "new_patient_registration"),
            "patient_data": patient_data,
            "voice_enabled": patient_data.get("voice_enabled", False),
            "audio_data": patient_data.get("audio_data") if patient_data.get("voice_enabled") else None,
        }

        log_healthcare_event(
            self.logger,
            logging.INFO,
            "Starting INTAKE_TO_BILLING workflow",
            context={
                "session_id": session_id,
                "user_id": user_id,
                "doctor_id": doctor_id,
                "intake_type": workflow_input["intake_type"],
                "voice_enabled": workflow_input["voice_enabled"],
            },
            operation_type="workflow_start_requested",
        )

        # Start workflow with orchestrator
        workflow_id = await workflow_orchestrator.start_workflow(
            workflow_type=WorkflowType.INTAKE_TO_BILLING,
            session_id=session_id,
            user_id=user_id,
            input_data=workflow_input,
            doctor_id=doctor_id,
        )

        log_healthcare_event(
            self.logger,
            logging.INFO,
            f"INTAKE_TO_BILLING workflow started successfully: {workflow_id}",
            context={
                "workflow_id": workflow_id,
                "workflow_type": "intake_to_billing",
                "session_id": session_id,
            },
            operation_type="workflow_started",
        )

        return workflow_id

    async def start_voice_intake_workflow(
        self,
        session_id: str,
        user_id: str,
        patient_data: dict[str, Any],
        audio_data: Any,
        doctor_id: str | None = None,
    ) -> str:
        """
        Start specialized voice intake workflow with real-time processing

        This workflow handles voice_intake_session → transcription_analysis →
        form_completion → clinical_validation

        Args:
            session_id: Enhanced session ID for cross-agent data sharing
            user_id: User initiating the workflow
            patient_data: Initial patient data with voice context
            audio_data: Audio data for voice processing
            doctor_id: Optional doctor ID for workflow context

        Returns:
            str: Workflow ID for tracking progress
        """

        workflow_input = {
            "intake_type": patient_data.get("intake_type", "voice_intake"),
            "patient_data": patient_data,
            "audio_data": audio_data,
            "voice_enabled": True,
            "real_time": True,
        }

        log_healthcare_event(
            self.logger,
            logging.INFO,
            "Starting VOICE_INTAKE_WORKFLOW",
            context={
                "session_id": session_id,
                "user_id": user_id,
                "doctor_id": doctor_id,
                "intake_type": workflow_input["intake_type"],
                "real_time_processing": True,
            },
            operation_type="voice_workflow_start_requested",
        )

        # Start voice-specific workflow
        workflow_id = await workflow_orchestrator.start_workflow(
            workflow_type=WorkflowType.VOICE_INTAKE_WORKFLOW,
            session_id=session_id,
            user_id=user_id,
            input_data=workflow_input,
            doctor_id=doctor_id,
        )

        log_healthcare_event(
            self.logger,
            logging.INFO,
            f"VOICE_INTAKE_WORKFLOW started successfully: {workflow_id}",
            context={
                "workflow_id": workflow_id,
                "workflow_type": "voice_intake_workflow",
                "session_id": session_id,
            },
            operation_type="voice_workflow_started",
        )

        return workflow_id

    async def process_request(self, step_input: dict[str, Any]) -> dict[str, Any]:
        """
        Process workflow step request from orchestrator

        This method is called by the workflow orchestrator when this agent
        is responsible for a specific step in a multi-agent workflow.

        Args:
            step_input: Input data from workflow orchestrator including:
                - workflow_id: ID of the workflow
                - session_id: Enhanced session ID
                - user_id: User ID
                - step_config: Configuration for this step
                - workflow_input: Original workflow input
                - previous_results: Results from previous workflow steps

        Returns:
            dict: Step result for workflow orchestrator
        """

        workflow_id = step_input.get("workflow_id")
        session_id = step_input.get("session_id")
        step_config = step_input.get("step_config", {})
        workflow_input = step_input.get("workflow_input", {})
        previous_results = step_input.get("previous_results", {})

        log_healthcare_event(
            self.logger,
            logging.INFO,
            f"Processing workflow step request for workflow: {workflow_id}",
            context={
                "workflow_id": workflow_id,
                "session_id": session_id,
                "step_config": step_config,
                "voice_enabled": step_config.get("voice_enabled", False),
            },
            operation_type="workflow_step_processing",
        )

        try:
            # Handle voice-enabled processing
            if step_config.get("voice_enabled", False):
                return await self._process_workflow_voice_step(
                    workflow_id, session_id, step_config, workflow_input, previous_results,
                )

            # Handle standard intake processing
            return await self._process_workflow_intake_step(
                workflow_id, session_id, step_config, workflow_input, previous_results,
            )

        except Exception as e:
            error_message = f"Workflow step processing failed: {str(e)}"

            log_healthcare_event(
                self.logger,
                logging.ERROR,
                error_message,
                context={
                    "workflow_id": workflow_id,
                    "session_id": session_id,
                    "error": str(e),
                },
                operation_type="workflow_step_error",
            )

            return {
                "success": False,
                "error": error_message,
                "workflow_id": workflow_id,
                "session_id": session_id,
                "agent": "intake",
                "timestamp": datetime.now().isoformat(),
            }

    async def _process_workflow_voice_step(
        self,
        workflow_id: str,
        session_id: str,
        step_config: dict[str, Any],
        workflow_input: dict[str, Any],
        previous_results: dict[str, Any],
    ) -> dict[str, Any]:
        """Process voice-enabled workflow step"""

        patient_data = workflow_input.get("patient_data", {})
        audio_data = workflow_input.get("audio_data")

        if step_config.get("voice_to_form", False):
            # Form completion step - use transcription results to complete forms
            transcription_results = previous_results.get("transcription_analysis", {})

            # Create voice session for form completion
            voice_session_id = await self.voice_processor.start_voice_intake_session(
                patient_id=patient_data.get("patient_id", "temp"),
                intake_type=patient_data.get("intake_type", "voice_intake"),
            )

            # Use transcription results to populate form
            if transcription_results.get("transcription_text"):
                await self.voice_processor.process_voice_transcription(
                    voice_session_id, transcription_results["transcription_text"],
                )

                # Finalize voice session
                session_summary = await self.voice_processor.finalize_voice_intake_session(voice_session_id)

                return {
                    "success": True,
                    "voice_session_id": voice_session_id,
                    "form_data": session_summary["form_data"],
                    "completion_percentage": session_summary["completion_percentage"],
                    "medical_terms_extracted": session_summary["medical_terms_extracted"],
                    "workflow_id": workflow_id,
                    "session_id": session_id,
                    "agent": "intake",
                    "step_type": "voice_form_completion",
                    "timestamp": datetime.now().isoformat(),
                }

        else:
            # Voice intake session initiation
            voice_session_id = await self.voice_processor.start_voice_intake_session(
                patient_id=patient_data.get("patient_id", "temp"),
                intake_type=patient_data.get("intake_type", "voice_intake"),
            )

            if audio_data:
                # Process initial audio data if provided
                await self.voice_processor.process_voice_chunk(
                    voice_session_id, audio_data,
                )

            return {
                "success": True,
                "voice_session_id": voice_session_id,
                "voice_session_active": True,
                "workflow_id": workflow_id,
                "session_id": session_id,
                "agent": "intake",
                "step_type": "voice_session_init",
                "timestamp": datetime.now().isoformat(),
            }
        return None

    async def _process_workflow_intake_step(
        self,
        workflow_id: str,
        session_id: str,
        step_config: dict[str, Any],
        workflow_input: dict[str, Any],
        previous_results: dict[str, Any],
    ) -> dict[str, Any]:
        """Process standard intake workflow step"""

        patient_data = workflow_input.get("patient_data", {})
        workflow_input.get("intake_type", "new_patient_registration")

        # Process intake using existing methods
        result = await self.process_intake_request(patient_data, session_id)

        return {
            "success": True,
            "intake_result": result.__dict__,
            "workflow_id": workflow_id,
            "session_id": session_id,
            "agent": "intake",
            "step_type": "standard_intake",
            "timestamp": datetime.now().isoformat(),
        }
