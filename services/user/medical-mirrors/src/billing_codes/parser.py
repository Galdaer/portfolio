"""
Billing codes parser and data processor
"""

import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)


class BillingCodesParser:
    """Parser for medical billing codes (CPT/HCPCS) data"""

    def __init__(self):
        self.processed_codes = 0
        self.validation_errors = 0
        self.duplicates_removed = 0

    def parse_and_validate(self, raw_codes: list[dict]) -> list[dict]:
        """Parse and validate billing codes data"""
        logger.info(f"Parsing and validating {len(raw_codes)} billing codes")

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
                logger.exception(f"Error parsing billing code {raw_code.get('code', 'unknown')}: {e}")
                self.validation_errors += 1
                continue

        logger.info(f"Parsed {len(validated_codes)} valid codes, "
                   f"removed {self.duplicates_removed} duplicates, "
                   f"rejected {self.validation_errors} invalid codes")

        return validated_codes

    def _parse_single_code(self, raw_code: dict) -> dict | None:
        """Parse a single billing code"""
        try:
            code = raw_code.get("code", "").strip()
            short_description = raw_code.get("short_description", "").strip()
            long_description = raw_code.get("long_description", "").strip()
            code_type = raw_code.get("code_type", "").strip().upper()

            if not code:
                return None

            # Use long description if available, otherwise short description
            description = long_description or short_description
            if not description:
                return None

            # Normalize code format
            normalized_code = self._normalize_code(code, code_type)

            # Extract additional metadata
            return {
                "code": normalized_code,
                "short_description": short_description,
                "long_description": long_description,
                "description": description,  # Primary description for search
                "code_type": code_type,
                "category": raw_code.get("category", "").strip(),
                "coverage_notes": raw_code.get("coverage_notes", "").strip(),
                "effective_date": self._parse_date(raw_code.get("effective_date")),
                "termination_date": self._parse_date(raw_code.get("termination_date")),
                "is_active": self._determine_active_status(raw_code),
                "modifier_required": self._check_modifier_requirements(code, description),
                "gender_specific": self._check_gender_specificity(description),
                "age_specific": self._check_age_specificity(description),
                "bilateral_indicator": self._check_bilateral_indicator(description),
                "source": raw_code.get("source", "unknown"),
                "last_updated": datetime.now().isoformat(),
                "search_text": self._create_search_text(normalized_code, description, short_description),
            }


        except Exception as e:
            logger.exception(f"Error parsing single billing code: {e}")
            return None

    def _normalize_code(self, code: str, code_type: str) -> str:
        """Normalize billing code format"""
        # Remove whitespace and convert to uppercase
        normalized = code.strip().upper()

        # Remove any non-alphanumeric characters except hyphens
        normalized = re.sub(r"[^A-Z0-9\-]", "", normalized)

        # Specific formatting rules by code type
        if code_type == "CPT":
            # CPT codes are typically 5 digits
            normalized = re.sub(r"[^0-9]", "", normalized)
            if len(normalized) == 5 and normalized.isdigit():
                return normalized

        elif code_type == "HCPCS":
            # HCPCS Level II codes are 1 letter + 4 digits
            if len(normalized) >= 4 and normalized[0].isalpha():
                return normalized[:5]  # Take first 5 characters max

        return normalized

    def _parse_date(self, date_str) -> str | None:
        """Parse date string into standard format"""
        if not date_str:
            return None

        try:
            # Try parsing common date formats
            if isinstance(date_str, datetime):
                return date_str.isoformat()

            # Add date parsing logic as needed
            return str(date_str)

        except Exception:
            return None

    def _determine_active_status(self, raw_code: dict) -> bool:
        """Determine if a billing code is currently active"""
        termination_date = raw_code.get("termination_date")
        effective_date = raw_code.get("effective_date")

        # If no dates provided, assume active
        if not termination_date and not effective_date:
            return True

        current_date = datetime.now()

        # Check if terminated
        if termination_date:
            try:
                if isinstance(termination_date, str):
                    term_date = datetime.fromisoformat(termination_date.replace("Z", "+00:00"))
                else:
                    term_date = termination_date

                if current_date > term_date:
                    return False
            except Exception:
                pass

        # Check if effective
        if effective_date:
            try:
                if isinstance(effective_date, str):
                    eff_date = datetime.fromisoformat(effective_date.replace("Z", "+00:00"))
                else:
                    eff_date = effective_date

                if current_date < eff_date:
                    return False
            except Exception:
                pass

        return True

    def _check_modifier_requirements(self, code: str, description: str) -> bool:
        """Check if code typically requires modifiers"""
        desc_lower = description.lower()

        # Common indicators for modifier requirements
        modifier_indicators = [
            "bilateral", "unilateral", "left", "right",
            "multiple", "each", "per", "additional",
            "professional component", "technical component",
            "assistant surgeon", "co-surgeon",
        ]

        return any(indicator in desc_lower for indicator in modifier_indicators)

    def _check_gender_specificity(self, description: str) -> str | None:
        """Check if code is gender-specific"""
        desc_lower = description.lower()

        if any(term in desc_lower for term in ["female", "woman", "maternal", "pregnancy", "obstetric"]):
            return "female"
        if any(term in desc_lower for term in ["male", "man", "prostate", "testicular"]):
            return "male"

        return None

    def _check_age_specificity(self, description: str) -> str | None:
        """Check if code is age-specific"""
        desc_lower = description.lower()

        if any(term in desc_lower for term in ["pediatric", "child", "infant", "newborn"]):
            return "pediatric"
        if any(term in desc_lower for term in ["adult", "geriatric", "elderly"]):
            return "adult"

        return None

    def _check_bilateral_indicator(self, description: str) -> bool:
        """Check if code involves bilateral procedures"""
        desc_lower = description.lower()
        bilateral_terms = ["bilateral", "both", "each side", "right and left"]

        return any(term in desc_lower for term in bilateral_terms)

    def _create_search_text(self, code: str, description: str, short_description: str = "") -> str:
        """Create searchable text combining all relevant fields"""
        search_parts = [code, description]

        if short_description and short_description != description:
            search_parts.append(short_description)

        return " ".join(search_parts).lower()

    def _validate_code(self, parsed_code: dict) -> bool:
        """Validate parsed billing code"""
        try:
            code = parsed_code.get("code", "")
            description = parsed_code.get("description", "")
            code_type = parsed_code.get("code_type", "")

            # Basic validation
            if not code or not description or not code_type:
                return False

            # Code format validation
            if not self._validate_code_format(code, code_type):
                return False

            # Description length validation
            return not (len(description) < 3 or len(description) > 1000)

        except Exception as e:
            logger.exception(f"Validation error: {e}")
            return False

    def _validate_code_format(self, code: str, code_type: str) -> bool:
        """Validate billing code format"""
        if not code or not code_type:
            return False

        if code_type == "CPT":
            # CPT codes are 5 digits
            return len(code) == 5 and code.isdigit()

        if code_type == "HCPCS":
            # HCPCS Level II: 1 letter + 4 digits
            if len(code) != 5:
                return False

            return code[0].isalpha() and code[1:5].isdigit()

        # Generic validation for other types
        return len(code) >= 3 and len(code) <= 10

    def organize_by_category(self, codes: list[dict]) -> dict[str, list[dict]]:
        """Organize codes by category for easier management"""
        logger.info("Organizing billing codes by category")

        categorized = {}

        for code in codes:
            category = code.get("category", "Unknown")
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(code)

        # Sort each category by code
        for category in categorized:
            categorized[category].sort(key=lambda x: x.get("code", ""))

        logger.info(f"Organized codes into {len(categorized)} categories")
        return categorized

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
    """Test the billing codes parser"""
    logging.basicConfig(level=logging.INFO)

    # Test data
    test_codes = [
        {
            "code": "A0021",
            "short_description": "Ambulance service",
            "long_description": "Ambulance service, outside state per mile, transport",
            "code_type": "HCPCS",
            "category": "Transportation Services",
            "source": "test",
        },
        {
            "code": "99213",
            "short_description": "Office visit",
            "long_description": "Office or other outpatient visit for evaluation and management",
            "code_type": "CPT",
            "category": "Evaluation and Management",
            "source": "test",
        },
    ]

    parser = BillingCodesParser()
    parsed_codes = parser.parse_and_validate(test_codes)

    print(f"Parsed {len(parsed_codes)} codes:")
    for code in parsed_codes:
        print(f"  {code['code']} ({code['code_type']}): {code['description']}")
        print(f"    Active: {code['is_active']}")
        print(f"    Modifier Required: {code['modifier_required']}")

    # Test categorization
    categorized = parser.organize_by_category(parsed_codes)
    print(f"\nCategories: {list(categorized.keys())}")

    stats = parser.get_parsing_stats()
    print(f"\nParsing stats: {stats}")


if __name__ == "__main__":
    main()
