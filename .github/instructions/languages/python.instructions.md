# Python Healthcare AI Development Instructions

## Purpose

Specialized Python development patterns for healthcare AI systems with focus on medical compliance, PHI protection, and modern Python tooling.

**For initial Python environment setup**: See `docs/PHASE_1.md` for Ruff, MyPy, and pre-commit installation commands.
**This file focuses on**: Ongoing development patterns and coding standards using those tools.

## Type Safety & Code Quality Requirements

### MANDATORY Type Annotations

- **MANDATORY Return Type Annotations**: All functions need `-> ReturnType`
- **MANDATORY Variable Type Annotations**: All class attributes and complex variables need explicit typing
- **Optional Type Handling**: Always check `if obj is not None:` before method calls
- **Type-Safe Dictionary Operations**: Use `isinstance()` checks before operations
- **Environment Variable Safety**: Handle `os.getenv()` returning None
- **Mixed Dictionary Types**: Use `Dict[str, Any]` for mixed-type dictionaries
- **CRITICAL: Implement Don't Remove**: When fixing "unused variable" warnings, ALWAYS implement the variable's intended functionality rather than removing it. Unused variables often represent important data (especially medical information) that should be used, not discarded.

### Systematic Type Annotation Checklist

**Before ANY code edit, verify these type patterns:**

1. **Class Attributes**: `self.data: List[Dict[str, Any]] = []`
2. **Function Returns**: `def process() -> Dict[str, Any]:`
3. **Complex Variables**: `results: Dict[str, Any] = {}`
4. **Healthcare Lists**: `patients: List[Dict[str, Any]] = []`
5. **Set Collections**: Import `Set` from typing when using `set()`

**Common Type Annotation Patterns:**

```python
# Healthcare data structures
self.patients: List[Dict[str, Any]] = []
self.encounters: List[Dict[str, Any]] = []

# Function signatures
def validate_data(self, data: Dict[str, Any]) -> Dict[str, Any]:

# Complex variables
results: Dict[str, Any] = {"status": "success"}
scenarios: List[HealthcareTestCase] = []
```

### MyPy Error Resolution Patterns

**Systematic approach to MyPy errors:**

1. **Missing Type Annotations**: Add explicit types for ALL variables
2. **Collection Issues**: Import specific types (`Set`, `List`, `Dict`) from typing
3. **Attribute Errors**: Use type annotations on class attributes
4. **Return Type Missing**: Add `-> ReturnType` to ALL function definitions
5. **Optional Handling**: Check `if obj is not None:` before method calls

**Common MyPy Error Fixes:**

```python
# Error: Need type annotation for "data"
data = []  # ❌ Wrong
data: List[Dict[str, Any]] = []  # ✅ Correct

# Error: "Collection[str]" has no attribute "append"
from typing import Set  # Add missing import
results["items"] = set()  # Then use proper typing

# Error: Function is missing return type annotation
def process():  # ❌ Wrong
def process() -> Dict[str, Any]:  # ✅ Correct
```

### Type Checking Best Practices

- **Mypy Medical Modules**: Use `python3 -m mypy [file] --config-file mypy.ini --ignore-missing-imports` for medical modules
- **Systematic Resolution**: Address type errors in order: missing imports, unused variables, type annotations, missing method implementations
- **Safe Attribute Access**: Use `getattr()` with defaults for accessing attributes that may not exist on all object types

### Python Error Prevention Checklist

**Before editing any file:**

1. **Read File Context**: Always read 20+ lines around your target edit area
2. **Check Imports**: Verify all required typing imports are present (`List`, `Dict`, `Set`, `Any`)
3. **Type Annotations**: Add explicit types for all new variables and function returns
4. **Medical Variables**: Investigate purpose of any "unused" variables before modifying
5. **Test Immediately**: Run `make lint` after each significant change

**Systematic Linting Workflow:**

