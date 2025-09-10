"""
Medical Entity Extractor for Health Topics

Extracts medical entities (drugs, conditions, symptoms) from health topic text
to enable better cross-referencing with other medical databases.
"""

import re
import logging
from typing import Dict, List, Set, Any
from sqlalchemy import text

logger = logging.getLogger(__name__)


class MedicalEntityExtractor:
    """Extract medical entities from health topic text"""
    
    def __init__(self, db_session=None):
        """
        Initialize the medical entity extractor.
        
        Args:
            db_session: Optional SQLAlchemy session for database lookups
        """
        self.session = db_session
        self.stats = {
            "topics_processed": 0,
            "entities_extracted": 0,
            "drugs_found": 0,
            "conditions_found": 0,
            "symptoms_found": 0
        }
        
        # Common medical terms patterns
        self.drug_patterns = self._build_drug_patterns()
        self.condition_patterns = self._build_condition_patterns()
        self.symptom_keywords = self._build_symptom_keywords()
        
    def _build_drug_patterns(self) -> List[re.Pattern]:
        """Build regex patterns for common drug names and classes"""
        patterns = []
        
        # Common drug suffixes
        drug_suffixes = [
            r'\b\w+(?:cillin|mycin|cycline|azole|statin|pril|sartan|olol|azepam|zepam|codone|morphine|phen|amine|ide|ate)\b',
            r'\b\w+(?:metformin|insulin|aspirin|ibuprofen|acetaminophen|warfarin|heparin|prednisone)\b',
        ]
        
        # Common drug classes
        drug_classes = [
            r'\b(?:antibiotic|antiviral|antifungal|antihistamine|antidepressant|antipsychotic|analgesic|NSAID|steroid|beta[\s-]?blocker|ACE[\s-]?inhibitor|statin|diuretic|bronchodilator|immunosuppressant)s?\b',
            r'\b(?:pain[\s-]?killer|blood[\s-]?thinner|acid[\s-]?reducer|sleep[\s-]?aid)s?\b'
        ]
        
        for pattern in drug_suffixes + drug_classes:
            patterns.append(re.compile(pattern, re.IGNORECASE))
            
        return patterns
    
    def _build_condition_patterns(self) -> List[re.Pattern]:
        """Build regex patterns for medical conditions"""
        patterns = []
        
        # Disease suffixes
        condition_suffixes = [
            r'\b\w+(?:itis|osis|emia|uria|pathy|plasia|trophy|rhea|rrhea|algia|ectomy|ostomy|otomy|plasty)\b',
            r'\b\w+(?:syndrome|disease|disorder|deficiency|infection|cancer|tumor|carcinoma)\b',
        ]
        
        # Common conditions
        common_conditions = [
            r'\b(?:diabetes|hypertension|asthma|COPD|pneumonia|bronchitis|arthritis|osteoporosis)\b',
            r'\b(?:depression|anxiety|bipolar|schizophrenia|ADHD|autism|dementia|alzheimer)\b',
            r'\b(?:heart[\s-]?(?:disease|failure|attack)|stroke|coronary[\s-]?artery|atrial[\s-]?fibrillation)\b',
            r'\b(?:kidney[\s-]?(?:disease|failure)|liver[\s-]?disease|hepatitis|cirrhosis)\b',
            r'\b(?:COVID|influenza|flu|cold|infection|sepsis|UTI|URI)\b'
        ]
        
        for pattern in condition_suffixes + common_conditions:
            patterns.append(re.compile(pattern, re.IGNORECASE))
            
        return patterns
    
    def _build_symptom_keywords(self) -> Set[str]:
        """Build set of common symptom keywords"""
        return {
            'pain', 'ache', 'fever', 'chills', 'fatigue', 'weakness', 'nausea', 'vomiting',
            'diarrhea', 'constipation', 'cough', 'shortness of breath', 'dyspnea', 'chest pain',
            'headache', 'dizziness', 'vertigo', 'rash', 'itching', 'swelling', 'edema',
            'bleeding', 'bruising', 'weight loss', 'weight gain', 'loss of appetite',
            'insomnia', 'anxiety', 'depression', 'confusion', 'memory loss', 'seizure',
            'tremor', 'numbness', 'tingling', 'blurred vision', 'hearing loss',
            'difficulty swallowing', 'difficulty breathing', 'palpitations', 'fainting'
        }
    
    def extract_entities(self, topic: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract medical entities from a health topic.
        
        Args:
            topic: Health topic dictionary with title, summary, etc.
            
        Returns:
            Dictionary of extracted medical entities
        """
        entities = {
            "conditions": [],
            "medications": [],
            "symptoms": [],
            "procedures": [],
            "anatomical_parts": []
        }
        
        # Combine text sources for extraction
        text_sources = [
            topic.get("title", ""),
            topic.get("summary", ""),
            topic.get("category", "")
        ]
        
        # Also check keywords if available
        keywords = topic.get("keywords", [])
        if isinstance(keywords, list):
            text_sources.extend(keywords)
        
        combined_text = " ".join(filter(None, text_sources))
        
        if not combined_text:
            return entities
        
        # Extract conditions
        entities["conditions"] = self._extract_conditions(combined_text, topic.get("title", ""))
        
        # Extract medications/drugs
        entities["medications"] = self._extract_medications(combined_text)
        
        # Extract symptoms
        entities["symptoms"] = self._extract_symptoms(combined_text)
        
        # Extract from title for more specific conditions
        entities["anatomical_parts"] = self._extract_anatomical_parts(combined_text)
        
        # Update statistics
        self.stats["topics_processed"] += 1
        self.stats["conditions_found"] += len(entities["conditions"])
        self.stats["drugs_found"] += len(entities["medications"])
        self.stats["symptoms_found"] += len(entities["symptoms"])
        self.stats["entities_extracted"] += sum(len(v) for v in entities.values())
        
        return entities
    
    def _extract_conditions(self, text: str, title: str) -> List[Dict[str, Any]]:
        """Extract medical conditions from text"""
        conditions = []
        seen = set()
        
        # First, check if the title itself is a condition
        title_lower = title.lower()
        for pattern in self.condition_patterns:
            if pattern.search(title):
                condition_name = title.strip()
                if condition_name.lower() not in seen:
                    conditions.append({
                        "name": condition_name,
                        "source": "title",
                        "confidence": 0.95
                    })
                    seen.add(condition_name.lower())
                break
        
        # Extract from full text
        for pattern in self.condition_patterns:
            matches = pattern.finditer(text)
            for match in matches:
                condition = match.group().strip()
                if condition.lower() not in seen and len(condition) > 3:
                    conditions.append({
                        "name": condition,
                        "source": "text",
                        "confidence": 0.8
                    })
                    seen.add(condition.lower())
        
        # If we have a database session, validate against ICD-10
        if self.session and conditions:
            validated = self._validate_conditions_with_icd10(conditions)
            return validated
        
        return conditions[:10]  # Limit to top 10
    
    def _validate_conditions_with_icd10(self, conditions: List[Dict]) -> List[Dict]:
        """Validate conditions against ICD-10 database"""
        validated = []
        
        for condition in conditions:
            condition_name = condition["name"]
            
            # Search for matching ICD-10 codes
            query = text("""
                SELECT code, description
                FROM icd10_codes
                WHERE LOWER(description) LIKE :pattern
                LIMIT 1
            """)
            
            result = self.session.execute(
                query, 
                {"pattern": f"%{condition_name.lower()}%"}
            ).first()
            
            if result:
                condition["icd10_code"] = result.code
                condition["icd10_description"] = result.description
                condition["confidence"] = min(1.0, condition["confidence"] + 0.1)
            
            validated.append(condition)
        
        return validated
    
    def _extract_medications(self, text: str) -> List[Dict[str, Any]]:
        """Extract medication/drug names from text"""
        medications = []
        seen = set()
        
        for pattern in self.drug_patterns:
            matches = pattern.finditer(text)
            for match in matches:
                drug = match.group().strip()
                if drug.lower() not in seen and len(drug) > 3:
                    medications.append({
                        "name": drug,
                        "confidence": 0.7
                    })
                    seen.add(drug.lower())
        
        # If we have a database session, validate against drug_information
        if self.session and medications:
            validated = self._validate_medications(medications)
            return validated
        
        return medications[:10]  # Limit to top 10
    
    def _validate_medications(self, medications: List[Dict]) -> List[Dict]:
        """Validate medications against drug database"""
        validated = []
        
        for med in medications:
            drug_name = med["name"]
            
            # Search for matching drugs
            query = text("""
                SELECT id, generic_name, brand_names
                FROM drug_information
                WHERE LOWER(generic_name) LIKE :pattern
                   OR :pattern = ANY(LOWER(brand_names::text)::text[])
                LIMIT 1
            """)
            
            result = self.session.execute(
                query,
                {"pattern": f"%{drug_name.lower()}%"}
            ).first()
            
            if result:
                med["drug_id"] = result.id
                med["generic_name"] = result.generic_name
                med["confidence"] = min(1.0, med["confidence"] + 0.2)
            
            validated.append(med)
        
        return validated
    
    def _extract_symptoms(self, text: str) -> List[str]:
        """Extract symptoms from text"""
        symptoms = []
        text_lower = text.lower()
        
        for symptom in self.symptom_keywords:
            if symptom in text_lower:
                symptoms.append(symptom)
        
        return symptoms[:10]  # Limit to top 10
    
    def _extract_anatomical_parts(self, text: str) -> List[str]:
        """Extract anatomical parts/body systems from text"""
        anatomical_keywords = {
            'heart', 'lung', 'liver', 'kidney', 'brain', 'bone', 'muscle', 'skin',
            'blood', 'nerve', 'eye', 'ear', 'nose', 'throat', 'stomach', 'intestine',
            'colon', 'pancreas', 'gallbladder', 'bladder', 'prostate', 'breast',
            'ovary', 'uterus', 'thyroid', 'adrenal', 'pituitary', 'spine', 'joint'
        }
        
        parts = []
        text_lower = text.lower()
        
        for part in anatomical_keywords:
            if part in text_lower:
                parts.append(part)
        
        return parts[:5]  # Limit to top 5
    
    def get_statistics(self) -> Dict[str, int]:
        """Get extraction statistics"""
        return self.stats.copy()