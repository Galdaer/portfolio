#!/usr/bin/env python3
"""
Direct FDA JSON parser to extract drug information and insert into database
This bypasses the complex smart downloader and directly processes the JSON files
"""

import json
import logging
import os
import sys
from typing import Any

import psycopg2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_ndc_file(json_file: str) -> list[dict[str, Any]]:
    """Parse FDA NDC JSON file and extract drug information"""
    logger.info(f"Parsing NDC file: {json_file}")
    drugs = []

    try:
        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)

        results = data.get("results", [])
        logger.info(f"Found {len(results)} NDC entries")

        for entry in results:
            # Extract basic information
            generic_name = entry.get("generic_name", "").strip()
            if not generic_name:
                continue

            brand_name = entry.get("brand_name", "").strip()
            brand_names = [brand_name] if brand_name else []

            # Extract manufacturer information
            labeler_name = entry.get("labeler_name", "").strip()
            manufacturers = [labeler_name] if labeler_name else []

            # Extract active ingredients and create formulations
            active_ingredients = entry.get("active_ingredients", [])
            formulations = []
            for ingredient in active_ingredients:
                formulation = {
                    "active_ingredient": ingredient.get("name", ""),
                    "strength": ingredient.get("strength", ""),
                    "source": "fda_ndc",
                }
                formulations.append(formulation)

            # Extract packaging information
            packaging = entry.get("packaging", [])

            # Determine application numbers from NDC
            product_ndc = entry.get("product_ndc", "")
            application_numbers = [product_ndc] if product_ndc else []

            # Extract marketing dates
            marketing_dates = []
            for package in packaging:
                start_date = package.get("marketing_start_date", "")
                if start_date:
                    marketing_dates.append(start_date)

            approval_dates = list(set(marketing_dates))  # Remove duplicates

            drug_dict = {
                "generic_name": generic_name,
                "brand_names": brand_names,
                "manufacturers": manufacturers,
                "formulations": formulations,
                "therapeutic_class": "",  # Not available in NDC data
                "indications_and_usage": "",
                "mechanism_of_action": "",
                "contraindications": [],
                "warnings": [],
                "precautions": [],
                "adverse_reactions": [],
                "drug_interactions": {},
                "dosage_and_administration": "",
                "pharmacokinetics": "",
                "pharmacodynamics": "",
                "boxed_warning": "",
                "clinical_studies": "",
                "pediatric_use": "",
                "geriatric_use": "",
                "pregnancy": "",
                "nursing_mothers": "",
                "overdosage": "",
                "nonclinical_toxicology": "",
                "approval_dates": approval_dates,
                "orange_book_codes": [],
                "application_numbers": application_numbers,
                "total_formulations": len(formulations),
                "data_sources": ["fda_ndc"],
                "confidence_score": 0.7,  # Medium confidence for NDC data
                "has_clinical_data": False,
            }

            drugs.append(drug_dict)

    except Exception as e:
        logger.exception(f"Error parsing NDC file: {e}")
        return []

    logger.info(f"Parsed {len(drugs)} drugs from NDC file")
    return drugs

