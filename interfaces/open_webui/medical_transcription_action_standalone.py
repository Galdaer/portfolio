"""
Medical Transcription Action for Open WebUI (Standalone Version)
Provides a simple button interface for live medical transcription with automatic SOAP note generation.
This standalone version works without external dependencies.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class Action:
    """
    Medical Transcription Action

    Adds a "🎙️ Start Medical Transcription" button to Open WebUI chat interface.
    When clicked, starts live transcription session and generates SOAP notes automatically.
    This standalone version uses environment variables and fallback configurations.
    """

    class Valves(BaseModel):
        """Dynamic Configuration for Medical Transcription Action - editable via Open WebUI"""

        # === Healthcare API Configuration ===
        HEALTHCARE_API_URL: str = Field(
            default=os.getenv('HEALTHCARE_WEBSOCKET_URL', 'ws://localhost:8000'),
            description="WebSocket URL for healthcare API connection",
        )
        HEALTHCARE_REST_URL: str = Field(
            default=os.getenv('HEALTHCARE_REST_URL', 'http://localhost:8000'),
            description="REST API URL for healthcare services",
        )

        # === Developer Configuration ===
        DEVELOPER_MODE: bool = Field(
            default=os.getenv('DEVELOPER_MODE', 'true').lower() == 'true',
            description="Enable developer mode with additional logging and test features",
        )
        DEVELOPER_USERS: list = Field(
            default=os.getenv('DEVELOPER_USERS', 'admin,justin,jeff').split(','),
            description="List of approved developer users for testing",
        )
        DEFAULT_TEST_USER: str = Field(
            default=os.getenv('DEFAULT_TEST_USER', 'admin'),
            description="Default user for testing when user detection fails",
        )
        DEBUG_LOGGING: bool = Field(
            default=os.getenv('DEBUG_LOGGING', 'false').lower() == 'true',
            description="Enable detailed debug logging for troubleshooting",
        )
        MOCK_TRANSCRIPTION: bool = Field(
            default=os.getenv('MOCK_TRANSCRIPTION', 'false').lower() == 'true',
            description="Use mock transcription for testing without real audio processing",
        )

        # === Transcription Settings ===
        TRANSCRIPTION_TIMEOUT: int = Field(
            default=int(os.getenv('TRANSCRIPTION_TIMEOUT', '300')),
            ge=60,
            le=1800,
            description="Maximum transcription session duration in seconds (1-30 minutes)",
        )
        CHUNK_INTERVAL: int = Field(
            default=int(os.getenv('CHUNK_INTERVAL', '2')),
            ge=1,
            le=10,
            description="Audio chunk interval in seconds (1-10 seconds)",
        )
        AUTO_SOAP_GENERATION: bool = Field(
            default=os.getenv('AUTO_SOAP_GENERATION', 'true').lower() == 'true',
            description="Automatically generate SOAP notes from completed transcriptions",
        )

        # === Medical Compliance ===
        MEDICAL_DISCLAIMER: str = Field(
            default=os.getenv('MEDICAL_DISCLAIMER_TEXT',
                            "⚠️ **Medical Disclaimer**: This system provides administrative support only, "
                            "not medical advice. Always consult healthcare professionals for medical decisions. "
                            "This tool is for documentation assistance only."),
            description="Medical disclaimer text shown to users",
        )
        SHOW_MEDICAL_DISCLAIMER: bool = Field(
            default=os.getenv('SHOW_MEDICAL_DISCLAIMER', 'true').lower() == 'true',
            description="Display medical disclaimer to users",
        )
        PHI_PROTECTION_ENABLED: bool = Field(
            default=os.getenv('PHI_PROTECTION_ENABLED', 'true').lower() == 'true',
            description="Enable PHI (Protected Health Information) protection",
        )

        # === User Experience ===
        SHOW_REAL_TIME_TRANSCRIPTION: bool = Field(
            default=os.getenv('SHOW_REAL_TIME_TRANSCRIPTION', 'true').lower() == 'true',
            description="Show transcription results in real-time as they are processed",
        )
        SHOW_STATUS_UPDATES: bool = Field(
            default=os.getenv('SHOW_STATUS_UPDATES', 'true').lower() == 'true',
            description="Display status updates during transcription process",
        )
        ALLOW_SESSION_HISTORY: bool = Field(
            default=os.getenv('ALLOW_SESSION_HISTORY', 'true').lower() == 'true',
            description="Allow users to view previous transcription sessions",
        )

        # === Advanced Settings ===
        CONNECTION_RETRY_ATTEMPTS: int = Field(
            default=int(os.getenv('CONNECTION_RETRY_ATTEMPTS', '3')),
            ge=1,
            le=10,
            description="Number of connection retry attempts (1-10)",
        )
        RETRY_DELAY_SECONDS: int = Field(
            default=int(os.getenv('RETRY_DELAY_SECONDS', '5')),
            ge=1,
            le=30,
            description="Delay between retry attempts in seconds (1-30)",
        )
        MAX_TRANSCRIPTION_LENGTH: int = Field(
            default=int(os.getenv('MAX_TRANSCRIPTION_LENGTH', '10000')),
            ge=1000,
            le=50000,
            description="Maximum transcription length in characters (1000-50000)",
        )

    def __init__(self):
        self.valves = self.Valves()
        self._setup_logging()

    def _setup_logging(self):
        """Setup logging configuration."""
        log_level = logging.DEBUG if self.valves.DEBUG_LOGGING else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def _is_developer_user(self, user_id: str) -> bool:
        """Check if user is in developer list."""
        return user_id in self.valves.DEVELOPER_USERS

    def _get_mock_transcription_data(self) -> dict:
        """Generate mock transcription data for testing."""
        return {
            "session_id": f"mock_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "status": "completed",
            "transcription": {
                "text": "Patient presents with chief complaint of headache lasting 3 days. "
                       "Pain is described as throbbing, located in temporal region. "
                       "Associated with mild nausea. No fever or visual disturbances. "
                       "Patient has history of migraines. Current medications include "
                       "ibuprofen as needed. Physical examination shows blood pressure "
                       "120/80, pulse 72, temperature 98.6 F. Neurological exam normal.",
                "confidence_score": 0.92,
                "duration_seconds": 180,
                "word_count": 67
            },
            "soap_note": {
                "subjective": "Patient reports headache lasting 3 days, throbbing in nature, "
                             "located in temporal region, associated with mild nausea. "
                             "History of migraines. Takes ibuprofen as needed.",
                "objective": "Vital signs: BP 120/80, HR 72, T 98.6°F. "
                            "Neurological examination within normal limits.",
                "assessment": "Likely migraine headache, consistent with patient's history.",
                "plan": "Continue current ibuprofen regimen. Consider preventive therapy "
                       "if frequency increases. Follow up if symptoms worsen or persist."
            },
            "metadata": {
                "phi_detected": False,
                "quality_flags": [],
                "processing_time_ms": 1500
            }
        }

    async def _simulate_transcription_session(self, __event_emitter__=None):
        """Simulate a transcription session for testing."""
        if __event_emitter__:
            await __event_emitter__({
                "type": "status",
                "data": {"description": "🎭 Starting mock transcription session..."}
            })
            await asyncio.sleep(1)

            await __event_emitter__({
                "type": "status", 
                "data": {"description": "🎤 Mock audio processing started"}
            })
            await asyncio.sleep(2)

            if self.valves.SHOW_REAL_TIME_TRANSCRIPTION:
                partial_texts = [
                    "Patient presents with...",
                    "Patient presents with chief complaint of headache...",
                    "Patient presents with chief complaint of headache lasting 3 days..."
                ]
                
                for text in partial_texts:
                    await __event_emitter__({
                        "type": "message",
                        "data": {"content": f"📝 **Transcribing**: {text}"}
                    })
                    await asyncio.sleep(1.5)

            await __event_emitter__({
                "type": "status",
                "data": {"description": "🧠 Generating SOAP note from transcription..."}
            })
            await asyncio.sleep(2)

        return self._get_mock_transcription_data()

    def _format_transcription_response(self, transcription_data: dict) -> str:
        """Format transcription data into a user-friendly response."""
        response_parts = []
        
        # Add disclaimer if enabled
        if self.valves.SHOW_MEDICAL_DISCLAIMER:
            response_parts.append(self.valves.MEDICAL_DISCLAIMER)
            response_parts.append("\n" + "="*50 + "\n")

        # Add session info
        response_parts.append(f"## 🎙️ Medical Transcription Complete")
        response_parts.append(f"**Session ID**: {transcription_data.get('session_id', 'N/A')}")
        response_parts.append(f"**Status**: {transcription_data.get('status', 'unknown')}")
        response_parts.append(f"**Timestamp**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        response_parts.append("")

        # Add transcription
        transcription = transcription_data.get('transcription', {})
        if transcription:
            response_parts.append("### 📝 Transcription")
            response_parts.append(f"**Text**: {transcription.get('text', 'No transcription available')}")
            response_parts.append(f"**Confidence**: {transcription.get('confidence_score', 0):.2%}")
            response_parts.append(f"**Duration**: {transcription.get('duration_seconds', 0)} seconds")
            response_parts.append(f"**Word Count**: {transcription.get('word_count', 0)} words")
            response_parts.append("")

        # Add SOAP note if auto-generation is enabled
        if self.valves.AUTO_SOAP_GENERATION:
            soap_note = transcription_data.get('soap_note', {})
            if soap_note:
                response_parts.append("### 📋 Generated SOAP Note")
                response_parts.append(f"**S** (Subjective): {soap_note.get('subjective', 'N/A')}")
                response_parts.append(f"**O** (Objective): {soap_note.get('objective', 'N/A')}")
                response_parts.append(f"**A** (Assessment): {soap_note.get('assessment', 'N/A')}")
                response_parts.append(f"**P** (Plan): {soap_note.get('plan', 'N/A')}")
                response_parts.append("")

        # Add metadata
        metadata = transcription_data.get('metadata', {})
        if metadata:
            response_parts.append("### 📊 Session Metadata")
            response_parts.append(f"**PHI Detected**: {'⚠️ Yes' if metadata.get('phi_detected', False) else '✅ None detected'}")
            response_parts.append(f"**Processing Time**: {metadata.get('processing_time_ms', 0)}ms")
            
            quality_flags = metadata.get('quality_flags', [])
            if quality_flags:
                response_parts.append(f"**Quality Flags**: {', '.join(quality_flags)}")
            else:
                response_parts.append("**Quality**: ✅ No issues detected")

        return "\n".join(response_parts)

    async def action(
        self,
        body: dict,
        __user__: Optional[dict] = None,
        __event_emitter__=None,
    ) -> Optional[dict]:
        """
        Main action handler for medical transcription.
        
        Args:
            body: The request body from Open WebUI
            __user__: User information (if available)
            __event_emitter__: Event emitter for real-time updates
        """
        try:
            user_id = __user__.get("email", self.valves.DEFAULT_TEST_USER) if __user__ else self.valves.DEFAULT_TEST_USER
            is_developer = self._is_developer_user(user_id)
            
            self.logger.info(f"Medical transcription action started for user: {user_id}")

            # Show initial status
            if __event_emitter__ and self.valves.SHOW_STATUS_UPDATES:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": "🎙️ Initializing medical transcription session..."}
                })

            # Check if we're in mock mode or if this is a developer
            if self.valves.MOCK_TRANSCRIPTION or (is_developer and self.valves.DEVELOPER_MODE):
                transcription_data = await self._simulate_transcription_session(__event_emitter__)
                response_text = self._format_transcription_response(transcription_data)
                
                if __event_emitter__:
                    await __event_emitter__({
                        "type": "status",
                        "data": {"description": "✅ Mock transcription completed successfully"}
                    })
                
                return {
                    "content": response_text,
                    "session_data": transcription_data
                }
            
            else:
                # Real transcription mode - would connect to actual service
                if __event_emitter__:
                    await __event_emitter__({
                        "type": "status",
                        "data": {"description": f"🔌 Connecting to transcription service at {self.valves.HEALTHCARE_API_URL}"}
                    })
                
                # For now, return instructions since we can't connect to real service in standalone mode
                instructions = f"""
