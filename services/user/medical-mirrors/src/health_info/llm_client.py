"""
LLM Client for Food Text Generation
Uses Ollama for local, PHI-safe food data generation
"""

import logging
import asyncio
import aiohttp
import json
import requests
import os
import sys
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Add parent directory to path for config imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config_loader import get_config

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration for LLM client"""
    def __init__(self):
        config = get_config()
        llm_settings = config.get_llm_generation_settings()
        
        self.model = config.get_llm_model("food_enhancement")
        self.base_url = config.get_endpoint_url("ollama")
        self.temperature = llm_settings.get("temperature", 0.3)
        self.max_tokens = llm_settings.get("max_tokens", 500)
        self.timeout = config.get_llm_settings().get("llm", {}).get("request", {}).get("timeout", 30.0)


class OllamaClient:
    """
    Client for communicating with Ollama for food text generation.
    
    All processing is local and PHI-safe.
    """
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """
        Initialize Ollama client.
        
        Args:
            config: LLM configuration (uses defaults from config files if not provided)
        """
        self.config = config if config else LLMConfig()
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
            
    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generate text using Ollama.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt for context (optional)
            
        Returns:
            Generated text
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
            
        # Build the full prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        else:
            full_prompt = prompt
            
        try:
            async with self.session.post(
                f"{self.config.base_url}/api/generate",
                json={
                    "model": self.config.model,
                    "prompt": full_prompt,
                    "temperature": self.config.temperature,
                    "stream": False
                },
                timeout=aiohttp.ClientTimeout(total=self.config.timeout)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("response", "")
                else:
                    error_text = await response.text()
                    logger.error(f"Ollama generation failed: {error_text}")
                    return ""
                    
        except asyncio.TimeoutError:
            logger.error("Ollama request timed out")
            return ""
        except Exception as e:
            logger.error(f"Ollama request failed: {e}")
            return ""
            
    async def generate_scientific_name(self, description: str, category: str = None, 
                                      food_entities: List[str] = None) -> str:
        """
        Generate scientific name for a food item.
        
        Args:
            description: Food description
            category: Food category (optional)
            food_entities: Optional list of food entities found in description
            
        Returns:
            Generated scientific name
        """
        entities_context = ""
        if food_entities:
            entities_context = f"\nFood entities found: {', '.join(food_entities)}"
        
        category_context = f"\nFood category: {category}" if category else ""
        
        prompt = f"""Generate the scientific name for this food:
"{description}"{category_context}{entities_context}

Provide the correct botanical or zoological scientific name (genus species format).
For example:
- Apple → Malus domestica
- Chicken → Gallus gallus domesticus
- Salmon → Salmo salar
- Broccoli → Brassica oleracea

Return ONLY the scientific name, no explanations.
If no scientific name exists (for processed foods), return empty."""

        system_prompt = """You are a food science expert specializing in taxonomic classification.
Generate accurate scientific names for foods using proper binomial nomenclature."""
        
        response = await self.generate(prompt, system_prompt)
        
        # Clean and validate the response
        if response:
            scientific_name = response.strip()
            # Basic validation: should have at least two words (genus species)
            if len(scientific_name.split()) >= 2 and scientific_name[0].isupper():
                return scientific_name
        
        return ""
        
    async def generate_common_food_names(self, description: str, 
                                        food_entities: List[str] = None) -> List[str]:
        """
        Generate common/alternative names for a food item.
        
        Args:
            description: Food description
            food_entities: Optional list of food entities found in description
            
        Returns:
            List of common names
        """
        entities_context = ""
        if food_entities:
            entities_context = f"\nFood entities found: {', '.join(food_entities)}"
        
        prompt = f"""Generate common and alternative names for this food:
"{description}"{entities_context}

Provide alternative names that people would use, including:
- Regional names
- Common variations
- Colloquial terms
- Alternative spellings
- Cultural names

For example:
- Eggplant → Aubergine, Brinjal
- Cilantro → Coriander leaves, Chinese parsley
- Garbanzo beans → Chickpeas, Ceci beans

Return ONLY a comma-separated list of names, no explanations or numbering."""

        system_prompt = """You are a culinary expert helping to identify alternative food names.
