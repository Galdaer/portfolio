"""
AI-Driven Food Data Enrichment Module
Uses SciSpacy NLP and Ollama LLM for intelligent food data enhancement

This module leverages:
- SciSpacy for food entity extraction
- Ollama for scientific names, common names, ingredients, and serving size generation
- Dynamic, context-aware enhancement without hardcoded food dictionaries
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import time
import json

from sqlalchemy import text
from database import get_db_session, get_thread_safe_session

from .scispacy_client import SciSpacyClient, SciSpacyClientSync
from .llm_client import OllamaClient, OllamaClientSync, LLMConfig
from .llm_client_optimized import OptimizedOllamaClient

logger = logging.getLogger(__name__)


class FoodAIEnhancer:
    """
    AI-driven food enhancement using NLP and LLM.
    
    No hardcoded food knowledge - uses:
    - SciSpacy for food entity recognition
    - Ollama for intelligent text generation
    - Context-aware enhancement based on actual food understanding
    """
    
    def __init__(self, batch_size: int = 100, use_scispacy: bool = False):
        """
        Initialize AI-driven food enhancer.
        
        Args:
            batch_size: Number of food items to process in each batch
            use_scispacy: Whether to use SciSpacy for entity extraction (optional, slower on CPU)
        """
        self.batch_size = batch_size
        self.use_scispacy = use_scispacy
        
        # Initialize AI clients
        if use_scispacy:
            self.scispacy_client = SciSpacyClientSync()
        else:
            self.scispacy_client = None
        
        # Use optimized client for faster processing
        from .llm_client_optimized import OptimizedOllamaClient
        self.ollama_client = OptimizedOllamaClient()
        
        # Statistics tracking
        self.stats = {
            'processed': 0,
            'enhanced': 0,
            'scientific_names_added': 0,
            'common_names_added': 0,
            'ingredients_added': 0,
            'serving_sizes_added': 0,
            'ai_calls': 0,
            'ai_failures': 0
        }
        
        # Rate limiting for AI services
        self.last_ai_call = 0
        self.min_ai_interval = 0.1  # Minimum seconds between AI calls
        
        # Comprehensive food seed words for search
        self.food_seed_words = self._get_comprehensive_food_seed_words()
        
    def enhance_food_database(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Enhance food database using AI-driven approach.
        
        Args:
            limit: Optional limit on number of food items to process
            
        Returns:
            Enhancement statistics
        """
        start_time = datetime.now()
        logger.info("Starting AI-driven food enhancement")
        
        # Check AI service health
        if not self._check_ai_services():
            logger.error("AI services not available, cannot proceed with enhancement")
            return self.stats
        
        with get_db_session() as session:
            # Get food items that need enhancement
            query = """
                SELECT fdc_id, description, scientific_name, common_names,
                       food_category, brand_owner, ingredients, serving_size,
                       serving_size_unit, source
                FROM food_items
                WHERE (scientific_name IS NULL OR scientific_name = '')
                   OR (common_names IS NULL OR common_names = '')
                   OR (ingredients IS NULL OR ingredients = '')
                   OR (serving_size IS NULL)
                ORDER BY fdc_id
            """
            
            if limit:
                query += f" LIMIT {limit}"
                
            result = session.execute(text(query))
            foods_to_enhance = result.fetchall()
            
            total_foods = len(foods_to_enhance)
            logger.info(f"Found {total_foods} food items needing AI enhancement")
            
            # Process in batches
            for i in range(0, total_foods, self.batch_size):
                batch = foods_to_enhance[i:i + self.batch_size]
                self._process_batch(session, batch)
                
                # Progress logging
                progress = min(i + self.batch_size, total_foods)
                logger.info(f"AI Enhancement progress: {progress}/{total_foods} "
                           f"({progress/total_foods*100:.1f}%)")
                
            session.commit()
            
        # Calculate final statistics
        end_time = datetime.now()
        duration = end_time - start_time
        
        self.stats['duration'] = str(duration)
        self.stats['success_rate'] = (
            (self.stats['enhanced'] / self.stats['processed'] * 100)
            if self.stats['processed'] > 0 else 0
        )
        
        logger.info(f"AI Food Enhancement completed in {duration}")
        logger.info(f"Statistics: {self.stats}")
        
        return self.stats
        
    def _check_ai_services(self) -> bool:
        """Check if AI services are available"""
        if self.use_scispacy and self.scispacy_client:
            scispacy_ok = self.scispacy_client.check_health()
            if not scispacy_ok:
                logger.warning("SciSpacy service not available")
        else:
            scispacy_ok = True  # Skip SciSpacy check if not using it
            
        ollama_ok = self.ollama_client.check_health()
        if not ollama_ok:
            logger.warning("Ollama service not available")
            
        return scispacy_ok and ollama_ok
        
    def _process_batch(self, session, batch):
        """Process a batch of food items with AI enhancement"""
        
        for row in batch:
            try:
                fdc_id = row.fdc_id
                description = row.description
                
                # Skip if no description
                if not description:
                    continue
                    
                self.stats['processed'] += 1
                
                # Rate limiting
                self._rate_limit()
                
                # Extract food entities using SciSpacy
                food_concepts = self._extract_food_concepts(description)
                
                # Generate enhancements using Ollama
                enhancements = self._generate_food_enhancements(
                    description, row.food_category, row.brand_owner,
                    row.ingredients, food_concepts
                )
                
                # Update database if we got enhancements
                if self._has_enhancements(enhancements):
                    self._update_food_item(session, fdc_id, enhancements)
                    self.stats['enhanced'] += 1
                    
            except Exception as e:
                logger.error(f"Error processing food {row.fdc_id}: {e}")
                self.stats['ai_failures'] += 1
                continue
                
    def _rate_limit(self):
        """Apply rate limiting for AI service calls"""
        elapsed = time.time() - self.last_ai_call
        if elapsed < self.min_ai_interval:
            time.sleep(self.min_ai_interval - elapsed)
        self.last_ai_call = time.time()
        
    def _extract_food_concepts(self, description: str) -> Dict[str, Any]:
        """Extract food concepts using SciSpacy (if available) or basic extraction"""
        if self.use_scispacy and self.scispacy_client:
            try:
                self.stats['ai_calls'] += 1
                concepts = self.scispacy_client.extract_food_concepts(description)
                return concepts
            except Exception as e:
                logger.error(f"SciSpacy extraction failed: {e}")
                self.stats['ai_failures'] += 1
                return {}
        else:
            # Basic extraction without SciSpacy - just split into tokens
            tokens = description.lower().split()
            return {
                'all_entities': tokens,
                'chemicals': [],
                'organisms': [],
                'foods': tokens
            }
            
    def _generate_food_enhancements(self, description: str, category: str,
                                   brand_owner: str, existing_ingredients: str,
                                   food_concepts: Dict[str, Any]) -> Dict[str, Any]:
        """Generate food enhancements using optimized Ollama LLM (single call)"""
        
        # Get food entities for context
        food_entities = food_concepts.get('all_entities', [])
        
        try:
            # Make a single optimized call for all enhancements
            self.stats['ai_calls'] += 1
            
            # Only generate for non-branded foods (generic items)
            if not brand_owner:
                enhancements = self.ollama_client.generate_all_food_enhancements(
                    description=description,
                    category=category,
                    food_entities=food_entities
                )
                
                # Track statistics
                if enhancements.get('scientific_name'):
                    self.stats['scientific_names_added'] += 1
                if enhancements.get('common_names'):
                    self.stats['common_names_added'] += 1
                if enhancements.get('ingredients') and not existing_ingredients:
                    self.stats['ingredients_added'] += 1
                if enhancements.get('serving_size') is not None:
                    self.stats['serving_sizes_added'] += 1
                    
                return enhancements
            else:
                # For branded foods, just get common names and serving size
                enhancements = self.ollama_client.generate_all_food_enhancements(
                    description=description,
                    category=category,
                    food_entities=food_entities
                )
                # Clear scientific name and ingredients for branded items
                enhancements['scientific_name'] = ''
                if existing_ingredients:
                    enhancements['ingredients'] = ''
                    
                # Track statistics
                if enhancements.get('common_names'):
                    self.stats['common_names_added'] += 1
                if enhancements.get('serving_size') is not None:
                    self.stats['serving_sizes_added'] += 1
                    
                return enhancements
                
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            self.stats['ai_failures'] += 1
            return {
                'scientific_name': '',
                'common_names': '',
                'ingredients': '',
                'serving_size': None,
                'serving_size_unit': ''
            }
        
    def _has_enhancements(self, enhancements: Dict[str, Any]) -> bool:
        """Check if we have any enhancements to apply"""
        return (
            bool(enhancements.get('scientific_name')) or
            bool(enhancements.get('common_names')) or
            bool(enhancements.get('ingredients')) or
            enhancements.get('serving_size') is not None
        )
        
    def _update_food_item(self, session, fdc_id: str, enhancements: Dict[str, Any]):
        """Update food item with AI-generated enhancements"""
        
        update_parts = []
        params = {'fdc_id': fdc_id}
        
        # Validate and add scientific_name (must be string)
        if enhancements.get('scientific_name'):
            scientific_name = enhancements['scientific_name']
            # Extra validation - ensure it's a string
            if isinstance(scientific_name, str):
                update_parts.append("scientific_name = :scientific_name")
                params['scientific_name'] = scientific_name
            else:
                logger.warning(f"Skipping invalid scientific_name type for fdc_id {fdc_id}: {type(scientific_name)}")
            
        # Validate and add common_names (must be string)
        if enhancements.get('common_names'):
            common_names = enhancements['common_names']
            if isinstance(common_names, str):
                update_parts.append("common_names = :common_names")
                params['common_names'] = common_names
            else:
                logger.warning(f"Skipping invalid common_names type for fdc_id {fdc_id}: {type(common_names)}")
            
        # Validate and add ingredients (must be string)
        if enhancements.get('ingredients'):
            ingredients = enhancements['ingredients']
            if isinstance(ingredients, str):
                update_parts.append("ingredients = :ingredients")
                params['ingredients'] = ingredients
            else:
                logger.warning(f"Skipping invalid ingredients type for fdc_id {fdc_id}: {type(ingredients)}")
            
        # Validate and add serving_size (must be numeric)
        if enhancements.get('serving_size') is not None:
            serving_size = enhancements['serving_size']
            if isinstance(serving_size, (int, float)):
                update_parts.append("serving_size = :serving_size")
                params['serving_size'] = serving_size
            else:
                logger.warning(f"Skipping invalid serving_size type for fdc_id {fdc_id}: {type(serving_size)}")
            
        # Validate and add serving_size_unit (must be string)
        if enhancements.get('serving_size_unit'):
            serving_size_unit = enhancements['serving_size_unit']
            if isinstance(serving_size_unit, str):
                update_parts.append("serving_size_unit = :serving_size_unit")
                params['serving_size_unit'] = serving_size_unit
            else:
                logger.warning(f"Skipping invalid serving_size_unit type for fdc_id {fdc_id}: {type(serving_size_unit)}")
            
        if update_parts:
            update_query = text(f"""
                UPDATE food_items 
                SET {', '.join(update_parts)},
                    last_updated = CURRENT_TIMESTAMP
                WHERE fdc_id = :fdc_id
            """)
            
            try:
                session.execute(update_query, params)
            except Exception as e:
                logger.error(f"Database update failed for fdc_id {fdc_id}: {e}")
                logger.debug(f"Attempted params: {params}")

    def _get_comprehensive_food_seed_words(self) -> List[str]:
        """Get comprehensive list of food search seed words for AI enhancement"""
        return [
            # Fruits
            "apple", "banana", "orange", "strawberry", "blueberry", "grapes", "pineapple", 
            "mango", "avocado", "lemon", "lime", "grapefruit", "peach", "pear", "cherry", 
            "watermelon", "cantaloupe", "kiwi", "papaya", "pomegranate", "blackberry", 
            "raspberry", "plum", "apricot", "fig", "date", "coconut", "cranberry",
            
            # Vegetables  
            "broccoli", "spinach", "kale", "carrots", "sweet potato", "potato", "tomato", 
            "onion", "bell pepper", "zucchini", "cauliflower", "brussels sprouts", 
            "asparagus", "cabbage", "cucumber", "celery", "lettuce", "mushrooms", 
            "eggplant", "squash", "pumpkin", "beets", "radish", "artichoke", "fennel",
            
            # Proteins
            "chicken", "beef", "salmon", "tuna", "eggs", "turkey", "pork", "shrimp", 
            "cod", "tilapia", "tofu", "tempeh", "beans", "lentils", "chickpeas", 
            "black beans", "kidney beans", "quinoa", "lamb", "duck", "crab", "lobster",
            
            # Grains
            "rice", "bread", "pasta", "oats", "barley", "wheat", "corn", "millet", 
            "buckwheat", "brown rice", "wild rice", "couscous", "bulgur", "farro", 
            "spelt", "amaranth", "teff",
            
            # Dairy
            "milk", "cheese", "yogurt", "butter", "cream", "cottage cheese", "mozzarella", 
            "cheddar", "ricotta", "feta", "parmesan", "goat cheese", "blue cheese",
            
            # Nuts and Seeds
            "almonds", "walnuts", "cashews", "pecans", "peanuts", "pistachios", 
            "sunflower seeds", "chia seeds", "flax seeds", "pumpkin seeds", 
            "sesame seeds", "hemp seeds", "macadamia", "hazelnuts", "pine nuts",
            
            # Beverages
            "coffee", "tea", "juice", "wine", "beer", "water", "soda", "kombucha",
            
            # Spices and Herbs
            "garlic", "ginger", "cinnamon", "turmeric", "cumin", "paprika", "oregano", 
            "basil", "thyme", "rosemary", "sage", "cilantro", "parsley", "dill",
            
            # Oils and Condiments
            "olive oil", "coconut oil", "avocado oil", "vinegar", "soy sauce", 
            "honey", "maple syrup", "mustard", "ketchup", "mayonnaise"
        ]


# Async version for use in async contexts
class FoodAIEnhancerAsync:
    """Async version of the AI-driven food enhancer"""
    
    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
        self.scispacy_client = None
        self.ollama_client = None
        self.stats = {
            'processed': 0,
            'enhanced': 0,
            'scientific_names_added': 0,
            'common_names_added': 0,
            'ingredients_added': 0,
            'serving_sizes_added': 0,
            'ai_calls': 0,
            'ai_failures': 0
        }
        
    async def __aenter__(self):
        self.scispacy_client = await SciSpacyClient().__aenter__()
        self.ollama_client = await OllamaClient().__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.scispacy_client:
            await self.scispacy_client.__aexit__(exc_type, exc_val, exc_tb)
        if self.ollama_client:
            await self.ollama_client.__aexit__(exc_type, exc_val, exc_tb)