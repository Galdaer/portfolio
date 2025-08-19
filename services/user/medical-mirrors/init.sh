#!/bin/bash
# Initialize medical mirrors service
# Run this after deploying the service

set -e

echo "Initializing Medical Mirrors Service..."

# Wait for service to be ready
echo "Waiting for service to start..."
sleep 30

# Check health
echo "Checking service health..."
curl -f http://172.20.0.20:8080/health || {
    echo "Service health check failed"
    exit 1
}

# Get initial status
echo "Getting service status..."
curl -s http://172.20.0.20:8080/status | python3 -m json.tool

echo "Medical Mirrors Service is ready!"
echo ""
echo "To initialize data (this will take several hours):"
echo "  curl -X POST http://172.20.0.20:8080/update/pubmed"
echo "  curl -X POST http://172.20.0.20:8080/update/trials"
echo "  curl -X POST http://172.20.0.20:8080/update/fda"
echo ""
echo "Or run all updates:"
echo "  docker exec medical-mirrors /app/update-scripts/update_all.sh"
