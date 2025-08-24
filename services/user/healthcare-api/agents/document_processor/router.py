"""
Document Processor API Router
Handles medical document formatting, organization, and administrative processing
"""

import builtins
import contextlib
import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from agents.document_processor.document_processor import HealthcareDocumentProcessor
from agents.document_processor.enhanced_document_processor import EnhancedDocumentProcessor
from core.dependencies import get_llm_client, get_mcp_client

logger = logging.getLogger(__name__)

router = APIRouter()


class DocumentProcessingRequest(BaseModel):
    """Document processing request model with healthcare compliance"""

    document_type: str = Field(
        default="soap_note",
        description="Type of document: soap_note, medical_form, patient_summary, clinical_note",
    )
    document_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Document data for processing",
    )
    session_id: str = Field(default="default", description="Session identifier")

    class Config:
        json_schema_extra = {
            "example": {
                "document_type": "soap_note",
                "document_data": {
                    "content": "Subjective: Patient reports headache\nObjective: BP 120/80\nAssessment: Tension headache\nPlan: Rest and hydration",
                    "patient_id": "PAT_001",
                    "provider_id": "PROV_001",
                },
                "session_id": "doc_session_001",
            },
        }


class SOAPNoteRequest(BaseModel):
    """SOAP note processing request model"""

    content: str = Field(..., description="Raw SOAP note content")
    patient_id: str = Field(..., description="Patient identifier")
    provider_id: str = Field(..., description="Provider identifier")

    class Config:
        json_schema_extra = {
            "example": {
                "content": "Subjective: Patient presents with chest pain\nObjective: HR 72, BP 120/80, no distress\nAssessment: Atypical chest pain\nPlan: EKG, follow up in 1 week",
                "patient_id": "PAT_001",
                "provider_id": "PROV_001",
            },
        }


class MedicalFormRequest(BaseModel):
    """Medical form processing request model"""

    form_type: str = Field(default="intake", description="Type of medical form")
    form_data: dict[str, Any] = Field(..., description="Form data to be processed")
    patient_id: str = Field(..., description="Patient identifier")

    class Config:
        json_schema_extra = {
            "example": {
                "form_type": "intake",
                "form_data": {
                    "patient_name": "John Doe",
                    "date_of_birth": "1980-01-15",
                    "contact_information": "555-123-4567",
                    "insurance_information": "Blue Cross",
                    "emergency_contact": "Jane Doe - 555-987-6543",
                },
                "patient_id": "PAT_001",
            },
        }


class PatientSummaryRequest(BaseModel):
    """Patient summary processing request model"""

    summary_type: str = Field(default="encounter", description="Type of patient summary")
    patient_data: dict[str, Any] = Field(..., description="Patient data for summary")

    class Config:
        json_schema_extra = {
            "example": {
                "summary_type": "encounter",
                "patient_data": {
                    "patient_id": "PAT_001",
                    "patient_demographics": {"name": "John Doe", "age": 44},
                    "chief_complaint": "Chest pain",
                    "encounter_details": {"date": "2024-08-03", "duration": "30 min"},
                },
            },
        }


@router.post("/process")
async def process_document(
    request: DocumentProcessingRequest,
    mcp_client: Any = Depends(get_mcp_client),
    llm_client: Any = Depends(get_llm_client),
) -> dict[str, Any]:
    """
    Process healthcare document with administrative formatting

    MEDICAL DISCLAIMER: This provides document formatting only,
    not medical interpretation or clinical advice.
    """
    try:
        # Initialize document processor
        processor = HealthcareDocumentProcessor(
            mcp_client=mcp_client,
            llm_client=llm_client,
        )

        # Process document
        return await processor._process_implementation(request.model_dump())

    except Exception as e:
        logger.exception(f"Document processing error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Document processing failed: {str(e)}",
        )


@router.post("/soap-note")
async def process_soap_note(
    request: SOAPNoteRequest,
    mcp_client: Any = Depends(get_mcp_client),
    llm_client: Any = Depends(get_llm_client),
) -> dict[str, Any]:
    """
    Process SOAP note with administrative formatting

    Document formatting only - not medical interpretation.
    """
    try:
        processing_request = {
            "document_type": "soap_note",
            "document_data": {
                "content": request.content,
                "patient_id": request.patient_id,
                "provider_id": request.provider_id,
            },
            "session_id": "soap_processing",
        }

        processor = HealthcareDocumentProcessor(mcp_client=mcp_client, llm_client=llm_client)
        return await processor._process_implementation(processing_request)

    except Exception as e:
        logger.exception(f"SOAP note processing error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"SOAP note processing failed: {str(e)}",
        )


