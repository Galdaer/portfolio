# LangChain Agent Orchestrator Instructions

**WORKFLOW CONTROL**: All workflows are controlled by `copilot-instructions.md`. This file provides implementation patterns only.

## Agent Adapter Pattern (2025-01-15)

### Core Principle: Thin Coordination Layer

**CRITICAL**: LangChain should act as orchestrator, NOT replacement for existing agents. Think "restaurant kitchen" - LangChain is the head chef coordinating specialized chefs (existing agents).

**CONSOLIDATED**: This file consolidates all LangChain healthcare patterns. See bottom for migration from deprecated files.

### Container Architecture Understanding

**MCP ARCHITECTURE**: MCP server runs INSIDE healthcare-api container at `/app/mcp-server/build/stdio_entry.js`, communicates via STDIO JSON-RPC, NOT as separate container.

**DATABASE**: PostgreSQL in separate container, requires `psycopg2-binary` for sync operations.

**TESTING**: Environment-aware tests with `pytest.xfail()` when MCP server binary not available on host.

### LangChain Agent Configuration (Fixed)

**CRITICAL FIX**: Remove unsupported `early_stopping_method="generate"` parameter that causes ValueError.

```python
# ✅ CORRECT CONFIGURATION (2025-01-15)
from langchain import hub
from langchain.agents import create_react_agent, AgentExecutor

# Use proven ReAct prompt from hub - no custom prompt needed  
prompt = hub.pull("hwchase17/react")
agent = create_react_agent(llm=self.llm, tools=self.tools, prompt=prompt)

self.executor = AgentExecutor(
    agent=agent,
    tools=self.tools,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=15,
    max_execution_time=120,
    # ❌ REMOVED: early_stopping_method="generate"  # Causes ValueError in current LangChain
)
```

### Implementation Pattern

```python
# File: core/langchain/agent_adapters.py
from langchain.tools import tool
from typing import Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

@tool
def medical_search_adapter(query: str) -> str:
    """Route medical literature searches through specialized medical search agent."""
    try:
        # Import inside function to avoid circular imports
        from agents.medical_search_agent import MedicalLiteratureSearchAssistant
        from core.mcp.direct_mcp_client import DirectMCPClient
        import ollama
        
        # Initialize agent components
        mcp_client = DirectMCPClient()
        llm_client = ollama.AsyncClient(host='http://172.20.0.10:11434')
        
        # Get specialized agent
        agent = MedicalLiteratureSearchAssistant(mcp_client, llm_client)
        
        # Route through agent instead of direct MCP
        result = agent.search_medical_literature(query)
        
        # Log agent activity for monitoring
        logger.info(f"Medical search agent processed query: {query}")
        
        return json.dumps(result) if isinstance(result, dict) else str(result)
        
    except Exception as e:
        logger.error(f"Medical search adapter error: {e}")
        return f"Medical search temporarily unavailable: {e}"

@tool  
def clinical_research_adapter(query: str) -> str:
    """Route clinical research queries through specialized clinical research agent."""
    try:
        from agents.clinical_research_agent import ClinicalResearchAgent
        from core.mcp.direct_mcp_client import DirectMCPClient
        
        mcp_client = DirectMCPClient()
        agent = ClinicalResearchAgent(mcp_client)
        
        result = agent.research_clinical_topic(query)
        logger.info(f"Clinical research agent processed query: {query}")
        
        return json.dumps(result) if isinstance(result, dict) else str(result)
        
    except Exception as e:
        logger.error(f"Clinical research adapter error: {e}")
        return f"Clinical research temporarily unavailable: {e}"

# Additional adapters for all 8 discovered agents...
```

### Healthcare Agent Initialization 

```python
class HealthcareLangChainAgent(BaseHealthcareAgent):
    """LangChain orchestrator that coordinates existing healthcare agents."""
    
    def __init__(self, mcp_client: DirectMCPClient, model: str = "llama3.1:8b"):
        """Initialize healthcare orchestrator with agent adapters."""
        super().__init__(agent_name="langchain_orchestrator")
        
        self.mcp_client = mcp_client
        self.logger = setup_healthcare_agent_logging('langchain_orchestrator')
        
        # CRITICAL: Use healthcare-specific Ollama configuration
        self.llm = self._create_healthcare_llm(model)
        self.tools = self._create_agent_adapter_tools()  # NOT direct MCP tools
        
        # Fixed LangChain configuration
        prompt = hub.pull("hwchase17/react")
        agent = create_react_agent(llm=self.llm, tools=self.tools, prompt=prompt)
        
        self.executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=15,
            max_execution_time=120,
            # ❌ REMOVED: early_stopping_method="generate"
        )
    
    def _create_agent_adapter_tools(self):
        """Create tools that route through existing agents, not direct MCP."""
        return [
            medical_search_adapter,
            clinical_research_adapter, 
            # Add more agent adapters here...
        ]
        
    def _create_healthcare_llm(self, model: str):
        """Create Ollama LLM optimized for healthcare."""
        from langchain_community.llms import Ollama
        
        return Ollama(
            model=model,
            base_url="http://172.20.0.10:11434",
            temperature=0.1,  # Low temperature for medical accuracy
            top_p=0.9,
            timeout=30,
        )
```

---

## DEPRECATED FILES MIGRATION

**FILES TO REMOVE**: 
- `agents/langchain-healthcare.instructions.md` (redundant patterns)
- `agents/healthcare-langchain-agent.instructions.md` (outdated configurations)

