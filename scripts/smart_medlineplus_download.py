#!/usr/bin/env python3
"""
Smart MedlinePlus health topics download script
Downloads comprehensive health information from MedlinePlus API
Rate limit: 85 requests per minute
"""

import asyncio
import aiohttp
import json
import logging
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import quote

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SmartMedlinePlusDownloader:
    """Smart downloader for MedlinePlus health topics with rate limiting"""
    
    BASE_URL = "https://wsearch.nlm.nih.gov/ws/query"
    RATE_LIMIT = 85  # requests per minute
    RATE_DELAY = 60 / 85  # ~0.7 seconds between requests
    
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.output_dir / "medlineplus_download_state.json"
        self.topics_file = self.output_dir / "medlineplus_topics.json"
        self.state = self.load_state()
        self.topics = []
        self.session = None
        
    def load_state(self) -> Dict:
        """Load download state for resumability"""
        if self.state_file.exists():
            with open(self.state_file) as f:
                return json.load(f)
        return {
            "downloaded_topics": [],
            "failed_topics": [],
            "last_download": None,
            "total_downloaded": 0
        }
    
    def save_state(self):
        """Save download state"""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f)
    
    async def search_topics(self, query: str = "", start: int = 0, max_results: int = 100) -> List[Dict]:
        """Search for health topics"""
        params = {
            "db": "healthTopics",
            "term": query if query else "health",
            "rettype": "brief",
            "retstart": start,
            "retmax": max_results
        }
        
        url = f"{self.BASE_URL}?" + "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    text = await response.text()
                    return self.parse_search_results(text)
                else:
                    logger.warning(f"Search failed with status {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    def parse_search_results(self, xml_text: str) -> List[Dict]:
        """Parse XML search results"""
        topics = []
        try:
            root = ET.fromstring(xml_text)
            
            # Find all documents in search results
            for doc in root.findall(".//document"):
                topic = {}
                
                # Extract content fields by name attribute
                for content in doc.findall(".//content"):
                    name = content.get('name')
                    if name and content.text:
                        # Clean HTML tags from content
                        text = content.text.replace('<span class="qt0">', '').replace('</span>', '')
                        
                        if name == 'title':
                            topic['title'] = text
                        elif name == 'FullSummary':
                            topic['summary'] = text
                        elif name == 'groupName' and 'category' not in topic:
                            topic['category'] = text
                        elif name == 'altTitle':
                            if 'also_called' not in topic:
                                topic['also_called'] = []
                            topic['also_called'].append(text)
                        elif name == 'mesh':
                            topic['mesh_terms'] = text
                
                # Extract URL from document attribute
                url = doc.get('url', '')
                if url:
                    topic['url'] = url
                    # Extract topic ID from URL
                    if '/' in url:
                        topic['topic_id'] = 'medlineplus_' + url.split('/')[-1].replace('.html', '')
                
                # Use rank as fallback ID
                if not topic.get('topic_id'):
                    rank = doc.get('rank')
                    if rank:
                        topic['topic_id'] = f"medlineplus_{rank}"
                
                # Convert also_called list to string
                if 'also_called' in topic:
                    topic['also_called'] = ', '.join(topic['also_called'])
                
                if topic.get('title'):
                    topics.append(topic)
                    
        except ET.ParseError as e:
            logger.error(f"XML parse error: {e}")
            
        return topics
    
    async def get_topic_details(self, topic_id: str) -> Optional[Dict]:
        """Get detailed information for a specific topic"""
        # Use the topic search to get full details
        params = {
            "db": "healthTopics",
            "term": topic_id,
            "rettype": "topic",
            "retmax": 1
        }
        
        url = f"{self.BASE_URL}?" + "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    text = await response.text()
                    topics = self.parse_topic_details(text)
                    return topics[0] if topics else None
                else:
                    logger.warning(f"Failed to get topic {topic_id}: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error getting topic {topic_id}: {e}")
            return None
    
    def parse_topic_details(self, xml_text: str) -> List[Dict]:
        """Parse detailed topic XML"""
        topics = []
        try:
            root = ET.fromstring(xml_text)
            
            for doc in root.findall(".//document"):
                topic = {
                    "source": "medlineplus",
                    "last_updated": datetime.now().isoformat()
                }
                
                # Extract all available fields
                field_mappings = {
                    'title': 'title',
                    'FullSummary': 'summary',
                    'groupName': 'category',
                    'language': 'language',
                    'dateCreated': 'date_created',
                    'dateRevised': 'last_reviewed',
                    'mesh': 'mesh_terms',
                    'alsoCalledAltTitle': 'also_called'
                }
                
                for xml_field, json_field in field_mappings.items():
                    elem = doc.find(f".//{xml_field}")
                    if elem is not None and elem.text:
                        topic[json_field] = elem.text.strip()
                
                # Extract URL
                url_elem = doc.find(".//content[@name='FullSummaryURL']")
                if url_elem is not None:
                    topic['url'] = url_elem.get('url', '')
                    # Extract topic ID from URL
                    if '/' in topic['url']:
                        topic['topic_id'] = topic['url'].split('/')[-1].replace('.html', '')
                
                # Extract related information
                related_elem = doc.find(".//relatedInformation")
                if related_elem is not None:
                    related_topics = []
                    for link in related_elem.findall(".//link"):
                        title = link.find("title")
                        if title is not None and title.text:
                            related_topics.append(title.text)
                    if related_topics:
                        topic['related_topics'] = related_topics
                
                # Extract sections from full summary
                if topic.get('summary'):
                    topic['sections'] = self.extract_sections(topic['summary'])
                    topic['content_length'] = len(topic['summary'])
                
                # Generate search text
                search_parts = [
                    topic.get('title', ''),
                    topic.get('category', ''),
                    topic.get('summary', '')[:500],  # First 500 chars of summary
                    ' '.join(topic.get('also_called', '').split(',')) if topic.get('also_called') else ''
                ]
                topic['search_text'] = ' '.join(search_parts).lower()
                
                if topic.get('title'):
                    topics.append(topic)
                    
        except ET.ParseError as e:
            logger.error(f"XML parse error: {e}")
            
        return topics
    
    def extract_sections(self, summary: str) -> List[Dict]:
        """Extract sections from summary text"""
        sections = []
        
        # Simple section extraction based on common patterns
        # MedlinePlus summaries often have clear section breaks
        lines = summary.split('\n')
        current_section = None
        current_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if this looks like a section header (all caps or ends with colon)
            if (line.isupper() and len(line) < 100) or line.endswith(':'):
                # Save previous section
                if current_section:
                    sections.append({
                        "title": current_section,
                        "content": ' '.join(current_content).strip(),
                        "type": "content"
                    })
                current_section = line.rstrip(':')
                current_content = []
            else:
                current_content.append(line)
        
        # Save last section
        if current_section:
            sections.append({
                "title": current_section,
                "content": ' '.join(current_content).strip(),
                "type": "content"
            })
        
        # If no sections found, create one main section
        if not sections and summary:
            sections.append({
                "title": "Overview",
                "content": summary,
                "type": "content"
            })
        
        return sections
    
    async def download_all_topics(self, max_topics: int = 2000):
        """Download all available health topics"""
        async with aiohttp.ClientSession() as self.session:
            logger.info("Starting MedlinePlus health topics download")
            
            # First, get a list of all topics through search
            all_topics = []
            batch_size = 100
            start = 0
            
            logger.info("Fetching topic list...")
            while len(all_topics) < max_topics:
                batch = await self.search_topics("", start, batch_size)
                if not batch:
                    break
                    
                all_topics.extend(batch)
                start += batch_size
                logger.info(f"Found {len(all_topics)} topics so far...")
                
                # Rate limiting
                await asyncio.sleep(self.RATE_DELAY)
                
                if len(batch) < batch_size:
                    break
            
            logger.info(f"Found {len(all_topics)} total topics to download")
            
            # Filter out already downloaded topics
            topics_to_download = [
                t for t in all_topics 
                if t.get('topic_id') not in self.state['downloaded_topics']
            ]
            
            logger.info(f"Need to download {len(topics_to_download)} new topics")
            
            # Download detailed information for each topic
            for i, topic in enumerate(topics_to_download):
                topic_id = topic.get('topic_id', topic.get('title', ''))
                
                logger.info(f"Downloading topic {i+1}/{len(topics_to_download)}: {topic.get('title', topic_id)}")
                
                # Try to get more details if possible
                if topic.get('url'):
                    detailed = await self.get_topic_details(topic.get('title', ''))
                    if detailed:
                        topic.update(detailed)
                
                # Add to our collection
                self.topics.append(topic)
                self.state['downloaded_topics'].append(topic_id)
                self.state['total_downloaded'] += 1
                
                # Save progress every 10 topics
                if (i + 1) % 10 == 0:
                    self.save_progress()
                    logger.info(f"Progress saved: {self.state['total_downloaded']} topics downloaded")
                
                # Rate limiting
                await asyncio.sleep(self.RATE_DELAY)
            
            # Final save
            self.save_progress()
            logger.info(f"Download complete! Total topics: {self.state['total_downloaded']}")
    
    def save_progress(self):
        """Save current progress"""
        # Save topics
        if self.topics:
            existing_topics = []
            if self.topics_file.exists():
                with open(self.topics_file) as f:
                    existing_topics = json.load(f)
            
            # Merge with existing topics
            existing_ids = {t.get('topic_id') for t in existing_topics if t.get('topic_id')}
            for topic in self.topics:
                if topic.get('topic_id') not in existing_ids:
                    existing_topics.append(topic)
            
            # Save merged topics
            with open(self.topics_file, 'w') as f:
                json.dump(existing_topics, f)
            
            logger.info(f"Saved {len(existing_topics)} total topics to {self.topics_file}")
        
        # Save state
        self.state['last_download'] = datetime.now().isoformat()
        self.save_state()

async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart MedlinePlus Health Topics Downloader")
    parser.add_argument("--output-dir", type=Path, 
                       default=Path("/home/intelluxe/database/medical_complete/medlineplus"),
                       help="Output directory for downloaded data")
    parser.add_argument("--max-topics", type=int, default=2000,
                       help="Maximum number of topics to download")
    parser.add_argument("--reset", action="store_true",
                       help="Reset download state and start fresh")
    
    args = parser.parse_args()
    
    downloader = SmartMedlinePlusDownloader(args.output_dir)
    
    if args.reset:
        logger.info("Resetting download state...")
        downloader.state = {
            "downloaded_topics": [],
            "failed_topics": [],
            "last_download": None,
            "total_downloaded": 0
        }
        downloader.topics = []
        if downloader.topics_file.exists():
            downloader.topics_file.unlink()
    
    try:
        await downloader.download_all_topics(args.max_topics)
        
        # Show summary
        logger.info("\n" + "="*50)
        logger.info("Download Summary:")
        logger.info(f"Total topics downloaded: {downloader.state['total_downloaded']}")
        logger.info(f"Output file: {downloader.topics_file}")
        logger.info(f"State file: {downloader.state_file}")
        logger.info("="*50)
        
    except KeyboardInterrupt:
        logger.info("\nDownload interrupted by user")
        downloader.save_progress()
        logger.info("Progress saved. Run again to resume.")
    except Exception as e:
        logger.error(f"Download failed: {e}")
        downloader.save_progress()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))