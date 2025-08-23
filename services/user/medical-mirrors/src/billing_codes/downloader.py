"""
Medical billing codes (CPT/HCPCS) downloader using NLM Clinical Tables API
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional

import aiohttp
from aiohttp import ClientError

from ..config import Config

logger = logging.getLogger(__name__)


class BillingCodesDownloader:
    """Downloads medical billing codes (HCPCS/CPT) from NLM Clinical Tables API"""
    
    def __init__(self, config: Config):
        self.config = config
        self.hcpcs_url = "https://clinicaltables.nlm.nih.gov/api/hcpcs/v3"
        self.session = None
        self.download_stats = {
            "hcpcs_codes_downloaded": 0,
            "cpt_codes_downloaded": 0,
            "requests_made": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"User-Agent": "Medical-Mirrors/1.0 (Healthcare Research)"}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def download_all_codes(self) -> List[Dict]:
        """Download all available billing codes"""
        logger.info("Starting comprehensive billing codes download")
        self.download_stats["start_time"] = datetime.now()
        
        all_codes = []
        
        try:
            # Download HCPCS codes (Level II)
            hcpcs_codes = await self._download_hcpcs_codes()
            all_codes.extend(hcpcs_codes)
            
            # Download available CPT-like codes (limited by copyright)
            # Note: Full CPT codes require AMA licensing
            cpt_codes = await self._download_available_cpt_codes()
            all_codes.extend(cpt_codes)
            
            # Deduplicate codes
            codes_dict = {code["code"]: code for code in all_codes}
            final_codes = list(codes_dict.values())
            
            self.download_stats["end_time"] = datetime.now()
            total_downloaded = len(final_codes)
            
            logger.info(f"Downloaded {total_downloaded} billing codes total")
            return final_codes
            
        except Exception as e:
            logger.error(f"Error in billing codes download: {e}")
            self.download_stats["errors"] += 1
            raise
    
    async def _download_hcpcs_codes(self) -> List[Dict]:
        """Download HCPCS Level II codes systematically"""
        logger.info("Downloading HCPCS Level II codes")
        
        all_codes = []
        
        # HCPCS Level II code categories
        hcpcs_categories = [
            "A",   # Transportation services, medical supplies
            "B",   # Enteral and parenteral therapy
            "C",   # Temporary hospital outpatient PPS
            "D",   # Dental procedures
            "E",   # Durable medical equipment
            "G",   # Temporary physician procedures
            "H",   # Behavioral health and substance abuse
            "J",   # Drugs administered other than oral method
            "K",   # Temporary codes
            "L",   # Orthotic/prosthetic procedures
            "M",   # Medical services
            "P",   # Pathology and laboratory services
            "Q",   # Temporary codes
            "R",   # Diagnostic radiology services
            "S",   # Temporary national codes
            "T",   # State Medicaid agency codes
            "V",   # Vision services
        ]
        
        for category in hcpcs_categories:
            try:
                category_codes = await self._search_billing_codes(f"{category}*", code_type="hcpcs")
                all_codes.extend(category_codes)
                
                logger.info(f"Downloaded {len(category_codes)} HCPCS codes for category {category}")
                self.download_stats["hcpcs_codes_downloaded"] += len(category_codes)
                
                # Rate limiting
                await asyncio.sleep(self.config.REQUEST_DELAY)
                
            except Exception as e:
                logger.error(f"Error downloading HCPCS category {category}: {e}")
                self.download_stats["errors"] += 1
                continue
        
        # Additional comprehensive searches for common procedures
        common_procedures = [
            "injection", "infusion", "procedure", "supply", "equipment",
            "orthotic", "prosthetic", "therapy", "radiology", "laboratory"
        ]
        
        for procedure in common_procedures:
            try:
                codes = await self._search_billing_codes(procedure, code_type="hcpcs", max_results=50)
                all_codes.extend(codes)
                
                await asyncio.sleep(self.config.REQUEST_DELAY)
                
            except Exception as e:
                logger.error(f"Error searching HCPCS for '{procedure}': {e}")
                continue
        
        return all_codes
    
    async def _download_available_cpt_codes(self) -> List[Dict]:
        """Download available CPT codes (limited by copyright restrictions)"""
        logger.info("Downloading available CPT codes (limited by copyright)")
        
        # Note: Full CPT codes are copyrighted by AMA
        # We can only get limited public domain codes or category headers
        
        all_codes = []
        
        # Try to get any publicly available CPT information
        # This would typically be category headers or procedure groups
        try:
            # Search for common CPT procedure categories
            cpt_searches = [
                "evaluation management",
                "anesthesia",
                "surgery", 
                "radiology",
                "pathology",
                "medicine"
            ]
            
            for search_term in cpt_searches:
                try:
                    # Try searching with CPT-related terms
                    codes = await self._search_billing_codes(search_term, code_type="cpt", max_results=20)
                    all_codes.extend(codes)
                    
                    await asyncio.sleep(self.config.REQUEST_DELAY)
                    
                except Exception as e:
                    logger.debug(f"Limited CPT search for '{search_term}': {e}")
                    continue
            
            self.download_stats["cpt_codes_downloaded"] = len(all_codes)
            
        except Exception as e:
            logger.info(f"CPT code access limited (expected due to copyright): {e}")
        
        return all_codes
    
    async def _search_billing_codes(
        self, 
        query: str, 
        code_type: str = "hcpcs",
        max_results: int = 100
    ) -> List[Dict]:
        """Search for billing codes using the NLM API"""
        
        if code_type.lower() == "hcpcs":
            url = f"{self.hcpcs_url}/search"
        else:
            # CPT searches might not be available or limited
            logger.debug(f"CPT search attempted for: {query}")
            return []
        
        params = {
            "sf": "code,short_name,long_name",
            "df": "code,short_name,long_name", 
            "maxList": min(max_results, 500),
            "q": query
        }
        
        try:
            self.download_stats["requests_made"] += 1
            
            async with self.session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                
                return self._parse_api_response(data, code_type)
                
        except ClientError as e:
            logger.error(f"HTTP error searching billing codes for '{query}': {e}")
            self.download_stats["errors"] += 1
            raise
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for query '{query}': {e}")
            self.download_stats["errors"] += 1
            raise
        except Exception as e:
            logger.error(f"Unexpected error searching '{query}': {e}")
            self.download_stats["errors"] += 1
            raise
    
    def _parse_api_response(self, data: Dict, code_type: str) -> List[Dict]:
        """Parse NLM API response into standardized format"""
        codes = []
        
        if not isinstance(data, list) or len(data) < 3:
            logger.warning("Unexpected billing codes API response format")
            return codes
        
        try:
            # NLM HCPCS API returns: [total_count, codes, short_names, long_names]
            total_count = data[0] if len(data) > 0 else 0
            code_list = data[1] if len(data) > 1 else []
            short_name_list = data[2] if len(data) > 2 else []
            long_name_list = data[3] if len(data) > 3 else []
            
            # Pair up codes with their descriptions
            for i, code in enumerate(code_list):
                short_name = short_name_list[i] if i < len(short_name_list) else ""
                long_name = long_name_list[i] if i < len(long_name_list) else ""
                
                billing_code = {
                    "code": code.strip(),
                    "short_description": short_name.strip() if short_name else "",
                    "long_description": long_name.strip() if long_name else short_name.strip(),
                    "code_type": code_type.upper(),
                    "category": self._determine_billing_category(code, code_type),
                    "effective_date": None,  # Not provided by API
                    "coverage_notes": "",    # Would need additional lookup
                    "source": "nlm_clinical_tables",
                    "last_updated": datetime.now().isoformat(),
                    "api_total_count": total_count
                }
                codes.append(billing_code)
            
        except (IndexError, KeyError, TypeError) as e:
            logger.error(f"Error parsing billing codes API response: {e}")
            return []
        
        return codes
    
    def _determine_billing_category(self, code: str, code_type: str) -> str:
        """Determine billing code category"""
        if not code:
            return "Unknown"
        
        if code_type.upper() == "HCPCS":
            # HCPCS Level II categories
            hcpcs_categories = {
                "A": "Transportation Services, Medical and Surgical Supplies",
                "B": "Enteral and Parenteral Therapy",
                "C": "Temporary Hospital Outpatient PPS",
                "D": "Dental Procedures", 
                "E": "Durable Medical Equipment",
                "G": "Temporary Physician Procedures",
                "H": "Behavioral Health and Substance Abuse Treatment",
                "J": "Drugs Administered Other Than Oral Method",
                "K": "Temporary Codes",
                "L": "Orthotic and Prosthetic Procedures",
                "M": "Medical Services",
                "P": "Pathology and Laboratory Services",
                "Q": "Temporary Codes",
                "R": "Diagnostic Radiology Services",
                "S": "Temporary National Codes",
                "T": "State Medicaid Agency Codes",
                "V": "Vision Services",
            }
            
            first_char = code[0].upper()
            return hcpcs_categories.get(first_char, "Unknown HCPCS Category")
        
        elif code_type.upper() == "CPT":
            # CPT code ranges (general categories)
            try:
                code_num = int(code)
                if 99201 <= code_num <= 99499:
                    return "Evaluation and Management"
                elif 10000 <= code_num <= 69999:
                    return "Surgery"
                elif 70000 <= code_num <= 79999:
                    return "Radiology"
                elif 80000 <= code_num <= 89999:
                    return "Pathology and Laboratory"
                elif 90000 <= code_num <= 99199:
                    return "Medicine"
                else:
                    return "Other CPT"
            except ValueError:
                return "CPT Category"
        
        return "Unknown"
    
    async def download_incremental_updates(self, since_date: Optional[datetime] = None) -> List[Dict]:
        """Download incremental updates since a given date"""
        logger.info(f"Checking for billing codes updates since {since_date}")
        
        # For billing codes, incremental updates are not directly supported by the API
        # We would need to download all and compare with existing data
        
        logger.info("Billing codes incremental updates not supported - performing full download")
        return await self.download_all_codes()
    
    def get_download_stats(self) -> Dict:
        """Get download statistics"""
        stats = self.download_stats.copy()
        
        if stats["start_time"] and stats["end_time"]:
            duration = stats["end_time"] - stats["start_time"]
            stats["duration_seconds"] = duration.total_seconds()
            
            total_codes = stats["hcpcs_codes_downloaded"] + stats["cpt_codes_downloaded"]
            stats["total_codes_downloaded"] = total_codes
            stats["codes_per_second"] = (
                total_codes / duration.total_seconds()
                if duration.total_seconds() > 0 else 0
            )
        
        return stats


async def main():
    """Test the billing codes downloader"""
    logging.basicConfig(level=logging.INFO)
    config = Config()
    
    async with BillingCodesDownloader(config) as downloader:
        # Test HCPCS search
        codes = await downloader._search_billing_codes("injection", code_type="hcpcs", max_results=10)
        print(f"Found {len(codes)} HCPCS codes for injection:")
        for code in codes[:5]:
            print(f"  {code['code']}: {code['long_description']}")
        
        # Get stats
        stats = downloader.get_download_stats()
        print(f"\nDownload stats: {stats}")


if __name__ == "__main__":
    asyncio.run(main())