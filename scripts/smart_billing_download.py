#!/usr/bin/env python3
"""
Smart billing codes download script - integrates with medical-mirrors system
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add medical-mirrors src to path
sys.path.append('/home/intelluxe/services/user/medical-mirrors/src')

from billing_codes.smart_downloader import SmartBillingCodesDownloader
from billing_codes.background_service import BillingCodesBackgroundService
from config import Config


async def main():
    """Main entry point for smart billing codes download"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart Billing Codes Downloader")
    parser.add_argument("command", choices=["download", "status", "service", "reset"],
                       help="Command to execute")
    parser.add_argument("--force-fresh", action="store_true", 
                       help="Force fresh download (reset all states)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    parser.add_argument("--data-dir", type=Path,
                       default=Path("/home/intelluxe/database/medical_complete/billing"),
                       help="Output directory for downloaded data")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    # Ensure output directory exists
    args.data_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        if args.command == "download":
            await run_download(args, logger)
        elif args.command == "status":
            await show_status(args, logger)
        elif args.command == "service":
            await run_background_service(args, logger)
        elif args.command == "reset":
            await reset_downloads(args, logger)
            
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error: {e}")
        if args.verbose:
            logger.exception("Full traceback:")
        sys.exit(1)


async def run_download(args, logger):
    """Run smart download of billing codes"""
    logger.info("Starting smart billing codes download")
    
    async with SmartBillingCodesDownloader(output_dir=args.data_dir) as downloader:
        # Show initial status
        initial_status = await downloader.get_download_status()
        logger.info(f"Initial status: {initial_status['progress']['completed']}/"
                   f"{initial_status['progress']['total_sources']} sources completed")
        
        if initial_status.get('ready_for_retry'):
            logger.info(f"Sources ready for retry: {len(initial_status['ready_for_retry'])}")
        
        # Run download
        start_time = datetime.now()
        summary = await downloader.download_all_billing_codes(force_fresh=args.force_fresh)
        end_time = datetime.now()
        
        # Display results
        print("\n" + "="*50)
        print("SMART BILLING CODES DOWNLOAD SUMMARY")
        print("="*50)
        print(f"Duration: {(end_time - start_time).total_seconds():.1f} seconds")
        print(f"Total codes downloaded: {summary['total_codes']:,}")
        print(f"Successful sources: {summary['successful_sources']}")
        print(f"Failed sources: {summary['failed_sources']}")
        print(f"Rate limited sources: {summary['rate_limited_sources']}")
        print(f"Success rate: {summary['success_rate']:.1f}%")
        
        if summary.get('by_source_breakdown'):
            print(f"\nBreakdown by source:")
            for source, count in summary['by_source_breakdown'].items():
                print(f"  {source}: {count:,} codes")
        
        if summary.get('parser_stats'):
            stats = summary['parser_stats']
            print(f"\nParser statistics:")
            print(f"  Processed: {stats['processed_codes']:,}")
            print(f"  Validation errors: {stats['validation_errors']:,}")
            print(f"  Duplicates removed: {stats['duplicates_removed']:,}")
            print(f"  Success rate: {stats['success_rate']:.1%}")
        
        # Show which sources might need retry
        final_status = await downloader.get_download_status()
        if final_status.get('ready_for_retry'):
            print(f"\nSources ready for retry: {final_status['ready_for_retry']}")
        
        if final_status.get('next_retry_times'):
            print(f"\nNext retry times:")
            for source, retry_time in final_status['next_retry_times'].items():
                print(f"  {source}: {retry_time}")
        
        # Save summary report
        report_file = args.data_dir / f"download_report_{start_time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(), 
                'summary': summary,
                'final_status': final_status
            }, f, indent=2, default=str)
        
        print(f"\nDetailed report saved to: {report_file}")
        print("\nRecommendation: Use 'smart_billing_download.py service' to run")
        print("background service for automatic retries of rate-limited sources.")


async def show_status(args, logger):
    """Show current download status"""
    async with SmartBillingCodesDownloader(output_dir=args.data_dir) as downloader:
        status = await downloader.get_download_status()
        
        print(json.dumps(status, indent=2, default=str))


async def run_background_service(args, logger):
    """Run background service"""
    logger.info("Starting billing codes background service")
    
    service = BillingCodesBackgroundService()
    await service.start_service()


async def reset_downloads(args, logger):
    """Reset all download states"""
    logger.info("Resetting all download states")
    
    async with SmartBillingCodesDownloader(output_dir=args.data_dir) as downloader:
        downloader._reset_all_states()
        logger.info("All download states have been reset")
        
        # Show new status
        status = await downloader.get_download_status()
        print(f"Reset complete. Status: {status['progress']['completed']}/"
              f"{status['progress']['total_sources']} sources completed")


if __name__ == "__main__":
    asyncio.run(main())