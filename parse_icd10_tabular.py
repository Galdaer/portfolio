#!/usr/bin/env python3
"""
Quick script to parse the ICD-10 tabular XML file and insert codes into database
This bypasses the complex smart downloader and directly processes the full dataset
"""

import json
import logging
import sys
import xml.etree.ElementTree as ET
from datetime import datetime

import psycopg2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def determine_chapter(code: str) -> str:
    """Determine ICD-10 chapter based on code prefix"""
    if not code:
        return ""

    first_char = code[0].upper()

    chapter_map = {
        "A": "A00-B99", "B": "A00-B99",  # Infectious and parasitic diseases
        "C": "C00-D49", "D": "C00-D49",  # Neoplasms / Blood disorders
        "E": "E00-E89",                  # Endocrine, nutritional and metabolic diseases
        "F": "F01-F99",                  # Mental, behavioral and neurodevelopmental disorders
        "G": "G00-G99",                  # Diseases of the nervous system
        "H": "H00-H59",                  # Diseases of the eye and adnexa / ear
        "I": "I00-I99",                  # Diseases of the circulatory system
        "J": "J00-J99",                  # Diseases of the respiratory system
        "K": "K00-K95",                  # Diseases of the digestive system
        "L": "L00-L99",                  # Diseases of the skin and subcutaneous tissue
        "M": "M00-M99",                  # Diseases of the musculoskeletal system
        "N": "N00-N99",                  # Diseases of the genitourinary system
        "O": "O00-O9A",                  # Pregnancy, childbirth and the puerperium
        "P": "P00-P96",                  # Perinatal conditions
        "Q": "Q00-Q99",                  # Congenital malformations
        "R": "R00-R99",                  # Symptoms, signs and abnormal findings
        "S": "S00-T88", "T": "S00-T88",  # Injury, poisoning
        "V": "V00-Y99", "W": "V00-Y99", "X": "V00-Y99", "Y": "V00-Y99",  # External causes
        "Z": "Z00-Z99",                  # Health status factors
    }

    return chapter_map.get(first_char, "Unknown")

def determine_billable_status(code: str) -> bool:
    """Determine if an ICD-10 code is billable (has sufficient specificity)"""
    if not code:
        return False

    # Generally, ICD-10 codes with more specificity are billable
    # Codes with 4+ characters are usually billable
    # 3-character codes are usually not billable (category codes)
    clean_code = code.replace(".", "")
    return len(clean_code) >= 4

def parse_icd10_xml(xml_file: str) -> list[dict]:
    """Parse ICD-10 tabular XML file and extract all codes"""
    logger.info(f"Parsing ICD-10 XML file: {xml_file}")
    codes = []

    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()

        # Find all elements that might contain ICD-10 codes and descriptions
        for elem in root.iter():
            # Look for elements with name children that contain codes
            name_elem = elem.find("name")
            if name_elem is not None and name_elem.text:
                code_text = name_elem.text.strip()

                # Check if this looks like an ICD-10 code (starts with letter + digit)
                if len(code_text) >= 3 and code_text[0].isalpha() and code_text[1].isdigit():

                    # Look for description in desc element
                    description = ""
                    desc_elem = elem.find("desc")
                    if desc_elem is not None and desc_elem.text:
                        description = desc_elem.text.strip()
                    else:
                        # Try to find description in title element
                        title_elem = elem.find("title")
                        if title_elem is not None and title_elem.text:
                            description = title_elem.text.strip()

                    # If no description found, use a default
                    if not description:
                        description = f"ICD-10 code {code_text}"

                    code_dict = {
                        "code": code_text,
                        "description": description,
                        "category": "",  # Not available in this format
                        "chapter": determine_chapter(code_text),
                        "synonyms": [],
                        "inclusion_notes": [],
                        "exclusion_notes": [],
                        "is_billable": determine_billable_status(code_text),
                        "code_length": len(code_text.replace(".", "")),
                        "parent_code": "",
                        "children_codes": [],
                        "source": "cdc_tabular_xml",
                        "search_text": f"{code_text} {description}",
                        "last_updated": datetime.now().isoformat(),
                    }

                    codes.append(code_dict)

    except Exception as e:
        logger.exception(f"Error parsing XML: {e}")
        return []

    logger.info(f"Parsed {len(codes)} ICD-10 codes from XML")
    return codes

