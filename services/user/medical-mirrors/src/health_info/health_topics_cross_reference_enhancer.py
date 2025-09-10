#!/usr/bin/env python3
"""
Health Topics Cross-Reference Enhancement System

This module provides comprehensive cross-referencing between health topics and other medical data tables:
- Cross-references with fda_drugs for drug interactions
- Cross-references with clinical_trials for related studies
- Cross-references with pubmed_articles for research papers
- Cross-references with food_items for dietary considerations
- Cross-references with exercises for exercise recommendations

Uses semantic similarity and keyword matching for intelligent cross-referencing.
"""

import logging
import json
import re
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from sqlalchemy import text
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


# Custom JSON encoder for Decimal types
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


@dataclass
class CrossReferenceResult:
    """Result of cross-referencing operations"""
    drug_interactions: List[Dict[str, Any]] = field(default_factory=list)
    clinical_trials: List[Dict[str, Any]] = field(default_factory=list)
    research_papers: List[Dict[str, Any]] = field(default_factory=list)
    dietary_considerations: List[Dict[str, Any]] = field(default_factory=list)
    exercise_recommendations: List[Dict[str, Any]] = field(default_factory=list)
    monitoring_parameters: List[Dict[str, Any]] = field(default_factory=list)
    patient_resources: List[Dict[str, Any]] = field(default_factory=list)
    provider_notes: Dict[str, Any] = field(default_factory=dict)
    quality_indicators: Dict[str, Any] = field(default_factory=dict)
    evidence_level: str = ""
    confidence_scores: Dict[str, float] = field(default_factory=dict)


