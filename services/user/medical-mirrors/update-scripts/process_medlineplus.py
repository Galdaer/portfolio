#!/usr/bin/env python3
"""
Process downloaded MedlinePlus topics through medical-mirrors
Loads JSON file and inserts into database
"""

import sys
import json
import logging
from pathlib import Path

# Add src to path
sys.path.append('/app/src')

from health_info.medlineplus_parser import MedlinePlusParser
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
        existing = [dict(row) for row in result]
        
        logger.info(f"Found {len(existing)} existing health topics")
        
        # Merge topics (MedlinePlus updates existing or adds new)
        merged = parser.merge_with_existing(parsed_topics, existing)
        
        # Upsert merged topics
        for topic in merged:
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
            """), topic)
        
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
            logger.info(f"  {row['source']}: {row['count']}")
        
        # Total count
        result = session.execute(text("SELECT COUNT(*) FROM health_topics"))
        total = result.scalar()
        logger.info(f"Total health topics in database: {total}")
        
    except Exception as e:
        logger.error(f"Database error: {e}")
        session.rollback()
        return 1
    finally:
        session.close()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())