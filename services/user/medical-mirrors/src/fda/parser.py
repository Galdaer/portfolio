"""
FDA data parser
Parses FDA database files and extracts drug information
"""

import json
import logging

import pandas as pd

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
        """Parse a single NDC record"""
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

            # Extract active ingredients
            ingredients = []
            active_ingredients = ndc_data.get("active_ingredients", [])
            for ingredient in active_ingredients:
                if isinstance(ingredient, dict):
                    name = ingredient.get("name")
                    if name:
                        ingredients.append(name)

            # Determine primary name
            name = brand_name or generic_name or "Unknown"

            return {
                "ndc": ndc,
                "name": name,
                "generic_name": generic_name,
                "brand_name": brand_name,
                "manufacturer": manufacturer,
                "ingredients": ingredients,
                "dosage_form": dosage_form,
                "route": route,
                "approval_date": "",  # Not in NDC data
                "orange_book_code": "",  # Not in NDC data
                "therapeutic_class": "",  # Not in NDC data
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
        """Parse a single Drugs@FDA record"""
        try:
            # Extract application number (use as identifier)
            app_number = drugs_fda_data.get("application_number")
            if not app_number:
                return None

            # Extract drug information
            brand_name = (
                drugs_fda_data.get("openfda", {}).get("brand_name", [""])[0]
                if drugs_fda_data.get("openfda", {}).get("brand_name")
                else ""
            )
            generic_name = (
                drugs_fda_data.get("openfda", {}).get("generic_name", [""])[0]
                if drugs_fda_data.get("openfda", {}).get("generic_name")
                else ""
            )
            manufacturer = drugs_fda_data.get("sponsor_name", "")

            # Extract active ingredients
            ingredients = []
            if drugs_fda_data.get("openfda", {}).get("substance_name"):
                ingredients = drugs_fda_data["openfda"]["substance_name"]

            # Extract approval date
            approval_date = ""
            products = drugs_fda_data.get("products", [])
            if products and isinstance(products[0], dict):
                approval_date = products[0].get("approval_date", "")

            # Use application number as NDC (not ideal but needed for structure)
            ndc = app_number
            name = brand_name or generic_name or "Unknown"

            return {
                "ndc": ndc,
                "name": name,
                "generic_name": generic_name,
                "brand_name": brand_name,
                "manufacturer": manufacturer,
                "ingredients": ingredients,
                "dosage_form": "",  # Not in this dataset
                "route": "",  # Not in this dataset
                "approval_date": approval_date,
                "orange_book_code": "",  # Not in this dataset
                "therapeutic_class": "",  # Not in this dataset
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

            return {
                "ndc": ndc,
                "name": name,
                "generic_name": ingredient,
                "brand_name": trade_name,
                "manufacturer": manufacturer,
                "ingredients": [ingredient] if ingredient else [],
                "dosage_form": dosage_form.strip(),
                "route": route.strip(),
                "approval_date": approval_date,
                "orange_book_code": te_code,
                "therapeutic_class": "",  # Not in Orange Book data
                "strength": strength,  # Include strength information
            }

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
