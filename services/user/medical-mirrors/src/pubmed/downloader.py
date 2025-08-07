"""
PubMed data downloader
Downloads XML dumps from NCBI FTP and processes them
"""

import os
import ftplib
import gzip
import logging
from typing import List, Optional
from datetime import datetime
import asyncio
import aiofiles
from config import Config

logger = logging.getLogger(__name__)


class PubMedDownloader:
    """Downloads PubMed XML data from NCBI FTP"""
    
    def __init__(self):
        self.config = Config()
        self.ftp_host = "ftp.ncbi.nlm.nih.gov"
        self.ftp_path = "/pubmed/baseline/"
        self.update_path = "/pubmed/updatefiles/"
        self.data_dir = self.config.get_pubmed_data_dir()
    
    async def download_baseline(self) -> List[str]:
        """Download PubMed baseline files"""
        logger.info("Starting PubMed baseline download")
        
        try:
            ftp = ftplib.FTP(self.ftp_host)
            ftp.login()
            ftp.cwd(self.ftp_path)
            
            # Get list of baseline files
            files = []
            ftp.retrlines('NLST', files.append)
            
            xml_files = [f for f in files if f.endswith('.xml.gz')]
            logger.info(f"Found {len(xml_files)} baseline files")
            
            downloaded_files = []
            for file in xml_files[:5]:  # Limit for initial implementation
                local_path = os.path.join(self.data_dir, file)
                if not os.path.exists(local_path):
                    logger.info(f"Downloading {file}")
                    with open(local_path, 'wb') as local_file:
                        ftp.retrbinary(f'RETR {file}', local_file.write)
                    downloaded_files.append(local_path)
                else:
                    logger.info(f"File {file} already exists, skipping")
                    downloaded_files.append(local_path)
            
            ftp.quit()
            logger.info(f"Downloaded {len(downloaded_files)} baseline files")
            return downloaded_files
            
        except Exception as e:
            logger.error(f"PubMed baseline download failed: {e}")
            raise
    
    async def download_updates(self) -> List[str]:
        """Download PubMed update files"""
        logger.info("Starting PubMed updates download")
        
        try:
            ftp = ftplib.FTP(self.ftp_host)
            ftp.login()
            ftp.cwd(self.update_path)
            
            # Get list of update files
            files = []
            ftp.retrlines('NLST', files.append)
            
            xml_files = [f for f in files if f.endswith('.xml.gz')]
            
            # Get recent updates (last 7 days worth)
            recent_files = xml_files[-50:]  # Approximate recent files
            logger.info(f"Found {len(recent_files)} recent update files")
            
            downloaded_files = []
            for file in recent_files:
                local_path = os.path.join(self.data_dir, f"updates_{file}")
                if not os.path.exists(local_path):
                    logger.info(f"Downloading update {file}")
                    with open(local_path, 'wb') as local_file:
                        ftp.retrbinary(f'RETR {file}', local_file.write)
                    downloaded_files.append(local_path)
                else:
                    downloaded_files.append(local_path)
            
            ftp.quit()
            logger.info(f"Downloaded {len(downloaded_files)} update files")
            return downloaded_files
            
        except Exception as e:
            logger.error(f"PubMed updates download failed: {e}")
            raise
    
    def extract_xml_file(self, gz_file_path: str) -> str:
        """Extract gzipped XML file"""
        extracted_path = gz_file_path.replace('.gz', '')
        
        if os.path.exists(extracted_path):
            return extracted_path
        
        try:
            with gzip.open(gz_file_path, 'rb') as gz_file:
                with open(extracted_path, 'wb') as xml_file:
                    xml_file.write(gz_file.read())
            
            logger.info(f"Extracted {gz_file_path} to {extracted_path}")
            return extracted_path
            
        except Exception as e:
            logger.error(f"Failed to extract {gz_file_path}: {e}")
            raise
    
    async def get_available_files(self) -> List[str]:
        """Get list of downloaded XML files ready for parsing"""
        xml_files = []
        
        for file in os.listdir(self.data_dir):
            if file.endswith('.xml.gz'):
                # Extract if needed
                gz_path = os.path.join(self.data_dir, file)
                xml_path = self.extract_xml_file(gz_path)
                xml_files.append(xml_path)
            elif file.endswith('.xml'):
                xml_files.append(os.path.join(self.data_dir, file))
        
        return xml_files
