"""
Text Document Handler for Healthcare Document Processing

Processes plain text documents with PHI detection and medical entity extraction.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from .base_handler import BaseDocumentHandler, DocumentMetadata, DocumentProcessingError


class TextDocumentHandler(BaseDocumentHandler):
    """
    Handles plain text document processing for healthcare applications

    Provides text processing, metadata parsing, and medical entity extraction
    while maintaining healthcare compliance and PHI detection capabilities.
    """

    def __init__(self, enable_phi_detection: bool = True, enable_redaction: bool = False):
        """
        Initialize text document handler

        Args:
            enable_phi_detection: Whether to perform PHI detection on content
            enable_redaction: Whether to create redacted versions of content
        """
        super().__init__(enable_phi_detection, enable_redaction)

        # Text-specific configuration
        self.max_text_size = 10_000_000  # 10MB limit for text processing
        self.supported_encodings = ["utf-8", "ascii", "iso-8859-1", "cp1252"]

    async def can_handle(self, file_path: str | Path, mime_type: str | None = None) -> bool:
        """
        Check if this handler can process the given text document

        Args:
            file_path: Path to the document
            mime_type: MIME type of the document (optional)

        Returns:
            True if this is a text document that can be processed
        """
        file_path = Path(file_path)

        # Check file extension
        text_extensions = {".txt", ".text", ".md", ".markdown", ".csv", ".tsv", ".log"}
        if file_path.suffix.lower() in text_extensions:
            return True

        # Check MIME type
        if mime_type and any(text_type in mime_type for text_type in ["text/", "application/csv"]):
            return True

        # Try to read as text to verify format
        try:
            with open(file_path, encoding="utf-8") as f:
                f.read(1024)  # Read first 1KB to test
            return True
        except (UnicodeDecodeError, PermissionError):
            # Try other encodings
            for encoding in self.supported_encodings[1:]:  # Skip utf-8 as already tried
                try:
                    with open(file_path, encoding=encoding) as f:
                        f.read(1024)
                    return True
                except (UnicodeDecodeError, PermissionError):
                    continue
            return False
        except Exception:
            return False

    async def extract_content(self, file_path: str | Path) -> str:
        """
        Extract text content from document

        Args:
            file_path: Path to the text document

        Returns:
            Extracted text content

        Raises:
            DocumentProcessingError: If text processing fails
        """
        file_path = Path(file_path)

        try:
            # Check file size
            file_size = file_path.stat().st_size
            if file_size > self.max_text_size:
                msg = f"Text file too large: {file_size} bytes (max: {self.max_text_size})"
                raise DocumentProcessingError(
                    msg,
                    str(file_path),
                )

            # Try to read with different encodings
            content = None
            used_encoding = None

            for encoding in self.supported_encodings:
                try:
                    with open(file_path, encoding=encoding) as f:
                        content = f.read()
                    used_encoding = encoding
                    break
                except UnicodeDecodeError:
                    continue

            if content is None:
                msg = f"Could not decode text file with supported encodings: {self.supported_encodings}"
                raise DocumentProcessingError(
                    msg,
                    str(file_path),
                )

            # Log encoding used for healthcare audit
            if used_encoding != "utf-8":
                self.logger.info(f"Text file read with encoding: {used_encoding}")

            # Basic text processing
            cleaned_content = self._clean_text_content(content)

            if not cleaned_content.strip():
                self.logger.warning(f"Empty or whitespace-only text file: {file_path}")
                return ""

            return cleaned_content

        except Exception as e:
            msg = f"Failed to extract content from text file: {e}"
            raise DocumentProcessingError(
                msg,
                str(file_path),
                e,
            )

    async def extract_metadata(self, file_path: str | Path) -> DocumentMetadata:
        """
        Extract metadata from text document

        Args:
            file_path: Path to the text document

        Returns:
            Document metadata including text-specific properties
        """
        file_path = Path(file_path)

        try:
            file_stats = file_path.stat()

            # Read content to analyze
            content = await self.extract_content(file_path)

            # Analyze text properties
            lines = content.splitlines()
            words = content.split()
            characters = len(content)

            # Detect text encoding
            detected_encoding = "utf-8"  # Default assumption
            for encoding in self.supported_encodings:
                try:
                    with open(file_path, encoding=encoding) as f:
                        f.read(1024)
                    detected_encoding = encoding
                    break
                except UnicodeDecodeError:
                    continue

            # Build custom properties
            custom_properties = {
                "text_statistics": {
                    "line_count": len(lines),
                    "word_count": len(words),
                    "character_count": characters,
                    "paragraph_count": len([line for line in lines if line.strip()]),
                    "average_line_length": sum(len(line) for line in lines) / len(lines) if lines else 0,
                    "average_word_length": sum(len(word) for word in words) / len(words) if words else 0,
                },
                "encoding_detected": detected_encoding,
                "content_type": self._detect_content_type(content),
                "language_hints": self._detect_language_hints(content),
            }

            # Calculate content hash
            content_hash = await self._calculate_file_hash(file_path)

            return DocumentMetadata(
                file_name=file_path.name,
                file_size=file_stats.st_size,
                file_type="text",
                mime_type=self._get_mime_type(file_path),
                content_hash=content_hash,
                created_at=datetime.fromtimestamp(file_stats.st_ctime),
                last_modified=datetime.fromtimestamp(file_stats.st_mtime),
                encoding=detected_encoding,
                custom_properties=custom_properties,
            )

        except Exception as e:
            msg = f"Failed to extract metadata from text file: {e}"
            raise DocumentProcessingError(
                msg,
                str(file_path),
                e,
            )

    def _clean_text_content(self, content: str) -> str:
        """Clean and normalize text content"""
        # Remove excessive whitespace while preserving structure
        lines = content.splitlines()
        cleaned_lines = []

        for line in lines:
            # Remove trailing whitespace but preserve leading for structure
            cleaned_line = line.rstrip()
            cleaned_lines.append(cleaned_line)

        # Join lines and normalize line endings
        cleaned_content = "\n".join(cleaned_lines)

        # Remove excessive empty lines (more than 2 consecutive)
        import re
        cleaned_content = re.sub(r"\n{3,}", "\n\n", cleaned_content)

        return cleaned_content.strip()

    def _detect_content_type(self, content: str) -> str:
        """Detect the type of text content"""
        content_lower = content.lower()

        # Medical document patterns
        medical_indicators = [
            "patient", "diagnosis", "treatment", "medication", "symptoms",
            "soap note", "chief complaint", "history", "examination",
            "assessment", "plan", "prescription", "vitals",
        ]

        # Structured data patterns
        if "," in content and content.count(",") > content.count("\n"):
            return "csv_data"
        if "\t" in content and content.count("\t") > content.count("\n"):
            return "tabular_data"
        if content.startswith("#") or "##" in content:
            return "markdown"
        if any(indicator in content_lower for indicator in medical_indicators):
            return "medical_text"
        if "log" in content_lower or any(level in content_lower for level in ["error", "warn", "info", "debug"]):
            return "log_file"
        return "plain_text"

    def _detect_language_hints(self, content: str) -> list[str]:
        """Detect language hints from content"""
        # Simple language detection based on common words
        english_indicators = ["the", "and", "is", "in", "to", "of", "a", "that", "it"]
        medical_indicators = ["patient", "treatment", "diagnosis", "medical", "health"]

        content_lower = content.lower()
        hints = []

        english_count = sum(1 for word in english_indicators if word in content_lower)
        medical_count = sum(1 for word in medical_indicators if word in content_lower)

        if english_count >= 3:
            hints.append("english")
        if medical_count >= 2:
            hints.append("medical_terminology")

        return hints

    def _get_mime_type(self, file_path: Path) -> str:
        """Get MIME type based on file extension"""
        extension_mime_map = {
            ".txt": "text/plain",
            ".text": "text/plain",
            ".md": "text/markdown",
            ".markdown": "text/markdown",
            ".csv": "text/csv",
            ".tsv": "text/tab-separated-values",
            ".log": "text/plain",
        }

        return extension_mime_map.get(file_path.suffix.lower(), "text/plain")

    def _get_content_type(self) -> str:
        """Get the content type identifier for text handler"""
        return "text_document"

    def get_supported_formats(self) -> list[str]:
        """Get list of supported text file formats/extensions"""
        return [".txt", ".text", ".md", ".markdown", ".csv", ".tsv", ".log"]

    def get_supported_mime_types(self) -> list[str]:
        """Get list of supported MIME types for text documents"""
        return [
            "text/plain",
            "text/markdown",
            "text/csv",
            "text/tab-separated-values",
            "application/csv",
        ]

    async def analyze_text_structure(self, file_path: str | Path) -> dict[str, Any]:
        """
        Analyze the structure of text content

        Args:
            file_path: Path to the text document

        Returns:
            Dictionary containing structural analysis
        """
        content = await self.extract_content(file_path)

        lines = content.splitlines()
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        sentences = [s.strip() for s in content.split(".") if s.strip()]

        return {
            "content_type": self._detect_content_type(content),
            "structure": {
                "total_lines": len(lines),
                "non_empty_lines": len([line for line in lines if line.strip()]),
                "paragraphs": len(paragraphs),
                "sentences": len(sentences),
            },
            "content_patterns": {
                "has_headers": any(line.startswith("#") for line in lines),
                "has_lists": any(line.strip().startswith(("-", "*", "+")) for line in lines),
                "has_numbers": any(line.strip()[0].isdigit() for line in lines if line.strip()),
                "has_tables": "\t" in content or "|" in content,
            },
            "language_hints": self._detect_language_hints(content),
            "medical_indicators": self._count_medical_indicators(content),
        }


    def _count_medical_indicators(self, content: str) -> dict[str, int]:
        """Count medical terminology indicators in content"""
        medical_terms = {
            "patient_references": ["patient", "pt", "client"],
            "medical_procedures": ["surgery", "procedure", "operation", "treatment"],
            "medications": ["medication", "drug", "prescription", "dosage"],
            "diagnoses": ["diagnosis", "condition", "disease", "disorder"],
            "anatomy": ["heart", "lung", "brain", "kidney", "liver"],
            "symptoms": ["pain", "fever", "nausea", "fatigue", "headache"],
        }

        content_lower = content.lower()
        indicators = {}

        for category, terms in medical_terms.items():
            count = sum(content_lower.count(term) for term in terms)
            indicators[category] = count

        return indicators
