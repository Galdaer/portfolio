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
1. scientific_name: The scientific/botanical/zoological name (or "N/A" if not applicable)
2. common_names: List of up to 5 common/alternative names
3. ingredients: Main ingredients or components (if inferrable)
4. serving_size: Standard USDA serving size as a number
5. serving_unit: Unit for the serving size (e.g., "g", "ml", "oz", "cup")

Respond ONLY with valid JSON in this exact format:
{{
  "scientific_name": "...",
  "common_names": ["name1", "name2", ...],
  "ingredients": "ingredient1, ingredient2, ...",
  "serving_size": 100,
  "serving_unit": "g"
}}"""

        system_prompt = """You are a food science expert. Provide accurate, concise information.
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
                    
                    # Validate and clean the result
                    enhancements = {
                        'scientific_name': result.get('scientific_name', ''),
                        'common_names': ', '.join(result.get('common_names', [])) if isinstance(result.get('common_names'), list) else '',
                        'ingredients': result.get('ingredients', ''),
                        'serving_size': result.get('serving_size'),
                        'serving_size_unit': result.get('serving_unit', '')
                    }
                    
                    # Clean up N/A values
                    if enhancements['scientific_name'] == 'N/A':
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