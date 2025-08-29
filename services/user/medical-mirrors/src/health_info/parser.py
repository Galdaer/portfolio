"""
Health information parser and data processor
"""

import logging
import re
from datetime import datetime

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
            "food_items": 0,
        }

    def parse_and_validate(self, raw_data: dict[str, list[dict]]) -> dict[str, list[dict]]:
        """Parse and validate health information data"""
        logger.info("Parsing and validating health information data")

        validated_data = {
            "health_topics": [],
            "exercises": [],
            "food_items": [],
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

    def _parse_category(self, category: str, items: list[dict]) -> list[dict]:
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
                logger.exception(f"Error parsing {category} item: {e}")
                self.validation_errors += 1
                continue

        return validated_items

    def _parse_health_topic(self, raw_topic: dict) -> dict | None:
        """Parse a health topic from MyHealthfinder"""
        try:
            topic_id = raw_topic.get("topic_id", "")
            title = raw_topic.get("title", "").strip()

            if not topic_id or not title:
                return None

            return {
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
                "item_type": "health_topic",
            }


        except Exception as e:
            logger.exception(f"Error parsing health topic: {e}")
            return None

    def _parse_exercise(self, raw_exercise: dict) -> dict | None:
        """Parse an exercise from ExerciseDB"""
        try:
            exercise_id = raw_exercise.get("exercise_id", "")
            name = raw_exercise.get("name", "").strip()

            if not exercise_id or not name:
                return None

            return {
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
                "item_type": "exercise",
            }


        except Exception as e:
            logger.exception(f"Error parsing exercise: {e}")
            return None

    def _parse_food_item(self, raw_food: dict) -> dict | None:
        """Parse a food item from USDA FoodData Central"""
        try:
            fdc_id = raw_food.get("fdc_id")
            description = raw_food.get("description", "").strip()

            if not fdc_id or not description:
                return None

            nutrients = raw_food.get("nutrients", [])

            return {
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
                "allergens": {},  # Allergens now included in dietary_flags
                "dietary_flags": self._determine_dietary_flags(raw_food),
                "nutritional_density": self._calculate_nutritional_density(nutrients),
                "source": raw_food.get("source", "usda_fooddata"),
                "last_updated": raw_food.get("last_updated", datetime.now().isoformat()),
                "search_text": (raw_food.get("search_text") or "").lower(),
                "item_type": "food_item",
            }


        except Exception as e:
            logger.exception(f"Error parsing food item: {e}")
            return None

    def _parse_sections(self, sections: list[dict]) -> list[dict]:
        """Parse content sections"""
        parsed_sections = []

        for section in sections:
            if isinstance(section, dict):
                parsed_section = {
                    "title": section.get("title", "").strip(),
                    "content": section.get("content", "").strip(),
                    "type": section.get("type", "content"),
                    "word_count": len(section.get("content", "").split()),
                }
                parsed_sections.append(parsed_section)

        return parsed_sections

    def _parse_instructions(self, instructions: list[str]) -> list[dict]:
        """Parse exercise instructions into structured format"""
        parsed_instructions = []

        for i, instruction in enumerate(instructions):
            if isinstance(instruction, str) and instruction.strip():
                parsed_instructions.append({
                    "step": i + 1,
                    "instruction": instruction.strip(),
                    "word_count": len(instruction.split()),
                })

        return parsed_instructions

    def _extract_summary(self, topic: dict) -> str:
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

    def _extract_keywords(self, title: str, sections: list[dict]) -> list[str]:
        """Extract keywords from title and content"""
        keywords = set()

        # Extract from title
        title_words = re.findall(r"\b\w{4,}\b", title.lower())
        keywords.update(title_words)

        # Extract from sections
        for section in sections:
            if isinstance(section, dict):
                content = section.get("content", "")
                content_words = re.findall(r"\b\w{5,}\b", content.lower())
                keywords.update(content_words[:10])  # Limit to avoid too many keywords

        # Filter out common words
        common_words = {"that", "with", "have", "this", "from", "they", "been", "were", "said", "each", "which"}
        keywords = keywords - common_words

        return sorted(list(keywords)[:20])  # Return top 20 keywords

    def _calculate_content_length(self, topic: dict) -> int:
        """Calculate total content length for a health topic"""
        total_length = 0
        sections = topic.get("sections", [])

        for section in sections:
            if isinstance(section, dict):
                content = section.get("content", "")
                total_length += len(content)

        return total_length

    def _determine_difficulty(self, exercise: dict) -> str:
        """Determine exercise difficulty level"""
        equipment = exercise.get("equipment", "").lower()
        name = exercise.get("name", "").lower()

        # Simple heuristic based on equipment and exercise name
        if "bodyweight" in equipment or equipment == "":
            return "beginner"
        if "barbell" in equipment or "olympic" in name:
            return "advanced"
        return "intermediate"

    def _determine_exercise_type(self, exercise: dict) -> str:
        """Determine exercise type"""
        exercise.get("target", "").lower()
        exercise.get("body_part", "").lower()
        name = exercise.get("name", "").lower()

        if "cardio" in name or "running" in name:
            return "cardio"
        if "stretch" in name or "flexibility" in name:
            return "flexibility"
        if any(term in name for term in ["squat", "deadlift", "bench", "press"]):
            return "strength"
        return "general"

    def _estimate_duration(self, exercise: dict) -> str:
        """Estimate exercise duration"""
        exercise_type = self._determine_exercise_type(exercise)

        duration_map = {
            "cardio": "20-30 minutes",
            "strength": "45-60 seconds per set",
            "flexibility": "30-60 seconds per stretch",
            "general": "varies",
        }

        return duration_map.get(exercise_type, "varies")

    def _estimate_calories(self, exercise: dict) -> str:
        """Estimate calories burned"""
        body_part = exercise.get("body_part", "").lower()

        if "cardio" in body_part:
            return "200-400 per 30 minutes"
        if "upper" in body_part or "lower" in body_part:
            return "100-200 per 30 minutes"
        return "varies by intensity"

    def _create_nutrition_summary(self, nutrients: list[dict]) -> dict:
        """Create a nutrition summary from nutrients list"""
        summary = {
            "calories": 0,
            "protein_g": 0,
            "fat_g": 0,
            "carbs_g": 0,
            "fiber_g": 0,
            "sodium_mg": 0,
        }

        nutrient_mapping = {
            "energy": "calories",
            "protein": "protein_g",
            "total lipid": "fat_g",
            "carbohydrate": "carbs_g",
            "fiber": "fiber_g",
            "sodium": "sodium_mg",
        }

        for nutrient in nutrients:
            name = nutrient.get("name", "").lower()
            amount = nutrient.get("amount", 0)

            for key_term, summary_key in nutrient_mapping.items():
                if key_term in name:
                    summary[summary_key] = amount
                    break

        return summary

    def _detect_allergens(self, food: dict) -> dict:
        """Detect FDA major allergens (FALCPA/FASTER Act) in food"""
        allergens_detected = []

        description = food.get("description", "").lower()
        ingredients = food.get("ingredients", "").lower()
        food_category = food.get("food_category", "").lower()
        text_to_check = f"{description} {ingredients} {food_category}"

        # FDA's 9 major allergens per FALCPA and FASTER Act (2021)
        fda_allergen_keywords = {
            "milk": ["milk", "dairy", "cheese", "butter", "cream", "lactose", "casein", "whey", "yogurt"],
            "eggs": ["egg", "eggs", "albumin", "mayonnaise"],
            "fish": ["fish", "salmon", "tuna", "cod", "halibut", "tilapia", "catfish", "bass", "trout"],
            "crustacean_shellfish": ["shrimp", "crab", "lobster", "crayfish", "prawns"],
            "tree_nuts": ["almond", "brazil nut", "cashew", "chestnut", "filbert", "hazelnut", 
                         "macadamia", "pecan", "pine nut", "pistachio", "walnut"],
            "peanuts": ["peanut", "peanuts", "groundnut"],
            "wheat": ["wheat", "flour", "gluten", "bulgur", "couscous", "seitan", "semolina"],
            "soybeans": ["soy", "soybean", "tofu", "tempeh", "miso", "edamame", "lecithin"],
            "sesame": ["sesame", "tahini", "sesame seed", "sesame oil"]
        }

        for allergen, keywords in fda_allergen_keywords.items():
            if any(keyword in text_to_check for keyword in keywords):
                allergens_detected.append(allergen)

        return {
            "allergens": allergens_detected,
            "disclaimer": "Allergen detection based on text parsing of description, ingredients, and category. Not a substitute for manufacturer allergen declarations. Consult product labels for definitive allergen information.",
            "data_source": "FDA FALCPA & FASTER Act (2021)"
        }

    def _determine_dietary_flags(self, food: dict) -> dict:
        """Determine professional dietary flags using USDA/FDA standards"""
        
        # Get MyPlate food group classification
        myplate_group = self._map_to_myplate_group(food.get("food_category", ""))
        
        # Get FDA nutritional claims
        fda_nutritional_claims = self._calculate_fda_nutritional_claims(food.get("nutrients", []))
        
        # Get potential allergens
        allergen_data = self._detect_allergens(food)
        potential_allergens = allergen_data.get("allergens", [])
        
        # Get basic dietary classifications (conservative)
        basic_flags = self._get_basic_dietary_flags(food)
        
        return {
            "myplate_food_group": myplate_group,
            "fda_nutritional_claims": fda_nutritional_claims,
            "potential_allergens": potential_allergens,
            "basic_classifications": basic_flags,
            "data_sources": {
                "myplate_mapping": "USDA MyPlate Guidelines",
                "nutritional_claims": "FDA Code of Federal Regulations Title 21",
                "allergen_detection": "FDA FALCPA & FASTER Act (2021)"
            },
            "disclaimers": {
                "allergen_disclaimer": "Allergen detection based on text parsing. Not a substitute for manufacturer declarations.",
                "nutritional_disclaimer": "Nutritional claims calculated from available nutrient data using FDA standards.",
                "classification_disclaimer": "Classifications are informational only and not medical advice."
            },
            "last_updated": datetime.now().isoformat()
        }

    def _calculate_nutritional_density(self, nutrients: list[dict]) -> float:
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

    def _get_item_key(self, item: dict, category: str) -> str:
        """Get unique key for deduplication"""
        if category == "health_topics":
            return item.get("topic_id", "")
        if category == "exercises":
            return item.get("exercise_id", "")
        if category == "food_items":
            return str(item.get("fdc_id", ""))
        return ""

    def _validate_item(self, item: dict, category: str) -> bool:
        """Validate parsed item"""
        try:
            if category == "health_topics":
                return bool(item.get("topic_id") and item.get("title"))
            if category == "exercises":
                return bool(item.get("exercise_id") and item.get("name"))
            if category == "food_items":
                return bool(item.get("fdc_id") and item.get("description"))

            return False

        except Exception:
            return False

    def _parse_date(self, date_str) -> str | None:
        """Parse date string into standard format"""
        if not date_str:
            return None

        try:
            if isinstance(date_str, datetime):
                return date_str.isoformat()
            return str(date_str)
        except Exception:
            return None

    def _map_to_myplate_group(self, food_category: str) -> str:
        """Map USDA food category to MyPlate food group"""
        category = food_category.lower()
        
        # USDA MyPlate food group mappings
        myplate_mapping = {
            "vegetables": [
                "vegetables and vegetable products",
                "legumes and legume products"  # Per MyPlate, legumes count as vegetables
            ],
            "fruits": [
                "fruits and fruit juices"
            ],
            "grains": [
                "cereal grains and pasta",
                "baked products",
                "breakfast cereals"
            ],
            "protein": [
                "beef products", "pork products", "lamb, veal, and game products",
                "poultry products", "sausages and luncheon meats",
                "finfish and shellfish products", "nut and seed products",
                "legumes and legume products"  # Also counts as protein
            ],
            "dairy": [
                "dairy and egg products"
            ]
        }
        
        for group, categories in myplate_mapping.items():
            if any(cat in category for cat in categories):
                # Handle legumes (can be both vegetables and protein)
                if "legume" in category:
                    return f"{group}_legumes"  # Special designation
                return group
        
        return "other"
    
    def _calculate_fda_nutritional_claims(self, nutrients: list[dict]) -> list[str]:
        """Calculate FDA nutritional claims using CFR Title 21 standards"""
        claims = []
        
        # Extract nutrient values
        nutrient_values = {}
        for nutrient in nutrients:
            name = nutrient.get("name", "").lower()
            try:
                amount = float(nutrient.get("amount", 0))
                nutrient_values[name] = amount
            except (ValueError, TypeError):
                continue
        
        # FDA nutritional claim thresholds (CFR Title 21)
        
        # Fat claims
        total_fat = nutrient_values.get("total lipid (fat)", 0)
        if total_fat < 0.5:
            claims.append("fat_free")
        elif total_fat <= 3:
            claims.append("low_fat")
        
        # Sodium claims  
        sodium = nutrient_values.get("sodium, na", 0)
        if sodium < 5:
            claims.append("sodium_free")
        elif sodium <= 140:
            claims.append("low_sodium")
        
        # Protein claims
        protein = nutrient_values.get("protein", 0)
        if protein >= 10:
            claims.append("high_protein")
        elif protein >= 5:
            claims.append("good_source_protein")
        
        # Fiber claims
        fiber = nutrient_values.get("fiber, total dietary", 0)
        if fiber >= 5:
            claims.append("high_fiber")
        elif fiber >= 2.5:
            claims.append("good_source_fiber")
        
        # Calorie claims (per 100g serving)
        energy = nutrient_values.get("energy", 0)
        if energy < 5:
            claims.append("calorie_free")
        elif energy <= 40:
            claims.append("low_calorie")
        
        return claims
    
    def _get_basic_dietary_flags(self, food: dict) -> list[str]:
        """Get basic dietary flags with conservative approach"""
        flags = []
        
        description = food.get("description", "").lower()
        ingredients = food.get("ingredients", "").lower()
        text_to_check = f"{description} {ingredients}"
        
        # Conservative classifications with "potentially" prefix
        animal_products = ["meat", "beef", "chicken", "pork", "fish", "dairy", "milk", "egg", "cheese", "butter"]
        
        if not any(product in text_to_check for product in animal_products):
            flags.append("potentially_plant_based")
        
        # Only add these if explicitly mentioned
        if "organic" in text_to_check:
            flags.append("labeled_organic")
        
        if "whole grain" in text_to_check or "whole wheat" in text_to_check:
            flags.append("whole_grain")
            
        if "gluten free" in text_to_check or "gluten-free" in text_to_check:
            flags.append("labeled_gluten_free")
        
        return flags

    def get_parsing_stats(self) -> dict:
        """Get parsing statistics"""
        return {
            "processed_items": self.processed_items,
            "validation_errors": self.validation_errors,
            "duplicates_removed": self.duplicates_removed,
            "categories_processed": self.categories,
            "success_rate": (
                self.processed_items / (self.processed_items + self.validation_errors)
                if (self.processed_items + self.validation_errors) > 0 else 0
            ),
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
                "source": "test",
            },
        ],
        "exercises": [
            {
                "exercise_id": "456",
                "name": "Push-ups",
                "body_part": "chest",
                "equipment": "bodyweight",
                "target": "pectorals",
                "instructions": ["Start in plank position", "Lower body", "Push up"],
                "source": "test",
            },
        ],
        "food_items": [
            {
                "fdc_id": 789,
                "description": "Apple, raw",
                "nutrients": [
                    {"name": "Energy", "amount": 52, "unit": "kcal"},
                    {"name": "Protein", "amount": 0.3, "unit": "g"},
                ],
                "source": "test",
            },
        ],
    }

    parser = HealthInfoParser()
    parsed_data = parser.parse_and_validate(test_data)

    print("Parsed data:")
    for category, items in parsed_data.items():
        print(f"  {category}: {len(items)} items")

    stats = parser.get_parsing_stats()
    print(f"\nParsing stats: {stats}")


if __name__ == "__main__":
    main()
