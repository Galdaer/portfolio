# Medical Literature Search Agent Instructions

## Core Contract (public output fields)
- formatted_summary: Required. Human-readable output rendered in UIs. Never omit; provide a safe fallback string on any internal error.
- information_sources: List[dict] of normalized article objects used to generate the summary.
- disclaimers: Standard medical disclaimers; administrative/educational, no medical advice.
- agent_type: "search" for consistency with downstream pipelines.

## Non-blocking instrumentation (lesson: 2025-08-14)
- Never let metrics or logging block user-visible results.
- Wrap metrics calls (incr/record_timing) with try/except and continue.
- Defer any best-effort telemetry to the very end or make it fire-and-forget.

## Resilient formatting pipeline
1) Classify intent via YAML patterns.
2) Execute literature search with bounded concurrency (Semaphore) and overall timeout (asyncio.wait_for).
3) Format using intent-aware template. If formatting throws, log and fall back to a minimal summary like: "Found N sources for 'query'".
4) Always populate formatted_summary even when search produced zero sources (communicate why: timeout, rejection of system prompt, etc.).

## Prompt injection and system-prompt rejection
- Reject Open WebUI system prompts (e.g., "Suggest 3-5 follow-up questions") with a safe disclaimer result instead of querying MCP.

## Source normalization rules
- Deduplicate by DOI/PMID.
- Prefer DOI link, fall back to PubMed or publisher URL.
- Keep author names intact (authors ≠ PHI). Do not sanitize authorship metadata.
- Include year, journal, and a brief abstract snippet when available.

## Concurrency and timeouts
- Use a bounded Semaphore for MCP calls (default 2) to avoid stdio contention.
- Enforce an overall search timeout; on timeout, return an empty sources list with a clear disclaimer explaining the timeout.

## Logging diagnostics
- Use clear DIAGNOSTIC markers around formatting, e.g.,
  - "DIAGNOSTIC: Starting response formatting..."
  - "DIAGNOSTIC: Response formatting completed successfully"
- Log preview of formatted_summary (first ~200 chars) and intent metadata to aid support.

## Error handling priorities
1) Patient/user experience: deliver a readable summary.
2) Safety: keep disclaimers and avoid medical advice.
3) Observability: log errors without leaking PHI.
4) Telemetry: do not block on metrics; best-effort only.

## Test checklist
- Produces formatted_summary for: normal query, zero results, timeout, system-prompt rejection, and formatting exception.
- Ensures author names are preserved and not treated as PHI.
- Guarantees agent_type and success fields are set consistently.
