#!/usr/bin/env python3
"""
Force reload existing health topics into the database
"""

import sys
import json
import logging
from pathlib import Path

# Add medical-mirrors src to path
sys.path.append("/home/intelluxe/services/user/medical-mirrors/src")

from health_info.parser import HealthInfoParser
from database import get_db_session
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Reload existing health topics"""
    # Load existing health topics file
    topics_file = Path("/home/intelluxe/database/medical_complete/health_info/health_topics_complete.json")
    
    if not topics_file.exists():
        logger.error(f"Health topics file not found: {topics_file}")
        return 1
    
    with open(topics_file) as f:
        topics = json.load(f)
    
    logger.info(f"Loaded {len(topics)} health topics from file")
    
    # Parse them
    parser = HealthInfoParser()
    parsed_data = parser.parse_and_validate({
        'health_topics': topics,
        'exercises': [],
        'food_items': []
    })
    
    parsed_topics = parsed_data['health_topics']
    logger.info(f"Successfully parsed {len(parsed_topics)} health topics")
    
    if not parsed_topics:
        logger.error("No topics were parsed successfully")
        return 1
    
    # Insert into database
    session = get_db_session()
    
    try:
        # Clear existing health topics
        session.execute(text("DELETE FROM health_topics"))
        session.commit()
        logger.info("Cleared existing health topics from database")
        
        # Insert parsed topics
        for topic in parsed_topics:
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
            """), {
                'topic_id': topic['topic_id'],
                'title': topic['title'],
                'category': topic['category'],
                'url': topic.get('url', ''),
                'last_reviewed': topic.get('last_reviewed'),
                'audience': json.dumps(topic.get('audience', [])),
                'sections': json.dumps(topic.get('sections', [])),
                'related_topics': json.dumps(topic.get('related_topics', [])),
                'summary': topic.get('summary', ''),
                'keywords': json.dumps(topic.get('keywords', [])),
                'content_length': topic.get('content_length', 0),
                'source': topic.get('source', 'myhealthfinder'),
                'last_updated': topic.get('last_updated'),
                'search_text': topic.get('search_text', ''),
                'item_type': 'health_topic'
            })
        
        session.commit()
        logger.info(f"Successfully inserted {len(parsed_topics)} health topics into database")
        
        # Update search vectors
        session.execute(text("""
            UPDATE health_topics 
            SET search_vector = to_tsvector('english', COALESCE(search_text, ''))
        """))
        session.commit()
        logger.info("Updated search vectors for health topics")
        
        # Get final count
        result = session.execute(text("SELECT COUNT(*) FROM health_topics"))
        count = result.scalar()
        logger.info(f"Final database count: {count} health topics")
        
    except Exception as e:
        logger.error(f"Database error: {e}")
        session.rollback()
        return 1
    finally:
        session.close()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())