# Python Healthcare AI Development Instructions

## Purpose

Python patterns for healthcare AI systems with focus on medical compliance, PHI protection, and beyond-HIPAA security standards that prioritize patient safety and privacy.

## Beyond-HIPAA Python Security Principles

### SciSpacy Model Upgrade Patterns (Biomedical NLP)

**PATTERN**: Upgrading biomedical NLP models while maintaining entity filtering compatibility.

```python
# ✅ SUCCESSFUL PATTERN: SciSpacy model upgrade from BC5CDR to BIONLP13CG
class SciSpacyModelUpgrade:
    """Patterns for upgrading biomedical NLP models."""
    
    # Entity type expansion: BC5CDR (2 types) → BIONLP13CG (16 types)
    BIONLP13CG_ENTITY_TYPES = {
        "AMINO_ACID", "ANATOMICAL_SYSTEM", "CANCER", "CELL", 
        "CELLULAR_COMPONENT", "DEVELOPING_ANATOMICAL_STRUCTURE",
        "GENE_OR_GENE_PRODUCT", "IMMATERIAL_ANATOMICAL_ENTITY",
        "MULTI-TISSUE_STRUCTURE", "ORGAN", "ORGANISM", 
        "ORGANISM_SUBDIVISION", "ORGANISM_SUBSTANCE",
        "PATHOLOGICAL_FORMATION", "SIMPLE_CHEMICAL", "TISSUE"
    }
    
    BC5CDR_ENTITY_TYPES = {"CHEMICAL", "DISEASE"}
    
    @staticmethod
    def update_entity_filtering(old_entities: set, new_entities: set) -> set:
        """Update entity filtering when upgrading models."""
        # Validate new entity types are comprehensive
        if len(new_entities) < len(old_entities):
            raise ValueError("New model should have equal or more entity types")
        
        # Update medical entity filtering
        medical_entity_types = {
            ent for ent in new_entities 
            if any(keyword in ent.lower() for keyword in [
                'organ', 'tissue', 'cell', 'anatomical', 'organism', 
                'chemical', 'disease', 'cancer', 'pathological'
            ])
        }
        
        return medical_entity_types

# ✅ CONTAINER UPDATE PATTERN: Model downloading in entrypoint
def update_container_model_download():
    """Pattern for updating container model downloads."""
    return '''
    # entrypoint.sh pattern for model upgrades
    echo "Downloading SciSpacy BIONLP13CG model..."
    python -m spacy download en_ner_bionlp13cg_md
    echo "Model download complete"
    '''

# ✅ SERVICE UPDATE PATTERN: Model loading in service
class SciSpacyService:
    def __init__(self):
        # Model upgrade: en_ner_bc5cdr_md → en_ner_bionlp13cg_md
        self.nlp = spacy.load("en_ner_bionlp13cg_md")
        
    def detect_entities(self, text: str) -> List[Dict[str, Any]]:
        """Detect biomedical entities with upgraded model."""
        doc = self.nlp(text)
        entities = []
        
        for ent in doc.ents:
            # Filter for medical relevance
            if ent.label_ in self.BIONLP13CG_ENTITY_TYPES:
                entities.append({
                    "text": ent.text,
                    "label": ent.label_,
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "confidence": getattr(ent, 'score', 0.0)
                })
        
        return entities
```

### Patient-First Python Standards
- **Zero tolerance for PHI exposure**: No `# type: ignore` in healthcare modules (suppresses safety checks)
- **Proactive type safety**: Enhanced type annotations beyond basic compliance
- **Emergency-safe error handling**: Failures never compromise patient care
- **Compassionate code design**: Code that supports healthcare providers, protects patients

## Enhanced Type Safety from Production Issues (Based on PR #31)

### MANDATORY Healthcare Type Safety Patterns (Lessons from Real Issues)

