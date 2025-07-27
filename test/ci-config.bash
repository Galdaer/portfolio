#!/usr/bin/env bash
# CI test configuration - makes tests more reliable in CI environment

if [[ "${CI:-false}" == "true" || "${GITHUB_ACTIONS:-false}" == "true" ]]; then
    # CI-specific test configurations
    
    # Skip tests that require specific system conditions
    export SKIP_SYSTEM_TESTS="${SKIP_SYSTEM_TESTS:-true}"
    export SKIP_NETWORK_TESTS="${SKIP_NETWORK_TESTS:-true}"
    export SKIP_WIREGUARD_TESTS="${SKIP_WIREGUARD_TESTS:-true}"
    export SKIP_LOG_PATH_TESTS="${SKIP_LOG_PATH_TESTS:-true}"
    
    # Mock commands that don't work well in CI
    export MOCK_SYSTEM_COMMANDS="${MOCK_SYSTEM_COMMANDS:-true}"
    
    # Suppress verbose output in CI
    export BATS_VERBOSE="${BATS_VERBOSE:-false}"
    export QUIET_MODE="${QUIET_MODE:-true}"
    
    # Use safer timeouts for CI
    export TEST_TIMEOUT="${TEST_TIMEOUT:-30}"
    
    # CI-specific paths and configurations
    export CI_MODE=true
    
    # Set up temporary directories that work in CI
    export TEST_CFG_ROOT="${TEST_CFG_ROOT:-/tmp/test-intelluxe-config}"
    export TEST_LOG_DIR="${TEST_LOG_DIR:-/tmp/test-intelluxe-logs}"
    
    # Create test directories
    mkdir -p "$TEST_CFG_ROOT" "$TEST_LOG_DIR"
    
    echo "[CI] Test configuration loaded - verbose output suppressed" >&2
fi
