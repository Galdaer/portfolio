"""
ClinicalTrials.gov data downloader
Downloads study data from ClinicalTrials.gov API
"""

import asyncio
import json
import logging
import os

import httpx

from config import Config

logger = logging.getLogger(__name__)


class ClinicalTrialsDownloader:
    """Downloads ClinicalTrials.gov study data"""

    def __init__(self):
        self.config = Config()
        self.api_base = self.config.CLINICALTRIALS_API
        self.data_dir = self.config.get_trials_data_dir()
        self.session = httpx.AsyncClient(timeout=30.0)

    async def download_all_studies(self, batch_size: int = 1000) -> list[str]:
        """Download all studies from ClinicalTrials.gov"""
        logger.info("Starting ClinicalTrials.gov full download")

        downloaded_files = []
        start = 1

        try:
            while True:
                batch_file = await self.download_studies_batch(start, batch_size)
                if not batch_file:
                    break

                downloaded_files.append(batch_file)
                start += batch_size

                # Small delay to be respectful
                await asyncio.sleep(self.config.REQUEST_DELAY)

                logger.info(f"Downloaded batch starting at {start}")

            logger.info(f"Downloaded {len(downloaded_files)} study batches")
            return downloaded_files

        except Exception as e:
            logger.error(f"ClinicalTrials download failed: {e}")
            raise

    async def download_studies_batch(self, start: int, batch_size: int) -> str | None:
        """Download a batch of studies"""
        try:
            params = {
                "fmt": "json",
                "min_rnk": start,
                "max_rnk": start + batch_size - 1,
                "fields": "NCTId,BriefTitle,OverallStatus,Phase,Condition,InterventionName,LocationFacility,LocationCity,LocationState,LocationCountry,StartDate,CompletionDate,EnrollmentCount,StudyType,LeadSponsorName",
            }

            response = await self.session.get(self.api_base, params=params)
            response.raise_for_status()

            data = response.json()

            # Check if we got any studies
            studies = data.get("studies", [])
            if not studies:
                logger.info("No more studies to download")
                return None

            # Save batch to file
            batch_file = os.path.join(
                self.data_dir, f"studies_batch_{start}_{start + len(studies) - 1}.json"
            )

            with open(batch_file, "w") as f:
                json.dump(data, f, indent=2)

            logger.info(f"Saved {len(studies)} studies to {batch_file}")
            return batch_file

        except Exception as e:
            logger.error(f"Failed to download studies batch {start}: {e}")
            return None

    async def download_study_details(self, nct_id: str) -> dict | None:
        """Download detailed information for a specific study"""
        try:
            url = f"{self.api_base}/{nct_id}"
            # API v2 doesn't need fmt=json parameter
            params = {}

            response = await self.session.get(url, params=params)
            response.raise_for_status()

            return response.json()

        except Exception as e:
            logger.error(f"Failed to download study {nct_id}: {e}")
            return None

    async def download_recent_updates(self, days: int = 7) -> list[str]:
        """Download recently updated studies"""
        logger.info("Downloading recent studies (API v2 doesn't support date filtering)")

        try:
            # API v2 doesn't support date filtering, so get recent studies without filter
            from datetime import datetime

            end_date = datetime.now()

            params = {
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
                    json.dump(data, f, indent=2)

                logger.info(f"Downloaded {len(studies)} updated studies")
                return [update_file]
            else:
                logger.info("No updated studies found")
                return []

        except Exception as e:
            logger.error(f"Failed to download recent updates: {e}")
            raise

    async def get_available_files(self) -> list[str]:
        """Get list of downloaded JSON files ready for parsing"""
        json_files = []

        for file in os.listdir(self.data_dir):
            if file.endswith(".json"):
                json_files.append(os.path.join(self.data_dir, file))

        return json_files

    async def close(self):
        """Close HTTP session"""
        await self.session.aclose()
