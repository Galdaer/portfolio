# MCP Development Instructions

## Strategic Purpose

**PATIENT-FIRST MCP ARCHITECTURE**: Develop Model Context Protocol servers with quantum-resistant security, offline-first deployment, and military-grade healthcare compliance that prioritizes patient safety over development convenience.

Provide comprehensive patterns for healthcare MCP development with beyond-HIPAA security, patient-first design principles, and advanced clinical integration patterns.

## ✅ BREAKTHROUGH: MCP Integration Working (2025-08-11)

**PROVEN WORKING ARCHITECTURE**: Open WebUI → Pipeline → Healthcare API → Agents → MCP Client → MCP Server

**CRITICAL TRANSPORT REQUIREMENT**: MCP MUST use stdio-only transport via docker exec. HTTP transport causes architectural bypass issues.

**Lazy MCP Client Pattern**: MCP client should connect on first use, not during startup, to prevent blocking healthcare-api initialization.

```python
# ✅ PATTERN: Lazy MCP client connection
class HealthcareMCPClient:
    async def ensure_connected(self):
        if not self.session:
            await self.connect()
    
    async def call_tool(self, name: str, params: Dict[str, Any]):
        await self.ensure_connected()  # Connect on first use
        return await self.session.call_tool(name, params)
```

**Agent Implementation Status**: Architecture working, now need to implement missing agent methods like `process_research_query` in ClinicalResearchAgent.

## Enhanced MCP Architecture

### Patient-First MCP Design Principles

**CORE PRINCIPLE**: Every MCP operation validates patient safety impact before execution, with quantum-resistant security and offline-first healthcare deployment.

**CRITICAL**: See `patterns/healthcare-mcp-auth-proxy.instructions.md` for detailed auth proxy development patterns, type safety requirements, and medical API integration.

```typescript
// Pattern: Patient-first MCP with enhanced security
interface PatientFirstMCPServer {…}

class EnhancedHealthcareMCP implements PatientFirstMCPServer {…}
```

### MCP Pipeline Architecture Integration

**THIN PIPELINE PATTERN**: MCP pipeline serves as minimal proxy, healthcare-api handles all complex logic.

```typescript
// Pattern: Thin MCP pipeline integration
interface ThinPipelineIntegration {
    forwardToHealthcareAPI(request: any): Promise<any>;
    handleTimeout(error: TimeoutError): ErrorResponse;
    transformRequest(openWebUIRequest: any): HealthcareAPIRequest;
}
```

**IMPLEMENTATION REFERENCES**:
- See `patterns/thin-mcp-pipeline.instructions.md` for minimal pipeline patterns
- See `patterns/healthcare-api-orchestration.instructions.md` for API orchestration patterns
- See `tasks/api-development.instructions.md` for MCP integration and authentication patterns

### Open WebUI Integration Patterns

**DIRECT MCP INTEGRATION ARCHITECTURE** (PROVEN SOLUTION): Direct JSON-RPC communication without mcpo bridge provides superior tool discovery and reliability.

**DEVELOPMENT PRIORITY**: Fix Healthcare MCP auth proxy type safety issues (25+ Pylance errors) before implementing new features.

```python
# Pattern: Direct MCP authentication proxy for Open WebUI
class DirectMCPAuthenticationProxy:
    """
    Direct JSON-RPC communication with MCP server via subprocess stdio.
    
    PROVEN ARCHITECTURE: Open WebUI → Auth Proxy (port 3001) → MCP Server (stdio/JSON-RPC)
    RESULT: All 15 healthcare tools properly discovered and accessible
    
    CURRENT STATUS: Needs type safety fixes - see patterns/healthcare-mcp-auth-proxy.instructions.md
    """
    
    async def start_mcp_server(self) -> bool:
        # Start MCP server as subprocess with stdin/stdout communication
        self.mcp_process = subprocess.Popen(
            ["node", "/app/build/index.js"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0
        )
        
        # Send MCP initialization and tools/list requests via JSON-RPC
        await self.initialize_mcp_protocol()
        return await self.discover_tools_via_mcp()
    
    async def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        # Direct JSON-RPC 2.0 tool execution via stdin/stdout
        tool_request = {
            "jsonrpc": "2.0",
            "id": self.request_id_counter,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments}
        }
        # Send request and read response with proper error handling
        pass
```

