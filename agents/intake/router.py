"""
Intake Agent API Router
Handles patient registration, scheduling, and administrative workflows
"""

import logging
from typing import Any, cast

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agents.intake.intake_agent import HealthcareIntakeAgent
from core.dependencies import LLMClient, MCPClient

logger = logging.getLogger(__name__)

router = APIRouter()


class IntakeRequest(BaseModel):
    """Intake request model with healthcare compliance"""

    intake_type: str = Field(
        default="new_patient_registration",
        description="Type of intake: new_patient_registration, appointment_scheduling, insurance_verification, document_checklist",
    )
    patient_data: dict[str, Any] = Field(
        default_factory=dict, description="Patient data for intake processing"
    )
    session_id: str = Field(default="default", description="Session identifier")

    class Config:
        json_schema_extra = {
            "example": {
                "intake_type": "new_patient_registration",
                "patient_data": {
                    "first_name": "John",
                    "last_name": "Doe",
                    "date_of_birth": "1980-01-15",
                    "contact_phone": "555-123-4567",
                    "contact_email": "john.doe@email.com",
                    "emergency_contact": "Jane Doe - 555-987-6543",
                    "insurance_primary": "Blue Cross Blue Shield",
                },
                "session_id": "intake_session_001",
            }
        }


class AppointmentSchedulingRequest(BaseModel):
    """Appointment scheduling request model"""

    patient_id: str = Field(..., description="Patient identifier")
    provider_preference: str | None = Field(None, description="Preferred provider")
    preferred_times: list[str] = Field(
        default_factory=list, description="Preferred appointment times"
    )
    appointment_type: str = Field(default="general", description="Type of appointment")

    class Config:
        json_schema_extra = {
            "example": {
                "patient_id": "PAT_20240803_123456",
                "provider_preference": "Dr. Smith",
                "preferred_times": ["2024-08-10 09:00", "2024-08-10 14:00"],
                "appointment_type": "annual_checkup",
            }
        }


class InsuranceVerificationRequest(BaseModel):
    """Insurance verification request model"""

    patient_id: str = Field(..., description="Patient identifier")
    insurance_info: dict[str, Any] = Field(
        ..., description="Insurance information for verification"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "patient_id": "PAT_20240803_123456",
                "insurance_info": {
                    "insurance_provider": "Blue Cross Blue Shield",
                    "policy_number": "BC123456789",
                    "group_number": "GRP001",
                    "subscriber_name": "John Doe",
                },
            }
        }


@router.post("/process")
async def process_intake(
    request: IntakeRequest,
    mcp_client: Any = MCPClient,
    llm_client: Any = LLMClient,
) -> dict[str, Any]:
    """
    Process intake request with administrative support

    MEDICAL DISCLAIMER: This provides administrative support only,
    not medical advice, diagnosis, or treatment recommendations.
    """
    try:
        # Initialize intake agent
        agent = HealthcareIntakeAgent(
            mcp_client=mcp_client,
            llm_client=llm_client,
        )

        # Process intake request
        result = await agent._process_implementation(request.model_dump())

        return cast(dict[str, Any], result)

    except Exception as e:
        logger.error(f"Intake processing error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Intake processing failed: {str(e)}",
        )


@router.post("/register-patient")
async def register_new_patient(
    patient_data: dict[str, Any],
    mcp_client: Any = MCPClient,
    llm_client: Any = LLMClient,
) -> dict[str, Any]:
    """
    Register new patient with administrative validation

    Administrative support only - not medical advice.
    """
    try:
        request = {
            "intake_type": "new_patient_registration",
            "patient_data": patient_data,
            "session_id": "registration",
        }

        agent = HealthcareIntakeAgent(mcp_client=mcp_client, llm_client=llm_client)
        result = await agent._process_implementation(request)

        return cast(dict[str, Any], result)

    except Exception as e:
        logger.error(f"Patient registration error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Patient registration failed: {str(e)}",
        )


@router.post("/schedule-appointment")
async def schedule_appointment(
    request: AppointmentSchedulingRequest,
    mcp_client: Any = MCPClient,
    llm_client: Any = LLMClient,
) -> dict[str, Any]:
    """
    Schedule appointment with administrative workflow

    Administrative support only - not medical advice.
    """
    try:
        intake_request = {
            "intake_type": "appointment_scheduling",
            "patient_data": {
                "patient_id": request.patient_id,
                "provider_preference": request.provider_preference,
                "preferred_times": request.preferred_times,
                "appointment_type": request.appointment_type,
            },
            "session_id": "scheduling",
        }

        agent = HealthcareIntakeAgent(mcp_client=mcp_client, llm_client=llm_client)
        result = await agent._process_implementation(intake_request)

        return cast(dict[str, Any], result)

    except Exception as e:
        logger.error(f"Appointment scheduling error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Appointment scheduling failed: {str(e)}",
        )


@router.post("/verify-insurance")
async def verify_insurance(
    request: InsuranceVerificationRequest,
    mcp_client: Any = MCPClient,
    llm_client: Any = LLMClient,
) -> dict[str, Any]:
    """
    Verify insurance coverage with administrative validation

    Administrative support only - not medical advice.
    """
    try:
        intake_request = {
            "intake_type": "insurance_verification",
            "patient_data": {
                "patient_id": request.patient_id,
                "insurance_info": request.insurance_info,
            },
            "session_id": "insurance_verification",
        }

        agent = HealthcareIntakeAgent(mcp_client=mcp_client, llm_client=llm_client)
        result = await agent._process_implementation(intake_request)

        return cast(dict[str, Any], result)

    except Exception as e:
        logger.error(f"Insurance verification error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Insurance verification failed: {str(e)}",
        )


@router.get("/document-checklist")
async def get_document_checklist(
    appointment_type: str = "general",
    patient_type: str = "new",
    mcp_client: Any = MCPClient,
    llm_client: Any = LLMClient,
) -> dict[str, Any]:
    """
    Generate document checklist for patient intake

    Administrative support only - not medical advice.
    """
    try:
        request = {
            "intake_type": "document_checklist",
            "patient_data": {
                "appointment_type": appointment_type,
                "patient_type": patient_type,
            },
            "session_id": "document_checklist",
        }

        agent = HealthcareIntakeAgent(mcp_client=mcp_client, llm_client=llm_client)
        result = await agent._process_implementation(request)

        return cast(dict[str, Any], result)

    except Exception as e:
        logger.error(f"Document checklist error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Document checklist generation failed: {str(e)}",
        )


@router.get("/health")
async def intake_health_check() -> dict[str, Any]:
    """Health check for intake services"""
    return {
        "status": "healthy",
        "service": "intake",
        "capabilities": [
            "new_patient_registration",
            "appointment_scheduling",
            "insurance_verification",
            "document_checklist",
        ],
        "disclaimer": "Administrative support only - not medical advice",
    }
