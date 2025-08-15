# Healthcare AI Debugging Instructions

## Healthcare-Specific Debugging Patterns

### PHI Detection False Positive Debugging (2025-08-15) **[CRITICAL PRIORITY]**

**PROBLEM PATTERN**: PHI detection system incorrectly flagging normal medical queries as containing PHI, causing over-sanitization.

**SYMPTOMS TO WATCH FOR**:
- Normal medical terms being masked with asterisks (`*****`)
- Log entries: `🛡️ PHI detected in request message 0, types: ['name']`
- Medical queries about conditions being treated as containing names
- User interface showing masked responses for legitimate medical content

**ROOT CAUSE**: Presidio PHI detection patterns too broad, medical terminology triggering name/person entity detection.

**DEBUGGING STEPS**:
1. **Check PHI Detection Logs**:
   ```bash
   tail -f logs/healthcare_system.log | grep "PHI detected"
   tail -f logs/phi_monitoring.log
   ```

2. **Test PHI Detection in Isolation**:
   ```python
   from core.phi_sanitizer import PHISanitizer
   sanitizer = PHISanitizer()
   result = sanitizer.detect_phi("cardiovascular health")
   print(f"PHI detected: {result.has_phi}")
   print(f"Entity types: {[e.entity_type for e in result.entities]}")
   ```

3. **Examine PHI Configuration**:
   ```bash
   cat config/phi_detection_config.yaml
   # Check for overly broad name patterns
   ```

4. **Test with Medical vs Personal Content**:
   ```python
   # Should NOT be flagged as PHI
   medical_queries = ["diabetes symptoms", "cardiovascular health", "cancer treatment"]
   
   # SHOULD be flagged as PHI  
   phi_content = ["Patient John Smith", "DOB: 01/01/1980", "SSN: 123-45-6789"]
   ```

**SOLUTION PATTERN**:
```yaml
# ❌ PROBLEMATIC: Too broad name detection
entities:
  - name: PERSON
    patterns:
      - "[A-Z][a-z]+ [A-Z][a-z]+"  # Catches "cardiovascular health"

# ✅ CORRECT: More specific patterns with medical exclusions  
entities:
  - name: PERSON
    patterns:
      - "(?<!medical |disease |condition |health )[A-Z][a-z]+ [A-Z][a-z]+"
    exclusions:
      - medical_terms.txt
```

**FILES TO CHECK**:
- `core/phi_sanitizer.py` - PHI detection logic  
- `src/healthcare_mcp/phi_detection.py` - Presidio configuration
- `main.py` lines 749, 802 - Request/response sanitization
- `config/phi_detection_config.yaml` - PHI detection patterns

### Enhanced Medical Query Engine Integration Debugging (2025-08-15)

**PROBLEM PATTERN**: Enhanced Medical Query Engine integration causing type errors or interface mismatches.

**SYMPTOMS TO WATCH FOR**:
- Import errors for `EnhancedMedicalQueryEngine` or `QueryType`
- Type mismatches between `MedicalQueryResult` and `MedicalSearchResult`
- Agent initialization failures with enhanced engine
- Intent classification not mapping to QueryType correctly

**DEBUGGING STEPS**:
1. **Test Enhanced Engine Integration**:
   ```bash
   cd /home/intelluxe && python3 tests/test_enhanced_medical_query_engine_integration.py
   ```

2. **Check Import Paths**:
   ```python
   from core.medical.enhanced_query_engine import EnhancedMedicalQueryEngine, QueryType
   from agents.medical_search_agent.medical_search_agent import MedicalLiteratureSearchAssistant
   ```

3. **Verify Agent Enhanced Engine Initialization**:
   ```python
   agent = MedicalLiteratureSearchAssistant(mcp_client, llm_client)
   print(f"Enhanced engine: {hasattr(agent, '_enhanced_query_engine')}")
   print(f"Type: {type(agent._enhanced_query_engine) if hasattr(agent, '_enhanced_query_engine') else 'Missing'}")
   ```

**SOLUTION PATTERN**:
```python
# ✅ CORRECT: Enhanced engine initialization in agent constructor
def __init__(self, mcp_client: object, llm_client: object) -> None:
    super().__init__(mcp_client, llm_client, agent_name="medical_search", agent_type="literature_search")
    
    # Initialize Enhanced Medical Query Engine for Phase 2 capabilities
    self._enhanced_query_engine = EnhancedMedicalQueryEngine(mcp_client, llm_client)
    logger.info("Enhanced Medical Query Engine initialized for sophisticated medical search")
```

**FILES TO CHECK**:
- `agents/medical_search_agent/medical_search_agent.py` - Agent integration
- `core/medical/enhanced_query_engine.py` - Enhanced engine implementation
- `tests/test_enhanced_medical_query_engine_integration.py` - Integration validation

