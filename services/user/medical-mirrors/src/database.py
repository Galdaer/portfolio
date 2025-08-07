"""
Database configuration and models for medical mirrors
"""

import os
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


def get_database_url():
    """Get database URL from environment"""
    return os.getenv(
        "POSTGRES_URL", "postgresql://intelluxe:secure_password@172.20.0.13:5432/intelluxe"
    )


class PubMedArticle(Base):
    """PubMed articles table with full-text search"""

    __tablename__ = "pubmed_articles"

    pmid = Column(String(20), primary_key=True)
    title = Column(Text, nullable=False)
    abstract = Column(Text)
    authors = Column(ARRAY(String))
    journal = Column(String(500))
    pub_date = Column(String(50))
    doi = Column(String(100))
    mesh_terms = Column(ARRAY(String))
    search_vector = Column(TSVECTOR)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ClinicalTrial(Base):
    """ClinicalTrials.gov studies table"""

    __tablename__ = "clinical_trials"

    nct_id = Column(String(20), primary_key=True)
    title = Column(Text, nullable=False)
    status = Column(String(50))
    phase = Column(String(50))
    conditions = Column(ARRAY(String))
    interventions = Column(ARRAY(String))
    locations = Column(ARRAY(String))
    sponsors = Column(ARRAY(String))
    start_date = Column(String(20))
    completion_date = Column(String(20))
    enrollment = Column(Integer)
    study_type = Column(String(50))
    search_vector = Column(TSVECTOR)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FDADrug(Base):
    """FDA drug information table"""

    __tablename__ = "fda_drugs"

    ndc = Column(String(20), primary_key=True)
    name = Column(String(500), nullable=False)
    generic_name = Column(String(500))
    brand_name = Column(String(500))
    manufacturer = Column(String(500))
    ingredients = Column(ARRAY(String))
    dosage_form = Column(String(100))
    route = Column(String(100))
    approval_date = Column(String(20))
    orange_book_code = Column(String(10))
    therapeutic_class = Column(String(200))
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
