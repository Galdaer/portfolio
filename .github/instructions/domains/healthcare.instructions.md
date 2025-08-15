# Healthcare Domain Patterns

**WORKFLOW CONTROL**: All workflows are controlled by `copilot-instructions.md`. This file provides implementation patterns only.

## Healthcare Infrastructure Integration Patterns (Updated 2025-01-15)

### LangChain Agent Orchestrator with Existing Agent Adapters

```python
# CRITICAL PATTERN: Thin adapter pattern preserves existing agents
# LangChain acts as orchestrator, not replacement for existing healthcare agents

from langchain.tools import tool
from typing import Dict, Any
import json

class HealthcareLangChainOrchestrator:
    """Orchestrator that coordinates existing healthcare agents through thin adapters."""
    
    def __init__(self, discovered_agents: Dict[str, Any]):
        # Create thin wrappers for each existing agent - NO CODE DUPLICATION
        self.tools = []
        for agent_name, agent_instance in discovered_agents.items():
            self.tools.append(create_agent_tool(agent_instance, agent_name))
        
        # LangChain uses these tools to coordinate workflow
        self.chain = create_orchestration_chain(self.tools)

def create_agent_tool(agent, name):
    """Create LangChain tool from existing agent - preserves agent logging."""
    
    @tool(name=f"{name}_agent")
    async def agent_wrapper(request: str) -> str:
        # Parse LangChain's string input to agent's expected format
        try:
            parsed_request = json.loads(request)
        except json.JSONDecodeError:
            parsed_request = {"query": request}  # Simple fallback
        
        # Call EXISTING agent's EXISTING method - preserves agent-specific logging
        result = await agent.process_request(parsed_request)
        
        # Return in format LangChain expects
        return json.dumps(result, default=str)
    
    return agent_wrapper

# Agent routing pattern - DON'T bypass existing agents
async def route_medical_query(query: str, orchestrator: HealthcareLangChainOrchestrator):
    """Route medical queries through proper agents, not direct MCP tools."""
    # LangChain decides which agents to use
    # Medical queries go to medical_search_agent (logs to agent_medical_search.log)
    # Intake queries go to intake_agent
    # Complex queries can use multiple agents
    return await orchestrator.process(query)
```

### MCP Integration with Container Architecture

```python
# BaseHealthcareAgent inheritance for LangChain agents
from agents import BaseHealthcareAgent
from core.mcp.direct_mcp_client import DirectMCPClient

class HealthcareLangChainAgent(BaseHealthcareAgent):
    def __init__(self, mcp_client: DirectMCPClient, **kwargs):
        super().__init__(mcp_client=mcp_client, agent_name="langchain_medical")
        
        # CRITICAL: Configure for medical query complexity
        self.max_iterations = 10  # Increased for medical searches
        self.timeout = 120  # 2 minutes for comprehensive medical queries
        
        # Inherits healthcare logging, PHI monitoring, database connectivity

# Container-aware MCP tool calling
async def call_healthcare_tool(tool_name: str, parameters: dict) -> dict:
    """Healthcare tool calling with container architecture awareness."""
    from core.tools import tool_registry
    
    try:
        # Use ToolRegistry with MCP container integration
        await tool_registry.initialize()
        result = await tool_registry.call_tool(tool_name, parameters)
        return result
    except FileNotFoundError as e:
        if "MCP server not found" in str(e):
            # Expected in host environment without MCP server
            logger.warning(f"MCP unavailable in host environment: {tool_name}")
            return {"error": "Medical database temporarily unavailable"}
        raise
    except Exception as e:
        logger.error(f"ToolRegistry call failed for {tool_name}: {e}")
        return {"error": f"Tool execution failed: {type(e).__name__}"}

# PHI Detection integration with medical content awareness
from src.healthcare_mcp.phi_detection import sanitize_for_compliance

def sanitize_medical_request(request_data: dict) -> dict:
    """HIPAA-compliant sanitization that preserves medical terminology."""
    return sanitize_for_compliance(request_data)

def sanitize_medical_response(response_data: dict) -> dict:
    """PHI sanitization for responses while preserving medical education content."""
    return sanitize_for_compliance(response_data)
```

### Open WebUI Medical Query Routing

