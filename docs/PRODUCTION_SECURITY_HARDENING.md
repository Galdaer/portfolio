# Production Security Hardening Guide

**Document Version**: 1.1.0  
**Target Audience**: System Administrators, DevOps Engineers  
**Phase**: Pre-Production Hardening (Phase 3)  
**Prerequisites**: Phase 0 Security Foundation Complete  
**Last Updated**: December 2024

## Overview

This document outlines security hardening steps required when transitioning the Intelluxe AI Healthcare System from development to production deployment. Building on the Phase 0 security foundation, this guide details how to implement enterprise-grade security for healthcare production environments.

⚠️ **Healthcare Compliance Notice**: All changes must maintain HIPAA compliance and ensure PHI/PII protection remains on-premise.

## 🔧 Development vs Production: Security Evolution

### Phase 0 Security Foundation (Current)
- **Multi-layer encryption** with AES-256-GCM
- **Role-based access control** with healthcare-specific roles
- **PHI detection and masking** with batch processing
- **JWT authentication** with production validation
- **Comprehensive audit logging** for compliance

### Production Security Hardening (Phase 3+)
- **Hardened for clinical deployment** with zero-trust architecture
- **Minimal attack surface** with container security
- **File copying instead of symlinks** for security isolation
- **Restricted user permissions** with dedicated service accounts
- **Network segmentation** with healthcare VLAN isolation

---

## 🛡️ 1. Enhanced File Ownership & Permissions Hardening

### Current Development State (Phase 0)
```bash
# Development permissions with security foundation
CFG_UID=1000    # justin (family member)
CFG_GID=1001    # intelluxe (group for family collaboration)

# File permissions with security awareness
Scripts: 755 (family editable with security validation)
Configs: 660/664 (group writable with encryption)
Logs: 664 (group readable with audit compliance)
Security Keys: 600 (owner only with validation)
```

### Production Hardening Steps

#### 1.1 Create Dedicated Service User with Security Context
```bash
# Create dedicated intelluxe service user (no shell, no home)
sudo useradd -r -s /bin/false -d /opt/intelluxe -M intelluxe-service

# Create dedicated group for production with security context
sudo groupadd --gid 2001 intelluxe-prod

# Create security-specific group for sensitive operations
sudo groupadd --gid 2002 intelluxe-security

# Update CFG_UID/CFG_GID in all scripts with security validation
CFG_UID=2000    # intelluxe-service
CFG_GID=2001    # intelluxe-prod
SECURITY_GID=2002  # intelluxe-security
```

#### 1.2 Security-Aware File Permissions
```bash
# Production permission model with security hardening
Scripts: 750 (owner execute only, group read)
Configs: 640 (owner read/write, group read only)
Logs: 640 (owner read/write, group read only)
Data directories: 700 (owner only)
Security keys: 600 (owner only, no group access)
PHI storage: 600 (owner only with encryption)
Audit logs: 640 (owner write, security group read)
```

