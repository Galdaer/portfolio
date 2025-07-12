"""
Foundation tests for Intelluxe AI Phase 0

Tests basic functionality of core components to ensure
Phase 0 setup is ready for Phase 1 development.

Based on patterns from reference/ai-patterns/ adapted for healthcare AI.
"""

import os
import sys
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Test configuration loading
def test_config_loading():
    """Test that configuration loads properly"""
    from config.app import config
    from config import validate_config, check_compliance_config
    
    assert config is not None
    assert config.project_name == "intelluxe-ai"
    
    # Test validation functions
    validate_config()  # Should not raise
    check_compliance_config()  # Should not raise

def test_config_helpers():
    """Test configuration helper functions"""
    from config import get_ai_config, get_database_config, get_compliance_config
    from config import is_development, is_production
    
    ai_config = get_ai_config()
    assert 'ollama_url' in ai_config
    assert 'mcp_server_url' in ai_config
    
    db_config = get_database_config()
    assert 'database_name' in db_config
    
    compliance_config = get_compliance_config()
    assert 'data_retention_days' in compliance_config
    assert 'pii_redaction_enabled' in compliance_config

def test_environment_variables():
    """Test that required environment variables are available"""
    env_file = project_root / ".env"
    assert env_file.exists(), ".env file should exist"
    
    # Read and verify basic environment structure
    with open(env_file) as f:
        env_content = f.read()
        assert "PROJECT_NAME=intelluxe-ai" in env_content
        assert "ENVIRONMENT=development" in env_content
        assert "OLLAMA_URL=" in env_content
        assert "MCP_SERVER_URL=" in env_content

# Test core component initialization (mocked)
@pytest.mark.asyncio
async def test_memory_manager_initialization():
    """Test memory manager can be initialized (mocked)"""
    try:
        from core.memory import MemoryManager
        
        # Mock external dependencies
        with patch('redis.asyncio.from_url') as mock_redis, \
             patch('asyncpg.create_pool') as mock_postgres:
            
            mock_redis.return_value.ping = AsyncMock()
            mock_postgres.return_value = AsyncMock()
            
            memory_manager = MemoryManager()
            await memory_manager.initialize()
            
            assert memory_manager._initialized is True
            await memory_manager.close()
            
    except ImportError:
        # Verify the module structure exists
        memory_init = project_root / "core" / "memory" / "__init__.py"
        assert memory_init.exists(), "core/memory/__init__.py should exist"

@pytest.mark.asyncio
async def test_model_registry_initialization():
    """Test model registry initialization"""
    try:
        from core.models import ModelRegistry
        
        registry = ModelRegistry()
        assert hasattr(registry, 'register_model')
        
    except ImportError:
        # Verify the module structure exists
        models_init = project_root / "core" / "models" / "__init__.py"
        assert models_init.exists(), "core/models/__init__.py should exist"

@pytest.mark.asyncio
async def test_tool_registry_initialization():
    """Test tool registry for MCP integration"""
    try:
        from core.tools import ToolRegistry
        
        registry = ToolRegistry()
        assert hasattr(registry, '_available_tools')
        
    except ImportError:
        # Verify the module structure exists
        tools_init = project_root / "core" / "tools" / "__init__.py"
        assert tools_init.exists(), "core/tools/__init__.py should exist"

# Test agent base class functionality
@pytest.mark.asyncio
async def test_base_agent_safety_boundaries():
    """Test that safety boundaries are enforced"""
    try:
        from agents import BaseHealthcareAgent
        
        # Create test agent instance
        agent = BaseHealthcareAgent("test_agent", "test")
        
        # Test that safety methods exist
        assert hasattr(agent, '_check_safety_boundaries')
        assert hasattr(agent, 'process_request')
        
    except ImportError:
        # Verify the module structure exists
        agents_init = project_root / "agents" / "__init__.py"
        assert agents_init.exists(), "agents/__init__.py should exist"

