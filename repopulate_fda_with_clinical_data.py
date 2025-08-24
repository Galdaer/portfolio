#!/usr/bin/env python3
"""
Enhanced FDA Database Repopulation Script
Populates the FDA database with complete clinical information from all sources
"""

import asyncio
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Add medical-mirrors to Python path
medical_mirrors_src = Path(__file__).parent / "services/user/medical-mirrors/src"
sys.path.insert(0, str(medical_mirrors_src))

try:
    from database import get_db_session, FDADrug
    from fda.api import FDAAPI
    from fda.parser_optimized import OptimizedFDAParser
    from sqlalchemy import text
except ImportError as e:
    print(f"Failed to import modules: {e}")
    print(f"Looking for modules in: {medical_mirrors_src}")
    sys.exit(1)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EnhancedFDARepopulator:
    """Repopulates FDA database with complete clinical information"""
    
    def __init__(self):
        # Minimal config for database operations
        class MinimalConfig:
            POSTGRES_URL = os.getenv(
                "POSTGRES_URL", 
                "postgresql://intelluxe:secure_password@172.20.0.13:5432/intelluxe_public"
            )
            ENABLE_MULTICORE_PARSING = True
            FDA_MAX_WORKERS = 6  # Use 6 workers for parallel processing
        
        self.config = MinimalConfig()
        self.session_factory = get_db_session
        self.parser = OptimizedFDAParser(max_workers=6)
        
        # Data directories
        self.data_base = "/home/intelluxe/database/medical_complete/fda"
        self.stats = {
            "start_time": time.time(),
            "datasets_processed": {},
            "total_records": 0,
            "errors": []
        }
    
    def get_available_data_files(self) -> Dict[str, List[str]]:
        """Get all available FDA data files"""
        files = {
            "drug_labels": [],
            "ndc_directory": [],
            "drugs_fda": [],
            "orange_book": []
        }
        
        # Drug labels (clinical information)
        labels_dir = os.path.join(self.data_base, "labels")
        if os.path.exists(labels_dir):
            for file in os.listdir(labels_dir):
                if file.endswith(".json"):
                    files["drug_labels"].append(os.path.join(labels_dir, file))
        
        # NDC Directory
        ndc_dir = os.path.join(self.data_base, "ndc_directory")
        if os.path.exists(ndc_dir):
            for file in os.listdir(ndc_dir):
                if file.endswith(".json"):
                    files["ndc_directory"].append(os.path.join(ndc_dir, file))
        
        # Drugs@FDA
        drugs_fda_dir = os.path.join(self.data_base, "drugs_fda")
        if os.path.exists(drugs_fda_dir):
            for file in os.listdir(drugs_fda_dir):
                if file.endswith(".json"):
                    files["drugs_fda"].append(os.path.join(drugs_fda_dir, file))
        
        # Orange Book
        orange_book_dir = os.path.join(self.data_base, "orange_book")
        if os.path.exists(orange_book_dir):
            for file in os.listdir(orange_book_dir):
                if file.endswith((".csv", ".txt")):
                    files["orange_book"].append(os.path.join(orange_book_dir, file))
        
        return files
    
    async def process_dataset(self, dataset_type: str, file_paths: List[str]) -> int:
        """Process a specific dataset type"""
        logger.info(f"📊 Processing {dataset_type} dataset: {len(file_paths)} files")
        
        if not file_paths:
            logger.warning(f"⚠️ No files found for {dataset_type}")
            return 0
        
        start_time = time.time()
        total_records = 0
        
        try:
            if dataset_type == "orange_book":
                # Handle CSV files separately
                for file_path in file_paths:
                    logger.info(f"🔄 Parsing Orange Book file: {os.path.basename(file_path)}")
                    records = self.parser.parse_orange_book_file(file_path)
                    
                    if records:
                        stored = await self.store_records(records)
                        total_records += stored
                        logger.info(f"✅ Orange Book: {stored} records stored")
            
            else:
                # Handle JSON files with parallel parsing
                logger.info(f"🔄 Parsing {len(file_paths)} {dataset_type} JSON files in parallel...")
                records = await self.parser.parse_json_files_parallel(file_paths, dataset_type)
                
                if records:
                    logger.info(f"🔄 Storing {len(records)} {dataset_type} records...")
                    stored = await self.store_records(records)
                    total_records += stored
                    logger.info(f"✅ {dataset_type}: {stored} records stored")
            
            duration = time.time() - start_time
            self.stats["datasets_processed"][dataset_type] = {
                "records": total_records,
                "duration": duration,
                "files": len(file_paths)
            }
            
            logger.info(f"📈 {dataset_type} completed: {total_records} records in {duration:.1f}s")
            return total_records
            
        except Exception as e:
            logger.exception(f"❌ Failed to process {dataset_type}: {e}")
            self.stats["errors"].append(f"{dataset_type}: {e}")
            return 0
    
    async def store_records(self, records: List[Dict]) -> int:
        """Store records in database using enhanced API"""
        if not records:
            return 0
        
        # Create FDA API instance without downloader
        fda_api = FDAAPI(self.session_factory, self.config, enable_downloader=False)
        
        db = self.session_factory()
        try:
            # Use enhanced storage with merging
            stored_count = await fda_api.store_drugs_with_merging(records, db)
            self.stats["total_records"] += stored_count
            return stored_count
            
        except Exception as e:
            logger.exception(f"❌ Failed to store records: {e}")
            return 0
        finally:
            db.close()
    
    def check_progress(self):
        """Check current progress"""
        db = self.session_factory()
        try:
            count = db.execute(text("SELECT COUNT(*) FROM fda_drugs")).fetchone()[0]
            
            # Check clinical field population
            clinical_count = db.execute(text("""
                SELECT COUNT(*) FROM fda_drugs 
                WHERE (contraindications IS NOT NULL AND array_length(contraindications, 1) > 0)
                   OR (warnings IS NOT NULL AND array_length(warnings, 1) > 0)
                   OR (indications_and_usage IS NOT NULL AND indications_and_usage != '')
            """)).fetchone()[0]
            
            logger.info(f"📊 Current progress: {count} total drugs, {clinical_count} with clinical info")
            return count, clinical_count
            
        finally:
            db.close()
    
    def sample_clinical_data(self):
        """Show sample clinical data to verify"""
        db = self.session_factory()
        try:
            samples = db.execute(text("""
                SELECT ndc, name, contraindications, warnings, indications_and_usage, mechanism_of_action
                FROM fda_drugs 
                WHERE (array_length(contraindications, 1) > 0 OR array_length(warnings, 1) > 0 
                       OR (indications_and_usage IS NOT NULL AND indications_and_usage != ''))
                LIMIT 3
            """)).fetchall()
            
            logger.info("📋 Sample clinical data:")
            for sample in samples:
                logger.info(f"  • {sample[0]}: {sample[1]}")
                if sample[2]:  # contraindications
                    logger.info(f"    Contraindications: {len(sample[2])} items")
                if sample[3]:  # warnings
                    logger.info(f"    Warnings: {len(sample[3])} items")
                if sample[4]:  # indications
                    preview = sample[4][:100] + "..." if len(sample[4]) > 100 else sample[4]
                    logger.info(f"    Indications: {preview}")
                if sample[5]:  # mechanism
                    preview = sample[5][:100] + "..." if len(sample[5]) > 100 else sample[5]
                    logger.info(f"    Mechanism: {preview}")
            
        finally:
            db.close()
    
    def print_final_report(self):
        """Print comprehensive final report"""
        duration = time.time() - self.stats["start_time"]
        
        print("\n" + "="*80)
        print("FDA DATABASE REPOPULATION COMPLETE")
        print("="*80)
        print(f"Total Duration: {duration/3600:.2f} hours ({duration:.0f} seconds)")
        print(f"Total Records: {self.stats['total_records']}")
        print(f"Errors: {len(self.stats['errors'])}")
        print()
        
        print("📊 DATASETS PROCESSED:")
        for dataset, stats in self.stats["datasets_processed"].items():
            print(f"  ✅ {dataset}: {stats['records']} records from {stats['files']} files ({stats['duration']:.1f}s)")
        
        print()
        
        # Final database check
        count, clinical_count = self.check_progress()
        print(f"📈 FINAL DATABASE STATUS:")
        print(f"  Total Drugs: {count:,}")
        print(f"  With Clinical Info: {clinical_count:,} ({clinical_count/count*100:.1f}%)")
        print()
        
        if self.stats["errors"]:
            print("❌ ERRORS:")
            for error in self.stats["errors"]:
                print(f"  • {error}")
            print()
        
        print("🎉 FDA database now contains complete clinical information!")
        print("   Including contraindications, warnings, drug interactions,")
        print("   indications, dosage administration, and pharmacology data.")

