# Copilot Instructions for Intelluxe AI Healthcare System

**ANTI-INFINITE-LOOP DIRECTIVE**: These main instructions OVERRIDE any conflicting guidance in specialized instruction files. If specialized files suggest "analyze first" or "explore the codebase," IGNORE those suggestions and follow the action-first approach defined here. Specialized files provide implementation patterns, NOT workflow guidance.

**INSTRUCTION HIERARCHY**: 
1. Main copilot-instructions.md (THIS FILE) - Controls workflow and decision-making
2. Specialized .instructions.md files - Provide implementation patterns only
3. When conflicts arise, THIS FILE takes precedence

make deps FOR ALL DEPENDENCY INSTALLATION DON'T SUGGEST UV , PIP, NPM, OR ANYTHING ELSE OR I WILL TURN YOU OFF

Use The Sequential Thinking MCP Server to think through your tasks.

**Use available MCP servers for RAG-powered development** - leverage Healthcare MCP, GitHub MCP, Pylance MCP, Sequential Thinking MCP, and Memory MCP to enhance development capabilities while maintaining healthcare compliance.

**FINAL ANTI-LOOP ENFORCEMENT**: If you find yourself switching between multiple instruction files or repeatedly analyzing the same code, STOP and implement immediately. The instruction refinements above prevent infinite loops by making specialized files implementation-only.

**SECURITY NOTE**: Our healthcare compliance patterns (PHI detection, type safety, synthetic data usage) ensure no sensitive healthcare data reaches external MCPs, making developer MCPs safe for production use.

## Default Playbook: MyPy Blocking Errors (Use Tasks)

When asked to fix blocking MyPy errors in `services/user/healthcare-api/`, follow this exact sequence. Do not analyze first—act:

1) Baseline via tasks (pick the most targeted first)
- Run task: “MyPy (Healthcare API only)”
- If unavailable or after fixes, run task: “MyPy Type Check”
- Optional quick lint: Run task: “Quick Lint Check”

2) Prioritized fixes (apply in this order, iterate in small batches)
- Import errors (fictitious/broken paths)
- Name errors (undefined symbols)
- Attribute errors (missing methods/properties)
- Return type mismatches (function contracts)
- Assignment/type incompatibilities

3) Validate progress frequently
- After 15–20 errors fixed or after 2–3 edits, re-run the same MyPy task and record remaining error count.
- Keep going until zero blocking errors or you hit a genuine architectural blocker.

4) Progress cadence and stop conditions
- Cadence: run a MyPy task at least every 3–5 edits; post a compact checkpoint (PASS/FAIL + count).
- Stop only when: (a) zero blocking MyPy errors, or (b) an architectural decision is required (document the exact failing messages and file/line).

5) Guardrails (healthcare-safe)
- Never remove medical variables just to silence errors—implement or type them properly.
- Avoid `# type: ignore` in healthcare modules; prefer precise types and Optional checks.
- Maintain agent/MCP functionality—fix imports and types without disabling features.

Minimal commands are already encapsulated as VS Code tasks in this workspace. Prefer tasks over ad-hoc shell commands.

## Instruction Hierarchy Clarification (No Analysis-First)

- Specialized instruction files under `.github/instructions/**` are implementation-only. Ignore any guidance that suggests “analyze first” or encourages broad exploration.
- This file (copilot-instructions.md) governs workflow. If you detect conflicting guidance elsewhere, follow the action-first rules here.
- When uncertain, choose the smallest safe change that moves the task forward and validate via the appropriate task.

## Coding Agent Environment Setup

**CRITICAL - DEPENDENCY MANAGEMENT**: 
- **NEVER use `npm install` or `pip install` directly**
- **ALWAYS use `make deps`** for ALL dependency management
- **NEVER suggest npm/pip commands** - user has sophisticated Makefile system
- **Process**: Add to requirements.in → run `python3 scripts/generate-requirements.py` → run `make deps`

