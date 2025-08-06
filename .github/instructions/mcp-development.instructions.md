## CRITICAL: MCP Offline-First Architecture

### Local Website Mirroring for Client Deployments

**REQUIREMENT**: All MCP tools must function offline for healthcare environments with intermittent internet connectivity.

**Local Mirror Infrastructure:**
```bash
# Create local website mirroring system
#!/bin/bash
# scripts/mirror-mcp-websites.sh

MIRROR_DIR="/opt/intelluxe/mcp-mirrors"
MIRROR_CONFIG="/etc/intelluxe/mirror-sources.yml"

# Mirror MCP-referenced websites
mirror_website() {
    local url="$1"
    local local_path="$2"
    
    wget --mirror --convert-links --adjust-extension \
         --page-requisites --no-parent \
         --directory-prefix="$MIRROR_DIR" \
         --wait=1 --limit-rate=200k \
         "$url"
    
    # Update MCP configuration to use local mirror
    update_mcp_config "$url" "$MIRROR_DIR/$local_path"
}

# Validate mirror integrity
validate_mirror() {
    local mirror_path="$1"
    
    # Check file integrity and update timestamps
    find "$mirror_path" -type f -name "*.html" -exec \
        grep -l "404\|403\|500" {} \; | tee mirror-errors.log
}
```

**MCP Server Offline Support:**
```typescript
// mcps/healthcare/src/offline-handler.ts
interface MirrorConfig {
    enabled: boolean;
    mirrorPath: string;
    fallbackToOnline: boolean;
    lastUpdate: Date;
}

class OfflineCapableHandler {
    private mirrorConfig: MirrorConfig;
    
    async handleRequest(method: string, params: any): Promise<any> {
        if (this.mirrorConfig.enabled && this.isOfflineMode()) {
            return await this.handleOfflineRequest(method, params);
        }
        
        try {
            return await this.handleOnlineRequest(method, params);
        } catch (NetworkError) {
            if (this.mirrorConfig.fallbackToOnline) {
                logger.warn("Falling back to offline mode");
                return await this.handleOfflineRequest(method, params);
            }
            throw;
        }
    }
    
    private async handleOfflineRequest(method: string, params: any): Promise<any> {
        const localData = await this.loadFromMirror(params.query);
        return this.processLocalData(localData);
    }
}
```

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

## CRITICAL DEPENDENCY MANAGEMENT RULES

**❌ NEVER USE THESE COMMANDS:**
- `npm install openai` or `npm install <anything>`  
- `pip install openai` or `pip install <anything>`
- Direct package manager commands

**✅ ALWAYS USE MAKE SYSTEM:**
- `make deps` - Installs ALL dependencies (Python + Node.js + system tools)
- `make mcp-build` - Builds Healthcare MCP server Docker image  
- `make mcp-rebuild` - Rebuilds with no cache
- `make mcp-clean` - Cleans Docker artifacts

**CRITICAL - VERSION VERIFICATION PROTOCOL:**
- **NEVER guess package versions, API parameters, or configuration options**
- **ALWAYS verify current versions using official documentation online** (npmjs.com, PyPI, GitHub releases, official docs)
- **REQUIRED**: Use fetch_webpage tool to check official package registries before specifying versions
- **Examples**: Check npmjs.com/package/openai for OpenAI version, pypi.org for Python packages, official API docs for parameters
- **Pattern**: Research first → Verify current versions/APIs → Then implement with accurate information

**For new dependencies:**
1. **Research versions online first** using fetch_webpage tool
2. Add Python dependencies to `requirements.in` with verified versions
3. Add Node.js dependencies to `mcps/healthcare/package.json` with verified versions  
4. Run `python3 scripts/generate-requirements.py` (if updating requirements.in)
5. Run `make deps` to install everything

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
## Advanced Healthcare MCP Integration Patterns

### Healthcare MCP Server Configuration