**CRITICAL SUCCESS FACTORS**:
- **Set MCP_TRANSPORT=stdio**: Enables proper MCP protocol mode instead of HTTP
- **Use subprocess with stdin/stdout**: Direct JSON-RPC 2.0 communication 
- **Genuine tool discovery**: Via MCP tools/list method, not fallback mechanisms
- **No mcpo dependency**: Eliminates compatibility issues and typing problems

### Tool Availability Management

**COMPLETE TOOL ACCESS ACHIEVED**: Direct MCP integration successfully provides all 15 healthcare tools.

```typescript
// Pattern: Complete tool registration via direct MCP protocol
class CompleteMCPToolRegistry {
    // ALL TOOLS AVAILABLE via direct JSON-RPC communication:
    // 1. Medical literature search (search-pubmed)
    // 2. Clinical trial discovery (search-trials) 
    // 3. Drug information access (get-drug-info)
    // 4. Patient data tools (find_patient, get_patient_observations, etc.)
    // 5. FHIR resource management tools
    // Plus 10 additional specialized healthcare tools
}
```

**Environment Configuration Success**:
- Direct MCP integration bypasses API key limitations during tool discovery
- Healthcare MCP server properly exposes all 15 tools via MCP protocol
- Authentication handled at proxy level, not tool registration level
- Result: Open WebUI shows complete tool set regardless of API key status

```bash
# Verify complete tool discovery (all 15 tools now visible)
curl -s "http://172.20.0.12:3001/tools" \
  -H "Authorization: Bearer healthcare-mcp-2025" | jq '.count'
# Returns: 15 (previously only 3 with mcpo bridge approach)
```

### Offline-First Healthcare MCP

**HEALTHCARE DEPLOYMENT REQUIREMENT**: MCP servers must function completely offline for clinical environments with intermittent connectivity.

```typescript
// Pattern: Offline-first MCP with local mirroring
class OfflineFirstHealthcareMCP {
  private mirrorManager: LocalMirrorManager;
  private quantumEncryption: QuantumResistantEncryption;
  
  async handleOfflineRequest(request: MCPRequest): Promise<MCPResponse> {
    // Handle requests using local mirrors and cached data
    const localData = await this.mirrorManager.getLocalData(request);
    const processedData = await this.processWithQuantumSecurity(localData);
    return this.createSecureResponse(processedData);
  }
  
  async synchronizeWhenOnline(): Promise<SyncResult> {
    // Quantum-encrypted synchronization when connection available
    return await this.quantumEncryption.secureSynchronize();
  }
}
```

## Beyond-HIPAA MCP Security

### Quantum-Resistant MCP Communication

**FUTURE-PROOF SECURITY**: Implement MCP communication patterns resistant to quantum computing threats.

```typescript
// Pattern: Quantum-resistant MCP security
class QuantumResistantMCPSecurity {
  async secureMessageTransmission(message: MCPMessage): Promise<SecureMessage> {
    // Post-quantum cryptographic message security
    const quantumKeys = await this.generatePostQuantumKeys();
    const encryptedMessage = await this.latticeBasedEncryption(message, quantumKeys);
    return this.addQuantumSignature(encryptedMessage);
  }
  
  async validateQuantumSignature(message: SecureMessage): Promise<ValidationResult> {
    // Quantum-resistant signature validation
    return await this.hashBasedSignatureValidation(message);
  }
}
```

### Military-Grade MCP Auditing

**ENHANCED AUDITING**: Implement MCP auditing patterns that exceed healthcare compliance requirements.

