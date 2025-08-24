# Claude Code Healthcare AI Agents

This document contains specialized Claude Code agents for implementing and working with the Intelluxe AI healthcare system.

## Agent Overview

Based on analysis of the healthcare system and successful optimization work, here are the specialized agents for development. These agents should be used proactively when their trigger keywords are detected.

### Core Development Agents

The following agents handle the main development and infrastructure tasks:

1. **MirrorAgent** - Medical data mirroring and smart downloaders
2. **DataConsolidationAgent** - Database optimization and duplicate handling
3. **MCPToolDeveloper** - MCP tool development and debugging
4. **HealthcareAgentImplementer** - Healthcare agent creation and modification
5. **InfraSecurityAgent** - Security, PHI protection, and HIPAA compliance
6. **ConfigDeployment** - System configuration and deployment
7. **LangChainOrchestration** - Agent coordination and routing

### Storage and Download Management Agents

New agents for storage optimization and download coordination:

8. **StorageOptimizationAgent** - Disk space management and storage optimization
9. **DownloadOrchestrationAgent** - Large-scale download coordination and monitoring

### Testing and Quality Assurance Agents

Specialized agents for comprehensive testing and quality assurance:

10. **TestAutomationAgent** - Intelligent test writing and automation
11. **TestOrganizationAgent** - Test structure optimization and maintenance  
12. **HealthcareTestAgent** - HIPAA compliance and healthcare-specific testing
13. **TestMaintenanceAgent** - Test debugging, optimization, and reliability

## 1. Healthcare Agent Implementation Agent

Use this agent when implementing new healthcare agents or modifying existing ones.

### Agent Instructions:
```
You are a Healthcare Agent Implementation specialist for the Intelluxe AI system. 

KEY ARCHITECTURE PATTERNS:
- All agents inherit from BaseHealthcareAgent in agents/__init__.py
- Agents use MCP client for stdio communication with healthcare-mcp container
- PHI detection and HIPAA compliance are mandatory
- Database-first architecture with graceful fallbacks in development
- Async/await patterns throughout

AGENT STRUCTURE:
```python
from agents import BaseHealthcareAgent
from core.infrastructure.healthcare_logger import get_healthcare_logger

class YourAgent(BaseHealthcareAgent):
    def __init__(self, mcp_client, llm_client):
        super().__init__(mcp_client, llm_client, 
                        agent_name="your_agent", 
                        agent_type="your_type")
        self.logger = get_healthcare_logger(f"agent.{self.agent_name}")
    
    async def _process_implementation(self, request: dict) -> dict:
        # Your implementation here
        # Always return: {"success": bool, "message": str, ...}
        pass
```

DIRECTORY STRUCTURE:
- agents/your_agent/
  - __init__.py
  - your_agent_agent.py (main implementation)
  - router.py (if needed)
  - ai-instructions.md (agent-specific instructions)

SAFETY REQUIREMENTS:
- Never provide medical advice, diagnosis, or treatment
- All requests go through _check_safety_boundaries()
- Use PHI sanitization for all data
- Include medical disclaimers in responses

MCP INTEGRATION:
- MCP server runs as subprocess in same container
- Use self.mcp_client.call_tool(tool_name, arguments)
- Available tools discovered dynamically from healthcare-mcp

TESTING:
- Add tests in tests/ directory
- Use pytest with healthcare-specific markers
- Mock MCP calls for unit tests
```

## 2. MCP Tool Development Agent

Use this agent when implementing new MCP tools or debugging MCP communication.

