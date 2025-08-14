"""
PHI Detection Configuration Loader

Loads and manages PHI detection patterns and settings from YAML configuration.
Allows users to customize PHI detection behavior for different healthcare environments.
"""

import re
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml

from core.infrastructure.healthcare_logger import get_healthcare_logger

logger = get_healthcare_logger("phi_config")


class PHIDetectionConfigLoader:
    """Load and manage PHI detection configuration from YAML files."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize PHI detection config loader.
        
        Args:
            config_path: Path to PHI detection config file. If None, uses default.
        """
        if config_path is None:
            config_path = Path(__file__).parent / "phi_detection_config.yaml"
        
        self.config_path = Path(config_path)
        self._config: Optional[Dict[str, Any]] = None
        self._compiled_patterns: Optional[Dict[str, List[re.Pattern]]] = None
    
    def load_config(self) -> Dict[str, Any]:
        """Load PHI detection configuration from YAML file."""
        if self._config is not None:
            return self._config
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
            
            logger.info(f"PHI detection config loaded from {self.config_path}")
            return self._config
            
        except FileNotFoundError:
            logger.error(f"PHI detection config file not found: {self.config_path}")
            # Return sensible defaults
            return self._get_default_config()
        
        except yaml.YAMLError as e:
            logger.error(f"Error parsing PHI detection config: {e}")
            return self._get_default_config()
    
    def get_compiled_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Get compiled regex patterns for efficient matching."""
        if self._compiled_patterns is not None:
            return self._compiled_patterns
        
        config = self.load_config()
        patterns = config.get("patterns", {})
        
        self._compiled_patterns = {}
        for phi_type, pattern_list in patterns.items():
            self._compiled_patterns[phi_type] = [
                re.compile(pattern, re.IGNORECASE)
                for pattern in pattern_list
            ]
        
        logger.info(f"Compiled {len(self._compiled_patterns)} PHI pattern types")
        return self._compiled_patterns
    
    def get_exemption_contexts(self) -> List[str]:
        """Get all context exemption patterns."""
        config = self.load_config()
        exemptions = config.get("exemptions", {})
        
        all_exemptions = []
        for category, contexts in exemptions.items():
            all_exemptions.extend(contexts)
        
        return all_exemptions
    
    def get_synthetic_patterns(self) -> List[re.Pattern]:
        """Get compiled synthetic data patterns."""
        config = self.load_config()
        patterns = config.get("synthetic_patterns", [])
        
        return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    
    def get_phi_field_names(self) -> set[str]:
        """Get PHI field names as a set for quick lookup."""
        config = self.load_config()
        field_names = config.get("phi_field_names", [])
        
        return {name.lower() for name in field_names}
    
    def get_risk_settings(self) -> Dict[str, Any]:
        """Get risk calculation settings."""
        config = self.load_config()
        return config.get("risk_settings", {
            "enable_synthetic_detection": True,
            "default_risk_level": "medium",
            "critical_threshold": 3
        })
    
    def get_risk_mappings(self) -> Dict[str, List[str]]:
        """Get risk level mappings for PHI types."""
        config = self.load_config()
        return config.get("risk_mappings", {
            "high_risk_types": ["ssn", "medical_record_number", "insurance_id"],
            "medium_risk_types": ["phone", "email", "date_of_birth"],
            "low_risk_types": ["patient_id"]
        })
    
    def get_recommendations(self) -> Dict[str, List[str]]:
        """Get customizable recommendations by risk level."""
        config = self.load_config()
        return config.get("recommendations", {
            "critical": ["IMMEDIATE ACTION REQUIRED: Critical PHI detected"],
            "high": ["HIGH PRIORITY: Multiple PHI types detected"],
            "medium": ["MEDIUM PRIORITY: PHI detected"],
            "low": ["LOW PRIORITY: Minimal PHI detected"]
        })
    
    def is_exempted_context(self, context: str) -> bool:
        """Check if a context should be exempted from PHI detection."""
        if not context:
            return False
        
        exemption_contexts = self.get_exemption_contexts()
        context_lower = context.lower()
        
        return any(exemption in context_lower for exemption in exemption_contexts)
    
    def reload_config(self) -> None:
        """Reload configuration from file (useful for runtime updates)."""
        self._config = None
        self._compiled_patterns = None
        logger.info("PHI detection config reloaded")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration if file loading fails."""
        return {
            "risk_settings": {
                "enable_synthetic_detection": True,
                "default_risk_level": "medium",
                "critical_threshold": 3
            },
            "exemptions": {
                "medical_literature": [
                    "medical_literature", "pubmed", "external_search",
                    "academic_paper", "journal_article", "literature_search"
                ]
            },
            "patterns": {
                "ssn": ["\\b\\d{3}-\\d{2}-\\d{4}\\b"],
                "phone": ["\\b\\d{3}-\\d{3}-\\d{4}\\b"],
                "email": ["\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b"]
            },
            "synthetic_patterns": [
                "\\bPAT\\d{3}\\b", "\\bTEST[-_]?PATIENT\\b"
            ],
            "phi_field_names": [
                "ssn", "phone", "email", "patient_id", "mrn"
            ],
            "risk_mappings": {
                "high_risk_types": ["ssn", "medical_record_number"],
                "medium_risk_types": ["phone", "email"],
                "low_risk_types": ["patient_id"]
            },
            "recommendations": {
                "critical": ["IMMEDIATE ACTION REQUIRED"],
                "high": ["HIGH PRIORITY"],
                "medium": ["MEDIUM PRIORITY"],
                "low": ["LOW PRIORITY"]
            }
        }


# Global config loader instance
phi_config = PHIDetectionConfigLoader()
