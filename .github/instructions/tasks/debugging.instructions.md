# Healthcare AI Debugging Instructions

## Purpose

Specialized debugging guidance for healthcare AI systems with PHI protection and medical compliance requirements.

## Healthcare-Specific Debugging Patterns

### MCP Async Task Management Debugging (CRITICAL)

**PROBLEM PATTERN**: MCP clients creating runaway async tasks causing CPU drain.

**SYMPTOMS TO WATCH FOR**:
- Terminal showing: `Task exception was never retrieved`
- Error pattern: `RuntimeError('Attempted to exit cancel scope in a different task')`
- `BrokenResourceError` in MCP STDIO communication
- Accumulating Task-XX entries with cancel scope violations
- High CPU usage from background async tasks

**ROOT CAUSE**: Async context managers opened but never properly closed.

**DEBUGGING APPROACH**:
```python
# ❌ PROBLEMATIC: Context managers without proper cleanup
async def search_medical_data(query: str):
    # Opens connection but may not close properly
    async with mcp_client:
        results = await mcp_client.search(query)
        return results  # Connection may leak on exception

# ✅ CORRECT: Explicit cleanup to prevent task accumulation
async def search_medical_data(query: str):
    try:
        results = await mcp_client.search(query)
        return results
    except Exception as e:
        logger.exception(f"Search error: {e}")
        return {"error": str(e)}
    finally:
        # CRITICAL: Always cleanup MCP connections
        try:
            if hasattr(mcp_client, 'disconnect'):
                await mcp_client.disconnect()
                logger.debug("MCP client disconnected after search")
        except Exception as cleanup_error:
            logger.warning(f"Error during MCP cleanup: {cleanup_error}")
```

**DETECTION TECHNIQUE**: Monitor terminal selection for async task exceptions:
```python
# Check for runaway task patterns
get_terminal_selection()  # Look for Task-XX exception patterns
```

### Database-Backed Debugging (NEW APPROACH)

**CRITICAL CHANGE**: Use database-backed synthetic data for debugging, not hardcoded PHI.

```python
# ✅ CORRECT: Debug with database-backed synthetic data
from tests.database_test_utils import SyntheticHealthcareData
import hashlib
import traceback
import logging
from datetime import datetime
from typing import Dict, List, Any

def debug_patient_processing(patient_id: str, error: Exception):
    """Debug patient processing with synthetic data only."""
    
    # Connect to synthetic database for debugging
    synthetic_data = SyntheticHealthcareData()
    try:
        # Get synthetic patient data for debugging context
        patients = synthetic_data.get_test_patients(limit=1)
        if patients:
            synthetic_patient = patients[0]
            
            # Log anonymized debug info (no PHI)
            logger.debug(f"Debugging with synthetic patient: {synthetic_patient['patient_id']}")
            logger.debug(f"Error type: {type(error).__name__}")
            
            return {
                "synthetic_patient_id": synthetic_patient['patient_id'],
                "error_type": str(type(error)),
                "synthetic": True,
                "timestamp": datetime.now().isoformat()
            }
        else:
            logger.error("No synthetic patients available for debugging")
            return None
    finally:
        synthetic_data.cleanup()

# ✅ CORRECT: Safe data sampling for debugging
def get_debug_sample(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Get anonymized sample data for debugging."""
    return [
        {k: "[REDACTED]" if is_phi_field(k) else v for k, v in record.items()}
        for record in data[:3]  # Small sample only
    ]
```

### Medical Logic Debugging

```python
# ✅ CORRECT: Validate medical data without interpretation
def debug_soap_note_processing(soap_data: Dict[str, Any]):
    """Debug SOAP note processing with medical data validation."""

    required_sections = ["subjective", "objective", "assessment", "plan"]

    for section in required_sections:
        if section not in soap_data:
            logger.warning(f"Missing SOAP section: {section}")
        elif not soap_data[section].strip():
            logger.warning(f"Empty SOAP section: {section}")

    # Validate structure without interpreting medical content
    if "assessment" in soap_data:
        assessment = soap_data["assessment"]
        if not any(keyword in assessment.lower() for keyword in ["diagnosis", "impression", "findings"]):
            logger.info("Assessment may need clinical review for completeness")
```

### Healthcare Integration Debugging

