# Medical Literature URL Generation Patterns

Purpose: Standardized patterns for generating proper URLs and links for medical literature sources based on database schema fields and data source types.

## Core Principles

**Database Schema-First Approach**: Always use actual database fields (pmid, doi, nct_id, ndc) to generate appropriate URLs for different medical data sources.

**Data Source-Specific URLs**: Different medical databases require different URL patterns - DOI for journal articles, ClinicalTrials.gov for studies, DailyMed for FDA drugs.

**Progressive Fallback**: Use preferred URL types (DOI) with fallbacks to alternative URLs (PubMed abstracts) when preferred identifiers unavailable.

## Database Schema Awareness

### PubMed Articles Schema
```python
# Database fields: pmid, doi, title, abstract, authors, journal, publication_date
# URL Priority: DOI (preferred) → PubMed PMID (fallback)

def generate_pubmed_url(article_data: Dict[str, Any]) -> str:
    if article_data.get("doi"):
        return f"https://doi.org/{article_data['doi']}"  # Journal article directly
    elif article_data.get("pmid"):
        return f"https://pubmed.ncbi.nlm.nih.gov/{article_data['pmid']}/"  # Abstract only
    return None
```

### Clinical Trials Schema
```python
# Database fields: nct_id, title, status, phase, conditions, intervention
# URL Pattern: ClinicalTrials.gov study pages

def generate_clinical_trial_url(trial_data: Dict[str, Any]) -> str:
    if trial_data.get("nct_id"):
        return f"https://clinicaltrials.gov/study/{trial_data['nct_id']}"
    return None
```

### FDA Drug Information Schema
```python
# Database fields: ndc, name, generic_name, manufacturer, approval_date
# URL Pattern: DailyMed drug information pages

def generate_fda_drug_url(drug_data: Dict[str, Any]) -> str:
    if drug_data.get("ndc"):
        return f"https://dailymed.nlm.nih.gov/dailymed/search.cfm?labeltype=all&query={drug_data['ndc']}"
    elif drug_data.get("name"):
        return f"https://dailymed.nlm.nih.gov/dailymed/search.cfm?labeltype=all&query={drug_data['name']}"
    return None
```

## Universal URL Generation Pattern

### Centralized URL Utilities
```python
def generate_source_url(source_type: str, source_data: Dict[str, Any]) -> Optional[str]:
    """Generate appropriate URL based on source type and available data"""
    url_generators = {
        "pubmed": generate_pubmed_url,
        "clinical_trial": generate_clinical_trial_url, 
        "fda_drug": generate_fda_drug_url
    }
    
    generator = url_generators.get(source_type)
    return generator(source_data) if generator else None

def format_source_for_display(source_type: str, source_data: Dict[str, Any]) -> Dict[str, Any]:
    """Format source data for user-friendly display"""
    url = generate_source_url(source_type, source_data)
    
    return {
        "title": source_data.get("title", "Untitled"),
        "url": url,
        "source_type": source_type,
        "identifier": get_primary_identifier(source_type, source_data),
        "description": generate_source_description(source_type, source_data)
    }
```

## Source Creation Integration

### Medical Search Agent Integration
```python
# ✅ CORRECT: Database schema-aware source creation
def create_medical_source(result_data: Dict[str, Any], source_type: str) -> Dict[str, Any]:
    """Create medical literature source with proper URLs and database fields"""
    source = {
        "title": result_data.get("title", ""),
        "summary": result_data.get("abstract", result_data.get("description", "")),
        "url": generate_source_url(source_type, result_data),
        "source_type": source_type,
        "evidence_level": determine_evidence_level(result_data),
        "publication_date": result_data.get("publication_date", ""),
    }
    
    # Add source-specific database fields
    if source_type == "pubmed":
        source.update({
            "pmid": result_data.get("pmid"),
            "doi": result_data.get("doi"),
            "authors": result_data.get("authors", []),
            "journal": result_data.get("journal", "")
        })
    elif source_type == "clinical_trial":
        source.update({
            "nct_id": result_data.get("nct_id"),
            "status": result_data.get("status"),
            "phase": result_data.get("phase"),
            "conditions": result_data.get("conditions", [])
        })
    elif source_type == "fda_drug":
        source.update({
            "ndc": result_data.get("ndc"),
            "generic_name": result_data.get("generic_name"),
            "manufacturer": result_data.get("manufacturer")
        })
    
    return source
```

## Common Anti-Patterns

### ❌ AVOID: Hardcoded URL Patterns
```python
# ❌ WRONG: Ignores actual data source and database schema
def bad_url_generation(pmid: str) -> str:
    return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"  # Always PubMed abstract
```

### ❌ AVOID: Generic URLs Without Source Context
```python
# ❌ WRONG: Doesn't consider data source differences
def bad_generic_url(identifier: str) -> str:
    return f"https://example.com/search?q={identifier}"  # Not source-specific
```

### ✅ CORRECT: Schema-Aware URL Generation
```python
# ✅ CORRECT: Uses database schema and data source awareness
def generate_medical_literature_url(source_data: Dict[str, Any]) -> str:
    source_type = determine_source_type(source_data)
    return generate_source_url(source_type, source_data)
```

## Testing Patterns

### URL Generation Validation
```python
def test_url_generation_patterns():
    """Test URL generation for different medical data sources"""
    # Test PubMed DOI preference
    pubmed_data = {"pmid": "12345", "doi": "10.1000/example.doi"}
    url = generate_pubmed_url(pubmed_data)
    assert url.startswith("https://doi.org/")
    
    # Test Clinical Trials NCT ID
    trial_data = {"nct_id": "NCT12345678", "title": "Example Study"}
    url = generate_clinical_trial_url(trial_data)
    assert "clinicaltrials.gov/study/NCT12345678" in url
    
    # Test FDA Drug NDC
    drug_data = {"ndc": "12345-678-90", "name": "Example Drug"}
    url = generate_fda_drug_url(drug_data)
    assert "dailymed.nlm.nih.gov" in url
```

## Compliance Considerations

- **Link Reliability**: DOI links preferred over institutional URLs for long-term access
- **Medical Disclaimers**: All generated URLs should be accompanied by appropriate disclaimers
- **Source Attribution**: Always include proper source type and identifier information
- **Fallback Handling**: Graceful degradation when preferred identifiers unavailable

## Integration Points

- **Medical Search Agent**: Source creation with database field population
- **MCP Result Processing**: Transform raw tool results using URL utilities
- **Conversational Response**: Include formatted links in user-friendly summaries
- **Database Persistence**: Store generated URLs with source records for caching