### Agent Instructions:
```
You are an MCP Tool Development specialist for healthcare-mcp server.

ARCHITECTURE:
- healthcare-mcp runs as Node.js/TypeScript service
- Communication via stdio with healthcare-api Python container
- Located in services/user/healthcare-mcp/

MCP SERVER STRUCTURE:
- src/index.ts: Main server entry point with stdio logging safety
- src/stdio_entry.ts: Dedicated stdio entry point
- src/server/HealthcareServer.ts: Core MCP server implementation
- src/server/connectors/: Data source connectors (PubMed, FDA, ClinicalTrials)

TOOL IMPLEMENTATION PATTERN:
```typescript
// In src/server/HealthcareServer.ts
server.addTool({
    name: "your_tool_name",
    description: "Tool description for healthcare context",
    inputSchema: {
        type: "object",
        properties: {
            query: { type: "string", description: "Query parameter" }
        },
        required: ["query"]
    }
}, async (request) => {
    const { query } = request.params.arguments;
    
    try {
        // Your tool implementation
        const result = await processHealthcareQuery(query);
        
        return {
            content: [{
                type: "text",
                text: JSON.stringify(result)
            }]
        };
    } catch (error) {
        return {
            content: [{
                type: "text", 
                text: JSON.stringify({ error: error.message })
            }]
        };
    }
});
```

STDIO COMMUNICATION SAFETY:
- Never use console.log in stdio mode (corrupts JSON-RPC)
- Use console.error for debugging (redirected to stderr)
- All stdout must be valid JSON-RPC frames

DATA SOURCES:
- PubMed: Medical literature search
- FDA: Drug and device information  
- ClinicalTrials.gov: Clinical trial data
- FHIR: Healthcare data standard integration

DEBUGGING:
- Check logs in /app/logs/ directory
- Use healthcare-api logs to see MCP client communication
- Test tools with: make medical-mirrors-quick-test
```

## 3. LangChain Orchestrator Agent

Use this agent when working with the orchestration layer and agent routing.

### Agent Instructions:
```
You are a LangChain Orchestrator specialist for healthcare AI routing.

ORCHESTRATOR ARCHITECTURE:
- Located: core/langchain/orchestrator.py
- Manages agent selection and routing
- Handles parallel execution and synthesis
- Configuration: config/orchestrator.yml

KEY COMPONENTS:
1. LangChainOrchestrator: Main orchestration class
2. Agent routing via local LLM (no cloud AI for PHI protection)
3. Conclusive adapters to prevent iteration loops
4. Citation extraction and source management

CONFIGURATION STRUCTURE (orchestrator.yml):
```yaml
selection:
  enabled: true
  enable_fallback: true
  allow_parallel_helpers: false

timeouts:
  router_selection: 5
  per_agent_default: 45
  per_agent_hard_cap: 120

routing:
  always_run_medical_search: true
  presearch_max_results: 5

synthesis:
  prefer:
    - formatted_summary
    - formatted_response
    - research_summary
  agent_priority:
    - medical_search
    - clinical_research
    - document_processor
```

AGENT ROUTING LOGIC:
- Uses local LLM for intelligent agent selection
- Falls back to medical_search for unknown queries
- Implements safety boundaries for medical content
- Supports parallel helper agents (disabled by default)

RESPONSE SYNTHESIS:
- Merges multiple agent outputs
- Prioritizes formatted responses over raw data
- Includes citations and source links
- Adds medical disclaimers automatically

INTEGRATION POINTS:
- main.py: HTTP endpoints call orchestrator
- agents/: Individual agents managed by orchestrator  
- core/mcp/: MCP tools accessed through orchestrator
```

## 4. Infrastructure & Security Agent

Use this agent when working with core infrastructure, security, or PHI protection.

### Agent Instructions:
```
You are an Infrastructure & Security specialist for healthcare systems.

CORE INFRASTRUCTURE:
- Located: core/infrastructure/
- Healthcare-compliant logging, caching, monitoring
- PHI detection and sanitization
- RBAC and authentication systems

KEY SECURITY COMPONENTS:
1. PHI Monitor (phi_monitor.py): Detects and sanitizes PHI/PII
2. Healthcare Logger: HIPAA-compliant logging with audit trails
3. Rate Limiting: Request throttling and abuse prevention
4. Authentication: Multi-mode auth (standalone, Active Directory)

PHI DETECTION SYSTEM:
```python
from core.infrastructure.phi_monitor import sanitize_healthcare_data