```python
# ✅ CORRECT: Healthcare system debugging with comprehensive logging
from core.infrastructure.healthcare_logger import setup_healthcare_logging
from core.infrastructure.phi_monitor import PHIMonitor
import logging

def debug_healthcare_agent_issue(agent_name: str, error_context: Dict[str, Any]):
    """Debug healthcare agent issues with comprehensive logging integration."""
    
    # Ensure healthcare logging is initialized
    setup_healthcare_logging()
    logger = logging.getLogger(f'healthcare.debug.{agent_name}')
    
    # Log debug session start
    logger.info(f"Starting debug session for {agent_name}", extra={
        'healthcare_context': {
            'debug_session': True,
            'agent': agent_name,
            'error_context_keys': list(error_context.keys())
        }
    })
    
    # PHI safety check on debug data
    if PHIMonitor.scan_for_phi(error_context):
        PHIMonitor.log_phi_detection(
            context=f"debug_session_{agent_name}",
            data_summary="Debug context contains potential PHI - scrubbing for safety"
        )
        # Scrub PHI before debugging
        scrubbed_context = {k: "[PHI_REDACTED]" if PHIMonitor.scan_for_phi(v) else v 
                          for k, v in error_context.items()}
        logger.info(f"Debug data scrubbed for PHI safety: {agent_name}")
        return scrubbed_context
    
    return error_context

# ✅ CORRECT: Healthcare error debugging with logging integration
def debug_medical_workflow_error(workflow_step: str, error: Exception, context: Dict[str, Any]):
    """Debug medical workflow errors with healthcare compliance logging."""
    
    logger = logging.getLogger('healthcare.debug.workflow')
    
    # Log workflow error with healthcare context
    logger.log(35, f"Medical workflow error in {workflow_step}", extra={
        'healthcare_context': {
            'workflow_step': workflow_step,
            'error_type': type(error).__name__,
            'error_message': str(error)[:200],  # Truncated for safety
            'medical_workflow': True,
            'requires_clinical_review': True
        }
    })
    
    # Additional debugging based on workflow step
    if workflow_step == 'patient_intake':
        logger.info("Debugging patient intake workflow", extra={
            'healthcare_context': {
                'intake_fields_present': list(context.keys()),
                'phi_detected': PHIMonitor.scan_for_phi(context)
            }
        })
    
    return {
        'error_logged': True,
        'healthcare_compliant': True,
        'debug_context': 'available_in_logs'
    }
```

```python
# ✅ CORRECT: Debug EHR integration safely
def debug_ehr_integration(ehr_response: Dict[str, Any], transaction_id: str):
    """Debug EHR integration without exposing patient data."""

    safe_response = {
        "status_code": ehr_response.get("status_code"),
        "transaction_id": transaction_id,
        "response_size": len(str(ehr_response)),
        "has_patient_data": "patient" in ehr_response,
        "timestamp": datetime.utcnow().isoformat()
    }

    logger.debug("EHR Integration Debug", extra=safe_response)

    # Validate response structure
    if "error" in ehr_response:
        logger.error(f"EHR Error: {ehr_response['error']}")

    # Check for required fields without exposing content
    required_fields = ["patient_id", "encounter_id", "timestamp"]
    missing_fields = [f for f in required_fields if f not in ehr_response]
    if missing_fields:
        logger.warning(f"Missing EHR fields: {missing_fields}")
```

## Debugging Workflow

### Step 1: Reproduce Safely

1. Use synthetic test data only
2. Never use production PHI for debugging
3. Sanitize logs before sharing
4. Use anonymized patient references

### Step 2: Isolate Healthcare Components

1. Test medical logic separately from PHI handling
2. Validate SOAP note structure without content interpretation
3. Check compliance patterns independently
4. Test EHR integration with mock data

### Step 3: Validate Medical Compliance

```python
def validate_debugging_compliance():
    """Ensure debugging practices meet healthcare standards."""

    checks = {
        "phi_protection": check_no_phi_in_logs(),
        "audit_logging": check_debug_audit_trail(),
        "data_minimization": check_minimal_data_exposure(),
        "access_controls": check_debug_access_restrictions()
    }

    failed_checks = [check for check, passed in checks.items() if not passed]
    if failed_checks:
        raise ComplianceError(f"Debugging compliance failed: {failed_checks}")
```

## Autonomous MyPy Error Resolution

### Autonomous MyPy Error Resolution

**❌ PROHIBITED: Healthcare Anti-Patterns**
- `# type: ignore` without medical safety justification  
- Removing medical variables to fix "unused" warnings
- Suppressing type checking for convenience

**✅ HEALTHCARE-COMPLIANT: MyPy Resolution Hierarchy**

```python
# 1. Optional import pattern (preferred for healthcare)
from typing import Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    import external_lib
else:
    external_lib: Optional[Any] = None
    try:
        import external_lib
    except ImportError:
        pass

# 2. Implement medical variables (don't remove them)
def process_patient_encounter(data: Dict[str, Any]) -> Dict[str, Any]:
    # ✅ IMPLEMENT medical data, don't remove it
    reason = data.get("reason", "routine care")  
    assessment = data.get("assessment", "stable")
    
    # Use in healthcare workflow
    return {
        "visit_reason": reason,
        "clinical_assessment": assessment
    }
```

