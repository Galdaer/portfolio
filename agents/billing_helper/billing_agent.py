"""
Healthcare Billing Helper Agent - Administrative Billing Support Only
Handles medical billing, claims processing, and coding assistance for administrative workflows
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from agents import BaseHealthcareAgent
from core.infrastructure.healthcare_logger import (
    get_healthcare_logger,
    healthcare_log_method,
    log_healthcare_event,
)
from core.infrastructure.phi_monitor import phi_monitor_decorator, sanitize_healthcare_data, scan_for_phi

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

    def __init__(self) -> None:
        super().__init__(agent_name="billing_helper", agent_type="billing_helper")
        self.agent_type = "billing_helper"
        self.capabilities = [
            "claims_processing",
            "code_validation",
            "insurance_verification",
            "compliance_checking",
            "denial_management",
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
                "capabilities": self.capabilities,
            },
            operation_type="agent_initialization",
        )

    @healthcare_log_method(operation_type="claim_processing", phi_risk_level="medium")
    @phi_monitor_decorator(risk_level="medium", operation_type="billing_processing")
    async def process_claim(self, claim_data: dict[str, Any]) -> BillingResult:
        """
        Process medical billing claim with compliance validation

        Args:
            claim_data: Dictionary containing claim information

        Returns:
            BillingResult with processing status and validation

        Medical Disclaimer: Administrative billing support only.
        Does not provide medical advice or clinical decision-making.
        """
        # Validate and sanitize input data for PHI protection
        scan_for_phi(str(claim_data))

        processing_errors = []
        claim_number = None

        try:
            # Validate required fields
            required_fields = ["patient_id", "provider_id", "service_date", "procedure_codes"]
            for field in required_fields:
                if field not in claim_data:
                    processing_errors.append(f"Missing required field: {field}")

            if processing_errors:
                return BillingResult(
                    billing_id=f"bill_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    status="validation_failed",
                    claim_number=None,
                    total_amount=None,
                    processing_errors=processing_errors,
                    compliance_validated=False,
                    timestamp=datetime.now(),
                    metadata={"validation_stage": "required_fields"},
                )

            # Validate CPT codes
            cpt_validations = []
            for code in claim_data.get("procedure_codes", []):
                validation = await self.validate_cpt_code(code)
                cpt_validations.append(validation)
                if not validation.is_valid:
                    processing_errors.append(f"Invalid CPT code: {code}")

            # Validate ICD-10 codes
            icd_validations = []
            for code in claim_data.get("diagnosis_codes", []):
                validation = await self.validate_icd_code(code)
                icd_validations.append(validation)
                if not validation.is_valid:
                    processing_errors.append(f"Invalid ICD-10 code: {code}")

            # Calculate total amount
            total_amount = self._calculate_claim_amount(claim_data, cpt_validations)

            # Generate claim number if validation passes
            if not processing_errors:
                claim_number = f"CLM{datetime.now().strftime('%Y%m%d%H%M%S')}"
                status = "processed"
                compliance_validated = True
            else:
                status = "requires_correction"
                compliance_validated = False

            log_healthcare_event(
                logger,
                logging.INFO,
                f"Claim processing completed: {status}",
                context={
                    "claim_number": claim_number,
                    "total_amount": total_amount,
                    "error_count": len(processing_errors),
                    "compliance_validated": compliance_validated,
                },
                operation_type="claim_processing",
            )

            return BillingResult(
                billing_id=f"bill_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                status=status,
                claim_number=claim_number,
                total_amount=total_amount,
                processing_errors=processing_errors,
                compliance_validated=compliance_validated,
                timestamp=datetime.now(),
                metadata={
                    "cpt_validations": len(cpt_validations),
                    "icd_validations": len(icd_validations),
                    "processing_stage": "complete",
                },
            )

        except Exception as e:
            log_healthcare_event(
                logger,
                logging.ERROR,
                f"Claim processing failed: {str(e)}",
                context={"error": str(e), "error_type": type(e).__name__},
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

    @healthcare_log_method(operation_type="cpt_validation", phi_risk_level="low")
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
        else:
            return CPTCodeValidation(
                code=clean_code,
                is_valid=False,
                description=None,
                modifier_required=False,
                billing_notes=[f"CPT code {clean_code} not found in database"],
            )

    @healthcare_log_method(operation_type="icd_validation", phi_risk_level="low")
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
        else:
            return ICDCodeValidation(
                code=clean_code,
                is_valid=False,
                description=None,
                category=None,
                billing_notes=[f"ICD-10 code {clean_code} not found in database"],
            )

    def _calculate_claim_amount(
        self, claim_data: dict[str, Any], cpt_validations: list[CPTCodeValidation]
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
                result = await self.process_claim(
                    request.get("billing_data", {})
                )
                base_response.update({"billing_result": result})
                
            elif request_type == "insurance_verification":
                result = await self.verify_insurance_benefits(
                    request.get("insurance_info", {})
                )
                base_response.update({"verification_result": result})
                
            elif request_type == "report_generation":
                result = await self.generate_billing_report(
                    request.get("date_range", {}),
                    request.get("report_type", "summary")
                )
                base_response.update({"report": result})
                
            else:
                base_response.update({
                    "success": False,
                    "error": f"Unknown request type: {request_type}",
                    "supported_types": ["billing_processing", "insurance_verification", "report_generation"]
                })
                
        except Exception as e:
            base_response.update({
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            })
            
        return base_response


# Initialize the billing helper agent
billing_helper_agent = BillingHelperAgent()
