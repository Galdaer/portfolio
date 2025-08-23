"""
PubMed API for local mirror
Provides search functionality matching Healthcare MCP interface
"""

import logging
from datetime import datetime
from typing import Any

from pubmed.downloader import PubMedDownloader
from pubmed.parser import PubMedParser
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from database import PubMedArticle, UpdateLog

logger = logging.getLogger(__name__)


class PubMedAPI:
    """Local PubMed API matching Healthcare MCP interface"""

    def __init__(self, session_factory: Any) -> None:
        self.session_factory = session_factory
        self.downloader = PubMedDownloader()
        self.parser = PubMedParser()

    async def search_articles(self, query: str, max_results: int = 10) -> list[dict[str, Any]]:
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

    async def get_status(self) -> dict:
        """Get status of PubMed mirror"""
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

            return {
                "source": "pubmed",
                "total_articles": total_count,
                "status": "healthy" if total_count > 0 else "empty",
                "last_update": last_update.started_at.isoformat() if last_update else None,
                "last_update_status": last_update.status if last_update else None,
            }

        finally:
            db.close()

    async def trigger_update(
        self, quick_test: bool = False, max_files: int | None = None
    ) -> dict[str, Any]:
        """Trigger PubMed data update"""
        if quick_test:
            logger.info(f"Triggering PubMed QUICK TEST update (max_files={max_files or 3})")
        else:
            logger.info("Triggering PubMed data update")

        db = self.session_factory()
        try:
            # Log update start
            update_log = UpdateLog(
                source="pubmed",
                update_type="incremental",
                status="in_progress",
                started_at=datetime.utcnow(),
            )
            db.add(update_log)
            db.commit()

            # Download and parse updates
            update_files = await self.downloader.download_updates()

            # Limit files for quick testing
            if quick_test:
                max_files_to_process = max_files or 3
                update_files = update_files[:max_files_to_process]
                logger.info(f"Quick test mode: processing only {len(update_files)} files")

            total_processed = 0

            for xml_file in update_files:
                articles = self.parser.parse_xml_file(xml_file)
                processed = await self.store_articles(articles, db)
                total_processed += processed

            # Update log
            update_log.status = "success"  # type: ignore[assignment]
            update_log.records_processed = total_processed  # type: ignore[assignment]
            update_log.completed_at = datetime.utcnow()  # type: ignore[assignment]
            db.commit()

            logger.info(f"PubMed update completed: {total_processed} articles processed")
            return {
                "status": "success",
                "records_processed": total_processed,
                "files_processed": len(update_files),
            }

        except Exception as e:
            logger.exception(f"PubMed update failed: {e}")
            update_log.status = "failed"  # type: ignore[assignment]
            update_log.error_message = str(e)  # type: ignore[assignment]
            update_log.completed_at = datetime.utcnow()  # type: ignore[assignment]
            db.commit()
            raise
        finally:
            db.close()

    async def store_articles(self, articles: list[dict], db: Session) -> int:
        """Store articles in database using proper UPSERT"""
        stored_count = 0

        for article_data in articles:
            try:
                # Use PostgreSQL UPSERT (INSERT ... ON CONFLICT DO UPDATE)
                from sqlalchemy.dialects.postgresql import insert

                stmt = insert(PubMedArticle).values(**article_data)
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

                db.execute(stmt)
                stored_count += 1

                # Commit in batches
                if stored_count % 100 == 0:
                    db.commit()

            except Exception as e:
                logger.exception(f"Failed to store article {article_data.get('pmid')}: {e}")
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
            logger.info("Updated search vectors for PubMed articles")

        except Exception as e:
            logger.exception(f"Failed to update search vectors: {e}")
            db.rollback()

    async def initialize_data(self) -> dict:
        """Initialize PubMed data from baseline files"""
        logger.info("Initializing PubMed data from baseline")

        db = self.session_factory()
        try:
            # Check if data already exists
            count = db.query(func.count(PubMedArticle.pmid)).scalar()
            if count > 0:
                logger.info(f"PubMed data already exists: {count} articles")
                return {"status": "already_initialized", "article_count": count}

            # Download baseline files
            baseline_files = await self.downloader.download_baseline()
            total_processed = 0

            for xml_file in baseline_files:
                articles = self.parser.parse_xml_file(xml_file)
                processed = await self.store_articles(articles, db)
                total_processed += processed
                logger.info(f"Processed {processed} articles from {xml_file}")

            logger.info(f"PubMed initialization completed: {total_processed} articles")
            return {
                "status": "initialized",
                "records_processed": total_processed,
                "files_processed": len(baseline_files),
            }

        except Exception as e:
            logger.exception(f"PubMed initialization failed: {e}")
            raise
        finally:
            db.close()
