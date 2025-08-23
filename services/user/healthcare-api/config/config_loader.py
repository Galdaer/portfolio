"""
Configuration Loader for Healthcare API
Loads and validates configuration from YAML files with environment overrides
"""

import os
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import yaml
from dataclasses import dataclass, field

from core.infrastructure.healthcare_logger import get_healthcare_logger

logger = get_healthcare_logger("config_loader")


@dataclass
class VoiceProcessingConfig:
    """Voice processing configuration"""
    enabled: bool = True
    real_time_processing: bool = True
    confidence_threshold: float = 0.8
    max_session_duration_minutes: int = 30
    field_mappings: Dict[str, List[str]] = field(default_factory=dict)
    medical_keywords: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class DocumentRequirementsConfig:
    """Document requirements configuration"""
    base_documents: List[str] = field(default_factory=list)
    new_patient_additional: List[str] = field(default_factory=list)
    specialist_additional: List[str] = field(default_factory=list)
    insurance_verification: List[str] = field(default_factory=list)
    appointment_scheduling: List[str] = field(default_factory=list)
    general_intake: List[str] = field(default_factory=list)


@dataclass
class ValidationConfig:
    """Field validation configuration"""
    field_validation: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class IntakeAgentConfig:
    """Intake agent configuration"""
    disclaimers: List[str] = field(default_factory=list)
    voice_processing: VoiceProcessingConfig = field(default_factory=VoiceProcessingConfig)
    document_requirements: DocumentRequirementsConfig = field(default_factory=DocumentRequirementsConfig)
    required_fields: Dict[str, List[str]] = field(default_factory=dict)
    next_steps_templates: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class AgentSpecializationConfig:
    """Agent specialization configuration"""
    name: str = ""
    capabilities: List[str] = field(default_factory=list)
    timeout_seconds: int = 300


@dataclass
class WorkflowStepConfig:
    """Workflow step configuration"""
    step_name: str = ""
    agent_specialization: str = ""
    step_config: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    parallel_capable: bool = False
    timeout_seconds: int = 300
    description: str = ""


@dataclass
class WorkflowTypeConfig:
    """Workflow type configuration"""
    name: str = ""
    description: str = ""
    timeout_seconds: int = 1800
    retry_attempts: int = 2


@dataclass
class WorkflowConfig:
    """Workflow orchestration configuration"""
    types: Dict[str, WorkflowTypeConfig] = field(default_factory=dict)
    agent_specializations: Dict[str, AgentSpecializationConfig] = field(default_factory=dict)
    step_definitions: Dict[str, List[WorkflowStepConfig]] = field(default_factory=dict)
    result_templates: Dict[str, Dict[str, str]] = field(default_factory=dict)


@dataclass
class OrchestrationConfig:
    """Orchestration settings configuration"""
    max_concurrent_workflows: int = 50
    workflow_cleanup_delay_seconds: int = 300
    status_check_interval_seconds: int = 5
    max_workflow_duration_seconds: int = 3600
    error_handling: Dict[str, Any] = field(default_factory=dict)
    monitoring: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthcareAPIConfig:
    """Complete healthcare API configuration"""
    intake_agent: IntakeAgentConfig = field(default_factory=IntakeAgentConfig)
    workflows: WorkflowConfig = field(default_factory=WorkflowConfig)
    orchestration: OrchestrationConfig = field(default_factory=OrchestrationConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)


