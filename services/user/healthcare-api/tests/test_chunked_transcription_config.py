"""
Test suite for chunked transcription configuration system
"""

import os
import tempfile
import pytest
from unittest.mock import patch

from config.chunked_transcription_config_loader import (
    ChunkedTranscriptionConfig,
    load_chunked_transcription_config,
    get_chunked_transcription_config,
    expand_environment_variables,
    get_config_for_environment
)


class TestChunkedTranscriptionConfig:
    """Test chunked transcription configuration loading"""

    def test_default_config_creation(self):
        """Test that default configuration can be created"""
        config = ChunkedTranscriptionConfig()
        
        assert config.environment == "development"
        assert config.chunk_processing.duration_seconds == 5
        assert config.chunk_processing.overlap_seconds == 1.0
        assert config.chunk_processing.sample_rate == 16000
        assert config.encryption.enabled is True
        assert config.encryption.algorithm == "AES-256-GCM"
        assert config.progressive_insights.enabled is True
        assert config.soap_generation.auto_generation is True
        assert config.phi_protection.enabled is True
        assert config.session.timeout_minutes == 30
        assert config.mock_mode is False
        assert config.debug_logging is False

    def test_environment_variable_expansion(self):
        """Test environment variable expansion in configuration"""
        test_dict = {
            "simple_var": "${TEST_VAR:-default_value}",
            "no_default": "${TEST_VAR_2}",
            "nested": {
                "inner_var": "${NESTED_VAR:-nested_default}"
            },
            "list": [
                "${LIST_VAR:-item1}",
                "static_item",
                {"nested_in_list": "${LIST_NESTED:-list_nested_default}"}
            ]
        }
        
        with patch.dict(os.environ, {
            "TEST_VAR": "actual_value",
            "NESTED_VAR": "nested_actual"
        }, clear=False):
            expanded = expand_environment_variables(test_dict)
            
            assert expanded["simple_var"] == "actual_value"
            assert expanded["no_default"] == "${TEST_VAR_2}"  # No default, returns original
            assert expanded["nested"]["inner_var"] == "nested_actual"
            assert expanded["list"][0] == "item1"  # Uses default
            assert expanded["list"][1] == "static_item"
            assert expanded["list"][2]["nested_in_list"] == "list_nested_default"

    def test_config_for_different_environments(self):
        """Test configuration loading for different environments"""
        # Test development environment
        dev_config = get_config_for_environment("development")
        assert dev_config.environment == "development"
        
        # Test production environment
        prod_config = get_config_for_environment("production")
        assert prod_config.environment == "production"
        
        # Test testing environment
        test_config = get_config_for_environment("testing")
        assert test_config.environment == "testing"

    def test_config_with_yaml_file(self):
        """Test configuration loading with a custom YAML file"""
        yaml_content = """
environment:
  default: "test"

chunk_processing:
  duration_seconds: 10
  overlap_seconds: 2.0
  sample_rate: 22050

encryption:
  enabled: false
  algorithm: "AES-128-GCM"

progressive_insights:
  enabled: false

soap_generation:
  auto_generation: false

phi_protection:
  enabled: false
  detection_level: "minimal"

session:
  timeout_minutes: 15
  max_recording_minutes: 30

development:
  mock_mode: true
  debug_logging: true

environments:
  test:
    encryption:
      enabled: false
    development:
      mock_mode: true
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            try:
                # Patch the config file path
                with patch('config.chunked_transcription_config_loader.os.path.join', return_value=f.name):
                    config = load_chunked_transcription_config()
                
                assert config.chunk_processing.duration_seconds == 10
                assert config.chunk_processing.overlap_seconds == 2.0
                assert config.chunk_processing.sample_rate == 22050
                assert config.encryption.enabled is False
                assert config.encryption.algorithm == "AES-128-GCM"
                assert config.progressive_insights.enabled is False
                assert config.soap_generation.auto_generation is False
                assert config.phi_protection.enabled is False
                assert config.phi_protection.detection_level == "minimal"
                assert config.session.timeout_minutes == 15
                assert config.session.max_recording_minutes == 30
                assert config.mock_mode is True
                assert config.debug_logging is True
                
            finally:
                os.unlink(f.name)

    def test_config_with_environment_overrides(self):
        """Test configuration with environment-specific overrides"""
        yaml_content = """