```typescript
// Pattern: Military-grade MCP auditing
class MilitaryGradeMCPAuditing {…}
```

### MCP-Open WebUI Integration Troubleshooting

**COMMON INTEGRATION ISSUES**:

1. **Authentication Mismatch**: mcpo bridge may not enforce authentication properly
   - Solution: Implement FastAPI authentication proxy with Bearer token validation
   
2. **Tool Discovery**: Only public tools visible (3 tools instead of full 15)
   - Expected: Patient tools require paid API keys (FHIR server, specialized databases)
   - Public tools: search-pubmed, search-trials, get-drug-info
   
3. **Port Conflicts**: Ensure auth proxy and mcpo use different ports
   - Auth proxy: External port (e.g., 3001) for Open WebUI
   - mcpo backend: Internal port (e.g., 3000) for proxy communication

### Docker MCP Integration Patterns

**CONTAINER ARCHITECTURE**: MCP servers with authentication proxy for production deployment.

```dockerfile
# Pattern: Multi-service MCP container with auth proxy
# Install Python dependencies for auth proxy at build time
RUN pip3 install --break-system-packages fastapi uvicorn aiohttp

# Startup script runs both mcpo backend and auth proxy
CMD ["/app/start_services.sh"]
```

```typescript
// Pattern: Military-grade MCP auditing with blockchain
class MilitaryGradeMCPAudit {
  async auditMCPOperation(operation: MCPOperation): Promise<BlockchainAudit> {
    // Triple-redundant audit with blockchain immutability
    const auditRecord = await this.createTripleValidatedAudit(operation);
    const blockchainRecord = await this.addToBlockchain(auditRecord);
    return this.validateAuditIntegrity(blockchainRecord);
  }
  
  async emergencyAuditAlert(violation: SecurityViolation): Promise<AlertResult> {
    // <500ms emergency audit alerts for patient protection
    return await this.immediateSecurityAlert(violation);
  }
}
```

## Advanced Healthcare MCP Tools

### Clinical Reasoning MCP Tools

**TRANSPARENT AI**: Develop MCP tools for clinical reasoning with complete transparency and auditability.

```typescript
// Pattern: Clinical reasoning MCP with transparent logic
class ClinicalReasoningMCP {
  async clinicalAnalysis(clinicalData: ClinicalData): Promise<ReasoningResult> {
    const reasoning = await this.transparentClinicalReasoning(clinicalData);
    const evidence = await this.gatherMedicalEvidence(reasoning);
    const confidence = await this.calculateConfidenceScores(evidence);
    
    return {
      reasoning: reasoning,
      evidence: evidence,
      confidence: confidence,
      auditTrail: await this.createReasoningAudit(reasoning),
      limitations: await this.identifyKnowledgeLimitations(reasoning)
    };
  }
}
```

### Patient Safety MCP Validation

**PATIENT-FIRST VALIDATION**: MCP tools that continuously validate patient safety throughout operations.

```typescript
// Pattern: Patient safety validation MCP
class PatientSafetyMCP {
  async continuousPatientSafetyMonitoring(operations: MCPOperation[]): Promise<SafetyStatus> {
    // Real-time patient safety monitoring for all MCP operations
    const safetyAnalysis = await this.analyzePotentialPatientRisks(operations);
    const emergencyProtocols = await this.checkEmergencyTriggers(safetyAnalysis);
    return this.generatePatientSafetyReport(safetyAnalysis, emergencyProtocols);
  }
  
  async emergencyPatientProtection(threat: PatientThreat): Promise<ProtectionResult> {
    // <500ms emergency patient protection protocols
    return await this.immediatePatientProtection(threat);
  }
}
```

## Enhanced MCP Integration Patterns

### Ollama + Healthcare MCP Integration

**SECURE AI INTEGRATION**: Integrate local Ollama models with healthcare MCP using quantum-resistant communication.

