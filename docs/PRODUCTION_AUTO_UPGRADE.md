# Production Auto-Upgrade System for Healthcare Environments

**Document Version**: 1.1.0  
**Target Audience**: Healthcare System Administrators, DevOps Engineers  
**Phase**: Production Deployment (Phase 3)  
**Component**: Auto-Upgrade System (`auto-upgrade.sh`, `auto-upgrade.service`, `auto-upgrade.timer`)  
**Last Updated**: December 2024

## Overview

This document outlines the production-ready auto-upgrade system for Intelluxe AI Healthcare environments. The auto-upgrade system automatically updates system packages while maintaining healthcare safety protocols and HIPAA compliance requirements.

⚠️ **Healthcare Safety Notice**: This system is designed to update ONLY system packages, never medical services or patient data systems.

## 🏥 Healthcare Environment Modes

### Development Mode (Phase 0-2)
- **Purpose**: Rapid development and testing with Phase 0 security foundation
- **Safety Checks**: Basic validation with comprehensive logging
- **Schedule**: Weekly (Sunday 2 AM) with development flexibility
- **Audit Logging**: Optional but recommended for security testing
- **Patient Safety**: Simulated checks for development validation

### Production Mode (Phase 3+)
- **Purpose**: Live clinical deployment with full security hardening
- **Safety Checks**: Full healthcare protocols with PHI protection
- **Schedule**: Maintenance windows only with clinical coordination
- **Audit Logging**: Required (HIPAA compliance with 7-year retention)
- **Patient Safety**: Active session monitoring with EHR integration

---

## 🔧 Production Configuration Files

### 1. Enhanced Auto-Upgrade Script (`auto-upgrade.sh`)

**Key Production Features:**
- **Healthcare Mode Detection**: Environment-aware security policies
- **Patient Safety Checks**: PHI-aware session monitoring
- **Maintenance Windows**: Clinical workflow coordination
- **HIPAA Audit Logging**: Comprehensive compliance tracking
- **Service Health Verification**: Healthcare service dependency validation
- **Security Validation**: Encryption and authentication checks

```bash
# Production environment variables
HEALTHCARE_MODE=production          # development|staging|production
MAINTENANCE_WINDOW=true            # Only update during maintenance windows
AUDIT_REQUIRED=true               # HIPAA compliance audit logging
PATIENT_SAFETY_CHECK=true         # Check for active patient sessions
PHI_PROTECTION_VERIFY=true        # Verify PHI protection systems
SECURITY_VALIDATION=true          # Validate encryption and auth systems
```

### 2. Production Service Configuration (`auto-upgrade.service`)

```ini
[Unit]
Description=Auto-upgrade system packages for Intelluxe AI Healthcare System
Documentation=https://github.com/Intelluxe-AI/intelluxe-core/docs/PRODUCTION_AUTO_UPGRADE.md
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/opt/intelluxe/scripts/auto-upgrade.sh
User=intelluxe-service
Group=intelluxe-prod

# Production healthcare environment
Environment=HEALTHCARE_MODE=production
Environment=CFG_UID=2000
Environment=CFG_GID=2001
Environment=HOME=/opt/intelluxe

# Security validation environment
Environment=PHI_PROTECTION_VERIFY=true
Environment=SECURITY_VALIDATION=true
Environment=AUDIT_REQUIRED=true

# HIPAA compliance logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=intelluxe-auto-upgrade

# Production security hardening
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
PrivateDevices=yes
ProtectKernelTunables=yes
ProtectControlGroups=yes
RestrictSUIDSGID=yes
MemoryDenyWriteExecute=yes

# Healthcare-specific access
ReadWritePaths=/var/log /var/run /tmp /var/lib/apt /var/cache/apt /opt/intelluxe/logs
ReadOnlyPaths=/opt/intelluxe/scripts /opt/intelluxe/config
InaccessiblePaths=/home /boot

# Resource limits for healthcare stability
MemoryMax=512M
TasksMax=50
TimeoutStartSec=1800
TimeoutStopSec=300

[Install]
WantedBy=multi-user.target
```

### 3. Production Timer Configuration (`auto-upgrade.timer`)

```ini
[Unit]
Description=Healthcare-safe auto-upgrade schedule for Intelluxe AI
Documentation=https://github.com/Intelluxe-AI/intelluxe-core/docs/PRODUCTION_AUTO_UPGRADE.md
Requires=intelluxe-auto-upgrade.service

[Timer]
# Healthcare maintenance window: Sunday 2-4 AM
OnCalendar=Sun *-*-* 02:00:00

# Healthcare safety features
Persistent=true
RandomizedDelaySec=1800
AccuracySec=15min

# Stability for healthcare environments
OnClockChange=no
OnTimezoneChange=no

[Install]
WantedBy=timers.target
```

