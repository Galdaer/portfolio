# Phase 0: Project Planning and Setup

**Duration:** 1-2 days  
**Goal:** Lightweight project planning, directory structure, and environment setup. No infrastructure deployment - that happens in Phase 1.

## Overview

This phase covers basic project organization and development environment setup. Keep this minimal - the real work starts in Phase 1.

## 1. Project Structure and Environment Setup

### Directory Structure

The complete project structure for Intelluxe AI:

```
intelluxe-ai/
├── agents/                           # AI Agent implementations
│   ├── __init__.py                   # Base agent classes
│   ├── intake/                       # Patient intake agent
│   ├── document_processor/           # Medical document processing
│   ├── research_assistant/           # Medical research and literature
│   ├── billing_helper/               # Insurance and billing support
│   └── scheduling_optimizer/         # Appointment optimization
├── core/                             # Core infrastructure
│   ├── memory/                       # Memory management
│   │   ├── __init__.py              # Memory interfaces and base classes
│   │   ├── redis_manager.py         # Redis-based session management
│   │   └── postgres_manager.py      # PostgreSQL context storage
│   ├── orchestration/               # Agent coordination
│   │   ├── __init__.py
│   │   └── workflow_engine.py
│   ├── models/                      # Model registry and management
│   │   ├── __init__.py              # Model registry and adapter support
│   │   ├── ollama_client.py         # Ollama integration
│   │   └── fine_tuning/             # LoRA adapters (Phase 2+)
│   └── tools/                       # Tool registry and MCP integration
│       ├── __init__.py              # Tool registry
│       ├── mcp_client.py            # AgentCare-MCP integration
│       └── custom_tools/            # Custom medical tools
├── data/                            # Data management
│   ├── training/                    # Training data collection
│   │   ├── user_samples/            # Real user interactions (gitignored)
│   │   ├── synthetic/               # Synthetic training data
│   │   ├── validation/              # Validation datasets
│   │   └── templates/               # Response templates
│   ├── evaluation/                  # Model evaluation datasets
│   └── vector_stores/               # Vector embeddings (gitignored)
├── infrastructure/                  # Deployment and infrastructure
│   ├── docker/                      # Docker configurations
│   │   ├── docker-compose.yml       # Development stack
│   │   ├── docker-compose.prod.yml  # Production stack
│   │   └── Dockerfile               # Application container
│   ├── monitoring/                  # Health monitoring
│   │   ├── health_monitor.py        # Custom health checks
│   │   └── grafana/                 # Grafana dashboards
│   ├── security/                    # Security configurations
│   │   ├── ssl/                     # SSL certificates
│   │   └── rbac.yml                 # Role-based access control
│   └── backup/                      # Backup scripts and configs
├── services/user/                   # Service configurations
│   ├── ollama/                      # Ollama model serving
│   ├── agentcare-mcp/              # AgentCare MCP server
│   ├── postgres/                    # PostgreSQL with TimescaleDB
│   └── redis/                       # Redis session storage
├── notebooks/                       # Jupyter notebooks for development
│   ├── data_exploration.ipynb       # Data analysis and exploration
│   ├── model_evaluation.ipynb       # Model performance evaluation
│   └── training_pipeline.ipynb      # Fine-tuning experiments
├── tests/                          # Testing framework
│   ├── test_foundation.py          # Foundation component tests
│   ├── test_agents.py              # Agent functionality tests
│   ├── test_integration.py         # Cross-component integration
│   └── test_performance.py         # Load and performance tests
├── config/                         # Configuration management
│   ├── app.py                      # Main application configuration
│   ├── development.yml             # Development environment config
│   └── production.yml              # Production environment config
├── docs/                           # Documentation
│   ├── ARCHITECTURE.md             # System architecture
│   ├── DEVELOPMENT.md              # Development guide
│   ├── API.md                      # API documentation
│   └── DEPLOYMENT.md               # Deployment instructions
├── scripts/                        # Utility scripts
│   ├── universal-service-runner.sh # Service management (from intelluxe)
│   ├── clinic-bootstrap.sh           # Interactive setup (from intelluxe)
│   ├── setup-environment.sh        # Environment initialization
│   └── backup-data.sh              # Data backup automation
├── systemd/                        # Systemd service definitions
│   ├── intelluxe-api.service       # Main API service
│   ├── intelluxe-monitor.service   # Health monitoring service
│   └── intelluxe-backup.timer      # Automated backup timer
├── logs/                           # Application logs (gitignored)
├── main.py                         # Application entry point
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment template
├── .env                           # Environment variables (gitignored)
├── .gitignore                     # Git ignore rules
└── README.md                      # Project overview and quick start
```

