"""
Medical Mirrors - Local mirrors for Healthcare MCP API sources
Provides unlimited access to PubMed, ClinicalTrials.gov, and FDA databases
"""

import logging
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from clinicaltrials.api import ClinicalTrialsAPI
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fda.api import FDAAPI
from pubmed.api import PubMedAPI
from pubmed.api_optimized import OptimizedPubMedAPI

# Import new API modules
from icd10.api import search_icd10_codes, get_icd10_code_details, get_icd10_categories, get_icd10_stats
from billing_codes.api import search_billing_codes, get_billing_code_details, get_billing_categories, get_billing_stats
from health_info.api import (
    search_health_topics, search_exercises, search_foods,
    get_health_topic_details, get_exercise_details, get_food_details,
    get_health_info_stats
)
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from config import Config
from database import Base, get_database_url

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
    pubmed_api: PubMedAPI | OptimizedPubMedAPI = OptimizedPubMedAPI(
        SessionLocal, max_workers=max_workers
    )
    logger.info(
        f"Using optimized multi-core PubMed parser (workers: {max_workers or 'auto-detect'})"
    )
else:
    pubmed_api = PubMedAPI(SessionLocal)
    logger.info("Using standard single-threaded PubMed parser")

trials_api = ClinicalTrialsAPI(SessionLocal)
fda_api = FDAAPI(SessionLocal)

# Initialize new data source APIs (these don't need specific API classes since they use direct database operations)
icd10_session_factory = SessionLocal
billing_session_factory = SessionLocal
health_info_session_factory = SessionLocal


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
async def search_trials(
    condition: str | None = None, location: str | None = None, max_results: int = 10
) -> dict[str, Any]:
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
async def search_fda(
    generic_name: str | None = None, ndc: str | None = None, max_results: int = 10
) -> dict[str, Any]:
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


# ICD-10 Diagnostic Codes Endpoints
@app.get("/icd10/search")
async def search_icd10(
    query: str,
    max_results: int = 10,
    exact_match: bool = False,
    category: str | None = None,
    billable_only: bool = False
) -> dict[str, Any]:
    """
    Search ICD-10 diagnostic codes local mirror
    Matches interface of Healthcare MCP search-icd10 tool
    """
    try:
        results = await search_icd10_codes(query, max_results, exact_match, category, billable_only)
        return {"content": [{"type": "text", "text": str(results)}]}
    except Exception as e:
        logger.exception(f"ICD-10 search failed: {e}")
        raise HTTPException(status_code=500, detail=f"ICD-10 search failed: {str(e)}")


@app.get("/icd10/code/{code}")
async def get_icd10_details(code: str) -> dict[str, Any]:
    """Get detailed information for a specific ICD-10 code"""
    try:
        details = await get_icd10_code_details(code)
        return details
    except Exception as e:
        logger.exception(f"ICD-10 code lookup failed: {e}")
        raise HTTPException(status_code=500, detail=f"ICD-10 lookup failed: {str(e)}")


@app.get("/icd10/categories")
async def get_icd10_categories_endpoint() -> dict[str, Any]:
    """Get all ICD-10 categories and chapters"""
    try:
        return await get_icd10_categories()
    except Exception as e:
        logger.exception(f"ICD-10 categories failed: {e}")
        raise HTTPException(status_code=500, detail=f"Categories failed: {str(e)}")


@app.get("/icd10/stats")
async def get_icd10_stats_endpoint() -> dict[str, Any]:
    """Get ICD-10 database statistics"""
    try:
        return await get_icd10_stats()
    except Exception as e:
        logger.exception(f"ICD-10 stats failed: {e}")
        raise HTTPException(status_code=500, detail=f"Stats failed: {str(e)}")


# Billing Codes (CPT/HCPCS) Endpoints
@app.get("/billing/search")
async def search_billing(
    query: str,
    code_type: str | None = None,
    max_results: int = 10,
    active_only: bool = True,
    category: str | None = None
) -> dict[str, Any]:
    """
    Search medical billing codes local mirror
    Matches interface of Healthcare MCP search-billing-codes tool
    """
    try:
        results = await search_billing_codes(query, code_type, max_results, active_only, category)
        return {"content": [{"type": "text", "text": str(results)}]}
    except Exception as e:
        logger.exception(f"Billing codes search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Billing search failed: {str(e)}")


@app.get("/billing/code/{code}")
async def get_billing_details(code: str) -> dict[str, Any]:
    """Get detailed information for a specific billing code"""
    try:
        details = await get_billing_code_details(code)
        return details
    except Exception as e:
        logger.exception(f"Billing code lookup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Billing lookup failed: {str(e)}")


@app.get("/billing/categories")
async def get_billing_categories_endpoint(code_type: str | None = None) -> dict[str, Any]:
    """Get all billing code categories"""
    try:
        return await get_billing_categories(code_type)
    except Exception as e:
        logger.exception(f"Billing categories failed: {e}")
        raise HTTPException(status_code=500, detail=f"Categories failed: {str(e)}")


