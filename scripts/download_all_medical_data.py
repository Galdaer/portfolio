#!/usr/bin/env python3
"""
Master Medical Data Orchestrator
Coordinates complete downloads of all medical data sources for offline database operation

This script orchestrates all 6 medical data sources:
1. PubMed (~220GB) - Medical literature
2. ClinicalTrials.gov (~500MB) - Clinical trials
3. FDA (~22GB) - Drug databases
4. ICD-10 - Diagnostic codes
5. Billing Codes (HCPCS/CPT) - Medical billing
6. Health Information - Topics, exercises, nutrition

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
        print("Make sure medical-mirrors service is properly installed")
        print(f"Looking for modules in: {medical_mirrors_src}")
        sys.exit(1)


class MedicalDataOrchestrator:
    """
    Orchestrates complete medical data downloads across all sources.

    Manages parallel downloads, progress tracking, error handling, and
    coordination between different data sources while respecting API limits.
    """

    def __init__(self, custom_data_dir: str | None = None):
        # Use medical-mirrors Config for consistency
        self.config = Config()
        self.scripts_dir = Path(__file__).parent

        # Allow custom data directory override
        if custom_data_dir:
            self.base_data_dir = custom_data_dir
            os.makedirs(self.base_data_dir, exist_ok=True)
        else:
            self.base_data_dir = self.config.DATA_DIR

        self.logger = self._setup_logging()

        # Define all data sources with their scripts and characteristics
        self.data_sources = {
            "pubmed": {
                "script": "download_full_pubmed.py",
                "size_estimate": "~220GB",
                "description": "Complete PubMed medical literature corpus",
                "priority": 1,  # Start early due to large size
                "parallel_safe": False,  # Large bandwidth usage
                "estimated_hours": 6,
            },
            "fda": {
                "script": "download_full_fda.py",
                "size_estimate": "~22GB",
                "description": "Complete FDA drug databases",
                "priority": 2,  # Start early, moderate size
                "parallel_safe": True,  # Can run with others
                "estimated_hours": 2,
            },
            "clinicaltrials": {
                "script": "download_full_clinicaltrials.py",
                "size_estimate": "~500MB",
                "description": "All ClinicalTrials.gov studies",
                "priority": 3,  # Fast download
                "parallel_safe": True,  # API-based, small size
                "estimated_hours": 0.5,
            },
            "icd10": {
                "script": "download_full_icd10.py",
                "size_estimate": "~50MB",
                "description": "Complete ICD-10 diagnostic codes",
                "priority": 4,  # Fast API download
                "parallel_safe": True,  # API-based
                "estimated_hours": 0.2,
            },
            "billing": {
                "script": "download_full_billing_codes.py",
                "size_estimate": "~30MB",
                "description": "Complete HCPCS/CPT billing codes",
                "priority": 5,  # Fast API download
                "parallel_safe": True,  # API-based
                "estimated_hours": 0.2,
            },
            "health_info": {
                "script": "download_full_health_info.py",
                "size_estimate": "~100MB",
                "description": "Health topics, exercises, nutrition data",
                "priority": 6,  # Depends on API keys
                "parallel_safe": True,  # Multiple APIs
                "estimated_hours": 0.3,
            },
        }

        # Overall statistics
        self.stats = {
            "total_sources": len(self.data_sources),
            "sources_completed": 0,
            "sources_failed": 0,
            "start_time": None,
            "end_time": None,
            "results": {},
            "errors": [],
        }

    def _setup_logging(self) -> logging.Logger:
        """Setup comprehensive orchestration logging"""
        logger = logging.getLogger("medical_data_orchestrator")
        logger.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # File handler for detailed logs
        log_file = os.path.join(self.base_data_dir, "medical_data_download.log")
        file_handler = logging.FileHandler(log_file)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        logger.info(f"Logging to: {log_file}")
        return logger

    def estimate_total_requirements(self) -> dict[str, Any]:
        """Estimate total download requirements"""
        total_size_gb = 220 + 22 + 0.5 + 0.05 + 0.03 + 0.1  # Approximate
        total_hours = sum(source["estimated_hours"] for source in self.data_sources.values())

        return {
            "total_size_gb": total_size_gb,
            "estimated_hours_sequential": total_hours,
            "estimated_hours_parallel": max(6, 2.5),  # Limited by PubMed and some parallel
            "disk_space_required": total_size_gb * 1.2,  # 20% buffer
            "sources_count": len(self.data_sources),
            "large_downloads": ["pubmed", "fda"],
            "api_dependencies": ["icd10", "billing", "health_info"],
            "api_keys_required": {
                "RAPIDAPI_KEY": "ExerciseDB data (optional)",
                "USDA_API_KEY": "USDA nutrition data (optional)",
            },
        }

    async def download_all_sources(self,
                                 selected_sources: list[str] | None = None,
                                 parallel: bool = True,
                                 max_parallel: int = 3) -> dict[str, Any]:
        """Download all or selected medical data sources"""

        # Determine which sources to download
        if selected_sources:
            sources_to_download = {k: v for k, v in self.data_sources.items() if k in selected_sources}
        else:
            sources_to_download = self.data_sources.copy()

        self.logger.info(f"Starting download of {len(sources_to_download)} data sources")
        self.logger.info(f"Parallel downloads: {'enabled' if parallel else 'disabled'}")
        self.logger.info(f"Data directory: {self.base_data_dir}")

        self.stats["start_time"] = time.time()

        try:
            if parallel:
                results = await self._download_parallel(sources_to_download, max_parallel)
            else:
                results = await self._download_sequential(sources_to_download)

            self.stats["end_time"] = time.time()
            duration = self.stats["end_time"] - self.stats["start_time"]

            # Compile final results
            successful = [k for k, v in results.items() if v.get("success", False)]
            failed = [k for k, v in results.items() if not v.get("success", False)]

            self.stats.update({
                "sources_completed": len(successful),
                "sources_failed": len(failed),
                "results": results,
                "duration_hours": duration / 3600,
            })

            self.logger.info("✅ Download orchestration completed!")
            self.logger.info(f"   Successful: {len(successful)}/{len(sources_to_download)}")
            self.logger.info(f"   Failed: {len(failed)}")
            self.logger.info(f"   Total time: {duration/3600:.1f} hours")

            return {
                "status": "completed",
                "successful_sources": successful,
                "failed_sources": failed,
                "total_sources": len(sources_to_download),
                "duration_hours": duration / 3600,
                "results": results,
                "stats": self.stats,
            }

        except Exception as e:
            self.logger.exception(f"Download orchestration failed: {e}")
            self.stats["errors"].append(str(e))
            return {
                "status": "failed",
                "error": str(e),
                "partial_results": self.stats,
            }

    async def _download_sequential(self, sources: dict[str, Any]) -> dict[str, Any]:
        """Download sources sequentially (safer for large downloads)"""
        self.logger.info("Starting sequential downloads")
        results = {}

        # Sort by priority
        sorted_sources = sorted(sources.items(), key=lambda x: x[1]["priority"])

        for source_name, source_info in sorted_sources:
            self.logger.info(f"🚀 Starting {source_name} download ({source_info['size_estimate']})")

            try:
                result = await self._run_download_script(source_name, source_info)
                results[source_name] = result

                if result.get("success", False):
                    self.logger.info(f"✅ {source_name} completed successfully")
                else:
                    self.logger.error(f"❌ {source_name} failed: {result.get('error', 'Unknown error')}")

            except Exception as e:
                self.logger.exception(f"❌ {source_name} download exception: {e}")
                results[source_name] = {"success": False, "error": str(e)}

        return results

    async def _download_parallel(self, sources: dict[str, Any], max_parallel: int) -> dict[str, Any]:
        """Download sources in parallel where safe"""
        self.logger.info(f"Starting parallel downloads (max {max_parallel} concurrent)")

        # Separate large downloads that should run alone vs parallel-safe downloads
        large_sources = {k: v for k, v in sources.items() if not v["parallel_safe"]}
        parallel_sources = {k: v for k, v in sources.items() if v["parallel_safe"]}

        results = {}

        # Run large downloads first, sequentially
        if large_sources:
            self.logger.info(f"Running large downloads sequentially: {list(large_sources.keys())}")
            large_results = await self._download_sequential(large_sources)
            results.update(large_results)

        # Run parallel-safe downloads concurrently
        if parallel_sources:
            self.logger.info(f"Running parallel downloads: {list(parallel_sources.keys())}")

            # Create semaphore to limit concurrent downloads
            semaphore = asyncio.Semaphore(max_parallel)

            async def download_with_semaphore(source_name: str, source_info: dict[str, Any]):
                async with semaphore:
                    return await self._run_download_script(source_name, source_info)

            # Start all parallel downloads
            tasks = [
                download_with_semaphore(name, info)
                for name, info in parallel_sources.items()
            ]

            # Wait for all to complete
            parallel_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for (source_name, _), result in zip(parallel_sources.items(), parallel_results, strict=False):
                if isinstance(result, Exception):
                    self.logger.exception(f"❌ {source_name} parallel download failed")
                    results[source_name] = {"success": False, "error": str(result)}
                else:
                    results[source_name] = result
                    if result.get("success", False):
                        self.logger.info(f"✅ {source_name} parallel download completed")

        return results

    async def _run_download_script(self, source_name: str, source_info: dict[str, Any]) -> dict[str, Any]:
        """Run individual download script"""
        script_path = self.scripts_dir / source_info["script"]

        if not script_path.exists():
            error_msg = f"Download script not found: {script_path}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}

        # Prepare command
        cmd = [
            sys.executable,
            str(script_path),
            "--data-dir", os.path.join(self.base_data_dir, source_name),
        ]

        try:
            self.logger.info(f"Executing: {' '.join(cmd)}")

            # Run script with timeout and capture output
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.scripts_dir,
            )

            # Wait for completion with timeout (very generous for large downloads)
            timeout = source_info["estimated_hours"] * 3600 * 2  # 2x estimated time

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
            except TimeoutError:
                # Kill the process if it takes too long
                process.kill()
                await process.wait()
                msg = f"Download timeout after {timeout/3600:.1f} hours"
                raise Exception(msg)

            # Check return code
            if process.returncode == 0:
                self.logger.info(f"{source_name} script completed successfully")
                return {
                    "success": True,
                    "source": source_name,
                    "script": source_info["script"],
                    "stdout": stdout.decode("utf-8", errors="replace"),
                    "stderr": stderr.decode("utf-8", errors="replace"),
                }
            error_msg = stderr.decode("utf-8", errors="replace")
            self.logger.error(f"{source_name} script failed with exit code {process.returncode}")
            self.logger.error(f"Error output: {error_msg}")
            return {
                "success": False,
                "source": source_name,
                "error": error_msg,
                "exit_code": process.returncode,
            }

        except Exception as e:
            self.logger.exception(f"Failed to run {source_name} download script")
            return {"success": False, "source": source_name, "error": str(e)}

    def save_orchestration_report(self) -> str:
        """Save detailed orchestration report"""
        report_file = os.path.join(self.base_data_dir, "medical_data_download_report.json")

        report = {
            "orchestration_summary": {
                "total_sources": self.stats["total_sources"],
                "sources_completed": self.stats["sources_completed"],
                "sources_failed": self.stats["sources_failed"],
                "duration_hours": self.stats.get("duration_hours", 0),
                "completion_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "data_directory": self.base_data_dir,
            },
            "source_details": self.data_sources,
            "download_results": self.stats.get("results", {}),
            "errors": self.stats["errors"],
            "requirements_estimate": self.estimate_total_requirements(),
            "next_steps": [
                "Parse downloaded data with: python scripts/parse_downloaded_archives.py",
                "Start medical-mirrors service to make data available",
                "Verify data integrity and completeness",
                "Set up periodic incremental updates",
            ],
        }

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        self.logger.info(f"Orchestration report saved: {report_file}")
        return report_file

    def check_prerequisites(self) -> dict[str, Any]:
        """Check system prerequisites for downloads"""
        import psutil

        # Check disk space
        disk_usage = psutil.disk_usage(self.base_data_dir)
        free_space_gb = disk_usage.free / (1024 ** 3)

        requirements = self.estimate_total_requirements()
        required_space_gb = requirements["disk_space_required"]

        # Check required Python packages
        required_packages = ["httpx", "aiohttp", "requests"]
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)

        # Check optional API keys
        api_keys = {
            "RAPIDAPI_KEY": os.getenv("RAPIDAPI_KEY") is not None,
            "USDA_API_KEY": os.getenv("USDA_API_KEY") is not None,
        }

        # Check network connectivity
        network_ok = True
        try:
            import socket
            socket.create_connection(("google.com", 80), 2)
        except OSError:
            network_ok = False

        return {
            "disk_space": {
                "available_gb": free_space_gb,
                "required_gb": required_space_gb,
                "sufficient": free_space_gb >= required_space_gb,
            },
            "packages": {
                "missing": missing_packages,
                "all_available": len(missing_packages) == 0,
            },
            "api_keys": api_keys,
            "network": network_ok,
            "ready": (
                free_space_gb >= required_space_gb and
                len(missing_packages) == 0 and
                network_ok
            ),
        }


def main():
    """Main function for medical data orchestration"""
    parser = argparse.ArgumentParser(
        description="Download complete medical datasets for offline operation",
        epilog="Orchestrates all 6 medical data sources with intelligent parallel processing",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        help="Base directory for all medical data (default: medical-mirrors config)",
    )
    parser.add_argument(
        "--sources",
        nargs="*",
        choices=["pubmed", "fda", "clinicaltrials", "icd10", "billing", "health_info"],
        help="Specific sources to download (default: all)",
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Force sequential downloads (safer for limited bandwidth)",
    )
    parser.add_argument(
        "--max-parallel",
        type=int,
        default=3,
        help="Maximum parallel downloads (default: 3)",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check prerequisites, don't download",
    )
    parser.add_argument(
        "--estimate-only",
        action="store_true",
        help="Only show size estimates, don't download",
    )

    args = parser.parse_args()

    # Create orchestrator
    orchestrator = MedicalDataOrchestrator(custom_data_dir=args.data_dir)

    print("\n🏥 Medical Data Download Orchestrator")
    print(f"📁 Data directory: {orchestrator.base_data_dir}")
    print(f"🗂️  Managing {orchestrator.stats['total_sources']} data sources\n")

    # Handle estimate-only mode
    if args.estimate_only:
        requirements = orchestrator.estimate_total_requirements()
        print("📊 Download Requirements Estimate:")
        print(f"   Total size: ~{requirements['total_size_gb']:.1f} GB")
        print(f"   Estimated time (sequential): {requirements['estimated_hours_sequential']:.1f} hours")
        print(f"   Estimated time (parallel): {requirements['estimated_hours_parallel']:.1f} hours")
        print(f"   Disk space needed: {requirements['disk_space_required']:.1f} GB")
        print(f"   Large downloads: {', '.join(requirements['large_downloads'])}")
        print("\n🔑 Optional API Keys:")
        for key, desc in requirements["api_keys_required"].items():
            status = "✅" if os.getenv(key) else "❌"
            print(f"   {key}: {status} - {desc}")
        return

    # Check prerequisites
    print("🔍 Checking prerequisites...")
    prereqs = orchestrator.check_prerequisites()

    print(f"💾 Disk space: {prereqs['disk_space']['available_gb']:.1f} GB available, "
          f"{prereqs['disk_space']['required_gb']:.1f} GB required "
          f"{'✅' if prereqs['disk_space']['sufficient'] else '❌'}")

    print(f"📦 Python packages: {'✅ All available' if prereqs['packages']['all_available'] else '❌ Missing: ' + ', '.join(prereqs['packages']['missing'])}")

    print(f"🌐 Network: {'✅ Connected' if prereqs['network'] else '❌ No connection'}")

    for key, available in prereqs["api_keys"].items():
        print(f"🔑 {key}: {'✅ Available' if available else '❌ Not set (optional)'}")

    if args.check_only:
        print(f"\n{'✅ Ready to download' if prereqs['ready'] else '❌ Prerequisites not met'}")
        return

    if not prereqs["ready"]:
        print("\n❌ Prerequisites not met. Please resolve issues above.")
        return

    print(f"\n{'✅ Prerequisites check passed' if prereqs['ready'] else '⚠️  Some optional items missing'}")

    # Show what will be downloaded
    sources_to_download = args.sources if args.sources else list(orchestrator.data_sources.keys())
    print(f"\n📋 Sources to download: {', '.join(sources_to_download)}")

    for source in sources_to_download:
        info = orchestrator.data_sources[source]
        print(f"   • {source}: {info['description']} ({info['size_estimate']})")

    download_mode = "sequential" if args.sequential else f"parallel (max {args.max_parallel})"
    print(f"\n🚀 Download mode: {download_mode}")
    print("⚠️  This may take several hours and download ~242GB total")

    # Start downloads
    result = asyncio.run(orchestrator.download_all_sources(
        selected_sources=args.sources,
        parallel=not args.sequential,
        max_parallel=args.max_parallel,
    ))

    # Show final results
    if result.get("status") == "completed":
        successful = result["successful_sources"]
        failed = result["failed_sources"]

        print("\n✅ Download orchestration completed!")
        print(f"   Successful: {len(successful)}/{result['total_sources']}")
        if successful:
            print(f"   ✅ Completed: {', '.join(successful)}")
        if failed:
            print(f"   ❌ Failed: {', '.join(failed)}")
        print(f"   Total time: {result['duration_hours']:.1f} hours")

        # Save comprehensive report
        report_file = orchestrator.save_orchestration_report()
        print(f"\n📊 Detailed report saved: {report_file}")

        # Show next steps
        print("\n📋 Next Steps:")
        print("   1. Parse downloaded data: python scripts/parse_downloaded_archives.py")
        print("   2. Start medical-mirrors service for database access")
        print("   3. Verify data completeness and integrity")
        print("   4. Set up incremental update schedules")

    else:
        print("\n❌ Download orchestration failed")
        if "error" in result:
            print(f"   Error: {result['error']}")


if __name__ == "__main__":
    main()
