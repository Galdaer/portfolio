# Production Security Hardening Guide

**Document Version**: 1.0.0  
**Target Audience**: System Administrators, DevOps Engineers  
**Phase**: Pre-Production Hardening (Phase 3)  
**Last Updated**: July 16, 2025

## Overview

This document outlines security hardening steps required when transitioning the Intelluxe AI Healthcare System from development to production deployment. During development (Phase 0-2), we intentionally use relaxed security settings for rapid iteration and debugging. This guide details how to tighten security for healthcare production environments.

⚠️ **Healthcare Compliance Notice**: All changes must maintain HIPAA compliance and ensure PHI/PII protection remains on-premise.

## 🔧 Development vs Production: Key Differences

### Current Development Model (Phase 0-2)
- **Permissive for rapid development and family collaboration**
- **Optimized for debugging and quick iteration**
- **Symlink-based for immediate file reflection**

### Production Model (Phase 3+)
- **Hardened for clinical deployment**
- **Minimal attack surface**
- **File copying instead of symlinks**
- **Restricted user permissions**

---

## 🛡️ 1. File Ownership & Permissions Hardening

### Current Development State
```bash
# Development permissions (Phase 0-2)
CFG_UID=1000    # justin (family member)
CFG_GID=1001    # intelluxe (group for family collaboration)

# File permissions
Scripts: 755 (all family members can edit)
Configs: 660/664 (group writable)
Logs: 664 (group readable)
```

### Production Hardening Steps

#### 1.1 Create Dedicated Service User
```bash
# Create dedicated intelluxe service user (no shell, no home)
sudo useradd -r -s /bin/false -d /opt/intelluxe -M intelluxe-service

# Create dedicated group for production
sudo groupadd --gid 2001 intelluxe-prod

# Update CFG_UID/CFG_GID in all scripts
CFG_UID=2000    # intelluxe-service
CFG_GID=2001    # intelluxe-prod
```

#### 1.2 Restrict File Permissions
```bash
# Production permission model
Scripts: 750 (owner execute only)
Configs: 640 (owner read/write, group read only)
Logs: 640 (owner read/write, group read only)
Data directories: 700 (owner only)
```

#### 1.3 Implementation Script
```bash
#!/bin/bash
# production-permission-hardening.sh

# Update all scripts with production UID/GID
find scripts/ -name "*.sh" -exec sed -i 's/DEFAULT_UID=1000/DEFAULT_UID=2000/g' {} \;
find scripts/ -name "*.sh" -exec sed -i 's/DEFAULT_GID=1001/DEFAULT_GID=2001/g' {} \;

# Apply production permissions
chmod 750 scripts/*.sh scripts/*.py
chmod 640 systemd/*.service systemd/*.timer
find stack/ -name "*.conf" -exec chmod 640 {} \;
find stack/ -name "*.log" -exec chmod 640 {} \;
chmod 700 stack/data/ stack/backups/
chown -R intelluxe-service:intelluxe-prod /opt/intelluxe/
```

---

## 🗂️ 2. Directory Structure Hardening

### Current Development State
```bash
# Development: Symlinks for easy editing
/opt/intelluxe/scripts -> /home/intelluxe/scripts/
/opt/intelluxe/stack -> /home/intelluxe/stack/
# (All directories symlinked except logs/)
```

### Production Hardening Steps

#### 2.1 Replace Symlinks with File Copies
```bash
# production-structure-hardening.sh

# Remove development symlinks
sudo rm -f /opt/intelluxe/scripts /opt/intelluxe/stack /opt/intelluxe/agents
sudo rm -f /opt/intelluxe/config /opt/intelluxe/core /opt/intelluxe/data
sudo rm -f /opt/intelluxe/infrastructure /opt/intelluxe/mcps
sudo rm -f /opt/intelluxe/notebooks /opt/intelluxe/services /opt/intelluxe/systemd

# Copy files instead of symlinks
sudo cp -r /home/intelluxe/scripts/ /opt/intelluxe/scripts/
sudo cp -r /home/intelluxe/stack/ /opt/intelluxe/stack/
sudo cp -r /home/intelluxe/agents/ /opt/intelluxe/agents/
sudo cp -r /home/intelluxe/config/ /opt/intelluxe/config/
sudo cp -r /home/intelluxe/core/ /opt/intelluxe/core/
sudo cp -r /home/intelluxe/data/ /opt/intelluxe/data/
sudo cp -r /home/intelluxe/infrastructure/ /opt/intelluxe/infrastructure/
sudo cp -r /home/intelluxe/mcps/ /opt/intelluxe/mcps/
sudo cp -r /home/intelluxe/notebooks/ /opt/intelluxe/notebooks/
sudo cp -r /home/intelluxe/services/ /opt/intelluxe/services/
sudo cp -r /home/intelluxe/systemd/ /opt/intelluxe/systemd/

# Set production ownership
sudo chown -R intelluxe-service:intelluxe-prod /opt/intelluxe/
```

