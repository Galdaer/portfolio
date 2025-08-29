"""
Configuration loader for Medical Mirrors service
Loads and manages configuration from YAML files for AI enhancement and medical terminology
"""

import os
import logging
from typing import Any, Dict, Optional
import yaml

logger = logging.getLogger(__name__)


class MedicalMirrorsConfig:
    """Centralized configuration management for Medical Mirrors service"""
    
    _instance = None
    _config = None
    
    def __new__(cls):
        """Singleton pattern to ensure single config instance"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_all_configs()
        return cls._instance
    
    def _load_all_configs(self):
        """Load all configuration files"""
        config_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'config'
        )
        
        self._config = {
            'medical_terminology': self._load_yaml(os.path.join(config_dir, 'medical_terminology.yaml')),
            'ai_enhancement': self._load_yaml(os.path.join(config_dir, 'ai_enhancement_config.yaml'))
        }
        
        # Log loaded configuration
        logger.info(f"Loaded medical terminology config: {bool(self._config['medical_terminology'])}")
        logger.info(f"Loaded AI enhancement config: {bool(self._config['ai_enhancement'])}")
        
        # Set AI mode from config or environment
        self.ai_enabled = self._determine_ai_mode()
        logger.info(f"AI enhancement mode: {'ENABLED' if self.ai_enabled else 'DISABLED (using patterns)'}")
    
    def _load_yaml(self, filepath: str) -> Dict[str, Any]:
        """Load a YAML configuration file"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    return yaml.safe_load(f) or {}
            else:
                logger.warning(f"Config file not found: {filepath}")
                return {}
        except Exception as e:
            logger.error(f"Error loading config from {filepath}: {e}")
            return {}
    
    def _determine_ai_mode(self) -> bool:
        """Determine if AI enhancement should be used"""
        # Priority: Environment variable > Config file > Default (True)
        env_ai = os.getenv('USE_AI_ENHANCEMENT', '').lower()
        if env_ai:
            return env_ai == 'true'
        
        # Check config file
        ai_config = self._config.get('ai_enhancement', {})
        modes = ai_config.get('enhancement_modes', {})
        default_mode = modes.get('default_mode', 'ai')
        
        return default_mode == 'ai'
    
    def get_medical_abbreviations(self) -> Dict[str, str]:
        """Get medical abbreviations mapping"""
        terminology = self._config.get('medical_terminology', {})
        abbrevs = terminology.get('abbreviations', {})
        
        # Flatten all abbreviations into single dict
        result = {}
        for category in abbrevs.values():
            if isinstance(category, dict):
                result.update(category)
        
        return result
    
    def get_term_variations(self) -> Dict[str, List[str]]:
        """Get medical term variations"""
        terminology = self._config.get('medical_terminology', {})
        variations = terminology.get('term_variations', {})
        
        # Flatten all variations
        result = {}
        for category in variations.values():
            if isinstance(category, dict):
                result.update(category)
        
        return result
    
    def get_icd10_clinical_notes(self, code: str) -> Dict[str, List[str]]:
        """Get clinical notes for specific ICD-10 code"""
        terminology = self._config.get('medical_terminology', {})
        clinical_notes = terminology.get('icd10_clinical_notes', {})
        
        # Try exact match first
        if code in clinical_notes:
            return clinical_notes[code]
        
        # Try prefix match (e.g., E10 for E10.9)
        code_prefix = code.split('.')[0] if '.' in code else code[:3]
        if code_prefix in clinical_notes:
            return clinical_notes[code_prefix]
        
        return {'inclusion': [], 'exclusion': []}
    
    def get_billing_synonyms(self, code: str) -> List[str]:
        """Get synonyms for billing code"""
        terminology = self._config.get('medical_terminology', {})
        billing = terminology.get('billing_code_patterns', {})
        procedure_synonyms = billing.get('procedure_synonyms', {})
        
        return procedure_synonyms.get(code, [])
    
    def get_ai_config(self) -> Dict[str, Any]:
        """Get AI enhancement configuration"""
        return self._config.get('ai_enhancement', {})
    
    def get_scispacy_config(self) -> Dict[str, Any]:
        """Get SciSpacy service configuration"""
        ai_config = self.get_ai_config()
        return ai_config.get('scispacy', {
            'host': 'localhost',
            'port': 8080,
            'timeout': 30,
            'batch_size': 100
        })
    
    def get_ollama_config(self) -> Dict[str, Any]:
        """Get Ollama service configuration"""
        ai_config = self.get_ai_config()
        return ai_config.get('ollama', {
            'host': 'localhost',
            'port': 11434,
            'model': 'llama3.2:latest',
            'timeout': 60,
            'temperature': 0.3
        })
    
    def get_enhancement_priorities(self) -> Dict[str, Dict[str, Any]]:
        """Get enhancement priorities for different data types"""
        ai_config = self.get_ai_config()
        return ai_config.get('enhancement_priorities', {})
    
    def is_enhancement_enabled(self, data_type: str) -> bool:
        """Check if enhancement is enabled for a specific data type"""
        priorities = self.get_enhancement_priorities()
        data_config = priorities.get(data_type, {})
        return data_config.get('enabled', True)
    
    def get_batch_size(self, data_type: str) -> int:
        """Get batch size for specific data type"""
        priorities = self.get_enhancement_priorities()
        data_config = priorities.get(data_type, {})
        return data_config.get('batch_size', 100)
    
    def get_quality_thresholds(self) -> Dict[str, Any]:
        """Get quality thresholds for AI-generated content"""
        ai_config = self.get_ai_config()
        return ai_config.get('quality_thresholds', {})
    
    def should_fallback_to_pattern(self) -> bool:
        """Check if pattern-based fallback is enabled"""
        ai_config = self.get_ai_config()
        modes = ai_config.get('enhancement_modes', {})
        return modes.get('fallback_to_pattern', True)


# Global config instance
_config_instance = None

def get_config() -> MedicalMirrorsConfig:
    """Get the global configuration instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = MedicalMirrorsConfig()
    return _config_instance


def reload_config():
    """Force reload of configuration files"""
    global _config_instance
    _config_instance = None
    return get_config()