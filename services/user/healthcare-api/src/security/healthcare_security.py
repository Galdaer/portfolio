"""
Healthcare Security Middleware
Comprehensive security framework for healthcare AI systems with HIPAA compliance
"""

import base64
import contextlib
import json
import logging
import os
import secrets
from collections.abc import Callable
from datetime import datetime, timedelta
from functools import wraps
from typing import TYPE_CHECKING, Any

# Optional dependencies - healthcare-compliant import pattern
if TYPE_CHECKING:
    import jwt
    import psycopg2
    import redis
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from fastapi import HTTPException, Request
else:
    jwt: Any | None = None
    psycopg2: Any | None = None
    redis: Any | None = None
    Fernet: Any | None = None
    hashes: Any | None = None
    PBKDF2HMAC: Any | None = None
    HTTPException: Any | None = None
    Request: Any | None = None

    with contextlib.suppress(ImportError):
        import jwt

    with contextlib.suppress(ImportError):
        import psycopg2

    with contextlib.suppress(ImportError):
        import redis

    try:
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    except ImportError:
        pass

    with contextlib.suppress(ImportError):
        from fastapi import HTTPException, Request

from src.healthcare_mcp.audit_logger import HealthcareAuditLogger
from src.healthcare_mcp.phi_detection import PHIDetector

# Configure logging
logger = logging.getLogger(__name__)


class SecurityConfig:
    """Security configuration for healthcare systems"""

    def __init__(self) -> None:
        # Encryption settings
        self.encryption_key = os.getenv("MCP_ENCRYPTION_KEY")
        self.master_encryption_key = os.getenv("MASTER_ENCRYPTION_KEY")
        self.jwt_secret = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
        self.jwt_algorithm = "HS256"
        self.jwt_expiration_hours = 8

        # Audit logging
        self.audit_log_level = os.getenv("AUDIT_LOGGING_LEVEL", "INFO")

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
    """Handles encryption/decryption for healthcare data"""

    def __init__(self, encryption_key: bytes | None = None):
        self.fernet: Any | None = None

        # Runtime check for cryptography availability
        try:
            if Fernet is not None:
                if encryption_key:
                    self.fernet = Fernet(
                        base64.urlsafe_b64encode(encryption_key[:32].ljust(32, b"\0")),
                    )
                else:
                    # Generate a key for development
                    key = Fernet.generate_key()
                    self.fernet = Fernet(key)
            else:
                raise ImportError("Cryptography library not available")
        except Exception:
            logger.warning("Cryptography library not available - encryption disabled")

    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        if self.fernet is None:
            logger.warning(
                "Encryption not available - returning data unencrypted (DEVELOPMENT ONLY)",
            )
            return data
        encrypted_bytes: bytes = self.fernet.encrypt(data.encode())
        # Ensure we return a string (Fernet.encrypt returns bytes)
        return encrypted_bytes.decode("utf-8")

    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        if self.fernet is None:
            logger.warning("Decryption not available - returning data as-is (DEVELOPMENT ONLY)")
            return encrypted_data
        decrypted_bytes: bytes = self.fernet.decrypt(encrypted_data.encode())
        # Ensure we return a string (Fernet.decrypt returns bytes)
        return decrypted_bytes.decode("utf-8")

    def hash_password(self, password: str, salt: str | None = None) -> tuple[str, str]:
        """
        Hash password with salt for secure storage

        Returns:
            tuple[str, str]: (hashed_password, salt) - Python 3.9+ syntax
        """
        # Runtime check for cryptography availability
        try:
            if PBKDF2HMAC is not None and hashes is not None:
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
            raise ImportError("Cryptography library not available")
        except Exception:
            logger.warning(
                "Cryptography library not available - using basic hash (DEVELOPMENT ONLY)",
            )
            if salt is None:
                salt = secrets.token_hex(16)
            # Use simple hash for development
            import hashlib

            hashed = hashlib.sha256((password + salt).encode()).hexdigest()
            return hashed, salt

    def verify_password(self, password: str, hashed: str, salt: str) -> bool:
        """Verify password against hash"""
        try:
            new_hash, _ = self.hash_password(password, salt)
            return secrets.compare_digest(hashed, new_hash)
        except Exception:
            return False


