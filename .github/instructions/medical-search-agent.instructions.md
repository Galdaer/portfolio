# Medical Search Agent Implementation Playbook

Purpose: Implement the medical_search_agent with MCP-first sourcing, robust tests, and clear diagnostics. Avoid medical liability by sourcing all medical content from authoritative MCP tools only.

## ✅ WORKING MCP INTEGRATION (2025-08-13)

**PROVEN SUCCESS**: Medical search agent successfully calls MCP tools via healthcare_mcp_client.py

**Evidence from Logs**:
- ✅ `MCP client: <class 'core.mcp.healthcare_mcp_client.HealthcareMCPClient'>`
- ✅ `Starting MCP call to 'search-pubmed'` - MCP communication working
- ✅ `MCP connection established successfully` - AttributeError RESOLVED (2025-08-13)
- ✅ Open WebUI shows formatted search response with search_id and confidence scores
- ⚠️ **NEW ISSUE**: MCP transport failures "WriteUnixTransport closed=True" causing 0 results

**Current Issue**: MCP calls succeed but stdio transport layer unstable - timeouts result in empty responses.

## Core Principles (Validated)
- MCP-first: All medical content comes from MCP tools (PubMed, clinical databases). ✅ Working
- LLM for text only: Use LLM for parsing/formatting, never for medical knowledge. ✅ Implemented  
- Fail fast: If MCP tools unavailable, return clear error with disclaimers. ✅ Working
- Logging and metrics: Use healthcare_logger with trace_id; collect counters where helpful. ✅ Working

## Minimal Contract (Implemented)
- Input: { message: str, format: 'human' | 'json' } ✅ Working
- Output: { information_sources: [], related_conditions: [], search_confidence: number, disclaimers: string[] } ✅ Working
- Errors: { success: false, error: string } ✅ Working

## ⚠️ NEXT STEPS NEEDED

**CURRENT STATUS**: Raw MCP search results are returned but need human-readable formatting.

**Open WebUI Response Shows**:
```json
{
  "status": "success", 
  "result": {
    "success": true, 
    "search_id": "aeaf7930978b",
    "information_sources": [], 
    "search_confidence": 0.0,
    "disclaimers": ["Search request timed out after 25 seconds"],
    "total_sources": 0
  }
}
```

**NEXT AGENT TASKS**:
1. **Result Parsing**: Transform raw MCP tool results into readable medical literature summaries
2. **Timeout Optimization**: Increase PubMed API timeout or implement async result fetching  
3. **Response Formatting**: Convert technical JSON into human-friendly medical research summaries
4. **Error Handling**: Better user messages for timeouts vs actual failures

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
