"""
Enhanced Session Manager for Healthcare AI System
PHI-aware conversation continuity with semantic understanding
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from core.dependencies import get_database_connection
from core.infrastructure.healthcare_logger import get_healthcare_logger, log_healthcare_event
from core.infrastructure.phi_monitor import sanitize_healthcare_data, scan_for_phi


class EnhancedSessionManager:
    """
    Enhanced session management with PHI protection and cross-agent data sharing

    Provides intelligent conversation continuity while maintaining healthcare privacy compliance.
    Supports real-time voice processing sessions and agent coordination.
    """

    def __init__(self):
        self.logger = get_healthcare_logger("enhanced_session_manager")
        self._db_connection = None
        self._initialized = False

        # Session caching for performance
        self._session_cache: dict[str, dict[str, Any]] = {}
        self._cache_expiry: dict[str, datetime] = {}
        self._cache_duration = timedelta(minutes=30)

    async def initialize(self) -> None:
        """Initialize session manager with database connectivity"""
        try:
            self._db_connection = await get_database_connection()
            await self._db_connection.execute("SELECT 1")  # Test connection

            self._initialized = True

            log_healthcare_event(
                self.logger,
                logging.INFO,
                "Enhanced Session Manager initialized",
                context={
                    "database_connected": True,
                    "phi_protection_enabled": True,
                    "cache_enabled": True,
                },
                operation_type="session_manager_init",
            )

        except Exception as e:
            log_healthcare_event(
                self.logger,
                logging.ERROR,
                f"Failed to initialize session manager: {str(e)}",
                context={"error": str(e)},
                operation_type="session_manager_init_error",
            )
            raise

    async def create_session(
        self,
        user_id: str,
        session_type: str = "conversation",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Create a new session with PHI protection

        Args:
            user_id: User identifier
            session_type: Type of session (conversation, voice_intake, etc.)
            metadata: Additional session metadata

        Returns:
            str: New session ID
        """
        try:
            session_id = str(uuid.uuid4())
            session_title = f"{session_type}_{datetime.now().strftime('%Y%m%d_%H%M')}"

            # Apply PHI detection to metadata
            safe_metadata = sanitize_healthcare_data(metadata or {})

            if self._db_connection:
                # Store in database
                await self._db_connection.execute("""
                    INSERT INTO user_conversation_sessions
                    (session_id, user_id, session_title, medical_topics, phi_detected, privacy_level)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, session_id, user_id, session_title, "[]", False, "standard")

            # Cache session data
            session_data = {
                "session_id": session_id,
                "user_id": user_id,
                "session_type": session_type,
                "session_title": session_title,
                "created_at": datetime.now(),
                "metadata": safe_metadata,
                "message_count": 0,
                "phi_detected": False,
            }

            self._session_cache[session_id] = session_data
            self._cache_expiry[session_id] = datetime.now() + self._cache_duration

            log_healthcare_event(
                self.logger,
                logging.INFO,
                f"Session created: {session_id}",
                context={
                    "session_id": session_id,
                    "user_id": user_id,
                    "session_type": session_type,
                },
                operation_type="session_created",
            )

            return session_id

        except Exception as e:
            log_healthcare_event(
                self.logger,
                logging.ERROR,
                f"Failed to create session: {str(e)}",
                context={"user_id": user_id, "error": str(e)},
                operation_type="session_creation_error",
            )
            raise

    async def store_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Store a message in the session with PHI protection

        Args:
            session_id: Session identifier
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Additional message metadata

        Returns:
            str: Message ID
        """
        try:
            message_id = str(uuid.uuid4())

            # PHI detection and sanitization
            phi_result = scan_for_phi(content)
            phi_detected = phi_result.get("phi_detected", False)

            # Sanitize content for storage
            sanitized_content = sanitize_healthcare_data({"content": content}).get("content", content)
            safe_metadata = sanitize_healthcare_data(metadata or {})

            if self._db_connection:
                # Store in database with PHI protection
                await self._db_connection.execute("""
                    INSERT INTO user_conversation_messages
                    (message_id, session_id, user_id, role, message_content,
                     medical_entities, topics, phi_score, phi_entities,
                     agent_name, processing_metadata)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """,
                message_id, session_id, "system",  # user_id from session lookup
                role, sanitized_content, "[]", "[]",
                1.0 if phi_detected else 0.0, "[]",
                safe_metadata.get("agent_name", "unknown"),
                safe_metadata,
                )

                # Update session message count
                await self._db_connection.execute("""
                    UPDATE user_conversation_sessions
                    SET message_count = message_count + 1, last_accessed = NOW(),
                        phi_detected = phi_detected OR $2
                    WHERE session_id = $1
                """, session_id, phi_detected)

            # Update cache
            if session_id in self._session_cache:
                self._session_cache[session_id]["message_count"] += 1
                self._session_cache[session_id]["phi_detected"] = (
                    self._session_cache[session_id]["phi_detected"] or phi_detected
                )

            log_healthcare_event(
                self.logger,
                logging.INFO,
                f"Message stored: {message_id}",
                context={
                    "session_id": session_id,
                    "message_id": message_id,
                    "role": role,
                    "phi_detected": phi_detected,
                    "content_length": len(content),
                },
                operation_type="message_stored",
            )

            return message_id

        except Exception as e:
            log_healthcare_event(
                self.logger,
                logging.ERROR,
                f"Failed to store message: {str(e)}",
                context={"session_id": session_id, "error": str(e)},
                operation_type="message_storage_error",
            )
            raise

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """
        Retrieve session data with PHI protection

        Args:
            session_id: Session identifier

        Returns:
            Optional[Dict]: Session data or None if not found
        """
        try:
            # Check cache first
            if session_id in self._session_cache:
                if datetime.now() < self._cache_expiry.get(session_id, datetime.min):
                    return self._session_cache[session_id].copy()
                # Clean up expired cache entry
                del self._session_cache[session_id]
                if session_id in self._cache_expiry:
                    del self._cache_expiry[session_id]

            # Fetch from database
            if self._db_connection:
                row = await self._db_connection.fetchrow("""
                    SELECT session_id, user_id, session_title, created_at,
                           last_accessed, message_count, medical_topics,
                           phi_detected, privacy_level
                    FROM user_conversation_sessions
                    WHERE session_id = $1
                """, session_id)

                if row:
                    session_data = {
                        "session_id": row["session_id"],
                        "user_id": row["user_id"],
                        "session_title": row["session_title"],
                        "created_at": row["created_at"],
                        "last_accessed": row["last_accessed"],
                        "message_count": row["message_count"],
                        "medical_topics": row["medical_topics"],
                        "phi_detected": row["phi_detected"],
                        "privacy_level": row["privacy_level"],
                    }

                    # Update cache
                    self._session_cache[session_id] = session_data
                    self._cache_expiry[session_id] = datetime.now() + self._cache_duration

                    return session_data

            return None

        except Exception as e:
            log_healthcare_event(
                self.logger,
                logging.ERROR,
                f"Failed to get session: {str(e)}",
                context={"session_id": session_id, "error": str(e)},
                operation_type="session_retrieval_error",
            )
            return None

    async def get_session_messages(
        self,
        session_id: str,
        limit: int = 50,
        phi_sanitized: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Retrieve session messages with PHI protection

        Args:
            session_id: Session identifier
            limit: Maximum number of messages to retrieve
            phi_sanitized: Whether to return sanitized content

        Returns:
            List[Dict]: List of messages
        """
        try:
            if not self._db_connection:
                return []

            # Use privacy-compliant view for message access
            query = """
                SELECT message_id, role, safe_content as content,
                       medical_entities, topics, timestamp, agent_name
                FROM conversation_messages_view
                WHERE session_id = $1
                ORDER BY timestamp DESC
                LIMIT $2
            """ if phi_sanitized else """
                SELECT message_id, role, message_content as content,
                       medical_entities, topics, timestamp, agent_name
                FROM user_conversation_messages
                WHERE session_id = $1
                ORDER BY timestamp DESC
                LIMIT $2
            """

            rows = await self._db_connection.fetch(query, session_id, limit)

            messages = []
            for row in rows:
                messages.append({
                    "message_id": row["message_id"],
                    "role": row["role"],
                    "content": row["content"],
                    "medical_entities": row["medical_entities"],
                    "topics": row["topics"],
                    "timestamp": row["timestamp"],
                    "agent_name": row["agent_name"],
                })

            return messages

        except Exception as e:
            log_healthcare_event(
                self.logger,
                logging.ERROR,
                f"Failed to get session messages: {str(e)}",
                context={"session_id": session_id, "error": str(e)},
                operation_type="message_retrieval_error",
            )
            return []

    async def share_session_data(
        self,
        source_session_id: str,
        target_session_id: str,
        data_types: list[str] = None,
    ) -> bool:
        """
        Share session data between agents with PHI protection

        Args:
            source_session_id: Source session
            target_session_id: Target session
            data_types: Types of data to share (medical_terms, form_data, etc.)

        Returns:
            bool: Success status
        """
        try:
            if not data_types:
                data_types = ["medical_terms", "topics", "metadata"]

            # Get source session data
            source_session = await self.get_session(source_session_id)
            if not source_session:
                return False

            # Create relationship record
            if self._db_connection:
                await self._db_connection.execute("""
                    INSERT INTO conversation_relationships
                    (source_session_id, related_session_id, user_id,
                     relationship_type, similarity_score, shared_topics)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """,
                source_session_id, target_session_id,
                source_session["user_id"], "cross_agent_sharing",
                1.0, source_session.get("medical_topics", []),
                )

            log_healthcare_event(
                self.logger,
                logging.INFO,
                f"Session data shared: {source_session_id} -> {target_session_id}",
                context={
                    "source_session": source_session_id,
                    "target_session": target_session_id,
                    "data_types": data_types,
                },
                operation_type="session_data_shared",
            )

            return True

        except Exception as e:
            log_healthcare_event(
                self.logger,
                logging.ERROR,
                f"Failed to share session data: {str(e)}",
                context={
                    "source_session": source_session_id,
                    "target_session": target_session_id,
                    "error": str(e),
                },
                operation_type="session_sharing_error",
            )
            return False

    async def cleanup(self) -> None:
        """Clean up session manager resources"""
        try:
            # Clear session cache
            self._session_cache.clear()
            self._cache_expiry.clear()

            # Close database connection
            if self._db_connection:
                await self._db_connection.close()
                self._db_connection = None

            log_healthcare_event(
                self.logger,
                logging.INFO,
                "Session manager cleanup completed",
                context={"cache_cleared": True, "db_connection_closed": True},
                operation_type="session_manager_cleanup",
            )

        except Exception as e:
            log_healthcare_event(
                self.logger,
                logging.ERROR,
                f"Error during session manager cleanup: {str(e)}",
                context={"error": str(e)},
                operation_type="session_cleanup_error",
            )
