# Copilot Instructions for Intelluxe AI Healthcare System

## Project Overview
**Intelluxe AI** - Privacy-First Healthcare AI System built for on-premise clinical deployment. Currently in active development, focusing on core infrastructure and test suite hardening.

### Core Architecture
- **Modular healthcare AI platform** with universal service orchestration
- **Focus**: Administrative/documentation support, NOT medical advice
- **Privacy-First**: All PHI/PII remains on-premise with no cloud dependencies
- **Development Status**: Build robust, maintainable features for future clinical environments, but defer production-specific hardening until later phases

## Primary Scripts & Components

### Main Healthcare AI Infrastructure
- **`bootstrap.sh`** - Main healthcare AI infrastructure bootstrapper
- **`universal-service-runner.sh`** - Universal service runner for ANY Docker service
- **`config_web_ui.py`** - Healthcare-focused web interface with service health monitoring
- **`lib.sh`** - Common utility functions for Intelluxe AI healthcare operations

### Directory Structure
```
reference/ai-patterns/  # MIT licensed AI engineering patterns (git submodule)
mcps/healthcare/        # Healthcare MCP server code (copied from agentcare-mcp)
services/user/          # Service configurations - each service has SERVICE.conf
agents/                 # AI agent implementations (intake/, document_processor/, etc.)
core/                   # Core healthcare AI infrastructure (memory/, orchestration/, etc.)
data/                   # AI training and evaluation data management
infrastructure/         # Healthcare deployment configs (docker/, monitoring/, etc.)
docs/                   # Comprehensive healthcare AI documentation including PHASE_*.md
scripts/                # Primary shell scripts (universal-service-runner.sh, lib.sh, etc.)
```

## AI Engineering Patterns

### Reference Library
- **`reference/ai-patterns/`** - MIT licensed AI engineering patterns (git submodule from ai-engineering-hub) adapted for healthcare
- **`mcps/healthcare/`** - Healthcare MCP server code directly copied from agentcare-mcp repository
- **Healthcare-Relevant Patterns**:
  - `agentic_rag/` - Medical document processing and research assistance
  - `document-chat-rag/` - Patient document Q&A with privacy protection
  - `corrective-rag/` - Accuracy-critical healthcare information retrieval
  - `audio-analysis-toolkit/` - Medical transcription and voice analysis
  - `content_planner_flow/` - Clinical workflow automation
  - `fastest-rag-stack/` - High-performance medical data retrieval
  - `eval-and-observability/` - Healthcare AI system monitoring
  - `mcp-agentic-rag/` - Model Context Protocol for healthcare agents
  - `multi-modal-rag/` - Medical imaging and document processing
  - `trustworthy-rag/` - Compliance-focused RAG for healthcare

### Healthcare Adaptation Principles
- **Privacy-First**: Replace cloud APIs with on-premise alternatives (Ollama, local models)
- **Compliance**: Add audit logging and compliance tracking to all implementations
- **PHI Protection**: Ensure no patient data leaves the local environment
- **Explainable AI**: Implement traceability features for medical compliance
- **HIPAA Alignment**: Adapt all patterns for healthcare privacy requirements

## Healthcare Security Development Patterns

### Critical Security Rules
- **Generic Error Messages**: Never expose JWT_SECRET, MASTER_ENCRYPTION_KEY, or config details
- **Environment-Aware Placeholders**: Block production deployment when incomplete, allow configurable development
- **Comprehensive Test Coverage**: Test security fallbacks with logging verification using caplog fixture
- **Scalability by Default**: Use batching (batch_size=500) for large dataset processing
- **Security Documentation**: Always explain WHY security choices were made (HIPAA, NANP standards, etc.)

### Development Anti-Patterns to Prevent
1. `raise RuntimeError("JWT_SECRET must be set")` → Use generic error messages
2. `return False` placeholders → Use environment-aware configurable behavior
3. Security tests without logging verification → Always test logging with caplog
4. Processing all items at once → Use batching for scalability
5. Undocumented security choices → Explain compliance rationale

### Reference Files
- See `.augment/rules/healthcare-security-patterns.md` for comprehensive patterns
- Follow environment detection patterns for secure fallbacks
- Use synthetic data generation standards (555 phone prefix, clearly marked test data)

## Type Safety and MyPy Compliance Patterns

### MANDATORY Type Annotation Requirements

#### 1. **Always Add Return Type Annotations**
```python
# ✅ CORRECT - All methods need return type annotations
def __init__(self) -> None:
    self.logger = logging.getLogger(__name__)

def process_data(self, data: str) -> Dict[str, Any]:
    return {"processed": data}

# ❌ INCORRECT - Missing return type annotations
def __init__(self):  # Missing -> None
    pass

def process_data(self, data: str):  # Missing return type
    return {"data": data}
```

#### 2. **Proper Optional Type Handling**
```python
# ✅ CORRECT - Always check None before method calls
def process_client(self, client: Optional[httpx.AsyncClient]) -> Dict[str, Any]:
    if client is None:
        return {"status": "not_initialized"}
    
    # Now safe to call methods on client
    response = await client.get("/api/endpoint")
    return {"status": "success"}

# ❌ INCORRECT - Calling methods on Optional type
def process_client(self, client: Optional[httpx.AsyncClient]) -> Dict[str, Any]:
    response = await client.get("/api/endpoint")  # MyPy error: client could be None
    return {"status": "success"}
```