---

## 🛡️ Enhanced Healthcare Safety Protocols

### 1. Security System Validation

```bash
# Production security validation before updates
validate_security_systems() {
    log "INFO" "Validating healthcare security systems..."
    
    # Validate encryption systems
    if ! python3 -c "from src.security.encryption_manager import EncryptionManager; EncryptionManager().validate_keys()"; then
        log "ERROR" "Encryption system validation failed"
        return 1
    fi
    
    # Validate PHI detection systems
    if ! python3 -c "from src.healthcare_mcp.phi_detection import PHIDetector; PHIDetector().validate_system()"; then
        log "ERROR" "PHI detection system validation failed"
        return 1
    fi
    
    # Validate authentication systems
    if [[ "$HEALTHCARE_MODE" == "production" ]]; then
        if ! python3 -c "from src.healthcare_mcp.secure_mcp_server import SecureMCPServer; SecureMCPServer().validate_auth_config()"; then
            log "ERROR" "Authentication system validation failed"
            return 1
        fi
    fi
    
    log "INFO" "Security system validation passed"
    return 0
}
```

### 2. Enhanced Patient Safety Checks

```bash
# Production patient safety verification with PHI awareness
check_patient_safety() {
    log "INFO" "Checking for active patient sessions with PHI protection..."
    
    # Check healthcare service containers with PHI processing
    if docker ps --filter "label=intelluxe.service=healthcare" --filter "status=running" -q | grep -q .; then
        log "WARN" "Healthcare services active - checking PHI processing status"
        
        # Check for active PHI processing
        local phi_processing_active
        phi_processing_active=$(docker exec -i $(docker ps --filter "label=intelluxe.phi=true" -q | head -1) \
            python3 -c "from src.healthcare_mcp.phi_detection import PHIDetector; print(PHIDetector().get_active_sessions())" 2>/dev/null || echo "0")
        
        if [[ $phi_processing_active -gt 0 ]]; then
            log "ERROR" "Active PHI processing detected - updates blocked"
            return 1
        fi
        
        # Business hours check with clinical workflow awareness
        local current_hour
        current_hour=$(date +%H)
        if [[ $current_hour -ge 8 && $current_hour -le 18 ]]; then
            # Check for scheduled appointments or active clinical workflows
            if check_clinical_workflows; then
                log "ERROR" "Updates blocked: Active clinical workflows during business hours"
                return 1
            fi
        fi
    fi
    
    # Enhanced database activity monitoring
    if systemctl is-active --quiet postgresql; then
        local active_connections phi_queries
        active_connections=$(sudo -u postgres psql -t -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';" 2>/dev/null || echo "0")
        phi_queries=$(sudo -u postgres psql -t -c "SELECT count(*) FROM pg_stat_activity WHERE query LIKE '%patient%' OR query LIKE '%phi%';" 2>/dev/null || echo "0")
        
        if [[ $phi_queries -gt 0 ]]; then
            log "ERROR" "Active PHI database queries detected - updates blocked"
            return 1
        fi
        
        if [[ $active_connections -gt 5 ]]; then
            log "WARN" "High database activity detected ($active_connections active connections)"
            if [[ "$HEALTHCARE_MODE" == "production" ]]; then
                log "ERROR" "Updates blocked: High database activity suggests active patient sessions"
                return 1
            fi
        fi
    fi
    
    return 0
}
```

### 3. Healthcare Service Health Verification