**CONSOLIDATED HERE**: All LangChain healthcare patterns now in this single file with:
- Fixed early_stopping_method error
- Container architecture understanding
- Agent adapter pattern implementation
- Proper healthcare agent inheritance

**LAST UPDATED**: 2025-01-15 | Workflow control and architecture fixes

class HealthcareLangChainOrchestrator:
    """Orchestrator that coordinates existing healthcare agents through thin adapters."""
    
    def __init__(self, discovered_agents: Dict[str, Any]):
        # Create thin wrappers for each existing agent - NO CODE DUPLICATION
        self.tools = []
        for agent_name, agent_instance in discovered_agents.items():
            self.tools.append(create_agent_tool(agent_instance, agent_name))
        
        # LangChain uses these tools to coordinate workflow
        self.agent_executor = create_orchestration_chain(self.tools)

def create_agent_tool(agent, name):
    """Create LangChain tool from existing agent - preserves agent logging."""
    
    @tool(name=f"{name}_agent")
    async def agent_wrapper(request: str) -> str:
        """Route to existing agent - preserves all agent functionality."""
        try:
            # Parse LangChain's string input to agent's expected format
            if request.startswith('{'):
                parsed_request = json.loads(request)
            else:
                parsed_request = {"query": request}  # Simple fallback
            
            # Call EXISTING agent's EXISTING method - preserves agent-specific logging
            logger.info(f"Routing to {name} agent with request: {parsed_request}")
            result = await agent.process_request(parsed_request)
            
            # Return in format LangChain expects
            return json.dumps(result, default=str)
            
        except Exception as e:
            logger.error(f"Agent adapter error for {name}: {e}")
            return json.dumps({"error": f"Agent {name} failed: {str(e)}"})
    
    return agent_wrapper
```

### Integration with main.py

```python
# File: main.py (modify existing orchestrator initialization)

# Replace direct MCP tools with agent adapters
from core.langchain.agent_adapters import HealthcareLangChainOrchestrator

# After agent discovery (keep existing agent loading):
discovered_agents = {...}  # Existing agent discovery code

# Initialize orchestrator with agent adapters instead of MCP tools
if orchestrator_type == "langchain":
    orchestrator = HealthcareLangChainOrchestrator(discovered_agents)
    logger.info("LangChain orchestrator initialized with agent adapters")
```

### Expected Behavior After Implementation

1. **Agent Logging Restored**: Medical queries should log to `agent_medical_search.log`
2. **Agent-Specific Processing**: Each agent maintains its specialized logic
3. **Multi-Agent Coordination**: LangChain can coordinate multiple agents for complex requests
4. **PHI Compliance**: All agent-specific PHI handling is preserved

### Common Mistakes to Avoid

- ❌ **Don't rewrite existing agents** - use thin adapters only
- ❌ **Don't bypass agent logging** - ensure all agent functionality is preserved
- ❌ **Don't duplicate agent logic** - adapters should be translation layers only
- ❌ **Don't break PHI compliance** - existing agent PHI handling must be maintained

### Testing Pattern

```python
# Test that agents are properly routed
async def test_agent_routing():
    # Medical query should route to medical_search_agent
    query = "What are the symptoms of diabetes?"
    result = await orchestrator.process(query)
    
    # Verify agent-specific logging occurred
    with open('logs/agent_medical_search.log', 'r') as f:
        logs = f.read()
        assert "diabetes" in logs  # Agent processed the query
    
    # Verify result contains agent-specific features
    assert "medical" in result.lower()
    assert "disclaimer" in result.lower()  # Agent-specific disclaimers
```

### Debugging Agent Adapters

**Symptoms of Incorrect Implementation**:
- Medical queries work but no agent-specific logs
- Missing agent disclaimers or specialized processing
- Error logs about MCP tools being called directly

**Diagnostic Commands**:
```bash
# Check if agents are being used
tail -f logs/agent_medical_search.log

# Verify LangChain tool registration (from within healthcare-api container)
cd services/user/healthcare-api
python3 -c "
try:
    from core.langchain.orchestrator import orchestrator
    print('Tools:', [tool.name for tool in orchestrator.agent_executor.tools])
except Exception as e:
    print('Orchestrator check failed:', e)
"

# Test medical query routing
curl -X POST http://localhost:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"healthcare","messages":[{"role":"user","content":"diabetes symptoms"}]}'
```

### Benefits of This Pattern

1. **Preserves Existing Investment**: All existing agent code continues to work
2. **Enables Coordination**: LangChain can use multiple agents for complex workflows
3. **Maintains Logging**: Agent-specific logging and monitoring is preserved
4. **Future Flexibility**: Can change orchestration without touching agent logic
5. **Testing Simplicity**: Each agent can still be tested independently

## Agent Coordination Patterns

### Simple Routing
- Medical queries → medical_search_agent
- Intake forms → intake_agent
- Document processing → document_processor_agent

### Multi-Agent Workflows
```python
# Complex request: "I need to refill my prescription and schedule a follow-up"
# LangChain coordinates:
# 1. intake_agent for prescription refill
# 2. scheduling_optimizer_agent for appointment
# 3. Combines responses into coherent workflow
```

### Error Handling in Adapters
```python
# Graceful degradation when agents fail
try:
    result = await agent.process_request(parsed_request)
except Exception as e:
    # Log error but don't crash orchestration
    logger.error(f"Agent {name} failed: {e}")
    return json.dumps({
        "error": f"Agent temporarily unavailable",
        "fallback": "Please try again or contact support"
    })
```
