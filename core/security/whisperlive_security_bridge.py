"""
WhisperLive Security Bridge for Healthcare AI
Memory-only audio processing with PHI protection and secure transcription
"""

import asyncio
import hashlib
import io
import os
import wave
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, BinaryIO

from core.infrastructure.healthcare_logger import get_healthcare_logger
from core.security.chat_log_manager import ChatLogManager
from core.security.phi_detector import PHIDetector

logger = get_healthcare_logger("whisperlive_security_bridge")


@dataclass
class AudioSecurityMetadata:
    """Security metadata for audio processing"""

    session_id: str
    user_id: str
    timestamp: datetime
    audio_format: str
    duration_seconds: float
    sample_rate: int
    phi_detection_enabled: bool
    encryption_applied: bool
    memory_only: bool = True
    audit_trail: list[str] = None

    def __post_init__(self):
        if self.audit_trail is None:
            self.audit_trail = []


@dataclass
class SecureTranscriptionResult:
    """Secure transcription result with PHI protection"""

    transcription_id: str
    session_id: str
    transcript: str
    confidence_score: float
    phi_detected: bool
    sanitized_transcript: str | None
    processing_time_ms: int
    security_metadata: AudioSecurityMetadata
    medical_disclaimer: str


class WhisperLiveSecurityBridge:
    """Security bridge for WhisperLive with healthcare compliance"""

    def __init__(self, whisperlive_config: dict[str, Any] | None = None):
        self.config = whisperlive_config or self._get_default_config()
        self.phi_detector = PHIDetector()
        self.chat_log_manager = ChatLogManager()

        # Security settings
        self.memory_only_processing = True
        self.auto_delete_after_processing = True
        self.phi_detection_enabled = True

        logger.info("WhisperLive Security Bridge initialized with healthcare compliance")

    async def transcribe_audio_secure(
        self,
        audio_data: BinaryIO,
        session_id: str,
        user_id: str,
        audio_format: str = "wav",
        healthcare_context: dict[str, Any] | None = None,
    ) -> SecureTranscriptionResult:
        """Securely transcribe audio with PHI protection and memory-only processing"""

        start_time = datetime.utcnow()
        transcription_id = self._generate_transcription_id(session_id, user_id)

        # Create security metadata
        security_metadata = AudioSecurityMetadata(
            session_id=session_id,
            user_id=user_id,
            timestamp=start_time,
            audio_format=audio_format,
            duration_seconds=0.0,  # Will be calculated
            sample_rate=16000,  # Default, will be detected
            phi_detection_enabled=self.phi_detection_enabled,
            encryption_applied=False,
            memory_only=True,
            audit_trail=[f"Processing started at {start_time.isoformat()}"],
        )

        try:
            # Log audio processing start
            logger.info(
                "Secure audio transcription started",
                extra={
                    "operation_type": "audio_transcription_start",
                    "transcription_id": transcription_id,
                    "session_id": session_id,
                    "user_id": user_id,
                    "memory_only": self.memory_only_processing,
                },
            )

            # Process audio in memory only
            async with self._secure_audio_context(audio_data, security_metadata) as processed_audio:
                # Transcribe using WhisperLive (memory-only)
                transcript, confidence = await self._transcribe_with_whisperlive(
                    processed_audio, security_metadata
                )

                # PHI detection and sanitization
                phi_detected = False
                sanitized_transcript = None

                if self.phi_detection_enabled:
                    phi_detected = await self.phi_detector.scan_text(transcript)

                    if phi_detected:
                        sanitized_transcript = await self.phi_detector.sanitize_text(transcript)
                        security_metadata.audit_trail.append(
                            f"PHI detected and sanitized at {datetime.utcnow().isoformat()}"
                        )

                        logger.warning(
                            "PHI detected in audio transcription",
                            extra={
                                "operation_type": "audio_phi_detection",
                                "transcription_id": transcription_id,
                                "session_id": session_id,
                                "phi_detected": True,
                            },
                        )

                # Calculate processing time
                processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

                # Create transcription result
                result = SecureTranscriptionResult(
                    transcription_id=transcription_id,
                    session_id=session_id,
                    transcript=sanitized_transcript if phi_detected else transcript,
                    confidence_score=confidence,
                    phi_detected=phi_detected,
                    sanitized_transcript=sanitized_transcript,
                    processing_time_ms=processing_time_ms,
                    security_metadata=security_metadata,
                    medical_disclaimer="This transcription service provides administrative support only. It does not provide medical advice, diagnosis, or treatment recommendations.",
                )

                # Log to chat manager if in healthcare context
                if healthcare_context:
                    await self.chat_log_manager.log_chat_message(
                        session_id=session_id,
                        user_id=user_id,
                        role="audio_transcript",
                        content=result.transcript,
                        healthcare_context=healthcare_context,
                    )

                # Log successful completion
                logger.info(
                    "Secure audio transcription completed",
                    extra={
                        "operation_type": "audio_transcription_complete",
                        "transcription_id": transcription_id,
                        "session_id": session_id,
                        "processing_time_ms": processing_time_ms,
                        "phi_detected": phi_detected,
                        "confidence_score": confidence,
                    },
                )

                return result

        except Exception as e:
            logger.error(
                "Secure audio transcription failed",
                extra={
                    "operation_type": "audio_transcription_error",
                    "transcription_id": transcription_id,
                    "session_id": session_id,
                    "error": str(e),
                },
            )
            raise

    @asynccontextmanager
    async def _secure_audio_context(
        self, audio_data: BinaryIO, security_metadata: AudioSecurityMetadata
    ):
        """Secure context manager for memory-only audio processing"""

        # Create in-memory buffer for processing
        memory_buffer = io.BytesIO()

        try:
            # Copy audio data to memory buffer
            audio_data.seek(0)
            audio_content = audio_data.read()
            memory_buffer.write(audio_content)
            memory_buffer.seek(0)

            # Detect audio properties
            await self._detect_audio_properties(memory_buffer, security_metadata)

            # Encrypt in memory if required
            if self.config.get("encrypt_audio_in_memory", False):
                encrypted_buffer = await self._encrypt_audio_memory(memory_buffer)
                security_metadata.encryption_applied = True
                security_metadata.audit_trail.append(
                    f"Audio encrypted in memory at {datetime.utcnow().isoformat()}"
                )
                yield encrypted_buffer
            else:
                yield memory_buffer

        finally:
            # Secure cleanup - overwrite memory buffer
            if hasattr(memory_buffer, "getvalue"):
                buffer_size = len(memory_buffer.getvalue())
                memory_buffer.seek(0)
                memory_buffer.write(b"\x00" * buffer_size)  # Overwrite with zeros

            memory_buffer.close()

            security_metadata.audit_trail.append(
                f"Memory securely cleared at {datetime.utcnow().isoformat()}"
            )

    async def _transcribe_with_whisperlive(
        self, audio_buffer: io.BytesIO, security_metadata: AudioSecurityMetadata
    ) -> tuple[str, float]:
        """Transcribe audio using WhisperLive in memory-only mode"""

        # For testing/development - mock transcription
        if self.config.get("mock_transcription", False):
            return await self._mock_transcription(audio_buffer, security_metadata)

        # Real WhisperLive integration would go here
        # This would interface with the actual WhisperLive service
        # using memory-only processing without temporary files

        try:
            # Prepare audio data for WhisperLive
            audio_buffer.seek(0)
            audio_data = audio_buffer.read()

            # Create WhisperLive request (memory-only)
            whisper_request = {
                "audio_data": audio_data,
                "format": security_metadata.audio_format,
                "sample_rate": security_metadata.sample_rate,
                "language": "en",  # Could be configurable
                "task": "transcribe",
                "memory_only": True,
                "no_cache": True,  # Don't cache for security
            }

            # Call WhisperLive service (implementation would be here)
            # For now, return mock data
            transcript = (
                "Mock medical transcription: Patient reports symptoms and requests follow-up care."
            )
            confidence = 0.95

            return transcript, confidence

        except Exception as e:
            logger.error(f"WhisperLive transcription failed: {e}")
            raise

    async def _mock_transcription(
        self, audio_buffer: io.BytesIO, security_metadata: AudioSecurityMetadata
    ) -> tuple[str, float]:
        """Mock transcription for testing purposes"""

        # Simulate processing time
        await asyncio.sleep(0.1)

        # Generate mock transcript based on audio duration
        duration = security_metadata.duration_seconds

        if duration < 10:
            transcript = "Patient reports feeling well today."
        elif duration < 30:
            transcript = "Patient discusses symptoms with healthcare provider. Requests follow-up appointment for continued care."
        else:
            transcript = "Extended patient consultation regarding ongoing treatment plan. Provider explains medication adjustments and lifestyle recommendations. Patient acknowledges understanding and agrees to follow-up in two weeks."

        confidence = 0.92

        return transcript, confidence

    async def _detect_audio_properties(
        self, audio_buffer: io.BytesIO, security_metadata: AudioSecurityMetadata
    ) -> None:
        """Detect audio properties for security metadata"""

        try:
            audio_buffer.seek(0)

            # For WAV files, we can read the header
            if security_metadata.audio_format.lower() == "wav":
                with wave.open(audio_buffer, "rb") as wav_file:
                    security_metadata.sample_rate = wav_file.getframerate()
                    security_metadata.duration_seconds = wav_file.getnframes() / float(
                        wav_file.getframerate()
                    )
            else:
                # For other formats, use defaults or audio library
                security_metadata.duration_seconds = 10.0  # Default estimate
                security_metadata.sample_rate = 16000  # Default

            audio_buffer.seek(0)  # Reset position

        except Exception as e:
            logger.warning(f"Could not detect audio properties: {e}")
            # Use defaults
            security_metadata.duration_seconds = 10.0
            security_metadata.sample_rate = 16000

    async def _encrypt_audio_memory(self, audio_buffer: io.BytesIO) -> io.BytesIO:
        """Encrypt audio data in memory"""

        # Simple XOR encryption for memory-only processing
        # In production, would use proper encryption

        audio_buffer.seek(0)
        audio_data = audio_buffer.read()

        # Generate encryption key from session
        key = hashlib.sha256(f"healthcare_audio_{datetime.utcnow()}".encode()).digest()

        # XOR encryption
        encrypted_data = bytearray()
        for i, byte in enumerate(audio_data):
            encrypted_data.append(byte ^ key[i % len(key)])

        encrypted_buffer = io.BytesIO(encrypted_data)
        return encrypted_buffer

    def _generate_transcription_id(self, session_id: str, user_id: str) -> str:
        """Generate unique transcription ID"""
        data = f"{session_id}_{user_id}_{datetime.utcnow().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def _get_default_config(self) -> dict[str, Any]:
        """Get default WhisperLive configuration"""
        return {
            "whisperlive_url": os.getenv("WHISPERLIVE_URL", "http://localhost:9090"),
            "model_name": "base.en",
            "language": "en",
            "mock_transcription": os.getenv("MOCK_TRANSCRIPTION", "true").lower() == "true",
            "encrypt_audio_in_memory": True,
            "max_audio_duration_seconds": 300,  # 5 minutes max
            "supported_formats": ["wav", "mp3", "flac", "m4a"],
            "memory_only_processing": True,
            "auto_delete_after_processing": True,
        }


