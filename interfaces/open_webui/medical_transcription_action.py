"""
Medical Transcription Action for Open WebUI
Provides a simple button interface for live medical transcription with automatic SOAP note generation.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import Any

import websockets
from pydantic import BaseModel, Field

# Add the healthcare-api config path for config loading
sys.path.append("/home/intelluxe/services/user/healthcare-api")
from config.ui_config_loader import UI_CONFIG


class Action:
    """
    Medical Transcription Action

    Adds a "🎙️ Start Medical Transcription" button to Open WebUI chat interface.
    When clicked, starts live transcription session and generates SOAP notes automatically.
    """

    class Valves(BaseModel):
        """Dynamic Configuration for Medical Transcription Action - editable via Open WebUI"""

        # === Healthcare API Configuration ===
        HEALTHCARE_API_URL: str = Field(
            default=UI_CONFIG.api_integration.websocket_url,
            description="WebSocket URL for healthcare API connection",
        )
        HEALTHCARE_REST_URL: str = Field(
            default=UI_CONFIG.api_integration.rest_api_url,
            description="REST API URL for healthcare services",
        )

        # === Developer Configuration ===
        DEVELOPER_MODE: bool = Field(
            default=UI_CONFIG.developer.mode_enabled,
            description="Enable developer mode with additional logging and test features",
        )
        DEVELOPER_USERS: list = Field(
            default=UI_CONFIG.developer.test_users,
            description="List of approved developer users for testing",
        )
        DEFAULT_TEST_USER: str = Field(
            default=UI_CONFIG.developer.default_test_user,
            description="Default user for testing when user detection fails",
        )
        DEBUG_LOGGING: bool = Field(
            default=UI_CONFIG.developer.debug_logging,
            description="Enable detailed debug logging for troubleshooting",
        )
        MOCK_TRANSCRIPTION: bool = Field(
            default=UI_CONFIG.developer.mock_transcription,
            description="Use mock transcription for testing without real audio processing",
        )

        # === Transcription Settings ===
        TRANSCRIPTION_TIMEOUT: int = Field(
            default=UI_CONFIG.session.timeout_seconds,
            ge=60,
            le=1800,
            description="Maximum transcription session duration in seconds (1-30 minutes)",
        )
        CHUNK_INTERVAL: int = Field(
            default=UI_CONFIG.session.chunk_interval_seconds,
            ge=1,
            le=10,
            description="Audio chunk interval in seconds (1-10 seconds)",
        )
        AUTO_SOAP_GENERATION: bool = Field(
            default=UI_CONFIG.session.auto_soap_generation,
            description="Automatically generate SOAP notes from completed transcriptions",
        )

        # === Medical Compliance ===
        MEDICAL_DISCLAIMER: str = Field(
            default=UI_CONFIG.compliance.disclaimer_text,
            description="Medical disclaimer text shown to users",
        )
        SHOW_MEDICAL_DISCLAIMER: bool = Field(
            default=UI_CONFIG.compliance.show_medical_disclaimer,
            description="Display medical disclaimer to users",
        )
        PHI_PROTECTION_ENABLED: bool = Field(
            default=UI_CONFIG.compliance.phi_protection_enabled,
            description="Enable PHI (Protected Health Information) protection",
        )

        # === User Experience ===
        SHOW_REAL_TIME_TRANSCRIPTION: bool = Field(
            default=UI_CONFIG.user_experience.show_real_time_transcription,
            description="Show transcription results in real-time as they are processed",
        )
        SHOW_STATUS_UPDATES: bool = Field(
            default=UI_CONFIG.user_experience.show_status_updates,
            description="Show status updates during transcription sessions",
        )

        # === Performance Settings ===
        MAX_CONCURRENT_SESSIONS: int = Field(
            default=UI_CONFIG.performance.max_concurrent_sessions,
            ge=1,
            le=20,
            description="Maximum concurrent transcription sessions per user",
        )
        CONNECTION_RETRY_ATTEMPTS: int = Field(
            default=UI_CONFIG.error_handling.connection_retry_attempts,
            ge=1,
            le=10,
            description="Number of connection retry attempts on failure",
        )

    def __init__(self):
        self.id = UI_CONFIG.action.id
        self.name = UI_CONFIG.action.name
        self.description = UI_CONFIG.action.description
        self.valves = self.Valves()

        # Set up logging
        self.logger = logging.getLogger(__name__)
        if self.valves.DEBUG_LOGGING:
            self.logger.setLevel(logging.DEBUG)

    def update_configuration(self, new_values: dict[str, Any]) -> dict[str, Any]:
        """
        Update YAML configuration files with new values from Valves
        This method is called when users change settings in the Open WebUI interface
        """
        try:
            from pathlib import Path

            import yaml

            config_path = Path("/home/intelluxe/services/user/healthcare-api/config/ui_config.yml")

            # Load current configuration
            with open(config_path, encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            # Map valve fields to YAML structure
            field_mappings = {
                "HEALTHCARE_API_URL": ("api_integration", "websocket_url"),
                "HEALTHCARE_REST_URL": ("api_integration", "rest_api_url"),
                "DEVELOPER_MODE": ("developer", "mode_enabled"),
                "DEVELOPER_USERS": ("developer", "test_users"),
                "DEFAULT_TEST_USER": ("developer", "default_test_user"),
                "DEBUG_LOGGING": ("developer", "debug_logging"),
                "MOCK_TRANSCRIPTION": ("developer", "mock_transcription"),
                "TRANSCRIPTION_TIMEOUT": ("session", "timeout_seconds"),
                "CHUNK_INTERVAL": ("session", "chunk_interval_seconds"),
                "AUTO_SOAP_GENERATION": ("session", "auto_soap_generation"),
                "MEDICAL_DISCLAIMER": ("compliance", "disclaimer_text"),
                "SHOW_MEDICAL_DISCLAIMER": ("compliance", "show_medical_disclaimer"),
                "PHI_PROTECTION_ENABLED": ("compliance", "phi_protection_enabled"),
                "SHOW_REAL_TIME_TRANSCRIPTION": ("user_experience", "show_real_time_transcription"),
                "SHOW_STATUS_UPDATES": ("user_experience", "show_status_updates"),
                "MAX_CONCURRENT_SESSIONS": ("performance", "max_concurrent_sessions"),
                "CONNECTION_RETRY_ATTEMPTS": ("error_handling", "connection_retry_attempts"),
            }

            # Update configuration data
            for valve_field, value in new_values.items():
                if valve_field in field_mappings:
                    section, key = field_mappings[valve_field]
                    if section in config_data and isinstance(config_data[section], dict):
                        config_data[section][key] = value
                        self.logger.info(f"Updated {section}.{key} = {value}")

            # Create backup of current configuration
            backup_path = config_path.with_suffix(".yml.backup")
            with open(backup_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(config_data, f, default_flow_style=False, sort_keys=False)

            # Write updated configuration
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(config_data, f, default_flow_style=False, sort_keys=False)

            # Reload configuration to validate changes
            global UI_CONFIG
            from config.ui_config_loader import load_ui_config
            UI_CONFIG = load_ui_config()

            self.logger.info("Configuration updated successfully")
            return {
                "success": True,
                "message": "Configuration updated successfully",
                "updated_fields": list(new_values.keys()),
                "backup_created": str(backup_path),
            }

        except Exception as e:
            error_msg = f"Failed to update configuration: {str(e)}"
            self.logger.exception(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "message": "Configuration update failed - check logs for details",
            }

    def validate_configuration(self, values: dict[str, Any]) -> dict[str, Any]:
        """Validate configuration values before applying"""
        errors = []
        warnings = []

        # Validate URLs
        if "HEALTHCARE_API_URL" in values:
            url = values["HEALTHCARE_API_URL"]
            if not (url.startswith(("ws://", "wss://"))):
                errors.append("HEALTHCARE_API_URL must be a valid WebSocket URL (ws:// or wss://)")

        if "HEALTHCARE_REST_URL" in values:
            url = values["HEALTHCARE_REST_URL"]
            if not (url.startswith(("http://", "https://"))):
                errors.append("HEALTHCARE_REST_URL must be a valid HTTP URL")

        # Validate timeouts
        if "TRANSCRIPTION_TIMEOUT" in values:
            timeout = values["TRANSCRIPTION_TIMEOUT"]
            if timeout < 60:
                errors.append("TRANSCRIPTION_TIMEOUT must be at least 60 seconds")
            elif timeout > 1800:
                errors.append("TRANSCRIPTION_TIMEOUT must not exceed 1800 seconds (30 minutes)")
            elif timeout > 600:
                warnings.append("TRANSCRIPTION_TIMEOUT over 10 minutes may impact user experience")

        # Validate user lists
        if "DEVELOPER_USERS" in values:
            users = values["DEVELOPER_USERS"]
            if not isinstance(users, list) or len(users) == 0:
                errors.append("DEVELOPER_USERS must be a non-empty list")

            if "DEFAULT_TEST_USER" in values:
                default_user = values["DEFAULT_TEST_USER"]
                if default_user not in users:
                    warnings.append("DEFAULT_TEST_USER should be included in DEVELOPER_USERS list")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def rollback_configuration(self, backup_path: str = None) -> dict[str, Any]:
        """Rollback configuration to previous backup"""
        try:
            from pathlib import Path

            import yaml

            config_path = Path("/home/intelluxe/services/user/healthcare-api/config/ui_config.yml")

            if backup_path:
                backup_file = Path(backup_path)
            else:
                backup_file = config_path.with_suffix(".yml.backup")

            if not backup_file.exists():
                return {
                    "success": False,
                    "error": "No backup file found",
                    "message": "Cannot rollback - no backup available",
                }

            # Restore from backup
            with open(backup_file, encoding="utf-8") as f:
                backup_data = yaml.safe_load(f)

            # Write restored configuration
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(backup_data, f, default_flow_style=False, sort_keys=False)

            # Reload configuration
            global UI_CONFIG
            from config.ui_config_loader import load_ui_config
            UI_CONFIG = load_ui_config()

            self.logger.info(f"Configuration rolled back from {backup_file}")
            return {
                "success": True,
                "message": f"Configuration restored from backup: {backup_file}",
                "restored_from": str(backup_file),
            }

        except Exception as e:
            error_msg = f"Failed to rollback configuration: {str(e)}"
            self.logger.exception(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "message": "Configuration rollback failed",
            }

    def create_configuration_snapshot(self) -> dict[str, Any]:
        """Create a timestamped configuration snapshot"""
        try:
            from pathlib import Path

            import yaml

            config_path = Path("/home/intelluxe/services/user/healthcare-api/config/ui_config.yml")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            snapshot_path = config_path.with_name(f"ui_config_snapshot_{timestamp}.yml")

            # Load current configuration
            with open(config_path, encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            # Add snapshot metadata
            config_data["_snapshot_metadata"] = {
                "created_at": datetime.now().isoformat(),
                "original_file": str(config_path),
                "snapshot_type": "manual",
            }

            # Write snapshot
            with open(snapshot_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(config_data, f, default_flow_style=False, sort_keys=False)

            self.logger.info(f"Configuration snapshot created: {snapshot_path}")
            return {
                "success": True,
                "message": f"Configuration snapshot created: {snapshot_path}",
                "snapshot_path": str(snapshot_path),
                "timestamp": timestamp,
            }

        except Exception as e:
            error_msg = f"Failed to create configuration snapshot: {str(e)}"
            self.logger.exception(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "message": "Snapshot creation failed",
            }

    def test_configuration(self, test_config: dict[str, Any] = None) -> dict[str, Any]:
        """Test configuration changes without applying them"""
        try:
            test_results = {
                "connection_tests": [],
                "validation_results": {},
                "warnings": [],
                "recommendations": [],
            }

            config_to_test = test_config or self.valves.dict()

            # Validate configuration
            validation_result = self.validate_configuration(config_to_test)
            test_results["validation_results"] = validation_result

            # Test WebSocket URL connectivity
            if "HEALTHCARE_API_URL" in config_to_test:
                ws_url = config_to_test["HEALTHCARE_API_URL"]
                test_results["connection_tests"].append({
                    "test": "websocket_connectivity",
                    "url": ws_url,
                    "status": "skipped",  # Would need async context for real test
                    "message": f"WebSocket URL format: {ws_url}",
                })

            # Test timeout settings
            if "TRANSCRIPTION_TIMEOUT" in config_to_test:
                timeout = config_to_test["TRANSCRIPTION_TIMEOUT"]
                if timeout > 600:
                    test_results["warnings"].append(
                        f"Transcription timeout ({timeout}s) is quite long - may impact user experience",
                    )
                if timeout < 120:
                    test_results["warnings"].append(
                        f"Transcription timeout ({timeout}s) is short - may cut off longer sessions",
                    )

            # Performance recommendations
            if "MAX_CONCURRENT_SESSIONS" in config_to_test:
                max_sessions = config_to_test["MAX_CONCURRENT_SESSIONS"]
                if max_sessions > 10:
                    test_results["recommendations"].append(
                        "Consider system resources with high concurrent session limits",
                    )

            # Developer mode checks
            if config_to_test.get("DEVELOPER_MODE", False):
                test_results["warnings"].append(
                    "Developer mode enabled - disable in production for security",
                )

            if config_to_test.get("DEBUG_LOGGING", False):
                test_results["warnings"].append(
                    "Debug logging enabled - may impact performance and create large log files",
                )

            return {
                "success": True,
                "test_results": test_results,
                "overall_status": "passed" if validation_result["valid"] else "failed",
                "message": "Configuration testing completed",
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Configuration testing failed: {str(e)}",
            }

    def get_configuration_history(self) -> dict[str, Any]:
        """Get history of configuration changes"""
        try:
            from pathlib import Path

            config_dir = Path("/home/intelluxe/services/user/healthcare-api/config/")

            # Find all backup and snapshot files
            backup_files = list(config_dir.glob("ui_config*.yml.backup"))
            snapshot_files = list(config_dir.glob("ui_config_snapshot_*.yml"))

            history = {
                "backups": [],
                "snapshots": [],
                "current_config": str(config_dir / "ui_config.yml"),
            }

            # Process backup files
            for backup_file in sorted(backup_files, key=lambda x: x.stat().st_mtime, reverse=True):
                stat = backup_file.stat()
                history["backups"].append({
                    "file": str(backup_file),
                    "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "size_bytes": stat.st_size,
                })

            # Process snapshot files
            for snapshot_file in sorted(snapshot_files, key=lambda x: x.stat().st_mtime, reverse=True):
                stat = snapshot_file.stat()
                history["snapshots"].append({
                    "file": str(snapshot_file),
                    "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "size_bytes": stat.st_size,
                })

            return {
                "success": True,
                "history": history,
                "message": f"Found {len(backup_files)} backups and {len(snapshot_files)} snapshots",
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to get configuration history: {str(e)}",
            }

    async def action(
        self,
        body: dict[str, Any],
        __user__: dict | None = None,
        __event_emitter__=None,
    ) -> dict[str, Any]:
        """
        Main action function - called when user clicks transcription button
        """
        try:
            # Extract user information
            user_id = self.extract_user_id(__user__, body)

            # Developer mode handling
            if self.valves.DEVELOPER_MODE:
                user_id = self.handle_developer_mode(user_id)

            doctor_id = f"dr_{user_id}"

            # Log session start
            await self.emit_status(
                f"🎙️ Starting medical transcription session for {user_id}",
                __event_emitter__,
                {"user_id": user_id, "doctor_id": doctor_id},
            )

            # Show medical disclaimer
            await self.emit_status(
                self.valves.MEDICAL_DISCLAIMER,
                __event_emitter__,
                {"type": "disclaimer"},
            )

            # Start transcription session
            session_result = await self.start_transcription_session(
                doctor_id, user_id, __event_emitter__,
            )

            if session_result["success"]:
                return {
                    "success": True,
                    "message": "✅ Medical transcription completed successfully",
                    "data": {
                        "session_id": session_result["session_id"],
                        "transcription": session_result["transcription"],
                        "soap_note": session_result.get("soap_note"),
                        "user_id": user_id,
                        "timestamp": datetime.now().isoformat(),
                    },
                }
            return {
                "success": False,
                "message": f"❌ Transcription failed: {session_result.get('error', 'Unknown error')}",
                "error": session_result.get("error"),
            }

        except Exception as e:
            self.logger.exception(f"Medical transcription action failed: {e}")
            return {
                "success": False,
                "message": f"❌ System error: {str(e)}",
                "error": str(e),
            }

    def extract_user_id(self, __user__: dict | None, body: dict[str, Any]) -> str | None:
        """Extract user ID from various possible sources"""

        user_candidates = []

        # Try user object attributes
        if __user__:
            if isinstance(__user__, dict):
                user_candidates.extend([
                    __user__.get("id"),
                    __user__.get("username"),
                    __user__.get("email"),
                    __user__.get("name"),
                ])
            else:
                # Try object attributes
                for attr in ["id", "username", "email", "name"]:
                    if hasattr(__user__, attr):
                        user_candidates.append(getattr(__user__, attr))

        # Try body user information
        if "user" in body:
            user_info = body["user"]
            if isinstance(user_info, dict):
                user_candidates.extend([
                    user_info.get("id"),
                    user_info.get("username"),
                    user_info.get("email"),
                    user_info.get("name"),
                ])

        # Return first valid candidate
        for candidate in user_candidates:
            if candidate and str(candidate).strip() and candidate != "unknown":
                return str(candidate).lower()

        return None

    def handle_developer_mode(self, user_id: str | None) -> str:
        """Handle developer mode user identification"""

        if not user_id or user_id == "unknown":
            user_id = self.valves.DEFAULT_TEST_USER
            self.logger.info(f"Developer mode: Using default test user '{user_id}'")

        # Validate developer users
        if user_id in self.valves.DEVELOPER_USERS:
            self.logger.info(f"Developer mode: Confirmed developer user '{user_id}'")
            return user_id
        # Check if it's a partial match
        for dev_user in self.valves.DEVELOPER_USERS:
            if dev_user in user_id or user_id in dev_user:
                self.logger.info(f"Developer mode: Matched '{user_id}' to '{dev_user}'")
                return dev_user

        # Default to primary test user
        self.logger.warning(f"Developer mode: Unknown user '{user_id}', using default '{self.valves.DEFAULT_TEST_USER}'")
        return self.valves.DEFAULT_TEST_USER

    async def start_transcription_session(
        self,
        doctor_id: str,
        user_id: str,
        __event_emitter__,
    ) -> dict[str, Any]:
        """Start WebSocket transcription session with healthcare API"""

        try:
            # Mock transcription for testing
            if self.valves.MOCK_TRANSCRIPTION:
                return await self.mock_transcription_session(doctor_id, user_id, __event_emitter__)

            # Real WebSocket connection
            ws_url = f"{self.valves.HEALTHCARE_API_URL}/ws/transcription/{doctor_id}"

            await self.emit_status(
                "🔗 Connecting to healthcare transcription service...",
                __event_emitter__,
            )

            session_data = {
                "session_id": None,
                "transcription_chunks": [],
                "full_transcription": "",
                "soap_note": None,
            }

            # Connect to WebSocket
            try:
                async with websockets.connect(ws_url) as websocket:

                    # Wait for session start message
                    initial_message = await websocket.recv()
                    session_start = json.loads(initial_message)

                    if session_start.get("type") == "session_start":
                        session_data["session_id"] = session_start.get("session_id")

                        await self.emit_status(
                            f"✅ Connected! Session ID: {session_data['session_id']}",
                            __event_emitter__,
                            {"session_id": session_data["session_id"]},
                        )

                        # Simulate transcription session
                        await self.simulate_transcription_session(
                            websocket, session_data, __event_emitter__,
                        )

                        # End session and get SOAP note
                        await websocket.send(json.dumps({"type": "end_session"}))

                        # Wait for session end response
                        end_message = await websocket.recv()
                        session_end = json.loads(end_message)

                        if session_end.get("type") == "session_end":
                            session_data["soap_note"] = session_end.get("soap_note")

                            await self.emit_status(
                                "📋 SOAP note generated successfully!",
                                __event_emitter__,
                                {"soap_generated": True},
                            )

            except websockets.exceptions.ConnectionClosed:
                self.logger.warning("WebSocket connection closed")
            except Exception as ws_error:
                self.logger.exception(f"WebSocket error: {ws_error}")
                return {
                    "success": False,
                    "error": f"Connection failed: {str(ws_error)}",
                }

            return {
                "success": True,
                "session_id": session_data["session_id"],
                "transcription": session_data["full_transcription"],
                "soap_note": session_data.get("soap_note"),
            }

        except Exception as e:
            self.logger.exception(f"Transcription session failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def simulate_transcription_session(
        self,
        websocket,
        session_data: dict,
        __event_emitter__,
    ):
        """Simulate a medical transcription session with audio chunks"""

        # Mock medical transcription chunks
        mock_transcription_chunks = [
            "Patient presents with chief complaint of fatigue lasting two weeks.",
            "History of present illness: 45-year-old female reports increasing fatigue.",
            "Physical examination: Blood pressure 140 over 85, heart rate 78 and regular.",
            "Patient appears tired but alert and oriented.",
            "Cardiovascular examination shows regular rate and rhythm.",
            "Assessment: Hypertension, newly diagnosed. Fatigue likely related to blood pressure elevation.",
            "Plan: Start lisinopril 10 milligrams daily. Patient education provided.",
            "Follow-up in two weeks to assess response to treatment.",
        ]

        await self.emit_status(
            "🎙️ Recording... (Simulated medical encounter)",
            __event_emitter__,
            {"recording": True},
        )

        for i, chunk in enumerate(mock_transcription_chunks):
            # Send mock audio chunk
            audio_message = {
                "type": "audio_chunk",
                "audio_data": {
                    "format": "webm",
                    "data": f"mock_audio_chunk_{i}",
                    "duration": 2.0,
                },
            }

            await websocket.send(json.dumps(audio_message))

            # Wait for transcription response
            response = await websocket.recv()
            transcription_result = json.loads(response)

            if transcription_result.get("type") == "transcription_chunk":
                result = transcription_result.get("result", {})
                if result.get("success"):
                    transcription_text = result.get("transcription", chunk)
                    session_data["transcription_chunks"].append(transcription_text)
                    session_data["full_transcription"] += transcription_text + " "

                    # Show real-time transcription
                    await self.emit_status(
                        f"📝 {transcription_text}",
                        __event_emitter__,
                        {"transcription_chunk": transcription_text, "chunk_index": i},
                    )

            # Simulate natural speaking pace
            await asyncio.sleep(1.5)

    async def mock_transcription_session(
        self,
        doctor_id: str,
        user_id: str,
        __event_emitter__,
    ) -> dict[str, Any]:
        """Mock transcription session for testing without WebSocket"""

        await self.emit_status(
            "🧪 Mock transcription mode (for testing)",
            __event_emitter__,
            {"mock_mode": True},
        )

        # Simulate connection delay
        await asyncio.sleep(1)

        session_id = f"mock_session_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Mock transcription content
        mock_transcription = (
            "Chief complaint: Patient presents with fatigue and headaches for the past two weeks. "
            "Physical examination: Blood pressure 140 over 85. Heart rate 78 and regular. "
            "Assessment: Hypertension, newly diagnosed. Fatigue likely related to blood pressure elevation. "
            "Plan: Start lisinopril 10 milligrams daily. Follow-up in two weeks."
        )

        # Mock SOAP note
        mock_soap_note = """
