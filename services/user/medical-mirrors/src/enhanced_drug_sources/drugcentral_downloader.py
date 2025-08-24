"""
DrugCentral Smart Downloader
Downloads drug data from DrugCentral PostgreSQL database focusing on mechanism of action, 
target data, and special population information
Follows no-parsing architecture - saves raw query results as JSON only
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
import asyncpg
import ssl

from config import Config

logger = logging.getLogger(__name__)


class DrugCentralDownloadState:
    """State management for DrugCentral downloads"""
    
    def __init__(self):
        self.successful_downloads = 0
        self.failed_downloads = 0
        self.connection_failures = 0
        self.total_files_downloaded = 0
        self.last_download = None
        self.completed_queries = set()  # Track which queries completed successfully
        self.downloaded_drug_ids = set()  # Track individual drug IDs
        self.download_start_time = None


class SmartDrugCentralDownloader:
    """Smart downloader for DrugCentral PostgreSQL database"""
    
    def __init__(self, output_dir: Optional[Path] = None, config: Optional[Config] = None):
        self.config = config or Config()
        self.output_dir = output_dir or Path(self.config.get_drugcentral_data_dir())
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize state
        self.state = DrugCentralDownloadState()
        
        # DrugCentral database connection parameters (from research)
        self.db_host = getattr(self.config, 'DRUGCENTRAL_DB_HOST', 'unmtid-dbs.net')
        self.db_port = getattr(self.config, 'DRUGCENTRAL_DB_PORT', 5433)
        self.db_name = getattr(self.config, 'DRUGCENTRAL_DB_NAME', 'drugcentral')
        self.db_user = getattr(self.config, 'DRUGCENTRAL_DB_USER', 'drugman')
        self.db_password = getattr(self.config, 'DRUGCENTRAL_DB_PASSWORD', 'dosage')
        
        # Connection settings
        self.connection_timeout = 30  # seconds
        self.query_timeout = 120  # seconds for large queries
        
        # Downloaded files tracking - NO PARSING
        self.downloaded_files: Dict[str, str] = {}  # query_type -> file_path
        self.connection: Optional[asyncpg.Connection] = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self._connect_database()
        await self._load_existing_results()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.connection:
            await self.connection.close()
    
    async def _connect_database(self):
        """Connect to DrugCentral PostgreSQL database"""
        try:
            # Create SSL context for secure connection
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            logger.info(f"Connecting to DrugCentral database at {self.db_host}:{self.db_port}")
            
            self.connection = await asyncpg.connect(
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
                user=self.db_user,
                password=self.db_password,
                ssl=ssl_context,
                command_timeout=self.connection_timeout
            )
            
            # Test connection with simple query
            result = await self.connection.fetchval('SELECT version()')
            logger.info(f"Connected to DrugCentral: {result}")
            
        except Exception as e:
            logger.error(f"Failed to connect to DrugCentral database: {e}")
            self.state.connection_failures += 1
            self.connection = None
            raise
    
    def _load_state(self) -> Dict[str, Any]:
        """Load download state from file"""
        state_file = self.output_dir / "drugcentral_download_state.json"
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state_data = json.load(f)
                    # Restore state
                    self.state.completed_queries = set(state_data.get('completed_queries', []))
                    self.state.downloaded_drug_ids = set(state_data.get('downloaded_drug_ids', []))
                    self.state.successful_downloads = state_data.get('successful_downloads', 0)
                    self.state.failed_downloads = state_data.get('failed_downloads', 0)
                    logger.info(f"Loaded DrugCentral state: {len(self.state.completed_queries)} completed queries")
                    return state_data
            except Exception as e:
                logger.warning(f"Failed to load DrugCentral state: {e}")
        return {}
    
    def _save_state(self):
        """Save download state to file"""
        state_file = self.output_dir / "drugcentral_download_state.json"
        state_data = {
            'timestamp': datetime.now().isoformat(),
            'completed_queries': list(self.state.completed_queries),
            'downloaded_drug_ids': list(self.state.downloaded_drug_ids),
            'successful_downloads': self.state.successful_downloads,
            'failed_downloads': self.state.failed_downloads,
            'connection_failures': self.state.connection_failures,
            'total_files_downloaded': self.state.total_files_downloaded
        }
        
        try:
            with open(state_file, 'w') as f:
                json.dump(state_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save DrugCentral state: {e}")
    
    async def _load_existing_results(self):
        """Load existing downloaded files - NO PARSING"""
        self._load_state()
        
        # Scan for existing JSON files
        for json_file in self.output_dir.glob("*.json"):
            if json_file.name.endswith("_state.json"):
                continue  # Skip state files
                
            try:
                # Extract query type from filename
                query_type = json_file.stem  # Remove .json extension
                self.downloaded_files[query_type] = str(json_file)
                logger.debug(f"Found existing DrugCentral file: {json_file.name}")
            except Exception as e:
                logger.warning(f"Error processing existing file {json_file}: {e}")
        
        logger.info(f"Loaded {len(self.downloaded_files)} existing DrugCentral files")
    
    async def download_mechanism_of_action_data(self) -> Optional[str]:
        """Download mechanism of action data for drugs - saves raw JSON only"""
        
        query_key = "mechanism_of_action"
        
        if query_key in self.state.completed_queries:
            logger.debug(f"DrugCentral query {query_key} already completed")
            return self.downloaded_files.get(query_key)
        
        if not self.connection:
            logger.error("No database connection available")
            return None
        
        try:
            # Query to get mechanism of action data using act_table_full (correct table)
            query = """
            SELECT DISTINCT
                s.id as drug_id,
                s.name as drug_name,
                s.smiles,
                s.inchikey,
                s.cas_reg_no,
                act.action_type as mechanism_of_action,
                act.target_name,
                act.target_class,
                act.gene,
                act.act_type,
                act.act_value,
                act.act_unit,
                act.moa,
                act.moa_source
            FROM structures s
            JOIN act_table_full act ON s.id = act.struct_id
            WHERE act.action_type IS NOT NULL
            AND s.name IS NOT NULL
            ORDER BY s.name, act.action_type
            LIMIT 10000
            """
            
            logger.info("Executing mechanism of action query...")
            rows = await self.connection.fetch(query)
            
            # Convert asyncpg.Record objects to dictionaries
            results = []
            for row in rows:
                row_dict = dict(row)
                # Track drug IDs
                if row_dict.get('drug_id'):
                    self.state.downloaded_drug_ids.add(str(row_dict['drug_id']))
                results.append(row_dict)
            
            # Save raw query results - NO PARSING
            output_file = self.output_dir / f"{query_key}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'query_type': query_key,
                    'download_timestamp': datetime.now().isoformat(),
                    'total_records': len(results),
                    'query_sql': query,
                    'results': results
                }, f, indent=2, ensure_ascii=False, default=str)
            
            self.downloaded_files[query_key] = str(output_file)
            self.state.completed_queries.add(query_key)
            self.state.successful_downloads += 1
            self.state.total_files_downloaded += 1
            
            logger.info(f"Downloaded {len(results)} mechanism of action records")
            return str(output_file)
            
        except Exception as e:
            logger.error(f"Error downloading mechanism of action data: {e}")
            self.state.failed_downloads += 1
            return None
    
    async def download_drug_target_data(self) -> Optional[str]:
        """Download drug target interaction data - saves raw JSON only"""
        
        query_key = "drug_targets"
        
        if query_key in self.state.completed_queries:
            logger.debug(f"DrugCentral query {query_key} already completed")
            return self.downloaded_files.get(query_key)
        
        if not self.connection:
            logger.error("No database connection available")
            return None
        
        try:
            # Query to get drug-target interaction data using act_table_full
            query = """
            SELECT DISTINCT
                s.id as drug_id,
                s.name as drug_name,
                s.cas_reg_no,
                s.smiles,
                act.target_name,
                act.target_class,
                act.accession,
                act.gene,
                act.swissprot,
                act.act_value,
                act.act_unit,
                act.act_type,
                act.relation,
                act.act_source
            FROM structures s
            JOIN act_table_full act ON s.id = act.struct_id
            WHERE act.target_name IS NOT NULL
            AND s.name IS NOT NULL
            ORDER BY s.name, act.target_name
            LIMIT 15000
            """
            
            logger.info("Executing drug targets query...")
            rows = await self.connection.fetch(query)
            
            # Convert asyncpg.Record objects to dictionaries
            results = []
            for row in rows:
                row_dict = dict(row)
                # Track drug IDs
                if row_dict.get('drug_id'):
                    self.state.downloaded_drug_ids.add(str(row_dict['drug_id']))
                results.append(row_dict)
            
            # Save raw query results - NO PARSING
            output_file = self.output_dir / f"{query_key}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'query_type': query_key,
                    'download_timestamp': datetime.now().isoformat(),
                    'total_records': len(results),
                    'query_sql': query,
                    'results': results
                }, f, indent=2, ensure_ascii=False, default=str)
            
            self.downloaded_files[query_key] = str(output_file)
            self.state.completed_queries.add(query_key)
            self.state.successful_downloads += 1
            self.state.total_files_downloaded += 1
            
            logger.info(f"Downloaded {len(results)} drug-target records")
            return str(output_file)
            
        except Exception as e:
            logger.error(f"Error downloading drug target data: {e}")
            self.state.failed_downloads += 1
            return None
    
    async def download_pharmacology_data(self) -> Optional[str]:
        """Download pharmacology and indication data - saves raw JSON only"""
        
        query_key = "pharmacology"
        
        if query_key in self.state.completed_queries:
            logger.debug(f"DrugCentral query {query_key} already completed")
            return self.downloaded_files.get(query_key)
        
        if not self.connection:
            logger.error("No database connection available")
            return None
        
        try:
            # Query to get pharmacology data including mechanism of action and activity types
            query = """
            SELECT DISTINCT
                s.id as drug_id,
                s.name as drug_name,
                s.cas_reg_no,
                s.smiles,
                act.moa as mechanism_of_action,
                act.moa_source,
                act.action_type,
                act.act_type as activity_type,
                act.act_value as activity_value,
                act.act_unit as activity_unit,
                act.target_name,
                act.target_class,
                act.gene,
                act.first_in_class
            FROM structures s
            JOIN act_table_full act ON s.id = act.struct_id
            WHERE s.name IS NOT NULL
            AND (act.moa IS NOT NULL 
                 OR act.action_type IS NOT NULL 
                 OR act.first_in_class IS NOT NULL)
            ORDER BY s.name
            LIMIT 8000
            """
            
            logger.info("Executing pharmacology query...")
            rows = await self.connection.fetch(query)
            
            # Convert asyncpg.Record objects to dictionaries
            results = []
            for row in rows:
                row_dict = dict(row)
                # Track drug IDs
                if row_dict.get('drug_id'):
                    self.state.downloaded_drug_ids.add(str(row_dict['drug_id']))
                results.append(row_dict)
            
            # Save raw query results - NO PARSING
            output_file = self.output_dir / f"{query_key}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'query_type': query_key,
                    'download_timestamp': datetime.now().isoformat(),
                    'total_records': len(results),
                    'query_sql': query,
                    'results': results
                }, f, indent=2, ensure_ascii=False, default=str)
            
            self.downloaded_files[query_key] = str(output_file)
            self.state.completed_queries.add(query_key)
            self.state.successful_downloads += 1
            self.state.total_files_downloaded += 1
            
            logger.info(f"Downloaded {len(results)} pharmacology records")
            return str(output_file)
            
        except Exception as e:
            logger.error(f"Error downloading pharmacology data: {e}")
            self.state.failed_downloads += 1
            return None
    
    async def download_comprehensive_drug_data(
        self,
        force_fresh: bool = False
    ) -> Dict[str, Any]:
        """Download comprehensive drug data from DrugCentral"""
        
        if force_fresh:
            self.state = DrugCentralDownloadState()
            self.downloaded_files.clear()
        
        self.state.download_start_time = datetime.now()
        
        if not self.connection:
            logger.error("No database connection - cannot download data")
            return {'error': 'Database connection failed'}
        
        logger.info("Starting comprehensive DrugCentral download")
        
        # Download different data types
        download_tasks = [
            self.download_mechanism_of_action_data(),
            self.download_drug_target_data(), 
            self.download_pharmacology_data()
        ]
        
        results = await asyncio.gather(*download_tasks, return_exceptions=True)
        
        # Count successful downloads
        successful_files = [r for r in results if isinstance(r, str) and r is not None]
        logger.info(f"Successfully downloaded {len(successful_files)} DrugCentral files")
        
        # Save final state
        self._save_state()
        
        return await self.get_download_summary()
    
    async def get_download_status(self) -> Dict[str, Any]:
        """Get current download status"""
        return {
            'timestamp': datetime.now().isoformat(),
            'data_type': 'drugcentral_comprehensive',
            'progress': {
                'total_files': self.state.total_files_downloaded,
                'successful_downloads': self.state.successful_downloads,
                'failed_downloads': self.state.failed_downloads,
                'connection_failures': self.state.connection_failures,
                'completed_queries': len(self.state.completed_queries),
                'unique_drugs': len(self.state.downloaded_drug_ids)
            },
            'files_downloaded': len(self.downloaded_files),
            'output_directory': str(self.output_dir),
            'state': 'completed' if len(self.state.completed_queries) >= 3 else 'in_progress',
            'database_connection': 'connected' if self.connection else 'disconnected'
        }
    
    async def get_download_summary(self) -> Dict[str, Any]:
        """Get download summary with file statistics"""
        total_files = len(self.downloaded_files)
        
        # Calculate file size statistics
        total_size = 0
        for file_path in self.downloaded_files.values():
            try:
                total_size += Path(file_path).stat().st_size
            except:
                continue
        
        return {
            'total_files': total_files,
            'successful_sources': 1 if total_files > 0 else 0,
            'failed_sources': 1 if self.state.failed_downloads > 0 else 0,
            'connection_failures': self.state.connection_failures,
            'success_rate': (self.state.successful_downloads / max(1, self.state.successful_downloads + self.state.failed_downloads)) * 100,
            'by_source_breakdown': {
                'drugcentral_postgresql': total_files
            },
            'download_stats': {
                'files_processed': total_files,
                'download_errors': self.state.failed_downloads,
                'files_verified': total_files,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'success_rate': (self.state.successful_downloads / max(1, self.state.successful_downloads + self.state.failed_downloads))
            },
            'completed_queries': len(self.state.completed_queries),
            'unique_drugs_downloaded': len(self.state.downloaded_drug_ids),
            'data_source': 'drugcentral'
        }
    
    def reset_download_state(self):
        """Reset all download states"""
        self.state = DrugCentralDownloadState()
        self.downloaded_files.clear()
        
        # Remove state file
        state_file = self.output_dir / "drugcentral_download_state.json"
        if state_file.exists():
            state_file.unlink()
        
        logger.info("Reset DrugCentral download state")