```bash
# 1. Check current state
make lint 2>&1 | tee lint_errors.txt

# 2. Fix one category at a time
# - Missing imports first
# - Type annotations second
# - Unused variable implementation third
# - Return type annotations last

# 3. Validate each step
make lint  # Should show fewer errors each iteration

# 4. Final validation
make lint && make validate
```

## Medical Data Preservation Protocol

**NEVER remove medical variables without understanding their purpose:**

1. **Investigate First**: Read the surrounding code to understand what the variable represents
2. **Check Medical Context**: Variables like `reason`, `assessment`, `diagnosis` often contain different medical information
3. **Implement Properly**: Use the variable in its intended medical context (SOAP notes, patient records, etc.)
4. **Verify Medical Accuracy**: Ensure medical terminology is used correctly

**Example - Medical Variable Implementation:**

```python
# ❌ WRONG: Removing unused medical variable
reason = context_data.get("reason", "routine care")  # Removed to fix linting

# ✅ CORRECT: Implementing medical variable properly
reason = context_data.get("reason", "routine care")  # Reason for visit
assessment = context_data.get("assessment", "stable")  # Clinical assessment

# Use both in appropriate medical contexts
subjective = f"Patient presents with {chief_complaint} (reason: {reason})"
soap_assessment = f"Assessment: {assessment}"
```

## Modern Python Development Tools

### Ruff: Ultra-Fast Python Tooling (10-100x Faster)

```bash
# Replaces: black + isort + flake8 + pyupgrade + autoflake (5 separate tools)
pip install ruff

# Format and fix all Python files
ruff format .
ruff check --fix .

# Pre-commit integration
ruff check --fix src/ tests/ scripts/
```

**Migration from Legacy Tools:**

- **BLACK → RUFF**: `ruff format` (same output, 10-100x faster)
- **isort → RUFF**: `ruff check --select I --fix` (import sorting)
- **flake8 → RUFF**: `ruff check` (linting with 600+ rules)
- **pyupgrade → RUFF**: `ruff check --select UP --fix` (Python syntax upgrades)
- **autoflake → RUFF**: `ruff check --select F401 --fix` (unused imports)

## Modern Python Healthcare Patterns

### Type Safety for Healthcare Data

```python
from typing import Dict, List, Optional, Union, Protocol, TypeVar, Generic
from dataclasses import dataclass
from datetime import datetime, date
import hashlib

# ✅ CORRECT: Healthcare data type definitions
@dataclass
class PatientData:
    """Type-safe patient data structure with PHI protection."""
    patient_id: str
    encounter_id: str
    demographics: Dict[str, Union[str, int, date]]
    medical_history: List[str]
    current_medications: List[Dict[str, str]]
    allergies: List[str]
    insurance_info: Dict[str, str]

    def anonymize_for_logging(self) -> Dict[str, str]:
        """Return anonymized version safe for logging."""
        return {
            "patient_hash": hashlib.sha256(self.patient_id.encode()).hexdigest()[:8],
            "encounter_hash": hashlib.sha256(self.encounter_id.encode()).hexdigest()[:8],
            "demographics_count": len(self.demographics),
            "medication_count": len(self.current_medications),
            "allergy_count": len(self.allergies)
        }

@dataclass
class SOAPNote:
    """Type-safe SOAP note structure."""
    subjective: str
    objective: str
    assessment: str
    plan: str
    timestamp: datetime
    provider_id: str

    def validate_completeness(self) -> List[str]:
        """Validate SOAP note completeness (administrative only)."""
        missing_sections = []
        if not self.subjective.strip():
            missing_sections.append("subjective")
        if not self.objective.strip():
            missing_sections.append("objective")
        if not self.assessment.strip():
            missing_sections.append("assessment")
        if not self.plan.strip():
            missing_sections.append("plan")
        return missing_sections

# ✅ CORRECT: Healthcare protocol definitions
class HealthcareProcessor(Protocol):
    """Protocol for healthcare data processors."""

    def process_patient_data(self, data: PatientData) -> Dict[str, any]: ...
    def validate_compliance(self, data: Dict[str, any]) -> bool: ...
    def generate_audit_log(self, action: str, data_hash: str) -> None: ...

T = TypeVar('T', bound=HealthcareProcessor)

class HealthcareService(Generic[T]):
    """Generic healthcare service with type safety."""

    def __init__(self, processor: T) -> None:
        self.processor = processor
        self.audit_logs: List[Dict[str, str]] = []

    def process_with_audit(self, data: PatientData) -> Dict[str, any]:
        """Process data with automatic audit logging."""
        data_hash = hashlib.sha256(str(data).encode()).hexdigest()[:8]

        try:
            result = self.processor.process_patient_data(data)
            self.processor.generate_audit_log("process_success", data_hash)
            return result
        except Exception as e:
            self.processor.generate_audit_log("process_error", data_hash)
            raise
```

