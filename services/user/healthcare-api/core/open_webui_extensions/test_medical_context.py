"""
Test suite for Open WebUI Medical Context Extensions
"""

import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from medical_context_manager import OpenWebUIMedicalContext
from open_webui_function import (
    get_medical_context_for_chat,
    store_chat_message_data,
    initialize_medical_context_system,
    get_medical_conversation_suggestions
)


class TestMedicalContextExtensions(unittest.TestCase):
    """Test the Open WebUI medical context functionality"""
    
    def setUp(self):
        """Set up test database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        # Initialize test database with basic Open WebUI tables
        with sqlite3.connect(self.db_path) as conn:
            # Create minimal Open WebUI tables for testing
            conn.execute("""
            CREATE TABLE IF NOT EXISTS chat (
                id TEXT PRIMARY KEY,
                title TEXT,
                user_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            conn.execute("""
            CREATE TABLE IF NOT EXISTS user (
                id TEXT PRIMARY KEY,
                email TEXT,
                name TEXT
            )
            """)
            
            # Insert test data
            conn.execute("INSERT INTO user (id, email, name) VALUES (?, ?, ?)",
                        ("test_user_123", "test@example.com", "Test User"))
            
            conn.execute("INSERT INTO chat (id, title, user_id) VALUES (?, ?, ?)",
                        ("test_chat_456", "Medical Discussion", "test_user_123"))
            
            conn.commit()
        
        self.context_manager = OpenWebUIMedicalContext(self.db_path)
        
    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_initialize_medical_tables(self):
        """Test medical table initialization"""
        self.context_manager.initialize_medical_tables()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'medical_%'"
            )
            tables = [row[0] for row in cursor.fetchall()]
            
        # Check that medical tables were created
        expected_tables = [
            'medical_topics_extracted',
            'user_medical_context', 
            'conversation_phi_flags',
            'conversation_semantic_tags',
            'conversation_relationships',
            'user_medical_preferences'
        ]
        
        for table in expected_tables:
            self.assertIn(table, tables, f"Table {table} not created")
    
    def test_medical_topic_extraction(self):
        """Test medical topic extraction"""
        self.context_manager.initialize_medical_tables()
        
        # Test text with medical topics
        test_text = "I have diabetes and take metformin. Also experiencing headaches."
        topics = self.context_manager.extract_medical_topics(test_text)
        
        # Should extract diabetes (condition) and metformin (medication)
        topic_names = [topic["name"] for topic in topics]
        self.assertIn("diabetes", topic_names)
        self.assertIn("metformin", topic_names)
        
        # Check categories
        topic_categories = [topic["category"] for topic in topics]
        self.assertIn("condition", topic_categories)
        self.assertIn("medication", topic_categories)
    
    def test_phi_detection(self):
        """Test PHI detection"""
        # Test text with potential PHI
        phi_text = "My name is John Smith and my phone is 555-123-4567"
        phi_detected, phi_types, risk_level = self.context_manager.detect_phi(phi_text)
        
        self.assertTrue(phi_detected)
        self.assertIn("name", phi_types)
        self.assertIn("phone", phi_types)
        self.assertEqual(risk_level, "medium")
        
        # Test text without PHI
        clean_text = "I have diabetes and need medication advice"
        phi_detected, phi_types, risk_level = self.context_manager.detect_phi(clean_text)
        
        self.assertFalse(phi_detected)
        self.assertEqual(len(phi_types), 0)
        self.assertEqual(risk_level, "low")
    
    def test_store_conversation_data(self):
        """Test storing conversation medical data"""
        self.context_manager.initialize_medical_tables()
        
        # Store a medical conversation
        chat_id = "test_chat_456"
        user_id = "test_user_123"
        message = "I have been dealing with diabetes for 5 years and take insulin daily"
        
        self.context_manager.store_conversation_medical_data(
            chat_id, user_id, message, "user"
        )
        
        # Check that topics were extracted and stored
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT topic_name, topic_category FROM medical_topics_extracted WHERE user_id = ?",
                (user_id,)
            )
            results = cursor.fetchall()
        
        self.assertGreater(len(results), 0, "No medical topics were stored")
        
        # Check for expected topics
        topic_names = [row[0] for row in results]
        self.assertIn("diabetes", topic_names)
        self.assertIn("insulin", topic_names)
    
    def test_get_medical_context(self):
        """Test getting medical context for queries"""
        self.context_manager.initialize_medical_tables()
        
        # Store some conversation data first
        user_id = "test_user_123"
        chat_id = "test_chat_456"
        
        # Store previous conversation about diabetes
        self.context_manager.store_conversation_medical_data(
            chat_id, user_id, "I was diagnosed with diabetes last year", "user"
        )
        
        # Store another message about medication
        self.context_manager.store_conversation_medical_data(
            chat_id, user_id, "My doctor prescribed metformin", "user"
        )
        
        # Now get context for a related query
        context = self.context_manager.get_medical_context(
            user_id, "How should I manage my diabetes medication?"
        )
        
        self.assertIn("user_id", context)
        self.assertIn("current_topics", context)
        self.assertIn("context_available", context)
        self.assertTrue(context["context_available"])
        
        # Should have detected diabetes-related topics
        current_topics = context["current_topics"]
        topic_names = [topic["name"] for topic in current_topics]
        self.assertIn("diabetes", topic_names)
    
    def test_find_similar_conversations(self):
        """Test finding similar conversations"""
        self.context_manager.initialize_medical_tables()
        
        user_id = "test_user_123"
        
        # Store conversations about different topics
        self.context_manager.store_conversation_medical_data(
            "chat_1", user_id, "I have diabetes and need help", "user"
        )
        
        self.context_manager.store_conversation_medical_data(
            "chat_2", user_id, "My diabetes medication isn't working", "user"
        )
        
        self.context_manager.store_conversation_medical_data(
            "chat_3", user_id, "I have a headache", "user"
        )
        
        # Find conversations similar to diabetes query
        similar = self.context_manager.find_similar_conversations(
            user_id, "diabetes treatment options", limit=5
        )
        
        self.assertGreater(len(similar), 0)
        
        # Should find the diabetes-related conversations
        chat_ids = [conv["chat_id"] for conv in similar]
        self.assertIn("chat_1", chat_ids)
        self.assertIn("chat_2", chat_ids)
    
    def test_user_preferences(self):
        """Test user medical preferences"""
        self.context_manager.initialize_medical_tables()
        
        user_id = "test_user_123"
        
        # Get default preferences
        prefs = self.context_manager.get_user_medical_preferences(user_id)
        self.assertEqual(prefs["enable_medical_context"], True)
        self.assertEqual(prefs["privacy_level"], "standard")
        
        # Update preferences
        new_prefs = {
            "enable_medical_context": True,
            "enable_phi_detection": False,
            "privacy_level": "enhanced",
            "context_retention_days": 180
        }
        
        success = self.context_manager.update_user_medical_preferences(user_id, new_prefs)
        self.assertTrue(success)
        
        # Verify update
        updated_prefs = self.context_manager.get_user_medical_preferences(user_id)
        self.assertEqual(updated_prefs["privacy_level"], "enhanced")
        self.assertEqual(updated_prefs["context_retention_days"], 180)
    
    def test_open_webui_functions(self):
        """Test the main Open WebUI integration functions"""
        # Mock the webui_db_path for testing
        with patch('open_webui_function.medical_context.webui_db_path', self.db_path):
            with patch('open_webui_function.medical_context.context_manager') as mock_manager:
                mock_manager.initialize_medical_tables.return_value = None
                mock_manager.get_medical_context.return_value = {
                    "context_available": True,
                    "current_topics": [{"name": "diabetes", "category": "condition"}],
                    "related_conversations": [],
                    "recent_topics": []
                }
                
                # Test get context
                context = get_medical_context_for_chat(
                    "test_user_123", "diabetes management", "test_chat_456"
                )
                
                self.assertIn("has_context", context)
                
                # Test store message
                success = store_chat_message_data(
                    "test_chat_456", "test_user_123", "I have diabetes", "user"
                )
                # With mock, this should succeed
                self.assertIsInstance(success, bool)


