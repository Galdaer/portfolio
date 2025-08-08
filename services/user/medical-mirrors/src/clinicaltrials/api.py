"""
ClinicalTrials.gov API for local mirror
Provides search functionality matching Healthcare MCP interface
"""

import logging
from datetime import datetime
from typing import Any

from clinicaltrials.downloader import ClinicalTrialsDownloader
from clinicaltrials.parser import ClinicalTrialsParser
from database import ClinicalTrial, UpdateLog
from sqlalchemy import func, text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ClinicalTrialsAPI:
    """Local ClinicalTrials.gov API matching Healthcare MCP interface"""

    def __init__(self, session_factory: Any) -> None:
        self.session_factory = session_factory
        self.downloader = ClinicalTrialsDownloader()
        self.parser = ClinicalTrialsParser()

    async def search_trials(
        self, condition: str | None = None, location: str | None = None, max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Search clinical trials in local database
        Matches the interface of Healthcare MCP search-trials tool
        """
        logger.info(
            f"Searching trials for condition: {condition}, location: {location}, max_results: {max_results}",
        )

        db = self.session_factory()
        try:
            # Build search query
            query_parts = []
            params: dict[str, Any] = {"limit": max_results}

            if condition:
                query_parts.append("search_vector @@ plainto_tsquery(:condition)")
                params["condition"] = condition

            if location:
                query_parts.append("search_vector @@ plainto_tsquery(:location)")
                params["location"] = location

            where_clause = " AND ".join(query_parts) if query_parts else "1=1"

            search_query = text(f"""
                SELECT nct_id, title, status, phase, conditions, interventions,
                       locations, sponsors, start_date, completion_date, enrollment, study_type,
                       ts_rank(search_vector, plainto_tsquery(:search_term)) as rank
                FROM clinical_trials
                WHERE {where_clause}
                ORDER BY rank DESC, start_date DESC
                LIMIT :limit
            """)

            # Combine search terms
            search_terms = []
            if condition:
                search_terms.append(condition)
            if location:
                search_terms.append(location)
            params["search_term"] = " ".join(search_terms) if search_terms else ""

            result = db.execute(search_query, params)

            trials = []
            for row in result:
                trial = {
                    "nctId": row.nct_id,
                    "title": row.title,
                    "status": row.status,
                    "phase": row.phase,
                    "conditions": row.conditions or [],
                    "interventions": row.interventions or [],
                    "locations": row.locations or [],
                    "sponsors": row.sponsors or [],
                    "startDate": row.start_date,
                    "completionDate": row.completion_date,
                    "enrollment": row.enrollment,
                    "studyType": row.study_type,
                }
                trials.append(trial)

            logger.info(f"Found {len(trials)} trials")
            return trials

        except Exception as e:
            logger.exception(f"Clinical trials search failed: {e}")
            raise
        finally:
            db.close()

    async def get_trial(self, nct_id: str) -> dict[str, Any] | None:
        """Get specific trial by NCT ID"""
        db = self.session_factory()
        try:
            trial = db.query(ClinicalTrial).filter(ClinicalTrial.nct_id == nct_id).first()
            if not trial:
                return None

            return {
                "nctId": trial.nct_id,
                "title": trial.title,
                "status": trial.status,
                "phase": trial.phase,
                "conditions": trial.conditions or [],
                "interventions": trial.interventions or [],
                "locations": trial.locations or [],
                "sponsors": trial.sponsors or [],
                "startDate": trial.start_date,
                "completionDate": trial.completion_date,
                "enrollment": trial.enrollment,
                "studyType": trial.study_type,
            }

        finally:
            db.close()

    async def get_status(self) -> dict[str, Any]:
        """Get status of ClinicalTrials mirror"""
        db = self.session_factory()
        try:
            # Get total trial count
            total_count = db.query(func.count(ClinicalTrial.nct_id)).scalar()

            # Get last update info
            last_update = (
                db.query(UpdateLog)
                .filter(UpdateLog.source == "trials")
                .order_by(UpdateLog.started_at.desc())
                .first()
            )

            return {
                "source": "clinicaltrials",
                "total_trials": total_count,
                "status": "healthy" if total_count > 0 else "empty",
                "last_update": last_update.started_at.isoformat() if last_update else None,
                "last_update_status": last_update.status if last_update else None,
            }

        finally:
            db.close()

    async def trigger_update(self, quick_test: bool = False, limit: int | None = None) -> dict[str, Any]:
        """Trigger ClinicalTrials data update"""
        if quick_test:
            logger.info(f"Triggering ClinicalTrials QUICK TEST update (limit={limit or 100})")
        else:
            logger.info("Triggering ClinicalTrials data update")

        db = self.session_factory()
        update_log: UpdateLog | None = None
        try:
            # Log update start
            update_log = UpdateLog(
                source="trials",
                update_type="incremental",
                status="in_progress",
                started_at=datetime.utcnow(),
            )
            db.add(update_log)
            db.commit()

            # Download and parse updates
            if quick_test:
                # For quick test, download fewer batches
                batch_limit = limit or 100
                logger.info(f"Quick test mode: limiting to {batch_limit} trials")
                update_files = await self.downloader.download_recent_updates(days=1)  # Only recent studies
            else:
                update_files = await self.downloader.download_recent_updates()

            total_processed: int = 0
            trials_processed: int = 0

            for json_file in update_files:
                trials = self.parser.parse_json_file(json_file)

                # For quick test, limit number of trials processed
                if quick_test and trials_processed + len(trials) > (limit or 100):
                    trials = trials[:(limit or 100) - trials_processed]
                    logger.info(f"Quick test: processing {len(trials)} trials from {json_file}")

                processed = await self.store_trials(trials, db)
                total_processed += processed
                trials_processed += len(trials)

                # Stop if we've reached the quick test limit
                if quick_test and trials_processed >= (limit or 100):
                    logger.info(f"Quick test complete: processed {trials_processed} trials")
                    break

            # Update log
            update_log.status = "success"
            update_log.records_processed = total_processed
            update_log.completed_at = datetime.utcnow()
            db.commit()

            logger.info(f"ClinicalTrials update completed: {total_processed} trials processed")
            return {
                "status": "success",
                "records_processed": total_processed,
                "files_processed": len(update_files),
            }

        except Exception as e:
            logger.exception(f"ClinicalTrials update failed: {e}")
            # Only update log if it was created
            if update_log is not None:
                update_log.status = "failed"
                update_log.error_message = str(e)
                update_log.completed_at = datetime.utcnow()
                db.commit()
            else:
                # update_log was not created yet, create a failed log entry
                failed_log = UpdateLog(
                    source="trials",
                    update_type="incremental",
                    status="failed",
                    error_message=str(e),
                    started_at=datetime.utcnow(),
                    completed_at=datetime.utcnow(),
                )
                db.add(failed_log)
                db.commit()
            raise
        finally:
            db.close()

    async def store_trials(self, trials: list[dict[str, Any]], db: Session) -> int:
        """Store trials in database"""
        stored_count = 0

        for trial_data in trials:
            try:
                # Check if trial already exists
                existing = (
                    db.query(ClinicalTrial)
                    .filter(ClinicalTrial.nct_id == trial_data["nct_id"])
                    .first()
                )

                if existing:
                    # Update existing trial
                    for key, value in trial_data.items():
                        setattr(existing, key, value)
                    existing.updated_at = datetime.utcnow()
                else:
                    # Create new trial
                    trial = ClinicalTrial(**trial_data)
                    db.add(trial)

                stored_count += 1

                # Commit in batches
                if stored_count % 100 == 0:
                    db.commit()

            except Exception as e:
                logger.exception(f"Failed to store trial {trial_data.get('nct_id')}: {e}")
                db.rollback()

        # Final commit
        db.commit()

        # Update search vectors
        await self.update_search_vectors(db)

        return stored_count

    async def update_search_vectors(self, db: Session) -> None:
        """Update full-text search vectors"""
        try:
            update_query = text("""
                UPDATE clinical_trials
                SET search_vector = to_tsvector('english',
                    COALESCE(title, '') || ' ' ||
                    COALESCE(array_to_string(conditions, ' '), '') || ' ' ||
                    COALESCE(array_to_string(interventions, ' '), '') || ' ' ||
                    COALESCE(array_to_string(locations, ' '), '') || ' ' ||
                    COALESCE(array_to_string(sponsors, ' '), '')
                )
                WHERE search_vector IS NULL
            """)

            db.execute(update_query)
            db.commit()
            logger.info("Updated search vectors for clinical trials")

        except Exception as e:
            logger.exception(f"Failed to update search vectors: {e}")
            db.rollback()

    async def initialize_data(self) -> dict[str, Any]:
        """Initialize ClinicalTrials data"""
        logger.info("Initializing ClinicalTrials data")

        db = self.session_factory()
        try:
            # Check if data already exists
            count = db.query(func.count(ClinicalTrial.nct_id)).scalar()
            if count > 0:
                logger.info(f"ClinicalTrials data already exists: {count} trials")
                return {"status": "already_initialized", "trial_count": count}

            # Download all studies
            study_files = await self.downloader.download_all_studies()
            total_processed = 0

            for json_file in study_files:
                trials = self.parser.parse_json_file(json_file)
                processed = await self.store_trials(trials, db)
                total_processed += processed
                logger.info(f"Processed {processed} trials from {json_file}")

            logger.info(f"ClinicalTrials initialization completed: {total_processed} trials")
            return {
                "status": "initialized",
                "records_processed": total_processed,
                "files_processed": len(study_files),
            }

        except Exception as e:
            logger.exception(f"ClinicalTrials initialization failed: {e}")
            raise
        finally:
            db.close()
