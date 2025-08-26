"""
Healthcare Billing Helper Agent - Administrative Billing Support Only
Handles medical billing, claims processing, and coding assistance for administrative workflows
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from agents import BaseHealthcareAgent
from agents.billing_helper.shared.billing_utils import SharedBillingUtils
from core.clients.business_services import get_business_client, ServiceResponse
from core.financial.healthcare_financial_utils import HealthcareFinancialUtils
from core.infrastructure.agent_logging_utils import (
    enhanced_agent_method,
)
from core.infrastructure.agent_metrics import AgentMetricsStore
from core.infrastructure.healthcare_cache import HealthcareCacheManager
from core.infrastructure.healthcare_logger import (
    get_healthcare_logger,
    healthcare_log_method,
    log_healthcare_event,
)
from core.infrastructure.phi_monitor import (
    phi_monitor_decorator,
    sanitize_healthcare_data,
    scan_for_phi,
)
from core.reasoning.tree_of_thoughts import (
    PlanningFocus,
    TreeOfThoughtsPlanner,
)

logger = get_healthcare_logger("agent.billing_helper")


@dataclass
class BillingResult:
    """Result from billing processing with healthcare compliance"""

    billing_id: str
    status: str
    claim_number: str | None
    total_amount: float | None
    processing_errors: list[str]
    compliance_validated: bool
    timestamp: datetime
    metadata: dict[str, Any]


@dataclass
@dataclass
class CPTCodeValidation:
    """CPT code validation result"""

    code: str
    is_valid: bool
    description: str | None
    modifier_required: bool
    billing_notes: list[str]


@dataclass
class ICDCodeValidation:
    """ICD-10 code validation result"""

    code: str
    is_valid: bool
    description: str | None
    category: str | None
    billing_notes: list[str]


class BillingHelperAgent(BaseHealthcareAgent):
    """
    Healthcare Billing Helper Agent

    MEDICAL DISCLAIMER: This agent provides administrative billing support and medical coding
    resources only. It assists healthcare professionals with billing procedures, code validation,
    and insurance processes. It does not provide medical diagnosis, treatment recommendations,
    or replace clinical judgment. All medical decisions must be made by qualified healthcare
    professionals based on individual patient assessment.

    Capabilities:
    - Medical billing and claims processing assistance
    - CPT and ICD-10 code validation and lookup
    - Insurance verification and benefits checking
    - Billing compliance validation
    - Claims status tracking and follow-up
    - Denial management and appeals assistance
    """

    def __init__(self, mcp_client=None, llm_client=None) -> None:
        super().__init__(agent_name="billing_helper", agent_type="billing_helper")
        self.mcp_client = mcp_client
        self.llm_client = llm_client
        self.agent_type = "billing_helper"

        # Initialize shared healthcare infrastructure tools
        self._metrics = AgentMetricsStore(agent_name="billing_helper")
        self._cache_manager = HealthcareCacheManager()

        # Initialize Tree-of-Thoughts planner for complex billing scenarios
        self._tree_planner = TreeOfThoughtsPlanner(
            llm_client=llm_client,
            knowledge_base=None,  # Could integrate billing knowledge base
        )
        self.capabilities = [
            "claims_processing",
            "code_validation",
            "insurance_verification",
            "compliance_checking",
            "denial_management",
            "advanced_insurance_calculations",  # NEW: Advanced insurance features
            "deductible_tracking",  # NEW: Deductible proximity tracking
            "cost_prediction",  # NEW: Exact visit cost prediction
        ]

        # Log agent initialization with healthcare context
        log_healthcare_event(
            logger,
            logging.INFO,
            "Healthcare Billing Helper Agent initialized",
            context={
                "agent": "billing_helper",
                "initialization": True,
                "phi_monitoring": True,
                "medical_advice_disabled": True,
                "database_required": True,
                "capabilities": self.capabilities,
            },
            operation_type="agent_initialization",
        )

    async def initialize(self) -> None:
        """Initialize billing helper agent with database connectivity validation"""
        try:
            # Call parent initialization which validates database connectivity
            await self.initialize_agent()

            # Initialize advanced insurance calculation components
            from domains.insurance_calculations import (
                DeductibleTracker,
                InsuranceCoverageCalculator,
            )

            self.insurance_calculator = InsuranceCoverageCalculator()
            self.deductible_tracker = DeductibleTracker()

            log_healthcare_event(
                logger,
                logging.INFO,
                "Billing Helper Agent fully initialized with database connectivity and advanced insurance calculations",
                context={
                    "agent": "billing_helper",
                    "database_validated": True,
                    "advanced_insurance_enabled": True,
                    "ready_for_operations": True,
                },
                operation_type="agent_ready",
            )
        except Exception as e:
            log_healthcare_event(
                logger,
                logging.CRITICAL,
                f"Billing Helper Agent initialization failed: {e}",
                context={
                    "agent": "billing_helper",
                    "initialization_failed": True,
                    "error": str(e),
                },
                operation_type="agent_initialization_error",
            )
            raise

    @enhanced_agent_method(operation_type="claim_processing", phi_risk_level="medium", track_performance=True)
    @phi_monitor_decorator(risk_level="medium", operation_type="billing_processing")
    async def process_claim(self, claim_data: dict[str, Any]) -> BillingResult:
        """
        Process medical billing claim using billing-engine service

        Args:
            claim_data: Dictionary containing claim information

        Returns:
            BillingResult with processing status and validation

        Medical Disclaimer: Administrative billing support only.
        Does not provide medical advice or clinical decision-making.
        """
        # Initialize workflow logger for detailed claim processing tracking
        workflow_logger = self.get_workflow_logger()
        workflow_logger.start_workflow("claim_processing_service", {
            "procedure_codes_count": len(claim_data.get("procedure_codes", [])),
            "diagnosis_codes_count": len(claim_data.get("diagnosis_codes", [])),
            "has_patient_id": "patient_id" in claim_data,
            "has_provider_id": "provider_id" in claim_data,
        })

        # Validate and sanitize input data for PHI protection
        workflow_logger.log_step("phi_scanning", {"scanning_fields": list(claim_data.keys())})
        scan_for_phi(str(claim_data))

        processing_errors = []
        patient_id = claim_data.get("patient_id")

        try:
            # Call business service for claim processing
            async with get_business_client() as client:
                # Prepare claim processing request for the service
                claim_request = {
                    "claim_id": f"claim_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "patient_id": claim_data.get("patient_id"),
                    "provider_id": claim_data.get("provider_id"),
                    "service_date": claim_data.get("service_date"),
                    "procedure_codes": claim_data.get("procedure_codes", []),
                    "diagnosis_codes": claim_data.get("diagnosis_codes", []),
                    "insurance_info": claim_data.get("insurance_info", {}),
                    "modifiers": claim_data.get("modifiers", []),
                    "units": claim_data.get("units", {}),
                    "place_of_service": claim_data.get("place_of_service", "11"),
                }

                workflow_logger.log_step("calling_billing_service", {
                    "service_endpoint": "process_claim",
                })

                service_response: ServiceResponse = await client.process_claim(claim_request)

                if service_response.success:
                    # Parse service response
                    claim_result = service_response.data.get("claim_result", {})
                    
                    # Extract claim processing details
                    status = claim_result.get("status", "unknown")
                    claim_number = claim_result.get("claim_number")
                    total_amount = claim_result.get("total_amount", 0.0)
                    validation_errors = claim_result.get("validation_errors", [])
                    compliance_validated = claim_result.get("compliance_validated", False)
                    
                    # Extract Tree of Thoughts reasoning
                    reasoning = service_response.data.get("reasoning", {})
                    
                    # Finish workflow logging
                    workflow_logger.finish_workflow("completed", {
                        "final_status": status,
                        "claim_number": claim_number,
                        "total_amount": total_amount,
                        "compliance_validated": compliance_validated,
                        "service_session_id": service_response.session_id,
                        "error_count": len(validation_errors),
                    })

                    log_healthcare_event(
                        logger,
                        logging.INFO,
                        f"Claim processing completed via service: {status}",
                        context={
                            "claim_number": claim_number,
                            "total_amount": total_amount,
                            "compliance_validated": compliance_validated,
                            "service_session_id": service_response.session_id,
                        },
                        operation_type="claim_processing",
                    )

                    return BillingResult(
                        billing_id=service_response.session_id or f"bill_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        status=status,
                        claim_number=claim_number,
                        total_amount=total_amount,
                        processing_errors=validation_errors,
                        compliance_validated=compliance_validated,
                        timestamp=datetime.now(),
                        metadata={
                            "service_response": True,
                            "reasoning": reasoning,
                            "processing_stage": "complete",
                        },
                    )
                else:
                    # Service call failed
                    error_msg = service_response.error or "Billing engine service unavailable"
                    processing_errors.append(error_msg)
                    
                    workflow_logger.finish_workflow("failed", {
                        "service_error": error_msg,
                    })
                    
                    log_healthcare_event(
                        logger,
                        logging.ERROR,
                        f"Claim processing service failed: {error_msg}",
                        context={
                            "error": error_msg,
                            "service": service_response.service,
                            "patient_id": patient_id[:4] + "****" if patient_id else "****",
                        },
                        operation_type="claim_processing_service_error",
                    )

                    return BillingResult(
                        billing_id=f"bill_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        status="service_unavailable",
                        claim_number=None,
                        total_amount=None,
                        processing_errors=processing_errors,
                        compliance_validated=False,
                        timestamp=datetime.now(),
                        metadata={"service_error": error_msg},
                    )

        except Exception as e:
            workflow_logger.finish_workflow("failed", error=e)

            log_healthcare_event(
                logger,
                logging.ERROR,
                f"Claim processing failed: {str(e)}",
                context={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "patient_id": patient_id[:4] + "****" if patient_id else "****",
                },
                operation_type="claim_processing_error",
            )

            return BillingResult(
                billing_id=f"bill_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                status="processing_failed",
                claim_number=None,
                total_amount=None,
                processing_errors=[f"Processing error: {str(e)}"],
                compliance_validated=False,
                timestamp=datetime.now(),
                metadata={"error_stage": "processing_exception"},
            )

    @enhanced_agent_method(operation_type="cpt_validation", phi_risk_level="low", track_performance=True)
    async def validate_cpt_code(self, cpt_code: str) -> CPTCodeValidation:
        """
        Validate CPT procedure code

        Args:
            cpt_code: CPT code to validate

        Returns:
            CPTCodeValidation with validation results
        """
        # Common CPT codes for validation (in production, use comprehensive database)
        cpt_database: dict[str, dict[str, Any]] = {
            "99213": {
                "description": "Office visit, established patient, low complexity",
                "modifier_required": False,
                "billing_notes": ["Standard office visit billing"],
            },
            "99214": {
                "description": "Office visit, established patient, moderate complexity",
                "modifier_required": False,
                "billing_notes": ["Requires documentation of complexity"],
            },
            "36415": {
                "description": "Collection of venous blood by venipuncture",
                "modifier_required": False,
                "billing_notes": ["Lab collection procedure"],
            },
            "85025": {
                "description": "Blood count; complete (CBC), automated",
                "modifier_required": False,
                "billing_notes": ["Laboratory test - CBC"],
            },
        }

        # Clean and validate format
        clean_code = cpt_code.strip().upper()

        if clean_code in cpt_database:
            code_info = cpt_database[clean_code]
            return CPTCodeValidation(
                code=clean_code,
                is_valid=True,
                description=str(code_info["description"]),
                modifier_required=bool(code_info["modifier_required"]),
                billing_notes=list(code_info["billing_notes"]),
            )
        return CPTCodeValidation(
            code=clean_code,
            is_valid=False,
            description=None,
            modifier_required=False,
            billing_notes=[f"CPT code {clean_code} not found in database"],
        )

    @enhanced_agent_method(operation_type="icd_validation", phi_risk_level="low", track_performance=True)
    async def validate_icd_code(self, icd_code: str) -> ICDCodeValidation:
        """
        Validate ICD-10 diagnosis code

        Args:
            icd_code: ICD-10 code to validate

        Returns:
            ICDCodeValidation with validation results
        """
        # Common ICD-10 codes for validation (in production, use comprehensive database)
        icd_database: dict[str, dict[str, Any]] = {
            "Z00.00": {
                "description": "Encounter for general adult medical examination without abnormal findings",
                "category": "Factors influencing health status",
                "billing_notes": ["Preventive care encounter"],
            },
            "I10": {
                "description": "Essential (primary) hypertension",
                "category": "Diseases of the circulatory system",
                "billing_notes": ["Chronic condition - hypertension"],
            },
            "E11.9": {
                "description": "Type 2 diabetes mellitus without complications",
                "category": "Endocrine, nutritional and metabolic diseases",
                "billing_notes": ["Chronic condition - diabetes"],
            },
            "M25.511": {
                "description": "Pain in right shoulder",
                "category": "Diseases of the musculoskeletal system",
                "billing_notes": ["Shoulder pain - specific location"],
            },
        }

        # Clean and validate format
        clean_code = icd_code.strip().upper()

        if clean_code in icd_database:
            code_info = icd_database[clean_code]
            return ICDCodeValidation(
                code=clean_code,
                is_valid=True,
                description=str(code_info["description"]),
                category=str(code_info["category"]),
                billing_notes=list(code_info["billing_notes"]),
            )
        return ICDCodeValidation(
            code=clean_code,
            is_valid=False,
            description=None,
            category=None,
            billing_notes=[f"ICD-10 code {clean_code} not found in database"],
        )

    def _calculate_claim_amount(
        self,
        claim_data: dict[str, Any],
        cpt_validations: list[CPTCodeValidation],
    ) -> float:
        """
        Calculate total claim amount based on procedure codes

        Args:
            claim_data: Claim information
            cpt_validations: Validated CPT codes

        Returns:
            Total calculated amount
        """
        # Simple fee schedule (in production, use comprehensive fee schedules)
        fee_schedule = {"99213": 150.00, "99214": 200.00, "36415": 25.00, "85025": 35.00}

        total = 0.0
        for validation in cpt_validations:
            if validation.is_valid and validation.code in fee_schedule:
                total += fee_schedule[validation.code]

        return total

    @healthcare_log_method(operation_type="insurance_verification", phi_risk_level="low")
    @phi_monitor_decorator(risk_level="low", operation_type="insurance_verification")
    async def verify_insurance_benefits(self, insurance_info: dict[str, Any]) -> dict[str, Any]:
        """
        Verify insurance benefits and coverage

        Args:
            insurance_info: Insurance information to verify

        Returns:
            Dictionary with verification results

        Medical Disclaimer: Administrative insurance verification only.
        Does not provide medical advice or treatment authorization.
        """
        # Sanitize input for PHI protection
        sanitize_healthcare_data(insurance_info)

        # Mock insurance verification (in production, integrate with payer APIs)
        verification_result: dict[str, Any] = {
            "verification_id": f"verify_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "status": "verified",
            "benefits": {
                "deductible_remaining": 500.00,
                "out_of_pocket_max": 2000.00,
                "copay_primary_care": 30.00,
                "copay_specialist": 50.00,
                "coverage_percentage": 80,
            },
            "coverage_active": True,
            "verification_timestamp": datetime.now().isoformat(),
            "notes": ["Coverage verified for outpatient services"],
        }

        log_healthcare_event(
            logger,
            logging.INFO,
            "Insurance benefits verification completed",
            context={
                "verification_id": verification_result["verification_id"],
                "coverage_active": verification_result["coverage_active"],
                "deductible_remaining": verification_result["benefits"]["deductible_remaining"],
            },
            operation_type="insurance_verification",
        )

        return verification_result

    @healthcare_log_method(operation_type="billing_report", phi_risk_level="low")
    async def generate_billing_report(self, date_range: dict[str, str]) -> dict[str, Any]:
        """
        Generate billing summary report for specified date range

        Args:
            date_range: Dictionary with 'start_date' and 'end_date'

        Returns:
            Dictionary with billing report data
        """
        # Mock report generation (in production, query actual billing database)
        report: dict[str, Any] = {
            "report_id": f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "date_range": date_range,
            "summary": {
                "total_claims": 45,
                "total_amount": 8750.00,
                "paid_claims": 38,
                "paid_amount": 7200.00,
                "pending_claims": 5,
                "pending_amount": 1200.00,
                "denied_claims": 2,
                "denied_amount": 350.00,
            },
            "top_procedures": [
                {"cpt_code": "99213", "count": 15, "amount": 2250.00},
                {"cpt_code": "99214", "count": 12, "amount": 2400.00},
                {"cpt_code": "85025", "count": 8, "amount": 280.00},
            ],
            "generated_timestamp": datetime.now().isoformat(),
        }

        log_healthcare_event(
            logger,
            logging.INFO,
            "Billing report generated",
            context={
                "report_id": report["report_id"],
                "total_claims": report["summary"]["total_claims"],
                "total_amount": report["summary"]["total_amount"],
            },
            operation_type="report_generation",
        )

        return report

    async def _process_implementation(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Implement billing agent-specific processing logic

        Routes requests to appropriate billing methods based on request type.
        All responses include medical disclaimers.
        """
        request_type = request.get("type", "unknown")

        # Add medical disclaimer to all responses
        base_response = {
            "medical_disclaimer": (
                "This system provides healthcare billing administrative support only. "
                "It does not provide medical advice, diagnosis, or treatment recommendations. "
                "All medical decisions must be made by qualified healthcare professionals."
            ),
            "success": True,
            "timestamp": datetime.now().isoformat(),
        }

        try:
            if request_type == "billing_processing":
                result = await self.process_claim(request.get("billing_data", {}))
                base_response.update({"billing_result": result})

            elif request_type == "insurance_verification":
                result = await self.verify_insurance_benefits(request.get("insurance_info", {}))
                base_response.update({"verification_result": result})

            elif request_type == "report_generation":
                result = await self.generate_billing_report(
                    request.get("date_range", {}),
                    request.get("report_type", "summary"),
                )
                base_response.update({"report": result})

            else:
                base_response.update(
                    {
                        "success": False,
                        "error": f"Unknown request type: {request_type}",
                        "supported_types": [
                            "billing_processing",
                            "insurance_verification",
                            "report_generation",
                            "cost_prediction",
                            "deductible_tracking",
                        ],
                    },
                )

        except Exception as e:
            base_response.update(
                {"success": False, "error": str(e), "error_type": type(e).__name__},
            )

        return base_response

    # =================== ADVANCED INSURANCE CALCULATION METHODS ===================

    @healthcare_log_method(operation_type="cost_prediction", phi_risk_level="medium")
    async def predict_visit_cost(self, visit_data: dict[str, Any]) -> dict[str, Any]:
        """
        Predict exact cost for scheduled visit with advanced insurance calculations

        Supports:
        - Percentage copays (not just fixed dollar amounts)
        - Deductible proximity tracking
        - Complex insurance structures (HSA, family vs individual)

        Args:
            visit_data: Dictionary containing visit information, CPT codes, patient insurance

        Returns:
            Detailed cost prediction with breakdown

        Medical Disclaimer: Administrative cost prediction only.
        Does not provide medical advice or treatment authorization.
        """
        try:
            patient_id = visit_data.get("patient_id")
            if not patient_id or not isinstance(patient_id, str):
                return {"error": "Valid patient_id is required"}

            cpt_codes = visit_data.get("cpt_codes", [])
            insurance_type = visit_data.get("insurance_type", "standard")

            # Get current deductible status
            deductible_status = await self.deductible_tracker.calculate_deductible_proximity(
                patient_id,
                "current_year",
            )

            # Calculate cost for each CPT code
            breakdown_by_cpt: list[dict[str, Any]] = []
            cost_explanation: list[str] = []

            total_cost_prediction: dict[str, Any] = {
                "total_estimated_cost": Decimal("0.00"),
                "patient_responsibility": Decimal("0.00"),
                "insurance_payment": Decimal("0.00"),
                "deductible_applied": Decimal("0.00"),
                "copay_amount": Decimal("0.00"),
                "coinsurance_amount": Decimal("0.00"),
                "breakdown_by_cpt": breakdown_by_cpt,
                "deductible_status": {
                    "annual_deductible": deductible_status.annual_deductible,
                    "amount_applied": deductible_status.amount_applied,
                    "remaining_amount": deductible_status.remaining_amount,
                    "percentage_met": deductible_status.percentage_met,
                },
                "cost_explanation": cost_explanation,
            }

            for cpt_code in cpt_codes:
                # Get negotiated rate for CPT code using shared utility
                negotiated_rate = SharedBillingUtils.get_negotiated_rate(cpt_code, insurance_type)

                # Create patient coverage data for insurance calculator using shared utility
                patient_coverage = SharedBillingUtils.get_patient_coverage_data(
                    patient_id,
                    insurance_type,
                )

                # Calculate cost using advanced insurance calculator
                cost_estimate = self.insurance_calculator.calculate_patient_cost(
                    cpt_code=cpt_code,
                    billed_amount=negotiated_rate,  # Already a Decimal from shared utility
                    patient_coverage=patient_coverage,
                )

                # Convert to Decimal for safe addition
                patient_cost = HealthcareFinancialUtils.ensure_decimal(
                    cost_estimate.patient_responsibility,
                )
                insurance_payment = HealthcareFinancialUtils.ensure_decimal(
                    cost_estimate.insurance_payment,
                )

                breakdown_by_cpt.append(
                    {
                        "cpt_code": cpt_code,
                        "negotiated_rate": negotiated_rate,
                        "patient_cost": patient_cost,
                        "insurance_payment": insurance_payment,
                    },
                )

                # Update totals with safe Decimal arithmetic
                total_estimated_cost = HealthcareFinancialUtils.ensure_decimal(
                    total_cost_prediction["total_estimated_cost"],
                )
                total_patient_resp = HealthcareFinancialUtils.ensure_decimal(
                    total_cost_prediction["patient_responsibility"],
                )
                total_insurance_payment = HealthcareFinancialUtils.ensure_decimal(
                    total_cost_prediction["insurance_payment"],
                )

                total_cost_prediction["total_estimated_cost"] = (
                    total_estimated_cost + negotiated_rate
                )
                total_cost_prediction["patient_responsibility"] = total_patient_resp + patient_cost
                total_cost_prediction["insurance_payment"] = (
                    total_insurance_payment + insurance_payment
                )

            # Add patient-friendly explanations
            if deductible_status.remaining_amount > 0:
                cost_explanation.append(
                    f"You have ${deductible_status.remaining_amount:.2f} remaining on your "
                    f"${deductible_status.annual_deductible:.2f} annual deductible",
                )

            if deductible_status.percentage_met > 0.8:
                cost_explanation.append(
                    f"You're {deductible_status.percentage_met:.0%} of the way to meeting your deductible",
                )

            cost_explanation.append(
                f"Total estimated cost: ${total_cost_prediction['patient_responsibility']:.2f}",
            )

            log_healthcare_event(
                logger,
                logging.INFO,
                "Visit cost prediction completed",
                context={
                    "patient_id": patient_id,
                    "cpt_codes": cpt_codes,
                    "total_patient_cost": total_cost_prediction["patient_responsibility"],
                    "deductible_remaining": deductible_status.remaining_amount,
                },
                operation_type="cost_prediction",
            )

            return {
                "success": True,
                "cost_prediction": total_cost_prediction,
                "prediction_timestamp": datetime.now().isoformat(),
                "disclaimer": "Cost estimates are for informational purposes only. Actual costs may vary based on services provided and insurance processing.",
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Cost prediction failed: {str(e)}",
                "disclaimer": "Unable to generate cost prediction. Please contact billing department for assistance.",
            }

    @healthcare_log_method(operation_type="deductible_tracking", phi_risk_level="medium")
    async def track_deductible_progress(self, patient_id: str) -> dict[str, Any]:
        """
        Track patient's deductible progress with advanced insights

        Args:
            patient_id: Patient identifier

        Returns:
            Comprehensive deductible tracking information

        Medical Disclaimer: Administrative tracking only.
        """
        try:
            deductible_status = await self.deductible_tracker.calculate_deductible_proximity(
                patient_id,
                "current_year",
            )

            insights = self.deductible_tracker.generate_deductible_insights(deductible_status)

            return {
                "success": True,
                "patient_id": patient_id,
                "deductible_status": {
                    "annual_deductible": deductible_status.annual_deductible,
                    "amount_applied": deductible_status.amount_applied,
                    "remaining_amount": deductible_status.remaining_amount,
                    "percentage_met": deductible_status.percentage_met,
                    "projected_meet_date": deductible_status.projected_meet_date.isoformat()
                    if deductible_status.projected_meet_date
                    else None,
                    "likelihood_to_meet": deductible_status.likelihood_to_meet,
                },
                "insights": insights,
                "tracking_timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return {"success": False, "error": f"Deductible tracking failed: {str(e)}"}

    @healthcare_log_method(operation_type="complex_billing_planning", phi_risk_level="medium")
    @phi_monitor_decorator(risk_level="medium", operation_type="complex_billing_planning")
    async def plan_complex_billing_scenario(
        self,
        billing_scenario: dict[str, Any],
        planning_focus: str = "billing_optimization",
        session_id: str = None,
        user_id: str = None,
    ) -> dict[str, Any]:
        """
        Plan complex billing scenarios using Tree-of-Thoughts reasoning

        Uses advanced planning to handle complex billing situations like:
        - Multi-payer scenarios
        - Complex coding situations
        - Denial management strategies
        - Revenue cycle optimization

        Args:
            billing_scenario: Dictionary containing billing scenario data
            planning_focus: Focus area for planning (billing_optimization, denial_management, etc.)
            session_id: Session ID for tracking
            user_id: User ID for audit trails

        Returns:
            Dictionary containing planning results and recommendations

        Medical Disclaimer: Administrative billing planning only.
        Does not provide medical advice or clinical decision-making.
        """

        try:
            # Increment metrics for Tree-of-Thoughts usage
            await self._metrics.incr("tree_of_thoughts_billing_requests")

            # Validate and sanitize input data for PHI protection
            scan_for_phi(str(billing_scenario))

            # Map planning focus to PlanningFocus enum
            focus_mapping = {
                "billing_optimization": PlanningFocus.BILLING_OPTIMIZATION,
                "coding_compliance": PlanningFocus.CODING_COMPLIANCE,
                "claim_processing": PlanningFocus.CLAIM_PROCESSING,
                "denial_management": PlanningFocus.DENIAL_MANAGEMENT,
                "revenue_cycle": PlanningFocus.REVENUE_CYCLE,
            }

            planning_focus_enum = focus_mapping.get(
                planning_focus.lower(),
                PlanningFocus.BILLING_OPTIMIZATION,
            )

            # Generate Tree-of-Thoughts planning
            tree_result = await self._tree_planner.plan_complex_scenario(
                scenario_data=billing_scenario,
                planning_focus=planning_focus_enum,
                planning_depth=3,
                branches_per_level=3,
                user_id=user_id,
            )

            # Convert tree result to response format
            planning_response = {
                "billing_scenario_analysis": {
                    "scenario_id": tree_result.tree_id,
                    "planning_focus": planning_focus,
                    "confidence_score": tree_result.confidence_score,
                    "final_recommendation": tree_result.final_recommendation,
                },
                "optimal_approach": {
                    "path_steps": [
                        {
                            "level": node.level,
                            "approach": node.approach,
                            "expected_outcome": node.expected_outcome,
                            "success_probability": node.success_probability,
                            "resource_requirements": node.resource_requirements,
                            "risk_assessment": node.risk_assessment,
                        }
                        for node in tree_result.optimal_path
                    ],
                    "overall_viability": tree_result.confidence_score,
                    "implementation_priority": "high" if tree_result.confidence_score > 0.7 else "medium",
                },
                "alternative_approaches": [
                    {
                        "branch_id": branch.branch_id,
                        "path_score": branch.path_score,
                        "implementation_complexity": branch.implementation_complexity,
                        "expected_roi": branch.expected_roi,
                        "compliance_rating": branch.compliance_rating,
                        "approach_summary": branch.nodes[0].approach if branch.nodes else "Alternative approach",
                    }
                    for branch in tree_result.alternative_paths
                ],
                "planning_metadata": {
                    "levels_explored": len(tree_result.planning_levels),
                    "total_branches_evaluated": sum(
                        len(level["branches"]) for level in tree_result.planning_levels
                    ),
                    "planning_timestamp": tree_result.created_at.isoformat(),
                    "session_id": session_id,
                    "user_id": user_id,
                },
                "medical_disclaimer": (
                    "This analysis provides administrative billing planning support only. "
                    "It does not provide medical advice, diagnosis, or treatment recommendations. "
                    "All medical decisions must be made by qualified healthcare professionals."
                ),
                "timestamp": datetime.now().isoformat(),
            }

            # Log Tree-of-Thoughts planning completion
            await self._metrics.incr("tree_of_thoughts_billing_completions")

            log_healthcare_event(
                logger,
                logging.INFO,
                "Tree-of-Thoughts billing planning completed",
                context={
                    "tree_id": tree_result.tree_id,
                    "planning_focus": planning_focus,
                    "confidence_score": tree_result.confidence_score,
                    "optimal_path_steps": len(tree_result.optimal_path),
                    "alternatives_generated": len(tree_result.alternative_paths),
                    "user_id": user_id,
                    "session_id": session_id,
                },
                operation_type="complex_billing_planning",
            )

            return planning_response

        except Exception as e:
            await self._metrics.incr("tree_of_thoughts_billing_errors")

            log_healthcare_event(
                logger,
                logging.ERROR,
                f"Tree-of-Thoughts billing planning failed: {str(e)}",
                context={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "planning_focus": planning_focus,
                    "user_id": user_id,
                    "session_id": session_id,
                },
                operation_type="complex_billing_planning_error",
            )

            # Return error response with fallback to standard processing
            return {
                "billing_scenario_analysis": {
                    "error": "Tree-of-Thoughts planning failed",
                    "error_details": str(e),
                    "fallback_recommendation": "Follow standard billing procedures for this scenario",
                },
                "optimal_approach": {
                    "fallback_used": True,
                    "standard_recommendation": "Process using established billing workflows",
                },
                "alternative_approaches": [],
                "medical_disclaimer": (
                    "This analysis provides administrative billing planning support only. "
                    "It does not provide medical advice, diagnosis, or treatment recommendations. "
                    "All medical decisions must be made by qualified healthcare professionals."
                ),
                "timestamp": datetime.now().isoformat(),
            }


# Initialize the billing helper agent
billing_helper_agent = BillingHelperAgent()
