# LangChain Orchestrator (Healthcare API)

This service uses a LangChain-based orchestrator by default to handle `/process` requests with local-only models (Ollama) and MCP-backed medical tools.

Key behaviors
- Always-on medical_search presearch: Runs a short PubMed search first to guarantee citations, then executes the agent and merges sources.
- Citations and Sources: Extracts citations from tool outputs and appends a "Sources" section to the formatted response.
- PHI-safe: Local inference only; tools access authoritative medical sources via the Healthcare MCP.
- Resilient tool calls: MCP tools use light retry/backoff to reduce transient failures.

Configuration
Edit `config/orchestrator.yml` to tune behavior. Defaults are applied if keys are missing.

- routing.always_run_medical_search: boolean (default true)
- routing.presearch_max_results: integer (default 5)
- langchain.citations_max_display: integer (default 10)
- timeouts.per_agent_default: seconds (default 30)
- timeouts.per_agent_hard_cap: seconds (default 90)
- timeouts.tool_max_retries: integer (default 2)
- timeouts.tool_retry_base_delay: seconds (default 0.2)

Notes
- The agent currently defaults to the label `medical_search` and will expand to multi-agent routing in future iterations.
- No cloud AI is used; ensure Ollama is accessible (default http://localhost:11434) or set `OLLAMA_BASE_URL`.

OpenAPI/UI
- The `/process` endpoint accepts `show_sources: bool | null` per request. When `false`, the human-readable "Sources" section is omitted from `formatted_response`, while `result.citations` still contains structured citations.
