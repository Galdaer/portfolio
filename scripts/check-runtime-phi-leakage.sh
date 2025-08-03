#!/usr/bin/env bash
# Runtime PHI Leakage Detection Script for Intelluxe AI
# Monitors logs, outputs, and data pipeline artifacts for PHI exposure

set -euo pipefail

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib.sh
source "$SCRIPT_DIR/lib.sh"

log "🔍 Starting runtime PHI leakage scan for data pipelines and outputs"

# Critical PHI patterns that should NEVER appear in logs/outputs
declare -a critical_phi_patterns=(
    # Real SSN patterns (excluding synthetic 555-XX-XXXX)
    "[0-9]{3}-[0-9]{2}-[0-9]{4}.*(?!555-[0-9]{2}-[0-9]{4})"
    "[0-9]{9}.*SSN"
    
    # Real medical record numbers (excluding synthetic patterns)
    "MRN.*[0-9]{6,10}.*(?!PAT[0-9]{3})"
    
    # Real dates of birth (excluding test dates)
    "[0-9]{2}/[0-9]{2}/(19|20)[0-9]{2}.*(?!01/01/1990)"
    
    # Real phone numbers (excluding 555 test numbers)
    "[0-9]{3}-[0-9]{3}-[0-9]{4}.*(?!555-[0-9]{3}-[0-9]{4})"
    
    # Insurance numbers in logs
    "Insurance.*ID.*[A-Z0-9]{9,15}"
    
    # Database connection strings with PHI
    "patient_data.*password="
    "phi_db.*credentials"
)

# Data pipeline monitoring patterns
declare -a pipeline_patterns=(
    # Database query results in logs
    "SELECT.*FROM.*patient"
    "INSERT.*INTO.*patient"
    "UPDATE.*patient.*SET"
    
    # API responses with patient data
    '"patient_id".*[0-9]+'
    '"medical_record".*[0-9]+'
    
    # Debugging output with PHI
    "DEBUG.*patient.*data"
    "TRACE.*medical.*record"
    
    # Error messages with PHI
    "ERROR.*patient.*[0-9]+"
    "EXCEPTION.*medical.*data"
)

# Safe synthetic data patterns (EXCLUDE from alerts)
declare -a safe_synthetic_patterns=(
    "PAT[0-9]{3}"           # Patient IDs like PAT001
    "PROV[0-9]{3}"          # Provider IDs like PROV001  
    "ENC[0-9]{3}"           # Encounter IDs like ENC001
    "555-[0-9]{3}-[0-9]{4}" # 555 test phone numbers
    "01/01/1990"            # Standard test DOB
    "test@example.com"      # Test emails
    "synthetic.*true"       # Synthetic data markers
    "demo.*patient"         # Demo patient data
    "test.*data"            # Test data markers
)

found_issues=0
warnings=0

# Directories to scan for runtime outputs
declare -a runtime_dirs=(
    "logs/"
    "data/evaluation/"
    "coverage/"
    ".pytest_cache/"
    "__pycache__/"
)

# File patterns to scan (runtime outputs, not source code)
declare -a runtime_file_patterns=(
    "*.log"
    "*.out"
    "*.err"
    "*.trace"
    "*.debug"
    "*.output"
    "*.json"  # Runtime JSON outputs
    "*.csv"   # Data export files
    "*.txt"   # Log files
)

# Function to check if a match is safe synthetic data
is_safe_synthetic() {
    local match="$1"
    
    for pattern in "${safe_synthetic_patterns[@]}"; do
        if echo "$match" | grep -q -i -E "$pattern"; then
            return 0  # It's safe synthetic data
        fi
    done
    
    return 1  # Not synthetic data - potential PHI
}