```python
class MedicalQueryRouter:
    """Routes medical queries to appropriate healthcare agents."""
    
    def __init__(self, healthcare_agent):
        self.healthcare_agent = healthcare_agent
        self.medical_indicators = [
            "symptoms", "treatment", "medication", "diagnosis", 
            "disease", "condition", "therapy", "clinical",
            "pubmed", "research", "studies", "trials"
        ]
    
    async def route_query(self, query: str, user_context: dict = None) -> dict:
        """Route query to medical agent if medical content detected."""
        
        if self._is_medical_query(query):
            # Route to healthcare agent with proper configuration
            try:
                result = await self.healthcare_agent.process(query)
                
                # Add medical disclaimers
                if result.get("success"):
                    result["medical_disclaimer"] = self._get_medical_disclaimer()
                    result["agent_type"] = "medical_search"
                
                return result
                
            except Exception as e:
                if "iteration limit" in str(e):
                    return {
                        "error": "Medical query too complex",
                        "suggestion": "Please break down your question into smaller parts",
                        "medical_disclaimer": self._get_medical_disclaimer()
                    }
                raise
        else:
            # Route to general agent
            return await self._process_general_query(query)
    
    def _is_medical_query(self, query: str) -> bool:
        """Detect if query requires medical agent processing."""
        query_lower = query.lower()
        return any(indicator in query_lower for indicator in self.medical_indicators)
    
    def _get_medical_disclaimer(self) -> str:
        """Standard medical disclaimer for all responses."""
        return (
            "This information is for educational purposes only. "
            "Always consult with qualified healthcare professionals for medical advice."
        )
```

## Medical Safety Patterns

```python
# Medical advice prevention
def validate_medical_request(request: str) -> bool:
    medical_keywords = ["diagnose", "treatment", "medication", "symptoms"]
    if any(keyword in request.lower() for keyword in medical_keywords):
        return False, "I cannot provide medical advice. Please consult with a healthcare professional."
    return True, None

# Medical disclaimer injection
MEDICAL_DISCLAIMER = """
This system provides information for healthcare professionals only.
Not intended for direct patient diagnosis or treatment decisions.
All medical decisions require licensed healthcare provider oversight.
"""

def add_medical_disclaimer(response: str) -> str:
    return f"{response}\n\n{MEDICAL_DISCLAIMER}"
```

## Financial Calculation Patterns

```python
from decimal import Decimal

# Safe division with zero protection
def safe_division(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator <= 0:
        return Decimal('0')
    return numerator / denominator

# Convert to Decimal safely
def to_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))  # Preserves precision
    raise ValueError(f"Cannot convert {type(value)} to Decimal")

# Insurance copay calculation
def calculate_copay(amount: Decimal, percentage: Decimal) -> Decimal:
    if percentage <= 0:
        return Decimal('0')
    return amount * (percentage / Decimal('100'))
```

### Healthcare LangChain Configuration (Updated 2025-08-15)

```python
# ✅ CRITICAL: Ollama connection patterns for healthcare environments
class HealthcareOllamaConfig:
    """Ollama configuration patterns for local healthcare environments."""
    
    @staticmethod
    def create_ollama_config(model: str = "llama3.1:8b") -> OllamaConfig:
        """Create Ollama config with proper environment handling."""
        import os
        
        # CRITICAL: Use localhost for local development, allow override
        base_url = os.getenv("OLLAMA_URL", "http://172.20.0.10:11434")
        
        # Warn if using Docker hostname in local environment
        if "ollama:" in base_url and "docker" not in os.getenv("CONTAINER_ENV", ""):
            logger.warning(f"Using Docker hostname {base_url} in local environment - may cause connection failures")
        
        return OllamaConfig(
            model=model,
            temperature=0.1,  # Conservative for healthcare
            base_url=base_url,
            num_ctx=4096
        )
    
    @staticmethod
    def test_ollama_connection(base_url: str) -> bool:
        """Test Ollama connection before agent initialization."""
        import httpx
        try:
            response = httpx.get(f"{base_url}/api/version", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

# ✅ Healthcare agent initialization with connection validation
def create_healthcare_langchain_agent(mcp_client, model: str = "llama3.1:8b"):
    """Create LangChain agent with healthcare-specific validation."""
    config = HealthcareOllamaConfig.create_ollama_config(model)
    
    # Test connection before proceeding
    if not HealthcareOllamaConfig.test_ollama_connection(config.base_url):
        raise ConnectionError(f"Cannot connect to Ollama at {config.base_url}")
    
    llm = build_chat_model(config)
    tools = create_mcp_tools(mcp_client)
    
    return HealthcareAgentReliability.create_stable_healthcare_agent(llm, tools)
`
### Open WebUI Integration Patterns (Added 2025-08-15)

