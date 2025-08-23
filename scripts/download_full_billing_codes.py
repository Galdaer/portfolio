#!/usr/bin/env python3
"""
Complete Medical Billing Codes Archive Downloader
Downloads complete HCPCS/CPT billing codes for offline database operation

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
from typing import Any, Dict, List

import aiohttp
from aiohttp import ClientError

# Type checking imports
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from medical_mirrors_types import Config, BillingCodesDownloader
else:
    # Runtime imports - add medical-mirrors to Python path
    medical_mirrors_src = str(Path(__file__).parent.parent / "services/user/medical-mirrors/src")
    if medical_mirrors_src not in sys.path:
        sys.path.insert(0, medical_mirrors_src)

    try:
        from config import Config
        from billing_codes.downloader import BillingCodesDownloader
    except ImportError as e:
        print(f"Failed to import medical-mirrors modules: {e}")
        print(f"Make sure medical-mirrors service is properly installed")
        print(f"Looking for modules in: {medical_mirrors_src}")
        sys.exit(1)


class CompleteBillingCodesDownloader:
    """
    Downloads complete medical billing codes for local database caching.
    
    Based on the existing medical-mirrors BillingCodesDownloader but enhanced
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
            self.data_dir = self.config.get_billing_codes_data_dir()
            
        self.logger = self._setup_logging()
        
        # Use the existing BillingCodesDownloader as base
        self.base_downloader = BillingCodesDownloader(self.config)
        
        # Download statistics
        self.stats = {
            "hcpcs_codes_downloaded": 0,
            "cpt_codes_downloaded": 0,
            "total_codes_downloaded": 0,
            "categories_processed": 0,
            "api_calls_made": 0,
            "start_time": None,
            "end_time": None,
            "errors": []
        }

    def _setup_logging(self) -> logging.Logger:
        """Setup comprehensive download logging"""
        logger = logging.getLogger("complete_billing_codes_downloader")
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    async def download_complete_archive(self) -> dict[str, Any]:
        """Download complete medical billing codes"""
        self.logger.info("Starting complete medical billing codes download")
        self.logger.info("Target: All HCPCS codes + available CPT codes from NLM Clinical Tables API")
        self.stats["start_time"] = time.time()

        try:
            async with self.base_downloader:
                # Download all billing codes using the existing comprehensive method
                all_codes = await self.base_downloader.download_all_codes()
                
                # Validate and normalize codes for medical-mirrors schema compatibility
                validated_codes = self._validate_and_normalize_codes(all_codes)
                
                # Save complete dataset
                complete_file = await self.save_complete_dataset(validated_codes)
                
                # Get download stats from base downloader
                base_stats = self.base_downloader.get_download_stats()
                self.stats.update({
                    "total_codes_downloaded": len(validated_codes),
                    "hcpcs_codes_downloaded": base_stats.get("hcpcs_codes_downloaded", 0),
                    "cpt_codes_downloaded": base_stats.get("cpt_codes_downloaded", 0),
                    "api_calls_made": base_stats.get("requests_made", 0),
                    "errors": self.stats["errors"] + [str(e) for e in base_stats.get("errors", [])]
                })
                
                self.stats["end_time"] = time.time()
                duration = self.stats["end_time"] - self.stats["start_time"]
                
                self.logger.info(f"✅ Complete billing codes download finished!")
                self.logger.info(f"   Total codes downloaded: {len(validated_codes)}")
                self.logger.info(f"   HCPCS codes: {self.stats['hcpcs_codes_downloaded']}")
                self.logger.info(f"   CPT codes: {self.stats['cpt_codes_downloaded']}")
                self.logger.info(f"   API calls made: {self.stats['api_calls_made']}")
                self.logger.info(f"   Duration: {duration/60:.1f} minutes")
                self.logger.info(f"   Complete dataset: {complete_file}")
                
                return {
                    "status": "success",
                    "total_codes_downloaded": len(validated_codes),
                    "hcpcs_codes": self.stats["hcpcs_codes_downloaded"],
                    "cpt_codes": self.stats["cpt_codes_downloaded"],
                    "api_calls": self.stats["api_calls_made"],
                    "duration_minutes": duration / 60,
                    "complete_file": complete_file,
                    "errors": self.stats["errors"]
                }

        except Exception as e:
            self.logger.exception(f"Complete billing codes download failed: {e}")
            self.stats["errors"].append(str(e))
            return {
                "status": "failed",
                "error": str(e),
                "partial_stats": self.stats
            }

    def _validate_and_normalize_codes(self, codes: List[Dict]) -> List[Dict]:
        """
        Validate and normalize billing codes for medical-mirrors schema compatibility.
        
        Maps API response to database column constraints from migration 002 + 004:
        - code: VARCHAR(30) PRIMARY KEY (extended from 20 in migration 004)
        - short_description: TEXT
        - long_description: TEXT
        - description: TEXT (computed from short/long)
        - code_type: VARCHAR(50) (extended from 20 in migration 004)
        - category: VARCHAR(300) (extended from 200 in migration 004)
        - coverage_notes: TEXT
        - effective_date: DATE
        - termination_date: DATE
        - is_active: BOOLEAN DEFAULT true
        - modifier_required: BOOLEAN DEFAULT false
        - gender_specific: VARCHAR(100) (extended from 20 in migration 004)
        - age_specific: VARCHAR(100) (extended from 20 in migration 004)
        - bilateral_indicator: BOOLEAN DEFAULT false
        - source: VARCHAR(100) (extended from 50 in migration 004)
        - search_text: TEXT
        - last_updated: TIMESTAMP
        - created_at: TIMESTAMP
        """
        
        validated_codes = []
        self.logger.info(f"Validating and normalizing {len(codes)} billing codes for database schema")
        
        for code_data in codes:
            try:
                # Validate required fields
                code = str(code_data.get("code", "")).strip()
                if not code:
                    self.logger.warning("Skipping code with empty code field")
                    continue
                
                # Apply column length constraints
                code = code[:30]  # VARCHAR(30) constraint
                code_type = str(code_data.get("code_type", "HCPCS"))[:50]  # VARCHAR(50) constraint
                category = str(code_data.get("category", ""))[:300]  # VARCHAR(300) constraint
                source = str(code_data.get("source", "nlm_clinical_tables"))[:100]  # VARCHAR(100) constraint
                gender_specific = str(code_data.get("gender_specific", ""))[:100]  # VARCHAR(100) constraint
                age_specific = str(code_data.get("age_specific", ""))[:100]  # VARCHAR(100) constraint
                
                # Handle description fields
                short_description = str(code_data.get("short_description", "")).strip()
                long_description = str(code_data.get("long_description", "")).strip()
                
                # Create primary description field (prefer long over short)
                description = long_description if long_description else short_description
                if not description:
                    self.logger.warning(f"Skipping code {code} with no description")
                    continue
                
                # Determine if code is active (assume true unless specified otherwise)
                is_active = True
                termination_date = code_data.get("termination_date")
                if termination_date:
                    # If there's a termination date, code might be inactive
                    # This would need real date parsing for full accuracy
                    pass
                
                # Determine billing properties based on code type and content
                modifier_required = self._determine_modifier_required(code, code_type)
                bilateral_indicator = self._determine_bilateral_indicator(code, description, code_type)
                
                # Create search text for full-text search
                search_text = self._create_search_text(code_data)
                
                # Build normalized code entry
                normalized_code = {
                    "code": code,
                    "short_description": short_description,
                    "long_description": long_description,
                    "description": description,
                    "code_type": code_type,
                    "category": category,
                    "coverage_notes": str(code_data.get("coverage_notes", "")),
                    "effective_date": code_data.get("effective_date"),  # DATE field
                    "termination_date": termination_date,  # DATE field
                    "is_active": is_active,
                    "modifier_required": modifier_required,
                    "gender_specific": gender_specific,
                    "age_specific": age_specific,
                    "bilateral_indicator": bilateral_indicator,
                    "source": source,
                    "search_text": search_text,
                    "last_updated": code_data.get("last_updated"),
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    
                    # Additional metadata for processing
                    "api_total_count": code_data.get("api_total_count", 0),
                    "download_timestamp": time.time()
                }
                
                validated_codes.append(normalized_code)
                
            except Exception as e:
                self.logger.warning(f"Failed to validate code {code_data.get('code', 'unknown')}: {e}")
                self.stats["errors"].append(f"Code validation {code_data.get('code', 'unknown')}: {e}")
                continue
        
        self.logger.info(f"Validated {len(validated_codes)} billing codes for database insertion")
        return validated_codes

    def _determine_modifier_required(self, code: str, code_type: str) -> bool:
        """
        Determine if a billing code typically requires modifiers.
        
        This is a simplified heuristic - real determination would need 
        comprehensive CMS/AMA modifier rules.
        """
        if not code or not code_type:
            return False
        
        # Some HCPCS codes commonly require modifiers
        if code_type.upper() == "HCPCS":
            # E codes (DME) often require modifiers
            if code.startswith("E"):
                return True
            # L codes (orthotics/prosthetics) often require modifiers
            if code.startswith("L"):
                return True
        
        # CPT surgery codes often require modifiers
        if code_type.upper() == "CPT":
            try:
                code_num = int(code)
                # Surgery codes (10000-69999) often require modifiers
                if 10000 <= code_num <= 69999:
                    return True
            except ValueError:
                pass
        
        return False

    def _determine_bilateral_indicator(self, code: str, description: str, code_type: str) -> bool:
        """
        Determine if a code has bilateral indicator (applies to both sides of body).
        """
        if not description:
            return False
        
        # Look for bilateral keywords in description
        bilateral_keywords = ["bilateral", "both", "each", "per side", "left and right"]
        description_lower = description.lower()
        
        return any(keyword in description_lower for keyword in bilateral_keywords)

    def _create_search_text(self, code_data: dict) -> str:
        """Create comprehensive search text for full-text search"""
        search_parts = [
            str(code_data.get("code", "")),
            str(code_data.get("short_description", "")),
            str(code_data.get("long_description", "")),
            str(code_data.get("category", "")),
            str(code_data.get("code_type", "")),
            str(code_data.get("coverage_notes", ""))
        ]
        
        return " ".join(search_parts).lower()

    async def save_complete_dataset(self, codes: List[Dict]) -> str:
        """Save complete billing codes dataset to JSON file for processing"""
        output_file = os.path.join(self.data_dir, "all_billing_codes_complete.json")
        
        # Organize codes by type and category for better structure
        codes_by_type = {"HCPCS": [], "CPT": [], "Other": []}
        codes_by_category = {}
        
        for code in codes:
            code_type = code.get("code_type", "Other").upper()
            if code_type in codes_by_type:
                codes_by_type[code_type].append(code)
            else:
                codes_by_type["Other"].append(code)
            
            category = code.get("category", "Uncategorized")
            if category not in codes_by_category:
                codes_by_category[category] = []
            codes_by_category[category].append(code)
        
        # Calculate statistics
        active_codes = len([c for c in codes if c.get("is_active", True)])
        modifier_required_codes = len([c for c in codes if c.get("modifier_required", False)])
        bilateral_codes = len([c for c in codes if c.get("bilateral_indicator", False)])
        
        # Prepare metadata
        dataset = {
            "metadata": {
                "total_codes": len(codes),
                "code_types": {k: len(v) for k, v in codes_by_type.items() if v},
                "categories": list(codes_by_category.keys()),
                "active_codes": active_codes,
                "inactive_codes": len(codes) - active_codes,
                "modifier_required_codes": modifier_required_codes,
                "bilateral_codes": bilateral_codes,
                "download_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "api_calls_made": self.stats["api_calls_made"],
                "source": "nlm_clinical_tables",
                "api_bases": [self.base_downloader.hcpcs_url],
                "schema_version": "medical_mirrors_compatible"
            },
            "codes_by_type": codes_by_type,
            "codes_by_category": codes_by_category,
            "codes": codes  # Flat list for easier processing
        }
        
        # Save with proper formatting
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False, default=str)
        
        self.logger.info(f"Saved complete billing codes dataset: {output_file}")
        return output_file

    def get_download_stats(self) -> dict[str, Any]:
        """Get comprehensive download statistics"""
        stats = self.stats.copy()
        
        if stats["start_time"] and stats["end_time"]:
            duration = stats["end_time"] - stats["start_time"]
            stats["duration_seconds"] = duration
            stats["duration_minutes"] = duration / 60
            
            if duration > 0:
                stats["codes_per_second"] = stats["total_codes_downloaded"] / duration
                stats["api_calls_per_minute"] = stats["api_calls_made"] / (duration / 60)
        
        return stats