class SessionManager:
    """Manages user sessions with Redis"""

    def __init__(self, config: SecurityConfig, redis_conn: Any):
        self.config = config
        self.redis_conn = redis_conn
        self.logger = logging.getLogger(f"{__name__}.SessionManager")

    def create_session(self, user_id: str, user_data: dict[str, Any]) -> str:
        """Create secure user session"""
        session_id = secrets.token_urlsafe(32)

        session_data = {
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "user_data": user_data,
            "ip_address": user_data.get("ip_address"),
            "user_agent": user_data.get("user_agent"),
        }

        # Store session in Redis with expiration - convert timedelta to seconds
        session_key = f"session:{session_id}"
        timeout_seconds = int(
            timedelta(minutes=self.config.session_timeout_minutes).total_seconds(),
        )
        self.redis_conn.setex(session_key, timeout_seconds, json.dumps(session_data))

        self.logger.info(f"Session created for user {user_id}")
        return session_id

    def validate_session(self, session_id: str) -> dict[str, Any] | None:
        """Validate and refresh session"""
        session_key = f"session:{session_id}"

        try:
            session_data_raw = self.redis_conn.get(session_key)

            if not session_data_raw:
                return None

            # Handle bytes response from Redis - be more explicit
            if isinstance(session_data_raw, bytes):
                session_data_str = session_data_raw.decode("utf-8")
            elif isinstance(session_data_raw, str):
                session_data_str = session_data_raw
            else:
                # Fallback for other types
                session_data_str = str(session_data_raw)

            session = json.loads(session_data_str)
            if not isinstance(session, dict):
                self.logger.error("Session data is not a valid dictionary")
                return None

            # Update last activity
            session["last_activity"] = datetime.now().isoformat()

            # Refresh session expiration
            self.redis_conn.setex(
                session_key,
                int(timedelta(minutes=self.config.session_timeout_minutes).total_seconds()),
                json.dumps(session),
            )

            return session

        except (json.JSONDecodeError, ValueError, TypeError, AttributeError) as e:
            self.logger.exception(f"Session validation failed: {e}")
            return None

    def invalidate_session(self, session_id: str) -> None:
        """Invalidate user session"""
        session_key = f"session:{session_id}"
        self.redis_conn.delete(session_key)
        self.logger.info(f"Session {session_id} invalidated")


class RateLimiter:
    """Rate limiting for API endpoints"""

    def __init__(self, config: SecurityConfig, redis_conn: Any):
        self.config = config
        self.redis_conn: Any = redis_conn  # Type annotation for redis connection
        self.logger = logging.getLogger(f"{__name__}.RateLimiter")

    def check_rate_limit(self, identifier: str, endpoint: str) -> bool:
        """Check if request is within rate limits"""
        key = f"rate_limit:{identifier}:{endpoint}"

        try:
            # Get current count - explicitly handle the response type
            current_count_raw = self.redis_conn.get(key)

            if current_count_raw is None:
                # First request in window
                timeout_seconds = int(
                    timedelta(minutes=self.config.rate_limit_window_minutes).total_seconds(),
                )
                self.redis_conn.setex(key, timeout_seconds, "1")
                return True

            # Convert Redis response to integer
            if isinstance(current_count_raw, bytes):
                current_count = int(current_count_raw.decode("utf-8"))
            elif isinstance(current_count_raw, str):
                current_count = int(current_count_raw)
            else:
                # This shouldn't happen with sync Redis, but handle it
                current_count = int(str(current_count_raw))

            if current_count >= self.config.rate_limit_requests:
                self.logger.warning(f"Rate limit exceeded for {identifier} on {endpoint}")
                return False

            # Increment counter
            self.redis_conn.incr(key)
            return True

        except (ValueError, TypeError, AttributeError) as e:
            self.logger.exception(f"Rate limit check failed: {e}")
            return True  # Fail open for availability


