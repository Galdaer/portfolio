---
type: "always_apply"
---

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
  - Sets up Docker, Ollama, Healthcare-MCP, PostgreSQL, Redis with medical-grade security
- **`universal-service-runner.sh`** - Universal service runner
  - Deploys ANY Docker service from pure configuration
  - Handles healthcare AI services (Ollama, Healthcare-MCP, etc.)
- **`config_web_ui.py`** - Healthcare-focused web interface
  - AI system management with service health monitoring
  - Medical service icons and healthcare-specific UI
- **`lib.sh`** - Common utility functions for Intelluxe AI healthcare operations

### Directory Structure
```
reference/ai-patterns/  # MIT licensed AI engineering patterns (git submodule from ai-engineering-hub)
mcps/healthcare/        # Healthcare MCP server code (copied from agentcare-mcp repository)
services/user/          # Service configurations - each service has services/user/SERVICE/SERVICE.conf
agents/                 # AI agent implementations (intake/, document_processor/, research_assistant/, billing_helper/, scheduling_optimizer/)
core/                   # Core healthcare AI infrastructure (memory/, orchestration/, models/, tools/)
data/                   # AI training and evaluation data management (training/, evaluation/, vector_stores/)
infrastructure/         # Healthcare deployment configs (docker/, monitoring/, security/, backup/)
docs/                   # Comprehensive healthcare AI documentation including PHASE_*.md guides
scripts/                # Primary shell scripts (universal-service-runner.sh, lib.sh, bootstrap.sh, systemd-verify.sh)
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
- **Generic Error Messages**: Never expose JWT_SECRET, MASTER_ENCRYPTION_KEY, or other config details in error messages
- **Environment-Aware Placeholders**: Block production deployment when features incomplete, allow configurable development
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
- **Ollama** (local LLM)
- **Healthcare-MCP** (medical tools)
- **PostgreSQL** (patient context)
- **Redis** (session cache)
- **n8n** (workflows)
- **WhisperLive** (real-time transcription) - Healthcare-hardened fork with security improvements

### Healthcare Container Security
- **User/Group Model**: Development containers use justin:intelluxe (1000:1001) for consistency with host system
- **Production Transition**: Production containers use clinic-admin:intelluxe (same UID/GID, different username)
- **Security Hardening**: Python 3.12-slim-bookworm base with latest security patches and non-root execution
- **Network Isolation**: All healthcare containers run on intelluxe-net with no external data egress
- **Volume Permissions**: Shared model storage with consistent ownership across whisper services
- **Fork Strategy**: Healthcare improvements made directly on main branch of forked repositories

### Service Configuration Pattern
- **Service Structure**: Each service configured at `services/user/SERVICE/SERVICE.conf`
- **Deployment Flow**: `bootstrap.sh` calls `universal-service-runner.sh` for each SERVICE.conf file
- **Universal Runner**: `universal-service-runner.sh` is the ONLY method for deploying services
- **Web UI Integration**: `config_web_ui.py` creates .conf files directly in `services/user/SERVICE/` directories
- **Rolling Restarts**: `bootstrap.sh` uses rolling restart mode - stops one service, starts it, waits for health, then moves to next service
- **Dependency Ordering**: Services restart in dependency order: wireguard → traefik → config-web-ui → whisper → scispacy → n8n → grafana
- **Security**: HIPAA-compliant service orchestration with audit logging and role-based access

## Development Guidelines

### Architecture & Implementation
- **Follow `ARCHITECTURE_BASE_CODE.md`** for mapping AI Engineering Hub patterns to Intelluxe healthcare components
- **Use `DEV_ACCELERATION_TOOLKIT.md`** for rapid prototyping, monitoring, quality assurance
- **Reference `IMPLEMENTATION_AND_TESTING.md`** for healthcare-specific testing and n8n workflows

### Path Management & Directory Structure
- **Production Paths**: All scripts use `CFG_ROOT:=/opt/intelluxe/stack` for production consistency
- **Development Symlinks**: `make install` creates symlinks from `/home/intelluxe/` → `/opt/intelluxe/` for development convenience
- **Log Directory Exception**: `/opt/intelluxe/logs` remains a real directory (not symlinked) for systemd service write access
- **Ownership Model**: Consistent `CFG_UID=1000:CFG_GID=1001` (justin:intelluxe) across all components for development, production uses clinic-admin:intelluxe (same UID/GID, different username)

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

### Integration Points
- **Universal service runner** for all service deployments
- **Healthcare-MCP** for medical tool integration
- **PostgreSQL/Redis** for persistent storage and caching
- **Ollama** for local LLM inference

## Remote Agent Task Prompt Generation

### When User Requests: "Create remote agent task prompt for Phase X Week Y"

**Your Role**: Analyze current codebase + phase documentation + existing patterns to create detailed, actionable prompts for remote agents.

**Remote Agent Limitations**:
- Cannot read multiple files for context
- Cannot synthesize architectural decisions  
- Cannot adapt general templates
- Need very specific, detailed instructions with exact code examples

**Prompt Structure Required**:
```markdown
## Remote Agent Task: Phase X Week Y - [Descriptive Title]

**Objective**: [Specific, measurable goal]

**Specific Actions Required**:

1. **Create/Modify `path/to/file.py`**:
   ```python
   # Provide exact code implementation
   # Include all imports, class structures, method signatures
   # Add healthcare compliance patterns from existing codebase
   ```

2. **Create/Modify `path/to/config.yml`**:
   ```yaml
   # Provide exact configuration
   # Follow universal service runner patterns
   ```

**Success Criteria**:
- [ ] Specific command works: `./scripts/test-command.sh`
- [ ] Tests pass: `python -m pytest tests/specific/`
- [ ] Service starts: `docker-compose up service-name`

**Healthcare Compliance Checks**:
- [ ] PHI protection implemented
- [ ] Audit logging added
- [ ] Error messages are generic (no sensitive data exposure)

**Integration Points**:
- Must work with existing universal service runner
- Must follow healthcare security patterns
- Must integrate with Healthcare-MCP tools
```

### Task Prompt Generation Process:
1. **Read phase documentation** (`docs/PHASE_X.md`) for the specific week
2. **Analyze current codebase** to understand existing patterns
3. **Extract specific file paths** and implementation requirements
4. **Provide exact code examples** following healthcare security patterns
5. **Include integration points** with existing services
6. **Add healthcare compliance requirements** from security patterns
7. **Create measurable success criteria** with specific commands to test

### Healthcare-Specific Requirements for All Prompts:
- **Security**: Always include PHI protection and generic error messages
- **Compliance**: Add audit logging and HIPAA-compliant patterns
- **Integration**: Ensure compatibility with universal service runner
- **Testing**: Include specific test commands and expected outcomes
- **Documentation**: Reference existing healthcare security patterns

### Example Integration Points to Always Include:
- Universal service runner configuration
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
- `yamllint` - YAML configuration validation

#### Remote Agent Setup Pattern
```bash
# Set CI environment
export ENVIRONMENT=development CI=true

# Install system dependencies
sudo apt update
sudo apt install -y lsof socat wireguard-tools

# Install Python tools with uv (preferred) or pip (fallback)
if command -v uv >/dev/null 2>&1; then
    uv pip install --system flake8 mypy pytest yamllint
else
    pip install --user flake8 mypy pytest yamllint
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