# Function to scan runtime outputs for PHI leakage
scan_runtime_phi() {
    local pattern_array=("$@")
    local pattern_type="$1"
    shift
    
    log "🔍 Scanning runtime outputs for $pattern_type patterns..."
    
    for dir in "${runtime_dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            continue
        fi
        
        for file_pattern in "${runtime_file_patterns[@]}"; do
            while IFS= read -r -d '' file; do
                [[ -f "$file" ]] || continue
                
                for pattern in "${pattern_array[@]}"; do
                    while IFS= read -r line; do
                        line_num=$(echo "$line" | cut -d: -f1)
                        match=$(echo "$line" | cut -d: -f2-)
                        
                        # Skip if it's safe synthetic data
                        if is_safe_synthetic "$match"; then
                            continue
                        fi
                        
                        # Found potential PHI leakage
                        echo "🚨 CRITICAL: Potential PHI leakage detected!"
                        echo "   File: $file:$line_num"
                        echo "   Pattern: $pattern"
                        echo "   Content: $match"
                        echo ""
                        ((found_issues++))
                        
                    done < <(grep -n -i -E "$pattern" "$file" 2>/dev/null || true)
                done
            done < <(find "$dir" -name "$file_pattern" -type f -print0 2>/dev/null)
        done
    done
}

# Function to check database connection security
check_db_connections() {
    log "🔍 Checking database connection security..."
    
    # Check for database credentials in logs
    for dir in "${runtime_dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            continue
        fi
        
        # Look for database connection strings with credentials
        while IFS= read -r -d '' file; do
            [[ -f "$file" ]] || continue
            
            # Check for exposed database URLs
            if grep -q -E "(postgresql|mysql|redis)://.*:.*@" "$file" 2>/dev/null; then
                echo "⚠️  WARNING: Database credentials found in runtime output!"
                echo "   File: $file"
                ((warnings++))
            fi
            
            # Check for raw SQL with patient data
            if grep -q -E "SELECT.*FROM.*(patient|medical_record)" "$file" 2>/dev/null; then
                echo "⚠️  WARNING: Raw SQL queries with patient data in logs!"
                echo "   File: $file"
                ((warnings++))
            fi
            
        done < <(find "$dir" -name "*.log" -o -name "*.out" -o -name "*.err" -print0 2>/dev/null)
    done
}

# Function to check for data export violations
check_data_exports() {
    log "🔍 Checking for unauthorized data exports..."
    
    # Look for CSV/JSON exports that might contain PHI
    while IFS= read -r -d '' file; do
        [[ -f "$file" ]] || continue
        
        file_size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo "0")
        
        # Large data files might contain PHI exports
        if [[ $file_size -gt 1048576 ]]; then  # > 1MB
            echo "⚠️  WARNING: Large data export file detected (potential PHI)!"
            echo "   File: $file (${file_size} bytes)"
            echo "   Please verify this file contains only synthetic data"
            ((warnings++))
        fi
        
    done < <(find . -name "*.csv" -o -name "*.json" -o -name "*.xlsx" -print0 2>/dev/null)
}

# Main scanning logic
main() {
    log "🏥 Intelluxe AI Runtime PHI Leakage Detection"
    log "Scanning data pipelines, logs, and outputs for PHI exposure..."
    
    # Scan for critical PHI patterns in runtime outputs
    scan_runtime_phi "${critical_phi_patterns[@]}" "Critical PHI"
    
    # Scan for data pipeline issues
    scan_runtime_phi "${pipeline_patterns[@]}" "Data Pipeline"
    
    # Check database connection security
    check_db_connections
    
    # Check for unauthorized data exports
    check_data_exports
    
    # Report results
    echo ""
    log "📊 Runtime PHI Leakage Scan Results:"
    log "   Critical Issues: $found_issues"
    log "   Warnings: $warnings"
    
    if [[ $found_issues -gt 0 ]]; then
        log "❌ CRITICAL: PHI leakage detected in runtime outputs!"
        log "   Please review and remediate immediately for HIPAA compliance"
        exit 1
    elif [[ $warnings -gt 0 ]]; then
        log "⚠️  Warnings found - please review for potential PHI exposure"
        exit 0
    else
        log "✅ No PHI leakage detected in runtime outputs"
        exit 0
    fi
}

# Run if called directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
