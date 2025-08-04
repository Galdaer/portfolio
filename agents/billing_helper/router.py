"""
FastAPI Router for Healthcare Billing Helper Agent
Provides REST API endpoints for medical billing and claims processing
"""

from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any, List
import logging
from datetime import datetime

from .billing_agent import billing_helper_agent
from core.infrastructure.healthcare_logger import get_healthcare_logger, log_healthcare_event
from core.infrastructure.phi_monitor import phi_monitor, scan_for_phi

logger = get_healthcare_logger('api.billing_helper')
router = APIRouter(prefix="/billing", tags=["billing_helper"])


@router.post("/process-claim")
@phi_monitor(risk_level="medium", operation_type="api_claim_processing")
async def process_claim(claim_data: Dict[str, Any]):
    """
    Process a medical billing claim
    
    Medical Disclaimer: Administrative billing support and coding assistance only.
    Does not provide medical advice, diagnosis, or treatment recommendations.
    """
    try:
        # Validate input for PHI exposure
        scan_for_phi(str(claim_data))
        
        log_healthcare_event(
            logger,
            logging.INFO,
            "Claim processing request received",
            context={
                'endpoint': '/billing/process-claim',
                'has_procedure_codes': 'procedure_codes' in claim_data,
                'has_diagnosis_codes': 'diagnosis_codes' in claim_data
            },
            operation_type='api_request'
        )
        
        result = await billing_helper_agent.process_claim(claim_data)
        
        return {
            "success": True,
            "data": {
                "billing_id": result.billing_id,
                "status": result.status,
                "claim_number": result.claim_number,
                "total_amount": result.total_amount,
                "processing_errors": result.processing_errors,
                "compliance_validated": result.compliance_validated,
                "timestamp": result.timestamp.isoformat()
            }
        }
        
    except Exception as e:
        log_healthcare_event(
            logger,
            logging.ERROR,
            f"Claim processing API error: {str(e)}",
            context={
                'endpoint': '/billing/process-claim',
                'error': str(e),
                'error_type': type(e).__name__
            },
            operation_type='api_error'
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Claim processing failed: {str(e)}"
        )


@router.post("/validate-cpt/{cpt_code}")
async def validate_cpt_code(cpt_code: str):
    """
    Validate a CPT procedure code
    
    Medical Disclaimer: Administrative code validation only.
    Does not provide medical advice or procedure recommendations.
    """
    try:
        log_healthcare_event(
            logger,
            logging.INFO,
            f"CPT code validation requested: {cpt_code}",
            context={
                'endpoint': '/billing/validate-cpt',
                'cpt_code': cpt_code
            },
            operation_type='code_validation'
        )
        
        result = await billing_helper_agent.validate_cpt_code(cpt_code)
        
        return {
            "success": True,
            "data": {
                "code": result.code,
                "is_valid": result.is_valid,
                "description": result.description,
                "modifier_required": result.modifier_required,
                "billing_notes": result.billing_notes
            }
        }
        
    except Exception as e:
        log_healthcare_event(
            logger,
            logging.ERROR,
            f"CPT validation API error: {str(e)}",
            context={
                'endpoint': '/billing/validate-cpt',
                'cpt_code': cpt_code,
                'error': str(e)
            },
            operation_type='api_error'
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"CPT validation failed: {str(e)}"
        )


@router.post("/validate-icd/{icd_code}")
async def validate_icd_code(icd_code: str):
    """
    Validate an ICD-10 diagnosis code
    
    Medical Disclaimer: Administrative code validation only.
    Does not provide medical advice or diagnostic recommendations.
    """
    try:
        log_healthcare_event(
            logger,
            logging.INFO,
            f"ICD-10 code validation requested: {icd_code}",
            context={
                'endpoint': '/billing/validate-icd',
                'icd_code': icd_code
            },
            operation_type='code_validation'
        )
        
        result = await billing_helper_agent.validate_icd_code(icd_code)
        
        return {
            "success": True,
            "data": {
                "code": result.code,
                "is_valid": result.is_valid,
                "description": result.description,
                "category": result.category,
                "billing_notes": result.billing_notes
            }
        }
        
    except Exception as e:
        log_healthcare_event(
            logger,
            logging.ERROR,
            f"ICD validation API error: {str(e)}",
            context={
                'endpoint': '/billing/validate-icd',
                'icd_code': icd_code,
                'error': str(e)
            },
            operation_type='api_error'
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ICD validation failed: {str(e)}"
        )


@router.post("/verify-insurance")
@phi_monitor(risk_level="medium", operation_type="api_insurance_verification")
async def verify_insurance_benefits(insurance_info: Dict[str, Any]):
    """
    Verify insurance benefits and coverage
    
    Medical Disclaimer: Administrative insurance verification only.
    Does not provide medical advice or treatment authorization.
    """
    try:
        # Validate input for PHI exposure
        scan_for_phi(str(insurance_info))
        
        log_healthcare_event(
            logger,
            logging.INFO,
            "Insurance verification request received",
            context={
                'endpoint': '/billing/verify-insurance',
                'has_member_id': 'member_id' in insurance_info,
                'has_group_id': 'group_id' in insurance_info
            },
            operation_type='api_request'
        )
        
        result = await billing_helper_agent.verify_insurance_benefits(insurance_info)
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        log_healthcare_event(
            logger,
            logging.ERROR,
            f"Insurance verification API error: {str(e)}",
            context={
                'endpoint': '/billing/verify-insurance',
                'error': str(e),
                'error_type': type(e).__name__
            },
            operation_type='api_error'
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Insurance verification failed: {str(e)}"
        )


@router.get("/report")
async def generate_billing_report(start_date: str, end_date: str):
    """
    Generate billing summary report for date range
    
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
            f"Billing report requested: {start_date} to {end_date}",
            context={
                'endpoint': '/billing/report',
                'start_date': start_date,
                'end_date': end_date
            },
            operation_type='report_generation'
        )
        
        date_range = {
            "start_date": start_date,
            "end_date": end_date
        }
        
        result = await billing_helper_agent.generate_billing_report(date_range)
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        log_healthcare_event(
            logger,
            logging.ERROR,
            f"Billing report API error: {str(e)}",
            context={
                'endpoint': '/billing/report',
                'start_date': start_date,
                'end_date': end_date,
                'error': str(e)
            },
            operation_type='api_error'
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation failed: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint for billing helper service"""
    return {
        "status": "healthy",
        "service": "billing_helper",
        "timestamp": datetime.now().isoformat(),
        "capabilities": billing_helper_agent.capabilities
    }
