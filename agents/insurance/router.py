"""
FastAPI Router for Healthcare Insurance Verification Agent
Provides REST API endpoints for insurance verification and prior authorization
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status

from core.infrastructure.healthcare_logger import get_healthcare_logger, log_healthcare_event
from core.infrastructure.phi_monitor import phi_monitor_decorator as phi_monitor
from core.infrastructure.phi_monitor import scan_for_phi

from .insurance_agent import insurance_verification_agent

logger = get_healthcare_logger("api.insurance_verification")
router = APIRouter(prefix="/insurance", tags=["insurance_verification"])


@router.post("/verify-eligibility")
@phi_monitor(risk_level="high", operation_type="api_insurance_verification")
async def verify_insurance_eligibility(insurance_info: dict[str, Any]):
    """
    Verify patient insurance eligibility and benefits

    Medical Disclaimer: Administrative insurance verification only.
    Does not provide medical advice or treatment authorization.
    """
    try:
        # Validate input for PHI exposure
        scan_for_phi(str(insurance_info))

        log_healthcare_event(
            logger,
            logging.INFO,
            "Insurance eligibility verification request received",
            context={
                "endpoint": "/insurance/verify-eligibility",
                "has_member_id": "member_id" in insurance_info,
                "has_group_id": "group_id" in insurance_info,
                "payer_name": insurance_info.get("payer_name", "unknown"),
            },
            operation_type="api_request",
        )

        result = await insurance_verification_agent.verify_insurance_eligibility(insurance_info)

        return {
            "success": True,
            "data": {
                "verification_id": result.verification_id,
                "status": result.status,
                "member_id": result.member_id[:4] + "****"
                if result.member_id
                else None,  # Mask for response
                "coverage_active": result.coverage_active,
                "benefits_summary": result.benefits_summary,
                "verification_errors": result.verification_errors,
                "compliance_validated": result.compliance_validated,
                "timestamp": result.timestamp.isoformat(),
                "metadata": result.metadata,
            },
        }

    except Exception as e:
        log_healthcare_event(
            logger,
            logging.ERROR,
            f"Insurance verification API error: {str(e)}",
            context={
                "endpoint": "/insurance/verify-eligibility",
                "error": str(e),
                "error_type": type(e).__name__,
            },
            operation_type="api_error",
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Insurance verification failed: {str(e)}",
        )


@router.post("/prior-authorization")
@phi_monitor(risk_level="medium", operation_type="api_prior_authorization")
async def request_prior_authorization(auth_request: dict[str, Any]):
    """
    Submit prior authorization request to insurance payer

    Medical Disclaimer: Administrative prior authorization processing only.
    Does not provide medical advice or treatment recommendations.
    """
    try:
        # Validate input for PHI exposure
        scan_for_phi(str(auth_request))

        log_healthcare_event(
            logger,
            logging.INFO,
            "Prior authorization request received",
            context={
                "endpoint": "/insurance/prior-authorization",
                "has_member_id": "member_id" in auth_request,
                "procedure_count": len(auth_request.get("procedure_codes", [])),
                "diagnosis_count": len(auth_request.get("diagnosis_codes", [])),
            },
            operation_type="api_request",
        )

        result = await insurance_verification_agent.request_prior_authorization(auth_request)

        return {
            "success": True,
            "data": {
                "auth_id": result.auth_id,
                "status": result.status,
                "reference_number": result.reference_number,
                "decision_date": result.decision_date.isoformat() if result.decision_date else None,
                "approved_services": result.approved_services,
                "denied_services": result.denied_services,
                "auth_errors": result.auth_errors,
                "estimated_decision_days": result.estimated_decision_days,
                "timestamp": result.timestamp.isoformat(),
            },
        }

    except Exception as e:
        log_healthcare_event(
            logger,
            logging.ERROR,
            f"Prior authorization API error: {str(e)}",
            context={
                "endpoint": "/insurance/prior-authorization",
                "error": str(e),
                "error_type": type(e).__name__,
            },
            operation_type="api_error",
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prior authorization failed: {str(e)}",
        )


@router.post("/check-coverage")
async def check_coverage_for_service(coverage_request: dict[str, Any]):
    """
    Check insurance coverage for specific healthcare service

    Medical Disclaimer: Administrative coverage checking only.
    Does not provide medical advice or treatment recommendations.
    """
    try:
        log_healthcare_event(
            logger,
            logging.INFO,
            f"Coverage check requested for service {coverage_request.get('service_code', 'unknown')}",
            context={
                "endpoint": "/insurance/check-coverage",
                "service_code": coverage_request.get("service_code"),
                "service_type": coverage_request.get("service_type"),
            },
            operation_type="coverage_check",
        )

        result = await insurance_verification_agent.check_coverage_for_service(coverage_request)

        return {"success": True, "data": result}

    except Exception as e:
        log_healthcare_event(
            logger,
            logging.ERROR,
            f"Coverage check API error: {str(e)}",
            context={
                "endpoint": "/insurance/check-coverage",
                "service_code": coverage_request.get("service_code"),
                "error": str(e),
            },
            operation_type="api_error",
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Coverage check failed: {str(e)}",
        )


@router.get("/report")
async def generate_insurance_report(start_date: str, end_date: str):
    """
    Generate insurance verification and authorization report

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Medical Disclaimer: Administrative reporting only.
    Does not provide medical advice or clinical insights.
    """
    try:
        log_healthcare_event(
            logger,
            logging.INFO,
            f"Insurance report requested: {start_date} to {end_date}",
            context={
                "endpoint": "/insurance/report",
                "start_date": start_date,
                "end_date": end_date,
            },
            operation_type="report_generation",
        )

        date_range = {"start_date": start_date, "end_date": end_date}

        result = await insurance_verification_agent.generate_insurance_report(date_range)

        return {"success": True, "data": result}

    except Exception as e:
        log_healthcare_event(
            logger,
            logging.ERROR,
            f"Insurance report API error: {str(e)}",
            context={
                "endpoint": "/insurance/report",
                "start_date": start_date,
                "end_date": end_date,
                "error": str(e),
            },
            operation_type="api_error",
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Insurance report generation failed: {str(e)}",
        )


@router.get("/health")
async def health_check():
    """Health check endpoint for insurance verification service"""
    return {
        "status": "healthy",
        "service": "insurance_verification",
        "timestamp": datetime.now().isoformat(),
        "capabilities": insurance_verification_agent.capabilities,
        "supported_payers": list(insurance_verification_agent.supported_payers.keys()),
    }
