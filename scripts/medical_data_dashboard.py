#!/usr/bin/env python3
"""
Medical Data Processing Dashboard

Comprehensive real-time dashboard for medical-mirrors parallel processing.
Uses the new monitoring API endpoints for detailed insights.

Features:
- Real-time processing status
- File processing progress
- System resource monitoring
- Error tracking and analysis
- Processing rate calculation and ETAs
- Interactive terminal dashboard

Usage:
    python medical_data_dashboard.py                    # Interactive dashboard
    python medical_data_dashboard.py --once             # Single snapshot
    python medical_data_dashboard.py --json             # JSON output
    python medical_data_dashboard.py --compact          # Compact view
    python medical_data_dashboard.py --api-url URL      # Custom API URL
"""

import argparse
import json
import os
import signal
import sqlite3
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("Warning: requests library not available. Some features may be limited.")

@dataclass
class ProcessingMetrics:
    """Comprehensive processing metrics for a data source"""
    source: str
    current_count: int
    target_count: int
    completion_percent: float
    status: str
    processing_rate: float = 0.0  # records per second
    eta_minutes: int | None = None
    files_total: int = 0
    files_processed: int = 0
    recent_errors: int = 0
    last_updated: datetime = None

class MedicalDataDashboard:
    """Comprehensive medical data processing dashboard"""

    def __init__(self, api_url: str = "http://localhost:8081", refresh_interval: int = 30):
        self.api_url = api_url.rstrip("/")
        self.refresh_interval = refresh_interval
        self.db_path = Path("/tmp/medical_dashboard.db")
        self.historical_data = {}
        self.start_time = datetime.now()

        # Initialize local database for rate calculations
        self.init_database()

        # Setup signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)

    def init_database(self):
        """Initialize SQLite database for historical data tracking"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processing_history (
                    timestamp TEXT,
                    source TEXT,
                    count INTEGER,
                    completion_percent REAL,
                    status TEXT,
                    PRIMARY KEY (timestamp, source)
                )
            """)

    def signal_handler(self, sig, frame):
        """Handle Ctrl+C gracefully"""
        print("\n\n🛑 Dashboard stopped by user")
        print(f"📊 Session duration: {datetime.now() - self.start_time}")
        sys.exit(0)

    def fetch_api_data(self, endpoint: str) -> dict[str, Any] | None:
        """Fetch data from API endpoint with error handling"""
        if not HAS_REQUESTS:
            return None

        try:
            response = requests.get(f"{self.api_url}/{endpoint}", timeout=10)
            if response.status_code == 200:
                return response.json()
            print(f"Warning: API endpoint {endpoint} returned {response.status_code}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Warning: Failed to fetch {endpoint}: {e}")
            return None

    def calculate_processing_rates(self, current_data: dict[str, Any]) -> dict[str, float]:
        """Calculate processing rates based on historical data"""
        rates = {}
        timestamp = datetime.now()

        if "sources" not in current_data:
            return rates

        # Store current data in database
        with sqlite3.connect(self.db_path) as conn:
            for source, data in current_data["sources"].items():
                conn.execute("""
                    INSERT OR REPLACE INTO processing_history
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    timestamp.isoformat(),
                    source,
                    data.get("current_count", 0),
                    data.get("completion_percent", 0),
                    data.get("status", "unknown"),
                ))

        # Calculate rates based on recent history
        cutoff_time = timestamp - timedelta(minutes=5)  # Look at last 5 minutes

        with sqlite3.connect(self.db_path) as conn:
            for source in current_data["sources"]:
                cursor = conn.execute("""
                    SELECT timestamp, count FROM processing_history
                    WHERE source = ? AND timestamp > ?
                    ORDER BY timestamp ASC
                """, (source, cutoff_time.isoformat()))

                history = cursor.fetchall()

                if len(history) >= 2:
                    # Calculate rate from oldest to newest in time window
                    first_time = datetime.fromisoformat(history[0][0])
                    last_time = datetime.fromisoformat(history[-1][0])
                    first_count = history[0][1]
                    last_count = history[-1][1]

                    time_diff = (last_time - first_time).total_seconds()
                    if time_diff > 0:
                        rates[source] = (last_count - first_count) / time_diff
                    else:
                        rates[source] = 0.0
                else:
                    rates[source] = 0.0

        return rates

    def calculate_eta(self, current_count: int, target_count: int, rate: float) -> int | None:
        """Calculate ETA in minutes"""
        if rate <= 0 or current_count >= target_count:
            return None

        remaining = target_count - current_count
        eta_seconds = remaining / rate

        # Cap at reasonable maximum (30 days)
        if eta_seconds > 2592000:  # 30 days in seconds
            return None

        return int(eta_seconds / 60)

    def format_eta(self, eta_minutes: int | None) -> str:
        """Format ETA in human readable format"""
        if not eta_minutes:
            return "N/A"

        if eta_minutes < 60:
            return f"{eta_minutes}m"
        if eta_minutes < 1440:  # Less than 24 hours
            hours = eta_minutes // 60
            minutes = eta_minutes % 60
            return f"{hours}h {minutes}m"
        days = eta_minutes // 1440
        hours = (eta_minutes % 1440) // 60
        return f"{days}d {hours}h"

    def format_rate(self, rate: float) -> str:
        """Format processing rate with appropriate units"""
        if rate < 1:
            return f"{rate:.2f}/sec"
        if rate < 60:
            return f"{rate:.1f}/sec"
        if rate < 3600:
            return f"{rate/60:.1f}/min"
        return f"{rate/3600:.1f}/hr"

    def get_comprehensive_data(self) -> dict[str, Any]:
        """Fetch all monitoring data from API endpoints"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "api_status": "offline",
            "database_counts": {},
            "processing_status": {},
            "file_progress": {},
            "system_resources": {},
            "error_summary": {},
            "calculated_rates": {},
            "health_status": "unknown",
        }

        # Try to get comprehensive dashboard data first
        dashboard_data = self.fetch_api_data("monitor/dashboard")
        if dashboard_data:
            data.update(dashboard_data)
            data["api_status"] = "online"

            # Calculate processing rates
            if "processing_status" in dashboard_data:
                rates = self.calculate_processing_rates(dashboard_data["processing_status"])
                data["calculated_rates"] = rates

                # Add ETAs to processing status
                for source, source_data in data["processing_status"].get("sources", {}).items():
                    rate = rates.get(source, 0.0)
                    eta = self.calculate_eta(
                        source_data.get("current_count", 0),
                        source_data.get("target_count", 0),
                        rate,
                    )
                    source_data["processing_rate_per_sec"] = rate
                    source_data["eta_minutes"] = eta
                    source_data["eta_human"] = self.format_eta(eta)

        else:
            # Fallback to individual endpoints
            endpoints = [
                "database/counts",
                "monitor/processing-status",
                "monitor/file-progress",
                "monitor/system-resources",
                "monitor/error-summary",
            ]

            for endpoint in endpoints:
                endpoint_data = self.fetch_api_data(endpoint)
                if endpoint_data:
                    key = endpoint.split("/")[-1].replace("-", "_")
                    data[key] = endpoint_data
                    data["api_status"] = "partial"

        return data

    def print_compact_dashboard(self, data: dict[str, Any]):
        """Print compact dashboard view"""
        os.system("clear")

        print("🏥 Medical Data Processing - Compact View")
        print("=" * 60)
        print(f"⏰ {data['timestamp'][:19]} | API: {data['api_status'].upper()}")

        if "processing_status" in data and "sources" in data["processing_status"]:
            sources = data["processing_status"]["sources"]
            summary = data["processing_status"].get("summary", {})

            print(f"\n📊 Total: {summary.get('total_records', 0):,} | "
                  f"Processing: {summary.get('sources_processing', 0)} | "
                  f"Complete: {summary.get('sources_completed', 0)}")

            print("\n" + "-" * 60)

            # Sort by completion percentage
            sorted_sources = sorted(sources.items(),
                                  key=lambda x: x[1].get("completion_percent", 0),
                                  reverse=True)

            for source, source_data in sorted_sources:
                name = source.replace("_", " ").title()[:15].ljust(15)
                count = f"{source_data.get('current_count', 0):,}".rjust(8)
                pct = f"{source_data.get('completion_percent', 0):5.1f}%"
                rate = self.format_rate(source_data.get("processing_rate_per_sec", 0)).ljust(8)
                eta = source_data.get("eta_human", "N/A").ljust(6)
                status = source_data.get("status", "unknown")

                # Status icons
                icon = {"completed": "✅", "processing": "🔄",
                       "not_started": "⏸️", "error": "❌"}.get(status, "❓")

                print(f"{icon} {name} {count} {pct} {rate} {eta}")

        print("\n🔄 Press Ctrl+C to exit")

    def print_full_dashboard(self, data: dict[str, Any]):
        """Print full detailed dashboard"""
        os.system("clear")

        print("=" * 80)
        print("🏥 MEDICAL DATA PROCESSING DASHBOARD")
        print(f"📊 Last Updated: {data['timestamp'][:19]} | API Status: {data['api_status'].upper()}")
        print("=" * 80)

        # Processing Summary
        if "processing_status" in data and "summary" in data["processing_status"]:
            summary = data["processing_status"]["summary"]
            print("\n📈 PROCESSING SUMMARY:")
            print(f"   Total Records: {summary.get('total_records', 0):,}")
            print(f"   Sources Processing: {summary.get('sources_processing', 0)}")
            print(f"   Sources Completed: {summary.get('sources_completed', 0)}")
            print(f"   Sources Not Started: {summary.get('sources_not_started', 0)}")
            if summary.get("sources_error", 0) > 0:
                print(f"   Sources with Errors: {summary.get('sources_error', 0)} ⚠️")

        # System Resources
        if "system_resources" in data:
            resources = data["system_resources"]
            print("\n🖥️  SYSTEM RESOURCES:")

            if "database" in resources and "size_human" in resources["database"]:
                print(f"   Database Size: {resources['database']['size_human']}")

            if "memory" in resources and resources["memory"]:
                mem = resources["memory"]
                if "total" in mem:
                    print(f"   Memory: {mem.get('used', 'N/A')}/{mem.get('total', 'N/A')} "
                          f"(Available: {mem.get('available', 'N/A')})")

            if "disk" in resources:
                for path, disk_info in resources["disk"].items():
                    if isinstance(disk_info, dict) and "usage_percent" in disk_info:
                        print(f"   Disk {path}: {disk_info['usage_percent']}% used "
                              f"({disk_info['free_gb']:.1f}GB free)")

        # File Progress
        if "file_progress" in data and "file_progress" in data["file_progress"]:
            file_data = data["file_progress"]["file_progress"]
            active_sources = {k: v for k, v in file_data.items()
                            if v.get("total_files", 0) > 0}

            if active_sources:
                print("\n📁 FILE PROCESSING:")
                for source, files in active_sources.items():
                    name = source.replace("_", " ").title()
                    total = files.get("total_files", 0)
                    recent = files.get("recently_processed", 0)
                    print(f"   {name}: {total:,} total files, {recent:,} recently processed")

        # Data Sources Details
        if "processing_status" in data and "sources" in data["processing_status"]:
            sources = data["processing_status"]["sources"]

            print("\n📋 DATA SOURCES DETAILS:")
            print("   " + "-" * 75)
            print("   Source               Current    Target    Progress   Rate/sec    ETA      Status")
            print("   " + "-" * 75)

            # Sort by progress percentage
            sorted_sources = sorted(sources.items(),
                                  key=lambda x: x[1].get("completion_percent", 0),
                                  reverse=True)

            for source, source_data in sorted_sources:
                name = source[:18].ljust(18)
                current = f"{source_data.get('current_count', 0):,}".rjust(9)
                target = f"{source_data.get('target_count', 0):,}".rjust(9)
                progress = f"{source_data.get('completion_percent', 0):5.1f}%".rjust(8)
                rate = self.format_rate(source_data.get("processing_rate_per_sec", 0)).ljust(9)
                eta = source_data.get("eta_human", "N/A").ljust(8)
                status = source_data.get("status", "unknown")

                # Status icons
                status_icons = {
                    "completed": "✅",
                    "processing": "🔄",
                    "not_started": "⏸️",
                    "error": "❌",
                }
                icon = status_icons.get(status, "❓")

                print(f"   {name} {current} {target} {progress} {rate} {eta} {icon} {status}")

        # Error Summary
        if "error_summary" in data and data["error_summary"].get("summary_counts"):
            error_counts = data["error_summary"]["summary_counts"]
            if any(count > 0 for count in error_counts.values()):
                print("\n⚠️  ERRORS (Last Hour):")
                for error_type, count in error_counts.items():
                    if count > 0:
                        print(f"   {error_type.replace('_', ' ').title()}: {count}")

        print("   " + "-" * 75)
        print(f"\n🔄 Auto-refresh every {self.refresh_interval}s | Press Ctrl+C to exit")
        print("=" * 80)

    def run_dashboard(self, compact: bool = False):
        """Run interactive dashboard with auto-refresh"""
        print("🚀 Starting Medical Data Dashboard...")
        print(f"📡 API URL: {self.api_url}")
        print(f"🔄 Refresh: {self.refresh_interval}s")
        print()

        try:
            while True:
                data = self.get_comprehensive_data()

                if compact:
                    self.print_compact_dashboard(data)
                else:
                    self.print_full_dashboard(data)

                time.sleep(self.refresh_interval)

        except KeyboardInterrupt:
            self.signal_handler(None, None)

    def run_once(self, output_format: str = "human", compact: bool = False):
        """Run dashboard once and exit"""
        data = self.get_comprehensive_data()

        if output_format == "json":
            print(json.dumps(data, indent=2))
        elif compact:
            self.print_compact_dashboard(data)
        else:
            self.print_full_dashboard(data)

