# Healthcare AI Refactoring Instructions

**WORKFLOW CONTROL**: All workflows are controlled by `copilot-instructions.md`. This file provides implementation patterns only.

## Purpose

Specialized refactoring guidance for healthcare AI systems emphasizing medical compliance preservation, PHI protection during code changes, and modern Python pattern adoption.

## Healthcare-Safe Refactoring Framework

### PHI-Safe Refactoring Patterns

```python
# ✅ CORRECT: Healthcare-safe refactoring approach
from typing import Dict, List, Any, Callable, TypeVar, Protocol
from dataclasses import dataclass
import hashlib
import logging

T = TypeVar('T')

class RefactoringSafetyValidator:
    """Validate refactoring changes maintain healthcare compliance."""

    def __init__(self) -> None:
        self.phi_patterns = [
            r'\d{3}-\d{2}-\d{4}',  # SSN
            r'\(\d{3}\)\s*\d{3}-\d{4}',  # Phone
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'  # Email
        ]
        self.medical_safety_keywords = [
            "diagnosis", "treatment", "medication", "dosage", "recommend"
        ]

    def validate_refactoring_safety(
        self,
        original_code: str,
        refactored_code: str
    ) -> Dict[str, Any]:
        """Validate refactoring maintains healthcare safety standards."""

        safety_report = {
            "phi_exposure_check": self._check_phi_exposure(original_code, refactored_code),
            "medical_safety_check": self._check_medical_safety_preservation(original_code, refactored_code),
            "compliance_preservation": self._check_compliance_preservation(original_code, refactored_code),
            "audit_trail_integrity": self._check_audit_trail_integrity(original_code, refactored_code),
            "safe_to_proceed": True
        }

        # Determine overall safety
        safety_report["safe_to_proceed"] = all([
            safety_report["phi_exposure_check"]["safe"],
            safety_report["medical_safety_check"]["safe"],
            safety_report["compliance_preservation"]["safe"],
            safety_report["audit_trail_integrity"]["safe"]
        ])

        return safety_report

    def _check_phi_exposure(self, original: str, refactored: str) -> Dict[str, Any]:
        """Check if refactoring introduces PHI exposure risks."""

        original_phi_count = sum(
            len(re.findall(pattern, original)) for pattern in self.phi_patterns
        )
        refactored_phi_count = sum(
            len(re.findall(pattern, refactored)) for pattern in self.phi_patterns
        )

        return {
            "safe": refactored_phi_count <= original_phi_count,
            "original_phi_patterns": original_phi_count,
            "refactored_phi_patterns": refactored_phi_count,
            "risk_level": "HIGH" if refactored_phi_count > original_phi_count else "LOW"
        }

    def _check_medical_safety_preservation(self, original: str, refactored: str) -> Dict[str, Any]:
        """Ensure refactoring doesn't introduce medical advice."""

        original_safety_violations = sum(
            1 for keyword in self.medical_safety_keywords if keyword in original.lower()
        )
        refactored_safety_violations = sum(
            1 for keyword in self.medical_safety_keywords if keyword in refactored.lower()
        )

        # Check for new medical advice patterns
        medical_advice_patterns = [
            "patient should", "recommend taking", "diagnosis is", "treatment plan"
        ]

        new_advice_patterns = sum(
            1 for pattern in medical_advice_patterns
            if pattern in refactored.lower() and pattern not in original.lower()
        )

        return {
            "safe": new_advice_patterns == 0,
            "new_medical_advice_patterns": new_advice_patterns,
            "requires_medical_review": new_advice_patterns > 0 or refactored_safety_violations > original_safety_violations
        }

### Modern Healthcare Refactoring Patterns (Based on PR #31 Lessons)

```python
# ✅ CRITICAL: Code formatting and line length patterns (From PR review feedback)
class ModernRefactoringStandards:
    """Modern refactoring patterns from real production issues."""
    
    @staticmethod
    def refactor_long_lines(code: str, max_length: int = 120) -> str:
        """Break extremely long lines identified in PR reviews."""
        
        # Pattern from PR #31: Long synthetic data generation lines  
        # Before: synthetic_ssn = f"{SyntheticDataConstants.SYNTHETIC_SSN_PREFIX}-{random.randint(SyntheticDataConstants.SSN_GROUP_MIN, SyntheticDataConstants.SSN_GROUP_MAX)}-{random.randint(SyntheticDataConstants.SSN_SERIAL_MIN, SyntheticDataConstants.SSN_SERIAL_MAX)}"
        # After: Extract variables for readability
        long_line_patterns = [
            {
                'pattern': r'(\w+)\s*=\s*f".*{.*}.*{.*}.*{.*}"',
                'refactor': 'Extract intermediate variables for f-string components'
            },
            {
                'pattern': r'synthetic_ssn\s*=.*{.*}.*{.*}.*{.*}',
                'refactor': 'Break SSN generation into multiple variables'
            }
        ]
        
        return code  # Implementation would apply refactoring patterns
    
    @staticmethod
    def eliminate_method_duplication(file_paths: List[str]) -> Dict[str, List[str]]:
        """Identify and eliminate method duplication across healthcare modules."""
        
        # Methods identified as duplicated in PR #31 reviews
        commonly_duplicated = [
            "_ensure_decimal",  # Found in billing_agent.py and insurance_calculations.py
            "_get_negotiated_rate",  # Found in multiple billing modules
            "_get_patient_coverage_data"  # Found in multiple insurance modules
        ]
        
        duplication_report = {}
        for method in commonly_duplicated:
            duplication_report[method] = []
            # Would scan files for duplicate implementations
        
        return duplication_report
    
    @staticmethod  
    def consolidate_imports(code: str) -> str:
        """Remove duplicate imports identified in PR reviews."""
        
        lines = code.split('\n')
        import_lines = []
        other_lines = []
        seen_imports = set()
        
        for line in lines:
            if line.strip().startswith(('import ', 'from ')):
                if line.strip() not in seen_imports:
                    import_lines.append(line)
                    seen_imports.add(line.strip())
                # Skip duplicate imports
            else:
                other_lines.append(line)
        
        # Combine unique imports with rest of code
        return '\n'.join(import_lines + [''] + other_lines)

