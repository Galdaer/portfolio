#!/usr/bin/env python3
"""
Medical Data Download Monitor
Real-time monitoring and auto-recovery for overnight medical data downloads

Features:
- Real-time progress tracking for all data sources
- Automatic retry on failures with exponential backoff
- Bandwidth and ETA calculations
- Log analysis and error detection
- Auto-restart capabilities
- Status dashboard display
"""

import asyncio
import json
import logging
import os
import signal
import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Progress tracking imports


class MedicalDataMonitor:
    """Monitor and manage medical data downloads with auto-recovery"""

    def __init__(self, data_dir: str = "/home/intelluxe/database/medical_complete"):
        self.data_dir = Path(data_dir)
        self.scripts_dir = Path(__file__).parent

        # Data sources to monitor
        self.sources = {
            "pubmed": {
                "script": "smart_pubmed_download.py",
                "size_estimate_gb": 220,
                "priority": 1,
            },
            "fda": {
                "script": "smart_fda_download.py",
                "size_estimate_gb": 22,
                "priority": 2,
            },
            "clinicaltrials": {
                "script": "smart_clinicaltrials_download.py",
                "size_estimate_gb": 0.5,
                "priority": 3,
            },
            "icd10": {
                "script": "smart_icd10_download.py",
                "size_estimate_gb": 0.05,
                "priority": 4,
            },
            "billing": {
                "script": "smart_billing_download.py",
                "size_estimate_gb": 0.03,
                "priority": 5,
            },
            "health_info": {
                "script": "smart_health_info_download.py",
                "size_estimate_gb": 0.1,
                "priority": 6,
            },
        }

        # Monitoring state
        self.start_time = None
        self.running_processes = {}  # source -> subprocess
        self.process_stats = {}  # source -> stats dict
        self.failed_sources = set()
        self.completed_sources = set()
        self.total_downloaded_gb = 0

        # Auto-recovery settings
        self.max_retries = 3
        self.retry_delay = 300  # 5 minutes base delay
        self.retry_counts = {}  # source -> retry count

        # Shutdown handling
        self.shutdown_requested = False
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        self.logger = self._setup_logging()

    def _setup_logging(self) -> logging.Logger:
        """Setup comprehensive monitoring logging"""
        logger = logging.getLogger("medical_data_monitor")
        logger.setLevel(logging.INFO)

        # Console handler with colors
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%H:%M:%S",
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # File handler for detailed logs
        log_file = self.data_dir / "monitor.log"
        file_handler = logging.FileHandler(log_file)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        return logger

    def _handle_shutdown(self, signum, frame):
        """Handle graceful shutdown"""
        self.logger.info(f"Received signal {signum} - initiating graceful shutdown")
        self.shutdown_requested = True

    async def start_monitoring(self, sources: list[str] | None = None,
                             parallel: bool = True, max_parallel: int = 3):
        """Start monitoring medical data downloads"""
        self.start_time = datetime.now()
        sources_to_monitor = sources or list(self.sources.keys())

        self.logger.info("🏥 Starting Medical Data Download Monitor")
        self.logger.info(f"📁 Data directory: {self.data_dir}")
        self.logger.info(f"🗂️  Sources to monitor: {', '.join(sources_to_monitor)}")
        self.logger.info(f"🔄 Parallel downloads: {'enabled' if parallel else 'disabled'}")

        try:
            if parallel:
                await self._monitor_parallel(sources_to_monitor, max_parallel)
            else:
                await self._monitor_sequential(sources_to_monitor)
        except KeyboardInterrupt:
            self.logger.info("Monitor interrupted by user")
        except Exception as e:
            self.logger.exception(f"Monitor failed: {e}")
        finally:
            await self._cleanup_processes()
            self._generate_final_report()

    async def _monitor_parallel(self, sources: list[str], max_parallel: int):
        """Monitor parallel downloads with intelligent scheduling"""

        # Sort by priority and size (large downloads first)
        sorted_sources = sorted(sources, key=lambda x: (
            self.sources[x]["priority"],
            -self.sources[x]["size_estimate_gb"],
        ))

        # Start large downloads first (PubMed, FDA)
        large_sources = [s for s in sorted_sources if self.sources[s]["size_estimate_gb"] > 1]
        small_sources = [s for s in sorted_sources if self.sources[s]["size_estimate_gb"] <= 1]

        # Start large downloads sequentially
        for source in large_sources:
            if self.shutdown_requested:
                break
            await self._start_source_download(source)
            await asyncio.sleep(30)  # Stagger start times

        # Start small downloads in parallel
        semaphore = asyncio.Semaphore(max_parallel)

        async def start_small_download(source):
            async with semaphore:
                await self._start_source_download(source)

        # Start small downloads
        small_tasks = [start_small_download(source) for source in small_sources]
        if small_tasks:
            await asyncio.gather(*small_tasks, return_exceptions=True)

        # Monitor all running processes
        await self._monitor_all_processes()

    async def _monitor_sequential(self, sources: list[str]):
        """Monitor sequential downloads"""
        sorted_sources = sorted(sources, key=lambda x: self.sources[x]["priority"])

        for source in sorted_sources:
            if self.shutdown_requested:
                break

            self.logger.info(f"🚀 Starting {source} download")
            await self._start_source_download(source)
            await self._monitor_source_until_complete(source)

            # Brief pause between downloads
            if not self.shutdown_requested:
                await asyncio.sleep(10)

    async def _start_source_download(self, source: str):
        """Start download for a specific source"""
        if source in self.running_processes:
            self.logger.warning(f"{source} download already running")
            return

        script_path = self.scripts_dir / self.sources[source]["script"]
        source_data_dir = self.data_dir / source
        source_data_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            sys.executable,
            str(script_path),
            "download",
            "--data-dir", str(source_data_dir),
            "--verbose",
        ]

        try:
            self.logger.info(f"Starting {source}: {' '.join(cmd)}")

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.scripts_dir,
            )

            self.running_processes[source] = process
            self.process_stats[source] = {
                "start_time": datetime.now(),
                "status": "running",
                "progress": 0,
                "estimated_size_gb": self.sources[source]["size_estimate_gb"],
            }

            self.logger.info(f"✅ {source} download started (PID: {process.pid})")

        except Exception as e:
            self.logger.exception(f"❌ Failed to start {source}: {e}")
            self.failed_sources.add(source)

    async def _monitor_all_processes(self):
        """Monitor all running processes until completion"""
        while self.running_processes and not self.shutdown_requested:
            await self._update_progress()
            await self._check_failed_processes()
            await self._display_dashboard()

            # Check if any processes completed
            completed_this_cycle = []
            for source, process in self.running_processes.items():
                if process.returncode is not None:
                    completed_this_cycle.append(source)

            for source in completed_this_cycle:
                await self._handle_process_completion(source)

            await asyncio.sleep(10)  # Update every 10 seconds

        self.logger.info("All downloads completed or stopped")

    async def _monitor_source_until_complete(self, source: str):
        """Monitor a single source until completion"""
        if source not in self.running_processes:
            return

        process = self.running_processes[source]

        while process.returncode is None and not self.shutdown_requested:
            await self._update_source_progress(source)
            await asyncio.sleep(5)

        await self._handle_process_completion(source)

    async def _update_progress(self):
        """Update progress for all running downloads"""
        for source in list(self.running_processes.keys()):
            await self._update_source_progress(source)

    async def _update_source_progress(self, source: str):
        """Update progress for a specific source"""
        if source not in self.process_stats:
            return

        source_dir = self.data_dir / source
        stats = self.process_stats[source]

        # Check directory size
        if source_dir.exists():
            total_size = sum(f.stat().st_size for f in source_dir.rglob("*") if f.is_file())
            size_gb = total_size / (1024**3)
            stats["current_size_gb"] = size_gb

            # Estimate progress based on size
            estimated_size = stats["estimated_size_gb"]
            if estimated_size > 0:
                progress = min(100, (size_gb / estimated_size) * 100)
                stats["progress"] = progress

        # Check for state files to get more accurate progress
        state_patterns = [
            f"{source}_download_state.json",
            f"{source}_download_errors.json",
        ]

        for pattern in state_patterns:
            state_file = source_dir / pattern
            if state_file.exists():
                try:
                    with open(state_file) as f:
                        state_data = json.load(f)

                    if "completion_time" in state_data:
                        stats["status"] = "completed"
                        stats["completion_time"] = state_data["completion_time"]
                    elif "error_message" in state_data:
                        stats["status"] = "error"
                        stats["error"] = state_data["error_message"]

                except Exception as e:
                    self.logger.debug(f"Failed to read state file {state_file}: {e}")

    async def _check_failed_processes(self):
        """Check for failed processes and implement retry logic"""
        failed_this_cycle = []

        for source, process in self.running_processes.items():
            if process.returncode is not None and process.returncode != 0:
                failed_this_cycle.append(source)

        for source in failed_this_cycle:
            await self._handle_failed_process(source)

    async def _handle_failed_process(self, source: str):
        """Handle a failed process with retry logic"""
        if source not in self.retry_counts:
            self.retry_counts[source] = 0

        self.retry_counts[source] += 1
        retry_count = self.retry_counts[source]

        self.logger.error(f"❌ {source} download failed (attempt {retry_count})")

        if retry_count <= self.max_retries:
            # Exponential backoff
            delay = self.retry_delay * (2 ** (retry_count - 1))
            self.logger.info(f"🔄 Retrying {source} in {delay} seconds")

            # Remove from running processes
            if source in self.running_processes:
                del self.running_processes[source]

            # Schedule retry
            asyncio.create_task(self._retry_after_delay(source, delay))
        else:
            self.logger.error(f"🚫 {source} exceeded max retries - marking as failed")
            self.failed_sources.add(source)
            if source in self.running_processes:
                del self.running_processes[source]

    async def _retry_after_delay(self, source: str, delay: int):
        """Retry a source after a delay"""
        await asyncio.sleep(delay)
        if not self.shutdown_requested:
            self.logger.info(f"🔄 Retrying {source} download")
            await self._start_source_download(source)

    async def _handle_process_completion(self, source: str):
        """Handle successful process completion"""
        if source not in self.running_processes:
            return

        process = self.running_processes[source]

        if process.returncode == 0:
            self.logger.info(f"✅ {source} download completed successfully")
            self.completed_sources.add(source)

            # Update final stats
            if source in self.process_stats:
                stats = self.process_stats[source]
                stats["status"] = "completed"
                stats["completion_time"] = datetime.now()

                # Add to total downloaded
                current_size = stats.get("current_size_gb", 0)
                self.total_downloaded_gb += current_size
        else:
            await self._handle_failed_process(source)
            return

        # Remove from running processes
        del self.running_processes[source]

    async def _display_dashboard(self):
        """Display real-time dashboard"""
        os.system("clear" if os.name == "posix" else "cls")

        print("🏥 Medical Data Download Monitor")
        print("=" * 60)

        # Overall progress
        total_sources = len(self.sources)
        completed_count = len(self.completed_sources)
        running_count = len(self.running_processes)
        failed_count = len(self.failed_sources)

        print(f"📊 Overall Progress: {completed_count}/{total_sources} completed")
        print(f"🔄 Running: {running_count} | ✅ Completed: {completed_count} | ❌ Failed: {failed_count}")
        print(f"💾 Total Downloaded: {self.total_downloaded_gb:.1f} GB")

        if self.start_time:
            elapsed = datetime.now() - self.start_time
            print(f"⏱️  Elapsed Time: {elapsed}")

        print("-" * 60)

        # Individual source status
        for source in self.sources:
            status_char = "🔄" if source in self.running_processes else "✅" if source in self.completed_sources else "❌" if source in self.failed_sources else "⏸️"

            if source in self.process_stats:
                stats = self.process_stats[source]
                progress = stats.get("progress", 0)
                current_size = stats.get("current_size_gb", 0)
                estimated_size = stats.get("estimated_size_gb", 0)

                print(f"{status_char} {source:15} {progress:5.1f}% ({current_size:.1f}/{estimated_size:.1f} GB)")
            else:
                print(f"{status_char} {source:15} Waiting...")

        print("-" * 60)
        print("Press Ctrl+C to stop monitoring")

    async def _cleanup_processes(self):
        """Clean up running processes"""
        if not self.running_processes:
            return

        self.logger.info("Cleaning up running processes...")

        for source, process in self.running_processes.items():
            if process.returncode is None:
                self.logger.info(f"Terminating {source} download")
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=10)
                except TimeoutError:
                    self.logger.warning(f"Force killing {source} download")
                    process.kill()

    def _generate_final_report(self):
        """Generate final monitoring report"""
        end_time = datetime.now()
        total_duration = end_time - self.start_time if self.start_time else timedelta(0)

        report = {
            "monitor_session": {
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "end_time": end_time.isoformat(),
                "total_duration_hours": total_duration.total_seconds() / 3600,
                "total_downloaded_gb": self.total_downloaded_gb,
            },
            "sources": {
                "completed": list(self.completed_sources),
                "failed": list(self.failed_sources),
                "retry_counts": self.retry_counts,
            },
            "process_stats": self.process_stats,
        }

        report_file = self.data_dir / "monitor_report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, default=str)

        self.logger.info(f"📊 Final report saved: {report_file}")

        # Print summary
        print("\n" + "=" * 60)
        print("🏥 Medical Data Download Monitor - Final Report")
        print("=" * 60)
        print(f"⏱️  Total Duration: {total_duration}")
        print(f"✅ Completed: {len(self.completed_sources)} sources")
        print(f"❌ Failed: {len(self.failed_sources)} sources")
        print(f"💾 Total Downloaded: {self.total_downloaded_gb:.1f} GB")

        if self.completed_sources:
            print(f"✅ Successful: {', '.join(self.completed_sources)}")
        if self.failed_sources:
            print(f"❌ Failed: {', '.join(self.failed_sources)}")


async def main():
    """Main entry point for medical data monitor"""
    import argparse

    parser = argparse.ArgumentParser(description="Medical Data Download Monitor")
    parser.add_argument("--data-dir", type=str,
                       default="/home/intelluxe/database/medical_complete",
                       help="Base data directory")
    parser.add_argument("--sources", nargs="*",
                       choices=["pubmed", "fda", "clinicaltrials", "icd10", "billing", "health_info"],
                       help="Specific sources to monitor (default: all)")
    parser.add_argument("--sequential", action="store_true",
                       help="Monitor sequential downloads (not parallel)")
    parser.add_argument("--max-parallel", type=int, default=3,
                       help="Maximum parallel downloads to monitor")

    args = parser.parse_args()

    monitor = MedicalDataMonitor(data_dir=args.data_dir)

    await monitor.start_monitoring(
        sources=args.sources,
        parallel=not args.sequential,
        max_parallel=args.max_parallel,
    )


if __name__ == "__main__":
    asyncio.run(main())