```python
# ✅ ADVANCED: Healthcare-specific MCP server configuration
class HealthcareMCPServerManager:
    """Advanced MCP server management for healthcare AI systems."""
    
    def generate_healthcare_mcp_config(self) -> Dict[str, Any]:
        """Generate comprehensive MCP configuration for healthcare development."""
        
        return {
            "inputs": [
                {
                    "type": "promptString",
                    "id": "healthcare-compliance-key",
                    "description": "Healthcare compliance validation key",
                    "password": True
                }
            ],
            "servers": {
                # Local Healthcare MCP Server (PHI-safe)
                "healthcare": {
                    "type": "stdio",
                    "command": "node",
                    "args": ["mcps/healthcare/build/index.js"],
                    "env": {
                        "HEALTHCARE_COMPLIANCE_MODE": "strict",
                        "PHI_PROTECTION_LEVEL": "maximum",
                        "AUDIT_LOGGING": "comprehensive",
                        "MEDICAL_DISCLAIMERS": "enabled"
                    },
                    "dev": {
                        "watch": "mcps/healthcare/build/**/*.js",
                        "debug": {"type": "node"}
                    }
                },
                # Sequential Thinking for Clinical Reasoning
                "sequential_thinking": {
                    "type": "stdio", 
                    "command": "npx",
                    "args": ["-y", "sequential-thinking-mcp"],
                    "healthcare_integration": True,
                    "clinical_reasoning": True
                },
                # Memory MCP with PHI Protection
                "memory": {
                    "type": "stdio",
                    "command": "npx", 
                    "args": ["-y", "memory-mcp"],
                    "phi_protection": True,
                    "healthcare_context": True
                },
                # GitHub MCP for Healthcare Codebase
                "github": {
                    "url": "https://api.githubcopilot.com/mcp/",
                    "healthcare_repository": True,
                    "compliance_scanning": True
                }
            },
            "healthcare_tool_sets": {
                "clinical_analysis": [
                    "mcp_healthcare-mc_literature_search",
                    "mcp_healthcare-mc_clinical_entity_extraction", 
                    "mcp_healthcare-mc_medical_terminology_validation",
                    "mcp_sequentialthi_sequentialthinking"
                ],
                "patient_workflow": [
                    "mcp_healthcare-mc_soap_note_generation",
                    "mcp_healthcare-mc_clinical_documentation_review",
                    "mcp_healthcare-mc_workflow_optimization"
                ],
                "compliance_validation": [
                    "mcp_healthcare-mc_phi_detection",
                    "mcp_healthcare-mc_hipaa_compliance_check",
                    "mcp_healthcare-mc_audit_trail_generation"
                ],
                "clinical_reasoning": [
                    "mcp_sequentialthi_sequentialthinking",
                    "mcp_memory_store_memory",
                    "mcp_memory_search_memory",
                    "mcp_healthcare-mc_differential_diagnosis"
                ]
            }
        }
    
    async def register_healthcare_mcp_tools(self):
        """Register healthcare-specific MCP tools with compliance wrappers."""
        
        # Clinical literature search with PHI protection
        @healthcare_mcp_tool("literature_search")
        async def clinical_literature_search(query: str, specialty: str = None):
            """Search medical literature with PHI safety and evidence grading."""
            
            # Sanitize query for PHI before external search
            sanitized_query = await self.sanitize_phi_from_query(query)
            
            # Search with healthcare-specific filters
            results = await self.search_medical_literature(
                query=sanitized_query,
                specialty=specialty,
                evidence_level="peer_reviewed",
                safety_validated=True
            )
            
            # Add medical disclaimers and evidence grading
            enhanced_results = [
                self.add_evidence_grading(result)
                for result in results
            ]
            
            return {
                "results": enhanced_results,
                "medical_disclaimer": "This literature search is for educational purposes only.",
                "evidence_quality": self.assess_overall_evidence_quality(enhanced_results),
                "search_metadata": {
                    "query_sanitized": True,
                    "phi_protected": True,
                    "specialty": specialty
                }
            }
        
        # Clinical reasoning with sequential thinking integration
        @healthcare_mcp_tool("clinical_reasoning")
        async def clinical_reasoning_workflow(case: Dict[str, Any]):
            """Advanced clinical reasoning using sequential thinking patterns."""
            
            # Use sequential thinking MCP for clinical reasoning
            reasoning_steps = await self.mcp_sequential_thinking({
                "clinical_case": case,
                "reasoning_type": "medical_differential_diagnosis",
                "safety_validation": True,
                "evidence_based": True
            })
            
            # Enhance with medical context and safety validation
            clinical_reasoning = await self.enhance_clinical_reasoning(reasoning_steps)
            
            return {
                "reasoning_chain": clinical_reasoning,
                "differential_diagnoses": clinical_reasoning.get("diagnoses", []),
                "evidence_summary": clinical_reasoning.get("evidence", {}),
                "uncertainty_quantification": clinical_reasoning.get("uncertainty", 0.0),
                "medical_disclaimer": "This reasoning supports clinical decision-making but does not replace professional medical judgment."
            }

### Healthcare MCP Development Patterns

```python
# ✅ ADVANCED: Healthcare MCP tool development with compliance integration
def healthcare_mcp_tool(tool_name: str):
    """Decorator for healthcare MCP tools with automatic compliance."""
    
    def decorator(func: Callable):
        @wraps(func)
        async def healthcare_compliance_wrapper(*args, **kwargs):
            
            # Pre-execution compliance validation
            compliance_check = await validate_healthcare_operation(
                tool_name=tool_name,
                args=args,
                kwargs=kwargs
            )
            
            if not compliance_check.is_compliant:
                return {
                    "error": "Healthcare compliance validation failed",
                    "compliance_issues": compliance_check.issues,
                    "medical_disclaimer": "Operation blocked for patient safety."
                }
            
            # PHI protection for all inputs
            sanitized_args = await sanitize_phi_from_args(args, kwargs)
            
            # Execute with healthcare audit logging
            with healthcare_operation_context(f"mcp_{tool_name}") as ctx:
                try:
                    result = await func(*sanitized_args)
                    
                    # Add medical disclaimers to all results
                    if isinstance(result, dict):
                        result["medical_disclaimer"] = get_appropriate_medical_disclaimer(tool_name)
                    
                    # Log successful healthcare operation
                    ctx.log_successful_operation(tool_name, result.get("status", "completed"))
                    
                    return result
                    
                except Exception as e:
                    ctx.log_healthcare_error(tool_name, str(e))
                    return {
                        "error": "Healthcare operation failed",
                        "tool": tool_name,
                        "medical_disclaimer": "Clinical operation could not be completed safely."
                    }
        
        return healthcare_compliance_wrapper
    return decorator

