# MCP Integration Patterns for Healthcare AI

**WORKFLOW CONTROL**: All workflows are controlled by `copilot-instructions.md`. This file provides implementation patterns only.

## Container-Based MCP Architecture (2025-01-15)

### Architectural Understanding

**CRITICAL**: MCP server runs INSIDE healthcare-api container, not as separate service.

```
Healthcare API Container Architecture:
├── FastAPI Application (Python)
├── DirectMCP Client (Python) 
└── MCP Server (/app/mcp-server/build/stdio_entry.js) ← JSON-RPC via stdio
```

### Environment-Aware MCP Client Pattern

```python
from pathlib import Path
from typing import Optional
import os

class DirectMCPClient:
    """MCP client with container/host environment awareness."""
    
    def _detect_mcp_server_path(self) -> Optional[str]:
        """Detect MCP server path for container vs host environment."""
        
        # Container environment paths (production)
        container_paths = [
            "/app/mcp-server/build/stdio_entry.js",
            "/app/build/index.js",
            "/app/mcp-server/build/index.js"
        ]
        
        # Host environment paths (development)
        host_paths = [
            "/home/intelluxe/services/user/healthcare-mcp/build/index.js",
            "/home/intelluxe/mcp-server/build/index.js"
        ]
        
        # Try container paths first (most common in production)
        for path in container_paths + host_paths:
            if Path(path).exists():
                return path
        
        return None
    
    def _is_container_environment(self) -> bool:
        """Detect if running in container environment."""
        return (
            os.path.exists("/.dockerenv") or 
            os.environ.get("DOCKER_CONTAINER") == "true" or
            Path("/app").exists()
        )
    
    async def initialize(self):
        """Initialize MCP client with clear error handling."""
        mcp_server_path = self._detect_mcp_server_path()
        
        if not mcp_server_path:
            if self._is_container_environment():
                raise FileNotFoundError(
                    "MCP server not found in container at expected paths: "
                    "/app/mcp-server/build/stdio_entry.js"
                )
            else:
                raise FileNotFoundError(
                    "MCP server not found on host. Please run 'make setup' to build MCP server "
                    "or check if healthcare-mcp service is running."
                )
        
        self.mcp_server_path = mcp_server_path
        self.logger.info(f"MCP server detected at: {mcp_server_path}")
```

### Broken Pipe Error Resolution Pattern

```python
import asyncio
import json
import select
from typing import Dict, Any

class MCPConnectionManager:
    """Manages MCP subprocess lifecycle to prevent broken pipes."""
    
    def __init__(self, server_path: str):
        self.server_path = server_path
        self.process: Optional[asyncio.subprocess.Process] = None
        self._connection_lock = asyncio.Lock()
    
    async def ensure_connection(self):
        """Ensure MCP server process is running and responsive."""
        async with self._connection_lock:
            if self.process is None or self.process.poll() is not None:
                await self._start_process()
    
    async def _start_process(self):
        """Start MCP server subprocess with proper stdio handling."""
        try:
            self.process = await asyncio.create_subprocess_exec(
                "node", self.server_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={
                    "MCP_TRANSPORT": "stdio",
                    "NODE_ENV": "production"
                }
            )
            
            # Test initial connection
            await self._send_initialize_request()
            
        except Exception as e:
            raise ConnectionError(f"Failed to start MCP server: {e}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call MCP tool with connection management."""
        await self.ensure_connection()
        
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        try:
            # Send request with null safety
            if self.process and self.process.stdin:
                request_data = json.dumps(request).encode() + b"\n"
                self.process.stdin.write(request_data)
                await self.process.stdin.drain()
            else:
                raise ConnectionError("MCP process stdin not available")
            
            # Read response with timeout
            if self.process and self.process.stdout:
                ready, _, _ = select.select([self.process.stdout], [], [], 10.0)
                if ready:
                    response_data = await self.process.stdout.readline()
                    response = json.loads(response_data.decode())
                    return response
                else:
                    raise TimeoutError("MCP tool call timed out")
            else:
                raise ConnectionError("MCP process stdout not available")
                
        except (json.JSONDecodeError, ConnectionError, TimeoutError) as e:
            # Reset connection on error
            await self._reset_connection()
            raise e
    
    async def _reset_connection(self):
        """Reset MCP connection after error."""
        if self.process:
            self.process.terminate()
            await self.process.wait()
            self.process = None
```

