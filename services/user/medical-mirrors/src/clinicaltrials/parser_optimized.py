"""
Optimized multi-core ClinicalTrials parser
Utilizes all available CPU cores for JSON parsing and database operations
"""

import json
import logging
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from typing import Any

logger = logging.getLogger(__name__)


def parse_json_chunk_worker(json_chunk: list[dict[str, Any]], chunk_id: int) -> tuple[int, list[dict[str, Any]]]:
    """Worker function for multiprocessing JSON chunk parsing"""
    try:
        logger.info(f"Worker parsing clinical trials chunk {chunk_id} ({len(json_chunk)} studies)")
        parsed_studies = []

        for study_data in json_chunk:
            parsed_study = parse_study_worker(study_data)
            if parsed_study:
                parsed_studies.append(parsed_study)

        logger.info(f"Worker parsed {len(parsed_studies)} studies from chunk {chunk_id}")
        return chunk_id, parsed_studies

    except Exception as e:
        logger.exception(f"Worker failed to parse chunk {chunk_id}: {e}")
        return chunk_id, []


def parse_json_file_worker(json_file_path: str) -> tuple[str, list[dict[str, Any]]]:
    """Worker function for parsing individual JSON files"""
    try:
        logger.info(f"Worker parsing clinical trials file: {json_file_path}")
        studies = []

        with open(json_file_path, encoding="utf-8") as f:
            data = json.load(f)

        # Handle different JSON structures
        studies_data = []
        if isinstance(data, dict):
            if "studies" in data:
                studies_data = data["studies"]
            elif "metadata" in data and "studies" in data:
                # Our download format
                studies_data = data["studies"]
            elif "StudyList" in data and "Study" in data["StudyList"]:
                studies_data = data["StudyList"]["Study"]
        elif isinstance(data, list):
            studies_data = data

        for study_data in studies_data:
            parsed_study = parse_study_worker(study_data)
            if parsed_study:
                studies.append(parsed_study)

        logger.info(f"Worker parsed {len(studies)} studies from {json_file_path}")
        return json_file_path, studies

    except Exception as e:
        logger.exception(f"Worker failed to parse {json_file_path}: {e}")
        return json_file_path, []


def parse_study_worker(study_data: dict[str, Any]) -> dict[str, Any] | None:
    """Parse a single study record (optimized for multiprocessing)"""
    try:
        # Extract NCT ID (required primary key)
        nct_id = extract_nct_id(study_data)
        if not nct_id:
            return None

        # Extract title
        title = extract_title(study_data)
        if not title:
            return None

        # Extract status (VARCHAR 100 constraint)
        status = extract_status(study_data)[:100] if extract_status(study_data) else ""

        # Extract phase (VARCHAR 100 constraint)
        phase = extract_phase(study_data)[:100] if extract_phase(study_data) else ""

        # Extract conditions as array
        conditions = extract_conditions(study_data)

        # Extract interventions as array
        interventions = extract_interventions(study_data)

        # Extract locations as array
        locations = extract_locations(study_data)

        # Extract sponsors as array
        sponsors = extract_sponsors(study_data)

        # Extract dates (VARCHAR 20 constraint)
        start_date = extract_start_date(study_data)[:20] if extract_start_date(study_data) else ""
        completion_date = extract_completion_date(study_data)[:20] if extract_completion_date(study_data) else ""

        # Extract enrollment (INTEGER)
        enrollment = extract_enrollment(study_data)

        # Extract study type (VARCHAR 100 constraint)
        study_type = extract_study_type(study_data)[:100] if extract_study_type(study_data) else ""

        return {
            "nct_id": nct_id,
            "title": title,
            "status": status,
            "phase": phase,
            "conditions": conditions,
            "interventions": interventions,
            "locations": locations,
            "sponsors": sponsors,
            "start_date": start_date,
            "completion_date": completion_date,
            "enrollment": enrollment,
            "study_type": study_type,
            "source": "clinicaltrials_gov_complete",
        }

    except Exception as e:
        logger.warning(f"Failed to parse study record: {e}")
        return None


def extract_nct_id(study_data: dict[str, Any]) -> str:
    """Extract NCT ID from study data"""
    # Try different possible locations for NCT ID
    nct_id = study_data.get("nct_id", "")
    if not nct_id:
        nct_id = study_data.get("protocolSection", {}).get("identificationModule", {}).get("nctId", "")
    if not nct_id:
        nct_id = study_data.get("id", "")
    return str(nct_id).strip()


def extract_title(study_data: dict[str, Any]) -> str:
    """Extract study title"""
    title = study_data.get("title", "")
    if not title:
        title = study_data.get("protocolSection", {}).get("identificationModule", {}).get("briefTitle", "")
    if not title:
        title = study_data.get("briefTitle", "")
    return str(title).strip()


def extract_status(study_data: dict[str, Any]) -> str:
    """Extract study status"""
    status = study_data.get("status", "")
    if not status:
        status = study_data.get("protocolSection", {}).get("statusModule", {}).get("overallStatus", "")
    if not status:
        status = study_data.get("overallStatus", "")
    return str(status).strip()


