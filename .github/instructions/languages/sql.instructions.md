# SQL Healthcare Instructions

## Purpose

SQL development patterns for healthcare AI systems, emphasizing PHI protection, HIPAA compliance, and secure database operations with synthetic vs. production data handling.

## Healthcare Database Architecture

### PHI-Safe Database Design

```sql
-- ✅ CORRECT: Separate PHI and non-PHI tables with encryption
CREATE TABLE patients_phi (
    patient_id UUID PRIMARY KEY,
    encrypted_name BYTEA NOT NULL,  -- AES-256 encrypted
    encrypted_ssn BYTEA NOT NULL,   -- AES-256 encrypted  
    encrypted_dob BYTEA NOT NULL,   -- AES-256 encrypted
    encryption_key_id UUID NOT NULL REFERENCES encryption_keys(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE patients_non_phi (
    patient_id UUID PRIMARY KEY REFERENCES patients_phi(patient_id),
    insurance_type VARCHAR(50),
    preferred_language VARCHAR(10),
    communication_preferences JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ✅ CORRECT: Audit trail for all PHI access
CREATE TABLE phi_access_log (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL,
    user_id UUID NOT NULL,
    access_type VARCHAR(20) NOT NULL, -- 'READ', 'WRITE', 'DELETE'
    table_name VARCHAR(50) NOT NULL,
    field_names TEXT[], -- Array of accessed fields
    purpose VARCHAR(100), -- 'TREATMENT', 'PAYMENT', 'OPERATIONS'
    ip_address INET,
    user_agent TEXT,
    session_id UUID,
    access_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Synthetic Data Patterns

```sql
-- ✅ CORRECT: Synthetic data markers
CREATE TABLE synthetic_patients (
    patient_id UUID PRIMARY KEY,
    synthetic_marker BOOLEAN DEFAULT TRUE,
    name VARCHAR(100) DEFAULT 'PAT' || LPAD(EXTRACT(EPOCH FROM NOW())::TEXT, 6, '0'),
    ssn VARCHAR(11) DEFAULT '555-55-' || LPAD((RANDOM() * 9999)::INTEGER::TEXT, 4, '0'),
    phone VARCHAR(12) DEFAULT '555-555-' || LPAD((RANDOM() * 9999)::INTEGER::TEXT, 4, '0'),
    email VARCHAR(100) DEFAULT 'patient' || EXTRACT(EPOCH FROM NOW())::INTEGER || '@synthetic.test',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ✅ CORRECT: Environment-aware data generation
DO $$
BEGIN
    IF current_setting('server_version_num')::int >= 120000 THEN
        -- Production: No synthetic data generation
        IF current_setting('application_name') LIKE '%production%' THEN
            RAISE EXCEPTION 'Synthetic data generation disabled in production environment';
        END IF;
    END IF;
END $$;
```

## PHI-Safe Query Patterns

### Secure Data Retrieval

```sql
-- ✅ CORRECT: Decrypt PHI only when necessary with logging
CREATE OR REPLACE FUNCTION get_patient_phi_secure(
    p_patient_id UUID,
    p_user_id UUID, 
    p_purpose VARCHAR(100),
    p_fields TEXT[] DEFAULT ARRAY['name', 'dob']
) RETURNS TABLE(
    patient_id UUID,
    decrypted_data JSONB
) AS $$
DECLARE
    encryption_key BYTEA;
    audit_log_id UUID;
BEGIN
    -- Log access attempt
    INSERT INTO phi_access_log (patient_id, user_id, access_type, table_name, field_names, purpose)
    VALUES (p_patient_id, p_user_id, 'READ', 'patients_phi', p_fields, p_purpose)
    RETURNING log_id INTO audit_log_id;
    
    -- Get encryption key (in production, this would use key management service)
    SELECT key_data INTO encryption_key 
    FROM encryption_keys e
    JOIN patients_phi p ON p.encryption_key_id = e.id
    WHERE p.patient_id = p_patient_id;
    
    -- Return decrypted data
    RETURN QUERY
    SELECT 
        p.patient_id,
        jsonb_build_object(
            'name', CASE WHEN 'name' = ANY(p_fields) THEN pgp_sym_decrypt(p.encrypted_name, encryption_key) END,
            'dob', CASE WHEN 'dob' = ANY(p_fields) THEN pgp_sym_decrypt(p.encrypted_dob, encryption_key) END,
            'audit_log_id', audit_log_id
        ) as decrypted_data
    FROM patients_phi p
    WHERE p.patient_id = p_patient_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ❌ WRONG: Direct PHI access without logging
SELECT encrypted_name, encrypted_ssn FROM patients_phi WHERE patient_id = '...';
```

### Healthcare Data Aggregation

```sql
-- ✅ CORRECT: Aggregate analytics without PHI exposure
CREATE VIEW patient_demographics_summary AS
SELECT 
    insurance_type,
    preferred_language,
    DATE_PART('year', AGE(encrypted_dob)) as age_group_10year, -- Rounded to 10-year groups
    COUNT(*) as patient_count,
    -- No direct PHI fields
    'AGGREGATED_DATA' as data_type
FROM patients_phi p
JOIN patients_non_phi np ON p.patient_id = np.patient_id
GROUP BY insurance_type, preferred_language, DATE_PART('year', AGE(encrypted_dob))
HAVING COUNT(*) >= 5; -- k-anonymity minimum

-- ✅ CORRECT: Clinical outcome tracking without PHI
CREATE VIEW treatment_outcomes AS
SELECT 
    t.treatment_type,
    t.provider_specialty,
    AVG(t.outcome_score) as avg_outcome,
    COUNT(*) as treatment_count,
    STDDEV(t.outcome_score) as outcome_std_dev
FROM treatments t
JOIN encounters e ON t.encounter_id = e.encounter_id
-- No patient identifying information
GROUP BY t.treatment_type, t.provider_specialty
HAVING COUNT(*) >= 10; -- Statistical significance threshold
```

## Database Migration Patterns

### Healthcare-Safe Migrations

```sql
-- ✅ CORRECT: PHI-aware migration with backup
BEGIN;

-- Create backup of PHI data before migration
CREATE TABLE patients_phi_backup_20250804 AS
SELECT * FROM patients_phi;

-- Add new encrypted field with proper constraints
ALTER TABLE patients_phi 
ADD COLUMN encrypted_emergency_contact BYTEA;

-- Migrate existing data (in chunks to avoid locks)
DO $$
DECLARE
    batch_size INTEGER := 1000;
    offset_val INTEGER := 0;
    rec RECORD;
BEGIN
    LOOP
        UPDATE patients_phi 
        SET encrypted_emergency_contact = pgp_sym_encrypt('MIGRATION_PLACEHOLDER', 'temp_key')
        WHERE patient_id IN (
            SELECT patient_id FROM patients_phi 
            ORDER BY patient_id 
            LIMIT batch_size OFFSET offset_val
        );
        
        IF NOT FOUND THEN EXIT; END IF;
        offset_val := offset_val + batch_size;
        
        -- Log migration progress
        INSERT INTO migration_log (migration_name, records_processed, timestamp)
        VALUES ('add_emergency_contact', offset_val, NOW());
        
        -- Commit in batches to avoid long locks
        COMMIT;
        BEGIN;
    END LOOP;
END $$;

COMMIT;
```

### Synthetic Data Integration

```sql
-- ✅ CORRECT: Environment-aware data handling
CREATE OR REPLACE FUNCTION ensure_synthetic_environment() RETURNS VOID AS $$
BEGIN
    -- Verify we're not in production
    IF current_setting('application_name') LIKE '%prod%' 
       OR current_setting('server_name') LIKE '%production%' THEN
        RAISE EXCEPTION 'Synthetic data operations not allowed in production environment';
    END IF;
    
    -- Verify synthetic data markers exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'patients' AND column_name = 'synthetic_marker') THEN
        RAISE EXCEPTION 'Synthetic data marker column missing - unsafe for development';
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ✅ CORRECT: Synthetic data generation for testing
CREATE OR REPLACE FUNCTION generate_synthetic_healthcare_data(record_count INTEGER DEFAULT 100) 
RETURNS INTEGER AS $$
DECLARE
    inserted_count INTEGER := 0;
