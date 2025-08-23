"""
Healthcare Intake Agent - Refactored with External Configuration
Administrative support with voice processing capabilities using external config
"""

import logging
import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, List

from agents import BaseHealthcareAgent
from agents.transcription.transcription_agent import TranscriptionAgent
from core.infrastructure.healthcare_logger import (
    get_healthcare_logger,
    healthcare_agent_log,
    healthcare_log_method,
    log_healthcare_event,
)
from core.infrastructure.phi_monitor import phi_monitor, sanitize_healthcare_data, scan_for_phi
from core.enhanced_sessions import EnhancedSessionManager, PHIAwareConversationStorage
from core.orchestration import WorkflowType, workflow_orchestrator
from config.config_loader import get_healthcare_config

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


class VoiceIntakeProcessor:
    """
    Voice processing component using external configuration
    Processes real-time intake form completion with PHI protection
    """
    
    def __init__(self, transcription_agent: TranscriptionAgent, session_manager: EnhancedSessionManager):
        self.transcription_agent = transcription_agent
        self.session_manager = session_manager
        self.logger = get_healthcare_logger("voice_intake_processor")
        
        # Load configuration
        self.config = get_healthcare_config()
        self.voice_config = self.config.intake_agent.voice_processing
        
        # Load field mappings and medical keywords from configuration
        self.field_mappings = self.voice_config.field_mappings
        self.medical_keywords = self.voice_config.medical_keywords
        
        # Configuration-driven settings
        self.confidence_threshold = self.voice_config.confidence_threshold
        self.max_session_duration = self.voice_config.max_session_duration_minutes
        
        # Form completion tracking
        self.active_voice_sessions: Dict[str, Dict[str, Any]] = {}
        
        log_healthcare_event(
            self.logger,
            logging.INFO,
            "Voice intake processor initialized with external configuration",
            context={
                "confidence_threshold": self.confidence_threshold,
                "max_session_duration": self.max_session_duration,
                "field_mappings_count": len(self.field_mappings),
                "medical_keywords_categories": len(self.medical_keywords)
            },
            operation_type="voice_processor_initialization"
        )
    
    @healthcare_log_method(operation_type="voice_intake_start", phi_risk_level="high")
    async def start_voice_intake_session(self, patient_id: str, intake_type: str = "new_patient_registration") -> str:
        """Start voice intake session with configuration-based setup"""
        
        voice_session_id = f"voice_{patient_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Get required fields from configuration
        required_fields = self.config.intake_agent.required_fields.get(intake_type, [])
        
        # Initialize session data
        session_data = {
            "patient_id": patient_id,
            "intake_type": intake_type,
            "required_fields": required_fields,
            "start_time": datetime.now(),
            "form_data": {},
            "transcription_buffer": [],
            "medical_terms_collected": [],
            "phi_incidents": [],
            "completion_percentage": 0.0,
            "session_active": True
        }
        
        self.active_voice_sessions[voice_session_id] = session_data
        
        # Store session in enhanced session manager
        await self.session_manager.store_message(
            session_id=voice_session_id,
            role="system",
            content="Voice intake session started",
            metadata={
                "session_type": "voice_intake",
                "patient_id": patient_id,
                "intake_type": intake_type,
                "required_fields": required_fields
            }
        )
        
        log_healthcare_event(
            self.logger,
            logging.INFO,
            f"Voice intake session started: {voice_session_id}",
            context={
                "patient_id": patient_id,
                "intake_type": intake_type,
                "required_fields_count": len(required_fields),
                "voice_session_id": voice_session_id
            },
            operation_type="voice_intake_session_started"
        )
        
        return voice_session_id
    
    async def process_voice_transcription(self, voice_session_id: str, transcription_text: str) -> Dict[str, Any]:
        """Process transcribed text and extract form data"""
        
        if voice_session_id not in self.active_voice_sessions:
            raise ValueError(f"Voice session not found: {voice_session_id}")
        
        session_data = self.active_voice_sessions[voice_session_id]
        
        # PHI detection and sanitization
        phi_scan = scan_for_phi(transcription_text)
        sanitized_text = sanitize_healthcare_data({"text": transcription_text})["text"]
        
        # Store transcription in buffer
        session_data["transcription_buffer"].append({
            "text": sanitized_text,
            "timestamp": datetime.now(),
            "phi_detected": len(phi_scan.phi_entities) > 0
        })
        
        # Extract form fields using configuration-based mappings
        form_updates = self._extract_form_fields(sanitized_text, transcription_text)
        
        # Extract medical terms using configuration-based keywords
        medical_terms = self._extract_medical_terms(sanitized_text)
        
        # Update session data
        session_data["form_data"].update(form_updates)
        session_data["medical_terms_collected"].extend(medical_terms)
        session_data["completion_percentage"] = self._calculate_completion_percentage(
            session_data["form_data"], 
            session_data["intake_type"]
        )
        
        if phi_scan.phi_entities:
            session_data["phi_incidents"].append({
                "timestamp": datetime.now(),
                "phi_types": [entity["type"] for entity in phi_scan.phi_entities],
                "sanitized": True
            })
        
        return {
            "success": True,
            "fields_updated": list(form_updates.keys()),
            "medical_terms_found": medical_terms,
            "completion_percentage": session_data["completion_percentage"],
            "phi_detected": len(phi_scan.phi_entities) > 0,
            "session_id": voice_session_id
        }
    
    def _extract_form_fields(self, sanitized_text: str, original_text: str) -> Dict[str, str]:
        """Extract form fields using configuration-based field mappings"""
        
        form_updates = {}
        text_lower = sanitized_text.lower()
        
        # Use configuration-based field mappings
        for field_name, patterns in self.field_mappings.items():
            if any(pattern in text_lower for pattern in patterns):
                
                if field_name in ["first_name", "last_name"]:
                    # Extract names
                    import re
                    name_pattern = r"(?:name is|i am|i'm|call me)\s+([a-zA-Z]+)"
                    match = re.search(name_pattern, text_lower)
                    if match:
                        form_updates[field_name] = match.group(1).title()
                
                elif field_name == "contact_phone":
                    # Extract phone numbers
                    import re
                    phone_pattern = r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"
                    match = re.search(phone_pattern, original_text)
                    if match:
                        form_updates[field_name] = match.group(0)
                
                elif field_name == "date_of_birth":
                    # Extract dates
                    import re
                    date_patterns = [
                        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b",
                        r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b"
                    ]
                    for pattern in date_patterns:
                        match = re.search(pattern, original_text)
                        if match:
                            form_updates[field_name] = match.group(0)
                            break
                
                elif field_name in ["chief_complaint", "current_medications", "allergies"]:
                    # Extract longer text fields
                    for keyword in self.medical_keywords.get(field_name.replace("current_", ""), []):
                        if keyword in text_lower:
                            # Extract context around the keyword
                            start = max(0, text_lower.find(keyword) - 20)
                            end = min(len(sanitized_text), text_lower.find(keyword) + 80)
                            context = sanitized_text[start:end].strip()
                            form_updates[field_name] = context
                            break
        
        return form_updates
    
    def _extract_medical_terms(self, text: str) -> List[str]:
        """Extract medical terms using configuration-based keywords"""
        
        found_terms = []
        text_lower = text.lower()
        
        # Use configuration-based medical keywords
        for category, keywords in self.medical_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    found_terms.append(keyword)
        
        return list(set(found_terms))  # Remove duplicates
    
    def _calculate_completion_percentage(self, form_data: Dict[str, Any], intake_type: str) -> float:
        """Calculate form completion percentage using configuration-based required fields"""
        
        required_fields = self.config.intake_agent.required_fields.get(intake_type, [])
        if not required_fields:
            return 100.0
        
        filled_fields = sum(1 for field in required_fields if form_data.get(field))
        return (filled_fields / len(required_fields)) * 100.0


