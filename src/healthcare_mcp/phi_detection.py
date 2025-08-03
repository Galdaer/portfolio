"""
PHI Detection and Masking Module
Detects and masks Protected Health Information (PHI) for HIPAA compliance
"""

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from io import StringIO
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
    AnalyzerEngineType = type[AnalyzerEngine]
    AnonymizerEngineType = type[AnonymizerEngine]
else:
    AnalyzerEngine: Any | None = None
    AnonymizerEngine: Any | None = None
    AnalyzerEngineType: Any | None = None
    AnonymizerEngineType: Any | None = None

try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False
    logging.warning("Presidio not available, using basic PHI detection")

# Configure logging
logger = logging.getLogger(__name__)

# Constants for PHI detection and redaction
REDACTION_LENGTH_THRESHOLD = 100  # Minimum length for value redaction in error logs


def apply_replacements_in_reverse(
    replacements: list[tuple[int, int, str]], text: str, batch_size: int = 500
) -> str:
    """
    Apply text replacements in reverse order with batching for large texts

    Args:
        replacements: List of (start, end, replacement) tuples
        text: Original text to modify
        batch_size: Number of replacements to process in each batch

    Returns:
        str: Text with replacements applied
    """
    import time

    start_time = time.time()
    replacement_count = len(replacements)
    text_length = len(text)

    # Memory usage monitoring for large documents
    memory_threshold = 1_000_000  # 1MB threshold for memory-efficient mode
    streaming_threshold = 5_000_000  # 5MB threshold for streaming mode

    if text_length > streaming_threshold:
        logger.info(
            f"Very large document detected: {text_length} bytes, enabling streaming processing"
        )
        return _mask_phi_streaming(text, replacements, start_time)
    elif text_length > memory_threshold:
        logger.info(
            f"Large document detected: {text_length} bytes, enabling memory-efficient processing"
        )
        return _apply_replacements_memory_efficient(replacements, text, batch_size, start_time)

    # For small replacement sets, process normally
    if replacement_count <= batch_size:
        logger.debug(
            f"PHI processing: {replacement_count} replacements in text of {text_length} chars (normal mode)"
        )
        sorted_replacements = sorted(replacements, key=lambda x: x[0], reverse=True)
        result = text
        for start, end, replacement in sorted_replacements:
            result = result[:start] + replacement + result[end:]

        processing_time = time.time() - start_time
        logger.debug(f"PHI processing completed in {processing_time:.3f}s (normal mode)")
        return result

    # For large replacement sets, process in batches
    result = text
    sorted_replacements = sorted(replacements, key=lambda x: x[0], reverse=True)
    batch_count = 0

    logger.info(
        f"Batching enabled: Total replacements={len(sorted_replacements)}, Batch size={batch_size}"
    )
    for i in range(0, len(sorted_replacements), batch_size):
        batch = sorted_replacements[i : i + batch_size]
        logger.debug(f"Processing batch {i // batch_size + 1}: Batch size={len(batch)}")
        batch_count += 1

        batch_start_time = time.time()
        for start, end, replacement in batch:
            result = result[:start] + replacement + result[end:]

        batch_time = time.time() - batch_start_time
        logger.debug(
            f"PHI batch {batch_count} processed: {len(batch)} replacements in {batch_time:.3f}s"
        )

    total_time = time.time() - start_time
    logger.info(f"PHI batch processing completed: {batch_count} batches in {total_time:.3f}s")

    return result