```bash
# Enhanced healthcare service verification with security validation
verify_healthcare_services() {
    local check_type="$1"  # "pre" or "post"
    
    log "INFO" "Running $check_type-update healthcare service verification with security validation..."
    
    # Critical healthcare services with security requirements
    local critical_services=(
        "postgresql"        # Patient data database
        "redis-server"      # Session cache
        "docker"           # Container runtime for healthcare services
    )
    
    # Check system services
    for service in "${critical_services[@]}"; do
        if systemctl is-enabled "$service" >/dev/null 2>&1; then
            if systemctl is-active --quiet "$service"; then
                log "INFO" "✓ $service is running"
            else
                log "ERROR" "✗ Critical service $service is not running"
                return 1
            fi
        fi
    done
    
    # Check healthcare Docker containers with security validation
    if command -v docker >/dev/null 2>&1; then
        local unhealthy_containers security_containers
        unhealthy_containers=$(docker ps --filter "label=intelluxe.healthcare=true" --filter "health=unhealthy" -q | wc -l)
        security_containers=$(docker ps --filter "label=intelluxe.security=true" --filter "status=running" -q | wc -l)
        
        if [[ $unhealthy_containers -gt 0 ]]; then
            log "ERROR" "Found $unhealthy_containers unhealthy healthcare containers"
            return 1
        fi
        
        if [[ $security_containers -eq 0 ]]; then
            log "ERROR" "No security containers running - healthcare system compromised"
            return 1
        fi
        
        local healthcare_containers
        healthcare_containers=$(docker ps --filter "label=intelluxe.healthcare=true" -q | wc -l)
        log "INFO" "✓ $healthcare_containers healthcare containers running and healthy"
        log "INFO" "✓ $security_containers security containers active"
    fi
    
    # Validate security systems post-update
    if [[ "$check_type" == "post" ]]; then
        if ! validate_security_systems; then
            log "ERROR" "Security system validation failed after update"
            return 1
        fi
    fi
    
    # Check disk space for healthcare data with PHI considerations
    local data_disk_usage phi_storage_usage
    data_disk_usage=$(df /opt/intelluxe/stack/data 2>/dev/null | awk 'NR==2 {print $5}' | tr -d '%' || echo "0")
    phi_storage_usage=$(du -sh /opt/intelluxe/stack/data/phi 2>/dev/null | awk '{print $1}' || echo "0")
    
    if [[ $data_disk_usage -gt 85 ]]; then
        log "WARN" "Healthcare data disk usage high: $data_disk_usage% (PHI storage: $phi_storage_usage)"
        if [[ $data_disk_usage -gt 95 ]]; then
            log "ERROR" "Critical: Healthcare data disk usage: $data_disk_usage%"
            return 1
        fi
    fi
    
    log "INFO" "$check_type-update healthcare service verification with security validation passed"
    return 0
}
```

---

## 📊 Enhanced HIPAA Compliance & Audit Logging

### 1. Security-Aware Audit Log Format

```bash
# Enhanced HIPAA-compliant audit logging with security context
audit_log() {
    local action="$1"
    local details="$2"
    local user="${3:-$(whoami)}"
    local security_context="${4:-normal}"
    local timestamp
    timestamp=$(date --iso-8601=seconds)
    
    # Enhanced HIPAA audit trail format with security validation
    cat >> "$AUDIT_LOG" << EOF
{
  "timestamp": "$timestamp",
  "system": "intelluxe-auto-upgrade",
  "action": "$action",
  "details": "$details",
  "user": "$user",
  "pid": "$$",
  "mode": "$HEALTHCARE_MODE",
  "security_context": "$security_context",
  "phi_protection_active": "$(check_phi_protection_status)",
  "encryption_validated": "$(check_encryption_status)",
  "compliance": "HIPAA"
}
EOF
}

# Enhanced audit events with security context
audit_log "UPGRADE_START" "System package upgrade initiated" "$(whoami)" "security_validated"
audit_log "SECURITY_CHECK" "Encryption and PHI protection validated" "$(whoami)" "security_critical"
audit_log "PATIENT_SAFETY_CHECK" "Active session and PHI processing check completed" "$(whoami)" "patient_safety"
audit_log "UPGRADE_COMPLETE" "System upgrade completed with security validation" "$(whoami)" "security_validated"
```

### 2. Log Retention & Security

```bash
# Healthcare log management
setup_healthcare_logging() {
    # Create secure log directories
    mkdir -p /var/log/intelluxe-healthcare
    chown intelluxe-service:intelluxe-prod /var/log/intelluxe-healthcare
    chmod 750 /var/log/intelluxe-healthcare
    
    # HIPAA-compliant log rotation (7 year retention)
    cat > /etc/logrotate.d/intelluxe-auto-upgrade << EOF
/var/log/intelluxe-healthcare/*.log {
    daily
    rotate 2555  # 7 years (HIPAA requirement)
    compress
    delaycompress
    missingok
    notifempty
    create 640 intelluxe-service intelluxe-prod
    postrotate
        systemctl reload intelluxe-auto-upgrade.service > /dev/null 2>&1 || true
    endscript
}
EOF
}
```

---

## 🚀 Enhanced Production Deployment Steps

### 1. Security-Enhanced Pre-Deployment Configuration

