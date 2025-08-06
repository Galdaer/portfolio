# Database Development Healthcare Instructions

## Purpose

**DATABASE-FIRST ARCHITECTURE**: All healthcare applications must use databases as primary data source. No synthetic file fallbacks allowed except for GitHub coding agents with database setup capability.

Database development patterns specifically for healthcare AI systems, emphasizing secure PHI handling, audit trails, synthetic data management, and HIPAA-compliant database architecture.

## CRITICAL: Database-First Enforcement

### Database Connection Requirements

**❌ PROHIBITED PATTERNS:**
```python
# ❌ WRONG: File fallbacks compromise security
def get_patient_data(patient_id):
    try:
        return database.query(patient_id)
    except DatabaseError:
        return load_synthetic_file(patient_id)  # SECURITY RISK
```

**✅ REQUIRED PATTERNS:**
```python
# ✅ CORRECT: Database-first with proper error handling
def get_patient_data(patient_id):
    try:
        return database.query(patient_id)
    except DatabaseError as e:
        logger.critical(f"Database unavailable: {e}")
        raise HealthcareDatabaseError(
            "Patient data requires secure database connection. "
            "Please ensure PostgreSQL is running and accessible."
        )
```

### Agent Database Requirements

**ALL AGENTS MUST:**
- Verify database connectivity at startup
- Fail gracefully with clear error messages when database unavailable
- Provide database setup guidance in error messages
- Log database connection attempts for audit compliance

**GITHUB CODING AGENT EXCEPTION:**
- May generate and populate test database if needed
- Must use `make deps` for database initialization
- Should provide automated database setup scripts

## Healthcare Database Architecture Principles

### 1. PHI Segregation Architecture

```python
# ✅ CORRECT: Separate PHI and non-PHI data models
from sqlalchemy import Column, String, DateTime, Boolean, LargeBinary, UUID
from sqlalchemy.ext.declarative import declarative_base
from cryptography.fernet import Fernet

Base = declarative_base()

class PatientPHI(Base):
    """PHI table with encryption - restricted access"""
    __tablename__ = 'patients_phi'
    
    patient_id = Column(UUID(as_uuid=True), primary_key=True)
    encrypted_name = Column(LargeBinary, nullable=False)  # AES encrypted
    encrypted_ssn = Column(LargeBinary, nullable=False)   # AES encrypted
    encrypted_dob = Column(LargeBinary, nullable=False)   # AES encrypted
    encryption_key_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Audit fields
    created_by = Column(UUID(as_uuid=True), nullable=False)
    last_accessed = Column(DateTime(timezone=True))
    access_count = Column(Integer, default=0)

class PatientNonPHI(Base):
    """Non-PHI table - general access allowed"""
    __tablename__ = 'patients_non_phi'
    
    patient_id = Column(UUID(as_uuid=True), primary_key=True)
    insurance_type = Column(String(50))
    preferred_language = Column(String(10))
    communication_preferences = Column(JSON)
    synthetic_marker = Column(Boolean, default=False)  # Critical for test data
```

### 2. Healthcare Database Connection Management