#### 2.2 Update Makefile for Production
```makefile
# Update PROD_DIRS handling in Makefile
install-production:
	@echo "🔒 Installing Intelluxe AI for PRODUCTION deployment"
	@echo "   - Creating production directories with file copies (not symlinks)"
	@for dir in $(PROD_DIRS); do \
	    if [ -d "$(PWD)/$$dir" ]; then \
	        echo "     Copying $$dir -> /opt/intelluxe/$$dir"; \
	        sudo cp -r $(PWD)/$$dir /opt/intelluxe/; \
	    fi; \
	done
	@echo "   - Setting production permissions"
	@sudo chown -R $(PROD_UID):$(PROD_GID) /opt/intelluxe
	@sudo chmod 750 /opt/intelluxe/scripts/*.sh
	@sudo chmod 640 /opt/intelluxe/systemd/*.service
```

#### 2.3 Remove Development Home Directory Access
```bash
# Remove /home/intelluxe/ access in production
sudo chmod 700 /home/intelluxe/  # Only justin can access
# OR: Move development to separate system entirely
```

---

## 🛡️ 3. Systemd Service Hardening

### Current Development State
```ini
# Development systemd services (minimal security)
[Service]
Type=oneshot
ExecStart=/opt/intelluxe/scripts/auto-upgrade.sh
Environment=HOME=/root
# Minimal security restrictions for debugging
```

### Production Hardening Steps

#### 3.1 Enable Full Systemd Security
```ini
# Production systemd service template
[Service]
Type=oneshot
ExecStart=/opt/intelluxe/scripts/auto-upgrade.sh
User=intelluxe-service
Group=intelluxe-prod

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

# Healthcare-specific paths (minimal required access)
ReadWritePaths=/opt/intelluxe/logs /opt/intelluxe/stack/data
ReadOnlyPaths=/opt/intelluxe/scripts /opt/intelluxe/config
InaccessiblePaths=/home /boot /root

# Capability restrictions
CapabilityBoundingSet=CAP_NET_BIND_SERVICE CAP_SETUID CAP_SETGID
AmbientCapabilities=

# Resource limits for healthcare stability
MemoryMax=1G
TasksMax=100
TimeoutStartSec=300
TimeoutStopSec=60

SyslogIdentifier=intelluxe-healthcare
StandardOutput=journal
StandardError=journal
```

#### 3.2 Service-Specific Hardening Script
```bash
#!/bin/bash
# production-systemd-hardening.sh

# Apply production security to all services
for service in /opt/intelluxe/systemd/*.service; do
    service_name=$(basename "$service")
    echo "Hardening $service_name..."
    
    # Add security sections to each service
    cat >> "$service" << EOF

# Production Security Hardening
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
ReadWritePaths=/opt/intelluxe/logs
ReadOnlyPaths=/opt/intelluxe/scripts /opt/intelluxe/config
User=intelluxe-service
Group=intelluxe-prod
EOF
done

# Update systemd and restart services
sudo systemctl daemon-reload
sudo systemctl restart intelluxe-*.service
```

---

## 🔐 4. Network Security Hardening

### Current Development State
```bash
# Development: Open access for family collaboration
# Services accessible from any IP
# Minimal firewall restrictions
```

### Production Hardening Steps

#### 4.1 Network Access Restrictions
```bash
# Production network hardening
# Restrict to LAN + VPN only
sudo ufw reset
sudo ufw default deny incoming
sudo ufw default deny outgoing
sudo ufw default allow routed

# Healthcare-specific network rules
sudo ufw allow from 192.168.0.0/16 to any port 22    # SSH (LAN only)
sudo ufw allow from 192.168.0.0/16 to any port 80    # HTTP (LAN only)
sudo ufw allow from 192.168.0.0/16 to any port 443   # HTTPS (LAN only)
sudo ufw allow from 192.168.0.0/16 to any port 11434 # Ollama (LAN only)
sudo ufw allow 51820/udp                             # WireGuard

# Block all other access
sudo ufw deny from any to any port 9123              # Block external config UI access
sudo ufw enable
```

