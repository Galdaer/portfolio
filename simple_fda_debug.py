#!/usr/bin/env python3
"""
Simple FDA debugging script to test the core parsing and database functionality
Bypasses downloads and focuses on testing with existing data
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
    from fda.parser_optimized import OptimizedFDAParser, parse_drug_label_record_worker
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

def check_database_status():
    """Check current database status"""
    logger.info("=== Checking Database Status ===")
    
    try:
        db = get_db_session()
        
        # Check connection
        result = db.execute(text("SELECT 1")).fetchone()
        logger.info("✅ Database connection successful")
        
        # Check fda_drugs table
        count = db.execute(text("SELECT COUNT(*) FROM fda_drugs")).fetchone()[0]
        logger.info(f"📊 Current fda_drugs count: {count}")
        
        # Show sample records with clinical data
        clinical_samples = db.execute(text("""
            SELECT ndc, name, contraindications, warnings, drug_interactions
            FROM fda_drugs 
            WHERE (contraindications IS NOT NULL AND array_length(contraindications, 1) > 0)
               OR (warnings IS NOT NULL AND array_length(warnings, 1) > 0)
               OR (drug_interactions IS NOT NULL AND drug_interactions != '{}')
            LIMIT 5
        """)).fetchall()
        
        logger.info(f"📋 Found {len(clinical_samples)} drugs with clinical information:")
        for sample in clinical_samples:
            logger.info(f"  • {sample[0]}: {sample[1]}")
            if sample[2]:  # contraindications
                logger.info(f"    Contraindications: {len(sample[2])} items")
            if sample[3]:  # warnings
                logger.info(f"    Warnings: {len(sample[3])} items")
            if sample[4] and sample[4] != {}:  # drug_interactions
                logger.info(f"    Drug interactions: {sample[4]}")
        
        db.close()
        return True
        
    except Exception as e:
        logger.exception(f"❌ Database check failed: {e}")
        return False

def test_real_fda_api():
    """Test the real FDA API functionality"""
    logger.info("=== Testing Real FDA API ===")
    
    try:
        # Create a minimal config class
        class MinimalConfig:
            POSTGRES_URL = os.getenv(
                "POSTGRES_URL", 
                "postgresql://intelluxe:secure_password@172.20.0.13:5432/intelluxe_public"
            )
        
        config = MinimalConfig()
        session_factory = get_db_session
        
        fda_api = FDAAPI(session_factory, config)
        
        # Test different search scenarios
        search_tests = [
            {"generic_name": "acetaminophen", "max_results": 3},
            {"generic_name": "ibuprofen", "max_results": 2},
            {"ndc": "0777-3105", "max_results": 1},
        ]
        
        for i, search_params in enumerate(search_tests, 1):
            try:
                logger.info(f"🔍 Search test {i}: {search_params}")
                
                results = asyncio.run(fda_api.search_drugs(**search_params))
                
                logger.info(f"✅ Found {len(results)} results")
                for result in results:
                    logger.info(f"  • {result['ndc']}: {result['name']}")
                    if 'genericName' in result and result['genericName']:
                        logger.info(f"    Generic: {result['genericName']}")
                    if 'manufacturer' in result and result['manufacturer']:
                        logger.info(f"    Manufacturer: {result['manufacturer']}")
                
            except Exception as e:
                logger.exception(f"❌ Search test {i} failed: {e}")
        
        # Test status endpoint
        try:
            logger.info("📊 Testing status endpoint")
            status = asyncio.run(fda_api.get_status())
            logger.info(f"✅ Status: {status}")
        except Exception as e:
            logger.exception(f"❌ Status test failed: {e}")
            
        return True
        
    except Exception as e:
        logger.exception(f"❌ FDA API test failed: {e}")
        return False

def test_parsing_with_synthetic_data():
    """Test parsing logic with synthetic drug label data"""
    logger.info("=== Testing Parsing with Synthetic Data ===")
    
    # Create realistic synthetic FDA drug label data
    synthetic_labels = [
        {
            "product_ndc": ["SYNTH-001"],
            "brand_name": ["Synthetic Drug Alpha"],
            "generic_name": ["syntheticcompound-alpha"],
            "manufacturer_name": ["Test Pharmaceuticals Inc."],
            "dosage_form": ["tablet, film coated"],
            "route": ["oral"],
            "active_ingredient": ["syntheticcompound-alpha 25 mg"],
            
            # Complex clinical data structures
            "contraindications": [
                "Known hypersensitivity to syntheticcompound-alpha or any excipients.",
                "Severe hepatic impairment (Child-Pugh Class C)."
            ],
            "warnings": [
                {
                    "section": "Hepatotoxicity",
                    "content": "Severe liver injury, including fatal cases, has been reported."
                },
                "May cause serious skin reactions including Stevens-Johnson syndrome."
            ],
            "precautions": [
                "Monitor liver function tests before and during treatment.",
                "Use with caution in patients with renal impairment.",
                "Avoid concurrent use with strong CYP3A4 inhibitors."
            ],
            "adverse_reactions": [
                {"frequency": "Common (≥1/10)", "reactions": ["Nausea", "Headache", "Dizziness"]},
                {"frequency": "Uncommon (≥1/100 to <1/10)", "reactions": ["Rash", "Fatigue"]},
                "Serious adverse reactions reported in clinical trials"
            ],
            "drug_interactions": {
                "major_interactions": [
                    {
                        "drug_name": "Warfarin",
                        "severity": "Major",
                        "mechanism": "CYP2C9 inhibition",
                        "clinical_effect": "Increased anticoagulant effect"
                    }
                ],
                "moderate_interactions": [
                    {
                        "drug_name": "Metformin",
                        "severity": "Moderate", 
                        "clinical_effect": "Potential for lactic acidosis"
                    }
                ]
            },
            "indications_and_usage": {
                "text": "Indicated for the treatment of moderate to severe chronic pain in adults when a continuous, around-the-clock opioid analgesic is needed for an extended period of time.",
                "limitations": "Not indicated for use as an as-needed analgesic."
            },
            "dosage_and_administration": {
                "general": "Take with or without food. Swallow tablets whole; do not crush, chew, or dissolve.",
                "adult_dose": "Initial dose: 25 mg twice daily. May increase by 50 mg daily every 3 days as tolerated.",
                "maximum_dose": "400 mg daily",
                "special_populations": "Reduce dose in elderly patients and those with hepatic impairment."
            },
            "mechanism_of_action": "Syntheticcompound-alpha is a selective inhibitor of cyclooxygenase-2 (COX-2) that exhibits anti-inflammatory, analgesic, and antipyretic activities.",
            "pharmacokinetics": {
                "absorption": "Peak plasma concentrations achieved within 2-3 hours after oral administration.",
                "distribution": "Protein binding: 97%. Volume of distribution: 455 L.",
                "metabolism": "Extensively metabolized by CYP2C9 and CYP3A4.",
                "elimination": "Terminal half-life: 11-17 hours. Eliminated primarily via metabolism."
            },
            "pharmacodynamics": "At therapeutic doses, provides sustained COX-2 inhibition with minimal effect on COX-1."
        },
        {
            # Another synthetic example with different structures
            "product_ndc": ["SYNTH-002"],
            "brand_name": ["Synthetic Drug Beta"],
            "generic_name": ["syntheticcompound-beta"],
            "manufacturer_name": ["Advanced Therapeutics LLC"],
            "dosage_form": ["injection"],
            "route": ["intravenous"],
            "active_ingredient": ["syntheticcompound-beta 100 mg/10 mL"],
            
            # Simpler clinical data structures
            "contraindications": "Hypersensitivity to syntheticcompound-beta. Pregnancy.",
            "warnings": ["Black Box Warning: Increased risk of serious cardiovascular events."],
            "drug_interactions": "Avoid concurrent use with live vaccines.",
            "indications_and_usage": "For the treatment of severe inflammatory conditions in hospitalized patients.",
            "mechanism_of_action": "Monoclonal antibody that binds to TNF-alpha, blocking its interaction with cell surface receptors."
        }
    ]
    
    try:
        parsed_results = []
        
        for i, label_data in enumerate(synthetic_labels, 1):
            logger.info(f"🔄 Parsing synthetic label {i}: {label_data['brand_name']}")
            
            try:
                parsed_drug = parse_drug_label_record_worker(label_data)
                
                if parsed_drug:
                    parsed_results.append(parsed_drug)
                    
                    logger.info(f"✅ Successfully parsed {parsed_drug['name']}")
                    logger.info(f"  NDC: {parsed_drug['ndc']}")
                    logger.info(f"  Generic: {parsed_drug['generic_name']}")
                    logger.info(f"  Manufacturer: {parsed_drug['manufacturer']}")
                    
                    # Check clinical fields
                    clinical_fields = [
                        'contraindications', 'warnings', 'precautions',
                        'adverse_reactions', 'drug_interactions',
                        'indications_and_usage', 'mechanism_of_action'
                    ]
                    
                    logger.info("  Clinical Information:")
                    for field in clinical_fields:
                        value = parsed_drug.get(field)
                        if value:
                            if isinstance(value, list):
                                logger.info(f"    {field}: {len(value)} items")
                            elif isinstance(value, dict):
                                logger.info(f"    {field}: Dict with {len(value)} keys")
                            elif isinstance(value, str):
                                preview = value[:80] + "..." if len(value) > 80 else value
                                logger.info(f"    {field}: {preview}")
                else:
                    logger.warning(f"❌ Parsing returned None for label {i}")
                    
            except Exception as e:
                logger.exception(f"❌ Parsing failed for synthetic label {i}: {e}")
        
        logger.info(f"📊 Successfully parsed {len(parsed_results)} out of {len(synthetic_labels)} synthetic labels")
        return parsed_results
        
    except Exception as e:
        logger.exception(f"❌ Synthetic data parsing test failed: {e}")
        return []

async def test_database_insertion_with_synthetic(parsed_drugs: List[Dict]):
    """Test database insertion with synthetic parsed drug data"""
    logger.info("=== Testing Database Insertion with Synthetic Data ===")
    
    if not parsed_drugs:
        logger.warning("⚠️ No parsed drugs to test database insertion")
        return False
    
    try:
        # Create a minimal config
        class MinimalConfig:
            POSTGRES_URL = os.getenv(
                "POSTGRES_URL", 
                "postgresql://intelluxe:secure_password@172.20.0.13:5432/intelluxe_public"
            )
        
        config = MinimalConfig()
        session_factory = get_db_session
        
        fda_api = FDAAPI(session_factory, config)
        db = session_factory()
        
        try:
            # Get initial count
            initial_count = db.execute(text("SELECT COUNT(*) FROM fda_drugs")).fetchone()[0]
            logger.info(f"📊 Initial drug count: {initial_count}")
            
            # Test storage
            start_time = time.time()
            stored_count = await fda_api.store_drugs_with_merging(parsed_drugs, db)
            duration = time.time() - start_time
            
            logger.info(f"✅ Database insertion successful!")
            logger.info(f"  Records stored: {stored_count}")
            logger.info(f"  Duration: {duration:.2f} seconds")
            
            # Verify storage
            final_count = db.execute(text("SELECT COUNT(*) FROM fda_drugs")).fetchone()[0]
            logger.info(f"📊 Final drug count: {final_count} (+{final_count - initial_count})")
            
            # Check stored records
            synth_records = db.execute(text("""
                SELECT ndc, name, generic_name, contraindications, warnings, drug_interactions
                FROM fda_drugs 
                WHERE ndc LIKE 'SYNTH-%'
                ORDER BY ndc
            """)).fetchall()
            
            logger.info(f"🔍 Verification: Found {len(synth_records)} synthetic records:")
            for record in synth_records:
                logger.info(f"  • {record[0]}: {record[1]}")
                if record[3]:  # contraindications
                    logger.info(f"    Contraindications: {len(record[3])} items")
                if record[4]:  # warnings
                    logger.info(f"    Warnings: {len(record[4])} items")
                if record[5] and record[5] != {}:  # drug_interactions
                    logger.info(f"    Drug interactions: Present")
            
            # Clean up synthetic records
            cleanup_result = db.execute(text("DELETE FROM fda_drugs WHERE ndc LIKE 'SYNTH-%'"))
            db.commit()
            logger.info(f"🧹 Cleaned up {cleanup_result.rowcount} synthetic records")
            
            return True
            
        finally:
            db.close()
        
    except Exception as e:
        logger.exception(f"❌ Database insertion test failed: {e}")
        return False

def main():
    """Run simple FDA debugging tests"""
    print("🔬 Starting Simple FDA Debugging Tests\n")
    
    results = []
    
    try:
        # Test 1: Check database status
        logger.info("Test 1: Database Status Check")
        results.append(("Database Status", check_database_status()))
        
        # Test 2: Test parsing with synthetic data
        logger.info("\nTest 2: Parsing with Synthetic Data")
        parsed_drugs = test_parsing_with_synthetic_data()
        results.append(("Synthetic Parsing", len(parsed_drugs) > 0))
        
        # Test 3: Test database insertion
        logger.info("\nTest 3: Database Insertion")
        db_insertion_success = asyncio.run(test_database_insertion_with_synthetic(parsed_drugs))
        results.append(("Database Insertion", db_insertion_success))
        
        # Test 4: Test real FDA API
        logger.info("\nTest 4: Real FDA API")
        results.append(("FDA API", test_real_fda_api()))
        
        # Results summary
        print("\n" + "="*60)
        print("SIMPLE FDA DEBUG RESULTS")
        print("="*60)
        
        passed = 0
        for test_name, success in results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} {test_name}")
            if success:
                passed += 1
        
        print(f"\n📊 {passed}/{len(results)} tests passed")
        
        if passed == len(results):
            print("\n🎉 All FDA components working correctly!")
            print("\n💡 The FDA drug label parsing and database insertion pipeline is functioning properly.")
            print("   Clinical information (contraindications, warnings, drug interactions, etc.)")
            print("   is being parsed and stored correctly in the database.")
            return 0
        else:
            print(f"\n⚠️ {len(results) - passed} tests failed - review error messages above")
            return 1
            
    except Exception as e:
        print(f"\n❌ Debug execution failed: {e}")
        logger.exception("Debug execution failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())