"""
ICD-10 Data Enrichment Module for Medical Mirrors System

This module provides comprehensive data enrichment capabilities to address
critical coverage gaps in the ICD-10 codes database:

- Exclusion Notes: 0% coverage (0/46,499) → Target: 80%+
- Inclusion Notes: 0% coverage (0/46,499) → Target: 80%+  
- Synonyms: 0.02% coverage (9/46,499) → Target: 90%+
- Children Codes: 2.28% coverage (1,060/46,499) → Target: 95%+

Architecture follows medical-mirrors service patterns with:
- Database session management integration
- Batch processing for performance
- Error handling and logging
- UPSERT operations for data integrity
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime

from sqlalchemy import text
from database import get_db_session, get_thread_safe_session

logger = logging.getLogger(__name__)


class ICD10ClinicalNotesExtractor:
    """
    Extracts clinical inclusion and exclusion notes from ICD-10 descriptions
    and existing data sources to populate missing clinical guidance.
    
    Uses medical text analysis to identify:
    - Inclusion patterns: "includes", "such as", "with", "encompasses"  
    - Exclusion patterns: "excludes", "not classified here", "except"
    - Clinical conditions and modifiers
    """
    
    def __init__(self):
        self.inclusion_patterns = [
            r'includes?\s*:?\s*([^.;]+)',
            r'such as\s*:?\s*([^.;]+)', 
            r'with\s*:?\s*([^.;]+)',
            r'encompasses?\s*:?\s*([^.;]+)',
            r'involving\s*:?\s*([^.;]+)',
            r'characterized by\s*:?\s*([^.;]+)'
        ]
        
        self.exclusion_patterns = [
            r'excludes?\s*:?\s*([^.;]+)',
            r'not classified here\s*:?\s*([^.;]+)',
            r'except\s*:?\s*([^.;]+)',
            r'not included\s*:?\s*([^.;]+)',
            r'does not include\s*:?\s*([^.;]+)',
            r'not elsewhere classified'
        ]
        
        self.processed_count = 0
        self.notes_extracted = 0

    def extract_clinical_notes(self, code: str, description: str, 
                             existing_data: Optional[Dict] = None) -> Dict[str, List[str]]:
        """
        Extract inclusion and exclusion notes from ICD-10 description.
        
        Args:
            code: ICD-10 code (e.g., "E11.9")
            description: Full description text
            existing_data: Any existing notes data to merge
            
        Returns:
            Dict with 'inclusion_notes' and 'exclusion_notes' lists
        """
        notes = {
            'inclusion_notes': [],
            'exclusion_notes': []
        }
        
        # Merge existing data if available
        if existing_data:
            if 'inclusion_notes' in existing_data:
                notes['inclusion_notes'].extend(existing_data['inclusion_notes'])
            if 'exclusion_notes' in existing_data:
                notes['exclusion_notes'].extend(existing_data['exclusion_notes'])
        
        # Extract inclusion notes
        for pattern in self.inclusion_patterns:
            matches = re.finditer(pattern, description, re.IGNORECASE)
            for match in matches:
                try:
                    note = match.group(1).strip()
                    if note and len(note) > 5:  # Filter meaningful notes
                        notes['inclusion_notes'].append(self._clean_note(note))
                except IndexError:
                    # Pattern doesn't have capture group, skip
                    continue
        
        # Extract exclusion notes  
        for pattern in self.exclusion_patterns:
            matches = re.finditer(pattern, description, re.IGNORECASE)
            for match in matches:
                try:
                    note = match.group(1).strip()
                    if note and len(note) > 5:  # Filter meaningful notes
                        notes['exclusion_notes'].append(self._clean_note(note))
                except IndexError:
                    # Pattern doesn't have capture group, skip
                    continue
        
        # Add code-specific clinical notes from medical knowledge
        clinical_notes = self._get_clinical_notes_by_code(code)
        if clinical_notes:
            notes['inclusion_notes'].extend(clinical_notes.get('inclusion', []))
            notes['exclusion_notes'].extend(clinical_notes.get('exclusion', []))
        
        # Remove duplicates while preserving order
        notes['inclusion_notes'] = list(dict.fromkeys(notes['inclusion_notes']))
        notes['exclusion_notes'] = list(dict.fromkeys(notes['exclusion_notes']))
        
        if notes['inclusion_notes'] or notes['exclusion_notes']:
            self.notes_extracted += 1
            
        return notes
    
    def _clean_note(self, note: str) -> str:
        """Clean and normalize extracted note text"""
        # Remove extra whitespace and normalize
        note = re.sub(r'\s+', ' ', note.strip())
        
        # Remove trailing punctuation for consistency
        note = re.sub(r'[,;:]+$', '', note)
        
        # Capitalize first letter
        if note:
            note = note[0].upper() + note[1:]
            
        return note
    
    def _get_clinical_notes_by_code(self, code: str) -> Optional[Dict[str, List[str]]]:
        """
        Get code-specific clinical notes from medical knowledge base.
        
        This method provides curated clinical guidance for common ICD-10 codes
        to enhance the automated extraction with medical expertise.
        """
        # Common diabetes codes (E10-E14)
        if code.startswith('E1'):
            if 'E10' in code:  # Type 1 diabetes
                return {
                    'inclusion': [
                        'Juvenile onset diabetes',
                        'Insulin-dependent diabetes mellitus (IDDM)',
                        'Brittle diabetes'
                    ],
                    'exclusion': [
                        'Type 2 diabetes mellitus',
                        'Gestational diabetes',
                        'Drug-induced diabetes'
                    ]
                }
            elif 'E11' in code:  # Type 2 diabetes
                return {
                    'inclusion': [
                        'Adult-onset diabetes',
                        'Non-insulin-dependent diabetes mellitus (NIDDM)',
                        'Maturity-onset diabetes'
                    ],
                    'exclusion': [
                        'Type 1 diabetes mellitus',
                        'Gestational diabetes',
                        'Secondary diabetes'
                    ]
                }
        
        # Hypertension codes (I10-I16)
        elif code.startswith('I1'):
            if code == 'I10':  # Essential hypertension
                return {
                    'inclusion': [
                        'Primary hypertension',
                        'Idiopathic hypertension',
                        'High blood pressure of unknown cause'
                    ],
                    'exclusion': [
                        'Secondary hypertension',
                        'Pulmonary hypertension',
                        'Gestational hypertension'
                    ]
                }
        
        # COPD codes (J44)
        elif code.startswith('J44'):
            return {
                'inclusion': [
                    'Chronic bronchitis with airway obstruction',
                    'Emphysema with chronic bronchitis',
                    'Chronic obstructive bronchitis'
                ],
                'exclusion': [
                    'Acute bronchitis',
                    'Asthma',
                    'Bronchiectasis'
                ]
            }
            
        # Fracture codes (S72)
        elif code.startswith('S72'):
            return {
                'inclusion': [
                    'Traumatic fracture',
                    'Closed fracture',
                    'Open fracture'
                ],
                'exclusion': [
                    'Pathological fracture',
                    'Stress fracture',
                    'Old fracture'
                ]
            }
            
        return None

    def batch_extract_notes(self, codes_data: List[Dict]) -> List[Dict]:
        """
        Process multiple ICD-10 codes for clinical notes extraction.
        
        Args:
            codes_data: List of ICD-10 code dictionaries
            
        Returns:
            Enhanced codes data with clinical notes
        """
        logger.info(f"Starting clinical notes extraction for {len(codes_data)} codes")
        
        enhanced_codes = []
        for code_data in codes_data:
            code = code_data.get('code', '')
            description = code_data.get('description', '')
            
            # Extract clinical notes
            notes = self.extract_clinical_notes(
                code, 
                description,
                {
                    'inclusion_notes': code_data.get('inclusion_notes', []),
                    'exclusion_notes': code_data.get('exclusion_notes', [])
                }
            )
            
            # Update code data with extracted notes
            enhanced_code = code_data.copy()
            enhanced_code.update(notes)
            enhanced_codes.append(enhanced_code)
            
            self.processed_count += 1
            
        logger.info(f"Clinical notes extraction completed. "
                   f"Processed: {self.processed_count}, Notes extracted: {self.notes_extracted}")
                   
        return enhanced_codes


class ICD10SynonymGenerator:
    """
    Generates medical synonyms from ICD-10 descriptions using:
    - Medical abbreviation expansion
    - Alternative terminology extraction  
    - Condition variation identification
    - Clinical terminology normalization
    
    Target: Generate 20,000+ synonyms from existing descriptions
    """
    
    def __init__(self):
        # Medical abbreviations and expansions
        self.medical_abbreviations = {
            # Common medical abbreviations
            'DM': 'diabetes mellitus',
            'HTN': 'hypertension', 
            'COPD': 'chronic obstructive pulmonary disease',
            'CHF': 'congestive heart failure',
            'MI': 'myocardial infarction',
            'CVA': 'cerebrovascular accident',
            'DVT': 'deep vein thrombosis',
            'PE': 'pulmonary embolism',
            'GERD': 'gastroesophageal reflux disease',
            'UTI': 'urinary tract infection',
            'URI': 'upper respiratory infection',
            'CAD': 'coronary artery disease',
            'PVD': 'peripheral vascular disease',
            'CKD': 'chronic kidney disease',
            'ESRD': 'end-stage renal disease',
            'IBD': 'inflammatory bowel disease',
            'RA': 'rheumatoid arthritis',
            'SLE': 'systemic lupus erythematosus',
            'ADHD': 'attention deficit hyperactivity disorder',
            'PTSD': 'post-traumatic stress disorder',
            'OCD': 'obsessive-compulsive disorder',
            'CHD': 'coronary heart disease',
            'NIDDM': 'non-insulin dependent diabetes mellitus',
            'IDDM': 'insulin dependent diabetes mellitus'
        }
        
        # Common medical term variations
        self.term_variations = {
            'hypertension': ['high blood pressure', 'elevated blood pressure'],
            'diabetes mellitus': ['diabetes', 'sugar diabetes'],
            'myocardial infarction': ['heart attack', 'MI', 'cardiac infarction'],
            'cerebrovascular accident': ['stroke', 'brain attack', 'CVA'],
            'pneumonia': ['lung infection', 'pulmonary infection'],
            'fracture': ['break', 'broken bone', 'bone fracture'],
            'neoplasm': ['tumor', 'mass', 'growth', 'cancer'],
            'infection': ['infectious disease', 'bacterial infection', 'viral infection'],
            'inflammation': ['inflammatory condition', 'swelling'],
            'disorder': ['disease', 'condition', 'syndrome'],
            'acute': ['sudden onset', 'rapid onset'],
            'chronic': ['long-term', 'persistent', 'ongoing'],
            'essential': ['primary', 'idiopathic'],
            'secondary': ['due to', 'caused by', 'resulting from']
        }
        
        self.processed_count = 0
        self.synonyms_generated = 0

    def generate_synonyms(self, code: str, description: str, 
                         existing_synonyms: Optional[List[str]] = None) -> List[str]:
        """
        Generate medical synonyms for an ICD-10 code description.
        
        Args:
            code: ICD-10 code
            description: ICD-10 description text
            existing_synonyms: Any existing synonyms to preserve
            
        Returns:
            List of generated synonyms
        """
        synonyms = []
        
        # Preserve existing synonyms
        if existing_synonyms:
            synonyms.extend(existing_synonyms)
        
        # Generate synonyms from description
        synonyms.extend(self._extract_synonyms_from_description(description))
        
        # Add abbreviation expansions
        synonyms.extend(self._expand_abbreviations(description))
        
        # Add term variations
        synonyms.extend(self._generate_term_variations(description))
        
        # Add code-specific synonyms
        code_synonyms = self._get_code_specific_synonyms(code)
        if code_synonyms:
            synonyms.extend(code_synonyms)
        
        # Clean and deduplicate
        synonyms = [self._clean_synonym(s) for s in synonyms if s and len(s.strip()) > 2]
        synonyms = list(dict.fromkeys(synonyms))  # Remove duplicates, preserve order
        
        # Filter out the original description to avoid redundancy
        synonyms = [s for s in synonyms if s.lower() != description.lower()]
        
        if len(synonyms) > len(existing_synonyms or []):
            self.synonyms_generated += len(synonyms) - len(existing_synonyms or [])
        
        return synonyms

    def _extract_synonyms_from_description(self, description: str) -> List[str]:
        """Extract synonym patterns from description text"""
        synonyms = []
        
        # Look for parenthetical terms
        parenthetical = re.findall(r'\(([^)]+)\)', description)
        synonyms.extend(parenthetical)
        
        # Look for "also known as" patterns
        aka_patterns = [
            r'also (?:known as|called)\s+([^,.;]+)',
            r'(?:also termed|termed)\s+([^,.;]+)',
            r'(?:synonymous with|synonym of)\s+([^,.;]+)'
        ]
        
        for pattern in aka_patterns:
            matches = re.findall(pattern, description, re.IGNORECASE)
            synonyms.extend(matches)
        
        return synonyms

    def _expand_abbreviations(self, description: str) -> List[str]:
        """Expand medical abbreviations found in description"""
        synonyms = []
        
        for abbrev, expansion in self.medical_abbreviations.items():
            # Case-insensitive search for abbreviation
            pattern = r'\b' + re.escape(abbrev) + r'\b'
            if re.search(pattern, description, re.IGNORECASE):
                synonyms.append(expansion)
                
            # Also check if expansion is in description, add abbreviation
            if expansion.lower() in description.lower():
                synonyms.append(abbrev)
        
        return synonyms

    def _generate_term_variations(self, description: str) -> List[str]:
        """Generate variations of medical terms found in description"""
        synonyms = []
        
        for term, variations in self.term_variations.items():
            if term.lower() in description.lower():
                synonyms.extend(variations)
                
        return synonyms

    def _get_code_specific_synonyms(self, code: str) -> Optional[List[str]]:
        """Get curated synonyms for specific code patterns"""
        # Diabetes codes
        if code.startswith('E10'):
            return ['Type 1 diabetes', 'T1DM', 'Juvenile diabetes', 'IDDM']
        elif code.startswith('E11'):
            return ['Type 2 diabetes', 'T2DM', 'Adult-onset diabetes', 'NIDDM']
        elif code.startswith('E78'):
            return ['Hyperlipidemia', 'High cholesterol', 'Dyslipidemia']
            
        # Hypertension codes
        elif code.startswith('I10'):
            return ['High blood pressure', 'HTN', 'Elevated BP']
        elif code.startswith('I11'):
            return ['Hypertensive heart disease', 'High blood pressure with heart disease']
            
        # Heart disease codes
        elif code.startswith('I25'):
            return ['CAD', 'Coronary heart disease', 'Ischemic heart disease']
        elif code.startswith('I21'):
            return ['Heart attack', 'MI', 'Cardiac infarction']
            
        # Respiratory codes
        elif code.startswith('J44'):
            return ['COPD', 'Chronic bronchitis', 'Emphysema']
        elif code.startswith('J45'):
            return ['Asthma', 'Bronchial asthma', 'Allergic asthma']
            
        # Mental health codes
        elif code.startswith('F32'):
            return ['Major depression', 'Clinical depression', 'Depressive episode']
        elif code.startswith('F41'):
            return ['Anxiety disorder', 'Generalized anxiety', 'Panic disorder']
            
        return None

    def _clean_synonym(self, synonym: str) -> str:
        """Clean and normalize synonym text"""
        # Remove extra whitespace
        synonym = re.sub(r'\s+', ' ', synonym.strip())
        
        # Remove trailing punctuation
        synonym = re.sub(r'[,.;:]+$', '', synonym)
        
        # Capitalize appropriately
        if synonym and not any(c.isupper() for c in synonym):
            # Capitalize first letter if no uppercase letters present
            synonym = synonym[0].upper() + synonym[1:]
            
        return synonym

    def batch_generate_synonyms(self, codes_data: List[Dict]) -> List[Dict]:
        """
        Generate synonyms for multiple ICD-10 codes.
        
        Args:
            codes_data: List of ICD-10 code dictionaries
            
        Returns:
            Enhanced codes data with generated synonyms
        """
        logger.info(f"Starting synonym generation for {len(codes_data)} codes")
        
        enhanced_codes = []
        for code_data in codes_data:
            code = code_data.get('code', '')
            description = code_data.get('description', '')
            existing_synonyms = code_data.get('synonyms', [])
            
            # Generate synonyms
            new_synonyms = self.generate_synonyms(code, description, existing_synonyms)
            
            # Update code data
            enhanced_code = code_data.copy()
            enhanced_code['synonyms'] = new_synonyms
            enhanced_codes.append(enhanced_code)
            
            self.processed_count += 1
            
        logger.info(f"Synonym generation completed. "
                   f"Processed: {self.processed_count}, Synonyms generated: {self.synonyms_generated}")
                   
        return enhanced_codes


class ICD10HierarchyBuilder:
    """
    Builds parent-child relationships from ICD-10 code structure:
    - 3-character codes are parents (e.g., E11)
    - 4+ character codes are children (e.g., E11.9, E11.21) 
    - Handles complex hierarchies (E11.21 → E11.2 → E11)
    - Generates bidirectional relationships
    
    Target: Build 40,000+ parent-child relationships from code structure
    """
    
    def __init__(self):
        self.processed_count = 0
        self.relationships_built = 0
        self.hierarchy_levels_created = 0

    def build_hierarchy(self, codes_data: List[Dict]) -> List[Dict]:
        """
        Build parent-child relationships for ICD-10 codes.
        
        Args:
            codes_data: List of ICD-10 code dictionaries
            
        Returns:
            Enhanced codes with parent-child relationships
        """
        logger.info(f"Building ICD-10 hierarchy for {len(codes_data)} codes")
        
        # Create code lookup for efficient parent finding
        code_lookup = {code_data['code']: code_data for code_data in codes_data}
        
        # Build relationships
        enhanced_codes = []
        for code_data in codes_data:
            code = code_data.get('code', '')
            
            # Find parent and children
            parent_code = self._find_parent_code(code)
            children_codes = self._find_children_codes(code, code_lookup)
            
            # Update code data
            enhanced_code = code_data.copy()
            
            # Set parent if exists and is in our dataset
            if parent_code and parent_code in code_lookup:
                enhanced_code['parent_code'] = parent_code
            
            # Set children if any exist
            existing_children = enhanced_code.get('children_codes', [])
            all_children = list(set(existing_children + children_codes))
            if all_children:
                enhanced_code['children_codes'] = all_children
                
            enhanced_codes.append(enhanced_code)
            
            # Track statistics
            if parent_code and parent_code in code_lookup:
                self.relationships_built += 1
            if children_codes:
                self.relationships_built += len(children_codes)
                
            self.processed_count += 1
            
        logger.info(f"Hierarchy building completed. "
                   f"Processed: {self.processed_count}, Relationships: {self.relationships_built}")
                   
        return enhanced_codes

    def _find_parent_code(self, code: str) -> Optional[str]:
        """
        Find parent code for given ICD-10 code.
        
        Examples:
        - E11.9 → E11 (remove decimal and following)
        - E11.21 → E11.2 (remove last character)
        - S72.001A → S72.001 → S72.00 → S72.0 → S72
        """
        if not code or len(code) <= 3:
            return None  # No parent for 3-character codes
            
        # Remove encounter/laterality indicators (A, D, S, etc.) from end
        clean_code = re.sub(r'[A-Z]$', '', code)
        
        if '.' in clean_code:
            # Handle decimal codes
            parts = clean_code.split('.')
            base = parts[0]
            decimal = parts[1] if len(parts) > 1 else ''
            
            if len(decimal) > 1:
                # E11.21 → E11.2
                return f"{base}.{decimal[:-1]}"
            elif len(decimal) == 1:
                # E11.9 → E11
                return base
        else:
            # Handle non-decimal codes (rare)
            if len(clean_code) > 3:
                return clean_code[:-1]
                
        return None

    def _find_children_codes(self, code: str, code_lookup: Dict[str, Dict]) -> List[str]:
        """
        Find all child codes for given ICD-10 code.
        
        Args:
            code: Parent code to find children for
            code_lookup: Dictionary of all available codes
            
        Returns:
            List of child codes
        """
        children = []
        
        # Clean the parent code
        clean_parent = re.sub(r'[A-Z]$', '', code)
        
        for other_code in code_lookup.keys():
            if other_code == code:
                continue
                
            # Check if other_code is a child of this code
            if self._is_child_of(other_code, clean_parent):
                children.append(other_code)
                
        return children

    def _is_child_of(self, potential_child: str, parent_code: str) -> bool:
        """
        Check if potential_child is a direct child of parent_code.
        
        Examples:
        - E11.9 is child of E11 ✓
        - E11.21 is child of E11.2 ✓
        - E11.21 is NOT direct child of E11 ✗ (E11.2 is intermediate)
        """
        # Clean potential child code
        clean_child = re.sub(r'[A-Z]$', '', potential_child)
        
        # Must start with parent code
        if not clean_child.startswith(parent_code):
            return False
            
        # Extract the part after parent
        suffix = clean_child[len(parent_code):]
        
        if not suffix:
            return False  # Same code
            
        # Check for direct child relationship
        if '.' in parent_code:
            # Parent has decimal (e.g., E11.2)
            # Child should add exactly one character (E11.21, not E11.212)
            return len(suffix) == 1 and suffix.isdigit()
        else:
            # Parent is base code (e.g., E11)
            # Child should be E11.X (single decimal digit)
            return suffix.startswith('.') and len(suffix) == 2 and suffix[1].isdigit()

    def get_hierarchy_statistics(self, codes_data: List[Dict]) -> Dict[str, int]:
        """Get statistics about the hierarchy structure"""
        stats = {
            'total_codes': len(codes_data),
            'parent_codes': 0,
            'child_codes': 0,
            'orphan_codes': 0,
            'max_depth': 0
        }
        
        for code_data in codes_data:
            has_parent = bool(code_data.get('parent_code'))
            has_children = bool(code_data.get('children_codes'))
            
            if has_children:
                stats['parent_codes'] += 1
            if has_parent:
                stats['child_codes'] += 1
            if not has_parent and not has_children:
                stats['orphan_codes'] += 1
                
        return stats


class ICD10DatabaseEnhancer:
    """
    Orchestrates the complete ICD-10 database enhancement process:
    - Coordinates all enhancement components
    - Manages database transactions 
    - Provides progress tracking
    - Handles batch processing for performance
    - Ensures data integrity with UPSERT operations
    """
    
    def __init__(self, batch_size: int = 1000):
        self.batch_size = batch_size
        self.notes_extractor = ICD10ClinicalNotesExtractor()
        self.synonym_generator = ICD10SynonymGenerator()
        self.hierarchy_builder = ICD10HierarchyBuilder()
        
        # Statistics tracking
        self.total_processed = 0
        self.total_enhanced = 0
        self.enhancement_stats = {
            'inclusion_notes_added': 0,
            'exclusion_notes_added': 0,
            'synonyms_added': 0,
            'relationships_added': 0
        }

    def enhance_icd10_database(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Perform comprehensive ICD-10 database enhancement.
        
        Args:
            limit: Optional limit for testing (processes all codes if None)
            
        Returns:
            Enhancement statistics and results
        """
        logger.info("Starting comprehensive ICD-10 database enhancement")
        start_time = datetime.now()
        
        try:
            # Get codes from database
            codes_data = self._fetch_codes_from_database(limit)
            logger.info(f"Fetched {len(codes_data)} codes for enhancement")
            
            if not codes_data:
                logger.warning("No codes found for enhancement")
                return self._generate_results_summary(start_time)
            
            # Process in batches for memory efficiency
            enhanced_batches = []
            for i in range(0, len(codes_data), self.batch_size):
                batch = codes_data[i:i + self.batch_size]
                logger.info(f"Processing batch {i//self.batch_size + 1} "
                           f"({len(batch)} codes)")
                
                enhanced_batch = self._process_batch(batch)
                enhanced_batches.append(enhanced_batch)
                
            # Combine all enhanced batches
            all_enhanced_codes = []
            for batch in enhanced_batches:
                all_enhanced_codes.extend(batch)
                
            # Update database with enhanced data
            self._update_database_with_enhancements(all_enhanced_codes)
            
            # Generate final statistics
            results = self._generate_results_summary(start_time)
            logger.info("ICD-10 database enhancement completed successfully")
            return results
            
        except Exception as e:
            logger.error(f"Error during ICD-10 enhancement: {str(e)}")
            raise

    def _fetch_codes_from_database(self, limit: Optional[int] = None) -> List[Dict]:
        """Fetch ICD-10 codes from database for enhancement"""
        with get_db_session() as db:
            query = """
                SELECT 
                    code,
                    description,
                    category,
                    chapter,
                    synonyms,
                    inclusion_notes,
                    exclusion_notes,
                    parent_code,
                    children_codes,
                    is_billable,
                    source
                FROM icd10_codes 
                ORDER BY code
            """
            
            if limit:
                query += f" LIMIT {limit}"
                
            result = db.execute(text(query)).fetchall()
            
            codes_data = []
            for row in result:
                code_data = {
                    'code': row.code,
                    'description': row.description or '',
                    'category': row.category,
                    'chapter': row.chapter,
                    'synonyms': row.synonyms or [],
                    'inclusion_notes': row.inclusion_notes or [],
                    'exclusion_notes': row.exclusion_notes or [],
                    'parent_code': row.parent_code,
                    'children_codes': row.children_codes or [],
                    'is_billable': row.is_billable,
                    'source': row.source
                }
                codes_data.append(code_data)
                
        return codes_data

    def _process_batch(self, batch: List[Dict]) -> List[Dict]:
        """Process a batch of codes through all enhancement steps"""
        
        # Step 1: Extract clinical notes
        logger.info(f"Extracting clinical notes for batch of {len(batch)} codes")
        batch = self.notes_extractor.batch_extract_notes(batch)
        
        # Step 2: Generate synonyms
        logger.info(f"Generating synonyms for batch of {len(batch)} codes")
        batch = self.synonym_generator.batch_generate_synonyms(batch)
        
        # Step 3: Build hierarchy
        logger.info(f"Building hierarchy for batch of {len(batch)} codes")
        batch = self.hierarchy_builder.build_hierarchy(batch)
        
        return batch

    def _update_database_with_enhancements(self, enhanced_codes: List[Dict]) -> None:
        """Update database with enhanced code data using UPSERT operations"""
        logger.info(f"Updating database with {len(enhanced_codes)} enhanced codes")
        
        with get_db_session() as db:
            try:
                for i, code_data in enumerate(enhanced_codes):
                    if i > 0 and i % 100 == 0:
                        logger.info(f"Updated {i} codes to database")
                        
                    # Use UPSERT to preserve existing data while adding enhancements
                    upsert_query = """
                        INSERT INTO icd10_codes (
                            code, description, category, chapter,
                            synonyms, inclusion_notes, exclusion_notes,
                            parent_code, children_codes, is_billable, source,
                            search_text, last_updated
                        ) VALUES (
                            :code, :description, :category, :chapter,
                            :synonyms, :inclusion_notes, :exclusion_notes,
                            :parent_code, :children_codes, :is_billable, :source,
                            :search_text, NOW()
                        )
                        ON CONFLICT (code) DO UPDATE SET
                            synonyms = CASE 
                                WHEN COALESCE(jsonb_array_length(EXCLUDED.synonyms), 0) > 
                                     COALESCE(jsonb_array_length(icd10_codes.synonyms), 0)
                                THEN EXCLUDED.synonyms 
                                ELSE icd10_codes.synonyms 
                            END,
                            inclusion_notes = CASE 
                                WHEN COALESCE(jsonb_array_length(EXCLUDED.inclusion_notes), 0) > 
                                     COALESCE(jsonb_array_length(icd10_codes.inclusion_notes), 0)
                                THEN EXCLUDED.inclusion_notes 
                                ELSE icd10_codes.inclusion_notes 
                            END,
                            exclusion_notes = CASE 
                                WHEN COALESCE(jsonb_array_length(EXCLUDED.exclusion_notes), 0) > 
                                     COALESCE(jsonb_array_length(icd10_codes.exclusion_notes), 0)
                                THEN EXCLUDED.exclusion_notes 
                                ELSE icd10_codes.exclusion_notes 
                            END,
                            children_codes = CASE 
                                WHEN COALESCE(jsonb_array_length(EXCLUDED.children_codes), 0) > 
                                     COALESCE(jsonb_array_length(icd10_codes.children_codes), 0)
                                THEN EXCLUDED.children_codes 
                                ELSE icd10_codes.children_codes 
                            END,
                            parent_code = COALESCE(EXCLUDED.parent_code, icd10_codes.parent_code),
                            category = COALESCE(EXCLUDED.category, icd10_codes.category),
                            search_text = EXCLUDED.search_text,
                            last_updated = NOW()
                    """
                    
                    # Prepare search text
                    search_components = [
                        code_data['code'],
                        code_data['description'],
                        code_data.get('category', '') or '',
                    ]
                    
                    if code_data.get('synonyms'):
                        search_components.extend(code_data['synonyms'])
                        
                    search_text = ' '.join(filter(None, search_components))
                    
                    # Execute upsert
                    db.execute(text(upsert_query), {
                        'code': code_data['code'],
                        'description': code_data['description'],
                        'category': code_data.get('category'),
                        'chapter': code_data.get('chapter'),
                        'synonyms': json.dumps(code_data.get('synonyms', [])),
                        'inclusion_notes': json.dumps(code_data.get('inclusion_notes', [])),
                        'exclusion_notes': json.dumps(code_data.get('exclusion_notes', [])),
                        'parent_code': code_data.get('parent_code'),
                        'children_codes': json.dumps(code_data.get('children_codes', [])),
                        'is_billable': code_data.get('is_billable'),
                        'source': code_data.get('source', 'enrichment'),
                        'search_text': search_text
                    })
                    
                    self.total_processed += 1
                    
                    # Track enhancement statistics
                    if code_data.get('inclusion_notes'):
                        self.enhancement_stats['inclusion_notes_added'] += 1
                    if code_data.get('exclusion_notes'):
                        self.enhancement_stats['exclusion_notes_added'] += 1
                    if code_data.get('synonyms'):
                        self.enhancement_stats['synonyms_added'] += 1
                    if code_data.get('children_codes') or code_data.get('parent_code'):
                        self.enhancement_stats['relationships_added'] += 1
                        
                db.commit()
                logger.info(f"Successfully updated {len(enhanced_codes)} codes in database")
                
            except Exception as e:
                db.rollback()
                logger.error(f"Database update failed: {str(e)}")
                raise

    def _generate_results_summary(self, start_time: datetime) -> Dict[str, Any]:
        """Generate comprehensive results summary"""
        end_time = datetime.now()
        duration = end_time - start_time
        
        # Get final database statistics
        final_stats = self._get_database_statistics()
        
        summary = {
            'processing_time': str(duration),
            'total_codes_processed': self.total_processed,
            'enhancement_statistics': self.enhancement_stats,
            'database_statistics': final_stats,
            'component_statistics': {
                'notes_extractor': {
                    'processed': self.notes_extractor.processed_count,
                    'notes_extracted': self.notes_extractor.notes_extracted
                },
                'synonym_generator': {
                    'processed': self.synonym_generator.processed_count,
                    'synonyms_generated': self.synonym_generator.synonyms_generated
                },
                'hierarchy_builder': {
                    'processed': self.hierarchy_builder.processed_count,
                    'relationships_built': self.hierarchy_builder.relationships_built
                }
            }
        }
        
        return summary

    def _get_database_statistics(self) -> Dict[str, Any]:
        """Get current database coverage statistics"""
        with get_db_session() as db:
            query = """
                SELECT 
                    COUNT(*) as total_codes,
                    COUNT(CASE WHEN synonyms IS NOT NULL AND jsonb_array_length(synonyms) > 0 THEN 1 END) as has_synonyms,
                    COUNT(CASE WHEN inclusion_notes IS NOT NULL AND jsonb_array_length(inclusion_notes) > 0 THEN 1 END) as has_inclusion_notes,
                    COUNT(CASE WHEN exclusion_notes IS NOT NULL AND jsonb_array_length(exclusion_notes) > 0 THEN 1 END) as has_exclusion_notes,
                    COUNT(CASE WHEN children_codes IS NOT NULL AND jsonb_array_length(children_codes) > 0 THEN 1 END) as has_children_codes,
                    COUNT(CASE WHEN parent_code IS NOT NULL AND parent_code != '' THEN 1 END) as has_parent_code
                FROM icd10_codes
            """
            
            result = db.execute(text(query)).fetchone()
            
            if result:
                total = result.total_codes
                return {
                    'total_codes': total,
                    'synonyms_coverage': {
                        'count': result.has_synonyms,
                        'percentage': (result.has_synonyms / total * 100) if total > 0 else 0
                    },
                    'inclusion_notes_coverage': {
                        'count': result.has_inclusion_notes,
                        'percentage': (result.has_inclusion_notes / total * 100) if total > 0 else 0
                    },
                    'exclusion_notes_coverage': {
                        'count': result.has_exclusion_notes,
                        'percentage': (result.has_exclusion_notes / total * 100) if total > 0 else 0
                    },
                    'children_codes_coverage': {
                        'count': result.has_children_codes,
                        'percentage': (result.has_children_codes / total * 100) if total > 0 else 0
                    },
                    'parent_code_coverage': {
                        'count': result.has_parent_code,
                        'percentage': (result.has_parent_code / total * 100) if total > 0 else 0
                    }
                }
        
        return {}

    def run_enhancement_test(self, limit: int = 100) -> Dict[str, Any]:
        """
        Run enhancement on a small sample for testing.
        
        Args:
            limit: Number of codes to test with
            
        Returns:
            Test results summary
        """
        logger.info(f"Running ICD-10 enhancement test with {limit} codes")
        return self.enhance_icd10_database(limit=limit)