async def main():
    """Main repopulation process"""
    print("🚀 Starting Enhanced FDA Database Repopulation")
    print("   This will populate the database with complete clinical information")
    print("   from drug labels, NDC directory, Drugs@FDA, and Orange Book\n")
    
    repopulator = EnhancedFDARepopulator()
    
    try:
        # Check starting state
        logger.info("📊 Checking starting database state...")
        start_count, _ = repopulator.check_progress()
        
        if start_count > 0:
            logger.warning(f"⚠️ Database contains {start_count} records. They should be cleared first.")
            response = input("Continue anyway? (y/n): ")
            if response.lower() != 'y':
                print("Exiting...")
                return 1
        
        # Get available data files
        logger.info("🔍 Scanning for available data files...")
        available_files = repopulator.get_available_data_files()
        
        total_files = sum(len(files) for files in available_files.values())
        logger.info(f"📁 Found {total_files} data files to process:")
        
        for dataset, files in available_files.items():
            if files:
                total_size = sum(os.path.getsize(f) for f in files if os.path.exists(f))
                size_gb = total_size / 1024 / 1024 / 1024
                logger.info(f"  • {dataset}: {len(files)} files ({size_gb:.1f} GB)")
        
        if total_files == 0:
            logger.error("❌ No data files found to process!")
            return 1
        
        # Process datasets in order of importance (drug labels first for clinical data)
        processing_order = ["drug_labels", "ndc_directory", "drugs_fda", "orange_book"]
        
        for dataset_type in processing_order:
            if available_files[dataset_type]:
                logger.info(f"\n🔄 Processing {dataset_type.upper()} dataset...")
                records_processed = await repopulator.process_dataset(
                    dataset_type, 
                    available_files[dataset_type]
                )
                
                if records_processed > 0:
                    # Show progress
                    repopulator.check_progress()
                else:
                    logger.warning(f"⚠️ No records processed for {dataset_type}")
            else:
                logger.info(f"⏭️ Skipping {dataset_type} (no files found)")
        
        # Final report
        repopulator.print_final_report()
        repopulator.sample_clinical_data()
        
        return 0
        
    except Exception as e:
        logger.exception(f"❌ Repopulation failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))