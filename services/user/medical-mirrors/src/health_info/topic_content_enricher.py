"""
Topic Content Enricher for Health Topics

Generates and enriches missing content fields like monitoring parameters,
quality improvements, and related medications based on medical best practices.
"""

import logging
from typing import Dict, List, Any
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class TopicContentEnricher:
    """Enrich health topics with generated medical content"""
    
    def __init__(self):
        """Initialize the topic content enricher"""
        self.stats = {
            "topics_enriched": 0,
            "fields_generated": 0
        }
    
    def enrich_topic(self, 
                     topic: Dict[str, Any], 
                     medical_entities: Dict[str, Any],
                     icd10_mapping: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich a health topic with generated content.
        
        Args:
            topic: Health topic dictionary
            medical_entities: Extracted medical entities
            icd10_mapping: ICD-10 mapping results
            
        Returns:
            Dictionary with enriched content
        """
        enrichment = {
            "related_medications": self._generate_related_medications(
                topic, medical_entities, icd10_mapping
            ),
            "quality_improvements": self._generate_quality_improvements(
                topic, icd10_mapping
            ),
            "monitoring_parameters": self._generate_monitoring_parameters(
                medical_entities, icd10_mapping
            ),
            "enhancement_metadata": self._generate_metadata(topic)
        }
        
        self.stats["topics_enriched"] += 1
        self.stats["fields_generated"] += sum(
            1 for v in enrichment.values() if v
        )
        
        return enrichment
    
    def _generate_related_medications(self, 
                                     topic: Dict[str, Any],
                                     medical_entities: Dict[str, Any],
                                     icd10_mapping: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate list of related medications based on condition"""
        medications = []
        
        # Get medications from entities
        entity_meds = medical_entities.get("medications", [])
        for med in entity_meds:
            medications.append({
                "name": med.get("name"),
                "generic_name": med.get("generic_name"),
                "purpose": "Treatment",
                "confidence": med.get("confidence", 0.7)
            })
        
        # Add common medications based on condition type
        title_lower = topic.get("title", "").lower()
        classifications = icd10_mapping.get("topic_classifications", [])
        
        # Condition-specific medication recommendations
        if "diabetes" in title_lower:
            medications.extend([
                {"name": "Metformin", "purpose": "First-line treatment", "confidence": 0.9},
                {"name": "Insulin", "purpose": "Glucose control", "confidence": 0.8},
                {"name": "GLP-1 agonists", "purpose": "Second-line treatment", "confidence": 0.7}
            ])
        elif "hypertension" in title_lower or "blood pressure" in title_lower:
            medications.extend([
                {"name": "ACE inhibitors", "purpose": "Blood pressure control", "confidence": 0.9},
                {"name": "Beta blockers", "purpose": "Heart rate control", "confidence": 0.8},
                {"name": "Diuretics", "purpose": "Fluid management", "confidence": 0.7}
            ])
        elif "depression" in title_lower or "Mental and behavioral" in classifications:
            medications.extend([
                {"name": "SSRIs", "purpose": "Antidepressant", "confidence": 0.8},
                {"name": "SNRIs", "purpose": "Antidepressant", "confidence": 0.7},
                {"name": "Therapy", "purpose": "Non-pharmacological", "confidence": 0.9}
            ])
        elif "pain" in title_lower:
            medications.extend([
                {"name": "NSAIDs", "purpose": "Anti-inflammatory", "confidence": 0.8},
                {"name": "Acetaminophen", "purpose": "Pain relief", "confidence": 0.8},
                {"name": "Physical therapy", "purpose": "Non-pharmacological", "confidence": 0.7}
            ])
        elif "infection" in title_lower or "Infectious diseases" in classifications:
            medications.extend([
                {"name": "Antibiotics", "purpose": "Bacterial infections", "confidence": 0.8},
                {"name": "Antivirals", "purpose": "Viral infections", "confidence": 0.7},
                {"name": "Supportive care", "purpose": "Symptom management", "confidence": 0.9}
            ])
        
        # Remove duplicates
        seen = set()
        unique_meds = []
        for med in medications:
            med_key = med.get("name", "").lower()
            if med_key and med_key not in seen:
                unique_meds.append(med)
                seen.add(med_key)
        
        return unique_meds[:10]  # Limit to 10 medications
    
    def _generate_quality_improvements(self, 
                                      topic: Dict[str, Any],
                                      icd10_mapping: Dict[str, Any]) -> List[str]:
        """Generate quality improvement recommendations"""
        improvements = []
        
        title_lower = topic.get("title", "").lower()
        classifications = icd10_mapping.get("topic_classifications", [])
        
        # General quality improvements
        improvements.extend([
            "Regular monitoring and follow-up appointments",
            "Patient education and self-management support",
            "Coordination of care between providers",
            "Evidence-based treatment protocols",
            "Quality metrics tracking and reporting"
        ])
        
        # Condition-specific improvements
        if "diabetes" in title_lower:
            improvements.extend([
                "HbA1c monitoring every 3 months",
                "Annual eye and foot examinations",
                "Diabetes self-management education",
                "Continuous glucose monitoring when appropriate"
            ])
        elif "heart" in title_lower or "Circulatory system" in classifications:
            improvements.extend([
                "Cardiac rehabilitation programs",
                "Medication adherence monitoring",
                "Risk factor modification programs",
                "Telemonitoring for high-risk patients"
            ])
        elif "mental" in title_lower or "Mental and behavioral" in classifications:
            improvements.extend([
                "Depression screening tools implementation",
                "Integrated behavioral health services",
                "Crisis intervention protocols",
                "Peer support programs"
            ])
        elif "cancer" in title_lower or "Neoplasms" in classifications:
            improvements.extend([
                "Multidisciplinary tumor boards",
                "Survivorship care planning",
                "Palliative care integration",
                "Clinical trial enrollment opportunities"
            ])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_improvements = []
        for improvement in improvements:
            if improvement not in seen:
                unique_improvements.append(improvement)
                seen.add(improvement)
        
        return unique_improvements[:8]  # Limit to 8 improvements
    
    def _generate_monitoring_parameters(self, 
                                       medical_entities: Dict[str, Any],
                                       icd10_mapping: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate monitoring parameters based on conditions"""
        parameters = []
        
        # Get conditions for targeted monitoring
        conditions = medical_entities.get("conditions", [])
        classifications = icd10_mapping.get("topic_classifications", [])
        
        # Default monitoring for all conditions
        parameters.append({
            "type": "vital_signs",
            "parameters": ["Blood pressure", "Heart rate", "Temperature", "Respiratory rate"],
            "frequency": "Per visit",
            "importance": "high"
        })
        
        # Condition-specific monitoring
        condition_names = " ".join([c.get("name", "") for c in conditions]).lower()
        
        if "diabetes" in condition_names:
            parameters.append({
                "type": "laboratory",
                "parameters": ["HbA1c", "Fasting glucose", "Lipid panel", "Kidney function"],
                "frequency": "Every 3-6 months",
                "importance": "critical"
            })
        
        if "hypertension" in condition_names or "heart" in condition_names:
            parameters.append({
                "type": "cardiovascular",
                "parameters": ["Blood pressure", "ECG", "Echocardiogram", "BNP levels"],
                "frequency": "As indicated",
                "importance": "high"
            })
        
        if "kidney" in condition_names or "renal" in condition_names:
            parameters.append({
                "type": "renal",
                "parameters": ["Creatinine", "GFR", "Urinalysis", "Electrolytes"],
                "frequency": "Every 3 months",
                "importance": "critical"
            })
        
        if "liver" in condition_names or "hepatic" in condition_names:
            parameters.append({
                "type": "hepatic",
                "parameters": ["Liver enzymes", "Bilirubin", "Albumin", "PT/INR"],
                "frequency": "Every 3-6 months",
                "importance": "high"
            })
        
        if "Mental and behavioral" in classifications:
            parameters.append({
                "type": "mental_health",
                "parameters": ["PHQ-9 score", "GAD-7 score", "Medication adherence", "Side effects"],
                "frequency": "Each visit",
                "importance": "high"
            })
        
        if "Neoplasms" in classifications:
            parameters.append({
                "type": "oncology",
                "parameters": ["Tumor markers", "Imaging studies", "Blood counts", "Performance status"],
                "frequency": "Per protocol",
                "importance": "critical"
            })
        
        return parameters[:5]  # Limit to 5 parameter sets
    
    def _generate_metadata(self, topic: Dict[str, Any]) -> Dict[str, Any]:
        """Generate enhancement metadata"""
        return {
            "enhancement_version": "2.0",
            "enhancement_date": datetime.now().isoformat(),
            "enhancement_source": "medical_entity_extraction_and_mapping",
            "topic_source": topic.get("source", "medlineplus"),
            "confidence_level": "moderate",
            "requires_review": True,
            "enhancement_methods": [
                "entity_extraction",
                "icd10_mapping",
                "content_generation",
                "cross_referencing"
            ]
        }
    
    def get_statistics(self) -> Dict[str, int]:
        """Get enrichment statistics"""
        return self.stats.copy()