#### 3. **Type-Safe Dictionary Operations**
```python
# ✅ CORRECT - Explicit typing and type guards
def format_results(self, issues: List[SecurityIssue]) -> Dict[str, Any]:
    results: Dict[str, Any] = {
        "issues_by_category": {},
        "recommendations": []
    }
    
    # Type-safe dictionary operations with type guards
    issues_by_category: Dict[str, List[SecurityIssue]] = {}
    for issue in issues:
        if issue.category not in issues_by_category:
            issues_by_category[issue.category] = []
        issues_by_category[issue.category].append(issue)
    
    results["issues_by_category"] = issues_by_category
    
    # Type-safe list operations
    recommendations = results["recommendations"]
    if isinstance(recommendations, list):
        recommendations.append("New recommendation")
    
    return results

# ❌ INCORRECT - Treating object as specific type without checking
def format_results(self, issues: List[SecurityIssue]) -> Dict[str, Any]:
    results = {"issues_by_category": {}, "recommendations": []}
    
    # MyPy error: "object" has no attribute "append"
    results["recommendations"].append("recommendation")
    
    # MyPy error: Unsupported right operand type for in ("object")
    if issue.category not in results["issues_by_category"]:
        results["issues_by_category"][issue.category] = []
    
    return results
```

#### 4. **Environment Variable Type Safety**
```python
# ✅ CORRECT - Handle None from os.getenv()
def __init__(self, secret_key: Optional[str] = None) -> None:
    default_key = secrets.token_hex(32)
    env_key = os.getenv('JWT_SECRET_KEY')
    self.secret_key: str = secret_key or env_key or default_key

# ❌ INCORRECT - os.getenv() can return None
def __init__(self, secret_key: Optional[str] = None) -> None:
    self.secret_key: str = secret_key or os.getenv('JWT_SECRET_KEY', secrets.token_hex(32))
    # MyPy error: expression has type "str | None", variable has type "str"
```

#### 5. **Mixed Dictionary Type Handling**
```python
# ✅ CORRECT - Use Dict[str, Any] for mixed types
def load_configuration(self) -> Dict[str, Any]:
    base_config: Dict[str, Any] = {
        'key_rotation_days': 365,        # int
        'audit_logging': True,           # bool
        'entropy_threshold': 0.8,        # float
        'min_key_length': 32             # int
    }
    return base_config

# ❌ INCORRECT - MyPy infers wrong type from first entry
def load_configuration(self) -> Dict[str, Any]:
    base_config = {
        'key_rotation_days': 365,        # MyPy assumes all values are int
        'audit_logging': True,           # Error: bool not compatible with int
        'entropy_threshold': 0.8,        # Error: float not compatible with int
    }
    return base_config
```

### Code Generation Anti-Patterns to Prevent

#### MyPy Error Prevention Checklist
- [ ] **All `__init__` methods have `-> None` return type**
- [ ] **All functions have explicit return type annotations**
- [ ] **Optional types checked for None before method calls**
- [ ] **Dictionary operations use type guards (`isinstance` checks)**
- [ ] **Mixed-type dictionaries explicitly typed as `Dict[str, Any]`**
- [ ] **Environment variables properly handle None returns**
- [ ] **Class attributes have explicit type annotations**

#### Common MyPy Error Patterns and Fixes

**Error Pattern**: `"object" has no attribute "append"`
**Fix**: Use type guards before operations on dictionary values
```python
# Before: results["recommendations"].append(item)
# After: 
recommendations = results["recommendations"]
if isinstance(recommendations, list):
    recommendations.append(item)
```

**Error Pattern**: `Unsupported right operand type for in ("object")`
**Fix**: Use separate typed variable for dictionary operations
```python
# Before: if key not in results["dict_field"]: ...
# After:
dict_field: Dict[str, List[Item]] = {}
# ... populate dict_field ...
results["dict_field"] = dict_field
```

**Error Pattern**: `Item "None" of "Optional[Type]" has no attribute "method"`
**Fix**: Add None check before method calls
```python
# Before: self.optional_client.get("/endpoint")
# After:
if self.optional_client is not None:
    self.optional_client.get("/endpoint")
```

**Error Pattern**: `Incompatible types in assignment (expression has type "str | None", variable has type "str")`
**Fix**: Provide explicit fallback for None values
```python
# Before: self.value: str = os.getenv('KEY', 'default')
# After: 
env_value = os.getenv('KEY')
self.value: str = env_value or 'default'
```

### Healthcare-Specific Type Safety Requirements
- **PHI Data Structures**: Always use strict typing for patient data with proper sanitization
- **Audit Logging**: Type-safe event logging with structured data validation
- **Security Keys**: Never allow None types for encryption/authentication keys
- **Configuration Management**: Environment-aware type checking with healthcare compliance validation

### Pre-Submission Validation
**ALWAYS run before committing Python code:**
```bash
# MyPy validation for all healthcare directories
python3 -m mypy src/ --ignore-missing-imports --strict-optional
python3 -m mypy agents/ --ignore-missing-imports --strict-optional
python3 -m mypy mcps/ --ignore-missing-imports --strict-optional  # if Python files exist
```

## Healthcare Philosophy & Safety

### Medical Safety Principles
- **NO medical advice, diagnosis, or treatment recommendations**
- **Focus ONLY on administrative and documentation support**
- **Explainable AI**: All AI decisions must be traceable and auditable for healthcare compliance
- **Modular Design**: Pluggable agents and tools customizable per clinic without affecting core system

