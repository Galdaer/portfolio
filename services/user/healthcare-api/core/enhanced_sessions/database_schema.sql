-- Enhanced Session Management Database Schema
-- PHI-aware conversation continuity for Open WebUI
-- Intelluxe AI Healthcare System

-- Enable vector extension for semantic embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- User conversation sessions with PHI handling
CREATE TABLE user_conversation_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    session_title VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_accessed TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    message_count INTEGER DEFAULT 0,
    medical_topics JSONB DEFAULT '[]'::jsonb,
    phi_detected BOOLEAN DEFAULT FALSE,
    privacy_level VARCHAR(50) DEFAULT 'standard', -- standard, high, maximum
    retention_policy VARCHAR(50) DEFAULT 'default', -- default, short, long, permanent
    CONSTRAINT fk_user_sessions FOREIGN KEY (user_id) REFERENCES auth_user(id) ON DELETE CASCADE
);

-- Individual conversation messages with PHI protection
CREATE TABLE user_conversation_messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES user_conversation_sessions(session_id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL, -- user, assistant, system
    message_content TEXT, -- PHI-sanitized content for search/display
    content_encrypted BYTEA, -- Original content encrypted with PHI
    encryption_key_id VARCHAR(100), -- Key reference for decryption
    medical_entities JSONB DEFAULT '[]'::jsonb, -- Extracted medical terms
    topics JSONB DEFAULT '[]'::jsonb, -- Conversation topics
    semantic_embedding VECTOR(768), -- For similarity search
    phi_score FLOAT DEFAULT 0.0, -- PHI detection confidence
    phi_entities JSONB DEFAULT '[]'::jsonb, -- Detected PHI entities (anonymized references)
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    agent_name VARCHAR(100), -- Which agent responded
    processing_metadata JSONB DEFAULT '{}'::jsonb
);

