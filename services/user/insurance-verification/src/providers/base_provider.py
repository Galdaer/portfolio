"""
Base class for insurance provider integrations
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import httpx
from models.verification_models import (
    BenefitsInquiryRequest,
    BenefitsInquiryResult,
    InsuranceVerificationRequest,
    InsuranceVerificationResult,
    PriorAuthRequest,
    PriorAuthResult,
    ProviderResponse,
)

logger = logging.getLogger(__name__)


class BaseInsuranceProvider(ABC):
    """Base class for all insurance provider integrations"""
    
    def __init__(self, provider_name: str, config: Optional[Dict[str, Any]] = None):
        self.provider_name = provider_name
        self.config = config or {}
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    @abstractmethod
    async def check_eligibility(
        self,
        request: InsuranceVerificationRequest
    ) -> InsuranceVerificationResult:
        """Check insurance eligibility for a member"""
        pass
    
    @abstractmethod
    async def request_prior_auth(
        self,
        request: PriorAuthRequest
    ) -> PriorAuthResult:
        """Request prior authorization"""
        pass
    
    @abstractmethod
    async def inquire_benefits(
        self,
        request: BenefitsInquiryRequest
    ) -> BenefitsInquiryResult:
        """Inquire about member benefits"""
        pass
    
    async def _make_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None
    ) -> ProviderResponse:
        """Make HTTP request to insurance provider API"""
        
        start_time = time.time()
        
        try:
            response = await self.client.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params
            )
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            return ProviderResponse(
                provider_name=self.provider_name,
                response_code=str(response.status_code),
                response_message=response.reason_phrase,
                raw_response=response.json() if response.content else None,
                processing_time_ms=processing_time_ms
            )
            
        except httpx.TimeoutException:
            logger.error(f"Timeout calling {self.provider_name} API at {url}")
            return ProviderResponse(
                provider_name=self.provider_name,
                response_code="TIMEOUT",
                response_message="Request timed out",
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
            
        except httpx.RequestError as e:
            logger.error(f"Request error calling {self.provider_name} API: {e}")
            return ProviderResponse(
                provider_name=self.provider_name,
                response_code="REQUEST_ERROR",
                response_message=str(e),
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
            
        except Exception as e:
            logger.error(f"Unexpected error calling {self.provider_name} API: {e}")
            return ProviderResponse(
                provider_name=self.provider_name,
                response_code="UNKNOWN_ERROR",
                response_message=str(e),
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
    
    def _validate_member_id(self, member_id: str) -> bool:
        """Validate member ID format for this provider"""
        # Basic validation - override in specific providers
        return bool(member_id and len(member_id) >= 6)
    
    def _sanitize_phi_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove or mask PHI from data before logging/storage"""
        sanitized = data.copy()
        
        # Common PHI fields to sanitize
        phi_fields = ['ssn', 'dob', 'phone', 'address', 'email', 'member_id']
        
        for field in phi_fields:
            if field in sanitized:
                if isinstance(sanitized[field], str) and len(sanitized[field]) > 4:
                    sanitized[field] = sanitized[field][:2] + "*" * (len(sanitized[field]) - 4) + sanitized[field][-2:]
                else:
                    sanitized[field] = "[MASKED]"
        
        return sanitized
    
    def _generate_verification_id(self) -> str:
        """Generate unique verification ID"""
        import uuid
        return f"{self.provider_name.lower()}_{uuid.uuid4().hex[:8]}"
    
    def _generate_auth_id(self) -> str:
        """Generate unique prior auth ID"""
        import uuid
        return f"{self.provider_name.lower()}_auth_{uuid.uuid4().hex[:8]}"
    
    def _generate_inquiry_id(self) -> str:
        """Generate unique benefits inquiry ID"""
        import uuid
        return f"{self.provider_name.lower()}_inquiry_{uuid.uuid4().hex[:8]}"