# ✅ CRITICAL: Healthcare financial calculation refactoring (From PR review feedback)
class HealthcareFinancialRefactoring:
    """Financial calculation refactoring patterns from production issues."""
    
    @staticmethod
    def add_division_by_zero_protection(code: str) -> str:
        """Add zero protection to financial calculations."""
        
        # Pattern from PR #31: Division by zero in deductible calculations
        division_patterns = [
            r'(\w+)\s*/\s*(\w+\.annual_deductible)',
            r'(\w+)\s*/\s*(\w+\.deductible)'
        ]
        
        # Would add protection like:
        # if patient_coverage.annual_deductible == 0: percentage_met = 1.0
        # else: percentage_met = float(patient_coverage.deductible_met / patient_coverage.annual_deductible)
        
        return code
    
    @staticmethod
    def ensure_decimal_type_safety(code: str) -> str:
        """Convert financial calculations to use Decimal consistently."""
        
        # Pattern from PR #31: Decimal vs float type mismatches
        float_to_decimal_patterns = [
            r'float\((.*deductible.*)\)',
            r'float\((.*amount.*)\)',
            r'(billed_amount.*=.*\d+\.\d+)',  # Raw float literals
        ]
        
        # Would convert to: self._ensure_decimal(value)
        
        return code

# ✅ CORRECT: Healthcare-specific refactoring patterns
class HealthcareRefactoringPatterns:
    """Common refactoring patterns for healthcare code."""

    @staticmethod
    def extract_phi_handling_method(
        original_function: Callable[..., T],
        phi_fields: List[str]
    ) -> Tuple[Callable[..., T], Callable[[Dict[str, Any]], Dict[str, Any]]]:
        """Extract PHI handling into separate, testable method."""

        def sanitized_function(*args, **kwargs) -> T:
            # Remove PHI handling from original function
            # Call original with sanitized data
            sanitized_kwargs = {
                k: v for k, v in kwargs.items()
                if k not in phi_fields
            }
            return original_function(*args, **sanitized_kwargs)

        def phi_handler(data: Dict[str, Any]) -> Dict[str, Any]:
            """Handle PHI data separately with proper protection."""
            phi_data = {
                field: data.get(field) for field in phi_fields if field in data
            }

            # Apply encryption/anonymization as needed
            protected_phi = {
                field: hashlib.sha256(str(value).encode()).hexdigest()[:8]
                for field, value in phi_data.items()
            }

            return protected_phi

        return sanitized_function, phi_handler

    @staticmethod
    def extract_medical_validation_logic(
        business_logic: Callable[..., T]
    ) -> Tuple[Callable[..., T], Callable[[Dict[str, Any]], List[str]]]:
        """Extract medical validation into separate method."""

        def core_business_logic(*args, **kwargs) -> T:
            # Core business logic without medical validation
            return business_logic(*args, **kwargs)

        def medical_validator(medical_data: Dict[str, Any]) -> List[str]:
            """Validate medical data format (administrative only)."""
            validation_errors = []

            # SOAP note structure validation
            if "soap_note" in medical_data:
                required_sections = ["subjective", "objective", "assessment", "plan"]
                soap_data = medical_data["soap_note"]

                for section in required_sections:
                    if section not in soap_data or not soap_data[section].strip():
                        validation_errors.append(f"Missing or empty SOAP section: {section}")

            # Medical coding validation
            if "icd_codes" in medical_data:
                for code in medical_data["icd_codes"]:
                    if not re.match(r'^[A-Z]\d{2}(\.\d{1,4})?$', code):
                        validation_errors.append(f"Invalid ICD-10 format: {code}")

            return validation_errors

        return core_business_logic, medical_validator