class ConfigLoader:
    """
    Configuration loader for healthcare API components
    
    Loads configuration from YAML files with environment variable overrides
    and provides type-safe access to configuration values.
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent
        self.config_cache: Dict[str, Any] = {}
        
        logger.info(f"Configuration loader initialized with config dir: {self.config_dir}")
    
    def load_config(self) -> HealthcareAPIConfig:
        """Load complete healthcare API configuration"""
        
        try:
            # Load intake configuration
            intake_config = self._load_yaml_file("intake_config.yml")
            
            # Load workflow configuration
            workflow_config = self._load_yaml_file("workflow_config.yml")
            
            # Create configuration objects
            config = HealthcareAPIConfig()
            
            # Parse intake agent configuration
            if "intake_agent" in intake_config:
                config.intake_agent = self._parse_intake_config(intake_config["intake_agent"])
            
            # Parse validation configuration
            if "validation" in intake_config:
                config.validation = self._parse_validation_config(intake_config["validation"])
            
            # Parse workflow configuration
            if "workflows" in workflow_config:
                config.workflows = self._parse_workflow_config(workflow_config["workflows"])
            
            # Parse orchestration configuration
            if "orchestration" in workflow_config:
                config.orchestration = self._parse_orchestration_config(workflow_config["orchestration"])
            
            # Apply environment overrides
            self._apply_environment_overrides(config)
            
            logger.info("Healthcare API configuration loaded successfully")
            return config
            
        except Exception as e:
            logger.error(f"Failed to load healthcare API configuration: {str(e)}")
            raise
    
    def _load_yaml_file(self, filename: str) -> Dict[str, Any]:
        """Load and cache YAML configuration file"""
        
        if filename in self.config_cache:
            return self.config_cache[filename]
        
        file_path = self.config_dir / filename
        
        if not file_path.exists():
            logger.warning(f"Configuration file not found: {file_path}")
            return {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f) or {}
            
            self.config_cache[filename] = config_data
            logger.debug(f"Loaded configuration from: {file_path}")
            return config_data
            
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML file {file_path}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to load configuration file {file_path}: {str(e)}")
            raise
    
    def _parse_intake_config(self, intake_data: Dict[str, Any]) -> IntakeAgentConfig:
        """Parse intake agent configuration"""
        
        config = IntakeAgentConfig()
        
        # Parse disclaimers
        config.disclaimers = intake_data.get("disclaimers", [])
        
        # Parse voice processing configuration
        if "voice_processing" in intake_data:
            vp_data = intake_data["voice_processing"]
            config.voice_processing = VoiceProcessingConfig(
                enabled=vp_data.get("enabled", True),
                real_time_processing=vp_data.get("real_time_processing", True),
                confidence_threshold=vp_data.get("confidence_threshold", 0.8),
                max_session_duration_minutes=vp_data.get("max_session_duration_minutes", 30),
                field_mappings=vp_data.get("field_mappings", {}),
                medical_keywords=vp_data.get("medical_keywords", {})
            )
        
        # Parse document requirements
        if "document_requirements" in intake_data:
            dr_data = intake_data["document_requirements"]
            config.document_requirements = DocumentRequirementsConfig(
                base_documents=dr_data.get("base_documents", []),
                new_patient_additional=dr_data.get("new_patient_additional", []),
                specialist_additional=dr_data.get("specialist_additional", []),
                insurance_verification=dr_data.get("insurance_verification", []),
                appointment_scheduling=dr_data.get("appointment_scheduling", []),
                general_intake=dr_data.get("general_intake", [])
            )
        
        # Parse required fields and next steps templates
        config.required_fields = intake_data.get("required_fields", {})
        config.next_steps_templates = intake_data.get("next_steps_templates", {})
        
        return config
    
    def _parse_workflow_config(self, workflow_data: Dict[str, Any]) -> WorkflowConfig:
        """Parse workflow configuration"""
        
        config = WorkflowConfig()
        
        # Parse workflow types
        if "types" in workflow_data:
            for type_name, type_data in workflow_data["types"].items():
                config.types[type_name] = WorkflowTypeConfig(
                    name=type_data.get("name", ""),
                    description=type_data.get("description", ""),
                    timeout_seconds=type_data.get("timeout_seconds", 1800),
                    retry_attempts=type_data.get("retry_attempts", 2)
                )
        
        # Parse agent specializations
        if "agent_specializations" in workflow_data:
            for spec_name, spec_data in workflow_data["agent_specializations"].items():
                config.agent_specializations[spec_name] = AgentSpecializationConfig(
                    name=spec_data.get("name", ""),
                    capabilities=spec_data.get("capabilities", []),
                    timeout_seconds=spec_data.get("timeout_seconds", 300)
                )
        
        # Parse step definitions
        if "step_definitions" in workflow_data:
            for workflow_name, steps_data in workflow_data["step_definitions"].items():
                config.step_definitions[workflow_name] = []
                for step_data in steps_data:
                    config.step_definitions[workflow_name].append(
                        WorkflowStepConfig(
                            step_name=step_data.get("step_name", ""),
                            agent_specialization=step_data.get("agent_specialization", ""),
                            step_config=step_data.get("step_config", {}),
                            dependencies=step_data.get("dependencies", []),
                            parallel_capable=step_data.get("parallel_capable", False),
                            timeout_seconds=step_data.get("timeout_seconds", 300),
                            description=step_data.get("description", "")
                        )
                    )
        
        # Parse result templates
        config.result_templates = workflow_data.get("result_templates", {})
        
        return config
    
    def _parse_orchestration_config(self, orchestration_data: Dict[str, Any]) -> OrchestrationConfig:
        """Parse orchestration configuration"""
        
        return OrchestrationConfig(
            max_concurrent_workflows=orchestration_data.get("max_concurrent_workflows", 50),
            workflow_cleanup_delay_seconds=orchestration_data.get("workflow_cleanup_delay_seconds", 300),
            status_check_interval_seconds=orchestration_data.get("status_check_interval_seconds", 5),
            max_workflow_duration_seconds=orchestration_data.get("max_workflow_duration_seconds", 3600),
            error_handling=orchestration_data.get("error_handling", {}),
            monitoring=orchestration_data.get("monitoring", {})
        )
    
    def _parse_validation_config(self, validation_data: Dict[str, Any]) -> ValidationConfig:
        """Parse validation configuration"""
        
        return ValidationConfig(
            field_validation=validation_data.get("field_validation", {})
        )
    
    def _apply_environment_overrides(self, config: HealthcareAPIConfig):
        """Apply environment variable overrides to configuration"""
        
        # Voice processing overrides
        if os.getenv("VOICE_PROCESSING_ENABLED"):
            config.intake_agent.voice_processing.enabled = os.getenv("VOICE_PROCESSING_ENABLED", "true").lower() == "true"
        
        if os.getenv("VOICE_CONFIDENCE_THRESHOLD"):
            try:
                config.intake_agent.voice_processing.confidence_threshold = float(os.getenv("VOICE_CONFIDENCE_THRESHOLD"))
            except ValueError:
                logger.warning("Invalid VOICE_CONFIDENCE_THRESHOLD environment variable")
        
        # Workflow orchestration overrides
        if os.getenv("MAX_CONCURRENT_WORKFLOWS"):
            try:
                config.orchestration.max_concurrent_workflows = int(os.getenv("MAX_CONCURRENT_WORKFLOWS"))
            except ValueError:
                logger.warning("Invalid MAX_CONCURRENT_WORKFLOWS environment variable")
        
        if os.getenv("MAX_WORKFLOW_DURATION"):
            try:
                config.orchestration.max_workflow_duration_seconds = int(os.getenv("MAX_WORKFLOW_DURATION"))
            except ValueError:
                logger.warning("Invalid MAX_WORKFLOW_DURATION environment variable")
        
        logger.debug("Applied environment variable overrides to configuration")


# Singleton configuration loader
_config_loader: Optional[ConfigLoader] = None
_cached_config: Optional[HealthcareAPIConfig] = None


def get_config_loader(config_dir: Optional[str] = None) -> ConfigLoader:
    """Get singleton configuration loader"""
    global _config_loader
    
    if _config_loader is None:
        _config_loader = ConfigLoader(config_dir)
    
    return _config_loader


def get_healthcare_config(reload: bool = False) -> HealthcareAPIConfig:
    """Get healthcare API configuration with caching"""
    global _cached_config
    
    if _cached_config is None or reload:
        loader = get_config_loader()
        _cached_config = loader.load_config()
    
    return _cached_config


def reload_config() -> HealthcareAPIConfig:
    """Reload configuration from files"""
    return get_healthcare_config(reload=True)