"""
Example usage of the chunked transcription configuration system
Demonstrates how to load and use configuration in different scenarios
"""

import asyncio
from datetime import datetime
from typing import Dict, Any

from config.chunked_transcription_config_loader import (
    get_chunked_transcription_config,
    reload_chunked_transcription_config,
    get_config_for_environment
)


def demonstrate_basic_usage():
    """Demonstrate basic configuration loading and usage"""
    
    print("=== Basic Configuration Usage ===")
    
    # Load the global configuration
    config = get_chunked_transcription_config()
    
    print(f"Environment: {config.environment}")
    print(f"Chunk Duration: {config.chunk_processing.duration_seconds} seconds")
    print(f"Chunk Overlap: {config.chunk_processing.overlap_seconds} seconds")
    print(f"Sample Rate: {config.chunk_processing.sample_rate} Hz")
    print(f"Encryption Enabled: {config.encryption.enabled}")
    print(f"Progressive Insights: {config.progressive_insights.enabled}")
    print(f"SOAP Generation: {config.soap_generation.auto_generation}")
    print(f"PHI Protection: {config.phi_protection.enabled} ({config.phi_protection.detection_level})")
    print()


def demonstrate_environment_specific_config():
    """Demonstrate loading configuration for specific environments"""
    
    print("=== Environment-Specific Configuration ===")
    
    environments = ["development", "testing", "production"]
    
    for env in environments:
        config = get_config_for_environment(env)
        print(f"{env.upper()}:")
        print(f"  Encryption: {config.encryption.enabled}")
        print(f"  Debug Logging: {config.debug_logging}")
        print(f"  Mock Mode: {config.mock_mode}")
        print(f"  Session Timeout: {config.session.timeout_minutes} minutes")
        print()


def demonstrate_audio_configuration():
    """Demonstrate using audio processing configuration"""
    
    print("=== Audio Configuration Usage ===")
    
    config = get_chunked_transcription_config()
    
    # Example: Configure media recorder settings
    audio_config = {
        "echoCancellation": config.audio_processing.echo_cancellation,
        "noiseSuppression": config.audio_processing.noise_suppression,
        "autoGainControl": config.audio_processing.auto_gain_control,
        "sampleRate": config.audio_processing.preferred_sample_rate,
        "channelCount": config.audio_processing.channel_count
    }
    
    print("MediaRecorder Configuration:")
    for key, value in audio_config.items():
        print(f"  {key}: {value}")
    
    # Example: Configure chunk processing
    chunk_config = {
        "duration_ms": config.chunk_processing.duration_seconds * 1000,
        "overlap_ms": config.chunk_processing.overlap_seconds * 1000,
        "sample_rate": config.chunk_processing.sample_rate,
        "audio_format": config.chunk_processing.audio_format,
        "codec": config.chunk_processing.codec,
        "bitrate": config.chunk_processing.bitrate
    }
    
    print("\nChunk Processing Configuration:")
    for key, value in chunk_config.items():
        print(f"  {key}: {value}")
    print()


def demonstrate_security_configuration():
    """Demonstrate using security and encryption configuration"""
    
    print("=== Security Configuration Usage ===")
    
    config = get_chunked_transcription_config()
    
    # Example: WebSocket security configuration
    websocket_security = {
        "encryption_enabled": config.encryption.enabled,
        "algorithm": config.encryption.algorithm,
        "key_size": config.encryption.key_size_bits,
        "session_key_rotation": config.encryption.session_key_rotation_interval_seconds,
        "ssl_verify": config.websocket.ssl_verify
    }
    
    print("WebSocket Security Configuration:")
    for key, value in websocket_security.items():
        print(f"  {key}: {value}")
    
    # Example: PHI protection configuration
    phi_config = {
        "enabled": config.phi_protection.enabled,
        "detection_level": config.phi_protection.detection_level,
        "real_time_scanning": config.phi_protection.real_time_scanning,
        "redaction_method": config.phi_protection.redaction_method,
        "replacement_token": config.phi_protection.replacement_token
    }
    
    print("\nPHI Protection Configuration:")
    for key, value in phi_config.items():
        print(f"  {key}: {value}")
    print()


