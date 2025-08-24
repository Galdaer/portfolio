#!/usr/bin/env python3
"""
Load billing codes JSON files into medical-mirrors database
Uses the same parsing logic as medical-mirrors update scripts
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

# Add medical-mirrors to Python path
medical_mirrors_src = str(Path(__file__).parent.parent / "services/user/medical-mirrors/src")
if medical_mirrors_src not in sys.path:
    sys.path.insert(0, medical_mirrors_src)

try:
    from billing_codes.parser import BillingCodesParser
    from sqlalchemy import text

    from config import Config
    from database import get_db_session
except ImportError as e:
    print(f"Failed to import medical-mirrors modules: {e}")
    print("Make sure medical-mirrors service is properly installed")
    sys.exit(1)


class BillingCodesLoader:
    """Load complete billing codes from JSON files into database"""

    def __init__(self, data_dir: str = None):
        self.config = Config()
        self.data_dir = data_dir or self.config.DATA_DIR
        self.logger = self._setup_logging()
        self.parser = BillingCodesParser()

        # Statistics
        self.stats = {
            "files_processed": 0,
            "billing_codes_loaded": 0,
            "total_items_loaded": 0,
            "errors": [],
        }

    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger("billing_codes_loader")
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def find_billing_codes_files(self) -> dict[str, str]:
        """Find all billing codes JSON files"""
        json_files = {}

        # Look for files in billing_codes/billing subdirectory and data root
        search_dirs = [
            os.path.join(self.data_dir, "billing_codes"),
            os.path.join(self.data_dir, "billing"),
            self.data_dir,
        ]

        for search_dir in search_dirs:
            if os.path.exists(search_dir):
                for filename in os.listdir(search_dir):
                    if filename.startswith("all_billing") and filename.endswith("_complete.json"):
                        # Extract dataset type from filename
                        # all_billing_codes_complete.json -> billing_codes
                        dataset_type = filename.replace("all_", "").replace("_complete.json", "")
                        json_files[dataset_type] = os.path.join(search_dir, filename)

        return json_files

    def load_json_file(self, file_path: str) -> dict[str, Any]:
        """Load and validate JSON file"""
        self.logger.info(f"Loading JSON file: {file_path}")

        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)

            # Validate structure
            if "metadata" not in data:
                raise ValueError("Missing metadata section")

            metadata = data["metadata"]
            total_codes = metadata.get("total_codes", 0)

            # Check for codes section
            if "codes" not in data:
                raise ValueError("Missing codes section")

            self.logger.info(f"Loaded {total_codes} billing codes from file")
            return data

        except Exception as e:
            self.logger.exception(f"Error loading JSON file {file_path}: {e}")
            self.stats["errors"].append(f"JSON load error in {file_path}: {e}")
            return {}

    def load_all_billing_codes(self):
        """Load all billing codes JSON files into database"""
        self.logger.info("Starting billing codes loading process")

        # Find all JSON files
        json_files = self.find_billing_codes_files()
        self.logger.info(f"Found {len(json_files)} JSON files: {list(json_files.keys())}")

        if not json_files:
            self.logger.warning("No billing codes JSON files found! Make sure to run download scripts first.")
            return False

        # Load billing codes files
        all_raw_codes = []

        for _dataset_type, file_path in json_files.items():
            file_data = self.load_json_file(file_path)
            if file_data and "codes" in file_data:
                all_raw_codes.extend(file_data["codes"])
                self.stats["files_processed"] += 1

        if not all_raw_codes:
            self.logger.warning("No billing codes found in JSON files")
            return False

        self.logger.info(f"Found {len(all_raw_codes)} total billing codes to process")

        # Parse and validate using the medical-mirrors parser
        self.logger.info("Parsing and validating billing codes")
        validated_codes = self.parser.parse_and_validate(all_raw_codes)

        self.logger.info(f"Validation complete: {len(validated_codes)} valid codes")

        # Insert into database using the same logic as update_billing.sh
        return self._insert_into_database(validated_codes)

    def _insert_into_database(self, validated_codes: list[dict]) -> bool:
        """Insert validated billing codes into database using medical-mirrors patterns"""
        self.logger.info("Inserting billing codes into database")

        try:
            with get_db_session() as db:
                self.logger.info("Upserting billing codes (preserving existing data)")

                # Use UPSERT with composite key (code + code_type) to preserve existing data
                for code_data in validated_codes:
                    db.execute(text("""
                        INSERT INTO billing_codes (
                            code, short_description, long_description, description,
                            code_type, category, coverage_notes, effective_date,
                            termination_date, is_active, modifier_required,
                            gender_specific, age_specific, bilateral_indicator,
                            source, search_text, last_updated, search_vector
                        ) VALUES (
                            :code, :short_description, :long_description, :description,
                            :code_type, :category, :coverage_notes, :effective_date,
                            :termination_date, :is_active, :modifier_required,
                            :gender_specific, :age_specific, :bilateral_indicator,
                            :source, :search_text, NOW(),
                            to_tsvector('english', COALESCE(:search_text, ''))
                        )
                        ON CONFLICT (code) DO UPDATE SET
                            -- Only update if we have better/more complete information
                            short_description = COALESCE(NULLIF(EXCLUDED.short_description, ''), billing_codes.short_description),
                            long_description = COALESCE(NULLIF(EXCLUDED.long_description, ''), billing_codes.long_description),
                            description = COALESCE(NULLIF(EXCLUDED.description, ''), billing_codes.description),
                            category = COALESCE(NULLIF(EXCLUDED.category, ''), billing_codes.category),
                            coverage_notes = COALESCE(NULLIF(EXCLUDED.coverage_notes, ''), billing_codes.coverage_notes),
                            effective_date = COALESCE(EXCLUDED.effective_date, billing_codes.effective_date),
                            termination_date = COALESCE(EXCLUDED.termination_date, billing_codes.termination_date),
                            is_active = COALESCE(EXCLUDED.is_active, billing_codes.is_active),
                            modifier_required = COALESCE(EXCLUDED.modifier_required, billing_codes.modifier_required),
                            gender_specific = COALESCE(NULLIF(EXCLUDED.gender_specific, ''), billing_codes.gender_specific),
                            age_specific = COALESCE(NULLIF(EXCLUDED.age_specific, ''), billing_codes.age_specific),
                            bilateral_indicator = COALESCE(EXCLUDED.bilateral_indicator, billing_codes.bilateral_indicator),
                            source = COALESCE(NULLIF(EXCLUDED.source, ''), billing_codes.source),
                            search_text = COALESCE(NULLIF(EXCLUDED.search_text, ''), billing_codes.search_text),
                            search_vector = to_tsvector('english', COALESCE(EXCLUDED.search_text, '')),
                            last_updated = NOW()
                    """), {
                        "code": code_data["code"],
                        "short_description": code_data.get("short_description"),
                        "long_description": code_data.get("long_description"),
                        "description": code_data.get("description"),
                        "code_type": code_data["code_type"],
                        "category": code_data.get("category"),
                        "coverage_notes": code_data.get("coverage_notes"),
                        "effective_date": code_data["effective_date"] if code_data.get("effective_date") and code_data["effective_date"] != "" else None,
                        "termination_date": code_data["termination_date"] if code_data.get("termination_date") and code_data["termination_date"] != "" else None,
                        "is_active": code_data.get("is_active", True),
                        "modifier_required": code_data.get("modifier_required", False),
                        "gender_specific": code_data.get("gender_specific"),
                        "age_specific": code_data.get("age_specific"),
                        "bilateral_indicator": code_data.get("bilateral_indicator", False),
                        "source": code_data.get("source"),
                        "search_text": code_data.get("search_text"),
                    })

                db.commit()

                # Update statistics
                result = db.execute(text("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(CASE WHEN is_active = true THEN 1 END) as active,
                        COUNT(CASE WHEN code_type = 'HCPCS' THEN 1 END) as hcpcs,
                        COUNT(CASE WHEN code_type = 'CPT' THEN 1 END) as cpt
                    FROM billing_codes
                """))

                stats = result.fetchone()
                self.stats["billing_codes_loaded"] = len(validated_codes)
                self.stats["total_items_loaded"] = len(validated_codes)

                self.logger.info(f"Successfully inserted {stats.total} billing codes total")
                self.logger.info(f"  Active: {stats.active}, HCPCS: {stats.hcpcs}, CPT: {stats.cpt}")
                self.logger.info(f"  Newly loaded: {len(validated_codes)}")

                return True

        except Exception as e:
            self.logger.exception(f"Error inserting billing codes into database: {e}")
            self.stats["errors"].append(f"Database insert error: {e}")
            return False


def main():
    """Main function to load billing codes"""
    import argparse

    parser = argparse.ArgumentParser(description="Load billing codes JSON files into database")
    parser.add_argument("--data-dir", help="Directory containing billing codes JSON files")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    loader = BillingCodesLoader(args.data_dir)

    try:
        success = loader.load_all_billing_codes()

        print("\n=== Billing Codes Loading Summary ===")
        print(f"Files processed: {loader.stats['files_processed']}")
        print(f"Billing codes loaded: {loader.stats['billing_codes_loaded']}")
        print(f"Total items: {loader.stats['total_items_loaded']}")

        if loader.stats["errors"]:
            print(f"Errors: {len(loader.stats['errors'])}")
            for error in loader.stats["errors"]:
                print(f"  - {error}")

        if success:
            print("✅ Billing codes loading completed successfully!")
            sys.exit(0)
        else:
            print("❌ Billing codes loading failed!")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Fatal error during billing codes loading: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
