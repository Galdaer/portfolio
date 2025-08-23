"""
Transcription Configuration Loader
Loads and validates transcription service configuration from YAML files
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import yaml
from pydantic import BaseModel, Field, validator


@dataclass
class WebSocketConfig:
    """WebSocket connection configuration"""
    base_url: str
    health_check_url: str
    endpoint_path: str
    connection_timeout_seconds: int
    heartbeat_interval_seconds: int


@dataclass
class SessionConfig:
    """Session management configuration"""
    default_timeout_seconds: int
    cleanup_interval_seconds: int
    max_concurrent_sessions: int
    session_id_prefix: str
    audio_chunk_interval_seconds: int


@dataclass
class AudioConfig:
    """Audio processing configuration"""
    supported_formats: List[str]
    max_chunk_size_bytes: int
    max_session_duration_seconds: int
    quality_threshold: float
    noise_reduction_enabled: bool


@dataclass
class QualityConfig:
    """Transcription quality and confidence configuration"""
    default_confidence_threshold: float
    high_confidence_threshold: float
    min_confidence_for_medical_terms: float
    max_confidence_cap: float
    confidence_boost_per_char: float


@dataclass
class MedicalTerminologyConfig:
    """Medical terminology processing configuration"""
    confidence_boost_factor: float
    specialized_terms_weight: float
    abbreviation_expansion_enabled: bool
    terminology_validation_enabled: bool


@dataclass
class RealtimeConfig:
    """Real-time processing configuration"""
    processing_interval_ms: int
    batch_size: int
    enable_live_corrections: bool
    streaming_enabled: bool


@dataclass
class IntegrationConfig:
    """Integration settings configuration"""
    soap_generation_enabled: bool
    auto_save_transcriptions: bool
    mcp_integration_enabled: bool
    phi_detection_enabled: bool


@dataclass
class DevelopmentConfig:
    """Development and testing configuration"""
    mock_transcription_enabled: bool
    debug_audio_logging: bool
    save_audio_chunks: bool
    test_mode: bool


@dataclass
class ErrorHandlingConfig:
    """Error handling and retries configuration"""
    max_retries: int
    retry_delay_seconds: int
    connection_retry_backoff_factor: float
    failed_chunk_retry_limit: int


@dataclass
class PerformanceConfig:
    """Performance tuning configuration"""
    concurrent_processing_limit: int
    memory_usage_limit_mb: int
    cpu_usage_limit_percent: int
    enable_performance_monitoring: bool


class TranscriptionConfig(BaseModel):
    """Complete transcription service configuration"""
    
    websocket: WebSocketConfig
    session: SessionConfig
    audio: AudioConfig
    quality: QualityConfig
    medical_terminology: MedicalTerminologyConfig
    realtime: RealtimeConfig
    integration: IntegrationConfig
    development: DevelopmentConfig
    error_handling: ErrorHandlingConfig
    performance: PerformanceConfig

    @validator('quality')
    def validate_quality_thresholds(cls, v):
        """Validate confidence thresholds are within valid ranges"""
        if not 0.0 <= v.default_confidence_threshold <= 1.0:
            raise ValueError("default_confidence_threshold must be between 0.0 and 1.0")
        if not 0.0 <= v.high_confidence_threshold <= 1.0:
            raise ValueError("high_confidence_threshold must be between 0.0 and 1.0")
        if v.default_confidence_threshold > v.high_confidence_threshold:
            raise ValueError("default_confidence_threshold cannot be higher than high_confidence_threshold")
        return v

    @validator('performance')
    def validate_performance_limits(cls, v):
        """Validate performance limits are reasonable"""
        if v.memory_usage_limit_mb < 64:
            raise ValueError("memory_usage_limit_mb must be at least 64MB")
        if not 1 <= v.cpu_usage_limit_percent <= 100:
            raise ValueError("cpu_usage_limit_percent must be between 1 and 100")
        return v


def load_transcription_config(config_path: str | Path | None = None) -> TranscriptionConfig:
    """Load transcription configuration from YAML file"""
    
    if config_path is None:
        config_path = Path(__file__).parent / "transcription_config.yml"
    
    config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Transcription config file not found: {config_path}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        if not isinstance(config_data, dict):
            raise ValueError("Config file must contain a YAML dictionary")
            
        # Create configuration objects
        return TranscriptionConfig(
            websocket=WebSocketConfig(**config_data.get("websocket", {})),
            session=SessionConfig(**config_data.get("session", {})),
            audio=AudioConfig(**config_data.get("audio", {})),
            quality=QualityConfig(**config_data.get("quality", {})),
            medical_terminology=MedicalTerminologyConfig(**config_data.get("medical_terminology", {})),
            realtime=RealtimeConfig(**config_data.get("realtime", {})),
            integration=IntegrationConfig(**config_data.get("integration", {})),
            development=DevelopmentConfig(**config_data.get("development", {})),
            error_handling=ErrorHandlingConfig(**config_data.get("error_handling", {})),
            performance=PerformanceConfig(**config_data.get("performance", {}))
        )
        
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in transcription config: {e}")
    except TypeError as e:
        raise ValueError(f"Invalid transcription configuration structure: {e}")


def update_transcription_config_yaml(config_updates: dict[str, Any], config_path: str | Path | None = None) -> bool:
    """Update transcription configuration YAML file with new values"""
    
    if config_path is None:
        config_path = Path(__file__).parent / "transcription_config.yml"
    
    config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Transcription config file not found: {config_path}")
    
    try:
        # Load current configuration
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        if not isinstance(config_data, dict):
            raise ValueError("Config file must contain a YAML dictionary")
        
        # Create backup
        backup_path = config_path.with_suffix('.yml.backup')
        with open(backup_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(config_data, f, default_flow_style=False, sort_keys=False)
        
        # Apply updates - deep merge
        def deep_update(base_dict, update_dict):
            for key, value in update_dict.items():
                if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                    deep_update(base_dict[key], value)
                else:
                    base_dict[key] = value
        
        deep_update(config_data, config_updates)
        
        # Write updated configuration
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(config_data, f, default_flow_style=False, sort_keys=False)
        
        return True
        
    except Exception as e:
        raise ValueError(f"Failed to update transcription configuration: {e}")


def reload_transcription_config() -> TranscriptionConfig:
    """Reload transcription configuration from file"""
    global TRANSCRIPTION_CONFIG
    TRANSCRIPTION_CONFIG = load_transcription_config()
    return TRANSCRIPTION_CONFIG


def create_default_transcription_config() -> dict[str, Any]:
    """Create default transcription configuration for fallback"""
    
    return {
        "websocket": {
            "base_url": "ws://localhost:8000",
            "health_check_url": "http://localhost:8000",
            "endpoint_path": "/ws/transcription",
            "connection_timeout_seconds": 30,
            "heartbeat_interval_seconds": 30
        },
        "session": {
            "default_timeout_seconds": 300,
            "cleanup_interval_seconds": 60,
            "max_concurrent_sessions": 50,
            "session_id_prefix": "session_",
            "audio_chunk_interval_seconds": 2
        },
        "audio": {
            "supported_formats": ["webm", "wav", "mp3", "m4a"],
            "max_chunk_size_bytes": 1048576,
            "max_session_duration_seconds": 1800,
            "quality_threshold": 0.7,
            "noise_reduction_enabled": True
        },
        "quality": {
            "default_confidence_threshold": 0.85,
            "high_confidence_threshold": 0.92,
            "min_confidence_for_medical_terms": 0.88,
            "max_confidence_cap": 0.98,
            "confidence_boost_per_char": 0.001
        },
        "medical_terminology": {
            "confidence_boost_factor": 1.15,
            "specialized_terms_weight": 1.2,
            "abbreviation_expansion_enabled": True,
            "terminology_validation_enabled": True
        },
        "realtime": {
            "processing_interval_ms": 100,
            "batch_size": 5,
            "enable_live_corrections": True,
            "streaming_enabled": True
        },
        "integration": {
            "soap_generation_enabled": True,
            "auto_save_transcriptions": True,
            "mcp_integration_enabled": True,
            "phi_detection_enabled": True
        },
        "development": {
            "mock_transcription_enabled": False,
            "debug_audio_logging": False,
            "save_audio_chunks": False,
            "test_mode": False
        },
        "error_handling": {
            "max_retries": 3,
            "retry_delay_seconds": 1,
            "connection_retry_backoff_factor": 2.0,
            "failed_chunk_retry_limit": 2
        },
        "performance": {
            "concurrent_processing_limit": 10,
            "memory_usage_limit_mb": 512,
            "cpu_usage_limit_percent": 80,
            "enable_performance_monitoring": True
        }
    }


# Global configuration instance
try:
    TRANSCRIPTION_CONFIG = load_transcription_config()
except (FileNotFoundError, ValueError) as e:
    print(f"Warning: Could not load transcription config ({e}), using defaults")
    default_config = create_default_transcription_config()
    # Create TranscriptionConfig from default dict
    TRANSCRIPTION_CONFIG = TranscriptionConfig(
        websocket=WebSocketConfig(**default_config["websocket"]),
        session=SessionConfig(**default_config["session"]),
        audio=AudioConfig(**default_config["audio"]),
        quality=QualityConfig(**default_config["quality"]),
        medical_terminology=MedicalTerminologyConfig(**default_config["medical_terminology"]),
        realtime=RealtimeConfig(**default_config["realtime"]),
        integration=IntegrationConfig(**default_config["integration"]),
        development=DevelopmentConfig(**default_config["development"]),
        error_handling=ErrorHandlingConfig(**default_config["error_handling"]),
        performance=PerformanceConfig(**default_config["performance"])
    )