```

### Modern Python Refactoring for Healthcare

```python
# ✅ CORRECT: Modernize healthcare code with Ruff and type safety
class HealthcareCodeModernizer:
    """Modernize healthcare code with current Python best practices."""

    def refactor_to_modern_python(self, legacy_code: str) -> str:
        """Refactor legacy healthcare code to modern Python patterns."""

        refactoring_steps = [
            self._add_future_annotations,
            self._modernize_type_hints,
            self._convert_to_dataclasses,
            self._add_async_patterns,
            self._improve_error_handling,
            self._optimize_for_ruff_compliance
        ]

        modernized_code = legacy_code
        for step in refactoring_steps:
            modernized_code = step(modernized_code)

        return modernized_code

    def _add_future_annotations(self, code: str) -> str:
        """Add future annotations for better type hinting."""
        if "from __future__ import annotations" not in code:
            imports_section = "from __future__ import annotations\n\n"
            return imports_section + code
        return code

    def _modernize_type_hints(self, code: str) -> str:
        """Convert to modern type hint patterns."""
        # Convert Dict to dict, List to list for Python 3.9+
        modernized = code
        modernized = re.sub(r'\bDict\[([^]]+)\]', r'dict[\1]', modernized)
        modernized = re.sub(r'\bList\[([^]]+)\]', r'list[\1]', modernized)
        modernized = re.sub(r'\bOptional\[([^]]+)\]', r'\1 | None', modernized)
        return modernized

    def _convert_to_dataclasses(self, code: str) -> str:
        """Convert simple classes to dataclasses for healthcare data."""
        # Pattern to detect simple data classes
        class_pattern = r'class\s+(\w+):\s*\n(\s+def\s+__init__.*?\n(?:\s+self\.\w+\s*=.*?\n)*)'

        def convert_to_dataclass(match):
            class_name = match.group(1)
            init_method = match.group(2)

            # Extract field assignments
            field_pattern = r'\s+self\.(\w+)\s*=\s*(\w+)'
            fields = re.findall(field_pattern, init_method)

            if fields and "Patient" in class_name or "Medical" in class_name:
                # Convert to dataclass for healthcare data structures
                dataclass_fields = []
                for field_name, param_name in fields:
                    # Add type hints for healthcare fields
                    if field_name in ["patient_id", "encounter_id"]:
                        dataclass_fields.append(f"    {field_name}: str")
                    elif field_name in ["timestamp", "created_at"]:
                        dataclass_fields.append(f"    {field_name}: datetime")
                    else:
                        dataclass_fields.append(f"    {field_name}: Any")

                return f"@dataclass\nclass {class_name}:\n" + "\n".join(dataclass_fields)

            return match.group(0)  # Return original if not healthcare data

        return re.sub(class_pattern, convert_to_dataclass, code, flags=re.MULTILINE | re.DOTALL)

    def _add_async_patterns(self, code: str) -> str:
        """Add async patterns for I/O-bound healthcare operations."""
        # Convert database operations to async
        async_patterns = {
            r'def\s+(.*database.*|.*ehr.*|.*external.*)\(': r'async def \1(',
            r'(\w+\.query\(.*?\))': r'await \1',
            r'(\w+\.save\(.*?\))': r'await \1',
            r'(\w+\.create\(.*?\))': r'await \1'
        }

        modernized = code
        for pattern, replacement in async_patterns.items():
            modernized = re.sub(pattern, replacement, modernized)

        return modernized
