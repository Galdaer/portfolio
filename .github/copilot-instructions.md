# Copilot Instructions for Intelluxe AI Healthcare System

Use The Sequential Thinking MCP Server to think through your tasks.

## Project Overview

**Intelluxe AI** - Privacy-First Healthcare AI System built for on-premise clinical deployment. Currently in active development, focusing on core infrastructure and test suite hardening.

### Core Architecture

- **Modular healthcare AI platform** with universal service orchestration
- **Focus**: Administrative/documentation support, NOT medical advice
- **Privacy-First**: All PHI/PII remains on-premise with no cloud dependencies
- **Development Status**: Build robust, maintainable features for future clinical environments

### Directory Structure

```
reference/ai-patterns/  # MIT licensed AI engineering patterns (git submodule)
mcps/healthcare/        # Healthcare MCP server code (copied from agentcare-mcp)
services/user/          # Service configurations - each service has SERVICE.conf
agents/                 # AI agent implementations (intake/, document_processor/, etc.)
core/                   # Core healthcare AI infrastructure (memory/, orchestration/, etc.)
scripts/                # Primary shell scripts (universal-service-runner.sh, lib.sh, etc.)
```

## Synthetic Healthcare Data Infrastructure

### Comprehensive Data Generation

**Located at**: `scripts/generate_synthetic_healthcare_data.py`

**Current Dataset**: 22,255+ records across 9 data types (12.9MB)

- 75 doctors, 2,500 patients, 6,000 encounters
- 5,016 lab results, 4,839 billing claims, 1,544 audit logs
- Cross-referenced and compliance-ready for local deployment

### Phase-Aligned Data Types

**Phase 1 Core Data (AI Infrastructure):**

- **Doctors** - Healthcare providers with specialties, credentials, NPI numbers
- **Patients** - Demographics, insurance, contact info (no real PHI)
- **Encounters** - Medical visits with SOAP notes, assessments, plans
- **Lab Results** - Laboratory tests with realistic values and reference ranges
- **Insurance Verifications** - Coverage validation for workflow testing
- **Agent Sessions** - AI interaction logs for Ollama/Healthcare-MCP integration

**Phase 2 Business Data (Local Automation):**

- **Billing Claims** - CPT/ICD codes, amounts, claim statuses for billing automation
- **Doctor Preferences** - Workflow settings, documentation styles for LoRA personalization
- **Audit Logs** - HIPAA compliance tracking, user actions, system events

### Data Generation Commands

```bash
# Generate comprehensive dataset (recommended for development)
python3 scripts/generate_synthetic_healthcare_data.py --doctors 75 --patients 2500 --encounters 6000

# Generate smaller test dataset
python3 scripts/generate_synthetic_healthcare_data.py --doctors 10 --patients 100 --encounters 200

# Include database population (requires running PostgreSQL/Redis)
python3 scripts/generate_synthetic_healthcare_data.py --use-database
```

### Data Reuse Strategy

- **DO NOT regenerate** unless adding new data types
- **Existing dataset supports** all Phase 1-2 testing without regeneration
- **Cross-referenced integrity** - all foreign keys properly linked
- **Future-proof design** - extensible for Phase 3 without breaking existing workflows

## Healthcare Security & Compliance

### Critical Security Rules

- **Generic Error Messages**: Never expose JWT_SECRET, MASTER_ENCRYPTION_KEY, or config details
- **Environment-Aware Placeholders**: Block production deployment when incomplete, allow configurable development
- **Comprehensive Test Coverage**: Test security fallbacks with logging verification using caplog fixture
- **Security Documentation**: Always explain WHY security choices were made (HIPAA, NANP standards, etc.)

### Medical Safety Principles

- **NO medical advice, diagnosis, or treatment recommendations**
- **Focus ONLY on administrative and documentation support**
- **Explainable AI**: All AI decisions must be traceable and auditable for healthcare compliance
- **All PHI/PII remains on-premise** - no cloud dependencies or external API calls with patient data

### Medical Module Development Patterns

