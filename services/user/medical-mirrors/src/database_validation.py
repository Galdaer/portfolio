"""
Database-specific validation for medical mirrors
"""

import logging
from typing import Any

from .validation_utils import DataValidator, ValidationError

logger = logging.getLogger(__name__)


class DatabaseValidator:
    """Validates records before database insertion"""

    @staticmethod
    def validate_pubmed_article(record: dict[str, Any]) -> dict[str, Any]:
        """Validate PubMed article before database insert"""
        validated = {}

        # Required fields
        try:
            validated["pmid"] = DataValidator.validate_required_field(
                record.get("pmid"), "pmid", "pubmed_articles",
            )
            validated["pmid"] = DataValidator.validate_pmid(validated["pmid"])
            if not validated["pmid"]:
                raise ValidationError("Invalid PMID format")
        except ValidationError:
            raise

        # Optional string fields with length limits
        validated["title"] = DataValidator.validate_string_length(
            record.get("title"), "title", "pubmed_articles",
        )
        validated["abstract"] = DataValidator.validate_string_length(
            record.get("abstract"), "abstract", "pubmed_articles",
        )
        validated["journal"] = DataValidator.validate_string_length(
            record.get("journal"), "journal", "pubmed_articles",
        )
        validated["pub_date"] = DataValidator.validate_string_length(
            record.get("pub_date"), "pub_date", "pubmed_articles",
        )

        # DOI validation
        validated["doi"] = DataValidator.validate_doi(record.get("doi"))
        validated["doi"] = DataValidator.validate_string_length(
            validated["doi"], "doi", "pubmed_articles",
        )

        # Array fields
        validated["authors"] = DataValidator.validate_array_field(
            record.get("authors"), "authors", "pubmed_articles",
        )
        validated["mesh_terms"] = DataValidator.validate_array_field(
            record.get("mesh_terms"), "mesh_terms", "pubmed_articles",
        )

        return validated

    @staticmethod
    def validate_clinical_trial(record: dict[str, Any]) -> dict[str, Any]:
        """Validate clinical trial before database insert"""
        validated = {}

        # Required fields
        try:
            validated["nct_id"] = DataValidator.validate_required_field(
                record.get("nct_id"), "nct_id", "clinical_trials",
            )
            validated["nct_id"] = DataValidator.validate_nct_id(validated["nct_id"])
            if not validated["nct_id"]:
                raise ValidationError("Invalid NCT ID format")
        except ValidationError:
            raise

        # String fields with length limits
        validated["title"] = DataValidator.validate_string_length(
            record.get("title"), "title", "clinical_trials",
        )
        validated["status"] = DataValidator.validate_string_length(
            record.get("status"), "status", "clinical_trials",
        )
        validated["phase"] = DataValidator.validate_string_length(
            record.get("phase"), "phase", "clinical_trials",
        )
        validated["study_type"] = DataValidator.validate_string_length(
            record.get("study_type"), "study_type", "clinical_trials",
        )
        validated["start_date"] = DataValidator.validate_string_length(
            record.get("start_date"), "start_date", "clinical_trials",
        )
        validated["completion_date"] = DataValidator.validate_string_length(
            record.get("completion_date"), "completion_date", "clinical_trials",
        )

        # Array fields
        validated["conditions"] = DataValidator.validate_array_field(
            record.get("conditions"), "conditions", "clinical_trials",
        )
        validated["interventions"] = DataValidator.validate_array_field(
            record.get("interventions"), "interventions", "clinical_trials",
        )
        validated["locations"] = DataValidator.validate_array_field(
            record.get("locations"), "locations", "clinical_trials",
        )
        validated["sponsors"] = DataValidator.validate_array_field(
            record.get("sponsors"), "sponsors", "clinical_trials",
        )

        # Integer fields
        validated["enrollment"] = DataValidator.validate_integer(
            record.get("enrollment"), "enrollment", "clinical_trials", min_value=0,
        )

        return validated

    @staticmethod
    def validate_fda_drug(record: dict[str, Any]) -> dict[str, Any]:
        """Validate FDA drug before database insert"""
        validated = {}

        # Required fields
        try:
            validated["ndc"] = DataValidator.validate_required_field(
                record.get("ndc"), "ndc", "drug_information",
            )
            validated["ndc"] = DataValidator.validate_ndc(validated["ndc"])
            if not validated["ndc"]:
                raise ValidationError("Invalid NDC format")

            validated["name"] = DataValidator.validate_required_field(
                record.get("name"), "name", "drug_information",
            )
        except ValidationError:
            raise

        # String fields with length limits
        validated["generic_name"] = DataValidator.validate_string_length(
            record.get("generic_name"), "generic_name", "drug_information",
        )
        validated["brand_name"] = DataValidator.validate_string_length(
            record.get("brand_name"), "brand_name", "drug_information",
        )
        validated["manufacturer"] = DataValidator.validate_string_length(
            record.get("manufacturer"), "manufacturer", "drug_information",
        )
        validated["applicant"] = DataValidator.validate_string_length(
            record.get("applicant"), "applicant", "drug_information",
        )
        validated["strength"] = DataValidator.validate_string_length(
            record.get("strength"), "strength", "drug_information",
        )
        validated["dosage_form"] = DataValidator.validate_string_length(
            record.get("dosage_form"), "dosage_form", "drug_information",
        )
        validated["route"] = DataValidator.validate_string_length(
            record.get("route"), "route", "drug_information",
        )
        validated["application_number"] = DataValidator.validate_string_length(
            record.get("application_number"), "application_number", "drug_information",
        )
        validated["product_number"] = DataValidator.validate_string_length(
            record.get("product_number"), "product_number", "drug_information",
        )
        validated["approval_date"] = DataValidator.validate_string_length(
            record.get("approval_date"), "approval_date", "drug_information",
        )
        validated["orange_book_code"] = DataValidator.validate_string_length(
            record.get("orange_book_code"), "orange_book_code", "drug_information",
        )
        validated["reference_listed_drug"] = DataValidator.validate_string_length(
            record.get("reference_listed_drug"), "reference_listed_drug", "drug_information",
        )
        validated["therapeutic_class"] = DataValidator.validate_string_length(
            record.get("therapeutic_class"), "therapeutic_class", "drug_information",
        )
        validated["pharmacologic_class"] = DataValidator.validate_string_length(
            record.get("pharmacologic_class"), "pharmacologic_class", "drug_information",
        )

        # Array fields
        validated["ingredients"] = DataValidator.validate_array_field(
            record.get("ingredients"), "ingredients", "drug_information",
        )
        validated["data_sources"] = DataValidator.validate_array_field(
            record.get("data_sources"), "data_sources", "drug_information",
        )

        return validated

    @staticmethod
    def validate_icd10_code(record: dict[str, Any]) -> dict[str, Any]:
        """Validate ICD-10 code before database insert"""
        validated = {}

        # Required fields
        try:
            validated["code"] = DataValidator.validate_required_field(
                record.get("code"), "code", "icd10_codes",
            )
            validated["code"] = DataValidator.validate_icd10_code(validated["code"])
            if not validated["code"]:
                raise ValidationError("Invalid ICD-10 code format")

            validated["description"] = DataValidator.validate_required_field(
                record.get("description"), "description", "icd10_codes",
            )
        except ValidationError:
            raise

        # String fields with length limits
        validated["category"] = DataValidator.validate_string_length(
            record.get("category"), "category", "icd10_codes",
        )
        validated["chapter"] = DataValidator.validate_string_length(
            record.get("chapter"), "chapter", "icd10_codes",
        )
        validated["parent_code"] = DataValidator.validate_string_length(
            record.get("parent_code"), "parent_code", "icd10_codes",
        )
        validated["source"] = DataValidator.validate_string_length(
            record.get("source"), "source", "icd10_codes",
        )
        validated["search_text"] = DataValidator.validate_string_length(
            record.get("search_text"), "search_text", "icd10_codes",
        )

        # Boolean fields
        validated["is_billable"] = record.get("is_billable", False)
        if isinstance(validated["is_billable"], str):
            validated["is_billable"] = validated["is_billable"].lower() in ("true", "yes", "1")

        # Integer fields
        validated["code_length"] = DataValidator.validate_integer(
            record.get("code_length"), "code_length", "icd10_codes", min_value=1, max_value=20,
        )

        # JSONB fields (pass through as-is, PostgreSQL will validate)
        validated["synonyms"] = record.get("synonyms")
        validated["inclusion_notes"] = record.get("inclusion_notes")
        validated["exclusion_notes"] = record.get("exclusion_notes")
        validated["children_codes"] = record.get("children_codes")

        return validated

    @staticmethod
    def validate_billing_code(record: dict[str, Any]) -> dict[str, Any]:
        """Validate billing code before database insert"""
        validated = {}

        # Required fields
        try:
            validated["code"] = DataValidator.validate_required_field(
                record.get("code"), "code", "billing_codes",
            )
            validated["code_type"] = DataValidator.validate_required_field(
                record.get("code_type"), "code_type", "billing_codes",
            )
        except ValidationError:
            raise

        # String fields with length limits
        validated["short_description"] = DataValidator.validate_string_length(
            record.get("short_description"), "short_description", "billing_codes",
        )
        validated["long_description"] = DataValidator.validate_string_length(
            record.get("long_description"), "long_description", "billing_codes",
        )
        validated["description"] = DataValidator.validate_string_length(
            record.get("description"), "description", "billing_codes",
        )
        validated["category"] = DataValidator.validate_string_length(
            record.get("category"), "category", "billing_codes",
        )
        validated["coverage_notes"] = DataValidator.validate_string_length(
            record.get("coverage_notes"), "coverage_notes", "billing_codes",
        )
        validated["gender_specific"] = DataValidator.validate_string_length(
            record.get("gender_specific"), "gender_specific", "billing_codes",
        )
        validated["age_specific"] = DataValidator.validate_string_length(
            record.get("age_specific"), "age_specific", "billing_codes",
        )
        validated["source"] = DataValidator.validate_string_length(
            record.get("source"), "source", "billing_codes",
        )
        validated["search_text"] = DataValidator.validate_string_length(
            record.get("search_text"), "search_text", "billing_codes",
        )

        # Boolean fields
        validated["is_active"] = record.get("is_active", True)
        validated["modifier_required"] = record.get("modifier_required", False)
        validated["bilateral_indicator"] = record.get("bilateral_indicator", False)

        # Date fields (stored as strings)
        validated["effective_date"] = DataValidator.validate_date_string(
            record.get("effective_date"),
        )
        validated["termination_date"] = DataValidator.validate_date_string(
            record.get("termination_date"),
        )

        return validated


