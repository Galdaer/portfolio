"""
PHI-Safe Chat Log Management for Healthcare AI
Manages chat logs with automatic PHI detection and secure storage
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from core.infrastructure.healthcare_logger import get_healthcare_logger

# Simple PHI detector for chat logging
class SimplePHIDetector:
    """Simple PHI detection for chat log management"""
    
    def __init__(self):
        import re
        self.phi_patterns = [
            re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),  # SSN
            re.compile(r'\b\d{3}-\d{3}-\d{4}\b'),  # Phone
            re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),  # Email
        ]
    
    def contains_phi(self, text: str) -> bool:
        """Check if text contains potential PHI patterns"""
        for pattern in self.phi_patterns:
            if pattern.search(text):
                return True
        return False
    
    async def scan_text(self, text: str) -> bool:
        """Async method to scan text for PHI"""
        return self.contains_phi(text)
    
    async def sanitize_text(self, text: str) -> str:
        """Async method to sanitize text by replacing PHI with placeholders"""
        sanitized = text
        for pattern in self.phi_patterns:
            sanitized = pattern.sub('[REDACTED]', sanitized)
        return sanitized

logger = get_healthcare_logger("chat_log_manager")


class ChatLogLevel(Enum):
    """Chat log security levels"""

    PUBLIC = "public"
    HEALTHCARE_SENSITIVE = "healthcare_sensitive"
    PHI_DETECTED = "phi_detected"
    QUARANTINED = "quarantined"


@dataclass
class ChatMessage:
    """Structured chat message with PHI protection"""

    message_id: str
    session_id: str
    user_id: str
    timestamp: datetime
    role: str  # 'user', 'assistant', 'system'
    content: str
    security_level: ChatLogLevel
    phi_detected: bool
    sanitized_content: str | None = None
    audit_trail: list[str] = None

    def __post_init__(self):
        if self.audit_trail is None:
            self.audit_trail = []


@dataclass
class ChatSession:
    """Chat session with healthcare compliance tracking"""

    session_id: str
    user_id: str
    start_time: datetime
    last_activity: datetime
    messages: list[ChatMessage]
    healthcare_context: dict[str, Any]
    phi_detected_count: int = 0
    security_alerts: list[str] = None

    def __post_init__(self):
        if self.security_alerts is None:
            self.security_alerts = []


class ChatLogManager:
    """PHI-safe chat log management for healthcare AI"""

    def __init__(self, log_directory: str = "/app/logs/chat"):
        self.log_directory = Path(log_directory)
        self.log_directory.mkdir(parents=True, exist_ok=True)

        self.phi_detector = SimplePHIDetector()
        self.active_sessions: dict[str, ChatSession] = {}

        # PHI quarantine directory
        self.quarantine_directory = self.log_directory / "quarantine"
        self.quarantine_directory.mkdir(exist_ok=True)

        logger.info("Chat log manager initialized with PHI protection")

    async def log_chat_message(
        self,
        session_id: str,
        user_id: str,
        role: str,
        content: str,
        healthcare_context: dict[str, Any] | None = None,
    ) -> ChatMessage:
        """Log chat message with automatic PHI detection and sanitization"""

        message_id = self._generate_message_id(session_id, content)

        # PHI detection
        phi_detected = await self.phi_detector.scan_text(content)

        # Determine security level
        security_level = self._determine_security_level(content, phi_detected, healthcare_context)

        # Sanitize content if PHI detected
        sanitized_content = None
        if phi_detected:
            sanitized_content = await self.phi_detector.sanitize_text(content)

            # Log PHI detection alert
            logger.warning(
                "PHI detected in chat message",
                extra={
                    "operation_type": "phi_chat_detection",
                    "session_id": session_id,
                    "message_id": message_id,
                    "user_id": user_id,
                    "role": role,
                    "security_level": security_level.value,
                    "compliance_requirement": "HIPAA_PHI_Protection",
                },
            )

        # Create message object
        message = ChatMessage(
            message_id=message_id,
            session_id=session_id,
            user_id=user_id,
            timestamp=datetime.utcnow(),
            role=role,
            content=content if not phi_detected else "[PHI_REDACTED]",
            security_level=security_level,
            phi_detected=phi_detected,
            sanitized_content=sanitized_content,
            audit_trail=[f"Created at {datetime.utcnow().isoformat()}"],
        )

        # Handle session
        await self._handle_session_message(message, healthcare_context)

        # Store message based on security level
        await self._store_message(message)

        logger.info(
            f"Chat message logged with security level: {security_level.value}",
            extra={
                "operation_type": "chat_message_logged",
                "session_id": session_id,
                "message_id": message_id,
                "security_level": security_level.value,
                "phi_detected": phi_detected,
            },
        )

        return message

    async def get_chat_history(
        self, session_id: str, user_id: str, include_phi: bool = False, max_messages: int = 100
    ) -> list[ChatMessage]:
        """Retrieve chat history with PHI protection"""

        # Verify user has access to session
        if not await self._verify_session_access(session_id, user_id):
            raise PermissionError(f"User {user_id} not authorized for session {session_id}")

        session = self.active_sessions.get(session_id)
        if not session:
            # Load from persistent storage
            session = await self._load_session(session_id)

        if not session:
            return []

        # Filter messages based on PHI access
        filtered_messages = []
        for message in session.messages[-max_messages:]:
            if message.phi_detected and not include_phi:
                # Return sanitized version
                sanitized_message = ChatMessage(
                    message_id=message.message_id,
                    session_id=message.session_id,
                    user_id=message.user_id,
                    timestamp=message.timestamp,
                    role=message.role,
                    content=message.sanitized_content or "[PHI_PROTECTED]",
                    security_level=message.security_level,
                    phi_detected=True,
                    sanitized_content=message.sanitized_content,
                    audit_trail=message.audit_trail
                    + [f"PHI_filtered_at_{datetime.utcnow().isoformat()}"],
                )
                filtered_messages.append(sanitized_message)
            else:
                filtered_messages.append(message)

        # Log access
        logger.info(
            "Chat history retrieved",
            extra={
                "operation_type": "chat_history_access",
                "session_id": session_id,
                "user_id": user_id,
                "messages_returned": len(filtered_messages),
                "phi_access_granted": include_phi,
            },
        )

        return filtered_messages

    async def create_session(
        self, user_id: str, healthcare_context: dict[str, Any] | None = None
    ) -> str:
        """Create new chat session with healthcare context"""

        session_id = self._generate_session_id(user_id)

        session = ChatSession(
            session_id=session_id,
            user_id=user_id,
            start_time=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            messages=[],
            healthcare_context=healthcare_context or {},
            phi_detected_count=0,
        )

        self.active_sessions[session_id] = session

        # Log session creation
        logger.info(
            "Chat session created",
            extra={
                "operation_type": "chat_session_created",
                "session_id": session_id,
                "user_id": user_id,
                "healthcare_context": bool(healthcare_context),
            },
        )

        return session_id

    async def end_session(self, session_id: str, user_id: str) -> dict[str, Any]:
        """End chat session with compliance summary"""

        session = self.active_sessions.get(session_id)
        if not session or session.user_id != user_id:
            raise ValueError("Session not found or access denied")

        # Generate session summary
        session_summary = {
            "session_id": session_id,
            "user_id": user_id,
            "duration_minutes": (datetime.utcnow() - session.start_time).total_seconds() / 60,
            "total_messages": len(session.messages),
            "phi_detected_count": session.phi_detected_count,
            "security_alerts": len(session.security_alerts),
            "healthcare_context": session.healthcare_context,
            "end_time": datetime.utcnow().isoformat(),
        }

        # Persist session before ending
        await self._persist_session(session)

        # Remove from active sessions
        del self.active_sessions[session_id]

        logger.info(
            "Chat session ended",
            extra={"operation_type": "chat_session_ended", "session_summary": session_summary},
        )

        return session_summary

    async def quarantine_message(
        self, message_id: str, reason: str, quarantine_level: str = "HIGH"
    ) -> None:
        """Quarantine message with potential PHI exposure"""

        # Find message across all sessions
        message = None
        for session in self.active_sessions.values():
            for msg in session.messages:
                if msg.message_id == message_id:
                    message = msg
                    break
            if message:
                break

        if not message:
            logger.error(f"Message {message_id} not found for quarantine")
            return

        # Create quarantine record
        quarantine_record = {
            "message_id": message_id,
            "session_id": message.session_id,
            "user_id": message.user_id,
            "quarantine_time": datetime.utcnow().isoformat(),
            "reason": reason,
            "quarantine_level": quarantine_level,
            "original_content": "[QUARANTINED]",  # Don't store actual content
            "security_level": message.security_level.value,
            "audit_trail": message.audit_trail + [f"Quarantined: {reason}"],
        }

        # Store in quarantine
        quarantine_file = self.quarantine_directory / f"{message_id}.json"
        with open(quarantine_file, "w") as f:
            json.dump(quarantine_record, f, indent=2)

        # Update message in session
        message.content = "[QUARANTINED]"
        message.security_level = ChatLogLevel.QUARANTINED
        message.audit_trail.append(f"Quarantined at {datetime.utcnow().isoformat()}: {reason}")

        logger.critical(
            "Message quarantined due to PHI exposure",
            extra={
                "operation_type": "message_quarantined",
                "message_id": message_id,
                "session_id": message.session_id,
                "reason": reason,
                "quarantine_level": quarantine_level,
            },
        )

    def _generate_message_id(self, session_id: str, content: str) -> str:
        """Generate unique message ID"""
        data = f"{session_id}_{content}_{datetime.utcnow().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def _generate_session_id(self, user_id: str) -> str:
        """Generate unique session ID"""
        data = f"{user_id}_{datetime.utcnow().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:12]

    def _determine_security_level(
        self, content: str, phi_detected: bool, healthcare_context: dict[str, Any] | None
    ) -> ChatLogLevel:
        """Determine security level for message"""

        if phi_detected:
            return ChatLogLevel.PHI_DETECTED

        # Check for healthcare sensitivity
        healthcare_keywords = [
            "patient",
            "diagnosis",
            "treatment",
            "medication",
            "symptoms",
            "medical",
            "hospital",
            "doctor",
            "nurse",
            "clinic",
        ]

        content_lower = content.lower()
        if any(keyword in content_lower for keyword in healthcare_keywords):
            return ChatLogLevel.HEALTHCARE_SENSITIVE

        if healthcare_context:
            return ChatLogLevel.HEALTHCARE_SENSITIVE

        return ChatLogLevel.PUBLIC

    async def _handle_session_message(
        self, message: ChatMessage, healthcare_context: dict[str, Any] | None
    ) -> None:
        """Handle message within session context"""

        session = self.active_sessions.get(message.session_id)
        if not session:
            # Create session if doesn't exist
            session = ChatSession(
                session_id=message.session_id,
                user_id=message.user_id,
                start_time=datetime.utcnow(),
                last_activity=datetime.utcnow(),
                messages=[],
                healthcare_context=healthcare_context or {},
            )
            self.active_sessions[message.session_id] = session

        # Update session
        session.last_activity = datetime.utcnow()
        session.messages.append(message)

        if message.phi_detected:
            session.phi_detected_count += 1

            # Add security alert if PHI threshold exceeded
            if session.phi_detected_count > 3:
                alert = f"Multiple PHI detections in session: {session.phi_detected_count}"
                session.security_alerts.append(alert)

                logger.warning(
                    "PHI threshold exceeded in session",
                    extra={
                        "operation_type": "phi_threshold_exceeded",
                        "session_id": message.session_id,
                        "phi_count": session.phi_detected_count,
                    },
                )

    async def _store_message(self, message: ChatMessage) -> None:
        """Store message based on security level"""

        # Determine storage path based on security level
        if message.security_level == ChatLogLevel.PHI_DETECTED:
            storage_path = self.log_directory / "phi_detected"
        elif message.security_level == ChatLogLevel.HEALTHCARE_SENSITIVE:
            storage_path = self.log_directory / "healthcare_sensitive"
        elif message.security_level == ChatLogLevel.QUARANTINED:
            storage_path = self.quarantine_directory
        else:
            storage_path = self.log_directory / "public"

        storage_path.mkdir(exist_ok=True)

        # Create message file
        message_file = storage_path / f"{message.message_id}.json"

        # Serialize message (exclude actual content if PHI detected)
        message_data = asdict(message)
        if message.phi_detected:
            message_data["content"] = "[PHI_REDACTED_FOR_STORAGE]"

        with open(message_file, "w") as f:
            json.dump(message_data, f, indent=2, default=str)

    async def _verify_session_access(self, session_id: str, user_id: str) -> bool:
        """Verify user has access to session"""

        session = self.active_sessions.get(session_id)
        if session:
            return session.user_id == user_id

        # Check persistent storage
        session = await self._load_session(session_id)
        return session.user_id == user_id if session else False

    async def _load_session(self, session_id: str) -> ChatSession | None:
        """Load session from persistent storage"""
        # Implementation would load from database or file system
        # For now, return None (session not found)
        return None

    async def _persist_session(self, session: ChatSession) -> None:
        """Persist session to storage"""

        session_file = self.log_directory / f"session_{session.session_id}.json"

        # Serialize session data
        session_data = asdict(session)

        with open(session_file, "w") as f:
            json.dump(session_data, f, indent=2, default=str)
