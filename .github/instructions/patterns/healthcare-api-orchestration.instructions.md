# Healthcare API Orchestration Patterns (Updated 2025-08-14)

## Strategic Purpose

Move orchestration to a LangChain-powered router in healthcare-api, with MCP tools wrapped as LangChain tools, local-only LLMs (Ollama), and HIPAA-safe provenance in every response.

## Current Architecture (Validated)

- Orchestrator: LangChain AgentExecutor and routing chains
- Tools: MCP tools exposed via StructuredTool wrappers
- LLM: Local Ollama models only (no cloud)
- Provenance: Always show agent headers in human responses
- Config: Externalized in `services/user/healthcare-api/config/orchestrator.yml`

## Key Patterns

1) Single-container MCP, subprocess spawn
- Use Python MCP client to spawn Node MCP server as a subprocess within the healthcare-api container.
- Wrap MCP client calls in LangChain `StructuredTool` with error handling and timeouts.

2) LangChain orchestration
- Use `AgentExecutor` with a conservative `max_iterations` and timeouts from `orchestrator.yml`.
- Prefer a single selected agent; optional parallel fan-out behind a config flag.

3) Provenance and synthesis
- Always include an agent header: "🤖 <Agent> Agent Response:" in human output.
- Prefer content keys in this order: formatted_summary, formatted_response, response, research_summary, message.

4) Fallback agent
- Provide a base fallback response when no specialized agent fits or errors occur.
- Keep fallback template in `orchestrator.yml`.

## Do/Don't (Routing Contract)

- Do select exactly one primary agent for each request using the local LLM router
- Do respect `timeouts.per_agent_default` and `timeouts.per_agent_hard_cap`
- Do include provenance headers in human responses when `provenance.show_agent_header=true`
- Do return a base fallback when the selected agent errors or returns unsuccessful
- Do prefer `formatted_summary` > `formatted_response` > `response` > `research_summary` > `message`
- Don't run medical_search by default for every request (no implicit helpers)
- Don't block user responses on metrics or logging
- Don't synthesize or re-route in the pipeline; orchestration lives in healthcare-api

## Config Map (services/user/healthcare-api/config/orchestrator.yml)

- selection:
    - enabled: bool - enable LLM-based routing
    - enable_fallback: bool - use base fallback on failure
    - allow_parallel_helpers: bool - disabled by default; optional fan-out later
- timeouts:
    - router_selection: int seconds for agent selection
    - per_agent_default: int seconds soft timeout
    - per_agent_hard_cap: int seconds hard cap
- provenance:
    - show_agent_header: bool - include agent header in human format
    - include_metadata: bool - append request_id/source links when available
- synthesis:
    - prefer: list[str] - field precedence when converting to human text
    - agent_priority: list[str] - tie-break preference order
    - header_prefix: str - UI header prefix
- fallback:
    - agent_name: str - logical name of fallback agent
    - message_template: str - safe, non-medical template with {user_message}

## Acceptance Checklist

- Router picks a single agent; no always-on medical_search
- Human responses show agent provenance header
- Base fallback returns safe message with disclaimers
- Timeouts are honored from orchestrator.yml
- JSON responses unchanged; human responses prefer formatted fields

## Compliance Requirements

- Local-only LLMs via Ollama; no cloud calls.
- PHI protection in memory/logs; redact before logging.
- Medical disclaimers included in responses from research agents.

## Files of Interest

- `services/user/healthcare-api/config/orchestrator.yml` (timeouts, provenance, routing)
- `services/user/healthcare-api/main.py` (router endpoint integration)
- `services/user/healthcare-api/core/langchain/` (agents, tools, orchestrator)

## Migration Notes

- Thin MCP pipeline is legacy; new work centers on API-level orchestration.
- Agents can remain as is; introduce LangChain wrappers incrementally per agent.

**Architecture Role**: Receives requests from thin MCP pipeline and orchestrates complete healthcare AI workflows.

## Healthcare API Architecture Patterns

### Agent Orchestration Hub

