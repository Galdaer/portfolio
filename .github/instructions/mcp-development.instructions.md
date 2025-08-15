# MCP Development Instructions (Updated 2025-01-15)

## CRITICAL: MCP Server Architecture - STOP MAKING MISTAKES

**THE MCP SERVER IS NOT A SEPARATE CONTAINER**
- MCP server is built INSIDE the healthcare-api container at `/app/mcp-server/build/stdio_entry.js`
- Healthcare-api communicates with MCP via STDIO JSON-RPC protocol
- Open WebUI → HTTP → healthcare-api → STDIO → MCP server (all within same container)
- NO separate MCP container, NO HTTP to MCP, NO network calls to MCP

**ARCHITECTURE PATTERN**:
```
Open WebUI (external)
    ↓ HTTP (port 8000)
healthcare-api container
    ├── Python FastAPI server (main.py)
    ├── DirectMCPClient (STDIO communication)
    └── MCP server (/app/mcp-server/build/stdio_entry.js)
```

## Database Integration Fixes (2025-01-15)

**PROBLEM**: Database searches failing with `'str' object has no attribute 'isoformat'` error.

**ROOT CAUSE**: Date fields from PostgreSQL can be either datetime objects or strings, but code assumed datetime objects.

**SOLUTION PATTERN**:
```python
# File: core/database/medical_db.py
# Handle mixed date types from database
def safe_date_format(date_obj):
    """Handle both datetime objects and strings from database."""
    if date_obj:
        if hasattr(date_obj, 'isoformat'):
            return date_obj.isoformat()
        else:
            return str(date_obj)
    return ""

# Apply in database queries
for row in rows:
    article = {
        "pmid": row[0],
        "title": row[1] or "",
        "pub_date": safe_date_format(row[5]),  # Safe date handling
        # ... other fields
    }
```

**FILES AFFECTED**:
- `services/user/healthcare-api/core/database/medical_db.py` (lines 65-85, 130-155)

## ToolRegistry Initialization Fixes (2025-01-15)

**PROBLEM**: ToolRegistry initialization deferred, causing "Database not available" errors.

**ROOT CAUSE**: Async initialization happening in background, not completing before tools were needed.

**SOLUTION PATTERN**:
```python
# File: core/langchain/healthcare_tools.py
from core.async_utils import safe_async_call

async def initialize_tool_registry(client):
    """Force ToolRegistry initialization instead of deferring."""
    logger.info("🔄 Initializing ToolRegistry with MCP client...")
    
    # CRITICAL: Force initialization, don't defer
    await safe_async_call(tool_registry.initialize, client)
    
    if not tool_registry._initialized:
        raise RuntimeError("ToolRegistry failed to initialize")
    
    logger.info("✅ ToolRegistry initialized successfully")
    return tool_registry
```

**FILES AFFECTED**:
- `services/user/healthcare-api/core/langchain/healthcare_tools.py` (line ~45)

## Testing MCP Integration - ENVIRONMENT AWARENESS REQUIRED

**From HOST environment**:
- MCP server binary does NOT exist on host filesystem
- Always mark MCP tests as `pytest.xfail()` when MCP server path not found
- Test imports and tool creation logic, not actual MCP calls
- NEVER assume MCP calls will work from host

**Inside healthcare-api container**:
- MCP server binary exists at `/app/mcp-server/build/stdio_entry.js`
- Full MCP integration testing possible
- MCP communication uses STDIO subprocess, not docker exec

**MCP Client Subprocess Pattern**:
```python
# ✅ CORRECT: Subprocess spawning for MCP communication
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class HealthcareMCPClient:
    def __init__(self):
        # Spawn MCP server as local subprocess
        self.params = StdioServerParameters(
            command="node",
            args=["/app/mcp-server/build/index.js"],
            env={"MCP_TRANSPORT": "stdio"}
        )
    
    async def call_tool(self, tool_name: str, arguments: dict):
        # Each call spawns fresh MCP subprocess
        async with stdio_client(self.params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                
                result = await session.call_tool(tool_name, arguments)
                return result
```

