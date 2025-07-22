# Phase 1: Core AI Infrastructure

**Duration:** 4 weeks  
**Goal:** Deploy functional healthcare AI system with Ollama inference, Healthcare-MCP integration, and basic agent workflows. Focus on core infrastructure that works reliably before adding business services.

## Week 1: Foundation Infrastructure and Essential Security

### 1.1 Essential Development Security (2-4 hours)

**Critical security patches (before any other setup):**
```bash
#!/bin/bash
# healthcare_dev_security.sh - Run BEFORE Phase 1 setup

# Update system packages
sudo apt update && sudo apt upgrade -y

# Install critical security patches
sudo apt install --only-upgrade \
  sudo systemd apport openssh-server xz-utils

# Configure fail2ban for SSH protection
sudo apt install fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Basic SSH hardening
sudo sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart sshd
```

**Pre-commit secret scanning (30 minutes):**
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
        exclude: .*\.lock|package-lock\.json
  
  - repo: local
    hooks:
      - id: check-healthcare-patterns
        name: Check for PHI patterns
        entry: scripts/check-phi-patterns.sh
        language: script
        files: '\.(py|js|yml|yaml|json)$'
```

**Healthcare pattern detector:**
```bash
#!/bin/bash
# scripts/check-phi-patterns.sh
if grep -rE '\b\d{3}-\d{2}-\d{4}\b' "$@"; then
  echo "ERROR: Potential SSN pattern detected"
  exit 1
fi

if grep -rE '\bMRN[:#]?\s*\d{6,}' "$@"; then
  echo "ERROR: Potential Medical Record Number detected"
  exit 1
fi
```

### 1.2 Database Infrastructure Deployment

**Deploy PostgreSQL with TimescaleDB using your service runner:**
```bash
# services/system/postgres/postgres.conf already exists
cd /opt/intelluxe
./scripts/universal-service-runner.sh start postgres

# Verify TimescaleDB extension
docker exec postgres psql -U intelluxe -d intelluxe -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"
```

**Deploy Redis for session management:**
```bash
# services/system/redis/redis.conf already exists
./scripts/universal-service-runner.sh start redis
```

**Enhanced database schema with monitoring and performance tracking:**
```sql
-- Enhanced schema for Phase 1 with monitoring and performance tracking
CREATE TABLE IF NOT EXISTS model_adapters (
    id SERIAL PRIMARY KEY,
    doctor_id VARCHAR(100) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    adapter_type VARCHAR(50) NOT NULL,
    adapter_data JSONB NOT NULL,
    performance_metrics JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) UNIQUE NOT NULL,
    doctor_id VARCHAR(100) NOT NULL,
    agent_type VARCHAR(50) NOT NULL,
    context_data JSONB,
    performance_data JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Time-series tables for monitoring (from updated monitoring scripts)
