"""
DDInter Static Data Loader
Loads drug-drug interaction data from DDInter static downloads
Supports multiple formats: CSV, TSV, JSON, SQL dumps
"""

import csv
import json
import logging
import sqlite3
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from config import Config

logger = logging.getLogger(__name__)


class DDInterStaticLoader:
    """Load and process DDInter static download files"""

    def __init__(self, config: Config):
        self.config = config
        # Use the enhanced_drug_data/ddinter directory where files were downloaded
        self.data_dir = Path(config.DATA_DIR) / "enhanced_drug_data" / "ddinter"
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def detect_file_format(self, file_path: Path) -> Optional[str]:
        """Auto-detect file format based on extension and content"""
        suffix = file_path.suffix.lower()
        
        format_map = {
            '.csv': 'csv',
            '.tsv': 'tsv',
            '.txt': 'tsv',  # Often tab-separated
            '.json': 'json',
            '.sql': 'sql',
            '.db': 'sqlite',
            '.sqlite': 'sqlite',
            '.sqlite3': 'sqlite',
            '.zip': 'zip',
        }
        
        return format_map.get(suffix)

    def load_from_csv(self, file_path: Path, delimiter: str = ',') -> List[Dict]:
        """Load data from CSV/TSV format"""
        logger.info(f"Loading DDInter data from CSV: {file_path}")
        interactions = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter=delimiter)
                
                for row in reader:
                    # Handle DDInter specific format: DDInterID_A,Drug_A,DDInterID_B,Drug_B,Level
                    if 'Drug_A' in row and 'Drug_B' in row:
                        # DDInter specific format
                        interaction = {
                            'drug_1': row.get('Drug_A', '').strip(),
                            'drug_2': row.get('Drug_B', '').strip(),
                            'interaction_type': 'drug-drug interaction',
                            'severity': row.get('Level', '').strip(),
                            'mechanism': None,  # Not provided in this format
                            'clinical_effect': None,  # Not provided in this format
                            'management': None,  # Not provided in this format
                            'evidence_level': None,  # Not provided in this format
                            'references': None,  # Not provided in this format
                            'ddinter_id_a': row.get('DDInterID_A', '').strip(),
                            'ddinter_id_b': row.get('DDInterID_B', '').strip(),
                            'source': 'DDInter'
                        }
                    else:
                        # Generic format
                        interaction = {
                            'drug_1': row.get('drug_1') or row.get('Drug1') or row.get('drug_name_1'),
                            'drug_2': row.get('drug_2') or row.get('Drug2') or row.get('drug_name_2'),
                            'interaction_type': row.get('interaction_type') or row.get('type'),
                            'severity': row.get('severity') or row.get('level') or row.get('Level'),
                            'mechanism': row.get('mechanism') or row.get('description'),
                            'clinical_effect': row.get('clinical_effect') or row.get('effect'),
                            'management': row.get('management') or row.get('recommendation'),
                            'evidence_level': row.get('evidence_level') or row.get('evidence'),
                            'references': row.get('references') or row.get('pmid'),
                            'source': 'DDInter'
                        }
                    
                    # Only include if we have both drugs
                    if interaction['drug_1'] and interaction['drug_2']:
                        interactions.append(interaction)
                        
        except Exception as e:
            logger.error(f"Error loading CSV file {file_path}: {e}")
            
        logger.info(f"Loaded {len(interactions)} interactions from CSV")
        return interactions

    def load_from_sqlite(self, file_path: Path) -> List[Dict]:
        """Load data from SQLite database"""
        logger.info(f"Loading DDInter data from SQLite: {file_path}")
        interactions = []
        
        try:
            conn = sqlite3.connect(file_path)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            cursor = conn.cursor()
            
            # Try common table names
            table_candidates = [
                'interactions', 'drug_interactions', 'ddi', 
                'ddinter_interactions', 'ddinter_data'
            ]
            
            table_name = None
            for candidate in table_candidates:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (candidate,))
                if cursor.fetchone():
                    table_name = candidate
                    break
            
            if not table_name:
                # List all tables and use the first one
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                if tables:
                    table_name = tables[0][0]
                    logger.info(f"Using table: {table_name}")
                else:
                    raise Exception("No tables found in SQLite database")
            
            # Query all interactions
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            
            for row in rows:
                # Convert sqlite3.Row to dict
                row_dict = dict(row)
                
                # Standardize field names
                interaction = {
                    'drug_1': self._extract_field(row_dict, ['drug_1', 'drug1', 'drug_name_1', 'drugname1']),
                    'drug_2': self._extract_field(row_dict, ['drug_2', 'drug2', 'drug_name_2', 'drugname2']),
                    'interaction_type': self._extract_field(row_dict, ['interaction_type', 'type', 'category']),
                    'severity': self._extract_field(row_dict, ['severity', 'level', 'grade']),
                    'mechanism': self._extract_field(row_dict, ['mechanism', 'description', 'details']),
                    'clinical_effect': self._extract_field(row_dict, ['clinical_effect', 'effect', 'outcome']),
                    'management': self._extract_field(row_dict, ['management', 'recommendation', 'action']),
                    'evidence_level': self._extract_field(row_dict, ['evidence_level', 'evidence', 'quality']),
                    'references': self._extract_field(row_dict, ['references', 'pmid', 'pubmed_id']),
                    'source': 'DDInter'
                }
                
                # Only include if we have both drugs
                if interaction['drug_1'] and interaction['drug_2']:
                    interactions.append(interaction)
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error loading SQLite file {file_path}: {e}")
            
        logger.info(f"Loaded {len(interactions)} interactions from SQLite")
        return interactions

    def load_from_json(self, file_path: Path) -> List[Dict]:
        """Load data from JSON format"""
        logger.info(f"Loading DDInter data from JSON: {file_path}")
        interactions = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Handle different JSON structures
            if isinstance(data, list):
                # Array of interactions
                raw_interactions = data
            elif isinstance(data, dict):
                # Object with interactions in a key
                raw_interactions = (
                    data.get('interactions') or 
                    data.get('data') or 
                    data.get('results') or
                    [data]  # Single interaction
                )
            else:
                raise Exception(f"Unexpected JSON structure: {type(data)}")
            
            for item in raw_interactions:
                if isinstance(item, dict):
                    # Standardize field names
                    interaction = {
                        'drug_1': self._extract_field(item, ['drug_1', 'drug1', 'drug_name_1', 'drugName1']),
                        'drug_2': self._extract_field(item, ['drug_2', 'drug2', 'drug_name_2', 'drugName2']),
                        'interaction_type': self._extract_field(item, ['interaction_type', 'type', 'category']),
                        'severity': self._extract_field(item, ['severity', 'level', 'grade']),
                        'mechanism': self._extract_field(item, ['mechanism', 'description', 'details']),
                        'clinical_effect': self._extract_field(item, ['clinical_effect', 'effect', 'outcome']),
                        'management': self._extract_field(item, ['management', 'recommendation', 'action']),
                        'evidence_level': self._extract_field(item, ['evidence_level', 'evidence', 'quality']),
                        'references': self._extract_field(item, ['references', 'pmid', 'pubmed_id']),
                        'source': 'DDInter'
                    }
                    
                    # Only include if we have both drugs
                    if interaction['drug_1'] and interaction['drug_2']:
                        interactions.append(interaction)
                        
        except Exception as e:
            logger.error(f"Error loading JSON file {file_path}: {e}")
            
        logger.info(f"Loaded {len(interactions)} interactions from JSON")
        return interactions

    def load_from_zip(self, file_path: Path) -> List[Dict]:
        """Extract and load data from ZIP archive"""
        logger.info(f"Loading DDInter data from ZIP: {file_path}")
        interactions = []
        
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                # Extract to temporary directory
                temp_dir = self.data_dir / "temp_extract"
                temp_dir.mkdir(exist_ok=True)
                zip_ref.extractall(temp_dir)
                
                # Process extracted files
                for extracted_file in temp_dir.rglob('*'):
                    if extracted_file.is_file():
                        file_format = self.detect_file_format(extracted_file)
                        if file_format in ['csv', 'tsv', 'json', 'sqlite']:
                            file_interactions = self.load_file(extracted_file)
                            interactions.extend(file_interactions)
                
                # Cleanup
                import shutil
                shutil.rmtree(temp_dir)
                
        except Exception as e:
            logger.error(f"Error loading ZIP file {file_path}: {e}")
            
        logger.info(f"Loaded {len(interactions)} interactions from ZIP")
        return interactions

    def _extract_field(self, data: Dict, field_names: List[str]) -> Optional[str]:
        """Extract field value trying multiple possible field names"""
        for field_name in field_names:
            if field_name in data and data[field_name]:
                return str(data[field_name]).strip()
        return None

    def load_file(self, file_path: Path) -> List[Dict]:
        """Load data from a single file, auto-detecting format"""
        file_format = self.detect_file_format(file_path)
        
        if file_format == 'csv':
            return self.load_from_csv(file_path, delimiter=',')
        elif file_format == 'tsv':
            return self.load_from_csv(file_path, delimiter='\t')
        elif file_format == 'json':
            return self.load_from_json(file_path)
        elif file_format == 'sqlite':
            return self.load_from_sqlite(file_path)
        elif file_format == 'zip':
            return self.load_from_zip(file_path)
        else:
            logger.warning(f"Unsupported file format for {file_path}")
            return []

    def load_all_files(self) -> List[Dict]:
        """Load data from all DDInter files in the data directory"""
        logger.info(f"Loading all DDInter files from {self.data_dir}")
        all_interactions = []
        
        # Look for DDInter download files
        for file_path in self.data_dir.iterdir():
            if file_path.is_file() and not file_path.name.endswith('_state.json'):
                interactions = self.load_file(file_path)
                all_interactions.extend(interactions)
        
        # Remove duplicates based on drug pair
        unique_interactions = []
        seen_pairs = set()
        
        for interaction in all_interactions:
            drug1 = interaction.get('drug_1', '').lower()
            drug2 = interaction.get('drug_2', '').lower()
            
            # Normalize pair (alphabetical order)
            pair = tuple(sorted([drug1, drug2]))
            
            if pair not in seen_pairs and drug1 and drug2:
                seen_pairs.add(pair)
                unique_interactions.append(interaction)
        
        logger.info(f"Loaded {len(unique_interactions)} unique drug interactions from DDInter")
        return unique_interactions

    def save_as_json(self, interactions: List[Dict], output_file: str = "ddinter_interactions.json"):
        """Save processed interactions as JSON"""
        output_path = self.data_dir / output_file
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(interactions, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(interactions)} interactions to {output_path}")
        return str(output_path)


def main():
    """Test the DDInter static loader"""
    from config import Config
    
    config = Config()
    loader = DDInterStaticLoader(config)
    
    # Load all available DDInter data
    interactions = loader.load_all_files()
    
    if interactions:
        # Save as processed JSON
        output_file = loader.save_as_json(interactions)
        print(f"✅ Successfully processed {len(interactions)} DDInter interactions")
        print(f"   Output saved to: {output_file}")
        
        # Show sample interaction
        if interactions:
            sample = interactions[0]
            print(f"\nSample interaction:")
            print(f"  Drug 1: {sample.get('drug_1')}")
            print(f"  Drug 2: {sample.get('drug_2')}")
            print(f"  Severity: {sample.get('severity')}")
            mechanism = sample.get('mechanism') or 'Not provided'
            print(f"  Mechanism: {mechanism[:100] if len(str(mechanism)) > 100 else mechanism}")
    else:
        print("❌ No DDInter data files found")
        print("   Place DDInter download files in:", loader.data_dir)
        print("   Supported formats: CSV, TSV, JSON, SQLite, ZIP")


if __name__ == "__main__":
    main()