```python
# ✅ CORRECT: Healthcare-specific database factory
import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from core.infrastructure.healthcare_logger import get_healthcare_logger

logger = get_healthcare_logger('database')

class HealthcareDatabaseManager:
    """Healthcare-compliant database connection management"""
    
    def __init__(self):
        self.phi_engine = None
        self.non_phi_engine = None
        self.synthetic_engine = None
        
    def get_phi_engine(self):
        """Get PHI database engine with enhanced security"""
        if not self.phi_engine:
            # Enhanced connection string with SSL and encryption
            phi_url = self._build_secure_connection_url(
                host=os.getenv('PHI_DB_HOST'),
                database=os.getenv('PHI_DB_NAME'),
                ssl_mode='require',
                connection_timeout=30
            )
            
            self.phi_engine = create_engine(
                phi_url,
                echo=False,  # Never log PHI queries
                pool_pre_ping=True,
                pool_recycle=3600,  # Rotate connections hourly
                connect_args={
                    "application_name": "intelluxe_phi_access",
                    "options": "-c default_transaction_isolation=serializable"
                }
            )
            
            # Add PHI access logging
            self._setup_phi_access_logging(self.phi_engine)
            
        return self.phi_engine
    
    def get_synthetic_engine(self):
        """Get synthetic data engine for development/testing"""
        if not self.synthetic_engine:
            # Ensure we're not in production
            if os.getenv('ENVIRONMENT') == 'production':
                raise ValueError("Synthetic database access not allowed in production")
                
            synthetic_url = self._build_connection_url(
                host=os.getenv('SYNTHETIC_DB_HOST', 'localhost'),
                database=os.getenv('SYNTHETIC_DB_NAME', 'intelluxe_synthetic'),
            )
            
            self.synthetic_engine = create_engine(
                synthetic_url,
                echo=True,  # OK to log synthetic data queries
                connect_args={
                    "application_name": "intelluxe_synthetic_dev"
                }
            )
            
        return self.synthetic_engine
    
    def _setup_phi_access_logging(self, engine):
        """Setup comprehensive PHI access logging"""
        
        @event.listens_for(engine, "before_cursor_execute")
        def log_phi_access(conn, cursor, statement, parameters, context, executemany):
            # Log all PHI database access
            logger.info(
                "PHI database access initiated",
                extra={
                    'operation_type': 'phi_database_access',
                    'user_id': context.get('current_user_id'),
                    'table_accessed': self._extract_table_name(statement),
                    'access_type': self._determine_access_type(statement)
                }
            )
```

## PHI-Safe Database Operations

### 1. Secure Data Access Patterns

```python
# ✅ CORRECT: PHI access with logging and decryption
from core.infrastructure.healthcare_logger import healthcare_log_method
from core.infrastructure.phi_monitor import phi_monitor

class SecurePHIRepository:
    """Repository for secure PHI database operations"""
    
    def __init__(self, db_manager: HealthcareDatabaseManager):
        self.db_manager = db_manager
        self.encryption_service = EncryptionService()
        
    @healthcare_log_method(logger)
    @phi_monitor(risk_level="high", operation_type="phi_database_read")
    async def get_patient_phi(
        self, 
        patient_id: UUID, 
        user_id: UUID, 
        purpose: str,
        fields_requested: List[str]
    ) -> Dict[str, Any]:
        """Securely retrieve patient PHI with full audit trail"""
        
        # Validate purpose is legitimate
        valid_purposes = ['TREATMENT', 'PAYMENT', 'OPERATIONS', 'RESEARCH_IRB_APPROVED']
        if purpose not in valid_purposes:
            raise ValueError(f"Invalid purpose: {purpose}")
        
        # Log access attempt
        audit_entry = PHIAccessLog(
            patient_id=patient_id,
            user_id=user_id,
            access_type='READ',
            purpose=purpose,
            fields_requested=fields_requested,
            timestamp=datetime.utcnow()
        )
        
        try:
            with self.db_manager.get_phi_engine().begin() as conn:
                # Record access attempt
                conn.execute(phi_access_log.insert().values(
                    patient_id=patient_id,
                    user_id=user_id,
                    access_type='READ',
                    fields_requested=fields_requested,
                    purpose=purpose,
                    ip_address=self._get_client_ip(),
                    timestamp=datetime.utcnow()
                ))
                
                # Retrieve encrypted data
                result = conn.execute(
                    select(PatientPHI).where(PatientPHI.patient_id == patient_id)
                ).first()
                
                if not result:
                    raise PatientNotFoundError(f"Patient {patient_id} not found")
                
                # Decrypt only requested fields
                decrypted_data = {}
                for field in fields_requested:
                    if hasattr(result, f'encrypted_{field}'):
                        encrypted_value = getattr(result, f'encrypted_{field}')
                        decrypted_data[field] = self.encryption_service.decrypt(
                            encrypted_value, 
                            result.encryption_key_id
                        )
                
                # Update access tracking
                conn.execute(
                    update(PatientPHI)
                    .where(PatientPHI.patient_id == patient_id)
                    .values(
                        last_accessed=datetime.utcnow(),
                        access_count=PatientPHI.access_count + 1
                    )
                )
                
                return {
                    'patient_id': patient_id,
                    'data': decrypted_data,
                    'access_logged': True,
                    'audit_id': audit_entry.id
                }
                
        except Exception as e:
            # Log failed access attempt
            logger.error(
                f"PHI access failed for patient {patient_id}",
                extra={
                    'error': str(e),
                    'user_id': str(user_id),
                    'purpose': purpose,
                    'operation_type': 'phi_access_error'
                }
            )
            raise HealthcareDatabaseError(f"PHI access failed: {str(e)}")
```

