-- Public Database Schema for Non-PHI Operational Data
-- This schema contains administrative and operational data without PHI
-- All patient-identifiable information is stored in the private database

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm" SCHEMA public;  -- For fuzzy text search
CREATE EXTENSION IF NOT EXISTS "btree_gin" SCHEMA public;  -- For composite indexes

-- ============================================
-- PROVIDER AND FACILITY MANAGEMENT
-- ============================================

-- Provider profiles and credentials
CREATE TABLE IF NOT EXISTS providers (
    provider_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    npi VARCHAR(20) UNIQUE,  -- National Provider Identifier
    provider_type VARCHAR(100) NOT NULL,
    specialties TEXT[],
    credentials TEXT[],
    department_id UUID,
    facility_ids UUID[],
    scheduling_preferences JSONB DEFAULT '{}',
    availability_rules JSONB DEFAULT '{}',
    default_appointment_duration INTEGER DEFAULT 30,
    buffer_time_minutes INTEGER DEFAULT 5,
    max_daily_appointments INTEGER,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

-- Healthcare facilities
CREATE TABLE IF NOT EXISTS facilities (
    facility_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    facility_name VARCHAR(255) NOT NULL,
    facility_type VARCHAR(100),
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(2),
    zip_code VARCHAR(10),
    phone VARCHAR(20),
    fax VARCHAR(20),
    email VARCHAR(255),
    time_zone VARCHAR(50) DEFAULT 'America/New_York',
    operating_hours JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Departments within facilities
CREATE TABLE IF NOT EXISTS departments (
    department_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    facility_id UUID REFERENCES facilities(facility_id),
    department_name VARCHAR(255) NOT NULL,
    department_type VARCHAR(100),
    floor_number VARCHAR(10),
    room_numbers TEXT[],
    phone_extension VARCHAR(10),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- SCHEDULING CONFIGURATION
-- ============================================

-- Appointment types and their requirements
CREATE TABLE IF NOT EXISTS appointment_types (
    type_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type_code VARCHAR(50) UNIQUE NOT NULL,
    type_name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    default_duration_minutes INTEGER NOT NULL,
    min_duration_minutes INTEGER,
    max_duration_minutes INTEGER,
    required_resources TEXT[],
    required_equipment TEXT[],
    preparation_instructions TEXT,
    followup_required BOOLEAN DEFAULT false,
    followup_interval_days INTEGER,
    billing_codes TEXT[],
    is_telehealth_eligible BOOLEAN DEFAULT false,
    requires_prior_auth BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Provider schedules (no PHI - just availability)
CREATE TABLE IF NOT EXISTS provider_schedules (
    schedule_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider_id UUID REFERENCES providers(provider_id),
    facility_id UUID REFERENCES facilities(facility_id),
    department_id UUID REFERENCES departments(department_id),
    schedule_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    time_slot_size_minutes INTEGER DEFAULT 15,
    appointment_types UUID[],  -- Allowed appointment types
    is_available BOOLEAN DEFAULT true,
    max_appointments INTEGER,
    max_new_patients INTEGER,
    max_followups INTEGER,
    break_times JSONB DEFAULT '[]',  -- Array of {start_time, end_time}
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(provider_id, schedule_date, start_time)
);

-- Available appointment slots (generated from schedules)
CREATE TABLE IF NOT EXISTS appointment_slots (
    slot_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider_id UUID REFERENCES providers(provider_id),
    facility_id UUID REFERENCES facilities(facility_id),
    department_id UUID REFERENCES departments(department_id),
    slot_date DATE NOT NULL,
    slot_time TIME NOT NULL,
    duration_minutes INTEGER NOT NULL,
    appointment_type_id UUID REFERENCES appointment_types(type_id),
    is_available BOOLEAN DEFAULT true,
    is_reserved BOOLEAN DEFAULT false,
    reserved_until TIMESTAMPTZ,
    is_overbook BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_available_slots ON appointment_slots (slot_date, is_available, provider_id);
CREATE INDEX idx_slot_datetime ON appointment_slots (slot_date, slot_time);

-- Scheduling rules and constraints
CREATE TABLE IF NOT EXISTS scheduling_rules (
    rule_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_name VARCHAR(255) NOT NULL,
    rule_type VARCHAR(50) NOT NULL,  -- 'provider', 'facility', 'department', 'global'
    applies_to_id UUID,  -- ID of provider/facility/department or NULL for global
    rule_conditions JSONB NOT NULL,
    rule_actions JSONB NOT NULL,
    priority INTEGER DEFAULT 100,
    effective_from DATE,
    effective_to DATE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- RESOURCE MANAGEMENT
-- ============================================

-- Medical equipment and resources
CREATE TABLE IF NOT EXISTS medical_resources (
    resource_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resource_type VARCHAR(100) NOT NULL,
    resource_name VARCHAR(255) NOT NULL,
    facility_id UUID REFERENCES facilities(facility_id),
    department_id UUID REFERENCES departments(department_id),
    quantity_available INTEGER DEFAULT 1,
    maintenance_schedule JSONB DEFAULT '{}',
    next_maintenance_date DATE,
    is_available BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Resource reservations (linked to appointments in private DB via appointment_id)
CREATE TABLE IF NOT EXISTS resource_reservations (
    reservation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resource_id UUID REFERENCES medical_resources(resource_id),
    appointment_id UUID NOT NULL,  -- References private.appointments
    reserved_from TIMESTAMPTZ NOT NULL,
    reserved_to TIMESTAMPTZ NOT NULL,
    status VARCHAR(50) DEFAULT 'reserved',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_resource_time ON resource_reservations (resource_id, reserved_from, reserved_to);

-- ============================================
-- ANALYTICS AND METRICS (Aggregated, No PHI)
-- ============================================

-- Aggregated scheduling metrics by provider
CREATE TABLE IF NOT EXISTS scheduling_analytics (
    analytics_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider_id UUID REFERENCES providers(provider_id),
    facility_id UUID REFERENCES facilities(facility_id),
    metric_date DATE NOT NULL,
    total_appointments INTEGER DEFAULT 0,
    completed_appointments INTEGER DEFAULT 0,
    cancelled_appointments INTEGER DEFAULT 0,
    no_show_appointments INTEGER DEFAULT 0,
    average_wait_time_minutes DECIMAL(10,2),
    average_appointment_duration DECIMAL(10,2),
    utilization_rate DECIMAL(5,2),
    patient_satisfaction_score DECIMAL(3,2),
    on_time_start_percentage DECIMAL(5,2),
    overbooking_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(provider_id, facility_id, metric_date)
);

-- Facility-wide metrics
CREATE TABLE IF NOT EXISTS facility_metrics (
    metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    facility_id UUID REFERENCES facilities(facility_id),
    metric_date DATE NOT NULL,
    metric_type VARCHAR(100) NOT NULL,
    metric_value JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(facility_id, metric_date, metric_type)
);

-- Appointment type statistics
CREATE TABLE IF NOT EXISTS appointment_type_stats (
    stat_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    appointment_type_id UUID REFERENCES appointment_types(type_id),
    facility_id UUID REFERENCES facilities(facility_id),
    stat_month DATE NOT NULL,
    total_scheduled INTEGER DEFAULT 0,
    total_completed INTEGER DEFAULT 0,
    average_duration_minutes DECIMAL(10,2),
    average_lead_time_days DECIMAL(10,2),
    cancellation_rate DECIMAL(5,2),
    no_show_rate DECIMAL(5,2),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(appointment_type_id, facility_id, stat_month)
);

-- ============================================
-- INTEGRATION AND CONFIGURATION
-- ============================================

-- External system integrations
CREATE TABLE IF NOT EXISTS integration_configs (
    config_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    integration_type VARCHAR(100) NOT NULL,  -- 'epic', 'cerner', 'athena', 'fhir'
    facility_id UUID REFERENCES facilities(facility_id),
    config_name VARCHAR(255) NOT NULL,
    endpoint_url VARCHAR(500),
    api_version VARCHAR(20),
    authentication_type VARCHAR(50),
    credentials_encrypted BYTEA,  -- Encrypted credentials
    connection_settings JSONB DEFAULT '{}',
    sync_schedule JSONB DEFAULT '{}',
    last_sync_at TIMESTAMPTZ,
    sync_status VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Integration sync logs
CREATE TABLE IF NOT EXISTS integration_sync_logs (
    log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    config_id UUID REFERENCES integration_configs(config_id),
    sync_type VARCHAR(50),  -- 'full', 'incremental', 'real-time'
    sync_started_at TIMESTAMPTZ NOT NULL,
    sync_completed_at TIMESTAMPTZ,
    records_processed INTEGER DEFAULT 0,
    records_created INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    error_messages TEXT[],
    sync_status VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- System configuration settings
CREATE TABLE IF NOT EXISTS system_configurations (
    config_key VARCHAR(255) PRIMARY KEY,
    config_value JSONB NOT NULL,
    config_type VARCHAR(50),
    description TEXT,
    is_sensitive BOOLEAN DEFAULT false,
    updated_by VARCHAR(255),
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- OPTIMIZATION AND RECOMMENDATIONS
-- ============================================

-- Schedule optimization recommendations
CREATE TABLE IF NOT EXISTS optimization_recommendations (
    recommendation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider_id UUID REFERENCES providers(provider_id),
    facility_id UUID REFERENCES facilities(facility_id),
    recommendation_type VARCHAR(100) NOT NULL,
    recommendation_date DATE NOT NULL,
    current_metrics JSONB NOT NULL,
    recommended_changes JSONB NOT NULL,
    expected_improvement JSONB,
    priority_score INTEGER,
    status VARCHAR(50) DEFAULT 'pending',
    applied_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Capacity planning projections
CREATE TABLE IF NOT EXISTS capacity_projections (
    projection_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    facility_id UUID REFERENCES facilities(facility_id),
    department_id UUID REFERENCES departments(department_id),
    projection_date DATE NOT NULL,
    time_period VARCHAR(50),  -- 'daily', 'weekly', 'monthly'
    projected_demand INTEGER,
    available_capacity INTEGER,
    utilization_percentage DECIMAL(5,2),
    bottleneck_resources TEXT[],
    recommendations JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(facility_id, department_id, projection_date, time_period)
);

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================

CREATE INDEX idx_providers_active ON providers(is_active) WHERE is_active = true;
CREATE INDEX idx_providers_facility ON providers USING GIN(facility_ids);
CREATE INDEX idx_providers_specialties ON providers USING GIN(specialties);

CREATE INDEX idx_schedules_date ON provider_schedules(schedule_date);
CREATE INDEX idx_schedules_provider_date ON provider_schedules(provider_id, schedule_date);
CREATE INDEX idx_schedules_available ON provider_schedules(schedule_date, is_available) 
    WHERE is_available = true;

CREATE INDEX idx_slots_provider_date ON appointment_slots(provider_id, slot_date);
CREATE INDEX idx_slots_availability ON appointment_slots(slot_date, is_available, is_reserved) 
    WHERE is_available = true AND is_reserved = false;

CREATE INDEX idx_analytics_provider_date ON scheduling_analytics(provider_id, metric_date);
CREATE INDEX idx_analytics_facility_date ON scheduling_analytics(facility_id, metric_date);

CREATE INDEX idx_integration_logs_config ON integration_sync_logs(config_id, sync_started_at DESC);
CREATE INDEX idx_optimization_status ON optimization_recommendations(status, created_at DESC);

-- ============================================
-- TRIGGERS FOR AUTOMATIC UPDATES
-- ============================================

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply update trigger to all tables with updated_at
CREATE TRIGGER update_providers_updated_at BEFORE UPDATE ON providers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_facilities_updated_at BEFORE UPDATE ON facilities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_departments_updated_at BEFORE UPDATE ON departments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_appointment_types_updated_at BEFORE UPDATE ON appointment_types
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_provider_schedules_updated_at BEFORE UPDATE ON provider_schedules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_appointment_slots_updated_at BEFORE UPDATE ON appointment_slots
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_scheduling_rules_updated_at BEFORE UPDATE ON scheduling_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_medical_resources_updated_at BEFORE UPDATE ON medical_resources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_resource_reservations_updated_at BEFORE UPDATE ON resource_reservations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_scheduling_analytics_updated_at BEFORE UPDATE ON scheduling_analytics
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_integration_configs_updated_at BEFORE UPDATE ON integration_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_optimization_recommendations_updated_at BEFORE UPDATE ON optimization_recommendations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- VIEWS FOR COMMON QUERIES
-- ============================================

-- Available slots view with provider and facility info
CREATE OR REPLACE VIEW v_available_slots AS
SELECT 
    s.slot_id,
    s.slot_date,
    s.slot_time,
    s.duration_minutes,
    p.provider_id,
    p.provider_type,
    p.specialties,
    f.facility_id,
    f.facility_name,
    d.department_id,
    d.department_name,
    at.type_name as appointment_type,
    at.category as appointment_category
FROM appointment_slots s
JOIN providers p ON s.provider_id = p.provider_id
JOIN facilities f ON s.facility_id = f.facility_id
LEFT JOIN departments d ON s.department_id = d.department_id
LEFT JOIN appointment_types at ON s.appointment_type_id = at.type_id
WHERE s.is_available = true 
    AND s.is_reserved = false
    AND s.slot_date >= CURRENT_DATE
    AND p.is_active = true
    AND f.is_active = true;

-- Provider utilization view
CREATE OR REPLACE VIEW v_provider_utilization AS
SELECT 
    p.provider_id,
    p.provider_type,
    p.specialties,
    f.facility_name,
    sa.metric_date,
    sa.total_appointments,
    sa.completed_appointments,
    sa.utilization_rate,
    sa.average_wait_time_minutes,
    sa.on_time_start_percentage,
    sa.patient_satisfaction_score
FROM providers p
JOIN scheduling_analytics sa ON p.provider_id = sa.provider_id
JOIN facilities f ON sa.facility_id = f.facility_id
WHERE sa.metric_date >= CURRENT_DATE - INTERVAL '30 days';

-- Resource availability view
CREATE OR REPLACE VIEW v_resource_availability AS
SELECT 
    mr.resource_id,
    mr.resource_type,
    mr.resource_name,
    f.facility_name,
    d.department_name,
    mr.quantity_available,
    mr.is_available,
    COUNT(rr.reservation_id) FILTER (
        WHERE rr.reserved_from <= CURRENT_TIMESTAMP 
        AND rr.reserved_to >= CURRENT_TIMESTAMP
    ) as currently_reserved
FROM medical_resources mr
JOIN facilities f ON mr.facility_id = f.facility_id
LEFT JOIN departments d ON mr.department_id = d.department_id
LEFT JOIN resource_reservations rr ON mr.resource_id = rr.resource_id
GROUP BY mr.resource_id, mr.resource_type, mr.resource_name, 
         f.facility_name, d.department_name, mr.quantity_available, mr.is_available;

-- ============================================
-- FUNCTIONS FOR SCHEDULING OPERATIONS
-- ============================================

-- Function to generate appointment slots from provider schedules
CREATE OR REPLACE FUNCTION generate_appointment_slots(
    p_provider_id UUID,
    p_date DATE,
    p_slot_duration INTEGER DEFAULT 15
)
RETURNS TABLE (
    slot_time TIME,
    duration_minutes INTEGER,
    is_available BOOLEAN
) AS $$
DECLARE
    v_schedule RECORD;
    v_current_time TIME;
BEGIN
    -- Get provider schedule for the date
    SELECT * INTO v_schedule
    FROM provider_schedules
    WHERE provider_id = p_provider_id 
        AND schedule_date = p_date
        AND is_available = true
    LIMIT 1;
    
    IF NOT FOUND THEN
        RETURN;
    END IF;
    
    -- Generate time slots
    v_current_time := v_schedule.start_time;
    
    WHILE v_current_time + (p_slot_duration * INTERVAL '1 minute') <= v_schedule.end_time LOOP
        -- Check if slot overlaps with break time
        IF NOT EXISTS (
            SELECT 1 
            FROM jsonb_array_elements(v_schedule.break_times) AS break
            WHERE (break->>'start_time')::TIME <= v_current_time
                AND (break->>'end_time')::TIME > v_current_time
        ) THEN
            RETURN QUERY SELECT v_current_time, p_slot_duration, true;
        END IF;
        
        v_current_time := v_current_time + (p_slot_duration * INTERVAL '1 minute');
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Function to check resource availability
CREATE OR REPLACE FUNCTION check_resource_availability(
    p_resource_id UUID,
    p_start_time TIMESTAMPTZ,
    p_end_time TIMESTAMPTZ
)
RETURNS BOOLEAN AS $$
DECLARE
    v_available INTEGER;
    v_reserved INTEGER;
BEGIN
    -- Get resource quantity
    SELECT quantity_available INTO v_available
    FROM medical_resources
    WHERE resource_id = p_resource_id AND is_available = true;
    
    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;
    
    -- Count overlapping reservations
    SELECT COUNT(*) INTO v_reserved
    FROM resource_reservations
    WHERE resource_id = p_resource_id
        AND status = 'reserved'
        AND reserved_from < p_end_time
        AND reserved_to > p_start_time;
    
    RETURN v_reserved < v_available;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- INITIAL DATA POPULATION
-- ============================================

-- Insert default appointment types
INSERT INTO appointment_types (type_code, type_name, category, default_duration_minutes, is_telehealth_eligible)
VALUES 
    ('ROUTINE', 'Routine Checkup', 'Primary Care', 30, true),
    ('PHYSICAL', 'Annual Physical', 'Primary Care', 60, false),
    ('FOLLOWUP', 'Follow-up Visit', 'General', 20, true),
    ('CONSULTATION', 'Specialist Consultation', 'Specialty', 45, true),
    ('PROCEDURE', 'Medical Procedure', 'Procedure', 90, false),
    ('LAB', 'Lab Work', 'Diagnostic', 15, false),
    ('IMAGING', 'Imaging Study', 'Diagnostic', 30, false),
    ('VACCINATION', 'Vaccination', 'Preventive', 15, false),
    ('TELEHEALTH', 'Telehealth Visit', 'Virtual', 30, true),
    ('URGENT', 'Urgent Care', 'Urgent', 45, false)
ON CONFLICT (type_code) DO NOTHING;

-- Insert default system configurations
INSERT INTO system_configurations (config_key, config_value, config_type, description)
VALUES 
    ('scheduling.default_slot_duration', '15', 'integer', 'Default appointment slot duration in minutes'),
    ('scheduling.max_advance_booking_days', '180', 'integer', 'Maximum days in advance for booking'),
    ('scheduling.allow_double_booking', 'false', 'boolean', 'Allow double booking of appointments'),
    ('scheduling.auto_confirm_appointments', 'true', 'boolean', 'Automatically confirm appointments'),
    ('scheduling.reminder_days_before', '[7, 3, 1]', 'array', 'Days before appointment to send reminders'),
    ('optimization.min_utilization_target', '0.75', 'decimal', 'Minimum target utilization rate'),
    ('optimization.max_wait_time_minutes', '30', 'integer', 'Maximum acceptable wait time'),
    ('integration.sync_interval_minutes', '15', 'integer', 'Default sync interval for integrations')
ON CONFLICT (config_key) DO NOTHING;

-- ============================================
-- PERMISSIONS (to be customized per deployment)
-- ============================================

-- Create roles for access control
CREATE ROLE scheduling_admin;
CREATE ROLE scheduling_user;
CREATE ROLE scheduling_viewer;
CREATE ROLE integration_service;

-- Grant permissions to roles
GRANT ALL ON ALL TABLES IN SCHEMA public TO scheduling_admin;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO scheduling_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO scheduling_viewer;
GRANT SELECT, INSERT, UPDATE ON integration_configs, integration_sync_logs TO integration_service;

-- Grant sequence permissions
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO scheduling_user;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO integration_service;

COMMENT ON SCHEMA public IS 'Public schema for non-PHI operational and administrative data';