#### 1.3 Enhanced Implementation Script
```bash
#!/bin/bash
# production-permission-hardening.sh - Enhanced with security validation

echo "🔒 Applying production security hardening with Phase 0 foundation validation..."

# Validate Phase 0 security foundation first
if ! python3 -c "
from src.security.encryption_manager import EncryptionManager
from src.healthcare_mcp.phi_detection import PHIDetector
from src.security.rbac_foundation import RBACFoundation

# Validate all security systems before hardening
EncryptionManager().validate_production_readiness()
PHIDetector().validate_system()
RBACFoundation().validate_production_readiness()
print('✅ Phase 0 security foundation validated')
"; then
    echo "❌ Phase 0 security validation failed - cannot proceed with hardening"
    exit 1
fi

# Update all scripts with production UID/GID and security context
find scripts/ -name "*.sh" -exec sed -i 's/DEFAULT_UID=1000/DEFAULT_UID=2000/g' {} \;
find scripts/ -name "*.sh" -exec sed -i 's/DEFAULT_GID=1001/DEFAULT_GID=2001/g' {} \;

# Apply production permissions with security hardening
chmod 750 scripts/*.sh scripts/*.py
chmod 640 systemd/*.service systemd/*.timer
find stack/ -name "*.conf" -exec chmod 640 {} \;
find stack/ -name "*.log" -exec chmod 640 {} \;

# Enhanced security for sensitive directories
chmod 700 stack/data/ stack/backups/
chmod 600 stack/data/phi/ stack/security/ 2>/dev/null || true
chmod 640 stack/logs/audit/ 2>/dev/null || true

# Set ownership with security context
chown -R intelluxe-service:intelluxe-prod /opt/intelluxe/
chown -R intelluxe-service:intelluxe-security /opt/intelluxe/stack/security/ 2>/dev/null || true
chown -R intelluxe-service:intelluxe-security /opt/intelluxe/stack/logs/audit/ 2>/dev/null || true

echo "✅ Production security hardening applied with Phase 0 foundation"
```

---

## 🗂️ 2. Enhanced Directory Structure Hardening

### Current Development State (Phase 0)
```bash
# Development: Symlinks with security validation
/opt/intelluxe/scripts -> /home/intelluxe/scripts/
/opt/intelluxe/stack -> /home/intelluxe/stack/
# Security systems validated at runtime
```

### Production Hardening Steps

#### 2.1 Security-Aware File Copy Replacement
```bash
# production-structure-hardening.sh - Enhanced with security validation

echo "🗂️ Replacing symlinks with secure file copies..."

# Validate security systems before structural changes
validate_security_systems() {
    python3 -c "
from src.security.encryption_manager import EncryptionManager
from src.healthcare_mcp.phi_detection import PHIDetector

# Validate critical security components
em = EncryptionManager()
em.validate_keys()

pd = PHIDetector()
pd.validate_system()

print('Security systems validated for structural hardening')
"
}

if ! validate_security_systems; then
    echo "❌ Security validation failed - cannot proceed with structural hardening"
    exit 1
fi

# Remove development symlinks
sudo rm -f /opt/intelluxe/scripts /opt/intelluxe/stack /opt/intelluxe/agents
sudo rm -f /opt/intelluxe/config /opt/intelluxe/core /opt/intelluxe/data
sudo rm -f /opt/intelluxe/infrastructure /opt/intelluxe/mcps
sudo rm -f /opt/intelluxe/notebooks /opt/intelluxe/services /opt/intelluxe/systemd

# Copy files with security preservation
sudo cp -r /home/intelluxe/scripts/ /opt/intelluxe/scripts/
sudo cp -r /home/intelluxe/stack/ /opt/intelluxe/stack/
sudo cp -r /home/intelluxe/src/ /opt/intelluxe/src/  # Include Phase 0 security code
sudo cp -r /home/intelluxe/config/ /opt/intelluxe/config/
sudo cp -r /home/intelluxe/core/ /opt/intelluxe/core/
sudo cp -r /home/intelluxe/data/ /opt/intelluxe/data/

# Create security-specific directories
sudo mkdir -p /opt/intelluxe/stack/security/keys
sudo mkdir -p /opt/intelluxe/stack/security/audit
sudo mkdir -p /opt/intelluxe/stack/data/phi

# Set production ownership with security context
sudo chown -R intelluxe-service:intelluxe-prod /opt/intelluxe/
sudo chown -R intelluxe-service:intelluxe-security /opt/intelluxe/stack/security/
sudo chown -R intelluxe-service:intelluxe-security /opt/intelluxe/src/security/

echo "✅ Secure file structure implemented"
```

