"""
Healthcare Data Encryption Manager
Advanced encryption and key management for healthcare data protection
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import secrets
import hashlib
import base64
from dataclasses import dataclass
from enum import Enum

from cryptography.fernet import Fernet, MultiFernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import psycopg2

# Configure logging
logger = logging.getLogger(__name__)

class EncryptionLevel(Enum):
    """Encryption levels for different data types"""
    BASIC = "basic"          # Standard encryption for non-PHI
    HEALTHCARE = "healthcare"  # Enhanced encryption for PHI
    CRITICAL = "critical"    # Maximum encryption for highly sensitive data

class KeyType(Enum):
    """Types of encryption keys"""
    SYMMETRIC = "symmetric"
    ASYMMETRIC = "asymmetric"
    DERIVED = "derived"

@dataclass
class EncryptionKey:
    """Encryption key metadata"""
    key_id: str
    key_type: KeyType
    encryption_level: EncryptionLevel
    created_at: datetime
    expires_at: Optional[datetime]
    algorithm: str
    key_size: int
    is_active: bool

class KeyManager:
    """Manages encryption keys with rotation and versioning"""
    
    def __init__(self, postgres_conn):
        self.postgres_conn = postgres_conn
        self.logger = logging.getLogger(f"{__name__}.KeyManager")
        self._init_key_tables()
        
        # Master key for key encryption (would be stored in HSM in production)
        self.master_key = self._get_or_create_master_key()
    
    def _init_key_tables(self):
        """Initialize key management tables"""
        try:
            with self.postgres_conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS encryption_keys (
                        id SERIAL PRIMARY KEY,
                        key_id VARCHAR(255) UNIQUE NOT NULL,
                        key_type VARCHAR(50) NOT NULL,
                        encryption_level VARCHAR(50) NOT NULL,
                        algorithm VARCHAR(100) NOT NULL,
                        key_size INTEGER NOT NULL,
                        encrypted_key TEXT NOT NULL,
                        salt VARCHAR(255),
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT NOW(),
                        expires_at TIMESTAMP,
                        rotated_from VARCHAR(255),
                        metadata JSONB
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS key_usage_log (
                        id SERIAL PRIMARY KEY,
                        key_id VARCHAR(255) NOT NULL,
                        operation VARCHAR(50) NOT NULL,
                        data_type VARCHAR(100),
                        user_id VARCHAR(255),
                        timestamp TIMESTAMP DEFAULT NOW(),
                        success BOOLEAN DEFAULT TRUE
                    )
                """)
                
                # Create indexes
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_encryption_keys_key_id 
                    ON encryption_keys(key_id)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_encryption_keys_active 
                    ON encryption_keys(is_active)
                """)
                
            self.postgres_conn.commit()
            self.logger.info("Key management tables initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize key tables: {e}")
            raise

    def _load_configuration(self) -> Dict[str, Any]:
        """Load configuration from secure source"""
        # Priority order: config file -> environment -> defaults
        config = {}

        # Try to load from secure config file first
        config_paths = [
            "/etc/intelluxe/config.json",
            "/opt/intelluxe/config/security.json",
            os.path.expanduser("~/.intelluxe/config.json")
        ]

        for config_path in config_paths:
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        file_config = json.load(f)
                        config.update(file_config)
                        self.logger.info(f"Loaded configuration from {config_path}")
                        break
                except Exception as e:
                    self.logger.warning(f"Failed to load config from {config_path}: {e}")

        # Fallback to environment variables
        config.setdefault("ENVIRONMENT", os.getenv("ENVIRONMENT", "development"))
        config.setdefault("MASTER_ENCRYPTION_KEY", os.getenv("MASTER_ENCRYPTION_KEY"))

        return config

    def _get_or_create_master_key(self) -> bytes:
        """Load or generate master encryption key"""
        # Load configuration from secure source
        config = self._load_configuration()
        master_key = config.get("MASTER_ENCRYPTION_KEY")

        if master_key:
            return base64.urlsafe_b64decode(master_key.encode())

        # Check configuration to determine if key generation is allowed
        if config.get("ENVIRONMENT", "development").lower() == "production":
            self.logger.error("MASTER_ENCRYPTION_KEY is not set in production environment")
            raise RuntimeError("MASTER_ENCRYPTION_KEY must be set in production")

        # Generate new master key (for development only)
        master_key = Fernet.generate_key()
        self.logger.warning("Generated new master key - store securely for production")
        return master_key
    
    def generate_key(self, encryption_level: EncryptionLevel, 
                    key_type: KeyType = KeyType.SYMMETRIC) -> EncryptionKey:
        """Generate new encryption key"""
        key_id = f"key_{secrets.token_hex(16)}"
        
        if key_type == KeyType.SYMMETRIC:
            if encryption_level == EncryptionLevel.CRITICAL:
                # Use AES-256 for critical data
                raw_key = secrets.token_bytes(32)  # 256 bits
                algorithm = "AES-256-GCM"
                key_size = 256
            else:
                # Use Fernet (AES-128) for standard encryption
                raw_key = Fernet.generate_key()
                algorithm = "Fernet"
                key_size = 128
        
        elif key_type == KeyType.ASYMMETRIC:
            # Generate RSA key pair
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048 if encryption_level != EncryptionLevel.CRITICAL else 4096,
                backend=default_backend()
            )
            raw_key = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            algorithm = "RSA"
            key_size = 2048 if encryption_level != EncryptionLevel.CRITICAL else 4096
        
        # Encrypt the key with master key
        master_fernet = Fernet(self.master_key)
        encrypted_key = master_fernet.encrypt(raw_key)
        
        # Store key metadata
        key_metadata = EncryptionKey(
            key_id=key_id,
            key_type=key_type,
            encryption_level=encryption_level,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=365),  # 1 year expiration
            algorithm=algorithm,
            key_size=key_size,
            is_active=True
        )
        
        try:
            with self.postgres_conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO encryption_keys 
                    (key_id, key_type, encryption_level, algorithm, key_size, 
                     encrypted_key, is_active, expires_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    key_id, key_type.value, encryption_level.value,
                    algorithm, key_size, base64.b64encode(encrypted_key).decode(),
                    True, key_metadata.expires_at
                ))
            self.postgres_conn.commit()
            
            self.logger.info(f"Generated new {key_type.value} key: {key_id}")
            return key_metadata
            
        except Exception as e:
            self.logger.error(f"Failed to store encryption key: {e}")
            raise
    
    def get_key(self, key_id: str) -> Optional[bytes]:
        """Retrieve and decrypt encryption key"""
        try:
            with self.postgres_conn.cursor() as cursor:
                cursor.execute("""
                    SELECT encrypted_key, is_active, expires_at
                    FROM encryption_keys
                    WHERE key_id = %s
                """, (key_id,))
                
                result = cursor.fetchone()
                if not result:
                    return None
                
                encrypted_key_b64, is_active, expires_at = result
                
                # Check if key is active and not expired
                if not is_active:
                    self.logger.warning(f"Attempted to use inactive key: {key_id}")
                    return None
                
                if expires_at and datetime.now() > expires_at:
                    self.logger.warning(f"Attempted to use expired key: {key_id}")
                    return None
                
                # Decrypt key with master key
                master_fernet = Fernet(self.master_key)
                encrypted_key = base64.b64decode(encrypted_key_b64.encode())
                raw_key = master_fernet.decrypt(encrypted_key)
                
                # Log key usage
                self._log_key_usage(key_id, "retrieve")
                
                return raw_key
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve key {key_id}: {e}")
            return None
    
    def rotate_key(self, old_key_id: str) -> EncryptionKey:
        """Rotate encryption key"""
        # Get old key metadata
        try:
            with self.postgres_conn.cursor() as cursor:
                cursor.execute("""
                    SELECT key_type, encryption_level, algorithm
                    FROM encryption_keys
                    WHERE key_id = %s
                """, (old_key_id,))
                
                result = cursor.fetchone()
                if not result:
                    raise ValueError(f"Key not found: {old_key_id}")
                
                key_type_str, encryption_level_str, algorithm = result
                key_type = KeyType(key_type_str)
                encryption_level = EncryptionLevel(encryption_level_str)
                
                # Generate new key
                new_key = self.generate_key(encryption_level, key_type)
                
                # Deactivate old key
                cursor.execute("""
                    UPDATE encryption_keys 
                    SET is_active = FALSE, rotated_from = %s
                    WHERE key_id = %s
                """, (new_key.key_id, old_key_id))
                
            self.postgres_conn.commit()
            
            self.logger.info(f"Rotated key {old_key_id} to {new_key.key_id}")
            return new_key
            
        except Exception as e:
            self.logger.error(f"Failed to rotate key {old_key_id}: {e}")
            raise
    
    def _log_key_usage(self, key_id: str, operation: str, 
                      data_type: Optional[str] = None, user_id: Optional[str] = None):
        """Log key usage for audit"""
        try:
            with self.postgres_conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO key_usage_log 
                    (key_id, operation, data_type, user_id)
                    VALUES (%s, %s, %s, %s)
                """, (key_id, operation, data_type, user_id))
            self.postgres_conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to log key usage: {e}")