def insert_codes_to_database(codes: list[dict]) -> bool:
    """Insert ICD-10 codes into PostgreSQL database"""
    try:
        # Database connection
        conn = psycopg2.connect(
            host="localhost",
            database="intelluxe_public",
            user="intelluxe",
            password="secure_password",
        )

        cursor = conn.cursor()

        logger.info(f"Inserting {len(codes)} ICD-10 codes into database")

        # Use UPSERT to preserve existing data
        for i, code_data in enumerate(codes):
            cursor.execute("""
                INSERT INTO icd10_codes (
                    code, description, category, chapter, synonyms,
                    inclusion_notes, exclusion_notes, is_billable,
                    code_length, parent_code, children_codes,
                    source, search_text, last_updated
                ) VALUES (
                    %(code)s, %(description)s, %(category)s, %(chapter)s, %(synonyms)s,
                    %(inclusion_notes)s, %(exclusion_notes)s, %(is_billable)s,
                    %(code_length)s, %(parent_code)s, %(children_codes)s,
                    %(source)s, %(search_text)s, NOW()
                )
                ON CONFLICT (code) DO UPDATE SET
                    -- Only update if we have better/more complete information
                    description = COALESCE(NULLIF(EXCLUDED.description, ''), icd10_codes.description),
                    category = COALESCE(NULLIF(EXCLUDED.category, ''), icd10_codes.category),
                    chapter = COALESCE(NULLIF(EXCLUDED.chapter, ''), icd10_codes.chapter),
                    synonyms = COALESCE(NULLIF(EXCLUDED.synonyms, '[]'::jsonb), icd10_codes.synonyms),
                    inclusion_notes = COALESCE(NULLIF(EXCLUDED.inclusion_notes, '[]'::jsonb), icd10_codes.inclusion_notes),
                    exclusion_notes = COALESCE(NULLIF(EXCLUDED.exclusion_notes, '[]'::jsonb), icd10_codes.exclusion_notes),
                    is_billable = COALESCE(EXCLUDED.is_billable, icd10_codes.is_billable),
                    code_length = COALESCE(EXCLUDED.code_length, icd10_codes.code_length),
                    parent_code = COALESCE(NULLIF(EXCLUDED.parent_code, ''), icd10_codes.parent_code),
                    children_codes = COALESCE(NULLIF(EXCLUDED.children_codes, '[]'::jsonb), icd10_codes.children_codes),
                    source = COALESCE(NULLIF(EXCLUDED.source, ''), icd10_codes.source),
                    search_text = COALESCE(NULLIF(EXCLUDED.search_text, ''), icd10_codes.search_text),
                    last_updated = NOW()
            """, {
                "code": code_data.get("code", ""),
                "description": code_data.get("description", ""),
                "category": code_data.get("category", ""),
                "chapter": code_data.get("chapter", ""),
                "synonyms": json.dumps(code_data.get("synonyms", [])),
                "inclusion_notes": json.dumps(code_data.get("inclusion_notes", [])),
                "exclusion_notes": json.dumps(code_data.get("exclusion_notes", [])),
                "is_billable": code_data.get("is_billable", False),
                "code_length": code_data.get("code_length", 0),
                "parent_code": code_data.get("parent_code", ""),
                "children_codes": json.dumps(code_data.get("children_codes", [])),
                "source": code_data.get("source", "cdc_tabular_xml"),
                "search_text": code_data.get("search_text", code_data.get("description", "")),
            })

            if (i + 1) % 1000 == 0:
                logger.info(f"Processed {i + 1}/{len(codes)} codes")

        conn.commit()

        # Get final count
        cursor.execute("SELECT COUNT(*) FROM icd10_codes")
        total_count = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        logger.info(f"Successfully inserted ICD-10 codes. Database now contains {total_count} total codes")
        return True

    except Exception as e:
        logger.exception(f"Error inserting codes into database: {e}")
        return False

def main():
    """Main function"""
    xml_file = "/home/intelluxe/database/medical_complete/icd10/icd-10-cm-tabular-2025.xml"

    # Parse XML file
    codes = parse_icd10_xml(xml_file)
    if not codes:
        logger.error("No codes parsed from XML file")
        return False

    # Insert into database
    success = insert_codes_to_database(codes)
    if success:
        logger.info(f"✅ Successfully processed {len(codes)} ICD-10 codes")
        return True
    logger.error("❌ Failed to insert codes into database")
    return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
