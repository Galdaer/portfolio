# Healthcare Configuration Management Instructions

## Purpose

Comprehensive configuration management patterns for healthcare AI systems, covering YAML externalization, environment-specific configurations, HIPAA-compliant security settings, and healthcare workflow customization with secure credential management.

## Healthcare Configuration Architecture

### 1. Configuration Hierarchy and Structure

```yaml
# ✅ CORRECT: Healthcare Configuration Structure (config/healthcare_settings.yml)
healthcare_system:
  metadata:
    system_name: "Intelluxe Healthcare AI"
    version: "1.0.0"
    deployment_environment: "${ENVIRONMENT}"  # dev, staging, production
    compliance_level: "HIPAA"
    last_updated: "2025-01-15T10:00:00Z"
    
  # Medical disclaimer and compliance settings
  medical_compliance:
    medical_disclaimer: |
      This system provides healthcare administrative and research assistance only.
      It does not provide medical advice, diagnosis, or treatment recommendations.
      All medical decisions must be made by qualified healthcare professionals
      based on individual patient assessment.
    
    hipaa_compliance:
      enabled: true
      audit_retention_days: 2555  # 7 years
      phi_detection_enabled: true
      minimum_necessary_enforcement: true
      
    gdpr_compliance:
      enabled: ${GDPR_COMPLIANCE_ENABLED:false}
      data_subject_rights_enabled: true
      consent_management_enabled: true
      
  # Healthcare AI model configurations
  ai_models:
    local_llm:
      provider: "ollama"
      model_name: "${LOCAL_LLM_MODEL:llama3.1:8b-instruct-q4_K_M}"
      base_url: "${OLLAMA_BASE_URL:http://localhost:11434}"
      timeout_seconds: 300
      max_tokens: 4096
      temperature: 0.1  # Conservative for healthcare
      
    medical_reasoning:
      chain_of_thought_enabled: true
      medical_literature_integration: true
      drug_interaction_checking: true
      clinical_decision_support: false  # Administrative support only
      
  # Healthcare workflow configurations
  clinical_workflows:
    documentation:
      soap_note_template: |
        SUBJECTIVE: {chief_complaint}
        OBJECTIVE: {physical_exam_findings}
        ASSESSMENT: {clinical_impression}
        PLAN: {treatment_plan}
      
      encounter_timeout_minutes: 120
      auto_save_interval_seconds: 30
      backup_enabled: true
      
    scheduling:
      appointment_types:
        - name: "routine_checkup"
          duration_minutes: 30
          buffer_minutes: 15
        - name: "consultation"  
          duration_minutes: 60
          buffer_minutes: 15
        - name: "follow_up"
          duration_minutes: 20
          buffer_minutes: 10
          
      business_hours:
        monday: { start: "08:00", end: "17:00" }
        tuesday: { start: "08:00", end: "17:00" }
        wednesday: { start: "08:00", end: "17:00" }
        thursday: { start: "08:00", end: "17:00" }
        friday: { start: "08:00", end: "16:00" }
        saturday: { start: "09:00", end: "13:00" }
        sunday: { closed: true }
        
  # Security and authentication configurations
  security:
    authentication:
      jwt_expiration_minutes: 15  # Short-lived for healthcare
      mfa_required_roles: ["healthcare_provider", "nurse", "security_officer"]
      password_policy:
        min_length: 12
        require_uppercase: true
        require_lowercase: true
        require_numbers: true
        require_special_chars: true
        expiry_days: 90
        
    encryption:
      phi_encryption_algorithm: "AES-256-GCM"
      key_rotation_days: 365
      backup_encryption_enabled: true
      
    audit_logging:
      log_level: "INFO"
      phi_access_logging: true
      failed_login_threshold: 3
      suspicious_activity_monitoring: true
      
  # Database configurations
  databases:
    primary:
      type: "postgresql"
      host: "${DB_HOST:localhost}"
      port: ${DB_PORT:5432}
      database: "${DB_NAME:healthcare_db}"
      pool_size: 20
      max_overflow: 30
      pool_timeout: 30
      
    cache:
      type: "redis"
      host: "${REDIS_HOST:localhost}"
      port: ${REDIS_PORT:6379}
      db: ${REDIS_DB:0}
      max_connections: 100
      
  # Healthcare service integrations
  integrations:
    medical_literature:
      pubmed_enabled: true
      clinical_trials_enabled: true
      search_timeout_seconds: 30
      max_results_per_search: 100
      
    drug_databases:
      fda_orange_book: true
      drug_interaction_database: true
      formulary_checking: false
      
    hl7_fhir:
      enabled: ${HL7_FHIR_ENABLED:false}
      version: "R4"
      base_url: "${FHIR_BASE_URL:}"
      
  # Performance and monitoring
  performance:
    caching:
      medical_literature_ttl_hours: 24
      drug_interaction_ttl_hours: 168  # 1 week
      user_session_ttl_minutes: 30
      
    rate_limiting:
      api_requests_per_minute: 100
      medical_search_per_hour: 50
      documentation_requests_per_hour: 20
      emergency_bypass_enabled: true
      
    monitoring:
      health_check_interval_seconds: 30
      performance_metrics_enabled: true
      error_tracking_enabled: true
      uptime_monitoring_enabled: true
```

