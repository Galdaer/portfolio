# Healthcare AI Integration Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the complete Healthcare AI Integration system with Open WebUI → Ollama → MCP → FastAPI Agent workflow.

## System Architecture

```
Doctor/User → Open WebUI (Port 1000) → Ollama (Port 11434) → MCP Server (Port 3000) → FastAPI Agents (Port 8000) → Healthcare Services → Response
```

## Prerequisites

### Hardware Requirements
- **CPU**: 8+ cores (16+ recommended for Ollama)
- **RAM**: 16GB minimum (32GB+ recommended)
- **Storage**: 50GB+ free space for models and data
- **Network**: Stable internet for model downloads

### Software Requirements
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Node.js**: 18.x+ (for MCP server)
- **Python**: 3.10+ (for FastAPI agents)
- **Redis**: 6.0+ (for caching)
- **PostgreSQL**: 13+ (for healthcare data)

## Installation Steps

### 1. Repository Setup

```bash
# Clone repository
git clone https://github.com/Intelluxe-AI/intelluxe-core.git
cd intelluxe-core

# Install dependencies
make install
make deps
make hooks

# Validate installation
make lint
make validate
```

### 2. Environment Configuration

Create environment files:

```bash
# Copy example configurations
cp .env.example .env
cp mcps/healthcare/.env.example mcps/healthcare/.env
```

**Main `.env` configuration:**
```bash
# Healthcare AI Configuration
ENVIRONMENT=production
HEALTHCARE_MODE=true
PHI_PROTECTION=strict
AUDIT_LOGGING=enabled

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=intelluxe
DB_USER=healthcare_user
DB_PASSWORD=secure_password_here

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=1

# Security Configuration
JWT_SECRET=your_jwt_secret_here_min_32_chars
HEALTHCARE_CONFIG_KEY=your_encryption_key_here
PHI_ENCRYPTION_KEY=your_phi_encryption_key_here

# Ollama Configuration
OLLAMA_BASE_URL=http://192.168.86.150:11434
OLLAMA_MODEL=llama3.1:8b-instruct-q4_K_M

# MCP Configuration
MCP_SERVER_URL=http://localhost:3000
MCP_ENABLED=true
```

**MCP Server `.env` configuration:**
```bash
# MCP Healthcare Server Configuration
HEALTHCARE_MCP_PORT=3000
MAIN_API_URL=http://localhost:8000
NODE_ENV=production

# Healthcare Compliance
PHI_DETECTION_ENABLED=true
AUDIT_LOGGING=true
MEDICAL_DISCLAIMERS=enabled

# Ollama Integration
OLLAMA_API_URL=http://192.168.86.150:11434
OLLAMA_MODEL=llama3.1:8b-instruct-q4_K_M

# External APIs (Optional)
FHIR_BASE_URL=http://localhost:8080/fhir
PUBMED_API_KEY=your_pubmed_key_optional
TRIALS_API_KEY=your_trials_key_optional
FDA_API_KEY=your_fda_key_optional

# WhisperLive Configuration
WHISPERLIVE_URL=http://localhost:9090
MOCK_TRANSCRIPTION=false
```

### 3. Database Setup

```bash
# Start PostgreSQL and Redis
docker run -d --name healthcare-postgres \
  -e POSTGRES_DB=intelluxe \
  -e POSTGRES_USER=healthcare_user \
  -e POSTGRES_PASSWORD=secure_password_here \
  -p 5432:5432 \
  postgres:13

docker run -d --name healthcare-redis \
  -p 6379:6379 \
  redis:6-alpine

# Initialize database schema
python3 scripts/init_healthcare_database.py
```

### 4. Ollama Model Installation

```bash
# Install Ollama (if not already installed)
curl -fsSL https://ollama.ai/install.sh | sh

# Pull recommended healthcare model
ollama pull llama3.1:8b-instruct-q4_K_M

# Alternative models for different performance needs:
# ollama pull llama3.1:70b-instruct-q4_K_M  # Higher accuracy, more resources
# ollama pull codellama:7b-instruct           # For code generation
# ollama pull medllama:7b                     # Specialized medical model (if available)

# Verify model installation
ollama list
```

