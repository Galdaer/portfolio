"""
Base Document Handler for Healthcare Document Processing

Provides the foundational interface for all document type handlers with
HIPAA compliance, PHI detection, and healthcare-specific validation.
"""

import hashlib
import logging
import mimetypes
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from src.healthcare_mcp.phi_detection import PHIDetectionResult

from core.infrastructure.healthcare_logger import get_healthcare_logger, log_healthcare_event

from ..extractors.entity_extractor import MedicalEntityExtractor
from ..extractors.phi_redactor import PHIRedactor

logger = get_healthcare_logger("document_processor.handlers")


@dataclass
class DocumentMetadata:
    """Metadata extracted from processed documents"""

    file_name: str
    file_size: int
    file_type: str
    mime_type: str
    content_hash: str
    created_at: datetime
    last_modified: datetime | None = None
    page_count: int | None = None
    language: str | None = None
    encoding: str | None = None
    custom_properties: dict[str, Any] | None = None


@dataclass
class DocumentProcessingResult:
    """Result from document processing with healthcare compliance"""

    success: bool
    document_id: str
    content_type: str
    extracted_text: str
    structured_data: dict[str, Any]
    metadata: DocumentMetadata
    phi_analysis: PHIDetectionResult
    medical_entities: list[dict[str, Any]]
    processing_warnings: list[str]
    processing_errors: list[str]
    redacted_content: str | None = None
    confidence_score: float = 1.0
    processing_time_ms: int = 0


