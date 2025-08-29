"""
Drug Name Matching Utilities
Provides fuzzy matching between different drug naming conventions
"""

import re
from difflib import SequenceMatcher


class DrugNameMatcher:
    """Intelligent drug name matching for enhanced source integration"""

    def __init__(self):
        # Common prefixes to remove for matching
        self.prefixes_to_remove = [
            r"^\([rs]\)-",  # (R)-, (S)- stereoisomer prefixes
            r"^\(\+\)-",    # (+)- optical isomer
            r"^\(-\)-",     # (-)- optical isomer
            r"^l-",         # L- prefix
            r"^d-",         # D- prefix
            r"^dl-",        # DL- prefix
        ]

        # Common suffixes to remove for matching
        self.suffixes_to_remove = [
            r"\s+(hydrochloride|hcl)$",
            r"\s+(sodium|na)$",
            r"\s+(potassium|k)$",
            r"\s+(calcium|ca)$",
            r"\s+(magnesium|mg)$",
            r"\s+(sulfate|sulphate)$",
            r"\s+(phosphate)$",
            r"\s+(citrate)$",
            r"\s+(tartrate)$",
            r"\s+(maleate)$",
            r"\s+(fumarate)$",
            r"\s+(succinate)$",
            r"\s+(acetate)$",
            r"\s+(benzoate)$",
            r"\s+(mesylate)$",
            r"\s+(tosylate)$",
            r"\s+(besylate)$",
            r"\s+(pamoate)$",
            r"\s+(embonate)$",
            r"\s+(dihydrate)$",
            r"\s+(monohydrate)$",
            r"\s+(anhydrous)$",
            r"\s+(free\s+base)$",
            r"\s+(base)$",
            r"\s+(salt)$",
            r"\s+injection$",
            r"\s+tablets?$",
            r"\s+capsules?$",
            r"\s+solution$",
            r"\s+suspension$",
            r"\s+extended.release$",
            r"\s+immediate.release$",
            r"\s+usp$",
            r"\s+nf$",
        ]

        # Common abbreviations and their expansions
        self.abbreviation_map = {
            "hcl": "hydrochloride",
            "na": "sodium",
            "k": "potassium",
            "ca": "calcium",
            "mg": "magnesium",
            "er": "extended release",
            "ir": "immediate release",
            "xl": "extended release",
            "sr": "sustained release",
            "cr": "controlled release",
        }

    def normalize_drug_name(self, drug_name: str) -> str:
        """Normalize a drug name for comparison"""
        if not drug_name:
            return ""

        # Convert to lowercase and strip
        normalized = drug_name.lower().strip()

        # Remove prefixes
        for prefix_pattern in self.prefixes_to_remove:
            normalized = re.sub(prefix_pattern, "", normalized, flags=re.IGNORECASE)

        # Remove suffixes
        for suffix_pattern in self.suffixes_to_remove:
            normalized = re.sub(suffix_pattern, "", normalized, flags=re.IGNORECASE)

        # Clean up whitespace and special characters
        normalized = re.sub(r"[^\w\s]", "", normalized)  # Remove non-alphanumeric except spaces
        return re.sub(r"\s+", " ", normalized).strip()  # Normalize whitespace


    def get_matching_score(self, name1: str, name2: str) -> float:
        """Calculate similarity score between two drug names"""
        norm1 = self.normalize_drug_name(name1)
        norm2 = self.normalize_drug_name(name2)

        if not norm1 or not norm2:
            return 0.0

        # Exact match after normalization
        if norm1 == norm2:
            return 1.0

        # Check if one is contained in the other
        if norm1 in norm2 or norm2 in norm1:
            return 0.9

        # Use sequence matching for similarity
        similarity = SequenceMatcher(None, norm1, norm2).ratio()

        # Boost score if major words match
        words1 = set(norm1.split())
        words2 = set(norm2.split())
        if words1 and words2:
            word_overlap = len(words1.intersection(words2)) / len(words1.union(words2))
            similarity = max(similarity, word_overlap * 0.8)

        return similarity

    def find_best_match(self, target_name: str, candidate_names: list[str],
                       threshold: float = 0.7) -> tuple[str, float] | None:
        """Find the best matching name from a list of candidates"""
        best_match = None
        best_score = 0.0

        for candidate in candidate_names:
            score = self.get_matching_score(target_name, candidate)
            if score > best_score and score >= threshold:
                best_match = candidate
                best_score = score

        return (best_match, best_score) if best_match else None

    def create_lookup_map(self, source_names: list[str], db_names: list[str],
                         threshold: float = 0.7) -> dict[str, str]:
        """Create a lookup map from source names to database names (highly optimized)"""
        lookup_map = {}

        # Create multiple lookup maps for different matching strategies
        exact_match_map = {}
        normalized_map = {}
        upper_map = {}

        for db_name in db_names:
            # Exact match
            exact_match_map[db_name] = db_name

            # Normalized match
            normalized = self.normalize_drug_name(db_name)
            if normalized:
                normalized_map[normalized] = db_name

            # Upper case match
            upper_map[db_name.upper()] = db_name

        matched_count = 0
        unmatched = []

        # Process source names with multiple fast matching strategies
        for source_name in source_names:
            matched = False

            # Strategy 1: Exact match
            if source_name in exact_match_map:
                lookup_map[source_name] = exact_match_map[source_name]
                matched = True
                matched_count += 1
                continue

            # Strategy 2: Normalized match
            normalized_source = self.normalize_drug_name(source_name)
            if normalized_source and normalized_source in normalized_map:
                lookup_map[source_name] = normalized_map[normalized_source]
                matched = True
                matched_count += 1
                continue

            # Strategy 3: Upper case match
            if source_name.upper() in upper_map:
                lookup_map[source_name] = upper_map[source_name.upper()]
                matched = True
                matched_count += 1
                continue

            # If no fast match, add to unmatched for potential fuzzy matching
            if not matched:
                unmatched.append(source_name)

        # Only do expensive fuzzy matching on remaining unmatched items (max 100 for performance)
        if unmatched and len(unmatched) <= 100:
            for source_name in unmatched:
                match_result = self.find_best_match(source_name, db_names, threshold)
                if match_result:
                    db_name, score = match_result
                    lookup_map[source_name] = db_name
                    matched_count += 1

        print(f"Matching results: {matched_count}/{len(source_names)} matched ({len(unmatched)} unmatched)")
        return lookup_map

    def get_alternative_names(self, drug_name: str) -> list[str]:
        """Generate alternative name variants for a drug"""
        alternatives = [drug_name]

        # Add normalized version
        normalized = self.normalize_drug_name(drug_name)
        if normalized and normalized != drug_name.lower():
            alternatives.append(normalized)
            alternatives.append(normalized.upper())
            alternatives.append(normalized.title())

        # Add versions with common salt forms
        base_name = self.normalize_drug_name(drug_name)
        if base_name:
            for salt in ["hydrochloride", "sodium", "potassium", "calcium"]:
                alternatives.append(f"{base_name} {salt}")
                alternatives.append(f"{base_name.upper()} {salt.upper()}")

        return list(set(alternatives))  # Remove duplicates
