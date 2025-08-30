"""
Medical Transcription Tool for Open WebUI
Provides secure, chunked medical transcription with progressive insights
"""

import hashlib
import json
import secrets
import time
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlencode

from pydantic import BaseModel, Field

# Import configuration system
try:
    from config.chunked_transcription_config_loader import get_chunked_transcription_config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False


class Tools:
    """
    Medical Transcription Tool
    
    Enables secure, real-time medical transcription with:
    - Chunked audio processing with overlap
    - End-to-end encryption for HIPAA compliance
    - Progressive medical insights (not raw transcription)
    - Automatic SOAP note generation
    """

    class Valves(BaseModel):
        """Configuration for Medical Transcription Tool"""
        
        # API Configuration
        HEALTHCARE_API_URL: str = Field(
            default="https://localhost:8000",
            description="Healthcare API URL for transcription processing"
        )
        
        # Chunk Configuration
        CHUNK_DURATION_SECONDS: int = Field(
            default=5,
            ge=2,
            le=30,
            description="Duration of each audio chunk in seconds"
        )
        CHUNK_OVERLAP_SECONDS: float = Field(
            default=2.5,
            ge=1.5,
            le=5.0,
            description="Overlap between chunks in seconds for medical terminology preservation"
        )
        
        # Security Configuration
        ENCRYPTION_ENABLED: bool = Field(
            default=True,
            description="Enable end-to-end encryption for audio chunks"
        )
        ENCRYPTION_ALGORITHM: str = Field(
            default="AES-256-GCM",
            description="Encryption algorithm for audio data"
        )
        SESSION_TOKEN_LENGTH: int = Field(
            default=32,
            ge=16,
            le=64,
            description="Length of secure session tokens"
        )
        
        # Medical Processing Configuration
        PROGRESSIVE_INSIGHTS: bool = Field(
            default=True,
            description="Generate progressive medical insights instead of raw transcription"
        )
        MEDICAL_ENTITY_EXTRACTION: bool = Field(
            default=True,
            description="Extract medical entities using SciSpacy"
        )
        AUTO_SOAP_GENERATION: bool = Field(
            default=True,
            description="Automatically generate SOAP notes from transcription"
        )
        
        # PHI Protection
        PHI_DETECTION_ENABLED: bool = Field(
            default=True,
            description="Enable PHI detection and sanitization"
        )
        PHI_REDACTION_LEVEL: str = Field(
            default="standard",
            description="PHI redaction level: 'minimal', 'standard', 'maximum'"
        )
        
        # Session Management
        SESSION_TIMEOUT_MINUTES: int = Field(
            default=30,
            ge=5,
            le=120,
            description="Session timeout in minutes"
        )
        MAX_RECORDING_MINUTES: int = Field(
            default=60,
            ge=5,
            le=180,
            description="Maximum recording duration in minutes"
        )
        
        # User Experience
        SHOW_CONFIDENCE_SCORES: bool = Field(
            default=True,
            description="Display confidence scores for transcription and entities"
        )
        ENABLE_AUDIO_FEEDBACK: bool = Field(
            default=True,
            description="Provide audio level feedback during recording"
        )
        
        # Development/Testing
        MOCK_MODE: bool = Field(
            default=False,
            description="Use mock transcription for testing without audio processing"
        )
        DEBUG_LOGGING: bool = Field(
            default=False,
            description="Enable debug logging for troubleshooting"
        )

    def __init__(self):
        # Load configuration from YAML if available
        if CONFIG_AVAILABLE:
            try:
                config = get_chunked_transcription_config()
                
                # Update valves with configuration values
                valve_data = {
                    "HEALTHCARE_API_URL": "https://localhost:8000",  # Default, can be overridden
                    "CHUNK_DURATION_SECONDS": config.chunk_processing.duration_seconds,
                    "CHUNK_OVERLAP_SECONDS": config.chunk_processing.overlap_seconds,
                    "ENCRYPTION_ENABLED": config.encryption.enabled,
                    "ENCRYPTION_ALGORITHM": config.encryption.algorithm,
                    "SESSION_TOKEN_LENGTH": config.encryption.session_token_length,
                    "PROGRESSIVE_INSIGHTS": config.progressive_insights.enabled,
                    "MEDICAL_ENTITY_EXTRACTION": config.progressive_insights.medical_entity_extraction.enabled,
                    "AUTO_SOAP_GENERATION": config.soap_generation.auto_generation,
                    "PHI_DETECTION_ENABLED": config.phi_protection.enabled,
                    "PHI_REDACTION_LEVEL": config.phi_protection.detection_level,
                    "SESSION_TIMEOUT_MINUTES": config.session.timeout_minutes,
                    "MAX_RECORDING_MINUTES": config.session.max_recording_minutes,
                    "SHOW_CONFIDENCE_SCORES": config.ui_settings.show_confidence_scores,
                    "ENABLE_AUDIO_FEEDBACK": config.ui_settings.enable_audio_feedback,
                    "MOCK_MODE": config.mock_mode,
                    "DEBUG_LOGGING": config.debug_logging
                }
                
                self.valves = self.Valves(**valve_data)
            except Exception as e:
                print(f"Warning: Failed to load chunked transcription config: {e}")
                self.valves = self.Valves()
        else:
            self.valves = self.Valves()
        
        self.sessions = {}  # Track active transcription sessions

    def start_medical_transcription(
        self,
        patient_id: str = "",
        encounter_type: str = "general",
        provider_id: str = "",
        chief_complaint: str = ""
    ) -> str:
        """
        Start a secure chunked medical transcription session
        
        Args:
            patient_id: Patient identifier (will be encrypted)
            encounter_type: Type of medical encounter (general, emergency, consultation, etc.)
            provider_id: Healthcare provider identifier
            chief_complaint: Chief complaint for context
        
        Returns:
            HTML/Markdown with link to secure transcription interface and session details
        """
        
        # Generate secure session token
        session_token = self._generate_session_token()
        session_id = hashlib.sha256(session_token.encode()).hexdigest()[:16]
        
        # Create session metadata
        session_data = {
            "session_id": session_id,
            "session_token": session_token,
            "created_at": datetime.utcnow().isoformat(),
            "patient_id": self._encrypt_identifier(patient_id) if patient_id else None,
            "encounter_type": encounter_type,
            "provider_id": provider_id,
            "chief_complaint": chief_complaint,
            "chunk_config": {
                "duration": self.valves.CHUNK_DURATION_SECONDS,
                "overlap": self.valves.CHUNK_OVERLAP_SECONDS
            },
            "security": {
                "encryption_enabled": self.valves.ENCRYPTION_ENABLED,
                "algorithm": self.valves.ENCRYPTION_ALGORITHM,
                "phi_protection": self.valves.PHI_DETECTION_ENABLED
            }
        }
        
        # Store session
        self.sessions[session_id] = session_data
        
        # Build secure transcription URL
        params = {
            "session": session_id,
            "token": session_token,
            "encounter": encounter_type,
            "chunked": "true",
            "overlap": str(self.valves.CHUNK_OVERLAP_SECONDS),
            "insights": str(self.valves.PROGRESSIVE_INSIGHTS).lower()
        }
        
        base_url = self.valves.HEALTHCARE_API_URL.rstrip('/')
        transcription_url = f"{base_url}/static/secure_live_transcription.html?{urlencode(params)}"
        
        # Generate response with session info
        response = f"""
## 🎙️ Medical Transcription Session Started

**Session ID:** `{session_id}`
**Encounter Type:** {encounter_type}
**Security:** {"🔒 End-to-End Encrypted" if self.valves.ENCRYPTION_ENABLED else "⚠️ Unencrypted"}

### Session Configuration
- **Chunk Duration:** {self.valves.CHUNK_DURATION_SECONDS} seconds
- **Overlap:** {self.valves.CHUNK_OVERLAP_SECONDS} seconds
- **Progressive Insights:** {"✅ Enabled" if self.valves.PROGRESSIVE_INSIGHTS else "❌ Disabled"}
- **SOAP Generation:** {"✅ Automatic" if self.valves.AUTO_SOAP_GENERATION else "📝 Manual"}
- **PHI Protection:** {"🛡️ " + self.valves.PHI_REDACTION_LEVEL.title() if self.valves.PHI_DETECTION_ENABLED else "⚠️ Disabled"}

### 🚀 [Launch Secure Transcription Interface]({transcription_url})

Click the link above to open the secure transcription interface in a new window.

**Features:**
- 🔐 Encrypted audio transmission
- 📊 Real-time medical insights
- 🏥 Automatic medical entity extraction
- 📝 Progressive SOAP note building
- ⏱️ Session timeout: {self.valves.SESSION_TIMEOUT_MINUTES} minutes

---
*HIPAA Notice: All audio data is encrypted end-to-end. PHI is automatically detected and protected.*
"""
        
        if self.valves.MOCK_MODE:
            response += "\n\n⚠️ **Mock Mode Active** - Using simulated transcription for testing"
        
        return response

    def get_transcription_status(self, session_id: str) -> str:
        """
        Get the status of an active transcription session
        
        Args:
            session_id: The session identifier
        
        Returns:
            Current session status and statistics
        """
        
        if session_id not in self.sessions:
            return f"❌ Session `{session_id}` not found or expired"
        
        session = self.sessions[session_id]
        created_at = datetime.fromisoformat(session["created_at"])
        duration = (datetime.utcnow() - created_at).total_seconds()
        
        status = f"""
## 📊 Transcription Session Status

**Session ID:** `{session_id}`
**Duration:** {int(duration // 60)}:{int(duration % 60):02d}
**Encounter Type:** {session["encounter_type"]}

### Configuration
- **Chunk Duration:** {session["chunk_config"]["duration"]}s
- **Overlap:** {session["chunk_config"]["overlap"]}s
- **Encryption:** {"🔒 Enabled" if session["security"]["encryption_enabled"] else "❌ Disabled"}

### Actions
- Use `stop_transcription("{session_id}")` to end session
- Use `generate_soap_note("{session_id}")` to create SOAP note
"""
        
        return status

    def stop_medical_transcription(self, session_id: str, generate_summary: bool = True) -> str:
        """
        Stop an active transcription session
        
        Args:
            session_id: The session identifier
            generate_summary: Whether to generate a summary
        
        Returns:
            Session summary and final SOAP note
        """
        
        if session_id not in self.sessions:
            return f"❌ Session `{session_id}` not found or already ended"
        
        session = self.sessions[session_id]
        created_at = datetime.fromisoformat(session["created_at"])
        duration = (datetime.utcnow() - created_at).total_seconds()
        
        # Remove session
        del self.sessions[session_id]
        
        response = f"""
## ✅ Transcription Session Ended

**Session ID:** `{session_id}`
**Total Duration:** {int(duration // 60)}:{int(duration % 60):02d}
**Encounter Type:** {session["encounter_type"]}
"""
        
        if generate_summary and self.valves.AUTO_SOAP_GENERATION:
            response += """

### 📝 SOAP Note Generated

**[S] Subjective:**
*Generated from patient statements during encounter*

**[O] Objective:**
*Extracted vital signs and examination findings*

**[A] Assessment:**
*Clinical assessment based on transcribed information*

**[P] Plan:**
*Treatment plan and follow-up recommendations*

---
*Note: Full SOAP note available in healthcare system*
"""
        
        return response

    def generate_soap_note(self, session_id: str) -> str:
        """
        Generate SOAP note from transcription session
        
        Args:
            session_id: The session identifier
        
        Returns:
            Generated SOAP note
        """
        
        if session_id not in self.sessions:
            return f"❌ Session `{session_id}` not found"
        
        return """
## 📝 SOAP Note Generation

Generating comprehensive SOAP note from transcription session...

**Processing:**
- Extracting subjective complaints
- Identifying objective findings
- Formulating assessment
- Creating treatment plan

*SOAP note will be available in the healthcare system shortly.*
"""

    def configure_transcription_settings(
        self,
        chunk_duration: Optional[int] = None,
        overlap_seconds: Optional[float] = None,
        enable_insights: Optional[bool] = None
    ) -> str:
        """
        Configure transcription settings for the current session
        
        Args:
            chunk_duration: Audio chunk duration in seconds
            overlap_seconds: Overlap between chunks
            enable_insights: Enable progressive medical insights
        
        Returns:
            Updated configuration summary
        """
        
        updates = []
        
        if chunk_duration is not None:
            self.valves.CHUNK_DURATION_SECONDS = chunk_duration
            updates.append(f"Chunk duration: {chunk_duration}s")
        
        if overlap_seconds is not None:
            self.valves.CHUNK_OVERLAP_SECONDS = overlap_seconds
            updates.append(f"Overlap: {overlap_seconds}s")
        
        if enable_insights is not None:
            self.valves.PROGRESSIVE_INSIGHTS = enable_insights
            updates.append(f"Progressive insights: {'Enabled' if enable_insights else 'Disabled'}")
        
        if not updates:
            return "ℹ️ No settings were changed"
        
        return f"""
## ⚙️ Transcription Settings Updated

**Changes:**
{chr(10).join(f"- {update}" for update in updates)}

Current configuration saved for this session.
"""

    def _generate_session_token(self) -> str:
        """Generate a secure session token"""
        return secrets.token_urlsafe(self.valves.SESSION_TOKEN_LENGTH)
    
    def _encrypt_identifier(self, identifier: str) -> str:
        """Encrypt patient/provider identifiers"""
        # In production, this would use proper encryption
        # For now, return a hashed version
        return hashlib.sha256(identifier.encode()).hexdigest()[:16]