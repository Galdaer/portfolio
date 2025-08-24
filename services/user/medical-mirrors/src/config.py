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

    # Update schedules (in seconds)
    PUBMED_UPDATE_INTERVAL: int = 86400  # Daily
    TRIALS_UPDATE_INTERVAL: int = 604800  # Weekly
    FDA_UPDATE_INTERVAL: int = 2592000  # Monthly
    ICD10_UPDATE_INTERVAL: int = 2592000  # Monthly (ICD codes change rarely)
    BILLING_CODES_UPDATE_INTERVAL: int = 7776000  # Quarterly
    HEALTH_INFO_UPDATE_INTERVAL: int = 604800  # Weekly

    # Rate limiting
    MAX_CONCURRENT_DOWNLOADS: int = 5
    REQUEST_DELAY: float = 0.1  # Seconds between requests

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
        path = f"{self.DATA_DIR}/trials"
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
