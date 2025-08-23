# MCP Tools Design for ICD-10 and Billing Codes Integration

## Overview

This document outlines the design for integrating ICD-10 diagnostic codes and medical billing codes (CPT/HCPCS) into the Clinical Research Agent via MCP tools. The integration will provide comprehensive medical coding lookup capabilities to enhance clinical research and administrative support.

## Data Sources

### ICD-10 Diagnostic Codes
1. **Primary Source**: Clinical Tables NLM API
   - URL: https://clinicaltables.nlm.nih.gov/api/icd10cm/v3/search
   - Free, government-sponsored service
   - Up-to-date with 2025 ICD-10-CM codes
   - RESTful API with JSON responses

2. **Secondary Source**: WHO ICD API
   - URL: https://icd.who.int/icdapi
   - Official WHO international classification
   - Fallback for complex diagnostic queries

### Medical Billing Codes (CPT/HCPCS)
1. **Primary Source**: Clinical Tables NLM HCPCS API
   - URL: https://clinicaltables.nlm.nih.gov/api/hcpcs/v3/search
   - Free, government-sponsored service
   - Covers HCPCS Level II codes
   - RESTful API with JSON responses

2. **Data Limitation**: CPT codes are AMA-copyrighted
   - Free access limited to basic lookups
   - Comprehensive CPT access requires AMA licensing
   - Focus on HCPCS codes for full functionality

## MCP Tool Architecture

### Tool 1: search-icd10
**Purpose**: Search and lookup ICD-10 diagnostic codes

**Input Schema**:
```json
{
  "query": "string (required) - diagnostic term or code to search",
  "max_results": "integer (optional, default: 10) - maximum results to return",
  "exact_match": "boolean (optional, default: false) - require exact code match"
}
```

**Output Schema**:
```json
{
  "codes": [
    {
      "code": "string - ICD-10 code (e.g., 'E11.9')",
      "description": "string - full diagnostic description",
      "category": "string - disease category/chapter",
      "inclusion_notes": "array - additional coding guidance",
      "exclusion_notes": "array - coding exclusions",
      "source": "string - data source identifier"
    }
  ],
  "total_results": "integer - total available results",
  "search_query": "string - processed search query"
}
```

### Tool 2: search-billing-codes
**Purpose**: Search HCPCS and available billing/procedure codes

**Input Schema**:
```json
{
  "query": "string (required) - procedure term or code to search",
  "code_type": "string (optional: 'hcpcs', 'all') - type of codes to search",
  "max_results": "integer (optional, default: 10) - maximum results to return"
}
```

**Output Schema**:
```json
{
  "codes": [
    {
      "code": "string - billing code (e.g., 'A0021')",
      "description": "string - procedure/item description",
      "code_type": "string - 'HCPCS' or 'CPT' (limited)",
      "category": "string - procedure category",
      "coverage_notes": "string - Medicare/insurance coverage notes",
      "effective_date": "string - code effective date",
      "source": "string - data source identifier"
    }
  ],
  "total_results": "integer - total available results",
  "search_query": "string - processed search query"
}
```

### Tool 3: lookup-code-details
**Purpose**: Get detailed information for specific medical codes

**Input Schema**:
```json
{
  "code": "string (required) - specific medical code to lookup",
  "code_type": "string (required: 'icd10', 'hcpcs') - type of code"
}
```

**Output Schema**:
```json
{
  "code": "string - the requested code",
  "description": "string - detailed description",
  "related_codes": "array - related or similar codes",
  "clinical_guidance": "string - clinical usage notes",
  "billing_guidance": "string - billing and reimbursement notes",
  "last_updated": "string - last update timestamp",
  "source": "string - authoritative source"
}
```

## Implementation Plan

### Phase 1: Core MCP Tools Development
1. **Create MCP Server Extension**
   - Add new tools to existing healthcare-mcp service
   - Implement NLM API integrations
   - Add error handling and rate limiting

2. **Database Integration**
   - Create local cache tables for frequently accessed codes
   - Implement periodic sync with authoritative sources
   - Add full-text search capabilities

### Phase 2: Clinical Research Agent Integration
1. **Query Enhancement**
   - Integrate code lookup into medical reasoning pipeline
   - Add diagnostic code context to literature searches
   - Enable billing code analysis for procedure research

