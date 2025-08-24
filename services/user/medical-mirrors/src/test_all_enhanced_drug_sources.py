#!/usr/bin/env python3
"""
Comprehensive test script for all enhanced drug source integrations
Tests DailyMed, ClinicalTrials.gov, OpenFDA FAERS, RxClass, DrugCentral, DDInter, and LactMed
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent))

from enhanced_drug_sources.dailymed_downloader import SmartDailyMedDownloader
from enhanced_drug_sources.clinical_trials_downloader import SmartClinicalTrialsDownloader
from enhanced_drug_sources.openfda_faers_downloader import SmartOpenFDAFAERSDownloader
from enhanced_drug_sources.rxclass_downloader import SmartRxClassDownloader
from enhanced_drug_sources.drugcentral_downloader import SmartDrugCentralDownloader
from enhanced_drug_sources.ddinter_downloader import SmartDDInterDownloader
from enhanced_drug_sources.lactmed_downloader import SmartLactMedDownloader
from config import Config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_all_enhanced_drug_sources():
    """Test all enhanced drug source integrations comprehensively"""
    config = Config()
    
    logger.info("=" * 80)
    logger.info("COMPREHENSIVE ENHANCED DRUG SOURCES TEST")
    logger.info("=" * 80)
    
    # Test drugs for comprehensive coverage
    test_drugs = ['aspirin', 'ibuprofen', 'acetaminophen', 'metformin', 'lisinopril']
    
    all_results = {}
    start_time = time.time()
    
    # Test 1: DailyMed API (FDA Drug Labeling)
    logger.info("\n🧪 Testing DailyMed API (FDA Drug Labeling)...")
    try:
        async with SmartDailyMedDownloader(config=config) as downloader:
            result = await downloader.download_enhanced_drug_labeling(
                drug_names=test_drugs[:3],  # Test 3 drugs
                max_concurrent=2
            )
            all_results['dailymed'] = result
            logger.info(f"✅ DailyMed: {result['total_files']} files, {result['success_rate']:.1f}% success")
    except Exception as e:
        logger.error(f"❌ DailyMed test failed: {e}")
        all_results['dailymed'] = {'error': str(e)}
    
    # Test 2: ClinicalTrials.gov API
    logger.info("\n🧪 Testing ClinicalTrials.gov API...")
    try:
        async with SmartClinicalTrialsDownloader(config=config) as downloader:
            result = await downloader.download_special_population_studies(
                drug_names=test_drugs[:3],
                max_concurrent=2
            )
            all_results['clinical_trials'] = result
            logger.info(f"✅ ClinicalTrials: {result['total_files']} files, {result['success_rate']:.1f}% success")
    except Exception as e:
        logger.error(f"❌ ClinicalTrials test failed: {e}")
        all_results['clinical_trials'] = {'error': str(e)}
    
    # Test 3: OpenFDA FAERS API (Adverse Events)
    logger.info("\n🧪 Testing OpenFDA FAERS API (Adverse Events)...")
    try:
        async with SmartOpenFDAFAERSDownloader(config=config) as downloader:
            result = await downloader.download_special_population_adverse_events(
                drug_names=test_drugs[:3],
                max_concurrent=2
            )
            all_results['openfda_faers'] = result
            logger.info(f"✅ OpenFDA FAERS: {result['total_files']} files, {result['success_rate']:.1f}% success")
    except Exception as e:
        logger.error(f"❌ OpenFDA FAERS test failed: {e}")
        all_results['openfda_faers'] = {'error': str(e)}
    
    # Test 4: RxClass API (Drug Classifications)
    logger.info("\n🧪 Testing RxClass API (Drug Classifications)...")
    try:
        async with SmartRxClassDownloader(config=config) as downloader:
            result = await downloader.download_comprehensive_classifications(
                drug_names=test_drugs[:3],
                max_concurrent=2
            )
            all_results['rxclass'] = result
            logger.info(f"✅ RxClass: {result['total_files']} files, {result['success_rate']:.1f}% success")
    except Exception as e:
        logger.error(f"❌ RxClass test failed: {e}")
        all_results['rxclass'] = {'error': str(e)}
    
    # Test 5: DrugCentral PostgreSQL Database
    logger.info("\n🧪 Testing DrugCentral PostgreSQL Database...")
    try:
        async with SmartDrugCentralDownloader(config=config) as downloader:
            # Test all three query types
            moa_file = await downloader.download_mechanism_of_action_data()
            target_file = await downloader.download_drug_target_data()
            pharm_file = await downloader.download_pharmacology_data()
            
            result = await downloader.get_download_summary()
            all_results['drugcentral'] = result
            logger.info(f"✅ DrugCentral: {result['total_files']} files, {result['success_rate']:.1f}% success")
    except Exception as e:
        logger.error(f"❌ DrugCentral test failed: {e}")
        all_results['drugcentral'] = {'error': str(e)}
    
    # Test 6: DDInter 2.0 (Drug-Drug Interactions)
    logger.info("\n🧪 Testing DDInter 2.0 (Drug-Drug Interactions)...")
    try:
        async with SmartDDInterDownloader(config=config) as downloader:
            result = await downloader.download_drug_interactions_batch(
                drug_names=test_drugs[:3],
                max_concurrent=1  # Very conservative for web scraping
            )
            all_results['ddinter'] = result
            logger.info(f"✅ DDInter: {result['total_files']} files, {result['success_rate']:.1f}% success")
    except Exception as e:
        logger.error(f"❌ DDInter test failed: {e}")
        all_results['ddinter'] = {'error': str(e)}
    
    # Test 7: LactMed (Breastfeeding Safety)
    logger.info("\n🧪 Testing LactMed via NCBI E-utilities (Breastfeeding Safety)...")
    try:
        async with SmartLactMedDownloader(config=config) as downloader:
            result = await downloader.download_lactation_safety_batch(
                drug_names=test_drugs[:3],
                max_concurrent=1  # Very conservative for NCBI
            )
            all_results['lactmed'] = result
            logger.info(f"✅ LactMed: {result['total_files']} files, {result['success_rate']:.1f}% success")
    except Exception as e:
        logger.error(f"❌ LactMed test failed: {e}")
        all_results['lactmed'] = {'error': str(e)}
    
    # Summary Report
    total_time = time.time() - start_time
    logger.info("\n" + "=" * 80)
    logger.info("COMPREHENSIVE TEST RESULTS SUMMARY")
    logger.info("=" * 80)
    
    total_files = 0
    total_sources_successful = 0
    total_sources_tested = len(all_results)
    
    for source, result in all_results.items():
        if 'error' in result:
            logger.error(f"❌ {source.upper()}: FAILED - {result['error']}")
        else:
            files = result.get('total_files', 0)
            success_rate = result.get('success_rate', 0)
            total_files += files
            if files > 0:
                total_sources_successful += 1
            logger.info(f"✅ {source.upper()}: {files} files downloaded, {success_rate:.1f}% success rate")
    
    logger.info(f"\n📊 OVERALL STATISTICS:")
    logger.info(f"   • Total sources tested: {total_sources_tested}")
    logger.info(f"   • Successful sources: {total_sources_successful}")
    logger.info(f"   • Source success rate: {(total_sources_successful / total_sources_tested) * 100:.1f}%")
    logger.info(f"   • Total files downloaded: {total_files}")
    logger.info(f"   • Total test time: {total_time:.1f} seconds")
    
    # Directory statistics
    logger.info(f"\n📁 DATA DIRECTORY STATISTICS:")
    base_dir = Path(config.get_enhanced_drug_data_dir())
    for source_dir in base_dir.iterdir():
        if source_dir.is_dir():
            file_count = len(list(source_dir.glob("*.json"))) + len(list(source_dir.glob("*.xml")))
            total_size = sum(f.stat().st_size for f in source_dir.glob("*") if f.is_file())
            size_mb = total_size / (1024 * 1024)
            logger.info(f"   • {source_dir.name}: {file_count} files, {size_mb:.2f} MB")
    
    if total_sources_successful >= 5:  # At least 5 out of 7 sources working
        logger.info("\n🎉 COMPREHENSIVE TEST PASSED!")
        logger.info("Enhanced drug sources integration is working successfully!")
        return True
    else:
        logger.error(f"\n❌ COMPREHENSIVE TEST FAILED!")
        logger.error(f"Only {total_sources_successful}/{total_sources_tested} sources working successfully")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_all_enhanced_drug_sources())
    sys.exit(0 if success else 1)