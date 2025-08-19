# AI Instructions for Configuration Management

## Purpose

Specialized guidance for developing and maintaining healthcare configuration management, security settings, RBAC policies, and environment detection systems.

## Configuration Management Standards

### Database-First Configuration Requirements

**CRITICAL**: All configuration management must use database-backed settings with secure fallbacks only for initial bootstrap.

**✅ CORRECT: Database-First Configuration Pattern**
```python
# config/database_config_manager.py
from typing import Dict, Any, Optional
from core.dependencies import get_database_connection
from core.infrastructure.healthcare_logger import get_healthcare_logger
import json
import os

class HealthcareConfigManager:
    """Database-first configuration management"""
    
    def __init__(self):
        self.logger = get_healthcare_logger('config_manager')
        self.db_connection = None
        self._config_cache = {}
    
    async def initialize(self):
        """Initialize configuration system with database requirement"""
        try:
            self.db_connection = await get_database_connection()
            await self._create_config_tables()
            await self._load_configuration_cache()
            
            self.logger.info("Healthcare configuration system initialized")
            
        except DatabaseConnectionError as e:
            self.logger.critical(
                "Configuration system requires database connectivity",
                extra={
                    'error': str(e),
                    'remedy': 'Ensure PostgreSQL is running for configuration management'
                }
            )
            raise ConfigurationError(
                "Configuration management cannot start without database. "
                "Please run 'make deps' and ensure PostgreSQL is accessible."
            )
    
    async def get_healthcare_config(
        self, 
        config_key: str, 
        default: Any = None,
        require_audit: bool = True
    ) -> Any:
        """Get configuration with audit logging"""
        
        try:
            # Try database first
            config_value = await self._get_from_database(config_key)
            
            if require_audit:
                self.logger.info(
                    f"Configuration accessed: {config_key}",
                    extra={
                        'config_key': config_key,
                        'has_value': config_value is not None,
                        'user_role': get_current_user_role()
                    }
                )
            
            return config_value if config_value is not None else default
            
        except DatabaseError:
            # Only fallback to environment for non-PHI config during bootstrap
            if self._is_bootstrap_config(config_key):
                env_value = os.getenv(config_key, default)
                self.logger.warning(
                    f"Using environment fallback for bootstrap config: {config_key}"
                )
                return env_value
            else:
                self.logger.error(f"Database required for healthcare config: {config_key}")
                raise ConfigurationError(
                    f"Healthcare configuration '{config_key}' requires database access"
                )
    
    def _is_bootstrap_config(self, config_key: str) -> bool:
        """Check if config can use environment fallback during bootstrap"""
        bootstrap_allowed = [
            'DATABASE_URL',
            'REDIS_URL', 
            'LOG_LEVEL',
            'ENVIRONMENT_TYPE'
        ]
        return config_key in bootstrap_allowed

    async def set_healthcare_config(
        self, 
        config_key: str, 
        config_value: Any,
        encrypted: bool = False
    ) -> bool:
        """Set configuration with encryption and audit trail"""
        
        # PHI detection for configuration values
        if await self._contains_phi(str(config_value)):
            self.logger.critical(
                f"PHI detected in configuration value for key: {config_key}"
            )
            raise PHIConfigurationError("Configuration values cannot contain PHI")
        
        try:
            await self._store_in_database(config_key, config_value, encrypted)
            
            # Audit log configuration change
            self.logger.info(
                f"Configuration updated: {config_key}",
                extra={
                    'config_key': config_key,
                    'encrypted': encrypted,
                    'updated_by': get_current_user_id(),
                    'timestamp': datetime.now()
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update configuration {config_key}: {e}")
            raise ConfigurationError(f"Configuration update failed: {e}")
```

### Healthcare Security Configuration

**Enhanced security settings management**:

**✅ CORRECT: Security-First Configuration**
```python
# config/healthcare_security_config.py
class HealthcareSecurityConfig:
    """Healthcare-specific security configuration management"""
    
    def __init__(self):
        self.config_manager = HealthcareConfigManager()
        self.phi_monitor = PHIMonitor()
    
    async def get_encryption_config(self) -> Dict[str, Any]:
        """Get encryption configuration for healthcare data"""
        
        encryption_config = {
            'phi_encryption_algorithm': await self.config_manager.get_healthcare_config(
                'PHI_ENCRYPTION_ALGORITHM', 
                default='AES-256-GCM'
            ),
            'key_derivation_function': await self.config_manager.get_healthcare_config(
                'KEY_DERIVATION_FUNCTION',
                default='PBKDF2-SHA256'
            ),
            'encryption_key_rotation_days': await self.config_manager.get_healthcare_config(
                'ENCRYPTION_KEY_ROTATION_DAYS',
                default=90
            ),
            'database_encryption_at_rest': await self.config_manager.get_healthcare_config(
                'DATABASE_ENCRYPTION_AT_REST',
                default=True
            )
        }
        
        return encryption_config
    
    async def get_audit_config(self) -> Dict[str, Any]:
        """Get audit logging configuration"""
        
        audit_config = {
            'audit_all_phi_access': await self.config_manager.get_healthcare_config(
                'AUDIT_ALL_PHI_ACCESS',
                default=True
            ),
            'audit_retention_years': await self.config_manager.get_healthcare_config(
                'AUDIT_RETENTION_YEARS', 
                default=7  # HIPAA requirement
            ),
            'audit_log_encryption': await self.config_manager.get_healthcare_config(
                'AUDIT_LOG_ENCRYPTION',
                default=True
            ),
            'failed_login_lockout_attempts': await self.config_manager.get_healthcare_config(
                'FAILED_LOGIN_LOCKOUT_ATTEMPTS',
                default=3
            )
        }
        
        return audit_config

    async def get_offline_config(self) -> Dict[str, Any]:
        """Get offline capability configuration"""
        
        offline_config = {
            'mcp_offline_mode_enabled': await self.config_manager.get_healthcare_config(
                'MCP_OFFLINE_MODE_ENABLED',
                default=True
            ),
            'local_mirror_path': await self.config_manager.get_healthcare_config(
                'LOCAL_MIRROR_PATH',
                default='/opt/intelluxe/mcp-mirrors'
            ),
            'mirror_update_interval_hours': await self.config_manager.get_healthcare_config(
                'MIRROR_UPDATE_INTERVAL_HOURS',
                default=24
            ),
            'offline_patient_data_cache_hours': await self.config_manager.get_healthcare_config(
                'OFFLINE_PATIENT_DATA_CACHE_HOURS',
                default=168  # 1 week
            )
        }
        
        return offline_config
```

