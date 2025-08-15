# 🏥 Intelluxe AI

**Family-Built, Privacy-First AI System for Healthcare**  
A modular, on-premise AI assistant platform for clinics and hospitals—co-designed by Justin and Jeffrey Sue. Intelluxe AI delivers explainable, local AI workflows using open-source LLMs and medical tools, without reliance on Big Tech or cloud lock-in.

## 📄 License & Attributions

Intelluxe AI proprietary software incorporating MIT-licensed open-source components.  
See [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) for complete open-source attributions including:
- Healthcare MCP Server (Kartha AI)
- AI Engineering Patterns (AI Engineering Hub)  
- WhisperLive Real-time Transcription (Collabora)

---

## 👁️‍🗨️ Why Intelluxe AI?

Healthcare needs secure, locally-controlled systems that can interpret patient text, automate routine tasks, and protect sensitive data.  
Intelluxe AI is built for clinics and healthcare teams who want to:

- **Own their AI:** No cloud lock-in, no hidden data sharing.
- **Protect patient privacy:** All PHI/PII remains inside your firewall.
- **Automate and document:** Speed up intake, documentation, and compliance.
- **Adapt to real-world workflows:** Modular tools, not "one size fits all".

---

## 🚦 Project Status (Q3 2025)

**Active development.**  
Phase 1: Core system, local demo, self-service install scripts, and initial MCP tool integrations.

### Core Components

- **Ollama:** Local LLM inference server (supports LLaMA 3, Meditron, Mistral, etc.)
- **MCP Orchestrator:** Manages medical tools and agent workflows
- **Memory Layer:** Custom session management using PostgreSQL for persistence and Redis for working memory
- **Health Monitor:** Custom service health checking with compliance-aware alerting
- **PostgreSQL + TimescaleDB:** Primary database with time-series support
- **Redis:** Session cache and rate limiting
- **Grafana:** Unified dashboards for metrics and monitoring
- **Prometheus:** System metrics collection
- **Nginx:** Reverse proxy and SSL termination
- **Compliance Layer:** Role-based access, audit logging, and data retention policies

### Example Agents/Tools (Non-Medical)

To avoid medical liability, we focus on administrative and documentation support:

- **Document Organization:** Categorize and tag incoming documents
- **PII Redaction:** Remove sensitive info from transcripts and documents
- **Schedule Optimization:** Suggest appointment scheduling improvements
- **Research Assistant:** Search PubMed/ClinicalTrials.gov mirrors
- **Billing Code Lookup:** Reference common codes (not medical advice)
- **Template Generation:** Create forms and documentation templates

**Note:** We explicitly avoid tools that could constitute medical advice, diagnosis, or treatment recommendations.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        INFERENCE LAYER                              │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │     Ollama      │    │   Model Adapter │    │  Health Monitor │  │
│  │   (Local LLM)   │    │    Registry     │    │   (Custom)      │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
┌───────────────────────────────────┼─────────────────────────────────┐
│                        ORCHESTRATION LAYER                          │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │   MCP Tools     │    │   Memory        │    │   Agent         │  │
│  │  & Registry     │    │   Manager       │    │  Coordinator    │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
│                                    │                                │
│     ┌──────────────────────────────┼──────────────────────────────┐ │
│     ▼                              ▼                              ▼ │
│ ┌─────────┐    ┌─────────┐    ┌─────────────┐    ┌─────────────┐    │
│ │  Redis  │    │ Postgres│    │ TimescaleDB │    │  Grafana    │    │
│ │(Session)│    │ (Core)  │    │ (Metrics)   │    │(Dashboard)  │    │
│ └─────────┘    └─────────┘    └─────────────┘    └─────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                    │
┌───────────────────────────────────┼─────────────────────────────────┐
│                         AGENT LAYER                                 │
│  ┌─────────────┬──────────────────┼─────────────┬──────────────┐    │
│  ▼             ▼                  ▼             ▼              ▼    │
│┌──────┐ ┌──────────┐ ┌────────────────┐ ┌──────────┐ ┌──────────┐   │
││Intake│ │Document  │ │   Scheduling   │ │Research  │ │Billing   │   │
││Agent │ │Processor │ │   Optimizer    │ │Assistant │ │Helper    │   │
│└──────┘ └──────────┘ └────────────────┘ └──────────┘ └──────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Hardware Requirements & Tiers