class HealthcareEncryptionManager:
    """Main encryption manager for healthcare data"""
    
    def __init__(self, postgres_conn):
        self.postgres_conn = postgres_conn
        self.logger = logging.getLogger(f"{__name__}.HealthcareEncryptionManager")
        self.key_manager = KeyManager(postgres_conn)
        
        # Initialize default keys for different encryption levels
        self._init_default_keys()
    
    def _init_default_keys(self):
        """Initialize default encryption keys"""
        try:
            # Check if default keys exist
            with self.postgres_conn.cursor() as cursor:
                cursor.execute("""
                    SELECT key_id, encryption_level 
                    FROM encryption_keys 
                    WHERE key_id LIKE 'default_%' AND is_active = TRUE
                """)
                existing_keys = {row[1]: row[0] for row in cursor.fetchall()}
            
            # Generate missing default keys
            for level in EncryptionLevel:
                if level.value not in existing_keys:
                    key = self.key_manager.generate_key(level)
                    # Update key_id to be default
                    with self.postgres_conn.cursor() as cursor:
                        cursor.execute("""
                            UPDATE encryption_keys 
                            SET key_id = %s 
                            WHERE key_id = %s
                        """, (f"default_{level.value}", key.key_id))
                    self.postgres_conn.commit()
                    
                    self.logger.info(f"Created default key for {level.value}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize default keys: {e}")
            raise
    
    def encrypt_phi_data(self, data: Union[str, Dict[str, Any]], 
                        user_id: Optional[str] = None) -> Dict[str, Any]:
        """Encrypt PHI data with healthcare-level encryption"""
        return self._encrypt_data(data, EncryptionLevel.HEALTHCARE, user_id)
    
    def encrypt_critical_data(self, data: Union[str, Dict[str, Any]], 
                            user_id: Optional[str] = None) -> Dict[str, Any]:
        """Encrypt critical data with maximum security"""
        return self._encrypt_data(data, EncryptionLevel.CRITICAL, user_id)
    
    def encrypt_basic_data(self, data: Union[str, Dict[str, Any]], 
                          user_id: Optional[str] = None) -> Dict[str, Any]:
        """Encrypt non-PHI data with basic encryption"""
        return self._encrypt_data(data, EncryptionLevel.BASIC, user_id)
    
    def _encrypt_data(self, data: Union[str, Dict[str, Any]], 
                     level: EncryptionLevel, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Internal method to encrypt data"""
        try:
            # Convert data to string if needed
            if isinstance(data, dict):
                data_str = json.dumps(data, sort_keys=True)
            else:
                data_str = str(data)
            
            # Get encryption key
            key_id = f"default_{level.value}"
            raw_key = self.key_manager.get_key(key_id)
            
            if not raw_key:
                raise ValueError(f"Encryption key not found: {key_id}")
            
            # Encrypt based on level
            if level == EncryptionLevel.CRITICAL:
                encrypted_data = self._encrypt_aes_gcm(data_str.encode(), raw_key)
            else:
                # Use Fernet for basic and healthcare levels
                fernet = Fernet(raw_key)
                encrypted_data = fernet.encrypt(data_str.encode())
            
            # Log encryption
            self.key_manager._log_key_usage(key_id, "encrypt", "phi_data", user_id)
            
            return {
                "encrypted_data": base64.b64encode(encrypted_data).decode(),
                "key_id": key_id,
                "encryption_level": level.value,
                "algorithm": "AES-256-GCM" if level == EncryptionLevel.CRITICAL else "Fernet",
                "encrypted_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt_data(self, encrypted_package: Dict[str, Any], 
                    user_id: Optional[str] = None) -> Union[str, Dict[str, Any]]:
        """Decrypt data package"""
        try:
            key_id = encrypted_package["key_id"]
            encrypted_data_b64 = encrypted_package["encrypted_data"]
            encryption_level = encrypted_package["encryption_level"]
            algorithm = encrypted_package.get("algorithm", "Fernet")
            
            # Get decryption key
            raw_key = self.key_manager.get_key(key_id)
            if not raw_key:
                raise ValueError(f"Decryption key not found: {key_id}")
            
            # Decrypt data
            encrypted_data = base64.b64decode(encrypted_data_b64.encode())
            
            if algorithm == "AES-256-GCM":
                decrypted_data = self._decrypt_aes_gcm(encrypted_data, raw_key)
            else:
                # Use Fernet
                fernet = Fernet(raw_key)
                decrypted_data = fernet.decrypt(encrypted_data)
            
            # Log decryption
            self.key_manager._log_key_usage(key_id, "decrypt", "phi_data", user_id)
            
            # Try to parse as JSON, otherwise return as string
            try:
                return json.loads(decrypted_data.decode())
            except json.JSONDecodeError:
                return decrypted_data.decode()
            
        except Exception as e:
            self.logger.error(f"Decryption failed: {e}")
            raise
    
    def _encrypt_aes_gcm(self, data: bytes, key: bytes) -> bytes:
        """Encrypt using AES-256-GCM"""
        # Generate random IV
        iv = secrets.token_bytes(12)  # 96-bit IV for GCM
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(key[:32]),  # Use first 32 bytes for AES-256
            modes.GCM(iv),
            backend=default_backend()
        )
        
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(data) + encryptor.finalize()
        
        # Return IV + tag + ciphertext
        return iv + encryptor.tag + ciphertext
    
    def _decrypt_aes_gcm(self, encrypted_data: bytes, key: bytes) -> bytes:
        """Decrypt using AES-256-GCM"""
        # Extract IV, tag, and ciphertext
        iv = encrypted_data[:12]
        tag = encrypted_data[12:28]
        ciphertext = encrypted_data[28:]
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(key[:32]),  # Use first 32 bytes for AES-256
            modes.GCM(iv, tag),
            backend=default_backend()
        )
        
        decryptor = cipher.decryptor()
        return decryptor.update(ciphertext) + decryptor.finalize()
    
    def get_encryption_status(self) -> Dict[str, Any]:
        """Get encryption system status"""
        try:
            with self.postgres_conn.cursor() as cursor:
                # Count active keys by level
                cursor.execute("""
                    SELECT encryption_level, COUNT(*) 
                    FROM encryption_keys 
                    WHERE is_active = TRUE 
                    GROUP BY encryption_level
                """)
                key_counts = dict(cursor.fetchall())
                
                # Get key usage stats
                cursor.execute("""
                    SELECT operation, COUNT(*) 
                    FROM key_usage_log 
                    WHERE timestamp > NOW() - INTERVAL '24 hours'
                    GROUP BY operation
                """)
                usage_stats = dict(cursor.fetchall())
                
                return {
                    "active_keys": key_counts,
                    "daily_usage": usage_stats,
                    "encryption_levels": [level.value for level in EncryptionLevel],
                    "status": "operational"
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get encryption status: {e}")
            return {"status": "error", "error": str(e)}

# Example usage
if __name__ == "__main__":
    # This would be used in testing
    pass
