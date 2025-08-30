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

#### Business Microservices
```bash
# Insurance Verification Service
make insurance-verification-build    # Build Insurance Verification Docker image
make insurance-verification-logs     # View Insurance Verification logs
make insurance-verification-health   # Check Insurance Verification health
make insurance-verification-test     # Run Insurance Verification validation

# Billing Engine Service
make billing-engine-build    # Build Billing Engine Docker image
make billing-engine-logs     # View Billing Engine logs
make billing-engine-health   # Check Billing Engine health
make billing-engine-test     # Run Billing Engine validation

# Compliance Monitor Service
make compliance-monitor-build    # Build Compliance Monitor Docker image
make compliance-monitor-logs     # View Compliance Monitor logs
make compliance-monitor-health   # Check Compliance Monitor health
make compliance-monitor-test     # Run Compliance Monitor validation

# Business Intelligence Service
make business-intelligence-build    # Build Business Intelligence Docker image
make business-intelligence-logs     # View Business Intelligence logs
make business-intelligence-health   # Check Business Intelligence health
make business-intelligence-test     # Run Business Intelligence validation

# Doctor Personalization Service
make doctor-personalization-build    # Build Doctor Personalization Docker image
make doctor-personalization-logs     # View Doctor Personalization logs
make doctor-personalization-health   # Check Doctor Personalization health
make doctor-personalization-test     # Run Doctor Personalization validation
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

#### Core Infrastructure Services
- **Healthcare API** (`services/user/healthcare-api/`): Main HIPAA-compliant API with administrative support agents
- **Medical Mirrors** (`services/user/medical-mirrors/`): Downloads and mirrors PubMed, ClinicalTrials.gov, and FDA data
- **SciSpacy** (`services/user/scispacy/`): NLP service for medical entity recognition
- **Healthcare MCP** (`services/user/healthcare-mcp/`): MCP server for healthcare tools
- **MCP Pipeline** (`services/user/mcp-pipeline/`): Pipeline integration for Open WebUI

#### Business Microservices
Standalone business services extracted from healthcare-api agents:

- **Insurance Verification** (`172.20.0.23`): Chain-of-Thought reasoning for insurance verification and prior authorization
- **Billing Engine** (`172.20.0.24`): Tree of Thoughts reasoning for billing decisions, claims processing, and code validation
- **Compliance Monitor** (`172.20.0.25`): HIPAA compliance monitoring, violation detection, and audit reporting
- **Business Intelligence** (`172.20.0.26`): Advanced analytics, business insights, and operational reporting
- **Doctor Personalization** (`172.20.0.27`): LoRA-based AI personalization for healthcare providers

### Key Directories

- `agents/`: Core AI agents for different healthcare workflows
- `core/`: Shared infrastructure, database, and utility modules
  - `core/clients/`: Business service HTTP clients with circuit breakers
  - `core/compliance/`: Compliance monitoring integration for agents
- `config/`: System configuration files and schemas
- `scripts/`: Management and deployment scripts
- `services/user/`: Docker service configurations
- `tests/`: Comprehensive test suite including healthcare evaluations

## Business Services Architecture

The system implements a microservices architecture with specialized business services extracted from the main healthcare-api for improved scalability and maintainability.

### Service Integration Patterns

#### HTTP Client with Resilience (`core/clients/business_services.py`)
- **Circuit Breaker**: Prevents cascade failures with configurable failure thresholds
- **Retry Logic**: Exponential backoff with configurable attempts and delay
- **Timeout Handling**: Service-specific timeout configurations (15s-120s)
- **PHI-Safe Logging**: Compliance-aware request/response logging (configurable by environment)

#### Configuration Management (`config/business_services.yml`)
- **Service URLs**: Static IP allocation on intelluxe-net (172.20.0.23-27)
- **Environment Overrides**: Development, testing, and production configurations
- **Circuit Breaker Settings**: Configurable failure thresholds and recovery timeouts
- **Logging Policies**: Environment-aware PHI logging controls

#### Compliance Integration (`core/compliance/agent_compliance_monitor.py`)
- **Real-time Monitoring**: All agent operations monitored via compliance-monitor service
- **PHI Detection**: Automated scanning of inputs and outputs for protected health information
- **Audit Trails**: Comprehensive logging of all healthcare operations with session tracking
- **Compliance Decorators**: Easy integration with `@compliance_monitor_decorator`

### Agent-to-Service Integration

Healthcare agents now delegate business logic to specialized services:

```python
# Insurance Agent → Insurance Verification Service (Chain-of-Thought)
async with get_business_client() as client:
    response = await client.verify_insurance(verification_request)
    reasoning = response.data.get("reasoning", {})  # CoT decision process
    
