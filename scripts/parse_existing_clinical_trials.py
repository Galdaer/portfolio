#!/usr/bin/env python3
"""
Parse existing Clinical Trials compressed files into database
Uses existing compressed .json.gz files instead of re-downloading
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any

# Add medical-mirrors to Python path
medical_mirrors_src = str(Path(__file__).parent.parent / "services/user/medical-mirrors/src")
if medical_mirrors_src not in sys.path:
    sys.path.insert(0, medical_mirrors_src)

try:
    from clinicaltrials.api import ClinicalTrialsAPI
    from clinicaltrials.parser import ClinicalTrialsParser
    from config import Config
    from database import get_db_session
    from sqlalchemy.orm import sessionmaker
    from database import get_database_url, create_engine
except ImportError as e:
    print(f"Failed to import medical-mirrors modules: {e}")
    print("Make sure medical-mirrors service is properly installed")
    sys.exit(1)


class ExistingClinicalTrialsLoader:
    """Load existing compressed clinical trials files into database"""

    def __init__(self, data_dir: str = None):
        self.config = Config()
        self.data_dir = data_dir or "/home/intelluxe/database/medical_complete/clinicaltrials"
        self.logger = self._setup_logging()
        self.parser = ClinicalTrialsParser()
        
        # Set up database connection
        DATABASE_URL = get_database_url()
        self.engine = create_engine(DATABASE_URL)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Initialize API for database operations
        self.api = ClinicalTrialsAPI(self.SessionLocal, self.config)

        # Statistics
        self.stats = {
            "files_found": 0,
            "files_processed": 0,
            "files_failed": 0,
            "trials_inserted": 0,
            "trials_failed": 0,
            "errors": [],
        }

    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger("clinical_trials_loader")
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def find_compressed_files(self) -> list[str]:
        """Find all compressed clinical trials JSON files"""
        compressed_files = []
        
        data_path = Path(self.data_dir)
        if not data_path.exists():
            self.logger.error(f"Data directory does not exist: {self.data_dir}")
            return compressed_files
        
        # Find all .json.gz files
        for file_path in data_path.glob("*.json.gz"):
            # Skip the all_clinical_trials_complete.json file
            if "all_clinical_trials_complete.json" not in file_path.name:
                compressed_files.append(str(file_path))
        
        compressed_files.sort()  # Process in order
        self.stats["files_found"] = len(compressed_files)
        self.logger.info(f"Found {len(compressed_files)} compressed files to process")
        
        return compressed_files

    async def process_compressed_files(self, batch_size: int = 50) -> dict[str, Any]:
        """Process all compressed files in batches"""
        compressed_files = self.find_compressed_files()
        
        if not compressed_files:
            self.logger.error("No compressed files found")
            return {"success": False, "error": "No files found"}

        self.logger.info(f"Starting to process {len(compressed_files)} files in batches of {batch_size}")
        
        # Process files in batches
        for i in range(0, len(compressed_files), batch_size):
            batch_files = compressed_files[i:i + batch_size]
            self.logger.info(f"Processing batch {i // batch_size + 1}/{(len(compressed_files) + batch_size - 1) // batch_size} ({len(batch_files)} files)")
            
            try:
                await self._process_file_batch(batch_files)
                self.logger.info(f"Completed batch {i // batch_size + 1}, progress: {self.stats['files_processed']}/{self.stats['files_found']} files")
            except Exception as e:
                self.logger.exception(f"Failed to process batch: {e}")
                self.stats["errors"].append(f"Batch {i // batch_size + 1}: {str(e)}")

        # Final statistics
        self.logger.info("=== PROCESSING COMPLETE ===")
        self.logger.info(f"Files found: {self.stats['files_found']}")
        self.logger.info(f"Files processed: {self.stats['files_processed']}")
        self.logger.info(f"Files failed: {self.stats['files_failed']}")
        self.logger.info(f"Trials inserted: {self.stats['trials_inserted']}")
        self.logger.info(f"Trials failed: {self.stats['trials_failed']}")
        
        if self.stats["errors"]:
            self.logger.error(f"Encountered {len(self.stats['errors'])} errors:")
            for error in self.stats["errors"][-10:]:  # Show last 10 errors
                self.logger.error(f"  - {error}")

        return {
            "success": self.stats["files_failed"] == 0,
            "stats": self.stats,
        }

    async def _process_file_batch(self, file_paths: list[str]) -> None:
        """Process a batch of compressed files"""
        db = self.SessionLocal()
        try:
            all_trials = []
            
            # Parse all files in the batch
            for file_path in file_paths:
                try:
                    file_trials = self.parser.parse_json_file(file_path)
                    all_trials.extend(file_trials)
                    self.stats["files_processed"] += 1
                    
                    if len(file_trials) > 0:
                        self.logger.debug(f"Parsed {len(file_trials)} trials from {file_path}")
                    
                except Exception as e:
                    self.logger.warning(f"Failed to parse {file_path}: {e}")
                    self.stats["files_failed"] += 1
                    self.stats["errors"].append(f"Parse {file_path}: {str(e)}")

            # Store all trials from this batch
            if all_trials:
                try:
                    processed = await self.api.store_trials(all_trials, db)
                    self.stats["trials_inserted"] += processed
                    self.logger.info(f"Stored {processed} trials from batch of {len(file_paths)} files")
                except Exception as e:
                    self.logger.exception(f"Failed to store trials batch: {e}")
                    self.stats["trials_failed"] += len(all_trials)
                    self.stats["errors"].append(f"Store batch: {str(e)}")
            
        finally:
            db.close()


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Parse existing Clinical Trials compressed files")
    parser.add_argument("--data-dir", type=str,
                       default="/home/intelluxe/database/medical_complete/clinicaltrials",
                       help="Directory containing compressed files")
    parser.add_argument("--batch-size", type=int, default=50,
                       help="Number of files to process per batch")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    loader = ExistingClinicalTrialsLoader(data_dir=args.data_dir)

    try:
        result = await loader.process_compressed_files(batch_size=args.batch_size)
        
        if result["success"]:
            print("\n✅ Successfully processed all compressed files!")
            print(f"   Files processed: {result['stats']['files_processed']}")
            print(f"   Trials inserted: {result['stats']['trials_inserted']}")
        else:
            print("\n❌ Processing completed with errors")
            print(f"   Files processed: {result['stats']['files_processed']}")
            print(f"   Files failed: {result['stats']['files_failed']}")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n🛑 Processing cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Processing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())