### Environment Setup

Create the comprehensive project structure:

```bash
# Create main project directory
mkdir -p /opt/intelluxe/code/intelluxe-ai
cd /opt/intelluxe/code/intelluxe-ai

# Create comprehensive directory structure
mkdir -p {agents,core,data,infrastructure,notebooks,tests,config,docs,services/user,scripts,systemd,logs}

# Agent implementations
mkdir -p agents/{intake,document_processor,research_assistant,billing_helper,scheduling_optimizer}

# Core infrastructure components
mkdir -p core/{memory,orchestration,models,tools}

# Data management and training
mkdir -p data/{training,evaluation,vector_stores}
mkdir -p data/training/{user_samples,synthetic,validation,templates}

# Infrastructure and deployment
mkdir -p infrastructure/{docker,monitoring,security,backup}
mkdir -p services/user/{ollama,agentcare-mcp,postgres,redis}

# Initialize git repository with comprehensive .gitignore
git init
cat > .gitignore << EOF
# Environment and secrets
.env*
!.env.example

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.venv/
venv/
ENV/
env/

# Logs and data
logs/*
*.log
data/training/user_samples/*
data/vector_stores/*
!data/training/templates/
!data/evaluation/

# Models and checkpoints
*.pt
*.pth
*.safetensors
models/
adapters/

# Jupyter Notebooks
.ipynb_checkpoints

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Docker
.dockerignore
EOF
```

**Modern environment setup with UV (10-100x faster than pip):**
```bash
# Install UV package manager (much faster than pip)
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc  # Reload shell to use uv command

# Create virtual environment with UV
uv venv
source .venv/bin/activate

# Create requirements.in for dependency management
cat > requirements.in << EOF
# Core AI framework dependencies
langchain
langgraph
ragas[eval]

# Vector storage and retrieval
faiss-cpu
chromadb
qdrant-client

# Memory and state management
redis
psycopg2-binary
influxdb-client

# Fine-tuning infrastructure (Unsloth + supporting libraries)
unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git
transformers
datasets
peft
bitsandbytes
accelerate
torch
trl
wandb

# Monitoring and observability
prometheus-client
grafana-api

# Security and compliance
cryptography
python-jose

# Development and testing
pytest
black
isort
pre-commit

# Data processing for training
pandas
numpy
scikit-learn
matplotlib
seaborn

# Web framework for APIs
fastapi
uvicorn

# Configuration management
pydantic
python-dotenv

# Container orchestration
docker-compose
EOF

# Install all dependencies with UV (much faster!)
uv pip install -r requirements.in

# Generate lockfile for reproducible installs
uv pip compile requirements.in -o requirements.lock

# Generate traditional requirements.txt for compatibility
uv pip freeze > requirements.txt

# Copy the existing universal service runner architecture
cp -r ../intelluxe/scripts/universal-service-runner.sh ./scripts/
cp -r ../intelluxe/scripts/clinic-bootstrap.sh ./scripts/

# Create comprehensive environment file
cat > .env.example << EOF
# Core Services
POSTGRES_PASSWORD=secure_password_here
REDIS_PASSWORD=another_secure_password

# Project Configuration
PROJECT_NAME=intelluxe-ai
DATABASE_NAME=intelluxe
LOG_LEVEL=info

# TimescaleDB Configuration
TIMESCALE_RETENTION_POLICY=90d
TIMESCALE_COMPRESSION_AFTER=7d

# Health Monitoring
HEALTH_CHECK_INTERVAL=60s
HEALTH_ALERT_WEBHOOK=https://your-clinic.local/alerts
HEALTH_PAGE_PUBLIC=false

# Training & Fine-tuning (Phase 2+)
UNSLOTH_TRAINING_ENABLED=false
TRAINING_DATA_PATH=/app/data/training
ADAPTER_REGISTRY_PATH=/app/models/adapters
WANDB_PROJECT=intelluxe-training

# Compliance & Security
DATA_RETENTION_DAYS=2555  # 7 years for healthcare
AUDIT_LOG_LEVEL=detailed
PII_REDACTION_ENABLED=true
RBAC_ENABLED=true

# Performance
GPU_MEMORY_FRACTION=0.8
OLLAMA_MAX_LOADED_MODELS=3
OLLAMA_KEEP_ALIVE=24h

# Development flags
DEVELOPMENT_MODE=true
DEBUG_ENABLED=false
EOF

cp .env.example .env
```

