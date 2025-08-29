"""
Drug Information API for local mirror
Provides comprehensive drug search functionality matching Healthcare MCP interface

Includes data from:
- FDA sources: NDC Directory, Orange Book, Drugs@FDA, drug labels
- NLM RxClass: Therapeutic classifications
- Future sources: DailyMed, drug interaction databases
"""

import builtins
import contextlib
import logging
import os
from datetime import datetime
from typing import Any

from enhanced_drug_sources.dailymed_parser import DailyMedParser
from enhanced_drug_sources.ddinter_parser import DDInterParser
from enhanced_drug_sources.drug_name_matcher import DrugNameMatcher
from enhanced_drug_sources.drugcentral_parser import DrugCentralParser
from enhanced_drug_sources.rxclass_parser import RxClassParser
from error_handling import (
    ErrorCollector,
)
from sqlalchemy import cast, func, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Session
from sqlalchemy.types import String, Text

from database import DrugInformation, UpdateLog

from .downloader import DrugDownloader
from .parser import DrugParser
from .parser_optimized import OptimizedDrugParser

logger = logging.getLogger(__name__)


class DrugAPI:
    """Local drug information API matching Healthcare MCP interface"""

    def __init__(self, session_factory: Any, config: Any = None, enable_downloader: bool = True) -> None:
        self.session_factory = session_factory
        self.config = config

        # Only initialize downloader if needed (for database-only operations, skip it)
        if enable_downloader:
            try:
                self.downloader = DrugDownloader()  # TODO: Rename to DrugDownloader
            except Exception as e:
                logger.warning(f"Failed to initialize drug downloader: {e}. Continuing without downloader.")
                self.downloader = None
        else:
            self.downloader = None

        self.parser = DrugParser()

        # Use optimized parser if multicore parsing is enabled
        if config and getattr(config, "ENABLE_MULTICORE_PARSING", False):
            max_workers = getattr(config, "FDA_MAX_WORKERS", None)
            self.optimized_parser = OptimizedDrugParser(max_workers=max_workers)
            logger.info(f"Using optimized drug parser with {max_workers or 'auto'} workers")
        else:
            self.optimized_parser = None

    async def search_drugs(
        self,
        generic_name: str | None = None,
        ndc: str | None = None,
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Search drug information in consolidated database
        Matches the interface of Healthcare MCP get-drug-info tool
        """
        logger.info(
            f"Searching drug information for generic_name: {generic_name}, ndc: {ndc}, max_results: {max_results}",
        )

        # Use consolidated data for all searches
        if generic_name:
            results = await self.search_consolidated_drugs(generic_name, max_results)
            logger.info(f"Found {len(results)} consolidated drugs")
            return results

        # For NDC-only searches, we can search within the formulations JSON
        if ndc:
            return await self.search_by_ndc(ndc, max_results)

        return []

    async def search_consolidated_drugs(
        self,
        generic_name: str,
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Search in the consolidated drugs table (preferred method)
        Returns clean, deduplicated results with rich formulation data
        """

        db = self.session_factory()
        try:
            # Use full-text search and fuzzy matching for consolidated drugs
            search_query = """
                SELECT
                    generic_name,
                    brand_names,
                    manufacturers,
                    formulations,
                    therapeutic_class,
                    indications_and_usage,
                    mechanism_of_action,
                    contraindications,
                    warnings,
                    adverse_reactions,
                    drug_interactions,
                    dosage_and_administration,
                    total_formulations,
                    confidence_score,
                    has_clinical_data,
                    ts_rank_cd(search_vector, plainto_tsquery('english', :search_term)) as relevance
                FROM drug_information
                WHERE search_vector @@ plainto_tsquery('english', :search_term)
                   OR LOWER(generic_name) LIKE LOWER(:fuzzy_search)
                   OR EXISTS (
                       SELECT 1 FROM unnest(brand_names) brand
                       WHERE LOWER(brand) LIKE LOWER(:fuzzy_search)
                   )
                ORDER BY relevance DESC, confidence_score DESC
                LIMIT :limit
            """

            params = {
                "search_term": generic_name,
                "fuzzy_search": f"%{generic_name}%",
                "limit": max_results,
            }

            result = db.execute(text(search_query), params)
            rows = result.fetchall()

            drugs = []
            for row in rows:
                drug_data = {
                    "generic_name": row.generic_name,
                    "brand_names": row.brand_names or [],
                    "manufacturers": row.manufacturers or [],
                    "formulations": row.formulations or [],
                    "therapeutic_class": row.therapeutic_class,
                    "indications_and_usage": row.indications_and_usage,
                    "mechanism_of_action": row.mechanism_of_action,
                    "contraindications": row.contraindications or [],
                    "warnings": row.warnings or [],
                    "adverse_reactions": row.adverse_reactions or [],
                    "drug_interactions": row.drug_interactions or {},
                    "dosage_and_administration": row.dosage_and_administration,
                    "total_formulations": row.total_formulations or 0,
                    "confidence_score": float(row.confidence_score) if row.confidence_score else 0.0,
                    "has_clinical_data": row.has_clinical_data,
                    "data_source": "consolidated",
                    "relevance_score": float(row.relevance) if row.relevance else 0.0,
                }
                drugs.append(drug_data)

            return drugs

        except Exception as e:
            logger.exception(f"Consolidated drug search failed: {e}")
            return []
        finally:
            db.close()

    async def search_by_ndc(
        self,
        ndc: str,
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Search for drugs by NDC within consolidated formulations data
        """
        logger.info(f"Searching consolidated drugs by NDC: {ndc}")

        db = self.session_factory()
        try:
            # Search for NDCs within the formulations JSON array
            search_query = """
                SELECT
                    generic_name,
                    brand_names,
                    manufacturers,
                    formulations,
                    therapeutic_class,
                    indications_and_usage,
                    mechanism_of_action,
                    contraindications,
                    warnings,
                    adverse_reactions,
                    drug_interactions,
                    dosage_and_administration,
                    total_formulations,
                    confidence_score,
                    has_clinical_data
                FROM drug_information
                WHERE EXISTS (
                    SELECT 1 FROM jsonb_array_elements(formulations) AS f
                    WHERE f->>'ndc' = :ndc
                )
                LIMIT :limit
            """

            result = db.execute(text(search_query), {"ndc": ndc, "limit": max_results})
            rows = result.fetchall()

            drugs = []
            for row in rows:
                # Find the specific formulation with this NDC
                formulations = row.formulations or []
                matching_formulation = None
                for form in formulations:
                    if form.get("ndc") == ndc:
                        matching_formulation = form
                        break

                drug = {
                    "genericName": row.generic_name,
                    "brandNames": row.brand_names or [],
                    "manufacturers": row.manufacturers or [],
                    "therapeuticClass": row.therapeutic_class,
                    "indicationsAndUsage": row.indications_and_usage,
                    "mechanismOfAction": row.mechanism_of_action,
                    "contraindications": row.contraindications or [],
                    "warnings": row.warnings or [],
                    "adverseReactions": row.adverse_reactions or [],
                    "drugInteractions": row.drug_interactions or {},
                    "dosageAndAdministration": row.dosage_and_administration,
                    "totalFormulations": row.total_formulations,
                    "confidenceScore": row.confidence_score,
                    "hasClinicalData": row.has_clinical_data,
                    # Include the specific matching formulation
                    "matchingFormulation": matching_formulation,
                }
                drugs.append(drug)

            logger.info(f"Found {len(drugs)} drugs with NDC {ndc}")
            return drugs

        except Exception as e:
            logger.exception(f"NDC search failed: {e}")
            return []
        finally:
            db.close()

    async def get_drug(self, ndc: str) -> dict | None:
        """Get specific drug by NDC"""
        db = self.session_factory()
        try:
            drug = db.query(DrugInformation).filter(DrugInformation.ndc == ndc).first()
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
            total_count = db.query(func.count(DrugInformation.id)).scalar()

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
            if not self.downloader:
                raise ValueError("FDA downloader not available. Initialize with enable_downloader=True.")
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
                stmt = insert(DrugInformation).values(insert_data)
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
        """Store drug data in database with intelligent merging and parallel processing"""
        if not drugs:
            return 0

        # Group drugs by matching records for merging
        grouped_drugs = self.parser.find_matching_records(drugs)

        logger.info(f"Merging {len(drugs)} records into {len(grouped_drugs)} unified drug entries")
        logger.info("Using high-performance parallel storage with batch operations")

        # Merge all drugs first (CPU-intensive, do this before I/O)
        merged_drugs = []
        merge_failures = 0

        for group_key, drug_group in grouped_drugs.items():
            try:
                merged_drug = self.parser.merge_drug_records(drug_group)
                if merged_drug.get("ndc"):
                    merged_drugs.append(merged_drug)
                else:
                    logger.warning(f"Skipping drug group without NDC: {group_key}")
            except Exception as e:
                logger.warning(f"Failed to merge drug group {group_key}: {e}")
                merge_failures += 1
                continue

        if merge_failures > 0:
            logger.warning(f"Failed to merge {merge_failures} drug groups")

        # Consolidate drugs by generic name, merging data for fullest information
        consolidated_drugs = {}
        duplicate_count = 0

        for drug in merged_drugs:
            generic_name = drug.get("generic_name", "").strip().upper()
            if not generic_name:
                continue

            if generic_name in consolidated_drugs:
                # Merge this drug data with existing entry
                existing = consolidated_drugs[generic_name]
                duplicate_count += 1

                # Merge arrays by combining unique values
                for array_field in ["brand_names", "manufacturers", "contraindications", "warnings",
                                  "precautions", "adverse_reactions", "approval_dates",
                                  "orange_book_codes", "application_numbers", "data_sources"]:
                    existing_values = set(existing.get(array_field, []))
                    new_values = set(drug.get(array_field, []))
                    consolidated_drugs[generic_name][array_field] = list(existing_values | new_values)

                # Merge formulations
                existing_formulations = existing.get("formulations", [])
                new_formulations = drug.get("formulations", [])
                consolidated_drugs[generic_name]["formulations"] = existing_formulations + new_formulations
                consolidated_drugs[generic_name]["total_formulations"] = len(existing_formulations) + len(new_formulations)

                # Use longer/better text fields
                for text_field in ["therapeutic_class", "indications_and_usage", "mechanism_of_action",
                                 "dosage_and_administration", "pharmacokinetics", "pharmacodynamics",
                                 "boxed_warning", "clinical_studies", "pediatric_use", "geriatric_use",
                                 "pregnancy", "nursing_mothers", "overdosage", "nonclinical_toxicology"]:
                    existing_text = existing.get(text_field, "") or ""
                    new_text = drug.get(text_field, "") or ""
                    if len(new_text) > len(existing_text):
                        consolidated_drugs[generic_name][text_field] = new_text

                # Merge drug interactions (JSON)
                existing_interactions = existing.get("drug_interactions", {})
                new_interactions = drug.get("drug_interactions", {})
                consolidated_drugs[generic_name]["drug_interactions"] = {**existing_interactions, **new_interactions}

                # Update confidence score to highest
                existing_confidence = existing.get("confidence_score", 0.0)
                new_confidence = drug.get("confidence_score", 0.0)
                consolidated_drugs[generic_name]["confidence_score"] = max(existing_confidence, new_confidence)

                # Update clinical data flag
                consolidated_drugs[generic_name]["has_clinical_data"] = (
                    existing.get("has_clinical_data", False) or drug.get("has_clinical_data", False)
                )

            else:
                consolidated_drugs[generic_name] = drug.copy()

        deduplicated_drugs = list(consolidated_drugs.values())
        if duplicate_count > 0:
            logger.info(f"Consolidated {duplicate_count} duplicate generic names, proceeding with {len(deduplicated_drugs)} unique drugs")

        logger.info(f"Successfully merged {len(deduplicated_drugs)} drugs, starting parallel database storage")

        # Use parallel batch storage for maximum speed
        stored_count = await self.store_drugs_parallel_batched(deduplicated_drugs)

        # Update search vectors
        await self.update_search_vectors(db)
        return stored_count

    async def store_drugs_parallel_batched(self, drugs: list[dict]) -> int:
        """Store drugs using parallel workers with batch operations for maximum performance"""
        import asyncio
        import threading
        from concurrent.futures import ThreadPoolExecutor

        if not drugs:
            return 0

        # Configuration for high performance
        batch_size = 500  # Records per batch
        max_workers = 10  # Parallel database workers

        # Create batches
        batches = [drugs[i:i + batch_size] for i in range(0, len(drugs), batch_size)]
        logger.info(f"Created {len(batches)} batches of {batch_size} drugs each for parallel processing")

        # Thread-local storage for database sessions
        thread_local = threading.local()

        def get_thread_db_session():
            """Get a database session for this thread"""
            if not hasattr(thread_local, "session"):
                thread_local.session = self.session_factory()
            return thread_local.session

        def process_batch(batch_drugs: list[dict]) -> int:
            """Process a batch of drugs in a single database transaction"""
            thread_db = get_thread_db_session()
            batch_count = 0

            try:
                # Prepare all batch data
                insert_data_list = []
                for drug_data in batch_drugs:
                    insert_data = self.prepare_drug_insert_data(drug_data)
                    if insert_data:
                        insert_data_list.append(insert_data)

                if insert_data_list:
                    # Use batch UPSERT for maximum speed
                    self.batch_upsert_drugs(insert_data_list, thread_db)
                    batch_count = len(insert_data_list)

                thread_db.commit()
                return batch_count

            except Exception as e:
                logger.exception(f"Failed to process batch: {e}")
                thread_db.rollback()
                return 0

        # Process batches in parallel
        total_stored = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all batches
            future_to_batch = {executor.submit(process_batch, batch): i
                             for i, batch in enumerate(batches)}

            # Collect results as they complete
            completed_batches = 0
            for future in asyncio.as_completed([asyncio.wrap_future(f) for f in future_to_batch]):
                try:
                    batch_stored = await future
                    total_stored += batch_stored
                    completed_batches += 1

                    if completed_batches % 5 == 0 or completed_batches == len(batches):
                        logger.info(f"Completed {completed_batches}/{len(batches)} batches, stored {total_stored} drugs")

                except Exception as e:
                    logger.exception(f"Batch processing failed: {e}")

        logger.info(f"Parallel batch storage completed: {total_stored} drugs stored using {max_workers} workers")
        return total_stored

    def prepare_drug_insert_data(self, drug_data: dict) -> dict | None:
        """Prepare drug data for database insertion"""
        try:
            # Use generic_name as the primary key (not ndc)
            generic_name = drug_data.get("generic_name", "").strip()
            if not generic_name:
                return None

            def get_non_empty_or_none(value):
                """Return None if value is empty string, otherwise return value"""
                if isinstance(value, str) and value.strip() == "":
                    return None
                if isinstance(value, list) and len(value) == 0:
                    return None
                if isinstance(value, dict) and len(value) == 0:
                    return None
                return value

            # Safely extract name with multiple fallbacks
            drug_data.get("name", "") or drug_data.get("generic_name", "") or drug_data.get("brand_name", "") or "Unknown"

            # Extract brand names as array
            brand_names = []
            brand_name = drug_data.get("brand_name")
            if brand_name and isinstance(brand_name, str) and brand_name.strip():
                brand_names = [brand_name.strip()]
            elif isinstance(brand_name, list):
                brand_names = [b.strip() for b in brand_name if b and isinstance(b, str) and b.strip()]

            # Extract manufacturers as array
            manufacturers = []
            manufacturer = drug_data.get("manufacturer")
            if manufacturer and isinstance(manufacturer, str) and manufacturer.strip():
                manufacturers = [manufacturer.strip()]
            elif isinstance(manufacturer, list):
                manufacturers = [m.strip() for m in manufacturer if m and isinstance(m, str) and m.strip()]

            # Build formulation entry
            formulation = {}
            if drug_data.get("strength"):
                formulation["strength"] = drug_data.get("strength")
            if drug_data.get("dosage_form"):
                formulation["dosage_form"] = drug_data.get("dosage_form")
            if drug_data.get("route"):
                formulation["route"] = drug_data.get("route")
            if drug_data.get("ndc"):
                formulation["ndc"] = drug_data.get("ndc")
            if brand_name:
                formulation["brand_name"] = brand_name
            if manufacturer:
                formulation["manufacturer"] = manufacturer
            if drug_data.get("application_number"):
                formulation["application_number"] = drug_data.get("application_number")

            formulations = [formulation] if formulation else []

            # Convert single values to arrays for list fields
            def ensure_array(value):
                if not value:
                    return []
                if isinstance(value, list):
                    return [str(v) for v in value if v]
                return [str(value)]

            return {
                "generic_name": generic_name,
                "brand_names": brand_names,
                "manufacturers": manufacturers,
                "formulations": formulations,
                "therapeutic_class": get_non_empty_or_none(drug_data.get("therapeutic_class")),
                "indications_and_usage": get_non_empty_or_none(drug_data.get("indications_and_usage")),
                "mechanism_of_action": get_non_empty_or_none(drug_data.get("mechanism_of_action")),
                "contraindications": ensure_array(drug_data.get("contraindications")),
                "warnings": ensure_array(drug_data.get("warnings")),
                "precautions": ensure_array(drug_data.get("precautions")),
                "adverse_reactions": ensure_array(drug_data.get("adverse_reactions")),
                "drug_interactions": drug_data.get("drug_interactions", {}),
                "dosage_and_administration": get_non_empty_or_none(drug_data.get("dosage_and_administration")),
                "pharmacokinetics": get_non_empty_or_none(drug_data.get("pharmacokinetics")),
                "pharmacodynamics": get_non_empty_or_none(drug_data.get("pharmacodynamics")),
                "boxed_warning": get_non_empty_or_none(drug_data.get("boxed_warning")),
                "clinical_studies": get_non_empty_or_none(drug_data.get("clinical_studies")),
                "pediatric_use": get_non_empty_or_none(drug_data.get("pediatric_use")),
                "geriatric_use": get_non_empty_or_none(drug_data.get("geriatric_use")),
                "pregnancy": get_non_empty_or_none(drug_data.get("pregnancy")),
                "nursing_mothers": get_non_empty_or_none(drug_data.get("nursing_mothers")),
                "overdosage": get_non_empty_or_none(drug_data.get("overdosage")),
                "nonclinical_toxicology": get_non_empty_or_none(drug_data.get("nonclinical_toxicology")),
                "approval_dates": ensure_array(drug_data.get("approval_date")),
                "orange_book_codes": ensure_array(drug_data.get("orange_book_code")),
                "application_numbers": ensure_array(drug_data.get("application_number")),
                "total_formulations": 1,
                "data_sources": ensure_array(drug_data.get("data_sources", ["FDA_Labels"])),
                "confidence_score": drug_data.get("confidence_score", 0.8),
                "has_clinical_data": bool(
                    drug_data.get("indications_and_usage") or
                    drug_data.get("mechanism_of_action") or
                    drug_data.get("contraindications") or
                    drug_data.get("warnings"),
                ),
                "last_updated": datetime.utcnow(),
            }

        except Exception as e:
            logger.exception(f"Error preparing drug insert data: {e}")
            return None

    def batch_upsert_drugs(self, insert_data_list: list[dict], db: Session):
        """Perform batch UPSERT operation for consolidated drug schema"""
        from sqlalchemy.dialects.postgresql import insert

        if not insert_data_list:
            return

        # Use PostgreSQL's powerful ON CONFLICT DO UPDATE for batch operations
        stmt = insert(DrugInformation)

        # Configure UPSERT with intelligent field merging (using generic_name as unique key)
        stmt = stmt.on_conflict_do_update(
            index_elements=["generic_name"],
            set_={
                # Always update timestamps
                "last_updated": stmt.excluded.last_updated,

                # Merge arrays intelligently - combine unique values
                "brand_names": func.array_cat(
                    func.coalesce(DrugInformation.brand_names, cast([], ARRAY(String))),
                    stmt.excluded.brand_names,
                ),
                "manufacturers": func.array_cat(
                    func.coalesce(DrugInformation.manufacturers, cast([], ARRAY(String))),
                    stmt.excluded.manufacturers,
                ),
                "formulations": func.coalesce(
                    stmt.excluded.formulations,
                    DrugInformation.formulations,
                ),
                "approval_dates": func.array_cat(
                    func.coalesce(DrugInformation.approval_dates, cast([], ARRAY(String))),
                    stmt.excluded.approval_dates,
                ),
                "orange_book_codes": func.array_cat(
                    func.coalesce(DrugInformation.orange_book_codes, cast([], ARRAY(String))),
                    stmt.excluded.orange_book_codes,
                ),
                "application_numbers": func.array_cat(
                    func.coalesce(DrugInformation.application_numbers, cast([], ARRAY(String))),
                    stmt.excluded.application_numbers,
                ),
                "data_sources": func.array_cat(
                    func.coalesce(DrugInformation.data_sources, cast([], ARRAY(String))),
                    stmt.excluded.data_sources,
                ),

                # Clinical text fields - use new data if better (longer/non-empty)
                "therapeutic_class": func.coalesce(
                    func.nullif(stmt.excluded.therapeutic_class, ""),
                    DrugInformation.therapeutic_class,
                ),
                "indications_and_usage": func.coalesce(
                    func.nullif(stmt.excluded.indications_and_usage, ""),
                    DrugInformation.indications_and_usage,
                ),
                "mechanism_of_action": func.coalesce(
                    func.nullif(stmt.excluded.mechanism_of_action, ""),
                    DrugInformation.mechanism_of_action,
                ),
                "dosage_and_administration": func.coalesce(
                    func.nullif(stmt.excluded.dosage_and_administration, ""),
                    DrugInformation.dosage_and_administration,
                ),
                "pharmacokinetics": func.coalesce(
                    func.nullif(stmt.excluded.pharmacokinetics, ""),
                    DrugInformation.pharmacokinetics,
                ),
                "pharmacodynamics": func.coalesce(
                    func.nullif(stmt.excluded.pharmacodynamics, ""),
                    DrugInformation.pharmacodynamics,
                ),
                "boxed_warning": func.coalesce(
                    func.nullif(stmt.excluded.boxed_warning, ""),
                    DrugInformation.boxed_warning,
                ),
                "clinical_studies": func.coalesce(
                    func.nullif(stmt.excluded.clinical_studies, ""),
                    DrugInformation.clinical_studies,
                ),
                "pediatric_use": func.coalesce(
                    func.nullif(stmt.excluded.pediatric_use, ""),
                    DrugInformation.pediatric_use,
                ),
                "geriatric_use": func.coalesce(
                    func.nullif(stmt.excluded.geriatric_use, ""),
                    DrugInformation.geriatric_use,
                ),
                "pregnancy": func.coalesce(
                    func.nullif(stmt.excluded.pregnancy, ""),
                    DrugInformation.pregnancy,
                ),
                "nursing_mothers": func.coalesce(
                    func.nullif(stmt.excluded.nursing_mothers, ""),
                    DrugInformation.nursing_mothers,
                ),
                "overdosage": func.coalesce(
                    func.nullif(stmt.excluded.overdosage, ""),
                    DrugInformation.overdosage,
                ),
                "nonclinical_toxicology": func.coalesce(
                    func.nullif(stmt.excluded.nonclinical_toxicology, ""),
                    DrugInformation.nonclinical_toxicology,
                ),

                # Clinical arrays - merge unique values
                "contraindications": func.array_cat(
                    func.coalesce(DrugInformation.contraindications, cast([], ARRAY(String))),
                    stmt.excluded.contraindications,
                ),
                "warnings": func.array_cat(
                    func.coalesce(DrugInformation.warnings, cast([], ARRAY(String))),
                    stmt.excluded.warnings,
                ),
                "precautions": func.array_cat(
                    func.coalesce(DrugInformation.precautions, cast([], ARRAY(String))),
                    stmt.excluded.precautions,
                ),
                "adverse_reactions": func.array_cat(
                    func.coalesce(DrugInformation.adverse_reactions, cast([], ARRAY(String))),
                    stmt.excluded.adverse_reactions,
                ),

                # JSON field - merge intelligently
                "drug_interactions": func.coalesce(
                    stmt.excluded.drug_interactions,
                    DrugInformation.drug_interactions,
                ),

                # Computed fields
                "total_formulations": func.coalesce(
                    stmt.excluded.total_formulations,
                    DrugInformation.total_formulations,
                ),
                "confidence_score": func.greatest(
                    stmt.excluded.confidence_score,
                    DrugInformation.confidence_score,
                ),
                "has_clinical_data": func.coalesce(
                    stmt.excluded.has_clinical_data,
                    DrugInformation.has_clinical_data,
                ),
            },
        )

        # Execute batch insert
        db.execute(stmt, insert_data_list)

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

            # Clinical information fields
            "contraindications": drug_data.get("contraindications", []),
            "warnings": drug_data.get("warnings", []),
            "precautions": drug_data.get("precautions", []),
            "adverse_reactions": drug_data.get("adverse_reactions", []),
            "drug_interactions": drug_data.get("drug_interactions", {}),
            "indications_and_usage": drug_data.get("indications_and_usage", ""),
            "dosage_and_administration": drug_data.get("dosage_and_administration", ""),
            "mechanism_of_action": drug_data.get("mechanism_of_action", ""),
            "pharmacokinetics": drug_data.get("pharmacokinetics", ""),
            "pharmacodynamics": drug_data.get("pharmacodynamics", ""),

            # Additional clinical fields
            "boxed_warning": drug_data.get("boxed_warning", ""),
            "clinical_studies": drug_data.get("clinical_studies", ""),
            "pediatric_use": drug_data.get("pediatric_use", ""),
            "geriatric_use": drug_data.get("geriatric_use", ""),
            "pregnancy": drug_data.get("pregnancy", ""),
            "nursing_mothers": drug_data.get("nursing_mothers", ""),
            "overdosage": drug_data.get("overdosage", ""),
            "nonclinical_toxicology": drug_data.get("nonclinical_toxicology", ""),

            "data_sources": drug_data.get("data_sources", []),
            "updated_at": datetime.utcnow(),
        }

        # Create intelligent UPSERT statement that merges data
        stmt = insert(DrugInformation).values(insert_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=["ndc"],
            set_={
                # Always update basic fields
                "name": stmt.excluded.name,
                "updated_at": stmt.excluded.updated_at,

                # Always update with new values if they're better (non-empty)
                "generic_name": func.coalesce(
                    func.nullif(stmt.excluded.generic_name, ""),
                    DrugInformation.generic_name,
                ),
                "brand_name": func.coalesce(
                    func.nullif(stmt.excluded.brand_name, ""),
                    DrugInformation.brand_name,
                ),
                "manufacturer": func.coalesce(
                    func.nullif(stmt.excluded.manufacturer, ""),
                    DrugInformation.manufacturer,
                ),
                "applicant": func.coalesce(
                    func.nullif(stmt.excluded.applicant, ""),
                    DrugInformation.applicant,
                ),
                "strength": func.coalesce(
                    func.nullif(stmt.excluded.strength, ""),
                    DrugInformation.strength,
                ),
                "dosage_form": func.coalesce(
                    func.nullif(stmt.excluded.dosage_form, ""),
                    DrugInformation.dosage_form,
                ),
                "route": func.coalesce(
                    func.nullif(stmt.excluded.route, ""),
                    DrugInformation.route,
                ),
                "application_number": func.coalesce(
                    func.nullif(stmt.excluded.application_number, ""),
                    DrugInformation.application_number,
                ),
                "product_number": func.coalesce(
                    func.nullif(stmt.excluded.product_number, ""),
                    DrugInformation.product_number,
                ),
                "approval_date": func.coalesce(
                    func.nullif(stmt.excluded.approval_date, ""),
                    DrugInformation.approval_date,
                ),
                "orange_book_code": func.coalesce(
                    func.nullif(stmt.excluded.orange_book_code, ""),
                    DrugInformation.orange_book_code,
                ),
                "reference_listed_drug": func.coalesce(
                    func.nullif(stmt.excluded.reference_listed_drug, ""),
                    DrugInformation.reference_listed_drug,
                ),
                "therapeutic_class": func.coalesce(
                    func.nullif(stmt.excluded.therapeutic_class, ""),
                    DrugInformation.therapeutic_class,
                ),
                "pharmacologic_class": func.coalesce(
                    func.nullif(stmt.excluded.pharmacologic_class, ""),
                    DrugInformation.pharmacologic_class,
                ),

                # Clinical information fields - always update with new data
                "contraindications": stmt.excluded.contraindications,
                "warnings": stmt.excluded.warnings,
                "precautions": stmt.excluded.precautions,
                "adverse_reactions": stmt.excluded.adverse_reactions,
                "drug_interactions": stmt.excluded.drug_interactions,
                "indications_and_usage": func.coalesce(
                    func.nullif(stmt.excluded.indications_and_usage, ""),
                    DrugInformation.indications_and_usage,
                ),
                "dosage_and_administration": func.coalesce(
                    func.nullif(stmt.excluded.dosage_and_administration, ""),
                    DrugInformation.dosage_and_administration,
                ),
                "mechanism_of_action": func.coalesce(
                    func.nullif(stmt.excluded.mechanism_of_action, ""),
                    DrugInformation.mechanism_of_action,
                ),
                "pharmacokinetics": func.coalesce(
                    func.nullif(stmt.excluded.pharmacokinetics, ""),
                    DrugInformation.pharmacokinetics,
                ),
                "pharmacodynamics": func.coalesce(
                    func.nullif(stmt.excluded.pharmacodynamics, ""),
                    DrugInformation.pharmacodynamics,
                ),

                # Additional clinical fields - always update with new data if available
                "boxed_warning": func.coalesce(
                    func.nullif(stmt.excluded.boxed_warning, ""),
                    DrugInformation.boxed_warning,
                ),
                "clinical_studies": func.coalesce(
                    func.nullif(stmt.excluded.clinical_studies, ""),
                    DrugInformation.clinical_studies,
                ),
                "pediatric_use": func.coalesce(
                    func.nullif(stmt.excluded.pediatric_use, ""),
                    DrugInformation.pediatric_use,
                ),
                "geriatric_use": func.coalesce(
                    func.nullif(stmt.excluded.geriatric_use, ""),
                    DrugInformation.geriatric_use,
                ),
                "pregnancy": func.coalesce(
                    func.nullif(stmt.excluded.pregnancy, ""),
                    DrugInformation.pregnancy,
                ),
                "nursing_mothers": func.coalesce(
                    func.nullif(stmt.excluded.nursing_mothers, ""),
                    DrugInformation.nursing_mothers,
                ),
                "overdosage": func.coalesce(
                    func.nullif(stmt.excluded.overdosage, ""),
                    DrugInformation.overdosage,
                ),
                "nonclinical_toxicology": func.coalesce(
                    func.nullif(stmt.excluded.nonclinical_toxicology, ""),
                    DrugInformation.nonclinical_toxicology,
                ),

                # For arrays, combine unique values
                "ingredients": stmt.excluded.ingredients,
                "data_sources": stmt.excluded.data_sources,
            },
        )

        db.execute(stmt)

    async def update_search_vectors(self, db: Session) -> None:
        """Update full-text search vectors with deadlock retry logic"""
        import random
        import time

        from psycopg2.errors import DeadlockDetected

        max_retries = 5
        base_delay = 0.1

        for attempt in range(max_retries):
            try:
                # Use advisory lock to prevent concurrent updates
                db.execute(text("SELECT pg_advisory_lock(12348)"))

                update_query = text("""
                    UPDATE drug_information
                    SET search_vector = to_tsvector('english',
                        COALESCE(generic_name, '') || ' ' ||
                        COALESCE(array_to_string(brand_names, ' '), '') || ' ' ||
                        COALESCE(array_to_string(manufacturers, ' '), '') || ' ' ||
                        COALESCE(therapeutic_class, '') || ' ' ||
                        COALESCE(indications_and_usage, '')
                    )
                    WHERE search_vector IS NULL
                """)

                db.execute(update_query)
                db.commit()

                # Release advisory lock
                db.execute(text("SELECT pg_advisory_unlock(12348)"))

                logger.info("Updated search vectors for FDA drugs")
                return

            except DeadlockDetected:
                db.rollback()
                # Release lock on error
                with contextlib.suppress(builtins.BaseException):
                    db.execute(text("SELECT pg_advisory_unlock(12348)"))

                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 0.1)
                    logger.warning(f"Deadlock detected, retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                else:
                    logger.exception(f"Failed to update search vectors after {max_retries} attempts due to deadlocks")

            except Exception as e:
                db.rollback()
                # Release lock on error
                with contextlib.suppress(builtins.BaseException):
                    db.execute(text("SELECT pg_advisory_unlock(12348)"))
                logger.exception(f"Failed to update search vectors: {e}")
                break

    async def process_ddinter_interactions(self, ddinter_data_dir: str, db: Session) -> dict:
        """Process DDInter drug interactions and integrate into drugs table"""
        logger.info(f"Processing DDInter interactions from {ddinter_data_dir}")

        from pathlib import Path

        try:
            # Initialize DDInter parser
            parser = DDInterParser()
            data_path = Path(ddinter_data_dir)

            if not data_path.exists():
                logger.warning(f"DDInter data directory not found: {data_path}")
                return {"status": "skipped", "message": "Data directory not found"}

            # Parse DDInter CSV files
            parsed_data = parser.parse_and_validate(data_path)
            interactions = parsed_data.get("drug_interactions", [])

            if not interactions:
                logger.warning("No DDInter interactions found")
                return {"status": "completed", "interactions_processed": 0}

            logger.info(f"Processing {len(interactions)} DDInter interactions")

            # Group interactions by drug names
            drug_interactions = {}
            processed_count = 0

            for interaction in interactions:
                drug1 = interaction.get("drug_1", "").strip()
                drug2 = interaction.get("drug_2", "").strip()

                if not drug1 or not drug2:
                    continue

                # Add interaction to both drugs
                for drug_name in [drug1, drug2]:
                    drug_key = drug_name.upper()

                    if drug_key not in drug_interactions:
                        drug_interactions[drug_key] = {"ddinter": []}

                    # Create interaction record
                    interaction_record = {
                        "interacting_drug": drug2 if drug_name == drug1 else drug1,
                        "severity": interaction.get("severity"),
                        "interaction_type": interaction.get("interaction_type"),
                        "source": "DDInter",
                        "metadata": interaction.get("metadata", {}),
                    }

                    drug_interactions[drug_key]["ddinter"].append(interaction_record)

                processed_count += 1

            logger.info(f"Prepared interactions for {len(drug_interactions)} drugs")

            # Update drugs in database using direct psycopg2 cursor
            updated_count = 0
            import json as json_lib

            # Get raw psycopg2 connection from SQLAlchemy
            raw_connection = db.connection().connection
            cursor = raw_connection.cursor()

            for drug_name, interactions_data in drug_interactions.items():
                try:
                    interactions_json = json_lib.dumps(interactions_data)

                    # Use direct psycopg2 execution with proper parameter binding
                    sql = """
                        UPDATE drug_information
                        SET drug_interactions = COALESCE(drug_interactions, '{}'::jsonb) || %s::jsonb
                        WHERE UPPER(generic_name) = %s
                          OR %s = ANY(SELECT UPPER(unnest(brand_names)))
                    """

                    cursor.execute(sql, (interactions_json, drug_name, drug_name))

                    if cursor.rowcount > 0:
                        updated_count += cursor.rowcount
                        logger.debug(f"Updated {cursor.rowcount} records for {drug_name}")

                except Exception as e:
                    logger.warning(f"Error updating interactions for {drug_name}: {e}")
                    # Rollback this specific update but continue with others
                    raw_connection.rollback()
                    continue

            # Commit all successful changes
            try:
                raw_connection.commit()
            except Exception as e:
                logger.exception(f"Error committing DDInter updates: {e}")
                raw_connection.rollback()

            # Log update
            from datetime import datetime as dt
            update_log = UpdateLog(
                source="ddinter_interactions",
                update_type="full",
                status="success",
                records_processed=processed_count,
            )
            update_log.started_at = dt.utcnow()
            update_log.completed_at = dt.utcnow()
            db.add(update_log)

            logger.info(f"✅ DDInter processing completed: {processed_count} interactions processed, {updated_count} drugs updated")

            return {
                "status": "completed",
                "interactions_processed": processed_count,
                "drugs_updated": updated_count,
                "parser_stats": parser.get_stats(),
            }

        except Exception as e:
            logger.exception(f"Error processing DDInter interactions: {e}")
            db.rollback()
            raise

    async def initialize_data(self) -> dict:
        """Initialize FDA data"""
        logger.info("Initializing FDA data")

        db = self.session_factory()
        try:
            # Check if data already exists
            count = db.query(func.count(DrugInformation.ndc)).scalar()
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

    async def process_existing_files(self, force: bool = False) -> dict[str, Any]:
        """Process existing FDA files without downloading new data"""
        logger.info("Processing existing FDA files")

        db = self.session_factory()
        try:
            # Check if we should skip if data exists (unless forced)
            if not force:
                count = db.query(func.count(DrugInformation.id)).scalar()
                if count > 10000:  # Only skip if we have substantial data
                    logger.info(f"FDA data already exists: {count} drugs (use force=True to reprocess)")
                    return {"status": "already_processed", "drug_count": count}

            # Find existing files using downloader
            if not self.downloader:
                raise ValueError("FDA downloader not available. Initialize with enable_downloader=True.")

            existing_files = self.downloader.get_existing_files()
            if not existing_files:
                logger.warning("No existing FDA files found")
                return {"status": "no_files_found", "drug_count": 0}

            logger.info(f"Found {len(existing_files)} existing FDA datasets to process")

            total_processed = 0

            # Process each existing dataset
            for dataset_name, data_dir in existing_files.items():
                logger.info(f"Processing existing {dataset_name} data from {data_dir}")
                processed = await self.process_fda_dataset(dataset_name, data_dir, db)
                total_processed += processed
                logger.info(f"Processed {processed} drugs from existing {dataset_name}")

            logger.info(f"Existing FDA files processing completed: {total_processed} drugs processed")

            # Process enhanced drug sources after FDA processing
            enhanced_stats = await self.process_enhanced_drug_sources(db)

            return {
                "status": "completed",
                "records_processed": total_processed,
                "datasets_processed": len(existing_files),
                "existing_files": list(existing_files.keys()),
                "enhanced_sources": enhanced_stats,
            }

        except Exception as e:
            logger.exception(f"Existing FDA files processing failed: {e}")
            raise
        finally:
            db.close()

    async def process_enhanced_drug_sources(self, db: Session) -> dict[str, Any]:
        """Process enhanced drug sources to enrich FDA data"""
        logger.info("🧬 Processing enhanced drug sources to enrich clinical data")

        stats = {
            "dailymed": {"processed": 0, "drugs_updated": 0},
            "drugcentral": {"processed": 0, "drugs_updated": 0},
            "rxclass": {"processed": 0, "drugs_updated": 0},
        }

        try:
            # Process DailyMed XML files
            dailymed_dir = "/app/data/enhanced_drug_data/dailymed"
            if os.path.exists(dailymed_dir):
                logger.info("📋 Processing DailyMed XML files...")
                dailymed_stats = await self._process_dailymed_data(dailymed_dir, db)
                stats["dailymed"] = dailymed_stats

            # Process DrugCentral JSON files
            drugcentral_dir = "/app/data/enhanced_drug_data/drugcentral"
            if os.path.exists(drugcentral_dir):
                logger.info("🎯 Processing DrugCentral mechanism/pharmacology data...")
                drugcentral_stats = await self._process_drugcentral_data(drugcentral_dir, db)
                stats["drugcentral"] = drugcentral_stats

            # Process RxClass JSON files
            rxclass_dir = "/app/data/enhanced_drug_data/rxclass"
            if os.path.exists(rxclass_dir):
                logger.info("🏷️ Processing RxClass therapeutic classifications...")
                rxclass_stats = await self._process_rxclass_data(rxclass_dir, db)
                stats["rxclass"] = rxclass_stats

            total_updated = sum(s["drugs_updated"] for s in stats.values())
            logger.info(f"✅ Enhanced sources processing completed: {total_updated} drugs enriched")

            return stats

        except Exception as e:
            logger.exception(f"Enhanced drug sources processing failed: {e}")
            return stats

    async def _process_dailymed_data(self, dailymed_dir: str, db: Session) -> dict[str, int]:
        """Process DailyMed XML files to extract clinical information"""
        parser = DailyMedParser()
        matcher = DrugNameMatcher()

        try:
            # Parse all DailyMed XML files
            dailymed_drugs = parser.parse_directory(dailymed_dir)

            # Get all database drug names for matching
            db_drugs = db.query(DrugInformation.generic_name).all()
            db_names = [drug.generic_name for drug in db_drugs]

            drugs_updated = 0

            # Update database with DailyMed clinical information
            for drug_data in dailymed_drugs:
                generic_name = drug_data.get("generic_name", "").strip()
                brand_name = drug_data.get("brand_name", "").strip()

                if not generic_name and not brand_name:
                    continue

                drug_record = None

                # Try fuzzy matching on generic name first
                if generic_name:
                    match_result = matcher.find_best_match(generic_name, db_names, threshold=0.7)
                    if match_result:
                        matched_name, score = match_result
                        drug_record = db.query(DrugInformation).filter(
                            DrugInformation.generic_name == matched_name,
                        ).first()

                # If no match, try exact brand name search
                if not drug_record and brand_name:
                    drug_record = db.query(DrugInformation).filter(
                        DrugInformation.brand_names.op("@>")(cast([brand_name], ARRAY(Text))),
                    ).first()

                if drug_record:
                    # Update clinical fields with DailyMed data (only if empty or shorter)
                    updated_fields = []

                    clinical_fields = [
                        "indications_and_usage", "contraindications", "warnings",
                        "precautions", "adverse_reactions", "drug_interactions",
                        "dosage_and_administration", "mechanism_of_action",
                        "pharmacokinetics", "pharmacodynamics", "boxed_warning",
                        "clinical_studies", "pediatric_use", "geriatric_use",
                        "pregnancy", "nursing_mothers", "overdosage", "nonclinical_toxicology",
                    ]

                    for field in clinical_fields:
                        new_value = drug_data.get(field)
                        if new_value:
                            current_value = getattr(drug_record, field, "")

                            # Update if current is empty or new value is significantly longer
                            if not current_value or (isinstance(new_value, str) and len(new_value) > len(str(current_value)) * 1.5):
                                if isinstance(new_value, list):
                                    setattr(drug_record, field, new_value)
                                else:
                                    setattr(drug_record, field, new_value)
                                updated_fields.append(field)

                    if updated_fields:
                        # Update data sources
                        current_sources = set(drug_record.data_sources or [])
                        current_sources.add("dailymed")
                        drug_record.data_sources = list(current_sources)

                        drugs_updated += 1
                        logger.debug(f"Updated {generic_name or brand_name} with DailyMed data: {updated_fields}")

            db.commit()
            logger.info(f"✅ DailyMed processing completed: {drugs_updated} drugs updated from {len(dailymed_drugs)} XML files")

            return {"processed": len(dailymed_drugs), "drugs_updated": drugs_updated}

        except Exception as e:
            logger.exception(f"Failed to process DailyMed data: {e}")
            db.rollback()
            return {"processed": 0, "drugs_updated": 0}

    async def _process_drugcentral_data(self, drugcentral_dir: str, db: Session) -> dict[str, int]:
        """Process DrugCentral JSON files to extract mechanism/pharmacology data"""
        parser = DrugCentralParser()
        matcher = DrugNameMatcher()

        try:
            # Parse all DrugCentral data
            drugcentral_data = parser.parse_drugcentral_directory(drugcentral_dir)

            # Get all database drug names for matching (optimized)
            db_drugs_query = db.query(DrugInformation.generic_name).all()
            db_names = [drug.generic_name for drug in db_drugs_query]

            # Create lookup map using optimized fuzzy matching
            source_names = list(drugcentral_data.keys())
            logger.info(f"DrugCentral: Starting fuzzy matching for {len(source_names)} source drugs against {len(db_names)} database drugs")

            # Use lower threshold and limit candidates for performance
            lookup_map = matcher.create_lookup_map(source_names, db_names, threshold=0.8)

            logger.info(f"DrugCentral: Created lookup map for {len(lookup_map)}/{len(source_names)} drugs")

            drugs_updated = 0

            # Update database with DrugCentral information
            for drug_key, drug_info in drugcentral_data.items():
                # Find matching drug using fuzzy matching
                matched_name = lookup_map.get(drug_key)
                if not matched_name:
                    continue

                drug_record = db.query(DrugInformation).filter(
                    DrugInformation.generic_name == matched_name,
                ).first()

                if drug_record:
                    updated_fields = []

                    # Update mechanism of action
                    if drug_info.get("mechanism_of_action"):
                        current_moa = drug_record.mechanism_of_action or ""
                        new_moa = drug_info["mechanism_of_action"]

                        if not current_moa or len(new_moa) > len(current_moa) * 1.2:
                            drug_record.mechanism_of_action = new_moa
                            updated_fields.append("mechanism_of_action")

                    # Update pharmacokinetics
                    if drug_info.get("pharmacokinetics"):
                        current_pk = drug_record.pharmacokinetics or ""
                        new_pk = drug_info["pharmacokinetics"]

                        if not current_pk or len(new_pk) > len(current_pk) * 1.2:
                            drug_record.pharmacokinetics = new_pk
                            updated_fields.append("pharmacokinetics")

                    # Update pharmacodynamics
                    if drug_info.get("pharmacodynamics"):
                        current_pd = drug_record.pharmacodynamics or ""
                        new_pd = drug_info["pharmacodynamics"]

                        if not current_pd or len(new_pd) > len(current_pd) * 1.2:
                            drug_record.pharmacodynamics = new_pd
                            updated_fields.append("pharmacodynamics")

                    if updated_fields:
                        # Update data sources
                        current_sources = set(drug_record.data_sources or [])
                        current_sources.add("drugcentral")
                        drug_record.data_sources = list(current_sources)

                        drugs_updated += 1
                        logger.debug(f"Updated {drug_record.generic_name} with DrugCentral data: {updated_fields}")

            db.commit()
            logger.info(f"✅ DrugCentral processing completed: {drugs_updated} drugs updated from {len(drugcentral_data)} records")

            return {"processed": len(drugcentral_data), "drugs_updated": drugs_updated}

        except Exception as e:
            logger.exception(f"Failed to process DrugCentral data: {e}")
            db.rollback()
            return {"processed": 0, "drugs_updated": 0}

    async def _process_rxclass_data(self, rxclass_dir: str, db: Session) -> dict[str, int]:
        """Process RxClass JSON files to extract therapeutic classifications"""
        parser = RxClassParser()
        matcher = DrugNameMatcher()

        try:
            # Parse all RxClass data
            rxclass_data = parser.parse_rxclass_directory(rxclass_dir)

            # Get all database drug names for matching
            db_drugs = db.query(DrugInformation.generic_name).all()
            db_names = [drug.generic_name for drug in db_drugs]

            # Create lookup map using fuzzy matching
            source_names = list(rxclass_data.keys())
            lookup_map = matcher.create_lookup_map(source_names, db_names, threshold=0.7)

            logger.info(f"RxClass: Created lookup map for {len(lookup_map)}/{len(source_names)} drugs")

            drugs_updated = 0

            # Update database with RxClass therapeutic classifications
            for drug_key, therapeutic_classes in rxclass_data.items():
                # Find matching drug using fuzzy matching
                matched_name = lookup_map.get(drug_key)
                if not matched_name:
                    continue

                drug_record = db.query(DrugInformation).filter(
                    DrugInformation.generic_name == matched_name,
                ).first()

                if drug_record:
                    # Get primary therapeutic class
                    primary_class = parser.extract_primary_therapeutic_class(therapeutic_classes)

                    if primary_class:
                        current_class = drug_record.therapeutic_class or ""

                        # Update if current is empty or new class is more specific
                        if not current_class or len(primary_class) > len(current_class):
                            drug_record.therapeutic_class = primary_class

                            # Update data sources
                            current_sources = set(drug_record.data_sources or [])
                            current_sources.add("rxclass")
                            drug_record.data_sources = list(current_sources)

                            drugs_updated += 1
                            logger.debug(f"Updated {drug_record.generic_name} with RxClass therapeutic class: {primary_class}")

            db.commit()
            logger.info(f"✅ RxClass processing completed: {drugs_updated} drugs updated from {len(rxclass_data)} records")

            return {"processed": len(rxclass_data), "drugs_updated": drugs_updated}

        except Exception as e:
            logger.exception(f"Failed to process RxClass data: {e}")
            db.rollback()
            return {"processed": 0, "drugs_updated": 0}