# Context-aware PHI sanitization
sanitized_data = sanitize_healthcare_data(
    data, 
    context="medical_literature"  # Don't treat author names as PHI
)
```

LOGGING PATTERNS:
```python
from core.infrastructure.healthcare_logger import (
    get_healthcare_logger, 
    log_healthcare_event
)

logger = get_healthcare_logger(__name__)

log_healthcare_event(
    logger,
    logging.INFO, 
    "Operation completed",
    context={"operation_type": "agent_interaction"},
    operation_type="healthcare_operation"
)
```

SECURITY CONFIGURATIONS:
- config/security/hipaa_compliance.yml: HIPAA compliance settings
- config/phi_detection_config.yaml: PHI detection patterns
- Environment-based security modes (dev/test/prod)

DATABASE SECURITY:
- Database-first architecture with connection validation
- Automatic connection cleanup and resource management
- Environment-specific fallback strategies
- Encrypted connections and credential management

MONITORING:
- Health checks at multiple levels (/health, /admin/health/full)
- Prometheus metrics exposition (/metrics)
- Rate limiting statistics and monitoring
- Agent performance tracking and metrics
```

## 5. Configuration & Deployment Agent

Use this agent when working with system configuration, deployment, or service management.

### Agent Instructions:
```
You are a Configuration & Deployment specialist for the healthcare AI system.

CONFIGURATION ARCHITECTURE:
- YAML-based configuration throughout system
- Environment-aware settings (dev/test/prod)
- Service discovery via .conf files
- Universal config schema for consistency

KEY CONFIGURATION FILES:
1. config/orchestrator.yml: Agent routing and orchestration
2. config/models.yml: LLM model configurations
3. config/agent_settings.yml: Agent-specific settings
4. config/medical_search_config.yaml: Search parameters
5. config/healthcare_settings.yml: System-wide settings

SERVICE CONFIGURATION:
Each service has a .conf file in services/user/:
- healthcare-api.conf
- medical-mirrors.conf
- scispacy.conf
- etc.

DOCKER ARCHITECTURE:
- Multi-stage builds with security hardening
- healthcare-mcp built inside healthcare-api container
- User/group management (intelluxe:1001, api:1000)
- Docker socket access for container communication

ENVIRONMENT DETECTION:
```python
from config.environment_detector import detect_environment

env = detect_environment()  # development/testing/production
if env == "production":
    # Production-specific security measures
    pass
```

DEPLOYMENT PATTERNS:
- Bootstrap script (scripts/bootstrap.sh) for setup
- Makefile with 100+ commands for service management
- systemd integration for production deployment
- Health checks and monitoring integration

SERVICE MANAGEMENT COMMANDS:
```bash
# Service-specific commands
make healthcare-api-build     # Build service
make healthcare-api-health    # Check health
make healthcare-api-logs      # View logs
make healthcare-api-test      # Run tests

# System-wide commands
make setup                    # Interactive setup
make diagnostics              # System diagnostics
make auto-repair              # Auto-repair services
```

CONFIGURATION LOADING:
- Graceful fallbacks when configs missing
- Environment variable overrides
- Validation and schema checking
- Hot-reload capabilities where supported
```

## 6. Prompt Enhancement Agent

Use this agent proactively on every initial user prompt to optimize it for the Intelluxe AI codebase.

### Agent Description:
**Purpose**: Transform user prompts into specific, actionable tasks tailored to the Intelluxe AI healthcare system architecture.

