-- Healthcare Private Database Schema (intelluxe_clinical)
-- Contains PHI and sensitive clinical data requiring HIPAA compliance
--
-- MEDICAL DISCLAIMER: This database contains protected health information (PHI).
-- Access is restricted and logged for HIPAA compliance. All medical decisions
-- must be made by qualified healthcare professionals.

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "timescaledb" CASCADE;

-- Enable row level security globally
ALTER DATABASE intelluxe_clinical SET row_security = on;

-- =====================================================
-- CORE APPOINTMENT TABLES WITH PHI
-- =====================================================

-- Core appointments table with patient PHI
CREATE TABLE IF NOT EXISTS appointments (
    id SERIAL PRIMARY KEY,
    appointment_uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    
    -- Patient PHI (encrypted at application level)
    patient_id VARCHAR(255) NOT NULL,
    patient_name VARCHAR(255),  -- PHI
    patient_dob DATE,  -- PHI  
    patient_phone VARCHAR(50),  -- PHI
    patient_email VARCHAR(255),  -- PHI
    
    -- Appointment details
    provider_id VARCHAR(255) NOT NULL,
    facility_id VARCHAR(255),
    appointment_datetime TIMESTAMP NOT NULL,
    appointment_type_id INTEGER,
    duration_minutes INTEGER DEFAULT 30,
    
    -- Status and workflow
    status VARCHAR(50) DEFAULT 'scheduled',
    -- scheduled, confirmed, checked_in, in_progress, completed, cancelled, no_show
    
    -- Clinical information (PHI)
    chief_complaint TEXT,  -- PHI
    appointment_notes TEXT,  -- PHI
    special_instructions TEXT,  -- PHI
    interpreter_needed BOOLEAN DEFAULT false,
    accessibility_requirements TEXT,  -- PHI
    
    -- Insurance and billing (PHI)
    insurance_id VARCHAR(255),  -- PHI
    insurance_group VARCHAR(255),  -- PHI
    copay_amount DECIMAL(10,2),
    prior_authorization VARCHAR(255),
    
    -- Scheduling metadata
    scheduled_by VARCHAR(255),
    rescheduled_from INTEGER REFERENCES appointments(id),
    cancellation_reason VARCHAR(255),
    no_show_reason VARCHAR(255),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,  -- Soft delete for audit trail
    
    -- Audit fields
    created_by VARCHAR(255),
    updated_by VARCHAR(255),
    version INTEGER DEFAULT 1,
    
    CONSTRAINT appointments_datetime_future CHECK (appointment_datetime > CURRENT_TIMESTAMP - INTERVAL '1 day'),
    CONSTRAINT valid_status CHECK (status IN ('scheduled', 'confirmed', 'checked_in', 'in_progress', 'completed', 'cancelled', 'no_show'))
);

-- Patient scheduling preferences (PHI)
CREATE TABLE IF NOT EXISTS patient_scheduling_preferences (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR(255) UNIQUE NOT NULL,
    
    -- Scheduling preferences (PHI)
    preferred_times JSONB,  -- e.g., {"morning": true, "afternoon": false, "days": ["monday", "wednesday"]}
    preferred_providers JSONB,  -- Provider IDs and preferences
    preferred_facilities JSONB,  -- Facility preferences
    
    -- Accessibility and special needs (PHI)
    accessibility_needs TEXT,  -- PHI - wheelchair access, mobility aids, etc.
    communication_preferences JSONB,  -- Language, interpreter, contact methods
    transportation_notes TEXT,  -- PHI - transportation limitations
    
    -- Medical scheduling considerations (PHI)
    medical_restrictions JSONB,  -- Fasting requirements, medication timing
    appointment_spacing_requirements TEXT,  -- Time between appointments
    
    -- Contact preferences (PHI)
    reminder_preferences JSONB,  -- Email, SMS, call preferences
    emergency_contact JSONB,  -- PHI - emergency contact information
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_by VARCHAR(255)
);

