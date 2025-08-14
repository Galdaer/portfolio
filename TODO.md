# LangChain Integration TODO - Healthcare AI System
**Date:** 2025-08-14
**Context:** Migrating from custom orchestration to LangChain for robust agent coordination, tool integration, and response synthesis
**Repository:** intelluxe-core (branch: main → create feature/langchain-integration)

## 🎯 INTEGRATION OBJECTIVES & SCOPE

### Primary Goals:
- Replace custom orchestration in `main.py` with LangChain's AgentExecutor
- Wrap existing MCP tools as LangChain tools with proper error handling
- Implement shared memory between agents for context preservation
- Ensure medical_search agent results are always surfaced (solving current synthesis issue)
- Maintain all PHI protection and healthcare compliance requirements

### Success Criteria:
- ✅ Agents coordinate properly without custom routing logic
- ✅ MCP tools work reliably through LangChain's tool abstraction
- ✅ Response synthesis handles partial failures gracefully
- ✅ Agent provenance is clear in all responses
- ✅ Configuration remains externalized in YAML files

## 📦 PHASE 1: Environment Setup & Dependencies

### 1.1 Install LangChain Components
```bash
# Add to requirements.in
langchain>=0.3.0
langchain-community>=0.3.0
langchain-core>=0.3.0
langchain-ollama>=0.2.0  # For local LLM integration

# Regenerate and install
python3 scripts/generate-requirements.py
make deps
```

### 1.2 Verify Ollama Integration
```python
# Create test file: tests/test_langchain_ollama.py
from langchain_ollama import OllamaLLM

def test_ollama_connection():
    llm = OllamaLLM(
        model="llama3.1:8b",
        base_url="http://ollama:11434",  # From your docker network
        temperature=0.1
    )
    response = llm.invoke("Test connection")
    assert response is not None
```

## 📋 PHASE 2: Tool Wrapping & Integration

### 2.1 Create LangChain Tool Wrappers
**File:** `services/user/healthcare-api/core/langchain/tools.py`

```python
from langchain.tools import StructuredTool
from langchain.pydantic_v1 import BaseModel, Field
from typing import Optional, List
from core.mcp.healthcare_mcp_client import HealthcareMCPClient

class PubMedSearchInput(BaseModel):
    """Input for PubMed search"""
    query: str = Field(description="Medical search query")
    max_results: int = Field(default=10, description="Maximum results")

class ClinicalTrialsInput(BaseModel):
    """Input for clinical trials search"""
    condition: str = Field(description="Medical condition")
    status: Optional[str] = Field(default="recruiting", description="Trial status")

class DrugInfoInput(BaseModel):
    """Input for FDA drug information"""
    drug_name: str = Field(description="Drug name to lookup")

def create_mcp_tools(mcp_client: HealthcareMCPClient) -> List[StructuredTool]:
    """Wrap MCP tools as LangChain tools with proper error handling"""
    
    tools = [
        StructuredTool.from_function(
            func=mcp_client.search_pubmed,
            name="search_medical_literature",
            description="Search PubMed for peer-reviewed medical literature",
            args_schema=PubMedSearchInput,
            return_direct=False,
            handle_tool_error=True
        ),
        StructuredTool.from_function(
            func=mcp_client.search_clinical_trials,
            name="search_clinical_trials",
            description="Search for active clinical trials",
            args_schema=ClinicalTrialsInput,
            return_direct=False,
            handle_tool_error=True
        ),
        StructuredTool.from_function(
            func=mcp_client.get_drug_info,
            name="get_drug_information",
            description="Get FDA drug information and warnings",
            args_schema=DrugInfoInput,
            return_direct=False,
            handle_tool_error=True
        ),
    ]
    
    return tools
```

### 2.2 Add Tool Error Recovery
```python
# Add custom error handling wrapper
def safe_tool_wrapper(tool_func):
    """Wrap tool functions with healthcare-safe error handling"""
    async def wrapper(*args, **kwargs):
        try:
            result = await tool_func(*args, **kwargs)
            return result
        except Exception as e:
            # Log with PHI-safe context
            logger.error(f"Tool error: {tool_func.__name__}", exc_info=False)
            return {
                "error": "Tool temporarily unavailable",
                "fallback": "Using cached medical data",
                "status": "degraded"
            }
    return wrapper
```

## 🤖 PHASE 3: Agent Migration

### 3.1 Create LangChain Agent Wrapper
**File:** `services/user/healthcare-api/core/langchain/agents.py`