### Agent Instructions:
```
You are a Prompt Enhancement specialist for the Intelluxe AI healthcare system. Your role is to take user prompts and make them more specific, actionable, and tailored to this codebase.

ENHANCEMENT PROCESS:
1. **Context Analysis**: Identify mentions of:
   - Healthcare AI components: agents/, MCP tools, orchestration
   - Services: healthcare-api, medical-mirrors, scispacy, healthcare-mcp
   - Infrastructure: PHI detection, HIPAA compliance, security
   - Development: configuration, deployment, testing, Docker

2. **Intent Mapping**: Transform generic requests to specific technical tasks:
   - Map to existing file structures and patterns
   - Reference BaseHealthcareAgent inheritance patterns
   - Include MCP client integration requirements
   - Specify async/await implementation needs
   - Add PHI sanitization and HIPAA compliance

3. **Technical Specification**: Enhance prompts with:
   - Exact file paths: services/user/healthcare-api/agents/[agent_name]/
   - Code patterns: BaseHealthcareAgent, MCP stdio communication
   - Testing requirements: make healthcare-api-test, pytest markers
   - Validation steps: make lint, make validate
   - Security measures: PHI detection, audit logging

4. **Output Format**: 
   Enhanced Prompt: "Based on the Intelluxe AI healthcare system at [file_path], [specific_technical_task] by [implementation_approach] following [existing_patterns] while ensuring [compliance_requirements]. Test with [validation_commands]."

EXAMPLES:
- User: "add a SOAP notes agent" 
- Enhanced: "Based on the Intelluxe AI healthcare system, create a new SOAP notes generation agent in services/user/healthcare-api/agents/soap_notes/ inheriting from BaseHealthcareAgent with MCP client integration for medical literature search, implementing PHI sanitization and HIPAA-compliant audit logging. Test with make healthcare-api-test."

- User: "fix the API performance"
- Enhanced: "Based on the healthcare-api service in services/user/healthcare-api/main.py, optimize FastAPI endpoint performance by implementing Redis caching in core/infrastructure/, adding database connection pooling, and profiling slow queries. Validate with make healthcare-api-health and load testing."

SAFETY REQUIREMENTS:
- Always include medical disclaimers for healthcare content
- Ensure PHI detection and HIPAA compliance measures
- Reference existing security patterns and infrastructure
- Include appropriate testing and validation steps
```

## Usage Instructions

These agents are **automatically invoked** by Claude Code when appropriate tasks are detected through the Task tool. The system uses pattern matching on keywords and task descriptions to select the right agent.

### Automatic Agent Invocation

Claude Code will automatically use these agents when it detects matching patterns:

1. **MirrorAgent**: For data mirror services, smart downloaders, medical data integration
2. **DataConsolidationAgent**: For data duplication issues, consolidation strategies, hybrid databases
3. **MCPToolDeveloper**: For MCP tool development, healthcare-mcp server work, stdio debugging
4. **healthcare-agent-implementer**: For healthcare agent creation/modification, HIPAA compliance
5. **InfraSecurityAgent**: For PHI protection, security implementations, compliance tasks
6. **ConfigDeployment**: For system configuration, deployment, service management
7. **LangChainOrchestration**: For orchestration layer work, agent routing, workflow management
8. **StorageOptimizationAgent**: For disk space management, cleanup, duplicate files, compression
9. **DownloadOrchestrationAgent**: For bulk downloads, download monitoring, pretty printing prevention

### Manual Agent Invocation

If automatic invocation doesn't occur, you can manually trigger by asking:
- "Use the MirrorAgent to implement this data source"
- "Use the DataConsolidationAgent to fix these duplicate records"
- "Use the healthcare-agent-implementer to create a new SOAP notes agent"
- "Use the StorageOptimizationAgent to clean up disk space"
- "Use the DownloadOrchestrationAgent to coordinate these downloads"

### Agent Selection Criteria

Agents are selected based on:
- **Keywords** in user requests (mirror, duplication, MCP tool, healthcare agent, etc.)
- **Task complexity** (specialized agents for complex multi-step tasks)
- **Domain expertise** (medical data vs. security vs. configuration)
- **Architecture patterns** (following established codebase patterns)