### Ollama LangChain Connection Debugging (2025-08-15)

**PROBLEM PATTERN**: LangChain agents failing with "All connection attempts failed" when connecting to Ollama.

**SYMPTOMS TO WATCH FOR**:
- Error: `httpx.ConnectError: All connection attempts failed`
- LangChain agent initialization succeeds but processing fails
- Stack trace showing connection failures in `langchain_ollama/chat_models.py`
- MCP tools work but LLM processing fails

**ROOT CAUSE**: Docker hostname resolution issues - LangChain configured for container environment but running in local environment.

**DEBUGGING STEPS**:
1. **Check Ollama Service Status**:
   ```bash
   systemctl status ollama || ps aux | grep ollama
   curl -s http://172.20.0.10:11434/api/version
   ```

2. **Verify Environment Variables**:
   ```bash
   echo "OLLAMA_URL: $OLLAMA_URL"
   export OLLAMA_URL="http://172.20.0.10:11434"
   ```

3. **Test Direct LLM Connection**:
   ```python
   # Test without MCP tools to isolate connection issue
   from langchain_core.messages import HumanMessage
   response = await agent.llm.ainvoke([HumanMessage(content='test')])
   ```

**SOLUTION PATTERN**:
```python
# ❌ PROBLEMATIC: Docker hostname in local environment
config = OllamaConfig(
    base_url=_os.getenv("OLLAMA_URL", "http://172.20.0.10:11434"),  # Fails locally
)

# ✅ CORRECT: Localhost default with environment override
config = OllamaConfig(
    base_url=_os.getenv("OLLAMA_URL", "http://172.20.0.10:11434"),  # Works locally
)
```

**FILES TO CHECK**:
- `services/user/healthcare-api/core/langchain/agents.py` - LangChain agent Ollama configuration
- `services/user/healthcare-mcp/src/server/HealthcareServer.ts` - MCP server Ollama configuration
- Container environment variables and docker-compose.yml Ollama service definitions

### MCP Broken Pipe Debugging (2025-08-15)

**PROBLEM PATTERN**: MCP tools work in isolation but fail with "Broken pipe" errors during LangChain agent execution.

**SYMPTOMS TO WATCH FOR**:
- Error: `[Errno 32] Broken pipe` in MCP tool execution
- MCP tools work via direct `call_tool()` but fail in LangChain context
- Subprocess stdio stream errors
- Tool execution starts but doesn't complete

**ROOT CAUSE**: Subprocess lifecycle management issues - MCP client spawning processes without proper session management.

**DEBUGGING STEPS**:
1. **Test MCP Tools in Isolation**:
   ```python
   # Direct MCP tool test
   client = DirectMCPClient()
   result = await client.call_tool('search-pubmed', {'query': 'test'})
   ```

2. **Monitor Subprocess Lifecycle**:
   ```bash
   # Monitor subprocess creation during agent execution
   ps aux | grep mcp-server | wc -l  # Before
   # Run LangChain agent
   ps aux | grep mcp-server | wc -l  # After
   ```

3. **Check Stream Status**:
   ```python
   # In DirectMCPClient, add debugging:
   logger.info(f"Process alive: {self.process.poll() is None}")
   logger.info(f"Stdin closed: {self.process.stdin.is_closing()}")
   ```

**SOLUTION PATTERN**:
```python
# ❌ PROBLEMATIC: Process spawned without lifecycle management
async def call_tool(self, name, params):
    process = await asyncio.create_subprocess_exec(...)
    # Process may be terminated before response read

# ✅ CORRECT: Connection pooling with proper cleanup
class MCPSessionPool:
    async def get_session(self):
        # Reuse existing sessions, manage lifecycle
        # Implement graceful shutdown patterns
```

**FILES TO CHECK**:
- `services/user/healthcare-api/core/mcp/direct_mcp_client.py` - Primary location for subprocess management fixes

### Open WebUI Integration Debugging (2025-08-15)

**PROBLEM PATTERN**: Healthcare agents not being triggered or logged when accessed through Open WebUI interface.

**SYMPTOMS TO WATCH FOR**:
- No entries in `logs/agent_medical_search.log` during Open WebUI queries
- Healthcare API responds but agents not executing
- MCP tools working but not being called in medical context
- Open WebUI receives generic responses instead of medical-specific responses

**DEBUGGING STEPS**:
1. **Verify Agent Registration**:
   ```python
   # Check if agents are properly registered in healthcare API
   from core.agent_coordinator import AgentCoordinator
   coordinator = AgentCoordinator()
   print(coordinator.list_agents())  # Should include medical search agent
   ```