```python
# ✅ CRITICAL: Financial type safety patterns (From PR review feedback)
from decimal import Decimal
from typing import Any, Union

class HealthcareFinancialTypeSafety:
    """Type safety patterns for healthcare financial calculations."""
    
    @staticmethod
    def ensure_decimal_precision(value: Any) -> Decimal:
        """Convert financial values to Decimal safely (pattern from PR #31)."""
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float)):
            return Decimal(str(value))  # String conversion preserves precision
        if isinstance(value, str):
            return Decimal(value)
        raise ValueError(f"Cannot convert {type(value)} to Decimal")
    
    @staticmethod
    def validate_method_signature_match(
        method_name: str, 
        provided_params: Dict[str, Any], 
        expected_params: List[str]
    ) -> bool:
        """Validate method calls match expected signatures (prevents runtime errors)."""
        provided_keys = set(provided_params.keys())
        expected_keys = set(expected_params)
        
        missing_params = expected_keys - provided_keys
        unexpected_params = provided_keys - expected_keys
        
        if missing_params or unexpected_params:
            logger.error(f"Method signature mismatch for {method_name}: missing={missing_params}, unexpected={unexpected_params}")
            return False
        return True

# ✅ CRITICAL: Import management patterns (From PR review feedback)
class HealthcareImportSafety:
    """Import safety patterns to prevent duplicate imports."""
    
    @staticmethod
    def detect_duplicate_imports(code: str) -> List[str]:
        """Detect duplicate import statements."""
        import_lines = [
            line.strip() for line in code.split('\n') 
            if line.strip().startswith(('import ', 'from '))
        ]
        
        duplicates = []
        seen = set()
        for line in import_lines:
            if line in seen:
                duplicates.append(line)
            seen.add(line)
        
        return duplicates
    
    @staticmethod
    def organize_healthcare_imports() -> str:
        """Standard import organization for healthcare modules."""
        return '''
# Standard library imports
import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

# Third-party imports
import asyncpg
from fastapi import HTTPException

# Healthcare-specific imports
from core.dependencies import get_database_connection, DatabaseConnectionError
from core.infrastructure.healthcare_logger import healthcare_log_method
'''

# ✅ CRITICAL: Database resource safety patterns (From PR review feedback)
class HealthcareDatabaseTypeSafety:
    """Database connection type safety patterns."""
    
    @asynccontextmanager
    async def get_connection_with_proper_release(self) -> AsyncGenerator[Any, None]:
        """Proper database connection management with type safety."""
        conn = await self.pool.acquire()
        try:
            yield conn
        finally:
            await self.pool.release(conn)  # CRITICAL: Always release
    
    async def safe_database_query(
        self, 
        query: str, 
        params: Optional[List[Any]] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """Type-safe database querying with connection management."""
        async with self.get_connection_with_proper_release() as conn:
            try:
                result = await conn.fetch(query, *(params or []))
                return [dict(row) for row in result]
            except Exception as e:
                logger.error(f"Database query failed: {e}")
                return None

## Type Safety & Code Quality Requirements (Enhanced)

### MANDATORY Type Safety Patterns for Healthcare

```python
# ❌ NEVER USE: Suppresses critical healthcare safety checks
patient_data = get_patient() # type: ignore[return-value]

# ✅ ALWAYS USE: Healthcare-safe optional import patterns
from typing import Optional, Any, TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from some_medical_package import MedicalRecord
else:
    MedicalRecord = Any

# ✅ PATTERN: Enhanced healthcare type safety
class HealthcareDataProcessor(Protocol):
    def process_patient_data(
        self, 
        patient_id: str, 
        data_fields: List[str],
        requesting_provider: str
    ) -> Optional[Dict[str, Any]]:
        """
        Process patient data with enhanced type safety.
        
        Returns None if PHI protection protocols prevent access.
        Includes audit logging and minimum necessary principle.
        """
        ...

# ✅ PATTERN: Type-safe healthcare data structures
@dataclass
class PatientDataRequest:
    patient_id: str
    requesting_provider_npi: str
    data_purpose: str  # Required for minimum necessary principle
    emergency_access: bool = False
    audit_trail_id: Optional[str] = None

@dataclass 
class PHISafeResponse:
    success: bool
    data: Optional[Dict[str, Any]]
    audit_logged: bool
    phi_detected: bool
    medical_disclaimer: str = "Administrative support only. No medical advice."
```

### Enhanced Error Handling (Beyond HIPAA)

```python
# ✅ PATTERN: Patient-first error handling
class HealthcareError(Exception):
    """Base exception for healthcare operations with enhanced safety."""
    
    def __init__(self, message: str, patient_impact: str = "none", escalate_to_human: bool = False):
        super().__init__(message)
        self.patient_impact = patient_impact
        self.escalate_to_human = escalate_to_human
        self.medical_disclaimer = "Administrative support only. Consult healthcare provider."

class EmergencyEscalationError(HealthcareError):
    """Critical error requiring immediate human intervention."""
    
    def __init__(self, message: str):
        super().__init__(
            message=message,
            patient_impact="potential",
            escalate_to_human=True
        )

# ✅ PATTERN: Safe error handling with patient protection
def safe_healthcare_operation(operation: Callable) -> PHISafeResponse:
    """Execute healthcare operations with comprehensive error protection."""
    try:
        result = operation()
        return PHISafeResponse(
            success=True,
            data=result,
            audit_logged=True,
            phi_detected=False
        )
    except EmergencyEscalationError as e:
        # Immediately escalate to human oversight
        escalation_service.notify_healthcare_provider(e)
        return PHISafeResponse(
            success=False,
            data=None,
            audit_logged=True,
            phi_detected=False
        )
    except Exception as e:
        # Generic error - ensure no PHI in error messages
        safe_error_msg = sanitize_error_message(str(e))
        logger.error(f"Healthcare operation failed: {safe_error_msg}")
        return PHISafeResponse(success=False, data=None, audit_logged=True, phi_detected=False)
