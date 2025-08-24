"""
FDA data parser
Parses FDA database files and extracts drug information
"""

import json
import logging

import pandas as pd
from validation_utils import validate_record

logger = logging.getLogger(__name__)


class FDAParser:
    """Parses FDA database files and extracts drug data"""

    def __init__(self) -> None:
        pass

    def parse_ndc_file(self, json_file_path: str) -> list[dict]:
        """Parse FDA NDC Directory JSON file"""
        logger.info(f"Parsing FDA NDC file: {json_file_path}")
        drugs = []

        try:
            with open(json_file_path) as f:
                # Parse the entire JSON file as a single object
                data = json.load(f)

                # Extract the results array
                if isinstance(data, dict) and "results" in data:
                    results = data["results"]
                    logger.info(f"Found {len(results)} NDC records")

                    for record in results:
                        drug = self.parse_ndc_record(record)
                        if drug:
                            drugs.append(drug)
                else:
                    logger.warning("No 'results' field found in NDC file")

            logger.info(f"Parsed {len(drugs)} drugs from NDC file")
            return drugs

        except Exception as e:
            logger.exception(f"Failed to parse NDC file {json_file_path}: {e}")
            return []

    def parse_ndc_record(self, ndc_data: dict) -> dict | None:
        """Parse a single NDC record with unified schema"""
        try:
            # Extract NDC code
            ndc = ndc_data.get("product_ndc")
            if not ndc:
                return None

            # Extract drug information
            brand_name = ndc_data.get("brand_name", "")
            generic_name = ndc_data.get("generic_name", "")
            manufacturer = ndc_data.get("labeler_name", "")
            dosage_form = ndc_data.get("dosage_form", "")
            route = ndc_data.get("route", "")

            # Extract active ingredients with strength
            ingredients = []
            active_ingredients = ndc_data.get("active_ingredients", [])
            strength_parts = []

            for ingredient in active_ingredients:
                if isinstance(ingredient, dict):
                    name = ingredient.get("name")
                    strength = ingredient.get("strength")
                    if name:
                        ingredients.append(name)
                        if strength:
                            strength_parts.append(f"{name} {strength}")

            # Determine primary name
            name = brand_name or generic_name or "Unknown"

            # Create strength string
            strength = "; ".join(strength_parts) if strength_parts else ""

            return {
                "ndc": ndc,
                "name": name,
                "generic_name": generic_name,
                "brand_name": brand_name,
                "manufacturer": manufacturer,
                "applicant": "",  # Not in NDC data
                "ingredients": ingredients,
                "strength": strength,
                "dosage_form": dosage_form,
                "route": route,
                "application_number": "",  # Not in NDC data
                "product_number": "",  # Not in NDC data
                "approval_date": "",  # Not in NDC data
                "orange_book_code": "",  # Not in NDC data
                "reference_listed_drug": "",  # Not in NDC data
                "therapeutic_class": "",  # Not in NDC data
                "pharmacologic_class": "",  # Not in NDC data
                "data_sources": ["ndc"],
                # Merge keys for data integration
                "_merge_generic_name": generic_name.lower().strip() if generic_name else "",
                "_merge_brand_name": brand_name.lower().strip() if brand_name else "",
                "_merge_manufacturer": manufacturer.lower().strip() if manufacturer else "",
            }

        except Exception as e:
            logger.exception(f"Failed to parse NDC record: {e}")
            return None

    def parse_drugs_fda_file(self, json_file_path: str) -> list[dict]:
        """Parse Drugs@FDA JSON file"""
        logger.info(f"Parsing Drugs@FDA file: {json_file_path}")
        drugs = []

        try:
            with open(json_file_path) as f:
                # Parse the entire JSON file as a single object
                data = json.load(f)

                # Extract the results array
                if isinstance(data, dict) and "results" in data:
                    results = data["results"]
                    logger.info(f"Found {len(results)} Drugs@FDA records")

                    for record in results:
                        drug = self.parse_drugs_fda_record(record)
                        if drug:
                            drugs.append(drug)
                else:
                    logger.warning("No 'results' field found in Drugs@FDA file")

            logger.info(f"Parsed {len(drugs)} drugs from Drugs@FDA file")
            return drugs

        except Exception as e:
            logger.exception(f"Failed to parse Drugs@FDA file {json_file_path}: {e}")
            return []

    def parse_drugs_fda_record(self, drugs_fda_data: dict) -> dict | None:
        """Parse a single Drugs@FDA record with unified schema"""
        try:
            # Extract application number (use as identifier)
            app_number = drugs_fda_data.get("application_number")
            if not app_number:
                return None

            # Extract drug information
            openfda = drugs_fda_data.get("openfda", {})
            brand_name = openfda.get("brand_name", [""])[0] if openfda.get("brand_name") else ""
            generic_name = openfda.get("generic_name", [""])[0] if openfda.get("generic_name") else ""

            # Get sponsor/applicant information
            sponsor = drugs_fda_data.get("sponsor_name", "")

            # Extract manufacturer from openfda if available, otherwise use sponsor
            manufacturer = (
                openfda.get("manufacturer_name", [""])[0] if openfda.get("manufacturer_name")
                else sponsor
            )

            # Extract active ingredients
            ingredients = openfda.get("substance_name", []) if openfda.get("substance_name") else []

            # Extract therapeutic and pharmacologic class
            therapeutic_class = ""
            pharmacologic_class = ""

            if openfda.get("pharm_class_epc"):
                pharmacologic_class = "; ".join(openfda["pharm_class_epc"])
            elif openfda.get("pharm_class_moa"):
                pharmacologic_class = "; ".join(openfda["pharm_class_moa"])

            # Extract route and dosage form
            route = "; ".join(openfda.get("route", [])) if openfda.get("route") else ""
            dosage_form = "; ".join(openfda.get("dosage_form", [])) if openfda.get("dosage_form") else ""

            # Extract approval date
            approval_date = ""
            products = drugs_fda_data.get("products", [])
            if products and isinstance(products[0], dict):
                approval_date = products[0].get("approval_date", "")

            # Create synthetic NDC using application number
            ndc = f"FDA_{app_number}"
            name = brand_name or generic_name or f"Application {app_number}"

            return {
                "ndc": ndc,
                "name": name,
                "generic_name": generic_name,
                "brand_name": brand_name,
                "manufacturer": manufacturer,
                "applicant": sponsor,
                "ingredients": ingredients,
                "strength": "",  # Not available in Drugs@FDA data
                "dosage_form": dosage_form,
                "route": route,
                "application_number": app_number,
                "product_number": "",  # Not available in this format
                "approval_date": approval_date,
                "orange_book_code": "",  # Not in Drugs@FDA data
                "reference_listed_drug": "",  # Not in Drugs@FDA data
                "therapeutic_class": therapeutic_class,
                "pharmacologic_class": pharmacologic_class,
                "data_sources": ["drugs_fda"],
                # Merge keys for data integration
                "_merge_generic_name": generic_name.lower().strip() if generic_name else "",
                "_merge_brand_name": brand_name.lower().strip() if brand_name else "",
                "_merge_manufacturer": manufacturer.lower().strip() if manufacturer else "",
                "_merge_applicant": sponsor.lower().strip() if sponsor else "",
                "_merge_app_number": app_number,
            }

        except Exception as e:
            logger.exception(f"Failed to parse Drugs@FDA record: {e}")
            return None

    def parse_orange_book_file(self, file_path: str) -> list[dict]:
        """Parse Orange Book file (typically CSV or text format)"""
        logger.info(f"Parsing Orange Book file: {file_path}")
        drugs = []

        try:
            # Try to detect file format
            if file_path.endswith(".csv"):
                df = pd.read_csv(file_path)
            elif file_path.endswith(".txt"):
                # Orange Book uses tilde (~) as delimiter
                df = pd.read_csv(file_path, sep="~")
            else:
                logger.warning(f"Unknown file format for {file_path}")
                return []

            for _, row in df.iterrows():
                drug = self.parse_orange_book_record(row.to_dict())
                if drug:
                    drugs.append(drug)

            logger.info(f"Parsed {len(drugs)} drugs from Orange Book file")
            return drugs

        except Exception as e:
            logger.exception(f"Failed to parse Orange Book file {file_path}: {e}")
            return []

    def parse_orange_book_record(self, orange_book_data: dict) -> dict | None:
        """Parse a single Orange Book record"""
        try:
            # Orange Book has fields like:
            # Ingredient, DF;Route, Trade_Name, Applicant, Strength, Appl_Type, Appl_No, Product_No, TE_Code, Approval_Date, RLD, RS, Type, Applicant_Full_Name

            # Extract basic information using actual Orange Book column names
            ingredient = orange_book_data.get("Ingredient", "")
            trade_name = orange_book_data.get("Trade_Name", "")
            applicant = orange_book_data.get("Applicant", "")
            applicant_full_name = orange_book_data.get("Applicant_Full_Name", "")
            dosage_form_route = orange_book_data.get("DF;Route", "")
            strength = orange_book_data.get("Strength", "")
            te_code = orange_book_data.get("TE_Code", "")
            approval_date = orange_book_data.get("Approval_Date", "")
            appl_no = orange_book_data.get("Appl_No", "")

            # Split dosage form and route
            if ";" in dosage_form_route:
                dosage_form, route = dosage_form_route.split(";", 1)
            else:
                dosage_form = dosage_form_route
                route = ""

            # Create synthetic NDC using application number (Orange Book doesn't have NDC)
            ndc = f"OB_{appl_no}_{orange_book_data.get('Product_No', '001')}"
            name = trade_name or ingredient or "Unknown"

            # Use full applicant name if available, otherwise short name
            manufacturer = applicant_full_name or applicant

            # Create raw record
            raw_record = {
                "ndc": ndc,
                "name": name,
                "generic_name": ingredient,
                "brand_name": trade_name,
                "manufacturer": manufacturer,
                "applicant": applicant_full_name or applicant,
                "ingredients": [ingredient] if ingredient else [],
                "strength": strength,
                "dosage_form": dosage_form.strip(),
                "route": route.strip(),
                "application_number": appl_no,
                "product_number": orange_book_data.get("Product_No", ""),
                "approval_date": approval_date,
                "orange_book_code": te_code,
                "reference_listed_drug": orange_book_data.get("RLD", ""),
                "therapeutic_class": "",  # Not in Orange Book data
                "pharmacologic_class": "",  # Not in Orange Book data
                "data_sources": ["orange_book"],
                # Merge keys for data integration
                "_merge_generic_name": ingredient.lower().strip() if ingredient else "",
                "_merge_brand_name": trade_name.lower().strip() if trade_name else "",
                "_merge_manufacturer": manufacturer.lower().strip() if manufacturer else "",
                "_merge_applicant": (applicant_full_name or applicant).lower().strip() if (applicant_full_name or applicant) else "",
                "_merge_app_number": appl_no,
            }

            # Validate record before returning
            try:
                return validate_record(
                    raw_record,
                    "fda_drugs",
                    required_fields=["ndc", "name"],  # NDC and name are required
                )
            except Exception as e:
                logger.warning(f"Validation failed for Orange Book drug {ndc}: {e}")
                return None

        except Exception as e:
            logger.exception(f"Failed to parse Orange Book record: {e}")
            return None

    def parse_drug_labels_file(self, json_file_path: str) -> list[dict]:
        """Parse FDA drug labels JSON file"""
        logger.info(f"Parsing drug labels file: {json_file_path}")
        drugs = []

        try:
            with open(json_file_path) as f:
                # Parse the entire JSON file as a single object
                data = json.load(f)

                # Extract the results array
                if isinstance(data, dict) and "results" in data:
                    results = data["results"]
                    logger.info(f"Found {len(results)} drug label records")

                    for record in results:
                        drug = self.parse_drug_label_record(record)
                        if drug:
                            drugs.append(drug)
                else:
                    # Fallback: try line-by-line parsing for JSONL format
                    logger.warning("No 'results' field found, trying line-by-line parsing")
                    f.seek(0)
                    for line in f:
                        try:
                            line_data = json.loads(line)
                            drug = self.parse_drug_label_record(line_data)
                            if drug:
                                drugs.append(drug)
                        except json.JSONDecodeError:
                            continue

            logger.info(f"Parsed {len(drugs)} drugs from labels file")
            return drugs

        except Exception as e:
            logger.exception(f"Failed to parse drug labels file {json_file_path}: {e}")
            return []

    def parse_drug_label_record(self, label_data: dict) -> dict | None:
        """Parse a single drug label record"""
        try:
            # Extract OpenFDA information
            openfda = label_data.get("openfda", {})

            # Extract NDC codes
            ndc_list = openfda.get("product_ndc", [])
            ndc = ndc_list[0] if ndc_list else f"LB_{hash(str(label_data)) % 1000000}"

            # Extract names
            brand_names = openfda.get("brand_name", [])
            generic_names = openfda.get("generic_name", [])
            manufacturers = openfda.get("manufacturer_name", [])

            brand_name = brand_names[0] if brand_names else ""
            generic_name = generic_names[0] if generic_names else ""
            manufacturer = manufacturers[0] if manufacturers else ""

            # Extract ingredients
            ingredients = openfda.get("substance_name", [])

            # Extract therapeutic class
            therapeutic_classes = openfda.get("pharm_class_epc", [])
            therapeutic_class = therapeutic_classes[0] if therapeutic_classes else ""

            name = brand_name or generic_name or "Unknown"

            return {
                "ndc": ndc,
                "name": name,
                "generic_name": generic_name,
                "brand_name": brand_name,
                "manufacturer": manufacturer,
                "ingredients": ingredients,
                "dosage_form": "",  # Not in labels
                "route": "",  # Not in labels
                "approval_date": "",  # Not in labels
                "orange_book_code": "",  # Not in labels
                "therapeutic_class": therapeutic_class,
            }

        except Exception as e:
            logger.exception(f"Failed to parse drug label record: {e}")
            return None

    def merge_drug_records(self, records: list[dict]) -> dict:
        """
        Merge multiple drug records from different sources into a unified record
        Priority order: NDC Directory > Orange Book > Drugs@FDA > Labels
        """
        if not records:
            return {}

        # Sort by data source priority
        source_priority = {"ndc": 1, "orange_book": 2, "drugs_fda": 3, "labels": 4}
        records = sorted(records, key=lambda r: min(source_priority.get(src, 5) for src in r.get("data_sources", [])) if r.get("data_sources") else 5)

        # Start with the highest priority record
        merged = records[0].copy()

        # Remove merge keys from final result
        merge_keys = [k for k in merged if k.startswith("_merge_")]
        for key in merge_keys:
            merged.pop(key, None)

        # Combine data_sources from all records
        all_sources = set()
        for record in records:
            all_sources.update(record.get("data_sources", []))
        merged["data_sources"] = list(all_sources)

        # Merge fields from other records, preferring non-empty values
        for record in records[1:]:
            for key, value in record.items():
                if key.startswith("_merge_") or key == "data_sources":
                    continue

                # Skip if current value is already good
                current_value = merged.get(key, "")
                if current_value and current_value not in ["", "Unknown", []]:
                    continue

                # Use new value if it's better
                if value and value not in ["", "Unknown", []]:
                    if key == "ingredients":
                        # Merge ingredient lists
                        current_ingredients = set(merged.get("ingredients", []))
                        new_ingredients = set(value) if isinstance(value, list) else {value}
                        merged["ingredients"] = list(current_ingredients.union(new_ingredients))
                    elif key in ["strength", "therapeutic_class", "pharmacologic_class"]:
                        # Combine text fields with semicolon separator
                        if current_value and current_value != value:
                            merged[key] = f"{current_value}; {value}"
                        else:
                            merged[key] = value
                    else:
                        # Replace with better value
                        merged[key] = value

        # Prefer real NDC over synthetic ones
        real_ndc = None
        for record in records:
            ndc = record.get("ndc", "")
            if ndc and not ndc.startswith(("OB_", "FDA_")):
                real_ndc = ndc
                break

        if real_ndc:
            merged["ndc"] = real_ndc

        # Update name if we have better info
        generic = merged.get("generic_name", "")
        brand = merged.get("brand_name", "")
        current_name = merged.get("name", "")

        if brand and brand != current_name:
            merged["name"] = brand
        elif generic and generic != current_name and current_name in ["Unknown", ""]:
            merged["name"] = generic

        return merged

    def find_matching_records(self, drug_records: list[dict]) -> dict[str, list[dict]]:
        """
        Group drug records that represent the same drug from different sources
        Returns dict mapping representative keys to lists of matching records
        """
        groups = {}

        for record in drug_records:
            # Generate matching keys
            merge_keys = []

            # Primary key: generic + brand name combination
            generic = record.get("_merge_generic_name", "")
            brand = record.get("_merge_brand_name", "")
            if generic and brand:
                merge_keys.append(f"generic_brand:{generic}#{brand}")
            elif generic:
                merge_keys.append(f"generic:{generic}")
            elif brand:
                merge_keys.append(f"brand:{brand}")

            # Secondary key: application number
            app_num = record.get("_merge_app_number", "")
            if app_num:
                merge_keys.append(f"app:{app_num}")

            # Tertiary key: manufacturer + generic name
            manufacturer = record.get("_merge_manufacturer", "")
            applicant = record.get("_merge_applicant", "")
            if (manufacturer or applicant) and generic:
                company = manufacturer or applicant
                merge_keys.append(f"company_generic:{company}#{generic}")

            # Add record to all matching groups
            if merge_keys:
                for key in merge_keys:
                    if key not in groups:
                        groups[key] = []
                    groups[key].append(record)
            else:
                # Handle records without merge keys - use NDC or fallback identifier
                ndc = record.get("ndc", "")
                if ndc:
                    fallback_key = f"ndc_only:{ndc}"
                else:
                    # Generate a unique key for orphaned records
                    fallback_key = f"orphan:{hash(str(record))}"

                if fallback_key not in groups:
                    groups[fallback_key] = []
                groups[fallback_key].append(record)

        # Since we now use unique keys, no Union-Find merging is needed
        total_records = sum(len(records) for records in groups.values())
        logger.info(f"Created {len(groups)} unique drug groups from {total_records} records")

        # Return the groups directly without Union-Find merging
        return groups
