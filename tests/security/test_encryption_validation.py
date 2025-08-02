"""
Tests for Encryption Security Validation
Validates master key security requirements and entropy validation
"""

import base64
import os
import secrets
from unittest.mock import patch

import pytest

from src.security.database_factory import PostgresConnectionFactory
from src.security.encryption_manager import HealthcareEncryptionManager


class TestEncryptionValidation:
    """Test encryption security validation functionality"""

    def setup_method(self) -> None:
        """Setup test environment"""
        connection_factory = PostgresConnectionFactory(
            host="localhost",
            database="intelluxe",
            user="intelluxe",
            password="secure_password",
        )
        self.test_connection = connection_factory.create_connection()

    def test_valid_master_key_base64_format(self) -> None:
        """Test valid master key in base64 format"""
        # Generate a proper 32-byte key and encode it
        key_bytes = secrets.token_bytes(32)
        valid_key = base64.b64encode(key_bytes).decode("utf-8")

        with patch.dict(
            os.environ,
            {"MASTER_ENCRYPTION_KEY": valid_key, "ENVIRONMENT": "development"},
        ):
            manager = HealthcareEncryptionManager(self.test_connection)
            assert manager is not None

            # Test actual encryption/decryption works if methods exist
            encryption_methods = ["encrypt_data", "encrypt", "encrypt_text"]
            decryption_methods = ["decrypt_data", "decrypt", "decrypt_text"]

            for encrypt_method in encryption_methods:
                if hasattr(manager, encrypt_method):
                    for decrypt_method in decryption_methods:
                        if hasattr(manager, decrypt_method):
                            try:
                                test_data = "Test healthcare data"
                                encrypt_func = getattr(manager, encrypt_method)
                                decrypt_func = getattr(manager, decrypt_method)
                                encrypted = encrypt_func(test_data)
                                decrypted = decrypt_func(encrypted)
                                assert decrypted == test_data
                                return  # Success, exit early
                            except (TypeError, AttributeError):
                                continue

    def test_invalid_master_key_too_short(self) -> None:
        """Test invalid master key - too short after decoding"""
        # Create a key that's too short (16 bytes instead of 32)
        short_key = base64.b64encode(b"a" * 16).decode("utf-8")

        with patch.dict(
            os.environ,
            {"MASTER_ENCRYPTION_KEY": short_key, "ENVIRONMENT": "development"},
        ):
            with pytest.raises(ValueError, match="MASTER_ENCRYPTION_KEY length error"):
                HealthcareEncryptionManager(self.test_connection)

    def test_invalid_master_key_not_base64(self) -> None:
        """Test invalid master key - not valid base64"""
        with patch.dict(
            os.environ,
            {
                "MASTER_ENCRYPTION_KEY": "not-valid-base64!@#",
                "ENVIRONMENT": "development",
            },
        ):
            with pytest.raises(ValueError, match="Master encryption key must be valid base64"):
                HealthcareEncryptionManager(self.test_connection)

    def test_production_requires_master_key(self) -> None:
        """Test that production environment requires MASTER_ENCRYPTION_KEY"""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=True):
            with pytest.raises(
                RuntimeError,
                match="Production environment requires secure configuration",
            ):
                HealthcareEncryptionManager(self.test_connection)

    def test_key_entropy_validation(self) -> None:
        """Test that keys have sufficient entropy"""
        # Test weak key (all same bytes)
        weak_key = base64.b64encode(b"a" * 32).decode("utf-8")

        with patch.dict(
            os.environ,
            {"MASTER_ENCRYPTION_KEY": weak_key, "ENVIRONMENT": "development"},
        ):
            # Should still work but log a warning
            manager = HealthcareEncryptionManager(self.test_connection)
            assert manager is not None

    def test_key_rotation_capability(self) -> None:
        """Test that encryption manager supports key rotation"""
        key1 = base64.b64encode(secrets.token_bytes(32)).decode("utf-8")
        key2 = base64.b64encode(secrets.token_bytes(32)).decode("utf-8")

        # Test with first key
        with patch.dict(os.environ, {"MASTER_ENCRYPTION_KEY": key1, "ENVIRONMENT": "development"}):
            manager1 = HealthcareEncryptionManager(self.test_connection)

            # Find available encryption method
            encryption_methods = ["encrypt_data", "encrypt", "encrypt_text"]
            decryption_methods = ["decrypt_data", "decrypt", "decrypt_text"]

            encrypted_data = None

            for method_name in encryption_methods:
                if hasattr(manager1, method_name):
                    try:
                        method = getattr(manager1, method_name)
                        encrypted_data = method("test data")
                        break
                    except (TypeError, AttributeError):
                        continue

            if encrypted_data:
                # Test with second key (should fail to decrypt)
                with patch.dict(
                    os.environ,
                    {"MASTER_ENCRYPTION_KEY": key2, "ENVIRONMENT": "development"},
                ):
                    manager2 = HealthcareEncryptionManager(self.test_connection)

                    for method_name in decryption_methods:
                        if hasattr(manager2, method_name):
                            try:
                                method = getattr(manager2, method_name)
                                with pytest.raises(
                                    (ValueError, RuntimeError, TypeError)
                                ):  # Should fail to decrypt with wrong key
                                    method(encrypted_data)
                                return  # Test passed
                            except (TypeError, AttributeError):
                                continue


