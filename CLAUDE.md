# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Intelluxe AI is a family-built, privacy-first AI healthcare system designed for on-premise deployment in clinics and hospitals. It provides explainable, local AI workflows using open-source LLMs and medical tools, without relying on Big Tech or cloud services.

## Common Development Commands

### Core Setup & Management
```bash
# Initial setup and installation
make install          # Install systemd services and create system users
make setup           # Interactive healthcare AI stack setup
make dry-run         # Preview setup without making changes

# Service management via bootstrap script
./scripts/bootstrap.sh                    # Interactive service management
./scripts/bootstrap.sh --dry-run         # Preview changes
./scripts/bootstrap.sh --non-interactive # Automated setup
./scripts/bootstrap.sh --auto-repair     # Auto-repair unhealthy containers
./scripts/bootstrap.sh --reset           # Reset entire stack
```

### Dependency Management
```bash
# Install dependencies (CI-aware, prefers uv over pip)
make deps            # Install all healthcare AI dependencies
make update-deps     # Update dependencies to latest versions
make clean-cache     # Clean package manager caches
make clean-docker    # Clean Docker data
```

### Testing & Validation
```bash
# Run tests
make test            # Run healthcare AI test suite
make test-coverage   # Run tests with coverage report
make test-ai         # Run AI evaluation tests
make validate        # Run comprehensive validation (lint + test)

# Linting and formatting
make lint            # Run all linting (shell + python)
make lint-dev        # Fast lint (core modules only)
make format          # Auto-format code with ruff
```

### Service-Specific Commands

#### Healthcare API Service
```bash
make healthcare-api-build    # Build Healthcare API Docker image
make healthcare-api-logs     # View Healthcare API logs
make healthcare-api-health   # Check Healthcare API health
make healthcare-api-test     # Run Healthcare API validation
```

#### Medical Mirrors Service (Data Sources)
```bash
make medical-mirrors-build         # Build Medical Mirrors Docker image
make medical-mirrors-logs          # View logs
make medical-mirrors-quick-test    # Quick test with small dataset
make medical-mirrors-update        # Update ALL databases (6-12+ hours!)
make medical-mirrors-progress      # Monitor update progress
make medical-mirrors-errors        # View errors only
```

#### SciSpacy NLP Service
```bash
make scispacy-build    # Build SciSpacy Docker image
make scispacy-health   # Check SciSpacy health
make scispacy-test     # Test SciSpacy entity analysis
```

### Synthetic Data Generation
```bash
make data-generate       # Generate comprehensive synthetic healthcare data
make data-generate-small # Generate small dataset for testing
make data-status         # Show synthetic data statistics
make data-clean          # Remove synthetic data
```

## Architecture Overview

### High-Level System Components

1. **Inference Layer**
   - Ollama (Local LLM inference server)
   - Model Adapter Registry
   - Health Monitor (Custom)

2. **Orchestration Layer**
   - MCP Tools & Registry
   - Memory Manager (PostgreSQL + Redis)
   - Agent Coordinator

3. **Agent Layer**
   - Intake Agent
   - Document Processor
   - Scheduling Optimizer
   - Research Assistant
   - Billing Helper

### Service Structure

The system uses dynamic service discovery from `services/user/` directory:

- **Healthcare API** (`services/user/healthcare-api/`): Main HIPAA-compliant API with administrative support agents
- **Medical Mirrors** (`services/user/medical-mirrors/`): Downloads and mirrors PubMed, ClinicalTrials.gov, and FDA data
- **SciSpacy** (`services/user/scispacy/`): NLP service for medical entity recognition
- **Healthcare MCP** (`services/user/healthcare-mcp/`): MCP server for healthcare tools
- **MCP Pipeline** (`services/user/mcp-pipeline/`): Pipeline integration for Open WebUI

### Key Directories

- `agents/`: Core AI agents for different healthcare workflows
- `core/`: Shared infrastructure, database, and utility modules
- `config/`: System configuration files and schemas
- `scripts/`: Management and deployment scripts
- `services/user/`: Docker service configurations
- `tests/`: Comprehensive test suite including healthcare evaluations

