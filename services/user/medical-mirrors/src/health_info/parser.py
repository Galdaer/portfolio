"""
Health information parser and data processor
"""

import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class HealthInfoParser:
    """Parser for health information data from various APIs"""
    
    def __init__(self):
        self.processed_items = 0
        self.validation_errors = 0
        self.duplicates_removed = 0
        self.categories = {
            "health_topics": 0,
            "exercises": 0,
            "food_items": 0
        }
    
    def parse_and_validate(self, raw_data: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """Parse and validate health information data"""
        logger.info(f"Parsing and validating health information data")
        
        validated_data = {
            "health_topics": [],
            "exercises": [],
            "food_items": []
        }
        
        # Process each category
        for category, items in raw_data.items():
            if category in validated_data:
                validated_items = self._parse_category(category, items)
                validated_data[category] = validated_items
                self.categories[category] = len(validated_items)
        
        total_processed = sum(self.categories.values())
        logger.info(f"Parsed {total_processed} total items: "
                   f"{self.categories['health_topics']} health topics, "
                   f"{self.categories['exercises']} exercises, "
                   f"{self.categories['food_items']} food items")
        
        return validated_data
    
    def _parse_category(self, category: str, items: List[Dict]) -> List[Dict]:
        """Parse items for a specific category"""
        validated_items = []
        seen_items = set()
        
        for item in items:
            try:
                if category == "health_topics":
                    parsed_item = self._parse_health_topic(item)
                elif category == "exercises":
                    parsed_item = self._parse_exercise(item)
                elif category == "food_items":
                    parsed_item = self._parse_food_item(item)
                else:
                    continue
                
                if parsed_item and self._validate_item(parsed_item, category):
                    # Check for duplicates
                    item_key = self._get_item_key(parsed_item, category)
                    if item_key not in seen_items:
                        validated_items.append(parsed_item)
                        seen_items.add(item_key)
                        self.processed_items += 1
                    else:
                        self.duplicates_removed += 1
                else:
                    self.validation_errors += 1
                    
            except Exception as e:
                logger.error(f"Error parsing {category} item: {e}")
                self.validation_errors += 1
                continue
        
        return validated_items
    
    def _parse_health_topic(self, raw_topic: Dict) -> Optional[Dict]:
        """Parse a health topic from MyHealthfinder"""
        try:
            topic_id = raw_topic.get("topic_id", "")
            title = raw_topic.get("title", "").strip()
            
            if not topic_id or not title:
                return None
            
            parsed = {
                "topic_id": topic_id,
                "title": title,
                "category": raw_topic.get("category", "General Health").strip(),
                "url": raw_topic.get("url", "").strip(),
                "last_reviewed": self._parse_date(raw_topic.get("last_reviewed")),
                "audience": raw_topic.get("audience", []),
                "sections": self._parse_sections(raw_topic.get("sections", [])),
                "related_topics": raw_topic.get("related_topics", []),
                "summary": self._extract_summary(raw_topic),
                "keywords": self._extract_keywords(title, raw_topic.get("sections", [])),
                "content_length": self._calculate_content_length(raw_topic),
                "source": raw_topic.get("source", "myhealthfinder"),
                "last_updated": raw_topic.get("last_updated", datetime.now().isoformat()),
                "search_text": raw_topic.get("search_text", "").lower(),
                "item_type": "health_topic"
            }
            
            return parsed
            
        except Exception as e:
            logger.error(f"Error parsing health topic: {e}")
            return None
    
    def _parse_exercise(self, raw_exercise: Dict) -> Optional[Dict]:
        """Parse an exercise from ExerciseDB"""
        try:
            exercise_id = raw_exercise.get("exercise_id", "")
            name = raw_exercise.get("name", "").strip()
            
            if not exercise_id or not name:
                return None
            
            parsed = {
                "exercise_id": exercise_id,
                "name": name,
                "body_part": raw_exercise.get("body_part", "").strip(),
                "equipment": raw_exercise.get("equipment", "").strip(),
                "target": raw_exercise.get("target", "").strip(),
                "secondary_muscles": raw_exercise.get("secondary_muscles", []),
                "instructions": self._parse_instructions(raw_exercise.get("instructions", [])),
                "gif_url": raw_exercise.get("gif_url", "").strip(),
                "difficulty_level": self._determine_difficulty(raw_exercise),
                "exercise_type": self._determine_exercise_type(raw_exercise),
                "duration_estimate": self._estimate_duration(raw_exercise),
                "calories_estimate": self._estimate_calories(raw_exercise),
                "source": raw_exercise.get("source", "exercisedb"),
                "last_updated": raw_exercise.get("last_updated", datetime.now().isoformat()),
                "search_text": raw_exercise.get("search_text", "").lower(),
                "item_type": "exercise"
            }
            
            return parsed
            
        except Exception as e:
            logger.error(f"Error parsing exercise: {e}")
            return None
    
    def _parse_food_item(self, raw_food: Dict) -> Optional[Dict]:
        """Parse a food item from USDA FoodData Central"""
        try:
            fdc_id = raw_food.get("fdc_id")
            description = raw_food.get("description", "").strip()
            
            if not fdc_id or not description:
                return None
            
            nutrients = raw_food.get("nutrients", [])
            
            parsed = {
                "fdc_id": fdc_id,
                "description": description,
                "scientific_name": (raw_food.get("scientific_name") or "").strip(),
                "common_names": (raw_food.get("common_names") or "").strip(),
                "food_category": (raw_food.get("food_category") or "").strip(),
                "nutrients": nutrients,
                "nutrition_summary": self._create_nutrition_summary(nutrients),
                "brand_owner": (raw_food.get("brand_owner") or "").strip(),
                "ingredients": (raw_food.get("ingredients") or "").strip(),
                "serving_size": raw_food.get("serving_size"),
                "serving_size_unit": (raw_food.get("serving_size_unit") or "").strip(),
                "allergens": self._detect_allergens(raw_food),
                "dietary_flags": self._determine_dietary_flags(raw_food),
                "nutritional_density": self._calculate_nutritional_density(nutrients),
                "source": raw_food.get("source", "usda_fooddata"),
                "last_updated": raw_food.get("last_updated", datetime.now().isoformat()),
                "search_text": (raw_food.get("search_text") or "").lower(),
                "item_type": "food_item"
            }
            
            return parsed
            
        except Exception as e:
            logger.error(f"Error parsing food item: {e}")
            return None
    
    def _parse_sections(self, sections: List[Dict]) -> List[Dict]:
        """Parse content sections"""
        parsed_sections = []
        
        for section in sections:
            if isinstance(section, dict):
                parsed_section = {
                    "title": section.get("title", "").strip(),
                    "content": section.get("content", "").strip(),
                    "type": section.get("type", "content"),
                    "word_count": len(section.get("content", "").split())
                }
                parsed_sections.append(parsed_section)
        
        return parsed_sections
    
    def _parse_instructions(self, instructions: List[str]) -> List[Dict]:
        """Parse exercise instructions into structured format"""
        parsed_instructions = []
        
        for i, instruction in enumerate(instructions):
            if isinstance(instruction, str) and instruction.strip():
                parsed_instructions.append({
                    "step": i + 1,
                    "instruction": instruction.strip(),
                    "word_count": len(instruction.split())
                })
        
        return parsed_instructions
    
    def _extract_summary(self, topic: Dict) -> str:
        """Extract a summary from health topic data"""
        sections = topic.get("sections", [])
        
        if sections:
            # Try to find an introduction or summary section
            for section in sections:
                if isinstance(section, dict):
                    title = section.get("title", "").lower()
                    content = section.get("content", "")
                    
                    if any(keyword in title for keyword in ["summary", "overview", "introduction"]):
                        return content[:500] + "..." if len(content) > 500 else content
            
            # If no summary section, use first section
            first_section = sections[0]
            if isinstance(first_section, dict):
                content = first_section.get("content", "")
                return content[:500] + "..." if len(content) > 500 else content
        
        return topic.get("title", "")
    
    def _extract_keywords(self, title: str, sections: List[Dict]) -> List[str]:
        """Extract keywords from title and content"""
        keywords = set()
        
        # Extract from title
        title_words = re.findall(r'\b\w{4,}\b', title.lower())
        keywords.update(title_words)
        
        # Extract from sections
        for section in sections:
            if isinstance(section, dict):
                content = section.get("content", "")
                content_words = re.findall(r'\b\w{5,}\b', content.lower())
                keywords.update(content_words[:10])  # Limit to avoid too many keywords
        
        # Filter out common words
        common_words = {"that", "with", "have", "this", "from", "they", "been", "were", "said", "each", "which"}
        keywords = keywords - common_words
        
        return sorted(list(keywords)[:20])  # Return top 20 keywords
    
    def _calculate_content_length(self, topic: Dict) -> int:
        """Calculate total content length for a health topic"""
        total_length = 0
        sections = topic.get("sections", [])
        
        for section in sections:
            if isinstance(section, dict):
                content = section.get("content", "")
                total_length += len(content)
        
        return total_length
    
    def _determine_difficulty(self, exercise: Dict) -> str:
        """Determine exercise difficulty level"""
        equipment = exercise.get("equipment", "").lower()
        name = exercise.get("name", "").lower()
        
        # Simple heuristic based on equipment and exercise name
        if "bodyweight" in equipment or equipment == "":
            return "beginner"
        elif "barbell" in equipment or "olympic" in name:
            return "advanced"
        else:
            return "intermediate"
    
    def _determine_exercise_type(self, exercise: Dict) -> str:
        """Determine exercise type"""
        target = exercise.get("target", "").lower()
        body_part = exercise.get("body_part", "").lower()
        name = exercise.get("name", "").lower()
        
        if "cardio" in name or "running" in name:
            return "cardio"
        elif "stretch" in name or "flexibility" in name:
            return "flexibility"
        elif any(term in name for term in ["squat", "deadlift", "bench", "press"]):
            return "strength"
        else:
            return "general"
    
    def _estimate_duration(self, exercise: Dict) -> str:
        """Estimate exercise duration"""
        exercise_type = self._determine_exercise_type(exercise)
        
        duration_map = {
            "cardio": "20-30 minutes",
            "strength": "45-60 seconds per set",
            "flexibility": "30-60 seconds per stretch",
            "general": "varies"
        }
        
        return duration_map.get(exercise_type, "varies")
    
    def _estimate_calories(self, exercise: Dict) -> str:
        """Estimate calories burned"""
        body_part = exercise.get("body_part", "").lower()
        
        if "cardio" in body_part:
            return "200-400 per 30 minutes"
        elif "upper" in body_part or "lower" in body_part:
            return "100-200 per 30 minutes"
        else:
            return "varies by intensity"
    
    def _create_nutrition_summary(self, nutrients: List[Dict]) -> Dict:
        """Create a nutrition summary from nutrients list"""
        summary = {
            "calories": 0,
            "protein_g": 0,
            "fat_g": 0,
            "carbs_g": 0,
            "fiber_g": 0,
            "sodium_mg": 0
        }
        
        nutrient_mapping = {
            "energy": "calories",
            "protein": "protein_g",
            "total lipid": "fat_g",
            "carbohydrate": "carbs_g",
            "fiber": "fiber_g",
            "sodium": "sodium_mg"
        }
        
        for nutrient in nutrients:
            name = nutrient.get("name", "").lower()
            amount = nutrient.get("amount", 0)
            
            for key_term, summary_key in nutrient_mapping.items():
                if key_term in name:
                    summary[summary_key] = amount
                    break
        
        return summary
    
    def _detect_allergens(self, food: Dict) -> List[str]:
        """Detect common allergens in food"""
        allergens = []
        
        description = food.get("description", "").lower()
        ingredients = food.get("ingredients", "").lower()
        text_to_check = f"{description} {ingredients}"
        
        allergen_keywords = {
            "dairy": ["milk", "cheese", "butter", "cream", "lactose"],
            "nuts": ["peanut", "almond", "walnut", "pecan", "cashew"],
            "gluten": ["wheat", "barley", "rye", "gluten"],
            "soy": ["soy", "soybean", "tofu"],
            "eggs": ["egg", "eggs"],
            "shellfish": ["shrimp", "crab", "lobster", "shellfish"]
        }
        
        for allergen, keywords in allergen_keywords.items():
            if any(keyword in text_to_check for keyword in keywords):
                allergens.append(allergen)
        
        return allergens
    
    def _determine_dietary_flags(self, food: Dict) -> List[str]:
        """Determine dietary flags (vegan, vegetarian, etc.)"""
        flags = []
        
        description = food.get("description", "").lower()
        ingredients = food.get("ingredients", "").lower()
        
        # Simple heuristics - would need more sophisticated logic
        animal_products = ["meat", "beef", "chicken", "pork", "fish", "dairy", "milk", "egg"]
        
        if not any(product in description for product in animal_products):
            flags.append("potentially_vegan")
        
        if "organic" in description:
            flags.append("organic")
            
        if "whole grain" in description:
            flags.append("whole_grain")
        
        return flags
    
    def _calculate_nutritional_density(self, nutrients: List[Dict]) -> float:
        """Calculate a simple nutritional density score"""
        score = 0
        
        for nutrient in nutrients:
            name = nutrient.get("name", "").lower()
            amount = nutrient.get("amount", 0) or 0
            
            # Simple scoring based on beneficial nutrients
            if "vitamin" in name or "mineral" in name:
                score += min(amount * 0.1, 10)  # Cap contribution
            elif "fiber" in name:
                score += min(amount * 0.5, 10)
            elif "protein" in name:
                score += min(amount * 0.2, 10)
        
        return min(score, 100)  # Cap at 100
    
    def _get_item_key(self, item: Dict, category: str) -> str:
        """Get unique key for deduplication"""
        if category == "health_topics":
            return item.get("topic_id", "")
        elif category == "exercises":
            return item.get("exercise_id", "")
        elif category == "food_items":
            return str(item.get("fdc_id", ""))
        return ""
    
    def _validate_item(self, item: Dict, category: str) -> bool:
        """Validate parsed item"""
        try:
            if category == "health_topics":
                return bool(item.get("topic_id") and item.get("title"))
            elif category == "exercises":
                return bool(item.get("exercise_id") and item.get("name"))
            elif category == "food_items":
                return bool(item.get("fdc_id") and item.get("description"))
            
            return False
            
        except Exception:
            return False
    
    def _parse_date(self, date_str) -> Optional[str]:
        """Parse date string into standard format"""
        if not date_str:
            return None
        
        try:
            if isinstance(date_str, datetime):
                return date_str.isoformat()
            return str(date_str)
        except Exception:
            return None
    
    def get_parsing_stats(self) -> Dict:
        """Get parsing statistics"""
        return {
            "processed_items": self.processed_items,
            "validation_errors": self.validation_errors,
            "duplicates_removed": self.duplicates_removed,
            "categories_processed": self.categories,
            "success_rate": (
                self.processed_items / (self.processed_items + self.validation_errors)
                if (self.processed_items + self.validation_errors) > 0 else 0
            )
        }


def main():
    """Test the health info parser"""
    logging.basicConfig(level=logging.INFO)
    
    # Test data
    test_data = {
        "health_topics": [
            {
                "topic_id": "123",
                "title": "Heart Health",
                "category": "Cardiovascular",
                "sections": [{"title": "Overview", "content": "Heart health is important..."}],
                "source": "test"
            }
        ],
        "exercises": [
            {
                "exercise_id": "456",
                "name": "Push-ups",
                "body_part": "chest",
                "equipment": "bodyweight",
                "target": "pectorals",
                "instructions": ["Start in plank position", "Lower body", "Push up"],
                "source": "test"
            }
        ],
        "food_items": [
            {
                "fdc_id": 789,
                "description": "Apple, raw",
                "nutrients": [
                    {"name": "Energy", "amount": 52, "unit": "kcal"},
                    {"name": "Protein", "amount": 0.3, "unit": "g"}
                ],
                "source": "test"
            }
        ]
    }
    
    parser = HealthInfoParser()
    parsed_data = parser.parse_and_validate(test_data)
    
    print(f"Parsed data:")
    for category, items in parsed_data.items():
        print(f"  {category}: {len(items)} items")
    
    stats = parser.get_parsing_stats()
    print(f"\nParsing stats: {stats}")


if __name__ == "__main__":
    main()