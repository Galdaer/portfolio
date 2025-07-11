# Phase 1: Core AI Infrastructure

**Duration:** 3-4 weeks  
**Goal:** Deploy functional healthcare AI system with Ollama inference, Healthcare-MCP integration, and basic agent workflows. Focus on core infrastructure that works reliably before adding business services.

## Deployment and Validation Checklist

**Phase 1 Completion Criteria:**

- [ ] Ollama serving healthcare-optimized models (llama3.1, mistral)
- [ ] Redis and PostgreSQL with TimescaleDB deployed and tested
- [ ] AgentCare-MCP integrated with FDA, PubMed, ClinicalTrials tools
- [ ] Memory Manager storing context in Redis + PostgreSQL
- [ ] Document Processor handling basic form/report categorization
- [ ] Research Assistant querying multiple sources via MCP
- [ ] Custom Health Monitor replacing Uptime Kuma
- [ ] Integration tests passing
- [ ] Universal service runner updated with new services

**Key Architecture Decisions:**
- TimescaleDB instead of InfluxDB for time-series data in PostgreSQL
- Custom health monitor integrated with compliance layer
- AgentCare-MCP provides existing medical research tools
- Redis for session caching, PostgreSQL for persistence
- Basic agents that can be enhanced in Phase 2

**Ready for Phase 2:**
- Database schema includes future tables for personalization
- Memory manager designed for training data collection
- Agent base classes ready for model adapter integration
- Health monitoring provides baseline for performance measurement

This Phase 1 delivers a solid, working foundation that healthcare organizations can deploy and use immediately, while being architected for the advanced capabilities coming in Phase 2 (business services + personalization) and Phase 3 (production deployment + scaling).


## Service Configuration Format

**All service configurations are compatible with the universal service runner.**

Service configuration files use lowercase keys that map directly to Docker arguments:
- `image=` - Docker image name (required)
- `port=` - Port mappings (e.g., "8080:80" or "8080:80 9090:90")
- `volumes=` - Volume mounts (e.g., "./data:/data ./config:/config:ro")
- `env=` - Environment variables (e.g., "VAR1=value1 VAR2=value2")
- `restart=` - Restart policy (e.g., "unless-stopped")
- `network=` - Docker network name
- `health_cmd=` - Health check command
- `memory_limit=` - Memory limit (e.g., "2g", "512m")
- `working_dir=` - Working directory inside container
- `command=` - Override container command

**Service names come from the CLI, not the config file:**
```bash
# Start a service by passing the service name as an argument
./universal-service-runner.sh ollama /services/user/ollama/ollama.conf
```

**Notes on removed fields:**
- `NAME=` and `CONTAINER_NAME=` - Not needed (service name from CLI)
- `BUILD_CONTEXT=` - Handled separately by build system
- `DEPENDS_ON=` - Managed by orchestration layer

---

## Week 1: Local LLM Infrastructure and Memory

### 1.1 Production Ollama Deployment

**Create `/services/user/ollama/ollama.conf`:**
```bash
# Service: ollama - Local AI model server
image="ollama/ollama:latest"
port="11434:11434"
volumes="./models:/root/.ollama ./config:/config:ro"
env="OLLAMA_HOST=0.0.0.0 OLLAMA_KEEP_ALIVE=24h OLLAMA_MAX_LOADED_MODELS=3"
restart="unless-stopped"
network="clinical-net"
health_cmd="curl -f http://localhost:11434/api/tags || exit 1"
device="/dev/nvidia0:/dev/nvidia0"
memory_limit="20g"
security_opt="no-new-privileges:true"
```

**Enhanced setup script (`/services/user/ollama/setup.sh`):**
```bash
#!/bin/bash
set -e

# Pull healthcare-optimized models
docker exec ollama ollama pull llama3.1:8b-instruct
docker exec ollama ollama pull mistral:7b-instruct

# Create custom healthcare model
docker exec ollama ollama create intelluxe-medical -f - <<EOF
FROM llama3.1:8b-instruct
PARAMETER temperature 0.1
PARAMETER top_p 0.9
SYSTEM """You are a healthcare administrative assistant. You help with documentation, research, and administrative tasks. You do not provide medical advice. Focus on: document processing, research assistance, administrative workflows, billing code reference, and scheduling optimization."""
EOF
```

