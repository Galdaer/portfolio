#!/usr/bin/env python3
"""
Complete ICD-10 Codes Archive Downloader
Downloads complete ICD-10 diagnostic codes for offline database operation

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

# Type checking imports
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from medical_mirrors_types import Config, ICD10Downloader
else:
    # Runtime imports - add medical-mirrors to Python path
    medical_mirrors_src = str(Path(__file__).parent.parent / "services/user/medical-mirrors/src")
    if medical_mirrors_src not in sys.path:
        sys.path.insert(0, medical_mirrors_src)

    try:
        from icd10.downloader import ICD10Downloader

        from config import Config
    except ImportError as e:
        print(f"Failed to import medical-mirrors modules: {e}")
        print("Make sure medical-mirrors service is properly installed")
        print(f"Looking for modules in: {medical_mirrors_src}")
        sys.exit(1)


class CompleteICD10Downloader:
    """
    Downloads complete ICD-10 diagnostic codes for local database caching.

    Based on the existing medical-mirrors ICD10Downloader but enhanced
    for systematic complete downloads with database schema compatibility.
    """

    def __init__(self, custom_data_dir: str | None = None):
        # Use medical-mirrors Config for consistency
        self.config = Config()

        # Allow custom data directory override
        if custom_data_dir:
            self.data_dir = custom_data_dir
            os.makedirs(self.data_dir, exist_ok=True)
        else:
            self.data_dir = self.config.get_icd10_data_dir()

        self.logger = self._setup_logging()

        # Use the existing ICD10Downloader as base
        self.base_downloader = ICD10Downloader(self.config)

        # Download statistics
        self.stats = {
            "codes_downloaded": 0,
            "chapters_processed": 0,
            "search_terms_processed": 0,
            "api_calls_made": 0,
            "start_time": None,
            "end_time": None,
            "errors": [],
        }

    def _setup_logging(self) -> logging.Logger:
        """Setup comprehensive download logging"""
        logger = logging.getLogger("complete_icd10_downloader")
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    async def download_complete_archive(self) -> dict[str, Any]:
        """Download complete ICD-10 diagnostic codes"""
        self.logger.info("Starting complete ICD-10 diagnostic codes download")
        self.logger.info("Target: All ICD-10 codes from NLM Clinical Tables API")
        self.stats["start_time"] = time.time()

        try:
            async with self.base_downloader:
                # Download all ICD-10 codes using the existing comprehensive method
                all_codes = await self.base_downloader.download_all_codes()

                # Validate and normalize codes for medical-mirrors schema compatibility
                validated_codes = self._validate_and_normalize_codes(all_codes)

                # Save complete dataset
                complete_file = await self.save_complete_dataset(validated_codes)

                # Get download stats from base downloader
                base_stats = self.base_downloader.get_download_stats()
                self.stats.update({
                    "codes_downloaded": len(validated_codes),
                    "api_calls_made": base_stats.get("requests_made", 0),
                    "errors": self.stats["errors"] + [str(e) for e in base_stats.get("errors", [])],
                })

                self.stats["end_time"] = time.time()
                duration = self.stats["end_time"] - self.stats["start_time"]

                self.logger.info("✅ Complete ICD-10 download finished!")
                self.logger.info(f"   Codes downloaded: {len(validated_codes)}")
                self.logger.info(f"   API calls made: {self.stats['api_calls_made']}")
                self.logger.info(f"   Duration: {duration/60:.1f} minutes")
                self.logger.info(f"   Complete dataset: {complete_file}")

                return {
                    "status": "success",
                    "codes_downloaded": len(validated_codes),
                    "api_calls": self.stats["api_calls_made"],
                    "duration_minutes": duration / 60,
                    "complete_file": complete_file,
                    "errors": self.stats["errors"],
                }

        except Exception as e:
            self.logger.exception(f"Complete ICD-10 download failed: {e}")
            self.stats["errors"].append(str(e))
            return {
                "status": "failed",
                "error": str(e),
                "partial_stats": self.stats,
            }

    def _validate_and_normalize_codes(self, codes: list[dict]) -> list[dict]:
        """
        Validate and normalize ICD-10 codes for medical-mirrors schema compatibility.

        Maps API response to database column constraints from migration 002 + 004:
        - code: VARCHAR(30) PRIMARY KEY (extended from 20 in migration 004)
        - description: TEXT NOT NULL
        - category: VARCHAR(300) (extended from 200 in migration 004)
        - chapter: VARCHAR(50) (extended from 10 in migration 004)
        - synonyms: JSONB
        - inclusion_notes: JSONB
        - exclusion_notes: JSONB
        - is_billable: BOOLEAN DEFAULT false
        - code_length: INTEGER
        - parent_code: VARCHAR(30)
        - children_codes: JSONB
        - source: VARCHAR(100) (extended from 50 in migration 004)
        - search_text: TEXT
        - last_updated: TIMESTAMP
        - created_at: TIMESTAMP
        """

        validated_codes = []
        self.logger.info(f"Validating and normalizing {len(codes)} ICD-10 codes for database schema")

        for code_data in codes:
            try:
                # Validate required fields
                code = str(code_data.get("code", "")).strip()
                if not code:
                    self.logger.warning("Skipping code with empty code field")
                    continue

                description = str(code_data.get("description", "")).strip()
                if not description:
                    self.logger.warning(f"Skipping code {code} with empty description")
                    continue

                # Apply column length constraints
                code = code[:30]  # VARCHAR(30) constraint
                category = str(code_data.get("category", ""))[:300]  # VARCHAR(300) constraint
                chapter = str(code_data.get("chapter", ""))[:50]  # VARCHAR(50) constraint
                source = str(code_data.get("source", "nlm_clinical_tables"))[:100]  # VARCHAR(100) constraint

                # Handle synonyms as JSONB
                synonyms = code_data.get("synonyms", [])
                if not isinstance(synonyms, list):
                    synonyms = [str(synonyms)] if synonyms else []

                # Determine if code is billable (ICD-10-CM specific logic)
                is_billable = self._determine_billability(code)

                # Calculate code length
                code_length = len(code)

                # Determine parent code (for hierarchical structure)
                parent_code = self._determine_parent_code(code)
                if parent_code:
                    parent_code = parent_code[:30]  # VARCHAR(30) constraint

                # Create search text for full-text search
                search_text = self._create_search_text(code_data)

                # Build normalized code entry
                normalized_code = {
                    "code": code,
                    "description": description,  # TEXT field, no length limit
                    "category": category,
                    "chapter": chapter,
                    "synonyms": synonyms,  # JSONB
                    "inclusion_notes": [],  # JSONB - could be enhanced with API data
                    "exclusion_notes": [],  # JSONB - could be enhanced with API data
                    "is_billable": is_billable,
                    "code_length": code_length,
                    "parent_code": parent_code,
                    "children_codes": [],  # JSONB - could be populated in post-processing
                    "source": source,
                    "search_text": search_text,
                    "last_updated": code_data.get("last_updated"),
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),

                    # Additional metadata for processing
                    "api_total_count": code_data.get("api_total_count", 0),
                    "download_timestamp": time.time(),
                }

                validated_codes.append(normalized_code)

            except Exception as e:
                self.logger.warning(f"Failed to validate code {code_data.get('code', 'unknown')}: {e}")
                self.stats["errors"].append(f"Code validation {code_data.get('code', 'unknown')}: {e}")
                continue

        self.logger.info(f"Validated {len(validated_codes)} ICD-10 codes for database insertion")
        return validated_codes

    def _determine_billability(self, code: str) -> bool:
        """
        Determine if an ICD-10 code is billable.

        ICD-10-CM billable codes are typically:
        - 3-7 characters long
        - Not category headers (which are usually 3 chars)
        - Have specific patterns for billable vs non-billable
        """
        if not code or len(code) < 3:
            return False

        # Category headers (3 characters) are typically not billable
        if len(code) == 3:
            return False

        # Codes with 4+ characters are typically billable
        # This is a simplified heuristic - real determination would need official CMS data
        return len(code) >= 4

    def _determine_parent_code(self, code: str) -> str | None:
        """Determine parent code for hierarchical structure"""
        if not code or len(code) <= 3:
            return None

        # For ICD-10, parent is typically the code with last character removed
        # until we reach the 3-character category
        if len(code) > 3:
            return code[:-1]

        return None

    def _create_search_text(self, code_data: dict) -> str:
        """Create comprehensive search text for full-text search"""
        search_parts = [
            str(code_data.get("code", "")),
            str(code_data.get("description", "")),
            str(code_data.get("category", "")),
            str(code_data.get("chapter", "")),
        ]

        # Add synonyms if available
        synonyms = code_data.get("synonyms", [])
        if isinstance(synonyms, list):
            search_parts.extend([str(s) for s in synonyms])

        return " ".join(search_parts).lower()

    async def save_complete_dataset(self, codes: list[dict]) -> str:
        """Save complete ICD-10 dataset to JSON file for processing"""
        output_file = os.path.join(self.data_dir, "all_icd10_codes_complete.json")

        # Organize codes by chapter for better structure
        codes_by_chapter = {}
        for code in codes:
            chapter = code.get("chapter", "Unknown")
            if chapter not in codes_by_chapter:
                codes_by_chapter[chapter] = []
            codes_by_chapter[chapter].append(code)

        # Prepare metadata
        dataset = {
            "metadata": {
                "total_codes": len(codes),
                "chapters": list(codes_by_chapter.keys()),
                "download_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "api_calls_made": self.stats["api_calls_made"],
                "source": "nlm_clinical_tables",
                "api_base": self.base_downloader.base_url,
                "schema_version": "medical_mirrors_compatible",
                "billable_codes": len([c for c in codes if c.get("is_billable", False)]),
                "non_billable_codes": len([c for c in codes if not c.get("is_billable", False)]),
            },
            "codes_by_chapter": codes_by_chapter,
            "codes": codes,  # Flat list for easier processing
        }

        # Save with proper formatting
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(dataset, f, ensure_ascii=False, default=str)

        self.logger.info(f"Saved complete ICD-10 dataset: {output_file}")
        return output_file

    def get_download_stats(self) -> dict[str, Any]:
        """Get comprehensive download statistics"""
        stats = self.stats.copy()

        if stats["start_time"] and stats["end_time"]:
            duration = stats["end_time"] - stats["start_time"]
            stats["duration_seconds"] = duration
            stats["duration_minutes"] = duration / 60

            if duration > 0:
                stats["codes_per_second"] = stats["codes_downloaded"] / duration
                stats["api_calls_per_minute"] = stats["api_calls_made"] / (duration / 60)

        return stats


def main():
    """Main function for complete ICD-10 download"""
    parser = argparse.ArgumentParser(
        description="Download complete ICD-10 diagnostic codes for offline operation",
        epilog="Uses medical-mirrors configuration for database compatibility",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        help="Directory to store complete ICD-10 data (default: medical-mirrors config)",
    )

    args = parser.parse_args()

    # Create downloader with optional custom data directory
    downloader = CompleteICD10Downloader(custom_data_dir=args.data_dir)

    print(f"\n🏥 Starting complete ICD-10 diagnostic codes download to: {downloader.data_dir}")
    print("⚠️  Target: All ICD-10 codes from NLM Clinical Tables API")
    print("📊 Includes all chapters (A-Z) with comprehensive search coverage")
    print("🔧 Using medical-mirrors config for database compatibility\n")

    # Run download
    result = asyncio.run(downloader.download_complete_archive())

    # Show results
    if isinstance(result, dict) and result.get("status") == "success":
        print("\n✅ ICD-10 download completed successfully!")
        print(f"   Codes downloaded: {result.get('codes_downloaded', 'N/A')}")
        print(f"   Duration: {result.get('duration_minutes', 0):.1f} minutes")
        print(f"   Complete file: {result.get('complete_file', 'N/A')}")
    else:
        print("\n❌ ICD-10 download failed or incomplete")
        if isinstance(result, dict) and "error" in result:
            print(f"   Error: {result['error']}")

    # Show download statistics
    stats = downloader.get_download_stats()
    print("\n📊 Download Statistics:")
    print(f"   API calls made: {stats.get('api_calls_made', 0)}")
    print(f"   Average speed: {stats.get('codes_per_second', 0):.1f} codes/sec")
    print(f"   Errors: {len(stats.get('errors', []))}")

    # Show next steps
    print("\n📋 Next Steps:")
    print("   1. Parse downloaded file: python scripts/parse_downloaded_archives.py icd10")
    print("   2. Or use medical-mirrors API: POST /update/icd10")
    print(f"   3. Files stored in: {downloader.data_dir}")


if __name__ == "__main__":
    main()