### Privacy & Security
- **HIPAA-compliant service orchestration** with audit logging and role-based access
- **All PHI/PII remains on-premise** - no cloud dependencies or external API calls with patient data
- **Performance-optimized**: GPU-accelerated local inference for real-time healthcare AI

## Service Management

### Healthcare Services
- **Ollama** (local LLM), **Healthcare-MCP** (medical tools), **PostgreSQL** (patient context)
- **Redis** (session cache), **n8n** (workflows), **WhisperLive** (real-time transcription)

### Healthcare Container Security
- **User/Group Model**: Development uses justin:intelluxe (1000:1001), production uses clinic-admin:intelluxe
- **Security Hardening**: Python 3.12-slim-bookworm base with latest security patches
- **Network Isolation**: All containers run on intelluxe-net with no external data egress
- **Fork Strategy**: Healthcare improvements made directly on main branch of forked repositories

### Service Configuration Pattern
- **Service Structure**: Each service configured at `services/user/SERVICE/SERVICE.conf`
- **Deployment Flow**: `bootstrap.sh` calls `universal-service-runner.sh` for each SERVICE.conf file
- **Universal Runner**: `universal-service-runner.sh` is the ONLY method for deploying services
- **Rolling Restarts**: Services restart in dependency order with health checks

## Development Guidelines

### Architecture & Implementation
- **Follow `ARCHITECTURE_BASE_CODE.md`** for mapping AI Engineering Hub patterns to Intelluxe healthcare components
- **Use `DEV_ACCELERATION_TOOLKIT.md`** for rapid prototyping, monitoring, quality assurance
- **Reference `IMPLEMENTATION_AND_TESTING.md`** for healthcare-specific testing and n8n workflows

### Path Management & Directory Structure
- **Production Paths**: All scripts use `CFG_ROOT:=/opt/intelluxe/stack` for production consistency
- **Development Symlinks**: `make install` creates symlinks from `/home/intelluxe/` → `/opt/intelluxe/`
- **Log Directory Exception**: `/opt/intelluxe/logs` remains a real directory for systemd service access
- **Ownership Model**: Consistent `CFG_UID=1000:CFG_GID=1001` across all components

### Systemd Service Management
- **Service Paths**: All systemd services use `/opt/intelluxe/scripts/` paths (via symlinks)
- **Security Settings**: Avoid overly restrictive `ProtectSystem=strict` - use minimal security for development phase
- **Environment Variables**: Services need `Environment=HOME=/root` for scripts that reference `$HOME`
- **Service Installation**: `make install` handles symlinks to `/etc/systemd/system/` with `intelluxe-` prefix

### Testing Approach
- **Healthcare-grade testing** with shadow deployment and quality metrics
- **Compliance-first**: All features must support HIPAA compliance, audit trails, data retention policies
- **Real-world validation**: Test with actual clinical scenarios using n8n workflows

## Phase Implementation

- **Phase 0**: Project setup and directory structure (`PHASE_0.md`)
- **Phase 1**: Core AI infrastructure with Ollama, MCP, and basic agents (`PHASE_1.md`)
- **Phase 2**: Business services, insurance verification, billing, and doctor personalization (`PHASE_2.md`)
- **Phase 3**: Production deployment with enterprise scaling and compliance monitoring (`PHASE_3.md`)

## Core AI Agents

1. **Intake Agent** - Patient intake form processing and data extraction (administrative only)
2. **Document Processor** - Medical document organization and PII redaction
3. **Research Assistant** - PubMed/FDA/ClinicalTrials.gov search and citation management
4. **Billing Helper** - Billing code lookup and claims assistance (reference only)
5. **Scheduling Optimizer** - Appointment scheduling and resource optimization

## Testing Guidelines

### Healthcare Testing Standards
- **Test with realistic medical scenarios** while avoiding actual patient data
- **Quality metrics**: Track response accuracy, medical appropriateness, and safety boundaries
- **Compliance testing**: Validate HIPAA compliance, audit logging, and data handling practices
- **Performance testing**: Ensure sub-30-second response times suitable for clinical workflows
- **Integration testing**: Test n8n workflows end-to-end with healthcare service chains

### Bats Testing Framework
- **Bats tests (*.bats)** are for shell script integration testing
- **MUST source functions** from actual scripts in `scripts/` to test real code
- **Variable safety**: Don't rely on potentially unbound variables like `$status` or `$lines`
- **Check expected output** in files or command results directly

## Code Structure & Best Practices

### Shell Scripts
- **Follow shellcheck best practices**
- **Use `lib.sh`** for common functions
- **Universal runner**: `universal-service-runner.sh` dynamically generates Docker commands from configuration

### Python Web UI
- **Creates .conf files directly** using universal service runner format in `services/user/SERVICE/` directories
- **Implements modern service addition** through universal configuration pattern

### Service Configurations
- **Universal key=value format** supporting all Docker features
- **See `UNIVERSAL_CONFIG_SCHEMA.md`** for specification
- **Service Pattern**: Each service at `services/user/SERVICE/SERVICE.conf` deployed through `universal-service-runner.sh`

## Development Principles

