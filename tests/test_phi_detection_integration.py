"""
Test PHI Detection Integration

Tests the complete PHI detection pipeline including:
- PHI detection in various contexts
- Configuration loading and pattern compilation
- Integration between sanitizer and detector
- Error handling and edge cases
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the healthcare-api directory to the path for imports
healthcare_api_path = Path(__file__).parent.parent / "services" / "user" / "healthcare-api"
sys.path.insert(0, str(healthcare_api_path))

from core.phi_sanitizer import get_phi_detector, sanitize_request_data, sanitize_response_data
from config.phi_detection_config_loader import phi_config


class TestPHIDetectorInitialization:
    """Test PHI detector initialization and configuration."""

    def test_phi_detector_singleton(self):
        """Test that PHI detector is properly initialized as singleton."""
        detector1 = get_phi_detector()
        detector2 = get_phi_detector()

        # Should be the same instance
        assert detector1 is detector2

    def test_phi_detector_fallback(self):
        """Test PHI detector fallback when Presidio is unavailable."""
        with patch("core.phi_sanitizer.PHIDetector") as mock_detector_class:
            # Mock Presidio failure, then success with basic detection
            mock_detector_class.side_effect = [Exception("Presidio failed"), MagicMock()]

            # Clear the global detector to test initialization
            import core.phi_sanitizer

            core.phi_sanitizer._phi_detector = None

            detector = get_phi_detector()

            # Should have been called twice - once with Presidio, once without
            assert mock_detector_class.call_count == 2
            assert mock_detector_class.call_args_list[0][1]["use_presidio"] is True
            assert mock_detector_class.call_args_list[1][1]["use_presidio"] is False


class TestConfigurationSystem:
    """Test the configuration system for PHI detection."""

    def test_config_loader_initialization(self):
        """Test that config loader initializes properly."""
        assert phi_config is not None
        assert hasattr(phi_config, "load_config")
        assert hasattr(phi_config, "get_medical_literature_patterns")

    def test_medical_literature_patterns_loaded(self):
        """Test that medical literature patterns are loaded correctly."""
        patterns = phi_config.get_medical_literature_patterns()

        # Check that all expected categories are present
        expected_categories = [
            "research_citations",
            "medical_terminology",
            "patient_specific_exclusions",
        ]
        for category in expected_categories:
            assert category in patterns, f"Missing pattern category: {category}"
            assert isinstance(patterns[category], list), (
                f"Pattern category {category} should be a list"
            )

    def test_compiled_patterns_generation(self):
        """Test that patterns compile correctly."""
        compiled_patterns = phi_config.get_compiled_medical_literature_patterns()

        # Check that compiled patterns exist
        assert "research_citations" in compiled_patterns
        assert "medical_terminology" in compiled_patterns
        assert "patient_specific_exclusions" in compiled_patterns

        # Check that patterns are actually compiled regex objects
        for category, patterns in compiled_patterns.items():
            assert isinstance(patterns, list), f"Compiled {category} should be a list"
            for pattern in patterns:
                assert hasattr(pattern, "search"), f"Pattern in {category} should be compiled regex"

    def test_exemption_contexts(self):
        """Test exemption context functionality."""
        # Test known exempted contexts
        assert phi_config.is_exempted_context("medical_literature")
        assert phi_config.is_exempted_context("pubmed")
        assert phi_config.is_exempted_context("research_paper")

        # Test non-exempted contexts
        assert not phi_config.is_exempted_context("patient_data")
        assert not phi_config.is_exempted_context("personal_info")

    def test_config_reload(self):
        """Test configuration reload functionality."""
        # Get initial patterns
        initial_patterns = phi_config.get_medical_literature_patterns()

        # Reload config
        phi_config.reload_config()

        # Get patterns again
        reloaded_patterns = phi_config.get_medical_literature_patterns()

        # Should be equivalent (deep comparison of structure)
        assert set(initial_patterns.keys()) == set(reloaded_patterns.keys())


class TestPHISanitizationFlow:
    """Test the complete PHI sanitization flow."""

    def test_request_sanitization_flow(self):
        """Test complete request sanitization flow."""
        # Test with research citation
        research_request = {
            "messages": [
                {"role": "user", "content": "What does Dr. Smith et al. say about heart disease?"}
            ]
        }

        sanitized = sanitize_request_data(research_request)
        # Should not be modified as it's research content
        assert sanitized["messages"][0]["content"] == research_request["messages"][0]["content"]

        # Test with medical terminology
        medical_request = {
            "messages": [{"role": "user", "content": "What are cardiovascular health symptoms?"}]
        }

        sanitized = sanitize_request_data(medical_request)
        # Should not be modified as it's medical terminology
        assert sanitized["messages"][0]["content"] == medical_request["messages"][0]["content"]

    def test_response_sanitization_flow(self):
        """Test complete response sanitization flow."""
        # Test with medical terminology in response
        medical_response = {
            "choices": [
                {
                    "message": {
                        "content": "Diabetes management involves monitoring blood glucose levels and medication adherence."
                    }
                }
            ]
        }

        sanitized = sanitize_response_data(medical_response)
        # Should not be modified as it's medical terminology
        assert (
            sanitized["choices"][0]["message"]["content"]
            == medical_response["choices"][0]["message"]["content"]
        )

    def test_error_handling_in_sanitization(self):
        """Test error handling in sanitization functions."""
        # Test with malformed request data
        malformed_request = {"invalid": "structure"}

        # Should not crash and should return the original data
        sanitized = sanitize_request_data(malformed_request)
        assert sanitized == malformed_request

        # Test with None values
        none_request = {"messages": None}
        sanitized = sanitize_request_data(none_request)
        assert sanitized == none_request

    def test_nested_data_structures(self):
        """Test handling of nested data structures."""
        complex_request = {
            "messages": [
                {"role": "user", "content": "According to Dr. Smith's research on diabetes..."},
                {"role": "assistant", "content": "Based on cardiovascular health studies..."},
                {"role": "user", "content": "Patient John Doe has these symptoms..."},
            ]
        }

        sanitized = sanitize_request_data(complex_request)

        # First two messages should be unchanged (research/medical content)
        assert sanitized["messages"][0]["content"] == complex_request["messages"][0]["content"]
        assert sanitized["messages"][1]["content"] == complex_request["messages"][1]["content"]

        # Third message contains patient data - behavior depends on PHI detector
        # At minimum, should not crash
        assert "messages" in sanitized
        assert len(sanitized["messages"]) == 3


class TestPatternMatching:
    """Test specific pattern matching functionality."""

    def test_research_citation_patterns(self):
        """Test research citation pattern matching."""
        from core.phi_sanitizer import _is_external_medical_content

        research_examples = [
            "Dr. Smith et al. published findings",
            "According to Anderson and colleagues",
            "Research by Johnson showed",
            "Study conducted by Brown et al. (2023)",
            "Published in Nature Medicine by Davis",
        ]

        for example in research_examples:
            assert _is_external_medical_content(example), (
                f"Should match research pattern: {example}"
            )

    def test_medical_terminology_patterns(self):
        """Test medical terminology pattern matching."""
        from core.phi_sanitizer import _is_external_medical_content

        medical_examples = [
            "cardiovascular health management",
            "diabetes treatment options",
            "cancer therapy protocols",
            "respiratory disease symptoms",
            "neurological examination findings",
        ]

        for example in medical_examples:
            assert _is_external_medical_content(example), (
                f"Should match medical terminology: {example}"
            )

    def test_patient_exclusion_patterns(self):
        """Test that patient-specific patterns are properly excluded."""
        from core.phi_sanitizer import _is_external_medical_content

        patient_examples = [
            "Patient Smith has diabetes",
            "Mr. Johnson was admitted",
            "The patient named Anderson",
            "Mary is a 45-year-old female",
        ]

        for example in patient_examples:
            assert not _is_external_medical_content(example), (
                f"Should NOT match patient pattern: {example}"
            )


class TestPerformanceAndEdgeCases:
    """Test performance and edge cases."""

    def test_empty_and_none_inputs(self):
        """Test handling of empty and None inputs."""
        from core.phi_sanitizer import _is_external_medical_content

        # Empty string
        assert not _is_external_medical_content("")

        # Whitespace only
        assert not _is_external_medical_content("   ")

        # Very long string
        long_text = (
            "Dr. Smith et al. published a comprehensive study on "
            + "cardiovascular " * 1000
            + "health"
        )
        # Should still work efficiently
        result = _is_external_medical_content(long_text)
        assert isinstance(result, bool)

    def test_unicode_and_special_characters(self):
        """Test handling of unicode and special characters."""
        from core.phi_sanitizer import _is_external_medical_content

        unicode_examples = [
            "Dr. Smith et al. published findings about café au lait spots",
            "Research by José García on diabetes",
            "Study on neurological symptoms with special chars: @#$%",
        ]

        for example in unicode_examples:
            # Should not crash
            result = _is_external_medical_content(example)
            assert isinstance(result, bool)

    def test_case_sensitivity(self):
        """Test case sensitivity handling."""
        from core.phi_sanitizer import _is_external_medical_content

        case_examples = [
            "dr. smith et al. published findings",  # lowercase
            "DR. SMITH ET AL. PUBLISHED FINDINGS",  # uppercase
            "Dr. SMITH Et Al. Published Findings",  # mixed case
        ]

        for example in case_examples:
            assert _is_external_medical_content(example), f"Should be case insensitive: {example}"


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])
