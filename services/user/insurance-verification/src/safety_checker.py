"""
Safety validation and input checking for insurance verification
"""

import logging
import re
from datetime import date, datetime
from typing import Any

from models.verification_models import (
    BenefitsInquiryRequest,
    InsuranceVerificationRequest,
    PriorAuthRequest,
)

logger = logging.getLogger(__name__)


class InsuranceSafetyChecker:
    """Safety validation for insurance verification requests and responses"""

    def __init__(self):
        # PHI patterns to detect and flag
        self.phi_patterns = {
            "ssn": re.compile(r"\b\d{3}-?\d{2}-?\d{4}\b"),
            "phone": re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"),
            "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
            "mrn": re.compile(r"\b(mrn|medical.?record.?number)\s*:?\s*\d+\b", re.IGNORECASE),
            "dob": re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"),
        }

    async def validate_verification_request(
        self,
        request: InsuranceVerificationRequest,
    ) -> dict[str, Any]:
        """Validate insurance verification request for safety and compliance"""

        issues = []
        warnings = []

        # Required fields validation
        required_fields = ["member_id", "provider_id"]
        for field in required_fields:
            value = getattr(request, field, None)
            if not value:
                issues.append(f"Missing required field: {field}")

        # Member ID validation
        if request.member_id:
            if len(request.member_id) < 6:
                issues.append("Member ID too short (minimum 6 characters)")
            elif len(request.member_id) > 20:
                issues.append("Member ID too long (maximum 20 characters)")

            # Check for potentially invalid characters
            if not re.match(r"^[A-Za-z0-9\-]+$", request.member_id):
                issues.append("Member ID contains invalid characters")

        # Provider ID validation
        if request.provider_id:
            if len(request.provider_id) < 3:
                issues.append("Provider ID too short")
            elif len(request.provider_id) > 15:
                issues.append("Provider ID too long")

        # Service codes validation
        if request.service_codes:
            for code in request.service_codes:
                if not self._validate_service_code(code):
                    warnings.append(f"Invalid service code format: {code}")

        # Date validation
        if request.patient_dob:
            if not self._validate_date_format(request.patient_dob):
                issues.append("Invalid patient date of birth format (use YYYY-MM-DD)")
            else:
                # Check if DOB is reasonable
                try:
                    dob = datetime.strptime(request.patient_dob, "%Y-%m-%d").date()
                    if dob > date.today():
                        issues.append("Patient date of birth cannot be in the future")
                    elif (date.today() - dob).days > 50000:  # ~137 years
                        warnings.append("Patient date of birth seems unusually old")
                except ValueError:
                    issues.append("Invalid date format for patient date of birth")

        if request.service_date and not self._validate_date_format(request.service_date):
            issues.append("Invalid service date format (use YYYY-MM-DD)")

        # NPI validation
        if request.provider_npi and not self._validate_npi(request.provider_npi):
            issues.append("Invalid NPI format")

        # PHI detection
        phi_detected = await self._scan_for_phi(request.dict())
        if phi_detected:
            warnings.extend([f"Potential PHI detected: {phi_type}" for phi_type in phi_detected])

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "phi_detected": phi_detected,
            "safe_to_proceed": len(issues) == 0 and len(phi_detected) == 0,
        }

    async def validate_prior_auth_request(
        self,
        request: PriorAuthRequest,
    ) -> dict[str, Any]:
        """Validate prior authorization request"""

        issues = []
        warnings = []

        # Required fields
        required_fields = ["member_id", "provider_id", "service_codes"]
        for field in required_fields:
            value = getattr(request, field, None)
            if not value:
                issues.append(f"Missing required field: {field}")

        # Service codes validation (required for prior auth)
        if not request.service_codes:
            issues.append("Service codes are required for prior authorization")
        else:
            for code in request.service_codes:
                if not self._validate_service_code(code):
                    warnings.append(f"Invalid service code format: {code}")

        # Diagnosis codes validation
        if request.diagnosis_codes:
            for code in request.diagnosis_codes:
                if not self._validate_diagnosis_code(code):
                    warnings.append(f"Invalid diagnosis code format: {code}")

        # Urgency level validation
        valid_urgency_levels = ["routine", "urgent", "emergency"]
        if request.urgency_level not in valid_urgency_levels:
            issues.append(f"Invalid urgency level. Must be one of: {valid_urgency_levels}")

        # Clinical notes validation
        if request.clinical_notes:
            if len(request.clinical_notes) > 2000:
                warnings.append("Clinical notes are very long (>2000 characters)")

            # Check for potential PHI in clinical notes
            phi_in_notes = await self._scan_text_for_phi(request.clinical_notes)
            if phi_in_notes:
                warnings.extend([f"Potential PHI in clinical notes: {phi_type}" for phi_type in phi_in_notes])

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "safe_to_proceed": len(issues) == 0,
        }

    async def validate_benefits_request(
        self,
        request: BenefitsInquiryRequest,
    ) -> dict[str, Any]:
        """Validate benefits inquiry request"""

        issues = []
        warnings = []

        # Member ID is required
        if not request.member_id:
            issues.append("Missing required field: member_id")

        # Service codes validation (if provided)
        if request.service_codes:
            for code in request.service_codes:
                if not self._validate_service_code(code):
                    warnings.append(f"Invalid service code format: {code}")

        # Benefit categories validation (if provided)
        valid_categories = [
            "medical", "surgical", "preventive", "mental_health",
            "substance_abuse", "prescription", "dental", "vision",
            "maternity", "emergency", "urgent_care",
        ]

        if request.benefit_categories:
            for category in request.benefit_categories:
                if category not in valid_categories:
                    warnings.append(f"Unknown benefit category: {category}")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "safe_to_proceed": len(issues) == 0,
        }

    async def validate_response(
        self,
        response_data: dict[str, Any],
        request_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate response data for consistency and safety"""

        issues = []
        warnings = []

        # Check for data consistency
        if "member_id" in response_data and "member_id" in request_data:
            if response_data["member_id"] != request_data["member_id"]:
                issues.append("Response member_id does not match request")

        # Check for reasonable values
        if "copay_amount" in response_data:
            copay = response_data["copay_amount"]
            if copay is not None and (copay < 0 or copay > 1000):
                warnings.append(f"Unusual copay amount: ${copay}")

        if "deductible_remaining" in response_data:
            deductible = response_data["deductible_remaining"]
            if deductible is not None and (deductible < 0 or deductible > 50000):
                warnings.append(f"Unusual deductible amount: ${deductible}")

        # Check for potential PHI in response
        phi_detected = await self._scan_for_phi(response_data)
        if phi_detected:
            warnings.extend([f"Potential PHI in response: {phi_type}" for phi_type in phi_detected])

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "phi_detected": phi_detected,
        }

    def _validate_service_code(self, code: str) -> bool:
        """Validate CPT/HCPCS service code format"""
        if not code:
            return False

        # CPT codes: 5 digits
        # HCPCS codes: 1 letter + 4 digits
        cpt_pattern = r"^\d{5}$"
        hcpcs_pattern = r"^[A-Z]\d{4}$"

        return bool(re.match(cpt_pattern, code) or re.match(hcpcs_pattern, code))

    def _validate_diagnosis_code(self, code: str) -> bool:
        """Validate ICD-10 diagnosis code format"""
        if not code:
            return False

        # ICD-10: 1 letter + 2 digits + optional dot + up to 4 more characters
        icd10_pattern = r"^[A-Z]\d{2}(\.\w{1,4})?$"

        return bool(re.match(icd10_pattern, code))

    def _validate_npi(self, npi: str) -> bool:
        """Validate National Provider Identifier format"""
        if not npi:
            return False

        # NPI: exactly 10 digits
        return bool(re.match(r"^\d{10}$", npi))

    def _validate_date_format(self, date_str: str) -> bool:
        """Validate date format (YYYY-MM-DD)"""
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    async def _scan_for_phi(self, data: dict[str, Any]) -> list[str]:
        """Scan data for potential PHI"""
        phi_detected = []

        # Convert data to string for scanning
        data_str = str(data)

        for phi_type, pattern in self.phi_patterns.items():
            if pattern.search(data_str):
                phi_detected.append(phi_type)

        return phi_detected

    async def _scan_text_for_phi(self, text: str) -> list[str]:
        """Scan text for potential PHI"""
        phi_detected = []

        for phi_type, pattern in self.phi_patterns.items():
            if pattern.search(text):
                phi_detected.append(phi_type)

        return phi_detected