def demonstrate_ui_configuration():
    """Demonstrate using UI configuration"""
    
    print("=== UI Configuration Usage ===")
    
    config = get_chunked_transcription_config()
    
    # Example: Audio visualization configuration
    visualization_config = {
        "enabled": config.ui_settings.audio_visualization_enabled,
        "bar_count": config.ui_settings.bar_count,
        "update_interval_ms": config.ui_settings.update_interval_ms,
        "fft_size": config.ui_settings.fft_size,
        "smoothing_factor": config.ui_settings.smoothing_factor
    }
    
    print("Audio Visualization Configuration:")
    for key, value in visualization_config.items():
        print(f"  {key}: {value}")
    
    # Example: User interface settings
    ui_settings = {
        "show_confidence_scores": config.ui_settings.show_confidence_scores,
        "enable_audio_feedback": config.ui_settings.enable_audio_feedback,
        "show_encryption_status": config.ui_settings.show_encryption_status,
        "auto_scroll_insights": config.ui_settings.auto_scroll_insights,
        "max_insights_displayed": config.ui_settings.max_insights_displayed,
        "show_progress_bar": config.ui_settings.show_progress_bar
    }
    
    print("\nUI Settings:")
    for key, value in ui_settings.items():
        print(f"  {key}: {value}")
    print()


def demonstrate_performance_configuration():
    """Demonstrate using performance configuration"""
    
    print("=== Performance Configuration Usage ===")
    
    config = get_chunked_transcription_config()
    
    # Example: Processing limits
    processing_config = {
        "max_concurrent_chunks": config.performance.max_concurrent_chunks,
        "chunk_processing_timeout": config.performance.chunk_processing_timeout_seconds,
        "max_memory_usage_mb": config.performance.max_memory_usage_mb,
        "cpu_usage_threshold": config.performance.cpu_usage_threshold
    }
    
    print("Processing Configuration:")
    for key, value in processing_config.items():
        print(f"  {key}: {value}")
    
    # Example: Caching configuration
    cache_config = {
        "session_cache_enabled": config.performance.enable_session_cache,
        "model_cache_enabled": config.performance.enable_model_cache,
        "cache_ttl_seconds": config.performance.cache_ttl_seconds,
        "max_cache_size_mb": config.performance.max_cache_size_mb
    }
    
    print("\nCaching Configuration:")
    for key, value in cache_config.items():
        print(f"  {key}: {value}")
    
    # Example: Optimization settings
    optimization_config = {
        "parallel_processing": config.performance.enable_parallel_processing,
        "gpu_acceleration": config.performance.use_gpu_acceleration,
        "memory_optimization": config.performance.optimize_memory_usage,
        "model_prefetching": config.performance.prefetch_models
    }
    
    print("\nOptimization Settings:")
    for key, value in optimization_config.items():
        print(f"  {key}: {value}")
    print()


async def demonstrate_session_configuration():
    """Demonstrate using session management configuration"""
    
    print("=== Session Configuration Usage ===")
    
    config = get_chunked_transcription_config()
    
    # Example: Session timeout management
    session_config = {
        "timeout_minutes": config.session.timeout_minutes,
        "max_recording_minutes": config.session.max_recording_minutes,
        "cleanup_interval_seconds": config.session.cleanup_interval_seconds,
        "max_concurrent_sessions": config.session.max_concurrent_sessions,
        "rate_limiting_enabled": config.session.rate_limiting_enabled
    }
    
    print("Session Management Configuration:")
    for key, value in session_config.items():
        print(f"  {key}: {value}")
    
    # Example: Session security configuration
    session_security = {
        "patient_id_encryption": config.session.patient_id_encryption,
        "provider_tracking": config.session.provider_tracking,
        "encounter_type_validation": config.session.encounter_type_validation,
        "chief_complaint_storage": config.session.chief_complaint_storage
    }
    
    print("\nSession Security Configuration:")
    for key, value in session_security.items():
        print(f"  {key}: {value}")
    print()