def parse_drugs_fda_file(json_file: str) -> list[dict[str, Any]]:
    """Parse FDA Drugs@FDA JSON file and extract drug information"""
    logger.info(f"Parsing Drugs@FDA file: {json_file}")
    drugs = []

    try:
        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)

        results = data.get("results", [])
        logger.info(f"Found {len(results)} Drugs@FDA entries")

        for entry in results:
            # Extract application information
            application_number = entry.get("application_number", "").strip()
            if not application_number:
                continue

            # Extract product information
            products = entry.get("products", [])
            if not products:
                continue

            for product in products:
                # Extract basic drug information
                brand_name = product.get("brand_name", "").strip()
                generic_name = product.get("generic_name", "").strip()

                if not generic_name and not brand_name:
                    continue

                # Use generic name as primary, fallback to brand name
                primary_name = generic_name if generic_name else brand_name
                brand_names = [brand_name] if brand_name and brand_name != primary_name else []

                # Extract active ingredients
                active_ingredients = product.get("active_ingredients", [])
                formulations = []
                for ingredient in active_ingredients:
                    formulation = {
                        "active_ingredient": ingredient.get("name", ""),
                        "strength": ingredient.get("strength", ""),
                        "source": "fda_drugs",
                    }
                    formulations.append(formulation)

                # Extract dosage form and route
                dosage_form = product.get("dosage_form", "") or ""
                route = product.get("route", "") or ""
                dosage_form = dosage_form.strip() if dosage_form else ""
                route = route.strip() if route else ""
                dosage_info = f"{dosage_form} {route}".strip() if dosage_form or route else ""

                # Extract submission dates as approval dates
                submissions = entry.get("submissions", [])
                approval_dates = []
                for submission in submissions:
                    status_date = submission.get("submission_status_date", "")
                    if status_date and submission.get("submission_status") == "AP":  # Approved
                        approval_dates.append(status_date)

                # Extract sponsor information as manufacturer
                sponsor_name = entry.get("sponsor_name", "").strip()
                manufacturers = [sponsor_name] if sponsor_name else []

                drug_dict = {
                    "generic_name": primary_name,
                    "brand_names": brand_names,
                    "manufacturers": manufacturers,
                    "formulations": formulations,
                    "therapeutic_class": "",
                    "indications_and_usage": "",
                    "mechanism_of_action": "",
                    "contraindications": [],
                    "warnings": [],
                    "precautions": [],
                    "adverse_reactions": [],
                    "drug_interactions": {},
                    "dosage_and_administration": dosage_info,
                    "pharmacokinetics": "",
                    "pharmacodynamics": "",
                    "boxed_warning": "",
                    "clinical_studies": "",
                    "pediatric_use": "",
                    "geriatric_use": "",
                    "pregnancy": "",
                    "nursing_mothers": "",
                    "overdosage": "",
                    "nonclinical_toxicology": "",
                    "approval_dates": approval_dates,
                    "orange_book_codes": [],
                    "application_numbers": [application_number],
                    "total_formulations": len(formulations),
                    "data_sources": ["fda_drugs"],
                    "confidence_score": 0.8,  # High confidence for Drugs@FDA data
                    "has_clinical_data": len(submissions) > 0,
                }

                drugs.append(drug_dict)

    except Exception as e:
        logger.exception(f"Error parsing Drugs@FDA file: {e}")
        return []

    logger.info(f"Parsed {len(drugs)} drugs from Drugs@FDA file")
    return drugs

