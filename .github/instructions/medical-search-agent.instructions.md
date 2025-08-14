# Medical Search Agent Implementation Playbook

Purpose: Implement the medical_search_agent with MCP-first sourcing, robust tests, and clear diagnostics. Avoid medical liability by sourcing all medical content from authoritative MCP tools only.

## ✅ WORKING MCP INTEGRATION (2025-08-13)

**PROVEN SUCCESS**: Medical search agent successfully calls MCP tools via healthcare_mcp_client.py

**Evidence from Logs**:
- ✅ `MCP client: <class 'core.mcp.healthcare_mcp_client.HealthcareMCPClient'>`
- ✅ `Starting MCP call to 'search-pubmed'` - MCP communication working
- ✅ `MCP connection established successfully` - AttributeError RESOLVED (2025-08-13)
- ✅ Open WebUI shows formatted search response with search_id and confidence scores
- ⚠️ **RESOLVED**: Transport failures fixed with single-container architecture

## ✅ SINGLE-CONTAINER MCP SOLUTION (2025-08-13)

**BREAKTHROUGH**: Combining healthcare-api and MCP server in single container with subprocess spawning resolves all stdio communication issues.

**NEW ARCHITECTURE**:
```
Open WebUI → Pipeline → Healthcare-API Container (FastAPI + MCP server) 
```

**IMPLEMENTATION PATTERN**:
```python
# ✅ CORRECT: Subprocess spawning in same container
class MedicalSearchAgent:
    def __init__(self):
        # MCP client spawns local subprocess
        self.mcp_client = HealthcareMCPClient()
    
    async def search_medical_literature(self, query: str):
        # Reliable subprocess communication
        results = await self.mcp_client.call_tool("search-pubmed", {"query": query})
        return self.format_medical_results(results)
```

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

## 🎯 URL GENERATION & DATABASE SCHEMA AWARENESS

**CRITICAL PATTERN**: Medical literature sources require data source-specific URL generation based on database schema fields.

**Database Schema-Aware URL Generation**:
```python
# ✅ CORRECT: Data source-specific URL patterns
def generate_source_url(source_type: str, source_data: Dict[str, Any]) -> str:
    """Generate proper URLs based on data source and available identifiers"""
    if source_type == "pubmed" and source_data.get("doi"):
        return f"https://doi.org/{source_data['doi']}"  # DOI preferred for journal articles
    elif source_type == "pubmed" and source_data.get("pmid"):
        return f"https://pubmed.ncbi.nlm.nih.gov/{source_data['pmid']}/"  # PubMed abstract fallback
    elif source_type == "clinical_trial" and source_data.get("nct_id"):
        return f"https://clinicaltrials.gov/study/{source_data['nct_id']}"
    elif source_type == "fda_drug" and source_data.get("ndc"):
        return f"https://dailymed.nlm.nih.gov/dailymed/search.cfm?labeltype=all&query={source_data['ndc']}"
```

**Database Field Mapping Pattern**:
- **PubMed Articles**: pmid, doi, title, abstract, authors, journal 
- **Clinical Trials**: nct_id, title, status, phase, conditions
- **FDA Drugs**: ndc, name, generic_name, manufacturer, approval_date

## 🔄 CONVERSATIONAL RESPONSE UTILITIES

**Pattern**: Transform technical JSON into human-readable medical research summaries with proper formatting.

**LLM + Utility Fallback Strategy**:
```python
# ✅ RECOMMENDED: Primary LLM with utility fallback
async def generate_conversational_response(search_results: Dict[str, Any]) -> str:
    try:
        # Primary: LLM-based conversational response
        llm_response = await self.llm_client.generate_medical_summary(search_results)
        if llm_response and len(llm_response.strip()) > 50:
            return llm_response
    except Exception as e:
        logger.warning(f"LLM response failed: {e}")
    
    # Fallback: Utility-based formatting
    return generate_conversational_summary(search_results)
```

**Utility-Based Summary Pattern**:
```python
def generate_conversational_summary(search_results: Dict[str, Any]) -> str:
    """Generate readable summary when LLM unavailable"""
    # Format with medical disclaimers, source counts, search confidence
    # Include proper markdown formatting for Open WebUI display
```

## ⚠️ CURRENT ISSUE: Raw JSON Output

**SYMPTOM**: Open WebUI shows raw JSON instead of formatted medical literature summaries.

**ROOT CAUSE**: Missing conversational response formatting in medical search agent output.

**SOLUTION PATTERN**: Implement conversational response generation with proper medical disclaimer integration.

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