#### 2.2 Security-Enhanced Makefile for Production
```makefile
# Update PROD_DIRS handling with security validation
install-production:
    @echo "🔒 Installing Intelluxe AI for PRODUCTION deployment with security validation"
    @echo "   - Validating Phase 0 security foundation"
    @python3 -c "from src.security.encryption_manager import EncryptionManager; EncryptionManager().validate_production_readiness()"
    @echo "   - Creating production directories with secure file copies (not symlinks)"
    @for dir in $(PROD_DIRS); do \
        if [ -d "$(PWD)/$$dir" ]; then \
            echo "     Copying $$dir -> /opt/intelluxe/$$dir"; \
            sudo cp -r $(PWD)/$$dir /opt/intelluxe/; \
        fi; \
    done
    @echo "   - Setting production permissions with security hardening"
    @sudo chown -R $(PROD_UID):$(PROD_GID) /opt/intelluxe
    @sudo chmod 750 /opt/intelluxe/scripts/*.sh
    @sudo chmod 640 /opt/intelluxe/systemd/*.service
    @sudo chmod 600 /opt/intelluxe/stack/security/keys/* 2>/dev/null || true
    @echo "   - Validating security systems post-installation"
    @sudo -u intelluxe-service python3 -c "from src.security.encryption_manager import EncryptionManager; EncryptionManager().validate_keys()"
```

---

## 🛡️ 3. Enhanced Systemd Service Hardening

### Current Development State (Phase 0)
```ini
# Development systemd services with security foundation
[Service]
Type=oneshot
ExecStart=/opt/intelluxe/scripts/auto-upgrade.sh
Environment=HOME=/root
Environment=HEALTHCARE_MODE=development
# Security validation enabled but permissive
```

### Production Hardening Steps

#### 3.1 Security-Enhanced Systemd Configuration
```ini
# Production systemd service template with security hardening
[Service]
Type=oneshot
ExecStart=/opt/intelluxe/scripts/auto-upgrade.sh
User=intelluxe-service
Group=intelluxe-prod
SupplementaryGroups=intelluxe-security

# Healthcare environment with security validation
Environment=HEALTHCARE_MODE=production
Environment=SECURITY_VALIDATION=true
Environment=PHI_PROTECTION_VERIFY=true
Environment=ENCRYPTION_VALIDATION=true

# Full security hardening
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictRealtime=yes
RestrictSUIDSGID=yes
PrivateTmp=yes
PrivateDevices=yes
PrivateNetwork=false  # Healthcare services need network access
MemoryDenyWriteExecute=yes
SystemCallFilter=@system-service
SystemCallErrorNumber=EPERM

# Healthcare-specific paths with security context
ReadWritePaths=/opt/intelluxe/logs /opt/intelluxe/stack/data
ReadOnlyPaths=/opt/intelluxe/scripts /opt/intelluxe/config /opt/intelluxe/src
InaccessiblePaths=/home /boot /root

# Security-specific access
ReadWritePaths=/opt/intelluxe/stack/security/audit
ReadOnlyPaths=/opt/intelluxe/stack/security/keys

# Enhanced capability restrictions
CapabilityBoundingSet=CAP_NET_BIND_SERVICE CAP_SETUID CAP_SETGID
AmbientCapabilities=

# Resource limits for healthcare stability with security overhead
MemoryMax=1G
TasksMax=100
TimeoutStartSec=300
TimeoutStopSec=60

# Enhanced logging with security context
SyslogIdentifier=intelluxe-healthcare-secure
StandardOutput=journal
StandardError=journal
```