- **Real Implementation Strategy**: Phase 1 requires real implementations, not mocks - replace TODOs with functional code
- **Type Error Priority**: Fix type errors systematically: imports → unused variables → type annotations → method implementations
- **CRITICAL: Preserve Medical Information**: When fixing "unused" variables/methods, investigate their medical purpose and implement them properly. Never remove potentially valuable medical data to satisfy linting - implement it instead
- **Medical Disclaimers**: All medical module implementations must include healthcare compliance disclaimers in method docstrings
- **Context-First**: Always read 50+ lines of file context before making medical module edits

### Medical Data Preservation Protocol

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

## Development Workflow & Code Quality

### Quick Developer Setup

```bash
make install && make deps && make hooks && make validate
```

### Git Hooks (Multi-Language Auto-Formatting)

- **Pre-commit hook**: Auto-formatting + light validation
  - **Python**: `black` + `isort` with automatic re-staging
  - **Shell/Bash**: `shfmt` with 4-space indentation
  - **JSON/YAML/Markdown**: `prettier` formatting
  - **All files**: Trailing whitespace removal + safety checks
- **Pre-push hook**: `make lint && make validate` (tests skipped during development)
- **Installation**: `make hooks` installs git hooks, `make deps` installs formatting tools

### Requirements Management

- **Source of truth**: `requirements.in` contains all package specifications
- **Auto-generation**: `python3 scripts/generate-requirements.py` generates:
  - `requirements.txt` - Full dependencies for development
  - `requirements-ci.txt` - Minimal dependencies for CI (excludes GPU packages, no "via" comments)
- **Development installs ALL dependencies** for complete testing capability
- **Never manually edit** generated requirements files

### Type Safety & Code Quality (Python)

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

### Validation Standards

```bash
# Required validation before any code submission
make lint && make validate && echo "✅ Code quality verified"
```

### Error Prevention Checklist

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

## Testing Standards

### Current Test Status

- **Phase 1 Implementation Testing**: Real implementations should now pass functional tests
- **Bats tests**: Shell script integration testing (source actual scripts)
- **Pre-push validation**: `make lint && make validate` (tests re-enabled for Phase 1)
- **Focus on functional validation** of real implementations over infrastructure setup

### Healthcare Testing Requirements

- **Test with realistic medical scenarios** using synthetic data
- **Compliance testing**: Validate HIPAA compliance and audit logging
- **Use project infrastructure**: `CI=true bash ./scripts/test.sh` or `make test`

### Synthetic Data Testing Strategy

- **Use existing dataset**: 22,255+ records in `data/synthetic/` cover all testing needs
- **Cross-reference validation**: Ensure patient IDs, doctor IDs, encounter IDs link correctly
- **Medical data accuracy**: CPT codes, ICD codes, lab values follow healthcare standards
- **Privacy compliance**: All synthetic data contains no real PHI/PII
- **Test data generation**: Validate `scripts/generate_synthetic_healthcare_data.py` works correctly

## Service Architecture

### Universal Service Pattern

- **Each service**: `services/user/SERVICE/SERVICE.conf`
- **Deployment**: `bootstrap.sh` calls `universal-service-runner.sh`
- **Container Security**: Development uses `justin:intelluxe (1000:1001)`
- **Network Isolation**: All containers on `intelluxe-net` with no external data egress

### Key Healthcare Services

- **Ollama** (local LLM), **Healthcare-MCP** (medical tools), **PostgreSQL** (patient context)
- **Redis** (session cache), **n8n** (workflows), **WhisperLive** (real-time transcription)

## Remote Agent Guidelines

### Autonomous Execution Requirements

- **Work continuously for 2-4 hours** without asking for continuation
- **Start with codebase analysis** (30-45 minutes) before making changes
- **Discover and fix related issues** beyond initial scope
- **Only stop for unrecoverable errors** or 100% completion
- **NEVER waste premium requests**: Always read current file contents before editing, pay attention to user's explicit instructions about infrastructure (self-hosted runners, etc.)

### When to Use Sequential Thinking

- **Complex Implementation Decisions**: Mock vs implement, architecture choices, technical debt tradeoffs
- **Large Codebase Analysis**: Understanding module relationships and dependencies before changes
- **Multi-Step Problem Solving**: Breaking down complex fixes into manageable phases
- **Phase 1 Priority Decisions**: Deciding what real implementations are complete vs what needs finishing for MCP integration

