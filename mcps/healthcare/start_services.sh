#!/bin/sh
# Healthcare MCP Service Startup Script - Direct MCP Integration
#
# Starts the authentication proxy with direct MCP communication for proper Open WebUI integration.
#
# Architecture:
# - Auth proxy (port 3001) - External authenticated endpoint with direct MCP communication
#
# Medical Disclaimer: This service provides administrative support only, not medical advice.

set -eu

# Configuration
AUTH_PROXY_PORT=3001

echo "🏥 Starting Healthcare MCP Services (Direct MCP Integration)..."
echo "Medical Disclaimer: Administrative support only, not medical advice"

# Set environment variable to run Healthcare MCP server in stdio mode
export MCP_TRANSPORT=stdio

# Start authentication proxy with direct MCP integration
echo "🔐 Starting authentication proxy with direct MCP on port $AUTH_PROXY_PORT..."
python3 /app/auth_proxy.py
