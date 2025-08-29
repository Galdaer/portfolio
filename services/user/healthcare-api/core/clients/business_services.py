"""
Business Services HTTP Client

Provides a centralized HTTP client for communicating with business microservices
including circuit breaker, retry logic, and PHI-safe logging.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from urllib.parse import urljoin

import aiohttp
import yaml
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class ServiceResponse(BaseModel):
    """Standardized response from business services"""
    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None
    service: str
    endpoint: str
    timestamp: datetime
    session_id: str | None = None


class CircuitBreaker:
    """Circuit breaker implementation for service resilience"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60, half_open_max_calls: int = 3):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
        self.half_open_calls = 0

    def can_request(self) -> bool:
        """Check if requests are allowed"""
        if self.state == CircuitBreakerState.CLOSED:
            return True

        if self.state == CircuitBreakerState.OPEN:
            if self.last_failure_time and datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout):
                self.state = CircuitBreakerState.HALF_OPEN
                self.half_open_calls = 0
                return True
            return False

        if self.state == CircuitBreakerState.HALF_OPEN:
            return self.half_open_calls < self.half_open_max_calls

        return False

    def record_success(self):
        """Record successful request"""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.CLOSED
            self.failure_count = 0
        self.failure_count = 0

    def record_failure(self):
        """Record failed request"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.state == CircuitBreakerState.HALF_OPEN or self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN


class BusinessServicesClient:
    """HTTP client for business microservices with resilience patterns"""

    def __init__(self, config_path: str = "/app/config/business_services.yml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.session = None
        self.circuit_breakers = {}
        self._initialize_circuit_breakers()

    def _load_config(self) -> dict[str, Any]:
        """Load business services configuration"""
        try:
            with open(self.config_path) as f:
                config = yaml.safe_load(f)

            # Apply environment-specific overrides
            environment = self._get_environment()
            if environment in config.get("environments", {}):
                env_config = config["environments"][environment]

                # Merge global settings
                if "global" in env_config:
                    config["global"].update(env_config["global"])

                # Merge service settings
                if "services" in env_config:
                    for service_name, service_config in env_config["services"].items():
                        if service_name in config["services"]:
                            config["services"][service_name].update(service_config)

            return config
        except Exception as e:
            logger.exception(f"Failed to load business services config: {e}")
            raise

    def _get_environment(self) -> str:
        """Detect current environment"""
        import os
        return os.getenv("ENVIRONMENT", "development")

    def _initialize_circuit_breakers(self):
        """Initialize circuit breakers for each service"""
        global_cb_config = self.config.get("global", {}).get("circuit_breaker", {})

        for service_name in self.config["services"]:
            self.circuit_breakers[service_name] = CircuitBreaker(
                failure_threshold=global_cb_config.get("failure_threshold", 5),
                recovery_timeout=global_cb_config.get("recovery_timeout", 60),
                half_open_max_calls=global_cb_config.get("half_open_max_calls", 3),
            )

    async def __aenter__(self):
        """Async context manager entry"""
        timeout = aiohttp.ClientTimeout(total=60)  # Default timeout
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def _make_request(
        self,
        service_name: str,
        endpoint: str,
        method: str = "POST",
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        timeout: int | None = None,
    ) -> ServiceResponse:
        """Make HTTP request with circuit breaker and retry logic"""

        if service_name not in self.config["services"]:
            msg = f"Unknown service: {service_name}"
            raise ValueError(msg)

        service_config = self.config["services"][service_name]
        circuit_breaker = self.circuit_breakers[service_name]

        # Check circuit breaker
        if not circuit_breaker.can_request():
            return ServiceResponse(
                success=False,
                error="Circuit breaker is open",
                service=service_name,
                endpoint=endpoint,
                timestamp=datetime.now(),
            )

        # Build URL
        base_url = service_config["url"]
        full_url = urljoin(base_url, endpoint)

        # Get timeout
        request_timeout = timeout or service_config.get("timeout", 30)

        # Retry logic
        retry_attempts = service_config.get("retry_attempts", 3)
        retry_delay = service_config.get("retry_delay", 1.0)

        last_error = None

        for attempt in range(retry_attempts):
            try:
                # Log request (PHI-safe)
                if self.config.get("global", {}).get("logging", {}).get("log_requests", True):
                    logger.info(f"Request to {service_name}{endpoint} (attempt {attempt + 1})")

                async with self.session.request(
                    method,
                    full_url,
                    json=data,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=request_timeout),
                ) as response:

                    response_data = await response.json()

                    if response.status == 200:
                        circuit_breaker.record_success()

                        # Log successful response (only in development/testing)
                        if self.config.get("global", {}).get("logging", {}).get("log_responses", False):
                            logger.debug(f"Successful response from {service_name}{endpoint}")

                        return ServiceResponse(
                            success=True,
                            data=response_data,
                            service=service_name,
                            endpoint=endpoint,
                            timestamp=datetime.now(),
                        )
                    error_msg = f"HTTP {response.status}: {response_data.get('detail', 'Unknown error')}"
                    last_error = error_msg

                    if self.config.get("global", {}).get("logging", {}).get("log_errors", True):
                        logger.warning(f"Request failed: {error_msg}")

            except TimeoutError:
                last_error = "Request timeout"
                if self.config.get("global", {}).get("logging", {}).get("log_errors", True):
                    logger.warning(f"Request to {service_name}{endpoint} timed out")

            except Exception as e:
                last_error = str(e)
                if self.config.get("global", {}).get("logging", {}).get("log_errors", True):
                    logger.exception(f"Request to {service_name}{endpoint} failed: {e}")

            # Wait before retry (except on last attempt)
            if attempt < retry_attempts - 1:
                await asyncio.sleep(retry_delay)

        # All attempts failed
        circuit_breaker.record_failure()

        return ServiceResponse(
            success=False,
            error=last_error or "All retry attempts failed",
            service=service_name,
            endpoint=endpoint,
            timestamp=datetime.now(),
        )

    # Insurance Verification Service Methods
    async def verify_insurance(self, request_data: dict[str, Any]) -> ServiceResponse:
        """Verify insurance eligibility"""
        return await self._make_request(
            service_name="insurance_verification",
            endpoint="/verify",
            data=request_data,
        )

    async def request_prior_auth(self, request_data: dict[str, Any]) -> ServiceResponse:
        """Request prior authorization"""
        return await self._make_request(
            service_name="insurance_verification",
            endpoint="/prior-auth",
            data=request_data,
        )

    async def inquire_benefits(self, request_data: dict[str, Any]) -> ServiceResponse:
        """Inquire about member benefits"""
        return await self._make_request(
            service_name="insurance_verification",
            endpoint="/benefits",
            data=request_data,
        )

    # Billing Engine Service Methods
    async def process_claim(self, claim_data: dict[str, Any]) -> ServiceResponse:
        """Process healthcare claim"""
        return await self._make_request(
            service_name="billing_engine",
            endpoint="/claims/process",
            data=claim_data,
        )

    async def track_payment(self, payment_data: dict[str, Any]) -> ServiceResponse:
        """Track payment status"""
        return await self._make_request(
            service_name="billing_engine",
            endpoint="/payments/track",
            data=payment_data,
        )

    async def validate_codes(self, codes_data: dict[str, Any]) -> ServiceResponse:
        """Validate medical codes"""
        return await self._make_request(
            service_name="billing_engine",
            endpoint="/codes/validate",
            data=codes_data,
        )

    async def generate_invoice(self, invoice_data: dict[str, Any]) -> ServiceResponse:
        """Generate patient invoice"""
        return await self._make_request(
            service_name="billing_engine",
            endpoint="/invoices/generate",
            data=invoice_data,
        )

    async def create_estimate(self, estimate_data: dict[str, Any]) -> ServiceResponse:
        """Create cost estimate"""
        return await self._make_request(
            service_name="billing_engine",
            endpoint="/estimates/create",
            data=estimate_data,
        )

    # Compliance Monitor Service Methods
    async def log_audit_event(self, event_data: dict[str, Any]) -> ServiceResponse:
        """Log audit event for compliance tracking"""
        return await self._make_request(
            service_name="compliance_monitor",
            endpoint="/audit/log",
            data=event_data,
        )

    async def check_compliance(self, check_data: dict[str, Any]) -> ServiceResponse:
        """Check compliance status"""
        return await self._make_request(
            service_name="compliance_monitor",
            endpoint="/audit/check",
            data=check_data,
        )

    async def scan_phi(self, text_data: dict[str, Any]) -> ServiceResponse:
        """Scan text for PHI"""
        return await self._make_request(
            service_name="compliance_monitor",
            endpoint="/audit/phi-scan",
            data=text_data,
        )

    # Business Intelligence Service Methods
    async def get_analytics(self, analytics_request: dict[str, Any]) -> ServiceResponse:
        """Get analytics data"""
        return await self._make_request(
            service_name="business_intelligence",
            endpoint="/analytics",
            data=analytics_request,
            timeout=60,  # Longer timeout for analytics
        )

    async def get_metrics(self, metrics_request: dict[str, Any]) -> ServiceResponse:
        """Get metrics data"""
        return await self._make_request(
            service_name="business_intelligence",
            endpoint="/metrics",
            data=metrics_request,
        )

    async def generate_report(self, report_request: dict[str, Any]) -> ServiceResponse:
        """Generate business intelligence report"""
        return await self._make_request(
            service_name="business_intelligence",
            endpoint="/reports",
            data=report_request,
            timeout=120,  # Longer timeout for reports
        )

    # Doctor Personalization Service Methods
    async def personalize_response(self, personalization_data: dict[str, Any]) -> ServiceResponse:
        """Personalize AI response for specific doctor"""
        return await self._make_request(
            service_name="doctor_personalization",
            endpoint="/personalize",
            data=personalization_data,
        )

    async def submit_feedback(self, feedback_data: dict[str, Any]) -> ServiceResponse:
        """Submit feedback for model improvement"""
        return await self._make_request(
            service_name="doctor_personalization",
            endpoint="/feedback",
            data=feedback_data,
        )

    async def get_preferences(self, doctor_id: str) -> ServiceResponse:
        """Get doctor preferences"""
        return await self._make_request(
            service_name="doctor_personalization",
            endpoint="/preferences",
            method="GET",
            params={"doctor_id": doctor_id},
        )

    # Health Check Methods
    async def check_service_health(self, service_name: str) -> ServiceResponse:
        """Check health of specific service"""
        if service_name not in self.config["services"]:
            return ServiceResponse(
                success=False,
                error=f"Unknown service: {service_name}",
                service=service_name,
                endpoint="/health",
                timestamp=datetime.now(),
            )

        return await self._make_request(
            service_name=service_name,
            endpoint="/health",
            method="GET",
            timeout=10,
        )

    async def check_all_services_health(self) -> dict[str, ServiceResponse]:
        """Check health of all business services"""
        health_checks = {}

        for service_name in self.config["services"]:
            health_checks[service_name] = await self.check_service_health(service_name)

        return health_checks


# Singleton instance for easy importing
business_client = None


def get_business_client() -> BusinessServicesClient:
    """Get singleton business services client instance"""
    global business_client
    if business_client is None:
        business_client = BusinessServicesClient()
    return business_client
