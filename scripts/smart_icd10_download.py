#!/usr/bin/env python3
"""
Smart ICD-10 codes download script - integrates with medical-mirrors system
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

import icd10.smart_downloader
import icd10.background_service
SmartICD10Downloader = icd10.smart_downloader.SmartICD10Downloader
ICD10BackgroundService = icd10.background_service.ICD10BackgroundService
from config import Config


async def main():
    """Main entry point for smart ICD-10 codes download"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart ICD-10 Codes Downloader")
    parser.add_argument("command", choices=["download", "status", "service", "reset", "analyze"],
                       help="Command to execute")
    parser.add_argument("--force-fresh", action="store_true", 
                       help="Force fresh download (reset all states)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    parser.add_argument("--data-dir", type=Path,
                       default=Path("/home/intelluxe/database/medical_complete/icd10"),
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
        elif args.command == "analyze":
            await analyze_codes(args, logger)
            
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error: {e}")
        if args.verbose:
            logger.exception("Full traceback:")
        sys.exit(1)


async def run_download(args, logger):
    """Run smart download of ICD-10 codes"""
    logger.info("Starting smart ICD-10 codes download")
    
    async with SmartICD10Downloader(output_dir=args.data_dir) as downloader:
        # Show initial status
        initial_status = await downloader.get_download_status()
        logger.info(f"Initial status: {initial_status['progress']['completed']}/"
                   f"{initial_status['progress']['total_sources']} sources completed")
        
        if initial_status.get('ready_for_retry'):
            logger.info(f"Sources ready for retry: {len(initial_status['ready_for_retry'])}")
        
        # Run download
        start_time = datetime.now()
        
        try:
            summary = await downloader.download_all_icd10_codes(force_fresh=args.force_fresh)
            end_time = datetime.now()
        
        except KeyboardInterrupt:
            # Handle graceful shutdown on interrupt
            duration = datetime.now() - start_time
            print("⚠️  Download interrupted by user")
            print(f"   Time elapsed: {duration}")
            
            # Save interrupt state for resume
            interrupt_file = args.data_dir / "icd10_download_interrupted.json"
            interrupt_info = {
                'interrupt_time': datetime.now().isoformat(),
                'duration_seconds': duration.total_seconds(),
            }
            
            try:
                interrupt_info['state'] = await downloader.get_download_status()
            except Exception:
                interrupt_info['state'] = 'unavailable'
            
            with open(interrupt_file, 'w') as f:
                json.dump(interrupt_info, f, indent=2)
            
            print(f"📁 Interrupted state saved to: {interrupt_file}")
            print("💡 Resume with the same command - download will continue from last checkpoint")
            
            # Exit cleanly
            return
        
        except Exception as e:
            print(f"❌ Download failed: {e}")
            
            # Save error state for analysis
            error_file = args.data_dir / "icd10_download_errors.json"
            error_info = {
                'error_time': datetime.now().isoformat(),
                'error_message': str(e),
                'duration_seconds': (datetime.now() - start_time).total_seconds(),
            }
            
            try:
                error_info['state'] = await downloader.get_download_status()
            except Exception:
                error_info['state'] = 'unavailable'
            
            with open(error_file, 'w') as f:
                json.dump(error_info, f, indent=2)
            
            print(f"Error state saved to: {error_file}")
            print("You can resume the download later using the same command")
            raise
        
        # Display results
        print("\n" + "="*60)
        print("SMART ICD-10 CODES DOWNLOAD SUMMARY")
        print("="*60)
        print(f"Duration: {(end_time - start_time).total_seconds():.1f} seconds")
        print(f"Total codes downloaded: {summary['total_codes']:,}")
        print(f"Successful sources: {summary['successful_sources']}")
        print(f"Failed sources: {summary['failed_sources']}")
        print(f"Rate limited sources: {summary['rate_limited_sources']}")
        print(f"Success rate: {summary['success_rate']:.1f}%")
        
        # Expected vs Actual
        expected_vs_actual = summary.get('expected_vs_actual', {})
        if expected_vs_actual:
            print(f"\n📊 Expected vs Actual:")
            print(f"  Expected: {expected_vs_actual.get('expected_total', 'Unknown')}")
            print(f"  Actual: {expected_vs_actual.get('actual_total', 0):,}")
            improvement = expected_vs_actual.get('improvement_over_fallback', 0)
            if improvement > 0:
                print(f"  Improvement: +{improvement:,} codes over fallback")
        
        if summary.get('by_source_breakdown'):
            print(f"\n📁 Breakdown by source:")
            for source, count in summary['by_source_breakdown'].items():
                print(f"  {source}: {count:,} codes")
        
        if summary.get('parser_stats'):
            stats = summary['parser_stats']
            print(f"\n🔍 Parser statistics:")
            print(f"  Processed: {stats.get('processed_codes', 0):,}")
            print(f"  Validation errors: {stats.get('validation_errors', 0):,}")
            print(f"  Duplicates removed: {stats.get('duplicates_removed', 0):,}")
            print(f"  Source conflicts resolved: {stats.get('source_conflicts_resolved', 0):,}")
            print(f"  Success rate: {stats.get('success_rate', 0):.1%}")
        
        # Show which sources might need retry
        final_status = await downloader.get_download_status()
        if final_status.get('ready_for_retry'):
            print(f"\n⏳ Sources ready for retry: {final_status['ready_for_retry']}")
        
        if final_status.get('next_retry_times'):
            print(f"\n⏰ Next retry times:")
            for source, retry_time in final_status['next_retry_times'].items():
                print(f"  {source}: {retry_time}")
        
        # Completion estimate
        completion_estimate = final_status.get('completion_estimate', {})
        if completion_estimate.get('status') == 'incomplete':
            print(f"\n🔮 Completion estimate:")
            print(f"  Incomplete sources: {completion_estimate.get('incomplete_sources', 0)}")
            if completion_estimate.get('estimated_completion'):
                print(f"  Estimated completion: {completion_estimate['estimated_completion']}")
        
        # Save summary report
        report_file = args.data_dir / f"download_report_{start_time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(), 
                'summary': summary,
                'final_status': final_status
            }, f, indent=2, default=str)
        
        print(f"\n📋 Detailed report saved to: {report_file}")
        print("\n💡 Recommendation: Use 'smart_icd10_download.py service' to run")
        print("background service for automatic retries of rate-limited sources.")