# Billing Agent → Billing Engine Service (Tree of Thoughts)
async with get_business_client() as client:
    response = await client.process_claim(claim_data)
    reasoning = response.data.get("reasoning", {})  # ToT decision tree
```

### Service Communication Benefits

This microservices architecture provides:
- **Scalability**: Each service can be scaled independently based on load
- **Maintainability**: Clear separation of concerns between administrative and business logic
- **Reliability**: Circuit breaker and retry patterns prevent cascade failures
- **Compliance**: Centralized PHI monitoring and audit trails across all services
- **Reasoning**: Advanced AI decision-making with Chain-of-Thought and Tree of Thoughts patterns

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
- **BusinessServiceAnalyzer**: Automatically use for extracting business logic from agents into standalone microservices, service architecture design
- **PhaseDocumentAnalyzer**: Automatically use for analyzing phase documents, cross-referencing implementation status, generating TODO lists
- **ServiceIntegrationAgent**: Automatically use for service-to-service communication, distributed system patterns, API design
- **ComplianceAutomationAgent**: Automatically use for automated compliance monitoring, HIPAA rule creation, compliance reporting

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
11. **Performance Issues** (slow processing, single-threaded, deadlock issues, parallel processing, multi-threading, bottleneck analysis, CPU utilization) → PerformanceOptimizationAgent
12. **Service Extraction** (extract service, standalone microservice, business logic separation, service architecture) → BusinessServiceAnalyzer
13. **Phase Analysis** (phase analysis, implementation status, TODO generation, project roadmap) → PhaseDocumentAnalyzer
14. **Service Integration** (service integration, microservice communication, inter-service API, distributed system) → ServiceIntegrationAgent
15. **Compliance Automation** (compliance automation, audit setup, violation rules, compliance reporting) → ComplianceAutomationAgent
16. **Drug Data Integration** (drug data integration, pharmaceutical sources, drug name matching, clinical enrichment, fuzzy matching) → DrugDataIntegrationAgent
17. **Parser Generation** (create parser, parse XML, parse JSON, data extraction, format conversion, streaming parser) → DataParserGeneratorAgent
18. **Docker Container Debugging** (docker cp, container file sync, docker build cache, container debugging, module import container) → DockerIntegrationDebugAgent

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

**Performance Optimization:**
```
When user asks: "This is only using one CPU" or "Processing is very slow" or "Deadlock issues"
You should: Immediately invoke PerformanceOptimizationAgent using Task tool with:
- subagent_type: "PerformanceOptimizationAgent" 
- description: "Optimize system performance"
- prompt: "User reports performance issues with slow processing. Analyze bottlenecks, implement parallel processing, resolve database deadlocks, and optimize CPU utilization using multi-threading patterns."
```

**Service Extraction & Architecture:**
```
When user asks: "Extract the billing logic into a separate service" or "Create standalone microservices"
You should: Immediately invoke BusinessServiceAnalyzer using Task tool with:
- subagent_type: "BusinessServiceAnalyzer"
- description: "Extract business service"
- prompt: "User needs to extract business logic into standalone microservice. Analyze existing agents, design service architecture, and implement with FastAPI following intelluxe-net patterns."
```

**Phase Analysis & TODO Generation:**
```
When user asks: "What's our implementation status against the phase documents?" or "Generate a TODO list"
You should: Immediately invoke PhaseDocumentAnalyzer using Task tool with:
- subagent_type: "PhaseDocumentAnalyzer"
- description: "Analyze implementation status"
- prompt: "User needs analysis of implementation status against phase documents. Cross-reference planned features with current codebase and generate prioritized TODO list."
```

**Service Integration & Communication:**
```
When user asks: "Set up communication between services" or "Implement distributed transaction patterns"
You should: Immediately invoke ServiceIntegrationAgent using Task tool with:
- subagent_type: "ServiceIntegrationAgent"
- description: "Design service integration"
- prompt: "User needs service integration patterns. Design resilient service communication with circuit breakers, retry logic, and distributed transaction patterns."
```

**Compliance Automation Setup:**
```
When user asks: "Set up automated HIPAA compliance monitoring" or "Create compliance dashboard"
You should: Immediately invoke ComplianceAutomationAgent using Task tool with:
- subagent_type: "ComplianceAutomationAgent"
- description: "Automate compliance monitoring"
- prompt: "User needs compliance automation. Set up HIPAA violation detection rules, automated audit trails, and compliance dashboards with regulatory reporting."
```

**Drug Data Integration:**
```
When user asks: "Integrate DailyMed data" or "Add drug classifications" or "Fuzzy match drug names"
You should: Immediately invoke DrugDataIntegrationAgent using Task tool with:
- subagent_type: "DrugDataIntegrationAgent"
- description: "Integrate pharmaceutical data"
- prompt: "User needs drug data integration. Implement enhanced drug sources with fuzzy matching, clinical data enrichment, and performance optimization following proven patterns from DailyMed/DrugCentral/RxClass integration."
```

**Parser Creation:**
```
When user asks: "Create parser for XML" or "Extract fields from JSON" or "Need streaming parser"
You should: Immediately invoke DataParserGeneratorAgent using Task tool with:
- subagent_type: "DataParserGeneratorAgent"
- description: "Generate data parser"
- prompt: "User needs parser creation. Generate robust parser class with validation, normalization, streaming support, and error handling based on healthcare data processing patterns."
```

**Docker Container Debugging:**
```
When user asks: "Files not in container" or "Import errors in docker" or "Database connection failed"
You should: Immediately invoke DockerIntegrationDebugAgent using Task tool with:
- subagent_type: "DockerIntegrationDebugAgent"
- description: "Debug container issues"
- prompt: "User has container integration problems. Diagnose file sync, build cache, module import, or database connectivity issues using proven debugging patterns."
```

**Business Service Maintenance:**
```
When user asks: "Service health issues" or "Circuit breaker tripping" or "Microservice logs showing errors"
You should: Immediately invoke BusinessServiceMaintenanceAgent using Task tool with:
- subagent_type: "BusinessServiceMaintenanceAgent"
- description: "Monitor and maintain business services"
- prompt: "User has business service issues. Diagnose health problems, analyze circuit breaker patterns, troubleshoot service communication, and optimize performance across the 5 business microservices."
```

**Distributed System Testing:**
```
When user asks: "Test service integrations" or "End-to-end testing across services" or "Validate circuit breaker logic"
You should: Immediately invoke ServiceTestOrchestrator using Task tool with:
- subagent_type: "ServiceTestOrchestrator"
- description: "Orchestrate distributed system tests"
- prompt: "User needs comprehensive testing across microservices. Design and execute integration tests, resilience tests, compliance tests, and performance tests for the distributed healthcare system."
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

