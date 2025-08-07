"""
FDA data downloader
Downloads FDA Orange Book, NDC Directory, and Drug@FDA databases
"""

import os
import json
import logging
import zipfile
from typing import List, Dict, Optional
import httpx
import asyncio
from datetime import datetime
import pandas as pd
from config import Config

logger = logging.getLogger(__name__)


class FDADownloader:
    """Downloads FDA drug databases"""
    
    def __init__(self):
        self.config = Config()
        self.data_dir = self.config.get_fda_data_dir()
        self.session = httpx.AsyncClient(timeout=60.0)
    
    async def download_orange_book(self) -> str:
        """Download FDA Orange Book data"""
        logger.info("Downloading FDA Orange Book")
        
        try:
            # Orange Book URL (updated periodically)
            url = "https://www.accessdata.fda.gov/scripts/cder/ob/search_product.cfm"
            
            # Alternative: Download from FDA.gov direct links
            orange_book_url = "https://www.fda.gov/media/76860/download"
            
            response = await self.session.get(orange_book_url)
            response.raise_for_status()
            
            # Save ZIP file
            zip_file = os.path.join(self.data_dir, "orange_book.zip")
            with open(zip_file, 'wb') as f:
                f.write(response.content)
            
            # Extract ZIP
            extract_dir = os.path.join(self.data_dir, "orange_book")
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            logger.info("FDA Orange Book downloaded and extracted")
            return extract_dir
            
        except Exception as e:
            logger.error(f"Failed to download Orange Book: {e}")
            raise
    
    async def download_ndc_directory(self) -> str:
        """Download FDA NDC Directory"""
        logger.info("Downloading FDA NDC Directory")
        
        try:
            # NDC Directory from openFDA
            url = "https://download.open.fda.gov/drug/ndc/drug-ndc-0001-of-0001.json.zip"
            
            response = await self.session.get(url)
            response.raise_for_status()
            
            # Save ZIP file
            zip_file = os.path.join(self.data_dir, "ndc_directory.zip")
            with open(zip_file, 'wb') as f:
                f.write(response.content)
            
            # Extract ZIP
            extract_dir = os.path.join(self.data_dir, "ndc")
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            logger.info("FDA NDC Directory downloaded and extracted")
            return extract_dir
            
        except Exception as e:
            logger.error(f"Failed to download NDC Directory: {e}")
            raise
    
    async def download_drugs_at_fda(self) -> str:
        """Download Drugs@FDA database"""
        logger.info("Downloading Drugs@FDA database")
        
        try:
            # Drugs@FDA from openFDA
            url = "https://download.open.fda.gov/drug/drugsfda/drug-drugsfda-0001-of-0001.json.zip"
            
            response = await self.session.get(url)
            response.raise_for_status()
            
            # Save ZIP file
            zip_file = os.path.join(self.data_dir, "drugs_fda.zip")
            with open(zip_file, 'wb') as f:
                f.write(response.content)
            
            # Extract ZIP
            extract_dir = os.path.join(self.data_dir, "drugs_fda")
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            logger.info("Drugs@FDA database downloaded and extracted")
            return extract_dir
            
        except Exception as e:
            logger.error(f"Failed to download Drugs@FDA: {e}")
            raise
    
    async def download_drug_labels(self) -> str:
        """Download FDA drug labeling data"""
        logger.info("Downloading FDA drug labels")
        
        try:
            # Drug labeling from openFDA
            url = "https://download.open.fda.gov/drug/label/drug-label-0001-of-0001.json.zip"
            
            response = await self.session.get(url)
            response.raise_for_status()
            
            # Save ZIP file
            zip_file = os.path.join(self.data_dir, "drug_labels.zip")
            with open(zip_file, 'wb') as f:
                f.write(response.content)
            
            # Extract ZIP
            extract_dir = os.path.join(self.data_dir, "labels")
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            logger.info("FDA drug labels downloaded and extracted")
            return extract_dir
            
        except Exception as e:
            logger.error(f"Failed to download drug labels: {e}")
            raise
    
    async def download_all_fda_data(self) -> Dict[str, str]:
        """Download all FDA datasets"""
        logger.info("Starting full FDA data download")
        
        try:
            # Download all datasets
            orange_book_dir = await self.download_orange_book()
            ndc_dir = await self.download_ndc_directory()
            drugs_fda_dir = await self.download_drugs_at_fda()
            labels_dir = await self.download_drug_labels()
            
            return {
                'orange_book': orange_book_dir,
                'ndc': ndc_dir,
                'drugs_fda': drugs_fda_dir,
                'labels': labels_dir
            }
            
        except Exception as e:
            logger.error(f"FDA data download failed: {e}")
            raise
    
    async def get_available_files(self) -> Dict[str, List[str]]:
        """Get list of downloaded files ready for parsing"""
        files = {
            'orange_book': [],
            'ndc': [],
            'drugs_fda': [],
            'labels': []
        }
        
        for dataset in files.keys():
            dataset_dir = os.path.join(self.data_dir, dataset)
            if os.path.exists(dataset_dir):
                for file in os.listdir(dataset_dir):
                    if file.endswith(('.json', '.txt', '.csv')):
                        files[dataset].append(os.path.join(dataset_dir, file))
        
        return files
    
    async def close(self):
        """Close HTTP session"""
        await self.session.aclose()
