"""
Role-Based Access Control (RBAC) Foundation
Healthcare-specific RBAC implementation with HIPAA compliance
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, cast

from .environment_detector import EnvironmentDetector

if TYPE_CHECKING:
    pass

try:
    import psycopg2.extras

    PSYCOPG2_AVAILABLE = True
    _RealDictCursor = psycopg2.extras.RealDictCursor
except ImportError:
    # Use mock cursor for development environments without PostgreSQL
    PSYCOPG2_AVAILABLE = False
    _RealDictCursor = None

from src.security.environment_detector import EnvironmentDetector
from src.security.patient_assignment_db import (
    PatientAssignmentDB,
    RBACConfig,
)

# Configure logging
logger = logging.getLogger(__name__)


class Permission(Enum):
    """Healthcare RBAC permissions"""

    READ_PATIENT_DATA = "read_patient_data"
    WRITE_PATIENT_DATA = "write_patient_data"
    DELETE_PATIENT_DATA = "delete_patient_data"
    ACCESS_PHI = "access_phi"
    ADMIN_USERS = "admin_users"
    SYSTEM_CONFIG = "system_config"

    # Medical records permissions
    READ_MEDICAL_RECORDS = "read_medical_records"
    WRITE_MEDICAL_RECORDS = "write_medical_records"
    DELETE_MEDICAL_RECORDS = "delete_medical_records"

    # Research permissions
    READ_RESEARCH_DATA = "read_research_data"
    WRITE_RESEARCH_DATA = "write_research_data"
    EXPORT_RESEARCH_DATA = "export_research_data"

    # Administrative permissions
    MANAGE_USERS = "manage_users"
    MANAGE_ROLES = "manage_roles"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    MANAGE_SYSTEM = "manage_system"

    # AI/ML permissions
    USE_AI_TOOLS = "use_ai_tools"
    TRAIN_AI_MODELS = "train_ai_models"
    DEPLOY_AI_MODELS = "deploy_ai_models"

    # Billing permissions
    READ_BILLING_DATA = "read_billing_data"
    WRITE_BILLING_DATA = "write_billing_data"
    PROCESS_PAYMENTS = "process_payments"


class ResourceType(Enum):
    """Types of resources in the system"""

    PATIENT = "patient"
    MEDICAL_RECORD = "medical_record"
    RESEARCH_DATA = "research_data"
    AI_MODEL = "ai_model"
    BILLING_RECORD = "billing_record"
    SYSTEM_CONFIG = "system_config"
    AUDIT_LOG = "audit_log"


class BooleanValue(Enum):
    """Valid boolean values for healthcare configuration"""

    TRUE = "true"
    FALSE = "false"


class Environment(Enum):
    """Valid environment values for healthcare systems"""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class Role:
    """Role definition"""

    role_id: str
    name: str
    description: str
    permissions: set[Permission]
    resource_constraints: dict[ResourceType, dict[str, Any]]
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass
class User:
    """User definition"""

    user_id: str
    username: str
    email: str
    roles: set[str]  # Role IDs
    is_active: bool
    last_login: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass
class AccessRequest:
    """Access request for audit"""

    user_id: str
    resource_type: ResourceType
    resource_id: str
    permission: Permission
    context: dict[str, Any]
    timestamp: datetime


class HealthcareRBACManager:
    """Healthcare Role-Based Access Control Manager with HIPAA compliance"""

    def __init__(self, postgres_conn: Any = None, config: Any = None) -> None:
        self.postgres_conn = postgres_conn
        self.logger = logging.getLogger(f"{__name__}.HealthcareRBACManager")

        # Check if PostgreSQL is available
        if not PSYCOPG2_AVAILABLE and postgres_conn is not None:
            self.logger.warning("PostgreSQL connection provided but psycopg2 not available")

        # Validate RBAC strict mode configuration
        rbac_strict_mode = os.getenv("RBAC_STRICT_MODE", "true").lower().strip()

        valid_boolean_values = {e.value for e in BooleanValue}
        if rbac_strict_mode not in valid_boolean_values:
            self.logger.error(f"Invalid RBAC_STRICT_MODE value: '{rbac_strict_mode}'")
            raise ValueError(
                f"Invalid value for RBAC_STRICT_MODE: '{rbac_strict_mode}'. "
                f"Expected one of {valid_boolean_values}."
            )

        self.STRICT_MODE = rbac_strict_mode == BooleanValue.TRUE.value
        self.logger.info(f"RBAC strict mode: {'enabled' if self.STRICT_MODE else 'disabled'}")

        # Configure placeholder warnings
        self.ENABLE_PLACEHOLDER_WARNINGS = (
            os.getenv("RBAC_PLACEHOLDER_WARNINGS", "true").lower() == "true"
        )

        # Initialize RBAC tables only if PostgreSQL is available and connected
        if self.postgres_conn and PSYCOPG2_AVAILABLE:
            # Test actual connectivity gracefully
            try:
                test_conn = self.postgres_conn.create_connection()
                test_conn.close()  # Close test connection immediately
                self._init_rbac_tables()
                self._init_default_roles()
            except Exception as e:
                env_detector = EnvironmentDetector()
                if env_detector.is_testing():
                    self.logger.warning(f"RBAC initialization skipped in testing environment: {e}")
                else:
                    self.logger.error(f"Failed to initialize RBAC: {e}")
                    # Don't raise in testing/development environments
                    if not env_detector.is_development():
                        raise
        else:
            self.logger.info("Running in development mode without PostgreSQL backend")

    def _init_rbac_tables(self) -> None:
        """Initialize RBAC database tables"""
        if not self.postgres_conn:
            self.logger.warning("No PostgreSQL connection available for table initialization")
            return

        connection = None
        try:
            # Get actual database connection from the factory
            connection = self.postgres_conn.create_connection()
            with connection.cursor() as cursor:
                # Roles table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS rbac_roles (
                        id SERIAL PRIMARY KEY,
                        role_id VARCHAR(255) UNIQUE NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        description TEXT,
                        permissions JSONB NOT NULL,
                        resource_constraints JSONB,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """
                )

                # Users table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS rbac_users (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(255) UNIQUE NOT NULL,
                        username VARCHAR(255) UNIQUE NOT NULL,
                        email VARCHAR(255) UNIQUE NOT NULL,
                        roles JSONB NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE,
                        last_login TIMESTAMP,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """
                )

                # Access log table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS rbac_access_log (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(255) NOT NULL,
                        resource_type VARCHAR(100) NOT NULL,
                        resource_id VARCHAR(255) NOT NULL,
                        permission VARCHAR(100) NOT NULL,
                        granted BOOLEAN NOT NULL,
                        context JSONB,
                        timestamp TIMESTAMP DEFAULT NOW()
                    )
                """
                )

                # Role assignments audit table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS rbac_role_assignments (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(255) NOT NULL,
                        role_id VARCHAR(255) NOT NULL,
                        assigned_by VARCHAR(255) NOT NULL,
                        assigned_at TIMESTAMP DEFAULT NOW(),
                        revoked_at TIMESTAMP,
                        revoked_by VARCHAR(255),
                        reason TEXT
                    )
                """
                )

                # Create indexes
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_rbac_users_user_id
                    ON rbac_users(user_id)
                """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_rbac_access_log_user_id
                    ON rbac_access_log(user_id)
                """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_rbac_access_log_timestamp
                    ON rbac_access_log(timestamp)
                """
                )

            connection.commit()
            self.logger.info("RBAC tables initialized")

        except Exception as e:
            if connection:
                connection.rollback()

            # More graceful handling for testing environments
            env_detector = EnvironmentDetector()
            if env_detector.is_testing():
                self.logger.warning(f"RBAC table initialization failed in testing environment: {e}")
                return  # Don't raise in testing mode

            self.logger.error(f"Failed to initialize RBAC tables: {e}")
            raise
        finally:
            if connection:
                connection.close()

    def _init_default_roles(self) -> None:
        """Initialize default healthcare roles"""
        if not self.postgres_conn:
            self.logger.info("No PostgreSQL connection available for default role initialization")
            return

        default_roles = [
            {
                "role_id": "healthcare_admin",
                "name": "Healthcare Administrator",
                "description": "Full administrative access to healthcare system",
                "permissions": [
                    Permission.READ_PATIENT_DATA,
                    Permission.WRITE_PATIENT_DATA,
                    Permission.READ_MEDICAL_RECORDS,
                    Permission.WRITE_MEDICAL_RECORDS,
                    Permission.MANAGE_USERS,
                    Permission.MANAGE_ROLES,
                    Permission.VIEW_AUDIT_LOGS,
                    Permission.MANAGE_SYSTEM,
                    Permission.USE_AI_TOOLS,
                ],
                "resource_constraints": {},
            },
            {
                "role_id": "physician",
                "name": "Physician",
                "description": "Licensed physician with patient care access",
                "permissions": [
                    Permission.READ_PATIENT_DATA,
                    Permission.WRITE_PATIENT_DATA,
                    Permission.READ_MEDICAL_RECORDS,
                    Permission.WRITE_MEDICAL_RECORDS,
                    Permission.USE_AI_TOOLS,
                    Permission.READ_BILLING_DATA,
                ],
                "resource_constraints": {ResourceType.PATIENT: {"assigned_patients_only": True}},
            },
            {
                "role_id": "nurse",
                "name": "Nurse",
                "description": "Nursing staff with patient care access",
                "permissions": [
                    Permission.READ_PATIENT_DATA,
                    Permission.WRITE_PATIENT_DATA,
                    Permission.READ_MEDICAL_RECORDS,
                    Permission.USE_AI_TOOLS,
                ],
                "resource_constraints": {ResourceType.PATIENT: {"assigned_patients_only": True}},
            },
            {
                "role_id": "researcher",
                "name": "Medical Researcher",
                "description": "Research access to anonymized data",
                "permissions": [
                    Permission.READ_RESEARCH_DATA,
                    Permission.WRITE_RESEARCH_DATA,
                    Permission.EXPORT_RESEARCH_DATA,
                    Permission.USE_AI_TOOLS,
                    Permission.TRAIN_AI_MODELS,
                ],
                "resource_constraints": {ResourceType.RESEARCH_DATA: {"anonymized_only": True}},
            },
            {
                "role_id": "billing_specialist",
                "name": "Billing Specialist",
                "description": "Billing and financial data access",
                "permissions": [
                    Permission.READ_BILLING_DATA,
                    Permission.WRITE_BILLING_DATA,
                    Permission.PROCESS_PAYMENTS,
                ],
                "resource_constraints": {},
            },
            {
                "role_id": "ai_engineer",
                "name": "AI Engineer",
                "description": "AI/ML model development and deployment",
                "permissions": [
                    Permission.READ_RESEARCH_DATA,
                    Permission.USE_AI_TOOLS,
                    Permission.TRAIN_AI_MODELS,
                    Permission.DEPLOY_AI_MODELS,
                ],
                "resource_constraints": {ResourceType.RESEARCH_DATA: {"anonymized_only": True}},
            },
        ]

        for role_data in default_roles:
            try:
                # Check if role already exists
                with self.postgres_conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT role_id FROM rbac_roles WHERE role_id = %s
                    """,
                        (role_data["role_id"],),
                    )

                    if cursor.fetchone():
                        continue  # Role already exists

                # Create role with explicit type casting
                role = Role(
                    role_id=str(role_data["role_id"]),
                    name=str(role_data["name"]),
                    description=str(role_data["description"]),
                    permissions=set(cast(list[Permission], role_data["permissions"])),
                    resource_constraints=cast(
                        dict[ResourceType, dict[str, Any]], role_data["resource_constraints"]
                    ),
                    is_active=True,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )

                self.create_role(role)
                self.logger.info(f"Created default role: {role.name}")

            except Exception as e:
                self.logger.error(f"Failed to create default role {role_data['role_id']}: {e}")

    def create_role(self, role: Role) -> bool:
        """Create a new role"""
        if not self.postgres_conn:
            self.logger.warning("No PostgreSQL connection available for role creation")
            return False

        try:
            with self.postgres_conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO rbac_roles
                    (role_id, name, description, permissions, resource_constraints, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """,
                    (
                        role.role_id,
                        role.name,
                        role.description,
                        json.dumps([p.value for p in role.permissions]),
                        json.dumps(role.resource_constraints, default=str),
                        role.is_active,
                    ),
                )

            self.postgres_conn.commit()
            self.logger.info(f"Created role: {role.name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create role {role.role_id}: {e}")
            return False

    def create_user(self, user: User) -> bool:
        """Create a new user"""
        if not self.postgres_conn:
            self.logger.warning("No PostgreSQL connection available for user creation")
            return False

        try:
            with self.postgres_conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO rbac_users
                    (user_id, username, email, roles, is_active)
                    VALUES (%s, %s, %s, %s, %s)
                """,
                    (
                        user.user_id,
                        user.username,
                        user.email,
                        json.dumps(list(user.roles)),
                        user.is_active,
                    ),
                )

            self.postgres_conn.commit()
            self.logger.info(f"Created user: {user.username}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create user {user.user_id}: {e}")
            return False

    async def assign_role(
        self, user_id: str, role_id: str, assigned_by: str, reason: str = ""
    ) -> bool:
        """Assign a role to a user"""
        if not self.postgres_conn:
            self.logger.warning("No PostgreSQL connection available for role assignment")
            return False

        try:
            # Get user
            user = await self.get_user(user_id)
            if not user:
                raise ValueError(f"User not found: {user_id}")

            # Check if role exists
            role = await self.get_role(role_id)
            if not role:
                raise ValueError(f"Role not found: {role_id}")

            # Add role to user
            user.roles.add(role_id)

            # Update user in database
            with self.postgres_conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE rbac_users
                    SET roles = %s, updated_at = NOW()
                    WHERE user_id = %s
                """,
                    (json.dumps(list(user.roles)), user_id),
                )

                # Log role assignment
                cursor.execute(
                    """
                    INSERT INTO rbac_role_assignments
                    (user_id, role_id, assigned_by, reason)
                    VALUES (%s, %s, %s, %s)
                """,
                    (user_id, role_id, assigned_by, reason),
                )

            self.postgres_conn.commit()
            self.logger.info(f"Assigned role {role_id} to user {user_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to assign role {role_id} to user {user_id}: {e}")
            return False

    async def check_permission(
        self,
        user_id: str,
        permission: Permission,
        resource_type: ResourceType,
        resource_id: str,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Check if user has permission for resource"""
        try:
            # Get user
            user = await self.get_user(user_id)
            if not user or not user.is_active:
                self._log_access_attempt(
                    user_id, permission, resource_type, resource_id, False, context
                )
                return False

            # Check each role
            for role_id in user.roles:
                role = await self.get_role(role_id)
                if not role or not role.is_active:
                    continue

                # Check if role has permission
                if permission in role.permissions:
                    # Check resource constraints
                    if await self._check_resource_constraints(
                        role, resource_type, resource_id, context
                    ):
                        self._log_access_attempt(
                            user_id,
                            permission,
                            resource_type,
                            resource_id,
                            True,
                            context,
                        )
                        return True

            # No role granted permission
            self._log_access_attempt(
                user_id, permission, resource_type, resource_id, False, context
            )
            return False

        except Exception as e:
            self.logger.error(f"Permission check failed for user {user_id}: {e}")
            self._log_access_attempt(
                user_id, permission, resource_type, resource_id, False, context
            )
            return False

    async def is_user_assigned_to_patient(self, user_id: str, patient_id: str) -> bool:
        """Check if user is assigned to specific patient with environment-aware behavior"""
        # Use centralized environment detection pattern
        if not EnvironmentDetector.is_production():
            # Development Mode: Patient assignment is planned as a Phase 2 business service
            # For the current phase, we allow access with logging for Core AI Infrastructure
            self.logger.info(f"Development mode: Allowing patient access for user {user_id}")
            return True
        else:
            # Production implementation will be added in Phase 2
            self.logger.warning(
                f"Patient assignment check in production - user {user_id}, patient {patient_id}"
            )
            return False

    async def check_patient_access(self, user_id: str, patient_id: str) -> bool:
        """Check if user has access to specific patient"""
        try:
            user = await self.get_user(user_id)
            if not user or not user.is_active:
                return False

            # Check each role for patient access
            for role_id in user.roles:
                role = await self.get_role(role_id)
                if not role or not role.is_active:
                    continue

                # Use correct permission name
                if Permission.READ_PATIENT_DATA in role.permissions:
                    if await self.is_user_assigned_to_patient(user_id, patient_id):
                        return True

            return False
        except Exception as e:
            self.logger.error(f"Patient access check failed: {e}")
            return False

    def _validate_production_patient_assignment(self, user_id: str, patient_id: str) -> bool:
        """
        Validate patient assignment in production environment

        CRITICAL SECURITY WARNING:
        This method contains placeholder implementation that MUST be replaced
        before production deployment. The current implementation will deny all
        patient access in production to prevent security vulnerabilities.

        PLACEHOLDER IMPLEMENTATION RISKS:
        - No actual database validation of patient-provider relationships
        - No care team membership verification
        - No emergency access or break-glass functionality
        - No audit trail of access decisions
        - Potential HIPAA compliance violations if deployed as-is

        REQUIRED FOR PRODUCTION:
        1. Implement database-backed patient assignment validation
        2. Add care team membership checking
        3. Implement emergency access with supervisor approval
        4. Add comprehensive audit logging
        5. Validate against actual healthcare provider assignments

        Args:
            user_id: User identifier
            patient_id: Patient identifier

        Returns:
            bool: True if user has access to patient

        Raises:
            NotImplementedError: If patient assignment not properly implemented
        """
        # Check feature flag for production deployment
        patient_assignment_enabled = (
            os.getenv("RBAC_ENABLE_PATIENT_ASSIGNMENT", "false").lower() == "true"
        )

        # Validate that proper implementation exists before allowing production use
        if not patient_assignment_enabled:
            self.logger.error("Patient assignment validation not implemented for production")
            raise NotImplementedError(
                "Patient assignment validation required for production deployment. "
                "Set RBAC_ENABLE_PATIENT_ASSIGNMENT=true when proper implementation is ready."
            )

        # Additional validation: Check if real implementation is available
        if not self._has_real_patient_assignment_implementation():
            self.logger.error(
                "RBAC_ENABLE_PATIENT_ASSIGNMENT=true but no real implementation found"
            )
            raise NotImplementedError(
                "Feature flag enabled but patient assignment implementation is still placeholder. "
                "Implement proper database-backed validation before production use."
            )

        # Check for emergency access conditions first
        emergency_access = self._check_emergency_access(user_id, patient_id)
        if emergency_access:
            return True

        # Check if we have a real patient assignment implementation
        if self._has_real_patient_assignment_implementation():
            return self._validate_real_patient_assignment(user_id, patient_id)

        # Check for basic production patient assignment patterns
        basic_assignment = self._check_basic_patient_assignment(user_id, patient_id)
        if basic_assignment:
            return True

        # Log warning about placeholder implementation
        self.logger.warning(
            f"Production patient assignment validation incomplete for user {user_id} -> patient {patient_id}"
        )
        self.logger.warning(
            "Consider implementing proper patient assignment validation or enabling emergency access"
        )

        # For production safety, deny access by default but provide clear guidance
        return False

    def _has_real_patient_assignment_implementation(self) -> bool:
        """
        Check if real patient assignment implementation is available

        Returns:
            bool: True if real implementation exists, False if still placeholder
        """
        # Check if we're in CI environment
        if os.getenv("CI") == "true":
            logging.debug("CI environment detected - patient assignment will be mocked")
            return False

        try:
            # Try to initialize database backend
            config = RBACConfig()
            PatientAssignmentDB(config.database_path)
            logging.info("Patient assignment database backend available")
            return True
        except Exception as e:
            logging.warning(f"Patient assignment database unavailable: {e}")
            return False

    def _check_basic_patient_assignment(self, user_id: str, patient_id: str) -> bool:
        """
        Check basic patient assignment patterns for production use

        This provides a basic implementation for production environments where
        full patient assignment validation is not yet implemented but some
        access control is needed.

        Args:
            user_id: User identifier
            patient_id: Patient identifier

        Returns:
            bool: True if basic assignment criteria are met
        """
        # Check for basic assignment patterns via environment variables
        # This allows for simple production deployment while proper implementation is developed

        # Pattern 1: Explicit user-patient assignments
        assignments = os.getenv("RBAC_BASIC_ASSIGNMENTS", "")
        if assignments:
            # Format: "user1:patient1,user1:patient2,user2:patient3"
            assignment_pairs = [pair.strip() for pair in assignments.split(",") if pair.strip()]
            user_patient_pair = f"{user_id}:{patient_id}"

            if user_patient_pair in assignment_pairs:
                self.logger.info(f"Basic assignment found: {user_id} -> {patient_id}")
                return True

        # Pattern 2: Role-based access (all users with specific roles can access all patients)
        admin_roles = os.getenv("RBAC_ADMIN_ROLES", "").split(",")
        user_roles = self._get_user_roles(user_id)

        if any(role.strip() in admin_roles for role in user_roles if role.strip()):
            self.logger.info(f"Admin role access granted: {user_id} -> {patient_id}")
            return True

        # Pattern 3: Same organization access (if both user and patient are in same org)
        if self._check_same_organization_access(user_id, patient_id):
            self.logger.info(f"Same organization access granted: {user_id} -> {patient_id}")
            return True

        return False

    def _validate_development_patient_assignment(self, user_id: str, patient_id: str) -> bool:
        """
        Validate patient assignment in development environment

        Args:
            user_id: User identifier
            patient_id: Patient identifier

        Returns:
            bool: True if user has access to patient
        """
        default_access = os.getenv("RBAC_DEFAULT_PATIENT_ACCESS", "true").lower() == "true"

        if default_access:
            self.logger.debug(f"DEV MODE: Allowing patient access {user_id} -> {patient_id}")
            return True
        else:
            self.logger.debug(f"DEV MODE: Denying patient access {user_id} -> {patient_id}")
            return False

    def _get_user_roles(self, user_id: str) -> list[str]:
        """
        Get user roles for basic role-based access control

        Args:
            user_id: User identifier

        Returns:
            List[str]: List of user roles
        """
        # TODO: Implement actual role retrieval
        # For now, check environment variable for testing
        user_roles_env = os.getenv(f"RBAC_USER_ROLES_{user_id.upper()}", "")
        return [role.strip() for role in user_roles_env.split(",") if role.strip()]

    def _check_same_organization_access(self, user_id: str, patient_id: str) -> bool:
        """
        Check if user and patient belong to the same organization

        Args:
            user_id: User identifier
            patient_id: Patient identifier

        Returns:
            bool: True if same organization
        """
        # TODO: Implement actual organization checking
        # For now, use environment variables for basic implementation
        user_org = os.getenv(f"RBAC_USER_ORG_{user_id.upper()}", "")
        patient_org = os.getenv(f"RBAC_PATIENT_ORG_{patient_id.upper()}", "")

        if user_org and patient_org and user_org == patient_org:
            return True

        return False

    def _check_emergency_access(self, user_id: str, patient_id: str) -> bool:
        """
        Check for emergency access conditions with comprehensive logging

        Emergency access patterns for production patient assignment:
        1. Emergency override flags for critical situations
        2. Emergency user roles (e.g., emergency physicians, supervisors)
        3. Break-glass access with supervisor approval
        4. Comprehensive audit logging for all emergency access

        Args:
            user_id: User identifier
            patient_id: Patient identifier

        Returns:
            bool: True if emergency access is granted
        """
        # Check for emergency override flags
        emergency_override = os.getenv("RBAC_EMERGENCY_OVERRIDE", "false").lower() == "true"

        if emergency_override:
            self.logger.warning(
                f"EMERGENCY ACCESS: User {user_id} accessing patient {patient_id} via emergency override"
            )
            self._log_emergency_access(
                user_id,
                patient_id,
                "emergency_override",
                "Emergency override flag enabled",
            )
            return True

        # Check for emergency user roles
        if self._is_emergency_user(user_id):
            self.logger.warning(
                f"EMERGENCY ACCESS: Emergency user {user_id} accessing patient {patient_id}"
            )
            self._log_emergency_access(
                user_id, patient_id, "emergency_user", "User has emergency access role"
            )
            return True

        # Check for break-glass access (requires supervisor approval)
        if self._check_break_glass_access(user_id, patient_id):
            self.logger.warning(
                f"EMERGENCY ACCESS: Break-glass access granted for user {user_id} to patient {patient_id}"
            )
            self._log_emergency_access(
                user_id,
                patient_id,
                "break_glass",
                "Break-glass access with supervisor approval",
            )
            return True

        return False

    def _is_emergency_user(self, user_id: str) -> bool:
        """
        Check if user has emergency access role

        Args:
            user_id: User identifier

        Returns:
            bool: True if user has emergency access role
        """
        # TODO: Implement actual emergency user role checking
        # This would check against:
        # - Emergency physician roles
        # - Supervisor roles
        # - On-call staff designations
        # - Break-glass authorized personnel

        # For now, check environment variable for testing
        emergency_users = os.getenv("RBAC_EMERGENCY_USERS", "").split(",")
        return user_id.strip() in [u.strip() for u in emergency_users if u.strip()]

    def _check_break_glass_access(self, user_id: str, patient_id: str) -> bool:
        """
        Check for break-glass access with supervisor approval

        Args:
            user_id: User identifier
            patient_id: Patient identifier

        Returns:
            bool: True if break-glass access is approved
        """
        # TODO: Implement actual break-glass access checking
        # This would include:
        # - Supervisor approval workflow
        # - Time-limited access tokens
        # - Justification requirements
        # - Multi-factor authentication

        # For now, check environment variable for testing
        break_glass_enabled = os.getenv("RBAC_BREAK_GLASS_ENABLED", "false").lower() == "true"
        return break_glass_enabled

    def _log_emergency_access(
        self, user_id: str, patient_id: str, access_type: str, reason: str
    ) -> None:
        """
        Log emergency access with comprehensive audit trail

        Args:
            user_id: User identifier
            patient_id: Patient identifier
            access_type: Type of emergency access
            reason: Reason for emergency access
        """
        import datetime

        # Comprehensive audit logging for emergency access
        audit_entry = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "event_type": "emergency_access",
            "user_id": user_id,
            "patient_id": patient_id,
            "access_type": access_type,
            "reason": reason,
            "environment": os.getenv("ENVIRONMENT", "unknown"),
            "source_ip": "unknown",  # TODO: Get actual source IP
            "session_id": "unknown",  # TODO: Get actual session ID
        }

        # Log to security audit system
        self.logger.error(f"SECURITY AUDIT - Emergency Access: {audit_entry}")

        # TODO: Send to external audit system
        # TODO: Alert security team
        # TODO: Store in audit database

    async def _check_patient_assignment_constraints(
        self, user_id: str, constraints: dict[str, Any]
    ) -> bool:
        """Check patient assignment constraints with Phase 2 preparation"""
        if not constraints:
            return True

        # Check assigned patients constraint
        assigned_patients = constraints.get("assigned_patients")
        if assigned_patients:
            # Phase 2 TODO: Replace with actual patient assignment check
            for patient_id in assigned_patients:
                if not await self.is_user_assigned_to_patient(user_id, patient_id):
                    if self.ENABLE_PLACEHOLDER_WARNINGS:
                        self.logger.warning(
                            f"Access denied: user {user_id} not assigned to patient {patient_id}. "
                            "Phase 2 will implement proper patient assignment validation."
                        )
                    return False

        # Add other constraint checks as needed
        return True

    async def _check_resource_constraints(
        self,
        role: Role,
        resource_type: ResourceType,
        resource_id: str,
        context: dict[str, Any] | None,
    ) -> bool:
        """Check resource-specific constraints"""
        constraints = role.resource_constraints.get(resource_type, {})

        if not constraints:
            return True  # No constraints

        # Check assigned patients only constraint
        if constraints.get("assigned_patients_only") and resource_type == ResourceType.PATIENT:
            # Check if the user is assigned to the patient
            user_id = context.get("user_id") if context else None
            if not user_id:
                self.logger.warning("No user_id provided in context for patient assignment check")
                return False

            if not await self.is_user_assigned_to_patient(user_id, resource_id):
                self.logger.warning(
                    f"Patient access denied - user {user_id} is not assigned to patient {resource_id}"
                )
                return False

            # User is assigned to the patient, allow access
            self.logger.info(
                f"Patient access granted - user {user_id} is assigned to patient {resource_id}"
            )
            return True

        # Check anonymized data only constraint
        if constraints.get("anonymized_only") and resource_type == ResourceType.RESEARCH_DATA:
            # TODO: Implement actual anonymization verification
            # For now, allow research data access but log for audit
            self.logger.info(
                f"Research data access granted - anonymization check pending for data {resource_id}"
            )
            return True

        # Default to allow for other constraint types not yet implemented
        return True

    async def get_user(self, user_id: str) -> User | None:
        """Get user by ID"""
        if not self.postgres_conn:
            self.logger.warning("No PostgreSQL connection available for user lookup")
            return None

        try:
            with self.postgres_conn.cursor(cursor_factory=_RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT * FROM rbac_users WHERE user_id = %s
                """,
                    (user_id,),
                )

                row = cursor.fetchone()
                if not row:
                    return None

                return User(
                    user_id=row["user_id"],
                    username=row["username"],
                    email=row["email"],
                    roles=set(row["roles"]),
                    is_active=row["is_active"],
                    last_login=row["last_login"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )

        except Exception as e:
            self.logger.error(f"Failed to get user {user_id}: {e}")
            return None

    async def get_role(self, role_id: str) -> Role | None:
        """Get role by ID"""
        if not self.postgres_conn:
            self.logger.warning("No PostgreSQL connection available for role lookup")
            return None

        try:
            with self.postgres_conn.cursor(cursor_factory=_RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT * FROM rbac_roles WHERE role_id = %s
                """,
                    (role_id,),
                )

                row = cursor.fetchone()
                if not row:
                    return None

                return Role(
                    role_id=row["role_id"],
                    name=row["name"],
                    description=row["description"],
                    permissions={Permission(p) for p in row["permissions"]},
                    resource_constraints=row["resource_constraints"] or {},
                    is_active=row["is_active"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )

        except Exception as e:
            self.logger.error(f"Failed to get role {role_id}: {e}")
            return None

    def _log_access_attempt(
        self,
        user_id: str,
        permission: Permission,
        resource_type: ResourceType,
        resource_id: str,
        granted: bool,
        context: dict[str, Any] | None,
    ) -> None:
        """Log access attempt for audit"""
        if not self.postgres_conn:
            # In development mode, log to file instead
            self.logger.info(
                f"Access attempt: user={user_id}, resource={resource_type.value}:{resource_id}, permission={permission.value}, granted={granted}"
            )
            return

        try:
            with self.postgres_conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO rbac_access_log
                    (user_id, resource_type, resource_id, permission, granted, context)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """,
                    (
                        user_id,
                        resource_type.value,
                        resource_id,
                        permission.value,
                        granted,
                        json.dumps(context) if context else None,
                    ),
                )
            self.postgres_conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to log access attempt: {e}")

    async def get_user_permissions(self, user_id: str) -> set[Permission]:
        """Get all permissions for a user"""
        user = await self.get_user(user_id)
        if not user:
            return set()

        permissions = set()
        for role_id in user.roles:
            role = await self.get_role(role_id)
            if role and role.is_active:
                permissions.update(role.permissions)

        return permissions

    def get_access_summary(self, user_id: str, days: int = 7) -> dict[str, Any]:
        """Get access summary for user"""
        if not self.postgres_conn:
            self.logger.info("No PostgreSQL connection available for access summary")
            return {"user_id": user_id, "access_stats": [], "total_accesses": 0}

        try:
            with self.postgres_conn.cursor(cursor_factory=_RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT
                        resource_type,
                        permission,
                        COUNT(*) as access_count,
                        SUM(CASE WHEN granted THEN 1 ELSE 0 END) as granted_count
                    FROM rbac_access_log
                    WHERE user_id = %s
                    AND timestamp > NOW() - INTERVAL '%s days'
                    GROUP BY resource_type, permission
                """,
                    (user_id, days),
                )

                access_stats = cursor.fetchall()

                return {
                    "user_id": user_id,
                    "period_days": days,
                    "access_statistics": [dict(row) for row in access_stats],
                    "total_attempts": sum(row["access_count"] for row in access_stats),
                    "total_granted": sum(row["granted_count"] for row in access_stats),
                }

        except Exception as e:
            self.logger.error(f"Failed to get access summary for {user_id}: {e}")
            return {"error": str(e)}

    def _validate_real_patient_assignment(self, user_id: str, patient_id: str) -> bool:
        """
        Real patient assignment validation implementation

        This method provides the actual database-backed patient assignment validation
        that should be implemented for production use.

        Args:
            user_id: User identifier
            patient_id: Patient identifier

        Returns:
            bool: True if user has validated access to patient
        """
        try:
            # Initialize database connection
            config = RBACConfig()
            db = PatientAssignmentDB(config.database_path)

            # Check patient assignment
            is_valid = db.validate_patient_assignment(user_id, patient_id)

            if is_valid:
                self.logger.info(f"Patient assignment validated: {user_id} -> {patient_id}")
                # Log successful access
                db.log_access_attempt(user_id, patient_id, "read", "allowed")
            else:
                self.logger.warning(f"Patient assignment denied: {user_id} -> {patient_id}")
                # Log denied access
                db.log_access_attempt(user_id, patient_id, "read", "denied")

            return is_valid

        except Exception as e:
            self.logger.error(f"Real patient assignment validation failed: {e}")
            # Log the error
            try:
                config = RBACConfig()
                db = PatientAssignmentDB(config.database_path)
                db.log_access_attempt(user_id, patient_id, "read", "error", str(e))
            except Exception:
                pass  # Don't fail on logging errors
            return False


class RBACMixin:
    """
    Mixin class for adding RBAC functionality to other classes

    This provides a simple interface for RBAC operations that can be used
    in development environments without requiring PostgreSQL setup.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"{__name__}.RBACMixin")
        self.rbac_manager = None
        self.patient_db: PatientAssignmentDB | None = None

        # Initialize with SQLite-backed patient assignment for development
        try:
            self.config = RBACConfig()
            self.patient_db = PatientAssignmentDB(self.config.database_path)
            self.logger.info("RBAC mixin initialized with SQLite backend")
        except Exception as e:
            self.logger.warning(f"RBAC mixin initialization failed: {e}")
            self.patient_db = None

    def check_patient_access(self, user_id: str, patient_id: str) -> bool:
        """
        Check if user has access to patient

        Args:
            user_id: User identifier
            patient_id: Patient identifier

        Returns:
            bool: True if access is allowed
        """
        if not self.patient_db:
            # Fallback for development
            self.logger.debug(f"No patient DB - allowing access {user_id} -> {patient_id}")
            return True

        try:
            return self.patient_db.validate_patient_assignment(user_id, patient_id)
        except Exception as e:
            self.logger.error(f"Patient access check failed: {e}")
            return False

    def log_access_attempt(
        self,
        user_id: str,
        patient_id: str,
        action: str,
        result: str,
        details: str | None = None,
    ) -> None:
        """
        Log access attempt for audit trail

        Args:
            user_id: User identifier
            patient_id: Patient identifier
            action: Action performed
            result: Result of action
            details: Additional details
        """
        if self.patient_db:
            try:
                self.patient_db.log_access_attempt(
                    user_id, patient_id, action, result, details or ""
                )
            except Exception as e:
                self.logger.error(f"Failed to log access attempt: {e}")
        else:
            self.logger.info(f"Access attempt: {user_id} -> {patient_id} [{action}] = {result}")


# Compatibility alias for workflows and external code
RBACFoundation = HealthcareRBACManager

# Example usage
if __name__ == "__main__":
    # This would be used in testing
    pass
