"""
Background service for automatic billing codes downloads with smart retry
"""

import asyncio
import json
import logging
import signal
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
import argparse

from .smart_downloader import SmartBillingCodesDownloader
from config import Config

logger = logging.getLogger(__name__)


class BillingCodesBackgroundService:
    """Background service that automatically manages billing codes downloads"""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.downloader: Optional[SmartBillingCodesDownloader] = None
        self.service_state_file = Path("/home/intelluxe/database/medical_complete/billing/service_state.json")
        
        # Service configuration
        self.check_interval = 300  # 5 minutes between checks
        self.daily_update_hour = 2  # 2 AM daily updates
        self.max_download_duration = 3600 * 4  # 4 hours max per download session
        
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
            "uptime_seconds": 0
        }
        
        self._load_service_state()
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Setup graceful shutdown signal handlers"""
        for sig in [signal.SIGINT, signal.SIGTERM]:
            signal.signal(sig, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_requested = True
    
    def _load_service_state(self):
        """Load service state from persistent storage"""
        try:
            if self.service_state_file.exists():
                with open(self.service_state_file, 'r') as f:
                    data = json.load(f)
                    
                self.last_full_download = data.get("last_full_download")
                self.last_check = data.get("last_check") 
                self.stats.update(data.get("stats", {}))
                
                if self.last_full_download:
                    logger.info(f"Last full download: {self.last_full_download}")
                else:
                    logger.info("No previous download history found")
                    
        except Exception as e:
            logger.error(f"Error loading service state: {e}")
    
    def _save_service_state(self):
        """Save service state to persistent storage"""
        try:
            self.service_state_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "last_full_download": self.last_full_download,
                "last_check": self.last_check,
                "stats": self.stats,
                "saved_at": datetime.now().isoformat()
            }
            
            # Write atomically
            temp_file = self.service_state_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            temp_file.replace(self.service_state_file)
            logger.debug("Saved service state")
            
        except Exception as e:
            logger.error(f"Error saving service state: {e}")
    
    async def start_service(self):
        """Start the background service"""
        logger.info("Starting billing codes background service")
        
        self.is_running = True
        self.stats["service_start_time"] = datetime.now().isoformat()
        
        # Initialize downloader
        self.downloader = SmartBillingCodesDownloader()
        await self.downloader.__aenter__()
        
        try:
            # Run initial download if needed
            if await self._should_run_initial_download():
                logger.info("Running initial download")
                await self._run_download_session("initial")
            
            # Start main service loop
            await self._service_loop()
            
        except Exception as e:
            logger.error(f"Error in service main loop: {e}")
        finally:
            await self._shutdown_service()
    
    async def _service_loop(self):
        """Main service loop"""
        logger.info(f"Started service loop (checking every {self.check_interval} seconds)")
        
        while not self.shutdown_requested:
            try:
                loop_start = datetime.now()
                
                # Check for retry opportunities
                await self._check_for_retries()
                
                # Check for daily updates
                await self._check_for_daily_update()
                
                # Update statistics
                self._update_service_stats()
                
                # Save state periodically
                self._save_service_state()
                
                self.last_check = datetime.now().isoformat()
                
                # Calculate sleep time (adaptive based on activity)
                sleep_time = self._calculate_sleep_time()
                
                # Sleep with periodic wake-up checks for shutdown
                await self._interruptible_sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Error in service loop iteration: {e}")
                await asyncio.sleep(60)  # Sleep a minute on error
    
    async def _should_run_initial_download(self) -> bool:
        """Determine if we should run an initial download"""
        # Check if we have never downloaded before
        if not self.last_full_download:
            return True
        
        # Check if last download was more than 7 days ago
        try:
            last_download = datetime.fromisoformat(self.last_full_download)
            if datetime.now() - last_download > timedelta(days=7):
                return True
        except Exception:
            return True
        
        # Check current status
        status = await self.downloader.get_download_status()
        
        # If we have very few codes, run initial download
        if status.get("total_codes_downloaded", 0) < 50:
            return True
        
        # Check if many sources are incomplete
        progress = status.get("progress", {})
        if progress.get("completed", 0) < progress.get("total_sources", 1) // 2:
            return True
        
        return False
    
    async def _check_for_retries(self):
        """Check for and execute ready retries"""
        try:
            status = await self.downloader.get_download_status()
            ready_sources = status.get("ready_for_retry", [])
            
            if ready_sources:
                logger.info(f"Found {len(ready_sources)} sources ready for retry")
                
                # Run targeted retry session
                summary = await self.downloader.download_all_billing_codes(force_fresh=False)
                
                # Update statistics
                if summary.get("successful_sources", 0) > 0:
                    self.stats["successful_retries"] += summary["successful_sources"]
                    logger.info(f"Successfully retried {summary['successful_sources']} sources")
                
                if summary.get("failed_sources", 0) > 0:
                    self.stats["failed_retries"] += summary["failed_sources"]
                
                if summary.get("rate_limited_sources", 0) > 0:
                    self.stats["rate_limit_events"] += summary["rate_limited_sources"]
                
                self.stats["total_codes_downloaded"] = max(
                    self.stats["total_codes_downloaded"], 
                    summary.get("total_codes", 0)
                )
                
        except Exception as e:
            logger.error(f"Error checking for retries: {e}")
    
    async def _check_for_daily_update(self):
        """Check if we should run daily full update"""
        now = datetime.now()
        
        # Only run daily updates at the scheduled hour
        if now.hour != self.daily_update_hour:
            return
        
        # Check if we've already run today
        if self.last_full_download:
            try:
                last_download = datetime.fromisoformat(self.last_full_download)
                if last_download.date() == now.date():
                    logger.debug("Daily update already completed today")
                    return
            except Exception:
                pass
        
        logger.info("Running scheduled daily update")
        await self._run_download_session("daily")
    
    async def _run_download_session(self, session_type: str):
        """Run a complete download session"""
        logger.info(f"Starting {session_type} download session")
        session_start = datetime.now()
        
        try:
            # Set timeout for download session
            summary = await asyncio.wait_for(
                self.downloader.download_all_billing_codes(force_fresh=(session_type == "initial")),
                timeout=self.max_download_duration
            )
            
            # Update statistics
            self.stats["total_download_sessions"] += 1
            self.stats["total_codes_downloaded"] = summary.get("total_codes", 0)
            self.last_full_download = datetime.now().isoformat()
            
            # Log results
            logger.info(f"Completed {session_type} download session: "
                       f"{summary['total_codes']} codes from "
                       f"{summary['successful_sources']} sources")
            
            # Generate session report
            await self._save_session_report(session_type, summary, session_start)
            
        except asyncio.TimeoutError:
            logger.error(f"Download session timed out after {self.max_download_duration} seconds")
        except Exception as e:
            logger.error(f"Error in {session_type} download session: {e}")
    
    async def _save_session_report(self, session_type: str, summary: Dict[str, Any], 
                                 session_start: datetime):
        """Save detailed session report"""
        try:
            reports_dir = Path("/home/intelluxe/database/medical_complete/billing/reports")
            reports_dir.mkdir(parents=True, exist_ok=True)
            
            report = {
                "session_type": session_type,
                "timestamp": session_start.isoformat(),
                "duration_seconds": (datetime.now() - session_start).total_seconds(),
                "summary": summary,
                "service_stats": self.stats.copy()
            }
            
            report_file = reports_dir / f"session_{session_type}_{session_start.strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info(f"Saved session report to {report_file}")
            
        except Exception as e:
            logger.error(f"Error saving session report: {e}")
    
    def _calculate_sleep_time(self) -> int:
        """Calculate adaptive sleep time based on service activity"""
        base_sleep = self.check_interval
        
        # Check current download activity
        if hasattr(self, 'downloader') and self.downloader:
            try:
                # If there are sources ready for retry soon, check more frequently
                loop = asyncio.get_event_loop()
                status_task = loop.create_task(self.downloader.get_download_status())
                # Don't wait for this, just use base sleep if we can't get status quickly
                return base_sleep
            except:
                pass
        
        return base_sleep
    
    async def _interruptible_sleep(self, sleep_time: int):
        """Sleep that can be interrupted by shutdown signal"""
        intervals = max(1, sleep_time // 10)  # Check for shutdown every 10% of sleep time
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
        logger.info("Shutting down billing codes background service")
        
        self.is_running = False
        
        # Close downloader
        if self.downloader:
            try:
                await self.downloader.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error closing downloader: {e}")
        
        # Save final state
        self._save_service_state()
        
        logger.info("Background service shutdown complete")
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get current service status"""
        status = {
            "is_running": self.is_running,
            "last_full_download": self.last_full_download,
            "last_check": self.last_check,
            "stats": self.stats.copy(),
            "config": {
                "check_interval": self.check_interval,
                "daily_update_hour": self.daily_update_hour,
                "max_download_duration": self.max_download_duration
            }
        }
        
        if self.downloader:
            try:
                download_status = await self.downloader.get_download_status()
                status["download_status"] = download_status
            except Exception as e:
                status["download_status_error"] = str(e)
        
        return status


