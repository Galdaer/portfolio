"""
Role-Based Access Control (RBAC) Foundation
Healthcare-specific RBAC implementation with HIPAA compliance
"""

import json
import logging
import os
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import psycopg2
from psycopg2.extras import RealDictCursor

# Configure logging
logger = logging.getLogger(__name__)

class Permission(Enum):
    """System permissions"""
    # Patient data permissions
    READ_PATIENT_DATA = "read_patient_data"
    WRITE_PATIENT_DATA = "write_patient_data"
    DELETE_PATIENT_DATA = "delete_patient_data"
    
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

@dataclass
class Role:
    """Role definition"""
    role_id: str
    name: str
    description: str
    permissions: Set[Permission]
    resource_constraints: Dict[ResourceType, Dict[str, Any]]
    is_active: bool
    created_at: datetime
    updated_at: datetime

@dataclass
class User:
    """User definition"""
    user_id: str
    username: str
    email: str
    roles: Set[str]  # Role IDs
    is_active: bool
    last_login: Optional[datetime]
    created_at: datetime
    updated_at: datetime

@dataclass
class AccessRequest:
    """Access request for audit"""
    user_id: str
    resource_type: ResourceType
    resource_id: str
    permission: Permission
    context: Dict[str, Any]
    timestamp: datetime

