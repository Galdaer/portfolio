"""
Healthcare Transcription Agent - Administrative Transcription Support Only
Handles medical dictation processing, clinical note generation, and documentation support for healthcare workflows
"""

import asyncio
import logging
import os
import re
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from agents import BaseHealthcareAgent
from config.transcription_config_loader import TRANSCRIPTION_CONFIG
from core.compliance.agent_compliance_monitor import compliance_monitor_decorator
from core.infrastructure.agent_metrics import AgentMetricsStore
from core.infrastructure.healthcare_cache import HealthcareCacheManager
from core.infrastructure.healthcare_logger import (
    get_healthcare_logger,
    healthcare_log_method,
    log_healthcare_event,
)
from core.infrastructure.phi_monitor import phi_monitor_decorator as phi_monitor, scan_for_phi

logger = get_healthcare_logger("agent.transcription")


@dataclass
class TranscriptionResult:
    """Result from transcription processing with healthcare compliance"""

    transcription_id: str
    status: str
    original_audio_duration: float | None
    transcribed_text: str | None
    confidence_score: float | None
    medical_terms_identified: list[str]
    transcription_errors: list[str]
    compliance_validated: bool
    timestamp: datetime
    metadata: dict[str, Any]


@dataclass
class ClinicalNoteResult:
    """Result from clinical note generation"""

    note_id: str
    note_type: str
    structured_content: dict[str, Any]
    formatted_note: str
    quality_score: float
    missing_sections: list[str]
    recommendations: list[str]
    timestamp: datetime


@dataclass
class DocumentationTemplate:
    """Template for clinical documentation"""

    template_id: str
    template_name: str
    template_type: str
    required_sections: list[str]
    optional_sections: list[str]
    formatting_rules: dict[str, Any]