@router.post("/medical-form")
async def process_medical_form(
    request: MedicalFormRequest,
    mcp_client: Any = Depends(get_mcp_client),
    llm_client: Any = Depends(get_llm_client),
) -> dict[str, Any]:
    """
    Process medical form with administrative validation

    Document formatting only - not medical interpretation.
    """
    try:
        processing_request = {
            "document_type": "medical_form",
            "document_data": {
                "form_type": request.form_type,
                "form_data": request.form_data,
                "patient_id": request.patient_id,
            },
            "session_id": "form_processing",
        }

        processor = HealthcareDocumentProcessor(mcp_client=mcp_client, llm_client=llm_client)
        return await processor._process_implementation(processing_request)

    except Exception as e:
        logger.exception(f"Medical form processing error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Medical form processing failed: {str(e)}",
        )


@router.post("/patient-summary")
async def process_patient_summary(
    request: PatientSummaryRequest,
    mcp_client: Any = Depends(get_mcp_client),
    llm_client: Any = Depends(get_llm_client),
) -> dict[str, Any]:
    """
    Process patient summary with administrative organization

    Document formatting only - not medical interpretation.
    """
    try:
        processing_request = {
            "document_type": "patient_summary",
            "document_data": {
                "summary_type": request.summary_type,
                "patient_data": request.patient_data,
            },
            "session_id": "summary_processing",
        }

        processor = HealthcareDocumentProcessor(mcp_client=mcp_client, llm_client=llm_client)
        return await processor._process_implementation(processing_request)

    except Exception as e:
        logger.exception(f"Patient summary processing error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Patient summary processing failed: {str(e)}",
        )


@router.post("/clinical-note")
async def process_clinical_note(
    content: str,
    note_type: str = "progress",
    provider_id: str = "",
    mcp_client: Any = Depends(get_mcp_client),
    llm_client: Any = Depends(get_llm_client),
) -> dict[str, Any]:
    """
    Process clinical note with administrative formatting

    Document formatting only - not medical interpretation.
    """
    try:
        processing_request = {
            "document_type": "clinical_note",
            "document_data": {
                "content": content,
                "note_type": note_type,
                "provider_id": provider_id,
            },
            "session_id": "clinical_note_processing",
        }

        processor = HealthcareDocumentProcessor(mcp_client=mcp_client, llm_client=llm_client)
        return await processor._process_implementation(processing_request)

    except Exception as e:
        logger.exception(f"Clinical note processing error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Clinical note processing failed: {str(e)}",
        )


@router.get("/validate-document")
async def validate_document_completeness(
    document_type: str,
    mcp_client: Any = Depends(get_mcp_client),
    llm_client: Any = Depends(get_llm_client),
) -> dict[str, Any]:
    """
    Get document validation requirements for specific document type

    Administrative support only - not medical interpretation.
    """
    try:
        validation_requirements = {
            "soap_note": {
                "required_sections": ["subjective", "objective", "assessment", "plan"],
                "required_fields": ["patient_id", "provider_id", "content"],
                "validation_rules": [
                    "All SOAP sections must have content",
                    "Patient and provider IDs are required",
                    "Content must be properly structured",
                ],
            },
            "medical_form": {
                "required_sections": ["patient_demographics", "form_content"],
                "required_fields": ["patient_name", "date", "form_data"],
                "validation_rules": [
                    "All required fields must be completed",
                    "Patient identification required",
                    "Form must match specified template",
                ],
            },
            "patient_summary": {
                "required_sections": ["demographics", "encounter_details"],
                "required_fields": ["patient_id", "summary_data"],
                "validation_rules": [
                    "Patient demographics required",
                    "Encounter information must be present",
                    "Summary type must be specified",
                ],
            },
            "clinical_note": {
                "required_sections": ["note_content"],
                "required_fields": ["content", "provider_id", "note_type"],
                "validation_rules": [
                    "Note content cannot be empty",
                    "Provider identification required",
                    "Note type must be specified",
                ],
            },
        }

        requirements = validation_requirements.get(
            document_type,
            validation_requirements["clinical_note"],
        )

        return {
            "document_type": document_type,
            "validation_requirements": requirements,
            "disclaimer": "These are administrative requirements only, not medical validation",
            "status": "requirements_provided",
        }

    except Exception as e:
        logger.exception(f"Document validation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Document validation failed: {str(e)}",
        )


# Enhanced Document Processing Endpoints

