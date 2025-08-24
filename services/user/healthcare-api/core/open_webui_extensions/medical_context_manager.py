"""
Open WebUI Medical Context Manager
Provides healthcare-aware conversation continuity by extending Open WebUI's existing SQLite database
"""

import json
import logging
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Import configuration loaders
try:
    from config.open_webui_config_loader import (
        get_database_config,
        get_medical_config,
        get_medical_keywords,
        get_phi_detection_config,
        get_topic_extraction_config,
        is_feature_enabled,
    )
    CONFIG_AVAILABLE = True
except ImportError:
    # Fallback if config system not available
    CONFIG_AVAILABLE = False
    logging.warning("Config system not available, using hardcoded defaults")

logger = logging.getLogger(__name__)


class OpenWebUIMedicalContext:
    """
    Manages medical context and conversation continuity for Open WebUI
    Extends the existing webui.db with healthcare-specific functionality
    """

    def __init__(self, webui_db_path: str = "app/backend/data/webui.db"):
        """
        Initialize with path to Open WebUI's database

        Args:
            webui_db_path: Path to Open WebUI's SQLite database
        """
        # Load configuration
        if CONFIG_AVAILABLE:
            db_config = get_database_config()
            self.db_path = webui_db_path or db_config.get("webui_db_path", "app/backend/data/webui.db")
            self.config = get_medical_config().load_medical_context_config()
            self.medical_keywords = get_medical_keywords()
            self.phi_config = get_phi_detection_config()

            # Validate configurations
            self._validate_configuration_on_startup()
        else:
            self.db_path = webui_db_path
            self.config = self._get_default_config()
            self.medical_keywords = self._load_medical_keywords()
            self.phi_config = {}

        # Extract PHI patterns from config
        self.phi_patterns = self._extract_phi_patterns_from_config()

    def _validate_configuration_on_startup(self) -> None:
        """Validate configuration during startup and log any issues"""
        try:
            from ...config.open_webui_config_loader import validate_medical_configurations
            validation_results = validate_medical_configurations()

            if not validation_results["valid"]:
                logger.warning("Medical context configuration validation failed on startup")
                for error in validation_results["errors"][:3]:  # Log first 3 errors
                    logger.warning(f"Config validation error: {error}")

                if len(validation_results["errors"]) > 3:
                    logger.warning(f"... and {len(validation_results['errors']) - 3} more configuration errors")
            else:
                logger.debug("Medical context configuration validation passed")

            for warning in validation_results["warnings"][:2]:  # Log first 2 warnings
                logger.debug(f"Config validation warning: {warning}")

        except Exception as e:
            logger.warning(f"Could not validate medical context configuration: {e}")

    def initialize_medical_tables(self) -> None:
        """Initialize medical context tables if they don't exist"""
        try:
            # Read and execute the schema file
            schema_path = Path(__file__).parent / "webui_medical_schema.sql"
            with open(schema_path) as f:
                schema_sql = f.read()

            with sqlite3.connect(self.db_path) as conn:
                conn.executescript(schema_sql)
                conn.commit()

            logger.info("Medical context tables initialized successfully")
        except Exception as e:
            logger.exception(f"Failed to initialize medical tables: {e}")
            raise

    def get_medical_context(self, user_id: str, current_query: str, limit: int = 5) -> dict[str, Any]:
        """
        Get relevant medical context for current query

        Args:
            user_id: Open WebUI user ID
            current_query: Current user query
            limit: Maximum number of related conversations to return

        Returns:
            Dict containing medical context information
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # Extract topics from current query
                current_topics = self.extract_medical_topics(current_query)

                # Get user's medical history
                user_context = self._get_user_medical_summary(conn, user_id)

                # Find related conversations
                related_chats = self._find_related_conversations(
                    conn, user_id, current_topics, limit,
                )

                # Get recent medical topics
                recent_topics = self._get_recent_medical_topics(conn, user_id)

                return {
                    "user_id": user_id,
                    "current_topics": current_topics,
                    "user_medical_summary": dict(user_context) if user_context else {},
                    "related_conversations": [dict(chat) for chat in related_chats],
                    "recent_topics": [dict(topic) for topic in recent_topics],
                    "context_available": len(related_chats) > 0 or len(recent_topics) > 0,
                    "generated_at": datetime.utcnow().isoformat(),
                }

        except Exception as e:
            logger.exception(f"Error getting medical context for user {user_id}: {e}")
            return {"error": str(e), "context_available": False}

    def store_conversation_medical_data(
        self,
        chat_id: str,
        user_id: str,
        message_content: str,
        message_role: str = "user",
    ) -> None:
        """
        Extract and store medical data from conversation message

        Args:
            chat_id: Open WebUI chat ID
            user_id: User ID
            message_content: Content of the message
            message_role: Role (user/assistant)
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Extract medical topics
                topics = self.extract_medical_topics(message_content)

                # Store extracted topics
                for topic in topics:
                    self._store_medical_topic(
                        conn, chat_id, f"{chat_id}_{datetime.utcnow().timestamp()}",
                        user_id, topic, message_content,
                    )

                # Check for PHI and flag if detected
                phi_detected, phi_types, risk_level = self.detect_phi(message_content)
                if phi_detected:
                    self._store_phi_flag(conn, chat_id, user_id, phi_types, risk_level)

                # Generate semantic tags
                tags = self._generate_semantic_tags(message_content, topics)
                for tag in tags:
                    self._store_semantic_tag(conn, chat_id, user_id, tag)

                conn.commit()

        except Exception as e:
            logger.exception(f"Error storing medical data for chat {chat_id}: {e}")

    def extract_medical_topics(self, text: str) -> list[dict[str, Any]]:
        """
        Extract medical topics from text using configuration-driven pattern matching

        Args:
            text: Text to analyze

        Returns:
            List of extracted medical topics with categories
        """
        if not self._is_feature_enabled("enable_topic_extraction"):
            return []

        topics = []
        text_lower = text.lower()

        # Get confidence settings from config
        topic_config = self.config.get("topic_extraction", {})
        confidence_settings = topic_config.get("confidence", {})
        category_adjustments = confidence_settings.get("confidence_adjustments", {})
        min_confidence = confidence_settings.get("minimum_topic_confidence", 0.5)

        # Get enabled categories from config
        enabled_categories = topic_config.get("categories", {}).get("enabled", [])

        # Process each category if enabled
        for category in enabled_categories:
            if category not in self.medical_keywords:
                continue

            base_confidence = category_adjustments.get(category, 0.7)
            category_terms = self.medical_keywords[category]

            # Handle nested categories (like conditions.endocrine)
            if isinstance(category_terms, dict):
                # Flatten nested categories
                all_terms = []
                for _subcategory, terms in category_terms.items():
                    if isinstance(terms, list):
                        all_terms.extend(terms)
                category_terms = all_terms
            elif not isinstance(category_terms, list):
                continue

            # Search for terms in text
            for term in category_terms:
                if isinstance(term, str) and term.lower() in text_lower:
                    # Apply context-based confidence adjustments
                    confidence = self._calculate_topic_confidence(
                        term, category, text_lower, base_confidence,
                    )

                    if confidence >= min_confidence:
                        topics.append({
                            "name": term,
                            "category": category,
                            "confidence": confidence,
                        })

        # Remove duplicates and apply final filtering
        unique_topics = self._deduplicate_and_filter_topics(topics)

        logger.debug(f"Extracted {len(unique_topics)} medical topics from text")
        return unique_topics

    def _calculate_topic_confidence(self, term: str, category: str, text: str, base_confidence: float) -> float:
        """Calculate confidence for a topic based on context"""
        confidence = base_confidence

        # Apply context modifiers from config
        if CONFIG_AVAILABLE:
            topic_config = self.config.get("topic_extraction", {})
            extraction_rules = topic_config.get("extraction_rules", {})
            context_modifiers = extraction_rules.get("context_modifiers", {})

            # Boost confidence for certain contexts
            if any(symptom in text for symptom in ["pain", "symptoms", "feeling"]):
                confidence *= context_modifiers.get("with_symptoms", 1.0)

            if any(med_word in text for med_word in ["taking", "prescribed", "medication"]):
                confidence *= context_modifiers.get("with_medications", 1.0)

            if any(proc_word in text for proc_word in ["surgery", "procedure", "treatment"]):
                confidence *= context_modifiers.get("with_procedures", 1.0)

            # Question context (slightly lower confidence)
            if any(q_word in text for q_word in ["what", "how", "when", "why", "?"]):
                confidence *= context_modifiers.get("question_context", 1.0)

            # Past tense (lower confidence for historical information)
            if any(past in text for past in ["was", "had", "were", "used to"]):
                confidence *= context_modifiers.get("past_tense", 1.0)

        return min(confidence, 1.0)  # Cap at 1.0

    def _deduplicate_and_filter_topics(self, topics: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove duplicate topics and apply filtering rules"""
        # Sort by confidence (highest first)
        topics.sort(key=lambda x: x["confidence"], reverse=True)

        unique_topics = []
        seen_names = set()

        for topic in topics:
            name = topic["name"].lower()

            # Skip duplicates
            if name in seen_names:
                continue

            # Apply exclusion rules from config
            if self._should_exclude_topic(topic["name"], topic["category"]):
                continue

            unique_topics.append(topic)
            seen_names.add(name)

        return unique_topics

    def _should_exclude_topic(self, topic_name: str, category: str) -> bool:
        """Check if topic should be excluded based on configuration rules"""
        if not CONFIG_AVAILABLE:
            return False

        topic_config = self.config.get("topic_extraction", {})
        extraction_rules = topic_config.get("extraction_rules", {})
        exclusions = extraction_rules.get("exclusions", [])
        min_lengths = extraction_rules.get("minimum_lengths", {})

        # Check exclusion patterns
        topic_lower = topic_name.lower()
        for exclusion in exclusions:
            if exclusion.lower() in topic_lower:
                return True

        # Check minimum length requirements
        min_length = min_lengths.get(category, 0)
        return len(topic_name) < min_length

    def detect_phi(self, text: str, context: str = None) -> tuple[bool, list[str], str]:
        """
        Configuration-driven PHI detection with conversation context awareness

        Args:
            text: Text to scan for PHI
            context: Conversation context for better accuracy

        Returns:
            Tuple of (phi_detected, phi_types, risk_level)
        """
        if not self._is_feature_enabled("enable_phi_detection"):
            return False, [], "low"

        phi_types = []

        # Check for context exemptions first
        if self._is_exempted_context(text, context):
            logger.debug("Text exempted from PHI detection due to context")
            return False, [], "low"

        # Apply PHI patterns from configuration
        for pattern_type, patterns in self.phi_patterns.items():
            if self._check_phi_patterns(text, patterns):
                phi_types.append(pattern_type)

        # Apply conversation-specific risk adjustments
        risk_multiplier = self._get_conversation_risk_multiplier(text)

        # Determine base risk level
        base_risk_level = self._calculate_base_risk_level(phi_types)

        # Apply context-based confidence adjustments
        adjusted_confidence = self._apply_context_confidence_adjustments(text)

        # Final risk calculation with configurable thresholds
        thresholds = self._get_confidence_thresholds()
        low_threshold = thresholds.get("low_confidence_threshold", 0.3)
        medium_threshold = thresholds.get("medium_confidence_threshold", 0.6)

        if adjusted_confidence < low_threshold:  # Very low confidence, probably false positive
            risk_level = "low"
            phi_types = []
        elif adjusted_confidence < medium_threshold:
            risk_level = "low" if base_risk_level == "medium" else base_risk_level
        else:
            risk_level = base_risk_level

        # Apply risk multiplier from conversation patterns
        if risk_multiplier > 1.0 and risk_level != "high":
            if risk_level == "low":
                risk_level = "medium"
            elif risk_level == "medium":
                risk_level = "high"

        return len(phi_types) > 0, phi_types, risk_level

    def _extract_phi_patterns_from_config(self) -> dict[str, list[str]]:
        """Extract PHI patterns from configuration"""
        if not CONFIG_AVAILABLE or not self.phi_config:
            return self._load_phi_patterns()

        patterns = self.phi_config.get("patterns", {})
        normalized_patterns = {}

        for pattern_type, pattern_list in patterns.items():
            if isinstance(pattern_list, list):
                normalized_patterns[pattern_type] = pattern_list
            elif isinstance(pattern_list, str):
                normalized_patterns[pattern_type] = [pattern_list]

        return normalized_patterns

    def _is_exempted_context(self, text: str, context: str = None) -> bool:
        """Check if text should be exempted from PHI detection based on context"""
        if not CONFIG_AVAILABLE:
            return False

        conversation_exemptions = self.phi_config.get("conversation_exemptions", {})
        text_lower = text.lower()

        # Check medical literature context
        literature_terms = conversation_exemptions.get("medical_literature_context", [])
        if any(term.lower() in text_lower for term in literature_terms):
            return True

        # Check educational context
        educational_terms = conversation_exemptions.get("educational_context", [])
        if any(term.lower() in text_lower for term in educational_terms):
            return True

        # Check system context
        system_terms = conversation_exemptions.get("system_context", [])
        return bool(any(term.lower() in text_lower for term in system_terms))

    def _check_phi_patterns(self, text: str, patterns: list[str]) -> bool:
        """Check if text matches any PHI patterns"""
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)

    def _get_conversation_risk_multiplier(self, text: str) -> float:
        """Get risk multiplier based on conversation patterns"""
        if not CONFIG_AVAILABLE:
            return 1.0

        risk_adjustments = self.phi_config.get("conversation_risk_adjustments", {})
        text_lower = text.lower()

        # Check for reduced risk patterns
        reduced_patterns = risk_adjustments.get("reduced_risk_patterns", {})
        for pattern_group in reduced_patterns.values():
            patterns = pattern_group.get("patterns", [])
            if any(pattern.lower() in text_lower for pattern in patterns):
                return pattern_group.get("risk_multiplier", 1.0)

        # Check for increased risk patterns
        increased_patterns = risk_adjustments.get("increased_risk_patterns", {})
        for pattern_group in increased_patterns.values():
            patterns = pattern_group.get("patterns", [])
            if any(pattern.lower() in text_lower for pattern in patterns):
                return pattern_group.get("risk_multiplier", 1.0)

        return 1.0

    def _calculate_base_risk_level(self, phi_types: list[str]) -> str:
        """Calculate base risk level from PHI types"""
        if not phi_types:
            return "low"

        if not CONFIG_AVAILABLE:
            # Fallback logic
            if len(phi_types) >= 3:
                return "high"
            if len(phi_types) >= 2:
                return "medium"
            return "low"

        # Use configuration risk mappings
        risk_mappings = self.phi_config.get("risk_mappings", {})
        high_risk_types = set(risk_mappings.get("high_risk_types", []))
        medium_risk_types = set(risk_mappings.get("medium_risk_types", []))

        phi_type_set = set(phi_types)

        if phi_type_set.intersection(high_risk_types):
            return "high"
        if phi_type_set.intersection(medium_risk_types):
            return "medium"
        return "low"

    def _get_confidence_thresholds(self) -> dict[str, float]:
        """Get confidence thresholds from configuration"""
        if CONFIG_AVAILABLE and hasattr(self, "phi_config"):
            # Try to get thresholds from conversation memory mode settings
            conversation_memory = self.phi_config.get("conversation_memory", {})
            modes = conversation_memory.get("phi_handling_modes", {})

            # Use balanced_mode thresholds as defaults
            balanced_mode = modes.get("balanced_mode", {})

            return {
                "low_confidence_threshold": balanced_mode.get("flag_threshold", 0.3),  # Below this is very low confidence
                "medium_confidence_threshold": balanced_mode.get("redact_threshold", 0.6),  # Above this is higher confidence
            }

        # Fallback thresholds
        return {
            "low_confidence_threshold": 0.3,
            "medium_confidence_threshold": 0.6,
        }

    def _apply_context_confidence_adjustments(self, text: str) -> float:
        """Apply context-based confidence adjustments"""
        if not CONFIG_AVAILABLE:
            return 1.0

        context_analysis = self.phi_config.get("context_analysis", {})
        if not context_analysis.get("enable_context_analysis", False):
            return 1.0

        confidence_adjustments = context_analysis.get("context_confidence_adjustments", {})
        text_lower = text.lower()
        base_confidence = 1.0

        for _context_type, settings in confidence_adjustments.items():
            keywords = settings.get("keywords", [])
            if any(keyword.lower() in text_lower for keyword in keywords):
                multiplier = settings.get("phi_confidence_multiplier", 1.0)
                base_confidence *= multiplier
                break  # Use first matching context

        return base_confidence

    def _is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled"""
        if CONFIG_AVAILABLE:
            return is_feature_enabled(feature_name)
        # Fallback defaults
        return feature_name in ["enable_medical_context", "enable_topic_extraction", "enable_phi_detection"]

    def get_user_medical_preferences(self, user_id: str) -> dict[str, Any]:
        """Get user's medical context preferences with config defaults"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM user_medical_preferences WHERE user_id = ?",
                    (user_id,),
                )
                result = cursor.fetchone()

                if result:
                    return dict(result)
                # Use configuration defaults
                return self._get_user_preference_defaults()
        except Exception as e:
            logger.exception(f"Error getting preferences for user {user_id}: {e}")
            return self._get_user_preference_defaults()

    def _get_user_preference_defaults(self) -> dict[str, Any]:
        """Get default user preferences from configuration"""
        if CONFIG_AVAILABLE:
            return get_medical_config().get_user_preference_defaults()
        return self._get_default_preferences()

    def _get_default_config(self) -> dict[str, Any]:
        """Get default configuration when config system not available"""
        return {
            "features": {
                "enable_medical_context": True,
                "enable_topic_extraction": True,
                "enable_conversation_linking": True,
                "enable_phi_detection": True,
            },
            "topic_extraction": {
                "confidence": {
                    "minimum_topic_confidence": 0.5,
                    "confidence_adjustments": {
                        "medication": 0.9,
                        "condition": 0.8,
                        "treatment": 0.7,
                        "symptom": 0.6,
                    },
                },
                "categories": {
                    "enabled": ["condition", "medication", "treatment", "symptom"],
                },
            },
            "user_preferences": {
                "defaults": {
                    "enable_medical_context": True,
                    "privacy_level": "standard",
                    "context_retention_days": 365,
                },
            },
        }

    def find_similar_conversations(self, user_id: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """
        Find conversations similar to the current query

        Args:
            user_id: User ID
            query: Current query
            limit: Max results

        Returns:
            List of similar conversations
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # Extract topics from query
                query_topics = self.extract_medical_topics(query)
                topic_names = [t["name"] for t in query_topics]

                if not topic_names:
                    return []

                # Use FTS to find similar conversations
                placeholders = ",".join("?" * len(topic_names))
                sql = f"""
                SELECT DISTINCT
                    mte.chat_id,
                    mte.topic_name,
                    mte.context_snippet,
                    mte.last_mentioned,
                    c.title as chat_title,
                    COUNT(*) as topic_matches
                FROM medical_topics_extracted mte
                LEFT JOIN chat c ON mte.chat_id = c.id
                WHERE mte.user_id = ?
                AND mte.topic_name IN ({placeholders})
                GROUP BY mte.chat_id
                ORDER BY topic_matches DESC, mte.last_mentioned DESC
                LIMIT ?
                """

                params = [user_id] + topic_names + [limit]
                cursor = conn.execute(sql, params)
                results = cursor.fetchall()

                return [dict(row) for row in results]

        except Exception as e:
            logger.exception(f"Error finding similar conversations: {e}")
            return []

    def get_user_medical_preferences(self, user_id: str) -> dict[str, Any]:
        """Get user's medical context preferences"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM user_medical_preferences WHERE user_id = ?",
                    (user_id,),
                )
                result = cursor.fetchone()
                return dict(result) if result else self._get_default_preferences()
        except Exception as e:
            logger.exception(f"Error getting preferences for user {user_id}: {e}")
            return self._get_default_preferences()

    def update_user_medical_preferences(self, user_id: str, preferences: dict[str, Any]) -> bool:
        """Update user's medical context preferences"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                INSERT OR REPLACE INTO user_medical_preferences
                (user_id, enable_medical_context, enable_topic_extraction,
                 enable_conversation_linking, enable_phi_detection, privacy_level,
                 context_retention_days, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    preferences.get("enable_medical_context", True),
                    preferences.get("enable_topic_extraction", True),
                    preferences.get("enable_conversation_linking", True),
                    preferences.get("enable_phi_detection", True),
                    preferences.get("privacy_level", "standard"),
                    preferences.get("context_retention_days", 365),
                    datetime.utcnow().isoformat(),
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.exception(f"Error updating preferences for user {user_id}: {e}")
            return False

    # Private helper methods
    def _get_user_medical_summary(self, conn: sqlite3.Connection, user_id: str) -> sqlite3.Row | None:
        """Get user's medical summary"""
        cursor = conn.execute(
            "SELECT * FROM user_medical_summary WHERE user_id = ?",
            (user_id,),
        )
        return cursor.fetchone()

    def _find_related_conversations(
        self,
        conn: sqlite3.Connection,
        user_id: str,
        current_topics: list[dict[str, Any]],
        limit: int,
    ) -> list[sqlite3.Row]:
        """Find conversations related to current topics"""
        if not current_topics:
            return []

        topic_names = [t["name"] for t in current_topics]
        placeholders = ",".join("?" * len(topic_names))

        sql = f"""
        SELECT DISTINCT
            cr.related_chat_id as chat_id,
            cr.relationship_type,
            cr.similarity_score,
            cr.shared_topics,
            c.title as chat_title
        FROM conversation_relationships cr
        LEFT JOIN chat c ON cr.related_chat_id = c.id
        WHERE cr.user_id = ?
        AND EXISTS (
            SELECT 1 FROM medical_topics_extracted mte
            WHERE mte.chat_id = cr.source_chat_id
            AND mte.topic_name IN ({placeholders})
        )
        ORDER BY cr.similarity_score DESC
        LIMIT ?
        """

        params = [user_id] + topic_names + [limit]
        cursor = conn.execute(sql, params)
        return cursor.fetchall()

    def _get_recent_medical_topics(self, conn: sqlite3.Connection, user_id: str, days: int = 30) -> list[sqlite3.Row]:
        """Get recent medical topics for user"""
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
        cursor = conn.execute(
            "SELECT * FROM recent_medical_topics WHERE user_id = ? AND last_mentioned > ? LIMIT 10",
            (user_id, cutoff_date),
        )
        return cursor.fetchall()

    def _store_medical_topic(
        self,
        conn: sqlite3.Connection,
        chat_id: str,
        message_id: str,
        user_id: str,
        topic: dict[str, Any],
        context: str,
    ) -> None:
        """Store extracted medical topic"""
        conn.execute("""
        INSERT OR IGNORE INTO medical_topics_extracted
        (chat_id, message_id, user_id, topic_category, topic_name, confidence_score, context_snippet)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            chat_id, message_id, user_id, topic["category"], topic["name"],
            topic["confidence"], context[:500],  # Truncate context
        ))

    def _store_phi_flag(
        self,
        conn: sqlite3.Connection,
        chat_id: str,
        user_id: str,
        phi_types: list[str],
        risk_level: str,
    ) -> None:
        """Store PHI detection flag"""
        conn.execute("""
        INSERT OR REPLACE INTO conversation_phi_flags
        (chat_id, user_id, phi_detected, phi_types, risk_level)
        VALUES (?, ?, ?, ?, ?)
        """, (chat_id, user_id, True, json.dumps(phi_types), risk_level))

    def _store_semantic_tag(
        self,
        conn: sqlite3.Connection,
        chat_id: str,
        user_id: str,
        tag: dict[str, Any],
    ) -> None:
        """Store semantic tag"""
        conn.execute("""
        INSERT OR IGNORE INTO conversation_semantic_tags
        (chat_id, user_id, tag_name, tag_category, relevance_score)
        VALUES (?, ?, ?, ?, ?)
        """, (chat_id, user_id, tag["name"], tag.get("category"), tag.get("relevance", 1.0)))

    def _generate_semantic_tags(self, text: str, topics: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Generate semantic tags from text and topics"""
        tags = []

        # Create tags from topics
        for topic in topics:
            tag_name = f"{topic['category']}_{topic['name'].lower().replace(' ', '_')}"
            tags.append({
                "name": tag_name,
                "category": f"{topic['category']}_discussion",
                "relevance": topic["confidence"],
            })

        # Add general medical discussion tag if any topics found
        if topics:
            tags.append({
                "name": "medical_discussion",
                "category": "general",
                "relevance": 0.8,
            })

        return tags

    def _load_medical_keywords(self) -> dict[str, list[str]]:
        """Load medical keywords for topic extraction - fallback when config not available"""
        if CONFIG_AVAILABLE:
            try:
                from ...config.open_webui_config_loader import get_medical_keywords
                return get_medical_keywords()
            except Exception as e:
                logger.warning(f"Could not load medical keywords from config, using fallback: {e}")

        # Fallback keywords when configuration is not available
        return {
            "conditions": [
                "diabetes", "hypertension", "cancer", "depression", "anxiety",
                "arthritis", "asthma", "heart disease", "stroke", "pneumonia",
                "flu", "covid", "infection", "fever", "headache", "migraine",
                "allergies", "eczema", "psoriasis", "obesity", "high blood pressure",
            ],
            "medications": [
                "aspirin", "ibuprofen", "acetaminophen", "metformin", "insulin",
                "lisinopril", "amlodipine", "atorvastatin", "levothyroxine",
                "antibiotics", "prednisone", "albuterol", "warfarin", "gabapentin",
            ],
            "treatments": [
                "surgery", "therapy", "physical therapy", "chemotherapy", "radiation",
                "dialysis", "transplant", "injection", "vaccination", "immunization",
                "treatment", "procedure", "operation", "intervention",
            ],
            "symptoms": [
                "pain", "nausea", "vomiting", "dizziness", "fatigue", "weakness",
                "shortness of breath", "chest pain", "abdominal pain", "back pain",
                "joint pain", "muscle pain", "rash", "swelling", "bruising",
            ],
        }

    def _load_phi_patterns(self) -> dict[str, str]:
        """Load PHI detection patterns - fallback when config not available"""
        if CONFIG_AVAILABLE:
            try:
                from ...config.open_webui_config_loader import get_phi_detection_config
                phi_config = get_phi_detection_config()
                patterns = phi_config.get("patterns", {})

                # Convert list patterns to single regex (use first pattern from each list)
                simple_patterns = {}
                for pattern_type, pattern_list in patterns.items():
                    if isinstance(pattern_list, list) and pattern_list:
                        simple_patterns[pattern_type] = pattern_list[0]
                    elif isinstance(pattern_list, str):
                        simple_patterns[pattern_type] = pattern_list

                if simple_patterns:
                    return simple_patterns
            except Exception as e:
                logger.warning(f"Could not load PHI patterns from config, using fallback: {e}")

        # Fallback patterns when configuration is not available
        return {
            "name": r"\b[A-Z][a-z]+ [A-Z][a-z]+\b",
            "date": r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
            "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        }

    def _get_default_preferences(self) -> dict[str, Any]:
        """Get default user preferences from config or fallback"""
        if CONFIG_AVAILABLE:
            try:
                from ...config.open_webui_config_loader import get_medical_config
                config = get_medical_config()
                return config.get_user_preference_defaults()
            except Exception as e:
                logger.warning(f"Could not load user preference defaults from config, using fallback: {e}")

        # Fallback preferences when configuration is not available
        return {
            "enable_medical_context": True,
            "enable_topic_extraction": True,
            "enable_conversation_linking": True,
            "enable_phi_detection": True,
            "privacy_level": "standard",
            "context_retention_days": 365,
        }


# Convenience functions for Open WebUI integration
def get_enhanced_context(user_id: str, current_query: str, webui_db_path: str = "app/backend/data/webui.db") -> dict[str, Any]:
    """
    Main function to get enhanced medical context for Open WebUI

    Usage in Open WebUI:
    from core.open_webui_extensions.medical_context_manager import get_enhanced_context
    context = get_enhanced_context(user.id, query)
    """
    manager = OpenWebUIMedicalContext(webui_db_path)
    return manager.get_medical_context(user_id, current_query)


def store_conversation_medical_data(
    chat_id: str,
    user_id: str,
    message_content: str,
    webui_db_path: str = "app/backend/data/webui.db",
) -> None:
    """
    Store medical data from conversation

    Usage in Open WebUI:
    from core.open_webui_extensions.medical_context_manager import store_conversation_medical_data
    store_conversation_medical_data(chat.id, user.id, message.content)
    """
    manager = OpenWebUIMedicalContext(webui_db_path)
    manager.store_conversation_medical_data(chat_id, user_id, message_content)


def initialize_medical_context_db(webui_db_path: str = "app/backend/data/webui.db") -> None:
    """
    Initialize medical context tables in Open WebUI database

    Usage:
    from core.open_webui_extensions.medical_context_manager import initialize_medical_context_db
    initialize_medical_context_db()
    """
    manager = OpenWebUIMedicalContext(webui_db_path)
    manager.initialize_medical_tables()
