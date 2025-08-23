"""
Optimized multi-core FDA parser
Utilizes all available CPU cores for JSON parsing and database operations
"""

import asyncio
import json
import logging
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from typing import Any, Dict, List
from pathlib import Path

from validation_utils import validate_record, DataValidator

logger = logging.getLogger(__name__)


def parse_json_file_worker(json_file_path: str, dataset_type: str) -> tuple[str, List[Dict[str, Any]]]:
    """Worker function for multiprocessing JSON parsing"""
    try:
        logger.info(f"Worker parsing {dataset_type}: {json_file_path}")
        records = []
        
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if dataset_type == "ndc":
            records = parse_ndc_data_worker(data)
        elif dataset_type == "drugs_fda":
            records = parse_drugs_fda_data_worker(data)
        elif dataset_type == "drug_labels" or dataset_type == "labels":
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


def parse_ndc_data_worker(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse NDC data structure"""
    records = []
    
    if isinstance(data, dict) and "results" in data:
        results = data["results"]
        for record in results:
            parsed_record = parse_ndc_record_worker(record)
            if parsed_record:
                records.append(parsed_record)
    
    return records


def parse_ndc_record_worker(ndc_data: Dict[str, Any]) -> Dict[str, Any] | None:
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
        if isinstance(route, list):
            route = ", ".join([str(r) for r in route])
        else:
            route = str(route)
            
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
        
        # Create search text for full-text search
        search_parts = [
            product_ndc, generic_name, brand_name, labeler_name, 
            active_ingredients_str, dosage_form, route
        ]
        search_text = " ".join([part for part in search_parts if part]).lower()
        
        return {
            "ndc_product_code": product_ndc,
            "product_type": product_type,
            "proprietary_name": brand_name,
            "nonproprietary_name": generic_name,
            "dosage_form_name": dosage_form,
            "route_of_administration": route,
            "marketing_status": marketing_status,
            "active_ingredients": active_ingredients_str,
            "labeler_name": labeler_name,
            "substance_name": generic_name,  # Use generic name as substance
            "strength": active_ingredients_str,  # Strength included in active ingredients
            "search_text": search_text,
            "source": "ndc_directory"
        }
        
    except Exception as e:
        logger.warning(f"Failed to parse NDC record: {e}")
        return None


def parse_drugs_fda_data_worker(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse Drugs@FDA data structure"""
    records = []
    
    if isinstance(data, dict) and "results" in data:
        results = data["results"]
        for record in results:
            parsed_record = parse_drugs_fda_record_worker(record)
            if parsed_record:
                records.append(parsed_record)
    
    return records


def parse_drugs_fda_record_worker(drug_data: Dict[str, Any]) -> Dict[str, Any] | None:
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
        
        # Create search text
        search_parts = [
            application_number, sponsor_name, brand_name, generic_name,
            dosage_form, route, marketing_status
        ]
        search_text = " ".join([part for part in search_parts if part]).lower()
        
        return {
            "ndc_product_code": application_number,  # Using application number as identifier
            "product_type": application_type,
            "proprietary_name": brand_name,
            "nonproprietary_name": generic_name,
            "dosage_form_name": dosage_form,
            "route_of_administration": route,
            "marketing_status": marketing_status,
            "active_ingredients": generic_name,
            "labeler_name": sponsor_name,
            "substance_name": generic_name,
            "strength": "",  # Not readily available in this dataset
            "search_text": search_text,
            "source": "drugs_fda"
        }
        
    except Exception as e:
        logger.warning(f"Failed to parse Drugs@FDA record: {e}")
        return None


def parse_drug_labels_data_worker(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse drug labels data structure"""
    records = []
    
    if isinstance(data, dict) and "results" in data:
        results = data["results"]
        for record in results:
            parsed_record = parse_drug_label_record_worker(record)
            if parsed_record:
                records.append(parsed_record)
    
    return records


def parse_drug_label_record_worker(label_data: Dict[str, Any]) -> Dict[str, Any] | None:
    """Parse a single drug label record"""
    try:
        # Extract NDC codes
        product_ndc = label_data.get("product_ndc", [])
        if isinstance(product_ndc, list) and product_ndc:
            ndc_code = str(product_ndc[0]).strip()
        elif isinstance(product_ndc, str):
            ndc_code = product_ndc.strip()
        else:
            ndc_code = ""
            
        if not ndc_code:
            return None
            
        # Get brand and generic names
        brand_name_list = label_data.get("brand_name", [])
        if isinstance(brand_name_list, list) and brand_name_list:
            brand_name = str(brand_name_list[0]).strip()
        elif isinstance(brand_name_list, str):
            brand_name = brand_name_list.strip()
        else:
            brand_name = ""
            
        generic_name_list = label_data.get("generic_name", [])
        if isinstance(generic_name_list, list) and generic_name_list:
            generic_name = str(generic_name_list[0]).strip()
        elif isinstance(generic_name_list, str):
            generic_name = generic_name_list.strip()
        else:
            generic_name = ""
            
        # Get manufacturer
        manufacturer_list = label_data.get("manufacturer_name", [])
        if isinstance(manufacturer_list, list) and manufacturer_list:
            manufacturer = str(manufacturer_list[0]).strip()
        elif isinstance(manufacturer_list, str):
            manufacturer = manufacturer_list.strip()
        else:
            manufacturer = ""
            
        # Get dosage form and route
        dosage_form_list = label_data.get("dosage_form", [])
        if isinstance(dosage_form_list, list) and dosage_form_list:
            dosage_form = str(dosage_form_list[0]).strip()
        elif isinstance(dosage_form_list, str):
            dosage_form = dosage_form_list.strip()
        else:
            dosage_form = ""
            
        route_list = label_data.get("route", [])
        if isinstance(route_list, list):
            route = ", ".join([str(r) for r in route_list])
        elif isinstance(route_list, str):
            route = route_list
        else:
            route = ""
            
        # Get active ingredients
        active_ingredients_list = label_data.get("active_ingredient", [])
        if isinstance(active_ingredients_list, list):
            active_ingredients = "; ".join([str(ai) for ai in active_ingredients_list])
        elif isinstance(active_ingredients_list, str):
            active_ingredients = active_ingredients_list
        else:
            active_ingredients = ""
            
        # Create search text
        search_parts = [
            ndc_code, brand_name, generic_name, manufacturer,
            dosage_form, route, active_ingredients
        ]
        search_text = " ".join([part for part in search_parts if part]).lower()
        
        return {
            "ndc_product_code": ndc_code,
            "product_type": "HUMAN PRESCRIPTION DRUG",  # Most drug labels are prescription
            "proprietary_name": brand_name,
            "nonproprietary_name": generic_name,
            "dosage_form_name": dosage_form,
            "route_of_administration": route,
            "marketing_status": "Prescription",
            "active_ingredients": active_ingredients,
            "labeler_name": manufacturer,
            "substance_name": generic_name,
            "strength": active_ingredients,  # Strength info is in active ingredients
            "search_text": search_text,
            "source": "drug_labels"
        }
        
    except Exception as e:
        logger.warning(f"Failed to parse drug label record: {e}")
        return None


class OptimizedFDAParser:
    """Multi-core FDA data parser with parallel processing"""
    
    def __init__(self, max_workers: int | None = None):
        """Initialize with specified number of workers"""
        if max_workers is None:
            max_workers = max(1, mp.cpu_count() // 2)
        self.max_workers = max_workers
        
        logger.info(
            f"Initialized FDA parser with {self.max_workers} workers (CPU cores: {mp.cpu_count()})"
        )
    
    async def parse_json_files_parallel(
        self, json_files: List[str], dataset_type: str
    ) -> List[Dict[str, Any]]:
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
            f"Parallel parsing completed: {total_records} total records from {len(parsed_files)} files"
        )
        
        return all_records

    def parse_orange_book_file(self, csv_file_path: str) -> List[Dict[str, Any]]:
        """Parse Orange Book CSV file (single-threaded as it's usually one file)"""
        logger.info(f"Parsing Orange Book CSV file: {csv_file_path}")
        drugs = []
        
        try:
            import pandas as pd
            
            # Read the Orange Book products file (uses ~ as delimiter)
            df = pd.read_csv(csv_file_path, sep='~', encoding='utf-8', low_memory=False, on_bad_lines='skip')
            
            for _, row in df.iterrows():
                drug = self._parse_orange_book_record(row)
                if drug:
                    drugs.append(drug)
                    
            logger.info(f"Parsed {len(drugs)} drugs from Orange Book")
            return drugs
            
        except Exception as e:
            logger.exception(f"Failed to parse Orange Book file {csv_file_path}: {e}")
            return []
    
    def _parse_orange_book_record(self, row) -> Dict[str, Any] | None:
        """Parse a single Orange Book record"""
        try:
            # Extract fields (Orange Book has specific column names)
            ingredient = str(row.get("Ingredient", "")).strip()
            trade_name = str(row.get("Trade_Name", "")).strip()
            applicant = str(row.get("Applicant_Full_Name", row.get("Applicant", ""))).strip()
            product_no = str(row.get("Product_No", "")).strip()
            # DF;Route format like "AEROSOL, FOAM;RECTAL"
            df_route = str(row.get("DF;Route", "")).strip()
            dosage_form = df_route.split(';')[0] if ';' in df_route else df_route
            route = df_route.split(';')[1] if ';' in df_route else ""
            strength = str(row.get("Strength", "")).strip()
            approval_date = str(row.get("Approval_Date", "")).strip()
            
            if not ingredient:
                return None
                
            # Create search text
            search_parts = [ingredient, trade_name, applicant, dosage_form, route, strength]
            search_text = " ".join([part for part in search_parts if part]).lower()
            
            return {
                "ndc_product_code": product_no,
                "product_type": "HUMAN PRESCRIPTION DRUG",
                "proprietary_name": trade_name,
                "nonproprietary_name": ingredient,
                "dosage_form_name": dosage_form,
                "route_of_administration": route,
                "marketing_status": "Prescription",
                "active_ingredients": ingredient,
                "labeler_name": applicant,
                "substance_name": ingredient,
                "strength": strength,
                "search_text": search_text,
                "source": "orange_book"
            }
            
        except Exception as e:
            logger.warning(f"Failed to parse Orange Book record: {e}")
            return None