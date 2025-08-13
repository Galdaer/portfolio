# Medical Search Agent Implementation Playbook

Purpose: Implement the medical_search_agent with MCP-first sourcing, robust tests, and clear diagnostics. Avoid medical liability by sourcing all medical content from authoritative MCP tools only.

## Core Principles
- MCP-first: All medical content comes from MCP tools (PubMed, clinical databases). No hardcoded medical facts.
- LLM for text only: Use LLM for parsing/formatting, never for medical knowledge.
- Fail fast: If MCP tools unavailable, return clear error with disclaimers.
- Logging and metrics: Use healthcare_logger with trace_id; collect counters where helpful.

## Minimal Contract
- Input: { message: str, format: 'human' | 'json' }
- Output: { information_sources: [], related_conditions: [], search_confidence: number, disclaimers: string[] }
- Errors: { success: false, error: string }

## Implementation Steps
1. Validation
   - _validate_medical_query(message): basic checks, redact PHI from logs.
2. Concept extraction
   - _extract_medical_concepts(message): SciSpacy BIONLP13CG; return entity spans/types.
3. MCP discovery
   - Ensure MCP client initializes; list tools; assert required tools exist (e.g., pubmed_search, mesh_lookup).
4. Searches (MCP-only)
   - _search_condition_information(): structured query via MCP, returns condition summaries with citations.
   - _search_clinical_references(): PubMed queries with date filters; return articles with PMID, title, url.
   - _search_drug_information(): Drug databases (dosage info excluded; stick to indications/interactions summaries).
5. Evidence assessment
   - _determine_evidence_level(item): prioritize systematic reviews, RCTs; de-prioritize editorials.
   - _rank_sources_by_evidence(items): combine relevance + evidence.
6. Response
   - Aggregate, dedupe sources; compute search_confidence from source quality and agreement.
   - Include medical disclaimers always.

## Testing Strategy
- Unit tests
  - Concept extraction returns expected entity types for sample text.
  - Ranking function orders RCT > observational > case reports > editorials.
- Integration tests
  - Probe MCP for tools, perform a short PubMed search, assert non-empty results.
  - Error path when MCP unavailable returns clear message, no medical content.
- Logging tests
  - Ensure no PHI in logs; include trace_id, timings.

## Diagnostics & Observability
- Add structured logs at each stage: validation, extraction, tool selection, calls, result normalization, ranking.
- Timeouts per external call (e.g., 20–45s) with context on failures.
- Metrics counters: agent:metrics:medical_search:{stage}:count (optional, Redis-backed).

## Edge Cases
- Empty/ambiguous queries → return guidance and disclaimers.
- Large result sets → cap and page; return top-N with reason codes.
- Timeout/temporary errors → partial results with warnings.

## Compliance
- No medical advice. Administrative/documentation support only.
- Provide evidence and citations; include disclaimers.
