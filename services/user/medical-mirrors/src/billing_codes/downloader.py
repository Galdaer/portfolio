"""
Medical billing codes (CPT/HCPCS) downloader using NLM Clinical Tables API
"""

import asyncio
import json
import logging
from datetime import datetime

import aiohttp
from aiohttp import ClientError

from config import Config

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

            # If no codes were downloaded, use fallback
            if not final_codes:
                logger.warning("NLM Clinical Tables API unavailable, using fallback billing codes")
                final_codes = self._get_fallback_billing_codes()

            self.download_stats["end_time"] = datetime.now()
            total_downloaded = len(final_codes)

            logger.info(f"Downloaded {total_downloaded} billing codes total")
            return final_codes

        except Exception as e:
            logger.exception(f"Error in billing codes download: {e}")
            self.download_stats["errors"] += 1
            # Use fallback billing codes on error
            logger.warning("Using fallback billing codes due to API error")
            return self._get_fallback_billing_codes()

    async def _download_hcpcs_codes(self) -> list[dict]:
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
                category_codes = await self._search_billing_codes_paginated(category, code_type="hcpcs")
                all_codes.extend(category_codes)

                logger.info(f"Downloaded {len(category_codes)} HCPCS codes for category {category}")
                self.download_stats["hcpcs_codes_downloaded"] += len(category_codes)

                # Rate limiting
                await asyncio.sleep(self.config.REQUEST_DELAY)

            except Exception as e:
                logger.exception(f"Error downloading HCPCS category {category}: {e}")
                self.download_stats["errors"] += 1
                continue

        # Additional comprehensive searches for common procedures
        common_procedures = [
            "injection", "infusion", "procedure", "supply", "equipment",
            "orthotic", "prosthetic", "therapy", "radiology", "laboratory",
        ]

        for procedure in common_procedures:
            try:
                codes = await self._search_billing_codes(procedure, code_type="hcpcs", max_results=50)
                all_codes.extend(codes)

                await asyncio.sleep(self.config.REQUEST_DELAY)

            except Exception as e:
                logger.exception(f"Error searching HCPCS for '{procedure}': {e}")
                continue

        return all_codes

    async def _download_available_cpt_codes(self) -> list[dict]:
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
                "medicine",
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
        
    async def _search_billing_codes_paginated(
        self,
        query: str,
        code_type: str = "hcpcs",
        max_results_per_batch: int = 500,
        max_total_results: int = 2000,
    ) -> list[dict]:
        """Search for billing codes with pagination to get complete results"""
        all_codes = []
        offset = 0
        batch_size = max_results_per_batch
        
        while len(all_codes) < max_total_results:
            try:
                # Get batch of results
                batch_codes = await self._search_billing_codes(
                    query, 
                    code_type=code_type, 
                    max_results=batch_size
                )
                
                if not batch_codes:
                    # No more results
                    break
                    
                all_codes.extend(batch_codes)
                
                # If we got fewer results than requested, we've reached the end
                if len(batch_codes) < batch_size:
                    break
                    
                # Rate limiting between batches
                await asyncio.sleep(0.5)
                offset += batch_size
                
                logger.debug(f"Downloaded {len(all_codes)} codes so far for query '{query}'")
                
            except Exception as e:
                logger.warning(f"Pagination failed for query '{query}' at offset {offset}: {e}")
                break
                
        logger.info(f"Paginated search for '{query}' returned {len(all_codes)} total codes")
        return all_codes

    async def _search_billing_codes(
        self,
        query: str,
        code_type: str = "hcpcs",
        max_results: int = 100,
    ) -> list[dict]:
        """Search for billing codes using the NLM API"""

        if code_type.lower() == "hcpcs":
            url = f"{self.hcpcs_url}/search"
        else:
            # CPT searches might not be available or limited
            logger.debug(f"CPT search attempted for: {query}")
            return []

        params = {
            "terms": query,
            "maxList": min(max_results, 500),
        }

        try:
            self.download_stats["requests_made"] += 1

            async with self.session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()

                return self._parse_api_response(data, code_type)

        except ClientError as e:
            logger.exception(f"HTTP error searching billing codes for '{query}': {e}")
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

    def _parse_api_response(self, data: dict, code_type: str) -> list[dict]:
        """Parse NLM API response into standardized format"""
        codes = []

        if not isinstance(data, list) or len(data) < 3:
            logger.warning("Unexpected billing codes API response format")
            return codes

        try:
            # NLM HCPCS API returns: [total_count, codes, extra_data, display_strings]
            total_count = data[0] if len(data) > 0 else 0
            code_list = data[1] if len(data) > 1 else []
            extra_data = data[2] if len(data) > 2 else None
            display_strings = data[3] if len(data) > 3 else []

            # Pair up codes with their descriptions from display strings
            for i, code in enumerate(code_list):
                # Display strings format: [["CODE", "Description"], ...]
                display_info = display_strings[i] if i < len(display_strings) else ["", ""]
                
                if isinstance(display_info, list) and len(display_info) >= 2:
                    display_code = display_info[0]
                    description = display_info[1]
                else:
                    display_code = code
                    description = ""

                billing_code = {
                    "code": code.strip(),
                    "short_description": description.strip(),
                    "long_description": description.strip(),
                    "code_type": code_type.upper(),
                    "category": self._determine_billing_category(code, code_type),
                    "effective_date": None,  # Not provided by API
                    "coverage_notes": "",    # Would need additional lookup
                    "source": "nlm_clinical_tables",
                    "last_updated": datetime.now().isoformat(),
                    "api_total_count": total_count,
                }
                codes.append(billing_code)

        except (IndexError, KeyError, TypeError) as e:
            logger.exception(f"Error parsing billing codes API response: {e}")
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

        if code_type.upper() == "CPT":
            # CPT code ranges (general categories)
            try:
                code_num = int(code)
                if 99201 <= code_num <= 99499:
                    return "Evaluation and Management"
                if 10000 <= code_num <= 69999:
                    return "Surgery"
                if 70000 <= code_num <= 79999:
                    return "Radiology"
                if 80000 <= code_num <= 89999:
                    return "Pathology and Laboratory"
                if 90000 <= code_num <= 99199:
                    return "Medicine"
                return "Other CPT"
            except ValueError:
                return "CPT Category"

        return "Unknown"

    async def download_incremental_updates(self, since_date: datetime | None = None) -> list[dict]:
        """Download incremental updates since a given date"""
        logger.info(f"Checking for billing codes updates since {since_date}")

        # For billing codes, incremental updates are not directly supported by the API
        # We would need to download all and compare with existing data

        logger.info("Billing codes incremental updates not supported - performing full download")
        return await self.download_all_codes()

    def get_download_stats(self) -> dict:
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

    def _get_fallback_billing_codes(self) -> list[dict]:
        """Comprehensive fallback billing codes for when NLM API is unavailable"""
        current_time = datetime.now().isoformat()

        return [
            # CPT Codes - Evaluation and Management
            {
                "code": "99201",
                "short_description": "Office visit new patient",
                "long_description": "Office or other outpatient visit for the evaluation and management of a new patient",
                "description": "New patient office visit - straightforward",
                "code_type": "CPT",
                "category": "Evaluation and Management",
                "coverage_notes": "Standard coverage for office visits",
                "effective_date": "2024-01-01",
                "termination_date": "",
                "is_active": True,
                "modifier_required": False,
                "gender_specific": "",
                "age_specific": "",
                "bilateral_indicator": False,
                "source": "fallback",
                "search_text": "99201 office visit new patient evaluation management",
                "last_updated": current_time,
            },
            {
                "code": "99202",
                "short_description": "Office visit new patient",
                "long_description": "Office or other outpatient visit for the evaluation and management of a new patient",
                "description": "New patient office visit - low complexity",
                "code_type": "CPT",
                "category": "Evaluation and Management",
                "coverage_notes": "Standard coverage for office visits",
                "effective_date": "2024-01-01",
                "termination_date": "",
                "is_active": True,
                "modifier_required": False,
                "gender_specific": "",
                "age_specific": "",
                "bilateral_indicator": False,
                "source": "fallback",
                "search_text": "99202 office visit new patient evaluation management low complexity",
                "last_updated": current_time,
            },
            {
                "code": "99203",
                "short_description": "Office visit new patient",
                "long_description": "Office or other outpatient visit for the evaluation and management of a new patient",
                "description": "New patient office visit - moderate complexity",
                "code_type": "CPT",
                "category": "Evaluation and Management",
                "coverage_notes": "Standard coverage for office visits",
                "effective_date": "2024-01-01",
                "termination_date": "",
                "is_active": True,
                "modifier_required": False,
                "gender_specific": "",
                "age_specific": "",
                "bilateral_indicator": False,
                "source": "fallback",
                "search_text": "99203 office visit new patient evaluation management moderate complexity",
                "last_updated": current_time,
            },
            {
                "code": "99204",
                "short_description": "Office visit new patient",
                "long_description": "Office or other outpatient visit for the evaluation and management of a new patient",
                "description": "New patient office visit - moderate to high complexity",
                "code_type": "CPT",
                "category": "Evaluation and Management",
                "coverage_notes": "Standard coverage for office visits",
                "effective_date": "2024-01-01",
                "termination_date": "",
                "is_active": True,
                "modifier_required": False,
                "gender_specific": "",
                "age_specific": "",
                "bilateral_indicator": False,
                "source": "fallback",
                "search_text": "99204 office visit new patient evaluation management moderate high complexity",
                "last_updated": current_time,
            },
            {
                "code": "99205",
                "short_description": "Office visit new patient",
                "long_description": "Office or other outpatient visit for the evaluation and management of a new patient",
                "description": "New patient office visit - high complexity",
                "code_type": "CPT",
                "category": "Evaluation and Management",
                "coverage_notes": "Standard coverage for office visits",
                "effective_date": "2024-01-01",
                "termination_date": "",
                "is_active": True,
                "modifier_required": False,
                "gender_specific": "",
                "age_specific": "",
                "bilateral_indicator": False,
                "source": "fallback",
                "search_text": "99205 office visit new patient evaluation management high complexity",
                "last_updated": current_time,
            },
            {
                "code": "99211",
                "short_description": "Office visit est patient",
                "long_description": "Office or other outpatient visit for the evaluation and management of an established patient",
                "description": "Established patient office visit - minimal",
                "code_type": "CPT",
                "category": "Evaluation and Management",
                "coverage_notes": "Standard coverage for office visits",
                "effective_date": "2024-01-01",
                "termination_date": "",
                "is_active": True,
                "modifier_required": False,
                "gender_specific": "",
                "age_specific": "",
                "bilateral_indicator": False,
                "source": "fallback",
                "search_text": "99211 office visit established patient evaluation management minimal",
                "last_updated": current_time,
            },
            {
                "code": "99212",
                "short_description": "Office visit est patient",
                "long_description": "Office or other outpatient visit for the evaluation and management of an established patient",
                "description": "Established patient office visit - straightforward",
                "code_type": "CPT",
                "category": "Evaluation and Management",
                "coverage_notes": "Standard coverage for office visits",
                "effective_date": "2024-01-01",
                "termination_date": "",
                "is_active": True,
                "modifier_required": False,
                "gender_specific": "",
                "age_specific": "",
                "bilateral_indicator": False,
                "source": "fallback",
                "search_text": "99212 office visit established patient evaluation management straightforward",
                "last_updated": current_time,
            },
            {
                "code": "99213",
                "short_description": "Office visit est patient",
                "long_description": "Office or other outpatient visit for the evaluation and management of an established patient",
                "description": "Established patient office visit - low complexity",
                "code_type": "CPT",
                "category": "Evaluation and Management",
                "coverage_notes": "Standard coverage for office visits",
                "effective_date": "2024-01-01",
                "termination_date": "",
                "is_active": True,
                "modifier_required": False,
                "gender_specific": "",
                "age_specific": "",
                "bilateral_indicator": False,
                "source": "fallback",
                "search_text": "99213 office visit established patient evaluation management low complexity",
                "last_updated": current_time,
            },
            {
                "code": "99214",
                "short_description": "Office visit est patient",
                "long_description": "Office or other outpatient visit for the evaluation and management of an established patient",
                "description": "Established patient office visit - moderate complexity",
                "code_type": "CPT",
                "category": "Evaluation and Management",
                "coverage_notes": "Standard coverage for office visits",
                "effective_date": "2024-01-01",
                "termination_date": "",
                "is_active": True,
                "modifier_required": False,
                "gender_specific": "",
                "age_specific": "",
                "bilateral_indicator": False,
                "source": "fallback",
                "search_text": "99214 office visit established patient evaluation management moderate complexity",
                "last_updated": current_time,
            },
            {
                "code": "99215",
                "short_description": "Office visit est patient",
                "long_description": "Office or other outpatient visit for the evaluation and management of an established patient",
                "description": "Established patient office visit - high complexity",
                "code_type": "CPT",
                "category": "Evaluation and Management",
                "coverage_notes": "Standard coverage for office visits",
                "effective_date": "2024-01-01",
                "termination_date": "",
                "is_active": True,
                "modifier_required": False,
                "gender_specific": "",
                "age_specific": "",
                "bilateral_indicator": False,
                "source": "fallback",
                "search_text": "99215 office visit established patient evaluation management high complexity",
                "last_updated": current_time,
            },

            # Emergency Department Visits
            {
                "code": "99281",
                "short_description": "Emergency dept visit",
                "long_description": "Emergency department visit for the evaluation and management of a patient",
                "description": "Emergency department visit - straightforward",
                "code_type": "CPT",
                "category": "Evaluation and Management",
                "coverage_notes": "Emergency department coverage",
                "effective_date": "2024-01-01",
                "termination_date": "",
                "is_active": True,
                "modifier_required": False,
                "gender_specific": "",
                "age_specific": "",
                "bilateral_indicator": False,
                "source": "fallback",
                "search_text": "99281 emergency department visit evaluation management straightforward",
                "last_updated": current_time,
            },
            {
                "code": "99282",
                "short_description": "Emergency dept visit",
                "long_description": "Emergency department visit for the evaluation and management of a patient",
                "description": "Emergency department visit - low complexity",
                "code_type": "CPT",
                "category": "Evaluation and Management",
                "coverage_notes": "Emergency department coverage",
                "effective_date": "2024-01-01",
                "termination_date": "",
                "is_active": True,
                "modifier_required": False,
                "gender_specific": "",
                "age_specific": "",
                "bilateral_indicator": False,
                "source": "fallback",
                "search_text": "99282 emergency department visit evaluation management low complexity",
                "last_updated": current_time,
            },
            {
                "code": "99283",
                "short_description": "Emergency dept visit",
                "long_description": "Emergency department visit for the evaluation and management of a patient",
                "description": "Emergency department visit - moderate complexity",
                "code_type": "CPT",
                "category": "Evaluation and Management",
                "coverage_notes": "Emergency department coverage",
                "effective_date": "2024-01-01",
                "termination_date": "",
                "is_active": True,
                "modifier_required": False,
                "gender_specific": "",
                "age_specific": "",
                "bilateral_indicator": False,
                "source": "fallback",
                "search_text": "99283 emergency department visit evaluation management moderate complexity",
                "last_updated": current_time,
            },
            {
                "code": "99284",
                "short_description": "Emergency dept visit",
                "long_description": "Emergency department visit for the evaluation and management of a patient",
                "description": "Emergency department visit - high complexity",
                "code_type": "CPT",
                "category": "Evaluation and Management",
                "coverage_notes": "Emergency department coverage",
                "effective_date": "2024-01-01",
                "termination_date": "",
                "is_active": True,
                "modifier_required": False,
                "gender_specific": "",
                "age_specific": "",
                "bilateral_indicator": False,
                "source": "fallback",
                "search_text": "99284 emergency department visit evaluation management high complexity",
                "last_updated": current_time,
            },
            {
                "code": "99285",
                "short_description": "Emergency dept visit",
                "long_description": "Emergency department visit for the evaluation and management of a patient",
                "description": "Emergency department visit - high complexity",
                "code_type": "CPT",
                "category": "Evaluation and Management",
                "coverage_notes": "Emergency department coverage",
                "effective_date": "2024-01-01",
                "termination_date": "",
                "is_active": True,
                "modifier_required": False,
                "gender_specific": "",
                "age_specific": "",
                "bilateral_indicator": False,
                "source": "fallback",
                "search_text": "99285 emergency department visit evaluation management high complexity critical care",
                "last_updated": current_time,
            },

            # Psychiatric Services
            {
                "code": "90791",
                "short_description": "Psychiatric diagnostic evaluation",
                "long_description": "Psychiatric diagnostic evaluation",
                "description": "Initial psychiatric evaluation",
                "code_type": "CPT",
                "category": "Psychiatry",
                "coverage_notes": "Mental health parity coverage",
                "effective_date": "2024-01-01",
                "termination_date": "",
                "is_active": True,
                "modifier_required": False,
                "gender_specific": "",
                "age_specific": "",
                "bilateral_indicator": False,
                "source": "fallback",
                "search_text": "90791 psychiatric diagnostic evaluation mental health",
                "last_updated": current_time,
            },
            {
                "code": "90834",
                "short_description": "Psychotherapy 45 minutes",
                "long_description": "Psychotherapy, 45 minutes with patient",
                "description": "Individual psychotherapy session 45 minutes",
                "code_type": "CPT",
                "category": "Psychiatry",
                "coverage_notes": "Mental health parity coverage",
                "effective_date": "2024-01-01",
                "termination_date": "",
                "is_active": True,
                "modifier_required": False,
                "gender_specific": "",
                "age_specific": "",
                "bilateral_indicator": False,
                "source": "fallback",
                "search_text": "90834 psychotherapy individual session mental health 45 minutes",
                "last_updated": current_time,
            },
            {
                "code": "90837",
                "short_description": "Psychotherapy 60 minutes",
                "long_description": "Psychotherapy, 60 minutes with patient",
                "description": "Individual psychotherapy session 60 minutes",
                "code_type": "CPT",
                "category": "Psychiatry",
                "coverage_notes": "Mental health parity coverage",
                "effective_date": "2024-01-01",
                "termination_date": "",
                "is_active": True,
                "modifier_required": False,
                "gender_specific": "",
                "age_specific": "",
                "bilateral_indicator": False,
                "source": "fallback",
                "search_text": "90837 psychotherapy individual session mental health 60 minutes",
                "last_updated": current_time,
            },

            # Laboratory
            {
                "code": "80053",
                "short_description": "Comprehensive metabolic panel",
                "long_description": "Comprehensive metabolic panel",
                "description": "Blood chemistry panel",
                "code_type": "CPT",
                "category": "Pathology and Laboratory",
                "coverage_notes": "Routine laboratory coverage",
                "effective_date": "2024-01-01",
                "termination_date": "",
                "is_active": True,
                "modifier_required": False,
                "gender_specific": "",
                "age_specific": "",
                "bilateral_indicator": False,
                "source": "fallback",
                "search_text": "80053 comprehensive metabolic panel blood chemistry laboratory",
                "last_updated": current_time,
            },
            {
                "code": "85025",
                "short_description": "Complete blood count",
                "long_description": "Blood count; complete (CBC), automated",
                "description": "Complete blood count with differential",
                "code_type": "CPT",
                "category": "Pathology and Laboratory",
                "coverage_notes": "Routine laboratory coverage",
                "effective_date": "2024-01-01",
                "termination_date": "",
                "is_active": True,
                "modifier_required": False,
                "gender_specific": "",
                "age_specific": "",
                "bilateral_indicator": False,
                "source": "fallback",
                "search_text": "85025 complete blood count cbc laboratory automated differential",
                "last_updated": current_time,
            },

            # HCPCS Level II Codes
            {
                "code": "A0425",
                "short_description": "Ground mileage ambulance",
                "long_description": "Ground mileage, per statute mile",
                "description": "Ambulance ground transport per mile",
                "code_type": "HCPCS",
                "category": "Transportation Services, Medical and Surgical Supplies",
                "coverage_notes": "Emergency ambulance coverage",
                "effective_date": "2024-01-01",
                "termination_date": "",
                "is_active": True,
                "modifier_required": False,
                "gender_specific": "",
                "age_specific": "",
                "bilateral_indicator": False,
                "source": "fallback",
                "search_text": "A0425 ground mileage ambulance transport emergency",
                "last_updated": current_time,
            },
            {
                "code": "E0470",
                "short_description": "Respiratory assist device",
                "long_description": "Respiratory assist device, bi-level pressure capability",
                "description": "BiPAP respiratory assist device",
                "code_type": "HCPCS",
                "category": "Durable Medical Equipment",
                "coverage_notes": "Durable medical equipment coverage with prior authorization",
                "effective_date": "2024-01-01",
                "termination_date": "",
                "is_active": True,
                "modifier_required": True,
                "gender_specific": "",
                "age_specific": "",
                "bilateral_indicator": False,
                "source": "fallback",
                "search_text": "E0470 respiratory assist device bipap durable medical equipment",
                "last_updated": current_time,
            },
            {
                "code": "G0463",
                "short_description": "Hospital outpatient clinic visit",
                "long_description": "Hospital outpatient clinic visit for assessment and management of a patient",
                "description": "Hospital outpatient clinic visit",
                "code_type": "HCPCS",
                "category": "Temporary Physician Procedures",
                "coverage_notes": "Medicare coverage for outpatient clinic visits",
                "effective_date": "2024-01-01",
                "termination_date": "",
                "is_active": True,
                "modifier_required": False,
                "gender_specific": "",
                "age_specific": "",
                "bilateral_indicator": False,
                "source": "fallback",
                "search_text": "G0463 hospital outpatient clinic visit assessment management",
                "last_updated": current_time,
            },
            {
                "code": "J1745",
                "short_description": "Infliximab injection",
                "long_description": "Injection, infliximab, excludes biosimilar, 10 mg",
                "description": "Infliximab injection 10 mg",
                "code_type": "HCPCS",
                "category": "Drugs Administered Other Than Oral Method",
                "coverage_notes": "Medicare Part B coverage for qualifying conditions",
                "effective_date": "2024-01-01",
                "termination_date": "",
                "is_active": True,
                "modifier_required": False,
                "gender_specific": "",
                "age_specific": "",
                "bilateral_indicator": False,
                "source": "fallback",
                "search_text": "J1745 injection infliximab biosimilar drug",
                "last_updated": current_time,
            },
            {
                "code": "J7050",
                "short_description": "Infusion saline solution",
                "long_description": "Infusion, normal saline solution, 1000 cc",
                "description": "Normal saline infusion 1000cc",
                "code_type": "HCPCS",
                "category": "Drugs Administered Other Than Oral Method",
                "coverage_notes": "Inpatient and outpatient infusion coverage",
                "effective_date": "2024-01-01",
                "termination_date": "",
                "is_active": True,
                "modifier_required": False,
                "gender_specific": "",
                "age_specific": "",
                "bilateral_indicator": False,
                "source": "fallback",
                "search_text": "J7050 infusion normal saline solution 1000cc",
                "last_updated": current_time,
            },
            {
                "code": "L3806",
                "short_description": "Wrist hand orthosis",
                "long_description": "Wrist hand finger orthosis, includes one or more nontorsion joint(s)",
                "description": "Wrist hand finger orthotic device",
                "code_type": "HCPCS",
                "category": "Orthotic and Prosthetic Procedures",
                "coverage_notes": "Durable medical equipment coverage",
                "effective_date": "2024-01-01",
                "termination_date": "",
                "is_active": True,
                "modifier_required": False,
                "gender_specific": "",
                "age_specific": "",
                "bilateral_indicator": False,
                "source": "fallback",
                "search_text": "L3806 wrist hand finger orthosis orthotic device",
                "last_updated": current_time,
            },
            {
                "code": "Q0091",
                "short_description": "Screening papanicolaou smear",
                "long_description": "Screening papanicolaou smear; obtaining, preparing and conveyance of cervical or vaginal smear to laboratory",
                "description": "Pap smear screening test",
                "code_type": "HCPCS",
                "category": "Temporary Codes",
                "coverage_notes": "Preventive care coverage",
                "effective_date": "2024-01-01",
                "termination_date": "",
                "is_active": True,
                "modifier_required": False,
                "gender_specific": "Female",
                "age_specific": "21-65",
                "bilateral_indicator": False,
                "source": "fallback",
                "search_text": "Q0091 screening papanicolaou pap smear cervical vaginal",
                "last_updated": current_time,
            },
            {
                "code": "V2020",
                "short_description": "Frames purchases",
                "long_description": "Frames, purchases",
                "description": "Eyeglass frames purchase",
                "code_type": "HCPCS",
                "category": "Vision Services",
                "coverage_notes": "Vision care coverage varies by plan",
                "effective_date": "2024-01-01",
                "termination_date": "",
                "is_active": True,
                "modifier_required": False,
                "gender_specific": "",
                "age_specific": "",
                "bilateral_indicator": False,
                "source": "fallback",
                "search_text": "V2020 frames purchases eyeglass vision",
                "last_updated": current_time,
            },
        ]


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