### 2. Synthetic Data Management

```python
# ✅ CORRECT: Synthetic data operations with safety checks
class SyntheticDataRepository:
    """Repository for synthetic data operations in development/testing"""
    
    def __init__(self, db_manager: HealthcareDatabaseManager):
        self.db_manager = db_manager
        
    def ensure_synthetic_environment(self) -> None:
        """Ensure we're operating in a synthetic data environment"""
        if os.getenv('ENVIRONMENT') == 'production':
            raise EnvironmentError("Synthetic data operations not allowed in production")
            
        if not os.getenv('SYNTHETIC_DATA_ENABLED', '').lower() == 'true':
            raise EnvironmentError("Synthetic data operations not enabled")
    
    @healthcare_log_method(logger)
    async def generate_synthetic_patients(self, count: int = 100) -> List[UUID]:
        """Generate synthetic patient data for testing"""
        self.ensure_synthetic_environment()
        
        synthetic_patients = []
        
        with self.db_manager.get_synthetic_engine().begin() as conn:
            for i in range(count):
                patient_id = uuid4()
                
                # Generate synthetic PHI data
                synthetic_phi = {
                    'patient_id': patient_id,
                    'name': f'PAT{i:03d}',  # Clear synthetic marker
                    'ssn': f'555-55-{i:04d}',  # 555 prefix = clearly synthetic
                    'dob': date(1990, 1, 1) + timedelta(days=random.randint(0, 365*30)),
                    'phone': f'555-555-{i:04d}',
                    'email': f'pat{i:03d}@synthetic.test',
                    'synthetic_marker': True  # Critical marker
                }
                
                # Encrypt synthetic PHI (still practice security)
                encrypted_phi = {
                    'patient_id': patient_id,
                    'encrypted_name': self._encrypt_synthetic(synthetic_phi['name']),
                    'encrypted_ssn': self._encrypt_synthetic(synthetic_phi['ssn']),
                    'encrypted_dob': self._encrypt_synthetic(synthetic_phi['dob'].isoformat()),
                    'synthetic_marker': True,
                    'created_at': datetime.utcnow()
                }
                
                conn.execute(patients_phi.insert().values(**encrypted_phi))
                synthetic_patients.append(patient_id)
        
        logger.info(
            f"Generated {count} synthetic patients",
            extra={
                'operation_type': 'synthetic_data_generation',
                'record_count': count,
                'environment': os.getenv('ENVIRONMENT')
            }
        )
        
        return synthetic_patients
    
    async def validate_synthetic_data_integrity(self) -> Dict[str, Any]:
        """Validate synthetic data markers are present and correct"""
        self.ensure_synthetic_environment()
        
        with self.db_manager.get_synthetic_engine().begin() as conn:
            # Check for missing synthetic markers
            unmarked_records = conn.execute(
                select(func.count()).select_from(patients_phi)
                .where(patients_phi.c.synthetic_marker.is_(False))
            ).scalar()
            
            # Check for realistic-looking synthetic data
            suspicious_patterns = conn.execute(
                select(func.count()).select_from(patients_phi)
                .where(
                    ~patients_phi.c.encrypted_name.like(b'PAT%') &
                    patients_phi.c.synthetic_marker.is_(True)
                )
            ).scalar()
            
            return {
                'total_synthetic_records': conn.execute(
                    select(func.count()).select_from(patients_phi)
                    .where(patients_phi.c.synthetic_marker.is_(True))
                ).scalar(),
                'unmarked_records': unmarked_records,
                'suspicious_patterns': suspicious_patterns,
                'validation_passed': unmarked_records == 0 and suspicious_patterns == 0
            }
```