def merge_drug_data(ndc_drugs: list[dict[str, Any]], drugs_fda: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge drug data from both sources, prioritizing more complete information"""
    logger.info("Merging drug data from both sources")

    # Create lookup by generic name for merging
    merged_drugs = {}

    # Process NDC drugs first (lower confidence)
    for drug in ndc_drugs:
        generic_name = drug["generic_name"].lower().strip()
        merged_drugs[generic_name] = drug.copy()

    # Process Drugs@FDA drugs (higher confidence), merge where possible
    for drug in drugs_fda:
        generic_name = drug["generic_name"].lower().strip()

        if generic_name in merged_drugs:
            # Merge data, prioritizing non-empty values from higher confidence source
            existing = merged_drugs[generic_name]

            # Merge arrays
            existing["brand_names"] = list(set(existing["brand_names"] + drug["brand_names"]))
            existing["manufacturers"] = list(set(existing["manufacturers"] + drug["manufacturers"]))
            existing["formulations"].extend(drug["formulations"])
            existing["approval_dates"] = list(set(existing["approval_dates"] + drug["approval_dates"]))
            existing["application_numbers"] = list(set(existing["application_numbers"] + drug["application_numbers"]))
            existing["data_sources"] = list(set(existing["data_sources"] + drug["data_sources"]))

            # Use higher confidence values for text fields
            for field in ["dosage_and_administration", "therapeutic_class"]:
                if drug[field] and not existing[field]:
                    existing[field] = drug[field]

            # Update metadata
            existing["total_formulations"] = len(existing["formulations"])
            existing["confidence_score"] = max(existing["confidence_score"], drug["confidence_score"])
            existing["has_clinical_data"] = existing["has_clinical_data"] or drug["has_clinical_data"]

            merged_drugs[generic_name] = existing
        else:
            # New drug from Drugs@FDA
            merged_drugs[generic_name] = drug.copy()

    result = list(merged_drugs.values())
    logger.info(f"Merged into {len(result)} unique drugs")
    return result

def insert_drugs_to_database(drugs: list[dict[str, Any]]) -> bool:
    """Insert drug information into PostgreSQL database"""
    try:
        # Database connection
        conn = psycopg2.connect(
            host="localhost",
            database="intelluxe_public",
            user="intelluxe",
            password="secure_password",
        )

        cursor = conn.cursor()

        logger.info(f"Inserting {len(drugs)} drugs into database")

        # Use UPSERT to handle duplicates
        for i, drug_data in enumerate(drugs):
            try:
                cursor.execute("""
                    INSERT INTO drug_information (
                        generic_name, brand_names, manufacturers, formulations,
                        therapeutic_class, indications_and_usage, mechanism_of_action,
                        contraindications, warnings, precautions, adverse_reactions,
                        drug_interactions, dosage_and_administration, pharmacokinetics,
                        pharmacodynamics, boxed_warning, clinical_studies,
                        pediatric_use, geriatric_use, pregnancy, nursing_mothers,
                        overdosage, nonclinical_toxicology, approval_dates,
                        orange_book_codes, application_numbers, total_formulations,
                        data_sources, confidence_score, has_clinical_data, last_updated
                    ) VALUES (
                        %(generic_name)s, %(brand_names)s, %(manufacturers)s, %(formulations)s,
                        %(therapeutic_class)s, %(indications_and_usage)s, %(mechanism_of_action)s,
                        %(contraindications)s, %(warnings)s, %(precautions)s, %(adverse_reactions)s,
                        %(drug_interactions)s, %(dosage_and_administration)s, %(pharmacokinetics)s,
                        %(pharmacodynamics)s, %(boxed_warning)s, %(clinical_studies)s,
                        %(pediatric_use)s, %(geriatric_use)s, %(pregnancy)s, %(nursing_mothers)s,
                        %(overdosage)s, %(nonclinical_toxicology)s, %(approval_dates)s,
                        %(orange_book_codes)s, %(application_numbers)s, %(total_formulations)s,
                        %(data_sources)s, %(confidence_score)s, %(has_clinical_data)s, NOW()
                    )
                    ON CONFLICT (generic_name) DO UPDATE SET
                        brand_names = EXCLUDED.brand_names,
                        manufacturers = EXCLUDED.manufacturers,
                        formulations = EXCLUDED.formulations,
                        therapeutic_class = COALESCE(NULLIF(EXCLUDED.therapeutic_class, ''), drug_information.therapeutic_class),
                        indications_and_usage = COALESCE(NULLIF(EXCLUDED.indications_and_usage, ''), drug_information.indications_and_usage),
                        mechanism_of_action = COALESCE(NULLIF(EXCLUDED.mechanism_of_action, ''), drug_information.mechanism_of_action),
                        contraindications = EXCLUDED.contraindications,
                        warnings = EXCLUDED.warnings,
                        precautions = EXCLUDED.precautions,
                        adverse_reactions = EXCLUDED.adverse_reactions,
                        drug_interactions = EXCLUDED.drug_interactions,
                        dosage_and_administration = COALESCE(NULLIF(EXCLUDED.dosage_and_administration, ''), drug_information.dosage_and_administration),
                        pharmacokinetics = COALESCE(NULLIF(EXCLUDED.pharmacokinetics, ''), drug_information.pharmacokinetics),
                        pharmacodynamics = COALESCE(NULLIF(EXCLUDED.pharmacodynamics, ''), drug_information.pharmacodynamics),
                        boxed_warning = COALESCE(NULLIF(EXCLUDED.boxed_warning, ''), drug_information.boxed_warning),
                        clinical_studies = COALESCE(NULLIF(EXCLUDED.clinical_studies, ''), drug_information.clinical_studies),
                        pediatric_use = COALESCE(NULLIF(EXCLUDED.pediatric_use, ''), drug_information.pediatric_use),
                        geriatric_use = COALESCE(NULLIF(EXCLUDED.geriatric_use, ''), drug_information.geriatric_use),
                        pregnancy = COALESCE(NULLIF(EXCLUDED.pregnancy, ''), drug_information.pregnancy),
                        nursing_mothers = COALESCE(NULLIF(EXCLUDED.nursing_mothers, ''), drug_information.nursing_mothers),
                        overdosage = COALESCE(NULLIF(EXCLUDED.overdosage, ''), drug_information.overdosage),
                        nonclinical_toxicology = COALESCE(NULLIF(EXCLUDED.nonclinical_toxicology, ''), drug_information.nonclinical_toxicology),
                        approval_dates = EXCLUDED.approval_dates,
                        orange_book_codes = EXCLUDED.orange_book_codes,
                        application_numbers = EXCLUDED.application_numbers,
                        total_formulations = EXCLUDED.total_formulations,
                        data_sources = EXCLUDED.data_sources,
                        confidence_score = GREATEST(drug_information.confidence_score, EXCLUDED.confidence_score),
                        has_clinical_data = drug_information.has_clinical_data OR EXCLUDED.has_clinical_data,
                        last_updated = NOW()
                """, {
                    "generic_name": drug_data.get("generic_name", ""),
                    "brand_names": drug_data.get("brand_names", []),
                    "manufacturers": drug_data.get("manufacturers", []),
                    "formulations": json.dumps(drug_data.get("formulations", [])),
                    "therapeutic_class": drug_data.get("therapeutic_class", ""),
                    "indications_and_usage": drug_data.get("indications_and_usage", ""),
                    "mechanism_of_action": drug_data.get("mechanism_of_action", ""),
                    "contraindications": drug_data.get("contraindications", []),
                    "warnings": drug_data.get("warnings", []),
                    "precautions": drug_data.get("precautions", []),
                    "adverse_reactions": drug_data.get("adverse_reactions", []),
                    "drug_interactions": json.dumps(drug_data.get("drug_interactions", {})),
                    "dosage_and_administration": drug_data.get("dosage_and_administration", ""),
                    "pharmacokinetics": drug_data.get("pharmacokinetics", ""),
                    "pharmacodynamics": drug_data.get("pharmacodynamics", ""),
                    "boxed_warning": drug_data.get("boxed_warning", ""),
                    "clinical_studies": drug_data.get("clinical_studies", ""),
                    "pediatric_use": drug_data.get("pediatric_use", ""),
                    "geriatric_use": drug_data.get("geriatric_use", ""),
                    "pregnancy": drug_data.get("pregnancy", ""),
                    "nursing_mothers": drug_data.get("nursing_mothers", ""),
                    "overdosage": drug_data.get("overdosage", ""),
                    "nonclinical_toxicology": drug_data.get("nonclinical_toxicology", ""),
                    "approval_dates": drug_data.get("approval_dates", []),
                    "orange_book_codes": drug_data.get("orange_book_codes", []),
                    "application_numbers": drug_data.get("application_numbers", []),
                    "total_formulations": drug_data.get("total_formulations", 0),
                    "data_sources": drug_data.get("data_sources", []),
                    "confidence_score": drug_data.get("confidence_score", 0.0),
                    "has_clinical_data": drug_data.get("has_clinical_data", False),
                })

                if (i + 1) % 1000 == 0:
                    logger.info(f"Processed {i + 1}/{len(drugs)} drugs")

            except Exception as e:
                logger.warning(f"Failed to insert drug {drug_data.get('generic_name', 'unknown')}: {e}")
                continue

        conn.commit()

        # Get final count
        cursor.execute("SELECT COUNT(*) FROM drug_information")
        total_count = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        logger.info(f"Successfully inserted FDA drug data. Database now contains {total_count} total drugs")
        return True

    except Exception as e:
        logger.exception(f"Error inserting drugs into database: {e}")
        return False

def main():
    """Main function"""
    fda_base_dir = "/home/intelluxe/database/medical_complete/fda"

    # Find JSON files
    ndc_file = os.path.join(fda_base_dir, "ndc", "drug-ndc-0001-of-0001.json")
    drugs_fda_file = os.path.join(fda_base_dir, "drugs_fda", "drug-drugsfda-0001-of-0001.json")

    all_drugs = []

    # Parse NDC file if it exists
    if os.path.exists(ndc_file):
        logger.info("Processing NDC file...")
        ndc_drugs = parse_ndc_file(ndc_file)
        all_drugs.extend(ndc_drugs)
    else:
        logger.warning(f"NDC file not found: {ndc_file}")
        ndc_drugs = []

    # Parse Drugs@FDA file if it exists
    if os.path.exists(drugs_fda_file):
        logger.info("Processing Drugs@FDA file...")
        drugs_fda = parse_drugs_fda_file(drugs_fda_file)

        # Merge with NDC data if both exist
        if ndc_drugs and drugs_fda:
            logger.info("Merging NDC and Drugs@FDA data...")
            all_drugs = merge_drug_data(ndc_drugs, drugs_fda)
        else:
            all_drugs.extend(drugs_fda)
    else:
        logger.warning(f"Drugs@FDA file not found: {drugs_fda_file}")

    if not all_drugs:
        logger.error("No drug data parsed from JSON files")
        return False

    # Insert into database
    success = insert_drugs_to_database(all_drugs)
    if success:
        logger.info(f"✅ Successfully processed {len(all_drugs)} FDA drugs")
        return True
    logger.error("❌ Failed to insert drugs into database")
    return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
