"""
Voice Intake Processor - Separate module for voice processing functionality
Handles voice-to-form processing for healthcare intake workflows
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

from core.infrastructure.healthcare_logger import get_healthcare_logger, log_healthcare_event
from core.infrastructure.phi_monitor import sanitize_healthcare_data, scan_for_phi


@dataclass
class VoiceIntakeResult:
    """Result from voice intake processing"""
    
    voice_session_id: str
    transcription_text: str
    confidence_score: float
    medical_terms: List[str]
    intake_form_data: Dict[str, Any]
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
    
    def __init__(self):
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
            "allergies": ["allergies", "allergic to", "drug allergies", "food allergies"]
        }
        
        # Form completion tracking
        self.active_voice_sessions: Dict[str, Dict[str, Any]] = {}
    
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
                "phi_incidents": []
            }
            
            log_healthcare_event(
                self.logger,
                logging.INFO,
                f"Voice intake session started: {voice_session_id}",
                context={
                    "voice_session_id": voice_session_id,
                    "patient_id": patient_id,
                    "intake_type": intake_type
                },
                operation_type="voice_intake_session_start"
            )
            
            return voice_session_id
            
        except Exception as e:
            log_healthcare_event(
                self.logger,
                logging.ERROR,
                f"Failed to start voice intake session: {str(e)}",
                context={"patient_id": patient_id, "error": str(e)},
                operation_type="voice_intake_session_error"
            )
            raise
    
    async def process_voice_chunk(self, voice_session_id: str, transcription_text: str, confidence_score: float, medical_terms: List[str]) -> VoiceIntakeResult:
        """
        Process transcribed voice chunk and update intake form
        
        Args:
            voice_session_id: Active voice intake session ID
            transcription_text: Transcribed text from audio
            confidence_score: Transcription confidence score
            medical_terms: Extracted medical terms
            
        Returns:
            VoiceIntakeResult: Processing result with form updates
        """
        try:
            if voice_session_id not in self.active_voice_sessions:
                raise ValueError(f"Voice session not found: {voice_session_id}")
                
            session_data = self.active_voice_sessions[voice_session_id]
            
            # PHI detection and sanitization
            phi_result = scan_for_phi(transcription_text)
            phi_detected = phi_result.get("phi_detected", False)
            
            if phi_detected:
                transcription_text = self._sanitize_phi_in_transcript(transcription_text)
            
            # Update session buffer
            session_data["transcription_buffer"].append({
                "text": transcription_text,
                "confidence": confidence_score,
                "timestamp": datetime.now(),
                "medical_terms": medical_terms
            })
            
            # Extract form field data from transcription
            form_updates = await self._extract_form_data_from_speech(transcription_text, session_data)
            
            # Update form data
            session_data["form_data"].update(form_updates)
            session_data["medical_terms_collected"].extend(medical_terms)
            
            if phi_detected:
                session_data["phi_incidents"].append({
                    "timestamp": datetime.now(),
                    "text_sample": transcription_text[:50] + "..." if len(transcription_text) > 50 else transcription_text
                })
            
            # Calculate completion percentage
            completion_percentage = self._calculate_form_completion(session_data["form_data"], session_data["intake_type"])
            session_data["completion_percentage"] = completion_percentage
            
            log_healthcare_event(
                self.logger,
                logging.INFO,
                f"Voice chunk processed for session {voice_session_id}",
                context={
                    "voice_session_id": voice_session_id,
                    "transcription_length": len(transcription_text),
                    "confidence_score": confidence_score,
                    "form_updates_count": len(form_updates),
                    "completion_percentage": completion_percentage,
                    "phi_detected": phi_detected
                },
                operation_type="voice_chunk_processed"
            )
            
            return VoiceIntakeResult(
                voice_session_id=voice_session_id,
                transcription_text=transcription_text,
                confidence_score=confidence_score,
                medical_terms=list(set(session_data["medical_terms_collected"])),
                intake_form_data=session_data["form_data"].copy(),
                form_completion_percentage=completion_percentage,
                phi_detected=phi_detected,
                phi_sanitized=phi_detected,
                processing_timestamp=datetime.now(),
                status="processing" if completion_percentage < 80.0 else "completed"
            )
            
        except Exception as e:
            log_healthcare_event(
                self.logger,
                logging.ERROR,
                f"Voice chunk processing failed: {str(e)}",
                context={
                    "voice_session_id": voice_session_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                operation_type="voice_processing_error"
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
                status="failed"
            )
    
    def _sanitize_phi_in_transcript(self, transcript: str) -> str:
        """Apply PHI sanitization to real-time transcript"""
        
        # Simple PHI patterns for real-time sanitization
        phi_patterns = {
            r'\b\d{3}-\d{2}-\d{4}\b': '[SSN_REDACTED]',  # SSN
            r'\b\d{10,11}\b': '[PHONE_REDACTED]',  # Phone numbers
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b': '[EMAIL_REDACTED]',  # Email
        }
        
        sanitized = transcript
        for pattern, replacement in phi_patterns.items():
            sanitized = re.sub(pattern, replacement, sanitized)
            
        return sanitized
    
    async def _extract_form_data_from_speech(self, transcribed_text: str, session_data: Dict[str, Any]) -> Dict[str, Any]:
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
        
        # Extract names
        if any(pattern in text_lower for pattern in self.field_mappings["first_name"]):
            # Look for name patterns after the question words
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
    
    def _calculate_form_completion(self, form_data: Dict[str, Any], intake_type: str) -> float:
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
                "insurance_primary"
            ]
        elif intake_type == "appointment_scheduling":
            required_fields = ["patient_id", "appointment_type", "preferred_times"]
        else:
            required_fields = ["patient_id"]
        
        filled_fields = sum(1 for field in required_fields if form_data.get(field))
        return (filled_fields / len(required_fields)) * 100.0 if required_fields else 100.0
    
    async def finalize_voice_intake_session(self, voice_session_id: str) -> Dict[str, Any]:
        """
        Complete and finalize a voice intake session
        
        Args:
            voice_session_id: Voice session to finalize
            
        Returns:
            dict: Final session summary and extracted data
        """
        try:
            if voice_session_id not in self.active_voice_sessions:
                raise ValueError(f"Voice session not found: {voice_session_id}")
            
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
                "finalized_at": datetime.now()
            }
            
            # Clean up active session
            del self.active_voice_sessions[voice_session_id]
            
            log_healthcare_event(
                self.logger,
                logging.INFO,
                f"Voice intake session finalized: {voice_session_id}",
                context=session_summary,
                operation_type="voice_intake_session_finalized"
            )
            
            return session_summary
            
        except Exception as e:
            log_healthcare_event(
                self.logger,
                logging.ERROR,
                f"Failed to finalize voice intake session: {str(e)}",
                context={"voice_session_id": voice_session_id, "error": str(e)},
                operation_type="voice_session_finalization_error"
            )
            raise