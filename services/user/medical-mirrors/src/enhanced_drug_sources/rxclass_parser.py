"""
RxClass JSON Parser
Parses RxClass JSON files to extract therapeutic classifications
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class RxClassParser:
    """Parser for RxClass JSON therapeutic classification files"""

    def __init__(self):
        pass

    def parse_drug_classes_file(self, json_file_path: str) -> dict[str, list[str]]:
        """Parse a single RxClass drug_classes_*.json file"""
        logger.debug(f"Parsing RxClass file: {json_file_path}")

        classes_data = {}

        try:
            with open(json_file_path) as f:
                data = json.load(f)

            # Extract drug name from filename (format: drug_classes_drugname.json)
            filename = Path(json_file_path).stem
            drug_name = filename.replace("drug_classes_", "")

            # Handle new RxClass JSON structure with classifications
            therapeutic_classes = set()

            # Look for classifications section (new format)
            classifications = data.get("classifications", {})
            if classifications:
                # Process each classification type (ATC, ATCPROD, etc.)
                for class_type, class_data in classifications.items():
                    rxclass_drug_info_list = class_data.get("rxclassDrugInfoList", {})
                    drug_info_list = rxclass_drug_info_list.get("rxclassDrugInfo", [])

                    for drug_info in drug_info_list:
                        try:
                            # Get RxClass minimal concept item (new structure)
                            rxclass_info = drug_info.get("rxclassMinConceptItem", {})

                            class_name = rxclass_info.get("className", "")
                            class_type_info = rxclass_info.get("classType", "")

                            if class_name:
                                # Add context if we have class type
                                if class_type_info:
                                    therapeutic_classes.add(f"{class_name} ({class_type_info})")
                                else:
                                    therapeutic_classes.add(class_name)

                        except Exception as e:
                            logger.warning(f"Error processing drug info in {json_file_path}: {e}")
                            continue
            else:
                # Fall back to old format
                rxclass_drug_info_list = data.get("rxclassDrugInfoList", {})
                drug_info_list = rxclass_drug_info_list.get("rxclassDrugInfo", [])

                for drug_info in drug_info_list:
                    try:
                        # Get RxClass information (old structure)
                        rxclass_info = drug_info.get("rxclassMinConcept", {})

                        class_name = rxclass_info.get("className", "")
                        class_type = rxclass_info.get("classType", "")

                        if class_name:
                            # Add context if we have class type
                            if class_type:
                                therapeutic_classes.add(f"{class_name} ({class_type})")
                            else:
                                therapeutic_classes.add(class_name)

                    except Exception as e:
                        logger.warning(f"Error processing drug info in {json_file_path}: {e}")
                        continue

            if therapeutic_classes:
                drug_key = drug_name.lower().strip()
                classes_data[drug_key] = list(therapeutic_classes)
                logger.debug(f"Found {len(therapeutic_classes)} therapeutic classes for {drug_name}")
            else:
                logger.debug(f"No drug class information found in {json_file_path}")

            return classes_data

        except Exception as e:
            logger.warning(f"Failed to parse RxClass file {json_file_path}: {e}")
            return {}

    def parse_rxclass_directory(self, rxclass_dir: str) -> dict[str, str]:
        """Parse all RxClass JSON files in directory"""
        logger.info(f"Parsing RxClass therapeutic classifications from {rxclass_dir}")

        therapeutic_classes_data = {}

        # Find all drug_classes_*.json files
        json_files = list(Path(rxclass_dir).glob("drug_classes_*.json"))
        logger.info(f"Found {len(json_files)} RxClass classification files")

        for json_file in json_files:
            try:
                file_classes = self.parse_drug_classes_file(str(json_file))

                # Merge the classes data
                for drug_key, classes_list in file_classes.items():
                    if classes_list:
                        # Convert list to string for database storage
                        classes_text = "; ".join(classes_list)

                        # If we already have data for this drug, combine it
                        if drug_key in therapeutic_classes_data:
                            existing = therapeutic_classes_data[drug_key]
                            # Avoid duplicates
                            combined_classes = set(existing.split("; ") + classes_list)
                            therapeutic_classes_data[drug_key] = "; ".join(sorted(combined_classes))
                        else:
                            therapeutic_classes_data[drug_key] = classes_text

            except Exception as e:
                logger.warning(f"Failed to parse {json_file}: {e}")
                continue

        logger.info(f"Parsed therapeutic classifications for {len(therapeutic_classes_data)} drugs")
        return therapeutic_classes_data

    def extract_primary_therapeutic_class(self, classes_text: str) -> str:
        """Extract the primary therapeutic class from combined classes text"""
        if not classes_text:
            return ""

        classes = classes_text.split("; ")

        # Prioritize certain class types
        priority_types = [
            "Chemical/Ingredient",
            "Mechanism of Action",
            "Physiologic Effect",
            "Therapeutic Category",
        ]

        for priority_type in priority_types:
            for class_info in classes:
                if f"({priority_type})" in class_info:
                    # Extract just the class name without type
                    return class_info.replace(f" ({priority_type})", "")

        # If no priority type found, return the first class
        if classes:
            # Remove type info from first class
            first_class = classes[0]
            return first_class.split(" (")[0] if " (" in first_class else first_class

        return ""
