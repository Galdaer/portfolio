#!/bin/bash

# Update health information from MyHealthfinder, ExerciseDB, and USDA APIs
# This script downloads health info and updates the local mirror

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Configuration
LOG_FILE="/app/logs/health_info_update.log"
LOCK_FILE="/tmp/health_info_update.lock"
PYTHON_ENV="/usr/local/bin/python"

# Create logs directory if it doesn't exist
mkdir -p /app/logs

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Function to cleanup
cleanup() {
    rm -f "$LOCK_FILE"
    log_message "Health info update cleanup completed"
}

# Set up trap to cleanup on exit
trap cleanup EXIT

# Check if already running
if [ -f "$LOCK_FILE" ]; then
    log_message "Health info update already running (lock file exists)"
    exit 1
fi

# Create lock file
echo $$ > "$LOCK_FILE"

log_message "Starting health information update"

# Change to project directory
cd "$PROJECT_DIR"

# Handle quick test mode
if [ "$QUICK_TEST" = "true" ]; then
    log_message "Running health info update in QUICK TEST mode (limited to 10 topics)"
    LIMIT_TOPICS=10
else
    log_message "Running health info update in FULL mode"
    LIMIT_TOPICS=0
fi

# Update health information
log_message "Downloading health information from multiple APIs"

$PYTHON_ENV -c "
import asyncio
import sys
import logging
import os
import json
from src.health_info.downloader import HealthInfoDownloader
from src.health_info.parser import HealthInfoParser
from src.config import Config
from src.database import get_db_session
from sqlalchemy import text