2. **Test Direct Agent Invocation**:
   ```python
   # Bypass Open WebUI to test agent directly
   from agents.medical_search import MedicalLiteratureSearchAssistant
   agent = MedicalLiteratureSearchAssistant()
   result = await agent.process("diabetes complications")
   ```

3. **Check Open WebUI Request Routing**:
   ```bash
   # Monitor healthcare API access logs
   tail -f logs/healthcare_system.log | grep -E "(medical|search|agent)"
   ```

**SOLUTION PATTERNS**:
- Verify agent intent classification patterns in medical query routing
- Ensure Open WebUI requests trigger correct agent selection logic
- Check healthcare API endpoint configuration for agent coordination
- `services/user/healthcare-api/core/langchain/agents.py` (main config)
- `services/user/healthcare-mcp/src/server/HealthcareServer.ts` (MCP server config)
- Any Docker compose files or environment configuration

### MCP Container Architecture Debugging (2025-01-15) **[CRITICAL UPDATE]**

**PROBLEM PATTERN**: MCP "broken pipe" errors resolved through container architecture understanding.

**KEY ARCHITECTURAL INSIGHT**: MCP server runs INSIDE healthcare-api container, not as separate service.

**CONTAINER ARCHITECTURE**:
```
Healthcare API Container:
├── Python Healthcare API (FastAPI)
├── DirectMCP Client (Python)
└── MCP Server (/app/mcp-server/build/stdio_entry.js) ← RUNS HERE
```

**RESOLVED ISSUE PATTERN**:
```python
# ❌ OLD BROKEN PATTERN: Expecting MCP on host
mcp_server_path = "/home/intelluxe/mcp-server/build/index.js"  # Host path (broken)

# ✅ WORKING PATTERN: Container-aware path detection
def _detect_mcp_server_path(self) -> Optional[str]:
    """Detect MCP server path for container vs host environment."""
    container_paths = [
        "/app/mcp-server/build/stdio_entry.js",  # Container path
        "/app/build/index.js"  # Alternative container path
    ]
    host_paths = [
        "/home/intelluxe/services/user/healthcare-mcp/build/index.js",
        "/home/intelluxe/mcp-server/build/index.js"
    ]
    
    # Try container paths first (production environment)
    for path in container_paths + host_paths:
        if Path(path).exists():
            return path
    return None
```

**DEBUGGING STEPS FOR MCP ISSUES**:
1. **Verify MCP server location**:
   ```bash
   # In container environment
   ls -la /app/mcp-server/build/
   # In host environment  
   ls -la /home/intelluxe/services/user/healthcare-mcp/build/
   ```

2. **Test container vs host detection**:
   ```python
   from core.mcp.direct_mcp_client import DirectMCPClient
   client = DirectMCPClient()
   print(f"Detected MCP path: {client._detect_mcp_server_path()}")
   ```

3. **Check environment-aware error messages**:
   ```python
   # ✅ Clear error messages (not broken pipes)
   if not mcp_server_path:
       if self._is_container_environment():
           raise FileNotFoundError("MCP server not found in container at expected paths")
       else:
           raise FileNotFoundError("MCP server not found on host - run 'make setup'")
   ```

**CONTAINER-AWARE TESTING PATTERN**:
```python
# ✅ Tests that work in both environments
@pytest.mark.asyncio
async def test_mcp_container_architecture():
    """Test MCP client with container architecture awareness."""
    client = DirectMCPClient()
    
    # Test graceful degradation on host (no MCP server)
    if not client._detect_mcp_server_path():
        # Host environment - should fail gracefully
        with pytest.raises(FileNotFoundError, match="MCP server not found"):
            await client.call_tool("search-pubmed", {"query": "test"})
    else:
        # Container environment - should work
        tools = await client.get_available_tools()
        assert len(tools) > 0
```

**FILES AFFECTED**:
- `core/mcp/direct_mcp_client.py` - Container path detection
- `tests/test_container_architecture_integration.py` - Architecture-aware tests

### Open WebUI Agent Iteration Debugging (2025-01-15) **[NEW ISSUE]**

**PROBLEM PATTERN**: Medical queries through Open WebUI fail with "Agent stopped due to iteration limit or time limit".

**SYMPTOMS TO WATCH FOR**:
- MCP tools work correctly (successful search-pubmed calls)
- PHI detection working (sanitizing requests)
- Agent initialization successful
- Agent processing hits timeout/iteration limits
- Logs show: `[Medical Search Agent] Agent stopped due to iteration limit or time limit`

**ROOT CAUSE**: LangChain agent configuration has overly restrictive iteration/timeout limits for medical queries.

**DEBUGGING STEPS**:
1. **Verify MCP layer works**:
   ```python
   # This should work (MCP infrastructure)
   client = DirectMCPClient()
   result = await client.call_tool('search-pubmed', {'query': 'diabetes'})
   print(f"MCP working: {result}")
   ```

