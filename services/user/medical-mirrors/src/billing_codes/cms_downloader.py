"""
CMS HCPCS Direct Downloader with rate limit handling and smart retry logic
"""

import asyncio
import csv
import io
import logging
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Any

import aiohttp

from .download_state_manager import DownloadStateManager, DownloadStatus

logger = logging.getLogger(__name__)


@dataclass
class RateLimitInfo:
    """Rate limiting information"""
    is_limited: bool = False
    reset_time: datetime | None = None
    retry_after: int | None = None
    remaining_requests: int | None = None
    limit: int | None = None


class CMSHCPCSDownloader:
    """Downloads HCPCS Level II codes directly from CMS"""

    # CMS HCPCS data sources (updated to October 2025)
    CMS_URLS = {
        "hcpcs_current": "https://www.cms.gov/files/zip/october-2025-alpha-numeric-hcpcs-file.zip",
        "hcpcs_alpha": "https://www.cms.gov/files/zip/october-2025-alpha-numeric-hcpcs-file.zip",
        "hcpcs_anweb": "https://www.cms.gov/files/zip/october-2025-alpha-numeric-hcpcs-file.zip",
    }

    def __init__(self, state_manager: DownloadStateManager | None = None,
                 output_dir: Path | None = None):
        self.state_manager = state_manager or DownloadStateManager()
        self.output_dir = output_dir or Path("/home/intelluxe/database/medical_complete/billing")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Rate limiting configuration
        self.max_retries = 5
        self.base_delay = 5  # Base delay in seconds
        self.max_delay = 3600  # Max delay (1 hour)
        self.request_timeout = 300  # 5 minutes

        # Session for connection reuse
        self.session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.request_timeout),
            headers={"User-Agent": "Intelluxe-Medical-Mirrors/1.0 (Healthcare AI System)"},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    def _parse_rate_limit_headers(self, headers: dict[str, str]) -> RateLimitInfo:
        """Parse rate limiting information from response headers"""
        rate_limit = RateLimitInfo()

        # Check for various rate limit header formats
        if "Retry-After" in headers:
            rate_limit.is_limited = True
            retry_after = headers["Retry-After"]

            # Retry-After can be seconds or HTTP date
            if retry_after.isdigit():
                rate_limit.retry_after = int(retry_after)
                rate_limit.reset_time = datetime.now() + timedelta(seconds=int(retry_after))
            else:
                try:
                    # Parse HTTP date format
                    reset_time = datetime.strptime(retry_after, "%a, %d %b %Y %H:%M:%S GMT")
                    rate_limit.reset_time = reset_time
                    rate_limit.retry_after = int((reset_time - datetime.now()).total_seconds())
                except ValueError:
                    # Default fallback
                    rate_limit.retry_after = 300  # 5 minutes

        # Check for X-RateLimit headers
        if "X-RateLimit-Remaining" in headers:
            rate_limit.remaining_requests = int(headers["X-RateLimit-Remaining"])
            if rate_limit.remaining_requests <= 0:
                rate_limit.is_limited = True

        if "X-RateLimit-Reset" in headers:
            reset_timestamp = int(headers["X-RateLimit-Reset"])
            rate_limit.reset_time = datetime.fromtimestamp(reset_timestamp)

        if "X-RateLimit-Limit" in headers:
            rate_limit.limit = int(headers["X-RateLimit-Limit"])

        return rate_limit

    async def _download_with_retry(self, url: str, source: str) -> bytes | None:
        """Download with intelligent retry logic"""
        state = self.state_manager.get_state(source)
        if not state:
            state = self.state_manager.create_state(source)

        for attempt in range(self.max_retries):
            try:
                logger.info(f"Downloading {source} from {url} (attempt {attempt + 1}/{self.max_retries})")

                # Update state
                self.state_manager.update_state(source, status=DownloadStatus.IN_PROGRESS)

                async with self.session.get(url) as response:
                    # Check for rate limiting
                    rate_limit = self._parse_rate_limit_headers(dict(response.headers))

                    if response.status == 429 or rate_limit.is_limited:
                        # Rate limited
                        retry_after = rate_limit.retry_after or (60 * (2 ** attempt))
                        logger.warning(f"Rate limited for {source}, retrying after {retry_after} seconds")

                        reset_time = rate_limit.reset_time or datetime.now() + timedelta(seconds=retry_after)
                        self.state_manager.mark_rate_limited(source, reset_time, retry_after)

                        await asyncio.sleep(min(retry_after, self.max_delay))
                        continue

                    if response.status == 404:
                        logger.error(f"Resource not found for {source}: {url}")
                        self.state_manager.mark_failed(source, f"404 Not Found: {url}")
                        return None

                    if response.status >= 400:
                        error_msg = f"HTTP {response.status} error for {source}"
                        logger.error(error_msg)

                        # Exponential backoff for server errors
                        if response.status >= 500:
                            delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                            logger.info(f"Server error, retrying after {delay} seconds")
                            await asyncio.sleep(delay)
                            continue
                        self.state_manager.mark_failed(source, error_msg)
                        return None

                    # Success - download content
                    content = await response.read()
                    logger.info(f"Successfully downloaded {len(content)} bytes for {source}")
                    return content

            except TimeoutError:
                logger.warning(f"Timeout downloading {source} (attempt {attempt + 1})")
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    await asyncio.sleep(delay)
                    continue
                self.state_manager.mark_failed(source, "Download timeout")

            except Exception as e:
                logger.exception(f"Error downloading {source}: {e}")
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    await asyncio.sleep(delay)
                    continue
                self.state_manager.mark_failed(source, str(e))

        return None

    def _parse_hcpcs_zip(self, zip_content: bytes, source: str) -> list[dict[str, Any]]:
        """Parse HCPCS codes from CMS ZIP file"""
        codes = []

        try:
            with zipfile.ZipFile(io.BytesIO(zip_content)) as zf:
                # Look for text/csv files in the zip
                for filename in zf.namelist():
                    if filename.lower().endswith((".txt", ".csv")):
                        logger.info(f"Processing {filename} from {source}")

                        with zf.open(filename) as f:
                            # Try to decode as various encodings
                            content = None
                            for encoding in ["utf-8", "cp1252", "latin-1"]:
                                try:
                                    content = f.read().decode(encoding)
                                    break
                                except UnicodeDecodeError:
                                    continue

                            if not content:
                                logger.error(f"Could not decode {filename}")
                                continue

                            # Parse content based on format
                            parsed_codes = self._parse_hcpcs_content(content, filename)
                            codes.extend(parsed_codes)

                            # Update progress
                            self.state_manager.mark_progress(
                                source,
                                completed_items=len(codes),
                                current_file=filename,
                            )

        except zipfile.BadZipFile:
            logger.exception(f"Invalid ZIP file for {source}")
        except Exception as e:
            logger.exception(f"Error parsing ZIP file for {source}: {e}")

        return codes

    def _parse_hcpcs_content(self, content: str, filename: str) -> list[dict[str, Any]]:
        """Parse HCPCS content from text/CSV"""
        codes = []
        lines = content.strip().split("\n")

        try:
            # Try to detect format
            if "," in lines[0] or "\t" in lines[0]:
                # CSV/TSV format
                delimiter = "," if "," in lines[0] else "\t"
                reader = csv.DictReader(lines, delimiter=delimiter)

                for row in reader:
                    code_dict = self._extract_hcpcs_fields(row)
                    if code_dict:
                        codes.append(code_dict)

            else:
                # Fixed-width or pipe-delimited format
                codes = self._parse_fixed_width_hcpcs(lines)

        except Exception as e:
            logger.exception(f"Error parsing content from {filename}: {e}")

        logger.info(f"Parsed {len(codes)} codes from {filename}")
        return codes

    def _extract_hcpcs_fields(self, row: dict[str, str]) -> dict[str, Any] | None:
        """Extract HCPCS fields from CSV row"""
        try:
            # Map common field names

            # Extract code
            code = None
            for field in ["HCPC", "HCPCS", "CODE", "code"]:
                if field in row and row[field]:
                    code = row[field].strip()
                    break

            if not code:
                return None

            # Extract descriptions
            long_desc = None
            short_desc = None

            for field in ["LONG_DESC", "LONG_DESCRIPTION", "DESCRIPTION", "long_description"]:
                if field in row and row[field]:
                    long_desc = row[field].strip()
                    break

            for field in ["SHORT_DESC", "SHORT_DESCRIPTION", "SHORT", "short_description"]:
                if field in row and row[field]:
                    short_desc = row[field].strip()
                    break

            # Use long description as primary, fallback to short
            description = long_desc or short_desc
            if not description:
                return None

            # Extract category
            category = ""
            for field in ["CATEGORY", "CAT", "category"]:
                if field in row and row[field]:
                    category = row[field].strip()
                    break

            return {
                "code": code,
                "short_description": short_desc or "",
                "long_description": long_desc or "",
                "description": description,
                "code_type": "HCPCS",
                "category": category,
                "source": "cms_direct",
                "last_updated": datetime.now().isoformat(),
                "is_active": True,
                "effective_date": None,
                "termination_date": None,
            }

        except Exception as e:
            logger.exception(f"Error extracting HCPCS fields: {e}")
            return None

    def _parse_fixed_width_hcpcs(self, lines: list[str]) -> list[dict[str, Any]]:
        """Parse fixed-width HCPCS format with proper CMS structure and multi-line handling"""
        codes = []
        current_record = None
        continuation_buffer = {}

        for line in lines[1:]:  # Skip header
            line_original = line
            line = line.rstrip()  # Keep trailing spaces for field extraction
            if not line or line.startswith("#"):
                continue

            try:
                # Common fixed-width format: CODE|DESCRIPTION|CATEGORY
                if "|" in line:
                    parts = line.split("|")
                    if len(parts) >= 2:
                        code = parts[0].strip()
                        description = parts[1].strip()
                        category = parts[2].strip() if len(parts) > 2 else ""

                        if code and description:
                            codes.append({
                                "code": code,
                                "short_description": "",
                                "long_description": description,
                                "description": description,
                                "code_type": "HCPCS",
                                "category": category,
                                "source": "cms_direct",
                                "last_updated": datetime.now().isoformat(),
                                "is_active": True,
                            })

                # Parse CMS fixed-width format based on official record layout
                elif len(line) >= 280:  # Must be at least 280 chars to include dates
                    # Parse based on CMS HCPCS record layout document
                    # Fields are 1-indexed in documentation, convert to 0-indexed for Python
                    
                    if line.startswith("   "):  # Format 1: 3 leading spaces
                        # HCPCS code: positions 4-8 (3-7 in 0-indexed)
                        # Sequence: positions 9-13 (8-12 in 0-indexed)
                        # Record ID: position 14 (13 in 0-indexed)
                        # Long desc: positions 15-94 (14-93 in 0-indexed)
                        # Short desc: positions 95-122 (94-121 in 0-indexed)
                        code = line[3:8].strip()
                        sequence = line[8:13].strip()
                        record_id = line[13:14]
                        long_desc = line[14:94].strip()
                        short_desc = line[94:122].strip()
                        
                        # Extract additional fields for format 1
                        pricing_indicator = line[119:121].strip() if len(line) > 120 else ""
                        multi_pricing_ind = line[127:128].strip() if len(line) > 127 else ""
                        coverage_code = line[229:230].strip() if len(line) > 229 else ""
                        betos_code = line[256:259].strip() if len(line) > 258 else ""
                        type_of_service = line[260:261].strip() if len(line) > 260 else ""
                        anesthesia_units = line[265:268].strip() if len(line) > 267 else ""
                        code_added_date_str = line[268:276].strip() if len(line) > 275 else ""
                        effective_date_str = line[276:284] if len(line) > 283 else ""
                        termination_date_str = line[284:292] if len(line) > 291 else ""
                        action_code = line[292:293] if len(line) > 292 else ""
                        
                    else:  # Format 2: No leading spaces
                        # HCPCS code: positions 1-5 (0-4 in 0-indexed)
                        # Sequence: positions 6-10 (5-9 in 0-indexed)
                        # Record ID: position 11 (10 in 0-indexed)
                        # Long desc: positions 12-91 (11-90 in 0-indexed)
                        # Short desc: positions 92-119 (91-118 in 0-indexed)
                        code = line[0:5].strip()
                        sequence = line[5:10].strip()
                        record_id = line[10:11]
                        long_desc = line[11:91].strip()
                        short_desc = line[91:119].strip()
                        
                        # Extract additional fields for format 2 
                        pricing_indicator = line[119:121].strip() if len(line) > 120 else ""
                        multi_pricing_ind = line[127:128].strip() if len(line) > 127 else ""
                        coverage_code = line[229:230].strip() if len(line) > 229 else ""
                        betos_code = line[256:259].strip() if len(line) > 258 else ""
                        type_of_service = line[260:261].strip() if len(line) > 260 else ""
                        anesthesia_units = line[265:268].strip() if len(line) > 267 else ""
                        code_added_date_str = line[268:276].strip() if len(line) > 275 else ""
                        effective_date_str = line[276:284] if len(line) > 283 else ""
                        termination_date_str = line[284:292] if len(line) > 291 else ""
                        action_code = line[292:293] if len(line) > 292 else ""
                    
                    # Parse dates
                    effective_date = self._parse_cms_date(effective_date_str)
                    termination_date = self._parse_cms_date(termination_date_str)
                    code_added_date = self._parse_cms_date(code_added_date_str)
                    
                    # Process coded fields
                    coverage_notes = self._get_coverage_description(coverage_code)
                    
                    # Build category from BETOS + Type of Service
                    category_parts = []
                    if betos_code:
                        category_parts.append(f"BETOS:{betos_code}")
                    if type_of_service:
                        category_parts.append(f"TOS:{type_of_service}")
                    category = "; ".join(category_parts)
                    
                    # Determine if code is active (no termination date or future termination)
                    is_active = not termination_date or termination_date > datetime.now().date()
                    
                    if code:
                        # Handle multi-line records with continuation sequences
                        if sequence.endswith('00'):  # Main record
                            # If we have a continuation buffer for this code, merge it
                            if code in continuation_buffer:
                                buffered = continuation_buffer.pop(code)
                                long_desc = (long_desc + " " + buffered['long_desc']).strip()
                                short_desc = short_desc or buffered['short_desc']
                            
                            if long_desc or short_desc:
                                # Use long description as primary, fallback to short
                                description = long_desc if long_desc else short_desc
                                
                                codes.append({
                                    "code": code,
                                    "short_description": short_desc if short_desc else "",
                                    "long_description": long_desc if long_desc else "",
                                    "description": description,
                                    "code_type": "HCPCS",
                                    "category": category,
                                    "coverage_notes": coverage_notes,
                                    "source": "cms_direct",
                                    "last_updated": datetime.now().isoformat(),
                                    "is_active": is_active,
                                    "effective_date": effective_date.isoformat() if effective_date else None,
                                    "termination_date": termination_date.isoformat() if termination_date else None,
                                    "code_added_date": code_added_date.isoformat() if code_added_date else None,
                                    "record_id": record_id,
                                    "sequence": sequence,
                                    "action_code": action_code,
                                    "coverage_code": coverage_code,
                                    "betos_code": betos_code,
                                    "type_of_service": type_of_service,
                                    "pricing_indicator": pricing_indicator,
                                    "anesthesia_units": anesthesia_units,
                                })
                        
                        else:  # Continuation record
                            # Buffer continuation records to merge with main record
                            if code not in continuation_buffer:
                                continuation_buffer[code] = {'long_desc': '', 'short_desc': ''}
                            
                            if long_desc:
                                continuation_buffer[code]['long_desc'] = (
                                    continuation_buffer[code]['long_desc'] + " " + long_desc
                                ).strip()
                            
                            if short_desc and not continuation_buffer[code]['short_desc']:
                                continuation_buffer[code]['short_desc'] = short_desc

            except Exception as e:
                logger.debug(f"Error parsing line: {line} - {e}")
                continue

        return codes
    
    def _parse_cms_date(self, date_str: str) -> date | None:
        """Parse CMS date format (YYYYMMDD) to date object"""
        if not date_str or not date_str.strip() or date_str.strip() == "":
            return None
        
        try:
            # CMS dates are in YYYYMMDD format
            date_str = date_str.strip()
            if len(date_str) == 8 and date_str.isdigit():
                year = int(date_str[:4])
                month = int(date_str[4:6])
                day = int(date_str[6:8])
                return date(year, month, day)
        except (ValueError, IndexError):
            logger.debug(f"Could not parse date: {date_str}")
        
        return None

    # CMS code mappings
    COVERAGE_CODE_MAPPINGS = {
        'C': 'Carrier judgment - Coverage decision left to local Medicare contractors',
        'D': 'Special coverage instructions apply - See Medicare manual for specific requirements',
        'I': 'Not payable by Medicare - Item or service not covered',
        'M': 'Non-covered by Medicare - Statutory non-coverage',
        'S': 'Non-covered by Medicare statute - Excluded by Medicare law',
        '': 'No coverage determination available'
    }
    
    ACTION_CODE_MAPPINGS = {
        'N': 'New code - Added to HCPCS',
        'R': 'Reinstated code - Previously deleted code restored',
        'D': 'Deleted code - Removed from HCPCS', 
        'C': 'Changed code - Modified description or coverage',
        '': 'No action specified'
    }

    def _get_coverage_description(self, coverage_code: str) -> str:
        """Get full description for coverage code"""
        return self.COVERAGE_CODE_MAPPINGS.get(coverage_code.strip(), 
                                               f'Unknown coverage code: {coverage_code}')

    async def download_all_hcpcs(self) -> dict[str, list[dict[str, Any]]]:
        """Download all HCPCS codes from CMS sources"""
        logger.info("Starting CMS HCPCS download process")
        all_codes = {}

        for source, url in self.CMS_URLS.items():
            logger.info(f"Processing source: {source}")

            # Check if source is already completed
            state = self.state_manager.get_state(source)
            if state and state.status == DownloadStatus.COMPLETED:
                logger.info(f"Source {source} already completed, skipping")
                continue

            # Check if source is rate limited and not ready
            if (state and state.status == DownloadStatus.RATE_LIMITED and
                state.next_retry):
                try:
                    retry_time = datetime.fromisoformat(state.next_retry)
                    if datetime.now() < retry_time:
                        logger.info(f"Source {source} rate limited until {state.next_retry}, skipping")
                        continue
                except Exception:
                    pass

            # Download the content
            content = await self._download_with_retry(url, source)
            if not content:
                logger.error(f"Failed to download {source}")
                continue

            # Parse the content
            codes = self._parse_hcpcs_zip(content, source)
            if codes:
                all_codes[source] = codes
                self.state_manager.mark_completed(source, len(codes))
                logger.info(f"Successfully processed {len(codes)} codes from {source}")

                # Save intermediate results
                output_file = self.output_dir / f"{source}_codes.json"
                await self._save_codes_to_file(codes, output_file)
            else:
                self.state_manager.mark_failed(source, "No codes extracted from download")

        return all_codes

    async def _save_codes_to_file(self, codes: list[dict[str, Any]], output_file: Path):
        """Save codes to JSON file"""
        try:
            import json
            with open(output_file, "w") as f:
                json.dump(codes, f, indent=2, default=str)
            logger.info(f"Saved {len(codes)} codes to {output_file}")
        except Exception as e:
            logger.exception(f"Error saving codes to {output_file}: {e}")

    def get_download_progress(self) -> dict[str, Any]:
        """Get current download progress"""
        return self.state_manager.get_progress_summary()


async def main():
    """Test the CMS HCPCS downloader"""
    logging.basicConfig(level=logging.INFO)

    async with CMSHCPCSDownloader() as downloader:
        # Download all HCPCS codes
        all_codes = await downloader.download_all_hcpcs()

        total_codes = sum(len(codes) for codes in all_codes.values())
        print(f"Downloaded {total_codes} total HCPCS codes from {len(all_codes)} sources")

        # Show progress
        progress = downloader.get_download_progress()
        print(f"Download progress: {progress}")


if __name__ == "__main__":
    asyncio.run(main())