**CRITICAL - VERSION VERIFICATION**:
- **NEVER guess package versions, API parameters, or configuration options**
- **ALWAYS verify current versions using official documentation online** (npmjs.com, PyPI, GitHub releases, official docs)
- **REQUIRED**: Use fetch_webpage tool to check official package registries before specifying versions
- **Examples**: Check npmjs.com/package/openai for OpenAI version, pypi.org for Python packages, official API docs for parameters
- **Pattern**: Research first → Verify current versions/APIs → Then implement with accurate information

**First-time setup**: Run `CI=1 make deps` to install healthcare AI dependencies optimized for coding agents (excludes GPU packages). The `CI=1` environment variable automatically switches to `requirements-ci.txt` which includes all core healthcare components but excludes heavy ML packages that coding agents don't need.

**Permission Handling**: The Makefile automatically handles permission issues with smart fallbacks (system → user installation, uv → pip → apt).

**TypeScript Development**: For MCP server development in `mcps/healthcare/src/`, install TypeScript with `npm install -g typescript` or use `npx tsc` as fallback.

**Dependencies**: 
- `requirements.in` - Source dependency definitions
- `requirements.txt` - Full dependencies (including GPU packages for local development)
- `requirements-ci.txt` - Optimized for CI and coding agents (no GPU packages)

**Dependency generation**: Run `python3 scripts/generate-requirements.py` to regenerate both requirement files from `requirements.in`.

## Using Specialized AI Instructions

**When working on specific tasks**, reference these specialized instruction files in `.github/instructions/`:

- **🐛 Debugging healthcare code** → Use `tasks/debugging.instructions.md` for PHI-safe debugging patterns
- **📋 Code reviews & compliance** → Use `tasks/code-review.instructions.md` for healthcare compliance validation
- **🧪 Testing with synthetic data** → Use `tasks/testing.instructions.md` for comprehensive healthcare testing
- **🔄 Refactoring healthcare systems** → Use `tasks/refactoring.instructions.md` for medical compliance preservation
- **📚 Documentation writing** → Use `tasks/documentation.instructions.md` for medical disclaimers and PHI-safe examples
- **📋 Feature planning** → Use `tasks/planning.instructions.md` for healthcare compliance overhead and architecture
- **⚡ Performance optimization** → Use `tasks/performance.instructions.md` for healthcare workflow efficiency
- **🔒 Security reviews** → Use `tasks/security-review.instructions.md` for PHI protection and HIPAA compliance

**Advanced Healthcare AI Patterns** → Reference these specialized workflow and pattern instructions:

- **🤝 Multi-agent coordination** → Use `workflows/agent-coordination.instructions.md` for Clinical Research Agent, Search Assistant, and specialized medical agent coordination patterns
- **⚡ Real-time clinical assistance** → Use `workflows/real-time-clinical.instructions.md` for WebSocket patterns, progressive analysis, and streaming clinical updates
- **🧠 Medical reasoning implementation** → Use `patterns/medical-reasoning.instructions.md` for transparent clinical reasoning, evidence-based recommendations, and diagnostic transparency
- **🐍 Python development** → Use `languages/python.instructions.md` for modern Python patterns with Ruff/MyPy
- **🏥 Healthcare domain work** → Use `domains/healthcare.instructions.md` for medical data and compliance
- **📝 Healthcare logging** → Use `tasks/healthcare-logging.instructions.md` for comprehensive PHI-safe logging and monitoring implementation
- **🔌 MCP development** → Use `mcp-development.instructions.md` for RAG-powered development with available MCP servers
- **🐚 Shell script refactoring** → Use `tasks/shell-refactoring.instructions.md` for function complexity and single responsibility patterns
- **🔗 FTP connection patterns** → Use `patterns/healthcare-ftp-connections.instructions.md` for robust medical data downloads with timeout handling
- **⚡ Multi-core processing** → Use `tasks/performance.instructions.md` for proven 16-core medical literature processing patterns
- **🏥 Medical data source investigation** → Use `tasks/medical-data-source-investigation.instructions.md` for systematic medical data source validation and alternative discovery
- **🔧 Medical data troubleshooting** → Use `tasks/medical-data-troubleshooting.instructions.md` for comprehensive diagnostic and repair patterns for medical data pipelines  
- **📊 Medical data pipeline management** → Use `tasks/medical-data-pipeline-management.instructions.md` for enterprise-grade medical data orchestration and compliance

