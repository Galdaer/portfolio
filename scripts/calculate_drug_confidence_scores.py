#!/usr/bin/env python3
"""
Calculate and update confidence scores for all drugs in the database.

The confidence score is a quality metric (0.0-1.0) based on:
- Clinical data completeness (40%)
- Formulation data completeness (30%)
- Data source diversity (20%)
- Therapeutic class availability (10%)
"""

import sys
import os
from typing import Dict, Any, List
import logging
from datetime import datetime
import json

# Add the medical-mirrors src directory to path
sys.path.insert(0, '/home/intelluxe/services/user/medical-mirrors/src')

from sqlalchemy import create_engine, text, update
from sqlalchemy.orm import sessionmaker
from database import DrugInformation, get_database_url

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DrugConfidenceCalculator:
    """Calculate confidence scores for drug records"""
    
    def __init__(self):
        """Initialize database connection"""
        self.engine = create_engine(
            get_database_url(),
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            echo=False
        )
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
    def calculate_confidence_score(self, drug: DrugInformation) -> float:
        """
        Calculate confidence score for a single drug record.
        
        Score breakdown:
        - Clinical data completeness: 40% (4.0 points)
        - Formulation data: 30% (3.0 points)
        - Data source diversity: 20% (2.0 points)
        - Therapeutic class: 10% (1.0 point)
        Total: 10.0 points, normalized to 0.0-1.0
        """
        score = 0.0
        max_score = 10.0
        
        # 1. Clinical data completeness (40% of score)
        clinical_fields = {
            'indications_and_usage': drug.indications_and_usage,
            'mechanism_of_action': drug.mechanism_of_action,
            'contraindications': drug.contraindications,
            'warnings': drug.warnings,
            'adverse_reactions': drug.adverse_reactions,
            'drug_interactions': drug.drug_interactions,
        }
        
        clinical_score = 0
        for field_name, value in clinical_fields.items():
            if value:
                if isinstance(value, str) and len(value) > 10:
                    clinical_score += 1
                elif isinstance(value, list) and len(value) > 0:
                    clinical_score += 1
                elif isinstance(value, dict) and len(value) > 0:
                    clinical_score += 1
        
        score += (clinical_score / len(clinical_fields)) * 4.0
        
        # 2. Formulation data completeness (30% of score)
        if drug.formulations:
            try:
                formulations = drug.formulations if isinstance(drug.formulations, list) else json.loads(drug.formulations)
                if formulations:
                    # Score based on number of formulations (cap at 5 for full points)
                    formulation_score = min(len(formulations) / 5.0, 1.0)
                    score += formulation_score * 3.0
            except (json.JSONDecodeError, TypeError):
                pass
        
        # 3. Data source diversity (20% of score)
        if drug.data_sources:
            # Common sources: ndc_directory, orange_book, drugs_fda, drug_labels, drugcentral
            unique_sources = set(drug.data_sources) if drug.data_sources else set()
            # Maximum expected sources is about 5
            source_diversity = min(len(unique_sources) / 5.0, 1.0)
            score += source_diversity * 2.0
        
        # 4. Therapeutic class availability (10% of score)
        if drug.therapeutic_class and len(str(drug.therapeutic_class)) > 2:
            score += 1.0
        
        # Additional bonus for comprehensive clinical data
        bonus_fields = [
            drug.pharmacokinetics,
            drug.pharmacodynamics,
            drug.clinical_studies,
            drug.boxed_warning
        ]
        
        bonus_score = sum(1 for field in bonus_fields if field and len(str(field)) > 10)
        if bonus_score > 0:
            score += min(bonus_score * 0.25, 1.0)  # Up to 1.0 bonus points
        
        # Normalize to 0.0-1.0 range
        return min(score / max_score, 1.0)
    
    def update_confidence_scores(self, batch_size: int = 1000, dry_run: bool = False):
        """
        Update confidence scores for all drugs in batches.
        
        Args:
            batch_size: Number of records to process at once
            dry_run: If True, calculate but don't save to database
        """
        total_drugs = self.session.query(DrugInformation).count()
        logger.info(f"Total drugs to process: {total_drugs}")
        
        processed = 0
        updated = 0
        score_distribution = {
            '0.0-0.2': 0,
            '0.2-0.4': 0,
            '0.4-0.6': 0,
            '0.6-0.8': 0,
            '0.8-1.0': 0
        }
        
        # Process in batches
        for offset in range(0, total_drugs, batch_size):
            drugs = self.session.query(DrugInformation).offset(offset).limit(batch_size).all()
            
            batch_updates = []
            for drug in drugs:
                old_score = drug.confidence_score or 0.0
                new_score = self.calculate_confidence_score(drug)
                
                # Track distribution
                if new_score <= 0.2:
                    score_distribution['0.0-0.2'] += 1
                elif new_score <= 0.4:
                    score_distribution['0.2-0.4'] += 1
                elif new_score <= 0.6:
                    score_distribution['0.4-0.6'] += 1
                elif new_score <= 0.8:
                    score_distribution['0.6-0.8'] += 1
                else:
                    score_distribution['0.8-1.0'] += 1
                
                if abs(new_score - old_score) > 0.001:  # Only update if changed
                    batch_updates.append({
                        'id': drug.id,
                        'confidence_score': new_score
                    })
                    updated += 1
                
                processed += 1
            
            # Apply updates if not dry run
            if batch_updates and not dry_run:
                stmt = update(DrugInformation).where(
                    DrugInformation.id == text(':id')
                ).values(confidence_score=text(':confidence_score'))
                
                for update_data in batch_updates:
                    self.session.execute(stmt, update_data)
                
                self.session.commit()
                logger.info(f"Processed {processed}/{total_drugs} drugs, updated {len(batch_updates)} scores")
            elif dry_run:
                logger.info(f"[DRY RUN] Processed {processed}/{total_drugs} drugs, would update {len(batch_updates)} scores")
        
        # Print summary
        logger.info("\n" + "="*50)
        logger.info("CONFIDENCE SCORE UPDATE SUMMARY")
        logger.info("="*50)
        logger.info(f"Total drugs processed: {processed}")
        logger.info(f"Drugs with updated scores: {updated}")
        logger.info("\nScore Distribution:")
        for range_label, count in score_distribution.items():
            percentage = (count / processed * 100) if processed > 0 else 0
            logger.info(f"  {range_label}: {count:,} drugs ({percentage:.1f}%)")
        
        if dry_run:
            logger.info("\n[DRY RUN] No changes were saved to the database")
        else:
            logger.info("\n✅ Confidence scores successfully updated in database")
    
    def show_examples(self, limit: int = 10):
        """Show example drugs with their calculated confidence scores"""
        logger.info("\nExample confidence score calculations:")
        logger.info("-" * 80)
        
        # Get a sample of drugs with varying data completeness
        sample_query = """
            SELECT * FROM drug_information 
            WHERE has_clinical_data = true 
            ORDER BY RANDOM() 
            LIMIT :limit
        """
        
        drugs = self.session.execute(text(sample_query), {'limit': limit}).fetchall()
        
        for drug in drugs:
            drug_obj = self.session.query(DrugInformation).filter_by(id=drug.id).first()
            score = self.calculate_confidence_score(drug_obj)
            
            print(f"\nDrug: {drug.generic_name}")
            print(f"  Current Score: {drug.confidence_score:.3f}")
            print(f"  New Score: {score:.3f}")
            print(f"  Data Sources: {len(drug.data_sources) if drug.data_sources else 0}")
            print(f"  Has Clinical Data: {drug.has_clinical_data}")
            print(f"  Has Therapeutic Class: {'Yes' if drug.therapeutic_class else 'No'}")
            
            # Show what contributes to the score
            clinical_count = sum([
                1 for field in [drug.indications_and_usage, drug.mechanism_of_action,
                               drug.contraindications, drug.warnings, drug.adverse_reactions]
                if field and ((isinstance(field, str) and len(field) > 10) or 
                             (isinstance(field, list) and len(field) > 0))
            ])
            print(f"  Clinical Fields Populated: {clinical_count}/6")
    
    def close(self):
        """Close database connection"""
        self.session.close()
        self.engine.dispose()


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Calculate and update drug confidence scores')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Calculate scores without updating database')
    parser.add_argument('--batch-size', type=int, default=1000,
                       help='Number of records to process at once (default: 1000)')
    parser.add_argument('--show-examples', action='store_true',
                       help='Show example calculations before processing')
    parser.add_argument('--examples-only', action='store_true',
                       help='Only show examples, do not update scores')
    
    args = parser.parse_args()
    
    calculator = DrugConfidenceCalculator()
    
    try:
        if args.show_examples or args.examples_only:
            calculator.show_examples()
        
        if not args.examples_only:
            logger.info(f"\nStarting confidence score calculation...")
            logger.info(f"Batch size: {args.batch_size}")
            logger.info(f"Dry run: {args.dry_run}")
            
            start_time = datetime.now()
            calculator.update_confidence_scores(
                batch_size=args.batch_size,
                dry_run=args.dry_run
            )
            
            elapsed = datetime.now() - start_time
            logger.info(f"\nTotal processing time: {elapsed}")
    
    finally:
        calculator.close()


if __name__ == '__main__':
    main()