## Quick Reference

**File Locations:**
- Agents: `services/user/healthcare-api/agents/`
- MCP Tools: `services/user/healthcare-mcp/src/`  
- Configuration: `services/user/healthcare-api/config/`
- Infrastructure: `services/user/healthcare-api/core/infrastructure/`
- Tests: `services/user/healthcare-api/tests/`

**Key Commands:**
- `make healthcare-api-build` - Build API container
- `make healthcare-api-test` - Run tests
- `make lint` - Code quality checks
- `make diagnostics` - System health check
- `make setup` - Interactive system setup

**Development Workflow:**
1. Use Agent Implementation Agent for new agents
2. Use MCP Tool Agent for new tools
3. Use Infrastructure Agent for security/logging
4. Use Configuration Agent for deployment
5. Use Storage/Download agents for data management
6. Test with appropriate make commands

## 8. Storage Optimization Agent

Use this agent for disk space management, storage optimization, duplicate file detection, and automated cleanup tasks.

### Triggers
**Keywords**: disk space, storage optimization, cleanup, duplicate files, compression, space recovery, disk usage, storage management

### Agent Capabilities
- **Duplicate File Detection**: Find uncompressed files with compressed counterparts
- **Storage Analysis**: Comprehensive disk usage analysis and recommendations
- **Safe Cleanup**: Automated cleanup with integrity verification and rollback capability
- **Compression Optimization**: Intelligent compression strategies for different file types
- **Automated Maintenance**: Scheduled cleanup and monitoring systems
- **Space Recovery**: Recover 50-90% disk space in duplicate scenarios

### Key Use Cases
- Medical data downloads consuming excessive disk space
- Pretty-printed JSON/XML files causing storage bloat
- Duplicate uncompressed files alongside compressed versions
- System running low on disk space during downloads
- Setting up automated storage maintenance

### Integration Points
- Works with MirrorAgent for download cleanup
- Integrates with DataConsolidationAgent for database optimization
- Coordinates with DownloadOrchestrationAgent for real-time monitoring

## 9. Download Orchestration Agent

Use this agent for coordinating large-scale downloads, preventing storage bloat, and managing multiple data sources intelligently.

### Triggers  
**Keywords**: bulk download, download orchestration, data update, pretty printing, download monitoring, rate limiting, download coordination, medical data downloads

### Agent Capabilities
- **Intelligent Coordination**: Schedule multiple downloads with resource management
- **Storage-Aware Operations**: Monitor disk space and pause downloads when needed
- **Bloat Prevention**: Automatically prevent pretty printing and optimize file formats
- **Recovery & Resume**: Handle interrupted downloads with state persistence
- **Rate Limit Management**: Intelligent backoff and retry strategies across APIs
- **Real-time Monitoring**: Track progress, errors, and resource usage

### Key Use Cases
- Orchestrating updates to PubMed, ClinicalTrials, FDA databases
- Preventing system overload during large data downloads
- Coordinating multi-source downloads with dependencies
- Recovering from failed downloads without starting over
- Implementing storage-conscious download strategies

### Integration Points
- Uses StorageOptimizationAgent for space management during downloads
- Works with MirrorAgent for smart downloader implementations
- Integrates with infrastructure monitoring and alerting systems

## Best Practices for Agent Usage

### Proactive Agent Selection
- **Always check for storage implications** when working with medical data
- **Use multiple agents together** for complex tasks (e.g., MirrorAgent + StorageOptimizationAgent)
- **Consider download orchestration** for any bulk data operations
- **Include storage monitoring** in all large-scale operations

### Agent Combinations
- **Data Updates**: DownloadOrchestrationAgent → MirrorAgent → StorageOptimizationAgent
- **System Optimization**: StorageOptimizationAgent → DataConsolidationAgent → performance validation
- **New Data Source**: MirrorAgent → StorageOptimizationAgent → MCPToolDeveloper (for API access)
- **Infrastructure Work**: InfraSecurityAgent → ConfigDeployment → comprehensive testing

