"""
Shared billing utilities for healthcare billing operations.

This module provides shared utilities for billing calculations, rate negotiations,
and patient coverage data retrieval across multiple billing modules.
"""

import logging
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from core.financial.healthcare_financial_utils import HealthcareFinancialUtils

if TYPE_CHECKING:
    from domains.insurance_calculations import PatientCoverage

logger = logging.getLogger(__name__)


class SharedBillingUtils:
    """Shared utilities for healthcare billing calculations."""

    @staticmethod
    def get_negotiated_rate(cpt_code: str, insurance_type: str) -> Decimal:
        """
        Get negotiated rate for CPT code based on insurance type.

        Args:
            cpt_code: The CPT procedure code
            insurance_type: The type of insurance (medicare, medicaid, ppo, etc.)

        Returns:
            Decimal: The negotiated rate for the procedure
        """
        # Mock negotiated rates - in production, would query insurance contracts
        base_rates = {
            "99213": 150.00,  # Office visit, established patient
            "99214": 200.00,  # Office visit, moderate complexity
            "36415": 25.00,  # Blood draw
            "85025": 35.00,  # CBC lab test
        }

        base_rate = base_rates.get(cpt_code, 100.00)
        base_rate_decimal = HealthcareFinancialUtils.ensure_decimal(base_rate)

        # Apply insurance-specific modifiers
        if insurance_type.lower() == "medicare":
            return base_rate_decimal * Decimal("0.85")  # Medicare typically pays less
        elif insurance_type.lower() == "medicaid":
            return base_rate_decimal * Decimal("0.75")  # Medicaid typically pays less
        else:
            return base_rate_decimal

    @staticmethod
    def get_patient_coverage_data(patient_id: str, insurance_type: str) -> "PatientCoverage":
        """
        Get patient coverage data for insurance calculations.

        Args:
            patient_id: The patient identifier
            insurance_type: The type of insurance

        Returns:
            PatientCoverage: The patient's insurance coverage details
        """
        from domains.insurance_calculations import (
            CopayStructure,
            CopayType,
            InsuranceType,
            PatientCoverage,
        )

        # Mock patient coverage data - in production, would query database
        return PatientCoverage(
            patient_id=patient_id,
            insurance_type=InsuranceType.PPO
            if insurance_type.lower() == "ppo"
            else InsuranceType.HMO,
            annual_deductible=Decimal("2000.00"),
            deductible_met=Decimal("450.00"),
            out_of_pocket_maximum=Decimal("8000.00"),
            out_of_pocket_met=Decimal("1200.00"),
            coinsurance_rate=Decimal("0.20"),  # 20% coinsurance
            copay_structures={
                "office_visit": CopayStructure(
                    copay_type=CopayType.FIXED_DOLLAR,
                    primary_amount=Decimal("25.00"),
                    service_type="office_visit",
                )
            },
        )

    @staticmethod
    def validate_billing_data(billing_data: dict[str, Any]) -> dict[str, Any]:
        """
        Validate billing data for healthcare compliance.

        Args:
            billing_data: The billing data to validate

        Returns:
            Dict: Validation results with any errors found
        """
        validation_errors = []

        # Validate required fields
        required_fields = ["patient_id", "provider_id", "service_date", "procedure_codes"]
        for field in required_fields:
            if field not in billing_data:
                validation_errors.append(f"Missing required field: {field}")

        # Validate financial amounts
        for amount_field in ["billed_amount", "negotiated_rate"]:
            if amount_field in billing_data:
                try:
                    HealthcareFinancialUtils.validate_financial_amount(
                        billing_data[amount_field], amount_field
                    )
                except ValueError as e:
                    validation_errors.append(str(e))

        return {"is_valid": len(validation_errors) == 0, "errors": validation_errors}