### Self-Assessment for Continued Work

```python
def assess_mypy_continuation_capability() -> bool:
    """
    Self-assessment questions for autonomous MyPy fixing:
    - Are there remaining errors that follow patterns I've already solved?
    - Can I add more type annotations without changing logic?
    - Are there import/collection type issues I can systematically resolve?
    - Do I have capacity to continue with more fixes in this session?
    - Do remaining errors require human architectural input?
    
    Returns True only if confident in continued autonomous progress.
    """
    return can_continue_autonomously

# Autonomous workflow pattern with verification
def autonomous_mypy_fixing_session():
    """
    CRITICAL: Always verify completion claims with fresh MyPy scan.
    Never trust incremental cache for "0 errors" claims.
    """
    while True:
        # Work on errors
        fix_systematic_mypy_errors()
        
        # MANDATORY: Verify with fresh scan (prevents infinite loops)
        actual_errors = run_fresh_mypy_scan()
        
        if actual_errors == 0:
            break  # True completion verified
        elif can_continue_autonomously(actual_errors):
            continue  # More work possible
        else:
            create_continuation_issue(actual_errors)
            break  # Hand off remaining work
```
    """
    Healthcare-focused self-assessment for autonomous MyPy fixing.
    Returns True if agent should continue, False if architectural input needed.
    """
    remaining_patterns = analyze_remaining_errors()
    
    # ✅ Continue if patterns can be resolved with healthcare-safe methods
    can_continue = (
        has_missing_return_annotations(remaining_patterns) or
        has_untyped_variables(remaining_patterns) or  
        has_import_errors_resolvable_with_type_checking(remaining_patterns) or
        has_medical_variables_needing_implementation(remaining_patterns)
    )
    
    # ❌ Stop if requires architectural decisions
    needs_architecture = (
        has_complex_inheritance_issues(remaining_patterns) or
        requires_external_library_integration_decisions(remaining_patterns) or
        needs_medical_workflow_redesign(remaining_patterns)
    )
    
    return can_continue and not needs_architecture
    """Determine if coding agent should continue MyPy error fixing."""
    
    # Run MyPy and analyze remaining errors
    result = subprocess.run(['mypy', '.'], capture_output=True, text=True)
    errors = result.stderr.split('\n')
    
    # Categorize remaining errors
    systematic_errors = 0
    complex_errors = 0
    
    for error in errors:
        if any(pattern in error for pattern in [
            'missing return type annotation',
            'need type annotation for',
            'has no attribute',
            'import untyped',
        ]):
            systematic_errors += 1
        elif any(pattern in error for pattern in [
            'incompatible types in assignment',
            'incompatible return value type', 
            'type is not subscriptable',
        ]):
            complex_errors += 1
    
    # Decision logic
    if systematic_errors > 10:
        print(f"✅ Continue: {systematic_errors} systematic errors remain")
        return True
    elif systematic_errors > 0 and complex_errors < 5:
        print(f"✅ Continue: {systematic_errors} systematic, {complex_errors} complex")
        return True
    else:
        print(f"🛑 Stop: Only {complex_errors} complex errors remain")
        return False

# Autonomous workflow pattern
def autonomous_mypy_fixing_session():
    """Execute autonomous MyPy fixing until completion or stuck."""
    
    max_iterations = 10
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        print(f"\n🔄 MyPy Fixing Iteration {iteration}")
        
        # Get current error count
        before_count = get_mypy_error_count()
        print(f"📊 Errors before iteration: {before_count}")
        
        # Fix batch of errors
        fix_systematic_mypy_errors(batch_size=25)
        
        # Check progress
        after_count = get_mypy_error_count()
        print(f"📊 Errors after iteration: {after_count}")
        
        # Assess continuation
        if after_count == 0:
            print("🎉 All MyPy errors resolved!")
            break
        elif after_count >= before_count:
            print("⚠️ No progress made - analyzing remaining errors")
            if not assess_mypy_continuation_capability():
                print("🛑 Stopping: Remaining errors require human input")
                break
        else:
            progress = before_count - after_count
            print(f"✅ Progress: {progress} errors fixed, continuing...")