## Database Migration Patterns

### 1. Healthcare-Safe Migrations

```python
# ✅ CORRECT: Healthcare database migration with PHI protection
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    """Add emergency contact field with PHI protection"""
    
    # Create backup table for rollback capability
    op.execute("""
        CREATE TABLE patients_phi_backup_migration_001 AS 
        SELECT * FROM patients_phi;
    """)
    
    # Add new encrypted field
    op.add_column(
        'patients_phi',
        sa.Column('encrypted_emergency_contact', sa.LargeBinary(), nullable=True)
    )
    
    # Add audit trail for migration
    op.execute("""
        INSERT INTO migration_audit_log (
            migration_name, 
            table_name, 
            operation_type, 
            timestamp,
            notes
        ) VALUES (
            'add_emergency_contact_001',
            'patients_phi',
            'ADD_COLUMN',
            NOW(),
            'Added encrypted emergency contact field for PHI compliance'
        );
    """)
    
    # Update existing records in batches to avoid locks
    op.execute("""
        DO $$
        DECLARE 
            batch_size INTEGER := 1000;
            processed INTEGER := 0;
        BEGIN
            LOOP
                UPDATE patients_phi 
                SET encrypted_emergency_contact = encrypt('MIGRATION_PLACEHOLDER', 'temp_key')
                WHERE patient_id IN (
                    SELECT patient_id FROM patients_phi 
                    WHERE encrypted_emergency_contact IS NULL
                    ORDER BY patient_id 
                    LIMIT batch_size
                );
                
                GET DIAGNOSTICS processed = ROW_COUNT;
                EXIT WHEN processed = 0;
                
                -- Log progress
                INSERT INTO migration_progress_log (
                    migration_name, 
                    records_processed, 
                    timestamp
                ) VALUES (
                    'add_emergency_contact_001', 
                    processed, 
                    NOW()
                );
                
                -- Prevent long-running transaction locks
                COMMIT;
            END LOOP;
        END $$;
    """)

def downgrade():
    """Safely remove emergency contact field"""
    
    # Verify no critical data will be lost
    op.execute("""
        SELECT CASE 
            WHEN COUNT(*) > 0 THEN 
                RAISE EXCEPTION 'Cannot downgrade: Emergency contact data exists'
            ELSE NULL
        END
        FROM patients_phi 
        WHERE encrypted_emergency_contact IS NOT NULL
          AND encrypted_emergency_contact != encrypt('MIGRATION_PLACEHOLDER', 'temp_key');
    """)
    
    # Safe to remove column
    op.drop_column('patients_phi', 'encrypted_emergency_contact')
    
    # Log downgrade
    op.execute("""
        INSERT INTO migration_audit_log (
            migration_name, 
            table_name, 
            operation_type, 
            timestamp
        ) VALUES (
            'add_emergency_contact_001',
            'patients_phi',
            'DOWNGRADE',
            NOW()
        );
    """)
```

### 2. Data Validation Migrations