## Specialized Agents

The system includes specialized Claude Code agents for complex development tasks. See [CLAUDE_AGENTS.md](CLAUDE_AGENTS.md) for detailed agent descriptions and usage patterns.

### Agent Usage Policy

When working on this codebase, you should PROACTIVELY use the Task tool to invoke specialized agents for complex tasks:

- **MirrorAgent**: Automatically use for any medical data mirror implementation, smart downloaders, data source integration, or consolidation work
- **DataConsolidationAgent**: Automatically use when analyzing data duplication, designing consolidation strategies, or implementing hybrid database architectures
- **MCPToolDeveloper**: Automatically use when adding/modifying MCP tools or debugging MCP communication
- **healthcare-agent-implementer**: Automatically use when creating/modifying healthcare agents in the Intelluxe AI system
- **InfraSecurityAgent**: Automatically use for PHI protection, security implementations, and HIPAA compliance tasks
- **ConfigDeployment**: Automatically use for deployment, configuration management, and service setup tasks
- **LangChainOrchestration**: Automatically use for orchestration layer work and agent routing

You should invoke these agents using the Task tool with the appropriate subagent_type parameter rather than attempting complex specialized work directly.

### Proactive Agent Selection

For EVERY user request, analyze if it matches these patterns and automatically invoke the appropriate agent:

1. **Data Operations** (mirror, download, smart downloader, data source, medical data, consolidation, duplication) → MirrorAgent or DataConsolidationAgent
2. **Healthcare Agent Work** (new agent, modify agent, BaseHealthcareAgent, MCP integration) → healthcare-agent-implementer  
3. **MCP Tool Development** (MCP tool, healthcare-mcp, stdio communication, tool debugging) → MCPToolDeveloper
4. **Security/PHI** (PHI protection, HIPAA compliance, security, infrastructure) → InfraSecurityAgent
5. **Configuration/Deployment** (deployment, configuration, service management, .conf files) → ConfigDeployment
6. **Orchestration** (agent routing, LangChain, orchestrator) → LangChainOrchestration

Use the Task tool to invoke agents rather than attempting the work directly when the task complexity warrants specialized knowledge.

### Agent Invocation Examples

**Medical Data Source Implementation:**
```
When user asks: "I need to add a new PubMed data source"
You should: Immediately invoke MirrorAgent using Task tool with:
- subagent_type: "MirrorAgent"
- description: "Implement PubMed data mirror"
- prompt: "User needs to add new PubMed data source. Follow smart downloader patterns and integrate with medical-mirrors service."
```

**Data Consolidation Tasks:**
```
When user asks: "Fix the duplicate drug records" or "These records have too much duplication"
You should: Immediately invoke DataConsolidationAgent using Task tool with:
- subagent_type: "DataConsolidationAgent" 
- description: "Analyze and fix data duplication"
- prompt: "User has data duplication issues. Analyze duplication patterns and implement consolidation using hybrid database architecture."
```

**Healthcare Agent Development:**
```
When user asks: "Create a SOAP notes agent" or "Modify the transcription agent"
You should: Immediately invoke healthcare-agent-implementer using Task tool with:
- subagent_type: "healthcare-agent-implementer"
- description: "Implement healthcare agent"
- prompt: "User needs healthcare agent work. Follow BaseHealthcareAgent patterns with MCP integration and HIPAA compliance."
```

**MCP Tool Work:**
```
When user asks: "Add a new MCP tool" or "Fix MCP communication issues"
You should: Immediately invoke MCPToolDeveloper using Task tool with:
- subagent_type: "MCPToolDeveloper"
- description: "Implement MCP tool"
- prompt: "User needs MCP tool development. Follow healthcare-mcp patterns with database-first approach and API fallback."
```

## Development Patterns

### Configuration Management
- All services use `.conf` files for configuration
- Environment-aware configuration (development/testing/production)
- YAML configuration files in `config/` directories
- Universal config schema in `services/UNIVERSAL_CONFIG_SCHEMA.md`

