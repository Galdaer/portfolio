"""
ClinicalTrials.gov data downloader
Downloads study data from ClinicalTrials.gov API
"""

import asyncio
import json
import logging
import os
from typing import Any

import httpx

from config import Config

logger = logging.getLogger(__name__)


class ClinicalTrialsDownloader:
    """Downloads ClinicalTrials.gov study data"""

    def __init__(self, config=None) -> None:
        self.config = config or Config()
        self.api_base = self.config.CLINICALTRIALS_API
        self.data_dir = self.config.get_trials_data_dir()
        self.session = httpx.AsyncClient(timeout=30.0)

    async def download_all_studies(self, batch_size: int = 10000) -> list[str]:
        """Download all studies from ClinicalTrials.gov using proper pagination"""
        logger.info("Starting ClinicalTrials.gov full download with pageToken pagination")

        downloaded_files: list[str] = []
        next_page_token = None
        batch_number = 1

        try:
            while True:
                batch_file, next_token = await self.download_studies_batch_paginated(batch_number, batch_size, next_page_token)
                if not batch_file:
                    break

                downloaded_files.append(batch_file)
                next_page_token = next_token
                batch_number += 1

                # Use ClinicalTrials-specific rate limit
                await asyncio.sleep(self.config.CLINICALTRIALS_REQUEST_DELAY)

                logger.info(f"Downloaded batch {batch_number}, next_token: {'Yes' if next_page_token else 'None'}")

                # If no next page token, we're done
                if not next_page_token:
                    break

            logger.info(f"Downloaded {len(downloaded_files)} study batches")
            return downloaded_files

        except Exception as e:
            logger.exception(f"ClinicalTrials download failed: {e}")
            raise

    async def download_studies_batch_paginated(self, batch_number: int, batch_size: int, page_token: str | None = None) -> tuple[str | None, str | None]:
        """Download a consolidated batch of studies using proper pageToken pagination"""
        try:
            all_studies = []
            current_token = page_token
            api_requests_made = 0
            
            # Make multiple API requests to reach desired batch_size (max 1000 per API call)
            while len(all_studies) < batch_size:
                # ClinicalTrials.gov API v2 uses pageSize and pageToken for pagination
                params: dict[str, Any] = {
                    "pageSize": min(1000, batch_size - len(all_studies)),  # Get remaining studies, max 1000 per request
                    "fields": "NCTId,BriefTitle,OverallStatus,Phase,Condition,InterventionName,LocationFacility,LocationCity,LocationState,LocationCountry,StartDate,CompletionDate,EnrollmentCount,StudyType,LeadSponsorName",
                }
                
                # Add page token if we have one
                if current_token:
                    params["pageToken"] = current_token

                response = await self.session.get(self.api_base, params=params)
                response.raise_for_status()
                api_requests_made += 1

                data = response.json()

                # Check if we got any studies
                studies = data.get("studies", [])
                if not studies:
                    logger.info("No more studies available from API")
                    break

                all_studies.extend(studies)
                current_token = data.get("nextPageToken")
                
                # If no next token, we've reached the end
                if not current_token:
                    break
                
                # Small delay between API requests to be respectful
                if api_requests_made > 1:
                    await asyncio.sleep(self.config.CLINICALTRIALS_REQUEST_DELAY)

            if not all_studies:
                logger.info("No studies to save")
                return None, None

            # Create consolidated data structure
            from datetime import datetime
            consolidated_data = {
                "metadata": {
                    "batch_number": batch_number,
                    "total_studies": len(all_studies),
                    "api_requests_made": api_requests_made,
                    "download_timestamp": datetime.now().isoformat(),
                },
                "studies": all_studies,
                "nextPageToken": current_token  # For continuation
            }

            # Save consolidated batch to file with better naming
            batch_file = os.path.join(
                self.data_dir,
                f"studies_consolidated_{batch_number:06d}_{len(all_studies)}.json",
            )

            # Save without pretty printing for efficiency
            with open(batch_file, "w", encoding="utf-8") as f:
                json.dump(consolidated_data, f, ensure_ascii=False, separators=(',', ':'))

            logger.info(f"Consolidated {len(all_studies)} studies into batch {batch_number} using {api_requests_made} API calls (next_token: {'Yes' if current_token else 'None'})")
            return batch_file, current_token

        except Exception as e:
            logger.exception(f"Failed to download consolidated studies batch {batch_number}: {e}")
            return None, None

    async def download_studies_batch(self, start: int, batch_size: int) -> str | None:
        """Legacy method - kept for compatibility but uses new pagination"""
        batch_file, _ = await self.download_studies_batch_paginated(start, batch_size, None)
        return batch_file

    async def download_study_details(self, nct_id: str) -> dict[str, Any] | None:
        """Download detailed information for a specific study"""
        try:
            url = f"{self.api_base}/{nct_id}"
            # API v2 doesn't need fmt=json parameter
            params: dict[str, Any] = {}

            response = await self.session.get(url, params=params)
            response.raise_for_status()

            data: dict[str, Any] = response.json()
            return data

        except Exception as e:
            logger.exception(f"Failed to download study {nct_id}: {e}")
            return None

    async def download_recent_updates(self, days: int = 7) -> list[str]:
        """Download recently updated studies"""
        logger.info("Downloading recent studies (API v2 doesn't support date filtering)")

        try:
            # API v2 doesn't support date filtering, so get recent studies without filter
            from datetime import datetime

            end_date = datetime.now()

            params: dict[str, Any] = {
                "pageSize": 100,  # Smaller page size since no date filtering
                "fields": "NCTId,BriefTitle,OverallStatus,Phase,Condition,InterventionName,LocationFacility,LocationCity,LocationState,LocationCountry,StartDate,CompletionDate,EnrollmentCount,StudyType,LeadSponsorName",
            }

            response = await self.session.get(self.api_base, params=params)
            response.raise_for_status()

            data = response.json()
            studies = data.get("studies", [])

            if studies:
                # Save updates to file
                update_file = os.path.join(
                    self.data_dir,
                    f"updates_{end_date.strftime('%Y%m%d')}.json",
                )

                with open(update_file, "w") as f:
                    json.dump(data, f)

                logger.info(f"Downloaded {len(studies)} updated studies")
                return [update_file]
            logger.info("No updated studies found")
            return []

        except Exception as e:
            logger.exception(f"Failed to download recent updates: {e}")
            raise

    async def get_available_files(self) -> list[str]:
        """Get list of downloaded JSON files ready for parsing"""
        json_files: list[str] = []

        for file in os.listdir(self.data_dir):
            if file.endswith(".json"):
                json_files.append(os.path.join(self.data_dir, file))

        return json_files

    async def close(self) -> None:
        """Close HTTP session"""
        await self.session.aclose()