```python
# ✅ CORRECT: Healthcare data validation during migration
def upgrade():
    """Add data validation for existing PHI records"""
    
    # Create validation results table
    op.create_table(
        'phi_validation_results',
        sa.Column('validation_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('validation_type', sa.String(50), nullable=False),
        sa.Column('validation_result', sa.String(20), nullable=False),  # PASS/FAIL/WARNING
        sa.Column('validation_message', sa.Text()),
        sa.Column('validated_at', sa.DateTime(timezone=True), server_default=sa.func.now())
    )
    
    # Run PHI validation checks
    op.execute("""
        -- Validate SSN format
        INSERT INTO phi_validation_results (
            validation_id, patient_id, validation_type, validation_result, validation_message
        )
        SELECT 
            gen_random_uuid(),
            patient_id,
            'SSN_FORMAT',
            CASE 
                WHEN decrypt(encrypted_ssn, key) ~ '^[0-9]{3}-?[0-9]{2}-?[0-9]{4}$' THEN 'PASS'
                WHEN decrypt(encrypted_ssn, key) LIKE '555%' THEN 'WARNING'  -- Synthetic data
                ELSE 'FAIL'
            END,
            'SSN format validation during migration'
        FROM patients_phi p
        JOIN encryption_keys e ON p.encryption_key_id = e.id;
        
        -- Validate phone number format
        INSERT INTO phi_validation_results (
            validation_id, patient_id, validation_type, validation_result, validation_message
        )
        SELECT 
            gen_random_uuid(),
            patient_id,
            'PHONE_FORMAT',
            CASE 
                WHEN decrypt(encrypted_phone, key) ~ '^[0-9]{3}-?[0-9]{3}-?[0-9]{4}$' THEN 'PASS'
                WHEN decrypt(encrypted_phone, key) LIKE '555-555%' THEN 'WARNING'  -- Test data
                ELSE 'FAIL'
            END,
            'Phone format validation during migration'
        FROM patients_phi p
        JOIN encryption_keys e ON p.encryption_key_id = e.id
        WHERE encrypted_phone IS NOT NULL;
    """)
    
    # Create alerts for validation failures
    op.execute("""
        INSERT INTO system_alerts (
            alert_type, 
            severity, 
            message, 
            alert_data, 
            created_at
        )
        SELECT 
            'PHI_VALIDATION_FAILURE',
            'HIGH',
            'PHI validation failures detected during migration',
            jsonb_build_object(
                'failed_validations', COUNT(*),
                'validation_types', array_agg(DISTINCT validation_type)
            ),
            NOW()
        FROM phi_validation_results 
        WHERE validation_result = 'FAIL'
        HAVING COUNT(*) > 0;
    """)
```

## Performance Optimization for Healthcare

### 1. Indexed Healthcare Queries

```python
# ✅ CORRECT: Healthcare-optimized database indexes
from sqlalchemy import Index, text

# Patient lookup optimization
patient_lookup_index = Index(
    'idx_patient_phi_lookup',
    PatientPHI.patient_id,
    PatientPHI.created_at,
    postgresql_where=PatientPHI.deleted_at.is_(None)
)

# PHI access audit optimization
phi_audit_index = Index(
    'idx_phi_access_audit',
    PHIAccessLog.patient_id,
    PHIAccessLog.access_timestamp.desc(),
    PHIAccessLog.user_id
)

# Synthetic data filtering
synthetic_data_index = Index(
    'idx_synthetic_marker',
    PatientPHI.synthetic_marker,
    PatientPHI.created_at,
    postgresql_where=PatientPHI.synthetic_marker.is_(True)
)

# Partial index for active patients only
active_patients_index = Index(
    'idx_active_patients_only',
    PatientPHI.patient_id,
    PatientPHI.last_accessed,
    postgresql_where=PatientPHI.deleted_at.is_(None)
)
```

### 2. Query Optimization Patterns

