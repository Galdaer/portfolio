## Real-World MCP & Ollama Integration Patterns

### Docker Networking

- Use a user-defined bridge network for multi-container setups:
  ```sh
  docker network create intelluxe-net
  docker run --network intelluxe-net --name ollama-container ... ollama-image
  docker run --network intelluxe-net --name mcp-container ... mcp-image
  ```
- Use container names as hostnames (e.g., `http://ollama-container:11434`) for internal API calls.

### Ollama API Integration

- Set `OLLAMA_API_URL` to the correct address for your environment:
  - Host: `http://host.docker.internal:11434`
  - Docker network: `http://ollama-container:11434`
- Only use `/mcp` endpoint with JSON-RPC payloads for MCP server requests.

### JSON-RPC Payload Example

```sh
curl -X POST http://localhost:3000/mcp \
  -H "Content-Type: application/json" \
  -d "{\"jsonrpc\": \"2.0\", \"method\": \"generate_documentation\", \"params\": {\"prompt\": \"Test prompt\"}, \"id\": 1}"
```

### Troubleshooting Patterns

- If you get "Unknown MCP method", ensure the handler is implemented in `index.ts`.
- For network issues, verify both containers are on the same Docker network.
- Install missing utilities in your dev container as needed:
  ```sh
  sudo apt update && sudo apt install iputils-ping
  ```

### Shell Script Robustness

- Avoid strict flags (`set -euo pipefail`) during debugging.
- Add `set -x` for verbose output.

### PHI Safety

- Always use synthetic data for development and testing.
- Include compliance disclaimers in all documentation and endpoint responses.
# MCP Development Instructions for Intelluxe AI Healthcare System

## MCP Server Integration Strategy

**Healthcare AI infrastructure is now complete** - leverage available MCP servers for feature development and enhancements built on our production-ready foundation.

### Infrastructure Status: PRODUCTION READY ✅

**COMPLETED COMPONENTS** (ready for MCP integration):
- ✅ **Background Task Processing**: HealthcareTaskManager with Redis
- ✅ **Caching Strategy**: HealthcareCacheManager for medical literature  
- ✅ **Health Monitoring**: HealthcareSystemMonitor with comprehensive checks
- ✅ **Authentication & Authorization**: JWT + RBAC with 6 healthcare roles
- ✅ **Configuration Management**: YAML-based healthcare settings
- ✅ **Response Streaming**: Real-time medical literature and AI reasoning
- ✅ **Rate Limiting**: Role-based limits with emergency bypass
- ✅ **API Documentation**: Healthcare-focused OpenAPI with compliance info
- ✅ **Testing Infrastructure**: Integration tests and clinical load simulation

**BLOCKED COMPONENT**: 
- ⏳ **MCP Client Integration**: Waiting for mcps/healthcare/ completion

### Available MCP Servers

#### 1. Healthcare MCP Server (`mcps/healthcare/`)

- **Purpose**: Healthcare-specific tools and PHI-safe operations
- **Location**: Local healthcare MCP server (copied from agentcare-mcp)
- **Use for**: Medical data processing, PHI detection, healthcare compliance validation

#### 2. GitHub MCP Server

- **Purpose**: Repository management, issue tracking, pull request automation
- **Use for**: Code reviews, automated issue creation, repository analysis
- **Key Tools**: Search code, create issues, manage PRs, repository insights

#### 3. Pylance MCP Server

- **Purpose**: Python development assistance with advanced IntelliSense
- **Use for**: Code analysis, type checking, refactoring, import optimization
- **Key Tools**: Syntax validation, import analysis, refactoring automation

#### 4. Sequential Thinking MCP Server

- **Purpose**: Complex problem-solving through structured thinking
- **Use for**: Breaking down complex healthcare AI problems, architecture decisions
- **Key Tools**: Multi-step reasoning, problem decomposition, solution validation

#### 5. Memory MCP Server

- **Purpose**: Persistent memory and context management across development sessions
- **Use for**: Maintaining context in long development tasks, remembering previous solutions
- **Key Tools**: Context storage, session continuity, knowledge retention

**HEALTHCARE COMPLIANCE**: All MCPs are safe for healthcare development since our PHI protection and type safety patterns prevent sensitive data from reaching external services.

### MCP-Powered Development Workflow

#### Phase 1: Analysis & Planning

```markdown
1. **Use Sequential Thinking MCP** for complex problem breakdown
   - Architecture decisions
   - Implementation strategy
   - Risk assessment for healthcare compliance

2. **Use GitHub MCP** for repository context
   - Search existing implementations
   - Analyze related issues and PRs
   - Understand codebase patterns

3. **Use Pylance MCP** for code analysis
   - Validate Python environments
   - Check dependencies and imports
   - Analyze existing code structure
```

#### Phase 2: Implementation

```markdown
1. **Healthcare MCP for medical features**
   - PHI detection and masking
   - Healthcare compliance validation
   - Medical data processing

2. **Pylance MCP for code quality**
   - Real-time syntax checking
   - Import optimization
   - Refactoring assistance

3. **GitHub MCP for collaboration**
   - Create implementation issues
   - Track progress with PRs
   - Code review automation
```

