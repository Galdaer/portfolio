"""
Optimized multi-core FDA parser
Utilizes all available CPU cores for JSON parsing and database operations
"""

import json
import logging
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from typing import Any

logger = logging.getLogger(__name__)


def _extract_text_field(field_data) -> str:
    """Extract text from various field formats in drug labels"""
    if not field_data:
        return ""
    
    if isinstance(field_data, str):
        return field_data.strip()
    elif isinstance(field_data, list):
        # Handle list of strings or complex objects
        text_parts = []
        for item in field_data:
            if isinstance(item, str):
                text_parts.append(item.strip())
            elif isinstance(item, dict):
                # Extract text from dict items
                if "text" in item:
                    text_parts.append(str(item["text"]).strip())
                elif "content" in item:
                    if isinstance(item["content"], list):
                        text_parts.extend([str(c) for c in item["content"] if c])
                    else:
                        text_parts.append(str(item["content"]).strip())
                elif "section" in item and "content" in item:
                    # Handle section-based content
                    section_text = f"{item['section']}: {item['content']}"
                    text_parts.append(section_text)
                else:
                    # Convert entire dict to readable string
                    text_parts.append(str(item))
            else:
                text_parts.append(str(item))
        
        return "; ".join([part for part in text_parts if part]).strip()
    elif isinstance(field_data, dict):
        # Handle various dict structures
        if "text" in field_data:
            text_content = field_data["text"]
            if isinstance(text_content, str):
                return text_content.strip()
            elif isinstance(text_content, list):
                return "; ".join([str(t) for t in text_content if t]).strip()
        elif "content" in field_data:
            content = field_data["content"]
            if isinstance(content, str):
                return content.strip()
            elif isinstance(content, list):
                return "; ".join([str(c) for c in content if c]).strip()
        elif "general" in field_data:
            # Handle dosage_and_administration structure
            parts = []
            for key, value in field_data.items():
                if value and key != "limitations":
                    parts.append(f"{key.replace('_', ' ').title()}: {value}")
            return "; ".join(parts).strip()
        else:
            # For other dict structures, create readable summary
            readable_parts = []
            for key, value in field_data.items():
                if value:
                    if isinstance(value, (list, dict)):
                        readable_parts.append(f"{key}: {len(value) if isinstance(value, list) else 'complex'} items")
                    else:
                        readable_parts.append(f"{key}: {str(value)[:100]}")
            return "; ".join(readable_parts).strip() if readable_parts else str(field_data).strip()
    else:
        return str(field_data).strip()


def parse_json_file_worker(json_file_path: str, dataset_type: str) -> tuple[str, list[dict[str, Any]]]:
    """Worker function for multiprocessing JSON parsing"""
    try:
        logger.info(f"Worker parsing {dataset_type}: {json_file_path}")
        records = []

        with open(json_file_path, encoding="utf-8") as f:
            data = json.load(f)

        if dataset_type in {"ndc", "ndc_directory"}:
            records = parse_ndc_data_worker(data)
        elif dataset_type == "drugs_fda":
            records = parse_drugs_fda_data_worker(data)
        elif dataset_type in {"drug_labels", "labels"}:
            records = parse_drug_labels_data_worker(data)
        elif dataset_type == "orange_book":
            # Orange Book is handled differently (CSV parsing)
            logger.info(f"Skipping Orange Book JSON file: {json_file_path}")
            return json_file_path, []
        else:
            logger.warning(f"Unknown dataset type: {dataset_type}")
            return json_file_path, []

        logger.info(f"Worker parsed {len(records)} records from {json_file_path}")
        return json_file_path, records

    except Exception as e:
        logger.exception(f"Worker failed to parse {json_file_path}: {e}")
        return json_file_path, []