### 2. Environment-Specific Configuration Management

```python
# ✅ CORRECT: Healthcare Configuration Manager
from typing import Dict, Any, Optional, List
import yaml
import os
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import logging
from cryptography.fernet import Fernet
import base64

class HealthcareEnvironment(str, Enum):
    """Healthcare deployment environments"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"

@dataclass
class HealthcareConfigValidation:
    """Configuration validation result"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    missing_required_fields: List[str]

class HealthcareConfigManager:
    """Secure configuration management for healthcare systems"""
    
    def __init__(self, environment: Optional[str] = None):
        self.environment = environment or os.getenv('ENVIRONMENT', 'development')
        self.config_dir = Path("config")
        self.logger = self._setup_logger()
        self._config_cache: Dict[str, Any] = {}
        self._encryption_key = self._get_encryption_key()
        
    def load_healthcare_config(self) -> Dict[str, Any]:
        """Load healthcare configuration with environment overrides"""
        
        try:
            # Load base healthcare configuration
            base_config = self._load_yaml_config("healthcare_settings.yml")
            
            # Load environment-specific overrides
            env_config_file = f"healthcare_settings_{self.environment}.yml"
            env_overrides = self._load_yaml_config(env_config_file, required=False)
            
            # Merge configurations
            merged_config = self._merge_configurations(base_config, env_overrides)
            
            # Apply environment variable substitutions
            resolved_config = self._resolve_environment_variables(merged_config)
            
            # Validate configuration
            validation_result = self._validate_healthcare_config(resolved_config)
            if not validation_result.is_valid:
                raise HealthcareConfigError(
                    f"Configuration validation failed: {validation_result.errors}"
                )
            
            # Cache resolved configuration
            self._config_cache['healthcare'] = resolved_config
            
            self.logger.info(
                f"Healthcare configuration loaded successfully",
                extra={
                    'operation_type': 'config_load_success',
                    'environment': self.environment,
                    'config_validation_warnings': len(validation_result.warnings)
                }
            )
            
            return resolved_config
            
        except Exception as e:
            self.logger.error(
                f"Failed to load healthcare configuration",
                extra={
                    'operation_type': 'config_load_error',
                    'environment': self.environment,
                    'error': str(e)
                }
            )
            raise HealthcareConfigError(f"Configuration loading failed: {e}")
    
    def get_database_config(self, database_name: str = "primary") -> Dict[str, Any]:
        """Get database configuration with credential decryption"""
        
        healthcare_config = self._get_cached_config('healthcare')
        db_config = healthcare_config['healthcare_system']['databases'][database_name].copy()
        
        # Decrypt sensitive database credentials
        if 'username' in db_config and db_config['username'].startswith('encrypted:'):
            db_config['username'] = self._decrypt_credential(db_config['username'])
        
        if 'password' in db_config and db_config['password'].startswith('encrypted:'):
            db_config['password'] = self._decrypt_credential(db_config['password'])
        
        return db_config
    
    def get_ai_model_config(self, model_type: str = "local_llm") -> Dict[str, Any]:
        """Get AI model configuration"""
        
        healthcare_config = self._get_cached_config('healthcare')
        model_config = healthcare_config['healthcare_system']['ai_models'][model_type].copy()
        
        # Decrypt API keys if present
        if 'api_key' in model_config and model_config['api_key'].startswith('encrypted:'):
            model_config['api_key'] = self._decrypt_credential(model_config['api_key'])
        
        return model_config
    
    def get_security_config(self) -> Dict[str, Any]:
        """Get security configuration with credential handling"""
        
        healthcare_config = self._get_cached_config('healthcare')
        security_config = healthcare_config['healthcare_system']['security'].copy()
        
        # Handle JWT secret
        if 'jwt_secret' not in security_config['authentication']:
            jwt_secret = os.getenv('JWT_SECRET')
            if not jwt_secret:
                if self.environment == 'production':
                    raise HealthcareConfigError("JWT_SECRET environment variable required in production")
                else:
                    jwt_secret = 'dev-jwt-secret-change-in-production'
            
            security_config['authentication']['jwt_secret'] = jwt_secret
        
        return security_config
    
    def get_compliance_config(self) -> Dict[str, Any]:
        """Get compliance configuration"""
        
        healthcare_config = self._get_cached_config('healthcare')
        return healthcare_config['healthcare_system']['medical_compliance']
    
    def update_configuration(
        self,
        config_path: str,
        new_value: Any,
        persist: bool = False
    ) -> None:
        """Update configuration value with optional persistence"""
        
        healthcare_config = self._get_cached_config('healthcare')
        
        # Navigate to the configuration path
        config_keys = config_path.split('.')
        current_config = healthcare_config
        
        for key in config_keys[:-1]:
            if key not in current_config:
                current_config[key] = {}
            current_config = current_config[key]
        
        # Update the value
        old_value = current_config.get(config_keys[-1])
        current_config[config_keys[-1]] = new_value
        
        # Log configuration change
        self.logger.info(
            f"Configuration updated: {config_path}",
            extra={
                'operation_type': 'config_update',
                'config_path': config_path,
                'old_value': '[REDACTED]' if 'secret' in config_path.lower() or 'key' in config_path.lower() else old_value,
                'new_value': '[REDACTED]' if 'secret' in config_path.lower() or 'key' in config_path.lower() else new_value,
                'environment': self.environment,
                'persisted': persist
            }
        )
        
        # Persist to file if requested
        if persist:
            self._persist_configuration_change(config_path, new_value)
    
    def _validate_healthcare_config(self, config: Dict[str, Any]) -> HealthcareConfigValidation:
        """Validate healthcare configuration completeness and correctness"""
        
        errors = []
        warnings = []
        missing_required_fields = []
        
        # Required top-level sections
        required_sections = [
            'healthcare_system.medical_compliance',
            'healthcare_system.ai_models',
            'healthcare_system.security',
            'healthcare_system.databases'
        ]
        
        for section_path in required_sections:
            if not self._config_path_exists(config, section_path):
                missing_required_fields.append(section_path)
        
        # Validate HIPAA compliance settings
        try:
            compliance_config = config['healthcare_system']['medical_compliance']
            if not compliance_config.get('hipaa_compliance', {}).get('enabled', False):
                warnings.append("HIPAA compliance is disabled")
            
            if not compliance_config.get('medical_disclaimer'):
                errors.append("Medical disclaimer is required for healthcare systems")
                
        except KeyError as e:
            errors.append(f"Missing compliance configuration: {e}")
        
        # Validate security settings
        try:
            security_config = config['healthcare_system']['security']
            
            # Check JWT expiration (should be short for healthcare)
            jwt_expiration = security_config.get('authentication', {}).get('jwt_expiration_minutes', 60)
            if jwt_expiration > 30:
                warnings.append(f"JWT expiration ({jwt_expiration} minutes) is longer than recommended for healthcare (30 minutes)")
            
            # Check encryption settings
            encryption_config = security_config.get('encryption', {})
            if encryption_config.get('phi_encryption_algorithm') != 'AES-256-GCM':
                errors.append("PHI encryption must use AES-256-GCM for HIPAA compliance")
                
        except KeyError as e:
            errors.append(f"Missing security configuration: {e}")
        
        # Validate database configurations
        try:
            databases = config['healthcare_system']['databases']
            
            for db_name, db_config in databases.items():
                if db_config.get('type') not in ['postgresql', 'mysql', 'redis']:
                    warnings.append(f"Database {db_name} uses unsupported type: {db_config.get('type')}")
                
                # Check for connection pooling in production
                if self.environment == 'production' and 'pool_size' not in db_config:
                    warnings.append(f"Database {db_name} missing connection pool configuration for production")
                    
        except KeyError as e:
            errors.append(f"Missing database configuration: {e}")
        
        return HealthcareConfigValidation(
            is_valid=len(errors) == 0 and len(missing_required_fields) == 0,
            errors=errors,
            warnings=warnings,
            missing_required_fields=missing_required_fields
        )
    
    def _encrypt_credential(self, credential: str) -> str:
        """Encrypt sensitive credential"""
        if not self._encryption_key:
            raise HealthcareConfigError("Encryption key not available for credential encryption")
        
        fernet = Fernet(self._encryption_key)
        encrypted_bytes = fernet.encrypt(credential.encode())
        return f"encrypted:{base64.b64encode(encrypted_bytes).decode()}"
    
    def _decrypt_credential(self, encrypted_credential: str) -> str:
        """Decrypt sensitive credential"""
        if not encrypted_credential.startswith('encrypted:'):
            return encrypted_credential
        
        if not self._encryption_key:
            raise HealthcareConfigError("Encryption key not available for credential decryption")
        
        try:
            encrypted_data = base64.b64decode(encrypted_credential[10:])  # Remove 'encrypted:' prefix
            fernet = Fernet(self._encryption_key)
            decrypted_bytes = fernet.decrypt(encrypted_data)
            return decrypted_bytes.decode()
        except Exception as e:
            raise HealthcareConfigError(f"Failed to decrypt credential: {e}")
    
    def _get_encryption_key(self) -> Optional[bytes]:
        """Get encryption key for sensitive configuration data"""
        key_env = os.getenv('HEALTHCARE_CONFIG_KEY')
        if key_env:
            return key_env.encode()
        
        # Generate key for development environment
        if self.environment == 'development':
            return Fernet.generate_key()
        
        return None
    
    def _resolve_environment_variables(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve environment variable placeholders in configuration"""
        
        def resolve_value(value):
            if isinstance(value, str):
                # Handle ${VAR:default} pattern
                import re
                pattern = r'\$\{([^}]+)\}'
                
                def replace_env_var(match):
                    env_expression = match.group(1)
                    if ':' in env_expression:
                        var_name, default_value = env_expression.split(':', 1)
                        return os.getenv(var_name, default_value)
                    else:
                        return os.getenv(env_expression, match.group(0))
                
                return re.sub(pattern, replace_env_var, value)
            
            elif isinstance(value, dict):
                return {k: resolve_value(v) for k, v in value.items()}
            
            elif isinstance(value, list):
                return [resolve_value(item) for item in value]
            
            else:
                return value
        
        return resolve_value(config)
    
    def _merge_configurations(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge configuration dictionaries"""
        if not override:
            return base
        
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configurations(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _load_yaml_config(self, filename: str, required: bool = True) -> Dict[str, Any]:
        """Load YAML configuration file"""
        config_path = self.config_dir / filename
        
        if not config_path.exists():
            if required:
                raise HealthcareConfigError(f"Required configuration file not found: {config_path}")
            return {}
        
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise HealthcareConfigError(f"Invalid YAML in {filename}: {e}")
    
    def _get_cached_config(self, config_type: str) -> Dict[str, Any]:
        """Get cached configuration"""
        if config_type not in self._config_cache:
            if config_type == 'healthcare':
                self.load_healthcare_config()
            else:
                raise HealthcareConfigError(f"Unknown configuration type: {config_type}")
        
        return self._config_cache[config_type]
    
    def _config_path_exists(self, config: Dict[str, Any], path: str) -> bool:
        """Check if configuration path exists"""
        keys = path.split('.')
        current = config
        
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return False
            current = current[key]
        
        return True
    
    def _setup_logger(self) -> logging.Logger:
        """Setup configuration manager logger"""
        logger = logging.getLogger('healthcare_config')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger

class HealthcareConfigError(Exception):
    """Healthcare configuration error"""
    pass
```

