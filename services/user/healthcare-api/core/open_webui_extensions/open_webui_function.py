"""
Open WebUI Function for Enhanced Medical Context
This is the main integration point that Open WebUI can import and use
"""

import logging
from typing import Any

from .medical_context_manager import OpenWebUIMedicalContext

logger = logging.getLogger(__name__)


class MedicalContextFunction:
    """
    Main Open WebUI function class for medical context features
    This can be imported directly by Open WebUI
    """

    def __init__(self, webui_db_path: str = "app/backend/data/webui.db"):
        self.webui_db_path = webui_db_path
        self.context_manager = OpenWebUIMedicalContext(webui_db_path)
        self._initialized = False

    def initialize(self) -> bool:
        """Initialize medical context system"""
        try:
            if not self._initialized:
                self.context_manager.initialize_medical_tables()
                self._initialized = True
                logger.info("Medical context system initialized")
            return True
        except Exception as e:
            logger.exception(f"Failed to initialize medical context: {e}")
            return False

    def get_context_for_query(
        self,
        user_id: str,
        query: str,
        chat_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Get medical context for a user query
        This is the main function Open WebUI should call

        Args:
            user_id: Open WebUI user ID
            query: Current user query
            chat_id: Current chat ID (optional)

        Returns:
            Dict with medical context and suggestions
        """
        if not self._initialized:
            self.initialize()

        try:
            # Get enhanced context
            context = self.context_manager.get_medical_context(user_id, query)

            # Format for Open WebUI
            return self._format_context_for_webui(context, query)

        except Exception as e:
            logger.exception(f"Error getting context for user {user_id}: {e}")
            return {"error": str(e), "has_context": False}

    def store_message_data(
        self,
        chat_id: str,
        user_id: str,
        message_content: str,
        message_role: str = "user",
    ) -> bool:
        """
        Store medical data from a message
        Open WebUI should call this after each message

        Args:
            chat_id: Chat ID
            user_id: User ID
            message_content: Message content
            message_role: user/assistant

        Returns:
            Success status
        """
        if not self._initialized:
            self.initialize()

        try:
            self.context_manager.store_conversation_medical_data(
                chat_id, user_id, message_content, message_role,
            )
            return True
        except Exception as e:
            logger.exception(f"Error storing message data: {e}")
            return False

    def get_conversation_suggestions(self, user_id: str, limit: int = 5) -> list[dict[str, Any]]:
        """
        Get conversation suggestions for user
        Can be used in Open WebUI sidebar

        Args:
            user_id: User ID
            limit: Max suggestions

        Returns:
            List of conversation suggestions
        """
        if not self._initialized:
            self.initialize()

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get recent medical topics
                cursor = conn.execute("""
                SELECT DISTINCT
                    umc.medical_topic,
                    umc.topic_category,
                    umc.last_discussed,
                    umc.summary
                FROM user_medical_context umc
                WHERE umc.user_id = ?
                ORDER BY umc.last_discussed DESC, umc.importance_score DESC
                LIMIT ?
                """, (user_id, limit))

                results = cursor.fetchall()

                suggestions = []
                for row in results:
                    suggestions.append({
                        "topic": row[0],
                        "category": row[1],
                        "last_discussed": row[2],
                        "summary": row[3],
                        "suggested_query": f"Tell me more about {row[0]}",
                        "type": "follow_up",
                    })

                return suggestions

        except Exception as e:
            logger.exception(f"Error getting suggestions for user {user_id}: {e}")
            return []

    def search_medical_history(
        self,
        user_id: str,
        search_query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Search user's medical conversation history

        Args:
            user_id: User ID
            search_query: Search terms
            limit: Max results

        Returns:
            Search results
        """
        if not self._initialized:
            self.initialize()

        try:
            # Use FTS search
            results = self.context_manager.find_similar_conversations(
                user_id, search_query, limit,
            )

            # Format for display
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "chat_id": result["chat_id"],
                    "title": result.get("chat_title", "Untitled Chat"),
                    "topic_matches": result["topic_matches"],
                    "last_mentioned": result["last_mentioned"],
                    "preview": result.get("context_snippet", "")[:100] + "...",
                })

            return formatted_results

        except Exception as e:
            logger.exception(f"Error searching medical history for user {user_id}: {e}")
            return []

    def get_user_medical_settings(self, user_id: str) -> dict[str, Any]:
        """Get user's medical context settings"""
        if not self._initialized:
            self.initialize()

        return self.context_manager.get_user_medical_preferences(user_id)

    def update_user_medical_settings(
        self,
        user_id: str,
        settings: dict[str, Any],
    ) -> bool:
        """Update user's medical context settings"""
        if not self._initialized:
            self.initialize()

        return self.context_manager.update_user_medical_preferences(user_id, settings)

    def _format_context_for_webui(
        self,
        context: dict[str, Any],
        original_query: str,
    ) -> dict[str, Any]:
        """Format context data for Open WebUI display"""
        if "error" in context:
            return context

        # Create user-friendly context
        formatted = {
            "has_context": context.get("context_available", False),
            "original_query": original_query,
            "medical_topics_detected": len(context.get("current_topics", [])),
            "related_conversations": len(context.get("related_conversations", [])),
            "recent_topics": len(context.get("recent_topics", [])),
        }

        # Add context suggestions if available
        if context.get("context_available"):
            suggestions = []

            # Add related conversation suggestions
            for chat in context.get("related_conversations", [])[:3]:
                suggestions.append({
                    "type": "related_chat",
                    "title": f"Related: {chat.get('chat_title', 'Previous discussion')}",
                    "description": f"Discussed {chat.get('topic_name', 'medical topic')}",
                    "action": f"Show me the conversation about {chat.get('topic_name', 'this topic')}",
                })

            # Add topic continuation suggestions
            for topic in context.get("recent_topics", [])[:2]:
                suggestions.append({
                    "type": "topic_continuation",
                    "title": f"Continue discussing {topic.get('topic_name', 'topic')}",
                    "description": f"Last discussed: {topic.get('last_mentioned', 'recently')}",
                    "action": f"What's the latest on {topic.get('topic_name', 'this topic')}?",
                })

            formatted["context_suggestions"] = suggestions

            # Add medical summary if available
            summary = context.get("user_medical_summary", {})
            if summary:
                formatted["medical_summary"] = {
                    "total_medical_chats": summary.get("medical_conversations", 0),
                    "unique_topics": summary.get("unique_topics", 0),
                    "last_medical_chat": summary.get("last_medical_discussion", "Never"),
                    "categories_discussed": summary.get("discussed_categories", "").split(",") if summary.get("discussed_categories") else [],
                }

        return formatted


