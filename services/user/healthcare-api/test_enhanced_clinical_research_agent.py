"""
Comprehensive test suite for the Enhanced Clinical Research Agent

Tests conversational synthesis, state management, and orchestrator integration.
"""

import asyncio
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from agents.clinical_research_agent.clinical_research_agent import ClinicalResearchAgent


class TestEnhancedClinicalResearchAgent:
    """Test suite for enhanced clinical research agent functionality"""

    @pytest.fixture
    def mock_mcp_client(self):
        """Mock MCP client for testing"""
        client = AsyncMock()
        client.call_tool = AsyncMock()
        return client

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client for testing"""
        client = AsyncMock()
        client.generate = AsyncMock()
        client.chat = AsyncMock()
        return client

    @pytest.fixture
    def mock_query_engine(self):
        """Mock query engine"""
        from unittest.mock import MagicMock
        engine = MagicMock()
        engine.process_medical_query = AsyncMock()
        return engine

    @pytest.fixture
    def mock_reasoning_engine(self):
        """Mock reasoning engine"""
        from unittest.mock import MagicMock
        reasoning = MagicMock()
        reasoning.reason_with_dynamic_knowledge = AsyncMock()
        
        # Mock reasoning result
        result = MagicMock()
        result.reasoning_type = "comprehensive_research"
        result.steps = []
        result.final_assessment = "Test clinical assessment"
        result.confidence_score = 0.85
        result.clinical_recommendations = ["Test recommendation"]
        result.evidence_sources = []
        result.disclaimers = ["Test disclaimer"]
        result.generated_at = datetime.utcnow()
        
        reasoning.reason_with_dynamic_knowledge.return_value = result
        return reasoning

    @pytest.fixture
    def clinical_research_agent(self, mock_mcp_client, mock_llm_client):
        """Create clinical research agent instance with mocked dependencies"""
        with patch('agents.clinical_research_agent.clinical_research_agent.EnhancedMedicalQueryEngine'), \
             patch('agents.clinical_research_agent.clinical_research_agent.EnhancedMedicalReasoning'):
            
            agent = ClinicalResearchAgent(
                mcp_client=mock_mcp_client,
                llm_client=mock_llm_client,
                config_override={
                    "max_steps": 10,
                    "max_iterations": 2,
                    "timeout_seconds": 30,
                    "llm_settings": {"temperature": 0.2, "max_tokens": 1000}
                }
            )
            return agent

    @pytest.mark.asyncio
    async def test_conversation_state_management(self, clinical_research_agent):
        """Test conversation memory and state management"""
        agent = clinical_research_agent
        session_id = "test_session_001"
        
        # Test conversation context tracking
        query1 = "Tell me about diabetes treatment"
        context1 = agent._get_conversation_context(session_id)
        assert context1["conversation_depth"] == 0
        
        # Simulate adding conversation memory
        await agent._update_conversation_state(
            session_id,
            query1,
            {"sources": [{"title": "Diabetes Study 1", "doi": "10.1234/test1"}]}
        )
        
        # Check updated context
        context2 = agent._get_conversation_context(session_id)
        assert context2["conversation_depth"] == 1
        assert len(context2["previous_queries"]) == 1
        assert context2["available_sources"] == 1

    @pytest.mark.asyncio
    async def test_source_deduplication(self, clinical_research_agent):
        """Test source deduplication functionality"""
        agent = clinical_research_agent
        session_id = "test_session_002"
        
        # Test duplicate detection
        source1 = {"title": "Diabetes Treatment Review", "doi": "10.1234/test1", "url": "http://example.com/1"}
        source2 = {"title": "Diabetes Treatment Review", "doi": "10.1234/test1", "url": "http://example.com/1"}
        source3 = {"title": "Different Study", "doi": "10.1234/test2", "url": "http://example.com/2"}
        
        cached_sources = [source1]
        
        assert agent._is_duplicate_source(source2, cached_sources) == True
        assert agent._is_duplicate_source(source3, cached_sources) == False

    @pytest.mark.asyncio
    async def test_query_enhancement_with_context(self, clinical_research_agent):
        """Test query enhancement for follow-up questions"""
        agent = clinical_research_agent
        session_id = "test_session_003"
        
        # Mock LLM response for query enhancement
        agent.llm_client.generate.return_value = {
            "response": "diabetes treatment complications management side effects"
        }
        
        # Set up conversation context
        agent._conversation_memory[session_id] = {
            "queries": [{"query": "diabetes treatment", "topics": ["condition:diabetes", "treatment:medication"]}],
            "last_updated": datetime.utcnow().isoformat()
        }
        agent._topic_history[session_id] = ["condition:diabetes", "treatment:medication"]
        
        # Test query enhancement
        original_query = "what about side effects"
        enhanced_query = await agent._enhance_query_with_context(original_query, session_id)
        
        # Should be enhanced for follow-up context
        assert len(enhanced_query) >= len(original_query)

    @pytest.mark.asyncio
    async def test_conversational_synthesis(self, clinical_research_agent):
        """Test conversational response synthesis"""
        agent = clinical_research_agent
        
        # Mock LLM response for synthesis
        agent.llm_client.generate.return_value = {
            "response": """## Research Summary