def extract_phase(study_data: dict[str, Any]) -> str:
    """Extract study phase"""
    # Try different locations for phase information
    phase_info = study_data.get("phase", "")
    if not phase_info:
        phases = study_data.get("protocolSection", {}).get("designModule", {}).get("phases", [])
        if isinstance(phases, list) and phases:
            phase_info = ", ".join(phases)
        else:
            phase_info = str(phases) if phases else ""
    return str(phase_info).strip()


def extract_conditions(study_data: dict[str, Any]) -> list[str]:
    """Extract study conditions"""
    conditions = []

    # Try different locations
    conditions_data = study_data.get("conditions", [])
    if not conditions_data:
        conditions_module = study_data.get("protocolSection", {}).get("conditionsModule", {})
        conditions_data = conditions_module.get("conditions", [])
    if not conditions_data:
        condition_single = study_data.get("condition", "")
        if condition_single:
            conditions_data = [condition_single] if isinstance(condition_single, str) else condition_single

    # Normalize to list of strings
    if isinstance(conditions_data, list):
        conditions = [str(c).strip() for c in conditions_data if c]
    elif isinstance(conditions_data, str) and conditions_data:
        conditions = [conditions_data.strip()]

    return conditions


def extract_interventions(study_data: dict[str, Any]) -> list[str]:
    """Extract study interventions"""
    interventions = []

    # Try different locations
    interventions_data = study_data.get("interventions", [])
    if not interventions_data:
        interventions_module = study_data.get("protocolSection", {}).get("armsInterventionsModule", {})
        if "interventions" in interventions_module:
            for intervention in interventions_module["interventions"]:
                if isinstance(intervention, dict) and "name" in intervention:
                    interventions.append(str(intervention["name"]).strip())
                elif isinstance(intervention, str):
                    interventions.append(intervention.strip())
    elif not interventions_data:
        intervention_name = study_data.get("interventionName", "")
        if intervention_name:
            if isinstance(intervention_name, list):
                interventions = [str(i).strip() for i in intervention_name if i]
            else:
                interventions = [str(intervention_name).strip()]

    # Normalize existing interventions_data
    if isinstance(interventions_data, list) and not interventions:
        for intervention in interventions_data:
            if isinstance(intervention, dict):
                name = intervention.get("name", intervention.get("interventionName", ""))
                if name:
                    interventions.append(str(name).strip())
            elif isinstance(intervention, str):
                interventions.append(intervention.strip())

    return interventions


def extract_locations(study_data: dict[str, Any]) -> list[str]:
    """Extract study locations"""
    locations = []

    # Try different locations
    locations_data = study_data.get("locations", [])
    if not locations_data:
        contacts_locations = study_data.get("protocolSection", {}).get("contactsLocationsModule", {})
        if "locations" in contacts_locations:
            for location in contacts_locations["locations"]:
                location_parts = []
                if isinstance(location, dict):
                    facility = location.get("facility", "")
                    city = location.get("city", "")
                    state = location.get("state", "")
                    country = location.get("country", "")

                    location_parts = [str(p).strip() for p in [facility, city, state, country] if p]
                elif isinstance(location, str):
                    location_parts = [location.strip()]

                if location_parts:
                    locations.append(", ".join(location_parts))

    # Handle existing locations_data
    if isinstance(locations_data, list) and not locations:
        for location in locations_data:
            if isinstance(location, str):
                locations.append(location.strip())
            elif isinstance(location, dict):
                # Try to build location string from dict
                parts = []
                for key in ["facility", "city", "state", "country", "name"]:
                    if key in location and location[key]:
                        parts.append(str(location[key]).strip())
                if parts:
                    locations.append(", ".join(parts))

    return locations


def extract_sponsors(study_data: dict[str, Any]) -> list[str]:
    """Extract study sponsors"""
    sponsors = []

    # Try different locations
    sponsors_data = study_data.get("sponsors", [])
    if not sponsors_data:
        sponsor_info = study_data.get("protocolSection", {}).get("sponsorCollaboratorsModule", {})
        if "leadSponsor" in sponsor_info:
            lead_sponsor = sponsor_info["leadSponsor"].get("name", "")
            if lead_sponsor:
                sponsors.append(str(lead_sponsor).strip())
        if "collaborators" in sponsor_info:
            for collaborator in sponsor_info["collaborators"]:
                if isinstance(collaborator, dict) and "name" in collaborator:
                    sponsors.append(str(collaborator["name"]).strip())
    elif not sponsors_data:
        lead_sponsor_name = study_data.get("leadSponsorName", "")
        if lead_sponsor_name:
            sponsors.append(str(lead_sponsor_name).strip())

    # Handle existing sponsors_data
    if isinstance(sponsors_data, list) and not sponsors:
        for sponsor in sponsors_data:
            if isinstance(sponsor, str):
                sponsors.append(sponsor.strip())
            elif isinstance(sponsor, dict) and "name" in sponsor:
                sponsors.append(str(sponsor["name"]).strip())

    return sponsors