async def run_service():
    """Run the background service"""
    parser = argparse.ArgumentParser(description="Billing Codes Background Service")
    parser.add_argument("--check-interval", type=int, default=300, 
                       help="Interval between checks in seconds (default: 300)")
    parser.add_argument("--daily-hour", type=int, default=2,
                       help="Hour for daily updates (0-23, default: 2)")
    parser.add_argument("--max-duration", type=int, default=14400,
                       help="Max download duration in seconds (default: 14400)")
    parser.add_argument("--log-level", default="INFO",
                       help="Logging level (DEBUG, INFO, WARNING, ERROR)")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('/home/intelluxe/logs/billing_codes_service.log')
        ]
    )
    
    # Create and configure service
    service = BillingCodesBackgroundService()
    service.check_interval = args.check_interval
    service.daily_update_hour = args.daily_hour
    service.max_download_duration = args.max_duration
    
    # Run service
    try:
        await service.start_service()
    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
    except Exception as e:
        logger.error(f"Service error: {e}")
        sys.exit(1)


async def check_service_status():
    """Check and display service status"""
    try:
        service = BillingCodesBackgroundService()
        service._load_service_state()
        
        # Create temporary downloader to get download status
        async with SmartBillingCodesDownloader() as downloader:
            service.downloader = downloader
            status = await service.get_service_status()
        
        print(json.dumps(status, indent=2, default=str))
        
    except Exception as e:
        print(f"Error checking service status: {e}")
        sys.exit(1)


def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        asyncio.run(check_service_status())
    else:
        asyncio.run(run_service())


if __name__ == "__main__":
    main()