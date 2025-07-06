#!/usr/bin/env bash
# CI test configuration - makes tests more reliable in CI environment
# This file is sourced by tests to provide CI-specific overrides

if [[ "${CI:-false}" == "true" || "${GITHUB_ACTIONS:-false}" == "true" ]]; then
    # CI-specific test configurations
    
    # Skip tests that require specific system conditions
    export SKIP_SYSTEM_TESTS="${SKIP_SYSTEM_TESTS:-true}"
    
    # Mock commands that don't work well in CI
    export MOCK_SYSTEM_COMMANDS="${MOCK_SYSTEM_COMMANDS:-true}"
    
    # Use safer timeouts for CI
    export TEST_TIMEOUT="${TEST_TIMEOUT:-30}"
    
    # CI-specific paths and configurations
    export CI_MODE=true
    
    # Set up temporary directories that work in CI
    export TEST_CFG_ROOT="${TEST_CFG_ROOT:-/tmp/test-homelab-config}"
    export TEST_LOG_DIR="${TEST_LOG_DIR:-/tmp/test-homelab-logs}"
    
    # Create test directories
    mkdir -p "$TEST_CFG_ROOT" "$TEST_LOG_DIR"
    
    # Functions to help with CI testing
    skip_if_ci() {
        if [[ "${CI:-false}" == "true" ]]; then
            skip "${1:-Skipped in CI environment}"
        fi
    }
    
    skip_if_no_docker() {
        if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
            skip "${1:-Skipped: Docker not available}"
        fi
    }
    
    skip_if_no_root() {
        if [[ $EUID -ne 0 ]] && ! sudo -n true 2>/dev/null; then
            skip "${1:-Skipped: Root access not available}"
        fi
    }
fi
