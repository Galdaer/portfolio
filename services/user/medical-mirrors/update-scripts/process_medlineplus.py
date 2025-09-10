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
from decimal import Decimal

# Add src to path
sys.path.append('/app/src')

# Custom JSON encoder for Decimal types
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        # Handle iterables that might contain Decimals
        if hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)):
            try:
                return [self.default(item) if isinstance(item, Decimal) else item for item in obj]
            except TypeError:
                pass
        return super(DecimalEncoder, self).default(obj)
    
    def encode(self, obj):
        # Pre-process the object to handle nested Decimals
        return super(DecimalEncoder, self).encode(convert_decimals(obj))

def convert_decimals(obj):
    """
    Recursively convert Decimal objects to float in any data structure.
    """
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_decimals(item) for item in obj)
    else:
        return obj

from health_info.medlineplus_parser import MedlinePlusParser
from health_info.health_topics_cross_reference_enhancer import HealthTopicsCrossReferenceEnhancer
from health_info.medical_entity_extractor import MedicalEntityExtractor
from health_info.icd10_mapper import ICD10Mapper
from health_info.topic_content_enricher import TopicContentEnricher
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
        
        # Now enhance topics with ALL enhancement components
        logger.info("Starting comprehensive topic enhancement...")
        
        # Initialize all enhancement components
        entity_extractor = MedicalEntityExtractor(session)
        icd10_mapper = ICD10Mapper(session)
        cross_referencer = HealthTopicsCrossReferenceEnhancer(session)
        content_enricher = TopicContentEnricher()
        
        # Get all topics that need enhancement - force reprocess ALL
        result = session.execute(text("""
            SELECT topic_id, title, category, summary, keywords, medical_entities
            FROM health_topics
            WHERE source = 'medlineplus'
        """))
        
        topics_to_enhance = [dict(row._mapping) for row in result]
        logger.info(f"Found {len(topics_to_enhance)} topics to enhance")
        
        enhanced_count = 0
        for topic in topics_to_enhance:
            try:
                # Prepare topic data
                topic_dict = {
                    'topic_id': topic['topic_id'],
                    'title': topic['title'],
                    'category': topic['category'],
                    'summary': topic['summary'],
                    'keywords': json.loads(topic['keywords']) if isinstance(topic['keywords'], str) else topic['keywords']
                }
                
                # Step 1: Extract medical entities
                medical_entities = convert_decimals(entity_extractor.extract_entities(topic_dict))
                
                # Step 2: Map to ICD-10 codes
                icd10_mapping = convert_decimals(icd10_mapper.map_topic_to_icd10(topic_dict, medical_entities))
                
                # Step 3: Cross-reference with other medical data
                topic_dict['medical_entities'] = medical_entities
                cross_ref_result_raw = cross_referencer.enhance_topic(topic_dict)
                cross_ref_result = convert_decimals({
                    'drug_interactions': cross_ref_result_raw.drug_interactions,
                    'clinical_trials': cross_ref_result_raw.clinical_trials,
                    'research_papers': cross_ref_result_raw.research_papers,
                    'dietary_considerations': cross_ref_result_raw.dietary_considerations,
                    'exercise_recommendations': cross_ref_result_raw.exercise_recommendations,
                    'monitoring_parameters': cross_ref_result_raw.monitoring_parameters,
                    'patient_resources': cross_ref_result_raw.patient_resources,
                    'provider_notes': cross_ref_result_raw.provider_notes,
                    'quality_indicators': cross_ref_result_raw.quality_indicators,
                    'evidence_level': cross_ref_result_raw.evidence_level
                })
                
                # Step 4: Enrich with generated content
                enrichment = convert_decimals(content_enricher.enrich_topic(topic_dict, medical_entities, icd10_mapping))
                
                # Combine all results and update database
                session.execute(text("""
                    UPDATE health_topics SET
                        medical_entities = :medical_entities,
                        icd10_conditions = :icd10_conditions,
                        clinical_relevance_score = :clinical_relevance_score,
                        topic_classifications = :topic_classifications,
                        risk_factors = :risk_factors,
                        related_medications = :related_medications,
                        quality_improvements = :quality_improvements,
                        enhancement_metadata = :enhancement_metadata,
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
                    # From entity extraction
                    'medical_entities': json.dumps(medical_entities, cls=DecimalEncoder),
                    # From ICD-10 mapping
                    'icd10_conditions': json.dumps(icd10_mapping['icd10_conditions'], cls=DecimalEncoder),
                    'clinical_relevance_score': icd10_mapping['clinical_relevance_score'],
                    'topic_classifications': json.dumps(icd10_mapping['topic_classifications'], cls=DecimalEncoder),
                    'risk_factors': json.dumps(icd10_mapping['risk_factors'], cls=DecimalEncoder),
                    # From content enricher
                    'related_medications': json.dumps(enrichment['related_medications'], cls=DecimalEncoder),
                    'quality_improvements': json.dumps(enrichment['quality_improvements'], cls=DecimalEncoder),
                    'enhancement_metadata': json.dumps(enrichment['enhancement_metadata'], cls=DecimalEncoder),
                    # From cross-referencer
                    'drug_interactions': json.dumps(cross_ref_result['drug_interactions'], cls=DecimalEncoder),
                    'clinical_trials': json.dumps(cross_ref_result['clinical_trials'], cls=DecimalEncoder),
                    'research_papers': json.dumps(cross_ref_result['research_papers'], cls=DecimalEncoder),
                    'dietary_considerations': json.dumps(cross_ref_result['dietary_considerations'], cls=DecimalEncoder),
                    'exercise_recommendations': json.dumps(cross_ref_result['exercise_recommendations'], cls=DecimalEncoder),
                    'monitoring_parameters': json.dumps(cross_ref_result['monitoring_parameters'], cls=DecimalEncoder),
                    'patient_resources': json.dumps(cross_ref_result['patient_resources'], cls=DecimalEncoder),
                    'provider_notes': json.dumps(cross_ref_result['provider_notes'], cls=DecimalEncoder),
                    'quality_indicators': json.dumps(cross_ref_result['quality_indicators'], cls=DecimalEncoder),
                    'evidence_level': cross_ref_result['evidence_level'],
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
        logger.info(f"  Entity Extraction: {entity_extractor.get_statistics()}")
        logger.info(f"  ICD-10 Mapping: {icd10_mapper.get_statistics()}")
        logger.info(f"  Cross-references: {cross_referencer.stats}")
        logger.info(f"  Content Enrichment: {content_enricher.get_statistics()}")
        
    except Exception as e:
        logger.error(f"Database error: {e}")
        session.rollback()
        return 1
    finally:
        session.close()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())