**Container Dockerfile Pattern**:
```dockerfile
# Combined healthcare-api + MCP server container
FROM python:3.12-slim

# Install Node.js for MCP server
RUN apt-get update && apt-get install -y nodejs npm && rm -rf /var/lib/apt/lists/*

# Copy and build MCP server
COPY mcps/healthcare /app/mcp-server
WORKDIR /app/mcp-server
RUN npm install && npm run build

# Copy and install Python API
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Start only FastAPI - MCP spawned as needed
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```
- **Agent Classes**: Inherit from BaseHealthcareAgent, call MCP via dependency injection

**Lazy MCP Client Pattern**: MCP client should connect on first use, not during startup, to prevent blocking healthcare-api initialization.

```python
# ✅ PATTERN: Clean separation with MCP client injection
class BaseHealthcareAgent:
    def __init__(self, mcp_client: Optional[Any] = None):
        self.mcp_client = mcp_client
    
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        # Base implementation with MCP tool access
        if self.mcp_client:
            tools = await self.mcp_client.list_tools()
            # Use tools for enhanced agent capabilities
        pass
```

## MCP Tool Communication Debugging (2025-08-15)

### Broken Pipe Error Resolution Patterns

**PROBLEM SIGNATURE**: `[Errno 32] Broken pipe` errors during LangChain agent MCP tool execution.

**ROOT CAUSE**: Subprocess lifecycle management issues - processes terminated before response streams fully read.

