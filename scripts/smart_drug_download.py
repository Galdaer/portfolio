#!/usr/bin/env python3
"""
Smart Drug Download script - integrates with medical-mirrors system
Handles rate limits, large file downloads, and state persistence for all drug data sources
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

from drugs.smart_downloader import SmartDrugDownloader
from config import Config

# Override Config paths for local execution
class LocalConfig(Config):
    def __init__(self):
        super().__init__()
        self.DATA_DIR = "/home/intelluxe/database/medical_complete"
        self.LOGS_DIR = "/home/intelluxe/logs"


async def main():
    """Main entry point for smart drug download"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart Drug Database Downloader")
    parser.add_argument("command", nargs="?", default="download", 
                       choices=["download", "status", "reset"],
                       help="Command to execute")
    parser.add_argument("--data-dir", type=Path,
                       default=Path("/home/intelluxe/database/medical_complete"),
                       help="Output directory for downloaded data")
    parser.add_argument("--force-fresh", action="store_true", 
                       help="Force fresh download (reset all states)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    parser.add_argument("--fda-only", action="store_true",
                       help="Download only FDA drug data")
    parser.add_argument("--rxclass-only", action="store_true",
                       help="Download only RxClass therapeutic classifications")
    parser.add_argument("--max-concurrent", type=int, default=5,
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
    """Run smart download of drug data from all sources"""
    logger.info("Starting smart drug database download (FDA + RxClass)")
    
    local_config = LocalConfig()
    async with SmartDrugDownloader(output_dir=args.data_dir, config=local_config) as downloader:
        # Show initial status
        initial_status = await downloader.get_download_status()
        logger.info(f"Initial status: {initial_status['progress']['completed']}/"
                   f"{initial_status['progress']['total_sources']} sources completed")
        
        if initial_status.get('ready_for_retry'):
            logger.info("Previous failed downloads detected - resuming with smart retry")
        
        if args.force_fresh:
            logger.info("Force fresh download requested - clearing all state")
            await downloader.reset_download_state()
        
        # Configure download scope
        sources = None
        if args.fda_only:
            sources = ['fda']
            logger.info("Downloading FDA drug data only")
        elif args.rxclass_only:
            sources = ['rxclass']
            logger.info("Downloading RxClass therapeutic classifications only")
        else:
            logger.info("Downloading complete drug databases (FDA + RxClass)")
        
        # Start the download process
        logger.info("Beginning smart download process...")
        start_time = datetime.now()
        
        try:
            # Run the unified smart download
            result = await downloader.download_all_drug_data(
                force_fresh=args.force_fresh,
                complete_dataset=True,
                sources=sources
            )
            
            # Get final status
            final_status = await downloader.get_download_status()
            duration = datetime.now() - start_time
            
            logger.info("✅ Drug download completed successfully!")
            logger.info(f"   Sources processed: {result.get('total_sources_processed', 0)}")
            logger.info(f"   Drugs processed: {result.get('total_drugs_processed', 0)}")
            logger.info(f"   Success rate: {result.get('success_rate', 0):.1f}%")
            logger.info(f"   Total duration: {duration}")
            
            # Save final state
            state_file = args.data_dir / "drug_download_state.json"
            with open(state_file, 'w') as f:
                json.dump({
                    'completion_time': datetime.now().isoformat(),
                    'total_drugs': result.get('total_drugs_processed', 0),
                    'duration_seconds': duration.total_seconds(),
                    'final_status': final_status,
                    'download_result': result
                }, f, indent=2)
            
            logger.info(f"Download state saved to: {state_file}")
            
        except KeyboardInterrupt:
            # Handle graceful shutdown on interrupt
            duration = datetime.now() - start_time
            logger.warning("⚠️  Download interrupted by user")
            
            try:
                partial_status = await downloader.get_download_status()
                logger.info(f"   Sources completed: {partial_status['progress']['completed']}")
            except Exception:
                logger.info("   Partial progress information unavailable")
            
            logger.info(f"   Time elapsed: {duration}")
            
            # Save interrupt state for resume
            interrupt_file = args.data_dir / "drug_download_interrupted.json"
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
            
            logger.info(f"📁 Interrupted state saved to: {interrupt_file}")
            logger.info("💡 Resume with the same command - download will continue from last checkpoint")
            
            # Exit cleanly
            raise
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            
            # Save error state for analysis
            error_file = args.data_dir / "drug_download_errors.json"
            try:
                partial_status = await downloader.get_download_status()
            except Exception:
                partial_status = {"error": "Failed to get status"}
                
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
    logger.info("Checking drug download status")
    
    local_config = LocalConfig()
    async with SmartDrugDownloader(output_dir=args.data_dir, config=local_config) as downloader:
        status = await downloader.get_download_status()
        
        print(f"\n📊 Drug Database Download Status")
        print(f"   Output directory: {args.data_dir}")
        print(f"   Progress: {status['progress']['completed']}/{status['progress']['total_sources']} sources")
        print(f"   Completion rate: {status['progress']['completion_rate']:.1f}%")
        print(f"   Total drugs processed: {status.get('total_drugs_processed', 0)}")
        
        if status.get('ready_for_retry'):
            print(f"   ⚠️  Ready for retry: {len(status['ready_for_retry'])} sources")
        
        if status.get('next_retry_times'):
            print(f"   🚫 Rate limited sources: {len(status['next_retry_times'])}")
        
        # Show source-specific details
        source_details = status.get('source_details', {})
        if source_details:
            print(f"\n📋 Source Details:")
            for source_name, source_status in source_details.items():
                print(f"   {source_name.upper()}:")
                if 'progress' in source_status:
                    source_progress = source_status['progress']
                    print(f"     Progress: {source_progress.get('completed', 0)}/{source_progress.get('total_sources', 0)}")
                    print(f"     Completion: {source_progress.get('completion_rate', 0):.1f}%")
        
        # Check for downloaded files
        data_files = []
        for pattern in ["**/*.json", "**/*.zip", "**/*.txt", "**/*.csv"]:
            data_files.extend(args.data_dir.glob(pattern))
        
        if data_files:
            total_size = sum(f.stat().st_size for f in data_files) / (1024 * 1024)  # MB
            print(f"   💾 Downloaded files: {len(data_files)} ({total_size:.1f} MB)")
        
        # Check for state files
        state_file = args.data_dir / "drug_download_state.json"
        error_file = args.data_dir / "drug_download_errors.json"
        
        if state_file.exists():
            with open(state_file) as f:
                state_data = json.load(f)
            print(f"   ✅ Last completion: {state_data.get('completion_time', 'Unknown')}")
            print(f"   📈 Last run drugs: {state_data.get('total_drugs', 0)}")
        
        if error_file.exists():
            with open(error_file) as f:
                error_data = json.load(f)
            print(f"   ❌ Last error: {error_data.get('error_time', 'Unknown')}")
            print(f"   💾 Error message: {error_data.get('error_message', 'Unknown')}")


async def reset_downloads(args, logger):
    """Reset download state and start fresh"""
    logger.info("Resetting drug download state")
    
    local_config = LocalConfig()
    async with SmartDrugDownloader(output_dir=args.data_dir, config=local_config) as downloader:
        await downloader.reset_download_state()
        
        # Remove state files
        state_files = [
            args.data_dir / "drug_download_state.json",
            args.data_dir / "drug_download_errors.json",
            args.data_dir / "drug_download_interrupted.json"
        ]
        
        for state_file in state_files:
            if state_file.exists():
                state_file.unlink()
                logger.info(f"Removed: {state_file}")
        
        # Optionally remove downloaded data files
        response = input("Remove all downloaded drug data files? [y/N]: ")
        if response.lower() in ['y', 'yes']:
            patterns = ["**/*.json", "**/*.zip", "**/*.txt", "**/*.csv"]
            for pattern in patterns:
                data_files = list(args.data_dir.glob(pattern))
                for data_file in data_files:
                    if data_file.name not in ['drug_download_state.json', 'drug_download_errors.json']:
                        data_file.unlink()
                        logger.info(f"Removed: {data_file}")
        
        logger.info("✅ Drug download state reset - ready for fresh download")


if __name__ == "__main__":
    asyncio.run(main())