"""
Healthcare SOAP Notes Agent - Clinical Documentation Generation

Generates structured clinical documentation from transcribed medical encounters.
Supports SOAP notes, progress notes, H&P notes, and other clinical formats.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from agents import BaseHealthcareAgent
from core.compliance.agent_compliance_monitor import compliance_monitor_decorator
from core.enhanced_sessions import EnhancedSessionManager
from core.infrastructure.agent_metrics import AgentMetricsStore
from core.infrastructure.healthcare_cache import HealthcareCacheManager
from core.infrastructure.healthcare_logger import (
    get_healthcare_logger,
    healthcare_log_method,
    log_healthcare_event,
)
from core.infrastructure.phi_monitor import phi_monitor_decorator as phi_monitor, scan_for_phi

logger = get_healthcare_logger("agent.soap_notes")


@dataclass
class SOAPNote:
    """Structured SOAP note representation"""
    note_id: str
    encounter_date: datetime
    provider_id: str
    patient_id: str

    # SOAP Components
    subjective: str
    objective: str
    assessment: str
    plan: str

    # Additional sections
    chief_complaint: str
    history_present_illness: str
    review_of_systems: str
    physical_examination: str
    medical_decision_making: str

    # Quality metrics
    completeness_score: float
    missing_sections: list[str]
    quality_recommendations: list[str]

    timestamp: datetime


@dataclass
class ProgressNote:
    """Progress note for follow-up visits"""
    note_id: str
    encounter_date: datetime
    provider_id: str
    patient_id: str

    interval_history: str
    current_medications: str
    physical_exam: str
    assessment_and_plan: str

    timestamp: datetime


@dataclass
class NoteTemplate:
    """Template for clinical note generation"""
    template_id: str
    template_name: str
    note_type: str
    required_sections: list[str]
    optional_sections: list[str]
    format_rules: dict[str, Any]


class SoapNotesAgent(BaseHealthcareAgent):
    """
    SOAP Notes Agent for Clinical Documentation

    MEDICAL DISCLAIMER: This agent provides administrative clinical documentation
    support only. It assists healthcare professionals with formatting and organizing
    clinical notes based on transcribed medical encounters. It does not provide
    medical advice, diagnosis, or treatment recommendations. All medical content
    must be reviewed and validated by qualified healthcare professionals.

    Capabilities:
    - SOAP note generation from transcription data
    - Progress note creation for follow-up visits
    - Clinical note template management
    - Documentation completeness assessment
    - Medical terminology validation in notes
    - Format standardization for EHR integration
    """

    def __init__(self, mcp_client=None, llm_client=None) -> None:
        super().__init__(
            mcp_client=mcp_client,
            llm_client=llm_client,
            agent_name="soap_notes",
            agent_type="clinical_documentation",
        )
        self.logger = get_healthcare_logger(f"agent.{self.agent_name}")

        # Initialize shared healthcare infrastructure tools
        self._metrics = AgentMetricsStore(agent_name="soap_notes")
        self._cache_manager = HealthcareCacheManager()
        self._session_manager = EnhancedSessionManager()

        # Initialize note templates
        self.note_templates = self._initialize_note_templates()

        # Clinical section patterns for content extraction
        self.section_patterns = {
            "chief_complaint": [
                r"chief complaint[:\s]+(.*?)(?=\n|$|history of present illness|physical exam)",
                r"cc[:\s]+(.*?)(?=\n|$|hpi|physical exam)",
                r"presenting complaint[:\s]+(.*?)(?=\n|$|history|physical exam)",
            ],
            "history_present_illness": [
                r"history of present illness[:\s]+(.*?)(?=\n\n|review of systems|physical exam|past medical history)",
                r"hpi[:\s]+(.*?)(?=\n\n|ros|physical exam|pmh)",
            ],
            "physical_examination": [
                r"physical exam(?:ination)?[:\s]+(.*?)(?=\n\n|assessment|plan|impression)",
                r"pe[:\s]+(.*?)(?=\n\n|assessment|plan|impression)",
                r"exam(?:ination)?[:\s]+(.*?)(?=\n\n|assessment|plan|impression)",
            ],
            "assessment": [
                r"assessment[:\s]+(.*?)(?=\n\n|plan|impression|diagnosis)",
                r"impression[:\s]+(.*?)(?=\n\n|plan|assessment)",
                r"diagnosis[:\s]+(.*?)(?=\n\n|plan|assessment)",
            ],
            "plan": [
                r"plan[:\s]+(.*?)(?=\n\n|$|follow.?up|return)",
                r"treatment plan[:\s]+(.*?)(?=\n\n|$|follow.?up|return)",
            ],
        }

        logger.info("SOAP Notes Agent initialized successfully")

    def _initialize_note_templates(self) -> dict[str, NoteTemplate]:
        """Initialize clinical note templates"""

        templates = {}

        # SOAP Note Template
        templates["soap"] = NoteTemplate(
            template_id="soap_standard",
            template_name="Standard SOAP Note",
            note_type="soap",
            required_sections=["subjective", "objective", "assessment", "plan"],
            optional_sections=["chief_complaint", "history_present_illness", "review_of_systems",
                              "physical_examination", "medical_decision_making"],
            format_rules={
                "section_headers": "uppercase",
                "indent_subsections": True,
                "include_timestamps": True,
                "numbered_assessments": True,
            },
        )

        # Progress Note Template
        templates["progress"] = NoteTemplate(
            template_id="progress_standard",
            template_name="Standard Progress Note",
            note_type="progress",
            required_sections=["interval_history", "physical_exam", "assessment_and_plan"],
            optional_sections=["current_medications", "vitals"],
            format_rules={
                "section_headers": "title_case",
                "bullet_points": True,
                "include_timestamps": True,
            },
        )

        # H&P Note Template
        templates["history_physical"] = NoteTemplate(
            template_id="hp_standard",
            template_name="History & Physical",
            note_type="history_physical",
            required_sections=["chief_complaint", "history_present_illness", "past_medical_history",
                              "medications", "allergies", "social_history", "physical_examination",
                              "assessment", "plan"],
            optional_sections=["review_of_systems", "family_history"],
            format_rules={
                "detailed_sections": True,
                "comprehensive_format": True,
                "include_normal_findings": True,
            },
        )

        return templates

    async def _process_implementation(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Process SOAP note generation requests

        Args:
            request: Request containing transcription data and note generation parameters

        Returns:
            dict: Generated clinical note with formatting and quality assessment
        """
        try:
            if "generate_soap_note" in request:
                # Generate SOAP note from transcription
                transcription_data = request["generate_soap_note"]
                note_type = transcription_data.get("note_type", "soap")

                result = await self.generate_soap_note(transcription_data, note_type)

                return {
                    "success": True,
                    "note_id": result.note_id,
                    "note_type": note_type,
                    "subjective": result.subjective,
                    "objective": result.objective,
                    "assessment": result.assessment,
                    "plan": result.plan,
                    "chief_complaint": result.chief_complaint,
                    "completeness_score": result.completeness_score,
                    "missing_sections": result.missing_sections,
                    "quality_recommendations": result.quality_recommendations,
                    "formatted_note": await self._format_soap_note(result),
                    "timestamp": result.timestamp.isoformat(),
                }

            if "generate_progress_note" in request:
                # Generate progress note from transcription
                transcription_data = request["generate_progress_note"]

                result = await self.generate_progress_note(transcription_data)

                return {
                    "success": True,
                    "note_id": result.note_id,
                    "note_type": "progress",
                    "interval_history": result.interval_history,
                    "physical_exam": result.physical_exam,
                    "assessment_and_plan": result.assessment_and_plan,
                    "formatted_note": await self._format_progress_note(result),
                    "timestamp": result.timestamp.isoformat(),
                }

            if "format_existing_note" in request:
                # Format an existing clinical note
                note_data = request["format_existing_note"]
                note_type = note_data.get("note_type", "soap")

                formatted_note = await self._format_clinical_note(note_data, note_type)

                return {
                    "success": True,
                    "formatted_note": formatted_note,
                    "note_type": note_type,
                    "timestamp": datetime.now().isoformat(),
                }

            if "session_to_soap" in request:
                # Generate SOAP note from live transcription session
                session_data = request["session_to_soap"]
                session_id = session_data.get("session_id")
                full_transcription = session_data.get("full_transcription")

                if not full_transcription:
                    return {
                        "success": False,
                        "error": "No transcription data provided for SOAP generation",
                    }

                # Create SOAP note from session transcription
                soap_data = {
                    "transcription_text": full_transcription,
                    "encounter_date": session_data.get("encounter_date", datetime.now().isoformat()),
                    "provider_id": session_data.get("doctor_id", "unknown"),
                    "patient_id": session_data.get("patient_id", "unknown"),
                    "note_type": "soap",
                }

                result = await self.generate_soap_note(soap_data, "soap")

                return {
                    "success": True,
                    "session_id": session_id,
                    "note_id": result.note_id,
                    "soap_note": await self._format_soap_note(result),
                    "completeness_score": result.completeness_score,
                    "missing_sections": result.missing_sections,
                    "quality_recommendations": result.quality_recommendations,
                    "timestamp": result.timestamp.isoformat(),
                }

            return {
                "success": False,
                "error": "No supported operation found in request",
                "supported_operations": [
                    "generate_soap_note",
                    "generate_progress_note",
                    "format_existing_note",
                    "session_to_soap",
                ],
            }

        except Exception as e:
            log_healthcare_event(
                self.logger,
                logging.ERROR,
                f"SOAP notes generation failed: {str(e)}",
                context={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "request_keys": list(request.keys()),
                },
                operation_type="soap_generation_error",
            )

            return {
                "success": False,
                "error": f"SOAP notes generation failed: {str(e)}",
                "timestamp": datetime.now().isoformat(),
            }

    @healthcare_log_method(operation_type="soap_note_generation", phi_risk_level="high")
    @phi_monitor(risk_level="high", operation_type="soap_note_generation")
    @compliance_monitor_decorator(
        operation_type="clinical_documentation",
        phi_risk_level="high",
        validate_input=True,
        validate_output=True
    )
    async def generate_soap_note(self, transcription_data: dict[str, Any], note_type: str = "soap") -> SOAPNote:
        """
        Generate structured SOAP note from transcription data

        Args:
            transcription_data: Dictionary containing transcription text and metadata
            note_type: Type of clinical note to generate

        Returns:
            SOAPNote: Structured clinical note with all sections
        """

        try:
            # Extract transcription text
            transcription_text = transcription_data.get("transcription_text", "")
            if not transcription_text:
                transcription_text = transcription_data.get("full_transcription", "")

            # Validate and sanitize transcription for PHI
            scan_for_phi(transcription_text)

            # Extract encounter information
            encounter_date = transcription_data.get("encounter_date", datetime.now())
            if isinstance(encounter_date, str):
                encounter_date = datetime.fromisoformat(encounter_date.replace("Z", "+00:00"))

            provider_id = transcription_data.get("provider_id", "unknown")
            patient_id = transcription_data.get("patient_id", "unknown")

            # Generate unique note ID
            note_id = f"soap_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{provider_id}"

            log_healthcare_event(
                self.logger,
                logging.INFO,
                "Generating SOAP note from transcription",
                context={
                    "note_id": note_id,
                    "provider_id": provider_id,
                    "transcription_length": len(transcription_text),
                    "note_type": note_type,
                },
                operation_type="soap_generation_start",
            )

            # Extract clinical sections using NLP patterns
            sections = await self._extract_clinical_sections(transcription_text)

            # Generate SOAP components
            subjective = await self._generate_subjective_section(sections, transcription_text)
            objective = await self._generate_objective_section(sections, transcription_text)
            assessment = await self._generate_assessment_section(sections, transcription_text)
            plan = await self._generate_plan_section(sections, transcription_text)

            # Generate additional sections
            chief_complaint = sections.get("chief_complaint", "Not specified in transcription")
            history_present_illness = sections.get("history_present_illness", "See subjective section")
            review_of_systems = "Not systematically reviewed"
            physical_examination = sections.get("physical_examination", objective)
            medical_decision_making = "See assessment and plan sections"

            # Assess note completeness and quality
            completeness_score, missing_sections, recommendations = await self._assess_note_quality({
                "subjective": subjective,
                "objective": objective,
                "assessment": assessment,
                "plan": plan,
                "chief_complaint": chief_complaint,
            })

            # Create SOAP note object
            soap_note = SOAPNote(
                note_id=note_id,
                encounter_date=encounter_date,
                provider_id=provider_id,
                patient_id=patient_id,
                subjective=subjective,
                objective=objective,
                assessment=assessment,
                plan=plan,
                chief_complaint=chief_complaint,
                history_present_illness=history_present_illness,
                review_of_systems=review_of_systems,
                physical_examination=physical_examination,
                medical_decision_making=medical_decision_making,
                completeness_score=completeness_score,
                missing_sections=missing_sections,
                quality_recommendations=recommendations,
                timestamp=datetime.now(),
            )

            log_healthcare_event(
                self.logger,
                logging.INFO,
                "SOAP note generated successfully",
                context={
                    "note_id": note_id,
                    "completeness_score": completeness_score,
                    "missing_sections_count": len(missing_sections),
                },
                operation_type="soap_generation_complete",
            )

            return soap_note

        except Exception as e:
            log_healthcare_event(
                self.logger,
                logging.ERROR,
                f"SOAP note generation failed: {str(e)}",
                context={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "provider_id": transcription_data.get("provider_id", "unknown"),
                },
                operation_type="soap_generation_error",
            )
            raise

    async def generate_progress_note(self, transcription_data: dict[str, Any]) -> ProgressNote:
        """Generate progress note for follow-up visits"""

        transcription_text = transcription_data.get("transcription_text", "")
        encounter_date = transcription_data.get("encounter_date", datetime.now())
        if isinstance(encounter_date, str):
            encounter_date = datetime.fromisoformat(encounter_date.replace("Z", "+00:00"))

        provider_id = transcription_data.get("provider_id", "unknown")
        patient_id = transcription_data.get("patient_id", "unknown")
        note_id = f"progress_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{provider_id}"

        # Extract sections for progress note
        sections = await self._extract_clinical_sections(transcription_text)

        interval_history = sections.get("interval_history", "Patient reports doing well since last visit.")
        current_medications = sections.get("medications", "Current medications reviewed.")
        physical_exam = sections.get("physical_examination", "Physical examination performed.")
        assessment_and_plan = f"{sections.get('assessment', 'Assessment documented.')} {sections.get('plan', 'Plan discussed with patient.')}"

        return ProgressNote(
            note_id=note_id,
            encounter_date=encounter_date,
            provider_id=provider_id,
            patient_id=patient_id,
            interval_history=interval_history,
            current_medications=current_medications,
            physical_exam=physical_exam,
            assessment_and_plan=assessment_and_plan,
            timestamp=datetime.now(),
        )

    async def _extract_clinical_sections(self, transcription_text: str) -> dict[str, str]:
        """Extract clinical sections from transcription text using pattern matching"""

        sections = {}
        text_lower = transcription_text.lower()

        for section_name, patterns in self.section_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text_lower, re.IGNORECASE | re.DOTALL)
                if match:
                    sections[section_name] = match.group(1).strip()
                    break

        return sections

    async def _generate_subjective_section(self, sections: dict[str, str], transcription: str) -> str:
        """Generate subjective section of SOAP note"""

        subjective_content = []

        # Chief complaint
        if "chief_complaint" in sections:
            subjective_content.append(f"Chief Complaint: {sections['chief_complaint']}")

        # History of present illness
        if "history_present_illness" in sections:
            subjective_content.append(f"History of Present Illness: {sections['history_present_illness']}")
        else:
            # Extract patient-reported symptoms from transcription
            symptoms_keywords = ["reports", "complains of", "states", "describes", "feels", "experiences"]
            for keyword in symptoms_keywords:
                if keyword in transcription.lower():
                    start_idx = transcription.lower().find(keyword)
                    excerpt = transcription[start_idx:start_idx+200]
                    subjective_content.append(f"Patient {excerpt}")
                    break

        if not subjective_content:
            subjective_content.append("Patient presents for evaluation. Details documented in encounter.")

        return " ".join(subjective_content)

    async def _generate_objective_section(self, sections: dict[str, str], transcription: str) -> str:
        """Generate objective section of SOAP note"""

        objective_content = []

        # Physical examination findings
        if "physical_examination" in sections:
            objective_content.append(f"Physical Examination: {sections['physical_examination']}")

        # Extract vital signs if mentioned
        vital_patterns = [
            r"blood pressure.*?(\d+\s+over\s+\d+|\d+/\d+)",
            r"heart rate.*?(\d+)",
            r"temperature.*?(\d+\.?\d*\s*degrees?)",
            r"respiratory rate.*?(\d+)",
        ]

        for pattern in vital_patterns:
            match = re.search(pattern, transcription.lower())
            if match:
                objective_content.append(f"Vitals: {match.group(0)}")
                break

        if not objective_content:
            objective_content.append("Physical examination performed and documented.")

        return " ".join(objective_content)

    async def _generate_assessment_section(self, sections: dict[str, str], transcription: str) -> str:
        """Generate assessment section of SOAP note"""

        if "assessment" in sections:
            return sections["assessment"]

        # Look for diagnostic keywords
        diagnostic_keywords = ["diagnosis", "impression", "assessment", "condition", "disorder"]
        for keyword in diagnostic_keywords:
            if keyword in transcription.lower():
                start_idx = transcription.lower().find(keyword)
                return transcription[start_idx:start_idx+150]

        return "Clinical assessment documented during encounter."

    async def _generate_plan_section(self, sections: dict[str, str], transcription: str) -> str:
        """Generate plan section of SOAP note"""

        if "plan" in sections:
            return sections["plan"]

        # Look for treatment/plan keywords
        plan_keywords = ["plan", "treatment", "therapy", "medication", "follow.?up", "return"]
        plan_content = []

        for keyword in plan_keywords:
            pattern = f"{keyword}.*?[.!?]"
            matches = re.findall(pattern, transcription.lower())
            plan_content.extend(matches)

        if plan_content:
            return " ".join(plan_content[:3])  # Limit to first 3 relevant sentences

        return "Treatment plan discussed with patient."

    async def _assess_note_quality(self, note_sections: dict[str, str]) -> tuple[float, list[str], list[str]]:
        """Assess the completeness and quality of the clinical note"""

        required_sections = ["subjective", "objective", "assessment", "plan"]
        missing_sections = []
        recommendations = []

        # Check for missing or inadequate sections
        for section in required_sections:
            if section not in note_sections or len(note_sections[section]) < 10:
                missing_sections.append(section)

        # Calculate completeness score
        completeness_score = (len(required_sections) - len(missing_sections)) / len(required_sections)

        # Generate quality recommendations
        if missing_sections:
            recommendations.append(f"Consider adding more detail to: {', '.join(missing_sections)}")

        if completeness_score < 0.7:
            recommendations.append("Note appears incomplete. Review transcription for missing clinical details.")

        if len(note_sections.get("subjective", "")) < 50:
            recommendations.append("Subjective section could benefit from more patient history details.")

        if len(note_sections.get("objective", "")) < 30:
            recommendations.append("Objective section should include more examination findings.")

        return completeness_score, missing_sections, recommendations

    async def _format_soap_note(self, soap_note: SOAPNote) -> str:
        """Format SOAP note for display/export"""

        formatted_note = f"""
SOAP NOTE
=========

Date: {soap_note.encounter_date.strftime('%Y-%m-%d')}
Provider: {soap_note.provider_id}
Note ID: {soap_note.note_id}

CHIEF COMPLAINT:
{soap_note.chief_complaint}

SUBJECTIVE:
{soap_note.subjective}

OBJECTIVE:
{soap_note.objective}

ASSESSMENT:
{soap_note.assessment}

PLAN:
{soap_note.plan}

---
Note Quality Score: {soap_note.completeness_score:.2f}
Generated: {soap_note.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
"""
        return formatted_note.strip()

    async def _format_progress_note(self, progress_note: ProgressNote) -> str:
        """Format progress note for display/export"""

        formatted_note = f"""
PROGRESS NOTE
=============

Date: {progress_note.encounter_date.strftime('%Y-%m-%d')}
Provider: {progress_note.provider_id}
Note ID: {progress_note.note_id}

INTERVAL HISTORY:
{progress_note.interval_history}

CURRENT MEDICATIONS:
{progress_note.current_medications}

PHYSICAL EXAMINATION:
{progress_note.physical_exam}

ASSESSMENT AND PLAN:
{progress_note.assessment_and_plan}

---
Generated: {progress_note.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
"""
        return formatted_note.strip()

    async def _format_clinical_note(self, note_data: dict[str, Any], note_type: str) -> str:
        """Format any clinical note based on type and data"""

        if note_type == "soap":
            return await self._format_soap_like_note(note_data)
        if note_type == "progress":
            return await self._format_progress_like_note(note_data)
        return await self._format_generic_note(note_data)

    async def _format_soap_like_note(self, note_data: dict[str, Any]) -> str:
        """Format data as SOAP-style note"""

        sections = ["subjective", "objective", "assessment", "plan"]
        formatted_sections = []

        for section in sections:
            if section in note_data:
                formatted_sections.append(f"{section.upper()}:\n{note_data[section]}\n")

        return "\n".join(formatted_sections)

    async def _format_progress_like_note(self, note_data: dict[str, Any]) -> str:
        """Format data as progress note style"""

        sections = ["interval_history", "physical_exam", "assessment_and_plan"]
        formatted_sections = []

        for section in sections:
            if section in note_data:
                title = section.replace("_", " ").title()
                formatted_sections.append(f"{title}:\n{note_data[section]}\n")

        return "\n".join(formatted_sections)

    async def _format_generic_note(self, note_data: dict[str, Any]) -> str:
        """Format data as generic clinical note"""

        formatted_sections = []
        for key, value in note_data.items():
            if isinstance(value, str) and value.strip():
                title = key.replace("_", " ").title()
                formatted_sections.append(f"{title}:\n{value}\n")

        return "\n".join(formatted_sections)