BEGIN
    -- Safety check
    PERFORM ensure_synthetic_environment();
    
    -- Generate synthetic patients
    INSERT INTO patients (
        patient_id,
        synthetic_marker,
        name,
        ssn,
        dob,
        phone,
        email
    )
    SELECT 
        gen_random_uuid(),
        TRUE, -- Always mark as synthetic
        'PAT' || LPAD(generate_series::TEXT, 3, '0'),
        '555-55-' || LPAD((RANDOM() * 9999)::INTEGER::TEXT, 4, '0'),
        CURRENT_DATE - (RANDOM() * 365 * 80)::INTEGER, -- Random age 0-80
        '555-555-' || LPAD((RANDOM() * 9999)::INTEGER::TEXT, 4, '0'),
        'pat' || generate_series || '@synthetic.test'
    FROM generate_series(1, record_count);
    
    GET DIAGNOSTICS inserted_count = ROW_COUNT;
    
    -- Log synthetic data generation
    INSERT INTO audit_log (action, table_name, record_count, timestamp, notes)
    VALUES ('GENERATE_SYNTHETIC_DATA', 'patients', inserted_count, NOW(), 
            'Generated for development/testing purposes');
    
    RETURN inserted_count;
END;
$$ LANGUAGE plpgsql;
```

## Performance Optimization for Healthcare

### Indexed PHI Access

```sql
-- ✅ CORRECT: Indexes for encrypted data (with care)
CREATE INDEX CONCURRENTLY idx_patients_phi_created_at 
ON patients_phi (created_at);