### 3. Environment-Specific Configuration Files

```yaml
# ✅ CORRECT: Development Environment Override (config/healthcare_settings_development.yml)
healthcare_system:
  metadata:
    deployment_environment: "development"
    
  ai_models:
    local_llm:
      model_name: "llama3.1:8b-instruct-q4_K_M"
      timeout_seconds: 60  # Shorter timeout for dev
      temperature: 0.3  # More creative for testing
      
  security:
    authentication:
      jwt_expiration_minutes: 60  # Longer for development convenience
      mfa_required_roles: []  # Disable MFA in development
      password_policy:
        min_length: 8  # Relaxed for development
        expiry_days: 365
        
  databases:
    primary:
      host: "localhost"
      database: "healthcare_dev"
      pool_size: 5  # Smaller pool for development
      
  performance:
    rate_limiting:
      api_requests_per_minute: 1000  # Higher limits for testing
      
  integrations:
    medical_literature:
      search_timeout_seconds: 10  # Shorter timeout for dev testing
```

```yaml
# ✅ CORRECT: Production Environment Override (config/healthcare_settings_production.yml)
healthcare_system:
  metadata:
    deployment_environment: "production"
    
  ai_models:
    local_llm:
      timeout_seconds: 300
      temperature: 0.1  # Conservative for production
      
  security:
    authentication:
      jwt_expiration_minutes: 10  # Very short for production security
      mfa_required_roles: ["healthcare_provider", "nurse", "security_officer", "privacy_officer"]
      password_policy:
        min_length: 16  # Stronger passwords in production
        expiry_days: 60
        
    audit_logging:
      log_level: "WARNING"  # Less verbose logging in production
      
  databases:
    primary:
      pool_size: 50  # Larger pool for production load
      max_overflow: 100
      
  performance:
    rate_limiting:
      api_requests_per_minute: 60  # Stricter limits in production
      emergency_bypass_enabled: false  # No bypass in production
      
    monitoring:
      health_check_interval_seconds: 10  # More frequent monitoring
      
  integrations:
    medical_literature:
      search_timeout_seconds: 45  # Longer timeout for production reliability
```