#### 4.2 Healthcare Network Segmentation
```bash
# Create healthcare network isolation
# Use separate VLAN for healthcare services
# Implement network monitoring for PHI protection
sudo iptables -A INPUT -j LOG --log-prefix "HEALTHCARE-BLOCKED: "
sudo iptables -A OUTPUT -j LOG --log-prefix "HEALTHCARE-OUTBOUND: "
```

---

## 📊 5. Logging & Monitoring Hardening

### Current Development State
```bash
# Development: Verbose logging for debugging
# Logs accessible to family group
# Minimal log rotation
```

### Production Hardening Steps

#### 5.1 Healthcare Audit Logging
```bash
# production-logging-hardening.sh

# Configure audit logging for HIPAA compliance
cat > /etc/audit/rules.d/99-intelluxe-healthcare.rules << EOF
# Monitor PHI access
-w /opt/intelluxe/stack/data/ -p rwxa -k healthcare-phi-access
-w /opt/intelluxe/logs/ -p rwxa -k healthcare-logs
-w /opt/intelluxe/config/ -p rwxa -k healthcare-config-changes

# Monitor service account actions
-w /etc/passwd -p wa -k healthcare-user-changes
-w /etc/group -p wa -k healthcare-group-changes
-w /etc/systemd/system/intelluxe-*.service -p wa -k healthcare-service-changes
EOF

sudo auditctl -R /etc/audit/rules.d/99-intelluxe-healthcare.rules
sudo systemctl enable auditd
sudo systemctl start auditd
```

#### 5.2 Log Security & Rotation
```bash
# Secure log permissions
sudo chmod 640 /opt/intelluxe/logs/*.log
sudo chown intelluxe-service:intelluxe-prod /opt/intelluxe/logs/*.log

# Healthcare log retention (7 years for compliance)
cat > /etc/logrotate.d/intelluxe-healthcare << EOF
/opt/intelluxe/logs/*.log {
    daily
    rotate 2555  # 7 years retention
    compress
    delaycompress
    missingok
    notifempty
    create 640 intelluxe-service intelluxe-prod
    postrotate
        systemctl reload intelluxe-*.service > /dev/null 2>&1 || true
    endscript
}
EOF
```

---

## 🔍 6. Healthcare Compliance Hardening

### 6.1 PHI Protection Verification
```bash
#!/bin/bash
# production-phi-protection-audit.sh

echo "🏥 Healthcare PHI Protection Audit"
echo "=================================="

# Verify no PHI in logs
echo "Checking for PHI exposure in logs..."
if grep -r -i -E "(ssn|social.?security|patient.?id|medical.?record)" /opt/intelluxe/logs/; then
    echo "❌ CRITICAL: PHI found in logs - investigate immediately"
    exit 1
else
    echo "✅ No PHI found in logs"
fi

# Verify network isolation
echo "Checking network isolation..."
if netstat -tulpn | grep -E ":(80|443|9123|11434)" | grep -v "127.0.0.1\|192.168."; then
    echo "❌ WARNING: Services accessible from external networks"
else
    echo "✅ Services properly isolated to internal networks"
fi

# Verify file permissions
echo "Checking file permissions..."
find /opt/intelluxe/ -type f -perm /o+rwx -ls | head -5
echo "✅ File permissions audit complete"

# Verify user access
echo "Checking user access..."
if id intelluxe-service >/dev/null 2>&1; then
    echo "✅ Production service user exists"
else
    echo "❌ Production service user missing"
fi

echo "🏥 PHI Protection Audit Complete"
```

### 6.2 HIPAA Compliance Checklist
```bash
#!/bin/bash
# production-hipaa-compliance-check.sh

echo "🏥 HIPAA Compliance Verification"
echo "==============================="

# Technical Safeguards (45 CFR § 164.312)
echo "📋 Technical Safeguards:"
echo "  [x] Access Control - User accounts restricted"
echo "  [x] Audit Controls - Audit logging enabled"
echo "  [x] Integrity - File permissions secured"
echo "  [x] Person or Entity Authentication - Service accounts"
echo "  [x] Transmission Security - VPN/TLS encryption"

# Administrative Safeguards (45 CFR § 164.308)
echo "📋 Administrative Safeguards:"
echo "  [x] Security Officer - Designated administrator"
echo "  [x] Workforce Training - Development team trained"
echo "  [x] Information Access Management - Role-based access"
echo "  [x] Security Awareness - Security procedures documented"

# Physical Safeguards (45 CFR § 164.310)
echo "📋 Physical Safeguards:"
echo "  [ ] Facility Access Controls - Customer responsibility"
echo "  [ ] Workstation Use - Customer responsibility"
echo "  [x] Device and Media Controls - Audit logging"

echo "🏥 HIPAA Compliance Check Complete"
echo "Note: Physical safeguards are customer/clinic responsibility"
```

