# 🏥 Intelluxe AI (On‑Prem Healthcare AI Platform)

Privacy‑first, on‑premise AI system designed for clinics and hospitals. This repository documents how the platform’s services are orchestrated via the bootstrap system and how they work together to provide compliant, operational AI capabilities.

This software supports administrative and documentation workflows. It does not provide diagnosis or treatment recommendations.

---

## 🔷 System Architecture Overview

The platform is composed of modular services running in Docker, managed via an interactive bootstrap menu (make setup). Services are grouped by layers and wired together through a private network, with a reverse proxy and monitoring by default.

- Inference & NLP
  - Ollama: Local LLM inference gateway
  - SciSpacy: Healthcare NLP entity extraction and enrichment
  - Wyoming Whisper: Local speech-to-text (optional)

- Orchestration & API
  - Healthcare API: FastAPI-based administrative and research-support endpoints
  - Healthcare MCP: Tool/agent orchestration for research and administrative tasks

- Data & Caching
  - PostgreSQL: Primary data store
  - Redis: Sessions, rate limiting, working memory

- Research Data Sources
  - Medical Mirrors: Local mirrors of PubMed, ClinicalTrials.gov, FDA datasets (admin/research use only)

- Access, Routing, and Security
  - Traefik: Reverse proxy and SSL termination
  - WireGuard: VPN for remote/secure access (optional)

- Observability
  - Grafana: Dashboards
  - (Compatible with Prometheus and health endpoints)

All services are declared and launched via the universal service runner and can be enabled/disabled or restarted individually from the menu.

---

## 🧩 Services Overview (bootstrap-managed)

- Traefik (Reverse Proxy)
  - Central routing, TLS termination, service discovery

- PostgreSQL (Core DB) and Redis (Cache/Sessions)
  - Durable storage, sessions, rate limiting, and short‑term working memory

- Ollama (LLM) and SciSpacy (NLP)
  - Local AI inference for language tasks and medical entity recognition

- Healthcare API
  - FastAPI endpoints for administrative and research‑support functions
  - Health: http://172.20.0.16:8000/health
  - Docs: http://172.20.0.16:8000/docs

- Healthcare MCP
  - Agent/tool orchestration with controlled capabilities (no diagnosis/treatment)

- Medical Mirrors
  - Local mirrors for research workflows: PubMed, ClinicalTrials.gov, FDA
  - Includes “smart” and “force” update/processing flows

- Grafana (Monitoring)
  - Dashboards for system health and service metrics

- WireGuard (VPN)
  - Optional secure remote access

Notes:
- IPs and ports above reflect default internal networking. Public access is typically routed via Traefik and/or VPN depending on your deployment.
- Exact services available depend on selections during setup.

---

## 🚀 Bootstrap‑First Setup

Use the interactive bootstrap to install, configure, and operate the stack. It safely handles networking, prerequisites, and service lifecycle.

1) Prepare environment
```bash
cp .env.example .env
# Edit values as needed (passwords, network, retention, etc.)
```

2) Run the interactive setup
```bash
make setup
```

3) Follow the menus to:
- Install/Initialize core services
- Start/Stop/Restart individual services
- Check health and diagnostics
- Update or process research mirrors (optional)
- Manage VPN (optional)

Tip: You can re‑run make setup anytime to change service selections or restart components.

---

## 🧭 Menu‑Driven Operations

Common actions via make setup:
- First‑time install: choose Install/Initialize, then enable the services you want
- Start/Stop/Restart a service: choose Service Management → select service → action
- Health & Diagnostics: choose Diagnostics/Health to run checks and view status
- Research Mirrors: choose Medical Mirrors to run smart or force updates/processing
- VPN: enable/disable WireGuard if needed

Menu shortcut (non-interactive) examples:
- Restart Healthcare API via menu path (as configured in this version):
```bash
printf '3\n2\n' | make setup
# 3 = Restart menu, 2 = Healthcare API index
```

Other known indices (restart menu) in this version:
- Grafana: 1
- Healthcare API: 2
- Llama.cpp: 3
- Ollama: 5
- Ollama WebUI: 6
- PostgreSQL: 7
- Redis: 8
- Medical Mirrors: 9
- Traefik: 10
- WireGuard: 11
- Wyoming Whisper: 12
- SciSpacy: 14

Note: Menu indices can change; the interactive menu always shows current numbers.

---

## 🔄 How Services Work Together

- Clients (internal apps, staff tools, or approved UI) call Healthcare API.
- Healthcare API orchestrates capabilities:
  - Queries LLMs via Ollama for local inference
  - Uses SciSpacy for domain entity extraction
  - Leverages Healthcare MCP for controlled tool/agent actions
  - Reads/writes data to PostgreSQL; uses Redis for sessions and throttling
- Traefik routes external traffic to the appropriate service, enforcing TLS and routing rules.
- Grafana provides status and dashboards; health endpoints offer quick checks.
- Medical Mirrors keeps research data localized to avoid external dependencies and to preserve privacy.
- WireGuard provides VPN access for administrators or remote staff when enabled.

Design priorities:
- On‑prem only, no cloud dependencies required
- HIPAA‑aware patterns (PHI redaction, auditability, RBAC via configuration)
- Health checks, least‑privilege networking, encrypted channels

---

## ✅ Health, Logs, and Status

Interactive:
- make setup → Diagnostics/Health for stack-level checks
- Menu → Service Management → [Service] → View Logs / Health

Direct checks (examples):
- Healthcare API: http://172.20.0.16:8000/health
- Grafana (if exposed locally): http://localhost:3000
- Ollama tags: http://172.20.0.10:11434/api/tags

---

## 🧰 Common Operational Flows

- Bring the stack online:
  - make setup → Install/Initialize → enable services → Start All

- Restart a single service (interactive):
  - make setup → Service Management → [Service] → Restart

- Research data sync (localized, optional):
  - make setup → Medical Mirrors → Smart Update or Force Update (time‑intensive)

- Troubleshoot:
  - make setup → Diagnostics/Health → run full checks
  - View service logs via menu, or use docker logs for targeted inspection

---

## 🔐 Safety and Scope

- No medical diagnosis or treatment recommendations
- Privacy‑first: data remains on clinic hardware
- Compliance‑aware: auditability, PHI safeguards, and retention policies supported
- RBAC and network isolation are expected in production deployments

---

## 📎 References

- Environment template: [.env.example](./.env.example)
- Service configurations and docs:
  - Services root: [services/user/](./services/user/)
  - Healthcare API: [services/user/healthcare-api/](./services/user/healthcare-api/)
  - Medical Mirrors: [services/user/medical-mirrors/](./services/user/medical-mirrors/)
  - SciSpacy: [services/user/scispacy/](./services/user/scispacy/)
  - Traefik: [services/user/traefik/](./services/user/traefik/)
  - WireGuard: [services/user/wireguard/](./services/user/wireguard/)
  - Ollama: [services/user/ollama/](./services/user/ollama/)
  - Grafana: [services/user/grafana/](./services/user/grafana/)
- Organization architecture reference (style-aligned): Intelluxe core README

---