```

### PHI-Safe Data Processing Patterns

```python
# ✅ PATTERN: Enhanced PHI detection and protection
class EnhancedPHIProtector:
    """PHI protection beyond HIPAA minimum requirements."""
    
    def __init__(self):
        # Beyond HIPAA: Additional privacy identifiers
        self.extended_phi_patterns = [
            "ssn", "phone", "email", "mrn", "dob", "address",
            # Enhanced: Additional sensitive patterns
            "voice_print", "biometric", "genetic_marker", 
            "mental_health", "substance_abuse", "hiv_status"
        ]
        self.zero_tolerance_policy = True
    
    def scan_for_phi(self, data: Any) -> PHIDetectionResult:
        """Scan data for PHI with enhanced detection beyond HIPAA."""
        # Pattern: Proactive PHI detection with zero false negatives
        detection_result = self.deep_scan_all_patterns(data)
        
        if detection_result.any_phi_detected and self.zero_tolerance_policy:
            # Refuse to process any data containing potential PHI
            raise PHIDetectedError("Potential PHI detected - refusing to process")
        
        return detection_result

# ✅ PATTERN: Minimum necessary principle with enhanced protection
class MinimumNecessaryEnforcer:
    """Enforce data minimization beyond HIPAA requirements."""
    
    def filter_to_necessary_fields(
        self, 
        patient_data: Dict[str, Any], 
        purpose: str,
        requesting_provider: str
    ) -> Dict[str, Any]:
        """Filter data to absolute minimum necessary for stated purpose."""
        
        # Pattern: Start with zero fields, add only what's essential
        necessary_fields = self.determine_essential_fields(purpose)
        
        # Beyond HIPAA: Additional purpose validation
        if not self.validate_legitimate_purpose(purpose, requesting_provider):
            raise UnauthorizedAccessError("Purpose not justified for data access")
        
        # Return only essential fields
        return {field: patient_data[field] for field in necessary_fields if field in patient_data}
```

### Healthcare-Specific Python Patterns

```python
# ✅ PATTERN: Medical workflow processing with safety validation
class HealthcareWorkflowProcessor:
    """Process healthcare workflows with enhanced safety checks."""
    
    @healthcare_audit_log
    def process_patient_intake(self, intake_data: Dict[str, Any]) -> PHISafeResponse:
        """Process patient intake with comprehensive safety validation."""
        
        # Pattern: Validate medical safety before processing
        if self.contains_medical_advice_request(intake_data):
            return PHISafeResponse(
                success=False,
                data={"message": "Cannot provide medical advice. Please consult healthcare provider."},
                audit_logged=True,
                phi_detected=False
            )
        
        # Pattern: Process administrative data only
        administrative_data = self.extract_administrative_fields(intake_data)
        result = self.process_administrative_workflow(administrative_data)
        
        return PHISafeResponse(
            success=True,
            data=result,
            audit_logged=True,
            phi_detected=self.phi_protector.scan_for_phi(result).any_phi_detected
        )

# ✅ PATTERN: Emergency-aware processing
class EmergencyAwareProcessor:
    """Healthcare processing with emergency scenario prioritization."""
    
    def __init__(self):
        self.emergency_indicators = [
            "chest pain", "difficulty breathing", "severe trauma",
            "loss of consciousness", "severe bleeding", "stroke symptoms"
        ]
        self.emergency_response_time_limit = 0.5  # 500ms max for emergencies
    
    def process_with_emergency_detection(self, request: Dict[str, Any]) -> PHISafeResponse:
        """Process requests with automatic emergency escalation."""
        
        # Pattern: Immediate emergency detection
        if self.is_emergency_scenario(request):
            # Escalate immediately to human oversight
            escalation_service.escalate_emergency(request)
            
            return PHISafeResponse(
                success=True,
                data={"escalated": True, "emergency_response": "Human provider notified immediately"},
                audit_logged=True,
                phi_detected=False
            )
        
        # Continue with normal processing for non-emergency scenarios
        return self.process_standard_request(request)
```

## Implementation Guidelines

### Python Best Practices (Beyond HIPAA)

**Patient-First Python Design:**
- **Zero PHI Tolerance**: Never suppress type checking in healthcare modules
- **Enhanced Type Safety**: Comprehensive type annotations beyond basic compliance
- **Emergency-Aware Processing**: Automatic detection and escalation of critical scenarios
- **Proactive Error Handling**: Failures escalate to human oversight when needed
- **Extended PHI Detection**: Protect additional sensitive data beyond HIPAA minimums

**Security-Enhanced Python Patterns:**
- **Minimum Necessary Plus**: Enforce data minimization beyond legal requirements
- **Audit Everything**: Comprehensive logging of all healthcare operations
- **Safe Error Messages**: Never expose PHI or system details in error responses
- **Emergency Response**: <500ms response time for critical medical scenarios
- **Human-in-the-Loop**: Automatic escalation for complex or emergency situations

---