```

### Progress Tracking and Continuation

```python
def create_continuation_issue_if_needed():
    """Create GitHub issue for continuation if work remains."""
    
    remaining_errors = get_mypy_error_count()
    
    if remaining_errors > 0:
        # Check if errors are systematic or complex
        if assess_mypy_continuation_capability():
            issue_body = f"""
## Autonomous MyPy Error Fixing - Continuation Required

**Remaining Errors**: {remaining_errors}

The coding agent has made progress but stopped before completion. 
Remaining errors appear to be systematic and can be resolved autonomously.

**Next Steps**:
1. Continue systematic type annotation fixes
2. Focus on missing return types and variable annotations
3. Address import/collection type issues

@github-copilot Please continue MyPy error resolution from where previous session left off.
"""
            
            # Create issue for automatic continuation
            create_github_issue(
                title="Continue MyPy Error Resolution - Autonomous Session",
                body=issue_body,
                labels=["mypy", "autonomous", "type-safety", "continue"]
            )
```

## Common Healthcare AI Debug Scenarios

### SOAP Note Processing Issues

```python
def debug_soap_processing(soap_note: str, expected_sections: List[str]):
    """Debug SOAP note processing issues."""

    # Parse sections safely
    sections = extract_soap_sections(soap_note)

    # Validate without medical interpretation
    debug_info = {
        "total_length": len(soap_note),
        "sections_found": list(sections.keys()),
        "sections_expected": expected_sections,
        "missing_sections": [s for s in expected_sections if s not in sections],
        "empty_sections": [s for s, content in sections.items() if not content.strip()]
    }

    logger.debug("SOAP Processing Debug", extra=debug_info)
    return debug_info
```

### Agent Communication Debugging

```python
def debug_agent_communication(agent_name: str, message: Dict[str, Any]):
    """Debug inter-agent communication safely."""

    safe_message = {
        "agent": agent_name,
        "message_type": message.get("type"),
        "message_size": len(str(message)),
        "has_patient_context": "patient_id" in message,
        "timestamp": message.get("timestamp")
    }

    # Log communication patterns without exposing content
    logger.debug("Agent Communication", extra=safe_message)

    # Validate message structure
    if "type" not in message:
        logger.error(f"Agent {agent_name} sent message without type")

    if "patient_id" in message and not is_valid_patient_id(message["patient_id"]):
        logger.error(f"Agent {agent_name} sent invalid patient_id format")
```

## Error Handling Patterns

### Healthcare-Safe Exception Handling

```python
class HealthcareSafeException(Exception):
    """Exception that safely logs healthcare errors without PHI exposure."""

    def __init__(self, message: str, patient_hash: str = None, context: Dict[str, Any] = None):
        super().__init__(message)
        self.patient_hash = patient_hash
        self.context = context or {}

        # Log safely
        logger.error(
            message,
            extra={
                "patient_hash": patient_hash,
                "context": {k: v for k, v in self.context.items() if not is_phi_field(k)}
            }
        )

# Usage
try:
    process_patient_data(patient_data)
except ValidationError as e:
    raise HealthcareSafeException(
        "Patient data validation failed",
        patient_hash=hash_patient_id(patient_data["id"]),
        context={"validation_errors": e.errors}
    )
```

### Compliance-Aware Debugging Tools

```python
def safe_debug_print(data: Any, context: str = ""):
    """Print debug information with PHI protection."""

    if isinstance(data, dict):
        safe_data = {
            k: "[PHI_REDACTED]" if is_phi_field(k) else v
            for k, v in data.items()
        }
    elif isinstance(data, str) and contains_phi_patterns(data):
        safe_data = "[PHI_CONTENT_REDACTED]"
    else:
        safe_data = data

    print(f"DEBUG {context}: {safe_data}")

def debug_trace_healthcare_function(func):
    """Decorator for tracing healthcare functions safely."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Log function entry without PHI
        safe_args = [str(type(arg)) for arg in args]
        safe_kwargs = {k: type(v) for k, v in kwargs.items()}

        logger.debug(f"Entering {func.__name__}", extra={
            "args_types": safe_args,
            "kwargs_types": safe_kwargs
        })

        try:
            result = func(*args, **kwargs)
            logger.debug(f"Exiting {func.__name__} successfully")
            return result
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {type(e).__name__}")
            raise

    return wrapper
```

## Debugging Checklist

### Before Starting Debug Session

- [ ] Verify using synthetic data only
- [ ] Enable audit logging for debug session
- [ ] Set up PHI-safe logging configuration
- [ ] Prepare anonymized test cases

### During Debugging

- [ ] Check for PHI exposure in logs/console
- [ ] Validate medical logic without interpretation
- [ ] Test compliance patterns independently
- [ ] Use modern development tools (Ruff, MyPy)

### After Debugging

- [ ] Clear any temporary debug data
- [ ] Review logs for accidental PHI exposure
- [ ] Document debugging insights safely
- [ ] Update test cases based on findings

Remember: Healthcare debugging requires balancing technical insight with strict PHI protection and medical compliance standards.