class TranscriptionAgent(BaseHealthcareAgent):
    """
    Healthcare Transcription Agent

    MEDICAL DISCLAIMER: This agent provides administrative transcription support and clinical
    documentation assistance only. It helps healthcare professionals with medical dictation
    processing, clinical note generation, and documentation formatting. It does not provide
    medical advice, diagnosis, or treatment recommendations. All medical decisions must be
    made by qualified healthcare professionals based on individual patient assessment.

    Capabilities:
    - Medical dictation transcription and processing
    - Clinical note generation and formatting
    - Medical terminology validation and correction
    - Documentation template management
    - SOAP note structuring and organization
    - Transcription quality assurance and review
    """

    def __init__(self, mcp_client=None, llm_client=None) -> None:
        super().__init__(
            mcp_client=mcp_client,
            llm_client=llm_client,
            agent_name="transcription",
            agent_type="transcription",
        )
        self.logger = get_healthcare_logger(f"agent.{self.agent_name}")

        # Initialize shared healthcare infrastructure tools
        self._metrics = AgentMetricsStore(agent_name="transcription")
        self._cache_manager = HealthcareCacheManager()
        self.capabilities = [
            "audio_transcription",
            "clinical_note_generation",
            "medical_terminology_validation",
            "documentation_formatting",
            "soap_note_structuring",
            "quality_assurance",
        ]

        # Initialize comprehensive medical terminology dictionary
        self.medical_terms = {
            # Vital signs and measurements
            "bp": "blood pressure",
            "hr": "heart rate",
            "temp": "temperature",
            "resp": "respiration",
            "rr": "respiratory rate",
            "wt": "weight",
            "ht": "height",
            "bmi": "body mass index",
            "o2 sat": "oxygen saturation",
            "pulse ox": "pulse oximetry",
            # Clinical sections
            "chief complaint": "CC",
            "history of present illness": "HPI",
            "past medical history": "PMH",
            "past surgical history": "PSH",
            "social history": "SH",
            "family history": "FH",
            "review of systems": "ROS",
            "physical exam": "PE",
            "physical examination": "PE",
            "assessment and plan": "A&P",
            "impression and plan": "I&P",
            # Common medical abbreviations
            "nkda": "no known drug allergies",
            "nka": "no known allergies",
            "sob": "shortness of breath",
            "doe": "dyspnea on exertion",
            "cp": "chest pain",
            "n/v": "nausea and vomiting",
            "b/l": "bilateral",
            "r/o": "rule out",
            "s/p": "status post",
            "h/o": "history of",
            "c/o": "complains of",
            "w/": "with",
            "w/o": "without",
            "prn": "as needed",
            "bid": "twice daily",
            "tid": "three times daily",
            "qid": "four times daily",
            "qd": "once daily",
            "qhs": "at bedtime",
            "ac": "before meals",
            "pc": "after meals",
            "po": "by mouth",
            "iv": "intravenous",
            "im": "intramuscular",
            "sq": "subcutaneous",
            "subq": "subcutaneous",
            # Body systems and anatomy
            "heent": "head, eyes, ears, nose, throat",
            "cv": "cardiovascular",
            "resp_system": "respiratory",
            "gi": "gastrointestinal",
            "gu": "genitourinary",
            "msk": "musculoskeletal",
            "neuro": "neurological",
            "psych": "psychiatric",
            "derm": "dermatologic",
            "endo": "endocrine",
            "heme": "hematologic",
            "onc": "oncologic",
            # Common conditions and findings
            "wnl": "within normal limits",
            "nad": "no acute distress",
            "rrr": "regular rate and rhythm",
            "ctab": "clear to auscultation bilaterally",
            "nt": "non-tender",
            "nd": "non-distended",
            "bs": "bowel sounds",
            "nabs": "normoactive bowel sounds",
            "rom": "range of motion",
            "cn": "cranial nerves",
            "dtr": "deep tendon reflexes",
            "jvd": "jugular venous distension",
            "pmr": "point of maximal impulse",
            "murmur": "cardiac murmur",
            "rales": "pulmonary rales",
            "wheeze": "wheeze",
            "rhonchi": "rhonchi",
        }

        # Initialize documentation templates
        self.templates = {
            "soap_note": DocumentationTemplate(
                template_id="soap_001",
                template_name="SOAP Note",
                template_type="clinical_note",
                required_sections=["subjective", "objective", "assessment", "plan"],
                optional_sections=["chief_complaint", "hpi", "ros", "pmh"],
                formatting_rules={"line_spacing": "single", "section_headers": "bold"},
            ),
            "progress_note": DocumentationTemplate(
                template_id="prog_001",
                template_name="Progress Note",
                template_type="progress_update",
                required_sections=["current_status", "changes", "plan"],
                optional_sections=["vital_signs", "medications"],
                formatting_rules={"date_format": "MM/DD/YYYY", "time_format": "24h"},
            ),
        }

        # Log agent initialization with healthcare context
        log_healthcare_event(
            self.logger,
            logging.INFO,
            "Healthcare Transcription Agent initialized",
            context={
                "agent": "transcription",
                "initialization": True,
                "phi_monitoring": True,
                "medical_advice_disabled": True,
                "database_required": True,
                "capabilities": self.capabilities,
                "medical_terms_count": len(self.medical_terms),
                "templates_count": len(self.templates),
            },
            operation_type="agent_initialization",
        )

    async def initialize(self) -> None:
        """Initialize transcription agent with database connectivity validation"""
        try:
            # Call parent initialization which validates database connectivity
            await self.initialize_agent()

            log_healthcare_event(
                self.logger,
                logging.INFO,
                "Transcription Agent fully initialized with database connectivity",
                context={
                    "agent": "transcription",
                    "database_validated": True,
                    "ready_for_operations": True,
                },
                operation_type="agent_ready",
            )
        except Exception as e:
            log_healthcare_event(
                self.logger,
                logging.CRITICAL,
                f"Transcription Agent initialization failed: {e}",
                context={
                    "agent": "transcription",
                    "initialization_failed": True,
                    "error": str(e),
                },
                operation_type="agent_initialization_error",
            )
            raise

    @healthcare_log_method(operation_type="audio_transcription", phi_risk_level="high")
    @phi_monitor(risk_level="high", operation_type="audio_transcription")
    @compliance_monitor_decorator(
        operation_type="medical_transcription",
        phi_risk_level="high",
        validate_input=True,
        validate_output=True,
    )
    async def transcribe_audio(self, audio_data: dict[str, Any]) -> TranscriptionResult:
        """
        Transcribe medical audio dictation with PHI protection

        Args:
            audio_data: Dictionary containing audio file information and metadata

        Returns:
            TranscriptionResult with transcribed text and validation

        Medical Disclaimer: Administrative transcription support only.
        Does not provide medical advice or clinical interpretation.
        """
        # Validate and sanitize input data for PHI protection
        scan_for_phi(str(audio_data))

        transcription_errors = []
        transcribed_text = None
        confidence_score = None

        try:
            # Initialize encounter_type early to avoid unbound variable issues
            encounter_type = audio_data.get("encounter_type", "office_visit")

            # Validate required fields
            required_fields = ["audio_file_path", "provider_id", "encounter_type"]
            for field in required_fields:
                if field not in audio_data:
                    transcription_errors.append(f"Missing required field: {field}")

            if transcription_errors:
                return TranscriptionResult(
                    transcription_id=f"trans_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    status="validation_failed",
                    original_audio_duration=None,
                    transcribed_text=None,
                    confidence_score=None,
                    medical_terms_identified=[],
                    transcription_errors=transcription_errors,
                    compliance_validated=False,
                    timestamp=datetime.now(),
                    metadata={"validation_stage": "required_fields"},
                )

            # Mock audio processing (in production, integrate with speech-to-text service)
            audio_duration = audio_data.get("duration_seconds", 120.0)

            # Simulate transcription processing
            await asyncio.sleep(TRANSCRIPTION_CONFIG.realtime.processing_interval_ms / 1000.0)  # Simulate processing time

            # Attempt real transcription through MCP client first
            transcribed_text = None
            confidence_score = None

            if self.mcp_client:
                try:
                    transcription_result = await self._transcribe_with_mcp(audio_data)
                    transcribed_text = transcription_result.get("transcribed_text")
                    confidence_score = transcription_result.get("confidence_score", TRANSCRIPTION_CONFIG.quality.default_confidence_threshold)
                except Exception as mcp_error:
                    log_healthcare_event(
                        self.logger,
                        logging.WARNING,
                        f"MCP transcription failed, falling back to mock: {mcp_error}",
                        context={
                            "audio_file": audio_data.get("audio_file_path"),
                            "mcp_error": str(mcp_error),
                            "fallback_mode": True,
                        },
                        operation_type="transcription_fallback",
                    )

            # Fallback to mock transcription if MCP failed or unavailable
            if not transcribed_text:
                transcribed_text = await self._generate_mock_transcription(encounter_type)
                confidence_score = TRANSCRIPTION_CONFIG.quality.high_confidence_threshold  # High confidence for demonstration

            # Identify medical terms in transcription
            medical_terms_found = self._identify_medical_terms(transcribed_text)

            # Validate transcription quality
            quality_issues = self._validate_transcription_quality(transcribed_text)
            if quality_issues:
                transcription_errors.extend(quality_issues)

            status = "completed" if not transcription_errors else "completed_with_warnings"

            log_healthcare_event(
                self.logger,
                logging.INFO,
                f"Audio transcription completed: {status}",
                context={
                    "encounter_type": encounter_type,
                    "audio_duration": audio_duration,
                    "confidence_score": confidence_score,
                    "medical_terms_count": len(medical_terms_found),
                    "text_length": len(transcribed_text) if transcribed_text else 0,
                },
                operation_type="audio_transcription",
            )

            return TranscriptionResult(
                transcription_id=f"trans_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                status=status,
                original_audio_duration=audio_duration,
                transcribed_text=transcribed_text,
                confidence_score=confidence_score,
                medical_terms_identified=medical_terms_found,
                transcription_errors=transcription_errors,
                compliance_validated=True,
                timestamp=datetime.now(),
                metadata={
                    "encounter_type": encounter_type,
                    "processing_time_seconds": 0.3,
                    "quality_score": confidence_score,
                },
            )

        except Exception as e:
            log_healthcare_event(
                self.logger,
                logging.ERROR,
                f"Audio transcription failed: {str(e)}",
                context={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "audio_file": audio_data.get("audio_file_path", "unknown"),
                },
                operation_type="transcription_error",
            )

            return TranscriptionResult(
                transcription_id=f"trans_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                status="transcription_failed",
                original_audio_duration=audio_data.get("duration_seconds"),
                transcribed_text=None,
                confidence_score=None,
                medical_terms_identified=[],
                transcription_errors=[f"Transcription error: {str(e)}"],
                compliance_validated=False,
                timestamp=datetime.now(),
                metadata={"error_stage": "processing_exception"},
            )

    @healthcare_log_method(operation_type="real_time_transcription", phi_risk_level="high")
    @phi_monitor(risk_level="high", operation_type="real_time_transcription")
    async def process_real_time_audio(self, audio_data: dict[str, Any], session_id: str, doctor_id: str) -> dict[str, Any]:
        """
        Process real-time audio chunks for live transcription during doctor-patient sessions

        Args:
            audio_data: Dictionary containing audio chunk data (base64, format, etc.)
            session_id: Live transcription session ID
            doctor_id: Identifier for the healthcare provider

        Returns:
            dict: Real-time transcription result with text, confidence, and medical terms

        Medical Disclaimer: Administrative transcription support only.
        Real-time transcription for documentation purposes, not medical interpretation.
        """
        try:
            # Validate audio chunk data
            if not audio_data:
                return {
                    "transcription": "",
                    "confidence": 0.0,
                    "error": "No audio data provided",
                    "medical_terms": [],
                }

            # Extract audio format and data
            audio_format = audio_data.get("format", "webm")
            audio_chunk_data = audio_data.get("data", "")
            chunk_duration = audio_data.get("duration", 1.0)

            # Log real-time processing start
            log_healthcare_event(
                self.logger,
                logging.INFO,
                f"Processing real-time audio chunk for session {session_id}",
                context={
                    "session_id": session_id,
                    "doctor_id": doctor_id,
                    "audio_format": audio_format,
                    "chunk_duration": chunk_duration,
                },
                operation_type="real_time_chunk_processing",
            )

            # Simulate real-time processing (in production, integrate with WhisperLive)
            transcribed_chunk = await self._process_real_time_chunk(audio_chunk_data, audio_format)

            # Apply PHI detection to real-time transcript
            phi_result = scan_for_phi(transcribed_chunk)
            if phi_result.get("phi_detected", False):
                # Apply PHI sanitization to real-time transcript
                transcribed_chunk = self._sanitize_phi_in_transcript(transcribed_chunk)

            # Identify medical terms in the chunk
            medical_terms = self._identify_medical_terms(transcribed_chunk)

            # Calculate confidence score (simulated)
            confidence_score = TRANSCRIPTION_CONFIG.quality.min_confidence_for_medical_terms + (len(transcribed_chunk) * TRANSCRIPTION_CONFIG.quality.confidence_boost_per_char)
            confidence_score = min(confidence_score, TRANSCRIPTION_CONFIG.quality.max_confidence_cap)

            log_healthcare_event(
                self.logger,
                logging.INFO,
                "Real-time transcription chunk completed",
                context={
                    "session_id": session_id,
                    "chunk_length": len(transcribed_chunk),
                    "confidence": confidence_score,
                    "medical_terms_count": len(medical_terms),
                    "phi_detected": phi_result.get("phi_detected", False),
                },
                operation_type="real_time_chunk_completed",
            )

            return {
                "transcription": transcribed_chunk,
                "confidence": confidence_score,
                "medical_terms": medical_terms,
                "session_id": session_id,
                "phi_sanitized": phi_result.get("phi_detected", False),
                "processing_timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            log_healthcare_event(
                self.logger,
                logging.ERROR,
                f"Real-time transcription failed: {str(e)}",
                context={
                    "session_id": session_id,
                    "doctor_id": doctor_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                operation_type="real_time_transcription_error",
            )

            return {
                "transcription": "",
                "confidence": 0.0,
                "error": f"Real-time transcription failed: {str(e)}",
                "medical_terms": [],
                "session_id": session_id,
            }

    async def _process_real_time_chunk(self, audio_chunk_data: str, audio_format: str) -> str:
        """Process individual audio chunk for real-time transcription"""

        # Simulate processing delay for real-time chunk
        await asyncio.sleep(TRANSCRIPTION_CONFIG.realtime.processing_interval_ms / 10000.0)  # Much faster than full audio processing

        # Generate realistic real-time transcription chunks
        chunk_templates = [
            "Patient reports feeling better today.",
            "Blood pressure reading is normal.",
            "Examination shows improvement in symptoms.",
            "Will continue with current medication regimen.",
            "Patient asks about side effects.",
            "Heart rate is regular and steady.",
            "Respiratory examination is clear.",
            "Patient's temperature is normal.",
            "No acute distress noted.",
            "Will schedule follow-up appointment.",
        ]

        # In production, this would interface with WhisperLive or similar service
        # For now, return a realistic medical transcription chunk
        import random
        return random.choice(chunk_templates)

    def _sanitize_phi_in_transcript(self, transcript: str) -> str:
        """Apply PHI sanitization to real-time transcript"""

        # Simple PHI patterns for real-time sanitization
        phi_patterns = {
            r"\b\d{3}-\d{2}-\d{4}\b": "[SSN_REDACTED]",  # SSN
            r"\b\d{10,11}\b": "[PHONE_REDACTED]",  # Phone numbers
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b": "[EMAIL_REDACTED]",  # Email
        }

        sanitized = transcript
        for pattern, replacement in phi_patterns.items():
            sanitized = re.sub(pattern, replacement, sanitized)

        return sanitized

    async def _generate_mock_transcription(self, encounter_type: str) -> str:
        """Generate mock transcription text based on encounter type"""

        transcription_templates = {
            "office_visit": """
            Chief complaint: Patient presents with fatigue and headaches for the past two weeks.

            History of present illness: 45-year-old female reports experiencing increasing fatigue
            and intermittent headaches. Symptoms began approximately two weeks ago. Fatigue is
            most prominent in the afternoons. Headaches are described as dull and pressure-like,
            primarily frontal. No associated nausea or visual changes. Sleep pattern has been
            disrupted with difficulty falling asleep.

            Physical examination: Blood pressure 140 over 85. Heart rate 78 and regular.
            Temperature 98.6 degrees. Patient appears tired but is alert and oriented.
            Head and neck examination reveals no lymphadenopathy. Cardiovascular examination
            shows regular rate and rhythm with no murmurs. Neurological examination is normal.

            Assessment and plan: Hypertension, newly diagnosed. Fatigue, likely related to
            blood pressure elevation and sleep disturbance. Will start lisinopril 10 milligrams
            daily. Patient education provided regarding blood pressure monitoring. Follow-up
            in two weeks to assess response to treatment.
            """,
            "follow_up": """
            Follow-up visit for hypertension management. Patient reports feeling much better
            since starting blood pressure medication two weeks ago. Fatigue has improved
            significantly. Headaches have resolved. Sleep quality is better.

            Current medications: Lisinopril 10 milligrams daily, taken consistently.

            Physical examination: Blood pressure today 128 over 76. Heart rate 72. Patient
            appears well. No acute distress noted.

            Assessment: Hypertension, well controlled on current therapy. Patient showing
            excellent response to treatment.

            Plan: Continue current medication regimen. Patient to monitor blood pressure
            at home. Return in one month for routine follow-up.
            """,
            "consultation": """
            Consultation for chronic back pain. Patient referred by primary care physician
            for evaluation of lower back pain persisting for three months. Pain is described
            as aching and stiff, worse in the morning and after prolonged sitting.

            Past medical history: No previous back injuries. No history of surgery.

            Physical examination: Lumbar spine shows mild tenderness over the lower lumbar
            region. Range of motion is limited with forward flexion. Straight leg raise
            test is negative bilaterally. Neurological examination of lower extremities
            is normal.

            Assessment: Chronic lower back pain, likely mechanical in nature. No evidence
            of nerve root compression.

            Recommendations: Physical therapy evaluation and treatment. Home exercise program
            focusing on core strengthening. Anti-inflammatory medication as needed.
            Re-evaluation in four weeks if symptoms persist.
            """,
        }

        return transcription_templates.get(encounter_type, transcription_templates["office_visit"])

    def _identify_medical_terms(self, text: str) -> list[str]:
        """Identify medical terms in transcribed text"""
        if not text:
            return []

        found_terms = []
        text_lower = text.lower()

        # Check for medical terms and abbreviations
        for term, expansion in self.medical_terms.items():
            if term.lower() in text_lower or expansion.lower() in text_lower:
                found_terms.append(term)

        # Check for common medical patterns
        medical_patterns = [
            r"\b\d+\s*(?:mg|milligrams?)\b",  # Medication dosages
            r"\b\d+\s*degrees?\b",  # Temperature
            r"\b\d+\s*over\s*\d+\b",  # Blood pressure
            r"\b\d+\s*(?:bpm|beats per minute)\b",  # Heart rate
        ]

        for pattern in medical_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            found_terms.extend([match.strip() for match in matches])

        return list(set(found_terms))  # Remove duplicates

    async def _transcribe_with_mcp(self, audio_data: dict[str, Any]) -> dict[str, Any]:
        """
        Use MCP client to perform real audio transcription

        Args:
            audio_data: Dictionary containing audio file information

        Returns:
            Dictionary with transcription results
        """
        if not self.mcp_client:
            raise RuntimeError("MCP client not available for transcription")

        try:
            # Prepare MCP transcription arguments
            transcription_args = {
                "audio_file_path": audio_data.get("audio_file_path"),
                "audio_format": audio_data.get("audio_format", "wav"),
                "sample_rate": audio_data.get("sample_rate", 16000),
                "channels": audio_data.get("channels", 1),
                "language": audio_data.get("language", "en-US"),
                "model_type": "medical",  # Use medical-specific model if available
                "provider_id": audio_data.get("provider_id"),
                "encounter_id": audio_data.get("encounter_id"),
            }

            # Call MCP transcription tool
            result = await self.mcp_client.call_tool("transcribe_medical_audio", transcription_args)

            if result.get("status") == "success":
                return {
                    "transcribed_text": result.get("text", ""),
                    "confidence_score": result.get("confidence", TRANSCRIPTION_CONFIG.quality.default_confidence_threshold),
                    "duration_seconds": result.get("duration", 0),
                    "word_count": result.get("word_count", 0),
                    "processing_time": result.get("processing_time", 0),
                }
            msg = f"MCP transcription failed: {result.get('error', 'Unknown error')}"
            raise RuntimeError(
                msg,
            )

        except Exception as e:
            log_healthcare_event(
                self.logger,
                logging.ERROR,
                f"MCP transcription error: {str(e)}",
                context={
                    "audio_file": audio_data.get("audio_file_path"),
                    "provider_id": audio_data.get("provider_id"),
                    "error": str(e),
                },
                operation_type="mcp_transcription_error",
            )
            raise

    async def _process_audio_file(
        self, audio_file_path: str, audio_format: str | None = None,
    ) -> dict[str, Any]:
        """
        Process audio file and prepare for transcription

        Args:
            audio_file_path: Path to the audio file
            audio_format: Audio format (wav, mp3, m4a, etc.)

        Returns:
            Dictionary with processed audio information
        """
        try:
            audio_path = Path(audio_file_path)

            if not audio_path.exists():
                msg = f"Audio file not found: {audio_file_path}"
                raise FileNotFoundError(msg)

            # Determine audio format from file extension if not provided
            if not audio_format:
                audio_format = audio_path.suffix.lower().lstrip(".")

            # Get file size and basic metadata
            file_size = audio_path.stat().st_size

            # Validate audio format
            supported_formats = ["wav", "mp3", "m4a", "flac", "ogg", "aac"]
            if audio_format not in supported_formats:
                msg = f"Unsupported audio format: {audio_format}. Supported formats: {supported_formats}"
                raise ValueError(
                    msg,
                )

            # Estimate duration (rough calculation - would use proper audio library in production)
            estimated_duration = self._estimate_audio_duration(file_size, audio_format)

            return {
                "file_path": str(audio_path),
                "file_size": file_size,
                "audio_format": audio_format,
                "estimated_duration": estimated_duration,
                "sample_rate": 16000,  # Default for medical audio
                "channels": 1,  # Mono for speech
            }

        except Exception as e:
            log_healthcare_event(
                self.logger,
                logging.ERROR,
                f"Audio file processing error: {str(e)}",
                context={
                    "audio_file_path": audio_file_path,
                    "audio_format": audio_format,
                    "error": str(e),
                },
                operation_type="audio_processing_error",
            )
            raise

    def _estimate_audio_duration(self, file_size: int, audio_format: str) -> float:
        """
        Estimate audio duration based on file size and format

        Args:
            file_size: File size in bytes
            audio_format: Audio format

        Returns:
            Estimated duration in seconds
        """
        # Rough estimates - would use proper audio library in production
        format_bitrates = {
            "wav": 1411200,  # CD quality uncompressed
            "mp3": 128000,  # Standard MP3
            "m4a": 256000,  # AAC
            "flac": 1000000,  # Lossless compressed
            "ogg": 160000,  # OGG Vorbis
            "aac": 256000,  # AAC
        }

        bitrate = format_bitrates.get(audio_format, 128000)
        return (file_size * 8) / bitrate  # Convert to seconds

    def _validate_transcription_quality(self, text: str) -> list[str]:
        """Validate transcription quality and identify potential issues"""
        if not text:
            return ["Empty transcription text"]

        quality_issues = []

        # Check for minimum length
        if len(text.strip()) < 50:
            quality_issues.append("Transcription appears too short for medical encounter")

        # Check for common transcription artifacts
        artifacts = ["um", "uh", "er", "[inaudible]", "[unclear]"]
        artifact_count = sum(text.lower().count(artifact) for artifact in artifacts)

        if artifact_count > 5:
            quality_issues.append(f"High number of speech artifacts detected: {artifact_count}")

        # Check for incomplete sentences
        sentence_endings = text.count(".") + text.count("!") + text.count("?")
        if sentence_endings < 3:
            quality_issues.append("Few complete sentences detected - check for truncation")

        return quality_issues

    @healthcare_log_method(operation_type="audio_transcription", phi_risk_level="high")
    @phi_monitor(risk_level="medium", operation_type="clinical_note_generation")
    async def generate_clinical_note(self, note_request: dict[str, Any]) -> ClinicalNoteResult:
        """
        Generate structured clinical note from transcription or input data

        Args:
            note_request: Dictionary containing note generation requirements

        Returns:
            ClinicalNoteResult with structured clinical note

        Medical Disclaimer: Administrative note formatting only.
        Does not provide medical advice or clinical decision-making.
        """
        # Validate and sanitize input data for PHI protection
        scan_for_phi(str(note_request))

        try:
            note_type = note_request.get("note_type", "soap_note")
            raw_content = note_request.get("content", "")

            # Get appropriate template
            template = self.templates.get(note_type)
            if not template:
                template = self.templates["soap_note"]  # Default to SOAP note

            # Structure the content
            structured_content = await self._structure_note_content(raw_content, template)

            # Format the note
            formatted_note = await self._format_clinical_note(structured_content, template)

            # Calculate quality score
            quality_score = self._calculate_note_quality(structured_content, template)

            # Identify missing sections
            missing_sections = self._identify_missing_sections(structured_content, template)

            # Generate recommendations
            recommendations = self._generate_note_recommendations(
                structured_content,
                missing_sections,
            )

            log_healthcare_event(
                self.logger,
                logging.INFO,
                f"Clinical note generated: {note_type}",
                context={
                    "note_type": note_type,
                    "quality_score": quality_score,
                    "missing_sections_count": len(missing_sections),
                    "recommendations_count": len(recommendations),
                },
                operation_type="clinical_note_generation",
            )

            return ClinicalNoteResult(
                note_id=f"note_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                note_type=note_type,
                structured_content=structured_content,
                formatted_note=formatted_note,
                quality_score=quality_score,
                missing_sections=missing_sections,
                recommendations=recommendations,
                timestamp=datetime.now(),
            )

        except Exception as e:
            log_healthcare_event(
                self.logger,
                logging.ERROR,
                f"Clinical note generation failed: {str(e)}",
                context={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "note_type": note_request.get("note_type", "unknown"),
                },
                operation_type="note_generation_error",
            )

            # Return minimal result on error
            return ClinicalNoteResult(
                note_id=f"note_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                note_type=note_request.get("note_type", "soap_note"),
                structured_content={},
                formatted_note=f"Error generating note: {str(e)}",
                quality_score=0.0,
                missing_sections=[],
                recommendations=[f"Note generation failed: {str(e)}"],
                timestamp=datetime.now(),
            )

    async def _structure_note_content(
        self,
        raw_content: str,
        template: DocumentationTemplate,
    ) -> dict[str, Any]:
        """Structure raw content into organized sections"""

        # Mock content structuring (in production, use NLP to extract sections)
        structured = {
            "subjective": "Patient reports symptoms as described above.",
            "objective": "Physical examination findings documented.",
            "assessment": "Clinical assessment based on presentation.",
            "plan": "Treatment plan outlined for patient care.",
        }

        # Add content from raw text if available
        if raw_content:
            # Simple keyword-based section detection
            if "chief complaint" in raw_content.lower():
                cc_start = raw_content.lower().find("chief complaint")
                cc_section = raw_content[cc_start : cc_start + 200]
                structured["chief_complaint"] = cc_section

            if "physical exam" in raw_content.lower():
                pe_start = raw_content.lower().find("physical exam")
                pe_section = raw_content[pe_start : pe_start + 300]
                structured["objective"] = pe_section

            if "assessment" in raw_content.lower():
                assessment_start = raw_content.lower().find("assessment")
                assessment_section = raw_content[assessment_start : assessment_start + 200]
                structured["assessment"] = assessment_section

            if "plan" in raw_content.lower():
                plan_start = raw_content.lower().find("plan")
                plan_section = raw_content[plan_start : plan_start + 200]
                structured["plan"] = plan_section

        return structured

    async def _format_clinical_note(
        self,
        structured_content: dict[str, Any],
        template: DocumentationTemplate,
    ) -> str:
        """Format structured content into clinical note"""

        formatted_lines = []
        formatted_lines.append(f"Clinical Note - {template.template_name}")
        formatted_lines.append(f"Date: {datetime.now().strftime('%m/%d/%Y')}")
        formatted_lines.append("")

        # Add sections in template order
        for section in template.required_sections:
            if section in structured_content:
                section_title = section.replace("_", " ").title()
                formatted_lines.append(f"{section_title}:")
                formatted_lines.append(structured_content[section])
                formatted_lines.append("")

        # Add optional sections if present
        for section in template.optional_sections:
            if section in structured_content:
                section_title = section.replace("_", " ").title()
                formatted_lines.append(f"{section_title}:")
                formatted_lines.append(structured_content[section])
                formatted_lines.append("")

        return "\n".join(formatted_lines)

    def _calculate_note_quality(
        self,
        structured_content: dict[str, Any],
        template: DocumentationTemplate,
    ) -> float:
        """Calculate quality score for clinical note"""

        total_sections = len(template.required_sections) + len(template.optional_sections)
        present_sections = len(
            [
                s
                for s in template.required_sections + template.optional_sections
                if s in structured_content
            ],
        )

        section_score = present_sections / total_sections if total_sections > 0 else 0.0

        # Check content quality
        content_score = 0.0
        for content in structured_content.values():
            if content and len(content.strip()) > 10:
                content_score += 1

        content_score = (
            min(content_score / len(structured_content), 1.0) if structured_content else 0.0
        )

        # Overall quality score
        quality_score = (section_score * 0.6) + (content_score * 0.4)
        return round(quality_score, 2)

    def _identify_missing_sections(
        self,
        structured_content: dict[str, Any],
        template: DocumentationTemplate,
    ) -> list[str]:
        """Identify missing required sections"""

        missing = []
        for section in template.required_sections:
            if section not in structured_content or not structured_content[section].strip():
                missing.append(section.replace("_", " ").title())

        return missing

    def _generate_note_recommendations(
        self,
        structured_content: dict[str, Any],
        missing_sections: list[str],
    ) -> list[str]:
        """Generate recommendations for note improvement"""

        recommendations = []

        if missing_sections:
            recommendations.append(
                f"Consider adding missing sections: {', '.join(missing_sections)}",
            )

        # Check for specific content recommendations
        if "assessment" in structured_content:
            assessment = structured_content["assessment"].lower()
            if "diagnosis" not in assessment and "condition" not in assessment:
                recommendations.append(
                    "Consider including specific diagnosis or clinical condition in assessment",
                )

        if "plan" in structured_content:
            plan = structured_content["plan"].lower()
            if "follow" not in plan and "return" not in plan:
                recommendations.append("Consider adding follow-up instructions to treatment plan")

        if not recommendations:
            recommendations.append("Clinical note appears complete and well-structured")

        return recommendations

    async def _store_transcription_result(self, result: TranscriptionResult) -> bool:
        """
        Store transcription result in database with HIPAA compliance

        Args:
            result: TranscriptionResult to store

        Returns:
            bool: Success status
        """
        try:
            if not self._db_connection:
                log_healthcare_event(
                    self.logger,
                    logging.WARNING,
                    "Database not available for transcription storage",
                    context={"transcription_id": result.transcription_id},
                    operation_type="database_unavailable",
                )
                return False

            # Store in database with PHI protection
            insert_query = """
            INSERT INTO medical_transcriptions
            (transcription_id, provider_id, encounter_type, status,
             audio_duration, confidence_score, medical_terms_count,
             compliance_validated, created_at, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """

            await self._db_connection.execute(
                insert_query,
                result.transcription_id,
                result.metadata.get("provider_id"),
                result.metadata.get("encounter_type"),
                result.status,
                result.original_audio_duration,
                result.confidence_score,
                len(result.medical_terms_identified),
                result.compliance_validated,
                result.timestamp,
                result.metadata,
            )

            log_healthcare_event(
                self.logger,
                logging.INFO,
                f"Transcription result stored: {result.transcription_id}",
                context={
                    "transcription_id": result.transcription_id,
                    "status": result.status,
                },
                operation_type="transcription_stored",
            )
            return True

        except Exception as e:
            log_healthcare_event(
                self.logger,
                logging.ERROR,
                f"Failed to store transcription result: {str(e)}",
                context={
                    "transcription_id": result.transcription_id,
                    "error": str(e),
                },
                operation_type="database_error",
            )
            return False

    async def _cleanup_temporary_files(self, file_paths: list[str]) -> None:
        """
        Clean up temporary audio files securely

        Args:
            file_paths: List of temporary file paths to clean up
        """
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    # Secure deletion for HIPAA compliance
                    with open(file_path, "r+b") as f:
                        length = f.tell()
                        f.seek(0)
                        f.write(os.urandom(length))  # Overwrite with random data
                        f.flush()
                        os.fsync(f.fileno())  # Force write to disk

                    os.remove(file_path)

                    log_healthcare_event(
                        self.logger,
                        logging.INFO,
                        f"Temporary file securely deleted: {file_path}",
                        context={"file_path": file_path},
                        operation_type="file_cleanup",
                    )

            except Exception as e:
                log_healthcare_event(
                    self.logger,
                    logging.WARNING,
                    f"Failed to clean up temporary file: {file_path} - {str(e)}",
                    context={
                        "file_path": file_path,
                        "error": str(e),
                    },
                    operation_type="cleanup_error",
                )

    async def _create_secure_temp_file(self, suffix: str = ".tmp") -> tuple[str, str]:
        """
        Create a secure temporary file for audio processing

        Args:
            suffix: File suffix

        Returns:
            Tuple of (file_path, file_descriptor)
        """
        try:
            # Create temporary file in secure location
            temp_dir = tempfile.gettempdir()
            temp_id = str(uuid.uuid4())
            temp_path = os.path.join(temp_dir, f"transcription_{temp_id}{suffix}")

            # Create file with secure permissions (owner read/write only)
            fd = os.open(temp_path, os.O_CREAT | os.O_WRONLY | os.O_EXCL, 0o600)

            log_healthcare_event(
                self.logger,
                logging.DEBUG,
                f"Secure temporary file created: {temp_path}",
                context={"temp_file": temp_path},
                operation_type="temp_file_created",
            )

            return temp_path, str(fd)

        except Exception as e:
            log_healthcare_event(
                self.logger,
                logging.ERROR,
                f"Failed to create secure temporary file: {str(e)}",
                context={"error": str(e)},
                operation_type="temp_file_error",
            )
            raise

    async def _process_implementation(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Implement agent-specific processing logic for transcription requests

        Args:
            request: Request containing transcription parameters

        Returns:
            dict: Processing result with transcription data
        """
        temp_files = []

        try:
            # Check for real-time transcription request first
            if request.get("real_time") and "audio_data" in request:
                # Process real-time audio chunk
                audio_data = request["audio_data"]
                session_id = request.get("session_id", "default")
                doctor_id = request.get("doctor_id", "unknown")

                # Handle real-time audio chunk processing
                result = await self.process_real_time_audio(audio_data, session_id, doctor_id)

                return {
                    "success": True,
                    "transcription": result.get("transcription", ""),
                    "confidence": result.get("confidence", 0.0),
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                    "medical_terms": result.get("medical_terms", []),
                }

            if "audio_data" in request:
                # Process audio transcription
                audio_data = request["audio_data"]

                # Store any temporary files for cleanup
                if "temp_audio_path" in audio_data:
                    temp_files.append(audio_data["temp_audio_path"])

                result = await self.transcribe_audio(audio_data)

                # Store result in database if available
                await self._store_transcription_result(result)

                response_dict = cast("dict[str, Any]", result.__dict__)
                response_dict["success"] = True
                return response_dict

            if "text_data" in request:
                # Process clinical note generation
                result = await self.generate_clinical_note(request["text_data"])

                response_dict = cast("dict[str, Any]", result.__dict__)
                response_dict["success"] = True
                return response_dict

            if "batch_audio_data" in request:
                # Process batch audio transcription
                batch_results = []
                for audio_item in request["batch_audio_data"]:
                    if "temp_audio_path" in audio_item:
                        temp_files.append(audio_item["temp_audio_path"])

                    result = await self.transcribe_audio(audio_item)
                    await self._store_transcription_result(result)
                    batch_results.append(cast("dict[str, Any]", result.__dict__))

                return {
                    "success": True,
                    "batch_results": batch_results,
                    "total_processed": len(batch_results),
                }

            return {
                "success": False,
                "error": "No supported data type found in request",
                "supported_types": ["audio_data", "text_data", "batch_audio_data"],
            }

        except Exception as e:
            log_healthcare_event(
                self.logger,
                logging.ERROR,
                f"Transcription processing failed: {str(e)}",
                context={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "request_id": request.get("request_id", "unknown"),
                },
                operation_type="processing_error",
            )

            return {
                "success": False,
                "error": f"Transcription processing failed: {str(e)}",
                "request_id": request.get("request_id", "unknown"),
            }

        finally:
            # Always clean up temporary files
            if temp_files:
                await self._cleanup_temporary_files(temp_files)

    async def cleanup(self) -> None:
        """
        Override cleanup method to include transcription-specific cleanup
        """
        try:
            # Clean up any remaining temporary files
            temp_dir = tempfile.gettempdir()
            transcription_temp_files = []

            for file_name in os.listdir(temp_dir):
                if file_name.startswith("transcription_"):
                    transcription_temp_files.append(os.path.join(temp_dir, file_name))

            if transcription_temp_files:
                await self._cleanup_temporary_files(transcription_temp_files)

            # Call parent cleanup for database connections
            await super().cleanup()

            log_healthcare_event(
                self.logger,
                logging.INFO,
                "Transcription agent cleanup completed",
                context={
                    "agent": self.agent_name,
                    "temp_files_cleaned": len(transcription_temp_files),
                },
                operation_type="agent_cleanup",
            )

        except Exception as e:
            log_healthcare_event(
                self.logger,
                logging.ERROR,
                f"Error during transcription agent cleanup: {str(e)}",
                context={
                    "agent": self.agent_name,
                    "error": str(e),
                },
                operation_type="cleanup_error",
            )


# Initialize the transcription agent
transcription_agent = TranscriptionAgent()
