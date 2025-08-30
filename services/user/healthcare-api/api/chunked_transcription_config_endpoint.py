"""
FastAPI Endpoint for Chunked Transcription Configuration
Serves configuration settings to the frontend interface
"""

from fastapi import APIRouter, HTTPException
from typing import Any, Dict

try:
    from config.chunked_transcription_config_loader import get_chunked_transcription_config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False

router = APIRouter(prefix="/api/transcription/chunked", tags=["transcription", "configuration"])


@router.get("/config")
async def get_chunked_transcription_config_endpoint() -> Dict[str, Any]:
    """
    Get chunked transcription configuration for frontend
    
    Returns:
        Dict containing configuration sections for frontend use
    """
    
    if not CONFIG_AVAILABLE:
        return {
            "error": "Configuration system not available",
            "chunk_processing": {
                "duration_seconds": 5,
                "overlap_seconds": 1.0,
                "sample_rate": 16000
            },
            "encryption": {
                "enabled": True,
                "algorithm": "AES-256-GCM"
            },
            "progressive_insights": {
                "enabled": True
            },
            "ui_settings": {
                "show_confidence_scores": True,
                "enable_audio_feedback": True,
                "bar_count": 30,
                "update_interval_ms": 100,
                "max_progress_duration_minutes": 30,
                "auto_scroll_insights": True,
                "max_insights_displayed": 50
            },
            "session": {
                "max_recording_minutes": 60
            },
            "websocket": {
                "default_port": 8000
            },
            "phi_protection": {
                "enabled": True
            }
        }
    
    try:
        config = get_chunked_transcription_config()
        
        # Build response with frontend-relevant configuration
        response = {
            "environment": config.environment,
            "chunk_processing": {
                "duration_seconds": config.chunk_processing.duration_seconds,
                "overlap_seconds": config.chunk_processing.overlap_seconds,
                "sample_rate": config.chunk_processing.sample_rate,
                "bit_depth": config.chunk_processing.bit_depth,
                "channels": config.chunk_processing.channels,
                "audio_format": config.chunk_processing.audio_format,
                "codec": config.chunk_processing.codec,
                "bitrate": config.chunk_processing.bitrate,
                "crossfade_enabled": config.chunk_processing.crossfade_enabled,
                "crossfade_duration_ms": config.chunk_processing.crossfade_duration_ms,
                "audio_artifact_prevention": config.chunk_processing.audio_artifact_prevention
            },
            "encryption": {
                "enabled": config.encryption.enabled,
                "algorithm": config.encryption.algorithm,
                "key_size_bits": config.encryption.key_size_bits,
                "session_key_rotation_interval_seconds": config.encryption.session_key_rotation_interval_seconds,
                "session_token_length": config.encryption.session_token_length
            },
            "websocket": {
                "base_path": config.websocket.base_path,
                "timeout_seconds": config.websocket.timeout_seconds,
                "heartbeat_interval_seconds": config.websocket.heartbeat_interval_seconds,
                "max_message_size_bytes": config.websocket.max_message_size_bytes,
                "compression_enabled": config.websocket.compression_enabled,
                "default_port": config.websocket.default_port,
                "ssl_verify": config.websocket.ssl_verify
            },
            "progressive_insights": {
                "enabled": config.progressive_insights.enabled,
                "medical_entity_extraction": {
                    "enabled": config.progressive_insights.medical_entity_extraction.enabled,
                    "confidence_threshold": config.progressive_insights.medical_entity_extraction.confidence_threshold,
                    "entity_types": config.progressive_insights.medical_entity_extraction.entity_types,
                    "medical_term_confidence_boost": config.progressive_insights.medical_entity_extraction.medical_term_confidence_boost,
                    "specialized_term_weight": config.progressive_insights.medical_entity_extraction.specialized_term_weight,
                    "terminology_validation": config.progressive_insights.medical_entity_extraction.terminology_validation
                },
                "clinical_alerts_enabled": config.progressive_insights.clinical_alerts_enabled,
                "alert_types": config.progressive_insights.alert_types,
                "critical_alert_threshold": config.progressive_insights.critical_alert_threshold,
                "warning_alert_threshold": config.progressive_insights.warning_alert_threshold,
                "info_alert_threshold": config.progressive_insights.info_alert_threshold,
                "batch_insights": config.progressive_insights.batch_insights,
                "real_time_updates": config.progressive_insights.real_time_updates,
                "context_window_chunks": config.progressive_insights.context_window_chunks,
                "insight_confidence_threshold": config.progressive_insights.insight_confidence_threshold
            },
            "soap_generation": {
                "auto_generation": config.soap_generation.auto_generation,
                "chunk_interval": config.soap_generation.chunk_interval,
                "time_interval_seconds": config.soap_generation.time_interval_seconds,
                "content_threshold_words": config.soap_generation.content_threshold_words,
                "manual_trigger": config.soap_generation.manual_trigger,
                "deduplicate_information": config.soap_generation.deduplicate_information,
                "merge_overlapping_content": config.soap_generation.merge_overlapping_content,
                "prioritize_recent_content": config.soap_generation.prioritize_recent_content,
                "maintain_chronological_order": config.soap_generation.maintain_chronological_order
            },
            "phi_protection": {
                "enabled": config.phi_protection.enabled,
                "detection_level": config.phi_protection.detection_level,
                "thresholds": config.phi_protection.thresholds,
                "phi_types": config.phi_protection.phi_types,
                "redaction_method": config.phi_protection.redaction_method,
                "replacement_token": config.phi_protection.replacement_token,
                "preserve_structure": config.phi_protection.preserve_structure,
                "context_aware": config.phi_protection.context_aware,
                "real_time_scanning": config.phi_protection.real_time_scanning,
                "scan_input": config.phi_protection.scan_input,
                "scan_output": config.phi_protection.scan_output,
                "alert_on_detection": config.phi_protection.alert_on_detection
            },
            "session": {
                "timeout_minutes": config.session.timeout_minutes,
                "max_recording_minutes": config.session.max_recording_minutes,
                "min_session_minutes": config.session.min_session_minutes,
                "max_session_minutes": config.session.max_session_minutes,
                "cleanup_interval_seconds": config.session.cleanup_interval_seconds,
                "expired_session_retention_hours": config.session.expired_session_retention_hours,
                "auto_cleanup_enabled": config.session.auto_cleanup_enabled,
                "max_concurrent_sessions": config.session.max_concurrent_sessions,
                "max_sessions_per_user": config.session.max_sessions_per_user,
                "rate_limiting_enabled": config.session.rate_limiting_enabled,
                "session_id_format": config.session.session_id_format,
                "patient_id_encryption": config.session.patient_id_encryption,
                "provider_tracking": config.session.provider_tracking,
                "encounter_type_validation": config.session.encounter_type_validation,
                "chief_complaint_storage": config.session.chief_complaint_storage
            },
            "audio_processing": {
                "echo_cancellation": config.audio_processing.echo_cancellation,
                "noise_suppression": config.audio_processing.noise_suppression,
                "auto_gain_control": config.audio_processing.auto_gain_control,
                "preferred_sample_rate": config.audio_processing.preferred_sample_rate,
                "channel_count": config.audio_processing.channel_count,
                "normalize_volume": config.audio_processing.normalize_volume,
                "remove_silence": config.audio_processing.remove_silence,
                "filter_noise": config.audio_processing.filter_noise,
                "validate_audio_format": config.audio_processing.validate_audio_format,
                "convert_sample_rate": config.audio_processing.convert_sample_rate,
                "apply_windowing": config.audio_processing.apply_windowing,
                "enhance_speech": config.audio_processing.enhance_speech,
                "reduce_artifacts": config.audio_processing.reduce_artifacts,
                "apply_compression": config.audio_processing.apply_compression,
                "min_audio_level": config.audio_processing.min_audio_level,
                "max_audio_level": config.audio_processing.max_audio_level,
                "silence_threshold": config.audio_processing.silence_threshold,
                "quality_score_threshold": config.audio_processing.quality_score_threshold
            },
            "ui_settings": {
                "audio_visualization_enabled": config.ui_settings.audio_visualization_enabled,
                "bar_count": config.ui_settings.bar_count,
                "update_interval_ms": config.ui_settings.update_interval_ms,
                "fft_size": config.ui_settings.fft_size,
                "smoothing_factor": config.ui_settings.smoothing_factor,
                "show_confidence_scores": config.ui_settings.show_confidence_scores,
                "enable_audio_feedback": config.ui_settings.enable_audio_feedback,
                "visual_feedback": config.ui_settings.visual_feedback,
                "haptic_feedback": config.ui_settings.haptic_feedback,
                "show_chunk_statistics": config.ui_settings.show_chunk_statistics,
                "show_encryption_status": config.ui_settings.show_encryption_status,
                "show_session_progress": config.ui_settings.show_session_progress,
                "auto_scroll_insights": config.ui_settings.auto_scroll_insights,
                "max_insights_displayed": config.ui_settings.max_insights_displayed,
                "show_progress_bar": config.ui_settings.show_progress_bar,
                "max_progress_duration_minutes": config.ui_settings.max_progress_duration_minutes,
                "progress_update_interval_seconds": config.ui_settings.progress_update_interval_seconds,
                "show_elapsed_time": config.ui_settings.show_elapsed_time
            },
            "performance": {
                "max_concurrent_chunks": config.performance.max_concurrent_chunks,
                "chunk_processing_timeout_seconds": config.performance.chunk_processing_timeout_seconds,
                "max_memory_usage_mb": config.performance.max_memory_usage_mb,
                "cpu_usage_threshold": config.performance.cpu_usage_threshold,
                "enable_session_cache": config.performance.enable_session_cache,
                "enable_model_cache": config.performance.enable_model_cache,
                "cache_ttl_seconds": config.performance.cache_ttl_seconds,
                "max_cache_size_mb": config.performance.max_cache_size_mb,
                "enable_parallel_processing": config.performance.enable_parallel_processing,
                "use_gpu_acceleration": config.performance.use_gpu_acceleration,
                "optimize_memory_usage": config.performance.optimize_memory_usage,
                "prefetch_models": config.performance.prefetch_models
            },
            "development": {
                "mock_mode": config.mock_mode,
                "debug_logging": config.debug_logging,
                "save_debug_data": config.save_debug_data
            }
        }
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error loading chunked transcription configuration: {str(e)}"
        )