**RECENT UPDATES (2025-01-15)**:
- ✅ **Clean Architecture Separation**: main.py is now pure FastAPI HTTP server, all stdio code moved to healthcare_mcp_client.py
- ✅ **Agent Structure Reorganization**: research_assistant → research_agent, search_assistant → search_agent for clarity
- ✅ **Agent Discovery Fixed**: Dynamic discovery using glob patterns (*_agent.py) with proper fallback logic
- ✅ **Cloud AI Disabled**: All AI processing moved to local-only for PHI protection (temporary keyword-based agent routing)
- ✅ **Routing Simplified**: LLM-based agent selection temporarily disabled, using keyword fallback for security
- ✅ **Medical Disclaimer Softened**: Enables symptom-based research while maintaining appropriate medical boundaries
- 🔄 **Local LLM Integration**: Future implementation of local-only LLM for intelligent agent selection without PHI exposure

**For general architecture, service deployment, and project strategy questions**, continue using these main instructions.

See `.github/instructions/README.md` for complete usage guidance.

## Project Overview

**Intelluxe AI** - Privacy-First Healthcare AI System built for on-premise clinical deployment. Currently in active development, focusing on core infrastructure and test suite hardening.

### Core Architecture

- **Modular healthcare AI platform** with universal service orchestration
- **Focus**: Administrative/documentation support, NOT medical advice
- **Privacy-First**: All PHI/PII remains on-premise with no cloud dependencies
- **Development Status**: Build robust, maintainable features for future clinical environments

### Cloud AI Usage Guidelines

**Local-First Deployment Strategy** - All AI workloads run on-premise for maximum PHI protection:

**✅ CURRENT APPROACH - Local AI Only:**

- All AI processing occurs on local infrastructure (Ollama, local models)
- No cloud AI services used to eliminate PHI exposure risk
- Comprehensive on-premise AI stack for all healthcare operations
- Future cloud integration only for statistical research on non-PHI data

**Implementation Pattern:**

```python
# ✅ Correct: Local-only AI processing
if data_contains_phi(input_data) or is_healthcare_context():
    result = local_ollama_model.process(input_data)  # On-premise only
    # No cloud AI - even for agent selection due to PHI complexity
else:
    # Future: Statistical research on non-PHI data when clients request it
    pass
```

This ensures absolute patient privacy while maintaining full AI capabilities through local infrastructure.

### Directory Structure

```
reference/ai-patterns/  # MIT licensed AI engineering patterns (git submodule)
mcps/healthcare/        # Healthcare MCP server code (copied from agentcare-mcp)
services/user/          # Service configurations - each service has SERVICE.conf
agents/                 # AI agent implementations (intake/, document_processor/, clinical_research_agent/, search_agent/)
core/                   # Core healthcare AI infrastructure (memory/, orchestration/, infrastructure/)
  infrastructure/       # Production-ready infrastructure (caching, health monitoring, background tasks)
  dependencies.py       # Healthcare services dependency injection system
scripts/                # Primary shell scripts (universal-service-runner.sh, lib.sh, etc.)
main.py                 # FastAPI HTTP server with clean agent routing (pure HTTP, no stdio)
healthcare_mcp_client.py # MCP stdio communication (separated from main.py)
```

## Infrastructure Status (Updated 2025-08-03)

