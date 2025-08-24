#!/usr/bin/env python3
"""
Smart Health Information download script - integrates with medical-mirrors system
Handles API rate limits, network issues, and state persistence for health topics, exercises, and nutrition data
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

from health_info.smart_downloader import SmartHealthInfoDownloader

# Import Config and override paths for non-Docker execution
from config import Config

# Override Config paths for local execution
class LocalConfig(Config):
    def __init__(self):
        super().__init__()
        self.DATA_DIR = "/home/intelluxe/database/medical_complete"
        self.LOGS_DIR = "/home/intelluxe/logs"
    
    def get_health_info_data_dir(self):
        return "/home/intelluxe/database/medical_complete/health_info"


async def main():
    """Main entry point for smart Health Information download"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart Health Information Downloader")
    parser.add_argument("command", nargs="?", default="download", 
                       choices=["download", "status", "reset"],
                       help="Command to execute")
    parser.add_argument("--data-dir", type=Path,
                       default=Path("/home/intelluxe/database/medical_complete/health_info"),
                       help="Output directory for downloaded data")
    parser.add_argument("--force-fresh", action="store_true", 
                       help="Force fresh download (reset all states)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    parser.add_argument("--max-concurrent", type=int, default=3,
                       help="Maximum concurrent API requests")
    parser.add_argument("--health-topics-only", action="store_true",
                       help="Download only health topics")
    parser.add_argument("--exercises-only", action="store_true",
                       help="Download only exercise data")
    parser.add_argument("--food-only", action="store_true",
                       help="Download only food/nutrition data")
    
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
    """Run smart download of health information data"""
    logger.info("Starting smart health information download (~100MB)")
    
    local_config = LocalConfig()
    async with SmartHealthInfoDownloader(output_dir=args.data_dir, config=local_config) as downloader:
        # Show initial status
        initial_status = await downloader.get_download_status()
        logger.info(f"Initial status: {initial_status['progress']['completed']}/"
                   f"{initial_status['progress']['total_sources']} sources completed")
        
        if initial_status.get('ready_for_retry'):
            logger.info("Previous failed downloads detected - resuming with smart retry")
        
        if args.force_fresh:
            logger.info("Force fresh download requested - clearing all state")
            await downloader.reset_download_state()
        
        # Configure download options
        download_options = {
            'max_concurrent': args.max_concurrent,
            'force_fresh': args.force_fresh
        }
        
        # Handle selective downloads
        if args.health_topics_only:
            logger.info("Downloading health topics only")
        elif args.exercises_only:
            logger.info("Downloading exercises only")
        elif args.food_only:
            logger.info("Downloading food/nutrition data only")
        else:
            logger.info("Downloading all health information sources")
        
        # Start the download process
        logger.info("Beginning smart download process...")
        start_time = datetime.now()
        
        try:
            # Run the smart download
            result = await downloader.download_and_parse_all(**download_options)
            
            # Get final status
            final_status = await downloader.get_download_status()
            duration = datetime.now() - start_time
            
            logger.info("✅ Health information download completed successfully!")
            logger.info(f"   Health topics: {result.get('total_health_topics', 0)}")
            logger.info(f"   Exercises: {result.get('total_exercises', 0)}")
            logger.info(f"   Food items: {result.get('total_food_items', 0)}")
            logger.info(f"   Sources completed: {len(result.get('successful_sources', []))}")
            logger.info(f"   Total duration: {duration}")
            
            # Save final state
            state_file = args.data_dir / "health_info_download_state.json"
            with open(state_file, 'w') as f:
                json.dump({
                    'completion_time': datetime.now().isoformat(),
                    'total_health_topics': result.get('total_health_topics', 0),
                    'total_exercises': result.get('total_exercises', 0),
                    'total_food_items': result.get('total_food_items', 0),
                    'duration_seconds': duration.total_seconds(),
                    'final_status': final_status,
                    'download_result': result
                }, f, indent=2)
            
            logger.info(f"Download state saved to: {state_file}")
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            
            # Save error state for analysis
            error_file = args.data_dir / "health_info_download_errors.json"
            partial_status = await downloader.get_download_status()
            error_info = {
                'error_time': datetime.now().isoformat(),
                'error_message': str(e),
                'partial_status': partial_status
            }
            
            with open(error_file, 'w') as f:
                json.dump(error_info, f, indent=2)
            
            logger.info(f"Error state saved to: {error_file}")
            logger.info("You can resume the download later using the same command")
            raise


