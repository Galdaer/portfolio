"""
Configuration for medical mirrors service
"""

import os


class Config:
    """Configuration settings for medical mirrors"""

    # Database settings
    POSTGRES_URL: str = os.getenv(
        "POSTGRES_URL",
        "postgresql://intelluxe:secure_password@172.20.0.13:5432/intelluxe",
    )

    # Data source URLs
    PUBMED_FTP_BASE: str = "ftp://ftp.ncbi.nlm.nih.gov/pubmed/"
    CLINICALTRIALS_API: str = "https://clinicaltrials.gov/api/v2/studies"
    FDA_API_BASE: str = "https://api.fda.gov"

    # Medical coding APIs
    NLM_ICD10_API: str = "https://clinicaltables.nlm.nih.gov/api/icd10cm/v3"
    NLM_HCPCS_API: str = "https://clinicaltables.nlm.nih.gov/api/hcpcs/v3"

    # Health information APIs
    MYHEALTHFINDER_API: str = "https://healthfinder.gov/developer/api"
    EXERCISEDB_API: str = "https://exercisedb.p.rapidapi.com"
    USDA_FOOD_API: str = "https://api.nal.usda.gov/fdc/v1"

    # Enhanced Drug Database APIs
    DAILYMED_API_BASE_URL: str = os.getenv("DAILYMED_API_BASE_URL", "https://dailymed.nlm.nih.gov/dailymed/services")
    CLINICAL_TRIALS_API_BASE_URL: str = os.getenv("CLINICAL_TRIALS_API_BASE_URL", "https://clinicaltrials.gov/api")
    OPENFDA_FAERS_API_BASE_URL: str = os.getenv("OPENFDA_FAERS_API_BASE_URL", "https://api.fda.gov/drug/event.json")
    RXCLASS_API_BASE_URL: str = os.getenv("RXCLASS_API_BASE_URL", "https://rxnav.nlm.nih.gov/REST/rxclass")

    # DrugCentral PostgreSQL Database Configuration
    DRUGCENTRAL_DB_HOST: str = os.getenv("DRUGCENTRAL_DB_HOST", "unmtid-dbs.net")
    DRUGCENTRAL_DB_PORT: int = int(os.getenv("DRUGCENTRAL_DB_PORT", "5433"))
    DRUGCENTRAL_DB_NAME: str = os.getenv("DRUGCENTRAL_DB_NAME", "drugcentral")
    DRUGCENTRAL_DB_USER: str = os.getenv("DRUGCENTRAL_DB_USER", "drugman")
    DRUGCENTRAL_DB_PASSWORD: str = os.getenv("DRUGCENTRAL_DB_PASSWORD", "dosage")

    # Additional API configurations
    DRUGCENTRAL_DATA_URL: str = os.getenv("DRUGCENTRAL_DATA_URL", "https://drugcentral.org/download")
    DDINTER_API_BASE_URL: str = os.getenv("DDINTER_API_BASE_URL", "https://ddinter2.scbdd.com/api")
    LACTMED_API_BASE_URL: str = os.getenv("LACTMED_API_BASE_URL", "https://eutils.ncbi.nlm.nih.gov/entrez/eutils")

    # Update schedules (in seconds)
    PUBMED_UPDATE_INTERVAL: int = 86400  # Daily
    TRIALS_UPDATE_INTERVAL: int = 604800  # Weekly
    FDA_UPDATE_INTERVAL: int = 2592000  # Monthly
    ICD10_UPDATE_INTERVAL: int = 2592000  # Monthly (ICD codes change rarely)
    BILLING_CODES_UPDATE_INTERVAL: int = 7776000  # Quarterly
    HEALTH_INFO_UPDATE_INTERVAL: int = 604800  # Weekly

    # Rate limiting - Per-source delays based on actual API limits (2024-2025)
    MAX_CONCURRENT_DOWNLOADS: int = 5
    REQUEST_DELAY: float = 0.1  # Default fallback - Seconds between requests

    # Per-source rate limits (requests per second) - Based on official API documentation
    #
    # PubMed E-utilities API Key Optimization:
    # - Without API key: 3 req/sec (PUBMED_REQUEST_DELAY = 0.33)
    # - With API key: 10 req/sec (PUBMED_REQUEST_DELAY = 0.1)
    # - To get API key: Create NCBI account at https://account.ncbi.nlm.nih.gov/
    # - Add to environment: PUBMED_API_KEY=your_key_here
    # - Enhanced keys (>10 rps) available by contacting info@ncbi.nlm.nih.gov
    PUBMED_REQUEST_DELAY: float = 0.33      # 3 req/sec (no API key) - can be 0.1 with API key
    CLINICALTRIALS_REQUEST_DELAY: float = 0.01   # Testing shows they handle more than documented - increased from 0.02s
    OPENFDA_REQUEST_DELAY: float = 0.25     # 4 req/sec (240 req/min)
    USDA_FOOD_REQUEST_DELAY: float = 2.0    # 0.5 req/sec (more reasonable for 1000 req/hour limit)
    RXCLASS_REQUEST_DELAY: float = 0.05     # 20 req/sec per IP
    DAILYMED_REQUEST_DELAY: float = 0.05    # 20 req/sec (NLM general limit)
    ICD10_REQUEST_DELAY: float = 0.1        # Government API - conservative
    BILLING_REQUEST_DELAY: float = 0.1      # Government API - conservative

    # Enhanced Drug API Rate Limiting (legacy - kept for compatibility)
    DAILYMED_RATE_LIMIT: int = int(os.getenv("DAILYMED_RATE_LIMIT", "20"))
    CLINICAL_TRIALS_RATE_LIMIT: int = int(os.getenv("CLINICAL_TRIALS_RATE_LIMIT", "1"))  # Updated to actual limit
    OPENFDA_RATE_LIMIT: int = int(os.getenv("OPENFDA_RATE_LIMIT", "4"))   # Updated to actual limit
    RXCLASS_RATE_LIMIT: int = int(os.getenv("RXCLASS_RATE_LIMIT", "20"))
    DDINTER_RATE_LIMIT: int = int(os.getenv("DDINTER_RATE_LIMIT", "5"))
    LACTMED_RATE_LIMIT: int = int(os.getenv("LACTMED_RATE_LIMIT", "3"))

    # Global Drug API Configuration
    DRUG_API_GLOBAL_RATE_LIMIT: int = int(os.getenv("DRUG_API_GLOBAL_RATE_LIMIT", "50"))
    DRUG_API_RETRY_ATTEMPTS: int = int(os.getenv("DRUG_API_RETRY_ATTEMPTS", "3"))
    DRUG_API_RETRY_BACKOFF: float = float(os.getenv("DRUG_API_RETRY_BACKOFF", "2"))
    DRUG_API_TIMEOUT: int = int(os.getenv("DRUG_API_TIMEOUT", "30"))
    DRUGCENTRAL_UPDATE_FREQUENCY: str = os.getenv("DRUGCENTRAL_UPDATE_FREQUENCY", "monthly")

    # Data paths
    DATA_DIR: str = os.getenv("DATA_DIR", "/home/intelluxe/database/medical_complete")
    LOGS_DIR: str = os.getenv("LOGS_DIR", "/home/intelluxe/logs")

    # Search limits
    DEFAULT_MAX_RESULTS: int = 10
    MAX_SEARCH_RESULTS: int = 1000

    # Performance optimization settings
    ENABLE_MULTICORE_PARSING: bool = os.getenv("ENABLE_MULTICORE_PARSING", "true").lower() == "true"
    MAX_PARSER_WORKERS: int = int(
        os.getenv("MAX_PARSER_WORKERS", "8"),
    )  # Default to 8 cores (half of typical 16-core system)

    # Service-specific worker settings
    FDA_MAX_WORKERS: int = int(
        os.getenv("FDA_MAX_WORKERS", "8"),
    )  # FDA-specific worker count
    CLINICALTRIALS_MAX_WORKERS: int = int(
        os.getenv("CLINICALTRIALS_MAX_WORKERS", "8"),
    )  # ClinicalTrials-specific worker count

    def get_pubmed_data_dir(self) -> str:
        """Get PubMed data directory"""
        path = f"{self.DATA_DIR}/pubmed"
        os.makedirs(path, exist_ok=True)
        return path

    def get_trials_data_dir(self) -> str:
        """Get ClinicalTrials data directory"""
        path = f"{self.DATA_DIR}/clinicaltrials"
        os.makedirs(path, exist_ok=True)
        return path

    def get_fda_data_dir(self) -> str:
        """Get FDA data directory"""
        path = f"{self.DATA_DIR}/fda"
        os.makedirs(path, exist_ok=True)
        return path

    def get_icd10_data_dir(self) -> str:
        """Get ICD-10 data directory"""
        path = f"{self.DATA_DIR}/icd10"
        os.makedirs(path, exist_ok=True)
        return path

    def get_billing_codes_data_dir(self) -> str:
        """Get billing codes data directory"""
        path = f"{self.DATA_DIR}/billing_codes"
        os.makedirs(path, exist_ok=True)
        return path

    def get_health_info_data_dir(self) -> str:
        """Get health information data directory"""
        path = f"{self.DATA_DIR}/health_info"
        os.makedirs(path, exist_ok=True)
        return path

    def get_enhanced_drug_data_dir(self) -> str:
        """Get enhanced drug data directory for new sources"""
        path = f"{self.DATA_DIR}/enhanced_drug_data"
        os.makedirs(path, exist_ok=True)
        return path

    def get_dailymed_data_dir(self) -> str:
        """Get DailyMed data directory"""
        path = f"{self.DATA_DIR}/enhanced_drug_data/dailymed"
        os.makedirs(path, exist_ok=True)
        return path

    def get_clinical_trials_data_dir(self) -> str:
        """Get ClinicalTrials.gov data directory"""
        path = f"{self.DATA_DIR}/enhanced_drug_data/clinical_trials"
        os.makedirs(path, exist_ok=True)
        return path

    def get_openfda_faers_data_dir(self) -> str:
        """Get OpenFDA FAERS data directory"""
        path = f"{self.DATA_DIR}/enhanced_drug_data/openfda_faers"
        os.makedirs(path, exist_ok=True)
        return path

    def get_rxclass_data_dir(self) -> str:
        """Get RxClass data directory"""
        path = f"{self.DATA_DIR}/enhanced_drug_data/rxclass"
        os.makedirs(path, exist_ok=True)
        return path

    def get_drugcentral_data_dir(self) -> str:
        """Get DrugCentral data directory"""
        path = f"{self.DATA_DIR}/enhanced_drug_data/drugcentral"
        os.makedirs(path, exist_ok=True)
        return path

    def get_ddinter_data_dir(self) -> str:
        """Get DDInter 2.0 data directory"""
        path = f"{self.DATA_DIR}/enhanced_drug_data/ddinter"
        os.makedirs(path, exist_ok=True)
        return path

    def get_lactmed_data_dir(self) -> str:
        """Get LactMed data directory"""
        path = f"{self.DATA_DIR}/enhanced_drug_data/lactmed"
        os.makedirs(path, exist_ok=True)
        return path
