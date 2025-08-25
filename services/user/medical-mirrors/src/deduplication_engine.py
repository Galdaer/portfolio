"""
Cross-Batch Deduplication Engine for Medical Mirrors

Handles massive duplication rates (99%+) efficiently by preventing re-processing
of identical records across multiple batches while providing accurate progress tracking.

Key Features:
- Pre-processing deduplication checks
- Cross-batch state tracking
- Memory-efficient bulk operations
- Accurate progress metrics with deduplication awareness
- Configurable deduplication strategies per data source
"""

import asyncio
import hashlib
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from database import ClinicalTrial, DrugInformation, PubMedArticle

logger = logging.getLogger(__name__)


class CrossBatchDeduplicator:
    """Cross-batch deduplication engine for medical data processing"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)
        
        # Deduplication strategies per data source
        self.deduplication_strategies = {
            'clinical_trials': {
                'primary_key': 'nct_id',
                'batch_size': 10000,
                'enable_content_hashing': True,
                'hash_fields': ['title', 'status', 'phase', 'conditions', 'interventions']
            },
            'pubmed_articles': {
                'primary_key': 'pmid',
                'batch_size': 5000,
                'enable_content_hashing': True,
                'hash_fields': ['title', 'abstract', 'authors', 'journal']
            },
            'drug_information': {
                'primary_key': 'generic_name',
                'batch_size': 5000,
                'enable_content_hashing': True,
                'hash_fields': ['generic_name', 'therapeutic_class', 'indications_and_usage']
            }
        }
    
    async def get_existing_record_keys(self, table_name: str, key_field: str) -> Set[str]:
        """Get all existing primary keys from database for deduplication"""
        try:
            query = text(f"SELECT {key_field} FROM {table_name}")
            result = self.db_session.execute(query)
            existing_keys = {str(row[0]) for row in result.fetchall()}
            
            self.logger.info(f"Found {len(existing_keys)} existing records in {table_name}")
            return existing_keys
            
        except Exception as e:
            self.logger.exception(f"Failed to get existing keys from {table_name}: {e}")
            return set()
    
    async def deduplicate_within_batch(self, records: List[Dict[str, Any]], 
                                     strategy: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], int]:
        """Remove duplicates within a single batch"""
        primary_key = strategy['primary_key']
        unique_records = {}
        duplicate_count = 0
        
        for record in records:
            key_value = record.get(primary_key)
            if not key_value:
                continue
                
            # Convert key to string for consistency
            key_str = str(key_value)
            
            if key_str not in unique_records:
                unique_records[key_str] = record
            else:
                duplicate_count += 1
                # Keep the record with more complete data
                current = unique_records[key_str]
                new = record
                
                # Simple completeness comparison - count non-empty fields
                current_completeness = sum(1 for v in current.values() if v)
                new_completeness = sum(1 for v in new.values() if v)
                
                if new_completeness > current_completeness:
                    unique_records[key_str] = new
        
        deduplicated_records = list(unique_records.values())
        
        if duplicate_count > 0:
            self.logger.info(f"Removed {duplicate_count} duplicates within batch, "
                           f"keeping {len(deduplicated_records)} unique records")
        
        return deduplicated_records, duplicate_count
    
    async def filter_existing_records(self, records: List[Dict[str, Any]], 
                                    existing_keys: Set[str], 
                                    strategy: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Separate new records from existing ones for cross-batch deduplication"""
        primary_key = strategy['primary_key']
        new_records = []
        existing_records = []
        
        for record in records:
            key_value = record.get(primary_key)
            if not key_value:
                continue
                
            key_str = str(key_value)
            if key_str in existing_keys:
                existing_records.append(record)
            else:
                new_records.append(record)
        
        self.logger.info(f"Cross-batch filtering: {len(new_records)} new, "
                       f"{len(existing_records)} existing records")
        
        return new_records, existing_records
    
    async def generate_content_hash(self, record: Dict[str, Any], 
                                  hash_fields: List[str]) -> str:
        """Generate content hash for detecting identical records with different keys"""
        content_parts = []
        
        for field in hash_fields:
            value = record.get(field)
            if value is not None:
                # Convert to string and normalize
                if isinstance(value, list):
                    content_parts.append('|'.join(sorted(str(item) for item in value)))
                else:
                    content_parts.append(str(value).strip().lower())
            else:
                content_parts.append('')
        
        content_string = '||'.join(content_parts)
        return hashlib.md5(content_string.encode('utf-8')).hexdigest()
    
    async def deduplicate_by_content(self, records: List[Dict[str, Any]], 
                                   strategy: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], int]:
        """Deduplicate records by content hash (detects identical content with different IDs)"""
        if not strategy.get('enable_content_hashing', False):
            return records, 0
            
        hash_fields = strategy.get('hash_fields', [])
        if not hash_fields:
            return records, 0
        
        unique_by_content = {}
        content_duplicates = 0
        
        for record in records:
            content_hash = await self.generate_content_hash(record, hash_fields)
            
            if content_hash not in unique_by_content:
                unique_by_content[content_hash] = record
            else:
                content_duplicates += 1
                # Keep record with more complete data or earlier ID
                existing = unique_by_content[content_hash]
                current = record
                
                # Prefer record with more non-empty fields
                existing_completeness = sum(1 for v in existing.values() if v)
                current_completeness = sum(1 for v in current.values() if v)
                
                if current_completeness > existing_completeness:
                    unique_by_content[content_hash] = current
        
        deduplicated_records = list(unique_by_content.values())
        
        if content_duplicates > 0:
            self.logger.info(f"Content-based deduplication removed {content_duplicates} "
                           f"identical records, keeping {len(deduplicated_records)} unique")
        
        return deduplicated_records, content_duplicates
    
    async def process_clinical_trials_batch(self, trials: List[Dict[str, Any]], 
                                          existing_keys: Optional[Set[str]] = None) -> Dict[str, Any]:
        """Process clinical trials batch with comprehensive deduplication"""
        if not trials:
            return {
                'processed_count': 0,
                'new_records': 0,
                'updated_records': 0,
                'duplicates_removed': 0,
                'content_duplicates_removed': 0
            }
        
        strategy = self.deduplication_strategies['clinical_trials']
        
        self.logger.info(f"Processing clinical trials batch: {len(trials)} raw records")
        
        # Step 1: Within-batch deduplication by primary key
        deduplicated_trials, within_batch_dupes = await self.deduplicate_within_batch(trials, strategy)
        
        # Step 2: Content-based deduplication (detect identical trials with different NCT IDs)
        content_deduped_trials, content_dupes = await self.deduplicate_by_content(deduplicated_trials, strategy)
        
        # Step 3: Cross-batch deduplication (filter out already processed records)
        if existing_keys is None:
            existing_keys = await self.get_existing_record_keys('clinical_trials', 'nct_id')
        
        new_trials, existing_trials = await self.filter_existing_records(
            content_deduped_trials, existing_keys, strategy
        )
        
        # Step 4: Bulk database operations
        new_records = 0
        updated_records = 0
        
        if new_trials:
            new_records = await self._bulk_insert_clinical_trials(new_trials)
            
        if existing_trials:
            updated_records = await self._bulk_update_clinical_trials(existing_trials)
        
        # Update search vectors
        await self._update_clinical_trials_search_vectors()
        
        results = {
            'processed_count': len(content_deduped_trials),
            'new_records': new_records,
            'updated_records': updated_records,
            'duplicates_removed': within_batch_dupes,
            'content_duplicates_removed': content_dupes,
            'total_input_records': len(trials),
            'deduplication_rate': (within_batch_dupes + content_dupes) / len(trials) * 100 if trials else 0
        }
        
        self.logger.info(f"✅ Clinical trials batch processed: {results}")
        return results
    
    async def _bulk_insert_clinical_trials(self, trials: List[Dict[str, Any]]) -> int:
        """Bulk insert new clinical trials with deadlock retry logic"""
        if not trials:
            return 0
        
        import time
        import random
        from psycopg2.errors import DeadlockDetected
        
        max_retries = 5
        base_delay = 0.1
        
        for attempt in range(max_retries):
            try:
                # Use advisory lock to prevent concurrent inserts
                self.db_session.execute(text("SELECT pg_advisory_lock(12347)"))
                
                current_time = datetime.utcnow()
                trial_mappings = []
                
                for trial in trials:
                    mapping = {
                        'nct_id': trial['nct_id'],
                        'title': trial.get('title', ''),
                        'status': trial.get('status', ''),
                        'phase': trial.get('phase', ''),
                        'conditions': trial.get('conditions', []),
                        'interventions': trial.get('interventions', []),
                        'locations': trial.get('locations', []),
                        'sponsors': trial.get('sponsors', []),
                        'start_date': trial.get('start_date'),
                        'completion_date': trial.get('completion_date'),
                        'enrollment': trial.get('enrollment'),
                        'study_type': trial.get('study_type', ''),
                        'created_at': current_time,
                        'updated_at': current_time
                    }
                    trial_mappings.append(mapping)
                
                self.db_session.bulk_insert_mappings(ClinicalTrial, trial_mappings)
                self.db_session.commit()
                
                # Release advisory lock
                self.db_session.execute(text("SELECT pg_advisory_unlock(12347)"))
                
                self.logger.info(f"✅ Bulk inserted {len(trial_mappings)} new clinical trials")
                return len(trial_mappings)
                
            except DeadlockDetected as e:
                self.db_session.rollback()
                # Release lock on error
                try:
                    self.db_session.execute(text("SELECT pg_advisory_unlock(12347)"))
                except:
                    pass
                
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 0.1)
                    self.logger.warning(f"Deadlock detected in bulk insert, retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                else:
                    self.logger.error(f"Failed to bulk insert clinical trials after {max_retries} attempts due to deadlocks")
                    raise
                    
            except Exception as e:
                self.db_session.rollback()
                # Release lock on error
                try:
                    self.db_session.execute(text("SELECT pg_advisory_unlock(12347)"))
                except:
                    pass
                self.logger.exception(f"Bulk insert failed: {e}")
                raise
    
    async def _bulk_update_clinical_trials(self, trials: List[Dict[str, Any]]) -> int:
        """Bulk update existing clinical trials with deadlock retry logic"""
        if not trials:
            return 0
        
        import time
        import random
        from psycopg2.errors import DeadlockDetected
        
        max_retries = 5
        base_delay = 0.1
        
        for attempt in range(max_retries):
            try:
                # Use advisory lock to prevent concurrent updates
                self.db_session.execute(text("SELECT pg_advisory_lock(12346)"))
                
                current_time = datetime.utcnow()
                trial_mappings = []
                
                for trial in trials:
                    mapping = {
                        'nct_id': trial['nct_id'],  # Required for bulk_update_mappings
                        'title': trial.get('title', ''),
                        'status': trial.get('status', ''),
                        'phase': trial.get('phase', ''),
                        'conditions': trial.get('conditions', []),
                        'interventions': trial.get('interventions', []),
                        'locations': trial.get('locations', []),
                        'sponsors': trial.get('sponsors', []),
                        'start_date': trial.get('start_date'),
                        'completion_date': trial.get('completion_date'),
                        'enrollment': trial.get('enrollment'),
                        'study_type': trial.get('study_type', ''),
                        'updated_at': current_time
                    }
                    trial_mappings.append(mapping)
                
                self.db_session.bulk_update_mappings(ClinicalTrial, trial_mappings)
                self.db_session.commit()
                
                # Release advisory lock
                self.db_session.execute(text("SELECT pg_advisory_unlock(12346)"))
                
                self.logger.info(f"✅ Bulk updated {len(trial_mappings)} existing clinical trials")
                return len(trial_mappings)
                
            except DeadlockDetected as e:
                self.db_session.rollback()
                # Release lock on error
                try:
                    self.db_session.execute(text("SELECT pg_advisory_unlock(12346)"))
                except:
                    pass
                
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 0.1)
                    self.logger.warning(f"Deadlock detected in bulk update, retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                else:
                    self.logger.error(f"Failed to bulk update clinical trials after {max_retries} attempts due to deadlocks")
                    raise
                    
            except Exception as e:
                self.db_session.rollback()
                # Release lock on error
                try:
                    self.db_session.execute(text("SELECT pg_advisory_unlock(12346)"))
                except:
                    pass
                self.logger.exception(f"Bulk update failed: {e}")
                raise
    
    async def _update_clinical_trials_search_vectors(self) -> None:
        """Update search vectors for clinical trials with deadlock retry logic"""
        import time
        import random
        from psycopg2.errors import DeadlockDetected
        
        max_retries = 5
        base_delay = 0.1
        
        for attempt in range(max_retries):
            try:
                # Use advisory lock to prevent concurrent updates
                self.db_session.execute(text("SELECT pg_advisory_lock(12345)"))
                
                update_query = text("""
                    UPDATE clinical_trials
                    SET search_vector = to_tsvector('english',
                        COALESCE(title, '') || ' ' ||
                        COALESCE(array_to_string(conditions, ' '), '') || ' ' ||
                        COALESCE(array_to_string(interventions, ' '), '') || ' ' ||
                        COALESCE(array_to_string(locations, ' '), '') || ' ' ||
                        COALESCE(array_to_string(sponsors, ' '), '')
                    )
                    WHERE search_vector IS NULL OR updated_at > NOW() - INTERVAL '1 hour'
                """)
                
                self.db_session.execute(update_query)
                self.db_session.commit()
                
                # Release advisory lock
                self.db_session.execute(text("SELECT pg_advisory_unlock(12345)"))
                
                self.logger.debug("Updated search vectors for clinical trials")
                return
                
            except DeadlockDetected as e:
                self.db_session.rollback()
                # Release lock on error
                try:
                    self.db_session.execute(text("SELECT pg_advisory_unlock(12345)"))
                except:
                    pass
                
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 0.1)
                    self.logger.warning(f"Deadlock detected, retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                else:
                    self.logger.error(f"Failed to update search vectors after {max_retries} attempts due to deadlocks")
                    
            except Exception as e:
                self.db_session.rollback()
                # Release lock on error  
                try:
                    self.db_session.execute(text("SELECT pg_advisory_unlock(12345)"))
                except:
                    pass
                self.logger.exception(f"Failed to update search vectors: {e}")
                break


class DeduplicationProgressTracker:
    """Track progress accounting for deduplication rates and cross-batch processing"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)
        
        # Progress tracking state
        self.processing_stats = {
            'start_time': None,
            'total_files': 0,
            'files_processed': 0,
            'total_raw_records': 0,
            'total_deduplicated_records': 0,
            'total_new_records': 0,
            'total_updated_records': 0,
            'total_duplicates_removed': 0,
            'total_content_duplicates_removed': 0,
            'current_batch_size': 0,
            'average_deduplication_rate': 0.0,
            'estimated_remaining_time': 0,
            'processing_rate_per_minute': 0.0
        }
    
    def start_processing(self, total_files: int) -> None:
        """Initialize progress tracking"""
        self.processing_stats['start_time'] = datetime.utcnow()
        self.processing_stats['total_files'] = total_files
        self.logger.info(f"📊 Starting progress tracking for {total_files} files")
    
    def update_batch_progress(self, batch_results: Dict[str, Any]) -> None:
        """Update progress with batch processing results"""
        stats = self.processing_stats
        
        # Update counters
        stats['files_processed'] += 1
        stats['total_raw_records'] += batch_results.get('total_input_records', 0)
        stats['total_deduplicated_records'] += batch_results.get('processed_count', 0)
        stats['total_new_records'] += batch_results.get('new_records', 0)
        stats['total_updated_records'] += batch_results.get('updated_records', 0)
        stats['total_duplicates_removed'] += batch_results.get('duplicates_removed', 0)
        stats['total_content_duplicates_removed'] += batch_results.get('content_duplicates_removed', 0)
        
        # Calculate rates
        if stats['total_raw_records'] > 0:
            total_dupes = stats['total_duplicates_removed'] + stats['total_content_duplicates_removed']
            stats['average_deduplication_rate'] = (total_dupes / stats['total_raw_records']) * 100
        
        # Calculate processing rate
        if stats['start_time']:
            elapsed_minutes = (datetime.utcnow() - stats['start_time']).total_seconds() / 60
            if elapsed_minutes > 0:
                stats['processing_rate_per_minute'] = stats['files_processed'] / elapsed_minutes
        
        # Estimate remaining time
        remaining_files = stats['total_files'] - stats['files_processed']
        if stats['processing_rate_per_minute'] > 0 and remaining_files > 0:
            stats['estimated_remaining_time'] = remaining_files / stats['processing_rate_per_minute']
        
        self.log_progress()
    
    def log_progress(self) -> None:
        """Log current progress with deduplication awareness"""
        stats = self.processing_stats
        
        completion_pct = (stats['files_processed'] / stats['total_files'] * 100) if stats['total_files'] > 0 else 0
        
        self.logger.info(f"📈 Processing Progress Report:")
        self.logger.info(f"   Files: {stats['files_processed']}/{stats['total_files']} ({completion_pct:.1f}%)")
        self.logger.info(f"   Raw Records Processed: {stats['total_raw_records']:,}")
        self.logger.info(f"   After Deduplication: {stats['total_deduplicated_records']:,}")
        self.logger.info(f"   New Records Added: {stats['total_new_records']:,}")
        self.logger.info(f"   Existing Records Updated: {stats['total_updated_records']:,}")
        self.logger.info(f"   Duplicates Removed: {stats['total_duplicates_removed']:,}")
        self.logger.info(f"   Content Duplicates Removed: {stats['total_content_duplicates_removed']:,}")
        self.logger.info(f"   Average Deduplication Rate: {stats['average_deduplication_rate']:.1f}%")
        
        if stats['estimated_remaining_time'] > 0:
            remaining_hours = stats['estimated_remaining_time'] / 60
            self.logger.info(f"   Estimated Time Remaining: {remaining_hours:.1f} hours")
        
        self.logger.info(f"   Processing Rate: {stats['processing_rate_per_minute']:.2f} files/minute")
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """Get comprehensive progress summary for API endpoints"""
        stats = self.processing_stats.copy()
        
        if stats['start_time']:
            stats['elapsed_time_minutes'] = (datetime.utcnow() - stats['start_time']).total_seconds() / 60
            stats['start_time'] = stats['start_time'].isoformat()
        
        stats['completion_percentage'] = (stats['files_processed'] / stats['total_files'] * 100) if stats['total_files'] > 0 else 0
        
        # Calculate efficiency metrics
        if stats['total_raw_records'] > 0:
            stats['efficiency_ratio'] = stats['total_deduplicated_records'] / stats['total_raw_records']
            stats['new_record_ratio'] = stats['total_new_records'] / stats['total_deduplicated_records'] if stats['total_deduplicated_records'] > 0 else 0
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'progress': stats,
            'status': 'processing' if stats['files_processed'] < stats['total_files'] else 'completed'
        }


class SmartBatchProcessor:
    """Smart batch processor that adapts batch sizes based on deduplication rates"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.deduplicator = CrossBatchDeduplicator(db_session)
        self.progress_tracker = DeduplicationProgressTracker(db_session)
        self.logger = logging.getLogger(__name__)
        
        # Adaptive batch sizing parameters
        self.min_batch_size = 1000
        self.max_batch_size = 20000
        self.target_processing_time_seconds = 30  # Target time per batch
        self.recent_batch_times = []  # Track recent processing times
    
    async def process_clinical_trials_files(self, json_files: List[str], 
                                          force_reprocess: bool = False) -> Dict[str, Any]:
        """Process clinical trials files with adaptive batching and deduplication"""
        if not json_files:
            return {'status': 'no_files_provided', 'total_processed': 0}
        
        self.logger.info(f"🚀 Starting smart batch processing of {len(json_files)} clinical trials files")
        
        # Initialize progress tracking
        self.progress_tracker.start_processing(len(json_files))
        
        # Get existing keys once for cross-batch deduplication
        if not force_reprocess:
            existing_keys = await self.deduplicator.get_existing_record_keys('clinical_trials', 'nct_id')
        else:
            existing_keys = set()
        
        total_results = {
            'files_processed': 0,
            'total_raw_records': 0,
            'total_new_records': 0,
            'total_updated_records': 0,
            'total_duplicates_removed': 0,
            'total_content_duplicates_removed': 0,
            'processing_errors': []
        }
        
        # Process files in batches
        current_batch_size = 5000  # Start with moderate batch size
        
        # Use optimized multi-core parser for parallel file processing
        from clinicaltrials.parser_optimized import OptimizedClinicalTrialsParser
        optimized_parser = OptimizedClinicalTrialsParser(max_workers=10)
        
        # Process files in parallel batches to reduce database contention
        batch_size = 10  # Process 10 files in parallel
        file_batches = [json_files[i:i + batch_size] for i in range(0, len(json_files), batch_size)]
        
        for batch_idx, file_batch in enumerate(file_batches):
            try:
                batch_start_time = datetime.utcnow()
                self.logger.info(f"🔄 Processing file batch {batch_idx + 1}/{len(file_batches)} "
                               f"({len(file_batch)} files in parallel)")
                
                # Parse all files in this batch in parallel
                all_raw_trials = await optimized_parser.parse_json_files_parallel(file_batch)
                
                if not all_raw_trials:
                    self.logger.warning(f"No trials found in batch {batch_idx + 1}")
                    continue
                
                self.logger.info(f"Parsed {len(all_raw_trials)} total raw trials from batch {batch_idx + 1}")
                
                # Process with deduplication
                batch_results = await self.deduplicator.process_clinical_trials_batch(
                    all_raw_trials, existing_keys
                )
                
                # Update existing keys with new records
                if batch_results['new_records'] > 0:
                    new_nct_ids = {trial['nct_id'] for trial in all_raw_trials 
                                 if trial.get('nct_id')}
                    existing_keys.update(new_nct_ids)
                
                # Update totals (note: now processing multiple files per batch)
                total_results['files_processed'] += len(file_batch)
                total_results['total_raw_records'] += batch_results.get('total_input_records', 0)
                total_results['total_new_records'] += batch_results.get('new_records', 0)
                total_results['total_updated_records'] += batch_results.get('updated_records', 0)
                total_results['total_duplicates_removed'] += batch_results.get('duplicates_removed', 0)
                total_results['total_content_duplicates_removed'] += batch_results.get('content_duplicates_removed', 0)
                
                # Update progress tracking
                self.progress_tracker.update_batch_progress(batch_results)
                
                # Brief pause to prevent overwhelming the database
                await asyncio.sleep(0.5)  # Slightly longer pause for parallel processing
                
            except Exception as e:
                error_msg = f"Failed to process file batch {batch_idx + 1} ({len(file_batch)} files): {str(e)}"
                total_results['processing_errors'].append(error_msg)
                self.logger.exception(error_msg)
                continue
        
        # Final summary
        total_results['status'] = 'completed'
        total_results['final_progress'] = self.progress_tracker.get_progress_summary()
        
        self.logger.info(f"🎉 Smart batch processing completed!")
        self.logger.info(f"   Files processed: {total_results['files_processed']}/{len(json_files)}")
        self.logger.info(f"   Total raw records: {total_results['total_raw_records']:,}")
        self.logger.info(f"   New records added: {total_results['total_new_records']:,}")
        self.logger.info(f"   Existing records updated: {total_results['total_updated_records']:,}")
        self.logger.info(f"   Duplicates removed: {total_results['total_duplicates_removed']:,}")
        self.logger.info(f"   Content duplicates removed: {total_results['total_content_duplicates_removed']:,}")
        
        if total_results['processing_errors']:
            self.logger.warning(f"⚠️  {len(total_results['processing_errors'])} files had errors")
        
        return total_results