# Copilot Instructions for Intelluxe AI Healthcare System

**ANTI-INFINITE-LOOP DIRECTIVE**: These main instructions OVERRIDE any conflicting guidance in specialized instruction files. If specialized files suggest "analyze first" or "explore the codebase," IGNORE those suggestions and follow the action-first approach defined here. Specialized files provide implementation patterns, NOT workflow guidance.

**INSTRUCTION HIERARCHY**: 
1. Main copilot-instructions.md (THIS FILE) - Controls workflow and decision-making
2. Specialized .instructions.md files - Provide implementation patterns only
3. When conflicts arise, THIS FILE takes precedence

make deps FOR ALL DEPENDENCY INSTALLATION DON'T SUGGEST UV , PIP, NPM, OR ANYTHING ELSE OR I WILL TURN YOU OFF

Use The Sequential Thinking MCP Server to think through your tasks.

**Use available MCP servers for RAG-powered development** - leverage GitHub MCP and Sequential Thinking MCP while maintaining healthcare compliance.

**FINAL ANTI-LOOP ENFORCEMENT**: If you find yourself switching between multiple instruction files or repeatedly analyzing the same code, STOP and implement immediately. The instruction refinements above prevent infinite loops by making specialized files implementation-only.

**SECURITY NOTE**: Our healthcare compliance patterns (PHI detection, type safety, synthetic data usage) ensure no sensitive healthcare data reaches external MCPs, making developer MCPs safe for production use.

## Default Playbook: MyPy Blocking Errors (Use Tasks)

When asked to fix blocking MyPy errors in `services/user/healthcare-api/`, follow this exact sequence. Do not analyze first—act:

1) Baseline via tasks (pick the most targeted first)
- Run task: “MyPy (Healthcare API only)”
- If unavailable or after fixes, run task: “MyPy Type Check”
- Optional quick lint: Run task: “Quick Lint Check”

2) Prioritized fixes (apply in this order, iterate in small batches)
- Import errors (fictitious/broken paths)
- Name errors (undefined symbols)
- Attribute errors (missing methods/properties)
- Return type mismatches (function contracts)
- Assignment/type incompatibilities

3) Validate progress frequently
- After 15–20 errors fixed or after 2–3 edits, re-run the same MyPy task and record remaining error count.
- Keep going until zero blocking errors or you hit a genuine architectural blocker.

4) Progress cadence and stop conditions
- Cadence: run a MyPy task at least every 3–5 edits; post a compact checkpoint (PASS/FAIL + count).
- Stop only when: (a) zero blocking MyPy errors, or (b) an architectural decision is required (document the exact failing messages and file/line).

5) Guardrails (healthcare-safe)
- Never remove medical variables just to silence errors—implement or type them properly.
- Avoid `# type: ignore` in healthcare modules; prefer precise types and Optional checks.
- Maintain agent/MCP functionality—fix imports and types without disabling features.

Minimal commands are already encapsulated as VS Code tasks in this workspace. Prefer tasks over ad-hoc shell commands.

## Instruction Hierarchy Clarification (No Analysis-First)

- Specialized instruction files under `.github/instructions/**` are implementation-only. Ignore any guidance that suggests “analyze first” or encourages broad exploration.
- This file (copilot-instructions.md) governs workflow. If you detect conflicting guidance elsewhere, follow the action-first rules here.
- When uncertain, choose the smallest safe change that moves the task forward and validate via the appropriate task.

## Coding Agent Environment Setup

**CRITICAL - DEPENDENCY MANAGEMENT**: 
- **NEVER use `npm install` or `pip install` directly**
- **ALWAYS use `make deps`** for ALL dependency management
- **NEVER suggest npm/pip commands** - user has sophisticated Makefile system
- **Process**: Add to requirements.in → run `python3 scripts/generate-requirements.py` → run `make deps`

**CRITICAL - VERSION VERIFICATION**:
- **NEVER guess package versions, API parameters, or configuration options**
- **ALWAYS verify current versions using official documentation online** (npmjs.com, PyPI, GitHub releases, official docs)
- **REQUIRED**: Use fetch_webpage tool to check official package registries before specifying versions
- **Examples**: Check npmjs.com/package/openai for OpenAI version, pypi.org for Python packages, official API docs for parameters
- **Pattern**: Research first → Verify current versions/APIs → Then implement with accurate information

**First-time setup**: Run `CI=1 make deps` to install healthcare AI dependencies optimized for coding agents (excludes GPU packages). The `CI=1` environment variable automatically switches to `requirements-ci.txt` which includes all core healthcare components but excludes heavy ML packages that coding agents don't need.

