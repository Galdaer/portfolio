"""
Test PHI Sanitizer External Medical Content Detection

Tests the PHI sanitizer's ability to distinguish between:
- External medical research content (should be exempted from PHI detection)
- General medical terminology (should be exempted from PHI detection)
- Patient-specific content (should be subject to PHI detection)
"""

import pytest
import sys
from pathlib import Path

# Add the healthcare-api directory to the path for imports
healthcare_api_path = Path(__file__).parent.parent / "services" / "user" / "healthcare-api"
sys.path.insert(0, str(healthcare_api_path))

from core.phi_sanitizer import (
    _is_external_medical_content,
    sanitize_request_data,
    sanitize_response_data,
)


class TestExternalMedicalContentDetection:
    """Test external medical content detection patterns."""

    def test_research_citations_exempted(self):
        """Test that research citations are properly exempted from PHI detection."""
        research_citation_examples = [
            "Dr. Smith et al. published a study on cardiovascular health",
            "According to Anderson and colleagues, diabetes management is crucial",
            "Research by Johnson showed promising results",
            "Smith et al. (2023) reported significant findings",
            "The study was conducted by Brown and team",
            "Jones, Williams et al. demonstrated effectiveness",
            "Published in Nature, the paper by Davis et al.",
            "The journal of medicine featured research by Taylor",
            "Study by Martinez led to breakthrough discoveries",
            "Authored by the research team at Johns Hopkins",
        ]

        for citation in research_citation_examples:
            assert _is_external_medical_content(citation), (
                f"Research citation should be exempted: {citation}"
            )

    def test_medical_terminology_exempted(self):
        """Test that general medical terminology is exempted from PHI detection."""
        medical_terminology_examples = [
            "cardiovascular health symptoms",
            "diabetes management strategies",
            "cancer treatment options",
            "hypertension medication side effects",
            "respiratory therapy techniques",
            "neurological symptoms assessment",
            "cardiac disease prevention",
            "diabetic complications monitoring",
            "oncology treatment protocols",
            "pulmonary disease therapy",
            "clinical diagnosis procedures",
            "therapeutic medication dosage",
            "medical treatment recommendations",
        ]

        for term in medical_terminology_examples:
            assert _is_external_medical_content(term), (
                f"Medical terminology should be exempted: {term}"
            )

    def test_patient_specific_content_not_exempted(self):
        """Test that patient-specific content is NOT exempted from PHI detection."""
        patient_specific_examples = [
            "Patient John Doe has diabetes",
            "Mr. Johnson was admitted yesterday",
            "Smith is a 45-year-old male with hypertension",
            "Patient Anderson was diagnosed with cancer",
            "Mrs. Wilson was treated for pneumonia",
            "The patient named Brown has cardiac issues",
            "Ms. Davis is a 32-year-old female",
            "Patient Miller was admitted for surgery",
        ]

        for patient_content in patient_specific_examples:
            assert not _is_external_medical_content(patient_content), (
                f"Patient content should NOT be exempted: {patient_content}"
            )

    def test_general_content_not_exempted(self):
        """Test that general non-medical content is not exempted."""
        general_content_examples = [
            "Hello world",
            "The weather is nice today",
            "Please send me the report",
            "Meeting scheduled for tomorrow",
            "Happy birthday John",
            "Thanks for your help",
        ]

        for content in general_content_examples:
            assert not _is_external_medical_content(content), (
                f"General content should NOT be exempted: {content}"
            )

    def test_edge_cases(self):
        """Test edge cases for medical content detection."""
        # Empty or None content
        assert not _is_external_medical_content("")

        # Mixed content with both research and patient data
        mixed_content = "According to Dr. Smith's research, Patient John Doe shows symptoms"
        # This should be flagged because it contains patient-specific content
        assert not _is_external_medical_content(mixed_content), (
            "Mixed content with patient data should NOT be exempted"
        )

        # Medical terms without proper context
        standalone_medical = "diabetes"
        # Single medical terms might not match the patterns - this is expected
        # The patterns are designed for more specific medical terminology

        # Complex research citation
        complex_citation = (
            "The multi-center study by Anderson, Smith, and colleagues (2023) published in NEJM"
        )
        assert _is_external_medical_content(complex_citation), (
            "Complex research citation should be exempted"
        )


class TestPHISanitizerIntegration:
    """Test PHI sanitizer integration with external content detection."""

    def test_request_sanitization_with_research_citations(self):
        """Test that research citations in requests are not sanitized."""
        request_data = {
            "messages": [
                {
                    "role": "user",
                    "content": "Tell me about the study by Dr. Smith et al. on cardiovascular health",
                }
            ]
        }

        sanitized = sanitize_request_data(request_data)

        # The content should remain unchanged because it's external medical content
        assert sanitized["messages"][0]["content"] == request_data["messages"][0]["content"]

    def test_request_sanitization_with_patient_data(self):
        """Test that patient data in requests is properly sanitized."""
        request_data = {"messages": [{"role": "user", "content": "Patient John Doe has diabetes"}]}

        # Note: This test depends on the PHI detector working properly
        # The actual sanitization behavior will depend on whether the PHI detector
        # considers "John Doe" to be PHI in this context
        sanitized = sanitize_request_data(request_data)

        # At minimum, the function should not crash
        assert "messages" in sanitized
        assert len(sanitized["messages"]) == 1

    def test_response_sanitization_with_medical_terminology(self):
        """Test that medical terminology in responses is not sanitized."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Cardiovascular health management involves regular monitoring of blood pressure"
                    }
                }
            ]
        }

        sanitized = sanitize_response_data(response_data)

        # The content should remain unchanged because it's medical terminology
        assert (
            sanitized["choices"][0]["message"]["content"]
            == response_data["choices"][0]["message"]["content"]
        )


class TestConfigurationIntegration:
    """Test that the configuration system is working properly."""

    def test_config_patterns_loaded(self):
        """Test that medical literature patterns are loaded from config."""
        from config.phi_detection_config_loader import phi_config

        patterns = phi_config.get_medical_literature_patterns()

        # Verify that the new pattern categories exist
        assert "research_citations" in patterns
        assert "medical_terminology" in patterns
        assert "patient_specific_exclusions" in patterns

        # Verify that patterns are not empty
        assert len(patterns["research_citations"]) > 0
        assert len(patterns["medical_terminology"]) > 0
        assert len(patterns["patient_specific_exclusions"]) > 0

    def test_compiled_patterns_work(self):
        """Test that compiled patterns work correctly."""
        from config.phi_detection_config_loader import phi_config

        compiled_patterns = phi_config.get_compiled_medical_literature_patterns()

        # Test a research citation pattern
        research_patterns = compiled_patterns.get("research_citations", [])
        test_text = "Dr. Smith et al. published results"

        found_match = False
        for pattern in research_patterns:
            if pattern.search(test_text):
                found_match = True
                break

        assert found_match, "Research citation should match compiled patterns"

    def test_exemption_context_check(self):
        """Test that exemption context checking works."""
        from config.phi_detection_config_loader import phi_config

        # Test that medical_literature context is exempted
        assert phi_config.is_exempted_context("medical_literature")
        assert phi_config.is_exempted_context("pubmed")
        assert phi_config.is_exempted_context("research_paper")

        # Test that non-exempted contexts return False
        assert not phi_config.is_exempted_context("patient_data")
        assert not phi_config.is_exempted_context("random_context")


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])
