"""
FDA API for local mirror
Provides search functionality matching Healthcare MCP interface
"""

import logging
from datetime import datetime
from typing import Any

from error_handling import (
    ErrorCollector,
)
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from database import FDADrug, UpdateLog

from .downloader import FDADownloader
from .parser import FDAParser
from .parser_optimized import OptimizedFDAParser

logger = logging.getLogger(__name__)


class FDAAPI:
    """Local FDA API matching Healthcare MCP interface"""

    def __init__(self, session_factory: Any, config: Any = None) -> None:
        self.session_factory = session_factory
        self.config = config
        self.downloader = FDADownloader()
        self.parser = FDAParser()

        # Use optimized parser if multicore parsing is enabled
        if config and getattr(config, "ENABLE_MULTICORE_PARSING", False):
            max_workers = getattr(config, "FDA_MAX_WORKERS", None)
            self.optimized_parser = OptimizedFDAParser(max_workers=max_workers)
            logger.info(f"Using optimized FDA parser with {max_workers or 'auto'} workers")
        else:
            self.optimized_parser = None

    async def search_drugs(
        self,
        generic_name: str | None = None,
        ndc: str | None = None,
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Search FDA drugs in local database
        Matches the interface of Healthcare MCP get-drug-info tool
        """
        logger.info(
            f"Searching FDA drugs for generic_name: {generic_name}, ndc: {ndc}, max_results: {max_results}",
        )

        db = self.session_factory()
        try:
            # Build search query
            query_parts = []
            params: dict[str, str] = {
                "limit": str(max_results),
            }

            if generic_name:
                query_parts.append("search_vector @@ plainto_tsquery(:generic_name)")
                params["generic_name"] = generic_name
                params["search_term"] = generic_name

            if ndc:
                query_parts.append("ndc = :ndc")
                params["ndc"] = ndc
                if not generic_name:
                    params["search_term"] = ndc

            if not query_parts:
                # No specific search, return recent drugs
                query_parts.append("1=1")
                params["search_term"] = ""

            where_clause = " AND ".join(query_parts)

            if params.get("search_term"):
                search_query = text(f"""
                    SELECT ndc, name, generic_name, brand_name, manufacturer, applicant,
                           ingredients, strength, dosage_form, route, application_number,
                           product_number, approval_date, orange_book_code, reference_listed_drug,
                           therapeutic_class, pharmacologic_class, data_sources,
                           ts_rank(search_vector, plainto_tsquery(:search_term)) as rank
                    FROM fda_drugs
                    WHERE {where_clause}
                    ORDER BY rank DESC, approval_date DESC
                    LIMIT :limit
                """)
            else:
                search_query = text(f"""
                    SELECT ndc, name, generic_name, brand_name, manufacturer, applicant,
                           ingredients, strength, dosage_form, route, application_number,
                           product_number, approval_date, orange_book_code, reference_listed_drug,
                           therapeutic_class, pharmacologic_class, data_sources,
                           0 as rank
                    FROM fda_drugs
                    WHERE {where_clause}
                    ORDER BY approval_date DESC
                    LIMIT :limit
                """)

            result = db.execute(search_query, params)

            drugs = []
            for row in result:
                drug = {
                    "ndc": row.ndc,
                    "name": row.name,
                    "genericName": row.generic_name,
                    "brandName": row.brand_name,
                    "manufacturer": row.manufacturer,
                    "applicant": row.applicant,
                    "ingredients": row.ingredients or [],
                    "strength": row.strength,
                    "dosageForm": row.dosage_form,
                    "route": row.route,
                    "applicationNumber": row.application_number,
                    "productNumber": row.product_number,
                    "approvalDate": row.approval_date,
                    "orangeBookCode": row.orange_book_code,
                    "referenceListedDrug": row.reference_listed_drug,
                    "therapeuticClass": row.therapeutic_class,
                    "pharmacologicClass": row.pharmacologic_class,
                    "dataSources": row.data_sources or [],
                }
                drugs.append(drug)

            logger.info(f"Found {len(drugs)} drugs")
            return drugs

        except Exception as e:
            logger.exception(f"FDA search failed: {e}")
            raise
        finally:
            db.close()

    async def get_drug(self, ndc: str) -> dict | None:
        """Get specific drug by NDC"""
        db = self.session_factory()
        try:
            drug = db.query(FDADrug).filter(FDADrug.ndc == ndc).first()
            if not drug:
                return None

            return {
                "ndc": drug.ndc,
                "name": drug.name,
                "genericName": drug.generic_name,
                "brandName": drug.brand_name,
                "manufacturer": drug.manufacturer,
                "applicant": drug.applicant,
                "ingredients": drug.ingredients or [],
                "strength": drug.strength,
                "dosageForm": drug.dosage_form,
                "route": drug.route,
                "applicationNumber": drug.application_number,
                "productNumber": drug.product_number,
                "approvalDate": drug.approval_date,
                "orangeBookCode": drug.orange_book_code,
                "referenceListedDrug": drug.reference_listed_drug,
                "therapeuticClass": drug.therapeutic_class,
                "pharmacologicClass": drug.pharmacologic_class,
                "dataSources": drug.data_sources or [],
            }

        finally:
            db.close()

    async def get_status(self) -> dict:
        """Get status of FDA mirror"""
        db = self.session_factory()
        try:
            # Get total drug count
            total_count = db.query(func.count(FDADrug.ndc)).scalar()

            # Get last update info
            last_update = (
                db.query(UpdateLog)
                .filter(UpdateLog.source == "fda")
                .order_by(UpdateLog.started_at.desc())
                .first()
            )

            return {
                "source": "fda",
                "total_drugs": total_count,
                "status": "healthy" if total_count > 0 else "empty",
                "last_update": last_update.started_at.isoformat() if last_update else None,
                "last_update_status": last_update.status if last_update else None,
            }

        finally:
            db.close()

    async def trigger_update(self, quick_test: bool = False, limit: int | None = None) -> dict:
        """Trigger FDA data update"""
        if quick_test:
            logger.info(f"Triggering FDA QUICK TEST update (limit={limit or 1000})")
        else:
            logger.info("Triggering FDA data update")

        db = self.session_factory()
        update_log = None
        try:
            # Log update start
            update_log = UpdateLog(
                source="fda",
                update_type="full",  # FDA updates are typically full refreshes
                status="in_progress",
                started_at=datetime.utcnow(),
            )
            db.add(update_log)
            db.commit()

            # Download latest FDA data
            fda_data_dirs = await self.downloader.download_all_fda_data()
            total_processed = 0
            drug_limit = limit or 1000 if quick_test else None

            # Process each dataset
            for dataset_name, data_dir in fda_data_dirs.items():
                if quick_test and drug_limit is not None and total_processed >= drug_limit:
                    logger.info(f"Quick test limit reached: {total_processed} drugs processed")
                    break

                remaining_limit = (
                    (drug_limit - total_processed)
                    if (quick_test and drug_limit is not None)
                    else None
                )
                processed = await self.process_fda_dataset(
                    dataset_name, data_dir, db, quick_test_limit=remaining_limit,
                )
                total_processed += processed

            # Update log
            update_log.status = "success"
            update_log.records_processed = total_processed
            update_log.completed_at = datetime.utcnow()
            db.commit()

            logger.info(f"FDA update completed: {total_processed} drugs processed")
            return {
                "status": "success",
                "records_processed": total_processed,
                "datasets_processed": len(fda_data_dirs),
            }
        except Exception as e:
            logger.exception(f"FDA update failed: {e}")
            if update_log is not None:
                update_log.status = "failed"
                update_log.error_message = str(e)
                update_log.completed_at = datetime.utcnow()
                db.commit()
            raise
            raise
        finally:
            db.close()

    async def process_fda_dataset(
        self, dataset_name: str, data_dir: str, db: Session, quick_test_limit: int | None = None,
    ) -> int:
        """Process a specific FDA dataset"""
        logger.info(f"Processing FDA dataset: {dataset_name}")

        import os

        processed_count = 0

        try:
            # Collect all relevant files for parallel processing
            json_files = []
            csv_files = []

            for file in os.listdir(data_dir):
                file_path = os.path.join(data_dir, file)

                if dataset_name == "ndc" and file.endswith(".json") or dataset_name == "drugs_fda" and file.endswith(".json") or dataset_name == "labels" and file.endswith(".json"):
                    json_files.append(file_path)
                elif dataset_name == "orange_book" and file.endswith((".csv", ".txt")):
                    csv_files.append(file_path)

            # Use optimized parser for JSON files if available
            if json_files and self.optimized_parser:
                logger.info(f"Using optimized parallel parsing for {len(json_files)} {dataset_name} JSON files")
                drugs = await self.optimized_parser.parse_json_files_parallel(json_files, dataset_name)

                if quick_test_limit:
                    drugs = drugs[:quick_test_limit]

                stored = await self.store_drugs_with_merging(drugs, db)
                processed_count += stored

            # Use serial parsing for JSON files if optimized parser not available
            elif json_files:
                for file_path in json_files:
                    if quick_test_limit and processed_count >= quick_test_limit:
                        logger.info(f"Quick test limit reached for {dataset_name}: {processed_count} drugs")
                        break

                    if dataset_name == "ndc":
                        drugs = self.parser.parse_ndc_file(file_path)
                    elif dataset_name == "drugs_fda":
                        drugs = self.parser.parse_drugs_fda_file(file_path)
                    elif dataset_name == "labels":
                        drugs = self.parser.parse_drug_labels_file(file_path)
                    else:
                        continue

                    if quick_test_limit:
                        remaining = quick_test_limit - processed_count
                        drugs = drugs[:remaining]

                    stored = await self.store_drugs_with_merging(drugs, db)
                    processed_count += stored

            # Handle CSV files (Orange Book) - single threaded as it's usually one file
            for file_path in csv_files:
                if quick_test_limit and processed_count >= quick_test_limit:
                    logger.info(f"Quick test limit reached for {dataset_name}: {processed_count} drugs")
                    break

                if self.optimized_parser:
                    drugs = self.optimized_parser.parse_orange_book_file(file_path)
                else:
                    drugs = self.parser.parse_orange_book_file(file_path)

                if quick_test_limit:
                    remaining = quick_test_limit - processed_count
                    drugs = drugs[:remaining]

                stored = await self.store_drugs_with_merging(drugs, db)
                processed_count += stored

            logger.info(f"Processed {processed_count} drugs from {dataset_name}")
            return processed_count

        except Exception as e:
            logger.exception(f"Failed to process dataset {dataset_name}: {e}")
            return processed_count

    async def store_drugs(self, drugs: list[dict], db: Session) -> int:
        """Store drugs in database using proper UPSERT to handle duplicates"""
        stored_count = 0
        error_collector = ErrorCollector("FDA Drug Storage")

        for drug_data in drugs:
            try:
                # Ensure NDC is properly formatted and not None
                ndc = drug_data.get("ndc", "").strip()
                if not ndc:
                    logger.warning(f"Skipping drug with empty NDC: {drug_data}")
                    continue

                # Use PostgreSQL UPSERT (ON CONFLICT DO UPDATE)
                from sqlalchemy.dialects.postgresql import insert

                # Prepare the data for insertion
                insert_data = {
                    "ndc": ndc,
                    "name": drug_data.get("name", ""),
                    "generic_name": drug_data.get("generic_name", ""),
                    "brand_name": drug_data.get("brand_name", ""),
                    "manufacturer": drug_data.get("manufacturer", ""),
                    "ingredients": drug_data.get("ingredients", []),
                    "dosage_form": drug_data.get("dosage_form", ""),
                    "route": drug_data.get("route", ""),
                    "approval_date": drug_data.get("approval_date"),
                    "orange_book_code": drug_data.get("orange_book_code", ""),
                    "therapeutic_class": drug_data.get("therapeutic_class", ""),
                    "updated_at": datetime.utcnow(),
                }

                # Create UPSERT statement
                stmt = insert(FDADrug).values(insert_data)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["ndc"],
                    set_={
                        "name": stmt.excluded.name,
                        "generic_name": stmt.excluded.generic_name,
                        "brand_name": stmt.excluded.brand_name,
                        "manufacturer": stmt.excluded.manufacturer,
                        "ingredients": stmt.excluded.ingredients,
                        "dosage_form": stmt.excluded.dosage_form,
                        "route": stmt.excluded.route,
                        "approval_date": stmt.excluded.approval_date,
                        "orange_book_code": stmt.excluded.orange_book_code,
                        "therapeutic_class": stmt.excluded.therapeutic_class,
                        "updated_at": stmt.excluded.updated_at,
                    },
                )

                db.execute(stmt)
                stored_count += 1

                # Commit in batches
                if stored_count % 100 == 0:
                    db.commit()
                    logger.info(f"Stored batch: {stored_count} drugs")

            except Exception as e:
                ndc = drug_data.get("ndc", "unknown")
                error_collector.record_error(e, record_id=ndc, context="storing drug")
                db.rollback()
                # Continue processing other drugs instead of failing completely

        # Final commit
        try:
            db.commit()
            error_collector.record_success()
            logger.info(f"Successfully stored {stored_count} FDA drugs")
        except Exception as e:
            error_collector.record_error(e, context="final commit")
            logger.exception(f"Final commit failed: {e}")
            db.rollback()

        # Log error summary
        error_collector.log_summary(logger)

        # Update search vectors
        await self.update_search_vectors(db)

        return stored_count

    async def store_drugs_with_merging(self, drugs: list[dict], db: Session) -> int:
        """Store drug data in database with intelligent merging from multiple sources"""
        if not drugs:
            return 0

        # Group drugs by matching records for merging
        grouped_drugs = self.parser.find_matching_records(drugs)
        stored_count = 0

        logger.info(f"Merging {len(drugs)} records into {len(grouped_drugs)} unified drug entries")

        for group_key, drug_group in grouped_drugs.items():
            try:
                # Merge multiple records into one
                merged_drug = self.parser.merge_drug_records(drug_group)

                if not merged_drug.get("ndc"):
                    logger.warning(f"Skipping drug group without NDC: {group_key}")
                    continue

                # Use PostgreSQL UPSERT with enhanced fields
                self.upsert_enhanced_drug(merged_drug, db)
                stored_count += 1

                if stored_count % 500 == 0:
                    logger.info(f"Processed {stored_count} merged drugs...")
                    db.commit()

            except Exception as e:
                logger.warning(f"Failed to store drug group {group_key}: {e}")
                continue

        # Final commit
        try:
            db.commit()
            logger.info(f"Successfully stored {stored_count} merged drug records")
        except Exception as e:
            logger.exception(f"Final commit failed: {e}")
            db.rollback()

        # Update search vectors
        await self.update_search_vectors(db)
        return stored_count

    def upsert_enhanced_drug(self, drug_data: dict, db: Session):
        """Insert or update a drug record using PostgreSQL UPSERT with all enhanced fields"""
        from sqlalchemy.dialects.postgresql import insert

        ndc = drug_data.get("ndc", "").strip()
        if not ndc:
            raise ValueError("NDC is required for drug upsert")

        # Prepare data for insertion with all new fields
        insert_data = {
            "ndc": ndc,
            "name": drug_data.get("name", ""),
            "generic_name": drug_data.get("generic_name", ""),
            "brand_name": drug_data.get("brand_name", ""),
            "manufacturer": drug_data.get("manufacturer", ""),
            "applicant": drug_data.get("applicant", ""),
            "ingredients": drug_data.get("ingredients", []),
            "strength": drug_data.get("strength", ""),
            "dosage_form": drug_data.get("dosage_form", ""),
            "route": drug_data.get("route", ""),
            "application_number": drug_data.get("application_number", ""),
            "product_number": drug_data.get("product_number", ""),
            "approval_date": drug_data.get("approval_date", ""),
            "orange_book_code": drug_data.get("orange_book_code", ""),
            "reference_listed_drug": drug_data.get("reference_listed_drug", ""),
            "therapeutic_class": drug_data.get("therapeutic_class", ""),
            "pharmacologic_class": drug_data.get("pharmacologic_class", ""),
            "data_sources": drug_data.get("data_sources", []),
            "updated_at": datetime.utcnow(),
        }

        # Create intelligent UPSERT statement that merges data
        stmt = insert(FDADrug).values(insert_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=["ndc"],
            set_={
                # Always update basic fields
                "name": stmt.excluded.name,
                "updated_at": stmt.excluded.updated_at,

                # Conditionally update fields - prefer non-empty values
                "generic_name": func.coalesce(
                    func.nullif(stmt.excluded.generic_name, ""),
                    FDADrug.generic_name,
                ),
                "brand_name": func.coalesce(
                    func.nullif(stmt.excluded.brand_name, ""),
                    FDADrug.brand_name,
                ),
                "manufacturer": func.coalesce(
                    func.nullif(stmt.excluded.manufacturer, ""),
                    FDADrug.manufacturer,
                ),
                "applicant": func.coalesce(
                    func.nullif(stmt.excluded.applicant, ""),
                    FDADrug.applicant,
                ),
                "strength": func.coalesce(
                    func.nullif(stmt.excluded.strength, ""),
                    FDADrug.strength,
                ),
                "dosage_form": func.coalesce(
                    func.nullif(stmt.excluded.dosage_form, ""),
                    FDADrug.dosage_form,
                ),
                "route": func.coalesce(
                    func.nullif(stmt.excluded.route, ""),
                    FDADrug.route,
                ),
                "application_number": func.coalesce(
                    func.nullif(stmt.excluded.application_number, ""),
                    FDADrug.application_number,
                ),
                "product_number": func.coalesce(
                    func.nullif(stmt.excluded.product_number, ""),
                    FDADrug.product_number,
                ),
                "approval_date": func.coalesce(
                    func.nullif(stmt.excluded.approval_date, ""),
                    FDADrug.approval_date,
                ),
                "orange_book_code": func.coalesce(
                    func.nullif(stmt.excluded.orange_book_code, ""),
                    FDADrug.orange_book_code,
                ),
                "reference_listed_drug": func.coalesce(
                    func.nullif(stmt.excluded.reference_listed_drug, ""),
                    FDADrug.reference_listed_drug,
                ),
                "therapeutic_class": func.coalesce(
                    func.nullif(stmt.excluded.therapeutic_class, ""),
                    FDADrug.therapeutic_class,
                ),
                "pharmacologic_class": func.coalesce(
                    func.nullif(stmt.excluded.pharmacologic_class, ""),
                    FDADrug.pharmacologic_class,
                ),

                # For arrays, combine unique values
                "ingredients": stmt.excluded.ingredients,
                "data_sources": stmt.excluded.data_sources,
            },
        )

        db.execute(stmt)

    async def update_search_vectors(self, db: Session) -> None:
        """Update full-text search vectors"""
        try:
            update_query = text("""
                UPDATE fda_drugs
                SET search_vector = to_tsvector('english',
                    COALESCE(name, '') || ' ' ||
                    COALESCE(generic_name, '') || ' ' ||
                    COALESCE(brand_name, '') || ' ' ||
                    COALESCE(manufacturer, '') || ' ' ||
                    COALESCE(array_to_string(ingredients, ' '), '') || ' ' ||
                    COALESCE(therapeutic_class, '')
                )
                WHERE search_vector IS NULL
            """)

            db.execute(update_query)
            db.commit()
            logger.info("Updated search vectors for FDA drugs")

        except Exception as e:
            logger.exception(f"Failed to update search vectors: {e}")
            db.rollback()

    async def initialize_data(self) -> dict:
        """Initialize FDA data"""
        logger.info("Initializing FDA data")

        db = self.session_factory()
        try:
            # Check if data already exists
            count = db.query(func.count(FDADrug.ndc)).scalar()
            if count > 0:
                logger.info(f"FDA data already exists: {count} drugs")
                return {"status": "already_initialized", "drug_count": count}

            # Download all FDA data
            fda_data_dirs = await self.downloader.download_all_fda_data()
            total_processed = 0

            # Process each dataset
            for dataset_name, data_dir in fda_data_dirs.items():
                processed = await self.process_fda_dataset(dataset_name, data_dir, db)
                total_processed += processed
                logger.info(f"Processed {processed} drugs from {dataset_name}")

            logger.info(f"FDA initialization completed: {total_processed} drugs")
            return {
                "status": "initialized",
                "records_processed": total_processed,
                "datasets_processed": len(fda_data_dirs),
            }

        except Exception as e:
            logger.exception(f"FDA initialization failed: {e}")
            raise
        finally:
            db.close()
