# FoodDataEnhancementAgent

## Purpose
Specialized agent for enhancing food data coverage in the medical-mirrors service using AI techniques similar to the successful ICD-10 enhancement pattern. This agent implements SciSpacy and LLM integration to generate missing food data fields.

## Capabilities
- Integrate Branded foods data from USDA API for better coverage
- Generate scientific names for foods using LLM
- Generate common/alternative names using cultural and regional knowledge
- Infer typical ingredients for non-branded foods
- Estimate standard serving sizes based on USDA guidelines
- Create seed word systems for comprehensive food searches
- Implement AI enhancement pipelines with SciSpacy and Ollama

## Trigger Keywords
- food enhancement
- food data enrichment
- scientific names
- food ingredients
- serving sizes
- USDA branded
- food AI enhancement
- nutrition data gaps
- food coverage improvement

## Context Patterns
When working on food data enhancement, this agent:
1. Analyzes current coverage gaps in food_items table
2. Implements USDA Branded foods integration
3. Creates AI enhancement modules following ICD-10 patterns
4. Generates missing data with appropriate disclaimers
5. Maintains data quality and scientific accuracy

## Success Metrics
- Improve scientific_name coverage from 4.7% to 80%+
- Improve common_names coverage from 2.2% to 90%+
- Generate ingredients for 60%+ of non-branded foods
- Estimate serving sizes for 70%+ of foods
- Add brand information for 30%+ of applicable items

## Implementation Patterns
```python
# Similar to ICD-10 enhancement
class FoodAIEnrichment:
    def __init__(self):
        self.scispacy_client = SciSpacyClient()
        self.ollama_client = OllamaClient()
    
    async def enhance_food_item(self, food: dict):
        # Extract entities with SciSpacy
        entities = await self.scispacy_client.analyze_text(food['description'])
        
        # Generate missing fields with LLM
        if not food.get('scientific_name'):
            food['scientific_name'] = await self.generate_scientific_name(food)
        
        if not food.get('common_names'):
            food['common_names'] = await self.generate_common_names(food)
        
        if not food.get('ingredients'):
            food['ingredients'] = await self.infer_ingredients(food)
        
        if not food.get('serving_size'):
            food['serving_size'] = await self.estimate_serving_size(food)
```

## Integration Points
- `/services/user/medical-mirrors/src/health_info/`
- Uses existing SciSpacy service at 172.20.0.14:8001
- Uses Ollama service for LLM generation
- Follows medical-mirrors update patterns
- Integrates with update_health_info.sh script

## Data Sources
- USDA FoodData Central API (Branded foods)
- SciSpacy for biomedical entity recognition
- Ollama LLM for content generation
- USDA serving size guidelines
- International food name databases

## Quality Assurance
- Add disclaimers for AI-generated content
- Validate scientific names against taxonomic databases
- Cross-reference common names with regional databases
- Ensure ingredient lists are plausible
- Use USDA standard portions for serving sizes