## 2. Foundation Code Structure

**Application entry point (`main.py`):**
```python
from fastapi import FastAPI
from contextlib import asynccontextmanager
from config.app import config
import logging

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    logger.info(f"Starting {config.project_name}")
    # Future: Initialize memory manager, model registry, etc.
    yield
    logger.info(f"Shutting down {config.project_name}")

app = FastAPI(
    title="Intelluxe AI",
    description="Healthcare AI Assistant Platform",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/")
async def root():
    return {"message": "Intelluxe AI Healthcare Platform", "status": "ready"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "intelluxe-api"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Enhanced project configuration (`config/app.py`):**
```python
from pydantic import BaseSettings
from typing import Optional

class IntelluxeConfig(BaseSettings):
    """Application configuration with environment variable support"""
    
    # Core settings
    project_name: str = "intelluxe-ai"
    database_name: str = "intelluxe"
    log_level: str = "info"
    
    # Database configurations
    postgres_password: str
    redis_password: str
    postgres_url: str = "postgresql://intelluxe:${POSTGRES_PASSWORD}@localhost/intelluxe"
    redis_url: str = "redis://:${REDIS_PASSWORD}@localhost:6379"
    
    # TimescaleDB settings
    timescale_retention_policy: str = "90d"
    timescale_compression_after: str = "7d"
    
    # Health monitoring
    health_check_interval: str = "60s"
    health_alert_webhook: Optional[str] = None
    health_page_public: bool = False
    
    # Training settings (Phase 2+)
    unsloth_training_enabled: bool = False
    training_data_path: str = "/app/data/training"
    adapter_registry_path: str = "/app/models/adapters"
    wandb_project: str = "intelluxe-training"
    
    # Compliance settings
    data_retention_days: int = 2555  # 7 years
    audit_log_level: str = "detailed"
    pii_redaction_enabled: bool = True
    rbac_enabled: bool = True
    
    # Performance settings
    gpu_memory_fraction: float = 0.8
    ollama_max_loaded_models: int = 3
    ollama_keep_alive: str = "24h"
    
    # Development settings
    development_mode: bool = True
    debug_enabled: bool = False
    
    class Config:
        env_file = ".env"

# Global configuration instance
config = IntelluxeConfig()
```

**Memory manager interface (`core/memory/__init__.py`):**
```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