def main():
    """Main function for complete billing codes download"""
    parser = argparse.ArgumentParser(
        description="Download complete medical billing codes for offline operation",
        epilog="Uses medical-mirrors configuration for database compatibility"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        help="Directory to store complete billing codes data (default: medical-mirrors config)"
    )
    parser.add_argument(
        "--hcpcs-only",
        action="store_true",
        help="Download only HCPCS codes (most comprehensive)"
    )

    args = parser.parse_args()

    # Create downloader with optional custom data directory
    downloader = CompleteBillingCodesDownloader(custom_data_dir=args.data_dir)

    print(f"\n🏦 Starting complete medical billing codes download to: {downloader.data_dir}")
    print("⚠️  Target: All HCPCS codes + available CPT codes from NLM Clinical Tables API")
    print("📊 Includes all HCPCS categories (A-V) with comprehensive coverage")
    print("🔧 Using medical-mirrors config for database compatibility")
    if args.hcpcs_only:
        print("🎯 HCPCS-only mode (CPT codes limited by copyright)\n")
    else:
        print("🎯 Complete mode (HCPCS + available CPT codes)\n")

    # Run download
    result = asyncio.run(downloader.download_complete_archive())

    # Show results
    if isinstance(result, dict) and result.get("status") == "success":
        print("\n✅ Billing codes download completed successfully!")
        print(f"   Total codes downloaded: {result.get('total_codes_downloaded', 'N/A')}")
        print(f"   HCPCS codes: {result.get('hcpcs_codes', 'N/A')}")
        print(f"   CPT codes: {result.get('cpt_codes', 'N/A')}")
        print(f"   Duration: {result.get('duration_minutes', 0):.1f} minutes")
        print(f"   Complete file: {result.get('complete_file', 'N/A')}")
    else:
        print("\n❌ Billing codes download failed or incomplete")
        if isinstance(result, dict) and "error" in result:
            print(f"   Error: {result['error']}")

    # Show download statistics
    stats = downloader.get_download_stats()
    print(f"\n📊 Download Statistics:")
    print(f"   API calls made: {stats.get('api_calls_made', 0)}")
    print(f"   Average speed: {stats.get('codes_per_second', 0):.1f} codes/sec")
    print(f"   Errors: {len(stats.get('errors', []))}")
    
    # Show next steps
    print(f"\n📋 Next Steps:")
    print(f"   1. Parse downloaded file: python scripts/parse_downloaded_archives.py billing")
    print(f"   2. Or use medical-mirrors API: POST /update/billing")
    print(f"   3. Files stored in: {downloader.data_dir}")
    
    # Show notes about CPT limitations
    if result.get("cpt_codes", 0) == 0:
        print(f"\n💡 Note: CPT codes are limited by AMA copyright restrictions")
        print(f"   Full CPT codes require licensing from the American Medical Association")
        print(f"   HCPCS codes (government published) are freely available and comprehensive")


if __name__ == "__main__":
    main()