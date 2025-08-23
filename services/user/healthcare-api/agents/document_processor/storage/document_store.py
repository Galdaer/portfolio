"""
Document Storage for Healthcare Document Processing

Integrates with existing PostgreSQL infrastructure to provide document storage,
retrieval, and search capabilities with HIPAA compliance.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.infrastructure.healthcare_logger import get_healthcare_logger, log_healthcare_event
from core.database.database_manager import DatabaseManager
from ..handlers.base_handler import DocumentProcessingResult


class DocumentStorage:
    """
    Document storage and retrieval using existing PostgreSQL infrastructure
    
    Provides HIPAA-compliant document storage with full-text search,
    metadata indexing, and audit logging capabilities.
    """
    
    def __init__(self):
        """Initialize document storage with database connection"""
        self.logger = get_healthcare_logger("document_processor.storage")
        self.db_manager = DatabaseManager()
        
        # Storage configuration
        self.max_content_size = 50_000_000  # 50MB limit for document content
        self.search_limit = 100  # Default search result limit
        
        # Initialize storage tables if needed
        self._ensure_tables_exist = False
        
        log_healthcare_event(
            self.logger,
            logging.INFO,
            "Document storage initialized with PostgreSQL backend",
            context={
                "storage_type": "postgresql",
                "hipaa_compliant": True,
                "full_text_search": True,
                "audit_logging": True,
            },
            operation_type="storage_initialization",
        )
    
    async def store_document(self, document_result: DocumentProcessingResult) -> Dict[str, Any]:
        """
        Store processed document in database
        
        Args:
            document_result: Result from document processing
            
        Returns:
            Storage operation result with document ID
        """
        try:
            await self._ensure_storage_tables()
            
            # Prepare document data for storage
            storage_data = {
                'document_id': document_result.document_id,
                'content_type': document_result.content_type,
                'file_name': document_result.metadata.file_name,
                'file_size': document_result.metadata.file_size,
                'file_type': document_result.metadata.file_type,
                'mime_type': document_result.metadata.mime_type,
                'content_hash': document_result.metadata.content_hash,
                'extracted_text': document_result.extracted_text,
                'structured_data': json.dumps(document_result.structured_data),
                'metadata': json.dumps({
                    'page_count': document_result.metadata.page_count,
                    'encoding': document_result.metadata.encoding,
                    'language': document_result.metadata.language,
                    'custom_properties': document_result.metadata.custom_properties,
                }),
                'phi_detected': document_result.phi_analysis.phi_detected if document_result.phi_analysis else False,
                'phi_types': json.dumps(document_result.phi_analysis.phi_types if document_result.phi_analysis else []),
                'medical_entities': json.dumps(document_result.medical_entities),
                'entity_count': len(document_result.medical_entities),
                'processing_warnings': json.dumps(document_result.processing_warnings),
                'processing_errors': json.dumps(document_result.processing_errors),
                'confidence_score': document_result.confidence_score,
                'processing_time_ms': document_result.processing_time_ms,
                'created_at': document_result.metadata.created_at,
                'stored_at': datetime.now(),
            }
            
            # Check content size
            if len(document_result.extracted_text) > self.max_content_size:
                self.logger.warning(
                    f"Document content exceeds size limit: {len(document_result.extracted_text)} > {self.max_content_size}"
                )
                storage_data['extracted_text'] = document_result.extracted_text[:self.max_content_size] + "\n[TRUNCATED]"
                storage_data['content_truncated'] = True
            else:
                storage_data['content_truncated'] = False
            
            # Store in database
            async with self.db_manager.get_connection() as conn:
                # Insert main document record
                insert_query = """
                INSERT INTO healthcare_documents (
                    document_id, content_type, file_name, file_size, file_type, mime_type,
                    content_hash, extracted_text, structured_data, metadata, phi_detected,
                    phi_types, medical_entities, entity_count, processing_warnings,
                    processing_errors, confidence_score, processing_time_ms, created_at,
                    stored_at, content_truncated, search_vector
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15,
                    $16, $17, $18, $19, $20, $21, to_tsvector('english', $8)
                )
                ON CONFLICT (document_id) DO UPDATE SET
                    extracted_text = EXCLUDED.extracted_text,
                    structured_data = EXCLUDED.structured_data,
                    metadata = EXCLUDED.metadata,
                    phi_detected = EXCLUDED.phi_detected,
                    phi_types = EXCLUDED.phi_types,
                    medical_entities = EXCLUDED.medical_entities,
                    entity_count = EXCLUDED.entity_count,
                    processing_warnings = EXCLUDED.processing_warnings,
                    processing_errors = EXCLUDED.processing_errors,
                    confidence_score = EXCLUDED.confidence_score,
                    processing_time_ms = EXCLUDED.processing_time_ms,
                    stored_at = EXCLUDED.stored_at,
                    content_truncated = EXCLUDED.content_truncated,
                    search_vector = to_tsvector('english', EXCLUDED.extracted_text)
                RETURNING id, document_id
                """
                
                result = await conn.fetchrow(
                    insert_query,
                    storage_data['document_id'],
                    storage_data['content_type'],
                    storage_data['file_name'],
                    storage_data['file_size'],
                    storage_data['file_type'],
                    storage_data['mime_type'],
                    storage_data['content_hash'],
                    storage_data['extracted_text'],
                    storage_data['structured_data'],
                    storage_data['metadata'],
                    storage_data['phi_detected'],
                    storage_data['phi_types'],
                    storage_data['medical_entities'],
                    storage_data['entity_count'],
                    storage_data['processing_warnings'],
                    storage_data['processing_errors'],
                    storage_data['confidence_score'],
                    storage_data['processing_time_ms'],
                    storage_data['created_at'],
                    storage_data['stored_at'],
                    storage_data['content_truncated'],
                )
                
                if result:
                    db_id, document_id = result
                    
                    # Store PHI analysis details if detected
                    if document_result.phi_analysis and document_result.phi_analysis.phi_detected:
                        await self._store_phi_details(conn, db_id, document_result.phi_analysis)
                    
                    log_healthcare_event(
                        self.logger,
                        logging.INFO,
                        f"Document stored successfully: {document_id}",
                        context={
                            "document_id": document_id,
                            "file_name": storage_data['file_name'],
                            "content_type": storage_data['content_type'],
                            "phi_detected": storage_data['phi_detected'],
                            "entity_count": storage_data['entity_count'],
                            "database_id": db_id,
                        },
                        operation_type="document_storage",
                        is_phi_related=storage_data['phi_detected'],
                    )
                    
                    return {
                        "stored": True,
                        "document_id": document_id,
                        "database_id": db_id,
                        "content_truncated": storage_data['content_truncated'],
                    }
                else:
                    raise Exception("Failed to insert document into database")
            
        except Exception as e:
            self.logger.exception(f"Document storage failed: {e}")
            return {
                "stored": False,
                "error": str(e),
                "document_id": document_result.document_id,
            }
    
    async def retrieve_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve document by ID
        
        Args:
            document_id: Document identifier
            
        Returns:
            Document data or None if not found
        """
        try:
            async with self.db_manager.get_connection() as conn:
                query = """
                SELECT 
                    id, document_id, content_type, file_name, file_size, file_type,
                    mime_type, content_hash, extracted_text, structured_data, metadata,
                    phi_detected, phi_types, medical_entities, entity_count,
                    processing_warnings, processing_errors, confidence_score,
                    processing_time_ms, created_at, stored_at, content_truncated
                FROM healthcare_documents 
                WHERE document_id = $1
                """
                
                result = await conn.fetchrow(query, document_id)
                
                if result:
                    document_data = dict(result)
                    # Parse JSON fields
                    json_fields = ['structured_data', 'metadata', 'phi_types', 'medical_entities', 'processing_warnings', 'processing_errors']
                    for field in json_fields:
                        if document_data[field]:
                            document_data[field] = json.loads(document_data[field])
                    
                    # Get PHI details if present
                    if document_data['phi_detected']:
                        phi_details = await self._retrieve_phi_details(conn, document_data['id'])
                        document_data['phi_details'] = phi_details
                    
                    log_healthcare_event(
                        self.logger,
                        logging.INFO,
                        f"Document retrieved: {document_id}",
                        context={
                            "document_id": document_id,
                            "content_type": document_data['content_type'],
                            "file_name": document_data['file_name'],
                        },
                        operation_type="document_retrieval",
                    )
                    
                    return document_data
                else:
                    return None
            
        except Exception as e:
            self.logger.exception(f"Document retrieval failed for {document_id}: {e}")
            return None
    
    async def search_documents(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search documents using full-text search
        
        Args:
            query: Search query string
            filters: Optional filters (content_type, phi_detected, etc.)
            
        Returns:
            List of matching document summaries
        """
        try:
            filters = filters or {}
            limit = min(filters.get('limit', self.search_limit), 500)  # Cap at 500 results
            
            # Build search query
            base_query = """
            SELECT 
                document_id, content_type, file_name, file_type, phi_detected,
                entity_count, confidence_score, created_at, stored_at,
                ts_headline('english', extracted_text, plainto_tsquery($1), 'MaxWords=50') as highlight,
                ts_rank(search_vector, plainto_tsquery($1)) as rank
            FROM healthcare_documents 
            WHERE search_vector @@ plainto_tsquery($1)
            """
            
            params = [query]
            param_count = 1
            
            # Add filters
            if filters.get('content_type'):
                param_count += 1
                base_query += f" AND content_type = ${param_count}"
                params.append(filters['content_type'])
            
            if filters.get('phi_detected') is not None:
                param_count += 1
                base_query += f" AND phi_detected = ${param_count}"
                params.append(filters['phi_detected'])
            
            if filters.get('file_type'):
                param_count += 1
                base_query += f" AND file_type = ${param_count}"
                params.append(filters['file_type'])
            
            # Add date range filters
            if filters.get('created_after'):
                param_count += 1
                base_query += f" AND created_at >= ${param_count}"
                params.append(filters['created_after'])
            
            if filters.get('created_before'):
                param_count += 1
                base_query += f" AND created_at <= ${param_count}"
                params.append(filters['created_before'])
            
            # Order and limit
            base_query += f" ORDER BY rank DESC, stored_at DESC LIMIT ${param_count + 1}"
            params.append(limit)
            
            async with self.db_manager.get_connection() as conn:
                results = await conn.fetch(base_query, *params)
                
                search_results = []
                for row in results:
                    result_data = dict(row)
                    search_results.append(result_data)
                
                log_healthcare_event(
                    self.logger,
                    logging.INFO,
                    f"Document search completed: {len(search_results)} results",
                    context={
                        "query": query,
                        "result_count": len(search_results),
                        "filters": filters,
                    },
                    operation_type="document_search",
                )
                
                return search_results
            
        except Exception as e:
            self.logger.exception(f"Document search failed: {e}")
            return []
    
    async def get_document_statistics(self) -> Dict[str, Any]:
        """Get storage statistics"""
        try:
            async with self.db_manager.get_connection() as conn:
                stats_query = """
                SELECT 
                    COUNT(*) as total_documents,
                    COUNT(CASE WHEN phi_detected THEN 1 END) as documents_with_phi,
                    AVG(entity_count) as avg_entities_per_document,
                    AVG(confidence_score) as avg_confidence_score,
                    COUNT(DISTINCT content_type) as content_types,
                    COUNT(DISTINCT file_type) as file_types,
                    MIN(stored_at) as oldest_document,
                    MAX(stored_at) as newest_document
                FROM healthcare_documents
                """
                
                stats = await conn.fetchrow(stats_query)
                
                return dict(stats) if stats else {}
                
        except Exception as e:
            self.logger.exception(f"Failed to get document statistics: {e}")
            return {}
    
    async def _ensure_storage_tables(self):
        """Ensure storage tables exist"""
        if self._ensure_tables_exist:
            return
        
        try:
            async with self.db_manager.get_connection() as conn:
                # Create main documents table
                create_table_query = """
                CREATE TABLE IF NOT EXISTS healthcare_documents (
                    id SERIAL PRIMARY KEY,
                    document_id VARCHAR(255) UNIQUE NOT NULL,
                    content_type VARCHAR(100) NOT NULL,
                    file_name TEXT NOT NULL,
                    file_size BIGINT NOT NULL,
                    file_type VARCHAR(50) NOT NULL,
                    mime_type VARCHAR(100) NOT NULL,
                    content_hash VARCHAR(64) NOT NULL,
                    extracted_text TEXT,
                    structured_data JSONB,
                    metadata JSONB,
                    phi_detected BOOLEAN DEFAULT FALSE,
                    phi_types JSONB,
                    medical_entities JSONB,
                    entity_count INTEGER DEFAULT 0,
                    processing_warnings JSONB,
                    processing_errors JSONB,
                    confidence_score FLOAT DEFAULT 1.0,
                    processing_time_ms INTEGER DEFAULT 0,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    stored_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    content_truncated BOOLEAN DEFAULT FALSE,
                    search_vector TSVECTOR
                );
                
                -- Create indexes for performance
                CREATE INDEX IF NOT EXISTS idx_healthcare_documents_document_id ON healthcare_documents(document_id);
                CREATE INDEX IF NOT EXISTS idx_healthcare_documents_content_type ON healthcare_documents(content_type);
                CREATE INDEX IF NOT EXISTS idx_healthcare_documents_phi_detected ON healthcare_documents(phi_detected);
                CREATE INDEX IF NOT EXISTS idx_healthcare_documents_stored_at ON healthcare_documents(stored_at);
                CREATE INDEX IF NOT EXISTS idx_healthcare_documents_search_vector ON healthcare_documents USING GIN(search_vector);
                
                -- Create PHI details table
                CREATE TABLE IF NOT EXISTS healthcare_document_phi_details (
                    id SERIAL PRIMARY KEY,
                    document_id INTEGER REFERENCES healthcare_documents(id) ON DELETE CASCADE,
                    phi_type VARCHAR(100) NOT NULL,
                    detected_text TEXT NOT NULL,
                    start_position INTEGER NOT NULL,
                    end_position INTEGER NOT NULL,
                    confidence_score FLOAT NOT NULL,
                    detection_method VARCHAR(100) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
                
                CREATE INDEX IF NOT EXISTS idx_phi_details_document_id ON healthcare_document_phi_details(document_id);
                CREATE INDEX IF NOT EXISTS idx_phi_details_phi_type ON healthcare_document_phi_details(phi_type);
                """
                
                await conn.execute(create_table_query)
                self._ensure_tables_exist = True
                
                self.logger.info("Healthcare document storage tables verified/created")
                
        except Exception as e:
            self.logger.exception(f"Failed to ensure storage tables: {e}")
            raise
    
    async def _store_phi_details(self, conn, document_db_id: int, phi_analysis) -> None:
        """Store detailed PHI detection information"""
        try:
            for detail in phi_analysis.detection_details:
                await conn.execute("""
                    INSERT INTO healthcare_document_phi_details 
                    (document_id, phi_type, detected_text, start_position, end_position, confidence_score, detection_method)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, 
                document_db_id,
                detail.get('type', 'unknown'),
                detail.get('text', ''),
                detail.get('start', 0),
                detail.get('end', 0),
                detail.get('confidence', 0.0),
                'automated_detection'
                )
        except Exception as e:
            self.logger.warning(f"Failed to store PHI details: {e}")
    
    async def _retrieve_phi_details(self, conn, document_db_id: int) -> List[Dict[str, Any]]:
        """Retrieve PHI detection details"""
        try:
            results = await conn.fetch("""
                SELECT phi_type, detected_text, start_position, end_position, 
                       confidence_score, detection_method, created_at
                FROM healthcare_document_phi_details
                WHERE document_id = $1
                ORDER BY start_position
            """, document_db_id)
            
            return [dict(row) for row in results]
        except Exception as e:
            self.logger.warning(f"Failed to retrieve PHI details: {e}")
            return []
    
    async def health_check(self) -> Dict[str, Any]:
        """Check document storage health"""
        try:
            async with self.db_manager.get_connection() as conn:
                # Test database connectivity and table existence
                result = await conn.fetchval("SELECT COUNT(*) FROM healthcare_documents")
                
                return {
                    "available": True,
                    "database_connection": "healthy",
                    "document_count": result,
                    "tables_exist": True,
                }
                
        except Exception as e:
            return {
                "available": False,
                "error": str(e),
                "database_connection": "failed",
            }