"""
Configuration Loader for Open WebUI Medical Context
Loads and validates configuration for healthcare-aware conversation continuity
"""

import logging
import os
from pathlib import Path
from typing import Any

import yaml

from .environment_detector import get_current_environment

logger = logging.getLogger(__name__)


class OpenWebUIMedicalConfig:
    """Configuration manager for Open WebUI medical context features"""

    def __init__(self, config_dir: Path | None = None):
        """
        Initialize configuration loader

        Args:
            config_dir: Path to configuration directory
        """
        self.config_dir = config_dir or Path(__file__).parent
        self.environment = get_current_environment()
        self._config_cache: dict[str, Any] = {}
        self._medical_terminology: dict[str, Any] | None = None
        self._phi_config: dict[str, Any] | None = None
        self._main_config: dict[str, Any] | None = None

    def load_medical_context_config(self) -> dict[str, Any]:
        """Load main Open WebUI medical context configuration"""
        if self._main_config is not None:
            return self._main_config

        config_file = self.config_dir / "open_webui_medical_context.yaml"

        try:
            with open(config_file) as f:
                config = yaml.safe_load(f)

            # Apply environment-specific overrides
            if config and "environments" in config:
                env_overrides = config["environments"].get(self.environment, {})
                config = self._apply_environment_overrides(config, env_overrides)

            # Apply validation
            config = self._validate_main_config(config or {})

            self._main_config = config
            logger.info(f"Loaded Open WebUI medical context config for {self.environment}")
            return config

        except FileNotFoundError:
            logger.warning(f"Open WebUI medical context config not found at {config_file}")
            return self._get_default_config()
        except Exception as e:
            logger.exception(f"Error loading Open WebUI medical context config: {e}")
            return self._get_default_config()

    def load_medical_terminology(self) -> dict[str, Any]:
        """Load medical terminology configuration"""
        if self._medical_terminology is not None:
            return self._medical_terminology

        config_file = self.config_dir / "medical_terminology.yaml"

        try:
            with open(config_file) as f:
                terminology = yaml.safe_load(f)

            # Validate and process terminology
            terminology = self._validate_terminology_config(terminology or {})

            self._medical_terminology = terminology
            logger.info("Loaded medical terminology configuration")
            return terminology

        except FileNotFoundError:
            logger.warning(f"Medical terminology config not found at {config_file}")
            return self._get_default_terminology()
        except Exception as e:
            logger.exception(f"Error loading medical terminology config: {e}")
            return self._get_default_terminology()

    def load_phi_detection_config(self) -> dict[str, Any]:
        """Load PHI detection configuration"""
        if self._phi_config is not None:
            return self._phi_config

        config_file = self.config_dir / "phi_detection_config.yaml"

        try:
            with open(config_file) as f:
                phi_config = yaml.safe_load(f)

            self._phi_config = phi_config or {}
            logger.info("Loaded PHI detection configuration")
            return self._phi_config

        except FileNotFoundError:
            logger.warning(f"PHI detection config not found at {config_file}")
            return {}
        except Exception as e:
            logger.exception(f"Error loading PHI detection config: {e}")
            return {}

    def load_healthcare_settings(self) -> dict[str, Any]:
        """Load healthcare settings with Open WebUI integration"""
        config_file = self.config_dir / "healthcare_settings.yml"

        try:
            with open(config_file) as f:
                settings = yaml.safe_load(f)

            # Extract Open WebUI integration settings
            integration_settings = settings.get("open_webui_integration", {})

            logger.info("Loaded healthcare settings with Open WebUI integration")
            return integration_settings

        except FileNotFoundError:
            logger.warning(f"Healthcare settings not found at {config_file}")
            return {}
        except Exception as e:
            logger.exception(f"Error loading healthcare settings: {e}")
            return {}

    def get_topic_extraction_config(self) -> dict[str, Any]:
        """Get topic extraction configuration"""
        main_config = self.load_medical_context_config()
        terminology = self.load_medical_terminology()

        return {
            **main_config.get("topic_extraction", {}),
            "terminology": terminology,
            "extraction_rules": terminology.get("extraction_rules", {}),
        }

    def get_phi_detection_config(self) -> dict[str, Any]:
        """Get PHI detection configuration for conversations"""
        phi_config = self.load_phi_detection_config()
        main_config = self.load_medical_context_config()

        # Merge conversation-specific PHI settings
        conversation_phi = phi_config.get("conversation_memory", {})
        user_preferences = main_config.get("user_preferences", {})

        return {
            **phi_config,
            "conversation_memory": conversation_phi,
            "default_privacy_level": user_preferences.get("defaults", {}).get("privacy_level", "standard"),
        }

    def get_database_config(self) -> dict[str, Any]:
        """Get database configuration for Open WebUI integration"""
        main_config = self.load_medical_context_config()
        healthcare_settings = self.load_healthcare_settings()

        db_config = main_config.get("database", {})
        integration_db = healthcare_settings.get("database", {})

        return {
            **db_config,
            **integration_db,
            "webui_db_path": os.getenv("OPEN_WEBUI_DB_PATH", db_config.get("default_webui_db_path", "app/backend/data/webui.db")),
        }

    def get_performance_config(self) -> dict[str, Any]:
        """Get performance configuration"""
        main_config = self.load_medical_context_config()
        healthcare_settings = self.load_healthcare_settings()

        perf_config = main_config.get("performance", {})
        integration_perf = healthcare_settings.get("performance", {})

        return {
            **perf_config,
            **integration_perf,
        }

    def get_user_preference_defaults(self) -> dict[str, Any]:
        """Get default user preferences"""
        main_config = self.load_medical_context_config()
        healthcare_settings = self.load_healthcare_settings()

        defaults = main_config.get("user_preferences", {}).get("defaults", {})
        privacy_defaults = healthcare_settings.get("privacy", {})

        return {
            **defaults,
            "default_privacy_level": privacy_defaults.get("default_privacy_level", "standard"),
            "phi_detection_mode": privacy_defaults.get("phi_detection_mode", "balanced_mode"),
        }

    def get_medical_keywords(self, category: str | None = None) -> dict[str, list[str]] | list[str]:
        """
        Get medical keywords for topic extraction

        Args:
            category: Specific category to get (conditions, medications, etc.)

        Returns:
            All keywords or keywords for specific category
        """
        terminology = self.load_medical_terminology()

        # Flatten nested categories into simple lists
        flattened_keywords = {}

        for main_category, subcategories in terminology.items():
            if main_category == "extraction_rules":
                continue

            if isinstance(subcategories, dict):
                # Handle nested categories (like conditions.endocrine, conditions.cardiovascular)
                all_items = []
                for _subcategory, items in subcategories.items():
                    if isinstance(items, list):
                        all_items.extend(items)
                flattened_keywords[main_category] = all_items
            elif isinstance(subcategories, list):
                # Handle simple lists
                flattened_keywords[main_category] = subcategories

        if category:
            return flattened_keywords.get(category, [])
        return flattened_keywords

    def get_phi_patterns(self) -> dict[str, list[str]]:
        """Get PHI detection patterns"""
        phi_config = self.load_phi_detection_config()
        patterns = phi_config.get("patterns", {})

        # Convert single patterns to lists
        normalized_patterns = {}
        for pattern_type, pattern_list in patterns.items():
            if isinstance(pattern_list, list):
                normalized_patterns[pattern_type] = pattern_list
            elif isinstance(pattern_list, str):
                normalized_patterns[pattern_type] = [pattern_list]

        return normalized_patterns

    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled"""
        main_config = self.load_medical_context_config()
        healthcare_settings = self.load_healthcare_settings()

        # Check main config first
        if feature_name in main_config.get("features", {}):
            return main_config["features"][feature_name]

        # Check healthcare settings
        if feature_name in healthcare_settings.get("features", {}):
            return healthcare_settings["features"][feature_name]

        # Default to disabled
        return False

    def _apply_environment_overrides(self, config: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
        """Apply environment-specific configuration overrides"""
        def deep_update(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
            """Recursively update nested dictionaries"""
            result = base.copy()
            for key, value in override.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_update(result[key], value)
                else:
                    result[key] = value
            return result

        return deep_update(config, overrides)

    def _validate_main_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """Validate main configuration"""
        # Ensure required sections exist
        required_sections = ["features", "database", "topic_extraction", "user_preferences"]
        for section in required_sections:
            if section not in config:
                config[section] = {}

        # Validate feature flags
        features = config.get("features", {})
        if not isinstance(features, dict):
            config["features"] = {}

        # Validate database settings
        db_config = config.get("database", {})
        if "retention" not in db_config:
            db_config["retention"] = {"default_days": 365}

        # Validate performance settings
        perf_config = config.get("performance", {})
        if "timeouts" not in perf_config:
            perf_config["timeouts"] = {}

        return config

    def _validate_terminology_config(self, terminology: dict[str, Any]) -> dict[str, Any]:
        """Validate medical terminology configuration"""
        required_categories = ["conditions", "medications", "treatments", "symptoms"]

        for category in required_categories:
            if category not in terminology:
                terminology[category] = {}

        # Ensure all categories have at least some basic terms
        if not terminology["conditions"]:
            terminology["conditions"] = {"general": ["diabetes", "hypertension", "heart disease"]}

        if not terminology["medications"]:
            terminology["medications"] = {"general": ["aspirin", "ibuprofen", "acetaminophen"]}

        return terminology

    def _get_default_config(self) -> dict[str, Any]:
        """Get default configuration when file is not available"""
        return {
            "features": {
                "enable_medical_context": True,
                "enable_topic_extraction": True,
                "enable_conversation_linking": True,
                "enable_phi_detection": True,
            },
            "database": {
                "default_webui_db_path": "app/backend/data/webui.db",
                "retention": {"default_days": 365},
            },
            "topic_extraction": {
                "confidence": {"minimum_topic_confidence": 0.5},
                "categories": {"enabled": ["condition", "medication", "treatment", "symptom"]},
            },
            "user_preferences": {
                "defaults": {
                    "enable_medical_context": True,
                    "privacy_level": "standard",
                    "context_retention_days": 365,
                },
            },
            "performance": {
                "timeouts": {"topic_extraction": 5, "phi_detection": 3},
            },
        }

    def _get_default_terminology(self) -> dict[str, Any]:
        """Get default medical terminology when file is not available"""
        return {
            "conditions": {
                "common": ["diabetes", "hypertension", "heart disease", "cancer", "depression", "anxiety"],
            },
            "medications": {
                "common": ["aspirin", "ibuprofen", "acetaminophen", "metformin", "lisinopril", "atorvastatin"],
            },
            "treatments": {
                "common": ["surgery", "physical therapy", "medication", "therapy", "treatment"],
            },
            "symptoms": {
                "common": ["pain", "nausea", "fatigue", "headache", "dizziness", "weakness"],
            },
        }

    def reload_config(self) -> None:
        """Reload all configuration from files"""
        self._config_cache.clear()
        self._medical_terminology = None
        self._phi_config = None
        self._main_config = None
        logger.info("Reloaded Open WebUI medical context configuration")

    def validate_configurations(self) -> dict[str, Any]:
        """
        Validate all configurations and return validation results

        Returns:
            Dict containing validation status and any errors found
        """
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "config_files_checked": [],
        }

        # Validate main medical context config
        try:
            main_config = self.load_medical_context_config()
            config_file = self.config_dir / "open_webui_medical_context.yaml"
            validation_results["config_files_checked"].append(str(config_file))

            errors = self._validate_main_config_structure(main_config)
            validation_results["errors"].extend(errors)

        except Exception as e:
            validation_results["errors"].append(f"Failed to load main config: {e}")
            validation_results["valid"] = False

        # Validate medical terminology config
        try:
            terminology = self.load_medical_terminology()
            config_file = self.config_dir / "medical_terminology.yaml"
            validation_results["config_files_checked"].append(str(config_file))

            errors = self._validate_terminology_structure(terminology)
            validation_results["errors"].extend(errors)

        except Exception as e:
            validation_results["errors"].append(f"Failed to load terminology config: {e}")
            validation_results["valid"] = False

        # Validate PHI detection config
        try:
            phi_config = self.load_phi_detection_config()
            config_file = self.config_dir / "phi_detection_config.yaml"
            validation_results["config_files_checked"].append(str(config_file))

            errors = self._validate_phi_config_structure(phi_config)
            validation_results["errors"].extend(errors)

        except Exception as e:
            validation_results["errors"].append(f"Failed to load PHI config: {e}")
            validation_results["valid"] = False

        # Validate healthcare settings
        try:
            healthcare_settings = self.load_healthcare_settings()
            config_file = self.config_dir / "healthcare_settings.yml"
            validation_results["config_files_checked"].append(str(config_file))

            errors = self._validate_healthcare_settings_structure(healthcare_settings)
            validation_results["errors"].extend(errors)

        except Exception as e:
            validation_results["warnings"].append(f"Healthcare settings not found or invalid: {e}")

        # Set overall validation status
        if validation_results["errors"]:
            validation_results["valid"] = False

        # Log validation results
        if validation_results["valid"]:
            logger.info("All medical context configurations validated successfully")
        else:
            logger.error(f"Configuration validation failed with {len(validation_results['errors'])} errors")
            for error in validation_results["errors"]:
                logger.error(f"Config validation error: {error}")

        if validation_results["warnings"]:
            for warning in validation_results["warnings"]:
                logger.warning(f"Config validation warning: {warning}")

        return validation_results

    def _validate_main_config_structure(self, config: dict[str, Any]) -> list[str]:
        """Validate main configuration structure"""
        errors = []

        # Required top-level sections
        required_sections = ["features", "database", "topic_extraction", "user_preferences"]
        for section in required_sections:
            if section not in config:
                errors.append(f"Missing required section '{section}' in main config")
                continue

            if not isinstance(config[section], dict):
                errors.append(f"Section '{section}' must be a dictionary")

        # Validate features section
        if "features" in config and isinstance(config["features"], dict):
            feature_flags = config["features"]
            expected_features = [
                "enable_medical_context",
                "enable_topic_extraction",
                "enable_conversation_linking",
                "enable_phi_detection",
            ]
            for feature in expected_features:
                if feature in feature_flags and not isinstance(feature_flags[feature], bool):
                    errors.append(f"Feature flag '{feature}' must be boolean")

        # Validate topic extraction config
        if "topic_extraction" in config and isinstance(config["topic_extraction"], dict):
            topic_config = config["topic_extraction"]
            if "confidence" in topic_config:
                confidence_config = topic_config["confidence"]
                if not isinstance(confidence_config, dict):
                    errors.append("topic_extraction.confidence must be a dictionary")
                elif "minimum_topic_confidence" in confidence_config:
                    min_conf = confidence_config["minimum_topic_confidence"]
                    if not isinstance(min_conf, int | float) or not 0 <= min_conf <= 1:
                        errors.append("minimum_topic_confidence must be a number between 0 and 1")

        return errors

    def _validate_terminology_structure(self, terminology: dict[str, Any]) -> list[str]:
        """Validate medical terminology structure"""
        errors = []

        # Required categories
        required_categories = ["conditions", "medications", "treatments", "symptoms"]
        for category in required_categories:
            if category not in terminology:
                errors.append(f"Missing required terminology category '{category}'")
                continue

            if not isinstance(terminology[category], dict):
                errors.append(f"Terminology category '{category}' must be a dictionary")
                continue

            # Check that categories contain lists of strings
            category_data = terminology[category]
            for subcategory, terms in category_data.items():
                if not isinstance(terms, list):
                    errors.append(f"Terminology '{category}.{subcategory}' must be a list")
                elif terms:  # If not empty, check first few items
                    for i, term in enumerate(terms[:3]):  # Check first 3 items
                        if not isinstance(term, str):
                            errors.append(f"Terminology term '{category}.{subcategory}[{i}]' must be a string")
                            break

        return errors

    def _validate_phi_config_structure(self, phi_config: dict[str, Any]) -> list[str]:
        """Validate PHI detection configuration structure"""
        errors = []

        # Validate patterns section
        if "patterns" in phi_config:
            patterns = phi_config["patterns"]
            if not isinstance(patterns, dict):
                errors.append("PHI patterns must be a dictionary")
            else:
                for pattern_type, pattern_list in patterns.items():
                    if not isinstance(pattern_list, list):
                        errors.append(f"PHI pattern '{pattern_type}' must be a list")
                    else:
                        # Test that patterns are valid regex
                        for i, pattern in enumerate(pattern_list[:2]):  # Check first 2 patterns
                            try:
                                import re
                                re.compile(pattern)
                            except re.error as e:
                                errors.append(f"Invalid regex in PHI pattern '{pattern_type}[{i}]': {e}")

        # Validate conversation memory settings
        if "conversation_memory" in phi_config:
            conv_memory = phi_config["conversation_memory"]
            if "phi_handling_modes" in conv_memory:
                modes = conv_memory["phi_handling_modes"]
                if not isinstance(modes, dict):
                    errors.append("conversation_memory.phi_handling_modes must be a dictionary")
                else:
                    for mode_name, mode_config in modes.items():
                        if not isinstance(mode_config, dict):
                            errors.append(f"PHI handling mode '{mode_name}' must be a dictionary")
                        else:
                            # Check threshold values
                            for threshold_key in ["redact_threshold", "flag_threshold"]:
                                if threshold_key in mode_config:
                                    threshold = mode_config[threshold_key]
                                    if not isinstance(threshold, int | float) or not 0 <= threshold <= 1:
                                        errors.append(f"Threshold '{mode_name}.{threshold_key}' must be a number between 0 and 1")

        return errors

    def _validate_healthcare_settings_structure(self, settings: dict[str, Any]) -> list[str]:
        """Validate healthcare settings structure"""
        errors = []

        # This is optional config, so just validate basic structure if present
        if settings:  # Only validate if settings exist
            if "features" in settings:
                features = settings["features"]
                if not isinstance(features, dict):
                    errors.append("Healthcare settings features must be a dictionary")

            if "privacy" in settings:
                privacy = settings["privacy"]
                if not isinstance(privacy, dict):
                    errors.append("Healthcare settings privacy must be a dictionary")
                elif "default_privacy_level" in privacy:
                    privacy_level = privacy["default_privacy_level"]
                    valid_levels = ["minimal", "standard", "enhanced"]
                    if privacy_level not in valid_levels:
                        errors.append(f"Invalid privacy level '{privacy_level}', must be one of {valid_levels}")

        return errors


# Global configuration instance
_medical_config_instance: OpenWebUIMedicalConfig | None = None


def get_medical_config() -> OpenWebUIMedicalConfig:
    """Get global medical configuration instance"""
    global _medical_config_instance
    if _medical_config_instance is None:
        _medical_config_instance = OpenWebUIMedicalConfig()
    return _medical_config_instance


# Convenience functions
def get_topic_extraction_config() -> dict[str, Any]:
    """Get topic extraction configuration"""
    return get_medical_config().get_topic_extraction_config()


def get_medical_keywords(category: str | None = None) -> dict[str, list[str]] | list[str]:
    """Get medical keywords for topic extraction"""
    return get_medical_config().get_medical_keywords(category)


def get_phi_detection_config() -> dict[str, Any]:
    """Get PHI detection configuration"""
    return get_medical_config().get_phi_detection_config()


def get_database_config() -> dict[str, Any]:
    """Get database configuration"""
    return get_medical_config().get_database_config()


def is_feature_enabled(feature_name: str) -> bool:
    """Check if a feature is enabled"""
    return get_medical_config().is_feature_enabled(feature_name)


def validate_medical_configurations() -> dict[str, Any]:
    """
    Validate all medical context configurations

    Returns:
        Dict containing validation results with errors and warnings

    Example:
        from config.open_webui_config_loader import validate_medical_configurations
        results = validate_medical_configurations()
        if not results["valid"]:
            for error in results["errors"]:
                print(f"Config error: {error}")
    """
    return get_medical_config().validate_configurations()
