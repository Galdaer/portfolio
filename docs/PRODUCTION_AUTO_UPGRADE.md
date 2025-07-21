# Production Auto-Upgrade System for Healthcare Environments

**Document Version**: 1.0.0  
**Target Audience**: Healthcare System Administrators, DevOps Engineers  
**Phase**: Production Deployment (Phase 3)  
**Component**: Auto-Upgrade System (`auto-upgrade.sh`, `auto-upgrade.service`, `auto-upgrade.timer`)  
**Last Updated**: July 16, 2025

## Overview

This document outlines the production-ready auto-upgrade system for Intelluxe AI Healthcare environments. The auto-upgrade system automatically updates system packages while maintaining healthcare safety protocols and HIPAA compliance requirements.

⚠️ **Healthcare Safety Notice**: This system is designed to update ONLY system packages, never medical services or patient data systems.

## 🏥 Healthcare Environment Modes

### Development Mode (Current - Phase 0-2)
- **Purpose**: Rapid development and testing
- **Safety Checks**: Minimal (basic disk space, lock files)
- **Schedule**: Weekly (Sunday 2 AM)
- **Audit Logging**: Optional
- **Patient Safety**: Disabled

### Production Mode (Phase 3+)
- **Purpose**: Live clinical deployment
- **Safety Checks**: Full healthcare protocols
- **Schedule**: Maintenance windows only
- **Audit Logging**: Required (HIPAA compliance)
- **Patient Safety**: Active session monitoring

---

## 🔧 Production Configuration Files

### 1. Enhanced Auto-Upgrade Script (`auto-upgrade.sh`)

**Key Production Features:**
- **Healthcare Mode Detection**: Automatically adjusts behavior based on environment
- **Patient Safety Checks**: Prevents updates during active patient sessions
- **Maintenance Windows**: Only allows updates during approved maintenance times
- **HIPAA Audit Logging**: Complete audit trail for compliance
- **Service Health Verification**: Checks critical healthcare services before/after updates

