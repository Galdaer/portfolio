#!/usr/bin/env python3
"""
Parse Downloaded Medical Archives
Parses existing downloaded medical data without re-downloading
"""

import logging
import requests
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional


class MedicalArchiveParser:
    """Parses already downloaded medical archives via medical-mirrors API"""

    def __init__(self, api_base_url: str = "http://localhost:8081"):
        self.api_base_url = api_base_url
        self.logger = self._setup_logging()

    def _setup_logging(self) -> logging.Logger:
        """Setup parsing logging"""
        logger = logging.getLogger("medical_archive_parser")
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def check_service_health(self) -> bool:
        """Check if medical-mirrors service is running"""
        try:
            response = requests.get(f"{self.api_base_url}/health", timeout=30)
            if response.status_code == 200:
                self.logger.info("✅ Medical-mirrors service is healthy")
                return True
            else:
                self.logger.error(f"❌ Medical-mirrors health check failed: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Cannot connect to medical-mirrors service: {e}")
            self.logger.info("💡 Service may be busy processing - try again in a few minutes")
            return False

    def trigger_parse_pubmed(self, quick_test: bool = False, max_files: Optional[int] = None) -> Dict[str, Any]:
        """Trigger PubMed parsing of existing files"""
        try:
            params = {}
            if quick_test:
                params["quick_test"] = "true"
            if max_files:
                params["max_files"] = str(max_files)

            self.logger.info(f"🚀 Triggering PubMed parsing (quick_test={quick_test}, max_files={max_files})")
            try:
                response = requests.post(
                    f"{self.api_base_url}/update/pubmed",
                    params=params,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    self.logger.info(f"✅ PubMed parsing triggered: {result}")
                    return result
                else:
                    self.logger.error(f"❌ PubMed parsing failed: {response.status_code} - {response.text}")
                    return {"status": "error", "message": f"HTTP {response.status_code}"}
            except requests.exceptions.Timeout:
                self.logger.info("⏳ PubMed parsing request sent (timeout normal - processing in background)")
                return {"status": "queued", "message": "Background processing started"}
            except requests.exceptions.RequestException as e:
                self.logger.error(f"❌ PubMed parsing request failed: {e}")
                return {"status": "error", "message": str(e)}

        except Exception as e:
            self.logger.error(f"❌ Unexpected error in PubMed parsing: {e}")
            return {"status": "error", "message": str(e)}

    def trigger_parse_fda(self, quick_test: bool = False, limit: Optional[int] = None) -> Dict[str, Any]:
        """Trigger FDA parsing of existing files"""
        try:
            params = {}
            if quick_test:
                params["quick_test"] = "true"
            if limit:
                params["limit"] = str(limit)

            self.logger.info(f"💊 Triggering FDA parsing (quick_test={quick_test}, limit={limit})")
            try:
                response = requests.post(
                    f"{self.api_base_url}/update/fda",
                    params=params,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    self.logger.info(f"✅ FDA parsing triggered: {result}")
                    return result
                else:
                    self.logger.error(f"❌ FDA parsing failed: {response.status_code} - {response.text}")
                    return {"status": "error", "message": f"HTTP {response.status_code}"}
            except requests.exceptions.Timeout:
                self.logger.info("⏳ FDA parsing request sent (timeout normal - processing in background)")
                return {"status": "queued", "message": "Background processing started"}
            except requests.exceptions.RequestException as e:
                self.logger.error(f"❌ FDA parsing request failed: {e}")
                return {"status": "error", "message": str(e)}

        except Exception as e:
            self.logger.error(f"❌ Unexpected error in FDA parsing: {e}")
            return {"status": "error", "message": str(e)}

    def trigger_parse_trials(self, quick_test: bool = False, limit: Optional[int] = None) -> Dict[str, Any]:
        """Trigger ClinicalTrials parsing of existing files"""
        try:
            params = {}
            if quick_test:
                params["quick_test"] = "true"
            if limit:
                params["limit"] = str(limit)

            self.logger.info(f"🧪 Triggering ClinicalTrials parsing (quick_test={quick_test}, limit={limit})")
            try:
                response = requests.post(
                    f"{self.api_base_url}/update/trials",
                    params=params,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    self.logger.info(f"✅ ClinicalTrials parsing triggered: {result}")
                    return result
                else:
                    self.logger.error(f"❌ ClinicalTrials parsing failed: {response.status_code} - {response.text}")
                    return {"status": "error", "message": f"HTTP {response.status_code}"}
            except requests.exceptions.Timeout:
                self.logger.info("⏳ ClinicalTrials parsing request sent (timeout normal - processing in background)")
                return {"status": "queued", "message": "Background processing started"}
            except requests.exceptions.RequestException as e:
                self.logger.error(f"❌ ClinicalTrials parsing request failed: {e}")
                return {"status": "error", "message": str(e)}

        except Exception as e:
            self.logger.error(f"❌ Unexpected error in ClinicalTrials parsing: {e}")
            return {"status": "error", "message": str(e)}

    def get_status(self) -> Dict[str, Any]:
        """Get current parsing status"""
        try:
            response = requests.get(f"{self.api_base_url}/status", timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "error", "message": f"HTTP {response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": str(e)}

    def parse_all_quick_test(self) -> None:
        """Run quick test parsing for all data sources"""
        self.logger.info("🔍 Running quick test parsing for all medical data sources")
        
        if not self.check_service_health():
            return

        # Quick test limits to avoid overwhelming the system
        self.logger.info("📚 Starting PubMed quick test (3 files max)...")
        self.trigger_parse_pubmed(quick_test=True, max_files=3)
        
        self.logger.info("⏳ Waiting 5 seconds before next request...")
        time.sleep(5)
        
        self.logger.info("💊 Starting FDA quick test (1000 records max)...")
        self.trigger_parse_fda(quick_test=True, limit=1000)
        
        self.logger.info("⏳ Waiting 5 seconds before next request...")
        time.sleep(5)
        
        self.logger.info("🧪 Starting ClinicalTrials quick test (100 records max)...")
        self.trigger_parse_trials(quick_test=True, limit=100)
        
        self.logger.info("✅ All quick test parsing requests sent - they run in background")
        self.logger.info("💡 Use 'docker logs medical-mirrors -f' to monitor progress")

    def parse_all_full(self) -> None:
        """Run full parsing for all data sources"""
        self.logger.info("🚀 Running full parsing for all medical data sources")
        
        if not self.check_service_health():
            return

        self.logger.warning("⚠️  Full parsing may take several hours for complete datasets")
        
        # Full parsing - no limits
        self.trigger_parse_pubmed(quick_test=False)
        self.logger.info("📚 PubMed parsing started in background")
        
        # Wait a bit before starting others to avoid overwhelming
        time.sleep(5)
        
        self.trigger_parse_fda(quick_test=False)
        self.logger.info("💊 FDA parsing started in background")
        
        time.sleep(5)
        
        self.trigger_parse_trials(quick_test=False)
        self.logger.info("🧪 ClinicalTrials parsing started in background")


def main():
    """Main parsing script entry point"""
    parser = MedicalArchiveParser()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python parse_downloaded_archives.py quick    # Quick test parsing")
        print("  python parse_downloaded_archives.py full     # Full parsing")
        print("  python parse_downloaded_archives.py status   # Check status")
        print("  python parse_downloaded_archives.py pubmed   # Parse PubMed only")
        print("  python parse_downloaded_archives.py fda      # Parse FDA only")
        print("  python parse_downloaded_archives.py trials   # Parse ClinicalTrials only")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "quick":
        parser.parse_all_quick_test()
    elif command == "full":
        parser.parse_all_full()
    elif command == "status":
        status = parser.get_status()
        print(f"Service Status: {status}")
    elif command == "pubmed":
        quick = "--quick" in sys.argv
        parser.trigger_parse_pubmed(quick_test=quick)
    elif command == "fda":
        quick = "--quick" in sys.argv
        parser.trigger_parse_fda(quick_test=quick)
    elif command == "trials":
        quick = "--quick" in sys.argv
        parser.trigger_parse_trials(quick_test=quick)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