# Get limit from environment variable
limit_topics = int(os.getenv('LIMIT_TOPICS', 0)) or $LIMIT_TOPICS

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('$LOG_FILE'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def update_health_information():
    config = Config()
    
    # Check if we should force fresh download
    force_fresh = os.getenv('FORCE_FRESH', 'false').lower() == 'true'
    
    try:
        # Download data from all sources
        async with HealthInfoDownloader(config, force_fresh=force_fresh) as downloader:
            logger.info('Starting health information download')
            raw_data = await downloader.download_all_health_data()
            download_stats = downloader.get_download_stats()
            
            logger.info(f'Download stats: {download_stats}')
        
        # Parse and validate with AI enhancement
        parser = HealthInfoParser(enable_ai_enhancement=True)
        validated_data = await parser.parse_and_validate_with_enhancement(raw_data)
        parsing_stats = parser.get_parsing_stats()
        
        logger.info(f'Parsing stats: {parsing_stats}')
        
        # Limit for quick test
        if limit_topics > 0:
            logger.info(f'Limiting to first {limit_topics} topics for quick test')
            if validated_data['health_topics']:
                validated_data['health_topics'] = validated_data['health_topics'][:limit_topics]
        
        # Insert into database
        with get_db_session() as db:
            # Upsert health topics
            if validated_data['health_topics']:
                logger.info('Upserting health topics (preserving existing data)')
                
                for topic in validated_data['health_topics']:
                    db.execute(text('''
                        INSERT INTO health_topics (
                            topic_id, title, category, url, last_reviewed,
                            audience, sections, related_topics, summary,
                            keywords, content_length, source, search_text,
                            medical_entities, icd10_conditions, clinical_relevance_score,
                            topic_classifications, risk_factors, related_medications,
                            quality_improvements, enhancement_metadata,
                            last_updated
                        ) VALUES (
                            :topic_id, :title, :category, :url, :last_reviewed,
                            :audience, :sections, :related_topics, :summary,
                            :keywords, :content_length, :source, :search_text,
                            :medical_entities, :icd10_conditions, :clinical_relevance_score,
                            :topic_classifications, :risk_factors, :related_medications,
                            :quality_improvements, :enhancement_metadata,
                            NOW()
                        )
                        ON CONFLICT (topic_id) DO UPDATE SET
                            -- Only update if we have better/more complete information
                            title = COALESCE(NULLIF(EXCLUDED.title, ''), health_topics.title),
                            category = COALESCE(NULLIF(EXCLUDED.category, ''), health_topics.category),
                            url = COALESCE(NULLIF(EXCLUDED.url, ''), health_topics.url),
                            last_reviewed = COALESCE(NULLIF(EXCLUDED.last_reviewed, ''), health_topics.last_reviewed),
                            audience = COALESCE(EXCLUDED.audience, health_topics.audience),
                            sections = COALESCE(EXCLUDED.sections, health_topics.sections),
                            related_topics = COALESCE(EXCLUDED.related_topics, health_topics.related_topics),
                            summary = COALESCE(NULLIF(EXCLUDED.summary, ''), health_topics.summary),
                            keywords = COALESCE(EXCLUDED.keywords, health_topics.keywords),
                            content_length = COALESCE(EXCLUDED.content_length, health_topics.content_length),
                            source = COALESCE(NULLIF(EXCLUDED.source, ''), health_topics.source),
                            search_text = COALESCE(NULLIF(EXCLUDED.search_text, ''), health_topics.search_text),
                            -- Update AI enhancement fields
                            medical_entities = COALESCE(EXCLUDED.medical_entities, health_topics.medical_entities),
                            icd10_conditions = COALESCE(EXCLUDED.icd10_conditions, health_topics.icd10_conditions),
                            clinical_relevance_score = COALESCE(EXCLUDED.clinical_relevance_score, health_topics.clinical_relevance_score),
                            topic_classifications = COALESCE(EXCLUDED.topic_classifications, health_topics.topic_classifications),
                            risk_factors = COALESCE(EXCLUDED.risk_factors, health_topics.risk_factors),
                            related_medications = COALESCE(EXCLUDED.related_medications, health_topics.related_medications),
                            quality_improvements = COALESCE(EXCLUDED.quality_improvements, health_topics.quality_improvements),
                            enhancement_metadata = COALESCE(EXCLUDED.enhancement_metadata, health_topics.enhancement_metadata),
                            last_updated = NOW()
                    '''), {
                        'topic_id': topic['topic_id'],
                        'title': topic['title'],
                        'category': topic['category'],
                        'url': topic['url'],
                        'last_reviewed': topic['last_reviewed'],
                        'audience': json.dumps(topic['audience']) if topic.get('audience') else '[]',
                        'sections': json.dumps(topic['sections']) if topic.get('sections') else '[]',
                        'related_topics': json.dumps(topic['related_topics']) if topic.get('related_topics') else '[]',
                        'summary': topic['summary'],
                        'keywords': json.dumps(topic['keywords']) if topic.get('keywords') else '[]',
                        'content_length': topic['content_length'],
                        'source': topic['source'],
                        'search_text': topic['search_text'],
                        # AI enhancement fields
                        'medical_entities': json.dumps(topic.get('medical_entities', [])),
                        'icd10_conditions': json.dumps(topic.get('icd10_conditions', [])),
                        'clinical_relevance_score': topic.get('clinical_relevance_score'),
                        'topic_classifications': json.dumps(topic.get('topic_classifications', [])),
                        'risk_factors': json.dumps(topic.get('risk_factors', [])),
                        'related_medications': json.dumps(topic.get('related_medications', [])),
                        'quality_improvements': json.dumps(topic.get('quality_improvements', {})),
                        'enhancement_metadata': json.dumps(topic.get('enhancement_metadata', {}))
                    })
                
                logger.info(f'Inserted {len(validated_data[\"health_topics\"])} health topics')
                
                # Update search vectors for health topics
                logger.info('Updating search vectors for health topics')
                db.execute(text('''
                    UPDATE health_topics 
                    SET search_vector = to_tsvector('english', 
                        COALESCE(title, '') || ' ' ||
                        COALESCE(category, '') || ' ' ||
                        COALESCE(summary, '') || ' ' ||
                        COALESCE(search_text, '')
                    )
                    WHERE search_vector IS NULL
                '''))
                logger.info('Search vectors updated for health topics')
            
            # Upsert exercises
            if validated_data['exercises']:
                logger.info('Upserting exercises (preserving existing data)')
                
                for exercise in validated_data['exercises']:
                    db.execute(text('''
                        INSERT INTO exercises (
                            exercise_id, name, body_part, equipment, target,
                            secondary_muscles, instructions, gif_url,
                            difficulty_level, exercise_type, duration_estimate,
                            calories_estimate, source, search_text, last_updated
                        ) VALUES (
                            :exercise_id, :name, :body_part, :equipment, :target,
                            :secondary_muscles, :instructions, :gif_url,
                            :difficulty_level, :exercise_type, :duration_estimate,
                            :calories_estimate, :source, :search_text, NOW()
                        )
                        ON CONFLICT (exercise_id) DO UPDATE SET
                            -- Only update if we have better/more complete information
                            name = COALESCE(NULLIF(EXCLUDED.name, ''), exercises.name),
                            body_part = COALESCE(NULLIF(EXCLUDED.body_part, ''), exercises.body_part),
                            equipment = COALESCE(NULLIF(EXCLUDED.equipment, ''), exercises.equipment),
                            target = COALESCE(NULLIF(EXCLUDED.target, ''), exercises.target),
                            secondary_muscles = COALESCE(EXCLUDED.secondary_muscles, exercises.secondary_muscles),
                            instructions = COALESCE(EXCLUDED.instructions, exercises.instructions),
                            gif_url = COALESCE(NULLIF(EXCLUDED.gif_url, ''), exercises.gif_url),
                            difficulty_level = COALESCE(NULLIF(EXCLUDED.difficulty_level, ''), exercises.difficulty_level),
                            exercise_type = COALESCE(NULLIF(EXCLUDED.exercise_type, ''), exercises.exercise_type),
                            duration_estimate = COALESCE(EXCLUDED.duration_estimate, exercises.duration_estimate),
                            calories_estimate = COALESCE(EXCLUDED.calories_estimate, exercises.calories_estimate),
                            source = COALESCE(NULLIF(EXCLUDED.source, ''), exercises.source),
                            search_text = COALESCE(NULLIF(EXCLUDED.search_text, ''), exercises.search_text),
                            last_updated = NOW()
                    '''), {
                        'exercise_id': exercise['exercise_id'],
                        'name': exercise['name'],
                        'body_part': exercise['body_part'],
                        'equipment': exercise['equipment'],
                        'target': exercise['target'],
                        'secondary_muscles': json.dumps(exercise['secondary_muscles']) if exercise.get('secondary_muscles') else '[]',
                        'instructions': json.dumps(exercise['instructions']) if exercise.get('instructions') else '[]',
                        'gif_url': exercise['gif_url'],
                        'difficulty_level': exercise.get('difficulty_level'),
                        'exercise_type': exercise.get('exercise_type'),
                        'duration_estimate': exercise.get('duration_estimate'),
                        'calories_estimate': exercise.get('calories_estimate'),
                        'source': exercise['source'],
                        'search_text': exercise['search_text']
                    })
                
                logger.info(f'Inserted {len(validated_data[\"exercises\"])} exercises')
                
                # Update search vectors for exercises  
                logger.info('Updating search vectors for exercises')
                db.execute(text('''
                    UPDATE exercises 
                    SET search_vector = to_tsvector('english', 
                        COALESCE(name, '') || ' ' ||
                        COALESCE(body_part, '') || ' ' ||
                        COALESCE(equipment, '') || ' ' ||
                        COALESCE(target, '') || ' ' ||
                        COALESCE(search_text, '')
                    )
                    WHERE search_vector IS NULL
                '''))
                logger.info('Search vectors updated for exercises')
            
            # Upsert food items
            if validated_data['food_items']:
                logger.info('Upserting food items (preserving existing data)')
                
                for food in validated_data['food_items']:
                    db.execute(text('''
                        INSERT INTO food_items (
                            fdc_id, description, scientific_name, common_names,
                            food_category, nutrients, nutrition_summary,
                            brand_owner, ingredients, serving_size, serving_size_unit,
                            allergens, dietary_flags, nutritional_density,
                            source, search_text, last_updated
                        ) VALUES (
                            :fdc_id, :description, :scientific_name, :common_names,
                            :food_category, :nutrients, :nutrition_summary,
                            :brand_owner, :ingredients, :serving_size, :serving_size_unit,
                            :allergens, :dietary_flags, :nutritional_density,
                            :source, :search_text, NOW()
                        )
                        ON CONFLICT (fdc_id) DO UPDATE SET
                            -- Only update if we have better/more complete information
                            description = COALESCE(NULLIF(EXCLUDED.description, ''), food_items.description),
                            scientific_name = COALESCE(NULLIF(EXCLUDED.scientific_name, ''), food_items.scientific_name),
                            common_names = COALESCE(NULLIF(EXCLUDED.common_names, ''), food_items.common_names),
                            food_category = COALESCE(NULLIF(EXCLUDED.food_category, ''), food_items.food_category),
                            nutrients = COALESCE(EXCLUDED.nutrients, food_items.nutrients),
                            nutrition_summary = COALESCE(EXCLUDED.nutrition_summary, food_items.nutrition_summary),
                            brand_owner = COALESCE(NULLIF(EXCLUDED.brand_owner, ''), food_items.brand_owner),
                            ingredients = COALESCE(NULLIF(EXCLUDED.ingredients, ''), food_items.ingredients),
                            serving_size = COALESCE(EXCLUDED.serving_size, food_items.serving_size),
                            serving_size_unit = COALESCE(NULLIF(EXCLUDED.serving_size_unit, ''), food_items.serving_size_unit),
                            allergens = COALESCE(EXCLUDED.allergens, food_items.allergens),
                            dietary_flags = COALESCE(EXCLUDED.dietary_flags, food_items.dietary_flags),
                            nutritional_density = COALESCE(EXCLUDED.nutritional_density, food_items.nutritional_density),
                            source = COALESCE(NULLIF(EXCLUDED.source, ''), food_items.source),
                            search_text = COALESCE(NULLIF(EXCLUDED.search_text, ''), food_items.search_text),
                            last_updated = NOW()
                    '''), {
                        'fdc_id': food['fdc_id'],
                        'description': food['description'],
                        'scientific_name': food.get('scientific_name'),
                        'common_names': food.get('common_names'),
                        'food_category': food.get('food_category'),
                        'nutrients': json.dumps(food['nutrients']) if food.get('nutrients') else '[]',
                        'nutrition_summary': json.dumps(food.get('nutrition_summary', {})),
                        'brand_owner': food.get('brand_owner'),
                        'ingredients': food.get('ingredients'),
                        'serving_size': food.get('serving_size'),
                        'serving_size_unit': food.get('serving_size_unit'),
                        'allergens': json.dumps(food.get('allergens', {})) if isinstance(food.get('allergens'), dict) else json.dumps({'allergens': food.get('allergens', [])}),
                        'dietary_flags': json.dumps(food.get('dietary_flags', {})) if isinstance(food.get('dietary_flags'), dict) else json.dumps(food.get('dietary_flags', [])),
                        'nutritional_density': food.get('nutritional_density'),
                        'source': food['source'],
                        'search_text': food['search_text']
                    })
                
                logger.info(f'Inserted {len(validated_data[\"food_items\"])} food items')
                
                # Update search vectors for food items
                logger.info('Updating search vectors for food items')
                db.execute(text('''
                    UPDATE food_items 
                    SET search_vector = to_tsvector('english', 
                        COALESCE(description, '') || ' ' ||
                        COALESCE(food_category, '') || ' ' ||
                        COALESCE(brand_owner, '') || ' ' ||
                        COALESCE(ingredients, '') || ' ' ||
                        COALESCE(search_text, '')
                    )
                    WHERE search_vector IS NULL
                '''))
                logger.info('Search vectors updated for food items')
            
            db.commit()
            
            # Get final statistics
            topics_result = db.execute(text('SELECT COUNT(*) as total FROM health_topics'))
            exercises_result = db.execute(text('SELECT COUNT(*) as total FROM exercises'))
            foods_result = db.execute(text('SELECT COUNT(*) as total FROM food_items'))
            
            topics_count = topics_result.fetchone().total
            exercises_count = exercises_result.fetchone().total
            foods_count = foods_result.fetchone().total
            
            logger.info(f'Final database counts:')
            logger.info(f'  Health topics: {topics_count}')
            logger.info(f'  Exercises: {exercises_count}') 
            logger.info(f'  Food items: {foods_count}')
        
        # Run AI enhancement for food items
        logger.info('Starting AI enhancement for food items')
        try:
            # Import food AI enhancement
            import sys
            sys.path.append('/app/src')  # Ensure imports work
            from health_info.food_ai_enrichment import FoodAIEnhancer
            
            # Run food enhancement with limit for quick test
            food_enhancer = FoodAIEnhancer()
            enhancement_limit = limit_topics if limit_topics > 0 else None
            enhancement_stats = food_enhancer.enhance_food_database(limit=enhancement_limit)
            
            logger.info(f'Food AI Enhancement completed: {enhancement_stats}')
            
        except Exception as e:
            logger.warning(f'Food AI enhancement failed: {e}')
            # Continue without enhancement - don't fail the entire update
            import traceback
            logger.debug(traceback.format_exc())
            
        logger.info('Health information update completed successfully')
        return True
        
    except Exception as e:
        logger.error(f'Error updating health information: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return False

# Run the update
if __name__ == '__main__':
    success = asyncio.run(update_health_information())
    sys.exit(0 if success else 1)
"

UPDATE_EXIT_CODE=$?

if [ $UPDATE_EXIT_CODE -eq 0 ]; then
    log_message "Health information update completed successfully"
else
    log_message "Health information update failed with exit code $UPDATE_EXIT_CODE"
fi

# Update last run timestamp
echo "$(date '+%Y-%m-%d %H:%M:%S')" > /app/data/.health_info_last_update

log_message "Health information update script finished"

exit $UPDATE_EXIT_CODE