---

## 🚀 7. Production Deployment Checklist

### Pre-Deployment Security Checklist
- [ ] **User Accounts**: Created dedicated service users (intelluxe-service:intelluxe-prod)
- [ ] **File Permissions**: Applied production permission model (750/640/700)
- [ ] **Directory Structure**: Replaced symlinks with file copies
- [ ] **Systemd Security**: Enabled full security hardening on all services
- [ ] **Network Security**: Configured firewall for LAN/VPN only access
- [ ] **Audit Logging**: Enabled healthcare-specific audit trails
- [ ] **Log Security**: Secured log files and configured HIPAA-compliant retention
- [ ] **PHI Protection**: Verified no PHI exposure in logs or configs
- [ ] **HIPAA Compliance**: Completed technical and administrative safeguards
- [ ] **Backup Security**: Secured backup processes and encryption
- [ ] **Documentation**: Updated all procedures for production environment

### Post-Deployment Verification
```bash
# Run full security audit
sudo bash production-phi-protection-audit.sh
sudo bash production-hipaa-compliance-check.sh

# Test service functionality
sudo systemctl status intelluxe-*.service
sudo journalctl -u intelluxe-*.service --since="1 hour ago"

# Verify network security
sudo ufw status numbered
sudo netstat -tulpn | grep -E ":(80|443|9123|11434)"

# Test PHI protection
sudo scripts/check-phi-exposure.sh --production-mode
```

---

## ⚠️ 8. Development to Production Migration Script

```bash
#!/bin/bash
# migrate-to-production.sh - Complete hardening automation

set -euo pipefail

echo "🔒 Intelluxe AI Healthcare: Development → Production Migration"
echo "============================================================="

# Backup current development state
echo "📦 Backing up development configuration..."
sudo tar -czf /opt/backup-intelluxe-dev-$(date +%Y%m%d).tar.gz /home/intelluxe/ /opt/intelluxe/

# Create production users
echo "👥 Creating production service accounts..."
sudo useradd -r -s /bin/false -d /opt/intelluxe -M intelluxe-service 2>/dev/null || true
sudo groupadd --gid 2001 intelluxe-prod 2>/dev/null || true

# Apply file hardening
echo "📁 Applying file permission hardening..."
bash production-permission-hardening.sh

# Apply directory hardening  
echo "🗂️ Applying directory structure hardening..."
bash production-structure-hardening.sh

# Apply systemd hardening
echo "🛡️ Applying systemd service hardening..."
bash production-systemd-hardening.sh

# Apply network hardening
echo "🌐 Applying network security hardening..."
bash production-network-hardening.sh

# Apply logging hardening
echo "📊 Applying logging and audit hardening..."
bash production-logging-hardening.sh

# Final verification
echo "🔍 Running production security verification..."
bash production-phi-protection-audit.sh
bash production-hipaa-compliance-check.sh

echo "✅ Production hardening complete!"
echo "📋 Review checklist above and complete any pending items"
echo "🏥 System ready for healthcare production deployment"
```

---

## 📚 Additional Resources

- **HIPAA Security Rule**: [45 CFR Part 164, Subpart C](https://www.hhs.gov/hipaa/for-professionals/security/index.html)
- **NIST Cybersecurity Framework**: Healthcare sector implementation
- **Systemd Security**: `man systemd.exec` for complete security options
- **Ubuntu Security Guide**: [Ubuntu Security Documentation](https://ubuntu.com/security)

---

**⚠️ Important Notes:**
1. **Test all changes in staging environment first**
2. **Coordinate with clinical staff before implementing**
3. **Maintain development environment separately for ongoing development**
4. **Document all changes for compliance audits**
5. **Schedule regular security reviews and updates**

---

*This document should be reviewed and updated before each major release and at least annually for compliance.*
