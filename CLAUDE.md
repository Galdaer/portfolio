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
- **TestAutomationAgent**: Automatically use for test writing, test automation, creating unit/integration tests, test coverage, and generating test scenarios
- **TestOrganizationAgent**: Automatically use for organizing tests, test structure optimization, test refactoring, and test maintenance
- **HealthcareTestAgent**: Automatically use for HIPAA testing, PHI testing, healthcare compliance, medical workflow testing, and healthcare evaluation
- **TestMaintenanceAgent**: Automatically use for test failures, flaky tests, test debugging, test optimization, and test performance issues

You should invoke these agents using the Task tool with the appropriate subagent_type parameter rather than attempting complex specialized work directly.

### Proactive Agent Selection

For EVERY user request, analyze if it matches these patterns and automatically invoke the appropriate agent:

1. **Data Operations** (mirror, download, smart downloader, data source, medical data, consolidation, duplication) → MirrorAgent or DataConsolidationAgent
2. **Healthcare Agent Work** (new agent, modify agent, BaseHealthcareAgent, MCP integration) → healthcare-agent-implementer  
3. **MCP Tool Development** (MCP tool, healthcare-mcp, stdio communication, tool debugging) → MCPToolDeveloper
4. **Security/PHI** (PHI protection, HIPAA compliance, security, infrastructure) → InfraSecurityAgent
5. **Configuration/Deployment** (deployment, configuration, service management, .conf files) → ConfigDeployment
6. **Orchestration** (agent routing, LangChain, orchestrator) → LangChainOrchestration
7. **Test Creation** (test writing, create tests, test automation, generate tests, test scenarios) → TestAutomationAgent
8. **Test Organization** (organize tests, test structure, test refactoring, test cleanup, duplicate tests) → TestOrganizationAgent
9. **Healthcare Testing** (HIPAA testing, PHI testing, compliance tests, medical workflow testing) → HealthcareTestAgent
10. **Test Issues** (test failures, flaky tests, test debugging, slow tests, test maintenance) → TestMaintenanceAgent

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

**Test Creation:**
```
When user asks: "Write tests for the transcription agent" or "Create unit tests"
You should: Immediately invoke TestAutomationAgent using Task tool with:
- subagent_type: "TestAutomationAgent"
- description: "Generate healthcare tests"
- prompt: "User needs test creation. Generate HIPAA-compliant tests using synthetic PHI-safe data with proper fixtures and healthcare scenarios."
```

**Test Organization:**
```
When user asks: "Organize our test files" or "Clean up duplicate tests"
You should: Immediately invoke TestOrganizationAgent using Task tool with:
- subagent_type: "TestOrganizationAgent"
- description: "Organize test structure"
- prompt: "User needs test organization. Analyze test structure, remove duplicates, and organize following healthcare testing patterns."
```

**Healthcare Compliance Testing:**
```
When user asks: "Test PHI detection" or "Validate HIPAA compliance"
You should: Immediately invoke HealthcareTestAgent using Task tool with:
- subagent_type: "HealthcareTestAgent"
- description: "Healthcare compliance testing"
- prompt: "User needs healthcare-specific testing. Create HIPAA compliance tests, PHI detection validation, and medical workflow tests."
```

**Test Maintenance:**
```
When user asks: "Fix failing tests" or "Why are tests flaky?"
You should: Immediately invoke TestMaintenanceAgent using Task tool with:
- subagent_type: "TestMaintenanceAgent"
- description: "Fix test issues"
- prompt: "User has test reliability issues. Analyze test failures, identify flaky tests, and provide optimization recommendations."
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

### Storage Management
Disk space monitoring and optimization commands for medical data operations:

```bash
# Disk space monitoring
python3 scripts/disk_space_monitor.py /home/intelluxe/database/medical_complete
python3 scripts/disk_space_monitor.py --save-report  # Generate detailed report

# Cleanup operations
python3 scripts/cleanup_medical_downloads.py --dry-run    # Preview cleanup
python3 scripts/cleanup_medical_downloads.py --execute   # Execute cleanup
./scripts/automated_cleanup.sh --force                   # Automated cleanup