def _mask_phi_streaming(
    text: str, replacements: list[tuple[int, int, str]], start_time: float
) -> str:
    """
    Memory-efficient PHI masking for very large documents using streaming approach

    This approach builds the result incrementally using list building instead of
    string concatenation to avoid memory spikes with very large medical records.

    Args:
        text: Original text to modify
        replacements: List of (start, end, replacement) tuples
        start_time: Processing start time for metrics

    Returns:
        str: Text with replacements applied
    """
    import sys
    import time

    text_length = len(text)
    replacement_count = len(replacements)

    logger.info(
        f"Streaming PHI processing: {replacement_count} replacements, {text_length:,} chars"
    )

    # Sort replacements by start position (forward order for streaming)
    sorted_replacements = sorted(replacements, key=lambda x: x[0])

    # Use list building for memory efficiency
    masked_parts = []
    current_index = 0

    # Track memory usage
    initial_memory = sys.getsizeof(text)

    # Process replacements in forward order for streaming
    for i, (start, end, replacement) in enumerate(sorted_replacements):
        # Validate indices
        if start < current_index:
            logger.warning(
                f"Overlapping replacement detected: start={start}, current_index={current_index}"
            )
            continue

        if start >= text_length or end > text_length or start >= end:
            logger.warning(
                f"Invalid replacement indices: start={start}, end={end}, text_length={text_length}"
            )
            continue

        # Add unmasked text up to replacement
        if start > current_index:
            masked_parts.append(text[current_index:start])

        # Add masked replacement
        masked_parts.append(replacement)
        current_index = end

        # Memory monitoring every 1000 replacements
        if i % 1000 == 0 and i > 0:
            current_memory = sys.getsizeof(masked_parts)
            logger.debug(
                f"Streaming progress: {i}/{replacement_count} replacements, memory: {current_memory:,} bytes"
            )

    # Add remaining text after last replacement
    if current_index < text_length:
        masked_parts.append(text[current_index:])

    # Join all parts (single memory allocation)
    result = "".join(masked_parts)

    total_time = time.time() - start_time
    final_memory = sys.getsizeof(result)

    logger.info(
        f"Streaming PHI processing completed: {replacement_count} replacements in {total_time:.3f}s, "
        f"input: {initial_memory:,} bytes, output: {final_memory:,} bytes"
    )

    return result


def _apply_replacements_memory_efficient(
    replacements: list[tuple[int, int, str]],
    text: str,
    batch_size: int,
    start_time: float,
) -> str:
    """
    Memory-efficient replacement processing for very large texts using StringIO

    Args:
        replacements: List of (start, end, replacement) tuples
        text: Original text to modify
        batch_size: Number of replacements to process in each batch
        start_time: Processing start time for metrics

    Returns:
        str: Text with replacements applied
    """
    import sys
    import time

    text_length = len(text)
    replacement_count = len(replacements)

    logger.info(
        f"Memory-efficient PHI processing: {replacement_count} replacements, {text_length} chars"
    )

    # Sort replacements in reverse order to prevent index shifting
    sorted_replacements = sorted(replacements, key=lambda x: x[0], reverse=True)

    # Use StringIO for memory-efficient string manipulation
    text_io = StringIO(text)
    text_chars = list(text_io.getvalue())  # Convert to character list for efficient indexing

    # Process replacements in batches
    batch_count = 0
    for i in range(0, len(sorted_replacements), batch_size):
        batch = sorted_replacements[i : i + batch_size]
        batch_count += 1

        batch_start_time = time.time()

        # Apply replacements in current batch
        for start, end, replacement in batch:
            # Validate indices
            if start < 0 or end > len(text_chars) or start >= end:
                logger.warning(
                    f"Invalid replacement indices: start={start}, end={end}, text_length={len(text_chars)}"
                )
                continue

            # Replace characters using list slicing (more memory efficient than string concatenation)
            text_chars[start:end] = list(replacement)

        batch_time = time.time() - batch_start_time

        # Memory usage monitoring
        current_memory = sys.getsizeof(text_chars)
        logger.debug(
            f"Memory-efficient batch {batch_count}: {len(batch)} replacements, "
            f"{batch_time:.3f}s, memory: {current_memory:,} bytes"
        )

    # Convert back to string
    result = "".join(text_chars)

    total_time = time.time() - start_time
    final_memory = sys.getsizeof(result)

    logger.info(
        f"Memory-efficient PHI processing completed: {batch_count} batches in {total_time:.3f}s, "
        f"final size: {len(result):,} chars, memory: {final_memory:,} bytes"
    )

    return result


@dataclass
class PHIDetectionResult:
    """Result of PHI detection"""

    phi_detected: bool
    phi_types: list[str]
    confidence_scores: list[float]
    masked_text: str
    detection_details: list[dict[str, Any]]


