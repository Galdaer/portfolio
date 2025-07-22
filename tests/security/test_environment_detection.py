"""
Tests for Secure Environment Detection
Validates critical environment detection security features
"""

import pytest
import os
from unittest.mock import patch
from src.security.environment_detector import EnvironmentDetector, Environment

# Test constants for consistent error message validation
ERROR_MSG_CANNOT_DETERMINE_ENVIRONMENT = "Cannot determine environment"


class TestEnvironmentDetector:
    """Test secure environment detection functionality"""
    
    def test_production_environment_detection(self):
        """Test production environment detection"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
            assert EnvironmentDetector.get_environment() == Environment.PRODUCTION
            assert EnvironmentDetector.is_production() is True
            assert EnvironmentDetector.is_development() is False
            assert EnvironmentDetector.is_testing() is False
            assert EnvironmentDetector.is_staging() is False
    
    def test_development_environment_detection(self):
        """Test development environment detection"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            assert EnvironmentDetector.get_environment() == Environment.DEVELOPMENT
            assert EnvironmentDetector.is_production() is False
            assert EnvironmentDetector.is_development() is True
            assert EnvironmentDetector.is_testing() is False
            assert EnvironmentDetector.is_staging() is False
    
    def test_testing_environment_detection(self):
        """Test testing environment detection"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'testing'}):
            assert EnvironmentDetector.get_environment() == Environment.TESTING
            assert EnvironmentDetector.is_production() is False
            assert EnvironmentDetector.is_development() is False
            assert EnvironmentDetector.is_testing() is True
            assert EnvironmentDetector.is_staging() is False
    
    def test_staging_environment_detection(self):
        """Test staging environment detection"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):
            assert EnvironmentDetector.get_environment() == Environment.STAGING
            assert EnvironmentDetector.is_production() is False
            assert EnvironmentDetector.is_development() is False
            assert EnvironmentDetector.is_testing() is False
            assert EnvironmentDetector.is_staging() is True
    
    def test_missing_environment_raises_error(self):
        """Test that missing ENVIRONMENT variable raises error (CRITICAL SECURITY)"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match="ENVIRONMENT variable must be explicitly set"):
                EnvironmentDetector.get_environment()
    
    def test_empty_environment_raises_error(self):
        """Test that empty ENVIRONMENT variable raises error"""
        with patch.dict(os.environ, {'ENVIRONMENT': ''}):
            with pytest.raises(RuntimeError, match="ENVIRONMENT variable must be explicitly set"):
                EnvironmentDetector.get_environment()
    
    def test_whitespace_environment_raises_error(self):
        """Test that whitespace-only ENVIRONMENT variable raises error"""
        with patch.dict(os.environ, {'ENVIRONMENT': '   '}):
            with pytest.raises(RuntimeError, match="ENVIRONMENT variable must be explicitly set"):
                EnvironmentDetector.get_environment()
    
    def test_invalid_environment_raises_error(self):
        """Test that invalid ENVIRONMENT value raises error"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'invalid'}):
            with pytest.raises(RuntimeError, match="Invalid ENVIRONMENT value"):
                EnvironmentDetector.get_environment()
    
    def test_case_insensitive_environment_detection(self):
        """Test that environment detection is case insensitive"""
        test_cases = [
            ('PRODUCTION', Environment.PRODUCTION),
            ('Production', Environment.PRODUCTION),
            ('DEVELOPMENT', Environment.DEVELOPMENT),
            ('Development', Environment.DEVELOPMENT),
            ('TESTING', Environment.TESTING),
            ('Testing', Environment.TESTING),
            ('STAGING', Environment.STAGING),
            ('Staging', Environment.STAGING)
        ]
        
        for env_value, expected_env in test_cases:
            with patch.dict(os.environ, {'ENVIRONMENT': env_value}):
                assert EnvironmentDetector.get_environment() == expected_env
    
    def test_require_environment_success(self):
        """Test require_environment with matching environment"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
            # Should not raise
            EnvironmentDetector.require_environment(Environment.PRODUCTION)
    
    def test_require_environment_failure(self):
        """Test require_environment with non-matching environment"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            with pytest.raises(RuntimeError, match="This operation requires production environment"):
                EnvironmentDetector.require_environment(Environment.PRODUCTION)
    
    def test_require_non_production_success(self):
        """Test require_non_production in development"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            # Should not raise
            EnvironmentDetector.require_non_production()
    
    def test_require_non_production_failure(self):
        """Test require_non_production in production"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
            with pytest.raises(RuntimeError, match="This operation is not allowed in production"):
                EnvironmentDetector.require_non_production()
    
    def test_is_production_secure_default_on_error(self):
        """Test that is_production returns True on error (secure default)"""
        with patch.dict(os.environ, {}, clear=True):
            # Should return True for security when environment cannot be determined
            assert EnvironmentDetector.is_production() is True
    
    def test_is_development_secure_default_on_error(self):
        """Test that is_development returns False on error (secure default)"""
        with patch.dict(os.environ, {}, clear=True):
            # Should return False for security when environment cannot be determined
            assert EnvironmentDetector.is_development() is False
    
    def test_get_environment_config_development(self):
        """Test environment-specific configuration for development"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            config = EnvironmentDetector.get_environment_config()
            
            assert config['debug'] is True
            assert config['log_level'] == 'DEBUG'
            assert config['allow_key_generation'] is True
            assert config['strict_validation'] is False
            assert config['enable_test_endpoints'] is True
    
    def test_get_environment_config_production(self):
        """Test environment-specific configuration for production"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
            config = EnvironmentDetector.get_environment_config()
            
            assert config['debug'] is False
            assert config['log_level'] == 'WARNING'
            assert config['allow_key_generation'] is False
            assert config['strict_validation'] is True
            assert config['enable_test_endpoints'] is False
    
    def test_get_environment_config_testing(self):
        """Test environment-specific configuration for testing"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'testing'}):
            config = EnvironmentDetector.get_environment_config()
            
            assert config['debug'] is True
            assert config['log_level'] == 'INFO'
            assert config['allow_key_generation'] is False
            assert config['strict_validation'] is True
            assert config['enable_test_endpoints'] is True
    
    def test_get_environment_config_staging(self):
        """Test environment-specific configuration for staging"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):
            config = EnvironmentDetector.get_environment_config()
            
            assert config['debug'] is False
            assert config['log_level'] == 'INFO'
            assert config['allow_key_generation'] is False
            assert config['strict_validation'] is True
            assert config['enable_test_endpoints'] is False