class HealthcareIntakeAgent(BaseHealthcareAgent):
    """
    Refactored Healthcare Intake Agent using external configuration
    
    CRITICAL: Provides administrative support only, never medical advice.
    All configuration loaded from external YAML files.
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
        self.config_override = config_override or {}
        
        # Load configuration
        self.config = get_healthcare_config()
        self.intake_config = self.config.intake_agent
        
        # Load disclaimers from configuration
        self.disclaimers = self.intake_config.disclaimers
        
        # Initialize agents
        self.transcription_agent = TranscriptionAgent(mcp_client=mcp_client, llm_client=llm_client)
        self.session_manager = EnhancedSessionManager()
        
        # Initialize voice processor with configuration
        self.voice_processor = VoiceIntakeProcessor(
            transcription_agent=self.transcription_agent,
            session_manager=self.session_manager
        )

        log_healthcare_event(
            logger,
            logging.INFO,
            "Healthcare Intake Agent initialized with external configuration",
            context={
                "agent": "intake",
                "configuration_loaded": True,
                "disclaimers_count": len(self.disclaimers),
                "voice_processing_enabled": self.intake_config.voice_processing.enabled,
                "document_requirements_loaded": len(self.intake_config.document_requirements.base_documents) > 0
            },
            operation_type="agent_initialization",
        )

    async def initialize(self) -> None:
        """Initialize intake agent with configuration validation"""
        try:
            await self.initialize_agent()
            await self.transcription_agent.initialize()
            await self.session_manager.initialize()

            log_healthcare_event(
                logger,
                logging.INFO,
                "Intake Agent fully initialized with configuration-based setup",
                context={
                    "agent": "intake",
                    "database_validated": True,
                    "configuration_validated": True,
                    "voice_processing_ready": self.intake_config.voice_processing.enabled
                },
                operation_type="agent_initialization_complete",
            )
        except Exception as e:
            log_healthcare_event(
                logger,
                logging.ERROR,
                f"Failed to initialize intake agent: {str(e)}",
                context={"error": str(e)},
                operation_type="initialization_error",
            )
            raise

    def _get_required_documents(self, intake_type: str, patient_type: str = "existing") -> List[str]:
        """Get required documents from configuration based on intake and patient type"""
        
        doc_req = self.intake_config.document_requirements
        
        # Handle specific intake types
        if intake_type == "insurance_verification":
            return doc_req.insurance_verification
        elif intake_type == "appointment_scheduling":
            return doc_req.appointment_scheduling
        elif intake_type == "general_intake":
            return doc_req.general_intake
        
        # Build comprehensive document list
        documents = doc_req.base_documents.copy()
        
        if patient_type == "new":
            documents.extend(doc_req.new_patient_additional)
        
        if intake_type == "specialist":
            documents.extend(doc_req.specialist_additional)
        
        return documents
    
    def _get_next_steps(self, intake_type: str) -> List[str]:
        """Get next steps from configuration based on intake type"""
        templates = self.intake_config.next_steps_templates
        return templates.get(intake_type, templates.get("general_intake", []))
    
    def _get_required_fields(self, intake_type: str) -> List[str]:
        """Get required fields from configuration based on intake type"""
        return self.intake_config.required_fields.get(intake_type, [])

    # ==== MAIN PROCESSING METHODS ====
    
    @healthcare_log_method(operation_type="intake_request", phi_risk_level="high")
    async def process_intake_request(self, patient_data: dict[str, Any], session_id: str) -> IntakeResult:
        """Process intake request using configuration-based logic"""
        
        intake_type = patient_data.get("intake_type", "general_intake")
        
        try:
            # Route to appropriate handler based on intake type
            if intake_type == "new_patient_registration":
                return await self._process_new_patient_registration(patient_data, session_id)
            elif intake_type == "appointment_scheduling":
                return await self._process_appointment_scheduling(patient_data, session_id)
            elif intake_type == "insurance_verification":
                return await self._process_insurance_verification(patient_data, session_id)
            elif intake_type == "document_checklist":
                return await self._process_document_checklist(patient_data, session_id)
            else:
                return await self._process_general_intake(patient_data, session_id)
                
        except Exception as e:
            log_healthcare_event(
                logger,
                logging.ERROR,
                f"Intake processing failed: {str(e)}",
                context={"intake_type": intake_type, "session_id": session_id, "error": str(e)},
                operation_type="intake_processing_error"
            )
            raise

    async def _process_new_patient_registration(self, patient_data: dict[str, Any], session_id: str) -> IntakeResult:
        """Process new patient registration using configuration"""
        
        intake_id = self._generate_intake_id("registration")
        
        # Get configuration-based requirements
        required_documents = self._get_required_documents("new_patient_registration", "new")
        next_steps = self._get_next_steps("new_patient_registration")
        required_fields = self._get_required_fields("new_patient_registration")
        
        # Validate required fields
        validation_errors = []
        for field in required_fields:
            if not patient_data.get(field):
                validation_errors.append(f"Required field missing: {field}")
        
        # Create patient record if validation passes
        patient_id = None
        if not validation_errors:
            patient_id = await self._create_patient_record(patient_data)
        
        administrative_notes = [
            "New patient registration processed using configuration-based requirements",
            f"Validated {len(required_fields)} required fields",
            f"Generated {len(required_documents)} document requirements"
        ]
        
        return IntakeResult(
            intake_id=intake_id,
            status="registration_complete" if not validation_errors else "validation_required",
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

    # ==== WORKFLOW ORCHESTRATION METHODS ====
    
    async def start_intake_to_billing_workflow(
        self, 
        session_id: str, 
        user_id: str,
        patient_data: dict[str, Any],
        doctor_id: Optional[str] = None
    ) -> str:
        """Start INTAKE_TO_BILLING workflow using configuration-based setup"""
        
        workflow_input = {
            "intake_type": patient_data.get("intake_type", "new_patient_registration"),
            "patient_data": patient_data,
            "voice_enabled": patient_data.get("voice_enabled", False),
            "audio_data": patient_data.get("audio_data") if patient_data.get("voice_enabled") else None
        }
        
        workflow_id = await workflow_orchestrator.start_workflow(
            workflow_type=WorkflowType.INTAKE_TO_BILLING,
            session_id=session_id,
            user_id=user_id,
            input_data=workflow_input,
            doctor_id=doctor_id
        )
        
        log_healthcare_event(
            self.logger,
            logging.INFO,
            f"INTAKE_TO_BILLING workflow started: {workflow_id}",
            context={
                "workflow_id": workflow_id,
                "session_id": session_id,
                "intake_type": workflow_input["intake_type"],
                "voice_enabled": workflow_input["voice_enabled"]
            },
            operation_type="workflow_started"
        )
        
        return workflow_id

    async def process_request(self, step_input: dict[str, Any]) -> dict[str, Any]:
        """Process workflow step request using configuration-based logic"""
        
        workflow_id = step_input.get("workflow_id")
        session_id = step_input.get("session_id")
        step_config = step_input.get("step_config", {})
        workflow_input = step_input.get("workflow_input", {})
        
        try:
            if step_config.get("voice_enabled", False):
                return await self._process_workflow_voice_step(
                    workflow_id, session_id, step_config, workflow_input, step_input.get("previous_results", {})
                )
            else:
                return await self._process_workflow_intake_step(
                    workflow_id, session_id, step_config, workflow_input, step_input.get("previous_results", {})
                )
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Workflow step processing failed: {str(e)}",
                "workflow_id": workflow_id,
                "session_id": session_id,
                "agent": "intake",
                "timestamp": datetime.now().isoformat()
            }

    # ==== UTILITY METHODS ====
    
    def _generate_intake_id(self, intake_type: str) -> str:
        """Generate intake ID with type prefix"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        return f"INTAKE_{intake_type.upper()}_{timestamp}"

    async def _create_patient_record(self, patient_data: dict[str, Any]) -> str:
        """Create patient record in system"""
        patient_id = f"PAT_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        logger.info(f"Patient record created: {patient_id}")
        return patient_id

    async def cleanup(self) -> None:
        """Cleanup resources with configuration validation"""
        try:
            if hasattr(self, 'voice_processor') and self.voice_processor:
                # Clean up active voice sessions
                for session_id in list(self.voice_processor.active_voice_sessions.keys()):
                    del self.voice_processor.active_voice_sessions[session_id]
            
            if hasattr(self, 'transcription_agent') and self.transcription_agent:
                await self.transcription_agent.cleanup()
            
            if hasattr(self, 'session_manager') and self.session_manager:
                await self.session_manager.cleanup()
            
            log_healthcare_event(
                logger,
                logging.INFO,
                "Configuration-based intake agent cleanup completed",
                context={"agent": "intake", "cleanup_successful": True},
                operation_type="agent_cleanup"
            )
            
        except Exception as e:
            log_healthcare_event(
                logger,
                logging.ERROR,
                f"Error during intake agent cleanup: {str(e)}",
                context={"error": str(e)},
                operation_type="cleanup_error"
            )