class BasicPHIDetector:
    """Basic PHI detector using regex patterns"""

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"{__name__}.BasicPHIDetector")

        # Synthetic data patterns to exclude from PHI detection
        self.synthetic_patterns = {
            "test_phone": r"\(555\)\s*\d{3}-\d{4}|555-\d{3}-\d{4}",
            "test_ssn": r"123-45-6789|XXX-XX-XXXX|\*{3}-\*{2}-\*{4}",
            "test_email": r".*@(synthetic|test|example)\..*",
            "test_patient_id": r"PAT\d{3}|SYN-\d+|TEST-\d+",
            "test_names": r"\b(John Doe|Jane Doe|Test Patient|Synthetic Patient)\b",
            "test_addresses": r"\b123 (Synthetic|Test|Example) (St|Street|Ave|Avenue)\b",
        }

        # PHI patterns based on HIPAA identifiers (excluding synthetic patterns)
        self.phi_patterns = {
            "ssn": {
                "pattern": r"\b\d{3}-\d{2}-\d{4}\b|\b\d{9}\b",
                "description": "Social Security Number",
            },
            "phone": {
                "pattern": r"\b\d{3}-\d{3}-\d{4}\b|\b\(\d{3}\)\s*\d{3}-\d{4}\b",
                "description": "Phone Number",
            },
            "email": {
                "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                "description": "Email Address",
            },
            "mrn": {
                "pattern": r"\b(mrn|medical\s+record\s+number|patient\s+id)\s*:?\s*[A-Z0-9]{6,12}\b",
                "description": "Medical Record Number",
            },
            "dob": {
                "pattern": r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b|\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b",
                "description": "Date of Birth",
            },
            "address": {
                "pattern": r"\b\d+\s+[A-Za-z\s]+\s+(street|st|avenue|ave|road|rd|drive|dr|lane|ln|boulevard|blvd)\b",
                "description": "Street Address",
            },
            "zip_code": {"pattern": r"\b\d{5}(-\d{4})?\b", "description": "ZIP Code"},
            "insurance_id": {
                "pattern": r"\b(insurance|policy)\s+(number|id)\s*:?\s*[A-Z0-9]{8,15}\b",
                "description": "Insurance ID",
            },
        }

    def _is_synthetic_data(self, text: str) -> bool:
        """Check if text contains synthetic data patterns"""
        for pattern_name, pattern in self.synthetic_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                self.logger.debug(f"Synthetic pattern detected: {pattern_name}")
                return True

        # Check for common synthetic markers
        synthetic_markers = [
            "_synthetic",
            "synthetic",
            "test",
            "example",
            "PAT001",
            "PAT002",
            "PAT003",
            "PROV001",
            "ENC001",
            "555-",
            "XXX-XX",
            "synthetic.test",
            "example.com",
        ]

        text_lower = text.lower()
        for marker in synthetic_markers:
            if marker.lower() in text_lower:
                self.logger.debug(f"Synthetic marker detected: {marker}")
                return True

        return False

    def _process_and_mask_matches(
        self,
        matches: Any,
        phi_type: str,
        pattern_info: dict[str, Any],
        phi_detected: bool,
        phi_types: list[str],
        confidence_scores: list[float],
        detection_details: list[dict[str, Any]],
        masked_text: str,
    ) -> tuple[bool, list[str], list[float], list[dict[str, Any]], str]:
        """Process matches and mask detected PHI"""
        # Process matches in reverse order to maintain valid positions during masking.
        # Masking modifies the string, which shifts the indices of subsequent matches.
        # Reverse iteration ensures that earlier matches are not affected by these shifts,
        # preventing potential IndexError or incorrect masking.

        for match in reversed(matches):
            phi_detected = True
            phi_types.append(phi_type)
            confidence_scores.append(0.8)  # Basic confidence score

            detection_details.append(
                {
                    "type": phi_type,
                    "description": pattern_info["description"],
                    "start": match.start(),
                    "end": match.end(),
                    "text": match.group(),
                    "confidence": 0.8,
                }
            )

            # Mask the detected PHI (processing in reverse order prevents IndexError)
            mask_length = len(match.group())
            mask = "*" * mask_length
            masked_text = masked_text[: match.start()] + mask + masked_text[match.end() :]

        return (
            phi_detected,
            phi_types,
            confidence_scores,
            detection_details,
            masked_text,
        )

    def detect_phi(self, text: str) -> PHIDetectionResult:
        """Detect PHI in text using regex patterns"""
        # First check if this is synthetic data
        if self._is_synthetic_data(text):
            self.logger.debug("Synthetic data detected - skipping PHI detection")
            return PHIDetectionResult(
                phi_detected=False,
                phi_types=[],
                confidence_scores=[],
                masked_text=text,  # No masking needed for synthetic data
                detection_details=[],
            )

        phi_detected = False
        phi_types = []
        confidence_scores = []
        detection_details = []

        # Collect all replacements first
        replacements = []

        for phi_type, pattern_info in self.phi_patterns.items():
            pattern = pattern_info["pattern"]
            matches = list(re.finditer(pattern, text, re.IGNORECASE))

            for match in matches:
                # Double-check that this specific match is not synthetic
                matched_text = match.group()
                if self._is_synthetic_data(matched_text):
                    self.logger.debug(f"Skipping synthetic match: {matched_text}")
                    continue

                phi_detected = True
                phi_types.append(phi_type)
                confidence_scores.append(0.8)

                detection_details.append(
                    {
                        "type": phi_type,
                        "description": pattern_info["description"],
                        "start": match.start(),
                        "end": match.end(),
                        "text": match.group(),
                        "confidence": 0.8,
                    }
                )

                # Collect replacement
                mask_length = len(match.group())
                mask = "*" * mask_length
                replacements.append((match.start(), match.end(), mask))

        # Apply all replacements using utility function
        masked_text = apply_replacements_in_reverse(replacements, text)

        return PHIDetectionResult(
            phi_detected=phi_detected,
            phi_types=list(set(phi_types)),
            confidence_scores=confidence_scores,
            masked_text=masked_text,
            detection_details=detection_details,
        )