### Ruff-Optimized Healthcare Code

```python
# ✅ CORRECT: Ruff-compliant healthcare code patterns
from __future__ import annotations  # Enable future annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Awaitable, Callable

# Modern Python patterns with Ruff optimization
logger = logging.getLogger(__name__)

class HealthcareDataProcessor:
    """Modern Python healthcare processor with Ruff compliance."""

    def __init__(self, config: Dict[str, any]) -> None:
        self.config = config
        self.encryption_key: bytes = self._load_encryption_key()
        self.audit_log_path: Path = Path(config["audit_log_path"])

    async def process_patient_batch(
        self,
        patients: List[PatientData],
        max_workers: int = 4
    ) -> List[Dict[str, any]]:
        """Process patient batch with async concurrency."""

        # Use async context manager for resource cleanup
        async with self._get_processing_context() as context:
            # Process with limited concurrency for healthcare compliance
            semaphore = asyncio.Semaphore(max_workers)

            async def process_single(patient: PatientData) -> Dict[str, any]:
                async with semaphore:
                    return await self._process_patient_async(patient, context)

            # Use asyncio.gather for concurrent processing
            results = await asyncio.gather(
                *[process_single(patient) for patient in patients],
                return_exceptions=True
            )

            # Handle exceptions with healthcare-specific error handling
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(
                        f"Patient processing failed",
                        extra={
                            "patient_hash": patients[i].anonymize_for_logging()["patient_hash"],
                            "error_type": type(result).__name__
                        }
                    )
                else:
                    processed_results.append(result)

            return processed_results

    @asynccontextmanager
    async def _get_processing_context(self) -> AsyncGenerator[Dict[str, any], None]:
        """Async context manager for healthcare processing resources."""
        context = {
            "session_id": hashlib.sha256(str(datetime.now()).encode()).hexdigest()[:8],
            "start_time": datetime.now()
        }

        try:
            # Initialize healthcare-specific resources
            await self._initialize_compliance_monitoring(context)
            yield context
        finally:
            # Cleanup with audit logging
            await self._cleanup_processing_session(context)

    async def _process_patient_async(
        self,
        patient: PatientData,
        context: Dict[str, any]
    ) -> Dict[str, any]:
        """Async patient processing with PHI protection."""

        # Modern Python error handling with healthcare context
        try:
            # Validate compliance before processing
            if not await self._validate_patient_compliance(patient):
                raise ValueError("Patient data failed compliance validation")

            # Process with encryption for PHI fields
            encrypted_data = await self._encrypt_phi_fields(patient)

            # Apply healthcare business logic
            processed_data = await self._apply_healthcare_logic(encrypted_data)

            # Generate audit trail
            await self._generate_audit_entry(patient, context, "success")

            return processed_data

        except Exception as e:
            await self._generate_audit_entry(patient, context, "error")
            raise HealthcareProcessingError(
                f"Patient processing failed: {type(e).__name__}"
            ) from e
```

### Healthcare-Specific Python Patterns

