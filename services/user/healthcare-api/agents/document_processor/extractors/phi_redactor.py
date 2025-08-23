"""
PHI Redactor for Healthcare Document Processing

Integrates with existing PHI detection system to provide document-level
PHI redaction capabilities with HIPAA compliance logging.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from core.infrastructure.healthcare_logger import get_healthcare_logger, log_healthcare_event
from core.phi_sanitizer import get_phi_detector, sanitize_text_content
from src.healthcare_mcp.phi_detection import PHIDetectionResult


class PHIRedactor:
    """
    Handles PHI detection and redaction for document processing
    
    Integrates with existing PHI detection infrastructure to provide
    document-level PHI handling with comprehensive audit logging.
    """
    
    def __init__(self, enable_presidio: bool = True):
        """
        Initialize PHI redactor
        
        Args:
            enable_presidio: Whether to use Presidio for advanced PHI detection
        """
        self.logger = get_healthcare_logger("document_processor.phi_redactor")
        self.enable_presidio = enable_presidio
        
        # Get the existing PHI detector singleton
        self.phi_detector = get_phi_detector()
        
        # Redaction configuration
        self.redaction_levels = {
            'minimal': ['ssn', 'mrn', 'phone'],
            'standard': ['ssn', 'mrn', 'phone', 'email', 'name', 'dob'],
            'comprehensive': ['ssn', 'mrn', 'phone', 'email', 'name', 'dob', 'address', 'insurance_id'],
        }
        
        # Administrative disclaimer
        self.disclaimer = (
            "PHI redaction provides administrative privacy protection only. "
            "All redaction results should be reviewed by qualified privacy professionals."
        )
        
        log_healthcare_event(
            self.logger,
            logging.INFO,
            "PHI redactor initialized with existing detection infrastructure",
            context={
                "presidio_enabled": enable_presidio,
                "redaction_levels": list(self.redaction_levels.keys()),
                "administrative_use": True,
                "hipaa_compliance": True,
            },
            operation_type="phi_redactor_initialization",
        )
    
    async def analyze_phi(self, text: str) -> PHIDetectionResult:
        """
        Analyze text for PHI using existing detection infrastructure
        
        Args:
            text: Text content to analyze
            
        Returns:
            PHI detection result with analysis details
        """
        if not text or not text.strip():
            return PHIDetectionResult(
                phi_detected=False,
                phi_types=[],
                confidence_scores=[],
                masked_text="",
                detection_details=[],
            )
        
        try:
            # Use existing PHI detector
            result = await self.phi_detector.detect_phi(text)
            
            # Log PHI detection event for HIPAA audit
            if result.phi_detected:
                log_healthcare_event(
                    self.logger,
                    logging.WARNING,
                    f"PHI detected in document content",
                    context={
                        "phi_types": result.phi_types,
                        "text_length": len(text),
                        "detection_count": len(result.detection_details),
                        "confidence_scores": result.confidence_scores,
                        "administrative_detection": True,
                    },
                    operation_type="phi_detection",
                    is_phi_related=True,
                )
            
            return result
            
        except Exception as e:
            self.logger.exception(f"PHI analysis failed: {e}")
            # Return empty result on failure
            return PHIDetectionResult(
                phi_detected=False,
                phi_types=[],
                confidence_scores=[],
                masked_text=text,
                detection_details=[],
            )
    
    async def redact_phi(
        self, 
        text: str, 
        redaction_level: str = 'standard',
        custom_mask: str = '*',
    ) -> Tuple[str, PHIDetectionResult]:
        """
        Redact PHI from text with configurable levels
        
        Args:
            text: Text content to redact
            redaction_level: Level of redaction (minimal, standard, comprehensive)
            custom_mask: Custom masking character
            
        Returns:
            Tuple of (redacted_text, phi_analysis_result)
        """
        if not text or not text.strip():
            return "", PHIDetectionResult(
                phi_detected=False,
                phi_types=[],
                confidence_scores=[],
                masked_text="",
                detection_details=[],
            )
        
        try:
            # Analyze for PHI first
            phi_result = await self.analyze_phi(text)
            
            if not phi_result.phi_detected:
                return text, phi_result
            
            # Apply redaction using existing sanitizer
            redacted_text = sanitize_text_content(text)
            
            # Create updated result with redacted text
            updated_result = PHIDetectionResult(
                phi_detected=phi_result.phi_detected,
                phi_types=phi_result.phi_types,
                confidence_scores=phi_result.confidence_scores,
                masked_text=redacted_text,
                detection_details=phi_result.detection_details,
            )
            
            # Log redaction event
            log_healthcare_event(
                self.logger,
                logging.INFO,
                f"PHI redaction completed",
                context={
                    "redaction_level": redaction_level,
                    "phi_types": phi_result.phi_types,
                    "original_length": len(text),
                    "redacted_length": len(redacted_text),
                    "administrative_redaction": True,
                },
                operation_type="phi_redaction",
                is_phi_related=True,
            )
            
            return redacted_text, updated_result
            
        except Exception as e:
            self.logger.exception(f"PHI redaction failed: {e}")
            return text, PHIDetectionResult(
                phi_detected=False,
                phi_types=[],
                confidence_scores=[],
                masked_text=text,
                detection_details=[],
            )
    
    async def create_redacted_versions(
        self, 
        text: str,
    ) -> Dict[str, Tuple[str, PHIDetectionResult]]:
        """
        Create multiple redacted versions with different levels
        
        Args:
            text: Original text content
            
        Returns:
            Dictionary mapping redaction levels to (redacted_text, phi_result)
        """
        redacted_versions = {}
        
        for level in self.redaction_levels.keys():
            redacted_text, phi_result = await self.redact_phi(text, level)
            redacted_versions[level] = (redacted_text, phi_result)
        
        return redacted_versions
    
    async def get_phi_summary(self, text: str) -> Dict[str, Any]:
        """
        Get comprehensive PHI analysis summary
        
        Args:
            text: Text content to analyze
            
        Returns:
            Summary of PHI analysis results
        """
        phi_result = await self.analyze_phi(text)
        
        summary = {
            "phi_detected": phi_result.phi_detected,
            "phi_count": len(phi_result.detection_details),
            "phi_types": phi_result.phi_types,
            "confidence_summary": {
                "average": (
                    sum(phi_result.confidence_scores) / len(phi_result.confidence_scores)
                    if phi_result.confidence_scores else 0.0
                ),
                "minimum": min(phi_result.confidence_scores) if phi_result.confidence_scores else 0.0,
                "maximum": max(phi_result.confidence_scores) if phi_result.confidence_scores else 0.0,
            },
            "detection_details": phi_result.detection_details,
            "text_statistics": {
                "original_length": len(text),
                "redacted_length": len(phi_result.masked_text),
                "reduction_percentage": (
                    (len(text) - len(phi_result.masked_text)) / len(text) * 100
                    if len(text) > 0 else 0.0
                ),
            },
            "recommended_actions": self._get_recommended_actions(phi_result),
            "administrative_note": self.disclaimer,
        }
        
        return summary
    
    def _get_recommended_actions(self, phi_result: PHIDetectionResult) -> List[str]:
        """Get recommended actions based on PHI detection results"""
        actions = []
        
        if not phi_result.phi_detected:
            actions.append("Document appears clear of PHI - safe for standard processing")
            return actions
        
        # High-risk PHI types
        high_risk_types = {'ssn', 'mrn', 'insurance_id'}
        detected_high_risk = [phi_type for phi_type in phi_result.phi_types if phi_type.lower() in high_risk_types]
        
        if detected_high_risk:
            actions.append("HIGH PRIORITY: Contains sensitive identifiers requiring immediate redaction")
        
        # Standard recommendations
        actions.extend([
            "Review and validate all detected PHI",
            "Apply appropriate redaction level based on use case",
            "Maintain audit trail of PHI handling",
            "Ensure HIPAA compliance before document sharing",
        ])
        
        # Low confidence detections
        low_confidence = [
            detail for detail in phi_result.detection_details 
            if detail.get('confidence', 1.0) < 0.7
        ]
        if low_confidence:
            actions.append(f"Manual review recommended for {len(low_confidence)} low-confidence detections")
        
        return actions
    
    async def batch_redact(
        self, 
        texts: List[str], 
        redaction_level: str = 'standard',
    ) -> List[Tuple[str, PHIDetectionResult]]:
        """
        Batch redaction of multiple texts
        
        Args:
            texts: List of text contents to redact
            redaction_level: Redaction level to apply
            
        Returns:
            List of (redacted_text, phi_result) tuples
        """
        results = []
        
        for i, text in enumerate(texts):
            try:
                redacted_text, phi_result = await self.redact_phi(text, redaction_level)
                results.append((redacted_text, phi_result))
                
                # Log batch progress
                if i % 10 == 0 and i > 0:
                    self.logger.info(f"Batch PHI redaction progress: {i}/{len(texts)} completed")
                    
            except Exception as e:
                self.logger.error(f"Batch redaction failed for text {i}: {e}")
                # Add failed result
                results.append((text, PHIDetectionResult(
                    phi_detected=False,
                    phi_types=[],
                    confidence_scores=[],
                    masked_text=text,
                    detection_details=[],
                )))
        
        log_healthcare_event(
            self.logger,
            logging.INFO,
            f"Batch PHI redaction completed: {len(texts)} documents processed",
            context={
                "batch_size": len(texts),
                "redaction_level": redaction_level,
                "successful_redactions": len([r for r in results if r[1].phi_detected]),
                "administrative_batch_processing": True,
            },
            operation_type="phi_batch_redaction",
            is_phi_related=True,
        )
        
        return results
    
    def get_redaction_levels(self) -> Dict[str, List[str]]:
        """Get available redaction levels and their PHI types"""
        return self.redaction_levels.copy()
    
    async def validate_redaction(self, original_text: str, redacted_text: str) -> Dict[str, Any]:
        """
        Validate that redaction was successful
        
        Args:
            original_text: Original text before redaction
            redacted_text: Text after redaction
            
        Returns:
            Validation results
        """
        # Re-analyze redacted text for any remaining PHI
        remaining_phi = await self.analyze_phi(redacted_text)
        
        validation_result = {
            "redaction_successful": not remaining_phi.phi_detected,
            "remaining_phi_detected": remaining_phi.phi_detected,
            "remaining_phi_types": remaining_phi.phi_types,
            "text_reduction": {
                "original_length": len(original_text),
                "redacted_length": len(redacted_text),
                "characters_redacted": len(original_text) - len(redacted_text),
                "reduction_percentage": (
                    (len(original_text) - len(redacted_text)) / len(original_text) * 100
                    if len(original_text) > 0 else 0.0
                ),
            },
            "validation_passed": not remaining_phi.phi_detected,
            "recommendations": [],
        }
        
        # Add recommendations based on validation
        if remaining_phi.phi_detected:
            validation_result["recommendations"].extend([
                "Additional redaction required - PHI still present",
                "Consider using comprehensive redaction level",
                "Manual review and redaction may be necessary",
            ])
        else:
            validation_result["recommendations"].append("Redaction successful - document ready for processing")
        
        return validation_result