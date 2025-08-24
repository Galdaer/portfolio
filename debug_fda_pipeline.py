#!/usr/bin/env python3
"""
Debug runner for the complete FDA drug label parsing and database insertion pipeline
Tests the full workflow from download to database insertion
"""

import asyncio
import json
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
    from config import Config
    from database import get_db_session, FDADrug
    from fda.downloader import FDADownloader
    from fda.api import FDAAPI
    from fda.parser_optimized import OptimizedFDAParser
    from sqlalchemy import text, func
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

class FDAPipelineDebugger:
    """Comprehensive debugger for FDA drug label pipeline"""
    
    def __init__(self):
        self.config = Config()
        # Override data directory to avoid permission issues
        self.config.DATA_DIR = str(Path.home() / "fda_debug_data")
        self.downloader = FDADownloader()
        self.parser = OptimizedFDAParser(max_workers=2)  # Use 2 workers for testing
        self.session_factory = get_db_session
        self.stats = {
            "start_time": time.time(),
            "downloads": {},
            "parsing": {},
            "database": {},
            "errors": []
        }
    
    async def test_download_capabilities(self):
        """Test FDA data download capabilities"""
        logger.info("=== Testing FDA Download Capabilities ===")
        
        try:
            # Test individual dataset downloads (small samples)
            datasets_to_test = [
                ("drug_labels", "download_drug_labels"),
                ("ndc_directory", "download_ndc_directory"), 
                ("drugs_fda", "download_drugs_at_fda"),
                ("orange_book", "download_orange_book")
            ]
            
            for dataset_name, method_name in datasets_to_test:
                try:
                    logger.info(f"📥 Testing download: {dataset_name}")
                    start_time = time.time()
                    
                    if hasattr(self.downloader, method_name):
                        method = getattr(self.downloader, method_name)
                        result_dir = await method()
                        
                        duration = time.time() - start_time
                        self.stats["downloads"][dataset_name] = {
                            "success": True,
                            "duration": duration,
                            "directory": result_dir
                        }
                        
                        logger.info(f"✅ {dataset_name} downloaded in {duration:.1f}s to {result_dir}")
                    else:
                        logger.warning(f"⚠️ Method {method_name} not found")
                        
                except Exception as e:
                    logger.exception(f"❌ Download failed for {dataset_name}: {e}")
                    self.stats["downloads"][dataset_name] = {
                        "success": False,
                        "error": str(e)
                    }
                    self.stats["errors"].append(f"Download {dataset_name}: {e}")
            
            return len([d for d in self.stats["downloads"].values() if d.get("success", False)]) > 0
            
        except Exception as e:
            logger.exception(f"❌ Download testing failed: {e}")
            return False
        finally:
            await self.downloader.close()
    
    def test_file_availability(self):
        """Check what FDA files are available for parsing"""
        logger.info("=== Checking Available FDA Files ===")
        
        data_dir = self.config.get_fda_data_dir()
        logger.info(f"📁 FDA data directory: {data_dir}")
        
        available_files = {
            "ndc": [],
            "drugs_fda": [],
            "labels": [],
            "orange_book": []
        }
        
        # Check each dataset directory
        for dataset in available_files.keys():
            dataset_dir = os.path.join(data_dir, dataset)
            if os.path.exists(dataset_dir):
                for file in os.listdir(dataset_dir):
                    file_path = os.path.join(dataset_dir, file)
                    if os.path.isfile(file_path):
                        file_size = os.path.getsize(file_path) / 1024 / 1024  # MB
                        available_files[dataset].append({
                            "path": file_path,
                            "name": file,
                            "size_mb": file_size
                        })
        
        # Report findings
        total_files = 0
        for dataset, files in available_files.items():
            if files:
                total_size = sum(f["size_mb"] for f in files)
                logger.info(f"📊 {dataset}: {len(files)} files ({total_size:.1f} MB)")
                for file in files[:3]:  # Show first 3 files
                    logger.info(f"  • {file['name']} ({file['size_mb']:.1f} MB)")
                if len(files) > 3:
                    logger.info(f"  ... and {len(files) - 3} more files")
                total_files += len(files)
            else:
                logger.info(f"📊 {dataset}: No files found")
        
        logger.info(f"📊 Total available files: {total_files}")
        self.stats["files_available"] = total_files
        return available_files
    
    async def test_parsing_small_sample(self, available_files: Dict[str, List]):
        """Test parsing with a small sample of available files"""
        logger.info("=== Testing Parsing with Small Sample ===")
        
        parsing_results = {}
        
        for dataset_type, files in available_files.items():
            if not files:
                continue
                
            logger.info(f"🔄 Testing parsing for {dataset_type}")
            
            try:
                # Take first file or first few files for testing
                test_files = [f["path"] for f in files[:2]]  # Max 2 files per dataset
                
                start_time = time.time()
                
                if dataset_type in ["ndc", "drugs_fda", "labels"]:
                    # JSON datasets - use optimized parser
                    parsed_records = await self.parser.parse_json_files_parallel(test_files, dataset_type)
                elif dataset_type == "orange_book":
                    # CSV dataset - use single-threaded parsing
                    parsed_records = []
                    for file_path in test_files:
                        if file_path.endswith(('.csv', '.txt')):
                            records = self.parser.parse_orange_book_file(file_path)
                            parsed_records.extend(records)
                else:
                    continue
                
                duration = time.time() - start_time
                
                parsing_results[dataset_type] = {
                    "success": True,
                    "records_parsed": len(parsed_records),
                    "duration": duration,
                    "files_tested": len(test_files),
                    "sample_record": parsed_records[0] if parsed_records else None
                }
                
                logger.info(f"✅ {dataset_type}: {len(parsed_records)} records in {duration:.1f}s")
                
                # Show sample record structure
                if parsed_records:
                    sample = parsed_records[0]
                    logger.info(f"📋 Sample {dataset_type} record fields:")
                    for key, value in sample.items():
                        if isinstance(value, str) and len(value) > 50:
                            display_value = value[:50] + "..."
                        else:
                            display_value = value
                        logger.info(f"  • {key}: {display_value}")
                
            except Exception as e:
                logger.exception(f"❌ Parsing failed for {dataset_type}: {e}")
                parsing_results[dataset_type] = {
                    "success": False,
                    "error": str(e)
                }
                self.stats["errors"].append(f"Parsing {dataset_type}: {e}")
        
        self.stats["parsing"] = parsing_results
        return parsing_results
    
    async def test_database_integration(self, parsing_results: Dict[str, Any]):
        """Test database integration with parsed results"""
        logger.info("=== Testing Database Integration ===")
        
        db = self.session_factory()
        try:
            # Get baseline count
            initial_count = db.execute(text("SELECT COUNT(*) FROM fda_drugs")).fetchone()[0]
            logger.info(f"📊 Initial fda_drugs count: {initial_count}")
            
            # Test with each dataset type
            total_inserted = 0
            
            for dataset_type, results in parsing_results.items():
                if not results.get("success") or not results.get("sample_record"):
                    continue
                
                logger.info(f"💾 Testing database insertion for {dataset_type}")
                
                try:
                    # Create FDAAPI instance
                    fda_api = FDAAPI(self.session_factory, self.config)
                    
                    # Create small test dataset (max 5 records)
                    sample_record = results["sample_record"]
                    test_records = [sample_record.copy() for _ in range(min(5, results["records_parsed"]))]
                    
                    # Modify NDCs to avoid conflicts
                    for i, record in enumerate(test_records):
                        record["ndc"] = f"DEBUG-{dataset_type.upper()}-{i:03d}"
                    
                    # Test database storage
                    start_time = time.time()
                    stored_count = await fda_api.store_drugs_with_merging(test_records, db)
                    duration = time.time() - start_time
                    
                    total_inserted += stored_count
                    
                    logger.info(f"✅ {dataset_type}: {stored_count} records stored in {duration:.1f}s")
                    
                    self.stats["database"][dataset_type] = {
                        "success": True,
                        "records_stored": stored_count,
                        "duration": duration
                    }
                    
                except Exception as e:
                    logger.exception(f"❌ Database insertion failed for {dataset_type}: {e}")
                    self.stats["database"][dataset_type] = {
                        "success": False,
                        "error": str(e)
                    }
                    self.stats["errors"].append(f"Database {dataset_type}: {e}")
            
            # Verify final count
            final_count = db.execute(text("SELECT COUNT(*) FROM fda_drugs")).fetchone()[0]
            logger.info(f"📊 Final fda_drugs count: {final_count} (+{final_count - initial_count})")
            
            # Clean up debug records
            cleanup_result = db.execute(text("DELETE FROM fda_drugs WHERE ndc LIKE 'DEBUG-%'"))
            db.commit()
            logger.info(f"🧹 Cleaned up {cleanup_result.rowcount} debug records")
            
            return total_inserted > 0
            
        except Exception as e:
            logger.exception(f"❌ Database integration test failed: {e}")
            return False
        finally:
            db.close()
    
    def test_api_search_functionality(self):
        """Test FDA API search functionality"""
        logger.info("=== Testing FDA API Search Functionality ===")
        
        try:
            fda_api = FDAAPI(self.session_factory, self.config)
            
            # Test different search scenarios
            search_tests = [
                {"generic_name": "acetaminophen", "max_results": 5},
                {"ndc": "0777-3105", "max_results": 1},
                {"generic_name": "ibuprofen", "max_results": 3},
            ]
            
            search_results = {}
            
            for i, search_params in enumerate(search_tests):
                try:
                    results = asyncio.run(fda_api.search_drugs(**search_params))
                    search_results[f"test_{i+1}"] = {
                        "success": True,
                        "params": search_params,
                        "results_count": len(results),
                        "sample_result": results[0] if results else None
                    }
                    
                    logger.info(f"✅ Search test {i+1}: {len(results)} results for {search_params}")
                    
                except Exception as e:
                    logger.exception(f"❌ Search test {i+1} failed: {e}")
                    search_results[f"test_{i+1}"] = {
                        "success": False,
                        "params": search_params,
                        "error": str(e)
                    }
            
            self.stats["api_search"] = search_results
            return len([r for r in search_results.values() if r.get("success")]) > 0
            
        except Exception as e:
            logger.exception(f"❌ API search functionality test failed: {e}")
            return False
    
    def generate_debug_report(self):
        """Generate comprehensive debug report"""
        duration = time.time() - self.stats["start_time"]
        
        print("\n" + "="*80)
        print("FDA PIPELINE DEBUG REPORT")
        print("="*80)
        print(f"Total Duration: {duration:.1f} seconds")
        print(f"Errors: {len(self.stats['errors'])}")
        print()
        
        # Download Results
        if "downloads" in self.stats:
            print("📥 DOWNLOAD RESULTS:")
            for dataset, result in self.stats["downloads"].items():
                status = "✅" if result.get("success") else "❌"
                print(f"  {status} {dataset}: {result}")
            print()
        
        # File Availability
        if "files_available" in self.stats:
            print(f"📁 FILES AVAILABLE: {self.stats['files_available']} total files")
            print()
        
        # Parsing Results
        if "parsing" in self.stats:
            print("🔄 PARSING RESULTS:")
            for dataset, result in self.stats["parsing"].items():
                status = "✅" if result.get("success") else "❌"
                if result.get("success"):
                    print(f"  {status} {dataset}: {result['records_parsed']} records in {result['duration']:.1f}s")
                else:
                    print(f"  {status} {dataset}: {result.get('error', 'Unknown error')}")
            print()
        
        # Database Results
        if "database" in self.stats:
            print("💾 DATABASE RESULTS:")
            for dataset, result in self.stats["database"].items():
                status = "✅" if result.get("success") else "❌"
                if result.get("success"):
                    print(f"  {status} {dataset}: {result['records_stored']} stored in {result['duration']:.1f}s")
                else:
                    print(f"  {status} {dataset}: {result.get('error', 'Unknown error')}")
            print()
        
        # API Search Results
        if "api_search" in self.stats:
            print("🔍 API SEARCH RESULTS:")
            for test, result in self.stats["api_search"].items():
                status = "✅" if result.get("success") else "❌"
                if result.get("success"):
                    print(f"  {status} {test}: {result['results_count']} results")
                else:
                    print(f"  {status} {test}: {result.get('error', 'Unknown error')}")
            print()
        
        # Errors
        if self.stats["errors"]:
            print("❌ ERRORS:")
            for error in self.stats["errors"]:
                print(f"  • {error}")
            print()
        
        # Recommendations
        print("💡 RECOMMENDATIONS:")
        
        if not self.stats.get("files_available"):
            print("  • Download FDA data first using scripts/download_full_fda.py")
        
        if self.stats.get("errors"):
            print("  • Review error messages above for specific issues")
            print("  • Check database connectivity and permissions")
            print("  • Verify FDA data file formats and structures")
        
        success_count = 0
        total_tests = 0
        
        for category in ["downloads", "parsing", "database", "api_search"]:
            if category in self.stats:
                for result in self.stats[category].values():
                    total_tests += 1
                    if result.get("success"):
                        success_count += 1
        
        print(f"\n📊 OVERALL SUCCESS RATE: {success_count}/{total_tests} ({success_count/total_tests*100:.1f}%)")
        
        if success_count == total_tests:
            print("🎉 All pipeline components working correctly!")
            return 0
        else:
            print("⚠️ Some pipeline components need attention.")
            return 1

async def main():
    """Run comprehensive FDA pipeline debugging"""
    print("🔬 Starting Comprehensive FDA Pipeline Debug\n")
    
    debugger = FDAPipelineDebugger()
    
    try:
        # Test 1: Download capabilities (optional - may take time)
        # await debugger.test_download_capabilities()
        
        # Test 2: Check available files
        available_files = debugger.test_file_availability()
        
        # Test 3: Test parsing with small samples
        parsing_results = await debugger.test_parsing_small_sample(available_files)
        
        # Test 4: Test database integration
        await debugger.test_database_integration(parsing_results)
        
        # Test 5: Test API search functionality
        debugger.test_api_search_functionality()
        
        # Generate comprehensive report
        return debugger.generate_debug_report()
        
    except Exception as e:
        print(f"\n❌ Debug pipeline failed: {e}")
        logger.exception("Debug pipeline execution failed")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))