**DEBUGGING PATTERN**:
```python
# ✅ Add comprehensive MCP subprocess monitoring
class MCPSubprocessMonitor:
    """Monitor MCP subprocess lifecycle for broken pipe debugging."""
    
    def __init__(self):
        self.active_processes = {}
        self.logger = logging.getLogger('mcp.subprocess')
    
    def track_process(self, tool_name: str, process: asyncio.subprocess.Process):
        """Track subprocess for lifecycle monitoring."""
        process_id = id(process)
        self.active_processes[process_id] = {
            'tool': tool_name,
            'process': process,
            'started': time.time(),
            'stdin_closed': False,
            'stdout_closed': False
        }
        self.logger.info(f"Started subprocess {process_id} for {tool_name}")
    
    async def check_process_health(self, process_id: int) -> bool:
        """Check if subprocess is still healthy."""
        if process_id not in self.active_processes:
            return False
        
        proc_info = self.active_processes[process_id]
        process = proc_info['process']
        
        # Check if process is still alive
        if process.returncode is not None:
            self.logger.warning(f"Process {process_id} terminated unexpectedly: {process.returncode}")
            return False
        
        # Check stream states
        if process.stdin.is_closing():
            proc_info['stdin_closed'] = True
            self.logger.warning(f"Process {process_id} stdin closed")
        
        if process.stdout.at_eof():
            proc_info['stdout_closed'] = True
            self.logger.warning(f"Process {process_id} stdout at EOF")
        
        return not (proc_info['stdin_closed'] and proc_info['stdout_closed'])

# ✅ Implement connection pooling to prevent rapid subprocess creation/destruction
class MCPConnectionPool:
    """Connection pool to prevent broken pipe errors from rapid subprocess cycling."""
    
    def __init__(self, max_connections: int = 3):
        self.max_connections = max_connections
        self.pool = asyncio.Queue(maxsize=max_connections)
        self.active_connections = {}
        self.logger = logging.getLogger('mcp.pool')
    
    async def get_connection(self, tool_category: str = 'general') -> 'MCPConnection':
        """Get reusable MCP connection from pool."""
        try:
            # Try to get existing connection from pool
            if not self.pool.empty():
                connection = await asyncio.wait_for(self.pool.get(), timeout=0.1)
                if await self._test_connection_health(connection):
                    self.logger.info(f"Reusing pooled connection for {tool_category}")
                    return connection
                else:
                    # Connection unhealthy, clean it up
                    await self._cleanup_connection(connection)
            
            # Create new connection
            self.logger.info(f"Creating new MCP connection for {tool_category}")
            connection = await self._create_new_connection()
            return connection
            
        except Exception as e:
            self.logger.error(f"Failed to get MCP connection: {e}")
            raise
    
    async def return_connection(self, connection: 'MCPConnection'):
        """Return connection to pool for reuse."""
        try:
            if await self._test_connection_health(connection):
                # Only return healthy connections to pool
                if self.pool.qsize() < self.max_connections:
                    await self.pool.put(connection)
                    self.logger.info("Returned connection to pool")
                else:
                    # Pool full, cleanup connection
                    await self._cleanup_connection(connection)
            else:
                # Connection unhealthy, cleanup
                await self._cleanup_connection(connection)
        except Exception as e:
            self.logger.warning(f"Error returning connection to pool: {e}")
    
    async def _test_connection_health(self, connection) -> bool:
        """Test if MCP connection is still healthy."""
        try:
            # Quick health check - try to call a simple tool or ping
            await asyncio.wait_for(connection.ping(), timeout=1.0)
            return True
        except Exception as e:
            self.logger.warning(f"Connection health check failed: {e}")
            return False
    
    async def _create_new_connection(self) -> 'MCPConnection':
        """Create new MCP connection with proper initialization."""
        params = StdioServerParameters(
            command="node",
            args=["/app/mcp-server/build/stdio_entry.js"],
            env={"MCP_TRANSPORT": "stdio", "NODE_ENV": "production"}
        )
        
        connection = MCPConnection(params)
        await connection.initialize()
        return connection
    
    async def _cleanup_connection(self, connection):
        """Properly cleanup MCP connection."""
        try:
            await connection.cleanup()
        except Exception as e:
            self.logger.warning(f"Error during connection cleanup: {e}")

# ✅ Enhanced DirectMCPClient with connection pooling
class DirectMCPClient:
    """Enhanced MCP client with connection pooling and broken pipe prevention."""
    
    def __init__(self):
        self.connection_pool = MCPConnectionPool()
        self.logger = logging.getLogger('mcp.direct_client')
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call MCP tool with connection pooling and error recovery."""
        connection = None
        retry_count = 0
        max_retries = 2
        
        while retry_count <= max_retries:
            try:
                # Get connection from pool
                connection = await self.connection_pool.get_connection(
                    tool_category=self._get_tool_category(tool_name)
                )
                
                # Execute tool with timeout
                self.logger.info(f"Executing {tool_name} with pooled connection")
                result = await asyncio.wait_for(
                    connection.call_tool(tool_name, arguments),
                    timeout=30.0
                )
                
                # Return connection to pool
                await self.connection_pool.return_connection(connection)
                
                self.logger.info(f"Successfully executed {tool_name}")
                return result
                
            except BrokenPipeError as e:
                self.logger.error(f"Broken pipe error in {tool_name} (attempt {retry_count + 1}): {e}")
                # Don't return broken connection to pool
                if connection:
                    await self.connection_pool._cleanup_connection(connection)
                    connection = None
                
                retry_count += 1
                if retry_count <= max_retries:
                    # Brief delay before retry
                    await asyncio.sleep(0.5 * retry_count)
                else:
                    raise
                    
            except asyncio.TimeoutError as e:
                self.logger.error(f"Timeout in {tool_name}: {e}")
                # Connection may be in bad state, don't return to pool
                if connection:
                    await self.connection_pool._cleanup_connection(connection)
                    connection = None
                raise
                
            except Exception as e:
                self.logger.error(f"Unexpected error in {tool_name}: {e}")
                # Return connection if it might still be good
                if connection:
                    await self.connection_pool.return_connection(connection)
                    connection = None
                raise
    
    def _get_tool_category(self, tool_name: str) -> str:
        """Categorize tools for connection affinity."""
        if 'pubmed' in tool_name or 'search' in tool_name:
            return 'search'
        elif 'drug' in tool_name or 'medication' in tool_name:
            return 'pharmaceutical'
        elif 'patient' in tool_name or 'fhir' in tool_name:
            return 'clinical'
        else:
            return 'general'

# ✅ MCP Connection class with proper cleanup patterns
class MCPConnection:
    """Individual MCP connection with proper lifecycle management."""
    
    def __init__(self, params: StdioServerParameters):
        self.params = params
        self.session = None
        self.process = None
        self.logger = logging.getLogger('mcp.connection')
    
    async def initialize(self):
        """Initialize MCP connection with proper error handling."""
        try:
            # Create subprocess with explicit process management
            self.process = await asyncio.create_subprocess_exec(
                *([self.params.command] + list(self.params.args)),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self.params.env
            )
            
            # Create session with streams
            self.session = ClientSession(
                self.process.stdout,
                self.process.stdin
            )
            
            # Initialize session
            await self.session.initialize()
            self.logger.info("MCP connection initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MCP connection: {e}")
            await self.cleanup()
            raise
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call tool with proper error handling."""
        if not self.session:
            raise RuntimeError("MCP connection not initialized")
        
        try:
            result = await self.session.call_tool(tool_name, arguments)
            return result
        except Exception as e:
            self.logger.error(f"Tool call failed: {e}")
            raise
    
    async def ping(self) -> bool:
        """Simple health check for connection."""
        try:
            # Try to list tools as a health check
            await self.session.list_tools()
            return True
        except Exception:
            return False
    
    async def cleanup(self):
        """Properly cleanup connection resources."""
        try:
            if self.session:
                # Close session gracefully
                await self.session.close()
                self.session = None
            
            if self.process and self.process.returncode is None:
                # Terminate process gracefully
                self.process.terminate()
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    # Force kill if graceful termination fails
                    self.process.kill()
                    await self.process.wait()
                
                self.process = None
                
        except Exception as e:
            self.logger.warning(f"Error during cleanup: {e}")
```