class MemoryInterface(ABC):
    """Abstract interface for memory management that can be extended"""
    
    @abstractmethod
    async def store_context(self, session_id: str, context: Dict[str, Any]) -> None:
        """Store conversation context"""
        pass
    
    @abstractmethod
    async def get_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve conversation context"""
        pass
    
    @abstractmethod
    async def log_interaction(self, session_id: str, user_id: str, 
                            agent_type: str, interaction_data: Dict[str, Any]) -> None:
        """Log agent interactions for future training data collection"""
        pass

class BaseMemoryManager(MemoryInterface):
    """Basic memory manager - will be enhanced in Phase 1"""
    
    def __init__(self):
        self._memory_store = {}  # In-memory for Phase 0
    
    async def store_context(self, session_id: str, context: Dict[str, Any]) -> None:
        self._memory_store[session_id] = context
    
    async def get_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._memory_store.get(session_id)
    
    async def log_interaction(self, session_id: str, user_id: str,
                            agent_type: str, interaction_data: Dict[str, Any]) -> None:
        # Basic logging - will be enhanced in Phase 1 with TimescaleDB
        print(f"Agent interaction: {agent_type} for user {user_id}")
```

**Agent base classes (`agents/__init__.py`):**
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from core.memory import MemoryInterface

class BaseAgent(ABC):
    """Base class for all Intelluxe agents"""
    
    def __init__(self, memory_manager: MemoryInterface):
        self.memory = memory_manager
        self.agent_type = self.__class__.__name__.lower().replace('agent', '')
    
    @abstractmethod
    async def process(self, input_data: Dict[str, Any], 
                     user_id: str, session_id: str) -> Dict[str, Any]:
        """Process input and return results"""
        pass
    
    async def log_interaction(self, session_id: str, user_id: str, 
                            input_data: Dict[str, Any], output_data: Dict[str, Any]) -> None:
        """Log this agent's interaction for future training"""
        await self.memory.log_interaction(
            session_id, user_id, self.agent_type,
            {"input": input_data, "output": output_data}
        )
```

## 3. Future-Ready Architecture Foundations

**Model registry placeholder (`core/models/__init__.py`):**
```python
from typing import Dict, Any, Optional
from pathlib import Path

class ModelRegistry:
    """Model registry with future fine-tuning support"""
    
    def __init__(self):
        self.models = {}
        self.adapters = {}  # For Phase 2 LoRA adapters
    
    def register_model(self, name: str, config: Dict[str, Any]) -> None:
        """Register a model configuration"""
        self.models[name] = config
    
    def get_model_config(self, name: str) -> Optional[Dict[str, Any]]:
        """Get model configuration"""
        return self.models.get(name)
    
    def register_adapter(self, user_id: str, adapter_path: str) -> None:
        """Register user-specific adapter (Phase 2)"""
        self.adapters[user_id] = adapter_path
    
    def get_user_model(self, user_id: str) -> str:
        """Get user's personalized model or default"""
        return self.adapters.get(user_id, "intelluxe-medical")

# Global registry
model_registry = ModelRegistry()
```

**Tool registry for MCP integration (`core/tools/__init__.py`):**
```python
from typing import Dict, Any, List, Optional

class ToolRegistry:
    """Registry for MCP tools and custom integrations"""
    
    def __init__(self):
        self.tools = {}
        self.tool_categories = {
            "medical_research": ["fda", "pubmed", "clinical_trials"],
            "insurance": ["anthem", "uhc", "cigna"],  # Phase 2
            "billing": ["billing_codes", "claims"],    # Phase 2
            "compliance": ["audit", "hipaa_check"]     # Phase 2
        }
    
    def register_tool(self, name: str, tool_config: Dict[str, Any]) -> None:
        """Register a tool configuration"""
        self.tools[name] = tool_config
    
    def get_tools_by_category(self, category: str) -> List[str]:
        """Get tools in a specific category"""
        return self.tool_categories.get(category, [])
    
    def is_tool_available(self, tool_name: str) -> bool:
        """Check if tool is configured and available"""
        return tool_name in self.tools

