"""
SciSpacy Client for Medical Entity Extraction
Connects to the SciSpacy service for biomedical NLP analysis
"""

import logging
import asyncio
import aiohttp
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MedicalEntity:
    """Represents a medical entity extracted by SciSpacy"""
    text: str
    label: str  # Entity type (DISEASE, ANATOMY, CHEMICAL, etc.)
    start: int
    end: int
    metadata: Optional[Dict[str, Any]] = None
    context: Optional[str] = None
    priority: Optional[str] = None


class SciSpacyClient:
    """
    Client for communicating with the SciSpacy biomedical NLP service.
    
    The SciSpacy service provides:
    - Medical entity recognition (16 entity types)
    - Entity relationships and context
    - Biomedical text analysis
    """
    
    def __init__(self, base_url: str = "http://172.20.0.14:8080"):
        """
        Initialize SciSpacy client.
        
        Args:
            base_url: SciSpacy service URL (default is Docker network address)
        """
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
        Analyze text for biomedical entities using SciSpacy.
        
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
            
    async def extract_medical_entities(self, text: str) -> List[MedicalEntity]:
        """
        Extract medical entities from text and return structured objects.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of MedicalEntity objects
        """
        result = await self.analyze_text(text, enrich=True)
        
        entities = []
        for entity_data in result.get("entities", []):
            entity = MedicalEntity(
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
        entities = await self.extract_medical_entities(text)
        
        entity_types = {}
        for entity in entities:
            if entity.label not in entity_types:
                entity_types[entity.label] = []
            if entity.text not in entity_types[entity.label]:
                entity_types[entity.label].append(entity.text)
                
        return entity_types
        
    async def extract_medical_concepts(self, description: str) -> Dict[str, Any]:
        """
        Extract medical concepts relevant for ICD10 enhancement.
        
        Args:
            description: ICD10 description text
            
        Returns:
            Dictionary with diseases, anatomy, symptoms, procedures, etc.
        """
        entity_types = await self.get_entity_types(description)
        
        # Map SciSpacy entity types to medical concepts
        concepts = {
            "diseases": entity_types.get("CANCER", []) + 
                       entity_types.get("PATHOLOGICAL_FORMATION", []),
            "anatomy": entity_types.get("ANATOMICAL_SYSTEM", []) + 
                      entity_types.get("ORGAN", []) + 
                      entity_types.get("TISSUE", []) +
                      entity_types.get("MULTI-TISSUE_STRUCTURE", []),
            "chemicals": entity_types.get("SIMPLE_CHEMICAL", []) + 
                        entity_types.get("AMINO_ACID", []),
            "organisms": entity_types.get("ORGANISM", []),
            "cells": entity_types.get("CELL", []) + 
                    entity_types.get("CELLULAR_COMPONENT", []),
            "substances": entity_types.get("ORGANISM_SUBSTANCE", []),
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
    """Synchronous wrapper for SciSpacy client"""
    
    def __init__(self, base_url: str = "http://172.20.0.14:8080"):
        self.client = SciSpacyClient(base_url)
        
    def analyze_text(self, text: str, enrich: bool = True) -> Dict[str, Any]:
        """Synchronous wrapper for analyze_text"""
        return asyncio.run(self.client.analyze_text(text, enrich))
        
    def extract_medical_entities(self, text: str) -> List[MedicalEntity]:
        """Synchronous wrapper for extract_medical_entities"""
        return asyncio.run(self.client.extract_medical_entities(text))
        
    def get_entity_types(self, text: str) -> Dict[str, List[str]]:
        """Synchronous wrapper for get_entity_types"""
        return asyncio.run(self.client.get_entity_types(text))
        
    def extract_medical_concepts(self, description: str) -> Dict[str, Any]:
        """Synchronous wrapper for extract_medical_concepts"""
        return asyncio.run(self.client.extract_medical_concepts(description))