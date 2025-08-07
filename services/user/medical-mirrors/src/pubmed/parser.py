"""
PubMed XML parser
Parses PubMed XML files and extracts article information
"""

import xml.etree.ElementTree as ET
import logging
from typing import List, Dict, Optional
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class PubMedParser:
    """Parses PubMed XML files and extracts article data"""
    
    def __init__(self):
        pass
    
    def parse_xml_file(self, xml_file_path: str) -> List[Dict]:
        """Parse a PubMed XML file and extract articles"""
        logger.info(f"Parsing PubMed XML file: {xml_file_path}")
        articles = []
        
        try:
            tree = ET.parse(xml_file_path)
            root = tree.getroot()
            
            # Find all PubmedArticle elements
            for article_elem in root.findall('.//PubmedArticle'):
                article_data = self.parse_article(article_elem)
                if article_data:
                    articles.append(article_data)
            
            logger.info(f"Parsed {len(articles)} articles from {xml_file_path}")
            return articles
            
        except Exception as e:
            logger.error(f"Failed to parse {xml_file_path}: {e}")
            return []
    
    def parse_article(self, article_elem) -> Optional[Dict]:
        """Parse a single PubmedArticle element"""
        try:
            # Get PMID
            pmid_elem = article_elem.find('.//PMID')
            if pmid_elem is None:
                return None
            pmid = pmid_elem.text
            
            # Get article title
            title_elem = article_elem.find('.//ArticleTitle')
            title = title_elem.text if title_elem is not None else ""
            
            # Get abstract
            abstract_elems = article_elem.findall('.//AbstractText')
            abstract_parts = []
            for abs_elem in abstract_elems:
                if abs_elem.text:
                    label = abs_elem.get('Label', '')
                    text = abs_elem.text
                    if label:
                        abstract_parts.append(f"{label}: {text}")
                    else:
                        abstract_parts.append(text)
            abstract = " ".join(abstract_parts)
            
            # Get authors
            authors = []
            author_elems = article_elem.findall('.//Author')
            for author_elem in author_elems:
                last_name = author_elem.find('LastName')
                first_name = author_elem.find('ForeName')
                if last_name is not None and first_name is not None:
                    authors.append(f"{first_name.text} {last_name.text}")
                elif last_name is not None:
                    authors.append(last_name.text)
            
            # Get journal
            journal_elem = article_elem.find('.//Journal/Title')
            journal = journal_elem.text if journal_elem is not None else ""
            
            # Get publication date
            pub_date = self.extract_pub_date(article_elem)
            
            # Get DOI
            doi = self.extract_doi(article_elem)
            
            # Get MeSH terms
            mesh_terms = self.extract_mesh_terms(article_elem)
            
            return {
                'pmid': pmid,
                'title': title,
                'abstract': abstract,
                'authors': authors,
                'journal': journal,
                'pub_date': pub_date,
                'doi': doi,
                'mesh_terms': mesh_terms
            }
            
        except Exception as e:
            logger.error(f"Failed to parse article: {e}")
            return None
    
    def extract_pub_date(self, article_elem) -> str:
        """Extract publication date from article"""
        try:
            # Try PubDate first
            pub_date_elem = article_elem.find('.//PubDate')
            if pub_date_elem is not None:
                year_elem = pub_date_elem.find('Year')
                month_elem = pub_date_elem.find('Month')
                day_elem = pub_date_elem.find('Day')
                
                year = year_elem.text if year_elem is not None else ""
                month = month_elem.text if month_elem is not None else ""
                day = day_elem.text if day_elem is not None else ""
                
                if year:
                    date_parts = [year]
                    if month:
                        date_parts.append(month)
                        if day:
                            date_parts.append(day)
                    return "-".join(date_parts)
            
            # Fallback to ArticleDate
            article_date_elem = article_elem.find('.//ArticleDate')
            if article_date_elem is not None:
                year_elem = article_date_elem.find('Year')
                month_elem = article_date_elem.find('Month')
                day_elem = article_date_elem.find('Day')
                
                year = year_elem.text if year_elem is not None else ""
                month = month_elem.text if month_elem is not None else ""
                day = day_elem.text if day_elem is not None else ""
                
                if year:
                    return f"{year}-{month}-{day}"
            
            return ""
            
        except Exception as e:
            logger.error(f"Failed to extract publication date: {e}")
            return ""
    
    def extract_doi(self, article_elem) -> str:
        """Extract DOI from article"""
        try:
            # Look for DOI in ArticleId elements
            article_ids = article_elem.findall('.//ArticleId')
            for aid_elem in article_ids:
                if aid_elem.get('IdType') == 'doi':
                    return aid_elem.text or ""
            
            # Look for DOI in ELocationID
            elocation_elems = article_elem.findall('.//ELocationID')
            for eloc_elem in elocation_elems:
                if eloc_elem.get('EIdType') == 'doi':
                    return eloc_elem.text or ""
            
            return ""
            
        except Exception as e:
            logger.error(f"Failed to extract DOI: {e}")
            return ""
    
    def extract_mesh_terms(self, article_elem) -> List[str]:
        """Extract MeSH terms from article"""
        try:
            mesh_terms = []
            
            # Get MeSH headings
            mesh_elems = article_elem.findall('.//MeshHeading/DescriptorName')
            for mesh_elem in mesh_elems:
                if mesh_elem.text:
                    mesh_terms.append(mesh_elem.text)
            
            # Get keywords as additional terms
            keyword_elems = article_elem.findall('.//Keyword')
            for keyword_elem in keyword_elems:
                if keyword_elem.text:
                    mesh_terms.append(keyword_elem.text)
            
            return mesh_terms
            
        except Exception as e:
            logger.error(f"Failed to extract MeSH terms: {e}")
            return []
