"""
Medical Database Access Layer

Provides database-first access to local medical literature mirrors:
- pubmed_articles
- clinical_trials
- fda_drugs
- health_topics
- food_items
- exercises
- icd10_codes
- billing_codes

This ensures rate limiting issues are avoided by using local data first.
All medical reference data is stored in the PUBLIC database as it contains no PHI.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from core.database.secure_db_manager import DatabaseType, get_db_manager
from core.infrastructure.healthcare_logger import get_healthcare_logger

if TYPE_CHECKING:
    from core.database.secure_db_manager import SecureDatabaseManager

logger = get_healthcare_logger(__name__)


class MedicalDatabaseAccess:
    """Database access layer for medical literature mirrors"""

    def __init__(self):
        """Initialize medical database access."""
        self.logger = logger
        self.db_manager: SecureDatabaseManager | None = (
            None  # Will be initialized on first use
        )

    async def _ensure_db_manager(self) -> "SecureDatabaseManager":
        """Ensure database manager is initialized"""
        if self.db_manager is None:
            self.db_manager = await get_db_manager()
        return self.db_manager

    async def search_pubmed_local(self, query: str, max_results: int = 10) -> list[dict[str, Any]]:
        """Search local PubMed articles database.

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of PubMed articles from local database
        """
        try:
            db_manager = await self._ensure_db_manager()
            self.logger.info(f"🔍 Searching local PubMed database: {query[:50]}...")

            # Use PostgreSQL full-text search
            search_sql = """
                SELECT pmid, title, abstract, authors, journal, pub_date, doi, mesh_terms,
                       ts_rank(search_vector, plainto_tsquery($1)) as rank
                FROM pubmed_articles
                WHERE search_vector @@ plainto_tsquery($2)
                ORDER BY rank DESC, pub_date DESC
                LIMIT $3
            """

            # PubMed articles are in public database (no PHI)
            rows = await db_manager.fetch(
                search_sql,
                query,
                query,
                max_results,
                database=DatabaseType.PUBLIC,
                tables=["pubmed_articles"],
            )

            articles = []
            for row in rows:
                # Handle pub_date - could be datetime object or string
                pub_date = row["pub_date"]
                if pub_date:
                    if hasattr(pub_date, "isoformat"):
                        pub_date_str = pub_date.isoformat()
                    else:
                        pub_date_str = str(pub_date)
                else:
                    pub_date_str = ""

                article = {
                    "pmid": row["pmid"],
                    "title": row["title"] or "",
                    "abstract": row["abstract"] or "",
                    "authors": row["authors"] or [],
                    "journal": row["journal"] or "",
                    "pub_date": pub_date_str,
                    "doi": row["doi"] or "",
                    "mesh_terms": row["mesh_terms"] or [],
                    "rank": float(row["rank"]) if row["rank"] else 0.0,
                    "source": "local_pubmed",
                }
                articles.append(article)

            self.logger.info(f"✅ Found {len(articles)} articles in local PubMed database")
            return articles

        except Exception as e:
            self.logger.exception(f"Local PubMed search error: {e}")
            return []

    async def search_clinical_trials_local(
        self, query: str, max_results: int = 5,
    ) -> list[dict[str, Any]]:
        """Search local clinical trials database.

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of clinical trials from local database
        """
        try:
            db_manager = await self._ensure_db_manager()
            self.logger.info(f"🔍 Searching local clinical trials database: {query[:50]}...")

            # Search clinical trials with text search
            search_sql = """
                SELECT nct_id, title, brief_summary, detailed_description,
                       primary_purpose, phase, enrollment, status, start_date,
                       completion_date, sponsor_name, location_countries,
                       ts_rank(search_vector, plainto_tsquery($1)) as rank
                FROM clinical_trials
                WHERE search_vector @@ plainto_tsquery($2)
                ORDER BY rank DESC, start_date DESC
                LIMIT $3
            """

            rows = await db_manager.fetch(
                search_sql,
                query,
                query,
                max_results,
                database=DatabaseType.PUBLIC,
                tables=["clinical_trials"],
            )

            trials = []
            for row in rows:
                # Handle dates - could be datetime objects or strings
                start_date = row["start_date"]
                if start_date:
                    if hasattr(start_date, "isoformat"):
                        start_date_str = start_date.isoformat()
                    else:
                        start_date_str = str(start_date)
                else:
                    start_date_str = ""

                completion_date = row["completion_date"]
                if completion_date:
                    if hasattr(completion_date, "isoformat"):
                        completion_date_str = completion_date.isoformat()
                    else:
                        completion_date_str = str(completion_date)
                else:
                    completion_date_str = ""

                trial = {
                    "nct_id": row["nct_id"] or "",
                    "title": row["title"] or "",
                    "brief_summary": row["brief_summary"] or "",
                    "detailed_description": row["detailed_description"] or "",
                    "primary_purpose": row["primary_purpose"] or "",
                    "phase": row["phase"] or "",
                    "enrollment": row["enrollment"] or 0,
                    "status": row["status"] or "",
                    "start_date": start_date_str,
                    "completion_date": completion_date_str,
                    "sponsor_name": row["sponsor_name"] or "",
                    "location_countries": row["location_countries"] or [],
                    "rank": float(row["rank"]) if row["rank"] else 0.0,
                    "source": "local_clinical_trials",
                }
                trials.append(trial)

            self.logger.info(f"✅ Found {len(trials)} trials in local clinical trials database")
            return trials

        except Exception as e:
            self.logger.exception(f"Local clinical trials search error: {e}")
            return []

    async def search_fda_drugs_local(
        self, query: str, max_results: int = 5,
    ) -> list[dict[str, Any]]:
        """Search local FDA drugs database.

        Args:
            query: Search query (drug name, indication, etc.)
            max_results: Maximum number of results

        Returns:
            List of FDA drugs from local database
        """
        try:
            db_manager = await self._ensure_db_manager()
            self.logger.info(f"🔍 Searching local FDA drugs database: {query[:50]}...")

            # Search FDA drugs with new unified schema
            search_sql = """
                SELECT ndc, name, generic_name, brand_name, manufacturer,
                       ingredients, dosage_form, route, strength,
                       approval_date, application_number, therapeutic_class,
                       orange_book_code, reference_listed_drug, data_sources,
                       ts_rank(search_vector, plainto_tsquery($1)) as rank
                FROM fda_drugs
                WHERE search_vector @@ plainto_tsquery($2)
                ORDER BY
                    rank DESC,
                    approval_date DESC NULLS LAST
                LIMIT $3
            """

            rows = await db_manager.fetch(
                search_sql,
                query,
                query,
                max_results,
                database=DatabaseType.PUBLIC,
                tables=["fda_drugs"],
            )

            drugs = []
            for row in rows:
                drug = {
                    "ndc": row["ndc"] or "",
                    "name": row["name"] or "",
                    "generic_name": row["generic_name"] or "",
                    "brand_name": row["brand_name"] or "",
                    "manufacturer": row["manufacturer"] or "",
                    "ingredients": row["ingredients"] or [],
                    "dosage_form": row["dosage_form"] or "",
                    "route": row["route"] or "",
                    "strength": row["strength"] or "",
                    "approval_date": row["approval_date"] or "",
                    "application_number": row["application_number"] or "",
                    "therapeutic_class": row["therapeutic_class"] or "",
                    "orange_book_code": row["orange_book_code"] or "",
                    "reference_listed_drug": row["reference_listed_drug"] or "",
                    "data_sources": row["data_sources"] or [],
                    "rank": float(row["rank"]) if row["rank"] else 0.0,
                    "source": "local_fda_drugs",
                }
                drugs.append(drug)

            self.logger.info(f"✅ Found {len(drugs)} drugs in local FDA drugs database")
            return drugs

        except Exception as e:
            self.logger.exception(f"Local FDA drugs search error: {e}")
            return []

    async def search_health_topics_local(
        self, query: str, max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """Search local health topics database.

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of health topics from local database
        """
        try:
            db_manager = await self._ensure_db_manager()
            self.logger.info(f"🔍 Searching local health topics database: {query[:50]}...")

            # Search health topics with actual schema
            search_sql = """
                SELECT topic_id, title, summary, category, url,
                       last_reviewed, audience, sections, related_topics,
                       keywords, content_length,
                       ts_rank(search_vector, plainto_tsquery($1)) as rank
                FROM health_topics
                WHERE search_vector @@ plainto_tsquery($2)
                ORDER BY rank DESC
                LIMIT $3
            """

            rows = await db_manager.fetch(
                search_sql,
                query,
                query,
                max_results,
                database=DatabaseType.PUBLIC,
                tables=["health_topics"],
            )

            topics = []
            for row in rows:
                # Extract sections for common health info
                sections = row["sections"] or {}

                topic = {
                    "topic_id": row["topic_id"] or "",
                    "title": row["title"] or "",
                    "summary": row["summary"] or "",
                    "category": row["category"] or "",
                    "url": row["url"] or "",
                    "last_reviewed": row["last_reviewed"] or "",
                    "audience": row["audience"] or {},
                    "sections": sections,
                    # Extract common sections if available
                    "symptoms": sections.get("symptoms", []),
                    "causes": sections.get("causes", []),
                    "treatments": sections.get("treatments", []),
                    "prevention": sections.get("prevention", []),
                    "related_topics": row["related_topics"] or [],
                    "keywords": row["keywords"] or [],
                    "content_length": row["content_length"] or 0,
                    "rank": float(row["rank"]) if row["rank"] else 0.0,
                    "source": "local_health_topics",
                }
                topics.append(topic)

            self.logger.info(f"✅ Found {len(topics)} topics in local health topics database")
            return topics

        except Exception as e:
            self.logger.exception(f"Local health topics search error: {e}")
            return []

    async def search_food_items_local(
        self, query: str, max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """Search local food items database.

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of food items from local database
        """
        try:
            db_manager = await self._ensure_db_manager()
            self.logger.info(f"🔍 Searching local food items database: {query[:50]}...")

            # Search food items with JSONB fields
            search_sql = """
                SELECT fdc_id, description, scientific_name, common_names,
                       brand_owner, ingredients, serving_size, serving_size_unit,
                       nutrients, nutrition_summary, food_category,
                       allergens, dietary_flags,
                       ts_rank(search_vector, plainto_tsquery($1)) as rank
                FROM food_items
                WHERE search_vector @@ plainto_tsquery($2)
                ORDER BY rank DESC
                LIMIT $3
            """

            rows = await db_manager.fetch(
                search_sql,
                query,
                query,
                max_results,
                database=DatabaseType.PUBLIC,
                tables=["food_items"],
            )

            foods = []
            for row in rows:
                # Extract nutrition from JSONB
                nutrition_summary = row["nutrition_summary"] or {}
                nutrients = row["nutrients"] or {}

                food = {
                    "fdc_id": row["fdc_id"] or "",
                    "description": row["description"] or "",
                    "scientific_name": row["scientific_name"] or "",
                    "common_names": row["common_names"] or "",
                    "brand_owner": row["brand_owner"] or "",
                    "ingredients": row["ingredients"] or "",
                    "serving_size": float(row["serving_size"]) if row["serving_size"] else 0,
                    "serving_size_unit": row["serving_size_unit"] or "",
                    "nutrients": nutrients,
                    "nutrition_summary": nutrition_summary,
                    # Extract common nutrition values from summary
                    "calories": nutrition_summary.get("calories", 0),
                    "protein": nutrition_summary.get("protein", 0),
                    "fat": nutrition_summary.get("fat", 0),
                    "carbohydrates": nutrition_summary.get("carbohydrates", 0),
                    "fiber": nutrition_summary.get("fiber", 0),
                    "sugar": nutrition_summary.get("sugar", 0),
                    "sodium": nutrition_summary.get("sodium", 0),
                    "food_category": row["food_category"] or "",
                    "allergens": row["allergens"] or {},
                    "dietary_flags": row["dietary_flags"] or {},
                    "rank": float(row["rank"]) if row["rank"] else 0.0,
                    "source": "local_food_items",
                }
                foods.append(food)

            self.logger.info(f"✅ Found {len(foods)} items in local food items database")
            return foods

        except Exception as e:
            self.logger.exception(f"Local food items search error: {e}")
            return []

    async def search_exercises_local(
        self,
        query: str,
        body_part: str | None = None,
        equipment: str | None = None,
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """Search local exercises database.

        Args:
            query: Search query
            body_part: Filter by body part (optional)
            equipment: Filter by equipment (optional)
            max_results: Maximum number of results

        Returns:
            List of exercises from local database
        """
        try:
            db_manager = await self._ensure_db_manager()
            self.logger.info(f"🔍 Searching local exercises database: {query[:50]}...")

            # Build search query with optional filters
            search_conditions = ["search_vector @@ plainto_tsquery($1)"]
            params = [query]
            param_count = 1

            if body_part:
                param_count += 1
                search_conditions.append(f"body_part = ${param_count}")
                params.append(body_part)

            if equipment:
                param_count += 1
                search_conditions.append(f"equipment = ${param_count}")
                params.append(equipment)

            param_count += 1
            params.append(str(max_results))

            # Search exercises with actual schema
            search_sql = f"""
                SELECT exercise_id, name, body_part, equipment, gif_url,
                       instructions, secondary_muscles, target,
                       difficulty_level, exercise_type, duration_estimate,
                       calories_estimate,
                       ts_rank(search_vector, plainto_tsquery($1)) as rank
                FROM exercises
                WHERE {" AND ".join(search_conditions)}
                ORDER BY rank DESC
                LIMIT ${param_count}
            """

            rows = await db_manager.fetch(
                search_sql, *params, database=DatabaseType.PUBLIC, tables=["exercises"],
            )

            exercises = []
            for row in rows:
                exercise = {
                    "exercise_id": row["exercise_id"] or "",
                    "name": row["name"] or "",
                    "body_part": row["body_part"] or "",
                    "equipment": row["equipment"] or "",
                    "gif_url": row["gif_url"] or "",
                    "instructions": row["instructions"] or [],
                    "secondary_muscles": row["secondary_muscles"] or [],
                    "target": row["target"] or "",
                    "difficulty_level": row["difficulty_level"] or "",
                    "exercise_type": row["exercise_type"] or "",
                    "duration_estimate": row["duration_estimate"] or "",
                    "calories_estimate": row["calories_estimate"] or "",
                    "rank": float(row["rank"]) if row["rank"] else 0.0,
                    "source": "local_exercises",
                }
                exercises.append(exercise)

            self.logger.info(f"✅ Found {len(exercises)} exercises in local exercises database")
            return exercises

        except Exception as e:
            self.logger.exception(f"Local exercises search error: {e}")
            return []

    async def search_icd10_codes_local(
        self, query: str, exact_match: bool = False, max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """Search local ICD-10 codes database.

        Args:
            query: Search query (code or description)
            exact_match: Whether to search for exact code match
            max_results: Maximum number of results

        Returns:
            List of ICD-10 codes from local database
        """
        try:
            db_manager = await self._ensure_db_manager()
            self.logger.info(f"🔍 Searching local ICD-10 codes database: {query[:50]}...")

            if exact_match:
                # Exact code match
                search_sql = """
                    SELECT code, description, category, chapter, parent_code,
                           billable, source, code_length
                    FROM icd10_codes
                    WHERE code = $1
                    LIMIT 1
                """
                rows = await db_manager.fetch(
                    search_sql, query.upper(), database=DatabaseType.PUBLIC, tables=["icd10_codes"],
                )
            else:
                # Full-text search
                search_sql = """
                    SELECT code, description, category, chapter, parent_code,
                           billable, source, code_length,
                           ts_rank(search_vector, plainto_tsquery($1)) as rank
                    FROM icd10_codes
                    WHERE search_vector @@ plainto_tsquery($2)
                    ORDER BY rank DESC, code_length ASC
                    LIMIT $3
                """
                rows = await db_manager.fetch(
                    search_sql,
                    query,
                    query,
                    max_results,
                    database=DatabaseType.PUBLIC,
                    tables=["icd10_codes"],
                )

            codes = []
            for row in rows:
                code = {
                    "code": row["code"] or "",
                    "description": row["description"] or "",
                    "category": row["category"] or "",
                    "chapter": row["chapter"] or "",
                    "parent_code": row["parent_code"] or "",
                    "billable": row["billable"] if row["billable"] is not None else False,
                    "source": row["source"] or "",
                    "code_length": row["code_length"] or 0,
                }
                if not exact_match and "rank" in row:
                    code["rank"] = float(row["rank"]) if row["rank"] else 0.0
                code["source_type"] = "local_icd10"
                codes.append(code)

            self.logger.info(f"✅ Found {len(codes)} codes in local ICD-10 database")
            return codes

        except Exception as e:
            self.logger.exception(f"Local ICD-10 codes search error: {e}")
            return []

    async def search_billing_codes_local(
        self, query: str, code_type: str | None = None, max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """Search local billing codes database.

        Args:
            query: Search query (code or description)
            code_type: Filter by code type (CPT, HCPCS, etc.)
            max_results: Maximum number of results

        Returns:
            List of billing codes from local database
        """
        try:
            db_manager = await self._ensure_db_manager()
            self.logger.info(f"🔍 Searching local billing codes database: {query[:50]}...")

            # Build search query with optional code type filter
            search_conditions = ["search_vector @@ plainto_tsquery($1)"]
            params = [query]
            param_count = 1

            if code_type:
                param_count += 1
                search_conditions.append(f"code_type = ${param_count}")
                params.append(code_type.upper())

            param_count += 1
            params.append(str(max_results))

            # Search billing codes with actual schema
            search_sql = f"""
                SELECT code, code_type, short_description, long_description,
                       category, is_active, effective_date, termination_date,
                       coverage_notes, gender_specific, age_specific,
                       ts_rank(search_vector, plainto_tsquery($1)) as rank
                FROM billing_codes
                WHERE {" AND ".join(search_conditions)}
                ORDER BY rank DESC
                LIMIT ${param_count}
            """

            rows = await db_manager.fetch(
                search_sql, *params, database=DatabaseType.PUBLIC, tables=["billing_codes"],
            )

            codes = []
            for row in rows:
                # Handle date fields
                effective_date = row["effective_date"]
                if effective_date:
                    if hasattr(effective_date, "isoformat"):
                        effective_date_str = effective_date.isoformat()
                    else:
                        effective_date_str = str(effective_date)
                else:
                    effective_date_str = ""

                termination_date = row["termination_date"]
                if termination_date:
                    if hasattr(termination_date, "isoformat"):
                        termination_date_str = termination_date.isoformat()
                    else:
                        termination_date_str = str(termination_date)
                else:
                    termination_date_str = ""

                code = {
                    "code": row["code"] or "",
                    "code_type": row["code_type"] or "",
                    "short_description": row["short_description"] or "",
                    "long_description": row["long_description"] or "",
                    "category": row["category"] or "",
                    "is_active": row["is_active"] if row["is_active"] is not None else True,
                    "effective_date": effective_date_str,
                    "termination_date": termination_date_str,
                    "coverage_notes": row["coverage_notes"] or "",
                    "gender_specific": row["gender_specific"] or "",
                    "age_specific": row["age_specific"] or "",
                    "rank": float(row["rank"]) if row["rank"] else 0.0,
                    "source": "local_billing_codes",
                }
                codes.append(code)

            self.logger.info(f"✅ Found {len(codes)} codes in local billing codes database")
            return codes

        except Exception as e:
            self.logger.exception(f"Local billing codes search error: {e}")
            return []

    async def get_database_status(self) -> dict[str, Any]:
        """Get status of medical database tables.

        Returns:
            Dictionary with table counts and status
        """
        try:
            db_manager = await self._ensure_db_manager()

            # Get counts for all medical mirror tables
            status = {}
            tables = [
                "pubmed_articles",
                "clinical_trials",
                "fda_drugs",
                "health_topics",
                "food_items",
                "exercises",
                "icd10_codes",
                "billing_codes",
                "update_logs",
            ]

            for table in tables:
                try:
                    count_sql = f"SELECT COUNT(*) as count FROM {table}"
                    count = await db_manager.fetchval(
                        count_sql, database=DatabaseType.PUBLIC, tables=[table],
                    )
                    status[table] = {"count": count, "available": True}
                except Exception as e:
                    status[table] = {"count": 0, "available": False, "error": str(e)}

            # Get last update times
            try:
                update_sql = """
                    SELECT source, MAX(completed_at) as last_update
                    FROM update_logs
                    WHERE status = 'success'
                    GROUP BY source
                """
                update_rows = await db_manager.fetch(
                    update_sql, database=DatabaseType.PUBLIC, tables=["update_logs"],
                )
                update_times = {
                    row["source"]: row["last_update"].isoformat() if row["last_update"] else None
                    for row in update_rows
                }
            except:
                update_times = {}

            return {
                "database_available": True,
                "tables": status,
                "last_updates": update_times,
                "last_checked": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.exception(f"Database status check error: {e}")
            return {
                "database_available": False,
                "error": str(e),
                "last_checked": datetime.now().isoformat(),
            }


# Global instance for easy access
_medical_db = None


async def get_medical_db() -> MedicalDatabaseAccess:
    """Get global medical database access instance."""
    global _medical_db
    if _medical_db is None:
        _medical_db = MedicalDatabaseAccess()
    return _medical_db