### LangChain Integration with MCP Error Handling

```python
# ✅ LangChain agent with robust MCP tool error handling
async def _call_mcp_tool_safe(self, tool_name: str, params: Dict[str, Any]) -> str:
    """Call MCP tool with comprehensive error handling and recovery."""
    try:
        self.logger.info(f"Calling MCP tool: {tool_name}")
        
        # Use enhanced MCP client with connection pooling
        result = await self.mcp_client.call_tool(tool_name, params)
        
        self.logger.info(f"MCP tool {tool_name} completed successfully")
        return str(result)
        
    except BrokenPipeError as e:
        self.logger.error(f"MCP tool {tool_name} broken pipe error: {e}")
        
        # Provide fallback response instead of failing completely
        fallback_response = self._get_tool_fallback_response(tool_name, params)
        return f"Tool {tool_name} temporarily unavailable. {fallback_response}"
        
    except asyncio.TimeoutError as e:
        self.logger.error(f"MCP tool {tool_name} timeout: {e}")
        return f"Tool {tool_name} timed out. Please try again with a more specific query."
        
    except Exception as e:
        self.logger.error(f"MCP tool {tool_name} failed: {e}")
        return f"Tool {tool_name} encountered an error: {str(e)}"

def _get_tool_fallback_response(self, tool_name: str, params: Dict[str, Any]) -> str:
    """Provide fallback guidance when MCP tools fail."""
    fallback_responses = {
        'search-pubmed': "For medical literature, try searching PubMed directly at https://pubmed.ncbi.nlm.nih.gov/",
        'search-clinical-trials': "For clinical trials, visit https://clinicaltrials.gov/",
        'get-drug-info': "For drug information, consult FDA databases or medical references.",
        'search-fhir-patients': "Patient data access requires proper authentication and authorization.",
    }
    
    return fallback_responses.get(tool_name, "Please consult appropriate medical databases directly.")
```

**PROBLEM PATTERN**: MCP tools experiencing "Broken pipe" errors during LangChain agent execution.

