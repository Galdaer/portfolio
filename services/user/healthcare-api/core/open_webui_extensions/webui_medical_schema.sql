-- Open WebUI SQLite Medical Context Extensions
-- Adds healthcare-aware conversation continuity to existing webui.db
-- Compatible with Open WebUI's existing chat/user tables

-- Medical topics extracted from conversations
-- Links to existing Open WebUI chat messages
CREATE TABLE IF NOT EXISTS medical_topics_extracted (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT NOT NULL, -- References Open WebUI's chat.id
    message_id TEXT NOT NULL, -- References specific message in chat
    user_id TEXT NOT NULL, -- References Open WebUI's user.id  
    topic_category TEXT NOT NULL CHECK (topic_category IN ('condition', 'treatment', 'medication', 'procedure', 'symptom', 'test')),
    topic_name TEXT NOT NULL,
    confidence_score REAL DEFAULT 1.0, -- How confident we are in this extraction
    first_mentioned DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_mentioned DATETIME DEFAULT CURRENT_TIMESTAMP,
    mention_count INTEGER DEFAULT 1,
    context_snippet TEXT, -- Relevant text snippet for context
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- User medical conversation context
-- Tracks ongoing medical themes per user
CREATE TABLE IF NOT EXISTS user_medical_context (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL, -- References Open WebUI's user.id
    medical_topic TEXT NOT NULL, -- e.g., "diabetes management", "hypertension treatment"
    topic_category TEXT NOT NULL,
    importance_score REAL DEFAULT 0.5, -- How important/frequent this topic is
    first_discussed DATETIME NOT NULL,
    last_discussed DATETIME NOT NULL,
    total_conversations INTEGER DEFAULT 1,
    related_chat_ids TEXT, -- JSON array of related chat IDs
    summary TEXT, -- Brief summary of user's context with this topic
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, medical_topic)
);

-- Simple PHI detection flags for privacy
-- Marks conversations that may contain PHI
CREATE TABLE IF NOT EXISTS conversation_phi_flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT NOT NULL, -- References Open WebUI's chat.id
    user_id TEXT NOT NULL,
    phi_detected BOOLEAN DEFAULT FALSE,
    phi_types TEXT, -- JSON array of detected PHI types (names, dates, etc.)
    risk_level TEXT DEFAULT 'low' CHECK (risk_level IN ('low', 'medium', 'high')),
    detection_method TEXT DEFAULT 'pattern_match', -- How PHI was detected
    flagged_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    reviewed BOOLEAN DEFAULT FALSE, -- For manual review workflow
    UNIQUE(chat_id)
);

-- Semantic tags for conversation clustering
-- Groups similar medical conversations without complex vector math
CREATE TABLE IF NOT EXISTS conversation_semantic_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    tag_name TEXT NOT NULL, -- e.g., "diabetes_management", "medication_questions"
    tag_category TEXT, -- medical_condition, treatment_inquiry, medication_info
    relevance_score REAL DEFAULT 1.0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Related conversation links
-- Simple way to connect similar conversations without vector search
CREATE TABLE IF NOT EXISTS conversation_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_chat_id TEXT NOT NULL,
    related_chat_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    relationship_type TEXT DEFAULT 'similar_topic' CHECK (
        relationship_type IN ('similar_topic', 'follow_up', 'continuation', 'related_condition')
    ),
    similarity_score REAL DEFAULT 0.5,
    shared_topics TEXT, -- JSON array of common topics
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_chat_id, related_chat_id)
);