### 4. Secure Credential Management

```python
# ✅ CORRECT: Healthcare Credential Management
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import getpass

class HealthcareCredentialManager:
    """Secure credential management for healthcare systems"""
    
    def __init__(self, config_manager: HealthcareConfigManager):
        self.config_manager = config_manager
        self.credentials_file = Path("config/secure/healthcare_credentials.encrypted")
        self.master_key_env = "HEALTHCARE_MASTER_KEY"
        self.logger = config_manager.logger
        
    def store_database_credentials(
        self,
        database_name: str,
        username: str,
        password: str,
        host: str,
        port: int
    ) -> None:
        """Store database credentials securely"""
        
        credentials = {
            'username': username,
            'password': password,
            'host': host,
            'port': port,
            'stored_at': datetime.utcnow().isoformat()
        }
        
        encrypted_credentials = self._encrypt_credentials(credentials)
        
        # Store in secure credentials file
        self._update_secure_store(f"database.{database_name}", encrypted_credentials)
        
        self.logger.info(
            f"Database credentials stored securely",
            extra={
                'operation_type': 'credential_storage',
                'database_name': database_name,
                'credential_type': 'database'
            }
        )
    
    def store_api_credentials(
        self,
        service_name: str,
        api_key: str,
        endpoint: str,
        additional_config: Optional[Dict[str, Any]] = None
    ) -> None:
        """Store API credentials securely"""
        
        credentials = {
            'api_key': api_key,
            'endpoint': endpoint,
            'additional_config': additional_config or {},
            'stored_at': datetime.utcnow().isoformat()
        }
        
        encrypted_credentials = self._encrypt_credentials(credentials)
        
        # Store in secure credentials file
        self._update_secure_store(f"api.{service_name}", encrypted_credentials)
        
        self.logger.info(
            f"API credentials stored securely",
            extra={
                'operation_type': 'credential_storage',
                'service_name': service_name,
                'credential_type': 'api'
            }
        )
    
    def get_database_credentials(self, database_name: str) -> Dict[str, Any]:
        """Retrieve database credentials"""
        
        encrypted_credentials = self._get_from_secure_store(f"database.{database_name}")
        if not encrypted_credentials:
            raise HealthcareConfigError(f"Database credentials not found: {database_name}")
        
        credentials = self._decrypt_credentials(encrypted_credentials)
        
        # Remove timestamp before returning
        credentials.pop('stored_at', None)
        
        return credentials
    
    def get_api_credentials(self, service_name: str) -> Dict[str, Any]:
        """Retrieve API credentials"""
        
        encrypted_credentials = self._get_from_secure_store(f"api.{service_name}")
        if not encrypted_credentials:
            raise HealthcareConfigError(f"API credentials not found: {service_name}")
        
        credentials = self._decrypt_credentials(encrypted_credentials)
        
        # Remove timestamp before returning
        credentials.pop('stored_at', None)
        
        return credentials
    
    def rotate_credentials(self, credential_path: str) -> None:
        """Rotate stored credentials"""
        
        # Get existing credentials
        encrypted_credentials = self._get_from_secure_store(credential_path)
        if not encrypted_credentials:
            raise HealthcareConfigError(f"Credentials not found for rotation: {credential_path}")
        
        old_credentials = self._decrypt_credentials(encrypted_credentials)
        
        # Generate new credentials based on type
        if credential_path.startswith('database.'):
            new_password = self._generate_secure_password()
            old_credentials['password'] = new_password
        elif credential_path.startswith('api.'):
            # API key rotation would typically involve calling the service API
            # This is a placeholder for the rotation logic
            self.logger.warning(f"API key rotation for {credential_path} requires manual intervention")
            return
        
        # Update stored credentials
        old_credentials['rotated_at'] = datetime.utcnow().isoformat()
        encrypted_credentials = self._encrypt_credentials(old_credentials)
        self._update_secure_store(credential_path, encrypted_credentials)
        
        self.logger.info(
            f"Credentials rotated successfully",
            extra={
                'operation_type': 'credential_rotation',
                'credential_path': credential_path
            }
        )
    
    def _encrypt_credentials(self, credentials: Dict[str, Any]) -> str:
        """Encrypt credentials dictionary"""
        
        master_key = self._get_master_key()
        fernet = Fernet(master_key)
        
        credentials_json = json.dumps(credentials)
        encrypted_bytes = fernet.encrypt(credentials_json.encode())
        
        return base64.b64encode(encrypted_bytes).decode()
    
    def _decrypt_credentials(self, encrypted_credentials: str) -> Dict[str, Any]:
        """Decrypt credentials dictionary"""
        
        master_key = self._get_master_key()
        fernet = Fernet(master_key)
        
        try:
            encrypted_bytes = base64.b64decode(encrypted_credentials.encode())
            decrypted_bytes = fernet.decrypt(encrypted_bytes)
            
            return json.loads(decrypted_bytes.decode())
        except Exception as e:
            raise HealthcareConfigError(f"Failed to decrypt credentials: {e}")
    
    def _get_master_key(self) -> bytes:
        """Get or generate master encryption key"""
        
        # Try to get from environment variable
        master_key_b64 = os.getenv(self.master_key_env)
        if master_key_b64:
            try:
                return base64.b64decode(master_key_b64.encode())
            except Exception:
                pass
        
        # For production, key must be provided
        if self.config_manager.environment == 'production':
            raise HealthcareConfigError(
                f"Master encryption key must be provided via {self.master_key_env} environment variable in production"
            )
        
        # Generate development key
        return Fernet.generate_key()
    
    def _update_secure_store(self, credential_path: str, encrypted_data: str) -> None:
        """Update secure credential store"""
        
        # Ensure secure directory exists
        self.credentials_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing store
        store = {}
        if self.credentials_file.exists():
            try:
                with open(self.credentials_file, 'r') as f:
                    store = json.load(f)
            except Exception:
                store = {}
        
        # Update credential
        store[credential_path] = encrypted_data
        
        # Write back to file
        with open(self.credentials_file, 'w') as f:
            json.dump(store, f, indent=2)
        
        # Set restrictive permissions
        os.chmod(self.credentials_file, 0o600)
    
    def _get_from_secure_store(self, credential_path: str) -> Optional[str]:
        """Get credential from secure store"""
        
        if not self.credentials_file.exists():
            return None
        
        try:
            with open(self.credentials_file, 'r') as f:
                store = json.load(f)
                return store.get(credential_path)
        except Exception:
            return None
    
    def _generate_secure_password(self, length: int = 32) -> str:
        """Generate secure random password"""
        import secrets
        import string
        
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
```

