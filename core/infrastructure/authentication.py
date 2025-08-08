"""
Healthcare Authentication & Authorization Infrastructure

HIPAA-compliant authentication with role-based access control and audit logging.
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# Healthcare Role Definitions
class HealthcareRole(str, Enum):
    """HIPAA-compliant healthcare roles with specific access permissions"""

    ADMIN = "admin"  # Full system access
    DOCTOR = "doctor"  # Full patient data access
    NURSE = "nurse"  # Limited patient data access
    RECEPTIONIST = "receptionist"  # Scheduling and basic demographics
    BILLING = "billing"  # Billing and insurance data
    RESEARCH = "research"  # De-identified data only


# JWT Token Models
class TokenData(BaseModel):
    """Healthcare JWT token payload"""

    user_id: str = Field(..., description="Unique user identifier")
    role: HealthcareRole = Field(..., description="Healthcare role")
    facility_id: str | None = Field(None, description="Healthcare facility ID")
    department: str | None = Field(None, description="Department assignment")
    expires_at: datetime = Field(..., description="Token expiration")
    issued_at: datetime = Field(..., description="Token issue time")


class AuthenticatedUser(BaseModel):
    """Authenticated healthcare user context"""

    user_id: str
    role: HealthcareRole
    facility_id: str | None = None
    department: str | None = None
    permissions: list[str] = Field(default_factory=list)


# Permission Definitions
ROLE_PERMISSIONS = {
    HealthcareRole.ADMIN: [
        "read:all_patients",
        "write:all_patients",
        "delete:all_patients",
        "read:system_config",
        "write:system_config",
        "read:audit_logs",
        "write:audit_logs",
    ],
    HealthcareRole.DOCTOR: [
        "read:patient_data",
        "write:patient_data",
        "read:medical_records",
        "write:medical_records",
        "read:prescriptions",
        "write:prescriptions",
    ],
    HealthcareRole.NURSE: [
        "read:patient_data",
        "write:patient_vitals",
        "read:medical_records",
        "write:nursing_notes",
    ],
    HealthcareRole.RECEPTIONIST: [
        "read:patient_demographics",
        "write:patient_demographics",
        "read:appointments",
        "write:appointments",
    ],
    HealthcareRole.BILLING: [
        "read:patient_demographics",
        "read:billing_data",
        "write:billing_data",
        "read:insurance_data",
        "write:insurance_data",
    ],
    HealthcareRole.RESEARCH: ["read:deidentified_data", "read:aggregated_data"],
}


class HealthcareAuthenticator:
    """HIPAA-compliant authentication manager"""

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.security = HTTPBearer()
        logger.info("Healthcare authenticator initialized")

    def create_access_token(
        self,
        user_id: str,
        role: HealthcareRole,
        facility_id: str | None = None,
        department: str | None = None,
        expires_delta: timedelta | None = None,
    ) -> str:
        """Create HIPAA-compliant JWT access token"""

        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(hours=8)  # Standard healthcare shift

        token_data = TokenData(
            user_id=user_id,
            role=role,
            facility_id=facility_id,
            department=department,
            expires_at=expire,
            issued_at=datetime.now(UTC),
        )

        to_encode = token_data.model_dump()
        to_encode["exp"] = expire.timestamp()

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

        # HIPAA Audit Log
        logger.info(
            f"Access token created - User: {user_id}, Role: {role.value}, "
            f"Facility: {facility_id}, Expires: {expire.isoformat()}",
        )

        return encoded_jwt

    def verify_token(self, token: str) -> TokenData:
        """Verify and decode healthcare JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Check expiration
            exp_timestamp = payload.get("exp")
            if exp_timestamp and datetime.fromtimestamp(exp_timestamp, UTC) < datetime.now(UTC):
                logger.warning(f"Expired token attempt - User: {payload.get('user_id')}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired",
                )

            # Create TokenData object
            return TokenData(
                user_id=payload["user_id"],
                role=HealthcareRole(payload["role"]),
                facility_id=payload.get("facility_id"),
                department=payload.get("department"),
                expires_at=datetime.fromtimestamp(exp_timestamp, UTC),
                issued_at=datetime.fromisoformat(payload["issued_at"]),
            )


        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token attempt: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials",
            )

    async def get_current_user(
        self, credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    ) -> AuthenticatedUser:
        """Extract authenticated user from request"""

        token_data = self.verify_token(credentials.credentials)

        # Get permissions for role
        permissions = ROLE_PERMISSIONS.get(token_data.role, [])

        user = AuthenticatedUser(
            user_id=token_data.user_id,
            role=token_data.role,
            facility_id=token_data.facility_id,
            department=token_data.department,
            permissions=permissions,
        )

        # HIPAA Audit Log
        logger.info(
            f"User authenticated - ID: {user.user_id}, Role: {user.role.value}, "
            f"Facility: {user.facility_id}, Permissions: {len(permissions)}",
        )

        return user


def require_permission(
    required_permission: str,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to require specific permission for endpoint access"""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract user from kwargs (assumes user is passed as dependency)
            user = None
            for arg in kwargs.values():
                if isinstance(arg, AuthenticatedUser):
                    user = arg
                    break

            if not user:
                logger.error("No authenticated user found in request")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required",
                )

            if required_permission not in user.permissions:
                logger.warning(
                    f"Permission denied - User: {user.user_id}, "
                    f"Required: {required_permission}, Has: {user.permissions}",
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission '{required_permission}' required",
                )

            # HIPAA Audit Log
            logger.info(
                f"Permission granted - User: {user.user_id}, Permission: {required_permission}",
            )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_role(
    required_role: HealthcareRole,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to require specific healthcare role"""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract user from kwargs
            user = None
            for arg in kwargs.values():
                if isinstance(arg, AuthenticatedUser):
                    user = arg
                    break

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required",
                )

            if user.role != required_role:
                logger.warning(
                    f"Role access denied - User: {user.user_id}, "
                    f"Required: {required_role.value}, Has: {user.role.value}",
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role '{required_role.value}' required",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Global healthcare authenticator instance
healthcare_authenticator: HealthcareAuthenticator | None = None


def get_healthcare_authenticator() -> HealthcareAuthenticator:
    """Get global healthcare authenticator instance"""
    global healthcare_authenticator
    if healthcare_authenticator is None:
        # In production, get this from secure environment variable
        secret_key = "your-secret-healthcare-jwt-key"  # TODO: Environment variable
        healthcare_authenticator = HealthcareAuthenticator(secret_key)
    return healthcare_authenticator


# Dependency for FastAPI endpoints
async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
) -> AuthenticatedUser:
    """FastAPI dependency to get authenticated user"""
    authenticator = get_healthcare_authenticator()
    return await authenticator.get_current_user(credentials)


# Common permission dependencies
async def require_doctor_access(
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """Require doctor-level access"""
    if "read:medical_records" not in user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Doctor-level access required",
        )
    return user


async def require_patient_data_access(
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """Require patient data access"""
    if "read:patient_data" not in user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Patient data access required",
        )
    return user
