# Conversational Medical Response Generation Patterns

Purpose: Transform technical JSON medical search results into human-readable, conversational responses for healthcare AI interfaces.

## Core Principles

**LLM + Utility Fallback**: Primary LLM-based conversational generation with utility-based fallback for reliability.

**Medical Disclaimers Required**: All conversational responses must include appropriate healthcare disclaimers.

**Evidence-Based Formatting**: Present medical literature with clear source attribution and evidence levels.

**User-Friendly Display**: Format for Open WebUI and similar interfaces with proper markdown and structure.

## LLM + Utility Fallback Pattern

### Primary LLM Strategy
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