# Global instance for Open WebUI to import
medical_context = MedicalContextFunction()


def get_medical_context_for_chat(
    user_id: str,
    query: str,
    chat_id: str | None = None,
) -> dict[str, Any]:
    """
    Main function for Open WebUI to get medical context

    Usage in Open WebUI:
    from core.open_webui_extensions.open_webui_function import get_medical_context_for_chat
    context = get_medical_context_for_chat(user.id, query, chat.id)

    Args:
        user_id: Open WebUI user ID
        query: Current query
        chat_id: Current chat ID

    Returns:
        Medical context for the query
    """
    return medical_context.get_context_for_query(user_id, query, chat_id)


def store_chat_message_data(
    chat_id: str,
    user_id: str,
    message_content: str,
    message_role: str = "user",
) -> bool:
    """
    Store medical data from chat message

    Usage in Open WebUI:
    from core.open_webui_extensions.open_webui_function import store_chat_message_data
    store_chat_message_data(chat.id, user.id, message.content, "user")

    Args:
        chat_id: Chat ID
        user_id: User ID
        message_content: Message content
        message_role: user/assistant/system

    Returns:
        Success status
    """
    return medical_context.store_message_data(chat_id, user_id, message_content, message_role)


def get_medical_conversation_suggestions(user_id: str) -> list[dict[str, Any]]:
    """
    Get medical conversation suggestions for sidebar

    Usage in Open WebUI:
    from core.open_webui_extensions.open_webui_function import get_medical_conversation_suggestions
    suggestions = get_medical_conversation_suggestions(user.id)

    Args:
        user_id: User ID

    Returns:
        List of conversation suggestions
    """
    return medical_context.get_conversation_suggestions(user_id)


def search_user_medical_history(user_id: str, query: str) -> list[dict[str, Any]]:
    """
    Search user's medical conversation history

    Usage in Open WebUI:
    from core.open_webui_extensions.open_webui_function import search_user_medical_history
    results = search_user_medical_history(user.id, "diabetes treatment")

    Args:
        user_id: User ID
        query: Search query

    Returns:
        Search results
    """
    return medical_context.search_medical_history(user_id, query)


def initialize_medical_context_system() -> bool:
    """
    Initialize the medical context system

    Usage in Open WebUI startup:
    from core.open_webui_extensions.open_webui_function import initialize_medical_context_system
    success = initialize_medical_context_system()

    Returns:
        Success status
    """
    return medical_context.initialize()


# Example integration for Open WebUI
def example_chat_handler_integration():
    """
    Example of how to integrate with Open WebUI's chat handler
    This shows the integration points where Open WebUI would call our functions
    """

    # 1. On chat startup/initialization
    def on_webui_startup():
        success = initialize_medical_context_system()
        if success:
            logger.info("Medical context system ready")
        else:
            logger.warning("Medical context system failed to initialize")

    # 2. Before processing user message
    def before_process_user_message(user_id: str, query: str, chat_id: str):
        # Get medical context for the assistant
        context = get_medical_context_for_chat(user_id, query, chat_id)

        if context.get("has_context"):
            logger.info(f"Medical context available for user {user_id}")
            # Add context to prompt or display suggestions to user
            return context

        return None

    # 3. After user sends message
    def after_user_message(chat_id: str, user_id: str, message_content: str):
        # Store medical data from user message
        success = store_chat_message_data(chat_id, user_id, message_content, "user")
        if success:
            logger.debug(f"Stored medical data for chat {chat_id}")

    # 4. After assistant responds
    def after_assistant_response(chat_id: str, user_id: str, response_content: str):
        # Store medical data from assistant response
        success = store_chat_message_data(chat_id, user_id, response_content, "assistant")
        if success:
            logger.debug(f"Stored assistant medical data for chat {chat_id}")

    # 5. For sidebar suggestions
    def get_sidebar_suggestions(user_id: str):
        return get_medical_conversation_suggestions(user_id)

    # 6. For search functionality
    def search_conversations(user_id: str, search_query: str):
        return search_user_medical_history(user_id, search_query)
