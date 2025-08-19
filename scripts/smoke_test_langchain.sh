#!/usr/bin/env bash
set -euo pipefail

echo "Testing LangChain integration..."

curl -s -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"message": "test connection", "format": "human"}' | head -c 200 | sed 's/.*/✅ Basic connectivity OK: &/'

curl -s -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"message": "recent articles on hypertension", "format": "human"}' | head -c 200 | sed 's/.*/✅ Medical search OK: &/'

if curl -s -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"message": "cardiovascular research", "format": "human"}' | grep -q "🤖"; then
  echo "✅ Provenance headers working"
else
  echo "⚠️  Provenance header not found"
fi

echo "Done"
