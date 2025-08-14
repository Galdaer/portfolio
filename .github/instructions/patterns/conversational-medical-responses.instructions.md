# Conversational Medical Response Generation Patterns

Purpose: Transform technical JSON medical search results into human-readable, conversational responses for healthcare AI interfaces.

## Core Principles

**Intent-Based Response Formatting**: Different query intents trigger different response formats and source selections.

**Multi-Source Query Patterns**: Configure source selection based on query intent - articles (PubMed focus), studies (PubMed + ClinicalTrials), treatments (all sources).

**Configurable Response Templates**: YAML-driven templates for structured articles vs conversational summaries.

**LLM + Utility Fallback**: Primary LLM-based conversational generation with utility-based fallback for reliability.

**Medical Disclaimers Required**: All conversational responses must include appropriate healthcare disclaimers.

**Evidence-Based Formatting**: Present medical literature with clear source attribution and evidence levels.

**User-Friendly Display**: Format for Open WebUI and similar interfaces with proper markdown and structure.

## Intent-Based Query Classification

### Query Intent Architecture
```python
class QueryIntentClassifier:
    def __init__(self, config_path: str):
        self.patterns = self.load_query_patterns(config_path)
    
    def classify_query(self, query: str) -> QueryIntent:
        """Classify user query to determine response format and sources"""
        query_lower = query.lower()
        
        # Check for specific intent patterns
        for intent_name, pattern_config in self.patterns.items():
            if self.matches_pattern(query_lower, pattern_config["keywords"]):
                return QueryIntent(
                    intent=intent_name,
                    response_format=pattern_config["response_format"],
                    primary_sources=pattern_config["primary_sources"],
                    max_results=pattern_config["max_results"],
                    include_abstracts=pattern_config.get("include_abstracts", True)
                )
        
        # Default to conversational information format
        return QueryIntent.default_information()

class QueryIntent:
    intent: str
    response_format: str  # "structured_articles" | "structured_studies" | "structured_treatments" | "conversational_summary"
    primary_sources: List[str]  # ["pubmed"] | ["clinical_trials"] | ["fda_drugs"] | ["pubmed", "trials", "drugs"]
    max_results: int
    include_abstracts: bool
```

### Configuration-Driven Response Patterns
```yaml
# services/user/healthcare-api/config/medical_query_patterns.yaml
query_patterns:
  articles_request:
    keywords: ["articles", "papers", "publications", "literature", "research papers"]
    response_format: "structured_articles"
    primary_sources: ["pubmed"]
    max_results: 10
    include_abstracts: true
    template: "academic_article_list"
    
  studies_request:
    keywords: ["studies", "clinical studies", "research studies", "trials"]
    response_format: "structured_studies" 
    primary_sources: ["pubmed", "clinical_trials"]
    max_results: 8
    include_abstracts: true
    template: "mixed_studies_list"
    
  treatments_request:
    keywords: ["treatments", "medications", "drugs", "therapies", "interventions"]
    response_format: "structured_treatments"
    primary_sources: ["pubmed", "clinical_trials", "fda_drugs"]
    max_results: 12
    include_abstracts: false
    template: "treatment_options_list"
    
  clinical_trials_request:
    keywords: ["clinical trials", "ongoing trials", "recruiting trials", "trial status"]
    response_format: "structured_trials"
    primary_sources: ["clinical_trials"]
    max_results: 15
    include_abstracts: false
    template: "clinical_trials_list"
    
  drug_information_request:
    keywords: ["drug information", "medication details", "pharmaceutical", "drug safety"]
    response_format: "structured_drugs"
    primary_sources: ["fda_drugs", "pubmed"]
    max_results: 8
    include_abstracts: true
    template: "drug_information_list"
    
  information_request:
    keywords: ["information", "recent", "latest", "updates", "overview", "summary"]
    response_format: "conversational_summary"
    primary_sources: ["pubmed", "clinical_trials", "fda_drugs"]
    max_results: 15
    include_abstracts: false
    template: "conversational_overview"
```

## Response Format Templates

### Template-Based Response Generation
```python
class ResponseTemplateManager:
    def __init__(self, template_config: Dict[str, Any]):
        self.templates = template_config
    
    def generate_response(
        self, 
        query_intent: QueryIntent, 
        search_results: Dict[str, Any]
    ) -> str:
        """Generate response using appropriate template for intent"""
        template_name = query_intent.template
        template_func = getattr(self, f"format_{template_name}", self.format_conversational_overview)
        return template_func(search_results, query_intent)
```