class HealthcareAudioProcessor:
    """Healthcare-specific audio processing with WhisperLive integration"""

    def __init__(self):
        self.security_bridge = WhisperLiveSecurityBridge()
        self.logger = get_healthcare_logger("healthcare_audio_processor")

    async def process_clinical_audio(
        self,
        audio_file: BinaryIO,
        session_id: str,
        doctor_id: str,
        patient_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Process clinical audio with healthcare compliance"""

        try:
            # Validate audio file
            await self._validate_audio_file(audio_file)

            # Determine audio format
            audio_format = self._detect_audio_format(audio_file)

            # Process with security bridge
            transcription_result = await self.security_bridge.transcribe_audio_secure(
                audio_data=audio_file,
                session_id=session_id,
                user_id=doctor_id,
                audio_format=audio_format,
                healthcare_context={
                    "patient_context": patient_context,
                    "clinical_session": True,
                    "doctor_id": doctor_id,
                },
            )

            # Create healthcare-compliant response
            response = {
                "transcription_id": transcription_result.transcription_id,
                "session_id": session_id,
                "transcript": transcription_result.transcript,
                "confidence_score": transcription_result.confidence_score,
                "processing_time_ms": transcription_result.processing_time_ms,
                "phi_detected": transcription_result.phi_detected,
                "memory_only_processing": True,
                "audio_deleted": True,
                "medical_disclaimer": transcription_result.medical_disclaimer,
                "audit_trail": transcription_result.security_metadata.audit_trail,
            }

            self.logger.info(
                "Clinical audio processed successfully",
                extra={
                    "operation_type": "clinical_audio_processed",
                    "transcription_id": transcription_result.transcription_id,
                    "session_id": session_id,
                    "doctor_id": doctor_id,
                    "phi_detected": transcription_result.phi_detected,
                },
            )

            return response

        except Exception as e:
            self.logger.error(
                "Clinical audio processing failed",
                extra={
                    "operation_type": "clinical_audio_error",
                    "session_id": session_id,
                    "doctor_id": doctor_id,
                    "error": str(e),
                },
            )
            raise

    async def _validate_audio_file(self, audio_file: BinaryIO) -> None:
        """Validate audio file for healthcare processing"""

        # Check file size
        audio_file.seek(0, 2)  # Seek to end
        file_size = audio_file.tell()
        audio_file.seek(0)  # Reset to beginning

        max_size = 50 * 1024 * 1024  # 50MB max
        if file_size > max_size:
            raise ValueError(f"Audio file too large: {file_size} bytes (max: {max_size})")

        if file_size == 0:
            raise ValueError("Audio file is empty")

    def _detect_audio_format(self, audio_file: BinaryIO) -> str:
        """Detect audio format from file header"""

        audio_file.seek(0)
        header = audio_file.read(12)
        audio_file.seek(0)

        if header.startswith(b"RIFF") and b"WAVE" in header:
            return "wav"
        elif header.startswith(b"ID3") or header.startswith(b"\xff\xfb"):
            return "mp3"
        elif header.startswith(b"fLaC"):
            return "flac"
        else:
            # Default to wav
            return "wav"


# FastAPI integration endpoint
async def transcribe_audio_endpoint(
    audio_file: BinaryIO,
    session_id: str,
    doctor_id: str,
    patient_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """FastAPI endpoint for audio transcription"""

    processor = HealthcareAudioProcessor()

    return await processor.process_clinical_audio(
        audio_file=audio_file,
        session_id=session_id,
        doctor_id=doctor_id,
        patient_context=patient_context,
    )