def demonstrate_medical_processing_configuration():
    """Demonstrate using medical processing configuration"""
    
    print("=== Medical Processing Configuration Usage ===")
    
    config = get_chunked_transcription_config()
    
    # Example: Medical entity extraction configuration
    entity_config = {
        "enabled": config.progressive_insights.medical_entity_extraction.enabled,
        "confidence_threshold": config.progressive_insights.medical_entity_extraction.confidence_threshold,
        "entity_types": config.progressive_insights.medical_entity_extraction.entity_types,
        "confidence_boost": config.progressive_insights.medical_entity_extraction.medical_term_confidence_boost,
        "terminology_validation": config.progressive_insights.medical_entity_extraction.terminology_validation
    }
    
    print("Medical Entity Extraction Configuration:")
    for key, value in entity_config.items():
        if isinstance(value, list):
            print(f"  {key}: {len(value)} types")
        else:
            print(f"  {key}: {value}")
    
    # Example: SOAP generation configuration
    soap_config = {
        "auto_generation": config.soap_generation.auto_generation,
        "chunk_interval": config.soap_generation.chunk_interval,
        "time_interval_seconds": config.soap_generation.time_interval_seconds,
        "content_threshold_words": config.soap_generation.content_threshold_words,
        "deduplicate_information": config.soap_generation.deduplicate_information
    }
    
    print("\nSOAP Generation Configuration:")
    for key, value in soap_config.items():
        print(f"  {key}: {value}")
    
    # Example: Clinical alerts configuration
    alerts_config = {
        "enabled": config.progressive_insights.clinical_alerts_enabled,
        "alert_types": len(config.progressive_insights.alert_types),
        "critical_threshold": config.progressive_insights.critical_alert_threshold,
        "warning_threshold": config.progressive_insights.warning_alert_threshold,
        "info_threshold": config.progressive_insights.info_alert_threshold
    }
    
    print("\nClinical Alerts Configuration:")
    for key, value in alerts_config.items():
        print(f"  {key}: {value}")
    print()


def demonstrate_configuration_reloading():
    """Demonstrate configuration reloading"""
    
    print("=== Configuration Reloading ===")
    
    # Load initial configuration
    config1 = get_chunked_transcription_config()
    print(f"Initial config chunk duration: {config1.chunk_processing.duration_seconds}")
    
    # Reload configuration (in real usage, this would pick up file changes)
    config2 = reload_chunked_transcription_config()
    print(f"Reloaded config chunk duration: {config2.chunk_processing.duration_seconds}")
    
    # Verify they're the same object (global singleton)
    config3 = get_chunked_transcription_config()
    print(f"Global config is same instance: {config2 is config3}")
    print()


def main():
    """Run all configuration usage demonstrations"""
    
    print("Chunked Transcription Configuration Usage Examples")
    print("=" * 60)
    print()
    
    try:
        demonstrate_basic_usage()
        demonstrate_environment_specific_config()
        demonstrate_audio_configuration()
        demonstrate_security_configuration()
        demonstrate_ui_configuration()
        demonstrate_performance_configuration()
        asyncio.run(demonstrate_session_configuration())
        demonstrate_medical_processing_configuration()
        demonstrate_configuration_reloading()
        
        print("=== Configuration System Benefits ===")
        print("✅ Centralized configuration management")
        print("✅ Environment-specific overrides")
        print("✅ Type safety with dataclasses")
        print("✅ Environment variable expansion")
        print("✅ Graceful fallbacks for missing config")
        print("✅ Hierarchical configuration structure")
        print("✅ Easy testing with environment-specific configs")
        print("✅ Validation and constraints")
        print()
        
    except Exception as e:
        print(f"Error demonstrating configuration: {e}")
        print("This might happen if the configuration file is not found.")
        print("The system will fall back to defaults in production.")


if __name__ == "__main__":
    main()