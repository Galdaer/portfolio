"""
CMS HCPCS Direct Downloader with rate limit handling and smart retry logic
"""

import asyncio
import csv
import io
import logging
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta
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

    # CMS HCPCS data sources
    CMS_URLS = {
        "hcpcs_current": "https://www.cms.gov/Medicare/Coding/HCPCSReleaseCodeSets/Downloads/2024-HCPCS-Level-II-Code-Set.zip",
        "hcpcs_alpha": "https://www.cms.gov/files/zip/2024-alpha-numeric-hcpcs-file.zip",
        "hcpcs_anweb": "https://www.cms.gov/files/zip/2024-hcpcs-anweb-file.zip",
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
        """Parse fixed-width HCPCS format"""
        codes = []

        for line in lines[1:]:  # Skip header
            line = line.strip()
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

                # Try to parse as fixed positions (common CMS format)
                elif len(line) > 10:
                    code = line[:5].strip()
                    description = line[5:].strip()

                    if code and description:
                        codes.append({
                            "code": code,
                            "short_description": "",
                            "long_description": description,
                            "description": description,
                            "code_type": "HCPCS",
                            "category": "",
                            "source": "cms_direct",
                            "last_updated": datetime.now().isoformat(),
                            "is_active": True,
                        })

            except Exception as e:
                logger.debug(f"Error parsing line: {line} - {e}")
                continue

        return codes

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