### Service Communication Patterns
- All services use static IPs on intelluxe-net (172.20.0.x)
- Service-to-service communication via HTTP REST APIs
- Shared PostgreSQL database at 172.20.0.11:5432
- Shared Redis cache at 172.20.0.12:6379
- Health checks at `/health` endpoint for all services
- Circuit breaker patterns for fault tolerance
- Retry logic with exponential backoff
- Service authentication via JWT tokens

### Enhanced Drug Sources Integration
When working with pharmaceutical data integration and drug name matching:

#### Best Practices
- **Fuzzy Matching**: Use tiered strategies (exact → normalized → fuzzy) for optimal performance
- **Drug Name Normalization**: Remove pharmaceutical salts, prefixes, and dosage forms before matching
- **Performance Optimization**: Limit expensive fuzzy matching to unmatched subset (max 100-1000 items)
- **Data Lineage**: Always maintain `data_sources` array for traceability
- **Field Population**: Prioritize high-value clinical fields (mechanism_of_action, pharmacokinetics)

#### Parser Creation Patterns
Follow `enhanced_drug_sources/` directory structure:
```
enhanced_drug_sources/
├── drug_name_matcher.py      # Fuzzy matching with tiered strategies
├── dailymed_parser.py        # HL7 v3 XML clinical data parser
├── drugcentral_parser.py     # Mechanism/pharmacology JSON parser
├── rxclass_parser.py         # Therapeutic classifications parser
└── base_parser.py            # Common validation/normalization patterns
```

