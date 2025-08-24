"""
Enhanced Healthcare Document Processor

Integrates document parsing, PHI detection, medical entity extraction, and storage
using existing healthcare-api infrastructure for comprehensive document processing.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from agents import BaseHealthcareAgent
from core.infrastructure.agent_metrics import AgentMetricsStore
from core.infrastructure.healthcare_cache import HealthcareCacheManager
from core.infrastructure.healthcare_logger import get_healthcare_logger, log_healthcare_event

from .extractors import MedicalEntityExtractor, PHIRedactor
from .handlers import (
    DocumentProcessingResult,
    DOCXDocumentHandler,
    ImageDocumentHandler,
    PDFDocumentHandler,
)
from .storage import DocumentStorage

if TYPE_CHECKING:
    from .handlers import (
        BaseDocumentHandler,
    )

logger = get_healthcare_logger("agent.enhanced_document_processor")


class EnhancedDocumentProcessor(BaseHealthcareAgent):
    """
    Enhanced Document Processor for comprehensive healthcare document processing

    MEDICAL DISCLAIMER: This system provides administrative document processing,
    organization, and entity extraction support only. It assists healthcare
    professionals with document parsing, PHI protection, and medical entity
    organization. It does not provide medical interpretation, diagnosis, or
    treatment recommendations. All medical decisions must be made by qualified
    healthcare professionals.
    """

    def __init__(
        self,
        mcp_client: Any,
        llm_client: Any,
        config_override: dict[str, Any] | None = None,
    ):
        super().__init__("enhanced_document_processor", "enhanced_document_processor")

        self.mcp_client = mcp_client
        self.llm_client = llm_client
        self.config = config_override or {}

        # Initialize shared healthcare infrastructure tools
        self._metrics = AgentMetricsStore(agent_name="enhanced_document_processor")
        self._cache_manager = HealthcareCacheManager()

        # Initialize document handlers
        self.handlers: dict[str, BaseDocumentHandler] = {
            "pdf": PDFDocumentHandler(enable_phi_detection=True, enable_redaction=True),
            "docx": DOCXDocumentHandler(enable_phi_detection=True, enable_redaction=True),
            "image": ImageDocumentHandler(enable_phi_detection=True, enable_redaction=True),
        }

        # Initialize extractors and storage
        self.entity_extractor = MedicalEntityExtractor()
        self.phi_redactor = PHIRedactor()
        self.document_storage = DocumentStorage()

        # Processing statistics
        self.processing_stats = {
            "documents_processed": 0,
            "phi_detections": 0,
            "entities_extracted": 0,
            "storage_operations": 0,
        }

        # Healthcare disclaimers
        self.disclaimers = [
            "Document processing provides administrative support only, not medical interpretation.",
            "All extracted content should be reviewed by qualified healthcare professionals.",
            "PHI detection and redaction requires professional validation for HIPAA compliance.",
            "Medical entity extraction is for administrative organization, not clinical decision-making.",
            "All document processing maintains audit trails for healthcare compliance.",
        ]

        log_healthcare_event(
            logger,
            logging.INFO,
            "Enhanced Document Processor initialized",
            context={
                "agent": "enhanced_document_processor",
                "handlers_loaded": list(self.handlers.keys()),
                "phi_detection_enabled": True,
                "entity_extraction_enabled": True,
                "administrative_use": True,
            },
            operation_type="agent_initialization",
        )

    async def initialize(self) -> None:
        """Initialize enhanced document processor with all services"""
        try:
            await self.initialize_agent()

            # Health check all services
            health_checks = await asyncio.gather(
                self._check_scispacy_health(),
                self._check_storage_health(),
                return_exceptions=True,
            )

            services_healthy = all(
                isinstance(check, dict) and check.get("available", False)
                for check in health_checks
            )

            log_healthcare_event(
                logger,
                logging.INFO,
                "Enhanced Document Processor fully initialized",
                context={
                    "agent": "enhanced_document_processor",
                    "services_healthy": services_healthy,
                    "scispacy_available": health_checks[0].get("available", False) if isinstance(health_checks[0], dict) else False,
                    "storage_available": health_checks[1].get("available", False) if isinstance(health_checks[1], dict) else False,
                    "ready_for_operations": True,
                },
                operation_type="agent_ready",
            )

        except Exception as e:
            log_healthcare_event(
                logger,
                logging.CRITICAL,
                f"Enhanced Document Processor initialization failed: {e}",
                context={
                    "agent": "enhanced_document_processor",
                    "initialization_failed": True,
                    "error": str(e),
                },
                operation_type="agent_initialization_error",
            )
            raise

    async def _process_implementation(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Process comprehensive document analysis request

        MEDICAL DISCLAIMER: Document processing only - not medical interpretation.
        """
        session_id = request.get("session_id", "default")

        try:
            operation_type = request.get("operation", "process_document")

            if operation_type == "process_document":
                return await self._handle_document_processing(request, session_id)
            if operation_type == "batch_process":
                return await self._handle_batch_processing(request, session_id)
            if operation_type == "analyze_phi":
                return await self._handle_phi_analysis(request, session_id)
            if operation_type == "extract_entities":
                return await self._handle_entity_extraction(request, session_id)
            if operation_type == "search_documents":
                return await self._handle_document_search(request, session_id)
            return self._create_error_response(f"Unknown operation: {operation_type}", session_id)

        except Exception as e:
            logger.exception(f"Enhanced document processing error: {e}")
            return self._create_error_response(f"Document processing failed: {str(e)}", session_id)

    async def _handle_document_processing(self, request: dict[str, Any], session_id: str) -> dict[str, Any]:
        """Handle single document processing with full analysis"""
        file_path = request.get("file_path")
        document_content = request.get("document_content")
        processing_options = request.get("options", {})

        if not file_path and not document_content:
            return self._create_error_response("Either file_path or document_content required", session_id)

        try:
            # Process document based on input type
            if file_path:
                result = await self._process_document_file(Path(file_path), processing_options)
            else:
                result = await self._process_document_content(document_content, processing_options)

            # Update statistics
            self.processing_stats["documents_processed"] += 1
            if result.phi_analysis and result.phi_analysis.phi_detected:
                self.processing_stats["phi_detections"] += 1
            self.processing_stats["entities_extracted"] += len(result.medical_entities)

            # Store document if requested
            if processing_options.get("store_document", False):
                storage_result = await self.document_storage.store_document(result)
                if storage_result.get("stored", False):
                    self.processing_stats["storage_operations"] += 1

            return self._format_processing_response(result, session_id)

        except Exception as e:
            logger.exception(f"Document processing failed: {e}")
            return self._create_error_response(f"Document processing failed: {str(e)}", session_id)

    async def _handle_batch_processing(self, request: dict[str, Any], session_id: str) -> dict[str, Any]:
        """Handle batch processing of multiple documents"""
        file_paths = request.get("file_paths", [])
        processing_options = request.get("options", {})

        if not file_paths:
            return self._create_error_response("file_paths required for batch processing", session_id)

        try:
            # Process documents concurrently
            tasks = [
                self._process_document_file(Path(file_path), processing_options)
                for file_path in file_paths
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Separate successful results from exceptions
            successful_results = []
            failed_results = []

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_results.append({
                        "file_path": file_paths[i],
                        "error": str(result),
                    })
                else:
                    successful_results.append(result)

            # Update statistics
            self.processing_stats["documents_processed"] += len(successful_results)
            self.processing_stats["phi_detections"] += sum(
                1 for result in successful_results
                if result.phi_analysis and result.phi_analysis.phi_detected
            )
            self.processing_stats["entities_extracted"] += sum(
                len(result.medical_entities) for result in successful_results
            )

            return {
                "agent_type": "enhanced_document_processor",
                "session_id": session_id,
                "operation": "batch_process",
                "total_documents": len(file_paths),
                "successful": len(successful_results),
                "failed": len(failed_results),
                "results": [self._format_processing_response(result, session_id) for result in successful_results],
                "failures": failed_results,
                "processing_stats": self.processing_stats.copy(),
                "disclaimers": self.disclaimers,
                "success": True,
            }

        except Exception as e:
            logger.exception(f"Batch processing failed: {e}")
            return self._create_error_response(f"Batch processing failed: {str(e)}", session_id)

    async def _handle_phi_analysis(self, request: dict[str, Any], session_id: str) -> dict[str, Any]:
        """Handle PHI analysis of document content"""
        content = request.get("content")
        if not content:
            return self._create_error_response("content required for PHI analysis", session_id)

        try:
            phi_analysis = await self.phi_redactor.analyze_phi(content)
            phi_summary = await self.phi_redactor.get_phi_summary(content)

            return {
                "agent_type": "enhanced_document_processor",
                "session_id": session_id,
                "operation": "analyze_phi",
                "phi_detected": phi_analysis.phi_detected,
                "phi_types": phi_analysis.phi_types,
                "detection_details": phi_analysis.detection_details,
                "phi_summary": phi_summary,
                "disclaimers": self.disclaimers,
                "success": True,
            }

        except Exception as e:
            logger.exception(f"PHI analysis failed: {e}")
            return self._create_error_response(f"PHI analysis failed: {str(e)}", session_id)

    async def _handle_entity_extraction(self, request: dict[str, Any], session_id: str) -> dict[str, Any]:
        """Handle medical entity extraction from content"""
        content = request.get("content")
        entity_types = request.get("entity_types")

        if not content:
            return self._create_error_response("content required for entity extraction", session_id)

        try:
            if entity_types:
                entities_by_type = await self.entity_extractor.extract_entities_by_type(content, entity_types)
                entities = [entity for entity_list in entities_by_type.values() for entity in entity_list]
            else:
                entities = await self.entity_extractor.extract_medical_entities(content)

            clinical_summary = await self.entity_extractor.get_clinical_summary(content)

            return {
                "agent_type": "enhanced_document_processor",
                "session_id": session_id,
                "operation": "extract_entities",
                "entities": entities,
                "entity_count": len(entities),
                "clinical_summary": clinical_summary,
                "disclaimers": self.disclaimers,
                "success": True,
            }

        except Exception as e:
            logger.exception(f"Entity extraction failed: {e}")
            return self._create_error_response(f"Entity extraction failed: {str(e)}", session_id)

    async def _handle_document_search(self, request: dict[str, Any], session_id: str) -> dict[str, Any]:
        """Handle document search operations"""
        search_query = request.get("query")
        search_filters = request.get("filters", {})

        if not search_query:
            return self._create_error_response("query required for document search", session_id)

        try:
            search_results = await self.document_storage.search_documents(search_query, search_filters)

            return {
                "agent_type": "enhanced_document_processor",
                "session_id": session_id,
                "operation": "search_documents",
                "query": search_query,
                "results": search_results,
                "result_count": len(search_results),
                "disclaimers": self.disclaimers,
                "success": True,
            }

        except Exception as e:
            logger.exception(f"Document search failed: {e}")
            return self._create_error_response(f"Document search failed: {str(e)}", session_id)

    async def _process_document_file(self, file_path: Path, options: dict[str, Any]) -> DocumentProcessingResult:
        """Process a document file using appropriate handler"""
        # Determine handler based on file extension
        file_extension = file_path.suffix.lower()
        handler = None

        for _handler_type, handler_instance in self.handlers.items():
            if await handler_instance.can_handle(file_path):
                handler = handler_instance
                break

        if not handler:
            msg = f"No handler available for file type: {file_extension}"
            raise ValueError(msg)

        # Process document with handler
        result = await handler.process_document(
            file_path,
            additional_context=options.get("context", {}),
        )

        log_healthcare_event(
            logger,
            logging.INFO,
            f"Document processed: {file_path.name}",
            context={
                "file_path": str(file_path),
                "handler_type": handler.__class__.__name__,
                "phi_detected": result.phi_analysis.phi_detected if result.phi_analysis else False,
                "entity_count": len(result.medical_entities),
                "processing_time_ms": result.processing_time_ms,
            },
            operation_type="document_processing",
            is_phi_related=bool(result.phi_analysis and result.phi_analysis.phi_detected),
        )

        return result

    async def _process_document_content(self, content: str, options: dict[str, Any]) -> DocumentProcessingResult:
        """Process document content directly (text-based)"""
        from .handlers.text_handler import TextDocumentHandler

        # Use text handler for direct content processing
        if "text" not in self.handlers:
            self.handlers["text"] = TextDocumentHandler(enable_phi_detection=True, enable_redaction=True)

        # Create a temporary "file" for processing
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as temp_file:
            temp_file.write(content)
            temp_file_path = Path(temp_file.name)

        try:
            return await self.handlers["text"].process_document(
                temp_file_path,
                additional_context=options.get("context", {}),
            )
        finally:
            # Clean up temporary file
            temp_file_path.unlink(missing_ok=True)

    async def _check_scispacy_health(self) -> dict[str, Any]:
        """Check SciSpacy service health"""
        try:
            return await self.entity_extractor.health_check()
        except Exception as e:
            return {"available": False, "error": str(e)}

    async def _check_storage_health(self) -> dict[str, Any]:
        """Check document storage health"""
        try:
            return await self.document_storage.health_check()
        except Exception as e:
            return {"available": False, "error": str(e)}

    def _format_processing_response(self, result: DocumentProcessingResult, session_id: str) -> dict[str, Any]:
        """Format document processing result for API response"""
        return {
            "agent_type": "enhanced_document_processor",
            "session_id": session_id,
            "document_id": result.document_id,
            "content_type": result.content_type,
            "processing_success": result.success,
            "extracted_text": result.extracted_text,
            "structured_data": result.structured_data,
            "metadata": {
                "file_name": result.metadata.file_name,
                "file_size": result.metadata.file_size,
                "file_type": result.metadata.file_type,
                "page_count": result.metadata.page_count,
                "custom_properties": result.metadata.custom_properties,
            },
            "phi_analysis": {
                "phi_detected": result.phi_analysis.phi_detected if result.phi_analysis else False,
                "phi_types": result.phi_analysis.phi_types if result.phi_analysis else [],
                "detection_details": result.phi_analysis.detection_details if result.phi_analysis else [],
                "redacted_content": result.redacted_content,
            },
            "medical_entities": result.medical_entities,
            "entity_summary": {
                "total_entities": len(result.medical_entities),
                "high_priority_entities": [
                    entity for entity in result.medical_entities
                    if entity.get("is_high_priority", False)
                ],
            },
            "processing_warnings": result.processing_warnings,
            "processing_errors": result.processing_errors,
            "confidence_score": result.confidence_score,
            "processing_time_ms": result.processing_time_ms,
            "disclaimers": self.disclaimers,
            "success": result.success,
        }

    def _create_error_response(self, error_message: str, session_id: str) -> dict[str, Any]:
        """Create standardized error response"""
        return {
            "agent_type": "enhanced_document_processor",
            "session_id": session_id,
            "error": error_message,
            "success": False,
            "disclaimers": self.disclaimers,
            "generated_at": datetime.now().isoformat(),
        }

    async def get_processing_statistics(self) -> dict[str, Any]:
        """Get processing statistics and health information"""
        scispacy_health = await self._check_scispacy_health()
        storage_health = await self._check_storage_health()

        return {
            "processing_stats": self.processing_stats.copy(),
            "handlers_available": list(self.handlers.keys()),
            "service_health": {
                "scispacy": scispacy_health,
                "storage": storage_health,
            },
            "disclaimers": self.disclaimers,
        }