### 5. Service Deployment

#### Option A: Docker Compose (Recommended)

```bash
# Create docker-compose.yml for full stack
cat > docker-compose.healthcare.yml << 'EOF'
version: '3.8'

services:
  # Open WebUI
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    ports:
      - "1000:8080"
    environment:
      - OLLAMA_BASE_URL=http://192.168.86.150:11434
      - HEALTHCARE_MODE=true
      - MCP_SERVER_URL=http://mcp-server:3000
      - MCP_ENABLED=true
      - PHI_PROTECTION=strict
      - AUDIT_LOGGING=enabled
    volumes:
      - open-webui-data:/app/backend/data
      - ./logs:/app/logs
    networks:
      - intelluxe-net
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/"]
      interval: 30s
      timeout: 10s
      retries: 3

  # MCP Healthcare Server
  mcp-server:
    build:
      context: ./mcps/healthcare
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - HEALTHCARE_MCP_PORT=3000
      - MAIN_API_URL=http://fastapi-agents:8000
      - PHI_DETECTION_ENABLED=true
      - AUDIT_LOGGING=true
      - OLLAMA_API_URL=http://192.168.86.150:11434
    volumes:
      - ./mcps/healthcare/.env:/app/.env
      - ./logs:/app/logs
    networks:
      - intelluxe-net
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # FastAPI Healthcare Agents
  fastapi-agents:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DB_HOST=postgres
      - REDIS_HOST=redis
      - PHI_PROTECTION=strict
    volumes:
      - ./.env:/app/.env
      - ./logs:/app/logs
    networks:
      - intelluxe-net
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # PostgreSQL Database
  postgres:
    image: postgres:13
    environment:
      - POSTGRES_DB=intelluxe
      - POSTGRES_USER=healthcare_user
      - POSTGRES_PASSWORD=secure_password_here
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./scripts/init_healthcare_database.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - intelluxe-net
    restart: unless-stopped

  # Redis Cache
  redis:
    image: redis:6-alpine
    volumes:
      - redis-data:/data
    networks:
      - intelluxe-net
    restart: unless-stopped

  # WhisperLive (Optional - for audio transcription)
  whisperlive:
    image: collabora/whisperlive:latest
    ports:
      - "9090:9090"
    environment:
      - MODEL=base.en
      - LANGUAGE=en
    networks:
      - intelluxe-net
    restart: unless-stopped

volumes:
  open-webui-data:
  postgres-data:
  redis-data:

networks:
  intelluxe-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
EOF

# Deploy full stack
docker-compose -f docker-compose.healthcare.yml up -d

# Verify all services are healthy
docker-compose -f docker-compose.healthcare.yml ps
```

#### Option B: Individual Service Deployment

```bash
# 1. Start MCP Server
cd mcps/healthcare
npm install
npm run build
npm start &

# 2. Start FastAPI Agents
cd ../..
python main.py &

# 3. Start Open WebUI (using docker)
docker run -d \
  --name open-webui \
  -p 1000:8080 \
  -e OLLAMA_BASE_URL=http://192.168.86.150:11434 \
  -e HEALTHCARE_MODE=true \
  -e MCP_SERVER_URL=http://localhost:3000 \
  -e MCP_ENABLED=true \
  -v open-webui-data:/app/backend/data \
  ghcr.io/open-webui/open-webui:main
```

### 6. Service Verification

```bash
# Test all services
./scripts/test_deployment.sh

# Manual verification
curl http://localhost:1000/               # Open WebUI
curl http://localhost:3000/health         # MCP Server
curl http://localhost:8000/health         # FastAPI Agents
curl http://192.168.86.150:11434/api/tags # Ollama
```

## Configuration Details

### Open WebUI MCP Integration

