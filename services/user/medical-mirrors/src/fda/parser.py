"""
FDA data parser
Parses FDA database files and extracts drug information
"""

import json
import csv
import logging
from typing import List, Dict, Optional
import pandas as pd

logger = logging.getLogger(__name__)


class FDAParser:
    """Parses FDA database files and extracts drug data"""
    
    def __init__(self):
        pass
    
    def parse_ndc_file(self, json_file_path: str) -> List[Dict]:
        """Parse FDA NDC Directory JSON file"""
        logger.info(f"Parsing FDA NDC file: {json_file_path}")
        drugs = []
        
        try:
            with open(json_file_path, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        drug = self.parse_ndc_record(data)
                        if drug:
                            drugs.append(drug)
                    except json.JSONDecodeError:
                        continue
            
            logger.info(f"Parsed {len(drugs)} drugs from NDC file")
            return drugs
            
        except Exception as e:
            logger.error(f"Failed to parse NDC file {json_file_path}: {e}")
            return []
    
    def parse_ndc_record(self, ndc_data: Dict) -> Optional[Dict]:
        """Parse a single NDC record"""
        try:
            # Extract NDC code
            ndc = ndc_data.get('product_ndc')
            if not ndc:
                return None
            
            # Extract drug information
            brand_name = ndc_data.get('brand_name', '')
            generic_name = ndc_data.get('generic_name', '')
            manufacturer = ndc_data.get('labeler_name', '')
            dosage_form = ndc_data.get('dosage_form', '')
            route = ndc_data.get('route', '')
            
            # Extract active ingredients
            ingredients = []
            active_ingredients = ndc_data.get('active_ingredients', [])
            for ingredient in active_ingredients:
                if isinstance(ingredient, dict):
                    name = ingredient.get('name')
                    if name:
                        ingredients.append(name)
            
            # Determine primary name
            name = brand_name or generic_name or 'Unknown'
            
            return {
                'ndc': ndc,
                'name': name,
                'generic_name': generic_name,
                'brand_name': brand_name,
                'manufacturer': manufacturer,
                'ingredients': ingredients,
                'dosage_form': dosage_form,
                'route': route,
                'approval_date': '',  # Not in NDC data
                'orange_book_code': '',  # Not in NDC data
                'therapeutic_class': ''  # Not in NDC data
            }
            
        except Exception as e:
            logger.error(f"Failed to parse NDC record: {e}")
            return None
    
    def parse_drugs_fda_file(self, json_file_path: str) -> List[Dict]:
        """Parse Drugs@FDA JSON file"""
        logger.info(f"Parsing Drugs@FDA file: {json_file_path}")
        drugs = []
        
        try:
            with open(json_file_path, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        drug = self.parse_drugs_fda_record(data)
                        if drug:
                            drugs.append(drug)
                    except json.JSONDecodeError:
                        continue
            
            logger.info(f"Parsed {len(drugs)} drugs from Drugs@FDA file")
            return drugs
            
        except Exception as e:
            logger.error(f"Failed to parse Drugs@FDA file {json_file_path}: {e}")
            return []
    
    def parse_drugs_fda_record(self, drugs_fda_data: Dict) -> Optional[Dict]:
        """Parse a single Drugs@FDA record"""
        try:
            # Extract application number (use as identifier)
            app_number = drugs_fda_data.get('application_number')
            if not app_number:
                return None
            
            # Extract drug information
            brand_name = drugs_fda_data.get('openfda', {}).get('brand_name', [''])[0] if drugs_fda_data.get('openfda', {}).get('brand_name') else ''
            generic_name = drugs_fda_data.get('openfda', {}).get('generic_name', [''])[0] if drugs_fda_data.get('openfda', {}).get('generic_name') else ''
            manufacturer = drugs_fda_data.get('sponsor_name', '')
            
            # Extract active ingredients
            ingredients = []
            if drugs_fda_data.get('openfda', {}).get('substance_name'):
                ingredients = drugs_fda_data['openfda']['substance_name']
            
            # Extract approval date
            approval_date = ''
            products = drugs_fda_data.get('products', [])
            if products and isinstance(products[0], dict):
                approval_date = products[0].get('approval_date', '')
            
            # Use application number as NDC (not ideal but needed for structure)
            ndc = app_number
            name = brand_name or generic_name or 'Unknown'
            
            return {
                'ndc': ndc,
                'name': name,
                'generic_name': generic_name,
                'brand_name': brand_name,
                'manufacturer': manufacturer,
                'ingredients': ingredients,
                'dosage_form': '',  # Not in this dataset
                'route': '',  # Not in this dataset
                'approval_date': approval_date,
                'orange_book_code': '',  # Not in this dataset
                'therapeutic_class': ''  # Not in this dataset
            }
            
        except Exception as e:
            logger.error(f"Failed to parse Drugs@FDA record: {e}")
            return None
    
    def parse_orange_book_file(self, file_path: str) -> List[Dict]:
        """Parse Orange Book file (typically CSV or text format)"""
        logger.info(f"Parsing Orange Book file: {file_path}")
        drugs = []
        
        try:
            # Try to detect file format
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file_path.endswith('.txt'):
                # Try tab-separated
                df = pd.read_csv(file_path, sep='\t')
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
            logger.error(f"Failed to parse Orange Book file {file_path}: {e}")
            return []
    
    def parse_orange_book_record(self, orange_book_data: Dict) -> Optional[Dict]:
        """Parse a single Orange Book record"""
        try:
            # Orange Book typically has fields like:
            # Ingredient, Trade_Name, Applicant, Strength, Dosage_Form, Route, TE_Code
            
            # Extract basic information
            ingredient = orange_book_data.get('Ingredient', orange_book_data.get('Active_Ingredient', ''))
            trade_name = orange_book_data.get('Trade_Name', orange_book_data.get('Brand_Name', ''))
            applicant = orange_book_data.get('Applicant', orange_book_data.get('Manufacturer', ''))
            dosage_form = orange_book_data.get('Dosage_Form', '')
            route = orange_book_data.get('Route', '')
            te_code = orange_book_data.get('TE_Code', orange_book_data.get('Therapeutic_Equivalence_Code', ''))
            
            # Create synthetic NDC (Orange Book doesn't have NDC)
            ndc = f"OB_{hash(str(orange_book_data)) % 1000000}"
            name = trade_name or ingredient or 'Unknown'
            
            return {
                'ndc': ndc,
                'name': name,
                'generic_name': ingredient,
                'brand_name': trade_name,
                'manufacturer': applicant,
                'ingredients': [ingredient] if ingredient else [],
                'dosage_form': dosage_form,
                'route': route,
                'approval_date': '',  # Not typically in Orange Book
                'orange_book_code': te_code,
                'therapeutic_class': ''
            }
            
        except Exception as e:
            logger.error(f"Failed to parse Orange Book record: {e}")
            return None
    
    def parse_drug_labels_file(self, json_file_path: str) -> List[Dict]:
        """Parse FDA drug labels JSON file"""
        logger.info(f"Parsing drug labels file: {json_file_path}")
        drugs = []
        
        try:
            with open(json_file_path, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        drug = self.parse_drug_label_record(data)
                        if drug:
                            drugs.append(drug)
                    except json.JSONDecodeError:
                        continue
            
            logger.info(f"Parsed {len(drugs)} drugs from labels file")
            return drugs
            
        except Exception as e:
            logger.error(f"Failed to parse drug labels file {json_file_path}: {e}")
            return []
    
    def parse_drug_label_record(self, label_data: Dict) -> Optional[Dict]:
        """Parse a single drug label record"""
        try:
            # Extract OpenFDA information
            openfda = label_data.get('openfda', {})
            
            # Extract NDC codes
            ndc_list = openfda.get('product_ndc', [])
            ndc = ndc_list[0] if ndc_list else f"LB_{hash(str(label_data)) % 1000000}"
            
            # Extract names
            brand_names = openfda.get('brand_name', [])
            generic_names = openfda.get('generic_name', [])
            manufacturers = openfda.get('manufacturer_name', [])
            
            brand_name = brand_names[0] if brand_names else ''
            generic_name = generic_names[0] if generic_names else ''
            manufacturer = manufacturers[0] if manufacturers else ''
            
            # Extract ingredients
            ingredients = openfda.get('substance_name', [])
            
            # Extract therapeutic class
            therapeutic_classes = openfda.get('pharm_class_epc', [])
            therapeutic_class = therapeutic_classes[0] if therapeutic_classes else ''
            
            name = brand_name or generic_name or 'Unknown'
            
            return {
                'ndc': ndc,
                'name': name,
                'generic_name': generic_name,
                'brand_name': brand_name,
                'manufacturer': manufacturer,
                'ingredients': ingredients,
                'dosage_form': '',  # Not in labels
                'route': '',  # Not in labels
                'approval_date': '',  # Not in labels
                'orange_book_code': '',  # Not in labels
                'therapeutic_class': therapeutic_class
            }
            
        except Exception as e:
            logger.error(f"Failed to parse drug label record: {e}")
            return None