**SYMPTOMS**:
- Error: `[Errno 32] Broken pipe` when calling MCP tools
- MCP tool calls start successfully but fail during execution
- LangChain agent retries same tool multiple times with same error
- Direct MCP client works but LangChain integration fails

**ROOT CAUSE ANALYSIS**:
1. **Process Lifecycle Mismatch**: LangChain may be calling tools faster than MCP subprocess can handle
2. **Async Context Issues**: MCP stdio streams not properly managed in async LangChain context
3. **Resource Cleanup**: MCP subprocess terminating before response completion

**DEBUGGING STEPS**:
```python
# 1. Test direct MCP client functionality
async def test_direct_mcp():
    client = DirectMCPClient()
    result = await client.call_tool("search_medical_literature", {"query": "test"})
    print(f"Direct MCP result: {result}")

# 2. Test MCP tool in isolation
from core.langchain.tools import create_mcp_tools
tools = create_mcp_tools(mcp_client)
for tool in tools:
    try:
        result = await tool.arun("test query")
        print(f"Tool {tool.name}: SUCCESS")
    except Exception as e:
        print(f"Tool {tool.name}: FAILED - {e}")

# 3. Monitor subprocess lifecycle
import psutil
def monitor_mcp_processes():
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        if 'node' in proc.info['name'] and 'mcp' in str(proc.info['cmdline']):
            print(f"MCP Process: {proc.info}")
```

**SOLUTION PATTERNS**:

### 1. Robust MCP Tool Wrapper
```python
class RobustMCPTool:
    def __init__(self, tool_name: str, mcp_client, max_retries: int = 3):
        self.tool_name = tool_name
        self.mcp_client = mcp_client
        self.max_retries = max_retries
    
    async def arun(self, query: str) -> str:
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                # Create fresh client session for each attempt
                async with self.mcp_client.create_session() as session:
                    result = await session.call_tool(self.tool_name, {"query": query})
                    return result
                    
            except BrokenPipeError as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff
                    continue
                    
            except Exception as e:
                # Non-retryable error
                raise e
        
        # If all retries failed, return graceful fallback
        return f"Tool {self.tool_name} temporarily unavailable. Please try again."
```

### 2. Session Management Pattern
```python
class HealthcareMCPClient:
    def __init__(self):
        self.session_pool = asyncio.Queue(maxsize=3)  # Limit concurrent sessions
    
    async def call_tool(self, tool_name: str, arguments: dict):
        # Use connection pooling to prevent resource exhaustion
        session = await self._get_session()
        try:
            result = await session.call_tool(tool_name, arguments)
            return result
        finally:
            await self._return_session(session)
    
    async def _get_session(self):
        if self.session_pool.empty():
            return await self._create_fresh_session()
        return await self.session_pool.get()
    
    async def _create_fresh_session(self):
        # Create new subprocess for each session
        async with stdio_client(self.params) as (read_stream, write_stream):
            session = ClientSession(read_stream, write_stream)
            await session.initialize()
            return session
```

**NEXT STEPS FOR BROKEN PIPE INVESTIGATION**:
1. Implement session pooling in DirectMCPClient
2. Add process monitoring to detect subprocess termination
3. Implement graceful fallback when MCP tools fail
4. Add timeout handling for long-running MCP operations

**Agent Implementation Status**: Implementation working with clean stdio/HTTP separation. All agents now use standardized BaseHealthcareAgent interface.

## MCP Implementation Patterns

### Patient-First MCP Design Principles

**CORE PRINCIPLE**: Every MCP operation validates patient safety impact before execution, with quantum-resistant security and offline-first healthcare deployment.

```typescript
// Pattern: Patient-first MCP with enhanced security
interface PatientFirstMCPServer {
    validatePatientSafety(request: any): Promise<boolean>;
    auditMedicalAccess(tool: string, user: string): Promise<void>;
    encryptHealthcareData(data: any): Promise<string>;
}

class EnhancedHealthcareMCP implements PatientFirstMCPServer {
    // Enhanced security implementation with single-container architecture
}
```

### Single-Container MCP Integration

