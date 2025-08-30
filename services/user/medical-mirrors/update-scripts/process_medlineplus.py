#!/usr/bin/env python3
"""
Process downloaded MedlinePlus topics through medical-mirrors
Loads JSON file, inserts into database, and enhances with cross-references
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.append('/app/src')

from health_info.medlineplus_parser import MedlinePlusParser
from health_info.health_topics_cross_reference_enhancer import HealthTopicsCrossReferenceEnhancer
from database import get_db_session
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Process MedlinePlus topics"""
    
    # Path to downloaded MedlinePlus data
    medlineplus_file = Path('/app/data/medlineplus/medlineplus_topics.json')
    
    if not medlineplus_file.exists():
        logger.error(f"MedlinePlus topics file not found: {medlineplus_file}")
        logger.info("Run smart_medlineplus_download.py first to download topics")
        return 1
    
    # Parse MedlinePlus topics
    parser = MedlinePlusParser()
    parsed_topics = parser.parse_topics_file(medlineplus_file)
    
    if not parsed_topics:
        logger.error("No topics parsed from MedlinePlus file")
        return 1
    
    logger.info(f"Successfully parsed {len(parsed_topics)} MedlinePlus topics")
    
    # Get database session
    session = get_db_session()
    
    try:
        # Get existing topics for merging
        result = session.execute(text("""
            SELECT topic_id, title, content_length, source 
            FROM health_topics
        """))
        existing = [dict(row._mapping) for row in result]
        
        logger.info(f"Found {len(existing)} existing health topics")
        
        # Merge topics (MedlinePlus updates existing or adds new)
        merged = parser.merge_with_existing(parsed_topics, existing)
        
        # Upsert merged topics
        for topic in merged:
            # Ensure all required fields have values
            topic_data = {
                'topic_id': topic.get('topic_id'),
                'title': topic.get('title', ''),
                'category': topic.get('category', ''),
                'url': topic.get('url', ''),
                'last_reviewed': topic.get('last_reviewed'),  # Can be None
                'audience': topic.get('audience', '[]'),
                'sections': topic.get('sections', '[]'),
                'related_topics': topic.get('related_topics', '[]'),
                'summary': topic.get('summary', ''),
                'keywords': topic.get('keywords', '[]'),
                'content_length': topic.get('content_length', 0),
                'source': topic.get('source', 'medlineplus'),
                'last_updated': topic.get('last_updated'),
                'search_text': topic.get('search_text', ''),
                'item_type': topic.get('item_type', 'health_topic')
            }
            
            # Use ON CONFLICT to update existing or insert new
            session.execute(text("""
                INSERT INTO health_topics (
                    topic_id, title, category, url, last_reviewed,
                    audience, sections, related_topics, summary, keywords,
                    content_length, source, last_updated, search_text, item_type
                ) VALUES (
                    :topic_id, :title, :category, :url, :last_reviewed,
                    :audience, :sections, :related_topics, :summary, :keywords,
                    :content_length, :source, :last_updated, :search_text, :item_type
                )
                ON CONFLICT (topic_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    category = EXCLUDED.category,
                    url = EXCLUDED.url,
                    last_reviewed = EXCLUDED.last_reviewed,
                    audience = EXCLUDED.audience,
                    sections = EXCLUDED.sections,
                    related_topics = EXCLUDED.related_topics,
                    summary = EXCLUDED.summary,
                    keywords = EXCLUDED.keywords,
                    content_length = EXCLUDED.content_length,
                    source = EXCLUDED.source,
                    last_updated = EXCLUDED.last_updated,
                    search_text = EXCLUDED.search_text,
                    item_type = EXCLUDED.item_type
            """), topic_data)
        
        session.commit()
        logger.info(f"Successfully upserted {len(merged)} health topics")
        
        # Update search vectors
        session.execute(text("""
            UPDATE health_topics 
            SET search_vector = to_tsvector('english', COALESCE(search_text, ''))
            WHERE source = 'medlineplus' OR search_vector IS NULL
        """))
        session.commit()
        logger.info("Updated search vectors")
        
        # Get final counts
        result = session.execute(text("""
            SELECT source, COUNT(*) as count 
            FROM health_topics 
            GROUP BY source
        """))
        
        logger.info("Final health topics by source:")
        for row in result:
            row_dict = dict(row._mapping)
            logger.info(f"  {row_dict['source']}: {row_dict['count']}")
        
        # Total count
        result = session.execute(text("SELECT COUNT(*) FROM health_topics"))
        total = result.scalar()
        logger.info(f"Total health topics in database: {total}")
        
        # Now enhance topics with cross-references
        logger.info("Starting cross-reference enhancement...")
        enhancer = HealthTopicsCrossReferenceEnhancer(session)
        
        # Get all topics that need enhancement
        result = session.execute(text("""
            SELECT topic_id, title, category, summary, keywords, medical_entities
            FROM health_topics
            WHERE source = 'medlineplus'
               AND (drug_interactions = '[]'::jsonb 
                    OR clinical_trials = '[]'::jsonb
                    OR last_ai_review IS NULL)
        """))
        
        topics_to_enhance = [dict(row._mapping) for row in result]
        logger.info(f"Found {len(topics_to_enhance)} topics to enhance")
        
        enhanced_count = 0
        for topic in topics_to_enhance:
            try:
                # Prepare topic data for enhancement
                topic_dict = {
                    'topic_id': topic['topic_id'],
                    'title': topic['title'],
                    'category': topic['category'],
                    'summary': topic['summary'],
                    'keywords': json.loads(topic['keywords']) if isinstance(topic['keywords'], str) else topic['keywords'],
                    'medical_entities': json.loads(topic['medical_entities']) if isinstance(topic['medical_entities'], str) else topic['medical_entities'] or {}
                }
                
                # Run enhancement
                result = enhancer.enhance_topic(topic_dict)
                
                # Update database with enhanced data
                session.execute(text("""
                    UPDATE health_topics SET
                        drug_interactions = :drug_interactions,
                        clinical_trials = :clinical_trials,
                        research_papers = :research_papers,
                        dietary_considerations = :dietary_considerations,
                        exercise_recommendations = :exercise_recommendations,
                        monitoring_parameters = :monitoring_parameters,
                        patient_resources = :patient_resources,
                        provider_notes = :provider_notes,
                        quality_indicators = :quality_indicators,
                        evidence_level = :evidence_level,
                        last_ai_review = :last_ai_review
                    WHERE topic_id = :topic_id
                """), {
                    'topic_id': topic['topic_id'],
                    'drug_interactions': json.dumps(result.drug_interactions),
                    'clinical_trials': json.dumps(result.clinical_trials),
                    'research_papers': json.dumps(result.research_papers),
                    'dietary_considerations': json.dumps(result.dietary_considerations),
                    'exercise_recommendations': json.dumps(result.exercise_recommendations),
                    'monitoring_parameters': json.dumps(result.monitoring_parameters),
                    'patient_resources': json.dumps(result.patient_resources),
                    'provider_notes': json.dumps(result.provider_notes),
                    'quality_indicators': json.dumps(result.quality_indicators),
                    'evidence_level': result.evidence_level,
                    'last_ai_review': datetime.now()
                })
                
                enhanced_count += 1
                if enhanced_count % 10 == 0:
                    session.commit()
                    logger.info(f"Enhanced {enhanced_count}/{len(topics_to_enhance)} topics...")
                    
            except Exception as e:
                logger.error(f"Error enhancing topic {topic['topic_id']}: {e}")
                continue
        
        session.commit()
        logger.info(f"✅ Successfully enhanced {enhanced_count} health topics")
        
        # Show enhancement statistics
        logger.info(f"Enhancement Statistics:")
        logger.info(f"  Topics processed: {enhancer.stats['topics_processed']}")
        logger.info(f"  Cross-references found: {enhancer.stats['cross_references_found']}")
        logger.info(f"  Errors: {enhancer.stats['errors']}")
        
    except Exception as e:
        logger.error(f"Database error: {e}")
        session.rollback()
        return 1
    finally:
        session.close()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())