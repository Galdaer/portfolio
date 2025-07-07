#!/bin/bash
# Script to restart the GitHub Actions runner

set -e

echo "🔄 Restarting GitHub Actions runner..."

# Stop the service
sudo systemctl stop actions.runner.*

# Wait a moment
sleep 5

# Start the service
sudo systemctl start actions.runner.*

# Check status
sudo systemctl status actions.runner.* --no-pager

echo "✅ Runner restarted successfully!"
