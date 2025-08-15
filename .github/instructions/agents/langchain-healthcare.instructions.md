# LangChain Healthcare Agent Implementation Patterns (Updated 2025-08-15)

**WORKFLOW CONTROL**: All workflows are controlled by `copilot-instructions.md`. This file provides implementation patterns only.

## Healthcare Agent Initialization Patterns (2025-08-15)

### Core Agent Structure

```python
class HealthcareLangChainAgent:
    """LangChain agent optimized for healthcare workflows with MCP integration."""
    
    def __init__(self, mcp_client: DirectMCPClient, model: str = "llama3.1:8b"):
        """Initialize healthcare agent with robust error handling."""
        self.mcp_client = mcp_client
        self.logger = setup_healthcare_agent_logging('langchain_healthcare')
        
        # CRITICAL: Use healthcare-specific Ollama configuration
        self.llm = self._create_healthcare_llm(model)
        self.tools = self._create_mcp_tools()
        self.executor = self._create_agent_executor()
        
        self.logger.info("HealthcareLangChainAgent initialized successfully")
    
    def _create_healthcare_llm(self, model: str):
        """Create LLM with healthcare-optimized configuration."""
        from .config import HealthcareOllamaConfig
        
        config = HealthcareOllamaConfig.create_ollama_config(model)
        
        # Test connection before proceeding
        if not HealthcareOllamaConfig.test_ollama_connection(config.base_url):
            raise ConnectionError(f"Ollama connection failed: {config.base_url}")
        
        return ChatOllama(
            model=config.model,
            temperature=config.temperature,
            base_url=config.base_url,
            num_ctx=config.num_ctx
        )
    
    def _create_mcp_tools(self) -> List[Tool]:
        """Create MCP tools with healthcare-specific error handling."""
        tools = []
        
        # Healthcare-specific MCP tools
        healthcare_tools = [
            'search-pubmed',
            'search-clinical-trials', 
            'get-drug-info',
            'search-fhir-patients',
            'get-medical-codes',
            'analyze-medical-image',
            'get-lab-reference-ranges',
            'search-medical-guidelines'
        ]
        
        for tool_name in healthcare_tools:
            try:
                tool = Tool(
                    name=tool_name,
                    description=self._get_tool_description(tool_name),
                    func=lambda query, name=tool_name: self._call_mcp_tool_safe(name, query)
                )
                tools.append(tool)
                self.logger.info(f"Registered MCP tool: {tool_name}")
            except Exception as e:
                self.logger.warning(f"Failed to register tool {tool_name}: {e}")
        
        return tools
    
    async def _call_mcp_tool_safe(self, tool_name: str, params: Dict[str, Any]) -> str:
        """Call MCP tool with comprehensive error handling."""
        try:
            self.logger.info(f"Calling MCP tool: {tool_name}")
            result = await self.mcp_client.call_tool(tool_name, params)
            self.logger.info(f"MCP tool {tool_name} completed successfully")
            return str(result)
        except BrokenPipeError as e:
            self.logger.error(f"MCP tool {tool_name} broken pipe error: {e}")
            return f"Tool {tool_name} temporarily unavailable (connection error). Please try again."
        except Exception as e:
            self.logger.error(f"MCP tool {tool_name} failed: {e}")
            return f"Tool {tool_name} failed: {str(e)}"
        from langchain import hub
        from langchain.agents import create_react_agent, AgentExecutor
        
        # Use official ReAct prompt - more stable than custom prompts
        prompt = hub.pull("hwchase17/react")
        agent = create_react_agent(llm=self.llm, tools=self.tools, prompt=prompt)
        
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=5,
            handle_parsing_errors="Check your output and make sure it conforms!",
            return_intermediate_steps=True
            # CRITICAL: No memory parameter - prevents scratchpad conflicts
        )
```

## Connection Debugging Patterns

### Ollama Connection Validation

