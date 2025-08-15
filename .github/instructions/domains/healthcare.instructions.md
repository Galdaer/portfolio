# Healthcare Domain Patterns

**WORKFLOW CONTROL**: All workflows are controlled by `copilot-instructions.md`. This file provides implementation patterns only.

## Healthcare Infrastructure Integration Patterns (Updated 2025-01-15)

### MCP Data Structure Patterns (CRITICAL - 2025-01-15)

```python
# UNIVERSAL MCP RESPONSE STRUCTURE - ALL TOOLS FOLLOW THIS PATTERN:
# {"content": [{"type": "text", "text": "JSON_STRING"}]}

# Tool-specific JSON_STRING contents:
# - PubMed: '{"articles": [...]}'
# - Clinical Trials: '{"results": [...]}'  (tool: "search-trials")
# - FDA: '{"results": [...]}'  (tool: "get-drug-info")

def parse_mcp_response(mcp_result: dict, data_key: str = "articles") -> list:
    """Universal MCP response parser for all healthcare tools."""
    import json
    
    try:
        if not mcp_result.get("content") or not len(mcp_result["content"]):
            return []
            
        content_item = mcp_result["content"][0]
        if "text" not in content_item:
            return []
            
        # Parse the JSON string to get actual data
        data = json.loads(content_item["text"])
        return data.get(data_key, [])
        
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.error(f"Failed to parse MCP response: {e}")
        return []

# Usage examples:
# PubMed: articles = parse_mcp_response(pubmed_result, "articles")
# Clinical Trials: trials = parse_mcp_response(trials_result, "results")
# FDA: drugs = parse_mcp_response(fda_result, "results")
```

### Enhanced Query Engine Tool Selection (CRITICAL - 2025-01-15)

```python
# AVOID HARDCODING - Let agents choose tools based on query intent and descriptions

class QueryType(Enum):
    SYMPTOM_ANALYSIS = "symptom_analysis"      # PubMed only
    LITERATURE_RESEARCH = "literature_research"  # PubMed + Clinical Trials
    DRUG_RESEARCH = "drug_research"           # PubMed + FDA + Trials
    COMPREHENSIVE = "comprehensive"           # All tools

def select_tools_by_intent(query_type: QueryType) -> list:
    """Dynamic tool selection based on medical query intent."""
    base_tools = ["search-pubmed"]  # Always include PubMed
    
    if query_type == QueryType.LITERATURE_RESEARCH:
        return base_tools + ["search-trials"]
    elif query_type == QueryType.DRUG_RESEARCH:
        return base_tools + ["get-drug-info", "search-trials"]
    elif query_type == QueryType.COMPREHENSIVE:
        return base_tools + ["search-trials", "get-drug-info"]
    else:  # SYMPTOM_ANALYSIS
        return base_tools  # PubMed only for simple symptom queries

# Session-level caching to prevent duplicate tool calls
_session_cache = {}

async def cached_tool_call(tool_name: str, params: dict, session_id: str) -> dict:
    """Prevent multiple calls to same tool within session."""
    cache_key = f"{session_id}:{tool_name}:{hash(str(sorted(params.items())))}"
    
    if cache_key in _session_cache:
        logger.info(f"Using cached result for {tool_name}")
        return _session_cache[cache_key]
    
    result = await call_tool(tool_name, params)
    _session_cache[cache_key] = result
    return result
```

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
        
        # CRITICAL: Return conclusive answers, not just source lists
        if "sources" in result and len(result["sources"]) > 0:
            # Synthesize actual answer from sources
            answer = synthesize_medical_answer(parsed_request["query"], result["sources"])
            return f"FINAL ANSWER: {answer}\n\nSources: {format_sources(result['sources'])}"
        
        return json.dumps(result, default=str)
    
    return agent_wrapper

def synthesize_medical_answer(query: str, sources: list) -> str:
    """Convert source lists into actual answers to prevent LangChain iteration loops."""
    # Extract key information from source abstracts/titles
    # Provide direct answer to user's question
    # Include medical disclaimers
    pass