Focus on generating accurate, commonly recognized alternative names."""
        
        response = await self.generate(prompt, system_prompt)
        
        # Parse response into list
        if response:
            names = [n.strip() for n in response.split(',') if n.strip()]
            # Filter out the original description and clean up
            original_words = set(description.lower().split())
            names = [n for n in names if not any(word in n.lower() for word in original_words) and len(n) > 2]
            return names[:15]  # Limit to top 15 names
        return []
        
    async def generate_food_ingredients(self, description: str, category: str = None,
                                       food_concepts: Dict[str, List[str]] = None) -> str:
        """
        Generate inferred typical ingredients for non-branded food items.
        
        Args:
            description: Food description
            category: Food category (optional)
            food_concepts: Optional food concepts extracted from description
            
        Returns:
            Inferred ingredients with disclaimer
        """
        context = ""
        if food_concepts:
            context = f"\nFood context: {json.dumps(food_concepts, indent=2)}"
        
        category_context = f"\nFood category: {category}" if category else ""
        
        prompt = f"""For this food item, infer typical ingredients:
"{description}"{category_context}{context}

This is for a non-branded, generic food item. Generate likely ingredients based on:
- Standard recipes for this food
- Common preparation methods
- Typical components

For example:
- "Chicken salad" → Chicken, mayonnaise, celery, seasonings
- "Vegetable soup" → Mixed vegetables, broth, onions, herbs, salt
- "Chocolate cake" → Flour, sugar, eggs, butter, cocoa powder, baking powder

Return ingredients with this disclaimer format:
"*Inferred typical ingredients based on common recipes: [ingredient list]"

If this is a single ingredient food (like "apple" or "chicken breast"), return empty."""

        system_prompt = """You are a food science expert helping to infer typical ingredients.
Only provide ingredients for prepared/processed foods, not single-ingredient items."""
        
        response = await self.generate(prompt, system_prompt)
        
        if response and "*Inferred typical ingredients" in response:
            return response.strip()
        
        return ""
        
    async def generate_serving_size(self, description: str, category: str = None) -> Dict[str, Any]:
        """
        Generate estimated USDA standard serving size for a food item.
        
        Args:
            description: Food description
            category: Food category (optional)
            
        Returns:
            Dictionary with size and unit
        """
        category_context = f"\nFood category: {category}" if category else ""
        
        prompt = f"""Generate a standard serving size for this food:
"{description}"{category_context}

Provide the typical USDA/standard serving size used in nutrition facts.
For example:
- Fruits: 1 medium apple (182g), 1 cup berries (150g)
- Vegetables: 1 cup raw (100g), 1/2 cup cooked (80g)
- Grains: 1 slice bread (28g), 1/2 cup cooked rice (100g)
- Proteins: 3 oz cooked meat (85g), 1 large egg (50g)
- Dairy: 1 cup milk (240ml), 1 oz cheese (28g)

Return ONLY in format: "number|unit"
Examples: "100|g", "240|ml", "28|g", "1|cup"

If unsure, use grams as default unit."""

        system_prompt = """You are a nutrition expert providing standard serving sizes.