### 5. Configuration Testing and Validation

```python
# ✅ CORRECT: Healthcare Configuration Testing
import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, Mock

@pytest.fixture
def temp_config_dir():
    """Create temporary configuration directory for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / "config"
        config_dir.mkdir()
        yield config_dir

@pytest.fixture
def sample_healthcare_config():
    """Sample healthcare configuration for testing"""
    return {
        'healthcare_system': {
            'metadata': {
                'system_name': 'Test Healthcare System',
                'version': '1.0.0',
                'deployment_environment': 'testing'
            },
            'medical_compliance': {
                'medical_disclaimer': 'Test medical disclaimer',
                'hipaa_compliance': {
                    'enabled': True,
                    'audit_retention_days': 2555
                }
            },
            'security': {
                'authentication': {
                    'jwt_expiration_minutes': 15
                },
                'encryption': {
                    'phi_encryption_algorithm': 'AES-256-GCM'
                }
            },
            'databases': {
                'primary': {
                    'type': 'postgresql',
                    'host': 'localhost',
                    'pool_size': 10
                }
            },
            'ai_models': {
                'local_llm': {
                    'provider': 'ollama',
                    'model_name': 'test-model'
                }
            }
        }
    }

def test_healthcare_config_loading(temp_config_dir, sample_healthcare_config):
    """Test healthcare configuration loading"""
    
    # Create config file
    config_file = temp_config_dir / "healthcare_settings.yml"
    with open(config_file, 'w') as f:
        yaml.dump(sample_healthcare_config, f)
    
    # Test configuration loading
    with patch('pathlib.Path') as mock_path:
        mock_path.return_value = temp_config_dir
        
        config_manager = HealthcareConfigManager(environment='testing')
        config_manager.config_dir = temp_config_dir
        
        loaded_config = config_manager.load_healthcare_config()
        
        assert loaded_config['healthcare_system']['metadata']['system_name'] == 'Test Healthcare System'
        assert loaded_config['healthcare_system']['medical_compliance']['hipaa_compliance']['enabled'] is True

def test_environment_variable_resolution(temp_config_dir):
    """Test environment variable resolution in configuration"""
    
    config_with_env_vars = {
        'healthcare_system': {
            'databases': {
                'primary': {
                    'host': '${DB_HOST:localhost}',
                    'port': '${DB_PORT:5432}',
                    'database': '${DB_NAME:test_db}'
                }
            }
        }
    }
    
    # Create config file
    config_file = temp_config_dir / "healthcare_settings.yml"
    with open(config_file, 'w') as f:
        yaml.dump(config_with_env_vars, f)
    
    # Test with environment variables set
    with patch.dict(os.environ, {'DB_HOST': 'production-db', 'DB_PORT': '5433'}):
        config_manager = HealthcareConfigManager(environment='testing')
        config_manager.config_dir = temp_config_dir
        
        resolved_config = config_manager._resolve_environment_variables(config_with_env_vars)
        
        db_config = resolved_config['healthcare_system']['databases']['primary']
        assert db_config['host'] == 'production-db'  # From environment
        assert db_config['port'] == '5433'  # From environment
        assert db_config['database'] == 'test_db'  # Default value

def test_configuration_validation(temp_config_dir):
    """Test healthcare configuration validation"""
    
    # Test invalid configuration (missing required fields)
    invalid_config = {
        'healthcare_system': {
            'metadata': {
                'system_name': 'Test System'
            }
            # Missing required sections
        }
    }
    
    config_manager = HealthcareConfigManager(environment='testing')
    config_manager.config_dir = temp_config_dir
    
    validation_result = config_manager._validate_healthcare_config(invalid_config)
    
    assert not validation_result.is_valid
    assert len(validation_result.missing_required_fields) > 0
    assert 'healthcare_system.medical_compliance' in validation_result.missing_required_fields

def test_credential_encryption_decryption():
    """Test credential encryption and decryption"""
    
    config_manager = HealthcareConfigManager(environment='development')
    credential_manager = HealthcareCredentialManager(config_manager)
    
    # Test credentials
    test_credentials = {
        'username': 'test_user',
        'password': 'test_password_123!',
        'host': 'localhost',
        'port': 5432
    }
    
    # Encrypt credentials
    encrypted = credential_manager._encrypt_credentials(test_credentials)
    assert encrypted.startswith('encrypted:') is False  # Internal format
    assert encrypted != json.dumps(test_credentials)  # Should be encrypted
    
    # Decrypt credentials
    decrypted = credential_manager._decrypt_credentials(encrypted)
    
    assert decrypted['username'] == test_credentials['username']
    assert decrypted['password'] == test_credentials['password']
    assert decrypted['host'] == test_credentials['host']
    assert decrypted['port'] == test_credentials['port']

def test_configuration_merging(temp_config_dir, sample_healthcare_config):
    """Test configuration merging with environment overrides"""
    
    # Create base config
    config_file = temp_config_dir / "healthcare_settings.yml"
    with open(config_file, 'w') as f:
        yaml.dump(sample_healthcare_config, f)
    
    # Create environment override
    override_config = {
        'healthcare_system': {
            'security': {
                'authentication': {
                    'jwt_expiration_minutes': 30  # Override base value
                }
            },
            'databases': {
                'primary': {
                    'pool_size': 20  # Override base value
                }
            }
        }
    }
    
    env_config_file = temp_config_dir / "healthcare_settings_testing.yml"
    with open(env_config_file, 'w') as f:
        yaml.dump(override_config, f)
    
    config_manager = HealthcareConfigManager(environment='testing')
    config_manager.config_dir = temp_config_dir
    
    loaded_config = config_manager.load_healthcare_config()
    
    # Check that overrides were applied
    assert loaded_config['healthcare_system']['security']['authentication']['jwt_expiration_minutes'] == 30
    assert loaded_config['healthcare_system']['databases']['primary']['pool_size'] == 20
    
    # Check that non-overridden values remain
    assert loaded_config['healthcare_system']['metadata']['system_name'] == 'Test Healthcare System'
```

## Medical Disclaimer

**MEDICAL DISCLAIMER: This configuration management instruction set provides patterns for healthcare administrative system configuration only. It assists developers in creating secure, HIPAA-compliant configuration management for healthcare AI systems that support medical literature research, clinical documentation assistance, and healthcare workflow optimization. It does not provide medical advice, diagnosis, or treatment recommendations. All configuration settings must be reviewed and validated by qualified healthcare compliance professionals and system administrators based on specific organizational requirements and regulatory standards.**