1. **Healthcare-first**: Build robust, maintainable features for future clinical environments, but defer production-specific hardening until later phases
2. **Privacy-by-design**: PHI/PII never leaves the local network or gets stored inappropriately
3. **Explainable AI**: Every AI decision must be traceable and auditable for medical compliance
4. **Modular architecture**: Agents, tools, and services can be customized per clinic without breaking core system
5. **Performance-critical**: Real-time AI inference suitable for busy clinical workflows
6. **Family-built philosophy**: Designed by healthcare family (Jeffrey & Justin Sue) for real-world clinical challenges
7. **User/Group Consistency**: Development uses justin:intelluxe (1000:1001), production uses clinic-admin:intelluxe (same UID/GID, different username for healthcare IT context)

## Editing Best Practices

### File Safety
- **ALWAYS read the file section** you're editing BEFORE making changes
- **NEVER break bash syntax** - check if/fi, case/esac, function boundaries match
- **Verify edits don't accidentally affect** unrelated code sections
- **Remove unused variables** after refactoring to pass shellcheck

### Error Prevention
- **Use shellcheck validation** after every bash script edit
- **Make one logical change per edit**, not multiple unrelated changes
- **When removing functions**, ensure their call sites are also updated
- **Run affected test suites** after making changes to verify no regressions

## Git Management

### Repository Architecture
- **Main Repository**: Intelluxe AI healthcare system with universal service orchestration
- **Submodules**: AI Engineering patterns (reference/ai-patterns) and healthcare-specific forks
- **WhisperLive Integration**: Forked submodule using main branch for healthcare improvements

