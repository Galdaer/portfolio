#!/usr/bin/env bash
# Quick MCP Pipeline validation script
set -euo pipefail

PIPELINE_HOST=${PIPELINE_HOST:-localhost}
PIPELINE_PORT=${PIPELINE_PORT:-9099}
INVOCATION_TOOL=${INVOCATION_TOOL:-find_patient}
LAST_NAME=${LAST_NAME:-Smith}

echo "[1] Health check"
curl -sf http://${PIPELINE_HOST}:${PIPELINE_PORT}/health | jq '.' || { echo "Health check failed"; exit 1; }

echo "[2] Tool count"
TOOL_COUNT=$(curl -s http://${PIPELINE_HOST}:${PIPELINE_PORT}/tools | jq '.data | length')
echo "Tools discovered: ${TOOL_COUNT}" || true

if [ "${TOOL_COUNT}" = "0" ]; then
  echo "No tools discovered - aborting"
  exit 2
fi

echo "[3] First five tools"
curl -s http://${PIPELINE_HOST}:${PIPELINE_PORT}/tools | jq '.data[0:5] | map({id: .id, name: .name})'

echo "[4] Invoke ${INVOCATION_TOOL}"
RESP=$(curl -s -X POST http://${PIPELINE_HOST}:${PIPELINE_PORT}/tools/${INVOCATION_TOOL}/invoke \
  -H 'Content-Type: application/json' \
  -d '{"arguments":{"lastName":"'"${LAST_NAME}"'"}}')
echo "$RESP" | jq '{tool: .data.tool_id, raw_type: (.data.raw | type)}'

if echo "$RESP" | jq -e '.data.status=="success"' >/dev/null 2>&1; then
  echo "Invocation success"
else
  echo "Invocation failed"; exit 3
fi

echo "Done."
