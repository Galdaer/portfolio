#!/usr/bin/env python3
"""
Real-time Medical Data Progress Monitor
Monitors the loading/updating progress of all medical data sources in real-time
Shows current record counts, progress rates, and estimated completion times
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Any

import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class MedicalDataMonitor:
    """Monitor progress of medical data loading/updating"""

    def __init__(self, refresh_interval: int = 5):
        self.refresh_interval = refresh_interval
        self.db_config = {
            "host": "localhost",
            "database": "intelluxe_public",
            "user": "intelluxe",
            "password": os.getenv("POSTGRES_PASSWORD", "secure_password"),
        }
        self.previous_counts = {}
        self.start_time = datetime.now()
        self.rates = {}

        # Expected total counts for progress calculation
        self.expected_totals = {
            "clinical_trials": 26813 * 1000,  # 26,813 files * ~1000 trials each
            "pubmed_articles": 3065 * 20000,  # 3,065 files * ~20,000 articles each
            "drug_information": 1189 * 500,   # 1,189 FDA files * ~500 drugs each
            "billing_codes": 100000,          # Estimated billing codes
            "icd10_codes": 100000,           # Estimated ICD-10 codes
            "exercises": 2000,               # Estimated exercises
            "health_topics": 5000,           # Estimated health topics
            "food_items": 50000,             # Estimated food items
        }

    def get_database_counts(self) -> dict[str, int]:
        """Get current record counts from all medical data tables"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()

            # Query all medical data tables
            queries = {
                "clinical_trials": "SELECT COUNT(*) FROM clinical_trials",
                "pubmed_articles": "SELECT COUNT(*) FROM pubmed_articles",
                "drug_information": "SELECT COUNT(*) FROM drug_information",
                "billing_codes": "SELECT COUNT(*) FROM billing_codes",
                "icd10_codes": "SELECT COUNT(*) FROM icd10_codes",
                "exercises": "SELECT COUNT(*) FROM exercises",
                "health_topics": "SELECT COUNT(*) FROM health_topics",
                "food_items": "SELECT COUNT(*) FROM food_items",
            }

            counts = {}
            for table_name, query in queries.items():
                try:
                    cursor.execute(query)
                    counts[table_name] = cursor.fetchone()[0]
                except psycopg2.Error as e:
                    if "relation" in str(e) and "does not exist" in str(e):
                        counts[table_name] = 0  # Table doesn't exist yet
                    else:
                        counts[table_name] = -1  # Error accessing table

            cursor.close()
            conn.close()
            return counts

        except psycopg2.Error as e:
            print(f"❌ Database connection error: {e}")
            return {}

    def calculate_rates_and_eta(self, current_counts: dict[str, int]) -> dict[str, dict[str, Any]]:
        """Calculate insertion rates and ETAs for each data source"""
        results = {}
        current_time = datetime.now()
        time_elapsed = (current_time - self.start_time).total_seconds()

        for table_name, current_count in current_counts.items():
            if current_count <= 0:
                continue

            # Calculate rate (records per second)
            if table_name in self.previous_counts:
                records_added = current_count - self.previous_counts[table_name]
                rate = records_added / self.refresh_interval if records_added > 0 else 0
            else:
                # First measurement - calculate overall rate since start
                rate = current_count / time_elapsed if time_elapsed > 0 else 0

            # Smooth the rate using exponential moving average
            if table_name in self.rates:
                self.rates[table_name] = 0.7 * self.rates[table_name] + 0.3 * rate
            else:
                self.rates[table_name] = rate

            # Calculate progress percentage
            expected_total = self.expected_totals.get(table_name, current_count * 2)
            progress_percent = (current_count / expected_total) * 100 if expected_total > 0 else 0

            # Calculate ETA with overflow protection
            if self.rates[table_name] > 0 and current_count < expected_total:
                remaining_records = expected_total - current_count
                eta_seconds = remaining_records / self.rates[table_name]

                # Prevent datetime overflow - cap at 365 days (31,536,000 seconds)
                if eta_seconds > 31536000:
                    eta = None  # Too far in the future to calculate
                else:
                    try:
                        eta = current_time + timedelta(seconds=eta_seconds)
                    except OverflowError:
                        eta = None
            else:
                eta = None

            results[table_name] = {
                "count": current_count,
                "rate": self.rates[table_name],
                "progress_percent": min(progress_percent, 100.0),
                "expected_total": expected_total,
                "eta": eta,
            }

        return results

    def format_number(self, num: int) -> str:
        """Format numbers with thousands separators"""
        return f"{num:,}"

    def format_rate(self, rate: float) -> str:
        """Format insertion rate with appropriate units"""
        if rate < 1:
            return f"{rate:.2f}/sec"
        if rate < 60:
            return f"{rate:.1f}/sec"
        if rate < 3600:
            return f"{rate/60:.1f}/min"
        return f"{rate/3600:.1f}/hour"

    def format_eta(self, eta: datetime) -> str:
        """Format ETA in a readable way"""
        if eta is None:
            return "N/A"

        now = datetime.now()
        if eta < now:
            return "Complete"

        delta = eta - now
        if delta.days > 0:
            return f"{delta.days}d {delta.seconds//3600}h"
        if delta.seconds > 3600:
            return f"{delta.seconds//3600}h {(delta.seconds%3600)//60}m"
        return f"{delta.seconds//60}m {delta.seconds%60}s"

    def display_progress(self, stats: dict[str, dict[str, Any]]) -> None:
        """Display formatted progress information"""
        # Clear screen
        os.system("clear" if os.name == "posix" else "cls")

        print("🏥 Medical Data Loading Progress Monitor")
        print("=" * 80)
        print(f"⏰ Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  Current: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏳ Running: {datetime.now() - self.start_time}")
        print()

        # Table header
        print(f"{'Source':<18} {'Count':<12} {'Progress':<10} {'Rate':<12} {'ETA':<15}")
        print("-" * 80)

        # Sort by progress percentage (highest first)
        sorted_stats = sorted(stats.items(), key=lambda x: x[1]["progress_percent"], reverse=True)

        total_records = 0
        active_sources = 0

        for table_name, data in sorted_stats:
            count = data["count"]
            rate = data["rate"]
            progress = data["progress_percent"]
            eta = data["eta"]

            if count > 0:
                total_records += count
                if rate > 0:
                    active_sources += 1

            # Format table name for display
            display_name = table_name.replace("_", " ").title()[:17]

            # Progress bar
            bar_length = 8
            filled_length = int(bar_length * progress / 100)
            bar = "█" * filled_length + "░" * (bar_length - filled_length)

            # Status indicator
            if count == 0:
                status = "⏸️"
            elif rate > 0:
                status = "🟢"
            else:
                status = "🟡"

            print(f"{status} {display_name:<15} {self.format_number(count):<12} "
                  f"{bar} {progress:>5.1f}% {self.format_rate(rate):<12} {self.format_eta(eta):<15}")

        print("-" * 80)
        print(f"📊 Total Records: {self.format_number(total_records)} | "
              f"🔄 Active Sources: {active_sources}/{len(stats)} | "
              f"🔄 Refresh: {self.refresh_interval}s")

        # Show specific progress messages
        if stats.get("clinical_trials", {}).get("rate", 0) > 0:
            stats["clinical_trials"]["count"]
            ct_progress = stats["clinical_trials"]["progress_percent"]
            if ct_progress < 50:
                print("\n📋 Clinical Trials: Processing existing 26,813 compressed files...")
            else:
                print(f"\n📋 Clinical Trials: {ct_progress:.1f}% complete, importing at {stats['clinical_trials']['rate']:.1f} records/sec")

        if stats.get("pubmed_articles", {}).get("count", 0) > 0:
            print(f"📚 PubMed: {stats['pubmed_articles']['count']:,} articles loaded from {3065} XML files")

        print("\n💡 Press Ctrl+C to exit monitor")

    async def monitor_progress(self) -> None:
        """Main monitoring loop"""
        print("🚀 Starting Medical Data Progress Monitor...")
        print(f"📊 Monitoring database: {self.db_config['database']} on {self.db_config['host']}")
        print(f"🔄 Refresh interval: {self.refresh_interval} seconds")
        print()

        try:
            while True:
                # Get current counts
                current_counts = self.get_database_counts()

                if not current_counts:
                    print("❌ Unable to connect to database. Retrying in 10 seconds...")
                    await asyncio.sleep(10)
                    continue

                # Calculate stats
                stats = self.calculate_rates_and_eta(current_counts)

                # Display progress
                self.display_progress(stats)

                # Store current counts for next iteration
                self.previous_counts = current_counts.copy()

                # Wait for next refresh
                await asyncio.sleep(self.refresh_interval)

        except KeyboardInterrupt:
            print("\n\n🛑 Monitoring stopped by user")
            print(f"📈 Final stats after {datetime.now() - self.start_time}:")

            # Show final counts
            final_counts = self.get_database_counts()
            for table_name, count in final_counts.items():
                if count > 0:
                    display_name = table_name.replace("_", " ").title()
                    print(f"   {display_name}: {self.format_number(count)} records")


async def main():
    parser = argparse.ArgumentParser(description="Monitor medical data loading progress")
    parser.add_argument("--refresh", "-r", type=int, default=5,
                       help="Refresh interval in seconds (default: 5)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)

    monitor = MedicalDataMonitor(refresh_interval=args.refresh)
    await monitor.monitor_progress()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
