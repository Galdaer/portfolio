# Database Development Healthcare Instructions

## Purpose

**DATABASE-FIRST ARCHITECTURE**: All healthcare applications must use databases as primary data source. No synthetic file fallbacks allowed except for GitHub coding agents with database setup capability.

## CRITICAL: Database-First Enforcement

### Database Connection Requirements

**❌ PROHIBITED PATTERNS:**
```python
# ❌ WRONG: File fallbacks compromise security
def get_patient_data(patient_id):
    try:
        return database.fetch_patient(patient_id)
    except DatabaseError:
        return load_synthetic_file(patient_id)  # PROHIBITED
```

**✅ REQUIRED PATTERNS:**
```python
# ✅ CORRECT: Database-first with proper error handling
def get_patient_data(patient_id):
    try:
        return database.fetch_patient(patient_id)
    except DatabaseError as e:
        logger.error(f"Database connection failed: {e}")
        raise DatabaseConnectionError("Healthcare database unavailable. Please check connection.")
```

### Agent Database Requirements

**ALL AGENTS MUST:**
- Verify database connectivity at startup
- Fail gracefully with clear error messages when database unavailable
- Provide database setup guidance in error messages
- Log database connection attempts for audit compliance

## Healthcare Database Architecture Principles

### 1. PHI Segregation Architecture

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

- **Database-First**: Never use file fallbacks, always require database connectivity
- **PHI Segregation**: Separate tables for PHI and non-PHI data
- **Encryption**: Encrypt all PHI at rest using industry-standard encryption
- **Audit Logging**: Log all database access for HIPAA compliance
- **Minimum Necessary**: Only access data fields required for the specific operation
- **Synthetic Data**: Use database-backed synthetic data for testing, not file-based

---
