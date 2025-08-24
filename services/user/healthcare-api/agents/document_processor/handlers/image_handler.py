"""
Image Document Handler with OCR for Healthcare Document Processing

Processes image documents (PNG, JPEG, TIFF) with OCR text extraction, metadata parsing,
and healthcare-specific content analysis while maintaining HIPAA compliance.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from PIL import ExifTags, Image
    from PIL.ExifTags import TAGS
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

from .base_handler import BaseDocumentHandler, DocumentMetadata, DocumentProcessingError


class ImageDocumentHandler(BaseDocumentHandler):
    """
    Handles image document processing with OCR for healthcare applications

    Provides OCR text extraction, metadata parsing, image analysis, and structured
    content analysis while maintaining healthcare compliance and PHI detection capabilities.
    """

    def __init__(self, enable_phi_detection: bool = True, enable_redaction: bool = False):
        """
        Initialize image document handler with OCR capabilities

        Args:
            enable_phi_detection: Whether to perform PHI detection on content
            enable_redaction: Whether to create redacted versions of content
        """
        if not PIL_AVAILABLE:
            raise ImportError("Pillow is required for image processing. Install with: pip install Pillow")

        if not TESSERACT_AVAILABLE:
            self.logger.warning(
                "pytesseract not available. OCR text extraction will be disabled. "
                "Install with: pip install pytesseract",
            )

        super().__init__(enable_phi_detection, enable_redaction)

        # OCR and image processing configuration
        self.ocr_enabled = TESSERACT_AVAILABLE
        self.max_image_size = (4000, 4000)  # Max dimensions to prevent memory issues
        self.supported_formats = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".gif"}

        # OCR language configuration (can be expanded for multilingual support)
        self.ocr_language = "eng"  # English by default
        self.ocr_config = "--oem 3 --psm 6"  # OCR Engine Mode 3, Page Segmentation Mode 6

        # Image preprocessing settings
        self.enable_preprocessing = True
        self.dpi_threshold = 150  # Minimum DPI for good OCR results

    async def can_handle(self, file_path: str | Path, mime_type: str | None = None) -> bool:
        """
        Check if this handler can process the given image document

        Args:
            file_path: Path to the document
            mime_type: MIME type of the document (optional)

        Returns:
            True if this is an image document that can be processed
        """
        file_path = Path(file_path)

        # Check file extension
        if file_path.suffix.lower() in self.supported_formats:
            return True

        # Check MIME type
        if mime_type and any(supported in mime_type for supported in ["image/"]):
            return True

        # Try to open as image to verify format
        try:
            with Image.open(file_path) as img:
                img.verify()
            return True
        except Exception:
            return False

    async def extract_content(self, file_path: str | Path) -> str:
        """
        Extract text content from image using OCR

        Args:
            file_path: Path to the image document

        Returns:
            OCR-extracted text content from the image

        Raises:
            DocumentProcessingError: If image processing or OCR fails
        """
        if not self.ocr_enabled:
            self.logger.warning("OCR is not available. Returning empty content for image.")
            return ""

        file_path = Path(file_path)

        try:
            with Image.open(file_path) as image:
                # Preprocess image for better OCR results
                processed_image = await self._preprocess_image(image)

                # Perform OCR text extraction
                ocr_text = pytesseract.image_to_string(
                    processed_image,
                    lang=self.ocr_language,
                    config=self.ocr_config,
                )

                # Clean up OCR text
                cleaned_text = await self._clean_ocr_text(ocr_text)

                if not cleaned_text.strip():
                    self.logger.warning(f"No text extracted from image: {file_path}")
                    return ""

                return cleaned_text

        except Exception as e:
            msg = f"Failed to extract content from image: {e}"
            raise DocumentProcessingError(
                msg,
                str(file_path),
                e,
            )

    async def extract_metadata(self, file_path: str | Path) -> DocumentMetadata:
        """
        Extract metadata from image document

        Args:
            file_path: Path to the image document

        Returns:
            Document metadata including image-specific properties
        """
        file_path = Path(file_path)

        try:
            file_stats = file_path.stat()

            with Image.open(file_path) as image:
                # Extract basic image properties
                width, height = image.size
                format_name = image.format
                mode = image.mode

                # Extract EXIF data if available
                exif_data = {}
                if hasattr(image, "_getexif") and image._getexif() is not None:
                    exif = image._getexif()
                    if exif:
                        for tag_id, value in exif.items():
                            tag = TAGS.get(tag_id, tag_id)
                            exif_data[str(tag)] = str(value)

                # Get OCR confidence if OCR is available
                ocr_confidence = 0.0
                if self.ocr_enabled:
                    try:
                        processed_image = await self._preprocess_image(image)
                        ocr_data = pytesseract.image_to_data(
                            processed_image,
                            output_type=pytesseract.Output.DICT,
                        )
                        # Calculate average confidence for text regions
                        confidences = [int(conf) for conf in ocr_data["conf"] if int(conf) > 0]
                        ocr_confidence = sum(confidences) / len(confidences) if confidences else 0.0
                    except Exception as e:
                        self.logger.warning(f"Failed to calculate OCR confidence: {e}")

                # Build custom properties
                custom_properties = {
                    "image_width": width,
                    "image_height": height,
                    "image_format": format_name,
                    "color_mode": mode,
                    "pixel_count": width * height,
                    "ocr_confidence": ocr_confidence,
                    "ocr_enabled": self.ocr_enabled,
                }

                # Add EXIF data
                if exif_data:
                    custom_properties["exif_data"] = exif_data

                # Detect if image has DPI information
                dpi = image.info.get("dpi", None)
                if dpi:
                    custom_properties["dpi"] = dpi
                    custom_properties["dpi_x"] = dpi[0]
                    custom_properties["dpi_y"] = dpi[1]

                # Calculate content hash
                content_hash = await self._calculate_file_hash(file_path)

                return DocumentMetadata(
                    file_name=file_path.name,
                    file_size=file_stats.st_size,
                    file_type="image",
                    mime_type=f"image/{format_name.lower()}" if format_name else "image/unknown",
                    content_hash=content_hash,
                    created_at=datetime.fromtimestamp(file_stats.st_ctime),
                    last_modified=datetime.fromtimestamp(file_stats.st_mtime),
                    custom_properties=custom_properties,
                )

        except Exception as e:
            msg = f"Failed to extract metadata from image: {e}"
            raise DocumentProcessingError(
                msg,
                str(file_path),
                e,
            )

    async def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for better OCR results

        Args:
            image: PIL Image object

        Returns:
            Preprocessed PIL Image object
        """
        if not self.enable_preprocessing:
            return image

        try:
            # Convert to RGB if necessary (for consistency)
            if image.mode != "RGB":
                image = image.convert("RGB")

            # Resize if image is too large
            width, height = image.size
            if width > self.max_image_size[0] or height > self.max_image_size[1]:
                image.thumbnail(self.max_image_size, Image.Resampling.LANCZOS)
                self.logger.info(f"Resized image from {width}x{height} to {image.size}")

            # Check and enhance DPI if needed
            dpi = image.info.get("dpi", (72, 72))
            current_dpi = max(dpi) if isinstance(dpi, list | tuple) else dpi

            if current_dpi < self.dpi_threshold:
                # Scale up image to improve DPI for OCR
                scale_factor = self.dpi_threshold / current_dpi
                new_size = (int(image.width * scale_factor), int(image.height * scale_factor))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
                self.logger.info(f"Enhanced image DPI from {current_dpi} to {self.dpi_threshold}")

            return image

        except Exception as e:
            self.logger.warning(f"Image preprocessing failed, using original: {e}")
            return image

    async def _clean_ocr_text(self, ocr_text: str) -> str:
        """
        Clean and format OCR-extracted text

        Args:
            ocr_text: Raw OCR text output

        Returns:
            Cleaned and formatted text
        """
        if not ocr_text:
            return ""

        # Remove excessive whitespace and normalize line endings
        lines = [line.strip() for line in ocr_text.splitlines()]
        cleaned_lines = [line for line in lines if line and len(line) > 1]  # Remove single chars

        # Join lines with proper spacing
        cleaned_text = "\n".join(cleaned_lines)

        # Remove common OCR artifacts

        # Apply replacements cautiously (context-dependent)
        # for old, new in replacements:
        #     cleaned_text = cleaned_text.replace(old, new)

        return cleaned_text.strip()

    def _get_content_type(self) -> str:
        """Get the content type identifier for image handler"""
        return "image_document"

    def get_supported_formats(self) -> list[str]:
        """Get list of supported image file formats/extensions"""
        return list(self.supported_formats)

    def get_supported_mime_types(self) -> list[str]:
        """Get list of supported MIME types for images"""
        return [
            "image/jpeg",
            "image/jpg",
            "image/png",
            "image/tiff",
            "image/bmp",
            "image/gif",
        ]

    async def extract_ocr_data(self, file_path: str | Path) -> dict[str, Any]:
        """
        Extract detailed OCR data including word-level confidence and positioning

        Args:
            file_path: Path to the image document

        Returns:
            Dictionary containing detailed OCR analysis
        """
        if not self.ocr_enabled:
            return {"error": "OCR not available"}

        file_path = Path(file_path)

        try:
            with Image.open(file_path) as image:
                processed_image = await self._preprocess_image(image)

                # Get detailed OCR data
                ocr_data = pytesseract.image_to_data(
                    processed_image,
                    output_type=pytesseract.Output.DICT,
                    lang=self.ocr_language,
                    config=self.ocr_config,
                )

                # Process OCR data into structured format
                words = []
                for i, word in enumerate(ocr_data["text"]):
                    if word.strip():  # Skip empty words
                        word_data = {
                            "word": word,
                            "confidence": int(ocr_data["conf"][i]),
                            "left": int(ocr_data["left"][i]),
                            "top": int(ocr_data["top"][i]),
                            "width": int(ocr_data["width"][i]),
                            "height": int(ocr_data["height"][i]),
                            "page_num": int(ocr_data["page_num"][i]),
                            "block_num": int(ocr_data["block_num"][i]),
                            "par_num": int(ocr_data["par_num"][i]),
                            "line_num": int(ocr_data["line_num"][i]),
                            "word_num": int(ocr_data["word_num"][i]),
                        }
                        words.append(word_data)

                # Calculate overall statistics
                confidences = [w["confidence"] for w in words if w["confidence"] > 0]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0

                return {
                    "words": words,
                    "total_words": len(words),
                    "average_confidence": avg_confidence,
                    "high_confidence_words": len([c for c in confidences if c > 80]),
                    "low_confidence_words": len([c for c in confidences if c < 60]),
                    "image_dimensions": processed_image.size,
                }

        except Exception as e:
            msg = f"Failed to extract OCR data from image: {e}"
            raise DocumentProcessingError(
                msg,
                str(file_path),
                e,
            )

    async def detect_document_regions(self, file_path: str | Path) -> dict[str, Any]:
        """
        Detect and analyze different regions in the document image

        Args:
            file_path: Path to the image document

        Returns:
            Dictionary containing detected regions and their properties
        """
        if not self.ocr_enabled:
            return {"error": "OCR not available for region detection"}

        file_path = Path(file_path)

        try:
            with Image.open(file_path) as image:
                processed_image = await self._preprocess_image(image)

                # Get block-level information
                ocr_data = pytesseract.image_to_data(
                    processed_image,
                    output_type=pytesseract.Output.DICT,
                    lang=self.ocr_language,
                    config=self.ocr_config,
                )

                # Group by blocks to identify regions
                blocks = {}
                for i, block_num in enumerate(ocr_data["block_num"]):
                    if block_num not in blocks:
                        blocks[block_num] = {
                            "block_id": block_num,
                            "left": int(ocr_data["left"][i]),
                            "top": int(ocr_data["top"][i]),
                            "width": int(ocr_data["width"][i]),
                            "height": int(ocr_data["height"][i]),
                            "text": [],
                            "confidence": [],
                        }

                    word = ocr_data["text"][i].strip()
                    confidence = int(ocr_data["conf"][i])

                    if word and confidence > 0:
                        blocks[block_num]["text"].append(word)
                        blocks[block_num]["confidence"].append(confidence)

                # Process blocks into regions
                regions = []
                for block_id, block_data in blocks.items():
                    if block_data["text"]:
                        region_text = " ".join(block_data["text"])
                        avg_confidence = sum(block_data["confidence"]) / len(block_data["confidence"])

                        regions.append({
                            "region_id": block_id,
                            "text": region_text,
                            "bounding_box": {
                                "left": block_data["left"],
                                "top": block_data["top"],
                                "width": block_data["width"],
                                "height": block_data["height"],
                            },
                            "confidence": avg_confidence,
                            "word_count": len(block_data["text"]),
                        })

                return {
                    "regions": regions,
                    "total_regions": len(regions),
                    "image_dimensions": processed_image.size,
                }

        except Exception as e:
            msg = f"Failed to detect document regions in image: {e}"
            raise DocumentProcessingError(
                msg,
                str(file_path),
                e,
            )