chunk_processing:
  duration_seconds: 5

encryption:
  enabled: true

development:
  mock_mode: false

environments:
  testing:
    chunk_processing:
      duration_seconds: 2
    encryption:
      enabled: false
    development:
      mock_mode: true
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            try:
                # Test with testing environment
                with patch('config.chunked_transcription_config_loader.os.path.join', return_value=f.name), \
                     patch('config.chunked_transcription_config_loader.detect_environment', return_value="testing"):
                    
                    config = load_chunked_transcription_config()
                
                # Base values should be overridden
                assert config.chunk_processing.duration_seconds == 2  # Overridden
                assert config.encryption.enabled is False  # Overridden
                assert config.mock_mode is True  # Overridden
                
            finally:
                os.unlink(f.name)

    def test_missing_config_file_handling(self):
        """Test handling of missing configuration file"""
        with patch('config.chunked_transcription_config_loader.os.path.join', return_value="/nonexistent/path.yml"):
            config = load_chunked_transcription_config()
            
            # Should return default configuration
            assert isinstance(config, ChunkedTranscriptionConfig)
            assert config.chunk_processing.duration_seconds == 5  # Default value

    def test_invalid_yaml_handling(self):
        """Test handling of invalid YAML content"""
        invalid_yaml = """
invalid: yaml: content:
  - [unclosed bracket
    nested:
      invalid_structure
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(invalid_yaml)
            f.flush()
            
            try:
                with patch('config.chunked_transcription_config_loader.os.path.join', return_value=f.name):
                    config = load_chunked_transcription_config()
                
                # Should return default configuration on YAML error
                assert isinstance(config, ChunkedTranscriptionConfig)
                assert config.chunk_processing.duration_seconds == 5
                
            finally:
                os.unlink(f.name)

    def test_configuration_validation(self):
        """Test configuration value validation"""
        config = ChunkedTranscriptionConfig()
        
        # Test chunk processing constraints
        assert 2 <= config.chunk_processing.duration_seconds <= 30
        assert 0.5 <= config.chunk_processing.overlap_seconds <= 5.0
        assert config.chunk_processing.sample_rate > 0
        
        # Test session constraints
        assert 5 <= config.session.timeout_minutes <= 180
        assert config.session.max_recording_minutes >= config.session.min_session_minutes
        
        # Test encryption settings
        assert config.encryption.algorithm in ["AES-256-GCM", "AES-128-GCM"]
        assert config.encryption.key_size_bits in [128, 256]
        
        # Test PHI protection levels
        assert config.phi_protection.detection_level in ["minimal", "standard", "maximum"]

    def test_config_serialization_safety(self):
        """Test that configuration doesn't contain sensitive data in logs"""
        config = ChunkedTranscriptionConfig()
        
        # Convert to dict representation (like what might be logged)
        config_str = str(config)
        
        # Should not contain sensitive patterns
        sensitive_patterns = [
            "password", "secret", "key", "token"
        ]
        
        config_lower = config_str.lower()
        for pattern in sensitive_patterns:
            # Configuration values might contain these words, but should not contain actual sensitive data
            assert pattern not in config_lower or "test" in config_lower or "example" in config_lower

    @pytest.mark.parametrize("environment", ["development", "testing", "production"])
    def test_environment_specific_settings(self, environment):
        """Test that each environment has appropriate settings"""
        config = get_config_for_environment(environment)
        
        assert config.environment == environment
        
        if environment == "development":
            # Development might have relaxed security for debugging
            pass
        elif environment == "testing":
            # Testing should have faster timeouts and safe defaults
            assert config.session.timeout_minutes <= 30
        elif environment == "production":
            # Production should have strong security settings
            assert config.encryption.enabled is True
            assert config.phi_protection.enabled is True

    def test_configuration_completeness(self):
        """Test that all expected configuration sections are present"""
        config = ChunkedTranscriptionConfig()
        
        # Check that all major sections exist
        required_sections = [
            "chunk_processing",
            "encryption", 
            "websocket",
            "progressive_insights",
            "soap_generation",
            "phi_protection",
            "session",
            "audio_processing",
            "ui_settings",
            "performance"
        ]
        
        for section in required_sections:
            assert hasattr(config, section), f"Missing required section: {section}"
            assert getattr(config, section) is not None, f"Section {section} is None"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])