Use USDA standard serving sizes when available."""
        
        response = await self.generate(prompt, system_prompt)
        
        if response and "|" in response:
            try:
                parts = response.strip().split("|")
                if len(parts) == 2:
                    size_str, unit = parts
                    # Try to parse the size as a number
                    try:
                        size = float(size_str)
                        return {"size": size, "unit": unit.strip()}
                    except ValueError:
                        # Handle cases like "1 cup" or "3 oz"
                        if size_str.strip().replace(".", "").isdigit():
                            return {"size": float(size_str), "unit": unit.strip()}
            except Exception as e:
                logger.debug(f"Could not parse serving size response: {response}")
        
        return {}
        
    def check_health(self) -> bool:
        """
        Check if Ollama service is healthy.
        
        Returns:
            True if service is responsive, False otherwise
        """
        import requests
        try:
            response = requests.get(f"{self.config.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False


# Synchronous wrapper for non-async contexts
class OllamaClientSync:
    """Synchronous client for Ollama using requests library"""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self.timeout = 60  # Longer timeout for LLM generation
        
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate text synchronously using requests with /api/generate endpoint"""
        try:
            # Build the full prompt like ICD-10 does
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            else:
                full_prompt = prompt
            
            response = requests.post(
                f"{self.config.base_url}/api/generate",
                json={
                    "model": self.config.model,
                    "prompt": full_prompt,
                    "temperature": self.config.temperature,
                    "stream": False
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "")
            else:
                logger.error(f"Ollama generate failed: {response.status_code}")
                return ""
        except Exception as e:
            logger.error(f"Ollama generate error: {e}")
            return ""
        
    def generate_scientific_name(self, description: str, category: str = None,
                                food_entities: List[str] = None) -> str:
        """Generate scientific name synchronously"""
        prompt = f"""Food item: {description}
{f'Category: {category}' if category else ''}
{f"Extracted entities: {', '.join(food_entities)}" if food_entities else ''}

Provide the scientific name for this food item.
If it's a plant-based food, provide the botanical name (e.g., Solanum lycopersicum for tomato).
If it's an animal product, provide the zoological name (e.g., Bos taurus for beef).
If it's a processed food without a specific organism, respond with "N/A".

Respond with ONLY the scientific name or "N/A", nothing else."""
        
        system_prompt = """You are a food science expert specializing in taxonomy.
Provide accurate scientific names for food items.
Respond concisely with only the scientific name."""
        
        response = self.generate(prompt, system_prompt)
        cleaned = response.strip()
        
        if cleaned and cleaned != "N/A" and len(cleaned) < 100:
            return cleaned
        return ""
        
    def generate_common_food_names(self, description: str,
                                  food_entities: List[str] = None) -> List[str]:
        """Generate common food names synchronously"""
        prompt = f"""Food item: {description}
{f"Related entities: {', '.join(food_entities)}" if food_entities else ''}

List up to 5 common names or aliases for this food item.
Include regional names, colloquial terms, and alternative names.

Respond with a comma-separated list, e.g.: "tomato, love apple, tomate"
Respond with ONLY the names, nothing else."""
        
        system_prompt = """You are a food expert with knowledge of regional food names.
Provide common alternative names for food items.
Respond concisely with only the names."""
        
        response = self.generate(prompt, system_prompt)
        
        if response:
            names = [name.strip() for name in response.split(",")]
            return [name for name in names if name and len(name) < 50][:5]
        return []
        
    def generate_food_ingredients(self, description: str, category: str = None,
                                 food_concepts: Dict[str, List[str]] = None) -> str:
        """Generate food ingredients synchronously"""
        prompt = f"""Food item: {description}
{f'Category: {category}' if category else ''}
{f"Chemical compounds: {', '.join(food_concepts.get('chemicals', []))}" if food_concepts and food_concepts.get('chemicals') else ''}
{f"Organisms: {', '.join(food_concepts.get('organisms', []))}" if food_concepts and food_concepts.get('organisms') else ''}

List the main ingredients or components of this food item.
For whole foods, list key nutritional components.
For processed foods, list typical ingredients.

Respond with a comma-separated list of ingredients.
Keep it concise and relevant."""
        
        system_prompt = """You are a food scientist and nutritionist.
Provide accurate ingredient information for food items.
Respond concisely with only the ingredients."""
        
        response = self.generate(prompt, system_prompt)
        
        if response and len(response) < 500:
            return response.strip()
        return ""
        
    def generate_serving_size(self, description: str, category: str = None) -> Dict[str, Any]:
        """Generate serving size synchronously"""
        prompt = f"""Food item: {description}
{f'Category: {category}' if category else ''}

Provide the standard serving size for this food using USDA guidelines.

Common serving sizes:
- Vegetables: 1 cup raw (85g), 1/2 cup cooked (75g)
- Fruits: 1 medium piece (150g), 1 cup chopped (150g)
- Grains: 1 slice bread (30g), 1/2 cup cooked rice/pasta (75g)
- Proteins: 3 oz cooked meat (85g), 1 large egg (50g)
- Dairy: 1 cup milk (240ml), 1 oz cheese (28g)

Return ONLY in format: "number|unit"
Examples: "100|g", "240|ml", "28|g", "1|cup"

If unsure, use grams as default unit."""
        
        system_prompt = """You are a nutrition expert providing standard serving sizes.
Use USDA standard serving sizes when available."""
        
        response = self.generate(prompt, system_prompt)
        
        if response and "|" in response:
            try:
                parts = response.strip().split("|")
                if len(parts) == 2:
                    size_str, unit = parts
                    try:
                        size = float(size_str)
                        return {"size": size, "unit": unit.strip()}
                    except ValueError:
                        if size_str.strip().replace(".", "").isdigit():
                            return {"size": float(size_str), "unit": unit.strip()}
            except Exception as e:
                logger.debug(f"Could not parse serving size response: {response}")
        
        return {}
        
    def check_health(self) -> bool:
        """Check if Ollama service is healthy"""
        try:
            response = requests.get(f"{self.config.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False