CREATE INDEX CONCURRENTLY idx_phi_access_log_patient_timestamp 
ON phi_access_log (patient_id, access_timestamp);

-- Hash index for exact matching of encrypted fields (PostgreSQL 10+)
CREATE INDEX CONCURRENTLY idx_patients_phi_encrypted_ssn_hash 
ON patients_phi USING hash (encrypted_ssn);

-- ✅ CORRECT: Partial indexes for active records
CREATE INDEX CONCURRENTLY idx_active_patients 
ON patients_phi (patient_id) 
WHERE deleted_at IS NULL;
```

### Query Optimization

```sql
-- ✅ CORRECT: Efficient PHI access with minimal decryption
EXPLAIN (ANALYZE, BUFFERS) 
SELECT p.patient_id, np.insurance_type
FROM patients_phi p
JOIN patients_non_phi np ON p.patient_id = np.patient_id
WHERE p.created_at >= CURRENT_DATE - INTERVAL '30 days'
  AND np.insurance_type = 'medicare'
  AND p.deleted_at IS NULL;

-- ✅ CORRECT: Use CTEs for complex healthcare queries
WITH recent_encounters AS (
    SELECT patient_id, encounter_id, encounter_date
    FROM encounters 
    WHERE encounter_date >= CURRENT_DATE - INTERVAL '90 days'
),
high_risk_patients AS (
    SELECT patient_id 
    FROM patient_risk_scores 
    WHERE risk_level >= 8
)
SELECT COUNT(*) as high_risk_recent_encounters
FROM recent_encounters re
JOIN high_risk_patients hrp ON re.patient_id = hrp.patient_id;
```

## Security and Compliance

### Row-Level Security (RLS)

```sql
-- ✅ CORRECT: RLS for PHI protection
ALTER TABLE patients_phi ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access patients they're authorized for
CREATE POLICY patient_access_policy ON patients_phi
FOR ALL TO healthcare_users
USING (
    patient_id IN (
        SELECT patient_id 
        FROM patient_provider_assignments ppa
        WHERE ppa.provider_id = current_setting('app.current_user_id')::UUID
          AND ppa.access_level IN ('FULL', 'LIMITED')
          AND ppa.effective_date <= CURRENT_DATE
          AND (ppa.expiration_date IS NULL OR ppa.expiration_date > CURRENT_DATE)
    )
);

-- Emergency access override (with logging)
CREATE POLICY emergency_access_policy ON patients_phi
FOR ALL TO emergency_users
USING (
    -- Log emergency access
    audit_emergency_access(patient_id, current_setting('app.current_user_id')::UUID)
);
```

### Data Retention and Purging

```sql
-- ✅ CORRECT: HIPAA-compliant data retention
CREATE OR REPLACE FUNCTION purge_expired_phi_data() RETURNS INTEGER AS $$
DECLARE
    retention_years INTEGER := 7; -- HIPAA minimum
    purged_count INTEGER := 0;
BEGIN
    -- Soft delete first (for recovery period)
    UPDATE patients_phi 
    SET deleted_at = NOW(),
        deleted_by = 'AUTOMATED_RETENTION_POLICY'
    WHERE created_at < CURRENT_DATE - (retention_years || ' years')::INTERVAL
      AND deleted_at IS NULL;
    
    GET DIAGNOSTICS purged_count = ROW_COUNT;
    
    -- Log retention action
    INSERT INTO audit_log (action, table_name, record_count, timestamp, notes)
    VALUES ('RETENTION_SOFT_DELETE', 'patients_phi', purged_count, NOW(),
            'HIPAA retention policy: ' || retention_years || ' years');
    
    RETURN purged_count;
END;
$$ LANGUAGE plpgsql;

-- Schedule automatic retention (using pg_cron extension)
SELECT cron.schedule('hipaa-retention', '0 2 * * 0', 'SELECT purge_expired_phi_data();');
```

## Development Best Practices

### Testing with Synthetic Data

```sql
-- ✅ CORRECT: Test data isolation
CREATE SCHEMA test_data;

