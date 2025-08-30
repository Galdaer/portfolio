"""
SciSpacy Client for Food Entity Extraction
Connects to the SciSpacy service for food and nutrition NLP analysis
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
class FoodEntity:
    """Represents a food entity extracted by SciSpacy"""
    text: str
    label: str  # Entity type (FOOD, CHEMICAL, ORGANISM, etc.)
    start: int
    end: int
    metadata: Optional[Dict[str, Any]] = None
    context: Optional[str] = None
    priority: Optional[str] = None


class SciSpacyClient:
    """
    Client for communicating with the SciSpacy biomedical NLP service for food analysis.
    
    The SciSpacy service provides:
    - Food and nutrition entity recognition
    - Chemical compound identification
    - Organism and ingredient detection
    - Biomedical text analysis relevant to foods
    """
    
    def __init__(self, base_url: str = None):
        """
        Initialize SciSpacy client for food analysis.
        
        Args:
            base_url: SciSpacy service URL (uses config if not provided)
        """
        if base_url is None:
            config = get_config()
            base_url = config.get_endpoint_url("scispacy")
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
            
    async def analyze_text(self, text: str, enrich: bool = True) -> Dict[str, Any]:
        """
        Analyze text for food-related entities using SciSpacy.
        
        Args:
            text: Text to analyze
            enrich: Whether to include enriched metadata and relationships
            
        Returns:
            Dictionary containing entities, metadata, and analysis results
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
            
        try:
            async with self.session.post(
                f"{self.base_url}/analyze",
                json={"text": text, "enrich": enrich},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"SciSpacy analysis failed: {error_text}")
                    return {"entities": [], "error": error_text}
                    
        except asyncio.TimeoutError:
            logger.error("SciSpacy request timed out")
            return {"entities": [], "error": "timeout"}
        except Exception as e:
            logger.error(f"SciSpacy request failed: {e}")
            return {"entities": [], "error": str(e)}
            
    async def extract_food_entities(self, text: str) -> List[FoodEntity]:
        """
        Extract food-related entities from text and return structured objects.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of FoodEntity objects
        """
        result = await self.analyze_text(text, enrich=True)
        
        entities = []
        for entity_data in result.get("entities", []):
            entity = FoodEntity(
                text=entity_data.get("text", ""),
                label=entity_data.get("label", ""),
                start=entity_data.get("start", 0),
                end=entity_data.get("end", 0),
                metadata=entity_data.get("metadata"),
                context=entity_data.get("context"),
                priority=entity_data.get("priority")
            )
            entities.append(entity)
            
        return entities
        
    async def get_entity_types(self, text: str) -> Dict[str, List[str]]:
        """
        Get entities grouped by type from text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary mapping entity types to lists of entity texts
        """
        entities = await self.extract_food_entities(text)
        
        entity_types = {}
        for entity in entities:
            if entity.label not in entity_types:
                entity_types[entity.label] = []
            if entity.text not in entity_types[entity.label]:
                entity_types[entity.label].append(entity.text)
                
        return entity_types
        
    async def extract_food_concepts(self, description: str) -> Dict[str, Any]:
        """
        Extract food concepts relevant for food enhancement.
        
        Args:
            description: Food description text
            
        Returns:
            Dictionary with organisms, chemicals, ingredients, etc.
        """
        entity_types = await self.get_entity_types(description)
        
        # Map SciSpacy entity types to food concepts
        concepts = {
            "organisms": entity_types.get("ORGANISM", []),
            "chemicals": entity_types.get("SIMPLE_CHEMICAL", []) + 
                        entity_types.get("AMINO_ACID", []),
            "substances": entity_types.get("ORGANISM_SUBSTANCE", []),
            "anatomy": entity_types.get("ANATOMICAL_SYSTEM", []) + 
                      entity_types.get("ORGAN", []) + 
                      entity_types.get("TISSUE", []),
            "cells": entity_types.get("CELL", []) + 
                    entity_types.get("CELLULAR_COMPONENT", []),
            "pathological": entity_types.get("PATHOLOGICAL_FORMATION", []),
            "all_entities": [e for entities in entity_types.values() for e in entities]
        }
        
        return concepts
        
    def check_health(self) -> bool:
        """
        Check if SciSpacy service is healthy.
        
        Returns:
            True if service is responsive, False otherwise
        """
        import requests
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False