```python
# ✅ CORRECT: Optimized healthcare queries with monitoring
class OptimizedHealthcareQueries:
    
    @healthcare_log_method(logger)
    async def get_recent_high_risk_patients(
        self, 
        days_back: int = 30,
        risk_threshold: int = 8
    ) -> List[Dict[str, Any]]:
        """Optimized query for recent high-risk patients"""
        
        # Use CTE for complex healthcare analytics
        query = text("""
            WITH recent_encounters AS (
                SELECT DISTINCT e.patient_id, e.encounter_date, e.risk_score
                FROM encounters e
                WHERE e.encounter_date >= :cutoff_date
                  AND e.risk_score >= :risk_threshold
                  AND e.deleted_at IS NULL
            ),
            patient_summary AS (
                SELECT 
                    re.patient_id,
                    MAX(re.encounter_date) as last_encounter,
                    AVG(re.risk_score) as avg_risk_score,
                    COUNT(*) as encounter_count
                FROM recent_encounters re
                GROUP BY re.patient_id
            )
            SELECT 
                ps.patient_id,
                ps.last_encounter,
                ps.avg_risk_score,
                ps.encounter_count,
                pnp.insurance_type,
                pnp.preferred_language
            FROM patient_summary ps
            JOIN patients_non_phi pnp ON ps.patient_id = pnp.patient_id
            ORDER BY ps.avg_risk_score DESC, ps.last_encounter DESC
            LIMIT 100;
        """)
        
        with self.db_manager.get_phi_engine().begin() as conn:
            result = conn.execute(query, {
                'cutoff_date': datetime.utcnow() - timedelta(days=days_back),
                'risk_threshold': risk_threshold
            })
            
            return [dict(row) for row in result.fetchall()]
```

## Error Handling and Monitoring

### 1. Healthcare-Specific Error Handling

```python
# ✅ CORRECT: Healthcare database error handling
class HealthcareDatabaseError(Exception):
    """Base exception for healthcare database operations"""
    pass

class PHIAccessViolationError(HealthcareDatabaseError):
    """Exception for unauthorized PHI access attempts"""
    
    def __init__(self, message: str, patient_id: UUID, user_id: UUID):
        super().__init__(message)
        self.patient_id = patient_id
        self.user_id = user_id
        
        # Immediately log security violation
        logger.error(
            "PHI access violation detected",
            extra={
                'error_type': 'PHI_ACCESS_VIOLATION',
                'patient_id': str(patient_id),
                'user_id': str(user_id),
                'message': message,
                'severity': 'CRITICAL'
            }
        )

class SyntheticDataIntegrityError(HealthcareDatabaseError):
    """Exception for synthetic data integrity violations"""
    pass

# Exception handler decorator
def handle_healthcare_db_errors(func):
    """Decorator for healthcare database error handling"""
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
            
        except IntegrityError as e:
            # Database constraint violation
            if 'phi_access_log' in str(e):
                raise PHIAccessViolationError(
                    "PHI access logging constraint violated",
                    kwargs.get('patient_id'),
                    kwargs.get('user_id')
                )
            raise HealthcareDatabaseError(f"Database integrity error: {str(e)}")
            
        except OperationalError as e:
            # Connection or query execution error
            logger.error(
                "Healthcare database operational error",
                extra={
                    'error': str(e),
                    'function': func.__name__,
                    'operation_type': 'database_operational_error'
                }
            )
            raise HealthcareDatabaseError(f"Database operation failed: {str(e)}")
            
        except Exception as e:
            # Unexpected error
            logger.error(
                "Unexpected healthcare database error",
                extra={
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'function': func.__name__,
                    'operation_type': 'database_unexpected_error'
                }
            )
            raise HealthcareDatabaseError(f"Unexpected database error: {str(e)}")
    
    return wrapper
```

### 2. Database Health Monitoring

