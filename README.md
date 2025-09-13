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
  - See: `services/README.md`

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

# Option B: if you prefer uv
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

4) Optional: Try the declarative service pattern (Docker)
- Read [services/README.md](services/README.md) for the `.conf` format.
- Create a simple service config in `services/user/` (e.g., a small cache, dashboard, or proxy) using the documented keys (`image`, `port`, `volumes`, `env`, `healthcheck`, etc.).
- Start/stop via your container tooling or your own lightweight runner script; the point is to see how services are described declaratively and composed safely.

Note: This portfolio repo does not ship a production orchestrator; it demonstrates the patterns and composable configuration style.

---

## What to Look At (Code Tour)

- Makefile
  - Large task surface for dev, quality, and automation workflows
  - Illustrates how I encode repeatable operations for teams

- services/ (and services/README.md)
  - Declarative `.conf` format for containerized services
  - Health checks, network modes, explicit capabilities, and setup requirements

- .claude/, CLAUDE.md, CLAUDE_AGENTS.md
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