def extract_start_date(study_data: dict[str, Any]) -> str:
    """Extract study start date"""
    start_date = study_data.get("start_date", "")
    if not start_date:
        start_date = study_data.get("protocolSection", {}).get("statusModule", {}).get("startDateStruct", {}).get("date", "")
    if not start_date:
        start_date = study_data.get("startDate", "")
    return str(start_date).strip()


def extract_completion_date(study_data: dict[str, Any]) -> str:
    """Extract study completion date"""
    completion_date = study_data.get("completion_date", "")
    if not completion_date:
        completion_date = study_data.get("protocolSection", {}).get("statusModule", {}).get("completionDateStruct", {}).get("date", "")
    if not completion_date:
        completion_date = study_data.get("completionDate", "")
    return str(completion_date).strip()


def extract_enrollment(study_data: dict[str, Any]) -> int | None:
    """Extract study enrollment"""
    enrollment = study_data.get("enrollment")
    if enrollment is None:
        enrollment_info = study_data.get("protocolSection", {}).get("designModule", {}).get("enrollmentInfo", {})
        if "count" in enrollment_info:
            try:
                enrollment = int(enrollment_info["count"])
            except (ValueError, TypeError):
                enrollment = None
    elif enrollment is None:
        enrollment_count = study_data.get("enrollmentCount")
        if enrollment_count:
            try:
                enrollment = int(enrollment_count)
            except (ValueError, TypeError):
                enrollment = None

    if enrollment is not None:
        try:
            return int(enrollment)
        except (ValueError, TypeError):
            return None

    return None


def extract_study_type(study_data: dict[str, Any]) -> str:
    """Extract study type"""
    study_type = study_data.get("study_type", "")
    if not study_type:
        study_type = study_data.get("protocolSection", {}).get("designModule", {}).get("studyType", "")
    if not study_type:
        study_type = study_data.get("studyType", "")
    return str(study_type).strip()


class OptimizedClinicalTrialsParser:
    """Multi-core ClinicalTrials data parser with parallel processing"""

    def __init__(self, max_workers: int | None = None):
        """Initialize with specified number of workers"""
        if max_workers is None:
            max_workers = max(1, mp.cpu_count() // 2)
        self.max_workers = max_workers

        logger.info(
            f"Initialized ClinicalTrials parser with {self.max_workers} workers (CPU cores: {mp.cpu_count()})",
        )

    async def parse_json_files_parallel(
        self, json_files: list[str],
    ) -> list[dict[str, Any]]:
        """Parse multiple JSON files in parallel using all CPU cores"""
        logger.info(f"Parsing {len(json_files)} ClinicalTrials files using {self.max_workers} cores")

        all_studies = []
        parsed_files = []

        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all parsing tasks
            future_to_file = {
                executor.submit(parse_json_file_worker, json_file): json_file
                for json_file in json_files
            }

            # Process completed tasks
            for future in future_to_file:
                json_file = future_to_file[future]
                try:
                    file_path, studies = future.result()
                    all_studies.extend(studies)
                    parsed_files.append(file_path)
                except Exception as e:
                    logger.exception(f"Failed to parse {json_file}: {e}")

        total_studies = len(all_studies)
        logger.info(
            f"Parallel parsing completed: {total_studies} total studies from {len(parsed_files)} files",
        )

        return all_studies

    async def parse_large_json_file_parallel(
        self, json_file_path: str, chunk_size: int = 1000,
    ) -> list[dict[str, Any]]:
        """Parse a large JSON file by splitting into chunks and processing in parallel"""
        logger.info(f"Parsing large ClinicalTrials file with chunking: {json_file_path}")

        try:
            # Load the entire JSON file
            with open(json_file_path, encoding="utf-8") as f:
                data = json.load(f)

            # Extract studies data
            studies_data = []
            if isinstance(data, dict):
                if "studies" in data or "metadata" in data and "studies" in data:
                    studies_data = data["studies"]
                elif "StudyList" in data and "Study" in data["StudyList"]:
                    studies_data = data["StudyList"]["Study"]
            elif isinstance(data, list):
                studies_data = data

            if not studies_data:
                logger.warning(f"No studies found in {json_file_path}")
                return []

            total_studies = len(studies_data)
            logger.info(f"Splitting {total_studies} studies into chunks of {chunk_size}")

            # Split into chunks
            chunks = []
            for i in range(0, total_studies, chunk_size):
                chunk = studies_data[i:i + chunk_size]
                chunks.append(chunk)

            logger.info(f"Created {len(chunks)} chunks for parallel processing")

            all_studies = []

            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all chunk parsing tasks
                future_to_chunk = {
                    executor.submit(parse_json_chunk_worker, chunk, i): i
                    for i, chunk in enumerate(chunks)
                }

                # Process completed tasks
                for future in future_to_chunk:
                    chunk_id = future_to_chunk[future]
                    try:
                        _, studies = future.result()
                        all_studies.extend(studies)
                    except Exception as e:
                        logger.exception(f"Failed to parse chunk {chunk_id}: {e}")

            total_parsed = len(all_studies)
            logger.info(
                f"Parallel chunk parsing completed: {total_parsed} total studies processed",
            )

            return all_studies

        except Exception as e:
            logger.exception(f"Failed to parse large JSON file {json_file_path}: {e}")
            return []
