"""
DrugCentral JSON Parser
Parses DrugCentral JSON files to extract mechanism of action and pharmacology data
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class DrugCentralParser:
    """Parser for DrugCentral JSON data files"""

    def __init__(self):
        pass

    def parse_mechanism_of_action_file(self, json_file_path: str) -> dict[str, str]:
        """Parse DrugCentral mechanism_of_action.json file"""
        logger.info(f"Parsing DrugCentral mechanism of action data: {json_file_path}")

        mechanism_data = {}

        try:
            with open(json_file_path) as f:
                data = json.load(f)

            results = data.get("results", [])
            logger.info(f"Found {len(results)} mechanism of action records")

            for record in results:
                try:
                    drug_name = record.get("drug_name", "").strip()
                    if not drug_name:
                        continue

                    # Build mechanism description
                    mechanism_parts = []

                    mechanism_action = record.get("mechanism_of_action", "")
                    target_name = record.get("target_name", "")
                    target_class = record.get("target_class", "")

                    if mechanism_action and target_name:
                        mechanism_parts.append(f"{mechanism_action} of {target_name}")
                    elif mechanism_action:
                        mechanism_parts.append(mechanism_action)
                    elif target_name:
                        mechanism_parts.append(f"Acts on {target_name}")

                    if target_class:
                        mechanism_parts.append(f"Target class: {target_class}")

                    gene_info = record.get("gene", "")
                    if gene_info:
                        mechanism_parts.append(f"Genes: {gene_info}")

                    if mechanism_parts:
                        mechanism_text = ". ".join(mechanism_parts) + "."

                        # Store by drug name (normalized)
                        drug_key = drug_name.lower().strip()

                        # If we already have data for this drug, combine it
                        if drug_key in mechanism_data:
                            existing = mechanism_data[drug_key]
                            mechanism_data[drug_key] = f"{existing} {mechanism_text}"
                        else:
                            mechanism_data[drug_key] = mechanism_text

                except Exception as e:
                    logger.warning(f"Error processing mechanism record: {e}")
                    continue

            logger.info(f"Processed mechanism of action for {len(mechanism_data)} drugs")
            return mechanism_data

        except Exception as e:
            logger.exception(f"Failed to parse mechanism of action file {json_file_path}: {e}")
            return {}

    def parse_pharmacology_file(self, json_file_path: str) -> dict[str, dict[str, str]]:
        """Parse DrugCentral pharmacology.json file"""
        logger.info(f"Parsing DrugCentral pharmacology data: {json_file_path}")

        pharmacology_data = {}

        try:
            with open(json_file_path) as f:
                data = json.load(f)

            results = data.get("results", [])
            logger.info(f"Found {len(results)} pharmacology records")

            for record in results:
                try:
                    drug_name = record.get("drug_name", "").strip()
                    if not drug_name:
                        continue

                    # Extract pharmacology information
                    pharmacology_info = {
                        "pharmacokinetics": "",
                        "pharmacodynamics": "",
                    }

                    # Build pharmacokinetics information
                    pk_parts = []

                    absorption = record.get("absorption", "")
                    distribution = record.get("distribution", "")
                    metabolism = record.get("metabolism", "")
                    elimination = record.get("elimination", "")
                    half_life = record.get("half_life", "")
                    bioavailability = record.get("bioavailability", "")

                    if absorption:
                        pk_parts.append(f"Absorption: {absorption}")
                    if distribution:
                        pk_parts.append(f"Distribution: {distribution}")
                    if metabolism:
                        pk_parts.append(f"Metabolism: {metabolism}")
                    if elimination:
                        pk_parts.append(f"Elimination: {elimination}")
                    if half_life:
                        pk_parts.append(f"Half-life: {half_life}")
                    if bioavailability:
                        pk_parts.append(f"Bioavailability: {bioavailability}")

                    if pk_parts:
                        pharmacology_info["pharmacokinetics"] = ". ".join(pk_parts) + "."

                    # Build pharmacodynamics information
                    pd_parts = []

                    mechanism = record.get("mechanism", "")
                    target_effect = record.get("target_effect", "")
                    onset_action = record.get("onset_action", "")
                    duration_action = record.get("duration_action", "")

                    if mechanism:
                        pd_parts.append(f"Mechanism: {mechanism}")
                    if target_effect:
                        pd_parts.append(f"Effect: {target_effect}")
                    if onset_action:
                        pd_parts.append(f"Onset: {onset_action}")
                    if duration_action:
                        pd_parts.append(f"Duration: {duration_action}")

                    if pd_parts:
                        pharmacology_info["pharmacodynamics"] = ". ".join(pd_parts) + "."

                    # Store by drug name (normalized)
                    drug_key = drug_name.lower().strip()

                    # If we already have data for this drug, combine it
                    if drug_key in pharmacology_data:
                        existing = pharmacology_data[drug_key]
                        for field in ["pharmacokinetics", "pharmacodynamics"]:
                            if pharmacology_info[field]:
                                if existing.get(field):
                                    existing[field] += f" {pharmacology_info[field]}"
                                else:
                                    existing[field] = pharmacology_info[field]
                    else:
                        pharmacology_data[drug_key] = pharmacology_info

                except Exception as e:
                    logger.warning(f"Error processing pharmacology record: {e}")
                    continue

            logger.info(f"Processed pharmacology data for {len(pharmacology_data)} drugs")
            return pharmacology_data

        except Exception as e:
            logger.exception(f"Failed to parse pharmacology file {json_file_path}: {e}")
            return {}

    def parse_drug_targets_file(self, json_file_path: str) -> dict[str, str]:
        """Parse DrugCentral drug_targets.json file"""
        logger.info(f"Parsing DrugCentral drug targets data: {json_file_path}")

        targets_data = {}

        try:
            with open(json_file_path) as f:
                data = json.load(f)

            results = data.get("results", [])
            logger.info(f"Found {len(results)} drug target records")

            for record in results:
                try:
                    drug_name = record.get("drug_name", "").strip()
                    if not drug_name:
                        continue

                    # Build target information
                    target_parts = []

                    target_name = record.get("target_name", "")
                    target_type = record.get("target_type", "")
                    action_type = record.get("action_type", "")

                    if action_type and target_name:
                        target_parts.append(f"{action_type} {target_name}")
                    elif target_name:
                        target_parts.append(target_name)

                    if target_type:
                        target_parts.append(f"({target_type})")

                    if target_parts:
                        target_text = " ".join(target_parts)

                        # Store by drug name (normalized)
                        drug_key = drug_name.lower().strip()

                        # If we already have data for this drug, combine it
                        if drug_key in targets_data:
                            existing = targets_data[drug_key]
                            targets_data[drug_key] = f"{existing}; {target_text}"
                        else:
                            targets_data[drug_key] = target_text

                except Exception as e:
                    logger.warning(f"Error processing drug target record: {e}")
                    continue

            logger.info(f"Processed drug targets for {len(targets_data)} drugs")
            return targets_data

        except Exception as e:
            logger.exception(f"Failed to parse drug targets file {json_file_path}: {e}")
            return {}

    def parse_drugcentral_directory(self, drugcentral_dir: str) -> dict[str, dict[str, str]]:
        """Parse all DrugCentral JSON files in directory"""
        logger.info(f"Parsing DrugCentral data from {drugcentral_dir}")

        drugcentral_data = {}

        # Parse mechanism of action file
        moa_file = Path(drugcentral_dir) / "mechanism_of_action.json"
        if moa_file.exists():
            mechanism_data = self.parse_mechanism_of_action_file(str(moa_file))

            # Add mechanism data to main dictionary
            for drug_key, mechanism_text in mechanism_data.items():
                if drug_key not in drugcentral_data:
                    drugcentral_data[drug_key] = {}
                drugcentral_data[drug_key]["mechanism_of_action"] = mechanism_text

        # Parse pharmacology file
        pharm_file = Path(drugcentral_dir) / "pharmacology.json"
        if pharm_file.exists():
            pharmacology_data = self.parse_pharmacology_file(str(pharm_file))

            # Add pharmacology data to main dictionary
            for drug_key, pharm_info in pharmacology_data.items():
                if drug_key not in drugcentral_data:
                    drugcentral_data[drug_key] = {}
                drugcentral_data[drug_key].update(pharm_info)

        # Parse drug targets file
        targets_file = Path(drugcentral_dir) / "drug_targets.json"
        if targets_file.exists():
            targets_data = self.parse_drug_targets_file(str(targets_file))

            # Add targets data to main dictionary
            for drug_key, target_text in targets_data.items():
                if drug_key not in drugcentral_data:
                    drugcentral_data[drug_key] = {}
                drugcentral_data[drug_key]["drug_targets"] = target_text

        logger.info(f"Parsed DrugCentral data for {len(drugcentral_data)} drugs")
        return drugcentral_data