-- Wait time tracking with patient context
CREATE TABLE IF NOT EXISTS appointment_wait_times (
    id SERIAL PRIMARY KEY,
    appointment_id INTEGER REFERENCES appointments(id),
    patient_id VARCHAR(255) NOT NULL,  -- PHI
    
    -- Wait time tracking
    scheduled_time TIMESTAMP NOT NULL,
    check_in_time TIMESTAMP,
    called_back_time TIMESTAMP,
    provider_seen_time TIMESTAMP,
    appointment_end_time TIMESTAMP,
    
    -- Calculated wait times
    wait_minutes INTEGER,
    total_visit_minutes INTEGER,
    
    -- Wait experience (PHI - patient feedback)
    patient_satisfaction_score INTEGER CHECK (patient_satisfaction_score BETWEEN 1 AND 10),
    wait_experience_notes TEXT,  -- PHI
    
    -- Context information
    facility_busy_level VARCHAR(50),  -- low, moderate, high
    delay_reasons JSONB,
    staff_notes TEXT,  -- PHI
    
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    recorded_by VARCHAR(255)
);

-- Clinical scheduling notes and requirements (PHI)
CREATE TABLE IF NOT EXISTS scheduling_clinical_notes (
    id SERIAL PRIMARY KEY,
    appointment_id INTEGER REFERENCES appointments(id),
    patient_id VARCHAR(255) NOT NULL,  -- PHI
    
    -- Clinical scheduling information (PHI)
    clinical_priority VARCHAR(50),  -- routine, urgent, emergent, stat
    medical_requirements TEXT,  -- PHI - prep instructions, medical needs
    pre_visit_instructions TEXT,  -- PHI - fasting, medication holds
    post_visit_followup TEXT,  -- PHI - follow-up care instructions
    
    -- Provider specific notes (PHI)
    provider_notes TEXT,  -- PHI
    nursing_notes TEXT,  -- PHI
    scheduling_alerts JSONB,  -- Critical scheduling information
    
    -- Coordination requirements
    requires_coordination BOOLEAN DEFAULT false,
    coordination_notes TEXT,  -- Multi-provider coordination
    
    -- Metadata
    created_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_clinical_priority CHECK (clinical_priority IN ('routine', 'urgent', 'emergent', 'stat'))
);

-- Patient communication log (PHI)
CREATE TABLE IF NOT EXISTS patient_communications (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR(255) NOT NULL,  -- PHI
    appointment_id INTEGER REFERENCES appointments(id),
    
    -- Communication details (PHI)
    communication_type VARCHAR(50),  -- email, sms, phone, mail, portal
    communication_content TEXT,  -- PHI - message content
    communication_direction VARCHAR(50),  -- inbound, outbound
    
    -- Contact information used (PHI)
    contact_method VARCHAR(255),  -- PHI - phone number, email used
    
    -- Status and response
    delivery_status VARCHAR(50),  -- sent, delivered, read, failed
    patient_response TEXT,  -- PHI
    response_timestamp TIMESTAMP,
    
    -- Metadata
    sent_by VARCHAR(255),
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_communication_type CHECK (communication_type IN ('email', 'sms', 'phone', 'mail', 'portal')),
    CONSTRAINT valid_communication_direction CHECK (communication_direction IN ('inbound', 'outbound'))
);

-- =====================================================
-- SESSION AND INTERACTION TABLES
-- =====================================================

-- Enhanced clinical sessions (PHI)
CREATE TABLE IF NOT EXISTS clinical_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    patient_id VARCHAR(255),  -- PHI (may be null for anonymous sessions)
    
    -- Session details
    session_type VARCHAR(100),  -- intake, scheduling, consultation, etc.
    session_status VARCHAR(50) DEFAULT 'active',
    
    -- PHI content tracking
    contains_phi BOOLEAN DEFAULT false,
    phi_detected_at TIMESTAMP,
    phi_sanitized_at TIMESTAMP,
    
    -- Session metadata (potentially PHI)
    session_context JSONB,  -- Session context that may contain PHI
    user_agent TEXT,
    ip_address INET,  -- Could be considered PII
    
    -- Timestamps
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Cleanup tracking
    expires_at TIMESTAMP,
    archived_at TIMESTAMP
);

