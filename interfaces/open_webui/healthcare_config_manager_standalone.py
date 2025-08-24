"""
Healthcare Configuration Manager for Open WebUI (Standalone Version)
Provides a comprehensive interface for managing healthcare system configurations
"""

import logging
import os
import yaml
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path

from pydantic import BaseModel, Field


class Action:
    """
    Healthcare Configuration Manager

    Provides a comprehensive interface for managing healthcare system configurations
    including transcription settings, UI preferences, security settings, and more.
    This standalone version works without external dependencies.
    """

    class Valves(BaseModel):
        """Configuration sections for healthcare system management"""

        # === Access Control ===
        ADMIN_ONLY_MODE: bool = Field(
            default=True,
            description="🔒 Restrict configuration access to administrators only",
        )
        ADMIN_USERS: list[str] = Field(
            default=["admin", "justin", "jeff"],
            description="👥 List of users with configuration management access",
        )

        # === Transcription Service Configuration ===
        TRANSCRIPTION_WEBSOCKET_URL: str = Field(
            default=os.getenv('HEALTHCARE_WEBSOCKET_URL', 'ws://localhost:8000'),
            description="🌐 WebSocket URL for transcription service",
        )
        TRANSCRIPTION_TIMEOUT_SECONDS: int = Field(
            default=int(os.getenv('TRANSCRIPTION_TIMEOUT', '300')),
            ge=60,
            le=3600,
            description="⏰ Maximum transcription session duration (60-3600 seconds)",
        )
        TRANSCRIPTION_CHUNK_INTERVAL: int = Field(
            default=int(os.getenv('CHUNK_INTERVAL', '2')),
            ge=1,
            le=10,
            description="🎵 Audio chunk processing interval (1-10 seconds)",
        )
        DEFAULT_CONFIDENCE_THRESHOLD: float = Field(
            default=float(os.getenv('CONFIDENCE_THRESHOLD', '0.85')),
            ge=0.1,
            le=1.0,
            description="🎯 Default confidence threshold for transcription (0.1-1.0)",
        )
        HIGH_CONFIDENCE_THRESHOLD: float = Field(
            default=float(os.getenv('HIGH_CONFIDENCE_THRESHOLD', '0.92')),
            ge=0.1,
            le=1.0,
            description="⭐ High confidence threshold for medical terms (0.1-1.0)",
        )

        # === UI and Experience Configuration ===
        UI_WEBSOCKET_URL: str = Field(
            default=os.getenv('UI_WEBSOCKET_URL', 'ws://localhost:8000'),
            description="🌐 UI WebSocket connection URL",
        )
        UI_REST_API_URL: str = Field(
            default=os.getenv('UI_REST_API_URL', 'http://localhost:8000'),
            description="🔗 UI REST API connection URL",
        )
        DEVELOPER_MODE_ENABLED: bool = Field(
            default=os.getenv('DEVELOPER_MODE', 'true').lower() == 'true',
            description="🛠️ Enable developer mode with additional features",
        )
        DEBUG_LOGGING_ENABLED: bool = Field(
            default=os.getenv('DEBUG_LOGGING', 'false').lower() == 'true',
            description="📝 Enable detailed debug logging",
        )
        MOCK_TRANSCRIPTION_MODE: bool = Field(
            default=os.getenv('MOCK_TRANSCRIPTION', 'false').lower() == 'true',
            description="🎭 Use mock transcription for testing",
        )

        # === Medical Compliance ===
        SHOW_MEDICAL_DISCLAIMER: bool = Field(
            default=os.getenv('SHOW_MEDICAL_DISCLAIMER', 'true').lower() == 'true',
            description="⚠️ Display medical disclaimer to users",
        )
        PHI_PROTECTION_ENABLED: bool = Field(
            default=os.getenv('PHI_PROTECTION_ENABLED', 'true').lower() == 'true',
            description="🔒 Enable PHI (Protected Health Information) protection",
        )
        HEALTHCARE_COMPLIANCE_MODE: bool = Field(
            default=os.getenv('HEALTHCARE_COMPLIANCE_MODE', 'true').lower() == 'true',
            description="⚖️ Enable strict healthcare compliance mode",
        )
        AUDIT_LOGGING_ENABLED: bool = Field(
            default=os.getenv('AUDIT_LOGGING_ENABLED', 'true').lower() == 'true',
            description="📋 Enable comprehensive audit logging",
        )
        MEDICAL_DISCLAIMER_TEXT: str = Field(
            default=os.getenv('MEDICAL_DISCLAIMER_TEXT', 
                            "This system provides administrative support only, not medical advice. "
                            "Always consult healthcare professionals for medical decisions."),
            description="📝 Custom medical disclaimer text",
        )

        # === Performance & Limits ===
        MAX_CONCURRENT_SESSIONS: int = Field(
            default=int(os.getenv('MAX_CONCURRENT_SESSIONS', '10')),
            ge=1,
            le=50,
            description="👥 Maximum concurrent transcription sessions per user (1-50)",
        )
        CONNECTION_RETRY_ATTEMPTS: int = Field(
            default=int(os.getenv('CONNECTION_RETRY_ATTEMPTS', '3')),
            ge=1,
            le=10,
            description="🔄 Connection retry attempts (1-10)",
        )
        RETRY_DELAY_SECONDS: int = Field(
            default=int(os.getenv('RETRY_DELAY_SECONDS', '5')),
            ge=1,
            le=30,
            description="⏱️ Delay between retry attempts (1-30 seconds)",
        )

        # === Features ===
        AUTO_SOAP_GENERATION: bool = Field(
            default=os.getenv('AUTO_SOAP_GENERATION', 'true').lower() == 'true',
            description="📋 Automatically generate SOAP notes from transcriptions",
        )
        REAL_TIME_TRANSCRIPTION_DISPLAY: bool = Field(
            default=os.getenv('REAL_TIME_TRANSCRIPTION_DISPLAY', 'true').lower() == 'true',
            description="🔄 Show transcription results in real-time",
        )
        STATUS_UPDATES_ENABLED: bool = Field(
            default=os.getenv('STATUS_UPDATES_ENABLED', 'true').lower() == 'true',
            description="📊 Show status updates during transcription",
        )

        # === Configuration File Paths ===
        CONFIG_BASE_PATH: str = Field(
            default=os.getenv('HEALTHCARE_CONFIG_PATH', '/home/intelluxe/services/user/healthcare-api/config'),
            description="📁 Base path for healthcare configuration files",
        )

    def __init__(self):
        self.valves = self.Valves()
        self._setup_logging()

    def _setup_logging(self):
        """Setup logging configuration."""
        log_level = logging.DEBUG if self.valves.DEBUG_LOGGING_ENABLED else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def _check_admin_access(self, user_id: str = None) -> bool:
        """Check if user has admin access."""
        if not self.valves.ADMIN_ONLY_MODE:
            return True
        
        # In Open WebUI, user detection might be limited
        # Default to allowing access if user can't be determined
        if not user_id:
            self.logger.warning("User ID not available, defaulting to admin access")
            return True
            
        return user_id in self.valves.ADMIN_USERS

    def _get_configuration_summary(self) -> Dict[str, Any]:
        """Generate current configuration summary."""
        return {
            "transcription": {
                "websocket_url": self.valves.TRANSCRIPTION_WEBSOCKET_URL,
                "timeout_seconds": self.valves.TRANSCRIPTION_TIMEOUT_SECONDS,
                "chunk_interval": self.valves.TRANSCRIPTION_CHUNK_INTERVAL,
                "confidence_threshold": self.valves.DEFAULT_CONFIDENCE_THRESHOLD,
                "high_confidence_threshold": self.valves.HIGH_CONFIDENCE_THRESHOLD,
            },
            "ui_integration": {
                "websocket_url": self.valves.UI_WEBSOCKET_URL,
                "rest_api_url": self.valves.UI_REST_API_URL,
                "developer_mode": self.valves.DEVELOPER_MODE_ENABLED,
                "mock_transcription": self.valves.MOCK_TRANSCRIPTION_MODE,
            },
            "compliance": {
                "show_disclaimer": self.valves.SHOW_MEDICAL_DISCLAIMER,
                "phi_protection": self.valves.PHI_PROTECTION_ENABLED,
                "compliance_mode": self.valves.HEALTHCARE_COMPLIANCE_MODE,
                "audit_logging": self.valves.AUDIT_LOGGING_ENABLED,
            },
            "performance": {
                "max_concurrent_sessions": self.valves.MAX_CONCURRENT_SESSIONS,
                "retry_attempts": self.valves.CONNECTION_RETRY_ATTEMPTS,
                "retry_delay": self.valves.RETRY_DELAY_SECONDS,
            },
            "features": {
                "auto_soap_generation": self.valves.AUTO_SOAP_GENERATION,
                "real_time_display": self.valves.REAL_TIME_TRANSCRIPTION_DISPLAY,
                "status_updates": self.valves.STATUS_UPDATES_ENABLED,
            }
        }

    def _save_configuration_to_yaml(self, config_data: Dict[str, Any]) -> bool:
        """Attempt to save configuration to YAML files if accessible."""
        try:
            config_base = Path(self.valves.CONFIG_BASE_PATH)
            
            # Try to save transcription config
            transcription_config_path = config_base / "transcription_config.yml"
            if transcription_config_path.parent.exists():
                transcription_config = {
                    "websocket": {
                        "base_url": config_data["transcription"]["websocket_url"],
                        "connection_timeout_seconds": 30,
                    },
                    "session": {
                        "default_timeout_seconds": config_data["transcription"]["timeout_seconds"],
                        "audio_chunk_interval_seconds": config_data["transcription"]["chunk_interval"],
                        "max_concurrent_sessions": config_data["performance"]["max_concurrent_sessions"],
                    },
                    "quality": {
                        "default_confidence_threshold": config_data["transcription"]["confidence_threshold"],
                        "high_confidence_threshold": config_data["transcription"]["high_confidence_threshold"],
                    }
                }
                
                with open(transcription_config_path, 'w') as f:
                    yaml.dump(transcription_config, f, default_flow_style=False)
                
                self.logger.info(f"Saved transcription config to {transcription_config_path}")
            
            # Try to save UI config
            ui_config_path = config_base / "ui_config.yml"
            if ui_config_path.parent.exists():
                ui_config = {
                    "api_integration": {
                        "websocket_url": config_data["ui_integration"]["websocket_url"],
                        "rest_api_url": config_data["ui_integration"]["rest_api_url"],
                    },
                    "developer": {
                        "mode_enabled": config_data["ui_integration"]["developer_mode"],
                        "debug_logging": self.valves.DEBUG_LOGGING_ENABLED,
                        "mock_transcription": config_data["ui_integration"]["mock_transcription"],
                        "test_users": self.valves.ADMIN_USERS,
                        "default_test_user": self.valves.ADMIN_USERS[0] if self.valves.ADMIN_USERS else "admin",
                    },
                    "compliance": {
                        "show_medical_disclaimer": config_data["compliance"]["show_disclaimer"],
                        "phi_protection_enabled": config_data["compliance"]["phi_protection"],
                        "healthcare_compliance_mode": config_data["compliance"]["compliance_mode"],
                        "disclaimer_text": self.valves.MEDICAL_DISCLAIMER_TEXT,
                    }
                }
                
                with open(ui_config_path, 'w') as f:
                    yaml.dump(ui_config, f, default_flow_style=False)
                
                self.logger.info(f"Saved UI config to {ui_config_path}")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save configuration to YAML: {e}")
            return False

    async def action(
        self,
        body: dict,
        __user__: Optional[dict] = None,
        __event_emitter__=None,
    ) -> Optional[dict]:
        """
        Main action handler for configuration management.
        
        Args:
            body: The request body from Open WebUI
            __user__: User information (if available)
            __event_emitter__: Event emitter for real-time updates
        """
        try:
            user_id = __user__.get("email", "unknown") if __user__ else "unknown"
            
            # Check admin access
            if not self._check_admin_access(user_id):
                return {
                    "error": "❌ Access denied. Administrator privileges required for configuration management.",
                    "user_id": user_id,
                    "admin_users": self.valves.ADMIN_USERS
                }
            
            # Get current configuration
            current_config = self._get_configuration_summary()
            
            # Attempt to save configuration to files
            save_success = self._save_configuration_to_yaml(current_config)
            
            # Generate response
            response = {
                "title": "⚙️ Healthcare Configuration Manager",
                "user": user_id,
                "timestamp": datetime.now().isoformat(),
                "config_saved_to_files": save_success,
                "current_configuration": current_config,
                "instructions": {
                    "modify_settings": "Update settings through the function's Valves in Open WebUI settings",
                    "save_changes": "Changes are automatically applied when you modify valve values",
                    "yaml_persistence": "Configuration files will be updated if accessible" if save_success 
                                       else "YAML files not accessible - using environment variables only",
                    "testing": {
                        "mock_mode": "Enable MOCK_TRANSCRIPTION_MODE for testing without real audio",
                        "developer_mode": "Enable DEVELOPER_MODE_ENABLED for additional features",
                        "debug_logging": "Enable DEBUG_LOGGING_ENABLED for detailed logs"
                    }
                },
                "environment_variables": {
                    "note": "You can also configure these settings using environment variables:",
                    "variables": {
                        "HEALTHCARE_WEBSOCKET_URL": "WebSocket URL for transcription service",
                        "TRANSCRIPTION_TIMEOUT": "Session timeout in seconds",
                        "DEVELOPER_MODE": "Enable developer features (true/false)",
                        "PHI_PROTECTION_ENABLED": "Enable PHI protection (true/false)",
                        "MAX_CONCURRENT_SESSIONS": "Maximum concurrent sessions per user"
                    }
                }
            }
            
            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": "Configuration loaded successfully"}
                })
            
            return response
            
        except Exception as e:
            error_msg = f"Configuration management error: {str(e)}"
            self.logger.error(error_msg)
            
            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": f"Error: {error_msg}"}
                })
            
            return {
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            }