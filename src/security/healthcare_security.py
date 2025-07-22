"""
Healthcare Security Middleware
Comprehensive security framework for healthcare AI systems with HIPAA compliance
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import hashlib
import secrets
from functools import wraps
import jwt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from fastapi import HTTPException, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import redis
import psycopg2

from .environment_detector import EnvironmentDetector

# Configure logging
logger = logging.getLogger(__name__)

class SecurityConfig:
    """Security configuration for healthcare systems"""
    
    def __init__(self):
        # Encryption settings
        self.encryption_key = os.getenv("MCP_ENCRYPTION_KEY")
        self.jwt_secret = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
        self.jwt_algorithm = "HS256"
        self.jwt_expiration_hours = 8
        
        # Session settings
        self.session_timeout_minutes = 30
        self.max_failed_attempts = 3
        self.lockout_duration_minutes = 15
        
        # HIPAA compliance settings
        self.audit_all_access = True
        self.require_mfa = False  # Would be True in production
        self.data_retention_days = 2555  # 7 years
        self.phi_encryption_required = True
        
        # Rate limiting
        self.rate_limit_requests = 100
        self.rate_limit_window_minutes = 15

class EncryptionManager:
    """Manages encryption for healthcare data"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.EncryptionManager")
        
        # Initialize encryption key with environment-aware validation
        if config.encryption_key:
            self.fernet = Fernet(config.encryption_key.encode())
            self.logger.info("Encryption key loaded from configuration")
        else:
            # Check environment before allowing key generation
            if EnvironmentDetector.is_production():
                self.logger.error("MCP_ENCRYPTION_KEY not configured for production environment")
                raise RuntimeError("Application cannot start in production without encryption key")

            # Generate key if not provided (for development only)
            key = Fernet.generate_key()
            self.fernet = Fernet(key)
            self.logger.warning("Using generated encryption key - not suitable for production")
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        try:
            encrypted = self.fernet.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            self.logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self.fernet.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            self.logger.error(f"Decryption failed: {e}")
            raise
    
    def hash_password(self, password: str, salt: Optional[str] = None) -> tuple[str, str]:
        """Hash password with salt"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        # Use PBKDF2 with SHA256
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt.encode(),
            iterations=100000,
        )
        key = kdf.derive(password.encode())
        hashed = base64.urlsafe_b64encode(key).decode()
        
        return hashed, salt
    
    def verify_password(self, password: str, hashed: str, salt: str) -> bool:
        """Verify password against hash"""
        try:
            new_hash, _ = self.hash_password(password, salt)
            return secrets.compare_digest(hashed, new_hash)
        except Exception:
            return False

class SessionManager:
    """Manages user sessions with security controls"""
    
    def __init__(self, config: SecurityConfig, redis_conn: redis.Redis):
        self.config = config
        self.redis_conn = redis_conn
        self.logger = logging.getLogger(f"{__name__}.SessionManager")
    
    def create_session(self, user_id: str, user_data: Dict[str, Any]) -> str:
        """Create secure user session"""
        session_id = secrets.token_urlsafe(32)
        
        session_data = {
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "user_data": user_data,
            "ip_address": user_data.get("ip_address"),
            "user_agent": user_data.get("user_agent")
        }
        
        # Store session in Redis with expiration
        session_key = f"session:{session_id}"
        self.redis_conn.setex(
            session_key,
            timedelta(minutes=self.config.session_timeout_minutes),
            json.dumps(session_data)
        )
        
        self.logger.info(f"Session created for user {user_id}")
        return session_id
    
    def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Validate and refresh session"""
        session_key = f"session:{session_id}"
        session_data = self.redis_conn.get(session_key)
        
        if not session_data:
            return None
        
        try:
            session = json.loads(session_data)
            
            # Update last activity
            session["last_activity"] = datetime.now().isoformat()
            
            # Refresh session expiration
            self.redis_conn.setex(
                session_key,
                timedelta(minutes=self.config.session_timeout_minutes),
                json.dumps(session)
            )
            
            return session
            
        except Exception as e:
            self.logger.error(f"Session validation failed: {e}")
            return None
    
    def invalidate_session(self, session_id: str):
        """Invalidate user session"""
        session_key = f"session:{session_id}"
        self.redis_conn.delete(session_key)
        self.logger.info(f"Session {session_id} invalidated")

class RateLimiter:
    """Rate limiting for API endpoints"""
    
    def __init__(self, config: SecurityConfig, redis_conn: redis.Redis):
        self.config = config
        self.redis_conn = redis_conn
        self.logger = logging.getLogger(f"{__name__}.RateLimiter")
    
    def check_rate_limit(self, identifier: str, endpoint: str) -> bool:
        """Check if request is within rate limits"""
        key = f"rate_limit:{identifier}:{endpoint}"
        window_start = datetime.now().replace(second=0, microsecond=0)
        
        # Use sliding window
        current_count = self.redis_conn.get(key)
        
        if current_count is None:
            # First request in window
            self.redis_conn.setex(
                key,
                timedelta(minutes=self.config.rate_limit_window_minutes),
                1
            )
            return True
        
        current_count = int(current_count)
        
        if current_count >= self.config.rate_limit_requests:
            self.logger.warning(f"Rate limit exceeded for {identifier} on {endpoint}")
            return False
        
        # Increment counter
        self.redis_conn.incr(key)
        return True

