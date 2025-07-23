# Async/Sync Patterns for Healthcare AI Systems

**Document Version**: 1.0.0  
**Target Audience**: Developers, System Architects  
**Phase**: All Phases - Foundational Pattern  
**Last Updated**: January 2025

## Overview

This document establishes clear patterns for when to use async vs sync operations in the Intelluxe AI Healthcare System, with specific focus on healthcare compliance, data safety, and performance requirements.

## Core Principles

### **Async for I/O-bound Operations** (waiting for external resources)
- **Web requests** (FastAPI endpoints, HTTP clients)
- **Database queries** (PostgreSQL connections, complex queries)
- **Cache operations** (Redis when used for session storage)
- **File I/O** (reading medical documents, log files)
- **Network calls** (Ollama API, external medical APIs)
- **AI model inference** (local LLM calls, embedding generation)

### **Sync for CPU-bound Operations** (computation and security)
- **Data processing** (parsing medical records, PHI detection)
- **Encryption/decryption** (patient data protection)
- **Business logic** (RBAC calculations, compliance checks)
- **Security middleware** (authentication, rate limiting)
- **In-memory operations** (data validation, transformations)

## Healthcare-Specific Patterns

### **Security Operations: Sync by Design**

Healthcare security operations use **sync patterns** for predictable, debuggable behavior:

```python
# ✅ GOOD - Sync security middleware
class HealthcareSecurityMiddleware:
    def __init__(self, redis_conn: redis.Redis):  # Sync Redis client
        self.redis_conn = redis_conn
    
    def check_rate_limit(self, user_id: str) -> bool:
        """Sync rate limiting for predictable security"""
        current_count = self.redis_conn.get(f"rate_limit:{user_id}")
        if current_count and int(current_count) > 100:
            return False
        self.redis_conn.incr(f"rate_limit:{user_id}")
        return True

# ❌ AVOID - Async security can complicate error handling
async def check_rate_limit_async(user_id: str) -> bool:
    # More complex error handling, harder to debug failures
    pass
```

**Why sync for security:**
- **Predictable performance** - no async overhead for critical paths
- **Simpler error handling** - easier to debug authentication failures
- **Atomic operations** - Redis operations are naturally atomic
- **HIPAA compliance** - clearer audit trails with synchronous execution

### **Web Framework: Async for Scalability**

FastAPI endpoints use **async patterns** for handling multiple concurrent requests:

```python
# ✅ GOOD - Async web endpoints
@app.post("/api/patient/intake")
async def process_patient_intake(
    intake_data: PatientIntakeModel,
    current_user: User = Depends(get_current_user)
):
    """Async endpoint for handling multiple concurrent intakes"""
    
    # Async I/O operations
    patient_record = await db.fetch_patient(intake_data.patient_id)
    ai_summary = await ollama_client.generate_summary(intake_data.notes)
    
    # Sync business logic
    compliance_check = validate_hipaa_compliance(intake_data)  # Sync
    
    # Async database save
    result = await db.save_intake_record(patient_record, ai_summary)
    return result
```

### **Database Operations: Async with Transaction Safety**

Database operations use **async for I/O** but **transactions for consistency**:

```python
# ✅ GOOD - Async I/O with transaction safety
async def update_patient_assignment(user_id: str, patient_id: str):
    """Async database operations with ACID transactions"""
    
    async with db_pool.acquire() as conn:
        async with conn.transaction():  # Prevents race conditions
            # Multiple operations in single transaction
            await conn.execute(
                "INSERT INTO patient_assignments (user_id, patient_id) VALUES ($1, $2)",
                user_id, patient_id
            )
            await conn.execute(
                "UPDATE audit_log SET assignment_count = assignment_count + 1"
            )
            # Transaction commits automatically or rolls back on error
```

**Race condition protection comes from:**
- **PostgreSQL transactions** (ACID compliance)
- **Redis atomic operations** (single-threaded by design)
- **Application-level locks** (when needed for complex operations)

## Implementation Guidelines

### **Mixed Async/Sync Patterns**

Many healthcare operations combine both patterns:

