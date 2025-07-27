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
- **Optional Type Handling**: Always check `if obj is not None:` before method calls
- **Type-Safe Dictionary Operations**: Use `isinstance()` checks before operations
- **Environment Variable Safety**: Handle `os.getenv()` returning None
- **Mixed Dictionary Types**: Use `Dict[str, Any]` for mixed-type dictionaries

### Validation Standards

```bash
# Required validation before any code submission
make lint && make validate && echo "✅ Code quality verified"
```

## Testing Standards

### Current Test Status

- **26 Python test failures expected** due to incomplete infrastructure
- **Bats tests**: Shell script integration testing (source actual scripts)
- **Pre-push skips tests** during development phase
- **Focus on code quality** validation over incomplete feature tests

### Healthcare Testing Requirements

- **Test with realistic medical scenarios** using synthetic data
- **Compliance testing**: Validate HIPAA compliance and audit logging
- **Use project infrastructure**: `CI=true bash ./scripts/test.sh` or `make test`

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

1. **Trailing whitespace** → Auto-stripped by pre-commit hook
2. **Inconsistent blank lines** → Follow flake8 E302/E305 rules
3. **Long lines** → Break at 100 characters
4. **Unused imports** → Remove to pass validation
5. **Method assumptions** → Use `hasattr()` checks
6. **Submitting with failing validation** → Always iterate until clean

## Repository Information

- **Owner**: Intelluxe-AI, **Repo**: intelluxe-core, **Branch**: main
- **Development Status**: Active development, Phase 0 enhanced infrastructure
- **Family-Built**: Co-designed by Jeffrey & Justin Sue for real-world clinical workflows

## Phase Implementation

- **Phase 0**: Project setup and development infrastructure
- **Phase 1**: Core AI infrastructure (Ollama, MCP, basic agents)
- **Phase 2**: Business services (insurance, billing, doctor personalization)
- **Phase 3**: Production deployment and enterprise scaling

---

**Last Updated**: 2025-01-23 | **Length**: ~500 lines (50% reduction from original)
