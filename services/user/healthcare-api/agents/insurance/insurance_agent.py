"""
Healthcare Insurance Verification Agent - Administrative Insurance Support Only
Handles insurance verification, benefits checking, and prior authorization for healthcare workflows
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from agents import BaseHealthcareAgent
from core.clients.business_services import get_business_client, ServiceResponse
from core.infrastructure.agent_metrics import AgentMetricsStore
from core.infrastructure.healthcare_cache import HealthcareCacheManager
from core.infrastructure.healthcare_logger import (
    get_healthcare_logger,
    healthcare_log_method,
    log_healthcare_event,
)
from core.infrastructure.phi_monitor import phi_monitor_decorator as phi_monitor, scan_for_phi
from core.reasoning.chain_of_thought import (
    ChainOfThoughtProcessor,
    ReasoningType,
)

logger = get_healthcare_logger("agent.insurance")


@dataclass
class InsuranceVerificationResult:
    """Result from insurance verification with compliance validation"""

    verification_id: str
    status: str
    member_id: str | None
    coverage_active: bool
    benefits_summary: dict[str, Any]
    verification_errors: list[str]
    compliance_validated: bool
    timestamp: datetime
    metadata: dict[str, Any]


@dataclass
class PriorAuthResult:
    """Result from prior authorization request"""

    auth_id: str
    status: str
    reference_number: str | None
    decision_date: date | None
    approved_services: list[str]
    denied_services: list[str]
    auth_errors: list[str]
    estimated_decision_days: int
    timestamp: datetime


@dataclass
class BenefitsDetails:
    """Detailed insurance benefits information"""

    deductible_remaining: float
    out_of_pocket_max: float
    out_of_pocket_met: float
    copay_primary_care: float
    copay_specialist: float
    coinsurance_rate: float
    coverage_percentage: int
    effective_date: date
    termination_date: date | None


class InsuranceVerificationAgent(BaseHealthcareAgent):
    """
    Healthcare Insurance Verification Agent

    MEDICAL DISCLAIMER: This agent provides administrative insurance verification and benefits
    analysis support only. It assists healthcare professionals with insurance eligibility
    verification, coverage checking, and prior authorization processes. It does not provide
    medical advice, diagnosis, or treatment recommendations. All medical decisions must be
    made by qualified healthcare professionals.

    Capabilities:
    - Real-time insurance eligibility verification
    - Benefits and coverage checking
    - Prior authorization request processing
    - Claims status tracking and follow-up
    - Insurance appeal assistance
    - Coverage gap identification
    """

    def __init__(self, mcp_client=None, llm_client=None) -> None:
        super().__init__(agent_name="insurance_verification", agent_type="administrative_support")
        self.mcp_client = mcp_client
        self.llm_client = llm_client
        self.agent_type = "insurance_verification"

        # Initialize shared healthcare infrastructure tools
        self._metrics = AgentMetricsStore(agent_name="insurance_verification")
        self._cache_manager = HealthcareCacheManager()

        # Initialize Chain-of-Thought reasoning processor
        self._reasoning_processor = ChainOfThoughtProcessor(
            llm_client=llm_client,
            audit_logger=logger,
        )
        self.capabilities = [
            "eligibility_verification",
            "benefits_checking",
            "prior_authorization",
            "claims_tracking",
            "appeal_assistance",
            "coverage_analysis",
            "advanced_insurance_calculations",  # NEW: Advanced insurance features
        ]

        # Initialize insurance provider configurations
        self.supported_payers = {
            "anthem": {"api_endpoint": "mock_anthem_api", "timeout": 30},
            "united_health": {"api_endpoint": "mock_united_api", "timeout": 30},
            "aetna": {"api_endpoint": "mock_aetna_api", "timeout": 30},
            "cigna": {"api_endpoint": "mock_cigna_api", "timeout": 30},
            "bcbs": {"api_endpoint": "mock_bcbs_api", "timeout": 30},
        }

        # Log agent initialization with healthcare context
        log_healthcare_event(
            logger,
            logging.INFO,
            "Healthcare Insurance Verification Agent initialized",
            context={
                "agent": "insurance_verification",
                "initialization": True,
                "phi_monitoring": True,
                "medical_advice_disabled": True,
                "database_required": True,
                "capabilities": self.capabilities,
                "supported_payers": list(self.supported_payers.keys()),
            },
            operation_type="agent_initialization",
        )

    async def initialize(self) -> None:
        """Initialize insurance agent with database connectivity validation"""
        try:
            # Call parent initialization which validates database connectivity
            await self.initialize_agent()

            log_healthcare_event(
                logger,
                logging.INFO,
                "Insurance Verification Agent fully initialized with database connectivity",
                context={
                    "agent": "insurance_verification",
                    "database_validated": True,
                    "ready_for_operations": True,
                },
                operation_type="agent_ready",
            )
        except Exception as e:
            log_healthcare_event(
                logger,
                logging.CRITICAL,
                f"Insurance Verification Agent initialization failed: {e}",
                context={
                    "agent": "insurance_verification",
                    "initialization_failed": True,
                    "error": str(e),
                },
                operation_type="agent_initialization_error",
            )
            raise

    @healthcare_log_method(operation_type="insurance_verification", phi_risk_level="high")
    @phi_monitor(risk_level="high", operation_type="insurance_verification")
    async def verify_insurance_eligibility(
        self,
        insurance_info: dict[str, Any],
    ) -> InsuranceVerificationResult:
        """
        Verify patient insurance eligibility and benefits using insurance-verification service

        Args:
            insurance_info: Dictionary containing insurance information

        Returns:
            InsuranceVerificationResult with verification status and benefits

        Medical Disclaimer: Administrative insurance verification only.
        Does not provide medical advice or treatment authorization.
        """
        # Validate and sanitize input data for PHI protection
        scan_for_phi(str(insurance_info))

        verification_errors = []
        member_id = insurance_info.get("member_id")

        try:
            # Call business service for insurance verification
            async with get_business_client() as client:
                # Prepare verification request for the service
                verification_request = {
                    "member_id": insurance_info.get("member_id"),
                    "provider_id": insurance_info.get("group_id", ""),
                    "date_of_birth": insurance_info.get("dob"),
                    "first_name": insurance_info.get("first_name", ""),
                    "last_name": insurance_info.get("last_name", ""),
                    "service_type": ["30"],  # Medical care
                }

                service_response: ServiceResponse = await client.verify_insurance(verification_request)

                if service_response.success:
                    # Parse service response
                    verification_data = service_response.data.get("verification_result", {})
                    
                    # Extract verification status
                    coverage_active = verification_data.get("eligible", False)
                    
                    # Extract benefits if available
                    benefits_summary = {}
                    if "benefits" in verification_data:
                        benefits_data = verification_data["benefits"]
                        benefits_summary = {
                            "deductible_remaining": benefits_data.get("deductible_remaining", 0.0),
                            "out_of_pocket_max": benefits_data.get("out_of_pocket_max", 0.0),
                            "out_of_pocket_met": benefits_data.get("out_of_pocket_met", 0.0),
                            "copay_primary_care": benefits_data.get("copay_primary_care", 0.0),
                            "copay_specialist": benefits_data.get("copay_specialist", 0.0),
                            "coinsurance_rate": benefits_data.get("coinsurance_rate", 0.0),
                            "coverage_percentage": benefits_data.get("coverage_percentage", 0),
                            "effective_date": benefits_data.get("effective_date"),
                            "termination_date": benefits_data.get("termination_date"),
                        }

                    verification_status = "verified" if coverage_active else "coverage_inactive"
                    
                    # Extract any reasoning from Chain-of-Thought service
                    reasoning = service_response.data.get("reasoning", {})
                    
                    log_healthcare_event(
                        logger,
                        logging.INFO,
                        f"Insurance verification completed via service: {verification_status}",
                        context={
                            "member_id": member_id[:4] + "****" if member_id else "****",
                            "coverage_active": coverage_active,
                            "verification_status": verification_status,
                            "service_session_id": service_response.session_id,
                        },
                        operation_type="insurance_verification",
                    )

                    return InsuranceVerificationResult(
                        verification_id=service_response.session_id or f"verify_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        status=verification_status,
                        member_id=member_id,
                        coverage_active=coverage_active,
                        benefits_summary=benefits_summary,
                        verification_errors=[],
                        compliance_validated=True,
                        timestamp=datetime.now(),
                        metadata={
                            "service_response": True,
                            "reasoning": reasoning,
                            "benefits_retrieved": bool(benefits_summary),
                        },
                    )
                else:
                    # Service call failed
                    error_msg = service_response.error or "Insurance verification service unavailable"
                    verification_errors.append(error_msg)
                    
                    log_healthcare_event(
                        logger,
                        logging.ERROR,
                        f"Insurance verification service failed: {error_msg}",
                        context={
                            "error": error_msg,
                            "service": service_response.service,
                            "member_id": member_id[:4] + "****" if member_id else "****",
                        },
                        operation_type="verification_service_error",
                    )

                    return InsuranceVerificationResult(
                        verification_id=f"verify_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        status="service_unavailable",
                        member_id=member_id,
                        coverage_active=False,
                        benefits_summary={},
                        verification_errors=verification_errors,
                        compliance_validated=False,
                        timestamp=datetime.now(),
                        metadata={"service_error": error_msg},
                    )

        except Exception as e:
            log_healthcare_event(
                logger,
                logging.ERROR,
                f"Insurance verification failed: {str(e)}",
                context={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "member_id": member_id[:4] + "****" if member_id else "****",
                },
                operation_type="verification_error",
            )

            return InsuranceVerificationResult(
                verification_id=f"verify_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                status="verification_failed",
                member_id=member_id,
                coverage_active=False,
                benefits_summary={},
                verification_errors=[f"Verification error: {str(e)}"],
                compliance_validated=False,
                timestamp=datetime.now(),
                metadata={"error_stage": "processing_exception"},
            )

    async def _check_eligibility(
        self,
        insurance_info: dict[str, Any],
        payer_name: str,
    ) -> dict[str, Any]:
        """
        Check insurance eligibility with payer API

        Args:
            insurance_info: Insurance details
            payer_name: Insurance payer name

        Returns:
            Dictionary with eligibility status
        """
        # Mock eligibility check (in production, integrate with actual payer APIs)
        await asyncio.sleep(0.1)  # Simulate API call delay

        # Mock 90% eligibility success rate
        import random

        eligible = random.random() > 0.1

        return {
            "eligible": eligible,
            "response_code": "00" if eligible else "77",
            "response_description": "Eligible" if eligible else "Coverage terminated",
            "api_response_time_ms": 150,
        }

    async def _get_benefits_details(
        self,
        insurance_info: dict[str, Any],
        payer_name: str,
    ) -> BenefitsDetails:
        """
        Get detailed benefits information from payer

        Args:
            insurance_info: Insurance details
            payer_name: Insurance payer name

        Returns:
            BenefitsDetails object with coverage information
        """
        # Mock benefits data (in production, integrate with actual payer APIs)
        await asyncio.sleep(0.1)  # Simulate API call delay

        # Generate mock benefits based on payer
        benefit_variations = {
            "anthem": {
                "deductible_remaining": 750.00,
                "copay_primary": 25.00,
                "copay_specialist": 45.00,
                "coinsurance": 0.20,
            },
            "united_health": {
                "deductible_remaining": 500.00,
                "copay_primary": 30.00,
                "copay_specialist": 50.00,
                "coinsurance": 0.15,
            },
            "aetna": {
                "deductible_remaining": 1000.00,
                "copay_primary": 20.00,
                "copay_specialist": 40.00,
                "coinsurance": 0.25,
            },
        }

        payer_benefits = benefit_variations.get(payer_name, benefit_variations["anthem"])

        return BenefitsDetails(
            deductible_remaining=payer_benefits["deductible_remaining"],
            out_of_pocket_max=3000.00,
            out_of_pocket_met=450.00,
            copay_primary_care=payer_benefits["copay_primary"],
            copay_specialist=payer_benefits["copay_specialist"],
            coinsurance_rate=payer_benefits["coinsurance"],
            coverage_percentage=int((1 - payer_benefits["coinsurance"]) * 100),
            effective_date=date(2024, 1, 1),
            termination_date=None,
        )

    @healthcare_log_method(operation_type="prior_authorization", phi_risk_level="medium")
    @phi_monitor(risk_level="medium", operation_type="prior_authorization")
    async def request_prior_authorization(self, auth_request: dict[str, Any]) -> PriorAuthResult:
        """
        Submit prior authorization request using insurance-verification service

        Args:
            auth_request: Dictionary containing authorization request details

        Returns:
            PriorAuthResult with authorization status

        Medical Disclaimer: Administrative prior authorization processing only.
        Does not provide medical advice or treatment recommendations.
        """
        # Validate and sanitize input data for PHI protection
        scan_for_phi(str(auth_request))

        auth_errors = []
        member_id = auth_request.get("member_id")

        try:
            # Call business service for prior authorization
            async with get_business_client() as client:
                # Prepare prior auth request for the service
                prior_auth_request = {
                    "member_id": auth_request.get("member_id"),
                    "provider_id": auth_request.get("provider_id"),
                    "procedure_codes": auth_request.get("procedure_codes", []),
                    "diagnosis_codes": auth_request.get("diagnosis_codes", []),
                    "service_date": auth_request.get("service_date"),
                    "urgency": auth_request.get("urgency", "routine"),
                    "clinical_notes": auth_request.get("clinical_notes", ""),
                    "supporting_documentation": auth_request.get("supporting_documentation", []),
                }

                service_response: ServiceResponse = await client.request_prior_auth(prior_auth_request)

                if service_response.success:
                    # Parse service response
                    auth_data = service_response.data.get("authorization_result", {})
                    
                    # Extract authorization details
                    status = auth_data.get("status", "pending")
                    reference_number = auth_data.get("reference_number")
                    approved_services = auth_data.get("approved_services", [])
                    denied_services = auth_data.get("denied_services", [])
                    estimated_decision_days = auth_data.get("estimated_decision_days", 3)
                    
                    # Parse decision date
                    decision_date_str = auth_data.get("decision_date")
                    decision_date = None
                    if decision_date_str:
                        try:
                            decision_date = datetime.fromisoformat(decision_date_str).date()
                        except ValueError:
                            decision_date = date.today() + timedelta(days=estimated_decision_days)
                    else:
                        decision_date = date.today() + timedelta(days=estimated_decision_days)

                    # Extract any reasoning from Chain-of-Thought service
                    reasoning = service_response.data.get("reasoning", {})
                    
                    log_healthcare_event(
                        logger,
                        logging.INFO,
                        f"Prior authorization completed via service: {status}",
                        context={
                            "reference_number": reference_number,
                            "status": status,
                            "procedure_count": len(auth_request.get("procedure_codes", [])),
                            "estimated_decision_days": estimated_decision_days,
                            "service_session_id": service_response.session_id,
                        },
                        operation_type="prior_authorization",
                    )

                    return PriorAuthResult(
                        auth_id=service_response.session_id or f"auth_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        status=status,
                        reference_number=reference_number,
                        decision_date=decision_date,
                        approved_services=approved_services,
                        denied_services=denied_services,
                        auth_errors=[],
                        estimated_decision_days=estimated_decision_days,
                        timestamp=datetime.now(),
                    )
                else:
                    # Service call failed
                    error_msg = service_response.error or "Prior authorization service unavailable"
                    auth_errors.append(error_msg)
                    
                    log_healthcare_event(
                        logger,
                        logging.ERROR,
                        f"Prior authorization service failed: {error_msg}",
                        context={
                            "error": error_msg,
                            "service": service_response.service,
                            "member_id": member_id[:4] + "****" if member_id else "****",
                        },
                        operation_type="auth_service_error",
                    )

                    return PriorAuthResult(
                        auth_id=f"auth_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        status="service_unavailable",
                        reference_number=None,
                        decision_date=None,
                        approved_services=[],
                        denied_services=[],
                        auth_errors=auth_errors,
                        estimated_decision_days=0,
                        timestamp=datetime.now(),
                    )

        except Exception as e:
            log_healthcare_event(
                logger,
                logging.ERROR,
                f"Prior authorization failed: {str(e)}",
                context={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "member_id": member_id[:4] + "****" if member_id else "****",
                },
                operation_type="auth_error",
            )

            return PriorAuthResult(
                auth_id=f"auth_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                status="processing_failed",
                reference_number=None,
                decision_date=None,
                approved_services=[],
                denied_services=[],
                auth_errors=[f"Processing error: {str(e)}"],
                estimated_decision_days=0,
                timestamp=datetime.now(),
            )

    @healthcare_log_method(operation_type="coverage_check", phi_risk_level="medium")
    async def check_coverage_for_service(self, coverage_request: dict[str, Any]) -> dict[str, Any]:
        """
        Check insurance coverage for specific healthcare service

        Args:
            coverage_request: Dictionary with service and insurance details

        Returns:
            Dictionary with coverage analysis
        """
        # Mock coverage analysis (in production, use actual payer rules)
        service_code = coverage_request.get("service_code", "")
        service_type = coverage_request.get("service_type", "outpatient")

        # Mock coverage rules
        coverage_rules = {
            "99213": {"covered": True, "copay": 30.00, "coinsurance": 0.0, "prior_auth": False},
            "99214": {"covered": True, "copay": 30.00, "coinsurance": 0.0, "prior_auth": False},
            "73721": {"covered": True, "copay": 0.00, "coinsurance": 0.20, "prior_auth": True},
            "45378": {"covered": True, "copay": 200.00, "coinsurance": 0.0, "prior_auth": True},
            "36415": {"covered": True, "copay": 0.00, "coinsurance": 0.0, "prior_auth": False},
        }

        coverage_info = coverage_rules.get(
            service_code,
            {"covered": False, "copay": 0.00, "coinsurance": 0.0, "prior_auth": False},
        )

        result = {
            "coverage_id": f"cov_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "service_code": service_code,
            "service_type": service_type,
            "is_covered": coverage_info["covered"],
            "patient_cost": {
                "copay": coverage_info["copay"],
                "coinsurance_rate": coverage_info["coinsurance"],
                "estimated_patient_cost": coverage_info["copay"]
                + (100.00 * coverage_info["coinsurance"]),
            },
            "prior_authorization_required": coverage_info["prior_auth"],
            "coverage_notes": [
                "Coverage subject to active policy status",
                "Costs are estimates based on standard fees",
            ],
            "timestamp": datetime.now().isoformat(),
        }

        log_healthcare_event(
            logger,
            logging.INFO,
            f"Coverage check completed for service {service_code}",
            context={
                "service_code": service_code,
                "is_covered": coverage_info["covered"],
                "prior_auth_required": coverage_info["prior_auth"],
                "estimated_cost": result["patient_cost"]["estimated_patient_cost"],
            },
            operation_type="coverage_check",
        )

        return result

    @healthcare_log_method(operation_type="insurance_report", phi_risk_level="low")
    async def generate_insurance_report(self, date_range: dict[str, str]) -> dict[str, Any]:
        """
        Generate insurance verification and authorization report

        Args:
            date_range: Dictionary with 'start_date' and 'end_date'

        Returns:
            Dictionary with insurance activity report
        """
        # Mock report generation (in production, query actual verification database)
        report: dict[str, Any] = {
            "report_id": f"ins_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "date_range": date_range,
            "verification_summary": {
                "total_verifications": 156,
                "successful_verifications": 142,
                "failed_verifications": 14,
                "success_rate": 91.0,
                "average_response_time_ms": 245,
            },
            "prior_auth_summary": {
                "total_requests": 45,
                "approved_requests": 34,
                "denied_requests": 8,
                "pending_requests": 3,
                "approval_rate": 75.6,
                "average_decision_days": 1.8,
            },
            "payer_breakdown": [
                {"payer": "anthem", "verifications": 48, "success_rate": 94.0},
                {"payer": "united_health", "verifications": 42, "success_rate": 88.0},
                {"payer": "aetna", "verifications": 35, "success_rate": 90.0},
                {"payer": "cigna", "verifications": 31, "success_rate": 92.0},
            ],
            "coverage_analysis": {
                "most_verified_services": ["99213", "99214", "36415"],
                "highest_denial_services": ["73721", "45378"],
                "average_patient_cost": 68.50,
            },
            "generated_timestamp": datetime.now().isoformat(),
        }

        log_healthcare_event(
            logger,
            logging.INFO,
            "Insurance report generated",
            context={
                "report_id": report["report_id"],
                "total_verifications": report["verification_summary"]["total_verifications"],
                "success_rate": report["verification_summary"]["success_rate"],
                "total_prior_auths": report["prior_auth_summary"]["total_requests"],
            },
            operation_type="report_generation",
        )

        return report

    @healthcare_log_method(operation_type="insurance_chain_of_thought", phi_risk_level="high")
    @phi_monitor(risk_level="high", operation_type="insurance_chain_of_thought")
    async def verify_eligibility_with_reasoning(
        self,
        insurance_info: dict[str, Any],
        service_codes: list[str] = None,
        session_id: str = None,
        user_id: str = None,
    ) -> dict[str, Any]:
        """
        Verify insurance eligibility using Chain-of-Thought reasoning

        Provides transparent, step-by-step reasoning for insurance eligibility decisions
        with full audit trails for compliance and quality assurance.

        Args:
            insurance_info: Dictionary containing insurance information
            service_codes: Optional list of service codes to verify coverage
            session_id: Session ID for tracking
            user_id: User ID for audit trails

        Returns:
            Dictionary containing reasoning chain and eligibility results

        Medical Disclaimer: Administrative insurance verification only.
        Does not provide medical advice or treatment authorization.
        """
        try:
            # Increment metrics for Chain-of-Thought usage
            await self._metrics.incr("chain_of_thought_requests")

            # Validate and sanitize input data for PHI protection
            scan_for_phi(str(insurance_info))

            # Prepare reasoning input data
            reasoning_input = {
                "member_id": insurance_info.get("member_id"),
                "provider_network": insurance_info.get("payer_name"),
                "plan_type": insurance_info.get("plan_type", "Unknown"),
                "service_date": insurance_info.get("service_date", datetime.now().date().isoformat()),
                "service_codes": service_codes or [],
                "provider_npi": insurance_info.get("provider_npi"),
                "group_id": insurance_info.get("group_id"),
                "date_of_birth": insurance_info.get("dob"),
            }

            # Generate Chain-of-Thought reasoning
            reasoning_question = f"""Verify insurance eligibility for member ID {insurance_info.get('member_id', 'N/A')}
            with {insurance_info.get('payer_name', 'Unknown')} insurance for the requested services.
            Provide administrative verification with step-by-step reasoning."""

            reasoning_result = await self._reasoning_processor.process_reasoning_chain(
                input_data=reasoning_input,
                question=reasoning_question,
                reasoning_type=ReasoningType.INSURANCE_ELIGIBILITY,
                session_id=session_id or f"ins_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                user_id=user_id,
            )

            # Perform actual eligibility verification
            eligibility_result = await self.verify_insurance_eligibility(insurance_info)

            # Combine reasoning with verification results
            enhanced_result = {
                "eligibility_verification": {
                    "verification_id": eligibility_result.verification_id,
                    "status": eligibility_result.status,
                    "coverage_active": eligibility_result.coverage_active,
                    "benefits_summary": eligibility_result.benefits_summary,
                    "verification_errors": eligibility_result.verification_errors,
                },
                "reasoning_chain": {
                    "chain_id": reasoning_result.chain_id,
                    "reasoning_steps": [
                        {
                            "step_id": step.step_id,
                            "step_type": step.step_type,
                            "conclusion": step.conclusion,
                            "confidence_score": step.confidence_score,
                            "evidence": step.evidence[:3],  # Top 3 evidence items
                            "timestamp": step.timestamp.isoformat(),
                        }
                        for step in reasoning_result.steps
                    ],
                    "final_conclusion": reasoning_result.final_conclusion,
                    "overall_confidence": reasoning_result.overall_confidence,
                    "recommendations": reasoning_result.recommendations,
                },
                "audit_trail": reasoning_result.audit_trail,
                "medical_disclaimer": (
                    "This analysis provides administrative insurance verification support only. "
                    "It does not provide medical advice, diagnosis, or treatment recommendations. "
                    "All medical decisions must be made by qualified healthcare professionals."
                ),
                "timestamp": datetime.now().isoformat(),
            }

            # Log Chain-of-Thought usage
            await self._metrics.incr("chain_of_thought_completions")

            log_healthcare_event(
                logger,
                logging.INFO,
                "Chain-of-Thought insurance verification completed",
                context={
                    "chain_id": reasoning_result.chain_id,
                    "reasoning_steps": len(reasoning_result.steps),
                    "overall_confidence": reasoning_result.overall_confidence,
                    "eligibility_status": eligibility_result.status,
                    "user_id": user_id,
                    "session_id": session_id,
                },
                operation_type="insurance_chain_of_thought",
            )

            return enhanced_result

        except Exception as e:
            await self._metrics.incr("chain_of_thought_errors")

            log_healthcare_event(
                logger,
                logging.ERROR,
                f"Chain-of-Thought insurance verification failed: {str(e)}",
                context={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "user_id": user_id,
                    "session_id": session_id,
                },
                operation_type="insurance_chain_of_thought_error",
            )

            # Return error response with fallback to standard verification
            try:
                fallback_result = await self.verify_insurance_eligibility(insurance_info)
                return {
                    "eligibility_verification": {
                        "verification_id": fallback_result.verification_id,
                        "status": fallback_result.status,
                        "coverage_active": fallback_result.coverage_active,
                        "benefits_summary": fallback_result.benefits_summary,
                        "verification_errors": fallback_result.verification_errors,
                    },
                    "reasoning_chain": {
                        "error": "Chain-of-Thought reasoning failed",
                        "error_details": str(e),
                        "fallback_used": True,
                    },
                    "medical_disclaimer": (
                        "This analysis provides administrative insurance verification support only. "
                        "It does not provide medical advice, diagnosis, or treatment recommendations. "
                        "All medical decisions must be made by qualified healthcare professionals."
                    ),
                    "timestamp": datetime.now().isoformat(),
                }
            except Exception as fallback_error:
                return {
                    "eligibility_verification": {
                        "status": "verification_failed",
                        "coverage_active": False,
                        "verification_errors": [f"Primary and fallback verification failed: {str(fallback_error)}"],
                    },
                    "reasoning_chain": {
                        "error": "Both Chain-of-Thought and standard verification failed",
                        "primary_error": str(e),
                        "fallback_error": str(fallback_error),
                    },
                    "medical_disclaimer": (
                        "This analysis provides administrative insurance verification support only. "
                        "It does not provide medical advice, diagnosis, or treatment recommendations. "
                        "All medical decisions must be made by qualified healthcare professionals."
                    ),
                    "timestamp": datetime.now().isoformat(),
                }

    async def _process_implementation(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Implement insurance agent-specific processing logic

        Routes requests to appropriate insurance methods based on request type.
        All responses include medical disclaimers.
        """
        request_type = request.get("type", "unknown")

        # Add medical disclaimer to all responses
        base_response = {
            "medical_disclaimer": (
                "This system provides healthcare insurance administrative support only. "
                "It does not provide medical advice, diagnosis, or treatment recommendations. "
                "All medical decisions must be made by qualified healthcare professionals."
            ),
            "success": True,
            "timestamp": datetime.now().isoformat(),
        }

        try:
            if request_type == "coverage_verification":
                result = await self.check_coverage_for_service(request.get("coverage_request", {}))
                base_response.update({"coverage_result": result})

            elif request_type == "prior_authorization":
                result = await self.request_prior_authorization(request.get("auth_request", {}))
                base_response.update({"authorization_result": result})

            elif request_type == "eligibility_verification":
                result = await self.verify_insurance_eligibility(
                    request.get("insurance_info", {}),
                )
                base_response.update({"eligibility_result": result})

            elif request_type == "eligibility_verification_with_reasoning":
                result = await self.verify_eligibility_with_reasoning(
                    insurance_info=request.get("insurance_info", {}),
                    service_codes=request.get("service_codes", []),
                    session_id=request.get("session_id"),
                    user_id=request.get("user_id"),
                )
                base_response.update({"enhanced_eligibility_result": result})

            elif request_type == "report_generation":
                result = await self.generate_insurance_report(request.get("date_range", {}))
                base_response.update({"report": result})

            else:
                base_response.update(
                    {
                        "success": False,
                        "error": f"Unknown request type: {request_type}",
                        "supported_types": [
                            "coverage_verification",
                            "prior_authorization",
                            "eligibility_verification",
                            "eligibility_verification_with_reasoning",
                            "report_generation",
                        ],
                    },
                )

        except Exception as e:
            base_response.update(
                {"success": False, "error": str(e), "error_type": type(e).__name__},
            )

        return base_response


# Initialize the insurance verification agent
insurance_verification_agent = InsuranceVerificationAgent()
