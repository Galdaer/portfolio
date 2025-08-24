"""
RxClass API Integration for Enhanced Therapeutic Classification

Integrates with the National Library of Medicine's RxClass API to provide
comprehensive drug classification including:
- ATC (Anatomical Therapeutic Chemical) codes
- EPC (Established Pharmacologic Class) codes
- MoA (Mechanism of Action) codes
- PE (Physiologic Effect) codes

API Documentation: https://lhncbc.nlm.nih.gov/RxNav/APIs/RxClassAPIs.html
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Set
import aiohttp
import json

logger = logging.getLogger(__name__)


class RxClassAPI:
    """RxClass API client for drug classification data"""
    
    BASE_URL = "https://rxnav.nlm.nih.gov/REST/rxclass"
    
    def __init__(self, rate_limit_delay: float = 0.1):
        """
        Initialize RxClass API client
        
        Args:
            rate_limit_delay: Delay between API calls to respect rate limits (seconds)
        """
        self.rate_limit_delay = rate_limit_delay
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def get_drug_classes(self, drug_name: str) -> Dict[str, List[str]]:
        """
        Get all classification types for a drug by name
        
        Args:
            drug_name: Generic drug name (e.g., "aspirin")
            
        Returns:
            Dictionary with classification types as keys and class names as values:
            {
                "EPC": ["Nonsteroidal Anti-inflammatory Drug", "Platelet Aggregation Inhibitor"],
                "ATC": ["N02BA01"], 
                "MoA": ["Cyclooxygenase Inhibitors"],
                "PE": ["Decreased Prostaglandin Production"]
            }
        """
        if not self.session:
            raise RuntimeError("RxClassAPI must be used as async context manager")
            
        classifications = {}
        
        # Get different classification types
        classification_types = [
            ("EPC", "FDASPL", "has_EPC"),
            ("MoA", "FDASPL", "has_MOA"), 
            ("PE", "FDASPL", "has_PE"),
            ("ATC", "ATC", "has_atc"),
        ]
        
        for class_type, rel_source, relation in classification_types:
            try:
                classes = await self._get_classes_by_drug_name(drug_name, rel_source, relation)
                if classes:
                    classifications[class_type] = classes
                
                # Rate limiting
                await asyncio.sleep(self.rate_limit_delay)
                
            except Exception as e:
                logger.debug(f"Failed to get {class_type} classes for {drug_name}: {e}")
                continue
        
        return classifications
    
    async def _get_classes_by_drug_name(self, drug_name: str, rel_source: str, relation: str) -> List[str]:
        """Get specific classification type for a drug"""
        url = f"{self.BASE_URL}/class/byDrugName.json"
        params = {
            "drugName": drug_name,
            "relaSource": rel_source,
            "relas": relation
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_classification_response(data)
                else:
                    logger.debug(f"RxClass API error {response.status} for {drug_name}")
                    return []
        except Exception as e:
            logger.debug(f"RxClass API request failed for {drug_name}: {e}")
            return []
    
    def _parse_classification_response(self, data: dict) -> List[str]:
        """Parse RxClass API response to extract class names"""
        classes = []
        
        drug_info_list = data.get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", [])
        
        for drug_info in drug_info_list:
            class_item = drug_info.get("rxclassMinConceptItem", {})
            class_name = class_item.get("className", "")
            
            if class_name:
                classes.append(class_name)
        
        return classes
    
    async def batch_classify_drugs(self, drug_names: List[str], max_concurrent: int = 5) -> Dict[str, Dict[str, List[str]]]:
        """
        Classify multiple drugs in parallel with concurrency control
        
        Args:
            drug_names: List of generic drug names
            max_concurrent: Maximum number of concurrent API calls
            
        Returns:
            Dictionary mapping drug names to their classifications
        """
        if not self.session:
            raise RuntimeError("RxClassAPI must be used as async context manager")
            
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def classify_single_drug(drug_name: str) -> tuple[str, Dict[str, List[str]]]:
            async with semaphore:
                classifications = await self.get_drug_classes(drug_name)
                return drug_name, classifications
        
        # Execute all classifications concurrently
        tasks = [classify_single_drug(drug_name.strip()) for drug_name in drug_names if drug_name.strip()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        classifications = {}
        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"Drug classification failed: {result}")
                continue
            
            drug_name, drug_classifications = result
            if drug_classifications:
                classifications[drug_name] = drug_classifications
        
        return classifications


async def enhance_drug_therapeutic_classes(db_session_factory, batch_size: int = 1000, max_concurrent: int = 3) -> int:
    """
    Enhance existing FDA drugs with therapeutic classes from RxClass API
    
    Args:
        db_session_factory: Database session factory function
        batch_size: Number of drugs to process per batch
        max_concurrent: Maximum concurrent API calls
        
    Returns:
        Number of drugs updated with new therapeutic classes
    """
    logger.info("Starting therapeutic class enhancement using RxClass API")
    
    db = db_session_factory()
    updated_count = 0
    
    try:
        # Get drugs that don't have therapeutic classes
        from sqlalchemy import text
        
        result = db.execute(text("""
            SELECT DISTINCT generic_name, ndc
            FROM drug_information 
            WHERE (therapeutic_class IS NULL OR therapeutic_class = '')
              AND generic_name IS NOT NULL 
              AND generic_name != ''
              AND generic_name NOT LIKE '%Unknown%'
            ORDER BY generic_name
            LIMIT :batch_size
        """), {"batch_size": batch_size})
        
        drug_records = result.fetchall()
        
        if not drug_records:
            logger.info("No drugs found that need therapeutic class enhancement")
            return 0
        
        logger.info(f"Found {len(drug_records)} drugs to enhance with therapeutic classes")
        
        # Extract unique generic names
        unique_generic_names = list(set(record[0] for record in drug_records))
        
        # Get classifications from RxClass API
        async with RxClassAPI(rate_limit_delay=0.1) as rxclass:
            classifications = await rxclass.batch_classify_drugs(unique_generic_names, max_concurrent)
        
        logger.info(f"Retrieved classifications for {len(classifications)} drugs")
        
        # Update database with therapeutic classes
        for generic_name, class_data in classifications.items():
            # Prefer EPC (Established Pharmacologic Class) as primary therapeutic class
            primary_class = ""
            
            if "EPC" in class_data and class_data["EPC"]:
                primary_class = class_data["EPC"][0]  # Use first EPC class
            elif "ATC" in class_data and class_data["ATC"]:
                primary_class = class_data["ATC"][0]  # Fallback to ATC
            elif "MoA" in class_data and class_data["MoA"]:
                primary_class = class_data["MoA"][0]  # Fallback to MoA
            
            if primary_class:
                # Update all drugs with this generic name
                update_result = db.execute(text("""
                    UPDATE drug_information 
                    SET therapeutic_class = :therapeutic_class,
                        updated_at = NOW()
                    WHERE generic_name = :generic_name 
                      AND (therapeutic_class IS NULL OR therapeutic_class = '')
                """), {
                    "therapeutic_class": primary_class,
                    "generic_name": generic_name
                })
                
                updated_count += update_result.rowcount
                logger.debug(f"Updated {update_result.rowcount} drugs with generic name '{generic_name}' to class '{primary_class}'")
        
        db.commit()
        logger.info(f"Successfully enhanced {updated_count} drugs with therapeutic classes")
        
    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to enhance therapeutic classes: {e}")
        raise
    finally:
        db.close()
    
    return updated_count


if __name__ == "__main__":
    # Test the API
    async def test_rxclass():
        async with RxClassAPI() as rxclass:
            # Test single drug
            classes = await rxclass.get_drug_classes("aspirin")
            print("Aspirin classifications:")
            for class_type, class_names in classes.items():
                print(f"  {class_type}: {class_names}")
            
            # Test batch classification
            drugs = ["insulin", "atorvastatin", "metformin"]
            batch_results = await rxclass.batch_classify_drugs(drugs)
            print("\nBatch results:")
            for drug, classifications in batch_results.items():
                print(f"{drug}:")
                for class_type, class_names in classifications.items():
                    print(f"  {class_type}: {class_names}")
    
    asyncio.run(test_rxclass())