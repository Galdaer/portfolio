"""
Database configuration and models for medical mirrors
"""

import os
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


def get_database_url():
    """Get database URL from environment"""
    return os.getenv(
        "POSTGRES_URL", "postgresql://intelluxe:secure_password@172.20.0.13:5432/intelluxe"
    )


def get_database_session():
    """Get database session for medical mirrors operations"""
    engine = create_engine(get_database_url())
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


class PubMedArticle(Base):
    """PubMed articles table with full-text search"""

    __tablename__ = "pubmed_articles"

    pmid = Column(String(20), primary_key=True)
    title = Column(Text, nullable=True)  # Changed from nullable=False to handle missing titles
    abstract = Column(Text)
    authors = Column(ARRAY(String))
    journal = Column(Text)  # Changed from String(500) to Text
    pub_date = Column(String(50))
    doi = Column(String(200))  # Increased from 100 to 200 for longer DOIs
    mesh_terms = Column(ARRAY(String))
    search_vector = Column(TSVECTOR)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ClinicalTrial(Base):
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


class FDADrug(Base):
    """FDA drug information table"""

    __tablename__ = "fda_drugs"

    ndc = Column(String(50), primary_key=True)  # Increased from 20 to handle longer NDCs
    name = Column(Text, nullable=False)  # Changed from String(500) to Text for unlimited length
    generic_name = Column(Text)  # Changed from String(500) to Text
    brand_name = Column(Text)  # Changed from String(500) to Text
    manufacturer = Column(Text)  # Changed from String(500) to Text
    ingredients = Column(ARRAY(String))
    dosage_form = Column(String(200))  # Increased from 100 to 200
    route = Column(String(200))  # Increased from 100 to 200
    approval_date = Column(String(20))
    orange_book_code = Column(String(20))  # Increased from 10 to 20
    therapeutic_class = Column(Text)  # Changed from String(200) to Text
    search_vector = Column(TSVECTOR)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UpdateLog(Base):
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