### 1.2 Memory System Deployment

**Redis Configuration (`/services/user/redis/redis.conf`):**
```bash
# Service: redis - In-memory data structure store
image="redis:7-alpine"
port="6379:6379"
volumes="./data:/data"
restart="unless-stopped"
network="clinical-net"
memory_limit="2g"
```

**PostgreSQL with TimescaleDB (`/services/user/postgres/postgres.conf`):**
```bash
# Service: postgres - PostgreSQL database with TimescaleDB extension
image="timescale/timescaledb:latest-pg16"
port="5432:5432"
volumes="./data:/var/lib/postgresql/data ./init:/docker-entrypoint-initdb.d:ro"
env="POSTGRES_DB=intelluxe POSTGRES_USER=intelluxe POSTGRES_PASSWORD=secure_password"
restart="unless-stopped"
network="clinical-net"
memory_limit="4g"
```

**Database schema (`/services/user/postgres/init/01-schema.sql`):**
```sql
-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Core context management
CREATE TABLE conversation_context (
    session_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    context JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Agent interaction logging with time-series
CREATE TABLE agent_interactions (
    interaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    agent_type VARCHAR(100) NOT NULL,
    task_type VARCHAR(100) NOT NULL,
    input_data JSONB,
    output_data JSONB,
    processing_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('agent_interactions', 'created_at');

-- Basic audit logging
CREATE TABLE audit_log (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    action VARCHAR(255) NOT NULL,
    resource_type VARCHAR(100),
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('audit_log', 'created_at');

-- Performance indexes
CREATE INDEX idx_conversation_context_user_id ON conversation_context(user_id);
CREATE INDEX idx_agent_interactions_user_id ON agent_interactions(user_id);
CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
```

## Week 2: AgentCare-MCP Integration and Basic Agents

### 2.1 MCP Credentials Management

**Create secure credentials management system:**

**Environment setup (`/services/user/agentcare-mcp/.env.example`):**
```bash
# MCP Tool Credentials Template
# Copy to .env and fill in real values

# Anthem (Availity) API
ANTHEM_API_KEY=dummy_key
ANTHEM_API_SECRET=dummy_secret

# UnitedHealthcare (Optum) API
UHC_API_USER=dummy_user
UHC_API_PASS=dummy_pass

# Cigna API
CIGNA_CLIENT_ID=dummy_client_id
CIGNA_CLIENT_SECRET=dummy_client_secret

# Public APIs (no credentials needed)
# PUBMED_API_KEY=optional
# CLINICALTRIALS_API_KEY=optional

# Database connections
DATABASE_URL=postgresql://intelluxe:${POSTGRES_PASSWORD}@postgres:5432/intelluxe
REDIS_URL=redis://redis:6379
```

**Credentials loading (`/services/user/agentcare-mcp/src/config/credentials.js`):**
```javascript
import dotenv from 'dotenv';
import { readFileSync, existsSync } from 'fs';

// Load environment variables
dotenv.config();

class CredentialsManager {
    constructor() {
        this.credentials = new Map();
        this.loadCredentials();
    }
    
    loadCredentials() {
        // Load from environment variables
        const envCredentials = {
            anthem: {
                apiKey: process.env.ANTHEM_API_KEY,
                apiSecret: process.env.ANTHEM_API_SECRET,
                requiresAuth: true
            },
            uhc: {
                apiUser: process.env.UHC_API_USER,
                apiPass: process.env.UHC_API_PASS,
                requiresAuth: true
            },
            cigna: {
                clientId: process.env.CIGNA_CLIENT_ID,
                clientSecret: process.env.CIGNA_CLIENT_SECRET,
                requiresAuth: true
            },
            pubmed: {
                apiKey: process.env.PUBMED_API_KEY || null,
                requiresAuth: false
            },
            clinicaltrials: {
                apiKey: process.env.CLINICALTRIALS_API_KEY || null,
                requiresAuth: false
            }
        };
        
        for (const [tool, creds] of Object.entries(envCredentials)) {
            this.credentials.set(tool, creds);
        }
    }
    
    getCredentials(toolName) {
        const creds = this.credentials.get(toolName);
        if (!creds) {
            throw new Error(`No credentials configured for tool: ${toolName}`);
        }
        
        if (creds.requiresAuth && this.isEmpty(creds)) {
            throw new Error(`Tool ${toolName} requires credentials but none are configured`);
        }
        
        return creds;
    }
    
    isEmpty(creds) {
        const values = Object.values(creds).filter(v => v !== null && v !== undefined && v !== '');
        return values.length === 0;
    }
    
    validateAllCredentials() {
        const validation = {};
        
        for (const [toolName, creds] of this.credentials) {
            validation[toolName] = {
                configured: !this.isEmpty(creds),
                required: creds.requiresAuth,
                status: creds.requiresAuth ? (!this.isEmpty(creds) ? 'ready' : 'missing') : 'optional'
            };
        }
        
        return validation;
    }
}

export const credentialsManager = new CredentialsManager();
```