-- Medical topic tracking across conversations
CREATE TABLE user_medical_context (
    context_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    topic_category VARCHAR(100) NOT NULL, -- condition, treatment, medication, procedure, test
    topic_name VARCHAR(255) NOT NULL,
    topic_code VARCHAR(50), -- ICD-10, CPT, etc. when available
    normalized_name VARCHAR(255), -- Standardized medical term
    first_discussed TIMESTAMP WITH TIME ZONE NOT NULL,
    last_discussed TIMESTAMP WITH TIME ZONE NOT NULL,
    conversation_count INTEGER DEFAULT 1,
    confidence_score FLOAT DEFAULT 1.0, -- Confidence in topic extraction
    importance_score FLOAT DEFAULT 0.5, -- Clinical importance/frequency
    related_topics JSONB DEFAULT '[]'::jsonb, -- Connected medical topics
    source_sessions UUID[] DEFAULT '{}', -- Sessions where discussed
    semantic_embedding VECTOR(768), -- Topic embedding for similarity
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Cross-session conversation relationships
CREATE TABLE conversation_relationships (
    relationship_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_session_id UUID NOT NULL REFERENCES user_conversation_sessions(session_id),
    related_session_id UUID NOT NULL REFERENCES user_conversation_sessions(session_id),
    user_id VARCHAR(255) NOT NULL,
    relationship_type VARCHAR(50) NOT NULL, -- continuation, related_topic, follow_up, clarification
    similarity_score FLOAT DEFAULT 0.0, -- Semantic similarity
    shared_topics JSONB DEFAULT '[]'::jsonb, -- Common medical topics
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- PHI detection audit log
CREATE TABLE phi_detection_log (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID REFERENCES user_conversation_messages(message_id),
    user_id VARCHAR(255) NOT NULL,
    phi_type VARCHAR(100), -- name, ssn, date_of_birth, phone, email, address, medical_record_number
    detection_confidence FLOAT NOT NULL,
    detection_method VARCHAR(100), -- regex, nlp_model, rule_based
    original_text_hash VARCHAR(64), -- SHA-256 hash for audit
    sanitized_replacement TEXT, -- What it was replaced with
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reviewed_by VARCHAR(255), -- For manual review workflow
    review_status VARCHAR(50) DEFAULT 'pending' -- pending, confirmed, false_positive
);

-- User privacy preferences
CREATE TABLE user_privacy_settings (
    user_id VARCHAR(255) PRIMARY KEY,
    conversation_retention_days INTEGER DEFAULT 365,
    phi_detection_enabled BOOLEAN DEFAULT TRUE,
    cross_session_linking BOOLEAN DEFAULT TRUE,
    semantic_search_enabled BOOLEAN DEFAULT TRUE,
    data_sharing_consent BOOLEAN DEFAULT FALSE,
    auto_summarization BOOLEAN DEFAULT TRUE,
    privacy_level VARCHAR(50) DEFAULT 'standard',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Conversation search cache for performance
CREATE TABLE conversation_search_cache (
    cache_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    search_query VARCHAR(1000) NOT NULL,
    search_type VARCHAR(50) NOT NULL, -- semantic, keyword, medical_topic
    results JSONB NOT NULL, -- Cached search results
    result_count INTEGER DEFAULT 0,
    search_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '1 hour')
);

-- Create indices for performance
CREATE INDEX idx_user_conversations_user_id ON user_conversation_sessions(user_id);
CREATE INDEX idx_user_conversations_created_at ON user_conversation_sessions(created_at DESC);
CREATE INDEX idx_user_conversations_medical_topics ON user_conversation_sessions USING GIN(medical_topics);

CREATE INDEX idx_messages_session_id ON user_conversation_messages(session_id);
CREATE INDEX idx_messages_user_id ON user_conversation_messages(user_id);
CREATE INDEX idx_messages_timestamp ON user_conversation_messages(timestamp DESC);
CREATE INDEX idx_messages_agent ON user_conversation_messages(agent_name);
CREATE INDEX idx_messages_topics ON user_conversation_messages USING GIN(topics);
CREATE INDEX idx_messages_medical_entities ON user_conversation_messages USING GIN(medical_entities);

-- Vector similarity search indices
CREATE INDEX idx_messages_semantic_embedding ON user_conversation_messages USING ivfflat (semantic_embedding vector_cosine_ops);
CREATE INDEX idx_medical_context_embedding ON user_medical_context USING ivfflat (semantic_embedding vector_cosine_ops);

CREATE INDEX idx_medical_context_user_id ON user_medical_context(user_id);
CREATE INDEX idx_medical_context_topic_category ON user_medical_context(topic_category);
CREATE INDEX idx_medical_context_last_discussed ON user_medical_context(last_discussed DESC);
CREATE INDEX idx_medical_context_importance ON user_medical_context(importance_score DESC);

CREATE INDEX idx_relationships_source_session ON conversation_relationships(source_session_id);
CREATE INDEX idx_relationships_related_session ON conversation_relationships(related_session_id);
CREATE INDEX idx_relationships_user_id ON conversation_relationships(user_id);
CREATE INDEX idx_relationships_type ON conversation_relationships(relationship_type);

CREATE INDEX idx_phi_log_message_id ON phi_detection_log(message_id);
CREATE INDEX idx_phi_log_user_id ON phi_detection_log(user_id);
CREATE INDEX idx_phi_log_detected_at ON phi_detection_log(detected_at DESC);

CREATE INDEX idx_search_cache_user_query ON conversation_search_cache(user_id, search_query);
CREATE INDEX idx_search_cache_expires ON conversation_search_cache(expires_at);

-- Create full-text search indices
CREATE INDEX idx_messages_content_fts ON user_conversation_messages USING gin(to_tsvector('english', message_content));
CREATE INDEX idx_sessions_title_fts ON user_conversation_sessions USING gin(to_tsvector('english', session_title));
CREATE INDEX idx_medical_context_name_fts ON user_medical_context USING gin(to_tsvector('english', topic_name));

-- Add constraints
ALTER TABLE user_conversation_messages ADD CONSTRAINT chk_role 
    CHECK (role IN ('user', 'assistant', 'system'));

ALTER TABLE user_medical_context ADD CONSTRAINT chk_topic_category 
    CHECK (topic_category IN ('condition', 'treatment', 'medication', 'procedure', 'test', 'symptom', 'anatomy'));

ALTER TABLE conversation_relationships ADD CONSTRAINT chk_relationship_type 
    CHECK (relationship_type IN ('continuation', 'related_topic', 'follow_up', 'clarification', 'similar_case'));

ALTER TABLE user_privacy_settings ADD CONSTRAINT chk_privacy_level 
    CHECK (privacy_level IN ('minimal', 'standard', 'high', 'maximum'));

-- Data retention policies
CREATE OR REPLACE FUNCTION enforce_data_retention() RETURNS void AS $$
DECLARE
    user_record RECORD;
BEGIN
    -- Clean up expired conversations based on user preferences
    FOR user_record IN 
        SELECT user_id, conversation_retention_days 
        FROM user_privacy_settings 
        WHERE conversation_retention_days > 0
    LOOP
        DELETE FROM user_conversation_sessions 
        WHERE user_id = user_record.user_id 
        AND created_at < (NOW() - INTERVAL '1 day' * user_record.conversation_retention_days);
    END LOOP;
    
    -- Clean up expired search cache
    DELETE FROM conversation_search_cache WHERE expires_at < NOW();
    
    -- Archive old PHI detection logs (keep for audit but mark as archived)
    UPDATE phi_detection_log 
    SET review_status = 'archived' 
    WHERE detected_at < (NOW() - INTERVAL '2 years') 
    AND review_status IN ('confirmed', 'false_positive');
END;
$$ LANGUAGE plpgsql;

-- PHI sanitization functions
CREATE OR REPLACE FUNCTION sanitize_phi_content(
    original_content TEXT,
    phi_entities JSONB DEFAULT '[]'::jsonb
) RETURNS TEXT AS $$
DECLARE
    sanitized_content TEXT;
    entity JSONB;
BEGIN
    sanitized_content := original_content;
    
    -- Replace PHI entities with placeholders
    FOR entity IN SELECT * FROM jsonb_array_elements(phi_entities)
    LOOP
        sanitized_content := regexp_replace(
            sanitized_content,
            entity->>'original_text',
            '[' || UPPER(entity->>'type') || '_REDACTED]',
            'gi'
        );
    END LOOP;
    
    RETURN sanitized_content;
END;
$$ LANGUAGE plpgsql;

-- Create materialized view for user medical summary
CREATE MATERIALIZED VIEW user_medical_summary AS
SELECT 
    user_id,
    COUNT(DISTINCT session_id) as total_sessions,
    COUNT(*) as total_messages,
    COUNT(DISTINCT (topics->>'category')) as unique_topic_categories,
    MAX(timestamp) as last_conversation,
    MIN(timestamp) as first_conversation,
    AVG(phi_score) as avg_phi_risk,
    ARRAY_AGG(DISTINCT agent_name) FILTER (WHERE agent_name IS NOT NULL) as agents_used,
    jsonb_agg(DISTINCT topics) FILTER (WHERE topics != '[]'::jsonb) as all_topics
FROM user_conversation_messages
GROUP BY user_id;

CREATE UNIQUE INDEX ON user_medical_summary (user_id);

-- Trigger to refresh materialized view
CREATE OR REPLACE FUNCTION refresh_user_medical_summary()
RETURNS TRIGGER AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY user_medical_summary;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_refresh_medical_summary
    AFTER INSERT OR UPDATE OR DELETE ON user_conversation_messages
    FOR EACH STATEMENT EXECUTE FUNCTION refresh_user_medical_summary();

-- Create view for privacy-compliant conversation access
CREATE VIEW conversation_messages_view AS
SELECT 
    m.message_id,
    m.session_id,
    m.user_id,
    m.role,
    CASE 
        WHEN p.privacy_level = 'maximum' THEN '[PRIVACY_PROTECTED]'
        WHEN m.phi_score > 0.7 THEN sanitize_phi_content(m.message_content, m.phi_entities)
        ELSE m.message_content
    END as safe_content,
    m.medical_entities,
    m.topics,
    m.timestamp,
    m.agent_name
FROM user_conversation_messages m
LEFT JOIN user_privacy_settings p ON m.user_id = p.user_id
WHERE 
    (p.privacy_level IS NULL OR p.privacy_level != 'maximum')
    OR CURRENT_USER = 'healthcare_admin'; -- Admins can see all with proper access

-- Comments for documentation
COMMENT ON TABLE user_conversation_sessions IS 'Stores conversation sessions with PHI-aware metadata';
COMMENT ON TABLE user_conversation_messages IS 'Individual messages with PHI detection and semantic embeddings';
COMMENT ON TABLE user_medical_context IS 'Tracks medical topics and context across user conversations';
COMMENT ON TABLE phi_detection_log IS 'Audit log for PHI detection and sanitization';
COMMENT ON COLUMN user_conversation_messages.semantic_embedding IS 'Vector embedding for semantic similarity search';
COMMENT ON COLUMN user_conversation_messages.phi_score IS 'Confidence score for PHI detection (0-1)';