```python
class PatientDataProcessor:
    def __init__(self):
        self.redis_conn = redis.Redis()  # Sync for security
        self.db_pool = asyncpg.create_pool()  # Async for I/O
    
    async def process_patient_document(self, document_path: str, user_id: str):
        """Mixed async/sync pattern for healthcare document processing"""
        
        # 1. Sync security check (predictable)
        if not self.check_user_permissions(user_id):  # Sync
            raise PermissionError("Access denied")
        
        # 2. Async file I/O (efficient)
        document_content = await aiofiles.open(document_path).read()
        
        # 3. Sync PHI detection (CPU-bound, security-critical)
        phi_detected = self.detect_phi(document_content)  # Sync
        
        # 4. Async AI processing (I/O-bound)
        if not phi_detected.has_phi:
            summary = await self.ollama_client.summarize(document_content)
        
        # 5. Async database save (I/O-bound)
        await self.save_processed_document(document_path, summary)
    
    def check_user_permissions(self, user_id: str) -> bool:
        """Sync security check"""
        return self.redis_conn.sismember("authorized_users", user_id)
    
    def detect_phi(self, content: str) -> PHIDetectionResult:
        """Sync PHI detection - CPU-bound and security-critical"""
        # Complex regex and NLP processing
        return PHIDetectionResult(...)
```

### **Error Handling Patterns**

Different error handling for async vs sync:

```python
# Sync error handling - simpler, more predictable
def sync_security_operation():
    try:
        result = redis_conn.get("security_key")
        return process_security_data(result)
    except redis.RedisError as e:
        logger.error(f"Security operation failed: {e}")
        raise SecurityError("Authentication system unavailable")

# Async error handling - more complex but necessary for I/O
async def async_database_operation():
    try:
        async with db_pool.acquire() as conn:
            return await conn.fetch("SELECT * FROM patients")
    except asyncpg.PostgreSQLError as e:
        logger.error(f"Database operation failed: {e}")
        raise DatabaseError("Patient data temporarily unavailable")
    except asyncio.TimeoutError:
        logger.error("Database operation timed out")
        raise DatabaseError("Request timed out - please try again")
```

## Performance Considerations

### **When Async Helps**
- **Multiple concurrent requests** (web endpoints)
- **I/O-heavy operations** (file processing, API calls)
- **Database queries** (especially with connection pooling)
- **Long-running AI operations** (document analysis, transcription)

### **When Sync is Better**
- **CPU-intensive operations** (encryption, data processing)
- **Security-critical paths** (authentication, authorization)
- **Simple operations** (configuration loading, validation)
- **Debugging complex workflows** (easier to trace execution)

## Testing Patterns

### **Testing Async Code**
```python
import pytest
import asyncio

@pytest.mark.asyncio
async def test_patient_data_processing():
    """Test async healthcare operations"""
    processor = PatientDataProcessor()
    result = await processor.process_patient_document("test.pdf", "user123")
    assert result.status == "processed"

# Use pytest-asyncio for async test support
```

### **Testing Sync Code**
```python
def test_security_middleware():
    """Test sync security operations"""
    middleware = HealthcareSecurityMiddleware(redis_conn)
    assert middleware.check_rate_limit("user123") == True
    
    # Easier to test edge cases with sync code
    for i in range(101):  # Exceed rate limit
        middleware.check_rate_limit("user123")
    assert middleware.check_rate_limit("user123") == False
```

## Migration Guidelines

### **Converting Sync to Async**
When you need to make sync code async (e.g., adding database operations):

```python
# Before: Sync only
def process_intake(intake_data):
    validation_result = validate_intake(intake_data)  # Sync
    return {"status": "validated"}

# After: Mixed async/sync
async def process_intake(intake_data):
    validation_result = validate_intake(intake_data)  # Keep sync
    
    # Add async database operation
    patient = await db.fetch_patient(intake_data.patient_id)  # New async
    
    return {"status": "validated", "patient": patient}
```

### **Converting Async to Sync**
When you need to make async code sync (e.g., for security middleware):

```python
# Before: Async (harder to debug)
async def check_permissions(user_id):
    result = await redis_client.get(f"permissions:{user_id}")
    return result

# After: Sync (easier to debug, more predictable)
def check_permissions(user_id):
    result = redis_client.get(f"permissions:{user_id}")  # Sync Redis
    return result
```

## Summary

**Use async for:**
- FastAPI endpoints and web I/O
- Database queries and file operations
- AI model calls and external APIs
- Any operation that waits for external resources

**Use sync for:**
- Security and authentication operations
- PHI detection and data processing
- Business logic and validation
- CPU-intensive computations

**Remember:** Race conditions are prevented by **database transactions** and **Redis atomicity**, not by choosing sync over async. The choice should be based on **I/O vs CPU** and **debugging complexity**.