"""
Chunked Transcription Configuration Loader
Loads and validates configuration for secure, chunked medical transcription
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import yaml

from config.environment_detector import EnvironmentDetector


@dataclass
class ChunkProcessingConfig:
    """Configuration for audio chunk processing"""
    duration_seconds: int = 5
    overlap_seconds: float = 1.0
    min_duration_seconds: int = 2
    max_duration_seconds: int = 30
    min_overlap_seconds: float = 0.5
    max_overlap_seconds: float = 5.0
    sample_rate: int = 16000
    bit_depth: int = 16
    channels: int = 1
    audio_format: str = "webm"
    codec: str = "opus"
    bitrate: int = 128000
    overlap_samples_multiplier: int = 2
    crossfade_enabled: bool = True
    crossfade_duration_ms: int = 50
    audio_artifact_prevention: bool = True
    context_words_to_preserve: int = 10
    transcription_tail_overlap: bool = True
    medical_context_carryover: bool = True


@dataclass
class EncryptionConfig:
    """Configuration for end-to-end encryption"""
    enabled: bool = True
    algorithm: str = "AES-256-GCM"
    key_size_bits: int = 256
    nonce_size_bits: int = 96
    session_key_rotation_interval_seconds: int = 3600
    key_derivation_iterations: int = 100000
    session_key_length: int = 32
    session_token_length: int = 32
    min_token_length: int = 16
    max_token_length: int = 64
    token_entropy_bits: int = 256
    asymmetric_key_exchange: bool = True
    rsa_key_size: int = 2048
    ecdh_curve: str = "P-256"


@dataclass
class WebSocketConfig:
    """Configuration for WebSocket connections"""
    base_path: str = "/ws/transcription"
    doctor_prefix: str = "doctor_"
    patient_prefix: str = "patient_"
    timeout_seconds: int = 30
    heartbeat_interval_seconds: int = 30
    max_message_size_bytes: int = 10485760  # 10MB
    compression_enabled: bool = True
    secure_protocol: str = "wss"
    insecure_protocol: str = "ws"
    default_port: int = 8000
    ssl_verify: bool = True
    message_types: List[str] = field(default_factory=lambda: [
        "initialize_session", "audio_chunk", "medical_insights",
        "end_session", "error", "heartbeat"
    ])


@dataclass
class MedicalEntityConfig:
    """Configuration for medical entity extraction"""
    enabled: bool = True
    confidence_threshold: float = 0.85
    entity_types: List[str] = field(default_factory=lambda: [
        "medications", "vital_signs", "symptoms", "diagnoses",
        "procedures", "allergies", "family_history"
    ])
    medical_term_confidence_boost: float = 0.15
    specialized_term_weight: float = 1.2
    terminology_validation: bool = True


@dataclass
class ProgressiveInsightsConfig:
    """Configuration for progressive medical insights"""
    enabled: bool = True
    medical_entity_extraction: MedicalEntityConfig = field(default_factory=MedicalEntityConfig)
    clinical_alerts_enabled: bool = True
    alert_types: List[str] = field(default_factory=lambda: [
        "drug_interactions", "abnormal_vitals", "critical_symptoms",
        "allergy_alerts", "contraindications"
    ])
    critical_alert_threshold: float = 0.9
    warning_alert_threshold: float = 0.75
    info_alert_threshold: float = 0.6
    batch_insights: bool = False
    real_time_updates: bool = True
    context_window_chunks: int = 5
    insight_confidence_threshold: float = 0.7


@dataclass
class SOAPSectionConfig:
    """Configuration for SOAP note sections"""
    enabled: bool = True
    weight: float = 1.0
    keywords: List[str] = field(default_factory=list)


@dataclass
class SOAPGenerationConfig:
    """Configuration for SOAP note generation"""
    auto_generation: bool = True
    subjective: SOAPSectionConfig = field(default_factory=lambda: SOAPSectionConfig(
        weight=1.0, keywords=["patient states", "reports", "complains", "feels"]
    ))
    objective: SOAPSectionConfig = field(default_factory=lambda: SOAPSectionConfig(
        weight=1.2, keywords=["vital signs", "examination", "observed", "measured"]
    ))
    assessment: SOAPSectionConfig = field(default_factory=lambda: SOAPSectionConfig(
        weight=1.5, keywords=["diagnosis", "condition", "impression", "likely"]
    ))
    plan: SOAPSectionConfig = field(default_factory=lambda: SOAPSectionConfig(
        weight=1.3, keywords=["treatment", "prescribe", "follow-up", "recommend"]
    ))
    chunk_interval: int = 10
    time_interval_seconds: int = 60
    content_threshold_words: int = 50
    manual_trigger: bool = True
    deduplicate_information: bool = True
    merge_overlapping_content: bool = True
    prioritize_recent_content: bool = True
    maintain_chronological_order: bool = True


@dataclass
class PHIProtectionConfig:
    """Configuration for PHI protection"""
    enabled: bool = True
    detection_level: str = "standard"
    thresholds: Dict[str, float] = field(default_factory=lambda: {
        "minimal": 0.6, "standard": 0.8, "maximum": 0.95
    })
    phi_types: List[str] = field(default_factory=lambda: [
        "names", "addresses", "phone_numbers", "ssn", "medical_record_numbers",
        "account_numbers", "dates", "ages_over_89", "biometric_identifiers",
        "photos", "email_addresses", "urls"
    ])
    redaction_method: str = "replacement"
    replacement_token: str = "[REDACTED]"
    preserve_structure: bool = True
    context_aware: bool = True
    real_time_scanning: bool = True
    scan_input: bool = True
    scan_output: bool = True
    alert_on_detection: bool = True


@dataclass
class SessionConfig:
    """Configuration for session management"""
    timeout_minutes: int = 30
    max_recording_minutes: int = 60
    min_session_minutes: int = 5
    max_session_minutes: int = 180
    cleanup_interval_seconds: int = 300
    expired_session_retention_hours: int = 24
    auto_cleanup_enabled: bool = True
    max_concurrent_sessions: int = 100
    max_sessions_per_user: int = 5
    rate_limiting_enabled: bool = True
    session_id_format: str = "session_{random}"
    patient_id_encryption: bool = True
    provider_tracking: bool = True
    encounter_type_validation: bool = True
    chief_complaint_storage: bool = True


@dataclass
class AudioProcessingConfig:
    """Configuration for audio processing"""
    echo_cancellation: bool = True
    noise_suppression: bool = True
    auto_gain_control: bool = True
    preferred_sample_rate: int = 16000
    channel_count: int = 1
    normalize_volume: bool = True
    remove_silence: bool = True
    filter_noise: bool = True
    validate_audio_format: bool = True
    convert_sample_rate: bool = True
    apply_windowing: bool = True
    enhance_speech: bool = True
    reduce_artifacts: bool = True
    apply_compression: bool = False
    min_audio_level: int = -60
    max_audio_level: int = 0
    silence_threshold: int = -40
    quality_score_threshold: float = 0.7


@dataclass
class UISettingsConfig:
    """Configuration for user interface settings"""
    audio_visualization_enabled: bool = True
    bar_count: int = 30
    update_interval_ms: int = 100
    fft_size: int = 256
    smoothing_factor: float = 0.8
    show_confidence_scores: bool = True
    enable_audio_feedback: bool = True
    visual_feedback: bool = True
    haptic_feedback: bool = False
    show_chunk_statistics: bool = True
    show_encryption_status: bool = True
    show_session_progress: bool = True
    auto_scroll_insights: bool = True
    max_insights_displayed: int = 50
    show_progress_bar: bool = True
    max_progress_duration_minutes: int = 30
    progress_update_interval_seconds: int = 1
    show_elapsed_time: bool = True


@dataclass
class PerformanceConfig:
    """Configuration for performance settings"""
    max_concurrent_chunks: int = 10
    chunk_processing_timeout_seconds: int = 30
    max_memory_usage_mb: int = 1024
    cpu_usage_threshold: int = 80
    enable_session_cache: bool = True
    enable_model_cache: bool = True
    cache_ttl_seconds: int = 3600
    max_cache_size_mb: int = 512
    enable_parallel_processing: bool = True
    use_gpu_acceleration: bool = True
    optimize_memory_usage: bool = True
    prefetch_models: bool = True


@dataclass
class ChunkedTranscriptionConfig:
    """Main configuration class for chunked transcription"""
    environment: str = "development"
    chunk_processing: ChunkProcessingConfig = field(default_factory=ChunkProcessingConfig)
    encryption: EncryptionConfig = field(default_factory=EncryptionConfig)
    websocket: WebSocketConfig = field(default_factory=WebSocketConfig)
    progressive_insights: ProgressiveInsightsConfig = field(default_factory=ProgressiveInsightsConfig)
    soap_generation: SOAPGenerationConfig = field(default_factory=SOAPGenerationConfig)
    phi_protection: PHIProtectionConfig = field(default_factory=PHIProtectionConfig)
    session: SessionConfig = field(default_factory=SessionConfig)
    audio_processing: AudioProcessingConfig = field(default_factory=AudioProcessingConfig)
    ui_settings: UISettingsConfig = field(default_factory=UISettingsConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    
    # Development settings
    mock_mode: bool = False
    debug_logging: bool = False
    save_debug_data: bool = False


def expand_environment_variables(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively expand environment variables in config values
    Supports ${VAR_NAME:-default_value} syntax
    """
    if isinstance(config_dict, dict):
        return {key: expand_environment_variables(value) for key, value in config_dict.items()}
    elif isinstance(config_dict, list):
        return [expand_environment_variables(item) for item in config_dict]
    elif isinstance(config_dict, str) and config_dict.startswith("${") and config_dict.endswith("}"):
        # Parse ${VAR_NAME:-default_value}
        var_spec = config_dict[2:-1]  # Remove ${ and }
        if ":-" in var_spec:
            var_name, default_value = var_spec.split(":-", 1)
            return os.getenv(var_name, default_value)
        else:
            return os.getenv(var_spec, config_dict)
    else:
        return config_dict


