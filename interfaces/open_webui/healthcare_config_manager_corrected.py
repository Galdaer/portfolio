"""
title: Healthcare Configuration Manager
author: Intelluxe AI
version: 2.0.0
license: MIT
description: Comprehensive healthcare system configuration manager for Open WebUI
"""

import contextlib
import os
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Action:
    """
    Healthcare Configuration Manager

    Provides comprehensive healthcare system configuration management
    through Open WebUI with environment variable-based configuration.
    """

    class Valves(BaseModel):
        """Healthcare System Configuration Options"""

        # === Access Control ===
        admin_only_mode: bool = Field(
            default=True,
            description="🔒 Restrict configuration access to administrators only",
        )
        admin_users: list[str] = Field(
            default=["admin", "justin", "jeff"],
            description="👥 List of users with configuration management access",
        )

        # === Healthcare API Configuration ===
        healthcare_websocket_url: str = Field(
            default="ws://localhost:8000",
            description="🌐 Healthcare API WebSocket URL",
        )
        healthcare_rest_url: str = Field(
            default="http://localhost:8000",
            description="🔗 Healthcare API REST URL",
        )

        # === Transcription Settings ===
        transcription_timeout: int = Field(
            default=300,
            ge=60,
            le=3600,
            description="⏰ Transcription timeout in seconds (60-3600)",
        )
        chunk_interval: int = Field(
            default=2,
            ge=1,
            le=10,
            description="🎵 Audio chunk interval in seconds (1-10)",
        )
        confidence_threshold: float = Field(
            default=0.85,
            ge=0.1,
            le=1.0,
            description="🎯 Transcription confidence threshold (0.1-1.0)",
        )

        # === Compliance & Security ===
        phi_protection_enabled: bool = Field(
            default=True,
            description="🔒 Enable PHI (Protected Health Information) protection",
        )
        show_medical_disclaimer: bool = Field(
            default=True,
            description="⚠️ Display medical disclaimer to users",
        )
        audit_logging_enabled: bool = Field(
            default=True,
            description="📋 Enable comprehensive audit logging",
        )

        # === Developer Settings ===
        developer_mode: bool = Field(
            default=False,
            description="🛠️ Enable developer mode with additional features",
        )
        debug_logging: bool = Field(
            default=False,
            description="📝 Enable detailed debug logging",
        )
        mock_transcription: bool = Field(
            default=False,
            description="🎭 Use mock transcription for testing",
        )

        # === Performance Settings ===
        max_concurrent_sessions: int = Field(
            default=10,
            ge=1,
            le=50,
            description="👥 Maximum concurrent sessions per user (1-50)",
        )
        connection_retry_attempts: int = Field(
            default=3,
            ge=1,
            le=10,
            description="🔄 Connection retry attempts (1-10)",
        )

        # === Feature Toggles ===
        auto_soap_generation: bool = Field(
            default=True,
            description="📋 Automatically generate SOAP notes",
        )
        real_time_transcription: bool = Field(
            default=True,
            description="🔄 Show real-time transcription updates",
        )

    def __init__(self):
        """Initialize the configuration manager"""
        self.valves = self.Valves()

        # Load environment variables if available
        self._load_from_environment()

    def _load_from_environment(self):
        """Load configuration from environment variables"""
        env_mappings = {
            "healthcare_websocket_url": "HEALTHCARE_WEBSOCKET_URL",
            "healthcare_rest_url": "HEALTHCARE_REST_URL",
            "transcription_timeout": "TRANSCRIPTION_TIMEOUT",
            "chunk_interval": "CHUNK_INTERVAL",
            "confidence_threshold": "CONFIDENCE_THRESHOLD",
            "phi_protection_enabled": "PHI_PROTECTION_ENABLED",
            "developer_mode": "DEVELOPER_MODE",
            "debug_logging": "DEBUG_LOGGING",
            "mock_transcription": "MOCK_TRANSCRIPTION",
        }

        for valve_name, env_var in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                # Convert string to appropriate type
                current_value = getattr(self.valves, valve_name)
                if isinstance(current_value, bool):
                    setattr(self.valves, valve_name, env_value.lower() in ["true", "1", "yes"])
                elif isinstance(current_value, int):
                    with contextlib.suppress(ValueError):
                        setattr(self.valves, valve_name, int(env_value))
                elif isinstance(current_value, float):
                    with contextlib.suppress(ValueError):
                        setattr(self.valves, valve_name, float(env_value))
                else:
                    setattr(self.valves, valve_name, env_value)

    def _check_admin_access(self, user: dict | None = None) -> bool:
        """Check if user has administrative access"""
        if not self.valves.admin_only_mode:
            return True

        if not user:
            # Default to admin access if user can't be determined
            return True

        user_id = user.get("email", user.get("name", "unknown"))
        return user_id in self.valves.admin_users

    def _get_configuration_summary(self) -> dict[str, Any]:
        """Generate a summary of current configuration"""
        return {
            "system_info": {
                "timestamp": datetime.now().isoformat(),
                "admin_mode": self.valves.admin_only_mode,
                "admin_users": self.valves.admin_users,
            },
            "healthcare_api": {
                "websocket_url": self.valves.healthcare_websocket_url,
                "rest_url": self.valves.healthcare_rest_url,
            },
            "transcription": {
                "timeout_seconds": self.valves.transcription_timeout,
                "chunk_interval": self.valves.chunk_interval,
                "confidence_threshold": self.valves.confidence_threshold,
            },
            "compliance": {
                "phi_protection": self.valves.phi_protection_enabled,
                "medical_disclaimer": self.valves.show_medical_disclaimer,
                "audit_logging": self.valves.audit_logging_enabled,
            },
            "developer": {
                "developer_mode": self.valves.developer_mode,
                "debug_logging": self.valves.debug_logging,
                "mock_transcription": self.valves.mock_transcription,
            },
            "performance": {
                "max_concurrent_sessions": self.valves.max_concurrent_sessions,
                "connection_retry_attempts": self.valves.connection_retry_attempts,
            },
            "features": {
                "auto_soap_generation": self.valves.auto_soap_generation,
                "real_time_transcription": self.valves.real_time_transcription,
            },
        }

    def _generate_environment_variables(self) -> dict[str, str]:
        """Generate environment variable export commands"""
        return {
            "HEALTHCARE_WEBSOCKET_URL": self.valves.healthcare_websocket_url,
            "HEALTHCARE_REST_URL": self.valves.healthcare_rest_url,
            "TRANSCRIPTION_TIMEOUT": str(self.valves.transcription_timeout),
            "CHUNK_INTERVAL": str(self.valves.chunk_interval),
            "CONFIDENCE_THRESHOLD": str(self.valves.confidence_threshold),
            "PHI_PROTECTION_ENABLED": str(self.valves.phi_protection_enabled).lower(),
            "DEVELOPER_MODE": str(self.valves.developer_mode).lower(),
            "DEBUG_LOGGING": str(self.valves.debug_logging).lower(),
            "MOCK_TRANSCRIPTION": str(self.valves.mock_transcription).lower(),
            "MAX_CONCURRENT_SESSIONS": str(self.valves.max_concurrent_sessions),
        }

    async def action(
        self,
        body: dict,
        __user__: dict | None = None,
        __event_emitter__=None,
    ) -> dict | None:
        """
        Execute the configuration management action

        Args:
            body: Request body from Open WebUI
            __user__: User information
            __event_emitter__: Event emitter for real-time updates

        Returns:
            dict: Configuration summary and management options
        """
        try:
            # Get user information
            user_name = __user__.get("name", "Unknown") if __user__ else "Unknown"
            user_email = __user__.get("email", "") if __user__ else ""

            # Emit initial status
            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": "Loading healthcare configuration..."},
                })

            # Check admin access
            has_admin_access = self._check_admin_access(__user__)

            if not has_admin_access:
                return {
                    "content": f"""
## ❌ Access Denied

**User**: {user_name} ({user_email})
**Status**: Administrator privileges required

### Admin Users
{', '.join(self.valves.admin_users)}

### Grant Access
To grant access, modify the `admin_users` valve in this function's settings.
                    """.strip(),
                }

            # Generate configuration summary
            config_summary = self._get_configuration_summary()
            env_vars = self._generate_environment_variables()

            # Emit processing status
            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": "Generating configuration report..."},
                })

            # Build response
            response_content = f"""
## ⚙️ Healthcare Configuration Manager

**Administrator**: {user_name} ({user_email})
**Timestamp**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

### 🏥 Healthcare API Configuration
- **WebSocket URL**: `{config_summary['healthcare_api']['websocket_url']}`
- **REST API URL**: `{config_summary['healthcare_api']['rest_url']}`

### 🎙️ Transcription Settings
- **Timeout**: {config_summary['transcription']['timeout_seconds']} seconds
- **Chunk Interval**: {config_summary['transcription']['chunk_interval']} seconds
- **Confidence Threshold**: {config_summary['transcription']['confidence_threshold']:.2f}

### 🔒 Compliance & Security
- **PHI Protection**: {'✅ Enabled' if config_summary['compliance']['phi_protection'] else '❌ Disabled'}
- **Medical Disclaimer**: {'✅ Shown' if config_summary['compliance']['medical_disclaimer'] else '❌ Hidden'}
- **Audit Logging**: {'✅ Enabled' if config_summary['compliance']['audit_logging'] else '❌ Disabled'}

### 🛠️ Developer Settings
- **Developer Mode**: {'✅ Enabled' if config_summary['developer']['developer_mode'] else '❌ Disabled'}
- **Debug Logging**: {'✅ Enabled' if config_summary['developer']['debug_logging'] else '❌ Disabled'}
- **Mock Transcription**: {'✅ Enabled' if config_summary['developer']['mock_transcription'] else '❌ Disabled'}

### ⚡ Performance Settings
- **Max Concurrent Sessions**: {config_summary['performance']['max_concurrent_sessions']}
- **Connection Retries**: {config_summary['performance']['connection_retry_attempts']}

### ✨ Feature Settings
- **Auto SOAP Generation**: {'✅ Enabled' if config_summary['features']['auto_soap_generation'] else '❌ Disabled'}
- **Real-time Transcription**: {'✅ Enabled' if config_summary['features']['real_time_transcription'] else '❌ Disabled'}

---

### 🔧 Configuration Management

#### Modify Settings
1. Click the **Settings** (⚙️) icon next to this function in Workspace → Functions
2. Adjust the **Valves** (configuration options) as needed
3. Click **Save** to apply changes

#### Environment Variables Export
Use these environment variables in your deployment:

```bash
{chr(10).join(f'export {key}="{value}"' for key, value in env_vars.items())}
```

#### Testing Configuration
- Enable **Mock Transcription** for testing without real audio
- Enable **Developer Mode** for additional debug features
- Check **Debug Logging** for detailed operation logs

---

**Note**: Configuration changes take effect immediately through the Valves system.
            """.strip()

            # Final status update
            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": "Configuration loaded successfully!"},
                })

            return {
                "content": response_content,
                "configuration": config_summary,
            }

        except Exception as e:
            error_message = f"Configuration error: {str(e)}"

            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": f"❌ {error_message}"},
                })

            return {
                "content": f"## ❌ Error\n\n{error_message}\n\n**Timestamp**: {datetime.now().isoformat()}",
            }