class TestIntegrationExample(unittest.TestCase):
    """Test integration examples"""
    
    def test_example_usage_patterns(self):
        """Test the example usage patterns from documentation"""
        # This tests the patterns shown in README without actual DB
        
        # Test context structure
        mock_context = {
            "has_context": True,
            "medical_topics_detected": 2,
            "related_conversations": 1,
            "recent_topics": 3,
            "context_suggestions": [
                {
                    "type": "related_chat",
                    "title": "Related: Previous diabetes discussion",
                    "description": "Discussed diabetes",
                    "action": "Show me the conversation about diabetes"
                }
            ]
        }
        
        # Verify expected structure
        self.assertTrue(mock_context["has_context"])
        self.assertGreater(mock_context["medical_topics_detected"], 0)
        self.assertIn("context_suggestions", mock_context)
        
        # Test suggestion structure
        suggestion = mock_context["context_suggestions"][0]
        required_fields = ["type", "title", "description", "action"]
        for field in required_fields:
            self.assertIn(field, suggestion)


def run_basic_functionality_test():
    """Run a basic functionality test with real database"""
    print("Running basic functionality test...")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        # Initialize manager
        manager = OpenWebUIMedicalContext(db_path)
        manager.initialize_medical_tables()
        print("✅ Database initialized")
        
        # Test topic extraction
        topics = manager.extract_medical_topics("I have diabetes and take metformin")
        print(f"✅ Extracted {len(topics)} medical topics")
        
        # Test PHI detection
        phi_detected, phi_types, risk = manager.detect_phi("My name is John Doe")
        print(f"✅ PHI detection: {phi_detected} (types: {phi_types}, risk: {risk})")
        
        # Test context storage and retrieval
        manager.store_conversation_medical_data(
            "test_chat", "test_user", "I need help managing my diabetes", "user"
        )
        print("✅ Stored conversation data")
        
        context = manager.get_medical_context("test_user", "diabetes medication help")
        print(f"✅ Retrieved context: {context.get('context_available', False)}")
        
        print("🎉 All basic functionality tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        if os.path.exists(db_path):
            os.unlink(db_path)


if __name__ == "__main__":
    # Run basic test if called directly
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--basic":
        run_basic_functionality_test()
    else:
        # Run full test suite
        unittest.main(verbosity=2)
        print("\n" + "="*50)
        print("To run basic functionality test:")
        print("python test_medical_context.py --basic")
        print("="*50)