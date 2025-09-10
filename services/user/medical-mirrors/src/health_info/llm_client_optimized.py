"""
Optimized LLM Client for Food Text Generation
Makes a single LLM call per food item instead of multiple calls
"""

import logging
import requests
import os
import sys
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json

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


class OptimizedOllamaClient:
    """
    Optimized client for Ollama that makes a single call per food item.
    """
    
    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config if config else LLMConfig()
        self.timeout = 60  # Longer timeout for comprehensive generation
        
    def generate_all_food_enhancements(self, description: str, category: str = None,
                                      food_entities: List[str] = None) -> Dict[str, Any]:
        """
        Generate all food enhancements in a single LLM call.
        Returns a dictionary with scientific_name, common_names, ingredients, and serving_size.
        """
        
        entities_context = f"\nExtracted entities: {', '.join(food_entities)}" if food_entities else ""
        category_context = f"\nCategory: {category}" if category else ""
        
        prompt = f"""Analyze this food item and provide comprehensive information:

Food item: {description}{category_context}{entities_context}

Provide the following information in JSON format:
1. scientific_name: A SINGLE scientific/botanical name as a STRING (for mixed items, use the primary ingredient or leave empty)
2. common_names: List of up to 5 common/alternative names as an ARRAY of STRINGS
3. ingredients: Main ingredients as a SINGLE STRING separated by commas
4. serving_size: Standard USDA serving size as a NUMBER (no units)
5. serving_unit: Unit for the serving size as a STRING (e.g., "g", "ml", "oz", "cup")

IMPORTANT RULES:
- scientific_name MUST be a single string, NOT a dictionary or list
- For multi-ingredient items, use the primary ingredient's scientific name or leave empty
- common_names MUST be an array of simple strings
- ingredients MUST be a single comma-separated string

Respond ONLY with valid JSON in this exact format:
{{
  "scientific_name": "Ananas comosus",
  "common_names": ["pineapple", "ananas"],
  "ingredients": "pineapple, papaya, banana, guava",
  "serving_size": 100,
  "serving_unit": "g"
}}"""

        system_prompt = """You are a food science expert. Provide accurate, concise information.
CRITICAL: scientific_name must be a SINGLE STRING (not dict/list). For mixed foods, use primary ingredient or empty string.
Use USDA standard serving sizes. Return only valid JSON, no explanations."""
        
        # Build the full prompt
        full_prompt = f"{system_prompt}\n\n{prompt}"
        
        try:
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
                response_text = data.get("response", "")
                
                # Try to parse JSON from response
                try:
                    # Clean up response - sometimes LLM adds markdown formatting
                    if "```json" in response_text:
                        response_text = response_text.split("```json")[1].split("```")[0]
                    elif "```" in response_text:
                        response_text = response_text.split("```")[1].split("```")[0]
                    
                    result = json.loads(response_text.strip())
                    
                    # Validate and clean the result with robust type handling
                    
                    # Handle scientific_name - ensure it's a string
                    scientific_name = result.get('scientific_name', '')
                    if isinstance(scientific_name, dict):
                        # If dict, take the first value or format as "Mixed"
                        if scientific_name:
                            # Get first value from dict
                            first_value = next(iter(scientific_name.values()), '')
                            scientific_name = str(first_value) if first_value else ''
                        else:
                            scientific_name = ''
                    elif isinstance(scientific_name, list):
                        # If list, take the first item or mark as "Mixed"
                        if scientific_name:
                            # If list of dicts, extract first scientific name
                            if isinstance(scientific_name[0], dict):
                                first_item = next(iter(scientific_name[0].values()), '')
                                scientific_name = str(first_item) if first_item else ''
                            else:
                                scientific_name = str(scientific_name[0])
                        else:
                            scientific_name = ''
                    else:
                        scientific_name = str(scientific_name) if scientific_name else ''
                    
                    # Handle common_names - ensure it's properly formatted
                    common_names = result.get('common_names', [])
                    if isinstance(common_names, list):
                        # Filter out any dict/complex items and convert to strings
                        clean_names = []
                        for name in common_names:
                            if isinstance(name, str):
                                clean_names.append(name)
                            elif isinstance(name, dict):
                                # Skip dict entries
                                continue
                        common_names = ', '.join(clean_names)
                    elif isinstance(common_names, str):
                        common_names = common_names
                    else:
                        common_names = ''
                    
                    # Handle ingredients - ensure it's a string
                    ingredients = result.get('ingredients', '')
                    if isinstance(ingredients, list):
                        ingredients = ', '.join(str(i) for i in ingredients if i)
                    elif isinstance(ingredients, dict):
                        # Format dict as comma-separated values
                        ingredients = ', '.join(str(v) for v in ingredients.values() if v)
                    else:
                        ingredients = str(ingredients) if ingredients else ''
                    
                    # Handle serving size - ensure it's numeric
                    serving_size = result.get('serving_size')
                    if serving_size is not None:
                        try:
                            serving_size = float(serving_size)
                        except (ValueError, TypeError):
                            serving_size = None
                    
                    enhancements = {
                        'scientific_name': scientific_name,
                        'common_names': common_names,
                        'ingredients': ingredients,
                        'serving_size': serving_size,
                        'serving_size_unit': str(result.get('serving_unit', ''))
                    }
                    
                    # Clean up N/A values
                    if enhancements['scientific_name'] in ['N/A', 'n/a', 'NA']:
                        enhancements['scientific_name'] = ''
                    
                    return enhancements
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    logger.debug(f"Response was: {response_text[:500]}")
                    return {}
            else:
                logger.error(f"Ollama generate failed: {response.status_code}")
                return {}
                
        except requests.Timeout:
            logger.error("Ollama request timed out")
            return {}
        except Exception as e:
            logger.error(f"Ollama generate error: {e}")
            return {}
    
    def check_health(self) -> bool:
        """Check if Ollama service is healthy"""
        try:
            response = requests.get(f"{self.config.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False