2. **Response Formatting**
   - Include relevant diagnostic codes in research summaries
   - Link procedures to appropriate billing codes
   - Provide clinical coding guidance in responses

### Phase 3: Advanced Features
1. **Code Validation**
   - Validate code combinations and hierarchies
   - Check for coding conflicts and recommendations
   - Provide coding best practices

2. **Integration with Existing Tools**
   - Link ICD-10 codes with PubMed research
   - Connect billing codes with FDA drug information
   - Cross-reference codes with clinical trials

## Technical Architecture

### MCP Tool Implementation Structure
```
services/user/healthcare-mcp/
├── tools/
│   ├── medical_codes/
│   │   ├── __init__.py
│   │   ├── icd10_lookup.py
│   │   ├── billing_codes.py
│   │   └── code_validator.py
│   └── ...
├── cache/
│   ├── icd10_cache.py
│   └── billing_cache.py
└── ...
```

### Database Schema (PostgreSQL)
```sql
-- ICD-10 codes cache
CREATE TABLE icd10_codes (
    code VARCHAR(10) PRIMARY KEY,
    description TEXT NOT NULL,
    category VARCHAR(100),
    chapter VARCHAR(100),
    inclusion_notes JSONB,
    exclusion_notes JSONB,
    last_updated TIMESTAMP DEFAULT NOW()
);

-- HCPCS codes cache
CREATE TABLE hcpcs_codes (
    code VARCHAR(10) PRIMARY KEY,
    description TEXT NOT NULL,
    code_type VARCHAR(20),
    category VARCHAR(100),
    coverage_notes TEXT,
    effective_date DATE,
    last_updated TIMESTAMP DEFAULT NOW()
);

-- Full-text search indices
CREATE INDEX idx_icd10_description_fts ON icd10_codes USING gin(to_tsvector('english', description));
CREATE INDEX idx_hcpcs_description_fts ON hcpcs_codes USING gin(to_tsvector('english', description));
```

### API Integration Strategy
1. **Rate Limiting**: Respect API limits with intelligent caching
2. **Error Handling**: Graceful degradation when APIs are unavailable
3. **Data Quality**: Validate and sanitize all external data
4. **Monitoring**: Track API usage and performance metrics

## Clinical Research Agent Enhancements

### Query Processing Enhancements
1. **Code Detection**: Automatically detect medical codes in queries
2. **Context Expansion**: Use codes to expand search contexts
3. **Validation**: Verify code accuracy and current validity

### Response Enhancement
1. **Code Integration**: Include relevant codes in literature summaries
2. **Clinical Guidance**: Provide coding best practices
3. **Cross-References**: Link codes with research findings

### Conversation Memory
1. **Code History**: Track discussed codes per session
2. **Related Lookups**: Suggest related codes for follow-ups
3. **Validation Cache**: Remember validated code combinations

## Compliance and Safety

### HIPAA Compliance
- No PHI stored in code lookups
- Audit logging for all code access
- Secure API communications (HTTPS)

### Medical Disclaimers
- Clear disclaimers about coding guidance vs. medical advice
- Emphasis on administrative support only
- Requirement for professional coding verification

### Data Governance
- Regular updates from authoritative sources
- Version tracking for code changes
- Change notifications for deprecated codes

## Testing Strategy

### Unit Tests
- API integration tests with mock responses
- Code validation logic tests
- Error handling scenarios

### Integration Tests
- End-to-end MCP tool functionality
- Clinical research agent integration
- Database performance under load

### Validation Tests
- Code accuracy against official sources
- Search relevance and ranking
- Response time performance

## Future Enhancements

### Advanced Code Intelligence
1. **AI-Powered Code Suggestion**: Use LLMs to suggest appropriate codes
2. **Code Hierarchy Navigation**: Visual navigation of code relationships
3. **Coding Pattern Recognition**: Learn from usage patterns

### Integration Expansion
1. **DRG Codes**: Add Diagnosis-Related Group codes
2. **NDC Codes**: National Drug Code integration
3. **SNOMED CT**: Clinical terminology integration

This design provides a solid foundation for medical coding integration while maintaining the healthcare compliance and safety standards required for the Intelluxe AI system.