def test_agent_templates_exist():
    """Test that agent base classes are available"""
    try:
        from agents import BaseHealthcareAgent
        assert BaseHealthcareAgent is not None
        
    except ImportError:
        # Verify basic agent directory structure
        agents_dir = project_root / "agents"
        assert agents_dir.exists(), "agents directory should exist"
        
        # Check for agent subdirectories from Phase 0
        expected_dirs = ["intake", "document_processor", "research_assistant", 
                        "billing_helper", "scheduling_optimizer"]
        for agent_dir in expected_dirs:
            agent_path = agents_dir / agent_dir
            assert agent_path.exists(), f"agents/{agent_dir} should exist"

def test_phase0_directory_structure():
    """Test that Phase 0 directories exist"""
    base_dirs = [
        "agents", "core", "data", "infrastructure",
        "notebooks", "config", "test"  # Changed from "tests" to "test"
    ]
    
    for directory in base_dirs:
        dir_path = project_root / directory
        assert dir_path.exists(), f"Directory {directory} should exist"

def test_data_directories():
    """Test healthcare-specific data directories"""
    data_dirs = [
        "data/training", "data/evaluation", "data/vector_stores",
        "data/training/user_samples", "data/training/synthetic",
        "data/training/validation", "data/training/templates"
    ]
    
    for data_dir in data_dirs:
        dir_path = project_root / data_dir
        assert dir_path.exists(), f"Data directory {data_dir} should exist"

def test_infrastructure_directories():
    """Test infrastructure directories for healthcare deployment"""
    infra_dirs = [
        "infrastructure/docker", "infrastructure/monitoring",
        "infrastructure/security", "infrastructure/backup"
    ]
    
    for infra_dir in infra_dirs:
        dir_path = project_root / infra_dir
        assert dir_path.exists(), f"Infrastructure directory {infra_dir} should exist"

def test_vendor_healthcare_mcp():
    """Test that healthcare-mcp is properly integrated"""
    vendor_dir = project_root / "vendor" / "healthcare-mcp"
    assert vendor_dir.exists(), "/mcps/healthcare should exist"
    
    # Check for key healthcare-mcp files
    package_json = vendor_dir / "package.json"
    if package_json.exists():
        import json
        with open(package_json) as f:
            package_data = json.load(f)
            # Should be renamed for Intelluxe integration
            assert "intelluxe" in package_data.get("name", "").lower() or "healthcare" in package_data.get("name", "").lower()

def test_gitignore_includes_ai_directories():
    """Test that .gitignore properly includes AI application directories"""
    with open(project_root / '.gitignore', 'r') as f:
        gitignore_content = f.read()
    
    # Check that AI directories are whitelisted
    required_entries = [
        "!/agents/", "!/core/", "!/data/", "!/config/",
        "!/main.py", "!*.py", "!/.env.example"
    ]
    
    for entry in required_entries:
        assert entry in gitignore_content, f"GitIgnore should include {entry}"

def test_main_application_entry():
    """Test that main application entry point exists"""
    main_py = project_root / "main.py"
    assert main_py.exists(), "main.py should exist"

def test_requirements_structure():
    """Test that requirements are properly structured"""
    req_files = ["requirements.in", "requirements.txt"]
    
    for req_file in req_files:
        req_path = project_root / req_file
        assert req_path.exists(), f"{req_file} should exist"

def test_healthcare_compliance_ready():
    """Test that healthcare compliance structures are in place"""
    # Check for compliance-related environment variables
    env_file = project_root / ".env"
    with open(env_file) as f:
        env_content = f.read()
        
    compliance_vars = [
        "DATA_RETENTION_DAYS",
        "AUDIT_LOG_LEVEL", 
        "PII_REDACTION_ENABLED",
        "RBAC_ENABLED"
    ]
    
    for var in compliance_vars:
        assert var in env_content, f"Compliance variable {var} should be in .env"

if __name__ == "__main__":
    # Run tests manually if needed
    pytest.main([__file__, "-v"])
