# Medical Search Configuration Patterns

Purpose: YAML-driven configuration patterns for intent-based medical search with multi-source response formatting.

## Core Architecture

**Intent-Based Query Classification**: Different user intents (articles, studies, treatments, trials, drugs, information) trigger appropriate response formats and source selections.

**Multi-Source Integration**: PubMed articles, ClinicalTrials.gov studies, and FDA drug information with shared keyword patterns.

**Configurable Response Templates**: YAML configuration drives response formatting without hardcoded logic.

## Query Pattern Configuration

### Primary Configuration File
```yaml
# services/user/healthcare-api/config/medical_query_patterns.yaml
query_patterns:
  articles_request:
    keywords: ["articles", "papers", "publications", "literature", "research papers", "peer reviewed"]
    response_format: "structured_articles"
    primary_sources: ["pubmed"]
    max_results: 10
    include_abstracts: true
    template: "academic_article_list"
    description: "Academic articles and peer-reviewed research papers"
    
  studies_request:
    keywords: ["studies", "clinical studies", "research studies", "trials", "clinical research"]
    response_format: "structured_studies" 
    primary_sources: ["pubmed", "clinical_trials"]
    max_results: 8
    include_abstracts: true
    template: "mixed_studies_list"
    description: "Published studies and ongoing clinical research"
    
  treatments_request:
    keywords: ["treatments", "medications", "drugs", "therapies", "interventions", "therapeutic options"]
    response_format: "structured_treatments"
    primary_sources: ["pubmed", "clinical_trials", "fda_drugs"]
    max_results: 12
    include_abstracts: false
    template: "treatment_options_list"
    description: "Treatment options from all available sources"
    
  clinical_trials_request:
    keywords: ["clinical trials", "ongoing trials", "recruiting trials", "trial status", "study recruitment"]
    response_format: "structured_trials"
    primary_sources: ["clinical_trials"]
    max_results: 15
    include_abstracts: false
    template: "clinical_trials_list"
    description: "Active and recruiting clinical trials"
    
  drug_information_request:
    keywords: ["drug information", "medication details", "pharmaceutical", "drug safety", "side effects"]
    response_format: "structured_drugs"
    primary_sources: ["fda_drugs", "pubmed"]
    max_results: 8
    include_abstracts: true
    template: "drug_information_list"
    description: "FDA drug information and safety data"
    
  information_request:
    keywords: ["information", "recent", "latest", "updates", "overview", "summary", "what is", "tell me about"]
    response_format: "conversational_summary"
    primary_sources: ["pubmed", "clinical_trials", "fda_drugs"]
    max_results: 15
    include_abstracts: false
    template: "conversational_overview"
    description: "General information from multiple sources"

# Source-specific configurations
source_configurations:
  pubmed:
    default_max_results: 20
    preferred_evidence_levels: ["systematic_review", "randomized_controlled_trial", "meta_analysis"]
    include_abstracts: true
    url_preference: "doi"  # doi > pmid
    
  clinical_trials:
    default_max_results: 25
    status_filter: ["recruiting", "active", "completed"]
    include_conditions: true
    url_pattern: "clinicaltrials_gov"
    
  fda_drugs:
    default_max_results: 15
    include_approval_status: true
    include_safety_info: true
    url_pattern: "dailymed"

# Response template configurations
response_templates:
  academic_article_list:
    format: "structured"
    sections: ["title", "authors", "journal", "abstract", "link"]
    numbering: true
    evidence_indicators: true
    
  mixed_studies_list:
    format: "grouped"
    groups: ["published_studies", "clinical_trials"]
    max_per_group: 6
    include_study_type: true
    
  treatment_options_list:
    format: "categorized"
    categories: ["evidence_based", "clinical_trials", "fda_approved"]
    include_evidence_level: true
    
  clinical_trials_list:
    format: "structured"
    sections: ["title", "status", "phase", "conditions", "recruitment", "link"]
    status_indicators: true
    
  drug_information_list:
    format: "structured"
    sections: ["name", "generic_name", "approval_status", "indications", "link"]
    safety_warnings: true
    
  conversational_overview:
    format: "narrative"
    include_highlights: true
    max_length: 500
    source_attribution: true
```

## Implementation Patterns

### Query Intent Classification
```python
class HealthcareQueryClassifier:
    def __init__(self, config_path: str = "config/medical_query_patterns.yaml"):
        self.config = self.load_configuration(config_path)
        self.patterns = self.config["query_patterns"]
    
    def classify_query(self, query: str) -> QueryIntent:
        """Classify user query to determine response format and sources"""
        query_lower = query.lower()
        
        # Score each pattern based on keyword matches
        pattern_scores = {}
        for pattern_name, pattern_config in self.patterns.items():
            score = self.calculate_pattern_score(query_lower, pattern_config["keywords"])
            if score > 0:
                pattern_scores[pattern_name] = score
        
        # Select highest scoring pattern
        if pattern_scores:
            best_pattern = max(pattern_scores, key=pattern_scores.get)
            return self.create_query_intent(best_pattern, self.patterns[best_pattern])
        
        # Default to information request
        return self.create_query_intent("information_request", self.patterns["information_request"])
    
    def calculate_pattern_score(self, query: str, keywords: List[str]) -> float:
        """Calculate match score for query against keyword pattern"""
        matches = sum(1 for keyword in keywords if keyword in query)
        return matches / len(keywords) if keywords else 0

## Orchestrator Alignment Note

- Medical search should run only when selected by the router
- Agents must populate `formatted_summary` for human UI consumption
- Provenance headers are added by healthcare-api based on `agent_name`
```