2. **Check agent timeout configuration**:
   ```python
   # Look for iteration/timeout settings
   grep -r "max_iterations" services/user/healthcare-api/
   grep -r "timeout" services/user/healthcare-api/core/langchain/
   ```

3. **Test agent directly (bypass Open WebUI)**:
   ```bash
   curl -X POST http://localhost:8000/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model":"healthcare","messages":[{"role":"user","content":"What are diabetes symptoms?"}]}'
   ```

**SOLUTION AREAS TO INVESTIGATE**:
- LangChain agent `max_iterations` settings
- Agent timeout configurations
- Open WebUI integration timeout handling
- Medical query complexity requiring more processing time

**LOG ANALYSIS PATTERN**:
```bash
# Check agent activity vs timeout
tail -f logs/agent_medical_search.log | grep -E "(initialized|stopped|timeout|iteration)"
tail -f logs/healthcare_system.log | grep -E "(mcp|agent|timeout)"
```

**CONFIGURATION FILES TO CHECK**:
- `agents/medical_search_agent/medical_search_agent.py`
- `core/langchain/agents.py`
- `core/langchain/orchestrator.py`
- Agent configuration YAML files

### MCP Async Task Management Debugging (CRITICAL)

**PROBLEM PATTERN**: MCP clients creating runaway async tasks causing CPU drain.

**SYMPTOMS TO WATCH FOR**:
- Terminal showing: `Task exception was never retrieved`
- Error pattern: `RuntimeError('Attempted to exit cancel scope in a different task')`
- `BrokenResourceError` in MCP STDIO communication
- Accumulating Task-XX entries with cancel scope violations
- High CPU usage from background async tasks

**ROOT CAUSE**: Async context managers opened but never properly closed.

### MCP STDIO Communication Debugging (2025-08-13)

**CRITICAL BREAKTHROUGH**: stdio communication between separate containers fails - MCP requires subprocess spawning.

**SYMPTOMS OF CONTAINER-TO-CONTAINER MCP ISSUES**:
- `WriteUnixTransport closed=True` in MCP logs
- `BrokenResourceError` during stdio communication
- MCP calls start but return 0 results
- `docker exec` commands work manually but fail in Python MCP client

**ROOT CAUSE**: MCP Python client expects subprocess spawning, not remote container stdio bridging.

**SOLUTION PATTERN**:
```python
# ❌ PROBLEMATIC: Container-to-container MCP communication
async def broken_mcp_client():
    # This fails because docker exec doesn't provide proper stdio streams
    process = await asyncio.create_subprocess_exec(
        "docker", "exec", "healthcare-mcp", "node", "/app/build/stdio_entry.js",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE
    )

# ✅ CORRECT: Single-container subprocess spawning
async def working_mcp_client():
    params = StdioServerParameters(
        command="node",
        args=["/app/mcp-server/build/index.js"],  # Local path in same container
        env={"MCP_TRANSPORT": "stdio"}
    )
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # Reliable stdio communication
            result = await session.call_tool(tool_name, arguments)
```

### LangChain Agent Scratchpad Debugging (2025-08-14) - CRITICAL FIX

**PROBLEM**: `variable agent_scratchpad should be a list of base messages, got str`

**SYMPTOMS**:
- Error occurs in `AgentExecutor.ainvoke()` around line 319 in agents.py
- Agent initialization succeeds but processing fails
- Error specifically mentions string instead of BaseMessages list

**ROOT CAUSE ANALYSIS**:
1. ConversationSummaryBufferMemory injects string summaries where BaseMessages expected
2. Structured chat agent expects MessagesPlaceholder("agent_scratchpad") as BaseMessages list
3. Memory conflicts with agent's internal scratchpad management

**COMPLETE FIX PATTERN**:
```python
# ❌ BROKEN: Using memory with AgentExecutor
self.executor = AgentExecutor(
    agent=agent,
    tools=self.tools,
    memory=self.memory,  # CAUSES SCRATCHPAD CONFLICT
    return_intermediate_steps=True
)

# ✅ WORKING: Switch to ReAct agent without memory
from langchain import hub
from langchain.agents import create_react_agent

# Use standard ReAct prompt from hub
prompt = hub.pull("hwchase17/react")
agent = create_react_agent(llm=self.llm, tools=self.tools, prompt=prompt)

self.executor = AgentExecutor(
    agent=agent,
    tools=self.tools,
    verbose=True,
    return_intermediate_steps=True,
    handle_parsing_errors="Check your output and make sure it conforms!"
    # NO memory parameter - prevents conflicts
)

# CRITICAL: Only pass {"input": query} to ainvoke()
result = await self.executor.ainvoke({"input": query})
```

