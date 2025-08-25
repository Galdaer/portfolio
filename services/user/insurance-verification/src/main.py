"""
Insurance Verification Service
Standalone microservice for multi-provider insurance verification with Chain-of-Thought reasoning
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from chain_of_thought_processor import InsuranceChainOfThoughtProcessor
from models.verification_models import (
    BenefitsInquiryRequest,
    BenefitsInquiryResult,
    InsuranceVerificationRequest,
    InsuranceVerificationResult,
    PriorAuthRequest,
    PriorAuthResult,
)
from providers.anthem_provider import AnthemProvider
from safety_checker import InsuranceSafetyChecker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Insurance Verification Service",
    description="Multi-provider insurance verification with Chain-of-Thought reasoning",
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
safety_checker = InsuranceSafetyChecker()
cot_processor = InsuranceChainOfThoughtProcessor()

# Initialize providers (mock implementations for now)
providers = {
    "anthem": AnthemProvider(),
    "uhc": None,  # TODO: Implement UnitedHealthProvider
    "cigna": None,  # TODO: Implement CignaProvider
    "aetna": None,  # TODO: Implement AetnaProvider
}


class InsuranceVerificationService:
    """Main insurance verification service class"""
    
    def __init__(self):
        self.providers = providers
        self.safety_checker = safety_checker
        self.cot_processor = cot_processor
        
    async def verify_eligibility(
        self,
        request: InsuranceVerificationRequest,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Verify patient eligibility with comprehensive error checking and CoT reasoning"""
        
        session_id = session_id or f"verify_{uuid4().hex[:8]}"
        
        # Step 1: Safety validation
        validation_result = await self.safety_checker.validate_verification_request(request)
        if not validation_result["valid"]:
            return {
                "error": "Validation failed",
                "issues": validation_result["issues"],
                "warnings": validation_result["warnings"],
                "safe_to_retry": False,
                "session_id": session_id
            }
        
        # Step 2: Determine insurance provider
        provider_name = await self._detect_provider(request.member_id, request.provider_id)
        
        if provider_name not in self.providers or self.providers[provider_name] is None:
            return {
                "error": f"Unsupported insurance provider: {provider_name}",
                "supported_providers": [name for name, provider in self.providers.items() if provider is not None],
                "session_id": session_id
            }
        
        try:
            # Step 3: Verify eligibility with specific provider
            provider = self.providers[provider_name]
            
            async with provider:
                eligibility_result = await provider.check_eligibility(request)
            
            # Step 4: Apply safety validations to response
            response_validation = await self.safety_checker.validate_response(
                eligibility_result.dict(), request.dict()
            )
            
            # Step 5: Chain-of-Thought reasoning
            cot_reasoning = await self.cot_processor.process_verification_reasoning(
                request, eligibility_result, session_id
            )
            
            # Step 6: Compile final response
            return {
                "verification_result": eligibility_result.dict(),
                "validation": {
                    "request_validation": validation_result,
                    "response_validation": response_validation
                },
                "reasoning": cot_reasoning,
                "session_id": session_id,
                "processed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Verification failed for provider {provider_name}: {e}")
            return {
                "error": "Verification failed",
                "provider": provider_name,
                "retry_recommended": True,
                "error_code": "PROVIDER_ERROR",
                "session_id": session_id
            }
    
    async def request_prior_authorization(
        self,
        request: PriorAuthRequest,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Request prior authorization with CoT reasoning"""
        
        session_id = session_id or f"auth_{uuid4().hex[:8]}"
        
        # Validate request
        validation_result = await self.safety_checker.validate_prior_auth_request(request)
        if not validation_result["valid"]:
            return {
                "error": "Validation failed",
                "issues": validation_result["issues"],
                "warnings": validation_result["warnings"],
                "session_id": session_id
            }
        
        # Determine provider
        provider_name = await self._detect_provider(request.member_id, request.provider_id)
        
        if provider_name not in self.providers or self.providers[provider_name] is None:
            return {
                "error": f"Unsupported insurance provider: {provider_name}",
                "supported_providers": [name for name, provider in self.providers.items() if provider is not None],
                "session_id": session_id
            }
        
        try:
            provider = self.providers[provider_name]
            
            async with provider:
                auth_result = await provider.request_prior_auth(request)
            
            # Chain-of-Thought reasoning for authorization decision
            cot_reasoning = await self.cot_processor.process_prior_auth_reasoning(
                request, auth_result, session_id
            )
            
            return {
                "authorization_result": auth_result.dict(),
                "validation": validation_result,
                "reasoning": cot_reasoning,
                "session_id": session_id,
                "processed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Prior auth failed for provider {provider_name}: {e}")
            return {
                "error": "Prior authorization request failed",
                "provider": provider_name,
                "retry_recommended": True,
                "error_code": "PROVIDER_ERROR",
                "session_id": session_id
            }
    
    async def inquire_benefits(
        self,
        request: BenefitsInquiryRequest,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Inquire about member benefits"""
        
        session_id = session_id or f"benefits_{uuid4().hex[:8]}"
        
        # Validate request
        validation_result = await self.safety_checker.validate_benefits_request(request)
        if not validation_result["valid"]:
            return {
                "error": "Validation failed",
                "issues": validation_result["issues"],
                "warnings": validation_result["warnings"],
                "session_id": session_id
            }
        
        # Determine provider
        provider_name = await self._detect_provider(request.member_id, "")
        
        if provider_name not in self.providers or self.providers[provider_name] is None:
            return {
                "error": f"Unsupported insurance provider: {provider_name}",
                "supported_providers": [name for name, provider in self.providers.items() if provider is not None],
                "session_id": session_id
            }
        
        try:
            provider = self.providers[provider_name]
            
            async with provider:
                benefits_result = await provider.inquire_benefits(request)
            
            return {
                "benefits_result": benefits_result.dict(),
                "validation": validation_result,
                "session_id": session_id,
                "processed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Benefits inquiry failed for provider {provider_name}: {e}")
            return {
                "error": "Benefits inquiry failed",
                "provider": provider_name,
                "retry_recommended": True,
                "error_code": "PROVIDER_ERROR",
                "session_id": session_id
            }
    
    async def _detect_provider(self, member_id: str, provider_id: str) -> str:
        """Detect insurance provider from member ID and provider ID patterns"""
        
        # Simple provider detection logic (enhance with real patterns)
        member_id_lower = member_id.lower()
        provider_id_lower = provider_id.lower()
        
        if "ant" in provider_id_lower or member_id.startswith(("A", "B", "C")):
            return "anthem"
        elif "uhc" in provider_id_lower or "united" in provider_id_lower:
            return "uhc"
        elif "cigna" in provider_id_lower:
            return "cigna"
        elif "aetna" in provider_id_lower:
            return "aetna"
        else:
            # Default to anthem for mock implementation
            return "anthem"


# Initialize service
verification_service = InsuranceVerificationService()


# API Endpoints
@app.post("/verify", response_model=None)
async def verify_insurance(request: InsuranceVerificationRequest):
    """Verify insurance eligibility"""
    try:
        result = await verification_service.verify_eligibility(request)
        return result
    except Exception as e:
        logger.error(f"Verification endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/prior-auth", response_model=None)
async def request_prior_authorization(request: PriorAuthRequest):
    """Request prior authorization"""
    try:
        result = await verification_service.request_prior_authorization(request)
        return result
    except Exception as e:
        logger.error(f"Prior auth endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/benefits", response_model=None)
async def inquire_benefits(request: BenefitsInquiryRequest):
    """Inquire about member benefits"""
    try:
        result = await verification_service.inquire_benefits(request)
        return result
    except Exception as e:
        logger.error(f"Benefits endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "insurance-verification",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "providers": {
            name: "available" if provider is not None else "not_implemented"
            for name, provider in providers.items()
        }
    }


@app.get("/providers")
async def list_providers():
    """List available insurance providers"""
    return {
        "providers": [
            {
                "name": name,
                "status": "available" if provider is not None else "not_implemented",
                "description": f"{name.title()} Insurance Provider"
            }
            for name, provider in providers.items()
        ]
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
    port = int(os.getenv("PORT", 8003))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("ENVIRONMENT", "development") == "development",
        log_level="info"
    )