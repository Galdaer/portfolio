"""
UI Configuration Loader
Loads and validates Open WebUI integration configuration from YAML files
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, validator


@dataclass
class ApiIntegrationConfig:
    """Healthcare API integration configuration"""
    websocket_url: str
    rest_api_url: str
    health_check_endpoint: str
    transcription_endpoint: str
    soap_generation_endpoint: str


@dataclass
class DeveloperConfig:
    """Developer configuration"""
    mode_enabled: bool
    debug_logging: bool
    test_users: list[str]
    default_test_user: str
    mock_transcription: bool
    bypass_user_validation: bool


@dataclass
class ActionConfig:
    """Open WebUI action configuration"""
    id: str
    name: str
    description: str
    icon: str
    category: str
    button_text: str


@dataclass
class SessionConfig:
    """Session management configuration"""
    timeout_seconds: int
    chunk_interval_seconds: int
    auto_soap_generation: bool
    session_cleanup_enabled: bool


@dataclass
class UserExperienceConfig:
    """User experience configuration"""
    show_real_time_transcription: bool
    show_status_updates: bool
    enable_progress_indicators: bool
    auto_scroll_enabled: bool


@dataclass
class ComplianceConfig:
    """Medical compliance configuration"""
    show_medical_disclaimer: bool
    disclaimer_text: str
    phi_protection_enabled: bool
    audit_logging_enabled: bool
    healthcare_compliance_mode: bool


@dataclass
class EventsConfig:
    """Event handling configuration"""
    emit_status_updates: bool
    emit_transcription_chunks: bool
    emit_session_events: bool
    emit_error_notifications: bool


@dataclass
class ErrorHandlingConfig:
    """Error handling configuration"""
    connection_retry_attempts: int
    retry_delay_seconds: int
    show_detailed_errors: bool
    fallback_to_mock_on_failure: bool


@dataclass
class PerformanceConfig:
    """Performance settings configuration"""
    debounce_events_ms: int
    max_concurrent_sessions: int
    memory_cleanup_interval_seconds: int


@dataclass
class UiCustomizationConfig:
    """UI customization configuration"""
    primary_color: str
    success_color: str
    warning_color: str
    error_color: str


@dataclass
class FeaturesConfig:
    """Feature flags configuration"""
    enable_audio_visualization: bool
    enable_session_history: bool
    enable_export_functionality: bool
    enable_real_time_editing: bool


@dataclass
class NotificationsConfig:
    """Notifications configuration"""
    show_connection_status: bool
    show_transcription_quality: bool
    show_session_time_remaining: bool
    auto_hide_success_messages: bool
    message_display_duration_seconds: int


@dataclass
class TestingConfig:
    """Testing and validation configuration"""
    enable_test_mode: bool
    mock_session_data: bool
    validation_checks_enabled: bool
    performance_monitoring: bool


class UiConfig(BaseModel):
    """Complete UI configuration"""

    api_integration: ApiIntegrationConfig
    developer: DeveloperConfig
    action: ActionConfig
    session: SessionConfig
    user_experience: UserExperienceConfig
    compliance: ComplianceConfig
    events: EventsConfig
    error_handling: ErrorHandlingConfig
    performance: PerformanceConfig
    ui_customization: UiCustomizationConfig
    features: FeaturesConfig
    notifications: NotificationsConfig
    testing: TestingConfig

    @validator("developer")
    def validate_developer_config(cls, v):
        """Validate developer configuration"""
        if v.mode_enabled and not v.test_users:
            raise ValueError("Developer mode enabled but no test users specified")
        if v.default_test_user and v.default_test_user not in v.test_users:
            raise ValueError("Default test user must be in test_users list")
        return v

    @validator("session")
    def validate_session_config(cls, v):
        """Validate session configuration"""
        if v.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if v.chunk_interval_seconds <= 0:
            raise ValueError("chunk_interval_seconds must be positive")
        if v.chunk_interval_seconds > v.timeout_seconds:
            raise ValueError("chunk_interval_seconds cannot exceed timeout_seconds")
        return v

    @validator("ui_customization")
    def validate_colors(cls, v):
        """Validate color values are valid hex colors"""
        colors = {
            "primary_color": v.primary_color,
            "success_color": v.success_color,
            "warning_color": v.warning_color,
            "error_color": v.error_color,
        }

        for color_name, color_value in colors.items():
            if not color_value.startswith("#") or len(color_value) != 7:
                msg = f"{color_name} must be a valid hex color (e.g., #2563eb)"
                raise ValueError(msg)
        return v


def load_ui_config(config_path: str | Path | None = None) -> UiConfig:
    """Load UI configuration from YAML file"""

    if config_path is None:
        config_path = Path(__file__).parent / "ui_config.yml"

    config_path = Path(config_path)

    if not config_path.exists():
        msg = f"UI config file not found: {config_path}"
        raise FileNotFoundError(msg)

    try:
        with open(config_path, encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        if not isinstance(config_data, dict):
            raise ValueError("Config file must contain a YAML dictionary")

        # Create configuration objects
        return UiConfig(
            api_integration=ApiIntegrationConfig(**config_data.get("api_integration", {})),
            developer=DeveloperConfig(**config_data.get("developer", {})),
            action=ActionConfig(**config_data.get("action", {})),
            session=SessionConfig(**config_data.get("session", {})),
            user_experience=UserExperienceConfig(**config_data.get("user_experience", {})),
            compliance=ComplianceConfig(**config_data.get("compliance", {})),
            events=EventsConfig(**config_data.get("events", {})),
            error_handling=ErrorHandlingConfig(**config_data.get("error_handling", {})),
            performance=PerformanceConfig(**config_data.get("performance", {})),
            ui_customization=UiCustomizationConfig(**config_data.get("ui_customization", {})),
            features=FeaturesConfig(**config_data.get("features", {})),
            notifications=NotificationsConfig(**config_data.get("notifications", {})),
            testing=TestingConfig(**config_data.get("testing", {})),
        )

    except yaml.YAMLError as e:
        msg = f"Invalid YAML in UI config: {e}"
        raise ValueError(msg)
    except TypeError as e:
        msg = f"Invalid UI configuration structure: {e}"
        raise ValueError(msg)


def update_ui_config_yaml(config_updates: dict[str, Any], config_path: str | Path | None = None) -> bool:
    """Update UI configuration YAML file with new values"""

    if config_path is None:
        config_path = Path(__file__).parent / "ui_config.yml"

    config_path = Path(config_path)

    if not config_path.exists():
        msg = f"UI config file not found: {config_path}"
        raise FileNotFoundError(msg)

    try:
        # Load current configuration
        with open(config_path, encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        if not isinstance(config_data, dict):
            raise ValueError("Config file must contain a YAML dictionary")

        # Create backup
        backup_path = config_path.with_suffix(".yml.backup")
        with open(backup_path, "w", encoding="utf-8") as f:
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
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config_data, f, default_flow_style=False, sort_keys=False)

        return True

    except Exception as e:
        msg = f"Failed to update UI configuration: {e}"
        raise ValueError(msg)


def reload_ui_config() -> UiConfig:
    """Reload UI configuration from file"""
    global UI_CONFIG
    UI_CONFIG = load_ui_config()
    return UI_CONFIG


def create_default_ui_config() -> dict[str, Any]:
    """Create default UI configuration for fallback"""

    return {
        "api_integration": {
            "websocket_url": "ws://localhost:8000",
            "rest_api_url": "http://localhost:8000",
            "health_check_endpoint": "/health",
            "transcription_endpoint": "/ws/transcription",
            "soap_generation_endpoint": "/generate-soap-from-session",
        },
        "developer": {
            "mode_enabled": True,
            "debug_logging": True,
            "test_users": ["justin", "jeff"],
            "default_test_user": "justin",
            "mock_transcription": False,
            "bypass_user_validation": True,
        },
        "action": {
            "id": "medical_transcription",
            "name": "🎙️ Medical Transcription",
            "description": "Start live medical transcription with automatic SOAP note generation",
            "icon": "🎙️",
            "category": "Healthcare",
            "button_text": "Start Medical Transcription",
        },
        "session": {
            "timeout_seconds": 300,
            "chunk_interval_seconds": 2,
            "auto_soap_generation": True,
            "session_cleanup_enabled": True,
        },
        "user_experience": {
            "show_real_time_transcription": True,
            "show_status_updates": True,
            "enable_progress_indicators": True,
            "auto_scroll_enabled": True,
        },
        "compliance": {
            "show_medical_disclaimer": True,
            "disclaimer_text": "⚠️ This system provides administrative transcription support only. It does not provide medical advice, diagnosis, or treatment recommendations. All clinical content must be reviewed by qualified healthcare professionals.",
            "phi_protection_enabled": True,
            "audit_logging_enabled": True,
            "healthcare_compliance_mode": True,
        },
        "events": {
            "emit_status_updates": True,
            "emit_transcription_chunks": True,
            "emit_session_events": True,
            "emit_error_notifications": True,
        },
        "error_handling": {
            "connection_retry_attempts": 3,
            "retry_delay_seconds": 2,
            "show_detailed_errors": True,
            "fallback_to_mock_on_failure": True,
        },
        "performance": {
            "debounce_events_ms": 100,
            "max_concurrent_sessions": 5,
            "memory_cleanup_interval_seconds": 30,
        },
        "ui_customization": {
            "primary_color": "#2563eb",
            "success_color": "#16a34a",
            "warning_color": "#d97706",
            "error_color": "#dc2626",
        },
        "features": {
            "enable_audio_visualization": True,
            "enable_session_history": True,
            "enable_export_functionality": True,
            "enable_real_time_editing": False,
        },
        "notifications": {
            "show_connection_status": True,
            "show_transcription_quality": True,
            "show_session_time_remaining": True,
            "auto_hide_success_messages": True,
            "message_display_duration_seconds": 5,
        },
        "testing": {
            "enable_test_mode": False,
            "mock_session_data": False,
            "validation_checks_enabled": True,
            "performance_monitoring": True,
        },
    }


# Global configuration instance
try:
    UI_CONFIG = load_ui_config()
except (FileNotFoundError, ValueError) as e:
    print(f"Warning: Could not load UI config ({e}), using defaults")
    default_config = create_default_ui_config()
    # Create UiConfig from default dict
    UI_CONFIG = UiConfig(
        api_integration=ApiIntegrationConfig(**default_config["api_integration"]),
        developer=DeveloperConfig(**default_config["developer"]),
        action=ActionConfig(**default_config["action"]),
        session=SessionConfig(**default_config["session"]),
        user_experience=UserExperienceConfig(**default_config["user_experience"]),
        compliance=ComplianceConfig(**default_config["compliance"]),
        events=EventsConfig(**default_config["events"]),
        error_handling=ErrorHandlingConfig(**default_config["error_handling"]),
        performance=PerformanceConfig(**default_config["performance"]),
        ui_customization=UiCustomizationConfig(**default_config["ui_customization"]),
        features=FeaturesConfig(**default_config["features"]),
        notifications=NotificationsConfig(**default_config["notifications"]),
        testing=TestingConfig(**default_config["testing"]),
    )