### Structured Articles Template (PubMed Focus)
```python
def format_academic_article_list(self, results: Dict[str, Any], intent: QueryIntent) -> str:
    """Format for 'articles for cardiovascular health' queries"""
    sources = results.get("information_sources", [])[:intent.max_results]
    
    response_parts = [
        f"## 📚 Recent Articles on {extract_topic(results['search_query'])}",
        ""
    ]
    
    for i, source in enumerate(sources, 1):
        if source.get("source_type") == "pubmed" and source.get("doi"):
            response_parts.extend([
                f"### {i}. {source.get('title', 'Untitled Article')} ",
                f"**Authors:** {format_authors(source.get('authors', []))}",
                f"**Journal:** *{source.get('journal', 'Unknown Journal')}* ({source.get('publication_date', 'Unknown Date')})",
                f"**Abstract:** {truncate_text(source.get('summary', ''), 200)}",
                f"**Link:** [Full Article]({source.get('url')})",
                ""
            ])
    
    response_parts.extend(get_medical_disclaimers())
    return "\n".join(response_parts)
```

### Mixed Studies Template (PubMed + ClinicalTrials)
```python
def format_mixed_studies_list(self, results: Dict[str, Any], intent: QueryIntent) -> str:
    """Format for 'studies on cardiovascular health' queries"""
    sources = results.get("information_sources", [])[:intent.max_results]
    
    response_parts = [
        f"## 🔬 Research Studies on {extract_topic(results['search_query'])}",
        ""
    ]
    
    # Group by source type
    pubmed_studies = [s for s in sources if s.get("source_type") == "pubmed"]
    clinical_trials = [s for s in sources if s.get("source_type") == "clinical_trial"]
    
    if pubmed_studies:
        response_parts.extend([
            "### 📖 Published Research Studies",
            ""
        ])
        for study in pubmed_studies[:6]:
            response_parts.extend(format_study_entry(study))
    
    if clinical_trials:
        response_parts.extend([
            "### 🏥 Clinical Trials",
            ""
        ])
        for trial in clinical_trials[:6]:
            response_parts.extend(format_trial_entry(trial))
    
    response_parts.extend(get_medical_disclaimers())
    return "\n".join(response_parts)
```

### Treatment Options Template (All Sources)
```python
def format_treatment_options_list(self, results: Dict[str, Any], intent: QueryIntent) -> str:
    """Format for 'treatments for cardiovascular health' queries"""
    sources = results.get("information_sources", [])
    drug_info = results.get("drug_information", [])
    
    response_parts = [
        f"## 💊 Treatment Options for {extract_topic(results['search_query'])}",
        ""
    ]
    
    # Evidence-based treatments from literature
    treatment_studies = [s for s in sources if "treatment" in s.get("title", "").lower()]
    if treatment_studies:
        response_parts.extend([
            "### 📚 Evidence-Based Treatments",
            ""
        ])
        for study in treatment_studies[:5]:
            response_parts.extend(format_treatment_study(study))
    
    # Clinical trials for treatments
    treatment_trials = [s for s in sources if s.get("source_type") == "clinical_trial"]
    if treatment_trials:
        response_parts.extend([
            "### 🧪 Clinical Trials for New Treatments",
            ""
        ])
        for trial in treatment_trials[:4]:
            response_parts.extend(format_trial_entry(trial))
    
    # FDA-approved medications
    if drug_info:
        response_parts.extend([
            "### 💊 FDA-Approved Medications",
            ""
        ])
        for drug in drug_info[:5]:
            response_parts.extend(format_drug_entry(drug))
    
    response_parts.extend(get_medical_disclaimers())
    return "\n".join(response_parts)
```

```python
async def generate_conversational_response(
    search_results: Dict[str, Any], 
    user_query: str
) -> str:
    """Generate conversational medical research summary"""
    try:
        # Primary: LLM-based conversational response
        llm_prompt = create_medical_summary_prompt(search_results, user_query)
        llm_response = await self.llm_client.generate_response(llm_prompt)
        
        if llm_response and len(llm_response.strip()) > 50:
            return add_medical_disclaimers(llm_response)
            
    except Exception as e:
        logger.warning(f"LLM conversational response failed: {e}")
    
    # Fallback: Utility-based formatting
    return generate_conversational_summary(search_results, user_query)
```