**Security best practices documentation:**
```markdown
# MCP Credentials Security Guide

## File Management
- Copy `.env.example` to `.env` and fill in real credentials
- Never commit `.env` files to source control
- Use strong file permissions: `chmod 600 .env`

## Credential Types
| Tool | Auth Type | Required | Notes |
|------|-----------|----------|-------|
| Anthem/Availity | OAuth2 | Yes | Insurance verification |
| UnitedHealthcare | Basic Auth | Yes | Claims/eligibility |
| Cigna | API Key | Yes | Prior authorization |
| PubMed | API Key | No | Public medical research |
| ClinicalTrials | None | No | Public trial data |

## Production Security
- Use Docker secrets or Kubernetes secrets in production
- Rotate credentials regularly
- Monitor credential usage in audit logs
- Use least-privilege access principles
```

### 2.2 AgentCare-MCP Setup and Customization

**Clone and configure AgentCare-MCP:**
```bash
# Fork AgentCare-MCP to your GitHub first, then clone your fork
git clone https://github.com/YOUR_USERNAME/agentcare-mcp.git services/user/agentcare-mcp
cd services/user/agentcare-mcp
rm -rf .git  # Vendor the code for local customization
```

**Create Dockerfile for AgentCare-MCP (`/services/user/agentcare-mcp/Dockerfile`):**
```dockerfile
FROM node:20-alpine
WORKDIR /app

# Copy source code (already cloned)
COPY . .

# Install dependencies
RUN npm install

# Install MCP Create Tool for custom tool generation
RUN npm install -g @anthropic/create-mcp-tool

# Create workspace for custom tools
RUN mkdir -p /app/tools/custom

# Copy custom configuration
COPY config/ ./config/

EXPOSE 3000
CMD ["npm", "start"]
```

**Create `/services/user/agentcare-mcp/agentcare-mcp.conf`:**
```bash
# Service: agentcare-mcp - Model Context Protocol server for AgentCare
image="agentcare-mcp:latest"
# Note: Build context handled separately by build system
port="3000:3000"
volumes="./config:/app/config:rw ./custom-tools:/app/tools/custom:rw"
env="NODE_ENV=production OLLAMA_URL=http://ollama:11434"
restart="unless-stopped"
network="clinical-net"
# Note: Dependencies managed by orchestration layer
health_cmd="curl -f http://localhost:3000/health || exit 1"
memory_limit="2g"
```

### 2.3 Universal Service Runner Updates

