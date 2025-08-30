# NutritionSeedWordsAgent

## Purpose
Specialized agent for creating and managing comprehensive seed word systems for nutrition and food data collection. This agent ensures complete coverage of food categories through strategic search term generation.

## Capabilities
- Generate comprehensive seed word lists for all food categories
- Create culturally diverse food search terms
- Implement strategic search patterns for USDA API
- Optimize API usage within rate limits
- Ensure coverage of ethnic and regional foods
- Generate compound search terms for complex dishes

## Trigger Keywords
- seed words
- food search terms
- nutrition queries
- food categories
- search optimization
- USDA queries
- food coverage
- comprehensive food list

## Seed Word Categories

### Core Food Groups
```python
SEED_WORDS = {
    "fruits": [
        "apple", "banana", "orange", "grape", "strawberry", "blueberry",
        "mango", "pineapple", "watermelon", "peach", "pear", "plum",
        "cherry", "kiwi", "papaya", "guava", "lychee", "dragon fruit"
    ],
    "vegetables": [
        "carrot", "broccoli", "spinach", "kale", "lettuce", "tomato",
        "potato", "onion", "garlic", "pepper", "cucumber", "zucchini",
        "eggplant", "cauliflower", "cabbage", "asparagus", "artichoke"
    ],
    "proteins": [
        "chicken", "beef", "pork", "fish", "turkey", "lamb", "duck",
        "tofu", "tempeh", "seitan", "beans", "lentils", "chickpeas",
        "eggs", "seafood", "shellfish", "nuts", "seeds"
    ],
    "grains": [
        "rice", "wheat", "oats", "quinoa", "barley", "millet", "buckwheat",
        "bread", "pasta", "noodles", "cereal", "crackers", "tortilla"
    ],
    "dairy": [
        "milk", "cheese", "yogurt", "butter", "cream", "ice cream",
        "cottage cheese", "sour cream", "whey", "kefir", "buttermilk"
    ]
}
```

### Ethnic & Regional Foods
```python
ETHNIC_FOODS = {
    "asian": ["sushi", "dim sum", "pho", "pad thai", "kimchi", "miso"],
    "mexican": ["taco", "burrito", "enchilada", "tamale", "salsa", "guacamole"],
    "italian": ["pizza", "lasagna", "risotto", "gnocchi", "tiramisu"],
    "indian": ["curry", "naan", "samosa", "biryani", "dal", "chutney"],
    "mediterranean": ["hummus", "falafel", "tzatziki", "baklava", "tabbouleh"]
}
```

### Preparation Methods
```python
PREPARATIONS = [
    "raw", "cooked", "baked", "fried", "grilled", "roasted", "steamed",
    "boiled", "sauteed", "braised", "poached", "smoked", "cured"
]
```

## Search Strategy
1. Start with basic terms from each category
2. Combine with preparation methods
3. Add brand searches for packaged foods
4. Include ethnic variations
5. Search for composite dishes
6. Use scientific names for completeness

## Implementation Pattern
```python
class FoodSeedWordGenerator:
    def generate_search_queries(self):
        queries = []
        
        # Basic foods
        for category, foods in SEED_WORDS.items():
            queries.extend(foods)
        
        # Prepared variations
        for food in queries[:50]:  # Top foods
            for prep in PREPARATIONS[:5]:  # Common preparations
                queries.append(f"{prep} {food}")
        
        # Composite dishes
        queries.extend(self.generate_composite_dishes())
        
        # Ethnic foods
        for cuisine, dishes in ETHNIC_FOODS.items():
            queries.extend(dishes)
        
        return queries
```

## API Optimization
- Batch queries efficiently
- Respect rate limits (1000 requests/hour)
- Use pagination for large result sets
- Cache results to avoid duplicates
- Prioritize high-value searches

## Coverage Goals
- Achieve 10,000+ unique food items
- Cover all major food categories
- Include ethnic and regional varieties
- Capture branded and generic foods
- Ensure nutritional diversity

## Quality Metrics
- Unique foods per query
- Category distribution balance
- Nutritional data completeness
- Brand vs. generic ratio
- Cultural representation