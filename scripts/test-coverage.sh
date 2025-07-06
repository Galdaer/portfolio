#!/usr/bin/env bash
# test-coverage.sh - Test coverage generation locally
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COVERAGE_DIR="$REPO_ROOT/coverage-test"

echo "Testing coverage generation locally..."

# Clean up previous test coverage
rm -rf "$COVERAGE_DIR"
mkdir -p "$COVERAGE_DIR"

# Check if kcov is available
if ! command -v kcov >/dev/null 2>&1; then
    echo "kcov not found. Installing with setup-environment.sh..."
    sudo "$REPO_ROOT/scripts/setup-environment.sh"
fi

echo "Running tests with kcov coverage..."
cd "$REPO_ROOT"

# Run a simple test with coverage
kcov \
    --exclude-pattern=/usr,/lib,/bin,/sbin,/opt,/var,/etc,/home,/root \
    --include-pattern="$REPO_ROOT/scripts" \
    --coveralls-id="local-test" \
    --verify \
    "$COVERAGE_DIR" \
    bats test/config-management.bats

echo "Coverage generation completed!"
echo "Coverage files:"
find "$COVERAGE_DIR" -type f | head -10

echo "Coverage HTML files:"
find "$COVERAGE_DIR" -name "*.html"

echo "You can view the coverage report by opening:"
find "$COVERAGE_DIR" -name "index.html" | head -1
