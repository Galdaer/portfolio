"""
Configuration for medical mirrors service
"""

import os
from typing import Optional


class Config:
    """Configuration settings for medical mirrors"""
    
    # Database settings
    POSTGRES_URL: str = os.getenv(
        "POSTGRES_URL",
        "postgresql://intelluxe:secure_password@172.20.0.13:5432/intelluxe"
    )
    
    # Data source URLs
    PUBMED_FTP_BASE: str = "ftp://ftp.ncbi.nlm.nih.gov/pubmed/"
    CLINICALTRIALS_API: str = "https://clinicaltrials.gov/api/v2/studies"
    FDA_API_BASE: str = "https://api.fda.gov"
    
    # Update schedules (in seconds)
    PUBMED_UPDATE_INTERVAL: int = 86400  # Daily
    TRIALS_UPDATE_INTERVAL: int = 604800  # Weekly
    FDA_UPDATE_INTERVAL: int = 2592000  # Monthly
    
    # Rate limiting
    MAX_CONCURRENT_DOWNLOADS: int = 5
    REQUEST_DELAY: float = 0.1  # Seconds between requests
    
    # Data paths
    DATA_DIR: str = "/app/data"
    LOGS_DIR: str = "/app/logs"
    
    # Search limits
    DEFAULT_MAX_RESULTS: int = 10
    MAX_SEARCH_RESULTS: int = 1000
    
    @classmethod
    def get_pubmed_data_dir(cls) -> str:
        """Get PubMed data directory"""
        path = f"{cls.DATA_DIR}/pubmed"
        os.makedirs(path, exist_ok=True)
        return path
    
    @classmethod
    def get_trials_data_dir(cls) -> str:
        """Get ClinicalTrials data directory"""
        path = f"{cls.DATA_DIR}/trials"
        os.makedirs(path, exist_ok=True)
        return path
    
    @classmethod
    def get_fda_data_dir(cls) -> str:
        """Get FDA data directory"""
        path = f"{cls.DATA_DIR}/fda"
        os.makedirs(path, exist_ok=True)
        return path