```python
# ✅ CORRECT: Healthcare database monitoring
class HealthcareDatabaseMonitor:
    """Monitor healthcare database health and compliance"""
    
    def __init__(self, db_manager: HealthcareDatabaseManager):
        self.db_manager = db_manager
        
    async def check_phi_database_health(self) -> Dict[str, Any]:
        """Comprehensive PHI database health check"""
        
        health_status = {
            'overall_status': 'HEALTHY',
            'checks': {},
            'alerts': []
        }
        
        try:
            with self.db_manager.get_phi_engine().begin() as conn:
                # Check connection health
                conn.execute(text("SELECT 1"))
                health_status['checks']['connection'] = 'HEALTHY'
                
                # Check encryption key availability
                key_count = conn.execute(
                    text("SELECT COUNT(*) FROM encryption_keys WHERE active = true")
                ).scalar()
                
                if key_count == 0:
                    health_status['checks']['encryption_keys'] = 'CRITICAL'
                    health_status['alerts'].append('No active encryption keys found')
                    health_status['overall_status'] = 'CRITICAL'
                else:
                    health_status['checks']['encryption_keys'] = 'HEALTHY'
                
                # Check PHI access audit integrity
                audit_gaps = conn.execute(text("""
                    SELECT COUNT(*) FROM patients_phi p
                    LEFT JOIN phi_access_log pal ON p.patient_id = pal.patient_id
                    WHERE p.last_accessed IS NOT NULL 
                      AND pal.patient_id IS NULL
                """)).scalar()
                
                if audit_gaps > 0:
                    health_status['checks']['audit_integrity'] = 'WARNING'
                    health_status['alerts'].append(f'{audit_gaps} PHI records missing audit trail')
                    if health_status['overall_status'] == 'HEALTHY':
                        health_status['overall_status'] = 'WARNING'
                else:
                    health_status['checks']['audit_integrity'] = 'HEALTHY'
                
                # Check for synthetic data in production
                if os.getenv('ENVIRONMENT') == 'production':
                    synthetic_count = conn.execute(
                        text("SELECT COUNT(*) FROM patients_phi WHERE synthetic_marker = true")
                    ).scalar()
                    
                    if synthetic_count > 0:
                        health_status['checks']['synthetic_data_leak'] = 'CRITICAL'
                        health_status['alerts'].append(f'{synthetic_count} synthetic records in production')
                        health_status['overall_status'] = 'CRITICAL'
                    else:
                        health_status['checks']['synthetic_data_leak'] = 'HEALTHY'
                
        except Exception as e:
            health_status['overall_status'] = 'CRITICAL'
            health_status['checks']['database_access'] = 'CRITICAL'
            health_status['alerts'].append(f'Database access failed: {str(e)}')
        
        return health_status
    
    async def generate_compliance_report(self) -> Dict[str, Any]:
        """Generate HIPAA compliance report for database operations"""
        
        report = {
            'report_date': datetime.utcnow().isoformat(),
            'compliance_status': 'COMPLIANT',
            'findings': []
        }
        
        with self.db_manager.get_phi_engine().begin() as conn:
            # Check audit log completeness
            audit_coverage = conn.execute(text("""
                SELECT 
                    COUNT(DISTINCT p.patient_id) as total_patients,
                    COUNT(DISTINCT pal.patient_id) as audited_patients,
                    ROUND(
                        COUNT(DISTINCT pal.patient_id) * 100.0 / 
                        NULLIF(COUNT(DISTINCT p.patient_id), 0), 2
                    ) as audit_coverage_percent
                FROM patients_phi p
                LEFT JOIN phi_access_log pal ON p.patient_id = pal.patient_id
                WHERE p.created_at >= NOW() - INTERVAL '30 days'
            """)).first()
            
            if audit_coverage.audit_coverage_percent < 95:
                report['compliance_status'] = 'NON_COMPLIANT'
                report['findings'].append({
                    'type': 'AUDIT_COVERAGE',
                    'severity': 'HIGH',
                    'description': f'Audit coverage only {audit_coverage.audit_coverage_percent}% (required: 95%)'
                })
            
            # Check encryption compliance
            unencrypted_phi = conn.execute(text("""
                SELECT COUNT(*) FROM patients_phi 
                WHERE encrypted_name IS NULL 
                   OR encrypted_ssn IS NULL 
                   OR encrypted_dob IS NULL
            """)).scalar()
            
            if unencrypted_phi > 0:
                report['compliance_status'] = 'NON_COMPLIANT'
                report['findings'].append({
                    'type': 'ENCRYPTION_COMPLIANCE',
                    'severity': 'CRITICAL',
                    'description': f'{unencrypted_phi} PHI records not properly encrypted'
                })
        
        return report
```

