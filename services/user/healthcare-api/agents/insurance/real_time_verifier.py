"""
Real-Time Insurance Verification System - Updated with Configuration

Provides real-time insurance verification with multiple provider APIs,
cost estimation, and prior authorization automation using configuration files.
"""

import asyncio
import hashlib
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from cachetools import TTLCache

from config.config_loader import get_healthcare_config
from core.infrastructure.agent_metrics import AgentMetricsStore
from core.infrastructure.healthcare_cache import HealthcareCacheManager
from core.infrastructure.healthcare_logger import get_healthcare_logger
from core.infrastructure.phi_monitor import phi_monitor_decorator

logger = get_healthcare_logger(__name__)

@dataclass
class InsuranceVerificationResult:
    """Comprehensive insurance verification result"""
    verified: bool
    provider: str | None = None
    member_id: str | None = None
    coverage_active: bool = False
    coverage_details: list[Any] = None
    cost_estimates: dict[str, float] = None
    copay_amounts: dict[str, float] = None
    deductible_remaining: float = 0.0
    out_of_pocket_max: float = 0.0
    out_of_pocket_met: float = 0.0
    verified_at: datetime | None = None
    error: str | None = None

@dataclass
class PriorAuthResult:
    """Prior authorization request result"""
    status: str
    tracking_id: str | None = None
    estimated_decision_date: date | None = None
    reference_number: str | None = None
    message: str | None = None

@dataclass
class EligibilityResponse:
    """Mock eligibility response structure"""
    is_active: bool
    deductible_remaining: float
    out_of_pocket_max: float
    out_of_pocket_met: float
    plan_type: str
    effective_date: date
    termination_date: date | None = None

@dataclass
class CoverageResponse:
    """Mock coverage response structure"""
    covered: bool
    copay: float
    coinsurance_rate: float
    estimated_charge: float
    requires_prior_auth: bool = False

class RealTimeInsuranceVerifier:
    """
    Real-time insurance verification with multiple provider APIs using configuration
    """

    def __init__(self):
        # Load configuration
        self.config = get_healthcare_config().insurance

        # Initialize provider clients based on configuration
        self.provider_clients = {}
        for provider_name, provider_config in self.config.providers.items():
            self.provider_clients[provider_name] = ConfigurableAPIClient(provider_config)

        # Configure caching from configuration
        cache_config = self.config.cache
        cache_ttl = cache_config.get("verification_cache_ttl_seconds", 1800)
        cache_size = cache_config.get("max_cache_size", 500)
        self.verification_cache = TTLCache(maxsize=cache_size, ttl=cache_ttl)

        self.cache_manager = HealthcareCacheManager()
        self.metrics = AgentMetricsStore(agent_name="real_time_insurance_verifier")

    @phi_monitor_decorator
    async def verify_insurance_real_time(
        self,
        patient_info: dict[str, Any],
        service_codes: list[str],
    ) -> InsuranceVerificationResult:
        """
        Perform real-time insurance verification for multiple services
        """

        insurance_info = patient_info.get("insurance", {})
        provider = insurance_info.get("provider", "").lower()
        member_id = insurance_info.get("member_id")

        if not provider or not member_id:
            await self.metrics.incr("verification_validation_errors")
            return InsuranceVerificationResult(
                verified=False,
                error="Missing required insurance information (provider or member_id)",
            )

        # Check cache first
        cache_key = hashlib.md5(f"{provider}_{member_id}_{'-'.join(service_codes)}".encode()).hexdigest()
        if cache_key in self.verification_cache:
            await self.metrics.incr("verification_cache_hits")
            return self.verification_cache[cache_key]

        try:
            # Find provider client
            if provider not in self.provider_clients:
                await self.metrics.incr("verification_provider_not_found")
                return InsuranceVerificationResult(
                    verified=False,
                    error=f"Insurance provider '{provider}' not supported",
                )

            api_client = self.provider_clients[provider]

            # Check eligibility first
            eligibility = await api_client.check_eligibility(member_id, date.today())

            if not eligibility.is_active:
                await self.metrics.incr("verification_eligibility_inactive")
                result = InsuranceVerificationResult(
                    verified=False,
                    provider=provider,
                    member_id=member_id,
                    coverage_active=False,
                    error="Insurance coverage is not active",
                )
                self.verification_cache[cache_key] = result
                return result

            # Check coverage for each service
            coverage_results = []
            for service_code in service_codes:
                coverage = await api_client.check_service_coverage(
                    member_id,
                    service_code,
                    provider_npi=patient_info.get("provider_npi"),
                )
                coverage_results.append(coverage)

            # Calculate cost estimates
            cost_estimates = await self._calculate_cost_estimates(service_codes, coverage_results, eligibility)

            result = InsuranceVerificationResult(
                verified=True,
                provider=provider,
                member_id=member_id,
                coverage_active=eligibility.is_active,
                coverage_details=[{
                    "service_code": code,
                    "covered": coverage.covered,
                    "copay": coverage.copay,
                    "coinsurance_rate": coverage.coinsurance_rate,
                    "requires_prior_auth": coverage.requires_prior_auth,
                } for code, coverage in zip(service_codes, coverage_results, strict=False)],
                cost_estimates=cost_estimates,
                copay_amounts={code: coverage.copay for code, coverage in zip(service_codes, coverage_results, strict=False)},
                deductible_remaining=eligibility.deductible_remaining,
                out_of_pocket_max=eligibility.out_of_pocket_max,
                out_of_pocket_met=eligibility.out_of_pocket_met,
                verified_at=datetime.now(),
            )

            # Cache successful result
            self.verification_cache[cache_key] = result
            await self.metrics.incr("verification_success")

            return result

        except Exception as e:
            await self.metrics.incr("verification_errors")
            logger.exception(f"Insurance verification error: {e}")
            return InsuranceVerificationResult(
                verified=False,
                provider=provider,
                member_id=member_id,
                error=f"Verification failed: {str(e)}",
            )

    async def request_prior_authorization(
        self,
        patient_info: dict[str, Any],
        service_codes: list[str],
        medical_justification: str,
    ) -> PriorAuthResult:
        """Request prior authorization for services"""

        insurance_info = patient_info.get("insurance", {})
        provider = insurance_info.get("provider", "").lower()

        if provider not in self.provider_clients:
            return PriorAuthResult(
                status="rejected",
                message=f"Provider '{provider}' not supported for prior authorization",
            )

        # Simulate prior authorization request
        tracking_id = f"PA_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{provider}"
        estimated_decision_date = date.today() + timedelta(days=3)

        await self.metrics.incr("prior_auth_requests")

        return PriorAuthResult(
            status="submitted",
            tracking_id=tracking_id,
            estimated_decision_date=estimated_decision_date,
            reference_number=f"REF_{tracking_id}",
            message="Prior authorization request submitted successfully",
        )

    async def _calculate_cost_estimates(
        self,
        service_codes: list[str],
        coverage_results: list[CoverageResponse],
        eligibility: EligibilityResponse,
    ) -> dict[str, float]:
        """Calculate estimated patient costs for services"""

        cost_estimates = {}

        for service_code, coverage in zip(service_codes, coverage_results, strict=False):
            if coverage.covered:
                # Calculate patient responsibility
                if coverage.copay > 0:
                    patient_cost = coverage.copay
                elif coverage.coinsurance_rate > 0:
                    estimated_charge = coverage.estimated_charge or 100.0  # Default estimate
                    patient_cost = estimated_charge * coverage.coinsurance_rate
                else:
                    patient_cost = 0.0

                # Apply deductible if not met
                if eligibility.deductible_remaining > 0:
                    deductible_portion = min(patient_cost, eligibility.deductible_remaining)
                    patient_cost = max(patient_cost, deductible_portion)

                cost_estimates[service_code] = patient_cost
            else:
                cost_estimates[service_code] = coverage.estimated_charge or 0.0

        return cost_estimates


