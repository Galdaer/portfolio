# Claude Code Specialized Agents

This directory contains specialized Claude Code agents that enhance development autonomy and efficiency for the Intelluxe AI healthcare system.

## Overview

These agents are automatically invoked by Claude Code when specific trigger keywords are detected in user requests. They provide specialized expertise for complex development tasks while maintaining consistency with the healthcare system's architecture, security, and compliance requirements.

## Agent Categories

### Business Service and Integration Agents

#### **BusinessServiceAnalyzer**
- **Purpose**: Extract business logic from existing healthcare agents into standalone microservices
- **Triggers**: extract service, standalone microservice, business logic separation, service extraction
- **Key Features**:
  - Analyzes existing agents for extractable business logic
  - Designs FastAPI-based microservice architectures with static IP allocation
  - Implements Chain-of-Thought and Tree of Thoughts reasoning patterns
  - Generates complete Docker configurations and service scaffolding

#### **PhaseDocumentAnalyzer**
- **Purpose**: Analyze phase documents and cross-reference with current implementation
- **Triggers**: phase analysis, implementation status, TODO generation, project roadmap
- **Key Features**:
  - Parses PHASE_*.md documents to extract planned features
  - Cross-references plans against current codebase implementation
  - Generates comprehensive TODO.md files with prioritized tasks
  - Calculates completion percentages and tracks progress over time

#### **ServiceIntegrationAgent**  
- **Purpose**: Handle integration between multiple microservices
- **Triggers**: service integration, microservice communication, inter-service API, distributed system
- **Key Features**:
  - Designs RESTful APIs for service-to-service communication
  - Implements circuit breaker patterns and retry logic with exponential backoff
  - Creates distributed transaction patterns using Saga orchestration
  - Sets up service authentication and comprehensive audit logging

#### **ComplianceAutomationAgent**
- **Purpose**: Automate HIPAA compliance monitoring and regulatory reporting
- **Triggers**: compliance automation, audit setup, violation rules, compliance reporting
- **Key Features**:
  - Generates HIPAA violation detection rules with configurable thresholds
  - Creates automated compliance dashboards with real-time metrics
  - Sets up comprehensive audit trail monitoring and analysis
  - Implements automated regulatory reporting for compliance officers

## Agent Usage Patterns

### Automatic Invocation

Claude Code automatically selects and invokes these agents based on keyword detection in user requests. For example:

- **"Extract the billing logic into a separate service"** → BusinessServiceAnalyzer
- **"What's our implementation status against the phase documents?"** → PhaseDocumentAnalyzer
- **"Set up communication between services"** → ServiceIntegrationAgent
- **"Set up automated HIPAA compliance monitoring"** → ComplianceAutomationAgent

### Manual Invocation

You can manually request specific agents by mentioning them:
- "Use the BusinessServiceAnalyzer to extract the insurance verification service"
- "Use the PhaseDocumentAnalyzer to generate a comprehensive TODO list"

### Agent Combinations

For complex workflows, multiple agents work together:

**Service Development Workflow:**
1. PhaseDocumentAnalyzer → Analyze what services need to be built
2. BusinessServiceAnalyzer → Extract and design the services
3. ServiceIntegrationAgent → Set up service communication
4. ComplianceAutomationAgent → Add compliance monitoring

**System Analysis and Optimization:**
1. PhaseDocumentAnalyzer → Understand current vs. planned state
2. StorageOptimizationAgent → Optimize data storage
3. PerformanceOptimizationAgent → Optimize system performance
4. TestAutomationAgent → Add comprehensive testing

## Architecture Integration

All agents are designed to work with the Intelluxe AI healthcare system's architecture:

### Service Communication Patterns
- Static IP allocation on intelluxe-net (172.20.0.x)
- Shared PostgreSQL (172.20.0.11) and Redis (172.20.0.12)
- Health checks at `/health` endpoints
- Circuit breaker patterns for fault tolerance
- JWT-based service authentication

### Healthcare Compliance
- HIPAA compliance built into all patterns
- PHI detection and sanitization
- Comprehensive audit logging
- Compliance reporting and monitoring
- Security-first architecture

### Development Standards
- FastAPI for all service implementations
- Docker containerization with health checks
- Async/await patterns throughout
- Comprehensive testing with pytest
- Ruff for code formatting and linting

## Key Benefits

### **Consistency**
All agents follow established patterns and architectural principles, ensuring consistent implementation across the system.

### **Compliance**
Healthcare compliance (HIPAA, PHI protection, audit logging) is built into every agent's implementation patterns.

### **Autonomy**
Agents can handle complex multi-step tasks independently, reducing the need for manual intervention and guidance.

### **Knowledge Preservation**
Institutional knowledge about the system architecture, patterns, and best practices is captured in reusable agent instructions.

### **Quality Assurance**
All agents include testing, validation, and quality assurance measures appropriate for healthcare systems.

## Agent Development Guidelines

When creating new agents:

1. **Follow Healthcare Standards**: Include HIPAA compliance, PHI protection, and audit logging
2. **Use Established Patterns**: Follow the architectural patterns used by existing services
3. **Include Testing**: Generate comprehensive test suites for all implementations
4. **Document Everything**: Provide clear documentation and usage examples
5. **Integration Ready**: Ensure agents work well with existing system components

## Future Expansion

The agent ecosystem can be expanded with additional specialized agents for:

- **Medical Data Processing**: Specialized handling of clinical data formats
- **Integration Testing**: End-to-end testing across distributed services  
- **Performance Monitoring**: Real-time system performance analysis
- **Security Auditing**: Automated security assessment and penetration testing
- **Clinical Workflow**: Healthcare-specific workflow optimization

## Contributing

When adding new agents:

1. Create agent instruction file in `.claude/agents/`
2. Update `CLAUDE_AGENTS.md` with agent description and usage patterns
3. Add trigger keywords to `CLAUDE.md` proactive agent selection
4. Include agent in appropriate workflow combinations
5. Test agent functionality with realistic scenarios

## Support

For questions about agent usage or development:

1. Refer to the comprehensive documentation in `CLAUDE_AGENTS.md`
2. Check the architectural patterns in `CLAUDE.md`
3. Review existing agent implementations for patterns
4. Test agents with small-scale examples before complex implementations

This agent ecosystem makes the Intelluxe AI healthcare system more autonomous, maintainable, and efficient while preserving the high standards of security, compliance, and quality required for healthcare applications.