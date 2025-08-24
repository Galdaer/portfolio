"""
Database configuration and models for medical mirrors
"""

import os
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR
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


class FDADrug(Base):  # type: ignore[misc,valid-type]
    """FDA drug information table - unified data from all FDA sources"""

    __tablename__ = "fda_drugs"

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

    # Data sources tracking
    data_sources = Column(ARRAY(String))  # Track which sources contributed: ndc, orange_book, drugs_fda, labels

    # Search and metadata
    search_vector = Column(TSVECTOR)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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