```typescript
// Pattern: Secure Ollama + MCP integration
class SecureOllamaMCPIntegration {
  async processHealthcareQuery(query: HealthcareQuery): Promise<SecureResponse> {
    // Quantum-encrypted communication between Ollama and MCP
    const encryptedQuery = await this.quantumEncryptQuery(query);
    const ollamaResponse = await this.sendToOllama(encryptedQuery);
    const mcpEnhancedResponse = await this.enhanceWithMCP(ollamaResponse);
    return this.createPatientSafeResponse(mcpEnhancedResponse);
  }
}
```

### Real-Time Clinical MCP Streaming

**REAL-TIME HEALTHCARE**: Stream MCP responses for real-time clinical assistance with patient safety priority.

```typescript
// Pattern: Real-time clinical MCP streaming
class RealTimeClinicalMCP {
  async streamClinicalAnalysis(clinicalCase: ClinicalCase): AsyncIterable<ClinicalUpdate> {
    // Stream clinical analysis with continuous patient safety validation
    for await (const analysis of this.analyzeClinicalCase(clinicalCase)) {
      const safetyValidated = await this.validatePatientSafety(analysis);
      if (safetyValidated.safe) {
        yield this.createSecureClinicalUpdate(analysis);
      }
    }
  }
}
```

## Implementation Guidelines

### MCP Security Requirements

**MANDATORY PATTERNS**:
- **Patient Safety First**: All MCP operations validate patient safety impact
- **Quantum-Resistant Communication**: Future-proof MCP message encryption
- **Offline-First Design**: Complete offline functionality for healthcare deployment
- **Military-Grade Auditing**: Enhanced audit trails exceeding healthcare minimums
- **Emergency Response Protocols**: <500ms emergency patient protection

### Healthcare MCP Standards

**ENHANCED REQUIREMENTS**:
- **Zero-PHI-Tolerance**: No PHI exposure in any MCP operation
- **Transparent Clinical Reasoning**: Complete AI reasoning auditability
- **Real-Time Patient Safety**: Continuous patient safety monitoring
- **Blockchain Audit Trails**: Immutable MCP operation logging
- **Emergency Override Protocols**: Patient safety overrides for critical situations

## MCP Development Workflow

### Enhanced Testing Patterns

**COMPREHENSIVE MCP TESTING**: Test MCP servers with realistic healthcare scenarios and patient safety validation.

```typescript
// Pattern: Enhanced MCP testing with patient safety focus
class EnhancedMCPTesting {
  async testPatientSafetyCompliance(mcpServer: MCPServer): Promise<ComplianceResult> {
    // Test MCP compliance with patient safety requirements
    const safetyTests = await this.runPatientSafetyTestSuite(mcpServer);
    const quantumSecurityTests = await this.runQuantumSecurityTests(mcpServer);
    const emergencyResponseTests = await this.runEmergencyResponseTests(mcpServer);
    
    return this.generateComplianceReport(safetyTests, quantumSecurityTests, emergencyResponseTests);
  }
}
```

## Success Metrics

**MCP EXCELLENCE INDICATORS**:
- **100% Patient Safety Validation**: All MCP operations validate patient safety first
- **Quantum-Resistant Security**: All MCP communication uses post-quantum cryptography
- **Complete Offline Functionality**: MCP servers function without internet connectivity
- **<500ms Emergency Response**: Emergency patient protection protocols
- **Immutable Audit Trails**: Complete blockchain-based MCP audit coverage

**PATIENT-FIRST MCP STANDARDS**:
- **Patient Safety Priority**: Every MCP decision prioritizes patient protection
- **Military-Grade Security**: MCP security exceeds healthcare regulatory minimums
- **Transparent Clinical Reasoning**: All AI reasoning fully auditable and explainable
- **Emergency Override Ready**: Life-saving MCP protocols with continuous audit
- **Zero-PHI-Tolerance**: No PHI exposure in any MCP development or deployment phase