-- Voice intake sessions (PHI)
CREATE TABLE IF NOT EXISTS voice_intake_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    patient_id VARCHAR(255),  -- PHI
    
    -- Voice session details (PHI)
    transcription_text TEXT,  -- PHI - voice transcription
    confidence_score DECIMAL(5,4),
    audio_duration_seconds INTEGER,
    
    -- Medical content extracted (PHI)
    medical_terms JSONB,  -- PHI - extracted medical information
    chief_complaint TEXT,  -- PHI
    symptoms_mentioned JSONB,  -- PHI
    
    -- Form data populated (PHI)
    form_data JSONB,  -- PHI - patient information extracted
    form_completion_percentage DECIMAL(5,2),
    
    -- Quality metrics
    audio_quality_score DECIMAL(5,4),
    background_noise_level VARCHAR(50),
    transcription_quality VARCHAR(50),
    
    -- PHI protection
    phi_detected BOOLEAN DEFAULT false,
    phi_sanitized BOOLEAN DEFAULT false,
    sanitization_notes TEXT,
    
    -- Processing metadata
    processing_status VARCHAR(50),  -- processing, completed, failed
    error_messages JSONB,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    archived_at TIMESTAMP,
    
    -- Audit
    processed_by VARCHAR(255),
    reviewed_by VARCHAR(255)
);

-- Transcription records (PHI)
CREATE TABLE IF NOT EXISTS transcription_records (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255),
    patient_id VARCHAR(255),  -- PHI
    
    -- Audio metadata
    audio_file_path VARCHAR(500),  -- Encrypted storage path
    audio_duration_seconds DECIMAL(8,2),
    audio_format VARCHAR(50),
    audio_quality_metrics JSONB,
    
    -- Transcription results (PHI)
    transcription_text TEXT,  -- PHI - full transcription
    confidence_score DECIMAL(5,4),
    speaker_identification JSONB,  -- PHI - who said what
    
    -- Medical content analysis (PHI)
    medical_entities JSONB,  -- PHI - extracted medical terms
    clinical_notes TEXT,  -- PHI - structured clinical information
    
    -- Processing information
    transcription_engine VARCHAR(100),
    processing_time_ms INTEGER,
    post_processing_applied JSONB,
    
    -- PHI and security
    phi_detected BOOLEAN DEFAULT true,  -- Assume PHI until proven otherwise
    encryption_key_id VARCHAR(255),
    phi_sanitization_log JSONB,
    
    -- Quality assurance
    human_reviewed BOOLEAN DEFAULT false,
    review_notes TEXT,
    accuracy_score DECIMAL(5,4),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP,
    archived_at TIMESTAMP,
    created_by VARCHAR(255),
    reviewed_by VARCHAR(255)
);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

-- Appointments indexes
CREATE INDEX IF NOT EXISTS idx_appointments_patient_id ON appointments(patient_id);
CREATE INDEX IF NOT EXISTS idx_appointments_provider_id ON appointments(provider_id);
CREATE INDEX IF NOT EXISTS idx_appointments_datetime ON appointments(appointment_datetime);
CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status);
CREATE INDEX IF NOT EXISTS idx_appointments_facility ON appointments(facility_id);
CREATE INDEX IF NOT EXISTS idx_appointments_created_at ON appointments(created_at);

-- Patient preferences indexes
CREATE INDEX IF NOT EXISTS idx_patient_preferences_patient_id ON patient_scheduling_preferences(patient_id);

-- Wait times indexes  
CREATE INDEX IF NOT EXISTS idx_wait_times_appointment_id ON appointment_wait_times(appointment_id);
CREATE INDEX IF NOT EXISTS idx_wait_times_patient_id ON appointment_wait_times(patient_id);
CREATE INDEX IF NOT EXISTS idx_wait_times_check_in ON appointment_wait_times(check_in_time);

-- Clinical notes indexes
CREATE INDEX IF NOT EXISTS idx_clinical_notes_appointment_id ON scheduling_clinical_notes(appointment_id);
CREATE INDEX IF NOT EXISTS idx_clinical_notes_patient_id ON scheduling_clinical_notes(patient_id);
CREATE INDEX IF NOT EXISTS idx_clinical_notes_priority ON scheduling_clinical_notes(clinical_priority);