### RBAC Configuration Management

**Database-backed role and permission management**:

**✅ CORRECT: Healthcare RBAC Configuration**
```python
# config/rbac_config.py
class HealthcareRBACConfig:
    """Healthcare Role-Based Access Control configuration"""
    
    HEALTHCARE_ROLES = {
        'healthcare_admin': {
            'permissions': ['*'],
            'description': 'Full healthcare system administration'
        },
        'physician': {
            'permissions': [
                'patient.read', 'patient.write', 'patient.diagnosis',
                'medication.prescribe', 'appointment.schedule'
            ],
            'description': 'Licensed physician with full patient care access'
        },
        'nurse': {
            'permissions': [
                'patient.read', 'patient.update', 'medication.administer',
                'vitals.record', 'appointment.view'
            ],
            'description': 'Nursing staff with patient care responsibilities'
        },
        'medical_assistant': {
            'permissions': [
                'patient.read_limited', 'appointment.schedule', 'vitals.record',
                'insurance.verify'
            ],
            'description': 'Medical assistant with administrative duties'
        },
        'billing_specialist': {
            'permissions': [
                'patient.read_billing', 'insurance.process', 'billing.generate',
                'claims.submit'
            ],
            'description': 'Billing and insurance processing specialist'
        },
        'data_analyst': {
            'permissions': [
                'analytics.read', 'reports.generate', 'synthetic_data.access'
            ],
            'description': 'Healthcare data analysis (synthetic data only)'
        }
    }
    
    async def validate_healthcare_access(
        self, 
        user_role: str, 
        requested_permission: str
    ) -> bool:
        """Validate healthcare access with database-backed permissions"""
        
        # Get role permissions from database
        role_config = await self.config_manager.get_healthcare_config(
            f'RBAC_ROLE_{user_role.upper()}_PERMISSIONS'
        )
        
        if not role_config:
            # Fallback to default role definitions during bootstrap
            role_config = self.HEALTHCARE_ROLES.get(user_role, {}).get('permissions', [])
        
        # Check permissions
        if '*' in role_config:
            return True
        
        if requested_permission in role_config:
            return True
        
        # Check wildcard permissions
        permission_parts = requested_permission.split('.')
        for i in range(len(permission_parts)):
            wildcard_perm = '.'.join(permission_parts[:i+1]) + '.*'
            if wildcard_perm in role_config:
                return True
        
        return False
```

## Configuration Testing Requirements

**Database-first configuration testing**:

**✅ CORRECT: Configuration Testing Pattern**
```python
# tests/config/test_healthcare_config.py
import pytest
from config.healthcare_config_manager import HealthcareConfigManager
from tests.database_test_utils import get_test_database

class TestHealthcareConfiguration:
    """Test configuration management with database requirement"""
    
    @pytest.fixture
    async def config_manager(self):
        """Create config manager with test database"""
        test_db = await get_test_database()
        config_mgr = HealthcareConfigManager()
        config_mgr.db_connection = test_db
        await config_mgr.initialize()
        return config_mgr
    
    @pytest.mark.asyncio
    async def test_database_required_for_config(self):
        """Test that configuration requires database"""
        config_mgr = HealthcareConfigManager()
        
        with pytest.raises(ConfigurationError, match="database"):
            await config_mgr.initialize()
    
    @pytest.mark.asyncio
    async def test_phi_detection_in_config_values(self, config_manager):
        """Test PHI detection in configuration values"""
        
        with pytest.raises(PHIConfigurationError):
            await config_manager.set_healthcare_config(
                'test_config',
                'Patient SSN: 123-45-6789'  # PHI should be detected
            )
```

## Privacy Excellence for Configuration

**All configuration management** must exceed HIPAA requirements:

- **Database-first storage** with encrypted sensitive configurations
- **Comprehensive audit logging** for all configuration access
- **PHI detection** in configuration values
- **Local-only processing** - no external configuration services
- **Role-based access controls** for configuration management

---

**Configuration Standards**: Database-first, HIPAA-compliant, privacy-first configuration management with comprehensive audit and security controls.