class EnhancedDocumentRequest(BaseModel):
    """Enhanced document processing request model"""

    operation: str = Field(default="process_document", description="Operation type: process_document, analyze_phi, extract_entities, search_documents")
    file_path: str | None = Field(default=None, description="Path to document file")
    document_content: str | None = Field(default=None, description="Direct document content")
    content: str | None = Field(default=None, description="Text content for analysis")
    entity_types: list[str] | None = Field(default=None, description="Specific entity types to extract")
    query: str | None = Field(default=None, description="Search query")
    filters: dict | None = Field(default_factory=dict, description="Search filters")
    options: dict = Field(default_factory=dict, description="Processing options")
    session_id: str = Field(default="enhanced_processing", description="Session identifier")

    class Config:
        json_schema_extra = {
            "example": {
                "operation": "process_document",
                "file_path": "/path/to/medical_record.pdf",
                "options": {
                    "store_document": True,
                    "context": {"patient_id": "PAT_001"},
                },
                "session_id": "enhanced_session_001",
            },
        }


class BatchProcessingRequest(BaseModel):
    """Batch document processing request model"""

    file_paths: list[str] = Field(..., description="List of document file paths")
    options: dict = Field(default_factory=dict, description="Processing options")
    session_id: str = Field(default="batch_processing", description="Session identifier")

    class Config:
        json_schema_extra = {
            "example": {
                "file_paths": [
                    "/path/to/document1.pdf",
                    "/path/to/document2.docx",
                    "/path/to/document3.txt",
                ],
                "options": {
                    "store_document": True,
                    "extract_entities": True,
                },
                "session_id": "batch_001",
            },
        }


@router.post("/enhanced/process")
async def enhanced_document_process(
    request: EnhancedDocumentRequest,
    mcp_client: Any = Depends(get_mcp_client),
    llm_client: Any = Depends(get_llm_client),
) -> dict[str, Any]:
    """
    Enhanced document processing with PHI detection, entity extraction, and storage

    MEDICAL DISCLAIMER: This provides document processing and entity extraction
    for administrative purposes only, not medical interpretation or clinical advice.
    """
    try:
        # Initialize enhanced document processor
        processor = EnhancedDocumentProcessor(
            mcp_client=mcp_client,
            llm_client=llm_client,
        )
        await processor.initialize()

        # Process document with enhanced capabilities
        return await processor._process_implementation(request.model_dump())

    except Exception as e:
        logger.exception(f"Enhanced document processing error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Enhanced document processing failed: {str(e)}",
        )


@router.post("/enhanced/upload")
async def upload_and_process_document(
    file: UploadFile = File(...),
    store_document: bool = Form(True),
    extract_entities: bool = Form(True),
    analyze_phi: bool = Form(True),
    mcp_client: Any = Depends(get_mcp_client),
    llm_client: Any = Depends(get_llm_client),
) -> dict[str, Any]:
    """
    Upload and process document with enhanced capabilities

    MEDICAL DISCLAIMER: Document processing for administrative purposes only.
    """
    import tempfile
    from pathlib import Path

    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        # Initialize processor
        processor = EnhancedDocumentProcessor(
            mcp_client=mcp_client,
            llm_client=llm_client,
        )
        await processor.initialize()

        # Process uploaded document
        request_data = {
            "operation": "process_document",
            "file_path": temp_file_path,
            "options": {
                "store_document": store_document,
                "extract_entities": extract_entities,
                "analyze_phi": analyze_phi,
                "context": {
                    "original_filename": file.filename,
                    "upload_timestamp": str(datetime.now()),
                },
            },
            "session_id": f"upload_{file.filename}_{int(datetime.now().timestamp())}",
        }

        result = await processor._process_implementation(request_data)

        # Clean up temporary file
        Path(temp_file_path).unlink(missing_ok=True)

        return result

    except Exception as e:
        logger.exception(f"Document upload processing error: {e}")
        # Clean up on error
        with contextlib.suppress(builtins.BaseException):
            Path(temp_file_path).unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail=f"Document upload processing failed: {str(e)}",
        )


@router.post("/enhanced/batch")
async def batch_process_documents(
    request: BatchProcessingRequest,
    mcp_client: Any = Depends(get_mcp_client),
    llm_client: Any = Depends(get_llm_client),
) -> dict[str, Any]:
    """
    Batch process multiple documents

    MEDICAL DISCLAIMER: Document processing for administrative purposes only.
    """
    try:
        processor = EnhancedDocumentProcessor(
            mcp_client=mcp_client,
            llm_client=llm_client,
        )
        await processor.initialize()

        batch_request = {
            "operation": "batch_process",
            "file_paths": request.file_paths,
            "options": request.options,
            "session_id": request.session_id,
        }

        return await processor._process_implementation(batch_request)

    except Exception as e:
        logger.exception(f"Batch document processing error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Batch document processing failed: {str(e)}",
        )


