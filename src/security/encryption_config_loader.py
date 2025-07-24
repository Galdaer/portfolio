"""Centralized encryption configuration management for healthcare AI system"""
import os
import base64
import secrets
from src.security.environment_detector import EnvironmentDetector

class EncryptionConfigLoader:
    """Centralized encryption configuration management"""

    @staticmethod
    def get_or_create_master_key(logger, config=None) -> bytes:
        """Get or create master encryption key with proper base64 encoding"""
        master_key_str = os.getenv('MASTER_ENCRYPTION_KEY')

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
            # Ensure proper base64 encoding for Fernet
            try:
                # If it's already base64 encoded, use it directly
                key_bytes = base64.urlsafe_b64decode(master_key_str + '==')  # Add padding if needed
                if len(key_bytes) == 32:
                    return base64.urlsafe_b64encode(key_bytes)
                else:
                    # If not 32 bytes, treat as raw string and encode
                    key_bytes = master_key_str.encode('utf-8')[:32].ljust(32, b'\0')
                    return base64.urlsafe_b64encode(key_bytes)
            except Exception:
                # Treat as raw string
                key_bytes = master_key_str.encode('utf-8')[:32].ljust(32, b'\0')
                return base64.urlsafe_b64encode(key_bytes)
        else:
            # Generate key for development - return base64 encoded
            return EncryptionConfigLoader._get_or_create_development_key(logger, config)

    @staticmethod
    def _get_or_create_development_key(logger, config=None) -> bytes:
        """Generate or load development encryption key with persistence"""

        # Use config path if provided, otherwise default
        if config and isinstance(config, dict) and config.get('dev_key_path'):
            key_file = config['dev_key_path']
        else:
            key_file = os.path.join(
                os.getenv('CFG_ROOT', '/opt/intelluxe/stack'),
                'security', 'dev_master_key'
            )

        try:
            if os.path.exists(key_file):
                with open(key_file, 'rb') as f:
                    stored_key = f.read().strip()
                    # Validate it's proper base64
                    try:
                        decoded = base64.urlsafe_b64decode(stored_key + b'==')
                        if len(decoded) == 32:
                            return stored_key  # Already base64 encoded
                    except Exception:
                        pass

            # Generate new key and store as base64
            key_bytes = secrets.token_bytes(32)
            encoded_key = base64.urlsafe_b64encode(key_bytes)

            # Store for persistence
            os.makedirs(os.path.dirname(key_file), exist_ok=True)
            with open(key_file, 'wb') as f:
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