```python
from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain.memory import ConversationSummaryBufferMemory
from langchain_ollama import OllamaLLM
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import Dict, Any, Optional
import yaml

class HealthcareLangChainAgent:
    """LangChain-powered healthcare agent with configurable behavior"""
    
    def __init__(self, config_path: str = "config/orchestrator.yml"):
        self.config = self.load_config(config_path)
        self.setup_llm()
        self.setup_memory()
        self.setup_tools()
        self.setup_agent()
        
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load orchestrator configuration"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def setup_llm(self):
        """Initialize local Ollama LLM"""
        self.llm = OllamaLLM(
            model=self.config.get('model', 'llama3.1:8b'),
            base_url=self.config.get('ollama_url', 'http://ollama:11434'),
            temperature=self.config.get('temperature', 0.1),
            timeout=self.config['timeouts']['per_agent_default']
        )
    
    def setup_memory(self):
        """Setup conversation memory with healthcare context"""
        self.memory = ConversationSummaryBufferMemory(
            llm=self.llm,
            max_token_limit=2000,
            return_messages=True,
            memory_key="chat_history"
        )
    
    def setup_tools(self):
        """Initialize and wrap tools"""
        from core.mcp.healthcare_mcp_client import HealthcareMCPClient
        mcp_client = HealthcareMCPClient()
        self.tools = create_mcp_tools(mcp_client)
    
    def setup_agent(self):
        """Create the agent with healthcare-specific prompt"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a healthcare AI assistant focused on providing 
            evidence-based medical information from authoritative sources.
            
            CRITICAL RULES:
            - Always cite sources with links when providing medical information
            - Never provide direct medical advice or diagnosis
            - Use available tools to search medical literature
            - Maintain patient privacy - never store or transmit PHI
            
            When responding:
            1. Search relevant medical literature using tools
            2. Synthesize findings with clear citations
            3. Include appropriate medical disclaimers
            4. Format response for clarity with headers and bullet points
            """),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        agent = create_structured_chat_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        self.executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,  # For debugging
            max_iterations=3,
            max_execution_time=self.config['timeouts']['per_agent_hard_cap'],
            early_stopping_method="generate",
            handle_parsing_errors=True,
            return_intermediate_steps=True  # For provenance
        )
    
    async def process(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Process query with automatic tool selection and error recovery"""
        try:
            result = await self.executor.ainvoke({
                "input": query,
                "context": context or {}
            })
            
            # Add provenance header
            if self.config['provenance']['show_agent_header']:
                agent_name = self.identify_active_agent(result)
                result['formatted_summary'] = f"🤖 {agent_name} Agent Response:\n\n{result.get('output', '')}"
            
            return {
                "success": True,
                "formatted_summary": result.get('formatted_summary', result.get('output', '')),
                "intermediate_steps": result.get('intermediate_steps', []),
                "agent_name": agent_name
            }
            
        except Exception as e:
            logger.error(f"Agent execution error: {str(e)}", exc_info=False)
            return self.get_fallback_response(query)
    
    def get_fallback_response(self, query: str) -> Dict[str, Any]:
        """Provide fallback response when agent fails"""
        return {
            "success": False,
            "formatted_summary": self.config['fallback']['message_template'].format(
                query=query[:100]
            ),
            "agent_name": "Fallback"
        }
```

### 3.2 Migrate Existing Agents
**Convert each existing agent to use LangChain patterns:**

```python
# Example: Migrate medical_search_agent
from langchain.agents import Tool
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

class MedicalSearchLangChainAgent:
    """Medical search agent using LangChain"""
    
    def __init__(self, base_agent: HealthcareLangChainAgent):
        self.base = base_agent
        self.add_specialized_tools()
    
    def add_specialized_tools(self):
        """Add medical-search-specific tools"""
        literature_tool = Tool(
            name="analyze_literature_quality",
            func=self.assess_evidence_quality,
            description="Assess quality of medical literature"
        )
        self.base.tools.append(literature_tool)
    
    async def assess_evidence_quality(self, articles: List[Dict]) -> Dict:
        """Evaluate evidence quality using local LLM"""
        prompt = PromptTemplate(
            input_variables=["articles"],
            template="""Assess the evidence quality of these medical articles:
            {articles}
            
            Provide quality scores for:
            - Study design strength
            - Sample size adequacy  
            - Recency and relevance
            - Source authority
            """
        )
        chain = LLMChain(llm=self.base.llm, prompt=prompt)
        return await chain.arun(articles=articles)
```

## 🔧 PHASE 4: Router Integration

### 4.1 Update main.py Router
**File:** `services/user/healthcare-api/main.py`