class HealthcareSecurityMiddleware:
    """Main security middleware for healthcare applications"""

    def __init__(
        self,
        config: SecurityConfig,
        postgres_conn: Any = None,
        redis_conn: Any = None,
    ) -> None:
        self.config = config
        self.postgres_conn = postgres_conn
        self.redis_conn = redis_conn

        # Check dependencies availability
        self.postgres_available = psycopg2 is not None and postgres_conn is not None
        self.redis_available = redis is not None and redis_conn is not None

        if not self.postgres_available:
            logger.warning("PostgreSQL not available - some security features disabled")
        if not self.redis_available:
            logger.warning("Redis not available - session management disabled")

        # Convert string encryption key to bytes if needed
        encryption_key = None
        if config.master_encryption_key:
            encryption_key = config.master_encryption_key.encode("utf-8")

        self.encryption_manager = EncryptionManager(encryption_key)
        self.phi_detector = PHIDetector()
        self.audit_logger = HealthcareAuditLogger(config, config.audit_log_level)
        self._current_request_ip: str | None = None
        self.logger = logging.getLogger(f"{__name__}.HealthcareSecurityMiddleware")

        # Initialize session manager and rate limiter
        self.session_manager = SessionManager(config, redis_conn)
        self.rate_limiter = RateLimiter(config, redis_conn)

        # Initialize security tables
        self._init_security_tables()

    def _init_security_tables(self) -> None:
        """Initialize security-related database tables"""
        try:
            with self.postgres_conn.cursor() as cursor:
                # User authentication table
                cursor.execute(
                    """
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
                """,
                )

                # Access control table
                cursor.execute(
                    """
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
                """,
                )

                # Security events table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS security_events (
                        id SERIAL PRIMARY KEY,
                        event_type VARCHAR(100),
                        severity VARCHAR(20),
                        user_id VARCHAR(255),
                        ip_address INET,
                        details JSONB,
                        timestamp TIMESTAMP DEFAULT NOW()
                    )
                """,
                )

            self.postgres_conn.commit()
            self.logger.info("Security tables initialized")

        except Exception as e:
            self.logger.exception(f"Failed to initialize security tables: {e}")
            raise

    async def authenticate_request(self, request: Request) -> dict[str, Any] | None:
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
                algorithms=[self.config.jwt_algorithm],
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
                    "token_payload": payload,
                }

            return {"user_id": user_id, "token_payload": payload}

        except jwt.ExpiredSignatureError:
            self.logger.warning("Expired JWT token")
            return None
        except jwt.InvalidTokenError:
            self.logger.warning("Invalid JWT token")
            return None

    async def authorize_access(self, user_data: dict[str, Any], resource: str, action: str) -> bool:
        """Authorize user access to resource"""
        user_id = user_data.get("user_id")
        user_role = user_data.get("token_payload", {}).get("role", "user")

        # Basic role-based access control
        access_rules = {
            "admin": ["*"],  # Admin can access everything
            "healthcare_provider": ["patient_data", "medical_records", "research"],
            "researcher": ["research", "anonymized_data"],
            "user": ["basic_info"],
        }

        allowed_resources = access_rules.get(user_role, [])

        # Check if user has access
        has_access = "*" in allowed_resources or resource in allowed_resources

        # Log access attempt - ensure user_id is a string
        if user_id:
            await self._log_access_attempt(str(user_id), resource, action, has_access)

        return has_access

    async def _log_access_attempt(
        self,
        user_id: str,
        resource: str,
        action: str,
        granted: bool,
    ) -> None:
        """Log access attempt for audit"""
        try:
            with self.postgres_conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO access_control_log
                    (user_id, resource, action, granted, timestamp)
                    VALUES (%s, %s, %s, %s, NOW())
                """,
                    (user_id, resource, action, granted),
                )
            self.postgres_conn.commit()
        except Exception as e:
            self.logger.exception(f"Failed to log access attempt: {e}")

    async def log_security_event(
        self,
        event_type: str,
        severity: str,
        user_id: str | None,
        details: dict[str, Any],
    ) -> None:
        """Log security event"""
        try:
            with self.postgres_conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO security_events
                    (event_type, severity, user_id, details, timestamp)
                    VALUES (%s, %s, %s, %s, NOW())
                """,
                    (event_type, severity, user_id, json.dumps(details)),
                )
            self.postgres_conn.commit()
        except Exception as e:
            self.logger.exception(f"Failed to log security event: {e}")


def require_authentication(security_middleware: HealthcareSecurityMiddleware) -> Callable:
    """Decorator to require authentication"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request: Request, *args: Any, **kwargs: Any) -> Any:
            user_data = await security_middleware.authenticate_request(request)
            if not user_data:
                raise HTTPException(status_code=401, detail="Authentication required")

            # Add user data to request state
            request.state.user_data = user_data
            return await func(request, *args, **kwargs)

        return wrapper

    return decorator


def require_authorization(resource: str, action: str) -> Callable:
    """Decorator to require authorization"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request: Request, *args: Any, **kwargs: Any) -> Any:
            user_data = getattr(request.state, "user_data", None)
            if not user_data:
                raise HTTPException(status_code=401, detail="Authentication required")

            security_middleware = getattr(request.app.state, "security_middleware", None)
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
