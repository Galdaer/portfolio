"""
Role-Based Access Control (RBAC) Foundation for Intelluxe AI Healthcare System

Provides healthcare-appropriate RBAC with HIPAA compliance considerations
"""

import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """Healthcare resource types for RBAC"""

    PATIENT_DATA = "patient_data"
    MEDICAL_RECORDS = "medical_records"
    BILLING_INFO = "billing_info"
    SCHEDULING = "scheduling"
    REPORTS = "reports"
    SYSTEM_CONFIG = "system_config"
    USER_MANAGEMENT = "user_management"
    AUDIT_LOGS = "audit_logs"


class Permission(Enum):
    """Permissions for healthcare resources"""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    APPROVE = "approve"
    AUDIT = "audit"


@dataclass
class Role:
    """
    RBAC Role definition for healthcare system
    """

    name: str
    description: str
    permissions: dict[ResourceType, set[Permission]]
    is_active: bool = True

    def has_permission(self, resource: ResourceType, permission: Permission) -> bool:
        """Check if role has specific permission for resource"""
        resource_perms = self.permissions.get(resource, set())
        return permission in resource_perms or Permission.ADMIN in resource_perms


class RBACFoundation:
    """
    Foundation for Role-Based Access Control in healthcare environment

    Provides HIPAA-compliant access control with proper audit logging
    """

    def __init__(self) -> None:
        """Initialize RBAC foundation with default healthcare roles"""
        self.roles: dict[str, Role] = {}
        self.user_roles: dict[str, set[str]] = {}
        self._setup_default_roles()

    def _setup_default_roles(self) -> None:
        """Setup default healthcare roles"""

        # Healthcare Provider - can access patient data for care
        provider_role = Role(
            name="healthcare_provider",
            description="Licensed healthcare provider with patient care access",
            permissions={
                ResourceType.PATIENT_DATA: {Permission.READ, Permission.WRITE},
                ResourceType.MEDICAL_RECORDS: {Permission.READ, Permission.WRITE},
                ResourceType.SCHEDULING: {Permission.READ, Permission.WRITE},
                ResourceType.REPORTS: {Permission.READ},
            },
        )

        # Administrative Staff - billing and scheduling
        admin_staff_role = Role(
            name="administrative_staff",
            description="Administrative staff with limited access",
            permissions={
                ResourceType.BILLING_INFO: {Permission.READ, Permission.WRITE},
                ResourceType.SCHEDULING: {Permission.READ, Permission.WRITE},
                ResourceType.REPORTS: {Permission.READ},
            },
        )

        # System Administrator - technical system access
        sysadmin_role = Role(
            name="system_administrator",
            description="System administrator with technical access",
            permissions={
                ResourceType.SYSTEM_CONFIG: {Permission.ADMIN},
                ResourceType.USER_MANAGEMENT: {Permission.ADMIN},
                ResourceType.AUDIT_LOGS: {Permission.READ, Permission.AUDIT},
                ResourceType.REPORTS: {Permission.READ},
            },
        )

        # Auditor - read-only access for compliance
        auditor_role = Role(
            name="compliance_auditor",
            description="Compliance auditor with read-only access",
            permissions={
                ResourceType.AUDIT_LOGS: {Permission.READ, Permission.AUDIT},
                ResourceType.REPORTS: {Permission.READ},
                ResourceType.PATIENT_DATA: {Permission.READ},
                ResourceType.MEDICAL_RECORDS: {Permission.READ},
            },
        )

        self.roles = {
            "healthcare_provider": provider_role,
            "administrative_staff": admin_staff_role,
            "system_administrator": sysadmin_role,
            "compliance_auditor": auditor_role,
        }

    def assign_role(self, user_id: str, role_name: str) -> bool:
        """
        Assign role to user

        Args:
            user_id: User identifier
            role_name: Name of role to assign

        Returns:
            True if role assigned successfully
        """
        if role_name not in self.roles:
            logger.warning(f"Attempted to assign unknown role: {role_name}")
            return False

        if user_id not in self.user_roles:
            self.user_roles[user_id] = set()

        self.user_roles[user_id].add(role_name)
        logger.info(f"Role {role_name} assigned to user {user_id}")
        return True

    def check_permission(
        self, user_id: str, resource: ResourceType, permission: Permission,
    ) -> bool:
        """
        Check if user has permission for resource

        Args:
            user_id: User identifier
            resource: Resource type
            permission: Required permission

        Returns:
            True if user has permission
        """
        user_role_names = self.user_roles.get(user_id, set())

        for role_name in user_role_names:
            role = self.roles.get(role_name)
            if role and role.is_active and role.has_permission(resource, permission):
                return True

        return False

    def get_user_permissions(self, user_id: str) -> dict[ResourceType, set[Permission]]:
        """
        Get all permissions for user across all their roles

        Args:
            user_id: User identifier

        Returns:
            Dictionary of resource types to sets of permissions
        """
        all_permissions: dict[ResourceType, set[Permission]] = {}
        user_role_names = self.user_roles.get(user_id, set())

        for role_name in user_role_names:
            role = self.roles.get(role_name)
            if role and role.is_active:
                for resource, perms in role.permissions.items():
                    if resource not in all_permissions:
                        all_permissions[resource] = set()
                    all_permissions[resource].update(perms)

        return all_permissions