The Open WebUI service is configured to connect to the MCP server and enable healthcare features:

```bash
# Environment variables in Open WebUI
OLLAMA_BASE_URL=http://192.168.86.150:11434
HEALTHCARE_MODE=true
MCP_SERVER_URL=http://localhost:3000
MCP_ENABLED=true
PHI_PROTECTION=strict
AUDIT_LOGGING=enabled
```

### MCP Server Tools

The MCP server exposes these healthcare tools to Open WebUI:

1. **clinical_intake** - Patient intake processing
2. **transcribe_audio** - Medical audio transcription
3. **research_medical_literature** - PubMed and clinical research
4. **process_healthcare_document** - Clinical document processing
5. **billing_assistance** - Healthcare billing support
6. **insurance_verification** - Insurance eligibility checking

### FastAPI Agent Endpoints

The system includes 7 healthcare agents:

1. **Intake Agent** (`/agents/intake/*`) - Patient intake and registration
2. **Document Processor** (`/agents/document/*`) - Clinical document processing
3. **Research Assistant** (`/agents/research/*`) - Medical literature research
4. **Transcription Agent** (`/agents/transcription/*`) - Audio transcription
5. **Billing Helper** (`/agents/billing/*`) - Healthcare billing assistance
6. **Insurance Verification** (`/agents/insurance/*`) - Insurance verification
7. **Conversation Agent** (`/agents/conversation/*`) - General healthcare conversation

## Testing & Validation

### Integration Tests

```bash
# Run comprehensive test suite
make test

# Run specific test categories
pytest tests/test_e2e_healthcare_workflows.py -v
pytest tests/test_mcp_integration.py -v
pytest tests/test_phi_protection.py -v
```

### Manual Workflow Testing

1. **Access Open WebUI**: http://localhost:1000
2. **Configure MCP Connection**:
   - Go to Settings → Connections
   - Add MCP Server: `http://localhost:3000`
   - Enable "Healthcare Mode"
3. **Test Workflow**:
   - Start new chat
   - Use healthcare-specific tools
   - Verify PHI protection active
   - Check audit logging

### Performance Benchmarks

```bash
# Run performance tests
python tests/test_e2e_healthcare_workflows.py

# Expected performance targets:
# - MCP tool list: < 1s
# - Clinical intake: < 5s
# - Medical literature search: < 10s
# - Audio transcription: < 30s
```

## Security Configuration

### PHI Protection

```bash
# Enable comprehensive PHI protection
export PHI_PROTECTION=strict
export PHI_DETECTION_ENABLED=true
export AUDIT_LOGGING=enabled

# Configure encryption keys
export PHI_ENCRYPTION_KEY=$(openssl rand -base64 32)
export JWT_SECRET=$(openssl rand -base64 32)
```

### Audit Logging

All healthcare interactions are logged with:
- User identification (hashed)
- Action performed
- Timestamp
- PHI detection status
- Medical disclaimer inclusion

Logs are stored in:
- `/app/logs/healthcare_system.log` - Main system logs
- `/app/logs/chat/` - Chat interactions
- `/app/logs/audit/` - Compliance audit trail

### Network Security

```bash
# Firewall configuration (example for Ubuntu)
sudo ufw allow 1000/tcp    # Open WebUI
sudo ufw allow 3000/tcp    # MCP Server
sudo ufw allow 8000/tcp    # FastAPI Agents
sudo ufw allow 11434/tcp   # Ollama (if remote)

# SSL/TLS termination (recommended for production)
# Configure reverse proxy (nginx/traefik) with SSL certificates
```

## Monitoring & Maintenance

### Health Monitoring

```bash
# Service health checks
curl http://localhost:1000/health      # Open WebUI
curl http://localhost:3000/health      # MCP Server  
curl http://localhost:8000/health      # FastAPI Agents

# Performance monitoring
curl http://localhost:8000/metrics     # Prometheus metrics
curl http://localhost:3000/stats       # MCP server stats
```