```python
# ✅ CORRECT: Medical terminology handling
class MedicalTerminologyProcessor:
    """Process medical terminology with Python best practices."""

    def __init__(self) -> None:
        self.icd10_codes: Dict[str, str] = self._load_icd10_codes()
        self.cpt_codes: Dict[str, str] = self._load_cpt_codes()
        self.medical_abbreviations: Dict[str, str] = self._load_abbreviations()

    def standardize_medical_terms(self, text: str) -> str:
        """Standardize medical terminology using modern Python patterns."""

        # Use str.translate for efficient string replacement
        translation_table = str.maketrans(self.medical_abbreviations)
        standardized_text = text.translate(translation_table)

        # Use regex with compiled patterns for performance
        import re

        # ICD-10 code standardization
        icd_pattern = re.compile(r'\b([A-Z]\d{2}(?:\.\d{1,4})?)\b')
        standardized_text = icd_pattern.sub(
            lambda m: self._format_icd_code(m.group(1)),
            standardized_text
        )

        # CPT code standardization
        cpt_pattern = re.compile(r'\b(\d{5})\b')
        standardized_text = cpt_pattern.sub(
            lambda m: self._format_cpt_code(m.group(1)),
            standardized_text
        )

        return standardized_text

    def _format_icd_code(self, code: str) -> str:
        """Format ICD-10 code with validation."""
        # Ensure proper ICD-10 format (administrative validation only)
        if len(code) >= 3 and code[0].isalpha() and code[1:3].isdigit():
            return code.upper()
        return code

    def _format_cpt_code(self, code: str) -> str:
        """Format CPT code with validation."""
        # Ensure 5-digit CPT format (administrative validation only)
        if code.isdigit() and len(code) == 5:
            return code
        return code

# ✅ CORRECT: SOAP note processing with Python patterns
class SOAPNoteProcessor:
    """Process SOAP notes with modern Python techniques."""

    def __init__(self) -> None:
        self.section_patterns = {
            'subjective': re.compile(r'(?:S:|Subjective:)\s*(.*?)(?=(?:O:|Objective:)|$)', re.DOTALL | re.IGNORECASE),
            'objective': re.compile(r'(?:O:|Objective:)\s*(.*?)(?=(?:A:|Assessment:)|$)', re.DOTALL | re.IGNORECASE),
            'assessment': re.compile(r'(?:A:|Assessment:)\s*(.*?)(?=(?:P:|Plan:)|$)', re.DOTALL | re.IGNORECASE),
            'plan': re.compile(r'(?:P:|Plan:)\s*(.*?)$', re.DOTALL | re.IGNORECASE)
        }

    def parse_soap_note(self, note_text: str) -> SOAPNote:
        """Parse SOAP note using Python regex patterns."""

        sections = {}
        for section_name, pattern in self.section_patterns.items():
            match = pattern.search(note_text)
            sections[section_name] = match.group(1).strip() if match else ""

        return SOAPNote(
            subjective=sections.get('subjective', ''),
            objective=sections.get('objective', ''),
            assessment=sections.get('assessment', ''),
            plan=sections.get('plan', ''),
            timestamp=datetime.now(),
            provider_id=""  # To be set by caller
        )

    def format_soap_note(self, soap: SOAPNote) -> str:
        """Format SOAP note with consistent structure."""

        # Use f-strings for modern Python formatting
        formatted_note = f"""
SUBJECTIVE:
{soap.subjective}

OBJECTIVE:
{soap.objective}

ASSESSMENT:
{soap.assessment}

PLAN:
{soap.plan}

Generated: {soap.timestamp.isoformat()}
Provider: {soap.provider_id}
        """.strip()

        return formatted_note
```

### Modern Python Healthcare Error Handling