# Convenience function for direct usage
def run_icd10_enhancement(limit: Optional[int] = None, batch_size: int = 1000) -> Dict[str, Any]:
    """
    Run complete ICD-10 database enhancement.
    
    Args:
        limit: Optional limit for testing (None = all codes)
        batch_size: Batch size for processing
        
    Returns:
        Enhancement results summary
    """
    enhancer = ICD10DatabaseEnhancer(batch_size=batch_size)
    return enhancer.enhance_icd10_database(limit=limit)


if __name__ == '__main__':
    # Example usage
    import sys
    
    # Parse command line arguments
    limit = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
            print(f"Running with limit of {limit} codes")
        except ValueError:
            print("Invalid limit argument, processing all codes")
    
    # Run enhancement
    results = run_icd10_enhancement(limit=limit)
    
    # Print results
    print("\n=== ICD-10 ENHANCEMENT RESULTS ===")
    print(f"Processing time: {results['processing_time']}")
    print(f"Codes processed: {results['total_codes_processed']:,}")
    
    print("\nEnhancement Statistics:")
    for key, value in results['enhancement_statistics'].items():
        print(f"  {key}: {value:,}")
        
    print("\nFinal Database Coverage:")
    db_stats = results['database_statistics']
    for field in ['synonyms', 'inclusion_notes', 'exclusion_notes', 'children_codes']:
        coverage = db_stats.get(f'{field}_coverage', {})
        count = coverage.get('count', 0)
        percentage = coverage.get('percentage', 0)
        print(f"  {field}: {count:,} ({percentage:.1f}%)")