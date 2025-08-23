"""
Health information API endpoints for medical mirrors service
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import HTTPException, Query
from sqlalchemy import and_, desc, func, or_, text
from sqlalchemy.orm import Session

from database import get_db_session

logger = logging.getLogger(__name__)


class HealthInfoAPI:
    """API for health information (topics, exercises, nutrition) search and lookup"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def search_health_topics(
        self,
        query: str,
        category: Optional[str] = None,
        audience: Optional[str] = None,
        max_results: int = 10
    ) -> Dict:
        """Search health topics from MyHealthfinder"""
        try:
            with get_db_session() as db:
                base_query = """
                    SELECT topic_id, title, category, url, last_reviewed,
                           audience, summary, keywords, content_length,
                           last_updated,
                           ts_rank(search_vector, plainto_tsquery(:query)) as rank
                    FROM health_topics
                    WHERE search_vector @@ plainto_tsquery(:query)
                """
                
                conditions = []
                params = {"query": query, "max_results": min(max_results, 50)}
                
                if category:
                    conditions.append("UPPER(category) = UPPER(:category)")
                    params["category"] = category
                
                if audience:
                    conditions.append("UPPER(:audience) = ANY(UPPER(audience::text)::text[])")
                    params["audience"] = audience
                
                where_clause = ""
                if conditions:
                    where_clause = "AND " + " AND ".join(conditions)
                
                final_query = f"""
                    {base_query}
                    {where_clause}
                    ORDER BY rank DESC, title
                    LIMIT :max_results
                """
                
                result = db.execute(text(final_query), params)
                rows = result.fetchall()
                
                topics = []
                for row in rows:
                    topic = {
                        "topic_id": row.topic_id,
                        "title": row.title,
                        "category": row.category or "",
                        "url": row.url or "",
                        "last_reviewed": row.last_reviewed,
                        "audience": row.audience or [],
                        "summary": row.summary or "",
                        "keywords": row.keywords or [],
                        "content_length": row.content_length or 0,
                        "last_updated": row.last_updated.isoformat() if row.last_updated else None,
                        "relevance_score": float(row.rank) if row.rank else 0.0,
                        "item_type": "health_topic"
                    }
                    topics.append(topic)
                
                return {
                    "topics": topics,
                    "total_results": len(topics),
                    "search_query": query,
                    "filters": {
                        "category": category,
                        "audience": audience
                    },
                    "timestamp": datetime.now().isoformat()
                }
        
        except Exception as e:
            logger.error(f"Error searching health topics: {e}")
            raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")
    
    async def search_exercises(
        self,
        query: str,
        body_part: Optional[str] = None,
        equipment: Optional[str] = None,
        difficulty: Optional[str] = None,
        max_results: int = 10
    ) -> Dict:
        """Search exercises from ExerciseDB"""
        try:
            with get_db_session() as db:
                base_query = """
                    SELECT exercise_id, name, body_part, equipment, target,
                           secondary_muscles, difficulty_level, exercise_type,
                           duration_estimate, calories_estimate, gif_url,
                           last_updated,
                           ts_rank(search_vector, plainto_tsquery(:query)) as rank
                    FROM exercises
                    WHERE search_vector @@ plainto_tsquery(:query)
                """
                
                conditions = []
                params = {"query": query, "max_results": min(max_results, 50)}
                
                if body_part:
                    conditions.append("UPPER(body_part) = UPPER(:body_part)")
                    params["body_part"] = body_part
                
                if equipment:
                    conditions.append("UPPER(equipment) = UPPER(:equipment)")
                    params["equipment"] = equipment
                
                if difficulty:
                    conditions.append("UPPER(difficulty_level) = UPPER(:difficulty)")
                    params["difficulty"] = difficulty
                
                where_clause = ""
                if conditions:
                    where_clause = "AND " + " AND ".join(conditions)
                
                final_query = f"""
                    {base_query}
                    {where_clause}
                    ORDER BY rank DESC, name
                    LIMIT :max_results
                """
                
                result = db.execute(text(final_query), params)
                rows = result.fetchall()
                
                exercises = []
                for row in rows:
                    exercise = {
                        "exercise_id": row.exercise_id,
                        "name": row.name,
                        "body_part": row.body_part or "",
                        "equipment": row.equipment or "",
                        "target": row.target or "",
                        "secondary_muscles": row.secondary_muscles or [],
                        "difficulty_level": row.difficulty_level or "",
                        "exercise_type": row.exercise_type or "",
                        "duration_estimate": row.duration_estimate or "",
                        "calories_estimate": row.calories_estimate or "",
                        "gif_url": row.gif_url or "",
                        "last_updated": row.last_updated.isoformat() if row.last_updated else None,
                        "relevance_score": float(row.rank) if row.rank else 0.0,
                        "item_type": "exercise"
                    }
                    exercises.append(exercise)
                
                return {
                    "exercises": exercises,
                    "total_results": len(exercises),
                    "search_query": query,
                    "filters": {
                        "body_part": body_part,
                        "equipment": equipment,
                        "difficulty": difficulty
                    },
                    "timestamp": datetime.now().isoformat()
                }
        
        except Exception as e:
            logger.error(f"Error searching exercises: {e}")
            raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")
    
    async def search_foods(
        self,
        query: str,
        food_category: Optional[str] = None,
        dietary_flags: Optional[str] = None,
        max_results: int = 10
    ) -> Dict:
        """Search food items from USDA FoodData Central"""
        try:
            with get_db_session() as db:
                base_query = """
                    SELECT fdc_id, description, food_category, nutrition_summary,
                           allergens, dietary_flags, nutritional_density,
                           serving_size, serving_size_unit, brand_owner,
                           last_updated,
                           ts_rank(search_vector, plainto_tsquery(:query)) as rank
                    FROM food_items
                    WHERE search_vector @@ plainto_tsquery(:query)
                """
                
                conditions = []
                params = {"query": query, "max_results": min(max_results, 50)}
                
                if food_category:
                    conditions.append("UPPER(food_category) LIKE UPPER(:food_category)")
                    params["food_category"] = f"%{food_category}%"
                
                if dietary_flags:
                    conditions.append("UPPER(:dietary_flags) = ANY(UPPER(dietary_flags::text)::text[])")
                    params["dietary_flags"] = dietary_flags
                
                where_clause = ""
                if conditions:
                    where_clause = "AND " + " AND ".join(conditions)
                
                final_query = f"""
                    {base_query}
                    {where_clause}
                    ORDER BY rank DESC, description
                    LIMIT :max_results
                """
                
                result = db.execute(text(final_query), params)
                rows = result.fetchall()
                
                foods = []
                for row in rows:
                    food = {
                        "fdc_id": row.fdc_id,
                        "description": row.description,
                        "food_category": row.food_category or "",
                        "nutrition_summary": row.nutrition_summary or {},
                        "allergens": row.allergens or [],
                        "dietary_flags": row.dietary_flags or [],
                        "nutritional_density": row.nutritional_density or 0,
                        "serving_size": row.serving_size,
                        "serving_size_unit": row.serving_size_unit or "",
                        "brand_owner": row.brand_owner or "",
                        "last_updated": row.last_updated.isoformat() if row.last_updated else None,
                        "relevance_score": float(row.rank) if row.rank else 0.0,
                        "item_type": "food_item"
                    }
                    foods.append(food)
                
                return {
                    "foods": foods,
                    "total_results": len(foods),
                    "search_query": query,
                    "filters": {
                        "food_category": food_category,
                        "dietary_flags": dietary_flags
                    },
                    "timestamp": datetime.now().isoformat()
                }
        
        except Exception as e:
            logger.error(f"Error searching foods: {e}")
            raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")
    
    async def get_health_topic_details(self, topic_id: str) -> Dict:
        """Get detailed information for a specific health topic"""
        try:
            with get_db_session() as db:
                result = db.execute(text("""
                    SELECT topic_id, title, category, url, last_reviewed,
                           audience, sections, related_topics, summary,
                           keywords, content_length, last_updated, source
                    FROM health_topics
                    WHERE topic_id = :topic_id
                """), {"topic_id": topic_id})
                
                row = result.fetchone()
                
                if not row:
                    raise HTTPException(status_code=404, detail=f"Health topic '{topic_id}' not found")
                
                topic_details = {
                    "topic_id": row.topic_id,
                    "title": row.title,
                    "category": row.category or "",
                    "url": row.url or "",
                    "last_reviewed": row.last_reviewed,
                    "audience": row.audience or [],
                    "sections": row.sections or [],
                    "related_topics": row.related_topics or [],
                    "summary": row.summary or "",
                    "keywords": row.keywords or [],
                    "content_length": row.content_length or 0,
                    "last_updated": row.last_updated.isoformat() if row.last_updated else None,
                    "source": row.source or "myhealthfinder"
                }
                
                return topic_details
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting health topic details for '{topic_id}': {e}")
            raise HTTPException(status_code=500, detail=f"Lookup error: {str(e)}")
    
    async def get_exercise_details(self, exercise_id: str) -> Dict:
        """Get detailed information for a specific exercise"""
        try:
            with get_db_session() as db:
                result = db.execute(text("""
                    SELECT exercise_id, name, body_part, equipment, target,
                           secondary_muscles, instructions, difficulty_level,
                           exercise_type, duration_estimate, calories_estimate,
                           gif_url, last_updated, source
                    FROM exercises
                    WHERE exercise_id = :exercise_id
                """), {"exercise_id": exercise_id})
                
                row = result.fetchone()
                
                if not row:
                    raise HTTPException(status_code=404, detail=f"Exercise '{exercise_id}' not found")
                
                exercise_details = {
                    "exercise_id": row.exercise_id,
                    "name": row.name,
                    "body_part": row.body_part or "",
                    "equipment": row.equipment or "",
                    "target": row.target or "",
                    "secondary_muscles": row.secondary_muscles or [],
                    "instructions": row.instructions or [],
                    "difficulty_level": row.difficulty_level or "",
                    "exercise_type": row.exercise_type or "",
                    "duration_estimate": row.duration_estimate or "",
                    "calories_estimate": row.calories_estimate or "",
                    "gif_url": row.gif_url or "",
                    "last_updated": row.last_updated.isoformat() if row.last_updated else None,
                    "source": row.source or "exercisedb"
                }
                
                return exercise_details
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting exercise details for '{exercise_id}': {e}")
            raise HTTPException(status_code=500, detail=f"Lookup error: {str(e)}")
    
    async def get_food_details(self, fdc_id: int) -> Dict:
        """Get detailed information for a specific food item"""
        try:
            with get_db_session() as db:
                result = db.execute(text("""
                    SELECT fdc_id, description, scientific_name, common_names,
                           food_category, nutrients, nutrition_summary,
                           brand_owner, ingredients, serving_size, serving_size_unit,
                           allergens, dietary_flags, nutritional_density,
                           last_updated, source
                    FROM food_items
                    WHERE fdc_id = :fdc_id
                """), {"fdc_id": fdc_id})
                
                row = result.fetchone()
                
                if not row:
                    raise HTTPException(status_code=404, detail=f"Food item '{fdc_id}' not found")
                
                food_details = {
                    "fdc_id": row.fdc_id,
                    "description": row.description,
                    "scientific_name": row.scientific_name or "",
                    "common_names": row.common_names or "",
                    "food_category": row.food_category or "",
                    "nutrients": row.nutrients or [],
                    "nutrition_summary": row.nutrition_summary or {},
                    "brand_owner": row.brand_owner or "",
                    "ingredients": row.ingredients or "",
                    "serving_size": row.serving_size,
                    "serving_size_unit": row.serving_size_unit or "",
                    "allergens": row.allergens or [],
                    "dietary_flags": row.dietary_flags or [],
                    "nutritional_density": row.nutritional_density or 0,
                    "last_updated": row.last_updated.isoformat() if row.last_updated else None,
                    "source": row.source or "usda_fooddata"
                }
                
                return food_details
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting food details for '{fdc_id}': {e}")
            raise HTTPException(status_code=500, detail=f"Lookup error: {str(e)}")
    
    async def get_stats(self) -> Dict:
        """Get health information database statistics"""
        try:
            with get_db_session() as db:
                # Health topics stats
                topics_stats = db.execute(text("""
                    SELECT COUNT(*) as total_topics,
                           COUNT(DISTINCT category) as total_categories
                    FROM health_topics
                """)).fetchone()
                
                # Exercises stats
                exercises_stats = db.execute(text("""
                    SELECT COUNT(*) as total_exercises,
                           COUNT(DISTINCT body_part) as body_parts,
                           COUNT(DISTINCT equipment) as equipment_types
                    FROM exercises
                """)).fetchone()
                
                # Food items stats
                foods_stats = db.execute(text("""
                    SELECT COUNT(*) as total_foods,
                           COUNT(DISTINCT food_category) as food_categories
                    FROM food_items
                """)).fetchone()
                
                return {
                    "health_topics": {
                        "total_topics": topics_stats.total_topics if topics_stats else 0,
                        "total_categories": topics_stats.total_categories if topics_stats else 0
                    },
                    "exercises": {
                        "total_exercises": exercises_stats.total_exercises if exercises_stats else 0,
                        "body_parts": exercises_stats.body_parts if exercises_stats else 0,
                        "equipment_types": exercises_stats.equipment_types if exercises_stats else 0
                    },
                    "food_items": {
                        "total_foods": foods_stats.total_foods if foods_stats else 0,
                        "food_categories": foods_stats.food_categories if foods_stats else 0
                    },
                    "data_sources": ["myhealthfinder", "exercisedb", "usda_fooddata"],
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting health info stats: {e}")
            raise HTTPException(status_code=500, detail=f"Stats error: {str(e)}")


# FastAPI route handlers
health_info_api = HealthInfoAPI()

async def search_health_topics(
    query: str = Query(..., description="Search term"),
    category: Optional[str] = Query(None, description="Filter by category"),
    audience: Optional[str] = Query(None, description="Filter by audience"),
    max_results: int = Query(10, ge=1, le=50, description="Maximum results to return")
):
    """Search health topics"""
    return await health_info_api.search_health_topics(query, category, audience, max_results)

async def search_exercises(
    query: str = Query(..., description="Search term"),
    body_part: Optional[str] = Query(None, description="Filter by body part"),
    equipment: Optional[str] = Query(None, description="Filter by equipment"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty"),
    max_results: int = Query(10, ge=1, le=50, description="Maximum results to return")
):
    """Search exercises"""
    return await health_info_api.search_exercises(query, body_part, equipment, difficulty, max_results)

async def search_foods(
    query: str = Query(..., description="Search term"),
    food_category: Optional[str] = Query(None, description="Filter by food category"),
    dietary_flags: Optional[str] = Query(None, description="Filter by dietary flags"),
    max_results: int = Query(10, ge=1, le=50, description="Maximum results to return")
):
    """Search food items"""
    return await health_info_api.search_foods(query, food_category, dietary_flags, max_results)

async def get_health_topic_details(topic_id: str):
    """Get detailed information for a health topic"""
    return await health_info_api.get_health_topic_details(topic_id)

async def get_exercise_details(exercise_id: str):
    """Get detailed information for an exercise"""
    return await health_info_api.get_exercise_details(exercise_id)

async def get_food_details(fdc_id: int):
    """Get detailed information for a food item"""
    return await health_info_api.get_food_details(fdc_id)

async def get_health_info_stats():
    """Get health information database statistics"""
    return await health_info_api.get_stats()