### Utility-Based Fallback
```python
def generate_conversational_summary(
    search_results: Dict[str, Any], 
    user_query: str
) -> str:
    """Reliable utility-based conversational formatting"""
    summary_parts = []
    
    # Opening with query acknowledgment
    summary_parts.append(f"🏥 **Medical Search Results for:** {user_query}")
    summary_parts.append("")
    
    # Format information sources
    sources = search_results.get("information_sources", [])
    if sources:
        summary_parts.append("## 📚 **Key Research Findings:**")
        for source in sources[:5]:  # Limit to top 5
            formatted_source = format_source_for_conversation(source)
            summary_parts.append(formatted_source)
        summary_parts.append("")
    
    # Related conditions
    conditions = search_results.get("related_conditions", [])
    if conditions:
        summary_parts.append("## 🔍 **Related Medical Conditions:**")
        conditions_text = ", ".join(conditions[:10])
        summary_parts.append(f"• {conditions_text}")
        summary_parts.append("")
    
    # Drug information
    drugs = search_results.get("drug_information", [])
    if drugs:
        summary_parts.append("## 💊 **Related Medications:**")
        for drug in drugs[:3]:
            drug_summary = format_drug_for_conversation(drug)
            summary_parts.append(drug_summary)
        summary_parts.append("")
    
    # Search metadata
    confidence = search_results.get("search_confidence", 0.0)
    total_sources = search_results.get("total_sources", 0)
    summary_parts.append(f"**Search Quality:** {confidence:.1f}/10.0 confidence • {total_sources} sources reviewed")
    summary_parts.append("")
    
    # Medical disclaimers
    disclaimers = get_medical_disclaimers()
    summary_parts.extend(disclaimers)
    
    return "\n".join(summary_parts)
```

## Source Formatting Patterns

### Individual Source Formatting
```python
def format_source_for_conversation(source: Dict[str, Any]) -> str:
    """Format individual medical literature source for conversational display"""
    title = source.get("title", "Untitled Research")
    summary = source.get("summary", "No summary available")
    url = source.get("url", "")
    source_type = source.get("source_type", "unknown")
    evidence_level = source.get("evidence_level", "unknown")
    
    # Create formatted source entry
    source_parts = []
    
    # Title with link if available
    if url:
        source_parts.append(f"• **[{title}]({url})**")
    else:
        source_parts.append(f"• **{title}**")
    
    # Evidence level indicator
    evidence_indicator = get_evidence_indicator(evidence_level)
    source_parts.append(f"  {evidence_indicator} *{source_type.title()}*")
    
    # Summary (truncated for readability)
    truncated_summary = truncate_summary(summary, max_length=200)
    source_parts.append(f"  {truncated_summary}")
    
    return "\n".join(source_parts)

def get_evidence_indicator(evidence_level: str) -> str:
    """Get visual indicator for evidence quality"""
    indicators = {
        "systematic_review": "🏆",
        "randomized_controlled_trial": "🥇", 
        "observational_study": "🥈",
        "case_report": "🥉",
        "editorial": "📝",
        "unknown": "📄"
    }
    return indicators.get(evidence_level, "📄")
```

### Drug Information Formatting
```python
def format_drug_for_conversation(drug: Dict[str, Any]) -> str:
    """Format drug information for conversational display"""
    name = drug.get("name", "Unknown medication")
    generic_name = drug.get("generic_name", "")
    url = drug.get("url", "")
    
    if generic_name and generic_name != name:
        display_name = f"{name} ({generic_name})"
    else:
        display_name = name
    
    if url:
        return f"• **[{display_name}]({url})**"
    else:
        return f"• **{display_name}**"
```

## Medical Disclaimer Integration

### Standard Medical Disclaimers
```python
def get_medical_disclaimers() -> List[str]:
    """Get standard medical disclaimers for conversational responses"""
    return [
        "---",
        "⚠️ **Important Medical Disclaimer:**",
        "",
        "This information is provided for educational and research purposes only. It should not be used as a substitute for professional medical advice, diagnosis, or treatment. Always consult with qualified healthcare providers for medical decisions.",
        "",
        "The research findings presented here represent current scientific literature and may not reflect the most recent developments. Individual medical situations vary significantly."
    ]

def add_medical_disclaimers(response: str) -> str:
    """Add medical disclaimers to any conversational response"""
    disclaimers = get_medical_disclaimers()
    
    # Ensure spacing before disclaimers
    if not response.endswith("\n\n"):
        response += "\n\n"
    
    return response + "\n".join(disclaimers)
```