```

### Healthcare Domain Refactoring Patterns

```python
# ✅ CORRECT: Domain-specific refactoring for healthcare
class HealthcareDomainRefactoring:
    """Refactoring patterns specific to healthcare domain logic."""

    def refactor_soap_note_processing(self, legacy_soap_code: str) -> str:
        """Refactor SOAP note processing to modern patterns."""

        # Extract SOAP processing into structured approach
        refactored_pattern = '''
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime

@dataclass
class SOAPNote:
    """Modern SOAP note structure with type safety."""
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

    def format_for_ehr(self) -> Dict[str, str]:
        """Format SOAP note for EHR integration."""
        return {
            "S": self.subjective,
            "O": self.objective,
            "A": self.assessment,
            "P": self.plan,
            "timestamp": self.timestamp.isoformat(),
            "provider": self.provider_id
        }

class SOAPNoteProcessor:
    """Process SOAP notes with modern Python patterns."""

    def __init__(self) -> None:
        self.validation_rules = self._load_validation_rules()

    async def process_soap_note(self, raw_note: str, provider_id: str) -> SOAPNote:
        """Process raw SOAP note with comprehensive validation."""

        # Parse sections using modern regex patterns
        sections = await self._parse_soap_sections(raw_note)

        # Create structured note
        soap_note = SOAPNote(
            subjective=sections.get("subjective", ""),
            objective=sections.get("objective", ""),
            assessment=sections.get("assessment", ""),
            plan=sections.get("plan", ""),
            timestamp=datetime.now(),
            provider_id=provider_id
        )

        # Validate completeness
        validation_errors = soap_note.validate_completeness()
        if validation_errors:
            raise ValueError(f"Incomplete SOAP note: {validation_errors}")

        return soap_note
        '''

        return refactored_pattern

    def refactor_patient_data_handling(self, legacy_patient_code: str) -> str:
        """Refactor patient data handling with PHI protection."""

        refactored_pattern = '''
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import hashlib
from datetime import date

@dataclass
class PatientData:
    """PHI-protected patient data structure."""
    patient_id: str
    demographics: Dict[str, Any] = field(default_factory=dict)
    medical_history: list[str] = field(default_factory=list)
    current_medications: list[Dict[str, str]] = field(default_factory=list)

    def anonymize_for_logging(self) -> Dict[str, Any]:
        """Generate anonymized version safe for logging."""
        return {
            "patient_hash": hashlib.sha256(self.patient_id.encode()).hexdigest()[:8],
            "demographics_count": len(self.demographics),
            "medication_count": len(self.current_medications),
            "history_entries": len(self.medical_history)
        }

    def extract_phi_fields(self) -> Dict[str, Any]:
        """Extract PHI fields for separate handling."""
        phi_fields = {
            "ssn": self.demographics.get("ssn"),
            "phone": self.demographics.get("phone"),
            "email": self.demographics.get("email"),
            "address": self.demographics.get("address")
        }
        return {k: v for k, v in phi_fields.items() if v is not None}

    def get_safe_demographics(self) -> Dict[str, Any]:
        """Get demographics with PHI removed."""
        phi_fields = {"ssn", "phone", "email", "address", "full_name"}
        return {
            k: v for k, v in self.demographics.items()
            if k not in phi_fields
        }

class PatientDataProcessor:
    """Process patient data with modern patterns and PHI protection."""

    def __init__(self) -> None:
        self.phi_protector = PHIProtectionService()
        self.audit_logger = AuditLogger()

    async def process_patient_data(
        self,
        patient_data: PatientData,
        processing_purpose: str
    ) -> Dict[str, Any]:
        """Process patient data with comprehensive protection."""

        # Log access for audit trail
        await self.audit_logger.log_patient_access(
            patient_hash=patient_data.anonymize_for_logging()["patient_hash"],
            purpose=processing_purpose,
            user_id=self._get_current_user_id()
        )

        # Apply data minimization
        minimized_data = self._apply_data_minimization(patient_data, processing_purpose)

        # Process with protection
        result = await self._process_minimized_data(minimized_data)

        return result
        '''

        return refactored_pattern
