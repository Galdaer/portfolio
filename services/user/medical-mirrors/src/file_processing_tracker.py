"""
File Processing Tracker - Avoid parsing files that have already been processed
"""

import hashlib
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy import and_, func, text
from sqlalchemy.orm import Session

from database import ProcessedFile

logger = logging.getLogger(__name__)


class FileProcessingTracker:
    """Track processed files to avoid redundant parsing operations"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)
    
    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of file for change detection"""
        sha256_hash = hashlib.sha256()
        bytes_read = 0
        
        try:
            self.logger.debug(f"📊 Starting hash calculation for: {file_path}")
            with open(file_path, "rb") as f:
                # Read file in chunks for memory efficiency
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
                    bytes_read += len(chunk)
            
            result_hash = sha256_hash.hexdigest()
            self.logger.debug(f"📊 Hash calculated for {Path(file_path).name}: {result_hash[:8]}... ({bytes_read} bytes read)")
            return result_hash
        except Exception as e:
            self.logger.error(f"Failed to calculate hash for {file_path}: {e}")
            return ""
    
    def get_file_info(self, file_path: str) -> Tuple[str, int]:
        """Get file hash and size"""
        try:
            file_stat = os.stat(file_path)
            file_hash = self.calculate_file_hash(file_path)
            return file_hash, file_stat.st_size
        except Exception as e:
            self.logger.error(f"Failed to get file info for {file_path}: {e}")
            return "", 0
    
    def is_file_already_processed(self, file_path: str, source_type: str) -> Optional[ProcessedFile]:
        """Check if file has already been processed (unchanged)"""
        try:
            file_name = Path(file_path).name
            
            # Look for existing record
            existing = (
                self.db_session.query(ProcessedFile)
                .filter(
                    and_(
                        ProcessedFile.file_name == file_name,
                        ProcessedFile.source_type == source_type
                    )
                )
                .first()
            )
            
            if not existing:
                self.logger.debug(f"No existing record found for: {file_name}")
                return None
                
            # Check if file has changed (hash comparison)
            self.logger.debug(f"Calculating hash for: {file_name}")
            current_hash, current_size = self.get_file_info(file_path)
            
            if not current_hash:
                self.logger.warning(f"Failed to calculate hash for: {file_name}")
                return None  # Error getting hash, assume needs processing
                
            self.logger.debug(f"Hash comparison for {file_name}: existing={existing.file_hash[:8]}..., current={current_hash[:8]}..., size_existing={existing.file_size}, size_current={current_size}")
            
            if existing.file_hash == current_hash and existing.file_size == current_size:
                self.logger.debug(f"✅ File already processed (unchanged): {file_name}")
                return existing
            else:
                self.logger.info(f"📝 File changed, will reprocess: {file_name} (hash or size mismatch)")
                return None
                
        except Exception as e:
            self.logger.error(f"Error checking processed file {file_path}: {e}")
            return None
    
    def mark_file_processed(
        self, 
        file_path: str, 
        source_type: str, 
        records_found: int, 
        records_processed: int, 
        processing_time: float
    ) -> ProcessedFile:
        """Mark a file as processed with metadata"""
        try:
            file_name = Path(file_path).name
            file_hash, file_size = self.get_file_info(file_path)
            
            # Check if record exists (for updates)
            existing = (
                self.db_session.query(ProcessedFile)
                .filter(
                    and_(
                        ProcessedFile.file_name == file_name,
                        ProcessedFile.source_type == source_type
                    )
                )
                .first()
            )
            
            if existing:
                # Update existing record
                existing.file_path = file_path
                existing.file_hash = file_hash
                existing.file_size = file_size
                existing.records_found = records_found
                existing.records_processed = records_processed
                existing.processing_time_seconds = processing_time
                existing.processed_at = datetime.utcnow()
                processed_file = existing
            else:
                # Create new record
                processed_file = ProcessedFile(
                    file_path=file_path,
                    file_name=file_name,
                    file_hash=file_hash,
                    file_size=file_size,
                    source_type=source_type,
                    records_found=records_found,
                    records_processed=records_processed,
                    processing_time_seconds=processing_time,
                    processed_at=datetime.utcnow()
                )
                self.db_session.add(processed_file)
            
            self.db_session.commit()
            
            self.logger.info(
                f"Marked file processed: {file_name} "
                f"({records_found} found, {records_processed} processed, "
                f"{processing_time:.2f}s)"
            )
            
            return processed_file
            
        except Exception as e:
            self.logger.error(f"Failed to mark file processed {file_path}: {e}")
            self.db_session.rollback()
            raise
    
    def filter_unprocessed_files(self, file_paths: List[str], source_type: str) -> Tuple[List[str], List[str]]:
        """Separate files into unprocessed and already processed lists"""
        unprocessed = []
        skipped = []
        
        self.logger.info(f"🔍 Checking {len(file_paths)} files for processing status...")
        
        for i, file_path in enumerate(file_paths):
            if i % 1000 == 0:
                self.logger.info(f"🔍 Progress: Checked {i}/{len(file_paths)} files...")
                
            if self.is_file_already_processed(file_path, source_type):
                skipped.append(file_path)
            else:
                unprocessed.append(file_path)
        
        self.logger.info(
            f"📋 File processing filter results: "
            f"{len(unprocessed)} need processing, {len(skipped)} already processed"
        )
        
        return unprocessed, skipped
    
    def get_processing_stats(self, source_type: Optional[str] = None) -> Dict[str, int]:
        """Get processing statistics"""
        try:
            query = self.db_session.query(
                func.count(ProcessedFile.id).label('total_files'),
                func.sum(ProcessedFile.records_found).label('total_records_found'),
                func.sum(ProcessedFile.records_processed).label('total_records_processed'),
                func.sum(ProcessedFile.processing_time_seconds).label('total_processing_time')
            )
            
            if source_type:
                query = query.filter(ProcessedFile.source_type == source_type)
            
            result = query.first()
            
            return {
                'total_files': result.total_files or 0,
                'total_records_found': result.total_records_found or 0,
                'total_records_processed': result.total_records_processed or 0,
                'total_processing_time_seconds': result.total_processing_time or 0.0
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get processing stats: {e}")
            return {
                'total_files': 0,
                'total_records_found': 0,
                'total_records_processed': 0,
                'total_processing_time_seconds': 0.0
            }
    
    def cleanup_old_records(self, days_old: int = 30) -> int:
        """Clean up old processed file records"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            deleted_count = (
                self.db_session.query(ProcessedFile)
                .filter(ProcessedFile.processed_at < cutoff_date)
                .delete()
            )
            
            self.db_session.commit()
            
            if deleted_count > 0:
                self.logger.info(f"Cleaned up {deleted_count} old processed file records")
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old records: {e}")
            self.db_session.rollback()
            return 0
    
    def reset_processing_status(self, source_type: Optional[str] = None, file_name: Optional[str] = None) -> int:
        """Reset processing status for reprocessing (useful for debugging)"""
        try:
            query = self.db_session.query(ProcessedFile)
            
            if source_type:
                query = query.filter(ProcessedFile.source_type == source_type)
                
            if file_name:
                query = query.filter(ProcessedFile.file_name == file_name)
            
            deleted_count = query.delete()
            self.db_session.commit()
            
            self.logger.info(f"Reset processing status for {deleted_count} files")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Failed to reset processing status: {e}")
            self.db_session.rollback()
            return 0


class OptimizedFileProcessor:
    """High-performance file processor with intelligent skipping"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.tracker = FileProcessingTracker(db_session)
        self.logger = logging.getLogger(__name__)
    
    def process_files_with_skipping(
        self, 
        file_paths: List[str], 
        source_type: str,
        processing_function,
        force_reprocess: bool = False
    ) -> Dict[str, int]:
        """Process files with intelligent skipping"""
        
        start_time = time.time()
        
        if force_reprocess:
            self.logger.info("Force reprocess enabled - will process all files")
            files_to_process = file_paths
            skipped_files = []
        else:
            # Filter out already processed files
            files_to_process, skipped_files = self.tracker.filter_unprocessed_files(
                file_paths, source_type
            )
        
        self.logger.info(
            f"File processing plan: {len(files_to_process)} to process, "
            f"{len(skipped_files)} skipped"
        )
        
        total_records_processed = 0
        total_records_found = 0
        processed_files_count = 0
        
        # Process unprocessed files
        for file_path in files_to_process:
            file_start_time = time.time()
            
            try:
                # Call the actual processing function
                result = processing_function(file_path)
                
                processing_time = time.time() - file_start_time
                records_found = result.get('records_found', 0)
                records_processed = result.get('records_processed', 0)
                
                # Track the file as processed
                self.tracker.mark_file_processed(
                    file_path, source_type, records_found, records_processed, processing_time
                )
                
                total_records_found += records_found
                total_records_processed += records_processed
                processed_files_count += 1
                
            except Exception as e:
                self.logger.error(f"Failed to process file {file_path}: {e}")
                continue
        
        total_time = time.time() - start_time
        
        results = {
            'total_files_provided': len(file_paths),
            'files_processed': processed_files_count,
            'files_skipped': len(skipped_files),
            'total_records_found': total_records_found,
            'total_records_processed': total_records_processed,
            'total_processing_time_seconds': total_time
        }
        
        self.logger.info(
            f"Processing complete: {processed_files_count} files processed, "
            f"{len(skipped_files)} skipped, {total_records_processed} records processed "
            f"in {total_time:.2f} seconds"
        )
        
        return results