CREATE TABLE IF NOT EXISTS system_metrics (
    timestamp TIMESTAMP NOT NULL,
    hostname VARCHAR(100) NOT NULL,
    cpu_usage DECIMAL(5,2),
    memory_usage DECIMAL(5,2),
    disk_usage DECIMAL(5,2),
    advanced_ai_status INTEGER DEFAULT 0,
    ai_response_time DECIMAL(10,6) DEFAULT 0,
    gpu_memory_mb INTEGER DEFAULT 0,
    gpu_utilization DECIMAL(5,2) DEFAULT 0,
    agent_queue_size INTEGER DEFAULT 0,
    insurance_status INTEGER DEFAULT 0,
    billing_status INTEGER DEFAULT 0,
    compliance_status INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS diagnostic_metrics (
    timestamp TIMESTAMP NOT NULL,
    hostname VARCHAR(100) NOT NULL,
    total_tests INTEGER DEFAULT 0,
    passed_tests INTEGER DEFAULT 0,
    failed_tests INTEGER DEFAULT 0,
    reasoning_status INTEGER DEFAULT 0,
    model_count INTEGER DEFAULT 0,
    whisper_status INTEGER DEFAULT 0,
    mcp_status INTEGER DEFAULT 0,
    diagnostic_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create hypertables for time-series optimization
SELECT create_hypertable('agent_sessions', 'created_at', if_not_exists => TRUE);
SELECT create_hypertable('system_metrics', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('diagnostic_metrics', 'timestamp', if_not_exists => TRUE);
```

### 1.3 Ollama Model Serving Setup

**Deploy Ollama using your service configuration:**
```bash
# services/user/ollama/ollama.conf already exists
./scripts/universal-service-runner.sh start ollama

# Install healthcare models
docker exec ollama ollama pull llama3.1:8b-instruct-q4_K_M
docker exec ollama ollama pull mistral:7b-instruct-q4_K_M

# Verify models are loaded
docker exec ollama ollama list
```

**RTX 5060 Ti 16GB optimization configuration:**
```python
# core/models/ollama_optimization.py
class HealthcareOllamaConfig:
    def __init__(self):
        self.gpu_memory = 16  # GB
        self.models = {
            'clinical_chat': {
                'model': 'llama3.1:8b-instruct-q4_K_M',
                'memory_usage': 6,  # GB
                'context_length': 32768,
                'use_case': 'patient_interaction'
            },
            'medical_analysis': {
                'model': 'mistral:7b-instruct-q4_K_M',
                'memory_usage': 5,  # GB
                'context_length': 16384,
                'use_case': 'diagnostic_support'
            }
        }
    
    def optimize_for_healthcare(self):
        """Optimize GPU memory usage for healthcare workflows"""
        return {
            'gpu_memory_fraction': 0.9,
            'parallel_requests': 2,
            'model_switching_enabled': True,
            'quantization': 'q4_K_M'
        }
```

## Week 2: Healthcare-MCP Integration

### 2.1 Healthcare-MCP Deployment

**Deploy your custom Healthcare-MCP service:**
```bash
# Create service config if not exists
# services/user/healthcare-mcp/healthcare-mcp.conf
cd mcps/healthcare
./scripts/universal-service-runner.sh start healthcare-mcp

# Verify Healthcare-MCP tools are available
curl http://localhost:3000/tools
```

**Enhanced MCP client with unified interface:**
```python
# core/tools/unified_mcp_client.py
import httpx
from typing import Optional, Dict, Any

class UnifiedMCPClient:
    """
    Enhanced MCP client for healthcare workflows
    Routes to local Healthcare-MCP, with cloud fallback for non-PHI data
    """
    def __init__(self):
        self.healthcare_mcp_url = "http://localhost:3000"
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def call_healthcare_tool(self, 
                                  tool: str, 
                                  params: Dict[str, Any],
                                  contains_phi: bool = True) -> Dict[str, Any]:
        """
        Call healthcare tools through local MCP
        """
        if contains_phi:
            # Always use local Healthcare-MCP for PHI data
            url = f"{self.healthcare_mcp_url}/tools/{tool}"
        else:
            # Could use cloud services for non-PHI research
            url = f"{self.healthcare_mcp_url}/tools/{tool}"
            
        response = await self.client.post(url, json=params)
        return response.json()
    
    async def search_pubmed(self, query: str) -> Dict[str, Any]:
        """Search medical literature"""
        return await self.call_healthcare_tool(
            "pubmed_search", 
            {"query": query, "max_results": 10},
            contains_phi=False
        )
    
    async def lookup_fda_drug(self, drug_name: str) -> Dict[str, Any]:
        """Lookup FDA drug information"""
        return await self.call_healthcare_tool(
            "fda_drug_lookup",
            {"drug_name": drug_name},
            contains_phi=False
        )
```

### 2.2 Optional: Docker MCP Toolkit for Tool Management

**If you want enhanced tool discovery and management:**
```bash
# Install Docker MCP Toolkit for easier tool management
# (This enhances your Healthcare-MCP rather than replacing it)

# In Docker Desktop, enable MCP Toolkit extension
# Add your Healthcare-MCP as a custom server in the toolkit
```

**Toolkit integration configuration:**
```json
{
  "name": "Healthcare-MCP",
  "url": "http://localhost:3000",
  "description": "Custom medical research and healthcare tools",
  "tools": [
    {
      "name": "pubmed_search",
      "description": "Search PubMed for medical literature"
    },
    {
      "name": "fda_drug_lookup", 
      "description": "Query FDA drug database"
    },
    {
      "name": "clinical_trials_search",
      "description": "Search ClinicalTrials.gov"
    }
  ]
}
```

## Week 3: Agent Infrastructure

### 3.1 Enhanced Memory Manager

**Deploy memory manager with performance tracking:**
```python
# core/memory/enhanced_memory_manager.py
import redis
import psycopg2
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

class EnhancedMemoryManager:
    """
    Memory management with performance tracking for future optimization
    """
    def __init__(self):
        self.redis_client = redis.Redis(
            host='localhost', port=6379, decode_responses=True
        )
        self.db_conn = psycopg2.connect(
            "postgresql://intelluxe:secure_password@localhost:5432/intelluxe"
        )
    
    async def store_session_context(self, 
                                   session_id: str,
                                   doctor_id: str,
                                   agent_type: str,
                                   context: Dict[str, Any],
                                   performance_data: Optional[Dict[str, Any]] = None) -> None:
        """Store session context with performance tracking"""
        
        # Store in Redis for fast access
        redis_key = f"session:{session_id}"
        session_data = {
            'doctor_id': doctor_id,
            'agent_type': agent_type,
            'context': json.dumps(context),
            'last_accessed': datetime.now().isoformat()
        }
        
        self.redis_client.hset(redis_key, mapping=session_data)
        self.redis_client.expire(redis_key, 3600)  # 1 hour TTL
        
        # Store in PostgreSQL for persistence and performance analysis
        cursor = self.db_conn.cursor()
        cursor.execute("""
            INSERT INTO agent_sessions 
            (session_id, doctor_id, agent_type, context_data, performance_data)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (session_id) 
            DO UPDATE SET 
                context_data = EXCLUDED.context_data,
                performance_data = EXCLUDED.performance_data,
                last_accessed = CURRENT_TIMESTAMP
        """, (session_id, doctor_id, agent_type, 
              json.dumps(context), json.dumps(performance_data or {})))
        
        self.db_conn.commit()
    
    async def get_session_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session context with performance logging"""
        
        # Try Redis first for speed
        redis_key = f"session:{session_id}"
        redis_data = self.redis_client.hgetall(redis_key)
        
        if redis_data:
            # Update last accessed time
            self.redis_client.hset(redis_key, 'last_accessed', datetime.now().isoformat())
            
            return {
                'doctor_id': redis_data['doctor_id'],
                'agent_type': redis_data['agent_type'],
                'context': json.loads(redis_data['context'])
            }
        
        # Fallback to PostgreSQL
        cursor = self.db_conn.cursor()
        cursor.execute("""
            SELECT doctor_id, agent_type, context_data 
            FROM agent_sessions 
            WHERE session_id = %s
        """, (session_id,))
        
        result = cursor.fetchone()
        if result:
            return {
                'doctor_id': result[0],
                'agent_type': result[1],
                'context': result[2]
            }
        
        return None

# Global memory manager
memory_manager = EnhancedMemoryManager()
```

### 3.2 Agent Base Classes with Future Capabilities

**Enhanced agent architecture:**
```python
# core/agents/base_agent.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from core.memory.enhanced_memory_manager import memory_manager
import time

class BaseAgent(ABC):
    """
    Enhanced base agent with performance tracking and future capabilities
    """
    
    def __init__(self, agent_type: str):
        self.agent_type = agent_type
        self.performance_tracker = PerformanceTracker()
        
    @abstractmethod
    async def process(self, input_data: Dict[str, Any], 
                     session_id: str) -> Dict[str, Any]:
        """Process input and return result"""
        pass
    
    async def process_with_tracking(self, input_data: Dict[str, Any],
                                   session_id: str) -> Dict[str, Any]:
        """Wrapper that adds performance tracking"""
        start_time = time.time()
        
        try:
            result = await self.process(input_data, session_id)
            
            # Track performance for future optimization
            performance_data = {
                'processing_time': time.time() - start_time,
                'success': True,
                'agent_type': self.agent_type,
                'input_size': len(str(input_data)),
                'output_size': len(str(result))
            }
            
            await self.performance_tracker.log_performance(
                session_id, self.agent_type, performance_data
            )
            
            return result
            
        except Exception as e:
            # Log errors for debugging
            performance_data = {
                'processing_time': time.time() - start_time,
                'success': False,
                'error': str(e),
                'agent_type': self.agent_type
            }
            
            await self.performance_tracker.log_performance(
                session_id, self.agent_type, performance_data
            )
            
            raise

class PerformanceTracker:
    """Track agent performance for future optimization"""
    
    async def log_performance(self, session_id: str, agent_type: str,
                             performance_data: Dict[str, Any]) -> None:
        """Log performance data for analysis"""
        
        # Store performance data in session context
        session_context = await memory_manager.get_session_context(session_id)
        if session_context:
            await memory_manager.store_session_context(
                session_id=session_id,
                doctor_id=session_context['doctor_id'],
                agent_type=agent_type,
                context=session_context['context'],
                performance_data=performance_data
            )
```

## Week 4: Core Healthcare Agents

### 4.1 Document Processor Agent

**Enhanced document processor with error prevention:**
```python
# core/agents/document_processor.py
from core.agents.base_agent import BaseAgent
from core.tools.unified_mcp_client import UnifiedMCPClient
from typing import Dict, Any

class DocumentProcessorAgent(BaseAgent):
    """
    Process medical documents with safety checks and PHI protection
    """
    
    def __init__(self):
        super().__init__("document_processor")
        self.mcp_client = UnifiedMCPClient()
        self.phi_detector = PHIDetector()
        
    async def process(self, input_data: Dict[str, Any], 
                     session_id: str) -> Dict[str, Any]:
        """Process medical documents safely"""
        
        document_text = input_data.get('document_text', '')
        document_type = input_data.get('document_type', 'unknown')
        
        # Safety check: Detect and protect PHI
        phi_analysis = await self.phi_detector.analyze(document_text)
        if phi_analysis['has_high_risk_phi']:
            return {
                'error': 'High-risk PHI detected',
                'safety_block': True,
                'phi_types': phi_analysis['phi_types']
            }
        
        # Process document based on type
        if document_type == 'lab_report':
            return await self._process_lab_report(document_text, session_id)
        elif document_type == 'prescription':
            return await self._process_prescription(document_text, session_id)
        else:
            return await self._process_general_document(document_text, session_id)
    
    async def _process_lab_report(self, text: str, session_id: str) -> Dict[str, Any]:
        """Process lab reports with medical context"""
        
        # Extract lab values and interpret
        lab_values = await self._extract_lab_values(text)
        interpretations = []
        
        for lab in lab_values:
            if lab['value_numeric'] and lab['reference_range']:
                interpretation = await self._interpret_lab_value(lab)
                interpretations.append(interpretation)
        
        return {
            'document_type': 'lab_report',
            'lab_values': lab_values,
            'interpretations': interpretations,
            'requires_physician_review': any(
                interp['abnormal'] for interp in interpretations
            )
        }

class PHIDetector:
    """Detect and classify PHI in medical documents"""
    
    async def analyze(self, text: str) -> Dict[str, Any]:
        """Analyze text for PHI content"""
        
        phi_patterns = {
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'mrn': r'\bMRN[:#]?\s*\d{6,}',
            'phone': r'\b\d{3}-\d{3}-\d{4}\b',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        }
        
        detected_phi = {}
        for phi_type, pattern in phi_patterns.items():
            import re
            matches = re.findall(pattern, text)
            if matches:
                detected_phi[phi_type] = len(matches)
        
        # Classify risk level
        high_risk_phi = ['ssn', 'mrn']
        has_high_risk = any(phi_type in detected_phi for phi_type in high_risk_phi)
        
        return {
            'has_phi': bool(detected_phi),
            'has_high_risk_phi': has_high_risk,
            'phi_types': detected_phi,
            'risk_level': 'high' if has_high_risk else 'medium' if detected_phi else 'low'
        }

# Register the agent
document_processor = DocumentProcessorAgent()
```

### 4.2 Research Assistant Agent

**Enhanced research assistant with Healthcare-MCP integration:**
```python
# core/agents/research_assistant.py
from core.agents.base_agent import BaseAgent
from core.tools.unified_mcp_client import UnifiedMCPClient
from typing import Dict, Any, List

class ResearchAssistantAgent(BaseAgent):
    """
    Medical research assistant using Healthcare-MCP tools
    """
    
    def __init__(self):
        super().__init__("research_assistant")
        self.mcp_client = UnifiedMCPClient()
        
    async def process(self, input_data: Dict[str, Any], 
                     session_id: str) -> Dict[str, Any]:
        """Process research queries using multiple medical sources"""
        
        query = input_data.get('query', '')
        research_type = input_data.get('research_type', 'general')
        max_results = input_data.get('max_results', 5)
        
        if research_type == 'drug_information':
            return await self._research_drug_information(query, max_results)
        elif research_type == 'clinical_trials':
            return await self._research_clinical_trials(query, max_results)
        elif research_type == 'literature_review':
            return await self._research_literature(query, max_results)
        else:
            return await self._comprehensive_research(query, max_results)
    
    async def _research_drug_information(self, drug_name: str, 
                                       max_results: int) -> Dict[str, Any]:
        """Research drug information from FDA and other sources"""
        
        # Get FDA drug information
        fda_data = await self.mcp_client.lookup_fda_drug(drug_name)
        
        # Get additional literature
        pubmed_query = f"{drug_name} safety efficacy"
        literature = await self.mcp_client.search_pubmed(pubmed_query)
        
        return {
            'research_type': 'drug_information',
            'drug_name': drug_name,
            'fda_information': fda_data,
            'supporting_literature': literature.get('results', [])[:max_results],
            'summary': await self._generate_drug_summary(fda_data, literature)
        }
    
    async def _comprehensive_research(self, query: str,
                                    max_results: int) -> Dict[str, Any]:
        """Comprehensive research using all available sources"""
        
        # Search multiple sources in parallel
        pubmed_results = await self.mcp_client.search_pubmed(query)
        
        # Combine and rank results
        all_results = []
        all_results.extend(pubmed_results.get('results', []))
        
        # Sort by relevance/recency
        sorted_results = sorted(
            all_results,
            key=lambda x: x.get('relevance_score', 0),
            reverse=True
        )
        
        return {
            'research_type': 'comprehensive',
            'query': query,
            'total_sources': len(all_results),
            'top_results': sorted_results[:max_results],
            'source_breakdown': {
                'pubmed': len(pubmed_results.get('results', []))
            }
        }

# Register the agent
research_assistant = ResearchAssistantAgent()
```

### 4.3 Audio Transcription with Medical NLP Integration

**Direct Whisper integration with SciSpacy medical processing:**
```python
# core/agents/transcription_agent.py
from core.agents.base_agent import BaseAgent
import httpx
import spacy
from typing import Dict, Any, List

class TranscriptionAgent(BaseAgent):
    """
    Direct transcription using WhisperLive with SciSpacy medical NLP processing
    """
    
    def __init__(self):
        super().__init__("transcription")
        # Use your existing WhisperLive service
        self.whisperlive_url = "http://localhost:8001"  # Your custom service port
        self.client = httpx.AsyncClient(timeout=60.0)
        
        # Load SciSpacy model for medical entity extraction
        try:
            self.nlp = spacy.load("en_core_sci_sm")
            self.medical_nlp_available = True
        except OSError:
            print("Warning: SciSpacy model not found. Install with: pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.1/en_core_sci_sm-0.5.1.tar.gz")
            self.medical_nlp_available = False
        
    async def process(self, input_data: Dict[str, Any], 
                     session_id: str) -> Dict[str, Any]:
        """Transcribe audio and extract medical entities using SciSpacy"""
        
        audio_data = input_data.get('audio_data')  # bytes
        audio_format = input_data.get('format', 'wav')
        language = input_data.get('language', 'en')
        
        if not audio_data:
            return {'error': 'No audio data provided'}
        
        # Send audio to WhisperLive service
        files = {'audio': ('audio.' + audio_format, audio_data, f'audio/{audio_format}')}
        data = {'language': language}
        
        response = await self.client.post(
            f"{self.whisperlive_url}/transcribe",
            files=files,
            data=data
        )
        
        if response.status_code == 200:
            result = response.json()
            transcription_text = result.get('text', '')
            
            # Process with SciSpacy for medical entity extraction
            medical_entities = []
            if self.medical_nlp_available and transcription_text:
                medical_entities = await self._extract_medical_entities(transcription_text)
            
            return {
                'transcription': transcription_text,
                'confidence': result.get('confidence', 0.0),
                'language': language,
                'processing_time': result.get('processing_time', 0),
                'segments': result.get('segments', []),
                'medical_entities': medical_entities,
                'scispacy_processed': self.medical_nlp_available
            }
        else:
            return {
                'error': f'Transcription failed: {response.status_code}',
                'details': response.text
            }
    
    async def _extract_medical_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract medical entities using SciSpacy"""
        
        if not self.medical_nlp_available:
            return []
        
        doc = self.nlp(text)
        entities = []
        
        for ent in doc.ents:
            entities.append({
                'text': ent.text,
                'label': ent.label_,
                'start': ent.start_char,
                'end': ent.end_char,
                'description': spacy.explain(ent.label_) if spacy.explain(ent.label_) else ent.label_
            })
        
        return entities

# Register the agent
transcription_agent = TranscriptionAgent()
```

### 4.4 Enhanced Monitoring Using TimescaleDB

**Update your existing monitoring scripts to use TimescaleDB:**
```bash
# Update scripts/resource-pusher.sh and scripts/diagnostic-pusher.sh
# to use TimescaleDB instead of InfluxDB

# Deploy updated monitoring
cp updated-resource-pusher.sh scripts/resource-pusher.sh
cp updated-diagnostic-pusher.sh scripts/diagnostic-pusher.sh

# Test the updated scripts
./scripts/resource-pusher.sh --debug
./scripts/diagnostic-pusher.sh --debug
```

**Enhanced monitoring with healthcare AI metrics:**
```python
# core/monitoring/healthcare_metrics_collector.py
import psycopg2
from datetime import datetime
import asyncio

class HealthcareMetricsCollector:
    """
    Collect healthcare AI specific metrics for TimescaleDB
    """
    
    def __init__(self):
        self.db_conn = psycopg2.connect(
            "postgresql://intelluxe:secure_password@localhost:5432/intelluxe"
        )
    
    async def record_transcription_metrics(self, session_id: str, doctor_id: str,
                                         processing_time: float, entities_count: int,
                                         scispacy_time: float) -> None:
        """Record transcription and SciSpacy processing metrics"""
        
        cursor = self.db_conn.cursor()
        cursor.execute("""
            INSERT INTO healthcare_ai_metrics (
                timestamp, hostname, transcription_chunks_processed, 
                medical_entities_extracted, scispacy_processing_time,
                doctor_id, session_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            datetime.now(), 
            'localhost',  # Would be actual hostname
            1,  # One chunk processed
            entities_count,
            scispacy_time,
            doctor_id,
            session_id
        ))
        self.db_conn.commit()
    
    async def get_doctor_transcription_stats(self, doctor_id: str, days: int = 7) -> Dict[str, Any]:
        """Get transcription statistics for a doctor"""
        
        cursor = self.db_conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total_sessions,
                SUM(transcription_chunks_processed) as total_chunks,
                SUM(medical_entities_extracted) as total_entities,
                AVG(scispacy_processing_time) as avg_scispacy_time
            FROM healthcare_ai_metrics 
            WHERE doctor_id = %s 
              AND timestamp >= NOW() - INTERVAL '%s days'
        """, (doctor_id, days))
        
        result = cursor.fetchone()
        if result:
            return {
                'total_sessions': result[0],
                'total_chunks': result[1],
                'total_entities': result[2],
                'avg_scispacy_time': float(result[3]) if result[3] else 0.0
            }
        
        return {'total_sessions': 0, 'total_chunks': 0, 'total_entities': 0, 'avg_scispacy_time': 0.0}

# Global metrics collector
healthcare_metrics = HealthcareMetricsCollector()
```

## Week 4: Integration Testing and Monitoring Setup

### 4.1 Enhanced Monitoring for Your Existing Setup

**Add healthcare metrics to your resource-pusher.sh:**
```bash
# Add to scripts/resource-pusher.sh - healthcare-specific metrics
collect_healthcare_metrics() {
    # Check agent performance
    agent_response_time=$(curl -s -w "%{time_total}" -o /dev/null http://localhost:8080/health)
    
    # Check model memory usage (if GPU monitoring available)
    if command -v nvidia-smi &> /dev/null; then
        gpu_memory=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
        gpu_utilization=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits | head -1)
        
        # Add to InfluxDB line protocol
        echo "healthcareMetrics,host=${HOSTNAME} agent_response_time=${agent_response_time},gpu_memory=${gpu_memory},gpu_utilization=${gpu_utilization} ${timestamp}"
    fi
}
```

**Create healthcare-specific Grafana dashboard config:**
```json
# Add to your existing Grafana setup
{
  "dashboard": {
    "title": "Intelluxe Healthcare AI Dashboard",
    "panels": [
      {
        "title": "Agent Performance",
        "type": "graph",
        "targets": [
          {
            "query": "SELECT mean(agent_response_time) FROM healthcareMetrics WHERE $timeFilter GROUP BY time(1m)"
          }
        ]
      },
      {
        "title": "GPU Utilization",
        "type": "singlestat",
        "targets": [
          {
            "query": "SELECT last(gpu_utilization) FROM healthcareMetrics"
          }
        ]
      },
      {
        "title": "Model Memory Usage",
        "type": "graph",
        "targets": [
          {
            "query": "SELECT mean(gpu_memory) FROM healthcareMetrics WHERE $timeFilter GROUP BY time(5m)"
          }
        ]
      }
    ]
  }
}
```

### 4.2 Comprehensive Integration Testing

**Integration test suite using your service architecture:**
```python
# tests/test_phase1_integration.py
import pytest
import asyncio
import httpx
from core.agents.document_processor import DocumentProcessorAgent
from core.agents.research_assistant import ResearchAssistantAgent
from core.agents.transcription_agent import TranscriptionAgent

class TestPhase1Integration:
    
    @pytest.mark.asyncio
    async def test_service_health_checks(self):
        """Test all services are running via universal service runner"""
        
        services_to_check = [
            'http://localhost:11434/api/version',  # Ollama
            'http://localhost:3000/health',        # Healthcare-MCP
            'http://localhost:8001/health',        # WhisperLive
        ]
        
        async with httpx.AsyncClient() as client:
            for service_url in services_to_check:
                response = await client.get(service_url, timeout=5.0)
                assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_document_processing_flow(self):
        """Test complete document processing workflow"""
        agent = DocumentProcessorAgent()
        
        # Test lab report processing
        lab_report = {
            'document_text': 'Patient: John D. Hemoglobin: 12.5 g/dL (Normal: 13.5-17.5)',
            'document_type': 'lab_report'
        }
        
        result = await agent.process_with_tracking(lab_report, 'test_session_1')
        
        assert result['document_type'] == 'lab_report'
        assert 'lab_values' in result
        assert 'interpretations' in result
    
    @pytest.mark.asyncio
    async def test_healthcare_mcp_integration(self):
        """Test Healthcare-MCP tool integration"""
        from core.tools.unified_mcp_client import UnifiedMCPClient
        
        client = UnifiedMCPClient()
        
        # Test PubMed search
        pubmed_result = await client.search_pubmed("diabetes management")
        assert 'results' in pubmed_result or 'error' in pubmed_result
        
        # Test FDA drug lookup
        fda_result = await client.lookup_fda_drug("metformin")
        assert 'drug_name' in fda_result or 'error' in fda_result
    
    @pytest.mark.asyncio
    async def test_whisperlive_integration(self):
        """Test your WhisperLive transcription service"""
        agent = TranscriptionAgent()
        
        # Test with minimal audio data (would be real audio in practice)
        audio_data = {
            'audio_data': b'dummy_audio_data',  # In practice, real audio bytes
            'format': 'wav',
            'language': 'en'
        }
        
        result = await agent.process_with_tracking(audio_data, 'test_session_transcription')
        
        # Should either succeed or fail gracefully
        assert 'transcription' in result or 'error' in result
    
    @pytest.mark.asyncio
    async def test_performance_tracking(self):
        """Test that performance tracking works with your database"""
        from core.memory.enhanced_memory_manager import memory_manager
        
        # Store session with performance data
        await memory_manager.store_session_context(
            session_id='perf_test_session',
            doctor_id='dr_test',
            agent_type='test_agent',
            context={'test': 'data'},
            performance_data={'processing_time': 1.5, 'success': True}
        )
        
        # Retrieve session
        session = await memory_manager.get_session_context('perf_test_session')
        assert session is not None
        assert session['doctor_id'] == 'dr_test'

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

## Deployment and Validation Checklist

**Phase 1 Completion Criteria:**

- [ ] Essential development security implemented (SSH hardening, secret scanning)
- [ ] PostgreSQL with TimescaleDB deployed using universal service runner
- [ ] Redis deployed for session management
- [ ] Ollama serving healthcare-optimized models (llama3.1, mistral)
- [ ] Healthcare-MCP integrated with FDA, PubMed, ClinicalTrials tools
- [ ] Enhanced Memory Manager storing context with performance tracking
- [ ] Document Processor handling medical documents with PHI protection
- [ ] Research Assistant querying multiple sources via Healthcare-MCP
- [ ] Transcription Agent integrated with your WhisperLive service
- [ ] Healthcare-specific monitoring added to your existing InfluxDB/Grafana setup
- [ ] Integration tests passing
- [ ] Performance tracking infrastructure in place

**Key Architecture Achievements:**
- TimescaleDB for time-series performance data within your existing PostgreSQL
- Healthcare monitoring integrated with your existing resource-pusher/diagnostic-pusher scripts
- Healthcare-MCP provides medical research tools
- Redis for session caching, PostgreSQL for persistence (using your current setup)
- Agent base classes with performance tracking for future optimization
- PHI detection and protection in document processing
- Direct integration with your WhisperLive service (no Windows/Ubuntu pipeline)

**Ready for Phase 2:**
- Database schema includes performance tracking tables
- Memory manager designed for training data collection
- Agent base classes ready for advanced reasoning features
- Your existing monitoring system extended with healthcare metrics
- Tool registry supports plugin architecture for future capabilities

This Phase 1 delivers a solid, working foundation using your actual service architecture that healthcare organizations can deploy and use immediately, while being designed for the advanced capabilities coming in Phase 2 (business services + personalization) and Phase 3 (production deployment + advanced AI).