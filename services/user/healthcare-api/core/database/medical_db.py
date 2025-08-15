"""
Medical Database Access Layer

Provides database-first access to local medical literature mirrors:
- pubmed_articles
- clinical_trials  
- fda_drugs

This ensures rate limiting issues are avoided by using local data first.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from src.security.database_factory import PostgresConnectionFactory
from core.infrastructure.healthcare_logger import get_healthcare_logger

logger = get_healthcare_logger(__name__)


class MedicalDatabaseAccess:
    """Database access layer for medical literature mirrors"""
    
    def __init__(self, connection_string: Optional[str] = None):
        """Initialize medical database access.
        
        Args:
            connection_string: PostgreSQL connection string (uses env defaults if None)
        """
        self.db_factory = PostgresConnectionFactory(connection_string)
        self.logger = logger
    
    def search_pubmed_local(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search local PubMed articles database.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of PubMed articles from local database
        """
        try:
            self.logger.info(f"🔍 Searching local PubMed database: {query[:50]}...")
            
            conn = self.db_factory.create_connection()
            try:
                cursor = conn.cursor()
                
                # Use PostgreSQL full-text search
                search_sql = """
                    SELECT pmid, title, abstract, authors, journal, pub_date, doi, mesh_terms,
                           ts_rank(search_vector, plainto_tsquery(%s)) as rank
                    FROM pubmed_articles
                    WHERE search_vector @@ plainto_tsquery(%s)
                    ORDER BY rank DESC, pub_date DESC
                    LIMIT %s
                """
                
                cursor.execute(search_sql, (query, query, max_results))
                rows = cursor.fetchall()
                
                articles = []
                for row in rows:
                    # Handle pub_date - could be datetime object or string
                    pub_date = row[5]
                    if pub_date:
                        if hasattr(pub_date, 'isoformat'):
                            pub_date_str = pub_date.isoformat()
                        else:
                            pub_date_str = str(pub_date)
                    else:
                        pub_date_str = ""
                    
                    article = {
                        "pmid": row[0],
                        "title": row[1] or "",
                        "abstract": row[2] or "",
                        "authors": row[3] or [],
                        "journal": row[4] or "",
                        "pub_date": pub_date_str,
                        "doi": row[6] or "",
                        "mesh_terms": row[7] or [],
                        "rank": float(row[8]) if row[8] else 0.0,
                        "source": "local_pubmed"
                    }
                    articles.append(article)
                
                self.logger.info(f"✅ Found {len(articles)} articles in local PubMed database")
                return articles
            finally:
                conn.close()
                
        except Exception as e:
            self.logger.error(f"Local PubMed search error: {e}")
            return []
    
    def search_clinical_trials_local(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search local clinical trials database.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of clinical trials from local database
        """
        try:
            self.logger.info(f"🔍 Searching local clinical trials database: {query[:50]}...")
            
            conn = self.db_factory.create_connection()
            try:
                cursor = conn.cursor()
                
                # Search clinical trials with text search
                search_sql = """
                    SELECT nct_id, title, brief_summary, detailed_description,
                           primary_purpose, phase, enrollment, status, start_date,
                           completion_date, sponsor_name, location_countries
                    FROM clinical_trials
                    WHERE search_vector @@ plainto_tsquery(%s)
                    ORDER BY
                        ts_rank(search_vector, plainto_tsquery(%s)) DESC,
                        start_date DESC
                    LIMIT %s
                """
                
                cursor.execute(search_sql, (query, query, max_results))
                rows = cursor.fetchall()
                
                trials = []
                for row in rows:
                    # Handle dates - could be datetime objects or strings
                    start_date = row[8]
                    if start_date:
                        if hasattr(start_date, 'isoformat'):
                            start_date_str = start_date.isoformat()
                        else:
                            start_date_str = str(start_date)
                    else:
                        start_date_str = ""
                        
                    completion_date = row[9]
                    if completion_date:
                        if hasattr(completion_date, 'isoformat'):
                            completion_date_str = completion_date.isoformat()
                        else:
                            completion_date_str = str(completion_date)
                    else:
                        completion_date_str = ""
                    
                    trial = {
                        "nct_id": row[0] or "",
                        "title": row[1] or "",
                        "brief_summary": row[2] or "",
                        "detailed_description": row[3] or "",
                        "primary_purpose": row[4] or "",
                        "phase": row[5] or "",
                        "enrollment": row[6] or 0,
                        "status": row[7] or "",
                        "start_date": start_date_str,
                        "completion_date": completion_date_str,
                        "sponsor_name": row[10] or "",
                        "location_countries": row[11] or [],
                        "source": "local_clinical_trials"
                    }
                    trials.append(trial)
                
                self.logger.info(f"✅ Found {len(trials)} trials in local clinical trials database")
                return trials
            finally:
                conn.close()
                
        except Exception as e:
            self.logger.error(f"Local clinical trials search error: {e}")
            return []
    
    def search_fda_drugs_local(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search local FDA drugs database.
        
        Args:
            query: Search query (drug name, indication, etc.)
            max_results: Maximum number of results
            
        Returns:
            List of FDA drugs from local database
        """
        try:
            self.logger.info(f"🔍 Searching local FDA drugs database: {query[:50]}...")
            
            with self.db_factory.create_connection() as conn:
                cursor = conn.cursor()
                
                # Search FDA drugs
                search_sql = """
                    SELECT application_number, product_number, form, strength, 
                           reference_drug, drug_name, active_ingredient, reference_standard,
                           dosage_form, route, marketing_status, te_code, rld, rs, 
                           approval_date, applicant_full_name
                    FROM fda_drugs
                    WHERE search_vector @@ plainto_tsquery(%s)
                    ORDER BY 
                        ts_rank(search_vector, plainto_tsquery(%s)) DESC,
                        approval_date DESC
                    LIMIT %s
                """
                
                cursor.execute(search_sql, (query, query, max_results))
                rows = cursor.fetchall()
                
                drugs = []
                for row in rows:
                    drug = {
                        "application_number": row[0] or "",
                        "product_number": row[1] or "",
                        "form": row[2] or "",
                        "strength": row[3] or "",
                        "reference_drug": row[4] or "",
                        "drug_name": row[5] or "",
                        "active_ingredient": row[6] or "",
                        "reference_standard": row[7] or "",
                        "dosage_form": row[8] or "",
                        "route": row[9] or "",
                        "marketing_status": row[10] or "",
                        "te_code": row[11] or "",
                        "rld": row[12] or "",
                        "rs": row[13] or "",
                        "approval_date": row[14].isoformat() if row[14] else "",
                        "applicant_full_name": row[15] or "",
                        "source": "local_fda_drugs"
                    }
                    drugs.append(drug)
                
                self.logger.info(f"✅ Found {len(drugs)} drugs in local FDA drugs database")
                return drugs
                
        except Exception as e:
            self.logger.error(f"Local FDA drugs search error: {e}")
            return []
    
    def get_database_status(self) -> Dict[str, Any]:
        """Get status of medical database tables.
        
        Returns:
            Dictionary with table counts and status
        """
        try:
            with self.db_factory.create_connection() as conn:
                cursor = conn.cursor()
                
                # Get counts for each table
                status = {}
                
                for table in ["pubmed_articles", "clinical_trials", "fda_drugs"]:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        status[table] = {
                            "count": count,
                            "available": True
                        }
                    except Exception as e:
                        status[table] = {
                            "count": 0,
                            "available": False,
                            "error": str(e)
                        }
                
                return {
                    "database_available": True,
                    "tables": status,
                    "last_checked": datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Database status check error: {e}")
            return {
                "database_available": False,
                "error": str(e),
                "last_checked": datetime.now().isoformat()
            }


# Global instance for easy access
_medical_db = None


def get_medical_db() -> MedicalDatabaseAccess:
    """Get global medical database access instance."""
    global _medical_db
    if _medical_db is None:
        # Use environment database URL
        from config import config
        _medical_db = MedicalDatabaseAccess(config.postgres_url)
    return _medical_db