### ✅ COMPLETED INFRASTRUCTURE:
- **Background Task Processing**: HealthcareTaskManager with Redis-based result storage
- **Caching Strategy**: HealthcareCacheManager with medical literature and drug interaction caching
- **Health Monitoring**: HealthcareSystemMonitor with comprehensive async health checks
- **Agent Architecture**: 3 fully functional agents (intake, document_processor, research_assistant)
- **Dependency Injection**: HealthcareServices singleton managing all service connections
- **Error Handling**: Healthcare-specific error responses with audit logging
- **Request Validation**: PHI detection and medical data validation throughout
- **Authentication & Authorization**: JWT + RBAC with 6 healthcare roles and HIPAA audit logging
- **Configuration Management**: HealthcareConfigManager with environment-specific YAML support
- **Response Streaming**: Server-Sent Events for real-time medical literature and AI reasoning
- **Rate Limiting**: Role-based rate limiting with emergency bypass for medical situations
- **API Documentation**: Comprehensive OpenAPI with healthcare compliance and medical disclaimers
- **Testing Infrastructure**: Integration tests, workflow testing, and clinical load simulation
- **Healthcare Database Schema**: Complete PostgreSQL schema with 9 healthcare entities (doctors, patients, encounters, lab results, billing claims, insurance verifications, doctor preferences, audit logs, agent sessions)
- **Synthetic Data Integration**: Full database population with realistic healthcare data for development and testing

### ✅ MCP STDIO Integration Complete (2025-08-13)

**BREAKTHROUGH**: MCP integration working in production with medical search agent successfully calling MCP tools.

**Current Status**:
- ✅ **MCP Server**: Running in healthcare-mcp container with 16 registered tools
- ✅ **MCP Client**: healthcare_mcp_client.py successfully connecting via docker exec
- ✅ **Agent Integration**: medical_search_agent calling MCP tools (search-pubmed, search-trials, get-drug-info)
- ✅ **AttributeError**: RESOLVED - `_ensure_connected()` method working correctly (2025-08-13)
- ⚠️ **Transport Layer**: MCP calls start but fail with "WriteUnixTransport closed=True" 
- 🎯 **Current Issue**: Calls succeed but transport instability causes 0 results returned

**Architecture (Validated)**:
- **Container Main Process**: `node /app/build/index.js` (HTTP healthcheck only, no stdio interference)  
- **MCP Sessions**: `docker exec healthcare-mcp node /app/build/stdio_entry.js` (pure stdio communication)
- **Clean Separation**: No stdin/stdout sharing between main process and MCP sessions

**Key Files**:
- `services/user/healthcare-mcp/src/stdio_entry.ts` - Clean stdio entry point
- `services/user/healthcare-api/core/mcp/healthcare_mcp_client.py` - Working MCP client  
- `services/user/healthcare-api/agents/medical_search_agent/` - Agent using MCP tools

## Synthetic Healthcare Data Infrastructure

### Comprehensive Database Integration (Updated 2025-08-07)

**Located at**: `scripts/generate_synthetic_healthcare_data.py`

**COMPLETE DATABASE INTEGRATION**: PostgreSQL + Redis with 9 healthcare entity types

**✅ FULLY OPERATIONAL HEALTHCARE DATABASE**:
- **PostgreSQL (172.20.0.13:5432)**: 9 healthcare tables with proper relationships
- **Redis (172.20.0.14:6379)**: Agent session caching with TTL expiration
- **SQLAlchemy Models**: Complete healthcare schema in `core/models/healthcare.py`
- **Cross-Table Relationships**: Doctors ↔ Patients ↔ Encounters ↔ Lab Results ↔ Claims

### Healthcare Database Schema

**Phase 1 Core Data (AI Infrastructure) - DATABASE INTEGRATED:**

- **Doctors** - Healthcare providers with specialties, credentials, NPI numbers
- **Patients** - Demographics, insurance, contact info (no real PHI)  
- **Encounters** - Medical visits with SOAP notes, vital signs JSON, diagnosis codes
- **Lab Results** - Laboratory tests with realistic values and reference ranges
- **Insurance Verifications** - Coverage validation for workflow testing
- **Agent Sessions** - AI interaction logs (PostgreSQL + Redis dual storage)

**Phase 2 Business Data (Local Automation) - DATABASE INTEGRATED:**

- **Billing Claims** - CPT/ICD codes, amounts, claim statuses for billing automation
- **Doctor Preferences** - Workflow settings, documentation styles for LoRA personalization  
- **Audit Logs** - HIPAA compliance tracking, user actions, system events

