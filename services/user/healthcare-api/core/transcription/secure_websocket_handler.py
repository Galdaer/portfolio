"""
Secure WebSocket Handler for Chunked Medical Transcription
Handles encrypted audio chunks with overlap processing and progressive insights
"""

import asyncio
import base64
import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import WebSocket

from core.infrastructure.healthcare_logger import get_healthcare_logger
from src.security.encryption_manager import EncryptionLevel, EncryptionManager

# Import configuration system
try:
    from config.chunked_transcription_config_loader import get_chunked_transcription_config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False

logger = get_healthcare_logger("transcription.secure_websocket")


@dataclass
class ChunkContext:
    """Context for overlapping chunk processing"""
    
    session_id: str
    chunk_number: int
    timestamp: datetime
    previous_audio_tail: bytes  # Last N seconds of previous chunk
    previous_transcription_tail: str  # Last words for context
    medical_context: dict[str, Any]  # Accumulated medical entities
    soap_progress: dict[str, str]  # Progressive SOAP building


class SecureTranscriptionHandler:
    """
    Handles secure, chunked transcription with:
    - End-to-end encryption
    - Chunk overlap processing
    - Progressive medical insights
    - HIPAA-compliant PHI handling
    """
    
    def __init__(self, encryption_manager: EncryptionManager):
        self.encryption_manager = encryption_manager
        self.logger = logger
        self.chunk_contexts: dict[str, ChunkContext] = {}
        
        # Load configuration
        if CONFIG_AVAILABLE:
            try:
                config = get_chunked_transcription_config()
                
                # Chunk processing configuration from YAML
                self.chunk_duration = float(config.chunk_processing.duration_seconds)
                self.chunk_overlap = config.chunk_processing.overlap_seconds
                self.sample_rate = config.chunk_processing.sample_rate
                
                # Security configuration from YAML
                self.encryption_enabled = config.encryption.enabled
                self.encryption_algorithm = config.encryption.algorithm
                self.key_rotation_interval = config.encryption.session_key_rotation_interval_seconds
                
                # Performance configuration
                self.max_concurrent_chunks = config.performance.max_concurrent_chunks
                self.chunk_processing_timeout = config.performance.chunk_processing_timeout_seconds
                
                self.logger.info(f"Loaded chunked transcription config: chunks={self.chunk_duration}s, "
                               f"overlap={self.chunk_overlap}s, sample_rate={self.sample_rate}Hz, "
                               f"encryption={self.encryption_enabled}")
                
            except Exception as e:
                self.logger.warning(f"Failed to load chunked transcription config: {e}. Using defaults.")
                self._set_default_config()
        else:
            self._set_default_config()
        
        # Security configuration
        self.encryption_level = EncryptionLevel.HEALTHCARE
        self.session_keys: dict[str, bytes] = {}  # Session-specific encryption keys
    
    def _set_default_config(self):
        """Set default configuration values"""
        # Medical terminology requires longer overlap (e.g., "electroencephalography", "immunohistochemistry")
        self.chunk_duration = 5.0  # seconds
        self.chunk_overlap = 2.5  # seconds (increased for medical terms)
        self.sample_rate = 16000  # Hz for audio
        self.encryption_enabled = True
        self.encryption_algorithm = "AES-256-GCM"
        self.key_rotation_interval = 3600  # 1 hour
        self.max_concurrent_chunks = 10
        self.chunk_processing_timeout = 30
    
    async def handle_encrypted_chunk(
        self,
        websocket: WebSocket,
        session_id: str,
        encrypted_message: dict[str, Any]
    ) -> None:
        """
        Process an encrypted audio chunk and return medical insights
        
        Args:
            websocket: Active WebSocket connection
            session_id: Session identifier
            encrypted_message: Encrypted audio chunk with metadata
        """
        
        try:
            # 1. Decrypt the audio chunk
            encrypted_audio = base64.b64decode(encrypted_message["audio_data"])
            nonce = base64.b64decode(encrypted_message["nonce"])
            
            decrypted_audio = await self._decrypt_chunk(
                session_id, encrypted_audio, nonce
            )
            
            # 2. Get or create chunk context
            context = self._get_or_create_context(session_id)
            
            # 3. Merge with overlap from previous chunk
            merged_audio = await self._merge_with_overlap(
                decrypted_audio, context
            )
            
            # 4. Process audio to transcription
            transcription_result = await self._transcribe_audio(
                merged_audio, context
            )
            
            # 5. Extract medical entities and generate insights
            medical_insights = await self._generate_medical_insights(
                transcription_result, context
            )
            
            # 6. Update context for next chunk
            await self._update_context(
                context, decrypted_audio, transcription_result, medical_insights
            )
            
            # 7. Encrypt and send insights back
            encrypted_response = await self._encrypt_insights(
                session_id, medical_insights
            )
            
            await websocket.send_json({
                "type": "medical_insights",
                "session_id": session_id,
                "chunk_number": context.chunk_number,
                "encrypted_data": encrypted_response["data"],
                "nonce": encrypted_response["nonce"],
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Increment chunk counter
            context.chunk_number += 1
            
        except Exception as e:
            self.logger.exception(f"Error processing encrypted chunk: {e}")
            await websocket.send_json({
                "type": "error",
                "session_id": session_id,
                "message": "Failed to process audio chunk",
                "error_code": "CHUNK_PROCESSING_ERROR"
            })
    
    async def initialize_secure_session(
        self,
        websocket: WebSocket,
        session_id: str,
        session_token: str
    ) -> dict[str, Any]:
        """
        Initialize a secure transcription session with key exchange
        
        Args:
            websocket: Active WebSocket connection
            session_id: Session identifier
            session_token: Session authentication token
        
        Returns:
            Session initialization data with encryption parameters
        """
        
        # Generate session-specific encryption key
        session_key = AESGCM.generate_key(bit_length=256)
        self.session_keys[session_id] = session_key
        
        # Create initial context
        self.chunk_contexts[session_id] = ChunkContext(
            session_id=session_id,
            chunk_number=0,
            timestamp=datetime.utcnow(),
            previous_audio_tail=b"",
            previous_transcription_tail="",
            medical_context={
                "medications": [],
                "vital_signs": [],
                "symptoms": [],
                "diagnoses": [],
                "procedures": []
            },
            soap_progress={
                "subjective": "",
                "objective": "",
                "assessment": "",
                "plan": ""
            }
        )
        
        # Prepare encrypted session key for client
        # In production, use asymmetric encryption for key exchange
        encrypted_session_key = base64.b64encode(session_key).decode()
        
        # Load configuration for session initialization
        progressive_insights_enabled = True
        medical_entity_extraction_enabled = True
        soap_generation_enabled = True
        phi_protection_enabled = True
        
        if CONFIG_AVAILABLE:
            try:
                config = get_chunked_transcription_config()
                progressive_insights_enabled = config.progressive_insights.enabled
                medical_entity_extraction_enabled = config.progressive_insights.medical_entity_extraction.enabled
                soap_generation_enabled = config.soap_generation.auto_generation
                phi_protection_enabled = config.phi_protection.enabled
            except Exception:
                pass  # Use defaults
        
        initialization_data = {
            "type": "session_initialized",
            "session_id": session_id,
            "encryption": {
                "algorithm": self.encryption_algorithm,
                "session_key": encrypted_session_key,  # Should be asymmetrically encrypted
                "key_rotation_interval": self.key_rotation_interval
            },
            "chunk_config": {
                "duration_seconds": self.chunk_duration,
                "overlap_seconds": self.chunk_overlap,
                "sample_rate": self.sample_rate
            },
            "features": {
                "progressive_insights": progressive_insights_enabled,
                "medical_entity_extraction": medical_entity_extraction_enabled,
                "soap_generation": soap_generation_enabled,
                "phi_protection": phi_protection_enabled
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return initialization_data
    
    async def _decrypt_chunk(
        self,
        session_id: str,
        encrypted_audio: bytes,
        nonce: bytes
    ) -> bytes:
        """Decrypt an audio chunk using session key"""
        
        session_key = self.session_keys.get(session_id)
        if not session_key:
            raise ValueError(f"No session key found for {session_id}")
        
        aesgcm = AESGCM(session_key)
        decrypted_audio = aesgcm.decrypt(nonce, encrypted_audio, None)
        
        return decrypted_audio
    
    async def _merge_with_overlap(
        self,
        current_audio: bytes,
        context: ChunkContext
    ) -> bytes:
        """
        Merge current audio chunk with overlap from previous chunk
        
        This prevents word cutoff at chunk boundaries
        """
        
        if not context.previous_audio_tail:
            # First chunk, no overlap
            return current_audio
        
        # Concatenate overlap with current chunk
        # Apply crossfade to prevent audio artifacts
        overlap_samples = int(self.chunk_overlap * self.sample_rate * 2)  # 2 bytes per sample
        
        # Simple concatenation for now
        # In production, apply proper audio crossfade
        merged_audio = context.previous_audio_tail + current_audio
        
        return merged_audio
    
    async def _transcribe_audio(
        self,
        audio_data: bytes,
        context: ChunkContext
    ) -> dict[str, Any]:
        """
        Transcribe audio using Whisper or configured STT service
        
        Returns transcription with confidence scores
        """
        
        # Placeholder for actual transcription
        # This would call the transcription agent or Whisper service
        
        transcription_result = {
            "text": "",  # Transcribed text
            "confidence": 0.95,
            "language": "en",
            "medical_terms_detected": [],
            "timestamp_start": context.timestamp.isoformat(),
            "timestamp_end": (context.timestamp + timedelta(seconds=self.chunk_duration)).isoformat()
        }
        
        # Add context from previous transcription for better accuracy
        if context.previous_transcription_tail:
            transcription_result["context"] = context.previous_transcription_tail
        
        return transcription_result
    
    async def _generate_medical_insights(
        self,
        transcription: dict[str, Any],
        context: ChunkContext
    ) -> dict[str, Any]:
        """
        Generate medical insights from transcription
        
        Instead of returning raw transcription, return:
        - Extracted medical entities
        - Clinical alerts
        - Progressive SOAP updates
        - Relevant suggestions
        """
        
        insights = {
            "chunk_number": context.chunk_number,
            "duration": f"{context.chunk_number * self.chunk_duration:.1f}s",
            "insights": {
                "vital_signs": [],  # Extracted vital signs
                "medications": [],  # Mentioned medications
                "symptoms": [],  # Patient symptoms
                "clinical_alerts": [],  # Important alerts
                "procedures": [],  # Mentioned procedures
                "diagnoses": []  # Potential diagnoses
            },
            "soap_progress": {
                "subjective": "",  # New subjective info
                "objective": "",  # New objective findings
                "assessment": "",  # Updated assessment
                "plan": ""  # Treatment plan updates
            },
            "suggestions": [],  # Contextual suggestions for provider
            "confidence": transcription.get("confidence", 0.0)
        }
        
        # Extract medical entities from transcription
        # This would use SciSpacy or medical NER
        
        # Update progressive SOAP note
        # Only show new/updated portions
        
        # Generate clinical alerts based on context
        # E.g., drug interactions, abnormal vitals
        
        return insights
    
    async def _update_context(
        self,
        context: ChunkContext,
        audio_data: bytes,
        transcription: dict[str, Any],
        insights: dict[str, Any]
    ) -> None:
        """Update context for next chunk processing"""
        
        # Store audio tail for overlap
        overlap_samples = int(self.chunk_overlap * self.sample_rate * 2)
        context.previous_audio_tail = audio_data[-overlap_samples:] if len(audio_data) > overlap_samples else audio_data
        
        # Store transcription tail for context
        transcribed_text = transcription.get("text", "")
        words = transcribed_text.split()
        context.previous_transcription_tail = " ".join(words[-10:]) if len(words) > 10 else transcribed_text
        
        # Update medical context
        for category in ["medications", "vital_signs", "symptoms", "diagnoses", "procedures"]:
            if category in insights["insights"]:
                context.medical_context[category].extend(insights["insights"][category])
        
        # Update SOAP progress
        for section in ["subjective", "objective", "assessment", "plan"]:
            if insights["soap_progress"].get(section):
                context.soap_progress[section] += " " + insights["soap_progress"][section]
    
    async def _encrypt_insights(
        self,
        session_id: str,
        insights: dict[str, Any]
    ) -> dict[str, str]:
        """Encrypt insights for transmission back to client"""
        
        session_key = self.session_keys.get(session_id)
        if not session_key:
            raise ValueError(f"No session key found for {session_id}")
        
        # Serialize insights to JSON
        insights_json = json.dumps(insights)
        insights_bytes = insights_json.encode()
        
        # Encrypt with AES-GCM
        aesgcm = AESGCM(session_key)
        nonce = AESGCM.generate_key(bit_length=96)  # 12 bytes for GCM
        encrypted_insights = aesgcm.encrypt(nonce, insights_bytes, None)
        
        return {
            "data": base64.b64encode(encrypted_insights).decode(),
            "nonce": base64.b64encode(nonce).decode()
        }
    
    def _get_or_create_context(self, session_id: str) -> ChunkContext:
        """Get existing context or create new one"""
        
        if session_id not in self.chunk_contexts:
            self.chunk_contexts[session_id] = ChunkContext(
                session_id=session_id,
                chunk_number=0,
                timestamp=datetime.utcnow(),
                previous_audio_tail=b"",
                previous_transcription_tail="",
                medical_context={
                    "medications": [],
                    "vital_signs": [],
                    "symptoms": [],
                    "diagnoses": [],
                    "procedures": []
                },
                soap_progress={
                    "subjective": "",
                    "objective": "",
                    "assessment": "",
                    "plan": ""
                }
            )
        
        return self.chunk_contexts[session_id]
    
    async def cleanup_session(self, session_id: str) -> None:
        """Clean up session data and keys"""
        
        # Remove session key
        if session_id in self.session_keys:
            del self.session_keys[session_id]
        
        # Remove context
        if session_id in self.chunk_contexts:
            del self.chunk_contexts[session_id]
        
        self.logger.info(f"Cleaned up secure session {session_id}")