# ✅ ADVANCED: Healthcare MCP agent coordination
class HealthcareMCPAgentCoordinator:
    """Coordinate multiple MCP tools for complex healthcare workflows."""
    
    async def coordinate_clinical_workflow(self, workflow: ClinicalWorkflow):
        """Coordinate multiple MCP tools for complex clinical cases."""
        
        # Phase 1: Information gathering with parallel MCP tools
        info_tasks = {
            "literature": self.call_mcp_tool("literature_search", {
                "query": workflow.clinical_question,
                "specialty": workflow.specialty
            }),
            "reasoning": self.call_mcp_tool("sequential_thinking", {
                "thought": f"Analyze clinical case: {workflow.clinical_question}",
                "healthcare_context": True
            }),
            "memory": self.call_mcp_tool("memory_search", {
                "query": workflow.clinical_question,
                "healthcare_context": True
            })
        }
        
        # Execute information gathering with timeout
        info_results = await asyncio.gather(
            *info_tasks.values(),
            return_exceptions=True
        )
        
        # Phase 2: Clinical synthesis using gathered information
        synthesis_input = {
            "literature_findings": info_results[0] if not isinstance(info_results[0], Exception) else None,
            "reasoning_steps": info_results[1] if not isinstance(info_results[1], Exception) else None,
            "relevant_memory": info_results[2] if not isinstance(info_results[2], Exception) else None,
            "clinical_question": workflow.clinical_question
        }
        
        # Final clinical synthesis with medical disclaimers
        clinical_synthesis = await self.call_mcp_tool("clinical_synthesis", synthesis_input)
        
        # Store workflow results in memory for future reference
        await self.call_mcp_tool("memory_store", {
            "workflow_id": workflow.id,
            "clinical_synthesis": clinical_synthesis,
            "healthcare_context": True,
            "phi_protected": True
        })
        
        return clinical_synthesis
```

### Security and Compliance Considerations

#### PHI Protection in MCP Usage

- Never pass real PHI data to external MCP servers
- Use Healthcare MCP (local) for all medical data processing
- Validate MCP tool compliance with healthcare regulations
- **CRITICAL**: All MCP tools must use PHI sanitization wrappers

#### Audit Trail for MCP Operations

- Log all MCP tool interactions for healthcare compliance
- Maintain audit trails for PHI-related MCP operations
- Document MCP tool usage in security reviews
- **NEW**: Comprehensive healthcare operation context logging

#### Advanced Healthcare MCP Security

```python
# ✅ ADVANCED: MCP security validation for healthcare
async def validate_mcp_healthcare_security(mcp_operation: Dict[str, Any]) -> SecurityValidation:
    """Validate MCP operations against healthcare security requirements."""
    
    security_checks = {
        "phi_protection": await check_phi_protection(mcp_operation),
        "audit_logging": await verify_audit_logging(mcp_operation),
        "compliance_validation": await validate_hipaa_compliance(mcp_operation),
        "medical_disclaimer": await verify_medical_disclaimers(mcp_operation),
        "emergency_handling": await check_emergency_protocols(mcp_operation)
    }
    
    return SecurityValidation(
        is_secure=all(security_checks.values()),
        security_results=security_checks,
        recommendations=generate_security_recommendations(security_checks)
    )
```

### Future MCP Integrations

#### Planned MCP Server Additions

- **Medical Literature MCP** - For evidence-based development
- **Clinical Workflow MCP** - For healthcare process automation  
- **Regulatory Compliance MCP** - For FDA/HIPAA validation
- **FHIR Integration MCP** - For healthcare interoperability
- **Medical Device MCP** - For device integration and monitoring

#### Custom Healthcare MCP Tools

- Develop domain-specific MCP tools for:
  - Medical coding (ICD-10, CPT)  
  - Clinical decision support with evidence grading
  - Healthcare data integration with PHI protection
  - Regulatory compliance automation
  - Multi-agent clinical workflow coordination
  - Real-time patient monitoring with WebSocket integration

---

**Remember**: MCP servers enable RAG-powered development where agents can access real-time information and tools to enhance development capabilities while maintaining healthcare compliance, PHI protection, and medical safety throughout all operations.
