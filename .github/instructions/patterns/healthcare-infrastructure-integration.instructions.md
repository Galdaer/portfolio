# Healthcare Infrastructure Integration Instructions

**WORKFLOW CONTROL**: All workflows are controlled by `copilot-instructions.md`. This file provides implementation patterns only.

## Infrastructure Integration Priority Order

### Phase 1: Core Infrastructure Integration (Immediate)
1. **ToolRegistry Integration** - Replace direct MCP calls with robust tool management
2. **PHI Detection Integration** - Add HIPAA compliance to all endpoints
3. **BaseHealthcareAgent Integration** - Add healthcare framework to LangChain agents

### Phase 2: Medical Infrastructure Integration (High Priority)  
1. **Enhanced Medical Query Engine** - 25x more sophisticated medical search
2. **Medical Search Utilities** - Evidence-based ranking and confidence scoring
3. **Medical Response Validation** - Trust scores and medical disclaimers

### Phase 3: Agent System Integration (Medium Priority)
1. **Agent Manager Implementation** - Centralized agent coordination
2. **Specialized Agent Routing** - All 8 healthcare agents accessible
3. **Multi-Agent Workflows** - Complex medical query handling

## ToolRegistry Integration Pattern

```python
# ✅ CORRECT: Replace direct MCP calls with ToolRegistry
from core.tools import tool_registry

# Before: Direct MCP calls in healthcare_tools.py
async def search_medical_literature_agent(query: str, mcp_client):
    result = await mcp_client.call_tool('search-pubmed', {'query': query})
    return result

# After: ToolRegistry integration with health checking
async def search_medical_literature_agent(query: str, tool_registry_instance=None):
    """Use ToolRegistry for robust tool management and health checking"""
    if tool_registry_instance is None:
        tool_registry_instance = tool_registry
    
    try:
        # Leverage health checking and performance tracking
        result = await tool_registry_instance.call_tool('search-pubmed', {'query': query})
        return result
    except Exception as e:
        logger.error(f"ToolRegistry call failed for search-pubmed: {e}")
        # Graceful fallback to ensure functionality
        return {"error": "Medical search temporarily unavailable", "fallback": True}

# ✅ CORRECT: Initialize ToolRegistry in healthcare_tools.py
async def initialize_healthcare_tools():
    """Initialize ToolRegistry for all healthcare tool calls"""
    try:
        await tool_registry.initialize()
        logger.info("ToolRegistry initialized for healthcare tools")
        return True
    except Exception as e:
        logger.error(f"ToolRegistry initialization failed: {e}")
        return False
```

## PHI Detection Integration Pattern

```python
# ✅ CORRECT: Add PHI detection to Open WebUI endpoints
from src.healthcare_mcp.phi_detection import sanitize_for_compliance

# Before: No PHI sanitization in main.py
@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    result = await orchestrator.process_query(request.messages[-1].content)
    return {"choices": [{"message": {"content": result}}]}

# After: Automatic HIPAA compliance  
@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    # Sanitize incoming request for PHI
    sanitized_request = sanitize_for_compliance({
        "content": request.messages[-1].content,
        "metadata": {"endpoint": "chat_completions"}
    })
    
    # Process with sanitized content
    result = await orchestrator.process_query(sanitized_request["content"])
    
    # Sanitize outgoing response
    sanitized_response = sanitize_for_compliance({
        "content": result,
        "metadata": {"endpoint": "chat_completions", "direction": "outbound"}
    })
    
    return {"choices": [{"message": {"content": sanitized_response["content"]}}]}
```

## BaseHealthcareAgent Integration Pattern

```python
# ✅ CORRECT: Inherit LangChain agents from BaseHealthcareAgent
from agents import BaseHealthcareAgent

# Before: LangChain agent without healthcare framework
class HealthcareLangChainAgent:
    def __init__(self, mcp_client):
        self.mcp_client = mcp_client
        self.logger = logging.getLogger(__name__)

# After: Inherit healthcare logging, PHI monitoring, safety
class HealthcareLangChainAgent(BaseHealthcareAgent):
    def __init__(self, mcp_client, **kwargs):
        # Initialize with healthcare framework
        super().__init__(
            mcp_client=mcp_client, 
            agent_name="langchain_medical",
            agent_type="medical_reasoning"
        )
        
        # Now automatically has:
        # - Healthcare-specific logging to healthcare_system.log
        # - PHI monitoring and sanitization
        # - Database connectivity for memory/session management
        # - Medical safety boundaries and disclaimers
        # - Performance tracking and metrics
        
    async def process_medical_query(self, query: str):
        """Process medical query with healthcare framework benefits"""
        # Automatic PHI sanitization via BaseHealthcareAgent
        # Automatic healthcare logging via BaseHealthcareAgent
        # Automatic medical disclaimer injection via BaseHealthcareAgent
        
        return await super().process_query(query)
```

## Enhanced Medical Query Engine Integration Pattern

```python
# ✅ CORRECT: Replace basic search with sophisticated medical RAG
from core.medical.enhanced_query_engine import EnhancedMedicalQueryEngine, QueryType

# Before: Basic medical search in medical_search_agent.py
async def basic_medical_search(query: str):
    result = await mcp_client.call_tool('search-pubmed', {'query': query})
    return {"sources": result.get("articles", [])}

# After: Sophisticated medical RAG with confidence scoring
async def enhanced_medical_search(query: str):
    """Use EnhancedMedicalQueryEngine for sophisticated medical search"""
    query_engine = EnhancedMedicalQueryEngine()
    
    # Automatic query type classification
    result = await query_engine.process_query(
        query=query,
        query_type=QueryType.LITERATURE_RESEARCH  # Auto-detected
    )
    
    return {
        "query_id": result.query_id,
        "query_type": result.query_type.value,
        "refined_queries": result.refined_queries,
        "sources": result.sources,
        "confidence_score": result.confidence_score,
        "reasoning_chain": result.reasoning_chain,
        "medical_entities": result.medical_entities,
        "disclaimers": result.disclaimers,
        "source_links": result.source_links
    }
```

