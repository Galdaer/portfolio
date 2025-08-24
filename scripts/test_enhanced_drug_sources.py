#!/usr/bin/env python3
"""
Test Enhanced Drug Sources
Tests all new drug data sources to ensure they work correctly
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add medical-mirrors src to path
sys.path.append("/home/intelluxe/services/user/medical-mirrors/src")

from enhanced_drug_sources.clinical_trials_downloader import SmartClinicalTrialsDownloader
from enhanced_drug_sources.dailymed_downloader import SmartDailyMedDownloader
from enhanced_drug_sources.openfda_faers_downloader import SmartOpenFDAFAERSDownloader
from enhanced_drug_sources.rxclass_downloader import SmartRxClassDownloader

from config import Config


async def test_dailymed():
    """Test DailyMed API downloader"""
    print("\n=== Testing DailyMed API Downloader ===")

    config = Config()
    async with SmartDailyMedDownloader(config=config) as downloader:
        # Test with a small set of common drugs
        test_drugs = ["acetaminophen", "ibuprofen", "aspirin"]

        print(f"Testing DailyMed with drugs: {test_drugs}")

        result = await downloader.download_enhanced_drug_labeling(
            drug_names=test_drugs,
            max_concurrent=2,
        )

        print("DailyMed Results:")
        print(f"  Total files: {result.get('total_files', 0)}")
        print(f"  Success rate: {result.get('success_rate', 0):.1f}%")
        print(f"  Data source: {result.get('data_source')}")

        # Get status
        status = await downloader.get_download_status()
        print(f"  Status: {status.get('state')}")
        print(f"  Files downloaded: {status.get('files_downloaded', 0)}")

        return result.get("total_files", 0) > 0


async def test_clinical_trials():
    """Test ClinicalTrials.gov API downloader"""
    print("\n=== Testing ClinicalTrials.gov API Downloader ===")

    config = Config()
    async with SmartClinicalTrialsDownloader(config=config) as downloader:
        # Test with a small set of drugs
        test_drugs = ["metformin", "insulin"]

        print(f"Testing ClinicalTrials with drugs: {test_drugs}")

        result = await downloader.download_special_population_studies(
            drug_names=test_drugs,
            max_concurrent=2,
        )

        print("ClinicalTrials Results:")
        print(f"  Total files: {result.get('total_files', 0)}")
        print(f"  Success rate: {result.get('success_rate', 0):.1f}%")
        print(f"  Unique studies: {result.get('unique_studies_downloaded', 0)}")
        print(f"  Data source: {result.get('data_source')}")

        # Get status
        status = await downloader.get_download_status()
        print(f"  Status: {status.get('state')}")
        print(f"  Files downloaded: {status.get('files_downloaded', 0)}")

        return result.get("total_files", 0) > 0


async def test_openfda_faers():
    """Test OpenFDA FAERS API downloader"""
    print("\n=== Testing OpenFDA FAERS API Downloader ===")

    config = Config()
    async with SmartOpenFDAFAERSDownloader(config=config) as downloader:
        # Test with a drug known to have FAERS data
        test_drugs = ["warfarin"]

        print(f"Testing OpenFDA FAERS with drugs: {test_drugs}")

        result = await downloader.download_special_population_adverse_events(
            drug_names=test_drugs,
            max_concurrent=1,  # Very conservative for testing
        )

        print("OpenFDA FAERS Results:")
        print(f"  Total files: {result.get('total_files', 0)}")
        print(f"  Success rate: {result.get('success_rate', 0):.1f}%")
        print(f"  Unique reports: {result.get('unique_reports_downloaded', 0)}")
        print(f"  Data source: {result.get('data_source')}")

        # Get status
        status = await downloader.get_download_status()
        print(f"  Status: {status.get('state')}")
        print(f"  Files downloaded: {status.get('files_downloaded', 0)}")

        return result.get("total_files", 0) > 0


async def test_rxclass():
    """Test RxClass API downloader"""
    print("\n=== Testing RxClass API Downloader ===")

    config = Config()
    async with SmartRxClassDownloader(config=config) as downloader:
        # Test with a small set of well-classified drugs
        test_drugs = ["acetaminophen", "ibuprofen"]

        print(f"Testing RxClass with drugs: {test_drugs}")

        result = await downloader.download_comprehensive_classifications(
            drug_names=test_drugs,
            max_concurrent=3,
            include_class_members=False,  # Skip class members for faster testing
        )

        print("RxClass Results:")
        print(f"  Total files: {result.get('total_files', 0)}")
        print(f"  Success rate: {result.get('success_rate', 0):.1f}%")
        print(f"  Unique classes: {result.get('unique_classes_discovered', 0)}")
        print(f"  Data source: {result.get('data_source')}")

        # Get status
        status = await downloader.get_download_status()
        print(f"  Status: {status.get('state')}")
        print(f"  Files downloaded: {status.get('files_downloaded', 0)}")

        return result.get("total_files", 0) > 0


async def test_environment_variables():
    """Test that environment variables are loaded correctly"""
    print("\n=== Testing Environment Variables ===")

    config = Config()

    # Check if new environment variables are loaded
    env_vars = [
        ("DAILYMED_API_BASE_URL", config.DAILYMED_API_BASE_URL),
        ("CLINICAL_TRIALS_API_BASE_URL", config.CLINICAL_TRIALS_API_BASE_URL),
        ("OPENFDA_FAERS_API_BASE_URL", config.OPENFDA_FAERS_API_BASE_URL),
        ("RXCLASS_API_BASE_URL", config.RXCLASS_API_BASE_URL),
        ("DAILYMED_RATE_LIMIT", config.DAILYMED_RATE_LIMIT),
        ("CLINICAL_TRIALS_RATE_LIMIT", config.CLINICAL_TRIALS_RATE_LIMIT),
        ("OPENFDA_RATE_LIMIT", config.OPENFDA_RATE_LIMIT),
        ("RXCLASS_RATE_LIMIT", config.RXCLASS_RATE_LIMIT),
    ]

    print("Environment Variables:")
    for var_name, var_value in env_vars:
        print(f"  {var_name}: {var_value}")

    # Check data directories
    data_dirs = [
        ("DailyMed", config.get_dailymed_data_dir()),
        ("ClinicalTrials", config.get_clinical_trials_data_dir()),
        ("OpenFDA FAERS", config.get_openfda_faers_data_dir()),
        ("RxClass", config.get_rxclass_data_dir()),
    ]

    print("Data Directories:")
    for dir_name, dir_path in data_dirs:
        dir_exists = Path(dir_path).exists()
        print(f"  {dir_name}: {dir_path} ({'exists' if dir_exists else 'will be created'})")

    return True


async def main():
    """Main test function"""
    print("Enhanced Drug Sources Test Suite")
    print("=" * 50)
    print(f"Started at: {datetime.now().isoformat()}")

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Test results
    test_results = {}

    try:
        # Test environment variables first
        test_results["environment"] = await test_environment_variables()

        # Test each downloader
        test_results["dailymed"] = await test_dailymed()
        test_results["clinical_trials"] = await test_clinical_trials()
        test_results["openfda_faers"] = await test_openfda_faers()
        test_results["rxclass"] = await test_rxclass()

    except KeyboardInterrupt:
        print("\n⚠️  Testing interrupted by user")
        return
    except Exception as e:
        print(f"\n❌ Testing failed with error: {e}")
        import traceback
        traceback.print_exc()
        return

    # Print summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)

    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results.values() if result)

    print(f"Total tests: {total_tests}")
    print(f"Passed tests: {passed_tests}")
    print(f"Failed tests: {total_tests - passed_tests}")
    print(f"Success rate: {(passed_tests / total_tests) * 100:.1f}%")

    print("\nDetailed Results:")
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")

    if passed_tests == total_tests:
        print("\n🎉 All tests passed! Enhanced drug sources are working correctly.")
    else:
        print(f"\n⚠️  {total_tests - passed_tests} test(s) failed. Check the logs above for details.")

    print(f"\nCompleted at: {datetime.now().isoformat()}")


if __name__ == "__main__":
    asyncio.run(main())