def parse_ndc_data_worker(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse NDC data structure"""
    records = []

    if isinstance(data, dict) and "results" in data:
        results = data["results"]
        for record in results:
            parsed_record = parse_ndc_record_worker(record)
            if parsed_record:
                records.append(parsed_record)

    return records


def parse_ndc_record_worker(ndc_data: dict[str, Any]) -> dict[str, Any] | None:
    """Parse a single NDC record"""
    try:
        # Extract basic drug information
        product_ndc = str(ndc_data.get("product_ndc", "")).strip()
        if not product_ndc:
            return None

        generic_name = str(ndc_data.get("generic_name", "")).strip()
        brand_name = str(ndc_data.get("brand_name", "")).strip()

        # Get labeler information
        labeler_name = str(ndc_data.get("labeler_name", "")).strip()

        # Get product information
        product_type = str(ndc_data.get("product_type", "")).strip()
        route = ndc_data.get("route", [])
        route = ", ".join([str(r) for r in route]) if isinstance(route, list) else str(route)

        # Get dosage form and strength
        dosage_form = str(ndc_data.get("dosage_form", "")).strip()
        active_ingredients = ndc_data.get("active_ingredients", [])

        # Parse active ingredients
        ingredients_list = []
        if isinstance(active_ingredients, list):
            for ingredient in active_ingredients:
                if isinstance(ingredient, dict):
                    name = ingredient.get("name", "")
                    strength = ingredient.get("strength", "")
                    if name:
                        ingredient_str = f"{name}"
                        if strength:
                            ingredient_str += f" {strength}"
                        ingredients_list.append(ingredient_str)

        active_ingredients_str = "; ".join(ingredients_list)

        # Marketing status
        marketing_status = str(ndc_data.get("marketing_status", "")).strip()
        
        # Extract therapeutic class from pharm_class field
        therapeutic_class = ""
        pharm_class_list = ndc_data.get("pharm_class", [])
        if isinstance(pharm_class_list, list):
            # Look for Established Pharmacologic Class (EPC) entries
            for pharm_class in pharm_class_list:
                if isinstance(pharm_class, str) and "[EPC]" in pharm_class:
                    therapeutic_class = pharm_class.replace(" [EPC]", "")
                    break
        elif isinstance(pharm_class_list, str) and "[EPC]" in pharm_class_list:
            therapeutic_class = pharm_class_list.replace(" [EPC]", "")

        # Validate that we have meaningful data - skip records without drug names
        if not generic_name and not brand_name:
            logger.debug(f"Skipping NDC record {product_ndc} - no drug names")
            return None

        # Create search text for full-text search
        search_parts = [
            product_ndc, generic_name, brand_name, labeler_name,
            active_ingredients_str, dosage_form, route,
        ]
        search_text = " ".join([part for part in search_parts if part]).lower()

        return {
            "ndc": product_ndc,
            "name": brand_name or generic_name or "Unknown",
            "generic_name": generic_name,
            "brand_name": brand_name,
            "manufacturer": labeler_name,
            "ingredients": active_ingredients_str.split("; ") if active_ingredients_str else [],
            "dosage_form": dosage_form,
            "route": route,
            "product_type": product_type,
            "marketing_status": marketing_status,
            "strength": active_ingredients_str,  # Strength included in active ingredients
            "therapeutic_class": therapeutic_class,  # Extracted from pharm_class
            "search_text": search_text,
            "data_sources": ["ndc_directory"],
            # Keep FDA-specific fields for compatibility
            "proprietary_name": brand_name,
            "nonproprietary_name": generic_name,
            "dosage_form_name": dosage_form,
            "route_of_administration": route,
            "active_ingredients": active_ingredients_str,
            "labeler_name": labeler_name,
            "substance_name": generic_name,
            # Merge fields for grouping
            "_merge_generic_name": generic_name.lower().strip() if generic_name else "",
            "_merge_brand_name": brand_name.lower().strip() if brand_name else "",
            "_merge_manufacturer": labeler_name.lower().strip() if labeler_name else "",
        }

    except Exception as e:
        logger.warning(f"Failed to parse NDC record: {e}")
        return None


def parse_drugs_fda_data_worker(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse Drugs@FDA data structure"""
    records = []

    if isinstance(data, dict) and "results" in data:
        results = data["results"]
        for record in results:
            parsed_record = parse_drugs_fda_record_worker(record)
            if parsed_record:
                records.append(parsed_record)

    return records


def parse_drugs_fda_record_worker(drug_data: dict[str, Any]) -> dict[str, Any] | None:
    """Parse a single Drugs@FDA record"""
    try:
        # Extract basic information
        application_number = str(drug_data.get("application_number", "")).strip()
        if not application_number:
            return None

        sponsor_name = str(drug_data.get("sponsor_name", "")).strip()

        # Get products
        products = drug_data.get("products", [])
        if not products:
            return None

        # Take the first product for now (could be enhanced to handle multiple)
        product = products[0] if isinstance(products, list) else products

        brand_name = str(product.get("brand_name", "")).strip()
        generic_name = str(product.get("active_ingredients", [{}])[0].get("name", "")).strip()

        dosage_form = str(product.get("dosage_form", "")).strip()
        route = str(product.get("route", "")).strip()
        marketing_status = str(product.get("marketing_status", "")).strip()

        # Get application details
        applications = drug_data.get("applications", [])
        application_type = ""
        if applications:
            app = applications[0] if isinstance(applications, list) else applications
            application_type = str(app.get("application_type", "")).strip()
        
        # Extract approval date from submissions (earliest approval date)
        approval_date = ""
        submissions = drug_data.get("submissions", [])
        approval_dates = []
        
        for submission in submissions:
            status = submission.get("submission_status", "")
            status_date = submission.get("submission_status_date", "")
            
            # Look for approved submissions
            if status in ["AP", "APPROVED"] and status_date:
                try:
                    # Convert YYYYMMDD to readable format
                    year = status_date[:4]
                    month = status_date[4:6]
                    day = status_date[6:8]
                    
                    if len(year) == 4 and len(month) == 2 and len(day) == 2:
                        # Store as sortable date for finding earliest
                        approval_dates.append((status_date, f"{month}/{day}/{year}"))
                except:
                    continue
        
        # Use the earliest approval date
        if approval_dates:
            approval_dates.sort()  # Sort by YYYYMMDD format
            approval_date = approval_dates[0][1]  # Get formatted date

        # Validate that we have meaningful data - skip records without drug names
        if not generic_name and not brand_name:
            logger.debug(f"Skipping Drugs@FDA record {application_number} - no drug names")
            return None

        # Create search text
        search_parts = [
            application_number, sponsor_name, brand_name, generic_name,
            dosage_form, route, marketing_status,
        ]
        search_text = " ".join([part for part in search_parts if part]).lower()

        return {
            "ndc": f"FDA_{application_number}",  # Using application number as synthetic identifier
            "name": brand_name or generic_name or "Unknown",
            "generic_name": generic_name,
            "brand_name": brand_name,
            "manufacturer": sponsor_name,
            "ingredients": [generic_name] if generic_name else [],
            "dosage_form": dosage_form,
            "route": route,
            "application_number": application_number,
            "applicant": sponsor_name,
            "product_type": application_type,
            "marketing_status": marketing_status,
            "approval_date": approval_date,
            "strength": "",  # Not readily available in this dataset
            "therapeutic_class": "",  # Not available in Drugs@FDA
            "search_text": search_text,
            "data_sources": ["drugs_fda"],
            # Keep FDA-specific fields for compatibility
            "proprietary_name": brand_name,
            "nonproprietary_name": generic_name,
            "dosage_form_name": dosage_form,
            "route_of_administration": route,
            "active_ingredients": generic_name,
            "labeler_name": sponsor_name,
            "substance_name": generic_name,
            # Merge fields for grouping
            "_merge_generic_name": generic_name.lower().strip() if generic_name else "",
            "_merge_brand_name": brand_name.lower().strip() if brand_name else "",
            "_merge_manufacturer": sponsor_name.lower().strip() if sponsor_name else "",
            "_merge_applicant": sponsor_name.lower().strip() if sponsor_name else "",
            "_merge_app_number": application_number,
        }

    except Exception as e:
        logger.warning(f"Failed to parse Drugs@FDA record: {e}")
        return None


def parse_drug_labels_data_worker(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse drug labels data structure"""
    records = []

    if isinstance(data, dict) and "results" in data:
        results = data["results"]
        for record in results:
            parsed_record = parse_drug_label_record_worker(record)
            if parsed_record:
                records.append(parsed_record)

    return records


def parse_drug_label_record_worker(label_data: dict[str, Any]) -> dict[str, Any] | None:
    """Parse a single drug label record with actual FDA label structure"""
    try:
        # Extract product information from openfda object (where it actually is)
        openfda = label_data.get("openfda", {})
        
        # Extract NDC codes from openfda.product_ndc
        product_ndc = openfda.get("product_ndc", [])
        if isinstance(product_ndc, list) and product_ndc:
            ndc_code = str(product_ndc[0]).strip()
        elif isinstance(product_ndc, str):
            ndc_code = product_ndc.strip()
        else:
            ndc_code = ""

        if not ndc_code:
            # Try to use set_id as fallback if no NDC
            set_id = label_data.get("set_id", "").strip()
            if not set_id:
                return None
            ndc_code = f"LABEL_{set_id[:8]}"

        # Get brand and generic names from openfda
        brand_name_list = openfda.get("brand_name", [])
        if isinstance(brand_name_list, list) and brand_name_list:
            brand_name = str(brand_name_list[0]).strip()
        elif isinstance(brand_name_list, str):
            brand_name = brand_name_list.strip()
        else:
            brand_name = ""

        generic_name_list = openfda.get("generic_name", [])
        if isinstance(generic_name_list, list) and generic_name_list:
            generic_name = str(generic_name_list[0]).strip()
        elif isinstance(generic_name_list, str):
            generic_name = generic_name_list.strip()
        else:
            generic_name = ""

        # Get manufacturer from openfda
        manufacturer_list = openfda.get("manufacturer_name", [])
        if isinstance(manufacturer_list, list) and manufacturer_list:
            manufacturer = str(manufacturer_list[0]).strip()
        elif isinstance(manufacturer_list, str):
            manufacturer = manufacturer_list.strip()
        else:
            manufacturer = ""

        # Get route from openfda
        route_list = openfda.get("route", [])
        if isinstance(route_list, list):
            route = ", ".join([str(r) for r in route_list])
        elif isinstance(route_list, str):
            route = route_list
        else:
            route = ""

        # Get active ingredients from openfda substance_name
        substance_names = openfda.get("substance_name", [])
        if isinstance(substance_names, list):
            active_ingredients = "; ".join([str(s) for s in substance_names])
        else:
            active_ingredients = str(substance_names) if substance_names else ""

        # Extract dosage form from openfda fields
        dosage_form = ""
        dosage_form_list = openfda.get("dosage_form", [])
        if isinstance(dosage_form_list, list) and dosage_form_list:
            dosage_form = str(dosage_form_list[0]).strip()
        elif isinstance(dosage_form_list, str):
            dosage_form = dosage_form_list.strip()
        
        # Try dosage_form_name as fallback
        if not dosage_form:
            dosage_form_name_list = openfda.get("dosage_form_name", [])
            if isinstance(dosage_form_name_list, list) and dosage_form_name_list:
                dosage_form = str(dosage_form_name_list[0]).strip()
            elif isinstance(dosage_form_name_list, str):
                dosage_form = dosage_form_name_list.strip()

        # Extract clinical information from drug labels (use actual field names)
        contraindications = _extract_text_field(label_data.get("contraindications"))
        
        # Use warnings_and_cautions instead of warnings (actual field name)
        warnings = _extract_text_field(label_data.get("warnings_and_cautions"))
        if not warnings:
            # Fallback to warnings if available
            warnings = _extract_text_field(label_data.get("warnings"))
        
        # Get adverse reactions 
        adverse_reactions = _extract_text_field(label_data.get("adverse_reactions"))
        
        # Extract drug interactions from multiple possible fields
        drug_interactions_text = ""
        interaction_sources = []
        
        if label_data.get("drug_interactions"):
            interaction_sources.append(_extract_text_field(label_data.get("drug_interactions")))
        if label_data.get("drug_and_or_laboratory_test_interactions"):
            interaction_sources.append(_extract_text_field(label_data.get("drug_and_or_laboratory_test_interactions")))
        if label_data.get("drug_interactions_table"):
            interaction_sources.append(_extract_text_field(label_data.get("drug_interactions_table")))
            
        if interaction_sources:
            drug_interactions_text = "; ".join([source for source in interaction_sources if source])
        
        # Extract precautions from multiple possible fields
        precautions_text = ""
        precaution_sources = []
        
        if label_data.get("precautions"):
            precaution_sources.append(_extract_text_field(label_data.get("precautions")))
        if label_data.get("general_precautions"):
            precaution_sources.append(_extract_text_field(label_data.get("general_precautions")))
            
        if precaution_sources:
            precautions_text = "; ".join([source for source in precaution_sources if source])
        
        # Clinical data from actual fields
        indications_and_usage = _extract_text_field(label_data.get("indications_and_usage"))
        dosage_and_administration = _extract_text_field(label_data.get("dosage_and_administration"))
        
        # Extract pharmacology information
        clinical_pharmacology = _extract_text_field(label_data.get("clinical_pharmacology"))
        mechanism_of_action = _extract_text_field(label_data.get("mechanism_of_action"))
        pharmacokinetics = _extract_text_field(label_data.get("pharmacokinetics"))
        pharmacodynamics = _extract_text_field(label_data.get("pharmacodynamics"))
        
        # If mechanism/pharmacokinetics/pharmacodynamics aren't separate, try to extract from clinical_pharmacology
        if not mechanism_of_action and clinical_pharmacology:
            if "mechanism of action" in clinical_pharmacology.lower():
                mechanism_of_action = clinical_pharmacology
        if not pharmacokinetics and clinical_pharmacology:
            if "pharmacokinetics" in clinical_pharmacology.lower():
                pharmacokinetics = clinical_pharmacology
        if not pharmacodynamics and clinical_pharmacology:
            if "pharmacodynamics" in clinical_pharmacology.lower():
                pharmacodynamics = clinical_pharmacology
        
        # Extract additional clinical fields that we weren't capturing before
        boxed_warning = _extract_text_field(label_data.get("boxed_warning"))
        clinical_studies = _extract_text_field(label_data.get("clinical_studies"))
        pediatric_use = _extract_text_field(label_data.get("pediatric_use"))
        geriatric_use = _extract_text_field(label_data.get("geriatric_use"))
        pregnancy = _extract_text_field(label_data.get("pregnancy"))
        nursing_mothers = _extract_text_field(label_data.get("nursing_mothers"))
        overdosage = _extract_text_field(label_data.get("overdosage"))
        nonclinical_toxicology = _extract_text_field(label_data.get("nonclinical_toxicology"))
        
        # Try alternative field names for better coverage
        if not warnings:
            warnings = _extract_text_field(label_data.get("warnings_and_precautions"))
        if not precautions_text:
            precautions_text = _extract_text_field(label_data.get("warnings_and_precautions"))
            if not precautions_text:
                precautions_text = _extract_text_field(label_data.get("special_populations"))
        
        # Try additional drug interaction field names
        if not drug_interactions_text:
            alt_interactions = []
            for field_name in ["drug_drug_interactions", "clinically_significant_drug_interactions", "drug_food_interactions"]:
                field_value = _extract_text_field(label_data.get(field_name))
                if field_value:
                    alt_interactions.append(field_value)
            if alt_interactions:
                drug_interactions_text = "; ".join(alt_interactions)
        
        # Extract approval date from effective_time if available
        approval_date = ""
        effective_time = label_data.get("effective_time", "")
        if effective_time and len(str(effective_time)) == 8:  # Format: YYYYMMDD
            try:
                year = effective_time[:4]
                month = effective_time[4:6] 
                day = effective_time[6:8]
                approval_date = f"{month}/{day}/{year}"
            except:
                pass
        
        # Extract therapeutic class from openfda.pharm_class_epc
        therapeutic_class = ""
        pharm_class_epc_list = openfda.get("pharm_class_epc", [])
        if isinstance(pharm_class_epc_list, list) and pharm_class_epc_list:
            # Take first EPC entry and clean it
            therapeutic_class = str(pharm_class_epc_list[0]).strip()
            if " [EPC]" in therapeutic_class:
                therapeutic_class = therapeutic_class.replace(" [EPC]", "")
        elif isinstance(pharm_class_epc_list, str) and pharm_class_epc_list:
            therapeutic_class = pharm_class_epc_list.strip()
            if " [EPC]" in therapeutic_class:
                therapeutic_class = therapeutic_class.replace(" [EPC]", "")

        # Validate that we have meaningful data - skip records without drug names
        if not generic_name and not brand_name:
            logger.debug(f"Skipping drug label record {ndc_code} - no drug names")
            return None

        # Create search text
        search_parts = [
            ndc_code, brand_name, generic_name, manufacturer,
            dosage_form, route, active_ingredients,
        ]
        search_text = " ".join([part for part in search_parts if part]).lower()

        return {
            "ndc": ndc_code,
            "name": brand_name or generic_name or "Unknown",
            "generic_name": generic_name,
            "brand_name": brand_name,
            "manufacturer": manufacturer,
            "ingredients": active_ingredients.split("; ") if active_ingredients else [],
            "dosage_form": dosage_form,
            "route": route,
            "product_type": "HUMAN PRESCRIPTION DRUG",  # Most drug labels are prescription
            "marketing_status": "Prescription",
            "strength": active_ingredients,  # Strength info is in active ingredients
            "therapeutic_class": therapeutic_class,  # Extracted from openfda.pharm_class_epc
            "approval_date": approval_date,  # Extracted from effective_time
            
            # Clinical information from labels
            "contraindications": [contraindications] if contraindications else [],
            "warnings": [warnings] if warnings else [],
            "precautions": [precautions_text] if precautions_text else [],
            "adverse_reactions": [adverse_reactions] if adverse_reactions else [],
            "drug_interactions": {"interactions": drug_interactions_text} if drug_interactions_text else {},
            "indications_and_usage": indications_and_usage,
            "dosage_and_administration": dosage_and_administration,
            "mechanism_of_action": mechanism_of_action,
            "pharmacokinetics": pharmacokinetics,
            "pharmacodynamics": pharmacodynamics,
            
            # Additional clinical fields
            "boxed_warning": boxed_warning,
            "clinical_studies": clinical_studies,
            "pediatric_use": pediatric_use,
            "geriatric_use": geriatric_use,
            "pregnancy": pregnancy,
            "nursing_mothers": nursing_mothers,
            "overdosage": overdosage,
            "nonclinical_toxicology": nonclinical_toxicology,
            
            "search_text": search_text,
            "data_sources": ["drug_labels"],
            # Keep FDA-specific fields for compatibility
            "proprietary_name": brand_name,
            "nonproprietary_name": generic_name,
            "dosage_form_name": dosage_form,
            "route_of_administration": route,
            "active_ingredients": active_ingredients,
            "labeler_name": manufacturer,
            "substance_name": generic_name,
            # Merge fields for grouping
            "_merge_generic_name": generic_name.lower().strip() if generic_name else "",
            "_merge_brand_name": brand_name.lower().strip() if brand_name else "",
            "_merge_manufacturer": manufacturer.lower().strip() if manufacturer else "",
        }

    except Exception as e:
        logger.warning(f"Failed to parse drug label record: {e}")
        return None


class OptimizedDrugParser:
    """Multi-core FDA data parser with parallel processing"""

    def __init__(self, max_workers: int | None = None):
        """Initialize with specified number of workers"""
        if max_workers is None:
            max_workers = max(1, mp.cpu_count() // 2)
        self.max_workers = max_workers

        logger.info(
            f"Initialized FDA parser with {self.max_workers} workers (CPU cores: {mp.cpu_count()})",
        )

    async def parse_json_files_parallel(
        self, json_files: list[str], dataset_type: str,
    ) -> list[dict[str, Any]]:
        """Parse multiple JSON files in parallel using all CPU cores"""
        logger.info(f"Parsing {len(json_files)} FDA {dataset_type} files using {self.max_workers} cores")

        all_records = []
        parsed_files = []

        # Create tasks for parallel processing
        tasks = [(json_file, dataset_type) for json_file in json_files]

        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all parsing tasks
            future_to_file = {
                executor.submit(parse_json_file_worker, json_file, dataset_type): json_file
                for json_file, dataset_type in tasks
            }

            # Process completed tasks
            for future in future_to_file:
                json_file = future_to_file[future]
                try:
                    file_path, records = future.result()
                    all_records.extend(records)
                    parsed_files.append(file_path)
                except Exception as e:
                    logger.exception(f"Failed to parse {json_file}: {e}")

        total_records = len(all_records)
        logger.info(
            f"Parallel parsing completed: {total_records} total records from {len(parsed_files)} files",
        )

        return all_records

    def parse_orange_book_file(self, csv_file_path: str) -> list[dict[str, Any]]:
        """Parse Orange Book CSV file (single-threaded as it's usually one file)"""
        logger.info(f"Parsing Orange Book CSV file: {csv_file_path}")
        drugs = []

        try:
            import pandas as pd

            # Read the Orange Book products file (uses ~ as delimiter)
            df = pd.read_csv(csv_file_path, sep="~", encoding="utf-8", low_memory=False, on_bad_lines="skip")

            for _, row in df.iterrows():
                drug = self._parse_orange_book_record(row)
                if drug:
                    drugs.append(drug)

            logger.info(f"Parsed {len(drugs)} drugs from Orange Book")
            return drugs

        except Exception as e:
            logger.exception(f"Failed to parse Orange Book file {csv_file_path}: {e}")
            return []

    def _clean_field_value(self, value: Any) -> str:
        """Clean field values to handle pandas nan values"""
        if value is None:
            return ""
        str_value = str(value).strip()
        # Handle pandas nan values
        if str_value.lower() in ['nan', 'none', 'null']:
            return ""
        return str_value

    def _parse_orange_book_record(self, row) -> dict[str, Any] | None:
        """Parse a single Orange Book record"""
        try:
            # Extract fields (Orange Book has specific column names) with nan cleaning
            ingredient = self._clean_field_value(row.get("Ingredient", ""))
            trade_name = self._clean_field_value(row.get("Trade_Name", ""))
            applicant = self._clean_field_value(row.get("Applicant_Full_Name", row.get("Applicant", "")))
            product_no = self._clean_field_value(row.get("Product_No", ""))
            # DF;Route format like "AEROSOL, FOAM;RECTAL"
            df_route = self._clean_field_value(row.get("DF;Route", ""))
            dosage_form = df_route.split(";")[0] if ";" in df_route else df_route
            route = df_route.split(";")[1] if ";" in df_route else ""
            strength = self._clean_field_value(row.get("Strength", ""))
            approval_date = self._clean_field_value(row.get("Approval_Date", ""))
            
            # Extract additional Orange Book fields with nan cleaning
            te_code = self._clean_field_value(row.get("TE_Code", ""))  # Therapeutic Equivalence Code
            rld = self._clean_field_value(row.get("RLD", ""))  # Reference Listed Drug
            appl_no = self._clean_field_value(row.get("Appl_No", ""))  # Application Number

            # Validate that we have meaningful data - skip records without drug names
            if not ingredient and not trade_name:
                return None

            # Create search text
            search_parts = [ingredient, trade_name, applicant, dosage_form, route, strength]
            search_text = " ".join([part for part in search_parts if part]).lower()

            return {
                "ndc": f"OB_{appl_no}_{product_no}",  # Orange Book app number + product number for uniqueness
                "name": trade_name or ingredient or "Unknown",
                "generic_name": ingredient,
                "brand_name": trade_name,
                "manufacturer": applicant,
                "ingredients": [ingredient] if ingredient else [],
                "dosage_form": dosage_form,
                "route": route,
                "product_number": product_no,
                "applicant": applicant,
                "approval_date": approval_date,
                "application_number": appl_no,  # FDA application number
                "orange_book_code": te_code,  # Therapeutic equivalence code
                "reference_listed_drug": rld,  # Reference listed drug flag
                "product_type": "HUMAN PRESCRIPTION DRUG",
                "marketing_status": "Prescription",
                "strength": strength,
                "therapeutic_class": "",  # Orange Book doesn't contain therapeutic class
                "search_text": search_text,
                "data_sources": ["orange_book"],
                # Keep FDA-specific fields for compatibility
                "proprietary_name": trade_name,
                "nonproprietary_name": ingredient,
                "dosage_form_name": dosage_form,
                "route_of_administration": route,
                "active_ingredients": ingredient,
                "labeler_name": applicant,
                "substance_name": ingredient,
                # Merge fields for grouping
                "_merge_generic_name": ingredient.lower().strip() if ingredient else "",
                "_merge_brand_name": trade_name.lower().strip() if trade_name else "",
                "_merge_manufacturer": applicant.lower().strip() if applicant else "",
                "_merge_applicant": applicant.lower().strip() if applicant else "",
                "_merge_app_number": appl_no or product_no,
            }

        except Exception as e:
            logger.warning(f"Failed to parse Orange Book record: {e}")
            return None