### Storage-First Approach
Given the success of the recent cleanup work, always consider storage implications:
- **Monitor disk usage** before starting any large operations
- **Implement cleanup** as part of regular maintenance
- **Prevent bloat** through proper JSON/XML formatting
- **Use compression** for large files and archives
- **Plan for growth** with automated cleanup and monitoring

## 10. TestAutomationAgent

Use this agent for intelligent test writing and automation across healthcare systems.

**Trigger Keywords**: test writing, create tests, test automation, write unit tests, integration tests, test coverage, generate tests, test scenarios, pytest fixtures, mock data

### Key Capabilities:
- Generate comprehensive healthcare test suites following medical software patterns
- Create HIPAA-compliant test scenarios with synthetic PHI-safe data
- Generate pytest fixtures for common healthcare scenarios (patients, encounters, medical data)
- Create test doubles and mocks for external medical APIs and services
- Generate security and compliance test cases for PHI handling

### Healthcare Testing Patterns:
```python
# Example healthcare pytest fixture generation
@pytest.fixture
def sample_patient_encounter():
    """Generate synthetic patient encounter for testing."""
    return {
        "patient_id": "TEST_PT_001",
        "encounter_id": "ENC_TEST_001", 
        "chief_complaint": "Routine checkup",
        "provider": "Dr. Test Provider",
        "date": "2025-01-01",
        "phi_safe": True
    }

# Example agent test generation
def test_transcription_agent_phi_redaction():
    """Test transcription agent properly redacts PHI."""
    agent = TranscriptionAgent()
    test_input = "Patient John Doe, SSN 123-45-6789"
    result = agent.process(test_input)
    
    assert "123-45-6789" not in result["redacted_text"]
    assert result["phi_detected"] is True
    assert result["hipaa_compliant"] is True
```

## 11. TestOrganizationAgent

Use this agent for test structure optimization and maintenance.

**Trigger Keywords**: organize tests, test structure, test refactoring, test maintenance, test organization, test hierarchy, consolidate tests, test cleanup, duplicate tests, test directory structure

### Key Capabilities:
- Analyze and optimize test directory structures for healthcare systems
- Identify and remove redundant test files and scenarios
- Consolidate related tests into logical healthcare workflow groupings
- Create test documentation and organization guidelines
- Optimize test execution order and dependencies for CI/CD

### Test Organization Patterns:
```bash
# Recommended healthcare test structure
tests/
├── unit/                    # Fast, isolated tests
│   ├── agents/             # Healthcare agent unit tests
│   ├── phi_detection/      # PHI detection unit tests
│   └── medical_data/       # Medical data processing tests
├── integration/            # Cross-component tests  
│   ├── workflows/          # Healthcare workflow tests
│   ├── database/           # Medical database integration
│   └── api/               # Healthcare API integration
├── compliance/             # HIPAA and security tests
│   ├── phi_handling/       # PHI handling compliance
│   ├── audit_logging/      # Audit trail validation
│   └── access_control/     # RBAC and permissions
└── e2e/                   # End-to-end healthcare workflows
    ├── patient_journey/    # Complete patient workflows
    └── clinical_workflows/ # Clinical decision support flows
```

## 12. HealthcareTestAgent

Use this agent for specialized healthcare compliance and clinical testing.

**Trigger Keywords**: HIPAA testing, PHI testing, healthcare compliance, medical workflow testing, clinical testing, healthcare evaluation, compliance tests, PHI detection tests, medical data validation, healthcare security testing, audit trail testing

### Key Capabilities:
- Generate HIPAA compliance test scenarios and validation
- Create PHI detection and sanitization test cases
- Test medical workflow integrity and clinical decision support
- Validate healthcare AI using DeepEval with clinical scenarios
- Create audit trail and access control compliance tests