## LLM Prompt Engineering

### Medical Summary Prompt Template
```python
def create_medical_summary_prompt(
    search_results: Dict[str, Any], 
    user_query: str
) -> str:
    """Create LLM prompt for medical literature summarization"""
    
    prompt_parts = [
        "You are a medical research assistant helping to summarize scientific literature.",
        "",
        f"User Query: {user_query}",
        "",
        "Search Results to Summarize:",
        json.dumps(search_results, indent=2),
        "",
        "Instructions:",
        "1. Create a conversational, user-friendly summary of the research findings",
        "2. Use markdown formatting appropriate for web display",
        "3. Include source titles with links when available", 
        "4. Prioritize high-evidence sources (systematic reviews, RCTs)",
        "5. Keep medical terminology accessible but accurate",
        "6. Do NOT include medical disclaimers (they will be added separately)",
        "7. Structure with clear headings and bullet points",
        "8. Limit to 300-500 words for readability",
        "",
        "Generate a helpful, informative summary:"
    ]
    
    return "\n".join(prompt_parts)
```

## Error Handling Patterns

### Graceful Degradation
```python
def handle_empty_results(user_query: str) -> str:
    """Handle empty search results conversationally"""
    return f"""🔍 **Search Results for:** {user_query}

Unfortunately, I wasn't able to find specific research articles matching your query at this time. This could be due to:

• **Search terms**: Try more general medical terms or synonyms
• **Database connectivity**: Temporary issues with medical literature databases  
• **Query specificity**: Very specific queries may have limited research available

**Suggestions:**
• Rephrase using broader medical terminology
• Try searching for related conditions or symptoms
• Check back later if this appears to be a technical issue

{chr(10).join(get_medical_disclaimers())}"""

def handle_timeout_results(user_query: str, partial_results: Dict[str, Any]) -> str:
    """Handle timeout with partial results"""
    if partial_results.get("information_sources"):
        summary = generate_conversational_summary(partial_results, user_query)
        return f"{summary}\n\n⏱️ **Note:** Search timed out - showing partial results. Try a more specific query for faster results."
    else:
        return handle_empty_results(user_query)
```

## Testing Patterns

### Conversational Response Testing
```python
def test_conversational_response_generation():
    """Test conversational response formatting"""
    mock_results = {
        "information_sources": [
            {
                "title": "Cardiovascular Benefits of Exercise",
                "summary": "Exercise reduces heart disease risk by 30%",
                "url": "https://doi.org/10.1000/example",
                "evidence_level": "systematic_review"
            }
        ],
        "search_confidence": 8.5,
        "total_sources": 15
    }
    
    response = generate_conversational_summary(mock_results, "exercise heart health")
    
    # Verify conversational elements
    assert "🏥 **Medical Search Results" in response
    assert "## 📚 **Key Research Findings:**" in response
    assert "**Search Quality:**" in response
    assert "⚠️ **Important Medical Disclaimer:**" in response
    assert "[Cardiovascular Benefits of Exercise]" in response
```

## Integration with Medical Search Agent

### Router Integration Pattern
```python
# In medical search agent router
async def search_medical_literature_endpoint(request: SearchRequest):
    """Enhanced endpoint with conversational response"""
    # Perform medical literature search
    search_results = await agent.search_medical_literature(request.message)
    
    # Generate conversational response
    if request.format == "human":
        conversational_response = await generate_conversational_response(
            search_results, 
            request.message
        )
        return {"response": conversational_response, "raw_data": search_results}
    else:
        return {"result": search_results}
```

## Performance Considerations

- **LLM Timeouts**: Set reasonable timeouts (10-15s) for LLM calls
- **Fallback Reliability**: Utility-based formatting should never fail
- **Response Length**: Keep conversational responses under 1000 words
- **Caching**: Cache formatted responses for common queries when appropriate
- **Progressive Enhancement**: Start with utility formatting, enhance with LLM when available