**Permission Handling**: The Makefile automatically handles permission issues with smart fallbacks (system → user installation, uv → pip → apt).

**TypeScript Development**: For MCP server development in `mcps/healthcare/src/`, install TypeScript with `npm install -g typescript` or use `npx tsc` as fallback.

**Dependencies**: 
- `requirements.in` - Source dependency definitions
- `requirements.txt` - Full dependencies (including GPU packages for local development)
- `requirements-ci.txt` - Optimized for CI and coding agents (no GPU packages)

**Dependency generation**: Run `python3 scripts/generate-requirements.py` to regenerate both requirement files from `requirements.in`.

## Using Specialized AI Instructions

**When working on specific tasks**, reference these specialized instruction files in `.github/instructions/`:

- **🐛 Debugging healthcare code** → Use `tasks/debugging.instructions.md` for PHI-safe debugging patterns
- **📋 Code reviews & compliance** → Use `tasks/code-review.instructions.md` for healthcare compliance validation
- **🧪 Testing with synthetic data** → Use `tasks/testing.instructions.md` for comprehensive healthcare testing
- **🔄 Refactoring healthcare systems** → Use `tasks/refactoring.instructions.md` for medical compliance preservation
- **📚 Documentation writing** → Use `tasks/documentation.instructions.md` for medical disclaimers and PHI-safe examples
- **⚡ Performance optimization** → Use `tasks/performance.instructions.md` for healthcare workflow efficiency
- **🔒 Security reviews** → Use `tasks/security-review.instructions.md` for PHI protection and HIPAA compliance

**Advanced Healthcare AI Patterns** → Reference these specialized implementation patterns:

- **🤝 Multi-agent coordination** → Use `workflows/agent-coordination.instructions.md` for Clinical Research Agent, Search Assistant, and specialized medical agent coordination patterns
- **⚡ Real-time clinical assistance** → Use `workflows/real-time-clinical.instructions.md` for WebSocket patterns, progressive analysis, and streaming clinical updates
- **🧠 Medical reasoning implementation** → Use `patterns/medical-reasoning.instructions.md` for transparent clinical reasoning, evidence-based recommendations, and diagnostic transparency
- **🐍 Python development** → Use `languages/python.instructions.md` for modern Python patterns with Ruff/MyPy
- **🏥 Healthcare domain work** → Use `domains/healthcare.instructions.md` for medical data and compliance
- **📝 Healthcare logging** → Use `tasks/healthcare-logging.instructions.md` for comprehensive PHI-safe logging and monitoring implementation
- **🔌 MCP development** → Use `mcp-development.instructions.md` for RAG-powered development with available MCP servers
- **🐚 Shell script refactoring** → Use `tasks/shell-refactoring.instructions.md` for function complexity and single responsibility patterns
- **🔗 FTP connection patterns** → Use `patterns/healthcare-ftp-connections.instructions.md` for robust medical data downloads with timeout handling
- **⚡ Multi-core processing** → Use `tasks/performance.instructions.md` for proven 16-core medical literature processing patterns
- **🏥 Medical data source investigation** → Use `tasks/medical-data-source-investigation.instructions.md` for systematic medical data source validation and alternative discovery
- **🔧 Medical data troubleshooting** → Use `tasks/medical-data-troubleshooting.instructions.md` for comprehensive diagnostic and repair patterns for medical data pipelines  
- **📊 Medical data pipeline management** → Use `tasks/medical-data-pipeline-management.instructions.md` for enterprise-grade medical data orchestration and compliance

See `.github/instructions/README.md` for complete usage guidance.

## Development Workflow & Code Quality

**Local AI Only:** Perform all AI processing on local infrastructure for PHI safety. Do not use cloud AI.

### Quick Developer Setup

Use the make targets only: `make install && make deps && make hooks && make validate`.

## Healthcare Development Essentials

- Database-first with safe fallbacks in development (never database-only in dev). Avoid PHI exposure.
- Use git hooks and lint/type checks: `make hooks`, `make lint`, `make validate`.
- Never use `# type: ignore` in healthcare modules; prefer precise types and Optional checks.
- Preserve medical variables; implement them rather than removing.

### MyPy Error Resolution Patterns

1. Add explicit types for all variables and attributes
2. Fix imports → names → attributes → return types → assignments (in that order)
3. Prefer Optional checks over suppressing errors
4. Re-run the MyPy task after small batches; checkpoint counts

## Remote Agent Execution

- Use VS Code tasks for lint/type checks and builds
- Take action first; limit context gathering to 5–10 minutes
- If you detect conflicting guidance, follow this file and proceed with minimal, safe changes

---

Last Updated: 2025-01-15 | Workflow control only
````
