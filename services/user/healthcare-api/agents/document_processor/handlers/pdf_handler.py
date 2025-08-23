"""
PDF Document Handler for Healthcare Document Processing

Processes PDF documents with text extraction, metadata parsing, and
healthcare-specific content analysis while maintaining HIPAA compliance.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

from .base_handler import BaseDocumentHandler, DocumentMetadata, DocumentProcessingError


class PDFDocumentHandler(BaseDocumentHandler):
    """
    Handles PDF document processing for healthcare applications
    
    Provides text extraction, metadata parsing, and page-level analysis
    while maintaining healthcare compliance and PHI detection capabilities.
    """
    
    def __init__(self, enable_phi_detection: bool = True, enable_redaction: bool = False):
        """
        Initialize PDF document handler
        
        Args:
            enable_phi_detection: Whether to perform PHI detection on content
            enable_redaction: Whether to create redacted versions of content
        """
        if not PDF_AVAILABLE:
            raise ImportError("PyPDF2 is required for PDF processing. Install with: pip install PyPDF2")
        
        super().__init__(enable_phi_detection, enable_redaction)
        
        # PDF-specific configuration
        self.max_pages = 1000  # Prevent processing extremely large documents
        self.extract_annotations = True
        self.extract_form_data = True
        
    async def can_handle(self, file_path: Union[str, Path], mime_type: Optional[str] = None) -> bool:
        """
        Check if this handler can process the given PDF document
        
        Args:
            file_path: Path to the document
            mime_type: MIME type of the document (optional)
            
        Returns:
            True if this is a PDF document that can be processed
        """
        file_path = Path(file_path)
        
        # Check file extension
        if file_path.suffix.lower() == '.pdf':
            return True
            
        # Check MIME type
        if mime_type and mime_type in self.get_supported_mime_types():
            return True
            
        # Try to open as PDF to verify format
        try:
            with open(file_path, 'rb') as file:
                PyPDF2.PdfReader(file)
            return True
        except Exception:
            return False
    
    async def extract_content(self, file_path: Union[str, Path]) -> str:
        """
        Extract text content from PDF document
        
        Args:
            file_path: Path to the PDF document
            
        Returns:
            Extracted text content from all pages
            
        Raises:
            DocumentProcessingError: If PDF processing fails
        """
        file_path = Path(file_path)
        
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Check if PDF is encrypted
                if pdf_reader.is_encrypted:
                    # Try to decrypt with empty password (common for healthcare forms)
                    if not pdf_reader.decrypt(''):
                        raise DocumentProcessingError(
                            f"PDF is password protected: {file_path}",
                            str(file_path)
                        )
                
                # Check page count limits
                num_pages = len(pdf_reader.pages)
                if num_pages > self.max_pages:
                    self.logger.warning(
                        f"PDF has {num_pages} pages, exceeding limit of {self.max_pages}. "
                        f"Processing first {self.max_pages} pages only."
                    )
                    num_pages = self.max_pages
                
                # Extract text from all pages
                extracted_text = []
                for page_num in range(num_pages):
                    try:
                        page = pdf_reader.pages[page_num]
                        text = page.extract_text()
                        
                        if text.strip():
                            # Add page separator for multi-page documents
                            if page_num > 0:
                                extracted_text.append(f"\n--- Page {page_num + 1} ---\n")
                            extracted_text.append(text)
                            
                    except Exception as e:
                        self.logger.warning(f"Failed to extract text from page {page_num + 1}: {e}")
                        continue
                
                # Extract form data if available
                if self.extract_form_data and pdf_reader.metadata:
                    form_data = await self._extract_form_data(pdf_reader)
                    if form_data:
                        extracted_text.append(f"\n--- Form Data ---\n{form_data}")
                
                # Extract annotations if enabled
                if self.extract_annotations:
                    annotations = await self._extract_annotations(pdf_reader)
                    if annotations:
                        extracted_text.append(f"\n--- Annotations ---\n{annotations}")
                
                final_text = ''.join(extracted_text).strip()
                
                if not final_text:
                    self.logger.warning(f"No text extracted from PDF: {file_path}")
                    return ""
                
                return final_text
                
        except Exception as e:
            raise DocumentProcessingError(
                f"Failed to extract content from PDF: {e}",
                str(file_path),
                e
            )
    
    async def extract_metadata(self, file_path: Union[str, Path]) -> DocumentMetadata:
        """
        Extract metadata from PDF document
        
        Args:
            file_path: Path to the PDF document
            
        Returns:
            Document metadata including PDF-specific properties
        """
        file_path = Path(file_path)
        
        try:
            file_stats = file_path.stat()
            
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Extract PDF metadata
                pdf_info = pdf_reader.metadata
                num_pages = len(pdf_reader.pages)
                
                # Build custom properties from PDF metadata
                custom_properties = {
                    "page_count": num_pages,
                    "is_encrypted": pdf_reader.is_encrypted,
                    "pdf_version": getattr(pdf_reader, 'pdf_header', 'Unknown'),
                }
                
                # Add PDF metadata if available
                if pdf_info:
                    custom_properties.update({
                        "title": pdf_info.get('/Title', ''),
                        "author": pdf_info.get('/Author', ''),
                        "subject": pdf_info.get('/Subject', ''),
                        "creator": pdf_info.get('/Creator', ''),
                        "producer": pdf_info.get('/Producer', ''),
                        "creation_date": str(pdf_info.get('/CreationDate', '')),
                        "modification_date": str(pdf_info.get('/ModDate', '')),
                    })
                
                # Calculate content hash
                content_hash = await self._calculate_file_hash(file_path)
                
                return DocumentMetadata(
                    file_name=file_path.name,
                    file_size=file_stats.st_size,
                    file_type="pdf",
                    mime_type="application/pdf",
                    content_hash=content_hash,
                    created_at=datetime.fromtimestamp(file_stats.st_ctime),
                    last_modified=datetime.fromtimestamp(file_stats.st_mtime),
                    page_count=num_pages,
                    custom_properties=custom_properties,
                )
                
        except Exception as e:
            raise DocumentProcessingError(
                f"Failed to extract metadata from PDF: {e}",
                str(file_path),
                e
            )
    
    async def _extract_form_data(self, pdf_reader: PyPDF2.PdfReader) -> str:
        """
        Extract form field data from PDF
        
        Args:
            pdf_reader: PyPDF2 reader instance
            
        Returns:
            Formatted form data as text
        """
        try:
            form_data = []
            
            # Check if PDF has interactive form fields
            if "/AcroForm" in pdf_reader.trailer.get("/Root", {}):
                # Note: PyPDF2 form extraction is limited
                # For comprehensive form data extraction, consider using PyMuPDF
                form_data.append("Interactive form detected (detailed extraction requires PyMuPDF)")
            
            return '\n'.join(form_data) if form_data else ""
            
        except Exception as e:
            self.logger.warning(f"Failed to extract form data: {e}")
            return ""
    
    async def _extract_annotations(self, pdf_reader: PyPDF2.PdfReader) -> str:
        """
        Extract annotations and comments from PDF
        
        Args:
            pdf_reader: PyPDF2 reader instance
            
        Returns:
            Formatted annotations as text
        """
        try:
            annotations = []
            
            for page_num, page in enumerate(pdf_reader.pages):
                if "/Annots" in page:
                    page_annotations = page["/Annots"]
                    if page_annotations:
                        annotations.append(f"Page {page_num + 1} annotations detected")
                        # Note: Full annotation extraction requires more complex parsing
            
            return '\n'.join(annotations) if annotations else ""
            
        except Exception as e:
            self.logger.warning(f"Failed to extract annotations: {e}")
            return ""
    
    def _get_content_type(self) -> str:
        """Get the content type identifier for PDF handler"""
        return "pdf_document"
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported PDF file formats/extensions"""
        return ['.pdf']
    
    def get_supported_mime_types(self) -> List[str]:
        """Get list of supported MIME types for PDF"""
        return ['application/pdf']
    
    async def extract_pages_content(
        self,
        file_path: Union[str, Path],
        page_range: Optional[tuple] = None,
    ) -> Dict[int, str]:
        """
        Extract text content from specific pages
        
        Args:
            file_path: Path to the PDF document
            page_range: Tuple of (start_page, end_page) or None for all pages
            
        Returns:
            Dictionary mapping page numbers to extracted text
        """
        file_path = Path(file_path)
        pages_content = {}
        
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                if pdf_reader.is_encrypted and not pdf_reader.decrypt(''):
                    raise DocumentProcessingError(
                        f"Cannot decrypt PDF: {file_path}",
                        str(file_path)
                    )
                
                # Determine page range
                total_pages = len(pdf_reader.pages)
                if page_range:
                    start_page, end_page = page_range
                    start_page = max(0, min(start_page, total_pages - 1))
                    end_page = min(end_page, total_pages)
                else:
                    start_page, end_page = 0, total_pages
                
                # Extract text from specified pages
                for page_num in range(start_page, end_page):
                    try:
                        page = pdf_reader.pages[page_num]
                        text = page.extract_text()
                        pages_content[page_num + 1] = text.strip()
                    except Exception as e:
                        self.logger.warning(f"Failed to extract page {page_num + 1}: {e}")
                        pages_content[page_num + 1] = ""
                
                return pages_content
                
        except Exception as e:
            raise DocumentProcessingError(
                f"Failed to extract pages content from PDF: {e}",
                str(file_path),
                e
            )