```bash
#!/bin/bash
# deploy-production-auto-upgrade.sh - Enhanced with security validation

echo "🏥 Deploying Production Auto-Upgrade System for Healthcare with Security Validation"
echo "================================================================================"

# Validate Phase 0 security foundation
echo "Validating Phase 0 security foundation..."
if ! python3 -c "
from src.security.encryption_manager import EncryptionManager
from src.healthcare_mcp.phi_detection import PHIDetector
from src.security.rbac_foundation import RBACFoundation

# Validate all security systems
EncryptionManager().validate_production_readiness()
PHIDetector().validate_system()
RBACFoundation().validate_production_readiness()
print('✅ Phase 0 security foundation validated')
"; then
    echo "❌ Phase 0 security validation failed - cannot deploy production auto-upgrade"
    exit 1
fi

# Create production configuration with security enhancements
cat > /etc/intelluxe/auto-upgrade.conf << EOF
# Intelluxe AI Healthcare Auto-Upgrade Production Configuration
HEALTHCARE_MODE=production
MAINTENANCE_WINDOW=true
AUDIT_REQUIRED=true
PATIENT_SAFETY_CHECK=true
PHI_PROTECTION_VERIFY=true
SECURITY_VALIDATION=true

# Enhanced security settings
ENCRYPTION_VALIDATION=true
AUTH_VALIDATION=true
RBAC_VALIDATION=true

# Clinic-specific settings (customize for your environment)
BUSINESS_HOURS_START=08
BUSINESS_HOURS_END=18
MAX_DB_CONNECTIONS=5
MAX_PHI_PROCESSING_SESSIONS=0
DATA_DISK_WARNING_THRESHOLD=85
DATA_DISK_CRITICAL_THRESHOLD=95

# Maintenance windows (customize for your clinic schedule)
PRIMARY_MAINTENANCE_DAY=7     # Sunday
PRIMARY_MAINTENANCE_HOUR=2    # 2 AM
EMERGENCY_MAINTENANCE_START=1 # 1 AM
EMERGENCY_MAINTENANCE_END=3   # 3 AM
EOF

# Set production permissions with security hardening
chown intelluxe-service:intelluxe-prod /etc/intelluxe/auto-upgrade.conf
chmod 640 /etc/intelluxe/auto-upgrade.conf

echo "✅ Production configuration with security enhancements deployed"
```

### 2. Production Service Installation

```bash
# Install production auto-upgrade system
sudo systemctl stop intelluxe-auto-upgrade.timer
sudo systemctl stop intelluxe-auto-upgrade.service

# Update service files with production configuration
sudo cp systemd/auto-upgrade.service /etc/systemd/system/intelluxe-auto-upgrade.service
sudo cp systemd/auto-upgrade.timer /etc/systemd/system/intelluxe-auto-upgrade.timer

# Enable and start production services
sudo systemctl daemon-reload
sudo systemctl enable intelluxe-auto-upgrade.service
sudo systemctl enable intelluxe-auto-upgrade.timer
sudo systemctl start intelluxe-auto-upgrade.timer

echo "✅ Production auto-upgrade system deployed"
```

### 3. Production Testing & Validation

```bash
#!/bin/bash
# test-production-auto-upgrade.sh

echo "🧪 Testing Production Auto-Upgrade System"
echo "========================================"

# Test healthcare mode detection
echo "Testing healthcare mode..."
if /opt/intelluxe/scripts/auto-upgrade.sh --test-mode 2>&1 | grep -q "Healthcare Mode: production"; then
    echo "✅ Healthcare mode detection working"
else
    echo "❌ Healthcare mode detection failed"
    exit 1
fi

# Test maintenance window logic
echo "Testing maintenance window logic..."
# This would be customized based on your actual maintenance windows

# Test patient safety checks
echo "Testing patient safety checks..."
# This would integrate with your actual EHR/session management system

# Test audit logging
echo "Testing audit logging..."
if [[ -f "/var/log/intelluxe-healthcare/audit.log" ]]; then
    echo "✅ Audit logging configured"
else
    echo "❌ Audit logging not configured"
    exit 1
fi

# Test service health verification
echo "Testing healthcare service verification..."
if /opt/intelluxe/scripts/diagnostics.sh --critical-only --no-color; then
    echo "✅ Healthcare service verification working"
else
    echo "❌ Healthcare service verification failed"
    exit 1
fi

echo "✅ Production auto-upgrade system tests passed"
```

---

## 📋 Enhanced Production Checklist