### Configuration-Driven Source Selection
```python
class SourceSelectionManager:
    def __init__(self, config: Dict[str, Any]):
        self.source_configs = config["source_configurations"]
    
    def get_sources_for_intent(self, query_intent: QueryIntent) -> List[SourceConfig]:
        """Get configured sources for a specific query intent"""
        return [
            SourceConfig(
                name=source_name,
                max_results=self.source_configs[source_name]["default_max_results"],
                **self.source_configs[source_name]
            )
            for source_name in query_intent.primary_sources
            if source_name in self.source_configs
        ]
```

### Template-Driven Response Generation
```python
class ResponseTemplateEngine:
    def __init__(self, config: Dict[str, Any]):
        self.template_configs = config["response_templates"]
    
    def generate_response(
        self,
        query_intent: QueryIntent,
        search_results: Dict[str, Any]
    ) -> str:
        """Generate response using configured template"""
        template_name = query_intent.template
        template_config = self.template_configs.get(template_name)
        
        if not template_config:
            return self.generate_fallback_response(search_results)
        
        formatter_method = getattr(
            self, 
            f"format_{template_config['format']}", 
            self.format_structured
        )
        
        return formatter_method(search_results, query_intent, template_config)
```

## Shared Keyword Handling

### Keyword Overlap Strategy
```python
# Handle shared keywords between sources intelligently
shared_keyword_resolution = {
    "studies": {
        "primary_check": "clinical_studies|research_studies",  # Prefer ClinicalTrials
        "secondary_sources": ["pubmed"],  # Include PubMed studies
        "combined_approach": True
    },
    "trials": {
        "primary_source": "clinical_trials",
        "include_trial_publications": True,  # PubMed articles about trials
        "cross_reference": True
    },
    "research": {
        "source_priority": ["pubmed", "clinical_trials"],
        "context_dependent": True,  # "research articles" vs "research studies"
        "fallback_to_all": False
    }
}
```

### Context-Aware Classification
```python
def classify_with_context(self, query: str) -> QueryIntent:
    """Enhanced classification considering keyword context"""
    # Check for compound patterns first
    if "clinical trials" in query.lower():
        return self.get_intent("clinical_trials_request")
    elif "research studies" in query.lower() or "clinical studies" in query.lower():
        return self.get_intent("studies_request")
    elif "articles" in query.lower() and ("peer" in query.lower() or "published" in query.lower()):
        return self.get_intent("articles_request")
    
    # Fall back to keyword scoring
    return self.classify_by_keywords(query)
```

## User Customization Support

### Client Configuration Override
```yaml
# config/client_overrides.yaml (optional)
client_preferences:
  default_response_format: "conversational_summary"  # Override system default
  max_results_preference: 12
  source_preferences: ["pubmed", "clinical_trials"]  # Exclude FDA if desired
  include_abstracts_always: true
  
  custom_patterns:
    # Client can add custom intent patterns
    my_custom_request:
      keywords: ["specific", "custom", "terms"]
      response_format: "structured_articles"
      primary_sources: ["pubmed"]
```

### Runtime Configuration Updates
```python
class ConfigurableSearchAgent:
    def update_configuration(self, client_config: Dict[str, Any]):
        """Allow runtime configuration updates"""
        self.classifier.update_patterns(client_config.get("custom_patterns", {}))
        self.template_engine.update_templates(client_config.get("custom_templates", {}))
        self.default_preferences = client_config.get("client_preferences", {})
```

## Testing Configuration Patterns

### Configuration Validation
```python
def test_query_pattern_configuration():
    """Validate query pattern configuration completeness"""
    config = load_medical_query_patterns()
    
    # Verify all patterns have required fields
    for pattern_name, pattern_config in config["query_patterns"].items():
        assert "keywords" in pattern_config
        assert "response_format" in pattern_config
        assert "primary_sources" in pattern_config
        assert "template" in pattern_config
    
    # Verify template configurations exist
    for pattern in config["query_patterns"].values():
        template_name = pattern["template"]
        assert template_name in config["response_templates"]

def test_keyword_classification():
    """Test classification accuracy for different query types"""
    classifier = HealthcareQueryClassifier()
    
    # Test specific intent detection
    assert classifier.classify_query("show me articles on heart disease").intent == "articles_request"
    assert classifier.classify_query("clinical studies for diabetes").intent == "studies_request" 
    assert classifier.classify_query("treatments for hypertension").intent == "treatments_request"
    assert classifier.classify_query("recruiting trials for cancer").intent == "clinical_trials_request"
```

## Migration and Deployment

### Configuration File Organization
```
config/
├── medical_query_patterns.yaml          # Main configuration
├── client_overrides.yaml               # Optional client customization
├── templates/
│   ├── structured_articles.template    # Response templates
│   ├── mixed_studies.template
│   └── conversational_summary.template
└── schemas/
    └── query_patterns.schema.json      # Validation schema
```

### Backward Compatibility
```python
# Maintain backward compatibility during configuration migration
class BackwardCompatibleClassifier:
    def classify_query(self, query: str, legacy_format: bool = False) -> Union[QueryIntent, str]:
        """Support both new intent objects and legacy string formats"""
        intent = self.classify_query_modern(query)
        
        if legacy_format:
            return intent.response_format  # Return format string for old code
        
        return intent  # Return full intent object for new code
```
