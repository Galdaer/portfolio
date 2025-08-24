#!/usr/bin/env python3
"""
Disk Space Monitor for Medical Data Downloads

Monitors disk usage and provides alerts/cleanup recommendations
for the medical data download system.
"""

import argparse
import json
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


class DiskSpaceMonitor:
    """Monitor disk usage for medical data directories."""

    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.logger = self._setup_logging()

    def _setup_logging(self) -> logging.Logger:
        """Set up logging."""
        logger = logging.getLogger("disk_monitor")
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def get_disk_usage(self) -> dict[str, Any]:
        """Get current disk usage statistics."""
        total, used, free = shutil.disk_usage(self.data_dir)

        return {
            "timestamp": datetime.now().isoformat(),
            "total_bytes": total,
            "used_bytes": used,
            "free_bytes": free,
            "total_gb": round(total / (1024**3), 2),
            "used_gb": round(used / (1024**3), 2),
            "free_gb": round(free / (1024**3), 2),
            "usage_percent": round((used / total) * 100, 2),
        }

    def get_directory_sizes(self) -> dict[str, dict[str, Any]]:
        """Get size information for each medical data directory."""
        directories = [
            "pubmed", "clinicaltrials", "fda", "enhanced_drug_sources",
            "enhanced_drug_data", "billing", "icd10", "health_info",
            "rxclass", "trials",
        ]

        sizes = {}
        for dir_name in directories:
            dir_path = self.data_dir / dir_name
            if dir_path.exists():
                size_bytes = self._get_directory_size(dir_path)
                sizes[dir_name] = {
                    "size_bytes": size_bytes,
                    "size_gb": round(size_bytes / (1024**3), 2),
                    "path": str(dir_path),
                }
            else:
                sizes[dir_name] = {
                    "size_bytes": 0,
                    "size_gb": 0,
                    "path": str(dir_path),
                    "note": "Directory does not exist",
                }

        return sizes

    def _get_directory_size(self, directory: Path) -> int:
        """Calculate total size of directory."""
        total = 0
        try:
            for file in directory.rglob("*"):
                if file.is_file():
                    total += file.stat().st_size
        except (OSError, PermissionError) as e:
            self.logger.warning(f"Could not access {directory}: {e}")
        return total

    def check_cleanup_opportunities(self) -> dict[str, Any]:
        """Check for potential cleanup opportunities."""
        opportunities = {
            "duplicate_uncompressed": [],
            "large_files": [],
            "old_temp_files": [],
        }

        # Check for uncompressed files with compressed counterparts
        for directory in ["pubmed", "clinicaltrials", "fda"]:
            dir_path = self.data_dir / directory
            if dir_path.exists():
                duplicates = self._find_duplicate_files(dir_path)
                if duplicates:
                    opportunities["duplicate_uncompressed"].extend(duplicates)

        # Check for unusually large files
        for file in self.data_dir.rglob("*"):
            if file.is_file():
                size = file.stat().st_size
                # Flag files larger than 1GB
                if size > 1024**3:
                    opportunities["large_files"].append({
                        "path": str(file),
                        "size_gb": round(size / (1024**3), 2),
                    })

        return opportunities

    def _find_duplicate_files(self, directory: Path) -> list[dict[str, Any]]:
        """Find uncompressed files that have compressed versions."""
        duplicates = []

        try:
            uncompressed_files = [f for f in directory.rglob("*")
                                if f.is_file() and not self._is_compressed(f)]

            for uncompressed in uncompressed_files:
                compressed_variants = self._find_compressed_variants(uncompressed)
                if compressed_variants:
                    duplicates.append({
                        "uncompressed": str(uncompressed),
                        "compressed": str(compressed_variants[0]),
                        "size_mb": round(uncompressed.stat().st_size / (1024**2), 2),
                    })
        except Exception as e:
            self.logger.exception(f"Error checking duplicates in {directory}: {e}")

        return duplicates

    def _is_compressed(self, file_path: Path) -> bool:
        """Check if file is compressed."""
        compressed_extensions = {".gz", ".zip", ".bz2", ".xz", ".tar", ".tgz", ".tbz2"}
        return file_path.suffix.lower() in compressed_extensions

    def _find_compressed_variants(self, uncompressed_file: Path) -> list[Path]:
        """Find compressed versions of an uncompressed file."""
        variants = []
        base_name = uncompressed_file.name
        parent_dir = uncompressed_file.parent

        for ext in [".gz", ".zip", ".bz2", ".xz"]:
            compressed_path = parent_dir / f"{base_name}{ext}"
            if compressed_path.exists():
                variants.append(compressed_path)

        return variants

    def generate_report(self) -> dict[str, Any]:
        """Generate comprehensive disk usage report."""
        disk_usage = self.get_disk_usage()
        directory_sizes = self.get_directory_sizes()
        cleanup_opportunities = self.check_cleanup_opportunities()

        # Calculate total medical data size
        total_medical_data = sum(d.get("size_bytes", 0) for d in directory_sizes.values())

        return {
            "report_timestamp": datetime.now().isoformat(),
            "disk_usage": disk_usage,
            "directory_sizes": directory_sizes,
            "total_medical_data_gb": round(total_medical_data / (1024**3), 2),
            "cleanup_opportunities": cleanup_opportunities,
            "recommendations": self._generate_recommendations(
                disk_usage, directory_sizes, cleanup_opportunities,
            ),
        }


    def _generate_recommendations(self, disk_usage: dict, directory_sizes: dict,
                                 cleanup_opportunities: dict) -> list[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # Disk space warnings
        if disk_usage["usage_percent"] > 90:
            recommendations.append("⚠️  CRITICAL: Disk usage over 90% - immediate cleanup required")
        elif disk_usage["usage_percent"] > 80:
            recommendations.append("⚠️  WARNING: Disk usage over 80% - consider cleanup")
        elif disk_usage["usage_percent"] > 70:
            recommendations.append("ℹ️  INFO: Disk usage over 70% - monitor closely")

        # Cleanup opportunities
        duplicate_count = len(cleanup_opportunities.get("duplicate_uncompressed", []))
        if duplicate_count > 0:
            total_duplicate_size = sum(d.get("size_mb", 0)
                                     for d in cleanup_opportunities["duplicate_uncompressed"])
            recommendations.append(
                f"🧹 {duplicate_count} duplicate files found - "
                f"potential {total_duplicate_size:.1f}MB savings",
            )

        large_files = cleanup_opportunities.get("large_files", [])
        if large_files:
            recommendations.append(f"📊 {len(large_files)} large files detected - review if necessary")

        # Directory-specific recommendations
        pubmed_size = directory_sizes.get("pubmed", {}).get("size_gb", 0)
        if pubmed_size > 200:
            recommendations.append("📚 PubMed directory is large - consider periodic cleanup")

        # General recommendations
        recommendations.extend([
            "🔄 Run cleanup script monthly to maintain optimal storage",
            "📈 Monitor disk usage during large downloads",
            "💾 Consider setting up automated backups of compressed data",
        ])

        return recommendations

    def save_report(self, report: dict[str, Any]) -> Path:
        """Save disk usage report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.data_dir / f"disk_usage_report_{timestamp}.json"

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, default=str)

        self.logger.info(f"Disk usage report saved: {report_file}")
        return report_file


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Medical Data Disk Space Monitor")
    parser.add_argument(
        "data_dir",
        help="Path to medical data directory",
        default="/home/intelluxe/database/medical_complete",
        nargs="?",
    )
    parser.add_argument(
        "--save-report",
        action="store_true",
        help="Save detailed report to file",
    )

    args = parser.parse_args()

    monitor = DiskSpaceMonitor(args.data_dir)

    try:
        report = monitor.generate_report()

        # Print summary
        disk = report["disk_usage"]
        print(f"Disk Usage Report - {report['report_timestamp']}")
        print("=" * 60)
        print(f"Total Space: {disk['total_gb']:.1f} GB")
        print(f"Used Space:  {disk['used_gb']:.1f} GB ({disk['usage_percent']:.1f}%)")
        print(f"Free Space:  {disk['free_gb']:.1f} GB")
        print(f"Medical Data: {report['total_medical_data_gb']:.1f} GB")
        print()

        # Directory breakdown
        print("Directory Sizes:")
        print("-" * 30)
        for name, info in report["directory_sizes"].items():
            if info.get("size_gb", 0) > 0:
                print(f"{name:20} {info['size_gb']:8.1f} GB")
        print()

        # Recommendations
        if report["recommendations"]:
            print("Recommendations:")
            print("-" * 30)
            for rec in report["recommendations"]:
                print(f"• {rec}")

        if args.save_report:
            report_file = monitor.save_report(report)
            print(f"\nDetailed report saved: {report_file}")

    except Exception as e:
        print(f"Error generating disk usage report: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