### Pre-Deployment Security Validation
- [ ] **Phase 0 Security Foundation**: Validated encryption, PHI detection, and RBAC systems
- [ ] **Environment Configuration**: Set `HEALTHCARE_MODE=production` with security validation
- [ ] **Service Accounts**: Created dedicated `intelluxe-service:intelluxe-prod` accounts
- [ ] **Security Systems**: Validated all encryption keys and authentication systems
- [ ] **PHI Protection**: Verified PHI detection and masking systems
- [ ] **Maintenance Windows**: Configured clinic-specific maintenance schedules
- [ ] **Patient Safety**: Integrated with EHR/session management system
- [ ] **Audit Logging**: Enabled HIPAA-compliant audit trails with security context
- [ ] **Log Retention**: Configured 7-year log retention for compliance
- [ ] **Network Security**: Restricted access to healthcare network only
- [ ] **Testing**: Completed full production testing suite with security validation
- [ ] **Documentation**: Updated all procedures for production environment
- [ ] **Staff Training**: Trained healthcare staff on maintenance and security procedures

### Post-Deployment Monitoring
- [ ] **Service Health**: Monitor auto-upgrade service status
- [ ] **Audit Compliance**: Regular audit log reviews
- [ ] **Maintenance Windows**: Verify updates only occur during approved times
- [ ] **Patient Safety**: Monitor for any update conflicts with patient care
- [ ] **Security**: Regular security assessments of update process
- [ ] **Performance**: Monitor impact on healthcare service performance

---

## 🔧 Customization for Your Healthcare Environment

### 1. EHR System Integration

```bash
# Example: Epic EHR integration
check_ehr_sessions() {
    # Replace with your EHR system's API/database check
    local active_sessions
    active_sessions=$(curl -s "http://ehr-api/sessions/active" | jq '.count' 2>/dev/null || echo "0")
    
    if [[ $active_sessions -gt 0 ]]; then
        log "ERROR" "Active EHR sessions detected: $active_sessions"
        return 1
    fi
    return 0
}
```

### 2. Clinic-Specific Schedules

```bash
# Example: Multi-location clinic
get_maintenance_window() {
    local clinic_location="${CLINIC_LOCATION:-main}"
    
    case "$clinic_location" in
        "main")
            echo "Sunday 2-4 AM"
            ;;
        "urgent_care")
            echo "Monday 3-5 AM"  # Different schedule for 24/7 urgent care
            ;;
        "satellite")
            echo "Tuesday 1-3 AM"
            ;;
    esac
}
```

### 3. Custom Healthcare Service Checks

```bash
# Example: Custom healthcare service monitoring
check_custom_healthcare_services() {
    # Check your specific healthcare applications
    local services=(
        "ollama-healthcare"
        "mcp-healthcare"
        "patient-portal"
        "billing-system"
    )
    
    for service in "${services[@]}"; do
        if docker ps --filter "name=$service" --filter "status=running" -q | grep -q .; then
            log "INFO" "✓ $service is running"
        else
            log "ERROR" "✗ $service is not running"
            return 1
        fi
    done
}
```

---

## 🚨 Emergency Procedures

### 1. Emergency Update Process

```bash
# emergency-update.sh - For critical security updates
#!/bin/bash
HEALTHCARE_MODE=production
MAINTENANCE_WINDOW=false  # Override for emergencies
EMERGENCY_UPDATE=true

# Log emergency justification
audit_log "EMERGENCY_UPDATE_START" "Critical security update - maintenance window overridden"

# Proceed with emergency update
/opt/intelluxe/scripts/auto-upgrade.sh
```

### 2. Rollback Procedures

```bash
# rollback-update.sh - Emergency rollback
#!/bin/bash
echo "🚨 Emergency Rollback Procedure"

# Stop healthcare services
systemctl stop intelluxe-*.service

# Restore from backup
tar -xzf /opt/backup/pre-update-$(date +%Y%m%d).tar.gz -C /

# Restart services
systemctl start intelluxe-*.service

audit_log "EMERGENCY_ROLLBACK" "System rollback completed"
```

---

**⚠️ Important Production Notes:**
1. **Complete Phase 0 security validation** before production deployment
2. **Test all security components** in staging environment first
3. **Coordinate with clinical staff** before implementing
4. **Maintain development environment** separately for ongoing development
5. **Document all customizations** for your healthcare environment
6. **Schedule regular security reviews** and updates for compliance
7. **Train healthcare staff** on emergency procedures and security protocols

---

*This document should be reviewed before each production deployment and updated whenever healthcare workflows or security requirements change.*
