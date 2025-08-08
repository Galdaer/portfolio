"""
Medical Mirrors - Local mirrors for Healthcare MCP API sources
Provides unlimited access to PubMed, ClinicalTrials.gov, and FDA databases
"""

import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from clinicaltrials.api import ClinicalTrialsAPI
from database import Base, get_database_url
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fda.api import FDAAPI
from pubmed.api import PubMedAPI
from pubmed.api_optimized import OptimizedPubMedAPI
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from config import Config

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize database
DATABASE_URL = get_database_url()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("Starting Medical Mirrors API")

    # Create database tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

    yield

    logger.info("Shutting down Medical Mirrors API")


# Initialize FastAPI app
app = FastAPI(
    title="Medical Mirrors API",
    description="Local mirrors for Healthcare MCP API sources - unlimited access to medical data",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize API handlers
config = Config()

# Use optimized multi-core parser if enabled
if config.ENABLE_MULTICORE_PARSING:
    max_workers = config.MAX_PARSER_WORKERS if config.MAX_PARSER_WORKERS > 0 else None
    pubmed_api = OptimizedPubMedAPI(SessionLocal, max_workers=max_workers)
    logger.info(f"Using optimized multi-core PubMed parser (workers: {max_workers or 'auto-detect'})")
else:
    pubmed_api = PubMedAPI(SessionLocal)
    logger.info("Using standard single-threaded PubMed parser")

trials_api = ClinicalTrialsAPI(SessionLocal)
fda_api = FDAAPI(SessionLocal)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()

        return {
            "status": "healthy",
            "service": "medical-mirrors",
            "version": "1.0.0",
            "database": "connected",
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.get("/status")
async def get_status():
    """Get status of all mirrors including data freshness"""
    try:
        pubmed_status = await pubmed_api.get_status()
        trials_status = await trials_api.get_status()
        fda_status = await fda_api.get_status()

        return {
            "service": "medical-mirrors",
            "mirrors": {
                "pubmed": pubmed_status,
                "clinicaltrials": trials_status,
                "fda": fda_status,
            },
        }
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail="Status check failed")


# PubMed Mirror Endpoints
@app.get("/pubmed/search")
async def search_pubmed(query: str, max_results: int = 10):
    """
    Search PubMed local mirror
    Matches interface of Healthcare MCP search-pubmed tool
    """
    try:
        results = await pubmed_api.search_articles(query, max_results)
        return {"content": [{"type": "text", "text": str(results)}]}
    except Exception as e:
        logger.error(f"PubMed search failed: {e}")
        raise HTTPException(status_code=500, detail=f"PubMed search failed: {str(e)}")


@app.get("/pubmed/article/{pmid}")
async def get_pubmed_article(pmid: str):
    """Get specific PubMed article by PMID"""
    try:
        article = await pubmed_api.get_article(pmid)
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        return article
    except Exception as e:
        logger.error(f"PubMed article retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Article retrieval failed: {str(e)}")


# ClinicalTrials Mirror Endpoints
@app.get("/trials/search")
async def search_trials(condition: str = None, location: str = None, max_results: int = 10):
    """
    Search ClinicalTrials.gov local mirror
    Matches interface of Healthcare MCP search-trials tool
    """
    try:
        results = await trials_api.search_trials(condition, location, max_results)
        return {"content": [{"type": "text", "text": str(results)}]}
    except Exception as e:
        logger.error(f"Clinical trials search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Trials search failed: {str(e)}")


@app.get("/trials/study/{nct_id}")
async def get_trial_details(nct_id: str):
    """Get specific clinical trial by NCT ID"""
    try:
        trial = await trials_api.get_trial(nct_id)
        if not trial:
            raise HTTPException(status_code=404, detail="Trial not found")
        return trial
    except Exception as e:
        logger.error(f"Trial retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Trial retrieval failed: {str(e)}")


# FDA Mirror Endpoints
@app.get("/fda/search")
async def search_fda(generic_name: str = None, ndc: str = None, max_results: int = 10):
    """
    Search FDA databases local mirror
    Matches interface of Healthcare MCP get-drug-info tool
    """
    try:
        results = await fda_api.search_drugs(generic_name, ndc, max_results)
        return {"content": [{"type": "text", "text": str(results)}]}
    except Exception as e:
        logger.error(f"FDA search failed: {e}")
        raise HTTPException(status_code=500, detail=f"FDA search failed: {str(e)}")


@app.get("/fda/drug/{ndc}")
async def get_drug_info(ndc: str):
    """Get specific drug information by NDC"""
    try:
        drug = await fda_api.get_drug(ndc)
        if not drug:
            raise HTTPException(status_code=404, detail="Drug not found")
        return drug
    except Exception as e:
        logger.error(f"Drug info retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Drug info retrieval failed: {str(e)}")


# Update endpoints for maintenance
@app.post("/update/pubmed")
async def trigger_pubmed_update(quick_test: bool = False, max_files: int = None):
    """Trigger PubMed data update"""
    try:
        result = await pubmed_api.trigger_update(quick_test=quick_test, max_files=max_files)
        return {"status": "update_triggered", "details": result}
    except Exception as e:
        logger.error(f"PubMed update failed: {e}")
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")


@app.post("/update/trials")
async def trigger_trials_update(quick_test: bool = False, limit: int = None):
    """Trigger ClinicalTrials data update"""
    try:
        result = await trials_api.trigger_update(quick_test=quick_test, limit=limit)
        return {"status": "update_triggered", "details": result}
    except Exception as e:
        logger.error(f"Trials update failed: {e}")
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")


@app.post("/update/fda")
async def trigger_fda_update(quick_test: bool = False, limit: int = None):
    """Trigger FDA data update"""
    try:
        result = await fda_api.trigger_update(quick_test=quick_test, limit=limit)
        return {"status": "update_triggered", "details": result}
    except Exception as e:
        logger.error(f"FDA update failed: {e}")
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
