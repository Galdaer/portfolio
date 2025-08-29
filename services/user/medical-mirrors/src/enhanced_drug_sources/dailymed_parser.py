"""
DailyMed XML Parser
Parses DailyMed XML files to extract clinical drug information
"""

import logging
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class DailyMedParser:
    """Parser for DailyMed XML drug label files"""

    def __init__(self):
        # Define namespaces used in DailyMed XML
        self.namespaces = {
            "": "urn:hl7-org:v3",
        }

        # Mapping of DailyMed section codes to our database fields
        self.section_mappings = {
            # Clinical information
            "34067-9": "indications_and_usage",
            "34090-1": "contraindications",
            "34071-1": "warnings",
            "42232-9": "precautions",
            "34084-4": "adverse_reactions",
            "34073-7": "drug_interactions",
            "34068-7": "dosage_and_administration",
            "43679-0": "mechanism_of_action",
            "43680-8": "pharmacokinetics",
            "43681-6": "pharmacodynamics",
            "12223-1": "clinical_pharmacology",

            # Special populations
            "34081-0": "pediatric_use",
            "34082-8": "geriatric_use",
            "42228-7": "pregnancy",
            "34080-2": "nursing_mothers",
            "34088-5": "overdosage",

            # Additional clinical information
            "34066-1": "boxed_warning",
            "34092-7": "clinical_studies",
            "34077-8": "nonclinical_toxicology",
        }

    def parse_xml_file(self, xml_file_path: str) -> dict[str, Any] | None:
        """Parse a single DailyMed XML file"""
        try:
            logger.debug(f"Parsing DailyMed XML file: {xml_file_path}")

            # Parse XML
            tree = ET.parse(xml_file_path)
            root = tree.getroot()

            # Extract basic drug information
            drug_info = self._extract_basic_info(root)

            # Extract clinical information from sections
            clinical_info = self._extract_clinical_sections(root)

            # Merge information
            drug_info.update(clinical_info)

            # Add source information
            drug_info["data_sources"] = ["dailymed"]
            drug_info["dailymed_file"] = os.path.basename(xml_file_path)

            return drug_info

        except ET.ParseError as e:
            logger.warning(f"Failed to parse XML file {xml_file_path}: {e}")
            return None
        except Exception as e:
            logger.exception(f"Error parsing DailyMed XML file {xml_file_path}: {e}")
            return None

    def _extract_basic_info(self, root: ET.Element) -> dict[str, Any]:
        """Extract basic drug information from XML"""
        info = {
            "generic_name": "",
            "brand_name": "",
            "manufacturer": "",
            "set_id": "",
            "effective_time": "",
        }

        try:
            # Extract title (contains drug names)
            title_elem = root.find(".//title", self.namespaces)
            if title_elem is not None and title_elem.text:
                title = title_elem.text.strip()
                # Parse drug name from title
                info["brand_name"], info["generic_name"] = self._parse_drug_names_from_title(title)

            # Extract manufacturer
            org_elem = root.find(".//author//representedOrganization/name", self.namespaces)
            if org_elem is not None and org_elem.text:
                info["manufacturer"] = org_elem.text.strip()

            # Extract set ID
            set_id_elem = root.find(".//setId", self.namespaces)
            if set_id_elem is not None:
                info["set_id"] = set_id_elem.get("root", "")

            # Extract effective time
            eff_time_elem = root.find(".//effectiveTime", self.namespaces)
            if eff_time_elem is not None:
                info["effective_time"] = eff_time_elem.get("value", "")

        except Exception as e:
            logger.warning(f"Error extracting basic info: {e}")

        return info

    def _parse_drug_names_from_title(self, title: str) -> tuple[str, str]:
        """Parse brand name and generic name from title"""
        # Remove HTML tags
        title = re.sub(r"<[^>]+>", "", title)

        # Common patterns in DailyMed titles
        # Example: "NP Thyroid® (THYROID TABLETS, USP)"
        brand_match = re.search(r"^([^(]+?)(?:\s*®|\s*™|\s*\()", title)
        brand_name = brand_match.group(1).strip() if brand_match else ""

        # Generic name often in parentheses or after brand name
        generic_match = re.search(r"\(([^)]+)\)", title)
        generic_name = ""
        if generic_match:
            generic_text = generic_match.group(1).strip()
            # Remove dosage forms and common suffixes
            generic_text = re.sub(r"\s+(TABLETS?|CAPSULES?|INJECTION|USP|NF).*", "", generic_text, flags=re.IGNORECASE)
            generic_name = generic_text.strip()

        # If no parentheses, try to extract from brand name
        if not generic_name and brand_name:
            generic_name = brand_name

        return brand_name, generic_name

    def _extract_clinical_sections(self, root: ET.Element) -> dict[str, Any]:
        """Extract clinical information from structured sections"""
        clinical_info = {}

        try:
            # Find all sections
            sections = root.findall(".//section", self.namespaces)

            for section in sections:
                # Get section code
                code_elem = section.find(".//code", self.namespaces)
                if code_elem is None:
                    continue

                section_code = code_elem.get("code", "")

                # Check if this is a section we care about
                if section_code in self.section_mappings:
                    field_name = self.section_mappings[section_code]

                    # Extract text content from section
                    section_text = self._extract_section_text(section)
                    if section_text:
                        # Some fields should be arrays
                        if field_name in ["contraindications", "warnings", "precautions", "adverse_reactions"]:
                            clinical_info[field_name] = [section_text]
                        else:
                            clinical_info[field_name] = section_text

        except Exception as e:
            logger.warning(f"Error extracting clinical sections: {e}")

        return clinical_info

    def _extract_section_text(self, section: ET.Element) -> str:
        """Extract text content from a section element"""
        try:
            # Get all text content from the section
            text_parts = []

            # Look for paragraph elements
            paragraphs = section.findall(".//paragraph", self.namespaces)
            for p in paragraphs:
                p_text = self._get_element_text(p)
                if p_text:
                    text_parts.append(p_text)

            # If no paragraphs, get all text
            if not text_parts:
                section_text = self._get_element_text(section)
                if section_text:
                    text_parts.append(section_text)

            # Join all text parts
            full_text = " ".join(text_parts).strip()

            # Clean up the text
            return self._clean_text(full_text)


        except Exception as e:
            logger.warning(f"Error extracting section text: {e}")
            return ""

    def _get_element_text(self, element: ET.Element) -> str:
        """Get all text content from an element"""
        try:
            # Get text from element and all its children
            text_parts = []

            if element.text:
                text_parts.append(element.text.strip())

            for child in element:
                child_text = self._get_element_text(child)
                if child_text:
                    text_parts.append(child_text)

                if child.tail:
                    text_parts.append(child.tail.strip())

            return " ".join(text_parts)

        except Exception:
            return ""

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ""

        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text)

        # Remove common unwanted patterns
        text = re.sub(r"^\s*\d+\.?\s*", "", text)  # Remove leading numbers
        text = re.sub(r"\s*\[.*?\]\s*", "", text)  # Remove reference brackets

        return text.strip()

    def parse_directory(self, dailymed_dir: str) -> list[dict[str, Any]]:
        """Parse all XML files in a DailyMed directory"""
        logger.info(f"Parsing DailyMed XML files from {dailymed_dir}")

        drugs = []
        xml_files = list(Path(dailymed_dir).glob("*.xml"))

        logger.info(f"Found {len(xml_files)} DailyMed XML files")

        for xml_file in xml_files:
            try:
                drug_info = self.parse_xml_file(str(xml_file))
                if drug_info:
                    drugs.append(drug_info)

            except Exception as e:
                logger.warning(f"Failed to parse {xml_file}: {e}")
                continue

        logger.info(f"Successfully parsed {len(drugs)} DailyMed XML files")
        return drugs