### Agent Iteration Limit Resolution Pattern

```python
from langchain.agents import AgentExecutor
from langchain_ollama import ChatOllama

class HealthcareLangChainAgent:
    """Healthcare agent with appropriate iteration limits for medical queries."""
    
    def __init__(self, mcp_client, model_name: str = "llama3.1:8b"):
        self.mcp_client = mcp_client
        
        # Configure LLM with healthcare-appropriate timeouts
        self.llm = ChatOllama(
            model=model_name,
            base_url="http://172.20.0.10:11434",
            temperature=0.7,
            timeout=60  # Longer timeout for medical queries
        )
        
        # Create tools from MCP client
        self.tools = self._create_mcp_tools()
        
        # Configure agent with medical query limits
        self.executor = AgentExecutor(
            agent=self._create_agent(),
            tools=self.tools,
            verbose=True,
            max_iterations=10,  # Increased for medical complexity
            max_execution_time=120,  # 2 minutes for medical searches
            return_intermediate_steps=True,
            handle_parsing_errors=True
        )
    
    def _create_agent(self):
        """Create agent optimized for medical queries."""
        # Use ReAct agent (more stable than structured chat)
        from langchain.agents import create_react_agent
        from langchain import hub
        
        # Medical-optimized prompt
        prompt = hub.pull("hwchase17/react")
        return create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
    
    async def process(self, query: str) -> Dict[str, Any]:
        """Process medical query with appropriate iteration limits."""
        try:
            # Execute with only input parameter
            result = await self.executor.ainvoke({"input": query})
            
            return {
                "success": True,
                "output": result.get("output", ""),
                "intermediate_steps": result.get("intermediate_steps", [])
            }
            
        except Exception as e:
            if "iteration limit" in str(e) or "time limit" in str(e):
                return {
                    "success": False,
                    "error": "Medical query exceeded processing limits",
                    "suggestion": "Try breaking down the query into smaller parts"
                }
            else:
                return {
                    "success": False,
                    "error": str(e)
                }
```

### Open WebUI Integration Pattern

```python
class OpenWebUIMedicalRouting:
    """Handles medical query routing for Open WebUI integration."""
    
    def __init__(self, healthcare_agent):
        self.healthcare_agent = healthcare_agent
        self.medical_keywords = [
            "symptoms", "treatment", "medication", "diagnosis", 
            "disease", "condition", "therapy", "clinical", 
            "medical", "health", "patient", "doctor"
        ]
    
    def is_medical_query(self, query: str) -> bool:
        """Determine if query should be routed to medical agent."""
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in self.medical_keywords)
    
    async def route_query(self, query: str) -> Dict[str, Any]:
        """Route query to appropriate agent based on content."""
        if self.is_medical_query(query):
            # Route to healthcare agent with medical processing
            result = await self.healthcare_agent.process(query)
            
            # Add medical disclaimers
            if result.get("success"):
                result["medical_disclaimer"] = (
                    "This information is for educational purposes only. "
                    "Consult healthcare professionals for medical advice."
                )
            
            return result
        else:
            # Route to general agent
            return await self._process_general_query(query)
    
    async def _process_general_query(self, query: str) -> Dict[str, Any]:
        """Process non-medical queries."""
        return {
            "success": True,
            "output": "This is a general response. For medical queries, please be more specific.",
            "agent_type": "general"
        }
```

### Testing Patterns for MCP Integration