class PresidioPHIDetector:
    """Advanced PHI detector using Microsoft Presidio"""

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"{__name__}.PresidioPHIDetector")

        if not PRESIDIO_AVAILABLE or AnalyzerEngine is None or AnonymizerEngine is None:
            raise ImportError("Presidio is not available")

        # Initialize Presidio engines with proper typing
        self.analyzer: Any = AnalyzerEngine()  # AnalyzerEngine when available
        self.anonymizer: Any = AnonymizerEngine()  # AnonymizerEngine when available

        # Healthcare-specific entities
        self.healthcare_entities = [
            "PERSON",
            "PHONE_NUMBER",
            "EMAIL_ADDRESS",
            "DATE_TIME",
            "LOCATION",
            "US_SSN",
            "MEDICAL_LICENSE",
            "US_PASSPORT",
            "CREDIT_CARD",
            "US_BANK_NUMBER",
            "IP_ADDRESS",
            "URL",
        ]

    def detect_phi(self, text: str) -> PHIDetectionResult:
        """Detect PHI using Presidio analyzer"""
        try:
            # Analyze text for PII/PHI
            results = self.analyzer.analyze(
                text=text, entities=self.healthcare_entities, language="en"
            )

            phi_detected = len(results) > 0
            phi_types = [result.entity_type for result in results]
            confidence_scores = [result.score for result in results]

            # Create anonymized version
            anonymized_result = self.anonymizer.anonymize(
                text=text,
                analyzer_results=cast(
                    list[Any], results
                ),  # Type cast to resolve Presidio type mismatch
            )
            masked_text = anonymized_result.text

            # Create detection details
            detection_details = []
            for result in results:
                detection_details.append(
                    {
                        "type": result.entity_type,
                        "description": f"Detected {result.entity_type}",
                        "start": result.start,
                        "end": result.end,
                        "text": text[result.start : result.end],
                        "confidence": result.score,
                    }
                )

            return PHIDetectionResult(
                phi_detected=phi_detected,
                phi_types=list(set(phi_types)),
                confidence_scores=confidence_scores,
                masked_text=masked_text,
                detection_details=detection_details,
            )

        except Exception as e:
            self.logger.error(f"Presidio PHI detection failed: {e}")
            # Fallback to basic detection
            basic_detector = BasicPHIDetector()
            return basic_detector.detect_phi(text)


