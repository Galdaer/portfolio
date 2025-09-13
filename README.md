# Portfolio: Privacy‑First AI Systems Engineering (Public)

A public, portfolio-friendly snapshot of my work building a privacy-first, on‑premise AI platform. This repository extracts generalized, non-clinical patterns from a family-built healthcare AI system and showcases the engineering approaches, tooling, and infrastructure I use to deliver secure, self-hosted AI services.

What this repo demonstrates:
- On‑prem AI orchestration using Docker and declarative service configs
- Secure-by-default patterns (env management, health checks, least-privilege)
- Python + Bash tooling, Makefile-based developer experience
- Observability fundamentals and testable infrastructure
- Agentic development documentation and reasoning patterns

No PHI/PII is included. This is not a medical product; it’s a portfolio for employers.

---

## Highlights

- Universal Service Runner (declarative services)
  - Define services with simple `.conf` files (image, ports, volumes, env, healthcheck)
  - Add/remove services without changing the runner
  - See: [services/README.md](services/README.md)

- Developer Experience
  - Makefile tasks, pre-commit hooks, linting/typing (`.flake8`, `mypy.ini`, `pyproject.toml`)
  - Devcontainer support (`.devcontainer/`) and editor settings (`.vscode/`)

- Security/Privacy Mindset
  - Environment-driven configuration (`.env.example`)
  - Healthchecks, network modes, explicit capabilities
  - Compliance-aware patterns from clinical contexts, generalized here for public use

- Agentic Development (Documentation)
  - Structured agent instructions and workflows captured in `.claude/` and `CLAUDE*.md`
  - Emphasis on testability, observability, and integration points

---

## Quick Start (Local, Minimal)

Goal: get oriented and run local checks without any special hardware or private services.

Prerequisites:
- Python 3.10+ (3.11 recommended)
- Docker (optional, for service demos)
- Make (optional, improves DX)

1) Clone and set up Python environment
```bash
git clone https://github.com/Galdaer/portfolio.git
cd portfolio

# Option A: venv + pip
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Option B: uv
# curl -LsSf https://astral.sh/uv/install.sh | sh
# source ~/.bashrc
# uv venv
# source .venv/bin/activate
# uv pip install -r requirements.txt
```

2) Configure environment (optional)
```bash
cp .env.example .env
# Adjust values to your local environment if needed
```

3) Explore and run basic checks
```bash
# If Make is available
make help || true
make lint || true
make test || true

# Or run tests directly
pytest -q || true
```

---

## Healthcare API (services/user/healthcare-api)

A FastAPI-based service that exposes administrative and research-support endpoints (no diagnosis/treatment). It demonstrates:
- Clear service boundaries, typed Python, and testable FastAPI patterns
- Declarative Docker builds and health checks
- Integration points for agents, transcription, research tooling, and compliance-aware features

Key paths:
- Service root: [services/user/healthcare-api](services/user/healthcare-api)
- Entrypoint: [main.py](services/user/healthcare-api/main.py)
- Dockerfile: [Dockerfile](services/user/healthcare-api/Dockerfile)
- Service config: [healthcare-api.conf](services/user/healthcare-api/healthcare-api.conf)
- API modules: [api/](services/user/healthcare-api/api)
- Core logic: [core/](services/user/healthcare-api/core)
- Domain models: [domains/](services/user/healthcare-api/domains)
- Agents and patterns: [agents/](services/user/healthcare-api/agents)
- Config and settings: [config/](services/user/healthcare-api/config)
- Supporting code: [src/](services/user/healthcare-api/src)
- Static assets: [static/](services/user/healthcare-api/static)
- Examples and docs: [examples/](services/user/healthcare-api/examples), [docs/](services/user/healthcare-api/docs)
- Tests: [tests/](services/user/healthcare-api/tests) and top-level test files in the folder

Default endpoints (used by Make targets):
- Health: http://172.20.0.16:8000/health
- OpenAPI docs: http://172.20.0.16:8000/docs

Note: The IP above is how the infrastructure targets check the container on a custom Docker network. For simple local runs you can publish `-p 8000:8000` and use `http://localhost:8000`.

### Build, Run, and Restart via Make

The Makefile includes a full set of convenience targets for the Healthcare API:

- Build image
```bash
make healthcare-api-build
# uses: docker build -f services/user/healthcare-api/Dockerfile -t intelluxe/healthcare-api:latest services/user
```

- Rebuild with no cache
```bash
make healthcare-api-rebuild
```

- Stop and remove container
```bash
make healthcare-api-stop
```

- View logs (last 50 lines)
```bash
make healthcare-api-logs
```

- Health and status checks
```bash
make healthcare-api-health
make healthcare-api-status
make healthcare-api-test   # checks /docs and /health
```

- Restart (interactive menu shortcut)
```bash
make healthcare-api
# This routes through scripts/bootstrap.sh to restart the Healthcare API service.
```

For orchestrated networking and environment, use the provided Make targets and the service config at:
- [services/user/healthcare-api/healthcare-api.conf](services/user/healthcare-api/healthcare-api.conf)
- Global env template: [.env.example](.env.example)

---

## What to Look At (Code Tour)

- Makefile
  - Rich task surface for dev, quality, and service lifecycle commands
  - Healthcare API targets cover build, test, health, logs, and restart flows

- services/ (and [services/README.md](services/README.md))
  - Declarative `.conf` format for containerized services
  - Health checks, network modes, explicit capabilities, and setup requirements

- .claude/, [CLAUDE.md](CLAUDE.md), [CLAUDE_AGENTS.md](CLAUDE_AGENTS.md)
  - How I document agent roles, triggers, and safety/compliance-aware workflows
  - Patterns for repeatable, auditable automation

- .github/, .pre-commit-config.yaml, .flake8, mypy.ini, pyproject.toml
  - CI/CD and local quality gates (typing, linting, formatting)

- tests/, test/
  - Testing harness and structure (focus on reproducibility and clarity)

- .env.example
  - Secure-by-default environment variables and operational toggles

---

## Tech Stack

- Languages: Python (FastAPI patterns), Bash
- Runtime/Infra: Docker (declarative service config), optional Traefik/Redis/Postgres patterns
- Tooling: Make, pre-commit, flake8, mypy, pytest
- Docs & Agents: Structured agent patterns in `.claude/` and `CLAUDE*.md`

---

## Design Principles

- Privacy-first and on‑prem capable
- Declarative configuration for reproducibility
- Strong defaults (health checks, explicit permissions, minimal caps)
- Testable infrastructure and developer ergonomics
- Clear separation of service concerns and responsibilities

---

## Attributions

This portfolio references and reuses open-source components. See [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) for acknowledgments and license information.

---

## Notes

- This is a public portfolio adaptation to demonstrate engineering approaches. It omits client-specific or clinical resources and is not intended for medical use.
- For a production deployment, you would harden, monitor, and tailor services to your environment (RBAC, secrets management, logging, backups, patching, network policies, etc.).