#### 3.2 Security-Enhanced Service Hardening Script
```bash
#!/bin/bash
# production-systemd-hardening.sh - Enhanced with security validation

echo "🛡️ Applying systemd security hardening with Phase 0 foundation..."

# Validate security systems before hardening services
if ! python3 -c "
from src.security.encryption_manager import EncryptionManager
from src.healthcare_mcp.phi_detection import PHIDetector
from src.security.rbac_foundation import RBACFoundation

# Comprehensive security validation
EncryptionManager().validate_production_readiness()
PHIDetector().validate_system()
RBACFoundation().validate_production_readiness()
print('✅ Security systems validated for systemd hardening')
"; then
    echo "❌ Security validation failed - cannot proceed with systemd hardening"
    exit 1
fi

# Apply production security to all services
for service in /opt/intelluxe/systemd/*.service; do
    service_name=$(basename "$service")
    echo "Hardening $service_name with security enhancements..."
    
    # Add enhanced security sections to each service
    cat >> "$service" << EOF

# Production Security Hardening with Phase 0 Foundation
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
PrivateDevices=yes
MemoryDenyWriteExecute=yes

# Healthcare-specific security
ReadWritePaths=/opt/intelluxe/logs /opt/intelluxe/stack/security/audit
ReadOnlyPaths=/opt/intelluxe/scripts /opt/intelluxe/config /opt/intelluxe/src
User=intelluxe-service
Group=intelluxe-prod
SupplementaryGroups=intelluxe-security

# Security validation environment
Environment=SECURITY_VALIDATION=true
Environment=PHI_PROTECTION_VERIFY=true
Environment=ENCRYPTION_VALIDATION=true
EOF
done

# Update systemd and restart services with security validation
sudo systemctl daemon-reload

# Validate each service before restart
for service in intelluxe-*.service; do
    echo "Validating security for $service..."
    if sudo systemctl start "$service"; then
        echo "✅ $service started successfully with security hardening"
    else
        echo "❌ $service failed to start - check security configuration"
        sudo journalctl -u "$service" --no-pager -n 20
    fi
done

echo "✅ Systemd security hardening complete"
```

---

## 🔐 4. Enhanced Network Security Hardening

### Current Development State (Phase 0)
```bash
# Development: Controlled access with security validation
# Services accessible from LAN with authentication
# Security systems validated at runtime
```

### Production Hardening Steps

#### 4.1 Security-Enhanced Network Access Restrictions
```bash
# Production network hardening with security validation
echo "🔐 Applying network security hardening..."

# Validate security systems before network changes
if ! python3 -c "
from src.healthcare_mcp.secure_mcp_server import SecureMCPServer
server = SecureMCPServer()
server.validate_auth_config()
print('✅ Authentication systems validated for network hardening')
"; then
    echo "❌ Authentication validation failed - cannot proceed with network hardening"
    exit 1
fi

# Reset firewall with security-aware rules
sudo ufw reset
sudo ufw default deny incoming
sudo ufw default deny outgoing
sudo ufw default allow routed

# Healthcare-specific network rules with authentication
sudo ufw allow from 192.168.0.0/16 to any port 22    # SSH (LAN only, key-based)
sudo ufw allow from 192.168.0.0/16 to any port 80    # HTTP (LAN only, redirects to HTTPS)
sudo ufw allow from 192.168.0.0/16 to any port 443   # HTTPS (LAN only, JWT required)
sudo ufw allow from 192.168.0.0/16 to any port 11434 # Ollama (LAN only, authenticated)
sudo ufw allow 51820/udp                             # WireGuard (encrypted tunnel)

# Block external access to sensitive services
sudo ufw deny from any to any port 9123              # Block external config UI access
sudo ufw deny from any to any port 5432              # Block external PostgreSQL access
sudo ufw deny from any to any port 6379              # Block external Redis access

# Enable with logging for security monitoring
sudo ufw logging on
sudo ufw enable

echo "✅ Network security hardening applied"
```

#### 4.2 Healthcare Network Segmentation with Security
```bash
# Create healthcare network isolation with security monitoring
echo "🏥 Implementing healthcare network segmentation..."

# Create security monitoring rules
sudo iptables -A INPUT -j LOG --log-prefix "HEALTHCARE-BLOCKED: " --log-level 4
sudo iptables -A OUTPUT -j LOG --log-prefix "HEALTHCARE-OUTBOUND: " --log-level 4

# Monitor PHI-related network traffic
sudo iptables -A INPUT -m string --string "patient" --algo bm -j LOG --log-prefix "PHI-NETWORK-ACCESS: "
sudo iptables -A OUTPUT -m string --string "patient" --algo bm -j LOG --log-prefix "PHI-NETWORK-EGRESS: "

# Create healthcare VLAN isolation (customize for your network)
# This would be implemented with your network infrastructure

echo "✅ Healthcare network segmentation implemented"
```