# Storage optimization
python3 scripts/storage_orchestrator.py --full-cycle     # Complete optimization
```

### Download Best Practices
Guidelines for efficient and storage-conscious downloads:

- **Never use pretty printing**: Remove `indent=` parameters from `json.dump()` calls
- **Monitor disk space**: Use `check_disk_space()` from `download_utils.py`
- **Keep compressed files**: Always preserve `.gz` versions for space efficiency
- **Use streaming parsers**: Process large XML/JSON files without loading entirely into memory
- **Auto-compress large files**: Compress downloads > 50MB immediately after completion
- **Clean up temporary files**: Remove `.tmp`, `.partial`, and `.download` files after completion

## Troubleshooting

### Common Issues
- Service discovery: Check `.conf` files in `services/user/`
- Health checks: Use `make diagnostics` for system-wide health
- Docker issues: Use `make clean-docker` to reset Docker state
- Permission issues: Use `make fix-permissions`
- Medical data updates failing: Check `make medical-mirrors-errors-summary`
- **Disk space issues**: Use `python3 scripts/disk_space_monitor.py` to check usage
- **Download bloat**: Run `scripts/cleanup_medical_downloads.py --dry-run` to identify duplicates
- **Storage performance**: Monitor with `scripts/storage_orchestrator.py --analyze`

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
- Storage Management Scripts

  The Intelluxe AI system has custom storage management scripts:
  - /home/intelluxe/scripts/cleanup_medical_downloads.py - Removes duplicate uncompressed files (use --dry-run first,
  then --execute)
  - /home/intelluxe/scripts/disk_space_monitor.py - Monitors disk usage and provides recommendations
  - /home/intelluxe/scripts/automated_cleanup.sh - Automated cleanup for cron jobs
  - /home/intelluxe/scripts/download_utils.py - Utilities to prevent download bloat
  These scripts recovered 101.7GB by removing duplicate uncompressed PubMed files while preserving compressed versions.
- Download Best Practices

    CRITICAL for medical data downloads:
    - NEVER use indent= parameter in json.dump() - causes massive storage bloat
    - Always keep compressed (.gz) files and remove uncompressed duplicates
    - Monitor disk space during downloads using check_disk_space() from download_utils.py
    - PubMed downloads can consume 200GB+ so always check space first
    - Use streaming parsers for large XML/JSON files to avoid memory issues
- Medical Data Storage Stats

  Medical data storage requirements (approximate):
  - PubMed: 115GB compressed (was 217GB with duplicates)
  - ClinicalTrials: 25GB
  - FDA: 30GB
  - Total medical_complete directory: ~172GB after optimization
  Run python3 scripts/disk_space_monitor.py for current usage
- Agent Usage Patterns

  Specialized agents in .claude/agents/ for complex tasks:
  - StorageOptimizationAgent: Use for disk space issues, cleanup, compression
  - DownloadOrchestrationAgent: Use for bulk downloads, monitoring, bloat prevention
  - MirrorAgent: Enhanced with storage management patterns
  - DataConsolidationAgent: Enhanced with filesystem duplicate detection
  These agents should be invoked automatically via Task tool when keywords are detected.
- Emergency Storage Commands

  If disk space becomes critical:
  1. Check usage: df -h /home/intelluxe/database/medical_complete
  2. Find large files: find /home/intelluxe/database/medical_complete -type f -size +100M -exec ls -lh {} \;
  3. Run cleanup dry-run: python3 scripts/cleanup_medical_downloads.py /home/intelluxe/database/medical_complete 
  --dry-run
  4. Execute cleanup: echo "yes" | python3 scripts/cleanup_medical_downloads.py 
  /home/intelluxe/database/medical_complete --execute
  5. Emergency automated cleanup: ./scripts/automated_cleanup.sh --force
- Cleanup Success Pattern

  Successfully recovered 101.7GB from PubMed directory by:
  1. Removing pretty printing from all download scripts (indent= parameters)
  2. Deleting 560 uncompressed XML files that had .gz counterparts
  3. Preserving all 3,065 compressed files for data integrity
  4. Creating monitoring and automation tools for future prevention
  This pattern applies to all medical data directories.
- Common Storage Issues

  Storage bloat typically comes from:
  1. Pretty-printed JSON/XML (indent=2 or indent=4 in json.dump)
  2. Uncompressed files alongside compressed versions
  3. Temporary download files (.tmp, .partial, .download)
  4. Old backup files that were never cleaned up
  Check with: python3 scripts/disk_space_monitor.py --save-report
- Proactive Storage Monitoring

  Set up weekly automated cleanup (add to crontab):
  0 2 * * 0 /home/intelluxe/scripts/automated_cleanup.sh --force >> /var/log/medical_cleanup.log 2>&1

  This will run every Sunday at 2 AM and only clean if disk usage > 70%
- Download Timeout Handling
  When downloads timeout (like clinical trials after 1 hour):
  1. Check state file: /home/intelluxe/database/medical_complete/clinicaltrials/download_state.json
  2. Resume with: python3 scripts/download_full_clinicaltrials.py
  3. Common timeout causes: Rate limiting, large dataset, network issues
  4. Adjust timeout in download_all_medical_data.py if needed (currently 2x estimated time)