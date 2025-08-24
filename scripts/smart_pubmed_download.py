#!/usr/bin/env python3
"""
Smart PubMed download script - integrates with medical-mirrors system
Handles FTP rate limits, network issues, and large file downloads with state persistence
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add medical-mirrors src to path
sys.path.append('/home/intelluxe/services/user/medical-mirrors/src')

from pubmed.smart_downloader import SmartPubMedDownloader
from config import Config

# Override Config paths for local execution
class LocalConfig(Config):
    def __init__(self):
        super().__init__()
        self.DATA_DIR = "/home/intelluxe/database/medical_complete"
        self.LOGS_DIR = "/home/intelluxe/logs"


async def main():
    """Main entry point for smart PubMed download"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart PubMed Downloader")
    parser.add_argument("command", nargs="?", default="download", 
                       choices=["download", "status", "reset"],
                       help="Command to execute")
    parser.add_argument("--data-dir", type=Path,
                       default=Path("/home/intelluxe/database/medical_complete/pubmed"),
                       help="Output directory for downloaded data")
    parser.add_argument("--force-fresh", action="store_true", 
                       help="Force fresh download (reset all states)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    parser.add_argument("--baseline-only", action="store_true",
                       help="Download only baseline files (not updates)")
    parser.add_argument("--max-concurrent", type=int, default=3,
                       help="Maximum concurrent downloads")
    
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
    """Run smart download of PubMed data"""
    logger.info("Starting smart PubMed download (~220GB)")
    
    local_config = LocalConfig()
    async with SmartPubMedDownloader(output_dir=args.data_dir, config=local_config) as downloader:
        # Show initial status
        initial_status = await downloader.get_download_status()
        total_files = len(downloader.baseline_files) + len(downloader.update_files)
        completed_files = len([f for f in downloader.all_articles if f.get('downloaded')])
        
        logger.info(f"Initial status: {completed_files}/{total_files} files downloaded")
        logger.info(f"Total articles parsed: {len(downloader.all_articles)}")
        
        if initial_status.get('ready_for_retry'):
            logger.info("Previous failed downloads detected - resuming with smart retry")
        
        if args.force_fresh:
            logger.info("Force fresh download requested - clearing all state")
            await downloader.reset_download_state()
        
        # Start the download process
        logger.info("Beginning smart download process...")
        start_time = datetime.now()
        
        try:
            # Download baseline files (most articles)
            if not args.baseline_only:
                logger.info("Phase 1: Downloading baseline PubMed files")
            
            await downloader.download_and_parse_all(
                baseline_only=args.baseline_only,
                max_concurrent=args.max_concurrent
            )
            
            # Get final status
            final_status = await downloader.get_download_status()
            duration = datetime.now() - start_time
            
            logger.info("✅ PubMed download completed successfully!")
            logger.info(f"   Articles downloaded: {len(downloader.all_articles)}")
            logger.info(f"   Files processed: {final_status['progress']['completed']}")
            logger.info(f"   Total duration: {duration}")
            logger.info(f"   Average speed: {len(downloader.all_articles) / duration.total_seconds():.1f} articles/sec")
            
            # Save final state
            state_file = args.data_dir / "pubmed_download_state.json"
            with open(state_file, 'w') as f:
                json.dump({
                    'completion_time': datetime.now().isoformat(),
                    'total_articles': len(downloader.all_articles),
                    'duration_seconds': duration.total_seconds(),
                    'final_status': final_status
                }, f, indent=2)
            
            logger.info(f"Download state saved to: {state_file}")
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            
            # Save error state for analysis
            error_file = args.data_dir / "pubmed_download_errors.json"
            error_info = {
                'error_time': datetime.now().isoformat(),
                'error_message': str(e),
                'partial_articles': len(downloader.all_articles),
                'state': await downloader.get_download_status()
            }
            
            with open(error_file, 'w') as f:
                json.dump(error_info, f, indent=2)
            
            logger.info(f"Error state saved to: {error_file}")
            logger.info("You can resume the download later using the same command")
            raise


async def show_status(args, logger):
    """Show current download status"""
    logger.info("Checking PubMed download status")
    
    local_config = LocalConfig()
    async with SmartPubMedDownloader(output_dir=args.data_dir, config=local_config) as downloader:
        status = await downloader.get_download_status()
        
        print(f"\n📊 PubMed Download Status")
        print(f"   Output directory: {args.data_dir}")
        print(f"   Articles downloaded: {len(downloader.all_articles)}")
        print(f"   Progress: {status['progress']['completed']}/{status['progress']['total_sources']} sources")
        print(f"   State: {status.get('state', 'unknown')}")
        
        if status.get('ready_for_retry'):
            print(f"   ⚠️  Ready for retry - previous downloads failed")
            print(f"   Next retry available: {status.get('next_retry_time', 'now')}")
        
        if status.get('rate_limited_sources'):
            print(f"   🚫 Rate limited sources: {len(status['rate_limited_sources'])}")
        
        # Check for state files
        state_file = args.data_dir / "pubmed_download_state.json"
        error_file = args.data_dir / "pubmed_download_errors.json"
        
        if state_file.exists():
            with open(state_file) as f:
                state_data = json.load(f)
            print(f"   ✅ Last completion: {state_data.get('completion_time')}")
            print(f"   📈 Last run articles: {state_data.get('total_articles')}")
        
        if error_file.exists():
            with open(error_file) as f:
                error_data = json.load(f)
            print(f"   ❌ Last error: {error_data.get('error_time')}")
            print(f"   💾 Partial progress: {error_data.get('partial_articles')} articles")


async def reset_downloads(args, logger):
    """Reset download state and start fresh"""
    logger.info("Resetting PubMed download state")
    
    local_config = LocalConfig()
    async with SmartPubMedDownloader(output_dir=args.data_dir, config=local_config) as downloader:
        await downloader.reset_download_state()
        
        # Remove state files
        state_files = [
            args.data_dir / "pubmed_download_state.json",
            args.data_dir / "pubmed_download_errors.json"
        ]
        
        for state_file in state_files:
            if state_file.exists():
                state_file.unlink()
                logger.info(f"Removed: {state_file}")
        
        logger.info("✅ PubMed download state reset - ready for fresh download")


if __name__ == "__main__":
    asyncio.run(main())