---

## 📊 5. Enhanced Logging & Monitoring Hardening

### Current Development State (Phase 0)
```bash
# Development: Comprehensive logging with security context
# Audit trails for security events
# PHI detection logging with masking
```

### Production Hardening Steps

#### 5.1 Security-Enhanced Healthcare Audit Logging
```bash
# production-logging-hardening.sh - Enhanced with security monitoring

echo "📊 Implementing security-enhanced healthcare audit logging..."

# Configure comprehensive audit logging for HIPAA compliance with security context
cat > /etc/audit/rules.d/99-intelluxe-healthcare-security.rules << EOF
# Monitor PHI access with security context
-w /opt/intelluxe/stack/data/ -p rwxa -k healthcare-phi-access
-w /opt/intelluxe/stack/data/phi/ -p rwxa -k healthcare-phi-critical
-w /opt/intelluxe/logs/ -p rwxa -k healthcare-logs
-w /opt/intelluxe/config/ -p rwxa -k healthcare-config-changes

# Monitor security system access
-w /opt/intelluxe/src/security/ -p rwxa -k healthcare-security-access
-w /opt/intelluxe/stack/security/ -p rwxa -k healthcare-security-critical
-w /opt/intelluxe/stack/security/keys/ -p rwxa -k healthcare-encryption-keys

# Monitor service account actions
-w /etc/passwd -p wa -k healthcare-user-changes
-w /etc/group -p wa -k healthcare-group-changes
-w /etc/systemd/system/intelluxe-*.service -p wa -k healthcare-service-changes

# Monitor authentication and authorization
-w /var/log/auth.log -p wa -k healthcare-auth-events
-w /opt/intelluxe/logs/audit/ -p wa -k healthcare-audit-access
EOF

# Apply audit rules with security validation
sudo auditctl -R /etc/audit/rules.d/99-intelluxe-healthcare-security.rules
sudo systemctl enable auditd
sudo systemctl start auditd

echo "✅ Security-enhanced audit logging configured"
```

#### 5.2 Enhanced Log Security & Retention
```bash
# Secure log permissions with security context
sudo chmod 640 /opt/intelluxe/logs/*.log
sudo chown intelluxe-service:intelluxe-prod /opt/intelluxe/logs/*.log

# Create security-specific log directories
sudo mkdir -p /opt/intelluxe/logs/security
sudo mkdir -p /opt/intelluxe/logs/phi-detection
sudo mkdir -p /opt/intelluxe/logs/audit

sudo chown intelluxe-service:intelluxe-security /opt/intelluxe/logs/security/
sudo chown intelluxe-service:intelluxe-security /opt/intelluxe/logs/audit/
sudo chmod 750 /opt/intelluxe/logs/security/
sudo chmod 750 /opt/intelluxe/logs/audit/

# Enhanced healthcare log retention with security monitoring
cat > /etc/logrotate.d/intelluxe-healthcare-security << EOF
/opt/intelluxe/logs/*.log {
    daily
    rotate 2555  # 7 years retention (HIPAA requirement)
    compress
    delaycompress
    missingok
    notifempty
    create 640 intelluxe-service intelluxe-prod
    postrotate
        # Validate security systems after log rotation
        python3 -c "from src.security.encryption_manager import EncryptionManager; EncryptionManager().validate_keys()" || logger "Security validation failed after log rotation"
        systemctl reload intelluxe-*.service > /dev/null 2>&1 || true
    endscript
}

/opt/intelluxe/logs/security/*.log {
    daily
    rotate 2555  # 7 years retention
    compress
    delaycompress
    missingok
    notifempty
    create 640 intelluxe-service intelluxe-security
    postrotate
        logger "Security logs rotated - validation required"
    endscript
}
EOF

echo "✅ Enhanced log security and retention configured"
```

