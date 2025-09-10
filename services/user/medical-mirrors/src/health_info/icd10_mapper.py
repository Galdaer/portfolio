"""
ICD-10 Code Mapper for Health Topics

Maps health topics to relevant ICD-10 diagnostic codes and calculates
clinical relevance scores based on code relationships.
"""

import logging
from typing import Dict, List, Any, Optional
from sqlalchemy import text
import json

logger = logging.getLogger(__name__)


class ICD10Mapper:
    """Map health topics to ICD-10 codes and calculate clinical relevance"""
    
    def __init__(self, db_session):
        """
        Initialize the ICD-10 mapper.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.session = db_session
        self.stats = {
            "topics_mapped": 0,
            "codes_assigned": 0,
            "billing_codes_linked": 0
        }
    
    def map_topic_to_icd10(self, topic: Dict[str, Any], medical_entities: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map a health topic to relevant ICD-10 codes.
        
        Args:
            topic: Health topic dictionary
            medical_entities: Extracted medical entities
            
        Returns:
            Dictionary containing ICD-10 mappings and clinical relevance
        """
        result = {
            "icd10_conditions": [],
            "related_billing_codes": [],
            "clinical_relevance_score": 0.0,
            "topic_classifications": [],
            "risk_factors": []
        }
        
        # Get title and conditions from entities
        title = topic.get("title", "")
        conditions = medical_entities.get("conditions", [])
        
        # Search for ICD-10 codes
        icd10_codes = self._find_icd10_codes(title, conditions)
        result["icd10_conditions"] = icd10_codes
        
        # Find related billing codes
        if icd10_codes:
            billing_codes = self._find_related_billing_codes(icd10_codes)
            result["related_billing_codes"] = billing_codes
        
        # Calculate clinical relevance score
        result["clinical_relevance_score"] = self._calculate_relevance_score(
            icd10_codes, 
            medical_entities
        )
        
        # Classify the topic based on ICD-10 chapters
        result["topic_classifications"] = self._classify_topic(icd10_codes)
        
        # Extract risk factors based on condition type
        result["risk_factors"] = self._identify_risk_factors(title, icd10_codes)
        
        # Update statistics
        self.stats["topics_mapped"] += 1
        self.stats["codes_assigned"] += len(icd10_codes)
        self.stats["billing_codes_linked"] += len(result["related_billing_codes"])
        
        return result
    
    def _find_icd10_codes(self, title: str, conditions: List[Dict]) -> List[Dict[str, Any]]:
        """Find relevant ICD-10 codes for the topic"""
        icd10_codes = []
        seen_codes = set()
        
        # First, search by exact title match
        if title:
            query = text("""
                SELECT code, description, category, chapter, is_billable
                FROM icd10_codes
                WHERE LOWER(description) LIKE :pattern
                   OR LOWER(category) LIKE :pattern
                ORDER BY 
                    CASE 
                        WHEN LOWER(description) = :exact THEN 1
                        WHEN LOWER(description) LIKE :start_pattern THEN 2
                        ELSE 3
                    END,
                    code_length ASC
                LIMIT 5
            """)
            
            result = self.session.execute(query, {
                "pattern": f"%{title.lower()}%",
                "exact": title.lower(),
                "start_pattern": f"{title.lower()}%"
            })
            
            for row in result:
                if row.code not in seen_codes:
                    icd10_codes.append({
                        "code": row.code,
                        "description": row.description,
                        "category": row.category,
                        "chapter": row.chapter,
                        "is_billable": row.is_billable,
                        "match_type": "title",
                        "confidence": 0.9
                    })
                    seen_codes.add(row.code)
        
        # Then search by extracted conditions
        for condition in conditions[:3]:  # Limit to top 3 conditions
            condition_name = condition.get("name", "")
            
            if not condition_name:
                continue
            
            query = text("""
                SELECT code, description, category, chapter, is_billable
                FROM icd10_codes
                WHERE LOWER(description) LIKE :pattern
                LIMIT 3
            """)
            
            result = self.session.execute(
                query,
                {"pattern": f"%{condition_name.lower()}%"}
            )
            
            for row in result:
                if row.code not in seen_codes:
                    icd10_codes.append({
                        "code": row.code,
                        "description": row.description,
                        "category": row.category,
                        "chapter": row.chapter,
                        "is_billable": row.is_billable,
                        "match_type": "condition",
                        "confidence": condition.get("confidence", 0.7)
                    })
                    seen_codes.add(row.code)
        
        return icd10_codes[:10]  # Limit to top 10 codes
    
    def _find_related_billing_codes(self, icd10_codes: List[Dict]) -> List[Dict[str, Any]]:
        """Find billing codes related to the ICD-10 codes"""
        billing_codes = []
        seen_codes = set()
        
        # Get categories from ICD-10 codes
        categories = set()
        for icd10 in icd10_codes:
            if icd10.get("category"):
                # Extract key words from category
                category_words = icd10["category"].lower().split()
                for word in category_words:
                    if len(word) > 4:  # Skip short words
                        categories.add(word)
        
        if not categories:
            return []
        
        # Search for related billing codes
        for category_word in list(categories)[:5]:  # Limit search
            query = text("""
                SELECT code, description, code_type, category
                FROM billing_codes
                WHERE is_active = true
                  AND (LOWER(description) LIKE :pattern
                       OR LOWER(category) LIKE :pattern)
                LIMIT 3
            """)
            
            result = self.session.execute(
                query,
                {"pattern": f"%{category_word}%"}
            )
            
            for row in result:
                if row.code not in seen_codes:
                    billing_codes.append({
                        "code": row.code,
                        "description": row.description,
                        "code_type": row.code_type,
                        "category": row.category
                    })
                    seen_codes.add(row.code)
        
        return billing_codes[:5]  # Limit to top 5
    
    def _calculate_relevance_score(self, icd10_codes: List[Dict], medical_entities: Dict) -> float:
        """Calculate clinical relevance score based on available data"""
        score = 0.0
        
        # Base score from ICD-10 codes
        if icd10_codes:
            # Higher score for billable codes
            billable_count = sum(1 for code in icd10_codes if code.get("is_billable"))
            score += min(0.3, billable_count * 0.1)
            
            # Score based on number of codes
            score += min(0.2, len(icd10_codes) * 0.04)
            
            # Score based on confidence
            avg_confidence = sum(code.get("confidence", 0) for code in icd10_codes) / len(icd10_codes)
            score += avg_confidence * 0.2
        
        # Score from medical entities
        if medical_entities:
            if medical_entities.get("conditions"):
                score += min(0.15, len(medical_entities["conditions"]) * 0.05)
            if medical_entities.get("medications"):
                score += min(0.1, len(medical_entities["medications"]) * 0.05)
            if medical_entities.get("symptoms"):
                score += min(0.05, len(medical_entities["symptoms"]) * 0.01)
        
        return min(1.0, score)  # Cap at 1.0
    
    def _classify_topic(self, icd10_codes: List[Dict]) -> List[str]:
        """Classify topic based on ICD-10 chapters"""
        classifications = set()
        
        # ICD-10 chapter mappings
        chapter_names = {
            "A": "Infectious diseases",
            "B": "Infectious diseases",
            "C": "Neoplasms",
            "D": "Blood and immune disorders",
            "E": "Endocrine and metabolic",
            "F": "Mental and behavioral",
            "G": "Nervous system",
            "H": "Eye and ear",
            "I": "Circulatory system",
            "J": "Respiratory system",
            "K": "Digestive system",
            "L": "Skin and subcutaneous",
            "M": "Musculoskeletal",
            "N": "Genitourinary",
            "O": "Pregnancy and childbirth",
            "P": "Perinatal conditions",
            "Q": "Congenital abnormalities",
            "R": "Symptoms and signs",
            "S": "Injury and poisoning",
            "T": "Injury and poisoning",
            "V": "External causes",
            "W": "External causes",
            "X": "External causes",
            "Y": "External causes",
            "Z": "Health status factors"
        }
        
        for code_info in icd10_codes:
            code = code_info.get("code", "")
            if code:
                chapter = code[0].upper()
                if chapter in chapter_names:
                    classifications.add(chapter_names[chapter])
        
        return list(classifications)
    
    def _identify_risk_factors(self, title: str, icd10_codes: List[Dict]) -> List[str]:
        """Identify risk factors based on condition type"""
        risk_factors = []
        
        title_lower = title.lower()
        
        # Common risk factor patterns
        if "diabetes" in title_lower:
            risk_factors = ["Obesity", "Family history", "Physical inactivity", "Poor diet", "Age over 45"]
        elif "heart" in title_lower or "cardiac" in title_lower:
            risk_factors = ["High blood pressure", "High cholesterol", "Smoking", "Obesity", "Diabetes"]
        elif "cancer" in title_lower:
            risk_factors = ["Smoking", "Family history", "Age", "Environmental exposures", "Poor diet"]
        elif "mental" in title_lower or "depression" in title_lower or "anxiety" in title_lower:
            risk_factors = ["Stress", "Trauma", "Family history", "Substance abuse", "Chronic illness"]
        elif "respiratory" in title_lower or "asthma" in title_lower or "copd" in title_lower:
            risk_factors = ["Smoking", "Air pollution", "Allergies", "Occupational exposures", "Family history"]
        elif "bone" in title_lower or "osteoporosis" in title_lower:
            risk_factors = ["Age", "Low calcium intake", "Vitamin D deficiency", "Physical inactivity", "Smoking"]
        
        # Add general risk factors if none specific
        if not risk_factors and icd10_codes:
            classifications = self._classify_topic(icd10_codes)
            if "Infectious diseases" in classifications:
                risk_factors = ["Weakened immune system", "Poor hygiene", "Close contact with infected", "Travel", "Age"]
            elif "Neoplasms" in classifications:
                risk_factors = ["Age", "Family history", "Environmental factors", "Lifestyle factors", "Previous cancer"]
            else:
                risk_factors = ["Age", "Family history", "Lifestyle factors", "Environmental factors", "Comorbidities"]
        
        return risk_factors[:5]  # Limit to 5 risk factors
    
    def get_statistics(self) -> Dict[str, int]:
        """Get mapping statistics"""
        return self.stats.copy()