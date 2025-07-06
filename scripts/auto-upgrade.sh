#!/bin/bash
# Auto-upgrade script for Intelluxe AI healthcare system
# Performs system updates and logs results

set -euo pipefail

# Configuration
LOG_FILE="/var/log/auto-upgrade.log"
LOCK_FILE="/var/run/auto-upgrade.lock"
NOTIFY_ON_REBOOT_REQUIRED=true

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $*" | tee -a "$LOG_FILE"
}

# Check if another upgrade is running
if [ -f "$LOCK_FILE" ]; then
    log "ERROR: Another upgrade process is already running"
    exit 1
fi

# Create lock file
echo $$ > "$LOCK_FILE"

# Cleanup function
cleanup() {
    rm -f "$LOCK_FILE"
}
trap cleanup EXIT

log "Starting auto-upgrade process"

# Update package lists
log "Updating package lists..."
if apt update; then
    log "Package lists updated successfully"
else
    log "ERROR: Failed to update package lists"
    exit 1
fi

# Perform full upgrade
log "Starting full system upgrade..."
if DEBIAN_FRONTEND=noninteractive apt full-upgrade -y; then
    log "System upgrade completed successfully"
else
    log "ERROR: System upgrade failed"
    exit 1
fi

# Clean up package cache
log "Cleaning up package cache..."
apt autoremove -y
apt autoclean

# Check if reboot is required
if [ -f /var/run/reboot-required ]; then
    log "NOTICE: System reboot is required after upgrade"
    if [ "$NOTIFY_ON_REBOOT_REQUIRED" = true ]; then
        # You can add notification logic here (email, webhook, etc.)
        echo "Reboot required after system upgrade" > /tmp/reboot-required-notification
    fi
else
    log "No reboot required"
fi

log "Auto-upgrade process completed successfully"