def load_chunked_transcription_config() -> ChunkedTranscriptionConfig:
    """
    Load chunked transcription configuration from YAML file
    with environment-specific overrides
    """
    # Determine current environment
    detector = EnvironmentDetector()
    environment = detector.detect_environment().value
    
    # Load base configuration
    config_path = os.path.join(
        os.path.dirname(__file__),
        "chunked_transcription_config.yml"
    )
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
        
        # Expand environment variables
        config_data = expand_environment_variables(config_data)
        
        # Apply environment-specific overrides
        if "environments" in config_data and environment in config_data["environments"]:
            env_overrides = config_data["environments"][environment]
            config_data = _merge_config_deep(config_data, env_overrides)
        
        # Create configuration object
        config = ChunkedTranscriptionConfig(environment=environment)
        
        # Populate configuration sections
        if "chunk_processing" in config_data:
            config.chunk_processing = ChunkProcessingConfig(**config_data["chunk_processing"])
        
        if "encryption" in config_data:
            config.encryption = EncryptionConfig(**config_data["encryption"])
        
        if "websocket" in config_data:
            websocket_data = config_data["websocket"]
            if "endpoints" in websocket_data:
                websocket_data.update(websocket_data["endpoints"])
            if "connection" in websocket_data:
                websocket_data.update(websocket_data["connection"])
            if "protocols" in websocket_data:
                protocols = websocket_data["protocols"]
                websocket_data.update({
                    "secure_protocol": protocols.get("secure", "wss"),
                    "insecure_protocol": protocols.get("insecure", "ws"),
                    "default_port": protocols.get("default_port", 8000),
                    "ssl_verify": protocols.get("ssl_verify", True)
                })
            if "message_types" in websocket_data:
                websocket_data["message_types"] = websocket_data["message_types"]
            config.websocket = WebSocketConfig(**_filter_config_keys(websocket_data, WebSocketConfig))
        
        if "progressive_insights" in config_data:
            insights_data = config_data["progressive_insights"]
            if "medical_entity_extraction" in insights_data:
                entity_config = MedicalEntityConfig(**insights_data["medical_entity_extraction"])
                insights_data["medical_entity_extraction"] = entity_config
            if "clinical_alerts" in insights_data:
                alerts = insights_data["clinical_alerts"]
                insights_data.update({
                    "clinical_alerts_enabled": alerts.get("enabled", True),
                    "alert_types": alerts.get("alert_types", []),
                    "critical_alert_threshold": alerts.get("critical_alert_threshold", 0.9),
                    "warning_alert_threshold": alerts.get("warning_alert_threshold", 0.75),
                    "info_alert_threshold": alerts.get("info_alert_threshold", 0.6)
                })
            if "insights_processing" in insights_data:
                processing = insights_data["insights_processing"]
                insights_data.update({
                    "batch_insights": processing.get("batch_insights", False),
                    "real_time_updates": processing.get("real_time_updates", True),
                    "context_window_chunks": processing.get("context_window_chunks", 5),
                    "insight_confidence_threshold": processing.get("insight_confidence_threshold", 0.7)
                })
            config.progressive_insights = ProgressiveInsightsConfig(**_filter_config_keys(insights_data, ProgressiveInsightsConfig))
        
        if "soap_generation" in config_data:
            soap_data = config_data["soap_generation"]
            
            # Handle sections
            if "sections" in soap_data:
                sections = soap_data["sections"]
                for section_name in ["subjective", "objective", "assessment", "plan"]:
                    if section_name in sections:
                        section_config = SOAPSectionConfig(**sections[section_name])
                        soap_data[section_name] = section_config
            
            # Handle triggers
            if "triggers" in soap_data:
                triggers = soap_data["triggers"]
                soap_data.update({
                    "chunk_interval": triggers.get("chunk_interval", 10),
                    "time_interval_seconds": triggers.get("time_interval_seconds", 60),
                    "content_threshold_words": triggers.get("content_threshold_words", 50),
                    "manual_trigger": triggers.get("manual_trigger", True)
                })
            
            # Handle content processing
            if "content_processing" in soap_data:
                processing = soap_data["content_processing"]
                soap_data.update({
                    "deduplicate_information": processing.get("deduplicate_information", True),
                    "merge_overlapping_content": processing.get("merge_overlapping_content", True),
                    "prioritize_recent_content": processing.get("prioritize_recent_content", True),
                    "maintain_chronological_order": processing.get("maintain_chronological_order", True)
                })
            
            config.soap_generation = SOAPGenerationConfig(**_filter_config_keys(soap_data, SOAPGenerationConfig))
        
        if "phi_protection" in config_data:
            phi_data = config_data["phi_protection"]
            if "redaction" in phi_data:
                redaction = phi_data["redaction"]
                phi_data.update({
                    "redaction_method": redaction.get("method", "replacement"),
                    "replacement_token": redaction.get("replacement_token", "[REDACTED]"),
                    "preserve_structure": redaction.get("preserve_structure", True),
                    "context_aware": redaction.get("context_aware", True)
                })
            if "real_time_scanning" in phi_data:
                scanning = phi_data["real_time_scanning"]
                phi_data.update({
                    "real_time_scanning": scanning.get("enabled", True),
                    "scan_input": scanning.get("scan_input", True),
                    "scan_output": scanning.get("scan_output", True),
                    "alert_on_detection": scanning.get("alert_on_detection", True)
                })
            config.phi_protection = PHIProtectionConfig(**_filter_config_keys(phi_data, PHIProtectionConfig))
        
        if "session" in config_data:
            session_data = config_data["session"]
            if "session_metadata" in session_data:
                metadata = session_data["session_metadata"]
                session_data.update({
                    "patient_id_encryption": metadata.get("patient_id_encryption", True),
                    "provider_tracking": metadata.get("provider_tracking", True),
                    "encounter_type_validation": metadata.get("encounter_type_validation", True),
                    "chief_complaint_storage": metadata.get("chief_complaint_storage", True)
                })
            config.session = SessionConfig(**_filter_config_keys(session_data, SessionConfig))
        
        if "audio_processing" in config_data:
            audio_data = config_data["audio_processing"]
            # Flatten nested structure
            for section in ["input", "pipeline", "quality"]:
                if section in audio_data:
                    audio_data.update(audio_data[section])
                    if "pre_processing" in audio_data:
                        audio_data.update(audio_data["pre_processing"])
                    if "chunk_processing" in audio_data:
                        audio_data.update(audio_data["chunk_processing"])
                    if "post_processing" in audio_data:
                        audio_data.update(audio_data["post_processing"])
            config.audio_processing = AudioProcessingConfig(**_filter_config_keys(audio_data, AudioProcessingConfig))
        
        if "ui_settings" in config_data:
            ui_data = config_data["ui_settings"]
            # Flatten nested structure
            for section in ["audio_visualization", "feedback", "display", "progress"]:
                if section in ui_data:
                    section_data = ui_data[section]
                    if section == "audio_visualization":
                        ui_data.update({
                            "audio_visualization_enabled": section_data.get("enabled", True),
                            "bar_count": section_data.get("bar_count", 30),
                            "update_interval_ms": section_data.get("update_interval_ms", 100),
                            "fft_size": section_data.get("fft_size", 256),
                            "smoothing_factor": section_data.get("smoothing_factor", 0.8)
                        })
                    elif section == "progress":
                        ui_data.update({
                            "show_progress_bar": section_data.get("show_progress_bar", True),
                            "max_progress_duration_minutes": section_data.get("max_progress_duration_minutes", 30),
                            "progress_update_interval_seconds": section_data.get("update_interval_seconds", 1),
                            "show_elapsed_time": section_data.get("show_elapsed_time", True)
                        })
                    else:
                        ui_data.update(section_data)
            config.ui_settings = UISettingsConfig(**_filter_config_keys(ui_data, UISettingsConfig))
        
        if "performance" in config_data:
            perf_data = config_data["performance"]
            # Flatten nested structure
            for section in ["processing", "caching", "optimization"]:
                if section in perf_data:
                    perf_data.update(perf_data[section])
            config.performance = PerformanceConfig(**_filter_config_keys(perf_data, PerformanceConfig))
        
        # Development settings
        if "development" in config_data:
            dev_data = config_data["development"]
            config.mock_mode = dev_data.get("mock_mode", False)
            config.debug_logging = dev_data.get("debug_logging", False)
            config.save_debug_data = dev_data.get("save_debug_data", False)
        
        return config
        
    except FileNotFoundError:
        print(f"Warning: Configuration file not found at {config_path}. Using defaults.")
        return ChunkedTranscriptionConfig(environment=environment)
    except yaml.YAMLError as e:
        print(f"Error parsing configuration file: {e}. Using defaults.")
        return ChunkedTranscriptionConfig(environment=environment)
    except Exception as e:
        print(f"Error loading configuration: {e}. Using defaults.")
        return ChunkedTranscriptionConfig(environment=environment)