```

### Refactoring Safety Checklist

```python
# ✅ CORRECT: Healthcare refactoring safety validation
class RefactoringSafetyChecklist:
    """Comprehensive safety checklist for healthcare code refactoring."""

    def validate_refactoring_safety(self, refactoring_context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate refactoring meets healthcare safety standards."""

        safety_checks = {
            "phi_protection": self._check_phi_protection_preserved(refactoring_context),
            "medical_safety": self._check_medical_safety_maintained(refactoring_context),
            "audit_integrity": self._check_audit_trail_preserved(refactoring_context),
            "compliance_standards": self._check_compliance_maintained(refactoring_context),
            "error_handling": self._check_error_handling_improved(refactoring_context),
            "type_safety": self._check_type_safety_enhanced(refactoring_context)
        }

        overall_safety = all(check["safe"] for check in safety_checks.values())

        return {
            "overall_safe": overall_safety,
            "safety_checks": safety_checks,
            "recommendations": self._generate_safety_recommendations(safety_checks),
            "required_reviews": self._identify_required_reviews(safety_checks)
        }

    def _check_phi_protection_preserved(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Check that PHI protection is maintained or improved."""
        return {
            "safe": True,  # Implementation details
            "details": "PHI protection patterns maintained",
            "improvements": ["Enhanced encryption patterns", "Better access logging"]
        }

    def _check_medical_safety_maintained(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Check that medical safety principles are maintained."""
        return {
            "safe": True,  # Implementation details
            "details": "No medical advice patterns introduced",
            "medical_review_required": False
        }
```

### Modern Tool Integration for Refactoring

```python
# ✅ CORRECT: Integrate modern tools in refactoring workflow
class ModernRefactoringWorkflow:
    """Integrate modern development tools into healthcare refactoring."""

    def setup_ruff_refactoring_workflow(self) -> Dict[str, str]:
        """Set up Ruff for ultra-fast refactoring feedback."""

        return {
            "format_command": "ruff format --check --diff",
            "lint_command": "ruff check --fix --select=ALL",
            "import_sorting": "ruff check --select=I --fix",
            "modernization": "ruff check --select=UP --fix",
            "performance": "ruff check --select=PERF --fix"
        }

    def setup_mypy_validation(self) -> Dict[str, str]:
        """Set up MyPy for type safety validation during refactoring."""

        return {
            "strict_mode": "mypy --strict",
            "healthcare_config": "mypy --config-file=mypy-healthcare.ini",
            "incremental_check": "mypy --incremental",
            "error_summary": "mypy --error-summary"
        }

    def setup_pre_commit_validation(self) -> List[str]:
        """Set up pre-commit hooks for refactoring validation."""

        return [
            "ruff-check",
            "ruff-format",
            "mypy",
            "healthcare-compliance-check",
            "phi-exposure-scan",
            "medical-safety-validation"
        ]
```

## Healthcare Refactoring Best Practices

### Refactoring Workflow

1. **Pre-Refactoring Safety Check**
   - Identify PHI handling code
   - Document medical safety requirements
   - Plan compliance preservation strategy
   - Set up comprehensive testing

2. **Incremental Refactoring**
   - Small, focused changes
   - Maintain functionality at each step
   - Validate healthcare compliance continuously
   - Test with synthetic data only

3. **Post-Refactoring Validation**
   - Run comprehensive test suite
   - Validate PHI protection maintained
   - Check medical safety compliance
   - Review audit logging integrity

### Modern Python Integration

- **Ruff Usage**: `ruff check --fix` for ultra-fast refactoring validation
- **Type Safety**: Add comprehensive type hints with MyPy validation
- **Async Patterns**: Convert I/O-bound operations to async/await
- **Dataclass Conversion**: Use dataclasses for healthcare data structures
- **Error Handling**: Implement healthcare-specific exception hierarchy

### Healthcare-Specific Considerations

- **PHI Protection**: Ensure refactoring doesn't expose PHI
- **Medical Safety**: Maintain strict separation between administrative and clinical functions
- **Audit Integrity**: Preserve audit logging throughout refactoring
- **Compliance Preservation**: Maintain HIPAA and regulatory compliance
- **Performance**: Optimize for healthcare-specific performance requirements

Remember: Healthcare refactoring requires balancing code improvement with strict preservation of medical safety, PHI protection, and regulatory compliance throughout the process.
