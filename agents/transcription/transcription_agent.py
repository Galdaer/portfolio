"""
Healthcare Transcription Agent - Administrative Transcription Support Only
Handles medical dictation processing, clinical note generation, and documentation support for healthcare workflows
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast

from agents import BaseHealthcareAgent
from core.infrastructure.healthcare_logger import (
    get_healthcare_logger,
    healthcare_log_method,
    log_healthcare_event,
)
from core.infrastructure.phi_monitor import phi_monitor_decorator as phi_monitor
from core.infrastructure.phi_monitor import scan_for_phi

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

    def __init__(self) -> None:
        super().__init__("transcription", "transcription")
        self.agent_type = "transcription"
        self.capabilities = [
            "audio_transcription",
            "clinical_note_generation",
            "medical_terminology_validation",
            "documentation_formatting",
            "soap_note_structuring",
            "quality_assurance",
        ]

        # Initialize medical terminology dictionary
        self.medical_terms = {
            # Common medical abbreviations and terms
            "bp": "blood pressure",
            "hr": "heart rate",
            "temp": "temperature",
            "resp": "respiration",
            "wt": "weight",
            "ht": "height",
            "bmi": "body mass index",
            "chief complaint": "CC",
            "history of present illness": "HPI",
            "past medical history": "PMH",
            "social history": "SH",
            "family history": "FH",
            "review of systems": "ROS",
            "physical exam": "PE",
            "assessment and plan": "A&P",
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
            logger,
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
                logger,
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
                logger,
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
            await asyncio.sleep(0.3)  # Simulate processing time

            # Mock transcribed text for different encounter types
            encounter_type = audio_data.get("encounter_type", "office_visit")
            transcribed_text = await self._generate_mock_transcription(encounter_type)

            # Calculate mock confidence score
            confidence_score = 0.92  # High confidence for demonstration

            # Identify medical terms in transcription
            medical_terms_found = self._identify_medical_terms(transcribed_text)

            # Validate transcription quality
            quality_issues = self._validate_transcription_quality(transcribed_text)
            if quality_issues:
                transcription_errors.extend(quality_issues)

            status = "completed" if not transcription_errors else "completed_with_warnings"

            log_healthcare_event(
                logger,
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
                logger,
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
                structured_content, missing_sections
            )

            log_healthcare_event(
                logger,
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
                logger,
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
        self, raw_content: str, template: DocumentationTemplate
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
        self, structured_content: dict[str, Any], template: DocumentationTemplate
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
        self, structured_content: dict[str, Any], template: DocumentationTemplate
    ) -> float:
        """Calculate quality score for clinical note"""

        total_sections = len(template.required_sections) + len(template.optional_sections)
        present_sections = len(
            [
                s
                for s in template.required_sections + template.optional_sections
                if s in structured_content
            ]
        )

        section_score = present_sections / total_sections if total_sections > 0 else 0.0

        # Check content quality
        content_score = 0.0
        for _section, content in structured_content.items():
            if content and len(content.strip()) > 10:
                content_score += 1

        content_score = (
            min(content_score / len(structured_content), 1.0) if structured_content else 0.0
        )

        # Overall quality score
        quality_score = (section_score * 0.6) + (content_score * 0.4)
        return round(quality_score, 2)

    def _identify_missing_sections(
        self, structured_content: dict[str, Any], template: DocumentationTemplate
    ) -> list[str]:
        """Identify missing required sections"""

        missing = []
        for section in template.required_sections:
            if section not in structured_content or not structured_content[section].strip():
                missing.append(section.replace("_", " ").title())

        return missing

    def _generate_note_recommendations(
        self, structured_content: dict[str, Any], missing_sections: list[str]
    ) -> list[str]:
        """Generate recommendations for note improvement"""

        recommendations = []

        if missing_sections:
            recommendations.append(
                f"Consider adding missing sections: {', '.join(missing_sections)}"
            )

        # Check for specific content recommendations
        if "assessment" in structured_content:
            assessment = structured_content["assessment"].lower()
            if "diagnosis" not in assessment and "condition" not in assessment:
                recommendations.append(
                    "Consider including specific diagnosis or clinical condition in assessment"
                )

        if "plan" in structured_content:
            plan = structured_content["plan"].lower()
            if "follow" not in plan and "return" not in plan:
                recommendations.append("Consider adding follow-up instructions to treatment plan")

        if not recommendations:
            recommendations.append("Clinical note appears complete and well-structured")

        return recommendations

    async def _process_implementation(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Implement agent-specific processing logic for transcription requests

        Args:
            request: Request containing transcription parameters

        Returns:
            dict: Processing result with transcription data
        """
        try:
            if "audio_data" in request:
                result = await self.transcribe_audio(request["audio_data"])
                return cast(dict[str, Any], result.__dict__)
            elif "text_data" in request:
                result = await self.generate_clinical_note(request["text_data"])
                return cast(dict[str, Any], result.__dict__)
            else:
                return {
                    "success": False,
                    "error": "No supported data type found in request",
                    "supported_types": ["audio_data", "text_data"],
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Transcription processing failed: {str(e)}",
                "request_id": request.get("request_id", "unknown"),
            }


# Initialize the transcription agent
transcription_agent = TranscriptionAgent()