```

### Database vs External API Investigation Patterns (NEW - 2025-01-15)

```python
# CRITICAL: Determine data source for accurate medical information

async def investigate_data_source(query: str, mcp_client: DirectMCPClient) -> dict:
    """Determine if results come from local database or external APIs."""
    import time
    
    start_time = time.time()
    result = await mcp_client.call_tool("search-pubmed", {"query": query})
    end_time = time.time()
    
    response_time = end_time - start_time
    
    # Pattern recognition for data source identification
    if response_time < 0.5:
        source_type = "cached_database"  # Fast responses = local database
    elif response_time > 5.0:
        source_type = "external_api"     # Slow responses = API calls
    else:
        source_type = "hybrid"           # Mixed sources
    
    # Check article count patterns
    articles = parse_mcp_response(result, "articles")
    if len(articles) > 50:
        source_type += "_large_dataset"  # Database likely has comprehensive data
    
    return {
        "source_type": source_type,
        "response_time": response_time,
        "article_count": len(articles),
        "investigation_time": time.strftime("%Y-%m-%d %H:%M:%S")
    }

# Pattern: Prefer database over external APIs for reliability
async def prioritized_search(query: str, mcp_client: DirectMCPClient) -> dict:
    """Search strategy that prioritizes database over external APIs."""
    
    # 1. Always try database first
    db_result = await investigate_data_source(query, mcp_client)
    
    if db_result["article_count"] >= 5:  # Sufficient database results
        logger.info(f"Using database results: {db_result['article_count']} articles")
        return db_result
    
    # 2. Only use external APIs if database insufficient
    logger.info("Database results insufficient, checking external APIs")
    # Implementation would check external API tools here
    
    return db_result

# Database schema investigation for medical content
def investigate_medical_database() -> dict:
    """Investigate local medical database capabilities and content."""
    try:
        # Check database connection and medical content availability
        # This helps determine what's available locally vs externally
        from core.database import DatabaseManager
        
        db = DatabaseManager()
        # Check for medical literature tables, article counts, etc.
        medical_stats = db.get_medical_content_stats()
        
        return {
            "database_available": True,
            "medical_articles": medical_stats.get("article_count", 0),
            "last_updated": medical_stats.get("last_update"),
            "data_sources": medical_stats.get("sources", [])
        }
    except Exception as e:
        return {
            "database_available": False,
            "error": str(e)
        }
```

### Agent Iteration Control Patterns (NEW - 2025-01-15)

```python
# Prevent LangChain orchestrator from hitting iteration limits

class MedicalQueryHandler:
    """Handle medical queries with controlled iteration and conclusive answers."""
    
    def __init__(self, max_iterations: int = 8):
        self.max_iterations = max_iterations
        self.current_iteration = 0
        
    async def process_medical_query(self, query: str) -> str:
        """Process medical query with iteration control and conclusive answers."""
        
        self.current_iteration = 0
        search_performed = False
        final_answer = ""
        
        while self.current_iteration < self.max_iterations:
            self.current_iteration += 1
            
            if not search_performed:
                # First iteration: search for medical information
                search_result = await self.search_medical_literature(query)
                search_performed = True
                
                if search_result["articles"]:
                    # CRITICAL: Provide conclusive answer, not just sources
                    final_answer = self.synthesize_medical_answer(query, search_result["articles"])
                    break  # Exit loop with answer
                else:
                    final_answer = "No relevant medical literature found for this query."
                    break  # Exit loop with no-results answer
            else:
                # Subsequent iterations shouldn't happen - we provide conclusive answers
                logger.warning(f"Unexpected iteration {self.current_iteration} for medical query")
                break
        
        if self.current_iteration >= self.max_iterations:
            logger.error("Medical query hit iteration limit - agent design issue")
            final_answer = "Medical query processing exceeded limits. Please rephrase your question."
        
        return final_answer
    
    def synthesize_medical_answer(self, query: str, articles: list) -> str:
        """Convert article list into conclusive medical answer."""
        
        # Extract relevant information from articles
        key_findings = []
        for article in articles[:5]:  # Use top 5 most relevant
            if "abstract" in article:
                key_findings.append(article["abstract"][:200])  # First 200 chars
        
        # Synthesize into answer format
        answer = f"Based on current medical literature:

