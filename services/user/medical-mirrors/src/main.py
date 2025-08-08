"""
Medical Mirrors - Local mirrors for Healthcare MCP API sources
Provides unlimited access to PubMed, ClinicalTrials.gov, and FDA databases
"""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from clinicaltrials.api import ClinicalTrialsAPI
from database import Base, get_database_url
from fastapi import BackgroundTasks, FastAPI, HTTPException
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
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan management"""
    logger.info("Starting Medical Mirrors API")

    # Create database tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.exception(f"Database initialization failed: {e}")
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
if hasattr(config, "ENABLE_MULTICORE_PARSING") and config.ENABLE_MULTICORE_PARSING:
    max_workers = config.MAX_PARSER_WORKERS if config.MAX_PARSER_WORKERS > 0 else None
    pubmed_api: PubMedAPI | OptimizedPubMedAPI = OptimizedPubMedAPI(SessionLocal, max_workers=max_workers)
    logger.info(f"Using optimized multi-core PubMed parser (workers: {max_workers or 'auto-detect'})")
else:
    pubmed_api = PubMedAPI(SessionLocal)
    logger.info("Using standard single-threaded PubMed parser")

trials_api = ClinicalTrialsAPI(SessionLocal)
fda_api = FDAAPI(SessionLocal)


@app.get("/health")
async def health_check() -> dict[str, Any]:
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
        logger.exception(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.get("/status")
async def get_status() -> dict[str, Any]:
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
        logger.exception(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail="Status check failed")


# PubMed Mirror Endpoints
@app.get("/pubmed/search")
async def search_pubmed(query: str, max_results: int = 10) -> dict[str, Any]:
    """
    Search PubMed local mirror
    Matches interface of Healthcare MCP search-pubmed tool
    """
    try:
        results = await pubmed_api.search_articles(query, max_results)
        return {"content": [{"type": "text", "text": str(results)}]}
    except Exception as e:
        logger.exception(f"PubMed search failed: {e}")
        raise HTTPException(status_code=500, detail=f"PubMed search failed: {str(e)}")


@app.get("/pubmed/article/{pmid}")
async def get_pubmed_article(pmid: str) -> dict[str, Any]:
    """Get specific PubMed article by PMID"""
    try:
        article = await pubmed_api.get_article(pmid)
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        return article
    except Exception as e:
        logger.exception(f"PubMed article retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Article retrieval failed: {str(e)}")


# ClinicalTrials Mirror Endpoints
@app.get("/trials/search")
async def search_trials(condition: str | None = None, location: str | None = None, max_results: int = 10) -> dict[str, Any]:
    """
    Search ClinicalTrials.gov local mirror
    Matches interface of Healthcare MCP search-trials tool
    """
    try:
        results = await trials_api.search_trials(condition, location, max_results)
        return {"content": [{"type": "text", "text": str(results)}]}
    except Exception as e:
        logger.exception(f"Clinical trials search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Trials search failed: {str(e)}")


@app.get("/trials/study/{nct_id}")
async def get_trial_details(nct_id: str) -> dict[str, Any]:
    """Get specific clinical trial by NCT ID"""
    try:
        trial = await trials_api.get_trial(nct_id)
        if not trial:
            raise HTTPException(status_code=404, detail="Trial not found")
        return trial
    except Exception as e:
        logger.exception(f"Trial retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Trial retrieval failed: {str(e)}")


# FDA Mirror Endpoints
@app.get("/fda/search")
async def search_fda(generic_name: str | None = None, ndc: str | None = None, max_results: int = 10) -> dict[str, Any]:
    """
    Search FDA databases local mirror
    Matches interface of Healthcare MCP get-drug-info tool
    """
    try:
        results = await fda_api.search_drugs(generic_name, ndc, max_results)
        return {"content": [{"type": "text", "text": str(results)}]}
    except Exception as e:
        logger.exception(f"FDA search failed: {e}")
        raise HTTPException(status_code=500, detail=f"FDA search failed: {str(e)}")


@app.get("/fda/drug/{ndc}")
async def get_drug_info(ndc: str) -> dict[str, Any]:
    """Get specific drug information by NDC"""
    try:
        drug = await fda_api.get_drug(ndc)
        if not drug:
            raise HTTPException(status_code=404, detail="Drug not found")
        return drug
    except Exception as e:
        logger.exception(f"Drug info retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Drug info retrieval failed: {str(e)}")


# Update endpoints for maintenance
async def background_pubmed_update(quick_test: bool = False, max_files: int | None = None) -> None:
    """Background task for PubMed update"""
    try:
        logger.info("🚀 Starting PubMed background update")
        result = await pubmed_api.trigger_update(quick_test=quick_test, max_files=max_files)
        logger.info(f"✅ PubMed background update completed: {result}")
    except Exception as e:
        logger.exception(f"❌ PubMed background update failed: {e}")


async def background_trials_update(quick_test: bool = False, limit: int | None = None) -> None:
    """Background task for ClinicalTrials update"""
    try:
        logger.info("🚀 Starting ClinicalTrials background update")
        result = await trials_api.trigger_update(quick_test=quick_test, limit=limit)
        logger.info(f"✅ ClinicalTrials background update completed: {result}")
    except Exception as e:
        logger.exception(f"❌ ClinicalTrials background update failed: {e}")


async def background_fda_update(quick_test: bool = False, limit: int | None = None) -> None:
    """Background task for FDA update"""
    try:
        logger.info("🚀 Starting FDA background update")
        result = await fda_api.trigger_update(quick_test=quick_test, limit=limit)
        logger.info(f"✅ FDA background update completed: {result}")
    except Exception as e:
        logger.exception(f"❌ FDA background update failed: {e}")


@app.post("/update/pubmed")
async def trigger_pubmed_update(background_tasks: BackgroundTasks, quick_test: bool = False, max_files: int | None = None) -> dict[str, Any]:
    """Trigger PubMed data update in background"""
    try:
        background_tasks.add_task(background_pubmed_update, quick_test, max_files)
        logger.info(f"📚 PubMed update task queued (quick_test={quick_test}, max_files={max_files})")
        return {"status": "update_started_in_background", "message": "PubMed update task queued successfully"}
    except Exception as e:
        logger.exception(f"PubMed update queuing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")


@app.post("/update/trials")
async def trigger_trials_update(background_tasks: BackgroundTasks, quick_test: bool = False, limit: int | None = None) -> dict[str, Any]:
    """Trigger ClinicalTrials data update in background"""
    try:
        background_tasks.add_task(background_trials_update, quick_test, limit)
        logger.info(f"🧪 ClinicalTrials update task queued (quick_test={quick_test}, limit={limit})")
        return {"status": "update_started_in_background", "message": "ClinicalTrials update task queued successfully"}
    except Exception as e:
        logger.exception(f"Trials update queuing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")


@app.post("/update/fda")
async def trigger_fda_update(background_tasks: BackgroundTasks, quick_test: bool = False, limit: int | None = None) -> dict[str, Any]:
    """Trigger FDA data update in background"""
    try:
        background_tasks.add_task(background_fda_update, quick_test, limit)
        logger.info(f"💊 FDA update task queued (quick_test={quick_test}, limit={limit})")
        return {"status": "update_started_in_background", "message": "FDA update task queued successfully"}
    except Exception as e:
        logger.exception(f"FDA update queuing failed: {e}")
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