-- Communications indexes
CREATE INDEX IF NOT EXISTS idx_patient_communications_patient_id ON patient_communications(patient_id);
CREATE INDEX IF NOT EXISTS idx_patient_communications_appointment_id ON patient_communications(appointment_id);
CREATE INDEX IF NOT EXISTS idx_patient_communications_sent_at ON patient_communications(sent_at);

-- Sessions indexes
CREATE INDEX IF NOT EXISTS idx_clinical_sessions_session_id ON clinical_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_clinical_sessions_patient_id ON clinical_sessions(patient_id);
CREATE INDEX IF NOT EXISTS idx_clinical_sessions_started_at ON clinical_sessions(started_at);

-- Voice sessions indexes
CREATE INDEX IF NOT EXISTS idx_voice_sessions_session_id ON voice_intake_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_voice_sessions_patient_id ON voice_intake_sessions(patient_id);
CREATE INDEX IF NOT EXISTS idx_voice_sessions_created_at ON voice_intake_sessions(created_at);

-- Transcription indexes
CREATE INDEX IF NOT EXISTS idx_transcription_session_id ON transcription_records(session_id);
CREATE INDEX IF NOT EXISTS idx_transcription_patient_id ON transcription_records(patient_id);
CREATE INDEX IF NOT EXISTS idx_transcription_created_at ON transcription_records(created_at);

-- =====================================================
-- TIMESCALE HYPERTABLES FOR TIME-SERIES DATA
-- =====================================================

-- Convert time-series tables to hypertables
SELECT create_hypertable('appointments', 'created_at', if_not_exists => TRUE);
SELECT create_hypertable('appointment_wait_times', 'recorded_at', if_not_exists => TRUE);
SELECT create_hypertable('patient_communications', 'sent_at', if_not_exists => TRUE);
SELECT create_hypertable('clinical_sessions', 'started_at', if_not_exists => TRUE);
SELECT create_hypertable('voice_intake_sessions', 'created_at', if_not_exists => TRUE);
SELECT create_hypertable('transcription_records', 'created_at', if_not_exists => TRUE);

-- =====================================================
-- ROW LEVEL SECURITY (RLS)
-- =====================================================

-- Enable RLS on all PHI tables
ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;
ALTER TABLE patient_scheduling_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE appointment_wait_times ENABLE ROW LEVEL SECURITY;
ALTER TABLE scheduling_clinical_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE patient_communications ENABLE ROW LEVEL SECURITY;
ALTER TABLE clinical_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE voice_intake_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE transcription_records ENABLE ROW LEVEL SECURITY;

-- Create RLS policies (example - customize based on your access control needs)
-- These policies should be customized based on your specific user roles and access patterns

-- Appointments: Users can only see their own data or data they're authorized for
CREATE POLICY appointments_access_policy ON appointments
    FOR ALL
    TO intelluxe_clinical_users
    USING (
        patient_id = current_setting('app.current_patient_id', true)
        OR provider_id = current_setting('app.current_provider_id', true)
        OR current_setting('app.user_role', true) = 'admin'
    );

-- =====================================================
-- AUDIT TRIGGERS
-- =====================================================

-- Create audit log table
CREATE TABLE IF NOT EXISTS phi_access_audit (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    operation VARCHAR(10) NOT NULL,
    user_id VARCHAR(255),
    patient_id VARCHAR(255),  -- PHI accessed
    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    query_hash VARCHAR(64),  -- Hash of the query for analysis
    ip_address INET,
    session_id VARCHAR(255),
    success BOOLEAN DEFAULT true,
    error_message TEXT
);

-- Audit trigger function
CREATE OR REPLACE FUNCTION phi_access_audit_trigger()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO phi_access_audit (
        table_name, 
        operation, 
        user_id, 
        patient_id,
        query_hash,
        ip_address,
        session_id
    ) VALUES (
        TG_TABLE_NAME,
        TG_OP,
        current_setting('app.current_user_id', true),
        COALESCE(NEW.patient_id, OLD.patient_id),
        md5(current_query()),
        inet_client_addr(),
        current_setting('app.session_id', true)
    );
    
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create audit triggers on PHI tables
CREATE TRIGGER appointments_audit_trigger
    AFTER INSERT OR UPDATE OR DELETE ON appointments
    FOR EACH ROW EXECUTE FUNCTION phi_access_audit_trigger();

