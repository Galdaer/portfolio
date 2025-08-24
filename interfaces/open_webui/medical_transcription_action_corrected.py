"""
title: Medical Transcription Action
author: Intelluxe AI
version: 2.0.0
license: MIT
description: Live medical transcription with automatic SOAP note generation for healthcare workflows
"""

import asyncio
import contextlib
import os
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Action:
    """
    Medical Transcription Action

    Provides live medical transcription capabilities with automatic SOAP note generation.
    Includes mock mode for testing and comprehensive healthcare compliance features.
    """

    class Valves(BaseModel):
        """Medical Transcription Configuration Options"""

        # === Healthcare API Configuration ===
        healthcare_websocket_url: str = Field(
            default="ws://localhost:8000",
            description="🌐 Healthcare API WebSocket URL for transcription",
        )
        healthcare_rest_url: str = Field(
            default="http://localhost:8000",
            description="🔗 Healthcare API REST URL",
        )

        # === Transcription Settings ===
        transcription_timeout: int = Field(
            default=300,
            ge=60,
            le=1800,
            description="⏰ Maximum transcription session duration (1-30 minutes)",
        )
        chunk_interval: int = Field(
            default=2,
            ge=1,
            le=10,
            description="🎵 Audio chunk processing interval (1-10 seconds)",
        )
        confidence_threshold: float = Field(
            default=0.85,
            ge=0.1,
            le=1.0,
            description="🎯 Minimum confidence threshold for transcription results",
        )

        # === Medical Compliance ===
        show_medical_disclaimer: bool = Field(
            default=True,
            description="⚠️ Display medical disclaimer to users",
        )
        medical_disclaimer_text: str = Field(
            default="⚠️ **Medical Disclaimer**: This system provides administrative support only, not medical advice. Always consult healthcare professionals for medical decisions.",
            description="📝 Custom medical disclaimer text",
        )
        phi_protection_enabled: bool = Field(
            default=True,
            description="🔒 Enable PHI (Protected Health Information) protection",
        )
        hipaa_compliance_mode: bool = Field(
            default=True,
            description="⚖️ Enable strict HIPAA compliance checks",
        )

        # === Developer & Testing ===
        developer_mode: bool = Field(
            default=False,
            description="🛠️ Enable developer mode with additional features",
        )
        developer_users: list[str] = Field(
            default=["admin", "justin", "jeff"],
            description="👥 List of approved developer users",
        )
        mock_transcription_enabled: bool = Field(
            default=True,
            description="🎭 Use mock transcription for testing (disable for production)",
        )
        debug_logging: bool = Field(
            default=False,
            description="📝 Enable detailed debug logging",
        )

        # === Features ===
        auto_soap_generation: bool = Field(
            default=True,
            description="📋 Automatically generate SOAP notes from transcriptions",
        )
        real_time_display: bool = Field(
            default=True,
            description="🔄 Show transcription progress in real-time",
        )
        session_history_enabled: bool = Field(
            default=True,
            description="📚 Enable session history and analytics",
        )

        # === Performance ===
        max_session_length: int = Field(
            default=10000,
            ge=1000,
            le=50000,
            description="📏 Maximum transcription length in characters",
        )
        connection_retry_attempts: int = Field(
            default=3,
            ge=1,
            le=10,
            description="🔄 Number of connection retry attempts",
        )

    def __init__(self):
        """Initialize the medical transcription action"""
        self.valves = self.Valves()
        self._load_from_environment()

    def _load_from_environment(self):
        """Load configuration from environment variables"""
        env_mappings = {
            "healthcare_websocket_url": "HEALTHCARE_WEBSOCKET_URL",
            "healthcare_rest_url": "HEALTHCARE_REST_URL",
            "transcription_timeout": "TRANSCRIPTION_TIMEOUT",
            "mock_transcription_enabled": "MOCK_TRANSCRIPTION",
            "developer_mode": "DEVELOPER_MODE",
            "debug_logging": "DEBUG_LOGGING",
        }

        for valve_name, env_var in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                current_value = getattr(self.valves, valve_name)
                if isinstance(current_value, bool):
                    setattr(self.valves, valve_name, env_value.lower() in ["true", "1", "yes"])
                elif isinstance(current_value, int):
                    with contextlib.suppress(ValueError):
                        setattr(self.valves, valve_name, int(env_value))
                else:
                    setattr(self.valves, valve_name, env_value)

    def _is_developer_user(self, user: dict | None = None) -> bool:
        """Check if user is a developer"""
        if not user:
            return True  # Default to developer access if user unknown

        user_id = user.get("email", user.get("name", ""))
        return user_id in self.valves.developer_users

    def _generate_mock_transcription_data(self) -> dict[str, Any]:
        """Generate realistic mock transcription data for testing"""
        mock_transcripts = [
            {
                "text": "Patient presents with chief complaint of headache lasting three days. Pain is described as throbbing, located in the temporal region bilaterally. Associated symptoms include mild nausea and photophobia. No fever reported. Patient has a history of migraines. Current medications include ibuprofen as needed. Physical examination reveals blood pressure 120 over 80, pulse 72, temperature 98.6 degrees Fahrenheit. Neurological examination is within normal limits.",
                "soap": {
                    "subjective": "45-year-old patient reports severe headache lasting 3 days. Pain described as throbbing, bilateral temporal location. Associated with mild nausea and light sensitivity. History of migraines. Taking ibuprofen PRN.",
                    "objective": "Vital signs: BP 120/80, HR 72, T 98.6°F. Alert and oriented. Neurological exam normal. No focal deficits noted.",
                    "assessment": "Migraine headache, consistent with patient's previous history. No concerning neurological findings.",
                    "plan": "Continue ibuprofen 600mg q6h PRN. Recommend rest in dark, quiet environment. Follow up if symptoms worsen or persist beyond 48 hours. Consider preventive therapy if frequency increases.",
                },
            },
            {
                "text": "Patient is a 28-year-old female presenting with acute onset chest pain. Pain started approximately two hours ago, described as sharp and stabbing, worsens with deep inspiration. No associated shortness of breath or palpitations. Denies recent travel or surgery. Physical exam shows clear lungs bilaterally, regular heart rate and rhythm, no murmurs. Chest wall is tender to palpation over the left costal margin.",
                "soap": {
                    "subjective": "28-year-old female with acute onset chest pain, sharp and stabbing quality, pleuritic in nature. Started 2 hours ago. Denies SOB, palpitations, recent travel.",
                    "objective": "Appears comfortable. Lungs clear bilaterally. RRR, no murmurs. Chest wall tender over left costal margin. No signs of respiratory distress.",
                    "assessment": "Musculoskeletal chest pain, likely costochondritis. Low probability for pulmonary embolism or cardiac etiology given presentation and exam.",
                    "plan": "NSAIDs for pain relief. Heat/ice therapy. Avoid strenuous activity. Return if pain worsens, develops SOB, or other concerning symptoms. Follow up with PCP if not improving in 1 week.",
                },
            },
        ]

        import random
        selected_case = random.choice(mock_transcripts)

        return {
            "session_id": f"mock_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
            "transcription": {
                "text": selected_case["text"],
                "confidence_score": round(random.uniform(0.85, 0.98), 3),
                "duration_seconds": random.randint(120, 300),
                "word_count": len(selected_case["text"].split()),
                "processing_time_ms": random.randint(800, 2000),
            },
            "soap_note": selected_case["soap"],
            "compliance": {
                "phi_detected": False,
                "hipaa_compliant": True,
                "quality_flags": [],
                "confidence_acceptable": True,
            },
            "metadata": {
                "mock_data": True,
                "transcription_engine": "Mock Engine v2.0",
                "model_version": "healthcare-speech-v1.2",
            },
        }

    async def _simulate_transcription_session(self, __event_emitter__=None) -> dict[str, Any]:
        """Simulate a realistic transcription session for testing"""
        if __event_emitter__:
            # Initial setup
            await __event_emitter__({
                "type": "status",
                "data": {"description": "🎤 Starting transcription session..."},
            })
            await asyncio.sleep(1)

            # Connection phase
            await __event_emitter__({
                "type": "status",
                "data": {"description": f"🔌 Connecting to {self.valves.healthcare_websocket_url}"},
            })
            await asyncio.sleep(1.5)

            # Audio processing
            await __event_emitter__({
                "type": "status",
                "data": {"description": "🎵 Processing audio input..."},
            })
            await asyncio.sleep(2)

            # Real-time transcription simulation
            if self.valves.real_time_display:
                partial_updates = [
                    "Patient presents with...",
                    "Patient presents with chief complaint of...",
                    "Patient presents with chief complaint of headache lasting...",
                    "Patient presents with chief complaint of headache lasting three days...",
                ]

                for update in partial_updates:
                    await __event_emitter__({
                        "type": "message",
                        "data": {"content": f"📝 **Transcribing**: {update}"},
                    })
                    await asyncio.sleep(1)

            # SOAP generation
            if self.valves.auto_soap_generation:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": "🧠 Generating SOAP note from transcription..."},
                })
                await asyncio.sleep(2)

            # Compliance checks
            if self.valves.phi_protection_enabled:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": "🔒 Running PHI protection scan..."},
                })
                await asyncio.sleep(1)

                await __event_emitter__({
                    "type": "status",
                    "data": {"description": "✅ No PHI detected - compliant"},
                })
                await asyncio.sleep(0.5)

        return self._generate_mock_transcription_data()

    def _format_transcription_response(self, transcription_data: dict[str, Any], user: dict | None = None) -> str:
        """Format transcription data into a comprehensive response"""
        lines = []

        # Add medical disclaimer if enabled
        if self.valves.show_medical_disclaimer:
            lines.extend([
                self.valves.medical_disclaimer_text,
                "",
                "---",
                "",
            ])

        # Header
        lines.extend([
            "## 🎙️ Medical Transcription Complete",
            "",
            f"**Session ID**: `{transcription_data.get('session_id', 'N/A')}`",
            f"**Status**: {transcription_data.get('status', 'unknown').title()}",
            f"**Timestamp**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ])

        if user:
            lines.append(f"**Provider**: {user.get('name', 'Unknown')}")

        lines.append("")

        # Transcription section
        transcription = transcription_data.get("transcription", {})
        if transcription:
            lines.extend([
                "### 📝 Transcription Results",
                "",
                f"**Text**: {transcription.get('text', 'No transcription available')}",
                "",
                "**Quality Metrics**:",
                f"- Confidence Score: {transcription.get('confidence_score', 0):.1%}",
                f"- Duration: {transcription.get('duration_seconds', 0)} seconds",
                f"- Word Count: {transcription.get('word_count', 0)} words",
                f"- Processing Time: {transcription.get('processing_time_ms', 0)}ms",
                "",
            ])

        # SOAP Note section
        if self.valves.auto_soap_generation:
            soap_note = transcription_data.get("soap_note", {})
            if soap_note:
                lines.extend([
                    "### 📋 Generated SOAP Note",
                    "",
                    f"**S** (Subjective): {soap_note.get('subjective', 'N/A')}",
                    "",
                    f"**O** (Objective): {soap_note.get('objective', 'N/A')}",
                    "",
                    f"**A** (Assessment): {soap_note.get('assessment', 'N/A')}",
                    "",
                    f"**P** (Plan): {soap_note.get('plan', 'N/A')}",
                    "",
                ])

        # Compliance section
        compliance = transcription_data.get("compliance", {})
        if compliance:
            lines.extend([
                "### 🔒 Compliance & Quality Assurance",
                "",
                f"**PHI Detected**: {'⚠️ Yes - Redacted' if compliance.get('phi_detected', False) else '✅ None detected'}",
                f"**HIPAA Compliant**: {'✅ Yes' if compliance.get('hipaa_compliant', True) else '❌ Issues found'}",
                f"**Quality Status**: {'✅ Acceptable' if compliance.get('confidence_acceptable', True) else '⚠️ Low confidence'}",
            ])

            quality_flags = compliance.get("quality_flags", [])
            if quality_flags:
                lines.append(f"**Quality Flags**: {', '.join(quality_flags)}")
            else:
                lines.append("**Quality Flags**: ✅ None")

            lines.append("")

        # Metadata (for developers)
        if self.valves.developer_mode:
            metadata = transcription_data.get("metadata", {})
            if metadata:
                lines.extend([
                    "### 🛠️ Technical Metadata (Developer Mode)",
                    "",
                    f"**Mock Data**: {'✅ Yes' if metadata.get('mock_data', False) else '❌ No'}",
                    f"**Engine**: {metadata.get('transcription_engine', 'Unknown')}",
                    f"**Model**: {metadata.get('model_version', 'Unknown')}",
                    "",
                ])

        return "\n".join(lines)

    async def action(
        self,
        body: dict,
        __user__: dict | None = None,
        __event_emitter__=None,
    ) -> dict | None:
        """
        Execute the medical transcription action

        Args:
            body: Request body from Open WebUI
            __user__: User information
            __event_emitter__: Event emitter for real-time updates

        Returns:
            dict: Transcription results and SOAP note
        """
        try:
            # Get user information
            user_name = __user__.get("name", "Unknown Provider") if __user__ else "Unknown Provider"
            is_developer = self._is_developer_user(__user__)

            # Initial status update
            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": f"🎙️ Initializing medical transcription for {user_name}..."},
                })

            # Determine transcription mode
            use_mock = (
                self.valves.mock_transcription_enabled or
                (self.valves.developer_mode and is_developer)
            )

            if use_mock:
                # Mock transcription for testing
                if __event_emitter__:
                    await __event_emitter__({
                        "type": "status",
                        "data": {"description": "🎭 Running in mock transcription mode"},
                    })

                transcription_data = await self._simulate_transcription_session(__event_emitter__)
                response_content = self._format_transcription_response(transcription_data, __user__)

                if __event_emitter__:
                    await __event_emitter__({
                        "type": "status",
                        "data": {"description": "✅ Mock transcription completed successfully!"},
                    })

                return {
                    "content": response_content,
                    "transcription_data": transcription_data,
                }

            # Production mode - would connect to real healthcare API
            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": f"🔌 Attempting connection to {self.valves.healthcare_websocket_url}"},
                })

            # For now, provide instructions since we can't connect to real service
            instructions_content = f"""
## 🎙️ Medical Transcription Service

### ⚠️ Production Mode Configuration Required

**Current Settings**:
- Healthcare API: `{self.valves.healthcare_websocket_url}`
- Timeout: {self.valves.transcription_timeout} seconds
- Confidence Threshold: {self.valves.confidence_threshold:.1%}

### 🚀 To Start Live Transcription:

1. **Ensure Healthcare API is Running**:
   - Verify the healthcare API service is accessible at `{self.valves.healthcare_websocket_url}`
   - Check that the transcription endpoints are available

2. **Test Connection**:
   - Enable **Mock Transcription** in function settings to test the interface
   - Or enable **Developer Mode** if you're a developer user

3. **Configure Settings**:
   - Click the ⚙️ icon next to this function in Workspace → Functions
   - Adjust the **Valves** as needed for your environment

### 🧪 Testing Options:
- **Mock Mode**: Enable `mock_transcription_enabled` for realistic test data
- **Developer Mode**: Enable `developer_mode` for additional debugging features

### 🔒 Compliance Features:
- **PHI Protection**: {'✅ Enabled' if self.valves.phi_protection_enabled else '❌ Disabled'}
- **HIPAA Mode**: {'✅ Enabled' if self.valves.hipaa_compliance_mode else '❌ Disabled'}
- **Auto SOAP**: {'✅ Enabled' if self.valves.auto_soap_generation else '❌ Disabled'}

---
*Configure the valves and try again, or enable mock mode for testing.*
                """.strip()

            if self.valves.show_medical_disclaimer:
                instructions_content = self.valves.medical_disclaimer_text + "\n\n---\n\n" + instructions_content

            return {"content": instructions_content}

        except Exception as e:
            error_msg = f"Medical transcription error: {str(e)}"

            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": f"❌ {error_msg}"},
                })

            return {
                "content": f"""
## ❌ Transcription Error

**Error**: {error_msg}
**Timestamp**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**User**: {__user__.get('name', 'Unknown') if __user__ else 'Unknown'}

### 🔧 Troubleshooting:
1. Check that the Healthcare API is running
2. Verify WebSocket URL configuration
3. Enable mock mode for testing
4. Check function logs for detailed error information

### 🆘 Support:
- Enable **Debug Logging** in function settings
- Enable **Mock Transcription** to test the interface
- Contact system administrator if issues persist
                """.strip(),
            }