**KEY DEBUGGING INSIGHTS**:
- Never pass `agent_scratchpad` manually - AgentExecutor manages it from intermediate_steps
- ReAct agents are more stable than structured chat in LangChain 0.3.x  
- Tools must return strings, not dicts (use json.dumps for complex data)
- Async tools need proper sync wrappers using `asyncio.iscoroutinefunction()`

**MCP Broken Pipe Investigation Pattern**:
```python
# When you see "[Errno 32] Broken pipe" in MCP calls:

# 1. Check MCP server is running and accessible
async def debug_mcp_connection():
    try:
        # Test basic connectivity first
        result = await mcp_client.list_tools()
        logger.info(f"MCP tools available: {len(result)}")
        
        # Then test specific tool
        result = await mcp_client.call_tool("search-pubmed", {"query": "test"})
        logger.info("MCP tool call successful")
        
    except Exception as e:
        logger.error(f"MCP connection issue: {e}")
        # Check: Is MCP server running? Network connectivity? Resource limits?
```

**DEBUGGING APPROACH**:
```python
# ❌ PROBLEMATIC: Context managers without proper cleanup
async def search_medical_data(query: str):
    # Opens connection but may not close properly
    async with mcp_client:
        results = await mcp_client.search(query)
        return results  # Connection may leak on exception

# ✅ CORRECT: Explicit cleanup to prevent task accumulation
async def search_medical_data(query: str):
    try:
        results = await mcp_client.search(query)
        return results
    except Exception as e:
        logger.exception(f"Search error: {e}")
        return {"error": str(e)}
    finally:
        # CRITICAL: Always cleanup MCP connections
        try:
            if hasattr(mcp_client, 'disconnect'):
                await mcp_client.disconnect()
                logger.debug("MCP client disconnected after search")
        except Exception as cleanup_error:
            logger.warning(f"Error during MCP cleanup: {cleanup_error}")
```

**DETECTION TECHNIQUE**: Monitor terminal selection for async task exceptions:
```python
# Check for runaway task patterns
get_terminal_selection()  # Look for Task-XX exception patterns
```

### Database-Backed Debugging (NEW APPROACH)

**CRITICAL CHANGE**: Use database-backed synthetic data for debugging, not hardcoded PHI.

```python
# ✅ CORRECT: Debug with database-backed synthetic data
from tests.database_test_utils import SyntheticHealthcareData
import hashlib
import traceback
import logging
from datetime import datetime
from typing import Dict, List, Any

def debug_patient_processing(patient_id: str, error: Exception):
    """Debug patient processing with synthetic data only."""
    
    # Connect to synthetic database for debugging
    synthetic_data = SyntheticHealthcareData()
    try:
        # Get synthetic patient data for debugging context
        patients = synthetic_data.get_test_patients(limit=1)
        if patients:
            synthetic_patient = patients[0]
            
            # Log anonymized debug info (no PHI)
            logger.debug(f"Debugging with synthetic patient: {synthetic_patient['patient_id']}")
            logger.debug(f"Error type: {type(error).__name__}")
            
            return {
                "synthetic_patient_id": synthetic_patient['patient_id'],
                "error_type": str(type(error)),
                "synthetic": True,
                "timestamp": datetime.now().isoformat()
            }
        else:
            logger.error("No synthetic patients available for debugging")
            return None
    finally:
        synthetic_data.cleanup()

# ✅ CORRECT: Safe data sampling for debugging
def get_debug_sample(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Get anonymized sample data for debugging."""
    return [
        {k: "[REDACTED]" if is_phi_field(k) else v for k, v in record.items()}
        for record in data[:3]  # Small sample only
    ]
```

### Medical Logic Debugging

```python
# ✅ CORRECT: Validate medical data without interpretation
def debug_soap_note_processing(soap_data: Dict[str, Any]):
    """Debug SOAP note processing with medical data validation."""

    required_sections = ["subjective", "objective", "assessment", "plan"]

    for section in required_sections:
        if section not in soap_data:
            logger.warning(f"Missing SOAP section: {section}")
        elif not soap_data[section].strip():
            logger.warning(f"Empty SOAP section: {section}")

    # Validate structure without interpreting medical content
    if "assessment" in soap_data:
        assessment = soap_data["assessment"]
        if not any(keyword in assessment.lower() for keyword in ["diagnosis", "impression", "findings"]):
            logger.info("Assessment may need clinical review for completeness")
```

### Healthcare Integration Debugging

