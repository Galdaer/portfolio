"""
Database configuration and models for medical mirrors
"""

import os
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.dialects.postgresql import ARRAY, JSON, TSVECTOR
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

Base = declarative_base()


def get_database_url() -> str:
    """Get database URL from environment"""
    return os.getenv(
        "POSTGRES_URL",
        "postgresql://intelluxe:secure_password@172.20.0.13:5432/intelluxe_public",
    )


# Global engine instance for migrations and direct database access
engine = create_engine(get_database_url())


def get_db_session() -> Session:
    """Get database session for medical mirrors operations"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


class PubMedArticle(Base):  # type: ignore[misc,valid-type]
    """PubMed articles table with full-text search"""

    __tablename__ = "pubmed_articles"

    pmid = Column(String(20), primary_key=True)  # PubMed ID as primary key
    title = Column(Text)  # Now nullable (was previously nullable=False) to handle missing titles
    abstract = Column(Text)
    authors = Column(ARRAY(String))
    journal = Column(Text)  # Changed from String(500) to Text
    pub_date = Column(String(50))
    doi = Column(String(200))  # Increased from 100 to 200 for longer DOIs
    mesh_terms = Column(ARRAY(String))
    search_vector = Column(TSVECTOR)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ClinicalTrial(Base):  # type: ignore[misc,valid-type]
    """ClinicalTrials.gov studies table"""

    __tablename__ = "clinical_trials"

    nct_id = Column(String(20), primary_key=True)
    title = Column(Text, nullable=True)  # Changed from nullable=False to handle missing titles
    status = Column(String(100))  # Increased from 50 to 100
    phase = Column(String(100))  # Increased from 50 to 100
    conditions = Column(ARRAY(String))
    interventions = Column(ARRAY(String))
    locations = Column(ARRAY(String))
    sponsors = Column(ARRAY(String))
    start_date = Column(String(20))
    completion_date = Column(String(20))
    enrollment = Column(Integer)
    study_type = Column(String(100))  # Increased from 50 to 100
    search_vector = Column(TSVECTOR)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DrugInformationDetail(Base):  # type: ignore[misc,valid-type]
    """Detailed drug information table - all original records from sources
    
    Includes data from:
    - FDA sources: NDC Directory, Orange Book, Drugs@FDA, drug labels
    - NLM RxClass: Therapeutic classifications (EPC, ATC, MoA, PE)
    - Future sources: DailyMed, drug interaction databases
    """

    __tablename__ = "drug_information_old"

    ndc = Column(String(50), primary_key=True)  # Real NDC from NDC Directory or synthetic from Orange Book

    # Core identification
    name = Column(Text, nullable=False)  # Primary display name
    generic_name = Column(Text)  # Generic/active ingredient name
    brand_name = Column(Text)  # Brand/trade name

    # Manufacturing
    manufacturer = Column(Text)  # Manufacturer/labeler name
    applicant = Column(Text)  # Application sponsor (from Orange Book/Drugs@FDA)

    # Drug composition
    ingredients = Column(ARRAY(String))  # Active ingredients list
    strength = Column(Text)  # Strength information

    # Product details
    dosage_form = Column(String(200))  # Tablet, capsule, injection, etc.
    route = Column(String(200))  # Oral, IV, topical, etc.

    # Regulatory information
    application_number = Column(String(20))  # FDA application number (links Orange Book to Drugs@FDA)
    product_number = Column(String(10))  # Product number within application
    approval_date = Column(String(100))  # Approval date

    # Orange Book specific
    orange_book_code = Column(String(20))  # Therapeutic equivalence code (AB, AT, etc.)
    reference_listed_drug = Column(String(5))  # RLD flag (Yes/No)

    # Classification
    therapeutic_class = Column(Text)  # Therapeutic classification
    pharmacologic_class = Column(Text)  # Pharmacologic class

    # Clinical information (from drug labels)
    contraindications = Column(ARRAY(String))  # Contraindications
    warnings = Column(ARRAY(String))  # Warnings and precautions
    precautions = Column(ARRAY(String))  # Precautions
    adverse_reactions = Column(ARRAY(String))  # Adverse reactions
    drug_interactions = Column(JSON)  # Drug interactions (structured)
    
    # Clinical usage
    indications_and_usage = Column(Text)  # Indications and usage
    dosage_and_administration = Column(Text)  # Dosage and administration
    
    # Pharmacology
    mechanism_of_action = Column(Text)  # Mechanism of action
    pharmacokinetics = Column(Text)  # Pharmacokinetics
    pharmacodynamics = Column(Text)  # Pharmacodynamics

    # Additional clinical information fields
    boxed_warning = Column(Text)  # FDA black box warnings
    clinical_studies = Column(Text)  # Clinical trial data and efficacy results
    pediatric_use = Column(Text)  # Pediatric usage information
    geriatric_use = Column(Text)  # Geriatric usage information
    pregnancy = Column(Text)  # Pregnancy category and safety information
    nursing_mothers = Column(Text)  # Lactation safety information
    overdosage = Column(Text)  # Overdose symptoms and treatment
    nonclinical_toxicology = Column(Text)  # Animal study data

    # Data sources tracking
    data_sources = Column(ARRAY(String))  # Track which sources contributed: ndc, orange_book, drugs_fda, labels

    # Search and metadata
    search_vector = Column(TSVECTOR)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DrugInformation(Base):  # type: ignore[misc,valid-type]
    """Consolidated drug information table - single record per generic drug
    
    This table consolidates the 141K drug_information records into ~20K unique
    generic drugs, solving the massive duplication problem while preserving
    all formulation details in structured format.
    """
    
    __tablename__ = "drug_information"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    generic_name = Column(Text, nullable=False, unique=True)  # Normalized generic name
    
    # Aggregated product variations
    brand_names = Column(ARRAY(String), default=[])  # All brand names for this generic
    manufacturers = Column(ARRAY(String), default=[])  # All manufacturers
    formulations = Column(JSON, default=[])  # [{strength, dosage_form, route, ndc, brand_name, manufacturer}]
    
    # Consolidated clinical information (single authoritative values)
    therapeutic_class = Column(Text)  # Most common/authoritative value
    indications_and_usage = Column(Text)  # Longest/most complete version
    mechanism_of_action = Column(Text)  # Longest/most complete version
    contraindications = Column(ARRAY(String), default=[])  # Merged unique values
    warnings = Column(ARRAY(String), default=[])  # Merged unique values
    precautions = Column(ARRAY(String), default=[])  # Merged unique values
    adverse_reactions = Column(ARRAY(String), default=[])  # Merged unique values
    drug_interactions = Column(JSON, default={})  # Merged interaction data
    
    # Additional clinical fields (consolidated)
    dosage_and_administration = Column(Text)
    pharmacokinetics = Column(Text)
    pharmacodynamics = Column(Text)
    boxed_warning = Column(Text)
    clinical_studies = Column(Text)
    pediatric_use = Column(Text)
    geriatric_use = Column(Text)
    pregnancy = Column(Text)
    nursing_mothers = Column(Text)
    overdosage = Column(Text)
    nonclinical_toxicology = Column(Text)
    
    # Regulatory information (aggregated)
    approval_dates = Column(ARRAY(String), default=[])  # All approval dates found
    orange_book_codes = Column(ARRAY(String), default=[])  # All therapeutic equivalence codes
    application_numbers = Column(ARRAY(String), default=[])  # All FDA application numbers
    
    # Metadata and quality metrics
    total_formulations = Column(Integer, default=0)
    data_sources = Column(ARRAY(String), default=[])  # All contributing sources
    confidence_score = Column(Float, default=0.0)  # Quality metric (0.0-1.0)
    has_clinical_data = Column(Boolean, default=False)  # Boolean for clinical data availability
    
    # Search and timestamps
    search_vector = Column(TSVECTOR)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UpdateLog(Base):  # type: ignore[misc,valid-type]
    """Track data update history"""

    __tablename__ = "update_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), nullable=False)  # pubmed, trials, fda
    update_type = Column(String(50), nullable=False)  # full, incremental
    status = Column(String(20), nullable=False)  # success, failed, in_progress
    records_processed = Column(Integer, default=0)
    error_message = Column(Text)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)