@router.get("/config/summary")
async def get_config_summary() -> Dict[str, Any]:
    """
    Get a summary of key configuration settings for frontend
    
    Returns:
        Simplified configuration object with key settings only
    """
    
    if not CONFIG_AVAILABLE:
        return {
            "chunk_duration_seconds": 5,
            "chunk_overlap_seconds": 1.0,
            "sample_rate": 16000,
            "encryption_enabled": True,
            "progressive_insights_enabled": True,
            "auto_soap_generation": True,
            "phi_protection_enabled": True,
            "max_recording_minutes": 60,
            "websocket_port": 8000
        }
    
    try:
        config = get_chunked_transcription_config()
        
        return {
            "environment": config.environment,
            "chunk_duration_seconds": config.chunk_processing.duration_seconds,
            "chunk_overlap_seconds": config.chunk_processing.overlap_seconds,
            "sample_rate": config.chunk_processing.sample_rate,
            "encryption_enabled": config.encryption.enabled,
            "encryption_algorithm": config.encryption.algorithm,
            "progressive_insights_enabled": config.progressive_insights.enabled,
            "medical_entity_extraction_enabled": config.progressive_insights.medical_entity_extraction.enabled,
            "auto_soap_generation": config.soap_generation.auto_generation,
            "phi_protection_enabled": config.phi_protection.enabled,
            "phi_detection_level": config.phi_protection.detection_level,
            "session_timeout_minutes": config.session.timeout_minutes,
            "max_recording_minutes": config.session.max_recording_minutes,
            "websocket_port": config.websocket.default_port,
            "show_confidence_scores": config.ui_settings.show_confidence_scores,
            "enable_audio_feedback": config.ui_settings.enable_audio_feedback,
            "audio_visualization_bars": config.ui_settings.bar_count,
            "max_insights_displayed": config.ui_settings.max_insights_displayed,
            "mock_mode": config.mock_mode,
            "debug_logging": config.debug_logging
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error loading configuration summary: {str(e)}"
        )


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint for chunked transcription configuration service
    
    Returns:
        Health status and configuration availability
    """
    
    status = "healthy"
    config_status = "available" if CONFIG_AVAILABLE else "unavailable"
    
    try:
        if CONFIG_AVAILABLE:
            # Try to load config to verify it's working
            get_chunked_transcription_config()
            config_load_status = "success"
        else:
            config_load_status = "not_available"
    except Exception as e:
        status = "degraded"
        config_load_status = f"error: {str(e)}"
    
    return {
        "status": status,
        "config_system": config_status,
        "config_loading": config_load_status,
        "service": "chunked_transcription_config"
    }