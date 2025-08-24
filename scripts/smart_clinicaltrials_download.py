#!/usr/bin/env python3
"""
Smart ClinicalTrials download script - integrates with medical-mirrors system
Handles API rate limits, network issues, and state persistence for ClinicalTrials.gov data
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

from clinicaltrials.smart_downloader import SmartClinicalTrialsDownloader
from config import Config

# Override Config paths for local execution
class LocalConfig(Config):
    def __init__(self):
        super().__init__()
        self.DATA_DIR = "/home/intelluxe/database/medical_complete"
        self.LOGS_DIR = "/home/intelluxe/logs"


async def main():
    """Main entry point for smart ClinicalTrials download"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart ClinicalTrials.gov Downloader")
    parser.add_argument("command", nargs="?", default="download", 
                       choices=["download", "status", "reset"],
                       help="Command to execute")
    parser.add_argument("--data-dir", type=Path,
                       default=Path("/home/intelluxe/database/medical_complete/clinicaltrials"),
                       help="Output directory for downloaded data")
    parser.add_argument("--force-fresh", action="store_true", 
                       help="Force fresh download (reset all states)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    parser.add_argument("--max-concurrent", type=int, default=10,
                       help="Maximum concurrent API requests")
    parser.add_argument("--batch-size", type=int, default=1000,
                       help="Number of studies per API request")
    parser.add_argument("--study-limit", type=int, 
                       help="Limit total studies downloaded (for testing)")
    
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
    """Run smart download of ClinicalTrials data"""
    logger.info("Starting smart ClinicalTrials.gov download (~500MB)")
    
    local_config = LocalConfig()
    async with SmartClinicalTrialsDownloader(output_dir=args.data_dir, config=local_config) as downloader:
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
            'batch_size': args.batch_size
        }
        
        if args.study_limit:
            download_options['study_limit'] = args.study_limit
            logger.info(f"Limiting download to {args.study_limit} studies")
        
        # Start the download process
        logger.info("Beginning smart download process...")
        start_time = datetime.now()
        
        try:
            # Run the smart download
            result = await downloader.download_all_clinical_trials(
                force_fresh=args.force_fresh,
                complete_dataset=True
            )
            
            # Get final status
            final_status = await downloader.get_download_status()
            duration = datetime.now() - start_time
            
            logger.info("✅ ClinicalTrials download completed successfully!")
            logger.info(f"   Studies downloaded: {result.get('total_studies', 0)}")
            logger.info(f"   Sources completed: {final_status['progress']['completed']}")
            logger.info(f"   Total duration: {duration}")
            logger.info(f"   Average speed: {result.get('total_studies', 0) / max(duration.total_seconds(), 1):.1f} studies/sec")
            
            # Save final state
            state_file = args.data_dir / "clinicaltrials_download_state.json"
            with open(state_file, 'w') as f:
                json.dump({
                    'completion_time': datetime.now().isoformat(),
                    'total_studies': result.get('total_studies', 0),
                    'duration_seconds': duration.total_seconds(),
                    'final_status': final_status,
                    'download_result': result
                }, f, indent=2)
            
            logger.info(f"Download state saved to: {state_file}")
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            
            # Save error state for analysis
            error_file = args.data_dir / "clinicaltrials_download_errors.json"
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
    logger.info("Checking ClinicalTrials download status")
    
    local_config = LocalConfig()
    async with SmartClinicalTrialsDownloader(output_dir=args.data_dir, config=local_config) as downloader:
        status = await downloader.get_download_status()
        
        print(f"\n📊 ClinicalTrials.gov Download Status")
        print(f"   Output directory: {args.data_dir}")
        print(f"   Progress: {status['progress']['completed']}/{status['progress']['total_sources']} sources")
        print(f"   State: {status.get('state', 'unknown')}")
        
        if status.get('ready_for_retry'):
            print(f"   ⚠️  Ready for retry - previous downloads failed")
            print(f"   Next retry available: {status.get('next_retry_time', 'now')}")
        
        if status.get('rate_limited_sources'):
            print(f"   🚫 Rate limited sources: {len(status['rate_limited_sources'])}")
        
        # Check for downloaded files
        data_files = list(args.data_dir.glob("*.json")) + list(args.data_dir.glob("*.xml"))
        if data_files:
            total_size = sum(f.stat().st_size for f in data_files) / (1024 * 1024)  # MB
            print(f"   💾 Downloaded files: {len(data_files)} ({total_size:.1f} MB)")
        
        # Check for state files
        state_file = args.data_dir / "clinicaltrials_download_state.json"
        error_file = args.data_dir / "clinicaltrials_download_errors.json"
        
        if state_file.exists():
            with open(state_file) as f:
                state_data = json.load(f)
            print(f"   ✅ Last completion: {state_data.get('completion_time')}")
            print(f"   📈 Last run studies: {state_data.get('total_studies')}")
        
        if error_file.exists():
            with open(error_file) as f:
                error_data = json.load(f)
            print(f"   ❌ Last error: {error_data.get('error_time')}")
            print(f"   💾 Error message: {error_data.get('error_message', 'Unknown')}")


async def reset_downloads(args, logger):
    """Reset download state and start fresh"""
    logger.info("Resetting ClinicalTrials download state")
    
    local_config = LocalConfig()
    async with SmartClinicalTrialsDownloader(output_dir=args.data_dir, config=local_config) as downloader:
        await downloader.reset_download_state()
        
        # Remove state files
        state_files = [
            args.data_dir / "clinicaltrials_download_state.json",
            args.data_dir / "clinicaltrials_download_errors.json"
        ]
        
        for state_file in state_files:
            if state_file.exists():
                state_file.unlink()
                logger.info(f"Removed: {state_file}")
        
        # Optionally remove downloaded data files
        response = input("Remove all downloaded ClinicalTrials data files? [y/N]: ")
        if response.lower() in ['y', 'yes']:
            data_files = list(args.data_dir.glob("*.json")) + list(args.data_dir.glob("*.xml"))
            for data_file in data_files:
                data_file.unlink()
                logger.info(f"Removed: {data_file}")
        
        logger.info("✅ ClinicalTrials download state reset - ready for fresh download")


if __name__ == "__main__":
    asyncio.run(main())