```python
@pytest.mark.asyncio
async def test_mcp_container_integration():
    """Test MCP integration with container architecture awareness."""
    client = DirectMCPClient()
    
    # Test environment detection
    detected_path = client._detect_mcp_server_path()
    
    if detected_path:
        # Container/dev environment - test actual integration
        tools = await client.get_available_tools()
        assert len(tools) > 0
        
        # Test tool call
        result = await client.call_tool("search-pubmed", {"query": "diabetes"})
        assert "results" in result or "error" in result
    else:
        # Host environment - test graceful degradation
        with pytest.raises(FileNotFoundError, match="MCP server not found"):
            await client.call_tool("search-pubmed", {"query": "test"})

@pytest.mark.asyncio
async def test_agent_iteration_limits():
    """Test that medical agents can handle complex queries."""
    
    # Mock MCP client for testing
    mock_mcp = MockMCPClient()
    agent = HealthcareLangChainAgent(mock_mcp)
    
    # Test complex medical query that might hit limits
    complex_query = (
        "What are the latest treatment options for type 2 diabetes, "
        "including medication interactions and contraindications?"
    )
    
    result = await agent.process(complex_query)
    
    # Should not hit iteration limits with proper configuration
    assert result["success"] == True
    assert "iteration limit" not in result.get("error", "")
```

### Configuration Patterns

```yaml
# config/medical_search_config.yaml
agent_settings:
  max_iterations: 10  # Increased for medical complexity
  max_execution_time: 120  # 2 minutes for thorough medical searches
  timeout_per_tool: 30  # Per-tool timeout
  
mcp_settings:
  connection_timeout: 10
  request_timeout: 30
  max_retries: 3
  
medical_routing:
  keywords:
    - symptoms
    - treatment  
    - medication
    - diagnosis
    - disease
    - condition
    - therapy
    - clinical
  
  disclaimers:
    medical_advice: "This information is for educational purposes only."
    consult_professional: "Consult healthcare professionals for medical advice."
```

### Error Handling Patterns

```python
class MCPHealthcareError(Exception):
    """Healthcare-specific MCP error with safe logging."""
    pass

class MCPConnectionError(MCPHealthcareError):
    """MCP connection-related errors."""
    pass

class MCPTimeoutError(MCPHealthcareError):
    """MCP timeout-related errors."""
    pass

def handle_mcp_error(error: Exception, context: str) -> Dict[str, Any]:
    """Handle MCP errors with healthcare-safe logging."""
    
    if isinstance(error, FileNotFoundError):
        return {
            "error": "MCP service unavailable",
            "suggestion": "Please contact system administrator",
            "technical_context": context
        }
    elif "broken pipe" in str(error).lower():
        return {
            "error": "Connection issue with medical database",
            "suggestion": "Please try your query again",
            "technical_context": "MCP connection reset"
        }
    elif "iteration limit" in str(error).lower():
        return {
            "error": "Query too complex for current processing limits",
            "suggestion": "Try breaking down your medical question into smaller parts",
            "technical_context": "Agent iteration limit reached"
        }
    else:
        return {
            "error": "Unexpected issue processing medical query",
            "suggestion": "Please try again or contact support",
            "technical_context": str(error)[:100]  # Truncated for safety
        }
```

### Performance Optimization Patterns

```python
class MCPConnectionPool:
    """Connection pooling for MCP to reduce subprocess overhead."""
    
    def __init__(self, max_connections: int = 5):
        self.max_connections = max_connections
        self.active_connections: List[MCPConnectionManager] = []
        self.available_connections: List[MCPConnectionManager] = []
        self._lock = asyncio.Lock()
    
    async def get_connection(self) -> MCPConnectionManager:
        """Get available MCP connection from pool."""
        async with self._lock:
            if self.available_connections:
                return self.available_connections.pop()
            elif len(self.active_connections) < self.max_connections:
                conn = MCPConnectionManager(self.mcp_server_path)
                await conn.ensure_connection()
                self.active_connections.append(conn)
                return conn
            else:
                # Wait for connection to become available
                await asyncio.sleep(0.1)
                return await self.get_connection()
    
    async def return_connection(self, connection: MCPConnectionManager):
        """Return connection to pool."""
        async with self._lock:
            if connection in self.active_connections:
                self.available_connections.append(connection)
```

This MCP integration pattern file captures all the key learnings from our session about container architecture, broken pipe resolution, agent iteration limits, and Open WebUI integration patterns.
