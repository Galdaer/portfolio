"""
Document Handlers for Healthcare Document Processing
Provides specialized handlers for different document types with PHI compliance
"""

from .base_handler import BaseDocumentHandler, DocumentProcessingResult, DocumentMetadata
from .pdf_handler import PDFDocumentHandler
from .docx_handler import DOCXDocumentHandler
from .image_handler import ImageDocumentHandler
from .text_handler import TextDocumentHandler
from .medical_record_handler import MedicalRecordHandler

__all__ = [
    "BaseDocumentHandler",
    "DocumentProcessingResult", 
    "DocumentMetadata",
    "PDFDocumentHandler",
    "DOCXDocumentHandler",
    "ImageDocumentHandler",
    "TextDocumentHandler",
    "MedicalRecordHandler",
]