def main():
    parser = argparse.ArgumentParser(
        description="Medical Data Processing Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python medical_data_dashboard.py                    # Interactive full dashboard
  python medical_data_dashboard.py --compact          # Interactive compact view
  python medical_data_dashboard.py --once             # Single snapshot
  python medical_data_dashboard.py --json --once      # JSON output
  python medical_data_dashboard.py --refresh 10       # Refresh every 10 seconds
        """,
    )

    parser.add_argument("--once", action="store_true",
                       help="Run once and exit (no auto-refresh)")
    parser.add_argument("--json", action="store_true",
                       help="Output JSON format (requires --once)")
    parser.add_argument("--compact", action="store_true",
                       help="Use compact view")
    parser.add_argument("--refresh", type=int, default=30,
                       help="Refresh interval in seconds (default: 30)")
    parser.add_argument("--api-url", default="http://localhost:8081",
                       help="Medical-mirrors API URL (default: http://localhost:8081)")

    args = parser.parse_args()

    # Validate arguments
    if args.json and not args.once:
        parser.error("--json requires --once")

    dashboard = MedicalDataDashboard(
        api_url=args.api_url,
        refresh_interval=args.refresh,
    )

    if args.once:
        output_format = "json" if args.json else "human"
        dashboard.run_once(output_format, compact=args.compact)
    else:
        dashboard.run_dashboard(compact=args.compact)

if __name__ == "__main__":
    main()
