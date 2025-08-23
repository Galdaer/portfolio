"""
Healthcare Configuration Manager for Open WebUI
Provides a comprehensive interface for managing all healthcare system configurations
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# Add the healthcare-api config path for config loading
sys.path.append('/home/intelluxe/services/user/healthcare-api')
from config.ui_config_loader import UI_CONFIG, update_ui_config_yaml, reload_ui_config
from config.transcription_config_loader import TRANSCRIPTION_CONFIG, update_transcription_config_yaml, reload_transcription_config


class Action:
    """
    Healthcare Configuration Manager
    
    Provides a comprehensive interface for managing healthcare system configurations
    including transcription settings, UI preferences, security settings, and more.
    """
    
    class Valves(BaseModel):
        """Configuration sections for healthcare system management"""
        
        # === Access Control ===
        ADMIN_ONLY_MODE: bool = Field(
            default=True,
            description="🔒 Restrict configuration access to administrators only"
        )
        ADMIN_USERS: List[str] = Field(
            default=["admin", "justin", "jeff"],
            description="👥 List of users with configuration management access"
        )
        
        # === Transcription Service Configuration ===
        TRANSCRIPTION_WEBSOCKET_URL: str = Field(
            default=TRANSCRIPTION_CONFIG.websocket.base_url,
            description="🌐 WebSocket URL for transcription service"
        )
        TRANSCRIPTION_TIMEOUT_SECONDS: int = Field(
            default=TRANSCRIPTION_CONFIG.session.default_timeout_seconds,
            ge=60,
            le=3600,
            description="⏰ Maximum transcription session duration (60-3600 seconds)"
        )
        TRANSCRIPTION_CHUNK_INTERVAL: int = Field(
            default=TRANSCRIPTION_CONFIG.session.audio_chunk_interval_seconds,
            ge=1,
            le=10,
            description="🎵 Audio chunk processing interval (1-10 seconds)"
        )
        DEFAULT_CONFIDENCE_THRESHOLD: float = Field(
            default=TRANSCRIPTION_CONFIG.quality.default_confidence_threshold,
            ge=0.1,
            le=1.0,
            description="🎯 Default confidence threshold for transcription (0.1-1.0)"
        )
        HIGH_CONFIDENCE_THRESHOLD: float = Field(
            default=TRANSCRIPTION_CONFIG.quality.high_confidence_threshold,
            ge=0.1,
            le=1.0,
            description="⭐ High confidence threshold for medical terms (0.1-1.0)"
        )
        
        # === UI and Experience Configuration ===
        UI_WEBSOCKET_URL: str = Field(
            default=UI_CONFIG.api_integration.websocket_url,
            description="🌐 UI WebSocket connection URL"
        )
        UI_REST_API_URL: str = Field(
            default=UI_CONFIG.api_integration.rest_api_url,
            description="🔗 UI REST API connection URL"
        )
        DEVELOPER_MODE_ENABLED: bool = Field(
            default=UI_CONFIG.developer.mode_enabled,
            description="🛠️ Enable developer mode with additional features"
        )
        DEBUG_LOGGING_ENABLED: bool = Field(
            default=UI_CONFIG.developer.debug_logging,
            description="📝 Enable detailed debug logging"
        )
        MOCK_TRANSCRIPTION_MODE: bool = Field(
            default=UI_CONFIG.developer.mock_transcription,
            description="🎭 Use mock transcription for testing"
        )
        
        # === Medical Compliance ===
        SHOW_MEDICAL_DISCLAIMER: bool = Field(
            default=UI_CONFIG.compliance.show_medical_disclaimer,
            description="⚠️ Display medical disclaimer to users"
        )
        PHI_PROTECTION_ENABLED: bool = Field(
            default=UI_CONFIG.compliance.phi_protection_enabled,
            description="🛡️ Enable PHI (Protected Health Information) protection"
        )
        HEALTHCARE_COMPLIANCE_MODE: bool = Field(
            default=UI_CONFIG.compliance.healthcare_compliance_mode,
            description="🏥 Enable strict healthcare compliance mode"
        )
        AUDIT_LOGGING_ENABLED: bool = Field(
            default=UI_CONFIG.compliance.audit_logging_enabled,
            description="📋 Enable audit logging for compliance tracking"
        )
        
        # === Performance and Limits ===
        MAX_CONCURRENT_SESSIONS: int = Field(
            default=UI_CONFIG.performance.max_concurrent_sessions,
            ge=1,
            le=50,
            description="⚡ Maximum concurrent sessions per user (1-50)"
        )
        CONNECTION_RETRY_ATTEMPTS: int = Field(
            default=UI_CONFIG.error_handling.connection_retry_attempts,
            ge=1,
            le=10,
            description="🔄 Connection retry attempts on failure (1-10)"
        )
        RETRY_DELAY_SECONDS: int = Field(
            default=UI_CONFIG.error_handling.retry_delay_seconds,
            ge=1,
            le=30,
            description="⏱️ Delay between retry attempts (1-30 seconds)"
        )
        
        # === Feature Flags ===
        AUTO_SOAP_GENERATION: bool = Field(
            default=UI_CONFIG.session.auto_soap_generation,
            description="📄 Automatically generate SOAP notes from transcriptions"
        )
        REAL_TIME_TRANSCRIPTION_DISPLAY: bool = Field(
            default=UI_CONFIG.user_experience.show_real_time_transcription,
            description="⚡ Show transcription results in real-time"
        )
        STATUS_UPDATES_ENABLED: bool = Field(
            default=UI_CONFIG.user_experience.show_status_updates,
            description="📢 Show status updates during operations"
        )
        AUDIO_VISUALIZATION_ENABLED: bool = Field(
            default=UI_CONFIG.features.enable_audio_visualization,
            description="🎵 Enable audio visualization features"
        )
        SESSION_HISTORY_ENABLED: bool = Field(
            default=UI_CONFIG.features.enable_session_history,
            description="📚 Enable session history tracking"
        )
        
        # === Medical Disclaimer Text ===
        MEDICAL_DISCLAIMER_TEXT: str = Field(
            default=UI_CONFIG.compliance.disclaimer_text,
            description="⚠️ Medical disclaimer text shown to users"
        )

    def __init__(self):
        self.id = "healthcare_config_manager"
        self.name = "⚙️ Healthcare Configuration Manager"
        self.description = "Comprehensive configuration management for the healthcare AI system"
        self.valves = self.Valves()
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    async def action(
        self, 
        body: Dict[str, Any], 
        __user__: Optional[Dict] = None, 
        __event_emitter__=None
    ) -> Dict[str, Any]:
        """
        Healthcare Configuration Management Interface
        """
        try:
            # Extract user information for access control
            user_id = self.extract_user_id(__user__, body)
            
            # Check access permissions
            if not self.check_admin_access(user_id):
                return {
                    "success": False,
                    "message": "❌ Access denied. Administrator privileges required for configuration management.",
                    "error": "Insufficient permissions"
                }
            
            await self.emit_status(
                f"🔧 Starting healthcare configuration management session for {user_id}",
                __event_emitter__
            )
            
            # Show current configuration summary
            config_summary = await self.get_configuration_summary()
            
            await self.emit_status(
                "📋 Current Configuration Summary:",
                __event_emitter__,
                {"config_summary": config_summary}
            )
            
            # Show configuration management options
            management_options = self.get_management_options()
            
            await self.emit_status(
                "⚙️ Configuration management interface ready",
                __event_emitter__,
                {"management_options": management_options}
            )
            
            return {
                "success": True,
                "message": "✅ Healthcare Configuration Manager ready",
                "data": {
                    "user_id": user_id,
                    "access_level": "administrator",
                    "current_config": config_summary,
                    "management_options": management_options,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            self.logger.error(f"Configuration manager error: {e}")
            return {
                "success": False,
                "message": f"❌ Configuration manager error: {str(e)}",
                "error": str(e)
            }

    def extract_user_id(self, __user__: Optional[Dict], body: Dict[str, Any]) -> Optional[str]:
        """Extract user ID from various possible sources"""
        
        user_candidates = []
        
        # Try user object attributes
        if __user__:
            if isinstance(__user__, dict):
                user_candidates.extend([
                    __user__.get('id'),
                    __user__.get('username'), 
                    __user__.get('email'),
                    __user__.get('name')
                ])
            else:
                # Try object attributes
                for attr in ['id', 'username', 'email', 'name']:
                    if hasattr(__user__, attr):
                        user_candidates.append(getattr(__user__, attr))
        
        # Try body user information
        if 'user' in body:
            user_info = body['user']
            if isinstance(user_info, dict):
                user_candidates.extend([
                    user_info.get('id'),
                    user_info.get('username'),
                    user_info.get('email'),
                    user_info.get('name')
                ])
        
        # Return first valid candidate
        for candidate in user_candidates:
            if candidate and str(candidate).strip() and candidate != 'unknown':
                return str(candidate).lower()
        
        return "unknown"

    def check_admin_access(self, user_id: str) -> bool:
        """Check if user has administrator access for configuration management"""
        
        if not self.valves.ADMIN_ONLY_MODE:
            return True  # Open access mode
        
        if not user_id or user_id == "unknown":
            return False  # Unknown users denied
        
        # Check admin users list
        admin_users = [user.lower() for user in self.valves.ADMIN_USERS]
        return user_id.lower() in admin_users

    async def get_configuration_summary(self) -> Dict[str, Any]:
        """Get summary of current configuration"""
        
        return {
            "transcription_service": {
                "websocket_url": TRANSCRIPTION_CONFIG.websocket.base_url,
                "session_timeout": f"{TRANSCRIPTION_CONFIG.session.default_timeout_seconds}s",
                "chunk_interval": f"{TRANSCRIPTION_CONFIG.session.audio_chunk_interval_seconds}s",
                "confidence_threshold": TRANSCRIPTION_CONFIG.quality.default_confidence_threshold,
                "max_sessions": TRANSCRIPTION_CONFIG.session.max_concurrent_sessions
            },
            "ui_integration": {
                "websocket_url": UI_CONFIG.api_integration.websocket_url,
                "rest_api_url": UI_CONFIG.api_integration.rest_api_url,
                "developer_mode": UI_CONFIG.developer.mode_enabled,
                "debug_logging": UI_CONFIG.developer.debug_logging,
                "mock_transcription": UI_CONFIG.developer.mock_transcription
            },
            "compliance": {
                "phi_protection": UI_CONFIG.compliance.phi_protection_enabled,
                "healthcare_compliance": UI_CONFIG.compliance.healthcare_compliance_mode,
                "audit_logging": UI_CONFIG.compliance.audit_logging_enabled,
                "show_disclaimer": UI_CONFIG.compliance.show_medical_disclaimer
            },
            "features": {
                "auto_soap_generation": UI_CONFIG.session.auto_soap_generation,
                "real_time_display": UI_CONFIG.user_experience.show_real_time_transcription,
                "audio_visualization": UI_CONFIG.features.enable_audio_visualization,
                "session_history": UI_CONFIG.features.enable_session_history
            }
        }

    def get_management_options(self) -> Dict[str, Any]:
        """Get available configuration management options"""
        
        return {
            "sections": [
                {
                    "name": "Transcription Service",
                    "description": "Core transcription engine settings",
                    "fields": [
                        "TRANSCRIPTION_WEBSOCKET_URL",
                        "TRANSCRIPTION_TIMEOUT_SECONDS", 
                        "TRANSCRIPTION_CHUNK_INTERVAL",
                        "DEFAULT_CONFIDENCE_THRESHOLD",
                        "HIGH_CONFIDENCE_THRESHOLD"
                    ]
                },
                {
                    "name": "UI Integration",
                    "description": "User interface and connection settings",
                    "fields": [
                        "UI_WEBSOCKET_URL",
                        "UI_REST_API_URL",
                        "DEVELOPER_MODE_ENABLED",
                        "DEBUG_LOGGING_ENABLED",
                        "MOCK_TRANSCRIPTION_MODE"
                    ]
                },
                {
                    "name": "Medical Compliance",
                    "description": "Healthcare compliance and safety features",
                    "fields": [
                        "SHOW_MEDICAL_DISCLAIMER",
                        "PHI_PROTECTION_ENABLED",
                        "HEALTHCARE_COMPLIANCE_MODE",
                        "AUDIT_LOGGING_ENABLED",
                        "MEDICAL_DISCLAIMER_TEXT"
                    ]
                },
                {
                    "name": "Performance & Limits",
                    "description": "System performance and connection limits",
                    "fields": [
                        "MAX_CONCURRENT_SESSIONS",
                        "CONNECTION_RETRY_ATTEMPTS",
                        "RETRY_DELAY_SECONDS"
                    ]
                },
                {
                    "name": "Features",
                    "description": "Feature flags and user experience settings",
                    "fields": [
                        "AUTO_SOAP_GENERATION",
                        "REAL_TIME_TRANSCRIPTION_DISPLAY",
                        "STATUS_UPDATES_ENABLED",
                        "AUDIO_VISUALIZATION_ENABLED",
                        "SESSION_HISTORY_ENABLED"
                    ]
                }
            ],
            "actions": [
                "📋 View current configuration",
                "💾 Save configuration changes",
                "🔄 Reload configuration from files",
                "📁 Backup current configuration",
                "↩️ Restore from backup",
                "🧪 Test configuration changes",
                "🔍 Validate configuration"
            ]
        }

    async def apply_configuration_changes(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        """Apply configuration changes to YAML files"""
        
        try:
            results = {"success": True, "changes_applied": [], "errors": []}
            
            # Map changes to configuration files
            transcription_changes = {}
            ui_changes = {}
            
            # Map valve fields to configuration structures
            transcription_field_map = {
                'TRANSCRIPTION_WEBSOCKET_URL': ('websocket', 'base_url'),
                'TRANSCRIPTION_TIMEOUT_SECONDS': ('session', 'default_timeout_seconds'),
                'TRANSCRIPTION_CHUNK_INTERVAL': ('session', 'audio_chunk_interval_seconds'),
                'DEFAULT_CONFIDENCE_THRESHOLD': ('quality', 'default_confidence_threshold'),
                'HIGH_CONFIDENCE_THRESHOLD': ('quality', 'high_confidence_threshold'),
            }
            
            ui_field_map = {
                'UI_WEBSOCKET_URL': ('api_integration', 'websocket_url'),
                'UI_REST_API_URL': ('api_integration', 'rest_api_url'),
                'DEVELOPER_MODE_ENABLED': ('developer', 'mode_enabled'),
                'DEBUG_LOGGING_ENABLED': ('developer', 'debug_logging'),
                'MOCK_TRANSCRIPTION_MODE': ('developer', 'mock_transcription'),
                'SHOW_MEDICAL_DISCLAIMER': ('compliance', 'show_medical_disclaimer'),
                'PHI_PROTECTION_ENABLED': ('compliance', 'phi_protection_enabled'),
                'HEALTHCARE_COMPLIANCE_MODE': ('compliance', 'healthcare_compliance_mode'),
                'AUDIT_LOGGING_ENABLED': ('compliance', 'audit_logging_enabled'),
                'MAX_CONCURRENT_SESSIONS': ('performance', 'max_concurrent_sessions'),
                'CONNECTION_RETRY_ATTEMPTS': ('error_handling', 'connection_retry_attempts'),
                'RETRY_DELAY_SECONDS': ('error_handling', 'retry_delay_seconds'),
                'AUTO_SOAP_GENERATION': ('session', 'auto_soap_generation'),
                'REAL_TIME_TRANSCRIPTION_DISPLAY': ('user_experience', 'show_real_time_transcription'),
                'STATUS_UPDATES_ENABLED': ('user_experience', 'show_status_updates'),
                'AUDIO_VISUALIZATION_ENABLED': ('features', 'enable_audio_visualization'),
                'SESSION_HISTORY_ENABLED': ('features', 'enable_session_history'),
                'MEDICAL_DISCLAIMER_TEXT': ('compliance', 'disclaimer_text'),
            }
            
            # Organize changes by configuration file
            for field, value in changes.items():
                if field in transcription_field_map:
                    section, key = transcription_field_map[field]
                    if section not in transcription_changes:
                        transcription_changes[section] = {}
                    transcription_changes[section][key] = value
                    
                elif field in ui_field_map:
                    section, key = ui_field_map[field]
                    if section not in ui_changes:
                        ui_changes[section] = {}
                    ui_changes[section][key] = value
            
            # Apply transcription configuration changes
            if transcription_changes:
                try:
                    update_transcription_config_yaml(transcription_changes)
                    reload_transcription_config()
                    results["changes_applied"].extend(list(transcription_changes.keys()))
                except Exception as e:
                    results["errors"].append(f"Transcription config update failed: {str(e)}")
                    results["success"] = False
            
            # Apply UI configuration changes
            if ui_changes:
                try:
                    update_ui_config_yaml(ui_changes)
                    reload_ui_config()
                    results["changes_applied"].extend(list(ui_changes.keys()))
                except Exception as e:
                    results["errors"].append(f"UI config update failed: {str(e)}")
                    results["success"] = False
            
            return results
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Configuration update failed: {str(e)}",
                "changes_applied": [],
                "errors": [str(e)]
            }

    async def emit_status(
        self, 
        message: str, 
        __event_emitter__, 
        data: Dict[str, Any] = None
    ):
        """Emit status message to Open WebUI interface"""
        
        if __event_emitter__:
            await __event_emitter__({
                "type": "status",
                "data": {
                    "message": message,
                    "timestamp": datetime.now().isoformat(),
                    **(data or {})
                }
            })
        
        self.logger.info(f"Config Manager: {message}")

    def get_action_metadata(self) -> Dict[str, Any]:
        """Return metadata about this configuration manager"""
        
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": "⚙️",
            "category": "Healthcare Administration",
            "admin_only": self.valves.ADMIN_ONLY_MODE,
            "supported_users": self.valves.ADMIN_USERS if self.valves.ADMIN_ONLY_MODE else "all",
            "healthcare_compliance": True,
            "configuration_management": True,
            "backup_restore": True
        }