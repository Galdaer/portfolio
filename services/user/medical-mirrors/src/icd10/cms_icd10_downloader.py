"""
CMS ICD-10-CM Direct Downloader with ZIP/XML parsing and smart retry logic
"""

import asyncio
import logging
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import aiohttp
import zipfile
import io
import csv
from dataclasses import dataclass

from .download_state_manager import ICD10DownloadStateManager, DownloadStatus

logger = logging.getLogger(__name__)


@dataclass 
class RateLimitInfo:
    """Rate limiting information"""
    is_limited: bool = False
    reset_time: Optional[datetime] = None
    retry_after: Optional[int] = None
    remaining_requests: Optional[int] = None
    limit: Optional[int] = None


class CMSICD10Downloader:
    """Downloads ICD-10-CM codes directly from CMS and WHO sources"""
    
    # Official ICD-10-CM data sources (CDC and CMS)
    CMS_URLS = {
        # CDC Official Sources (Primary - Complete detailed codes)
        "cdc_icd10_cm_2025": "https://ftp.cdc.gov/pub/health_statistics/nchs/Publications/ICD10CM/2025/ICD10-CM%20Code%20Descriptions%202025.zip",
        "cdc_icd10_cm_2025_april": "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Publications/ICD10CM/2025-Update/Code-desciptions-April-2025.zip",
        "cdc_icd10_cm_2024": "https://ftp.cdc.gov/pub/health_statistics/nchs/publications/ICD10CM/2024/icd10cm-CodesDescriptions-2024.zip",
        "cdc_icd10_cm_tabular_2025": "https://ftp.cdc.gov/pub/health_statistics/nchs/Publications/ICD10CM/2025/icd10cm-table-index-2025.zip",
        "cdc_icd10_cm_tabular_2025_april": "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Publications/ICD10CM/2025-Update/icd10cm-table-index-April-2025.zip",
        "cdc_icd10_cm_tabular_2024": "https://ftp.cdc.gov/pub/health_statistics/nchs/publications/ICD10CM/2024/icd10cm-Table%20and%20Index-2024.zip",
        
        # CMS Secondary Sources (Category codes only) 
        "cms_icd10_cm_2024": "https://www.cms.gov/files/zip/2024-code-descriptions-tabular-order-updated-02/01/2024.zip",
        "cms_icd10_cm_2025": "https://www.cms.gov/files/zip/2025-code-descriptions-tabular-order.zip",
        "cms_icd10_cm_2026": "https://www.cms.gov/files/zip/2026-code-descriptions-tabular-order.zip"
    }
    
    def __init__(self, state_manager: Optional[ICD10DownloadStateManager] = None, 
                 output_dir: Optional[Path] = None):
        self.state_manager = state_manager or ICD10DownloadStateManager()
        self.output_dir = output_dir or Path("/home/intelluxe/database/medical_complete/icd10")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Rate limiting configuration (more conservative for medical data)
        self.max_retries = 5
        self.base_delay = 10  # Base delay in seconds (longer for ICD-10)
        self.max_delay = 7200  # Max delay (2 hours)
        self.request_timeout = 600  # 10 minutes (larger files)
        
        # Session for connection reuse
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.request_timeout),
            headers={'User-Agent': 'Intelluxe-Medical-Mirrors/1.0 (Healthcare AI System - ICD-10 Research)'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def _parse_rate_limit_headers(self, headers: Dict[str, str]) -> RateLimitInfo:
        """Parse rate limiting information from response headers"""
        rate_limit = RateLimitInfo()
        
        # Check for various rate limit header formats
        if 'Retry-After' in headers:
            rate_limit.is_limited = True
            retry_after = headers['Retry-After']
            
            # Retry-After can be seconds or HTTP date
            if retry_after.isdigit():
                rate_limit.retry_after = int(retry_after)
                rate_limit.reset_time = datetime.now() + timedelta(seconds=int(retry_after))
            else:
                try:
                    # Parse HTTP date format
                    reset_time = datetime.strptime(retry_after, '%a, %d %b %Y %H:%M:%S GMT')
                    rate_limit.reset_time = reset_time
                    rate_limit.retry_after = int((reset_time - datetime.now()).total_seconds())
                except ValueError:
                    # Default fallback
                    rate_limit.retry_after = 1800  # 30 minutes
        
        # Check for X-RateLimit headers
        if 'X-RateLimit-Remaining' in headers:
            rate_limit.remaining_requests = int(headers['X-RateLimit-Remaining'])
            if rate_limit.remaining_requests <= 0:
                rate_limit.is_limited = True
        
        if 'X-RateLimit-Reset' in headers:
            reset_timestamp = int(headers['X-RateLimit-Reset'])
            rate_limit.reset_time = datetime.fromtimestamp(reset_timestamp)
        
        if 'X-RateLimit-Limit' in headers:
            rate_limit.limit = int(headers['X-RateLimit-Limit'])
        
        return rate_limit
    
    async def _download_with_retry(self, url: str, source: str) -> Optional[bytes]:
        """Download with intelligent retry logic for ICD-10 sources"""
        state = self.state_manager.get_state(source)
        if not state:
            state = self.state_manager.create_state(source)
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Downloading ICD-10 {source} from {url} (attempt {attempt + 1}/{self.max_retries})")
                
                # Update state
                self.state_manager.update_state(source, status=DownloadStatus.IN_PROGRESS)
                
                async with self.session.get(url, allow_redirects=True) as response:
                    # Check for rate limiting
                    rate_limit = self._parse_rate_limit_headers(dict(response.headers))
                    
                    if response.status == 429 or rate_limit.is_limited:
                        # Rate limited
                        retry_after = rate_limit.retry_after or (120 * (2 ** attempt))
                        logger.warning(f"Rate limited for ICD-10 {source}, retrying after {retry_after} seconds")
                        
                        reset_time = rate_limit.reset_time or datetime.now() + timedelta(seconds=retry_after)
                        self.state_manager.mark_rate_limited(source, reset_time, retry_after)
                        
                        await asyncio.sleep(min(retry_after, self.max_delay))
                        continue
                    
                    if response.status == 404:
                        logger.error(f"ICD-10 resource not found for {source}: {url}")
                        self.state_manager.mark_failed(source, f"404 Not Found: {url}")
                        return None
                    
                    if response.status == 403:
                        logger.error(f"Access forbidden for ICD-10 {source}: {url}")
                        self.state_manager.mark_failed(source, f"403 Forbidden: {url}")
                        return None
                    
                    if response.status >= 400:
                        error_msg = f"HTTP {response.status} error for ICD-10 {source}"
                        logger.error(error_msg)
                        
                        # Exponential backoff for server errors
                        if response.status >= 500:
                            delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                            logger.info(f"Server error, retrying after {delay} seconds")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            self.state_manager.mark_failed(source, error_msg)
                            return None
                    
                    # Success - download content (may be large for ICD-10)
                    content = await response.read()
                    logger.info(f"Successfully downloaded {len(content)} bytes for ICD-10 {source}")
                    return content
            
            except asyncio.TimeoutError:
                logger.warning(f"Timeout downloading ICD-10 {source} (attempt {attempt + 1})")
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    await asyncio.sleep(delay)
                    continue
                else:
                    self.state_manager.mark_failed(source, "Download timeout after multiple retries")
            
            except Exception as e:
                logger.error(f"Error downloading ICD-10 {source}: {e}")
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    await asyncio.sleep(delay)
                    continue
                else:
                    self.state_manager.mark_failed(source, str(e))
        
        return None
    
    def _parse_icd10_zip(self, zip_content: bytes, source: str) -> List[Dict[str, Any]]:
        """Parse ICD-10 codes from CMS/WHO ZIP file"""
        codes = []
        
        try:
            with zipfile.ZipFile(io.BytesIO(zip_content)) as zf:
                # DEBUG: List all files in the zip
                logger.info(f"ZIP contains {len(zf.namelist())} files: {zf.namelist()}")
                
                # Look for ICD-10 files in the zip
                for filename in zf.namelist():
                    if self._is_icd10_file(filename):
                        logger.info(f"Processing ICD-10 file {filename} from {source}")
                        
                        with zf.open(filename) as f:
                            # Try to decode as various encodings
                            content = None
                            for encoding in ['utf-8', 'cp1252', 'latin-1', 'utf-16']:
                                try:
                                    content = f.read().decode(encoding)
                                    break
                                except UnicodeDecodeError:
                                    continue
                            
                            if not content:
                                logger.error(f"Could not decode ICD-10 file {filename}")
                                continue
                            
                            # Parse content based on format
                            if filename.lower().endswith('.xml'):
                                parsed_codes = self._parse_icd10_xml(content, filename)
                            elif filename.lower().endswith(('.txt', '.csv')):
                                parsed_codes = self._parse_icd10_text(content, filename)
                            else:
                                # Try to auto-detect format
                                parsed_codes = self._parse_icd10_content_auto(content, filename)
                            
                            codes.extend(parsed_codes)
                            
                            # Update progress
                            self.state_manager.mark_progress(
                                source, 
                                completed_items=len(codes),
                                current_file=filename
                            )
        
        except zipfile.BadZipFile:
            logger.error(f"Invalid ZIP file for ICD-10 {source}")
        except Exception as e:
            logger.error(f"Error parsing ICD-10 ZIP file for {source}: {e}")
        
        return codes
    
    def _is_icd10_file(self, filename: str) -> bool:
        """Check if a file in the ZIP is likely an ICD-10 data file"""
        filename_lower = filename.lower()
        
        # Common ICD-10 file patterns
        icd10_patterns = [
            'icd10', 'icd-10', 'tabular', 'codes', 'diagnosis',
            'cm.txt', 'pcs.txt', 'order.txt', 'xml'
        ]
        
        # Skip non-data files
        skip_patterns = [
            'readme', 'license', 'instruction', 'header', 
            'guidelines', 'intro', 'appendix', '__macosx'
        ]
        
        # Check for skip patterns first
        if any(pattern in filename_lower for pattern in skip_patterns):
            return False
        
        # Check for ICD-10 patterns
        return any(pattern in filename_lower for pattern in icd10_patterns)
    
    def _parse_icd10_xml(self, xml_content: str, filename: str) -> List[Dict[str, Any]]:
        """Parse ICD-10 codes from XML content"""
        codes = []
        
        try:
            # Remove XML namespace prefixes for easier parsing
            xml_content = re.sub(r'xmlns\w*="[^"]*"', '', xml_content)
            xml_content = re.sub(r'</?[\w:]+:', '<', xml_content)
            
            root = ET.fromstring(xml_content)
            
            # Common XML structures for ICD-10
            code_elements = (
                root.findall('.//code') + 
                root.findall('.//ICD10') + 
                root.findall('.//diagnosis') +
                root.findall('.//item')
            )
            
            for elem in code_elements:
                code_data = self._extract_icd10_from_xml_element(elem)
                if code_data:
                    codes.append(code_data)
        
        except ET.ParseError as e:
            logger.error(f"XML parsing error in {filename}: {e}")
        except Exception as e:
            logger.error(f"Error parsing ICD-10 XML from {filename}: {e}")
        
        logger.info(f"Parsed {len(codes)} ICD-10 codes from XML file {filename}")
        return codes
    
    def _parse_icd10_text(self, text_content: str, filename: str) -> List[Dict[str, Any]]:
        """Parse ICD-10 codes from text/CSV content"""
        codes = []
        lines = text_content.strip().split('\n')
        
        try:
            # Try to detect format
            if ',' in lines[0] or '\t' in lines[0]:
                # CSV/TSV format
                delimiter = ',' if ',' in lines[0] else '\t'
                
                # Try to parse as CSV with headers
                if self._looks_like_header(lines[0]):
                    reader = csv.DictReader(lines, delimiter=delimiter)
                    for row in reader:
                        code_dict = self._extract_icd10_from_csv_row(row)
                        if code_dict:
                            codes.append(code_dict)
                else:
                    # Fixed positions or simple format
                    codes = self._parse_fixed_width_icd10(lines)
            else:
                # Fixed-width or simple format
                codes = self._parse_fixed_width_icd10(lines)
        
        except Exception as e:
            logger.error(f"Error parsing ICD-10 text from {filename}: {e}")
        
        logger.info(f"Parsed {len(codes)} ICD-10 codes from text file {filename}")
        return codes
    
    def _parse_icd10_content_auto(self, content: str, filename: str) -> List[Dict[str, Any]]:
        """Auto-detect and parse ICD-10 content format"""
        # Try XML first
        if content.strip().startswith('<?xml') or '<' in content[:100]:
            return self._parse_icd10_xml(content, filename)
        else:
            return self._parse_icd10_text(content, filename)
    
    def _looks_like_header(self, line: str) -> bool:
        """Check if a line looks like a CSV header"""
        header_indicators = ['code', 'description', 'title', 'name', 'diagnosis', 'icd']
        return any(indicator in line.lower() for indicator in header_indicators)
    
    def _extract_icd10_from_xml_element(self, elem) -> Optional[Dict[str, Any]]:
        """Extract ICD-10 fields from XML element"""
        try:
            # Common XML field mappings
            code = (
                elem.get('code') or 
                elem.get('id') or
                elem.findtext('.//code') or
                elem.findtext('.//id')
            )
            
            description = (
                elem.get('description') or
                elem.get('title') or
                elem.findtext('.//description') or
                elem.findtext('.//title') or
                elem.findtext('.//name') or
                elem.text
            )
            
            if not code or not description:
                return None
            
            # Extract additional metadata
            category = elem.get('category') or elem.findtext('.//category') or ""
            chapter = elem.get('chapter') or elem.findtext('.//chapter') or ""
            
            # Determine chapter from code if not provided
            if not chapter and code:
                chapter = self._determine_icd10_chapter(code)
            
            return {
                "code": code.strip(),
                "description": description.strip(),
                "category": category.strip(),
                "chapter": chapter,
                "source": "cms_direct",
                "last_updated": datetime.now().isoformat(),
                "is_billable": self._determine_billable_status(code),
                "code_length": len(code.replace('.', ''))
            }
            
        except Exception as e:
            logger.debug(f"Error extracting ICD-10 from XML element: {e}")
            return None
    
    def _extract_icd10_from_csv_row(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Extract ICD-10 fields from CSV row"""
        try:
            # Map common field names
            field_mapping = {
                'code': ['code', 'icd10', 'icd_code', 'diagnosis_code'],
                'description': ['description', 'title', 'name', 'diagnosis', 'long_description', 'desc'],
                'category': ['category', 'cat', 'class', 'group'],
                'chapter': ['chapter', 'chap', 'section']
            }
            
            code = None
            description = None
            category = ""
            chapter = ""
            
            # Extract code
            for field_name, possible_names in field_mapping.items():
                for name in possible_names:
                    if name in row and row[name]:
                        if field_name == 'code':
                            code = row[name].strip()
                        elif field_name == 'description':
                            description = row[name].strip()
                        elif field_name == 'category':
                            category = row[name].strip()
                        elif field_name == 'chapter':
                            chapter = row[name].strip()
                        break
                if (field_name == 'code' and code) or (field_name == 'description' and description):
                    break
            
            if not code or not description:
                return None
            
            # Determine chapter from code if not provided
            if not chapter:
                chapter = self._determine_icd10_chapter(code)
            
            return {
                "code": code,
                "description": description,
                "category": category,
                "chapter": chapter,
                "source": "cms_direct",
                "last_updated": datetime.now().isoformat(),
                "is_billable": self._determine_billable_status(code),
                "code_length": len(code.replace('.', ''))
            }
            
        except Exception as e:
            logger.debug(f"Error extracting ICD-10 from CSV row: {e}")
            return None
    
    def _parse_fixed_width_icd10(self, lines: List[str]) -> List[Dict[str, Any]]:
        """Parse fixed-width ICD-10 format"""
        codes = []
        
        for line in lines[1:]:  # Skip potential header
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('//'):
                continue
            
            try:
                # Common ICD-10 fixed-width formats
                if '\t' in line:
                    # Tab-separated
                    parts = line.split('\t')
                elif '|' in line:
                    # Pipe-separated
                    parts = line.split('|')
                else:
                    # Fixed positions (common CMS format)
                    if len(line) > 20:
                        # Typical format: CODE (positions 0-7), DESCRIPTION (positions 8+)
                        code = line[:8].strip()
                        description = line[8:].strip()
                        parts = [code, description]
                    else:
                        continue
                
                if len(parts) >= 2:
                    code = parts[0].strip()
                    description = parts[1].strip()
                    category = parts[2].strip() if len(parts) > 2 else ""
                    
                    if code and description and self._is_valid_icd10_code(code):
                        codes.append({
                            "code": code,
                            "description": description,
                            "category": category,
                            "chapter": self._determine_icd10_chapter(code),
                            "source": "cms_direct",
                            "last_updated": datetime.now().isoformat(),
                            "is_billable": self._determine_billable_status(code),
                            "code_length": len(code.replace('.', ''))
                        })
            
            except Exception as e:
                logger.debug(f"Error parsing ICD-10 line: {line} - {e}")
                continue
        
        return codes
    
    def _is_valid_icd10_code(self, code: str) -> bool:
        """Check if a code looks like a valid ICD-10 code"""
        if not code or len(code) < 3:
            return False
        
        # Basic ICD-10 pattern: Letter followed by digits (with optional decimal)
        pattern = r'^[A-Z]\d{2}(\.\w+)?$'
        return bool(re.match(pattern, code.upper().replace(' ', '')))
    
    def _determine_icd10_chapter(self, code: str) -> str:
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
    
    def _determine_billable_status(self, code: str) -> bool:
        """Determine if an ICD-10 code is billable (has sufficient specificity)"""
        if not code:
            return False
        
        # Generally, ICD-10 codes with more specificity are billable
        # This is a simplified check - real validation would be more complex
        clean_code = code.replace('.', '')
        
        # Codes with 4+ characters are usually billable
        # 3-character codes are usually not billable (category codes)
        return len(clean_code) >= 4
    
    async def download_all_icd10(self) -> Dict[str, List[Dict[str, Any]]]:
        """Download all ICD-10 codes from CMS/WHO sources"""
        logger.info("Starting CMS/WHO ICD-10 download process")
        all_codes = {}
        
        for source, url in self.CMS_URLS.items():
            logger.info(f"Processing ICD-10 source: {source}")
            
            # Check if source is already completed
            state = self.state_manager.get_state(source)
            if state and state.status == DownloadStatus.COMPLETED:
                logger.info(f"ICD-10 source {source} already completed, skipping")
                continue
            
            # Check if source is rate limited and not ready
            if (state and state.status == DownloadStatus.RATE_LIMITED and 
                state.next_retry):
                try:
                    retry_time = datetime.fromisoformat(state.next_retry)
                    if datetime.now() < retry_time:
                        logger.info(f"ICD-10 source {source} rate limited until {state.next_retry}, skipping")
                        continue
                except Exception:
                    pass
            
            # Download the content
            content = await self._download_with_retry(url, source)
            if not content:
                logger.error(f"Failed to download ICD-10 {source}")
                continue
            
            # Parse the content
            codes = self._parse_icd10_zip(content, source)
            if codes:
                all_codes[source] = codes
                self.state_manager.mark_completed(source, len(codes))
                logger.info(f"Successfully processed {len(codes)} ICD-10 codes from {source}")
                
                # Save intermediate results
                output_file = self.output_dir / f"{source}_codes.json"
                await self._save_codes_to_file(codes, output_file)
            else:
                self.state_manager.mark_failed(source, "No ICD-10 codes extracted from download")
        
        return all_codes
    
    async def _save_codes_to_file(self, codes: List[Dict[str, Any]], output_file: Path):
        """Save ICD-10 codes to JSON file"""
        try:
            import json
            with open(output_file, 'w') as f:
                json.dump(codes, f, indent=2, default=str)
            logger.info(f"Saved {len(codes)} ICD-10 codes to {output_file}")
        except Exception as e:
            logger.error(f"Error saving ICD-10 codes to {output_file}: {e}")
    
    def get_download_progress(self) -> Dict[str, Any]:
        """Get current ICD-10 download progress"""
        return self.state_manager.get_progress_summary()


async def main():
    """Test the CMS ICD-10 downloader"""
    logging.basicConfig(level=logging.INFO)
    
    async with CMSICD10Downloader() as downloader:
        # Download all ICD-10 codes
        all_codes = await downloader.download_all_icd10()
        
        total_codes = sum(len(codes) for codes in all_codes.values())
        print(f"Downloaded {total_codes} total ICD-10 codes from {len(all_codes)} sources")
        
        # Show progress
        progress = downloader.get_download_progress()
        print(f"Download progress: {progress}")


if __name__ == "__main__":
    asyncio.run(main())