#### Docker Development Workflow
For container-based testing and debugging:
- Use `docker cp` for quick file synchronization during development
- Test with container-specific scripts: `docker exec container python3 test_enhanced.py`
- Handle module imports with `sys.path.append('/app/src')` in container scripts
- Monitor database connectivity with container-appropriate connection strings

#### Database Integration Patterns
```sql
-- PostgreSQL array operations with proper type casting
SELECT * FROM drug_information 
WHERE brand_names @> CAST(ARRAY['drug_name'] AS TEXT[]);

-- Field update strategy (longer content wins)
UPDATE drug_information 
SET mechanism_of_action = CASE 
    WHEN LENGTH(COALESCE(new_value, '')) > LENGTH(COALESCE(mechanism_of_action, '')) 
    THEN new_value 
    ELSE mechanism_of_action 
END;
```

#### Success Metrics from Implementation
- **DrugCentral Integration**: 66% match rate (1,455/2,581 drugs updated)
- **RxClass Classifications**: 100% match rate (7/7 drugs updated)  
- **Field Population**: 4,049 drugs with mechanism_of_action (12.1% improvement)
- **Performance**: Process 33K+ drugs in minutes using optimized matching
- **Data Quality**: Maintained data integrity with comprehensive error handling

## Business Services Implementation Patterns

Based on the successful extraction and integration of 5 business microservices, these patterns ensure scalable and maintainable healthcare architectures.

### Service Extraction Strategy

#### From Monolith to Microservices
The transition from monolithic healthcare-api to distributed business services followed these principles:

1. **Business Logic Identification**: Extract complex business workflows (insurance, billing, compliance)
2. **Service Boundaries**: Define clear boundaries around business capabilities, not technical layers
3. **Data Ownership**: Each service owns its domain data while sharing common infrastructure
4. **Communication Patterns**: Implement resilient service-to-service communication with circuit breakers

#### Service Architecture Patterns
```python
# HTTP Client with Circuit Breaker Pattern
async with get_business_client() as client:
    response: ServiceResponse = await client.verify_insurance(request_data)
    if response.success:
        # Use Chain-of-Thought reasoning from service
        reasoning = response.data.get("reasoning", {})
        process_reasoning(reasoning)
```

### Integration Implementation

#### Agent Integration Pattern
Healthcare agents now delegate to business services instead of implementing business logic:

**Before (Monolithic)**:
```python
class InsuranceAgent(BaseHealthcareAgent):
    async def verify_eligibility(self, data):
        # 200+ lines of business logic embedded in agent
        eligibility_result = self._check_eligibility(data)
        benefits = self._get_benefits_details(data)
        return process_verification(eligibility_result, benefits)
```

**After (Microservices)**:
```python
class InsuranceAgent(BaseHealthcareAgent):
    async def verify_eligibility(self, data):
        # Delegate to specialized service with advanced reasoning
        async with get_business_client() as client:
            response = await client.verify_insurance(data)
            return response.data  # Includes Chain-of-Thought reasoning
```

#### Configuration Management
Business services configuration in `config/business_services.yml`:
- **Environment-aware**: Different timeouts and logging for dev/test/prod
- **Circuit Breaker**: Configurable failure thresholds and recovery patterns
- **PHI Protection**: Environment-specific logging policies for compliance

### Advanced Reasoning Integration

#### Chain-of-Thought for Linear Decisions (Insurance)
Insurance verification uses CoT for step-by-step decision making:
1. Validate member eligibility
2. Check coverage status
3. Determine benefits
4. Apply business rules
5. Generate decision with reasoning trail

#### Tree of Thoughts for Complex Decisions (Billing)
Billing engine uses ToT for exploring multiple decision paths:
1. Code validation (multiple approaches)
2. Amount calculation (various methodologies)
3. Insurance coordination (different strategies)
4. Final decision synthesis