@app.get("/billing/stats")
async def get_billing_stats_endpoint() -> dict[str, Any]:
    """Get billing codes database statistics"""
    try:
        return await get_billing_stats()
    except Exception as e:
        logger.exception(f"Billing stats failed: {e}")
        raise HTTPException(status_code=500, detail=f"Stats failed: {str(e)}")


# Health Information Endpoints
@app.get("/health-topics/search")
async def search_health_topics_endpoint(
    query: str,
    category: str | None = None,
    audience: str | None = None,
    max_results: int = 10
) -> dict[str, Any]:
    """
    Search health topics from MyHealthfinder
    Supports lifestyle and health information queries
    """
    try:
        results = await search_health_topics(query, category, audience, max_results)
        return {"content": [{"type": "text", "text": str(results)}]}
    except Exception as e:
        logger.exception(f"Health topics search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health topics search failed: {str(e)}")


@app.get("/health-topics/topic/{topic_id}")
async def get_health_topic_details_endpoint(topic_id: str) -> dict[str, Any]:
    """Get detailed information for a specific health topic"""
    try:
        return await get_health_topic_details(topic_id)
    except Exception as e:
        logger.exception(f"Health topic lookup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health topic lookup failed: {str(e)}")


@app.get("/exercises/search")
async def search_exercises_endpoint(
    query: str,
    body_part: str | None = None,
    equipment: str | None = None,
    difficulty: str | None = None,
    max_results: int = 10
) -> dict[str, Any]:
    """
    Search exercises from ExerciseDB
    Supports physical therapy and fitness queries
    """
    try:
        results = await search_exercises(query, body_part, equipment, difficulty, max_results)
        return {"content": [{"type": "text", "text": str(results)}]}
    except Exception as e:
        logger.exception(f"Exercise search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Exercise search failed: {str(e)}")


@app.get("/exercises/exercise/{exercise_id}")
async def get_exercise_details_endpoint(exercise_id: str) -> dict[str, Any]:
    """Get detailed information for a specific exercise"""
    try:
        return await get_exercise_details(exercise_id)
    except Exception as e:
        logger.exception(f"Exercise lookup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Exercise lookup failed: {str(e)}")


@app.get("/nutrition/search")
async def search_foods_endpoint(
    query: str,
    food_category: str | None = None,
    dietary_flags: str | None = None,
    max_results: int = 10
) -> dict[str, Any]:
    """
    Search food items from USDA FoodData Central
    Supports nutrition and dietary queries
    """
    try:
        results = await search_foods(query, food_category, dietary_flags, max_results)
        return {"content": [{"type": "text", "text": str(results)}]}
    except Exception as e:
        logger.exception(f"Food search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Food search failed: {str(e)}")


@app.get("/nutrition/food/{fdc_id}")
async def get_food_details_endpoint(fdc_id: int) -> dict[str, Any]:
    """Get detailed information for a specific food item"""
    try:
        return await get_food_details(fdc_id)
    except Exception as e:
        logger.exception(f"Food lookup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Food lookup failed: {str(e)}")


@app.get("/health-info/stats")
async def get_health_info_stats_endpoint() -> dict[str, Any]:
    """Get health information database statistics"""
    try:
        return await get_health_info_stats()
    except Exception as e:
        logger.exception(f"Health info stats failed: {e}")
        raise HTTPException(status_code=500, detail=f"Stats failed: {str(e)}")


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


async def background_icd10_update(quick_test: bool = False) -> None:
    """Background task for ICD-10 codes update"""
    try:
        import subprocess
        import os
        
        if quick_test:
            logger.info("🏥 Starting ICD-10 codes background update (QUICK TEST - 100 codes)")
        else:
            logger.info("🏥 Starting ICD-10 codes background update")
        
        # Run the ICD-10 update script with quick_test parameter
        script_path = "/app/update-scripts/update_icd10.sh"
        if os.path.exists(script_path):
            # Pass quick_test as environment variable
            env = os.environ.copy()
            env['QUICK_TEST'] = 'true' if quick_test else 'false'
            
            result = subprocess.run([script_path], capture_output=True, text=True, env=env)
            if result.returncode == 0:
                logger.info(f"✅ ICD-10 background update completed successfully")
            else:
                logger.error(f"❌ ICD-10 update script failed: {result.stderr}")
        else:
            logger.error(f"❌ ICD-10 update script not found: {script_path}")
            
    except Exception as e:
        logger.exception(f"❌ ICD-10 background update failed: {e}")


