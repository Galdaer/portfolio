#!/usr/bin/env bash
# Test Ollama documentation endpoint for MCP server

set -euo pipefail

API_URL="http://localhost:3000/generate_documentation"
PROMPT="Generate a SOAP note for a patient encounter: Chief Complaint: Fatigue and headaches; Assessment: Likely stress-related symptoms; Plan: Stress management and follow-up; Visit Type: Follow-up."

response=$(curl -s -X POST "$API_URL" \
    -H "Content-Type: application/json" \
    -d "{\"prompt\": \"$PROMPT\"}")

echo "Response: $response"

if echo "$response" | grep -q 'documentation'; then
    echo "✅ Ollama documentation endpoint returned a result."
    exit 0
else
    echo "❌ No documentation returned."
    exit 1
fi
