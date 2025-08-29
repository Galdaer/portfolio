"""
Database loader for ICD-10 codes - handles insertion into medical-mirrors database
Following proven billing_codes success patterns for 100% field coverage
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from database import ICD10Code, get_db_session
from sqlalchemy import text

# Import enhancer for post-load enhancement
from .icd10_enrichment import ICD10DatabaseEnhancer

logger = logging.getLogger(__name__)


class ICD10DatabaseLoader:
    """Loads ICD-10 codes data into the medical-mirrors database with enhanced field population"""

    def __init__(self):
        self.batch_size = 1000
        self.processed_count = 0
        self.inserted_count = 0
        self.updated_count = 0

        # ICD-10 chapter mapping for category population
        self.chapter_categories = {
            # Based on official ICD-10-CM chapter structure
            "A": "Certain infectious and parasitic diseases",
            "B": "Certain infectious and parasitic diseases",
            "C": "Neoplasms",
            "D": "Diseases of the blood and blood-forming organs and certain disorders involving the immune mechanism",
            "E": "Endocrine, nutritional and metabolic diseases",
            "F": "Mental, Behavioral and Neurodevelopmental disorders",
            "G": "Diseases of the nervous system",
            "H": "Diseases of the eye and adnexa",
            "I": "Diseases of the circulatory system",
            "J": "Diseases of the respiratory system",
            "K": "Diseases of the digestive system",
            "L": "Diseases of the skin and subcutaneous tissue",
            "M": "Diseases of the musculoskeletal system and connective tissue",
            "N": "Diseases of the genitourinary system",
            "O": "Pregnancy, childbirth and the puerperium",
            "P": "Certain conditions originating in the perinatal period",
            "Q": "Congenital malformations, deformations and chromosomal abnormalities",
            "R": "Symptoms, signs and abnormal clinical and laboratory findings, not elsewhere classified",
            "S": "Injury, poisoning and certain other consequences of external causes",
            "T": "Injury, poisoning and certain other consequences of external causes",
            "V": "External causes of morbidity",
            "W": "External causes of morbidity",
            "X": "External causes of morbidity",
            "Y": "External causes of morbidity",
            "Z": "Factors influencing health status and contact with health services",
        }

        # Additional subcategory mappings for enhanced specificity
        self.enhanced_categories = {
            # Eye conditions (H chapter)
            "H00-H05": "Disorders of eyelid, lacrimal system and orbit",
            "H10-H11": "Disorders of conjunctiva",
            "H15-H22": "Disorders of sclera, cornea, iris and ciliary body",
            "H25-H28": "Disorders of lens",
            "H30-H36": "Disorders of choroid and retina",
            "H40-H42": "Glaucoma",
            "H43-H44": "Disorders of vitreous body and globe",
            "H46-H47": "Disorders of optic nerve and visual pathways",
            "H49-H52": "Disorders of ocular muscles, binocular movement, accommodation and refraction",
            "H53-H54": "Visual disturbances and blindness",
            "H55-H57": "Other disorders of eye and adnexa",
            
            # Circulatory system (I chapter)
            "I00-I02": "Acute rheumatic fever",
            "I05-I09": "Chronic rheumatic heart diseases",
            "I10-I16": "Hypertensive diseases",
            "I20-I25": "Ischemic heart diseases",
            "I26-I28": "Pulmonary heart disease and diseases of pulmonary circulation",
            "I30-I52": "Other forms of heart disease",
            "I60-I69": "Cerebrovascular diseases",
            "I70-I79": "Diseases of arteries, arterioles and capillaries",
            "I80-I89": "Diseases of veins, lymphatic vessels and lymph nodes",
            "I95-I99": "Other and unspecified disorders of the circulatory system",
            
            # Respiratory system (J chapter)
            "J00-J06": "Acute upper respiratory infections",
            "J09-J18": "Influenza and pneumonia",
            "J20-J22": "Other acute lower respiratory infections",
            "J30-J39": "Other diseases of upper respiratory tract",
            "J40-J47": "Chronic lower respiratory diseases",
            "J60-J70": "Lung diseases due to external agents",
            "J80-J84": "Other respiratory diseases principally affecting the interstitium",
            "J85-J86": "Suppurative and necrotic conditions of the lower respiratory tract",
            "J90-J94": "Other diseases of the pleura",
            "J95-J99": "Other diseases of the respiratory system",

            # Add more as needed for comprehensive category coverage
        }

    def load_from_json_file(self, json_file_path: str | Path, enhance_after_load: bool = True) -> Dict[str, int]:
        """
        Load ICD-10 codes from JSON file into database
        
        Args:
            json_file_path: Path to JSON file containing ICD-10 codes data
            enhance_after_load: If True, automatically enhance database after loading completes
            
        Returns:
            Dictionary with loading statistics
        """
        json_file_path = Path(json_file_path)
        if not json_file_path.exists():
            raise FileNotFoundError(f"JSON file not found: {json_file_path}")

        logger.info(f"Loading ICD-10 codes from {json_file_path}")
        
        with open(json_file_path, 'r') as f:
            codes_data = json.load(f)
        
        if not isinstance(codes_data, list):
            raise ValueError("Expected JSON array format")
        
        logger.info(f"Loaded {len(codes_data)} ICD-10 codes from JSON")
        return self.load_codes(codes_data, enhance_after_load=enhance_after_load)

    def load_codes(self, codes_data: List[Dict[str, Any]], enhance_after_load: bool = True) -> Dict[str, int]:
        """
        Load ICD-10 codes data into database with enhanced field population
        
        Args:
            codes_data: List of ICD-10 code dictionaries
            enhance_after_load: If True, automatically enhance database after loading completes
            
        Returns:
            Dictionary with loading statistics
        """
        if not codes_data:
            logger.warning("No ICD-10 codes data provided")
            return {"processed": 0, "inserted": 0, "updated": 0}

        # Enhance data with proper category and search text
        enhanced_codes = self._enhance_codes_data(codes_data)

        with get_db_session() as session:
            try:
                # Process in batches using UPSERT to preserve existing data
                logger.info(f"Upserting {len(enhanced_codes)} ICD-10 codes in batches of {self.batch_size}")
                
                for i in range(0, len(enhanced_codes), self.batch_size):
                    batch = enhanced_codes[i:i + self.batch_size]
                    self._upsert_batch(session, batch)
                    batch_num = i // self.batch_size + 1
                    total_batches = (len(enhanced_codes) + self.batch_size - 1) // self.batch_size
                    logger.info(f"Processed batch {batch_num}/{total_batches}")
                
                # Update search vectors for full-text search
                logger.info("Updating search vectors for full-text search")
                session.execute(text("""
                    UPDATE icd10_codes 
                    SET search_vector = to_tsvector('english', 
                        COALESCE(code, '') || ' ' || 
                        COALESCE(description, '') || ' ' || 
                        COALESCE(category, '') || ' ' ||
                        COALESCE(search_text, '')
                    )
                    WHERE search_vector IS NULL OR search_text IS NOT NULL
                """))
                
                session.commit()
                
                # Get final count and comprehensive field coverage stats
                stats_result = session.execute(text("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN category IS NOT NULL AND category != '' THEN 1 END) as with_category,
                        COUNT(CASE WHEN search_vector IS NOT NULL THEN 1 END) as with_search_vector,
                        COUNT(CASE WHEN synonyms IS NOT NULL AND synonyms != '[]'::jsonb THEN 1 END) as with_synonyms,
                        COUNT(CASE WHEN inclusion_notes IS NOT NULL AND inclusion_notes != '[]'::jsonb THEN 1 END) as with_inclusion_notes,
                        COUNT(CASE WHEN exclusion_notes IS NOT NULL AND exclusion_notes != '[]'::jsonb THEN 1 END) as with_exclusion_notes,
                        COUNT(CASE WHEN children_codes IS NOT NULL AND children_codes != '[]'::jsonb THEN 1 END) as with_children_codes
                    FROM icd10_codes
                """)).fetchone()
                
                logger.info(f"✅ Successfully processed {len(enhanced_codes)} ICD-10 codes")
                logger.info(f"✅ Database totals: {stats_result.total} codes")
                logger.info(f"✅ Category coverage: {stats_result.with_category}/{stats_result.total} ({stats_result.with_category/stats_result.total*100:.1f}%)")
                logger.info(f"✅ Search vector coverage: {stats_result.with_search_vector}/{stats_result.total} ({stats_result.with_search_vector/stats_result.total*100:.1f}%)")
                logger.info(f"✅ Synonyms coverage: {stats_result.with_synonyms}/{stats_result.total} ({stats_result.with_synonyms/stats_result.total*100:.1f}%)")
                logger.info(f"✅ Inclusion notes coverage: {stats_result.with_inclusion_notes}/{stats_result.total} ({stats_result.with_inclusion_notes/stats_result.total*100:.1f}%)")
                logger.info(f"✅ Exclusion notes coverage: {stats_result.with_exclusion_notes}/{stats_result.total} ({stats_result.with_exclusion_notes/stats_result.total*100:.1f}%)")
                logger.info(f"✅ Children codes coverage: {stats_result.with_children_codes}/{stats_result.total} ({stats_result.with_children_codes/stats_result.total*100:.1f}%)")
                
                # Prepare return statistics
                load_stats = {
                    "processed": len(enhanced_codes),
                    "total_in_db": stats_result.total,
                    "category_coverage": stats_result.with_category,
                    "search_vector_coverage": stats_result.with_search_vector,
                    "synonyms_coverage": stats_result.with_synonyms,
                    "inclusion_notes_coverage": stats_result.with_inclusion_notes,
                    "exclusion_notes_coverage": stats_result.with_exclusion_notes,
                    "children_codes_coverage": stats_result.with_children_codes
                }
                
                # Run database enhancement if requested
                if enhance_after_load:
                    logger.info("Running post-load database enhancement...")
                    try:
                        enhancer = ICD10DatabaseEnhancer()
                        enhancement_stats = enhancer.enhance_icd10_database()
                        
                        # Add enhancement stats to return data
                        load_stats['enhancement_completed'] = True
                        load_stats['enhancement_stats'] = enhancement_stats
                        
                        logger.info(f"✅ Post-load enhancement completed: "
                                   f"{enhancement_stats.get('enhanced', 0):,} codes enhanced, "
                                   f"{enhancement_stats.get('synonyms_added', 0):,} synonyms added")
                        
                    except Exception as e:
                        logger.error(f"Post-load enhancement failed: {e}")
                        load_stats['enhancement_completed'] = False
                        load_stats['enhancement_error'] = str(e)
                        # Don't re-raise - enhancement failure shouldn't fail the load
                
                return load_stats
                
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to load ICD-10 codes: {e}")
                raise

    def _enhance_codes_data(self, codes_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enhance ICD-10 codes with proper category population and search text
        This addresses the core issue causing 0.02% category coverage
        """
        logger.info("Enhancing ICD-10 codes with category data and search text")
        
        enhanced_codes = []
        category_populated = 0
        
        for code_data in codes_data:
            enhanced_code = dict(code_data)  # Copy original data
            
            # Extract category from hierarchical structure
            category = self._extract_category(enhanced_code)
            if category:
                enhanced_code["category"] = category
                category_populated += 1
            
            # Ensure proper search text
            search_text = self._create_comprehensive_search_text(enhanced_code)
            enhanced_code["search_text"] = search_text
            
            enhanced_codes.append(enhanced_code)
        
        logger.info(f"Enhanced {category_populated}/{len(codes_data)} codes with category data ({category_populated/len(codes_data)*100:.1f}%)")
        return enhanced_codes

    def _extract_category(self, code_data: Dict[str, Any]) -> str:
        """
        Extract category from code using hierarchical ICD-10 structure
        This is the key fix for 0.02% → 100% category coverage
        """
        code = code_data.get("code", "").strip().upper()
        existing_category = code_data.get("category", "").strip()
        
        # Use existing category if available and non-empty
        if existing_category:
            return existing_category
        
        if not code:
            return ""
        
        # Extract first character for chapter-level category
        first_char = code[0]
        chapter_category = self.chapter_categories.get(first_char, "")
        
        # Try to get more specific subcategory based on code range
        specific_category = self._get_specific_subcategory(code, chapter_category)
        if specific_category:
            return specific_category
        
        return chapter_category

    def _get_specific_subcategory(self, code: str, chapter_category: str) -> str:
        """Get specific subcategory based on code range"""
        if not code or len(code) < 3:
            return chapter_category
        
        # Check enhanced category mappings
        for code_range, category in self.enhanced_categories.items():
            if self._code_in_range(code, code_range):
                return category
        
        return chapter_category

    def _code_in_range(self, code: str, code_range: str) -> bool:
        """Check if code falls within specified range"""
        try:
            if "-" not in code_range:
                return False
                
            start_range, end_range = code_range.split("-")
            
            # Extract numeric portion for comparison
            code_base = code[:3]  # First 3 characters
            
            return start_range <= code_base <= end_range
        except Exception:
            return False

    def _create_comprehensive_search_text(self, code_data: Dict[str, Any]) -> str:
        """Create comprehensive search text for full-text search"""
        search_parts = []
        
        # Add code
        code = code_data.get("code", "").strip()
        if code:
            search_parts.append(code)
        
        # Add description
        description = code_data.get("description", "").strip()
        if description:
            search_parts.append(description)
        
        # Add category
        category = code_data.get("category", "").strip()
        if category:
            search_parts.append(category)
        
        # Add chapter
        chapter = code_data.get("chapter", "").strip()
        if chapter:
            search_parts.append(chapter)
        
        # Add synonyms if available
        synonyms = code_data.get("synonyms", [])
        if isinstance(synonyms, list):
            search_parts.extend([str(s).strip() for s in synonyms if s])
        elif synonyms:
            search_parts.append(str(synonyms))
        
        return " ".join(search_parts).lower()

    def _upsert_batch(self, session, batch: List[Dict[str, Any]]) -> None:
        """Upsert a batch of ICD-10 codes using enhanced UPSERT logic"""
        upsert_sql = text("""
            INSERT INTO icd10_codes (
                code, description, category, chapter, synonyms,
                inclusion_notes, exclusion_notes, is_billable,
                code_length, parent_code, children_codes,
                source, search_text, last_updated
            ) VALUES (
                :code, :description, :category, :chapter, :synonyms,
                :inclusion_notes, :exclusion_notes, :is_billable,
                :code_length, :parent_code, :children_codes,
                :source, :search_text, NOW()
            )
            ON CONFLICT (code) DO UPDATE SET
                -- Only update if we have better/more complete information
                description = COALESCE(
                    CASE WHEN LENGTH(COALESCE(EXCLUDED.description, '')) > LENGTH(COALESCE(icd10_codes.description, ''))
                         THEN EXCLUDED.description
                         ELSE icd10_codes.description
                    END, 
                    EXCLUDED.description, 
                    icd10_codes.description
                ),
                category = COALESCE(
                    CASE WHEN EXCLUDED.category IS NOT NULL AND EXCLUDED.category != '' 
                         THEN EXCLUDED.category
                         ELSE icd10_codes.category
                    END,
                    EXCLUDED.category, 
                    icd10_codes.category
                ),
                chapter = COALESCE(NULLIF(EXCLUDED.chapter, ''), icd10_codes.chapter),
                synonyms = COALESCE(
                    CASE WHEN EXCLUDED.synonyms != '[]'::jsonb 
                         THEN EXCLUDED.synonyms
                         ELSE icd10_codes.synonyms
                    END,
                    EXCLUDED.synonyms, 
                    icd10_codes.synonyms
                ),
                inclusion_notes = COALESCE(
                    CASE WHEN EXCLUDED.inclusion_notes != '[]'::jsonb 
                         THEN EXCLUDED.inclusion_notes
                         ELSE icd10_codes.inclusion_notes
                    END,
                    EXCLUDED.inclusion_notes, 
                    icd10_codes.inclusion_notes
                ),
                exclusion_notes = COALESCE(
                    CASE WHEN EXCLUDED.exclusion_notes != '[]'::jsonb 
                         THEN EXCLUDED.exclusion_notes
                         ELSE icd10_codes.exclusion_notes
                    END,
                    EXCLUDED.exclusion_notes, 
                    icd10_codes.exclusion_notes
                ),
                is_billable = COALESCE(EXCLUDED.is_billable, icd10_codes.is_billable),
                code_length = COALESCE(EXCLUDED.code_length, icd10_codes.code_length),
                parent_code = COALESCE(NULLIF(EXCLUDED.parent_code, ''), icd10_codes.parent_code),
                children_codes = COALESCE(
                    CASE WHEN EXCLUDED.children_codes != '[]'::jsonb 
                         THEN EXCLUDED.children_codes
                         ELSE icd10_codes.children_codes
                    END,
                    EXCLUDED.children_codes, 
                    icd10_codes.children_codes
                ),
                source = COALESCE(NULLIF(EXCLUDED.source, ''), icd10_codes.source),
                search_text = COALESCE(
                    CASE WHEN LENGTH(COALESCE(EXCLUDED.search_text, '')) > LENGTH(COALESCE(icd10_codes.search_text, ''))
                         THEN EXCLUDED.search_text
                         ELSE icd10_codes.search_text
                    END,
                    EXCLUDED.search_text, 
                    icd10_codes.search_text
                ),
                last_updated = NOW()
        """)
        
        # Prepare batch data
        prepared_batch = []
        for code_data in batch:
            prepared_data = self._prepare_code_data(code_data)
            prepared_batch.append(prepared_data)
        
        session.execute(upsert_sql, prepared_batch)

    def _prepare_code_data(self, code_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare code data for database insertion with proper field handling"""
        
        # Handle JSON fields properly
        synonyms = code_data.get("synonyms", [])
        if isinstance(synonyms, list):
            synonyms_json = json.dumps(synonyms)
        else:
            synonyms_json = json.dumps([synonyms] if synonyms else [])
        
        inclusion_notes = code_data.get("inclusion_notes", [])
        if isinstance(inclusion_notes, list):
            inclusion_json = json.dumps(inclusion_notes)
        else:
            inclusion_json = json.dumps([inclusion_notes] if inclusion_notes else [])
        
        exclusion_notes = code_data.get("exclusion_notes", [])
        if isinstance(exclusion_notes, list):
            exclusion_json = json.dumps(exclusion_notes)
        else:
            exclusion_json = json.dumps([exclusion_notes] if exclusion_notes else [])
        
        children_codes = code_data.get("children_codes", [])
        if isinstance(children_codes, list):
            children_json = json.dumps(children_codes)
        else:
            children_json = json.dumps([children_codes] if children_codes else [])
        
        # Safe string handling for None values
        def safe_strip(value, default=""):
            return str(value or default).strip()
        
        return {
            "code": safe_strip(code_data.get("code")),
            "description": safe_strip(code_data.get("description")),
            "category": safe_strip(code_data.get("category")),  # Enhanced category
            "chapter": safe_strip(code_data.get("chapter")),
            "synonyms": synonyms_json,
            "inclusion_notes": inclusion_json,
            "exclusion_notes": exclusion_json,
            "is_billable": code_data.get("is_billable", False),
            "code_length": code_data.get("code_length", 0),
            "parent_code": safe_strip(code_data.get("parent_code")),
            "children_codes": children_json,
            "source": safe_strip(code_data.get("source"), "enhanced_icd10_loader"),
            "search_text": safe_strip(code_data.get("search_text")),
        }

    def get_loading_stats(self) -> Dict[str, int]:
        """Get comprehensive loading statistics"""
        return {
            "processed_count": self.processed_count,
            "inserted_count": self.inserted_count,
            "updated_count": self.updated_count,
        }


def main():
    """Test the ICD-10 database loader"""
    logging.basicConfig(level=logging.INFO)
    
    # Test with sample data
    test_codes = [
        {
            "code": "E11.9",
            "description": "Type 2 diabetes mellitus without complications",
            "chapter": "E00-E89",
            "synonyms": ["Adult-onset diabetes", "NIDDM"],
            "source": "test"
        },
        {
            "code": "I10",
            "description": "Essential (primary) hypertension",
            "chapter": "I00-I99", 
            "synonyms": ["High blood pressure"],
            "source": "test"
        }
    ]
    
    loader = ICD10DatabaseLoader()
    stats = loader.load_codes(test_codes)
    
    print(f"Loading completed: {stats}")


if __name__ == "__main__":
    main()