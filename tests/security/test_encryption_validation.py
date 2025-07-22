"""
Tests for Encryption Security Validation
Validates master key security requirements and entropy validation
"""

import pytest
import base64
import secrets
import os
from unittest.mock import patch, Mock
from src.security.encryption_manager import HealthcareEncryptionManager
from src.security.database_factory import MockConnectionFactory
from src.security.environment_detector import Environment


class TestEncryptionValidation:
    """Test encryption security validation functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.mock_factory = MockConnectionFactory()
        
    def test_master_key_length_validation_too_short(self):
        """Test master key minimum length validation - too short"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            manager = HealthcareEncryptionManager(self.mock_factory)
            
            # Test short key (should fail)
            short_key = base64.urlsafe_b64encode(b'short').decode()
            config = {"MASTER_ENCRYPTION_KEY": short_key}
            
            with patch.object(manager, '_load_configuration', return_value=config):
                with pytest.raises(ValueError, match="minimum length requirements"):
                    manager._get_or_create_master_key()
    
    def test_master_key_length_validation_minimum_valid(self):
        """Test master key minimum length validation - exactly 32 bytes"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            manager = HealthcareEncryptionManager(self.mock_factory)
            
            # Test minimum valid key (32 bytes)
            valid_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
            config = {"MASTER_ENCRYPTION_KEY": valid_key}
            
            with patch.object(manager, '_load_configuration', return_value=config):
                result = manager._get_or_create_master_key()
                assert len(result) == 32
    
    def test_master_key_entropy_validation_low_entropy(self):
        """Test master key entropy validation - low entropy key"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            manager = HealthcareEncryptionManager(self.mock_factory)
            
            # Test low entropy key (all zeros)
            low_entropy_key = base64.urlsafe_b64encode(b'\x00' * 32).decode()
            config = {"MASTER_ENCRYPTION_KEY": low_entropy_key}
            
            with patch.object(manager, '_load_configuration', return_value=config):
                with pytest.raises(ValueError, match="entropy requirements"):
                    manager._get_or_create_master_key()
    
    def test_master_key_entropy_validation_high_entropy(self):
        """Test master key entropy validation - high entropy key"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            manager = HealthcareEncryptionManager(self.mock_factory)
            
            # Test high entropy key
            high_entropy_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
            config = {"MASTER_ENCRYPTION_KEY": high_entropy_key}
            
            with patch.object(manager, '_load_configuration', return_value=config):
                result = manager._get_or_create_master_key()
                assert len(result) == 32
    
    def test_master_key_invalid_base64(self):
        """Test master key validation - invalid base64"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            manager = HealthcareEncryptionManager(self.mock_factory)
            
            # Test invalid base64
            invalid_key = "not_valid_base64!"
            config = {"MASTER_ENCRYPTION_KEY": invalid_key}
            
            with patch.object(manager, '_load_configuration', return_value=config):
                with pytest.raises(ValueError, match="not valid base64"):
                    manager._get_or_create_master_key()
    
    def test_entropy_calculation_empty_data(self):
        """Test entropy calculation with empty data"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            manager = HealthcareEncryptionManager(self.mock_factory)
            
            entropy = manager._calculate_entropy(b'')
            assert entropy == 0.0
    
    def test_entropy_calculation_uniform_data(self):
        """Test entropy calculation with uniform data (high entropy)"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            manager = HealthcareEncryptionManager(self.mock_factory)
            
            # Random data should have high entropy
            random_data = secrets.token_bytes(32)
            entropy = manager._calculate_entropy(random_data)
            assert entropy > 4.0  # Should be well above threshold
    
    def test_entropy_calculation_low_entropy_data(self):
        """Test entropy calculation with low entropy data"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            manager = HealthcareEncryptionManager(self.mock_factory)
            
            # Repeated pattern has low entropy
            low_entropy_data = b'AAAA' * 8  # 32 bytes of repeated 'A'
            entropy = manager._calculate_entropy(low_entropy_data)
            assert entropy < 4.0  # Should be below threshold
    
    def test_generate_secure_key_development_only(self):
        """Test secure key generation only works in development"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            manager = HealthcareEncryptionManager(self.mock_factory)
            
            # Should work in development
            key = manager.generate_secure_key()
            assert len(key) > 0
            
            # Verify it's valid base64
            decoded = base64.urlsafe_b64decode(key.encode())
            assert len(decoded) == 32
    
    def test_generate_secure_key_production_blocked(self):
        """Test secure key generation blocked in production"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
            manager = HealthcareEncryptionManager(self.mock_factory)
            
            # Should fail in production
            with pytest.raises(RuntimeError, match="requires development environment"):
                manager.generate_secure_key()
    
    def test_generate_secure_key_entropy_validation(self):
        """Test generated secure key meets entropy requirements"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            manager = HealthcareEncryptionManager(self.mock_factory)
            
            # Generate key and verify entropy
            key = manager.generate_secure_key()
            decoded_key = base64.urlsafe_b64decode(key.encode())
            entropy = manager._calculate_entropy(decoded_key)
            
            assert entropy >= 4.0  # Should meet minimum entropy requirement
    
    def test_production_requires_master_key(self):
        """Test that production environment requires master key"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
            manager = HealthcareEncryptionManager(self.mock_factory)
            
            # No master key in config
            config = {}
            
            with patch.object(manager, '_load_configuration', return_value=config):
                with pytest.raises(RuntimeError, match="MASTER_ENCRYPTION_KEY must be set in production"):
                    manager._get_or_create_master_key()
    
    def test_development_allows_key_generation(self):
        """Test that development environment allows key generation"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            manager = HealthcareEncryptionManager(self.mock_factory)
            
            # No master key in config
            config = {}
            
            with patch.object(manager, '_load_configuration', return_value=config):
                result = manager._get_or_create_master_key()
                assert len(result) == 32  # Should generate 32-byte key
    
    def test_staging_blocks_key_generation(self):
        """Test that staging environment blocks key generation"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):
            manager = HealthcareEncryptionManager(self.mock_factory)
            
            # No master key in config
            config = {}
            
            with patch.object(manager, '_load_configuration', return_value=config):
                with pytest.raises(RuntimeError, match="Key generation only allowed in development"):
                    manager._get_or_create_master_key()


class TestRBACStrictModeValidation:
    """Test RBAC strict mode validation"""
    
    def test_valid_rbac_strict_mode_true(self):
        """Test valid RBAC strict mode - true"""
        with patch.dict(os.environ, {'RBAC_STRICT_MODE': 'true', 'ENVIRONMENT': 'development'}):
            from src.security.rbac_foundation import HealthcareRBACManager
            from src.security.database_factory import MockConnectionFactory
            
            mock_factory = MockConnectionFactory()
            manager = HealthcareRBACManager(mock_factory)
            assert manager.STRICT_MODE is True
    
    def test_valid_rbac_strict_mode_false(self):
        """Test valid RBAC strict mode - false"""
        with patch.dict(os.environ, {'RBAC_STRICT_MODE': 'false', 'ENVIRONMENT': 'development'}):
            from src.security.rbac_foundation import HealthcareRBACManager
            from src.security.database_factory import MockConnectionFactory
            
            mock_factory = MockConnectionFactory()
            manager = HealthcareRBACManager(mock_factory)
            assert manager.STRICT_MODE is False
    
    def test_invalid_rbac_strict_mode(self):
        """Test invalid RBAC strict mode value"""
        with patch.dict(os.environ, {'RBAC_STRICT_MODE': 'invalid', 'ENVIRONMENT': 'development'}):
            from src.security.rbac_foundation import HealthcareRBACManager
            from src.security.database_factory import MockConnectionFactory
            
            mock_factory = MockConnectionFactory()
            
            with pytest.raises(ValueError, match="Invalid value for RBAC_STRICT_MODE"):
                HealthcareRBACManager(mock_factory)
    
    def test_rbac_strict_mode_case_insensitive(self):
        """Test RBAC strict mode is case insensitive"""
        test_cases = [
            ('TRUE', True),
            ('True', True),
            ('FALSE', False),
            ('False', False)
        ]
        
        for env_value, expected in test_cases:
            with patch.dict(os.environ, {'RBAC_STRICT_MODE': env_value, 'ENVIRONMENT': 'development'}):
                from src.security.rbac_foundation import HealthcareRBACManager
                from src.security.database_factory import MockConnectionFactory
                
                mock_factory = MockConnectionFactory()
                manager = HealthcareRBACManager(mock_factory)
                assert manager.STRICT_MODE is expected
    
    def test_rbac_strict_mode_whitespace_handling(self):
        """Test RBAC strict mode handles whitespace"""
        with patch.dict(os.environ, {'RBAC_STRICT_MODE': '  true  ', 'ENVIRONMENT': 'development'}):
            from src.security.rbac_foundation import HealthcareRBACManager
            from src.security.database_factory import MockConnectionFactory
            
            mock_factory = MockConnectionFactory()
            manager = HealthcareRBACManager(mock_factory)
            assert manager.STRICT_MODE is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
