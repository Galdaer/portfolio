"""
AI-Driven ICD-10 Data Enrichment Module
Uses SciSpacy NLP and Ollama LLM instead of hardcoded medical knowledge

This module leverages:
- SciSpacy for medical entity extraction
- Ollama for synonym and note generation
- No hardcoded medical dictionaries
- Dynamic, context-aware enhancement
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import time

from sqlalchemy import text
from database import get_db_session, get_thread_safe_session

from .scispacy_client import SciSpacyClient, SciSpacyClientSync
from .llm_client import OllamaClient, OllamaClientSync, LLMConfig

logger = logging.getLogger(__name__)


class ICD10AIEnhancer:
    """
    AI-driven ICD10 enhancement using NLP and LLM.
    
    No hardcoded medical knowledge - uses:
    - SciSpacy for medical entity recognition
    - Ollama for intelligent text generation
    - Context-aware enhancement based on actual medical understanding
    """
    
    def __init__(self, batch_size: int = 100):
        """
        Initialize AI-driven enhancer.
        
        Args:
            batch_size: Number of codes to process in each batch
        """
        self.batch_size = batch_size
        
        # Initialize AI clients
        self.scispacy_client = SciSpacyClientSync()
        self.ollama_client = OllamaClientSync()
        
        # Statistics tracking
        self.stats = {
            'processed': 0,
            'enhanced': 0,
            'synonyms_added': 0,
            'inclusion_notes_added': 0,
            'exclusion_notes_added': 0,
            'relationships_added': 0,
            'ai_calls': 0,
            'ai_failures': 0
        }
        
        # Rate limiting for AI services
        self.last_ai_call = 0
        self.min_ai_interval = 0.1  # Minimum seconds between AI calls
        
    def enhance_icd10_database(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Enhance ICD10 database using AI-driven approach.
        
        Args:
            limit: Optional limit on number of codes to process
            
        Returns:
            Enhancement statistics
        """
        start_time = datetime.now()
        logger.info("Starting AI-driven ICD10 enhancement")
        
        # Check AI service health
        if not self._check_ai_services():
            logger.error("AI services not available, cannot proceed with enhancement")
            return self.stats
        
        with get_db_session() as session:
            # Get codes that need enhancement
            query = """
                SELECT code, description, 
                       synonyms, inclusion_notes, exclusion_notes, 
                       parent_code, children_codes
                FROM icd10_codes
                WHERE (synonyms IS NULL OR synonyms = '[]'::jsonb)
                   OR (inclusion_notes IS NULL OR inclusion_notes = '[]'::jsonb)
                   OR (exclusion_notes IS NULL OR exclusion_notes = '[]'::jsonb)
                ORDER BY code
            """
            
            if limit:
                query += f" LIMIT {limit}"
                
            result = session.execute(text(query))
            codes_to_enhance = result.fetchall()
            
            total_codes = len(codes_to_enhance)
            logger.info(f"Found {total_codes} codes needing AI enhancement")
            
            # Process in batches
            for i in range(0, total_codes, self.batch_size):
                batch = codes_to_enhance[i:i + self.batch_size]
                self._process_batch(session, batch)
                
                # Progress logging
                progress = min(i + self.batch_size, total_codes)
                logger.info(f"AI Enhancement progress: {progress}/{total_codes} "
                           f"({progress/total_codes*100:.1f}%)")
                
            session.commit()
            
        # Calculate final statistics
        end_time = datetime.now()
        duration = end_time - start_time
        
        self.stats['duration'] = str(duration)
        self.stats['success_rate'] = (
            (self.stats['enhanced'] / self.stats['processed'] * 100)
            if self.stats['processed'] > 0 else 0
        )
        
        logger.info(f"AI Enhancement completed in {duration}")
        logger.info(f"Statistics: {self.stats}")
        
        return self.stats
        
    def _check_ai_services(self) -> bool:
        """Check if AI services are available"""
        scispacy_ok = self.scispacy_client.check_health()
        ollama_ok = self.ollama_client.check_health()
        
        if not scispacy_ok:
            logger.warning("SciSpacy service not available")
        if not ollama_ok:
            logger.warning("Ollama service not available")
            
        return scispacy_ok and ollama_ok
        
    def _process_batch(self, session, batch):
        """Process a batch of ICD10 codes with AI enhancement"""
        
        for row in batch:
            try:
                code = row.code
                description = row.description
                
                # Skip if no description
                if not description:
                    continue
                    
                self.stats['processed'] += 1
                
                # Rate limiting
                self._rate_limit()
                
                # Extract medical entities using SciSpacy
                medical_concepts = self._extract_medical_concepts(description)
                
                # Generate enhancements using Ollama
                enhancements = self._generate_enhancements(
                    code, description, medical_concepts
                )
                
                # Build hierarchical relationships
                hierarchy = self._build_hierarchy(code, session)
                enhancements.update(hierarchy)
                
                # Update database if we got enhancements
                if self._has_enhancements(enhancements):
                    self._update_code(session, code, enhancements)
                    self.stats['enhanced'] += 1
                    
            except Exception as e:
                logger.error(f"Error processing code {row.code}: {e}")
                self.stats['ai_failures'] += 1
                continue
                
    def _rate_limit(self):
        """Apply rate limiting for AI service calls"""
        elapsed = time.time() - self.last_ai_call
        if elapsed < self.min_ai_interval:
            time.sleep(self.min_ai_interval - elapsed)
        self.last_ai_call = time.time()
        
    def _extract_medical_concepts(self, description: str) -> Dict[str, Any]:
        """Extract medical concepts using SciSpacy"""
        try:
            self.stats['ai_calls'] += 1
            concepts = self.scispacy_client.extract_medical_concepts(description)
            return concepts
        except Exception as e:
            logger.error(f"SciSpacy extraction failed: {e}")
            self.stats['ai_failures'] += 1
            return {}
            
    def _generate_enhancements(self, code: str, description: str, 
                              medical_concepts: Dict[str, Any]) -> Dict[str, Any]:
        """Generate enhancements using Ollama LLM"""
        
        enhancements = {
            'synonyms': [],
            'inclusion_notes': [],
            'exclusion_notes': []
        }
        
        # Get medical entities for context
        medical_entities = medical_concepts.get('all_entities', [])
        
        try:
            # Generate synonyms
            self.stats['ai_calls'] += 1
            synonyms = self.ollama_client.generate_medical_synonyms(
                description, medical_entities
            )
            if synonyms:
                enhancements['synonyms'] = synonyms
                self.stats['synonyms_added'] += len(synonyms)
                
            # Generate inclusion notes
            self.stats['ai_calls'] += 1
            inclusion_notes = self.ollama_client.generate_inclusion_notes(
                description, medical_concepts
            )
            if inclusion_notes:
                enhancements['inclusion_notes'] = inclusion_notes
                self.stats['inclusion_notes_added'] += len(inclusion_notes)
                
            # Generate exclusion notes
            self.stats['ai_calls'] += 1
            exclusion_notes = self.ollama_client.generate_exclusion_notes(
                description, medical_concepts
            )
            if exclusion_notes:
                enhancements['exclusion_notes'] = exclusion_notes
                self.stats['exclusion_notes_added'] += len(exclusion_notes)
                
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            self.stats['ai_failures'] += 1
            
        return enhancements
        
    def _build_hierarchy(self, code: str, session) -> Dict[str, Any]:
        """Build hierarchical relationships for the code"""
        hierarchy = {}
        
        # Find parent code (existing logic, not AI-driven)
        parent_code = self._find_parent_code(code)
        if parent_code:
            hierarchy['parent_code'] = parent_code
            
        # Find children codes
        children_query = text("""
            SELECT code FROM icd10_codes 
            WHERE code LIKE :pattern AND code != :code
            ORDER BY code
        """)
        
        # Pattern for finding children (codes that start with this code)
        if '.' in code:
            pattern = f"{code}%"
        else:
            pattern = f"{code}.%"
            
        result = session.execute(children_query, {'pattern': pattern, 'code': code})
        children = [row.code for row in result.fetchall()]
        
        if children:
            hierarchy['children_codes'] = children
            self.stats['relationships_added'] += len(children)
            
        return hierarchy
        
    def _find_parent_code(self, code: str) -> Optional[str]:
        """Find parent code based on ICD10 structure"""
        if not code or len(code) <= 3:
            return None
            
        if '.' in code:
            parts = code.split('.')
            base = parts[0]
            decimal = parts[1] if len(parts) > 1 else ''
            
            if len(decimal) > 1:
                # E11.21 → E11.2
                return f"{base}.{decimal[:-1]}"
            elif len(decimal) == 1:
                # E11.9 → E11
                return base
        else:
            # Handle non-decimal codes
            if len(code) > 3:
                return code[:-1]
                
        return None
        
    def _has_enhancements(self, enhancements: Dict[str, Any]) -> bool:
        """Check if we have any enhancements to apply"""
        return (
            len(enhancements.get('synonyms', [])) > 0 or
            len(enhancements.get('inclusion_notes', [])) > 0 or
            len(enhancements.get('exclusion_notes', [])) > 0 or
            enhancements.get('parent_code') is not None or
            len(enhancements.get('children_codes', [])) > 0
        )
        
    def _update_code(self, session, code: str, enhancements: Dict[str, Any]):
        """Update ICD10 code with AI-generated enhancements"""
        
        update_parts = []
        params = {'code': code}
        
        if enhancements.get('synonyms'):
            update_parts.append("synonyms = :synonyms")
            params['synonyms'] = json.dumps(enhancements['synonyms'])
            
        if enhancements.get('inclusion_notes'):
            update_parts.append("inclusion_notes = :inclusion_notes")
            params['inclusion_notes'] = json.dumps(enhancements['inclusion_notes'])
            
        if enhancements.get('exclusion_notes'):
            update_parts.append("exclusion_notes = :exclusion_notes")
            params['exclusion_notes'] = json.dumps(enhancements['exclusion_notes'])
            
        if enhancements.get('parent_code'):
            update_parts.append("parent_code = :parent_code")
            params['parent_code'] = enhancements['parent_code']
            
        if enhancements.get('children_codes'):
            update_parts.append("children_codes = :children_codes")
            params['children_codes'] = json.dumps(enhancements['children_codes'])
            
        if update_parts:
            update_query = text(f"""
                UPDATE icd10_codes 
                SET {', '.join(update_parts)},
                    updated_at = CURRENT_TIMESTAMP
                WHERE code = :code
            """)
            
            session.execute(update_query, params)


# Async version for use in async contexts
class ICD10AIEnhancerAsync:
    """Async version of the AI-driven ICD10 enhancer"""
    
    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
        self.scispacy_client = None
        self.ollama_client = None
        self.stats = {
            'processed': 0,
            'enhanced': 0,
            'synonyms_added': 0,
            'inclusion_notes_added': 0,
            'exclusion_notes_added': 0,
            'relationships_added': 0,
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
            
    # Async versions of all methods would go here...
    # (Similar to sync version but with async/await)


import json  # Add this import at the top with other imports