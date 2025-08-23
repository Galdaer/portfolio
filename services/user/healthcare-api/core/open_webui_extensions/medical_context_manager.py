"""
Open WebUI Medical Context Manager
Provides healthcare-aware conversation continuity by extending Open WebUI's existing SQLite database
"""

import json
import re
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import logging

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
        self.db_path = webui_db_path
        self.medical_keywords = self._load_medical_keywords()
        self.phi_patterns = self._load_phi_patterns()
        
    def initialize_medical_tables(self) -> None:
        """Initialize medical context tables if they don't exist"""
        try:
            # Read and execute the schema file
            schema_path = Path(__file__).parent / "webui_medical_schema.sql"
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.executescript(schema_sql)
                conn.commit()
            
            logger.info("Medical context tables initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize medical tables: {e}")
            raise
    
    def get_medical_context(self, user_id: str, current_query: str, limit: int = 5) -> Dict[str, Any]:
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
                    conn, user_id, current_topics, limit
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
                    "generated_at": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting medical context for user {user_id}: {e}")
            return {"error": str(e), "context_available": False}
    
    def store_conversation_medical_data(
        self, 
        chat_id: str, 
        user_id: str, 
        message_content: str, 
        message_role: str = "user"
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
                        user_id, topic, message_content
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
            logger.error(f"Error storing medical data for chat {chat_id}: {e}")
    
    def extract_medical_topics(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract medical topics from text using pattern matching and keywords
        
        Args:
            text: Text to analyze
            
        Returns:
            List of extracted medical topics with categories
        """
        topics = []
        text_lower = text.lower()
        
        # Check for medical conditions
        for condition in self.medical_keywords.get("conditions", []):
            if condition.lower() in text_lower:
                topics.append({
                    "name": condition,
                    "category": "condition",
                    "confidence": 0.8
                })
        
        # Check for medications
        for medication in self.medical_keywords.get("medications", []):
            if medication.lower() in text_lower:
                topics.append({
                    "name": medication,
                    "category": "medication", 
                    "confidence": 0.9
                })
        
        # Check for treatments/procedures
        for treatment in self.medical_keywords.get("treatments", []):
            if treatment.lower() in text_lower:
                topics.append({
                    "name": treatment,
                    "category": "treatment",
                    "confidence": 0.7
                })
        
        # Check for symptoms
        for symptom in self.medical_keywords.get("symptoms", []):
            if symptom.lower() in text_lower:
                topics.append({
                    "name": symptom,
                    "category": "symptom",
                    "confidence": 0.6
                })
        
        # Remove duplicates and return
        unique_topics = []
        seen_names = set()
        for topic in topics:
            if topic["name"] not in seen_names:
                unique_topics.append(topic)
                seen_names.add(topic["name"])
        
        return unique_topics
    
    def detect_phi(self, text: str) -> Tuple[bool, List[str], str]:
        """
        Simple PHI detection using pattern matching
        
        Args:
            text: Text to scan for PHI
            
        Returns:
            Tuple of (phi_detected, phi_types, risk_level)
        """
        phi_types = []
        
        # Check for names (simple pattern)
        if re.search(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', text):
            phi_types.append("name")
        
        # Check for dates
        if re.search(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', text):
            phi_types.append("date")
        
        # Check for phone numbers
        if re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', text):
            phi_types.append("phone")
        
        # Check for email addresses
        if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text):
            phi_types.append("email")
        
        # Check for SSN pattern
        if re.search(r'\b\d{3}-\d{2}-\d{4}\b', text):
            phi_types.append("ssn")
        
        # Determine risk level
        if len(phi_types) == 0:
            risk_level = "low"
        elif len(phi_types) <= 2:
            risk_level = "medium"  
        else:
            risk_level = "high"
        
        return len(phi_types) > 0, phi_types, risk_level
    
    def find_similar_conversations(self, user_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
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
            logger.error(f"Error finding similar conversations: {e}")
            return []
    
    def get_user_medical_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user's medical context preferences"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM user_medical_preferences WHERE user_id = ?",
                    (user_id,)
                )
                result = cursor.fetchone()
                return dict(result) if result else self._get_default_preferences()
        except Exception as e:
            logger.error(f"Error getting preferences for user {user_id}: {e}")
            return self._get_default_preferences()
    
    def update_user_medical_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
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
                    datetime.utcnow().isoformat()
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating preferences for user {user_id}: {e}")
            return False
    
    # Private helper methods
    def _get_user_medical_summary(self, conn: sqlite3.Connection, user_id: str) -> Optional[sqlite3.Row]:
        """Get user's medical summary"""
        cursor = conn.execute(
            "SELECT * FROM user_medical_summary WHERE user_id = ?",
            (user_id,)
        )
        return cursor.fetchone()
    
    def _find_related_conversations(
        self, 
        conn: sqlite3.Connection, 
        user_id: str, 
        current_topics: List[Dict[str, Any]], 
        limit: int
    ) -> List[sqlite3.Row]:
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
    
    def _get_recent_medical_topics(self, conn: sqlite3.Connection, user_id: str, days: int = 30) -> List[sqlite3.Row]:
        """Get recent medical topics for user"""
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
        cursor = conn.execute(
            "SELECT * FROM recent_medical_topics WHERE user_id = ? AND last_mentioned > ? LIMIT 10",
            (user_id, cutoff_date)
        )
        return cursor.fetchall()
    
    def _store_medical_topic(
        self, 
        conn: sqlite3.Connection, 
        chat_id: str, 
        message_id: str,
        user_id: str, 
        topic: Dict[str, Any], 
        context: str
    ) -> None:
        """Store extracted medical topic"""
        conn.execute("""
        INSERT OR IGNORE INTO medical_topics_extracted 
        (chat_id, message_id, user_id, topic_category, topic_name, confidence_score, context_snippet)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            chat_id, message_id, user_id, topic["category"], topic["name"],
            topic["confidence"], context[:500]  # Truncate context
        ))
    
    def _store_phi_flag(
        self, 
        conn: sqlite3.Connection, 
        chat_id: str, 
        user_id: str, 
        phi_types: List[str], 
        risk_level: str
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
        tag: Dict[str, Any]
    ) -> None:
        """Store semantic tag"""
        conn.execute("""
        INSERT OR IGNORE INTO conversation_semantic_tags 
        (chat_id, user_id, tag_name, tag_category, relevance_score)
        VALUES (?, ?, ?, ?, ?)
        """, (chat_id, user_id, tag["name"], tag.get("category"), tag.get("relevance", 1.0)))
    
    def _generate_semantic_tags(self, text: str, topics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate semantic tags from text and topics"""
        tags = []
        
        # Create tags from topics
        for topic in topics:
            tag_name = f"{topic['category']}_{topic['name'].lower().replace(' ', '_')}"
            tags.append({
                "name": tag_name,
                "category": f"{topic['category']}_discussion", 
                "relevance": topic["confidence"]
            })
        
        # Add general medical discussion tag if any topics found
        if topics:
            tags.append({
                "name": "medical_discussion",
                "category": "general",
                "relevance": 0.8
            })
        
        return tags
    
    def _load_medical_keywords(self) -> Dict[str, List[str]]:
        """Load medical keywords for topic extraction"""
        return {
            "conditions": [
                "diabetes", "hypertension", "cancer", "depression", "anxiety",
                "arthritis", "asthma", "heart disease", "stroke", "pneumonia",
                "flu", "covid", "infection", "fever", "headache", "migraine",
                "allergies", "eczema", "psoriasis", "obesity", "high blood pressure"
            ],
            "medications": [
                "aspirin", "ibuprofen", "acetaminophen", "metformin", "insulin",
                "lisinopril", "amlodipine", "atorvastatin", "levothyroxine",
                "antibiotics", "prednisone", "albuterol", "warfarin", "gabapentin"
            ],
            "treatments": [
                "surgery", "therapy", "physical therapy", "chemotherapy", "radiation",
                "dialysis", "transplant", "injection", "vaccination", "immunization",
                "treatment", "procedure", "operation", "intervention"
            ],
            "symptoms": [
                "pain", "nausea", "vomiting", "dizziness", "fatigue", "weakness",
                "shortness of breath", "chest pain", "abdominal pain", "back pain",
                "joint pain", "muscle pain", "rash", "swelling", "bruising"
            ]
        }
    
    def _load_phi_patterns(self) -> Dict[str, str]:
        """Load PHI detection patterns"""
        return {
            "name": r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',
            "date": r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
            "phone": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "ssn": r'\b\d{3}-\d{2}-\d{4}\b'
        }
    
    def _get_default_preferences(self) -> Dict[str, Any]:
        """Get default user preferences"""
        return {
            "enable_medical_context": True,
            "enable_topic_extraction": True,
            "enable_conversation_linking": True,
            "enable_phi_detection": True,
            "privacy_level": "standard",
            "context_retention_days": 365
        }


# Convenience functions for Open WebUI integration
def get_enhanced_context(user_id: str, current_query: str, webui_db_path: str = "app/backend/data/webui.db") -> Dict[str, Any]:
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
    webui_db_path: str = "app/backend/data/webui.db"
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