```python
from core.langchain.agents import HealthcareLangChainAgent
from core.langchain.orchestrator import LangChainOrchestrator

# Initialize orchestrator
orchestrator = LangChainOrchestrator(config_path="config/orchestrator.yml")

@app.post("/complete")
async def process_message(request: Dict[str, Any]):
    """Process message using LangChain orchestration"""
    try:
        # LangChain handles all routing and orchestration
        result = await orchestrator.process(
            query=request.get("messages", [])[-1].get("content", ""),
            session_id=request.get("session_id"),
            user_context=request.get("user", {})
        )
        
        # Format for Open WebUI
        if "application/json" in request.headers.get("accept", ""):
            return result
        else:
            # Human-readable format with provenance
            return result.get("formatted_summary", "No response generated")
            
    except Exception as e:
        logger.error(f"Orchestration error: {str(e)}", exc_info=False)
        return orchestrator.get_fallback_response()
```

### 4.2 Create LangChain Orchestrator
**File:** `services/user/healthcare-api/core/langchain/orchestrator.py`

```python
from langchain.agents import AgentExecutor
from typing import Dict, List, Any
import asyncio

class LangChainOrchestrator:
    """Multi-agent orchestrator using LangChain"""
    
    def __init__(self, config_path: str):
        self.config = self.load_config(config_path)
        self.agents = self.initialize_agents()
        self.setup_routing_chain()
    
    def initialize_agents(self) -> Dict[str, AgentExecutor]:
        """Initialize all specialized agents"""
        agents = {}
        
        # Base medical search agent
        agents['medical_search'] = MedicalSearchLangChainAgent()
        
        # Other specialized agents
        agents['clinical_research'] = ClinicalResearchLangChainAgent()
        agents['differential_diagnosis'] = DifferentialDiagnosisAgent()
        
        # Fallback agent
        agents['fallback'] = FallbackAgent()
        
        return agents
    
    def setup_routing_chain(self):
        """Create routing logic using LangChain"""
        from langchain.chains.router import MultiPromptChain
        from langchain.chains.router.llm_router import LLMRouterChain
        
        # Define routing destinations
        destinations = [
            {
                "name": "medical_search",
                "description": "For searching medical literature and research papers"
            },
            {
                "name": "clinical_research", 
                "description": "For complex clinical research questions"
            },
            {
                "name": "differential_diagnosis",
                "description": "For diagnostic reasoning and symptom analysis"
            }
        ]
        
        # Create router
        router_chain = LLMRouterChain.from_llm(
            llm=self.base_llm,
            destinations=destinations,
            default_chain="medical_search"  # Always have medical search as fallback
        )
        
        self.chain = MultiPromptChain(
            router_chain=router_chain,
            destination_chains={name: agent.executor for name, agent in self.agents.items()},
            default_chain=self.agents['medical_search'].executor
        )
    
    async def process(self, query: str, **kwargs) -> Dict[str, Any]:
        """Process query with multi-agent orchestration"""
        
        if self.config['selection']['allow_parallel_helpers']:
            # Run multiple agents in parallel
            results = await self.run_parallel_agents(query, **kwargs)
            return self.synthesize_results(results)
        else:
            # Single agent selection (current behavior)
            result = await self.chain.arun(input=query)
            return self.format_result(result)
    
    async def run_parallel_agents(self, query: str, **kwargs) -> List[Dict]:
        """Run multiple agents in parallel for comprehensive response"""
        tasks = []
        
        # Always include medical_search
        tasks.append(self.agents['medical_search'].process(query, **kwargs))
        
        # Add other relevant agents based on query
        if "diagnosis" in query.lower():
            tasks.append(self.agents['differential_diagnosis'].process(query, **kwargs))
        
        if "research" in query.lower() or "study" in query.lower():
            tasks.append(self.agents['clinical_research'].process(query, **kwargs))
        
        # Run with timeout
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful results
        return [r for r in results if not isinstance(r, Exception) and r.get('success')]
    
    def synthesize_results(self, results: List[Dict]) -> Dict[str, Any]:
        """Merge results from multiple agents with priority"""
        if not results:
            return self.get_fallback_response()
        
        # Prioritize based on config
        priority_order = self.config['synthesis']['agent_priority']
        
        synthesized = {
            "success": True,
            "formatted_summary": "",
            "agents_used": []
        }
        
        # Build merged response with agent headers
        for result in sorted(results, key=lambda x: priority_order.get(x.get('agent_name', ''), 999)):
            if result.get('formatted_summary'):
                agent_name = result.get('agent_name', 'Unknown')
                synthesized['agents_used'].append(agent_name)
                
                if self.config['provenance']['show_agent_header']:
                    synthesized['formatted_summary'] += f"\n\n🤖 {agent_name} Agent:\n"
                
                synthesized['formatted_summary'] += result['formatted_summary']
        
        return synthesized
```

## 🧪 PHASE 5: Testing & Validation

### 5.1 Create Integration Tests
**File:** `tests/test_langchain_integration.py`

