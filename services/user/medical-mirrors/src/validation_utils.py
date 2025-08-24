"""
Data validation utilities for medical mirrors
"""

import logging
import re
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors"""


class DataValidator:
    """Utility class for validating data before database insertion"""

    # Column length limits (updated after migration 004)
    COLUMN_LIMITS = {
        # UpdateLog table
        "update_logs": {
            "source": 100,
            "update_type": 100,
            "status": 50,
        },

        # PubMed articles
        "pubmed_articles": {
            "pmid": 20,
            "pub_date": 50,
            "doi": 200,
        },

        # Clinical Trials
        "clinical_trials": {
            "nct_id": 20,
            "status": 100,
            "phase": 100,
            "start_date": 20,
            "completion_date": 20,
            "study_type": 100,
        },

        # FDA Drugs
        "drug_information": {
            "ndc": 50,
            "dosage_form": 200,
            "route": 200,
            "application_number": 50,
            "product_number": 20,
            "approval_date": 100,
            "orange_book_code": 50,
            "reference_listed_drug": 10,
        },

        # ICD-10 Codes (if table exists)
        "icd10_codes": {
            "code": 30,
            "category": 300,
            "chapter": 50,
            "parent_code": 30,
            "source": 100,
        },

        # Billing Codes (if table exists)
        "billing_codes": {
            "code": 30,
            "code_type": 50,
            "category": 300,
            "gender_specific": 100,
            "age_specific": 100,
            "source": 100,
        },

        # Health Topics (if table exists)
        "health_topics": {
            "topic_id": 100,
            "category": 300,
            "last_reviewed": 100,
            "source": 100,
        },

        # Exercises (if table exists)
        "exercises": {
            "exercise_id": 100,
            "body_part": 200,
            "equipment": 200,
            "target": 200,
            "difficulty_level": 100,
            "exercise_type": 100,
            "duration_estimate": 200,
            "calories_estimate": 200,
            "source": 100,
        },

        # Food Items (if table exists)
        "food_items": {
            "food_category": 300,
            "brand_owner": 300,
            "serving_size_unit": 100,
            "source": 100,
        },
    }

    @classmethod
    def validate_string_length(cls, value: Any, field_name: str, table_name: str,
                             max_length: int | None = None) -> str | None:
        """Validate string length for a specific field"""
        if value is None:
            return None

        # Convert to string if needed
        str_value = str(value).strip()

        # Get max length from limits or use provided max_length
        if max_length is None:
            table_limits = cls.COLUMN_LIMITS.get(table_name, {})
            max_length = table_limits.get(field_name)

        if max_length and len(str_value) > max_length:
            logger.warning(f"Truncating {table_name}.{field_name}: "
                         f"'{str_value[:50]}...' ({len(str_value)} chars > {max_length} limit)")
            return str_value[:max_length]

        return str_value

    @classmethod
    def validate_required_field(cls, value: Any, field_name: str, table_name: str) -> Any:
        """Validate that a required field is not empty"""
        if value is None or (isinstance(value, str) and not value.strip()):
            msg = f"Required field {table_name}.{field_name} is empty"
            raise ValidationError(msg)
        return value

    @classmethod
    def validate_integer(cls, value: Any, field_name: str, table_name: str,
                        min_value: int | None = None, max_value: int | None = None) -> int | None:
        """Validate integer field"""
        if value is None:
            return None

        try:
            int_value = int(value)

            if min_value is not None and int_value < min_value:
                logger.warning(f"Value {int_value} for {table_name}.{field_name} below minimum {min_value}")
                return min_value

            if max_value is not None and int_value > max_value:
                logger.warning(f"Value {int_value} for {table_name}.{field_name} above maximum {max_value}")
                return max_value

            return int_value

        except (ValueError, TypeError):
            logger.warning(f"Invalid integer value '{value}' for {table_name}.{field_name}, setting to None")
            return None

    @classmethod
    def validate_email(cls, email: str) -> bool:
        """Validate email format"""
        if not email:
            return False

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(email_pattern, email))

    @classmethod
    def validate_doi(cls, doi: str) -> str | None:
        """Validate DOI format"""
        if not doi:
            return None

        doi_str = str(doi).strip()

        # Standard DOI pattern: 10.xxxx/xxxxx
        standard_doi_pattern = r"^10\.\d{4,}/.+"
        if re.match(standard_doi_pattern, doi_str):
            return doi_str

        # Handle common malformed DOIs missing "10." prefix
        # If it looks like a DOI but missing 10. prefix, try to fix it
        missing_prefix_pattern = r"^\d{4,}/.+"
        if re.match(missing_prefix_pattern, doi_str):
            fixed_doi = f"10.{doi_str}"
            logger.debug(f"Fixed DOI missing prefix: {doi_str} -> {fixed_doi}")
            return fixed_doi

        # For other formats, log warning but return as-is
        logger.warning(f"Invalid DOI format: {doi_str}")
        return doi_str

    @classmethod
    def validate_pmid(cls, pmid: str) -> str | None:
        """Validate PubMed ID format"""
        if not pmid:
            return None

        # PMID should be numeric
        pmid_str = str(pmid).strip()
        if pmid_str.isdigit():
            return cls.validate_string_length(pmid_str, "pmid", "pubmed_articles")
        logger.warning(f"Invalid PMID format: {pmid}")
        return None

    @classmethod
    def validate_nct_id(cls, nct_id: str) -> str | None:
        """Validate ClinicalTrials.gov NCT ID format"""
        if not nct_id:
            return None

        # NCT ID pattern: NCTxxxxxxxx
        nct_pattern = r"^NCT\d{8}$"
        nct_str = str(nct_id).strip().upper()

        if re.match(nct_pattern, nct_str):
            return cls.validate_string_length(nct_str, "nct_id", "clinical_trials")
        logger.warning(f"Invalid NCT ID format: {nct_id}")
        return None

    @classmethod
    def validate_ndc(cls, ndc: str) -> str | None:
        """Validate NDC (National Drug Code) format"""
        if not ndc:
            return None

        ndc_str = str(ndc).strip()

        # Allow synthetic NDCs (starting with OB_, DF_, etc)
        if ndc_str.startswith(("OB_", "DF_", "DL_")):
            return cls.validate_string_length(ndc_str, "ndc", "drug_information")

        # Real NDC format validation (various formats allowed)
        # Remove hyphens and spaces for validation
        clean_ndc = re.sub(r"[-\s]", "", ndc_str)
        if clean_ndc.isdigit() and len(clean_ndc) >= 10:
            return cls.validate_string_length(ndc_str, "ndc", "drug_information")
        logger.warning(f"Invalid NDC format: {ndc}")
        return cls.validate_string_length(ndc_str, "ndc", "drug_information")  # Allow but log warning

    @classmethod
    def validate_icd10_code(cls, code: str) -> str | None:
        """Validate ICD-10 code format"""
        if not code:
            return None

        code_str = str(code).strip().upper()

        # ICD-10 pattern: Letter followed by digits, with optional decimal point and more digits
        icd10_pattern = r"^[A-Z]\d{2}(\.\d+)?$"

        if re.match(icd10_pattern, code_str):
            return cls.validate_string_length(code_str, "code", "icd10_codes")
        # Allow but log warning for non-standard formats
        logger.warning(f"Non-standard ICD-10 code format: {code}")
        return cls.validate_string_length(code_str, "code", "icd10_codes")

    @classmethod
    def validate_array_field(cls, value: Any, field_name: str, table_name: str,
                           max_items: int = 100) -> list[str]:
        """Validate array field"""
        if value is None:
            return []

        if isinstance(value, str):
            # Convert string to list (split on common delimiters)
            items = [item.strip() for item in re.split(r"[,;|]", value) if item.strip()]
        elif isinstance(value, list):
            items = [str(item).strip() for item in value if item]
        else:
            logger.warning(f"Invalid array format for {table_name}.{field_name}: {type(value)}")
            return []

        # Limit number of items
        if len(items) > max_items:
            logger.warning(f"Truncating {table_name}.{field_name} array from {len(items)} to {max_items} items")
            items = items[:max_items]

        return items

    @classmethod
    def validate_date_string(cls, date_value: Any) -> str | None:
        """Validate and normalize date string"""
        if not date_value:
            return None

        date_str = str(date_value).strip()

        # Try to parse various date formats
        date_formats = [
            "%Y-%m-%d",           # 2023-01-15
            "%Y/%m/%d",           # 2023/01/15
            "%m/%d/%Y",           # 01/15/2023
            "%m-%d-%Y",           # 01-15-2023
            "%d/%m/%Y",           # 15/01/2023
            "%d-%m-%Y",           # 15-01-2023
            "%Y",                 # 2023
            "%Y-%m",              # 2023-01 (YYYY-MM format common in medical data)
            "%Y-%b",              # 1979-Feb (YYYY-Mon format from ClinicalTrials/PubMed)
            "%Y-%B",              # 1979-February (YYYY-Month format)
            "%Y-%b-%d",           # 1979-Jul-01 (YYYY-Mon-DD format from medical data)
            "%Y-%B-%d",           # 1979-July-01 (YYYY-Month-DD format)
            "%B %Y",              # January 2023
            "%b %Y",              # Jan 2023
            "%B %d, %Y",          # January 15, 2023
            "%b %d, %Y",          # Jan 15, 2023
        ]

        for date_format in date_formats:
            try:
                datetime.strptime(date_str, date_format)
                return date_str  # Return original format if successfully parsed
            except ValueError:
                continue

        # If no format matches, return as-is but log warning
        logger.warning(f"Unable to parse date format: {date_str}")
        return date_str


def validate_record(record: dict[str, Any], table_name: str,
                   required_fields: list[str] | None = None) -> dict[str, Any]:
    """
    Validate a complete record for a specific table

    Args:
        record: Dictionary containing record data
        table_name: Name of the target table
        required_fields: List of fields that must not be empty

    Returns:
        Validated and potentially modified record

    Raises:
        ValidationError: If required fields are missing or invalid
    """
    validated_record = {}

    # Validate required fields first
    if required_fields:
        for field in required_fields:
            if field in record:
                validated_record[field] = DataValidator.validate_required_field(
                    record[field], field, table_name,
                )
            else:
                msg = f"Missing required field: {field}"
                raise ValidationError(msg)

    # Validate all other fields
    for field, value in record.items():
        if field in validated_record:
            continue  # Already validated as required field

        validated_record[field] = _validate_field_by_type(
            value, field, table_name,
        )

    return validated_record


def _validate_field_by_type(value: Any, field_name: str, table_name: str) -> Any:
    """Validate a field based on its name and expected type"""

    # Special handling for specific field types
    if field_name in ["pmid"]:
        return DataValidator.validate_pmid(value)
    if field_name in ["nct_id"]:
        return DataValidator.validate_nct_id(value)
    if field_name in ["ndc"]:
        return DataValidator.validate_ndc(value)
    if field_name in ["doi"]:
        return DataValidator.validate_doi(value)
    if field_name.endswith("_date") or field_name in ["pub_date", "approval_date"]:
        return DataValidator.validate_date_string(value)
    if field_name in ["authors", "ingredients", "mesh_terms", "conditions",
                       "interventions", "locations", "sponsors", "data_sources"]:
        return DataValidator.validate_array_field(value, field_name, table_name)
    if field_name in ["enrollment", "fdc_id", "code_length", "content_length"]:
        return DataValidator.validate_integer(value, field_name, table_name, min_value=0)
    if field_name.startswith("is_") or field_name.endswith(("_required", "_indicator")):
        # Boolean fields
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "yes", "1", "on")
        return bool(value)
    # Default string validation
    return DataValidator.validate_string_length(value, field_name, table_name)