```python
# ✅ Open WebUI request classification for healthcare
class HealthcareRequestClassifier:
    """Classify incoming requests for proper agent routing."""
    
    MEDICAL_KEYWORDS = [
        'medical', 'health', 'disease', 'condition', 'symptoms', 'treatment',
        'medication', 'clinical', 'patient', 'diagnosis', 'research', 'study',
        'pubmed', 'literature', 'journal', 'evidence', 'drug', 'therapy'
    ]
    
    @classmethod
    def is_medical_query(cls, query: str) -> bool:
        """Determine if query should be routed to medical agents."""
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in cls.MEDICAL_KEYWORDS)
    
    @classmethod
    def get_intent_classification(cls, query: str) -> str:
        """Classify query intent for agent selection."""
        if cls.is_medical_query(query):
            if 'research' in query.lower() or 'study' in query.lower():
                return 'medical_research'
            elif 'drug' in query.lower() or 'medication' in query.lower():
                return 'pharmaceutical'
            else:
                return 'medical_general'
        return 'general'

# ✅ Healthcare API endpoint patterns for Open WebUI
class HealthcareAPIEndpoints:
    """Endpoint patterns for Open WebUI integration."""
    
    @staticmethod
    async def chat_completion(request: ChatCompletionRequest) -> ChatCompletionResponse:
        """Handle Open WebUI chat completion requests."""
        query = request.messages[-1].content
        intent = HealthcareRequestClassifier.get_intent_classification(query)
        
        # Route to appropriate healthcare agent
        if intent.startswith('medical'):
            agent = get_medical_agent(intent)
            response = await agent.process(query)
            
            # Ensure medical disclaimer is included
            response = add_medical_disclaimer(response)
        else:
            response = await process_general_query(query)
        
        return ChatCompletionResponse(
            id=f"chat-{uuid4()}",
            choices=[Choice(message=Message(content=response))],
            model=request.model
        )

# ✅ Agent logging patterns for debugging Open WebUI issues
def setup_healthcare_agent_logging(agent_name: str):
    """Setup comprehensive logging for healthcare agent debugging."""
    import logging
    
    # Create agent-specific logger
    logger = logging.getLogger(f'healthcare.agent.{agent_name}')
    logger.setLevel(logging.INFO)
    
    # Add file handler for agent-specific logs
    handler = logging.FileHandler(f'logs/agent_{agent_name}.log')
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Log initialization
    logger.info(f"{agent_name} initialized")
    logger.info(f"MCP client: {type(mcp_client)} - {mcp_client}")
    logger.info(f"LLM client: {type(llm_client)} - {llm_client}")
    
    return logger
```

### Healthcare AI Agent Reliability (Updated 2025-08-14)

```python
# ✅ CRITICAL: LangChain agent patterns for healthcare stability
class HealthcareAgentReliability:
    """Agent reliability patterns from critical bug fixes."""
    
    @staticmethod
    def create_stable_healthcare_agent(llm, tools):
        """Create LangChain agent with healthcare-specific stability patterns."""
        from langchain import hub
        from langchain.agents import create_react_agent, AgentExecutor
        
        # Use proven ReAct pattern - more stable than structured chat
        prompt = hub.pull("hwchase17/react")
        agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)
        
        # CRITICAL: No memory parameter to prevent scratchpad conflicts
        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            return_intermediate_steps=True,
            handle_parsing_errors="Check your output and make sure it conforms!",
            # NO memory - prevents "agent_scratchpad should be a list of base messages" error
            # NO early_stopping_method - not supported by ReAct agents
        )
        return executor
    
    @staticmethod
    def safe_agent_execution(executor, query: str) -> Dict[str, Any]:
        """Execute agent with healthcare-appropriate error handling."""
        try:
            # CRITICAL: Only pass input - let AgentExecutor manage scratchpad
            result = await executor.ainvoke({"input": query})
            
            return {
                "success": True,
                "response": result.get("output", ""),
                "steps": result.get("intermediate_steps", [])
            }
        except Exception as e:
            # Healthcare-appropriate error response
            return {
                "success": False,
                "response": "I encountered a technical issue. Please try rephrasing your question.",
                "error": str(e),  # For logging only
                "steps": []
            }
    
    @staticmethod
    def create_medical_tool_wrapper(async_tool_func):
        """Wrap async medical tools for LangChain compatibility."""
        import asyncio
        import json
        
        def sync_wrapper(*args, **kwargs) -> str:
            if asyncio.iscoroutinefunction(async_tool_func):
                try:
                    asyncio.get_running_loop()
                    # In async context - use thread executor
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, async_tool_func(*args, **kwargs))
                        result = future.result()
                except RuntimeError:
                    # No running loop - use asyncio.run directly
                    result = asyncio.run(async_tool_func(*args, **kwargs))
            else:
                result = async_tool_func(*args, **kwargs)
            
            # Always return string for LangChain compatibility
            if isinstance(result, dict):
                return json.dumps(result, indent=2)
            return str(result)
        
        return sync_wrapper
```