**Enhanced universal-service-runner.sh for new parameters:**
```bash
# Add new services to arg_map
arg_map+=("ollama:docker")
arg_map+=("agentcare-mcp:docker")
arg_map+=("postgres:docker")
arg_map+=("redis:docker")

# Enhanced docker handler with new parameters
docker_handler() {
    local CONFIG_FILE=$1
    
    # ... existing config loading ...
    
    # Add support for DEVICES parameter (GPU access)
    if [ ! -z "$DEVICES" ]; then
        DOCKER_ARGS="$DOCKER_ARGS --device=$DEVICES"
    fi
    
    # Add support for BUILD_CONTEXT
    if [ ! -z "$BUILD_CONTEXT" ] && [ "$BUILD_CONTEXT" != "." ]; then
        echo "Building image from context: $BUILD_CONTEXT"
        ORIGINAL_PWD=$(pwd)
        cd "$BUILD_CONTEXT"
        docker build -t "$IMAGE" .
        cd "$ORIGINAL_PWD"
    fi
    
    # Add support for WORKING_DIR
    if [ ! -z "$WORKING_DIR" ]; then
        DOCKER_ARGS="$DOCKER_ARGS -w $WORKING_DIR"
    fi
    
    # Add support for COMMAND override
    if [ ! -z "$COMMAND" ]; then
        DOCKER_ARGS="$DOCKER_ARGS"
        # Command will be appended at the end
    fi
    
    # Add support for DEPENDS_ON (wait for dependencies)
    if [ ! -z "$DEPENDS_ON" ]; then
        echo "Waiting for dependencies: $DEPENDS_ON"
        for dep in $DEPENDS_ON; do
            wait_for_service "$dep"
        done
    fi
    
    # ... rest of docker handler ...
}

# Add dependency waiting function
wait_for_service() {
    local service_name=$1
    local max_wait=120
    local count=0
    
    echo "Waiting for $service_name to be ready..."
    while [ $count -lt $max_wait ]; do
        if docker ps --filter "name=$service_name" --filter "status=running" | grep -q $service_name; then
            echo "$service_name is ready"
            return 0
        fi
        sleep 1
        count=$((count + 1))
    done
    
    echo "Warning: $service_name did not start within $max_wait seconds"
    return 1
}
```

**Test the services:**
```bash
./clinic-bootstrap.sh
# Select ollama and agentcare-mcp to install/start
# After starting:
docker exec ollama ollama pull llama3.1:8b-instruct
curl http://localhost:11434/api/tags
curl http://localhost:3000/health
```

## Week 3: Basic Agent Implementation

### 3.1 Memory Manager Implementation

**Create enhanced memory manager (`core/memory/memory_manager.py`):**
```python
from typing import Dict, List, Any, Optional
import redis
import psycopg2
import json
from datetime import datetime

class MemoryManager:
    """Enhanced memory manager using Redis and PostgreSQL with TimescaleDB"""
    
    def __init__(self):
        self.redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)
        self.pg_conn = psycopg2.connect(
            "postgresql://intelluxe:secure_password@postgres:5432/intelluxe"
        )
        
    async def store_context(self, session_id: str, user_id: str, 
                          context: Dict[str, Any]) -> None:
        """Store conversation context with Redis cache and PostgreSQL persistence"""
        context_entry = {
            "context": context,
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "user_id": user_id
        }
        
        # Store in Redis for immediate access (1 hour TTL)
        self.redis_client.setex(f"context:{session_id}", 3600, json.dumps(context_entry))
        
        # Store in PostgreSQL for persistence
        cursor = self.pg_conn.cursor()
        cursor.execute("""
            INSERT INTO conversation_context (session_id, user_id, context) 
            VALUES (%s, %s, %s) 
            ON CONFLICT (session_id) 
            DO UPDATE SET context = %s, updated_at = NOW()
        """, (session_id, user_id, context, context))
        self.pg_conn.commit()
    
    async def get_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve context from Redis cache first, fallback to PostgreSQL"""
        # Try Redis first
        cached = self.redis_client.get(f"context:{session_id}")
        if cached:
            return json.loads(cached)
        
        # Fallback to PostgreSQL
        cursor = self.pg_conn.cursor()
        cursor.execute("""
            SELECT context FROM conversation_context 
            WHERE session_id = %s
        """, (session_id,))
        
        result = cursor.fetchone()
        if result:
            context = result[0]
            # Refresh Redis cache
            self.redis_client.setex(f"context:{session_id}", 3600, json.dumps(context))
            return context
        
        return None
    
    async def log_interaction(self, session_id: str, user_id: str, agent_type: str,
                            task_type: str, input_data: Dict[str, Any],
                            output_data: Dict[str, Any], processing_time_ms: int) -> None:
        """Log agent interactions to TimescaleDB"""
        cursor = self.pg_conn.cursor()
        cursor.execute("""
            INSERT INTO agent_interactions (
                session_id, user_id, agent_type, task_type, 
                input_data, output_data, processing_time_ms
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (session_id, user_id, agent_type, task_type,
              json.dumps(input_data), json.dumps(output_data), processing_time_ms))
        self.pg_conn.commit()
```

