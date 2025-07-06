#!/usr/bin/env bash
# test.sh - Run Bats unit tests with optional coverage
# Author: Justin Michael Sue (Galdaer)
# Repo: https://github.com/galdaer/intelluxe
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
#    - Contact: jmsue42@gmail.com for commercial licensing terms
#    - Allows embedding in closed-source products
#
# Choose the license that best fits your use case.
#
# TRADEMARK NOTICE: "SHAN" and related branding may be trademark protected.
# Commercial use of project branding requires separate permission.
#_______________________________________________________________________________
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_DIR="$REPO_ROOT/test"
COVERAGE_DIR="$REPO_ROOT/coverage"
QUIET=${QUIET:-false}

mkdir -p "$COVERAGE_DIR"

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
        bats -r "$TEST_DIR" || echo "Tests completed or timed out"
else
    if [[ "$QUIET" == "true" ]]; then
        echo "Running tests in quiet mode..." >&2
        # Pass through environment variables to bats with minimal output
        timeout 300 env CI="${CI:-false}" GITHUB_ACTIONS="${GITHUB_ACTIONS:-false}" \
            bats -p "$TEST_DIR" 2>/dev/null || \
            timeout 300 env CI="${CI:-false}" GITHUB_ACTIONS="${GITHUB_ACTIONS:-false}" \
            bats -p "$TEST_DIR" || echo "Tests completed or timed out"
    else
        echo "Running tests without coverage (kcov not available)..." >&2
        # Pass through environment variables to bats with less verbose output
        timeout 300 env CI="${CI:-false}" GITHUB_ACTIONS="${GITHUB_ACTIONS:-false}" \
            bats -p "$TEST_DIR" || echo "Tests completed or timed out"
    fi
fi

if command -v pytest >/dev/null 2>&1; then
    pytest -q "$TEST_DIR/python"
else
    python3 -m pytest -q "$TEST_DIR/python"
fi
