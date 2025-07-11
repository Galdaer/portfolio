"""
Foundation tests for Intelluxe AI Phase 0

Tests basic functionality of core components to ensure
Phase 0 setup is ready for Phase 1 development.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch

# Test configuration loading
def test_config_loading():
    """Test that configuration loads correctly"""
    from config.app import config
    
    assert config.project_name == "intelluxe-ai"
    assert config.version == "1.0.0"
    assert config.port == 8000


# Test core component initialization (mocked)
@pytest.mark.asyncio
async def test_memory_manager_initialization():
    """Test memory manager can be initialized"""
    from core.memory import MemoryManager
    
    # Mock the actual connections for testing
    with patch('redis.asyncio.from_url') as mock_redis, \
         patch('asyncpg.create_pool') as mock_postgres:
        
        mock_redis.return_value.ping = AsyncMock()
        mock_postgres.return_value = AsyncMock()
        
        memory_manager = MemoryManager()
        await memory_manager.initialize()
        
        assert memory_manager._initialized is True
        await memory_manager.close()


@pytest.mark.asyncio
async def test_model_registry_initialization():
    """Test model registry can be initialized"""
    from core.models import ModelRegistry
    
    # Mock the HTTP client for testing
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": []}
        mock_client.return_value.get = AsyncMock(return_value=mock_response)
        
        model_registry = ModelRegistry()
        await model_registry.initialize()
        
        assert model_registry._initialized is True
        await model_registry.close()


@pytest.mark.asyncio
async def test_tool_registry_initialization():
    """Test tool registry can be initialized"""
    from core.tools import ToolRegistry
    
    # Mock the HTTP client for testing
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"tools": []}
        mock_client.return_value.get = AsyncMock(return_value=mock_response)
        
        tool_registry = ToolRegistry()
        await tool_registry.initialize()
        
        assert tool_registry._initialized is True
        await tool_registry.close()


# Test agent base class functionality
@pytest.mark.asyncio
async def test_base_agent_safety_boundaries():
    """Test that safety boundaries are enforced"""
    from agents import BaseHealthcareAgent
    
    class TestAgent(BaseHealthcareAgent):
        def __init__(self):
            super().__init__("test_agent", "test")
        
        async def _process_implementation(self, request):
            return {"success": True, "message": "Test response"}
    
    agent = TestAgent()
    
    # Test safe request
    safe_request = {"message": "Help me organize my documents"}
    safety_check = await agent._check_safety_boundaries(safe_request)
    assert safety_check["safe"] is True
    
    # Test unsafe request (medical advice)
    unsafe_request = {"message": "What medication should I take for my headache?"}
    safety_check = await agent._check_safety_boundaries(unsafe_request)
    assert safety_check["safe"] is False
    assert "cannot provide medical advice" in safety_check["message"].lower()


def test_agent_templates_exist():
    """Test that agent templates are available"""
    from agents import document_agent, research_agent
    
    assert document_agent.agent_name == "document_processor"
    assert research_agent.agent_name == "research_assistant"


# Test directory structure exists
def test_phase0_directory_structure():
    """Test that Phase 0 directories exist"""
    import os
    
    base_dirs = [
        "agents", "core", "data", "infrastructure", 
        "notebooks", "config", "tests"
    ]
    
    for directory in base_dirs:
        assert os.path.exists(directory), f"Directory {directory} should exist"
    
    # Test agent subdirectories
    agent_dirs = [
        "agents/intake", "agents/document_processor", 
        "agents/research_assistant", "agents/billing_helper", 
        "agents/scheduling_optimizer"
    ]
    
    for directory in agent_dirs:
        assert os.path.exists(directory), f"Agent directory {directory} should exist"


def test_gitignore_includes_ai_directories():
    """Test that .gitignore properly includes AI application directories"""
    with open('.gitignore', 'r') as f:
        gitignore_content = f.read()
    
    # Check that AI directories are whitelisted
    required_entries = [
        "!/agents/", "!/core/", "!/data/", "!/config/",
        "!/main.py", "!*.py", "!/.env.example"
    ]
    
    for entry in required_entries:
        assert entry in gitignore_content, f"GitIgnore should include {entry}"


if __name__ == "__main__":
    # Run tests manually if needed
    pytest.main([__file__, "-v"])