```python
# ✅ CORRECT: Healthcare-specific exception hierarchy
class HealthcareError(Exception):
    """Base exception for healthcare operations."""

    def __init__(self, message: str, patient_hash: Optional[str] = None, context: Optional[Dict[str, any]] = None) -> None:
        super().__init__(message)
        self.patient_hash = patient_hash
        self.context = context or {}
        self.timestamp = datetime.now()

        # Safe logging without PHI exposure
        logger.error(
            message,
            extra={
                "patient_hash": patient_hash,
                "error_context": {k: v for k, v in self.context.items() if not self._is_phi_field(k)},
                "timestamp": self.timestamp.isoformat()
            }
        )

    def _is_phi_field(self, field_name: str) -> bool:
        """Check if field contains PHI."""
        phi_fields = {"ssn", "phone", "email", "address", "patient_name", "dob"}
        return field_name.lower() in phi_fields

class HealthcareProcessingError(HealthcareError):
    """Error during healthcare data processing."""
    pass

class HealthcareComplianceError(HealthcareError):
    """Error related to healthcare compliance validation."""
    pass

class PHIExposureError(HealthcareError):
    """Critical error when PHI might be exposed."""

    def __init__(self, message: str, phi_type: str, context: Optional[Dict[str, any]] = None) -> None:
        super().__init__(message, context=context)
        self.phi_type = phi_type

        # Immediate escalation for PHI exposure
        logger.critical(
            f"PHI EXPOSURE RISK: {message}",
            extra={
                "phi_type": phi_type,
                "requires_immediate_action": True,
                "escalation_required": True
            }
        )

# ✅ CORRECT: Context managers for healthcare operations
@asynccontextmanager
async def healthcare_transaction(
    patient_id: str,
    operation: str,
    audit_required: bool = True
) -> AsyncGenerator[Dict[str, any], None]:
    """Context manager for healthcare transactions with audit logging."""

    patient_hash = hashlib.sha256(patient_id.encode()).hexdigest()[:8]
    transaction_id = hashlib.sha256(f"{patient_id}{operation}{datetime.now()}".encode()).hexdigest()[:8]

    context = {
        "patient_hash": patient_hash,
        "transaction_id": transaction_id,
        "operation": operation,
        "start_time": datetime.now()
    }

    if audit_required:
        logger.info(
            f"Healthcare transaction started: {operation}",
            extra=context
        )

    try:
        yield context

        # Success audit log
        if audit_required:
            context["end_time"] = datetime.now()
            context["status"] = "success"
            context["duration"] = (context["end_time"] - context["start_time"]).total_seconds()

            logger.info(
                f"Healthcare transaction completed: {operation}",
                extra=context
            )

    except Exception as e:
        # Error audit log
        if audit_required:
            context["end_time"] = datetime.now()
            context["status"] = "error"
            context["error_type"] = type(e).__name__
            context["duration"] = (context["end_time"] - context["start_time"]).total_seconds()

            logger.error(
                f"Healthcare transaction failed: {operation}",
                extra=context
            )

        raise
```

### Performance Optimization for Healthcare

```python
# ✅ CORRECT: Performance patterns for healthcare data
from functools import lru_cache
import multiprocessing as mp
from typing import Iterator

class HealthcareDataOptimizer:
    """Optimize healthcare data processing with Python performance patterns."""

    @lru_cache(maxsize=1000)
    def get_medical_code_info(self, code: str, code_type: str) -> Dict[str, str]:
        """Cache medical code lookups for performance."""
        # Expensive medical code lookup with caching
        if code_type == "icd10":
            return self._lookup_icd10_code(code)
        elif code_type == "cpt":
            return self._lookup_cpt_code(code)
        return {}

    def process_large_patient_dataset(
        self,
        patient_data: List[PatientData],
        chunk_size: int = 100
    ) -> Iterator[List[Dict[str, any]]]:
        """Process large datasets efficiently with chunking."""

        # Use generators for memory efficiency
        for i in range(0, len(patient_data), chunk_size):
            chunk = patient_data[i:i + chunk_size]

            # Process chunk with multiprocessing for CPU-bound tasks
            with mp.Pool(processes=min(4, mp.cpu_count())) as pool:
                results = pool.map(self._process_patient_secure, chunk)

            yield results

    def _process_patient_secure(self, patient: PatientData) -> Dict[str, any]:
        """Process individual patient with security considerations."""

        # Use __slots__ for memory efficiency in data classes
        @dataclass
        class ProcessingResult:
            __slots__ = ['patient_hash', 'processing_time', 'result_data']

            patient_hash: str
            processing_time: float
            result_data: Dict[str, any]

        start_time = time.time()

        # Healthcare processing logic here
        result_data = {
            "demographics_processed": True,
            "medical_history_validated": True,
            "compliance_checked": True
        }

        return ProcessingResult(
            patient_hash=patient.anonymize_for_logging()["patient_hash"],
            processing_time=time.time() - start_time,
            result_data=result_data
        ).__dict__
```

