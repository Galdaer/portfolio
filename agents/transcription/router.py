"""
FastAPI Router for Healthcare Transcription Agent
Provides REST API endpoints for medical transcription and clinical note generation
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status

from core.infrastructure.healthcare_logger import get_healthcare_logger, log_healthcare_event
from core.infrastructure.phi_monitor import phi_monitor_decorator as phi_monitor
from core.infrastructure.phi_monitor import scan_for_phi

from .transcription_agent import transcription_agent

logger = get_healthcare_logger("api.transcription")
router = APIRouter(prefix="/transcription", tags=["transcription"])


@router.post("/transcribe-audio")
@phi_monitor(risk_level="high", operation_type="api_audio_transcription")
async def transcribe_audio(audio_data: dict[str, Any]) -> dict[str, Any]:
    """
    Transcribe medical audio dictation

    Medical Disclaimer: Administrative transcription support only.
    Does not provide medical advice or clinical interpretation.
    """
    try:
        # Validate input for PHI exposure
        scan_for_phi(str(audio_data))

        log_healthcare_event(
            logger,
            logging.INFO,
            "Audio transcription request received",
            context={
                "endpoint": "/transcription/transcribe-audio",
                "encounter_type": audio_data.get("encounter_type"),
                "has_audio_file": "audio_file_path" in audio_data,
                "duration": audio_data.get("duration_seconds"),
            },
            operation_type="api_request",
        )

        result = await transcription_agent.transcribe_audio(audio_data)

        return {
            "success": True,
            "data": {
                "transcription_id": result.transcription_id,
                "status": result.status,
                "original_audio_duration": result.original_audio_duration,
                "transcribed_text": result.transcribed_text,
                "confidence_score": result.confidence_score,
                "medical_terms_identified": result.medical_terms_identified,
                "transcription_errors": result.transcription_errors,
                "compliance_validated": result.compliance_validated,
                "timestamp": result.timestamp.isoformat(),
                "metadata": result.metadata,
            },
        }

    except Exception as e:
        log_healthcare_event(
            logger,
            logging.ERROR,
            f"Audio transcription API error: {str(e)}",
            context={
                "endpoint": "/transcription/transcribe-audio",
                "error": str(e),
                "error_type": type(e).__name__,
            },
            operation_type="api_error",
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audio transcription failed: {str(e)}",
        )


@router.post("/generate-clinical-note")
@phi_monitor(risk_level="medium", operation_type="api_clinical_note_generation")
async def generate_clinical_note(note_request: dict[str, Any]) -> dict[str, Any]:
    """
    Generate structured clinical note from transcription or input data

    Medical Disclaimer: Administrative note formatting only.
    Does not provide medical advice or clinical decision-making.
    """
    try:
        # Validate input for PHI exposure
        scan_for_phi(str(note_request))

        log_healthcare_event(
            logger,
            logging.INFO,
            "Clinical note generation request received",
            context={
                "endpoint": "/transcription/generate-clinical-note",
                "note_type": note_request.get("note_type"),
                "has_content": "content" in note_request,
                "content_length": len(note_request.get("content", "")),
            },
            operation_type="api_request",
        )

        result = await transcription_agent.generate_clinical_note(note_request)

        return {
            "success": True,
            "data": {
                "note_id": result.note_id,
                "note_type": result.note_type,
                "structured_content": result.structured_content,
                "formatted_note": result.formatted_note,
                "quality_score": result.quality_score,
                "missing_sections": result.missing_sections,
                "recommendations": result.recommendations,
                "timestamp": result.timestamp.isoformat(),
            },
        }

    except Exception as e:
        log_healthcare_event(
            logger,
            logging.ERROR,
            f"Clinical note generation API error: {str(e)}",
            context={
                "endpoint": "/transcription/generate-clinical-note",
                "note_type": note_request.get("note_type"),
                "error": str(e),
            },
            operation_type="api_error",
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Clinical note generation failed: {str(e)}",
        )


@router.get("/templates")
async def get_documentation_templates() -> dict[str, Any]:
    """
    Get available clinical documentation templates

    Medical Disclaimer: Administrative template information only.
    Does not provide medical advice or clinical guidance.
    """
    try:
        log_healthcare_event(
            logger,
            logging.INFO,
            "Documentation templates requested",
            context={
                "endpoint": "/transcription/templates",
                "templates_count": len(transcription_agent.templates),
            },
            operation_type="template_request",
        )

        templates_info = []
        for _template_id, template in transcription_agent.templates.items():
            templates_info.append(
                {
                    "template_id": template.template_id,
                    "template_name": template.template_name,
                    "template_type": template.template_type,
                    "required_sections": template.required_sections,
                    "optional_sections": template.optional_sections,
                    "formatting_rules": template.formatting_rules,
                }
            )

        return {
            "success": True,
            "data": {"templates": templates_info, "total_templates": len(templates_info)},
        }

    except Exception as e:
        log_healthcare_event(
            logger,
            logging.ERROR,
            f"Templates request API error: {str(e)}",
            context={"endpoint": "/transcription/templates", "error": str(e)},
            operation_type="api_error",
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Templates request failed: {str(e)}",
        )


@router.get("/medical-terms")
async def get_medical_terms() -> dict[str, Any]:
    """
    Get recognized medical terms and abbreviations

    Medical Disclaimer: Administrative terminology reference only.
    Does not provide medical advice or clinical definitions.
    """
    try:
        log_healthcare_event(
            logger,
            logging.INFO,
            "Medical terms dictionary requested",
            context={
                "endpoint": "/transcription/medical-terms",
                "terms_count": len(transcription_agent.medical_terms),
            },
            operation_type="terms_request",
        )

        return {
            "success": True,
            "data": {
                "medical_terms": transcription_agent.medical_terms,
                "total_terms": len(transcription_agent.medical_terms),
            },
        }

    except Exception as e:
        log_healthcare_event(
            logger,
            logging.ERROR,
            f"Medical terms request API error: {str(e)}",
            context={"endpoint": "/transcription/medical-terms", "error": str(e)},
            operation_type="api_error",
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Medical terms request failed: {str(e)}",
        )


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint for transcription service"""
    return {
        "status": "healthy",
        "service": "transcription",
        "timestamp": datetime.now().isoformat(),
        "capabilities": transcription_agent.capabilities,
        "medical_terms_count": len(transcription_agent.medical_terms),
        "templates_count": len(transcription_agent.templates),
    }
