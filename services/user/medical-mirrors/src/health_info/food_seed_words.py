"""
Comprehensive Food Seed Words for AI Enhancement
Used to identify foods that need scientific names, common names, and other enhancements
"""

# Core food categories with comprehensive seed words
FOOD_SEED_WORDS = {
    "fruits": [
        "apple", "banana", "orange", "strawberry", "blueberry", "grapes", "pineapple", 
        "mango", "avocado", "lemon", "lime", "grapefruit", "peach", "pear", "cherry", 
        "watermelon", "cantaloupe", "honeydew", "kiwi", "papaya", "pomegranate", 
        "blackberry", "raspberry", "plum", "apricot", "fig", "date", "coconut", 
        "cranberry", "elderberry", "gooseberry", "guava", "jackfruit", "lychee", 
        "passion fruit", "persimmon", "plantain", "star fruit", "tangerine"
    ],
    
    "vegetables": [
        "broccoli", "spinach", "kale", "carrots", "sweet potato", "potato", "tomato", 
        "onion", "bell pepper", "zucchini", "cauliflower", "brussels sprouts", 
        "asparagus", "cabbage", "cucumber", "celery", "lettuce", "mushrooms", 
        "eggplant", "squash", "pumpkin", "beets", "radish", "artichoke", "fennel",
        "arugula", "bok choy", "collard greens", "endive", "leeks", "okra",
        "parsnips", "rutabaga", "swiss chard", "turnips", "watercress"
    ],
    
    "proteins": [
        "chicken", "beef", "salmon", "tuna", "eggs", "turkey", "pork", "shrimp", 
        "cod", "tilapia", "tofu", "tempeh", "beans", "lentils", "chickpeas", 
        "black beans", "kidney beans", "quinoa", "lamb", "duck", "crab", "lobster",
        "sardines", "mackerel", "halibut", "trout", "venison", "bison", "rabbit",
        "scallops", "mussels", "oysters", "clams", "squid", "octopus"
    ],
    
    "grains": [
        "rice", "bread", "pasta", "oats", "barley", "wheat", "corn", "millet", 
        "buckwheat", "brown rice", "wild rice", "couscous", "bulgur", "farro", 
        "spelt", "amaranth", "teff", "sorghum", "rye", "quinoa", "kamut",
        "freekeh", "emmer", "einkorn"
    ],
    
    "dairy": [
        "milk", "cheese", "yogurt", "butter", "cream", "cottage cheese", "mozzarella", 
        "cheddar", "ricotta", "feta", "parmesan", "goat cheese", "blue cheese",
        "brie", "camembert", "swiss cheese", "provolone", "gouda", "manchego",
        "roquefort", "pecorino", "mascarpone", "cream cheese", "sour cream"
    ],
    
    "nuts_seeds": [
        "almonds", "walnuts", "cashews", "pecans", "peanuts", "pistachios", 
        "sunflower seeds", "chia seeds", "flax seeds", "pumpkin seeds", 
        "sesame seeds", "hemp seeds", "macadamia", "hazelnuts", "pine nuts",
        "brazil nuts", "chestnuts", "poppy seeds", "cumin seeds", "coriander seeds"
    ],
    
    "herbs_spices": [
        "garlic", "ginger", "cinnamon", "turmeric", "cumin", "paprika", "oregano", 
        "basil", "thyme", "rosemary", "sage", "cilantro", "parsley", "dill",
        "mint", "chives", "tarragon", "marjoram", "cardamom", "cloves", "nutmeg",
        "allspice", "bay leaves", "black pepper", "cayenne", "chili powder",
        "curry powder", "fennel seeds", "mustard seeds", "saffron", "vanilla"
    ],
    
    "beverages": [
        "coffee", "tea", "juice", "wine", "beer", "water", "soda", "kombucha",
        "green tea", "black tea", "herbal tea", "oolong tea", "white tea",
        "coconut water", "almond milk", "soy milk", "oat milk", "rice milk"
    ],
    
    "oils_fats": [
        "olive oil", "coconut oil", "avocado oil", "canola oil", "sunflower oil",
        "safflower oil", "sesame oil", "walnut oil", "flaxseed oil", "hemp oil",
        "grapeseed oil", "peanut oil", "corn oil", "soybean oil", "palm oil"
    ],
    
    "seafood": [
        "salmon", "tuna", "cod", "halibut", "tilapia", "trout", "sardines", 
        "mackerel", "anchovies", "herring", "sea bass", "snapper", "mahi-mahi",
        "swordfish", "flounder", "sole", "catfish", "perch", "pike", "eel"
    ],
    
    "legumes": [
        "black beans", "kidney beans", "navy beans", "pinto beans", "lima beans",
        "garbanzo beans", "chickpeas", "lentils", "split peas", "black-eyed peas",
        "adzuki beans", "cannellini beans", "fava beans", "mung beans", "soybeans"
    ],
    
    "fungi": [
        "button mushrooms", "shiitake", "portobello", "cremini", "oyster mushrooms",
        "chanterelles", "morel mushrooms", "porcini", "enoki", "maitake"
    ]
}

