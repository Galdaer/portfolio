"""
Optimized PubMed API with multi-core processing and bulk database operations
Provides significant performance improvements for large medical datasets
"""

import logging
from datetime import datetime
from typing import Any

from pubmed.downloader import PubMedDownloader
from pubmed.parser_optimized import OptimizedPubMedParser
from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from database import PubMedArticle, UpdateLog

logger = logging.getLogger(__name__)


class OptimizedPubMedAPI:
    """Multi-core optimized PubMed API for high-performance medical data processing"""

    def __init__(self, session_factory: Any, max_workers: int | None = None) -> None:
        self.session_factory = session_factory
        self.downloader = PubMedDownloader()
        self.parser = OptimizedPubMedParser(max_workers=max_workers)

    async def search_articles(self, query: str, max_results: int = 10) -> list[dict]:
        """
        Search PubMed articles in local database
        Matches the interface of Healthcare MCP search-pubmed tool
        """
        logger.info(f"Searching PubMed for: {query}, max_results: {max_results}")

        db = self.session_factory()
        try:
            # Use PostgreSQL full-text search
            search_query = text("""
                SELECT pmid, title, abstract, authors, journal, pub_date, doi, mesh_terms,
                       ts_rank(search_vector, plainto_tsquery(:query)) as rank
                FROM pubmed_articles
                WHERE search_vector @@ plainto_tsquery(:query)
                ORDER BY rank DESC, pub_date DESC
                LIMIT :limit
            """)

            result = db.execute(search_query, {"query": query, "limit": max_results})

            articles = []
            for row in result:
                article = {
                    "pmid": row.pmid,
                    "title": row.title,
                    "abstract": row.abstract or "",
                    "authors": row.authors or [],
                    "journal": row.journal or "",
                    "pubDate": row.pub_date or "",
                    "doi": row.doi or "",
                    "meshTerms": row.mesh_terms or [],
                }
                articles.append(article)

            logger.info(f"Found {len(articles)} articles for query: {query}")
            return articles

        except Exception as e:
            logger.exception(f"PubMed search failed: {e}")
            raise
        finally:
            db.close()

    async def update_recent_articles(self, quick_test: bool = False, max_files: int | None = None) -> dict:
        """
        Multi-core optimized update of recent PubMed articles
        Uses all available CPU cores for XML parsing and bulk database operations
        """
        logger.info(f"Starting optimized PubMed update (quick_test={quick_test}, max_files={max_files})")

        db = self.session_factory()
        update_log = UpdateLog(
            source="pubmed",
            update_type="recent",
            started_at=datetime.utcnow(),
            status="running",
        )
        db.add(update_log)
        db.commit()

        try:
            # Download update files
            logger.info("Downloading PubMed update files...")
            update_files = await self.downloader.download_updates()

            # Limit files for quick testing
            if quick_test:
                max_files_to_process = max_files or 3
                update_files = update_files[:max_files_to_process]
                logger.info(f"Quick test mode: processing only {len(update_files)} files")

            if not update_files:
                logger.info("No update files to process")
                return {"status": "success", "records_processed": 0, "files_processed": 0}

            # PARALLEL XML PARSING - This is where the magic happens!
            logger.info(f"Starting parallel parsing of {len(update_files)} files...")
            parsed_files = await self.parser.parse_xml_files_parallel(update_files)

            # BULK DATABASE OPERATIONS
            total_processed = 0
            all_articles = []

            # Collect all articles from all files
            for xml_file, articles in parsed_files.items():
                all_articles.extend(articles)
                logger.info(f"Collected {len(articles)} articles from {xml_file}")

            # CRITICAL: Remove duplicates by PMID to prevent database constraint violations
            if all_articles:
                logger.info(f"Deduplicating {len(all_articles)} articles by PMID...")
                unique_articles = {}
                for article in all_articles:
                    pmid = article.get("pmid")
                    if pmid:
                        # Keep the most recent version if we see the same PMID multiple times
                        unique_articles[pmid] = article

                deduplicated_articles = list(unique_articles.values())
                duplicate_count = len(all_articles) - len(deduplicated_articles)

                if duplicate_count > 0:
                    logger.info(f"Removed {duplicate_count} duplicate PMIDs, processing {len(deduplicated_articles)} unique articles")

                # Bulk store deduplicated articles
                logger.info(f"Bulk storing {len(deduplicated_articles)} unique articles...")
                processed = await self.bulk_store_articles(deduplicated_articles, db)
                total_processed = processed

                # Single bulk search vector update
                logger.info("Updating search vectors in bulk...")
                await self.bulk_update_search_vectors(db)

            # Update log
            update_log.status = "success"
            update_log.records_processed = total_processed
            update_log.completed_at = datetime.utcnow()
            db.merge(update_log)
            db.commit()

            logger.info(f"Optimized PubMed update completed: {total_processed} articles processed")
            return {
                "status": "success",
                "records_processed": total_processed,
                "files_processed": len(update_files),
                "optimization": "multi-core parallel processing",
            }
        except Exception as e:
            logger.exception(f"Optimized PubMed update failed: {e}")
            update_log.status = "failed"
            update_log.error_message = str(e)
            update_log.completed_at = datetime.utcnow()
            db.merge(update_log)
            db.commit()
            raise
            raise
        finally:
            db.close()

    async def bulk_store_articles(self, articles: list[dict[str, Any]], db: Session) -> int:
        """
        Bulk store articles using PostgreSQL UPSERT for maximum performance
        Much faster than individual INSERT operations
        """
        logger.info(f"Bulk storing {len(articles)} articles...")

        if not articles:
            return 0

        try:
            # Prepare bulk UPSERT statement
            stmt = insert(PubMedArticle)
            stmt = stmt.on_conflict_do_update(
                index_elements=["pmid"],
                set_={
                    "title": stmt.excluded.title,
                    "abstract": stmt.excluded.abstract,
                    "authors": stmt.excluded.authors,
                    "journal": stmt.excluded.journal,
                    "pub_date": stmt.excluded.pub_date,
                    "doi": stmt.excluded.doi,
                    "mesh_terms": stmt.excluded.mesh_terms,
                    "updated_at": stmt.excluded.updated_at,
                },
            )

            # Process in batches for memory efficiency
            batch_size = 1000
            stored_count = 0

            for i in range(0, len(articles), batch_size):
                batch = articles[i:i + batch_size]

                # Execute bulk insert for this batch
                db.execute(stmt, batch)
                stored_count += len(batch)

                # Commit batch
                db.commit()

                if stored_count % 5000 == 0:
                    logger.info(f"Bulk stored {stored_count}/{len(articles)} articles...")

            logger.info(f"Bulk storage completed: {stored_count} articles stored")
            return stored_count

        except Exception as e:
            logger.exception(f"Bulk storage failed: {e}")
            db.rollback()
            raise

    async def bulk_update_search_vectors(self, db: Session) -> None:
        """
        Bulk update search vectors for all new articles
        Much more efficient than updating after each file
        """
        logger.info("Starting bulk search vector update...")

        try:
            # Update search vectors for articles that don't have them
            update_query = text("""
                UPDATE pubmed_articles
                SET search_vector = to_tsvector('english',
                    COALESCE(title, '') || ' ' ||
                    COALESCE(abstract, '') || ' ' ||
                    COALESCE(array_to_string(authors, ' '), '') || ' ' ||
                    COALESCE(array_to_string(mesh_terms, ' '), '')
                )
                WHERE search_vector IS NULL
            """)

            db.execute(update_query)
            db.commit()

            logger.info("Bulk search vector update completed")

        except Exception as e:
            logger.exception(f"Bulk search vector update failed: {e}")
            db.rollback()
            raise

    async def get_status(self) -> dict:
        """Get status of optimized PubMed mirror"""
        db = self.session_factory()
        try:
            # Get total article count
            total_count = db.query(func.count(PubMedArticle.pmid)).scalar()

            # Get last update info
            last_update = (
                db.query(UpdateLog)
                .filter(UpdateLog.source == "pubmed")
                .order_by(UpdateLog.started_at.desc())
                .first()
            )

            last_update_info = None
            if last_update:
                last_update_info = {
                    "timestamp": last_update.started_at.isoformat(),
                    "status": last_update.status,
                    "records_processed": last_update.records_processed,
                }

            return {
                "source": "pubmed",
                "status": "active",
                "total_articles": total_count,
                "last_update": last_update_info,
                "optimization": "multi-core parallel processing enabled",
            }

        finally:
            db.close()

    # Keep backward compatibility methods
    async def trigger_update(self, quick_test: bool = False, max_files: int | None = None) -> dict:
        """Compatibility method - calls optimized update_recent_articles"""
        return await self.update_recent_articles(quick_test=quick_test, max_files=max_files)

    async def get_article(self, pmid: str) -> dict | None:
        """Get specific article by PMID"""
        db = self.session_factory()
        try:
            article = db.query(PubMedArticle).filter(PubMedArticle.pmid == pmid).first()
            if not article:
                return None

            return {
                "pmid": article.pmid,
                "title": article.title,
                "abstract": article.abstract or "",
                "authors": article.authors or [],
                "journal": article.journal or "",
                "pubDate": article.pub_date or "",
                "doi": article.doi or "",
                "meshTerms": article.mesh_terms or [],
            }

        finally:
            db.close()