class PHIDetector:
    """Main PHI detector with fallback capabilities"""

    def __init__(self, use_presidio: bool = True) -> None:
        self.logger = logging.getLogger(f"{__name__}.PHIDetector")
        self.use_presidio = use_presidio and PRESIDIO_AVAILABLE

        # Initialize detector with proper typing
        self.detector: PresidioPHIDetector | BasicPHIDetector

        if self.use_presidio:
            try:
                self.detector = PresidioPHIDetector()
                self.logger.info("Using Presidio for PHI detection")
            except Exception as e:
                self.logger.warning(f"Failed to initialize Presidio: {e}")
                self.detector = BasicPHIDetector()
                self.logger.info("Using basic PHI detection")
        else:
            self.detector = BasicPHIDetector()
            self.logger.info("Using basic PHI detection")

    async def detect_phi(self, text: str) -> PHIDetectionResult:
        """Detect PHI in text (async wrapper)"""
        return self.detector.detect_phi(text)

    def detect_phi_sync(self, text: str) -> PHIDetectionResult:
        """Detect PHI in text (synchronous)"""
        return self.detector.detect_phi(text)

    async def detect_phi_in_json(self, data: dict[str, Any]) -> dict[str, PHIDetectionResult]:
        """Detect PHI in JSON data structure"""
        results = {}

        def process_value(key: str, value: Any) -> PHIDetectionResult:
            # Handle different data types
            if isinstance(value, str):
                # Detect PHI in strings
                return self.detector.detect_phi(value)
            elif isinstance(value, dict):
                # Recursively process nested dictionaries
                dict_phi_results = {}
                for nested_key, nested_value in value.items():
                    dict_phi_results[nested_key] = process_value(nested_key, nested_value)
                return PHIDetectionResult(
                    phi_detected=any(res.phi_detected for res in dict_phi_results.values()),
                    phi_types=list(
                        {ptype for res in dict_phi_results.values() for ptype in res.phi_types}
                    ),
                    confidence_scores=[
                        score
                        for res in dict_phi_results.values()
                        for score in res.confidence_scores
                    ],
                    masked_text=json.dumps(
                        {k: res.masked_text for k, res in dict_phi_results.items()}
                    ),
                    detection_details=[
                        detail
                        for res in dict_phi_results.values()
                        for detail in res.detection_details
                    ],
                )
            elif isinstance(value, list):
                # Recursively process lists
                list_phi_results = []
                for i, item in enumerate(value):
                    list_phi_results.append(process_value(f"{key}[{i}]", item))
                try:
                    return PHIDetectionResult(
                        phi_detected=any(res.phi_detected for res in list_phi_results),
                        phi_types=list(
                            {ptype for res in list_phi_results for ptype in res.phi_types}
                        ),
                        confidence_scores=[
                            score for res in list_phi_results for score in res.confidence_scores
                        ],
                        masked_text=json.dumps([res.masked_text for res in list_phi_results]),
                        detection_details=[
                            detail for res in list_phi_results for detail in res.detection_details
                        ],
                    )
                except (TypeError, ValueError) as e:
                    self.logger.error(
                        "Failed to serialize list value to JSON. Key: %s, List length: %s, Error: %s",
                        key,
                        len(value) if isinstance(value, list) else "unknown",
                        str(e),
                    )
                    return PHIDetectionResult(
                        phi_detected=False,
                        phi_types=[],
                        confidence_scores=[],
                        masked_text="",
                        detection_details=[],
                    )
            else:
                # No PHI in non-string values
                return PHIDetectionResult(
                    phi_detected=False,
                    phi_types=[],
                    confidence_scores=[],
                    masked_text=str(value),
                    detection_details=[],
                )

        def traverse_dict(obj: dict[str, Any], prefix: str = "") -> None:
            for key, value in obj.items():
                full_key = f"{prefix}.{key}" if prefix else key

                if isinstance(value, dict):
                    traverse_dict(value, full_key)
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            traverse_dict(item, f"{full_key}[{i}]")
                        else:
                            results[f"{full_key}[{i}]"] = process_value(f"{full_key}[{i}]", item)
                else:
                    results[full_key] = process_value(full_key, value)

        traverse_dict(data)
        return results

    def mask_phi_in_text(self, text: str, mask_char: str = "*") -> str:
        """Mask PHI in text"""
        result = self.detector.detect_phi(text)
        return result.masked_text

    def detect_phi_batch(self, field_data: dict[str, str]) -> dict[str, PHIDetectionResult]:
        """
        Detect PHI in multiple fields efficiently using batch processing

        Args:
            field_data: Dictionary of field names to text values

        Returns:
            Dictionary of field names to PHI detection results
        """
        import time

        start_time = time.time()
        field_count = len(field_data)

        self.logger.debug(f"Starting batch PHI detection for {field_count} fields")

        results = {}

        # Process each field (can be optimized further with true batch processing)
        for field_name, text_value in field_data.items():
            if isinstance(text_value, str) and text_value.strip():
                results[field_name] = self.detector.detect_phi(text_value)
            else:
                # Empty or non-string values
                results[field_name] = PHIDetectionResult(
                    phi_detected=False,
                    phi_types=[],
                    confidence_scores=[],
                    masked_text=str(text_value) if text_value is not None else "",
                    detection_details=[],
                )

        processing_time = time.time() - start_time
        phi_detected_count = sum(1 for result in results.values() if result.phi_detected)

        self.logger.info(
            f"Batch PHI detection completed: {field_count} fields processed in {processing_time:.3f}s, "
            f"{phi_detected_count} fields with PHI detected"
        )

        return results

    def get_phi_summary(self, text: str) -> dict[str, Any]:
        """Get summary of PHI detection"""
        result = self.detector.detect_phi(text)

        return {
            "phi_detected": result.phi_detected,
            "phi_count": len(result.detection_details),
            "phi_types": result.phi_types,
            "average_confidence": (
                sum(result.confidence_scores) / len(result.confidence_scores)
                if result.confidence_scores
                else 0
            ),
            "detection_timestamp": datetime.now().isoformat(),
        }