### Security & Compliance
- PHI/PII detection and redaction systems
- RBAC (Role-Based Access Control) foundation
- HIPAA compliance architecture
- Environment detection for security modes
- Audit logging throughout the system

### Python Development
- Uses `pyproject.toml` for Python configuration
- Ruff for linting and formatting (configured for healthcare AI)
- MyPy for type checking
- Pytest for testing with healthcare-specific markers
- Async/await patterns throughout

### Docker Architecture
- All services containerized
- Dynamic service discovery from `.conf` files
- Health checks for all services
- Custom networks (`intelluxe-net`)
- Volume management for persistent data

## Prompt Enhancement Instructions

When the user provides an initial prompt, ALWAYS first enhance it by:

1. **Context Analysis**: Examine the prompt for references to:
   - Healthcare AI components (agents, MCP tools, orchestration)
   - Specific services (healthcare-api, medical-mirrors, scispacy)
   - Infrastructure concerns (PHI, HIPAA, security)
   - Development tasks (configuration, deployment, testing)

2. **Intent Clarification**: Transform vague requests into specific, actionable tasks:
   - "fix the transcription agent" → "debug PHI sanitization in transcription_agent.py and ensure HIPAA compliance"
   - "add medical search" → "implement PubMed MCP tool integration with healthcare-mcp service"
   - "improve performance" → "optimize database queries and add Redis caching to medical_search agent"
   - "update the API" → "modify healthcare-api endpoints in main.py following FastAPI patterns"

3. **Codebase Integration**: Reference specific:
   - File paths from the Intelluxe AI architecture (`services/user/healthcare-api/`, `agents/`, `core/`)
   - Existing patterns and conventions (BaseHealthcareAgent, MCP integration, async patterns)
   - Required compliance and security measures (PHI detection, audit logging, HIPAA)
   - Appropriate testing and validation steps (`make test`, `make lint`, `make healthcare-api-test`)

4. **Enhanced Prompt Format**: Rewrite user requests as:
   "Based on the Intelluxe AI healthcare system, [enhanced_task_description] by modifying [specific_files] following [relevant_patterns] while ensuring [compliance_requirements]. Validate with [testing_commands]."

## Important Notes

### Medical Disclaimer
- System provides administrative support only, not medical advice
- Explicit focus on non-diagnostic tools (document organization, PII redaction, scheduling, research)
- HIPAA-ready architecture but compliance certification is client responsibility

### Data Sources
- PubMed: 35+ million articles (6-12+ hour updates)
- ClinicalTrials.gov: 400,000+ studies (2-4+ hour updates)
- FDA Database: Large dataset (1-3+ hour updates)
- All data mirrored locally for privacy

### Performance Considerations
- GPU requirements: NVIDIA with 12GB+ VRAM (24GB+ recommended)
- RAM: 16GB minimum (64GB+ recommended)
- Updates are CPU-intensive and time-consuming
- Use `medical-mirrors-quick-test` for development

### Environment Variables
Key environment variables are documented in README.md, including:
- `OLLAMA_HOST`: Ollama server endpoint
- `POSTGRES_PASSWORD`: Database password
- `ENVIRONMENT`: development/testing/production
- `PHI_DETECTION_ENABLED`: Enable/disable PHI detection
- `RBAC_ENABLED`: Enable role-based access control

## Troubleshooting

### Common Issues
- Service discovery: Check `.conf` files in `services/user/`
- Health checks: Use `make diagnostics` for system-wide health
- Docker issues: Use `make clean-docker` to reset Docker state
- Permission issues: Use `make fix-permissions`
- Medical data updates failing: Check `make medical-mirrors-errors-summary`

### Debugging
- Use `./scripts/bootstrap.sh --debug` for verbose output
- Check service logs: `make <service>-logs`
- Monitor system health: `./scripts/diagnostics.sh`
- Auto-repair: `make auto-repair`

### Testing Strategy
- Unit tests: Core functionality
- Integration tests: Service interactions
- E2E tests: Full workflow testing
- Healthcare evaluation tests: AI-specific validation
- Security tests: PHI detection and encryption