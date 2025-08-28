"""
DDInter drug interaction parser
Processes downloaded DDInter CSV files into standardized format
Follows medical-mirrors parser architecture
"""

import csv
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class DDInterParser:
    """Parser for DDInter drug-drug interaction data"""

    def __init__(self):
        self.processed_interactions = 0
        self.validation_errors = 0
        self.duplicates_removed = 0

    def parse_and_validate(self, data_dir: Path) -> dict[str, list[dict]]:
        """Parse and validate DDInter CSV files"""
        logger.info(f"Parsing DDInter data from {data_dir}")
        
        interactions = []
        seen_pairs = set()
        
        # Process all DDInter CSV files
        for csv_file in data_dir.glob("ddinter_downloads_code_*.csv"):
            logger.info(f"Processing {csv_file.name}")
            file_interactions = self._parse_csv_file(csv_file)
            
            # Deduplicate interactions
            for interaction in file_interactions:
                drug1 = interaction.get('drug_1', '').lower().strip()
                drug2 = interaction.get('drug_2', '').lower().strip()
                
                if not drug1 or not drug2:
                    self.validation_errors += 1
                    continue
                
                # Create normalized pair (alphabetical order for consistency)
                pair = tuple(sorted([drug1, drug2]))
                
                if pair in seen_pairs:
                    self.duplicates_removed += 1
                    continue
                
                seen_pairs.add(pair)
                interactions.append(interaction)
                self.processed_interactions += 1
        
        logger.info(f"Processed {self.processed_interactions} interactions, "
                   f"removed {self.duplicates_removed} duplicates, "
                   f"{self.validation_errors} validation errors")
        
        return {"drug_interactions": interactions}

    def _parse_csv_file(self, csv_file: Path) -> list[dict]:
        """Parse a single DDInter CSV file"""
        interactions = []
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row_num, row in enumerate(reader, 1):
                    try:
                        interaction = self._parse_interaction_row(row)
                        if interaction:
                            interactions.append(interaction)
                    except Exception as e:
                        logger.warning(f"Error parsing row {row_num} in {csv_file.name}: {e}")
                        self.validation_errors += 1
                        
        except Exception as e:
            logger.error(f"Error reading CSV file {csv_file}: {e}")
            
        return interactions

    def _parse_interaction_row(self, row: dict) -> dict | None:
        """Parse a single interaction row from DDInter CSV"""
        # DDInter format: DDInterID_A,Drug_A,DDInterID_B,Drug_B,Level
        drug_a = row.get('Drug_A', '').strip()
        drug_b = row.get('Drug_B', '').strip()
        severity = row.get('Level', '').strip()
        
        if not drug_a or not drug_b:
            return None
        
        # Normalize severity levels
        severity_mapping = {
            'Major': 'major',
            'Moderate': 'moderate', 
            'Minor': 'minor'
        }
        normalized_severity = severity_mapping.get(severity, 'unknown')
        
        interaction = {
            'drug_1': drug_a,
            'drug_2': drug_b,
            'severity': normalized_severity,
            'interaction_type': 'drug-drug interaction',
            'mechanism': None,  # Not provided in DDInter CSV format
            'clinical_effect': None,
            'management': None,
            'evidence_level': None,
            'references': None,
            'source': 'DDInter',
            'metadata': {
                'ddinter_id_a': row.get('DDInterID_A', '').strip(),
                'ddinter_id_b': row.get('DDInterID_B', '').strip(),
                'original_severity': severity
            },
            'last_updated': datetime.now().isoformat()
        }
        
        return interaction

    def get_stats(self) -> dict:
        """Get parsing statistics"""
        return {
            'processed_interactions': self.processed_interactions,
            'validation_errors': self.validation_errors,
            'duplicates_removed': self.duplicates_removed
        }