```python
# ✅ CORRECT: Healthcare system debugging with comprehensive logging
from core.infrastructure.healthcare_logger import setup_healthcare_logging
from core.infrastructure.phi_monitor import PHIMonitor
import logging

def debug_healthcare_agent_issue(agent_name: str, error_context: Dict[str, Any]):
    """Debug healthcare agent issues with comprehensive logging integration."""
    
    # Ensure healthcare logging is initialized
    setup_healthcare_logging()
    logger = logging.getLogger(f'healthcare.debug.{agent_name}')
    
    # Log debug session start
    logger.info(f"Starting debug session for {agent_name}", extra={
        'healthcare_context': {
            'debug_session': True,
            'agent': agent_name,
            'error_context_keys': list(error_context.keys())
        }
    })
    
    # PHI safety check on debug data
    if PHIMonitor.scan_for_phi(error_context):
        PHIMonitor.log_phi_detection(
            context=f"debug_session_{agent_name}",
            data_summary="Debug context contains potential PHI - scrubbing for safety"
        )
        # Scrub PHI before debugging
        scrubbed_context = {k: "[PHI_REDACTED]" if PHIMonitor.scan_for_phi(v) else v 
                          for k, v in error_context.items()}
        logger.info(f"Debug data scrubbed for PHI safety: {agent_name}")
        return scrubbed_context
    
    return error_context

# ✅ CORRECT: Healthcare error debugging with logging integration
def debug_medical_workflow_error(workflow_step: str, error: Exception, context: Dict[str, Any]):
    """Debug medical workflow errors with healthcare compliance logging."""
    
    logger = logging.getLogger('healthcare.debug.workflow')
    
    # Log workflow error with healthcare context
    logger.log(35, f"Medical workflow error in {workflow_step}", extra={
        'healthcare_context': {
            'workflow_step': workflow_step,
            'error_type': type(error).__name__,
            'error_message': str(error)[:200],  # Truncated for safety
            'medical_workflow': True,
            'requires_clinical_review': True
        }
    })
    
    # Additional debugging based on workflow step
    if workflow_step == 'patient_intake':
        logger.info("Debugging patient intake workflow", extra={
            'healthcare_context': {
                'intake_fields_present': list(context.keys()),
                'phi_detected': PHIMonitor.scan_for_phi(context)
            }
        })
    
    return {
        'error_logged': True,
        'healthcare_compliant': True,
        'debug_context': 'available_in_logs'
    }
```

```python
# ✅ CORRECT: Debug EHR integration safely
def debug_ehr_integration(ehr_response: Dict[str, Any], transaction_id: str):
    """Debug EHR integration without exposing patient data."""

    safe_response = {
        "status_code": ehr_response.get("status_code"),
        "transaction_id": transaction_id,
        "response_size": len(str(ehr_response)),
        "has_patient_data": "patient" in ehr_response,
        "timestamp": datetime.utcnow().isoformat()
    }

    logger.debug("EHR Integration Debug", extra=safe_response)

    # Validate response structure
    if "error" in ehr_response:
        logger.error(f"EHR Error: {ehr_response['error']}")

    # Check for required fields without exposing content
    required_fields = ["patient_id", "encounter_id", "timestamp"]
    missing_fields = [f for f in required_fields if f not in ehr_response]
    if missing_fields:
        logger.warning(f"Missing EHR fields: {missing_fields}")
```

## Healthcare Debugging Implementation Patterns

**WORKFLOW CONTROL**: All debugging workflows are controlled by `copilot-instructions.md`. This file provides implementation patterns only.

### Healthcare-Safe Debugging Patterns

```python
def validate_debugging_compliance():
    """Ensure debugging practices meet healthcare standards."""

    checks = {
        "phi_protection": check_no_phi_in_logs(),
        "audit_logging": check_debug_audit_trail(),
        "data_minimization": check_minimal_data_exposure(),
        "access_controls": check_debug_access_restrictions()
    }

    failed_checks = [check for check, passed in checks.items() if not passed]
    if failed_checks:
        raise ComplianceError(f"Debugging compliance failed: {failed_checks}")
```

## Autonomous MyPy Error Resolution

### Autonomous MyPy Error Resolution

**❌ PROHIBITED: Healthcare Anti-Patterns**
- `# type: ignore` without medical safety justification  
- Removing medical variables to fix "unused" warnings
- Suppressing type checking for convenience

**✅ HEALTHCARE-COMPLIANT: MyPy Resolution Hierarchy**

```python
# 1. Optional import pattern (preferred for healthcare)
from typing import Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    import external_lib
else:
    external_lib: Optional[Any] = None
    try:
        import external_lib
    except ImportError:
        pass

# 2. Implement medical variables (don't remove them)
def process_patient_encounter(data: Dict[str, Any]) -> Dict[str, Any]:
    # ✅ IMPLEMENT medical data, don't remove it
    reason = data.get("reason", "routine care")  
    assessment = data.get("assessment", "stable")
    
    # Use in healthcare workflow
    return {
        "visit_reason": reason,
        "clinical_assessment": assessment
    }
```

### Self-Assessment for Continued Work

