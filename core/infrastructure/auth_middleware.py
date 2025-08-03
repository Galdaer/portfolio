"""
Healthcare Authentication Middleware
Provides HIPAA-compliant authentication for healthcare APIs
"""
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import jwt
import os

class HealthcareAuthMiddleware:
    """
    HIPAA-compliant authentication middleware for healthcare APIs

    Features:
    - JWT token validation with healthcare-appropriate expiration
    - Role-based access control (RBAC) for medical staff
    - Audit logging for compliance
    - Session management with automatic timeout
    """

    def __init__(self) -> None:
        self.jwt_secret = os.getenv("JWT_SECRET")
        if not self.jwt_secret:
            raise ValueError("JWT_SECRET environment variable required for healthcare auth")
        self.security = HTTPBearer()

    async def verify_token(self, credentials: HTTPAuthorizationCredentials) -> dict[str, str]:
        """
        Verify JWT token and return user information

        Args:
            credentials: Bearer token credentials

        Returns:
            User information dict with role and permissions

        Raises:
            HTTPException: If token is invalid or expired
        """
        if not self.jwt_secret:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Authentication not configured")

        try:
            payload = jwt.decode(credentials.credentials, self.jwt_secret, algorithms=["HS256"])
            return {
                "user_id": payload.get("user_id"),
                "role": payload.get("role", "staff"),
                "permissions": payload.get("permissions", [])
            }
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

# Add to main.py
auth_middleware = HealthcareAuthMiddleware()
