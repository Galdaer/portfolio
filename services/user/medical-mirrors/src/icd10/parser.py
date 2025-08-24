"""
ICD-10 codes parser and data processor with enhanced validation and smart download integration
"""

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class ICD10Parser:
    """Parser for ICD-10 diagnostic codes data"""

    def __init__(self):
        self.processed_codes = 0
        self.validation_errors = 0
        self.duplicates_removed = 0
        self.hierarchy_built = 0
        self.source_conflicts_resolved = 0

        # Chapter mapping for enhanced validation
        self.chapter_ranges = {
            "A": ("A00", "B99"), "B": ("A00", "B99"),  # Infectious diseases
            "C": ("C00", "D49"), "D": ("C00", "D49"),  # Neoplasms/Blood disorders
            "E": ("E00", "E89"),                        # Endocrine diseases
            "F": ("F01", "F99"),                        # Mental disorders
            "G": ("G00", "G99"),                        # Nervous system
            "H": ("H00", "H95"),                        # Eye/Ear diseases
            "I": ("I00", "I99"),                        # Circulatory system
            "J": ("J00", "J99"),                        # Respiratory system
            "K": ("K00", "K95"),                        # Digestive system
            "L": ("L00", "L99"),                        # Skin diseases
            "M": ("M00", "M99"),                        # Musculoskeletal system
            "N": ("N00", "N99"),                        # Genitourinary system
            "O": ("O00", "O9A"),                        # Pregnancy conditions
            "P": ("P00", "P96"),                        # Perinatal conditions
            "Q": ("Q00", "Q99"),                        # Congenital malformations
            "R": ("R00", "R99"),                        # Symptoms and signs
            "S": ("S00", "T88"), "T": ("S00", "T88"),   # Injuries
            "V": ("V00", "Y99"), "W": ("V00", "Y99"),   # External causes
            "X": ("V00", "Y99"), "Y": ("V00", "Y99"),
            "Z": ("Z00", "Z99"),                        # Health status factors
        }

    def parse_and_validate(self, raw_codes: list[dict]) -> list[dict]:
        """Parse and validate ICD-10 codes data with smart conflict resolution"""
        logger.info(f"Parsing and validating {len(raw_codes)} ICD-10 codes")

        validated_codes = []
        seen_codes: dict[str, dict] = {}  # Store best version of each code

        for raw_code in raw_codes:
            try:
                parsed_code = self._parse_single_code(raw_code)

                if parsed_code and self._validate_code(parsed_code):
                    code_key = parsed_code["code"]

                    if code_key not in seen_codes:
                        # New code
                        seen_codes[code_key] = parsed_code
                        self.processed_codes += 1
                    else:
                        # Duplicate - resolve conflict intelligently
                        existing_code = seen_codes[code_key]
                        resolved_code = self._resolve_code_conflict(existing_code, parsed_code)
                        seen_codes[code_key] = resolved_code
                        self.duplicates_removed += 1
                        self.source_conflicts_resolved += 1
                else:
                    self.validation_errors += 1

            except Exception as e:
                logger.exception(f"Error parsing ICD-10 code {raw_code.get('code', 'unknown')}: {e}")
                self.validation_errors += 1
                continue

        # Convert to list and build hierarchy
        validated_codes = list(seen_codes.values())
        validated_codes = self.build_hierarchy(validated_codes)

        logger.info(f"Parsed {len(validated_codes)} valid ICD-10 codes, "
                   f"removed {self.duplicates_removed} duplicates, "
                   f"resolved {self.source_conflicts_resolved} source conflicts, "
                   f"rejected {self.validation_errors} invalid codes")

        return validated_codes

    def _resolve_code_conflict(self, existing: dict, new: dict) -> dict:
        """Intelligently resolve conflicts between duplicate codes from different sources"""
        # Source priority (official sources take precedence)
        source_priority = {
            "cms_icd10_cm_2024": 10,
            "cms_icd10_cm_tabular": 9,
            "cms_direct": 8,
            "who_icd10_2019": 7,
            "who_icd11_foundation": 6,
            "nlm_clinical_tables": 5,
            "nlm_api": 4,
            "fallback": 1,
            "unknown": 0,
        }

        existing_priority = source_priority.get(existing.get("source", "unknown"), 0)
        new_priority = source_priority.get(new.get("source", "unknown"), 0)

        # Use higher priority source as base
        if new_priority > existing_priority:
            base_code = new.copy()
            merge_from = existing
        else:
            base_code = existing.copy()
            merge_from = new

        # Merge additional information from lower priority source
        # Prefer longer/more detailed descriptions
        if len(merge_from.get("description", "")) > len(base_code.get("description", "")):
            base_code["description"] = merge_from["description"]

        # Merge synonyms
        existing_synonyms = set(base_code.get("synonyms", []))
        new_synonyms = set(merge_from.get("synonyms", []))
        base_code["synonyms"] = list(existing_synonyms.union(new_synonyms))

        # Merge inclusion/exclusion notes
        existing_inc = set(base_code.get("inclusion_notes", []))
        new_inc = set(merge_from.get("inclusion_notes", []))
        base_code["inclusion_notes"] = list(existing_inc.union(new_inc))

        existing_exc = set(base_code.get("exclusion_notes", []))
        new_exc = set(merge_from.get("exclusion_notes", []))
        base_code["exclusion_notes"] = list(existing_exc.union(new_exc))

        # Use more specific category if available
        if not base_code.get("category") and merge_from.get("category"):
            base_code["category"] = merge_from["category"]

        # Update search text with merged information
        base_code["search_text"] = self._create_search_text(
            base_code["code"],
            base_code["description"],
            base_code["synonyms"],
        )

        # Track source merge
        sources = [base_code.get("source", "unknown")]
        if merge_from.get("source") not in sources:
            sources.append(merge_from.get("source", "unknown"))
        base_code["merged_sources"] = sources

        return base_code

    def _parse_single_code(self, raw_code: dict) -> dict | None:
        """Parse a single ICD-10 code"""
        try:
            code = raw_code.get("code", "").strip()
            description = raw_code.get("description", "").strip()

            if not code or not description:
                return None

            # Normalize code format
            normalized_code = self._normalize_code(code)

            # Determine chapter if not provided
            chapter = raw_code.get("chapter", "").strip()
            if not chapter:
                chapter = self._determine_chapter_from_code(normalized_code)

            # Extract additional metadata
            parsed_code = {
                "code": normalized_code,
                "description": description,
                "category": raw_code.get("category", "").strip(),
                "chapter": chapter,
                "synonyms": self._parse_synonyms(raw_code.get("synonyms", [])),
                "inclusion_notes": self._extract_inclusion_notes(description),
                "exclusion_notes": self._extract_exclusion_notes(description),
                "is_billable": self._determine_billability(normalized_code),
                "code_length": len(normalized_code.replace(".", "")),
                "parent_code": self._get_parent_code(normalized_code),
                "children_codes": [],  # Will be populated later
                "source": raw_code.get("source", "unknown"),
                "last_updated": datetime.now().isoformat(),
                "search_text": self._create_search_text(normalized_code, description, raw_code.get("synonyms", [])),
            }

            # Add any additional fields from source
            for key, value in raw_code.items():
                if key not in parsed_code and value is not None:
                    parsed_code[key] = value

            return parsed_code


        except Exception as e:
            logger.exception(f"Error parsing single code: {e}")
            return None

    def _normalize_code(self, code: str) -> str:
        """Normalize ICD-10 code format"""
        # Remove whitespace and convert to uppercase
        normalized = code.strip().upper()

        # Ensure proper format (e.g., E11.9 not E119)
        if len(normalized) > 3 and "." not in normalized:
            normalized = normalized[:3] + "." + normalized[3:]

        return normalized

    def _determine_chapter_from_code(self, code: str) -> str:
        """Determine ICD-10 chapter range from code"""
        if not code:
            return ""

        first_char = code[0].upper()
        chapter_range = self.chapter_ranges.get(first_char)

        if chapter_range:
            return f"{chapter_range[0]}-{chapter_range[1]}"

        return ""

    def _parse_synonyms(self, synonyms) -> list[str]:
        """Parse synonyms into a clean list"""
        if not synonyms:
            return []

        if isinstance(synonyms, str):
            # Split on common delimiters
            synonym_list = synonyms.replace(";", ",").split(",")
        elif isinstance(synonyms, list):
            synonym_list = synonyms
        else:
            return []

        # Clean and filter synonyms
        clean_synonyms = []
        for synonym in synonym_list:
            if isinstance(synonym, str):
                clean = synonym.strip()
                if clean and len(clean) > 2:
                    clean_synonyms.append(clean)

        return clean_synonyms

    def _extract_inclusion_notes(self, description: str) -> list[str]:
        """Extract inclusion notes from description"""
        # Look for common inclusion patterns
        inclusion_patterns = [
            "includes:",
            "including:",
            "such as:",
            "code also:",
            "use additional code",
        ]

        notes = []
        desc_lower = description.lower()

        for pattern in inclusion_patterns:
            if pattern in desc_lower:
                # Extract text after the pattern
                start_idx = desc_lower.find(pattern)
                if start_idx != -1:
                    text_after = description[start_idx + len(pattern):].strip()
                    if text_after:
                        notes.append(text_after.split(".")[0].strip())

        return notes

    def _extract_exclusion_notes(self, description: str) -> list[str]:
        """Extract exclusion notes from description"""
        # Look for common exclusion patterns
        exclusion_patterns = [
            "excludes:",
            "excluding:",
            "not including:",
            "code first:",
            "excludes1:",
            "excludes2:",
        ]

        notes = []
        desc_lower = description.lower()

        for pattern in exclusion_patterns:
            if pattern in desc_lower:
                start_idx = desc_lower.find(pattern)
                if start_idx != -1:
                    text_after = description[start_idx + len(pattern):].strip()
                    if text_after:
                        notes.append(text_after.split(".")[0].strip())

        return notes

    def _determine_billability(self, code: str) -> bool:
        """Determine if an ICD-10 code is billable"""
        # Generally, codes with more specificity (longer length) are billable
        # This is a simplified heuristic - in reality, billability requires
        # official CMS guidance

        if not code or len(code) < 3:
            return False

        # Most 4+ character codes are billable
        # 3-character codes are usually category headers
        code_without_dot = code.replace(".", "")
        return len(code_without_dot) >= 4

    def _get_parent_code(self, code: str) -> str | None:
        """Get the parent code for hierarchical structure"""
        if not code or len(code) <= 3:
            return None

        code_without_dot = code.replace(".", "")

        if len(code_without_dot) > 3:
            # Parent is the 3-character category
            return code_without_dot[:3]

        return None

    def _create_search_text(self, code: str, description: str, synonyms: list) -> str:
        """Create searchable text combining all relevant fields"""
        search_parts = [code, description]

        if isinstance(synonyms, list):
            search_parts.extend([str(s) for s in synonyms if s])
        elif synonyms:
            search_parts.append(str(synonyms))

        return " ".join(search_parts).lower()

    def _validate_code(self, parsed_code: dict) -> bool:
        """Validate parsed ICD-10 code"""
        try:
            code = parsed_code.get("code", "")
            description = parsed_code.get("description", "")

            # Basic validation
            if not code or not description:
                return False

            # Code format validation
            if not self._validate_code_format(code):
                return False

            # Description length validation
            return not (len(description) < 5 or len(description) > 500)

        except Exception as e:
            logger.exception(f"Validation error: {e}")
            return False

    def _validate_code_format(self, code: str) -> bool:
        """Validate ICD-10 code format"""
        if not code:
            return False

        # Remove dots for validation
        code_clean = code.replace(".", "")

        # Must be 3-7 characters
        if len(code_clean) < 3 or len(code_clean) > 7:
            return False

        # First character must be letter
        if not code_clean[0].isalpha():
            return False

        # Second and third characters must be digits
        if not (code_clean[1:3].isdigit()):
            return False

        # Additional characters can be letters or digits
        if len(code_clean) > 3:
            for char in code_clean[3:]:
                if not (char.isalnum()):
                    return False

        return True

    def build_hierarchy(self, codes: list[dict]) -> list[dict]:
        """Build hierarchical relationships between codes"""
        logger.info("Building ICD-10 code hierarchy")

        # Create lookup by code
        code_lookup = {code["code"]: code for code in codes}

        # Build parent-child relationships
        for code in codes:
            parent_code = code.get("parent_code")
            if parent_code and parent_code in code_lookup:
                parent = code_lookup[parent_code]
                if "children_codes" not in parent:
                    parent["children_codes"] = []
                parent["children_codes"].append(code["code"])

        logger.info("ICD-10 hierarchy building completed")
        return codes

    def get_parsing_stats(self) -> dict[str, Any]:
        """Get comprehensive parsing statistics"""
        total_attempted = self.processed_codes + self.validation_errors

        return {
            "processed_codes": self.processed_codes,
            "validation_errors": self.validation_errors,
            "duplicates_removed": self.duplicates_removed,
            "source_conflicts_resolved": self.source_conflicts_resolved,
            "hierarchy_relationships_built": self.hierarchy_built,
            "success_rate": (
                self.processed_codes / total_attempted
                if total_attempted > 0 else 0
            ),
            "duplication_rate": (
                self.duplicates_removed / (self.processed_codes + self.duplicates_removed)
                if (self.processed_codes + self.duplicates_removed) > 0 else 0
            ),
            "conflict_resolution_rate": (
                self.source_conflicts_resolved / self.duplicates_removed
                if self.duplicates_removed > 0 else 0
            ),
        }

    def analyze_code_distribution(self, codes: list[dict]) -> dict[str, Any]:
        """Analyze the distribution of ICD-10 codes"""
        analysis = {
            "total_codes": len(codes),
            "by_chapter": {},
            "by_source": {},
            "billable_vs_non_billable": {"billable": 0, "non_billable": 0},
            "code_length_distribution": {},
            "hierarchy_depth": {"category_codes": 0, "subcategory_codes": 0, "detailed_codes": 0},
        }

        for code in codes:
            # Chapter analysis
            chapter = code.get("chapter", "Unknown")
            analysis["by_chapter"][chapter] = analysis["by_chapter"].get(chapter, 0) + 1

            # Source analysis
            source = code.get("source", "unknown")
            analysis["by_source"][source] = analysis["by_source"].get(source, 0) + 1

            # Billable analysis
            if code.get("is_billable", False):
                analysis["billable_vs_non_billable"]["billable"] += 1
            else:
                analysis["billable_vs_non_billable"]["non_billable"] += 1

            # Code length analysis
            code_length = code.get("code_length", 0)
            analysis["code_length_distribution"][str(code_length)] = analysis["code_length_distribution"].get(str(code_length), 0) + 1

            # Hierarchy depth analysis
            if code_length == 3:
                analysis["hierarchy_depth"]["category_codes"] += 1
            elif code_length == 4:
                analysis["hierarchy_depth"]["subcategory_codes"] += 1
            elif code_length >= 5:
                analysis["hierarchy_depth"]["detailed_codes"] += 1

        # Sort by frequency
        analysis["by_chapter"] = dict(sorted(analysis["by_chapter"].items(), key=lambda x: x[1], reverse=True))
        analysis["by_source"] = dict(sorted(analysis["by_source"].items(), key=lambda x: x[1], reverse=True))

        return analysis


def main():
    """Test the ICD-10 parser"""
    logging.basicConfig(level=logging.INFO)

    # Test data
    test_codes = [
        {
            "code": "E11.9",
            "description": "Type 2 diabetes mellitus without complications",
            "category": "Endocrine, nutritional and metabolic diseases",
            "chapter": "E",
            "synonyms": ["Adult-onset diabetes", "NIDDM"],
            "source": "test",
        },
        {
            "code": "I10",
            "description": "Essential (primary) hypertension",
            "category": "Diseases of the circulatory system",
            "chapter": "I",
            "synonyms": [],
            "source": "test",
        },
    ]

    parser = ICD10Parser()
    parsed_codes = parser.parse_and_validate(test_codes)

    print(f"Parsed {len(parsed_codes)} codes:")
    for code in parsed_codes:
        print(f"  {code['code']}: {code['description']}")
        print(f"    Billable: {code['is_billable']}")
        print(f"    Parent: {code['parent_code']}")

    stats = parser.get_parsing_stats()
    print(f"\nParsing stats: {stats}")


if __name__ == "__main__":
    main()
