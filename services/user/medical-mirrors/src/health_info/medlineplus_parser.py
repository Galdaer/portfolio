"""
MedlinePlus health topics parser for medical-mirrors
Processes MedlinePlus topics downloaded by smart_medlineplus_download.py
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class MedlinePlusParser:
    """Parser for MedlinePlus health topics"""
    
    def __init__(self):
        self.processed_count = 0
        self.error_count = 0
        
    def parse_topics_file(self, file_path: Path) -> List[Dict]:
        """Parse MedlinePlus topics from JSON file"""
        if not file_path.exists():
            logger.error(f"MedlinePlus topics file not found: {file_path}")
            return []
        
        try:
            with open(file_path) as f:
                topics = json.load(f)
            
            logger.info(f"Loaded {len(topics)} MedlinePlus topics from {file_path}")
            return self.parse_topics(topics)
            
        except Exception as e:
            logger.error(f"Error loading MedlinePlus topics: {e}")
            return []
    
    def parse_topics(self, raw_topics: List[Dict]) -> List[Dict]:
        """Parse and normalize MedlinePlus topics"""
        parsed_topics = []
        
        for raw_topic in raw_topics:
            try:
                parsed = self.parse_single_topic(raw_topic)
                if parsed:
                    parsed_topics.append(parsed)
                    self.processed_count += 1
            except Exception as e:
                logger.error(f"Error parsing MedlinePlus topic: {e}")
                self.error_count += 1
        
        logger.info(f"Parsed {len(parsed_topics)} MedlinePlus topics successfully")
        if self.error_count > 0:
            logger.warning(f"Failed to parse {self.error_count} topics")
        
        return parsed_topics
    
    def parse_single_topic(self, raw_topic: Dict) -> Optional[Dict]:
        """Parse a single MedlinePlus topic"""
        # Required fields
        topic_id = raw_topic.get('topic_id', '')
        title = raw_topic.get('title', '')
        
        if not topic_id or not title:
            return None
        
        # Parse the topic into our standard format
        parsed = {
            'topic_id': topic_id,
            'title': title.strip(),
            'category': raw_topic.get('category', raw_topic.get('groupName', 'General Health')),
            'url': raw_topic.get('url', ''),
            'source': 'medlineplus',
            'item_type': 'health_topic',
            'last_updated': raw_topic.get('last_updated', datetime.now().isoformat())
        }
        
        # Parse optional fields
        if raw_topic.get('summary'):
            parsed['summary'] = raw_topic['summary'][:5000]  # Limit summary length
        else:
            parsed['summary'] = ''
        
        # Parse dates
        if raw_topic.get('last_reviewed'):
            parsed['last_reviewed'] = raw_topic['last_reviewed']
        elif raw_topic.get('dateRevised'):
            parsed['last_reviewed'] = raw_topic['dateRevised']
        
        # Parse sections
        sections = raw_topic.get('sections', [])
        if not sections and parsed.get('summary'):
            # Create sections from summary if not provided
            sections = self.create_sections_from_summary(parsed['summary'])
        parsed['sections'] = json.dumps(sections)
        
        # Parse related topics
        related = raw_topic.get('related_topics', [])
        if isinstance(related, list):
            parsed['related_topics'] = json.dumps(related)
        else:
            parsed['related_topics'] = '[]'
        
        # Parse audience
        audience = raw_topic.get('audience', [])
        if not audience:
            # Default audience based on language
            if raw_topic.get('language', '').lower() == 'spanish':
                audience = ['Spanish Speakers']
            else:
                audience = ['General Public']
        parsed['audience'] = json.dumps(audience)
        
        # Parse keywords
        keywords = self.extract_keywords(raw_topic)
        parsed['keywords'] = json.dumps(keywords)
        
        # Calculate content length
        content_length = len(parsed.get('summary', ''))
        for section in sections:
            if isinstance(section, dict):
                content_length += len(section.get('content', ''))
        parsed['content_length'] = content_length
        
        # Generate search text
        search_parts = [
            parsed['title'],
            parsed['category'],
            parsed.get('summary', '')[:500],
            ' '.join(keywords),
            raw_topic.get('also_called', ''),
            raw_topic.get('mesh_terms', '')
        ]
        parsed['search_text'] = ' '.join(filter(None, search_parts)).lower()
        
        return parsed
    
    def create_sections_from_summary(self, summary: str) -> List[Dict]:
        """Create sections from summary text"""
        sections = []
        
        # Split summary into paragraphs
        paragraphs = [p.strip() for p in summary.split('\n\n') if p.strip()]
        
        if paragraphs:
            # First paragraph as overview
            sections.append({
                'title': 'Overview',
                'content': paragraphs[0],
                'type': 'content'
            })
            
            # Remaining paragraphs as details
            if len(paragraphs) > 1:
                sections.append({
                    'title': 'Details',
                    'content': '\n\n'.join(paragraphs[1:]),
                    'type': 'content'
                })
        
        return sections
    
    def extract_keywords(self, topic: Dict) -> List[str]:
        """Extract keywords from topic"""
        keywords = []
        
        # Extract from MeSH terms
        if topic.get('mesh_terms'):
            mesh_terms = topic['mesh_terms']
            if isinstance(mesh_terms, str):
                keywords.extend([t.strip() for t in mesh_terms.split(',')])
        
        # Extract from also_called
        if topic.get('also_called'):
            also_called = topic['also_called']
            if isinstance(also_called, str):
                keywords.extend([t.strip() for t in also_called.split(',')])
        
        # Extract from title (important words)
        title = topic.get('title', '')
        title_words = title.split()
        for word in title_words:
            word = word.strip().lower()
            if len(word) > 4 and word not in ['about', 'health', 'medical', 'disease']:
                keywords.append(word)
        
        # Remove duplicates and limit to 20 keywords
        keywords = list(dict.fromkeys(keywords))[:20]
        
        return keywords
    
    def merge_with_existing(self, new_topics: List[Dict], existing_topics: List[Dict]) -> List[Dict]:
        """Merge new MedlinePlus topics with existing health topics"""
        # Create a map of existing topics by ID
        existing_map = {t['topic_id']: t for t in existing_topics}
        
        merged = []
        updated_count = 0
        new_count = 0
        
        for topic in new_topics:
            topic_id = topic['topic_id']
            
            if topic_id in existing_map:
                # Update existing topic if MedlinePlus has more content
                existing = existing_map[topic_id]
                if topic.get('content_length', 0) > existing.get('content_length', 0):
                    # MedlinePlus has more comprehensive content
                    existing.update(topic)
                    updated_count += 1
                merged.append(existing)
            else:
                # New topic from MedlinePlus
                merged.append(topic)
                new_count += 1
        
        # Add remaining existing topics not in MedlinePlus
        medlineplus_ids = {t['topic_id'] for t in new_topics}
        for topic_id, topic in existing_map.items():
            if topic_id not in medlineplus_ids:
                merged.append(topic)
        
        logger.info(f"Merge complete: {new_count} new, {updated_count} updated, {len(merged)} total topics")
        
        return merged