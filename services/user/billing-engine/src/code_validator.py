"""
Medical Code Validation for Billing Engine
Validates CPT, HCPCS, ICD-10, and other medical codes
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from models.billing_models import BillingCodeType, CodeValidationRequest, CodeValidationResult

logger = logging.getLogger(__name__)


class MedicalCodeValidator:
    """Validates medical billing codes for accuracy and compliance"""
    
    def __init__(self):
        # Code validation patterns
        self.code_patterns = {
            BillingCodeType.CPT: re.compile(r'^\d{5}$'),
            BillingCodeType.HCPCS: re.compile(r'^[A-Z]\d{4}$'),
            BillingCodeType.ICD10: re.compile(r'^[A-Z]\d{2}(\.\w{1,4})?$'),
            BillingCodeType.DRG: re.compile(r'^\d{3}$'),
            BillingCodeType.MODIFIER: re.compile(r'^[A-Z0-9]{2}$')
        }
        
        # Common invalid code ranges (mock data - replace with real validation database)
        self.invalid_ranges = {
            BillingCodeType.CPT: [
                (0, 99), (100, 999), (10022, 10040), (19499, 19500)
            ]
        }
        
        # Code cross-reference validation rules
        self.validation_rules = {
            "age_restrictions": {},
            "gender_restrictions": {},
            "procedure_combinations": {},
            "diagnosis_requirements": {}
        }
    
    async def validate_codes(
        self,
        request: CodeValidationRequest
    ) -> CodeValidationResult:
        """Validate a list of medical codes"""
        
        validation_id = f"validation_{uuid4().hex[:8]}"
        validated_codes = []
        validation_errors = []
        validation_warnings = []
        suggested_corrections = []
        
        for code in request.codes:
            # Validate individual code
            code_result = await self._validate_single_code(
                code, request.code_type, request.service_date
            )
            validated_codes.append(code_result)
            
            # Collect errors and warnings
            if not code_result["valid"]:
                validation_errors.extend(code_result.get("errors", []))
            
            validation_warnings.extend(code_result.get("warnings", []))
            
            # Generate suggestions for invalid codes
            if not code_result["valid"] and code_result.get("suggested_correction"):
                suggested_corrections.append({
                    "original_code": code,
                    "suggested_code": code_result["suggested_correction"],
                    "reason": code_result.get("correction_reason", "")
                })
        
        # Cross-validate codes if diagnosis codes provided
        if request.diagnosis_codes:
            cross_validation = await self._cross_validate_codes(
                request.codes, request.diagnosis_codes, request.code_type
            )
            validation_warnings.extend(cross_validation["warnings"])
            validation_errors.extend(cross_validation["errors"])
        
        # Validate code combinations
        combination_validation = await self._validate_code_combinations(
            request.codes, request.code_type
        )
        validation_warnings.extend(combination_validation["warnings"])
        validation_errors.extend(combination_validation["errors"])
        
        overall_valid = len(validation_errors) == 0
        
        return CodeValidationResult(
            validation_id=validation_id,
            validated_codes=validated_codes,
            overall_valid=overall_valid,
            validation_errors=validation_errors,
            validation_warnings=validation_warnings,
            suggested_corrections=suggested_corrections
        )
    
    async def _validate_single_code(
        self,
        code: str,
        code_type: BillingCodeType,
        service_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Validate a single medical code"""
        
        result = {
            "code": code,
            "code_type": code_type.value,
            "valid": False,
            "errors": [],
            "warnings": [],
            "details": {}
        }
        
        # Basic format validation
        pattern = self.code_patterns.get(code_type)
        if not pattern or not pattern.match(code):
            result["errors"].append(f"Invalid {code_type.value.upper()} code format: {code}")
            result["suggested_correction"] = await self._suggest_format_correction(code, code_type)
            return result
        
        # Check against invalid ranges
        if code_type in self.invalid_ranges:
            numeric_code = self._extract_numeric_part(code)
            if numeric_code and self._is_in_invalid_range(numeric_code, code_type):
                result["errors"].append(f"Code {code} is in an invalid range")
                return result
        
        # Date-specific validations
        if service_date:
            date_validation = await self._validate_code_date(code, code_type, service_date)
            if not date_validation["valid"]:
                result["warnings"].extend(date_validation["warnings"])
        
        # Code-specific validations based on type
        if code_type == BillingCodeType.CPT:
            cpt_validation = await self._validate_cpt_specific(code, service_date)
            result["details"].update(cpt_validation["details"])
            result["warnings"].extend(cpt_validation["warnings"])
        elif code_type == BillingCodeType.ICD10:
            icd_validation = await self._validate_icd10_specific(code)
            result["details"].update(icd_validation["details"])
            result["warnings"].extend(icd_validation["warnings"])
        
        # If we get here, basic validation passed
        result["valid"] = True
        result["details"]["validation_level"] = "basic_format_passed"
        
        return result
    
    async def _validate_cpt_specific(
        self,
        cpt_code: str,
        service_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """CPT-specific validation logic"""
        
        details = {}
        warnings = []
        
        numeric_code = int(cpt_code)
        
        # Categorize CPT code
        if 99201 <= numeric_code <= 99499:
            details["category"] = "Evaluation and Management"
            details["category_code"] = "E&M"
        elif 10021 <= numeric_code <= 69990:
            details["category"] = "Surgery"
            details["category_code"] = "Surgery"
        elif 70010 <= numeric_code <= 79999:
            details["category"] = "Radiology"
            details["category_code"] = "Radiology"
        elif 80047 <= numeric_code <= 89398:
            details["category"] = "Pathology and Laboratory"
            details["category_code"] = "Lab"
        elif 90281 <= numeric_code <= 99607:
            details["category"] = "Medicine"
            details["category_code"] = "Medicine"
        else:
            details["category"] = "Unknown"
            warnings.append(f"CPT code {cpt_code} category could not be determined")
        
        # Check for common billing issues
        if numeric_code in [99201, 99202, 99203]:  # New patient E&M
            warnings.append("Ensure patient is truly new (no visits in past 3 years)")
        
        if 90000 <= numeric_code <= 90999:  # Vaccines
            warnings.append("Verify vaccine administration and counseling documentation")
        
        return {
            "details": details,
            "warnings": warnings
        }
    
    async def _validate_icd10_specific(self, icd_code: str) -> Dict[str, Any]:
        """ICD-10 specific validation logic"""
        
        details = {}
        warnings = []
        
        # Extract main category
        main_category = icd_code[0]
        
        # Categorize ICD-10 code
        category_map = {
            'A': 'Infectious and parasitic diseases',
            'B': 'Infectious and parasitic diseases',
            'C': 'Neoplasms',
            'D': 'Diseases of blood and certain immune disorders/Neoplasms',
            'E': 'Endocrine, nutritional and metabolic diseases',
            'F': 'Mental and behavioral disorders',
            'G': 'Diseases of the nervous system',
            'H': 'Diseases of the eye/ear',
            'I': 'Diseases of the circulatory system',
            'J': 'Diseases of the respiratory system',
            'K': 'Diseases of the digestive system',
            'L': 'Diseases of the skin',
            'M': 'Diseases of the musculoskeletal system',
            'N': 'Diseases of the genitourinary system',
            'O': 'Pregnancy, childbirth and puerperium',
            'P': 'Conditions originating in the perinatal period',
            'Q': 'Congenital malformations',
            'R': 'Symptoms, signs and abnormal findings',
            'S': 'Injury, poisoning',
            'T': 'Injury, poisoning',
            'V': 'External causes of morbidity',
            'W': 'External causes of morbidity',
            'X': 'External causes of morbidity',
            'Y': 'External causes of morbidity',
            'Z': 'Factors influencing health status'
        }
        
        details["category"] = category_map.get(main_category, "Unknown category")
        details["main_category_code"] = main_category
        
        # Specificity warnings
        if len(icd_code) <= 4:
            warnings.append(f"ICD-10 code {icd_code} may lack specificity - consider more detailed code")
        
        # Gender-specific warnings
        if main_category == 'O':  # Pregnancy codes
            warnings.append("Verify patient gender is female for pregnancy-related diagnosis")
        
        if main_category in ['C', 'D']:  # Neoplasms
            warnings.append("Ensure neoplasm behavior and site are correctly specified")
        
        return {
            "details": details,
            "warnings": warnings
        }
    
    async def _cross_validate_codes(
        self,
        service_codes: List[str],
        diagnosis_codes: List[str],
        code_type: BillingCodeType
    ) -> Dict[str, Any]:
        """Cross-validate service codes against diagnosis codes"""
        
        warnings = []
        errors = []
        
        # Mock cross-validation logic (replace with real clinical decision support)
        for service_code in service_codes:
            if not await self._is_service_supported_by_diagnoses(service_code, diagnosis_codes):
                warnings.append(
                    f"Service code {service_code} may not be supported by provided diagnoses"
                )
        
        return {
            "warnings": warnings,
            "errors": errors
        }
    
    async def _validate_code_combinations(
        self,
        codes: List[str],
        code_type: BillingCodeType
    ) -> Dict[str, Any]:
        """Validate combinations of codes for potential conflicts"""
        
        warnings = []
        errors = []
        
        if code_type == BillingCodeType.CPT:
            # Check for mutually exclusive procedures
            exclusive_pairs = [
                ("99213", "99214"),  # Can't bill both E&M levels same day
                ("29881", "29882")   # Arthroscopy procedures
            ]
            
            for code1, code2 in exclusive_pairs:
                if code1 in codes and code2 in codes:
                    warnings.append(f"Codes {code1} and {code2} may be mutually exclusive")
        
        return {
            "warnings": warnings,
            "errors": errors
        }
    
    async def _validate_code_date(
        self,
        code: str,
        code_type: BillingCodeType,
        service_date: datetime
    ) -> Dict[str, Any]:
        """Validate code against service date (e.g., code effective dates)"""
        
        warnings = []
        valid = True
        
        # Mock date validation - in production, check against code effective date tables
        if service_date.year < 2015:  # ICD-10 implementation
            if code_type == BillingCodeType.ICD10:
                warnings.append(f"ICD-10 code {code} used before ICD-10 implementation date")
        
        # Check for deprecated codes
        deprecated_codes = ["99201", "99202", "99203"]  # Mock deprecated codes
        if code in deprecated_codes and service_date.year >= 2024:
            warnings.append(f"Code {code} may be deprecated for services after 2023")
        
        return {
            "valid": valid,
            "warnings": warnings
        }
    
    # Helper methods
    def _extract_numeric_part(self, code: str) -> Optional[int]:
        """Extract numeric part from code"""
        try:
            numeric_part = re.sub(r'[^0-9]', '', code)
            return int(numeric_part) if numeric_part else None
        except ValueError:
            return None
    
    def _is_in_invalid_range(self, numeric_code: int, code_type: BillingCodeType) -> bool:
        """Check if numeric code is in invalid range"""
        ranges = self.invalid_ranges.get(code_type, [])
        return any(start <= numeric_code <= end for start, end in ranges)
    
    async def _suggest_format_correction(
        self,
        code: str,
        code_type: BillingCodeType
    ) -> Optional[str]:
        """Suggest format correction for invalid code"""
        
        if code_type == BillingCodeType.CPT:
            # Try to pad with zeros
            numeric_part = re.sub(r'[^0-9]', '', code)
            if numeric_part and len(numeric_part) < 5:
                return numeric_part.zfill(5)
        
        elif code_type == BillingCodeType.ICD10:
            # Try to add decimal point
            if len(code) >= 3 and '.' not in code:
                return f"{code[:3]}.{code[3:]}"
        
        return None
    
    async def _is_service_supported_by_diagnoses(
        self,
        service_code: str,
        diagnosis_codes: List[str]
    ) -> bool:
        """Check if service is medically supported by diagnoses"""
        
        # Mock validation - in production, use clinical decision support system
        # This would check medical necessity rules
        
        # Simple example: certain procedures require specific diagnoses
        service_diagnosis_map = {
            "29881": ["M23", "S83"],  # Knee arthroscopy requires knee conditions
            "99213": [],  # E&M codes generally don't require specific diagnoses
        }
        
        required_patterns = service_diagnosis_map.get(service_code, [])
        if not required_patterns:
            return True  # No specific requirements
        
        for pattern in required_patterns:
            if any(diag_code.startswith(pattern) for diag_code in diagnosis_codes):
                return True
        
        return False