"
        for i, finding in enumerate(key_findings, 1):
            answer += f"{i}. {finding}...
"
        
        answer += "
**Medical Disclaimer**: This information is for educational purposes only and should not replace professional medical advice."
        
        return answer

# Pattern: Agent adapters must return conclusive answers
def create_conclusive_agent_adapter(agent, name):
    """Create agent adapter that prevents iteration loops."""
    
    @tool(name=f"{name}_conclusive")
    async def conclusive_agent(request: str) -> str:
        """Agent wrapper that always provides conclusive answers."""
        
        # Process request through existing agent
        result = await agent.process_request({"query": request})
        
        # CRITICAL: Never return just source lists - always synthesize answer
        if isinstance(result, dict) and "sources" in result:
            if len(result["sources"]) > 0:
                answer = synthesize_answer_from_sources(request, result["sources"])
                return f"CONCLUSIVE ANSWER: {answer}"
            else:
                return f"CONCLUSIVE ANSWER: No information found for '{request}'"
        
        # For other result types, ensure it's conclusive
        if isinstance(result, str) and len(result.strip()) > 0:
            return f"CONCLUSIVE ANSWER: {result}"
        
        return f"CONCLUSIVE ANSWER: Unable to process request '{request}'"
    
    return conclusive_agent
```

### PHI Detection integration with medical content awareness

```python
from src.healthcare_mcp.phi_detection import sanitize_for_compliance

def sanitize_medical_request(request_data: dict) -> dict:
    """HIPAA-compliant sanitization that preserves medical terminology."""
    return sanitize_for_compliance(request_data)

# Medical query validation - distinguish between PHI and medical terminology
def is_medical_terminology(text: str) -> bool:
    """Determine if text contains medical terminology vs PHI."""
    medical_terms = [
        "cardiovascular", "diabetes", "hypertension", "oncology", 
        "neurology", "cardiology", "symptoms", "treatment", "diagnosis",
        "medication", "therapy", "syndrome", "disease", "condition"
    ]
    
    # Medical terminology should pass PHI detection
    return any(term in text.lower() for term in medical_terms)

def enhanced_phi_detection(content: dict) -> dict:
    """Enhanced PHI detection that preserves medical queries."""
    
    text = content.get("content", "")
    
    # Skip PHI detection for medical terminology
    if is_medical_terminology(text):
        return {"sanitized": False, "content": content}
    
    # Apply normal PHI detection for actual personal data
    return sanitize_for_compliance(content)
