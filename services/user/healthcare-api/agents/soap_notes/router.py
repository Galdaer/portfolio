"""
SOAP Notes Agent Router

Provides REST API endpoints for SOAP note generation and clinical documentation services.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from datetime import datetime

from agents.soap_notes import SoapNotesAgent

# Initialize router
router = APIRouter(prefix="/soap-notes", tags=["SOAP Notes"])

# Initialize agent
soap_notes_agent = SoapNotesAgent()


# Request/Response Models
class SOAPGenerationRequest(BaseModel):
    transcription_text: str
    provider_id: str
    patient_id: Optional[str] = "unknown"
    encounter_date: Optional[str] = None
    note_type: str = "soap"


class ProgressNoteRequest(BaseModel):
    transcription_text: str
    provider_id: str
    patient_id: Optional[str] = "unknown"
    encounter_date: Optional[str] = None


class SessionToSOAPRequest(BaseModel):
    session_id: str
    full_transcription: str
    doctor_id: str
    patient_id: Optional[str] = "unknown"
    encounter_date: Optional[str] = None


class FormatNoteRequest(BaseModel):
    note_data: Dict[str, Any]
    note_type: str = "soap"


class SOAPNoteResponse(BaseModel):
    success: bool
    note_id: str
    formatted_note: str
    completeness_score: float
    missing_sections: List[str]
    quality_recommendations: List[str]
    timestamp: str
    error: Optional[str] = None


# API Endpoints

@router.post("/generate-soap", response_model=SOAPNoteResponse)
async def generate_soap_note(request: SOAPGenerationRequest):
    """
    Generate SOAP note from transcription text
    
    Creates a structured SOAP note with Subjective, Objective, Assessment, and Plan
    sections from medical transcription data.
    """
    try:
        # Prepare request for agent
        agent_request = {
            "generate_soap_note": {
                "transcription_text": request.transcription_text,
                "provider_id": request.provider_id,
                "patient_id": request.patient_id,
                "encounter_date": request.encounter_date or datetime.now().isoformat(),
                "note_type": request.note_type
            }
        }
        
        # Process with SOAP notes agent
        result = await soap_notes_agent.process_request(agent_request)
        
        if result.get("success", False):
            return SOAPNoteResponse(
                success=True,
                note_id=result["note_id"],
                formatted_note=result["formatted_note"],
                completeness_score=result["completeness_score"],
                missing_sections=result["missing_sections"],
                quality_recommendations=result["quality_recommendations"],
                timestamp=result["timestamp"]
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"SOAP note generation failed: {result.get('error', 'Unknown error')}"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/generate-progress", response_model=Dict[str, Any])
async def generate_progress_note(request: ProgressNoteRequest):
    """
    Generate progress note from transcription text
    
    Creates a structured progress note for follow-up visits.
    """
    try:
        # Prepare request for agent
        agent_request = {
            "generate_progress_note": {
                "transcription_text": request.transcription_text,
                "provider_id": request.provider_id,
                "patient_id": request.patient_id,
                "encounter_date": request.encounter_date or datetime.now().isoformat()
            }
        }
        
        # Process with SOAP notes agent
        result = await soap_notes_agent.process_request(agent_request)
        
        if result.get("success", False):
            return result
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Progress note generation failed: {result.get('error', 'Unknown error')}"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/session-to-soap", response_model=SOAPNoteResponse)
async def convert_session_to_soap(request: SessionToSOAPRequest):
    """
    Convert live transcription session to SOAP note
    
    Takes the full transcription from a live doctor-patient session and
    generates a structured SOAP note.
    """
    try:
        # Prepare request for agent
        agent_request = {
            "session_to_soap": {
                "session_id": request.session_id,
                "full_transcription": request.full_transcription,
                "doctor_id": request.doctor_id,
                "patient_id": request.patient_id,
                "encounter_date": request.encounter_date or datetime.now().isoformat()
            }
        }
        
        # Process with SOAP notes agent
        result = await soap_notes_agent.process_request(agent_request)
        
        if result.get("success", False):
            return SOAPNoteResponse(
                success=True,
                note_id=result["note_id"],
                formatted_note=result["soap_note"],
                completeness_score=result["completeness_score"],
                missing_sections=result["missing_sections"],
                quality_recommendations=result["quality_recommendations"],
                timestamp=result["timestamp"]
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Session to SOAP conversion failed: {result.get('error', 'Unknown error')}"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/format-note", response_model=Dict[str, Any])
async def format_existing_note(request: FormatNoteRequest):
    """
    Format existing clinical note data
    
    Takes raw clinical note data and formats it according to specified template.
    """
    try:
        # Prepare request for agent
        agent_request = {
            "format_existing_note": {
                **request.note_data,
                "note_type": request.note_type
            }
        }
        
        # Process with SOAP notes agent
        result = await soap_notes_agent.process_request(agent_request)
        
        if result.get("success", False):
            return result
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Note formatting failed: {result.get('error', 'Unknown error')}"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/templates")
async def get_note_templates():
    """
    Get available clinical note templates
    
    Returns information about available note templates and their requirements.
    """
    try:
        templates = {
            "soap": {
                "name": "Standard SOAP Note",
                "description": "Subjective, Objective, Assessment, Plan format",
                "required_sections": ["subjective", "objective", "assessment", "plan"],
                "optional_sections": ["chief_complaint", "history_present_illness", "review_of_systems"]
            },
            "progress": {
                "name": "Progress Note",
                "description": "Follow-up visit documentation", 
                "required_sections": ["interval_history", "physical_exam", "assessment_and_plan"],
                "optional_sections": ["current_medications", "vitals"]
            },
            "history_physical": {
                "name": "History & Physical",
                "description": "Comprehensive initial evaluation",
                "required_sections": ["chief_complaint", "history_present_illness", "past_medical_history", 
                                    "medications", "allergies", "physical_examination", "assessment", "plan"],
                "optional_sections": ["review_of_systems", "family_history", "social_history"]
            }
        }
        
        return {
            "success": True,
            "templates": templates,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving templates: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint for SOAP Notes service"""
    return {
        "status": "healthy",
        "service": "soap-notes-agent",
        "timestamp": datetime.now().isoformat()
    }