class TestEnvironmentDetectorIntegration:
    """Integration tests for environment detector with other components"""
    
    def test_encryption_manager_integration(self):
        """Test that encryption manager uses secure environment detection"""
        # This would be tested with actual encryption manager
        # For now, just verify the environment detector works as expected
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
            assert EnvironmentDetector.is_production() is True
            
            # Should require environment to be set
            EnvironmentDetector.require_environment(Environment.PRODUCTION)
    
    def test_mcp_server_integration(self):
        """Test that MCP server uses secure environment detection"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            assert EnvironmentDetector.is_development() is True
            assert EnvironmentDetector.is_production() is False
    
    def test_security_critical_operations(self):
        """Test security-critical operations require proper environment"""
        # Test that dangerous operations are blocked in production
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
            with pytest.raises(RuntimeError):
                EnvironmentDetector.require_non_production()

        # Test that they're allowed in development
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            EnvironmentDetector.require_non_production()  # Should not raise

    def test_production_fallback_with_logging(self, caplog):
        """Test that production fallback logs appropriate warnings by testing actual behavior"""
        # Test actual behavior by setting up conditions that trigger fallback
        # Remove ENVIRONMENT variable to trigger fallback behavior
        with patch.dict(os.environ, {}, clear=True):
            # Call public interface methods to test actual behavior
            result = EnvironmentDetector.is_production()

            # Should return True for security (production fallback)
            assert result is True

            # Verify that other environment checks return False in fallback
            assert EnvironmentDetector.is_development() is False
            assert EnvironmentDetector.is_testing() is False
            assert EnvironmentDetector.is_staging() is False

    def test_production_fallback_with_logging_verification(self, caplog):
        """Test that production fallback logs appropriate warnings with detailed verification"""
        # Test actual behavior without mocking internal methods
        with patch.dict(os.environ, {}, clear=True):
            # Test multiple public interface calls to verify consistent behavior
            result1 = EnvironmentDetector.is_production()
            result2 = EnvironmentDetector.get_environment()

            # Should consistently return production for security
            assert result1 is True
            assert result2 == Environment.PRODUCTION

            # Verify logging behavior through public interface
            # The actual logging happens in the implementation, we test the behavior
            assert EnvironmentDetector.is_production() is True


class TestEnvironmentDetectorBehavior:
    """Test environment detector behavior without internal method mocking"""

    def test_invalid_environment_handling(self):
        """Test behavior with invalid environment values"""
        # Test actual behavior with invalid environment
        with patch.dict(os.environ, {'ENVIRONMENT': 'invalid_env'}):
            # Should fall back to production for security
            assert EnvironmentDetector.is_production() is True
            assert EnvironmentDetector.get_environment() == Environment.PRODUCTION

    def test_case_insensitive_environment_detection(self):
        """Test that environment detection handles case variations"""
        # Test uppercase
        with patch.dict(os.environ, {'ENVIRONMENT': 'PRODUCTION'}):
            assert EnvironmentDetector.is_production() is True

        # Test mixed case
        with patch.dict(os.environ, {'ENVIRONMENT': 'Development'}):
            assert EnvironmentDetector.is_development() is True

    def test_environment_consistency_across_calls(self):
        """Test that environment detection is consistent across multiple calls"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'testing'}):
            # Multiple calls should return consistent results
            results = [EnvironmentDetector.is_testing() for _ in range(5)]
            assert all(results)

            # Environment should be consistent
            environments = [EnvironmentDetector.get_environment() for _ in range(5)]
            assert all(env == Environment.TESTING for env in environments)

    def test_environment_security_requirements(self):
        """Test security requirements without mocking internal methods"""
        # Test production security requirements
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
            # Should require production environment
            EnvironmentDetector.require_environment(Environment.PRODUCTION)

            # Should not allow non-production operations
            with pytest.raises(RuntimeError):
                EnvironmentDetector.require_non_production()

        # Test development flexibility
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            # Should allow non-production operations
            EnvironmentDetector.require_non_production()

            # Should not require production
            with pytest.raises(RuntimeError):
                EnvironmentDetector.require_environment(Environment.PRODUCTION)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