### Log Management

```bash
# Log rotation configuration
sudo logrotate -d /etc/logrotate.d/healthcare-ai

# Log analysis
tail -f logs/healthcare_system.log | grep -E "(ERROR|PHI_ALERT|MEDICAL_ERROR)"

# Audit trail verification
python scripts/verify_audit_trail.py --days 7
```

### Database Maintenance

```bash
# Database backup
pg_dump -h localhost -U healthcare_user intelluxe > backup_$(date +%Y%m%d).sql

# Cache maintenance
redis-cli -h localhost -p 6379 INFO memory
redis-cli -h localhost -p 6379 FLUSHDB  # Clear cache if needed
```

## Troubleshooting

### Common Issues

1. **MCP Server Connection Failed**
   ```bash
   # Check MCP server logs
   docker logs mcp-server
   
   # Verify network connectivity
   curl http://localhost:3000/mcp -X POST -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
   ```

2. **Ollama Model Not Found**
   ```bash
   # Verify model installation
   ollama list
   
   # Pull missing model
   ollama pull llama3.1:8b-instruct-q4_K_M
   ```

3. **PHI Detection Errors**
   ```bash
   # Check PHI detector logs
   grep "PHI_ALERT" logs/healthcare_system.log
   
   # Verify synthetic data usage
   python scripts/validate_synthetic_data.py
   ```

4. **Agent Connection Issues**
   ```bash
   # Test individual agents
   curl http://localhost:8000/agents/intake/health
   curl http://localhost:8000/agents/research/health
   
   # Check FastAPI logs
   tail -f logs/fastapi.log
   ```

### Performance Optimization

1. **Ollama Optimization**
   ```bash
   # Allocate more RAM to Ollama
   export OLLAMA_HOST=0.0.0.0
   export OLLAMA_NUM_PARALLEL=4
   export OLLAMA_MAX_LOADED_MODELS=2
   ```

2. **Redis Cache Tuning**
   ```bash
   # Increase Redis memory
   redis-cli CONFIG SET maxmemory 2gb
   redis-cli CONFIG SET maxmemory-policy allkeys-lru
   ```

3. **Database Tuning**
   ```sql
   -- PostgreSQL optimization
   ALTER SYSTEM SET shared_buffers = '256MB';
   ALTER SYSTEM SET effective_cache_size = '1GB';
   SELECT pg_reload_conf();
   ```

## Production Considerations

### Scaling

- **Horizontal scaling**: Deploy multiple FastAPI agent instances behind load balancer
- **Database scaling**: Consider read replicas for high-load environments  
- **Cache scaling**: Redis cluster for distributed caching
- **Model scaling**: Multiple Ollama instances for concurrent requests

### Security Hardening

- **Network isolation**: Deploy in private network with VPN access
- **Certificate management**: Use proper SSL/TLS certificates
- **Secret management**: Use secret management service (Vault, etc.)
- **Regular updates**: Keep all components updated for security patches

### Backup Strategy

- **Database**: Daily automated backups with point-in-time recovery
- **Configuration**: Version-controlled configuration management
- **Logs**: Centralized logging with retention policies
- **Models**: Backup of custom-trained models

### Compliance Monitoring

- **Audit trails**: Regular compliance report generation
- **PHI protection**: Continuous monitoring for PHI exposure
- **Access controls**: Regular review of user permissions
- **Incident response**: Documented procedures for security incidents

## Support & Maintenance

For support and maintenance:

1. **Documentation**: Complete system documentation in `/docs/`
2. **Issue tracking**: GitHub issues for bug reports and feature requests
3. **Monitoring**: Comprehensive logging and metrics for troubleshooting
4. **Updates**: Regular system updates and security patches

## Medical Disclaimer

**IMPORTANT**: This system provides healthcare administrative and research assistance only. It does not provide medical advice, diagnosis, or treatment recommendations. All medical decisions must be made by qualified healthcare professionals based on individual patient assessment and clinical judgment.