```python
import pytest
from core.langchain.orchestrator import LangChainOrchestrator

@pytest.mark.asyncio
async def test_medical_search_always_returns():
    """Verify medical_search results are always surfaced"""
    orchestrator = LangChainOrchestrator("config/orchestrator.yml")
    
    # Test query that should trigger medical_search
    result = await orchestrator.process("recent articles on cardiovascular health")
    
    assert result['success'] is True
    assert 'formatted_summary' in result
    assert len(result['formatted_summary']) > 0
    assert 'medical_search' in result.get('agents_used', [])

@pytest.mark.asyncio
async def test_fallback_on_failure():
    """Verify fallback works when all agents fail"""
    orchestrator = LangChainOrchestrator("config/orchestrator.yml")
    
    # Simulate failure by disconnecting MCP
    orchestrator.agents = {}  # No agents available
    
    result = await orchestrator.process("test query")
    
    assert 'formatted_summary' in result
    assert 'Fallback' in result.get('agent_name', '')

@pytest.mark.asyncio
async def test_parallel_agent_execution():
    """Test parallel agent execution preserves all results"""
    orchestrator = LangChainOrchestrator("config/orchestrator.yml")
    orchestrator.config['selection']['allow_parallel_helpers'] = True
    
    result = await orchestrator.process("research on diabetes diagnosis")
    
    # Should have multiple agents responding
    assert len(result.get('agents_used', [])) > 1
    assert 'medical_search' in result['agents_used']
```

### 5.2 Smoke Test Script
```bash
#!/bin/bash
# smoke_test_langchain.sh

echo "Testing LangChain integration..."

# Test 1: Basic connectivity
curl -X POST http://localhost:8000/complete \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"content": "test connection"}]}'

# Test 2: Medical search
curl -X POST http://localhost:8000/complete \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"content": "recent articles on hypertension"}]}'

# Test 3: Verify provenance headers
curl -X POST http://localhost:8000/complete \
  -H "Accept: text/plain" \
  -d '{"messages": [{"content": "cardiovascular research"}]}' \
  | grep -q "🤖.*Agent Response:" && echo "✅ Provenance headers working"
```

## 📋 PHASE 6: Configuration Updates

### 6.1 Update orchestrator.yml
```yaml
# Add LangChain-specific settings
langchain:
  verbose: true  # Enable detailed logging
  max_iterations: 3
  early_stopping_method: "generate"
  
  # Chain configuration
  routing:
    default_agent: "medical_search"
    router_model: "llama3.1:8b"
    
  # Memory settings
  memory:
    type: "conversation_summary_buffer"
    max_tokens: 2000
    
  # Tool settings
  tools:
    handle_errors: true
    return_direct: false
    max_retries: 2
```

## ⚠️ CRITICAL CONSIDERATIONS

### Must Maintain:
- **PHI Protection**: All LangChain components must use local models only
- **Medical Disclaimers**: Every response must include appropriate disclaimers
- **Audit Logging**: Maintain HIPAA-compliant audit trail through LangChain
- **Configuration**: Keep all settings externalized in YAML

### Watch Out For:
- **Memory Management**: LangChain's memory can grow large - implement cleanup
- **Token Limits**: Monitor token usage with local models
- **Error Handling**: Ensure all errors are PHI-safe in logs
- **Performance**: Add caching layer for repeated queries

## 🚀 IMPLEMENTATION ORDER

1. **Day 1: Setup & Tool Wrapping**
   - Install dependencies
   - Create tool wrappers
   - Test MCP integration through LangChain

2. **Day 2: Agent Migration**
   - Implement base HealthcareLangChainAgent
   - Migrate medical_search_agent first
   - Test with simple queries

3. **Day 3: Orchestrator & Router**
   - Implement LangChainOrchestrator
   - Update main.py integration
   - Test multi-agent coordination

4. **Day 4: Testing & Refinement**
   - Run comprehensive tests
   - Fix synthesis issues
   - Optimize performance

5. **Day 5: Documentation & Handoff**
   - Update instruction files
   - Document patterns learned
   - Create next session handoff

## 📝 SUCCESS METRICS

- [ ] MCP tools work reliably through LangChain
- [ ] Medical_search results always appear when relevant
- [ ] Agent failures don't block responses
- [ ] Response time < 5 seconds for simple queries
- [ ] All tests passing
- [ ] Configuration remains external
- [ ] PHI protection maintained
- [ ] Audit logging working

## 🔄 ROLLBACK PLAN

If LangChain integration fails:
1. Keep current code in `main_legacy.py`
2. Use feature flag to switch between implementations
3. Gradual migration - start with one agent
4. Maintain parallel implementations during transition

---

**Ready to Start**: This TODO provides a complete roadmap for LangChain integration. Begin with Phase 1 and work systematically through each phase. The key is wrapping existing components rather than rewriting everything.