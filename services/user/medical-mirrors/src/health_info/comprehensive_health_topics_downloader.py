"""
Comprehensive Health Topics Downloader - Fixes all MyHealthfinder API issues

This downloader addresses the following problems:
1. Progress blocking with 103 topics showing as downloaded but no content saved
2. Missing health_topics_complete.json file
3. Fallback data pollution in database
4. Missing AI enhancement integration
5. Incomplete API utilization

Solution:
- Fresh API discovery to find ALL available health topics (not just 103)
- Complete topic detail download with proper error handling
- AI enhancement integration with health_topics_enrichment.py
- Search vector generation for database integration
- Proper progress tracking and resume capability
"""

import asyncio
import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import aiohttp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import existing components
import sys
sys.path.append(str(Path(__file__).parent.parent))

from config import Config
from health_info.health_topics_enrichment import HealthTopicsEnricher, convert_enhancement_to_dict
from config_loader import get_config

logger = logging.getLogger(__name__)


class ComprehensiveHealthTopicsState:
    """Enhanced state management for comprehensive health topics download"""
    
    def __init__(self):
        self.api_exploration_complete = False
        self.total_topics_discovered = 0
        self.topics_downloaded = 0
        self.topics_enhanced = 0
        self.failed_topics = []
        self.rate_limited_until = None
        self.daily_retry_count = 0
        self.last_update = None
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "api_exploration_complete": self.api_exploration_complete,
            "total_topics_discovered": self.total_topics_discovered,
            "topics_downloaded": self.topics_downloaded,
            "topics_enhanced": self.topics_enhanced,
            "failed_topics": self.failed_topics,
            "rate_limited_until": self.rate_limited_until.isoformat() if self.rate_limited_until else None,
            "daily_retry_count": self.daily_retry_count,
            "last_update": self.last_update.isoformat() if self.last_update else None
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ComprehensiveHealthTopicsState':
        state = cls()
        state.api_exploration_complete = data.get("api_exploration_complete", False)
        state.total_topics_discovered = data.get("total_topics_discovered", 0)
        state.topics_downloaded = data.get("topics_downloaded", 0)
        state.topics_enhanced = data.get("topics_enhanced", 0)
        state.failed_topics = data.get("failed_topics", [])
        
        rate_limited_str = data.get("rate_limited_until")
        if rate_limited_str:
            state.rate_limited_until = datetime.fromisoformat(rate_limited_str)
            
        state.daily_retry_count = data.get("daily_retry_count", 0)
        
        last_update_str = data.get("last_update")
        if last_update_str:
            state.last_update = datetime.fromisoformat(last_update_str)
            
        return state


