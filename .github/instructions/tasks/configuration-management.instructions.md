# Healthcare Configuration Management Instructions

## Purpose

YAML externalization and environment-specific configurations for healthcare AI systems with secure credential management.

## Healthcare Configuration Architecture

### 1. Configuration Hierarchy and Structure

```yaml
# ✅ CORRECT: Healthcare Configuration Structure (config/healthcare_settings.yml)
healthcare_system:
  metadata:
    system_name: "Healthcare AI"
    compliance_level: "HIPAA"
    
  medical_compliance:
    medical_disclaimer: "Administrative support only. No medical advice."
    hipaa_compliance:
      enabled: true
      audit_retention_days: 2555
      phi_detection_enabled: true
      
  ai_models:
    local_llm:
      provider: "ollama"
      model_name: "${LOCAL_LLM_MODEL:llama3.1:8b}"
      base_url: "${OLLAMA_BASE_URL:http://localhost:11434}"
      temperature: 0.1  # Conservative for healthcare
```

### 2. Environment-Specific Configuration Management

```python
# ✅ CORRECT: Healthcare Configuration Manager
from typing import Dict, Any, Optional
import yaml
import os
from pathlib import Path

class HealthcareEnvironment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"  
    PRODUCTION = "production"

class HealthcareConfigManager:
    def __init__(self, environment: Optional[HealthcareEnvironment] = None):
        # Load base config + environment overrides
        # Validate required healthcare settings
        pass
    
    def load_config(self) -> Dict[str, Any]:
        # Load YAML files with environment variable substitution
        # Validate medical compliance requirements
        pass
    
    def get_database_config(self) -> Dict[str, Any]:
        # Return database settings with credential protection
        pass
```

### 3. Environment-Specific Configuration Files

```yaml
# ✅ CORRECT: Development Override (config/healthcare_settings_development.yml)
healthcare_system:
  ai_models:
    local_llm:
      model_name: "llama3.1:8b-instruct-q4_K_M"
  database:
    use_synthetic_data: true

# ✅ CORRECT: Production Override (config/healthcare_settings_production.yml)
healthcare_system:
  medical_compliance:
    hipaa_compliance:
      audit_retention_days: 2555
  database:
    use_synthetic_data: false
    backup_enabled: true
```

### 4. Secure Credential Management

```python
# ✅ CORRECT: Healthcare Credential Management
import os
from pathlib import Path
from cryptography.fernet import Fernet

class HealthcareCredentialManager:
    def __init__(self):
        # Initialize encryption for healthcare credentials
        pass
    
    def encrypt_credential(self, credential: str) -> str:
        # Encrypt sensitive healthcare credentials
        pass
    
    def get_database_password(self) -> str:
        # Retrieve encrypted database credentials
        pass
```

## Implementation Guidelines

### Configuration Best Practices

- **Environment Separation**: Different configs for dev/staging/production
- **Credential Security**: Encrypt all database passwords and API keys
- **YAML Externalization**: Move all hardcoded values to YAML configuration
- **Environment Variables**: Use ${VAR} syntax for environment-specific values
- **Validation**: Validate all healthcare configuration on startup
- **Audit Compliance**: Log all configuration changes for HIPAA audit trail

---
