#!/bin/bash
# MCP Pipeline Service Startup Script
# Healthcare-compliant MCP pipeline for Open WebUI integration

set -eu

echo "🏥 Starting Healthcare MCP Pipeline Service"
echo "Medical Disclaimer: Administrative support only, not medical advice"

# Configuration
export PIPELINES_PORT=${PIPELINES_PORT:-9099}
export PIPELINES_HOST=${PIPELINES_HOST:-0.0.0.0}
export MCP_CONFIG_PATH=${MCP_CONFIG_PATH:-/app/data/mcp_config.json}

# Optional config presence (warn only)
if [[ -f "$MCP_CONFIG_PATH" ]]; then
    echo "✅ Optional MCP config present: $MCP_CONFIG_PATH"
else
    echo "⚠️ Optional MCP config missing ($MCP_CONFIG_PATH); continuing (not required for thin proxy)"
fi

echo "🚀 Starting thin pipeline server (proxy mode)"
LOG_LEVEL_NORMALIZED="${LOG_LEVEL:-info}"
exec uvicorn pipelines.pipeline_server:app \
    --host "${PIPELINES_HOST}" \
    --port "${PIPELINES_PORT}" \
    --log-level "${LOG_LEVEL_NORMALIZED}" \
    ${UVICORN_EXTRA_ARGS:-}
