# Food Data AI Enhancement

This module implements comprehensive AI-driven enhancement for the USDA food database, similar to the successful ICD-10 AI enhancement pattern.

## Overview

The food enhancement system uses:
- **SciSpacy NLP Service** (172.20.0.14:8001) for food entity extraction
- **Ollama LLM Service** (172.20.0.10:11434) for intelligent text generation
- **Dynamic, context-aware enhancement** without hardcoded food dictionaries
- **PHI-safe local processing** - no external API calls

## Enhanced Data Coverage

### Current Poor Coverage (Before Enhancement):
- scientific_name: 4.7% (347/7,350)
- common_names: 2.2% (159/7,350)
- ingredients: 0%
- brand_owner: 0% 
- serving_size: 0%

### Target Coverage (After Enhancement):
- scientific_name: 80%+ (for generic foods)
- common_names: 90%+
- ingredients: 60%+ (for non-branded foods)
- brand_owner: 30%+ (from branded foods)
- serving_size: 70%+

## Key Features

### 1. Branded Food Support
Modified USDA downloader to include "Branded" foods alongside "Foundation" and "SR Legacy" data types, providing:
- Brand owner information
- Ingredient lists from product labels
- Serving size data from packaging

### 2. Scientific Name Generation
Uses Ollama to generate botanical/zoological scientific names:
- Apple → *Malus domestica*
- Chicken → *Gallus gallus domesticus*
- Salmon → *Salmo salar*
- Broccoli → *Brassica oleracea*

### 3. Common/Alternative Names
Generates regional and cultural variations:
- Eggplant → Aubergine, Brinjal
- Cilantro → Coriander leaves, Chinese parsley
- Chickpeas → Garbanzo beans, Ceci beans

### 4. Ingredient Inference
For non-branded foods, infers typical ingredients with disclaimers:
- "Chicken salad" → "*Inferred typical ingredients: Chicken, mayonnaise, celery, seasonings*"
- Single-ingredient foods (like "apple") are skipped

### 5. Standard Serving Sizes
Generates USDA-standard serving sizes:
- Fruits: 150g typical
- Vegetables: 100g raw, 80g cooked
- Proteins: 85g cooked
- Grains: 125g cooked

## Architecture

### Files Structure
```
src/health_info/
├── food_ai_enrichment.py      # Main enhancement engine
├── scispacy_client.py         # SciSpacy NLP client
├── llm_client.py             # Ollama LLM client
├── food_seed_words.py        # Comprehensive food vocabulary
└── downloader.py             # Enhanced with branded foods
```

### Enhancement Process
1. **Data Collection**: Download Foundation, SR Legacy, Branded, and Survey foods
2. **Entity Extraction**: Use SciSpacy to identify food components
3. **AI Generation**: Use Ollama to generate enhancements
4. **Database Integration**: UPSERT with existing data preservation
5. **Search Optimization**: Update full-text search vectors

## Usage

### Integrated with Health Info Update
```bash
# Run full update with AI enhancement
./update-scripts/update_health_info.sh

# Quick test with limited data
QUICK_TEST=true ./update-scripts/update_health_info.sh
```

### Standalone Testing
```bash
# Test AI services and enhancement
python3 test_food_enhancement.py

# Test specific components
python3 -c "
from src.health_info.food_ai_enrichment import FoodAIEnhancer
enhancer = FoodAIEnhancer()
stats = enhancer.enhance_food_database(limit=10)
print(stats)
"
```

### Database Coverage Analysis
```sql
-- Check current coverage
SELECT 
    COUNT(*) as total_foods,
    COUNT(CASE WHEN scientific_name IS NOT NULL AND scientific_name != '' THEN 1 END) as has_scientific_name,
    COUNT(CASE WHEN common_names IS NOT NULL AND common_names != '' THEN 1 END) as has_common_names,
    COUNT(CASE WHEN ingredients IS NOT NULL AND ingredients != '' THEN 1 END) as has_ingredients,
    COUNT(serving_size) as has_serving_size
FROM food_items;
```

## AI Service Dependencies

### SciSpacy Service (172.20.0.14:8001)
- Biomedical entity extraction
- Food component identification
- Chemical and organism detection

### Ollama Service (172.20.0.10:11434)  
- Scientific name generation
- Common name synthesis
- Ingredient inference
- Serving size estimation

## Configuration

### Environment Variables
```bash
# Ollama configuration
OLLAMA_HOST=http://172.20.0.10:11434
OLLAMA_MODEL=llama3.1:8b

# SciSpacy configuration  
SCISPACY_HOST=http://172.20.0.14:8001

# USDA API (for branded foods)
USDA_API_KEY=your_api_key_here
```

### Rate Limiting
- Minimum 0.1 seconds between AI calls
- USDA API: 3.6 seconds between requests (under 1000/hour limit)
- Batch processing with progress persistence

## Performance Optimization

### Batch Processing
- Default batch size: 100 food items
- Configurable for memory/performance tuning
- Progress checkpointing for resume capability

### Database Efficiency
- UPSERT operations preserve existing data
- Only update empty/null fields
- Bulk full-text search vector updates
- Connection pooling for parallel operations

## Error Handling

### Service Resilience
- Health checks before processing
- Graceful degradation if AI services unavailable
- Continue updates without enhancement if services fail
- Comprehensive error logging and statistics

### Data Validation
- Scientific name format validation (genus species)
- Common name deduplication
- Serving size unit standardization
- Ingredient disclaimer formatting

## Integration Points

### Medical Mirrors Service
- Automatic integration with existing update scripts
- Preserves all existing food data
- Compatible with existing database schema
- No breaking changes to current functionality

### Healthcare MCP Tools
- Enhanced food data automatically available through MCP
- Improved search results with scientific names
- Better nutrition analysis with complete ingredient data
- Rich serving size information for meal planning

## Monitoring and Statistics

### Enhancement Metrics
- Total foods processed
- Scientific names added
- Common names generated  
- Ingredients inferred
- Serving sizes estimated
- AI service call statistics
- Success/failure rates

### Database Impact
```sql
-- Monitor enhancement progress
SELECT source, 
       COUNT(*) as total,
       COUNT(scientific_name) as with_scientific_name,
       COUNT(common_names) as with_common_names,
       COUNT(ingredients) as with_ingredients
FROM food_items 
GROUP BY source;
```

## Future Enhancements

### Planned Features
- Nutritional density scoring
- Allergen detection and tagging
- Dietary flag generation (vegan, gluten-free, etc.)
- Recipe suggestion based on ingredients
- Seasonal availability information

### Performance Improvements
- Parallel AI processing with worker pools
- Caching layer for repeated queries
- Incremental updates for new foods only
- Machine learning for better serving size estimation

## Troubleshooting

### Common Issues
1. **AI services unavailable**: Check Ollama and SciSpacy health endpoints
2. **Database connection failures**: Verify PostgreSQL connectivity
3. **USDA API rate limiting**: Increase delay between requests
4. **Memory issues**: Reduce batch size or increase container memory

### Debug Mode
```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Test individual components
from src.health_info.llm_client import OllamaClientSync
client = OllamaClientSync()
result = client.generate_scientific_name("apple", "fruits")
print(result)
```

This comprehensive food enhancement system significantly improves the quality and completeness of the USDA food database, making it much more valuable for healthcare applications, nutrition analysis, and meal planning tools.