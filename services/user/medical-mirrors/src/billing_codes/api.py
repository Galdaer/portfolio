"""
Billing codes API endpoints for medical mirrors service
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import HTTPException, Query
from sqlalchemy import and_, desc, func, or_, text
from sqlalchemy.orm import Session

from database import get_db_session

logger = logging.getLogger(__name__)


class BillingCodesAPI:
    """API for medical billing codes (CPT/HCPCS) search and lookup"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def search_codes(
        self,
        query: str,
        code_type: Optional[str] = None,
        max_results: int = 10,
        active_only: bool = True,
        category: Optional[str] = None
    ) -> Dict:
        """Search billing codes"""
        try:
            with get_db_session() as db:
                # Build base query
                base_query = """
                    SELECT code, short_description, long_description, description,
                           code_type, category, coverage_notes, effective_date,
                           termination_date, is_active, modifier_required,
                           gender_specific, age_specific, bilateral_indicator,
                           last_updated,
                           ts_rank(search_vector, plainto_tsquery(:query)) as rank
                    FROM billing_codes
                    WHERE search_vector @@ plainto_tsquery(:query)
                """
                
                # Apply filters
                conditions = []
                params = {"query": query, "max_results": min(max_results, 100)}
                
                if code_type:
                    conditions.append("UPPER(code_type) = UPPER(:code_type)")
                    params["code_type"] = code_type
                
                if active_only:
                    conditions.append("is_active = true")
                
                if category:
                    conditions.append("UPPER(category) = UPPER(:category)")
                    params["category"] = category
                
                # Build final query
                where_clause = ""
                if conditions:
                    where_clause = "AND " + " AND ".join(conditions)
                
                final_query = f"""
                    {base_query}
                    {where_clause}
                    ORDER BY rank DESC, code_type, code
                    LIMIT :max_results
                """
                
                result = db.execute(text(final_query), params)
                rows = result.fetchall()
                
                codes = []
                for row in rows:
                    code_dict = {
                        "code": row.code,
                        "short_description": row.short_description or "",
                        "long_description": row.long_description or "",
                        "description": row.description,
                        "code_type": row.code_type,
                        "category": row.category or "",
                        "coverage_notes": row.coverage_notes or "",
                        "effective_date": row.effective_date.isoformat() if row.effective_date else None,
                        "termination_date": row.termination_date.isoformat() if row.termination_date else None,
                        "is_active": bool(row.is_active),
                        "modifier_required": bool(row.modifier_required),
                        "gender_specific": row.gender_specific,
                        "age_specific": row.age_specific,
                        "bilateral_indicator": bool(row.bilateral_indicator),
                        "last_updated": row.last_updated.isoformat() if row.last_updated else None,
                        "relevance_score": float(row.rank) if row.rank else 0.0
                    }
                    codes.append(code_dict)
                
                return {
                    "codes": codes,
                    "total_results": len(codes),
                    "search_query": query,
                    "filters": {
                        "code_type": code_type,
                        "active_only": active_only,
                        "category": category
                    },
                    "timestamp": datetime.now().isoformat()
                }
        
        except Exception as e:
            logger.error(f"Error searching billing codes: {e}")
            raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")
    
    async def get_code_details(self, code: str) -> Dict:
        """Get detailed information for a specific billing code"""
        try:
            with get_db_session() as db:
                result = db.execute(text("""
                    SELECT code, short_description, long_description, description,
                           code_type, category, coverage_notes, effective_date,
                           termination_date, is_active, modifier_required,
                           gender_specific, age_specific, bilateral_indicator,
                           search_text, last_updated, source
                    FROM billing_codes
                    WHERE UPPER(code) = UPPER(:code)
                """), {"code": code})
                
                row = result.fetchone()
                
                if not row:
                    raise HTTPException(status_code=404, detail=f"Billing code '{code}' not found")
                
                # Get related codes (similar codes in same category)
                related_codes = await self._get_related_codes(db, row.code, row.category, row.code_type)
                
                code_details = {
                    "code": row.code,
                    "short_description": row.short_description or "",
                    "long_description": row.long_description or "",
                    "description": row.description,
                    "code_type": row.code_type,
                    "category": row.category or "",
                    "coverage_notes": row.coverage_notes or "",
                    "effective_date": row.effective_date.isoformat() if row.effective_date else None,
                    "termination_date": row.termination_date.isoformat() if row.termination_date else None,
                    "is_active": bool(row.is_active),
                    "modifier_required": bool(row.modifier_required),
                    "gender_specific": row.gender_specific,
                    "age_specific": row.age_specific,
                    "bilateral_indicator": bool(row.bilateral_indicator),
                    "related_codes": related_codes,
                    "clinical_guidance": self._generate_clinical_guidance(row),
                    "billing_guidance": self._generate_billing_guidance(row),
                    "last_updated": row.last_updated.isoformat() if row.last_updated else None,
                    "source": row.source or "unknown"
                }
                
                return code_details
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting code details for '{code}': {e}")
            raise HTTPException(status_code=500, detail=f"Lookup error: {str(e)}")
    
    async def _get_related_codes(
        self, 
        db: Session, 
        code: str, 
        category: str, 
        code_type: str
    ) -> List[Dict]:
        """Get related codes in the same category"""
        related_codes = []
        
        try:
            # Get similar codes in same category
            result = db.execute(text("""
                SELECT code, description, code_type
                FROM billing_codes
                WHERE category = :category 
                  AND code_type = :code_type
                  AND code != :code
                  AND is_active = true
                ORDER BY code
                LIMIT 10
            """), {
                "category": category,
                "code_type": code_type,
                "code": code
            })
            
            for row in result.fetchall():
                related_codes.append({
                    "code": row.code,
                    "description": row.description,
                    "code_type": row.code_type
                })
        
        except Exception as e:
            logger.error(f"Error getting related codes: {e}")
        
        return related_codes
    
    def _generate_clinical_guidance(self, code_data) -> str:
        """Generate clinical usage guidance"""
        guidance_parts = []
        
        # Basic usage
        guidance_parts.append(f"Use this code for: {code_data.description}")
        
        # Gender specificity
        if code_data.gender_specific:
            guidance_parts.append(f"Gender-specific: {code_data.gender_specific} patients only")
        
        # Age specificity
        if code_data.age_specific:
            guidance_parts.append(f"Age-specific: {code_data.age_specific} patients")
        
        # Bilateral indicator
        if code_data.bilateral_indicator:
            guidance_parts.append("Consider bilateral nature of procedure")
        
        # Modifier requirements
        if code_data.modifier_required:
            guidance_parts.append("May require appropriate modifiers")
        
        return " | ".join(guidance_parts)
    
    def _generate_billing_guidance(self, code_data) -> str:
        """Generate billing and reimbursement guidance"""
        guidance_parts = []
        
        # Active status
        if code_data.is_active:
            guidance_parts.append("Currently active for billing")
        else:
            guidance_parts.append("Code is inactive - check for replacement")
        
        # Coverage notes
        if code_data.coverage_notes:
            guidance_parts.append(f"Coverage: {code_data.coverage_notes}")
        
        # Code type specific guidance
        if code_data.code_type == "HCPCS":
            guidance_parts.append("HCPCS Level II code - may have specific coverage requirements")
        elif code_data.code_type == "CPT":
            guidance_parts.append("CPT code - check current year CPT manual for updates")
        
        # Modifier guidance
        if code_data.modifier_required:
            guidance_parts.append("Verify appropriate modifiers are applied")
        
        # Effective dates
        if code_data.effective_date:
            guidance_parts.append(f"Effective from: {code_data.effective_date}")
        
        if code_data.termination_date:
            guidance_parts.append(f"Terminated: {code_data.termination_date}")
        
        return " | ".join(guidance_parts)
    
    async def get_categories(self, code_type: Optional[str] = None) -> Dict:
        """Get all billing code categories"""
        try:
            with get_db_session() as db:
                query = """
                    SELECT code_type, category, COUNT(*) as code_count,
                           COUNT(CASE WHEN is_active = true THEN 1 END) as active_count
                    FROM billing_codes
                    WHERE category IS NOT NULL AND category != ''
                """
                
                params = {}
                if code_type:
                    query += " AND UPPER(code_type) = UPPER(:code_type)"
                    params["code_type"] = code_type
                
                query += """
                    GROUP BY code_type, category
                    ORDER BY code_type, category
                """
                
                result = db.execute(text(query), params)
                
                categories = []
                for row in result.fetchall():
                    categories.append({
                        "code_type": row.code_type,
                        "category": row.category,
                        "code_count": row.code_count,
                        "active_count": row.active_count
                    })
                
                return {
                    "categories": categories,
                    "total_categories": len(categories),
                    "filter_applied": code_type,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            raise HTTPException(status_code=500, detail=f"Categories error: {str(e)}")
    
    async def get_stats(self) -> Dict:
        """Get billing codes database statistics"""
        try:
            with get_db_session() as db:
                stats_result = db.execute(text("""
                    SELECT 
                        COUNT(*) as total_codes,
                        COUNT(CASE WHEN is_active = true THEN 1 END) as active_codes,
                        COUNT(CASE WHEN code_type = 'CPT' THEN 1 END) as cpt_codes,
                        COUNT(CASE WHEN code_type = 'HCPCS' THEN 1 END) as hcpcs_codes,
                        COUNT(DISTINCT category) as total_categories,
                        MAX(last_updated) as last_updated
                    FROM billing_codes
                """))
                
                row = stats_result.fetchone()
                
                return {
                    "total_codes": row.total_codes,
                    "active_codes": row.active_codes,
                    "inactive_codes": row.total_codes - row.active_codes,
                    "cpt_codes": row.cpt_codes,
                    "hcpcs_codes": row.hcpcs_codes,
                    "total_categories": row.total_categories,
                    "last_updated": row.last_updated.isoformat() if row.last_updated else None,
                    "data_sources": ["nlm_clinical_tables"],
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            raise HTTPException(status_code=500, detail=f"Stats error: {str(e)}")


# FastAPI route handlers
billing_codes_api = BillingCodesAPI()

async def search_billing_codes(
    query: str = Query(..., description="Search term or code"),
    code_type: Optional[str] = Query(None, description="Filter by code type (CPT, HCPCS)"),
    max_results: int = Query(10, ge=1, le=100, description="Maximum results to return"),
    active_only: bool = Query(True, description="Return only active codes"),
    category: Optional[str] = Query(None, description="Filter by category")
):
    """Search medical billing codes"""
    return await billing_codes_api.search_codes(query, code_type, max_results, active_only, category)

async def get_billing_code_details(code: str):
    """Get detailed information for a specific billing code"""
    return await billing_codes_api.get_code_details(code)

async def get_billing_categories(
    code_type: Optional[str] = Query(None, description="Filter by code type")
):
    """Get all billing code categories"""
    return await billing_codes_api.get_categories(code_type)

async def get_billing_stats():
    """Get billing codes database statistics"""
    return await billing_codes_api.get_stats()