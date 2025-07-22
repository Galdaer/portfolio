# Healthcare Security Development Patterns

## Security Error Message Guidelines

### NEVER expose internal configuration in error messages
```python
# ❌ BAD - Reveals internal config structure
raise RuntimeError("JWT_SECRET must be set in production")
raise RuntimeError("MASTER_ENCRYPTION_KEY is not set in production environment")

# ✅ GOOD - Generic security error
raise RuntimeError("Critical security configuration missing. Contact system administrator.")
raise RuntimeError("Authentication system configuration error. Please contact support.")
```

### Log detailed errors internally, show generic errors externally
```python
# ✅ PATTERN: Detailed internal logging + generic external error
def validate_production_config(self):
    if not os.getenv("JWT_SECRET"):
        self.logger.error("JWT_SECRET not configured for production environment")
        raise RuntimeError("Authentication configuration error. Contact support.")
    
    if not os.getenv("MASTER_ENCRYPTION_KEY"):
        self.logger.error("MASTER_ENCRYPTION_KEY missing in production")
        raise RuntimeError("Encryption configuration error. Contact support.")
```

## Placeholder Implementation Guidelines

### NEVER create overly restrictive placeholders that block development
```python
# ❌ BAD - Blocks all legitimate development work
def is_user_assigned_to_patient(self, user_id: str, patient_id: str) -> bool:
    return False  # Always denies access

# ✅ GOOD - Configurable with safe defaults
def is_user_assigned_to_patient(self, user_id: str, patient_id: str) -> bool:
    environment = os.getenv("ENVIRONMENT", "development").lower()
    
    if environment == "production":
        self.logger.error("Patient assignment validation not implemented for production")
        raise NotImplementedError(
            "Patient assignment validation required for production deployment"
        )
    
    # Development mode: configurable behavior
    default_access = os.getenv('RBAC_DEFAULT_PATIENT_ACCESS', 'true').lower() == 'true'
    
    if default_access:
        self.logger.debug(f"DEV MODE: Allowing patient access {user_id} -> {patient_id}")
        return True
    else:
        self.logger.debug(f"DEV MODE: Denying patient access {user_id} -> {patient_id}")
        return False
```

### Production Deployment Blocks
```python
# ✅ PATTERN: Block production deployment, allow development
def validate_production_readiness(self):
    """Validate system is ready for production deployment"""
    environment = os.getenv("ENVIRONMENT", "development").lower()
    
    if environment == "production":
        missing_features = []
        
        if not self._has_patient_assignment_logic():
            missing_features.append("Patient assignment validation")
        
        if not self._has_audit_compliance():
            missing_features.append("HIPAA audit compliance")
        
        if missing_features:
            error_msg = f"Production deployment blocked. Missing: {', '.join(missing_features)}"
            self.logger.error(error_msg)
            raise NotImplementedError(error_msg)
```

## Test Coverage Patterns

### ALWAYS test security fallback behavior with logging verification
```python
# ✅ PATTERN: Test both behavior AND logging
def test_security_fallback_with_logging(self, caplog):
    """Test security fallback returns secure default AND logs appropriately"""
    with patch.dict(os.environ, {}, clear=True):
        with patch('module.function', side_effect=Exception("Config error")):
            
            # Test secure behavior
            result = SecurityClass.secure_method()
            assert result is True  # Secure default
            
            # Test logging behavior
            assert "Environment detection failed" in caplog.text
            assert "Assuming production mode as secure default" in caplog.text
            assert caplog.records[-1].levelname == "WARNING"
```

## Scalability Patterns

### ALWAYS consider large dataset handling
```python
# ❌ BAD - No batching for large datasets
def process_all_items(self, items: List[str]) -> List[str]:
    return [self.expensive_operation(item) for item in items]

# ✅ GOOD - Batched processing with memory management
def process_all_items(self, items: List[str], batch_size: int = 500) -> List[str]:
    """Process items in batches to manage memory usage"""
    results = []
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_results = [self.expensive_operation(item) for item in batch]
        results.extend(batch_results)
        
        # Optional: garbage collection for very large datasets
        if len(results) % 5000 == 0:
            import gc
            gc.collect()
    
    return results
```

## Documentation Patterns

### ALWAYS explain security/compliance choices
```python
# ✅ PATTERN: Document WHY security choices were made
class SyntheticDataGenerator:
    # The 555 prefix complies with North American Numbering Plan (NANP) 
    # standards for fictional numbers, preventing accidental contact with real people
    PHONE_PREFIX = "555"
    
    # Synthetic insurance names prevent confusion with real providers
    # and ensure test data is clearly identified as non-production
    INSURANCE_PROVIDERS = [
        'Synthetic Health Plan A',  # Clearly marked as test data
        'Synthetic Medicare',       # Prevents real Medicare confusion
    ]
```

## Environment Detection Patterns

### ALWAYS provide fallback behavior with appropriate logging
```python
# ✅ PATTERN: Secure fallback with comprehensive logging
@classmethod
def is_production(cls) -> bool:
    """Determine if running in production with secure fallback"""
    try:
        environment = cls.get_environment()
        return environment.lower() == "production"
    except Exception as e:
        # Log the specific error for debugging
        logger.warning(f"Environment detection failed: {e}")
        logger.warning("Falling back to production mode as secure default")
        
        # Return secure default (production mode has stricter security)
        return True
```

## Configuration Management Patterns

### ALWAYS provide environment-appropriate defaults
```python
# ✅ PATTERN: Environment-aware configuration
class HealthcareConfig:
    def __init__(self):
        environment = os.getenv("ENVIRONMENT", "development").lower()
        
        # Security settings based on environment
        if environment == "production":
            self.rbac_strict_mode = True
            self.placeholder_warnings = False
            self.require_all_secrets = True
        else:
            # Development: More permissive but with warnings
            self.rbac_strict_mode = False
            self.placeholder_warnings = True
            self.require_all_secrets = False
```

## Code Review Checklist

Before submitting code, verify:

- [ ] Error messages don't reveal internal configuration details
- [ ] Placeholder implementations don't block legitimate development workflows
- [ ] Production deployment is blocked when features are incomplete
- [ ] Security fallbacks are tested with logging verification
- [ ] Large dataset processing includes batching/memory management
- [ ] Security and compliance choices are documented with rationale
- [ ] Environment-specific behavior is clearly defined
- [ ] All configuration has appropriate defaults for each environment

## Anti-Patterns to Avoid

1. **Information Disclosure**: `"JWT_SECRET must be set"` → `"Authentication error"`
2. **Development Blockers**: `return False` → `configurable with safe defaults`
3. **Untested Fallbacks**: Security fallbacks without logging tests
4. **Memory Issues**: Processing large datasets without batching
5. **Undocumented Security**: Security choices without explanation
6. **Environment Confusion**: Same behavior in dev/prod without consideration