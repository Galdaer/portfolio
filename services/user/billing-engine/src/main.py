"""
Billing Engine Service
Standalone microservice for medical billing, claims processing, and payment tracking
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from claim_processor import BillingTreeOfThoughtsProcessor
from code_validator import MedicalCodeValidator
from models.billing_models import (
    BillingAnalytics,
    BillingReport,
    ClaimRequest,
    ClaimResult,
    ClaimStatus,
    CodeValidationRequest,
    PaymentRequest,
    PaymentResult,
)
from payment_tracker import PaymentTracker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Billing Engine Service",
    description="Medical billing engine with claims processing, code validation, and payment tracking",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
code_validator = MedicalCodeValidator()
payment_tracker = PaymentTracker()

# Get service URLs from environment
INSURANCE_VERIFICATION_URL = os.getenv("INSURANCE_VERIFICATION_URL", "http://172.20.0.23:8003")
HEALTHCARE_API_URL = os.getenv("HEALTHCARE_API_URL", "http://172.20.0.11:8000")


class BillingEngineService:
    """Main billing engine service class"""
    
    def __init__(self):
        self.code_validator = code_validator
        self.payment_tracker = payment_tracker
        self.tot_processor = None  # Initialize in async context
        
    async def initialize_async_components(self):
        """Initialize async components"""
        self.tot_processor = BillingTreeOfThoughtsProcessor(INSURANCE_VERIFICATION_URL)
    
    async def submit_claim(
        self,
        request: ClaimRequest,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Submit insurance claim with Tree-of-Thoughts reasoning"""
        
        session_id = session_id or f"claim_{uuid4().hex[:8]}"
        claim_id = f"claim_{uuid4().hex[:8]}"
        
        try:
            # Step 1: Validate claim request
            validation_errors = await self._validate_claim_request(request)
            if validation_errors:
                return {
                    "error": "Claim validation failed",
                    "validation_errors": validation_errors,
                    "session_id": session_id,
                    "claim_id": claim_id
                }
            
            # Step 2: Process Tree-of-Thoughts reasoning
            async with self.tot_processor:
                reasoning_result = await self.tot_processor.process_claim_reasoning(
                    request, session_id
                )
            
            # Step 3: Determine processing action based on reasoning
            final_action = reasoning_result["final_decision"]["final_action"]
            
            if final_action == "SUBMIT_IMMEDIATELY":
                # Submit claim immediately
                claim_result = await self._submit_claim_to_payer(request, claim_id)
                processing_status = "submitted"
            elif final_action == "SUBMIT_WITH_MONITORING":
                # Submit with enhanced monitoring
                claim_result = await self._submit_claim_to_payer(request, claim_id)
                processing_status = "submitted_monitoring"
            else:  # HOLD_FOR_REVIEW
                # Hold for manual review
                claim_result = await self._create_pending_claim(request, claim_id)
                processing_status = "held_for_review"
            
            # Step 4: Store claim and reasoning
            await self._store_claim_record(claim_result, reasoning_result)
            
            return {
                "claim_result": claim_result.dict(),
                "processing_status": processing_status,
                "reasoning": reasoning_result,
                "session_id": session_id,
                "recommendations": reasoning_result["final_decision"]["recommendations"],
                "submitted_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Claim submission failed: {e}")
            return {
                "error": "Claim submission failed",
                "error_details": str(e),
                "session_id": session_id,
                "claim_id": claim_id
            }
    
    async def validate_codes(
        self,
        request: CodeValidationRequest
    ) -> Dict[str, Any]:
        """Validate medical billing codes"""
        
        try:
            validation_result = await self.code_validator.validate_codes(request)
            return {
                "validation_result": validation_result.dict(),
                "validated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Code validation failed: {e}")
            return {
                "error": "Code validation failed",
                "error_details": str(e)
            }
    
    async def process_payment(
        self,
        request: PaymentRequest
    ) -> Dict[str, Any]:
        """Process payment for a claim"""
        
        try:
            # Get claim information
            claim_info = await self._get_claim_info(request.claim_id)
            if not claim_info:
                return {
                    "error": "Claim not found",
                    "claim_id": request.claim_id
                }
            
            # Process payment
            payment_result = await self.payment_tracker.process_payment(request, claim_info)
            
            # Update claim status if fully paid
            if payment_result.remaining_balance <= Decimal("0.01"):
                await self._update_claim_status(request.claim_id, ClaimStatus.PAID)
            
            return {
                "payment_result": payment_result.dict(),
                "processed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Payment processing failed: {e}")
            return {
                "error": "Payment processing failed",
                "error_details": str(e),
                "claim_id": request.claim_id
            }
    
    async def get_claim_status(
        self,
        claim_id: str
    ) -> Dict[str, Any]:
        """Get current status of a claim"""
        
        try:
            claim_info = await self._get_claim_info(claim_id)
            if not claim_info:
                return {
                    "error": "Claim not found",
                    "claim_id": claim_id
                }
            
            # Get payment history
            payment_history = await self._get_claim_payment_history(claim_id)
            
            # Get processing timeline
            timeline = await self._get_claim_timeline(claim_id)
            
            return {
                "claim_info": claim_info.dict(),
                "payment_history": payment_history,
                "timeline": timeline,
                "retrieved_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Claim status retrieval failed: {e}")
            return {
                "error": "Claim status retrieval failed",
                "error_details": str(e),
                "claim_id": claim_id
            }
    
    async def generate_billing_analytics(
        self,
        start_date: datetime,
        end_date: datetime,
        provider_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate billing analytics for a date range"""
        
        try:
            # Get claims data for period
            claims_data = await self._get_claims_for_period(start_date, end_date, provider_filter)
            
            # Calculate analytics
            analytics = await self._calculate_billing_analytics(claims_data, start_date, end_date)
            
            return {
                "analytics": analytics.dict(),
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Analytics generation failed: {e}")
            return {
                "error": "Analytics generation failed",
                "error_details": str(e)
            }
    
    # Validation and helper methods
    async def _validate_claim_request(self, request: ClaimRequest) -> List[str]:
        """Validate claim request"""
        
        errors = []
        
        # Required fields
        if not request.patient_id:
            errors.append("Patient ID is required")
        
        if not request.member_id:
            errors.append("Member ID is required")
        
        if not request.provider_npi:
            errors.append("Provider NPI is required")
        
        if not request.service_line_items:
            errors.append("At least one service line item is required")
        
        # Validate service line items
        for i, line_item in enumerate(request.service_line_items):
            if line_item.quantity <= 0:
                errors.append(f"Line item {i+1}: Quantity must be greater than 0")
            
            if line_item.unit_price <= Decimal("0.00"):
                errors.append(f"Line item {i+1}: Unit price must be greater than 0")
            
            if line_item.total_amount != line_item.quantity * line_item.unit_price:
                errors.append(f"Line item {i+1}: Total amount doesn't match quantity * unit price")
        
        # Validate total charges
        calculated_total = sum(item.total_amount for item in request.service_line_items)
        if request.total_charges != calculated_total:
            errors.append("Total charges doesn't match sum of line items")
        
        return errors
    
    async def _submit_claim_to_payer(
        self,
        request: ClaimRequest,
        claim_id: str
    ) -> ClaimResult:
        """Submit claim to insurance payer (mock implementation)"""
        
        # Mock claim submission - in production, integrate with EDI system
        await asyncio.sleep(0.1)  # Simulate processing delay
        
        # Generate mock claim number
        claim_number = f"CLM{datetime.utcnow().strftime('%Y%m%d')}{claim_id[-6:]}"
        
        # Mock approval logic
        if request.total_charges <= Decimal("500.00"):
            status = ClaimStatus.APPROVED
            approved_amount = request.total_charges * Decimal("0.9")  # 90% approved
            denial_reasons = []
        elif request.total_charges <= Decimal("2000.00"):
            status = ClaimStatus.PENDING
            approved_amount = None
            denial_reasons = []
        else:
            status = ClaimStatus.DENIED
            approved_amount = Decimal("0.00")
            denial_reasons = ["Amount exceeds authorization limit"]
        
        return ClaimResult(
            claim_id=claim_id,
            claim_number=claim_number,
            status=status,
            total_charges=request.total_charges,
            approved_amount=approved_amount,
            denied_amount=request.total_charges - (approved_amount or Decimal("0.00")),
            patient_responsibility=approved_amount * Decimal("0.2") if approved_amount else None,
            denial_reasons=denial_reasons,
            reference_number=f"REF{uuid4().hex[:8].upper()}",
            estimated_payment_date=datetime.utcnow() + timedelta(days=14) if status == ClaimStatus.APPROVED else None
        )
    
    async def _create_pending_claim(
        self,
        request: ClaimRequest,
        claim_id: str
    ) -> ClaimResult:
        """Create pending claim for manual review"""
        
        return ClaimResult(
            claim_id=claim_id,
            status=ClaimStatus.PENDING,
            total_charges=request.total_charges,
            processing_errors=["Held for manual review based on Tree-of-Thoughts analysis"]
        )
    
    # Mock data methods - replace with actual database operations
    async def _store_claim_record(
        self,
        claim_result: ClaimResult,
        reasoning_result: Dict[str, Any]
    ) -> None:
        """Store claim record and reasoning"""
        # Mock storage - in production, store in database
        logger.info(f"Stored claim {claim_result.claim_id} with reasoning {reasoning_result['reasoning_id']}")
    
    async def _get_claim_info(self, claim_id: str) -> Optional[ClaimResult]:
        """Get claim information by ID"""
        # Mock claim data
        return ClaimResult(
            claim_id=claim_id,
            claim_number=f"CLM{claim_id[-8:]}",
            status=ClaimStatus.APPROVED,
            total_charges=Decimal("250.00"),
            approved_amount=Decimal("225.00"),
            denied_amount=Decimal("25.00"),
            patient_responsibility=Decimal("45.00")
        )
    
    async def _update_claim_status(
        self,
        claim_id: str,
        status: ClaimStatus
    ) -> None:
        """Update claim status"""
        logger.info(f"Updated claim {claim_id} status to {status}")
    
    async def _get_claim_payment_history(
        self,
        claim_id: str
    ) -> List[Dict[str, Any]]:
        """Get payment history for claim"""
        # Mock payment history
        return [
            {
                "payment_id": "pay_12345678",
                "amount": 150.00,
                "payment_date": (datetime.utcnow() - timedelta(days=5)).isoformat(),
                "payment_method": "electronic",
                "status": "completed"
            }
        ]
    
    async def _get_claim_timeline(self, claim_id: str) -> List[Dict[str, Any]]:
        """Get processing timeline for claim"""
        # Mock timeline
        return [
            {
                "date": (datetime.utcnow() - timedelta(days=7)).isoformat(),
                "event": "claim_submitted",
                "description": "Claim submitted to payer"
            },
            {
                "date": (datetime.utcnow() - timedelta(days=5)).isoformat(),
                "event": "claim_approved",
                "description": "Claim approved by payer"
            }
        ]
    
    async def _get_claims_for_period(
        self,
        start_date: datetime,
        end_date: datetime,
        provider_filter: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Get claims data for analytics period"""
        # Mock claims data
        return [
            {
                "claim_id": "claim_001",
                "status": "approved",
                "total_charges": 250.00,
                "approved_amount": 225.00,
                "submission_date": start_date + timedelta(days=1),
                "provider_id": "PROV001"
            },
            {
                "claim_id": "claim_002",
                "status": "denied",
                "total_charges": 150.00,
                "approved_amount": 0.00,
                "submission_date": start_date + timedelta(days=2),
                "provider_id": "PROV002"
            }
        ]
    
    async def _calculate_billing_analytics(
        self,
        claims_data: List[Dict[str, Any]],
        start_date: datetime,
        end_date: datetime
    ) -> BillingAnalytics:
        """Calculate billing analytics from claims data"""
        
        total_claims = len(claims_data)
        approved_claims = sum(1 for claim in claims_data if claim["status"] == "approved")
        denied_claims = sum(1 for claim in claims_data if claim["status"] == "denied")
        
        total_billed = sum(Decimal(str(claim["total_charges"])) for claim in claims_data)
        total_approved = sum(Decimal(str(claim["approved_amount"])) for claim in claims_data)
        total_denied = total_billed - total_approved
        
        return BillingAnalytics(
            period_start=start_date,
            period_end=end_date,
            total_claims_submitted=total_claims,
            total_claims_approved=approved_claims,
            total_claims_denied=denied_claims,
            approval_rate=(approved_claims / total_claims * 100) if total_claims > 0 else 0.0,
            average_processing_time_days=5.2,  # Mock average
            total_billed_amount=total_billed,
            total_approved_amount=total_approved,
            total_denied_amount=total_denied,
            collection_rate=85.5,  # Mock collection rate
            top_denial_reasons=[
                {"reason": "Lack of authorization", "count": 3},
                {"reason": "Invalid diagnosis code", "count": 2}
            ],
            provider_performance={
                "PROV001": {"approval_rate": 90.0, "avg_amount": 275.00},
                "PROV002": {"approval_rate": 75.0, "avg_amount": 180.00}
            }
        )


# Initialize service
billing_service = BillingEngineService()


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize async components on startup"""
    await billing_service.initialize_async_components()
    logger.info("Billing Engine Service started successfully")


# API Endpoints
@app.post("/claim", response_model=None)
async def submit_claim(request: ClaimRequest):
    """Submit insurance claim"""
    try:
        result = await billing_service.submit_claim(request)
        return result
    except Exception as e:
        logger.error(f"Claim submission endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/validate-codes", response_model=None)
async def validate_codes(request: CodeValidationRequest):
    """Validate medical codes"""
    try:
        result = await billing_service.validate_codes(request)
        return result
    except Exception as e:
        logger.error(f"Code validation endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/claim/{claim_id}", response_model=None)
async def get_claim_status(claim_id: str):
    """Get claim status"""
    try:
        result = await billing_service.get_claim_status(claim_id)
        return result
    except Exception as e:
        logger.error(f"Claim status endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/payment", response_model=None)
async def process_payment(request: PaymentRequest):
    """Process payment"""
    try:
        result = await billing_service.process_payment(request)
        return result
    except Exception as e:
        logger.error(f"Payment endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/analytics", response_model=None)
async def get_billing_analytics(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    provider_id: Optional[str] = Query(None, description="Provider ID filter")
):
    """Get billing analytics"""
    try:
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)
        
        result = await billing_service.generate_billing_analytics(
            start_dt, end_dt, provider_id
        )
        return result
    except Exception as e:
        logger.error(f"Analytics endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "billing-engine",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "dependencies": {
            "insurance_verification": INSURANCE_VERIFICATION_URL,
            "healthcare_api": HEALTHCARE_API_URL
        }
    }


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception handler: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8004))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("ENVIRONMENT", "development") == "development",
        log_level="info"
    )