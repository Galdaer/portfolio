"""
Drug Information Consolidator

Consolidates the 141K duplicate drug records into ~20K unique generic drugs
with comprehensive data merging and conflict resolution.
"""

import logging
import re
from collections import Counter
from typing import Any

from sqlalchemy import text

from database import DrugInformation, get_db_session

logger = logging.getLogger(__name__)


class DrugConsolidationEngine:
    """Engine for consolidating duplicate drug information records"""

    def __init__(self):
        self.session = get_db_session()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    def normalize_generic_name(self, generic_name: str | None) -> str | None:
        """Normalize generic drug names for consistent grouping"""
        if not generic_name:
            return None

        # Convert to lowercase and strip whitespace
        normalized = generic_name.lower().strip()

        # Remove extra whitespace
        normalized = re.sub(r"\s+", " ", normalized)

        # Handle common variations
        # Remove trailing dosage information in parentheses
        normalized = re.sub(r"\s*\([^)]*mg[^)]*\)$", "", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\s*\([^)]*mcg[^)]*\)$", "", normalized, flags=re.IGNORECASE)

        return normalized if normalized else None

    def get_duplicates_analysis(self) -> dict[str, Any]:
        """Analyze the current duplication situation"""
        result = self.session.execute(text("""
            SELECT
                COUNT(*) as total_records,
                COUNT(DISTINCT LOWER(TRIM(generic_name))) as unique_generics,
                COUNT(*) - COUNT(DISTINCT LOWER(TRIM(generic_name))) as duplicates
            FROM drug_information
            WHERE generic_name IS NOT NULL
        """)).fetchone()

        return {
            "total_records": result[0],
            "unique_generics": result[1],
            "duplicates": result[2],
            "duplication_ratio": result[0] / result[1] if result[1] > 0 else 0,
        }

    def get_generic_drug_groups(self, limit: int | None = None) -> list[tuple[str, int]]:
        """Get list of generic drugs and their record counts"""
        query = """
            SELECT
                LOWER(TRIM(generic_name)) as normalized_generic,
                COUNT(*) as record_count
            FROM drug_information
            WHERE generic_name IS NOT NULL
              AND TRIM(generic_name) != ''
            GROUP BY LOWER(TRIM(generic_name))
            ORDER BY record_count DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        result = self.session.execute(text(query))
        return [(row[0], row[1]) for row in result.fetchall()]

    def get_records_for_generic(self, normalized_generic: str) -> list[DrugInformation]:
        """Get all records for a specific normalized generic name"""
        return self.session.query(DrugInformation).filter(
            text("LOWER(TRIM(generic_name)) = :generic"),
        ).params(generic=normalized_generic).all()

    def consolidate_clinical_text_field(self, records: list[DrugInformation], field_name: str) -> str | None:
        """Consolidate clinical text fields by selecting the longest non-empty value"""
        values = []
        for record in records:
            value = getattr(record, field_name)
            if value and isinstance(value, str) and len(value.strip()) > 0:
                values.append(value.strip())

        if not values:
            return None

        # Return the longest value (most comprehensive information)
        return max(values, key=len)

    def consolidate_array_field(self, records: list[DrugInformation], field_name: str) -> list[str]:
        """Consolidate array fields by merging and deduplicating"""
        all_values = set()

        for record in records:
            value = getattr(record, field_name)
            if value and isinstance(value, list):
                for item in value:
                    if item and isinstance(item, str) and item.strip():
                        # Clean up the value
                        clean_item = item.strip()
                        if clean_item and clean_item.lower() not in ["null", "none", "n/a", ""]:
                            all_values.add(clean_item)

        return sorted(all_values)

    def consolidate_therapeutic_class(self, records: list[DrugInformation]) -> str | None:
        """Consolidate therapeutic class by selecting most frequent non-conflicting value"""
        values = []

        for record in records:
            if record.therapeutic_class and record.therapeutic_class.strip():
                clean_value = record.therapeutic_class.strip()
                if clean_value.lower() not in ["null", "none", "n/a", "unknown"]:
                    values.append(clean_value)

        if not values:
            return None

        # Use most frequent value
        value_counts = Counter(values)
        most_common = value_counts.most_common(1)[0][0]

        # Log conflicts if there are multiple different values
        if len(value_counts) > 1:
            logger.debug(f"Therapeutic class conflict: {dict(value_counts)}, chose: {most_common}")

        return most_common

    def create_formulations_list(self, records: list[DrugInformation]) -> list[dict[str, Any]]:
        """Create structured list of all formulations for this generic"""
        formulations = []
        seen_combinations = set()

        for record in records:
            # Create a unique key for this formulation
            key_parts = [
                record.ndc or "",
                record.strength or "",
                record.dosage_form or "",
                record.route or "",
                record.brand_name or "",
                record.manufacturer or "",
            ]
            key = "|".join(key_parts).lower()

            if key not in seen_combinations:
                formulation = {
                    "ndc": record.ndc,
                    "name": record.name,
                    "brand_name": record.brand_name,
                    "manufacturer": record.manufacturer,
                    "strength": record.strength,
                    "dosage_form": record.dosage_form,
                    "route": record.route,
                    "application_number": record.application_number,
                    "product_number": record.product_number,
                    "approval_date": record.approval_date,
                    "orange_book_code": record.orange_book_code,
                    "reference_listed_drug": record.reference_listed_drug,
                    "data_sources": record.data_sources,
                }

                # Only add if it has meaningful data
                if any([record.strength, record.dosage_form, record.route, record.brand_name]):
                    formulations.append(formulation)
                    seen_combinations.add(key)

        return formulations

    def calculate_confidence_score(self, records: list[DrugInformation], consolidated: dict[str, Any]) -> float:
        """Calculate confidence score based on data completeness and consistency"""
        score = 0.0
        max_score = 10.0

        # Clinical data completeness (40% of score)
        clinical_fields = [
            "indications_and_usage", "mechanism_of_action", "contraindications",
            "warnings", "adverse_reactions", "drug_interactions",
        ]

        clinical_score = 0
        for field in clinical_fields:
            value = consolidated.get(field)
            if value and (isinstance(value, str) and len(value) > 10) or (isinstance(value, list) and value):
                clinical_score += 1

        score += (clinical_score / len(clinical_fields)) * 4.0

        # Formulation data completeness (30% of score)
        formulations = consolidated.get("formulations", [])
        if formulations:
            formulation_score = min(len(formulations) / 5.0, 1.0)  # Cap at 5 formulations
            score += formulation_score * 3.0

        # Data source diversity (20% of score)
        all_sources = set()
        for record in records:
            if record.data_sources:
                all_sources.update(record.data_sources)

        source_diversity = len(all_sources) / 4.0  # Max 4 sources (ndc, orange_book, drugs_fda, labels)
        score += min(source_diversity, 1.0) * 2.0

        # Therapeutic class availability (10% of score)
        if consolidated.get("therapeutic_class"):
            score += 1.0

        return min(score / max_score, 1.0)

    def consolidate_drug_group(self, normalized_generic: str, records: list[DrugInformation]) -> DrugInformation:
        """Consolidate all records for a single generic drug"""
        if not records:
            raise ValueError("No records provided for consolidation")

        # Extract unique values for aggregated fields
        brand_names = set()
        manufacturers = set()
        approval_dates = set()
        orange_book_codes = set()
        application_numbers = set()
        all_data_sources = set()

        for record in records:
            if record.brand_name and record.brand_name.strip():
                brand_names.add(record.brand_name.strip())
            if record.manufacturer and record.manufacturer.strip():
                manufacturers.add(record.manufacturer.strip())
            if record.approval_date and record.approval_date.strip():
                approval_dates.add(record.approval_date.strip())
            if record.orange_book_code and record.orange_book_code.strip():
                orange_book_codes.add(record.orange_book_code.strip())
            if record.application_number and record.application_number.strip():
                application_numbers.add(record.application_number.strip())
            if record.data_sources:
                all_data_sources.update(record.data_sources)

        # Create formulations list
        formulations_list = self.create_formulations_list(records)

        # Create consolidated record
        consolidated_data = {
            "generic_name": normalized_generic,
            "brand_names": sorted(brand_names),
            "manufacturers": sorted(manufacturers),
            "formulations": formulations_list,

            # Consolidated clinical information
            "therapeutic_class": self.consolidate_therapeutic_class(records),
            "indications_and_usage": self.consolidate_clinical_text_field(records, "indications_and_usage"),
            "mechanism_of_action": self.consolidate_clinical_text_field(records, "mechanism_of_action"),
            "contraindications": self.consolidate_array_field(records, "contraindications"),
            "warnings": self.consolidate_array_field(records, "warnings"),
            "precautions": self.consolidate_array_field(records, "precautions"),
            "adverse_reactions": self.consolidate_array_field(records, "adverse_reactions"),

            # Additional clinical fields
            "dosage_and_administration": self.consolidate_clinical_text_field(records, "dosage_and_administration"),
            "pharmacokinetics": self.consolidate_clinical_text_field(records, "pharmacokinetics"),
            "pharmacodynamics": self.consolidate_clinical_text_field(records, "pharmacodynamics"),
            "boxed_warning": self.consolidate_clinical_text_field(records, "boxed_warning"),
            "clinical_studies": self.consolidate_clinical_text_field(records, "clinical_studies"),
            "pediatric_use": self.consolidate_clinical_text_field(records, "pediatric_use"),
            "geriatric_use": self.consolidate_clinical_text_field(records, "geriatric_use"),
            "pregnancy": self.consolidate_clinical_text_field(records, "pregnancy"),
            "nursing_mothers": self.consolidate_clinical_text_field(records, "nursing_mothers"),
            "overdosage": self.consolidate_clinical_text_field(records, "overdosage"),
            "nonclinical_toxicology": self.consolidate_clinical_text_field(records, "nonclinical_toxicology"),

            # Regulatory information
            "approval_dates": sorted(approval_dates),
            "orange_book_codes": sorted(orange_book_codes),
            "application_numbers": sorted(application_numbers),

            # Metadata
            "total_formulations": len(formulations_list),
            "data_sources": sorted(all_data_sources),
        }

        # Calculate confidence score
        consolidated_data["confidence_score"] = self.calculate_confidence_score(records, consolidated_data)

        # Determine if has clinical data
        clinical_fields = ["indications_and_usage", "mechanism_of_action", "contraindications", "warnings"]
        consolidated_data["has_clinical_data"] = any(
            consolidated_data.get(field) for field in clinical_fields
        )

        # Handle drug_interactions (JSON field)
        drug_interactions = {}
        for record in records:
            if record.drug_interactions and isinstance(record.drug_interactions, dict):
                drug_interactions.update(record.drug_interactions)
        consolidated_data["drug_interactions"] = drug_interactions

        return DrugInformation(**consolidated_data)

    def consolidate_all_drugs(self, batch_size: int = 1000, start_offset: int = 0) -> dict[str, Any]:
        """Consolidate all duplicate drug records into consolidated table"""
        stats = self.get_duplicates_analysis()
        logger.info(f"Starting consolidation: {stats['total_records']} records -> {stats['unique_generics']} drugs")

        # Get all generic drug groups
        drug_groups = self.get_generic_drug_groups()
        total_groups = len(drug_groups)

        processed = 0
        errors = 0

        for _i, (normalized_generic, _record_count) in enumerate(drug_groups[start_offset:], start_offset):
            try:
                # Get all records for this generic
                records = self.get_records_for_generic(normalized_generic)

                if not records:
                    logger.warning(f"No records found for generic: {normalized_generic}")
                    continue

                # Check if already consolidated
                existing = self.session.query(DrugInformation).filter_by(generic_name=normalized_generic).first()
                if existing:
                    logger.debug(f"Skipping already consolidated drug: {normalized_generic}")
                    processed += 1
                    continue

                # Consolidate the records
                consolidated_drug = self.consolidate_drug_group(normalized_generic, records)

                # Save to database
                self.session.add(consolidated_drug)

                processed += 1

                if processed % batch_size == 0:
                    self.session.commit()
                    logger.info(f"Processed {processed}/{total_groups} drugs ({processed/total_groups*100:.1f}%)")

            except Exception as e:
                logger.exception(f"Error consolidating {normalized_generic}: {e}")
                errors += 1
                continue

        # Final commit
        self.session.commit()

        result_stats = {
            "original_records": stats["total_records"],
            "unique_generics": stats["unique_generics"],
            "processed": processed,
            "errors": errors,
            "consolidation_ratio": stats["total_records"] / processed if processed > 0 else 0,
        }

        logger.info(f"Consolidation complete: {result_stats}")
        return result_stats

    def recalculate_confidence_scores(self, batch_size: int = 1000, dry_run: bool = False) -> dict[str, Any]:
        """
        Recalculate confidence scores for all existing drug records.
        
        Args:
            batch_size: Number of records to process at once
            dry_run: If True, calculate but don't save to database
            
        Returns:
            Statistics about the update process
        """
        total_drugs = self.session.query(DrugInformation).count()
        logger.info(f"Recalculating confidence scores for {total_drugs} drugs")
        
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
            
            for drug in drugs:
                # Convert drug record to dict for calculation
                drug_dict = {
                    "generic_name": drug.generic_name,
                    "formulations": drug.formulations,
                    "therapeutic_class": drug.therapeutic_class,
                    "indications_and_usage": drug.indications_and_usage,
                    "mechanism_of_action": drug.mechanism_of_action,
                    "contraindications": drug.contraindications,
                    "warnings": drug.warnings,
                    "adverse_reactions": drug.adverse_reactions,
                    "drug_interactions": drug.drug_interactions,
                    "data_sources": drug.data_sources,
                }
                
                # Create a fake records list with the drug's data sources
                fake_records = []
                if drug.data_sources:
                    for source in drug.data_sources:
                        fake_record = type('obj', (object,), {'data_sources': [source]})()
                        fake_records.append(fake_record)
                
                old_score = drug.confidence_score or 0.0
                new_score = self.calculate_confidence_score(fake_records or [drug], drug_dict)
                
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
                    if not dry_run:
                        drug.confidence_score = new_score
                    updated += 1
                
                processed += 1
            
            # Commit batch if not dry run
            if not dry_run and updated > 0:
                self.session.commit()
                logger.info(f"Processed {processed}/{total_drugs} drugs, updated {updated} scores")
            elif dry_run:
                logger.info(f"[DRY RUN] Processed {processed}/{total_drugs} drugs, would update {updated} scores")
        
        # Final commit
        if not dry_run:
            self.session.commit()
        
        result_stats = {
            "total_drugs": total_drugs,
            "processed": processed,
            "updated": updated,
            "score_distribution": score_distribution,
            "dry_run": dry_run
        }
        
        logger.info(f"Confidence score update complete: {result_stats}")
        return result_stats


def run_consolidation(batch_size: int = 1000, start_offset: int = 0) -> dict[str, Any]:
    """Run the drug consolidation process"""
    with DrugConsolidationEngine() as consolidator:
        return consolidator.consolidate_all_drugs(batch_size, start_offset)


def recalculate_confidence_scores(batch_size: int = 1000, dry_run: bool = False) -> dict[str, Any]:
    """Recalculate confidence scores for existing records"""
    with DrugConsolidationEngine() as consolidator:
        return consolidator.recalculate_confidence_scores(batch_size, dry_run)


if __name__ == "__main__":
    import argparse
    
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description='Drug data consolidation and confidence scoring')
    parser.add_argument('--action', type=str, default='consolidate',
                       choices=['consolidate', 'recalculate-scores'],
                       help='Action to perform (default: consolidate)')
    parser.add_argument('--batch-size', type=int, default=1000,
                       help='Number of records to process at once (default: 1000)')
    parser.add_argument('--dry-run', action='store_true',
                       help='For recalculate-scores: calculate but do not save')
    
    args = parser.parse_args()
    
    if args.action == 'consolidate':
        results = run_consolidation(batch_size=args.batch_size)
        print("\n=== Drug Consolidation Results ===")
        for key, value in results.items():
            print(f"{key}: {value}")
    
    elif args.action == 'recalculate-scores':
        results = recalculate_confidence_scores(batch_size=args.batch_size, dry_run=args.dry_run)
        print("\n=== Confidence Score Update Results ===")
        print(f"Total drugs: {results['total_drugs']}")
        print(f"Processed: {results['processed']}")
        print(f"Updated: {results['updated']}")
        print("\nScore Distribution:")
        for range_label, count in results['score_distribution'].items():
            percentage = (count / results['processed'] * 100) if results['processed'] > 0 else 0
            print(f"  {range_label}: {count:,} drugs ({percentage:.1f}%)")
        if results['dry_run']:
            print("\n[DRY RUN] No changes were saved to the database")