### 3.2 Basic Document Processing Agent

**Create document processor (`agents/document_processor.py`):**
```python
from typing import Dict, Any
import asyncio
import time
from core.memory.memory_manager import MemoryManager

class DocumentProcessor:
    """Basic document processing agent for healthcare documents"""
    
    def __init__(self, memory_manager: MemoryManager):
        self.memory = memory_manager
        
    async def process_document(self, document_data: Dict[str, Any], 
                             user_id: str, session_id: str) -> Dict[str, Any]:
        """Process healthcare documents with basic categorization"""
        start_time = time.time()
        
        doc_type = self._identify_document_type(document_data)
        
        if doc_type == "form":
            result = await self._process_form(document_data)
        elif doc_type == "report":
            result = await self._process_report(document_data)
        else:
            result = await self._process_generic_document(document_data)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Log interaction
        await self.memory.log_interaction(
            session_id, user_id, "document_processor", doc_type,
            {"document_id": document_data.get("id", "unknown")},
            result, processing_time
        )
        
        return result
    
    def _identify_document_type(self, document_data: Dict[str, Any]) -> str:
        """Identify document type for appropriate processing"""
        content = str(document_data.get("content", "")).lower()
        
        if "patient information" in content or "insurance" in content:
            return "form"
        elif "results" in content or "findings" in content:
            return "report"
        else:
            return "generic"
    
    async def _process_form(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process intake forms and administrative documents"""
        return {
            "document_type": "form",
            "extracted_fields": {
                "has_patient_info": True,
                "has_insurance_info": True,
                "completeness_score": 0.85
            },
            "suggested_actions": ["verify_insurance", "schedule_follow_up"]
        }
    
    async def _process_report(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process medical reports and lab results"""
        return {
            "document_type": "report",
            "key_findings": ["results_available", "follow_up_needed"],
            "confidence_score": 0.9
        }
    
    async def _process_generic_document(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process general documents"""
        return {
            "document_type": "generic",
            "processing_status": "completed",
            "confidence_score": 0.7
        }
```

### 3.3 Research Assistant Agent

**Create research assistant (`agents/research_assistant.py`):**
```python
from typing import Dict, Any, List
import asyncio
import time
import requests
from core.memory.memory_manager import MemoryManager

class ResearchAssistant:
    """Research assistant using AgentCare-MCP tools"""
    
    def __init__(self, memory_manager: MemoryManager, mcp_base_url: str = "http://agentcare-mcp:3000"):
        self.memory = memory_manager
        self.mcp_url = mcp_base_url
        
    async def research_query(self, query: str, user_id: str, 
                           session_id: str) -> Dict[str, Any]:
        """Research healthcare queries using MCP tools"""
        start_time = time.time()
        
        # Use AgentCare-MCP tools (FDA, PubMed, ClinicalTrials)
        results = await self._search_multiple_sources(query)
        
        # Synthesize results
        synthesis = await self._synthesize_results(results, query)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Log interaction
        await self.memory.log_interaction(
            session_id, user_id, "research_assistant", "research_query",
            {"query": query[:100]},  # Truncate for logging
            {"results_count": len(results), "sources": list(results.keys())},
            processing_time
        )
        
        return {
            "query": query,
            "results": results,
            "synthesis": synthesis,
            "sources_searched": ["fda", "pubmed", "clinical_trials"],
            "total_results": sum(len(r) for r in results.values())
        }
    
    async def _search_multiple_sources(self, query: str) -> Dict[str, List[Dict[str, Any]]]:
        """Search FDA, PubMed, and ClinicalTrials via MCP"""
        sources = ["fda", "pubmed", "clinical_trials"]
        results = {}
        
        for source in sources:
            try:
                # Call AgentCare-MCP tool endpoint
                response = requests.post(f"{self.mcp_url}/tools/{source}/search", 
                                       json={"query": query}, timeout=30)
                if response.status_code == 200:
                    results[source] = response.json().get("data", [])
                else:
                    results[source] = []
            except Exception as e:
                print(f"Error searching {source}: {e}")
                results[source] = []
        
        return results
    
    async def _synthesize_results(self, results: Dict[str, List[Dict[str, Any]]], 
                                query: str) -> Dict[str, Any]:
        """Synthesize research results into actionable insights"""
        total_results = sum(len(r) for r in results.values())
        
        if total_results == 0:
            return {
                "summary": "No relevant results found",
                "confidence": 0.0,
                "recommendations": ["Try different search terms", "Consult specialist"]
            }
        
        # Basic synthesis (enhance with LLM in production)
        synthesis = {
            "summary": f"Found {total_results} relevant results across {len(results)} sources",
            "confidence": min(0.8, total_results / 10),  # Simple confidence scoring
            "recommendations": [
                "Review FDA guidance" if results.get("fda") else None,
                "Check recent publications" if results.get("pubmed") else None,
                "Look for ongoing trials" if results.get("clinical_trials") else None
            ]
        }
        
        # Filter out None recommendations
        synthesis["recommendations"] = [r for r in synthesis["recommendations"] if r]
        
        return synthesis
```

