"""
ICD-10 codes API endpoints for medical mirrors service
"""

import logging
from datetime import datetime

from fastapi import HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db_session

logger = logging.getLogger(__name__)


class ICD10API:
    """API for ICD-10 diagnostic codes search and lookup"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def search_codes(
        self,
        query: str,
        max_results: int = 10,
        exact_match: bool = False,
        category: str | None = None,
        billable_only: bool = False,
    ) -> dict:
        """Search ICD-10 codes"""
        try:
            # Validate query parameter
            if not query or not query.strip():
                return {
                    "codes": [],
                    "total_results": 0,
                    "search_query": query,
                    "search_type": "exact_match" if exact_match else "full_text_search",
                    "timestamp": datetime.now().isoformat(),
                    "error": "Search query cannot be empty",
                }

            with get_db_session() as db:
                # Apply filters
                conditions = []
                params = {
                    "query": query.strip(),
                    "exact_match": exact_match,
                }

                if category:
                    conditions.append("UPPER(category) = UPPER(:category)")
                    params["category"] = category

                if billable_only:
                    conditions.append("is_billable = true")

                # Build final query
                where_clause = ""
                if conditions:
                    where_clause = "AND " + " AND ".join(conditions)

                final_query = f"""
                    SELECT code, description, category, chapter, synonyms,
                           inclusion_notes, exclusion_notes, is_billable,
                           parent_code, last_updated,
                           CASE WHEN :exact_match = true THEN 1.0
                                ELSE ts_rank(search_vector, plainto_tsquery(:query))
                           END as rank
                    FROM icd10_codes
                    WHERE ((:exact_match = false AND search_vector @@ plainto_tsquery(:query))
                           OR (:exact_match = true AND UPPER(code) = UPPER(:query)))
                    {where_clause}
                    ORDER BY rank DESC, code
                    LIMIT :max_results
                """

                params["max_results"] = min(max_results, 100)

                result = db.execute(text(final_query), params)
                rows = result.fetchall()

                codes = []
                for row in rows:
                    code_dict = {
                        "code": row.code,
                        "description": row.description,
                        "category": row.category or "",
                        "chapter": row.chapter or "",
                        "synonyms": row.synonyms or [],
                        "inclusion_notes": row.inclusion_notes or [],
                        "exclusion_notes": row.exclusion_notes or [],
                        "is_billable": bool(row.is_billable),
                        "parent_code": row.parent_code,
                        "last_updated": row.last_updated.isoformat() if row.last_updated else None,
                        "relevance_score": float(row.rank) if row.rank else 0.0,
                    }
                    codes.append(code_dict)

                return {
                    "codes": codes,
                    "total_results": len(codes),
                    "search_query": query,
                    "search_type": "exact_match" if exact_match else "full_text_search",
                    "timestamp": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.exception(f"Error searching ICD-10 codes: {e}")
            raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

    async def get_code_details(self, code: str) -> dict:
        """Get detailed information for a specific ICD-10 code"""
        try:
            with get_db_session() as db:
                result = db.execute(text("""
                    SELECT code, description, category, chapter, synonyms,
                           inclusion_notes, exclusion_notes, is_billable,
                           parent_code, children_codes, search_text, last_updated
                    FROM icd10_codes
                    WHERE UPPER(code) = UPPER(:code)
                """), {"code": code})

                row = result.fetchone()

                if not row:
                    raise HTTPException(status_code=404, detail=f"ICD-10 code '{code}' not found")

                # Get related codes (parent and children)
                related_codes = await self._get_related_codes(db, code, row.parent_code, row.children_codes)

                return {
                    "code": row.code,
                    "description": row.description,
                    "category": row.category or "",
                    "chapter": row.chapter or "",
                    "synonyms": row.synonyms or [],
                    "inclusion_notes": row.inclusion_notes or [],
                    "exclusion_notes": row.exclusion_notes or [],
                    "is_billable": bool(row.is_billable),
                    "parent_code": row.parent_code,
                    "children_codes": row.children_codes or [],
                    "related_codes": related_codes,
                    "clinical_guidance": self._generate_clinical_guidance(row),
                    "billing_guidance": self._generate_billing_guidance(row),
                    "last_updated": row.last_updated.isoformat() if row.last_updated else None,
                    "source": "nlm_clinical_tables",
                }


        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Error getting code details for '{code}': {e}")
            raise HTTPException(status_code=500, detail=f"Lookup error: {str(e)}")

    async def _get_related_codes(
        self,
        db: Session,
        code: str,
        parent_code: str | None,
        children_codes: list[str] | None,
    ) -> dict:
        """Get related codes (parent, children, siblings)"""
        related = {
            "parent": None,
            "children": [],
            "siblings": [],
        }

        try:
            # Get parent details
            if parent_code:
                parent_result = db.execute(text("""
                    SELECT code, description FROM icd10_codes
                    WHERE code = :parent_code
                """), {"parent_code": parent_code})

                parent_row = parent_result.fetchone()
                if parent_row:
                    related["parent"] = {
                        "code": parent_row.code,
                        "description": parent_row.description,
                    }

            # Get children details
            if children_codes:
                for child_code in children_codes[:10]:  # Limit to 10 children
                    child_result = db.execute(text("""
                        SELECT code, description FROM icd10_codes
                        WHERE code = :child_code
                    """), {"child_code": child_code})

                    child_row = child_result.fetchone()
                    if child_row:
                        related["children"].append({
                            "code": child_row.code,
                            "description": child_row.description,
                        })

            # Get siblings (other codes with same parent)
            if parent_code:
                sibling_result = db.execute(text("""
                    SELECT code, description FROM icd10_codes
                    WHERE parent_code = :parent_code AND code != :code
                    LIMIT 5
                """), {"parent_code": parent_code, "code": code})

                for sibling_row in sibling_result.fetchall():
                    related["siblings"].append({
                        "code": sibling_row.code,
                        "description": sibling_row.description,
                    })

        except Exception as e:
            logger.exception(f"Error getting related codes: {e}")

        return related

    def _generate_clinical_guidance(self, code_data) -> str:
        """Generate clinical usage guidance"""
        guidance_parts = []

        # Basic usage
        guidance_parts.append(f"Use this code for: {code_data.description}")

        # Inclusion notes
        if code_data.inclusion_notes:
            guidance_parts.append("Includes: " + "; ".join(code_data.inclusion_notes))

        # Exclusion notes
        if code_data.exclusion_notes:
            guidance_parts.append("Excludes: " + "; ".join(code_data.exclusion_notes))

        # Hierarchical guidance
        if code_data.parent_code:
            guidance_parts.append(f"This is a specific type of {code_data.parent_code}")

        return " | ".join(guidance_parts)

    def _generate_billing_guidance(self, code_data) -> str:
        """Generate billing and reimbursement guidance"""
        guidance_parts = []

        # Billability
        if code_data.is_billable:
            guidance_parts.append("This code is billable for reimbursement")
        else:
            guidance_parts.append("This code is typically not billable - it may be a category header")

        # Specificity
        code_length = len(code_data.code.replace(".", ""))
        if code_length < 4:
            guidance_parts.append("Consider using a more specific code for billing")
        elif code_length >= 5:
            guidance_parts.append("This code provides high specificity for accurate billing")

        # Additional guidance based on chapter
        chapter_guidance = {
            "S": "Injury codes - consider using 7th character for encounter type",
            "T": "Injury/poisoning codes - may require additional codes for cause",
            "Z": "Z-codes are for encounters, not primary diagnoses",
        }

        if code_data.chapter in chapter_guidance:
            guidance_parts.append(chapter_guidance[code_data.chapter])

        return " | ".join(guidance_parts)

    async def get_categories(self) -> dict:
        """Get all ICD-10 categories/chapters"""
        try:
            with get_db_session() as db:
                result = db.execute(text("""
                    SELECT DISTINCT chapter, category, COUNT(*) as code_count
                    FROM icd10_codes
                    WHERE chapter IS NOT NULL AND category IS NOT NULL
                    GROUP BY chapter, category
                    ORDER BY chapter
                """))

                categories = []
                for row in result.fetchall():
                    categories.append({
                        "chapter": row.chapter,
                        "category": row.category,
                        "code_count": row.code_count,
                    })

                return {
                    "categories": categories,
                    "total_categories": len(categories),
                    "timestamp": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.exception(f"Error getting categories: {e}")
            raise HTTPException(status_code=500, detail=f"Categories error: {str(e)}")

    async def get_stats(self) -> dict:
        """Get ICD-10 database statistics"""
        try:
            with get_db_session() as db:
                stats_result = db.execute(text("""
                    SELECT
                        COUNT(*) as total_codes,
                        COUNT(CASE WHEN is_billable = true THEN 1 END) as billable_codes,
                        COUNT(DISTINCT chapter) as total_chapters,
                        COUNT(DISTINCT category) as total_categories,
                        MAX(last_updated) as last_updated
                    FROM icd10_codes
                """))

                row = stats_result.fetchone()

                return {
                    "total_codes": row.total_codes,
                    "billable_codes": row.billable_codes,
                    "non_billable_codes": row.total_codes - row.billable_codes,
                    "total_chapters": row.total_chapters,
                    "total_categories": row.total_categories,
                    "last_updated": row.last_updated.isoformat() if row.last_updated else None,
                    "data_source": "nlm_clinical_tables",
                    "timestamp": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.exception(f"Error getting stats: {e}")
            raise HTTPException(status_code=500, detail=f"Stats error: {str(e)}")


# FastAPI route handlers
icd10_api = ICD10API()

async def search_icd10_codes(
    query: str = Query(..., description="Search term or code"),
    max_results: int = Query(10, ge=1, le=100, description="Maximum results to return"),
    exact_match: bool = Query(False, description="Require exact code match"),
    category: str | None = Query(None, description="Filter by category"),
    billable_only: bool = Query(False, description="Return only billable codes"),
):
    """Search ICD-10 diagnostic codes"""
    return await icd10_api.search_codes(query, max_results, exact_match, category, billable_only)

async def get_icd10_code_details(code: str):
    """Get detailed information for a specific ICD-10 code"""
    return await icd10_api.get_code_details(code)

async def get_icd10_categories():
    """Get all ICD-10 categories and chapters"""
    return await icd10_api.get_categories()

async def get_icd10_stats():
    """Get ICD-10 database statistics"""
    return await icd10_api.get_stats()
