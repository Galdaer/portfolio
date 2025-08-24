"""
Medical Entity Extractor for Healthcare Document Processing

Integrates with existing SciSpacy service to extract medical entities from documents.
Uses existing HTTP client infrastructure for service communication.
"""

import logging
from typing import Any

from core.infrastructure.healthcare_logger import get_healthcare_logger, log_healthcare_event
from core.infrastructure.http_client import HTTPRequestSpec, http_request


class MedicalEntityExtractor:
    """
    Extracts medical entities using the existing SciSpacy service

    Integrates with the healthcare-api's SciSpacy service to provide
    medical entity extraction with proper healthcare compliance logging.
    """

    def __init__(self, scispacy_url: str = "http://scispacy:8010"):
        """
        Initialize medical entity extractor

        Args:
            scispacy_url: URL for the SciSpacy service
        """
        self.logger = get_healthcare_logger("document_processor.entity_extractor")
        self.scispacy_url = scispacy_url.rstrip("/")

        # Medical entity configuration
        self.high_priority_entities = {
            "SIMPLE_CHEMICAL",  # Medications, drugs
            "PATHOLOGICAL_FORMATION",  # Diseases, conditions
            "ORGAN",  # Body parts, organs
            "GENE_OR_GENE_PRODUCT",  # Genetic information
        }

        # Administrative disclaimer
        self.disclaimer = (
            "Medical entity extraction provides administrative document organization only. "
            "All extracted entities should be reviewed by qualified healthcare professionals."
        )

        log_healthcare_event(
            self.logger,
            logging.INFO,
            f"Medical entity extractor initialized: {scispacy_url}",
            context={
                "service_url": scispacy_url,
                "high_priority_entities": list(self.high_priority_entities),
                "administrative_use": True,
            },
            operation_type="extractor_initialization",
        )

    async def extract_medical_entities(
        self,
        text: str,
        enrich: bool = True,
        filter_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Extract medical entities from text using SciSpacy service

        Args:
            text: Text content to analyze
            enrich: Whether to use enriched analysis with metadata
            filter_types: Optional list of entity types to filter for

        Returns:
            List of extracted medical entities with metadata
        """
        if not text or not text.strip():
            return []

        try:
            # Prepare request for SciSpacy service
            request_spec = HTTPRequestSpec(
                method="POST",
                url=f"{self.scispacy_url}/analyze",
                headers={"Content-Type": "application/json"},
                json_body={
                    "text": text,
                    "enrich": enrich,
                },
                timeout=30.0,
            )

            # Make request to SciSpacy service
            status_code, response_data = await http_request(
                request_spec,
                retries=3,
                mask_phi=True,  # Enable PHI masking for logs
            )

            if status_code != 200:
                self.logger.error(f"SciSpacy service returned status {status_code}")
                return []

            if not isinstance(response_data, dict):
                self.logger.error("Invalid response format from SciSpacy service")
                return []

            # Process entities from response
            entities = response_data.get("entities", [])

            # Filter by entity types if specified
            if filter_types:
                entities = [
                    entity for entity in entities
                    if entity.get("type") in filter_types
                ]

            # Add administrative context to entities
            processed_entities = []
            for entity in entities:
                processed_entity = self._process_entity(entity)
                processed_entities.append(processed_entity)

            log_healthcare_event(
                self.logger,
                logging.INFO,
                f"Medical entity extraction completed: {len(processed_entities)} entities",
                context={
                    "text_length": len(text),
                    "total_entities": len(entities),
                    "filtered_entities": len(processed_entities),
                    "high_priority_count": len([
                        e for e in processed_entities
                        if e.get("type") in self.high_priority_entities
                    ]),
                },
                operation_type="entity_extraction",
            )

            return processed_entities

        except Exception as e:
            self.logger.exception(f"Medical entity extraction failed: {e}")
            return []

    async def extract_entities_by_type(
        self,
        text: str,
        entity_types: list[str],
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Extract specific types of medical entities

        Args:
            text: Text content to analyze
            entity_types: List of entity types to extract

        Returns:
            Dictionary mapping entity types to lists of entities
        """
        if not text or not text.strip():
            return {}

        try:
            # Use the filtered extraction endpoint if available
            request_spec = HTTPRequestSpec(
                method="POST",
                url=f"{self.scispacy_url}/extract-by-type",
                headers={"Content-Type": "application/json"},
                json_body={
                    "text": text,
                    "types": entity_types,
                },
                timeout=30.0,
            )

            status_code, response_data = await http_request(
                request_spec,
                retries=3,
                mask_phi=True,
            )

            if status_code != 200:
                # Fallback to general extraction with filtering
                self.logger.warning(
                    f"Filtered extraction unavailable (status {status_code}), "
                    "falling back to general extraction",
                )
                entities = await self.extract_medical_entities(text, filter_types=entity_types)
                return self._group_entities_by_type(entities)

            if not isinstance(response_data, dict):
                self.logger.error("Invalid response format from filtered extraction")
                return {}

            # Process grouped entities
            entities = response_data.get("entities", [])
            processed_entities = [self._process_entity(entity) for entity in entities]

            return self._group_entities_by_type(processed_entities)

        except Exception as e:
            self.logger.exception(f"Filtered entity extraction failed: {e}")
            return {}

    async def get_clinical_summary(self, text: str) -> dict[str, Any]:
        """
        Get clinical summary of extracted entities

        Args:
            text: Text content to analyze

        Returns:
            Clinical summary with categorized entities
        """
        entities = await self.extract_medical_entities(text, enrich=True)

        if not entities:
            return {
                "has_medical_content": False,
                "entity_summary": {},
                "administrative_note": self.disclaimer,
            }

        # Categorize entities for administrative purposes
        return {
            "has_medical_content": True,
            "total_entities": len(entities),
            "entity_summary": self._categorize_entities(entities),
            "high_priority_entities": [
                entity for entity in entities
                if entity.get("type") in self.high_priority_entities
            ],
            "administrative_note": self.disclaimer,
        }


    def _process_entity(self, entity: dict[str, Any]) -> dict[str, Any]:
        """
        Process and enrich entity with administrative context

        Args:
            entity: Raw entity from SciSpacy

        Returns:
            Processed entity with additional metadata
        """
        processed = entity.copy()

        # Add administrative metadata
        processed["extracted_for"] = "administrative_processing"
        processed["requires_review"] = True
        processed["is_high_priority"] = entity.get("type") in self.high_priority_entities

        # Add usage hints for different entity types
        entity_type = entity.get("type", "")
        if entity_type in self.high_priority_entities:
            processed["administrative_usage"] = self._get_administrative_usage_hint(entity_type)

        return processed

    def _get_administrative_usage_hint(self, entity_type: str) -> str:
        """Get administrative usage hint for entity type"""
        usage_hints = {
            "SIMPLE_CHEMICAL": "Medication tracking, formulary management, drug interaction checks",
            "PATHOLOGICAL_FORMATION": "Condition tracking, care coordination, outcome monitoring",
            "ORGAN": "Anatomical reference, procedure categorization, specialist routing",
            "GENE_OR_GENE_PRODUCT": "Genetic counseling referrals, precision medicine coordination",
        }
        return usage_hints.get(entity_type, "General medical reference and documentation")

    def _group_entities_by_type(self, entities: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        """Group entities by their type"""
        grouped = {}
        for entity in entities:
            entity_type = entity.get("type", "UNKNOWN")
            if entity_type not in grouped:
                grouped[entity_type] = []
            grouped[entity_type].append(entity)
        return grouped

    def _categorize_entities(self, entities: list[dict[str, Any]]) -> dict[str, Any]:
        """Categorize entities for administrative summary"""
        categories = {
            "medications": [],
            "conditions": [],
            "anatomy": [],
            "genetics": [],
            "other": [],
        }

        type_to_category = {
            "SIMPLE_CHEMICAL": "medications",
            "PATHOLOGICAL_FORMATION": "conditions",
            "ORGAN": "anatomy",
            "ANATOMICAL_SYSTEM": "anatomy",
            "GENE_OR_GENE_PRODUCT": "genetics",
        }

        for entity in entities:
            entity_type = entity.get("type", "")
            category = type_to_category.get(entity_type, "other")
            categories[category].append(entity)

        # Return summary counts and samples
        return {
            category: {
                "count": len(items),
                "sample_entities": [item.get("text", "") for item in items[:3]],
            }
            for category, items in categories.items()
            if items  # Only include non-empty categories
        }

    async def health_check(self) -> dict[str, Any]:
        """Check if SciSpacy service is available"""
        try:
            request_spec = HTTPRequestSpec(
                method="GET",
                url=f"{self.scispacy_url}/health",
                timeout=5.0,
            )

            status_code, response_data = await http_request(
                request_spec,
                retries=1,
                mask_phi=False,
            )

            return {
                "available": status_code == 200,
                "status_code": status_code,
                "service_url": self.scispacy_url,
                "response": response_data,
            }

        except Exception as e:
            return {
                "available": False,
                "error": str(e),
                "service_url": self.scispacy_url,
            }