```python
def assess_mypy_continuation_capability() -> bool:
    """
    Self-assessment questions for autonomous MyPy fixing:
    - Are there remaining errors that follow patterns I've already solved?
    - Can I add more type annotations without changing logic?
    - Are there import/collection type issues I can systematically resolve?
    - Do I have capacity to continue with more fixes in this session?
    - Do remaining errors require human architectural input?
    
    Returns True only if confident in continued autonomous progress.
    """
    return can_continue_autonomously

# Autonomous workflow pattern with verification
def autonomous_mypy_fixing_session():
    """
    CRITICAL: Always verify completion claims with fresh MyPy scan.
    Never trust incremental cache for "0 errors" claims.
    """
    while True:
        # Work on errors
        fix_systematic_mypy_errors()
        
        # MANDATORY: Verify with fresh scan (prevents infinite loops)
        actual_errors = run_fresh_mypy_scan()
        
        if actual_errors == 0:
            break  # True completion verified
        elif can_continue_autonomously(actual_errors):
            continue  # More work possible
        else:
            create_continuation_issue(actual_errors)
            break  # Hand off remaining work
```
    """
    Healthcare-focused self-assessment for autonomous MyPy fixing.
    Returns True if agent should continue, False if architectural input needed.
    """
    remaining_patterns = analyze_remaining_errors()
    
    # ✅ Continue if patterns can be resolved with healthcare-safe methods
    can_continue = (
        has_missing_return_annotations(remaining_patterns) or
        has_untyped_variables(remaining_patterns) or  
        has_import_errors_resolvable_with_type_checking(remaining_patterns) or
        has_medical_variables_needing_implementation(remaining_patterns)
    )
    
    # ❌ Stop if requires architectural decisions
    needs_architecture = (
        has_complex_inheritance_issues(remaining_patterns) or
        requires_external_library_integration_decisions(remaining_patterns) or
        needs_medical_workflow_redesign(remaining_patterns)
    )
    
    return can_continue and not needs_architecture
    """Determine if coding agent should continue MyPy error fixing."""
    
    # Run MyPy and analyze remaining errors
    result = subprocess.run(['mypy', '.'], capture_output=True, text=True)
    errors = result.stderr.split('\n')
    
    # Categorize remaining errors
    systematic_errors = 0
    complex_errors = 0
    
    for error in errors:
        if any(pattern in error for pattern in [
            'missing return type annotation',
            'need type annotation for',
            'has no attribute',
            'import untyped',
        ]):
            systematic_errors += 1
        elif any(pattern in error for pattern in [
            'incompatible types in assignment',
            'incompatible return value type', 
            'type is not subscriptable',
        ]):
            complex_errors += 1
    
    # Decision logic
    if systematic_errors > 10:
        print(f"✅ Continue: {systematic_errors} systematic errors remain")
        return True
    elif systematic_errors > 0 and complex_errors < 5:
        print(f"✅ Continue: {systematic_errors} systematic, {complex_errors} complex")
        return True
    else:
        print(f"🛑 Stop: Only {complex_errors} complex errors remain")
        return False

# Autonomous workflow pattern
def autonomous_mypy_fixing_session():
    """Execute autonomous MyPy fixing until completion or stuck."""
    
    max_iterations = 10
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        print(f"\n🔄 MyPy Fixing Iteration {iteration}")
        
        # Get current error count
        before_count = get_mypy_error_count()
        print(f"📊 Errors before iteration: {before_count}")
        
        # Fix batch of errors
        fix_systematic_mypy_errors(batch_size=25)
        
        # Check progress
        after_count = get_mypy_error_count()
        print(f"📊 Errors after iteration: {after_count}")
        
        # Assess continuation
        if after_count == 0:
            print("🎉 All MyPy errors resolved!")
            break
        elif after_count >= before_count:
            print("⚠️ No progress made - analyzing remaining errors")
            if not assess_mypy_continuation_capability():
                print("🛑 Stopping: Remaining errors require human input")
                break
        else:
            progress = before_count - after_count
            print(f"✅ Progress: {progress} errors fixed, continuing...")
```

### Progress Tracking and Continuation

```python
def create_continuation_issue_if_needed():
    """Create GitHub issue for continuation if work remains."""
    
    remaining_errors = get_mypy_error_count()
    
    if remaining_errors > 0:
        # Check if errors are systematic or complex
        if assess_mypy_continuation_capability():
            issue_body = f"""
## Autonomous MyPy Error Fixing - Continuation Required

**Remaining Errors**: {remaining_errors}

The coding agent has made progress but stopped before completion. 
Remaining errors appear to be systematic and can be resolved autonomously.

**Next Steps**:
1. Continue systematic type annotation fixes
2. Focus on missing return types and variable annotations
3. Address import/collection type issues

@github-copilot Please continue MyPy error resolution from where previous session left off.
"""
            
            # Create issue for automatic continuation
            create_github_issue(
                title="Continue MyPy Error Resolution - Autonomous Session",
                body=issue_body,
                labels=["mypy", "autonomous", "type-safety", "continue"]
            )
