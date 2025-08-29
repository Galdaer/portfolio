"""
LLM Client for Medical Text Generation
Uses Ollama for local, PHI-safe medical text generation
"""

import logging
import asyncio
import aiohttp
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration for LLM client"""
    model: str = "llama3.2:latest"  # Default model
    base_url: str = "http://172.20.0.10:11434"  # Ollama service URL
    temperature: float = 0.3  # Lower temperature for medical accuracy
    max_tokens: int = 500
    timeout: float = 30.0


class OllamaClient:
    """
    Client for communicating with Ollama for medical text generation.
    
    All processing is local and PHI-safe.
    """
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """
        Initialize Ollama client.
        
        Args:
            config: LLM configuration (uses defaults if not provided)
        """
        self.config = config or LLMConfig()
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
            
    async def generate_medical_synonyms(self, description: str, 
                                       medical_entities: List[str] = None) -> List[str]:
        """
        Generate medical synonyms for an ICD10 description.
        
        Args:
            description: ICD10 description
            medical_entities: Optional list of medical entities found in description
            
        Returns:
            List of generated synonyms
        """
        entities_context = ""
        if medical_entities:
            entities_context = f"\nMedical entities found: {', '.join(medical_entities)}"
        
        prompt = f"""Generate medical synonyms and alternative terms for this ICD-10 description:
"{description}"{entities_context}

Provide synonyms that medical professionals would use, including:
- Common medical abbreviations
- Alternative medical terminology
- Colloquial medical terms
- Related medical phrases

Return ONLY a comma-separated list of synonyms, no explanations or numbering.
Example format: term1, term2, term3"""

        system_prompt = """You are a medical terminology expert helping to enhance ICD-10 code descriptions.
Focus on generating accurate, clinically relevant synonyms that healthcare professionals would recognize."""
        
        response = await self.generate(prompt, system_prompt)
        
        # Parse response into list
        if response:
            synonyms = [s.strip() for s in response.split(',') if s.strip()]
            # Filter out the original description and clean up
            synonyms = [s for s in synonyms if s.lower() != description.lower() and len(s) > 2]
            return synonyms[:20]  # Limit to top 20 synonyms
        return []
        
    async def generate_inclusion_notes(self, description: str, 
                                      medical_concepts: Dict[str, List[str]] = None) -> List[str]:
        """
        Generate inclusion notes for an ICD10 code.
        
        Args:
            description: ICD10 description
            medical_concepts: Optional medical concepts extracted from description
            
        Returns:
            List of inclusion notes
        """
        context = ""
        if medical_concepts:
            context = f"\nMedical context: {json.dumps(medical_concepts, indent=2)}"
        
        prompt = f"""Generate inclusion notes for this ICD-10 code:
"{description}"{context}

What conditions, symptoms, or scenarios SHOULD BE INCLUDED under this code?
Focus on what IS covered by this diagnostic code.

Return ONLY a semicolon-separated list of inclusion criteria, no explanations.
Example format: includes condition A; includes symptom B; includes scenario C"""

        system_prompt = """You are a medical coding expert helping to clarify ICD-10 code coverage.
Generate specific, clinically accurate inclusion criteria."""
        
        response = await self.generate(prompt, system_prompt)
        
        if response:
            notes = [n.strip() for n in response.split(';') if n.strip()]
            # Clean up common prefixes
            notes = [n.replace("includes ", "").replace("Includes ", "") for n in notes]
            return notes[:10]  # Limit to top 10 notes
        return []
        
    async def generate_exclusion_notes(self, description: str,
                                      medical_concepts: Dict[str, List[str]] = None) -> List[str]:
        """
        Generate exclusion notes for an ICD10 code.
        
        Args:
            description: ICD10 description
            medical_concepts: Optional medical concepts extracted from description
            
        Returns:
            List of exclusion notes
        """
        context = ""
        if medical_concepts:
            context = f"\nMedical context: {json.dumps(medical_concepts, indent=2)}"
        
        prompt = f"""Generate exclusion notes for this ICD-10 code:
"{description}"{context}

What conditions, symptoms, or scenarios should NOT be coded here?
What is EXCLUDED from this diagnostic code?

Return ONLY a semicolon-separated list of exclusion criteria, no explanations.
Example format: excludes condition X; excludes symptom Y; excludes scenario Z"""

        system_prompt = """You are a medical coding expert helping to clarify ICD-10 code boundaries.
Generate specific exclusions that distinguish this code from similar conditions."""
        
        response = await self.generate(prompt, system_prompt)
        
        if response:
            notes = [n.strip() for n in response.split(';') if n.strip()]
            # Clean up common prefixes
            notes = [n.replace("excludes ", "").replace("Excludes ", "") for n in notes]
            return notes[:10]  # Limit to top 10 notes
        return []
        
    async def identify_related_codes(self, description: str, code: str) -> List[str]:
        """
        Identify related ICD10 codes based on medical understanding.
        
        Args:
            description: ICD10 description
            code: ICD10 code
            
        Returns:
            List of potentially related code patterns
        """
        prompt = f"""For ICD-10 code {code}: "{description}"

Identify related ICD-10 code patterns for:
- Complications of this condition
- Associated conditions
- Similar diagnoses
- Parent/child relationships

Return ONLY ICD-10 code patterns (like E11.*, I10, etc.), comma-separated.
Focus on codes that would likely be used together or are medically related."""

        system_prompt = """You are an ICD-10 coding expert identifying medically related diagnostic codes."""
        
        response = await self.generate(prompt, system_prompt)
        
        if response:
            codes = [c.strip() for c in response.split(',') if c.strip()]
            # Filter valid ICD10 patterns
            valid_codes = []
            for c in codes:
                # Basic ICD10 code pattern validation
                if len(c) >= 3 and (c[0].isalpha() or c[:2].isalpha()):
                    valid_codes.append(c)
            return valid_codes[:5]  # Limit to top 5 related codes
        return []
        
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
    """Synchronous wrapper for Ollama client"""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        self.client = OllamaClient(config)
        
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Synchronous wrapper for generate"""
        return asyncio.run(self.client.generate(prompt, system_prompt))
        
    def generate_medical_synonyms(self, description: str, 
                                 medical_entities: List[str] = None) -> List[str]:
        """Synchronous wrapper for generate_medical_synonyms"""
        return asyncio.run(self.client.generate_medical_synonyms(description, medical_entities))
        
    def generate_inclusion_notes(self, description: str,
                                medical_concepts: Dict[str, List[str]] = None) -> List[str]:
        """Synchronous wrapper for generate_inclusion_notes"""
        return asyncio.run(self.client.generate_inclusion_notes(description, medical_concepts))
        
    def generate_exclusion_notes(self, description: str,
                                medical_concepts: Dict[str, List[str]] = None) -> List[str]:
        """Synchronous wrapper for generate_exclusion_notes"""
        return asyncio.run(self.client.generate_exclusion_notes(description, medical_concepts))