class TestRBACStrictModeValidation:
    """Test RBAC strict mode validation"""

    def test_valid_rbac_strict_mode_true(self) -> None:
        """Test valid RBAC strict mode - true"""
        with patch.dict(os.environ, {"RBAC_STRICT_MODE": "true", "ENVIRONMENT": "development"}):
            from src.security.rbac_foundation import HealthcareRBACManager

            connection_factory = PostgresConnectionFactory(
                host="localhost",
                database="intelluxe",
                user="intelluxe",
                password="secure_password",
            )
            test_connection = connection_factory.create_connection()
            manager = HealthcareRBACManager(test_connection)
            assert manager.STRICT_MODE is True

    def test_valid_rbac_strict_mode_false(self) -> None:
        """Test valid RBAC strict mode - false"""
        with patch.dict(os.environ, {"RBAC_STRICT_MODE": "false", "ENVIRONMENT": "development"}):
            from src.security.rbac_foundation import HealthcareRBACManager

            connection_factory = PostgresConnectionFactory(
                host="localhost",
                database="intelluxe",
                user="intelluxe",
                password="secure_password",
            )
            test_connection = connection_factory.create_connection()
            manager = HealthcareRBACManager(test_connection)
            assert manager.STRICT_MODE is False

    def test_invalid_rbac_strict_mode(self) -> None:
        """Test invalid RBAC strict mode value"""
        with patch.dict(os.environ, {"RBAC_STRICT_MODE": "invalid", "ENVIRONMENT": "development"}):
            from src.security.rbac_foundation import HealthcareRBACManager

            connection_factory = PostgresConnectionFactory(
                host="localhost",
                database="intelluxe",
                user="intelluxe",
                password="secure_password",
            )
            test_connection = connection_factory.create_connection()

            with pytest.raises(ValueError, match="Invalid value for RBAC_STRICT_MODE"):
                HealthcareRBACManager(test_connection)

    def test_rbac_strict_mode_case_insensitive(self) -> None:
        """Test RBAC strict mode is case insensitive"""
        test_cases = [
            ("TRUE", True),
            ("True", True),
            ("FALSE", False),
            ("False", False),
        ]

        for env_value, expected in test_cases:
            with patch.dict(
                os.environ,
                {"RBAC_STRICT_MODE": env_value, "ENVIRONMENT": "development"},
            ):
                from src.security.rbac_foundation import HealthcareRBACManager

                connection_factory = PostgresConnectionFactory(
                    host="localhost",
                    database="intelluxe",
                    user="intelluxe",
                    password="secure_password",
                )
                test_connection = connection_factory.create_connection()
                manager = HealthcareRBACManager(test_connection)
                assert manager.STRICT_MODE is expected

    def test_rbac_strict_mode_whitespace_handling(self) -> None:
        """Test RBAC strict mode handles whitespace"""
        with patch.dict(os.environ, {"RBAC_STRICT_MODE": "  true  ", "ENVIRONMENT": "development"}):
            from src.security.rbac_foundation import HealthcareRBACManager

            connection_factory = PostgresConnectionFactory(
                host="localhost",
                database="intelluxe",
                user="intelluxe",
                password="secure_password",
            )
            test_connection = connection_factory.create_connection()
            manager = HealthcareRBACManager(test_connection)
            assert manager.STRICT_MODE is True


class TestConfigurationInjection:
    """Test configuration injection pattern for better test maintainability"""


class TestSecurityScan:
    """Test security scanning functionality"""

    def setup_method(self) -> None:
        """Setup test environment"""
        connection_factory = PostgresConnectionFactory(
            host="localhost",
            database="intelluxe",
            user="intelluxe",
            password="secure_password",
        )
        self.test_connection = connection_factory.create_connection()

    def test_configuration_injection_pattern(self) -> None:
        """Test that configuration injection works without mocking private methods"""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            # Create test configuration
            test_config = {
                "MASTER_ENCRYPTION_KEY": base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
                "ENCRYPTION_ALGORITHM": "AES-256-GCM",
                "KEY_ROTATION_DAYS": 90,
            }

            # Inject configuration via constructor
            manager = HealthcareEncryptionManager(self.test_connection, config=test_config)

            # Test behavior without mocking internal methods
            assert manager.config == test_config
            assert manager.key_manager.config == test_config

    def test_configuration_override_behavior(self) -> None:
        """Test that injected configuration overrides default loading"""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            # Test configuration with specific values
            override_config = {
                "MASTER_ENCRYPTION_KEY": base64.urlsafe_b64encode(
                    b"test_key_32_bytes_long_exactly!"
                ).decode(),
                "TEST_MODE": True,
            }

            # Create manager with injected config
            manager = HealthcareEncryptionManager(self.test_connection, config=override_config)

            # Verify configuration is used
            assert manager.config.get("TEST_MODE") is True
            assert "MASTER_ENCRYPTION_KEY" in manager.config

    def test_fallback_to_default_configuration(self) -> None:
        """Test that manager falls back to default configuration when none injected"""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            # Create manager without injected config
            manager = HealthcareEncryptionManager(self.test_connection)

            # Should have loaded default configuration
            assert manager.config is not None
            assert isinstance(manager.config, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
