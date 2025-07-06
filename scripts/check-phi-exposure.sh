#!/usr/bin/env bash
# PHI Exposure Detection Script for Intelluxe AI
# Scans codebase for potential Protected Health Information (PHI) exposure

set -euo pipefail

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/clinic-lib.sh
source "$SCRIPT_DIR/clinic-lib.sh"

log "🔍 Starting PHI exposure scan for Intelluxe AI healthcare platform"

# PHI patterns to detect (HIPAA identifiers)
declare -a phi_patterns=(
    # Social Security Numbers
    "ssn.*[0-9]{3}-[0-9]{2}-[0-9]{4}"
    "social.*security.*[0-9]{9}"
    "ss#.*[0-9]{3}-[0-9]{2}-[0-9]{4}"
    
    # Medical Record Numbers
    "mrn.*[0-9]{6,10}"
    "medical.*record.*number.*[0-9]+"
    "patient.*id.*[0-9]{6,10}"
    
    # Dates of Birth
    "dob.*[0-9]{2}/[0-9]{2}/[0-9]{4}"
    "date.*birth.*[0-9]{2}/[0-9]{2}/[0-9]{4}"
    "birth.*date.*[0-9]{2}/[0-9]{2}/[0-9]{4}"
    
    # Phone Numbers (medical context)
    "patient.*phone.*[0-9]{3}-[0-9]{3}-[0-9]{4}"
    "emergency.*contact.*[0-9]{10}"
    
    # Email in medical context
    "patient.*email.*[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    
    # Insurance Numbers
    "insurance.*number.*[A-Z0-9]{9,12}"
    "policy.*number.*[A-Z0-9]{8,15}"
    
    # Medical Device Identifiers
    "device.*serial.*[A-Z0-9]{8,20}"
    "implant.*id.*[A-Z0-9]{8,15}"
)

# Sensitive healthcare terms that shouldn't be in logs or hardcoded
declare -a sensitive_terms=(
    "diagnosis"
    "prescription"
    "medication"
    "treatment"
    "symptom"
    "condition"
    "procedure"
    "surgery"
    "therapy"
    "counseling"
    "mental.?health"
    "substance.?abuse"
    "hiv"
    "aids"
    "cancer"
    "pregnancy"
    "psychiatric"
    "psychological"
)

# Test data patterns that might accidentally contain real-looking PHI
declare -a test_data_patterns=(
    "john.*doe"
    "jane.*smith"
    "test.*patient"
    "sample.*patient"
    "demo.*patient"
    "fake.*patient"
    "123-45-6789"  # Common test SSN
    "555-555-5555" # Common test phone
    "test@example.com"
)

found_issues=0
warnings=0

# Function to scan for patterns
scan_patterns() {
    local pattern_array=("$@")
    local pattern_type="$1"
    shift
    
    log "Scanning for $pattern_type patterns..."
    
    for pattern in "${pattern_array[@]}"; do
        if grep -r -i -E "$pattern" \
           --include="*.py" --include="*.sh" --include="*.js" --include="*.txt" --include="*.yml" --include="*.yaml" \
           --exclude-dir=".git" --exclude-dir="test" --exclude-dir="docs" --exclude-dir="coverage" \
           --exclude-dir="logs" --exclude-dir=".vscode" \
           . 2>/dev/null; then
            warn "Found potential $pattern_type pattern: $pattern"
            found_issues=$((found_issues + 1))
        fi
    done
}

# Function to check for sensitive terms in logs/print statements
check_logging_exposure() {
    log "Checking for sensitive terms in logging statements..."
    
    for term in "${sensitive_terms[@]}"; do
        # Check for print/log statements with sensitive terms
        if grep -r -i -E "(print|log|echo|printf).*$term" \
           --include="*.py" --include="*.sh" --include="*.js" \
           --exclude-dir=".git" --exclude-dir="test" --exclude-dir="docs" \
           . 2>/dev/null; then
            warn "Found potential PHI in logging: $term"
            warnings=$((warnings + 1))
        fi
    done
}

# Function to check for hardcoded credentials that might access PHI
check_hardcoded_credentials() {
    log "Checking for hardcoded credentials that might access PHI..."
    
    if grep -r -i -E "(password|secret|key|token)\s*=\s*['\"][^'\"]*['\"]" \
       --include="*.py" --include="*.sh" --include="*.yml" --include="*.yaml" \
       --exclude-dir=".git" --exclude-dir="test" \
       . 2>/dev/null; then
        warn "Found hardcoded credentials - ensure these don't access PHI systems"
        warnings=$((warnings + 1))
    fi
}

# Function to check for test data in non-test files
check_test_data_exposure() {
    log "Checking for test PHI data in production code..."
    
    for pattern in "${test_data_patterns[@]}"; do
        if grep -r -i -E "$pattern" \
           --include="*.py" --include="*.sh" --include="*.js" \
           --exclude-dir=".git" --exclude-dir="test" --exclude-dir="docs" \
           . 2>/dev/null; then
            warn "Found potential test PHI data in non-test files: $pattern"
            warnings=$((warnings + 1))
        fi
    done
}

# Function to check for insecure configurations
check_insecure_configs() {
    log "Checking for insecure configurations..."
    
    # Check for debug mode in production
    if grep -r -i -E "(debug\s*=\s*true|debug.*mode.*true)" \
       --include="*.py" --include="*.sh" --include="*.yml" --include="*.yaml" \
       --exclude-dir=".git" --exclude-dir="test" \
       . 2>/dev/null; then
        warn "Debug mode enabled - may expose PHI in logs"
        warnings=$((warnings + 1))
    fi
    
    # Check for development URLs in production code
    if grep -r -i -E "(localhost|127\.0\.0\.1|0\.0\.0\.0)" \
       --include="*.py" --include="*.sh" --include="*.yml" --include="*.yaml" \
       --exclude-dir=".git" --exclude-dir="test" --exclude-dir="docs" \
       . 2>/dev/null | grep -v "# Development only" | grep -v "# Test only"; then
        warn "Found localhost/development URLs in production code"
        warnings=$((warnings + 1))
    fi
}

# Main scanning logic
main() {
    log "Starting comprehensive PHI exposure scan..."
    
    # Scan for actual PHI patterns
    scan_patterns "PHI" "${phi_patterns[@]}"
    
    # Check logging exposure
    check_logging_exposure
    
    # Check hardcoded credentials
    check_hardcoded_credentials
    
    # Check test data exposure
    check_test_data_exposure
    
    # Check insecure configurations
    check_insecure_configs
    
    # Report results
    echo ""
    if [ $found_issues -eq 0 ] && [ $warnings -eq 0 ]; then
        ok "✅ No PHI exposure detected - Intelluxe AI codebase is clean"
        exit 0
    elif [ $found_issues -eq 0 ] && [ $warnings -gt 0 ]; then
        warn "⚠ Found $warnings potential security concerns (no PHI detected)"
        log "Please review warnings for HIPAA compliance"
        exit 0
    else
        err "❌ Found $found_issues potential PHI exposure issues and $warnings warnings"
        err "IMMEDIATE ACTION REQUIRED: Review and remediate PHI exposure"
        log ""
        log "HIPAA Compliance Guidelines:"
        log "1. Remove any actual PHI from code, logs, and configuration"
        log "2. Use environment variables for sensitive configuration"
        log "3. Implement proper logging controls"
        log "4. Ensure test data is clearly synthetic"
        log "5. Review access controls and encryption"
        exit 1
    fi
}

# Run the scan
main "$@"