### Submodule Strategy
- **reference/ai-patterns/**: MIT licensed patterns (upstream submodule from ai-engineering-hub)
- **services/user/whisperlive/**: Healthcare-hardened fork of WhisperLive on main branch
- **Upstream Integration**: Periodic merging of upstream improvements with healthcare customizations
- **No Branching Complexity**: Use main branch for healthcare improvements, not separate healthcare branches

### Tracked Files
- `services/core/`, `scripts/`, `test/`, `systemd/`, `docs/`, `services/user/.gitkeep`, `reference/` (submodule), `mcps/`, `services/user/whisperlive/` (healthcare fork)
- `THIRD_PARTY_LICENSES.md` (MIT license attributions for compliance)

### Ignored Files
- `services/user/*` (except .gitkeep), `docker-stack/`, `logs/`, `venv/`

### Commit Guidelines
- **Never commit user services** or generated directories
- **Test bootstrap creates proper structure**
- **Maintain MIT license attributions** for healthcare-mcp, ai-patterns, and whisperlive

## Repository Information

- **Owner**: Galdaer
- **Name**: Intelluxe
- **Branch**: main
- **Major Version**: 1.0 - Healthcare AI Platform with Universal Service Architecture
- **Development Status**: Active development, focusing on hardening test suite for robust integration testing

## Family-Built Heritage

Co-designed by father-son team (Jeffrey & Justin Sue) for real-world clinical workflows, ensuring practical applicability and healthcare industry expertise.

### Code Quality Enhancement Patterns

#### String Constant Management
- **ALWAYS extract repeated error messages** to named constants
- **Use descriptive constant names** that explain the context
- **Group related constants** in dedicated sections or files

#### Technical Documentation Standards
- **Complex algorithms MUST include examples** showing edge cases
- **Explain compliance rationale** (NANP standards, HIPAA requirements)
- **Document WHY technical decisions were made**, not just what they do

#### Feature Flag Best Practices
- **Incomplete production features** must use feature flags
- **Default to safe/disabled state** in production
- **Use environment variables** for feature flag control
- **Clear error messages** when features are disabled

#### Security Event Logging
- **ALL authentication events** must be logged (success and failure)
- **Use appropriate log levels** (warning for failures, info for success)
- **Include context** in log messages (environment, user info when available)

#### Performance Monitoring Requirements
- **Optimization features** (batching, caching) must include performance logging
- **Log when optimizations are triggered** with relevant metrics
- **Use debug level** for detailed performance information
- **Monitor effectiveness** of caches and optimizations

### Reference Implementation Patterns
- See existing code for constant extraction patterns
- Follow environment detection patterns for feature flags
- Use structured logging for security and performance events

## Remote Agent Workflow Guidelines

### Task Scope Management
- **Focus on weekly deliverables** from phase documentation
- **Prioritize functional completeness** over perfect optimization
- **Implement healthcare security patterns** from day one
- **Test incrementally** - don't wait for full phase completion

### Remote Agent Best Practices
- **Read phase documentation first** before starting implementation
- **Follow existing code patterns** in the repository
- **Maintain healthcare compliance** in all implementations
- **Create meaningful commit messages** that explain healthcare context
- **Test with realistic medical scenarios** using synthetic data
- **PRIORITIZE EFFICIENCY**: Always choose resource-efficient solutions over apparent simplicity
- **DESIGN FOR SCALE**: Implement caching, sharing, and optimization patterns from the start
- **AVOID DUPLICATION**: Never duplicate expensive operations when sharing is possible

### Integration Points
- **Universal service runner** for all service deployments
- **Healthcare-MCP** for medical tool integration
- **PostgreSQL/Redis** for persistent storage and caching
- **Ollama** for local LLM inference

## Remote Agent Task Prompt Generation

### When User Requests: "Create remote agent task prompt for Phase X Week Y"

**Your Role**: Analyze current codebase + phase documentation + existing patterns to create detailed, actionable prompts for remote agents.

**CRITICAL: NEVER Provide Specific Code Implementations**

Remote agent prompts must NEVER include:
- Exact code implementations
- Specific import statements  
- Hardcoded method signatures
- Assumed file contents or structure
- Predetermined configuration values

**Why**: Providing specific code guarantees formatting errors, import mismatches, and structural conflicts with the actual codebase.

**MANDATORY: Always Include Autonomous Execution Mode**

Every remote agent prompt MUST include this section:

```markdown
## AUTONOMOUS EXECUTION MODE

**Work Continuously**: Execute ALL tasks without asking for continuation unless you encounter an unrecoverable error that requires human decision-making.

**Context Management**: If you approach token limits, summarize your progress and continue with remaining tasks. Do NOT ask permission to continue.

**Expected Duration**: [Specify 1-4 hours based on task complexity]

**Interruption Policy**: Only stop for:
- Unrecoverable errors requiring human input
- Ambiguous requirements needing clarification  
- 100% task completion

**Progress Reporting**: Provide brief progress updates every 30-45 minutes, then immediately continue working.
```

**Remote Agent Limitations**:
- Cannot read multiple files for context
- Cannot synthesize architectural decisions
- Need systematic methodology, not specific implementations
- Must analyze actual codebase before making changes
- Should work autonomously for 2-4 hours without human intervention

**Required Prompt Structure**:
```markdown
## Remote Agent Task: Phase X Week Y - [Descriptive Title]

**Objective**: [Specific, measurable goal]

## MANDATORY FIRST STEP: Codebase Analysis (30-45 minutes)
1. **Read actual error messages**: `make lint 2>&1 | tee current_errors.txt`
2. **Examine actual file structure**: `find src/ -name "*.py" | head -20`
3. **Understand actual imports**: Open and read files mentioned in errors
4. **Identify root cause patterns**: Missing files? Import paths? Formatting?

## SYSTEMATIC APPROACH: Analysis-First Development
1. **Read the actual file before modifying it**
2. **Match existing code style exactly**
3. **Fix only the specific error, don't refactor**
4. **Validate each change immediately**
5. **Only proceed if validation passes**

## ERROR PREVENTION METHODOLOGY:
- **Analysis-First**: Understand actual code before changing
- **Validation-Driven**: Test each change immediately
- **Pattern-Matching**: Follow existing codebase conventions
- **Incremental**: One error at a time

**Success Criteria**:
- [ ] Actual codebase analyzed and understood
- [ ] Root cause identified for each error
- [ ] Minimal fixes applied matching existing patterns
- [ ] Each fix validated individually
- [ ] No new errors introduced
- [ ] `make lint && make validate && make test` passes

**Healthcare Compliance Checks**:
- [ ] PHI protection preserved
- [ ] Audit logging maintained
- [ ] Security patterns intact
- [ ] No sensitive data exposure in error messages

**Validation Commands**:
```bash
# Individual file validation (after each change)
python -m py_compile <modified_file>
flake8 --max-line-length=100 <modified_file>

# Full validation (only at end)
make lint && make validate && make test
```
```

### Task Prompt Generation Process:
1. **Read phase documentation** (`docs/PHASE_X.md`) for the specific week
2. **Identify systematic methodology needed** (not specific implementations)
3. **Emphasize codebase analysis requirements**
4. **Focus on error prevention and validation workflow**
5. **Include healthcare compliance preservation requirements**
6. **Create measurable success criteria** with specific validation commands

### Healthcare-Specific Requirements for All Prompts:
- **Security**: Preserve existing PHI protection and security patterns
- **Compliance**: Maintain audit logging and HIPAA-compliant patterns
- **Integration**: Ensure compatibility with existing service architecture
- **Testing**: Include incremental validation workflow
- **Documentation**: Require understanding existing patterns before changes

### Remote Agent Anti-Patterns to Prevent:
1. **Providing exact code** → Require codebase analysis first
2. **Assuming file structure** → Require actual file examination
3. **Hardcoding implementations** → Emphasize pattern matching
4. **Skipping validation** → Mandate incremental testing
5. **Making multiple changes** → One error at a time approach

### Example Integration Points to Always Include:
- Universal service runner compatibility
- Healthcare-MCP tool integration
- PostgreSQL/Redis for healthcare data
- Ollama for local LLM inference
- Healthcare security middleware
- Audit logging requirements

## Remote Agent Quality Assurance Patterns

### Iterative Validation Requirements
- **ALWAYS run validation after each change**: `make lint && make validate`
- **Continue iterating until both pass**: Never submit work with failing validation
- **Fix one category at a time**: Don't attempt to fix all issues simultaneously
- **Test incrementally**: Verify each fix before moving to the next

### Shellcheck Issue Resolution Patterns
- **SC2317 (Unreachable Code)**: Check function calls, exit statements, nested definitions
- **SC2016 (Quote Expansion)**: Use double quotes for variable expansion, single quotes for literals
- **Function Structure**: Ensure all defined functions are called or properly disabled
- **Exit Code Verification**: Always check `echo $?` after make commands

### Remote Agent Validation Workflow
1. **Initial Assessment**: Run `make lint` and `make validate` to identify all issues
2. **Categorize Issues**: Group similar shellcheck warnings together
3. **Fix Incrementally**: Address one category, then test
4. **Verify Progress**: Confirm issue count decreases after each iteration
5. **Final Validation**: Both commands must exit with code 0

### Quality Gates for Remote Agents
- **Pre-commit**: `make lint` must pass (exit code 0)
- **Pre-submit**: `make validate` must pass (exit code 0)
- **Healthcare Compliance**: All security patterns preserved
- **No Regressions**: Existing functionality maintained

### Common Anti-Patterns to Prevent
1. **Submitting with failing validation** → Always iterate until clean
2. **Fixing all issues at once** → Fix incrementally and test
3. **Ignoring unreachable code warnings** → Properly structure or disable
4. **Using single quotes for variables** → Use double quotes for expansion
5. **Not testing after each change** → Always validate incrementally

### Remote Agent Success Criteria Template
```bash
# Required validation before task completion
make lint && make validate && echo "✅ Ready for submission"
```

**All remote agent tasks must include this validation workflow in success criteria.**

### Remote Agent Environment Setup Requirements

#### CI Environment Variables
Remote agents must set these environment variables for proper operation:
```bash
export ENVIRONMENT=development
export CI=true
```

#### Required Dependencies for Remote Agents
Remote agents operating in CI environments need these additional packages:

**System packages (install with apt/dnf/pacman):**
- `lsof` - Process monitoring for validation scripts
- `socat` - Network utilities for service testing  
- `wireguard-tools` - VPN functionality testing

**Python packages (install with uv, fallback to pip):**
- `flake8` - Python linting for healthcare AI code
- `mypy` - Type checking for security-critical code
- `pytest` - Testing framework for validation
- `pytest-asyncio` - Async testing support for healthcare AI
- `yamllint` - YAML configuration validation
- `psycopg2-binary` - PostgreSQL adapter for healthcare data
- `cryptography` - Security and encryption libraries

#### Remote Agent Setup Pattern
```bash
# Set CI environment
export ENVIRONMENT=development CI=true

# Install system dependencies (preferred for Ubuntu/Debian)
sudo apt update
sudo apt install -y lsof socat wireguard-tools python3-flake8 python3-pytest python3-yaml python3-cryptography python3-psycopg2

# Install Python tools with uv (preferred) or pip (fallback)
if command -v uv >/dev/null 2>&1; then
    uv pip install --system --break-system-packages mypy pytest-asyncio yamllint || echo "uv install failed"
else
    pip install --user --break-system-packages mypy pytest-asyncio yamllint || echo "pip install failed"
fi

# Verify installation
make lint && make validate
```

#### Dependency Installation Priority
1. **Use uv for Python packages** (10-100x faster than pip)
2. **Fallback to pip** if uv unavailable
3. **Install system packages** via native package manager
4. **Always verify** with `make lint && make validate`

#### Remote Agent Pre-flight Checklist
- [ ] Environment variables set (`ENVIRONMENT=development`, `CI=true`)
- [ ] System dependencies installed (`lsof`, `socat`, `wireguard-tools`)
- [ ] Python linting tools available (`flake8`, `mypy`)
- [ ] Validation passes (`make lint && make validate`)

## CI Environment Testing Patterns

### Docker Test Container Architecture
- **Test Isolation**: All tests run in `intelluxe-test-runner:latest` container
- **Coverage Generation**: kcov generates HTML/JSON coverage reports
- **CI Mocking**: `[CI] Sourcing lib.sh in test mode - root actions will be mocked`
- **Expected Failures**: 3 tests fail in CI (network, filesystem, WireGuard key generation)

### Test Directory Structure
- **Primary**: `test/` directory contains Bats test files
- **Secondary**: `tests/` directory for Python tests (if present)
- **Coverage**: `./coverage/` directory for kcov HTML reports
- **Artifacts**: Coverage uploaded as GitHub Actions artifacts

### CI Test Success Criteria
- **Pass Rate**: 136/139 tests passing (97.8%) is acceptable
- **Expected Failures**: Network IP parsing, log directory paths, WireGuard key generation
- **Coverage**: HTML reports with 57 files, ~330KB indicates successful coverage generation

### Healthcare AI Testing Standards
- **Environment Variables**: `CI=true`, `ENVIRONMENT=development`, `DRY_RUN=true`
- **Security**: All PHI/PII operations mocked in CI
- **Isolation**: Tests run in isolated Docker network with DNS
- **Timeout**: 180s for coverage runs, 120s for standard tests

## Architectural Decision-Making Principles

### CRITICAL: Always Choose Efficiency Over Simplicity

When faced with multiple implementation options, **ALWAYS prioritize efficiency, scalability, and resource optimization** over apparent simplicity. Simple solutions that waste resources or reduce performance are technical debt.

#### Decision Framework (Mandatory Order):

1. **Performance & Resource Efficiency FIRST**
   - Will this scale with increased load?
   - Does this minimize resource usage (time, memory, bandwidth, compute)?
   - Can this be cached, shared, or optimized for reuse?

2. **Healthcare Compliance & Security SECOND** 
   - Does this maintain HIPAA compliance?
   - Are audit trails preserved?
   - Is PHI protection maintained?

3. **Maintainability & Debugging THIRD**
   - Can this be easily debugged when it fails?
   - Is the architecture comprehensible to other developers?
   - Does this reduce or increase technical debt?

4. **Implementation Simplicity LAST**
   - Only consider "simplicity" after the above are satisfied
   - "Simple" solutions that waste resources are NOT actually simple

### Architectural Anti-Patterns to REJECT

❌ **"Let each job install its own dependencies"** 
- Wastes CI minutes, bandwidth, and time
- Multiplies resource usage unnecessarily
- Creates maintenance overhead across multiple jobs

❌ **"Keep it simple by duplicating work"**
- Apparent simplicity that creates hidden complexity
- Resource waste is never actually "simple"
- Harder to maintain when changes are needed

❌ **"Avoid caching because it's complex"**
- Caching is fundamental to efficient systems
- "Complexity" of proper caching pays dividends immediately
- Avoiding caching creates performance debt

❌ **"Individual jobs are easier to understand"**
- False simplicity that ignores system-level efficiency
- Wastes shared resources (CI time, bandwidth, compute)
- Creates dependency management nightmares

### Architectural Patterns to EMBRACE

✅ **Shared dependency caching with intelligent job orchestration**
- One setup job installs and caches everything
- All other jobs reuse cached dependencies
- Parallel execution with proper dependency graphs

✅ **Resource sharing and optimization**
- Cache compiled assets, installed packages, model downloads
- Share expensive operations across multiple consumers
- Design for reuse from the beginning

✅ **Strategic complexity for system efficiency**
- Accept implementation complexity that provides systemic benefits
- Invest in proper architecture that scales and performs
- Build once, benefit everywhere

✅ **Performance-first healthcare architecture**
- Healthcare systems must be fast and reliable
- Optimize for real-world clinical workflow needs
- Every second saved helps patient care

### Decision Examples Applied

**WRONG Approach**: 
```yaml
# ❌ Each job installs its own deps "for simplicity"
job-1: install deps → run tests
job-2: install deps → run tests  
job-3: install deps → run tests
# Result: 3x resource usage, 3x time, 3x failure points
```

**CORRECT Approach**:
```yaml
# ✅ Shared setup with parallel execution
setup-deps: install & cache everything
job-1: depends on setup-deps → run tests (fast)
job-2: depends on setup-deps → run tests (fast) 
job-3: depends on setup-deps → run tests (fast)
# Result: 1x setup cost, 3x parallel speed benefit
```

**Healthcare AI Specific Examples**:

❌ **REJECT**: Installing spaCy models in every security check job
✅ **EMBRACE**: Cache spaCy models once, reuse across PHI detection, audit logging, compliance checks

❌ **REJECT**: "Simple" workflows that reinstall PyTorch/CUDA in every step
✅ **EMBRACE**: Strategic dependency sharing for ML workloads

❌ **REJECT**: Avoiding optimization "until later" 
✅ **EMBRACE**: Build efficient patterns from day one

### Implementation Guidelines

When designing any workflow, CI/CD pipeline, or system component:

1. **Map all resource usage** - identify what can be shared
2. **Design dependency graphs** - maximize parallelization opportunities  
3. **Implement strategic caching** - cache expensive operations aggressively
4. **Optimize the critical path** - focus on end-to-end speed
5. **Accept beneficial complexity** - complex setup that enables simple execution

### CI/CD Efficiency Requirements

**MANDATORY for all CI/CD workflows:**

1. **Shared dependency installation** - Never install the same dependencies multiple times
2. **Aggressive caching** - Cache everything that can be cached (pip, uv, models, compiled assets)
3. **Strategic job dependencies** - Use `needs:` to create optimal dependency graphs
4. **Resource-conscious design** - Every minute saved helps the entire development team

**CI/CD Anti-Patterns to REJECT:**
- Installing Python dependencies in every job separately
- Downloading spaCy models multiple times
- Running the same setup scripts across multiple jobs
- "Simple" approaches that multiply resource usage

**CI/CD Patterns to EMBRACE:**
- One setup job that caches everything for reuse
- Parallel execution wherever possible
- Smart dependency graphs that optimize the critical path
- Comprehensive caching strategies that benefit all subsequent runs

### Code Quality and Linting Standards

### Python Code Quality Requirements
- **ALWAYS follow flake8 standards**: No trailing whitespace (W293), proper blank lines (E302, E305)
- **Line length**: Maximum 100 characters per line
- **Import organization**: One import per line, grouped properly
- **Blank line rules**: 
  - Two blank lines before class definitions
  - One blank line before method definitions
  - No trailing blank lines at end of functions
- **String formatting**: Use f-strings for Python 3.6+
- **Method verification**: Always check if methods exist before calling them in tests
- **Unused imports**: Remove all unused imports to pass Pylance validation
- **Defensive programming**: Use hasattr() checks before calling unknown methods

### Code Generation Anti-Patterns to Prevent
1. **Trailing whitespace** → Always strip whitespace from generated code
2. **Inconsistent blank lines** → Follow E302/E305 rules strictly
3. **Long lines** → Break at 100 characters with proper indentation
4. **Unused imports** → Remove imports that aren't used in the code
5. **Method assumptions** → Use hasattr() to verify methods exist before calling them
6. **Optional parameter type safety** → Always check if optional parameters are None before calling methods on them

### Type Safety Requirements for Optional Parameters
- **ALWAYS check None before method calls**: When a parameter can be None, check `if param is not None:` before calling methods
- **Database connections**: Check `if self.postgres_conn:` before calling `.cursor()` or `.commit()`
- **Optional objects**: Use `if obj:` or `if obj is not None:` before accessing attributes or methods
- **Graceful degradation**: Provide fallback behavior when optional dependencies are unavailable

### Pre-Generation Checklist
Before generating any Python code:
- [ ] Check line length compliance (≤100 chars)
- [ ] Verify proper blank line spacing
- [ ] Ensure no trailing whitespace
- [ ] Remove unused imports
- [ ] Use hasattr() checks for method calls
- [ ] Add None checks for optional parameters before calling methods
- [ ] Test flake8 and Pylance compliance

### Shell Script Quality Standards
- **Shellcheck compliance**: All scripts must pass shellcheck validation
- **Quote expansion**: Use double quotes for variables, single for literals
- **Function structure**: Proper if/fi, case/esac matching
- **Variable safety**: Check for unbound variables

### Healthcare Code Quality Patterns
- **Security-first**: Generic error messages, no config exposure
- **Compliance**: HIPAA-compliant logging and audit trails
- **Testing**: Real functionality tests, not mocked placeholders
- **Documentation**: Explain WHY security choices were made

### Validation Workflow
```bash
# Required validation before any code submission
make lint && make validate && echo "✅ Code quality verified"
```

**CRITICAL**: All generated code must pass `make lint` without warnings.

### Remote Agent Testing Guidelines
- **Use project test infrastructure**: Always use `CI=true bash ./scripts/test.sh` or `make test` instead of raw bats commands
- **Debug with grep**: Use `grep -A 20 "test name" test/file.bats` to examine specific test failures
- **Validation workflow**: Always end with `make lint && make validate && make test`
- **No direct bats installation**: Remote agents should leverage existing project infrastructure

### Remote Agent Debugging Commands Template
```bash
# Use project test infrastructure (handles bats installation)
CI=true bash ./scripts/test.sh

# Debug specific test failures by examining test files
grep -A 20 "test failure name" test/relevant-file.bats

# Use make targets for validation
make lint && make validate && make test
```

#### Required Setup Commands for Remote Agents
```bash
# Set CI environment with all required variables
export ENVIRONMENT=development CI=true
export CFG_ROOT=/opt/intelluxe/stack CFG_UID=1000 CFG_GID=1001

# Create required directory structure
sudo mkdir -p /opt/intelluxe/stack/{logs,backups,qrcodes}
sudo mkdir -p /etc/wireguard
sudo chown -R $(id -u):$(id -g) /opt/intelluxe/stack

# Install dependencies and run make install
sudo apt update
sudo apt install -y lsof socat wireguard-tools shellcheck python3-flake8 python3-pytest python3-yaml python3-cryptography python3-psycopg2

# CRITICAL: Run make install to set up symlinks and systemd units
sudo make install

# Verify everything works
make lint && make validate && make test
```

## Remote Agent Autonomous Execution Guidelines

### Scope Expansion Requirements

**Remote agents MUST work autonomously for 2-4 hours minimum**. Prompts should:

1. **Give broad objectives** rather than narrow tasks
2. **Allow agents to discover related issues** during analysis
3. **Encourage comprehensive solutions** not just single fixes
4. **Let agents determine their own work breakdown**
5. **Expect agents to find and fix additional problems** they discover

### Autonomous Decision-Making Patterns

**Instead of**: "Fix these 3 specific Pylance errors"
**Use**: "Systematically resolve all code quality issues, starting with Pylance/Flake8 but expanding to related problems you discover"

**Instead of**: "Create file X with methods Y and Z"  
**Use**: "Analyze the codebase architecture and implement the missing components needed for proper functionality"

**Instead of**: "Follow these 5 specific steps"
**Use**: "Use this systematic methodology but adapt it based on what you discover in the actual codebase"

### Expected Work Patterns

Remote agents should:
- **Start with analysis** (30-45 minutes)
- **Discover the full scope** of related issues (not just what's explicitly mentioned)
- **Work systematically** through all discovered problems
- **Continue until comprehensive completion** (2-4 hours total)
- **Only stop for unrecoverable errors** or 100% completion

### Prompt Structure for Autonomous Work

```markdown
## Remote Agent Task: [Broad Objective] - Comprehensive Implementation

**Objective**: [High-level goal that allows for scope expansion]

**Autonomous Scope**: You are expected to work for 2-4 hours and discover/fix related issues beyond the initial objective.

## DISCOVERY PHASE (45-60 minutes)
1. **Analyze the full problem space** - don't just fix what's mentioned
2. **Identify all related issues** that should be addressed together  
3. **Plan comprehensive solution** that addresses root causes
4. **Expand scope** to include logical extensions and improvements

## IMPLEMENTATION PHASE (90-180 minutes)
- **Work systematically** through all discovered issues
- **Make architectural improvements** where needed
- **Add comprehensive testing** for new functionality
- **Document your changes** and reasoning

## VALIDATION PHASE (30-45 minutes)
- **Test everything thoroughly** including edge cases
- **Verify no regressions** in existing functionality
- **Ensure healthcare compliance** is maintained

**Expected Discoveries**: You should find and address issues beyond the initial scope. This is expected and encouraged.
```

### Anti-Patterns That Limit Autonomy

❌ **Micro-task lists** - Don't break work into tiny steps
❌ **Predetermined file lists** - Let agents discover what needs to be created/modified
❌ **Specific time allocations** - Don't say "spend 15 minutes on X"
❌ **Narrow problem definitions** - Allow scope expansion during analysis
❌ **Prescriptive solutions** - Let agents determine the best approach

### Patterns That Enable Autonomy

✅ **Broad problem statements** - "Improve system reliability" not "fix error X"
✅ **Discovery-driven work** - "Analyze and address all related issues"
✅ **Architectural thinking** - "Design and implement proper solution"
✅ **Comprehensive scope** - "Continue until system is production-ready"
✅ **Quality-driven completion** - "Work until all validation passes"

Last Updated: 2025-01-23
