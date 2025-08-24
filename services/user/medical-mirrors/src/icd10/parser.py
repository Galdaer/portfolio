"""
ICD-10 codes parser and data processor
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ICD10Parser:
    """Parser for ICD-10 diagnostic codes data"""

    def __init__(self):
        self.processed_codes = 0
        self.validation_errors = 0
        self.duplicates_removed = 0

    def parse_and_validate(self, raw_codes: list[dict]) -> list[dict]:
        """Parse and validate ICD-10 codes data"""
        logger.info(f"Parsing and validating {len(raw_codes)} ICD-10 codes")

        validated_codes = []
        seen_codes = set()

        for raw_code in raw_codes:
            try:
                parsed_code = self._parse_single_code(raw_code)

                if parsed_code and self._validate_code(parsed_code):
                    # Check for duplicates
                    code_key = parsed_code["code"]
                    if code_key not in seen_codes:
                        validated_codes.append(parsed_code)
                        seen_codes.add(code_key)
                        self.processed_codes += 1
                    else:
                        self.duplicates_removed += 1
                else:
                    self.validation_errors += 1

            except Exception as e:
                logger.exception(f"Error parsing code {raw_code.get('code', 'unknown')}: {e}")
                self.validation_errors += 1
                continue

        logger.info(f"Parsed {len(validated_codes)} valid codes, "
                   f"removed {self.duplicates_removed} duplicates, "
                   f"rejected {self.validation_errors} invalid codes")

        return validated_codes

    def _parse_single_code(self, raw_code: dict) -> dict | None:
        """Parse a single ICD-10 code"""
        try:
            code = raw_code.get("code", "").strip()
            description = raw_code.get("description", "").strip()

            if not code or not description:
                return None

            # Normalize code format
            normalized_code = self._normalize_code(code)

            # Extract additional metadata
            return {
                "code": normalized_code,
                "description": description,
                "category": raw_code.get("category", "").strip(),
                "chapter": raw_code.get("chapter", "").strip(),
                "synonyms": self._parse_synonyms(raw_code.get("synonyms", [])),
                "inclusion_notes": self._extract_inclusion_notes(description),
                "exclusion_notes": self._extract_exclusion_notes(description),
                "is_billable": self._determine_billability(normalized_code),
                "code_length": len(normalized_code),
                "parent_code": self._get_parent_code(normalized_code),
                "children_codes": [],  # Will be populated later
                "source": raw_code.get("source", "unknown"),
                "last_updated": datetime.now().isoformat(),
                "search_text": self._create_search_text(normalized_code, description, raw_code.get("synonyms", [])),
            }


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

    def get_parsing_stats(self) -> dict:
        """Get parsing statistics"""
        return {
            "processed_codes": self.processed_codes,
            "validation_errors": self.validation_errors,
            "duplicates_removed": self.duplicates_removed,
            "success_rate": (
                self.processed_codes / (self.processed_codes + self.validation_errors)
                if (self.processed_codes + self.validation_errors) > 0 else 0
            ),
        }


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
