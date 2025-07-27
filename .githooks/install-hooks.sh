#!/bin/bash
# Install git hooks for Intelluxe AI Healthcare System

set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_DIR="$REPO_ROOT/.githooks"

echo "🔗 Installing Intelluxe AI Healthcare git hooks..."

# Configure git to use our hooks directory
git config core.hooksPath "$HOOKS_DIR"

# Make hooks executable
chmod +x "$HOOKS_DIR"/*

echo "✅ Git hooks installed successfully!"
echo ""
echo "📋 Available hooks:"
echo "   - pre-push: Runs 'make lint && make validate && make test-quiet'"
echo ""
echo "💡 To disable temporarily: git push --no-verify"
echo "💡 To uninstall: git config --unset core.hooksPath"