def validate_record_for_table(record: dict[str, Any], table_name: str) -> dict[str, Any]:
    """
    Validate a record for a specific table using appropriate validator

    Args:
        record: Record data to validate
        table_name: Target table name

    Returns:
        Validated record ready for database insertion

    Raises:
        ValidationError: If validation fails
    """
    try:
        if table_name == "pubmed_articles":
            return DatabaseValidator.validate_pubmed_article(record)
        if table_name == "clinical_trials":
            return DatabaseValidator.validate_clinical_trial(record)
        if table_name == "drug_information":
            return DatabaseValidator.validate_fda_drug(record)
        if table_name == "icd10_codes":
            return DatabaseValidator.validate_icd10_code(record)
        if table_name == "billing_codes":
            return DatabaseValidator.validate_billing_code(record)
        logger.warning(f"No specific validator for table {table_name}, using generic validation")
        # Fallback to generic validation from validation_utils
        from .validation_utils import validate_record
        return validate_record(record, table_name)

    except Exception as e:
        logger.exception(f"Validation failed for {table_name} record: {e}")
        msg = f"Record validation failed: {e}"
        raise ValidationError(msg)


def batch_validate_records(records: list[dict[str, Any]], table_name: str) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Validate a batch of records for a specific table

    Args:
        records: List of records to validate
        table_name: Target table name

    Returns:
        Tuple of (validated_records, failed_record_ids)
    """
    validated_records = []
    failed_record_ids = []

    for record in records:
        try:
            validated_record = validate_record_for_table(record, table_name)
            validated_records.append(validated_record)
        except ValidationError as e:
            # Try to extract record ID for logging
            record_id = (
                record.get("pmid") or
                record.get("nct_id") or
                record.get("ndc") or
                record.get("code") or
                record.get("topic_id") or
                record.get("exercise_id") or
                record.get("fdc_id") or
                "unknown"
            )
            failed_record_ids.append(str(record_id))
            logger.warning(f"Validation failed for record {record_id}: {e}")

    logger.info(
        f"Batch validation for {table_name}: "
        f"{len(validated_records)}/{len(records)} records validated successfully",
    )

    return validated_records, failed_record_ids