```

## Medical Query Processing Patterns

### Comprehensive Medical Search Strategy

```python
# Multi-source medical research with proper data parsing
async def comprehensive_medical_search(query: str, mcp_client: DirectMCPClient) -> dict:
    """Comprehensive medical search across all available sources."""
    
    results = {
        "pubmed_articles": [],
        "clinical_trials": [],
        "drug_information": [],
        "search_metadata": {}
    }
    
    # 1. PubMed search (primary source)
    pubmed_result = await mcp_client.call_tool("search-pubmed", {"query": query})
    results["pubmed_articles"] = parse_mcp_response(pubmed_result, "articles")
    
    # 2. Clinical trials (if drug/treatment related)
    if any(term in query.lower() for term in ["treatment", "therapy", "drug", "medication"]):
        trials_result = await mcp_client.call_tool("search-trials", {"query": query})
        results["clinical_trials"] = parse_mcp_response(trials_result, "results")
    
    # 3. Drug information (if drug-specific)
    if any(term in query.lower() for term in ["drug", "medication", "pharmaceutical"]):
        drug_result = await mcp_client.call_tool("get-drug-info", {"query": query})
        results["drug_information"] = parse_mcp_response(drug_result, "results")
    
    # Add search metadata for transparency
    results["search_metadata"] = {
        "query": query,
        "sources_searched": ["PubMed", "Clinical Trials", "FDA Drug Info"],
        "total_results": len(results["pubmed_articles"]) + len(results["clinical_trials"]) + len(results["drug_information"]),
        "search_timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    return results

# Medical answer synthesis from multiple sources
def synthesize_comprehensive_medical_answer(query: str, search_results: dict) -> str:
    """Synthesize medical answer from multiple sources."""
    
    answer_sections = []
    
    # PubMed literature findings
    if search_results["pubmed_articles"]:
        literature_summary = summarize_literature(search_results["pubmed_articles"][:3])
        answer_sections.append(f"**Research Literature:**\n{literature_summary}")
    
    # Clinical trial findings
    if search_results["clinical_trials"]:
        trial_summary = summarize_trials(search_results["clinical_trials"][:2])
        answer_sections.append(f"**Clinical Trials:**\n{trial_summary}")
    
    # Drug information
    if search_results["drug_information"]:
        drug_summary = summarize_drug_info(search_results["drug_information"][:1])
        answer_sections.append(f"**Drug Information:**\n{drug_summary}")
    
    # Combine all sections
    comprehensive_answer = "\n\n".join(answer_sections)
    
    # Add medical disclaimer and metadata
    comprehensive_answer += f"\n\n**Medical Disclaimer:** This information is for educational purposes only and should not replace professional medical advice.\n\n**Search Metadata:** {search_results['search_metadata']['total_results']} results from {len(search_results['search_metadata']['sources_searched'])} sources."
    
    return comprehensive_answer
```

### Error Handling and Fallback Patterns

```python
# Robust error handling for medical queries
async def robust_medical_query(query: str, mcp_client: DirectMCPClient) -> dict:
    """Medical query with comprehensive error handling."""
    
    try:
        # Attempt comprehensive search
        result = await comprehensive_medical_search(query, mcp_client)
        
        if result["search_metadata"]["total_results"] > 0:
            return {
                "status": "success",
                "answer": synthesize_comprehensive_medical_answer(query, result),
                "sources": result
            }
        else:
            # No results found
            return {
                "status": "no_results", 
                "answer": f"No medical literature found for '{query}'. Consider rephrasing your query or consulting a healthcare professional.",
                "sources": {}
            }
            
    except Exception as e:
        logger.error(f"Medical query failed for '{query}': {e}")
        
        # Fallback to database-only search
        try:
            fallback_result = await investigate_data_source(query, mcp_client)
            if fallback_result.get("article_count", 0) > 0:
                return {
                    "status": "fallback_success",
                    "answer": f"Found {fallback_result['article_count']} articles in local database. Medical tools temporarily limited.",
                    "sources": fallback_result
                }
        except Exception as fallback_error:
            logger.error(f"Fallback search also failed: {fallback_error}")
        
        # Final fallback
        return {
            "status": "error",
            "answer": "Medical information services are temporarily unavailable. Please consult a healthcare professional for medical questions.",
            "sources": {},
            "error": str(e)
        }
```

---

**CRITICAL REMINDERS for Healthcare Development:**

1. **MCP Response Structure**: All MCP tools return nested JSON structure `{"content": [{"type": "text", "text": "JSON_STRING"}]}` - must parse the JSON_STRING to get actual data
2. **Agent Iteration Control**: Agents must provide conclusive answers, not just source lists, to prevent LangChain iteration loops
3. **Database vs API Investigation**: Use response time and result patterns to determine data source reliability
4. **Medical Query Synthesis**: Convert article lists into actual answers with medical disclaimers
5. **PHI Detection Balance**: Preserve medical terminology while blocking actual personal health information
6. **Container Architecture**: MCP tools only available inside healthcare-api container, not from host environment
7. **Agent Adapter Pattern**: Thin wrappers preserve existing agent functionality and logging
8. **Error Handling**: Comprehensive fallbacks for medical query reliability
9. **Medical Disclaimers**: Always include appropriate disclaimers for medical information
10. **Session Caching**: Prevent duplicate tool calls within same session to improve performance

Last Updated: 2025-01-15 | Enhanced with critical debugging patterns and data structure handling
```
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