class ComprehensiveHealthTopicsDownloader:
    """Comprehensive health topics downloader with complete API exploration"""
    
    def __init__(self, output_dir: Optional[Path] = None, config: Optional[Config] = None):
        self.config = config or Config()
        self.output_dir = output_dir or Path("/home/intelluxe/database/medical_complete/health_info")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # API configuration
        self.myhealthfinder_url = "https://odphp.health.gov/myhealthfinder/api/v4"
        self.request_delay = 2.0  # 2 seconds between requests to be respectful
        self.max_retries = 3
        self.timeout = 30
        
        # State management
        self.state_file = self.output_dir / "comprehensive_health_topics_state.json"
        self.state = self._load_state()
        
        # AI enhancement
        self.ai_config = get_config()
        self.enricher = None
        self.enable_ai_enhancement = True
        
        # Results storage
        self.all_topics: List[Dict[str, Any]] = []
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={"User-Agent": "Medical-Mirrors/2.0 (Healthcare Research - Comprehensive)"}
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
            
    def _load_state(self) -> ComprehensiveHealthTopicsState:
        """Load download state from JSON file"""
        if not self.state_file.exists():
            return ComprehensiveHealthTopicsState()
            
        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)
            return ComprehensiveHealthTopicsState.from_dict(data)
        except Exception as e:
            logger.warning(f"Failed to load state file: {e}, using fresh state")
            return ComprehensiveHealthTopicsState()
            
    def _save_state(self):
        """Save download state to JSON file"""
        try:
            self.state.last_update = datetime.now()
            with open(self.state_file, 'w') as f:
                json.dump(self.state.to_dict(), f, indent=2)
            logger.debug(f"State saved to {self.state_file}")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
            
    async def discover_all_health_topics(self, force_fresh: bool = False) -> Dict[str, Any]:
        """
        Comprehensive health topics discovery and download
        
        This method:
        1. Discovers ALL available health topics from the API
        2. Downloads complete details for each topic
        3. Applies AI enhancement for medical relevance
        4. Generates search vectors for database integration
        5. Saves complete dataset to health_topics_complete.json
        
        Args:
            force_fresh: If True, ignore existing state and start fresh
            
        Returns:
            Summary of discovery and download results
        """
        logger.info("Starting comprehensive health topics discovery and download")
        
        if force_fresh:
            logger.info("Force fresh mode - resetting all state")
            self.state = ComprehensiveHealthTopicsState()
            self._save_state()
            
        start_time = time.time()
        
        try:
            # Step 1: Discover all available topics
            if not self.state.api_exploration_complete:
                await self._explore_api_comprehensively()
                
            # Step 2: Download topic details
            await self._download_all_topic_details()
            
            # Step 3: Apply AI enhancement
            if self.enable_ai_enhancement and self.all_topics:
                await self._enhance_topics_with_ai()
                
            # Step 4: Generate search vectors and finalize
            await self._finalize_topics_data()
            
            # Step 5: Save complete dataset
            await self._save_complete_dataset()
            
            duration = time.time() - start_time
            
            summary = {
                "total_topics_discovered": self.state.total_topics_discovered,
                "total_topics_downloaded": self.state.topics_downloaded,
                "total_topics_enhanced": self.state.topics_enhanced,
                "failed_topics_count": len(self.state.failed_topics),
                "duration_seconds": duration,
                "success_rate": (self.state.topics_downloaded / max(self.state.total_topics_discovered, 1)) * 100,
                "enhancement_rate": (self.state.topics_enhanced / max(self.state.topics_downloaded, 1)) * 100,
                "api_exploration_complete": self.state.api_exploration_complete,
                "final_dataset_size": len(self.all_topics)
            }
            
            logger.info(f"Comprehensive health topics download completed in {duration:.1f}s")
            logger.info(f"Topics: {self.state.topics_downloaded}/{self.state.total_topics_discovered} downloaded")
            logger.info(f"Enhanced: {self.state.topics_enhanced} topics with AI")
            logger.info(f"Success rate: {summary['success_rate']:.1f}%")
            
            return summary
            
        except Exception as e:
            logger.exception(f"Comprehensive health topics download failed: {e}")
            raise
            
    async def _explore_api_comprehensively(self):
        """Comprehensive API exploration to find ALL available health topics"""
        logger.info("Starting comprehensive API exploration")
        
        try:
            # Method 1: Standard itemlist endpoint
            topics_from_itemlist = await self._get_topics_from_itemlist()
            logger.info(f"Found {len(topics_from_itemlist)} topics from itemlist endpoint")
            
            # Method 2: Try different API parameters and endpoints
            additional_topics = await self._explore_additional_endpoints()
            logger.info(f"Found {len(additional_topics)} additional topics from exploration")
            
            # Method 3: ID range scanning (responsible)
            scanned_topics = await self._responsible_id_scanning(topics_from_itemlist)
            logger.info(f"Found {len(scanned_topics)} topics from responsible ID scanning")
            
            # Combine and deduplicate
            all_discovered = self._combine_and_deduplicate_topics(
                topics_from_itemlist, additional_topics, scanned_topics
            )
            
            self.state.total_topics_discovered = len(all_discovered)
            self.state.api_exploration_complete = True
            self._save_state()
            
            # Store topic IDs for download
            self.topic_ids_to_download = [topic.get("Id") for topic in all_discovered if topic.get("Id")]
            
            logger.info(f"✅ API exploration complete: {self.state.total_topics_discovered} unique topics discovered")
            
        except Exception as e:
            logger.error(f"API exploration failed: {e}")
            raise
            
    async def _get_topics_from_itemlist(self) -> List[Dict[str, Any]]:
        """Get topics from standard itemlist endpoint"""
        url = f"{self.myhealthfinder_url}/itemlist.json"
        params = {"Type": "topic"}
        
        try:
            await asyncio.sleep(self.request_delay)
            async with self.session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                
                result = data.get("Result", {})
                if result.get("Error") != "False":
                    raise Exception(f"API returned error: {result}")
                    
                items = result.get("Items", {}).get("Item", [])
                logger.info(f"Standard API returned {len(items)} topics")
                return items
                
        except Exception as e:
            logger.error(f"Failed to get topics from itemlist: {e}")
            return []
            
    async def _explore_additional_endpoints(self) -> List[Dict[str, Any]]:
        """Explore additional API endpoints and parameters"""
        additional_topics = []
        
        # Try different API parameters
        exploration_params = [
            {"Type": "topic", "Lang": "en"},
            {"Type": "topic", "Category": "prevention"},
            {"Type": "topic", "Category": "screening"},
            {"Type": "topic", "Audience": "adults"},
            {"Type": "topic", "Audience": "children"},
            {"Type": "topic", "Audience": "teens"},
            {"Type": "topic", "Audience": "seniors"},
        ]
        
        base_url = f"{self.myhealthfinder_url}/itemlist.json"
        
        for params in exploration_params:
            try:
                await asyncio.sleep(self.request_delay)  # Rate limiting
                async with self.session.get(base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        result = data.get("Result", {})
                        
                        if result.get("Error") == "False":
                            items = result.get("Items", {}).get("Item", [])
                            additional_topics.extend(items)
                            logger.debug(f"Found {len(items)} topics with params {params}")
                            
            except Exception as e:
                logger.warning(f"Failed to explore with params {params}: {e}")
                continue
                
        return additional_topics
        
    async def _responsible_id_scanning(self, known_topics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Responsible ID scanning to find topics that might not appear in itemlist
        Only scans reasonable ranges based on known topic IDs
        """
        if not known_topics:
            return []
            
        # Extract known IDs and find ranges
        known_ids = []
        for topic in known_topics:
            try:
                topic_id = int(topic.get("Id", 0))
                if topic_id > 0:
                    known_ids.append(topic_id)
            except (ValueError, TypeError):
                continue
                
        if not known_ids:
            return []
            
        known_ids.sort()
        min_id, max_id = min(known_ids), max(known_ids)
        
        logger.info(f"Responsible ID scanning range: {min_id} to {max_id}")
        logger.info(f"Known IDs: {len(known_ids)}, will scan for gaps")
        
        # Find gaps in known IDs and scan only those
        scanned_topics = []
        gap_count = 0
        scan_limit = 50  # Limit gap scanning to be responsible
        
        for topic_id in range(min_id, max_id + 1):
            if topic_id not in known_ids and gap_count < scan_limit:
                try:
                    topic_data = await self._get_topic_by_id(str(topic_id))
                    if topic_data:
                        scanned_topics.append({
                            "Id": str(topic_id),
                            "Title": topic_data.get("title", f"Topic {topic_id}"),
                            "ParentId": "-1",
                            "TranslationId": "0",
                            "Type": "Topic"
                        })
                        logger.info(f"Found additional topic via ID scan: {topic_id}")
                        
                    gap_count += 1
                    await asyncio.sleep(self.request_delay)  # Rate limiting
                    
                except Exception as e:
                    logger.debug(f"No topic found for ID {topic_id}: {e}")
                    continue
                    
        logger.info(f"ID scanning found {len(scanned_topics)} additional topics")
        return scanned_topics
        
    async def _get_topic_by_id(self, topic_id: str) -> Optional[Dict[str, Any]]:
        """Get a single topic by ID to check if it exists"""
        url = f"{self.myhealthfinder_url}/topicsearch.json"
        params = {"TopicId": topic_id}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    result = data.get("Result", {})
                    
                    if result.get("Error") == "False":
                        resources = result.get("Resources", {}).get("Resource", [])
                        if resources:
                            resource = resources[0]
                            return {
                                "topic_id": topic_id,
                                "title": resource.get("Title", "")
                            }
        except Exception:
            pass  # Topic doesn't exist
            
        return None
        
    def _combine_and_deduplicate_topics(self, *topic_lists) -> List[Dict[str, Any]]:
        """Combine topic lists and remove duplicates"""
        seen_ids = set()
        combined_topics = []
        
        for topic_list in topic_lists:
            for topic in topic_list:
                topic_id = topic.get("Id")
                if topic_id and topic_id not in seen_ids:
                    seen_ids.add(topic_id)
                    combined_topics.append(topic)
                    
        return combined_topics
        
    async def _download_all_topic_details(self):
        """Download detailed information for all discovered topics"""
        if not hasattr(self, 'topic_ids_to_download'):
            logger.error("No topic IDs available for download. Run API exploration first.")
            return
            
        logger.info(f"Starting download of {len(self.topic_ids_to_download)} topic details")
        
        downloaded_count = 0
        
        for i, topic_id in enumerate(self.topic_ids_to_download):
            try:
                if topic_id in [t.get("topic_id") for t in self.all_topics]:
                    logger.debug(f"Topic {topic_id} already downloaded, skipping")
                    continue
                    
                logger.info(f"Downloading topic {i+1}/{len(self.topic_ids_to_download)}: {topic_id}")
                
                topic_detail = await self._download_topic_detail(topic_id)
                if topic_detail:
                    self.all_topics.append(topic_detail)
                    downloaded_count += 1
                    
                    # Update state frequently
                    self.state.topics_downloaded = downloaded_count
                    if downloaded_count % 10 == 0:  # Save state every 10 downloads
                        self._save_state()
                        
                else:
                    self.state.failed_topics.append(topic_id)
                    
                await asyncio.sleep(self.request_delay)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Failed to download topic {topic_id}: {e}")
                self.state.failed_topics.append(topic_id)
                continue
                
        self.state.topics_downloaded = len(self.all_topics)
        self._save_state()
        
        logger.info(f"✅ Downloaded {downloaded_count} topic details")
        logger.info(f"❌ Failed to download {len(self.state.failed_topics)} topics")
        
    async def _download_topic_detail(self, topic_id: str) -> Optional[Dict[str, Any]]:
        """Download detailed information for a specific topic"""
        url = f"{self.myhealthfinder_url}/topicsearch.json"
        params = {"TopicId": topic_id}
        
        for attempt in range(self.max_retries):
            try:
                async with self.session.get(url, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    result = data.get("Result", {})
                    if result.get("Error") != "False":
                        logger.warning(f"API returned error for topic {topic_id}: {result}")
                        return None
                        
                    resources = result.get("Resources", {}).get("Resource", [])
                    if not resources:
                        logger.warning(f"No resource data found for topic {topic_id}")
                        return None
                        
                    resource = resources[0]
                    return self._parse_topic_detail(topic_id, resource)
                    
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    logger.warning(f"Attempt {attempt + 1} failed for topic {topic_id}: {e}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"All attempts failed for topic {topic_id}: {e}")
                    return None
                    
        return None
        
    def _parse_topic_detail(self, topic_id: str, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Parse topic detail from API response into structured format"""
        # Extract sections
        sections = []
        if "Sections" in resource:
            sections_data = resource["Sections"].get("section", [])
            for section in sections_data:
                if isinstance(section, dict):
                    content = section.get("Content", "")
                    # Clean HTML content
                    content = re.sub(r"<[^>]+>", "", content)
                    content = content.replace("&nbsp;", " ").replace("&amp;", "&")
                    content = content.replace("&lt;", "<").replace("&gt;", ">")
                    
                    sections.append({
                        "title": section.get("Title", ""),
                        "content": content.strip(),
                        "type": "content"
                    })
                    
        # Extract related topics
        related_topics = []
        if "RelatedItems" in resource:
            related_items = resource["RelatedItems"].get("RelatedItem", [])
            for item in related_items:
                if isinstance(item, dict):
                    title = item.get("Title")
                    if title:
                        related_topics.append(title)
                        
        # Generate comprehensive topic data
        return {
            "topic_id": topic_id,
            "title": resource.get("Title", ""),
            "category": resource.get("Categories", "General Health"),
            "url": resource.get("AccessibleVersion", ""),
            "last_reviewed": resource.get("LastUpdate", ""),
            "audience": self._extract_audience_from_content(resource, sections),
            "sections": sections,
            "related_topics": related_topics,
            "summary": self._create_summary_from_sections(sections),
            "keywords": self._extract_keywords_from_content(sections),
            "content_length": sum(len(s.get("content", "")) for s in sections),
            "source": "myhealthfinder",
            "search_text": self._create_search_text(resource, sections),
            "last_updated": datetime.now().isoformat(),
            "item_type": "health_topic",
            "api_version": "v4",
            "comprehensive_download": True  # Mark as comprehensive download
        }
        
    def _extract_audience_from_content(self, resource: Dict[str, Any], sections: List[Dict[str, Any]]) -> List[str]:
        """Extract target audience from resource and content"""
        audiences = []
        
        # Check all content for audience indicators
        all_content = str(resource) + " " + " ".join(s.get("content", "") for s in sections)
        content_lower = all_content.lower()
        
        # Age groups
        if any(word in content_lower for word in ["adult", "grown-up", "18+"]):
            audiences.append("adults")
        if any(word in content_lower for word in ["child", "kid", "pediatric", "under 18"]):
            audiences.append("children")
        if any(word in content_lower for word in ["teen", "adolescent", "youth", "13-17"]):
            audiences.append("teens")
        if any(word in content_lower for word in ["senior", "older", "elderly", "65+"]):
            audiences.append("seniors")
            
        # Specific groups
        if any(word in content_lower for word in ["women", "female"]) and "pregnant" not in content_lower:
            audiences.append("women")
        if any(word in content_lower for word in ["men", "male"]):
            audiences.append("men")
        if any(word in content_lower for word in ["pregnant", "pregnancy", "expecting"]):
            audiences.append("pregnant_women")
            
        return audiences if audiences else ["general"]
        
    def _create_summary_from_sections(self, sections: List[Dict[str, Any]]) -> str:
        """Create a comprehensive summary from sections"""
        for section in sections:
            title = (section.get("title") or "").lower()
            if title in ["overview", "basics", "the basics", "about"]:
                content = section.get("content", "")
                if content:
                    summary = content[:300].strip()
                    if len(content) > 300:
                        summary += "..."
                    return summary
                    
        # If no overview section, use first non-empty section
        for section in sections:
            content = section.get("content", "")
            if len(content.strip()) > 50:  # At least 50 characters
                summary = content[:300].strip()
                if len(content) > 300:
                    summary += "..."
                return summary
                
        return ""
        
    def _extract_keywords_from_content(self, sections: List[Dict[str, Any]]) -> List[str]:
        """Extract comprehensive keywords from all content"""
        all_content = " ".join(s.get("content", "") for s in sections).lower()
        all_titles = " ".join(s.get("title", "") for s in sections).lower()
        
        # Medical and health keywords
        medical_keywords = [
            "health", "disease", "prevention", "treatment", "symptoms", "diagnosis",
            "medical", "doctor", "screening", "therapy", "medication", "care",
            "wellness", "fitness", "nutrition", "exercise", "diet", "lifestyle",
            "chronic", "acute", "condition", "disorder", "syndrome", "infection",
            "cancer", "diabetes", "heart", "blood", "pressure", "cholesterol",
            "mental", "physical", "emotional", "behavioral", "cognitive",
            "risk", "factor", "complication", "side effect", "adverse",
            "vaccine", "immunization", "surgery", "procedure", "test",
            "hospital", "clinic", "emergency", "urgent", "primary", "specialist"
        ]
        
        found_keywords = []
        for keyword in medical_keywords:
            if keyword in all_content or keyword in all_titles:
                found_keywords.append(keyword)
                
        # Extract title words as additional keywords
        title_words = re.findall(r"\b\w{4,}\b", all_titles)
        found_keywords.extend([w for w in title_words if len(w) > 3 and w not in found_keywords])
        
        # Remove common words and limit
        common_words = {"this", "that", "with", "have", "from", "they", "been", "were", "said", "each", "which", "more", "some", "what", "make", "take", "than", "only", "also"}
        filtered_keywords = [kw for kw in found_keywords if kw not in common_words]
        
        return sorted(list(set(filtered_keywords)))[:30]  # Top 30 unique keywords
        
    def _create_search_text(self, resource: Dict[str, Any], sections: List[Dict[str, Any]]) -> str:
        """Create comprehensive search text for database indexing"""
        search_parts = [
            resource.get("Title", ""),
            resource.get("Categories", ""),
            " ".join(s.get("title", "") for s in sections),
            " ".join(s.get("content", "") for s in sections)
        ]
        
        return " ".join(search_parts).lower().strip()
        
    async def _enhance_topics_with_ai(self):
        """Apply AI enhancement to all downloaded topics"""
        if not self.all_topics:
            logger.info("No topics available for AI enhancement")
            return
            
        if not self.ai_config.is_enhancement_enabled('health_topics'):
            logger.info("AI enhancement is disabled in configuration")
            return
            
        try:
            logger.info(f"Starting AI enhancement for {len(self.all_topics)} health topics")
            
            # Initialize enricher
            if self.enricher is None:
                self.enricher = HealthTopicsEnricher()
                
            # Enhance topics in batches
            batch_size = 10  # Process 10 topics at a time
            enhanced_count = 0
            
            for i in range(0, len(self.all_topics), batch_size):
                batch = self.all_topics[i:i + batch_size]
                
                try:
                    enhanced_batch = await self.enricher.enhance_health_topics(batch)
                    
                    # Merge enhanced data back into original topics
                    for j, enhanced_topic in enumerate(enhanced_batch):
                        if i + j < len(self.all_topics):
                            original_topic = self.all_topics[i + j]
                            enhancement_data = convert_enhancement_to_dict(enhanced_topic)
                            
                            # Add enhancement fields
                            original_topic.update({
                                "medical_entities": enhancement_data.get("medical_entities", {}),
                                "icd10_mappings": enhancement_data.get("icd10_mappings", []),
                                "clinical_relevance_score": enhancement_data.get("clinical_relevance_score", 0.0),
                                "topic_classification": enhancement_data.get("topic_classification", "general"),
                                "risk_factors": enhancement_data.get("risk_factors", []),
                                "related_medications": enhancement_data.get("related_medications", []),
                                "enhanced_keywords": enhancement_data.get("enhanced_keywords", []),
                                "related_topics_suggestions": enhancement_data.get("related_topics_suggestions", []),
                                "patient_summary": enhancement_data.get("patient_summary", ""),
                                "provider_summary": enhancement_data.get("provider_summary", ""),
                                "enhancement_timestamp": enhancement_data.get("enhancement_timestamp", ""),
                                "ai_confidence": enhancement_data.get("ai_confidence", 0.0),
                                "data_sources": enhancement_data.get("data_sources", [])
                            })
                            
                            # Update keywords with enhanced ones
                            if enhancement_data.get("enhanced_keywords"):
                                original_topic["keywords"] = enhancement_data["enhanced_keywords"]
                                
                            enhanced_count += 1
                            
                    logger.info(f"Enhanced batch {i//batch_size + 1}: {len(enhanced_batch)} topics")
                    
                    # Update state
                    self.state.topics_enhanced = enhanced_count
                    self._save_state()
                    
                except Exception as e:
                    logger.error(f"Failed to enhance batch starting at index {i}: {e}")
                    continue
                    
            logger.info(f"✅ AI enhancement completed: {enhanced_count} topics enhanced")
            
        except Exception as e:
            logger.error(f"AI enhancement failed: {e}")
            raise
            
    async def _finalize_topics_data(self):
        """Finalize topics data with search vectors and validation"""
        logger.info("Finalizing topics data with search vectors")
        
        finalized_count = 0
        
        for topic in self.all_topics:
            try:
                # Generate search vector text (simple approach for now)
                search_components = [
                    topic.get("title", ""),
                    topic.get("category", ""),
                    topic.get("summary", ""),
                    " ".join(topic.get("keywords", [])),
                    " ".join(topic.get("enhanced_keywords", [])) if topic.get("enhanced_keywords") else ""
                ]
                
                # Update search text with enhanced content
                topic["search_text"] = " ".join(search_components).lower().strip()
                
                # Add final processing timestamp
                topic["final_processing_timestamp"] = datetime.now().isoformat()
                
                # Validate required fields
                if not topic.get("topic_id") or not topic.get("title"):
                    logger.warning(f"Invalid topic data: {topic.get('topic_id', 'unknown')}")
                    continue
                    
                finalized_count += 1
                
            except Exception as e:
                logger.error(f"Failed to finalize topic {topic.get('topic_id', 'unknown')}: {e}")
                continue
                
        logger.info(f"✅ Finalized {finalized_count} topics with search vectors")
        
    async def _save_complete_dataset(self):
        """Save complete health topics dataset to JSON file"""
        if not self.all_topics:
            logger.warning("No topics available to save")
            return
            
        output_file = self.output_dir / "health_topics_complete.json"
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.all_topics, f, ensure_ascii=False, separators=(',', ':'))
                
            logger.info(f"✅ Saved {len(self.all_topics)} health topics to {output_file}")
            logger.info(f"File size: {output_file.stat().st_size / 1024 / 1024:.1f}MB")
            
            # Also save metadata
            metadata = {
                "total_topics": len(self.all_topics),
                "download_timestamp": datetime.now().isoformat(),
                "api_version": "v4",
                "enhancement_enabled": self.enable_ai_enhancement,
                "topics_enhanced": self.state.topics_enhanced,
                "data_source": "myhealthfinder_comprehensive",
                "success_rate": (self.state.topics_downloaded / max(self.state.total_topics_discovered, 1)) * 100
            }
            
            metadata_file = self.output_dir / "health_topics_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
                
            logger.info(f"✅ Saved metadata to {metadata_file}")
            
        except Exception as e:
            logger.error(f"Failed to save complete dataset: {e}")
            raise
            
    def get_download_status(self) -> Dict[str, Any]:
        """Get current download status"""
        return {
            "api_exploration_complete": self.state.api_exploration_complete,
            "total_topics_discovered": self.state.total_topics_discovered,
            "topics_downloaded": self.state.topics_downloaded,
            "topics_enhanced": self.state.topics_enhanced,
            "failed_topics_count": len(self.state.failed_topics),
            "success_rate": (self.state.topics_downloaded / max(self.state.total_topics_discovered, 1)) * 100,
            "enhancement_rate": (self.state.topics_enhanced / max(self.state.topics_downloaded, 1)) * 100,
            "current_dataset_size": len(self.all_topics),
            "rate_limited": self.state.rate_limited_until is not None,
            "last_update": self.state.last_update.isoformat() if self.state.last_update else None
        }
        

async def main():
    """Test the comprehensive health topics downloader"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    config = Config()
    
    async with ComprehensiveHealthTopicsDownloader(config=config) as downloader:
        try:
            # Run comprehensive discovery and download
            summary = await downloader.discover_all_health_topics(force_fresh=True)
            
            print("\n" + "="*60)
            print("COMPREHENSIVE HEALTH TOPICS DOWNLOAD COMPLETE")
            print("="*60)
            print(f"Topics discovered: {summary['total_topics_discovered']}")
            print(f"Topics downloaded: {summary['total_topics_downloaded']}")
            print(f"Topics enhanced: {summary['total_topics_enhanced']}")
            print(f"Success rate: {summary['success_rate']:.1f}%")
            print(f"Enhancement rate: {summary['enhancement_rate']:.1f}%")
            print(f"Duration: {summary['duration_seconds']:.1f} seconds")
            print(f"Final dataset size: {summary['final_dataset_size']} topics")
            print("\nDataset saved to: health_topics_complete.json")
            print("Ready for database integration with AI enhancements!")
            
        except Exception as e:
            print(f"Download failed: {e}")
            raise
            

if __name__ == "__main__":
    asyncio.run(main())
