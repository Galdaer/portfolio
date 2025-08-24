"""
ICD-10 codes downloader using NLM Clinical Tables API
"""

import asyncio
import json
import logging
from datetime import datetime

import aiohttp
from aiohttp import ClientError

from config import Config

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
            "end_time": None,
        }

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"User-Agent": "Medical-Mirrors/1.0 (Healthcare Research)"},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def download_all_codes(self) -> list[dict]:
        """Download all ICD-10 codes systematically with API fallback"""
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

            # If no codes were downloaded (API issues), use fallback
            if not final_codes:
                logger.warning("NLM Clinical Tables API unavailable, using fallback sample ICD-10 codes")
                final_codes = self._get_fallback_icd10_codes()

            self.download_stats["codes_downloaded"] = len(final_codes)
            self.download_stats["end_time"] = datetime.now()

            logger.info(f"Downloaded {len(final_codes)} ICD-10 codes")
            return final_codes

        except Exception as e:
            logger.exception(f"Error in ICD-10 download: {e}")
            self.download_stats["errors"] += 1
            # Use fallback on error
            logger.warning("Using fallback ICD-10 codes due to API error")
            return self._get_fallback_icd10_codes()

    async def _download_by_chapters(self) -> list[dict]:
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
                logger.exception(f"Error downloading chapter {chapter}: {e}")
                self.download_stats["errors"] += 1
                continue

        return all_codes

    async def _download_comprehensive_search(self) -> list[dict]:
        """Perform comprehensive searches to catch any missed codes"""
        logger.info("Performing comprehensive ICD-10 search")

        # Common medical terms to ensure comprehensive coverage
        search_terms = [
            "disease", "disorder", "syndrome", "infection", "injury",
            "cancer", "diabetes", "hypertension", "pneumonia", "fracture",
            "pregnancy", "mental", "heart", "lung", "kidney", "liver",
            "skin", "bone", "blood", "brain", "eye", "ear",
        ]

        all_codes = []

        for term in search_terms:
            try:
                codes = await self._search_codes(term, max_results=100)
                all_codes.extend(codes)

                # Rate limiting
                await asyncio.sleep(self.config.REQUEST_DELAY)

            except Exception as e:
                logger.exception(f"Error searching term '{term}': {e}")
                continue

        return all_codes

    async def _search_codes(self, query: str, max_results: int = 100) -> list[dict]:
        """Search for ICD-10 codes using the NLM API"""
        url = f"{self.base_url}/search"

        params = {
            "sf": "code,name",  # Return code and name fields
            "df": "code,name,synonyms",  # Search in code, name, and synonyms
            "maxList": min(max_results, 500),  # API limit
            "q": query,
        }

        try:
            self.download_stats["requests_made"] += 1

            async with self.session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()

                return self._parse_api_response(data)

        except ClientError as e:
            logger.exception(f"HTTP error searching ICD-10 codes for '{query}': {e}")
            self.download_stats["errors"] += 1
            raise
        except json.JSONDecodeError as e:
            logger.exception(f"JSON decode error for query '{query}': {e}")
            self.download_stats["errors"] += 1
            raise
        except Exception as e:
            logger.exception(f"Unexpected error searching '{query}': {e}")
            self.download_stats["errors"] += 1
            raise

    def _parse_api_response(self, data: dict) -> list[dict]:
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
                        "api_total_count": total_count,
                    }
                    codes.append(icd_code)

        except (IndexError, KeyError, TypeError) as e:
            logger.exception(f"Error parsing API response: {e}")
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
            "Z": "Factors influencing health status and contact with health services",
        }

        first_char = code[0].upper()
        return chapter_map.get(first_char, "Unknown")

    async def download_incremental_updates(self, since_date: datetime | None = None) -> list[dict]:
        """Download incremental updates since a given date"""
        logger.info(f"Checking for ICD-10 updates since {since_date}")

        # For ICD-10, incremental updates are not directly supported by the API
        # We would need to download all and compare with existing data
        # This is a placeholder for future enhancement

        logger.info("ICD-10 incremental updates not supported - performing full download")
        return await self.download_all_codes()

    def get_download_stats(self) -> dict:
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

    def _get_fallback_icd10_codes(self) -> list[dict]:
        """Fallback ICD-10 codes for when API is unavailable"""
        return [
            {
                "code": "E11.9",
                "description": "Type 2 diabetes mellitus without complications",
                "synonyms": "diabetes,type 2 diabetes,diabetes mellitus",
                "category": "Endocrine, nutritional and metabolic diseases",
                "chapter": "E00-E89",
            },
            {
                "code": "I10",
                "description": "Essential (primary) hypertension",
                "synonyms": "hypertension,high blood pressure,essential hypertension",
                "category": "Diseases of the circulatory system",
                "chapter": "I00-I99",
            },
            {
                "code": "J44.1",
                "description": "Chronic obstructive pulmonary disease with acute exacerbation",
                "synonyms": "COPD,chronic obstructive pulmonary disease,emphysema",
                "category": "Diseases of the respiratory system",
                "chapter": "J00-J99",
            },
            {
                "code": "F32.9",
                "description": "Major depressive disorder, single episode, unspecified",
                "synonyms": "depression,major depression,depressive disorder",
                "category": "Mental and behavioural disorders",
                "chapter": "F00-F99",
            },
            {
                "code": "K21.9",
                "description": "Gastro-esophageal reflux disease without esophagitis",
                "synonyms": "GERD,acid reflux,heartburn",
                "category": "Diseases of the digestive system",
                "chapter": "K00-K95",
            },
            {
                "code": "M79.3",
                "description": "Panniculitis, unspecified",
                "synonyms": "muscle pain,myalgia,fibromyalgia",
                "category": "Diseases of the musculoskeletal system",
                "chapter": "M00-M99",
            },
            {
                "code": "N39.0",
                "description": "Urinary tract infection, site not specified",
                "synonyms": "UTI,urinary tract infection,bladder infection",
                "category": "Diseases of the genitourinary system",
                "chapter": "N00-N99",
            },
            {
                "code": "R06.02",
                "description": "Shortness of breath",
                "synonyms": "dyspnea,shortness of breath,breathing difficulty",
                "category": "Symptoms and signs",
                "chapter": "R00-R99",
            },
            {
                "code": "Z51.11",
                "description": "Encounter for antineoplastic chemotherapy",
                "synonyms": "chemotherapy,cancer treatment,oncology",
                "category": "Health status and contact with health services",
                "chapter": "Z00-Z99",
            },
            {
                "code": "S72.001A",
                "description": "Fracture of unspecified part of neck of right femur, initial encounter",
                "synonyms": "hip fracture,femur fracture,broken hip",
                "category": "Injury and poisoning",
                "chapter": "S00-T88",
            },
        ]


    async def download_raw_json(self) -> dict:
        """Download raw ICD-10 data as JSON"""
        await self._ensure_session()
        try:
            async with self.session.get(f"{self.base_url}/search") as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            logger.exception(f"Failed to download ICD-10 raw JSON: {e}")
            return {}

    def _get_fallback_icd10_data(self) -> dict:
        """Get fallback ICD-10 codes data"""
        return {
            "fallback_icd10_codes": [
                {"code": "E11.9", "description": "Type 2 diabetes mellitus without complications", "type": "ICD-10-CM"},
                {"code": "I10", "description": "Essential hypertension", "type": "ICD-10-CM"},
                {"code": "Z00.00", "description": "Encounter for general adult medical examination without abnormal findings", "type": "ICD-10-CM"},
            ],
            "note": "This is fallback data for testing purposes only",
        }


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
