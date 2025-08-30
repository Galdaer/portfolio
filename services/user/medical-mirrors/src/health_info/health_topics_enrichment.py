"""
AI-Driven Health Topics Enrichment Module
Enhanced medical entity extraction, ICD-10 mapping, and clinical relevance scoring for health topics

This module provides comprehensive AI enhancement for health topics including:
- Medical entity extraction using SciSpacy NLP
- ICD-10 condition mapping
- Clinical relevance scoring (0.0-1.0)
- Topic classification (prevention vs treatment)
- Risk factor identification
- Related medication extraction
- Quality improvements for keywords and summaries
"""

import asyncio
import json
import logging
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field

import aiohttp

import sys
from pathlib import Path

# Add parent directory to path for imports  
sys.path.append(str(Path(__file__).parent.parent))

from config_loader import get_config

logger = logging.getLogger(__name__)

# Try to import AI clients - may not be available if services are down
try:
    from icd10.scispacy_client import SciSpacyClientSync
    from icd10.llm_client import OllamaClientSync
    AI_CLIENTS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"AI clients not available: {e}")
    SciSpacyClientSync = None
    OllamaClientSync = None
    AI_CLIENTS_AVAILABLE = False


@dataclass
class HealthTopicEnhancement:
    """Enhanced health topic data structure"""
    # Core topic information
    topic_id: str
    title: str
    original_data: Dict[str, Any]
    
    # AI-enhanced fields
    medical_entities: Dict[str, List[str]] = field(default_factory=dict)
    icd10_mappings: List[Dict[str, Any]] = field(default_factory=list)
    clinical_relevance_score: float = 0.0
    topic_classification: str = "general"
    risk_factors: List[Dict[str, Any]] = field(default_factory=list)
    related_medications: List[Dict[str, Any]] = field(default_factory=list)
    
    # Quality improvements
    enhanced_keywords: List[str] = field(default_factory=list)
    related_topics_suggestions: List[str] = field(default_factory=list)
    patient_summary: str = ""
    provider_summary: str = ""
    
    # Enhancement metadata
    enhancement_timestamp: str = ""
    ai_confidence: float = 0.0
    data_sources: List[str] = field(default_factory=list)