#### Phase 3: Validation & Deployment

```markdown
1. **Sequential Thinking MCP for testing strategy**
   - Comprehensive test planning
   - Edge case identification
   - Validation methodology

2. **Healthcare MCP for compliance**
   - HIPAA compliance validation
   - PHI exposure checks
   - Audit trail verification

3. **GitHub MCP for release management**
   - Automated PR creation
   - Release documentation
   - Issue tracking
```

### RAG-Powered Development Patterns

#### Code Search and Analysis

```python
# Example: Use GitHub MCP to find similar implementations
# Search for existing PHI detection patterns
search_results = github_mcp.search_code("PHI detection healthcare")

# Use Pylance MCP to analyze imports and dependencies
import_analysis = pylance_mcp.analyze_imports(workspace_root)

# Use Sequential Thinking MCP for complex decisions
solution = sequential_thinking_mcp.solve_problem(
    "How to implement HIPAA-compliant real-time PHI detection"
)
```

#### Healthcare-Specific Development

```python
# Example: Healthcare MCP integration for medical features
# Check PHI compliance before processing
phi_result = healthcare_mcp.detect_phi(user_input)

# Validate healthcare configuration
compliance_check = healthcare_mcp.validate_hipaa_compliance(config)

# Generate synthetic medical data for testing
test_data = healthcare_mcp.generate_synthetic_healthcare_data(
    doctors=10, patients=100, encounters=200
)
```

#### Automated Code Quality

```python
# Example: Pylance MCP for code improvement
# Analyze and fix imports
import_fixes = pylance_mcp.fix_imports(file_path)

# Refactor code structure
refactored_code = pylance_mcp.refactor_code(
    file_path, refactor_type="extract_function"
)

# Validate syntax across workspace
syntax_errors = pylance_mcp.check_syntax_errors(workspace_root)
```

### MCP Tool Selection Guidelines

#### When to Use Each MCP Server

**🏥 Healthcare MCP** - Use for:

- Any medical data processing
- PHI detection and masking
- HIPAA compliance validation
- Healthcare workflow automation
- Medical terminology handling

**🐙 GitHub MCP** - Use for:

- Repository analysis and search
- Issue and PR management
- Code review automation
- Release management
- Collaboration workflows

**🐍 Pylance MCP** - Use for:

- Python code analysis
- Import management
- Type checking and validation
- Code refactoring
- Syntax error detection

**🧠 Sequential Thinking MCP** - Use for:

- Complex problem decomposition
- Architecture decision making
- Multi-step reasoning tasks
- Solution validation
- Risk assessment

### Integration with Existing Development Tools

#### VS Code Integration

```json
// .vscode/settings.json additions for MCP
{
  "mcp.servers": {
    "healthcare": {
      "command": "python",
      "args": ["-m", "mcps.healthcare.server"],
      "env": {
        "HEALTHCARE_MCP_MODE": "development"
      }
    }
  }
}
```

#### GitHub Actions Integration

```yaml
# Example: Use MCP servers in CI/CD
- name: Healthcare Compliance Check (MCP-powered)
  run: |
    # Use Healthcare MCP for automated compliance validation
    python3 -c "
    import mcp_client
    healthcare = mcp_client.connect('healthcare')
    result = healthcare.validate_hipaa_compliance('src/')
    print(f'Compliance status: {result.status}')
    "
```

### MCP Development Best Practices

#### 1. Context-Aware Tool Selection

- Always consider the healthcare context when choosing MCP tools
- Prioritize PHI-safe operations and HIPAA compliance
- Use healthcare-specific MCP tools for medical data processing

#### 2. RAG-Enhanced Problem Solving

- Combine multiple MCP servers for comprehensive solutions
- Use Sequential Thinking MCP for complex architectural decisions
- Leverage GitHub MCP for codebase knowledge and patterns

#### 3. Automated Quality Assurance

- Integrate Pylance MCP into development workflow
- Use Healthcare MCP for continuous compliance monitoring
- Automate code reviews with GitHub MCP integration

#### 4. Documentation and Knowledge Sharing

- Document MCP tool usage in code comments
- Create MCP-powered development guides
- Share MCP integration patterns across the team

### Security and Compliance Considerations

#### PHI Protection in MCP Usage

- Never pass real PHI data to external MCP servers
- Use Healthcare MCP (local) for all medical data processing
- Validate MCP tool compliance with healthcare regulations

#### Audit Trail for MCP Operations

- Log all MCP tool interactions for healthcare compliance
- Maintain audit trails for PHI-related MCP operations
- Document MCP tool usage in security reviews

### Future MCP Integrations

#### Planned MCP Server Additions

- **Medical Literature MCP** - For evidence-based development
- **Clinical Workflow MCP** - For healthcare process automation
- **Regulatory Compliance MCP** - For FDA/HIPAA validation

#### Custom Healthcare MCP Tools

- Develop domain-specific MCP tools for:
  - Medical coding (ICD-10, CPT)
  - Clinical decision support
  - Healthcare data integration
  - Regulatory compliance automation

---

**Remember**: MCP servers enable RAG-powered development where agents can access real-time information and tools to enhance development capabilities while maintaining healthcare compliance and security.