class BaseDocumentHandler(ABC):
    """
    Base class for all healthcare document handlers

    Provides common functionality for PHI detection, medical entity extraction,
    and healthcare compliance validation while maintaining the safety boundaries
    of administrative support only.
    """

    def __init__(self, enable_phi_detection: bool = True, enable_redaction: bool = False):
        """
        Initialize base document handler

        Args:
            enable_phi_detection: Whether to perform PHI detection on content
            enable_redaction: Whether to create redacted versions of content
        """
        self.logger = get_healthcare_logger(f"document_processor.{self.__class__.__name__}")
        self.enable_phi_detection = enable_phi_detection
        self.enable_redaction = enable_redaction

        # Initialize PHI redactor and entity extractor using existing infrastructure
        self.phi_redactor = PHIRedactor() if enable_phi_detection else None
        self.entity_extractor = MedicalEntityExtractor()

        # Healthcare compliance disclaimers
        self.disclaimers = [
            "Document processing provides administrative support only, not medical interpretation.",
            "All extracted content should be reviewed by qualified healthcare professionals.",
            "PHI detection is provided for compliance assistance but requires professional validation.",
            "Medical entity extraction is for administrative organization, not clinical decision-making.",
        ]

        log_healthcare_event(
            self.logger,
            logging.INFO,
            f"Healthcare document handler initialized: {self.__class__.__name__}",
            context={
                "handler_type": self.__class__.__name__,
                "phi_detection_enabled": enable_phi_detection,
                "redaction_enabled": enable_redaction,
                "healthcare_compliance": True,
            },
            operation_type="handler_initialization",
        )

    @abstractmethod
    async def can_handle(self, file_path: str | Path, mime_type: str | None = None) -> bool:
        """
        Check if this handler can process the given document

        Args:
            file_path: Path to the document
            mime_type: MIME type of the document (optional)

        Returns:
            True if this handler can process the document
        """

    @abstractmethod
    async def extract_content(self, file_path: str | Path) -> str:
        """
        Extract text content from the document

        Args:
            file_path: Path to the document

        Returns:
            Extracted text content

        Raises:
            DocumentProcessingError: If content extraction fails
        """

    @abstractmethod
    async def extract_metadata(self, file_path: str | Path) -> DocumentMetadata:
        """
        Extract metadata from the document

        Args:
            file_path: Path to the document

        Returns:
            Document metadata
        """

    async def process_document(
        self,
        file_path: str | Path,
        document_id: str | None = None,
        additional_context: dict[str, Any] | None = None,
    ) -> DocumentProcessingResult:
        """
        Process a document with full healthcare compliance pipeline

        Args:
            file_path: Path to the document to process
            document_id: Optional custom document identifier
            additional_context: Optional additional processing context

        Returns:
            Complete document processing result
        """
        start_time = datetime.now()
        processing_warnings = []
        processing_errors = []

        try:
            # Validate file access
            file_path = Path(file_path)
            if not file_path.exists():
                msg = f"Document not found: {file_path}"
                raise FileNotFoundError(msg)

            # Check if this handler can process the document
            mime_type = mimetypes.guess_type(str(file_path))[0]
            if not await self.can_handle(file_path, mime_type):
                msg = f"Handler {self.__class__.__name__} cannot process {file_path}"
                raise ValueError(msg)

            # Generate document ID if not provided
            if document_id is None:
                content_hash = await self._calculate_file_hash(file_path)
                document_id = f"DOC_{self.__class__.__name__}_{content_hash[:8]}_{int(start_time.timestamp())}"

            log_healthcare_event(
                self.logger,
                logging.INFO,
                f"Starting document processing: {document_id}",
                context={
                    "document_id": document_id,
                    "file_path": str(file_path),
                    "handler": self.__class__.__name__,
                    "file_size": file_path.stat().st_size,
                },
                operation_type="document_processing_start",
            )

            # Extract content and metadata
            extracted_text = await self.extract_content(file_path)
            metadata = await self.extract_metadata(file_path)

            # Perform PHI detection if enabled
            phi_analysis = None
            redacted_content = None
            if self.phi_monitor and extracted_text:
                phi_analysis = await self._analyze_phi(extracted_text)
                if self.enable_redaction and phi_analysis.phi_detected:
                    redacted_content = await self._redact_phi(extracted_text, phi_analysis)

            # Extract medical entities (placeholder for integration with SciSpacy)
            medical_entities = await self._extract_medical_entities(extracted_text)

            # Create structured data representation
            structured_data = await self._create_structured_data(
                extracted_text, metadata, additional_context or {},
            )

            # Calculate processing time
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

            # Create processing result
            result = DocumentProcessingResult(
                success=True,
                document_id=document_id,
                content_type=self._get_content_type(),
                extracted_text=extracted_text,
                structured_data=structured_data,
                metadata=metadata,
                phi_analysis=phi_analysis,
                medical_entities=medical_entities,
                processing_warnings=processing_warnings,
                processing_errors=processing_errors,
                redacted_content=redacted_content,
                processing_time_ms=processing_time,
            )

            log_healthcare_event(
                self.logger,
                logging.INFO,
                f"Document processing completed: {document_id}",
                context={
                    "document_id": document_id,
                    "processing_time_ms": processing_time,
                    "text_length": len(extracted_text),
                    "phi_detected": phi_analysis.phi_detected if phi_analysis else False,
                    "medical_entities_count": len(medical_entities),
                },
                operation_type="document_processing_complete",
            )

            return result

        except Exception as e:
            processing_errors.append(str(e))
            self.logger.exception(f"Document processing failed for {file_path}: {e}")

            # Return failed result with error information
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            return DocumentProcessingResult(
                success=False,
                document_id=document_id or f"FAILED_{int(start_time.timestamp())}",
                content_type=self._get_content_type(),
                extracted_text="",
                structured_data={},
                metadata=DocumentMetadata(
                    file_name=file_path.name if isinstance(file_path, Path) else str(file_path),
                    file_size=0,
                    file_type="unknown",
                    mime_type="",
                    content_hash="",
                    created_at=start_time,
                ),
                phi_analysis=None,
                medical_entities=[],
                processing_warnings=processing_warnings,
                processing_errors=processing_errors,
                processing_time_ms=processing_time,
            )

    async def _analyze_phi(self, content: str) -> PHIDetectionResult:
        """Analyze content for PHI using existing PHI detection infrastructure"""
        if not self.phi_redactor:
            return PHIDetectionResult(
                phi_detected=False,
                phi_types=[],
                confidence_scores=[],
                masked_text=content,
                detection_details=[],
            )

        return await self.phi_redactor.analyze_phi(content)

    async def _redact_phi(self, content: str, phi_analysis: PHIDetectionResult) -> str:
        """Create redacted version of content using existing PHI redactor"""
        if not self.phi_redactor or not phi_analysis.phi_detected:
            return content

        # Use existing PHI redaction infrastructure
        redacted_text, _ = await self.phi_redactor.redact_phi(content, redaction_level="standard")
        return redacted_text

    async def _extract_medical_entities(self, content: str) -> list[dict[str, Any]]:
        """Extract medical entities from content using existing SciSpacy integration"""
        if not content or not content.strip():
            return []

        try:
            # Use existing entity extractor
            entities = await self.entity_extractor.extract_medical_entities(
                content,
                enrich=True,  # Use enriched analysis for better context
            )

            self.logger.debug(f"Extracted {len(entities)} medical entities from content")
            return entities

        except Exception as e:
            self.logger.warning(f"Medical entity extraction failed: {e}")
            return []

    async def _create_structured_data(
        self,
        content: str,
        metadata: DocumentMetadata,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Create structured representation of document data"""
        return {
            "content_preview": content[:500] + "..." if len(content) > 500 else content,
            "content_statistics": {
                "character_count": len(content),
                "word_count": len(content.split()) if content else 0,
                "line_count": len(content.splitlines()) if content else 0,
            },
            "document_type": self._get_content_type(),
            "processing_metadata": {
                "handler": self.__class__.__name__,
                "processed_at": datetime.now().isoformat(),
                "context": context,
            },
            "file_metadata": {
                "name": metadata.file_name,
                "size": metadata.file_size,
                "type": metadata.file_type,
                "mime_type": metadata.mime_type,
            },
        }

    async def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file content"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    @abstractmethod
    def _get_content_type(self) -> str:
        """Get the content type identifier for this handler"""

    def get_supported_formats(self) -> list[str]:
        """Get list of supported file formats/extensions"""
        return []

    def get_supported_mime_types(self) -> list[str]:
        """Get list of supported MIME types"""
        return []


class DocumentProcessingError(Exception):
    """Exception raised when document processing fails"""

    def __init__(self, message: str, document_path: str | None = None, cause: Exception | None = None):
        super().__init__(message)
        self.document_path = document_path
        self.cause = cause