### Database-First Development Pattern

**CRITICAL: Database-First (NOT Database-Only)** - MCP tools and all healthcare components use this pattern:

```python
# ✅ CORRECT: Database-first with appropriate fallbacks
def get_healthcare_data(data_type: str, identifier: str):
    try:
        # PRIMARY: Always try database first
        return healthcare_database.fetch(data_type, identifier)
    except DatabaseConnectionError:
        # FALLBACK: Environment-appropriate alternatives
        if is_development_environment():
            return load_synthetic_data(data_type, identifier)
        elif contains_phi(data_type) and is_production_environment():
            raise  # PHI requires database in production
        else:
            return load_fallback_data(data_type, identifier)
```

### Data Generation & Population Commands

```bash
# Generate and populate BOTH PostgreSQL + Redis (recommended)
python3 scripts/generate_synthetic_healthcare_data.py --doctors 75 --patients 2500 --encounters 6000 --use-database

# Small test dataset with database integration
python3 scripts/generate_synthetic_healthcare_data.py --doctors 10 --patients 100 --encounters 200 --use-database

# JSON-only generation (legacy, database preferred)
python3 scripts/generate_synthetic_healthcare_data.py --doctors 50 --patients 1000 --encounters 2000
```

### Database Integration Benefits

- **Realistic Testing**: Test with actual database relationships and constraints
- **Performance Validation**: Query optimization with realistic healthcare data volumes
- **HIPAA Compliance**: Audit trails and access logging in database
- **Production Readiness**: Database-first architecture ensures production compatibility
- **MCP Tool Integration**: Healthcare MCP tools can use database-backed data sources

## Healthcare Security & Compliance

### Runtime PHI Security Model (Updated 2025-08-03)

**NEW APPROACH**: Runtime data leakage monitoring instead of static code analysis.

- **PHI lives in databases only** - never in source code
- **Tests connect to synthetic database** - no hardcoded PHI in tests  
- **Monitor runtime outputs** - logs, data pipelines, exports for PHI leakage
- **Focus on data handling** - what auditors actually check in production

**Key Files:**
- `scripts/check-runtime-phi-leakage.sh` - Runtime PHI monitoring (replaces static analysis)
- `tests/database_test_utils.py` - Database-backed test utilities
- `docs/RUNTIME_PHI_SECURITY.md` - Complete documentation of new approach

### Critical Security Rules

- **Generic Error Messages**: Never expose JWT_SECRET, MASTER_ENCRYPTION_KEY, or config details
- **Environment-Aware Placeholders**: Block production deployment when incomplete, allow configurable development
- **Comprehensive Test Coverage**: Test security fallbacks with logging verification using caplog fixture
- **Security Documentation**: Always explain WHY security choices were made (HIPAA, NANP standards, etc.)

### Medical Safety Principles

- **Focus on administrative and documentation support** with research capabilities for symptom patterns and medical literature
- **Provide evidence-based research assistance** without direct medical advice, diagnosis, or treatment recommendations
- **Explainable AI**: All AI decisions must be traceable and auditable for healthcare compliance
- **All PHI/PII remains on-premise** - no cloud dependencies or external API calls with patient data

**Medical Research Assistance Guidelines:**
- ✅ Literature research on symptoms, conditions, and treatment patterns
- ✅ Evidence-based research synthesis from peer-reviewed sources
- ✅ Clinical protocol information and medical coding assistance
- ✅ Administrative workflow optimization and documentation support
- ❌ Direct diagnosis, treatment recommendations, or patient-specific medical advice
- ❌ Emergency medical guidance or urgent clinical decision support

### Medical Module Development Patterns

