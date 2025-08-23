"""
Healthcare Document Processor Agent - Administrative Document Support Only
Handles medical document formatting, organization, and administrative processing
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from agents import BaseHealthcareAgent
from core.infrastructure.healthcare_logger import (
    get_healthcare_logger,
    log_healthcare_event,
)
from core.infrastructure.agent_logging_utils import (
    AgentWorkflowLogger,
    enhanced_agent_method,
)

logger = get_healthcare_logger("agent.document_processor")


@dataclass
class DocumentProcessingResult:
    """Result from document processing with healthcare compliance"""

    processing_id: str
    document_type: str
    status: str
    processed_document: dict[str, Any] | None
    validation_results: list[str]
    formatting_applied: list[str]
    administrative_notes: list[str]
    missing_sections: list[str]
    disclaimers: list[str]
    generated_at: datetime


class HealthcareDocumentProcessor(BaseHealthcareAgent):
    """
    Healthcare Document Processor for administrative support

    MEDICAL DISCLAIMER: This agent provides administrative document processing and formatting
    support only. It assists healthcare professionals with document organization, SOAP note
    structuring, and administrative completeness checks. It does not provide medical
    interpretation, diagnosis, or treatment recommendations. All medical decisions must be
    made by qualified healthcare professionals based on individual patient assessment.
    """

    def __init__(
        self,
        mcp_client: Any,
        llm_client: Any,
        config_override: dict[str, Any] | None = None,
    ) -> None:
        super().__init__("document_processor", "document_processor")

        self.mcp_client = mcp_client
        self.llm_client = llm_client
        self.config = config_override or {}

        # Log agent initialization with healthcare context
        log_healthcare_event(
            logger,
            logging.INFO,
            "Healthcare Document Processor Agent initialized",
            context={
                "agent": "document_processor",
                "initialization": True,
                "phi_monitoring": True,
                "medical_interpretation_disabled": True,
                "database_required": True,
            },
            operation_type="agent_initialization",
        )

        # Standard healthcare disclaimers
        self.disclaimers = [
            "This system provides document formatting support only, not medical interpretation.",
            "Document content should be reviewed by qualified healthcare professionals.",
            "All medical decisions must be made by licensed healthcare providers.",
            "In case of emergency, contact emergency services immediately.",
            "All document processing complies with HIPAA regulations.",
            "Database connectivity required for healthcare operations.",
        ]

    async def initialize(self) -> None:
        """Initialize document processor agent with database connectivity validation"""
        try:
            # Call parent initialization which validates database connectivity
            await self.initialize_agent()

            log_healthcare_event(
                logger,
                logging.INFO,
                "Document Processor Agent fully initialized with database connectivity",
                context={
                    "agent": "document_processor",
                    "database_validated": True,
                    "ready_for_operations": True,
                },
                operation_type="agent_ready",
            )
        except Exception as e:
            log_healthcare_event(
                logger,
                logging.CRITICAL,
                f"Document Processor Agent initialization failed: {e}",
                context={
                    "agent": "document_processor",
                    "initialization_failed": True,
                    "error": str(e),
                },
                operation_type="agent_initialization_error",
            )
            raise

    @enhanced_agent_method(operation_type="document_processing", phi_risk_level="high", track_performance=True)
    async def _process_implementation(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Process document formatting request

        MEDICAL DISCLAIMER: Document formatting only - not medical interpretation.
        """
        session_id = request.get("session_id", "default")
        
        # Initialize workflow logger for document processing pipeline
        workflow_logger = self.get_workflow_logger()
        workflow_logger.start_workflow("document_processing", {
            "session_id": session_id,
            "document_type": request.get("document_type", "soap_note"),
            "has_document_data": "document_data" in request,
        })

        try:
            workflow_logger.log_step("extract_request_parameters")
            document_type = request.get("document_type", "soap_note")
            document_data = request.get("document_data", {})

            workflow_logger.log_step("route_document_processing", {
                "document_type": document_type,
                "data_keys": list(document_data.keys())
            })

            if document_type == "soap_note":
                workflow_logger.log_step("processing_soap_note")
                result = await self._process_soap_note(document_data, session_id)
            elif document_type == "medical_form":
                workflow_logger.log_step("processing_medical_form")
                result = await self._process_medical_form(document_data, session_id)
            elif document_type == "patient_summary":
                workflow_logger.log_step("processing_patient_summary")
                result = await self._process_patient_summary(document_data, session_id)
            elif document_type == "clinical_note":
                workflow_logger.log_step("processing_clinical_note")
                result = await self._process_clinical_note(document_data, session_id)
            else:
                workflow_logger.log_step("processing_general_document")
                result = await self._process_general_document(document_data, session_id)

            workflow_logger.log_step("format_response", {
                "processing_status": result.status if result else "no_result"
            })
            
            response = self._format_processing_response(result, session_id)
            
            workflow_logger.finish_workflow("completed", {
                "final_status": result.status if result else "unknown",
                "processing_id": result.processing_id if result else None,
                "validation_errors_count": len(result.validation_results) if result else 0,
            })
            
            return response

        except Exception as e:
            workflow_logger.finish_workflow("failed", error=e)
            logger.exception(f"Document processing error: {e}")
            return self._create_error_response(f"Document processing failed: {str(e)}", session_id)
        finally:
            # Critical: Clean up MCP connection to prevent runaway tasks
            try:
                if hasattr(self.mcp_client, "disconnect"):
                    await self.mcp_client.disconnect()
                    logger.debug("MCP client disconnected after document processing")
            except Exception as cleanup_error:
                logger.warning(f"Error during MCP cleanup: {cleanup_error}")

    async def _process_soap_note(
        self,
        document_data: dict[str, Any],
        session_id: str,
    ) -> DocumentProcessingResult:
        """
        Process SOAP note formatting with administrative structure validation
        """
        processing_id = self._generate_processing_id("soap")
        validation_results = []
        formatting_applied = []
        administrative_notes = []

        # Extract SOAP sections from raw data
        raw_content = document_data.get("content", "")
        provider_id = document_data.get("provider_id", "")
        patient_id = document_data.get("patient_id", "")

        # Structure SOAP note sections
        soap_sections = await self._extract_soap_sections(raw_content)

        # Validate SOAP completeness (administrative check only)
        required_sections = ["subjective", "objective", "assessment", "plan"]
        missing_sections = []

        for section in required_sections:
            if not soap_sections.get(section) or not soap_sections[section].strip():
                missing_sections.append(section)
                validation_results.append(f"Missing or empty {section.title()} section")

        # Apply SOAP formatting
        if not missing_sections:
            formatted_soap = self._format_soap_structure(soap_sections)
            formatting_applied = [
                "Applied standard SOAP note structure",
                "Formatted section headers and content",
                "Applied healthcare documentation standards",
            ]
            administrative_notes.append("SOAP note formatted successfully")
        else:
            formatted_soap = None
            administrative_notes.append("SOAP note incomplete - missing required sections")

        # Add metadata for administrative tracking
        processed_document = None
        if formatted_soap:
            processed_document = {
                "document_type": "soap_note",
                "patient_id": patient_id,
                "provider_id": provider_id,
                "content": formatted_soap,
                "created_at": datetime.utcnow().isoformat(),
                "version": "1.0",
                "administrative_metadata": {
                    "processing_id": processing_id,
                    "validation_status": "complete" if not missing_sections else "incomplete",
                    "sections_present": list(soap_sections.keys()),
                },
            }

        return DocumentProcessingResult(
            processing_id=processing_id,
            document_type="soap_note",
            status="completed" if not missing_sections else "incomplete",
            processed_document=processed_document,
            validation_results=validation_results,
            formatting_applied=formatting_applied,
            administrative_notes=administrative_notes,
            missing_sections=missing_sections,
            disclaimers=self.disclaimers,
            generated_at=datetime.utcnow(),
        )

    async def _process_medical_form(
        self,
        document_data: dict[str, Any],
        session_id: str,
    ) -> DocumentProcessingResult:
        """
        Process medical form formatting with administrative validation
        """
        processing_id = self._generate_processing_id("form")
        validation_results = []
        formatting_applied = []
        administrative_notes = []

        form_type = document_data.get("form_type", "general")
        form_data = document_data.get("form_data", {})
        patient_id = document_data.get("patient_id", "")

        # Get form template and required fields
        form_template = self._get_form_template(form_type)
        required_fields = form_template.get("required_fields", [])

        # Validate form completeness
        missing_sections = []
        for field in required_fields:
            if not form_data.get(field):
                missing_sections.append(field)
                validation_results.append(f"Missing required field: {field}")

        # Format form according to template
        if not missing_sections:
            processed_form = self._format_medical_form(form_data, form_template)
            formatting_applied = [
                f"Applied {form_type} form template",
                "Formatted required fields and sections",
                "Applied healthcare form standards",
            ]
            administrative_notes.append("Medical form formatted successfully")
        else:
            processed_form = None
            administrative_notes.append("Medical form incomplete - missing required fields")

        processed_document = None
        if processed_form:
            processed_document = {
                "document_type": "medical_form",
                "form_type": form_type,
                "patient_id": patient_id,
                "content": processed_form,
                "created_at": datetime.utcnow().isoformat(),
                "version": "1.0",
                "administrative_metadata": {
                    "processing_id": processing_id,
                    "validation_status": "complete" if not missing_sections else "incomplete",
                    "form_template": form_type,
                },
            }

        return DocumentProcessingResult(
            processing_id=processing_id,
            document_type="medical_form",
            status="completed" if not missing_sections else "incomplete",
            processed_document=processed_document,
            validation_results=validation_results,
            formatting_applied=formatting_applied,
            administrative_notes=administrative_notes,
            missing_sections=missing_sections,
            disclaimers=self.disclaimers,
            generated_at=datetime.utcnow(),
        )

    async def _process_patient_summary(
        self,
        document_data: dict[str, Any],
        session_id: str,
    ) -> DocumentProcessingResult:
        """
        Process patient summary formatting with administrative organization
        """
        processing_id = self._generate_processing_id("summary")
        validation_results = []
        formatting_applied = []
        administrative_notes = []

        patient_data = document_data.get("patient_data", {})
        summary_type = document_data.get("summary_type", "encounter")

        # Validate summary data
        required_sections = ["patient_demographics", "chief_complaint", "encounter_details"]
        missing_sections = []

        for section in required_sections:
            if not patient_data.get(section):
                missing_sections.append(section)
                validation_results.append(f"Missing summary section: {section}")

        # Format patient summary
        if not missing_sections:
            formatted_summary = self._format_patient_summary(patient_data, summary_type)
            formatting_applied = [
                "Applied patient summary template",
                "Organized sections by healthcare standards",
                "Applied administrative formatting rules",
            ]
            administrative_notes.append("Patient summary formatted successfully")
        else:
            formatted_summary = None
            administrative_notes.append("Patient summary incomplete - missing required sections")

        processed_document = None
        if formatted_summary:
            processed_document = {
                "document_type": "patient_summary",
                "summary_type": summary_type,
                "patient_id": patient_data.get("patient_id", ""),
                "content": formatted_summary,
                "created_at": datetime.utcnow().isoformat(),
                "version": "1.0",
                "administrative_metadata": {
                    "processing_id": processing_id,
                    "validation_status": "complete" if not missing_sections else "incomplete",
                    "summary_template": summary_type,
                },
            }

        return DocumentProcessingResult(
            processing_id=processing_id,
            document_type="patient_summary",
            status="completed" if not missing_sections else "incomplete",
            processed_document=processed_document,
            validation_results=validation_results,
            formatting_applied=formatting_applied,
            administrative_notes=administrative_notes,
            missing_sections=missing_sections,
            disclaimers=self.disclaimers,
            generated_at=datetime.utcnow(),
        )

    async def _process_clinical_note(
        self,
        document_data: dict[str, Any],
        session_id: str,
    ) -> DocumentProcessingResult:
        """
        Process clinical note formatting with administrative structure
        """
        processing_id = self._generate_processing_id("clinical")
        validation_results = []
        formatting_applied = []
        administrative_notes = []

        note_content = document_data.get("content", "")
        note_type = document_data.get("note_type", "progress")
        provider_id = document_data.get("provider_id", "")

        # Validate note content
        missing_sections = []
        if not note_content.strip():
            missing_sections.append("note_content")
            validation_results.append("Clinical note content is empty")

        if not provider_id:
            missing_sections.append("provider_id")
            validation_results.append("Provider ID is required")

        # Format clinical note
        if not missing_sections:
            formatted_note = self._format_clinical_note(note_content, note_type)
            formatting_applied = [
                f"Applied {note_type} note format",
                "Structured note content",
                "Applied clinical documentation standards",
            ]
            administrative_notes.append("Clinical note formatted successfully")
        else:
            formatted_note = None
            administrative_notes.append("Clinical note incomplete - missing required information")

        processed_document = None
        if formatted_note:
            processed_document = {
                "document_type": "clinical_note",
                "note_type": note_type,
                "provider_id": provider_id,
                "content": formatted_note,
                "created_at": datetime.utcnow().isoformat(),
                "version": "1.0",
                "administrative_metadata": {
                    "processing_id": processing_id,
                    "validation_status": "complete" if not missing_sections else "incomplete",
                    "note_template": note_type,
                },
            }

        return DocumentProcessingResult(
            processing_id=processing_id,
            document_type="clinical_note",
            status="completed" if not missing_sections else "incomplete",
            processed_document=processed_document,
            validation_results=validation_results,
            formatting_applied=formatting_applied,
            administrative_notes=administrative_notes,
            missing_sections=missing_sections,
            disclaimers=self.disclaimers,
            generated_at=datetime.utcnow(),
        )

    async def _process_general_document(
        self,
        document_data: dict[str, Any],
        session_id: str,
    ) -> DocumentProcessingResult:
        """
        Process general healthcare document with basic formatting
        """
        processing_id = self._generate_processing_id("general")

        return DocumentProcessingResult(
            processing_id=processing_id,
            document_type="general",
            status="basic_formatting",
            processed_document={
                "document_type": "general",
                "content": document_data.get("content", ""),
                "created_at": datetime.utcnow().isoformat(),
                "administrative_metadata": {"processing_id": processing_id},
            },
            validation_results=["Basic document formatting applied"],
            formatting_applied=["Standard healthcare document format"],
            administrative_notes=["General document processing completed"],
            missing_sections=[],
            disclaimers=self.disclaimers,
            generated_at=datetime.utcnow(),
        )

    async def _extract_soap_sections(self, content: str) -> dict[str, str]:
        """Extract SOAP sections from raw content (administrative parsing only)"""
        sections = {"subjective": "", "objective": "", "assessment": "", "plan": ""}

        # Simple keyword-based extraction (administrative tool only)
        lines = content.split("\n")
        current_section = None

        for line in lines:
            line_lower = line.lower().strip()

            if line_lower.startswith(("subjective", "s:")):
                current_section = "subjective"
            elif line_lower.startswith(("objective", "o:")):
                current_section = "objective"
            elif line_lower.startswith(("assessment", "a:")):
                current_section = "assessment"
            elif line_lower.startswith(("plan", "p:")):
                current_section = "plan"
            elif current_section and line.strip():
                sections[current_section] += line + "\n"

        return sections

    def _format_soap_structure(self, soap_sections: dict[str, str]) -> str:
        """Format SOAP sections with standard healthcare structure"""
        formatted_soap = ""

        for section_name, content in soap_sections.items():
            if content.strip():
                formatted_soap += f"\n{section_name.upper()}:\n{content.strip()}\n"

        return formatted_soap.strip()

    def _get_form_template(self, form_type: str) -> dict[str, Any]:
        """Get form template for specific form type"""
        templates = {
            "intake": {
                "required_fields": [
                    "patient_name",
                    "date_of_birth",
                    "contact_information",
                    "insurance_information",
                    "emergency_contact",
                ],
                "sections": ["demographics", "insurance", "emergency_contacts"],
            },
            "consent": {
                "required_fields": [
                    "patient_name",
                    "procedure_description",
                    "patient_signature",
                    "date",
                ],
                "sections": ["consent_details", "signatures"],
            },
            "general": {
                "required_fields": ["patient_name", "date"],
                "sections": ["content"],
            },
        }

        return templates.get(form_type, templates["general"])

    def _format_medical_form(
        self,
        form_data: dict[str, Any],
        template: dict[str, Any],
    ) -> dict[str, Any]:
        """Format medical form according to template"""
        formatted_form = {
            "header": {
                "form_type": template.get("form_type", "medical_form"),
                "created_at": datetime.utcnow().isoformat(),
            },
            "sections": {},
        }

        # Organize data by template sections
        for section in template.get("sections", []):
            formatted_form["sections"][section] = {}

        # Place form data into appropriate sections
        for field, value in form_data.items():
            # Administrative organization only
            formatted_form["sections"].setdefault("content", {})[field] = value

        return formatted_form

    def _format_patient_summary(
        self,
        patient_data: dict[str, Any],
        summary_type: str,
    ) -> dict[str, Any]:
        """Format patient summary with administrative organization"""
        return {
            "header": {
                "summary_type": summary_type,
                "patient_id": patient_data.get("patient_id", ""),
                "created_at": datetime.utcnow().isoformat(),
            },
            "demographics": patient_data.get("patient_demographics", {}),
            "encounter": {
                "chief_complaint": patient_data.get("chief_complaint", ""),
                "encounter_details": patient_data.get("encounter_details", {}),
            },
            "administrative_info": {
                "insurance": patient_data.get("insurance_info", {}),
                "contact": patient_data.get("contact_info", {}),
            },
        }

    def _format_clinical_note(self, content: str, note_type: str) -> dict[str, Any]:
        """Format clinical note with administrative structure"""
        return {
            "header": {
                "note_type": note_type,
                "created_at": datetime.utcnow().isoformat(),
            },
            "content": {
                "note_text": content,
                "structured_format": self._structure_note_content(content),
            },
            "metadata": {
                "character_count": len(content),
                "formatting_applied": "clinical_note_standard",
            },
        }

    def _structure_note_content(self, content: str) -> dict[str, Any]:
        """Structure note content into organized sections (administrative tool)"""
        # Basic content organization
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

        return {
            "main_content": content,
            "paragraph_count": len(paragraphs),
            "structured_sections": paragraphs[:5],  # First 5 paragraphs
        }

    def _generate_processing_id(self, doc_type: str) -> str:
        """Generate unique processing ID"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"DOC_{doc_type.upper()}_{timestamp}"

    def _format_processing_response(
        self,
        result: DocumentProcessingResult,
        session_id: str,
    ) -> dict[str, Any]:
        """Format processing result for API response"""
        return {
            "agent_type": "document_processor",
            "session_id": session_id,
            "processing_id": result.processing_id,
            "document_type": result.document_type,
            "status": result.status,
            "processed_document": result.processed_document,
            "validation_results": result.validation_results,
            "formatting_applied": result.formatting_applied,
            "administrative_notes": result.administrative_notes,
            "missing_sections": result.missing_sections,
            "disclaimers": result.disclaimers,
            "generated_at": result.generated_at.isoformat(),
            "success": result.status in ["completed", "basic_formatting"],
        }

    def _create_error_response(self, error_message: str, session_id: str) -> dict[str, Any]:
        """Create standardized error response"""
        return {
            "agent_type": "document_processor",
            "session_id": session_id,
            "error": error_message,
            "success": False,
            "disclaimers": self.disclaimers,
            "generated_at": datetime.utcnow().isoformat(),
        }