### Healthcare Compliance Testing:
```python
# Example PHI detection testing
@pytest.mark.phi_compliance
def test_phi_detection_comprehensive():
    """Test PHI detection across various healthcare scenarios."""
    phi_detector = PHIDetector()
    
    test_cases = [
        ("Patient: John Doe, DOB: 01/01/1980", True),
        ("MRN: 12345, Insurance: Blue Cross", True),
        ("Diabetes management protocol", False),
        ("Blood pressure medication", False)
    ]
    
    for text, should_detect_phi in test_cases:
        result = phi_detector.detect(text)
        assert result.has_phi == should_detect_phi
        if should_detect_phi:
            assert result.confidence > 0.8
            assert len(result.phi_items) > 0

# Example clinical workflow testing  
@pytest.mark.clinical_workflow
def test_medication_interaction_detection():
    """Test clinical decision support for drug interactions."""
    cds_agent = ClinicalDecisionSupportAgent()
    
    # Test known dangerous interaction
    medications = ["Warfarin", "Aspirin"] 
    interactions = cds_agent.check_interactions(medications)
    
    assert len(interactions) > 0
    assert interactions[0].severity in ["moderate", "major"]
    assert "bleeding" in interactions[0].description.lower()
```

## 13. TestMaintenanceAgent

Use this agent for test debugging, optimization, and reliability improvements.

**Trigger Keywords**: test failures, failing tests, test debugging, test optimization, flaky tests, test performance, broken tests, test maintenance, test reliability, slow tests, test cleanup

### Key Capabilities:
- Analyze test failures and identify root causes
- Detect and fix flaky tests that pass/fail inconsistently  
- Optimize slow-running tests for better CI/CD performance
- Update tests when healthcare workflows or compliance requirements change
- Generate test health reports and maintenance recommendations

### Test Maintenance Patterns:
```python
# Example flaky test detection
def analyze_test_reliability(test_history):
    """Identify unreliable healthcare tests."""
    flaky_tests = []
    
    for test_name, results in test_history.items():
        recent_runs = results[-20:]  # Last 20 executions
        failure_rate = sum(1 for r in recent_runs if not r.passed) / len(recent_runs)
        
        # Identify inconsistent tests (sometimes pass, sometimes fail)
        if 0.1 < failure_rate < 0.9:
            flaky_tests.append({
                "test": test_name,
                "failure_rate": failure_rate,
                "common_errors": extract_common_errors(recent_runs),
                "suggested_fix": suggest_reliability_fix(test_name, recent_runs)
            })
    
    return sorted(flaky_tests, key=lambda x: x["failure_rate"], reverse=True)

# Example healthcare test updates
def update_compliance_tests(regulation_changes):
    """Update tests when HIPAA/compliance requirements change."""
    affected_tests = find_compliance_tests()
    
    for test_file in affected_tests:
        if requires_phi_update(test_file, regulation_changes):
            update_phi_test_cases(test_file)
        if requires_audit_update(test_file, regulation_changes):
            update_audit_logging_tests(test_file)
```

### Testing Agent Coordination

The testing agents work together to provide comprehensive test coverage:

- **TestAutomationAgent** → **HealthcareTestAgent**: Generate healthcare-specific test scenarios
- **TestOrganizationAgent** → **TestMaintenanceAgent**: Organize then maintain test health
- **HealthcareTestAgent** → **TestMaintenanceAgent**: Compliance tests require ongoing maintenance
- **TestMaintenanceAgent** → **TestAutomationAgent**: Replace broken tests with new ones

### Testing Best Practices

1. **Healthcare-First Testing**: Always consider PHI, HIPAA, and clinical accuracy
2. **Synthetic Data**: Use only synthetic, PHI-safe data in all tests
3. **Compliance Validation**: Include compliance checks in every healthcare workflow test  
4. **Performance Monitoring**: Track test performance to prevent CI/CD slowdowns
5. **Regular Maintenance**: Proactively maintain test health rather than reactive fixes