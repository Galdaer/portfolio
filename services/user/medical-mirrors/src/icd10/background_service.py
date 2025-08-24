"""
Background service for automatic ICD-10 codes downloads with smart retry
"""

import argparse
import asyncio
import json
import logging
import signal
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from config import Config

from .smart_downloader import SmartICD10Downloader

logger = logging.getLogger(__name__)


class ICD10BackgroundService:
    """Background service that automatically manages ICD-10 codes downloads"""

    def __init__(self, config: Config | None = None):
        self.config = config or Config()
        self.downloader: SmartICD10Downloader | None = None
        self.service_state_file = Path("/home/intelluxe/database/medical_complete/icd10/service_state.json")

        # Service configuration (more conservative for ICD-10)
        self.check_interval = 600  # 10 minutes between checks
        self.daily_update_hour = 3  # 3 AM daily updates (after billing codes)
        self.max_download_duration = 7200  # 2 hours max per download session

        # Service state
        self.is_running = False
        self.last_full_download = None
        self.last_check = None
        self.shutdown_requested = False

        # Statistics
        self.stats = {
            "service_start_time": None,
            "total_download_sessions": 0,
            "total_codes_downloaded": 0,
            "successful_retries": 0,
            "failed_retries": 0,
            "rate_limit_events": 0,
            "uptime_seconds": 0,
            "largest_successful_download": 0,
            "data_type": "icd10_codes",
        }

        self._load_service_state()
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Setup graceful shutdown signal handlers"""
        for sig in [signal.SIGINT, signal.SIGTERM]:
            signal.signal(sig, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown of ICD-10 service...")
        self.shutdown_requested = True

    def _load_service_state(self):
        """Load service state from persistent storage"""
        try:
            if self.service_state_file.exists():
                with open(self.service_state_file) as f:
                    data = json.load(f)

                self.last_full_download = data.get("last_full_download")
                self.last_check = data.get("last_check")
                self.stats.update(data.get("stats", {}))

                if self.last_full_download:
                    logger.info(f"Last ICD-10 full download: {self.last_full_download}")
                else:
                    logger.info("No previous ICD-10 download history found")

        except Exception as e:
            logger.exception(f"Error loading ICD-10 service state: {e}")

    def _save_service_state(self):
        """Save service state to persistent storage"""
        try:
            self.service_state_file.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "last_full_download": self.last_full_download,
                "last_check": self.last_check,
                "stats": self.stats,
                "saved_at": datetime.now().isoformat(),
                "data_type": "icd10_codes",
            }

            # Write atomically
            temp_file = self.service_state_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(data, f, indent=2, default=str)

            temp_file.replace(self.service_state_file)
            logger.debug("Saved ICD-10 service state")

        except Exception as e:
            logger.exception(f"Error saving ICD-10 service state: {e}")

    async def start_service(self):
        """Start the ICD-10 background service"""
        logger.info("Starting ICD-10 codes background service")

        self.is_running = True
        self.stats["service_start_time"] = datetime.now().isoformat()

        # Initialize downloader
        self.downloader = SmartICD10Downloader()
        await self.downloader.__aenter__()

        try:
            # Run initial download if needed
            if await self._should_run_initial_download():
                logger.info("Running initial ICD-10 download")
                await self._run_download_session("initial")

            # Start main service loop
            await self._service_loop()

        except Exception as e:
            logger.exception(f"Error in ICD-10 service main loop: {e}")
        finally:
            await self._shutdown_service()

    async def _service_loop(self):
        """Main service loop"""
        logger.info(f"Started ICD-10 service loop (checking every {self.check_interval} seconds)")

        while not self.shutdown_requested:
            try:
                datetime.now()

                # Check for retry opportunities
                await self._check_for_retries()

                # Check for daily updates
                await self._check_for_daily_update()

                # Update statistics
                self._update_service_stats()

                # Save state periodically
                self._save_service_state()

                self.last_check = datetime.now().isoformat()

                # Calculate sleep time
                sleep_time = self._calculate_sleep_time()

                # Sleep with periodic wake-up checks for shutdown
                await self._interruptible_sleep(sleep_time)

            except Exception as e:
                logger.exception(f"Error in ICD-10 service loop iteration: {e}")
                await asyncio.sleep(60)  # Sleep a minute on error

    async def _should_run_initial_download(self) -> bool:
        """Determine if we should run an initial ICD-10 download"""
        # Check if we have never downloaded before
        if not self.last_full_download:
            return True

        # Check if last download was more than 30 days ago (ICD-10 updates less frequently)
        try:
            last_download = datetime.fromisoformat(self.last_full_download)
            if datetime.now() - last_download > timedelta(days=30):
                return True
        except Exception:
            return True

        # Check current status
        status = await self.downloader.get_download_status()

        # If we have very few codes (less than 100), run initial download
        if status.get("total_codes_downloaded", 0) < 100:
            return True

        # Check if many sources are incomplete
        progress = status.get("progress", {})
        return progress.get("completed", 0) < progress.get("total_sources", 1) // 2

    async def _check_for_retries(self):
        """Check for and execute ready retries"""
        try:
            status = await self.downloader.get_download_status()
            ready_sources = status.get("ready_for_retry", [])

            if ready_sources:
                logger.info(f"Found {len(ready_sources)} ICD-10 sources ready for retry")

                # Run targeted retry session
                summary = await self.downloader.download_all_icd10_codes(force_fresh=False)

                # Update statistics
                if summary.get("successful_sources", 0) > 0:
                    self.stats["successful_retries"] += summary["successful_sources"]
                    logger.info(f"Successfully retried {summary['successful_sources']} ICD-10 sources")

                if summary.get("failed_sources", 0) > 0:
                    self.stats["failed_retries"] += summary["failed_sources"]

                if summary.get("rate_limited_sources", 0) > 0:
                    self.stats["rate_limit_events"] += summary["rate_limited_sources"]

                current_total = summary.get("total_codes", 0)
                self.stats["total_codes_downloaded"] = max(
                    self.stats["total_codes_downloaded"],
                    current_total,
                )

                # Track largest successful download
                self.stats["largest_successful_download"] = max(self.stats["largest_successful_download"], current_total)

        except Exception as e:
            logger.exception(f"Error checking for ICD-10 retries: {e}")

    async def _check_for_daily_update(self):
        """Check if we should run daily ICD-10 full update"""
        now = datetime.now()

        # Only run daily updates at the scheduled hour
        if now.hour != self.daily_update_hour:
            return

        # Check if we've already run today
        if self.last_full_download:
            try:
                last_download = datetime.fromisoformat(self.last_full_download)
                if last_download.date() == now.date():
                    logger.debug("Daily ICD-10 update already completed today")
                    return
            except Exception:
                pass

        logger.info("Running scheduled daily ICD-10 update")
        await self._run_download_session("daily")

    async def _run_download_session(self, session_type: str):
        """Run a complete ICD-10 download session"""
        logger.info(f"Starting {session_type} ICD-10 download session")
        session_start = datetime.now()

        try:
            # Set timeout for download session (longer for ICD-10)
            summary = await asyncio.wait_for(
                self.downloader.download_all_icd10_codes(force_fresh=(session_type == "initial")),
                timeout=self.max_download_duration,
            )

            # Update statistics
            self.stats["total_download_sessions"] += 1
            current_total = summary.get("total_codes", 0)
            self.stats["total_codes_downloaded"] = current_total
            self.last_full_download = datetime.now().isoformat()

            # Track largest successful download
            self.stats["largest_successful_download"] = max(self.stats["largest_successful_download"], current_total)

            # Log results
            logger.info(f"Completed {session_type} ICD-10 download session: "
                       f"{summary['total_codes']:,} codes from "
                       f"{summary['successful_sources']} sources")

            # Log expected vs actual
            expected_vs_actual = summary.get("expected_vs_actual", {})
            if expected_vs_actual.get("improvement_over_fallback", 0) > 0:
                logger.info(f"Improvement over fallback: +{expected_vs_actual['improvement_over_fallback']:,} codes")

            # Generate session report
            await self._save_session_report(session_type, summary, session_start)

        except TimeoutError:
            logger.exception(f"ICD-10 download session timed out after {self.max_download_duration} seconds")
        except Exception as e:
            logger.exception(f"Error in {session_type} ICD-10 download session: {e}")

    async def _save_session_report(self, session_type: str, summary: dict[str, Any],
                                 session_start: datetime):
        """Save detailed session report"""
        try:
            reports_dir = Path("/home/intelluxe/database/medical_complete/icd10/reports")
            reports_dir.mkdir(parents=True, exist_ok=True)

            # Get detailed code statistics
            code_stats = await self.downloader.get_codes_statistics()

            report = {
                "session_type": session_type,
                "timestamp": session_start.isoformat(),
                "duration_seconds": (datetime.now() - session_start).total_seconds(),
                "data_type": "icd10_codes",
                "summary": summary,
                "code_statistics": code_stats,
                "service_stats": self.stats.copy(),
            }

            report_file = reports_dir / f"session_{session_type}_{session_start.strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, "w") as f:
                json.dump(report, f, indent=2, default=str)

            logger.info(f"Saved ICD-10 session report to {report_file}")

        except Exception as e:
            logger.exception(f"Error saving ICD-10 session report: {e}")

    def _calculate_sleep_time(self) -> int:
        """Calculate adaptive sleep time based on service activity"""
        base_sleep = self.check_interval

        # For ICD-10, we can be more patient since updates are less frequent
        # and downloads are larger

        try:
            # Check if there are sources ready for retry soon
            # If so, we might want to check more frequently
            if hasattr(self, "downloader") and self.downloader:
                # Don't wait for status check, just use base sleep
                pass
        except:
            pass

        return base_sleep

    async def _interruptible_sleep(self, sleep_time: int):
        """Sleep that can be interrupted by shutdown signal"""
        intervals = max(1, sleep_time // 15)  # Check for shutdown every 15 seconds
        interval_sleep = sleep_time / intervals

        for _ in range(intervals):
            if self.shutdown_requested:
                break
            await asyncio.sleep(interval_sleep)

    def _update_service_stats(self):
        """Update service statistics"""
        if self.stats["service_start_time"]:
            try:
                start_time = datetime.fromisoformat(self.stats["service_start_time"])
                self.stats["uptime_seconds"] = int((datetime.now() - start_time).total_seconds())
            except:
                pass

    async def _shutdown_service(self):
        """Graceful service shutdown"""
        logger.info("Shutting down ICD-10 codes background service")

        self.is_running = False

        # Close downloader
        if self.downloader:
            try:
                await self.downloader.__aexit__(None, None, None)
            except Exception as e:
                logger.exception(f"Error closing ICD-10 downloader: {e}")

        # Save final state
        self._save_service_state()

        logger.info("ICD-10 background service shutdown complete")

    async def get_service_status(self) -> dict[str, Any]:
        """Get current service status"""
        status = {
            "is_running": self.is_running,
            "data_type": "icd10_codes",
            "last_full_download": self.last_full_download,
            "last_check": self.last_check,
            "stats": self.stats.copy(),
            "config": {
                "check_interval": self.check_interval,
                "daily_update_hour": self.daily_update_hour,
                "max_download_duration": self.max_download_duration,
            },
        }

        if self.downloader:
            try:
                download_status = await self.downloader.get_download_status()
                status["download_status"] = download_status

                # Add code statistics
                code_stats = await self.downloader.get_codes_statistics()
                status["code_statistics"] = code_stats

            except Exception as e:
                status["download_status_error"] = str(e)

        return status

    async def trigger_immediate_download(self, force_fresh: bool = False) -> dict[str, Any]:
        """Trigger an immediate download (for manual/API use)"""
        if not self.downloader:
            raise RuntimeError("Service not initialized")

        logger.info(f"Triggering immediate ICD-10 download (force_fresh={force_fresh})")
        session_start = datetime.now()

        try:
            summary = await self.downloader.download_all_icd10_codes(force_fresh=force_fresh)

            # Update service statistics
            self.stats["total_download_sessions"] += 1
            current_total = summary.get("total_codes", 0)
            self.stats["total_codes_downloaded"] = current_total

            self.stats["largest_successful_download"] = max(self.stats["largest_successful_download"], current_total)

            # Save session report
            await self._save_session_report("manual", summary, session_start)

            logger.info(f"Manual ICD-10 download completed: {current_total:,} codes")
            return summary

        except Exception as e:
            logger.exception(f"Error in manual ICD-10 download: {e}")
            raise


async def run_service():
    """Run the ICD-10 background service"""
    parser = argparse.ArgumentParser(description="ICD-10 Codes Background Service")
    parser.add_argument("--check-interval", type=int, default=600,
                       help="Interval between checks in seconds (default: 600)")
    parser.add_argument("--daily-hour", type=int, default=3,
                       help="Hour for daily updates (0-23, default: 3)")
    parser.add_argument("--max-duration", type=int, default=7200,
                       help="Max download duration in seconds (default: 7200)")
    parser.add_argument("--log-level", default="INFO",
                       help="Logging level (DEBUG, INFO, WARNING, ERROR)")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("/home/intelluxe/logs/icd10_service.log"),
        ],
    )

    # Create and configure service
    service = ICD10BackgroundService()
    service.check_interval = args.check_interval
    service.daily_update_hour = args.daily_hour
    service.max_download_duration = args.max_duration

    # Run service
    try:
        await service.start_service()
    except KeyboardInterrupt:
        logger.info("ICD-10 service interrupted by user")
    except Exception as e:
        logger.exception(f"ICD-10 service error: {e}")
        sys.exit(1)


async def check_service_status():
    """Check and display service status"""
    try:
        service = ICD10BackgroundService()
        service._load_service_state()

        # Create temporary downloader to get download status
        async with SmartICD10Downloader() as downloader:
            service.downloader = downloader
            status = await service.get_service_status()

        print(json.dumps(status, indent=2, default=str))

    except Exception as e:
        print(f"Error checking ICD-10 service status: {e}")
        sys.exit(1)


async def trigger_manual_download():
    """Trigger a manual download"""
    try:
        service = ICD10BackgroundService()

        async with SmartICD10Downloader() as downloader:
            service.downloader = downloader
            summary = await service.trigger_immediate_download()

        print("Manual ICD-10 download completed:")
        print(json.dumps(summary, indent=2, default=str))

    except Exception as e:
        print(f"Error in manual ICD-10 download: {e}")
        sys.exit(1)


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "status":
            asyncio.run(check_service_status())
        elif sys.argv[1] == "download":
            asyncio.run(trigger_manual_download())
        else:
            print("Usage: icd10_background_service.py [status|download]")
            sys.exit(1)
    else:
        asyncio.run(run_service())


if __name__ == "__main__":
    main()
