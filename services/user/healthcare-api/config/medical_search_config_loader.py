"""
Medical Search Configuration Loader
Provides configurable parameters for medical literature search
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class SearchParameters:
    """Search parameter configuration"""
    max_results: dict[str, int]
    timeouts: dict[str, int]
    query_templates: dict[str, str]

@dataclass
class PublicationConfig:
    """Publication type preferences"""
    condition_info: list[str]
    symptom_literature: list[str]
    drug_information: list[str]
    clinical_references: list[str]

@dataclass
class MedicalSearchConfig:
    """Complete medical search configuration"""
    search_parameters: SearchParameters
    publication_types: PublicationConfig
    evidence_weights: dict[str, int]
    trusted_organizations: list[str]
    confidence_parameters: dict[str, Any]
    url_patterns: dict[str, str]

class MedicalSearchConfigLoader:
    """Loads medical search configuration from YAML with defaults"""

    def __init__(self, config_path: str = None):
        if config_path is None:
            # Default to config file in same directory as this module
            config_dir = Path(__file__).parent
            config_path = config_dir / "medical_search_config.yaml"

        self.config_path = Path(config_path)
        self._config = None

    def load_config(self) -> MedicalSearchConfig:
        """Load configuration from YAML file with fallback to defaults"""
        if self._config is not None:
            return self._config

        try:
            if self.config_path.exists():
                with open(self.config_path) as f:
                    config_data = yaml.safe_load(f)
            else:
                # Use defaults if config file doesn't exist
                config_data = self._get_default_config()

            # Parse configuration sections
            search_params = SearchParameters(
                max_results=config_data.get("search_parameters", {}).get("max_results", {}),
                timeouts=config_data.get("search_parameters", {}).get("timeouts", {}),
                query_templates=config_data.get("search_parameters", {}).get("query_templates", {}),
            )

            publication_types = PublicationConfig(
                condition_info=config_data.get("publication_types", {}).get("condition_info", []),
                symptom_literature=config_data.get("publication_types", {}).get("symptom_literature", []),
                drug_information=config_data.get("publication_types", {}).get("drug_information", []),
                clinical_references=config_data.get("publication_types", {}).get("clinical_references", []),
            )

            self._config = MedicalSearchConfig(
                search_parameters=search_params,
                publication_types=publication_types,
                evidence_weights=config_data.get("evidence_weights", {}),
                trusted_organizations=config_data.get("trusted_organizations", []),
                url_patterns=config_data.get("url_patterns", {}),
                confidence_parameters=config_data.get("confidence_parameters", {}),
            )

            return self._config

        except Exception:
            # Fallback to minimal defaults on any error
            return self._get_minimal_config()

    def _get_default_config(self) -> dict[str, Any]:
        """Default configuration if YAML file is missing"""
        return {
            "search_parameters": {
                "max_results": {
                    "condition_info": 10,
                    "symptom_literature": 15,
                    "drug_information": 8,
                    "clinical_references": 5,
                },
                "timeouts": {
                    "scispacy_request": 10,
                    "mcp_request": 30,
                    "search_request": 25,
                },
                "query_templates": {
                    "condition_info": "{concept} overview pathophysiology symptoms",
                    "symptom_literature": "{symptom} presentation differential clinical features",
                    "drug_information": "{drug_name} indications contraindications interactions",
                },
            },
            "publication_types": {
                "condition_info": ["review", "meta_analysis", "systematic_review"],
                "symptom_literature": ["clinical_study", "review"],
                "drug_information": ["clinical_trial", "regulatory_approval"],
                "clinical_references": ["clinical_guideline", "practice_guideline"],
            },
            "evidence_weights": {
                "systematic_review": 10,
                "meta_analysis": 9,
                "clinical_guideline": 8,
                "regulatory_approval": 7,
                "review": 3,
                "unknown": 1,
            },
            "trusted_organizations": ["AHA", "ACC", "ACP", "USPSTF"],
            "url_patterns": {
                "pubmed_article": "https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "fda_drug": "https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm",
            },
            "confidence_parameters": {
                "min_sources_for_high_confidence": 15,
                "min_high_quality_sources": 5,
            },
        }

    def _get_minimal_config(self) -> MedicalSearchConfig:
        """Minimal configuration for error recovery"""
        return MedicalSearchConfig(
            search_parameters=SearchParameters(
                max_results={"condition_info": 10, "symptom_literature": 15},
                timeouts={"scispacy_request": 10, "mcp_request": 30},
                query_templates={"condition_info": "{concept} overview"},
            ),
            publication_types=PublicationConfig(
                condition_info=["review"],
                symptom_literature=["clinical_study"],
                drug_information=["clinical_trial"],
                clinical_references=["clinical_guideline"],
            ),
            evidence_weights={"review": 3, "unknown": 1},
            trusted_organizations=["AHA"],
            url_patterns={"pubmed_article": "https://pubmed.ncbi.nlm.nih.gov/{pmid}/"},
            confidence_parameters={"min_sources_for_high_confidence": 10},
        )
