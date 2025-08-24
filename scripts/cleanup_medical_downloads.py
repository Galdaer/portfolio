#!/usr/bin/env python3
"""
Medical Data Download Cleanup Script

Safely removes uncompressed duplicate files where compressed versions exist.
Prioritizes disk space recovery while maintaining data integrity.

Safety features:
- Dry-run mode for testing
- Comprehensive logging and audit trail
- File integrity verification
- Backup of deletion list
- Size calculations and reporting
"""

import argparse
import gzip
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


class MedicalDataCleanup:
    """Safe cleanup of medical download duplicates."""

    def __init__(self, data_dir: str, dry_run: bool = True):
        self.data_dir = Path(data_dir)
        self.dry_run = dry_run
        self.logger = self._setup_logging()

        # Stats tracking
        self.stats = {
            "files_analyzed": 0,
            "duplicates_found": 0,
            "space_to_recover": 0,
            "files_to_delete": [],
            "errors": [],
            "directories_processed": 0,
        }

    def _setup_logging(self) -> logging.Logger:
        """Set up comprehensive logging."""
        logger = logging.getLogger("medical_cleanup")
        logger.setLevel(logging.INFO)

        # Create logs directory
        log_dir = self.data_dir / "cleanup_logs"
        log_dir.mkdir(exist_ok=True)

        # File handler
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"cleanup_{timestamp}.log"
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.DEBUG)

        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        logger.addHandler(fh)
        logger.addHandler(ch)

        mode = "DRY-RUN" if self.dry_run else "EXECUTION"
        logger.info(f"Medical data cleanup started - Mode: {mode}")
        logger.info(f"Target directory: {self.data_dir}")

        return logger

    def find_duplicate_files(self, directory: Path) -> list[tuple[Path, Path, int]]:
        """
        Find uncompressed files that have compressed counterparts.

        Returns:
            List of (uncompressed_file, compressed_file, size_to_recover)
        """
        duplicates = []

        if not directory.exists():
            self.logger.warning(f"Directory does not exist: {directory}")
            return duplicates

        self.logger.info(f"Scanning directory: {directory}")

        try:
            # Find all files in directory
            all_files = list(directory.rglob("*"))
            uncompressed_files = [f for f in all_files if f.is_file() and not self._is_compressed(f)]

            self.stats["files_analyzed"] += len(all_files)

            for uncompressed in uncompressed_files:
                compressed_variants = self._find_compressed_variants(uncompressed)

                if compressed_variants:
                    # Choose the best compressed variant (smallest)
                    best_compressed = min(compressed_variants, key=lambda x: x.stat().st_size)
                    file_size = uncompressed.stat().st_size

                    duplicates.append((uncompressed, best_compressed, file_size))
                    self.logger.debug(
                        f"Duplicate found: {uncompressed.name} "
                        f"({self._format_size(file_size)}) -> {best_compressed.name}",
                    )

        except Exception as e:
            error_msg = f"Error scanning {directory}: {str(e)}"
            self.logger.exception(error_msg)
            self.stats["errors"].append(error_msg)

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

        # Common compression patterns
        patterns_to_check = [
            f"{base_name}.gz",
            f"{base_name}.zip",
            f"{base_name}.bz2",
            f"{base_name}.xz",
        ]

        for pattern in patterns_to_check:
            compressed_path = parent_dir / pattern
            if compressed_path.exists() and compressed_path.is_file():
                variants.append(compressed_path)

        return variants

    def verify_compressed_integrity(self, compressed_file: Path) -> bool:
        """Verify that compressed file is readable."""
        try:
            if compressed_file.suffix == ".gz":
                with gzip.open(compressed_file, "rt", encoding="utf-8", errors="ignore") as f:
                    # Try to read first few lines
                    for i, _line in enumerate(f):
                        if i >= 5:  # Read first 5 lines
                            break
                return True
            # For other formats, just check if file exists and has size > 0
            return compressed_file.stat().st_size > 0
        except Exception as e:
            self.logger.exception(f"Integrity check failed for {compressed_file}: {e}")
            return False

    def cleanup_directory(self, directory: Path) -> dict[str, Any]:
        """Clean up a specific directory."""
        self.logger.info(f"Processing directory: {directory}")

        duplicates = self.find_duplicate_files(directory)
        directory_stats = {
            "directory": str(directory),
            "duplicates_found": len(duplicates),
            "space_to_recover": 0,
            "files_deleted": 0,
            "errors": [],
        }

        for uncompressed, compressed, size in duplicates:
            # Verify compressed file integrity
            if not self.verify_compressed_integrity(compressed):
                error_msg = f"Skipping {uncompressed} - compressed version failed integrity check"
                self.logger.warning(error_msg)
                directory_stats["errors"].append(error_msg)
                continue

            directory_stats["space_to_recover"] += size
            self.stats["space_to_recover"] += size
            self.stats["duplicates_found"] += 1

            file_info = {
                "uncompressed": str(uncompressed),
                "compressed": str(compressed),
                "size": size,
                "size_formatted": self._format_size(size),
            }
            self.stats["files_to_delete"].append(file_info)

            if not self.dry_run:
                try:
                    uncompressed.unlink()
                    directory_stats["files_deleted"] += 1
                    self.logger.info(f"Deleted: {uncompressed} ({self._format_size(size)} recovered)")
                except Exception as e:
                    error_msg = f"Failed to delete {uncompressed}: {e}"
                    self.logger.exception(error_msg)
                    directory_stats["errors"].append(error_msg)
                    self.stats["errors"].append(error_msg)

        self.stats["directories_processed"] += 1
        return directory_stats

    def cleanup_all(self) -> dict[str, Any]:
        """Clean up all medical data directories."""
        self.logger.info("Starting comprehensive cleanup")

        # Priority directories (largest impact first)
        directories_to_clean = [
            self.data_dir / "pubmed",           # Largest impact
            self.data_dir / "clinicaltrials",   # Second largest
            self.data_dir / "fda",              # FDA data
            self.data_dir / "enhanced_drug_sources",
            self.data_dir / "enhanced_drug_data",
            self.data_dir / "billing",
            self.data_dir / "icd10",
            self.data_dir / "health_info",
            self.data_dir / "rxclass",
            self.data_dir / "trials",
        ]

        results = []
        for directory in directories_to_clean:
            if directory.exists():
                try:
                    result = self.cleanup_directory(directory)
                    results.append(result)
                except Exception as e:
                    error_msg = f"Failed to process directory {directory}: {e}"
                    self.logger.exception(error_msg)
                    self.stats["errors"].append(error_msg)

        # Generate comprehensive report
        report = self._generate_report(results)
        self._save_report(report)

        return report

    def _generate_report(self, directory_results: list[dict]) -> dict[str, Any]:
        """Generate comprehensive cleanup report."""
        return {
            "cleanup_summary": {
                "mode": "dry_run" if self.dry_run else "execution",
                "timestamp": datetime.now().isoformat(),
                "data_directory": str(self.data_dir),
                "total_directories_processed": self.stats["directories_processed"],
                "total_files_analyzed": self.stats["files_analyzed"],
                "total_duplicates_found": self.stats["duplicates_found"],
                "total_space_to_recover": self.stats["space_to_recover"],
                "total_space_formatted": self._format_size(self.stats["space_to_recover"]),
                "total_errors": len(self.stats["errors"]),
            },
            "directory_details": directory_results,
            "files_to_delete": self.stats["files_to_delete"][:100],  # Limit for readability
            "errors": self.stats["errors"],
            "recommendations": self._generate_recommendations(),
        }

    def _generate_recommendations(self) -> list[str]:
        """Generate cleanup recommendations."""
        recommendations = []

        if self.stats["space_to_recover"] > 10 * 1024**3:  # > 10GB
            recommendations.append("Significant space recovery possible (>10GB)")

        if len(self.stats["errors"]) > 0:
            recommendations.append("Review errors before proceeding with cleanup")

        if self.dry_run:
            recommendations.append("Run without --dry-run to execute actual cleanup")

        recommendations.extend([
            "Verify compressed files are accessible after cleanup",
            "Consider setting up automated cleanup for future downloads",
            "Monitor disk space regularly during large downloads",
        ])

        return recommendations

    def _save_report(self, report: dict[str, Any]) -> Path:
        """Save cleanup report to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        mode = "dry_run" if self.dry_run else "executed"
        report_file = self.data_dir / f"cleanup_report_{mode}_{timestamp}.json"

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, default=str)

        self.logger.info(f"Cleanup report saved: {report_file}")
        return report_file

    def _format_size(self, size_bytes: int) -> str:
        """Format size in human-readable format."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Medical Data Download Cleanup")
    parser.add_argument(
        "data_dir",
        help="Path to medical data directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Preview changes without executing (default: True)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute actual cleanup (overrides --dry-run)",
    )
    parser.add_argument(
        "--directory",
        help="Clean up specific directory only",
    )

    args = parser.parse_args()

    # Determine execution mode
    dry_run = not args.execute

    if not dry_run:
        print("WARNING: This will permanently delete files!")
        response = input("Are you sure you want to continue? (yes/no): ")
        if response.lower() != "yes":
            print("Cleanup cancelled.")
            sys.exit(0)

    # Initialize cleanup
    cleanup = MedicalDataCleanup(args.data_dir, dry_run=dry_run)

    try:
        if args.directory:
            # Clean specific directory
            target_dir = Path(args.data_dir) / args.directory
            result = cleanup.cleanup_directory(target_dir)
            print(f"\nCleanup completed for {target_dir}")
            print(f"Space to recover: {cleanup._format_size(result['space_to_recover'])}")
        else:
            # Clean all directories
            report = cleanup.cleanup_all()
            summary = report["cleanup_summary"]

            print("\nCleanup completed!")
            print(f"Mode: {summary['mode'].upper()}")
            print(f"Directories processed: {summary['total_directories_processed']}")
            print(f"Files analyzed: {summary['total_files_analyzed']}")
            print(f"Duplicates found: {summary['total_duplicates_found']}")
            print(f"Space to recover: {summary['total_space_formatted']}")

            if summary["total_errors"] > 0:
                print(f"Errors encountered: {summary['total_errors']}")
                print("Check the log file for details.")

    except KeyboardInterrupt:
        print("\nCleanup interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Cleanup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