- **Real Implementation Strategy**: Phase 1 requires real implementations, not mocks - replace TODOs with functional code
- **Type Error Priority**: Fix type errors systematically: imports → unused variables → type annotations → method implementations
- **CRITICAL: Preserve Medical Information**: When fixing "unused" variables/methods, investigate their medical purpose and implement them properly. Never remove potentially valuable medical data to satisfy linting - implement it instead
- **Medical Disclaimers**: All medical module implementations must include healthcare compliance disclaimers in method docstrings
- **Context-First**: Always read 50+ lines of file context before making medical module edits

### Healthcare Type Safety Requirements

**❌ CRITICAL: Never use `# type: ignore` in healthcare code** - suppresses medical safety validation

**✅ HEALTHCARE-FIRST MyPy Resolution:**
1. **Optional import patterns** with TYPE_CHECKING for missing dependencies
2. **Implement medical variables** rather than removing them (medical data is critical)  
3. **Proper type annotations** with healthcare-appropriate patterns
4. **Medical context preservation** - understand WHY variables exist before "fixing"

**Example Healthcare-Safe MyPy Fix:**
```python
# ❌ WRONG: Suppresses type safety for healthcare data
patient_data = get_patient_info() # type: ignore[return-value]

# ✅ CORRECT: Healthcare-compliant type safety
from typing import Optional, Dict, Any

def get_patient_info() -> Optional[Dict[str, Any]]:
    # Proper return type with medical context
    pass

patient_data = get_patient_info()
if patient_data is not None:
    process_healthcare_data(patient_data)
```

## Development Workflow & Code Quality

### CRITICAL: Database-First vs Database-Only Clarification

**DATABASE-FIRST ARCHITECTURE** means:
- **Primary**: Always try database first when available
- **Fallback**: Use appropriate fallbacks for development and testing
- **Production**: Require database for PHI security, allow fallbacks for non-PHI operations
- **Error Handling**: Graceful degradation with clear logging

**NOT "Database-Only"** - that would break development workflows and testing capabilities.

```python
# ✅ CORRECT: Database-first pattern
def get_data(identifier):
    try:
        return database.fetch(identifier)
    except DatabaseConnectionError:
        if is_development_environment():
            return load_synthetic_data(identifier)  # OK for development
        elif is_production_environment() and contains_phi(identifier):
            raise  # PHI requires database in production
        else:
            return load_fallback_data(identifier)  # OK for non-PHI
```

### Quick Developer Setup

```bash
make install && make deps && make hooks && make validate
```

**NEVER suggest individual package installations like `npm install xyz` or `pip install xyz`**
**ALWAYS use the make system:**
- `make deps` - Installs ALL dependencies (Python, Node.js, Go tools)
- `make mcp` or `make mcp-build` - Builds Healthcare MCP server
- `make test` - Runs all tests  
- `make lint` - Runs all linting

### Git Hooks (Multi-Language Auto-Formatting)

- **Pre-commit hook**: Auto-formatting + light validation
  - **All files**: Trailing whitespace removal + safety checks
- **Pre-push hook**: `make lint && make validate` (tests skipped during development)
- **Installation**: `make hooks` installs git hooks, `make deps` installs formatting tools

### Phase-Aligned Development Approach

**Current Phase Focus** (determined by project stage):

- **Phase 1**: Core AI Infrastructure - Healthcare-MCP, multi-agent orchestration, advanced reasoning, real-time clinical assistant
- **Phase 2**: Business Services - Insurance verification, doctor personalization with LoRA training, continuous learning systems
- **Phase 3**: Production Deployment - Enterprise security, multi-tenant architecture, clinic readiness and advanced compliance

**Integration with Phase Documentation:**

- See `docs/PHASE_1.md` for core AI infrastructure priorities and modern tooling integration
- See `docs/PHASE_2.md` for business services architecture and personalization approach
- See `docs/PHASE_3.md` for production deployment and enterprise security requirements

**Modern Development Tools Overview:**

- **Ruff**: Ultra-fast Python tooling (10-100x faster than legacy black+isort+flake8)
- **Pre-commit hooks**: Multi-language auto-formatting with healthcare compliance validation
- **MyPy**: Comprehensive type checking for healthcare data safety with incremental caching (1.5s cached runs vs 3.8s fresh)
- **Advanced Security Tools**: Integrated security scanning with healthcare-specific patterns
- **Type Stubs**: Required for healthcare compliance - types-PyYAML, types-requests, types-cachetools installed