```python
# ✅ PATTERN: Healthcare API as central orchestration hub
class HealthcareOrchestrator:
    def __init__(self):
        self.agents = {
            'intake': IntakeAgent(),
            'document_processor': DocumentProcessorAgent(),
            'clinical_research_agent': ClinicalResearchAgent()
        }
        self.mcp_client = HealthcareMCPClient()
    
    async def route_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Route request to appropriate agent based on content analysis"""
        # Analyze request and select appropriate agent
        pass
    
    async def coordinate_agents(self, primary_agent: str, request: Dict[str, Any]) -> Any:
        """Coordinate multiple agents for complex workflows"""
```

### Single-Container MCP Integration (2025-08-13)

**PROVEN ARCHITECTURE**: Healthcare-API container includes both FastAPI application and MCP server for reliable stdio communication.

**Implementation Pattern**:
```python
# ✅ PATTERN: Combined container MCP integration
class HealthcareAPIWithMCP:
    def __init__(self):
        # MCP server runs as subprocess within same container
        self.mcp_client = HealthcareMCPClient()
        
    async def process_agent_request(self, request_type: str, data: dict):
        # 1. Select appropriate agent
        agent = self.select_agent(request_type)
        
        # 2. Agent calls MCP tools via subprocess
        agent_result = await agent.process(data, mcp_client=self.mcp_client)
        
        # 3. Return processed result
        return agent_result
```

**Service Configuration (.conf Pattern)**:
```bash
# healthcare-api.conf - Single container with MCP
image=intelluxe/healthcare-api:latest
env=MCP_SERVER_INCLUDED=true,MCP_SERVER_PATH=/app/mcp-server/build/index.js
# No separate MCP container needed
```
        # Multi-agent coordination with MCP tool integration
        pass
```

### Agent-MCP Integration

```python
# ✅ PATTERN: Agent-driven MCP tool selection (builds on api-development.instructions.md)
class AgentMCPCoordination:
    async def agent_select_mcp_tools(self, agent_type: str, context: Dict[str, Any]) -> List[str]:
        """Let agents decide which MCP tools to use based on context"""
        # Agent-specific tool selection logic
        pass
    
    async def coordinate_agent_mcp_workflow(self, primary_agent: str, mcp_tools: List[str]) -> Any:
        """Coordinate agent workflow with selected MCP tools"""
        # Multi-step agent + MCP coordination
        pass
```

## Agent Coordination Patterns (Focus on Orchestration Hub Role)

### Agent Selection Logic

```python
# ✅ PATTERN: Intelligent agent selection based on request analysis
class AgentSelector:
    def analyze_request_intent(self, user_message: str) -> str:
        """Analyze user message to determine appropriate agent"""
        # Intent classification for agent selection
        pass
    
    def select_primary_agent(self, intent: str, context: Dict[str, Any]) -> str:
        """Select primary agent based on intent and context"""
        # Agent selection logic
        pass
```

## Database Integration Patterns

### Healthcare Data Access

```python
# ✅ PATTERN: Database-first healthcare data access
class HealthcareDataManager:
    async def get_patient_context(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get patient context from database with PHI protection"""
        # Database-first with synthetic fallbacks
        pass
    
    async def store_interaction(self, interaction_data: Dict[str, Any]) -> str:
        """Store healthcare interaction with audit logging"""
        # HIPAA-compliant interaction storage
        pass
```

### Session Management

```python
# ✅ PATTERN: Healthcare session management with Redis
class HealthcareSessionManager:
    async def create_session(self, user_id: str, role: str) -> str:
        """Create healthcare session with RBAC validation"""
        # Session creation with healthcare RBAC
        pass
    
    async def maintain_context(self, session_id: str, context: Dict[str, Any]) -> None:
        """Maintain conversation context across interactions"""
        # Context preservation with PHI protection
        pass
```

## Agent Workflow Orchestration (Non-Duplicative Focus)

### Multi-Agent Coordination

```python
# ✅ PATTERN: Multi-agent workflow coordination
class MultiAgentCoordinator:
    async def coordinate_sequential_agents(self, workflow: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """Run agents in sequence with context passing"""
        # Sequential agent execution with context preservation
        pass
    
    async def coordinate_parallel_agents(self, agents: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """Run agents in parallel and merge results"""
        # Parallel agent execution with result merging
        pass
```