async def background_billing_update(quick_test: bool = False) -> None:
    """Background task for billing codes update"""
    try:
        import subprocess
        import os
        
        if quick_test:
            logger.info("🏦 Starting billing codes background update (QUICK TEST - 100 codes)")
        else:
            logger.info("🏦 Starting billing codes background update")
        
        # Run the billing codes update script with quick_test parameter
        script_path = "/app/update-scripts/update_billing.sh"
        if os.path.exists(script_path):
            # Pass quick_test as environment variable
            env = os.environ.copy()
            env['QUICK_TEST'] = 'true' if quick_test else 'false'
            
            result = subprocess.run([script_path], capture_output=True, text=True, env=env)
            if result.returncode == 0:
                logger.info(f"✅ Billing codes background update completed successfully")
            else:
                logger.error(f"❌ Billing codes update script failed: {result.stderr}")
        else:
            logger.error(f"❌ Billing codes update script not found: {script_path}")
            
    except Exception as e:
        logger.exception(f"❌ Billing codes background update failed: {e}")


async def background_health_info_update(quick_test: bool = False) -> None:
    """Background task for health information update"""
    try:
        import subprocess
        import os
        
        if quick_test:
            logger.info("📋 Starting health information background update (QUICK TEST - 10 topics)")
        else:
            logger.info("📋 Starting health information background update")
        
        # Run the health info update script with quick_test parameter
        script_path = "/app/update-scripts/update_health_info.sh"
        if os.path.exists(script_path):
            # Pass quick_test as environment variable
            env = os.environ.copy()
            env['QUICK_TEST'] = 'true' if quick_test else 'false'
            
            result = subprocess.run([script_path], capture_output=True, text=True, env=env)
            if result.returncode == 0:
                logger.info(f"✅ Health information background update completed successfully")
            else:
                logger.error(f"❌ Health info update script failed: {result.stderr}")
        else:
            logger.error(f"❌ Health info update script not found: {script_path}")
            
    except Exception as e:
        logger.exception(f"❌ Health information background update failed: {e}")


@app.post("/update/pubmed")
async def trigger_pubmed_update(
    background_tasks: BackgroundTasks, quick_test: bool = False, max_files: int | None = None
) -> dict[str, Any]:
    """Trigger PubMed data update in background"""
    try:
        background_tasks.add_task(background_pubmed_update, quick_test, max_files)
        logger.info(
            f"📚 PubMed update task queued (quick_test={quick_test}, max_files={max_files})"
        )
        return {
            "status": "update_started_in_background",
            "message": "PubMed update task queued successfully",
        }
    except Exception as e:
        logger.exception(f"PubMed update queuing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")


@app.post("/update/trials")
async def trigger_trials_update(
    background_tasks: BackgroundTasks, quick_test: bool = False, limit: int | None = None
) -> dict[str, Any]:
    """Trigger ClinicalTrials data update in background"""
    try:
        background_tasks.add_task(background_trials_update, quick_test, limit)
        logger.info(
            f"🧪 ClinicalTrials update task queued (quick_test={quick_test}, limit={limit})"
        )
        return {
            "status": "update_started_in_background",
            "message": "ClinicalTrials update task queued successfully",
        }
    except Exception as e:
        logger.exception(f"Trials update queuing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")


@app.post("/update/fda")
async def trigger_fda_update(
    background_tasks: BackgroundTasks, quick_test: bool = False, limit: int | None = None
) -> dict[str, Any]:
    """Trigger FDA data update in background"""
    try:
        background_tasks.add_task(background_fda_update, quick_test, limit)
        logger.info(f"💊 FDA update task queued (quick_test={quick_test}, limit={limit})")
        return {
            "status": "update_started_in_background",
            "message": "FDA update task queued successfully",
        }
    except Exception as e:
        logger.exception(f"FDA update queuing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")


@app.post("/update/icd10")
async def trigger_icd10_update(
    background_tasks: BackgroundTasks, quick_test: bool = False
) -> dict[str, Any]:
    """Trigger ICD-10 codes update in background"""
    try:
        background_tasks.add_task(background_icd10_update, quick_test)
        logger.info(f"🏥 ICD-10 update task queued (quick_test={quick_test})")
        return {
            "status": "update_started_in_background",
            "message": "ICD-10 codes update task queued successfully",
        }
    except Exception as e:
        logger.exception(f"ICD-10 update queuing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")


@app.post("/update/billing")
async def trigger_billing_update(
    background_tasks: BackgroundTasks, quick_test: bool = False
) -> dict[str, Any]:
    """Trigger billing codes update in background"""
    try:
        background_tasks.add_task(background_billing_update, quick_test)
        logger.info(f"🏦 Billing codes update task queued (quick_test={quick_test})")
        return {
            "status": "update_started_in_background", 
            "message": "Billing codes update task queued successfully",
        }
    except Exception as e:
        logger.exception(f"Billing codes update queuing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")


@app.post("/update/health-info")
async def trigger_health_info_update(
    background_tasks: BackgroundTasks, quick_test: bool = False
) -> dict[str, Any]:
    """Trigger health information update in background"""
    try:
        background_tasks.add_task(background_health_info_update, quick_test)
        logger.info(f"📋 Health information update task queued (quick_test={quick_test})")
        return {
            "status": "update_started_in_background",
            "message": "Health information update task queued successfully",
        }
    except Exception as e:
        logger.exception(f"Health information update queuing failed: {e}")
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
