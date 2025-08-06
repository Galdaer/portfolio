# Database Development Healthcare Instructions

## Purpose

**DATABASE-FIRST ARCHITECTURE**: Healthcare applications prioritize databases as primary data source with appropriate fallbacks for development and testing. Production systems require database connectivity for PHI security.

## CRITICAL: Database-First Pattern (NOT Database-Only)

### Correct Database-First Implementation

**❌ WRONG PATTERN (Database-Only):**
```python
# ❌ WRONG: No fallbacks breaks development workflow
def get_patient_data(patient_id):
    try:
        return database.fetch_patient(patient_id)
    except DatabaseError as e:
        raise DatabaseConnectionError("Database required")  # Too rigid
```

**✅ CORRECT PATTERN (Database-First with Graceful Fallbacks):**
```python
# ✅ CORRECT: Database-first with appropriate fallbacks
def get_patient_data(patient_id):
    try:
        return database.fetch_patient(patient_id)
    except DatabaseConnectionError as e:
        logger.warning(f"Database unavailable: {e}")
        
        # Appropriate fallbacks based on environment and data sensitivity
        if is_development_environment():
            logger.info("Using synthetic data for development")
            return load_synthetic_data(patient_id)
        elif is_testing_environment():
            logger.info("Using test fixtures for automated testing") 
            return load_test_fixtures(patient_id)
        else:
            # Production: Database required for PHI security
            raise DatabaseConnectionError(
                "Production database required for PHI security. "
                "Please check database connectivity and configuration."
            )
```

**✅ ENHANCED PATTERN (Smart Fallback Selection):**
```python
# ✅ ENHANCED: Smart fallback based on data type and environment
def get_healthcare_data(data_type: str, identifier: str):
    try:
        return database.fetch_data(data_type, identifier)
    except DatabaseConnectionError:
        return handle_database_fallback(data_type, identifier)

def handle_database_fallback(data_type: str, identifier: str):
    """Handle database fallbacks based on data sensitivity and environment"""
    if contains_phi(data_type):
        # PHI data requires database in production
        if is_production_environment():
            raise DatabaseConnectionError("PHI data requires secure database connection")
        else:
            return generate_synthetic_phi_like_data(data_type, identifier)
    else:
        # Non-PHI data can use file fallbacks
        return load_fallback_data(data_type, identifier)
```

### Agent Database Requirements

**ALL AGENTS MUST:**
- **Primary**: Attempt database connectivity at startup
- **Fallback**: Use appropriate fallbacks for development/testing environments
- **Production**: Require database connectivity for PHI security
- **Error Handling**: Provide clear error messages and setup guidance
- **Logging**: Log database connection attempts and fallback usage for audit compliance

### Environment-Based Database Patterns

**Development Environment:**
- Database preferred, synthetic data fallback acceptable
- Clear logging when fallbacks are used
- Synthetic data clearly marked as non-PHI

**Testing Environment:**
- Database preferred, test fixtures fallback acceptable
- Isolated test database recommended
- No real PHI data ever used in testing

**Production Environment:**
- Database connectivity required
- No fallbacks for PHI data
- Graceful degradation only for non-PHI operations

### Database Connection Management Patterns

**✅ CORRECT: Proper connection management with context managers:**
```python
# ✅ CORRECT: Context manager for automatic connection release
from contextlib import asynccontextmanager

@asynccontextmanager
async def get_database_connection():
    """Get database connection with automatic release"""
    if healthcare_services.db_pool is None:
        raise DatabaseConnectionError("Database connection required")
    
    conn = await healthcare_services.db_pool.acquire()
    try:
        yield conn
    finally:
        await healthcare_services.db_pool.release(conn)

# Usage pattern
async def fetch_patient_data(patient_id: str):
    async with get_database_connection() as conn:
        return await conn.fetch("SELECT * FROM patients WHERE id = $1", patient_id)
```

**❌ WRONG: Connection leaks without proper release:**
```python
# ❌ WRONG: Connection never released back to pool
async def get_database_connection():
    return await healthcare_services.db_pool.acquire()  # LEAK!
```

```python
# ✅ CORRECT: Separate PHI and non-PHI data models
from sqlalchemy import Column, String, DateTime, Boolean, LargeBinary, UUID
from cryptography.fernet import Fernet

class PatientPHI(Base):
    __tablename__ = "patients_phi"
    
    patient_id = Column(UUID, primary_key=True)
    encrypted_name = Column(LargeBinary)  # Encrypted PHI
    encrypted_ssn = Column(LargeBinary)
    encrypted_dob = Column(LargeBinary)
    created_at = Column(DateTime)
    
class PatientNonPHI(Base):
    __tablename__ = "patients_non_phi"
    
    patient_id = Column(UUID, primary_key=True)
    insurance_type = Column(String(50))
    preferred_language = Column(String(20))
    visit_count = Column(Integer)
```

### 2. Healthcare Data Access Patterns

```python
# ✅ CORRECT: PHI-safe data access with audit logging
class HealthcareDataAccess:
    def __init__(self):
        self.phi_encryptor = Fernet(encryption_key)
        self.audit_logger = get_healthcare_logger('data_access')
    
    async def get_patient_data(self, patient_id: str, requesting_user: str):
        # Minimum necessary principle + audit logging
        self.audit_logger.info(f"PHI access requested", extra={
            'patient_id': patient_id,
            'requesting_user': requesting_user,
            'access_time': datetime.utcnow()
        })
        
        # Fetch only necessary fields
        phi_data = await self.decrypt_phi_fields(patient_id, required_fields)
        non_phi_data = await self.get_non_phi_data(patient_id)
        
        return merge_patient_data(phi_data, non_phi_data)
```

### 3. Synthetic Data Management

```python
# ✅ CORRECT: Database-backed synthetic data generation
class SyntheticHealthcareDataManager:
    def generate_realistic_phi_like_data(self) -> List[Dict[str, Any]]:
        # Generate synthetic data that looks like real PHI for testing PHI detection
        # Store in separate synthetic_patients table
        pass
    
    def populate_test_database(self):
        # Populate test database with synthetic healthcare data
        # Use for development and testing environments only
        pass
```

## Implementation Guidelines

### Healthcare Database Best Practices

- **Database-First**: Prioritize database connectivity, use appropriate fallbacks for development/testing
- **PHI Segregation**: Separate tables for PHI and non-PHI data
- **Encryption**: Encrypt all PHI at rest using industry-standard encryption
- **Audit Logging**: Log all database access for HIPAA compliance
- **Minimum Necessary**: Only access data fields required for the specific operation
- **Synthetic Data**: Use database-backed synthetic data for testing, with file fallbacks for development

---