**PROVEN PATTERN**: Healthcare-API container includes MCP server for reliable subprocess communication.

```typescript
// Pattern: Single-container MCP integration
interface HealthcareAPIWithMCP {
    spawnMCPServer(): Promise<MCPProcess>;
    callMCPTool(tool: string, args: any): Promise<any>;
    cleanupMCPProcess(): Promise<void>;
}
```

**IMPLEMENTATION REFERENCES**:
- See `patterns/healthcare-api-orchestration.instructions.md` for single-container patterns
- See `tasks/api-development.instructions.md` for MCP integration without separate containers
- See `tasks/debugging.instructions.md` for subprocess spawning troubleshooting

### Tool Availability Management

**COMPLETE TOOL ACCESS ACHIEVED**: Single-container MCP integration provides all healthcare tools via subprocess spawning.

```python
# Pattern: Complete tool access via subprocess spawning
class SingleContainerMCPClient:
    def __init__(self):
        self.mcp_server_path = "/app/mcp-server/build/index.js"
        
    async def list_tools(self) -> List[str]:
        # Spawn MCP subprocess to get available tools
        async with self.spawn_mcp_process() as mcp_session:
            tools = await mcp_session.list_tools()
            return [tool.name for tool in tools]
    
    async def spawn_mcp_process(self) -> MCPSession:
        # Reliable subprocess spawning in same container
        params = StdioServerParameters(
            command="node",
            args=[self.mcp_server_path],
            env={"MCP_TRANSPORT": "stdio"}
        )
        return MCPSession(params)
``` 
    // 3. Drug information access (get-drug-info)
    // 4. Patient data tools (find_patient, get_patient_observations, etc.)
    // 5. FHIR resource management tools
    // Plus 10 additional specialized healthcare tools
}
```

**Environment Configuration Success**:
- Single-container MCP integration provides reliable tool access via subprocess spawning
- Healthcare MCP server properly exposes all 15 tools via subprocess communication
- Authentication handled at healthcare-api level with integrated security
- Result: All tools available through reliable stdio communication

```bash
# Verify complete tool discovery (all 15 tools now available)
curl -s "http://localhost:8000/agents/medical_search/tools" \
  -H "Content-Type: application/json" | jq '.count'
# Returns: 15 (reliable subprocess communication)
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
class MilitaryGradeMCPAuditing {
  async auditSubprocessSpawning(mcp_process: MCPProcess): Promise<AuditResult> {
    // Audit subprocess spawning for security compliance
    return this.validateSecureSpawning(mcp_process);
  }
}
```

### Single-Container MCP Troubleshooting

**COMMON INTEGRATION ISSUES**:

1. **Node.js Not Found**: MCP server subprocess fails to start
   - Solution: Ensure Node.js is installed in healthcare-api container during build
   - Debug: Node.js availability is tested during container startup
   
2. **MCP Server Path Missing**: subprocess cannot find /app/mcp-server/build/index.js
   - Solution: Verify MCP server build completed successfully in Dockerfile
   - Debug: Path detection is handled by DirectMCPClient environment detection
   
3. **Subprocess Communication Failures**: stdio streams not properly connected
   - Solution: Use StdioServerParameters with proper environment variables
   - Debug: Check MCP_TRANSPORT=stdio environment variable

### Single-Container MCP Deployment Patterns

**INTEGRATED ARCHITECTURE**: Healthcare-API container includes MCP server for reliable subprocess communication.

```dockerfile
# Pattern: Single-container MCP architecture
FROM python:3.12-slim

# Install Node.js for MCP server
RUN apt-get update && apt-get install -y nodejs npm && rm -rf /var/lib/apt/lists/*

# Copy and build MCP server
COPY mcps/healthcare /app/mcp-server
WORKDIR /app/mcp-server
RUN npm install && npm run build

# Copy and install Python API
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

# Start only FastAPI - MCP spawned as subprocess when needed
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
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

## Healthcare MCP Tools

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

## MCP Integration Patterns

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

### Testing Patterns

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
