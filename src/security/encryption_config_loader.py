"""Centralized encryption configuration management for healthcare AI system"""

import base64
import os
import secrets

from src.security.environment_detector import EnvironmentDetector


class EncryptionConfigLoader:
    """Centralized encryption configuration management"""

    @staticmethod
    def get_or_create_master_key(logger, config=None) -> bytes:
        """Get or create master encryption key with proper base64 encoding"""
        master_key_str = os.getenv("MASTER_ENCRYPTION_KEY")

        if EnvironmentDetector.is_production():
            if not master_key_str:
                logger.error("MASTER_ENCRYPTION_KEY not configured for production environment")
                raise RuntimeError(
                    "Critical security configuration missing: MASTER_ENCRYPTION_KEY. "
                    "Ensure the MASTER_ENCRYPTION_KEY is set in the environment variables or configuration files. "
                    "Contact the system administrator for assistance."
                )

            # Validate key format and entropy
            if len(master_key_str) < 32:
                logger.error("MASTER_ENCRYPTION_KEY does not meet minimum length requirements")
                raise ValueError(
                    "MASTER_ENCRYPTION_KEY must be at least 32 characters long. "
                    "Generate a new key using: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
                )

        if master_key_str:
            # Use helper function to handle all key conversion logic
            return EncryptionConfigLoader.create_fernet_key_from_string(master_key_str)
        else:
            # Generate key for development - return base64 encoded
            return EncryptionConfigLoader._get_or_create_development_key(logger, config)

    @staticmethod
    def _get_or_create_development_key(logger, config=None) -> bytes:
        """Generate or load development encryption key with persistence"""

        # Use config path if provided, otherwise default
        if config and isinstance(config, dict) and config.get("dev_key_path"):
            key_file = config["dev_key_path"]
        else:
            key_file = os.path.join(
                os.getenv("CFG_ROOT", "/opt/intelluxe/stack"), "security", "dev_master_key"
            )

        try:
            if os.path.exists(key_file):
                with open(key_file, "rb") as f:
                    stored_key = f.read().strip()
                    # Validate it's proper base64
                    try:
                        decoded = base64.urlsafe_b64decode(stored_key + b"==")
                        if len(decoded) == 32:
                            return stored_key  # Already base64 encoded
                    except Exception:
                        pass

            # Generate new key and store as base64
            key_bytes = secrets.token_bytes(32)
            encoded_key = base64.urlsafe_b64encode(key_bytes)

            # Store for persistence
            os.makedirs(os.path.dirname(key_file), exist_ok=True)
            with open(key_file, "wb") as f:
                f.write(encoded_key)
            os.chmod(key_file, 0o600)

            logger.warning("Using generated encryption key - not suitable for production")
            return encoded_key

        except Exception as e:
            logger.warning(f"Development key persistence failed: {e}")
            # Fallback to in-memory key
            key_bytes = secrets.token_bytes(32)
            encoded_key = base64.urlsafe_b64encode(key_bytes)
            logger.warning("Using generated encryption key - not suitable for production")
            return encoded_key

    @staticmethod
    def calculate_base64_padding(length: int) -> int:
        """Calculate required padding for base64 decoding"""
        return (4 - length % 4) % 4

    @staticmethod
    def validate_fernet_key_length(key_bytes: bytes) -> bool:
        """Validate that key bytes are the correct length for Fernet (32 bytes)"""
        return len(key_bytes) == 32

    @staticmethod
    def normalize_string_to_fernet_key(key_str: str) -> bytes:
        """Convert a string to a properly formatted 32-byte Fernet key"""
        key_bytes = key_str.encode("utf-8")[:32].ljust(32, b"\0")
        return base64.urlsafe_b64encode(key_bytes)

    @staticmethod
    def try_decode_as_base64_key(key_str: str) -> tuple[bool, bytes]:
        """
        Attempt to decode string as base64 and validate as Fernet key

        Returns:
            tuple: (success: bool, key_bytes: bytes)
        """
        try:
            padding = EncryptionConfigLoader.calculate_base64_padding(len(key_str))
            padded_key_str = key_str + ("=" * padding)
            key_bytes = base64.urlsafe_b64decode(padded_key_str)

            if EncryptionConfigLoader.validate_fernet_key_length(key_bytes):
                return True, base64.urlsafe_b64encode(key_bytes)
            else:
                return False, b""
        except Exception:
            return False, b""

    @staticmethod
    def create_fernet_key_from_string(key_str: str) -> bytes:
        """
        Convert any string to a valid Fernet key with proper error handling

        Args:
            key_str: Input key string (may be base64 encoded or raw)

        Returns:
            bytes: Base64-encoded 32-byte key suitable for Fernet
        """
        # First, try to decode as existing base64 key
        success, base64_key = EncryptionConfigLoader.try_decode_as_base64_key(key_str)
        if success:
            return base64_key

        # If not valid base64, treat as raw string and normalize
        return EncryptionConfigLoader.normalize_string_to_fernet_key(key_str)
