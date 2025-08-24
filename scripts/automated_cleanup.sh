#!/bin/bash
"""
Automated Medical Data Cleanup Script

This script can be run periodically (e.g., via cron) to automatically
clean up duplicate uncompressed files and maintain optimal storage usage.

Usage:
  ./automated_cleanup.sh [--dry-run] [--force]

Options:
  --dry-run  Preview changes without executing (default)
  --force    Execute actual cleanup (required for real cleanup)

Example cron job (weekly cleanup on Sundays at 3 AM):
  0 3 * * 0 /home/intelluxe/scripts/automated_cleanup.sh --force >> /var/log/medical_cleanup.log 2>&1
"""

set -euo pipefail

# Configuration
DATA_DIR="/home/intelluxe/database/medical_complete"
SCRIPT_DIR="/home/intelluxe/scripts"
LOG_FILE="/var/log/medical_cleanup.log"
MAX_LOG_SIZE="10M"

# Default to dry-run for safety
DRY_RUN="true"
FORCE="false"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN="true"
            shift
            ;;
        --force)
            FORCE="true"
            DRY_RUN="false"
            shift
            ;;
        --help|-h)
            echo "Automated Medical Data Cleanup"
            echo "Usage: $0 [--dry-run] [--force]"
            echo "Options:"
            echo "  --dry-run  Preview changes without executing (default)"
            echo "  --force    Execute actual cleanup"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Safety check
if [[ "$FORCE" != "true" ]] && [[ "$DRY_RUN" != "true" ]]; then
    echo "ERROR: Must specify either --dry-run or --force"
    exit 1
fi

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Rotate log file if it gets too large
rotate_log() {
    if [[ -f "$LOG_FILE" ]] && [[ $(stat -c%s "$LOG_FILE") -gt $(numfmt --from=iec "$MAX_LOG_SIZE") ]]; then
        mv "$LOG_FILE" "${LOG_FILE}.old"
        log "Log file rotated"
    fi
}

# Check disk space and determine if cleanup is needed
check_disk_space() {
    local usage_percent
    usage_percent=$(df "$DATA_DIR" | awk 'NR==2 {gsub(/%/, "", $5); print $5}')
    
    log "Current disk usage: ${usage_percent}%"
    
    # Only proceed with cleanup if disk usage is above threshold
    if [[ "$usage_percent" -lt 70 ]] && [[ "$FORCE" != "true" ]]; then
        log "Disk usage below 70% threshold - skipping cleanup"
        return 1
    fi
    
    return 0
}

# Run disk space monitoring
monitor_disk_space() {
    log "Generating disk usage report..."
    if python3 "$SCRIPT_DIR/disk_space_monitor.py" "$DATA_DIR" --save-report >> "$LOG_FILE" 2>&1; then
        log "Disk usage report generated successfully"
    else
        log "ERROR: Failed to generate disk usage report"
    fi
}

# Main cleanup function
run_cleanup() {
    local cleanup_args=""
    
    if [[ "$DRY_RUN" == "true" ]]; then
        cleanup_args="--dry-run"
        log "Starting AUTOMATED CLEANUP (DRY-RUN MODE)"
    else
        cleanup_args="--execute"
        log "Starting AUTOMATED CLEANUP (EXECUTION MODE)"
    fi
    
    # Run the cleanup script
    if echo "yes" | python3 "$SCRIPT_DIR/cleanup_medical_downloads.py" "$DATA_DIR" $cleanup_args >> "$LOG_FILE" 2>&1; then
        log "Cleanup completed successfully"
        
        # Monitor disk space after cleanup
        monitor_disk_space
        
        return 0
    else
        log "ERROR: Cleanup failed with exit code $?"
        return 1
    fi
}

# Verify prerequisites
verify_prerequisites() {
    local missing_files=()
    
    # Check if required scripts exist
    if [[ ! -f "$SCRIPT_DIR/cleanup_medical_downloads.py" ]]; then
        missing_files+=("cleanup_medical_downloads.py")
    fi
    
    if [[ ! -f "$SCRIPT_DIR/disk_space_monitor.py" ]]; then
        missing_files+=("disk_space_monitor.py")
    fi
    
    if [[ ! -d "$DATA_DIR" ]]; then
        missing_files+=("data directory: $DATA_DIR")
    fi
    
    if [[ ${#missing_files[@]} -gt 0 ]]; then
        log "ERROR: Missing required files/directories:"
        for file in "${missing_files[@]}"; do
            log "  - $file"
        done
        return 1
    fi
    
    return 0
}

# Main execution
main() {
    # Initialize logging
    rotate_log
    log "========================================"
    log "Automated Medical Data Cleanup Started"
    log "Mode: $([ "$DRY_RUN" == "true" ] && echo "DRY-RUN" || echo "EXECUTION")"
    log "Data Directory: $DATA_DIR"
    
    # Verify prerequisites
    if ! verify_prerequisites; then
        log "Prerequisites check failed - aborting"
        exit 1
    fi
    
    # Check if cleanup is needed (unless forced)
    if [[ "$FORCE" != "true" ]] && ! check_disk_space; then
        log "Cleanup not needed at this time"
        log "Automated cleanup completed (no action taken)"
        exit 0
    fi
    
    # Run the cleanup
    if run_cleanup; then
        log "Automated cleanup completed successfully"
        exit 0
    else
        log "Automated cleanup failed"
        exit 1
    fi
}

# Execute main function
main "$@"