class HealthTopicsCrossReferenceEnhancer:
    """
    Enhances health topics with cross-referenced data from other medical tables.
    
    Uses multiple strategies:
    - Keyword matching
    - Medical entity extraction
    - Semantic similarity
    - ICD-10 code relationships
    """
    
    def __init__(self, db_session):
        """
        Initialize the cross-reference enhancer.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.session = db_session
        self.stats = {
            "topics_processed": 0,
            "cross_references_found": 0,
            "errors": 0
        }
    
    def enhance_topic(self, topic: Dict[str, Any]) -> CrossReferenceResult:
        """
        Enhance a single health topic with cross-referenced data.
        
        Args:
            topic: Health topic dictionary with at least topic_id, title, and medical_entities
        
        Returns:
            CrossReferenceResult with all cross-referenced data
        """
        result = CrossReferenceResult()
        
        try:
            # Extract key information from topic
            topic_id = topic.get("topic_id", "")
            title = topic.get("title", "")
            medical_entities = topic.get("medical_entities", {})
            keywords = topic.get("keywords", [])
            
            # Prepare search terms
            search_terms = self._prepare_search_terms(title, medical_entities, keywords)
            
            # Cross-reference with each data source
            result.drug_interactions = self._find_drug_interactions(search_terms, medical_entities)
            result.clinical_trials = self._find_clinical_trials(search_terms, title)
            result.research_papers = self._find_research_papers(search_terms, title)
            result.dietary_considerations = self._find_dietary_considerations(search_terms)
            result.exercise_recommendations = self._find_exercise_recommendations(search_terms)
            
            # Generate derived fields
            result.monitoring_parameters = self._generate_monitoring_parameters(
                result.drug_interactions, medical_entities
            )
            result.patient_resources = self._generate_patient_resources(topic, result)
            result.provider_notes = self._generate_provider_notes(topic, result)
            result.quality_indicators = self._calculate_quality_indicators(result)
            result.evidence_level = self._determine_evidence_level(result)
            
            self.stats["topics_processed"] += 1
            self.stats["cross_references_found"] += sum([
                len(result.drug_interactions),
                len(result.clinical_trials),
                len(result.research_papers),
                len(result.dietary_considerations),
                len(result.exercise_recommendations)
            ])
            
        except Exception as e:
            logger.error(f"Error enhancing topic {topic.get('topic_id')}: {e}")
            self.stats["errors"] += 1
        
        return result
    
    def _prepare_search_terms(self, title: str, medical_entities: Dict, keywords: List) -> Set[str]:
        """Prepare search terms from topic data"""
        terms = set()
        
        # Add title words
        title_words = re.findall(r'\b\w+\b', title.lower())
        terms.update(title_words)
        
        # Add medical entities
        for entity_type, entities in medical_entities.items():
            if isinstance(entities, list):
                for entity in entities:
                    if isinstance(entity, str):
                        terms.add(entity.lower())
                    elif isinstance(entity, dict) and "name" in entity:
                        terms.add(entity["name"].lower())
        
        # Add keywords
        if isinstance(keywords, list):
            terms.update([k.lower() for k in keywords if isinstance(k, str)])
        
        # Remove common stop words
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        terms = terms - stop_words
        
        return terms
    
    def _find_drug_interactions(self, search_terms: Set[str], medical_entities: Dict) -> List[Dict]:
        """Find related drug interactions from fda_drugs table"""
        interactions = []
        
        try:
            # Look for drugs mentioned in medical entities
            drug_names = medical_entities.get("medications", [])
            if isinstance(drug_names, list):
                for drug in drug_names:
                    drug_name = drug if isinstance(drug, str) else drug.get("name", "")
                    if drug_name:
                        # Search for drug in fda_drugs
                        query = text("""
                            SELECT id, generic_name, brand_names, 
                                   drug_interactions, warnings,
                                   contraindications, adverse_reactions
                            FROM drug_information
                            WHERE LOWER(generic_name) LIKE :drug_pattern
                               OR :drug_pattern = ANY(SELECT LOWER(unnest(brand_names)))
                            LIMIT 5
                        """)
                        
                        result = self.session.execute(
                            query, 
                            {"drug_pattern": f"%{drug_name.lower()}%"}
                        )
                        
                        for row in result:
                            brand_names_str = ", ".join(row.brand_names) if row.brand_names else ""
                            interaction_data = {
                                "drug_id": row.id,
                                "drug_name": row.generic_name,
                                "brand_names": brand_names_str,
                                "interactions": row.drug_interactions if row.drug_interactions else {},
                                "warnings": row.warnings if row.warnings else [],
                                "contraindications": row.contraindications if row.contraindications else [],
                                "confidence": 0.9 if drug_name.lower() in row.generic_name.lower() else 0.7
                            }
                            interactions.append(interaction_data)
            
        except Exception as e:
            logger.error(f"Error finding drug interactions: {e}")
            self.session.rollback()
        
        return interactions[:10]  # Limit to top 10 most relevant
    
    def _find_clinical_trials(self, search_terms: Set[str], title: str) -> List[Dict]:
        """Find related clinical trials from clinical_trials table"""
        trials = []
        
        try:
            # Build search query for clinical trials
            # Build search query - escape terms and use OR operator
            # Filter out multi-word phrases as they cause TSQuery syntax errors
            single_words = [term.replace("'", "''") for term in list(search_terms)[:10] if ' ' not in term]
            search_query = " | ".join(single_words) if single_words else "health"  # Use OR for broader matching
            
            query = text("""
                SELECT nct_id, title, status, phase, conditions, 
                       interventions, enrollment
                FROM clinical_trials
                WHERE search_vector @@ to_tsquery('english', :search_query)
                   OR LOWER(title) LIKE :title_pattern
                ORDER BY 
                    ts_rank(search_vector, to_tsquery('english', :search_query)) DESC,
                    CASE status 
                        WHEN 'Recruiting' THEN 1
                        WHEN 'Active, not recruiting' THEN 2
                        WHEN 'Completed' THEN 3
                        ELSE 4
                    END
                LIMIT 10
            """)
            
            result = self.session.execute(
                query,
                {
                    "search_query": search_query,
                    "title_pattern": f"%{title.lower()[:50]}%"
                }
            )
            
            for row in result:
                trial_data = {
                    "nct_id": row.nct_id,
                    "title": row.title,
                    "status": row.status,
                    "phase": row.phase,
                    "conditions": row.conditions if row.conditions else [],
                    "interventions": row.interventions if row.interventions else [],
                    "enrollment": row.enrollment,
                    "relevance_score": self._calculate_relevance(title, row.title)
                }
                trials.append(trial_data)
            
        except Exception as e:
            logger.error(f"Error finding clinical trials: {e}")
            self.session.rollback()
        
        return sorted(trials, key=lambda x: x.get("relevance_score", 0), reverse=True)[:5]
    
    def _find_research_papers(self, search_terms: Set[str], title: str) -> List[Dict]:
        """Find related research papers from pubmed_articles table"""
        papers = []
        
        try:
            # Build search query for research papers - escape and use OR
            # Filter out multi-word phrases as they cause TSQuery syntax errors
            single_words = [term.replace("'", "''") for term in list(search_terms)[:10] if ' ' not in term]
            search_query = " | ".join(single_words) if single_words else "health"
            
            query = text("""
                SELECT pmid, title, abstract, pub_date, 
                       authors, journal, mesh_terms
                FROM pubmed_articles
                WHERE search_vector @@ to_tsquery('english', :search_query)
                   OR LOWER(title) LIKE :title_pattern
                ORDER BY 
                    ts_rank(search_vector, to_tsquery('english', :search_query)) DESC,
                    pub_date DESC
                LIMIT 10
            """)
            
            result = self.session.execute(
                query,
                {
                    "search_query": search_query,
                    "title_pattern": f"%{title.lower()[:50]}%"
                }
            )
            
            for row in result:
                paper_data = {
                    "pmid": row.pmid,
                    "title": row.title,
                    "abstract": row.abstract[:500] if row.abstract else "",
                    "publication_date": str(row.pub_date) if row.pub_date else None,
                    "authors": row.authors if row.authors else [],
                    "journal": row.journal,
                    "relevance_score": self._calculate_relevance(title, row.title)
                }
                papers.append(paper_data)
            
        except Exception as e:
            logger.error(f"Error finding research papers: {e}")
            self.session.rollback()
        
        return sorted(papers, key=lambda x: x.get("relevance_score", 0), reverse=True)[:5]
    
    def _find_dietary_considerations(self, search_terms: Set[str]) -> List[Dict]:
        """Find related dietary recommendations from food_items table"""
        dietary_items = []
        
        try:
            # Focus on nutritional aspects related to health conditions
            query = text("""
                SELECT fdc_id, description, food_category, serving_size,
                       nutrients, nutrition_summary, nutritional_density,
                       dietary_flags, allergens
                FROM food_items
                WHERE search_vector @@ to_tsquery('english', :search_query)
                   OR food_category IN ('Dietary Supplements', 'Medical Food')
                ORDER BY nutritional_density DESC NULLS LAST
                LIMIT 10
            """)
            
            # Use OR operator for better coverage
            # Filter out multi-word phrases as they cause TSQuery syntax errors
            single_words = [term.replace("'", "''") for term in list(search_terms)[:5] if ' ' not in term]
            search_query = " | ".join(single_words) if single_words else "health"
            result = self.session.execute(query, {"search_query": search_query})
            
            for row in result:
                dietary_data = {
                    "fdc_id": row.fdc_id,
                    "name": row.description,
                    "category": row.food_category,
                    "serving_size": row.serving_size,
                    "nutritional_info": row.nutrition_summary if row.nutrition_summary else {},
                    "nutrients": row.nutrients if row.nutrients else {},
                    "dietary_flags": row.dietary_flags if row.dietary_flags else [],
                    "allergens": row.allergens if row.allergens else []
                }
                dietary_items.append(dietary_data)
            
        except Exception as e:
            logger.error(f"Error finding dietary considerations: {e}")
            self.session.rollback()
        
        return dietary_items[:5]
    
    def _find_exercise_recommendations(self, search_terms: Set[str]) -> List[Dict]:
        """Find related exercise recommendations from exercises table"""
        exercises = []
        
        try:
            # Look for exercises related to health conditions
            query = text("""
                SELECT exercise_id, name, exercise_type, body_part,
                       difficulty_level, equipment, target, instructions,
                       calories_estimate, duration_estimate
                FROM exercises
                WHERE search_vector @@ to_tsquery('english', :search_query)
                ORDER BY 
                    CASE difficulty_level
                        WHEN 'Beginner' THEN 1
                        WHEN 'Intermediate' THEN 2
                        WHEN 'Advanced' THEN 3
                        ELSE 4
                    END
                LIMIT 10
            """)
            
            # Use OR operator for better coverage
            # Filter out multi-word phrases as they cause TSQuery syntax errors
            single_words = [term.replace("'", "''") for term in list(search_terms)[:5] if ' ' not in term]
            search_query = " | ".join(single_words) if single_words else "health"
            result = self.session.execute(query, {"search_query": search_query})
            
            for row in result:
                exercise_data = {
                    "exercise_id": row.exercise_id,
                    "name": row.name,
                    "type": row.exercise_type,
                    "body_part": row.body_part,
                    "difficulty": row.difficulty_level,
                    "equipment": row.equipment,
                    "target": row.target,
                    "instructions": row.instructions if row.instructions else [],
                    "calories_estimate": float(row.calories_estimate) if row.calories_estimate is not None else None,
                    "duration_estimate": float(row.duration_estimate) if row.duration_estimate is not None else None
                }
                exercises.append(exercise_data)
            
        except Exception as e:
            logger.error(f"Error finding exercise recommendations: {e}")
            self.session.rollback()
        
        return exercises[:5]
    
    def _generate_monitoring_parameters(self, drug_interactions: List, medical_entities: Dict) -> List[Dict]:
        """Generate clinical monitoring parameters based on drugs and conditions"""
        parameters = []
        
        # Add drug-specific monitoring
        for drug in drug_interactions:
            if drug.get("warnings"):
                parameters.append({
                    "type": "drug_monitoring",
                    "drug": drug.get("drug_name"),
                    "parameters": ["Liver function", "Kidney function", "Blood pressure"],
                    "frequency": "As per prescribing information"
                })
        
        # Add condition-specific monitoring
        conditions = medical_entities.get("conditions", [])
        if "diabetes" in str(conditions).lower():
            parameters.append({
                "type": "condition_monitoring",
                "condition": "Diabetes",
                "parameters": ["HbA1c", "Fasting glucose", "Blood pressure", "Lipid panel"],
                "frequency": "Every 3-6 months"
            })
        
        if "hypertension" in str(conditions).lower():
            parameters.append({
                "type": "condition_monitoring",
                "condition": "Hypertension",
                "parameters": ["Blood pressure", "Kidney function", "Electrolytes"],
                "frequency": "Monthly initially, then every 3 months"
            })
        
        return parameters[:5]
    
    def _generate_patient_resources(self, topic: Dict, result: CrossReferenceResult) -> List[Dict]:
        """Generate patient education resources"""
        resources = []
        
        # Add basic education resource
        resources.append({
            "type": "education",
            "title": f"Understanding {topic.get('title', 'Your Condition')}",
            "content": topic.get("summary", "")[:500],
            "source": "MedlinePlus"
        })
        
        # Add medication guides if drugs are involved
        for drug in result.drug_interactions[:2]:
            resources.append({
                "type": "medication_guide",
                "title": f"About {drug.get('drug_name', 'Your Medication')}",
                "content": "Important information about your medication",
                "warnings": drug.get("warnings", "")[:300] if drug.get("warnings") else ""
            })
        
        # Add lifestyle resources if exercises or diet are involved
        if result.exercise_recommendations:
            resources.append({
                "type": "lifestyle",
                "title": "Exercise Recommendations",
                "content": f"Recommended exercises for your condition",
                "exercises": [e.get("name") for e in result.exercise_recommendations[:3]]
            })
        
        if result.dietary_considerations:
            resources.append({
                "type": "nutrition",
                "title": "Dietary Considerations",
                "content": "Nutritional recommendations for your health",
                "foods": [d.get("name") for d in result.dietary_considerations[:3]]
            })
        
        return resources
    
    def _generate_provider_notes(self, topic: Dict, result: CrossReferenceResult) -> Dict:
        """Generate clinical notes for healthcare providers"""
        notes = {
            "clinical_summary": topic.get("summary", "")[:500],
            "key_considerations": [],
            "evidence_base": {
                "clinical_trials": len(result.clinical_trials),
                "research_papers": len(result.research_papers),
                "last_updated": datetime.now().isoformat()
            }
        }
        
        # Add drug interaction warnings
        if result.drug_interactions:
            notes["key_considerations"].append({
                "type": "drug_interactions",
                "severity": "moderate",
                "details": f"{len(result.drug_interactions)} potential drug interactions identified"
            })
        
        # Add monitoring requirements
        if result.monitoring_parameters:
            notes["key_considerations"].append({
                "type": "monitoring",
                "priority": "high",
                "details": f"{len(result.monitoring_parameters)} monitoring parameters recommended"
            })
        
        # Add contraindications
        for drug in result.drug_interactions:
            if drug.get("contraindications"):
                notes["key_considerations"].append({
                    "type": "contraindication",
                    "drug": drug.get("drug_name"),
                    "details": drug.get("contraindications", "")[:200]
                })
        
        return notes
    
    def _calculate_quality_indicators(self, result: CrossReferenceResult) -> Dict:
        """Calculate quality indicators for the cross-referenced data"""
        indicators = {
            "completeness_score": 0.0,
            "evidence_quality": 0.0,
            "clinical_relevance": 0.0,
            "data_sources": 0,
            "last_updated": datetime.now().isoformat()
        }
        
        # Calculate completeness based on populated fields
        populated_fields = sum([
            1 if result.drug_interactions else 0,
            1 if result.clinical_trials else 0,
            1 if result.research_papers else 0,
            1 if result.dietary_considerations else 0,
            1 if result.exercise_recommendations else 0,
            1 if result.monitoring_parameters else 0
        ])
        indicators["completeness_score"] = populated_fields / 6.0
        
        # Calculate evidence quality based on sources
        evidence_points = (
            len(result.clinical_trials) * 3 +  # Clinical trials weighted highest
            len(result.research_papers) * 2 +   # Research papers medium weight
            len(result.drug_interactions) * 1   # Drug data lower weight
        )
        indicators["evidence_quality"] = min(evidence_points / 20.0, 1.0)
        
        # Clinical relevance based on cross-references found
        total_refs = sum([
            len(result.drug_interactions),
            len(result.clinical_trials),
            len(result.research_papers)
        ])
        indicators["clinical_relevance"] = min(total_refs / 10.0, 1.0)
        
        # Count data sources
        indicators["data_sources"] = sum([
            1 if result.drug_interactions else 0,
            1 if result.clinical_trials else 0,
            1 if result.research_papers else 0,
            1 if result.dietary_considerations else 0,
            1 if result.exercise_recommendations else 0
        ])
        
        return indicators
    
    def _determine_evidence_level(self, result: CrossReferenceResult) -> str:
        """
        Determine evidence level based on available research.
        
        Levels:
        - Level I: Systematic reviews and meta-analyses
        - Level II: Randomized controlled trials
        - Level III: Controlled trials without randomization
        - Level IV: Case-control and cohort studies
        - Level V: Expert opinion
        """
        if len(result.clinical_trials) >= 3:
            # Multiple clinical trials suggest Level II evidence
            return "Level II"
        elif len(result.clinical_trials) >= 1:
            # At least one clinical trial
            return "Level III"
        elif len(result.research_papers) >= 3:
            # Multiple research papers
            return "Level IV"
        elif len(result.research_papers) >= 1:
            # Some research available
            return "Level V"
        else:
            # Limited evidence
            return "Level V"
    
    def _calculate_relevance(self, title1: str, title2: str) -> float:
        """Calculate relevance score between two titles"""
        if not title1 or not title2:
            return 0.0
        
        # Simple sequence matching for now
        return SequenceMatcher(None, title1.lower(), title2.lower()).ratio()
    
    def enhance_all_topics(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Enhance all health topics in the database.
        
        Args:
            limit: Optional limit on number of topics to process
        
        Returns:
            Statistics about the enhancement process
        """
        try:
            # Get topics to enhance
            query = text("""
                SELECT topic_id, title, medical_entities, keywords, summary
                FROM health_topics
                WHERE last_ai_review IS NULL
                   OR last_ai_review < NOW() - INTERVAL '30 days'
                ORDER BY clinical_relevance_score DESC NULLS LAST
                LIMIT :limit
            """)
            
            topics = self.session.execute(
                query, 
                {"limit": limit if limit else 1000}
            ).fetchall()
            
            logger.info(f"Enhancing {len(topics)} health topics with cross-references")
            
            for topic_row in topics:
                topic = {
                    "topic_id": topic_row.topic_id,
                    "title": topic_row.title,
                    "medical_entities": topic_row.medical_entities if topic_row.medical_entities else {},
                    "keywords": topic_row.keywords if topic_row.keywords else [],
                    "summary": topic_row.summary
                }
                
                # Enhance the topic
                result = self.enhance_topic(topic)
                
                # Update database with enhanced data
                update_query = text("""
                    UPDATE health_topics
                    SET drug_interactions = :drug_interactions,
                        clinical_trials = :clinical_trials,
                        research_papers = :research_papers,
                        dietary_considerations = :dietary_considerations,
                        exercise_recommendations = :exercise_recommendations,
                        monitoring_parameters = :monitoring_parameters,
                        patient_resources = :patient_resources,
                        provider_notes = :provider_notes,
                        quality_indicators = :quality_indicators,
                        evidence_level = :evidence_level,
                        last_ai_review = NOW()
                    WHERE topic_id = :topic_id
                """)
                
                self.session.execute(update_query, {
                    "topic_id": topic["topic_id"],
                    "drug_interactions": json.dumps(result.drug_interactions, cls=DecimalEncoder),
                    "clinical_trials": json.dumps(result.clinical_trials, cls=DecimalEncoder),
                    "research_papers": json.dumps(result.research_papers, cls=DecimalEncoder),
                    "dietary_considerations": json.dumps(result.dietary_considerations, cls=DecimalEncoder),
                    "exercise_recommendations": json.dumps(result.exercise_recommendations, cls=DecimalEncoder),
                    "monitoring_parameters": json.dumps(result.monitoring_parameters, cls=DecimalEncoder),
                    "patient_resources": json.dumps(result.patient_resources, cls=DecimalEncoder),
                    "provider_notes": json.dumps(result.provider_notes, cls=DecimalEncoder),
                    "quality_indicators": json.dumps(result.quality_indicators, cls=DecimalEncoder),
                    "evidence_level": result.evidence_level
                })
                
                self.session.commit()
                
                if self.stats["topics_processed"] % 10 == 0:
                    logger.info(f"Progress: {self.stats['topics_processed']} topics enhanced")
            
            logger.info(f"✅ Enhancement complete: {self.stats}")
            
        except Exception as e:
            logger.error(f"Error in batch enhancement: {e}")
            self.session.rollback()
            self.stats["errors"] += 1
        
        return self.stats


if __name__ == "__main__":
    # Test the enhancer
    import sys
    sys.path.append("/home/intelluxe/services/user/medical-mirrors/src")
    from database import get_db_session
    
    logging.basicConfig(level=logging.INFO)
    
    session = get_db_session()
    enhancer = HealthTopicsCrossReferenceEnhancer(session)
    
    # Enhance first 10 topics as a test
    stats = enhancer.enhance_all_topics(limit=10)
    print(f"Enhancement statistics: {stats}")
    
    session.close()