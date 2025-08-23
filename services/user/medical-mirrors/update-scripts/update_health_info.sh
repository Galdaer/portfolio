#!/bin/bash

# Update health information from MyHealthfinder, ExerciseDB, and USDA APIs
# This script downloads health info and updates the local mirror

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Configuration
LOG_FILE="/app/logs/health_info_update.log"
LOCK_FILE="/tmp/health_info_update.lock"
PYTHON_ENV="/app/venv/bin/python"

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

# Update health information
log_message "Downloading health information from multiple APIs"

$PYTHON_ENV -c "
import asyncio
import sys
import logging
import os
from src.health_info.downloader import HealthInfoDownloader
from src.health_info.parser import HealthInfoParser
from src.config import Config
from src.database import get_db_session
from sqlalchemy import text

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
    
    try:
        # Download data from all sources
        async with HealthInfoDownloader(config) as downloader:
            logger.info('Starting health information download')
            raw_data = await downloader.download_all_health_data()
            download_stats = downloader.get_download_stats()
            
            logger.info(f'Download stats: {download_stats}')
        
        # Parse and validate
        parser = HealthInfoParser()
        validated_data = parser.parse_and_validate(raw_data)
        parsing_stats = parser.get_parsing_stats()
        
        logger.info(f'Parsing stats: {parsing_stats}')
        
        # Insert into database
        with get_db_session() as db:
            # Update health topics
            if validated_data['health_topics']:
                logger.info('Updating health topics')
                db.execute(text('DELETE FROM health_topics'))
                
                for topic in validated_data['health_topics']:
                    db.execute(text('''
                        INSERT INTO health_topics (
                            topic_id, title, category, url, last_reviewed,
                            audience, sections, related_topics, summary,
                            keywords, content_length, source, search_text,
                            last_updated
                        ) VALUES (
                            :topic_id, :title, :category, :url, :last_reviewed,
                            :audience, :sections, :related_topics, :summary,
                            :keywords, :content_length, :source, :search_text,
                            NOW()
                        )
                    '''), {
                        'topic_id': topic['topic_id'],
                        'title': topic['title'],
                        'category': topic['category'],
                        'url': topic['url'],
                        'last_reviewed': topic['last_reviewed'],
                        'audience': topic['audience'],
                        'sections': topic['sections'],
                        'related_topics': topic['related_topics'],
                        'summary': topic['summary'],
                        'keywords': topic['keywords'],
                        'content_length': topic['content_length'],
                        'source': topic['source'],
                        'search_text': topic['search_text']
                    })
                
                logger.info(f'Inserted {len(validated_data[\"health_topics\"])} health topics')
            
            # Update exercises
            if validated_data['exercises']:
                logger.info('Updating exercises')
                db.execute(text('DELETE FROM exercises'))
                
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
                    '''), {
                        'exercise_id': exercise['exercise_id'],
                        'name': exercise['name'],
                        'body_part': exercise['body_part'],
                        'equipment': exercise['equipment'],
                        'target': exercise['target'],
                        'secondary_muscles': exercise['secondary_muscles'],
                        'instructions': exercise['instructions'],
                        'gif_url': exercise['gif_url'],
                        'difficulty_level': exercise['difficulty_level'],
                        'exercise_type': exercise['exercise_type'],
                        'duration_estimate': exercise['duration_estimate'],
                        'calories_estimate': exercise['calories_estimate'],
                        'source': exercise['source'],
                        'search_text': exercise['search_text']
                    })
                
                logger.info(f'Inserted {len(validated_data[\"exercises\"])} exercises')
            
            # Update food items
            if validated_data['food_items']:
                logger.info('Updating food items')
                db.execute(text('DELETE FROM food_items'))
                
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
                    '''), {
                        'fdc_id': food['fdc_id'],
                        'description': food['description'],
                        'scientific_name': food['scientific_name'],
                        'common_names': food['common_names'],
                        'food_category': food['food_category'],
                        'nutrients': food['nutrients'],
                        'nutrition_summary': food['nutrition_summary'],
                        'brand_owner': food['brand_owner'],
                        'ingredients': food['ingredients'],
                        'serving_size': food['serving_size'],
                        'serving_size_unit': food['serving_size_unit'],
                        'allergens': food['allergens'],
                        'dietary_flags': food['dietary_flags'],
                        'nutritional_density': food['nutritional_density'],
                        'source': food['source'],
                        'search_text': food['search_text']
                    })
                
                logger.info(f'Inserted {len(validated_data[\"food_items\"])} food items')
            
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