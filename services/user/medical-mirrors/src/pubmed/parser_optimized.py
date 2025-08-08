"""
Optimized multi-core PubMed parser
Utilizes all available CPU cores for XML parsing and database operations
"""

import asyncio
import gzip
import logging
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from typing import Any
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)


def parse_xml_file_worker(xml_file_path: str) -> "tuple[str, list[dict]]":
    """Worker function for multiprocessing XML parsing"""
    try:
        logger.info(f"Worker parsing: {xml_file_path}")
        articles = []

        if xml_file_path.endswith(".gz"):
            with gzip.open(xml_file_path, "rt", encoding="utf-8") as f:
                tree = ET.parse(f)
        else:
            tree = ET.parse(xml_file_path)

        root = tree.getroot()

        # Find all PubmedArticle elements
        for article_elem in root.findall(".//PubmedArticle"):
            article_data = parse_article_element(article_elem)
            if article_data:
                articles.append(article_data)

        logger.info(f"Worker parsed {len(articles)} articles from {xml_file_path}")
        return xml_file_path, articles

    except Exception as e:
        logger.exception(f"Worker failed to parse {xml_file_path}: {e}")
        return xml_file_path, []


def parse_article_element(article_elem: ET.Element) -> dict[str, Any] | None:
    """Parse a single PubmedArticle element (pure function for multiprocessing)"""
    try:
        # Get PMID
        pmid_elem = article_elem.find(".//PMID")
        if pmid_elem is None:
            return None
        pmid = pmid_elem.text

        # Get article title
        title_elem = article_elem.find(".//ArticleTitle")
        title = title_elem.text if title_elem is not None else ""

        # Get abstract
        abstract_elems = article_elem.findall(".//AbstractText")
        abstract_parts = []
        for abs_elem in abstract_elems:
            if abs_elem.text:
                label = abs_elem.get("Label", "")
                text = abs_elem.text
                if label:
                    abstract_parts.append(f"{label}: {text}")
                else:
                    abstract_parts.append(text)
        abstract = " ".join(abstract_parts)

        # Get authors
        authors = []
        author_elems = article_elem.findall(".//Author")
        for author_elem in author_elems:
            last_name = author_elem.find("LastName")
            first_name = author_elem.find("ForeName")
            if last_name is not None and first_name is not None:
                authors.append(f"{first_name.text} {last_name.text}")
            elif last_name is not None and last_name.text is not None:
                authors.append(last_name.text)

        # Get journal
        journal_elem = article_elem.find(".//Journal/Title")
        journal = journal_elem.text if journal_elem is not None else ""

        # Get publication date
        pub_date = extract_pub_date(article_elem)

        # Get DOI
        doi = extract_doi(article_elem)

        # Get MeSH terms
        mesh_terms = extract_mesh_terms(article_elem)

        return {
            "pmid": pmid,
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "journal": journal,
            "pub_date": pub_date,
            "doi": doi,
            "mesh_terms": mesh_terms,
        }

    except Exception as e:
        logger.exception(f"Failed to parse article element: {e}")
        return None


def extract_pub_date(article_elem: ET.Element) -> str:
    """Extract publication date from article element"""
    try:
        # Try PubDate first
        pub_date_elem = article_elem.find(".//PubDate")
        if pub_date_elem is not None:
            year_elem = pub_date_elem.find("Year")
            month_elem = pub_date_elem.find("Month")
            day_elem = pub_date_elem.find("Day")

            if year_elem is not None:
                year = year_elem.text
                month = month_elem.text if month_elem is not None else "01"
                day = day_elem.text if day_elem is not None else "01"

                # Convert month name to number if needed
                month_map = {
                    "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
                    "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
                    "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12",
                }
                if month in month_map:
                    month = month_map[month]

                return f"{year}-{month:0>2}-{day:0>2}"

        return ""
    except Exception:
        return ""


def extract_doi(article_elem: ET.Element) -> str:
    """Extract DOI from article element"""
    try:
        doi_elems = article_elem.findall(".//ArticleId[@IdType='doi']")
        if doi_elems:
            return doi_elems[0].text or ""
        return ""
    except Exception:
        return ""


def extract_mesh_terms(article_elem: ET.Element) -> list[str]:
    """Extract MeSH terms from article element"""
    try:
        mesh_terms = []
        mesh_elems = article_elem.findall(".//MeshHeading/DescriptorName")
        for mesh_elem in mesh_elems:
            if mesh_elem.text:
                mesh_terms.append(mesh_elem.text)
        return mesh_terms
    except Exception:
        return []


class OptimizedPubMedParser:
    """Multi-core optimized PubMed XML parser"""

    def __init__(self, max_workers: int | None = None):
        # Use half of available CPU cores by default to leave resources for other processes
        if max_workers is None:
            max_workers = max(1, mp.cpu_count() // 2)
        self.max_workers = max_workers
        logger.info(f"Initialized PubMed parser with {self.max_workers} workers (CPU cores: {mp.cpu_count()})")

    async def parse_xml_files_parallel(self, xml_files: list[str]) -> dict[str, list[dict[str, Any]]]:
        """Parse multiple XML files in parallel using all CPU cores"""
        logger.info(f"Parsing {len(xml_files)} XML files using {self.max_workers} cores")

        # Use ProcessPoolExecutor for CPU-intensive XML parsing
        loop = asyncio.get_event_loop()

        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all parsing tasks
            tasks = []
            for xml_file in xml_files:
                task = loop.run_in_executor(executor, parse_xml_file_worker, xml_file)
                tasks.append(task)

            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        parsed_files = {}
        total_articles = 0

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Parsing task failed: {result}")
                continue

            if not isinstance(result, tuple) or len(result) != 2:
                logger.error(f"Invalid result format: {result}")
                continue

            xml_file, articles = result
            parsed_files[xml_file] = articles
            total_articles += len(articles)

        logger.info(f"Parallel parsing completed: {total_articles} total articles from {len(parsed_files)} files")
        return parsed_files

    def parse_xml_file(self, xml_file_path: str) -> list[dict]:
        """Single file parsing (backward compatibility)"""
        _, articles = parse_xml_file_worker(xml_file_path)
        return articles
