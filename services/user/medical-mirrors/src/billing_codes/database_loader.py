"""
Database loader for billing codes - handles insertion into medical-mirrors database
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from database import BillingCode, get_db_session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class BillingCodesDatabaseLoader:
    """Loads billing codes data into the medical-mirrors database"""

    def __init__(self):
        self.batch_size = 1000
        self.processed_count = 0
        self.inserted_count = 0
        self.updated_count = 0

    def load_from_json_file(self, json_file_path: str | Path) -> Dict[str, int]:
        """
        Load billing codes from JSON file into database
        
        Args:
            json_file_path: Path to JSON file containing billing codes data
            
        Returns:
            Dictionary with loading statistics
        """
        json_file_path = Path(json_file_path)
        if not json_file_path.exists():
            raise FileNotFoundError(f"JSON file not found: {json_file_path}")

        logger.info(f"Loading billing codes from {json_file_path}")
        
        with open(json_file_path, 'r') as f:
            codes_data = json.load(f)
        
        if not isinstance(codes_data, list):
            raise ValueError("Expected JSON array format")
        
        logger.info(f"Loaded {len(codes_data)} billing codes from JSON")
        return self.load_codes(codes_data)

    def load_codes(self, codes_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Load billing codes data into database
        
        Args:
            codes_data: List of billing code dictionaries
            
        Returns:
            Dictionary with loading statistics
        """
        if not codes_data:
            logger.warning("No billing codes data provided")
            return {"processed": 0, "inserted": 0, "updated": 0}

        with get_db_session() as session:
            try:
                # Clear existing data
                logger.info("Clearing existing billing codes")
                session.execute(text("DELETE FROM billing_codes"))
                session.commit()
                
                # Process in batches
                logger.info(f"Inserting {len(codes_data)} billing codes in batches of {self.batch_size}")
                
                for i in range(0, len(codes_data), self.batch_size):
                    batch = codes_data[i:i + self.batch_size]
                    self._insert_batch(session, batch)
                    batch_num = i // self.batch_size + 1
                    total_batches = (len(codes_data) + self.batch_size - 1) // self.batch_size
                    logger.info(f"Inserted batch {batch_num}/{total_batches}")
                
                # Update search vectors
                logger.info("Updating search vectors for full-text search")
                session.execute(text("""
                    UPDATE billing_codes 
                    SET search_vector = to_tsvector('english', COALESCE(search_text, ''))
                    WHERE search_vector IS NULL
                """))
                
                session.commit()
                
                # Get final count
                final_count = session.execute(text("SELECT COUNT(*) FROM billing_codes")).scalar()
                logger.info(f"✅ Successfully loaded {final_count} billing codes into database")
                
                return {
                    "processed": len(codes_data),
                    "inserted": final_count,
                    "updated": 0
                }
                
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to load billing codes: {e}")
                raise

    def _insert_batch(self, session, batch: List[Dict[str, Any]]) -> None:
        """Insert a batch of billing codes"""
        insert_sql = text("""
            INSERT INTO billing_codes (
                code, short_description, long_description, description, code_type, category,
                coverage_notes, effective_date, termination_date, is_active,
                modifier_required, gender_specific, age_specific, bilateral_indicator,
                source, last_updated, search_text
            ) VALUES (
                :code, :short_description, :long_description, :description, :code_type, :category,
                :coverage_notes, :effective_date, :termination_date, :is_active,
                :modifier_required, :gender_specific, :age_specific, :bilateral_indicator,
                :source, :last_updated, :search_text
            )
            ON CONFLICT (code) DO UPDATE SET
                short_description = EXCLUDED.short_description,
                long_description = EXCLUDED.long_description,
                description = EXCLUDED.description,
                code_type = EXCLUDED.code_type,
                category = EXCLUDED.category,
                coverage_notes = EXCLUDED.coverage_notes,
                effective_date = EXCLUDED.effective_date,
                termination_date = EXCLUDED.termination_date,
                is_active = EXCLUDED.is_active,
                modifier_required = EXCLUDED.modifier_required,
                gender_specific = EXCLUDED.gender_specific,
                age_specific = EXCLUDED.age_specific,
                bilateral_indicator = EXCLUDED.bilateral_indicator,
                source = EXCLUDED.source,
                last_updated = EXCLUDED.last_updated,
                search_text = EXCLUDED.search_text
        """)
        
        # Prepare batch data - ensure all required fields are present
        prepared_batch = []
        for code_data in batch:
            prepared_data = self._prepare_code_data(code_data)
            prepared_batch.append(prepared_data)
        
        session.execute(insert_sql, prepared_batch)

    def _prepare_code_data(self, code_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare code data for database insertion"""
        # Build search text for full-text search
        search_parts = [
            code_data.get("code", "").lower(),
            code_data.get("long_description", ""),
            code_data.get("short_description", "")
        ]
        search_text = " ".join(filter(None, search_parts))
        
        return {
            "code": code_data.get("code", ""),
            "short_description": code_data.get("short_description", ""),
            "long_description": code_data.get("long_description", ""),
            "description": code_data.get("description", ""),
            "code_type": code_data.get("code_type", "HCPCS"),
            "category": code_data.get("category", ""),
            "coverage_notes": code_data.get("coverage_notes", ""),
            "effective_date": code_data.get("effective_date"),
            "termination_date": code_data.get("termination_date"),
            "is_active": code_data.get("is_active", True),
            "modifier_required": code_data.get("modifier_required", False),
            "gender_specific": code_data.get("gender_specific"),
            "age_specific": code_data.get("age_specific"),
            "bilateral_indicator": code_data.get("bilateral_indicator", False),
            "source": code_data.get("source", "cms_direct"),
            "last_updated": code_data.get("last_updated"),
            "search_text": search_text
        }