## Testing Patterns

### 1. Database Testing with Synthetic Data

```python
# ✅ CORRECT: Healthcare database testing patterns
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def synthetic_db_session():
    """Create isolated synthetic database session for testing"""
    
    # Ensure we're in test environment
    os.environ['ENVIRONMENT'] = 'test'
    os.environ['SYNTHETIC_DATA_ENABLED'] = 'true'
    
    # Create in-memory SQLite for fast testing
    engine = create_engine('sqlite:///:memory:', echo=True)
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Generate synthetic test data
    synthetic_patients = []
    for i in range(10):
        patient = PatientPHI(
            patient_id=uuid4(),
            encrypted_name=f'PAT{i:03d}'.encode(),  # Simple encoding for testing
            encrypted_ssn=f'555-55-{i:04d}'.encode(),
            encrypted_dob=date(1990, 1, 1).isoformat().encode(),
            synthetic_marker=True
        )
        session.add(patient)
        synthetic_patients.append(patient)
    
    session.commit()
    
    yield session, synthetic_patients
    
    session.close()

@pytest.mark.asyncio
async def test_phi_access_with_audit_logging(synthetic_db_session):
    """Test PHI access creates proper audit trail"""
    
    session, synthetic_patients = synthetic_db_session
    test_patient = synthetic_patients[0]
    test_user_id = uuid4()
    
    # Mock the repository with test session
    repo = SecurePHIRepository(MockDatabaseManager(session))
    
    # Test PHI access
    result = await repo.get_patient_phi(
        patient_id=test_patient.patient_id,
        user_id=test_user_id,
        purpose='TREATMENT',
        fields_requested=['name', 'dob']
    )
    
    # Verify results
    assert result['patient_id'] == test_patient.patient_id
    assert 'data' in result
    assert result['access_logged'] is True
    
    # Verify audit log entry was created
    audit_entries = session.query(PHIAccessLog).filter_by(
        patient_id=test_patient.patient_id,
        user_id=test_user_id
    ).all()
    
    assert len(audit_entries) == 1
    assert audit_entries[0].purpose == 'TREATMENT'
    assert set(audit_entries[0].fields_requested) == {'name', 'dob'}

@pytest.mark.asyncio
async def test_synthetic_data_validation(synthetic_db_session):
    """Test synthetic data validation and integrity"""
    
    session, synthetic_patients = synthetic_db_session
    
    repo = SyntheticDataRepository(MockDatabaseManager(session))
    
    # Validate synthetic data integrity
    validation_result = await repo.validate_synthetic_data_integrity()
    
    assert validation_result['validation_passed'] is True
    assert validation_result['total_synthetic_records'] == 10
    assert validation_result['unmarked_records'] == 0
    assert validation_result['suspicious_patterns'] == 0
```

## Medical Disclaimer

**MEDICAL DISCLAIMER: This database development instruction set provides database architecture and development patterns for healthcare administrative systems only. It assists healthcare technology professionals with secure PHI handling, HIPAA compliance, audit trails, and database security. It does not provide medical advice, diagnosis, or treatment recommendations. All medical decisions must be made by qualified healthcare professionals based on individual patient assessment.**