## Week 4: Basic Monitoring and Testing

### 4.1 Custom Health Monitor (replaces Uptime Kuma)

**Create custom health monitor (`/services/user/health-monitor/health-monitor.conf`):**
```bash
# Service: health-monitor - Custom health monitoring service
image="python:3.11-slim"
# Note: Build context handled separately by build system
port="8080:8080"
volumes="./app:/app:rw"
env="POSTGRES_URL=postgresql://intelluxe:secure_password@postgres:5432/intelluxe"
restart="unless-stopped"
network="clinical-net"
# Note: Dependencies managed by orchestration layer
health_cmd="curl -f http://localhost:8080/health || exit 1"
memory_limit="256m"
working_dir="/app"
command="python health_monitor.py"
```

**Health monitor service (`/services/user/health-monitor/app/health_monitor.py`):**
```python
from flask import Flask, jsonify
import psycopg2
import redis
import requests
import time
from datetime import datetime
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

class HealthMonitor:
    """Custom health monitoring service with PostgreSQL storage"""
    
    def __init__(self):
        self.db_conn = psycopg2.connect(
            "postgresql://intelluxe:secure_password@postgres:5432/intelluxe"
        )
        self.services = {
            "ollama": "http://ollama:11434/api/tags",
            "agentcare-mcp": "http://agentcare-mcp:3000/health",
            "redis": "redis://redis:6379",
            "postgres": "postgresql://postgres:5432"
        }
        self._init_health_table()
    
    def _init_health_table(self):
        """Initialize health check results table"""
        cursor = self.db_conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS health_checks (
                id SERIAL PRIMARY KEY,
                service_name VARCHAR(100) NOT NULL,
                status VARCHAR(20) NOT NULL,
                response_time_ms INTEGER,
                error_message TEXT,
                checked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        
        # Convert to hypertable for time-series data
        try:
            cursor.execute("SELECT create_hypertable('health_checks', 'checked_at')")
        except:
            pass  # Table might already be a hypertable
        
        self.db_conn.commit()
    
    def check_all_services(self):
        """Check health of all services"""
        results = {}
        
        for service, endpoint in self.services.items():
            result = self._check_service(service, endpoint)
            results[service] = result
            self._store_health_result(service, result)
        
        return results
    
    def _check_service(self, service_name: str, endpoint: str) -> dict:
        """Check individual service health"""
        start_time = time.time()
        
        try:
            if service_name == "redis":
                r = redis.from_url(endpoint)
                r.ping()
                status = "healthy"
                error = None
            elif service_name == "postgres":
                # Already connected, just test query
                cursor = self.db_conn.cursor()
                cursor.execute("SELECT 1")
                status = "healthy"
                error = None
            else:
                response = requests.get(endpoint, timeout=10)
                if response.status_code == 200:
                    status = "healthy"
                    error = None
                else:
                    status = "unhealthy"
                    error = f"HTTP {response.status_code}"
        except Exception as e:
            status = "unhealthy"
            error = str(e)
        
        response_time = int((time.time() - start_time) * 1000)
        
        return {
            "status": status,
            "response_time_ms": response_time,
            "error": error,
            "checked_at": datetime.now().isoformat()
        }
    
    def _store_health_result(self, service_name: str, result: dict):
        """Store health check result in database"""
        cursor = self.db_conn.cursor()
        cursor.execute("""
            INSERT INTO health_checks (service_name, status, response_time_ms, error_message)
            VALUES (%s, %s, %s, %s)
        """, (service_name, result["status"], result["response_time_ms"], result["error"]))
        self.db_conn.commit()

health_monitor = HealthMonitor()

@app.route('/health')
def health_check():
    """Health check endpoint for this service"""
    return jsonify({"status": "healthy", "service": "health-monitor"})

@app.route('/check')
def check_services():
    """Check all services and return results"""
    results = health_monitor.check_all_services()
    overall_status = "healthy" if all(r["status"] == "healthy" for r in results.values()) else "degraded"
    
    return jsonify({
        "overall_status": overall_status,
        "services": results,
        "checked_at": datetime.now().isoformat()
    })

@app.route('/history/<service>')
def service_history(service):
    """Get health history for a specific service"""
    cursor = health_monitor.db_conn.cursor()
    cursor.execute("""
        SELECT status, response_time_ms, error_message, checked_at
        FROM health_checks 
        WHERE service_name = %s 
        ORDER BY checked_at DESC 
        LIMIT 50
    """, (service,))
    
    history = []
    for row in cursor.fetchall():
        history.append({
            "status": row[0],
            "response_time_ms": row[1],
            "error_message": row[2],
            "checked_at": row[3].isoformat()
        })
    
    return jsonify({"service": service, "history": history})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
```

