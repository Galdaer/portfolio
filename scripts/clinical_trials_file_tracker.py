#!/usr/bin/env python3
"""
Clinical Trials File Processing Tracker

Specialized monitoring for clinical trials file processing with 26,813 files.
Tracks individual file processing progress, identifies bottlenecks, and monitors
the parallel processing workers.

Features:
- Track processing of 26,813 clinical trial files
- Monitor worker thread performance
- Identify stalled or problematic files
- Calculate processing rates per worker
- Show file processing queue status
- Detect memory or performance issues

Usage:
    python clinical_trials_file_tracker.py                    # Interactive view
    python clinical_trials_file_tracker.py --once             # Single snapshot
    python clinical_trials_file_tracker.py --files-only       # Show file details only
    python clinical_trials_file_tracker.py --workers-only     # Show worker details only
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict
import subprocess

class ClinicalTrialsFileTracker:
    """Track clinical trials file processing in detail"""
    
    def __init__(self, data_dir: str = "/home/intelluxe/database/medical_complete/clinicaltrials"):
        self.data_dir = Path(data_dir)
        self.processed_files_cache = {}
        self.worker_stats = defaultdict(list)
        
    def get_file_inventory(self) -> Dict[str, Any]:
        """Get comprehensive inventory of clinical trials files"""
        if not self.data_dir.exists():
            return {
                "error": f"Data directory not found: {self.data_dir}",
                "total_files": 0,
                "file_types": {}
            }
        
        inventory = {
            "timestamp": datetime.now().isoformat(),
            "data_directory": str(self.data_dir),
            "file_types": defaultdict(int),
            "size_distribution": defaultdict(int),
            "processing_status": defaultdict(int),
            "files": []
        }
        
        # Scan all files
        for file_path in self.data_dir.iterdir():
            if file_path.is_file():
                try:
                    stat = file_path.stat()
                    file_info = {
                        "name": file_path.name,
                        "size_mb": round(stat.st_size / (1024*1024), 2),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "age_hours": round((datetime.now().timestamp() - stat.st_mtime) / 3600, 1)
                    }
                    
                    # Categorize file types
                    if file_path.suffix == '.gz':
                        if '.json.gz' in file_path.name:
                            file_type = 'json_gz'
                        elif '.xml.gz' in file_path.name:
                            file_type = 'xml_gz'
                        else:
                            file_type = 'other_gz'
                    else:
                        file_type = file_path.suffix[1:] if file_path.suffix else 'no_extension'
                    
                    file_info["type"] = file_type
                    inventory["file_types"][file_type] += 1
                    
                    # Size distribution
                    if file_info["size_mb"] < 1:
                        size_cat = "small (<1MB)"
                    elif file_info["size_mb"] < 10:
                        size_cat = "medium (1-10MB)" 
                    elif file_info["size_mb"] < 100:
                        size_cat = "large (10-100MB)"
                    else:
                        size_cat = "xlarge (>100MB)"
                    
                    inventory["size_distribution"][size_cat] += 1
                    
                    # Processing status based on modification time
                    if file_info["age_hours"] < 1:
                        status = "recently_processed"
                    elif file_info["age_hours"] < 24:
                        status = "processed_today"
                    elif file_info["age_hours"] < 168:  # 7 days
                        status = "processed_this_week"
                    else:
                        status = "old"
                    
                    file_info["status"] = status
                    inventory["processing_status"][status] += 1
                    
                    inventory["files"].append(file_info)
                    
                except Exception as e:
                    # Skip files that can't be accessed
                    continue
        
        inventory["total_files"] = len(inventory["files"])
        
        # Convert defaultdicts to regular dicts for JSON serialization
        inventory["file_types"] = dict(inventory["file_types"])
        inventory["size_distribution"] = dict(inventory["size_distribution"])
        inventory["processing_status"] = dict(inventory["processing_status"])
        
        return inventory
    
    def analyze_worker_performance(self) -> Dict[str, Any]:
        """Analyze worker performance from recent logs"""
        worker_analysis = {
            "timestamp": datetime.now().isoformat(),
            "workers": {},
            "overall_stats": {},
            "bottlenecks": []
        }
        
        try:
            # Get recent logs from medical-mirrors container
            result = subprocess.run([
                "docker", "logs", "medical-mirrors", "--tail", "1000"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                worker_analysis["error"] = "Could not fetch container logs"
                return worker_analysis
            
            log_lines = result.stdout.split('\n')
            
            # Parse worker activity
            worker_files = defaultdict(list)
            total_processed = 0
            processing_times = []
            
            for line in log_lines:
                if "Worker parsed" in line and "studies from" in line:
                    try:
                        # Extract file name and count
                        parts = line.split("studies from ")
                        if len(parts) > 1:
                            file_name = parts[1].strip()
                            
                            # Extract count
                            count_part = line.split("parsed ")[1].split(" studies")[0]
                            count = int(count_part)
                            
                            # Extract timestamp
                            timestamp_str = line.split(" - ")[0]
                            timestamp = datetime.fromisoformat(timestamp_str.replace(',', '.'))
                            
                            worker_files["worker"].append({
                                "file": file_name,
                                "count": count,
                                "timestamp": timestamp.isoformat()
                            })
                            
                            total_processed += count
                            
                    except Exception as e:
                        continue
            
            # Calculate overall statistics
            if worker_files:
                all_entries = worker_files["worker"]
                if all_entries:
                    first_time = datetime.fromisoformat(all_entries[0]["timestamp"])
                    last_time = datetime.fromisoformat(all_entries[-1]["timestamp"])
                    
                    duration = (last_time - first_time).total_seconds()
                    if duration > 0:
                        overall_rate = total_processed / duration
                        worker_analysis["overall_stats"] = {
                            "total_records_processed": total_processed,
                            "files_processed": len(all_entries),
                            "duration_seconds": round(duration, 1),
                            "records_per_second": round(overall_rate, 2),
                            "files_per_minute": round(len(all_entries) / (duration / 60), 2) if duration > 60 else 0
                        }
            
            # Analyze for bottlenecks
            if len(worker_files["worker"]) > 0:
                recent_files = worker_files["worker"][-10:]  # Last 10 files
                processing_times = []
                
                for i in range(1, len(recent_files)):
                    prev_time = datetime.fromisoformat(recent_files[i-1]["timestamp"])
                    curr_time = datetime.fromisoformat(recent_files[i]["timestamp"])
                    processing_time = (curr_time - prev_time).total_seconds()
                    processing_times.append(processing_time)
                
                if processing_times:
                    avg_time = sum(processing_times) / len(processing_times)
                    slow_files = [t for t in processing_times if t > avg_time * 2]
                    
                    if slow_files:
                        worker_analysis["bottlenecks"].append(
                            f"Detected {len(slow_files)} slow file(s) in recent processing"
                        )
                    
                    worker_analysis["processing_timing"] = {
                        "average_file_time": round(avg_time, 2),
                        "slowest_file_time": round(max(processing_times), 2),
                        "fastest_file_time": round(min(processing_times), 2)
                    }
            
            worker_analysis["workers"]["worker"] = {
                "files_processed": len(worker_files["worker"]),
                "records_processed": total_processed,
                "recent_files": worker_files["worker"][-5:]  # Last 5 files
            }
            
        except Exception as e:
            worker_analysis["error"] = f"Failed to analyze worker performance: {e}"
        
        return worker_analysis
    
    def get_processing_queue_status(self) -> Dict[str, Any]:
        """Estimate processing queue status based on file modification patterns"""
        inventory = self.get_file_inventory()
        
        if "error" in inventory:
            return {"error": inventory["error"]}
        
        queue_status = {
            "timestamp": datetime.now().isoformat(),
            "queue_analysis": {},
            "estimated_remaining": 0,
            "processing_rate": 0
        }
        
        # Sort files by modification time
        files_by_time = sorted(inventory["files"], 
                              key=lambda x: x["modified"], 
                              reverse=True)
        
        # Identify recently processed files (last 2 hours)
        cutoff_time = datetime.now() - timedelta(hours=2)
        recently_processed = []
        
        for file_info in files_by_time:
            file_time = datetime.fromisoformat(file_info["modified"])
            if file_time > cutoff_time:
                recently_processed.append(file_info)
            else:
                break
        
        # Calculate processing rate
        if recently_processed:
            time_span = 2 * 3600  # 2 hours in seconds
            processing_rate = len(recently_processed) / time_span
            queue_status["processing_rate"] = round(processing_rate * 3600, 2)  # files per hour
        
        # Estimate remaining files (those not modified recently)
        total_files = inventory["total_files"]
        processed_recently = len(recently_processed)
        remaining = total_files - processed_recently
        
        queue_status["queue_analysis"] = {
            "total_files": total_files,
            "processed_recently": processed_recently, 
            "estimated_remaining": remaining,
            "completion_percent": round((processed_recently / total_files) * 100, 2) if total_files > 0 else 0
        }
        
        # Estimate completion time
        if queue_status["processing_rate"] > 0 and remaining > 0:
            hours_remaining = remaining / queue_status["processing_rate"]
            eta = datetime.now() + timedelta(hours=hours_remaining)
            queue_status["estimated_completion"] = eta.isoformat()
            queue_status["hours_remaining"] = round(hours_remaining, 1)
        
        return queue_status
    
    def print_file_details(self, inventory: Dict[str, Any]):
        """Print detailed file information"""
        print("📁 CLINICAL TRIALS FILE INVENTORY")
        print("=" * 60)
        print(f"📂 Directory: {inventory.get('data_directory', 'N/A')}")
        print(f"📊 Total Files: {inventory.get('total_files', 0):,}")
        print()
        
        # File types breakdown
        file_types = inventory.get("file_types", {})
        if file_types:
            print("📋 File Types:")
            for file_type, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True):
                print(f"   {file_type}: {count:,}")
            print()
        
        # Size distribution
        sizes = inventory.get("size_distribution", {})
        if sizes:
            print("📏 Size Distribution:")
            for size_cat, count in sizes.items():
                print(f"   {size_cat}: {count:,}")
            print()
        
        # Processing status
        status = inventory.get("processing_status", {})
        if status:
            print("⏱️  Processing Status:")
            for status_cat, count in status.items():
                status_name = status_cat.replace("_", " ").title()
                print(f"   {status_name}: {count:,}")
            print()
    
    def print_worker_analysis(self, worker_data: Dict[str, Any]):
        """Print worker performance analysis"""
        print("👷 WORKER PERFORMANCE ANALYSIS")
        print("=" * 60)
        
        if "error" in worker_data:
            print(f"❌ Error: {worker_data['error']}")
            return
        
        overall = worker_data.get("overall_stats", {})
        if overall:
            print("📈 Overall Performance:")
            print(f"   Records Processed: {overall.get('total_records_processed', 0):,}")
            print(f"   Files Processed: {overall.get('files_processed', 0):,}")
            print(f"   Duration: {overall.get('duration_seconds', 0)} seconds")
            print(f"   Rate: {overall.get('records_per_second', 0)} records/sec")
            print(f"   Rate: {overall.get('files_per_minute', 0)} files/min")
            print()
        
        timing = worker_data.get("processing_timing", {})
        if timing:
            print("⏱️  File Processing Timing:")
            print(f"   Average Time per File: {timing.get('average_file_time', 0)}s")
            print(f"   Fastest File: {timing.get('fastest_file_time', 0)}s")
            print(f"   Slowest File: {timing.get('slowest_file_time', 0)}s")
            print()
        
        bottlenecks = worker_data.get("bottlenecks", [])
        if bottlenecks:
            print("⚠️  Identified Issues:")
            for issue in bottlenecks:
                print(f"   • {issue}")
            print()
    
    def print_queue_status(self, queue_data: Dict[str, Any]):
        """Print processing queue status"""
        print("🚀 PROCESSING QUEUE STATUS")
        print("=" * 60)
        
        if "error" in queue_data:
            print(f"❌ Error: {queue_data['error']}")
            return
        
        analysis = queue_data.get("queue_analysis", {})
        if analysis:
            print("📊 Queue Analysis:")
            print(f"   Total Files: {analysis.get('total_files', 0):,}")
            print(f"   Recently Processed: {analysis.get('processed_recently', 0):,}")
            print(f"   Estimated Remaining: {analysis.get('estimated_remaining', 0):,}")
            print(f"   Completion: {analysis.get('completion_percent', 0):.1f}%")
            print()
        
        rate = queue_data.get("processing_rate", 0)
        if rate > 0:
            print(f"⚡ Processing Rate: {rate:.1f} files/hour")
            
        if "hours_remaining" in queue_data:
            hours = queue_data["hours_remaining"]
            if hours < 24:
                print(f"⏰ ETA: {hours:.1f} hours")
            else:
                days = hours / 24
                print(f"⏰ ETA: {days:.1f} days")
            
        if "estimated_completion" in queue_data:
            completion_time = datetime.fromisoformat(queue_data["estimated_completion"])
            print(f"🎯 Estimated Completion: {completion_time.strftime('%Y-%m-%d %H:%M')}")
        
        print()
    
    def print_dashboard(self, files_only: bool = False, workers_only: bool = False):
        """Print comprehensive dashboard"""
        os.system('clear')
        
        print("🏥 CLINICAL TRIALS FILE PROCESSING TRACKER")
        print("=" * 80)
        print(f"⏰ Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        if not workers_only:
            # File inventory
            inventory = self.get_file_inventory()
            self.print_file_details(inventory)
            
            # Queue status
            queue_status = self.get_processing_queue_status()
            self.print_queue_status(queue_status)
        
        if not files_only:
            # Worker analysis
            worker_data = self.analyze_worker_performance()
            self.print_worker_analysis(worker_data)
        
        print("🔄 Press Ctrl+C to exit")
    
    def run_dashboard(self, refresh_interval: int = 60, files_only: bool = False, workers_only: bool = False):
        """Run interactive dashboard with auto-refresh"""
        try:
            while True:
                self.print_dashboard(files_only, workers_only)
                time.sleep(refresh_interval)
        except KeyboardInterrupt:
            print(f"\n\n🛑 Clinical Trials File Tracker stopped by user")
            sys.exit(0)
    
    def run_once(self, output_format: str = "human", files_only: bool = False, workers_only: bool = False):
        """Run once and exit"""
        if output_format == "json":
            data = {
                "timestamp": datetime.now().isoformat(),
                "file_inventory": self.get_file_inventory() if not workers_only else None,
                "queue_status": self.get_processing_queue_status() if not workers_only else None,
                "worker_analysis": self.analyze_worker_performance() if not files_only else None
            }
            print(json.dumps(data, indent=2))
        else:
            self.print_dashboard(files_only, workers_only)

def main():
    parser = argparse.ArgumentParser(
        description="Clinical Trials File Processing Tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--once", action="store_true",
                       help="Run once and exit (no auto-refresh)")
    parser.add_argument("--json", action="store_true", 
                       help="Output JSON format (requires --once)")
    parser.add_argument("--files-only", action="store_true",
                       help="Show only file details")
    parser.add_argument("--workers-only", action="store_true",
                       help="Show only worker performance") 
    parser.add_argument("--refresh", type=int, default=60,
                       help="Refresh interval in seconds (default: 60)")
    parser.add_argument("--data-dir", 
                       default="/home/intelluxe/database/medical_complete/clinicaltrials",
                       help="Clinical trials data directory")
    
    args = parser.parse_args()
    
    if args.json and not args.once:
        parser.error("--json requires --once")
    
    if args.files_only and args.workers_only:
        parser.error("Cannot specify both --files-only and --workers-only")
    
    tracker = ClinicalTrialsFileTracker(data_dir=args.data_dir)
    
    if args.once:
        output_format = "json" if args.json else "human"
        tracker.run_once(output_format, args.files_only, args.workers_only)
    else:
        tracker.run_dashboard(args.refresh, args.files_only, args.workers_only)

if __name__ == "__main__":
    main()