### Solo Practice (1-3 providers)
- **CPU:** AMD EPYC or Intel Xeon (8+ cores)
- **GPU:** 1× NVIDIA RTX 4090/5090 (24GB VRAM)
- **RAM:** 64GB ECC
- **Storage:** 2TB NVMe (RAID 1)
- **Network:** Gigabit, airgap-capable
- **Form Factor:** Tower or 2U rackmount

### Small Clinic (4-10 providers)
- **CPU:** Dual AMD EPYC (16+ cores each)
- **GPU:** 2× NVIDIA RTX 6000 Ada (48GB VRAM each)
- **RAM:** 128GB ECC
- **Storage:** 4TB NVMe (RAID 10)
- **Network:** 10GbE, VLAN support
- **Form Factor:** 4U rackmount with redundant PSU

### Multi-Site Practice (11-50 providers)
- **CPU:** Dual AMD EPYC (32+ cores each)
- **GPU:** 2-4× NVIDIA A100/H100 (80GB VRAM)
- **RAM:** 256-512GB ECC
- **Storage:** 8TB+ NVMe (RAID 10) + cold storage
- **Network:** Dual 10GbE, site-to-site VPN
- **Form Factor:** Full rack with UPS

### Enterprise (50+ providers)
- **Custom architecture consultation required**
- **Multi-node clustering**
- **Geographic redundancy**
- **Dedicated support team**

---

## 🔑 Environment Variables

Create `.env` from `.env.example`:

```bash
# Core Services
OLLAMA_HOST=http://172.20.0.10:11434
POSTGRES_PASSWORD=secure_password_here
REDIS_PASSWORD=another_secure_password

# TimescaleDB
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

# Compliance & Security
DATA_RETENTION_DAYS=2555  # 7 years for healthcare
AUDIT_LOG_LEVEL=detailed
PII_REDACTION_ENABLED=true
RBAC_ENABLED=true

# Performance
GPU_MEMORY_FRACTION=0.8
MAX_CONCURRENT_REQUESTS=10
INFERENCE_TIMEOUT=30s
```

---

## 🚀 Quick Start

### Prerequisites
- **OS:** Ubuntu 22.04 LTS or compatible
- **RAM:** 16GB minimum (64GB+ recommended)
- **GPU:** NVIDIA with 12GB+ VRAM (24GB+ recommended)
- **Storage:** 100GB+ free space
- **Docker:** 24.0+ with GPU support

### Installation

```bash
# Clone repository
git clone https://github.com/Intelluxe-AI/intelluxe-core.git
cd intelluxe-ai

# Install system dependencies
sudo apt update
sudo apt install docker.io nvidia-docker2 python3-venv curl

# Install uv for faster Python package management
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc  # Reload PATH for uv

# Setup Python environment
python3 -m venv venv
source venv/bin/activate
uv pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Setup and deploy core infrastructure
./scripts/setup-environment.sh

# Verify deployment and health check
./scripts/setup-environment.sh --health-check
```

### Verification

```bash
# Check services are running
curl http://172.20.0.10:11434/api/tags  # Ollama
curl http://localhost:3000           # Grafana
curl http://localhost:9090           # Prometheus

# Test AI capabilities
curl -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Test healthcare administrative query"}'
```

---

## 📊 Development Phases

### Phase 0: Foundation (Weeks 1-2)
- Core infrastructure setup (PostgreSQL, Redis, TimescaleDB)
- Memory management framework
- Agent coordination patterns
- Testing infrastructure