-- User preferences for medical context features
-- Let users control their healthcare conversation features
CREATE TABLE IF NOT EXISTS user_medical_preferences (
    user_id TEXT PRIMARY KEY, -- References Open WebUI's user.id
    enable_medical_context BOOLEAN DEFAULT TRUE,
    enable_topic_extraction BOOLEAN DEFAULT TRUE,
    enable_conversation_linking BOOLEAN DEFAULT TRUE,
    enable_phi_detection BOOLEAN DEFAULT TRUE,
    privacy_level TEXT DEFAULT 'standard' CHECK (privacy_level IN ('minimal', 'standard', 'enhanced')),
    context_retention_days INTEGER DEFAULT 365, -- How long to keep extracted context
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create indices for performance
CREATE INDEX IF NOT EXISTS idx_medical_topics_user_id ON medical_topics_extracted(user_id);
CREATE INDEX IF NOT EXISTS idx_medical_topics_chat_id ON medical_topics_extracted(chat_id);
CREATE INDEX IF NOT EXISTS idx_medical_topics_category ON medical_topics_extracted(topic_category);
CREATE INDEX IF NOT EXISTS idx_medical_topics_name ON medical_topics_extracted(topic_name);
CREATE INDEX IF NOT EXISTS idx_medical_topics_last_mentioned ON medical_topics_extracted(last_mentioned DESC);

CREATE INDEX IF NOT EXISTS idx_user_context_user_id ON user_medical_context(user_id);
CREATE INDEX IF NOT EXISTS idx_user_context_topic ON user_medical_context(medical_topic);
CREATE INDEX IF NOT EXISTS idx_user_context_last_discussed ON user_medical_context(last_discussed DESC);
CREATE INDEX IF NOT EXISTS idx_user_context_importance ON user_medical_context(importance_score DESC);

CREATE INDEX IF NOT EXISTS idx_phi_flags_user_id ON conversation_phi_flags(user_id);
CREATE INDEX IF NOT EXISTS idx_phi_flags_chat_id ON conversation_phi_flags(chat_id);
CREATE INDEX IF NOT EXISTS idx_phi_flags_risk_level ON conversation_phi_flags(risk_level);

CREATE INDEX IF NOT EXISTS idx_semantic_tags_user_id ON conversation_semantic_tags(user_id);
CREATE INDEX IF NOT EXISTS idx_semantic_tags_chat_id ON conversation_semantic_tags(chat_id);
CREATE INDEX IF NOT EXISTS idx_semantic_tags_name ON conversation_semantic_tags(tag_name);

CREATE INDEX IF NOT EXISTS idx_relationships_source ON conversation_relationships(source_chat_id);
CREATE INDEX IF NOT EXISTS idx_relationships_user_id ON conversation_relationships(user_id);
CREATE INDEX IF NOT EXISTS idx_relationships_type ON conversation_relationships(relationship_type);

-- Views for easy data access
-- Medical summary per user
CREATE VIEW IF NOT EXISTS user_medical_summary AS
SELECT 
    u.user_id,
    COUNT(DISTINCT t.topic_name) as unique_topics,
    COUNT(DISTINCT t.chat_id) as medical_conversations,
    GROUP_CONCAT(DISTINCT t.topic_category) as discussed_categories,
    MAX(t.last_mentioned) as last_medical_discussion,
    AVG(c.importance_score) as avg_topic_importance,
    COUNT(CASE WHEN p.phi_detected THEN 1 END) as phi_flagged_conversations
FROM (
    SELECT DISTINCT user_id FROM medical_topics_extracted
) u
LEFT JOIN medical_topics_extracted t ON u.user_id = t.user_id
LEFT JOIN user_medical_context c ON u.user_id = c.user_id
LEFT JOIN conversation_phi_flags p ON u.user_id = p.user_id
GROUP BY u.user_id;

-- Recent medical topics per user
CREATE VIEW IF NOT EXISTS recent_medical_topics AS
SELECT 
    t.user_id,
    t.topic_category,
    t.topic_name,
    t.last_mentioned,
    t.mention_count,
    t.context_snippet,
    c.summary as user_context_summary
FROM medical_topics_extracted t
LEFT JOIN user_medical_context c ON t.user_id = c.user_id AND t.topic_name = c.medical_topic
WHERE t.last_mentioned > datetime('now', '-30 days')
ORDER BY t.user_id, t.last_mentioned DESC;

-- Helper functions for common queries
-- Note: SQLite has limited function support, so these are implemented as views

-- Get related conversations for a given chat
CREATE VIEW IF NOT EXISTS chat_related_conversations AS
SELECT 
    r.source_chat_id as chat_id,
    r.related_chat_id,
    r.relationship_type,
    r.similarity_score,
    r.shared_topics,
    -- Try to get chat title from Open WebUI's chat table (if it exists)
    c.title as related_chat_title
FROM conversation_relationships r
LEFT JOIN chat c ON r.related_chat_id = c.id
ORDER BY r.similarity_score DESC;

-- Triggers to maintain data consistency
-- Update last_mentioned when topic is referenced again
CREATE TRIGGER IF NOT EXISTS update_topic_last_mentioned
    AFTER INSERT ON medical_topics_extracted
    WHEN NEW.topic_name IN (
        SELECT topic_name FROM medical_topics_extracted 
        WHERE user_id = NEW.user_id AND topic_name = NEW.topic_name
    )
BEGIN
    UPDATE medical_topics_extracted 
    SET last_mentioned = NEW.created_at,
        mention_count = mention_count + 1
    WHERE user_id = NEW.user_id 
    AND topic_name = NEW.topic_name 
    AND id != NEW.id;
    
    UPDATE user_medical_context 
    SET last_discussed = NEW.created_at,
        total_conversations = total_conversations + 1,
        updated_at = CURRENT_TIMESTAMP
    WHERE user_id = NEW.user_id 
    AND medical_topic = NEW.topic_name;
END;

-- Auto-create user medical context entry when new topic is extracted
CREATE TRIGGER IF NOT EXISTS create_user_medical_context
    AFTER INSERT ON medical_topics_extracted
    WHEN NEW.topic_name NOT IN (
        SELECT medical_topic FROM user_medical_context 
        WHERE user_id = NEW.user_id
    )
BEGIN
    INSERT OR IGNORE INTO user_medical_context (
        user_id, 
        medical_topic, 
        topic_category,
        first_discussed, 
        last_discussed,
        summary
    ) VALUES (
        NEW.user_id, 
        NEW.topic_name, 
        NEW.topic_category,
        NEW.created_at, 
        NEW.created_at,
        'Medical topic: ' || NEW.topic_name || '. Context: ' || COALESCE(NEW.context_snippet, 'No additional context.')
    );
END;

-- Data retention trigger (cleanup old data based on user preferences)
CREATE TRIGGER IF NOT EXISTS cleanup_old_medical_data
    AFTER INSERT ON medical_topics_extracted
BEGIN
    DELETE FROM medical_topics_extracted 
    WHERE user_id IN (
        SELECT p.user_id 
        FROM user_medical_preferences p 
        WHERE p.context_retention_days > 0
    )
    AND created_at < datetime('now', '-' || (
        SELECT context_retention_days 
        FROM user_medical_preferences 
        WHERE user_id = NEW.user_id
    ) || ' days');
END;

-- Initialize default preferences for new users
-- This would typically be called when a user first uses medical features
CREATE VIEW IF NOT EXISTS ensure_user_medical_preferences AS
SELECT 
    'INSERT OR IGNORE INTO user_medical_preferences (user_id) VALUES (''' || user_id || ''');' as sql_command
FROM (
    SELECT DISTINCT user_id FROM medical_topics_extracted
    WHERE user_id NOT IN (SELECT user_id FROM user_medical_preferences)
);

-- Simple search function simulation using FTS (Full-Text Search)
-- Create FTS virtual table for medical topic search
CREATE VIRTUAL TABLE IF NOT EXISTS medical_topics_fts USING fts5(
    topic_name, 
    context_snippet, 
    content='medical_topics_extracted',
    content_rowid='id'
);

-- Triggers to keep FTS table updated
CREATE TRIGGER IF NOT EXISTS medical_topics_fts_insert 
    AFTER INSERT ON medical_topics_extracted 
BEGIN
    INSERT INTO medical_topics_fts(rowid, topic_name, context_snippet) 
    VALUES (new.id, new.topic_name, new.context_snippet);
END;

CREATE TRIGGER IF NOT EXISTS medical_topics_fts_delete 
    AFTER DELETE ON medical_topics_extracted 
BEGIN
    DELETE FROM medical_topics_fts WHERE rowid = old.id;
END;

CREATE TRIGGER IF NOT EXISTS medical_topics_fts_update 
    AFTER UPDATE ON medical_topics_extracted 
BEGIN
    UPDATE medical_topics_fts 
    SET topic_name = new.topic_name, context_snippet = new.context_snippet 
    WHERE rowid = new.id;
END;

-- Comments for documentation
-- These tables extend Open WebUI's existing database with healthcare-specific functionality
-- while maintaining compatibility with the existing schema.