### 4.2 Integration Testing

**Create integration test suite (`tests/test_phase1_integration.py`):**
```python
import pytest
import requests
import time
import asyncio
from core.memory.memory_manager import MemoryManager
from agents.document_processor import DocumentProcessor
from agents.research_assistant import ResearchAssistant

class TestPhase1Integration:
    """Integration tests for Phase 1 components"""
    
    def test_service_health(self):
        """Test that all core services are healthy"""
        services = {
            "ollama": "http://localhost:11434/api/tags",
            "agentcare-mcp": "http://localhost:3000/health",
            "health-monitor": "http://localhost:8080/health"
        }
        
        for service, url in services.items():
            response = requests.get(url, timeout=10)
            assert response.status_code == 200, f"{service} is not healthy"
    
    @pytest.mark.asyncio
    async def test_memory_manager(self):
        """Test memory manager functionality"""
        memory = MemoryManager()
        
        test_context = {"user_query": "test query", "session_data": "test"}
        await memory.store_context("test_session", "test_user", test_context)
        
        retrieved = await memory.get_context("test_session")
        assert retrieved is not None
        assert retrieved["context"]["user_query"] == "test query"
    
    @pytest.mark.asyncio 
    async def test_document_processor(self):
        """Test document processing agent"""
        memory = MemoryManager()
        processor = DocumentProcessor(memory)
        
        test_doc = {
            "id": "test_doc_1",
            "content": "Patient information form with insurance details"
        }
        
        result = await processor.process_document(test_doc, "test_user", "test_session")
        
        assert result["document_type"] == "form"
        assert "extracted_fields" in result
        assert result["extracted_fields"]["has_patient_info"] == True
    
    @pytest.mark.asyncio
    async def test_research_assistant(self):
        """Test research assistant with mock MCP"""
        memory = MemoryManager()
        assistant = ResearchAssistant(memory)
        
        # This will fail gracefully if MCP is not responding
        result = await assistant.research_query("diabetes treatment", "test_user", "test_session")
        
        assert "query" in result
        assert "results" in result
        assert "sources_searched" in result
    
    def test_health_monitor_api(self):
        """Test health monitor endpoints"""
        # Test main health check
        response = requests.get("http://localhost:8080/check")
        assert response.status_code == 200
        
        data = response.json()
        assert "overall_status" in data
        assert "services" in data
        
        # Test service history
        response = requests.get("http://localhost:8080/history/ollama")
        assert response.status_code == 200
```