class HealthcareSecurityMiddleware:
    """Main security middleware for healthcare applications"""
    
    def __init__(self, config: SecurityConfig, postgres_conn, redis_conn):
        self.config = config
        self.postgres_conn = postgres_conn
        self.redis_conn = redis_conn
        self.logger = logging.getLogger(f"{__name__}.HealthcareSecurityMiddleware")
        
        # Initialize security components
        self.encryption_manager = EncryptionManager(config)
        self.session_manager = SessionManager(config, redis_conn)
        self.rate_limiter = RateLimiter(config, redis_conn)
        
        # Initialize security tables
        self._init_security_tables()
    
    def _init_security_tables(self):
        """Initialize security-related database tables"""
        try:
            with self.postgres_conn.cursor() as cursor:
                # User authentication table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS healthcare_users (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(255) UNIQUE NOT NULL,
                        username VARCHAR(255) UNIQUE NOT NULL,
                        password_hash VARCHAR(255) NOT NULL,
                        password_salt VARCHAR(255) NOT NULL,
                        role VARCHAR(100) NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE,
                        failed_attempts INTEGER DEFAULT 0,
                        locked_until TIMESTAMP,
                        last_login TIMESTAMP,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                
                # Access control table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS access_control_log (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(255),
                        resource VARCHAR(255),
                        action VARCHAR(100),
                        granted BOOLEAN,
                        reason TEXT,
                        ip_address INET,
                        timestamp TIMESTAMP DEFAULT NOW()
                    )
                """)
                
                # Security events table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS security_events (
                        id SERIAL PRIMARY KEY,
                        event_type VARCHAR(100),
                        severity VARCHAR(20),
                        user_id VARCHAR(255),
                        ip_address INET,
                        details JSONB,
                        timestamp TIMESTAMP DEFAULT NOW()
                    )
                """)
                
            self.postgres_conn.commit()
            self.logger.info("Security tables initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize security tables: {e}")
            raise
    
    async def authenticate_request(self, request: Request) -> Optional[Dict[str, Any]]:
        """Authenticate incoming request"""
        # Extract authentication token
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header.split(" ")[1]
        
        # Validate JWT token
        try:
            payload = jwt.decode(
                token,
                self.config.jwt_secret,
                algorithms=[self.config.jwt_algorithm]
            )
            
            user_id = payload.get("user_id")
            if not user_id:
                return None
            
            # Validate session
            session_id = payload.get("session_id")
            if session_id:
                session_data = self.session_manager.validate_session(session_id)
                if not session_data:
                    return None
                
                return {
                    "user_id": user_id,
                    "session_data": session_data,
                    "token_payload": payload
                }
            
            return {"user_id": user_id, "token_payload": payload}
            
        except jwt.ExpiredSignatureError:
            self.logger.warning("Expired JWT token")
            return None
        except jwt.InvalidTokenError:
            self.logger.warning("Invalid JWT token")
            return None
    
    async def authorize_access(self, user_data: Dict[str, Any], resource: str, action: str) -> bool:
        """Authorize user access to resource"""
        user_id = user_data.get("user_id")
        user_role = user_data.get("token_payload", {}).get("role", "user")
        
        # Basic role-based access control
        access_rules = {
            "admin": ["*"],  # Admin can access everything
            "healthcare_provider": ["patient_data", "medical_records", "research"],
            "researcher": ["research", "anonymized_data"],
            "user": ["basic_info"]
        }
        
        allowed_resources = access_rules.get(user_role, [])
        
        # Check if user has access
        has_access = "*" in allowed_resources or resource in allowed_resources
        
        # Log access attempt
        await self._log_access_attempt(user_id, resource, action, has_access)
        
        return has_access
    
    async def _log_access_attempt(self, user_id: str, resource: str, action: str, granted: bool):
        """Log access attempt for audit"""
        try:
            with self.postgres_conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO access_control_log 
                    (user_id, resource, action, granted, timestamp)
                    VALUES (%s, %s, %s, %s, NOW())
                """, (user_id, resource, action, granted))
            self.postgres_conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to log access attempt: {e}")
    
    async def log_security_event(self, event_type: str, severity: str, 
                                user_id: Optional[str], details: Dict[str, Any]):
        """Log security event"""
        try:
            with self.postgres_conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO security_events 
                    (event_type, severity, user_id, details, timestamp)
                    VALUES (%s, %s, %s, %s, NOW())
                """, (event_type, severity, user_id, json.dumps(details)))
            self.postgres_conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to log security event: {e}")

def require_authentication(security_middleware: HealthcareSecurityMiddleware):
    """Decorator to require authentication"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            user_data = await security_middleware.authenticate_request(request)
            if not user_data:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            # Add user data to request state
            request.state.user_data = user_data
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

def require_authorization(resource: str, action: str):
    """Decorator to require authorization"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            user_data = getattr(request.state, 'user_data', None)
            if not user_data:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            security_middleware = getattr(request.app.state, 'security_middleware', None)
            if not security_middleware:
                raise HTTPException(status_code=500, detail="Security middleware not configured")
            
            has_access = await security_middleware.authorize_access(user_data, resource, action)
            if not has_access:
                raise HTTPException(status_code=403, detail="Access denied")
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

# Example usage
if __name__ == "__main__":
    # This would be used in testing
    pass