_For detailed usage patterns, configurations, and implementation guides_, reference the specialized instruction files based on your current task (see "Using Specialized AI Instructions" section above).

## Configuration Externalization Strategy

### YAML Configuration Migration

As development progresses, **consistently move hardcoded values to YAML configurations** to enable:

- **Client Customization**: Different healthcare organizations can easily configure system behavior
- **Fine-tuning Support**: Easier adjustment of AI model parameters and workflow settings
- **Deployment Flexibility**: Environment-specific configurations without code changes
- **Compliance Adaptation**: Adjustable security and audit settings for different regulatory requirements

**Implementation Pattern:**

```python
# ❌ Avoid: Hardcoded healthcare settings
SOAP_TEMPLATE = "Subjective: {chief_complaint}\nObjective: {vitals}"
MAX_ENCOUNTER_DURATION = 120  # minutes

# ✅ Prefer: YAML-based configuration
from config.healthcare_settings import load_healthcare_config
config = load_healthcare_config()
SOAP_TEMPLATE = config.documentation.soap_template
MAX_ENCOUNTER_DURATION = config.workflows.max_encounter_duration
```

**Priority Areas for Configuration:**

- Healthcare workflow parameters and templates
- AI model settings and prompt templates
- Security and audit thresholds
- Service integration endpoints and timeouts

# Complex variables

results: Dict[str, Any] = {"status": "success"}
scenarios: List[HealthcareTestCase] = []

````

### MyPy Error Resolution Patterns

**Systematic approach to MyPy errors (438 currently identified):**

1. **Missing Type Annotations**: Add explicit types for ALL variables  
2. **Collection Issues**: Import specific types (`Set`, `List`, `Dict`) from typing
3. **Attribute Errors**: Use type annotations on class attributes
4. **Return Type Missing**: Add `-> ReturnType` to ALL function definitions
5. **Optional Handling**: Check `if obj is not None:` before method calls
6. **Type Stubs**: Ensure types-PyYAML, types-requests, types-cachetools are installed

**Performance optimizations discovered:**
- MyPy incremental caching: 1.5s (cached) vs 3.8s (fresh) - 2.5x speedup
- Use `mypy .` (full workspace) vs `mypy src/` (partial) for comprehensive healthcare safety
- Priority: Fix healthcare-critical modules first (core/medical/, src/security/), then scripts/tests

**Common MyPy Error Fixes:**