```

## Common Healthcare AI Debug Scenarios

### SOAP Note Processing Issues

```python
def debug_soap_processing(soap_note: str, expected_sections: List[str]):
    """Debug SOAP note processing issues."""

    # Parse sections safely
    sections = extract_soap_sections(soap_note)

    # Validate without medical interpretation
    debug_info = {
        "total_length": len(soap_note),
        "sections_found": list(sections.keys()),
        "sections_expected": expected_sections,
        "missing_sections": [s for s in expected_sections if s not in sections],
        "empty_sections": [s for s, content in sections.items() if not content.strip()]
    }

    logger.debug("SOAP Processing Debug", extra=debug_info)
    return debug_info
```

### Agent Communication Debugging

```python
def debug_agent_communication(agent_name: str, message: Dict[str, Any]):
    """Debug inter-agent communication safely."""

    safe_message = {
        "agent": agent_name,
        "message_type": message.get("type"),
        "message_size": len(str(message)),
        "has_patient_context": "patient_id" in message,
        "timestamp": message.get("timestamp")
    }

    # Log communication patterns without exposing content
    logger.debug("Agent Communication", extra=safe_message)

    # Validate message structure
    if "type" not in message:
        logger.error(f"Agent {agent_name} sent message without type")

    if "patient_id" in message and not is_valid_patient_id(message["patient_id"]):
        logger.error(f"Agent {agent_name} sent invalid patient_id format")
```

## Error Handling Patterns

### Healthcare-Safe Exception Handling

```python
class HealthcareSafeException(Exception):
    """Exception that safely logs healthcare errors without PHI exposure."""

    def __init__(self, message: str, patient_hash: str = None, context: Dict[str, Any] = None):
        super().__init__(message)
        self.patient_hash = patient_hash
        self.context = context or {}

        # Log safely
        logger.error(
            message,
            extra={
                "patient_hash": patient_hash,
                "context": {k: v for k, v in self.context.items() if not is_phi_field(k)}
            }
        )

# Usage
try:
    process_patient_data(patient_data)
except ValidationError as e:
    raise HealthcareSafeException(
        "Patient data validation failed",
        patient_hash=hash_patient_id(patient_data["id"]),
        context={"validation_errors": e.errors}
    )
```

### Compliance-Aware Debugging Tools

```python
def safe_debug_print(data: Any, context: str = ""):
    """Print debug information with PHI protection."""

    if isinstance(data, dict):
        safe_data = {
            k: "[PHI_REDACTED]" if is_phi_field(k) else v
            for k, v in data.items()
        }
    elif isinstance(data, str) and contains_phi_patterns(data):
        safe_data = "[PHI_CONTENT_REDACTED]"
    else:
        safe_data = data

    print(f"DEBUG {context}: {safe_data}")

def debug_trace_healthcare_function(func):
    """Decorator for tracing healthcare functions safely."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Log function entry without PHI
        safe_args = [str(type(arg)) for arg in args]
        safe_kwargs = {k: type(v) for k, v in kwargs.items()}

        logger.debug(f"Entering {func.__name__}", extra={
            "args_types": safe_args,
            "kwargs_types": safe_kwargs
        })

        try:
            result = func(*args, **kwargs)
            logger.debug(f"Exiting {func.__name__} successfully")
            return result
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {type(e).__name__}")
            raise

    return wrapper
```

## Debugging Checklist

### Before Starting Debug Session

- [ ] Verify using synthetic data only
- [ ] Enable audit logging for debug session
- [ ] Set up PHI-safe logging configuration
- [ ] Prepare anonymized test cases

### During Debugging

- [ ] Check for PHI exposure in logs/console
- [ ] Validate medical logic without interpretation
- [ ] Test compliance patterns independently
- [ ] Use modern development tools (Ruff, MyPy)

### After Debugging

- [ ] Clear any temporary debug data
- [ ] Review logs for accidental PHI exposure
- [ ] Document debugging insights safely
- [ ] Update test cases based on findings

Remember: Healthcare debugging requires balancing technical insight with strict PHI protection and medical compliance standards.

## Incident Addendum (2025-08-14)

- Ensure `formatted_summary` is always populated by agents that render to UI.
- Add DIAGNOSTIC logs immediately before/after formatting to pinpoint failures.
- Wrap metrics and any telemetry in try/except so they never block formatting.
- In multi-agent runs, keep successful agent outputs even if others fail; synthesis must be non-blocking.
