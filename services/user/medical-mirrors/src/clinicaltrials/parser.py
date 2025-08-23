"""
ClinicalTrials.gov JSON parser
Parses ClinicalTrials.gov JSON files and extracts study information
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ClinicalTrialsParser:
    """Parses ClinicalTrials.gov JSON files and extracts study data"""

    def __init__(self) -> None:
        pass

    def parse_json_file(self, json_file_path: str) -> list[dict[str, Any]]:
        """Parse a ClinicalTrials.gov JSON file and extract studies"""
        logger.info(f"Parsing ClinicalTrials JSON file: {json_file_path}")
        studies: list[dict[str, Any]] = []

        try:
            with open(json_file_path) as f:
                data = json.load(f)

            # Extract studies from the JSON structure
            studies_data = data.get("studies", [])
            if not studies_data:
                # Handle different JSON structures
                studies_data = data.get("StudyList", {}).get("Study", [])

            for study_data in studies_data:
                study = self.parse_study(study_data)
                if study:
                    studies.append(study)

            logger.info(f"Parsed {len(studies)} studies from {json_file_path}")
            return studies

        except Exception as e:
            logger.exception(f"Failed to parse {json_file_path}: {e}")
            return []

    def parse_study(self, study_data: dict[str, Any]) -> dict[str, Any] | None:
        """Parse a single study record"""
        try:
            # Handle API v2 structure (protocolSection)
            protocol_section = study_data.get("protocolSection", {})

            # Extract NCT ID
            nct_id = None
            if protocol_section:
                # API v2 structure
                nct_id = protocol_section.get("identificationModule", {}).get("nctId")
            else:
                # Legacy structure
                nct_id = self.extract_value(study_data, ["NCTId", "Identification", "NCTId"])

            if not nct_id:
                return None

            # Extract basic information
            if protocol_section:
                # API v2 structure
                identification = protocol_section.get("identificationModule", {})
                status_module = protocol_section.get("statusModule", {})
                design_module = protocol_section.get("designModule", {})

                title = identification.get("briefTitle", "")
                status = status_module.get("overallStatus", "")
                phase = design_module.get("phases", [""])[0] if design_module.get("phases") else ""
                study_type = design_module.get("studyType", "")

                # Extract conditions
                conditions_module = protocol_section.get("conditionsModule", {})
                conditions = conditions_module.get("conditions", [])

                # Extract interventions
                arms_module = protocol_section.get("armsInterventionsModule", {})
                interventions = []
                if arms_module.get("interventions"):
                    for intervention in arms_module["interventions"]:
                        interventions.append(intervention.get("name", ""))

                # Extract sponsors
                sponsors_module = protocol_section.get("sponsorCollaboratorsModule", {})
                sponsors = []
                if sponsors_module.get("leadSponsor"):
                    sponsors.append(sponsors_module["leadSponsor"].get("name", ""))
                if sponsors_module.get("collaborators"):
                    for collab in sponsors_module["collaborators"]:
                        sponsors.append(collab.get("name", ""))

                # Extract dates
                start_date = status_module.get("startDateStruct", {}).get("date", "")
                completion_date = status_module.get("completionDateStruct", {}).get("date", "")

                # Extract locations
                contacts_module = protocol_section.get("contactsLocationsModule", {})
                locations = []
                if contacts_module.get("locations"):
                    for location in contacts_module["locations"]:
                        loc_str = location.get("facility", "")
                        if location.get("city"):
                            loc_str += f", {location['city']}"
                        if location.get("state"):
                            loc_str += f", {location['state']}"
                        if location.get("country"):
                            loc_str += f", {location['country']}"
                        if loc_str:
                            locations.append(loc_str)

            else:
                # Legacy structure
                title = self.extract_value(
                    study_data,
                    ["BriefTitle", "IdentificationModule", "BriefTitle"],
                )
                status = self.extract_value(
                    study_data,
                    ["OverallStatus", "StatusModule", "OverallStatus"],
                )
                phase = self.extract_value(study_data, ["Phase", "DesignModule", "Phase"])
                study_type = self.extract_value(
                    study_data, ["StudyType", "DesignModule", "StudyType"]
                )

                # Extract conditions, interventions, locations, sponsors using legacy methods
                conditions = self.extract_conditions(study_data)
                interventions = self.extract_interventions(study_data)
                locations = self.extract_locations(study_data)
                sponsors = self.extract_sponsors(study_data)

                # Extract dates
                start_date = self.extract_value(
                    study_data,
                    ["StartDate", "StatusModule", "StartDateStruct", "StartDate"],
                )
                completion_date = self.extract_value(
                    study_data,
                    ["CompletionDate", "StatusModule", "CompletionDateStruct", "CompletionDate"],
                )

            # Extract enrollment
            enrollment = self.extract_enrollment(study_data)

            return {
                "nct_id": nct_id,
                "title": title or "",
                "status": status or "",
                "phase": phase or "",
                "conditions": conditions,
                "interventions": interventions,
                "locations": locations,
                "sponsors": sponsors,
                "start_date": start_date or "",
                "completion_date": completion_date or "",
                "enrollment": enrollment,
                "study_type": study_type or "",
            }

        except Exception as e:
            logger.exception(f"Failed to parse study: {e}")
            return None

    def extract_value(self, data: dict[str, Any], paths: list[str]) -> str | None:
        """Extract value from nested dict using multiple possible paths"""
        for path in paths:
            try:
                value: Any = data
                for key in path.split(".") if "." in path else [path]:
                    if isinstance(value, dict) and key in value:
                        value = value[key]
                    else:
                        value = None
                        break

                if value:
                    return str(value)
            except (KeyError, TypeError, AttributeError):
                continue

        return None

    def extract_conditions(self, study_data: dict[str, Any]) -> list[str]:
        """Extract condition names from study"""
        conditions: list[str] = []

        # Try different paths for conditions
        condition_paths = [
            "Condition",
            "ConditionsModule.ConditionList.Condition",
            "ConditionsModule.Condition",
        ]

        for path in condition_paths:
            try:
                value: Any = study_data
                for key in path.split("."):
                    if isinstance(value, dict):
                        value = value.get(key, {})
                    else:
                        value = None
                        break

                if isinstance(value, list):
                    conditions.extend([str(c) for c in value if c])
                elif value:
                    conditions.append(str(value))

            except (KeyError, TypeError, AttributeError):
                continue

        return list(set(conditions))  # Remove duplicates

    def extract_interventions(self, study_data: dict[str, Any]) -> list[str]:
        """Extract intervention names from study"""
        interventions: list[str] = []

        # Try different paths for interventions
        intervention_paths = [
            "InterventionName",
            "ArmsInterventionsModule.InterventionList.Intervention",
            "InterventionList.Intervention",
        ]

        for path in intervention_paths:
            try:
                value: Any = study_data
                for key in path.split("."):
                    if isinstance(value, dict):
                        value = value.get(key, {})
                    else:
                        value = None
                        break

                if isinstance(value, list):
                    for intervention in value:
                        if isinstance(intervention, dict):
                            name = intervention.get("InterventionName") or intervention.get("Name")
                            if name:
                                interventions.append(str(name))
                        else:
                            interventions.append(str(intervention))
                elif value:
                    interventions.append(str(value))

            except (KeyError, TypeError, AttributeError):
                continue

        return list(set(interventions))  # Remove duplicates

    def extract_locations(self, study_data: dict[str, Any]) -> list[str]:
        """Extract location information from study"""
        locations: list[str] = []

        try:
            # Try different paths for locations
            location_paths = [
                "ContactsLocationsModule.LocationList.Location",
                "LocationList.Location",
            ]

            for path in location_paths:
                value: Any = study_data
                for key in path.split("."):
                    if isinstance(value, dict):
                        value = value.get(key, {})
                    else:
                        value = None
                        break

                if isinstance(value, list):
                    for location in value:
                        if isinstance(location, dict):
                            facility = location.get("LocationFacility", "")
                            city = location.get("LocationCity", "")
                            state = location.get("LocationState", "")
                            country = location.get("LocationCountry", "")

                            location_str = ", ".join(filter(None, [facility, city, state, country]))
                            if location_str:
                                locations.append(location_str)

            # Also try simple location fields
            simple_locations: list[str] = []
            for field in ["LocationFacility", "LocationCity", "LocationState", "LocationCountry"]:
                value = study_data.get(field)
                if value:
                    simple_locations.append(str(value))

            if simple_locations:
                locations.append(", ".join(simple_locations))

        except Exception as e:
            logger.exception(f"Failed to extract locations: {e}")

        return list(set(locations))  # Remove duplicates

    def extract_sponsors(self, study_data: dict[str, Any]) -> list[str]:
        """Extract sponsor information from study"""
        sponsors: list[str] = []

        try:
            # Try different paths for sponsors
            sponsor_paths = [
                "SponsorCollaboratorsModule.LeadSponsor.LeadSponsorName",
                "LeadSponsorName",
                "SponsorList.LeadSponsor.LeadSponsorName",
            ]

            for path in sponsor_paths:
                value: Any = study_data
                for key in path.split("."):
                    if isinstance(value, dict):
                        value = value.get(key, {})
                    else:
                        value = None
                        break

                if value:
                    sponsors.append(str(value))

            # Also try collaborators
            collab_paths = [
                "SponsorCollaboratorsModule.CollaboratorList.Collaborator",
                "CollaboratorList.Collaborator",
            ]

            for path in collab_paths:
                value = study_data
                for key in path.split("."):
                    if isinstance(value, dict):
                        value = value.get(key, {})
                    else:
                        value = None
                        break

                if isinstance(value, list):
                    for collab in value:
                        if isinstance(collab, dict):
                            name = collab.get("CollaboratorName")
                            if name:
                                sponsors.append(str(name))
                        else:
                            sponsors.append(str(collab))

        except Exception as e:
            logger.exception(f"Failed to extract sponsors: {e}")

        return list(set(sponsors))  # Remove duplicates

    def extract_enrollment(self, study_data: dict[str, Any]) -> int | None:
        """Extract enrollment count from study"""
        try:
            enrollment_paths = [
                "EnrollmentCount",
                "DesignModule.EnrollmentInfo.EnrollmentCount",
                "EnrollmentInfo.EnrollmentCount",
            ]

            for path in enrollment_paths:
                value: Any = study_data
                for key in path.split("."):
                    if isinstance(value, dict):
                        value = value.get(key, {})
                    else:
                        value = None
                        break

                if value:
                    try:
                        return int(value)
                    except (ValueError, TypeError):
                        continue

            return None

        except Exception as e:
            logger.exception(f"Failed to extract enrollment: {e}")
            return None