```python
# Error: Need type annotation for "data"
data = []  # ❌ Wrong
data: List[Dict[str, Any]] = []  # ✅ Correct

# Error: "Collection[str]" has no attribute "append"
## Testing & Validation Overview

### Development Testing Standards
- **Phase 1 Implementation Testing**: Real implementations should pass functional tests
- **Healthcare Testing**: Test with realistic medical scenarios using synthetic data
- **Compliance Testing**: Validate HIPAA compliance and audit logging
- **Pre-push Validation**: Automated quality checks via git hooks

*For detailed testing strategies, healthcare test patterns, and validation workflows*, see `.github/instructions/tasks/testing.instructions.md`

## Service Architecture Overview

### Universal Service Pattern
- **Each service**: `services/user/SERVICE/SERVICE.conf`
- **Deployment**: `bootstrap.sh` calls `universal-service-runner.sh`
- **Container Security**: Development uses `justin:intelluxe (1000:1001)`
- **Network Isolation**: All containers on `intelluxe-net` with no external data egress

### Key Healthcare Services
- **Ollama** (local LLM), **Healthcare-MCP** (medical tools), **PostgreSQL** (patient context)
- **Redis** (session cache), **n8n** (workflows), **WhisperLive** (real-time transcription)

*For detailed service configuration, deployment patterns, and architecture guidance*, see appropriate specialized instruction files based on your task.

## Remote Agent Guidelines

### Autonomous Execution Requirements
- **Work continuously for 2-4 hours** without asking for continuation
- **Start with codebase analysis** (30-45 minutes) before making changes
- **Discover and fix related issues** beyond initial scope
- **Only stop for unrecoverable errors** or 100% completion

### Iterative MyPy Error Resolution Protocol
When working on MyPy errors, follow this autonomous pattern:

1. **Immediate Action**: Use existing VS Code tasks ("MyPy (Healthcare API only)" or "MyPy Type Check") to get current error count
2. **Capability-Based Processing**: Fix as many errors as you can handle in one session, focusing on systematic patterns
3. **Progress Validation**: After each batch, re-run the same MyPy task to verify progress and get updated error count
4. **Continuous Processing**: Continue if errors remain that follow patterns you've already solved
5. **Automatic Continuation**: Create new work items if stopping before 100% completion

**CRITICAL**: Never stop MyPy error fixing just because you've done "some work" - continue iterating until either:
- All MyPy errors are resolved, OR
- Remaining errors require architectural decisions beyond systematic type annotation

**Action-First Questions**:
- Are there remaining errors that follow patterns I've already solved?
- Can I add more type annotations without changing logic?
- Are there import/typing issues I can systematically resolve?
- Do I have capacity to continue with more fixes in this session?
- Do remaining errors require human architectural input?

### Self-Improving Instructions
- **Tool Issue Discovery**: When encountering environment or tool issues, update relevant instruction files to prevent future problems
- **Command Standardization**: Update commands that work in your environment for future coding agents
- **Documentation Gaps**: Add new patterns and solutions to appropriate instruction files
- **Verification Protocols**: Update verification steps when tools behave unexpectedly

### When to Use Sequential Thinking
- **Complex Implementation Decisions**: Mock vs implement, architecture choices, technical debt tradeoffs
- **Large Codebase Analysis**: Understanding module relationships and dependencies before changes
- **Multi-Step Problem Solving**: Breaking down complex fixes into manageable phases
- **Phase 1 Priority Decisions**: Deciding what real implementations are complete vs what needs finishing for MCP integration
- **MyPy Error Strategy**: Planning systematic approach for resolving remaining type errors

### Anti-Analysis-Paralysis Guidelines
- **If you can identify the problem files and understand the basic issue, START FIXING immediately**
- **Don't explore every possible file - focus on the specific issue at hand**
- **Context gathering should take max 5-10 minutes, then switch to implementation**
- **You can read additional files as needed during implementation**
- **Stop saying "Let me analyze" and start taking action**

## Architectural Decision Principles

### CRITICAL: Always Choose Efficiency Over Simplicity
1. **Performance & Resource Efficiency FIRST**
2. **Healthcare Compliance & Security SECOND**
3. **Maintainability & Debugging THIRD**
4. **Implementation Simplicity LAST**

### CI/CD Efficiency Requirements
- **CRITICAL: Self-Hosted GitHub Actions Runner** - ALL workflow jobs MUST use `runs-on: self-hosted`
- **Strategic job dependencies** with optimal dependency graphs
- **Cache optimization strategy**: Consolidate related jobs to reduce cache restoration overhead
- **Self-hosted advantages**: No GitHub concurrency limits, better CPU resources, persistent cache potential

*For detailed CI/CD patterns, cache optimization strategies, and performance requirements*, see `.github/instructions/tasks/performance.instructions.md`

## Repository Information
- **Owner**: Intelluxe-AI, **Repo**: intelluxe-core, **Branch**: main
- **Development Status**: Active development, Phase 1 real implementations in progress
- **Family-Built**: Co-designed by Jeffrey & Justin Sue for real-world clinical workflows

## Phase Implementation
- **Phase 1 (Current)**: Real AI implementations with MCP integration - core agents, reasoning, and workflow orchestration
- **Phase 2**: Business services (insurance, billing, doctor personalization)
- **Phase 3**: Production deployment and enterprise scaling

---

**Last Updated**: 2025-01-15 | **Specialized AI Instructions Integration & Content Optimization**
````