# Synchronous wrapper for non-async contexts
class SciSpacyClientSync:
    """Synchronous client for SciSpacy using requests library"""
    
    def __init__(self, base_url: str = None):
        if base_url is None:
            config = get_config()
            base_url = config.get_endpoint_url("scispacy")
        self.base_url = base_url
        self.timeout = 30
        
    def analyze_text(self, text: str, enrich: bool = True) -> Dict[str, Any]:
        """Analyze text synchronously using requests"""
        try:
            response = requests.post(
                f"{self.base_url}/analyze",
                json={"text": text, "enrich": enrich},
                timeout=self.timeout
            )
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"SciSpacy analyze failed: {response.status_code}")
                return {}
        except Exception as e:
            logger.error(f"SciSpacy analyze error: {e}")
            return {}
        
    def extract_food_entities(self, text: str) -> List[FoodEntity]:
        """Extract food entities synchronously"""
        result = self.analyze_text(text, enrich=True)
        entities = []
        for entity_data in result.get("entities", []):
            entities.append(FoodEntity(
                text=entity_data.get("text", ""),
                label=entity_data.get("label", "UNKNOWN"),
                start=entity_data.get("start", 0),
                end=entity_data.get("end", 0),
                metadata=entity_data.get("metadata"),
                context=entity_data.get("context"),
                priority=entity_data.get("priority")
            ))
        return entities
        
    def get_entity_types(self, text: str) -> Dict[str, List[str]]:
        """Get entity types synchronously using requests"""
        result = self.analyze_text(text, enrich=False)
        entity_types = {}
        for entity in result.get("entities", []):
            label = entity.get("label", "UNKNOWN")
            if label not in entity_types:
                entity_types[label] = []
            entity_types[label].append(entity.get("text", ""))
        return entity_types
        
    def extract_food_concepts(self, description: str) -> Dict[str, Any]:
        """Extract food concepts synchronously using requests with fallback to token analysis"""
        try:
            response = requests.post(
                f"{self.base_url}/analyze",
                json={"text": description, "enrich": True},
                timeout=self.timeout
            )
            if response.status_code == 200:
                data = response.json()
                entities = data.get("entities", [])
                tokens = data.get("tokens", [])
                
                # Extract relevant food-related entities
                concepts = {
                    "chemicals": [],
                    "organisms": [],
                    "foods": [],
                    "compounds": [],
                    "all_entities": []  # For Ollama context
                }
                
                # First try to get entities
                for entity in entities:
                    entity_type = entity.get("label", "")
                    entity_text = entity.get("text", "")
                    
                    if entity_type == "CHEMICAL":
                        concepts["chemicals"].append(entity_text)
                        concepts["all_entities"].append(entity_text)
                    elif entity_type == "ORGANISM":
                        concepts["organisms"].append(entity_text)
                        concepts["all_entities"].append(entity_text)
                    elif entity_type in ["FOOD", "PRODUCT"]:
                        concepts["foods"].append(entity_text)
                        concepts["all_entities"].append(entity_text)
                    elif entity_type == "COMPOUND":
                        concepts["compounds"].append(entity_text)
                        concepts["all_entities"].append(entity_text)
                
                # Fallback: If no entities found, extract nouns as potential food items
                if not concepts["all_entities"] and tokens:
                    # Extract nouns and proper nouns as potential food/ingredient names
                    for token in tokens:
                        if token.get("pos") in ["NOUN", "PROPN"] and token.get("is_alpha"):
                            text = token.get("text", "")
                            # Skip common stop words and very short words
                            if len(text) > 2 and text.lower() not in ["the", "and", "with", "for", "from"]:
                                concepts["all_entities"].append(text)
                                # Heuristically categorize based on common patterns
                                if any(suffix in text.lower() for suffix in ["berry", "fruit", "nut", "seed", "bean"]):
                                    concepts["organisms"].append(text)
                                elif any(word in text.lower() for word in ["vitamin", "acid", "protein", "sugar"]):
                                    concepts["chemicals"].append(text)
                                else:
                                    concepts["foods"].append(text)
                
                return concepts
            else:
                logger.error(f"SciSpacy extract failed: {response.status_code}")
                return {"chemicals": [], "organisms": [], "foods": [], "compounds": [], "all_entities": []}
        except Exception as e:
            logger.error(f"SciSpacy extract error: {e}")
            return {"chemicals": [], "organisms": [], "foods": [], "compounds": [], "all_entities": []}
        
    def check_health(self) -> bool:
        """Check if SciSpacy service is healthy"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False