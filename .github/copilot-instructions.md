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
  - Sets up Docker, Ollama, AgentCare-MCP, PostgreSQL, Redis with medical-grade security
- **`universal-service-runner.sh`** - Universal service runner
  - Deploys ANY Docker service from pure configuration
  - Handles healthcare AI services (Ollama, AgentCare-MCP, etc.)
- **`config_web_ui.py`** - Healthcare-focused web interface
  - AI system management with service health monitoring
  - Medical service icons and healthcare-specific UI
- **`lib.sh`** - Common utility functions for Intelluxe AI healthcare operations

### Directory Structure
```
vendor/                 # Source code for third-party services (git submodules like healthcare-mcp)
services/user/          # Runtime configurations (.conf files) for all services
agents/                 # AI agent implementations (intake/, document_processor/, research_assistant/, billing_helper/, scheduling_optimizer/)
core/                   # Core healthcare AI infrastructure (memory/, orchestration/, models/, tools/)
data/                   # AI training and evaluation data management (training/, evaluation/, vector_stores/)
infrastructure/         # Healthcare deployment configs (docker/, monitoring/, security/, backup/)
docs/                   # Comprehensive healthcare AI documentation including phase guides
reference/ai-patterns/  # MIT licensed AI engineering patterns for healthcare adaptation (git submodule)
```

## AI Engineering Patterns

### Reference Library
- **`reference/ai-patterns/`** - MIT licensed AI engineering patterns adapted for healthcare
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
- **AgentCare-MCP** (medical tools)
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
- **Creates .conf files directly** using universal service runner format
- **Never calls legacy scripts**
- **Implements modern service addition**

### Service Configurations
- **Universal key=value format** supporting all Docker features
- **See `UNIVERSAL_CONFIG_SCHEMA.md`** for specification
- **No legacy code**: No plugin.sh files, no add-service.sh references

## Development Principles

1. **Healthcare-first**: Build robust, maintainable features for future clinical environments, but defer production-specific hardening until later phases
2. **Privacy-by-design**: PHI/PII never leaves the local network or gets stored inappropriately
3. **Explainable AI**: Every AI decision must be traceable and auditable for medical compliance
4. **Modular architecture**: Agents, tools, and services can be customized per clinic without breaking core system
5. **Performance-critical**: Real-time AI inference suitable for busy clinical workflows
6. **Family-built philosophy**: Designed by healthcare family (Jeffrey & Justin Sue) for real-world clinical challenges

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
