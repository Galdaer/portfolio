#!/usr/bin/env python3
"""
Complete ClinicalTrials.gov Archive Downloader
Downloads all clinical trials (~450,000 studies) for offline database operation

Uses the same configuration and patterns as the medical-mirrors service
for consistency with the existing database schema and architecture.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx

# Type checking imports  
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from medical_mirrors_types import Config
else:
    # Runtime imports - add medical-mirrors to Python path
    medical_mirrors_src = str(Path(__file__).parent.parent / "services/user/medical-mirrors/src")
    if medical_mirrors_src not in sys.path:
        sys.path.insert(0, medical_mirrors_src)

    try:
        from config import Config
    except ImportError as e:
        print(f"Failed to import medical-mirrors modules: {e}")
        print(f"Make sure medical-mirrors service is properly installed")
        print(f"Looking for modules in: {medical_mirrors_src}")
        sys.exit(1)


class CompleteClinicalTrialsDownloader:
    """
    Downloads complete ClinicalTrials.gov archive for local database caching.
    
    Based on the existing medical-mirrors ClinicalTrialsDownloader but enhanced
    for complete archive downloads instead of incremental updates.
    """

    def __init__(self, custom_data_dir: str | None = None):
        # Use medical-mirrors Config for consistency
        self.config = Config()
        self.api_base = self.config.CLINICALTRIALS_API  # https://clinicaltrials.gov/api/v2/studies
        
        # Allow custom data directory override
        if custom_data_dir:
            self.data_dir = custom_data_dir
            os.makedirs(self.data_dir, exist_ok=True)
        else:
            self.data_dir = self.config.get_trials_data_dir()
            
        self.logger = self._setup_logging()
        
        # HTTP session with timeout consistent with medical-mirrors
        self.session = httpx.AsyncClient(timeout=30.0)
        
        # Download statistics
        self.stats = {
            "studies_downloaded": 0,
            "batch_files_created": 0,
            "total_api_calls": 0,
            "start_time": None,
            "end_time": None,
            "errors": []
        }

    def _setup_logging(self) -> logging.Logger:
        """Setup comprehensive download logging"""
        logger = logging.getLogger("complete_clinicaltrials_downloader")
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    async def download_complete_archive(self) -> dict[str, Any]:
        """Download all ClinicalTrials.gov studies"""
        self.logger.info("Starting complete ClinicalTrials.gov archive download")
        self.logger.info("Target: ~450,000 studies (~500MB total)")
        self.stats["start_time"] = time.time()

        try:
            # Download all studies using API pagination
            all_studies = await self.download_all_studies()
            
            # Save complete dataset to single file for easier processing
            complete_file = await self.save_complete_dataset(all_studies)
            
            self.stats["end_time"] = time.time()
            duration = self.stats["end_time"] - self.stats["start_time"]
            
            self.logger.info(f"✅ Complete ClinicalTrials download finished!")
            self.logger.info(f"   Studies downloaded: {len(all_studies)}")
            self.logger.info(f"   API calls made: {self.stats['total_api_calls']}")
            self.logger.info(f"   Duration: {duration/60:.1f} minutes")
            self.logger.info(f"   Complete dataset: {complete_file}")
            
            return {
                "status": "success",
                "studies_downloaded": len(all_studies),
                "api_calls": self.stats["total_api_calls"],
                "duration_minutes": duration / 60,
                "complete_file": complete_file,
                "errors": self.stats["errors"]
            }

        except Exception as e:
            self.logger.exception(f"Complete ClinicalTrials download failed: {e}")
            self.stats["errors"].append(str(e))
            return {
                "status": "failed",
                "error": str(e),
                "partial_stats": self.stats
            }

    async def download_all_studies(self) -> list[dict]:
        """Download all studies from ClinicalTrials.gov API v2"""
        self.logger.info("Downloading all ClinicalTrials.gov studies")
        
        all_studies = []
        page_size = 1000  # Maximum allowed by API
        next_page_token = None
        
        # Fields matching the medical-mirrors ClinicalTrial schema
        fields = [
            "NCTId", "BriefTitle", "OverallStatus", "Phase", 
            "Condition", "InterventionName", "LocationFacility", 
            "LocationCity", "LocationState", "LocationCountry",
            "StartDate", "CompletionDate", "EnrollmentCount", 
            "StudyType", "LeadSponsorName"
        ]
        
        while True:
            try:
                self.logger.info(f"Downloading studies batch (total so far: {len(all_studies)})")
                
                # Prepare API parameters (consistent with medical-mirrors patterns)
                params = {
                    "pageSize": page_size,
                    "fields": ",".join(fields),
                    "format": "json"
                }
                
                # Add pagination token if available
                if next_page_token:
                    params["pageToken"] = next_page_token
                
                # Make API request
                self.stats["total_api_calls"] += 1
                response = await self.session.get(self.api_base, params=params)
                response.raise_for_status()
                
                data = response.json()
                studies = data.get("studies", [])
                
                if not studies:
                    self.logger.info("No more studies to download")
                    break
                
                # Process and normalize studies for medical-mirrors schema compatibility
                normalized_studies = []
                for study in studies:
                    normalized_study = self._normalize_study_data(study)
                    normalized_studies.append(normalized_study)
                
                all_studies.extend(normalized_studies)
                self.stats["studies_downloaded"] = len(all_studies)
                
                self.logger.info(f"Downloaded {len(studies)} studies in this batch")
                
                # Check for next page
                next_page_token = data.get("nextPageToken")
                if not next_page_token:
                    self.logger.info("Reached end of data - no more pages")
                    break
                
                # Rate limiting to be respectful to API
                await asyncio.sleep(self.config.REQUEST_DELAY)
                
            except Exception as e:
                self.logger.error(f"Error downloading studies batch: {e}")
                self.stats["errors"].append(f"Batch download: {e}")
                # Continue with next batch on error
                break
        
        self.logger.info(f"Downloaded {len(all_studies)} total studies")
        return all_studies

    def _normalize_study_data(self, study: dict) -> dict:
        """
        Normalize study data to match medical-mirrors ClinicalTrial schema.
        
        Maps API v2 response fields to database column constraints:
        - nct_id: VARCHAR(20) PRIMARY KEY
        - title: TEXT
        - status: VARCHAR(100) 
        - phase: VARCHAR(100)
        - conditions: ARRAY(String)
        - interventions: ARRAY(String)
        - locations: ARRAY(String)
        - sponsors: ARRAY(String)
        - start_date: VARCHAR(20)
        - completion_date: VARCHAR(20)
        - enrollment: INTEGER
        - study_type: VARCHAR(100)
        """
        
        # Extract and validate NCT ID (required primary key)
        nct_id = study.get("protocolSection", {}).get("identificationModule", {}).get("nctId", "")
        if not nct_id:
            nct_id = study.get("nctId", "")  # fallback
        
        # Extract title
        title = study.get("protocolSection", {}).get("identificationModule", {}).get("briefTitle", "")
        if not title:
            title = study.get("briefTitle", "")  # fallback
        
        # Extract status (VARCHAR 100 constraint)
        status = study.get("protocolSection", {}).get("statusModule", {}).get("overallStatus", "")
        if not status:
            status = study.get("overallStatus", "")
        status = str(status)[:100] if status else ""  # Enforce length limit
        
        # Extract phase (VARCHAR 100 constraint) 
        phase_info = study.get("protocolSection", {}).get("designModule", {}).get("phases", [])
        if isinstance(phase_info, list) and phase_info:
            phase = ", ".join(phase_info)
        else:
            phase = study.get("phase", "")
        phase = str(phase)[:100] if phase else ""  # Enforce length limit
        
        # Extract conditions as array
        conditions_list = []
        conditions_module = study.get("protocolSection", {}).get("conditionsModule", {})
        if "conditions" in conditions_module:
            conditions_list = conditions_module["conditions"]
        elif "condition" in study:
            # Fallback to flatter structure
            if isinstance(study["condition"], list):
                conditions_list = study["condition"]
            else:
                conditions_list = [study["condition"]]
        
        # Extract interventions as array
        interventions_list = []
        interventions_module = study.get("protocolSection", {}).get("armsInterventionsModule", {})
        if "interventions" in interventions_module:
            for intervention in interventions_module["interventions"]:
                if "name" in intervention:
                    interventions_list.append(intervention["name"])
        elif "interventionName" in study:
            # Fallback to flatter structure
            if isinstance(study["interventionName"], list):
                interventions_list = study["interventionName"]
            else:
                interventions_list = [study["interventionName"]]
        
        # Extract locations as array
        locations_list = []
        contacts_locations = study.get("protocolSection", {}).get("contactsLocationsModule", {})
        if "locations" in contacts_locations:
            for location in contacts_locations["locations"]:
                facility = location.get("facility", "")
                city = location.get("city", "")
                state = location.get("state", "")
                country = location.get("country", "")
                location_str = f"{facility}, {city}, {state}, {country}".strip(", ")
                if location_str:
                    locations_list.append(location_str)
        
        # Extract sponsors as array
        sponsors_list = []
        sponsor_info = study.get("protocolSection", {}).get("sponsorCollaboratorsModule", {})
        if "leadSponsor" in sponsor_info:
            lead_sponsor = sponsor_info["leadSponsor"].get("name", "")
            if lead_sponsor:
                sponsors_list.append(lead_sponsor)
        elif "leadSponsorName" in study:
            sponsors_list.append(study["leadSponsorName"])
        
        # Extract dates (VARCHAR 20 constraint)
        start_date = study.get("protocolSection", {}).get("statusModule", {}).get("startDateStruct", {}).get("date", "")
        if not start_date:
            start_date = study.get("startDate", "")
        start_date = str(start_date)[:20] if start_date else ""
        
        completion_date = study.get("protocolSection", {}).get("statusModule", {}).get("completionDateStruct", {}).get("date", "")  
        if not completion_date:
            completion_date = study.get("completionDate", "")
        completion_date = str(completion_date)[:20] if completion_date else ""
        
        # Extract enrollment (INTEGER)
        enrollment = None
        enrollment_info = study.get("protocolSection", {}).get("designModule", {}).get("enrollmentInfo", {})
        if "count" in enrollment_info:
            try:
                enrollment = int(enrollment_info["count"])
            except (ValueError, TypeError):
                enrollment = None
        elif "enrollmentCount" in study:
            try:
                enrollment = int(study["enrollmentCount"])
            except (ValueError, TypeError):
                enrollment = None
        
        # Extract study type (VARCHAR 100 constraint)
        study_type = study.get("protocolSection", {}).get("designModule", {}).get("studyType", "")
        if not study_type:
            study_type = study.get("studyType", "")
        study_type = str(study_type)[:100] if study_type else ""
        
        return {
            "nct_id": nct_id,
            "title": title,
            "status": status,
            "phase": phase,
            "conditions": conditions_list,
            "interventions": interventions_list,
            "locations": locations_list,
            "sponsors": sponsors_list,
            "start_date": start_date,
            "completion_date": completion_date,
            "enrollment": enrollment,
            "study_type": study_type,
            "source": "clinicaltrials_gov_complete",
            "download_timestamp": time.time()
        }

    async def save_complete_dataset(self, studies: list[dict]) -> str:
        """Save complete dataset to JSON file for processing"""
        output_file = os.path.join(self.data_dir, "all_clinical_trials_complete.json")
        
        # Prepare metadata
        dataset = {
            "metadata": {
                "total_studies": len(studies),
                "download_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "api_calls_made": self.stats["total_api_calls"],
                "source": "clinicaltrials.gov",
                "api_version": "v2",
                "schema_version": "medical_mirrors_compatible"
            },
            "studies": studies
        }
        
        # Save with proper formatting
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Saved complete dataset: {output_file}")
        return output_file

    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.aclose()

    def get_download_stats(self) -> dict[str, Any]:
        """Get comprehensive download statistics"""
        stats = self.stats.copy()
        
        if stats["start_time"] and stats["end_time"]:
            duration = stats["end_time"] - stats["start_time"]
            stats["duration_seconds"] = duration
            stats["duration_minutes"] = duration / 60
            
            if duration > 0:
                stats["studies_per_second"] = stats["studies_downloaded"] / duration
                stats["api_calls_per_minute"] = stats["total_api_calls"] / (duration / 60)
        
        return stats


def main():
    """Main function for complete ClinicalTrials download"""
    parser = argparse.ArgumentParser(
        description="Download complete ClinicalTrials.gov archive for offline operation",
        epilog="Uses medical-mirrors configuration for database compatibility"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        help="Directory to store complete ClinicalTrials data (default: medical-mirrors config)"
    )

    args = parser.parse_args()

    # Create downloader with optional custom data directory
    downloader = CompleteClinicalTrialsDownloader(custom_data_dir=args.data_dir)

    print(f"\n🧪 Starting complete ClinicalTrials.gov download to: {downloader.data_dir}")
    print("⚠️  Target: ~450,000 studies (~500MB total)")
    print("💾 Uses API pagination for complete dataset")
    print("🔧 Using medical-mirrors config for database compatibility\n")

    # Run download
    result = asyncio.run(downloader.download_complete_archive())

    # Show results
    if isinstance(result, dict) and result.get("status") == "success":
        print("\n✅ ClinicalTrials download completed successfully!")
        print(f"   Studies downloaded: {result.get('studies_downloaded', 'N/A')}")
        print(f"   Duration: {result.get('duration_minutes', 0):.1f} minutes")
        print(f"   Complete file: {result.get('complete_file', 'N/A')}")
    else:
        print("\n❌ ClinicalTrials download failed or incomplete")
        if isinstance(result, dict) and "error" in result:
            print(f"   Error: {result['error']}")

    # Show download statistics
    stats = downloader.get_download_stats()
    print(f"\n📊 Download Statistics:")
    print(f"   API calls made: {stats.get('total_api_calls', 0)}")
    print(f"   Average speed: {stats.get('studies_per_second', 0):.1f} studies/sec")
    print(f"   Errors: {len(stats.get('errors', []))}")
    
    # Show next steps
    print(f"\n📋 Next Steps:")
    print(f"   1. Parse downloaded file: python scripts/parse_downloaded_archives.py trials")
    print(f"   2. Or use medical-mirrors API: POST /update/trials")
    print(f"   3. Files stored in: {downloader.data_dir}")

    # Clean up
    asyncio.run(downloader.close())


if __name__ == "__main__":
    main()