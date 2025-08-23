#!/usr/bin/env python3
"""
Load health information JSON files into medical-mirrors database
Uses the same parsing logic as medical-mirrors update scripts
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add medical-mirrors to Python path
medical_mirrors_src = str(Path(__file__).parent.parent / "services/user/medical-mirrors/src")
if medical_mirrors_src not in sys.path:
    sys.path.insert(0, medical_mirrors_src)

try:
    from config import Config
    from health_info.parser import HealthInfoParser
    from billing_codes.parser import BillingCodesParser
    from database import get_db_session
    from sqlalchemy import text
except ImportError as e:
    print(f"Failed to import medical-mirrors modules: {e}")
    print(f"Make sure medical-mirrors service is properly installed")
    sys.exit(1)


class HealthDataLoader:
    """Load complete health data from JSON files into database"""
    
    def __init__(self, data_dir: str = None):
        self.config = Config()
        self.data_dir = data_dir or self.config.DATA_DIR
        self.logger = self._setup_logging()
        self.health_parser = HealthInfoParser()
        self.billing_parser = BillingCodesParser()
        
        # Statistics
        self.stats = {
            "files_processed": 0,
            "health_topics_loaded": 0,
            "exercises_loaded": 0, 
            "food_items_loaded": 0,
            "billing_codes_loaded": 0,
            "total_items_loaded": 0,
            "errors": []
        }

    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger("health_data_loader")
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def find_json_files(self) -> Dict[str, str]:
        """Find all complete health data JSON files"""
        json_files = {}
        
        # Look for files in health_info, billing_codes/billing subdirectories and data root
        search_dirs = [
            os.path.join(self.data_dir, "health_info"),
            os.path.join(self.data_dir, "billing_codes"),
            os.path.join(self.data_dir, "billing"),
            self.data_dir
        ]
        
        for search_dir in search_dirs:
            if os.path.exists(search_dir):
                for filename in os.listdir(search_dir):
                    if filename.startswith("all_") and filename.endswith("_complete.json"):
                        # Extract dataset type from filename
                        # all_health_topics_complete.json -> health_topics
                        # all_billing_codes_complete.json -> billing_codes
                        dataset_type = filename.replace("all_", "").replace("_complete.json", "")
                        json_files[dataset_type] = os.path.join(search_dir, filename)
        
        return json_files

    def load_json_file(self, file_path: str) -> Dict[str, Any]:
        """Load and validate JSON file"""
        self.logger.info(f"Loading JSON file: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate structure
            if 'metadata' not in data:
                raise ValueError("Missing metadata section")
            
            metadata = data['metadata']
            
            # Handle both health data structure and billing codes structure
            if 'dataset_type' in metadata:
                # Health data structure
                dataset_type = metadata.get('dataset_type')
                if dataset_type not in data:
                    raise ValueError(f"Missing dataset section: {dataset_type}")
                item_count = metadata.get('total_items', 0)
            elif 'total_codes' in metadata:
                # Billing codes structure
                dataset_type = 'billing_codes'
                if 'codes' not in data:
                    raise ValueError("Missing codes section in billing data")
                item_count = metadata.get('total_codes', 0)
            else:
                raise ValueError("Unknown JSON structure - missing dataset_type or total_codes")
            
            self.logger.info(f"Loaded {item_count} items of type {dataset_type}")
            return data
            
        except Exception as e:
            self.logger.error(f"Error loading JSON file {file_path}: {e}")
            self.stats['errors'].append(f"JSON load error in {file_path}: {e}")
            return {}

    def load_all_health_data(self):
        """Load all health data JSON files into database"""
        self.logger.info("Starting health data loading process")
        
        # Find all JSON files
        json_files = self.find_json_files()
        self.logger.info(f"Found {len(json_files)} JSON files: {list(json_files.keys())}")
        
        if not json_files:
            self.logger.warning("No JSON files found! Make sure to run download scripts first.")
            return False
        
        # Load health data files
        all_raw_data = {
            "health_topics": [],
            "exercises": [],
            "food_items": []
        }
        
        # Load billing codes separately
        billing_codes_raw = []
        
        for dataset_type, file_path in json_files.items():
            if dataset_type in all_raw_data:
                # Health data
                file_data = self.load_json_file(file_path)
                if file_data and dataset_type in file_data:
                    all_raw_data[dataset_type] = file_data[dataset_type]
                    self.stats['files_processed'] += 1
            elif dataset_type == 'billing_codes':
                # Billing codes data
                file_data = self.load_json_file(file_path)
                if file_data and 'codes' in file_data:
                    billing_codes_raw.extend(file_data['codes'])
                    self.stats['files_processed'] += 1
        
        # Parse and validate health data using the health parser
        self.logger.info("Parsing and validating health data")
        validated_health_data = self.health_parser.parse_and_validate(all_raw_data)
        
        # Parse and validate billing codes using the billing parser
        validated_billing_codes = []
        if billing_codes_raw:
            self.logger.info(f"Parsing and validating {len(billing_codes_raw)} billing codes")
            validated_billing_codes = self.billing_parser.parse_and_validate(billing_codes_raw)
        
        # Insert into database
        health_success = self._insert_health_data_into_database(validated_health_data)
        billing_success = True
        if validated_billing_codes:
            billing_success = self._insert_billing_codes_into_database(validated_billing_codes)
        
        return health_success and billing_success
    
    def _insert_health_data_into_database(self, validated_data: Dict[str, List[Dict]]) -> bool:
        """Insert validated data into database using medical-mirrors patterns"""
        self.logger.info("Inserting health data into database")
        
        try:
            with get_db_session() as db:
                # Insert health topics
                if validated_data['health_topics']:
                    self.logger.info('Upserting health topics (preserving existing data)')
                    
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
                            ON CONFLICT (topic_id) DO UPDATE SET
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
                            'search_text': topic['search_text']
                        })
                    
                    self.stats['health_topics_loaded'] = len(validated_data['health_topics'])
                    self.logger.info(f'Inserted {len(validated_data["health_topics"])} health topics')
                
                # Insert exercises
                if validated_data['exercises']:
                    self.logger.info('Upserting exercises (preserving existing data)')
                    
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
                    
                    self.stats['exercises_loaded'] = len(validated_data['exercises'])
                    self.logger.info(f'Inserted {len(validated_data["exercises"])} exercises')
                
                # Insert food items
                if validated_data['food_items']:
                    self.logger.info('Upserting food items (preserving existing data)')
                    
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
                            'allergens': json.dumps(food.get('allergens', [])),
                            'dietary_flags': json.dumps(food.get('dietary_flags', [])),
                            'nutritional_density': food.get('nutritional_density'),
                            'source': food['source'],
                            'search_text': food['search_text']
                        })
                    
                    self.stats['food_items_loaded'] = len(validated_data['food_items'])
                    self.logger.info(f'Inserted {len(validated_data["food_items"])} food items')
                
                # Commit all changes
                db.commit()
                
                # Calculate total
                self.stats['total_items_loaded'] = (
                    self.stats['health_topics_loaded'] +
                    self.stats['exercises_loaded'] +
                    self.stats['food_items_loaded']
                )
                
                self.logger.info(f"✅ Successfully loaded {self.stats['total_items_loaded']} total health items")
                return True
                
        except Exception as e:
            self.logger.error(f"Database insertion failed: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            self.stats['errors'].append(f"Database insertion error: {e}")
            return False

    def _insert_billing_codes_into_database(self, validated_codes: List[Dict]) -> bool:
        """Insert validated billing codes into database using medical-mirrors patterns"""
        self.logger.info("Inserting billing codes into database")
        
        try:
            with get_db_session() as db:
                self.logger.info('Upserting billing codes (preserving existing data)')
                
                # Use UPSERT with composite key (code + code_type) to preserve existing data
                for code_data in validated_codes:
                    db.execute(text('''
                        INSERT INTO billing_codes (
                            code, short_description, long_description, description,
                            code_type, category, coverage_notes, effective_date,
                            termination_date, is_active, modifier_required,
                            gender_specific, age_specific, bilateral_indicator,
                            source, search_text, last_updated, search_vector
                        ) VALUES (
                            :code, :short_description, :long_description, :description,
                            :code_type, :category, :coverage_notes, :effective_date,
                            :termination_date, :is_active, :modifier_required,
                            :gender_specific, :age_specific, :bilateral_indicator,
                            :source, :search_text, NOW(), 
                            to_tsvector('english', COALESCE(:search_text, ''))
                        )
                        ON CONFLICT (code) DO UPDATE SET
                            -- Only update if we have better/more complete information
                            short_description = COALESCE(NULLIF(EXCLUDED.short_description, ''), billing_codes.short_description),
                            long_description = COALESCE(NULLIF(EXCLUDED.long_description, ''), billing_codes.long_description),
                            description = COALESCE(NULLIF(EXCLUDED.description, ''), billing_codes.description),
                            category = COALESCE(NULLIF(EXCLUDED.category, ''), billing_codes.category),
                            coverage_notes = COALESCE(NULLIF(EXCLUDED.coverage_notes, ''), billing_codes.coverage_notes),
                            effective_date = COALESCE(EXCLUDED.effective_date, billing_codes.effective_date),
                            termination_date = COALESCE(EXCLUDED.termination_date, billing_codes.termination_date),
                            is_active = COALESCE(EXCLUDED.is_active, billing_codes.is_active),
                            modifier_required = COALESCE(EXCLUDED.modifier_required, billing_codes.modifier_required),
                            gender_specific = COALESCE(NULLIF(EXCLUDED.gender_specific, ''), billing_codes.gender_specific),
                            age_specific = COALESCE(NULLIF(EXCLUDED.age_specific, ''), billing_codes.age_specific),
                            bilateral_indicator = COALESCE(EXCLUDED.bilateral_indicator, billing_codes.bilateral_indicator),
                            source = COALESCE(NULLIF(EXCLUDED.source, ''), billing_codes.source),
                            search_text = COALESCE(NULLIF(EXCLUDED.search_text, ''), billing_codes.search_text),
                            search_vector = to_tsvector('english', COALESCE(EXCLUDED.search_text, '')),
                            last_updated = NOW()
                    '''), {
                        'code': code_data['code'],
                        'short_description': code_data.get('short_description'),
                        'long_description': code_data.get('long_description'),
                        'description': code_data.get('description'),
                        'code_type': code_data['code_type'],
                        'category': code_data.get('category'),
                        'coverage_notes': code_data.get('coverage_notes'),
                        'effective_date': code_data['effective_date'] if code_data.get('effective_date') and code_data['effective_date'] != '' else None,
                        'termination_date': code_data['termination_date'] if code_data.get('termination_date') and code_data['termination_date'] != '' else None,
                        'is_active': code_data.get('is_active', True),
                        'modifier_required': code_data.get('modifier_required', False),
                        'gender_specific': code_data.get('gender_specific'),
                        'age_specific': code_data.get('age_specific'),
                        'bilateral_indicator': code_data.get('bilateral_indicator', False),
                        'source': code_data.get('source'),
                        'search_text': code_data.get('search_text')
                    })
                
                db.commit()
                
                # Update statistics
                result = db.execute(text('''
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN is_active = true THEN 1 END) as active,
                        COUNT(CASE WHEN code_type = 'HCPCS' THEN 1 END) as hcpcs,
                        COUNT(CASE WHEN code_type = 'CPT' THEN 1 END) as cpt
                    FROM billing_codes
                '''))
                
                stats = result.fetchone()
                self.stats['billing_codes_loaded'] = len(validated_codes)
                
                # Update total to include billing codes
                self.stats['total_items_loaded'] = (
                    self.stats['health_topics_loaded'] +
                    self.stats['exercises_loaded'] +
                    self.stats['food_items_loaded'] +
                    self.stats['billing_codes_loaded']
                )
                
                self.logger.info(f'Successfully inserted {stats.total} billing codes total')
                self.logger.info(f'  Active: {stats.active}, HCPCS: {stats.hcpcs}, CPT: {stats.cpt}')
                self.logger.info(f'  Newly loaded: {len(validated_codes)}')
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error inserting billing codes into database: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            self.stats['errors'].append(f"Billing codes database insert error: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get loading statistics"""
        return self.stats.copy()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Load health information JSON files into medical-mirrors database"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        help="Custom data directory (default: /app/data)"
    )
    
    args = parser.parse_args()
    
    # Create loader
    loader = HealthDataLoader(data_dir=args.data_dir)
    
    print("📥 Loading health information data into medical-mirrors database...")
    print(f"📁 Data directory: {loader.data_dir}")
    
    # Load data
    success = loader.load_all_health_data()
    
    # Show results
    stats = loader.get_stats()
    print(f"\n📊 Loading Results:")
    print(f"  Files processed: {stats['files_processed']}")
    print(f"  Health topics: {stats['health_topics_loaded']}")
    print(f"  Exercises: {stats['exercises_loaded']}")
    print(f"  Food items: {stats['food_items_loaded']}")
    print(f"  Billing codes: {stats['billing_codes_loaded']}")
    print(f"  Total items: {stats['total_items_loaded']}")
    
    if stats['errors']:
        print(f"\n⚠️  Errors ({len(stats['errors'])}):")
        for error in stats['errors']:
            print(f"    {error}")
    
    if success:
        print("\n✅ Health data loading completed successfully")
        sys.exit(0)
    else:
        print("\n❌ Health data loading failed")
        sys.exit(1)