---

## 🔍 6. Enhanced Healthcare Compliance Hardening

### 6.1 Security-Enhanced PHI Protection Verification
```bash
#!/bin/bash
# production-phi-protection-audit.sh - Enhanced with security validation

echo "🏥 Enhanced Healthcare PHI Protection Audit with Security Validation"
echo "=================================================================="

# Validate Phase 0 security foundation
echo "Validating Phase 0 security foundation..."
if ! python3 -c "
from src.security.encryption_manager import EncryptionManager
from src.healthcare_mcp.phi_detection import PHIDetector
from src.security.rbac_foundation import RBACFoundation

# Comprehensive security validation
em = EncryptionManager()
em.validate_production_readiness()

pd = PHIDetector()
pd.validate_system()

rbac = RBACFoundation()
rbac.validate_production_readiness()

print('✅ Phase 0 security foundation validated')
"; then
    echo "❌ CRITICAL: Phase 0 security validation failed"
    exit 1
fi

# Verify no PHI in logs with enhanced detection
echo "Checking for PHI exposure in logs with enhanced detection..."
if python3 -c "
from src.healthcare_mcp.phi_detection import PHIDetector
import os

detector = PHIDetector()
phi_found = False

for root, dirs, files in os.walk('/opt/intelluxe/logs/'):
    for file in files:
        if file.endswith('.log'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r') as f:
                content = f.read()
                result = detector.detect_phi_sync(content)
                if result.phi_detected:
                    print(f'PHI detected in {filepath}')
                    phi_found = True

if phi_found:
    exit(1)
else:
    print('No PHI found in logs')
"; then
    echo "✅ No PHI found in logs"
else
    echo "❌ CRITICAL: PHI found in logs - investigate immediately"
    exit 1
fi

# Verify encryption systems
echo "Checking encryption system integrity..."
if python3 -c "
from src.security.encryption_manager import EncryptionManager
em = EncryptionManager()
em.validate_keys()
em.test_encryption_decryption()
print('✅ Encryption systems validated')
"; then
    echo "✅ Encryption systems validated"
else
    echo "❌ CRITICAL: Encryption system validation failed"
    exit 1
fi

# Verify authentication systems
echo "Checking authentication system integrity..."
if python3 -c "
from src.healthcare_mcp.secure_mcp_server import SecureMCPServer
server = SecureMCPServer()
server.validate_auth_config()
print('✅ Authentication systems validated')
"; then
    echo "✅ Authentication systems validated"
else
    echo "❌ CRITICAL: Authentication system validation failed"
    exit 1
fi

# Verify network isolation
echo "Checking network isolation..."
if netstat -tulpn | grep -E ":(80|443|9123|11434)" | grep -v "127.0.0.1\|192.168."; then
    echo "❌ WARNING: Services accessible from external networks"
else
    echo "✅ Services properly isolated to internal networks"
fi

# Verify file permissions with security context
echo "Checking file permissions with security context..."
find /opt/intelluxe/ -type f -perm /o+rwx -ls | head -5
find /opt/intelluxe/stack/security/ -type f ! -perm 600 -ls | head -5
echo "✅ File permissions audit complete"

# Verify user access with security groups
echo "Checking user access with security groups..."
if id intelluxe-service >/dev/null 2>&1; then
    echo "✅ Production service user exists"
    if groups intelluxe-service | grep -q intelluxe-security; then
        echo "✅ Security group membership configured"
    else
        echo "❌ Security group membership missing"
    fi
else
    echo "❌ Production service user missing"
fi

echo "🏥 Enhanced PHI Protection Audit with Security Validation Complete"
```

---

## 🚀 7. Enhanced Production Deployment Checklist

