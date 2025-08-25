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


# Global engine instance for migrations and direct database access with connection pooling
engine = create_engine(
    get_database_url(),
    # Connection pool settings for high-performance bulk operations
    pool_size=20,          # Base number of connections to maintain
    max_overflow=30,       # Additional connections beyond pool_size
    pool_pre_ping=True,    # Validate connections before use
    pool_recycle=3600,     # Recycle connections every hour
    echo=False             # Set to True for SQL debugging
)


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


class ICD10Code(Base):  # type: ignore[misc,valid-type]
    """ICD-10 diagnostic codes table"""

    __tablename__ = "icd10_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True, nullable=False)  # ICD-10 code
    description = Column(Text, nullable=False)
    category = Column(String(200))  # Category name
    chapter = Column(String(200))  # Chapter name
    block = Column(String(200))  # Block name
    billable = Column(Boolean, default=False)
    hcc_category = Column(String(100))  # HCC risk adjustment category
    search_vector = Column(TSVECTOR)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BillingCode(Base):  # type: ignore[misc,valid-type]
    """Medical billing codes (CPT/HCPCS) table"""

    __tablename__ = "billing_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False)  # CPT/HCPCS code
    description = Column(Text, nullable=False)
    code_type = Column(String(20), nullable=False)  # CPT, HCPCS
    category = Column(String(200))
    modifier_applicable = Column(Boolean, default=False)
    price_range_min = Column(Float)
    price_range_max = Column(Float)
    active = Column(Boolean, default=True)
    effective_date = Column(String(20))
    termination_date = Column(String(20))
    search_vector = Column(TSVECTOR)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class HealthTopic(Base):  # type: ignore[misc,valid-type]
    """Health topics from MyHealthfinder"""

    __tablename__ = "health_topics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    topic_id = Column(String(50), unique=True, nullable=False)
    title = Column(Text, nullable=False)
    category = Column(String(100))
    url = Column(Text)
    last_reviewed = Column(String(50))
    audience = Column(ARRAY(String))
    sections = Column(JSON)
    related_topics = Column(ARRAY(String))
    summary = Column(Text)
    keywords = Column(ARRAY(String))
    content_length = Column(Integer)
    source = Column(String(50), default="myhealthfinder")
    search_vector = Column(TSVECTOR)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Exercise(Base):  # type: ignore[misc,valid-type]
    """Exercise information from ExerciseDB"""

    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True, autoincrement=True)
    exercise_id = Column(String(50), unique=True, nullable=False)
    name = Column(Text, nullable=False)
    body_part = Column(String(100))
    equipment = Column(String(100))
    target = Column(String(100))  # Primary target muscle
    secondary_muscles = Column(ARRAY(String))
    instructions = Column(ARRAY(String))
    difficulty_level = Column(String(50))
    exercise_type = Column(String(50))  # strength, cardio, flexibility, etc.
    duration_estimate = Column(String(50))
    calories_estimate = Column(String(50))
    gif_url = Column(Text)
    source = Column(String(50), default="exercisedb")
    search_vector = Column(TSVECTOR)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FoodItem(Base):  # type: ignore[misc,valid-type]
    """Food items from USDA FoodData Central"""

    __tablename__ = "food_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fdc_id = Column(Integer, unique=True, nullable=False)  # USDA FoodData Central ID
    description = Column(Text, nullable=False)
    scientific_name = Column(Text)
    common_names = Column(Text)
    food_category = Column(String(200))
    nutrients = Column(JSON)  # Nutritional information
    nutrition_summary = Column(JSON)  # Key nutritional facts
    brand_owner = Column(String(200))
    ingredients = Column(Text)
    serving_size = Column(Float)
    serving_size_unit = Column(String(50))
    allergens = Column(ARRAY(String))
    dietary_flags = Column(ARRAY(String))  # vegan, gluten-free, etc.
    nutritional_density = Column(Float)  # Overall nutritional score
    source = Column(String(50), default="usda_fooddata")
    search_vector = Column(TSVECTOR)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