Based on current evidence, diabetes treatment involves multiple approaches including:

- **Medication Management**: Metformin remains first-line therapy
- **Lifestyle Interventions**: Diet and exercise show significant benefits
- **Monitoring**: Regular HbA1c monitoring is essential

The evidence suggests a comprehensive approach yields the best outcomes."""
        }
        
        # Mock research stages with sample data
        research_stages = [
            {
                "success": True,
                "stage": "pubmed_search",
                "result": {
                    "articles": [
                        {
                            "title": "Metformin in Type 2 Diabetes",
                            "authors": ["Smith, J.", "Doe, A."],
                            "journal": "Diabetes Care",
                            "publication_date": "2024",
                            "abstract": "Metformin shows excellent efficacy in diabetes management..."
                        }
                    ]
                }
            }
        ]
        
        # Mock reasoning result
        reasoning_result = MagicMock()
        reasoning_result.final_assessment = "Comprehensive diabetes management is essential"
        reasoning_result.confidence_score = 0.9
        reasoning_result.generated_at = datetime.utcnow()
        
        # Test synthesis
        with patch('agents.clinical_research_agent.clinical_research_agent.parse_pubmed_response') as mock_parser:
            mock_parser.return_value = research_stages[0]["result"]["articles"]
            
            result = await agent._synthesize_research_findings(
                "diabetes treatment",
                research_stages,
                reasoning_result
            )
            
            assert "Research Summary" in result
            assert "Medication Management" in result
            assert len(result) > 100  # Should be substantial

    @pytest.mark.asyncio
    async def test_orchestrator_compatibility(self, clinical_research_agent):
        """Test compatibility with LangChain orchestrator"""
        agent = clinical_research_agent
        
        # Mock dependencies
        agent.llm_client.generate.return_value = {"response": "Test synthesis"}
        agent.mcp_client.call_tool.return_value = {"articles": []}
        
        # Mock reasoning result
        reasoning_result = MagicMock()
        reasoning_result.reasoning_type = "comprehensive_research"
        reasoning_result.steps = []
        reasoning_result.final_assessment = "Test assessment"
        reasoning_result.confidence_score = 0.8
        reasoning_result.clinical_recommendations = []
        reasoning_result.evidence_sources = []
        reasoning_result.disclaimers = []
        reasoning_result.generated_at = datetime.utcnow()
        
        agent.medical_reasoning.reason_with_dynamic_knowledge.return_value = reasoning_result
        
        # Test process_research_query method (orchestrator entry point)
        result = await agent.process_research_query(
            query="test medical query",
            user_id="test_user",
            session_id="test_session"
        )
        
        # Check orchestrator-expected format
        assert result["status"] == "success"
        assert "research_results" in result
        assert "formatted_summary" in result["research_results"]
        assert "disclaimers" in result
        assert result["agent_type"] == "clinical_research"

    @pytest.mark.asyncio
    async def test_topic_extraction(self, clinical_research_agent):
        """Test medical topic extraction from queries"""
        agent = clinical_research_agent
        
        # Test various query types
        queries_and_topics = [
            ("diabetes treatment with metformin", ["condition:diabetes", "treatment:treatment", "treatment:medication"]),
            ("cancer research studies", ["condition:cancer", "research:research", "research:study"]),
            ("hypertension medication side effects", ["condition:hypertension", "treatment:medication"]),
        ]
        
        for query, expected_topics in queries_and_topics:
            topics = agent._extract_topics_from_query(query)
            # Check that at least some expected topics are found
            topic_match = any(topic in topics for topic in expected_topics)
            assert topic_match, f"No expected topics found for query: {query}"

    def test_agent_capabilities(self, clinical_research_agent):
        """Test agent capability reporting"""
        agent = clinical_research_agent
        capabilities = agent.get_agent_capabilities()
        
        assert capabilities["agent_name"] == "clinical_research"
        assert "comprehensive_medical_research" in capabilities["capabilities"]
        assert "conversation_support" in capabilities
        assert capabilities["conversation_support"] is True
        assert capabilities["phi_compliant"] is True

    @pytest.mark.asyncio
    async def test_health_check(self, clinical_research_agent):
        """Test agent health check functionality"""
        agent = clinical_research_agent
        health = await agent.health_check()
        
        assert health["agent_name"] == "clinical_research"
        assert health["status"] in ["healthy", "unhealthy"]
        assert "mcp_client" in health
        assert "memory_status" in health
        assert "capabilities" in health

    @pytest.mark.asyncio
    async def test_error_handling(self, clinical_research_agent):
        """Test error handling and graceful degradation"""
        agent = clinical_research_agent
        
        # Mock MCP client failure
        agent.mcp_client.call_tool.side_effect = Exception("MCP connection failed")
        agent.llm_client.generate.return_value = {"response": "Fallback response"}
        
        # Mock reasoning result for error case
        reasoning_result = MagicMock()
        reasoning_result.reasoning_type = "error_handling"
        reasoning_result.steps = []
        reasoning_result.final_assessment = "Error occurred during processing"
        reasoning_result.confidence_score = 0.1
        reasoning_result.clinical_recommendations = []
        reasoning_result.evidence_sources = []
        reasoning_result.disclaimers = ["Error occurred"]
        reasoning_result.generated_at = datetime.utcnow()
        
        agent.medical_reasoning.reason_with_dynamic_knowledge.return_value = reasoning_result
        
        # Should handle errors gracefully
        result = await agent.process_research_query(
            query="test query",
            user_id="test_user",
            session_id="test_session"
        )
        
        # Should return structured error response
        assert "status" in result
        # Error responses may have status "error" or still "success" with error info

    @pytest.mark.asyncio
    async def test_memory_management(self, clinical_research_agent):
        """Test conversation memory limits and cleanup"""
        agent = clinical_research_agent
        session_id = "memory_test_session"
        
        # Add many queries to test memory limits
        for i in range(15):  # More than the 10-query limit
            await agent._update_conversation_state(
                session_id,
                f"Query {i}",
                {"sources": [{"title": f"Source {i}"}]}
            )
        
        # Check memory limits are enforced
        memory = agent._conversation_memory[session_id]
        assert len(memory["queries"]) <= 10  # Should be limited to 10
        
        # Check source cache limits
        source_cache_key = f"{session_id}_sources"
        if source_cache_key in agent._source_cache:
            assert len(agent._source_cache[source_cache_key]["sources"]) <= 50


if __name__ == "__main__":
    # Run tests with asyncio
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--run":
        # Simple test runner for development
        async def run_basic_tests():
            print("Running basic clinical research agent tests...")
            
            # Mock clients for basic testing
            mock_mcp = AsyncMock()
            mock_llm = AsyncMock()
            mock_llm.generate.return_value = {"response": "Test response"}
            
            with patch('agents.clinical_research_agent.clinical_research_agent.EnhancedMedicalQueryEngine'), \
                 patch('agents.clinical_research_agent.clinical_research_agent.EnhancedMedicalReasoning'):
                
                agent = ClinicalResearchAgent(mock_mcp, mock_llm)
                
                # Test basic functionality
                capabilities = agent.get_agent_capabilities()
                print(f"✓ Agent capabilities: {len(capabilities['capabilities'])} capabilities")
                
                health = await agent.health_check()
                print(f"✓ Health check: {health['status']}")
                
                # Test conversation state
                session_id = "test_session"
                context = agent._get_conversation_context(session_id)
                print(f"✓ Initial context depth: {context['conversation_depth']}")
                
                await agent._update_conversation_state(
                    session_id, 
                    "test query", 
                    {"sources": [{"title": "Test"}]}
                )
                
                updated_context = agent._get_conversation_context(session_id)
                print(f"✓ Updated context depth: {updated_context['conversation_depth']}")
                
                print("All basic tests passed!")
        
        asyncio.run(run_basic_tests())
    else:
        print("Run with --run flag to execute basic tests, or use pytest for full test suite")
        print("Example: python test_enhanced_clinical_research_agent.py --run")
        print("Or: pytest test_enhanced_clinical_research_agent.py -v")