```python
def validate_ollama_connection(base_url: str) -> Dict[str, Any]:
    """Validate Ollama connection with detailed diagnostics."""
    import httpx
    
    try:
        response = httpx.get(f"{base_url}/api/version", timeout=5.0)
        if response.status_code == 200:
            version_data = response.json()
            return {
                "connected": True,
                "version": version_data.get("version", "unknown"),
                "url": base_url
            }
    except httpx.ConnectError:
        return {
            "connected": False,
            "error": "Connection refused",
            "suggestion": "Check if Ollama is running and URL is correct"
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "suggestion": "Check network connectivity and firewall settings"
        }

def diagnose_langchain_connection_issues():
    """Comprehensive LangChain connection diagnostics."""
    import os
    
    print("🔍 LangChain Healthcare Agent Connection Diagnostics")
    
    # Check environment
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    print(f"OLLAMA_URL: {ollama_url}")
    
    # Test direct connection
    connection_result = validate_ollama_connection(ollama_url)
    if connection_result["connected"]:
        print(f"✅ Ollama connection successful: {connection_result['version']}")
    else:
        print(f"❌ Ollama connection failed: {connection_result['error']}")
        print(f"💡 Suggestion: {connection_result['suggestion']}")
    
    # Test agent creation
    try:
        from core.mcp.direct_mcp_client import DirectMCPClient
        mcp_client = DirectMCPClient()
        agent = HealthcareLangChainAgent(mcp_client)
        print("✅ Healthcare agent creation successful")
        
        # Test direct LLM call
        from langchain_core.messages import HumanMessage
        response = agent.llm.invoke([HumanMessage(content="Hello")])
        print("✅ Direct LLM communication successful")
        
    except Exception as e:
        print(f"❌ Agent creation failed: {e}")
```

## Error Handling Patterns

### Graceful MCP Tool Failures

```python
async def safe_agent_processing(agent, query: str) -> Dict[str, Any]:
    """Process query with healthcare-appropriate error handling."""
    try:
        result = await agent.executor.ainvoke({"input": query})
        
        # Extract meaningful response
        output = result.get("output", "")
        steps = result.get("intermediate_steps", [])
        
        return {
            "success": True,
            "response": output,
            "steps": steps,
            "agent_name": "medical_search"
        }
        
    except Exception as e:
        # Log error but return user-friendly message
        logger.error(f"Agent processing failed: {e}", exc_info=True)
        
        return {
            "success": True,  # Don't expose errors to users
            "response": "I encountered a technical issue while processing your request. Please try rephrasing your question or contact support if the issue persists.",
            "steps": [],
            "agent_name": "medical_search",
            "internal_error": str(e)  # For debugging only
        }
```

## Tool Integration Patterns

### MCP Tool Creation with Retry Logic

```python
def create_robust_mcp_tools(mcp_client, max_retries: int = 3):
    """Create MCP tools with robust retry patterns."""
    
    class RetryMCPTool:
        def __init__(self, tool_name: str, client, max_retries: int):
            self.tool_name = tool_name
            self.client = client
            self.max_retries = max_retries
        
        async def __call__(self, *args, **kwargs):
            last_error = None
            
            for attempt in range(self.max_retries):
                try:
                    return await self.client.call_tool(self.tool_name, *args, **kwargs)
                except BrokenPipeError as e:
                    last_error = e
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff
                        continue
                    break
                except Exception as e:
                    # Non-retryable errors
                    raise e
            
            raise last_error or Exception(f"Tool {self.tool_name} failed after {self.max_retries} attempts")
    
    return [RetryMCPTool("search_medical_literature", mcp_client, max_retries)]
```

## Configuration Files to Update

When implementing healthcare LangChain agents, ensure these files use correct Ollama URLs:

1. **Core Agent Configuration**: `services/user/healthcare-api/core/langchain/agents.py`
   - Default: `http://localhost:11434` (not `http://ollama:11434`)

2. **MCP Server Configuration**: `services/user/healthcare-mcp/src/server/HealthcareServer.ts`
   - Default: `http://localhost:11434`

3. **Test Configurations**: Any test files should use environment variables with localhost fallback

## Environment Variables

```bash
# Recommended environment setup
export OLLAMA_URL="http://localhost:11434"
export HEALTHCARE_AGENT_DEBUG="true"  # Enable verbose logging
export LANGCHAIN_TRACING_V2="false"   # Disable external tracing for PHI safety
```