### Pre-Deployment Security Validation
- [ ] **Phase 0 Security Foundation**: Validated encryption manager, PHI detection, and RBAC systems
- [ ] **User Accounts**: Created dedicated service users with security group membership
- [ ] **File Permissions**: Applied production permission model with security hardening
- [ ] **Directory Structure**: Replaced symlinks with secure file copies
- [ ] **Systemd Security**: Enabled full security hardening with Phase 0 integration
- [ ] **Network Security**: Configured firewall with authentication-aware rules
- [ ] **Audit Logging**: Enabled healthcare-specific audit trails with security context
- [ ] **Log Security**: Secured log files with enhanced retention and security monitoring
- [ ] **PHI Protection**: Verified PHI detection and masking with batch processing
- [ ] **Encryption Validation**: Confirmed all encryption keys meet security requirements
- [ ] **Authentication Systems**: Validated JWT configuration and production readiness
- [ ] **HIPAA Compliance**: Completed technical and administrative safeguards
- [ ] **Security Testing**: Completed comprehensive security validation suite
- [ ] **Documentation**: Updated all procedures for production environment with security context

### Post-Deployment Security Verification
```bash
# Run comprehensive security audit with Phase 0 validation
sudo bash production-phi-protection-audit.sh
sudo bash production-hipaa-compliance-check.sh

# Test security systems integration
python3 -c "
from src.security.encryption_manager import EncryptionManager
from src.healthcare_mcp.phi_detection import PHIDetector
from src.security.rbac_foundation import RBACFoundation

# Comprehensive integration test
em = EncryptionManager()
pd = PHIDetector()
rbac = RBACFoundation()

# Test encryption
test_data = 'Test healthcare data'
encrypted = em.encrypt_data(test_data)
decrypted = em.decrypt_data(encrypted)
assert decrypted == test_data

# Test PHI detection
phi_result = pd.detect_phi_sync('Patient John Doe, SSN: 123-45-6789')
assert phi_result.phi_detected

# Test RBAC
rbac_result = rbac.check_patient_access('user123', 'patient456')
print('✅ Security systems integration test passed')
"

# Test service functionality with security
sudo systemctl status intelluxe-*.service
sudo journalctl -u intelluxe-*.service --since="1 hour ago" | grep -i security

# Verify network security with authentication
sudo ufw status numbered
sudo netstat -tulpn | grep -E ":(80|443|9123|11434)"

# Test PHI protection with enhanced detection
sudo python3 -c "
from src.healthcare_mcp.phi_detection import PHIDetector
detector = PHIDetector()
result = detector.detect_phi_sync('Test patient data without PHI')
print(f'PHI detection test: {result.phi_detected}')
"

### User Authentication Integration Testing

# Test healthcare authentication integration
python3 -c "
from src.security.healthcare_auth import HealthcareAuthManager
import os

# Test authentication manager initialization
auth = HealthcareAuthManager()
print(f'✅ Current user detected: {auth.current_user}')
print(f'✅ Auth mode: {auth.auth_mode.value}')

# Test user config loading
try:
    config = auth.load_user_environment()
    print(f'✅ User config loaded: {len(config)} settings')
    print(f'✅ User role: {config.get(\"INTELLUXE_ROLE\", \"not_set\")}')
except Exception as e:
    print(f'⚠️  User config creation needed: {e}')

# Test config encryption/decryption
if hasattr(auth, '_derive_user_key'):
    key = auth._derive_user_key()
    print('✅ User session key derivation working')

print('✅ Healthcare authentication integration test passed')
"
```

---

**⚠️ Critical Production Security Notes:**
1. **Complete Phase 0 security validation** before any production hardening
2. **Test all security integrations** in staging environment first
3. **Validate encryption, PHI detection, and RBAC** systems work together
4. **Coordinate with clinical and IT staff** before implementing
5. **Maintain development environment** separately with security validation
6. **Document all security customizations** for compliance audits
7. **Schedule regular security reviews** and penetration testing
8. **Train healthcare staff** on security procedures and incident response

---

*This document should be reviewed and updated before each major security update and at least quarterly for ongoing compliance validation.*
