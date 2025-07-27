# Healthcare Authentication Integration Guide

## Overview

Intelluxe AI integrates seamlessly with existing clinic authentication systems while providing secure, user-specific configuration management. No additional passwords or complex setup required.

## Architecture

```
Clinic Workstation Login (AD/LDAP/SAML)
    ↓
System User Authentication
    ↓
Intelluxe healthcare_auth.py Detection
    ↓
Automatic User Config Decryption
    ↓
Personalized AI Experience
```

## Supported Authentication Systems

### Active Directory (Most Common)
```bash
# .env configuration
AUTH_MODE=active_directory
EXISTING_AUTH_DOMAIN=yourclinic.local
USER_ENV_FILES=true
EMERGENCY_ACCESS_ENABLED=true
```

### LDAP Integration
```bash
# .env configuration  
AUTH_MODE=ldap
EXISTING_LDAP_SERVER=ldap://yourclinic.local:389
EXISTING_LDAP_BASE_DN=dc=yourclinic,dc=local
USER_ENV_FILES=true
```

### SAML SSO Integration
```bash
# .env configuration
AUTH_MODE=saml_sso
EXISTING_SAML_METADATA_URL=https://sso.yourclinic.com/metadata
USER_ENV_FILES=true
```

### Standalone Mode
```bash
# .env configuration
AUTH_MODE=standalone
STANDALONE_AUTH_ENABLED=true
USER_ENV_FILES=true
```

## User Configuration Management

### Automatic User Config Creation
When a user first launches Intelluxe, `healthcare_auth.py` automatically:

1. **Detects system user** (`getpass.getuser()`)
2. **Creates encrypted config directory** (`/home/{username}/.intelluxe/`)
3. **Generates default user configuration** based on system role detection
4. **Encrypts config** using session-derived key
5. **Loads personalized AI settings**

### User Configuration Examples

**Healthcare Provider:**
```bash
# /home/dr_martinez/.intelluxe/user.env.encrypted (decrypted view)
INTELLUXE_ROLE=healthcare_provider
PREFERRED_AI_MODEL=llama3.1:medical
MEDICAL_SPECIALTY=cardiology
PATIENT_ACCESS_LEVEL=assigned_patients
CLINICAL_DECISION_SUPPORT=enabled
AUTO_TRANSCRIPTION=true
RESEARCH_ACCESS=pubmed_clinical_trials
WORKFLOW_OPTIMIZATION=clinical_focused
```

**Nurse:**
```bash
# /home/nurse_johnson/.intelluxe/user.env.encrypted (decrypted view)
INTELLUXE_ROLE=nursing_staff
PREFERRED_AI_MODEL=llama3.1:nursing
PATIENT_ACCESS_LEVEL=care_team_patients
MEDICATION_ALERTS=strict
VITAL_SIGNS_MONITORING=enabled
PATIENT_EDUCATION_TOOLS=enabled
```

**Administrative Staff:**
```bash
# /home/admin_chen/.intelluxe/user.env.encrypted (decrypted view)
INTELLUXE_ROLE=administrative_staff
PREFERRED_AI_MODEL=llama3.1:admin
PATIENT_ACCESS_LEVEL=scheduling_billing_only
INSURANCE_VERIFICATION=enabled
BILLING_ASSISTANCE=enabled
SCHEDULING_OPTIMIZATION=enabled
```

## Security Features

### Session-Based Encryption
- **User configs encrypted** with keys derived from system login session
- **Automatic decryption** when user is authenticated to workstation
- **Automatic lock** when user logs out or session expires
- **No password storage** - leverages existing clinic security

### Role-Based Access Control
- **Automatic role detection** based on system groups/permissions
- **Healthcare-appropriate permissions** (providers vs. staff vs. admin)
- **Patient access controls** integrated with clinic assignment systems
- **Audit logging** for all authentication and access events

### Emergency Access
- **Fallback authentication** during system outages
- **Emergency provider access** for critical patient care
- **Audit trail maintenance** even during emergency access
- **Automatic restoration** when primary auth systems recover

## Implementation Steps

### 1. Choose Authentication Mode
Determine your clinic's authentication system and configure accordingly.

### 2. Deploy Intelluxe with Auth Integration
```bash
# Configure authentication in .env
vim .env  # Set AUTH_MODE and related settings

# Deploy with authentication enabled
./bootstrap.sh
```

### 3. Test User Authentication
```bash
# Test authentication integration
python -c "
from src.security.healthcare_auth import HealthcareAuthManager
auth = HealthcareAuthManager()
config = auth.load_user_environment()
print(f'User: {auth.current_user}')
print(f'Role: {config.get(\"INTELLUXE_ROLE\")}')
print('✅ Authentication integration working')
"
```

### 4. Verify User Configs
Check that user-specific configurations are created and encrypted:
```bash
# Check user config directories
ls -la /home/*/\.intelluxe/
# Should show encrypted user.env.encrypted files

# Verify encryption is working
file /home/dr_smith/.intelluxe/user.env.encrypted
# Should show: data (encrypted)
```

## Troubleshooting

### Common Issues
- **Config not decrypting**: Check user session and system authentication
- **Role not detected**: Verify system groups and permissions
- **Emergency access needed**: Use `EMERGENCY_ACCESS_ENABLED=true`
- **Integration failing**: Check domain/LDAP/SAML connectivity

### Debug Commands
```bash
# Test current user detection
python -c "import getpass; print(f'Current user: {getpass.getuser()}')"

# Test authentication mode
python -c "
import os
from src.security.healthcare_auth import AuthenticationMode
mode = AuthenticationMode(os.getenv('AUTH_MODE', 'standalone'))
print(f'Auth mode: {mode.value}')
"

# Verify user config path
python -c "
from src.security.healthcare_auth import HealthcareAuthManager
auth = HealthcareAuthManager()
print(f'User config path: {auth.user_config_path}')
"
```

This integration provides seamless authentication while maintaining the security and personalization that healthcare environments require.