-- Copy structure but ensure synthetic markers
CREATE TABLE test_data.patients (LIKE patients INCLUDING ALL);
ALTER TABLE test_data.patients ALTER COLUMN synthetic_marker SET DEFAULT TRUE;

-- Test data generation function
CREATE OR REPLACE FUNCTION test_data.setup_test_scenario(scenario_name VARCHAR) 
RETURNS VOID AS $$
BEGIN
    -- Clear previous test data
    DELETE FROM test_data.patients WHERE scenario_tag = scenario_name;
    
    CASE scenario_name
        WHEN 'diabetes_patients' THEN
            INSERT INTO test_data.patients (name, synthetic_marker, scenario_tag)
            VALUES ('PAT001_DIABETES', TRUE, scenario_name),
                   ('PAT002_DIABETES', TRUE, scenario_name);
                   
        WHEN 'elderly_patients' THEN
            INSERT INTO test_data.patients (name, dob, synthetic_marker, scenario_tag)
            SELECT 'PAT' || LPAD(generate_series::TEXT, 3, '0'),
                   CURRENT_DATE - (RANDOM() * 365 * 20 + 365 * 65)::INTEGER,
                   TRUE,
                   scenario_name
            FROM generate_series(1, 10);
    END CASE;
END;
$$ LANGUAGE plpgsql;
```

### Healthcare SQL Code Review Checklist

```sql
-- ✅ CHECKLIST: Healthcare SQL Review Points

-- 1. PHI Protection
--    □ All PHI fields are encrypted
--    □ Access is logged in audit trail
--    □ Row-level security enabled where appropriate

-- 2. Synthetic Data Safety
--    □ Synthetic data markers present and checked
--    □ Environment validation prevents production synthetic data

-- 3. Performance
--    □ Appropriate indexes for healthcare query patterns
--    □ Query plans reviewed for efficiency
--    □ Batch processing for large PHI operations

-- 4. Compliance
--    □ HIPAA audit requirements met
--    □ Data retention policies implemented
--    □ Emergency access procedures documented

-- 5. Security
--    □ SQL injection prevention (parameterized queries)
--    □ Principle of least privilege applied
--    □ Encryption keys managed securely
```

## Common Anti-Patterns to Avoid

### ❌ WRONG: PHI Anti-Patterns

```sql
-- ❌ WRONG: Storing PHI in plain text
CREATE TABLE patients (
    name VARCHAR(100), -- Unencrypted PHI
    ssn VARCHAR(11)    -- Unencrypted PHI
);

-- ❌ WRONG: No audit logging
SELECT name, ssn FROM patients WHERE patient_id = '...'; -- No access logging

-- ❌ WRONG: Hardcoded encryption keys
UPDATE patients SET encrypted_ssn = pgp_sym_encrypt(ssn, 'hardcoded_key'); -- Security risk

-- ❌ WRONG: Missing synthetic data markers
INSERT INTO patients (name, ssn) VALUES ('John Doe', '123-45-6789'); -- Could be real PHI

-- ❌ WRONG: No environment checks
DROP TABLE patients; -- No production safety checks
```

### ✅ CORRECT: Healthcare SQL Patterns

```sql
-- ✅ CORRECT: Comprehensive PHI handling
SELECT 
    get_patient_phi_secure(
        p_patient_id := %s,
        p_user_id := %s,
        p_purpose := 'TREATMENT',
        p_fields := ARRAY['name', 'dob']
    ) as patient_data;

-- ✅ CORRECT: Environment-aware operations
SELECT ensure_synthetic_environment() BEFORE INSERT INTO patients (...);

-- ✅ CORRECT: Parameterized queries with logging
PREPARE get_patient_encounters AS
SELECT e.encounter_id, e.encounter_date, e.chief_complaint
FROM encounters e
WHERE e.patient_id = $1 
  AND e.encounter_date >= $2;

-- Log the query execution
INSERT INTO query_audit_log (query_name, parameters, user_id, timestamp)
VALUES ('get_patient_encounters', ARRAY[$1::TEXT, $2::TEXT], current_user_id(), NOW());
```

## Medical Disclaimer

**MEDICAL DISCLAIMER: This SQL instruction set provides database development patterns for healthcare administrative systems only. It assists healthcare technology professionals with secure data handling, HIPAA compliance, and PHI protection. It does not provide medical advice, diagnosis, or treatment recommendations. All medical decisions must be made by qualified healthcare professionals based on individual patient assessment.**