async def show_status(args, logger):
    """Show current download status"""
    async with SmartICD10Downloader(output_dir=args.data_dir) as downloader:
        status = await downloader.get_download_status()
        
        print(json.dumps(status, indent=2, default=str))


async def run_background_service(args, logger):
    """Run background service"""
    logger.info("Starting ICD-10 codes background service")
    
    service = ICD10BackgroundService()
    await service.start_service()


async def reset_downloads(args, logger):
    """Reset all download states"""
    logger.info("Resetting all ICD-10 download states")
    
    async with SmartICD10Downloader(output_dir=args.data_dir) as downloader:
        downloader._reset_all_states()
        logger.info("All ICD-10 download states have been reset")
        
        # Show new status
        status = await downloader.get_download_status()
        print(f"Reset complete. Status: {status['progress']['completed']}/"
              f"{status['progress']['total_sources']} sources completed")


async def analyze_codes(args, logger):
    """Analyze downloaded ICD-10 codes"""
    logger.info("Analyzing downloaded ICD-10 codes")
    
    async with SmartICD10Downloader(output_dir=args.data_dir) as downloader:
        # Load existing codes
        await downloader._load_existing_results()
        
        if not downloader.all_codes:
            print("No ICD-10 codes found. Run download first.")
            return
        
        # Get detailed statistics
        stats = await downloader.get_codes_statistics()
        
        print("\n" + "="*50)
        print("ICD-10 CODES ANALYSIS")
        print("="*50)
        
        print(f"Total codes: {stats['total_codes']:,}")
        
        print(f"\n📂 By Source:")
        for source, count in stats['by_source'].items():
            percentage = (count / stats['total_codes']) * 100
            print(f"  {source}: {count:,} ({percentage:.1f}%)")
        
        print(f"\n📊 By Chapter (Top 10):")
        chapter_items = list(stats['by_chapter'].items())[:10]
        for chapter, count in chapter_items:
            percentage = (count / stats['total_codes']) * 100
            print(f"  {chapter}: {count:,} ({percentage:.1f}%)")
        
        print(f"\n💰 Billable vs Non-Billable:")
        billable = stats['billable_vs_non_billable']
        total = billable['billable'] + billable['non_billable']
        print(f"  Billable: {billable['billable']:,} ({billable['billable']/total*100:.1f}%)")
        print(f"  Non-billable: {billable['non_billable']:,} ({billable['non_billable']/total*100:.1f}%)")
        
        print(f"\n📏 Code Length Distribution:")
        for length, count in sorted(stats['code_length_distribution'].items()):
            percentage = (count / stats['total_codes']) * 100
            print(f"  {length} characters: {count:,} ({percentage:.1f}%)")
        
        print(f"\n🌳 Most Common Categories (Top 10):")
        category_items = list(stats['most_common_categories'].items())[:10]
        for category, count in category_items:
            percentage = (count / stats['total_codes']) * 100
            print(f"  {category}: {count:,} ({percentage:.1f}%)")
        
        # Save analysis report
        analysis_file = args.data_dir / f"analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(analysis_file, 'w') as f:
            json.dump(stats, f, indent=2, default=str)
        
        print(f"\n📋 Detailed analysis saved to: {analysis_file}")


if __name__ == "__main__":
    asyncio.run(main())