### Compliance Integration

#### Distributed Compliance Monitoring
```python
@compliance_monitor_decorator(
    operation_type="medical_transcription",
    phi_risk_level="high",
    validate_input=True,
    validate_output=True
)
async def transcribe_audio(self, audio_data):
    # Automatic PHI scanning and audit logging
    # Integrated with compliance-monitor service
```

#### Cross-Service Audit Trails
All business service interactions create audit events:
- **Service-to-service calls**: Logged with session tracking
- **PHI exposure detection**: Real-time scanning and alerting
- **Compliance violations**: Automatic detection and response

### Testing Strategies

#### Distributed System Testing
- **Integration Tests**: Validate service-to-service communication
- **Resilience Tests**: Circuit breaker and failure scenario testing
- **Compliance Tests**: PHI protection across service boundaries
- **Performance Tests**: End-to-end response time validation

#### Test Data Management
Use synthetic healthcare data that mirrors production complexity:
- **Patient Scenarios**: Complete healthcare journeys across services
- **Compliance Scenarios**: PHI detection and violation testing
- **Performance Scenarios**: High-volume realistic data loads

### Lessons Learned

#### What Works Well
1. **Static IP Allocation**: Predictable networking (172.20.0.23-27)
2. **Circuit Breaker Patterns**: Prevent cascade failures effectively
3. **Compliance Integration**: Real-time monitoring catches issues early
4. **Advanced Reasoning**: CoT/ToT provides explainable business decisions

#### Key Success Factors
- **Configuration Management**: Environment-aware settings prevent issues
- **PHI-Safe Logging**: Configurable logging policies maintain compliance
- **Service Health Monitoring**: Proactive health checks prevent downtime
- **Comprehensive Testing**: Distributed testing catches integration issues

#### Future Considerations
- **Service Mesh**: Consider Istio/Linkerd for advanced traffic management
- **Event Streaming**: Implement event-driven architecture for loose coupling
- **Auto-scaling**: Implement horizontal scaling based on service load
- **Advanced Monitoring**: Add distributed tracing for complex workflow debugging

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

## Configuration Architecture

### Service Configuration Hierarchy
1. **YAML config files** (source of truth) - Located in `services/user/*/config/`
2. **Environment variables** (overrides) - Use `${VAR:-default}` syntax
3. **Hardcoded defaults** (fallbacks) - In config loaders and classes

### Configuration Loading Patterns

**Healthcare-API Service:**
```python
from config.config_loader import get_config
config = get_config()
```
Config files: `/services/user/healthcare-api/config/*.yml`

**Medical-Mirrors Service:**
```python
from config_loader import get_config
config = get_config()
settings = config.get_llm_settings()
endpoint = config.get_endpoint_url("ollama")
```
Config files: `/services/user/medical-mirrors/config/*.yaml`

**Open WebUI Interfaces:**
- Access configs via `sys.path.append` imports from healthcare-api
- Include fallback configurations for standalone operation
- Use environment variables for containerized deployment

### Key Configuration Files

**Healthcare-API** (`/services/user/healthcare-api/config/`):
- `config_index.yml` - Lists all active configuration files
- `business_services.yml` - Microservice endpoints and settings
- `transcription_config.yml` - Transcription service configuration
- `ui_config.yml` - UI integration settings
- `compliance_config.yml` - HIPAA compliance settings
- `models.yml` - LLM model configurations
- `orchestrator.yml` - Agent routing configuration

**Medical-Mirrors** (`/services/user/medical-mirrors/config/`):
- `service_endpoints.yaml` - External service URLs
- `llm_settings.yaml` - LLM models and generation settings
- `rate_limits.yaml` - API rate limiting configuration
- `ai_enhancement_config.yaml` - AI enhancement settings
- `medical_terminology.yaml` - Medical terms and patterns

### Configuration Best Practices
1. **Never hardcode** service URLs, use config files
2. **Use environment variables** for secrets and API keys
3. **Provide fallbacks** for all configuration values
4. **Document changes** in YAML comments
5. **Validate configs** with pydantic models where possible
6. **Centralize per service** - each service owns its configs
7. **Make accessible** for Open WebUI integration needs