# Configuration-based API Client
class ConfigurableAPIClient:
    """Insurance API client that uses configuration for all responses"""

    def __init__(self, provider_config):
        self.config = provider_config
        self.api_delay = self.config.api_delay_seconds
        self.eligibility_config = self.config.eligibility
        self.coverage_rules = self.config.coverage_rules
        self.default_coverage = self.config.default_coverage

    async def check_eligibility(self, member_id: str, service_date: date) -> EligibilityResponse:
        """Check member eligibility using configuration"""
        await asyncio.sleep(self.api_delay)

        return EligibilityResponse(
            is_active=True,
            deductible_remaining=float(self.eligibility_config.get("deductible_remaining", 500.0)),
            out_of_pocket_max=float(self.eligibility_config.get("out_of_pocket_max", 2000.0)),
            out_of_pocket_met=float(self.eligibility_config.get("out_of_pocket_met", 300.0)),
            plan_type=self.eligibility_config.get("plan_type", "PPO"),
            effective_date=date.fromisoformat(self.eligibility_config.get("effective_date", "2024-01-01")),
        )

    async def check_service_coverage(
        self,
        member_id: str,
        service_code: str,
        provider_npi: str,
    ) -> CoverageResponse:
        """Check coverage for specific service using configuration"""
        await asyncio.sleep(self.api_delay / 2)

        if service_code in self.coverage_rules:
            rule = self.coverage_rules[service_code]
            return CoverageResponse(
                covered=rule.get("covered", True),
                copay=float(rule.get("copay", 0.0)),
                coinsurance_rate=float(rule.get("coinsurance_rate", 0.0)),
                estimated_charge=float(rule.get("estimated_charge", 150.0)),
                requires_prior_auth=rule.get("requires_prior_auth", False),
            )

        # Use default coverage if specific rule not found
        return CoverageResponse(
            covered=self.default_coverage.get("covered", True),
            copay=float(self.default_coverage.get("copay", 30.0)),
            coinsurance_rate=float(self.default_coverage.get("coinsurance_rate", 0.2)),
            estimated_charge=float(self.default_coverage.get("estimated_charge", 150.0)),
            requires_prior_auth=self.default_coverage.get("requires_prior_auth", False),
        )