## Modern Python Tools Integration

### Ruff Configuration for Healthcare

```toml
# pyproject.toml - Ruff configuration for healthcare AI
[tool.ruff]
target-version = "py310"
line-length = 100
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # Pyflakes
    "UP",  # pyupgrade
    "B",   # flake8-bugbear
    "SIM", # flake8-simplify
    "I",   # isort
    "N",   # pep8-naming
    "C4",  # flake8-comprehensions
    "PIE", # flake8-pie
    "PT",  # flake8-pytest-style
    "RET", # flake8-return
    "ERA", # eradicate
]

ignore = [
    "E501",  # Line too long (handled by formatter)
    "B904",  # raise-without-from-inside-except (healthcare error handling)
]

[tool.ruff.per-file-ignores]
"tests/*" = ["S101"]  # Allow assert in tests
"scripts/*" = ["T201"]  # Allow print in scripts

[tool.ruff.isort]
known-first-party = ["agents", "core", "config"]
force-single-line = true
```

### MyPy Configuration for Healthcare Types

```ini
# mypy.ini - Type checking for healthcare code
[mypy]
python_version = 3.10
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
disallow_untyped_decorators = True
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
warn_unreachable = True
strict_equality = True

# Healthcare-specific module configurations
[mypy-agents.*]
ignore_missing_imports = True

[mypy-mcps.healthcare.*]
ignore_missing_imports = True
```

### Pre-commit Integration

```yaml
# .pre-commit-config.yaml - Healthcare-specific hooks
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.1
    hooks:
      - id: mypy
        additional_dependencies: [types-requests, types-PyYAML]

  - repo: local
    hooks:
      - id: healthcare-compliance-check
        name: Healthcare Compliance Check
        entry: python3 scripts/healthcare-compliance-check.py
        language: system
        files: \.(py)$
```

## Healthcare Python Development Checklist

### Code Quality Standards

- [ ] **Type Safety**: All functions have return type annotations
- [ ] **Ruff Compliance**: Code passes `ruff check` and `ruff format`
- [ ] **MyPy Validation**: No type errors with strict configuration
- [ ] **PHI Protection**: No PHI in logs or debug output
- [ ] **Medical Safety**: No medical advice or clinical recommendations

### Healthcare-Specific Patterns

- [ ] **SOAP Processing**: Proper SOAP note structure handling
- [ ] **Medical Terminology**: Standardized medical term processing
- [ ] **EHR Integration**: HL7 FHIR compliance where applicable
- [ ] **Audit Logging**: Comprehensive audit trails for all PHI access
- [ ] **Error Handling**: Healthcare-specific exception hierarchy

### Performance & Modern Python

- [ ] **Async Patterns**: Use async/await for I/O-bound healthcare operations
- [ ] **Type Protocols**: Define clear interfaces for healthcare processors
- [ ] **Context Managers**: Use context managers for healthcare transactions
- [ ] **Memory Efficiency**: Use generators and chunking for large datasets
- [ ] **Caching**: Cache expensive medical code lookups appropriately

Remember: Python healthcare development combines modern Python best practices with strict medical compliance and PHI protection requirements.