async def show_status(args, logger):
    """Show current download status"""
    logger.info("Checking health information download status")
    
    local_config = LocalConfig()
    async with SmartHealthInfoDownloader(output_dir=args.data_dir, config=local_config) as downloader:
        status = await downloader.get_download_status()
        
        print(f"\n📊 Health Information Download Status")
        print(f"   Output directory: {args.data_dir}")
        print(f"   Progress: {status['progress']['completed']}/{status['progress']['total_sources']} sources")
        print(f"   State: {status.get('state', 'unknown')}")
        
        if status.get('totals'):
            totals = status['totals']
            print(f"   Health topics: {totals.get('health_topics', 0)}")
            print(f"   Exercises: {totals.get('exercises', 0)}")
            print(f"   Food items: {totals.get('food_items', 0)}")
        
        if status.get('ready_for_retry'):
            print(f"   ⚠️  Ready for retry - previous downloads failed")
            print(f"   Next retry available: {status.get('next_retry_time', 'now')}")
        
        if status.get('rate_limited_sources'):
            print(f"   🚫 Rate limited sources: {len(status['rate_limited_sources'])}")
            for source in status['rate_limited_sources']:
                print(f"      - {source}")
        
        # Check for downloaded files
        data_files = list(args.data_dir.glob("*_complete.json"))
        if data_files:
            print(f"   💾 Downloaded files: {len(data_files)}")
            for data_file in data_files:
                file_size = data_file.stat().st_size / 1024  # KB
                print(f"      - {data_file.name} ({file_size:.1f} KB)")
        
        # Check for state files
        state_file = args.data_dir / "health_info_download_state.json"
        error_file = args.data_dir / "health_info_download_errors.json"
        
        if state_file.exists():
            with open(state_file) as f:
                state_data = json.load(f)
            print(f"   ✅ Last completion: {state_data.get('completion_time')}")
            print(f"   📈 Last run totals: Health({state_data.get('total_health_topics', 0)}), "
                  f"Exercise({state_data.get('total_exercises', 0)}), "
                  f"Food({state_data.get('total_food_items', 0)})")
        
        if error_file.exists():
            with open(error_file) as f:
                error_data = json.load(f)
            print(f"   ❌ Last error: {error_data.get('error_time')}")
            print(f"   💾 Error message: {error_data.get('error_message', 'Unknown')}")


async def reset_downloads(args, logger):
    """Reset download state and start fresh"""
    logger.info("Resetting health information download state")
    
    local_config = LocalConfig()
    async with SmartHealthInfoDownloader(output_dir=args.data_dir, config=local_config) as downloader:
        await downloader.reset_download_state()
        
        # Remove state files
        state_files = [
            args.data_dir / "health_info_download_state.json",
            args.data_dir / "health_info_download_errors.json"
        ]
        
        for state_file in state_files:
            if state_file.exists():
                state_file.unlink()
                logger.info(f"Removed: {state_file}")
        
        # Optionally remove downloaded data files
        response = input("Remove all downloaded health information data files? [y/N]: ")
        if response.lower() in ['y', 'yes']:
            data_files = list(args.data_dir.glob("*_complete.json"))
            for data_file in data_files:
                data_file.unlink()
                logger.info(f"Removed: {data_file}")
        
        logger.info("✅ Health information download state reset - ready for fresh download")


if __name__ == "__main__":
    asyncio.run(main())