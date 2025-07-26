"""
Patient Assignment Database Implementation
Handles database-backed patient assignment validation for healthcare RBAC
"""

import sqlite3
import secrets
import jwt
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class PatientAssignmentDB:
    """Database handler for patient assignment validation"""

    def __init__(self, db_path: str = "healthcare.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(f"{__name__}.PatientAssignmentDB")
        self.init_database()

    def init_database(self):
        """Initialize patient assignment tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS patient_assignments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        patient_id TEXT NOT NULL,
                        assignment_type TEXT DEFAULT 'primary',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1,
                        UNIQUE(user_id, patient_id)
                    )
                ''')

                conn.execute('''
                    CREATE TABLE IF NOT EXISTS emergency_access (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        patient_id TEXT NOT NULL,
                        supervisor_id TEXT,
                        reason TEXT NOT NULL,
                        granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP NOT NULL,
                        is_active BOOLEAN DEFAULT 1
                    )
                ''')

                conn.execute('''
                    CREATE TABLE IF NOT EXISTS audit_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        patient_id TEXT,
                        action TEXT NOT NULL,
                        result TEXT NOT NULL,
                        details TEXT,
                        ip_address TEXT,
                        user_agent TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                self.logger.info("Patient assignment database initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise

    def validate_patient_assignment(self, user_id: str, patient_id: str) -> bool:
        """Check if user is assigned to patient"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT COUNT(*) FROM patient_assignments
                    WHERE user_id = ? AND patient_id = ?
                    AND is_active = 1
                    AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                ''', (user_id, patient_id))

                result = cursor.fetchone()[0] > 0
                self.logger.debug(f"Patient assignment check: {user_id} -> {patient_id} = {result}")
                return result

        except Exception as e:
            self.logger.error(f"Patient assignment validation failed: {e}")
            return False

    def check_emergency_access(self, user_id: str, patient_id: str) -> bool:
        """Check for valid emergency access"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT COUNT(*) FROM emergency_access
                    WHERE user_id = ? AND patient_id = ?
                    AND is_active = 1
                    AND expires_at > CURRENT_TIMESTAMP
                ''', (user_id, patient_id))

                result = cursor.fetchone()[0] > 0
                self.logger.debug(f"Emergency access check: {user_id} -> {patient_id} = {result}")
                return result

        except Exception as e:
            self.logger.error(f"Emergency access check failed: {e}")
            return False

    def log_access_attempt(
            self, user_id: str, patient_id: Optional[str], action: str,
            result: str, details: Optional[str] = None, ip_address: Optional[str] = None
    ):
        """Log access attempt for audit trail"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO audit_log (user_id, patient_id, action, result, details, ip_address)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, patient_id, action, result, details, ip_address))

                self.logger.debug(f"Logged access attempt: {user_id} -> {patient_id} [{action}] = {result}")

        except Exception as e:
            self.logger.error(f"Failed to log access attempt: {e}")

    def add_patient_assignment(
            self, user_id: str, patient_id: str,
            assignment_type: str = 'primary', expires_at: Optional[str] = None
    ) -> bool:
        """Add a new patient assignment"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO patient_assignments
                    (user_id, patient_id, assignment_type, expires_at, is_active)
                    VALUES (?, ?, ?, ?, 1)
                ''', (user_id, patient_id, assignment_type, expires_at))

                self.logger.info(f"Added patient assignment: {user_id} -> {patient_id} ({assignment_type})")
                return True

        except Exception as e:
            self.logger.error(f"Failed to add patient assignment: {e}")
            return False

    def grant_emergency_access(
            self, user_id: str, patient_id: str, reason: str,
            supervisor_id: Optional[str] = None, hours: int = 24
    ) -> bool:
        """Grant emergency access for specified duration"""
        try:
            expires_at = datetime.now() + timedelta(hours=hours)

            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO emergency_access
                    (user_id, patient_id, supervisor_id, reason, expires_at, is_active)
                    VALUES (?, ?, ?, ?, ?, 1)
                ''', (user_id, patient_id, supervisor_id, reason, expires_at.isoformat()))

                self.logger.warning(
                    f"Emergency access granted: {user_id} -> {patient_id} "
                    f"(expires: {expires_at}, reason: {reason})"
                )
                return True

        except Exception as e:
            self.logger.error(f"Failed to grant emergency access: {e}")
            return False


class SessionManager:
    """Session management for authenticated healthcare users"""

    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or os.getenv('JWT_SECRET_KEY', secrets.token_hex(32))
        self.db = PatientAssignmentDB()
        self.logger = logging.getLogger(f"{__name__}.SessionManager")

    def create_session(self, user_id: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> Optional[str]:
        """Create authenticated session"""
        try:
            payload = {
                'user_id': user_id,
                'session_id': secrets.token_hex(16),
                'created_at': datetime.utcnow().isoformat(),
                'ip_address': ip_address,
                'exp': datetime.utcnow() + timedelta(hours=8)
            }

            token = jwt.encode(payload, self.secret_key, algorithm='HS256')

            # Log session creation
            self.db.log_access_attempt(
                user_id, None, "session_created", "success",
                f"IP: {ip_address}", ip_address
            )

            self.logger.info(f"Session created for user {user_id}")
            return token

        except Exception as e:
            self.logger.error(f"Failed to create session: {e}")
            return None

    def validate_session(self, token: str) -> Optional[Dict]:
        """Validate session token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            self.logger.warning("Session expired")
            return None
        except jwt.InvalidTokenError:
            self.logger.warning("Invalid session token")
            return None

    def get_session_user_id(self, token: str) -> Optional[str]:
        """Extract user ID from session token"""
        session = self.validate_session(token)
        return session.get('user_id') if session else None


class RBACConfig:
    """Configuration management for RBAC system"""

    def __init__(self):
        self.patient_assignment_enabled = os.getenv('RBAC_ENABLE_PATIENT_ASSIGNMENT', 'false').lower() == 'true'
        self.emergency_roles = [role.strip() for role in os.getenv('RBAC_EMERGENCY_ROLES', '').split(',') if role.strip()]
        self.audit_external_endpoint = os.getenv('RBAC_AUDIT_ENDPOINT')
        self.session_timeout_hours = int(os.getenv('RBAC_SESSION_TIMEOUT_HOURS', '8'))
        self.database_path = os.getenv('RBAC_DATABASE_PATH', 'healthcare.db')
        self.logger = logging.getLogger(f"{__name__}.RBACConfig")

    def is_production_ready(self) -> bool:
        """Check if RBAC is ready for production"""
        if not self.patient_assignment_enabled:
            self.logger.info("Patient assignment not enabled")
            return False

        # Check database accessibility
        try:
            db = PatientAssignmentDB(self.database_path)
            # Test database connectivity
            with sqlite3.connect(db.db_path) as conn:
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='patient_assignments'")
                has_tables = cursor.fetchone() is not None

            if has_tables:
                self.logger.info("RBAC production readiness confirmed")
                return True
            else:
                self.logger.warning("Patient assignment tables not found")
                return False

        except Exception as e:
            self.logger.error(f"RBAC production readiness check failed: {e}")
            return False