CREATE TRIGGER patient_preferences_audit_trigger  
    AFTER INSERT OR UPDATE OR DELETE ON patient_scheduling_preferences
    FOR EACH ROW EXECUTE FUNCTION phi_access_audit_trigger();

CREATE TRIGGER wait_times_audit_trigger
    AFTER INSERT OR UPDATE OR DELETE ON appointment_wait_times  
    FOR EACH ROW EXECUTE FUNCTION phi_access_audit_trigger();

CREATE TRIGGER clinical_notes_audit_trigger
    AFTER INSERT OR UPDATE OR DELETE ON scheduling_clinical_notes
    FOR EACH ROW EXECUTE FUNCTION phi_access_audit_trigger();

CREATE TRIGGER communications_audit_trigger
    AFTER INSERT OR UPDATE OR DELETE ON patient_communications
    FOR EACH ROW EXECUTE FUNCTION phi_access_audit_trigger();

-- =====================================================
-- DATA RETENTION POLICIES
-- =====================================================

-- Retention policy for audit logs (7 years per HIPAA)
SELECT add_retention_policy('phi_access_audit', INTERVAL '7 years');

-- Retention policy for old appointment data (customize based on requirements)
-- Note: Be careful with retention on PHI data - must comply with HIPAA requirements
SELECT add_retention_policy('appointment_wait_times', INTERVAL '10 years');

-- =====================================================
-- INITIAL SECURITY SETUP
-- =====================================================

-- Create database roles
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'intelluxe_clinical_admin') THEN
        CREATE ROLE intelluxe_clinical_admin WITH LOGIN ENCRYPTED PASSWORD 'change_this_password';
    END IF;
    
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'intelluxe_clinical_users') THEN
        CREATE ROLE intelluxe_clinical_users;
    END IF;
    
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'intelluxe_clinical_readonly') THEN
        CREATE ROLE intelluxe_clinical_readonly;
    END IF;
END
$$;

-- Grant appropriate permissions
GRANT USAGE ON SCHEMA public TO intelluxe_clinical_users;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO intelluxe_clinical_users;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO intelluxe_clinical_users;

GRANT USAGE ON SCHEMA public TO intelluxe_clinical_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO intelluxe_clinical_readonly;

-- Admin gets all permissions
GRANT ALL PRIVILEGES ON DATABASE intelluxe_clinical TO intelluxe_clinical_admin;

-- =====================================================
-- COMMENTS AND DOCUMENTATION
-- =====================================================

COMMENT ON DATABASE intelluxe_clinical IS 'Private database containing PHI and sensitive clinical data for Intelluxe AI healthcare system. All access is audited and logged for HIPAA compliance.';

COMMENT ON TABLE appointments IS 'Core appointment records containing patient PHI including names, contact information, and clinical details';
COMMENT ON TABLE patient_scheduling_preferences IS 'Patient scheduling preferences and accessibility needs - contains PHI';
COMMENT ON TABLE appointment_wait_times IS 'Wait time tracking with patient context and satisfaction scores - contains PHI';
COMMENT ON TABLE scheduling_clinical_notes IS 'Clinical notes and requirements for scheduled appointments - contains PHI';
COMMENT ON TABLE patient_communications IS 'Log of all patient communications including content - contains PHI';
COMMENT ON TABLE clinical_sessions IS 'Clinical session data that may contain PHI';
COMMENT ON TABLE voice_intake_sessions IS 'Voice intake transcriptions and extracted medical information - contains PHI';
COMMENT ON TABLE transcription_records IS 'Audio transcription records with medical content analysis - contains PHI';
COMMENT ON TABLE phi_access_audit IS 'Audit log of all access to PHI data for HIPAA compliance tracking';

-- Record schema creation
INSERT INTO phi_access_audit (
    table_name, 
    operation, 
    user_id, 
    accessed_at
) VALUES (
    'schema_creation', 
    'CREATE', 
    'system', 
    CURRENT_TIMESTAMP
);