def _merge_config_deep(base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge configuration dictionaries"""
    result = base_config.copy()
    
    for key, value in override_config.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_config_deep(result[key], value)
        else:
            result[key] = value
    
    return result


def _filter_config_keys(config_dict: Dict[str, Any], config_class: type) -> Dict[str, Any]:
    """Filter dictionary to only include keys that exist in the dataclass"""
    if hasattr(config_class, "__dataclass_fields__"):
        valid_keys = set(config_class.__dataclass_fields__.keys())
        return {k: v for k, v in config_dict.items() if k in valid_keys}
    return config_dict


# Global configuration instance
_chunked_config: Optional[ChunkedTranscriptionConfig] = None


def get_chunked_transcription_config() -> ChunkedTranscriptionConfig:
    """Get the global chunked transcription configuration instance"""
    global _chunked_config
    if _chunked_config is None:
        _chunked_config = load_chunked_transcription_config()
    return _chunked_config


def reload_chunked_transcription_config() -> ChunkedTranscriptionConfig:
    """Reload the configuration from file"""
    global _chunked_config
    _chunked_config = load_chunked_transcription_config()
    return _chunked_config


def get_config_for_environment(environment: str) -> ChunkedTranscriptionConfig:
    """Get configuration for a specific environment"""
    # Temporarily override environment detection
    original_env = os.environ.get("ENVIRONMENT")
    os.environ["ENVIRONMENT"] = environment
    
    try:
        config = load_chunked_transcription_config()
        return config
    finally:
        # Restore original environment
        if original_env:
            os.environ["ENVIRONMENT"] = original_env
        elif "ENVIRONMENT" in os.environ:
            del os.environ["ENVIRONMENT"]