@router.post("/enhanced/analyze-phi")
async def analyze_phi_in_content(
    request: EnhancedDocumentRequest,
    mcp_client: Any = Depends(get_mcp_client),
    llm_client: Any = Depends(get_llm_client),
) -> dict[str, Any]:
    """
    Analyze content for PHI detection and classification

    MEDICAL DISCLAIMER: PHI detection for administrative compliance support only.
    """
    try:
        if not request.content:
            raise HTTPException(status_code=400, detail="Content field is required for PHI analysis")

        processor = EnhancedDocumentProcessor(
            mcp_client=mcp_client,
            llm_client=llm_client,
        )
        await processor.initialize()

        phi_request = {
            "operation": "analyze_phi",
            "content": request.content,
            "session_id": request.session_id,
        }

        return await processor._process_implementation(phi_request)

    except Exception as e:
        logger.exception(f"PHI analysis error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"PHI analysis failed: {str(e)}",
        )


@router.post("/enhanced/extract-entities")
async def extract_medical_entities(
    request: EnhancedDocumentRequest,
    mcp_client: Any = Depends(get_mcp_client),
    llm_client: Any = Depends(get_llm_client),
) -> dict[str, Any]:
    """
    Extract medical entities from content using SciSpacy

    MEDICAL DISCLAIMER: Entity extraction for administrative organization only.
    """
    try:
        if not request.content:
            raise HTTPException(status_code=400, detail="Content field is required for entity extraction")

        processor = EnhancedDocumentProcessor(
            mcp_client=mcp_client,
            llm_client=llm_client,
        )
        await processor.initialize()

        entity_request = {
            "operation": "extract_entities",
            "content": request.content,
            "entity_types": request.entity_types,
            "session_id": request.session_id,
        }

        return await processor._process_implementation(entity_request)

    except Exception as e:
        logger.exception(f"Entity extraction error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Entity extraction failed: {str(e)}",
        )


@router.post("/enhanced/search")
async def search_documents(
    request: EnhancedDocumentRequest,
    mcp_client: Any = Depends(get_mcp_client),
    llm_client: Any = Depends(get_llm_client),
) -> dict[str, Any]:
    """
    Search stored documents using full-text search

    MEDICAL DISCLAIMER: Document search for administrative purposes only.
    """
    try:
        if not request.query:
            raise HTTPException(status_code=400, detail="Query field is required for document search")

        processor = EnhancedDocumentProcessor(
            mcp_client=mcp_client,
            llm_client=llm_client,
        )
        await processor.initialize()

        search_request = {
            "operation": "search_documents",
            "query": request.query,
            "filters": request.filters,
            "session_id": request.session_id,
        }

        return await processor._process_implementation(search_request)

    except Exception as e:
        logger.exception(f"Document search error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Document search failed: {str(e)}",
        )


@router.get("/enhanced/stats")
async def get_processing_statistics(
    mcp_client: Any = Depends(get_mcp_client),
    llm_client: Any = Depends(get_llm_client),
) -> dict[str, Any]:
    """
    Get document processing statistics and service health

    Administrative metrics and service status information.
    """
    try:
        processor = EnhancedDocumentProcessor(
            mcp_client=mcp_client,
            llm_client=llm_client,
        )
        await processor.initialize()

        return await processor.get_processing_statistics()

    except Exception as e:
        logger.exception(f"Statistics retrieval error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Statistics retrieval failed: {str(e)}",
        )


@router.get("/health")
async def document_processor_health_check() -> dict[str, Any]:
    """Health check for document processor services"""
    from datetime import datetime
    return {
        "status": "healthy",
        "service": "document_processor",
        "capabilities": [
            # Traditional capabilities
            "soap_note_formatting",
            "medical_form_processing",
            "patient_summary_generation",
            "clinical_note_formatting",
            "document_validation",
            # Enhanced capabilities
            "pdf_document_parsing",
            "docx_document_parsing",
            "image_ocr_processing",
            "phi_detection_and_redaction",
            "medical_entity_extraction",
            "full_text_search",
            "batch_processing",
            "document_storage",
        ],
        "integrations": [
            "scispacy_nlp_service",
            "phi_detection_system",
            "postgresql_storage",
            "http_client_infrastructure",
        ],
        "disclaimer": "Document processing for administrative purposes only - not medical interpretation",
        "timestamp": datetime.now().isoformat(),
    }
