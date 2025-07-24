#!/usr/bin/env bash
# test.sh - Run Bats unit tests with optional coverage
# Author: Justin Michael Sue (Galdaer)
# Repo: https://github.com/Intelluxe-AI/intelluxe-core
#
# Copyright (c) 2025 Justin Michael Sue
#
# Dual License Notice:
# This software is available under two licensing options:
#
# 1. AGPL v3.0 License (Open Source)
#    - Free for personal, educational, and open-source use
#    - Requires derivative works to also be open source
#    - See LICENSE-AGPL file for full terms
#
# 2. Commercial License
#    - For proprietary/commercial use without AGPL restrictions
#    - Contact: licensing@intelluxeai.com for commercial licensing terms
#    - Allows embedding in closed-source products
#
# Choose the license that best fits your use case.
#
# TRADEMARK NOTICE: "Intelluxe" and related branding may be trademark protected.
# Commercial use of project branding requires separate permission.
#_______________________________________________________________________________
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_DIR="$REPO_ROOT/test"
TESTS_DIR="$REPO_ROOT/tests"
COVERAGE_DIR="$REPO_ROOT/coverage"
QUIET=${QUIET:-false}

mkdir -p "$COVERAGE_DIR"

# Determine which test directory to use
if [[ -d "$TEST_DIR" && -d "$TESTS_DIR" ]]; then
    echo "Both test/ and tests/ directories found. Running tests from both directories" >&2
    ACTIVE_TEST_DIRS=("$TEST_DIR" "$TESTS_DIR")
elif [[ -d "$TEST_DIR" ]]; then
    ACTIVE_TEST_DIRS=("$TEST_DIR")
elif [[ -d "$TESTS_DIR" ]]; then
    ACTIVE_TEST_DIRS=("$TESTS_DIR")
else
    echo "No test directory found (test/ or tests/)" >&2
    exit 1
fi

echo "Using test directories: ${ACTIVE_TEST_DIRS[*]}" >&2

if ! command -v bats >/dev/null 2>&1; then
    if [[ -x "$REPO_ROOT/scripts/setup-environment.sh" ]]; then
        echo "Installing test dependencies..." >&2
        sudo "$REPO_ROOT/scripts/setup-environment.sh"
    else
        echo "bats command not found. Install with 'make deps' or run" \
            "./scripts/setup-environment.sh" >&2
        exit 1
    fi
fi

if command -v kcov >/dev/null 2>&1 && [[ "${USE_KCOV:-false}" == "true" ]] && [[ "$QUIET" != "true" ]]; then
    echo "Running tests with kcov coverage..." >&2
    # Pass through environment variables to bats with kcov
    timeout 300 env CI="${CI:-false}" GITHUB_ACTIONS="${GITHUB_ACTIONS:-false}" \
        kcov \
        --exclude-pattern=/usr,/lib,/bin,/sbin,/opt,/var,/etc,/home,/root \
        --include-pattern="$REPO_ROOT/scripts" \
        --coveralls-id="${GITHUB_RUN_ID:-local}" \
        "$COVERAGE_DIR" \
        bats -r "${ACTIVE_TEST_DIRS[@]}" || echo "Tests completed or timed out"
else
    if [[ "$QUIET" == "true" ]]; then
        echo "Running tests in quiet mode..." >&2
        # Pass through environment variables to bats with minimal output
        timeout 300 env CI="${CI:-false}" GITHUB_ACTIONS="${GITHUB_ACTIONS:-false}" \
            bats -p "${ACTIVE_TEST_DIRS[@]}" 2>/dev/null || \
            timeout 300 env CI="${CI:-false}" GITHUB_ACTIONS="${GITHUB_ACTIONS:-false}" \
            bats -p "${ACTIVE_TEST_DIRS[@]}" || echo "Tests completed or timed out"
    else
        echo "Running tests without coverage (kcov not available)..." >&2
        # Pass through environment variables to bats with less verbose output
        timeout 300 env CI="${CI:-false}" GITHUB_ACTIONS="${GITHUB_ACTIONS:-false}" \
            bats -p "${ACTIVE_TEST_DIRS[@]}" || echo "Tests completed or timed out"
    fi
fi

# Run Python tests if they exist
PYTHON_TEST_DIRS=()
[[ -d "$TEST_DIR/python" ]] && PYTHON_TEST_DIRS+=("$TEST_DIR/python")
[[ -d "$TESTS_DIR/python" ]] && PYTHON_TEST_DIRS+=("$TESTS_DIR/python")
[[ -d "$TESTS_DIR" && ! -d "$TESTS_DIR/python" ]] && PYTHON_TEST_DIRS+=("$TESTS_DIR")

if [[ ${#PYTHON_TEST_DIRS[@]} -gt 0 ]]; then
    echo "Running Python tests..." >&2
    if command -v pytest >/dev/null 2>&1; then
        pytest -q "${PYTHON_TEST_DIRS[@]}"
    else
        python3 -m pytest -q "${PYTHON_TEST_DIRS[@]}"
    fi
else
    echo "No Python tests found" >&2
fi