SOAP NOTE
=========

SUBJECTIVE:
Chief Complaint: Patient presents with fatigue and headaches for the past two weeks.
History of Present Illness: 45-year-old female reports increasing fatigue and intermittent headaches.

OBJECTIVE:
Physical Examination: Blood pressure 140 over 85. Heart rate 78 and regular. Patient appears tired but alert.

ASSESSMENT:
Hypertension, newly diagnosed. Fatigue likely related to blood pressure elevation.

PLAN:
Start lisinopril 10 milligrams daily. Patient education provided. Follow-up in two weeks.

---
Generated by Medical Transcription System
Quality Score: 0.92
"""

        await self.emit_status(
            f"📝 Transcription: {mock_transcription[:100]}...",
            __event_emitter__,
            {"transcription_preview": True},
        )

        await asyncio.sleep(2)

        await self.emit_status(
            "📋 Generating SOAP note...",
            __event_emitter__,
            {"generating_soap": True},
        )

        await asyncio.sleep(1)

        return {
            "success": True,
            "session_id": session_id,
            "transcription": mock_transcription,
            "soap_note": mock_soap_note,
        }

    async def emit_status(
        self,
        message: str,
        __event_emitter__,
        data: dict[str, Any] = None,
    ):
        """Emit status message to Open WebUI interface"""

        if __event_emitter__:
            await __event_emitter__({
                "type": "status",
                "data": {
                    "message": message,
                    "timestamp": datetime.now().isoformat(),
                    **(data or {}),
                },
            })

        if self.valves.DEBUG_LOGGING:
            self.logger.info(f"Status: {message}")

    def get_action_metadata(self) -> dict[str, Any]:
        """Return metadata about this action for Open WebUI"""

        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": UI_CONFIG.action.icon,
            "category": UI_CONFIG.action.category,
            "developer_mode": self.valves.DEVELOPER_MODE,
            "supported_users": self.valves.DEVELOPER_USERS if self.valves.DEVELOPER_MODE else "all",
            "healthcare_compliance": UI_CONFIG.compliance.healthcare_compliance_mode,
            "phi_protection": UI_CONFIG.compliance.phi_protection_enabled,
        }