# Alternative names and synonyms for better matching
FOOD_SYNONYMS = {
    "eggplant": ["aubergine", "brinjal"],
    "cilantro": ["coriander leaves", "chinese parsley"],
    "chickpeas": ["garbanzo beans", "ceci beans"],
    "scallions": ["green onions", "spring onions"],
    "zucchini": ["courgette"],
    "bell pepper": ["capsicum", "sweet pepper"],
    "sweet potato": ["yam", "kumara"],
    "arugula": ["rocket", "roquette"],
    "endive": ["chicory", "witloof"],
    "rutabaga": ["swede", "neep"],
    "turnips": ["white turnip", "baby turnip"]
}

# Scientific name mappings for common foods
KNOWN_SCIENTIFIC_NAMES = {
    "apple": "Malus domestica",
    "banana": "Musa acuminata",
    "orange": "Citrus sinensis",
    "tomato": "Solanum lycopersicum",
    "potato": "Solanum tuberosum",
    "carrot": "Daucus carota",
    "broccoli": "Brassica oleracea",
    "spinach": "Spinacia oleracea",
    "onion": "Allium cepa",
    "garlic": "Allium sativum",
    "chicken": "Gallus gallus domesticus",
    "beef": "Bos taurus",
    "pork": "Sus scrofa domesticus",
    "salmon": "Salmo salar",
    "rice": "Oryza sativa",
    "wheat": "Triticum aestivum",
    "corn": "Zea mays",
    "soybean": "Glycine max"
}

# Standard serving sizes for common foods (USDA guidelines)
STANDARD_SERVING_SIZES = {
    "fruits": {"size": 150, "unit": "g"},
    "vegetables_raw": {"size": 100, "unit": "g"},
    "vegetables_cooked": {"size": 80, "unit": "g"},
    "grains_cooked": {"size": 125, "unit": "g"},
    "meat_cooked": {"size": 85, "unit": "g"},
    "fish_cooked": {"size": 85, "unit": "g"},
    "nuts": {"size": 30, "unit": "g"},
    "cheese": {"size": 30, "unit": "g"},
    "milk": {"size": 240, "unit": "ml"},
    "yogurt": {"size": 170, "unit": "g"},
    "oils": {"size": 15, "unit": "ml"},
    "bread": {"size": 30, "unit": "g"}
}


def get_all_food_terms():
    """Get all food terms from all categories"""
    all_terms = []
    for category_terms in FOOD_SEED_WORDS.values():
        all_terms.extend(category_terms)
    
    # Add synonyms
    for synonyms in FOOD_SYNONYMS.values():
        all_terms.extend(synonyms)
    
    return list(set(all_terms))  # Remove duplicates


def get_food_category(food_name):
    """Determine the category of a food item"""
    food_lower = food_name.lower()
    
    for category, terms in FOOD_SEED_WORDS.items():
        if any(term in food_lower for term in terms):
            return category
    
    # Check synonyms
    for main_term, synonyms in FOOD_SYNONYMS.items():
        if any(synonym in food_lower for synonym in synonyms):
            # Find category of main term
            return get_food_category(main_term)
    
    return "other"


def is_single_ingredient_food(description):
    """Check if a food is likely a single ingredient (vs processed food)"""
    single_ingredient_indicators = [
        "raw", "fresh", "whole", "unprocessed", "plain"
    ]
    
    processed_indicators = [
        "prepared", "cooked", "baked", "fried", "seasoned", "sauce", "soup", 
        "salad", "mix", "blend", "frozen dinner", "canned", "packaged"
    ]
    
    desc_lower = description.lower()
    
    # If it contains processed indicators, it's likely multi-ingredient
    if any(indicator in desc_lower for indicator in processed_indicators):
        return False
    
    # If it contains single ingredient indicators, it's likely single ingredient
    if any(indicator in desc_lower for indicator in single_ingredient_indicators):
        return True
    
    # Default: if it's just a simple food name, assume single ingredient
    word_count = len(description.split())
    return word_count <= 3