```bash
# Production environment variables
HEALTHCARE_MODE=production          # development|staging|production
MAINTENANCE_WINDOW=true            # Only update during maintenance windows
AUDIT_REQUIRED=true               # HIPAA compliance audit logging
PATIENT_SAFETY_CHECK=true         # Check for active patient sessions
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

## 🛡️ Healthcare Safety Protocols

### 1. Patient Safety Checks

```bash
# Production patient safety verification
check_patient_safety() {
    log "INFO" "Checking for active patient sessions..."
    
    # Check healthcare service containers
    if docker ps --filter "label=intelluxe.service=healthcare" --filter "status=running" -q | grep -q .; then
        log "WARN" "Healthcare services active - checking session status"
        
        # Production integration points:
        # - EHR system session monitoring
        # - Active appointment checking
        # - Patient data processing status
        
        # Business hours check (customize for your clinic)
        local current_hour
        current_hour=$(date +%H)
        if [[ $current_hour -ge 8 && $current_hour -le 18 ]]; then
            log "ERROR" "Updates blocked: Potential active sessions during business hours"
            return 1
        fi
    fi
    
    # Check for active database transactions
    if systemctl is-active --quiet postgresql; then
        local active_connections
        active_connections=$(sudo -u postgres psql -t -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';" 2>/dev/null || echo "0")
        if [[ $active_connections -gt 5 ]]; then  # Adjust threshold for your environment
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

### 2. Maintenance Window Configuration

```bash
# Healthcare maintenance windows
check_maintenance_window() {
    if [[ "$MAINTENANCE_WINDOW" == "true" ]]; then
        local current_day current_hour current_minute
        current_day=$(date +%u)    # 1-7 (Monday-Sunday)
        current_hour=$(date +%H)   # 00-23
        current_minute=$(date +%M) # 00-59
        
        # Primary maintenance window: Sunday 2-4 AM
        if [[ "$current_day" -eq 7 ]] && [[ $current_hour -ge 2 && $current_hour -le 4 ]]; then
            log "INFO" "Within primary maintenance window (Sunday 2-4 AM)"
            return 0
        fi
        
        # Emergency maintenance window: Any day 1-3 AM (for critical security updates)
        if [[ $current_hour -ge 1 && $current_hour -le 3 ]]; then
            log "INFO" "Within emergency maintenance window (1-3 AM)"
            return 0
        fi
        
        # Outside maintenance windows
        log "WARN" "Outside maintenance window - current time: $(date)"
        if [[ "$HEALTHCARE_MODE" == "production" ]]; then
            log "ERROR" "Production updates blocked outside maintenance window"
            return 1
        fi
    fi
    return 0
}
```

### 3. Healthcare Service Health Verification

```bash
# Pre/post update healthcare service verification
verify_healthcare_services() {
    local check_type="$1"  # "pre" or "post"
    
    log "INFO" "Running $check_type-update healthcare service verification..."
    
    # Critical healthcare services that must remain healthy
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
    
    # Check healthcare Docker containers
    if command -v docker >/dev/null 2>&1; then
        local unhealthy_containers
        unhealthy_containers=$(docker ps --filter "label=intelluxe.healthcare=true" --filter "health=unhealthy" -q | wc -l)
        if [[ $unhealthy_containers -gt 0 ]]; then
            log "ERROR" "Found $unhealthy_containers unhealthy healthcare containers"
            return 1
        fi
        
        local healthcare_containers
        healthcare_containers=$(docker ps --filter "label=intelluxe.healthcare=true" -q | wc -l)
        log "INFO" "✓ $healthcare_containers healthcare containers running and healthy"
    fi
    
    # Check disk space for healthcare data
    local data_disk_usage
    data_disk_usage=$(df /opt/intelluxe/stack/data 2>/dev/null | awk 'NR==2 {print $5}' | tr -d '%' || echo "0")
    if [[ $data_disk_usage -gt 85 ]]; then
        log "WARN" "Healthcare data disk usage high: $data_disk_usage%"
        if [[ $data_disk_usage -gt 95 ]]; then
            log "ERROR" "Critical: Healthcare data disk usage: $data_disk_usage%"
            return 1
        fi
    fi
    
    log "INFO" "$check_type-update healthcare service verification passed"
    return 0
}
```

---

## 📊 HIPAA Compliance & Audit Logging

### 1. Audit Log Format

```bash
# HIPAA-compliant audit logging
audit_log() {
    local action="$1"
    local details="$2"
    local user="${3:-$(whoami)}"
    local timestamp
    timestamp=$(date --iso-8601=seconds)
    
    # HIPAA audit trail format
    cat >> "$AUDIT_LOG" << EOF
{
  "timestamp": "$timestamp",
  "system": "intelluxe-auto-upgrade",
  "action": "$action",
  "details": "$details",
  "user": "$user",
  "pid": "$$",
  "mode": "$HEALTHCARE_MODE",
  "compliance": "HIPAA"
}
EOF
}

# Example audit events
audit_log "UPGRADE_START" "System package upgrade initiated"
audit_log "PATIENT_SAFETY_CHECK" "Active session check completed: no active sessions"
audit_log "PACKAGE_UPGRADE" "$(apt list --upgradable 2>/dev/null | wc -l) packages upgraded"
audit_log "UPGRADE_COMPLETE" "System upgrade completed successfully"
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

## 🚀 Production Deployment Steps

### 1. Pre-Deployment Configuration

```bash
#!/bin/bash
# deploy-production-auto-upgrade.sh

echo "🏥 Deploying Production Auto-Upgrade System for Healthcare"
echo "========================================================"

# Create production configuration
cat > /etc/intelluxe/auto-upgrade.conf << EOF
# Intelluxe AI Healthcare Auto-Upgrade Production Configuration
HEALTHCARE_MODE=production
MAINTENANCE_WINDOW=true
AUDIT_REQUIRED=true
PATIENT_SAFETY_CHECK=true

# Clinic-specific settings (customize for your environment)
BUSINESS_HOURS_START=08
BUSINESS_HOURS_END=18
MAX_DB_CONNECTIONS=5
DATA_DISK_WARNING_THRESHOLD=85
DATA_DISK_CRITICAL_THRESHOLD=95

# Maintenance windows (customize for your clinic schedule)
PRIMARY_MAINTENANCE_DAY=7     # Sunday
PRIMARY_MAINTENANCE_HOUR=2    # 2 AM
EMERGENCY_MAINTENANCE_START=1 # 1 AM
EMERGENCY_MAINTENANCE_END=3   # 3 AM
EOF

# Set production permissions
chown intelluxe-service:intelluxe-prod /etc/intelluxe/auto-upgrade.conf
chmod 640 /etc/intelluxe/auto-upgrade.conf

echo "✅ Production configuration deployed"
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

## 📋 Production Checklist

### Pre-Deployment Checklist
- [ ] **Environment Configuration**: Set `HEALTHCARE_MODE=production` in all configs
- [ ] **Service Accounts**: Created dedicated `intelluxe-service:intelluxe-prod` accounts
- [ ] **Maintenance Windows**: Configured clinic-specific maintenance schedules
- [ ] **Patient Safety**: Integrated with EHR/session management system
- [ ] **Audit Logging**: Enabled HIPAA-compliant audit trails
- [ ] **Log Retention**: Configured 7-year log retention for compliance
- [ ] **Network Security**: Restricted access to healthcare network only
- [ ] **Testing**: Completed full production testing suite
- [ ] **Documentation**: Updated all procedures for production environment
- [ ] **Staff Training**: Trained healthcare staff on maintenance procedures

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
1. **Test thoroughly in staging environment first**
2. **Coordinate with clinical staff before deployment**
3. **Maintain development environment separately**
4. **Document all customizations for your healthcare environment**
5. **Schedule regular reviews and updates for compliance**
6. **Train healthcare staff on emergency procedures**

---

*This document should be reviewed before each production deployment and updated whenever healthcare workflows change.*
