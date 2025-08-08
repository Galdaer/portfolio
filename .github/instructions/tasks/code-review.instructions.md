````instructions
# Healthcare AI Code Review Instructions

## Purpose

Code review guidance for healthcare AI systems emphasizing medical compliance, PHI protection, and healthcare-specific patterns.

## Healthcare Code Review Patterns (Based on PR #31 Analysis)

### Type Safety & Financial Calculations
```python
# ❌ WRONG: Float precision loss in healthcare billing
copay_amount = 25.50  # float - precision issues
coinsurance = 0.80    # float - rounding errors

# ✅ CORRECT: Decimal precision for financial calculations
from decimal import Decimal
copay_amount = Decimal('25.50')
coinsurance = Decimal('0.80')

# ✅ CORRECT: Method signature consistency
def calculate_patient_cost(self, 
                          base_cost: Decimal,
                          insurance_rate: Decimal,
                          copay: Decimal) -> Decimal:
    """Calculate patient cost with exact precision"""
    if base_cost <= 0:
        raise ValueError("Base cost must be positive")
    
    insurance_portion = base_cost * insurance_rate
    patient_portion = base_cost - insurance_portion + copay
    return patient_portion.quantize(Decimal('0.01'))
```

### Database Resource Management Patterns  
```python
# ❌ WRONG: Connection leak risk
async def get_patient_data(patient_id: str):
    conn = await pool.acquire()
    result = await conn.fetch("SELECT * FROM patients WHERE id = $1", patient_id)
    # Missing connection release!
    return result

# ✅ CORRECT: Proper async context management
async def get_patient_data(self, patient_id: str) -> Optional[Dict[str, Any]]:
    async with self.db_pool.acquire() as conn:
        result = await conn.fetchrow(
            "SELECT * FROM patients WHERE id = $1", patient_id
        )
        return dict(result) if result else None

# ✅ CORRECT: Exception-safe cleanup
async def complex_patient_operation(self, patient_id: str):
    conn = await self.pool.acquire()
    try:
        async with conn.transaction():
            # Multiple database operations
            await self.update_patient_record(conn, patient_id)
            await self.log_access_event(conn, patient_id)
    finally:
        await self.pool.release(conn)
```

### Code Duplication Prevention
```python
# ❌ WRONG: Duplicate utility methods across files
# In billing_helper.py:
def _ensure_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))

# In insurance.py: (DUPLICATE!)
def _ensure_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))

# ✅ CORRECT: Shared utilities module
# In core/financial/utils.py:
class FinancialUtils:
    @staticmethod
    def ensure_decimal(value: Any) -> Decimal:
        """Convert value to Decimal for financial calculations"""
        if isinstance(value, Decimal):
            return value
        if value is None:
            return Decimal('0')
        return Decimal(str(value))
    
    @staticmethod
    def safe_division(numerator: Decimal, denominator: Decimal) -> Decimal:
        """Perform safe division with zero-check"""
        if denominator == 0:
            return Decimal('0')
        return numerator / denominator
```

### PHI Protection in Code Reviews
```python
# ❌ WRONG: PHI in logging
logger.info(f"Processing patient John Doe, SSN: 123-45-6789")

# ❌ WRONG: PHI in error messages  
raise ValueError(f"Invalid patient data for {patient_name}")

# ✅ CORRECT: PHI-safe logging and errors
logger.info(f"Processing patient {patient_id[:4]}***", extra={
    'patient_ref': patient_id,
    'operation': 'data_processing'
})

raise ValueError(f"Invalid patient data for patient_ref {patient_id}")
```

### Security Review Patterns
```python
# ❌ WRONG: Hardcoded credentials
API_KEY = "sk-1234567890abcdef"  # Exposed in code

# ❌ WRONG: Overly permissive CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Security risk!
    allow_credentials=True,
)

# ✅ CORRECT: Environment-based configuration
from config import Config
config = Config()
api_key = config.get_api_key()  # From environment/vault

# ✅ CORRECT: Restricted CORS for healthcare
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,  # Specific healthcare domains
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
```

## Healthcare Code Review Checklist

### Medical Safety & Compliance
- [ ] **No medical advice**: Code doesn't provide diagnosis or treatment recommendations
- [ ] **Medical disclaimers**: Appropriate disclaimers in healthcare-facing modules
- [ ] **PHI protection**: No patient data hardcoded or inappropriately logged
- [ ] **HIPAA compliance**: Proper audit trails and access controls

### Financial & Data Accuracy  
- [ ] **Decimal precision**: Financial calculations use Decimal, not float
- [ ] **Division by zero**: Protected against zero-division errors
- [ ] **Null handling**: Proper None value checking in calculations
- [ ] **Method signatures**: Consistent parameter types across related methods

### Resource Management
- [ ] **Database connections**: Proper acquisition and release patterns
- [ ] **Async context**: Using async context managers appropriately  
- [ ] **Exception safety**: Resources cleaned up in error scenarios
- [ ] **Memory leaks**: No unclosed files, connections, or resources

### Code Quality Patterns
- [ ] **No duplication**: Shared utilities extracted to common modules
- [ ] **Import cleanup**: No redundant or unused imports
- [ ] **Constants**: Magic numbers replaced with named constants
- [ ] **Type annotations**: All functions have proper return types

### Security & Performance
- [ ] **Credential management**: No hardcoded API keys or passwords
- [ ] **Input validation**: User inputs properly sanitized
- [ ] **Error handling**: Errors don't expose sensitive information
- [ ] **Performance**: No obvious N+1 query or memory leak patterns
````