class PHIMaskingService:
    """Service for masking PHI in various data formats"""

    def __init__(self, phi_detector: PHIDetector) -> None:
        self.phi_detector = phi_detector
        self.logger = logging.getLogger(f"{__name__}.PHIMaskingService")

    def mask_patient_data(self, patient_data: dict[str, Any]) -> dict[str, Any]:
        """Mask PHI in patient data structure using batch processing"""
        masked_data = patient_data.copy()

        # Fields that commonly contain PHI
        phi_fields = [
            "first_name",
            "last_name",
            "full_name",
            "name",
            "phone",
            "phone_number",
            "email",
            "email_address",
            "ssn",
            "social_security_number",
            "patient_id",
            "mrn",
            "date_of_birth",
            "dob",
            "birth_date",
            "address",
            "street_address",
            "zip_code",
            "postal_code",
        ]

        # Collect all string fields that need PHI detection
        fields_to_process = {}
        for field in phi_fields:
            if field in masked_data and isinstance(masked_data[field], str):
                fields_to_process[field] = masked_data[field]

        # Batch detect PHI in all collected fields
        if fields_to_process:
            detection_results = self.phi_detector.detect_phi_batch(fields_to_process)

            # Apply masking results
            masked_fields = []
            for field, result in detection_results.items():
                if result.phi_detected:
                    masked_data[field] = result.masked_text
                    masked_fields.append(field)

            if masked_fields:
                self.logger.info(
                    f"Batch PHI masking completed: {len(masked_fields)} fields masked - {', '.join(masked_fields)}"
                )

        return masked_data

    def create_synthetic_replacement(self, original_data: dict[str, Any]) -> dict[str, Any]:
        """Create synthetic replacement for data containing PHI"""
        synthetic_data = original_data.copy()

        # Replace with clearly synthetic values
        replacements = {
            "first_name": "John",
            "last_name": "Doe",
            "phone": "555-0123",
            "email": "patient@synthetic.test",
            "ssn": "XXX-XX-XXXX",
            "patient_id": "SYN-12345",
            "date_of_birth": "1990-01-01",
            "address": "123 Synthetic St",
            "zip_code": "00000",
        }

        for field, synthetic_value in replacements.items():
            if field in synthetic_data:
                synthetic_data[field] = synthetic_value

        # Add synthetic marker
        synthetic_data["_synthetic"] = True
        synthetic_data["_original_masked"] = datetime.now().isoformat()

        return synthetic_data


# Example usage and testing
if __name__ == "__main__":
    # Test PHI detection
    detector = PHIDetector()

    test_text = """
    Patient John Smith, DOB: 01/15/1980, SSN: 123-45-6789
    Phone: (555) 123-4567, Email: john.smith@email.com
    Address: 123 Main Street, Anytown, NY 12345
    MRN: MED123456
    """

    result = detector.detect_phi_sync(test_text)

    print(f"PHI Detected: {result.phi_detected}")
    print(f"PHI Types: {result.phi_types}")
    print(f"Masked Text: {result.masked_text}")
    print(f"Detection Details: {json.dumps(result.detection_details, indent=2)}")