class HealthTopicsEnricher:
    """
    AI-driven enhancement engine for health topics data.
    
    Provides comprehensive medical enhancement including:
    - Medical entity extraction using SciSpacy
    - ICD-10 condition mapping with confidence scores
    - Clinical relevance scoring for healthcare providers
    - Topic classification for patient vs provider content
    - Risk factor and medication extraction
    - Quality improvements for patient education
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the health topics enricher.
        
        Args:
            config: Optional configuration override
        """
        # Load configuration
        self.config = get_config()
        self.user_config = config or {}
        
        # AI mode configuration
        self.ai_enabled = self.config.ai_enabled
        self.scispacy_config = self.config.get_scispacy_config()
        self.ollama_config = self.config.get_ollama_config()
        
        # Initialize AI clients
        if self.ai_enabled and AI_CLIENTS_AVAILABLE:
            try:
                self.scispacy_client = SciSpacyClientSync()
                self.ollama_client = OllamaClientSync()
            except Exception as e:
                logger.warning(f"Failed to initialize AI clients: {e}")
                self.scispacy_client = None
                self.ollama_client = None
                self.ai_enabled = False
        else:
            self.scispacy_client = None
            self.ollama_client = None
            if self.ai_enabled and not AI_CLIENTS_AVAILABLE:
                logger.info("AI clients not available, disabling AI enhancement")
                self.ai_enabled = False
            
        # Enhancement configuration
        self.batch_size = self.config.get_batch_size('health_topics')
        self.quality_thresholds = self.config.get_quality_thresholds()
        
        # Statistics tracking
        self.stats = {
            'processed': 0,
            'enhanced': 0,
            'medical_entities_extracted': 0,
            'icd10_mappings_found': 0,
            'risk_factors_identified': 0,
            'medications_extracted': 0,
            'keywords_enhanced': 0,
            'ai_calls': 0,
            'ai_failures': 0,
            'fallback_to_pattern': 0
        }
        
        # Pattern-based fallback data
        self._load_pattern_data()
        
        # Rate limiting
        self.last_ai_call = 0
        self.min_ai_interval = 0.2  # 200ms between AI calls
        
    def _load_pattern_data(self):
        """Load pattern-based enhancement data for fallback mode"""
        self.medical_abbreviations = self.config.get_medical_abbreviations()
        self.term_variations = self.config.get_term_variations()
        
        # Health topic specific patterns
        self.topic_classification_patterns = {
            'prevention': [
                'prevent', 'prevention', 'screening', 'vaccine', 'immunization',
                'healthy lifestyle', 'risk factors', 'early detection', 'wellness',
                'diet', 'exercise', 'nutrition', 'lifestyle'
            ],
            'treatment': [
                'treatment', 'therapy', 'medication', 'surgery', 'procedure',
                'medicine', 'cure', 'healing', 'intervention', 'drug',
                'rehabilitation', 'recovery'
            ],
            'diagnosis': [
                'diagnosis', 'symptoms', 'signs', 'test', 'exam', 'screening',
                'diagnostic', 'evaluation', 'assessment'
            ],
            'management': [
                'management', 'managing', 'control', 'monitoring', 'maintenance',
                'ongoing care', 'chronic care', 'follow-up'
            ]
        }
        
        self.risk_factor_patterns = [
            'risk factor', 'increases risk', 'higher risk', 'predisposes',
            'smoking', 'obesity', 'diabetes', 'hypertension', 'age',
            'family history', 'genetic', 'environmental', 'lifestyle'
        ]
        
        self.medication_patterns = [
            'medication', 'medicine', 'drug', 'treatment', 'therapy',
            'prescription', 'over-the-counter', 'supplement', 'vaccine'
        ]
        
    async def enhance_health_topics(self, health_topics: List[Dict[str, Any]], 
                                  max_concurrent: int = 5) -> List[HealthTopicEnhancement]:
        """
        Enhance a list of health topics with AI-driven medical information.
        
        Args:
            health_topics: List of health topic dictionaries
            max_concurrent: Maximum concurrent AI processing
            
        Returns:
            List of enhanced health topic objects
        """
        logger.info(f"Starting enhancement of {len(health_topics)} health topics")
        
        # Check AI services if enabled
        if self.ai_enabled and not self._check_ai_services():
            logger.warning("AI services unavailable, falling back to pattern-based enhancement")
            self.ai_enabled = False
            
        start_time = time.time()
        enhanced_topics = []
        
        # Process in batches for memory efficiency
        for i in range(0, len(health_topics), self.batch_size):
            batch = health_topics[i:i + self.batch_size]
            
            if self.ai_enabled:
                batch_results = await self._process_batch_ai(batch, max_concurrent)
            else:
                batch_results = await self._process_batch_patterns(batch)
                
            enhanced_topics.extend(batch_results)
            
            # Progress logging
            processed = min(i + self.batch_size, len(health_topics))
            logger.info(f"Health topics enhancement progress: {processed}/{len(health_topics)} "
                       f"({processed/len(health_topics)*100:.1f}%)")
                       
        duration = time.time() - start_time
        
        logger.info(f"Enhanced {len(enhanced_topics)} health topics in {duration:.2f}s")
        logger.info(f"Enhancement statistics: {self.stats}")
        
        return enhanced_topics
        
    async def _process_batch_ai(self, batch: List[Dict[str, Any]], 
                              max_concurrent: int) -> List[HealthTopicEnhancement]:
        """Process a batch of topics using AI enhancement"""
        semaphore = asyncio.Semaphore(max_concurrent)
        tasks = []
        
        for topic_data in batch:
            task = self._enhance_single_topic_ai(topic_data, semaphore)
            tasks.append(task)
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and log errors
        enhanced_topics = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error enhancing topic {batch[i].get('topic_id', 'unknown')}: {result}")
                self.stats['ai_failures'] += 1
                # Fallback to pattern-based enhancement
                fallback_result = await self._enhance_single_topic_patterns(batch[i])
                enhanced_topics.append(fallback_result)
                self.stats['fallback_to_pattern'] += 1
            else:
                enhanced_topics.append(result)
                
        return enhanced_topics
        
    async def _process_batch_patterns(self, batch: List[Dict[str, Any]]) -> List[HealthTopicEnhancement]:
        """Process a batch using pattern-based enhancement"""
        enhanced_topics = []
        
        for topic_data in batch:
            enhanced = await self._enhance_single_topic_patterns(topic_data)
            enhanced_topics.append(enhanced)
            
        return enhanced_topics
        
    async def _enhance_single_topic_ai(self, topic_data: Dict[str, Any], 
                                     semaphore: asyncio.Semaphore) -> HealthTopicEnhancement:
        """Enhance a single topic using AI services"""
        async with semaphore:
            self.stats['processed'] += 1
            
            topic_id = topic_data.get('topic_id', '')
            title = topic_data.get('title', '')
            
            # Create enhancement object
            enhancement = HealthTopicEnhancement(
                topic_id=topic_id,
                title=title,
                original_data=topic_data,
                enhancement_timestamp=datetime.now().isoformat(),
                data_sources=['ai_enhanced']
            )
            
            # Extract full text content
            content_text = self._extract_content_text(topic_data)
            
            if not content_text:
                logger.warning(f"No content found for topic {topic_id}")
                return enhancement
                
            # Apply rate limiting
            await self._rate_limit()
            
            try:
                # 1. Medical entity extraction using SciSpacy
                entities = await self._extract_medical_entities(content_text)
                enhancement.medical_entities = entities
                if entities:
                    self.stats['medical_entities_extracted'] += len(sum(entities.values(), []))
                    
                # 2. ICD-10 mapping
                icd10_mappings = await self._map_to_icd10(content_text, entities)
                enhancement.icd10_mappings = icd10_mappings
                if icd10_mappings:
                    self.stats['icd10_mappings_found'] += len(icd10_mappings)
                    
                # 3. Clinical relevance scoring
                relevance_score = await self._calculate_clinical_relevance(content_text, entities)
                enhancement.clinical_relevance_score = relevance_score
                
                # 4. Topic classification
                classification = await self._classify_topic(content_text, entities)
                enhancement.topic_classification = classification
                
                # 5. Risk factor identification
                risk_factors = await self._identify_risk_factors(content_text, entities)
                enhancement.risk_factors = risk_factors
                if risk_factors:
                    self.stats['risk_factors_identified'] += len(risk_factors)
                    
                # 6. Related medication extraction
                medications = await self._extract_medications(content_text, entities)
                enhancement.related_medications = medications
                if medications:
                    self.stats['medications_extracted'] += len(medications)
                    
                # 7. Quality improvements
                enhanced_keywords = await self._enhance_keywords(topic_data, entities)
                enhancement.enhanced_keywords = enhanced_keywords
                if enhanced_keywords:
                    self.stats['keywords_enhanced'] += len(enhanced_keywords)
                    
                related_suggestions = await self._suggest_related_topics(content_text, entities)
                enhancement.related_topics_suggestions = related_suggestions
                
                patient_summary = await self._generate_patient_summary(content_text, entities)
                enhancement.patient_summary = patient_summary
                
                provider_summary = await self._generate_provider_summary(content_text, entities)
                enhancement.provider_summary = provider_summary
                
                # Calculate overall AI confidence
                enhancement.ai_confidence = self._calculate_ai_confidence(enhancement)
                
                self.stats['enhanced'] += 1
                
            except Exception as e:
                logger.error(f"AI enhancement failed for topic {topic_id}: {e}")
                self.stats['ai_failures'] += 1
                # Apply pattern-based fallback
                pattern_enhancement = await self._enhance_single_topic_patterns(topic_data)
                return pattern_enhancement
                
            return enhancement
            
    async def _enhance_single_topic_patterns(self, topic_data: Dict[str, Any]) -> HealthTopicEnhancement:
        """Enhance a single topic using pattern-based methods"""
        self.stats['processed'] += 1
        
        topic_id = topic_data.get('topic_id', '')
        title = topic_data.get('title', '')
        
        # Create enhancement object
        enhancement = HealthTopicEnhancement(
            topic_id=topic_id,
            title=title,
            original_data=topic_data,
            enhancement_timestamp=datetime.now().isoformat(),
            data_sources=['pattern_based']
        )
        
        content_text = self._extract_content_text(topic_data)
        if not content_text:
            return enhancement
            
        # Pattern-based enhancements
        enhancement.medical_entities = self._extract_entities_patterns(content_text)
        enhancement.topic_classification = self._classify_topic_patterns(content_text)
        enhancement.risk_factors = self._identify_risk_factors_patterns(content_text)
        enhancement.related_medications = self._extract_medications_patterns(content_text)
        enhancement.enhanced_keywords = self._enhance_keywords_patterns(topic_data)
        enhancement.clinical_relevance_score = self._calculate_relevance_patterns(content_text)
        
        # Generate summaries using template approach
        enhancement.patient_summary = self._generate_patient_summary_patterns(topic_data)
        enhancement.provider_summary = self._generate_provider_summary_patterns(topic_data)
        
        enhancement.ai_confidence = 0.6  # Lower confidence for pattern-based
        
        self.stats['enhanced'] += 1
        self.stats['fallback_to_pattern'] += 1
        
        return enhancement
        
    def _extract_content_text(self, topic_data: Dict[str, Any]) -> str:
        """Extract all text content from a topic"""
        content_parts = []
        
        # Add title
        title = topic_data.get('title', '')
        if title:
            content_parts.append(title)
            
        # Add summary
        summary = topic_data.get('summary', '')
        if summary:
            content_parts.append(summary)
            
        # Add sections content
        sections = topic_data.get('sections', [])
        for section in sections:
            if isinstance(section, dict):
                section_content = section.get('content', '')
                if section_content:
                    content_parts.append(section_content)
                    
        return ' '.join(content_parts)
        
    async def _rate_limit(self):
        """Apply rate limiting for AI service calls"""
        elapsed = time.time() - self.last_ai_call
        if elapsed < self.min_ai_interval:
            await asyncio.sleep(self.min_ai_interval - elapsed)
        self.last_ai_call = time.time()
        
    def _check_ai_services(self) -> bool:
        """Check if AI services are available"""
        if not self.scispacy_client or not self.ollama_client:
            return False
            
        scispacy_ok = self.scispacy_client.check_health()
        ollama_ok = self.ollama_client.check_health()
        
        if not scispacy_ok:
            logger.warning("SciSpacy service not available")
        if not ollama_ok:
            logger.warning("Ollama service not available")
            
        return scispacy_ok and ollama_ok
        
    # AI-based enhancement methods
    async def _extract_medical_entities(self, content: str) -> Dict[str, List[str]]:
        """Extract medical entities using SciSpacy"""
        try:
            self.stats['ai_calls'] += 1
            entities = self.scispacy_client.extract_medical_concepts(content)
            
            # Organize entities by type
            organized_entities = {
                'diseases': entities.get('diseases', []),
                'chemicals': entities.get('chemicals', []),
                'genes': entities.get('genes', []),
                'organisms': entities.get('organisms', []),
                'anatomy': entities.get('anatomy', []),
                'medical_procedures': entities.get('procedures', []),
                'all_entities': entities.get('all_entities', [])
            }
            
            return organized_entities
            
        except Exception as e:
            logger.error(f"SciSpacy entity extraction failed: {e}")
            self.stats['ai_failures'] += 1
            return {}
            
    async def _map_to_icd10(self, content: str, entities: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """Map health topic content to ICD-10 codes"""
        try:
            self.stats['ai_calls'] += 1
            
            # Use Ollama to suggest ICD-10 mappings
            prompt = self._build_icd10_mapping_prompt(content, entities)
            response = self.ollama_client.generate_structured_response(
                prompt, 
                response_format="json",
                max_tokens=400
            )
            
            if response and 'icd10_mappings' in response:
                mappings = response['icd10_mappings']
                
                # Validate and enhance mappings
                validated_mappings = []
                for mapping in mappings:
                    if self._validate_icd10_mapping(mapping):
                        validated_mappings.append(mapping)
                        
                return validated_mappings
                
        except Exception as e:
            logger.error(f"ICD-10 mapping failed: {e}")
            self.stats['ai_failures'] += 1
            
        return []
        
    async def _calculate_clinical_relevance(self, content: str, entities: Dict[str, List[str]]) -> float:
        """Calculate clinical relevance score (0.0-1.0)"""
        try:
            self.stats['ai_calls'] += 1
            
            prompt = self._build_clinical_relevance_prompt(content, entities)
            response = self.ollama_client.generate_structured_response(
                prompt,
                response_format="json",
                max_tokens=200
            )
            
            if response and 'clinical_relevance_score' in response:
                score = float(response['clinical_relevance_score'])
                return max(0.0, min(1.0, score))  # Clamp to 0-1 range
                
        except Exception as e:
            logger.error(f"Clinical relevance scoring failed: {e}")
            self.stats['ai_failures'] += 1
            
        return 0.5  # Default neutral score
        
    async def _classify_topic(self, content: str, entities: Dict[str, List[str]]) -> str:
        """Classify topic type (prevention, treatment, diagnosis, etc.)"""
        try:
            self.stats['ai_calls'] += 1
            
            prompt = self._build_classification_prompt(content, entities)
            response = self.ollama_client.generate_structured_response(
                prompt,
                response_format="json",
                max_tokens=100
            )
            
            if response and 'classification' in response:
                classification = response['classification'].lower()
                valid_classifications = ['prevention', 'treatment', 'diagnosis', 'management', 'general']
                
                if classification in valid_classifications:
                    return classification
                    
        except Exception as e:
            logger.error(f"Topic classification failed: {e}")
            self.stats['ai_failures'] += 1
            
        return 'general'
        
    async def _identify_risk_factors(self, content: str, entities: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """Identify risk factors mentioned in content"""
        try:
            self.stats['ai_calls'] += 1
            
            prompt = self._build_risk_factors_prompt(content, entities)
            response = self.ollama_client.generate_structured_response(
                prompt,
                response_format="json",
                max_tokens=300
            )
            
            if response and 'risk_factors' in response:
                risk_factors = response['risk_factors']
                validated_factors = []
                
                for factor in risk_factors:
                    if self._validate_risk_factor(factor):
                        validated_factors.append(factor)
                        
                return validated_factors
                
        except Exception as e:
            logger.error(f"Risk factor identification failed: {e}")
            self.stats['ai_failures'] += 1
            
        return []
        
    async def _extract_medications(self, content: str, entities: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """Extract medication information from content"""
        try:
            self.stats['ai_calls'] += 1
            
            prompt = self._build_medications_prompt(content, entities)
            response = self.ollama_client.generate_structured_response(
                prompt,
                response_format="json",
                max_tokens=300
            )
            
            if response and 'medications' in response:
                medications = response['medications']
                validated_meds = []
                
                for med in medications:
                    if self._validate_medication(med):
                        validated_meds.append(med)
                        
                return validated_meds
                
        except Exception as e:
            logger.error(f"Medication extraction failed: {e}")
            self.stats['ai_failures'] += 1
            
        return []
        
    async def _enhance_keywords(self, topic_data: Dict[str, Any], 
                              entities: Dict[str, List[str]]) -> List[str]:
        """Enhance keywords with medical synonyms"""
        try:
            self.stats['ai_calls'] += 1
            
            original_keywords = topic_data.get('keywords', [])
            content = self._extract_content_text(topic_data)
            
            prompt = self._build_keywords_prompt(original_keywords, content, entities)
            response = self.ollama_client.generate_structured_response(
                prompt,
                response_format="json",
                max_tokens=200
            )
            
            if response and 'enhanced_keywords' in response:
                enhanced = response['enhanced_keywords']
                
                # Combine original and enhanced keywords, remove duplicates
                all_keywords = set(original_keywords + enhanced)
                return sorted(list(all_keywords))
                
        except Exception as e:
            logger.error(f"Keywords enhancement failed: {e}")
            self.stats['ai_failures'] += 1
            
        return topic_data.get('keywords', [])
        
    async def _suggest_related_topics(self, content: str, entities: Dict[str, List[str]]) -> List[str]:
        """Suggest related health topics"""
        try:
            self.stats['ai_calls'] += 1
            
            prompt = self._build_related_topics_prompt(content, entities)
            response = self.ollama_client.generate_structured_response(
                prompt,
                response_format="json",
                max_tokens=150
            )
            
            if response and 'related_topics' in response:
                return response['related_topics']
                
        except Exception as e:
            logger.error(f"Related topics suggestion failed: {e}")
            self.stats['ai_failures'] += 1
            
        return []
        
    async def _generate_patient_summary(self, content: str, entities: Dict[str, List[str]]) -> str:
        """Generate patient-friendly summary"""
        try:
            self.stats['ai_calls'] += 1
            
            prompt = self._build_patient_summary_prompt(content, entities)
            response = self.ollama_client.generate_text(
                prompt,
                max_tokens=200,
                temperature=0.3
            )
            
            if response:
                return response.strip()
                
        except Exception as e:
            logger.error(f"Patient summary generation failed: {e}")
            self.stats['ai_failures'] += 1
            
        return ""
        
    async def _generate_provider_summary(self, content: str, entities: Dict[str, List[str]]) -> str:
        """Generate healthcare provider summary"""
        try:
            self.stats['ai_calls'] += 1
            
            prompt = self._build_provider_summary_prompt(content, entities)
            response = self.ollama_client.generate_text(
                prompt,
                max_tokens=250,
                temperature=0.2
            )
            
            if response:
                return response.strip()
                
        except Exception as e:
            logger.error(f"Provider summary generation failed: {e}")
            self.stats['ai_failures'] += 1
            
        return ""
        
    # Pattern-based enhancement methods (fallback)
    def _extract_entities_patterns(self, content: str) -> Dict[str, List[str]]:
        """Extract entities using pattern matching"""
        entities = {
            'diseases': [],
            'chemicals': [],
            'anatomy': [],
            'medical_procedures': [],
            'all_entities': []
        }
        
        content_lower = content.lower()
        
        # Pattern-based entity extraction using medical abbreviations and variations
        for abbrev, full_form in self.medical_abbreviations.items():
            if abbrev.lower() in content_lower:
                entities['diseases'].append(full_form)
                entities['all_entities'].append(full_form)
                
        for term, variations in self.term_variations.items():
            for variation in variations:
                if variation.lower() in content_lower:
                    entities['diseases'].append(term)
                    entities['all_entities'].append(term)
                    
        # Remove duplicates
        for key in entities:
            entities[key] = list(set(entities[key]))
            
        return entities
        
    def _classify_topic_patterns(self, content: str) -> str:
        """Classify topic using pattern matching"""
        content_lower = content.lower()
        scores = {}
        
        for classification, patterns in self.topic_classification_patterns.items():
            score = 0
            for pattern in patterns:
                if pattern in content_lower:
                    score += 1
            scores[classification] = score
            
        if not scores or max(scores.values()) == 0:
            return 'general'
            
        return max(scores, key=scores.get)
        
    def _identify_risk_factors_patterns(self, content: str) -> List[Dict[str, Any]]:
        """Identify risk factors using patterns"""
        content_lower = content.lower()
        risk_factors = []
        
        for pattern in self.risk_factor_patterns:
            if pattern in content_lower:
                risk_factors.append({
                    'factor': pattern,
                    'type': 'lifestyle' if pattern in ['smoking', 'obesity', 'diet'] else 'medical',
                    'confidence': 0.7
                })
                
        return risk_factors
        
    def _extract_medications_patterns(self, content: str) -> List[Dict[str, Any]]:
        """Extract medications using patterns"""
        content_lower = content.lower()
        medications = []
        
        for pattern in self.medication_patterns:
            if pattern in content_lower:
                medications.append({
                    'name': pattern,
                    'type': 'general',
                    'confidence': 0.6
                })
                
        return medications
        
    def _enhance_keywords_patterns(self, topic_data: Dict[str, Any]) -> List[str]:
        """Enhance keywords using patterns"""
        original_keywords = topic_data.get('keywords', [])
        enhanced_keywords = set(original_keywords)
        
        content = self._extract_content_text(topic_data).lower()
        
        # Add medical abbreviations found in content
        for abbrev, full_form in self.medical_abbreviations.items():
            if abbrev.lower() in content or full_form.lower() in content:
                enhanced_keywords.add(abbrev)
                enhanced_keywords.add(full_form)
                
        return sorted(list(enhanced_keywords))
        
    def _calculate_relevance_patterns(self, content: str) -> float:
        """Calculate clinical relevance using patterns"""
        content_lower = content.lower()
        clinical_terms = 0
        total_words = len(content.split())
        
        # Count clinical terms
        for abbrev in self.medical_abbreviations:
            if abbrev.lower() in content_lower:
                clinical_terms += 1
                
        for variations in self.term_variations.values():
            for variation in variations:
                if variation.lower() in content_lower:
                    clinical_terms += 1
                    
        # Calculate relevance score
        if total_words == 0:
            return 0.0
            
        relevance_ratio = min(clinical_terms / total_words * 10, 1.0)  # Scale to 0-1
        return relevance_ratio
        
    def _generate_patient_summary_patterns(self, topic_data: Dict[str, Any]) -> str:
        """Generate patient summary using template approach"""
        title = topic_data.get('title', '')
        summary = topic_data.get('summary', '')
        
        if summary and len(summary) > 50:
            # Extract first sentence or first 150 characters
            sentences = summary.split('. ')
            if sentences:
                return sentences[0] + '.' if not sentences[0].endswith('.') else sentences[0]
            else:
                return summary[:150] + '...' if len(summary) > 150 else summary
        elif title:
            return f"Information about {title.lower()} including symptoms, causes, and treatment options."
            
        return ""
        
    def _generate_provider_summary_patterns(self, topic_data: Dict[str, Any]) -> str:
        """Generate provider summary using template approach"""
        title = topic_data.get('title', '')
        category = topic_data.get('category', '')
        
        if title and category:
            return f"Clinical information for {title} ({category}). Review for patient education and care planning."
        elif title:
            return f"Clinical overview of {title} for healthcare providers."
            
        return ""
        
    def _calculate_ai_confidence(self, enhancement: HealthTopicEnhancement) -> float:
        """Calculate overall AI confidence score"""
        confidence_factors = []
        
        # Factor in number of successful enhancements
        if enhancement.medical_entities:
            confidence_factors.append(0.9)
        if enhancement.icd10_mappings:
            confidence_factors.append(0.8)
        if enhancement.risk_factors:
            confidence_factors.append(0.7)
        if enhancement.related_medications:
            confidence_factors.append(0.7)
        if enhancement.enhanced_keywords:
            confidence_factors.append(0.6)
        if enhancement.patient_summary:
            confidence_factors.append(0.8)
        if enhancement.provider_summary:
            confidence_factors.append(0.8)
            
        if not confidence_factors:
            return 0.3
            
        return sum(confidence_factors) / len(confidence_factors)
        
    # Prompt building methods
    def _build_icd10_mapping_prompt(self, content: str, entities: Dict[str, List[str]]) -> str:
        """Build prompt for ICD-10 mapping"""
        return f"""
        Analyze this health topic content and identify relevant ICD-10 codes:
        
        Content: {content[:1000]}
        Medical entities found: {entities.get('diseases', [])}
        
        Provide JSON response with ICD-10 mappings:
        {{
            "icd10_mappings": [
                {{
                    "code": "E11.9",
                    "description": "Type 2 diabetes mellitus without complications",
                    "confidence": 0.85,
                    "reasoning": "Content discusses diabetes management"
                }}
            ]
        }}
        
        Focus on:
        1. Primary conditions mentioned
        2. Related conditions
        3. Confidence based on content relevance
        """
        
    def _build_clinical_relevance_prompt(self, content: str, entities: Dict[str, List[str]]) -> str:
        """Build prompt for clinical relevance scoring"""
        return f"""
        Rate the clinical relevance of this health topic for healthcare providers (0.0-1.0):
        
        Content: {content[:800]}
        Medical entities: {entities.get('all_entities', [])}
        
        Consider:
        - Clinical decision making value
        - Patient care impact
        - Medical accuracy and detail
        - Healthcare provider utility
        
        Provide JSON response:
        {{
            "clinical_relevance_score": 0.75,
            "reasoning": "High relevance for patient care decisions"
        }}
        """
        
    def _build_classification_prompt(self, content: str, entities: Dict[str, List[str]]) -> str:
        """Build prompt for topic classification"""
        return f"""
        Classify this health topic into one category:
        
        Content: {content[:600]}
        
        Categories:
        - prevention: Focuses on preventing disease/conditions
        - treatment: Focuses on treating existing conditions  
        - diagnosis: Focuses on diagnosing conditions
        - management: Focuses on ongoing care management
        - general: General health information
        
        Provide JSON response:
        {{
            "classification": "prevention",
            "confidence": 0.8
        }}
        """
        
    def _build_risk_factors_prompt(self, content: str, entities: Dict[str, List[str]]) -> str:
        """Build prompt for risk factor identification"""
        return f"""
        Identify risk factors mentioned in this health content:
        
        Content: {content[:800]}
        
        Provide JSON response:
        {{
            "risk_factors": [
                {{
                    "factor": "smoking",
                    "type": "lifestyle",
                    "severity": "high",
                    "description": "Increases risk significantly"
                }}
            ]
        }}
        
        Types: lifestyle, medical, genetic, environmental, age-related
        Severity: low, moderate, high
        """
        
    def _build_medications_prompt(self, content: str, entities: Dict[str, List[str]]) -> str:
        """Build prompt for medication extraction"""
        return f"""
        Extract medication information from this health content:
        
        Content: {content[:800]}
        Medical entities: {entities.get('chemicals', [])}
        
        Provide JSON response:
        {{
            "medications": [
                {{
                    "name": "metformin",
                    "type": "prescription",
                    "purpose": "diabetes management",
                    "class": "biguanide"
                }}
            ]
        }}
        
        Types: prescription, over-the-counter, supplement
        """
        
    def _build_keywords_prompt(self, original_keywords: List[str], content: str, 
                             entities: Dict[str, List[str]]) -> str:
        """Build prompt for keyword enhancement"""
        return f"""
        Enhance these keywords with medical synonyms and related terms:
        
        Original keywords: {original_keywords}
        Content context: {content[:400]}
        Medical entities: {entities.get('all_entities', [])}
        
        Provide JSON response:
        {{
            "enhanced_keywords": ["diabetes", "blood sugar", "glucose", "insulin resistance"]
        }}
        
        Add relevant medical terms, synonyms, and patient-friendly language.
        """
        
    def _build_related_topics_prompt(self, content: str, entities: Dict[str, List[str]]) -> str:
        """Build prompt for related topics suggestion"""
        return f"""
        Suggest related health topics based on this content:
        
        Content: {content[:600]}
        Medical entities: {entities.get('all_entities', [])}
        
        Provide JSON response:
        {{
            "related_topics": ["Blood Sugar Management", "Diabetes Prevention", "Insulin Therapy"]
        }}
        
        Suggest 3-5 related topics that patients or providers might find useful.
        """
        
    def _build_patient_summary_prompt(self, content: str, entities: Dict[str, List[str]]) -> str:
        """Build prompt for patient summary generation"""
        return f"""
        Create a patient-friendly summary (100-150 words) of this health information:
        
        Content: {content[:800]}
        
        Requirements:
        - Simple, clear language
        - Avoid medical jargon
        - Focus on key points patients need to know
        - Encouraging and informative tone
        
        Generate a summary paragraph only, no JSON format.
        """
        
    def _build_provider_summary_prompt(self, content: str, entities: Dict[str, List[str]]) -> str:
        """Build prompt for provider summary generation"""
        return f"""
        Create a clinical summary (100-200 words) for healthcare providers:
        
        Content: {content[:800]}
        Medical entities: {entities.get('all_entities', [])}
        
        Requirements:
        - Medical terminology appropriate
        - Focus on clinical relevance
        - Include key diagnostic/treatment considerations
        - Professional tone
        
        Generate a summary paragraph only, no JSON format.
        """
        
    # Validation methods
    def _validate_icd10_mapping(self, mapping: Dict[str, Any]) -> bool:
        """Validate ICD-10 mapping structure"""
        required_fields = ['code', 'description', 'confidence']
        return all(field in mapping for field in required_fields)
        
    def _validate_risk_factor(self, factor: Dict[str, Any]) -> bool:
        """Validate risk factor structure"""
        required_fields = ['factor', 'type']
        return all(field in factor for field in required_fields)
        
    def _validate_medication(self, medication: Dict[str, Any]) -> bool:
        """Validate medication structure"""
        required_fields = ['name', 'type']
        return all(field in medication for field in required_fields)
        
    def get_enhancement_stats(self) -> Dict[str, Any]:
        """Get comprehensive enhancement statistics"""
        return {
            **self.stats,
            'ai_enabled': self.ai_enabled,
            'success_rate': (
                (self.stats['enhanced'] / self.stats['processed'] * 100)
                if self.stats['processed'] > 0 else 0
            ),
            'fallback_rate': (
                (self.stats['fallback_to_pattern'] / self.stats['processed'] * 100)
                if self.stats['processed'] > 0 else 0
            )
        }


def convert_enhancement_to_dict(enhancement: HealthTopicEnhancement) -> Dict[str, Any]:
    """Convert HealthTopicEnhancement object to dictionary for JSON serialization"""
    return {
        'topic_id': enhancement.topic_id,
        'title': enhancement.title,
        'original_data': enhancement.original_data,
        'medical_entities': enhancement.medical_entities,
        'icd10_mappings': enhancement.icd10_mappings,
        'clinical_relevance_score': enhancement.clinical_relevance_score,
        'topic_classification': enhancement.topic_classification,
        'risk_factors': enhancement.risk_factors,
        'related_medications': enhancement.related_medications,
        'enhanced_keywords': enhancement.enhanced_keywords,
        'related_topics_suggestions': enhancement.related_topics_suggestions,
        'patient_summary': enhancement.patient_summary,
        'provider_summary': enhancement.provider_summary,
        'enhancement_timestamp': enhancement.enhancement_timestamp,
        'ai_confidence': enhancement.ai_confidence,
        'data_sources': enhancement.data_sources
    }


def convert_dict_to_enhancement(data: Dict[str, Any]) -> HealthTopicEnhancement:
    """Convert dictionary back to HealthTopicEnhancement object"""
    return HealthTopicEnhancement(
        topic_id=data.get('topic_id', ''),
        title=data.get('title', ''),
        original_data=data.get('original_data', {}),
        medical_entities=data.get('medical_entities', {}),
        icd10_mappings=data.get('icd10_mappings', []),
        clinical_relevance_score=data.get('clinical_relevance_score', 0.0),
        topic_classification=data.get('topic_classification', 'general'),
        risk_factors=data.get('risk_factors', []),
        related_medications=data.get('related_medications', []),
        enhanced_keywords=data.get('enhanced_keywords', []),
        related_topics_suggestions=data.get('related_topics_suggestions', []),
        patient_summary=data.get('patient_summary', ''),
        provider_summary=data.get('provider_summary', ''),
        enhancement_timestamp=data.get('enhancement_timestamp', ''),
        ai_confidence=data.get('ai_confidence', 0.0),
        data_sources=data.get('data_sources', [])
    )