"""
ICD-10 codes downloader using NLM Clinical Tables API
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


class ICD10Downloader:
    """Downloads ICD-10 diagnostic codes from NLM Clinical Tables API"""
    
    def __init__(self, config: Config):
        self.config = config
        self.base_url = "https://clinicaltables.nlm.nih.gov/api/icd10cm/v3"
        self.session = None
        self.download_stats = {
            "codes_downloaded": 0,
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
        """Download all ICD-10 codes systematically"""
        logger.info("Starting comprehensive ICD-10 codes download")
        self.download_stats["start_time"] = datetime.now()
        
        all_codes = []
        
        try:
            # Strategy 1: Get codes by major categories (chapters)
            chapter_codes = await self._download_by_chapters()
            all_codes.extend(chapter_codes)
            
            # Strategy 2: Comprehensive search for any missed codes
            additional_codes = await self._download_comprehensive_search()
            
            # Deduplicate codes
            codes_dict = {code["code"]: code for code in all_codes + additional_codes}
            final_codes = list(codes_dict.values())
            
            self.download_stats["codes_downloaded"] = len(final_codes)
            self.download_stats["end_time"] = datetime.now()
            
            logger.info(f"Downloaded {len(final_codes)} ICD-10 codes")
            return final_codes
            
        except Exception as e:
            logger.error(f"Error in ICD-10 download: {e}")
            self.download_stats["errors"] += 1
            raise
    
    async def _download_by_chapters(self) -> List[Dict]:
        """Download codes organized by ICD-10 chapters"""
        logger.info("Downloading ICD-10 codes by chapters")
        
        # ICD-10 major chapters/categories
        chapters = [
            "A", "B",  # Certain infectious and parasitic diseases
            "C", "D",  # Neoplasms, Blood and blood-forming organs
            "E",       # Endocrine, nutritional and metabolic diseases
            "F",       # Mental, behavioral and neurodevelopmental disorders
            "G",       # Diseases of the nervous system
            "H",       # Diseases of the eye and adnexa, ear
            "I",       # Diseases of the circulatory system
            "J",       # Diseases of the respiratory system
            "K",       # Diseases of the digestive system
            "L",       # Diseases of the skin and subcutaneous tissue
            "M",       # Diseases of the musculoskeletal system
            "N",       # Diseases of the genitourinary system
            "O",       # Pregnancy, childbirth and the puerperium
            "P",       # Certain conditions originating in the perinatal period
            "Q",       # Congenital malformations
            "R",       # Symptoms, signs and abnormal clinical findings
            "S", "T",  # Injury, poisoning
            "V", "W", "X", "Y",  # External causes of morbidity
            "Z",       # Factors influencing health status
        ]
        
        all_codes = []
        
        for chapter in chapters:
            try:
                chapter_codes = await self._search_codes(f"{chapter}*", max_results=1000)
                all_codes.extend(chapter_codes)
                
                logger.info(f"Downloaded {len(chapter_codes)} codes for chapter {chapter}")
                
                # Rate limiting
                await asyncio.sleep(self.config.REQUEST_DELAY)
                
            except Exception as e:
                logger.error(f"Error downloading chapter {chapter}: {e}")
                self.download_stats["errors"] += 1
                continue
        
        return all_codes
    
    async def _download_comprehensive_search(self) -> List[Dict]:
        """Perform comprehensive searches to catch any missed codes"""
        logger.info("Performing comprehensive ICD-10 search")
        
        # Common medical terms to ensure comprehensive coverage
        search_terms = [
            "disease", "disorder", "syndrome", "infection", "injury",
            "cancer", "diabetes", "hypertension", "pneumonia", "fracture",
            "pregnancy", "mental", "heart", "lung", "kidney", "liver",
            "skin", "bone", "blood", "brain", "eye", "ear"
        ]
        
        all_codes = []
        
        for term in search_terms:
            try:
                codes = await self._search_codes(term, max_results=100)
                all_codes.extend(codes)
                
                # Rate limiting
                await asyncio.sleep(self.config.REQUEST_DELAY)
                
            except Exception as e:
                logger.error(f"Error searching term '{term}': {e}")
                continue
        
        return all_codes
    
    async def _search_codes(self, query: str, max_results: int = 100) -> List[Dict]:
        """Search for ICD-10 codes using the NLM API"""
        url = f"{self.base_url}/search"
        
        params = {
            "sf": "code,name",  # Return code and name fields
            "df": "code,name,synonyms",  # Search in code, name, and synonyms
            "maxList": min(max_results, 500),  # API limit
            "q": query
        }
        
        try:
            self.download_stats["requests_made"] += 1
            
            async with self.session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                
                return self._parse_api_response(data)
                
        except ClientError as e:
            logger.error(f"HTTP error searching ICD-10 codes for '{query}': {e}")
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
    
    def _parse_api_response(self, data: Dict) -> List[Dict]:
        """Parse NLM API response into standardized format"""
        codes = []
        
        if not isinstance(data, list) or len(data) < 4:
            logger.warning("Unexpected API response format")
            return codes
        
        # NLM API returns: [total_count, codes, descriptions, synonyms]
        try:
            total_count = data[0]
            code_list = data[1] if len(data) > 1 else []
            name_list = data[2] if len(data) > 2 else []
            synonym_list = data[3] if len(data) > 3 else []
            
            # Pair up codes with their descriptions
            for i, code in enumerate(code_list):
                if i < len(name_list):
                    icd_code = {
                        "code": code.strip(),
                        "description": name_list[i].strip() if name_list[i] else "",
                        "category": self._determine_category(code),
                        "chapter": code[0] if code else "",
                        "synonyms": synonym_list[i] if i < len(synonym_list) and synonym_list[i] else [],
                        "source": "nlm_clinical_tables",
                        "last_updated": datetime.now().isoformat(),
                        "api_total_count": total_count
                    }
                    codes.append(icd_code)
            
        except (IndexError, KeyError, TypeError) as e:
            logger.error(f"Error parsing API response: {e}")
            return []
        
        return codes
    
    def _determine_category(self, code: str) -> str:
        """Determine ICD-10 category based on code prefix"""
        if not code:
            return "Unknown"
        
        chapter_map = {
            "A": "Certain infectious and parasitic diseases",
            "B": "Certain infectious and parasitic diseases", 
            "C": "Neoplasms",
            "D": "Diseases of the blood and blood-forming organs",
            "E": "Endocrine, nutritional and metabolic diseases",
            "F": "Mental, behavioral and neurodevelopmental disorders",
            "G": "Diseases of the nervous system",
            "H": "Diseases of the eye and adnexa / ear",
            "I": "Diseases of the circulatory system",
            "J": "Diseases of the respiratory system", 
            "K": "Diseases of the digestive system",
            "L": "Diseases of the skin and subcutaneous tissue",
            "M": "Diseases of the musculoskeletal system and connective tissue",
            "N": "Diseases of the genitourinary system",
            "O": "Pregnancy, childbirth and the puerperium",
            "P": "Certain conditions originating in the perinatal period",
            "Q": "Congenital malformations, deformations and chromosomal abnormalities",
            "R": "Symptoms, signs and abnormal clinical and laboratory findings",
            "S": "Injury, poisoning and certain other consequences of external causes",
            "T": "Injury, poisoning and certain other consequences of external causes",
            "V": "External causes of morbidity",
            "W": "External causes of morbidity",
            "X": "External causes of morbidity", 
            "Y": "External causes of morbidity",
            "Z": "Factors influencing health status and contact with health services"
        }
        
        first_char = code[0].upper()
        return chapter_map.get(first_char, "Unknown")
    
    async def download_incremental_updates(self, since_date: Optional[datetime] = None) -> List[Dict]:
        """Download incremental updates since a given date"""
        logger.info(f"Checking for ICD-10 updates since {since_date}")
        
        # For ICD-10, incremental updates are not directly supported by the API
        # We would need to download all and compare with existing data
        # This is a placeholder for future enhancement
        
        logger.info("ICD-10 incremental updates not supported - performing full download")
        return await self.download_all_codes()
    
    def get_download_stats(self) -> Dict:
        """Get download statistics"""
        stats = self.download_stats.copy()
        if stats["start_time"] and stats["end_time"]:
            duration = stats["end_time"] - stats["start_time"]
            stats["duration_seconds"] = duration.total_seconds()
            stats["codes_per_second"] = (
                stats["codes_downloaded"] / duration.total_seconds()
                if duration.total_seconds() > 0 else 0
            )
        return stats


async def main():
    """Test the ICD-10 downloader"""
    logging.basicConfig(level=logging.INFO)
    config = Config()
    
    async with ICD10Downloader(config) as downloader:
        # Test search
        codes = await downloader._search_codes("diabetes", max_results=10)
        print(f"Found {len(codes)} codes for diabetes:")
        for code in codes[:5]:
            print(f"  {code['code']}: {code['description']}")
        
        # Get stats
        stats = downloader.get_download_stats()
        print(f"\nDownload stats: {stats}")


if __name__ == "__main__":
    asyncio.run(main())