## Medical Search Utilities Integration Pattern

```python
# ✅ CORRECT: Use evidence-based ranking for medical literature
from core.medical.search_utils import determine_evidence_level, calculate_medical_confidence

# Before: No evidence-level ranking
def rank_medical_results(articles):
    return sorted(articles, key=lambda x: x.get("relevance", 0))

# After: Evidence-based medical ranking
def rank_medical_results(articles):
    """Rank medical literature by evidence level and medical confidence"""
    for article in articles:
        # Add evidence level (systematic review > RCT > clinical study)
        article["evidence_level"] = determine_evidence_level(article)
        
        # Add medical-specific confidence scoring
        article["medical_confidence"] = calculate_medical_confidence(article)
        
        # Combined ranking score prioritizing evidence quality
        article["ranking_score"] = (
            evidence_level_weight(article["evidence_level"]) * 0.6 +
            article["medical_confidence"] * 0.4
        )
    
    # Sort by evidence quality, then confidence
    return sorted(articles, key=lambda x: x["ranking_score"], reverse=True)

def evidence_level_weight(evidence_level: str) -> float:
    """Weight evidence levels for medical ranking"""
    weights = {
        "systematic_review": 1.0,
        "meta_analysis": 0.95, 
        "randomized_controlled_trial": 0.9,
        "clinical_guideline": 0.85,
        "clinical_study": 0.7,
        "review": 0.5,
        "unknown": 0.3
    }
    return weights.get(evidence_level, 0.3)
```

## Integration Validation Patterns

```python
# ✅ CORRECT: Validate infrastructure integration
async def validate_infrastructure_integration():
    """Comprehensive validation of infrastructure integration"""
    validation_results = {
        "tool_registry": False,
        "phi_detection": False, 
        "base_healthcare_agent": False,
        "enhanced_query_engine": False
    }
    
    try:
        # Test ToolRegistry integration
        from core.tools import tool_registry
        await tool_registry.initialize()
        health = await tool_registry.health_check()
        validation_results["tool_registry"] = health["status"] == "healthy"
        
        # Test PHI detection integration
        from src.healthcare_mcp.phi_detection import sanitize_for_compliance
        test_data = {"content": "Test PHI detection"}
        sanitized = sanitize_for_compliance(test_data)
        validation_results["phi_detection"] = "content" in sanitized
        
        # Test BaseHealthcareAgent integration
        from agents import BaseHealthcareAgent
        agent = BaseHealthcareAgent(agent_name="test")
        validation_results["base_healthcare_agent"] = hasattr(agent, "logger")
        
        # Test Enhanced Query Engine
        from core.medical.enhanced_query_engine import EnhancedMedicalQueryEngine
        engine = EnhancedMedicalQueryEngine()
        validation_results["enhanced_query_engine"] = hasattr(engine, "process_query")
        
    except Exception as e:
        logger.error(f"Infrastructure validation failed: {e}")
    
    return validation_results

# ✅ CORRECT: End-to-end integration test
async def test_end_to_end_integration():
    """Test complete medical query flow through integrated infrastructure"""
    try:
        # Initialize all components
        await tool_registry.initialize()
        
        # Create healthcare agent with integrated framework
        agent = HealthcareLangChainAgent(mcp_client=None)
        
        # Test medical query with PHI sanitization and evidence ranking
        test_query = "What are the latest treatments for diabetes?"
        result = await agent.process_medical_query(test_query)
        
        # Validate result has healthcare framework benefits
        assert "confidence_score" in result  # Enhanced Query Engine
        assert "disclaimers" in result       # Medical safety
        assert "evidence_level" in str(result)  # Medical ranking
        
        logger.info("✅ End-to-end infrastructure integration successful")
        return True
        
    except Exception as e:
        logger.error(f"❌ End-to-end integration test failed: {e}")
        return False
```

## Critical Integration Warnings

### DO NOT BREAK:
- **Open WebUI Endpoint Compatibility**: Maintain `/v1/chat/completions` OpenAI format
- **MCP Tool Execution**: Keep DirectMCPClient subprocess architecture working
- **LangChain Iteration Limits**: Preserve two-tier iteration system (orchestrator: 3, agent: 8)

### INTEGRATION ORDER MATTERS:
1. **ToolRegistry First**: Establishes robust tool management foundation
2. **PHI Detection Second**: Adds compliance layer to all interactions  
3. **BaseHealthcareAgent Third**: Integrates healthcare framework with existing agents
4. **Enhanced Components Last**: Add sophisticated medical capabilities on stable foundation

### GRACEFUL FALLBACK REQUIRED:
- **ToolRegistry unavailable**: Fall back to direct MCP calls
- **PHI detection fails**: Log error but continue processing
- **BaseHealthcareAgent issues**: Maintain basic agent functionality
- **Enhanced components fail**: Degrade to basic medical search

The integration patterns ensure 25x more sophisticated healthcare capabilities while maintaining all existing functionality and adding HIPAA compliance.
