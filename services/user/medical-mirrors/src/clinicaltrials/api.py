"""
ClinicalTrials.gov API for local mirror
Provides search functionality matching Healthcare MCP interface
"""

import logging
from datetime import datetime
from typing import Any

from clinicaltrials.downloader import ClinicalTrialsDownloader
from clinicaltrials.parser import ClinicalTrialsParser
from clinicaltrials.parser_optimized import OptimizedClinicalTrialsParser
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from database import ClinicalTrial, UpdateLog

logger = logging.getLogger(__name__)


class ClinicalTrialsAPI:
    """Local ClinicalTrials.gov API matching Healthcare MCP interface"""

    def __init__(self, session_factory: Any, config: Any = None) -> None:
        self.session_factory = session_factory
        self.config = config
        self.downloader = ClinicalTrialsDownloader()
        self.parser = ClinicalTrialsParser()

        # Use optimized parser if multicore parsing is enabled
        if config and getattr(config, "ENABLE_MULTICORE_PARSING", False):
            max_workers = getattr(config, "CLINICALTRIALS_MAX_WORKERS", None)
            self.optimized_parser = OptimizedClinicalTrialsParser(max_workers=max_workers)
            logger.info(f"Using optimized ClinicalTrials parser with {max_workers or 'auto'} workers")
        else:
            self.optimized_parser = None

    def _is_large_file(self, file_path: str, size_threshold_mb: int = 50) -> bool:
        """Check if a file is large enough to benefit from chunked parallel processing"""
        try:
            import os
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            return file_size_mb > size_threshold_mb
        except:
            return False

    async def search_trials(
        self,
        condition: str | None = None,
        location: str | None = None,
        max_results: int = 10,
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

    async def trigger_update(
        self, quick_test: bool = False, limit: int | None = None,
    ) -> dict[str, Any]:
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
                update_files = await self.downloader.download_recent_updates(
                    days=1,
                )  # Only recent studies
            else:
                update_files = await self.downloader.download_recent_updates()

            total_processed: int = 0
            trials_processed: int = 0

            # Use optimized parser if available and not in quick test mode
            if self.optimized_parser and not quick_test and len(update_files) > 1:
                logger.info(f"Using optimized parallel parsing for {len(update_files)} files")
                all_trials = await self.optimized_parser.parse_json_files_parallel(update_files)
                processed = await self.store_trials(all_trials, db)
                total_processed += processed
                trials_processed += len(all_trials)
            else:
                # Use serial parsing for quick tests or when optimized parser unavailable
                for json_file in update_files:
                    # Check if we have a large JSON file that would benefit from chunking
                    if self.optimized_parser and not quick_test and self._is_large_file(json_file):
                        logger.info(f"Using chunked parallel parsing for large file: {json_file}")
                        trials = await self.optimized_parser.parse_large_json_file_parallel(json_file)
                    else:
                        trials = self.parser.parse_json_file(json_file)

                    # For quick test, limit number of trials processed
                    if quick_test and trials_processed + len(trials) > (limit or 100):
                        trials = trials[: (limit or 100) - trials_processed]
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
        """Store trials in database using advanced cross-batch deduplication engine"""
        from deduplication_engine import CrossBatchDeduplicator
        
        logger.info(f"Storing {len(trials)} trials using advanced deduplication engine...")
        
        if not trials:
            logger.info("No trials to process")
            return 0
        
        # Use the advanced deduplication engine
        deduplicator = CrossBatchDeduplicator(db)
        
        # Process trials with comprehensive deduplication
        results = await deduplicator.process_clinical_trials_batch(trials)
        
        total_processed = results.get('new_records', 0) + results.get('updated_records', 0)
        
        logger.info(f"📊 Advanced Deduplication Results:")
        logger.info(f"   Input trials: {len(trials)}")
        logger.info(f"   After deduplication: {results.get('processed_count', 0)}")
        logger.info(f"   New records: {results.get('new_records', 0)}")
        logger.info(f"   Updated records: {results.get('updated_records', 0)}")
        logger.info(f"   Duplicates removed: {results.get('duplicates_removed', 0)}")
        logger.info(f"   Content duplicates removed: {results.get('content_duplicates_removed', 0)}")
        logger.info(f"   Deduplication rate: {results.get('deduplication_rate', 0):.1f}%")
        
        return total_processed

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

            # Use optimized parser if available for multiple files
            if self.optimized_parser and len(study_files) > 1:
                logger.info(f"Using optimized parallel parsing for {len(study_files)} study files")
                all_trials = await self.optimized_parser.parse_json_files_parallel(study_files)
                processed = await self.store_trials(all_trials, db)
                total_processed += processed
                logger.info(f"Processed {processed} trials using parallel parsing")
            else:
                # Use serial parsing or chunked parsing for large single files
                for json_file in study_files:
                    # Check if we have a large JSON file that would benefit from chunking
                    if self.optimized_parser and self._is_large_file(json_file):
                        logger.info(f"Using chunked parallel parsing for large file: {json_file}")
                        trials = await self.optimized_parser.parse_large_json_file_parallel(json_file)
                    else:
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

    def find_existing_files(self) -> list[str]:
        """Find existing clinical trials JSON files to process"""
        import glob
        import os
        
        data_dir = self.config.get_trials_data_dir()
        
        # Find all compressed JSON files
        json_gz_files = glob.glob(os.path.join(data_dir, "studies_batch_*.json.gz"))
        
        # Sort files for consistent processing order
        json_gz_files.sort()
        
        logger.info(f"Found {len(json_gz_files)} existing clinical trials files to process")
        return json_gz_files

    async def process_existing_files(self, force: bool = False) -> dict[str, Any]:
        """Process existing clinical trials files with advanced deduplication"""
        logger.info("Processing existing ClinicalTrials files with smart deduplication")
        
        db = self.session_factory()
        try:
            # Check if we should skip if data exists (unless forced)
            if not force:
                count = db.query(func.count(ClinicalTrial.nct_id)).scalar()
                if count > 100000:  # Only skip if we have a substantial amount of data
                    logger.info(f"ClinicalTrials data already exists: {count} trials (use force=True to reprocess)")
                    return {"status": "already_processed", "trial_count": count}

            # Find existing files
            study_files = self.find_existing_files()
            if not study_files:
                return {"status": "no_files_found", "trial_count": 0}
            
            # Use the smart batch processor for optimal deduplication
            from deduplication_engine import SmartBatchProcessor
            
            smart_processor = SmartBatchProcessor(db)
            results = await smart_processor.process_clinical_trials_files(study_files, force)
            
            logger.info(f"Smart batch processing completed: {results}")
            
            return {
                "status": results.get('status', 'completed'),
                "records_processed": results.get('total_new_records', 0) + results.get('total_updated_records', 0),
                "files_processed": results.get('files_processed', 0),
                "new_records": results.get('total_new_records', 0),
                "updated_records": results.get('total_updated_records', 0),
                "duplicates_removed": results.get('total_duplicates_removed', 0),
                "content_duplicates_removed": results.get('total_content_duplicates_removed', 0),
                "deduplication_summary": results.get('final_progress', {}),
                "processing_errors": results.get('processing_errors', [])
            }

        except Exception as e:
            logger.exception(f"Smart batch processing failed: {e}")
            raise
        finally:
            db.close()