## 🎙️ Medical Transcription Service

**Configuration**:
- WebSocket URL: `{self.valves.HEALTHCARE_API_URL}`
- REST API URL: `{self.valves.HEALTHCARE_REST_URL}`
- Timeout: {self.valves.TRANSCRIPTION_TIMEOUT} seconds
- Chunk Interval: {self.valves.CHUNK_INTERVAL} seconds

**Status**: ⚠️ **Standalone Mode**

This function is running in standalone mode and cannot connect to the actual transcription service.

**To test this function**:
1. Enable `MOCK_TRANSCRIPTION` in the function settings (Valves)
2. Or set `DEVELOPER_MODE` to true if you're a developer user

**To use with real transcription service**:
1. Ensure the healthcare API service is running at the configured URL
2. Set `MOCK_TRANSCRIPTION` to false
3. Click the transcription button again

**Current Settings**:
- Developer Mode: {'✅ Enabled' if self.valves.DEVELOPER_MODE else '❌ Disabled'}
- Mock Transcription: {'✅ Enabled' if self.valves.MOCK_TRANSCRIPTION else '❌ Disabled'}
- PHI Protection: {'✅ Enabled' if self.valves.PHI_PROTECTION_ENABLED else '❌ Disabled'}
- Auto SOAP Generation: {'✅ Enabled' if self.valves.AUTO_SOAP_GENERATION else '❌ Disabled'}
                """
                
                if self.valves.SHOW_MEDICAL_DISCLAIMER:
                    instructions = self.valves.MEDICAL_DISCLAIMER + "\n\n" + instructions
                
                return {"content": instructions}

        except Exception as e:
            error_msg = f"Medical transcription error: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": f"❌ Error: {error_msg}"}
                })
            
            return {
                "error": error_msg,
                "timestamp": datetime.now().isoformat(),
                "user": user_id
            }