### Phase 1: Core System (Weeks 3-6)  
- Ollama deployment with healthcare models
- MCP tool integration (FDA, PubMed, ClinicalTrials)
- Enhanced agents with AI Engineering Hub patterns
- Monitoring and compliance framework

### Phase 2: Personalization (Weeks 7-11)
- Unsloth training infrastructure
- Doctor-specific style adaptation via QLoRA
- Training data collection and synthetic generation
- Personalized model deployment

### Phase 3: Advanced Orchestration (Weeks 12-16)
- Multi-agent workflows with Tree of Thought
- Performance optimization (40x improvements)
- Voice interaction capabilities
- Production-scale deployment

---

## 🛡️ Security & Compliance

### Data Protection
- **PHI/PII Redaction:** Automatic removal of sensitive information
- **Role-Based Access:** Admin, Physician, Nurse, Staff, ReadOnly roles
- **Audit Logging:** Comprehensive activity tracking
- **Data Retention:** Configurable policies (default: 7 years)

### Network Security
- **Air-Gap Capable:** No external dependencies required
- **VPN Access:** Secure remote connectivity
- **Firewall Integration:** Automated security rules
- **SSL/TLS:** End-to-end encryption

### Compliance Features
- **HIPAA-Ready Architecture:** Supports compliance requirements
- **Audit Trails:** Immutable activity logs
- **Access Controls:** Granular permission system
- **Data Sovereignty:** All data remains on-premise

---

### Legal Considerations
- **No Medical Advice:** Intelluxe provides administrative support only
- **HIPAA Compliance:** Architecture supports compliance; certification is client's responsibility
- **Data Sovereignty:** All data remains on-premise
- **No Model Training:** We never use client data for model improvement

---

## 🤝 Contributing

### Development Setup
```bash
# Fork and clone
git clone https://github.com/your-username/intelluxe-ai.git
cd intelluxe-ai

# Install development dependencies
make dev-setup

# Run tests
make test

# Check code quality
make lint

# Create feature branch
git checkout -b feature/your-feature
```

### Architecture Guidelines
- **Modular Design:** Each component should be independently deployable
- **Security First:** All data processing must respect healthcare privacy requirements
- **Performance:** Optimize for on-premise hardware constraints
- **Compliance:** Consider audit and regulatory requirements in all features

---

## 📞 Contact & Community

- **GitHub Issues:** [Bug reports and feature requests](https://github.com/Intelluxe-AI/intelluxe-core/issues)
- **Email:** intelluxe@example.com
- **Documentation:** [https://docs.intelluxe.ai](https://docs.intelluxe.ai)
- **Community Forum:** [https://community.intelluxe.ai](https://community.intelluxe.ai)

---

## Authentication Setup

Intelluxe integrates with your existing clinic authentication or provides standalone auth:

### Option 1: Integrate with Existing Systems
```bash
# Configure for Active Directory integration
echo "AUTH_MODE=active_directory" >> .env
echo "EXISTING_AUTH_DOMAIN=yourclinic.local" >> .env
echo "USER_ENV_FILES=true" >> .env

# Each user gets encrypted personal config
# /home/dr_jones/.intelluxe/user.env.encrypted
# /home/nurse_smith/.intelluxe/user.env.encrypted
```

### Option 2: Standalone Authentication
```bash
# Independent authentication for small clinics
echo "AUTH_MODE=standalone" >> .env
echo "USER_ENV_FILES=true" >> .env
echo "STANDALONE_AUTH_ENABLED=true" >> .env
```

### User Configuration
Each staff member gets personal AI settings automatically encrypted based on their system login:
- **No additional passwords** - uses existing clinic authentication
- **Personal AI preferences** - model selection, specialty focus, workflow settings
- **Role-based permissions** - automatic access control based on job function
- **Session security** - config only accessible when user is logged in