# ✅ CRITICAL: Database resource management patterns
class HealthcareDatabaseSafety:
    """Database connection safety patterns from production issues."""
    
    @asynccontextmanager
    async def get_connection_with_auto_release(self):
        """Proper database connection management."""
        conn = await self.pool.acquire()
        try:
            yield conn
        finally:
            await self.pool.release(conn)
    
    async def safe_database_operation(self, operation_func, *args, **kwargs):
        """Template for safe database operations."""
        async with self.get_connection_with_auto_release() as conn:
            return await operation_func(conn, *args, **kwargs)

# ✅ CRITICAL: Avoid code duplication patterns
class HealthcareCodeOrganization:
    """Code organization patterns to prevent duplication."""
    
    # Common utilities should be in shared modules:
    # - domains/healthcare_utils.py for financial utilities
    # - core/utils/type_conversion.py for type safety utilities  
    # - core/utils/database_helpers.py for connection management
    
    @staticmethod
    def identify_duplicate_methods() -> List[str]:
        """Methods commonly duplicated across healthcare modules."""
        return [
            "_ensure_decimal",
            "_get_negotiated_rate", 
            "_get_patient_coverage_data",
            "_validate_database_connection"
        ]

### Healthcare Compliance Patterns

```python
# ✅ CORRECT: Comprehensive healthcare logging and PHI monitoring
class HealthcareLoggingPatterns:
    def __init__(self):
        # Setup HIPAA-compliant logging with PHI detection
        pass

class PHIMonitor:
    def detect_phi(self, data: str) -> bool:
        # Detect SSN, DOB, medical record numbers, phone numbers
        pass
    
    def anonymize_for_logging(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Remove/hash PHI for safe logging
        pass

@healthcare_log_method
def process_patient_intake(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
    # Process healthcare data with automatic audit logging
    return processed_data
```

### Medical Workflow Integration

```python
# ✅ CORRECT: Healthcare workflow patterns
class HealthcareWorkflowManager:
    def process_soap_note(self, soap_data: Dict[str, Any]) -> Dict[str, Any]:
        # Process SOAP notes with medical compliance validation
        pass
    
    def schedule_appointment(self, request: Dict[str, Any]) -> Dict[str, Any]:
        # Administrative scheduling without medical decision-making
        pass
```

### Healthcare AI Agent Coordination

```python
# ✅ CORRECT: Multi-agent healthcare coordination
class HealthcareAgentOrchestrator:
    def coordinate_intake_workflow(self, patient_request: Dict[str, Any]):
        # Route through: intake → document_processor → clinical_research_agent
        pass
    
    def handle_emergency_scenario(self, emergency_data: Dict[str, Any]):
        # Escalate to human healthcare providers immediately
        pass
```

## Healthcare Domain Integration Patterns

### EHR Integration with AI Safety

```python
# ✅ CORRECT: Safe EHR integration patterns
class SafeEHRIntegration:
    def fetch_patient_data(self, patient_id: str, required_fields: List[str]):
        # Minimum necessary principle, audit logging, PHI protection
        pass
    
    def update_patient_record(self, patient_id: str, updates: Dict[str, Any]):
        # Validate updates don't contain medical advice or diagnosis
        pass
```

### Clinical Decision Support Integration

```python
# ✅ CORRECT: AI-assisted clinical decision support (administrative only)
class ClinicalDecisionSupportAssistant:
    def suggest_documentation_improvements(self, note: str):
        # Suggest documentation completeness, not medical decisions
        pass
    
    def validate_coding_accuracy(self, diagnosis_codes: List[str]):
        # Administrative coding validation, not medical interpretation
        pass
```

## PHI-Safe Development Patterns

- **Never expose real patient data** in logs, tests, or API calls
- **Use synthetic data generators** for all healthcare scenarios
- **Document all endpoints** with compliance disclaimers
- **Validate all external API calls** for PHI safety before deployment
- **Medical Safety**: Always redirect medical advice requests to healthcare professionals

## Updated PHI Handling (2025-08-14)

- Literature authorship and publication metadata are not PHI and should be preserved.
- Error logs must not include patient identifiers; use DIAGNOSTIC markers and previews capped to 200 chars.
- Minimum Necessary still applies to EHR data; not applicable to public literature metadata.

## Medical Data Processing Patterns (2025-08-14)

- Normalize literature sources with DOI/PMID/URL keys; deduplicate on that precedence.
- Provide DOI link first, then PubMed link; include year, journal, and abstract snippet when present.
- Always return a disclaimer and a readable summary even on timeouts or upstream errors.

---