class HealthcareRBACManager:
    """Healthcare-specific RBAC manager"""
    
    def __init__(self, postgres_conn):
        self.postgres_conn = postgres_conn
        self.logger = logging.getLogger(f"{__name__}.HealthcareRBACManager")

        # Configure strict mode for security
        self.STRICT_MODE = os.getenv('RBAC_STRICT_MODE', 'true').lower() == 'true'
        self.logger.info(f"RBAC strict mode: {'enabled' if self.STRICT_MODE else 'disabled'}")

        # Initialize RBAC tables
        self._init_rbac_tables()

        # Initialize default roles
        self._init_default_roles()
    
    def _init_rbac_tables(self):
        """Initialize RBAC database tables"""
        try:
            with self.postgres_conn.cursor() as cursor:
                # Roles table
                cursor.execute("""
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
                """)
                
                # Users table
                cursor.execute("""
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
                """)
                
                # Access log table
                cursor.execute("""
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
                """)
                
                # Role assignments audit table
                cursor.execute("""
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
                """)
                
                # Create indexes
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_rbac_users_user_id 
                    ON rbac_users(user_id)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_rbac_access_log_user_id 
                    ON rbac_access_log(user_id)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_rbac_access_log_timestamp 
                    ON rbac_access_log(timestamp)
                """)
                
            self.postgres_conn.commit()
            self.logger.info("RBAC tables initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize RBAC tables: {e}")
            raise
    
    def _init_default_roles(self):
        """Initialize default healthcare roles"""
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
                    Permission.USE_AI_TOOLS
                ],
                "resource_constraints": {}
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
                    Permission.READ_BILLING_DATA
                ],
                "resource_constraints": {
                    ResourceType.PATIENT: {"assigned_patients_only": True}
                }
            },
            {
                "role_id": "nurse",
                "name": "Nurse",
                "description": "Nursing staff with patient care access",
                "permissions": [
                    Permission.READ_PATIENT_DATA,
                    Permission.WRITE_PATIENT_DATA,
                    Permission.READ_MEDICAL_RECORDS,
                    Permission.USE_AI_TOOLS
                ],
                "resource_constraints": {
                    ResourceType.PATIENT: {"assigned_patients_only": True}
                }
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
                    Permission.TRAIN_AI_MODELS
                ],
                "resource_constraints": {
                    ResourceType.RESEARCH_DATA: {"anonymized_only": True}
                }
            },
            {
                "role_id": "billing_specialist",
                "name": "Billing Specialist",
                "description": "Billing and financial data access",
                "permissions": [
                    Permission.READ_BILLING_DATA,
                    Permission.WRITE_BILLING_DATA,
                    Permission.PROCESS_PAYMENTS
                ],
                "resource_constraints": {}
            },
            {
                "role_id": "ai_engineer",
                "name": "AI Engineer",
                "description": "AI/ML model development and deployment",
                "permissions": [
                    Permission.READ_RESEARCH_DATA,
                    Permission.USE_AI_TOOLS,
                    Permission.TRAIN_AI_MODELS,
                    Permission.DEPLOY_AI_MODELS
                ],
                "resource_constraints": {
                    ResourceType.RESEARCH_DATA: {"anonymized_only": True}
                }
            }
        ]
        
        for role_data in default_roles:
            try:
                # Check if role already exists
                with self.postgres_conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT role_id FROM rbac_roles WHERE role_id = %s
                    """, (role_data["role_id"],))
                    
                    if cursor.fetchone():
                        continue  # Role already exists
                
                # Create role
                role = Role(
                    role_id=role_data["role_id"],
                    name=role_data["name"],
                    description=role_data["description"],
                    permissions=set(role_data["permissions"]),
                    resource_constraints=role_data["resource_constraints"],
                    is_active=True,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                
                self.create_role(role)
                self.logger.info(f"Created default role: {role.name}")
                
            except Exception as e:
                self.logger.error(f"Failed to create default role {role_data['role_id']}: {e}")
    
    def create_role(self, role: Role) -> bool:
        """Create a new role"""
        try:
            with self.postgres_conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO rbac_roles 
                    (role_id, name, description, permissions, resource_constraints, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    role.role_id,
                    role.name,
                    role.description,
                    json.dumps([p.value for p in role.permissions]),
                    json.dumps(role.resource_constraints, default=str),
                    role.is_active
                ))
            
            self.postgres_conn.commit()
            self.logger.info(f"Created role: {role.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create role {role.role_id}: {e}")
            return False
    
    def create_user(self, user: User) -> bool:
        """Create a new user"""
        try:
            with self.postgres_conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO rbac_users 
                    (user_id, username, email, roles, is_active)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    user.user_id,
                    user.username,
                    user.email,
                    json.dumps(list(user.roles)),
                    user.is_active
                ))
            
            self.postgres_conn.commit()
            self.logger.info(f"Created user: {user.username}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create user {user.user_id}: {e}")
            return False
    
    def assign_role(self, user_id: str, role_id: str, assigned_by: str, reason: str = "") -> bool:
        """Assign role to user"""
        try:
            # Get current user roles
            user = self.get_user(user_id)
            if not user:
                raise ValueError(f"User not found: {user_id}")
            
            # Check if role exists
            role = self.get_role(role_id)
            if not role:
                raise ValueError(f"Role not found: {role_id}")
            
            # Add role to user
            user.roles.add(role_id)
            
            # Update user in database
            with self.postgres_conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE rbac_users 
                    SET roles = %s, updated_at = NOW()
                    WHERE user_id = %s
                """, (json.dumps(list(user.roles)), user_id))
                
                # Log role assignment
                cursor.execute("""
                    INSERT INTO rbac_role_assignments 
                    (user_id, role_id, assigned_by, reason)
                    VALUES (%s, %s, %s, %s)
                """, (user_id, role_id, assigned_by, reason))
            
            self.postgres_conn.commit()
            self.logger.info(f"Assigned role {role_id} to user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to assign role {role_id} to user {user_id}: {e}")
            return False
    
    def check_permission(self, user_id: str, permission: Permission, 
                        resource_type: ResourceType, resource_id: str,
                        context: Optional[Dict[str, Any]] = None) -> bool:
        """Check if user has permission for resource"""
        try:
            # Get user
            user = self.get_user(user_id)
            if not user or not user.is_active:
                self._log_access_attempt(user_id, permission, resource_type, resource_id, False, context)
                return False
            
            # Check each role
            for role_id in user.roles:
                role = self.get_role(role_id)
                if not role or not role.is_active:
                    continue
                
                # Check if role has permission
                if permission in role.permissions:
                    # Check resource constraints
                    if self._check_resource_constraints(role, resource_type, resource_id, context):
                        self._log_access_attempt(user_id, permission, resource_type, resource_id, True, context)
                        return True
            
            # No role granted permission
            self._log_access_attempt(user_id, permission, resource_type, resource_id, False, context)
            return False
            
        except Exception as e:
            self.logger.error(f"Permission check failed for user {user_id}: {e}")
            self._log_access_attempt(user_id, permission, resource_type, resource_id, False, context)
            return False

    def is_user_assigned_to_patient(self, user_id: str, patient_id: str) -> bool:
        """Check if user is assigned to specific patient"""
        # TODO: Replace with actual database/service lookup
        # For now, implement basic validation logic

        # Example implementation - replace with actual assignment service
        try:
            # This should query your patient assignment database/service
            # assignments = self.assignment_service.get_user_assignments(user_id)
            # return patient_id in assignments

            # Temporary implementation - log and deny for security
            self.logger.warning(f"Patient assignment check not fully implemented - denying access to patient {patient_id} for user {user_id}")
            return False
        except Exception as e:
            self.logger.error(f"Error checking patient assignment: {e}")
            return False

    def _check_resource_constraints(self, role: Role, resource_type: ResourceType,
                                  resource_id: str, context: Optional[Dict[str, Any]]) -> bool:
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

            if not self.is_user_assigned_to_patient(user_id, resource_id):
                self.logger.warning(f"Patient access denied - user {user_id} is not assigned to patient {resource_id}")
                return False

            # User is assigned to the patient, allow access
            self.logger.info(f"Patient access granted - user {user_id} is assigned to patient {resource_id}")
            return True

        # Check anonymized data only constraint
        if constraints.get("anonymized_only") and resource_type == ResourceType.RESEARCH_DATA:
            # TODO: Implement actual anonymization verification
            # For now, allow research data access but log for audit
            self.logger.info(f"Research data access granted - anonymization check pending for data {resource_id}")
            return True

        # Default to allow for other constraint types not yet implemented
        return True
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            with self.postgres_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM rbac_users WHERE user_id = %s
                """, (user_id,))
                
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
                    updated_at=row["updated_at"]
                )
                
        except Exception as e:
            self.logger.error(f"Failed to get user {user_id}: {e}")
            return None
    
    def get_role(self, role_id: str) -> Optional[Role]:
        """Get role by ID"""
        try:
            with self.postgres_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM rbac_roles WHERE role_id = %s
                """, (role_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                return Role(
                    role_id=row["role_id"],
                    name=row["name"],
                    description=row["description"],
                    permissions=set(Permission(p) for p in row["permissions"]),
                    resource_constraints=row["resource_constraints"] or {},
                    is_active=row["is_active"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"]
                )
                
        except Exception as e:
            self.logger.error(f"Failed to get role {role_id}: {e}")
            return None
    
    def _log_access_attempt(self, user_id: str, permission: Permission, 
                           resource_type: ResourceType, resource_id: str,
                           granted: bool, context: Optional[Dict[str, Any]]):
        """Log access attempt for audit"""
        try:
            with self.postgres_conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO rbac_access_log 
                    (user_id, resource_type, resource_id, permission, granted, context)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    user_id,
                    resource_type.value,
                    resource_id,
                    permission.value,
                    granted,
                    json.dumps(context) if context else None
                ))
            self.postgres_conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to log access attempt: {e}")
    
    def get_user_permissions(self, user_id: str) -> Set[Permission]:
        """Get all permissions for a user"""
        user = self.get_user(user_id)
        if not user:
            return set()
        
        permissions = set()
        for role_id in user.roles:
            role = self.get_role(role_id)
            if role and role.is_active:
                permissions.update(role.permissions)
        
        return permissions
    
    def get_access_summary(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """Get access summary for user"""
        try:
            with self.postgres_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        resource_type,
                        permission,
                        COUNT(*) as access_count,
                        SUM(CASE WHEN granted THEN 1 ELSE 0 END) as granted_count
                    FROM rbac_access_log 
                    WHERE user_id = %s 
                    AND timestamp > NOW() - INTERVAL '%s days'
                    GROUP BY resource_type, permission
                """, (user_id, days))
                
                access_stats = cursor.fetchall()
                
                return {
                    "user_id": user_id,
                    "period_days": days,
                    "access_statistics": [dict(row) for row in access_stats],
                    "total_attempts": sum(row["access_count"] for row in access_stats),
                    "total_granted": sum(row["granted_count"] for row in access_stats)
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get access summary for {user_id}: {e}")
            return {"error": str(e)}

# Example usage
if __name__ == "__main__":
    # This would be used in testing
    pass