### Required Environment Setup

```bash
export ENVIRONMENT=development CI=true
sudo apt install -y lsof socat wireguard-tools python3-flake8 python3-psycopg2
sudo make install  # Critical: sets up symlinks and systemd units
make lint && make validate  # Verify setup
```

### Systematic Approach

1. **Analysis-First**: `make lint 2>&1 | tee current_errors.txt`
2. **Read actual files** before modifying them
3. **Match existing code style** exactly
4. **Fix incrementally**: One error category at a time
5. **Validate each change**: Test immediately after changes
6. **CI/CD Considerations**: Remember self-hosted runner setup, optimize for cache efficiency vs parallelization balance

### Success Criteria Template

```bash
# Required validation before task completion
make lint && make validate && echo "✅ Ready for submission"
```

### CI/CD Workflow Optimization Principles

- **Self-hosted runner advantages**: Can handle more parallel jobs than GitHub's 2-core limit
- **Cache vs Parallelization**: Balance cache restoration overhead (30-60s per job) against parallel execution benefits
- **Grouped Jobs Strategy**: Consolidate related checks to reduce cache restorations while maintaining meaningful parallelization
- **Phase 0 Development**: Prioritize fast feedback over perfect granularity during active development

## Architectural Decision Principles

### CRITICAL: Always Choose Efficiency Over Simplicity

1. **Performance & Resource Efficiency FIRST**
2. **Healthcare Compliance & Security SECOND**
3. **Maintainability & Debugging THIRD**
4. **Implementation Simplicity LAST**

### CI/CD Efficiency Requirements

- **CRITICAL: Self-Hosted GitHub Actions Runner** - ALL workflow jobs MUST use `runs-on: self-hosted`
- **Use `requirements-ci.txt`** for CI/CD (excludes heavy GPU/ML packages)
- **Shared dependency caching** - never install same dependencies multiple times
- **Strategic job dependencies** with optimal dependency graphs
- **Never modify workflows to skip dependencies** - fix requirements files instead
- **Cache optimization strategy**: Consolidate related jobs to reduce cache restoration overhead
- **Parallelization balance**: Use matrix strategies for CPU-intensive tasks (Python validation), consolidate for I/O-bound tasks (security/infrastructure checks)
- **Self-hosted advantages**: No GitHub concurrency limits, better CPU resources, persistent cache potential

## File Safety & Editing Best Practices

### Before Any Edit

- **ALWAYS read the file section** you're editing BEFORE making changes
- **NEVER break bash syntax** - check if/fi, case/esac, function boundaries
- **Use shellcheck validation** after every bash script edit
- **Remove unused variables** after refactoring

### Common Anti-Patterns to Prevent

1. **Missing Type Annotations** → Add explicit types for ALL variables and functions
2. **Removing Medical Variables** → Implement unused medical variables instead of removing them
3. **Inline Comments in Dictionaries** → Never add inline comments in JSON-like structures (syntax error)
4. **Trailing whitespace** → Auto-stripped by pre-commit hook
5. **Inconsistent blank lines** → Follow flake8 E302/E305 rules
6. **Long lines** → Break at 100 characters
7. **Unused imports** → Remove to pass validation
8. **Method assumptions** → Use `hasattr()` checks
9. **Submitting with failing validation** → Always iterate until clean

## Repository Information

- **Owner**: Intelluxe-AI, **Repo**: intelluxe-core, **Branch**: main
- **Development Status**: Active development, Phase 1 real implementations in progress
- **Family-Built**: Co-designed by Jeffrey & Justin Sue for real-world clinical workflows

## Phase Implementation

- **Phase 1 (Current)**: Real AI implementations with MCP integration - core agents, reasoning, and workflow orchestration
- **Phase 2**: Business services (insurance, billing, doctor personalization)
- **Phase 3**: Production deployment and enterprise scaling

---

**Last Updated**: 2025-08-01 | **Comprehensive Type Safety & Medical Data Preservation Guidelines Added**