# Global tool registry
tool_registry = ToolRegistry()
```

**Plugin architecture for extensibility (`core/plugins/__init__.py`):**
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class TranscriberPlugin(ABC):
    """Base class for transcription plugins - enables future multi-agent transcription"""
    
    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, metadata: Dict[str, Any]) -> str:
        """Transcribe audio to text with metadata context"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """Return plugin capabilities and requirements"""
        pass

class PostProcessorPlugin(ABC):
    """Base class for post-processing plugins - enables Chain of Thought and advanced reasoning"""
    
    @abstractmethod
    async def process(self, text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process transcribed text with metadata"""
        pass
    
    @abstractmethod
    def supports_feature(self, feature: str) -> bool:
        """Check if plugin supports advanced features like CoT, voting, etc."""
        pass

class AgentPlugin(ABC):
    """Base class for specialized agent plugins - enables Motia-style orchestration"""
    
    @abstractmethod
    async def execute(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute specialized agent task"""
        pass

class PluginRegistry:
    """Registry for managing all plugins with future orchestration support"""
    
    def __init__(self):
        self.transcribers: Dict[str, TranscriberPlugin] = {}
        self.processors: Dict[str, PostProcessorPlugin] = {}
        self.agents: Dict[str, AgentPlugin] = {}
        self.routing_config = {}
        
    def register_transcriber(self, name: str, plugin: TranscriberPlugin) -> None:
        """Register a transcription plugin"""
        self.transcribers[name] = plugin
        
    def register_processor(self, name: str, plugin: PostProcessorPlugin) -> None:
        """Register a post-processing plugin"""
        self.processors[name] = plugin
        
    def register_agent(self, name: str, plugin: AgentPlugin) -> None:
        """Register a specialized agent plugin"""
        self.agents[name] = plugin
    
    def get_best_transcriber(self, metadata: Dict[str, Any]) -> str:
        """Select best transcriber based on metadata (future: Opik-style optimization)"""
        sensitivity = metadata.get('sensitivity', 'high')
        if sensitivity == 'high':
            return 'whisper_local'  # Always use local for sensitive data
        return self.routing_config.get('default_transcriber', 'whisper_local')
    
    def supports_chain_of_thought(self, processor_name: str) -> bool:
        """Check if processor supports Chain of Thought reasoning"""
        processor = self.processors.get(processor_name)
        return processor and processor.supports_feature('chain_of_thought')
    
    def supports_majority_voting(self, transcriber_name: str) -> bool:
        """Check if transcriber supports majority voting"""
        transcriber = self.transcribers.get(transcriber_name)
        return transcriber and 'voting' in transcriber.get_capabilities()

# Global plugin registry
plugin_registry = PluginRegistry()
```

**Basic plugins implementation (`core/plugins/basic_plugins.py`):**
```python
from typing import Dict, Any
from . import TranscriberPlugin, PostProcessorPlugin

class WhisperLocalTranscriber(TranscriberPlugin):
    """Local Whisper transcriber - secure, on-premise"""
    
    async def transcribe(self, audio_bytes: bytes, metadata: Dict[str, Any]) -> str:
        # Future: Implement actual Whisper transcription
        return f"[TRANSCRIBED via Whisper Local] audio_length: {len(audio_bytes)} bytes"
    
    def get_capabilities(self) -> Dict[str, Any]:
        return {
            'security': 'high',
            'local': True,
            'voting': False,  # Future: Enable for critical transcripts
            'languages': ['en', 'es', 'fr']
        }

class BasicTextProcessor(PostProcessorPlugin):
    """Basic text processing - formatting and cleaning"""
    
    async def process(self, text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        # Basic processing: clean and format
        cleaned_text = text.strip()
        
        return {
            'processed_text': cleaned_text,
            'confidence': 0.95,
            'processing_type': 'basic',
            'metadata': metadata
        }
    
    def supports_feature(self, feature: str) -> bool:
        # Future: Enable chain_of_thought, majority_voting, tree_of_thought
        return feature in ['basic_formatting', 'text_cleaning']

class MedicalTextProcessor(PostProcessorPlugin):
    """Medical-specific text processing - future CoT and reasoning"""
    
    async def process(self, text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        # Future: Add medical terminology normalization, SOAP note generation
        return {
            'processed_text': text,
            'medical_entities': [],  # Future: Extract medical entities
            'confidence': 0.90,
            'processing_type': 'medical',
            'chain_of_thought': None,  # Future: Add reasoning steps
            'metadata': metadata
        }
    
    def supports_feature(self, feature: str) -> bool:
        # Future capabilities for advanced medical AI
        future_features = [
            'chain_of_thought',      # For complex medical reasoning
            'majority_voting',       # For critical medical decisions
            'tree_of_thought',       # For treatment planning
            'medical_entities',      # Medical entity extraction
            'soap_generation'        # SOAP note generation
        ]
        return feature in future_features
```

