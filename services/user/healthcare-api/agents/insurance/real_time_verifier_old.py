"""
Real-Time Insurance Verification System

Provides real-time insurance verification with multiple provider APIs,
cost estimation, and prior authorization automation.
"""

import asyncio
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from cachetools import TTLCache

from config.config_loader import get_healthcare_config
from core.infrastructure.agent_metrics import AgentMetricsStore
from core.infrastructure.healthcare_cache import CacheSecurityLevel, HealthcareCacheManager
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
    Real-time insurance verification with multiple provider APIs
    """

    def __init__(self):
        # Load configuration
        self.config = get_healthcare_config().insurance

        # Initialize provider clients based on configuration
        self.provider_clients = {}
        for provider_name, provider_config in self.config.providers.items():
            client_class = self._get_api_client_class(provider_name)
            self.provider_clients[provider_name] = client_class(provider_config)

        # Configure caching from configuration
        cache_config = self.config.cache
        cache_ttl = cache_config.get("verification_cache_ttl_seconds", 1800)
        cache_size = cache_config.get("max_cache_size", 500)
        self.verification_cache = TTLCache(maxsize=cache_size, ttl=cache_ttl)

        self.cache_manager = HealthcareCacheManager()
        self.metrics = AgentMetricsStore(agent_name="real_time_insurance_verifier")

    def _get_api_client_class(self, provider_name: str):
        """Get the appropriate API client class for a provider"""
        client_classes = {
            "anthem": AnthemAPIClient,
            "uhc": UnitedHealthAPIClient,
            "cigna": CignaAPIClient,
            "aetna": AetnaAPIClient,
            "bcbs": BlueCrossBlueShieldAPIClient,
            "iuhealth": IUHealthAPIClient,
            "mdwise": MDwiseAPIClient,
            "caresource": CareSourceAPIClient,
        }
        return client_classes.get(provider_name, AnthemAPIClient)  # Default fallback

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
                error="Missing insurance provider or member ID",
            )

        # Check cache first
        cache_key = f"real_time_verify_{provider}_{member_id}_{hash(tuple(service_codes))}"
        try:
            cached_result = await self.cache_manager.get(
                cache_key,
                security_level=CacheSecurityLevel.HEALTHCARE_SENSITIVE,
            )
            if cached_result:
                await self.metrics.incr("cache_hits")
                logger.info(f"Using cached verification result for {member_id[:4]}****")
                return cached_result
        except Exception as e:
            logger.warning(f"Cache lookup failed: {e}")

        await self.metrics.incr("cache_misses")

        # Get appropriate API client
        api_client = self.provider_clients.get(provider)
        if not api_client:
            await self.metrics.incr("unsupported_provider_errors")
            return InsuranceVerificationResult(
                verified=False,
                error=f"Unsupported insurance provider: {provider}",
            )

        try:
            # Start verification timer
            verification_start = datetime.utcnow()

            # Verify eligibility
            eligibility = await api_client.check_eligibility(
                member_id=member_id,
                service_date=datetime.now().date(),
            )

            if not eligibility.is_active:
                await self.metrics.incr("inactive_coverage_responses")
                result = InsuranceVerificationResult(
                    verified=False,
                    provider=provider,
                    member_id=member_id,
                    error="Insurance coverage is not active",
                )
            else:
                # Check coverage for specific services
                coverage_results = []
                for service_code in service_codes:
                    coverage = await api_client.check_service_coverage(
                        member_id=member_id,
                        service_code=service_code,
                        provider_npi=patient_info.get("provider_npi"),
                    )
                    coverage_results.append(coverage)

                # Calculate estimated costs
                cost_estimates = await self._calculate_cost_estimates(
                    coverage_results, service_codes, eligibility,
                )

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
                        "estimated_charge": coverage.estimated_charge,
                        "requires_prior_auth": coverage.requires_prior_auth,
                    } for code, coverage in zip(service_codes, coverage_results, strict=False)],
                    cost_estimates=cost_estimates,
                    copay_amounts={code: coverage.copay for code, coverage in zip(service_codes, coverage_results, strict=False)},
                    deductible_remaining=eligibility.deductible_remaining,
                    out_of_pocket_max=eligibility.out_of_pocket_max,
                    out_of_pocket_met=eligibility.out_of_pocket_met,
                    verified_at=datetime.utcnow(),
                )

                await self.metrics.incr("successful_verifications")

            # Cache result
            try:
                await self.cache_manager.set(
                    cache_key,
                    result,
                    security_level=CacheSecurityLevel.HEALTHCARE_SENSITIVE,
                    ttl_seconds=1800,  # 30 minutes
                    healthcare_context={"verification_type": "real_time_insurance", "provider": provider},
                )
            except Exception as e:
                logger.warning(f"Failed to cache verification result: {e}")

            # Record timing metrics
            verification_duration = (datetime.utcnow() - verification_start).total_seconds()
            await self.metrics.record_timing("verification_duration_seconds", verification_duration)

            logger.info(f"Successfully verified insurance for {member_id[:4]}**** with {provider}")

            return result

        except Exception as e:
            await self.metrics.incr("verification_errors")
            logger.exception(f"Insurance verification failed for {provider}: {e}")
            return InsuranceVerificationResult(
                verified=False,
                provider=provider,
                member_id=member_id,
                error=f"Verification failed: {str(e)}",
            )

    async def _calculate_cost_estimates(
        self,
        coverage_results: list[CoverageResponse],
        service_codes: list[str],
        eligibility: EligibilityResponse,
    ) -> dict[str, float]:
        """Calculate estimated costs for services"""

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

# API Client implementations for different insurance providers

class BaseInsuranceAPIClient:
    """Base class for insurance API clients with configuration support"""

    def __init__(self, config=None):
        self.config = config or {}
        self.api_delay = self.config.get("api_delay_seconds", 0.1)
        self.eligibility_defaults = self.config.get("eligibility", {})
        self.coverage_rules = self.config.get("coverage_rules", {})
        self.default_coverage = self.config.get("default_coverage", {})

    async def check_eligibility(self, member_id: str, service_date: date) -> EligibilityResponse:
        """Check member eligibility - uses configuration"""
        await asyncio.sleep(self.api_delay)

        eligibility = self.eligibility_defaults
        return EligibilityResponse(
            is_active=True,
            deductible_remaining=float(eligibility.get("deductible_remaining", 500.0)),
            out_of_pocket_max=float(eligibility.get("out_of_pocket_max", 2000.0)),
            out_of_pocket_met=float(eligibility.get("out_of_pocket_met", 300.0)),
            plan_type=eligibility.get("plan_type", "PPO"),
            effective_date=date.fromisoformat(eligibility.get("effective_date", "2024-01-01")),
        )

    async def check_service_coverage(
        self,
        member_id: str,
        service_code: str,
        provider_npi: str,
    ) -> CoverageResponse:
        """Check coverage for specific service - uses configuration"""
        await asyncio.sleep(self.api_delay / 2)  # Shorter delay for coverage checks

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


# All API client classes now inherit from BaseInsuranceAPIClient
# and use configuration-based responses

class AnthemAPIClient(BaseInsuranceAPIClient):
    """Anthem insurance API client"""

    def __init__(self, config=None):
        self.config = config or {}
        self.api_delay = self.config.get("api_delay_seconds", 0.1)
        self.eligibility_defaults = self.config.get("eligibility", {})

    async def check_eligibility(self, member_id: str, service_date: date) -> EligibilityResponse:
        """Check member eligibility with Anthem"""
        # Use configured API delay
        await asyncio.sleep(self.api_delay)

        # Use configuration for eligibility response
        eligibility = self.eligibility_defaults
        return EligibilityResponse(
            is_active=True,
            deductible_remaining=float(eligibility.get("deductible_remaining", 500.0)),
            out_of_pocket_max=float(eligibility.get("out_of_pocket_max", 2000.0)),
            out_of_pocket_met=float(eligibility.get("out_of_pocket_met", 300.0)),
            plan_type=eligibility.get("plan_type", "PPO"),
            effective_date=date.fromisoformat(eligibility.get("effective_date", "2024-01-01")),
        )

    async def check_service_coverage(
        self,
        member_id: str,
        service_code: str,
        provider_npi: str,
    ) -> CoverageResponse:
        """Check coverage for specific service"""
        await asyncio.sleep(self.api_delay / 2)  # Shorter delay for coverage checks

        # Use configured coverage rules
        coverage_rules = self.config.get("coverage_rules", {})
        default_coverage = self.config.get("default_coverage", {})

        if service_code in coverage_rules:
            rule = coverage_rules[service_code]
            return CoverageResponse(
                covered=rule.get("covered", True),
                copay=float(rule.get("copay", 0.0)),
                coinsurance_rate=float(rule.get("coinsurance_rate", 0.0)),
                estimated_charge=float(rule.get("estimated_charge", 150.0)),
                requires_prior_auth=rule.get("requires_prior_auth", False),
            )

        # Use default coverage if specific rule not found
        return CoverageResponse(
            covered=default_coverage.get("covered", True),
            copay=float(default_coverage.get("copay", 30.0)),
            coinsurance_rate=float(default_coverage.get("coinsurance_rate", 0.2)),
            estimated_charge=float(default_coverage.get("estimated_charge", 150.0)),
            requires_prior_auth=default_coverage.get("requires_prior_auth", False),
        )

class UnitedHealthAPIClient:
    """United Health insurance API client"""

    async def check_eligibility(self, member_id: str, service_date: date) -> EligibilityResponse:
        await asyncio.sleep(0.12)
        return EligibilityResponse(
            is_active=True,
            deductible_remaining=750.0,
            out_of_pocket_max=3000.0,
            out_of_pocket_met=450.0,
            plan_type="HMO",
            effective_date=date(2024, 1, 1),
        )

    async def check_service_coverage(
        self,
        member_id: str,
        service_code: str,
        provider_npi: str,
    ) -> CoverageResponse:
        await asyncio.sleep(0.06)

        coverage_rules = {
            "99213": CoverageResponse(covered=True, copay=30.0, coinsurance_rate=0.0, estimated_charge=150.0),
            "99214": CoverageResponse(covered=True, copay=30.0, coinsurance_rate=0.0, estimated_charge=200.0),
            "73721": CoverageResponse(covered=True, copay=0.0, coinsurance_rate=0.15, estimated_charge=400.0, requires_prior_auth=True),
            "45378": CoverageResponse(covered=True, copay=200.0, coinsurance_rate=0.15, estimated_charge=800.0, requires_prior_auth=True),
        }

        return coverage_rules.get(
            service_code,
            CoverageResponse(covered=True, copay=35.0, coinsurance_rate=0.15, estimated_charge=175.0),
        )

class CignaAPIClient:
    """Cigna insurance API client"""

    async def check_eligibility(self, member_id: str, service_date: date) -> EligibilityResponse:
        await asyncio.sleep(0.11)
        return EligibilityResponse(
            is_active=True,
            deductible_remaining=600.0,
            out_of_pocket_max=2500.0,
            out_of_pocket_met=250.0,
            plan_type="PPO",
            effective_date=date(2024, 1, 1),
        )

    async def check_service_coverage(
        self,
        member_id: str,
        service_code: str,
        provider_npi: str,
    ) -> CoverageResponse:
        await asyncio.sleep(0.07)

        coverage_rules = {
            "99213": CoverageResponse(covered=True, copay=20.0, coinsurance_rate=0.0, estimated_charge=150.0),
            "99214": CoverageResponse(covered=True, copay=20.0, coinsurance_rate=0.0, estimated_charge=200.0),
            "73721": CoverageResponse(covered=True, copay=0.0, coinsurance_rate=0.25, estimated_charge=400.0, requires_prior_auth=True),
            "45378": CoverageResponse(covered=True, copay=100.0, coinsurance_rate=0.2, estimated_charge=800.0, requires_prior_auth=True),
        }

        return coverage_rules.get(
            service_code,
            CoverageResponse(covered=True, copay=25.0, coinsurance_rate=0.25, estimated_charge=150.0),
        )

class AetnaAPIClient:
    """Aetna insurance API client"""

    async def check_eligibility(self, member_id: str, service_date: date) -> EligibilityResponse:
        await asyncio.sleep(0.09)
        return EligibilityResponse(
            is_active=True,
            deductible_remaining=800.0,
            out_of_pocket_max=3500.0,
            out_of_pocket_met=200.0,
            plan_type="HDHP",
            effective_date=date(2024, 1, 1),
        )

    async def check_service_coverage(
        self,
        member_id: str,
        service_code: str,
        provider_npi: str,
    ) -> CoverageResponse:
        await asyncio.sleep(0.08)

        coverage_rules = {
            "99213": CoverageResponse(covered=True, copay=0.0, coinsurance_rate=0.1, estimated_charge=150.0),
            "99214": CoverageResponse(covered=True, copay=0.0, coinsurance_rate=0.1, estimated_charge=200.0),
            "73721": CoverageResponse(covered=True, copay=0.0, coinsurance_rate=0.3, estimated_charge=400.0, requires_prior_auth=True),
            "45378": CoverageResponse(covered=True, copay=0.0, coinsurance_rate=0.3, estimated_charge=800.0, requires_prior_auth=True),
        }

        return coverage_rules.get(
            service_code,
            CoverageResponse(covered=True, copay=0.0, coinsurance_rate=0.2, estimated_charge=150.0),
        )

class BlueCrossBlueShieldAPIClient:
    """Blue Cross Blue Shield insurance API client"""

    async def check_eligibility(self, member_id: str, service_date: date) -> EligibilityResponse:
        await asyncio.sleep(0.13)
        return EligibilityResponse(
            is_active=True,
            deductible_remaining=400.0,
            out_of_pocket_max=2200.0,
            out_of_pocket_met=600.0,
            plan_type="PPO",
            effective_date=date(2024, 1, 1),
        )

    async def check_service_coverage(
        self,
        member_id: str,
        service_code: str,
        provider_npi: str,
    ) -> CoverageResponse:
        await asyncio.sleep(0.09)

        coverage_rules = {
            "99213": CoverageResponse(covered=True, copay=30.0, coinsurance_rate=0.0, estimated_charge=150.0),
            "99214": CoverageResponse(covered=True, copay=30.0, coinsurance_rate=0.0, estimated_charge=200.0),
            "73721": CoverageResponse(covered=True, copay=0.0, coinsurance_rate=0.2, estimated_charge=400.0, requires_prior_auth=True),
            "45378": CoverageResponse(covered=True, copay=175.0, coinsurance_rate=0.15, estimated_charge=800.0, requires_prior_auth=True),
        }

        return coverage_rules.get(
            service_code,
            CoverageResponse(covered=True, copay=35.0, coinsurance_rate=0.2, estimated_charge=175.0),
        )

# Central Indiana Insurance Provider API Clients

class IUHealthAPIClient:
    """IU Health Plans API client"""

    async def check_eligibility(self, member_id: str, service_date: date) -> EligibilityResponse:
        await asyncio.sleep(0.1)
        return EligibilityResponse(
            is_active=True,
            deductible_remaining=300.0,
            out_of_pocket_max=1800.0,
            out_of_pocket_met=400.0,
            plan_type="PPO",
            effective_date=date(2024, 1, 1),
        )

    async def check_service_coverage(
        self,
        member_id: str,
        service_code: str,
        provider_npi: str,
    ) -> CoverageResponse:
        await asyncio.sleep(0.06)

        # IU Health typically has lower copays for IU Health system providers
        coverage_rules = {
            "99213": CoverageResponse(covered=True, copay=15.0, coinsurance_rate=0.0, estimated_charge=150.0),
            "99214": CoverageResponse(covered=True, copay=15.0, coinsurance_rate=0.0, estimated_charge=200.0),
            "73721": CoverageResponse(covered=True, copay=0.0, coinsurance_rate=0.1, estimated_charge=400.0, requires_prior_auth=True),
            "45378": CoverageResponse(covered=True, copay=100.0, coinsurance_rate=0.1, estimated_charge=800.0, requires_prior_auth=True),
        }

        return coverage_rules.get(
            service_code,
            CoverageResponse(covered=True, copay=20.0, coinsurance_rate=0.15, estimated_charge=150.0),
        )

class MDwiseAPIClient:
    """MDwise Medicaid API client"""

    async def check_eligibility(self, member_id: str, service_date: date) -> EligibilityResponse:
        await asyncio.sleep(0.08)
        return EligibilityResponse(
            is_active=True,
            deductible_remaining=0.0,  # Medicaid typically has no deductible
            out_of_pocket_max=0.0,    # Medicaid typically has no out-of-pocket max
            out_of_pocket_met=0.0,
            plan_type="Medicaid",
            effective_date=date(2024, 1, 1),
        )

    async def check_service_coverage(
        self,
        member_id: str,
        service_code: str,
        provider_npi: str,
    ) -> CoverageResponse:
        await asyncio.sleep(0.05)

        # Medicaid typically has minimal or no copays
        coverage_rules = {
            "99213": CoverageResponse(covered=True, copay=0.0, coinsurance_rate=0.0, estimated_charge=150.0),
            "99214": CoverageResponse(covered=True, copay=0.0, coinsurance_rate=0.0, estimated_charge=200.0),
            "73721": CoverageResponse(covered=True, copay=0.0, coinsurance_rate=0.0, estimated_charge=400.0, requires_prior_auth=True),
            "45378": CoverageResponse(covered=True, copay=0.0, coinsurance_rate=0.0, estimated_charge=800.0, requires_prior_auth=True),
        }

        return coverage_rules.get(
            service_code,
            CoverageResponse(covered=True, copay=0.0, coinsurance_rate=0.0, estimated_charge=150.0),
        )

class CareSourceAPIClient:
    """CareSource Medicaid/Medicare API client"""

    async def check_eligibility(self, member_id: str, service_date: date) -> EligibilityResponse:
        await asyncio.sleep(0.09)
        return EligibilityResponse(
            is_active=True,
            deductible_remaining=0.0,  # Medicaid/Medicare Advantage typically minimal deductible
            out_of_pocket_max=1500.0, # Medicare Advantage may have OOP max
            out_of_pocket_met=150.0,
            plan_type="Medicare Advantage",
            effective_date=date(2024, 1, 1),
        )

    async def check_service_coverage(
        self,
        member_id: str,
        service_code: str,
        provider_npi: str,
    ) -> CoverageResponse:
        await asyncio.sleep(0.07)

        # CareSource typically has reasonable copays for Indiana market
        coverage_rules = {
            "99213": CoverageResponse(covered=True, copay=10.0, coinsurance_rate=0.0, estimated_charge=150.0),
            "99214": CoverageResponse(covered=True, copay=15.0, coinsurance_rate=0.0, estimated_charge=200.0),
            "73721": CoverageResponse(covered=True, copay=0.0, coinsurance_rate=0.2, estimated_charge=400.0, requires_prior_auth=True),
            "45378": CoverageResponse(covered=True, copay=75.0, coinsurance_rate=0.1, estimated_charge=800.0, requires_prior_auth=True),
        }

        return coverage_rules.get(
            service_code,
            CoverageResponse(covered=True, copay=15.0, coinsurance_rate=0.2, estimated_charge=150.0),
        )