## 4. Planning and Design Decisions

**Architecture decisions to document:**

1. **Service Management**: Use existing universal service runner pattern
2. **Database**: PostgreSQL with TimescaleDB extension (not InfluxDB)
3. **Session Storage**: Redis for fast session management
4. **Model Serving**: Ollama for local LLM inference
5. **Tool Orchestration**: AgentCare-MCP for medical tools
6. **Monitoring**: Custom health monitor (not Uptime Kuma)

**Security and compliance considerations:**
- All data stays on-premise
- HIPAA compliance built-in from Phase 1
- Role-based access control
- Comprehensive audit logging

## 5. Planning and Design Decisions

**Architecture decisions to document:**

1. **Service Management**: Use existing universal service runner pattern
2. **Database**: PostgreSQL with TimescaleDB extension (not InfluxDB)
3. **Session Storage**: Redis for fast session management
4. **Model Serving**: Ollama for local LLM inference
5. **Tool Orchestration**: AgentCare-MCP for medical tools
6. **Monitoring**: Custom health monitor (not Uptime Kuma)

**Security and compliance considerations:**
- All data stays on-premise
- HIPAA compliance built-in from Phase 1
- Role-based access control
- Comprehensive audit logging

## 6. Phase 0 Completion Checklist

**Basic Setup:**
- [ ] Comprehensive project directory structure created
- [ ] Git repository initialized with proper .gitignore
- [ ] Python virtual environment with all dependencies installed
- [ ] Environment configuration (.env) set up with all future settings
- [ ] Universal service runner scripts copied and ready
- [ ] Application entry point (main.py) created and tested

**Foundation Code:**
- [ ] Configuration management system implemented
- [ ] Memory manager interface and base implementation
- [ ] Model registry with future fine-tuning support
- [ ] Tool registry for MCP integration
- [ ] Base agent classes with logging hooks
- [ ] Basic testing framework established

**Documentation:**
- [ ] Comprehensive README.md created
- [ ] Architecture documentation written
- [ ] Development guide established
- [ ] Phase progression clearly defined

**Ready for Phase 1:**
- [ ] All foundation tests passing
- [ ] API server runs successfully
- [ ] Configuration loads correctly
- [ ] Development environment fully functional
- [ ] Service management scripts tested

Phase 0 creates a robust foundation for building a production-ready clinical AI system with forward-thinking architecture that gracefully supports the advanced capabilities planned for Phases 1-3.

**Migrate existing pip installations to UV:**
```bash
# If you have existing pip installations, migrate them to UV for faster future installs
# This step converts any existing pip-based projects to use UV

# 1. If you have an existing virtual environment, deactivate and backup
deactivate 2>/dev/null || true
if [ -d ".venv" ]; then
    mv .venv .venv.pip.backup
    echo "Backed up existing .venv to .venv.pip.backup"
fi

# 2. If you have existing requirements.txt, convert to requirements.in
if [ -f "requirements.txt" ] && [ ! -f "requirements.in" ]; then
    cp requirements.txt requirements.in
    echo "Converted requirements.txt to requirements.in for UV"
fi

# 3. Create new UV-managed virtual environment
uv venv
source .venv/bin/activate

# 4. Install dependencies with UV (much faster)
if [ -f "requirements.in" ]; then
    uv pip install -r requirements.in
elif [ -f "requirements.txt" ]; then
    uv pip install -r requirements.txt
fi

# 5. Generate lockfile for reproducible installs
uv pip compile requirements.in -o requirements.lock 2>/dev/null || echo "Skipping lockfile generation (no requirements.in)"

# 6. Update any pip commands in scripts to use UV
echo "Don't forget to update any scripts that use 'pip' to use 'uv pip' instead!"
echo "Search and replace 'pip install' with 'uv pip install' in your project files."

# 7. Performance comparison (optional)
echo "UV performance benefits:"
echo "- 10-100x faster package installation"
echo "- Built-in dependency resolution"
echo "- Lockfile support for reproducible environments"
echo "- Drop-in replacement for pip"
```